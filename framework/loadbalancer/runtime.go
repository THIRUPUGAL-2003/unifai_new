package loadbalancer

import (
	"context"
	"encoding/json"
	"math/rand"
	"sync"

	"github.com/unifai/unifai/framework/configstore"
)

// Config is the adaptive load balancer workspace setting.
type Config struct {
	Enabled                   bool `json:"enabled"`
	DirectionSelectionEnabled bool `json:"direction_selection_enabled"`
	RouteSelectionEnabled     bool `json:"route_selection_enabled"`
	RerouteFailedDirections   bool `json:"reroute_failed_directions"`
	PruneFailedFallbacks      bool `json:"prune_failed_fallbacks"`
}

// ProviderKey is a weighted inference API key candidate.
type ProviderKey struct {
	ID       string
	Provider string
	Weight   float64
	Enabled  bool
}

// Runtime holds the live load balancer config.
type Runtime struct {
	mu   sync.RWMutex
	cfg  Config
	keys []ProviderKey
}

// Default is the process-wide adaptive routing runtime.
var Default = &Runtime{}

// ReloadFromStore loads load balancer settings from workspace_settings.
func ReloadFromStore(ctx context.Context, store configstore.WorkspaceStore) error {
	if store == nil {
		return nil
	}
	row, err := store.GetWorkspaceSetting(ctx, configstore.WorkspaceSettingLoadBalancer)
	if err != nil {
		if err == configstore.ErrNotFound {
			Default.mu.Lock()
			Default.cfg = Config{}
			Default.mu.Unlock()
			return nil
		}
		return err
	}
	var cfg Config
	if err := json.Unmarshal([]byte(row.Data), &cfg); err != nil {
		return err
	}
	Default.mu.Lock()
	Default.cfg = cfg
	Default.mu.Unlock()
	return nil
}

// SetProviderKeys updates the provider key pool used for route selection.
func (r *Runtime) SetProviderKeys(keys []ProviderKey) {
	r.mu.Lock()
	r.keys = append([]ProviderKey(nil), keys...)
	r.mu.Unlock()
}

// ConfigSnapshot returns the current config.
func (r *Runtime) ConfigSnapshot() Config {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.cfg
}

// SelectProviderKey picks a weighted provider key when adaptive route selection is enabled.
func (r *Runtime) SelectProviderKey(provider string) (string, bool) {
	r.mu.RLock()
	cfg := r.cfg
	keys := append([]ProviderKey(nil), r.keys...)
	r.mu.RUnlock()
	if !cfg.Enabled || !cfg.RouteSelectionEnabled {
		return "", false
	}
	var candidates []ProviderKey
	for _, key := range keys {
		if key.Provider != provider || !key.Enabled || key.Weight <= 0 {
			continue
		}
		candidates = append(candidates, key)
	}
	if len(candidates) == 0 {
		return "", false
	}
	total := 0.0
	for _, key := range candidates {
		total += key.Weight
	}
	if total <= 0 {
		return candidates[0].ID, true
	}
	randomValue := rand.Float64() * total
	current := 0.0
	for _, key := range candidates {
		current += key.Weight
		if randomValue <= current {
			return key.ID, true
		}
	}
	return candidates[0].ID, true
}
