package logstore

import "testing"

func TestMinimizePACHosts(t *testing.T) {
	in := []string{
		"example.com",
		"www.example.com",
		"api.example.com",
		"parent.test",
		"api.parent.test",
		"other.org",
	}
	out := minimizePACHosts(in)
	got := map[string]bool{}
	for _, h := range out {
		got[h] = true
	}
	if !got["example.com"] || !got["parent.test"] || !got["other.org"] {
		t.Fatalf("expected parents kept: %v", out)
	}
	if got["www.example.com"] || got["api.example.com"] || got["api.parent.test"] {
		t.Fatalf("expected children collapsed: %v", out)
	}
}
