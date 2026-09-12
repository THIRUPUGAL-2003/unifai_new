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

// normalizeUserRole accepts admin/user or a custom RBAC role that exists in the workspace store.
// Returns ("", false) when the role is invalid so callers can 400 instead of silently coercing to "user".
func (h *SessionHandler) normalizeUserRole(ctx *fasthttp.RequestCtx, role string) (string, bool) {
	role = strings.TrimSpace(role)
	if role == "" {
		return "user", true
	}
	if role == "admin" || role == "user" {
		return role, true
	}
	ws, ok := configstore.AsWorkspaceStore(h.configStore)
	if !ok || ws == nil {
		return "", false
	}
	_ = ws.EnsureRBACRoles(ctx)
	rows, err := ws.ListRBACRoles(ctx)
	if err != nil {
		return "", false
	}
	for _, row := range rows {
		if strings.EqualFold(strings.TrimSpace(row.Name), role) {
			return row.Name, true
		}
	}
	return "", false
}

// RegisterRoutes registers the session-related routes
func (h *SessionHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	r.POST("/api/session/login", lib.ChainMiddlewares(h.login, middlewares...))
	r.POST("/api/session/logout", lib.ChainMiddlewares(h.logout, middlewares...))
	r.GET("/api/session/is-auth-enabled", lib.ChainMiddlewares(h.isAuthEnabled, middlewares...))
	r.POST("/api/session/ws-ticket", lib.ChainMiddlewares(h.issueWSTicket, middlewares...))
	r.POST("/api/session/register", lib.ChainMiddlewares(h.register, middlewares...))
	r.POST("/api/session/forgot-password", lib.ChainMiddlewares(h.forgotPassword, middlewares...))
	r.POST("/api/session/reset-password", lib.ChainMiddlewares(h.resetPassword, middlewares...))
	r.GET("/api/session/users", lib.ChainMiddlewares(h.getUsers, middlewares...))
	r.POST("/api/session/users", lib.ChainMiddlewares(h.createUser, middlewares...))
	r.PUT("/api/session/users/{id}", lib.ChainMiddlewares(h.updateUser, middlewares...))
	r.DELETE("/api/session/users/{id}", lib.ChainMiddlewares(h.deleteUser, middlewares...))
	r.POST("/api/session/users/{id}/approve", lib.ChainMiddlewares(h.approveUser, middlewares...))
	r.POST("/api/session/users/{id}/reject", lib.ChainMiddlewares(h.rejectUser, middlewares...))
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
	allowedSections := ""
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
			if username != "" && (role == "admin" || role == "user") {
				if dbUser, err := h.configStore.GetUserByUsername(ctx, username); err == nil && dbUser != nil {
					allowedSections = dbUser.AllowedSections
				}
			}
		}
	}
	SendJSON(ctx, map[string]any{
		"is_auth_enabled":  authConfig.IsEnabled,
		"has_valid_token":  hasValidToken,
		"auth_type":        dashboardAuthType(authConfig.IsEnabled),
		"role":             role,
		"username":         username,
		"allowed_sections": allowedSections,
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

	payload.Username = strings.TrimSpace(payload.Username)
	if locked, retryAfter, err := checkLoginLockout(h.configStore, ctx, payload.Username); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to check login lockout")
		return
	} else if locked {
		mins := int(retryAfter.Minutes()) + 1
		SendError(ctx, fasthttp.StatusTooManyRequests, fmt.Sprintf("Too many failed login attempts. Try again in about %d minutes", mins))
		return
	}

	// Verify credentials
	sessionRole := "admin"
	sessionUsername := payload.Username
	notifyEmail := ""

	dbUser, err := h.configStore.GetUserByUsername(ctx, payload.Username)
	if err == nil && dbUser != nil {
		if !dbUser.IsApproved() {
			switch dbUser.Status {
			case tables.UserStatusPending:
				SendError(ctx, fasthttp.StatusForbidden, "Your registration is waiting for admin approval")
			case tables.UserStatusRejected:
				SendError(ctx, fasthttp.StatusForbidden, "Admin has not accepted your request")
			default:
				SendError(ctx, fasthttp.StatusForbidden, "Your account is not active")
			}
			return
		}
		compare, err := encrypt.CompareHash(dbUser.Password, payload.Password)
		if err != nil || !compare {
			if locked, retryAfter := recordLoginFailure(h.configStore, ctx, payload.Username); locked {
				mins := int(retryAfter.Minutes()) + 1
				SendError(ctx, fasthttp.StatusTooManyRequests, fmt.Sprintf("Too many failed login attempts. Account locked for about %d minutes", mins))
				return
			}
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
		sessionRole = dbUser.Role
		notifyEmail = dbUser.Email
	} else {
		if payload.Username != authConfig.AdminUserName.GetValue() {
			if locked, retryAfter := recordLoginFailure(h.configStore, ctx, payload.Username); locked {
				mins := int(retryAfter.Minutes()) + 1
				SendError(ctx, fasthttp.StatusTooManyRequests, fmt.Sprintf("Too many failed login attempts. Account locked for about %d minutes", mins))
				return
			}
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
		compare, err := encrypt.CompareHash(authConfig.AdminPassword.GetValue(), payload.Password)
		if err != nil || !compare {
			if locked, retryAfter := recordLoginFailure(h.configStore, ctx, payload.Username); locked {
				mins := int(retryAfter.Minutes()) + 1
				SendError(ctx, fasthttp.StatusTooManyRequests, fmt.Sprintf("Too many failed login attempts. Account locked for about %d minutes", mins))
				return
			}
			SendError(ctx, fasthttp.StatusUnauthorized, "Invalid username or password")
			return
		}
	}

	clearLoginFailures(h.configStore, ctx, payload.Username)

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

	trySendLoginNoticeEmail(h.configStore, ctx, sessionUsername, notifyEmail)

	SendJSON(ctx, map[string]any{
		"message": "Login successful",
		"role":    sessionRole,
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

func alreadyRegisteredMessage(existing *tables.TableUser) string {
	switch existing.Status {
	case tables.UserStatusPending:
		return "This username already has a registration waiting for admin approval"
	case tables.UserStatusRejected:
		return "Admin has not accepted this registration"
	default:
		return "Username is already registered"
	}
}

// assertEmailAvailable rejects when another user already owns this email.
// exceptUserID allows the same user to keep/update their own email.
// Returns false after sending the HTTP error.
func (h *SessionHandler) assertEmailAvailable(ctx *fasthttp.RequestCtx, email, exceptUserID string) bool {
	email = strings.TrimSpace(strings.ToLower(email))
	if email == "" || h.configStore == nil {
		return true
	}
	other, err := h.configStore.GetUserByEmail(ctx, email)
	if err != nil || other == nil {
		return true
	}
	if exceptUserID != "" && other.ID == exceptUserID {
		return true
	}
	SendError(ctx, fasthttp.StatusConflict, "This email is already registered with another account")
	return false
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
	visible := make([]*tables.TableUser, 0, len(users))
	for _, u := range users {
		if u == nil {
			continue
		}
		// Denied rows stay in DB for login messaging, but are not listed as users.
		if u.Status == tables.UserStatusRejected {
			continue
		}
		u.Password = ""
		visible = append(visible, u)
	}
	SendJSON(ctx, visible)
}

// createUser handles POST /api/session/users - Create a new user (Admin only)
func (h *SessionHandler) createUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	var payload struct {
		Username           string  `json:"username"`
		Email              string  `json:"email"`
		Password           string  `json:"password"`
		Role               string  `json:"role"`
		Budget             float64 `json:"budget"`
		RateLimit          int     `json:"rate_limit"`
		AllowedPromptRepos string  `json:"allowed_prompt_repos"`
		AllowedSections    string  `json:"allowed_sections"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	payload.Username = strings.TrimSpace(payload.Username)
	payload.Email = strings.TrimSpace(strings.ToLower(payload.Email))
	if payload.Username == "" || payload.Password == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Username and password are required")
		return
	}
	if failures := getPasswordPolicyFailures(payload.Password); len(failures) > 0 {
		SendError(ctx, fasthttp.StatusBadRequest, "Password must include "+strings.Join(failures, ", "))
		return
	}
	role, roleOK := h.normalizeUserRole(ctx, payload.Role)
	if !roleOK {
		SendError(ctx, fasthttp.StatusBadRequest, "Unknown role — create it under Roles & Permissions first, or use admin/user")
		return
	}
	payload.Role = role

	hashedPassword, err := encrypt.Hash(payload.Password)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to hash password")
		return
	}

	now := time.Now()
	if existing, err := h.configStore.GetUserByUsername(ctx, payload.Username); err == nil && existing != nil {
		if existing.IsApproved() {
			SendError(ctx, fasthttp.StatusConflict, "Username is already registered")
			return
		}
		// Admin create bypasses pending/denied — activate immediately.
		if payload.Email != "" && !h.assertEmailAvailable(ctx, payload.Email, existing.ID) {
			return
		}
		if payload.Email != "" {
			existing.Email = payload.Email
		}
		existing.Password = hashedPassword
		existing.Role = payload.Role
		existing.Status = tables.UserStatusApproved
		existing.Budget = payload.Budget
		existing.RateLimit = payload.RateLimit
		existing.AllowedPromptRepos = payload.AllowedPromptRepos
		existing.AllowedSections = payload.AllowedSections
		existing.ReviewedAt = &now
		existing.UpdatedAt = now
		if err := h.configStore.UpdateUser(ctx, existing); err != nil {
			logger.Error("failed to update pending governance user username=%s: %v", payload.Username, err)
			SendError(ctx, fasthttp.StatusInternalServerError, "Failed to create user")
			return
		}
		existing.Password = ""
		emailTo := strings.TrimSpace(payload.Email)
		if emailTo == "" {
			emailTo = strings.TrimSpace(existing.Email)
		}
		emailSent, emailErr := trySendWelcomeEmail(h.configStore, ctx, payload.Username, emailTo, payload.Password)
		SendJSON(ctx, map[string]any{
			"id":                   existing.ID,
			"username":             existing.Username,
			"email":                existing.Email,
			"role":                 existing.Role,
			"status":               existing.Status,
			"budget":               existing.Budget,
			"rate_limit":           existing.RateLimit,
			"allowed_prompt_repos": existing.AllowedPromptRepos,
			"allowed_sections":     existing.AllowedSections,
			"created_at":           existing.CreatedAt,
			"email_sent":           emailSent,
			"email_error":          emailErr,
		})
		return
	}

	if payload.Email != "" && !h.assertEmailAvailable(ctx, payload.Email, "") {
		return
	}

	user := &tables.TableUser{
		ID:                 uuid.New().String(),
		Username:           payload.Username,
		Email:              payload.Email,
		Password:           hashedPassword,
		Role:               payload.Role,
		Status:             tables.UserStatusApproved,
		Budget:             payload.Budget,
		RateLimit:          payload.RateLimit,
		AllowedPromptRepos: payload.AllowedPromptRepos,
		AllowedSections:    payload.AllowedSections,
		CreatedAt:          now,
		UpdatedAt:          now,
	}

	if err := h.configStore.CreateUser(ctx, user); err != nil {
		logger.Error("failed to create governance user username=%s: %v", payload.Username, err)
		errLower := strings.ToLower(err.Error())
		if strings.Contains(errLower, "duplicate") || strings.Contains(errLower, "unique") {
			SendError(ctx, fasthttp.StatusConflict, "Username is already registered")
			return
		}
		if strings.Contains(errLower, "column") && (strings.Contains(errLower, "status") || strings.Contains(errLower, "email") || strings.Contains(errLower, "reviewed_at") || strings.Contains(errLower, "external_id")) {
			SendError(ctx, fasthttp.StatusInternalServerError, "Database is missing user registration columns; restart the server to apply migrations")
			return
		}
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to create user")
		return
	}

	user.Password = ""
	emailSent, emailErr := trySendWelcomeEmail(h.configStore, ctx, payload.Username, payload.Email, payload.Password)
	SendJSON(ctx, map[string]any{
		"id":                   user.ID,
		"username":             user.Username,
		"email":                user.Email,
		"role":                 user.Role,
		"status":               user.Status,
		"budget":               user.Budget,
		"rate_limit":           user.RateLimit,
		"allowed_prompt_repos": user.AllowedPromptRepos,
		"allowed_sections":     user.AllowedSections,
		"created_at":           user.CreatedAt,
		"email_sent":           emailSent,
		"email_error":          emailErr,
	})
}

// forgotPassword emails a 6-digit OTP when the account has an email on file.
func (h *SessionHandler) forgotPassword(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store not available")
		return
	}
	var payload struct {
		Username string `json:"username"`
		Email    string `json:"email"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	payload.Username = strings.TrimSpace(payload.Username)
	payload.Email = strings.TrimSpace(payload.Email)

	// Always return the same message to avoid account enumeration.
	generic := map[string]any{"message": "If an account matches, a one-time code was sent by email"}

	var user *tables.TableUser
	if payload.Username != "" {
		if u, err := h.configStore.GetUserByUsername(ctx, payload.Username); err == nil {
			user = u
		}
	}
	if user == nil && payload.Email != "" {
		if u, err := h.configStore.GetUserByEmail(ctx, payload.Email); err == nil {
			user = u
		}
	}
	if user == nil || !user.IsApproved() || strings.TrimSpace(user.Email) == "" {
		SendJSON(ctx, generic)
		return
	}

	otp, err := generateOTP6()
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to generate OTP")
		return
	}
	hash, err := encrypt.Hash(otp)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to store OTP")
		return
	}
	row := &tables.TablePasswordResetOTP{
		Username:  user.Username,
		Email:     user.Email,
		OTPHash:   hash,
		ExpiresAt: time.Now().Add(passwordResetOTPTTL),
		CreatedAt: time.Now(),
	}
	if err := h.configStore.CreatePasswordResetOTP(ctx, row); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to store OTP")
		return
	}
	body := fmt.Sprintf(
		"Hello %s,\n\nYour UnifAI password reset code is: %s\n\nIt expires in %d minutes. If you did not request this, ignore this email.\n",
		user.Username, otp, int(passwordResetOTPTTL.Minutes()),
	)
	if err := sendAuthEmail(h.configStore, ctx, user.Email, "UnifAI password reset code", body); err != nil {
		logger.Warn("password reset OTP email failed username=%s: %v", user.Username, err)
		SendError(ctx, fasthttp.StatusBadRequest, "Could not send email. Ask an admin to configure SMTP in Settings → Security.")
		return
	}
	SendJSON(ctx, generic)
}

// resetPassword verifies OTP and sets a new password.
func (h *SessionHandler) resetPassword(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store not available")
		return
	}
	var payload struct {
		Username    string `json:"username"`
		OTP         string `json:"otp"`
		NewPassword string `json:"new_password"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	payload.Username = strings.TrimSpace(payload.Username)
	payload.OTP = strings.TrimSpace(payload.OTP)
	if payload.Username == "" || payload.OTP == "" || payload.NewPassword == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Username, OTP, and new password are required")
		return
	}
	if failures := getPasswordPolicyFailures(payload.NewPassword); len(failures) > 0 {
		SendError(ctx, fasthttp.StatusBadRequest, "Password must include "+strings.Join(failures, ", "))
		return
	}

	user, err := h.configStore.GetUserByUsername(ctx, payload.Username)
	if err != nil || user == nil || !user.IsApproved() {
		SendError(ctx, fasthttp.StatusUnauthorized, "Invalid OTP or username")
		return
	}
	sameAsCurrent, cmpErr := encrypt.CompareHash(user.Password, payload.NewPassword)
	if cmpErr == nil && sameAsCurrent {
		SendError(ctx, fasthttp.StatusBadRequest, "New password must be different from your current password")
		return
	}
	otpRow, err := h.configStore.GetLatestPasswordResetOTP(ctx, user.Username)
	if err != nil || otpRow == nil {
		SendError(ctx, fasthttp.StatusUnauthorized, "Invalid or expired OTP")
		return
	}
	ok, err := encrypt.CompareHash(otpRow.OTPHash, payload.OTP)
	if err != nil || !ok {
		SendError(ctx, fasthttp.StatusUnauthorized, "Invalid or expired OTP")
		return
	}
	hashed, err := encrypt.Hash(payload.NewPassword)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to hash password")
		return
	}
	user.Password = hashed
	user.UpdatedAt = time.Now()
	if err := h.configStore.UpdateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to update password")
		return
	}
	_ = h.configStore.MarkPasswordResetOTPUsed(ctx, otpRow.ID)
	// Do not clear login lockout here — failed-login lockout must still apply
	// until the timer expires (forgot-password must not bypass the lock).
	msg := "Password updated. You can sign in now."
	if locked, retryAfter, _ := checkLoginLockout(h.configStore, ctx, user.Username); locked {
		mins := int(retryAfter.Minutes()) + 1
		msg = fmt.Sprintf("Password updated. Your account is still locked for about %d minutes after failed logins — wait, then sign in with the new password.", mins)
	}
	SendJSON(ctx, map[string]any{"message": msg})
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
		Email              *string `json:"email"`
		Status             *string `json:"status"`
		Budget             float64 `json:"budget"`
		RateLimit          int     `json:"rate_limit"`
		AllowedPromptRepos *string `json:"allowed_prompt_repos"`
		AllowedSections    *string `json:"allowed_sections"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}

	if payload.Username != "" {
		existingUser.Username = payload.Username
	}
	if payload.Email != nil {
		newEmail := strings.TrimSpace(strings.ToLower(*payload.Email))
		if newEmail != "" && !h.assertEmailAvailable(ctx, newEmail, existingUser.ID) {
			return
		}
		existingUser.Email = newEmail
	}
	if payload.Status != nil && (*payload.Status == tables.UserStatusApproved || *payload.Status == tables.UserStatusPending || *payload.Status == tables.UserStatusRejected) {
		existingUser.Status = *payload.Status
	}
	if payload.Password != "" {
		if failures := getPasswordPolicyFailures(payload.Password); len(failures) > 0 {
			SendError(ctx, fasthttp.StatusBadRequest, "Password must include "+strings.Join(failures, ", "))
			return
		}
		hashedPassword, err := encrypt.Hash(payload.Password)
		if err != nil {
			SendError(ctx, fasthttp.StatusInternalServerError, "Failed to hash password")
			return
		}
		existingUser.Password = hashedPassword
	}
	if payload.Role != "" {
		role, ok := h.normalizeUserRole(ctx, payload.Role)
		if !ok {
			SendError(ctx, fasthttp.StatusBadRequest, "Unknown role — create it under Roles & Permissions first, or use admin/user")
			return
		}
		existingUser.Role = role
	}
	existingUser.Budget = payload.Budget
	existingUser.RateLimit = payload.RateLimit
	if payload.AllowedPromptRepos != nil {
		existingUser.AllowedPromptRepos = *payload.AllowedPromptRepos
	}
	if payload.AllowedSections != nil {
		existingUser.AllowedSections = *payload.AllowedSections
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

// register handles POST /api/session/register - public self-registration (pending approval).
func (h *SessionHandler) register(ctx *fasthttp.RequestCtx) {
	if h.configStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "User registration is not available")
		return
	}
	var payload struct {
		Username string `json:"username"`
		Email    string `json:"email"`
		Password string `json:"password"`
		Role     string `json:"role"`
	}
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid request payload")
		return
	}
	payload.Username = strings.TrimSpace(payload.Username)
	payload.Email = strings.TrimSpace(strings.ToLower(payload.Email))
	if payload.Username == "" || payload.Password == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Username and password are required")
		return
	}
	if payload.Email == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Email is required")
		return
	}
	if failures := getPasswordPolicyFailures(payload.Password); len(failures) > 0 {
		SendError(ctx, fasthttp.StatusBadRequest, "Password must include "+strings.Join(failures, ", "))
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

	now := time.Now()
	if existing, err := h.configStore.GetUserByUsername(ctx, payload.Username); err == nil && existing != nil {
		if existing.IsApproved() || existing.Status == tables.UserStatusPending {
			SendError(ctx, fasthttp.StatusConflict, alreadyRegisteredMessage(existing))
			return
		}
		// Denied users may request access again — send back to pending.
		if !h.assertEmailAvailable(ctx, payload.Email, existing.ID) {
			return
		}
		existing.Email = payload.Email
		existing.Password = hashedPassword
		existing.Role = payload.Role
		existing.Status = tables.UserStatusPending
		existing.ReviewedAt = nil
		existing.UpdatedAt = now
		if err := h.configStore.UpdateUser(ctx, existing); err != nil {
			SendError(ctx, fasthttp.StatusInternalServerError, "Failed to submit registration")
			return
		}
		SendJSON(ctx, map[string]any{
			"message": "Sent to the admin waiting for approval",
			"id":      existing.ID,
			"status":  existing.Status,
			"role":    existing.Role,
		})
		return
	}

	if !h.assertEmailAvailable(ctx, payload.Email, "") {
		return
	}

	user := &tables.TableUser{
		ID:        uuid.New().String(),
		Username:  payload.Username,
		Email:     payload.Email,
		Password:  hashedPassword,
		Role:      payload.Role,
		Status:    tables.UserStatusPending,
		CreatedAt: now,
		UpdatedAt: now,
	}
	if err := h.configStore.CreateUser(ctx, user); err != nil {
		logger.Error("failed to register user username=%s: %v", payload.Username, err)
		errLower := strings.ToLower(err.Error())
		if strings.Contains(errLower, "duplicate") || strings.Contains(errLower, "unique") {
			SendError(ctx, fasthttp.StatusConflict, "Username is already registered")
			return
		}
		if strings.Contains(errLower, "column") && (strings.Contains(errLower, "status") || strings.Contains(errLower, "email") || strings.Contains(errLower, "reviewed_at")) {
			SendError(ctx, fasthttp.StatusInternalServerError, "Database is missing user registration columns; restart the server to apply migrations")
			return
		}
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to submit registration")
		return
	}

	SendJSON(ctx, map[string]any{
		"message": "Sent to the admin waiting for approval",
		"id":      user.ID,
		"status":  user.Status,
		"role":    user.Role,
	})
}

// approveUser handles POST /api/session/users/{id}/approve
func (h *SessionHandler) approveUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	id, ok := h.extractParam(ctx, "id")
	if !ok {
		return
	}
	user, err := h.configStore.GetUserByID(ctx, id)
	if err != nil {
		SendError(ctx, fasthttp.StatusNotFound, "User not found")
		return
	}
	now := time.Now()
	user.Status = tables.UserStatusApproved
	user.ReviewedAt = &now
	user.UpdatedAt = now
	if err := h.configStore.UpdateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to approve user: "+err.Error())
		return
	}
	emailSent, emailErr := trySendRegistrationDecisionEmail(h.configStore, ctx, user.Username, user.Email, "approved")
	user.Password = ""
	SendJSON(ctx, map[string]any{
		"id":          user.ID,
		"username":    user.Username,
		"email":       user.Email,
		"role":        user.Role,
		"status":      user.Status,
		"reviewed_at": user.ReviewedAt,
		"updated_at":  user.UpdatedAt,
		"email_sent":  emailSent,
		"email_error": emailErr,
	})
}

// rejectUser handles POST /api/session/users/{id}/reject
func (h *SessionHandler) rejectUser(ctx *fasthttp.RequestCtx) {
	if !h.isAdmin(ctx) {
		SendError(ctx, fasthttp.StatusForbidden, "Forbidden")
		return
	}
	id, ok := h.extractParam(ctx, "id")
	if !ok {
		return
	}
	user, err := h.configStore.GetUserByID(ctx, id)
	if err != nil {
		SendError(ctx, fasthttp.StatusNotFound, "User not found")
		return
	}
	now := time.Now()
	user.Status = tables.UserStatusRejected
	user.ReviewedAt = &now
	user.UpdatedAt = now
	if err := h.configStore.UpdateUser(ctx, user); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, "Failed to reject user: "+err.Error())
		return
	}
	emailSent, emailErr := trySendRegistrationDecisionEmail(h.configStore, ctx, user.Username, user.Email, "rejected")
	SendJSON(ctx, map[string]any{
		"message":     "Registration denied",
		"id":          user.ID,
		"status":      user.Status,
		"email_sent":  emailSent,
		"email_error": emailErr,
	})
}
