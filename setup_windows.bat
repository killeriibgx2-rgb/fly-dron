@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found.
  echo Install Python 3.11 for Windows, enable "Add Python to PATH", then run this file again.
  pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 was not found.
  echo Install Python 3.11 for Windows, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the private environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :failed
)

echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo Installing the desktop app and training libraries. This may take a while.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Setup finished. Double-click Start_LM.vbs to open the application.
pause
exit /b 0

:failed
echo.
echo Setup failed. Check the error above and see README.md for troubleshooting.
pause
exit /b 1
