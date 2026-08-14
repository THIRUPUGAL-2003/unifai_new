import { baseApi } from "./baseApi";

export interface GuardrailRule {
	id: number;
	name: string;
	description: string;
	cel_expression: string;
	apply_to: "input" | "output" | "both";
	enabled: boolean;
	provider_config_ids: number[]; // List of provider IDs
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

export const guardrailsApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		getGuardrailsConfig: builder.query<GuardrailsConfig, void>({
			query: () => ({
				url: "/guardrails/config",
			}),
			providesTags: ["GuardrailsConfig" as any], // Cast as any if TagTypes doesn't have GuardrailsConfig yet
		}),
		updateGuardrailsConfig: builder.mutation<null, GuardrailsConfig>({
			query: (data) => ({
				url: "/guardrails/config",
				method: "PUT",
				body: data,
			}),
			invalidatesTags: ["GuardrailsConfig" as any],
		}),
	}),
});

export const { useGetGuardrailsConfigQuery, useUpdateGuardrailsConfigMutation } = guardrailsApi;
