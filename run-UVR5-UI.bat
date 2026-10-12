@echo off
setlocal
title UVR5 UI
cd /d "%~dp0"

rem Extra arguments are passed through, e.g.: run-UVR5-UI.bat --share --listen-port 8080
if exist env\python.exe (
    env\python.exe app.py --open %*
) else (
    echo Searching for global python and dependencies...
    where python > nul 2>&1
    if errorlevel 1 (
        echo Error: Python not found. Please install UVR5 UI globally or run 'UVR5-UI-installer.bat' to set up the environment.
        pause
        exit /b 1
    )
    python app.py --open %*
)

if errorlevel 1 (
    echo.
    echo UVR5 UI exited with an error. Check the output above for details.
    pause
)
