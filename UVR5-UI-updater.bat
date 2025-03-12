@echo off
setlocal

set REPO_URL=https://github.com/Eddycrack864/UVR5-UI

where git > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Git is not installed. Please install Git and try again.
    pause
    exit /b 1
)

if not exist .git (
    git init
    git remote add origin %REPO_URL%
)

git fetch origin
if %errorlevel% neq 0 (
    echo Error: Failed to fetch updates. Check your internet connection or Git configuration.
    pause
    exit /b 1
)

git reset --hard origin/main
if %errorlevel% neq 0 (
    echo Error: Failed to reset repository. Check your Git configuration or repository status.
    pause
    exit /b 1
)

echo Update Complete!
echo.
pause
endlocal