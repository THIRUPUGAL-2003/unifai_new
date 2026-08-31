package handlers

import (
	"encoding/json"

	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/connectors"
	"github.com/valyala/fasthttp"
)

type scimConfigPayload struct {
	Enabled  bool           `json:"enabled"`
	Provider string         `json:"provider"`
	Config   map[string]any `json:"config"`
}

func (h *WorkspaceHandler) getSCIMConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingSCIM)
	if isStoreNotFound(err) {
		SendJSON(ctx, scimConfigPayload{Enabled: false, Config: map[string]any{}})
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load scim config")
		return
	}
	var cfg scimConfigPayload
	if err := json.Unmarshal([]byte(row.Data), &cfg); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to parse scim config")
		return
	}
	if cfg.Config == nil {
		cfg.Config = map[string]any{}
	}
	SendJSON(ctx, cfg)
}

func (h *WorkspaceHandler) updateSCIMConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	var payload scimConfigPayload
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	if payload.Enabled && payload.Provider == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "provider is required when scim is enabled")
		return
	}
	switch payload.Provider {
	case "", "okta", "entra", "keycloak":
	default:
		SendError(ctx, fasthttp.StatusBadRequest, "provider must be okta, entra, or keycloak")
		return
	}
	if payload.Config == nil {
		payload.Config = map[string]any{}
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to save scim config")
		return
	}
	if err := store.UpsertWorkspaceSetting(ctx, configstore.WorkspaceSettingSCIM, string(raw)); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to save scim config")
		return
	}
	SendJSON(ctx, payload)
}

func (h *WorkspaceHandler) listSCIMProviders(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingSCIM)
	if err != nil {
		SendJSON(ctx, []any{})
		return
	}
	var cfg scimConfigPayload
	if err := json.Unmarshal([]byte(row.Data), &cfg); err != nil || !cfg.Enabled || cfg.Provider == "" {
		SendJSON(ctx, []any{})
		return
	}
	SendJSON(ctx, []map[string]any{{"provider": cfg.Provider, "enabled": cfg.Enabled}})
}

var allowedConnectors = map[string]bool{
	"datadog":  true,
	"kafka":    true,
	"bigquery": true,
	"pubsub":   true,
}

func (h *WorkspaceHandler) getConnector(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	name := pathID(ctx, "name")
	if !allowedConnectors[name] {
		SendError(ctx, fasthttp.StatusNotFound, "unknown connector")
		return
	}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingConnector(name))
	if isStoreNotFound(err) {
		SendJSON(ctx, map[string]any{"name": name, "enabled": false, "config": map[string]any{}})
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load connector")
		return
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(row.Data), &payload); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to parse connector")
		return
	}
	payload["name"] = name
	SendJSON(ctx, payload)
}

func (h *WorkspaceHandler) updateConnector(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	name := pathID(ctx, "name")
	if !allowedConnectors[name] {
		SendError(ctx, fasthttp.StatusNotFound, "unknown connector")
		return
	}
	var payload map[string]any
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	payload["name"] = name
	raw, err := json.Marshal(payload)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to save connector")
		return
	}
	if err := store.UpsertWorkspaceSetting(ctx, configstore.WorkspaceSettingConnector(name), string(raw)); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to save connector")
		return
	}
	ReloadConnectorsFromStore(store)
	settings := connectors.Settings{Name: name, Enabled: false, Config: map[string]string{}}
	if enabled, ok := payload["enabled"].(bool); ok {
		settings.Enabled = enabled
	}
	if cfgMap, ok := payload["config"].(map[string]any); ok {
		for k, v := range cfgMap {
			if s, ok := v.(string); ok {
				settings.Config[k] = s
			}
		}
	}
	connectors.Default.ApplySettings(settings)
	test := connectors.Default.Test(ctx, name, settings)
	payload["connection"] = test
	if settings.Enabled && !test.OK {
		SendJSONWithStatus(ctx, payload, fasthttp.StatusBadGateway)
		return
	}
	SendJSON(ctx, payload)
}

func (h *WorkspaceHandler) testConnector(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	name := pathID(ctx, "name")
	if !allowedConnectors[name] {
		SendError(ctx, fasthttp.StatusNotFound, "unknown connector")
		return
	}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingConnector(name))
	if isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "connector not configured")
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load connector")
		return
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(row.Data), &payload); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to parse connector")
		return
	}
	settings := connectors.Settings{Name: name, Config: map[string]string{}}
	if enabled, ok := payload["enabled"].(bool); ok {
		settings.Enabled = enabled
	}
	if cfgMap, ok := payload["config"].(map[string]any); ok {
		for k, v := range cfgMap {
			if s, ok := v.(string); ok {
				settings.Config[k] = s
			}
		}
	}
	result := connectors.Default.Test(ctx, name, settings)
	if !result.OK {
		SendJSONWithStatus(ctx, map[string]any{"connection": result}, fasthttp.StatusBadGateway)
		return
	}
	SendJSON(ctx, map[string]any{"connection": result})
}
