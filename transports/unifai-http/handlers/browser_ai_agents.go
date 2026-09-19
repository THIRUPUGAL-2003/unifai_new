package handlers

import (
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/valyala/fasthttp"
)

var (
	uninstallAttemptsMu sync.Mutex
	uninstallAttempts   = make(map[string]struct {
		count int
		last  time.Time
	})
)

const (
	maxUninstallAttempts   = 5
	uninstallLockoutPeriod = 15 * time.Minute
)

func (h *BrowserAIHandler) listAgents(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	status := string(ctx.QueryArgs().Peek("status"))
	search := string(ctx.QueryArgs().Peek("search"))
	agentType := string(ctx.QueryArgs().Peek("agent_type"))
	limit, _ := strconv.Atoi(string(ctx.QueryArgs().Peek("limit")))
	offset, _ := strconv.Atoi(string(ctx.QueryArgs().Peek("offset")))
	if limit <= 0 {
		limit = 50
	}
	agents, total, err := h.manager.ListAgents(ctx, status, search, limit, offset, agentType)
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
	body.AgentType = logstore.NormalizeBrowserAIAgentType(body.AgentType)
	host := strings.ToLower(strings.TrimSpace(body.Hostname))
	// Laptop-only setups: drop shared network proxy heartbeats (corp-network-proxy)
	// so they cannot reappear after admin delete. Opt back in with BROWSER_AI_ALLOW_NETWORK_AGENTS=1.
	allowNetwork := strings.TrimSpace(os.Getenv("BROWSER_AI_ALLOW_NETWORK_AGENTS"))
	allowNetworkOn := allowNetwork == "1" || strings.EqualFold(allowNetwork, "true") || strings.EqualFold(allowNetwork, "yes")
	if !allowNetworkOn && (body.AgentType == "network" || host == "corp-network-proxy" || strings.HasPrefix(strings.ToLower(strings.TrimSpace(body.ID)), "network-")) {
		SendJSON(ctx, map[string]any{
			"status":  "ignored",
			"reason":  "network agents disabled",
			"command": "",
		})
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
	fleet, _ := h.manager.GetFleetConfig(ctx)
	command := ""
	if agent != nil && agent.UninstallRequested && agent.Status != logstore.AgentStatusUninstalled {
		command = "uninstall"
	}
	SendJSON(ctx, map[string]any{
		"status":       "success",
		"agent":        agent,
		"settings":     settings,
		"fleet_config": fleet,
		"command":      command,
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
	clientIP := clientIPAddress(ctx)

	uninstallAttemptsMu.Lock()
	if state, exists := uninstallAttempts[clientIP]; exists && state.count >= maxUninstallAttempts && time.Since(state.last) <= uninstallLockoutPeriod {
		uninstallAttemptsMu.Unlock()
		SendError(ctx, fasthttp.StatusTooManyRequests, "Too many failed uninstall attempts. Locked out for 15 minutes.")
		return
	}
	uninstallAttemptsMu.Unlock()

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
	if !ok {
		uninstallAttemptsMu.Lock()
		state := uninstallAttempts[clientIP]
		if time.Since(state.last) > uninstallLockoutPeriod {
			state.count = 0
		}
		state.count++
		state.last = time.Now()
		uninstallAttempts[clientIP] = state
		fails := state.count
		uninstallAttemptsMu.Unlock()

		if fails >= maxUninstallAttempts {
			SendError(ctx, fasthttp.StatusTooManyRequests, "Too many failed uninstall attempts. Locked out for 15 minutes.")
			return
		}
	} else {
		uninstallAttemptsMu.Lock()
		delete(uninstallAttempts, clientIP)
		uninstallAttemptsMu.Unlock()
	}

	SendJSON(ctx, map[string]any{
		"valid":    ok,
		"settings": settings,
	})
}

func (h *BrowserAIHandler) uninstallAgent(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	clientIP := clientIPAddress(ctx)

	uninstallAttemptsMu.Lock()
	if state, exists := uninstallAttempts[clientIP]; exists && state.count >= maxUninstallAttempts && time.Since(state.last) <= uninstallLockoutPeriod {
		uninstallAttemptsMu.Unlock()
		SendError(ctx, fasthttp.StatusTooManyRequests, "Too many failed uninstall attempts. Locked out for 15 minutes.")
		return
	}
	uninstallAttemptsMu.Unlock()

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
		uninstallAttemptsMu.Lock()
		state := uninstallAttempts[clientIP]
		if time.Since(state.last) > uninstallLockoutPeriod {
			state.count = 0
		}
		state.count++
		state.last = time.Now()
		uninstallAttempts[clientIP] = state
		fails := state.count
		uninstallAttemptsMu.Unlock()

		if fails >= maxUninstallAttempts {
			SendError(ctx, fasthttp.StatusTooManyRequests, "Too many failed uninstall attempts. Locked out for 15 minutes.")
			return
		}
		SendError(ctx, fasthttp.StatusForbidden, "Invalid uninstall key")
		return
	}

	uninstallAttemptsMu.Lock()
	delete(uninstallAttempts, clientIP)
	uninstallAttemptsMu.Unlock()
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
