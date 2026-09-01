package handlers

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
)

const (
	browserAIGuardBotDefaultProvider = "ollama"
	browserAIGuardBotDefaultModel      = "llama3.2"
	browserAIGuardBotDefaultOllamaURL  = "http://76.13.243.253:11434"
	browserAIGuardBotMaxPromptRunes    = 50000
)

type ollamaChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ollamaChatRequest struct {
	Model    string              `json:"model"`
	Messages []ollamaChatMessage `json:"messages"`
	Stream   bool                `json:"stream"`
	Format   string              `json:"format,omitempty"`
}

type ollamaChatResponse struct {
	Message struct {
		Content string `json:"content"`
	} `json:"message"`
	Error string `json:"error,omitempty"`
}

func defaultOllamaBaseURL() string {
	for _, key := range []string{"BROWSER_AI_OLLAMA_URL", "OLLAMA_BASE_URL"} {
		if v := strings.TrimSpace(os.Getenv(key)); v != "" {
			return strings.TrimRight(v, "/")
		}
	}
	return browserAIGuardBotDefaultOllamaURL
}

func isOllamaGuardProvider(provider string) bool {
	p := strings.ToLower(strings.TrimSpace(provider))
	return p == "" || p == "ollama"
}

func applyAIBotDefaults(rule *logstore.BrowserGuardRule) {
	if rule == nil || strings.ToLower(strings.TrimSpace(rule.RuleType)) != "ai_bot" {
		return
	}
	if strings.TrimSpace(rule.BotProvider) == "" {
		rule.BotProvider = browserAIGuardBotDefaultProvider
	}
	if strings.TrimSpace(rule.BotModel) == "" {
		rule.BotModel = browserAIGuardBotDefaultModel
	}
}

func applyGuardBotDefaults(provider, model string) (string, string) {
	provider = strings.TrimSpace(provider)
	model = strings.TrimSpace(model)
	if provider == "" {
		provider = browserAIGuardBotDefaultProvider
	}
	if model == "" {
		model = browserAIGuardBotDefaultModel
	}
	return provider, model
}

func callOllamaChat(baseURL, model, systemPrompt, userMsg string, jsonMode bool, timeout time.Duration) (string, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		baseURL = defaultOllamaBaseURL()
	}
	model = strings.TrimSpace(model)
	if model == "" {
		model = browserAIGuardBotDefaultModel
	}

	messages := make([]ollamaChatMessage, 0, 2)
	if strings.TrimSpace(systemPrompt) != "" {
		messages = append(messages, ollamaChatMessage{
			Role:    "system",
			Content: systemPrompt,
		})
	}
	messages = append(messages, ollamaChatMessage{
		Role:    "user",
		Content: userMsg,
	})

	reqBody := ollamaChatRequest{
		Model:    model,
		Messages: messages,
		Stream:   false,
	}
	if jsonMode {
		reqBody.Format = "json"
	}

	body, err := sonic.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("ollama request encode failed: %w", err)
	}

	if timeout <= 0 {
		timeout = 90 * time.Second
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, baseURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("ollama request failed: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("ollama unreachable at %s: %w", baseURL, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("ollama response read failed: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("ollama HTTP %d: %s", resp.StatusCode, truncateRunes(string(respBody), 180))
	}

	var parsed ollamaChatResponse
	if err := sonic.Unmarshal(respBody, &parsed); err != nil {
		return "", fmt.Errorf("ollama response decode failed: %w", err)
	}
	if strings.TrimSpace(parsed.Error) != "" {
		return "", fmt.Errorf("ollama error: %s", strings.TrimSpace(parsed.Error))
	}
	text := strings.TrimSpace(parsed.Message.Content)
	if text == "" {
		return "", fmt.Errorf("empty ollama response")
	}
	return text, nil
}
