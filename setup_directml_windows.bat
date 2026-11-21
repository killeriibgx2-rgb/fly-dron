@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 goto :launcher_missing

if not exist ".venv-directml\Scripts\python.exe" (
  echo Creating an isolated DirectML environment with Python 3.11...
  py -3.11 -m venv .venv-directml >nul 2>nul
)

if not exist ".venv-directml\Scripts\python.exe" (
  echo Python 3.11 is not installed yet. Trying to install it with the Python launcher...
  py install 3.11
  if errorlevel 1 goto :python_install_failed
  py -3.11 -m venv .venv-directml
  if errorlevel 1 goto :failed
)

if not exist ".venv-directml\Scripts\python.exe" goto :python_install_failed

echo Checking pip in the DirectML environment...
".venv-directml\Scripts\python.exe" -m pip --version
if errorlevel 1 goto :failed

echo Installing DirectML and compatible libraries. This is a large download.
echo Your existing .venv will not be changed.
".venv-directml\Scripts\python.exe" -m pip install --disable-pip-version-check --timeout 120 --retries 10 -r requirements-directml.txt
if errorlevel 1 goto :failed

echo.
echo Setup finished. Double-click Start_LM_DirectML.vbs to try the RX 580.
echo DirectML is experimental; if its training test fails, the app will use CPU.
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
echo Then double-click setup_directml_windows.bat again.
pause
exit /b 1

:failed
echo.
echo DirectML setup failed. Your regular .venv remains untouched.
echo Check the error above and the DirectML troubleshooting section in README.md.
pause
exit /b 1
