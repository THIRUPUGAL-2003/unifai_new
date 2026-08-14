#!/bin/bash

echo "===================================================="
echo "🚀 Starting UnifAI & AI Guard (system-wide)"
echo "===================================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 0. Check if mitmproxy/mitmweb is installed
if ! command -v mitmweb &> /dev/null; then
    echo "❌ Error: mitmweb is not installed or not in PATH."
    echo "   Please install mitmproxy (e.g. pip install mitmproxy or winget install mitmproxy)"
    exit 1
fi

WIN_USERPROFILE=$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("UserProfile")' | tr -d '\r')
MITM_CERT_CER="${WIN_USERPROFILE}\\.mitmproxy\\mitmproxy-ca-cert.cer"

# 1. Trust mitmproxy CA in Current User store (required for HTTPS MITM)
echo "1. Ensuring mitmproxy CA is trusted (Current User)..."
if [[ -f "$HOME/.mitmproxy/mitmproxy-ca-cert.cer" ]]; then
    certutil.exe -user -addstore Root "$MITM_CERT_CER" >/dev/null 2>&1 || true
    echo "   CA trust OK (Chrome / Edge / Brave)"
else
    echo "   ⚠️  CA not found yet — will be created when mitmweb starts."
    echo "   Re-run ./start_app.sh once after first start if HTTPS sites warn."
fi

# 2. Start mitmweb
echo "2. Starting Proxy Interceptor (Proxy Port: 8085, Web UI Port: 8081)..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
Get-CimInstance Win32_Process |
  Where-Object { \$_.CommandLine -match 'mitmweb|mitmdump' } |
  ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }
" 2>/dev/null
sleep 1

mitmweb -p 8085 --web-host 127.0.0.1 --web-port 8081 \
  -s "$SCRIPT_DIR/scripts/browser_ai_proxy.py" \
  --set block_global=false \
  --set connection_strategy=lazy \
  > "$SCRIPT_DIR/mitmweb.log" 2>&1 &
PROXY_PID=$!
echo "   Proxy running (PID: $PROXY_PID)"
sleep 3

# Re-try CA install after mitmweb may have created ~/.mitmproxy
if [[ -f "$HOME/.mitmproxy/mitmproxy-ca-cert.cer" ]]; then
    certutil.exe -user -addstore Root "$MITM_CERT_CER" >/dev/null 2>&1 || true
fi

# 3. Force Windows SYSTEM proxy (not file:// PAC — Chrome ignores file PAC)
#    Localhost bypass so Dashboard / UnifAI on :8080 keep working.
echo "3. Enabling Windows system proxy → 127.0.0.1:8085 ..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
\$path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Remove-ItemProperty -Path \$path -Name AutoConfigURL -ErrorAction SilentlyContinue
Set-ItemProperty -Path \$path -Name ProxyEnable -Value 1
Set-ItemProperty -Path \$path -Name ProxyServer -Value '127.0.0.1:8085'
Set-ItemProperty -Path \$path -Name ProxyOverride -Value 'localhost;127.0.0.1;*.local;<local>'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinInetFlush {
  [DllImport(\"wininet.dll\", SetLastError=true)]
  public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
}
'@
[void][WinInetFlush]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0)
[void][WinInetFlush]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0)
# WinHTTP (some apps / services)
netsh winhttp import proxy source=ie | Out-Null
Write-Host '   ProxyEnable=1 ProxyServer=127.0.0.1:8085'
"

# 4. Verify proxy accepts CONNECT (otherwise guard cannot see HTTPS)
echo "4. Verifying proxy path..."
VERIFY=$(powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
try {
  \$proxy = New-Object System.Net.WebProxy('http://127.0.0.1:8085', \$true)
  \$wc = New-Object System.Net.WebClient
  \$wc.Proxy = \$proxy
  # Hit mitm.it — only reachable meaningfully via mitmproxy MITM page
  \$null = \$wc.DownloadString('http://mitm.it')
  'OK'
} catch {
  'FAIL: ' + \$_.Exception.Message
}
" | tr -d '\r')
echo "   Proxy check: $VERIFY"

# 5. Open dashboard in default browser (bypasses proxy via ProxyOverride)
echo "5. Opening Dashboard & Proxy Monitor..."
cmd.exe //c start "" "http://localhost:8080/workspace/browser-ai" >/dev/null 2>&1 &
cmd.exe //c start "" "http://127.0.0.1:8081" >/dev/null 2>&1 &

echo "===================================================="
echo "✅ AI Guard is ON for this laptop"
echo "   Dashboard: http://localhost:8080/workspace/browser-ai"
echo "   Proxy UI:  http://127.0.0.1:8081  ← must show flows when you browse"
echo ""
echo "⚠️  REQUIRED: Fully quit Chrome/Edge (all windows), then reopen."
echo "   Already-open browsers keep the old (no-proxy) settings."
echo ""
echo "   Test: open chatgpt.com, send a prompt — Proxy UI should"
echo "   show chatgpt.com flows, and Prompt Logs should increase."
echo ""
echo "   When done:  ./stop_app.sh"
echo "===================================================="
