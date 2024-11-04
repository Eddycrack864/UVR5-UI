@echo off
setlocal
title UVR5 UI

if not exist env (
    echo Please run 'UVR5-UI-installer.bat' first to set up the environment
    pause
    exit /b 1
)

env\python.exe app.py
echo.
pause