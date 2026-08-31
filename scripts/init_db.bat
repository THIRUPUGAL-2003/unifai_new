@echo off
echo ====================================================
echo UnifAI DB Init - creates all tables in unifai_test
echo Uses credentials from config.json
echo ====================================================

cd /d "%~dp0.."
if not exist "scripts\db-init\db-init.exe" (
  echo Building db-init tool...
  cd scripts\db-init
  set CGO_ENABLED=0
  set GOWORK=off
  go build -o db-init.exe .
  if errorlevel 1 exit /b 1
  cd ..\..
)

scripts\db-init\db-init.exe -config "%~dp0..\config.json"
if errorlevel 1 (
  echo.
  echo FAILED - if password auth failed, run setup_db_user.sql in pgAdmin first.
  exit /b 1
)

echo.
echo SUCCESS - refresh Tables in pgAdmin for Unifai_test
pause
