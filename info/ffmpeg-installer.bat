@echo off
title FFmpeg Installer by Eddycrack864

NET SESSION >nul 2>&1
IF %ERRORLEVEL% EQU 0 (

  echo Running as Administrator, continuing...
  
  echo Downloading FFmpeg...
  curl -Lo C:\ffmpeg.zip --ssl-revoke-best-effort https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
  echo Done!
  echo Unzipping...
  powershell -Command "Expand-Archive -LiteralPath C:\ffmpeg.zip C:\ffmpeg"
  echo Done!
  echo Cleaning up...
  del C:\ffmpeg.zip
  echo Done!
  echo Setting environment variable...
  setx PATH "%PATH%;C:/ffmpeg/ffmpeg-master-latest-win64-gpl/bin"
  echo Done!
  echo Installation finished!
  pause

) ELSE (
  echo ERROR: This script must be run as an Administrator.
  echo Please right-click the script and select "Run as administrator".
  pause
  EXIT /B 1
)