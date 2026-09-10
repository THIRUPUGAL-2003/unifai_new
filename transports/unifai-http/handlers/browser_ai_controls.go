package handlers

import (
	"github.com/bytedance/sonic"
	"github.com/valyala/fasthttp"
)

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
