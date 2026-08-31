
UnifAI Guard — Company Release Notes
====================================

Employee file to distribute:
  release\UnifAI_Guard_Setup.exe

Configured backend:
  https://unifaiv2.dev-yp.com

BEFORE company rollout — verify server APIs return JSON (not HTML):
  https://unifaiv2.dev-yp.com/health
  https://unifaiv2.dev-yp.com/api/browser-ai/targets
  https://unifaiv2.dev-yp.com/api/browser-ai/rules
  https://unifaiv2.dev-yp.com/api/browser-ai/proxy.pac?proxy=127.0.0.1:8085

If /api/browser-ai/* returns the UnifAI web page HTML, deploy the latest
backend that includes Browser AI routes, then re-test.

Rebuild installer anytime:
  installer\build_installer.bat

Packaging structure
-------------------
dist\UnifAI_Guard.exe            Raw standalone agent build
dist\unifai_guard_config.json    Raw agent config
installer\UnifAI_Guard.iss       Inno Setup source
installer\build_installer.bat    Rebuilds staging + setup EXE
installer\EMPLOYEE_README.txt    Included in installer package
installer\staging\               Temporary/generated build staging
release\UnifAI_Guard_Setup.exe   Final employee installer
