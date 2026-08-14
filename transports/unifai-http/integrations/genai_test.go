package integrations

import (
	"context"
	"testing"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/core/providers/gemini"
	"github.com/unifai/unifai/core/providers/vertex"
	"github.com/unifai/unifai/core/schemas"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/valyala/fasthttp"
)

func TestCreateGenAIRerankRouteConfig(t *testing.T) {
	route := createGenAIRerankRouteConfig("/genai")

	assert.Equal(t, "/genai/v1/rank", route.Path)
	assert.Equal(t, "POST", route.Method)
	assert.Equal(t, RouteConfigTypeGenAI, route.Type)
	assert.NotNil(t, route.GetHTTPRequestType)
	assert.Equal(t, schemas.RerankRequest, route.GetHTTPRequestType(nil))
	assert.NotNil(t, route.GetRequestTypeInstance)
	assert.NotNil(t, route.RequestConverter)
	assert.NotNil(t, route.RerankResponseConverter)
	assert.NotNil(t, route.ErrorConverter)
	assert.Nil(t, route.PreCallback)

	// Verify request instance type
	reqInstance := route.GetRequestTypeInstance(context.Background())
	_, ok := reqInstance.(*vertex.VertexRankRequest)
	assert.True(t, ok, "GetRequestTypeInstance should return *vertex.VertexRankRequest")
}

func TestCreateGenAIRouteConfigsIncludesRerank(t *testing.T) {
	routes := CreateGenAIRouteConfigs("/genai")

	found := false
	for _, route := range routes {
		if route.Path == "/genai/v1/rank" && route.Method == "POST" {
			found = true
			break
		}
	}
	assert.True(t, found, "expected rerank route in genai route configs")
}

func findGenAIRouteForTest(t *testing.T, routes []RouteConfig, path, method string) RouteConfig {
	t.Helper()
	for _, route := range routes {
		if route.Path == path && route.Method == method {
			return route
		}
	}
	t.Fatalf("route %s %s not found", method, path)
	return RouteConfig{}
}

func TestExtractAndSetModelAndRequestTypePreservesRawBodyForGenerateContent(t *testing.T) {
	rawBody := []byte(`{"contents":[{"role":"user","parts":[{"text":"hello"}]}],"generationConfig":{"responseJsonSchema":{"type":"object","properties":{"b":{"type":"string"},"a":{"type":"string"}}}}}`)
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "gemini-2.5-flash:generateContent")
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(rawBody)

	req := &gemini.GeminiGenerationRequest{}
	require.NoError(t, sonic.Unmarshal(rawBody, req))
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)

	err := extractAndSetModelAndRequestType(ctx, unifaiCtx, req)
	require.NoError(t, err)

	assert.Equal(t, true, unifaiCtx.Value(schemas.UnifAIContextKeyUseRawRequestBody))
	assert.Equal(t, rawBody, unifaiCtx.Value(genAIRawRequestBodyContextKey))
}

func TestExtractAndSetModelAndRequestTypeDoesNotRawPassthroughEmbedding(t *testing.T) {
	rawBody := []byte(`{"content":{"parts":[{"text":"hello"}]}}`)
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "gemini-embedding-001:embedContent")
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(rawBody)

	req := &gemini.GeminiEmbeddingRequest{}
	require.NoError(t, sonic.Unmarshal(rawBody, req))
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)

	err := extractAndSetModelAndRequestType(ctx, unifaiCtx, req)
	require.NoError(t, err)

	assert.Nil(t, unifaiCtx.Value(schemas.UnifAIContextKeyUseRawRequestBody))
	assert.Nil(t, unifaiCtx.Value(genAIRawRequestBodyContextKey))
}

func TestGenAIBatchCreateConverterCarriesRawBody(t *testing.T) {
	rawBody := []byte(`{"batch":{"inputConfig":{"requests":{"requests":[{"request":{"contents":[{"role":"user","parts":[{"text":"hello"}]}],"generationConfig":{"temperature":0.2}},"metadata":{"key":"req-1"}}]}}}}`)
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "gemini-2.5-flash:batchGenerateContent")
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(rawBody)

	req := &gemini.GeminiBatchCreateRequest{}
	require.NoError(t, sonic.Unmarshal(rawBody, req))
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	require.NoError(t, extractAndSetModelAndRequestType(ctx, unifaiCtx, req))

	route := findGenAIRouteForTest(t, CreateGenAIRouteConfigs("/genai"), "/genai/v1beta/models/{model:*}", "POST")
	batchReq, err := route.BatchRequestConverter(unifaiCtx, req)
	require.NoError(t, err)
	require.NotNil(t, batchReq)
	require.NotNil(t, batchReq.CreateRequest)

	assert.Equal(t, rawBody, batchReq.CreateRequest.RawRequestBody)
	assert.Equal(t, true, unifaiCtx.Value(schemas.UnifAIContextKeyUseRawRequestBody))
}

func TestGenAICachedContentCreateParserRejectsNonStringScalars(t *testing.T) {
	rawBody := []byte(`{"model":123,"ttl":3600}`)
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(rawBody)

	route := findGenAIRouteForTest(t, CreateGenAICachedContentRouteConfigs("/genai", nil), "/genai/v1beta/cachedContents", "POST")
	req := route.GetRequestTypeInstance(context.Background())

	err := route.RequestParser(ctx, req)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "model must be a string")
}

func TestGenAICachedContentCreateParserCarriesRawBody(t *testing.T) {
	rawBody := []byte(`{"model":"models/gemini-2.5-flash","contents":[{"role":"user","parts":[{"text":"alpha"}]}],"tools":[{"functionDeclarations":[{"name":"lookup","parametersJsonSchema":{"type":"object","properties":{"z":{"type":"string"},"a":{"type":"string"}}}}]}],"ttl":"3600s"}`)
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(rawBody)

	route := findGenAIRouteForTest(t, CreateGenAICachedContentRouteConfigs("/genai", nil), "/genai/v1beta/cachedContents", "POST")
	req := route.GetRequestTypeInstance(context.Background())
	require.NoError(t, route.RequestParser(ctx, req))

	createReq := req.(*schemas.UnifAICachedContentCreateRequest)
	assert.Equal(t, rawBody, createReq.RawRequestBody)
	assert.Equal(t, "gemini-2.5-flash", createReq.Model)
	require.NotNil(t, createReq.TTL)
	assert.Equal(t, "3600s", *createReq.TTL)

	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	converted, err := route.CachedContentRequestConverter(unifaiCtx, req)
	require.NoError(t, err)
	require.NotNil(t, converted)
	assert.Equal(t, true, unifaiCtx.Value(schemas.UnifAIContextKeyUseRawRequestBody))
}

func TestCreateGenAIRouteConfigsIncludesRerankForCompositePrefixes(t *testing.T) {
	prefixes := []string{"/litellm", "/langchain", "/pydanticai"}

	for _, prefix := range prefixes {
		routes := CreateGenAIRouteConfigs(prefix)
		found := false
		for _, route := range routes {
			if route.Path == prefix+"/v1/rank" && route.Method == "POST" {
				found = true
				break
			}
		}
		assert.Truef(t, found, "expected rerank route for prefix %s", prefix)
	}
}

func TestGenAIRerankRequestConverter(t *testing.T) {
	route := createGenAIRerankRouteConfig("/genai")
	require.NotNil(t, route.RequestConverter)

	model := "semantic-ranker-default@latest"
	topN := 2
	content1 := "Paris is capital of France"
	content2 := "Berlin is capital of Germany"
	req := &vertex.VertexRankRequest{
		Model: &model,
		Query: "capital of france",
		Records: []vertex.VertexRankRecord{
			{ID: "rec-1", Content: &content1},
			{ID: "rec-2", Content: &content2},
		},
		TopN: &topN,
	}

	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	unifaiReq, err := route.RequestConverter(unifaiCtx, req)
	require.NoError(t, err)
	require.NotNil(t, unifaiReq)
	require.NotNil(t, unifaiReq.RerankRequest)
	assert.Equal(t, schemas.Vertex, unifaiReq.RerankRequest.Provider)
	assert.Equal(t, "semantic-ranker-default@latest", unifaiReq.RerankRequest.Model)
	assert.Equal(t, "capital of france", unifaiReq.RerankRequest.Query)
	require.Len(t, unifaiReq.RerankRequest.Documents, 2)
	assert.Equal(t, "Paris is capital of France", unifaiReq.RerankRequest.Documents[0].Text)
	assert.Equal(t, "Berlin is capital of Germany", unifaiReq.RerankRequest.Documents[1].Text)
	require.NotNil(t, unifaiReq.RerankRequest.Params)
	require.NotNil(t, unifaiReq.RerankRequest.Params.TopN)
	assert.Equal(t, 2, *unifaiReq.RerankRequest.Params.TopN)
}

func TestGenAIRerankResponseConverterUsesRawResponse(t *testing.T) {
	route := createGenAIRerankRouteConfig("/genai")
	require.NotNil(t, route.RerankResponseConverter)

	raw := map[string]interface{}{"records": []interface{}{}}
	resp := &schemas.UnifAIRerankResponse{
		ExtraFields: schemas.UnifAIResponseExtraFields{
			Provider:    schemas.Vertex,
			RawResponse: raw,
		},
	}
	converted, err := route.RerankResponseConverter(nil, resp)
	require.NoError(t, err)
	assert.Equal(t, raw, converted)
}

func TestGenAIRerankResponseConverterFallsBackWhenNotVertex(t *testing.T) {
	route := createGenAIRerankRouteConfig("/genai")
	require.NotNil(t, route.RerankResponseConverter)

	resp := &schemas.UnifAIRerankResponse{
		Results: []schemas.RerankResult{
			{Index: 0, RelevanceScore: 0.9},
		},
		ExtraFields: schemas.UnifAIResponseExtraFields{
			Provider: schemas.Cohere,
		},
	}
	converted, err := route.RerankResponseConverter(nil, resp)
	require.NoError(t, err)
	assert.Equal(t, resp, converted)
}

func TestCreateGenAIRouteConfigsIncludesModelMetadataRoute(t *testing.T) {
	routes := CreateGenAIRouteConfigs("/genai")

	found := false
	for _, route := range routes {
		if route.Path == "/genai/v1beta/models/{model}" && route.Method == "GET" {
			found = true
			assert.Equal(t, schemas.ListModelsRequest, route.GetHTTPRequestType(nil))
			require.NotNil(t, route.PreCallback)
			require.NotNil(t, route.ListModelsResponseConverter)
			break
		}
	}

	assert.True(t, found, "expected model metadata route in genai route configs")
}

func TestExtractGeminiModelMetadataParams(t *testing.T) {
	ctx := &fasthttp.RequestCtx{}
	ctx.SetUserValue("model", "models/gemini-3-pro-preview")

	listReq := &schemas.UnifAIListModelsRequest{}
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)

	err := extractGeminiModelMetadataParams(ctx, unifaiCtx, listReq)
	require.NoError(t, err)
	assert.Equal(t, schemas.Gemini, listReq.Provider)
	assert.Equal(t, "/models/gemini-3-pro-preview", unifaiCtx.Value(schemas.UnifAIContextKeyURLPath))
	assert.Equal(t, "gemini-3-pro-preview", unifaiCtx.Value(requestedGeminiModelMetadataContextKey))
}

func TestConvertGeminiModelMetadataResponse(t *testing.T) {
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	unifaiCtx.SetValue(requestedGeminiModelMetadataContextKey, "gemini-2.5-pro")

	resp := &schemas.UnifAIListModelsResponse{
		Data: []schemas.Model{{ID: "gemini/gemini-2.5-pro", Name: schemas.Ptr("Gemini 2.5 Pro")}},
	}

	converted, err := convertGeminiModelMetadataResponse(unifaiCtx, resp)
	require.NoError(t, err)

	model, ok := converted.(gemini.GeminiModel)
	require.True(t, ok, "expected gemini.GeminiModel")
	assert.Equal(t, "models/gemini-2.5-pro", model.Name)
	assert.Equal(t, "Gemini 2.5 Pro", model.DisplayName)
}

func TestConvertGeminiModelMetadataResponse_MatchesRequestedModelNotFirst(t *testing.T) {
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	unifaiCtx.SetValue(requestedGeminiModelMetadataContextKey, "gemini-3-pro-preview")

	resp := &schemas.UnifAIListModelsResponse{
		Data: []schemas.Model{
			{ID: "gemini/gemini-1.5-pro", Name: schemas.Ptr("Gemini 1.5 Pro")},
			{ID: "gemini/gemini-3-pro-preview", Name: schemas.Ptr("Gemini 3 Pro Preview")},
		},
	}

	converted, err := convertGeminiModelMetadataResponse(unifaiCtx, resp)
	require.NoError(t, err)

	model, ok := converted.(gemini.GeminiModel)
	require.True(t, ok, "expected gemini.GeminiModel")
	assert.Equal(t, "models/gemini-3-pro-preview", model.Name)
	assert.Equal(t, "Gemini 3 Pro Preview", model.DisplayName)
}

func TestConvertGeminiModelMetadataResponse_EmptyReturnsMinimalModel(t *testing.T) {
	unifaiCtx := schemas.NewUnifAIContext(context.Background(), schemas.NoDeadline)
	unifaiCtx.SetValue(requestedGeminiModelMetadataContextKey, "gemini-3-pro-preview")

	converted, err := convertGeminiModelMetadataResponse(unifaiCtx, &schemas.UnifAIListModelsResponse{Data: []schemas.Model{}})
	require.NoError(t, err)
	model, ok := converted.(gemini.GeminiModel)
	require.True(t, ok, "expected gemini.GeminiModel")
	assert.Equal(t, "models/gemini-3-pro-preview", model.Name)
}
