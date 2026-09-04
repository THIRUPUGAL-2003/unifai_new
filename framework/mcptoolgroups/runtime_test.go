package mcptoolgroups

import (
	"reflect"
	"testing"
)

func TestToolNamesUIBundleShape(t *testing.T) {
	spec := map[string]any{
		"tools": []any{
			map[string]any{
				"mcp_client_id":   "abc-123",
				"mcp_client_name": "notion",
				"tool_names":      []any{"search", "fetch"},
			},
		},
	}
	got := toolNames(spec)
	want := []string{"notion-search", "notion-fetch"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("toolNames() = %#v, want %#v", got, want)
	}
}

func TestToolNamesBlankMeansWildcard(t *testing.T) {
	spec := map[string]any{
		"tools": []any{
			map[string]any{
				"mcp_client_name": "jira",
				"tool_names":      []any{},
			},
		},
	}
	got := toolNames(spec)
	want := []string{"jira-*"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("toolNames() = %#v, want %#v", got, want)
	}
}

func TestToolNamesFlatName(t *testing.T) {
	spec := map[string]any{
		"tools": []any{
			map[string]any{"name": "slack-post_message"},
			"github-*",
		},
	}
	got := toolNames(spec)
	want := []string{"slack-post_message", "github-*"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("toolNames() = %#v, want %#v", got, want)
	}
}

func TestIsToolAllowedWithUIShape(t *testing.T) {
	r := &Runtime{groups: []Group{{
		ID: 1, Name: "g", Enabled: true,
		Tools: toolNames(map[string]any{
			"tools": []any{map[string]any{
				"mcp_client_name": "notion",
				"tool_names":      []any{"search"},
			}},
		}),
	}}}
	if !r.IsToolAllowed("notion-search", RequestContext{}) {
		t.Fatal("expected notion-search allowed")
	}
	if r.IsToolAllowed("notion-fetch", RequestContext{}) {
		t.Fatal("expected notion-fetch denied when group matched with allowlist")
	}
}
