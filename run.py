"""Start RealConvert.

The first time, this sets everything up (a private Python environment in the
.venv folder with yt-dlp, ffmpeg and Deno inside it) and adds a RealConvert
shortcut to your desktop / Start menu / Applications. After that it opens
RealConvert in its own window, with no console window, and keeps the download
engine up to date.

Usage:
  python run.py                    open RealConvert in its own window (normal use)
  python run.py --console          run inside this terminal and use a browser tab instead
  python run.py --lan              like --console, and let phones on your Wi-Fi use it too
  python run.py --make-shortcuts   add the RealConvert shortcut/icon again
  Also: --port N, --no-update, --no-browser
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / '.venv'
REQUIREMENTS = HERE / 'requirements.txt'
STAMP = VENV / '.realconvert-installed'
SHORTCUT_STAMP = VENV / '.realconvert-shortcuts'
UPDATE_EVERY = 12 * 3600  # seconds between automatic engine update checks
MIN_PYTHON = (3, 10)
DEFAULT_PORT = 8765
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

# Optional add-ons. deno: solves YouTube's JavaScript checks (needed for full YouTube support).
# curl-cffi: lets yt-dlp look like a real browser on sites that block plain downloaders.
EXTRAS = ('deno', 'curl-cffi')


# --------------------------------------------------------------------------
# Output: the console when there is one, otherwise realconvert.log
# --------------------------------------------------------------------------

def has_console() -> bool:
    try:
        return sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        return False


CONSOLE = has_console()


def send_output_to_log() -> None:
    for folder in (HERE, Path(tempfile.gettempdir())):
        path = folder / 'realconvert.log'
        try:
            if path.exists() and path.stat().st_size > 2_000_000:
                path.unlink()
            log = open(path, 'a', encoding='utf-8', errors='replace', buffering=1)
            break
        except OSError:
            continue
    else:
        log = open(os.devnull, 'w')
    sys.stdout = sys.stderr = log
    print(f'\n===== RealConvert starting {time.strftime("%Y-%m-%d %H:%M:%S")} =====', flush=True)


def say(msg: str = '') -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode(), flush=True)
    except Exception:
        pass


def fail(msg: str) -> None:
    say()
    say('  ' + msg.replace('\n', '\n  '))
    say()
    if CONSOLE:
        try:
            input('  Press Enter to close…')
        except Exception:
            pass
    else:
        import desktop
        desktop.show_error(msg)
    sys.exit(1)


# --------------------------------------------------------------------------
# Installing and updating
# --------------------------------------------------------------------------

def in_our_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except Exception:
        return False


def venv_python() -> Path:
    return VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def _run(cmd: list[str], quiet: bool = False) -> int:
    if CONSOLE:
        return subprocess.call(cmd)
    return subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.DEVNULL,
                           creationflags=NO_WINDOW)


def helper_python() -> str:
    """The Python to run helper commands with (on Windows: python.exe with its console hidden)."""
    exe = Path(sys.executable)
    if exe.name.lower() == 'pythonw.exe' and exe.with_name('python.exe').exists():
        return str(exe.with_name('python.exe'))
    return str(exe)


def pip(*args: str, quiet: bool = False) -> int:
    return _run([helper_python(), '-m', 'pip', *args, '--disable-pip-version-check', *(['-q'] if quiet else [])])


def can_import(*modules: str) -> bool:
    code = '; '.join(f'import {m}' for m in modules)
    return subprocess.call([helper_python(), '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           stdin=subprocess.DEVNULL, creationflags=NO_WINDOW) == 0


def ensure_venv() -> None:
    """Create .venv (if needed) and re-launch this script inside it."""
    if not venv_python().exists():
        say('  Setting up RealConvert for the first time (this only happens once)…')
        rc = _run([sys.executable, '-m', 'venv', str(VENV)])
        if rc != 0 or not venv_python().exists():
            hint = ''
            if sys.platform.startswith('linux'):
                hint = '\nOn Ubuntu/Debian run:  sudo apt install python3-venv   then try again.'
            fail('Could not create the Python environment for RealConvert.' + hint)
    if CONSOLE:
        rc = subprocess.call([str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]])
    else:
        python = venv_python()
        pythonw = python.with_name('pythonw.exe')
        rc = subprocess.call([str(pythonw if pythonw.exists() else python), str(Path(__file__).resolve()),
                              *sys.argv[1:]], creationflags=NO_WINDOW)
    sys.exit(rc)


def needs_install() -> bool:
    return not STAMP.exists() or not can_import('flask', 'yt_dlp', 'imageio_ffmpeg')


def install() -> None:
    say('  Installing the download engine (yt-dlp), ffmpeg and the app…')
    say('  This takes a minute or two the first time.\n')
    pip('install', '-U', 'pip', quiet=True)
    if pip('install', '-r', str(REQUIREMENTS)) != 0:
        fail('Installing failed. Check your internet connection and open RealConvert again.')
    if pip('install', f'yt-dlp[{",".join(EXTRAS)}]', quiet=True) != 0:
        for extra in EXTRAS:
            if pip('install', f'yt-dlp[{extra}]', quiet=True) != 0:
                note = ' YouTube may be limited unless Deno or Node.js is installed.' if extra == 'deno' else ''
                say(f'  (Optional add-on "{extra}" isn’t available for this computer — skipping.{note})')
    STAMP.write_text(str(time.time()))
    say()


def update_due() -> bool:
    try:
        last = float(STAMP.read_text().strip() or 0)
    except Exception:
        last = 0
    return time.time() - last >= UPDATE_EVERY


def update() -> None:
    say('  Checking for download-engine updates…')
    net = ('--retries', '1', '--timeout', '8')
    rc = pip('install', '-U', f'yt-dlp[default,{",".join(EXTRAS)}]', *net, quiet=True)
    if rc != 0:  # an optional extra may not exist for this computer; update the core on its own
        rc = pip('install', '-U', 'yt-dlp[default]', *net, quiet=True)
    if rc == 0:
        STAMP.write_text(str(time.time()))
    else:
        say('  (Couldn’t check for updates — carrying on with the installed version.)')


def ensure_shortcuts(force: bool = False) -> None:
    if SHORTCUT_STAMP.exists() and not force:
        return
    import desktop
    try:
        places = desktop.make_shortcuts(VENV)
    except Exception as exc:
        places = []
        say(f'  (Couldn’t add a RealConvert shortcut: {exc})')
    SHORTCUT_STAMP.write_text('\n'.join(places) or 'none')
    if places:
        say('  Added a RealConvert icon to: ' + ', '.join(places))


# --------------------------------------------------------------------------
# App mode helpers
# --------------------------------------------------------------------------

def ping(port: int) -> str | None:
    """'RealConvert' if the app is running on this port, 'starting' if it is starting up."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/api/ping', timeout=1.5) as resp:
            return json.load(resp).get('app')
    except Exception:
        return None


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if os.name != 'nt':
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def start_in_background(args: list[str]) -> None:
    """Run another copy of RealConvert with no console window, so this one can close."""
    exe = sys.executable
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                  cwd=str(HERE), close_fds=True)
    if os.name == 'nt':
        pythonw = Path(exe).with_name('pythonw.exe')
        exe = str(pythonw) if pythonw.exists() else exe
        kwargs['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True
    subprocess.Popen([exe, str(Path(__file__).resolve()), *args], **kwargs)


SPLASH_HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>RealConvert</title>
<link rel="icon" href="data:,">
<style>
:root{--bg:#f5f5f9;--text:#15151d;--muted:#6b6b7e;--track:#e3e3ec;--accent:#6346f0}
@media (prefers-color-scheme:dark){:root{--bg:#0b0b11;--text:#f2f2f7;--muted:#9c9cb0;--track:#2a2a38;--accent:#7d68ff}}
html,body{height:100%;margin:0}
body{display:grid;place-items:center;background:var(--bg);color:var(--text);
font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.box{text-align:center;padding:16px}
svg{width:76px;height:76px;filter:drop-shadow(0 8px 22px rgba(124,92,255,.35))}
h1{font-size:24px;margin:18px 0 4px;letter-spacing:-.02em}
p{margin:0;color:var(--muted)}
.bar{width:220px;height:5px;border-radius:9px;background:var(--track);margin:22px auto 0;overflow:hidden}
.bar i{display:block;width:35%;height:100%;border-radius:inherit;background:var(--accent);animation:m 1.1s infinite ease-in-out}
@keyframes m{from{transform:translateX(-100%)}to{transform:translateX(300%)}}
</style></head><body><div class="box">
<svg viewBox="0 0 64 64" aria-hidden="true"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#ff4d8d"/></linearGradient></defs>
<rect width="64" height="64" rx="16" fill="url(#g)"/>
<path d="M26 14.5c0-1.6 1.8-2.6 3.1-1.7l13.6 9.2c1.2.8 1.2 2.6 0 3.4l-13.6 9.2c-1.3.9-3.1-.1-3.1-1.7z" fill="#fff"/>
<path d="M19 41.5v4a4 4 0 0 0 4 4h18a4 4 0 0 0 4-4v-4" fill="none" stroke="#fff" stroke-width="4.5"
stroke-linecap="round" stroke-linejoin="round"/></svg>
<h1>RealConvert</h1><p id="msg">Starting…</p><div class="bar"><i></i></div></div>
<script>
async function tick(){
  try{
    const r=await fetch('/api/ping',{cache:'no-store'}); const d=await r.json();
    if(d.app==='RealConvert'){location.replace('/');return}
    if(d.message)document.getElementById('msg').textContent=d.message;
  }catch(e){}
  setTimeout(tick,400);
}
tick();
</script></body></html>'''


class Splash:
    """A tiny 'Starting…' page shown in the app window while RealConvert gets ready."""

    def __init__(self, port: int):
        self.message = 'Starting…'
        splash = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path.startswith('/api/ping'):
                    body = json.dumps({'app': 'starting', 'message': splash.message}).encode()
                    ctype = 'application/json'
                else:
                    body, ctype = SPLASH_HTML.encode(), 'text/html; charset=utf-8'
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def set(self, message: str) -> None:
        self.message = message

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def option(args: list[str], name: str, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    if not CONSOLE:
        send_output_to_log()
    if sys.version_info < MIN_PYTHON:
        fail(f'RealConvert needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer '
             f'(you have {sys.version.split()[0]}).\nGet the latest from https://www.python.org/downloads/')
    os.chdir(HERE)
    if not in_our_venv():
        ensure_venv()
        return
    sys.path.insert(0, str(HERE))
    args = sys.argv[1:]
    import desktop

    if '--make-shortcuts' in args:
        ensure_shortcuts(force=True)
        say('  ' + desktop.shortcut_hint())
        return

    # --console / --lan: the classic way, inside this terminal with a browser tab.
    if '--console' in args or '--lan' in args:
        if needs_install():
            install()
        elif update_due() and '--no-update' not in args:
            update()
        ensure_shortcuts()
        import app
        app.main([a for a in args if a not in ('--console', '--no-update')])
        return

    try:
        port = int(option(args, '--port', os.environ.get('REALCONVERT_PORT', DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT

    # Already open (or opening)? Just bring up a window.
    if ping(port) in ('RealConvert', 'starting'):
        desktop.open_app_window(f'http://127.0.0.1:{port}')
        return

    if CONSOLE:
        # Started from the start file: do any first-time setup here where you can watch it,
        # then hand over to a copy of RealConvert that has no console window.
        if needs_install():
            install()
        ensure_shortcuts()
        start_in_background(args)
        say('\n  RealConvert is opening in its own window.')
        say('  ' + desktop.shortcut_hint())
        say('  You can close this window.\n')
        if os.name == 'nt':
            time.sleep(4)  # long enough to read; then the window closes by itself
        return

    # No console (desktop icon, Start menu, Applications): show "Starting…" in the app window right away.
    start_port = port
    while not port_free(port):
        port += 1
        if port > start_port + 50:
            fail('RealConvert couldn’t find a free port to run on.')
    splash = Splash(port)
    if '--no-browser' not in args:
        desktop.open_app_window(f'http://127.0.0.1:{port}')
    try:
        if needs_install():
            splash.set('Setting up for the first time — this takes a minute or two…')
            install()
        elif update_due() and '--no-update' not in args:
            splash.set('Checking for updates…')
            update()
        ensure_shortcuts()
        splash.set('Starting…')
        import app
    except BaseException:
        splash.close()
        raise
    splash.close()
    passthrough = [a for a in args if a in ('--no-update',)]
    app.main(['--port', str(port), '--app-mode', '--no-browser', *passthrough])


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # never fail silently when there's no console to show the error
        import traceback
        traceback.print_exc()
        if not CONSOLE:
            sys.path.insert(0, str(HERE))
            import desktop
            desktop.show_error(f'Something went wrong: {exc}\n\nDetails are in realconvert.log in the '
                               f'RealConvert folder.')
        raise
