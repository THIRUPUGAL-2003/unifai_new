package logstore

import "testing"

func TestLooksLikeBinaryOrWireGarbage(t *testing.T) {
	garbage := []string{
		`Rp];$u\OVoT]xy 9+)*wlTP-`,
		`X*L$( rF2D:TvJxf<`,
		`-gW..eKBN f!D@k|J7XY[olJ#7AFA}N*X;`,
		`Cursor.exe*@c8df43df32fdc3daf238c2dba17c9acbfa6a6066b06556fd3946a533190`,
		`(Intel(R) Core(TM) i7-8850H CPU @ 2.60GHz`,
	}
	ok := []string{
		"what is my phone number 9876543210",
		"hello",
		"cat",
		"a=1",
		"SELECT * FROM users WHERE id=1",
		"hi",
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
