@echo off
setlocal EnableExtensions
title Build UnifAI Guard Enterprise Installer 1.5.8

cd /d "%~dp0.."

echo ============================================================
echo  Preflight: config + sources
echo ============================================================
if not exist scripts\unifai_agent.py (
  echo Missing scripts\unifai_agent.py
  exit /b 1
)
if not exist scripts\browser_ai_proxy.py (
  echo Missing scripts\browser_ai_proxy.py
  exit /b 1
)
if not exist unifai_guard_config.json (
  echo Missing unifai_guard_config.json
  exit /b 1
)

findstr /C:"unifaiv2.dev-yp.com" unifai_guard_config.json >nul
if errorlevel 1 (
  echo WARNING: backend_url may not be production unifaiv2.dev-yp.com — check unifai_guard_config.json
)

echo.
echo ============================================================
echo  1) Building UnifAI_Guard.exe  (embeds latest browser_ai_proxy.py)
echo ============================================================
python scripts\build_agent.py
if errorlevel 1 (
  echo EXE build failed.
  exit /b 1
)

echo.
echo ============================================================
echo  2) Preparing installer staging
echo ============================================================
if not exist installer\staging mkdir installer\staging
if not exist release mkdir release

copy /Y dist\UnifAI_Guard.exe installer\staging\UnifAI_Guard.exe >nul
copy /Y unifai_guard_config.json installer\staging\unifai_guard_config.json >nul
if exist installer\EMPLOYEE_README.txt copy /Y installer\EMPLOYEE_README.txt installer\staging\EMPLOYEE_README.txt >nul

echo.
echo ============================================================
echo  3) Compiling Setup EXE (Inno Setup)
echo ============================================================
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 not found. Staging folder is ready at installer\staging
  echo Install Inno Setup, then re-run this script.
  echo Raw EXE: dist\UnifAI_Guard.exe
  exit /b 1
)

%ISCC% installer\UnifAI_Guard.iss
if errorlevel 1 (
  echo Inno compile failed.
  exit /b 1
)

echo.
echo ============================================================
echo  SUCCESS — UnifAI Guard 1.5.8
echo  Employee installer:
echo    release\UnifAI_Guard_Setup.exe
echo  Backend:
echo    https://unifaiv2.dev-yp.com
echo ============================================================
dir release\UnifAI_Guard_Setup.exe
endlocal
