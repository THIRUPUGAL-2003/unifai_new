package guardrails

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/cel-go/cel"
	"github.com/unifai/unifai/core/schemas"
)

const PluginName = "guardrails"

// Ensure interface compliance
var _ schemas.LLMPlugin = (*GuardrailsPlugin)(nil)

type GuardrailsPlugin struct {
	config *Config
	
	// Pre-compiled CEL programs mapped by rule ID
	celPrograms map[int]cel.Program
	
	// Initialized providers mapped by their ID
	providers map[int]Provider
}

// Config passed during initialization is now defined in config.go

// Provider interface for all guardrail types
type Provider interface {
	ValidateInput(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest) error
	ValidateOutput(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest, resp *schemas.UnifAIResponse) error
}

func Init(ctx context.Context, config *Config, logger schemas.Logger) (schemas.BasePlugin, error) {
	plugin := &GuardrailsPlugin{
		config:      config,
		celPrograms: make(map[int]cel.Program),
		providers:   make(map[int]Provider),
	}
	
	if err := plugin.initializeProviders(); err != nil {
		logger.Error("failed to initialize guardrail providers: %v", err)
		return nil, err
	}
	if err := plugin.compileRules(); err != nil {
		logger.Error("failed to compile guardrail rules: %v", err)
		return nil, err
	}

	return plugin, nil
}

func (p *GuardrailsPlugin) initializeProviders() error {
	if p.config == nil {
		return nil
	}
	for _, providerCfg := range p.config.GuardrailProviders {
		if !providerCfg.Enabled {
			continue
		}
		
		switch providerCfg.ProviderName {
		case "regex":
			provider, err := NewRegexProvider(providerCfg)
			if err != nil {
				return fmt.Errorf("failed to initialize regex provider config %d: %w", providerCfg.ID, err)
			}
			p.providers[providerCfg.ID] = provider
		default:
			// For MVP, we ignore unknown providers instead of erroring
			continue
		}
	}
	return nil
}

func (p *GuardrailsPlugin) compileRules() error {
	if p.config == nil {
		return nil
	}
	
	// request is a map so expressions like request.model == "gpt-4" compile.
	// A dotted variable name ("request.model") is not a valid CEL identifier.
	env, err := cel.NewEnv(
		cel.Variable("request", cel.MapType(cel.StringType, cel.DynType)),
	)
	if err != nil {
		return fmt.Errorf("failed to create CEL env: %w", err)
	}

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled {
			continue
		}
		
		expr := strings.TrimSpace(rule.CELExpression)
		if expr == "" {
			expr = "true"
		}
		ast, issues := env.Compile(expr)
		if issues != nil && issues.Err() != nil {
			return fmt.Errorf("invalid CEL expression for rule %d: %w", rule.ID, issues.Err())
		}
		
		prg, err := env.Program(ast)
		if err != nil {
			return fmt.Errorf("failed to create CEL program for rule %d: %w", rule.ID, err)
		}
		
		p.celPrograms[rule.ID] = prg
	}
	
	return nil
}

// GetName returns the name of the plugin
func (p *GuardrailsPlugin) GetName() string {
	return PluginName
}

// Cleanup cleans up the plugin resources
func (p *GuardrailsPlugin) Cleanup() error {
	return nil
}

func (p *GuardrailsPlugin) PreRequestHook(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest) error {
	return nil
}

func (p *GuardrailsPlugin) PreLLMHook(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest) (*schemas.UnifAIRequest, *schemas.LLMPluginShortCircuit, error) {
	if p.config == nil {
		return nil, nil, nil
	}

	modelName := modelNameFromRequest(req)

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled || (rule.ApplyTo != "input" && rule.ApplyTo != "both") {
			continue
		}
		if !p.ruleMatches(rule, modelName) {
			continue
		}

		for _, providerID := range rule.ProviderConfigIDs {
			provider, ok := p.providers[providerID]
			if !ok {
				continue
			}

			if err := provider.ValidateInput(ctx, req); err != nil {
				return req, &schemas.LLMPluginShortCircuit{
					Error: guardrailViolationError(err.Error()),
				}, nil
			}
		}
	}

	return req, nil, nil
}

func (p *GuardrailsPlugin) PostLLMHook(ctx *schemas.UnifAIContext, resp *schemas.UnifAIResponse, err *schemas.UnifAIError) (*schemas.UnifAIResponse, *schemas.UnifAIError, error) {
	if p.config == nil || err != nil || resp == nil {
		return resp, err, nil
	}

	modelName := modelNameFromResponse(resp)

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled || (rule.ApplyTo != "output" && rule.ApplyTo != "both") {
			continue
		}
		if !p.ruleMatches(rule, modelName) {
			continue
		}

		for _, providerID := range rule.ProviderConfigIDs {
			provider, ok := p.providers[providerID]
			if !ok {
				continue
			}

			if validateErr := provider.ValidateOutput(ctx, nil, resp); validateErr != nil {
				return nil, guardrailViolationError(validateErr.Error()), nil
			}
		}
	}

	return resp, err, nil
}

func (p *GuardrailsPlugin) ruleMatches(rule GuardrailRule, model string) bool {
	if !ruleAppliesToModel(rule.Models, model) {
		return false
	}
	prg, ok := p.celPrograms[rule.ID]
	if !ok {
		return false
	}
	out, _, err := prg.Eval(map[string]interface{}{
		"request": map[string]interface{}{"model": model},
	})
	if err != nil {
		return false
	}
	match, ok := out.Value().(bool)
	return ok && match
}

func ruleAppliesToModel(selected []string, requestModel string) bool {
	if len(selected) == 0 {
		return true
	}
	for _, model := range selected {
		if model == "" || model == "*" {
			return true
		}
		if modelMatches(model, requestModel) {
			return true
		}
	}
	return false
}

func modelMatches(selected, requestModel string) bool {
	if selected == "" || requestModel == "" {
		return selected == requestModel
	}
	if selected == requestModel {
		return true
	}
	_, selectedBare := schemas.ParseModelString(selected, "")
	_, requestBare := schemas.ParseModelString(requestModel, "")
	if selectedBare != "" && selectedBare == requestBare {
		return true
	}
	if selectedBare != "" && selectedBare == requestModel {
		return true
	}
	if requestBare != "" && requestBare == selected {
		return true
	}
	return strings.HasSuffix(requestModel, "/"+selected) || strings.HasSuffix(selected, "/"+requestModel)
}

func modelNameFromRequest(req *schemas.UnifAIRequest) string {
	if req == nil {
		return ""
	}
	if req.ChatRequest != nil && req.ChatRequest.Model != "" {
		return req.ChatRequest.Model
	}
	if req.ResponsesRequest != nil && req.ResponsesRequest.Model != "" {
		return req.ResponsesRequest.Model
	}
	return ""
}

func modelNameFromResponse(resp *schemas.UnifAIResponse) string {
	if resp == nil {
		return ""
	}
	if resp.ChatResponse != nil && resp.ChatResponse.Model != "" {
		return resp.ChatResponse.Model
	}
	if resp.ResponsesResponse != nil && resp.ResponsesResponse.Model != "" {
		return resp.ResponsesResponse.Model
	}
	return ""
}

func guardrailViolationError(message string) *schemas.UnifAIError {
	statusCode := 400
	code := "guardrail_violation"
	return &schemas.UnifAIError{
		IsUnifAIError: true,
		StatusCode:    &statusCode,
		Error: &schemas.ErrorField{
			Message: message,
			Code:    &code,
		},
	}
}
