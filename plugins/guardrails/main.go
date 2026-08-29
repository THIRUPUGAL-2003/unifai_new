package guardrails

import (
	"context"
	"fmt"

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
	
	// Create a CEL environment with variables for the request
	env, err := cel.NewEnv(
		cel.Variable("request.model", cel.StringType),
	)
	if err != nil {
		return fmt.Errorf("failed to create CEL env: %w", err)
	}

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled {
			continue
		}
		
		ast, issues := env.Compile(rule.CELExpression)
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

	// Prepare CEL variables
	modelName := ""
	if req.ChatRequest != nil {
		modelName = req.ChatRequest.Model
	}
	
	vars := map[string]interface{}{
		"request.model": modelName,
	}

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled || (rule.ApplyTo != "input" && rule.ApplyTo != "both") {
			continue
		}

		prg, ok := p.celPrograms[rule.ID]
		if !ok {
			continue
		}

		out, _, err := prg.Eval(vars)
		if err != nil {
			// Log error but don't block on evaluation failures
			continue
		}

		if match, ok := out.Value().(bool); ok && match {
			// Rule matched, run configured providers
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
	}

	return req, nil, nil
}

func (p *GuardrailsPlugin) PostLLMHook(ctx *schemas.UnifAIContext, resp *schemas.UnifAIResponse, err *schemas.UnifAIError) (*schemas.UnifAIResponse, *schemas.UnifAIError, error) {
	if p.config == nil || err != nil || resp == nil {
		return resp, err, nil
	}

	vars := map[string]interface{}{
		"request.model": modelNameFromResponse(resp),
	}

	for _, rule := range p.config.GuardrailRules {
		if !rule.Enabled || (rule.ApplyTo != "output" && rule.ApplyTo != "both") {
			continue
		}

		prg, ok := p.celPrograms[rule.ID]
		if !ok {
			continue
		}

		out, _, evalErr := prg.Eval(vars)
		if evalErr != nil {
			continue
		}

		if match, ok := out.Value().(bool); ok && match {
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
	}

	return resp, err, nil
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
