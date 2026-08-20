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
		{`hello`, false},
	}
	for _, tt := range tests {
		if got := parseAIBotViolation(tt.raw); got != tt.want {
			t.Fatalf("parseAIBotViolation(%q)=%v want %v", tt.raw, got, tt.want)
		}
	}
}
