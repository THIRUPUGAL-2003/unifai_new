@echo off
echo ====================================================
echo Starting UnifAI ^& AI Guard Proxy Launcher
echo ====================================================

set "REPO_ROOT=%~dp0..\.."
set "PROXY_SCRIPT=%REPO_ROOT%\apps\browser-guard\proxy\browser_ai_proxy.py"

rem 1. Start mitmweb proxy server in background (Proxy: 8085, Web UI: 8083)
echo 1. Starting Proxy Interceptor...
start /b mitmweb -p 8085 --web-port 8083 -s "%PROXY_SCRIPT%" --set block_global=false

timeout /t 2 >nul

rem 2. Open Chrome with proxy configured
echo 2. Opening Chrome with Proxy...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --proxy-server="http://127.0.0.1:8085" --user-data-dir="%TEMP%\chrome_proxy" --ignore-certificate-errors "http://localhost:8081/workspace/browser-ai" "http://127.0.0.1:8083" "https://chatgpt.com"

echo ====================================================
echo Everything is running ^& opened in Chrome!
echo - Dashboard UI: http://localhost:8081/workspace/browser-ai
echo - Proxy Monitor UI: http://127.0.0.1:8083
echo - ChatGPT: https://chatgpt.com
echo ====================================================
