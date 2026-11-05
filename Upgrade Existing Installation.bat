@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\PinterestBoardStudio\venv\Scripts\python.exe"
set "PYOPTS="
if exist "%PY%" goto run
where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py"
  set "PYOPTS=-3"
  goto run
)
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ not found. Install Python or run the previous app first.
  pause
  exit /b 1
)
set "PY=python"
:run
echo.
echo PinHarbor - Safe Update
 echo Close PinHarbor before updating.
echo Select the folder containing your OLD Run on Windows.bat.
echo The program will back up old program files before replacing them.
echo Downloaded media and archive will not be deleted.
echo.
if "%~1"=="" (
  "%PY%" %PYOPTS% "%~dp0upgrade_existing.py"
) else (
  "%PY%" %PYOPTS% "%~dp0upgrade_existing.py" --target "%~1"
)
if errorlevel 1 goto failed
echo.
echo Update completed. Open Run on Windows.bat from the OLD installation folder.
pause
exit /b 0
:failed
echo Upgrade was not completed. Read the error above.
pause
exit /b 1
