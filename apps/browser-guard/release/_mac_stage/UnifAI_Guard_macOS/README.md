# UnifAI Guard (Browser AI desktop agent)

One product for **Windows** and **macOS**. Same backend API, Target Websites, Prompt Logs, and Guard Bot.

| OS | Package | Build |
|----|---------|--------|
| Windows | `release/UnifAI_Guard_Setup.exe` | Inno + PyInstaller on Windows |
| macOS | `release/UnifAI_Guard_macOS.zip` | `./build_macos.sh` **on a Mac** |

## Windows

```bat
REM From apps/browser-guard on Windows
pyinstaller UnifAI_Guard.spec
REM Then compile installer\UnifAI_Guard.iss with Inno Setup → release\UnifAI_Guard_Setup.exe
```

## macOS

```bash
cd apps/browser-guard
chmod +x build_macos.sh
UNIFAI_BACKEND_URL=https://your-unifai.example.com ./build_macos.sh
# Output: release/UnifAI_Guard_macOS.zip
```

Copy both artifacts onto the UnifAI server under:

- `apps/browser-guard/release/` or
- `release/`

Then redeploy so **Download Setup ZIP** includes Windows and/or Mac packages.

## Runtime behavior

- PAC only for admin **Target Websites**
- Heartbeat → Browser AI Agents
- CA trust: Windows Root store / macOS login keychain
- Autostart: Windows Run key / macOS LaunchAgent `com.unifai.guard`
