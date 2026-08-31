package mcptoolgroups

import (
	"context"
	"encoding/json"
	"strings"
	"sync"

	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
)

// Group is the runtime view of an MCP tool group.
type Group struct {
	ID            uint
	Name          string
	Enabled       bool
	Tools         []string
	VirtualKeyIDs []string
	TeamIDs       []string
	CustomerIDs   []string
	UserIDs       []string
	ProviderNames []string
}

// Runtime holds enabled MCP tool groups.
type Runtime struct {
	mu     sync.RWMutex
	groups []Group
}

// Default is the process-wide MCP tool group runtime.
var Default = &Runtime{}

// ReloadFromStore refreshes tool groups from the workspace DB.
func ReloadFromStore(ctx context.Context, store configstore.WorkspaceStore) error {
	if store == nil {
		Default.mu.Lock()
		Default.groups = nil
		Default.mu.Unlock()
		return nil
	}
	rows, err := store.ListMCPToolGroups(ctx)
	if err != nil {
		return err
	}
	groups := make([]Group, 0, len(rows))
	for _, row := range rows {
		if !row.Enabled {
			continue
		}
		groups = append(groups, groupFromRow(row))
	}
	Default.mu.Lock()
	Default.groups = groups
	Default.mu.Unlock()
	return nil
}

func groupFromRow(row tables.TableMCPToolGroup) Group {
	spec := row.ParsedSpec
	if spec == nil {
		spec = map[string]any{}
	}
	return Group{
		ID: row.ID, Name: row.Name, Enabled: row.Enabled,
		Tools:         toolNames(spec),
		VirtualKeyIDs: stringSlice(spec, "virtual_key_ids"),
		TeamIDs:       stringSlice(spec, "team_ids"),
		CustomerIDs:   stringSlice(spec, "customer_ids"),
		UserIDs:       stringSlice(spec, "user_ids"),
		ProviderNames: stringSlice(spec, "provider_names"),
	}
}

func toolNames(spec map[string]any) []string {
	raw, ok := spec["tools"]
	if !ok {
		return nil
	}
	items, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		for _, key := range []string{"name", "tool_name", "id"} {
			if v, ok := m[key].(string); ok && v != "" {
				out = append(out, v)
				break
			}
		}
	}
	return out
}

func stringSlice(spec map[string]any, key string) []string {
	raw, ok := spec[key]
	if !ok {
		return nil
	}
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
		if b, err := json.Marshal(raw); err == nil {
			var out []string
			_ = json.Unmarshal(b, &out)
			return out
		}
	}
	return nil
}

// RequestContext carries identifiers for tool group matching.
type RequestContext struct {
	VirtualKeyID string
	UserID       string
	TeamID       string
	CustomerID   string
	ProviderName string
}

// IsToolAllowed returns whether toolName is permitted by any matching enabled group.
// When no groups are configured, all tools are allowed.
func (r *Runtime) IsToolAllowed(toolName string, req RequestContext) bool {
	r.mu.RLock()
	groups := append([]Group(nil), r.groups...)
	r.mu.RUnlock()
	if len(groups) == 0 {
		return true
	}
	toolName = strings.TrimSpace(toolName)
	if toolName == "" {
		return true
	}
	matched := false
	for _, group := range groups {
		if !group.matches(req) {
			continue
		}
		matched = true
		if len(group.Tools) == 0 {
			return true
		}
		for _, allowed := range group.Tools {
			if toolMatches(allowed, toolName) {
				return true
			}
		}
	}
	if !matched {
		return true
	}
	return false
}

func (g Group) matches(req RequestContext) bool {
	if len(g.VirtualKeyIDs) > 0 && !contains(g.VirtualKeyIDs, req.VirtualKeyID) {
		return false
	}
	if len(g.UserIDs) > 0 && !contains(g.UserIDs, req.UserID) {
		return false
	}
	if len(g.TeamIDs) > 0 && !contains(g.TeamIDs, req.TeamID) {
		return false
	}
	if len(g.CustomerIDs) > 0 && !contains(g.CustomerIDs, req.CustomerID) {
		return false
	}
	if len(g.ProviderNames) > 0 && !contains(g.ProviderNames, req.ProviderName) {
		return false
	}
	return true
}

func contains(list []string, value string) bool {
	if value == "" {
		return false
	}
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}

func toolMatches(pattern, toolName string) bool {
	pattern = strings.TrimSpace(pattern)
	if pattern == "" {
		return false
	}
	if strings.HasSuffix(pattern, "-*") {
		prefix := strings.TrimSuffix(pattern, "-*")
		return strings.HasPrefix(toolName, prefix+"-")
	}
	return pattern == toolName
}
