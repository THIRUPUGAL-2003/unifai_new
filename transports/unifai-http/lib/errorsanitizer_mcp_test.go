package lib

import (
	"errors"
	"strings"
	"testing"
)

func TestClientSafeMCPConnectMessageStripsHTML429(t *testing.T) {
	raw := errors.New(`request failed with status 429: <!DOCTYPE html><html><head></head><body>cloudflare 429_title</body></html>`)
	got := ClientSafeMCPConnectMessage("Failed to connect MCP client", raw)
	if strings.Contains(strings.ToLower(got), "<html") || strings.Contains(got, "DOCTYPE") {
		t.Fatalf("HTML leaked: %q", got)
	}
	if !strings.Contains(got, "429") {
		t.Fatalf("expected 429 in %q", got)
	}
}

func TestClientSafeMCPConnectMessageAuthStatus(t *testing.T) {
	raw := errors.New(`request failed with status 401: {"error":"unauthorized"}`)
	got := ClientSafeMCPConnectMessage("", raw)
	if !strings.Contains(got, "401") {
		t.Fatalf("expected 401 in %q", got)
	}
	if !strings.Contains(strings.ToLower(got), "headers") && !strings.Contains(strings.ToLower(got), "oauth") {
		t.Fatalf("expected auth guidance in %q", got)
	}
}
