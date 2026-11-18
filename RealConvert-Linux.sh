#!/usr/bin/env bash
# Start RealConvert on Linux:  ./RealConvert-Linux.sh   (add --lan to use it from your phone)
cd "$(dirname "$0")" || exit 1

for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    exec "$c" run.py "$@"
  fi
done

echo "RealConvert needs Python 3.10 or newer."
echo "Ubuntu/Debian:  sudo apt install python3 python3-venv python3-tk"
echo "Fedora:         sudo dnf install python3 python3-tkinter"
echo "Arch:           sudo pacman -S python tk"
exit 1
