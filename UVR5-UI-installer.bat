@echo off
setlocal enabledelayedexpansion
title UVR5 UI Installer

echo Welcome to the UVR5 UI Installer!
echo.

set "INSTALL_DIR=%cd%"
set "MINICONDA_DIR=%UserProfile%\Miniconda3"
set "ENV_DIR=%INSTALL_DIR%\env"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Windows-x86_64.exe"
set "CONDA_EXE=%MINICONDA_DIR%\Scripts\conda.exe"

call :privilege_checking || exit /b 1
call :path_checking
call :install_miniconda || goto :error
call :create_conda_env || goto :error
call :install_dependencies || goto :error

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

:create_conda_env
echo Creating Conda environment...
call "%MINICONDA_DIR%\_conda.exe" create --no-shortcuts -y -k --prefix "%ENV_DIR%" python=3.10.12
if errorlevel 1 exit /b 1
echo Conda environment created successfully
echo.

if exist "%ENV_DIR%\python.exe" (
    echo Installing specific pip version...
    "%ENV_DIR%\python.exe" -m pip install "pip==24.1.2"
    if errorlevel 1 exit /b 1
    echo Pip installation complete
    echo.
)
exit /b 0

:install_dependencies
echo Installing dependencies...
call "%MINICONDA_DIR%\condabin\conda.bat" activate "%ENV_DIR%" || exit /b 1
pip install -r "%INSTALL_DIR%\requirements.txt" || exit /b 1
pip uninstall torch torchvision -y || exit /b 1
pip install torch==2.7.0 torchvision --upgrade --index-url https://download.pytorch.org/whl/cu128 || exit /b 1
call "%MINICONDA_DIR%\condabin\conda.bat" deactivate
echo Dependencies installation complete
echo.
exit /b 0

:error
echo An error occurred during installation. Please check the output above for details
pause
exit /b 1
