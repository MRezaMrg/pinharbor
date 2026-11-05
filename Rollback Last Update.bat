@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\PinterestBoardStudio\venv\Scripts\python.exe"
set "PYOPTS="
if exist "%PY%" goto start
where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py"
  set "PYOPTS=-3"
  goto start
)
set "PY=python"
:start
echo Close Pinterest Board Studio before a rollback.
if "%~1"=="" (
  "%PY%" %PYOPTS% "%~dp0upgrade_existing.py" --rollback --target "%~dp0"
) else (
  "%PY%" %PYOPTS% "%~dp0upgrade_existing.py" --rollback --target "%~1"
)
if errorlevel 1 echo Rollback failed: see message above.
pause
