package handlers

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/valyala/fasthttp"
)

func (h *WorkspaceHandler) scimServiceProviderConfig(ctx *fasthttp.RequestCtx) {
	SendJSON(ctx, map[string]any{
		"schemas": []string{"urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"},
		"patch":   map[string]any{"supported": true},
		"bulk":    map[string]any{"supported": false, "maxOperations": 0, "maxPayloadSize": 0},
		"filter":  map[string]any{"supported": true, "maxResults": 200},
		"changePassword": map[string]any{"supported": false},
		"sort":    map[string]any{"supported": false},
		"etag":    map[string]any{"supported": false},
		"authenticationSchemes": []map[string]any{{
			"type":        "oauthbearertoken",
			"name":        "OAuth Bearer Token",
			"description": "Authentication scheme using the bearer token configured in SCIM settings",
		}},
	})
}

func (h *WorkspaceHandler) scimSchemas(ctx *fasthttp.RequestCtx) {
	SendJSON(ctx, map[string]any{
		"schemas":      []string{"urn:ietf:params:scim:api:messages:2.0:ListResponse"},
		"totalResults": 1,
		"itemsPerPage": 1,
		"startIndex":   1,
		"Resources": []map[string]any{{
			"id":          "urn:ietf:params:scim:schemas:core:2.0:User",
			"name":        "User",
			"description": "User Account",
			"attributes": []map[string]any{
				{"name": "userName", "type": "string", "required": true},
				{"name": "active", "type": "boolean"},
			},
		}},
	})
}

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
	filter := string(ctx.QueryArgs().Peek("filter"))
	if filter != "" {
		users = scimFilterUsers(users, filter)
	}
	startIndex := queryInt(ctx, "startIndex", 1)
	if startIndex < 1 {
		startIndex = 1
	}
	count := queryInt(ctx, "count", 100)
	if count <= 0 {
		count = 100
	}
	total := len(users)
	offset := startIndex - 1
	if offset > total {
		offset = total
	}
	end := offset + count
	if end > total {
		end = total
	}
	page := users[offset:end]
	resources := make([]map[string]any, 0, len(page))
	for _, user := range page {
		resources = append(resources, scimUserResource(user))
	}
	SendJSON(ctx, map[string]any{
		"schemas":      []string{"urn:ietf:params:scim:api:messages:2.0:ListResponse"},
		"totalResults": total,
		"itemsPerPage": len(resources),
		"startIndex":   startIndex,
		"Resources":    resources,
	})
}

func scimFilterUsers(users []*tables.TableUser, filter string) []*tables.TableUser {
	filter = strings.TrimSpace(filter)
	// userName eq "value"
	if strings.HasPrefix(strings.ToLower(filter), `username eq `) {
		raw := strings.TrimSpace(filter[len(`username eq `):])
		raw = strings.Trim(raw, `"`)
		out := make([]*tables.TableUser, 0)
		for _, user := range users {
			if strings.EqualFold(user.Username, raw) {
				out = append(out, user)
			}
		}
		return out
	}
	return users
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
		UserName   string `json:"userName"`
		ExternalID string `json:"externalId"`
		Emails     []struct {
			Value   string `json:"value"`
			Primary bool   `json:"primary"`
		} `json:"emails"`
		Active bool `json:"active"`
		Roles  []struct {
			Value string `json:"value"`
		} `json:"roles"`
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
	email := scimEmailFromBody(body.Emails)
	role := "user"
	if len(body.Roles) > 0 && body.Roles[0].Value != "" {
		role = body.Roles[0].Value
	}
	user := &tables.TableUser{
		ID:       uuid.NewString(),
		Username: username,
		Email:    email,
		Password: uuid.NewString(),
		Role:     role,
		Status:   scimStatusFromActive(body.Active),
	}
	if body.ExternalID != "" {
		user.ExternalID = body.ExternalID
	}
	if err := h.store.ConfigStore.CreateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to create user")
		return
	}
	SendJSONWithStatus(ctx, scimUserResource(user), fasthttp.StatusCreated)
}

func (h *WorkspaceHandler) scimPutUser(ctx *fasthttp.RequestCtx) {
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
	var body map[string]any
	if err := json.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid scim payload")
		return
	}
	applySCIMUserPatch(user, body)
	user.UpdatedAt = time.Now().UTC()
	if err := h.store.ConfigStore.UpdateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to update user")
		return
	}
	SendJSON(ctx, scimUserResource(user))
}

func (h *WorkspaceHandler) scimPatchUser(ctx *fasthttp.RequestCtx) {
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
	var body struct {
		Operations []struct {
			Op    string `json:"op"`
			Path  string `json:"path"`
			Value any    `json:"value"`
		} `json:"Operations"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid scim patch payload")
		return
	}
	for _, op := range body.Operations {
		switch strings.ToLower(op.Op) {
		case "replace":
			patch := map[string]any{}
			if op.Path != "" {
				patch[op.Path] = op.Value
			} else if m, ok := op.Value.(map[string]any); ok {
				patch = m
			}
			applySCIMUserPatch(user, patch)
		case "add", "remove":
			// no-op for minimal support
		}
	}
	user.UpdatedAt = time.Now().UTC()
	if err := h.store.ConfigStore.UpdateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "failed to update user")
		return
	}
	SendJSON(ctx, scimUserResource(user))
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

func applySCIMUserPatch(user *tables.TableUser, patch map[string]any) {
	if user == nil || len(patch) == 0 {
		return
	}
	if v, ok := patch["userName"].(string); ok && v != "" {
		user.Username = v
	}
	if v, ok := patch["active"].(bool); ok {
		user.Status = scimStatusFromActive(v)
	}
	if v, ok := patch["externalId"].(string); ok {
		user.ExternalID = v
	}
	if roles, ok := patch["roles"].([]any); ok && len(roles) > 0 {
		if roleMap, ok := roles[0].(map[string]any); ok {
			if role, ok := roleMap["value"].(string); ok && role != "" {
				user.Role = role
			}
		}
	}
	if emails, ok := patch["emails"].([]any); ok {
		for _, item := range emails {
			if m, ok := item.(map[string]any); ok {
				if email, ok := m["value"].(string); ok && email != "" {
					user.Email = email
					break
				}
			}
		}
	}
}

func scimEmailFromBody(emails []struct {
	Value   string `json:"value"`
	Primary bool   `json:"primary"`
}) string {
	email := ""
	for _, item := range emails {
		if item.Value != "" {
			email = item.Value
			if item.Primary {
				break
			}
		}
	}
	return email
}

func scimStatusFromActive(active bool) string {
	if active {
		return tables.UserStatusApproved
	}
	return tables.UserStatusPending
}

func scimUserResource(user *tables.TableUser) map[string]any {
	if user == nil {
		return map[string]any{}
	}
	email := user.Email
	if email == "" {
		email = user.Username
	}
	externalID := user.ExternalID
	resource := map[string]any{
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
	if externalID != "" {
		resource["externalId"] = externalID
	}
	return resource
}
