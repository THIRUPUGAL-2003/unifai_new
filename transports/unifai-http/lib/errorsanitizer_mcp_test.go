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

func TestClientSafeMCPConnectMessageUnwrapsNestedTimeout(t *testing.T) {
	raw := errors.New("failed to connect MCP client: failed to connect MCP client Weather_2: failed to connect MCP client Weather_2: failed to start MCP client transport after 5 retries: timeout waiting for endpoint")
	got := ClientSafeMCPConnectMessage("Failed to connect MCP client", raw)
	if strings.Count(strings.ToLower(got), "failed to connect") > 1 {
		t.Fatalf("still nested: %q", got)
	}
	if !strings.Contains(got, "Weather_2") {
		t.Fatalf("expected client name in %q", got)
	}
	if !strings.Contains(strings.ToLower(got), "timed out") && !strings.Contains(strings.ToLower(got), "timeout") {
		t.Fatalf("expected timeout guidance in %q", got)
	}
	if strings.Contains(got, "after 5 retries") {
		t.Fatalf("should not expose misleading retry noise: %q", got)
	}
}
