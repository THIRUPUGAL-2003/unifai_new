@echo off
setlocal EnableExtensions
title Update UnifAI Guard to 1.6.13
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting Administrator...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b 0
)

set "SRC=%~dp0UnifAI_Guard.exe"
set "DST=%LOCALAPPDATA%\Programs\UnifAI\Guard\UnifAI_Guard.exe"
if not exist "%SRC%" (
  echo Missing UnifAI_Guard.exe next to this script.
  pause
  exit /b 1
)

echo Stopping UnifAI_Guard...
taskkill /F /IM UnifAI_Guard.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if not exist "%LOCALAPPDATA%\Programs\UnifAI\Guard" mkdir "%LOCALAPPDATA%\Programs\UnifAI\Guard"
copy /Y "%SRC%" "%DST%"
if errorlevel 1 (
  echo Copy failed. Close Guard from tray and retry.
  pause
  exit /b 1
)

echo Starting new Guard...
start "" "%DST%"
timeout /t 5 /nobreak >nul
echo Open http://127.0.0.1:18085/ and confirm version 1.6.13
start "" "http://127.0.0.1:18085/"
pause
