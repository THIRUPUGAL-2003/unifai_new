package handlers

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/valyala/fasthttp"
)

type accessProfilePayload struct {
	ID               uint             `json:"id"`
	Name             string           `json:"name"`
	Description      string           `json:"description,omitempty"`
	IsActive         bool             `json:"is_active"`
	Version          int              `json:"version"`
	Tags             []string         `json:"tags,omitempty"`
	ProviderConfigs  []map[string]any `json:"provider_configs,omitempty"`
	Budgets          []map[string]any `json:"budgets,omitempty"`
	RateLimit        map[string]any   `json:"rate_limit,omitempty"`
	CalendarAligned  bool             `json:"calendar_aligned"`
	MCPToolGroups    []map[string]any `json:"mcp_tool_groups,omitempty"`
	MCPServers       []map[string]any `json:"mcp_servers,omitempty"`
	MCPToolOverrides []map[string]any `json:"mcp_tool_overrides,omitempty"`
	CreatedAt        time.Time        `json:"created_at"`
	UpdatedAt        time.Time        `json:"updated_at"`
}

func accessProfileFromRow(row tables.TableAccessProfile) accessProfilePayload {
	spec := row.Spec()
	return accessProfilePayload{
		ID: row.ID, Name: row.Name, Description: row.Description, IsActive: row.IsActive,
		Version: row.Version, Tags: row.ParsedTags, CalendarAligned: row.CalendarAligned,
		ProviderConfigs:  specMapSlice(spec, "provider_configs"),
		Budgets:          specMapSlice(spec, "budgets"),
		RateLimit:        specMap(spec, "rate_limit"),
		MCPToolGroups:    specMapSlice(spec, "mcp_tool_groups"),
		MCPServers:       specMapSlice(spec, "mcp_servers"),
		MCPToolOverrides: specMapSlice(spec, "mcp_tool_overrides"),
		CreatedAt:        row.CreatedAt, UpdatedAt: row.UpdatedAt,
	}
}

func (p accessProfilePayload) toRow() tables.TableAccessProfile {
	return tables.TableAccessProfile{
		ID: p.ID, Name: p.Name, Description: p.Description, IsActive: p.IsActive,
		Version: p.Version, CalendarAligned: p.CalendarAligned, ParsedTags: p.Tags,
		ParsedSpec: map[string]any{
			"provider_configs":   p.ProviderConfigs,
			"budgets":            p.Budgets,
			"rate_limit":         p.RateLimit,
			"mcp_tool_groups":    p.MCPToolGroups,
			"mcp_servers":        p.MCPServers,
			"mcp_tool_overrides": p.MCPToolOverrides,
		},
		CreatedAt: p.CreatedAt, UpdatedAt: p.UpdatedAt,
	}
}

func (h *WorkspaceHandler) listAccessProfiles(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	rows, err := store.ListAccessProfiles(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to list access profiles")
		return
	}
	search := strings.ToLower(string(ctx.QueryArgs().Peek("search")))
	tagFilter := string(ctx.QueryArgs().Peek("tags"))
	activeFilter := string(ctx.QueryArgs().Peek("is_active"))
	items := make([]accessProfilePayload, 0, len(rows))
	for _, row := range rows {
		item := accessProfileFromRow(row)
		if search != "" && !strings.Contains(strings.ToLower(item.Name), search) && !strings.Contains(strings.ToLower(item.Description), search) {
			continue
		}
		if tagFilter != "" {
			wanted := map[string]bool{}
			for _, tag := range strings.Split(tagFilter, ",") {
				wanted[strings.TrimSpace(tag)] = true
			}
			matched := false
			for _, tag := range item.Tags {
				if wanted[tag] {
					matched = true
					break
				}
			}
			if !matched {
				continue
			}
		}
		if activeFilter == "true" && !item.IsActive {
			continue
		}
		if activeFilter == "false" && item.IsActive {
			continue
		}
		items = append(items, item)
	}
	limit := queryInt(ctx, "limit", 0)
	offset := queryInt(ctx, "offset", 0)
	total := len(items)
	if offset > total {
		offset = total
	}
	end := total
	if limit > 0 && offset+limit < end {
		end = offset + limit
	}
	if limit > 0 {
		items = items[offset:end]
	}
	SendJSON(ctx, map[string]any{"access_profiles": items, "count": len(items), "total_count": total})
}

func (h *WorkspaceHandler) createAccessProfile(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	var payload accessProfilePayload
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	payload.Name = strings.TrimSpace(payload.Name)
	if payload.Name == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "name is required")
		return
	}
	existing, err := store.ListAccessProfiles(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to list access profiles")
		return
	}
	for _, row := range existing {
		if strings.EqualFold(row.Name, payload.Name) {
			SendError(ctx, fasthttp.StatusConflict, "a profile with this name already exists")
			return
		}
	}
	now := time.Now().UTC()
	row := payload.toRow()
	row.ID = 0
	row.Version = 1
	row.CreatedAt = now
	row.UpdatedAt = now
	if err := store.CreateAccessProfile(ctx, &row); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to save access profile")
		return
	}
	SendJSONWithStatus(ctx, map[string]any{"access_profile": accessProfileFromRow(row)}, fasthttp.StatusCreated)
}

func (h *WorkspaceHandler) getAccessProfile(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	id, ok := pathUint(ctx, "id")
	if !ok {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid profile id")
		return
	}
	row, err := store.GetAccessProfile(ctx, id)
	if isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "profile not found")
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load access profile")
		return
	}
	SendJSON(ctx, map[string]any{"access_profile": accessProfileFromRow(*row), "role_attachments": []any{}, "user_copy_count": 0})
}

func (h *WorkspaceHandler) updateAccessProfile(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	id, ok := pathUint(ctx, "id")
	if !ok {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid profile id")
		return
	}
	existing, err := store.GetAccessProfile(ctx, id)
	if isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "profile not found")
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load access profile")
		return
	}
	current := accessProfileFromRow(*existing)
	var patch map[string]any
	if err := json.Unmarshal(ctx.PostBody(), &patch); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	raw, _ := json.Marshal(current)
	merged := map[string]any{}
	_ = json.Unmarshal(raw, &merged)
	for key, value := range patch {
		merged[key] = value
	}
	updatedRaw, _ := json.Marshal(merged)
	var updated accessProfilePayload
	if err := json.Unmarshal(updatedRaw, &updated); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid request payload")
		return
	}
	row := updated.toRow()
	row.ID = existing.ID
	row.CreatedAt = existing.CreatedAt
	row.UpdatedAt = time.Now().UTC()
	row.Version = existing.Version + 1
	if err := store.UpdateAccessProfile(ctx, &row); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to update access profile")
		return
	}
	SendJSON(ctx, map[string]any{"access_profile": accessProfileFromRow(row)})
}

func (h *WorkspaceHandler) deleteAccessProfile(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	id, ok := pathUint(ctx, "id")
	if !ok {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid profile id")
		return
	}
	if err := store.DeleteAccessProfile(ctx, id); isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "profile not found")
		return
	} else if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to delete access profile")
		return
	}
	SendJSON(ctx, map[string]string{"message": "deleted"})
}

func (h *WorkspaceHandler) setAccessProfileActive(ctx *fasthttp.RequestCtx, active bool) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	id, ok := pathUint(ctx, "id")
	if !ok {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid profile id")
		return
	}
	row, err := store.GetAccessProfile(ctx, id)
	if isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "profile not found")
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load access profile")
		return
	}
	row.IsActive = active
	row.UpdatedAt = time.Now().UTC()
	if err := store.UpdateAccessProfile(ctx, row); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to update access profile")
		return
	}
	SendJSON(ctx, map[string]any{"access_profile": accessProfileFromRow(*row)})
}

func (h *WorkspaceHandler) activateAccessProfile(ctx *fasthttp.RequestCtx) {
	h.setAccessProfileActive(ctx, true)
}

func (h *WorkspaceHandler) deactivateAccessProfile(ctx *fasthttp.RequestCtx) {
	h.setAccessProfileActive(ctx, false)
}

func (h *WorkspaceHandler) cloneAccessProfile(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	id, ok := pathUint(ctx, "id")
	if !ok {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid profile id")
		return
	}
	existing, err := store.GetAccessProfile(ctx, id)
	if isStoreNotFound(err) {
		SendError(ctx, fasthttp.StatusNotFound, "profile not found")
		return
	}
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to load access profile")
		return
	}
	var body struct {
		Name string `json:"name"`
	}
	_ = json.Unmarshal(ctx.PostBody(), &body)
	clone := *existing
	clone.ID = 0
	if body.Name != "" {
		clone.Name = body.Name
	} else {
		clone.Name = existing.Name + " copy"
	}
	clone.IsActive = false
	clone.Version = 1
	now := time.Now().UTC()
	clone.CreatedAt = now
	clone.UpdatedAt = now
	if err := store.CreateAccessProfile(ctx, &clone); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to clone access profile")
		return
	}
	SendJSONWithStatus(ctx, map[string]any{"access_profile": accessProfileFromRow(clone)}, fasthttp.StatusCreated)
}

func (h *WorkspaceHandler) listUserAccessProfiles(ctx *fasthttp.RequestCtx) {
	SendJSON(ctx, map[string]any{"access_profiles": []any{}})
}
