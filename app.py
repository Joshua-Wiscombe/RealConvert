"""RealConvert local web server.

Run `python run.py` (or double-click the start file for your system) rather
than this file directly — run.py installs and updates everything first.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file
from werkzeug.serving import make_server

import engine

APP_NAME = 'RealConvert'
APP_VERSION = '1.0.0'
DEFAULT_PORT = 8765
STATIC_DIR = engine.APP_DIR / 'static'

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path='/static')
app.json.ensure_ascii = False
settings = engine.Settings()
jobs = engine.JobManager(settings)

STATE = {'lan': False, 'port': DEFAULT_PORT, 'restart_needed': False, 'updating': False,
         'app_mode': False, 'last_seen': None, 'bye_at': None, 'visible': True}
WINDOW_GONE_AFTER = 25           # seconds without a sign of life from a window that's on screen
HIDDEN_WINDOW_GONE_AFTER = 150   # minimized/hidden windows check in much less often
BYE_GRACE = 6             # seconds to wait after the window closes, in case it was only reloading
LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}


def _hostname(host: str) -> str:
    if host.startswith('['):
        return host[1:].split(']')[0]
    return host.rsplit(':', 1)[0] if host.count(':') == 1 else host


# --------------------------------------------------------------------------
# Safety: only this computer's browser (or the LAN with --lan) may use the app,
# and other websites can't trigger downloads through it.
# --------------------------------------------------------------------------

@app.before_request
def guard():
    if not STATE['lan'] and _hostname(request.host or '') not in LOCAL_HOSTS:
        abort(403)
    if request.path == '/api/bye':
        # Sent by the page as it closes (navigator.sendBeacon can't add headers): same-origin only.
        origin = request.headers.get('Origin')
        if origin and _hostname(origin.split('://', 1)[-1]) != _hostname(request.host or ''):
            abort(403)
        return None
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('X-RealConvert') != '1':
        abort(403)
    if request.path.startswith('/api/') and request.path != '/api/ping':
        STATE['last_seen'] = time.time()
        if request.headers.get('X-RealConvert-Visible') in ('0', '1'):
            STATE['visible'] = request.headers['X-RealConvert-Visible'] == '1'


@app.after_request
def headers(resp: Response):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    if request.path == '/' or request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'no-cache'
    return resp


def body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def normalize_url(raw) -> str:
    url = str(raw or '').strip()
    if not url:
        raise ValueError('Paste a link first.')
    if re.match(r'^[a-z][a-z0-9+.-]*://', url, re.I):
        if not re.match(r'^https?://', url, re.I):
            raise ValueError('Only web links (starting with http:// or https://) are supported.')
        return url
    return 'https://' + url


def error(message: str, status: int = 400, detail: str | None = None):
    return jsonify({'error': message, 'detail': detail}), status


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@app.get('/')
def index():
    return send_file(STATIC_DIR / 'index.html')


@app.post('/api/bye')
def bye():
    STATE['bye_at'] = time.time()
    return ('', 204)


@app.get('/api/ping')
def ping():
    return jsonify({'app': APP_NAME, 'version': APP_VERSION})


@app.get('/api/status')
def status():
    s = settings.snapshot()
    return jsonify({
        'app_version': APP_VERSION,
        'ytdlp_version': engine.ytdlp_version(),
        'ffmpeg': bool(engine.FFMPEG),
        'ffmpeg_version': FFMPEG_VERSION,
        'js_runtime': next(iter(engine.JS_RUNTIMES), None),
        'restart_needed': STATE['restart_needed'],
        'updating': STATE['updating'],
        'lan': STATE['lan'],
        'lan_url': lan_url() if STATE['lan'] else None,
        'app_mode': STATE['app_mode'],
        'settings': s,
        'browsers': list(engine.COOKIE_BROWSERS),
        'platform': sys.platform,
    })


# --------------------------------------------------------------------------
# Links and downloads
# --------------------------------------------------------------------------

@app.post('/api/info')
def info():
    try:
        url = normalize_url(body().get('url'))
    except ValueError as exc:
        return error(str(exc))
    try:
        return jsonify(engine.get_info(url, settings.snapshot()))
    except Exception as exc:
        message, detail = engine.friendly_error(exc)
        engine.log(f'[info] {url} failed: {detail}')
        return error(message, 422, detail)


@app.post('/api/download')
def download():
    data = body()
    meta = {k: data.get(k) for k in ('title', 'thumbnail', 'platform', 'platform_key')}
    try:
        job = jobs.submit(normalize_url(data.get('url')), data, meta)
    except ValueError as exc:
        return error(str(exc))
    return jsonify(job.to_dict())


@app.get('/api/jobs')
def list_jobs():
    return jsonify({'jobs': jobs.list(), 'restart_needed': STATE['restart_needed']})


def _job_or_404(job_id: str) -> engine.Job:
    job = jobs.get(job_id)
    if not job:
        abort(404)
    return job


@app.post('/api/jobs/<job_id>/cancel')
def cancel_job(job_id):
    _job_or_404(job_id)
    return jsonify({'ok': jobs.cancel(job_id)})


@app.post('/api/jobs/<job_id>/remove')
def remove_job(job_id):
    return jsonify({'ok': jobs.remove(job_id)})


@app.post('/api/jobs/clear')
def clear_jobs():
    return jsonify({'removed': jobs.clear_finished()})


@app.post('/api/jobs/<job_id>/retry')
def retry_job(job_id):
    old = _job_or_404(job_id)
    o = old.options
    raw = {
        'format': o['format'], 'quality': o['quality'], 'audio_quality': o['audio_quality'],
        'compat': o['compat'], 'trim_start': o['trim_start'], 'trim_end': o['trim_end'],
    }
    meta = {'title': old.title, 'thumbnail': old.thumbnail, 'platform': old.platform,
            'platform_key': old.platform_key}
    jobs.remove(job_id)
    job = jobs.submit(old.url, raw, meta)
    return jsonify(job.to_dict())


def _job_file(job: engine.Job, index: int) -> Path:
    if index < 0 or index >= len(job.files):
        abort(404)
    path = job.files[index]
    if not path.exists():
        abort(410)
    return path


@app.post('/api/jobs/<job_id>/open')
def open_job_file(job_id):
    job = _job_or_404(job_id)
    data = body()
    path = _job_file(job, int(data.get('index') or 0))
    try:
        engine.open_in_file_manager(path, select=data.get('target') != 'file')
    except Exception as exc:
        return error(f'Couldn’t open it: {exc}', 500)
    return jsonify({'ok': True})


@app.get('/api/jobs/<job_id>/file')
def job_file(job_id):
    job = _job_or_404(job_id)
    path = _job_file(job, int(request.args.get('index') or 0))
    inline = request.args.get('inline') == '1'
    return send_file(path, as_attachment=not inline, download_name=path.name, conditional=True)


@app.get('/api/thumb/<key>')
def thumb(key):
    result = engine.THUMBS.fetch(key)
    if not result:
        abort(404)
    data, ctype = result
    resp = Response(data, mimetype=ctype)
    resp.headers['Cache-Control'] = 'max-age=86400'
    return resp


# --------------------------------------------------------------------------
# Settings, folders, engine updates
# --------------------------------------------------------------------------

@app.get('/api/settings')
def get_settings():
    return jsonify(settings.snapshot())


@app.post('/api/settings')
def save_settings():
    try:
        return jsonify(settings.update(body()))
    except ValueError as exc:
        return error(str(exc))


@app.post('/api/open-folder')
def open_output_folder():
    try:
        engine.open_in_file_manager(settings.output_dir(), select=False)
    except Exception as exc:
        return error(f'Couldn’t open the folder: {exc}', 500)
    return jsonify({'ok': True})


PICK_FOLDER_SCRIPT = r'''
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    sys.exit(3)
root = tk.Tk()
root.withdraw()
try:
    root.attributes("-topmost", True)
except Exception:
    pass
path = filedialog.askdirectory(initialdir=sys.argv[1] if len(sys.argv) > 1 else None,
                               title="Choose where RealConvert saves files")
sys.stdout.write(path or "")
'''


@app.post('/api/pick-folder')
def pick_folder():
    """Open the system's folder picker (runs in its own process so it works on every OS)."""
    if STATE['lan'] and (request.remote_addr or '') not in ('127.0.0.1', '::1'):
        return error('The folder picker only works on the computer running RealConvert.', 400)
    try:
        proc = subprocess.run([sys.executable, '-c', PICK_FOLDER_SCRIPT, settings.snapshot()['output_dir']],
                              capture_output=True, text=True, timeout=600,
                              creationflags=engine.NO_WINDOW)
    except subprocess.TimeoutExpired:
        return jsonify({'path': ''})
    if proc.returncode == 3:
        return error('This system has no folder picker — type the folder path instead.', 501)
    return jsonify({'path': proc.stdout.strip()})


def _pypi_latest() -> str | None:
    try:
        with urllib.request.urlopen('https://pypi.org/pypi/yt-dlp/json', timeout=10,
                                    context=engine.ssl_context()) as resp:
            return json.load(resp)['info']['version']
    except Exception:
        return None


def _normalize_version(v: str | None) -> tuple:
    if not v:
        return ()
    return tuple(int(x) for x in v.replace('-', '.').split('.') if x.isdigit())


@app.post('/api/update')
def update_engine():
    if STATE['updating']:
        return error('An update is already running.', 409)
    STATE['updating'] = True
    try:
        current = engine.ytdlp_version()
        latest = _pypi_latest()
        if latest and _normalize_version(latest) <= _normalize_version(current):
            return jsonify({'updated': False, 'version': current, 'message': f'Already up to date (yt-dlp {current}).'})
        python = Path(sys.executable)
        if python.name.lower() == 'pythonw.exe' and python.with_name('python.exe').exists():
            python = python.with_name('python.exe')
        proc = subprocess.run([str(python), '-m', 'pip', 'install', '-U', '--disable-pip-version-check',
                               'yt-dlp[default]'], capture_output=True, text=True, timeout=600,
                              creationflags=engine.NO_WINDOW)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or '').strip().splitlines()[-3:]
            return error('The update failed. Check your internet connection and try again.', 502, ' '.join(tail))
        try:
            from importlib.metadata import version
            new_version = version('yt-dlp')
        except Exception:
            new_version = latest or 'new version'
        changed = _normalize_version(new_version) != _normalize_version(current)
        STATE['restart_needed'] = STATE['restart_needed'] or changed
        msg = (f'Updated yt-dlp {current} → {new_version}. Close RealConvert and open it again to use it.'
               if changed else f'Already up to date (yt-dlp {current}).')
        return jsonify({'updated': changed, 'version': new_version, 'message': msg})
    except subprocess.TimeoutExpired:
        return error('The update took too long and was stopped.', 504)
    finally:
        STATE['updating'] = False


# --------------------------------------------------------------------------
# Startup
# --------------------------------------------------------------------------

FFMPEG_VERSION = None


def lan_url() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        return f'http://{ip}:{STATE["port"]}'
    except Exception:
        return None


def already_running(port: int) -> bool:
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{port}/api/ping')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=1.5) as resp:
            return json.load(resp).get('app') == APP_NAME
    except Exception:
        return False


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if os.name != 'nt':  # match the server's own setting, so a just-closed port counts as free
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def open_window(url: str, app_mode: bool) -> None:
    if app_mode:
        import desktop
        desktop.open_app_window(url)
    else:
        webbrowser.open(url)


def quit_when_window_closed(server) -> None:
    """In app mode, stop once the RealConvert window has been closed and nothing is downloading."""
    started = time.time()
    while True:
        time.sleep(2)
        now = time.time()
        if jobs.active_count():
            continue
        last, bye = STATE['last_seen'], STATE['bye_at']
        if last is None:
            if now - started > 180:  # the window never showed up
                break
            continue
        if now - last > (WINDOW_GONE_AFTER if STATE['visible'] else HIDDEN_WINDOW_GONE_AFTER):
            break
        if bye and bye > last and now - bye > BYE_GRACE:
            break
    engine.log('The RealConvert window was closed — quitting.')
    server.shutdown()


def main(argv=None):
    global FFMPEG_VERSION
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description='RealConvert — download and convert videos from links.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('REALCONVERT_PORT', DEFAULT_PORT)))
    parser.add_argument('--lan', action='store_true',
                        help='also allow phones/computers on your Wi-Fi to use RealConvert')
    parser.add_argument('--no-browser', action='store_true', help='don’t open the browser automatically')
    parser.add_argument('--app-mode', action='store_true',
                        help='open in its own window and quit when that window is closed')
    args = parser.parse_args(argv)
    if args.lan:
        args.app_mode = False

    host = '0.0.0.0' if args.lan else '127.0.0.1'
    port = args.port
    if already_running(port):
        print(f'RealConvert is already running — opening http://127.0.0.1:{port}')
        if not args.no_browser:
            open_window(f'http://127.0.0.1:{port}', args.app_mode)
        return
    while not port_free(host, port):
        port += 1
        if port > args.port + 50:
            print('Could not find a free port to run on.')
            sys.exit(1)

    moved = port != args.port
    STATE.update(lan=args.lan, port=port, app_mode=args.app_mode)
    FFMPEG_VERSION = engine.ffmpeg_version()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    jobs.cleanup_temp()

    url = f'http://127.0.0.1:{port}'
    line = '─' * 58
    print(f'\n  {line}')
    print(f'   RealConvert {APP_VERSION} is running  →  {url}')
    if args.lan and lan_url():
        print(f'   On your phone (same Wi-Fi)        →  {lan_url()}')
    print(f'   Saving files to: {settings.snapshot()["output_dir"]}')
    print(f'   Engine: yt-dlp {engine.ytdlp_version()} · ffmpeg {FFMPEG_VERSION or "MISSING"}'
          f' · JS runtime: {next(iter(engine.JS_RUNTIMES), "none")}')
    if args.app_mode:
        print('   Closing the RealConvert window quits the app (after any downloads finish).')
    else:
        print('   Keep this window open while you use RealConvert.')
        print('   Close it (or press Ctrl+C) to quit.')
    print(f'  {line}\n')
    if not engine.FFMPEG:
        print('  ! ffmpeg was not found. Downloads will work but converting will not.\n')
    if not engine.JS_RUNTIMES:
        print('  ! No JavaScript runtime (Deno) found. Some YouTube videos may fail or be lower quality.\n')

    server = make_server(host, port, app, threaded=True)
    if not args.no_browser or (moved and args.app_mode):
        threading.Timer(0.5, lambda: open_window(url, args.app_mode)).start()
    if args.app_mode:
        threading.Thread(target=quit_when_window_closed, args=(server,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping RealConvert…')
    finally:
        for job in list(jobs.jobs.values()):
            if job.active:
                jobs.cancel(job.id)
        time.sleep(0.3)
        jobs.cleanup_temp()


if __name__ == '__main__':
    main()
