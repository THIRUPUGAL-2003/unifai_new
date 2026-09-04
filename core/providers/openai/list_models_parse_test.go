package openai

import (
	"testing"
)

func TestParseOpenAIListModelsBody_ObjectEnvelope(t *testing.T) {
	body := []byte(`{"object":"list","data":[{"id":"gpt-4","object":"model","owned_by":"openai"}]}`)
	out, err := parseOpenAIListModelsBody(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(out.Data) != 1 || out.Data[0].ID != "gpt-4" {
		t.Fatalf("unexpected: %+v", out)
	}
}

func TestParseOpenAIListModelsBody_BareArray(t *testing.T) {
	// Together AI style
	body := []byte(`[{"id":"meta-llama/Llama-3","object":"model","organization":"Meta","context_length":8192,"created":1,"type":"chat"}]`)
	out, err := parseOpenAIListModelsBody(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(out.Data) != 1 || out.Data[0].ID != "meta-llama/Llama-3" {
		t.Fatalf("unexpected: %+v", out)
	}
	if out.Data[0].Organization != "Meta" {
		t.Fatalf("organization not parsed: %+v", out.Data[0])
	}
}
