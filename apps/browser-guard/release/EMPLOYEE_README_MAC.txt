UnifAI Guard — macOS Employee Install Guide
==========================================

Company server: https://unifaiv2.dev-yp.com
(If IT gave you a different backend URL, use the config in this ZIP.)

INSTALL (turn ON)
-----------------
1. Unzip UnifAI_Guard_macOS.zip completely (keep all files in one folder)
2. Double-click Install_UnifAI_Guard.command
   - If macOS says it cannot be opened: Right-click → Open → Open
3. Allow any Keychain / admin prompts (needed to trust the Guard certificate)
4. Fully quit Safari / Chrome / Edge / Firefox (Cmd+Q), then reopen
5. Open a monitored AI website as usual

Health check: http://127.0.0.1:18085/
Logs: ~/Library/Application Support/UnifAI/Guard/unifai_guard.log

What it does
------------
- Connects to the company UnifAI backend for rules & target websites
- Runs a local proxy on this Mac only (127.0.0.1:8085)
- Sets system Auto Proxy URL (same idea as Windows PAC)
- Starts again at login (LaunchAgent) — like Windows autostart
- Does NOT need Docker or direct database access

TURN OFF / UNINSTALL
--------------------
1. Double-click Uninstall_UnifAI_Guard.command (in this ZIP, or ask IT)
2. Enter the company uninstall key from IT (Browser AI → Setup)
3. Finish — Guard stops, proxy/PAC cleared, app removed from /Applications
4. Fully quit and reopen browsers

Same key rule as Windows. Leave blank only if IT disabled the key requirement.

Admin remote uninstall from Browser AI also turns Guard OFF on the next heartbeat
(no employee key) — same as Windows.
