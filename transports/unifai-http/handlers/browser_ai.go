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

	r.POST("/api/browser-ai/intercept", lib.ChainMiddlewares(h.intercept, middlewares...))
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
	if strings.TrimSpace(rule.Name) == "" || strings.TrimSpace(rule.Pattern) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Rule name and regex pattern are required")
		return
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
		"UnifAI_Guard.exe": {
			filepath.Join("dist", "UnifAI_Guard.exe"),
		},
		"EMPLOYEE_README.txt": {
			filepath.Join("installer", "EMPLOYEE_README.txt"),
		},
		"unifai_guard_config.json": {
			"unifai_guard_config.json",
			filepath.Join("dist", "unifai_guard_config.json"),
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
	SendJSON(ctx, map[string]any{
		"status":   "success",
		"agent":    agent,
		"settings": settings,
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
		"redacted_prompt":    logEntry.UserPromptFull,
		"risk_score":         logEntry.RiskScore,
		"predictive_risk":    logEntry.PredictiveRisk,
		"predicted_category": logEntry.PredictedCategory,
		"reply_text":         replyText,
		"reply_bot_provider": replyProvider,
		"reply_bot_model":    replyModel,
		"log":                logEntry,
	})
}

func (h *BrowserAIHandler) generateReplyBotText(ctx *fasthttp.RequestCtx, provider, model, platform, ruleTriggered, userPrompt, kind string) (string, error) {
	if h.client == nil {
		return "", fmt.Errorf("unifai client not available")
	}

	providerName := schemas.ModelProvider(provider)
	modelName := model
	if strings.Contains(provider, "/") {
		providerName, modelName = schemas.ParseModelString(provider+"/"+model, "")
	}

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
	_ = ctx // keep signature consistent with other handlers

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
