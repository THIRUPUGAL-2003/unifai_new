import type { GuardrailProvider, GuardrailRule, GuardrailsConfig } from "@/lib/store/apis/guardrailsApi";

export function mergeGuardrailsConfig(
	config: GuardrailsConfig | undefined,
	patch: Partial<GuardrailsConfig>,
): GuardrailsConfig {
	return {
		guardrail_rules: patch.guardrail_rules ?? config?.guardrail_rules ?? [],
		guardrail_providers: patch.guardrail_providers ?? config?.guardrail_providers ?? [],
	};
}

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
