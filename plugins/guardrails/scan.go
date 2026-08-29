package guardrails

import (
	"github.com/unifai/unifai/core/schemas"
)

func collectRequestTexts(req *schemas.UnifAIRequest) []string {
	if req == nil {
		return nil
	}
	var texts []string
	if req.ChatRequest != nil {
		for i := range req.ChatRequest.Input {
			texts = append(texts, chatMessageTexts(&req.ChatRequest.Input[i])...)
		}
	}
	if req.ResponsesRequest != nil {
		for i := range req.ResponsesRequest.Input {
			texts = append(texts, responsesMessageTexts(&req.ResponsesRequest.Input[i])...)
		}
	}
	if req.TextCompletionRequest != nil && req.TextCompletionRequest.Input != nil {
		in := req.TextCompletionRequest.Input
		if in.PromptStr != nil {
			texts = append(texts, *in.PromptStr)
		}
		texts = append(texts, in.PromptArray...)
	}
	return texts
}

func collectResponseTexts(resp *schemas.UnifAIResponse) []string {
	if resp == nil {
		return nil
	}
	var texts []string
	if resp.ChatResponse != nil {
		for _, choice := range resp.ChatResponse.Choices {
			if choice.ChatNonStreamResponseChoice != nil && choice.ChatNonStreamResponseChoice.Message != nil {
				texts = append(texts, chatMessageTexts(choice.ChatNonStreamResponseChoice.Message)...)
			}
			if choice.ChatStreamResponseChoice != nil && choice.ChatStreamResponseChoice.Delta != nil {
				d := choice.ChatStreamResponseChoice.Delta
				if d.Content != nil {
					texts = append(texts, *d.Content)
				}
				if d.Refusal != nil {
					texts = append(texts, *d.Refusal)
				}
			}
		}
	}
	if resp.ResponsesResponse != nil {
		for i := range resp.ResponsesResponse.Output {
			texts = append(texts, responsesMessageTexts(&resp.ResponsesResponse.Output[i])...)
		}
	}
	if resp.TextCompletionResponse != nil {
		for _, choice := range resp.TextCompletionResponse.Choices {
			if choice.TextCompletionResponseChoice != nil && choice.TextCompletionResponseChoice.Text != nil {
				texts = append(texts, *choice.TextCompletionResponseChoice.Text)
			}
		}
	}
	return texts
}

func chatMessageTexts(msg *schemas.ChatMessage) []string {
	if msg == nil || msg.Content == nil {
		return nil
	}
	var texts []string
	if msg.Content.ContentStr != nil {
		texts = append(texts, *msg.Content.ContentStr)
	}
	for _, block := range msg.Content.ContentBlocks {
		if block.Text != nil {
			texts = append(texts, *block.Text)
		}
		if block.Refusal != nil {
			texts = append(texts, *block.Refusal)
		}
	}
	return texts
}

func responsesMessageTexts(msg *schemas.ResponsesMessage) []string {
	if msg == nil || msg.Content == nil {
		return nil
	}
	var texts []string
	if msg.Content.ContentStr != nil {
		texts = append(texts, *msg.Content.ContentStr)
	}
	for _, block := range msg.Content.ContentBlocks {
		if block.Text != nil {
			texts = append(texts, *block.Text)
		}
	}
	return texts
}
