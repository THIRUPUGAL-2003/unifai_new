package lib

import (
	"context"
	"testing"

	configstoreTables "github.com/unifai/unifai/framework/configstore/tables"
	"github.com/unifai/unifai/framework/kvstore"
	"github.com/unifai/unifai/framework/logstore"

	"github.com/unifai/unifai/core/schemas"
	"github.com/valyala/fasthttp"
)

// testHandlerStore is a minimal HandlerStore for ctx tests.
type testHandlerStore struct {
	matcher         *HeaderMatcher
	allowDirectKeys bool
}

func (s testHandlerStore) GetHeaderMatcher() *HeaderMatcher                      { return s.matcher }
func (s testHandlerStore) GetProvidersForModel(_ string) []schemas.ModelProvider { return nil }
func (s testHandlerStore) GetStreamChunkInterceptor() StreamChunkInterceptor     { return nil }
func (s testHandlerStore) GetAsyncJobExecutor() *logstore.AsyncJobExecutor       { return nil }
func (s testHandlerStore) GetAsyncJobResultTTL() int                             { return 0 }
func (s testHandlerStore) GetKVStore() *kvstore.Store                            { return nil }
func (s testHandlerStore) GetMCPHeaderCombinedAllowlist() schemas.WhiteList {
	return schemas.WhiteList{}
}
func (s testHandlerStore) ShouldAllowPerRequestStorageOverride() bool { return false }
func (s testHandlerStore) ShouldAllowPerRequestRawOverride() bool     { return false }
func (s testHandlerStore) ShouldAllowDirectKeys() bool                { return s.allowDirectKeys }
func (s testHandlerStore) GetMCPExternalServerURL() string            { return "" }
func (s testHandlerStore) GetMCPExternalClientURL() string            { return "" }

func TestParseSessionIDFromBaggage(t *testing.T) {
	tests := []struct {
		name   string
		header string
		want   string
	}{
		{name: "single member", header: "session-id=abc", want: "abc"},
		{name: "multiple members", header: "foo=bar, session-id=abc, baz=qux", want: "abc"},
		{name: "member with properties", header: "session-id=abc;ttl=60", want: "abc"},
		{name: "spaces preserved around parsing", header: " foo=bar , session-id = abc123 ;ttl=60 ", want: "abc123"},
		{name: "missing member", header: "foo=bar", want: ""},
		{name: "malformed ignored", header: "session-id, foo=bar", want: ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := ParseSessionIDFromBaggage(tt.header); got != tt.want {
				t.Fatalf("ParseSessionIDFromBaggage(%q) = %q, want %q", tt.header, got, tt.want)
			}
		})
	}
}

func TestConvertToUnifAIContext_ReusesSharedContext(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	base := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	base.SetValue(schemas.UnifAIContextKeyRequestID, "req-shared")
	ctx.SetUserValue(FastHTTPUserValueUnifAIContext, base)

	converted, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	if converted == nil {
		t.Fatal("expected non-nil converted context")
	}
	if got, _ := converted.Value(schemas.UnifAIContextKeyRequestID).(string); got != "req-shared" {
		t.Fatalf("expected converted context to preserve parent values, got request-id=%q", got)
	}
	if stored, ok := ctx.UserValue(FastHTTPUserValueUnifAIContext).(*schemas.UnifAIContext); !ok || stored == nil {
		t.Fatal("expected shared context pointer to be stored on fasthttp user values")
	}
	if ctx.UserValue(FastHTTPUserValueUnifAICancel) == nil {
		t.Fatal("expected shared cancel function to be stored on fasthttp user values")
	}
}

func TestConvertToUnifAIContext_SecondCallReturnsSameSharedContext(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}

	first, cancelFirst := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancelFirst()
	if first == nil {
		t.Fatal("expected first context to be non-nil")
	}

	second, cancelSecond := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancelSecond()
	if second == nil {
		t.Fatal("expected second context to be non-nil")
	}
	if first != second {
		t.Fatal("expected ConvertToUnifAIContext to reuse the shared context on repeated calls")
	}
}

// TestConvertToUnifAIContext_StarAllowlistSecurityHeadersBlocked verifies that
// even with a "*" allowlist (allow all), the hardcoded security denylist in
// ConvertToUnifAIContext still blocks security-sensitive headers.
func TestConvertToUnifAIContext_StarAllowlistSecurityHeadersBlocked(t *testing.T) {
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"*"},
	})

	ctx := &fasthttp.RequestCtx{}
	// x-uf-eh-* prefixed headers
	ctx.Request.Header.Set("x-uf-eh-custom-header", "allowed-value")
	ctx.Request.Header.Set("x-uf-eh-cookie", "should-be-blocked")
	ctx.Request.Header.Set("x-uf-eh-x-api-key", "should-be-blocked")
	ctx.Request.Header.Set("x-uf-eh-host", "should-be-blocked")
	ctx.Request.Header.Set("x-uf-eh-connection", "should-be-blocked")
	ctx.Request.Header.Set("x-uf-eh-proxy-authorization", "should-be-blocked")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	// custom-header should be forwarded
	if _, ok := extraHeaders["custom-header"]; !ok {
		t.Error("expected custom-header to be forwarded via x-uf-eh- prefix")
	}

	// Security headers should be blocked even with * allowlist
	securityHeaders := []string{"cookie", "x-api-key", "host", "connection", "proxy-authorization"}
	for _, h := range securityHeaders {
		if _, ok := extraHeaders[h]; ok {
			t.Errorf("expected security header %q to be blocked even with * allowlist", h)
		}
	}
}

// TestConvertToUnifAIContext_StarAllowlistDirectForwardingSecurityBlocked verifies
// that direct header forwarding with "*" allowlist forwards non-security headers
// but still blocks security headers.
func TestConvertToUnifAIContext_StarAllowlistDirectForwardingSecurityBlocked(t *testing.T) {
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"*"},
	})

	ctx := &fasthttp.RequestCtx{}
	// Direct headers (not prefixed with x-uf-eh-)
	ctx.Request.Header.Set("custom-header", "allowed-value")
	ctx.Request.Header.Set("anthropic-beta", "some-beta-feature")
	// Security headers sent directly — should be blocked
	ctx.Request.Header.Set("proxy-authorization", "should-be-blocked")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	// Direct non-security headers should be forwarded when allowlist has *
	if _, ok := extraHeaders["custom-header"]; !ok {
		t.Error("expected custom-header to be forwarded directly")
	}
	if _, ok := extraHeaders["anthropic-beta"]; !ok {
		t.Error("expected anthropic-beta to be forwarded directly")
	}

	// Security headers should still be blocked in direct forwarding path
	directSecurityHeaders := []string{"proxy-authorization", "cookie", "host", "connection"}
	for _, h := range directSecurityHeaders {
		if _, ok := extraHeaders[h]; ok {
			t.Errorf("expected security header %q to be blocked in direct forwarding even with * allowlist", h)
		}
	}
}

// TestConvertToUnifAIContext_PrefixWildcardDirectForwarding verifies that
// prefix wildcard patterns like "anthropic-*" work for direct header forwarding
// (without x-uf-eh- prefix).
func TestConvertToUnifAIContext_PrefixWildcardDirectForwarding(t *testing.T) {
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"anthropic-*"},
	})

	ctx := &fasthttp.RequestCtx{}
	// Direct headers matching the wildcard pattern
	ctx.Request.Header.Set("anthropic-beta", "beta-value")
	ctx.Request.Header.Set("anthropic-version", "2024-01-01")
	// Header not matching the pattern
	ctx.Request.Header.Set("openai-version", "should-not-forward")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	if _, ok := extraHeaders["anthropic-beta"]; !ok {
		t.Error("expected anthropic-beta to be forwarded directly via wildcard allowlist")
	}
	if _, ok := extraHeaders["anthropic-version"]; !ok {
		t.Error("expected anthropic-version to be forwarded directly via wildcard allowlist")
	}
	if _, ok := extraHeaders["openai-version"]; ok {
		t.Error("expected openai-version to NOT be forwarded (doesn't match anthropic-*)")
	}
}

// TestConvertToUnifAIContext_WildcardAllowlistFiltering verifies wildcard patterns
// correctly filter headers via the x-uf-eh- prefix path.
func TestConvertToUnifAIContext_WildcardAllowlistFiltering(t *testing.T) {
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"anthropic-*"},
	})

	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-eh-anthropic-beta", "beta-value")
	ctx.Request.Header.Set("x-uf-eh-anthropic-version", "2024-01-01")
	ctx.Request.Header.Set("x-uf-eh-openai-version", "should-be-blocked")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	if _, ok := extraHeaders["anthropic-beta"]; !ok {
		t.Error("expected anthropic-beta to be forwarded")
	}
	if _, ok := extraHeaders["anthropic-version"]; !ok {
		t.Error("expected anthropic-version to be forwarded")
	}
	if _, ok := extraHeaders["openai-version"]; ok {
		t.Error("expected openai-version to be blocked (not matching anthropic-*)")
	}
}

// TestConvertToUnifAIContext_WildcardDenylistBlocking verifies wildcard denylist
// patterns block matching headers.
func TestConvertToUnifAIContext_WildcardDenylistBlocking(t *testing.T) {
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Denylist: []string{"x-internal-*"},
	})

	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-eh-x-internal-id", "blocked-value")
	ctx.Request.Header.Set("x-uf-eh-x-internal-secret", "blocked-value")
	ctx.Request.Header.Set("x-uf-eh-custom-header", "allowed-value")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	if _, ok := extraHeaders["x-internal-id"]; ok {
		t.Error("expected x-internal-id to be blocked by denylist")
	}
	if _, ok := extraHeaders["x-internal-secret"]; ok {
		t.Error("expected x-internal-secret to be blocked by denylist")
	}
	if _, ok := extraHeaders["custom-header"]; !ok {
		t.Error("expected custom-header to be forwarded")
	}
}

// TestConvertToUnifAIContext_NilMatcher verifies nil matcher allows all headers.
func TestConvertToUnifAIContext_NilMatcher(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-eh-custom-header", "allowed-value")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)

	if _, ok := extraHeaders["custom-header"]; !ok {
		t.Error("expected custom-header to be forwarded with nil matcher")
	}
}

func TestConvertToUnifAIContext_BaggageSessionIDSetsGrouping(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("baggage", "foo=bar, session-id=rt-123, baz=qux")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	if got, _ := unifaiCtx.Value(schemas.UnifAIContextKeyParentRequestID).(string); got != "rt-123" {
		t.Fatalf("parent request id = %q, want %q", got, "rt-123")
	}
}

func TestConvertToUnifAIContext_EmptyBaggageSessionIDIgnored(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("baggage", "session-id=   ")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	if got := unifaiCtx.Value(schemas.UnifAIContextKeyParentRequestID); got != nil {
		t.Fatalf("parent request id should be unset, got %#v", got)
	}
}

func TestConvertToUnifAIContext_DimHeadersDoNotOverrideReservedContextKeys(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-request-id", "trusted-request-id")
	ctx.Request.Header.Set("x-uf-dim-request-id", "attacker-request-id")
	ctx.Request.Header.Set("x-uf-dim-x-uf-vk", "attacker-vk")
	ctx.Request.Header.Set("x-uf-prom-x-uf-vk", "attacker-vk")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	// request-id must remain from trusted source, not from x-uf-dim-request-id.
	if got, _ := unifaiCtx.Value(schemas.UnifAIContextKeyRequestID).(string); got != "trusted-request-id" {
		t.Fatalf("request-id = %q, want %q", got, "trusted-request-id")
	}
	// Virtual key must not be set through x-uf-dim-x-uf-vk.
	if got := unifaiCtx.Value(schemas.UnifAIContextKeyVirtualKey); got != nil {
		t.Fatalf("virtual key should not be set via x-uf-dim-*, got %#v", got)
	}

	// Dimension values are still captured in the dedicated dimensions map.
	dimensions, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDimensions).(map[string]string)
	if !ok {
		t.Fatal("expected dimensions map in context")
	}
	if dimensions["request-id"] != "attacker-request-id" {
		t.Fatalf("dimensions[request-id] = %q, want %q", dimensions["request-id"], "attacker-request-id")
	}
	if dimensions["x-uf-vk"] != "attacker-vk" {
		t.Fatalf("dimensions[x-uf-vk] = %q, want %q", dimensions["x-uf-vk"], "attacker-vk")
	}
}

func TestConvertToUnifAIContext_PromHeadersDoNotOverrideReservedContextKeys(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-request-id", "trusted-request-id")
	ctx.Request.Header.Set("x-uf-prom-request-id", "attacker-request-id")
	ctx.Request.Header.Set("x-uf-prom-x-uf-vk", "attacker-vk")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	// request-id must remain from trusted source, not from x-uf-prom-request-id.
	if got, _ := unifaiCtx.Value(schemas.UnifAIContextKeyRequestID).(string); got != "trusted-request-id" {
		t.Fatalf("request-id = %q, want %q", got, "trusted-request-id")
	}
	// Virtual key must not be set through x-uf-prom-x-uf-vk.
	if got := unifaiCtx.Value(schemas.UnifAIContextKeyVirtualKey); got != nil {
		t.Fatalf("virtual key should not be set via x-uf-prom-*, got %#v", got)
	}
	// Legacy x-uf-prom-* headers are not mirrored into global context keyspace.
	if got := unifaiCtx.Value(schemas.UnifAIContextKey("request-id")); got != "trusted-request-id" {
		t.Fatalf("global request-id key should remain trusted value, got %#v", got)
	}

	// Legacy x-uf-prom-* must not be included in unified dimensions.
	if dimensions, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDimensions).(map[string]string); ok && len(dimensions) > 0 {
		t.Fatalf("expected no unified dimensions from x-uf-prom-*, got %#v", dimensions)
	}
}

func TestConvertToUnifAIContext_DimAndPromCanCoexistWithoutCrossing(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-prom-team", "legacy-team")
	ctx.Request.Header.Set("x-uf-dim-team", "platform")
	ctx.Request.Header.Set("x-uf-dim-environment", "prod")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{})
	defer cancel()

	dimensions, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDimensions).(map[string]string)
	if !ok {
		t.Fatal("expected dimensions map in context")
	}
	if dimensions["team"] != "platform" {
		t.Fatalf("dimensions[team] = %q, want %q", dimensions["team"], "platform")
	}
	if dimensions["environment"] != "prod" {
		t.Fatalf("dimensions[environment] = %q, want %q", dimensions["environment"], "prod")
	}
	if len(dimensions) != 2 {
		t.Fatalf("expected only dim headers in unified dimensions, got %#v", dimensions)
	}
}

func TestConvertToUnifAIContext_DirectKey_ServerDisabled(t *testing.T) {
	// x-uf-direct-key: true present but server setting is off — no direct key should be set.
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "Bearer sk-real-openai-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: false})
	defer cancel()

	if _, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key); ok {
		t.Error("expected no direct key when server setting is disabled")
	}
}

func TestConvertToUnifAIContext_DirectKey_HeaderAbsent(t *testing.T) {
	// Server allows direct keys but caller did not send x-uf-direct-key header.
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("Authorization", "Bearer sk-real-openai-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	if _, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key); ok {
		t.Error("expected no direct key when x-uf-direct-key header is absent")
	}
}

func TestConvertToUnifAIContext_DirectKey_BearerRealKey(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "Bearer sk-real-openai-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	key, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key)
	if !ok {
		t.Fatal("expected direct key to be set")
	}
	if key.Value.GetValue() != "sk-real-openai-key" {
		t.Errorf("direct key value = %q, want %q", key.Value.GetValue(), "sk-real-openai-key")
	}
	if key.ID != "header-provided" {
		t.Errorf("direct key ID = %q, want %q", key.ID, "header-provided")
	}
}

func TestConvertToUnifAIContext_DirectKey_VirtualKeyNotBypassed(t *testing.T) {
	// A virtual key (sk-uf-*) in Authorization must not be treated as a direct key.
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "Bearer sk-uf-virtual-key-here")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	if _, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key); ok {
		t.Error("expected virtual key not to be treated as a direct key")
	}
	// The virtual key should still be set normally.
	if vk, ok := unifaiCtx.Value(schemas.UnifAIContextKeyVirtualKey).(string); !ok || vk == "" {
		t.Error("expected virtual key to be set in context")
	}
}

func TestConvertToUnifAIContext_DirectKey_XAPIKey(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("x-api-key", "sk-ant-real-anthropic-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	key, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key)
	if !ok {
		t.Fatal("expected direct key to be set from x-api-key")
	}
	if key.Value.GetValue() != "sk-ant-real-anthropic-key" {
		t.Errorf("direct key value = %q, want %q", key.Value.GetValue(), "sk-ant-real-anthropic-key")
	}
}

func TestConvertToUnifAIContext_DirectKey_XGoogAPIKey(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("x-goog-api-key", "AIza-real-gemini-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	key, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key)
	if !ok {
		t.Fatal("expected direct key to be set from x-goog-api-key")
	}
	if key.Value.GetValue() != "AIza-real-gemini-key" {
		t.Errorf("direct key value = %q, want %q", key.Value.GetValue(), "AIza-real-gemini-key")
	}
}

func TestConvertToUnifAIContext_DirectKey_CannotBeSpoofedViaEHPrefix(t *testing.T) {
	// x-uf-eh-x-uf-direct-key must be blocked by the security denylist.
	matcher := NewHeaderMatcher(&configstoreTables.GlobalHeaderFilterConfig{
		Allowlist: []string{"*"},
	})
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-eh-x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "Bearer sk-real-openai-key")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{matcher: matcher, allowDirectKeys: true})
	defer cancel()

	if _, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key); ok {
		t.Error("expected x-uf-direct-key to be blocked when injected via x-uf-eh- prefix")
	}
	extraHeaders, _ := unifaiCtx.Value(schemas.UnifAIContextKeyExtraHeaders).(map[string][]string)
	if _, ok := extraHeaders["x-uf-direct-key"]; ok {
		t.Error("expected x-uf-direct-key to be absent from extra headers (denylist)")
	}
}

func TestConvertToUnifAIContext_DirectKey_RawVirtualKeyNotBypassed(t *testing.T) {
	// VK sent without Bearer prefix must also be excluded from direct key path.
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "sk-uf-virtual-key-no-bearer-prefix")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	if _, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key); ok {
		t.Error("expected raw VK (no Bearer prefix) to be excluded from direct key path")
	}
}

func TestConvertToUnifAIContext_DirectKey_EnvPrefixNotResolved(t *testing.T) {
	// A caller sending "env.SOME_VAR" must get that literal string as the key value,
	// not the server env var it might reference.
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.Set("x-uf-direct-key", "true")
	ctx.Request.Header.Set("Authorization", "Bearer env.SOME_SECRET")

	unifaiCtx, cancel := ConvertToUnifAIContext(ctx, testHandlerStore{allowDirectKeys: true})
	defer cancel()

	key, ok := unifaiCtx.Value(schemas.UnifAIContextKeyDirectKey).(schemas.Key)
	if !ok {
		t.Fatal("expected direct key to be set")
	}
	if key.Value.GetValue() != "env.SOME_SECRET" {
		t.Errorf("direct key value = %q, want literal %q (must not resolve env vars)", key.Value.GetValue(), "env.SOME_SECRET")
	}
	if key.Value.IsFromSecret() {
		t.Error("direct key must not be marked as from-secret")
	}
}

func TestBuildBaseURL(t *testing.T) {
	const host = "unifai.example.com"
	tests := []struct {
		name     string
		external string
		host     string
		xfProto  string
		xbfProto string
		want     string
	}{
		{name: "defaults to http", host: host, want: "http://" + host},
		{name: "x-forwarded-proto https", host: host, xfProto: "https", want: "https://" + host},
		{name: "x-forwarded-proto comma list", host: host, xfProto: "https, http", want: "https://" + host},
		{name: "x-forwarded-proto uppercase", host: host, xfProto: "HTTPS", want: "https://" + host},
		{name: "x-uf-forwarded-proto https", host: host, xbfProto: "https", want: "https://" + host},
		{name: "x-uf-forwarded-proto uppercase trimmed", host: host, xbfProto: " HTTPS ", want: "https://" + host},
		{name: "x-uf-forwarded-proto comma list", host: host, xbfProto: "https, http", want: "https://" + host},
		{name: "x-uf-forwarded-proto http stays http", host: host, xbfProto: "http", want: "http://" + host},
		{name: "external override wins", external: "https://proxy.example.com", host: host, xfProto: "http", want: "https://proxy.example.com"},
		{name: "external override trailing slash trimmed", external: "https://proxy.example.com/", host: host, want: "https://proxy.example.com"},
		{name: "invalid external falls back to inference", external: "not-a-url", host: host, xbfProto: "https", want: "https://" + host},
		{name: "empty host yields empty", host: "", xbfProto: "https", want: ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := &fasthttp.RequestCtx{}
			ctx.Request.SetHost(tt.host)
			if tt.xfProto != "" {
				ctx.Request.Header.Set("X-Forwarded-Proto", tt.xfProto)
			}
			if tt.xbfProto != "" {
				ctx.Request.Header.Set("x-uf-forwarded-proto", tt.xbfProto)
			}
			if got := BuildBaseURL(ctx, tt.external); got != tt.want {
				t.Fatalf("BuildBaseURL() = %q, want %q", got, tt.want)
			}
		})
	}
}
