package handlers

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode"

	"github.com/google/uuid"
)

const browserAIAttachmentMaxBytes = 20 << 20 // 20 MiB

var unsafeAttachmentNameChars = regexp.MustCompile(`[^a-zA-Z0-9._\- ]+`)

// browserAIPdfDir is the temporary PDF store under APP_DIR/pdf (or ./data/pdf).
func browserAIPdfDir() string {
	base := strings.TrimSpace(os.Getenv("APP_DIR"))
	if base == "" {
		base = "data"
	}
	return filepath.Join(base, "pdf")
}

func ensureBrowserAIPdfDir() (string, error) {
	dir := browserAIPdfDir()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", fmt.Errorf("create pdf dir: %w", err)
	}
	return dir, nil
}

func sanitizeAttachmentFileName(name string) string {
	name = strings.TrimSpace(name)
	name = filepath.Base(name)
	name = strings.ReplaceAll(name, "..", "")
	name = unsafeAttachmentNameChars.ReplaceAllString(name, "_")
	name = strings.Trim(name, " ._")
	if name == "" {
		name = "attachment.pdf"
	}
	// Cap length
	runes := []rune(name)
	if len(runes) > 120 {
		ext := filepath.Ext(name)
		base := strings.TrimSuffix(string(runes), ext)
		if len([]rune(base)) > 100 {
			base = string([]rune(base)[:100])
		}
		name = base + ext
	}
	return name
}

func extractPDFBytes(data []byte) []byte {
	if len(data) == 0 {
		return nil
	}
	if string(data[:min(5, len(data))]) == "%PDF-" {
		return data
	}
	idx := strings.Index(string(data), "%PDF-")
	if idx < 0 {
		// binary-safe search
		idx = indexPDFMagic(data)
	}
	if idx < 0 {
		return nil
	}
	pdf := data[idx:]
	// Prefer trim after last %%EOF if present
	if eof := lastIndexBytes(pdf, []byte("%%EOF")); eof >= 0 {
		end := eof + 5
		if end < len(pdf) {
			// include trailing newline if any
			for end < len(pdf) && (pdf[end] == '\n' || pdf[end] == '\r') {
				end++
			}
			pdf = pdf[:end]
		}
	}
	return pdf
}

func indexPDFMagic(data []byte) int {
	sig := []byte("%PDF-")
	for i := 0; i+len(sig) <= len(data) && i < 64*1024; i++ {
		match := true
		for j := 0; j < len(sig); j++ {
			if data[i+j] != sig[j] {
				match = false
				break
			}
		}
		if match {
			return i
		}
	}
	return -1
}

func lastIndexBytes(haystack, needle []byte) int {
	if len(needle) == 0 || len(haystack) < len(needle) {
		return -1
	}
	for i := len(haystack) - len(needle); i >= 0; i-- {
		ok := true
		for j := 0; j < len(needle); j++ {
			if haystack[i+j] != needle[j] {
				ok = false
				break
			}
		}
		if ok {
			return i
		}
	}
	return -1
}

func storeBrowserAIPDF(logID, originalName string, data []byte) (storedName string, contentType string, err error) {
	if len(data) == 0 {
		return "", "", fmt.Errorf("empty file")
	}
	if len(data) > browserAIAttachmentMaxBytes {
		return "", "", fmt.Errorf("file too large (max %d bytes)", browserAIAttachmentMaxBytes)
	}
	pdf := extractPDFBytes(data)
	if len(pdf) == 0 {
		return "", "", fmt.Errorf("not a pdf")
	}
	dir, err := ensureBrowserAIPdfDir()
	if err != nil {
		return "", "", err
	}
	safe := sanitizeAttachmentFileName(originalName)
	if !strings.HasSuffix(strings.ToLower(safe), ".pdf") {
		safe += ".pdf"
	}
	id := strings.TrimSpace(logID)
	if id == "" {
		id = uuid.New().String()
	}
	// Flatten id for filename
	id = strings.Map(func(r rune) rune {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '-' {
			return r
		}
		return '-'
	}, id)
	storedName = id + "_" + safe
	path := filepath.Join(dir, storedName)
	if err := os.WriteFile(path, pdf, 0o644); err != nil {
		return "", "", err
	}
	return storedName, "application/pdf", nil
}

func resolveBrowserAIAttachmentPath(storedName string) (string, error) {
	storedName = filepath.Base(strings.TrimSpace(storedName))
	if storedName == "" || storedName == "." || storedName == ".." {
		return "", fmt.Errorf("invalid attachment")
	}
	dir, err := ensureBrowserAIPdfDir()
	if err != nil {
		return "", err
	}
	full := filepath.Join(dir, storedName)
	// Ensure path stays inside pdf dir
	absDir, err := filepath.Abs(dir)
	if err != nil {
		return "", err
	}
	absFile, err := filepath.Abs(full)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(absDir, absFile)
	if err != nil || strings.HasPrefix(rel, "..") {
		return "", fmt.Errorf("invalid attachment path")
	}
	if _, err := os.Stat(absFile); err != nil {
		return "", fmt.Errorf("attachment not found")
	}
	return absFile, nil
}
