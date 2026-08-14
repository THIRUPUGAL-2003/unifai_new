import { baseApi } from "./baseApi";

export interface BrowserAILogEntry {
	id: string;
	timestamp: string;
	platform: string;
	user_prompt_preview: string;
	user_prompt_full: string;
	est_tokens: number;
	client_ip: string;
	agent_id?: string;
	agent_hostname?: string;
	status: string;
	action: string;
	rule_triggered?: string;
	risk_score?: number;
	predictive_risk?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
	predicted_category?: string;
	reply_bot_provider?: string;
	reply_bot_model?: string;
	reply_bot_text?: string;
	metadata?: string;
	created_at: string;
}

export interface BrowserAIAgent {
	id: string;
	hostname: string;
	username: string;
	ip_address: string;
	mac_address?: string;
	transport_name?: string;
	os_version: string;
	agent_version: string;
	status: "active" | "inactive" | "sleep" | "shutdown" | "uninstalled" | string;
	last_seen_at: string;
	installed_at: string;
	uninstalled_at?: string;
	created_at: string;
	updated_at: string;
}

export interface BrowserAIAgentSettings {
	id: string;
	require_uninstall_key: boolean;
	key_configured: boolean;
	updated_at: string;
	updated_by: string;
}

export interface BrowserGuardRule {
	id: string;
	name: string;
	severity: "CRITICAL" | "HIGH" | "MEDIUM";
	action: "BLOCK" | "WARN" | "REDACT";
	pattern: string;
	active: boolean;
	description: string;
	warning_message?: string;
	created_at?: string;
}

export interface BrowserControlSettings {
	id: string;
	enabled: boolean;
	block_upload: boolean;
	upload_warning?: string;
	updated_at?: string;
}

export interface BrowserTargetWebsite {
	id: string;
	domain: string;
	platform_name: string;
	monitored: boolean;
	/** When true, Guard blocks opening the whole website (not only prompts). */
	block_site?: boolean;
	intercepted_count: number;
	status: string;
	reply_bot_enabled?: boolean;
	reply_bot_provider?: string;
	reply_bot_model?: string;
	/** "violations" (default) | "all" */
	reply_bot_mode?: string;
	/** Related host nested under this parent Target Website. Empty = top-level domain. */
	parent_id?: string;
	created_at?: string;
}

export const browserAiApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		getBrowserAiLogs: builder.query<
			{ logs: BrowserAILogEntry[]; total: number; limit: number; offset: number },
			{ platform?: string; status?: string; action?: string; search?: string; limit?: number; offset?: number } | void
		>({
			query: (params) => ({
				url: "/browser-ai/logs",
				params: params || {},
			}),
			providesTags: ["BrowserAiLogs" as any],
		}),

		clearBrowserAiLogs: builder.mutation<void, void>({
			query: () => ({
				url: "/browser-ai/logs",
				method: "DELETE",
			}),
			invalidatesTags: ["BrowserAiLogs" as any],
		}),

		getBrowserAiRules: builder.query<{ rules: BrowserGuardRule[] }, void>({
			query: () => "/browser-ai/rules",
			providesTags: ["BrowserAiRules" as any],
		}),

		createBrowserAiRule: builder.mutation<{ status: string; rule: BrowserGuardRule }, Partial<BrowserGuardRule>>({
			query: (body) => ({
				url: "/browser-ai/rules",
				method: "POST",
				body,
			}),
			invalidatesTags: ["BrowserAiRules" as any],
		}),

		updateBrowserAiRule: builder.mutation<{ status: string }, { id: string; updates: Partial<BrowserGuardRule> }>({
			query: ({ id, updates }) => ({
				url: `/browser-ai/rules/${id}`,
				method: "PUT",
				body: updates,
			}),
			invalidatesTags: ["BrowserAiRules" as any],
		}),

		deleteBrowserAiRule: builder.mutation<{ status: string }, string>({
			query: (id) => ({
				url: `/browser-ai/rules/${id}`,
				method: "DELETE",
			}),
			invalidatesTags: ["BrowserAiRules" as any],
		}),

		getBrowserAiControls: builder.query<{ controls: BrowserControlSettings }, void>({
			query: () => "/browser-ai/controls",
			providesTags: ["BrowserAiControls" as any],
		}),

		updateBrowserAiControls: builder.mutation<{ status: string; controls: BrowserControlSettings }, Partial<BrowserControlSettings>>({
			query: (body) => ({
				url: "/browser-ai/controls",
				method: "PUT",
				body,
			}),
			invalidatesTags: ["BrowserAiControls" as any],
		}),

		getBrowserAiTargets: builder.query<{ targets: BrowserTargetWebsite[] }, void>({
			query: () => "/browser-ai/targets",
			providesTags: ["BrowserAiTargets" as any],
		}),

		createBrowserAiTarget: builder.mutation<{ status: string; target: BrowserTargetWebsite }, Partial<BrowserTargetWebsite>>({
			query: (body) => ({
				url: "/browser-ai/targets",
				method: "POST",
				body,
			}),
			invalidatesTags: ["BrowserAiTargets" as any],
		}),

		updateBrowserAiTarget: builder.mutation<{ status: string }, { id: string; updates: Partial<BrowserTargetWebsite> }>({
			query: ({ id, updates }) => ({
				url: `/browser-ai/targets/${id}`,
				method: "PUT",
				body: updates,
			}),
			invalidatesTags: ["BrowserAiTargets" as any],
		}),

		deleteBrowserAiTarget: builder.mutation<{ status: string }, string>({
			query: (id) => ({
				url: `/browser-ai/targets/${id}`,
				method: "DELETE",
			}),
			invalidatesTags: ["BrowserAiTargets" as any],
		}),

		getBrowserAiAgents: builder.query<
			{ agents: BrowserAIAgent[]; total: number; limit: number; offset: number },
			{ status?: string; search?: string; limit?: number; offset?: number } | void
		>({
			query: (params) => ({
				url: "/browser-ai/agents",
				params: params || {},
			}),
			providesTags: ["BrowserAiAgents" as any],
		}),

		getBrowserAiAgentSettings: builder.query<{ settings: BrowserAIAgentSettings }, void>({
			query: () => "/browser-ai/agents/settings",
			providesTags: ["BrowserAiAgentSettings" as any],
		}),

		saveBrowserAiUninstallKey: builder.mutation<
			{ status: string; settings: BrowserAIAgentSettings },
			{ key?: string; require_uninstall_key?: boolean; updated_by?: string }
		>({
			query: (body) => ({
				url: "/browser-ai/agents/uninstall-key",
				method: "PUT",
				body,
			}),
			invalidatesTags: ["BrowserAiAgentSettings" as any],
		}),
	}),
});

export const {
	useGetBrowserAiLogsQuery,
	useClearBrowserAiLogsMutation,
	useGetBrowserAiRulesQuery,
	useCreateBrowserAiRuleMutation,
	useUpdateBrowserAiRuleMutation,
	useDeleteBrowserAiRuleMutation,
	useGetBrowserAiControlsQuery,
	useUpdateBrowserAiControlsMutation,
	useGetBrowserAiTargetsQuery,
	useCreateBrowserAiTargetMutation,
	useUpdateBrowserAiTargetMutation,
	useDeleteBrowserAiTargetMutation,
	useGetBrowserAiAgentsQuery,
	useGetBrowserAiAgentSettingsQuery,
	useSaveBrowserAiUninstallKeyMutation,
} = browserAiApi;
