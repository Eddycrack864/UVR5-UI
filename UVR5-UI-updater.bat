@echo off
setlocal enabledelayedexpansion

set REPO_URL=https://github.com/Eddycrack864/UVR5-UI
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

echo Code updated successfully.
echo.

if not exist "%PYTHON_EXE%" (
    echo Error: Python environment not found at "%ENV_DIR%". Please run the installer first.
    pause
    exit /b 1
)

echo Updating Conda environment...
echo Checking for updated dependencies...

"%PYTHON_EXE%" -m pip install --upgrade -r "%INSTALL_DIR%\requirements.txt" --no-warn-script-location || goto :error

echo Conda environment updated successfully.
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

