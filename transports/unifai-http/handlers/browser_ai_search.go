package handlers

import (
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/bytedance/sonic"
	"github.com/google/uuid"
	"github.com/valyala/fasthttp"
)

// BrowserAISearchLogEntry represents an in-memory live search event.
// As instructed, this is kept in-memory (no database required for now).
type BrowserAISearchLogEntry struct {
	ID             string    `json:"id"`
	Timestamp      time.Time `json:"timestamp"`
	Engine         string    `json:"engine"`          // "Google", "Bing", "Safari / Apple", "DuckDuckGo", "Yahoo"
	Browser        string    `json:"browser"`         // "Edge", "Chrome", "Safari", "Firefox", "Brave"
	IsIncognito    bool      `json:"is_incognito"`    // true if incognito / private mode
	Query          string    `json:"query"`           // Searched keywords
	ClickedURL     string    `json:"clicked_url"`     // URL of search result link clicked
	ClickedTitle   string    `json:"clicked_title"`   // Host or title of clicked result
	URL            string    `json:"url"`             // Raw search URL
	Host           string    `json:"host"`            // Search engine host
	ClientIP       string    `json:"client_ip"`       // Originating IP
	AgentHostname  string    `json:"agent_hostname"`  // Device hostname
	AgentID        string    `json:"agent_id"`        // Device / agent ID
	RiskScore      int       `json:"risk_score"`      // 0 - 100
	PredictiveRisk string    `json:"predictive_risk"` // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
	RiskCategory   string    `json:"risk_category"`   // "DLP / Data Leak", "Exploit / Bypass", "Reconnaissance", "General Search"
	CreatedAt      string    `json:"created_at"`
}

var (
	searchLogsMu   sync.RWMutex
	searchLogsList []BrowserAISearchLogEntry
)

func init() {
	// Seed initial realistic enterprise search logs to demonstrate the feature working immediately
	now := time.Now()
	searchLogsList = []BrowserAISearchLogEntry{
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-2 * time.Minute),
			Engine:         "Google",
			Browser:        "Chrome",
			IsIncognito:    true,
			Query:          "merger acquisition confidential financial model 2026 xlsx download",
			ClickedURL:     "https://sec-filings.corp-archive.internal/deals/q4-ma-brief.pdf",
			ClickedTitle:   "sec-filings.corp-archive.internal",
			URL:            "https://www.google.com/search?q=merger+acquisition+confidential+financial+model+2026+xlsx+download",
			Host:           "www.google.com",
			ClientIP:       "192.168.1.104",
			AgentHostname:  "FINANCE-DESK-04",
			AgentID:        "agent-fin-04",
			RiskScore:      88,
			PredictiveRisk: "CRITICAL",
			RiskCategory:   "DLP / Data Leak",
			CreatedAt:      now.Add(-2 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-8 * time.Minute),
			Engine:         "Bing",
			Browser:        "Edge",
			IsIncognito:    true,
			Query:          "how to kill background dlp service windows powershell bypass admin",
			ClickedURL:     "https://github.com/adversary-tools/edr-silencer",
			ClickedTitle:   "github.com/adversary-tools/edr-silencer",
			URL:            "https://www.bing.com/search?q=how+to+kill+background+dlp+service+windows+powershell+bypass+admin",
			Host:           "www.bing.com",
			ClientIP:       "192.168.1.142",
			AgentHostname:  "DEV-LAPTOP-09",
			AgentID:        "agent-dev-09",
			RiskScore:      92,
			PredictiveRisk: "CRITICAL",
			RiskCategory:   "Exploit / Bypass",
			CreatedAt:      now.Add(-8 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-15 * time.Minute),
			Engine:         "Safari / Apple",
			Browser:        "Safari",
			IsIncognito:    false,
			Query:          "soc2 type 2 audit compliance requirements checklist 2026",
			ClickedURL:     "https://www.aicpa-cima.com/resources/toolkit/soc-2-reporting",
			ClickedTitle:   "aicpa-cima.com",
			URL:            "https://www.google.com/search?q=soc2+type+2+audit+compliance+requirements+checklist+2026",
			Host:           "www.google.com",
			ClientIP:       "192.168.1.75",
			AgentHostname:  "EXEC-MACBOOK-PRO",
			AgentID:        "agent-exec-01",
			RiskScore:      15,
			PredictiveRisk: "LOW",
			RiskCategory:   "General Search",
			CreatedAt:      now.Add(-15 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-27 * time.Minute),
			Engine:         "DuckDuckGo",
			Browser:        "Firefox",
			IsIncognito:    true,
			Query:          "corporate employee ssn and payroll records leak database search",
			ClickedURL:     "https://pastebin.com/raw/d84fK9m",
			ClickedTitle:   "pastebin.com",
			URL:            "https://duckduckgo.com/?q=corporate+employee+ssn+and+payroll+records+leak+database+search",
			Host:           "duckduckgo.com",
			ClientIP:       "192.168.1.189",
			AgentHostname:  "HR-WORKSTATION-02",
			AgentID:        "agent-hr-02",
			RiskScore:      95,
			PredictiveRisk: "CRITICAL",
			RiskCategory:   "DLP / Data Leak",
			CreatedAt:      now.Add(-27 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-42 * time.Minute),
			Engine:         "Bing",
			Browser:        "Edge",
			IsIncognito:    false,
			Query:          "latest enterprise generative ai security architecture whitepaper",
			ClickedURL:     "https://learn.microsoft.com/en-us/security/cybersecurity/ai-guidance",
			ClickedTitle:   "learn.microsoft.com",
			URL:            "https://www.bing.com/search?q=latest+enterprise+generative+ai+security+architecture+whitepaper",
			Host:           "www.bing.com",
			ClientIP:       "192.168.1.104",
			AgentHostname:  "FINANCE-DESK-04",
			AgentID:        "agent-fin-04",
			RiskScore:      10,
			PredictiveRisk: "LOW",
			RiskCategory:   "General Search",
			CreatedAt:      now.Add(-42 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-65 * time.Minute),
			Engine:         "Google",
			Browser:        "Chrome",
			IsIncognito:    true,
			Query:          "competitor internal roadmap leaked confidential slideshare",
			ClickedURL:     "",
			ClickedTitle:   "",
			URL:            "https://www.google.com/search?q=competitor+internal+roadmap+leaked+confidential+slideshare",
			Host:           "www.google.com",
			ClientIP:       "192.168.1.160",
			AgentHostname:  "MARKETING-PC-07",
			AgentID:        "agent-mkt-07",
			RiskScore:      76,
			PredictiveRisk: "HIGH",
			RiskCategory:   "Reconnaissance",
			CreatedAt:      now.Add(-65 * time.Minute).Format(time.RFC3339),
		},
		{
			ID:             uuid.New().String(),
			Timestamp:      now.Add(-90 * time.Minute),
			Engine:         "Yahoo",
			Browser:        "Safari",
			IsIncognito:    false,
			Query:          "top ai developer productivity tools 2026 review",
			ClickedURL:     "https://techcrunch.com/2026/02/top-developer-tools",
			ClickedTitle:   "techcrunch.com",
			URL:            "https://search.yahoo.com/search?p=top+ai+developer+productivity+tools+2026+review",
			Host:           "search.yahoo.com",
			ClientIP:       "192.168.1.75",
			AgentHostname:  "EXEC-MACBOOK-PRO",
			AgentID:        "agent-exec-01",
			RiskScore:      5,
			PredictiveRisk: "LOW",
			RiskCategory:   "General Search",
			CreatedAt:      now.Add(-90 * time.Minute).Format(time.RFC3339),
		},
	}
}

// computeSearchRisk assigns threat scores and category based on query keywords.
func computeSearchRisk(query string) (int, string, string) {
	q := strings.ToLower(query)
	critKeywords := []string{"bypass", "kill agent", "disable dlp", "exploit", "ssn", "password", "private key", "secret key", "leak", "payroll", "unauthorized"}
	for _, kw := range critKeywords {
		if strings.Contains(q, kw) {
			if strings.Contains(q, "bypass") || strings.Contains(q, "kill") || strings.Contains(q, "exploit") {
				return 92, "CRITICAL", "Exploit / Bypass"
			}
			return 90, "CRITICAL", "DLP / Data Leak"
		}
	}

	highKeywords := []string{"confidential", "internal roadmap", "acquisition", "financial model", "merger", "patent pending", "source code"}
	for _, kw := range highKeywords {
		if strings.Contains(q, kw) {
			return 78, "HIGH", "DLP / Data Leak"
		}
	}

	medKeywords := []string{"competitor", "pricing sheet", "salary", "bonus", "audit", "security test"}
	for _, kw := range medKeywords {
		if strings.Contains(q, kw) {
			return 45, "MEDIUM", "Reconnaissance"
		}
	}

	return 10, "LOW", "General Search"
}

// getSearchLogs serves in-memory search logs with filtering.
func (h *BrowserAIHandler) getSearchLogs(ctx *fasthttp.RequestCtx) {
	engineFilter := strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("engine"))))
	browserFilter := strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("browser"))))
	incognitoFilter := strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("is_incognito"))))
	searchFilter := strings.ToLower(strings.TrimSpace(string(ctx.QueryArgs().Peek("search"))))
	limitStr := string(ctx.QueryArgs().Peek("limit"))
	offsetStr := string(ctx.QueryArgs().Peek("offset"))

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)
	if limit <= 0 {
		limit = 50
	}

	searchLogsMu.RLock()
	defer searchLogsMu.RUnlock()

	var filtered []BrowserAISearchLogEntry
	incognitoCount := 0
	queriesCount := 0
	clicksCount := 0

	for _, entry := range searchLogsList {
		if entry.IsIncognito {
			incognitoCount++
		}
		if entry.Query != "" {
			queriesCount++
		}
		if entry.ClickedURL != "" {
			clicksCount++
		}

		// Filter Engine
		if engineFilter != "" && !strings.Contains(strings.ToLower(entry.Engine), engineFilter) {
			continue
		}
		// Filter Browser
		if browserFilter != "" && !strings.Contains(strings.ToLower(entry.Browser), browserFilter) {
			continue
		}
		// Filter Incognito
		if incognitoFilter == "true" && !entry.IsIncognito {
			continue
		} else if incognitoFilter == "false" && entry.IsIncognito {
			continue
		}
		// Filter Search term
		if searchFilter != "" {
			qMatch := strings.Contains(strings.ToLower(entry.Query), searchFilter)
			cMatch := strings.Contains(strings.ToLower(entry.ClickedURL), searchFilter) || strings.Contains(strings.ToLower(entry.ClickedTitle), searchFilter)
			hMatch := strings.Contains(strings.ToLower(entry.AgentHostname), searchFilter) || strings.Contains(strings.ToLower(entry.ClientIP), searchFilter)
			if !qMatch && !cMatch && !hMatch {
				continue
			}
		}

		filtered = append(filtered, entry)
	}

	total := len(filtered)
	start := offset
	if start > total {
		start = total
	}
	end := start + limit
	if end > total {
		end = total
	}

	paged := filtered[start:end]
	if paged == nil {
		paged = []BrowserAISearchLogEntry{}
	}

	SendJSON(ctx, map[string]any{
		"logs":            paged,
		"total":           total,
		"incognito_count": incognitoCount,
		"queries_count":   queriesCount,
		"clicks_count":    clicksCount,
		"limit":           limit,
		"offset":          offset,
	})
}

// recordSearchLog records a search query or click in memory from proxy or UI test.
func (h *BrowserAIHandler) recordSearchLog(ctx *fasthttp.RequestCtx) {
	var body BrowserAISearchLogEntry
	if err := sonic.Unmarshal(ctx.PostBody(), &body); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}

	if body.ID == "" {
		body.ID = uuid.New().String()
	}
	if body.Timestamp.IsZero() {
		body.Timestamp = time.Now()
	}
	body.CreatedAt = body.Timestamp.Format(time.RFC3339)

	if body.Engine == "" {
		body.Engine = "Google"
	}
	if body.Browser == "" {
		body.Browser = "Chrome"
	}

	if body.RiskScore == 0 && body.Query != "" {
		score, risk, cat := computeSearchRisk(body.Query)
		body.RiskScore = score
		body.PredictiveRisk = risk
		body.RiskCategory = cat
	} else if body.PredictiveRisk == "" {
		body.PredictiveRisk = "LOW"
		body.RiskCategory = "General Search"
	}

	searchLogsMu.Lock()
	// Prepend to top so newest searches appear first
	searchLogsList = append([]BrowserAISearchLogEntry{body}, searchLogsList...)
	if len(searchLogsList) > 500 {
		searchLogsList = searchLogsList[:500]
	}
	searchLogsMu.Unlock()

	SendJSON(ctx, map[string]any{
		"status": "success",
		"log":    body,
	})
}

// deleteSearchLogs clears the in-memory search logs buffer.
func (h *BrowserAIHandler) deleteSearchLogs(ctx *fasthttp.RequestCtx) {
	searchLogsMu.Lock()
	searchLogsList = []BrowserAISearchLogEntry{}
	searchLogsMu.Unlock()

	SendJSON(ctx, map[string]any{
		"status":  "success",
		"message": "Search logs cleared",
	})
}
