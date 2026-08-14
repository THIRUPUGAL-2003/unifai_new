package guardrails

import (
	"fmt"
	"regexp"

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
		pMap, ok := pRaw.(map[string]interface{})
		if !ok {
			continue
		}

		patternStr, _ := pMap["pattern"].(string)
		desc, _ := pMap["description"].(string)
		flags, _ := pMap["flags"].(string)

		if patternStr == "" {
			continue
		}

		// Simple regex compilation. We prepend case insensitive flag if requested
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
		return nil // Only scanning chat requests for MVP
	}

	for _, msg := range req.ChatRequest.Input {
		if msg.Content != nil && msg.Content.ContentStr != nil {
			content := *msg.Content.ContentStr
			for _, pattern := range p.patterns {
				if pattern.compiled.MatchString(content) {
					return fmt.Errorf("input matches blocked pattern: %s", pattern.Description)
				}
			}
		}
	}
	return nil
}

func (p *RegexProvider) ValidateOutput(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest, resp *schemas.UnifAIResponse) error {
	if resp.ChatResponse == nil || len(resp.ChatResponse.Choices) == 0 {
		return nil
	}
	
	choice := resp.ChatResponse.Choices[0]
	if choice.ChatNonStreamResponseChoice == nil || choice.ChatNonStreamResponseChoice.Message == nil {
		return nil
	}
	
	msg := choice.ChatNonStreamResponseChoice.Message
	if msg.Content == nil || msg.Content.ContentStr == nil {
		return nil
	}

	content := *msg.Content.ContentStr
	for _, pattern := range p.patterns {
		if pattern.compiled.MatchString(content) {
			return fmt.Errorf("output matches blocked pattern: %s", pattern.Description)
		}
	}
	return nil
}
