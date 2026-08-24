package logstore

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

var pacHostSafe = regexp.MustCompile(`^[a-z0-9.-]+$`)
var pacProxyAddrSafe = regexp.MustCompile(`^[A-Za-z0-9.:\[\]-]+$`)
var nicGUID = regexp.MustCompile(`(?i)\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}`)
var secretTokenPrefix = regexp.MustCompile(`(?i)^(sk-|sk-ant-|sk-proj-|sk-admin-|ghp_|gho_|github_pat_|akia|aizasy|pcsk_)`)

func looksLikeSecretToken(s string) bool {
	return secretTokenPrefix.MatchString(strings.TrimSpace(s))
}

func isPhoneLikeRule(name, pattern string) bool {
	n := strings.ToLower(name)
	p := strings.ToLower(pattern)
	if strings.Contains(n, "phone") || strings.Contains(n, "mobile") || strings.Contains(n, "cell") {
		return true
	}
	return strings.Contains(p, `\d{8`) || strings.Contains(p, `\d{9`) || strings.Contains(p, `\d{10`) ||
		strings.Contains(p, `\d{11`) || strings.Contains(p, `[0-9]{10`)
}

type BrowserAILog struct {
	ID                string    `gorm:"primaryKey" json:"id"`
	Timestamp         time.Time `gorm:"index" json:"timestamp"`
	Platform          string    `gorm:"index" json:"platform"`
	UserPromptPreview string    `json:"user_prompt_preview"`
	UserPromptFull    string    `gorm:"type:text" json:"user_prompt_full"`
	EstTokens         int       `json:"est_tokens"`
	ClientIP          string    `json:"client_ip"`
	AgentID           string    `gorm:"index" json:"agent_id"`
	AgentHostname     string    `json:"agent_hostname"`
	Status            string    `gorm:"index" json:"status"`
	Action            string    `json:"action"`
	RuleTriggered     string    `json:"rule_triggered"`
	RiskScore         int       `json:"risk_score"`
	PredictiveRisk    string    `json:"predictive_risk"`    // "LOW", "MEDIUM", "HIGH", "CRITICAL"
	PredictedCategory string    `json:"predicted_category"` // "SAFE", "SECRET_LEAK_REDACTED", "SECURITY_POLICY_VIOLATION", "PREDICTED_SECRET_EXPOSURE"
	ReplyBotProvider  string    `json:"reply_bot_provider"`
	ReplyBotModel     string    `json:"reply_bot_model"`
	ReplyBotText      string    `gorm:"type:text" json:"reply_bot_text"`
	// Attachment* — intercepted file upload (PDF stored under APP_DIR/pdf for now).
	AttachmentName        string `json:"attachment_name,omitempty"`
	AttachmentStoredName  string `json:"attachment_stored_name,omitempty"` // basename only under pdf/
	AttachmentContentType string `json:"attachment_content_type,omitempty"`
	Metadata              string    `gorm:"type:text" json:"metadata"`
	CreatedAt             time.Time `json:"created_at"`
}

// BrowserAIAgent tracks every installed Guard EXE (unlimited scale in unifai_new).
type BrowserAIAgent struct {
	ID            string     `gorm:"primaryKey" json:"id"`
	Hostname      string     `gorm:"index" json:"hostname"`
	Username      string     `json:"username"`
	IPAddress     string     `json:"ip_address"`
	MacAddress    string     `json:"mac_address"`
	TransportName string     `json:"transport_name"`
	OSVersion     string     `json:"os_version"`
	AgentVersion  string     `json:"agent_version"`
	Status             string     `gorm:"index" json:"status"` // active | uninstall_pending | uninstalled
	UninstallRequested bool       `json:"uninstall_requested"`
	LastSeenAt         time.Time  `gorm:"index" json:"last_seen_at"`
	InstalledAt        time.Time  `json:"installed_at"`
	UninstalledAt      *time.Time `json:"uninstalled_at,omitempty"`
	CreatedAt     time.Time  `json:"created_at"`
	UpdatedAt     time.Time  `json:"updated_at"`
}

// BrowserAIAgentSettings stores company uninstall-key policy (single row).
type BrowserAIAgentSettings struct {
	ID                  string    `gorm:"primaryKey" json:"id"`
	UninstallKeyHash    string    `json:"-"`
	RequireUninstallKey bool      `json:"require_uninstall_key"`
	KeyConfigured       bool      `gorm:"-" json:"key_configured"`
	UpdatedAt           time.Time `json:"updated_at"`
	UpdatedBy           string    `json:"updated_by"`
}

const BrowserAIAgentSettingsID = "browser-agent-settings-default"
const AgentStatusActive = "active"
const AgentStatusInactive = "inactive"
const AgentStatusSleep = "sleep"
const AgentStatusShutdown = "shutdown"
const AgentStatusUninstalled = "uninstalled"
const AgentStatusUninstallPending = "uninstall_pending"

type BrowserGuardRule struct {
	ID             string    `gorm:"primaryKey" json:"id"`
	Name           string    `json:"name"`
	RuleType       string    `json:"rule_type"`                   // "regex" (default) or "ai_bot"
	BotProvider    string    `json:"bot_provider"`                // e.g. "openai", "anthropic", "gemini"
	BotModel       string    `json:"bot_model"`                   // e.g. "gpt-4o-mini", "claude-3-5-haiku"
	BotPrompt      string    `gorm:"type:text" json:"bot_prompt"` // Custom evaluation instruction for the LLM
	Severity       string    `json:"severity"`                    // "CRITICAL", "HIGH", "MEDIUM"
	Action         string    `json:"action"`                      // "BLOCK" or "WARN" (legacy "REDACT" is normalized to "WARN")
	Pattern        string    `json:"pattern"`
	Active         bool      `json:"active"`
	Description    string    `json:"description"`
	WarningMessage string    `json:"warning_message"` // shown in-chat when this rule blocks
	CreatedAt      time.Time `json:"created_at"`
}

// BrowserControlSettings is a single-row policy for browser AI interaction controls.
type BrowserControlSettings struct {
	ID            string    `gorm:"primaryKey" json:"id"`
	Enabled       bool      `json:"enabled"`                         // master switch for upload control
	BlockUpload   bool      `json:"block_upload"`                    // block file uploads to AI sites
	UploadWarning string    `gorm:"type:text" json:"upload_warning"` // shown when this upload policy blocks; empty = no message
	UpdatedAt     time.Time `json:"updated_at"`
}

type BrowserTargetWebsite struct {
	ID           string `gorm:"primaryKey" json:"id"`
	Domain       string `gorm:"uniqueIndex" json:"domain"`
	PlatformName string `json:"platform_name"`
	Monitored    bool   `json:"monitored"`
	// BlockSite: when true, Guard blocks opening the whole website (not only prompts).
	BlockSite        bool   `json:"block_site"`
	InterceptedCount int64  `json:"intercepted_count"`
	Status           string `json:"status"` // "MONITORED", "PAUSED", "BLOCKED"
	ReplyBotEnabled  bool   `json:"reply_bot_enabled"`
	ReplyBotProvider string `json:"reply_bot_provider"`
	ReplyBotModel    string `json:"reply_bot_model"`
	// ReplyBotMode: "violations" (default) = reply only on Guard BLOCK;
	// "all" = answer every intercepted prompt via Reply Bot (never forward to the site AI).
	ReplyBotMode string `json:"reply_bot_mode"`
	// ParentID: related host nested under another Target Website. Empty = top-level domain.
	ParentID  string    `gorm:"index" json:"parent_id"`
	CreatedAt time.Time `json:"created_at"`
}

func (BrowserAILog) TableName() string {
	return "browser_ai_logs"
}

func (BrowserGuardRule) TableName() string {
	return "browser_guard_rules"
}

func (BrowserControlSettings) TableName() string {
	return "browser_control_settings"
}

func (BrowserTargetWebsite) TableName() string {
	return "browser_target_websites"
}

func (BrowserAIAgent) TableName() string {
	return "browser_ai_agents"
}

func (BrowserAIAgentSettings) TableName() string {
	return "browser_ai_agent_settings"
}

const BrowserControlSettingsID = "browser-controls-default"

// NormalizeDomain cleans values like "https://gemini.google.com/" -> "gemini.google.com".
func NormalizeDomain(raw string) string {
	domain := strings.TrimSpace(strings.ToLower(raw))
	if domain == "" {
		return ""
	}
	if i := strings.Index(domain, "://"); i >= 0 {
		domain = domain[i+3:]
	}
	domain = strings.Split(domain, "/")[0]
	domain = strings.Split(domain, "?")[0]
	domain = strings.Split(domain, "#")[0]
	if strings.HasPrefix(domain, "[") {
		if end := strings.Index(domain, "]"); end > 0 {
			domain = domain[1:end]
		}
	} else if i := strings.LastIndex(domain, ":"); i > 0 {
		// strip port, but keep IPv6 handled above
		maybePort := domain[i+1:]
		if maybePort != "" && strings.Trim(maybePort, "0123456789") == "" {
			domain = domain[:i]
		}
	}
	domain = strings.TrimPrefix(domain, "www.")
	return strings.TrimSpace(domain)
}

type BrowserAIManager struct {
	db       *gorm.DB
	migrated bool
	mu       sync.RWMutex
}

func NewBrowserAIManager(db *gorm.DB) *BrowserAIManager {
	m := &BrowserAIManager{db: db}
	if db != nil {
		_ = m.AutoMigrate(context.Background())
	}
	return m
}

func (m *BrowserAIManager) SetDB(db *gorm.DB) {
	m.mu.Lock()
	m.db = db
	needsMigrate := !m.migrated && db != nil
	m.mu.Unlock()

	if needsMigrate {
		_ = m.AutoMigrate(context.Background())
	}
}

func (m *BrowserAIManager) GetDB() *gorm.DB {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.db
}

func (m *BrowserAIManager) AutoMigrate(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil
	}

	err := m.db.WithContext(ctx).AutoMigrate(
		&BrowserAILog{},
		&BrowserGuardRule{},
		&BrowserControlSettings{},
		&BrowserTargetWebsite{},
		&BrowserAIAgent{},
		&BrowserAIAgentSettings{},
	)
	if err != nil {
		return err
	}

	// Seed default browser control settings if missing
	var ctrl BrowserControlSettings
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserControlSettingsID).First(&ctrl).Error; err != nil {
		_ = m.db.WithContext(ctx).Create(&BrowserControlSettings{
			ID:          BrowserControlSettingsID,
			Enabled:     true,
			BlockUpload: false,
			UpdatedAt:   time.Now(),
		}).Error
	}

	var agentSettings BrowserAIAgentSettings
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserAIAgentSettingsID).First(&agentSettings).Error; err != nil {
		_ = m.db.WithContext(ctx).Create(&BrowserAIAgentSettings{
			ID:                  BrowserAIAgentSettingsID,
			RequireUninstallKey: true,
			UpdatedAt:           time.Now(),
		}).Error
	}

	// Do NOT seed default guard rules.
	// Proxy applies only rules the admin adds in Guard Rules.

	// Do NOT seed default target websites.
	// Proxy only monitors domains the admin adds in Target Websites.

	m.migrated = true
	return nil
}

func (m *BrowserAIManager) GetLogs(ctx context.Context, platform, status, action, search string, limit, offset int) ([]BrowserAILog, int64, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var logs []BrowserAILog
	var total int64

	if m.db == nil {
		return logs, 0, nil
	}

	query := m.db.WithContext(ctx).Model(&BrowserAILog{})

	if platform != "" && strings.ToLower(platform) != "all" {
		query = query.Where("LOWER(platform) = ?", strings.ToLower(platform))
	}
	if status != "" && strings.ToLower(status) != "all" {
		if strings.ToLower(status) == "blocked" {
			query = query.Where("LOWER(action) = ?", "blocked")
		} else if strings.ToLower(status) == "allowed" {
			query = query.Where("LOWER(action) = ?", "allowed")
		} else {
			query = query.Where("LOWER(status) LIKE ?", "%"+strings.ToLower(status)+"%")
		}
	}
	if action != "" && strings.ToLower(action) != "all" {
		switch strings.ToLower(strings.TrimSpace(action)) {
		case "siteblocked", "site_blocked", "site blocked":
			// Full-site lock logs (Target Websites → Block entire website), not DLP prompt blocks.
			query = query.Where(
				"LOWER(user_prompt_full) LIKE ? OR LOWER(user_prompt_preview) LIKE ? OR LOWER(rule_triggered) = ? OR LOWER(predicted_category) = ?",
				"%[site blocked]%",
				"%[site blocked]%",
				"block entire website",
				"site_block",
			)
		default:
			query = query.Where("LOWER(action) = ?", strings.ToLower(action))
		}
	}
	if search != "" {
		s := "%" + strings.ToLower(search) + "%"
		query = query.Where("LOWER(user_prompt_full) LIKE ? OR LOWER(platform) LIKE ? OR LOWER(client_ip) LIKE ? OR LOWER(rule_triggered) LIKE ? OR LOWER(agent_id) LIKE ? OR LOWER(agent_hostname) LIKE ?", s, s, s, s, s, s)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if limit <= 0 {
		limit = 50
	}

	err := query.Order("timestamp DESC").Limit(limit).Offset(offset).Find(&logs).Error
	return logs, total, err
}

func (m *BrowserAIManager) ClearLogs(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil
	}
	return m.db.WithContext(ctx).Exec("DELETE FROM browser_ai_logs").Error
}

func (m *BrowserAIManager) GetRules(ctx context.Context) ([]BrowserGuardRule, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var rules []BrowserGuardRule
	if m.db == nil {
		return rules, nil
	}
	err := m.db.WithContext(ctx).Order("created_at ASC").Find(&rules).Error
	if err != nil {
		return rules, err
	}
	// Legacy REDACT → WARN (persist so UI no longer shows REDACT).
	for i := range rules {
		if strings.EqualFold(strings.TrimSpace(rules[i].Action), "REDACT") {
			_ = m.db.WithContext(ctx).Model(&BrowserGuardRule{}).Where("id = ?", rules[i].ID).Update("action", "WARN").Error
			rules[i].Action = "WARN"
		}
	}
	return rules, nil
}

func (m *BrowserAIManager) CreateRule(ctx context.Context, rule *BrowserGuardRule) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	if rule.ID == "" {
		rule.ID = "rule-" + uuid.New().String()[:8]
	}
	rule.Name = strings.TrimSpace(rule.Name)
	if rule.RuleType == "" {
		rule.RuleType = "regex"
	}
	rule.RuleType = strings.TrimSpace(rule.RuleType)
	rule.BotProvider = strings.TrimSpace(rule.BotProvider)
	rule.BotModel = strings.TrimSpace(rule.BotModel)
	rule.BotPrompt = strings.TrimSpace(rule.BotPrompt)
	rule.Pattern = strings.TrimSpace(rule.Pattern)
	rule.Description = strings.TrimSpace(rule.Description)
	rule.WarningMessage = strings.TrimSpace(rule.WarningMessage)
	rule.Action = NormalizeGuardRuleAction(rule.Action)
	rule.CreatedAt = time.Now()
	return m.db.WithContext(ctx).Create(rule).Error
}

func (m *BrowserAIManager) UpdateRule(ctx context.Context, id string, updates map[string]any) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	allowed := map[string]bool{
		"name": true, "severity": true, "action": true, "pattern": true,
		"active": true, "description": true, "warning_message": true,
		"rule_type": true, "bot_provider": true, "bot_model": true, "bot_prompt": true,
	}
	filtered := make(map[string]any, len(updates))
	for k, v := range updates {
		if !allowed[k] {
			continue
		}
		if s, ok := v.(string); ok && (k == "name" || k == "pattern" || k == "description" || k == "warning_message" || k == "severity" || k == "action" || k == "rule_type" || k == "bot_provider" || k == "bot_model" || k == "bot_prompt") {
			if k == "action" {
				filtered[k] = NormalizeGuardRuleAction(s)
			} else {
				filtered[k] = strings.TrimSpace(s)
			}
			continue
		}
		filtered[k] = v
	}
	if len(filtered) == 0 {
		return nil
	}
	return m.db.WithContext(ctx).Model(&BrowserGuardRule{}).Where("id = ?", id).Updates(filtered).Error
}

func (m *BrowserAIManager) UpdateLogRuleViolation(ctx context.Context, id, action, status, ruleTriggered string, riskScore int, predictiveRisk, predictedCategory string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil
	}
	return m.db.WithContext(ctx).Model(&BrowserAILog{}).Where("id = ?", id).Updates(map[string]any{
		"action":             action,
		"status":             status,
		"rule_triggered":     ruleTriggered,
		"risk_score":         riskScore,
		"predictive_risk":    predictiveRisk,
		"predicted_category": predictedCategory,
	}).Error
}

func (m *BrowserAIManager) DeleteRule(ctx context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	return m.db.WithContext(ctx).Where("id = ?", id).Delete(&BrowserGuardRule{}).Error
}

func (m *BrowserAIManager) GetControls(ctx context.Context) (*BrowserControlSettings, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return &BrowserControlSettings{
			ID:          BrowserControlSettingsID,
			Enabled:     true,
			BlockUpload: false,
			UpdatedAt:   time.Now(),
		}, nil
	}
	var ctrl BrowserControlSettings
	err := m.db.WithContext(ctx).Where("id = ?", BrowserControlSettingsID).First(&ctrl).Error
	if err != nil {
		ctrl = BrowserControlSettings{
			ID:          BrowserControlSettingsID,
			Enabled:     true,
			BlockUpload: false,
			UpdatedAt:   time.Now(),
		}
		if createErr := m.db.WithContext(ctx).Create(&ctrl).Error; createErr != nil {
			return &ctrl, createErr
		}
	}
	return &ctrl, nil
}

func (m *BrowserAIManager) UpdateControls(ctx context.Context, updates map[string]any) (*BrowserControlSettings, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}

	var ctrl BrowserControlSettings
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserControlSettingsID).First(&ctrl).Error; err != nil {
		ctrl = BrowserControlSettings{
			ID:          BrowserControlSettingsID,
			Enabled:     true,
			BlockUpload: false,
			UpdatedAt:   time.Now(),
		}
		if createErr := m.db.WithContext(ctx).Create(&ctrl).Error; createErr != nil {
			return nil, createErr
		}
	}

	allowed := map[string]bool{
		"enabled":        true,
		"block_upload":   true,
		"upload_warning": true,
	}
	filtered := map[string]any{}
	for k, v := range updates {
		if !allowed[k] {
			continue
		}
		if k == "upload_warning" {
			if s, ok := v.(string); ok {
				filtered[k] = strings.TrimSpace(s)
				continue
			}
		}
		filtered[k] = v
	}
	filtered["updated_at"] = time.Now()

	if err := m.db.WithContext(ctx).Model(&BrowserControlSettings{}).Where("id = ?", BrowserControlSettingsID).Updates(filtered).Error; err != nil {
		return nil, err
	}
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserControlSettingsID).First(&ctrl).Error; err != nil {
		return nil, err
	}
	return &ctrl, nil
}

func (m *BrowserAIManager) GetTargets(ctx context.Context) ([]BrowserTargetWebsite, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var targets []BrowserTargetWebsite
	if m.db == nil {
		return targets, nil
	}
	err := m.db.WithContext(ctx).Order("domain ASC").Find(&targets).Error
	return targets, err
}

func sanitizeProxyAddr(raw string) string {
	s := strings.TrimSpace(raw)
	if s == "" || len(s) > 80 || !pacProxyAddrSafe.MatchString(s) {
		return "127.0.0.1:8085"
	}
	return s
}

func emptyPAC(proxyAddr string) string {
	_ = proxyAddr
	return `// UnifAI Browser AI Guard — no Target Websites yet.
function FindProxyForURL(url, host) {
    return "DIRECT";
}
`
}

// BuildProxyPAC builds a PAC script from Target Websites that are monitored
// and/or fully blocked (block_site). Empty list means all traffic is DIRECT.
// Never returns an error — a valid PAC is always produced so employee browsers
// are not left without a proxy config (a 500 here used to break Guard).
func (m *BrowserAIManager) BuildProxyPAC(ctx context.Context, proxyAddr string) (string, error) {
	proxyAddr = sanitizeProxyAddr(proxyAddr)
	var targets []BrowserTargetWebsite
	if m != nil && m.db != nil {
		dbCtx := ctx
		if dbCtx == nil {
			dbCtx = context.Background()
		}
		if err := m.db.WithContext(dbCtx).Order("domain ASC").Find(&targets).Error; err != nil {
			return emptyPAC(proxyAddr), nil
		}
	}

	seen := map[string]bool{}
	var hosts []string
	for _, t := range targets {
		// Must route through local Guard proxy to monitor prompts OR lock the whole site.
		if !t.Monitored && !t.BlockSite {
			continue
		}
		d := NormalizeDomain(t.Domain)
		if d == "" || seen[d] {
			continue
		}
		if !pacHostSafe.MatchString(d) {
			continue
		}
		seen[d] = true
		hosts = append(hosts, d)
	}
	sort.Strings(hosts)

	var b strings.Builder
	b.WriteString("// UnifAI Browser AI Guard — generated from Target Websites (monitored or block_site).\n")
	b.WriteString("// Only domains the admin added. Subdomains of those hosts are included.\n")
	b.WriteString("// Empty list => all traffic goes DIRECT (not through the proxy).\n")
	b.WriteString("function FindProxyForURL(url, host) {\n")
	b.WriteString("    host = host.toLowerCase();\n\n")
	b.WriteString("    var aiHosts = [\n")
	for _, d := range hosts {
		b.WriteString("        \"")
		b.WriteString(d)
		b.WriteString("\",\n")
	}
	b.WriteString("    ];\n\n")
	b.WriteString("    for (var i = 0; i < aiHosts.length; i++) {\n")
	b.WriteString("        var d = aiHosts[i];\n")
	b.WriteString("        if (host === d || dnsDomainIs(host, \".\" + d) || shExpMatch(host, \"*.\" + d)) {\n")
	b.WriteString("            return \"PROXY ")
	b.WriteString(proxyAddr)
	b.WriteString("\";\n")
	b.WriteString("        }\n")
	b.WriteString("    }\n\n")
	b.WriteString("    return \"DIRECT\";\n")
	b.WriteString("}\n")
	return b.String(), nil
}

// GetTargetByDomain finds a monitored target matching host or parent domain.
func (m *BrowserAIManager) GetTargetByDomain(ctx context.Context, host string) (*BrowserTargetWebsite, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.db == nil {
		return nil, nil
	}
	host = NormalizeDomain(host)
	if host == "" {
		return nil, nil
	}
	var targets []BrowserTargetWebsite
	if err := m.db.WithContext(ctx).Find(&targets).Error; err != nil {
		return nil, err
	}
	for i := range targets {
		d := strings.ToLower(strings.TrimSpace(targets[i].Domain))
		if d == "" {
			continue
		}
		if host == d || strings.HasSuffix(host, "."+d) {
			t := targets[i]
			return &t, nil
		}
	}
	return nil, nil
}

func (m *BrowserAIManager) CreateTarget(ctx context.Context, target *BrowserTargetWebsite) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	target.Domain = NormalizeDomain(target.Domain)
	if target.Domain == "" {
		return fmt.Errorf("invalid target domain")
	}
	if strings.TrimSpace(target.PlatformName) == "" {
		target.PlatformName = target.Domain
	}
	if target.ID == "" {
		target.ID = "tgt-" + uuid.New().String()[:8]
	}
	parentMonitored := true
	parentBlockSite := false
	target.ParentID = strings.TrimSpace(target.ParentID)
	if target.ParentID != "" {
		if target.ParentID == target.ID {
			target.ParentID = ""
		} else {
			var parent BrowserTargetWebsite
			if err := m.db.WithContext(ctx).Where("id = ?", target.ParentID).First(&parent).Error; err != nil {
				target.ParentID = ""
			} else if strings.TrimSpace(parent.ParentID) != "" {
				target.ParentID = parent.ParentID
				parentMonitored = parent.Monitored
				parentBlockSite = parent.BlockSite
			} else {
				target.ParentID = parent.ID
				parentMonitored = parent.Monitored
				parentBlockSite = parent.BlockSite
			}
		}
	}
	if target.ParentID != "" {
		target.Monitored = parentMonitored
		if parentBlockSite {
			target.BlockSite = true
		}
	} else {
		target.Monitored = true
	}
	if target.BlockSite {
		target.Status = "BLOCKED"
	} else if !target.Monitored {
		target.Status = "PAUSED"
	} else {
		target.Status = "MONITORED"
	}
	target.CreatedAt = time.Now()
	return m.db.WithContext(ctx).Create(target).Error
}

func (m *BrowserAIManager) UpdateTarget(ctx context.Context, id string, updates map[string]any) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	if raw, ok := updates["domain"]; ok {
		if s, ok := raw.(string); ok {
			updates["domain"] = NormalizeDomain(s)
		}
	}
	allowed := map[string]bool{
		"domain":             true,
		"platform_name":      true,
		"monitored":          true,
		"block_site":         true,
		"status":             true,
		"reply_bot_enabled":  true,
		"reply_bot_provider": true,
		"reply_bot_model":    true,
		"reply_bot_mode":     true,
		"parent_id":          true,
	}
	filtered := map[string]any{}
	for k, v := range updates {
		if allowed[k] {
			filtered[k] = v
		}
	}
	if len(filtered) == 0 {
		return nil
	}
	if rawParent, ok := filtered["parent_id"].(string); ok {
		pid := strings.TrimSpace(rawParent)
		if pid == "" || pid == id {
			delete(filtered, "parent_id")
		} else {
			var parent BrowserTargetWebsite
			if err := m.db.WithContext(ctx).Where("id = ?", pid).First(&parent).Error; err != nil {
				delete(filtered, "parent_id")
			} else if strings.TrimSpace(parent.ParentID) != "" {
				filtered["parent_id"] = parent.ParentID
			} else {
				filtered["parent_id"] = parent.ID
			}
		}
		if len(filtered) == 0 {
			return nil
		}
	}
	// Keep status aligned with block_site when that flag is updated alone.
	if bs, ok := filtered["block_site"].(bool); ok {
		if _, hasStatus := filtered["status"]; !hasStatus {
			if bs {
				filtered["status"] = "BLOCKED"
			} else if mon, ok := filtered["monitored"].(bool); ok && !mon {
				filtered["status"] = "PAUSED"
			} else {
				filtered["status"] = "MONITORED"
			}
		}
	}
	if err := m.db.WithContext(ctx).Model(&BrowserTargetWebsite{}).Where("id = ?", id).Updates(filtered).Error; err != nil {
		return err
	}
	child := map[string]any{}
	if mon, ok := filtered["monitored"].(bool); ok {
		child["monitored"] = mon
		if st, ok := filtered["status"].(string); ok && st != "" {
			child["status"] = st
		} else if mon {
			child["status"] = "MONITORED"
		} else {
			child["status"] = "PAUSED"
		}
	}
	if bs, ok := filtered["block_site"].(bool); ok {
		child["block_site"] = bs
		if _, hasStatus := child["status"]; !hasStatus {
			if bs {
				child["status"] = "BLOCKED"
			}
		}
	}
	if len(child) > 0 {
		_ = m.db.WithContext(ctx).Model(&BrowserTargetWebsite{}).Where("parent_id = ?", id).Updates(child).Error
	}
	return nil
}

func (m *BrowserAIManager) DeleteTarget(ctx context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return fmt.Errorf("database not initialized")
	}
	return m.db.WithContext(ctx).Where("id = ? OR parent_id = ?", id, id).Delete(&BrowserTargetWebsite{}).Error
}

func (m *BrowserAIManager) InterceptPrompt(ctx context.Context, platform, promptFull, clientIP string, metadata map[string]any) (*BrowserAILog, string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.db == nil {
		return nil, "", fmt.Errorf("database connection not available")
	}

	words := strings.Fields(promptFull)
	estTokens := int(float64(len(words)) * 1.3)
	if estTokens == 0 && len(promptFull) > 0 {
		estTokens = 1
	}

	preview := promptFull
	if len(preview) > 100 {
		preview = preview[:97] + "..."
	}

	var rules []BrowserGuardRule
	_ = m.db.WithContext(ctx).Where("active = ?", true).Find(&rules).Error

	action := "Allowed"
	status := "Allowed"
	ruleTriggered := ""
	matchedWarning := ""
	riskScore := 10
	predictiveRisk := "LOW"
	predictedCategory := "SAFE"

	if isBlocked, ok := metadata["is_blocked"].(bool); ok && isBlocked {
		action = "Blocked"
		if blockedReason, ok := metadata["blocked_reason"].(string); ok && blockedReason != "" {
			status = fmt.Sprintf("Blocked (%s)", blockedReason)
			ruleTriggered = blockedReason
			if strings.EqualFold(strings.TrimSpace(blockedReason), "Block Entire Website") {
				predictedCategory = "SITE_BLOCK"
			}
		} else if statusStr, ok := metadata["status"].(string); ok && statusStr != "" {
			status = statusStr
		} else {
			status = "Blocked (Security Violation)"
		}
		riskScore = 95
		predictiveRisk = "CRITICAL"
		if predictedCategory == "SAFE" {
			predictedCategory = "SECURITY_POLICY_VIOLATION"
		}
	}

	if estTokens > 500 {
		riskScore += 15
	}

	sort.SliceStable(rules, func(i, j int) bool {
		pi := isPhoneLikeRule(rules[i].Name, rules[i].Pattern)
		pj := isPhoneLikeRule(rules[j].Name, rules[j].Pattern)
		return pi != pj && !pi && pj
	})

	for _, rule := range rules {
		if strings.ToLower(rule.RuleType) == "ai_bot" || rule.Pattern == "" {
			continue
		}
		re, err := regexp.Compile("(?i)" + rule.Pattern)
		if err != nil || !re.MatchString(promptFull) {
			continue
		}
		if isPhoneLikeRule(rule.Name, rule.Pattern) && looksLikeSecretToken(promptFull) {
			continue
		}
		if loc := re.FindStringIndex(promptFull); loc != nil && loc[0] >= 3 {
			if strings.EqualFold(promptFull[loc[0]-3:loc[0]], "sk-") {
				continue
			}
		}
		ruleTriggered = rule.Name
		matchedWarning = strings.TrimSpace(rule.WarningMessage)
		ruleAction := NormalizeGuardRuleAction(rule.Action)

		if ruleAction == "BLOCK" {
			action = "Blocked"
			status = fmt.Sprintf("Blocked (%s)", rule.Name)
			riskScore = 95
			predictiveRisk = "CRITICAL"
			predictedCategory = "SECURITY_POLICY_VIOLATION"
			break
		} else if ruleAction == "WARN" {
			// Log keeps the real prompt; ChatGPT gets prompt+warning via forward_prompt on the API.
			action = "Warned"
			status = fmt.Sprintf("Warned (%s)", rule.Name)
			riskScore = 55
			predictiveRisk = "MEDIUM"
			predictedCategory = "SUSPICIOUS_CONTENT"
			break
		}
	}

	if action == "Allowed" && looksLikeSecretToken(promptFull) {
		for _, rule := range rules {
			n := strings.ToLower(rule.Name)
			if strings.Contains(n, "phone") || strings.Contains(n, "mobile") {
				continue
			}
			if strings.Contains(n, "api") || strings.Contains(n, "key") || strings.Contains(n, "secret") || strings.Contains(n, "token") || strings.Contains(n, "openai") {
				ruleTriggered = rule.Name
				matchedWarning = strings.TrimSpace(rule.WarningMessage)
				action = "Blocked"
				status = fmt.Sprintf("Blocked (%s)", rule.Name)
				riskScore = 95
				predictiveRisk = "CRITICAL"
				predictedCategory = "SECURITY_POLICY_VIOLATION"
				break
			}
		}
	}

	if ruleTriggered == "" {
		if riskScore > 20 {
			predictiveRisk = "MEDIUM"
		}
	}

	preview = promptFull
	if len(preview) > 100 {
		preview = preview[:97] + "..."
	}

	metaBytes, _ := json.Marshal(metadata)

	agentID := ""
	agentHostname := ""
	if v, ok := metadata["agent_id"].(string); ok {
		agentID = strings.TrimSpace(v)
	}
	if v, ok := metadata["agent_hostname"].(string); ok {
		agentHostname = strings.TrimSpace(v)
	}
	attachmentName := ""
	if v, ok := metadata["file_name"].(string); ok {
		attachmentName = strings.TrimSpace(v)
	}

	logEntry := BrowserAILog{
		ID:                uuid.New().String(),
		Timestamp:         time.Now(),
		Platform:          platform,
		UserPromptPreview: preview,
		UserPromptFull:    promptFull,
		EstTokens:         estTokens,
		ClientIP:          clientIP,
		AgentID:           agentID,
		AgentHostname:     agentHostname,
		Status:            status,
		Action:            action,
		RuleTriggered:     ruleTriggered,
		RiskScore:         riskScore,
		PredictiveRisk:    predictiveRisk,
		PredictedCategory: predictedCategory,
		AttachmentName:    attachmentName,
		Metadata:          string(metaBytes),
		CreatedAt:         time.Now(),
	}

	if err := m.db.WithContext(ctx).Create(&logEntry).Error; err != nil {
		return nil, "", err
	}

	if domain, ok := metadata["domain"].(string); ok && domain != "" {
		m.db.WithContext(ctx).Model(&BrowserTargetWebsite{}).Where("domain = ?", domain).UpdateColumn("intercepted_count", gorm.Expr("intercepted_count + 1"))
	}

	return &logEntry, matchedWarning, nil
}

// UpdateLogAttachment links a stored upload file to an intercept log.
func (m *BrowserAIManager) UpdateLogAttachment(ctx context.Context, logID, name, storedName, contentType string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil || strings.TrimSpace(logID) == "" || strings.TrimSpace(storedName) == "" {
		return nil
	}
	return m.db.WithContext(ctx).Model(&BrowserAILog{}).Where("id = ?", logID).Updates(map[string]any{
		"attachment_name":         strings.TrimSpace(name),
		"attachment_stored_name":  strings.TrimSpace(storedName),
		"attachment_content_type": strings.TrimSpace(contentType),
	}).Error
}

// GetLogByID returns one intercept log by id.
func (m *BrowserAIManager) GetLogByID(ctx context.Context, id string) (*BrowserAILog, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.db == nil || strings.TrimSpace(id) == "" {
		return nil, fmt.Errorf("log not found")
	}
	var log BrowserAILog
	if err := m.db.WithContext(ctx).Where("id = ?", id).First(&log).Error; err != nil {
		return nil, err
	}
	return &log, nil
}

// UpdateLogReplyBot stores the Reply Bot provider/model/text on an existing intercept log.
func (m *BrowserAIManager) UpdateLogReplyBot(ctx context.Context, logID, provider, model, text string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil || strings.TrimSpace(logID) == "" {
		return nil
	}
	return m.db.WithContext(ctx).Model(&BrowserAILog{}).Where("id = ?", logID).Updates(map[string]any{
		"reply_bot_provider": provider,
		"reply_bot_model":    model,
		"reply_bot_text":     text,
	}).Error
}

// UpdateLogActionStatus updates action/status after Reply Bot "all questions" mode answers.
func (m *BrowserAIManager) UpdateLogActionStatus(ctx context.Context, logID, action, status string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil || strings.TrimSpace(logID) == "" {
		return nil
	}
	updates := map[string]any{}
	if strings.TrimSpace(action) != "" {
		updates["action"] = action
	}
	if strings.TrimSpace(status) != "" {
		updates["status"] = status
	}
	if len(updates) == 0 {
		return nil
	}
	return m.db.WithContext(ctx).Model(&BrowserAILog{}).Where("id = ?", logID).Updates(updates).Error
}

// NormalizeGuardRuleAction maps legacy REDACT to WARN. Only BLOCK and WARN are supported.
func NormalizeGuardRuleAction(action string) string {
	a := strings.ToUpper(strings.TrimSpace(action))
	switch a {
	case "WARN", "ALERT":
		return "WARN"
	case "REDACT":
		return "WARN"
	case "BLOCK":
		return "BLOCK"
	case "":
		return "BLOCK"
	default:
		return "BLOCK"
	}
}

// FormatWarnedForwardPrompt is what ChatGPT/browser receives on WARN: full original prompt + warning.
// Prompt Logs still store the original prompt only.
func FormatWarnedForwardPrompt(original, warningMessage string) string {
	w := strings.TrimSpace(warningMessage)
	if w == "" {
		w = "This prompt triggered a UnifAI Guard warning."
	}
	return strings.TrimRight(original, " \t\r\n") + "\n\n[UNIFAI WARNING] " + w
}

// SecurityReplyForRule returns only the admin-authored warning. Empty if none was set.
func SecurityReplyForRule(ruleTriggered, warningMessage string) string {
	return strings.TrimSpace(warningMessage)
}

func hashUninstallKey(plaintext string) string {
	sum := sha256.Sum256([]byte(strings.TrimSpace(plaintext)))
	return hex.EncodeToString(sum[:])
}

func (m *BrowserAIManager) ensureAgentSettingsLocked(ctx context.Context) (*BrowserAIAgentSettings, error) {
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}
	var settings BrowserAIAgentSettings
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserAIAgentSettingsID).First(&settings).Error; err != nil {
		settings = BrowserAIAgentSettings{
			ID:                  BrowserAIAgentSettingsID,
			RequireUninstallKey: true,
			UpdatedAt:           time.Now(),
		}
		if createErr := m.db.WithContext(ctx).Create(&settings).Error; createErr != nil {
			return nil, createErr
		}
	}
	settings.KeyConfigured = strings.TrimSpace(settings.UninstallKeyHash) != ""
	return &settings, nil
}

func (m *BrowserAIManager) GetAgentSettings(ctx context.Context) (*BrowserAIAgentSettings, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.ensureAgentSettingsLocked(ctx)
}

func (m *BrowserAIManager) SaveUninstallKey(ctx context.Context, plaintext, updatedBy string, requireKey *bool) (*BrowserAIAgentSettings, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, err := m.ensureAgentSettingsLocked(ctx); err != nil {
		return nil, err
	}
	updates := map[string]any{
		"updated_at": time.Now(),
		"updated_by": strings.TrimSpace(updatedBy),
	}
	if plaintext = strings.TrimSpace(plaintext); plaintext != "" {
		updates["uninstall_key_hash"] = hashUninstallKey(plaintext)
	}
	if requireKey != nil {
		updates["require_uninstall_key"] = *requireKey
	}
	if err := m.db.WithContext(ctx).Model(&BrowserAIAgentSettings{}).Where("id = ?", BrowserAIAgentSettingsID).Updates(updates).Error; err != nil {
		return nil, err
	}
	return m.ensureAgentSettingsLocked(ctx)
}

func (m *BrowserAIManager) VerifyUninstallKey(ctx context.Context, plaintext string) (bool, *BrowserAIAgentSettings, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.db == nil {
		return false, nil, fmt.Errorf("database not initialized")
	}
	var settings BrowserAIAgentSettings
	if err := m.db.WithContext(ctx).Where("id = ?", BrowserAIAgentSettingsID).First(&settings).Error; err != nil {
		return false, nil, err
	}
	settings.KeyConfigured = strings.TrimSpace(settings.UninstallKeyHash) != ""
	// If admin never saved a key, do not lock employees out of uninstall.
	if !settings.RequireUninstallKey || !settings.KeyConfigured {
		return true, &settings, nil
	}
	ok := hashUninstallKey(plaintext) == settings.UninstallKeyHash
	return ok, &settings, nil
}

func (m *BrowserAIManager) UpsertAgentHeartbeat(ctx context.Context, incoming *BrowserAIAgent) (*BrowserAIAgent, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}
	if incoming == nil || strings.TrimSpace(incoming.ID) == "" {
		return nil, fmt.Errorf("agent id is required")
	}
	now := time.Now()
	var existing BrowserAIAgent
	err := m.db.WithContext(ctx).Where("id = ?", incoming.ID).First(&existing).Error
	if err != nil {
		agent := BrowserAIAgent{
			ID:            strings.TrimSpace(incoming.ID),
			Hostname:      strings.TrimSpace(incoming.Hostname),
			Username:      strings.TrimSpace(incoming.Username),
			IPAddress:     strings.TrimSpace(incoming.IPAddress),
			MacAddress:    strings.TrimSpace(incoming.MacAddress),
			TransportName: nicGUIDFromTransport(incoming.TransportName),
			OSVersion:     strings.TrimSpace(incoming.OSVersion),
			AgentVersion:  strings.TrimSpace(incoming.AgentVersion),
			Status:        AgentStatusActive,
			LastSeenAt:    now,
			InstalledAt:   now,
			CreatedAt:     now,
			UpdatedAt:     now,
		}
		if createErr := m.db.WithContext(ctx).Create(&agent).Error; createErr != nil {
			return nil, createErr
		}
		return &agent, nil
	}

	existing.Hostname = firstNonEmpty(strings.TrimSpace(incoming.Hostname), existing.Hostname)
	existing.Username = firstNonEmpty(strings.TrimSpace(incoming.Username), existing.Username)
	existing.IPAddress = firstNonEmpty(strings.TrimSpace(incoming.IPAddress), existing.IPAddress)
	existing.MacAddress = firstNonEmpty(strings.TrimSpace(incoming.MacAddress), existing.MacAddress)
	if guid := nicGUIDFromTransport(incoming.TransportName); guid != "" {
		existing.TransportName = guid
	}
	existing.OSVersion = firstNonEmpty(strings.TrimSpace(incoming.OSVersion), existing.OSVersion)
	existing.AgentVersion = firstNonEmpty(strings.TrimSpace(incoming.AgentVersion), existing.AgentVersion)
	existing.LastSeenAt = now
	existing.UpdatedAt = now
	if existing.UninstallRequested || existing.Status == AgentStatusUninstallPending {
		existing.Status = AgentStatusUninstallPending
		existing.UninstallRequested = true
	} else {
		existing.Status = AgentStatusActive
		existing.UninstalledAt = nil
	}
	if err := m.db.WithContext(ctx).Save(&existing).Error; err != nil {
		return nil, err
	}
	return &existing, nil
}

func nicGUIDFromTransport(raw string) string {
	s := strings.TrimSpace(raw)
	if s == "" {
		return ""
	}
	m := nicGUID.FindString(s)
	if m == "" {
		return ""
	}
	return strings.ToUpper(m)
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if strings.TrimSpace(v) != "" {
			return v
		}
	}
	return ""
}

func (m *BrowserAIManager) ListAgents(ctx context.Context, status, search string, limit, offset int) ([]BrowserAIAgent, int64, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var agents []BrowserAIAgent
	var total int64
	if m.db == nil {
		return agents, 0, nil
	}

	query := m.db.WithContext(ctx).Model(&BrowserAIAgent{})
	if status != "" && strings.ToLower(status) != "all" {
		query = query.Where("LOWER(status) = ?", strings.ToLower(status))
	}
	if search != "" {
		s := "%" + strings.ToLower(search) + "%"
		query = query.Where(
			"LOWER(hostname) LIKE ? OR LOWER(username) LIKE ? OR LOWER(ip_address) LIKE ? OR LOWER(mac_address) LIKE ? OR LOWER(transport_name) LIKE ? OR LOWER(id) LIKE ? OR LOWER(agent_version) LIKE ?",
			s, s, s, s, s, s, s,
		)
	}
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	if limit <= 0 {
		limit = 50
	}
	err := query.Order("last_seen_at DESC").Limit(limit).Offset(offset).Find(&agents).Error
	return agents, total, err
}

func (m *BrowserAIManager) MarkAgentUninstalled(ctx context.Context, agentID string) (*BrowserAIAgent, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}
	agentID = strings.TrimSpace(agentID)
	if agentID == "" {
		return nil, fmt.Errorf("agent id is required")
	}
	now := time.Now()
	var agent BrowserAIAgent
	err := m.db.WithContext(ctx).Where("id = ?", agentID).First(&agent).Error
	if err != nil {
		// Never registered / heartbeat never landed — still record uninstall so Windows setup can finish.
		agent = BrowserAIAgent{
			ID:                 agentID,
			Status:             AgentStatusUninstalled,
			UninstallRequested: false,
			LastSeenAt:         now,
			InstalledAt:        now,
			UninstalledAt:      &now,
			CreatedAt:          now,
			UpdatedAt:          now,
		}
		if createErr := m.db.WithContext(ctx).Create(&agent).Error; createErr != nil {
			return nil, createErr
		}
		return &agent, nil
	}
	agent.Status = AgentStatusUninstalled
	agent.UninstallRequested = false
	agent.UninstalledAt = &now
	agent.UpdatedAt = now
	if err := m.db.WithContext(ctx).Save(&agent).Error; err != nil {
		return nil, err
	}
	return &agent, nil
}

func (m *BrowserAIManager) RequestRemoteUninstall(ctx context.Context, agentID string) (*BrowserAIAgent, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}
	agentID = strings.TrimSpace(agentID)
	if agentID == "" {
		return nil, fmt.Errorf("agent id is required")
	}
	var agent BrowserAIAgent
	if err := m.db.WithContext(ctx).Where("id = ?", agentID).First(&agent).Error; err != nil {
		return nil, fmt.Errorf("agent not found")
	}
	if agent.Status == AgentStatusUninstalled {
		return &agent, nil
	}
	now := time.Now()
	agent.UninstallRequested = true
	agent.Status = AgentStatusUninstallPending
	agent.UpdatedAt = now
	if err := m.db.WithContext(ctx).Save(&agent).Error; err != nil {
		return nil, err
	}
	return &agent, nil
}

func (m *BrowserAIManager) AckRemoteUninstall(ctx context.Context, agentID string) (*BrowserAIAgent, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.db == nil {
		return nil, fmt.Errorf("database not initialized")
	}
	agentID = strings.TrimSpace(agentID)
	if agentID == "" {
		return nil, fmt.Errorf("agent id is required")
	}
	var agent BrowserAIAgent
	if err := m.db.WithContext(ctx).Where("id = ?", agentID).First(&agent).Error; err != nil {
		return nil, fmt.Errorf("agent not found")
	}
	if !agent.UninstallRequested && agent.Status != AgentStatusUninstallPending {
		return nil, fmt.Errorf("remote uninstall was not requested")
	}
	now := time.Now()
	agent.Status = AgentStatusUninstalled
	agent.UninstallRequested = false
	agent.UninstalledAt = &now
	agent.UpdatedAt = now
	if err := m.db.WithContext(ctx).Save(&agent).Error; err != nil {
		return nil, err
	}
	return &agent, nil
}
