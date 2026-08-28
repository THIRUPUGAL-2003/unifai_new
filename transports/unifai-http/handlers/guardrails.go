package handlers

import (
	"encoding/json"

	"github.com/fasthttp/router"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/plugins/guardrails"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

// GuardrailsHandler manages runtime configuration updates for Guardrails.
type GuardrailsHandler struct {
	store         *lib.Config
	configManager ConfigManager
}

// NewGuardrailsHandler creates a new handler for guardrails configuration management.
func NewGuardrailsHandler(configManager ConfigManager, store *lib.Config) *GuardrailsHandler {
	return &GuardrailsHandler{
		configManager: configManager,
		store:         store,
	}
}

// RegisterRoutes registers the configuration-related routes.
func (h *GuardrailsHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	r.GET("/api/guardrails/config", lib.ChainMiddlewares(h.getConfig, middlewares...))
	r.PUT("/api/guardrails/config", lib.ChainMiddlewares(h.updateConfig, middlewares...))
}

// getConfig handles GET /api/guardrails/config - Get the current guardrails configuration
func (h *GuardrailsHandler) getConfig(ctx *fasthttp.RequestCtx) {
	h.store.Mu.RLock()
	defer h.store.Mu.RUnlock()
	SendJSON(ctx, cloneGuardrailsConfig(h.store.GuardrailsConfig))
}

// updateConfig handles PUT /api/guardrails/config - Updates the guardrails configuration
// and reloads the guardrails plugin so rules take effect immediately.
func (h *GuardrailsHandler) updateConfig(ctx *fasthttp.RequestCtx) {
	var payload lib.GuardrailsConfig

	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	payload = cloneGuardrailsConfig(&payload)

	pluginCfg := &guardrails.Config{}
	cfgBytes, err := json.Marshal(payload)
	if err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid guardrails configuration")
		return
	}
	if err := json.Unmarshal(cfgBytes, pluginCfg); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid guardrails configuration")
		return
	}
	if err := guardrails.ValidateConfig(pluginCfg); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, err.Error())
		return
	}

	// Persist first so a disk failure does not leave memory ahead of the file.
	if err := h.store.PersistGuardrailsConfig(&payload); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to persist guardrails config: "+err.Error())
		return
	}

	h.store.Mu.Lock()
	copied := payload
	h.store.GuardrailsConfig = &copied
	h.store.Mu.Unlock()

	// InstantiatePlugin(guardrails) reads unifaiConfig.GuardrailsConfig — reload so CEL/providers apply now.
	reloaded := true
	if h.configManager != nil {
		placement := schemas.PluginPlacementBuiltin
		order := 9
		if err := h.configManager.ReloadPlugin(ctx, guardrails.PluginName, nil, nil, &placement, &order); err != nil {
			// Config is already persisted; do not fail the save. The new config is in memory
			// and will load on the next process start even if live reload fails.
			logger.Warn("guardrails plugin reload failed after save: %v", err)
			reloaded = false
		}
	}

	SendJSON(ctx, map[string]any{"success": true, "reloaded": reloaded})
}

func cloneGuardrailsConfig(cfg *lib.GuardrailsConfig) lib.GuardrailsConfig {
	out := lib.GuardrailsConfig{
		GuardrailRules:     []lib.GuardrailRule{},
		GuardrailProviders: []lib.GuardrailProvider{},
	}
	if cfg == nil {
		return out
	}
	if cfg.GuardrailRules != nil {
		out.GuardrailRules = cfg.GuardrailRules
	}
	if cfg.GuardrailProviders != nil {
		out.GuardrailProviders = cfg.GuardrailProviders
	}
	return out
}
