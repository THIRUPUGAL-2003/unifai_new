package governance

import (
	unifai "github.com/unifai/unifai/core"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/circuitbreaker"
)

type circuitBreakerCtxKey string

const (
	circuitBreakerPrimaryProviderKey circuitBreakerCtxKey = "governance-circuit-breaker-primary-provider"
	circuitBreakerPrimaryModelKey    circuitBreakerCtxKey = "governance-circuit-breaker-primary-model"
)

func (p *GovernancePlugin) applyCircuitBreakerFailover(ctx *schemas.UnifAIContext, req *schemas.UnifAIRequest) bool {
	provider, model, _ := req.GetRequestFields()
	if model == "" {
		return false
	}
	decision, ok := circuitbreaker.Default.ApplyFailover(provider, model)
	if !ok || decision == nil {
		return false
	}
	ctx.SetValue(circuitBreakerPrimaryProviderKey, decision.FromProv)
	ctx.SetValue(circuitBreakerPrimaryModelKey, decision.FromModel)
	req.SetProvider(schemas.ModelProvider(decision.ToProv))
	req.SetModel(decision.ToModel)
	schemas.AppendToContextList(ctx, schemas.UnifAIContextKeyRoutingEnginesUsed, schemas.RoutingEngineCircuitBreaker)
	if p.logger != nil {
		p.logger.Info("[Governance] Circuit breaker failover policy=%s %s/%s → %s/%s",
			decision.PolicyName, decision.FromProv, decision.FromModel, decision.ToProv, decision.ToModel)
	}
	ctx.AppendRoutingEngineLog(schemas.RoutingEngineCircuitBreaker, schemas.LogLevelInfo,
		"Failover: "+decision.FromProv+"/"+decision.FromModel+" → "+decision.ToProv+"/"+decision.ToModel)
	return true
}

func (p *GovernancePlugin) evaluateCircuitBreakerTrip(ctx *schemas.UnifAIContext, result *schemas.UnifAIResponse, err *schemas.UnifAIError) {
	if !unifai.IsFinalChunk(ctx) {
		return
	}
	_, provider, model, _ := unifai.GetResponseFields(result, err)
	if model == "" {
		return
	}
	// If we failed over on this request, the upstream primary was not called — do not trip.
	if prov, _ := ctx.Value(circuitBreakerPrimaryProviderKey).(string); prov != "" {
		return
	}
	headers := collectProviderResponseHeaders(ctx, result, err)
	if len(headers) == 0 {
		return
	}
	if name, tripped := circuitbreaker.Default.EvaluateTrip(provider, model, headers); tripped {
		if p.logger != nil {
			p.logger.Info("[Governance] Circuit breaker tripped policy=%s provider=%s model=%s", name, provider, model)
		}
		ctx.AppendRoutingEngineLog(schemas.RoutingEngineCircuitBreaker, schemas.LogLevelWarn,
			"Tripped policy "+name+" — routing to fallback until cooldown expires")
	}
}

func collectProviderResponseHeaders(ctx *schemas.UnifAIContext, result *schemas.UnifAIResponse, err *schemas.UnifAIError) map[string]string {
	if result != nil {
		if extra := result.GetExtraFields(); extra != nil && extra.ProviderResponseHeaders != nil {
			return extra.ProviderResponseHeaders
		}
	}
	if raw, ok := ctx.Value(schemas.UnifAIContextKeyProviderResponseHeaders).(map[string]string); ok && len(raw) > 0 {
		return raw
	}
	return nil
}

// circuitBreakerPoliciesActive is a cheap check used by PreRequestHook gating.
func circuitBreakerPoliciesActive() bool {
	return circuitbreaker.Default.HasPolicies()
}
