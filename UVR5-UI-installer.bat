@echo off
setlocal enabledelayedexpansion
title UVR5 UI Installer

rem Versions shared by fresh installs and updates (UVR5-UI-updater.bat runs this script with --update)
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py313_26.7.1-1-Windows-x86_64.exe"
set "PYTHON_VERSION=3.13.16"
set "PIP_VERSION=26.2.1"
set "TORCH_VERSION=2.7.1"
set "TORCHVISION_VERSION=0.22.1"
set "TORCH_INDEX=https://download.pytorch.org/whl/cu128"

set "INSTALL_DIR=%cd%"
set "MINICONDA_DIR=%UserProfile%\Miniconda3"
set "ENV_DIR=%INSTALL_DIR%\env"
set "OLD_ENV_DIR=%INSTALL_DIR%\env_old"
set "CONDA_BAT=%MINICONDA_DIR%\condabin\conda.bat"
set "CONDA_EXE=%MINICONDA_DIR%\Scripts\conda.exe"
set "PYTHON_EXE=%ENV_DIR%\python.exe"

if /i "%~1"=="--update" goto :update

echo Welcome to the UVR5 UI Installer!
echo.

call :privilege_checking || exit /b 1
call :path_checking
call :install_miniconda || goto :error
call :build_env || goto :error

echo UVR5 UI has been installed successfully!
echo To start UVR5 UI, please run 'run-UVR5-UI.bat'
echo.
pause
exit /b 0

:privilege_checking
NET SESSION >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ERROR: This script must not be run with Administrator privileges, close this window and run it without Administrator privileges
    pause
    exit /b 1
)

echo The script is running without Administrator privileges, continuing...
echo.
exit /b 0

:path_checking
if not "%INSTALL_DIR%"=="%INSTALL_DIR: =%" (
    echo WARNING: The installation path contains spaces:
    echo   !INSTALL_DIR!
    echo Conda environments in paths with spaces or special characters often fail to install.
    echo Consider moving UVR5 UI to a simple path such as C:\UVR5-UI
    echo Close this window to cancel, or
    pause
    echo.
)
exit /b 0

:install_miniconda
if exist "%CONDA_EXE%" (
    echo Miniconda already installed. Skipping installation...
    exit /b 0
)

echo Miniconda not found. Starting download and installation...
powershell -Command "& {Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile 'miniconda.exe'}"
if not exist "miniconda.exe" (
    echo Download failed. Please check your internet connection and try again
    exit /b 1
)

start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%MINICONDA_DIR%
if errorlevel 1 (
    echo Miniconda installation failed
    exit /b 1
)

del miniconda.exe
echo Miniconda installation complete
echo.
exit /b 0

rem Creates env\ from scratch: Python from conda-forge (no Anaconda Terms of Service prompt), torch, then requirements.
:build_env
echo Creating Conda environment with Python %PYTHON_VERSION%...
call "%CONDA_BAT%" create --no-shortcuts -y -k --override-channels -c conda-forge --prefix "%ENV_DIR%" python=%PYTHON_VERSION%
if errorlevel 1 exit /b 1
if not exist "%PYTHON_EXE%" exit /b 1
echo Conda environment created successfully
echo.

echo Installing pip %PIP_VERSION%...
"%PYTHON_EXE%" -m pip install "pip==%PIP_VERSION%" --no-warn-script-location || exit /b 1
echo.

call :install_torch || exit /b 1
call :install_requirements || exit /b 1
call :verify_env || exit /b 1
echo Dependencies installation complete
echo.
exit /b 0

:install_torch
echo Installing torch %TORCH_VERSION%...
"%PYTHON_EXE%" -m pip install "torch==%TORCH_VERSION%" "torchvision==%TORCHVISION_VERSION%" --index-url %TORCH_INDEX% --no-warn-script-location || exit /b 1
echo.
exit /b 0

:install_requirements
echo Installing dependencies...
"%PYTHON_EXE%" -m pip install --upgrade -r "%INSTALL_DIR%\requirements.txt" --no-warn-script-location || exit /b 1
echo.
exit /b 0

:verify_env
"%PYTHON_EXE%" -c "import audio_separator.separator, gradio, torch" || (
    echo The Python environment is incomplete: some dependencies could not be imported
    exit /b 1
)
exit /b 0

rem ---------------------------------------------------------------------------
rem Update mode, called by UVR5-UI-updater.bat after the code has been updated.
rem ---------------------------------------------------------------------------
:update
call :recover_interrupted_rebuild || exit /b 1

if not exist "%PYTHON_EXE%" (
    echo Error: Python environment not found at "%ENV_DIR%". Please run the installer first.
    exit /b 1
)

"%PYTHON_EXE%" -c "import sys; sys.exit(sys.version_info[:2] < tuple(map(int, sys.argv[1].split('.')[:2])))" %PYTHON_VERSION%
if errorlevel 1 (
    call :offer_rebuild
    exit /b !errorlevel!
)

echo Checking for updated dependencies...
call :install_torch || exit /b 1
call :install_requirements || exit /b 1
echo Python environment updated successfully.
exit /b 0

:offer_rebuild
echo.
echo UVR5 UI now uses Python %PYTHON_VERSION%, but your Python environment is older.
echo It can be rebuilt automatically: this downloads about 3 GB and needs about 6 GB of free disk space.
echo If anything goes wrong, your current environment is restored.
echo.
choice /c YN /m "Rebuild the Python environment now"
if errorlevel 2 (
    echo.
    echo Skipping the rebuild. Updating the dependencies of your current environment...
    call :install_requirements || exit /b 1
    echo You can rebuild the environment later by running the updater again.
    exit /b 0
)

rem Precompiled versions ship env\ without Miniconda
call :install_miniconda || exit /b 1
if exist "%OLD_ENV_DIR%" rmdir /s /q "%OLD_ENV_DIR%"
move "%ENV_DIR%" "%OLD_ENV_DIR%" > nul 2>&1
if errorlevel 1 (
    echo Error: Could not move the current environment. Close UVR5 UI and any program using it, then try again.
    exit /b 1
)

call :build_env
if errorlevel 1 (
    echo.
    echo The rebuild failed. Restoring your previous environment...
    call :restore_old_env
    exit /b 1
)

echo Removing the previous environment...
rmdir /s /q "%OLD_ENV_DIR%"
echo Python environment rebuilt successfully.
exit /b 0

rem env_old\ only exists if a rebuild was interrupted: keep env\ if it is complete, otherwise bring env_old\ back.
:recover_interrupted_rebuild
if not exist "%OLD_ENV_DIR%" exit /b 0
call :verify_env > nul 2>&1
if not errorlevel 1 (
    rmdir /s /q "%OLD_ENV_DIR%"
    exit /b 0
)
echo A previous environment rebuild was interrupted. Restoring your previous environment...
call :restore_old_env
exit /b

:restore_old_env
if exist "%ENV_DIR%" rmdir /s /q "%ENV_DIR%"
move "%OLD_ENV_DIR%" "%ENV_DIR%" > nul 2>&1
if errorlevel 1 (
    echo Error: Could not restore "%OLD_ENV_DIR%". Rename it to "env" manually.
    exit /b 1
)
echo Previous environment restored.
exit /b 0

:error
echo An error occurred during installation. Please check the output above for details
pause
exit /b 1
