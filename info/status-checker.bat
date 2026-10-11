@echo off
title UVR5 UI Status

cd /d "%~dp0"

if exist "..\env\Scripts\audio-separator.exe" (
    ..\env\Scripts\audio-separator.exe -e
) else (
    echo Searching for a global audio-separator installation...
    where audio-separator > nul 2>&1
    if errorlevel 1 (
        echo Error: audio-separator not found. Run 'UVR5-UI-installer.bat' first.
    ) else (
        audio-separator -e
    )
)

echo.
pause
