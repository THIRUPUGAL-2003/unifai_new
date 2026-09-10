package handlers

import (
	"context"
	"strconv"
	"sync"
	"time"

	"github.com/fasthttp/router"
	unifai "github.com/unifai/unifai/core"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

type BrowserAIHandler struct {
	configStore configstore.ConfigStore
	config      *lib.Config
	client      *unifai.UnifAI
	manager     *logstore.BrowserAIManager

	// Short TTL cache — 1000+ employees hammer GetRules on every AI-bot prompt.
	rulesCacheMu sync.RWMutex
	rulesCache   []logstore.BrowserGuardRule
	rulesCacheAt time.Time
}

func NewBrowserAIHandler(configStore configstore.ConfigStore, config *lib.Config, client *unifai.UnifAI) *BrowserAIHandler {
	manager := logstore.NewBrowserAIManager(nil)
	h := &BrowserAIHandler{
		configStore: configStore,
		config:      config,
		client:      client,
		manager:     manager,
	}
	h.initDB()
	startBrowserAIAttachmentCleanup(manager)
	return h
}

// getRulesCached returns active rules with a 2s in-memory cache (hot intercept path).
func (h *BrowserAIHandler) getRulesCached(ctx context.Context) ([]logstore.BrowserGuardRule, error) {
	h.rulesCacheMu.RLock()
	if h.rulesCache != nil && time.Since(h.rulesCacheAt) < 2*time.Second {
		out := h.rulesCache
		h.rulesCacheMu.RUnlock()
		return out, nil
	}
	h.rulesCacheMu.RUnlock()

	rules, err := h.manager.GetRules(ctx)
	if err != nil {
		return rules, err
	}
	h.rulesCacheMu.Lock()
	h.rulesCache = rules
	h.rulesCacheAt = time.Now()
	h.rulesCacheMu.Unlock()
	return rules, nil
}

// invalidateRulesCache clears the short TTL after admin rule writes.
func (h *BrowserAIHandler) invalidateRulesCache() {
	h.rulesCacheMu.Lock()
	h.rulesCache = nil
	h.rulesCacheAt = time.Time{}
	h.rulesCacheMu.Unlock()
}
func (h *BrowserAIHandler) initDB() {
	if h.configStore != nil {
		if db := h.configStore.DB(); db != nil {
			h.manager.SetDB(db)
		}
	}
}

func (h *BrowserAIHandler) ensureDB(ctx *fasthttp.RequestCtx) {
	if h.manager == nil || h.manager.GetDB() == nil {
		h.initDB()
	}
}

func (h *BrowserAIHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	r.GET("/api/browser-ai/logs", lib.ChainMiddlewares(h.getLogs, middlewares...))
	r.DELETE("/api/browser-ai/logs", lib.ChainMiddlewares(h.deleteLogs, middlewares...))

	r.GET("/api/browser-ai/rules", lib.ChainMiddlewares(h.getRules, middlewares...))
	r.POST("/api/browser-ai/rules", lib.ChainMiddlewares(h.createRule, middlewares...))
	r.PUT("/api/browser-ai/rules/{id}", lib.ChainMiddlewares(h.updateRule, middlewares...))
	r.DELETE("/api/browser-ai/rules/{id}", lib.ChainMiddlewares(h.deleteRule, middlewares...))

	r.GET("/api/browser-ai/controls", lib.ChainMiddlewares(h.getControls, middlewares...))
	r.PUT("/api/browser-ai/controls", lib.ChainMiddlewares(h.updateControls, middlewares...))

	r.GET("/api/browser-ai/targets", lib.ChainMiddlewares(h.getTargets, middlewares...))
	r.POST("/api/browser-ai/targets", lib.ChainMiddlewares(h.createTarget, middlewares...))
	r.PUT("/api/browser-ai/targets/{id}", lib.ChainMiddlewares(h.updateTarget, middlewares...))
	r.DELETE("/api/browser-ai/targets/{id}", lib.ChainMiddlewares(h.deleteTarget, middlewares...))
	r.GET("/api/browser-ai/proxy.pac", lib.ChainMiddlewares(h.getProxyPAC, middlewares...))
	r.GET("/api/browser-ai/pac", lib.ChainMiddlewares(h.getProxyPAC, middlewares...))
	r.GET("/api/browser-ai/setup/download.zip", lib.ChainMiddlewares(h.downloadSetupPackage, middlewares...))
	r.GET("/api/browser-ai/setup/download-windows.zip", lib.ChainMiddlewares(h.downloadSetupPackage, middlewares...))
	r.GET("/api/browser-ai/setup/download-mac.zip", lib.ChainMiddlewares(h.downloadSetupPackage, middlewares...))

	r.GET("/api/browser-ai/agents", lib.ChainMiddlewares(h.listAgents, middlewares...))
	r.POST("/api/browser-ai/agents/heartbeat", lib.ChainMiddlewares(h.agentHeartbeat, middlewares...))
	r.GET("/api/browser-ai/fleet-config", lib.ChainMiddlewares(h.getFleetConfig, middlewares...))
	r.PUT("/api/browser-ai/fleet-config", lib.ChainMiddlewares(h.putFleetConfig, middlewares...))
	r.GET("/api/browser-ai/agents/settings", lib.ChainMiddlewares(h.getAgentSettings, middlewares...))
	r.PUT("/api/browser-ai/agents/uninstall-key", lib.ChainMiddlewares(h.saveUninstallKey, middlewares...))
	r.POST("/api/browser-ai/agents/uninstall-verify", lib.ChainMiddlewares(h.verifyUninstall, middlewares...))
	r.POST("/api/browser-ai/agents/uninstall", lib.ChainMiddlewares(h.uninstallAgent, middlewares...))
	r.POST("/api/browser-ai/agents/uninstall-ack", lib.ChainMiddlewares(h.ackRemoteUninstall, middlewares...))
	r.POST("/api/browser-ai/agents/{id}/remote-uninstall", lib.ChainMiddlewares(h.remoteUninstallAgent, middlewares...))
	r.POST("/api/browser-ai/agents/bulk-delete", lib.ChainMiddlewares(h.bulkDeleteAgents, middlewares...))
	r.DELETE("/api/browser-ai/agents/{id}", lib.ChainMiddlewares(h.deleteAgent, middlewares...))

	r.POST("/api/browser-ai/intercept", lib.ChainMiddlewares(h.intercept, middlewares...))
	r.POST("/api/browser-ai/intercept-file", lib.ChainMiddlewares(h.interceptFile, middlewares...))
	r.GET("/api/browser-ai/attachments/{id}", lib.ChainMiddlewares(h.getAttachment, middlewares...))
	r.POST("/api/browser-ai/rules/test-bot", lib.ChainMiddlewares(h.testAIGuardBot, middlewares...))
	r.POST("/api/browser-ai/rules/generate-regex", lib.ChainMiddlewares(h.generateRegexFromPolicy, middlewares...))
	r.GET("/api/browser-ai/ollama-models", lib.ChainMiddlewares(h.getOllamaModels, middlewares...))
}

func (h *BrowserAIHandler) getLogs(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)

	platform := string(ctx.QueryArgs().Peek("platform"))
	status := string(ctx.QueryArgs().Peek("status"))
	action := string(ctx.QueryArgs().Peek("action"))
	search := string(ctx.QueryArgs().Peek("search"))
	limitStr := string(ctx.QueryArgs().Peek("limit"))
	offsetStr := string(ctx.QueryArgs().Peek("offset"))

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)
	if limit <= 0 {
		limit = 50
	}

	logs, total, err := h.manager.GetLogs(ctx, platform, status, action, search, limit, offset)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}

	SendJSON(ctx, map[string]any{
		"logs":   logs,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

func (h *BrowserAIHandler) deleteLogs(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	if err := h.manager.ClearLogs(ctx); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "message": "Browser AI logs cleared"})
}
