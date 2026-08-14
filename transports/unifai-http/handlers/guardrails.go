package handlers

import (
	"encoding/json"

	"github.com/fasthttp/router"
	"github.com/unifai/unifai/core/schemas"
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

	if h.store.GuardrailsConfig == nil {
		SendJSON(ctx, &lib.GuardrailsConfig{})
		return
	}
	SendJSON(ctx, h.store.GuardrailsConfig)
}

// updateConfig handles PUT /api/guardrails/config - Updates the guardrails configuration in-memory
func (h *GuardrailsHandler) updateConfig(ctx *fasthttp.RequestCtx) {
	var payload lib.GuardrailsConfig

	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}

	h.store.Mu.Lock()
	h.store.GuardrailsConfig = &payload
	h.store.Mu.Unlock()

	// In a real MVP, you might also trigger a reload of the guardrails plugin so the rules take effect immediately.
	// We'll leave that as a TODO if needed, but for now we just update the in-memory configuration struct.

	SendJSON(ctx, map[string]any{"success": true})
}
