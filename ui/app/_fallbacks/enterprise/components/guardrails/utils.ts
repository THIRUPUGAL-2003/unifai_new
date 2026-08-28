import { toast } from "sonner";
import type {
	GuardrailProvider,
	GuardrailRule,
	GuardrailsConfig,
	GuardrailsUpdateResult,
} from "@/lib/store/apis/guardrailsApi";
import { normalizeGuardrailsConfig } from "@/lib/store/apis/guardrailsApi";

export function nextGuardrailId(existingIds: number[]): number {
	if (existingIds.length === 0) {
		return 1;
	}
	return Math.max(...existingIds) + 1;
}

export function collectGuardrailIds(rules: GuardrailRule[], providers: GuardrailProvider[]): number[] {
	const ids = new Set<number>();
	for (const rule of rules) {
		ids.add(rule.id);
	}
	for (const provider of providers) {
		ids.add(provider.id);
	}
	return Array.from(ids);
}

export function providerLabel(provider: GuardrailProvider): string {
	return `${provider.policy_name} (#${provider.id})`;
}

export function formatLinkedProviders(rule: GuardrailRule, providers: GuardrailProvider[]): string {
	const linked = (rule.provider_config_ids || [])
		.map((id) => providers.find((provider) => provider.id === id))
		.filter((provider): provider is GuardrailProvider => provider != null)
		.map((provider) => provider.policy_name);

	if (linked.length === 0) {
		return "None";
	}
	return linked.join(", ");
}

export function formatRuleModels(rule: GuardrailRule): string {
	const models = (rule.models || []).filter((model) => model.trim() !== "");
	if (models.length === 0 || models.includes("*")) {
		return "All models";
	}
	if (models.length <= 2) {
		return models.join(", ");
	}
	return `${models.slice(0, 2).join(", ")} +${models.length - 2}`;
}

export function normalizeRuleModels(models?: string[]): string[] {
	const next = (models || []).filter((model) => model.trim() !== "");
	if (next.includes("*")) {
		return ["*"];
	}
	return next;
}

export function mergeGuardrailsConfig(
	config: GuardrailsConfig | undefined,
	patch: Partial<GuardrailsConfig>,
): GuardrailsConfig {
	const current = normalizeGuardrailsConfig(config);
	return {
		guardrail_rules: patch.guardrail_rules ?? current.guardrail_rules,
		guardrail_providers: patch.guardrail_providers ?? current.guardrail_providers,
	};
}

export function toastGuardrailsSave(message: string, result?: GuardrailsUpdateResult | null) {
	toast.success(message);
	if (result?.persisted === false) {
		toast.warning("Saved for this session only. Disk write failed — this change is lost if the container restarts.");
	}
}
