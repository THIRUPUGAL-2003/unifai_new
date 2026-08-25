package handlers

import (
	"archive/zip"
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
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

	r.POST("/api/browser-ai/intercept", lib.ChainMiddlewares(h.intercept, middlewares...))
	r.POST("/api/browser-ai/intercept-file", lib.ChainMiddlewares(h.interceptFile, middlewares...))
	r.GET("/api/browser-ai/attachments/{id}", lib.ChainMiddlewares(h.getAttachment, middlewares...))
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
		if strings.TrimSpace(rule.BotPrompt) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Evaluation prompt is required for AI Guard Bot rule")
			return
		}
		if strings.TrimSpace(rule.BotProvider) == "" || strings.TrimSpace(rule.BotModel) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Provider and model are required for AI Guard Bot rule")
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
	needsAIBotCheck := ruleType == "ai_bot" || hasBotPrompt || hasBotProvider || hasBotModel
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
				break
			}
		}
	}
	if ruleType == "ai_bot" {
		botPrompt, _ := updates["bot_prompt"].(string)
		botProvider, _ := updates["bot_provider"].(string)
		botModel, _ := updates["bot_model"].(string)
		if strings.TrimSpace(botPrompt) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Evaluation prompt is required for AI Guard Bot rule")
			return
		}
		if strings.TrimSpace(botProvider) == "" || strings.TrimSpace(botModel) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Provider and model are required for AI Guard Bot rule")
			return
		}
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

	logEntry, ruleWarning, err := h.manager.InterceptPrompt(ctx, payload.Platform, payload.Prompt, payload.ClientIP, payload.Metadata)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}

	allowed := logEntry.Action == "Allowed" || logEntry.Action == "Redacted" || logEntry.Action == "Warned"
	isViolationBlock := !allowed

	// File-upload audit logs: proxy already decided allow/block. Do not re-run AI Guard Bot
	// or Reply Bot on "[FILE UPLOAD] …" — that corrupts Allowed upload rows in Prompt Logs.
	uploadScan := false
	if v, ok := payload.Metadata["upload_scan"].(bool); ok && v {
		uploadScan = true
	}
	if strings.HasPrefix(strings.TrimSpace(payload.Prompt), "[FILE UPLOAD]") {
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
	// Evaluate AI Guard Bot whenever the prompt is still allowed (Allowed or Warned).
	// A regex WARN must not short-circuit a stronger AI Guard Bot BLOCK policy.
	if allowed {
		rules, _ := h.manager.GetRules(ctx)
		for _, rule := range rules {
			if !rule.Active || strings.ToLower(rule.RuleType) != "ai_bot" {
				continue
			}
			if strings.TrimSpace(rule.BotPrompt) == "" || strings.TrimSpace(rule.BotProvider) == "" || strings.TrimSpace(rule.BotModel) == "" {
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
						ruleWarning = "AI Guard Bot rule is incomplete (provider/model/prompt required)."
					}
					allowed = false
					isViolationBlock = true
					evalError = "ai guard bot misconfigured: provider, model, and prompt are required"
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
					break
				}
				continue
			}
			violated, evalErr := h.evaluateAIBotRule(rule, payload.Prompt)
			if evalErr != "" {
				evalError = evalErr
				ruleAction := logstore.NormalizeGuardRuleAction(rule.Action)
				// BLOCK rules fail-closed so DLP cannot be bypassed when the evaluator errors.
				if ruleAction == "BLOCK" {
					logEntry.Action = "Blocked"
					logEntry.Status = fmt.Sprintf("Blocked (%s — AI Guard Bot eval failed)", rule.Name)
					logEntry.RiskScore = 95
					logEntry.PredictiveRisk = "CRITICAL"
					logEntry.PredictedCategory = "AI_GUARD_BOT_EVAL_ERROR"
					logEntry.RuleTriggered = rule.Name
					ruleWarning = strings.TrimSpace(rule.WarningMessage)
					if ruleWarning == "" {
						ruleWarning = "UnifAI Guard could not evaluate this prompt. Blocked for safety."
					}
					allowed = false
					isViolationBlock = true
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
					break
				}
				logEntry.Status = "Allowed (AI Guard Bot eval failed)"
				logEntry.PredictedCategory = "AI_GUARD_BOT_EVAL_ERROR"
				logEntry.RuleTriggered = rule.Name
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
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
					break
				} else if ruleAction == "WARN" {
					logEntry.Action = "Warned"
					logEntry.Status = fmt.Sprintf("Warned (%s)", rule.Name)
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
					logEntry.PredictedCategory = "AI_GUARD_BOT_WARNING"
					logEntry.RuleTriggered = rule.Name
					ruleWarning = strings.TrimSpace(rule.WarningMessage)
					evalError = ""
					_ = h.manager.UpdateLogRuleViolation(ctx, logEntry.ID, logEntry.Action, logEntry.Status, logEntry.RuleTriggered, logEntry.RiskScore, logEntry.PredictiveRisk, logEntry.PredictedCategory)
				}
			}
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
		"reply_text":         replyText,
		"reply_bot_provider": replyProvider,
		"reply_bot_model":    replyModel,
		"eval_error":         evalError,
		"log":                logEntry,
	})
}

// interceptFile accepts multipart upload from Guard/proxy: form fields + optional PDF file.
// Stores PDFs under APP_DIR/pdf and links them on the intercept log for View/Download in UI.
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

	var fileBytes []byte
	fileName := getForm("file_name")
	if form.File != nil {
		for _, headers := range form.File {
			if len(headers) == 0 {
				continue
			}
			fh := headers[0]
			if fileName == "" && fh.Filename != "" {
				fileName = fh.Filename
			}
			f, openErr := fh.Open()
			if openErr != nil {
				continue
			}
			buf := make([]byte, browserAIAttachmentMaxBytes+1)
			n, _ := f.Read(buf)
			_ = f.Close()
			if n > 0 {
				if n > browserAIAttachmentMaxBytes {
					SendError(ctx, fasthttp.StatusRequestEntityTooLarge, "file too large (max 20MB)")
					return
				}
				fileBytes = buf[:n]
				break
			}
		}
	}
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

	logEntry, ruleWarning, err := h.manager.InterceptPrompt(ctx, platform, prompt, clientIP, metadata)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}

	if len(fileBytes) > 0 {
		stored, ctype, storeErr := storeBrowserAIPDF(logEntry.ID, fileName, fileBytes)
		if storeErr == nil {
			_ = h.manager.UpdateLogAttachment(ctx, logEntry.ID, sanitizeAttachmentFileName(fileName), stored, ctype)
			logEntry.AttachmentName = sanitizeAttachmentFileName(fileName)
			logEntry.AttachmentStoredName = stored
			logEntry.AttachmentContentType = ctype
		}
	}

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
	if err != nil || logEntry == nil || strings.TrimSpace(logEntry.AttachmentStoredName) == "" {
		SendError(ctx, fasthttp.StatusNotFound, "attachment not found")
		return
	}
	path, err := resolveBrowserAIAttachmentPath(logEntry.AttachmentStoredName)
	if err != nil {
		SendError(ctx, fasthttp.StatusNotFound, "attachment file missing")
		return
	}
	data, err := os.ReadFile(path)
	if err != nil {
		SendError(ctx, fasthttp.StatusNotFound, "attachment file missing")
		return
	}
	ctype := strings.TrimSpace(logEntry.AttachmentContentType)
	if ctype == "" {
		ctype = "application/pdf"
	}
	name := strings.TrimSpace(logEntry.AttachmentName)
	if name == "" {
		name = "document.pdf"
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

func (h *BrowserAIHandler) evaluateAIBotRule(rule logstore.BrowserGuardRule, userPrompt string) (bool, string) {
	if h.client == nil {
		return false, "unifai client not available"
	}

	providerName, modelName := resolveGuardBotModel(rule.BotProvider, rule.BotModel)
	if providerName == "" || strings.TrimSpace(modelName) == "" {
		return false, "guard bot provider/model missing"
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
		truncateRunes(userPrompt, 3000),
	)

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
	if h.client == nil {
		return "", fmt.Errorf("unifai client not available")
	}

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
		truncateRunes(userPrompt, 1200),
	)

	if kind != "violation" {
		systemPrompt = `You are UnifAI Reply Bot, answering on behalf of an enterprise policy that routes this website's chat through UnifAI.
Answer the user's question helpfully and accurately in plain text (no markdown headings).
Keep replies concise (typically under 12 sentences) unless the user asks for detail.
If the question is unsafe or asks for secrets/credentials, refuse briefly and explain.`
		userMsg = fmt.Sprintf("Platform: %s\nUser question:\n%s", platform, truncateRunes(userPrompt, 4000))
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
