# UnifAI Guard — macOS production packaging

## Already done on Windows (repo prep)
- Agent split (`agent_*.py`) + proxy parts (`responses_inject.py` in MANIFEST)
- Version **1.6.24** synced (`VERSION.txt`, Info.plist fields, docs)
- `UnifAI_Guard.macos.spec` bundles `unifai_proxy_parts/` + agent hiddenimports
- `build_macos.sh` preflight checks modules/MANIFEST and syncs CFBundle version
- Employee install scripts + `INSTALL_MACOS.txt`
- Your Mac-only steps: `installer/MAC_ONLY_TODO.txt`

## What YOU must run on a Mac (Apple / Darwin only)

```bash
cd apps/browser-guard
./installer/build_macos.sh

# Sign + notarize (requires Developer ID)
export MACOS_APP_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="you@company.com"
export APPLE_TEAM_ID="TEAMID"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
# optional installer identity:
export MACOS_SIGN_IDENTITY="Developer ID Installer: Your Name (TEAMID)"

./installer/sign_and_notarize_macos.sh
# or unsigned pkg only:
./installer/build_pkg_macos.sh
```

Deploy `release/UnifAI_Guard_macOS.zip` and/or `release/UnifAI_Guard_*.pkg` to the server
`apps/browser-guard/release/` and redeploy.

## MDM
- Template: `installer/mdm/disable_private_relay.mobileconfig`
- Also push mitmproxy CA as a trust profile from your MDM for silent HTTPS intercept.

## Without Apple Developer ID
Gatekeeper will still warn; Install `.command` may need Right-click → Open.
That path is **pilot only**, not enterprise fleet production.
