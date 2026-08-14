package handlers

import (
	"errors"
	"net"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	configstoreTables "github.com/unifai/unifai/framework/configstore/tables"
	"github.com/unifai/unifai/framework/kvstore"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

type testWSHandlerStore struct {
	matcher *lib.HeaderMatcher
}

func (s testWSHandlerStore) GetHeaderMatcher() *lib.HeaderMatcher {
	return s.matcher
}

func (s testWSHandlerStore) GetStreamChunkInterceptor() lib.StreamChunkInterceptor {
	return nil
}

func (s testWSHandlerStore) GetAsyncJobExecutor() *logstore.AsyncJobExecutor {
	return nil
}

func (s testWSHandlerStore) GetAsyncJobResultTTL() int {
	return 0
}

func (s testWSHandlerStore) GetKVStore() *kvstore.Store {
	return nil
}

func (s testWSHandlerStore) GetMCPHeaderCombinedAllowlist() schemas.WhiteList {
	return nil
}

func (s testWSHandlerStore) ShouldAllowPerRequestStorageOverride() bool { return false }
func (s testWSHandlerStore) ShouldAllowPerRequestRawOverride() bool     { return false }
func (s testWSHandlerStore) ShouldAllowDirectKeys() bool                { return false }
func (s testWSHandlerStore) GetMCPExternalServerURL() string            { return "" }
func (s testWSHandlerStore) GetMCPExternalClientURL() string            { return "" }

type timeoutNetError struct{}

func (timeoutNetError) Error() string   { return "i/o timeout" }
func (timeoutNetError) Timeout() bool   { return true }
func (timeoutNetError) Temporary() bool { return false }

func TestResolveWSStreamIdleTimeoutUsesProviderOverride(t *testing.T) {
	cfg := &lib.Config{
		Providers: map[schemas.ModelProvider]configstore.ProviderConfig{
			schemas.OpenAI: {
				NetworkConfig: &schemas.NetworkConfig{StreamIdleTimeoutInSeconds: 7},
			},
		},
	}

	timeout := resolveWSStreamIdleTimeout(cfg, schemas.OpenAI)
	assert.Equal(t, 7*time.Second, timeout)
}

func TestResolveWSStreamIdleTimeoutFallsBackToDefault(t *testing.T) {
	timeout := resolveWSStreamIdleTimeout(&lib.Config{}, schemas.OpenAI)
	assert.Equal(t, time.Duration(schemas.DefaultStreamIdleTimeoutInSeconds)*time.Second, timeout)
}

func TestIsWSReadTimeout(t *testing.T) {
	assert.True(t, isWSReadTimeout(timeoutNetError{}))
	assert.False(t, isWSReadTimeout(net.UnknownNetworkError("unknown")))
	assert.False(t, isWSReadTimeout(errors.New("boom")))
	assert.False(t, isWSReadTimeout(nil))
}

func TestNewUnifAIError(t *testing.T) {
	unifaiErr := newUnifAIError(504, "upstream_timeout", "upstream websocket stream timed out")
	if unifaiErr == nil {
		t.Fatal("expected unifai error, got nil")
	}
	if unifaiErr.StatusCode == nil || *unifaiErr.StatusCode != 504 {
		t.Fatalf("status code = %#v, want 504", unifaiErr.StatusCode)
	}
	if unifaiErr.Error == nil {
		t.Fatal("expected error field, got nil")
	}
	if unifaiErr.Error.Type == nil || *unifaiErr.Error.Type != "upstream_timeout" {
		t.Fatalf("error type = %#v, want upstream_timeout", unifaiErr.Error.Type)
	}
	if unifaiErr.Error.Message != "upstream websocket stream timed out" {
		t.Fatalf("error message = %q, want upstream websocket stream timed out", unifaiErr.Error.Message)
	}
}

func TestCreateUnifAIContextFromAuth_BaggageSessionIDSetsGrouping(t *testing.T) {
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{}, &authHeaders{
		baggage: "foo=bar, session-id=rt-ws-123, baz=qux",
	})
	defer cancel()

	if got, _ := ctx.Value(schemas.UnifAIContextKeyParentRequestID).(string); got != "rt-ws-123" {
		t.Fatalf("parent request id = %q, want %q", got, "rt-ws-123")
	}
}

func TestCreateUnifAIContextFromAuth_EmptyBaggageSessionIDIgnored(t *testing.T) {
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{}, &authHeaders{
		baggage: "session-id=   ",
	})
	defer cancel()

	if got := ctx.Value(schemas.UnifAIContextKeyParentRequestID); got != nil {
		t.Fatalf("parent request id should be unset, got %#v", got)
	}
}

func TestCreateUnifAIContextFromAuth_ForwardsPrefixedHeaders(t *testing.T) {
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{}, &authHeaders{
		headers: map[string][]string{
			"x-uf-eh-originator": {"my-test-client"},
			"x-uf-eh-x-trace-id": {"abc-123"},
			"x-uf-eh-cookie":     {"blocked"},
		},
	})
	defer cancel()

	extraHeaders, ok := ctx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)
	if !ok {
		t.Fatal("expected websocket extra headers in context")
	}
	assert.Equal(t, []string{"my-test-client"}, extraHeaders["originator"])
	assert.Equal(t, []string{"abc-123"}, extraHeaders["x-trace-id"])
	assert.NotContains(t, extraHeaders, "cookie")
}

func TestCreateUnifAIContextFromAuth_AppliesHeaderFilterAndDirectAllowlist(t *testing.T) {
	matcher := lib.NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"originator", "anthropic-*"},
		Denylist:  []string{"anthropic-secret"},
	})
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{matcher: matcher}, &authHeaders{
		headers: map[string][]string{
			"x-uf-eh-originator":       {"allowed-prefix"},
			"x-uf-eh-x-trace-id":       {"blocked-by-allowlist"},
			"anthropic-beta":           {"allowed-direct"},
			"anthropic-secret":         {"blocked-by-denylist"},
			"x-uf-eh-anthropic-secret": {"blocked-prefix-denylist"},
		},
	})
	defer cancel()

	extraHeaders, ok := ctx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)
	if !ok {
		t.Fatal("expected websocket extra headers in context")
	}
	assert.Equal(t, []string{"allowed-prefix"}, extraHeaders["originator"])
	assert.Equal(t, []string{"allowed-direct"}, extraHeaders["anthropic-beta"])
	assert.NotContains(t, extraHeaders, "x-trace-id")
	assert.NotContains(t, extraHeaders, "anthropic-secret")
}

func TestCaptureAuthHeaders_PreservesDuplicateHeaderValues(t *testing.T) {
	var req fasthttp.Request
	req.Header.Set("Host", "example.test")
	req.Header.Add("x-uf-eh-x-trace-id", "trace-a")
	req.Header.Add("x-uf-eh-x-trace-id", "trace-b")

	ctx := &fasthttp.RequestCtx{}
	ctx.Init(&req, &net.TCPAddr{IP: net.IPv4(127, 0, 0, 1), Port: 12345}, nil)

	auth := captureAuthHeaders(ctx)
	assert.Equal(t, []string{"trace-a", "trace-b"}, auth.headers["x-uf-eh-x-trace-id"])
}

func TestCreateUnifAIContextFromAuth_PreservesMultipleForwardedHeaderValues(t *testing.T) {
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{}, &authHeaders{
		headers: map[string][]string{
			"x-uf-eh-x-trace-id": {"trace-a", "trace-b"},
		},
	})
	defer cancel()

	extraHeaders, ok := ctx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)
	if !ok {
		t.Fatal("expected websocket extra headers in context")
	}
	assert.Equal(t, []string{"trace-a", "trace-b"}, extraHeaders["x-trace-id"])
}

func TestCreateUnifAIContextFromAuth_BlocksWebSocketHandshakeForwardedHeaders(t *testing.T) {
	matcher := lib.NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"*"},
	})
	ctx, cancel := createUnifAIContextFromAuth(testWSHandlerStore{matcher: matcher}, &authHeaders{
		headers: map[string][]string{
			"x-uf-eh-upgrade":                {"websocket"},
			"x-uf-eh-sec-websocket-protocol": {"realtime"},
			"sec-websocket-extensions":       {"permessage-deflate"},
			"x-uf-eh-originator":             {"safe"},
		},
	})
	defer cancel()

	extraHeaders, ok := ctx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)
	if !ok {
		t.Fatal("expected websocket extra headers in context")
	}
	assert.Equal(t, []string{"safe"}, extraHeaders["originator"])
	assert.NotContains(t, extraHeaders, "upgrade")
	assert.NotContains(t, extraHeaders, "sec-websocket-protocol")
	assert.NotContains(t, extraHeaders, "sec-websocket-extensions")
}

func TestMergeWebSocketHeaders_ForwardedHeadersOverrideProviderHeadersAndPreserveValues(t *testing.T) {
	ctx := schemas.NewUnifAIContext(nil, time.Time{})
	ctx.SetValue(schemas.UnifAIContextKeyExtraHeaders, map[string][]string{
		"originator":    {"my-test-client"},
		"authorization": {"Bearer malicious"},
		"x-static":      {"client-value-1", "client-value-2"},
	})

	merged := mergeWebSocketHeaders(ctx, map[string]string{
		"Authorization": "Bearer provider-key",
		"x-static":      "provider-value",
	})

	assert.Equal(t, []string{"my-test-client"}, merged.Values("originator"))
	assert.Equal(t, []string{"Bearer provider-key"}, merged.Values("Authorization"))
	assert.Equal(t, []string{"client-value-1", "client-value-2"}, merged.Values("x-static"))
	assert.NotContains(t, merged.Values("Authorization"), "Bearer malicious")
}

func TestHasWebSocketForwardedHeaders(t *testing.T) {
	ctx := schemas.NewUnifAIContext(nil, time.Time{})
	assert.False(t, hasWebSocketForwardedHeaders(ctx))

	ctx.SetValue(schemas.UnifAIContextKeyExtraHeaders, map[string][]string{
		"authorization": {"Bearer malicious"},
	})
	assert.False(t, hasWebSocketForwardedHeaders(ctx))

	ctx.SetValue(schemas.UnifAIContextKeyExtraHeaders, map[string][]string{
		"x-trace-id": {"abc-123"},
	})
	assert.True(t, hasWebSocketForwardedHeaders(ctx))
}
