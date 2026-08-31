package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/valyala/fasthttp"
)

func propagateAccessProfile(ctx context.Context, configStore configstore.ConfigStore, profile tables.TableAccessProfile) error {
	if configStore == nil || !profile.IsActive {
		return nil
	}
	spec := profile.Spec()
	vkIDs := specStringSlice(spec, "virtual_key_ids")
	if len(vkIDs) == 0 {
		return nil
	}
	providerConfigs := specMapSlice(spec, "provider_configs")
	for _, vkID := range vkIDs {
		vk, err := configStore.GetVirtualKey(ctx, vkID)
		if err != nil || vk == nil {
			continue
		}
		if len(providerConfigs) > 0 {
			vk.ProviderConfigs = providerConfigsFromSpec(providerConfigs, vk.ID)
		}
		if rl := specMap(spec, "rate_limit"); rl != nil {
			vk.RateLimit = rateLimitFromSpec(rl, vk.RateLimitID)
		}
		if budgets := specMapSlice(spec, "budgets"); len(budgets) > 0 {
			vk.Budgets = budgetsFromSpec(budgets, vk.ID)
		}
		if err := configStore.UpdateVirtualKey(ctx, vk); err != nil {
			return fmt.Errorf("update virtual key %s: %w", vkID, err)
		}
	}
	return nil
}

func providerConfigsFromSpec(items []map[string]any, vkID string) []tables.TableVirtualKeyProviderConfig {
	out := make([]tables.TableVirtualKeyProviderConfig, 0, len(items))
	for _, item := range items {
		provider := firstString(item, "provider", "provider_name")
		if provider == "" {
			continue
		}
		cfg := tables.TableVirtualKeyProviderConfig{
			VirtualKeyID: vkID,
			Provider:     provider,
		}
		if models := stringSliceFromAny(item["allowed_models"]); len(models) > 0 {
			cfg.AllowedModels = schemas.WhiteList(models)
		} else if all, ok := item["all_models_allowed"].(bool); ok && all {
			cfg.AllowedModels = schemas.WhiteList{"*"}
		}
		if weight, ok := item["weight"].(float64); ok {
			cfg.Weight = &weight
		}
		out = append(out, cfg)
	}
	return out
}

func rateLimitFromSpec(spec map[string]any, existingID *string) *tables.TableRateLimit {
	id := uuid.NewString()
	if existingID != nil && *existingID != "" {
		id = *existingID
	}
	rl := &tables.TableRateLimit{ID: id}
	if v, ok := spec["request_max_limit"].(float64); ok {
		n := int64(v)
		rl.RequestMaxLimit = &n
	}
	if v, ok := spec["request_reset_duration"].(string); ok {
		rl.RequestResetDuration = &v
	}
	if v, ok := spec["token_max_limit"].(float64); ok {
		n := int64(v)
		rl.TokenMaxLimit = &n
	}
	if v, ok := spec["token_reset_duration"].(string); ok {
		rl.TokenResetDuration = &v
	}
	return rl
}

func budgetsFromSpec(items []map[string]any, vkID string) []tables.TableBudget {
	out := make([]tables.TableBudget, 0, len(items))
	for _, item := range items {
		b := tables.TableBudget{
			ID:           uuid.NewString(),
			VirtualKeyID: &vkID,
		}
		if v, ok := item["max_limit"].(float64); ok {
			b.MaxLimit = v
		}
		if v, ok := item["reset_duration"].(string); ok {
			b.ResetDuration = v
		}
		out = append(out, b)
	}
	return out
}

func stringSliceFromAny(raw any) []string {
	switch typed := raw.(type) {
	case []string:
		return typed
	case []any:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			if s, ok := item.(string); ok && s != "" {
				out = append(out, s)
			}
		}
		return out
	default:
		return nil
	}
}

func firstString(item map[string]any, keys ...string) string {
	for _, key := range keys {
		if v, ok := item[key].(string); ok && v != "" {
			return v
		}
	}
	return ""
}

// SCIM v2 minimal handlers backed by governance_users.
func (h *WorkspaceHandler) scimListUsers(ctx *fasthttp.RequestCtx) {
	if h.store == nil || h.store.ConfigStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store is not available")
		return
	}
	users, err := h.store.ConfigStore.GetUsers(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to list users")
		return
	}
	resources := make([]map[string]any, 0, len(users))
	for _, user := range users {
		resources = append(resources, scimUserResource(user))
	}
	SendJSON(ctx, map[string]any{
		"schemas":      []string{"urn:ietf:params:scim:api:messages:2.0:ListResponse"},
		"totalResults": len(resources),
		"itemsPerPage": len(resources),
		"startIndex":   1,
		"Resources":    resources,
	})
}

func (h *WorkspaceHandler) scimGetUser(ctx *fasthttp.RequestCtx) {
	if h.store == nil || h.store.ConfigStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store is not available")
		return
	}
	id := pathID(ctx, "id")
	user, err := h.store.ConfigStore.GetUserByID(ctx, id)
	if err != nil || user == nil {
		SendError(ctx, fasthttp.StatusNotFound, "user not found")
		return
	}
	SendJSON(ctx, scimUserResource(user))
}

func (h *WorkspaceHandler) scimCreateUser(ctx *fasthttp.RequestCtx) {
	if h.store == nil || h.store.ConfigStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store is not available")
		return
	}
	var body struct {
		UserName string `json:"userName"`
		Emails   []struct {
			Value   string `json:"value"`
			Primary bool   `json:"primary"`
		} `json:"emails"`
		Active bool `json:"active"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid scim payload")
		return
	}
	username := strings.TrimSpace(body.UserName)
	if username == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "userName is required")
		return
	}
	email := ""
	for _, item := range body.Emails {
		if item.Value != "" {
			email = item.Value
			if item.Primary {
				break
			}
		}
	}
	status := tables.UserStatusApproved
	if !body.Active {
		status = tables.UserStatusPending
	}
	user := &tables.TableUser{
		ID:       uuid.NewString(),
		Username: username,
		Email:    email,
		Password: uuid.NewString(),
		Role:     "user",
		Status:   status,
	}
	if err := h.store.ConfigStore.CreateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to create user")
		return
	}
	SendJSONWithStatus(ctx, scimUserResource(user), fasthttp.StatusCreated)
}

func (h *WorkspaceHandler) scimDeleteUser(ctx *fasthttp.RequestCtx) {
	if h.store == nil || h.store.ConfigStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store is not available")
		return
	}
	id := pathID(ctx, "id")
	user, err := h.store.ConfigStore.GetUserByID(ctx, id)
	if err != nil || user == nil {
		SendError(ctx, fasthttp.StatusNotFound, "user not found")
		return
	}
	if err := h.store.ConfigStore.DeleteUser(ctx, id); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to delete user")
		return
	}
	ctx.SetStatusCode(fasthttp.StatusNoContent)
}

func scimUserResource(user *tables.TableUser) map[string]any {
	if user == nil {
		return map[string]any{}
	}
	email := user.Email
	if email == "" {
		email = user.Username
	}
	return map[string]any{
		"schemas":  []string{"urn:ietf:params:scim:schemas:core:2.0:User"},
		"id":       user.ID,
		"userName": user.Username,
		"active":   user.IsApproved(),
		"emails": []map[string]any{{
			"value": email, "primary": true,
		}},
		"roles": []map[string]any{{"value": user.Role}},
		"meta": map[string]any{
			"resourceType": "User",
			"created":      user.CreatedAt,
			"lastModified": user.UpdatedAt,
		},
	}
}
