@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\PinterestBoardStudio\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Please launch Run on Windows.bat once before updating download engines.
  pause
  exit /b 1
)
"%PY%" -m pip install --upgrade --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 goto failed
"%PY%" "%~dp0tools\bootstrap.py" record --requirements "%~dp0requirements.txt"
if errorlevel 1 goto failed
echo Download engine packages updated successfully.
pause
exit /b 0
:failed
echo Failed to update dependencies. Check internet access and retry.
pause
exit /b 1
