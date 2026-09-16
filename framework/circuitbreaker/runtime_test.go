package circuitbreaker

import (
	"testing"
	"time"

	"github.com/unifai/unifai/core/schemas"
	configstoreTables "github.com/unifai/unifai/framework/configstore/tables"
)

func TestApplyFailoverWhenOpen(t *testing.T) {
	r := &Runtime{}
	r.LoadPolicies([]configstoreTables.TableCircuitBreakerPolicy{{
		Name: "p1", Enabled: true,
		PrimaryProvider: "openai", PrimaryModel: "gpt-4o",
		FallbackProvider: "anthropic", FallbackModel: "claude-3-5-sonnet",
		DefaultCooldown: "1m",
		ParsedCondition: map[string]any{
			"operator": "OR",
			"signals": []map[string]any{{"header_name": "x-degraded", "source": "response_header"}},
		},
	}})
	r.trip("p1", time.Minute, time.Now())

	dec, ok := r.ApplyFailover(schemas.ModelProvider("openai"), "gpt-4o")
	if !ok || dec == nil {
		t.Fatal("expected failover")
	}
	if dec.ToProv != "anthropic" || dec.ToModel != "claude-3-5-sonnet" {
		t.Fatalf("unexpected failover target: %+v", dec)
	}
}

func TestEvaluateTripOnHeader(t *testing.T) {
	r := &Runtime{}
	r.LoadPolicies([]configstoreTables.TableCircuitBreakerPolicy{{
		Name: "p1", Enabled: true,
		PrimaryProvider: "openai", PrimaryModel: "gpt-4o",
		FallbackProvider: "anthropic", FallbackModel: "claude-3-5-sonnet",
		DefaultCooldown: "45s",
		ParsedCondition: map[string]any{
			"operator": "OR",
			"signals": []map[string]any{{"header_name": "x-degraded", "header_value": "true", "source": "response_header"}},
		},
	}})

	name, tripped := r.EvaluateTrip(schemas.ModelProvider("openai"), "gpt-4o", map[string]string{"X-Degraded": "true"})
	if !tripped || name != "p1" {
		t.Fatalf("expected trip, got tripped=%v name=%q", tripped, name)
	}
	states := r.ListStates()
	if states["p1"].Status != "open" {
		t.Fatalf("expected open circuit, got %+v", states["p1"])
	}
}

func TestEvaluateTripMistralHeaderAlias(t *testing.T) {
	r := &Runtime{}
	r.LoadPolicies([]configstoreTables.TableCircuitBreakerPolicy{{
		Name: "mistral-cb", Enabled: true,
		PrimaryProvider: "mistral", PrimaryModel: "codestral-2508",
		FallbackProvider: "openrouter", FallbackModel: "openai/gpt-4o-mini",
		DefaultCooldown: "30s",
		ParsedCondition: map[string]any{
			"operator": "OR",
			// Policy uses OpenAI-style name; provider returns Mistral/Kong minute header.
			"signals": []map[string]any{{
				"header_name":  "x-ratelimit-remaining-requests",
				"header_value": "0",
				"source":       "response_header",
			}},
		},
	}})

	name, tripped := r.EvaluateTrip(
		schemas.ModelProvider("mistral"),
		"codestral-2508",
		map[string]string{"X-Ratelimit-Remaining-Req-Minute": "0"},
	)
	if !tripped || name != "mistral-cb" {
		t.Fatalf("expected alias trip, got tripped=%v name=%q", tripped, name)
	}
}
