package integrations

import (
	"context"
	"strings"
	"testing"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/core/providers/anthropic"
	"github.com/unifai/unifai/core/providers/bedrock"
	"github.com/unifai/unifai/core/providers/gemini"
	"github.com/unifai/unifai/core/schemas"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/valyala/fasthttp"
)

// testLogger implements schemas.Logger for testing (all no-ops)
type testLogger struct{}

func (t *testLogger) Debug(msg string, args ...any)                     {}
func (t *testLogger) Info(msg string, args ...any)                      {}
func (t *testLogger) Warn(msg string, args ...any)                      {}
func (t *testLogger) Error(msg string, args ...any)                     {}
func (t *testLogger) Fatal(msg string, args ...any)                     {}
func (t *testLogger) SetLevel(level schemas.LogLevel)                   {}
func (t *testLogger) SetOutputType(outputType schemas.LoggerOutputType) {}
func (t *testLogger) LogHTTPRequest(level schemas.LogLevel, msg string) schemas.LogEventBuilder {
	return schemas.NoopLogEvent
}

var _ schemas.Logger = (*testLogger)(nil)

func ptr(i int) *int {
	return &i
}

func strPtr(s string) *string {
	return &s
}

func newTestGenericRouter() *GenericRouter {
	return NewGenericRouter(nil, &mockHandlerStore{}, nil, nil, &testLogger{})
}

func newTestUnifAIContext() *schemas.UnifAIContext {
	return schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
}

func TestExtractAndParseFallbacks_GeminiGenerationRequest(t *testing.T) {
	router := newTestGenericRouter()
	geminiReq := &gemini.GeminiGenerationRequest{
		Model:     "gemini/gemini-3-flash-preview",
		Fallbacks: []string{"vertex/gemini-3-flash-preview"},
	}
	unifaiReq := &schemas.UnifAIRequest{
		ResponsesRequest: &schemas.UnifAIResponsesRequest{
			Provider: schemas.Gemini,
			Model:    "gemini-3-flash-preview",
		},
	}

	err := router.extractAndParseFallbacks(newTestUnifAIContext(), geminiReq, unifaiReq)

	require.NoError(t, err)
	require.NotNil(t, unifaiReq.ResponsesRequest)
	require.Len(t, unifaiReq.ResponsesRequest.Fallbacks, 1)
	assert.Equal(t, schemas.Vertex, unifaiReq.ResponsesRequest.Fallbacks[0].Provider)
	assert.Equal(t, "gemini-3-flash-preview", unifaiReq.ResponsesRequest.Fallbacks[0].Model)
}

// TestSendStreamError_PropagatesProviderStatusCode verifies that sendStreamError
// sets the HTTP status code from the provider's UnifAIError.StatusCode field.
// All three providers (OpenAI, Anthropic, Bedrock) return actual HTTP error codes
// for pre-stream errors, so UnifAI must propagate them faithfully.
func TestSendStreamError_PropagatesProviderStatusCode(t *testing.T) {
	tests := []struct {
		name               string
		statusCode         *int
		expectedStatusCode int
	}{
		{
			name:               "provider 400 - Bedrock ValidationException / OpenAI invalid_request_error",
			statusCode:         ptr(400),
			expectedStatusCode: 400,
		},
		{
			name:               "provider 429 - rate limiting (all providers)",
			statusCode:         ptr(429),
			expectedStatusCode: 429,
		},
		{
			name:               "provider 503 - Bedrock ServiceUnavailableException",
			statusCode:         ptr(503),
			expectedStatusCode: 503,
		},
		{
			name:               "provider 529 - Anthropic overloaded_error",
			statusCode:         ptr(529),
			expectedStatusCode: 529,
		},
		{
			name:               "nil StatusCode defaults to 500",
			statusCode:         nil,
			expectedStatusCode: 500,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			router := newTestGenericRouter()
			ctx := &fasthttp.RequestCtx{}
			unifaiCtx := newTestUnifAIContext()

			unifaiErr := &schemas.UnifAIError{
				StatusCode: tt.statusCode,
				Error: &schemas.ErrorField{
					Message: "test error",
				},
			}

			config := RouteConfig{
				ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
					return err
				},
			}

			router.sendStreamError(ctx, unifaiCtx, config, unifaiErr)

			assert.Equal(t, tt.expectedStatusCode, ctx.Response.StatusCode())
			assert.Equal(t, "application/json", string(ctx.Response.Header.ContentType()))

			body := string(ctx.Response.Body())
			assert.True(t, sonic.Valid(ctx.Response.Body()), "response body should be valid JSON, got: %s", body)
			assert.False(t, strings.HasPrefix(body, "data: "), "response should not be SSE format")
		})
	}
}

// TestSendStreamError_OpenAIErrorFormat verifies the response body matches the
// OpenAI error format. OpenAI's ErrorConverter returns *schemas.UnifAIError directly,
// which serializes to {"is_unifai_error":false,"status_code":400,"error":{...}}.
func TestSendStreamError_OpenAIErrorFormat(t *testing.T) {
	router := newTestGenericRouter()
	ctx := &fasthttp.RequestCtx{}
	unifaiCtx := newTestUnifAIContext()

	unifaiErr := &schemas.UnifAIError{
		IsUnifAIError: false,
		StatusCode:     ptr(400),
		Error: &schemas.ErrorField{
			Type:    strPtr("invalid_request_error"),
			Message: "content is empty",
		},
	}

	config := RouteConfig{
		ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
			return err
		},
	}

	router.sendStreamError(ctx, unifaiCtx, config, unifaiErr)

	assert.Equal(t, 400, ctx.Response.StatusCode())

	// Unmarshal and verify the structure
	var result map[string]interface{}
	err := sonic.Unmarshal(ctx.Response.Body(), &result)
	require.NoError(t, err)

	assert.Contains(t, result, "is_unifai_error")
	assert.Contains(t, result, "status_code")
	assert.Contains(t, result, "error")
	assert.Equal(t, false, result["is_unifai_error"])

	errorObj, ok := result["error"].(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, "invalid_request_error", errorObj["type"])
	assert.Equal(t, "content is empty", errorObj["message"])
}

// TestSendStreamError_AnthropicErrorFormat verifies the response body matches the
// Anthropic error format: {"type":"error","error":{"type":"...","message":"..."}}.
// Critically, it also verifies that the StreamConfig.ErrorConverter (which returns
// raw SSE strings) is NOT used — sendStreamError must use the route-level ErrorConverter.
func TestSendStreamError_AnthropicErrorFormat(t *testing.T) {
	router := newTestGenericRouter()
	ctx := &fasthttp.RequestCtx{}
	unifaiCtx := newTestUnifAIContext()

	unifaiErr := &schemas.UnifAIError{
		StatusCode: ptr(429),
		Error: &schemas.ErrorField{
			Type:    strPtr("rate_limit_error"),
			Message: "rate limited",
		},
	}

	config := RouteConfig{
		// Route-level: returns JSON-marshallable *AnthropicMessageError
		ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
			return anthropic.ToAnthropicChatCompletionError(err)
		},
		// Stream-level: returns raw SSE string — should NOT be used by sendStreamError
		StreamConfig: &StreamConfig{
			ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
				return anthropic.ToAnthropicResponsesStreamError(err)
			},
		},
	}

	router.sendStreamError(ctx, unifaiCtx, config, unifaiErr)

	assert.Equal(t, 429, ctx.Response.StatusCode())
	assert.Equal(t, "application/json", string(ctx.Response.Header.ContentType()))

	body := string(ctx.Response.Body())

	// Must NOT contain SSE markers — that would mean StreamConfig.ErrorConverter was used
	assert.NotContains(t, body, "event: error", "response should not contain SSE event markers")

	// Unmarshal and verify Anthropic error structure
	var result anthropic.AnthropicMessageError
	err := sonic.Unmarshal(ctx.Response.Body(), &result)
	require.NoError(t, err)

	assert.Equal(t, "error", result.Type)
	assert.Equal(t, "rate_limit_error", result.Error.Type)
	assert.Equal(t, "rate limited", result.Error.Message)
}

// TestSendStreamError_BedrockErrorFormat verifies the response body matches the
// Bedrock error format: {"__type":"ValidationException","message":"..."}.
func TestSendStreamError_BedrockErrorFormat(t *testing.T) {
	router := newTestGenericRouter()
	ctx := &fasthttp.RequestCtx{}
	unifaiCtx := newTestUnifAIContext()

	unifaiErr := &schemas.UnifAIError{
		StatusCode: ptr(400),
		Error: &schemas.ErrorField{
			Code:    strPtr("ValidationException"),
			Message: "validation error",
		},
	}

	config := RouteConfig{
		ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
			return bedrock.ToBedrockError(err)
		},
	}

	router.sendStreamError(ctx, unifaiCtx, config, unifaiErr)

	assert.Equal(t, 400, ctx.Response.StatusCode())

	// Unmarshal and verify Bedrock error structure
	var result bedrock.BedrockError
	err := sonic.Unmarshal(ctx.Response.Body(), &result)
	require.NoError(t, err)

	assert.Equal(t, "ValidationException", result.Type)
	assert.Equal(t, "validation error", result.Message)
}

// TestSendStreamError_ForwardsProviderHeaders verifies that provider response headers
// stored in the UnifAIContext are forwarded to the HTTP response. This ensures
// clients receive provider-specific headers (e.g., x-amzn-requestid for Bedrock,
// x-request-id for Anthropic) even in error scenarios.
func TestSendStreamError_ForwardsProviderHeaders(t *testing.T) {
	router := newTestGenericRouter()
	ctx := &fasthttp.RequestCtx{}
	unifaiCtx := newTestUnifAIContext()

	// Set provider response headers on the context
	unifaiCtx.SetValue(schemas.UnifAIContextKeyProviderResponseHeaders, map[string]string{
		"x-amzn-requestid": "req-123",
		"x-amzn-errortype": "ValidationException",
	})

	unifaiErr := &schemas.UnifAIError{
		StatusCode: ptr(400),
		Error: &schemas.ErrorField{
			Message: "validation error",
		},
	}

	config := RouteConfig{
		ErrorConverter: func(ctx *schemas.UnifAIContext, err *schemas.UnifAIError) interface{} {
			return err
		},
	}

	router.sendStreamError(ctx, unifaiCtx, config, unifaiErr)

	assert.Equal(t, 400, ctx.Response.StatusCode())
	assert.Equal(t, "req-123", string(ctx.Response.Header.Peek("x-amzn-requestid")))
	assert.Equal(t, "ValidationException", string(ctx.Response.Header.Peek("x-amzn-errortype")))
}

// TestApplyUnifAIResponseHeaders covers the routed-identity headers added so
// drop-in integration callers (Anthropic SDK against `/anthropic/v1/messages`,
// OpenAI SDK against `/openai/v1/chat/completions`, etc.) can recover the
// actual provider/model that handled the request — including after fallback
// or routing-rule resolution. The body shape they get back has no place to
// surface this; headers do.
func TestApplyUnifAIResponseHeaders(t *testing.T) {
	t.Run("routed identity emits all headers", func(t *testing.T) {
		ctx := &fasthttp.RequestCtx{}
		unifaiCtx := newTestUnifAIContext()

		extra := schemas.UnifAIResponseExtraFields{
			Provider:               schemas.Bedrock,
			OriginalModelRequested: "claude-sonnet-4-6",
			ResolvedModelUsed:      "us.anthropic.claude-sonnet-4-6",
			RequestType:            schemas.ChatCompletionRequest,
			ProviderResponseHeaders: map[string]string{
				"x-amzn-requestid": "req-789",
			},
		}

		applyUnifAIResponseHeaders(ctx, unifaiCtx, extra)

		assert.Equal(t, "bedrock", string(ctx.Response.Header.Peek(HeaderUnifAIProvider)))
		assert.Equal(t, "claude-sonnet-4-6", string(ctx.Response.Header.Peek(HeaderUnifAIOriginalModel)))
		assert.Equal(t, "us.anthropic.claude-sonnet-4-6", string(ctx.Response.Header.Peek(HeaderUnifAIResolvedModel)))
		assert.Equal(t, string(schemas.ChatCompletionRequest), string(ctx.Response.Header.Peek(HeaderUnifAIRequestType)))
		assert.Equal(t, "req-789", string(ctx.Response.Header.Peek("x-amzn-requestid")))
		// No fallback fired — header must be absent.
		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIFallbackIndex)))
	})

	t.Run("fallback index from context emits when non-zero", func(t *testing.T) {
		ctx := &fasthttp.RequestCtx{}
		unifaiCtx := newTestUnifAIContext()
		unifaiCtx.SetValue(schemas.UnifAIContextKeyFallbackIndex, 2)

		extra := schemas.UnifAIResponseExtraFields{
			Provider:          schemas.Anthropic,
			ResolvedModelUsed: "claude-haiku-4-5",
		}

		applyUnifAIResponseHeaders(ctx, unifaiCtx, extra)

		assert.Equal(t, "2", string(ctx.Response.Header.Peek(HeaderUnifAIFallbackIndex)))
	})

	t.Run("zero-value extra writes no headers", func(t *testing.T) {
		ctx := &fasthttp.RequestCtx{}
		unifaiCtx := newTestUnifAIContext()

		applyUnifAIResponseHeaders(ctx, unifaiCtx, schemas.UnifAIResponseExtraFields{})

		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIProvider)))
		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIOriginalModel)))
		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIResolvedModel)))
		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIRequestType)))
		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIFallbackIndex)))
	})

	t.Run("primary-provider success (FallbackIndex=0) does not emit fallback header", func(t *testing.T) {
		ctx := &fasthttp.RequestCtx{}
		unifaiCtx := newTestUnifAIContext()
		unifaiCtx.SetValue(schemas.UnifAIContextKeyFallbackIndex, 0)

		applyUnifAIResponseHeaders(ctx, unifaiCtx, schemas.UnifAIResponseExtraFields{
			Provider: schemas.OpenAI,
		})

		assert.Empty(t, string(ctx.Response.Header.Peek(HeaderUnifAIFallbackIndex)),
			"FallbackIndex=0 means primary succeeded; absence of header is the signal")
	})
}
