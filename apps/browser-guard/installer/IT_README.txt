
UnifAI Guard — Company Release Notes
====================================

Employee files to distribute:
  Windows: release\UnifAI_Guard_Setup.exe
  macOS:   release\UnifAI_Guard_macOS.zip

Configured backend:
  https://unifaiv2.dev-yp.com

Hybrid (laptop + network, ONE Browser AI dashboard):
  See HYBRID_DEPLOY.txt in this folder (parent apps\browser-guard).
  Laptop EXE/.app and docker network proxy share the same rules + Prompt Logs.

BEFORE company rollout — verify server APIs return JSON (not HTML):
  https://unifaiv2.dev-yp.com/health
  https://unifaiv2.dev-yp.com/api/browser-ai/targets
  https://unifaiv2.dev-yp.com/api/browser-ai/rules
  https://unifaiv2.dev-yp.com/api/browser-ai/proxy.pac?proxy=127.0.0.1:8085
  Network PAC example:
  https://unifaiv2.dev-yp.com/api/browser-ai/pac?proxy=proxy.company.local:8082

If /api/browser-ai/* returns the UnifAI web page HTML, deploy the latest
backend that includes Browser AI routes, then re-test.

Rebuild installers:
  Windows: installer\build_installer.bat
  macOS:   ./installer/build_macos.sh   (must run on a Mac, Python 3.11+)

Uninstall / turn OFF
--------------------
  Windows: Settings → Apps → UnifAI Guard → Uninstall (company key)
  macOS:   Uninstall_UnifAI_Guard.command (same company key)

Packaging structure
-------------------
dist\UnifAI_Guard.exe            Raw standalone Windows agent build
dist\UnifAI_Guard.app            Raw macOS app (after Mac build)
installer\UnifAI_Guard.iss       Inno Setup source
installer\build_installer.bat    Rebuilds Windows staging + setup EXE
installer\build_macos.sh         Rebuilds Mac .app + UnifAI_Guard_macOS.zip
installer\EMPLOYEE_README.txt    Windows employee readme
installer\EMPLOYEE_README_MAC.txt Mac employee readme
installer\staging\               Temporary/generated Windows build staging
release\UnifAI_Guard_Setup.exe   Final Windows employee installer
release\UnifAI_Guard_macOS.zip   Final Mac employee package
