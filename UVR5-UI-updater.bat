@echo off
setlocal enabledelayedexpansion

set REPO_URL=https://github.com/Eddycrack864/UVR5-UI
set "INSTALL_DIR=%cd%"
set "MINICONDA_DIR=%UserProfile%\Miniconda3"
set "ENV_DIR=%INSTALL_DIR%\env"
set "CONDA_EXE=%MINICONDA_DIR%\Scripts\conda.exe"
set "PIP_EXE=%MINICONDA_DIR%\Scripts\pip.exe"

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

if not exist "%CONDA_EXE%" (
    echo Error: Miniconda is not installed. Please run the installer first.
    pause
    exit /b 1
)

echo Updating Conda environment...
call "%MINICONDA_DIR%\condabin\conda.bat" activate "%ENV_DIR%" || goto :error
if errorlevel 1 (
    echo Error: Failed to activate conda environment.
    goto :error
)

echo Checking for updated dependencies...
%PIP_EXE% install -r "%INSTALL_DIR%\requirements.txt" || goto :error

call "%MINICONDA_DIR%\condabin\conda.bat" deactivate
if errorlevel 1 (
    echo Error: Failed to deactivate conda environment.
    goto :error
)
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
