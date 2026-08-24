package handlers

import (
	"os"
	"path/filepath"
	"testing"
)

func TestExtractAndStorePDF(t *testing.T) {
	t.Setenv("APP_DIR", t.TempDir())
	raw := []byte("%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
	stored, ctype, err := storeBrowserAIPDF("log-abc", "report.pdf", raw)
	if err != nil {
		t.Fatal(err)
	}
	if ctype != "application/pdf" {
		t.Fatalf("ctype=%s", ctype)
	}
	path, err := resolveBrowserAIAttachmentPath(stored)
	if err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(raw) {
		t.Fatalf("stored mismatch")
	}
	dir := filepath.Dir(path)
	if filepath.Base(dir) != "pdf" {
		t.Fatalf("expected pdf dir, got %s", dir)
	}
}

func TestExtractPDFFromMultipartish(t *testing.T) {
	body := append([]byte("-----boundary\r\nContent-Disposition: form-data\r\n\r\n"), []byte("%PDF-1.4\nx\n%%EOF\n")...)
	pdf := extractPDFBytes(body)
	if pdf == nil || string(pdf[:5]) != "%PDF-" {
		t.Fatalf("failed to extract pdf")
	}
}
