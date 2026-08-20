package handlers

import "testing"

func TestParseAIBotViolation(t *testing.T) {
	tests := []struct {
		raw  string
		want bool
	}{
		{`{"violation":true,"reason":"name"}`, true},
		{`{"violation":false,"reason":"safe"}`, false},
		{`{"violation":false,"reason":"safe"} extra {"violation":true,"reason":"policy"}`, true},
		{`not json but "violation": false then later "violation": true`, true},
		{`{"violation":true}`, true},
		{`YES`, true},
		{`true`, true},
		{`{"violation":false}`, false},
		{`hello`, false},
	}
	for _, tt := range tests {
		if got := parseAIBotViolation(tt.raw); got != tt.want {
			t.Fatalf("parseAIBotViolation(%q)=%v want %v", tt.raw, got, tt.want)
		}
	}
}

func TestParseAIBotDecisionUnrecognized(t *testing.T) {
	if _, ok := parseAIBotDecision("hello"); ok {
		t.Fatal("expected unrecognized garbage")
	}
	if v, ok := parseAIBotDecision(`{"violation":false}`); !ok || v {
		t.Fatalf("false json: v=%v ok=%v", v, ok)
	}
	if v, ok := parseAIBotDecision(`{"violation":true}`); !ok || !v {
		t.Fatalf("true json: v=%v ok=%v", v, ok)
	}
}

func TestResolveGuardBotModel(t *testing.T) {
	p, m := resolveGuardBotModel("openrouter", "cohere/north-mini-code:free")
	if string(p) != "openrouter" || m != "cohere/north-mini-code:free" {
		t.Fatalf("got %s %s", p, m)
	}
	p, m = resolveGuardBotModel("openai", "gpt-4o-mini")
	if string(p) != "openai" || m != "gpt-4o-mini" {
		t.Fatalf("openai got %s %s", p, m)
	}
	p, m = resolveGuardBotModel("openai", "openai/gpt-4o-mini")
	if string(p) != "openai" || m != "gpt-4o-mini" {
		t.Fatalf("prefixed openai got %s %s", p, m)
	}
}
