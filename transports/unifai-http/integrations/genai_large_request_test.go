package integrations

import (
	"context"
	"strings"
	"testing"

	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/transports/unifai-http/lib"
	"github.com/valyala/fasthttp"
)

func TestExtractModelAndRequestType_LargePayloadUsesMetadataWithoutBodyParse(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "gemini-2.5-pro:generateContent")
	// Intentionally invalid JSON: detection must rely on large-payload metadata, not body parse.
	ctx.Request.SetBodyString(`{"contents":[INVALID`)

	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	unifaiCtx.SetValue(schemas.UnifAIContextKeyLargePayloadMode, true)
	unifaiCtx.SetValue(schemas.UnifAIContextKeyLargePayloadMetadata, &schemas.LargePayloadMetadata{
		ResponseModalities: []string{"AUDIO"},
	})
	ctx.SetUserValue(lib.FastHTTPUserValueUnifAIContext, unifaiCtx)

	model, reqType := extractModelAndRequestType(ctx)
	if model != "gemini-2.5-pro" {
		t.Fatalf("expected normalized model gemini-2.5-pro, got %q", model)
	}
	if reqType != schemas.SpeechRequest {
		t.Fatalf("expected speech request type from metadata, got %q", reqType)
	}
}

func TestExtractModelAndRequestType_LargeBodyHeuristicSkipsParse(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "gemini-2.5-pro:generateContent")
	ctx.Request.SetBodyStream(strings.NewReader(`{"contents":[INVALID`), schemas.DefaultLargePayloadRequestThresholdBytes+1)

	model, reqType := extractModelAndRequestType(ctx)
	if model != "gemini-2.5-pro" {
		t.Fatalf("expected normalized model gemini-2.5-pro, got %q", model)
	}
	if reqType != schemas.ResponsesRequest {
		t.Fatalf("expected responses request type from large-body heuristic, got %q", reqType)
	}
}
