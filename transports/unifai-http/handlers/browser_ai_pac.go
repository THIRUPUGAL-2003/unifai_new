package handlers

import (
	"context"
	"strings"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/valyala/fasthttp"
)

// getProxyPAC serves a PAC built only from monitored Target Websites (no hardcoded defaults).
func (h *BrowserAIHandler) getProxyPAC(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	proxyAddr := string(ctx.QueryArgs().Peek("proxy"))
	if strings.TrimSpace(proxyAddr) == "" {
		if fleet, err := h.manager.GetFleetConfig(ctx); err == nil && fleet != nil {
			if v := strings.TrimSpace(fleet.PacAdvertiseAddr); v != "" {
				proxyAddr = v
			} else if v := strings.TrimSpace(fleet.DefaultProxyAddr); v != "" {
				proxyAddr = v
			}
		}
	}
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

func (h *BrowserAIHandler) getFleetConfig(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	fleet, err := h.manager.GetFleetConfig(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"fleet_config": fleet})
}

func (h *BrowserAIHandler) putFleetConfig(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var body logstore.BrowserGuardFleetConfig
	if err := sonic.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	saved, err := h.manager.SaveFleetConfig(ctx, &body)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "success", "fleet_config": saved})
}
