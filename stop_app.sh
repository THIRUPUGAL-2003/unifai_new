#!/bin/bash

echo "===================================================="
echo "🛑 Stopping UnifAI & AI Guard Proxy"
echo "===================================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Disable Windows user proxy + WinHTTP
echo "1. Disabling system proxy..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
\$path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Remove-ItemProperty -Path \$path -Name AutoConfigURL -ErrorAction SilentlyContinue
Set-ItemProperty -Path \$path -Name ProxyEnable -Value 0
Set-ItemProperty -Path \$path -Name ProxyServer -Value ''
Set-ItemProperty -Path \$path -Name ProxyOverride -Value ''
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinInetClear {
  [DllImport(\"wininet.dll\", SetLastError=true)]
  public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
}
'@
[void][WinInetClear]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0)
[void][WinInetClear]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0)
netsh winhttp reset proxy | Out-Null
Write-Host '   Proxy disabled'
" 2>/dev/null || echo "   Warning: could not clear proxy settings"

# 2. Stop mitmweb / mitmdump
echo "2. Stopping mitmproxy..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
Get-CimInstance Win32_Process |
  Where-Object { \$_.CommandLine -match 'mitmweb|mitmdump|ai_guard_proxy' } |
  ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }
" 2>/dev/null

if command -v netstat >/dev/null 2>&1; then
  for port in 8085 8081; do
    pids=$(netstat -ano 2>/dev/null | grep ":$port " | grep LISTENING | awk '{print $NF}' | sort -u)
    for pid in $pids; do
      [[ "$pid" =~ ^[0-9]+$ ]] && taskkill //PID "$pid" //F >/dev/null 2>&1 || true
    done
  done
fi

echo "===================================================="
echo "✅ Guard stopped. Quit & reopen browsers if needed."
echo "===================================================="
