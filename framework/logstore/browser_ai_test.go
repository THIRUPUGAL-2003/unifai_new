package logstore

import (
	"strings"
	"testing"
)

func TestBuildProxyPACOnlyUsesAddedHosts(t *testing.T) {
	pac, err := (&BrowserAIManager{}).BuildProxyPAC(t.Context(), "127.0.0.1:8085")
	if err != nil {
		t.Fatal(err)
	}
	if pac == "" {
		t.Fatal("expected PAC script")
	}
	if !strings.Contains(pac, "FindProxyForURL") || !strings.Contains(pac, "DIRECT") {
		t.Fatalf("expected a valid PAC, got %q", pac)
	}
}

func TestBuildProxyPACNeverErrorsOnBadProxyAddr(t *testing.T) {
	pac, err := (&BrowserAIManager{}).BuildProxyPAC(t.Context(), "http://evil.example/x\"; DROP")
	if err != nil {
		t.Fatal(err)
	}
	if pac == "" {
		t.Fatal("expected PAC even with a bad proxy addr")
	}
	if strings.Contains(pac, "DROP") || strings.Contains(pac, "evil.example") {
		t.Fatalf("unsafe proxy addr leaked into PAC: %q", pac)
	}
}

func TestSanitizeProxyAddr(t *testing.T) {
	if got := sanitizeProxyAddr(""); got != "127.0.0.1:8085" {
		t.Fatalf("empty: %s", got)
	}
	if got := sanitizeProxyAddr("127.0.0.1:8085"); got != "127.0.0.1:8085" {
		t.Fatalf("valid: %s", got)
	}
	if got := sanitizeProxyAddr("bad\"addr"); got != "127.0.0.1:8085" {
		t.Fatalf("unsafe: %s", got)
	}
}
