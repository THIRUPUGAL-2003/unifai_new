package mcp

import (
	"encoding/json"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/unifai/unifai/core/schemas"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestConvertMCPToolToUnifAISchema_EmptyParameters tests that tools with no parameters
// get an empty properties map instead of nil, which is required by some providers like OpenAI
func TestConvertMCPToolToUnifAISchema_EmptyParameters(t *testing.T) {
	// Create a tool with no parameters (like return_special_chars or return_null)
	mcpTool := &mcp.Tool{
		Name:        "test_tool_no_params",
		Description: "A test tool with no parameters",
		InputSchema: mcp.ToolInputSchema{
			Type:       "object",
			Properties: map[string]interface{}{}, // Empty properties
			Required:   []string{},
		},
	}

	// Convert the tool
	unifaiTool := convertMCPToolToUnifAISchema(mcpTool, defaultLogger)

	// Verify the function was created
	if unifaiTool.Function == nil {
		t.Fatal("Function should not be nil")
	}

	// Verify parameters were created
	if unifaiTool.Function.Parameters == nil {
		t.Fatal("Parameters should not be nil")
	}

	// Verify properties is not nil (this is the key fix)
	if unifaiTool.Function.Parameters.Properties == nil {
		t.Error("Properties should not be nil for object type, even if empty")
	}

	// Verify it's an empty map
	if unifaiTool.Function.Parameters.Properties != nil && unifaiTool.Function.Parameters.Properties.Len() != 0 {
		t.Errorf("Expected empty properties map, got %d properties", unifaiTool.Function.Parameters.Properties.Len())
	}

	// Verify the type is preserved
	if unifaiTool.Function.Parameters.Type != "object" {
		t.Errorf("Expected type 'object', got '%s'", unifaiTool.Function.Parameters.Type)
	}
}

// TestConvertMCPToolToUnifAISchema_WithAnnotations tests that MCP tool annotations
// are preserved on ChatTool.Annotations (not ChatToolFunction) and are absent from JSON.
func TestConvertMCPToolToUnifAISchema_WithAnnotations(t *testing.T) {
	readOnly := true
	destructive := false

	mcpTool := &mcp.Tool{
		Name:        "read_resource",
		Description: "Reads a resource",
		InputSchema: mcp.ToolInputSchema{
			Type:       "object",
			Properties: map[string]interface{}{},
		},
		Annotations: mcp.ToolAnnotation{
			Title:           "Resource Reader",
			ReadOnlyHint:    &readOnly,
			DestructiveHint: &destructive,
			IdempotentHint:  schemas.Ptr(true),
		},
	}

	unifaiTool := convertMCPToolToUnifAISchema(mcpTool, defaultLogger)

	// Annotations must be on ChatTool, not buried in Function
	require.NotNil(t, unifaiTool.Annotations, "Annotations should be set on ChatTool")
	assert.Equal(t, "Resource Reader", unifaiTool.Annotations.Title)
	require.NotNil(t, unifaiTool.Annotations.ReadOnlyHint)
	assert.True(t, *unifaiTool.Annotations.ReadOnlyHint)
	require.NotNil(t, unifaiTool.Annotations.DestructiveHint)
	assert.False(t, *unifaiTool.Annotations.DestructiveHint)
	require.NotNil(t, unifaiTool.Annotations.IdempotentHint)
	assert.True(t, *unifaiTool.Annotations.IdempotentHint)
	assert.Nil(t, unifaiTool.Annotations.OpenWorldHint)

	// The JSON sent to providers must not contain annotations
	toolJSON, err := json.Marshal(unifaiTool)
	require.NoError(t, err)
	s := string(toolJSON)
	assert.NotContains(t, s, "annotations", "annotations must be absent from provider JSON")
	assert.NotContains(t, s, "readOnlyHint", "readOnlyHint must be absent from provider JSON")
	assert.NotContains(t, s, "Resource Reader", "annotation title must be absent from provider JSON")
}

// TestConvertMCPToolToUnifAISchema_NilAnnotationsWhenAllZero verifies the nil guard:
// when all annotation fields are zero-valued, ChatTool.Annotations must remain nil.
func TestConvertMCPToolToUnifAISchema_NilAnnotationsWhenAllZero(t *testing.T) {
	mcpTool := &mcp.Tool{
		Name:        "no_hints_tool",
		Description: "A tool with no annotation hints",
		InputSchema: mcp.ToolInputSchema{
			Type:       "object",
			Properties: map[string]interface{}{},
		},
		Annotations: mcp.ToolAnnotation{}, // All zero values — Title empty, all hints nil
	}

	unifaiTool := convertMCPToolToUnifAISchema(mcpTool, defaultLogger)

	assert.Nil(t, unifaiTool.Annotations,
		"Annotations should be nil when all MCP annotation fields are zero")
}

// TestConvertMCPToolToUnifAISchema_WithParameters tests the normal case with parameters
func TestConvertMCPToolToUnifAISchema_WithParameters(t *testing.T) {
	// Create a tool with parameters
	mcpTool := &mcp.Tool{
		Name:        "test_tool_with_params",
		Description: "A test tool with parameters",
		InputSchema: mcp.ToolInputSchema{
			Type: "object",
			Properties: map[string]interface{}{
				"param1": map[string]interface{}{
					"type":        "string",
					"description": "A string parameter",
				},
				"param2": map[string]interface{}{
					"type":        "number",
					"description": "A number parameter",
				},
			},
			Required: []string{"param1"},
		},
	}

	// Convert the tool
	unifaiTool := convertMCPToolToUnifAISchema(mcpTool, defaultLogger)

	// Verify the function was created
	if unifaiTool.Function == nil {
		t.Fatal("Function should not be nil")
	}

	// Verify parameters were created
	if unifaiTool.Function.Parameters == nil {
		t.Fatal("Parameters should not be nil")
	}

	// Verify properties is not nil
	if unifaiTool.Function.Parameters.Properties == nil {
		t.Fatal("Properties should not be nil")
	}

	// Verify the correct number of properties
	if unifaiTool.Function.Parameters.Properties.Len() != 2 {
		t.Errorf("Expected 2 properties, got %d", unifaiTool.Function.Parameters.Properties.Len())
	}

	// Verify required fields
	if len(unifaiTool.Function.Parameters.Required) != 1 {
		t.Errorf("Expected 1 required field, got %d", len(unifaiTool.Function.Parameters.Required))
	}

	if unifaiTool.Function.Parameters.Required[0] != "param1" {
		t.Errorf("Expected required field 'param1', got '%s'", unifaiTool.Function.Parameters.Required[0])
	}
}

// TestConvertMCPToolToUnifAISchema_PreservesDefs verifies that top-level JSON
// Schema definitions ($defs) on an MCP tool's input schema survive conversion.
// Without this, a $ref inside a property (which rides along in Properties) would
// be left dangling once the definitions it targets are dropped — the cause of
// Vertex Gemini rejecting such tools with INVALID_ARGUMENT.
func TestConvertMCPToolToUnifAISchema_PreservesDefs(t *testing.T) {
	mcpTool := &mcp.Tool{
		Name:        "suggest_time",
		Description: "Suggests time periods",
		InputSchema: mcp.ToolInputSchema{
			Type: "object",
			Properties: map[string]interface{}{
				"preferences": map[string]interface{}{
					"$ref": "#/$defs/Preferences",
				},
			},
			Required: []string{"preferences"},
			Defs: map[string]interface{}{
				"Preferences": map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"startHour": map[string]interface{}{"type": "string"},
					},
				},
			},
		},
	}

	unifaiTool := convertMCPToolToUnifAISchema(mcpTool, defaultLogger)
	require.NotNil(t, unifaiTool.Function)
	require.NotNil(t, unifaiTool.Function.Parameters)
	require.NotNil(t, unifaiTool.Function.Parameters.Defs, "$defs must be preserved on conversion")

	data, err := json.Marshal(unifaiTool.Function.Parameters)
	require.NoError(t, err)
	s := string(data)
	assert.Contains(t, s, `"$defs"`, "marshalled schema must carry $defs")
	assert.Contains(t, s, "Preferences", "definition name must be present")
	assert.Contains(t, s, `"$ref"`, "the property $ref must still be present (resolution happens per-provider)")
}
