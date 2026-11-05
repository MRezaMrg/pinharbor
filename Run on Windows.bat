@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "ENV_DIR=%LOCALAPPDATA%\PinterestBoardStudio\venv"
set "PY=%ENV_DIR%\Scripts\python.exe"

if exist "%PY%" goto preflight
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m venv "%ENV_DIR%"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.10+ is required. Download from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    python -m venv "%ENV_DIR%"
)
if errorlevel 1 goto failed

:preflight
"%PY%" "%~dp0tools\bootstrap.py" check --requirements "%~dp0requirements.txt"
if errorlevel 3 (
    echo The virtual environment uses an unsupported Python version.
    echo Install Python 3.10+ and recreate the old environment at:
    echo %ENV_DIR%
    pause
    exit /b 1
)
if not errorlevel 1 goto run

echo Installing / updating PinHarbor Python dependencies...
"%PY%" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 goto failed
"%PY%" "%~dp0tools\bootstrap.py" record --requirements "%~dp0requirements.txt"
if errorlevel 1 goto failed

:run
"%PY%" "%~dp0pinterest_studio.py"
if errorlevel 1 goto failed
exit /b 0

:failed
echo PinHarbor could not start. See the error above and README-FA.md.
pause
exit /b 1
