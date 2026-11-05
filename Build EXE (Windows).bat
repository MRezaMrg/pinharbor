@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\PinterestBoardStudio\venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Run "Run on Windows.bat" first to initialize the environment.
    pause
    exit /b 1
)
"%PY%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto fail
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --name PinHarbor ^
    --collect-all gallery_dl --collect-all yt_dlp --collect-all imageio_ffmpeg ^
    --hidden-import gallery_dl.__main__ --add-data "app_icon.png;." --icon app_icon.ico pinterest_studio.py
if errorlevel 1 goto fail
"%PY%" "%~dp0tools\collect_licenses.py" "%~dp0dist\PinHarbor\licenses"
echo Built in dist\PinHarbor\PinHarbor.exe
echo IMPORTANT: Review licenses folder and NOTICE.md before redistributing the EXE.
echo IMPORTANT: EXE packaging has not been verified on an actual Windows machine here.
pause
exit /b 0
:fail
echo Could not build the executable.
pause
exit /b 1
