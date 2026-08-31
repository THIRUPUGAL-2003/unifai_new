@echo off
title Uninstall UnifAI Guard Autostart
cd /d "%~dp0"

echo Removing UnifAI Guard from Windows Startup...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v UnifAI_Guard /f >nul 2>&1

echo Stopping running Guard process...
taskkill /F /IM UnifAI_Guard.exe >nul 2>&1

echo DONE. Guard will not start at next login.
pause
