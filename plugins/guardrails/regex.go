package guardrails

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/unifai/unifai/core/schemas"
)

type RegexProvider struct {
	id       int
	patterns []RegexPattern
}

type RegexPattern struct {
	Pattern     string
	Description string
	Flags       string
	compiled    *regexp.Regexp
}

func NewRegexProvider(config GuardrailProvider) (*RegexProvider, error) {
	provider := &RegexProvider{
		id: config.ID,
	}

	patternsRaw, ok := config.Config["patterns"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("patterns configuration missing or invalid")
	}

	for _, pRaw := range patternsRaw {
		var patternStr, desc, flags string

		switch p := pRaw.(type) {
		case string:
			patternStr = strings.TrimSpace(p)
		case map[string]interface{}:
			patternStr, _ = p["pattern"].(string)
			desc, _ = p["description"].(string)
			flags, _ = p["flags"].(string)
		default:
			continue
		}

		if patternStr == "" {
			continue
		}

		expr := patternStr
		if flags == "i" {
			expr = "(?i)" + expr
		}

		compiled, err := regexp.Compile(expr)
		if err != nil {
			return nil, fmt.Errorf("invalid regex pattern %q: %w", patternStr, err)
		}

		provider.patterns = append(provider.patterns, RegexPattern{
			Pattern:     patternStr,
			Description: desc,
			Flags:       flags,
			compiled:    compiled,
		})
	}

	return provider, nil
}

func (p *RegexProvider) ValidateInput(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest) error {
	if req.ChatRequest == nil {
		return nil
	}

	for _, msg := range req.ChatRequest.Input {
		for _, content := range extractChatMessageTexts(msg) {
			if err := p.matchBlocked(content, "input"); err != nil {
				return err
			}
		}
	}
	return nil
}

func (p *RegexProvider) ValidateOutput(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest, resp *schemas.UnifAIResponse) error {
	for _, content := range extractChatOutputTexts(resp) {
		if err := p.matchBlocked(content, "output"); err != nil {
			return err
		}
	}
	return nil
}

// MatchText runs patterns against an arbitrary string (used for streamed accumulation).
func (p *RegexProvider) MatchText(content, phase string) error {
	return p.matchBlocked(content, phase)
}

func (p *RegexProvider) matchBlocked(content, phase string) error {
	for _, pattern := range p.patterns {
		if pattern.compiled.MatchString(content) {
			desc := pattern.Description
			if desc == "" {
				desc = pattern.Pattern
			}
			return fmt.Errorf("%s matches blocked pattern: %s", phase, desc)
		}
	}
	return nil
}

func extractChatMessageTexts(msg schemas.ChatMessage) []string {
	if msg.Content == nil {
		return nil
	}
	var texts []string
	if msg.Content.ContentStr != nil && *msg.Content.ContentStr != "" {
		texts = append(texts, *msg.Content.ContentStr)
	}
	for _, block := range msg.Content.ContentBlocks {
		if block.Type == schemas.ChatContentBlockTypeText && block.Text != nil && *block.Text != "" {
			texts = append(texts, *block.Text)
		}
		if block.Type == schemas.ChatContentBlockTypeRefusal && block.Refusal != nil && *block.Refusal != "" {
			texts = append(texts, *block.Refusal)
		}
	}
	return texts
}

func extractChatOutputTexts(resp *schemas.UnifAIResponse) []string {
	if resp == nil || resp.ChatResponse == nil || len(resp.ChatResponse.Choices) == 0 {
		return nil
	}
	var texts []string
	for _, choice := range resp.ChatResponse.Choices {
		if choice.ChatNonStreamResponseChoice != nil && choice.ChatNonStreamResponseChoice.Message != nil {
			texts = append(texts, extractChatMessageTexts(*choice.ChatNonStreamResponseChoice.Message)...)
		}
	}
	return texts
}
