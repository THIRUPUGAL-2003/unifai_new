package handlers

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
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
