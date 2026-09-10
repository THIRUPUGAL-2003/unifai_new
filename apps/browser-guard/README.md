# UnifAI Guard (Browser AI desktop agent)

Desktop agent for Target Websites, Prompt Logs, and Guard Bot — **Windows + macOS**.

## Windows setup

| Package | How |
|---------|-----|
| `release/UnifAI_Guard_Setup.exe` | Inno installer (preferred for employees) |
| `release/UnifAI_Guard.exe` | Portable / latest PyInstaller build |

Build on Windows: `installer\build_installer.bat`

See `release/INSTALL_WINDOWS.txt`.

**Uninstall / turn OFF:** Windows Settings → Apps → UnifAI Guard → Uninstall (company uninstall key).

## macOS setup

| Package | How |
|---------|-----|
| `release/UnifAI_Guard_macOS.zip` | `.app` + Install / Uninstall `.command` scripts |
| `release/UnifAI_Guard.app` | PyInstaller app bundle (after build) |

Build **on a Mac**:

```bash
cd apps/browser-guard
./installer/build_macos.sh
```

Then copy `release/UnifAI_Guard_macOS.zip` (and docs) onto the UnifAI server under `apps/browser-guard/release/` and redeploy so **Download Setup ZIP** includes it.

See:

- `release/INSTALL_MACOS.txt` — install / turn ON
- `release/UNINSTALL_MACOS.txt` — turn OFF / uninstall
- `installer/EMPLOYEE_README_MAC.txt` — employee one-pager

**Uninstall / turn OFF:** double-click `Uninstall_UnifAI_Guard.command` (same company uninstall key as Windows).

## Deploy to server

Copy Windows and/or macOS artifacts into `apps/browser-guard/release/` and redeploy so **Browser AI → Setup → Download Setup ZIP** ships them.
