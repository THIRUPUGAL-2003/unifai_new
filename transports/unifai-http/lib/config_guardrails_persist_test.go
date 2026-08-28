package lib

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestPersistGuardrailsConfigWritesConfigJSON(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.json")
	if err := os.WriteFile(cfgPath, []byte("{}\n"), 0644); err != nil {
		t.Fatal(err)
	}

	c := &Config{configPath: cfgPath}
	cfg := &GuardrailsConfig{
		GuardrailProviders: []GuardrailProvider{{ID: 1, ProviderName: "regex", PolicyName: "pii"}},
	}
	if err := c.PersistGuardrailsConfig(cfg); err != nil {
		t.Fatal(err)
	}

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		t.Fatal(err)
	}
	var root map[string]json.RawMessage
	if err := json.Unmarshal(data, &root); err != nil {
		t.Fatal(err)
	}
	var saved GuardrailsConfig
	if err := json.Unmarshal(root["guardrails_config"], &saved); err != nil {
		t.Fatal(err)
	}
	if len(saved.GuardrailProviders) != 1 || saved.GuardrailProviders[0].PolicyName != "pii" {
		t.Fatalf("unexpected saved config: %+v", saved)
	}
}

func TestPersistGuardrailsConfigFallsBackToOverlay(t *testing.T) {
	dir := t.TempDir()
	// A directory at config.json makes in-place writes fail portably (including Windows).
	cfgPath := filepath.Join(dir, "config.json")
	if err := os.Mkdir(cfgPath, 0755); err != nil {
		t.Fatal(err)
	}

	c := &Config{configPath: cfgPath}
	cfg := &GuardrailsConfig{
		GuardrailProviders: []GuardrailProvider{{ID: 7, ProviderName: "regex", PolicyName: "blocklist"}},
	}
	if err := c.PersistGuardrailsConfig(cfg); err != nil {
		t.Fatal(err)
	}

	overlay := loadGuardrailsOverlay(cfgPath)
	if overlay == nil || len(overlay.GuardrailProviders) != 1 || overlay.GuardrailProviders[0].ID != 7 {
		t.Fatalf("overlay not loaded: %+v", overlay)
	}
}

func TestPersistGuardrailsConfigClearsOverlayAfterSuccessfulWrite(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.json")
	if err := os.WriteFile(cfgPath, []byte("{}\n"), 0644); err != nil {
		t.Fatal(err)
	}
	overlayPath := filepath.Join(dir, "guardrails_config.json")
	if err := os.WriteFile(overlayPath, []byte(`{"guardrail_rules":[],"guardrail_providers":[]}`), 0644); err != nil {
		t.Fatal(err)
	}

	c := &Config{configPath: cfgPath}
	cfg := &GuardrailsConfig{
		GuardrailProviders: []GuardrailProvider{{ID: 2, ProviderName: "regex", PolicyName: "fresh"}},
	}
	if err := c.PersistGuardrailsConfig(cfg); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(overlayPath); !os.IsNotExist(err) {
		t.Fatalf("overlay should be removed after successful config.json write, err=%v", err)
	}
}

func TestLoadGuardrailsOverlay(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.json")
	overlayPath := filepath.Join(dir, "guardrails_config.json")
	payload := []byte(`{"guardrail_rules":[],"guardrail_providers":[{"id":3,"provider_name":"regex","policy_name":"from-overlay","enabled":true}]}`)
	if err := os.WriteFile(overlayPath, payload, 0644); err != nil {
		t.Fatal(err)
	}

	overlay := loadGuardrailsOverlay(cfgPath)
	if overlay == nil || len(overlay.GuardrailProviders) != 1 || overlay.GuardrailProviders[0].PolicyName != "from-overlay" {
		t.Fatalf("unexpected overlay: %+v", overlay)
	}
	if loadGuardrailsOverlay(filepath.Join(dir, "missing", "config.json")) != nil {
		t.Fatal("missing overlay should return nil")
	}
}
