"""Start RealConvert.

This sets everything up the first time (a private Python environment in the
.venv folder with yt-dlp, ffmpeg and Deno inside it), keeps the download
engine up to date, then opens the app in your browser.

Usage:  python run.py [--lan] [--port 8765] [--no-browser] [--no-update]
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / '.venv'
REQUIREMENTS = HERE / 'requirements.txt'
STAMP = VENV / '.realconvert-installed'
UPDATE_EVERY = 12 * 3600  # seconds between automatic engine update checks
MIN_PYTHON = (3, 10)


def say(msg: str = '') -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode(), flush=True)


def fail(msg: str) -> None:
    say()
    say('  ' + msg.replace('\n', '\n  '))
    say()
    if sys.stdin and sys.stdin.isatty():
        try:
            input('  Press Enter to close…')
        except Exception:
            pass
    sys.exit(1)


def in_our_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except Exception:
        return False


def venv_python() -> Path:
    return VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def pip(*args: str, quiet: bool = False) -> int:
    cmd = [sys.executable, '-m', 'pip', *args, '--disable-pip-version-check']
    if quiet:
        cmd.append('-q')
    return subprocess.call(cmd)


def can_import(*modules: str) -> bool:
    code = '; '.join(f'import {m}' for m in modules)
    return subprocess.call([sys.executable, '-c', code],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def ensure_venv() -> None:
    """Create .venv (if needed) and re-launch this script inside it."""
    if not venv_python().exists():
        say('  Setting up RealConvert for the first time (this only happens once)…')
        rc = subprocess.call([sys.executable, '-m', 'venv', str(VENV)])
        if rc != 0 or not venv_python().exists():
            hint = ''
            if sys.platform.startswith('linux'):
                hint = '\nOn Ubuntu/Debian run:  sudo apt install python3-venv   then try again.'
            fail('Could not create the Python environment for RealConvert.' + hint)
    rc = subprocess.call([str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.exit(rc)


# Optional add-ons. deno: solves YouTube's JavaScript checks (needed for full YouTube support).
# curl-cffi: lets yt-dlp look like a real browser on sites that block plain downloaders.
EXTRAS = ('deno', 'curl-cffi')


def install_extras() -> None:
    if pip('install', f'yt-dlp[{",".join(EXTRAS)}]', quiet=True) == 0:
        return
    for extra in EXTRAS:
        if pip('install', f'yt-dlp[{extra}]', quiet=True) != 0:
            note = ' YouTube may be limited unless Deno or Node.js is installed.' if extra == 'deno' else ''
            say(f'  (Optional add-on "{extra}" isn’t available for this computer — skipping.{note})')


def install_or_update(skip_update: bool) -> None:
    first_run = not STAMP.exists() or not can_import('flask', 'yt_dlp', 'imageio_ffmpeg')
    if first_run:
        say('  Installing the download engine (yt-dlp), ffmpeg and the web app…')
        say('  This takes a minute or two the first time.\n')
        pip('install', '-U', 'pip', quiet=True)
        if pip('install', '-r', str(REQUIREMENTS)) != 0:
            fail('Installing failed. Check your internet connection and run RealConvert again.')
        install_extras()
        STAMP.write_text(str(time.time()))
        say()
        return
    if skip_update:
        return
    try:
        last = float(STAMP.read_text().strip() or 0)
    except Exception:
        last = 0
    if time.time() - last < UPDATE_EVERY:
        return
    say('  Checking for download-engine updates…')
    net = ('--retries', '1', '--timeout', '8')
    rc = pip('install', '-U', f'yt-dlp[default,{",".join(EXTRAS)}]', *net, quiet=True)
    if rc != 0:  # an optional extra may not exist for this computer; update the core on its own
        rc = pip('install', '-U', 'yt-dlp[default]', *net, quiet=True)
    if rc == 0:
        STAMP.write_text(str(time.time()))
    else:
        say('  (Couldn’t check for updates — carrying on with the installed version.)')


def main() -> None:
    if sys.version_info < MIN_PYTHON:
        fail(f'RealConvert needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer '
             f'(you have {sys.version.split()[0]}).\nGet the latest from https://www.python.org/downloads/')
    os.chdir(HERE)
    if not in_our_venv():
        ensure_venv()
        return
    args = [a for a in sys.argv[1:] if a != '--no-update']
    install_or_update(skip_update='--no-update' in sys.argv[1:])
    sys.path.insert(0, str(HERE))
    import app  # noqa: E402 - imported after dependencies are installed
    app.main(args)


if __name__ == '__main__':
    main()
