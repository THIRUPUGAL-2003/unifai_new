@echo off
title Install UnifAI Guard Autostart
cd /d "%~dp0"

if not exist "%~dp0UnifAI_Guard.exe" (
  echo ERROR: UnifAI_Guard.exe not found in this folder.
  pause
  exit /b 1
)

echo ====================================================
echo  Installing UnifAI Guard to start at Windows login
echo  (Settings ^> Apps ^> Startup / permanent background)
echo ====================================================

REM Register in current-user Startup (HKCU Run) — required so proxy settings apply to THIS user
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v UnifAI_Guard /t REG_SZ /d "\"%~dp0UnifAI_Guard.exe\"" /f

REM Start now without waiting for reboot
start "" "%~dp0UnifAI_Guard.exe"

echo.
echo DONE.
echo  - Starts automatically every login
echo  - No terminal window (logs: unifai_guard.log in this folder)
echo  - Check: Windows Settings ^> Apps ^> Startup ^> UnifAI_Guard = On
echo  - Stop later: run Uninstall_Autostart.bat
echo.
pause
