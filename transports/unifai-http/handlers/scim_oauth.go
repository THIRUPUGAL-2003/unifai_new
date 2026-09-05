package handlers

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/unifai/unifai/framework/configstore"
	"github.com/valyala/fasthttp"
)

// SCIM OAuth routes are allowlisted for browser redirects / logout.
// These handlers keep discovery + logout flows from 404ing and persist
// callback state into the SCIM workspace setting when possible.

func (h *WorkspaceHandler) getSCIMOAuthConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	cfg := loadSCIMConfig(ctx, store)
	oauth, _ := cfg.Config["oauth"].(map[string]any)
	if oauth == nil {
		oauth = map[string]any{}
	}
	SendJSON(ctx, map[string]any{
		"enabled": cfg.Enabled,
		"provider": cfg.Provider,
		"oauth":   oauth,
	})
}

func (h *WorkspaceHandler) scimOAuthCallback(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	var body struct {
		Code  string `json:"code"`
		State string `json:"state"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	if strings.TrimSpace(body.Code) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "authorization code is required")
		return
	}
	cfg := loadSCIMConfig(ctx, store)
	if cfg.Config == nil {
		cfg.Config = map[string]any{}
	}
	oauth, _ := cfg.Config["oauth"].(map[string]any)
	if oauth == nil {
		oauth = map[string]any{}
	}
	oauth["last_callback_at"] = time.Now().UTC().Format(time.RFC3339)
	oauth["last_state"] = body.State
	oauth["discovery_complete"] = true
	// Store code briefly so admins can finish token exchange from the wizard;
	// production IdP token exchange can replace this with a real access_token.
	oauth["pending_code"] = body.Code
	cfg.Config["oauth"] = oauth
	if err := saveSCIMConfig(ctx, store, cfg); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to persist SCIM OAuth callback")
		return
	}
	SendJSON(ctx, map[string]any{"status": "ok", "message": "SCIM OAuth discovery completed"})
}

func (h *WorkspaceHandler) scimOAuthRefresh(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	cfg := loadSCIMConfig(ctx, store)
	oauth, _ := cfg.Config["oauth"].(map[string]any)
	if oauth == nil {
		SendJSON(ctx, map[string]any{"status": "ok", "refreshed": false})
		return
	}
	oauth["last_refresh_at"] = time.Now().UTC().Format(time.RFC3339)
	cfg.Config["oauth"] = oauth
	_ = saveSCIMConfig(ctx, store, cfg)
	SendJSON(ctx, map[string]any{"status": "ok", "refreshed": true})
}

func (h *WorkspaceHandler) scimOAuthLogout(ctx *fasthttp.RequestCtx) {
	if h.workspace != nil {
		cfg := loadSCIMConfig(ctx, h.workspace)
		if cfg.Config == nil {
			cfg.Config = map[string]any{}
		}
		oauth, _ := cfg.Config["oauth"].(map[string]any)
		if oauth == nil {
			oauth = map[string]any{}
		}
		delete(oauth, "pending_code")
		delete(oauth, "access_token")
		delete(oauth, "refresh_token")
		oauth["discovery_complete"] = false
		oauth["logged_out_at"] = time.Now().UTC().Format(time.RFC3339)
		cfg.Config["oauth"] = oauth
		_ = saveSCIMConfig(ctx, h.workspace, cfg)
	}
	SendJSON(ctx, map[string]string{"message": "logged out"})
}

func loadSCIMConfig(ctx *fasthttp.RequestCtx, store configstore.WorkspaceStore) scimConfigPayload {
	cfg := scimConfigPayload{Enabled: false, Config: map[string]any{}}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingSCIM)
	if err != nil {
		return cfg
	}
	_ = json.Unmarshal([]byte(row.Data), &cfg)
	if cfg.Config == nil {
		cfg.Config = map[string]any{}
	}
	return cfg
}

func saveSCIMConfig(ctx *fasthttp.RequestCtx, store configstore.WorkspaceStore, cfg scimConfigPayload) error {
	if cfg.Config == nil {
		cfg.Config = map[string]any{}
	}
	raw, err := json.Marshal(cfg)
	if err != nil {
		return err
	}
	return store.UpsertWorkspaceSetting(ctx, configstore.WorkspaceSettingSCIM, string(raw))
}
