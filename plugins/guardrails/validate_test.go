package guardrails

import "testing"

func TestValidateConfigRequiresLinkedProviders(t *testing.T) {
	cfg := &Config{
		GuardrailProviders: []GuardrailProvider{
			{
				ID:           1,
				ProviderName: "regex",
				PolicyName:   "pii",
				Enabled:      true,
				Config: map[string]interface{}{
					"patterns": []interface{}{map[string]interface{}{"pattern": "secret", "flags": "i"}},
				},
			},
		},
		GuardrailRules: []GuardrailRule{
			{
				ID:            10,
				Name:          "block secrets",
				Enabled:       true,
				CELExpression: "true",
				ApplyTo:       "input",
			},
		},
	}

	if err := ValidateConfig(cfg); err == nil {
		t.Fatal("expected error when enabled rule has no linked providers")
	}

	cfg.GuardrailRules[0].ProviderConfigIDs = []int{1}
	if err := ValidateConfig(cfg); err != nil {
		t.Fatalf("expected valid config, got %v", err)
	}
}
