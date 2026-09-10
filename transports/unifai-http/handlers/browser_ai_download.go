package handlers

import (
	"archive/zip"
	"bufio"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/valyala/fasthttp"
)

func browserAISetupCandidates() map[string][]string {
	return map[string][]string{
		"UnifAI_Guard_Setup.exe": {
			filepath.Join("apps", "browser-guard", "release", "UnifAI_Guard_Setup.exe"),
			filepath.Join("release", "UnifAI_Guard_Setup.exe"),
			"/app/release/UnifAI_Guard_Setup.exe",
			"/app/apps/browser-guard/release/UnifAI_Guard_Setup.exe",
		},
		// Portable EXE (latest PyInstaller build) — preferred when newer than Setup.exe.
		"UnifAI_Guard.exe": {
			filepath.Join("apps", "browser-guard", "release", "UnifAI_Guard.exe"),
			filepath.Join("apps", "browser-guard", "dist", "UnifAI_Guard.exe"),
			filepath.Join("release", "UnifAI_Guard.exe"),
			"/app/release/UnifAI_Guard.exe",
			"/app/apps/browser-guard/release/UnifAI_Guard.exe",
		},
		// macOS employee package (PyInstaller .app + install/uninstall scripts).
		"UnifAI_Guard_macOS.zip": {
			filepath.Join("apps", "browser-guard", "release", "UnifAI_Guard_macOS.zip"),
			filepath.Join("release", "UnifAI_Guard_macOS.zip"),
			"/app/release/UnifAI_Guard_macOS.zip",
			"/app/apps/browser-guard/release/UnifAI_Guard_macOS.zip",
		},
		"INSTALL_WINDOWS.txt": {
			filepath.Join("apps", "browser-guard", "release", "INSTALL_WINDOWS.txt"),
			filepath.Join("release", "INSTALL_WINDOWS.txt"),
			"/app/release/INSTALL_WINDOWS.txt",
			"/app/apps/browser-guard/release/INSTALL_WINDOWS.txt",
		},
		"INSTALL_MACOS.txt": {
			filepath.Join("apps", "browser-guard", "release", "INSTALL_MACOS.txt"),
			filepath.Join("release", "INSTALL_MACOS.txt"),
			"/app/release/INSTALL_MACOS.txt",
			"/app/apps/browser-guard/release/INSTALL_MACOS.txt",
		},
		"UNINSTALL_MACOS.txt": {
			filepath.Join("apps", "browser-guard", "release", "UNINSTALL_MACOS.txt"),
			filepath.Join("release", "UNINSTALL_MACOS.txt"),
			"/app/release/UNINSTALL_MACOS.txt",
			"/app/apps/browser-guard/release/UNINSTALL_MACOS.txt",
		},
		"EMPLOYEE_README_MAC.txt": {
			filepath.Join("apps", "browser-guard", "release", "EMPLOYEE_README_MAC.txt"),
			filepath.Join("apps", "browser-guard", "installer", "EMPLOYEE_README_MAC.txt"),
			filepath.Join("release", "EMPLOYEE_README_MAC.txt"),
			"/app/release/EMPLOYEE_README_MAC.txt",
			"/app/apps/browser-guard/release/EMPLOYEE_README_MAC.txt",
		},
		"Install_UnifAI_Guard.command": {
			filepath.Join("apps", "browser-guard", "release", "Install_UnifAI_Guard.command"),
			filepath.Join("apps", "browser-guard", "installer", "Install_UnifAI_Guard.command"),
			filepath.Join("release", "Install_UnifAI_Guard.command"),
			"/app/release/Install_UnifAI_Guard.command",
			"/app/apps/browser-guard/release/Install_UnifAI_Guard.command",
		},
		"Uninstall_UnifAI_Guard.command": {
			filepath.Join("apps", "browser-guard", "release", "Uninstall_UnifAI_Guard.command"),
			filepath.Join("apps", "browser-guard", "installer", "Uninstall_UnifAI_Guard.command"),
			filepath.Join("release", "Uninstall_UnifAI_Guard.command"),
			"/app/release/Uninstall_UnifAI_Guard.command",
			"/app/apps/browser-guard/release/Uninstall_UnifAI_Guard.command",
		},
		"VERSION.txt": {
			filepath.Join("apps", "browser-guard", "release", "VERSION.txt"),
			filepath.Join("release", "VERSION.txt"),
			"/app/release/VERSION.txt",
			"/app/apps/browser-guard/release/VERSION.txt",
		},
	}
}

func findFirstExisting(candidates []string) (string, bool) {
	for _, candidate := range candidates {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			return candidate, true
		}
	}
	return "", false
}

func fileModTime(path string) time.Time {
	info, err := os.Stat(path)
	if err != nil {
		return time.Time{}
	}
	return info.ModTime()
}

func readGuardReleaseVersion() string {
	for _, p := range []string{
		filepath.Join("apps", "browser-guard", "release", "VERSION.txt"),
		filepath.Join("release", "VERSION.txt"),
	} {
		data, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		v := strings.TrimSpace(string(data))
		if v != "" {
			return v
		}
	}
	// Fallback: parse AGENT_VERSION from source when VERSION.txt missing.
	agentPy := filepath.Join("apps", "browser-guard", "agent", "unifai_agent.py")
	data, err := os.ReadFile(agentPy)
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "AGENT_VERSION") && strings.Contains(line, "=") {
			parts := strings.SplitN(line, "=", 2)
			if len(parts) == 2 {
				v := strings.Trim(strings.TrimSpace(parts[1]), `"'`)
				if v != "" {
					return v
				}
			}
		}
	}
	return ""
}

func (h *BrowserAIHandler) downloadSetupPackage(ctx *fasthttp.RequestCtx) {
	type zipAsset struct {
		name string
		path string
	}

	platform := strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("platform"))))
	if platform == "" {
		platform = strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("os"))))
	}
	path := string(ctx.Path())
	if strings.Contains(path, "download-windows") {
		platform = "windows"
	} else if strings.Contains(path, "download-mac") {
		platform = "mac"
	}

	setupPath, setupOK := findFirstExisting(browserAISetupCandidates()["UnifAI_Guard_Setup.exe"])
	exePath, exeOK := findFirstExisting(browserAISetupCandidates()["UnifAI_Guard.exe"])
	macZipPath, macZipOK := findFirstExisting(browserAISetupCandidates()["UnifAI_Guard_macOS.zip"])
	releaseVer := readGuardReleaseVersion()

	// 1. MAC DEDICATED DOWNLOAD
	if platform == "mac" || platform == "macos" || platform == "darwin" {
		if !macZipOK {
			SendError(ctx, fasthttp.StatusNotFound, "No macOS Guard installer on server — add UnifAI_Guard_macOS.zip under apps/browser-guard/release/")
			return
		}
		ctx.SetStatusCode(fasthttp.StatusOK)
		ctx.SetContentType("application/zip")
		ctx.Response.Header.Set("Content-Disposition", `attachment; filename="UnifAI_Guard_macOS.zip"`)
		if releaseVer != "" {
			ctx.Response.Header.Set("X-UnifAI-Guard-Version", releaseVer)
		}
		ctx.SetBodyStreamWriter(func(w *bufio.Writer) {
			f, err := os.Open(macZipPath)
			if err != nil {
				return
			}
			defer f.Close()
			_, _ = io.Copy(w, f)
			_ = w.Flush()
		})
		return
	}

	// 2. WINDOWS DEDICATED DOWNLOAD
	if platform == "windows" || platform == "win" {
		if !setupOK && !exeOK {
			SendError(ctx, fasthttp.StatusNotFound, "No Windows Guard installer on server — add UnifAI_Guard_Setup.exe or UnifAI_Guard.exe under apps/browser-guard/release/")
			return
		}
		if setupOK && exeOK {
			if fileModTime(exePath).After(fileModTime(setupPath)) {
				setupOK = false
			}
		}
		var winAssets []zipAsset
		if setupOK {
			winAssets = append(winAssets, zipAsset{name: "UnifAI_Guard_Setup.exe", path: setupPath})
		}
		if exeOK {
			winAssets = append(winAssets, zipAsset{name: "UnifAI_Guard.exe", path: exePath})
		}
		for _, name := range []string{"INSTALL_WINDOWS.txt", "VERSION.txt"} {
			if p, ok := findFirstExisting(browserAISetupCandidates()[name]); ok {
				winAssets = append(winAssets, zipAsset{name: name, path: p})
			}
		}
		ctx.SetStatusCode(fasthttp.StatusOK)
		ctx.SetContentType("application/zip")
		ctx.Response.Header.Set("Content-Disposition", `attachment; filename="UnifAI_Guard_Windows.zip"`)
		if releaseVer != "" {
			ctx.Response.Header.Set("X-UnifAI-Guard-Version", releaseVer)
		}
		ctx.SetBodyStreamWriter(func(w *bufio.Writer) {
			zw := zip.NewWriter(w)
			wroteVersion := false
			for _, asset := range winAssets {
				data, err := os.ReadFile(asset.path)
				if err != nil {
					continue
				}
				entry, err := zw.Create(asset.name)
				if err != nil {
					continue
				}
				_, _ = entry.Write(data)
				if asset.name == "VERSION.txt" {
					wroteVersion = true
				}
			}
			if !wroteVersion && releaseVer != "" {
				if entry, err := zw.Create("VERSION.txt"); err == nil {
					_, _ = entry.Write([]byte(releaseVer + "\n"))
				}
			}
			_ = zw.Close()
			_ = w.Flush()
		})
		return
	}

	// 3. COMBINED / LEGACY DOWNLOAD (when no platform specified)
	if setupOK && exeOK {
		if fileModTime(exePath).After(fileModTime(setupPath)) {
			setupOK = false
		}
	}

	var assets []zipAsset
	if setupOK {
		assets = append(assets, zipAsset{name: "UnifAI_Guard_Setup.exe", path: setupPath})
	}
	if exeOK {
		assets = append(assets, zipAsset{name: "UnifAI_Guard.exe", path: exePath})
	}
	if macZipOK {
		assets = append(assets, zipAsset{name: "UnifAI_Guard_macOS.zip", path: macZipPath})
	}
	for _, name := range []string{
		"INSTALL_WINDOWS.txt",
		"INSTALL_MACOS.txt",
		"UNINSTALL_MACOS.txt",
		"EMPLOYEE_README_MAC.txt",
		"Install_UnifAI_Guard.command",
		"Uninstall_UnifAI_Guard.command",
		"VERSION.txt",
	} {
		if path, ok := findFirstExisting(browserAISetupCandidates()[name]); ok {
			assets = append(assets, zipAsset{name: name, path: path})
		}
	}

	hasWindows := setupOK || exeOK
	hasMac := macZipOK
	if !hasWindows && !hasMac {
		SendError(ctx, fasthttp.StatusNotFound, "No Guard installer on server — add UnifAI_Guard.exe / UnifAI_Guard_Setup.exe and/or UnifAI_Guard_macOS.zip under apps/browser-guard/release/")
		return
	}
	if len(assets) == 0 {
		SendError(ctx, fasthttp.StatusNotFound, "No Browser AI setup package files found on server")
		return
	}

	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetContentType("application/zip")
	ctx.Response.Header.Set("Content-Disposition", `attachment; filename="unifai-browser-ai-setup.zip"`)
	if releaseVer != "" {
		ctx.Response.Header.Set("X-UnifAI-Guard-Version", releaseVer)
	}
	ctx.SetBodyStreamWriter(func(w *bufio.Writer) {
		zw := zip.NewWriter(w)
		wroteVersion := false
		for _, asset := range assets {
			data, err := os.ReadFile(asset.path)
			if err != nil {
				continue
			}
			entry, err := zw.Create(asset.name)
			if err != nil {
				continue
			}
			_, _ = entry.Write(data)
			if asset.name == "VERSION.txt" {
				wroteVersion = true
			}
		}
		// Always embed the current release version so employees see the expected number.
		if !wroteVersion && releaseVer != "" {
			if entry, err := zw.Create("VERSION.txt"); err == nil {
				_, _ = entry.Write([]byte(releaseVer + "\n"))
			}
		}
		_ = zw.Close()
		_ = w.Flush()
	})
}
