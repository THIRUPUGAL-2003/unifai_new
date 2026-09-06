package logstore

import "testing"

func TestLooksLikeBinaryOrWireGarbage(t *testing.T) {
	garbage := []string{
		`Rp];$u\OVoT]xy 9+)*wlTP-`,
		`X*L$( rF2D:TvJxf<`,
		`-gW..eKBN f!D@k|J7XY[olJ#7AFA}N*X;`,
	}
	ok := []string{
		"what is my phone number 9876543210",
		"hello",
		"cat",
		"a=1",
		"SELECT * FROM users WHERE id=1",
	}
	for _, s := range garbage {
		if !looksLikeBinaryOrWireGarbage(s) {
			t.Fatalf("expected garbage: %q", s)
		}
	}
	for _, s := range ok {
		if looksLikeBinaryOrWireGarbage(s) {
			t.Fatalf("expected OK: %q", s)
		}
	}
}
