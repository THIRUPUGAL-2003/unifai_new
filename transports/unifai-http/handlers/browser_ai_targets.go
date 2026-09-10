package handlers

import (
	"strings"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/valyala/fasthttp"
)

func (h *BrowserAIHandler) getTargets(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	targets, err := h.manager.GetTargets(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	forAgent := strings.EqualFold(string(ctx.QueryArgs().Peek("for")), "agent")
	if forAgent {
		out := make([]map[string]any, 0, len(targets))
		for _, t := range targets {
			out = append(out, map[string]any{
				"id":            t.ID,
				"domain":        t.Domain,
				"platform_name": t.PlatformName,
				"monitored":     t.Monitored,
				"block_site":    t.BlockSite,
				"parent_id":     t.ParentID,
				"host_role":     t.HostRole,
			})
		}
		SendJSON(ctx, map[string]any{"targets": out})
		return
	}
	SendJSON(ctx, map[string]any{"targets": targets})
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
