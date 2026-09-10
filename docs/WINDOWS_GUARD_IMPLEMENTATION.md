# UnifAI — Windows Guard Implementation Guide

**Version:** 1.0  
**Date:** 10 Sep 2026  
**Guard release:** see `apps/browser-guard/release/VERSION.txt` (current: **1.6.21**)  
**Audience:** Company IT · Desktop support · Employees  
**Scope:** Install, upgrade, uninstall, verify Windows Guard  

Related docs:
- Server → `SERVER_IMPLEMENTATION.md`
- Config keys → `CONFIGURATION.md`

---

## 1. Overview

**UnifAI Guard** is a Windows desktop agent. It:

1. Connects to the company UnifAI server (`backend_url`)
2. Runs a **local proxy** on this PC only: `127.0.0.1:8085`
3. Applies company **Target websites** and **rules**
4. Sends prompt/activity logs to Browser AI → **Prompt Logs**
5. Appears in Browser AI → **Guard Agents** as type **Laptop** (`endpoint`)

| Item | Value |
|------|--------|
| Preferred package | `UnifAI_Guard_Setup.exe` |
| Portable package | `UnifAI_Guard.exe` |
| Install folder | `%LOCALAPPDATA%\Programs\UnifAI\Guard\` |
| Runtime data / logs | `%LOCALAPPDATA%\UnifAI\Guard\` |
| Status page | `http://127.0.0.1:18085/` |
| Local proxy | `127.0.0.1:8085` |
| Log file | `%LOCALAPPDATA%\UnifAI\Guard\unifai_guard.log` |
| CA status | `%LOCALAPPDATA%\UnifAI\Guard\ca_install_status.txt` |

Guard does **not** need Docker on the laptop and does **not** talk to the database directly.

---

## 2. Before you install (IT checklist)

Confirm the **server** is ready:

```text
https://<SERVER_DOMAIN>/health
https://<SERVER_DOMAIN>/api/browser-ai/targets
https://<SERVER_DOMAIN>/api/browser-ai/rules
https://<SERVER_DOMAIN>/api/browser-ai/proxy.pac?proxy=127.0.0.1:8085
```

All must return **JSON or PAC text**, not the UnifAI HTML page.

Know your company values:

| Item | Where |
|------|--------|
| Backend URL | e.g. `https://unifaiv2.dev-yp.com` |
| Uninstall key | Browser AI → **Setup** (give to employees for uninstall) |
| Package version | Must match `release/VERSION.txt` |

---

## 3. Install — employees (Setup EXE)

### Steps

1. Get `UnifAI_Guard_Setup.exe` from IT or UnifAI **Download Setup ZIP**.
2. Close old Guard if present: Task Manager → end **all** `UnifAI_Guard.exe`.
3. Run **`UnifAI_Guard_Setup.exe`**.
4. Keep **"Start automatically at Windows login"** checked (recommended).
5. Finish the wizard — Guard starts in the background (no black console window required).
6. Open `http://127.0.0.1:18085/`  
   - Version = `VERSION.txt`  
   - Proxy port healthy  
7. Ask IT to confirm Browser AI → Guard Agents shows your PC **Active** with the same version.
8. Fully quit Chrome/Edge (all windows) → reopen.
9. Open a company **Target Website** and send a test prompt.  
   IT confirms a row in **Prompt Logs**.

### Certificate warnings

If the browser shows certificate errors on AI sites:

- Tell IT.
- Check `%LOCALAPPDATA%\UnifAI\Guard\ca_install_status.txt`.
- CA trust must succeed for HTTPS inspect to work.

### What got installed

| Location | Contents |
|----------|----------|
| `%LOCALAPPDATA%\Programs\UnifAI\Guard\` | `UnifAI_Guard.exe`, config, Start Menu / Desktop shortcuts |
| HKCU Run (if autostart checked) | `UnifAI_Guard` → starts at login |
| Start Menu | UnifAI Guard · Uninstall UnifAI Guard |

---

## 4. Install — portable EXE (IT / emergency)

Use when Setup is older than `VERSION.txt`, or for quick replace:

1. End all `UnifAI_Guard.exe` in Task Manager.
2. Copy `UnifAI_Guard.exe` (and `unifai_guard_config.json` if needed) to:

   ```text
   %LOCALAPPDATA%\Programs\UnifAI\Guard\
   ```

3. Run **as Administrator once** if CA install fails without elevation.
4. Verify `http://127.0.0.1:18085/` version.
5. Restart browsers and test a Target site.

---

## 5. Upgrade

1. End all `UnifAI_Guard.exe`.
2. Install newer Setup **or** replace EXE with the build that matches new `VERSION.txt`.
3. Confirm status page version.
4. Confirm Guard Agents UI version (not an old number like 1.6.0).
5. Restart Chrome/Edge and retest.

After each company rebuild, IT must redeploy the server so **Download Setup ZIP** contains the new files.

---

## 6. Uninstall — employees (Apps / Start Menu)

### Method A — Windows Settings (recommended)

1. **Settings → Apps → Installed apps** → **UnifAI Guard** → **Uninstall**  
   **or** Start Menu → **UnifAI Guard** → **Uninstall UnifAI Guard**
2. When prompted, enter the **company uninstall key** from IT  
   (Browser AI → Setup).  
   Leave blank **only** if IT disabled the key requirement.
3. Finish the wizard.

Installer will:

- Run Guard with `--uninstall-prompt` (key check against backend)
- Stop `UnifAI_Guard.exe`
- Remove app files and `%LOCALAPPDATA%\UnifAI\Guard` data
- Remove autostart registry value (if installed with that task)

### Method B — command line (IT)

```text
"%LOCALAPPDATA%\Programs\UnifAI\Guard\UnifAI_Guard.exe" --uninstall "YOUR_COMPANY_KEY"
```

Or interactive key dialog:

```text
"%LOCALAPPDATA%\Programs\UnifAI\Guard\UnifAI_Guard.exe" --uninstall-prompt
```

Then remove leftovers via Apps uninstall if the folder remains.

### Method C — admin remote uninstall

From UnifAI UI (Browser AI), admin can request uninstall on an agent.  
The laptop Guard receives it on heartbeat and stops **without** employee key (`uninstall-ack`).

### If uninstall is rejected

| Cause | Fix |
|-------|-----|
| Wrong key | Get key from Browser AI → Setup |
| Backend unreachable | Connect laptop to network; key cannot verify offline (PAC may stay on) |
| Exit code non-zero | See message: check uninstall key; try again |

---

## 7. Hybrid: laptop + office network

Full detail: `apps/browser-guard/HYBRID_DEPLOY.txt`.

| Mode | Install | Proxy | Agent type |
|------|---------|-------|------------|
| Laptop | Setup/EXE on PC | `127.0.0.1:8085` | `endpoint` |
| Network | Docker `unifai_broswer_proxy` on server | `:8082` | `network` |

**One dashboard:** Workspace → Browser AI (Prompt Logs + Agents + shared rules).

**Do not double-MITM:** same browser session must not use laptop PAC **and** corp PAC together.

- Office → corp PAC → `:8082`
- Home/remote → laptop Guard only

Network PAC example:

```text
https://<SERVER_DOMAIN>/api/browser-ai/pac?proxy=proxy.company.local:8082
```

Distribute mitmproxy CA to machines using the network proxy.

---

## 8. IT rebuild (how to make a new installer)

```text
apps/browser-guard/
  agent/unifai_agent.py
  proxy/browser_ai_proxy.py
  config/unifai_guard_config.json   ← set backend_url
  installer/build_installer.bat
  installer/UnifAI_Guard.iss
  release/VERSION.txt
  release/UnifAI_Guard_Setup.exe
  release/UnifAI_Guard.exe
```

### Build steps

1. Edit `config/unifai_guard_config.json` → correct `backend_url`.
2. Update `VERSION.txt` (and keep ISS / build script version in sync when shipping).
3. Run:

   ```text
   apps\browser-guard\installer\build_installer.bat
   ```

4. Requires: Python build path + **Inno Setup 6** (`ISCC.exe`).
5. Outputs:
   - `release\UnifAI_Guard_Setup.exe`
   - `release\UnifAI_Guard.exe` (also under `dist\`)
6. Copy release folder onto UnifAI server; redeploy so Download ZIP updates.
7. Pilot on one PC → then company rollout.

Also see: `installer/IT_README.txt`, `installer/EMPLOYEE_README.txt`.

---

## 9. Default laptop config

File: `apps/browser-guard/config/unifai_guard_config.json`

| Field | Laptop value |
|-------|----------------|
| `backend_url` | Company UnifAI HTTPS URL |
| `proxy_addr` | `127.0.0.1:8085` |
| `server_mode` | `false` |
| `agent_type` | `endpoint` |
| `listen_host` | `127.0.0.1` |
| `pac_sync_seconds` | `3` |

---

## 10. Mac note

Mac Guard agent is **not** production-ready.  
Until it ships: use **network proxy + PAC + CA** (Section 7). Mac traffic shows as Network agent, not Laptop Guard.

---

## 11. Known limitations

| Item | Status |
|------|--------|
| Site coverage | Target list based (not every website) |
| LLM classification | Often incomplete; regex path used |
| Chrome “all sites” | Not implemented |

---

## 12. Verify checklist

**Install**

- [ ] Status page version = `VERSION.txt`
- [ ] Guard Agents = Active + same version
- [ ] Target site → Prompt Logs row
- [ ] Autostart works after reboot (if enabled)
- [ ] No unexpected cert errors (or CA status OK)

**Uninstall**

- [ ] Uninstall key accepted
- [ ] `UnifAI_Guard.exe` gone from Task Manager
- [ ] App removed from Settings → Apps
- [ ] Agent no longer Active (or marked uninstalled) in UI
- [ ] Browser proxy/PAC cleared for that user

---

## 13. Troubleshooting

| Problem | Fix |
|---------|-----|
| Status page not loading | Guard not running — start from Start Menu; check Task Manager |
| Wrong version in UI | Old EXE still running — kill all, replace, restart browsers |
| No Prompt Logs | Target not configured; backend URL wrong; PAC not applied; restart browser |
| Cert warnings | Fix CA trust; read `ca_install_status.txt` |
| Uninstall blocked | Correct key; network to UnifAI; or admin remote uninstall |
| Setup older than EXE | Prefer EXE matching `VERSION.txt` until Setup rebuilt |

---

*End of Windows Guard Implementation Guide.*
