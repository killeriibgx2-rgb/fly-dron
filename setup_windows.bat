@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 goto :launcher_missing

if not exist ".venv\Scripts\python.exe" (
  echo Creating the private environment with Python 3.11...
  py -3.11 -m venv .venv >nul 2>nul
)

if not exist ".venv\Scripts\python.exe" (
  echo Python 3.11 is not installed yet. Trying to install it with the Python launcher...
  py install 3.11
  if errorlevel 1 goto :python_install_failed
  echo Creating the private environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :failed
)

if not exist ".venv\Scripts\python.exe" goto :python_install_failed

echo Checking the existing pip installation...
".venv\Scripts\python.exe" -m pip --version
if errorlevel 1 goto :failed

echo Installing the app and Qwen fine-tuning libraries. This may take a while.
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --timeout 120 --retries 10 -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Setup finished. Double-click Start_LM.vbs to open the application.
pause
exit /b 0

:launcher_missing
echo The Python launcher was not found.
echo Install Python 3.11 for Windows, including the Python launcher, then run this file again.
pause
exit /b 1

:python_install_failed
echo.
echo Python 3.11 could not be installed automatically.
echo Open PowerShell in this folder and run: py install 3.11
echo Then double-click setup_windows.bat again.
pause
exit /b 1

:failed
echo.
echo Setup failed. Check the error above and see README.md for troubleshooting.
pause
exit /b 1
