@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo PinHarbor GitHub publisher - requires Git and GitHub CLI (gh)
echo You must authenticate first: gh auth login
echo.
set /p "REPO=Repository name [pinharbor]: "
if "%REPO%"=="" set "REPO=pinharbor"
set /p "VISIBILITY=Visibility: public or private [public]: "
if "%VISIBILITY%"=="" set "VISIBILITY=public"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0tools\github_publish.py" --repo "%REPO%" --visibility "%VISIBILITY%" --execute
) else (
  python "%~dp0tools\github_publish.py" --repo "%REPO%" --visibility "%VISIBILITY%" --execute
)
if errorlevel 1 (
  echo Upload was cancelled or failed. No Release was published.
) else (
  echo Sources uploaded. Check GitHub Actions, then review the release checklist.
)
pause
