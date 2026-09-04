package handlers

import (
	"archive/zip"
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/bytedance/sonic"
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

	r.GET("/api/browser-ai/agents", lib.ChainMiddlewares(h.listAgents, middlewares...))
	r.POST("/api/browser-ai/agents/heartbeat", lib.ChainMiddlewares(h.agentHeartbeat, middlewares...))
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

func (h *BrowserAIHandler) getRules(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	rules, err := h.manager.GetRules(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"rules": rules})
}

func (h *BrowserAIHandler) getOllamaModels(ctx *fasthttp.RequestCtx) {
	models, baseURL, err := listOllamaInstalledModels(10 * time.Second)
	if err != nil {
		SendError(ctx, fasthttp.StatusBadGateway, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{
		"models":   models,
		"base_url": baseURL,
	})
}

func (h *BrowserAIHandler) createRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var rule logstore.BrowserGuardRule
	if err := sonic.Unmarshal(ctx.PostBody(), &rule); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if strings.TrimSpace(rule.Name) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Rule name is required")
		return
	}
	if strings.ToLower(rule.RuleType) == "ai_bot" {
		applyAIBotDefaults(&rule)
		if err := validateAIBotRuleFields(&rule); err != nil {
			SendError(ctx, fasthttp.StatusBadRequest, err.Error())
			return
		}
	} else {
		rule.RuleType = "regex"
		if strings.TrimSpace(rule.Pattern) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Regex pattern is required for Regex rule")
			return
		}
	}
	if err := h.manager.CreateRule(ctx, &rule); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "rule": rule})
}

func (h *BrowserAIHandler) updateRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing rule ID")
		return
	}
	var updates map[string]any
	if err := sonic.Unmarshal(ctx.PostBody(), &updates); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}

	// Validate AI Guard Bot fields for the resulting rule (including partial updates).
	ruleType := ""
	if v, ok := updates["rule_type"].(string); ok {
		ruleType = strings.ToLower(strings.TrimSpace(v))
	}
	_, hasBotPrompt := updates["bot_prompt"]
	_, hasBotProvider := updates["bot_provider"]
	_, hasBotModel := updates["bot_model"]
	_, hasBotReferenceImage := updates["bot_reference_image"]
	_, hasBotReferenceImageType := updates["bot_reference_image_type"]
	needsAIBotCheck := ruleType == "ai_bot" || hasBotPrompt || hasBotProvider || hasBotModel || hasBotReferenceImage || hasBotReferenceImageType
	if needsAIBotCheck {
		if existingRules, getErr := h.manager.GetRules(ctx); getErr == nil {
			for i := range existingRules {
				if existingRules[i].ID != id {
					continue
				}
				existing := existingRules[i]
				if ruleType == "" {
					ruleType = strings.ToLower(strings.TrimSpace(existing.RuleType))
				}
				if !hasBotPrompt {
					updates["bot_prompt"] = existing.BotPrompt
				}
				if !hasBotProvider {
					updates["bot_provider"] = existing.BotProvider
				}
				if !hasBotModel {
					updates["bot_model"] = existing.BotModel
				}
				if !hasBotReferenceImage {
					updates["bot_reference_image"] = existing.BotReferenceImage
				}
				if !hasBotReferenceImageType {
					updates["bot_reference_image_type"] = existing.BotReferenceImageType
				}
				break
			}
		}
	}
	if ruleType == "ai_bot" {
		tmp := logstore.BrowserGuardRule{
			RuleType:              "ai_bot",
			BotProvider:           stringFromUpdate(updates, "bot_provider"),
			BotModel:              stringFromUpdate(updates, "bot_model"),
			BotPrompt:             stringFromUpdate(updates, "bot_prompt"),
			BotReferenceImage:     stringFromUpdate(updates, "bot_reference_image"),
			BotReferenceImageType: stringFromUpdate(updates, "bot_reference_image_type"),
		}
		if err := validateAIBotRuleFields(&tmp); err != nil {
			SendError(ctx, fasthttp.StatusBadRequest, err.Error())
			return
		}
		updates["bot_provider"] = tmp.BotProvider
		updates["bot_model"] = tmp.BotModel
		updates["bot_prompt"] = tmp.BotPrompt
		updates["bot_reference_image"] = tmp.BotReferenceImage
		updates["bot_reference_image_type"] = tmp.BotReferenceImageType
	}

	if err := h.manager.UpdateRule(ctx, id, updates); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success"})
}

func (h *BrowserAIHandler) deleteRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing rule ID")
		return
	}
	if err := h.manager.DeleteRule(ctx, id); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success"})
}

func (h *BrowserAIHandler) getControls(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	ctrl, err := h.manager.GetControls(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"controls": ctrl})
}

func (h *BrowserAIHandler) updateControls(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var updates map[string]any
	if err := sonic.Unmarshal(ctx.PostBody(), &updates); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	ctrl, err := h.manager.UpdateControls(ctx, updates)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "controls": ctrl})
}

func (h *BrowserAIHandler) getTargets(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	targets, err := h.manager.GetTargets(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"targets": targets})
}

// getProxyPAC serves a PAC built only from monitored Target Websites (no hardcoded defaults).
func (h *BrowserAIHandler) getProxyPAC(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	proxyAddr := string(ctx.QueryArgs().Peek("proxy"))
	if strings.TrimSpace(proxyAddr) == "" {
		proxyAddr = "127.0.0.1:8085"
	}
	pac, _ := h.manager.BuildProxyPAC(context.Background(), proxyAddr)
	if strings.TrimSpace(pac) == "" {
		pac, _ = h.manager.BuildProxyPAC(context.Background(), "127.0.0.1:8085")
	}
	ctx.Response.Header.Set("Content-Type", "application/x-ns-proxy-autoconfig; charset=utf-8")
	ctx.Response.Header.Set("Cache-Control", "no-store, no-cache, must-revalidate")
	ctx.Response.Header.Set("Access-Control-Allow-Origin", "*")
	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetBodyString(pac)
}

func browserAISetupCandidates() map[string][]string {
	return map[string][]string{
		"UnifAI_Guard_Setup.exe": {
			filepath.Join("apps", "browser-guard", "release", "UnifAI_Guard_Setup.exe"),
			filepath.Join("release", "UnifAI_Guard_Setup.exe"),
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

func (h *BrowserAIHandler) downloadSetupPackage(ctx *fasthttp.RequestCtx) {
	type zipAsset struct {
		name string
		path string
	}

	var assets []zipAsset
	for name, candidates := range browserAISetupCandidates() {
		if path, ok := findFirstExisting(candidates); ok {
			assets = append(assets, zipAsset{name: name, path: path})
		}
	}

	hasSetupEXE := false
	for _, a := range assets {
		if a.name == "UnifAI_Guard_Setup.exe" {
			hasSetupEXE = true
			break
		}
	}
	if !hasSetupEXE {
		SendError(ctx, fasthttp.StatusNotFound, "UnifAI_Guard_Setup.exe missing on server — rebuild installer and redeploy image")
		return
	}
	if len(assets) == 0 {
		SendError(ctx, fasthttp.StatusNotFound, "No Browser AI setup package files found on server")
		return
	}

	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetContentType("application/zip")
	ctx.Response.Header.Set("Content-Disposition", `attachment; filename="unifai-browser-ai-setup.zip"`)
	ctx.SetBodyStreamWriter(func(w *bufio.Writer) {
		zw := zip.NewWriter(w)
		for _, asset := range assets {
			data, err := os.ReadFile(asset.path)
			if err != nil {
				continue
			}
			entry, err := zw.Create(asset.name)
			if err != nil {
				continue
			}
			if _, err := entry.Write(data); err != nil {
				continue
			}
		}
		_ = zw.Close()
		_ = w.Flush()
	})
}

func (h *BrowserAIHandler) listAgents(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	status := string(ctx.QueryArgs().Peek("status"))
	search := string(ctx.QueryArgs().Peek("search"))
	limit, _ := strconv.Atoi(string(ctx.QueryArgs().Peek("limit")))
	offset, _ := strconv.Atoi(string(ctx.QueryArgs().Peek("offset")))
	if limit <= 0 {
		limit = 50
	}
	agents, total, err := h.manager.ListAgents(ctx, status, search, limit, offset)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{
		"agents": agents,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

func (h *BrowserAIHandler) agentHeartbeat(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var body logstore.BrowserAIAgent
	if err := sonic.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if strings.TrimSpace(body.ID) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "agent id is required")
		return
	}
	if strings.TrimSpace(body.IPAddress) == "" {
		body.IPAddress = ctx.RemoteIP().String()
	}
	agent, err := h.manager.UpsertAgentHeartbeat(ctx, &body)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	settings, _ := h.manager.GetAgentSettings(ctx)
	command := ""
	if agent != nil && agent.UninstallRequested && agent.Status != logstore.AgentStatusUninstalled {
		command = "uninstall"
	}
	SendJSON(ctx, map[string]any{
		"status":   "success",
		"agent":    agent,
		"settings": settings,
		"command":  command,
	})
}

func (h *BrowserAIHandler) getAgentSettings(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	settings, err := h.manager.GetAgentSettings(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"settings": settings})
}

func (h *BrowserAIHandler) saveUninstallKey(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var req struct {
		Key                 string `json:"key"`
		RequireUninstallKey *bool  `json:"require_uninstall_key"`
		UpdatedBy           string `json:"updated_by"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &req); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if strings.TrimSpace(req.Key) == "" && req.RequireUninstallKey == nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Provide uninstall key and/or require_uninstall_key")
		return
	}
	settings, err := h.manager.SaveUninstallKey(ctx, req.Key, req.UpdatedBy, req.RequireUninstallKey)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "settings": settings})
}

func (h *BrowserAIHandler) verifyUninstall(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var req struct {
		Key string `json:"key"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &req); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	ok, settings, err := h.manager.VerifyUninstallKey(ctx, req.Key)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{
		"valid":    ok,
		"settings": settings,
	})
}

func (h *BrowserAIHandler) uninstallAgent(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var req struct {
		AgentID string `json:"agent_id"`
		Key     string `json:"key"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &req); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	ok, settings, err := h.manager.VerifyUninstallKey(ctx, req.Key)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	if !ok {
		SendError(ctx, fasthttp.StatusForbidden, "Invalid uninstall key")
		return
	}
	agent, err := h.manager.MarkAgentUninstalled(ctx, req.AgentID)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{
		"status":   "success",
		"agent":    agent,
		"settings": settings,
	})
}

func (h *BrowserAIHandler) remoteUninstallAgent(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing agent ID")
		return
	}
	agent, err := h.manager.RequestRemoteUninstall(ctx, id)
	if err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "agent": agent, "command": "uninstall"})
}

func (h *BrowserAIHandler) deleteAgent(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing agent ID")
		return
	}
	deleted, err := h.manager.DeleteAgents(ctx, []string{id})
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	if deleted == 0 {
		SendError(ctx, fasthttp.StatusNotFound, "Agent not found")
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "deleted": deleted})
}

func (h *BrowserAIHandler) bulkDeleteAgents(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var req struct {
		IDs []string `json:"ids"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &req); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	deleted, err := h.manager.DeleteAgents(ctx, req.IDs)
	if err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "deleted": deleted})
}

func (h *BrowserAIHandler) ackRemoteUninstall(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var req struct {
		AgentID string `json:"agent_id"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &req); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	agent, err := h.manager.AckRemoteUninstall(ctx, req.AgentID)
	if err != nil {
		if strings.Contains(err.Error(), "not requested") || strings.Contains(err.Error(), "not found") {
			SendError(ctx, fasthttp.StatusForbidden, err.Error())
			return
		}
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "agent": agent})
}

func (h *BrowserAIHandler) createTarget(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var target logstore.BrowserTargetWebsite
	if err := sonic.Unmarshal(ctx.PostBody(), &target); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if err := h.manager.CreateTarget(ctx, &target); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "target": target})
}

func (h *BrowserAIHandler) updateTarget(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing target ID")
		return
	}
	var updates map[string]any
	if err := sonic.Unmarshal(ctx.PostBody(), &updates); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if err := h.manager.UpdateTarget(ctx, id, updates); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success"})
}

func (h *BrowserAIHandler) deleteTarget(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing target ID")
		return
	}
	if err := h.manager.DeleteTarget(ctx, id); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success"})
}

func (h *BrowserAIHandler) intercept(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)

	var payload struct {
		Platform      string         `json:"platform"`
		Prompt        string         `json:"prompt"`
		ClientIP      string         `json:"client_ip"`
		AgentID       string         `json:"agent_id"`
		AgentHostname string         `json:"agent_hostname"`
		UploadImages  []string       `json:"upload_images"`
		Metadata      map[string]any `json:"metadata"`
	}

	if err := sonic.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}

	if payload.ClientIP == "" {
		payload.ClientIP = string(ctx.RemoteIP().String())
	}
	if payload.Platform == "" {
		payload.Platform = "Browser AI"
	}
	if payload.Metadata == nil {
		payload.Metadata = make(map[string]any)
	}
	if strings.TrimSpace(payload.AgentID) != "" {
		payload.Metadata["agent_id"] = strings.TrimSpace(payload.AgentID)
	}
	if strings.TrimSpace(payload.AgentHostname) != "" {
		payload.Metadata["agent_hostname"] = strings.TrimSpace(payload.AgentHostname)
	}

	evalOnly := metadataBool(payload.Metadata, "evaluation_only")
	if evalOnly {
		allowed, action, ruleTriggered, ruleWarning, evalError, securityVerdict := h.evaluateGuardOnly(ctx, payload.Prompt, payload.UploadImages)
		forwardPrompt := payload.Prompt
		if action == "Redacted" || action == "Warned" {
			forwardPrompt = logstore.FormatWarnedForwardPrompt(payload.Prompt, ruleWarning)
		}
		SendJSON(ctx, map[string]any{
			"status":             "success",
			"allowed":            allowed,
			"action":             action,
			"rule_triggered":     ruleTriggered,
			"warning_message":    ruleWarning,
			"forward_prompt":     forwardPrompt,
			"redacted_prompt":    forwardPrompt,
			"eval_error":         evalError,
			"security_verdict":   securityVerdict,
			"security_message":   securityVerdictMessage(securityVerdict, ruleTriggered),
			"predicted_category": securityVerdictCategory(securityVerdict),
		})
		return
	}

	logEntry, ruleWarning, err := h.manager.InterceptPrompt(ctx, payload.Platform, payload.Prompt, payload.ClientIP, payload.Metadata)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}

	allowed := logEntry.Action == "Allowed" || logEntry.Action == "Redacted" || logEntry.Action == "Warned"
	isViolationBlock := !allowed

	// File-upload audit logs: proxy already decided allow/block. Do not re-run AI Guard Bot
	// or Reply Bot on "[FILE UPLOAD] …" — that corrupts Allowed upload rows in Prompt Logs.
	uploadScan := metadataBool(payload.Metadata, "upload_scan")
	if strings.HasPrefix(strings.TrimSpace(payload.Prompt), "[FILE UPLOAD]") ||
		strings.HasPrefix(strings.TrimSpace(payload.Prompt), "[VOICE UPLOAD]") {
		uploadScan = true
	}
	if uploadScan {
		SendJSON(ctx, map[string]any{
			"status":             "success",
			"allowed":            allowed,
			"action":             logEntry.Action,
			"rule_triggered":     logEntry.RuleTriggered,
			"warning_message":    ruleWarning,
			"redacted_prompt":    payload.Prompt,
			"forward_prompt":     payload.Prompt,
			"risk_score":         logEntry.RiskScore,
			"predictive_risk":    logEntry.PredictiveRisk,
			"predicted_category": logEntry.PredictedCategory,
			"reply_text":         "",
			"reply_bot_provider": "",
			"reply_bot_model":    "",
			"eval_error":         "",
			"log":                logEntry,
		})
		return
	}

	evalError := ""
	securityVerdict := "not_evaluated" // clear | violation | warning | eval_failed | misconfigured | not_evaluated
	aiBotCheckedOK := false
	// Evaluate AI Guard Bot whenever the prompt is still allowed (Allowed or Warned).
	// A regex WARN must not short-circuit a stronger AI Guard Bot BLOCK policy.
	if allowed {
		rules, _ := h.manager.GetRules(ctx)
		for _, rule := range rules {
			if !rule.Active || strings.ToLower(rule.RuleType) != "ai_bot" {
				continue
			}
			applyAIBotDefaults(&rule)
			if strings.TrimSpace(rule.BotPrompt) == "" && strings.TrimSpace(rule.BotReferenceImage) == "" {
				// Misconfigured bot rule — do not silently skip BLOCK policies.
				if logstore.NormalizeGuardRuleAction(rule.Action) == "BLOCK" {
					logEntry.Action = "Blocked"
					logEntry.Status = fmt.Sprintf("Blocked (%s — AI Guard Bot misconfigured)", rule.Name)
					logEntry.RiskScore = 95
					logEntry.PredictiveRisk = "CRITICAL"
					logEntry.PredictedCategory = "AI_GUARD_BOT_MISCONFIGURED"
					logEntry.RuleTriggered = rule.Name
					ruleWarning = strings.TrimSpace(rule.WarningMessage)
					if ruleWarning == "" {
						ruleWarning = "AI Guard Bot rule is incomplete (evaluation prompt required)."
					}
					allowed = false
					isViolationBlock = true
					evalError = "ai guard bot misconfigured: evaluation prompt is required"
					securityVerdict = "misconfigured"
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
					break
				}
				continue
			}
			if skipAIBotRuleWithoutImages(rule.BotModel, rule.BotReferenceImage, payload.UploadImages) {
				continue
			}
			var violated bool
			var evalErr string
			if rulePatternMatches(rule, payload.Prompt) {
				violated = true
			} else {
				violated, evalErr = h.evaluateAIBotRule(rule, payload.Prompt, payload.UploadImages)
			}
			if evalErr != "" {
				evalError = evalErr
				ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
				// Evaluator errors must NOT block normal traffic — only a confirmed
				// violation from the model may block/warn. Log the error and allow.
				logEntry.Status = fmt.Sprintf("Allowed (%s — AI Guard Bot eval failed)", rule.Name)
				logEntry.PredictedCategory = "AI_GUARD_BOT_EVAL_ERROR"
				logEntry.RuleTriggered = rule.Name
				securityVerdict = "eval_failed"
				if ruleAction == "BLOCK" {
					evalError = evalErr + " (allowed — eval error does not block)"
				}
				_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
				continue
			}
			if violated {
				ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
				sevScore, sevLabel := logstore.GuardSeverityScore(rule.Severity)
				if ruleAction == "BLOCK" {
					logEntry.Action = "Blocked"
					logEntry.Status = fmt.Sprintf("Blocked (%s)", rule.Name)
					logEntry.RiskScore = sevScore
					if logEntry.RiskScore < 80 {
						logEntry.RiskScore = 90
					}
					logEntry.PredictiveRisk = sevLabel
					if logEntry.PredictiveRisk == "LOW" || logEntry.PredictiveRisk == "MEDIUM" {
						logEntry.PredictiveRisk = "HIGH"
					}
					logEntry.PredictedCategory = "AI_GUARD_BOT_VIOLATION"
					logEntry.RuleTriggered = rule.Name
					ruleWarning = strings.TrimSpace(rule.WarningMessage)
					if strings.Contains(strings.ToLower(ruleWarning), "evaluation failed") {
						ruleWarning = ""
					}
					if ruleWarning == "" {
						ruleWarning = "This request was blocked by UnifAI Guard."
					}
					allowed = false
					isViolationBlock = true
					evalError = ""
					securityVerdict = "violation"
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
					break
				} else if ruleAction == "REDACT" {
					logEntry.Action = "Redacted"
					logEntry.Status = fmt.Sprintf("Redacted (%s)", rule.Name)
					logEntry.RiskScore = sevScore
					if logEntry.RiskScore > 70 {
						logEntry.RiskScore = 65
					}
					if logEntry.RiskScore < 40 {
						logEntry.RiskScore = 50
					}
					logEntry.PredictiveRisk = "MEDIUM"
					if sevLabel == "CRITICAL" || sevLabel == "HIGH" {
						logEntry.PredictiveRisk = "HIGH"
					}
					logEntry.PredictedCategory = "AI_GUARD_BOT_REDACT"
					logEntry.RuleTriggered = rule.Name
					ruleWarning = strings.TrimSpace(rule.WarningMessage)
					evalError = ""
					securityVerdict = "warning"
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
				}
			} else {
				// Model said no violation — security policy met for this bot rule.
				aiBotCheckedOK = true
				if securityVerdict == "not_evaluated" || securityVerdict == "clear" || securityVerdict == "eval_failed" {
					securityVerdict = "clear"
					evalError = ""
				}
			}
		}
		if allowed && aiBotCheckedOK && securityVerdict == "clear" && logEntry.Action == "Allowed" {
			logEntry.Status = "Allowed (AI Guard Bot: security OK)"
			logEntry.PredictedCategory = "AI_GUARD_BOT_CLEAR"
			logEntry.RuleTriggered = ""
			_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
		} else if allowed && securityVerdict == "eval_failed" && logEntry.PredictedCategory != "AI_GUARD_BOT_EVAL_ERROR" {
			// Ensure Prompt Logs never look like "bot never ran" when evaluation failed.
			logEntry.Status = fmt.Sprintf("Allowed (%s — AI Guard Bot eval failed)", logEntry.RuleTriggered)
			if strings.TrimSpace(logEntry.RuleTriggered) == "" {
				logEntry.Status = "Allowed (AI Guard Bot eval failed)"
			}
			logEntry.PredictedCategory = "AI_GUARD_BOT_EVAL_ERROR"
			_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
		}
	}

	// What the browser AI receives on WARN: full prompt + warning. Logs keep the original only.
	forwardPrompt := payload.Prompt
	if logEntry.Action == "Warned" || logEntry.Action == "Redacted" {
		forwardPrompt = logstore.FormatWarnedForwardPrompt(payload.Prompt, ruleWarning)
	}

	replyText := ""
	replyProvider := ""
	replyModel := ""

	domainHint := ""
	if d, ok := payload.Metadata["domain"].(string); ok {
		domainHint = d
	}
	target, _ := h.manager.GetTargetByDomain(ctx, domainHint)
	replyMode := "violations"
	if target != nil {
		replyMode = strings.ToLower(strings.TrimSpace(target.ReplyBotMode))
		if replyMode != "all" {
			replyMode = "violations"
		}
	}
	botReady := target != nil &&
		target.ReplyBotEnabled &&
		strings.TrimSpace(target.ReplyBotProvider) != "" &&
		strings.TrimSpace(target.ReplyBotModel) != ""

	// "all" mode: Answer every prompt with Reply Bot (do not forward to the site AI).
	if allowed && botReady && replyMode == "all" {
		allowed = false
		logEntry.Action = "Bot Answered"
		logEntry.Status = "REPLIED"
	}

	if !allowed {
		if isViolationBlock {
			// Only the admin-authored rule warning — never a built-in template or Reply Bot rewrite.
			replyText = logstore.SecurityReplyForRule(logEntry.RuleTriggered, ruleWarning)
		} else if botReady {
			replyProvider = strings.TrimSpace(target.ReplyBotProvider)
			replyModel = strings.TrimSpace(target.ReplyBotModel)
			if generated, genErr := h.generateReplyBotText(ctx, replyProvider, replyModel, payload.Platform, logEntry.RuleTriggered, payload.Prompt, "answer"); genErr == nil && strings.TrimSpace(generated) != "" {
				replyText = strings.TrimSpace(generated)
			}
		}
		if strings.TrimSpace(replyText) == "" && !isViolationBlock {
			replyText = "UnifAI Reply Bot is enabled for this site, but no model response was returned. Please try again or check provider/model settings."
		}
		_ = h.manager.UpdateLogReplyBot(ctx, logEntry.ID, replyProvider, replyModel, replyText)
		logEntry.ReplyBotProvider = replyProvider
		logEntry.ReplyBotModel = replyModel
		logEntry.ReplyBotText = replyText
		if logEntry.Action == "Bot Answered" {
			_ = h.manager.UpdateLogActionStatus(ctx, logEntry.ID, logEntry.Action, logEntry.Status)
		}
	}

	SendJSON(ctx, map[string]any{
		"status":             "success",
		"allowed":            allowed,
		"action":             logEntry.Action,
		"rule_triggered":     logEntry.RuleTriggered,
		"warning_message":    ruleWarning,
		"redacted_prompt":    forwardPrompt, // proxy injects this into the chat request body
		"forward_prompt":     forwardPrompt,
		"risk_score":         logEntry.RiskScore,
		"predictive_risk":    logEntry.PredictiveRisk,
		"predicted_category": logEntry.PredictedCategory,
		"security_verdict":   securityVerdict,
		"security_message":   securityVerdictMessage(securityVerdict, logEntry.RuleTriggered),
		"reply_text":         replyText,
		"reply_bot_provider": replyProvider,
		"reply_bot_model":    replyModel,
		"eval_error":         evalError,
		"log":                logEntry,
	})
}

func getMetadataString(metadata map[string]any, key string) string {
	if metadata == nil {
		return ""
	}
	v, ok := metadata[key].(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(v)
}

func parseUploadImagesMetadata(metadata map[string]any) []string {
	if metadata == nil {
		return nil
	}
	raw, ok := metadata["upload_images"]
	if !ok || raw == nil {
		return nil
	}
	switch v := raw.(type) {
	case []string:
		out := make([]string, 0, len(v))
		for _, s := range v {
			if t := strings.TrimSpace(s); t != "" {
				out = append(out, t)
			}
		}
		return out
	case []any:
		out := make([]string, 0, len(v))
		for _, item := range v {
			if s, ok := item.(string); ok && strings.TrimSpace(s) != "" {
				out = append(out, strings.TrimSpace(s))
			}
		}
		return out
	default:
		return nil
	}
}

func rulePatternMatches(rule logstore.BrowserGuardRule, text string) bool {
	pattern := strings.TrimSpace(rule.Pattern)
	text = strings.TrimSpace(text)
	if pattern == "" || text == "" {
		return false
	}
	re, err := regexp.Compile("(?i)" + pattern)
	if err != nil {
		return false
	}
	return re.MatchString(text)
}

// evaluateGuardOnly runs regex + AI Guard Bot rules without persisting a log row (file-scan pre-check).
// Returns evalError/securityVerdict so the proxy never stamps a false "security OK".
func (h *BrowserAIHandler) evaluateGuardOnly(ctx *fasthttp.RequestCtx, prompt string, uploadImages []string) (allowed bool, action, ruleTriggered, ruleWarning, evalError, securityVerdict string) {
	allowed = true
	action = "Allowed"
	securityVerdict = "not_evaluated"
	prompt = strings.TrimSpace(prompt)
	rules, _ := h.manager.GetRules(ctx)
	for _, rule := range rules {
		if !rule.Active || strings.ToLower(rule.RuleType) == "ai_bot" || rule.Pattern == "" {
			continue
		}
		re, err := regexp.Compile("(?i)" + rule.Pattern)
		if err != nil || !re.MatchString(prompt) {
			continue
		}
		ruleTriggered = rule.Name
		ruleWarning = strings.TrimSpace(rule.WarningMessage)
		ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
		if ruleAction == "BLOCK" {
			return false, "Blocked", ruleTriggered, ruleWarning, "", "violation"
		}
		if ruleAction == "REDACT" {
			allowed = true
			action = "Redacted"
			securityVerdict = "warning"
		}
	}
	botCheckedOK := false
	for _, rule := range rules {
		if !rule.Active || strings.ToLower(rule.RuleType) != "ai_bot" {
			continue
		}
		applyAIBotDefaults(&rule)
		if strings.TrimSpace(rule.BotPrompt) == "" && strings.TrimSpace(rule.BotReferenceImage) == "" {
			continue
		}
		if skipAIBotRuleWithoutImages(rule.BotModel, rule.BotReferenceImage, uploadImages) {
			continue
		}
		violated := rulePatternMatches(rule, prompt)
		var evalErr string
		if !violated {
			violated, evalErr = h.evaluateAIBotRule(rule, prompt, uploadImages)
		}
		if evalErr != "" {
			evalError = evalErr
			securityVerdict = "eval_failed"
			if ruleTriggered == "" {
				ruleTriggered = rule.Name
			}
			continue
		}
		if !violated {
			botCheckedOK = true
			if securityVerdict == "not_evaluated" || securityVerdict == "clear" || securityVerdict == "eval_failed" {
				securityVerdict = "clear"
				evalError = ""
			}
			continue
		}
		ruleTriggered = rule.Name
		ruleWarning = strings.TrimSpace(rule.WarningMessage)
		ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
		evalError = ""
		if ruleAction == "BLOCK" {
			return false, "Blocked", ruleTriggered, ruleWarning, "", "violation"
		}
		if ruleAction == "REDACT" {
			allowed = true
			action = "Redacted"
			securityVerdict = "warning"
			botCheckedOK = true
		}
	}
	if botCheckedOK && securityVerdict == "eval_failed" {
		securityVerdict = "clear"
		evalError = ""
	}
	return allowed, action, ruleTriggered, ruleWarning, evalError, securityVerdict
}

func metadataBool(metadata map[string]any, key string) bool {
	if metadata == nil {
		return false
	}
	v, ok := metadata[key]
	if !ok || v == nil {
		return false
	}
	switch t := v.(type) {
	case bool:
		return t
	case string:
		s := strings.ToLower(strings.TrimSpace(t))
		return s == "1" || s == "true" || s == "yes"
	case float64:
		return t != 0
	case int:
		return t != 0
	default:
		return false
	}
}

func securityVerdictCategory(verdict string) string {
	switch verdict {
	case "clear":
		return "AI_GUARD_BOT_CLEAR"
	case "violation":
		return "AI_GUARD_BOT_VIOLATION"
	case "warning":
		return "AI_GUARD_BOT_REDACT"
	case "eval_failed":
		return "AI_GUARD_BOT_EVAL_ERROR"
	case "misconfigured":
		return "AI_GUARD_BOT_MISCONFIGURED"
	default:
		return ""
	}
}

func guardActionRank(action string) int {
	switch strings.ToLower(strings.TrimSpace(action)) {
	case "blocked", "block":
		return 3
	case "redacted", "redact", "warned", "warn":
		return 2
	default:
		return 1
	}
}

// applyScanGuardFromMetadata uses the proxy's guard scan result (regex + bot already evaluated on Send).
func (h *BrowserAIHandler) applyScanGuardFromMetadata(ctx *fasthttp.RequestCtx, logEntry *logstore.BrowserAILog, metadata map[string]any, ruleWarning *string) bool {
	if logEntry == nil || metadata == nil {
		return false
	}
	decided := metadataBool(metadata, "scan_guard_decided")
	if !decided {
		return false
	}
	// Proxy marked "evaluated" but bot actually failed — do not stamp security OK; re-run below.
	if evalErr := getMetadataString(metadata, "scan_guard_eval_error"); evalErr != "" {
		return false
	}
	action := strings.TrimSpace(getMetadataString(metadata, "scan_guard_action"))
	if action == "" {
		return false
	}
	// Keep stricter InterceptPrompt regex result — never downgrade Blocked/Redacted to Allowed.
	if guardActionRank(logEntry.Action) > guardActionRank(action) {
		return true
	}
	if logEntry.Action == "Blocked" {
		return true
	}
	ruleName := getMetadataString(metadata, "scan_rule_triggered")
	warn := getMetadataString(metadata, "scan_warning_message")

	switch strings.ToLower(action) {
	case "blocked", "block":
		logEntry.Action = "Blocked"
		if ruleName != "" {
			logEntry.Status = fmt.Sprintf("Blocked (%s)", ruleName)
		} else {
			logEntry.Status = "Blocked (Guard Rule)"
		}
		logEntry.RuleTriggered = ruleName
		logEntry.RiskScore = 90
		logEntry.PredictiveRisk = "HIGH"
		logEntry.PredictedCategory = "AI_GUARD_BOT_VIOLATION"
	case "redacted", "redact", "warned", "warn":
		logEntry.Action = "Redacted"
		if ruleName != "" {
			logEntry.Status = fmt.Sprintf("Redacted (%s)", ruleName)
		} else {
			logEntry.Status = "Redacted (Guard Rule)"
		}
		logEntry.RuleTriggered = ruleName
		logEntry.RiskScore = 65
		logEntry.PredictiveRisk = "MEDIUM"
		logEntry.PredictedCategory = "AI_GUARD_BOT_REDACT"
	default:
		logEntry.Action = "Allowed"
		logEntry.Status = "Allowed (AI Guard Bot: security OK)"
		logEntry.RuleTriggered = ""
		logEntry.PredictedCategory = "AI_GUARD_BOT_CLEAR"
	}
	if warn != "" && ruleWarning != nil {
		*ruleWarning = warn
	}
	_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
	return true
}

// runAIBotOnLogEntry evaluates active AI Guard Bot rules against file/voice extracted content.
func (h *BrowserAIHandler) runAIBotOnLogEntry(ctx *fasthttp.RequestCtx, logEntry *logstore.BrowserAILog, content string, uploadImages []string, ruleWarning *string) {
	if logEntry == nil || logEntry.Action == "Blocked" {
		return
	}
	content = strings.TrimSpace(content)
	if content == "" && len(uploadImages) == 0 {
		return
	}
	rules, _ := h.manager.GetRules(ctx)
	anyClear := false
	for _, rule := range rules {
		if !rule.Active || strings.ToLower(rule.RuleType) != "ai_bot" {
			continue
		}
		applyAIBotDefaults(&rule)
		if strings.TrimSpace(rule.BotPrompt) == "" && strings.TrimSpace(rule.BotReferenceImage) == "" {
			continue
		}
		if skipAIBotRuleWithoutImages(rule.BotModel, rule.BotReferenceImage, uploadImages) {
			continue
		}
		var violated bool
		var evalErr string
		if rulePatternMatches(rule, content) {
			violated = true
		} else {
			violated, evalErr = h.evaluateAIBotRule(rule, content, uploadImages)
		}
		if evalErr != "" {
			if logEntry.Action == "Allowed" {
				logEntry.Status = fmt.Sprintf("Allowed (%s — AI Guard Bot eval failed)", rule.Name)
				logEntry.PredictedCategory = "AI_GUARD_BOT_EVAL_ERROR"
				logEntry.RuleTriggered = rule.Name
				_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
			}
			continue
		}
		if !violated {
			if logEntry.Action == "Allowed" {
				anyClear = true
			}
			continue
		}
		ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
		sevScore, sevLabel := logstore.GuardSeverityScore(rule.Severity)
		if ruleAction == "BLOCK" {
			logEntry.Action = "Blocked"
			logEntry.Status = fmt.Sprintf("Blocked (%s)", rule.Name)
			logEntry.RiskScore = sevScore
			if logEntry.RiskScore < 80 {
				logEntry.RiskScore = 90
			}
			logEntry.PredictiveRisk = sevLabel
			logEntry.PredictedCategory = "AI_GUARD_BOT_VIOLATION"
			logEntry.RuleTriggered = rule.Name
			if ruleWarning != nil {
				*ruleWarning = strings.TrimSpace(rule.WarningMessage)
			}
			_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
			return
		}
		if ruleAction == "REDACT" {
			logEntry.Action = "Redacted"
			logEntry.Status = fmt.Sprintf("Redacted (%s)", rule.Name)
			logEntry.RiskScore = sevScore
			logEntry.PredictedCategory = "AI_GUARD_BOT_REDACT"
			logEntry.RuleTriggered = rule.Name
			if ruleWarning != nil {
				*ruleWarning = strings.TrimSpace(rule.WarningMessage)
			}
			_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
		}
	}
	if anyClear && logEntry.Action == "Allowed" {
		logEntry.Status = "Allowed (AI Guard Bot: security OK)"
		logEntry.PredictedCategory = "AI_GUARD_BOT_CLEAR"
		logEntry.RuleTriggered = ""
		_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
	}
}

// interceptFile accepts multipart metadata + optional file bytes from Guard/proxy.
// Filename + extracted text are permanent in Prompt Logs.
// File bytes are stored temporarily (~10 minutes) for View/Download, then deleted.
func (h *BrowserAIHandler) interceptFile(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)

	form, err := ctx.MultipartForm()
	if err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "expected multipart form")
		return
	}

	getForm := func(key string) string {
		if form.Value == nil {
			return ""
		}
		vals := form.Value[key]
		if len(vals) == 0 {
			return ""
		}
		return strings.TrimSpace(vals[0])
	}

	platform := getForm("platform")
	prompt := getForm("prompt")
	clientIP := getForm("client_ip")
	agentID := getForm("agent_id")
	agentHostname := getForm("agent_hostname")
	metaRaw := getForm("metadata")
	contentTypeHint := getForm("content_type")

	metadata := map[string]any{}
	if metaRaw != "" {
		_ = sonic.Unmarshal([]byte(metaRaw), &metadata)
	}
	if metadata == nil {
		metadata = map[string]any{}
	}
	if clientIP == "" {
		clientIP = ctx.RemoteIP().String()
	}
	if platform == "" {
		platform = "Browser AI"
	}
	if agentID != "" {
		metadata["agent_id"] = agentID
	}
	if agentHostname != "" {
		metadata["agent_hostname"] = agentHostname
	}
	metadata["upload_scan"] = true

	fileName := getForm("file_name")
	if fileName != "" {
		metadata["file_name"] = fileName
	}
	if prompt == "" {
		if fileName != "" {
			prompt = "[FILE UPLOAD] " + fileName
		} else {
			prompt = "[FILE UPLOAD] attachment"
		}
	}

	// Optional file part for temp View (does not affect extract/predict — already done on proxy).
	uploadName, uploadBytes, uploadErr := readMultipartUploadFile(form.File)
	if uploadErr != nil {
		// Keep logging even if temp file store is rejected (size etc.)
		uploadBytes = nil
	}
	if fileName == "" && uploadName != "" {
		fileName = uploadName
		metadata["file_name"] = fileName
	}

	logEntry, ruleWarning, err := h.manager.InterceptPrompt(ctx, platform, prompt, clientIP, metadata)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}

	extractedText := strings.TrimSpace(getMetadataString(metadata, "extracted_text"))
	uploadImages := parseUploadImagesMetadata(metadata)
	scanApplied := h.applyScanGuardFromMetadata(ctx, logEntry, metadata, &ruleWarning)
	if !scanApplied && logEntry.Action != "Blocked" && (extractedText != "" || len(uploadImages) > 0) {
		h.runAIBotOnLogEntry(ctx, logEntry, extractedText, uploadImages, &ruleWarning)
	}

	safeName := sanitizeAttachmentFileName(fileName)
	if safeName != "" {
		logEntry.AttachmentName = safeName
		// Permanent filename on the log (even if temp file store is skipped).
		_ = h.manager.UpdateLogAttachment(ctx, logEntry.ID, safeName, "", contentTypeHint)
	}

	if len(uploadBytes) >= 32 {
		stored, ctype, storeErr := storeBrowserAIAttachment(logEntry.ID, safeName, uploadBytes, contentTypeHint)
		if storeErr == nil && stored != "" {
			if err := h.manager.UpdateLogAttachment(ctx, logEntry.ID, safeName, stored, ctype); err == nil {
				logEntry.AttachmentStoredName = stored
				logEntry.AttachmentContentType = ctype
				logEntry.AttachmentName = safeName
			}
		}
	}

	// Opportunistic cleanup of expired temp files
	go purgeExpiredBrowserAIAttachments(h.manager)

	SendJSON(ctx, map[string]any{
		"status":          "success",
		"allowed":         logEntry.Action == "Allowed" || logEntry.Action == "Warned" || logEntry.Action == "Redacted",
		"action":          logEntry.Action,
		"rule_triggered":  logEntry.RuleTriggered,
		"warning_message": ruleWarning,
		"log":             logEntry,
	})
}

func (h *BrowserAIHandler) getAttachment(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id := ctx.UserValue("id")
	idStr, _ := id.(string)
	idStr = strings.TrimSpace(idStr)
	if idStr == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "missing attachment id")
		return
	}
	logEntry, err := h.manager.GetLogByID(ctx, idStr)
	if err != nil || logEntry == nil {
		SendError(ctx, fasthttp.StatusNotFound, "attachment not found")
		return
	}
	name := strings.TrimSpace(logEntry.AttachmentName)
	if name == "" {
		name = "attachment"
	}
	stored := strings.TrimSpace(logEntry.AttachmentStoredName)
	if stored == "" {
		SendError(ctx, fasthttp.StatusGone, "file expired (available for 10 minutes only); log and filename remain")
		return
	}
	path, err := resolveBrowserAIAttachmentPath(stored)
	if err != nil {
		_ = h.manager.ClearLogAttachmentFile(ctx, logEntry.ID)
		SendError(ctx, fasthttp.StatusGone, "file expired (available for 10 minutes only); log and filename remain")
		return
	}
	if browserAIAttachmentExpired(path) {
		_ = os.Remove(path)
		_ = h.manager.ClearLogAttachmentFile(ctx, logEntry.ID)
		SendError(ctx, fasthttp.StatusGone, "file expired (available for 10 minutes only); log and filename remain")
		return
	}
	data, err := os.ReadFile(path)
	if err != nil {
		_ = h.manager.ClearLogAttachmentFile(ctx, logEntry.ID)
		SendError(ctx, fasthttp.StatusGone, "file expired (available for 10 minutes only); log and filename remain")
		return
	}
	ctype := sniffAttachmentContentType(data, name, logEntry.AttachmentContentType)
	if len(data) >= 5 && string(data[:5]) == "%PDF-" {
		ctype = "application/pdf"
	} else if len(data) > 0 && (data[0] == '{' || data[0] == '[') {
		ctype = "application/json; charset=utf-8"
	}
	if ctype == "" {
		ctype = "application/octet-stream"
	}
	download := string(ctx.QueryArgs().Peek("download")) == "1" ||
		strings.EqualFold(string(ctx.QueryArgs().Peek("download")), "true")

	ctx.SetStatusCode(fasthttp.StatusOK)
	ctx.SetContentType(ctype)
	ctx.Response.Header.Set("Cache-Control", "private, max-age=60")
	if download {
		ctx.Response.Header.Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, strings.ReplaceAll(name, `"`, "")))
	} else {
		ctx.Response.Header.Set("Content-Disposition", fmt.Sprintf(`inline; filename="%s"`, strings.ReplaceAll(name, `"`, "")))
	}
	ctx.SetBody(data)
}

type aiBotEvalResult struct {
	Violation   bool   `json:"violation"`
	Reason      string `json:"reason"`
	Explanation string `json:"explanation"`
}

func evaluatorChoiceText(resp *schemas.UnifAIChatResponse) string {
	if resp == nil || len(resp.Choices) == 0 || resp.Choices[0].Message.Content == nil {
		return ""
	}
	c := resp.Choices[0].Message.Content
	if c.ContentStr != nil {
		return strings.TrimSpace(*c.ContentStr)
	}
	var b strings.Builder
	for _, block := range c.ContentBlocks {
		if block.Text != nil {
			b.WriteString(*block.Text)
		}
	}
	return strings.TrimSpace(b.String())
}

func securityVerdictMessage(verdict, ruleName string) string {
	switch verdict {
	case "clear":
		if ruleName != "" {
			return "Security OK — AI Guard Bot found no policy violation (" + ruleName + ")."
		}
		return "Security OK — AI Guard Bot found no policy violation."
	case "violation":
		if ruleName != "" {
			return "Security NOT met — prompt violates AI Guard Bot policy (" + ruleName + "). Blocked."
		}
		return "Security NOT met — prompt violates AI Guard Bot policy. Blocked."
	case "warning":
		if ruleName != "" {
			return "Security warning — prompt matched AI Guard Bot policy (" + ruleName + "). Allowed with warning."
		}
		return "Security warning — prompt matched AI Guard Bot policy. Allowed with warning."
	case "eval_failed":
		return "Security check failed — AI Guard Bot could not evaluate this prompt."
	case "misconfigured":
		return "Security check failed — AI Guard Bot rule is incomplete (provider/model/prompt)."
	default:
		return ""
	}
}

// testAIGuardBot dry-runs an AI Guard Bot policy against a sample prompt (admin only).
func (h *BrowserAIHandler) testAIGuardBot(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var payload struct {
		BotProvider  string `json:"bot_provider"`
		BotModel     string `json:"bot_model"`
		BotPrompt    string `json:"bot_prompt"`
		SamplePrompt string `json:"sample_prompt"`
		Action       string `json:"action"`
		Name         string `json:"name"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid JSON payload")
		return
	}
	if strings.TrimSpace(payload.BotPrompt) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "bot_prompt is required")
		return
	}
	sample := strings.TrimSpace(payload.SamplePrompt)
	if sample == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "sample_prompt is required")
		return
	}
	rule := logstore.BrowserGuardRule{
		Name:        strings.TrimSpace(payload.Name),
		RuleType:    "ai_bot",
		BotProvider: strings.TrimSpace(payload.BotProvider),
		BotModel:    strings.TrimSpace(payload.BotModel),
		BotPrompt:   strings.TrimSpace(payload.BotPrompt),
		Action:      logstore.NormalizeGuardRuleAction(payload.Action),
		Active:      true,
	}
	if rule.Name == "" {
		rule.Name = "Test AI Guard Bot"
	}
	applyAIBotDefaults(&rule)
	violated, evalErr := h.evaluateAIBotRule(rule, sample, nil)
	verdict := "clear"
	message := securityVerdictMessage("clear", rule.Name)
	wouldBlock := false
	wouldWarn := false
	if evalErr != "" {
		verdict = "eval_failed"
		message = securityVerdictMessage("eval_failed", rule.Name) + " " + evalErr
		message += " (live traffic is allowed — only confirmed violations block.)"
	} else if violated {
		if rule.Action == "REDACT" || rule.Action == "WARN" {
			verdict = "redact"
			wouldWarn = true
			message = securityVerdictMessage("redact", rule.Name)
		} else {
			verdict = "violation"
			wouldBlock = true
			message = securityVerdictMessage("violation", rule.Name)
		}
	}
	SendJSON(ctx, map[string]any{
		"status":            "success",
		"violation":         violated && evalErr == "",
		"security_verdict":  verdict,
		"security_message":  message,
		"security_met":      verdict == "clear",
		"would_block":       wouldBlock,
		"would_warn":        wouldWarn,
		"eval_error":        evalErr,
		"rule_name":         rule.Name,
		"bot_provider":      rule.BotProvider,
		"bot_model":         rule.BotModel,
	})
}

// generateRegexFromPolicy turns a security-policy prompt into a RE2 regex
// using Download (Ollama) or Outsource (configured Model Providers) models.
func (h *BrowserAIHandler) generateRegexFromPolicy(ctx *fasthttp.RequestCtx) {
	var payload struct {
		BotProvider string `json:"bot_provider"`
		BotModel    string `json:"bot_model"`
		BotPrompt   string `json:"bot_prompt"`
	}
	if err := sonic.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid JSON payload")
		return
	}
	policy := strings.TrimSpace(payload.BotPrompt)
	if policy == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "bot_prompt is required")
		return
	}
	provider := strings.TrimSpace(payload.BotProvider)
	model := strings.TrimSpace(payload.BotModel)
	if provider == "" {
		provider = browserAIGuardBotDefaultProvider
	}
	if model == "" {
		model = browserAIGuardBotDefaultModel
	}
	provider, model = applyGuardBotDefaults(provider, model)
	providerName, modelName := resolveGuardBotModel(provider, model)
	provider = string(providerName)
	model = modelName

	// Vision-only models are poor at regex generation — prefer text chat models.
	if isVisionOnlyGuardModelName(model) {
		SendError(ctx, fasthttp.StatusBadRequest, "pick a text model (e.g. llama3.2) to generate regex — vision models are for images")
		return
	}

	// Fast path: common policies → known-good RE2 patterns (do not trust weak model output).
	if pattern, focus, notes, ok := heuristicRegexFromPolicy(policy); ok {
		SendJSON(ctx, map[string]any{
			"status":   "success",
			"pattern":  pattern,
			"focus":    focus,
			"notes":    notes,
			"model":    model,
			"provider": provider,
			"source":   "heuristic",
		})
		return
	}

	systemPrompt := `You are a regex generator for a DLP engine (Go RE2).

Return ONLY one JSON object:
{"pattern":"<regex>","focus":"<short>","notes":"<short>"}

HARD RULES for "pattern":
- Must be a REAL regular expression that can match text (digits, words, emails, keys, etc.).
- NEVER invent fake patterns like []word[] or empty [].
- NEVER output English sentences as the pattern.
- Prefer \b, \d, [A-Za-z], |, (), {n,m}.
- No lookbehind/lookahead, no backreferences (RE2).
- Keep pattern under 200 characters.
- Case folding is applied by the engine (?i), so do not rely on case.

Examples:
Policy "mobile number" / "phone" → {"pattern":"\\b(?:\\+?91[\\s-]*)?[6-9]\\d{9}\\b","focus":"Indian mobile","notes":"Edit if you need other country formats"}
Policy "email" → {"pattern":"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b","focus":"email","notes":""}
Policy "openai api key" → {"pattern":"\\bsk-[A-Za-z0-9]{20,}\\b","focus":"OpenAI API key","notes":""}

If unsure, return a tight keyword alternation with word boundaries, e.g. \b(salary|ctc|payslip)\b`

	userMsg := fmt.Sprintf(
		"SECURITY_POLICY:\n%s\n\nJSON only. pattern must be a valid RE2 regex string.",
		truncateRunes(policy, 8000),
	)

	var raw string
	var genErr error
	genSource := "ollama"

	if isOllamaGuardProvider(provider) {
		runOnce := func(jsonMode bool) (string, error) {
			return callOllamaChatAny(model, systemPrompt, userMsg, jsonMode, 90*time.Second)
		}
		raw, genErr = runOnce(true)
		if genErr != nil || strings.TrimSpace(raw) == "" {
			raw2, err2 := runOnce(false)
			if err2 == nil && strings.TrimSpace(raw2) != "" {
				raw, genErr = raw2, nil
			} else if genErr == nil {
				genErr = err2
			} else if err2 != nil {
				genErr = fmt.Errorf("%v; retry: %v", genErr, err2)
			}
		}
	} else {
		genSource = "outsource"
		if h.client == nil {
			SendError(ctx, fasthttp.StatusBadGateway, "unifai client not available for outsource model")
			return
		}
		maxTokens := 256
		temp := 0.0
		responseFormat := any(map[string]any{"type": "json_object"})
		unifaiReq := &schemas.UnifAIChatRequest{
			Provider: schemas.ModelProvider(provider),
			Model:    model,
			Input: []schemas.ChatMessage{
				{
					Role: schemas.ChatMessageRoleSystem,
					Content: &schemas.ChatMessageContent{
						ContentStr: schemas.Ptr(systemPrompt),
					},
				},
				{
					Role: schemas.ChatMessageRoleUser,
					Content: &schemas.ChatMessageContent{
						ContentStr: schemas.Ptr(userMsg),
					},
				},
			},
			Params: &schemas.ChatParameters{
				MaxCompletionTokens: &maxTokens,
				Temperature:         &temp,
				ResponseFormat:      &responseFormat,
			},
		}
		runOutsource := func() (string, error) {
			deadline := time.Now().Add(45 * time.Second)
			unifaiCtx := schemas.NewUnifAIContext(context.Background(), deadline)
			unifaiCtx.SetValue(schemas.UnifAIContextKeySkipBudgetAndRateLimits, true)
			unifaiCtx.SetValue(schemas.UnifAIContextKeySkipPluginPipeline, true)
			resp, unifaiErr := h.client.ChatCompletionRequest(unifaiCtx, unifaiReq)
			if unifaiErr != nil {
				return "", fmt.Errorf("%s", unifaiErrorMessage(unifaiErr))
			}
			return evaluatorChoiceText(resp), nil
		}
		raw, genErr = runOutsource()
		if genErr != nil || strings.TrimSpace(raw) == "" {
			if unifaiReq.Params != nil {
				unifaiReq.Params.ResponseFormat = nil
			}
			raw2, err2 := runOutsource()
			if err2 == nil && strings.TrimSpace(raw2) != "" {
				raw, genErr = raw2, nil
			} else if genErr == nil {
				genErr = err2
			} else if err2 != nil {
				genErr = fmt.Errorf("%v; retry: %v", genErr, err2)
			}
		}
	}

	if genErr != nil || strings.TrimSpace(raw) == "" {
		msg := "generate-regex failed"
		if genErr != nil {
			msg = genErr.Error()
		}
		if fb, fFocus, fNotes, ok := fallbackKeywordRegex(policy); ok {
			SendJSON(ctx, map[string]any{
				"status":   "success",
				"pattern":  fb,
				"focus":    fFocus,
				"notes":    fNotes + " (model failed: " + truncateRunes(msg, 80) + ")",
				"model":    model,
				"provider": provider,
				"source":   "fallback",
			})
			return
		}
		SendError(ctx, fasthttp.StatusBadGateway, "generate-regex failed: "+truncateRunes(msg, 180))
		return
	}
	raw = stripEvalMarkdown(strings.TrimSpace(raw))
	pattern, focus, notes := parseGeneratedRegexPayload(raw)
	pattern = sanitizeGeneratedRegex(pattern)
	if !isUsableGeneratedRegex(pattern) {
		if fb, fFocus, fNotes, ok := heuristicRegexFromPolicy(policy); ok {
			SendJSON(ctx, map[string]any{
				"status":   "success",
				"pattern":  fb,
				"focus":    fFocus,
				"notes":    fNotes + " (model output was not a usable regex; used built-in pattern)",
				"model":    model,
				"provider": provider,
				"source":   "heuristic",
			})
			return
		}
		if fb, fFocus, fNotes, ok := fallbackKeywordRegex(policy); ok {
			SendJSON(ctx, map[string]any{
				"status":   "success",
				"pattern":  fb,
				"focus":    fFocus,
				"notes":    fNotes + " (model output was not a usable regex)",
				"model":    model,
				"provider": provider,
				"source":   "fallback",
			})
			return
		}
		SendError(ctx, fasthttp.StatusBadGateway, "model did not return a usable regex pattern — try a clearer policy (e.g. \"block Indian 10-digit mobile numbers\")")
		return
	}
	if focus == "" {
		focus = "policy match"
	}
	SendJSON(ctx, map[string]any{
		"status":   "success",
		"pattern":  pattern,
		"focus":    focus,
		"notes":    notes,
		"model":    model,
		"provider": provider,
		"source":   genSource,
	})
}

func isVisionOnlyGuardModelName(model string) bool {
	m := strings.ToLower(strings.TrimSpace(model))
	if strings.Contains(m, "gemma4") || strings.Contains(m, "gemma-4") {
		return false
	}
	return strings.Contains(m, "llava") || strings.Contains(m, "vision") || strings.Contains(m, "bakllava")
}

func sanitizeGeneratedRegex(pattern string) string {
	pattern = strings.TrimSpace(pattern)
	pattern = strings.Trim(pattern, "`\"'")
	pattern = strings.TrimPrefix(pattern, "(?i)")
	pattern = strings.TrimPrefix(pattern, "(?m)")
	pattern = strings.TrimSpace(pattern)
	return pattern
}

func isUsableGeneratedRegex(pattern string) bool {
	pattern = strings.TrimSpace(pattern)
	if pattern == "" || len(pattern) < 2 || len(pattern) > 400 {
		return false
	}
	// Reject garbage like []direct[]and[]dial[]
	if strings.Contains(pattern, "[]") {
		return false
	}
	if strings.Count(pattern, " ") > 8 && !strings.ContainsAny(pattern, `\[\].*+?{}|()\\`) {
		return false // looks like a sentence, not a regex
	}
	lower := strings.ToLower(pattern)
	for _, bad := range []string{"http://", "https://", "return ", "policy", "you should"} {
		if strings.Contains(lower, bad) {
			return false
		}
	}
	if _, err := regexp.Compile("(?i)" + pattern); err != nil {
		return false
	}
	// Must have at least one "regex-ish" token or a simple word with boundaries
	hasMeta := strings.ContainsAny(pattern, `\.*+?[]{}|()^$`)
	if !hasMeta {
		// plain keyword ok if single token-ish
		if strings.Contains(pattern, " ") {
			return false
		}
	}
	return true
}

func heuristicRegexFromPolicy(policy string) (pattern, focus, notes string, ok bool) {
	p := strings.ToLower(strings.TrimSpace(policy))
	p = strings.ReplaceAll(p, "-", " ")
	p = strings.ReplaceAll(p, "_", " ")

	switch {
	case strings.Contains(p, "mobile") || strings.Contains(p, "phone") || strings.Contains(p, "cell"):
		// Indian mobiles + optional +91; also generic 10–12 digit runs
		return `\b(?:\+?91[\s-]*)?[6-9]\d{9}\b|\b\d{10,12}\b`,
			"mobile / phone number",
			"Matches Indian 10-digit mobiles (optional +91) and generic 10–12 digit numbers. Edit if too broad.",
			true
	case strings.Contains(p, "aadhaar") || strings.Contains(p, "aadhar") || strings.Contains(p, "uidai"):
		return `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b`, "Aadhaar number", "12-digit Aadhaar-like pattern.", true
	case strings.Contains(p, "pan") && (strings.Contains(p, "card") || strings.Contains(p, "income") || len(p) < 20):
		return `\b[A-Z]{5}\d{4}[A-Z]\b`, "PAN", "Indian PAN format.", true
	case strings.Contains(p, "email") || strings.Contains(p, "e-mail"):
		return `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`, "email address", "", true
	case strings.Contains(p, "salary") || strings.Contains(p, "ctc") || strings.Contains(p, "payslip") || strings.Contains(p, "payroll"):
		return `\b(salary|ctc|payslip|payroll|compensation|take[\s-]?home)\b`, "salary / payroll terms", "Keyword match — tighten if needed.", true
	case strings.Contains(p, "api key") || strings.Contains(p, "openai") || strings.Contains(p, "sk-"):
		return `\bsk-[A-Za-z0-9]{20,}\b`, "OpenAI-style API key", "", true
	case strings.Contains(p, "credit card") || strings.Contains(p, "card number"):
		return `\b(?:\d[ -]*?){13,19}\b`, "card-like digit run", "Broad digit pattern — review before production.", true
	default:
		return "", "", "", false
	}
}

func fallbackKeywordRegex(policy string) (pattern, focus, notes string, ok bool) {
	policy = strings.TrimSpace(policy)
	if policy == "" {
		return "", "", "", false
	}
	// Take up to 6 meaningful words
	reWord := regexp.MustCompile(`[A-Za-z][A-Za-z0-9]{1,32}`)
	words := reWord.FindAllString(policy, 8)
	uniq := make([]string, 0, 6)
	seen := map[string]bool{}
	for _, w := range words {
		lw := strings.ToLower(w)
		if len(lw) < 3 || seen[lw] {
			continue
		}
		switch lw {
		case "the", "and", "for", "with", "from", "that", "this", "block", "detect", "policy", "number", "numbers":
			continue
		}
		seen[lw] = true
		uniq = append(uniq, regexp.QuoteMeta(lw))
		if len(uniq) >= 6 {
			break
		}
	}
	if len(uniq) == 0 {
		return "", "", "", false
	}
	pattern = `\b(?:` + strings.Join(uniq, "|") + `)\b`
	if _, err := regexp.Compile("(?i)" + pattern); err != nil {
		return "", "", "", false
	}
	return pattern, "policy keywords", "Simple keyword regex from your policy text. Edit for better accuracy.", true
}

func parseGeneratedRegexPayload(raw string) (pattern, focus, notes string) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", "", ""
	}
	var obj struct {
		Pattern string `json:"pattern"`
		Focus   string `json:"focus"`
		Notes   string `json:"notes"`
		Regex   string `json:"regex"`
	}
	if err := sonic.Unmarshal([]byte(raw), &obj); err == nil {
		pattern = strings.TrimSpace(obj.Pattern)
		if pattern == "" {
			pattern = strings.TrimSpace(obj.Regex)
		}
		return pattern, strings.TrimSpace(obj.Focus), strings.TrimSpace(obj.Notes)
	}
	// Fallback: extract "pattern":"..."
	re := regexp.MustCompile(`(?i)"pattern"\s*:\s*"((?:\\.|[^"\\])*)"`)
	if m := re.FindStringSubmatch(raw); len(m) > 1 {
		pattern = m[1]
		pattern = strings.ReplaceAll(pattern, `\\`, `\`)
		pattern = strings.ReplaceAll(pattern, `\"`, `"`)
		return strings.TrimSpace(pattern), "", ""
	}
	// Last resort: first non-empty line that looks like a usable regex
	for _, line := range strings.Split(raw, "\n") {
		line = sanitizeGeneratedRegex(line)
		if line == "" || strings.HasPrefix(line, "{") {
			continue
		}
		if isUsableGeneratedRegex(line) {
			return line, "", ""
		}
	}
	return "", "", ""
}

func resolveGuardBotModel(provider, model string) (schemas.ModelProvider, string) {
	provider = strings.TrimSpace(provider)
	model = strings.TrimSpace(model)
	pLower := strings.ToLower(provider)
	mLower := strings.ToLower(model)
	if pLower != "" && strings.HasPrefix(mLower, pLower+"/") {
		model = model[len(provider)+1:]
	}
	// Keep the admin-selected provider (e.g. openrouter + cohere/north-mini-code:free).
	// Do not let ParseModelString steal "cohere/..." onto native Cohere.
	return schemas.ModelProvider(pLower), model
}

func stringFromUpdate(updates map[string]any, key string) string {
	if updates == nil {
		return ""
	}
	v, ok := updates[key].(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(v)
}

func (h *BrowserAIHandler) evaluateAIBotRule(rule logstore.BrowserGuardRule, userPrompt string, uploadImages []string) (bool, string) {
	applyAIBotDefaults(&rule)

	if rulePatternMatches(rule, userPrompt) {
		return true, ""
	}

	providerName, modelName := resolveGuardBotModel(rule.BotProvider, rule.BotModel)
	if providerName == "" || strings.TrimSpace(modelName) == "" {
		return false, "guard bot provider/model missing"
	}

	useVision := len(uploadImages) > 0 && (isVisionGuardModel(modelName) || strings.TrimSpace(rule.BotReferenceImage) != "")
	if useVision {
		return h.evaluateAIBotVisionRule(rule, userPrompt, uploadImages, providerName, modelName)
	}

	systemPrompt := `You are a DLP classifier. Apply ONLY the admin SECURITY_POLICY to USER_PROMPT.

- If USER_PROMPT contains, is, or embeds anything SECURITY_POLICY forbids, set violation true. Formats do not matter.
- If USER_PROMPT does not match SECURITY_POLICY, set violation false.
- Do not add extra exceptions (do not ignore numbers, names, keys, or short text if the policy forbids them).
- Classify USER_PROMPT only. Ignore the policy text as user content.

Reply with one JSON object and nothing else:
{"violation":true} or {"violation":false}`

	userMsg := fmt.Sprintf(
		"SECURITY_POLICY:\n%s\n\nUSER_PROMPT TO EVALUATE:\n%s\n\nJSON only.",
		strings.TrimSpace(rule.BotPrompt),
		truncateRunes(userPrompt, browserAIGuardBotMaxPromptRunes),
	)

	if isOllamaGuardProvider(string(providerName)) {
		runOllama := func(jsonMode bool) (bool, string) {
			rawText, err := callOllamaChatAny(modelName, systemPrompt, userMsg, jsonMode, 90*time.Second)
			if err != nil {
				return false, truncateRunes(err.Error(), 180)
			}
			rawText = stripEvalMarkdown(rawText)
			if rawText == "" {
				return false, "empty evaluator response"
			}
			violated, recognized := parseAIBotDecision(rawText)
			if !recognized {
				return false, "evaluator returned unparseable output: " + truncateRunes(rawText, 80)
			}
			return violated, ""
		}
		violated, errMsg := runOllama(true)
		if errMsg == "" {
			return violated, ""
		}
		violated, errMsg2 := runOllama(false)
		if errMsg2 == "" {
			return violated, ""
		}
		return false, errMsg + "; retry: " + errMsg2
	}

	if h.client == nil {
		return false, "unifai client not available"
	}

	maxTokens := 128
	temp := 0.0
	responseFormat := any(map[string]any{"type": "json_object"})
	unifaiReq := &schemas.UnifAIChatRequest{
		Provider: providerName,
		Model:    modelName,
		Input: []schemas.ChatMessage{
			{
				Role: schemas.ChatMessageRoleSystem,
				Content: &schemas.ChatMessageContent{
					ContentStr: schemas.Ptr(systemPrompt),
				},
			},
			{
				Role: schemas.ChatMessageRoleUser,
				Content: &schemas.ChatMessageContent{
					ContentStr: schemas.Ptr(userMsg),
				},
			},
		},
		Params: &schemas.ChatParameters{
			MaxCompletionTokens: &maxTokens,
			Temperature:         &temp,
			ResponseFormat:      &responseFormat,
		},
	}

	runOnce := func() (bool, string) {
		deadline := time.Now().Add(18 * time.Second)
		unifaiCtx := schemas.NewUnifAIContext(context.Background(), deadline)
		unifaiCtx.SetValue(schemas.UnifAIContextKeySkipBudgetAndRateLimits, true)
		// Guard eval is an internal call using configured provider keys. Skip the plugin
		// pipeline so mandatory virtual-key / session auth cannot fail-open the DLP check.
		unifaiCtx.SetValue(schemas.UnifAIContextKeySkipPluginPipeline, true)
		resp, unifaiErr := h.client.ChatCompletionRequest(unifaiCtx, unifaiReq)
		if unifaiErr != nil {
			return false, truncateRunes(unifaiErrorMessage(unifaiErr), 180)
		}
		rawText := stripEvalMarkdown(evaluatorChoiceText(resp))
		if rawText == "" {
			return false, "empty evaluator response"
		}
		violated, recognized := parseAIBotDecision(rawText)
		if !recognized {
			return false, "evaluator returned unparseable output: " + truncateRunes(rawText, 80)
		}
		return violated, ""
	}

	violated, errMsg := runOnce()
	if errMsg == "" {
		return violated, ""
	}
	// One retry without json_object — some providers reject response_format.
	unifaiReq.Params.ResponseFormat = nil
	violated, errMsg2 := runOnce()
	if errMsg2 == "" {
		return violated, ""
	}
	return false, errMsg + "; retry: " + errMsg2
}

func (h *BrowserAIHandler) evaluateAIBotVisionRule(rule logstore.BrowserGuardRule, userPrompt string, uploadImages []string, providerName schemas.ModelProvider, modelName string) (bool, string) {
	systemPrompt := `You are a DLP vision classifier. Apply ONLY the admin SECURITY_POLICY to uploaded document image(s).

- The first image (when present) is the admin REFERENCE_TEMPLATE to match against.
- Remaining images are from the user upload (PDF page images, photos, scans).
- If the upload visually matches the reference template or violates SECURITY_POLICY, set violation true.
- If there is no meaningful visual match or policy violation, set violation false.

Reply with one JSON object and nothing else:
{"violation":true} or {"violation":false}`

	policy := strings.TrimSpace(rule.BotPrompt)
	if policy == "" {
		policy = "Block uploads that visually match the reference template image."
	}

	userMsg := fmt.Sprintf(
		"SECURITY_POLICY:\n%s\n\nEXTRACTED_TEXT (if any):\n%s\n\nEvaluate the attached upload image(s). JSON only.",
		policy,
		truncateRunes(userPrompt, browserAIGuardBotMaxPromptRunes),
	)

	images := make([]string, 0, 1+len(uploadImages))
	if ref := normalizeBase64Image(rule.BotReferenceImage); ref != "" {
		images = append(images, ref)
	}
	for _, img := range uploadImages {
		if cleaned := normalizeBase64Image(img); cleaned != "" {
			images = append(images, cleaned)
		}
	}
	if len(images) == 0 {
		return false, "no vision images to evaluate"
	}

	if isOllamaGuardProvider(string(providerName)) {
		runOllama := func(jsonMode bool) (bool, string) {
			rawText, err := callOllamaVisionAny(modelName, systemPrompt, userMsg, images, jsonMode, 120*time.Second)
			if err != nil {
				return false, truncateRunes(err.Error(), 180)
			}
			rawText = stripEvalMarkdown(rawText)
			if rawText == "" {
				return false, "empty vision evaluator response"
			}
			violated, recognized := parseAIBotDecision(rawText)
			if !recognized {
				return false, "vision evaluator returned unparseable output: " + truncateRunes(rawText, 80)
			}
			return violated, ""
		}
		violated, errMsg := runOllama(true)
		if errMsg == "" {
			return violated, ""
		}
		violated, errMsg2 := runOllama(false)
		if errMsg2 == "" {
			return violated, ""
		}
		return false, errMsg + "; retry: " + errMsg2
	}

	if h.client == nil {
		return false, "unifai client not available"
	}

	// Outsource vision: send text + image data-URLs via UnifAI multimodal chat.
	maxImages := 6
	if len(images) > maxImages {
		images = images[:maxImages]
	}
	blocks := make([]schemas.ChatContentBlock, 0, 1+len(images))
	blocks = append(blocks, schemas.ChatContentBlock{
		Type: schemas.ChatContentBlockTypeText,
		Text: schemas.Ptr(userMsg),
	})
	for _, img := range images {
		img = strings.TrimSpace(img)
		if img == "" {
			continue
		}
		dataURL := img
		if !strings.HasPrefix(strings.ToLower(img), "data:") {
			dataURL = "data:image/png;base64," + img
		}
		blocks = append(blocks, schemas.ChatContentBlock{
			Type: schemas.ChatContentBlockTypeImage,
			ImageURLStruct: &schemas.ChatInputImage{
				URL: dataURL,
			},
		})
	}
	if len(blocks) < 2 {
		return false, "no vision images to evaluate"
	}

	maxTokens := 128
	temp := 0.0
	responseFormat := any(map[string]any{"type": "json_object"})
	unifaiReq := &schemas.UnifAIChatRequest{
		Provider: providerName,
		Model:    modelName,
		Input: []schemas.ChatMessage{
			{
				Role: schemas.ChatMessageRoleSystem,
				Content: &schemas.ChatMessageContent{
					ContentStr: schemas.Ptr(systemPrompt),
				},
			},
			{
				Role: schemas.ChatMessageRoleUser,
				Content: &schemas.ChatMessageContent{
					ContentBlocks: blocks,
				},
			},
		},
		Params: &schemas.ChatParameters{
			MaxCompletionTokens: &maxTokens,
			Temperature:         &temp,
			ResponseFormat:      &responseFormat,
		},
	}

	runOnce := func() (bool, string) {
		deadline := time.Now().Add(45 * time.Second)
		unifaiCtx := schemas.NewUnifAIContext(context.Background(), deadline)
		unifaiCtx.SetValue(schemas.UnifAIContextKeySkipBudgetAndRateLimits, true)
		unifaiCtx.SetValue(schemas.UnifAIContextKeySkipPluginPipeline, true)
		resp, unifaiErr := h.client.ChatCompletionRequest(unifaiCtx, unifaiReq)
		if unifaiErr != nil {
			return false, truncateRunes(unifaiErrorMessage(unifaiErr), 180)
		}
		rawText := stripEvalMarkdown(evaluatorChoiceText(resp))
		if rawText == "" {
			return false, "empty vision evaluator response"
		}
		violated, recognized := parseAIBotDecision(rawText)
		if !recognized {
			return false, "vision evaluator returned unparseable output: " + truncateRunes(rawText, 80)
		}
		return violated, ""
	}

	violated, errMsg := runOnce()
	if errMsg == "" {
		return violated, ""
	}
	if unifaiReq.Params != nil {
		unifaiReq.Params.ResponseFormat = nil
	}
	violated, errMsg2 := runOnce()
	if errMsg2 == "" {
		return violated, ""
	}
	return false, errMsg + "; retry: " + errMsg2
}

func unifaiErrorMessage(err *schemas.UnifAIError) string {
	if err == nil {
		return "unknown evaluator error"
	}
	if err.Error != nil && strings.TrimSpace(err.Error.Message) != "" {
		return strings.TrimSpace(err.Error.Message)
	}
	return "evaluator request failed"
}

func stripEvalMarkdown(raw string) string {
	raw = strings.TrimSpace(raw)
	if strings.HasPrefix(raw, "```json") {
		raw = strings.TrimPrefix(raw, "```json")
		raw = strings.TrimSuffix(raw, "```")
	} else if strings.HasPrefix(raw, "```") {
		raw = strings.TrimPrefix(raw, "```")
		raw = strings.TrimSuffix(raw, "```")
	}
	return strings.TrimSpace(raw)
}

func parseAIBotViolation(raw string) bool {
	v, ok := parseAIBotDecision(raw)
	return ok && v
}

func parseAIBotDecision(raw string) (bool, bool) {
	compact := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(raw, " ", ""), "\n", ""))
	iTrue := maxIndex(
		strings.LastIndex(compact, `"violation":true`),
		strings.LastIndex(compact, `"violation":1`),
		strings.LastIndex(compact, `violation:true`),
	)
	iFalse := maxIndex(
		strings.LastIndex(compact, `"violation":false`),
		strings.LastIndex(compact, `"violation":0`),
		strings.LastIndex(compact, `violation:false`),
	)
	if iTrue >= 0 || iFalse >= 0 {
		return iTrue > iFalse, true
	}
	if v, ok := violationFromJSON(raw); ok {
		return v, true
	}
	start := strings.LastIndex(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start >= 0 && end > start {
		if v, ok := violationFromJSON(raw[start : end+1]); ok {
			return v, true
		}
	}
	trimmed := strings.ToLower(strings.TrimSpace(raw))
	trimmed = strings.Trim(trimmed, "`\"'")
	switch trimmed {
	case "true", "yes", "block", "violation", "violated", "1":
		return true, true
	case "false", "no", "allow", "allowed", "safe", "0":
		return false, true
	}
	return false, false
}

func maxIndex(vals ...int) int {
	best := -1
	for _, v := range vals {
		if v > best {
			best = v
		}
	}
	return best
}

func violationFromJSON(raw string) (bool, bool) {
	var typed aiBotEvalResult
	if err := sonic.Unmarshal([]byte(raw), &typed); err == nil {
		return typed.Violation, true
	}
	var generic map[string]any
	if err := sonic.Unmarshal([]byte(raw), &generic); err != nil {
		return false, false
	}
	for _, key := range []string{"violation", "is_violation", "violated"} {
		if v, ok := generic[key]; ok {
			return truthyEval(v), true
		}
	}
	return false, false
}

func truthyEval(v any) bool {
	switch t := v.(type) {
	case bool:
		return t
	case string:
		s := strings.ToLower(strings.TrimSpace(t))
		return s == "true" || s == "1" || s == "yes"
	case float64:
		return t != 0
	default:
		return false
	}
}

func (h *BrowserAIHandler) generateReplyBotText(ctx *fasthttp.RequestCtx, provider, model, platform, ruleTriggered, userPrompt, kind string) (string, error) {
	provider, model = applyGuardBotDefaults(provider, model)
	providerName, modelName := resolveGuardBotModel(provider, model)

	systemPrompt := `You are UnifAI Guard, an enterprise security assistant embedded in browser AI chats.
A user tried to send sensitive or policy-violating content to a public AI website.
Write a short, professional in-chat reply (4-8 sentences max) that:
1) Clearly states the request was BLOCKED by security policy
2) Names the violation / rule when provided
3) Explains why pasting API keys, passwords, secrets, or confidential company data into web AI chats is prohibited
4) Tells the user to remove secrets and retry with a safe prompt
Do NOT include the secret itself. Do NOT help bypass the policy. Plain text only — no markdown headings.`

	userMsg := fmt.Sprintf(
		"Platform: %s\nViolation rule: %s\nUser prompt (may contain secrets — do not repeat them):\n%s",
		platform,
		ruleTriggered,
		truncateRunes(userPrompt, browserAIGuardBotMaxPromptRunes),
	)

	if kind != "violation" {
		systemPrompt = `You are UnifAI Reply Bot, answering on behalf of an enterprise policy that routes this website's chat through UnifAI.
Answer the user's question helpfully and accurately in plain text (no markdown headings).
Keep replies concise (typically under 12 sentences) unless the user asks for detail.
If the question is unsafe or asks for secrets/credentials, refuse briefly and explain.`
		userMsg = fmt.Sprintf("Platform: %s\nUser question:\n%s", platform, truncateRunes(userPrompt, browserAIGuardBotMaxPromptRunes))
	}

	if isOllamaGuardProvider(string(providerName)) {
		text, err := callOllamaChatAny(modelName, systemPrompt, userMsg, false, 90*time.Second)
		if err != nil {
			return "", err
		}
		return strings.TrimSpace(text), nil
	}

	if h.client == nil {
		return "", fmt.Errorf("unifai client not available")
	}

	maxTokens := 350
	temp := 0.3
	if kind != "violation" {
		maxTokens = 900
		temp = 0.5
	}
	unifaiReq := &schemas.UnifAIChatRequest{
		Provider: providerName,
		Model:    modelName,
		Input: []schemas.ChatMessage{
			{
				Role: schemas.ChatMessageRoleSystem,
				Content: &schemas.ChatMessageContent{
					ContentStr: schemas.Ptr(systemPrompt),
				},
			},
			{
				Role: schemas.ChatMessageRoleUser,
				Content: &schemas.ChatMessageContent{
					ContentStr: schemas.Ptr(userMsg),
				},
			},
		},
		Params: &schemas.ChatParameters{
			MaxCompletionTokens: &maxTokens,
			Temperature:         &temp,
		},
	}

	deadline := time.Now().Add(18 * time.Second)
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), deadline)
	unifaiCtx.SetValue(schemas.UnifAIContextKeySkipBudgetAndRateLimits, true)
	unifaiCtx.SetValue(schemas.UnifAIContextKeySkipPluginPipeline, true)
	_ = ctx

	resp, unifaiErr := h.client.ChatCompletionRequest(unifaiCtx, unifaiReq)
	if unifaiErr != nil {
		return "", fmt.Errorf("reply bot completion failed: %v", unifaiErr)
	}
	if resp == nil || len(resp.Choices) == 0 || resp.Choices[0].Message == nil || resp.Choices[0].Message.Content == nil {
		return "", fmt.Errorf("empty reply bot response")
	}
	if resp.Choices[0].Message.Content.ContentStr != nil {
		return strings.TrimSpace(*resp.Choices[0].Message.Content.ContentStr), nil
	}
	return "", fmt.Errorf("reply bot returned non-text content")
}

func truncateRunes(s string, max int) string {
	r := []rune(s)
	if len(r) <= max {
		return s
	}
	return string(r[:max]) + "…"
}
