package handlers

import (
	"strconv"
	"strings"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/valyala/fasthttp"
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
