@echo off
rem Double-click this file to start RealConvert on Windows.
setlocal
title RealConvert
cd /d "%~dp0"

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto nopython

%PY% run.py %*
if errorlevel 1 (
  echo.
  echo   RealConvert stopped because of an error - see the messages above.
  pause
)
exit /b

:nopython
echo.
echo   RealConvert needs Python to run. It is free and only takes a minute to install.
echo.
where winget >nul 2>&1
if errorlevel 1 goto manual
choice /c YN /m "  Install Python now"
if errorlevel 2 goto manual
winget install -e --id Python.Python.3.13 --scope user --accept-source-agreements --accept-package-agreements
echo.
echo   All set. Close this window and double-click RealConvert-Windows.bat again.
pause
exit /b

:manual
echo   1. Install the latest Python from https://www.python.org/downloads/
echo   2. IMPORTANT: tick "Add python.exe to PATH" on the first screen of the installer.
echo   3. Double-click RealConvert-Windows.bat again.
start "" https://www.python.org/downloads/
pause
exit /b 1
