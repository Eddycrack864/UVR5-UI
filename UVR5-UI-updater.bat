@echo off
setlocal enabledelayedexpansion
title UVR5 UI Updater

set "REPO_URL=https://github.com/Eddycrack864/UVR5-UI"
set "INSTALL_DIR=%cd%"
set "ENV_DIR=%INSTALL_DIR%\env"
set "PYTHON_EXE=%ENV_DIR%\python.exe"

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

rem Older versions kept user preferences in the tracked assets\config.json, which the reset below deletes.
if exist "assets\config.json" if not exist "user_data\config.json" (
    if not exist "user_data" mkdir "user_data"
    copy /y "assets\config.json" "user_data\config.json" > nul
    echo Your preferences were backed up to user_data\config.json
)

set "LOCAL_CHANGES="
for /f "delims=" %%L in ('git status --porcelain --untracked-files=no 2^>nul') do set "LOCAL_CHANGES=1"
if defined LOCAL_CHANGES (
    echo WARNING: These local changes to UVR5 UI files will be discarded by the update:
    git status --short --untracked-files=no
    echo Your settings in user_data\ and your models are not affected.
    echo Close this window to cancel, or
    pause
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

rem ===== Do not edit anything above this line. =====
rem Older updaters keep reading this file at the same byte position after "git reset" rewrites it,
rem so everything above must stay byte-identical. Put new update steps below.

echo Code updated successfully.
echo.

call "%INSTALL_DIR%\UVR5-UI-installer.bat" --update || goto :error

echo.
echo Update Complete!
echo UVR5 UI has been updated to the latest version.
pause
endlocal
exit /b 0

:error
echo An error occurred during the update process. Please check the output above for details.
pause
exit /b 1
