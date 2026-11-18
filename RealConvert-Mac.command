#!/bin/bash
# Double-click this file to start RealConvert on a Mac.
cd "$(dirname "$0")" || exit 1

find_python() {
  for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
           python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 &&
       "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

PY="$(find_python)"
if [ -z "$PY" ]; then
  echo
  echo "  RealConvert needs Python 3.10 or newer. It's free."
  if command -v brew >/dev/null 2>&1; then
    read -r -p "  Install it now with Homebrew? [Y/n] " answer
    if [[ ! "$answer" =~ ^[Nn] ]]; then
      brew install python python-tk && PY="$(find_python)"
    fi
  fi
  if [ -z "$PY" ]; then
    echo "  Opening python.org: download and install Python, then double-click RealConvert-Mac.command again."
    open "https://www.python.org/downloads/macos/"
    read -r -p "  Press Enter to close..." _
    exit 1
  fi
fi

exec "$PY" run.py "$@"
