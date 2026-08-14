package handlers

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/fasthttp/router"
	"github.com/google/uuid"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/unifai/unifai/framework/encrypt"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

// SessionHandler manages HTTP requests for session operations
type SessionHandler struct {
	configStore   configstore.ConfigStore
	wsTicketStore *WSTicketStore
}

// NewSessionHandler creates a new session handler instance
func NewSessionHandler(configStore configstore.ConfigStore, wsTicketStore *WSTicketStore) *SessionHandler {
	return &SessionHandler{
		configStore:   configStore,
		wsTicketStore: wsTicketStore,
	}
}

// RegisterRoutes registers the session-related routes
func (h *SessionHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	r.POST("/api/session/login", lib.ChainMiddlewares(h.login, middlewares...))
	r.POST("/api/session/logout", lib.ChainMiddlewares(h.logout, middlewares...))
	r.GET("/api/session/is-auth-enabled", lib.ChainMiddlewares(h.isAuthEnabled, middlewares...))
	r.POST("/api/session/ws-ticket", lib.ChainMiddlewares(h.issueWSTicket, middlewares...))
	r.GET("/api/session/users", lib.ChainMiddlewares(h.getUsers, middlewares...))
	r.POST("/api/session/users", lib.ChainMiddlewares(h.createUser, middlewares...))
	r.PUT("/api/session/users/{id}", lib.ChainMiddlewares(h.updateUser, middlewares...))
	r.DELETE("/api/session/users/{id}", lib.ChainMiddlewares(h.deleteUser, middlewares...))
}

// isAuthEnabled handles GET /api/session/is-auth-enabled - Check if auth is enabled
func (h *SessionHandler) isAuthEnabled(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendJSON(ctx, map[string]any{
			"is_auth_enabled": false,
			"has_valid_token": false,
			"auth_type":       "none",
			"role":            "",
			"username":        "",
		})
		return
	}
	authConfig, err := h.configStore.GetAuthConfig(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, fmt.Sprintf("Failed to get auth config: %v", err))
		return
	}
	if authConfig == nil {
		SendJSON(ctx, map[string]any{
			"is_auth_enabled": false,
			"has_valid_token": false,
			"auth_type":       "none",
			"role":            "",
			"username":        "",
		})
		return
	}
	// Check if the header has a token and is valid (Authorization header or cookie)
	token := ""
	if authHeader := string(ctx.Request.Header.Peek("Authorization")); strings.HasPrefix(authHeader, "Bearer ") {
		token = strings.TrimPrefix(authHeader, "Bearer ")
	}
	if token == "" {
		token = string(ctx.Request.Header.Cookie("token"))
	}
	hasValidToken := false
	role := ""
	username := ""
	if token != "" {
		session, err := h.configStore.GetSession(ctx, token)
		if err == nil && session != nil && session.ExpiresAt.After(time.Now()) {
			hasValidToken = true
			role = session.Role
			username = session.Username
			if role == "" {
				role = "admin"
			}
			if username == "" {
				username = "admin"
			}
		}
	}
	SendJSON(ctx, map[string]any{
		"is_auth_enabled": authConfig.IsEnabled,
		"has_valid_token": hasValidToken,
		"auth_type":       dashboardAuthType(authConfig.IsEnabled),
		"role":            role,
		"username":        username,
	})
}

// dashboardAuthType reports the dashboard session auth mode for frontend flows.
func dashboardAuthType(isEnabled bool) string {
	if isEnabled {
		return "password"
	}
	return "none"
}

// login handles POST /api/session/login - Login a user
func (h *SessionHandler) login(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendError(ctx, fasthttp.StatusForbidden, "Authentication is not enabled")
		return
	}
	payload := struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}{}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}

	// Get auth config
	authConfig, err := h.configStore.GetAuthConfig(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, fmt.Sprintf("Failed to get auth config: %v", err))
		return
	}

	// Check if auth is enabled
	if authConfig == nil || !authConfig.IsEnabled {
		SendError(ctx, fasthttp.StatusForbidden, "Authentication is not enabled")
		return
	}

	// Verify credentials
	sessionRole := "admin"
	sessionUsername := payload.Username

	dbUser, err := h.configStore.GetUserByUsername(ctx, payload.Username)
	if err == nil && dbUser != nil {
		compare, err := encrypt.CompareHash(dbUser.Password, payload.Password)
		if err != nil || !compare {
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
		sessionRole = dbUser.Role
	} else {
		if payload.Username != authConfig.AdminUserName.GetValue() {
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
		compare, err := encrypt.CompareHash(authConfig.AdminPassword.GetValue(), payload.Password)
		if err != nil || !compare {
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
	}

	// Creating a new session
	token := uuid.New().String()
	session := &tables.SessionsTable{
		Token:     token,
		ExpiresAt: time.Now().Add(time.Hour * 24 * 30), // 30 days
		Username:  sessionUsername,
		Role:      sessionRole,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	err = h.configStore.CreateSession(ctx, session)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, fmt.Sprintf("Failed to create session: %v", err))
		return
	}

	// Setting cookies
	cookie := fasthttp.AcquireCookie()
	defer fasthttp.ReleaseCookie(cookie)
	cookie.SetKey("token")
	cookie.SetValue(token)
	cookie.SetExpire(time.Now().Add(time.Hour * 24 * 30))
	cookie.SetPath("/")
	cookie.SetHTTPOnly(true)
	cookie.SetSameSite(fasthttp.CookieSameSiteLaxMode)
	// Check if source is https then set secure
	if string(ctx.Request.Header.Peek("X-Forwarded-Proto")) == "https" {
		cookie.SetSecure(true)
	}
	ctx.Response.Header.SetCookie(cookie)

	SendJSON(ctx, map[string]any{
		"message": "Login successful",
	})
}

// logout handles POST /api/session/logout - Logout a user
func (h *SessionHandler) logout(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendError(ctx, fasthttp.StatusForbidden, "Authentication is not enabled")
		return
	}
	// Get token from Authorization header
	token := string(ctx.Request.Header.Peek("Authorization"))
	token = strings.TrimPrefix(token, "Bearer ")

	// If no token in header, try to get from cookie
	if token == "" {
		token = string(ctx.Request.Header.Cookie("token"))
	}

	// clear token from cookies
	cookie := fasthttp.AcquireCookie()
	defer fasthttp.ReleaseCookie(cookie)
	cookie.SetKey("token")
	cookie.SetValue("")
	cookie.SetExpire(time.Now().Add(-time.Hour * 24 * 30))
	cookie.SetPath("/")
	cookie.SetHTTPOnly(true)
	cookie.SetSameSite(fasthttp.CookieSameSiteLaxMode)
	// Check if source is https then set secure
	if string(ctx.Request.Header.Peek("X-Forwarded-Proto")) == "https" {
		cookie.SetSecure(true)
	}
	ctx.Response.Header.SetCookie(cookie)

	// delete session from database if token exists
	if token != "" {
		err := h.configStore.DeleteSession(ctx, token)
		if err != nil && !errors.Is(err, configstore.ErrNotFound) {
			logger.Error("failed to delete session during logout: %v", err)
			SendError(ctx, fasthttp.StatusInternalServerError, "Failed to invalidate session. Please try again.")
			return
		}
	}

	SendJSON(ctx, map[string]any{
		"message": "Logout successful",
	})
}

// issueWSTicket handles POST /api/session/ws-ticket - Issue a short-lived ticket for WebSocket auth.
// The caller must already be authenticated (via cookie or Authorization header).
// Returns a one-time-use ticket that the frontend passes as ?ticket= when opening the WebSocket.
func (h *SessionHandler) issueWSTicket(ctx *fasthttp.RequestCtx) {
	if h.wsTicketStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "WebSocket tickets are not available")
		return
	}
	sessionToken, ok := ctx.UserValue(schemas.UnifAIContextKeySessionToken).(string)
	if !ok {
		SendError(ctx, fasthttp.StatusUnauthorized, "Unauthorized")
		return
	}
	if sessionToken == "" {
		// This is the case where auth is not configured or not enabled
		sessionToken = "dummy-session"
	}
	ticket, err := h.wsTicketStore.Issue(sessionToken)
	if err != nil {
		logger.Error("failed to issue WS ticket: %v", err)
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to issue WebSocket ticket")
		return
	}
	SendJSON(ctx, map[string]any{
		"ticket": ticket,
	})
}

// extractParam extracts a path param and sends an error if missing.
func (h *SessionHandler) extractParam(ctx *fasthttp.RequestCtx, name string) (string, bool) {
	val := ctx.UserValue(name)
	if val == nil {
		SendError(ctx, fasthttp.StatusBadRequest, name+" is required")
		return "", false
	}
	s, ok := val.(string)
	if !ok || s == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid "+name)
		return "", false
	}
	return s, true
}

// isAdmin checks if the current request session belongs to an admin.
// When dashboard auth is disabled (or not configured), user-management APIs
// stay usable in open mode — otherwise create/list users always 403 with no
// way to bootstrap an admin session.
func (h *SessionHandler) isAdmin(ctx *fasthttp.RequestCtx) bool {
	if h.configStore == nil {
		return true
	}
	authConfig, err := h.configStore.GetAuthConfig(ctx)
	if err != nil {
		return false
	}
	if authConfig == nil || !authConfig.IsEnabled {
		return true
	}

	token := ""
	if authHeader := string(ctx.Request.Header.Peek("Authorization")); strings.HasPrefix(authHeader, "Bearer ") {
		token = strings.TrimPrefix(authHeader, "Bearer ")
	}
	if token == "" {
		token = string(ctx.Request.Header.Cookie("token"))
	}
	if token == "" {
		return false
	}
	session, err := h.configStore.GetSession(ctx, token)
	if err != nil || session == nil || session.ExpiresAt.Before(time.Now()) {
		return false
	}
	return session.Role == "admin"
}

// getUsers handles GET /api/session/users - Get all users (Admin only)
func (h *SessionHandler) getUsers(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	users, err := h.configStore.GetUsers(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	// Redact passwords
	for _, u := range users {
		u.Password = ""
	}
	SendJSON(ctx, users)
}

// createUser handles POST /api/session/users - Create a new user (Admin only)
func (h *SessionHandler) createUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	var payload struct {
		Username           string  `json:"username"`
		Password           string  `json:"password"`
		Role               string  `json:"role"`
		Budget             float64 `json:"budget"`
		RateLimit          int     `json:"rate_limit"`
		AllowedPromptRepos string  `json:"allowed_prompt_repos"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	if payload.Username == "" || payload.Password == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Username and password are required")
		return
	}
	if payload.Role != "admin" && payload.Role != "user" {
		payload.Role = "user"
	}

	hashedPassword, err := encrypt.Hash(payload.Password)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to hash password")
		return
	}

	user := &tables.TableUser{
		ID:                 uuid.New().String(),
		Username:           payload.Username,
		Password:           hashedPassword,
		Role:               payload.Role,
		Budget:             payload.Budget,
		RateLimit:          payload.RateLimit,
		AllowedPromptRepos: payload.AllowedPromptRepos,
		CreatedAt:          time.Now(),
		UpdatedAt:          time.Now(),
	}

	if err := h.configStore.CreateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to create user: "+err.Error())
		return
	}

	user.Password = ""
	SendJSON(ctx, user)
}

// updateUser handles PUT /api/session/users/{id} - Update user (Admin only)
func (h *SessionHandler) updateUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	id, ok := h.extractParam(ctx, "id")
	if !ok {
		return
	}

	existingUser, err := h.configStore.GetUserByID(ctx, id)
	if err != nil {
		SendError(ctx, fasthttp.StatusNotFound, "User not found")
		return
	}

	var payload struct {
		Username           string  `json:"username"`
		Password           string  `json:"password"`
		Role               string  `json:"role"`
		Budget             float64 `json:"budget"`
		RateLimit          int     `json:"rate_limit"`
		AllowedPromptRepos *string `json:"allowed_prompt_repos"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}

	if payload.Username != "" {
		existingUser.Username = payload.Username
	}
	if payload.Password != "" {
		hashedPassword, err := encrypt.Hash(payload.Password)
		if err != nil {
			SendError(ctx, fasthttp.StatusInternalServerError, "Failed to hash password")
			return
		}
		existingUser.Password = hashedPassword
	}
	if payload.Role == "admin" || payload.Role == "user" {
		existingUser.Role = payload.Role
	}
	existingUser.Budget = payload.Budget
	existingUser.RateLimit = payload.RateLimit
	if payload.AllowedPromptRepos != nil {
		existingUser.AllowedPromptRepos = *payload.AllowedPromptRepos
	}
	existingUser.UpdatedAt = time.Now()

	if err := h.configStore.UpdateUser(ctx, existingUser); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to update user: "+err.Error())
		return
	}

	existingUser.Password = ""
	SendJSON(ctx, existingUser)
}

// deleteUser handles DELETE /api/session/users/{id} - Delete user (Admin only)
func (h *SessionHandler) deleteUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	id, ok := h.extractParam(ctx, "id")
	if !ok {
		return
	}

	if err := h.configStore.DeleteUser(ctx, id); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to delete user: "+err.Error())
		return
	}

	SendJSON(ctx, map[string]any{
		"message": "User deleted successfully",
	})
}
