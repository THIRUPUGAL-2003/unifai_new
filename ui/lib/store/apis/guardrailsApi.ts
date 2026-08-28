import { baseApi } from "./baseApi";

export interface GuardrailRule {
	id: number;
	name: string;
	description: string;
	cel_expression: string;
	apply_to: "input" | "output" | "both";
	enabled: boolean;
	provider_config_ids: number[]; // List of provider IDs
	models?: string[]; // Empty or ["*"] = all models
}

export interface GuardrailProvider {
	id: number;
	provider_name: "regex";
	policy_name: string;
	enabled: boolean;
	config: Record<string, any>;
}

export interface GuardrailsConfig {
	guardrail_rules: GuardrailRule[];
	guardrail_providers: GuardrailProvider[];
}

export interface GuardrailsUpdateResult {
	success?: boolean;
	persisted?: boolean;
	reloaded?: boolean;
}

export function emptyGuardrailsConfig(): GuardrailsConfig {
	return { guardrail_rules: [], guardrail_providers: [] };
}

export function normalizeGuardrailsConfig(config?: Partial<GuardrailsConfig> | null): GuardrailsConfig {
	return {
		guardrail_rules: config?.guardrail_rules ?? [],
		guardrail_providers: config?.guardrail_providers ?? [],
	};
}

export const guardrailsApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		getGuardrailsConfig: builder.query<GuardrailsConfig, void>({
			query: () => ({
				url: "/guardrails/config",
			}),
			transformResponse: (response: GuardrailsConfig | null) => normalizeGuardrailsConfig(response),
			providesTags: ["Guardrails"],
		}),
		updateGuardrailsConfig: builder.mutation<GuardrailsUpdateResult, GuardrailsConfig>({
			query: (data) => ({
				url: "/guardrails/config",
				method: "PUT",
				body: normalizeGuardrailsConfig(data),
			}),
			invalidatesTags: ["Guardrails"],
		}),
	}),
});

export const { useGetGuardrailsConfigQuery, useUpdateGuardrailsConfigMutation } = guardrailsApi;
