UnifAI Guard — Employee Install Guide
=====================================

Company server: https://unifaiv2.dev-yp.com
(If IT gave you a different backend URL, use the config in this ZIP.)

1. Run UnifAI_Guard_Setup.exe
2. Keep "Start automatically at Windows login" checked
3. Finish — Guard starts in background (no black terminal)
4. Open ChatGPT / monitored AI sites as usual
5. If sites show certificate warnings, tell IT — CA trust must succeed
   (status file: %LOCALAPPDATA%\UnifAI\Guard\ca_install_status.txt)

What it does
------------
- Connects to the company UnifAI backend for rules & target websites
- Runs a local proxy on this PC only (127.0.0.1:8085)
- Does NOT need the Docker proxy container or direct database access

Logs (if IT asks)
-----------------
%LOCALAPPDATA%\UnifAI\Guard\unifai_guard.log

Uninstall
---------
Windows Settings > Apps > UnifAI Guard > Uninstall
(or Start Menu > UnifAI Guard > Uninstall)

When prompted, enter the company uninstall key from IT
(Browser AI → Setup). Leave blank only if IT disabled the key requirement.
