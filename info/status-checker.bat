@echo off
title UVR5 UI Status

cd /d "%~dp0"

if exist "..\env\python.exe" (
    ..\env\python.exe ..\env\Scripts\audio-separator.exe -e
) else (
    echo "Searching for global python..."
    where python > nul 2>&1
    if %errorlevel% equ 0 (
        python ..\env\Scripts\audio-separator.exe -e
    ) else (
        echo "Error: Python not found."
    )
)

echo.
pause