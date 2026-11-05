@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo =============================================
echo PinHarbor - GitHub source sync (safe mode)
echo =============================================
echo This tool publishes curated files only.
echo It untracks known obsolete docs but never deletes them from disk.
echo It does NOT publish a release or executable.
echo.
where gh >nul 2>nul
if errorlevel 1 (
    echo ERROR: GitHub CLI not found. See https://cli.github.com/
    pause
    exit /b 1
)
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git not found. See https://git-scm.com/
    pause
    exit /b 1
)
echo Connected GitHub account:
gh auth status
if errorlevel 1 (
    echo Login first: gh auth login
    pause
    exit /b 1
)
echo.
set /p "REPO=Repository [pinharbor]: "
if "%REPO%"=="" set "REPO=pinharbor"
set /p "VISIBILITY=Visibility for NEW repositories [public]: "
if "%VISIBILITY%"=="" set "VISIBILITY=public"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0tools\github_publish.py" --repo "%REPO%" --visibility "%VISIBILITY%" --execute
) else (
    python "%~dp0tools\github_publish.py" --repo "%REPO%" --visibility "%VISIBILITY%" --execute
)
if errorlevel 1 (
    echo Upload cancelled or failed. Read the error above.
) else (
    echo Source sync complete. Check the main branch and Actions tab on GitHub.
)
pause
