package configstore

import "testing"

func TestCanonicalMCPCategory(t *testing.T) {
	cases := map[string]string{
		"":               "",
		"ai":             "AI",
		"AI":             "AI",
		"Communications": "Communication",
		"communication":  "Communication",
		"ecommerce":      "E-commerce",
		"E-commerce":     "E-commerce",
		"design":         "Design",
		"Custom Thing":   "Custom Thing",
	}
	for in, want := range cases {
		if got := CanonicalMCPCategory(in); got != want {
			t.Fatalf("CanonicalMCPCategory(%q)=%q want %q", in, got, want)
		}
	}
}

func TestDedupeCanonicalMCPCategories(t *testing.T) {
	got := DedupeCanonicalMCPCategories([]string{"ai", "AI", "Communications", "Communication", "design"})
	want := map[string]bool{"AI": true, "Communication": true, "Design": true}
	if len(got) != len(want) {
		t.Fatalf("got %v", got)
	}
	for _, c := range got {
		if !want[c] {
			t.Fatalf("unexpected %q in %v", c, got)
		}
	}
}

func TestMCPCategoryFilterValuesIncludesAliases(t *testing.T) {
	got := MCPCategoryFilterValues([]string{"Communication"})
	has := false
	for _, v := range got {
		if v == "Communications" || v == "communications" {
			has = true
			break
		}
	}
	if !has {
		t.Fatalf("expected Communications alias in %v", got)
	}
}
