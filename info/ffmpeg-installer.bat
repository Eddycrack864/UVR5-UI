@echo off
setlocal
title FFmpeg Installer by Eddycrack864

rem Installs FFmpeg for the current user (no Administrator rights needed) and adds it to the user PATH.
rem Alternative: winget install Gyan.FFmpeg

where ffmpeg > nul 2>&1
if not errorlevel 1 (
    echo FFmpeg is already installed:
    where ffmpeg
    pause
    exit /b 0
)

set "FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
set "FFMPEG_ROOT=%LOCALAPPDATA%\ffmpeg"
set "FFMPEG_BIN=%FFMPEG_ROOT%\ffmpeg-master-latest-win64-gpl\bin"
set "FFMPEG_ZIP=%TEMP%\ffmpeg.zip"

echo Downloading FFmpeg...
curl -Lo "%FFMPEG_ZIP%" --ssl-revoke-best-effort "%FFMPEG_URL%"
if errorlevel 1 goto :error
echo Done!

echo Unzipping...
powershell -NoProfile -Command "Expand-Archive -LiteralPath $env:FFMPEG_ZIP -DestinationPath $env:FFMPEG_ROOT -Force"
if errorlevel 1 goto :error
del "%FFMPEG_ZIP%"
echo Done!

echo Adding FFmpeg to your user PATH...
rem Only the *user* PATH is read and written, so the system PATH is never copied or truncated (unlike setx).
powershell -NoProfile -Command ^
  "$bin = $env:FFMPEG_BIN;" ^
  "$path = [Environment]::GetEnvironmentVariable('Path', 'User');" ^
  "$entries = @($path -split ';' | Where-Object { $_ });" ^
  "if ($entries -notcontains $bin) { [Environment]::SetEnvironmentVariable('Path', (($entries + $bin) -join ';'), 'User') }"
if errorlevel 1 goto :error
echo Done!

echo Installation finished! Close and reopen your terminal for the PATH change to take effect.
pause
exit /b 0

:error
echo An error occurred while installing FFmpeg. Please check the output above for details.
if exist "%FFMPEG_ZIP%" del "%FFMPEG_ZIP%"
pause
exit /b 1
