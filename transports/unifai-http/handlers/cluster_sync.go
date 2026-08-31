package handlers

import (
	"github.com/unifai/unifai/framework/cluster"
	"github.com/valyala/fasthttp"
)

func (h *WorkspaceHandler) clusterKVReplicate(ctx *fasthttp.RequestCtx) {
	if !cluster.IsReplicationRequest(string(ctx.Request.Header.Peek(cluster.ReplicateHeaderName()))) {
		SendError(ctx, fasthttp.StatusForbidden, "missing cluster replication header")
		return
	}
	if h.store == nil || h.store.KVStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "kv store is not available")
		return
	}
	msg, err := cluster.ReadReplicationBody(ctx.Request.BodyStream())
	if err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid replication payload")
		return
	}
	if err := cluster.ApplyReplication(h.store.KVStore, msg); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to apply replication")
		return
	}
	ctx.SetStatusCode(fasthttp.StatusNoContent)
}
