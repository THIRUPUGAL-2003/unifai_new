package logstore

import "testing"

func TestMinimizePACHosts(t *testing.T) {
	in := []string{
		"chatgpt.com",
		"www.chatgpt.com",
		"ab.chatgpt.com",
		"claude.ai",
		"api.claude.ai",
		"example.org",
	}
	out := minimizePACHosts(in)
	got := map[string]bool{}
	for _, h := range out {
		got[h] = true
	}
	if !got["chatgpt.com"] || !got["claude.ai"] || !got["example.org"] {
		t.Fatalf("expected parents kept: %v", out)
	}
	if got["www.chatgpt.com"] || got["ab.chatgpt.com"] || got["api.claude.ai"] {
		t.Fatalf("expected children collapsed: %v", out)
	}
}
