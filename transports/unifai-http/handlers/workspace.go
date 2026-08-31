package handlers

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/fasthttp/router"
	"github.com/google/uuid"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

// WorkspaceHandler serves workspace feature APIs. Persistence goes through
// configstore.WorkspaceStore; this type only does HTTP.
type WorkspaceHandler struct {
	store     *lib.Config
	workspace configstore.WorkspaceStore
}

func NewWorkspaceHandler(store *lib.Config) *WorkspaceHandler {
	h := &WorkspaceHandler{store: store}
	if store != nil {
		h.workspace, _ = configstore.AsWorkspaceStore(store.ConfigStore)
	}
	return h
}

// NewEnterpriseFeaturesHandler is kept so existing call sites compile.
func NewEnterpriseFeaturesHandler(store *lib.Config) *WorkspaceHandler {
	return NewWorkspaceHandler(store)
}

func (h *WorkspaceHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	wrap := func(fn fasthttp.RequestHandler) fasthttp.RequestHandler {
		return lib.ChainMiddlewares(h.withAudit(fn), middlewares...)
	}

	r.GET("/api/circuit-breaker/policies", wrap(h.listCircuitBreakerPolicies))
	r.POST("/api/circuit-breaker/policies", wrap(h.createCircuitBreakerPolicy))
	r.PUT("/api/circuit-breaker/policies/{name}", wrap(h.updateCircuitBreakerPolicy))
	r.DELETE("/api/circuit-breaker/policies/{name}", wrap(h.deleteCircuitBreakerPolicy))
	r.GET("/api/circuit-breaker/state", wrap(h.getCircuitBreakerState))
	r.POST("/api/circuit-breaker/policies/{name}/reset", wrap(h.resetCircuitBreakerPolicy))

	r.GET("/api/access-profiles", wrap(h.listAccessProfiles))
	r.POST("/api/access-profiles", wrap(h.createAccessProfile))
	r.GET("/api/access-profiles/{id}", wrap(h.getAccessProfile))
	r.PUT("/api/access-profiles/{id}", wrap(h.updateAccessProfile))
	r.DELETE("/api/access-profiles/{id}", wrap(h.deleteAccessProfile))
	r.POST("/api/access-profiles/{id}/activate", wrap(h.activateAccessProfile))
	r.POST("/api/access-profiles/{id}/deactivate", wrap(h.deactivateAccessProfile))
	r.POST("/api/access-profiles/{id}/clone", wrap(h.cloneAccessProfile))
	r.GET("/api/users/{target_user_id}/access-profiles", wrap(h.listUserAccessProfiles))

	r.GET("/api/roles", wrap(h.listRoles))
	r.POST("/api/roles", wrap(h.createRole))
	r.GET("/api/roles/{id}", wrap(h.getRole))
	r.PUT("/api/roles/{id}", wrap(h.updateRole))
	r.DELETE("/api/roles/{id}", wrap(h.deleteRole))
	r.GET("/api/roles/{id}/permissions", wrap(h.getRolePermissions))
	r.PUT("/api/roles/{id}/permissions", wrap(h.updateRolePermissions))
	r.GET("/api/resources", wrap(h.listRBACResources))
	r.GET("/api/operations", wrap(h.listRBACOperations))
	r.GET("/api/permissions", wrap(h.listRBACPermissions))
	r.PUT("/api/users/{id}/role", wrap(h.assignUserRole))

	r.GET("/api/governance/business-units", wrap(h.listBusinessUnits))
	r.POST("/api/governance/business-units", wrap(h.createBusinessUnit))
	r.GET("/api/governance/business-units/{id}", wrap(h.getBusinessUnit))
	r.DELETE("/api/governance/business-units/{id}", wrap(h.deleteBusinessUnit))
	r.GET("/api/governance/business-units/{id}/teams", wrap(h.listBusinessUnitTeams))
	r.POST("/api/governance/business-units/{id}/teams", wrap(h.assignBusinessUnitTeam))
	r.DELETE("/api/governance/business-units/{id}/teams/{team_id}", wrap(h.removeBusinessUnitTeam))
	r.PUT("/api/governance/business-units/{id}/governance", wrap(h.updateBusinessUnitGovernance))

	r.GET("/api/mcp/tool-groups", wrap(h.listMCPToolGroups))
	r.POST("/api/mcp/tool-groups", wrap(h.createMCPToolGroup))
	r.GET("/api/mcp/tool-groups/{id}", wrap(h.getMCPToolGroup))
	r.PUT("/api/mcp/tool-groups/{id}", wrap(h.updateMCPToolGroup))
	r.DELETE("/api/mcp/tool-groups/{id}", wrap(h.deleteMCPToolGroup))

	r.GET("/api/cluster", wrap(h.getClusterConfig))
	r.PUT("/api/cluster", wrap(h.updateClusterConfig))
	r.GET("/api/load-balancer", wrap(h.getLoadBalancerConfig))
	r.PUT("/api/load-balancer", wrap(h.updateLoadBalancerConfig))
	r.GET("/api/load-balancer/routes", wrap(h.getLoadBalancerRoutes))

	r.GET("/api/scim/config", wrap(h.getSCIMConfig))
	r.PUT("/api/scim/config", wrap(h.updateSCIMConfig))
	r.GET("/api/scim/providers", wrap(h.listSCIMProviders))

	r.GET("/api/alert-channels", wrap(h.listAlertChannels))
	r.POST("/api/alert-channels", wrap(h.createAlertChannel))
	r.PUT("/api/alert-channels/{id}", wrap(h.updateAlertChannel))
	r.DELETE("/api/alert-channels/{id}", wrap(h.deleteAlertChannel))
	r.POST("/api/alert-channels/{id}/test", wrap(h.testAlertChannel))

	r.GET("/api/audit-logs", wrap(h.listAuditLogs))
	r.GET("/api/audit-logs/export", wrap(h.exportAuditLogs))
	r.GET("/api/audit-logs/settings", wrap(h.getAuditSettings))
	r.PUT("/api/audit-logs/settings", wrap(h.updateAuditSettings))

	r.GET("/api/prompt-deployments", wrap(h.listPromptDeployments))
	r.POST("/api/prompt-deployments", wrap(h.createPromptDeployment))
	r.PUT("/api/prompt-deployments/{id}", wrap(h.updatePromptDeployment))
	r.DELETE("/api/prompt-deployments/{id}", wrap(h.deletePromptDeployment))

	r.GET("/api/connectors/{name}", wrap(h.getConnector))
	r.PUT("/api/connectors/{name}", wrap(h.updateConnector))
	r.POST("/api/connectors/{name}/test", wrap(h.testConnector))
}

func (h *WorkspaceHandler) requireStore(ctx *fasthttp.RequestCtx) configstore.WorkspaceStore {
	if h.workspace == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store is not available")
		return nil
	}
	return h.workspace
}

func (h *WorkspaceHandler) sessionActor(ctx *fasthttp.RequestCtx) string {
	if h.store == nil || h.store.ConfigStore == nil {
		return "system"
	}
	token := ""
	if authHeader := string(ctx.Request.Header.Peek("Authorization")); strings.HasPrefix(authHeader, "Bearer ") {
		token = strings.TrimPrefix(authHeader, "Bearer ")
	}
	if token == "" {
		token = string(ctx.Request.Header.Cookie("token"))
	}
	if token == "" {
		return "system"
	}
	session, err := h.store.ConfigStore.GetSession(ctx, token)
	if err != nil || session == nil {
		return "system"
	}
	if session.Username != "" {
		return session.Username
	}
	return "admin"
}

func (h *WorkspaceHandler) withAudit(next fasthttp.RequestHandler) fasthttp.RequestHandler {
	return func(ctx *fasthttp.RequestCtx) {
		start := time.Now()
		next(ctx)
		method := string(ctx.Method())
		if method == fasthttp.MethodGet || method == fasthttp.MethodHead || method == fasthttp.MethodOptions {
			return
		}
		if h.workspace == nil {
			return
		}
		status := ctx.Response.StatusCode()
		outcome := "success"
		if status >= 400 {
			outcome = "failure"
		}
		action := "update"
		switch method {
		case fasthttp.MethodPost:
			action = "create"
		case fasthttp.MethodDelete:
			action = "delete"
		}
		_ = h.workspace.CreateAuditLog(ctx, &tables.TableAuditLog{
			Action:     action,
			Outcome:    outcome,
			Initiator:  h.sessionActor(ctx),
			Target:     string(ctx.Path()),
			Method:     method,
			Path:       string(ctx.Path()),
			IP:         ctx.RemoteIP().String(),
			DurationMs: time.Since(start).Milliseconds(),
			CreatedAt:  time.Now().UTC(),
		})
	}
}

func pathID(ctx *fasthttp.RequestCtx, name string) string {
	value := ctx.UserValue(name)
	if value == nil {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return typed
	case []byte:
		return string(typed)
	default:
		return fmt.Sprint(typed)
	}
}

func pathUint(ctx *fasthttp.RequestCtx, name string) (uint, bool) {
	raw := pathID(ctx, name)
	n, err := strconv.ParseUint(raw, 10, 64)
	if err != nil {
		return 0, false
	}
	return uint(n), true
}

func queryInt(ctx *fasthttp.RequestCtx, name string, fallback int) int {
	raw := string(ctx.QueryArgs().Peek(name))
	if raw == "" {
		return fallback
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return n
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func newEntityID() string {
	return uuid.NewString()
}

func isStoreNotFound(err error) bool {
	return errors.Is(err, configstore.ErrNotFound)
}

func specStringSlice(spec map[string]any, key string) []string {
	raw, _ := spec[key].([]any)
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		if s, ok := item.(string); ok {
			out = append(out, s)
		}
	}
	if len(out) == 0 {
		if typed, ok := spec[key].([]string); ok {
			return typed
		}
	}
	return out
}

func specMapSlice(spec map[string]any, key string) []map[string]any {
	raw, ok := spec[key]
	if !ok || raw == nil {
		return nil
	}
	switch typed := raw.(type) {
	case []map[string]any:
		return typed
	case []any:
		out := make([]map[string]any, 0, len(typed))
		for _, item := range typed {
			if m, ok := item.(map[string]any); ok {
				out = append(out, m)
			}
		}
		return out
	default:
		return nil
	}
}

func specMap(spec map[string]any, key string) map[string]any {
	raw, _ := spec[key].(map[string]any)
	return raw
}
