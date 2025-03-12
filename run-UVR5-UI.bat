@echo off
setlocal
title UVR5 UI

if exist env (
    env\python.exe app.py --open
) else (
    echo Searching for global python and dependencies...
    where python > nul 2>&1
    if %errorlevel% equ 0 (
        python app.py --open
    ) else (
        echo Error: Python not found. Please install UVR5 UI globally or run 'UVR5-UI-installer.bat' to set up the environment.
        pause
        exit /b 1
    )
)

echo.
pause