package handlers

import (
	"strings"
	"time"

	"github.com/bytedance/sonic"
	"github.com/unifai/unifai/framework/logstore"
	"github.com/valyala/fasthttp"
)

func (h *BrowserAIHandler) getRules(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	rules, err := h.manager.GetRules(ctx)
	if err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	forAgent := strings.EqualFold(string(ctx.QueryArgs().Peek("for")), "agent")
	if forAgent {
		out := make([]map[string]any, 0, len(rules))
		hasAIBot := false
		for _, r := range rules {
			if !r.Active {
				continue
			}
			rt := strings.ToLower(strings.TrimSpace(r.RuleType))
			if rt == "ai_bot" {
				hasAIBot = true
			}
			// Lite payload: pattern + action for local regex. Skip huge bot_prompt blobs.
			row := map[string]any{
				"id":              r.ID,
				"name":            r.Name,
				"rule_type":       r.RuleType,
				"pattern":         r.Pattern,
				"action":          r.Action,
				"severity":        r.Severity,
				"warning_message": r.WarningMessage,
				"active":          true,
			}
			if rt == "ai_bot" {
				row["bot_provider"] = r.BotProvider
				row["bot_model"] = r.BotModel
				// Intentionally omit bot_prompt / reference image — agent only needs has_ai_bot.
			}
			out = append(out, row)
		}
		SendJSON(ctx, map[string]any{"rules": out, "has_ai_bot": hasAIBot})
		return
	}
	SendJSON(ctx, map[string]any{"rules": rules})
}

func (h *BrowserAIHandler) getOllamaModels(ctx *fasthttp.RequestCtx) {
	models, baseURL, err := listOllamaInstalledModels(10 * time.Second)
	if err != nil {
		SendError(ctx, fasthttp.StatusBadGateway, err.Error())
		return
	}
	SendJSON(ctx, map[string]any{
		"models":   models,
		"base_url": baseURL,
	})
}

func (h *BrowserAIHandler) createRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	var rule logstore.BrowserGuardRule
	if err := sonic.Unmarshal(ctx.PostBody(), &rule); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}
	if strings.TrimSpace(rule.Name) == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Rule name is required")
		return
	}
	if strings.ToLower(rule.RuleType) == "ai_bot" {
		applyAIBotDefaults(&rule)
		if err := validateAIBotRuleFields(&rule); err != nil {
			SendError(ctx, fasthttp.StatusBadRequest, err.Error())
			return
		}
	} else {
		rule.RuleType = "regex"
		if strings.TrimSpace(rule.Pattern) == "" {
			SendError(ctx, fasthttp.StatusBadRequest, "Regex pattern is required for Regex rule")
			return
		}
	}
	if err := h.manager.CreateRule(ctx, &rule); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	h.invalidateRulesCache()
	SendJSON(ctx, map[string]any{"status": "success", "rule": rule})
}

func (h *BrowserAIHandler) updateRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing rule ID")
		return
	}
	var updates map[string]any
	if err := sonic.Unmarshal(ctx.PostBody(), &updates); err != nil {
		SendError(ctx, fasthttp.StatusBadRequest, "Invalid JSON payload")
		return
	}

	// Validate AI Guard Bot fields for the resulting rule (including partial updates).
	ruleType := ""
	if v, ok := updates["rule_type"].(string); ok {
		ruleType = strings.ToLower(strings.TrimSpace(v))
	}
	_, hasBotPrompt := updates["bot_prompt"]
	_, hasBotProvider := updates["bot_provider"]
	_, hasBotModel := updates["bot_model"]
	_, hasBotReferenceImage := updates["bot_reference_image"]
	_, hasBotReferenceImageType := updates["bot_reference_image_type"]
	needsAIBotCheck := ruleType == "ai_bot" || hasBotPrompt || hasBotProvider || hasBotModel || hasBotReferenceImage || hasBotReferenceImageType
	if needsAIBotCheck {
		if existingRules, getErr := h.manager.GetRules(ctx); getErr == nil {
			for i := range existingRules {
				if existingRules[i].ID != id {
					continue
				}
				existing := existingRules[i]
				if ruleType == "" {
					ruleType = strings.ToLower(strings.TrimSpace(existing.RuleType))
				}
				if !hasBotPrompt {
					updates["bot_prompt"] = existing.BotPrompt
				}
				if !hasBotProvider {
					updates["bot_provider"] = existing.BotProvider
				}
				if !hasBotModel {
					updates["bot_model"] = existing.BotModel
				}
				if !hasBotReferenceImage {
					updates["bot_reference_image"] = existing.BotReferenceImage
				}
				if !hasBotReferenceImageType {
					updates["bot_reference_image_type"] = existing.BotReferenceImageType
				}
				break
			}
		}
	}
	if ruleType == "ai_bot" {
		tmp := logstore.BrowserGuardRule{
			RuleType:              "ai_bot",
			BotProvider:           stringFromUpdate(updates, "bot_provider"),
			BotModel:              stringFromUpdate(updates, "bot_model"),
			BotPrompt:             stringFromUpdate(updates, "bot_prompt"),
			BotReferenceImage:     stringFromUpdate(updates, "bot_reference_image"),
			BotReferenceImageType: stringFromUpdate(updates, "bot_reference_image_type"),
		}
		if err := validateAIBotRuleFields(&tmp); err != nil {
			SendError(ctx, fasthttp.StatusBadRequest, err.Error())
			return
		}
		updates["bot_provider"] = tmp.BotProvider
		updates["bot_model"] = tmp.BotModel
		updates["bot_prompt"] = tmp.BotPrompt
		updates["bot_reference_image"] = tmp.BotReferenceImage
		updates["bot_reference_image_type"] = tmp.BotReferenceImageType
	}

	if err := h.manager.UpdateRule(ctx, id, updates); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	h.invalidateRulesCache()
	SendJSON(ctx, map[string]any{"status": "success"})
}

func (h *BrowserAIHandler) deleteRule(ctx *fasthttp.RequestCtx) {
	h.ensureDB(ctx)
	id, ok := ctx.UserValue("id").(string)
	if !ok || id == "" {
		SendError(ctx, fasthttp.StatusBadRequest, "Missing rule ID")
		return
	}
	if err := h.manager.DeleteRule(ctx, id); err != nil {
		SendError(ctx, fasthttp.StatusInternalServerError, err.Error())
		return
	}
	h.invalidateRulesCache()
	SendJSON(ctx, map[string]any{"status": "success"})
}
