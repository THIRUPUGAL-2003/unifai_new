package handlers

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"math/big"
	"strings"
	"time"

	"github.com/fasthttp/router"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/configstore/tables"
	"github.com/unifai/unifai/framework/encrypt"
	"github.com/unifai/unifai/framework/mailer"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

const (
	loginMaxFailedAttempts = 3
	loginLockoutDuration   = 20 * time.Minute
	passwordResetOTPTTL    = 15 * time.Minute
)

// SMTPHandler manages SMTP settings used for auth emails.
type SMTPHandler struct {
	store *lib.Config
}

func NewSMTPHandler(store *lib.Config) *SMTPHandler {
	return &SMTPHandler{store: store}
}

func (h *SMTPHandler) RegisterRoutes(r *router.Router, middlewares ...schemas.UnifAIHTTPMiddleware) {
	r.GET("/api/smtp-config", lib.ChainMiddlewares(h.getSMTPConfig, middlewares...))
	r.PUT("/api/smtp-config", lib.ChainMiddlewares(h.updateSMTPConfig, middlewares...))
	r.POST("/api/smtp-config/test", lib.ChainMiddlewares(h.testSMTPConfig, middlewares...))
}

type smtpConfigPayload struct {
	Enabled            bool   `json:"enabled"`
	Host               string `json:"host"`
	Port               int    `json:"port"`
	Username           string `json:"username"`
	Password           string `json:"password"`
	FromEmail          string `json:"from_email"`
	FromName           string `json:"from_name"`
	UseTLS             bool   `json:"use_tls"`
	NotifyOnLogin      bool   `json:"notify_on_login"`
	NotifyOnUserCreate bool   `json:"notify_on_user_create"`
}

func (h *SMTPHandler) requireStore(ctx *fasthttp.RequestCtx) configstore.ConfigStore {
	if h.store == nil || h.store.ConfigStore == nil {
		SendError(ctx, fasthttp.StatusServiceUnavailable, "config store not available")
		return nil
	}
	return h.store.ConfigStore
}

func (h *SMTPHandler) getSMTPConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	row, err := store.GetSMTPConfig(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	if row == nil {
		SendJSON(ctx, smtpConfigPayload{Port: 587, UseTLS: true, NotifyOnUserCreate: true})
		return
	}
	SendJSON(ctx, smtpConfigPayload{
		Enabled:            row.Enabled,
		Host:               row.Host,
		Port:               row.Port,
		Username:           row.Username,
		Password:           "<redacted>",
		FromEmail:          row.FromEmail,
		FromName:           row.FromName,
		UseTLS:             row.UseTLS,
		NotifyOnLogin:      row.NotifyOnLogin,
		NotifyOnUserCreate: row.NotifyOnUserCreate,
	})
}

func (h *SMTPHandler) updateSMTPConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	var payload smtpConfigPayload
	if err := json.Unmarshal(ctx.PostBody(), &payload); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "invalid payload")
		return
	}
	if payload.Enabled {
		if strings.TrimSpace(payload.Host) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "SMTP host is required")
			return
		}
		if strings.TrimSpace(payload.FromEmail) == "" && strings.TrimSpace(payload.Username) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "From email or SMTP username is required")
			return
		}
	}
	if payload.Port <= 0 {
		payload.Port = 587
	}

	existing, err := store.GetSMTPConfig(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	password := payload.Password
	if password == "" || strings.EqualFold(password, "<redacted>") || strings.Contains(password, "*") {
		if existing != nil {
			password = existing.Password
		} else {
			password = ""
		}
	}
	if payload.Enabled && strings.TrimSpace(password) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "SMTP password is required when SMTP is enabled")
		return
	}

	row := &tables.TableSMTPConfig{
		Enabled:            payload.Enabled,
		Host:               strings.TrimSpace(payload.Host),
		Port:               payload.Port,
		Username:           strings.TrimSpace(payload.Username),
		Password:           password,
		FromEmail:          strings.TrimSpace(payload.FromEmail),
		FromName:           strings.TrimSpace(payload.FromName),
		UseTLS:             payload.UseTLS,
		NotifyOnLogin:      payload.NotifyOnLogin,
		NotifyOnUserCreate: payload.NotifyOnUserCreate,
		EncryptionStatus:   tables.EncryptionStatusPlainText,
	}
	if err := store.UpdateSMTPConfig(ctx, row); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{"status": "ok"})
}

func (h *SMTPHandler) testSMTPConfig(ctx *fasthttp.RequestCtx) {
	store := h.requireStore(ctx)
	if store == nil {
		return
	}
	var payload struct {
		To string `json:"to"`
	}
	_ = json.Unmarshal(ctx.PostBody(), &payload)
	row, err := store.GetSMTPConfig(ctx)
	if err != nil || row == nil || !row.Enabled {
		SendError(ctx, fasthttp.StatusBadRequest, "enable and save SMTP settings first")
		return
	}
	to := strings.TrimSpace(payload.To)
	if to == "" {
		to = row.FromEmail
	}
	if to == "" {
		to = row.Username
	}
	if err := mailer.Send(smtpToMailer(row), mailer.Message{
		To:      to,
		Subject: "UnifAI SMTP test",
		Body:    "This is a test email from UnifAI Security → SMTP settings.",
	}); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, fmt.Sprintf("SMTP test failed: %v", err))
		return
	}
	SendJSON(ctx, map[string]any{"status": "ok", "to": to})
}

func smtpToMailer(row *tables.TableSMTPConfig) mailer.Config {
	if row == nil {
		return mailer.Config{}
	}
	return mailer.Config{
		Enabled:   row.Enabled,
		Host:      row.Host,
		Port:      row.Port,
		Username:  row.Username,
		Password:  row.Password,
		FromEmail: row.FromEmail,
		FromName:  row.FromName,
		UseTLS:    row.UseTLS,
	}
}

func sendAuthEmail(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, to, subject, body string) error {
	if store == nil || strings.TrimSpace(to) == "" {
		return fmt.Errorf("no recipient")
	}
	row, err := store.GetSMTPConfig(ctx)
	if err != nil {
		return err
	}
	if row == nil || !row.Enabled {
		return fmt.Errorf("SMTP is not configured")
	}
	return mailer.Send(smtpToMailer(row), mailer.Message{To: to, Subject: subject, Body: body})
}

func welcomeAccountEmailBody(username, email, password string) string {
	return fmt.Sprintf(
		"Hello %s,\n\nYour UnifAI account was created.\n\nEmail: %s\nUsername: %s\nTemporary password: %s\n\nSign in with this username and password. Use Forgot password on the login page if you need an OTP reset.\n",
		username, email, username, password,
	)
}

// trySendWelcomeEmail sends create-user mail when SMTP notify-on-create is on.
// Returns (sent, errorMessage). Missing email / disabled SMTP is not an error.
func trySendWelcomeEmail(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username, email, password string) (bool, string) {
	email = strings.TrimSpace(email)
	if email == "" || store == nil {
		return false, ""
	}
	smtpRow, err := store.GetSMTPConfig(ctx)
	if err != nil {
		return false, err.Error()
	}
	if smtpRow == nil || !smtpRow.Enabled || !smtpRow.NotifyOnUserCreate {
		return false, ""
	}
	if err := sendAuthEmail(store, ctx, email, "Your UnifAI account", welcomeAccountEmailBody(username, email, password)); err != nil {
		return false, err.Error()
	}
	return true, ""
}

func accountApprovedEmailBody(username string) string {
	return fmt.Sprintf(
		"Hello %s,\n\nYour UnifAI registration was approved by an administrator.\n\nYou can sign in now with the username and password you registered with.\n\nIf you forgot your password, use Forgot password on the login page.\n",
		username,
	)
}

func accountRejectedEmailBody(username string) string {
	return fmt.Sprintf(
		"Hello %s,\n\nYour UnifAI registration was reviewed and was not approved.\n\nYou will not be able to sign in with this account. Contact your administrator if you believe this is a mistake.\n",
		username,
	)
}

// trySendRegistrationDecisionEmail notifies the user after admin accept/reject.
// Sends when SMTP is enabled and the user has an email address.
func trySendRegistrationDecisionEmail(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username, email, decision string) (bool, string) {
	email = strings.TrimSpace(email)
	if email == "" || store == nil {
		return false, ""
	}
	smtpRow, err := store.GetSMTPConfig(ctx)
	if err != nil {
		return false, err.Error()
	}
	if smtpRow == nil || !smtpRow.Enabled {
		return false, ""
	}
	var subject, body string
	switch strings.ToLower(strings.TrimSpace(decision)) {
	case "approved", "approve", "accepted", "accept":
		subject = "UnifAI account approved"
		body = accountApprovedEmailBody(username)
	case "rejected", "reject", "denied", "deny":
		subject = "UnifAI registration not approved"
		body = accountRejectedEmailBody(username)
	default:
		return false, "unknown registration decision"
	}
	if err := sendAuthEmail(store, ctx, email, subject, body); err != nil {
		return false, err.Error()
	}
	return true, ""
}

func loginUsernameKey(username string) string {
	return strings.ToLower(strings.TrimSpace(username))
}

func checkLoginLockout(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username string) (locked bool, retryAfter time.Duration, err error) {
	row, err := store.GetLoginLockout(ctx, loginUsernameKey(username))
	if err != nil || row == nil || row.LockedUntil == nil {
		return false, 0, err
	}
	if time.Now().Before(*row.LockedUntil) {
		return true, time.Until(*row.LockedUntil), nil
	}
	return false, 0, nil
}

func recordLoginFailure(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username string) (locked bool, retryAfter time.Duration) {
	key := loginUsernameKey(username)
	now := time.Now()
	row, _ := store.GetLoginLockout(ctx, key)
	if row == nil {
		row = &tables.TableLoginLockout{UsernameKey: key}
	}
	if row.LockedUntil != nil && now.Before(*row.LockedUntil) {
		return true, time.Until(*row.LockedUntil)
	}
	// Fresh window after lockout expired.
	if row.LockedUntil != nil && now.After(*row.LockedUntil) {
		row.FailedCount = 0
		row.LockedUntil = nil
	}
	row.FailedCount++
	row.LastFailedAt = &now
	if row.FailedCount >= loginMaxFailedAttempts {
		until := now.Add(loginLockoutDuration)
		row.LockedUntil = &until
		row.FailedCount = 0
		_ = store.UpsertLoginLockout(ctx, row)
		return true, loginLockoutDuration
	}
	_ = store.UpsertLoginLockout(ctx, row)
	return false, 0
}

func clearLoginFailures(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username string) {
	_ = store.ClearLoginLockout(ctx, loginUsernameKey(username))
}

func clientIPAddress(ctx *fasthttp.RequestCtx) string {
	if xff := string(ctx.Request.Header.Peek("X-Forwarded-For")); xff != "" {
		parts := strings.Split(xff, ",")
		if ip := strings.TrimSpace(parts[0]); ip != "" {
			return ip
		}
	}
	if xri := strings.TrimSpace(string(ctx.Request.Header.Peek("X-Real-IP"))); xri != "" {
		return xri
	}
	return ctx.RemoteIP().String()
}

func loginDeviceFingerprint(ctx *fasthttp.RequestCtx) (fingerprint, ip, ua string) {
	ip = clientIPAddress(ctx)
	ua = string(ctx.Request.Header.Peek("User-Agent"))
	fingerprint = encrypt.HashSHA256(ip + "|" + ua)
	return fingerprint, ip, ua
}

// trySendLoginNoticeEmail sends only on first login or a new device when NotifyOnLogin is on.
func trySendLoginNoticeEmail(store configstore.ConfigStore, ctx *fasthttp.RequestCtx, username, email string) {
	email = strings.TrimSpace(email)
	if store == nil || email == "" || username == "" {
		return
	}
	smtpRow, err := store.GetSMTPConfig(ctx)
	if err != nil || smtpRow == nil || !smtpRow.Enabled || !smtpRow.NotifyOnLogin {
		return
	}
	fp, ip, ua := loginDeviceFingerprint(ctx)
	key := loginUsernameKey(username)
	known, err := store.HasLoginDevice(ctx, key, fp)
	if err != nil {
		known = false
	}
	_ = store.UpsertLoginDevice(ctx, &tables.TableLoginDevice{
		UsernameKey: key,
		Fingerprint: fp,
		UserAgent:   truncateASCII(ua, 500),
		IPAddress:   truncateASCII(ip, 64),
	})
	if known {
		return // same device — no email
	}
	body := fmt.Sprintf(
		"Hello %s,\n\nYour UnifAI account signed in from a new device or for the first time.\n\nIP: %s\nBrowser: %s\n\nIf this was not you, reset your password immediately.\n",
		username, ip, truncateASCII(ua, 200),
	)
	_ = sendAuthEmail(store, ctx, email, "UnifAI login notice", body)
}

func truncateASCII(s string, max int) string {
	if max <= 0 || len(s) <= max {
		return s
	}
	return s[:max]
}

func generateOTP6() (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(1000000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()), nil
}
