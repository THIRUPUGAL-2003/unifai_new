# UnifAI Guard (Browser AI desktop agent)

One product for **Windows** and **macOS**. Same backend, Target Websites, Prompt Logs, Guard Bot.

## Mac test setup (ready now)

ZIP already built:

`apps/browser-guard/release/UnifAI_Guard_macOS.zip`

On the **Mac**:

```bash
unzip UnifAI_Guard_macOS.zip
cd UnifAI_Guard_macOS
chmod +x install_macos.sh uninstall_macos.sh
./install_macos.sh
```

Then quit browsers (Cmd+Q), reopen, hit a monitored AI site, check Prompt Logs.

See `START_HERE_MAC.txt` inside the ZIP.

| OS | Package | How |
|----|---------|-----|
| Windows | `release/UnifAI_Guard_Setup.exe` | Inno installer |
| macOS (test/employee) | `release/UnifAI_Guard_macOS.zip` | `./install_macos.sh` on Mac |
| macOS (.app later) | run `./build_macos.sh` on Mac | optional packaging |

Copy both Windows EXE + Mac ZIP onto the UnifAI server under `apps/browser-guard/release/` (or `release/`) and redeploy so **Download Setup ZIP** includes them.
