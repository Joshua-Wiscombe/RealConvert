"""Desktop integration: the app window, shortcuts/icons, and error pop-ups.

Uses only the Python standard library, so run.py can use it before anything
else is installed.
"""

from __future__ import annotations

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

APP_NAME = 'RealConvert'
APP_DIR = Path(__file__).resolve().parent
ICONS = APP_DIR / 'static' / 'icons'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


# --------------------------------------------------------------------------
# The app window: a browser engine in "app mode" (own window, no tabs or
# address bar). Edge ships with Windows 10/11; Chrome/Edge/Brave elsewhere.
# --------------------------------------------------------------------------

def _windows_browsers() -> list[str]:
    found = []
    try:
        import winreg
        for exe in ('msedge.exe', 'chrome.exe', 'brave.exe'):
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    key = winreg.OpenKey(root, rf'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}')
                    found.append(winreg.QueryValue(key, None))
                except OSError:
                    pass
    except ImportError:
        pass
    bases = [os.environ.get(v) for v in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA')]
    rel = [r'Microsoft\Edge\Application\msedge.exe', r'Google\Chrome\Application\chrome.exe',
           r'BraveSoftware\Brave-Browser\Application\brave.exe']
    found += [str(Path(b) / r) for r in rel for b in bases if b]
    return found


def _mac_browsers() -> list[str]:
    apps = [('Google Chrome', 'Google Chrome'), ('Microsoft Edge', 'Microsoft Edge'),
            ('Brave Browser', 'Brave Browser'), ('Chromium', 'Chromium')]
    found = []
    for folder in ('/Applications', str(Path.home() / 'Applications')):
        for app, binary in apps:
            found.append(f'{folder}/{app}.app/Contents/MacOS/{binary}')
    return found


def _linux_browsers() -> list[str]:
    names = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge',
             'microsoft-edge-stable', 'brave-browser', 'brave')
    return [p for p in (shutil.which(n) for n in names) if p]


def find_app_browser() -> str | None:
    if sys.platform.startswith('win'):
        candidates = _windows_browsers()
    elif sys.platform == 'darwin':
        candidates = _mac_browsers()
    else:
        candidates = _linux_browsers()
    return next((c for c in candidates if c and Path(c).is_file()), None)


def open_app_window(url: str) -> bool:
    """Open RealConvert in its own window. Falls back to a normal browser tab."""
    browser = find_app_browser()
    if browser:
        try:
            subprocess.Popen([browser, f'--app={url}', '--window-size=1080,900'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=NO_WINDOW, start_new_session=(os.name != 'nt'))
            return True
        except Exception:
            pass
    try:
        return webbrowser.open(url)
    except Exception:
        return False


# --------------------------------------------------------------------------
# Error pop-up (there's no console window to print to in app mode)
# --------------------------------------------------------------------------

def show_error(message: str) -> None:
    title = f'{APP_NAME} couldn’t start'
    try:
        if sys.platform.startswith('win'):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
        elif sys.platform == 'darwin':
            script = f'display dialog {_applescript_str(message)} with title {_applescript_str(title)} ' \
                     f'buttons {{"OK"}} with icon stop'
            subprocess.run(['osascript', '-e', script], timeout=600)
        elif shutil.which('zenity'):
            subprocess.run(['zenity', '--error', f'--title={title}', f'--text={message}'], timeout=600)
        elif shutil.which('notify-send'):
            subprocess.run(['notify-send', title, message], timeout=30)
    except Exception:
        pass


def _applescript_str(text: str) -> str:
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


# --------------------------------------------------------------------------
# Shortcuts: desktop + Start menu (Windows), Applications (Mac), app menu (Linux)
# --------------------------------------------------------------------------

def make_shortcuts(venv: Path) -> list[str]:
    """Create launchers that open RealConvert with no console window. Returns where they were put."""
    run_py = APP_DIR / 'run.py'
    if sys.platform.startswith('win'):
        return _windows_shortcuts(venv / 'Scripts' / 'pythonw.exe', run_py)
    if sys.platform == 'darwin':
        return _mac_app(venv / 'bin' / 'python', run_py)
    return _linux_desktop_entry(venv / 'bin' / 'python', run_py)


_PS_SHORTCUTS = r'''
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
$made = @()
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
  if (-not $dir) { continue }
  try {
    $lnk = $shell.CreateShortcut((Join-Path $dir 'RealConvert.lnk'))
    $lnk.TargetPath = $env:RC_TARGET
    $lnk.Arguments = '"' + $env:RC_SCRIPT + '"'
    $lnk.WorkingDirectory = $env:RC_DIR
    $lnk.IconLocation = $env:RC_ICON + ',0'
    $lnk.Description = 'Download and convert videos from links'
    $lnk.Save()
    $made += $dir
  } catch { }
}
$made -join "`n"
'''


def _windows_shortcuts(pythonw: Path, run_py: Path) -> list[str]:
    if not pythonw.exists():
        return []
    env = dict(os.environ, RC_TARGET=str(pythonw), RC_SCRIPT=str(run_py), RC_DIR=str(APP_DIR),
               RC_ICON=str(ICONS / 'icon.ico'))
    proc = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                           '-Command', _PS_SHORTCUTS], env=env, capture_output=True, text=True,
                          timeout=60, creationflags=NO_WINDOW)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _mac_app(python: Path, run_py: Path) -> list[str]:
    for folder in (Path('/Applications'), Path.home() / 'Applications'):
        try:
            folder.mkdir(exist_ok=True)
            build_mac_app(folder / f'{APP_NAME}.app', python, run_py)
            return [str(folder)]
        except OSError:
            continue
    return []


def build_mac_app(bundle: Path, python: Path, run_py: Path) -> None:
    """A tiny .app that starts RealConvert in the background (no Terminal window)."""
    if bundle.exists():
        shutil.rmtree(bundle)
    macos, resources = bundle / 'Contents' / 'MacOS', bundle / 'Contents' / 'Resources'
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)
    with open(bundle / 'Contents' / 'Info.plist', 'wb') as f:
        plistlib.dump({
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleIdentifier': 'local.realconvert.app',
            'CFBundleExecutable': APP_NAME,
            'CFBundleIconFile': APP_NAME,
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1',
            'LSMinimumSystemVersion': '10.13',
            'LSUIElement': True,  # no bouncing Dock icon: the RealConvert window is the app
        }, f)
    launcher = macos / APP_NAME
    launcher.write_text(f'#!/bin/bash\nexec {shlex.quote(str(python))} {shlex.quote(str(run_py))} "$@"\n')
    launcher.chmod(0o755)
    shutil.copy(ICONS / 'icon.icns', resources / f'{APP_NAME}.icns')
    if sys.platform == 'darwin':
        # Clear any "downloaded from the internet" flag and sign it locally, so macOS opens it without fuss.
        for cmd in (['xattr', '-cr', str(bundle)], ['codesign', '--force', '--deep', '--sign', '-', str(bundle)]):
            try:
                subprocess.run(cmd, capture_output=True, timeout=60)
            except Exception:
                pass
    os.utime(bundle)  # nudge Finder to pick up the icon


def _linux_desktop_entry(python: Path, run_py: Path) -> list[str]:
    folder = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'applications'
    try:
        folder.mkdir(parents=True, exist_ok=True)
        entry = folder / 'realconvert.desktop'
        entry.write_text('\n'.join([
            '[Desktop Entry]',
            'Type=Application',
            f'Name={APP_NAME}',
            'Comment=Download and convert videos from links',
            f'Exec="{python}" "{run_py}"',
            f'Icon={ICONS / "icon-512.png"}',
            'Terminal=false',
            'Categories=AudioVideo;Video;Network;',
            'StartupNotify=false',
            '',
        ]))
        entry.chmod(0o755)
        return [str(folder)]
    except OSError:
        return []


def shortcut_hint() -> str:
    if sys.platform.startswith('win'):
        return 'Next time, open RealConvert from the icon on your desktop or in the Start menu.'
    if sys.platform == 'darwin':
        return 'Next time, open RealConvert from Launchpad, Spotlight or your Applications folder.'
    return 'Next time, open RealConvert from your applications menu.'
