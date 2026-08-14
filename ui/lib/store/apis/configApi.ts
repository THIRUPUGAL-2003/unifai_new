import { UnifAIConfig, GlobalProxyConfig, LatestReleaseResponse } from "@/lib/types/config";
import axios from "axios";
import { baseApi } from "./baseApi";

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
	typeof value === "object" && value !== null && !Array.isArray(value);

const applyMetadataPatch = (metadata: UnifAIConfig["metadata"] | undefined, patch: Record<string, unknown>): Record<string, unknown> => {
	const next = { ...(metadata ?? {}) };
	Object.entries(patch).forEach(([key, value]) => {
		if (value === null) {
			delete next[key];
			return;
		}
		const currentValue = next[key];
		next[key] = isPlainObject(value) && isPlainObject(currentValue) ? applyMetadataPatch(currentValue, value) : value;
	});
	return next;
};

export const configApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		// Get core configuration
		getCoreConfig: builder.query<UnifAIConfig, { fromDB?: boolean }>({
			query: ({ fromDB = false } = {}) => ({
				url: "/config",
				params: { from_db: fromDB },
			}),
			providesTags: ["Config"],
		}),

		// Get version information
		getVersion: builder.query<string, void>({
			query: () => ({
				url: "/version",
			}),
		}),

		// Get latest release from public site
		getLatestRelease: builder.query<LatestReleaseResponse, void>({
			queryFn: async () => {
				return { data: { name: "", changelogUrl: "" } };
			},
		}),
		// Update core configuration
		updateCoreConfig: builder.mutation<null, UnifAIConfig>({
			query: (data) => ({
				url: "/config",
				method: "PUT",
				body: data,
			}),
			invalidatesTags: ["Config"],
		}),

		// Update proxy configuration
		updateProxyConfig: builder.mutation<null, GlobalProxyConfig>({
			query: (data) => ({
				url: "/proxy-config",
				method: "PUT",
				body: data,
			}),
			invalidatesTags: ["Config"],
		}),

		// Force a pricing sync immediately
		forcePricingSync: builder.mutation<null, void>({
			query: () => ({
				url: "/pricing/force-sync",
				method: "POST",
			}),
			invalidatesTags: ["Config"],
		}),

		// Merge-patch the ClientConfig.metadata UI/admin preferences blob.
		// Pass {key: null} to remove a key.
		updateClientMetadata: builder.mutation<{ success: boolean }, Record<string, unknown>>({
			query: (patch) => ({
				url: "/config/metadata",
				method: "POST",
				body: patch,
			}),
			async onQueryStarted(patch, { dispatch, queryFulfilled }) {
				const patchResults = [
					dispatch(
						configApi.util.updateQueryData("getCoreConfig", {}, (draft) => {
							draft.metadata = applyMetadataPatch(draft.metadata, patch);
						}),
					),
					dispatch(
						configApi.util.updateQueryData("getCoreConfig", { fromDB: true }, (draft) => {
							draft.metadata = applyMetadataPatch(draft.metadata, patch);
						}),
					),
				];
				try {
					await queryFulfilled;
				} catch {
					patchResults.forEach((patchResult) => patchResult.undo());
				}
			},
		}),
	}),
});

export const {
	useGetVersionQuery,
	useGetCoreConfigQuery,
	useUpdateCoreConfigMutation,
	useUpdateProxyConfigMutation,
	useForcePricingSyncMutation,
	useUpdateClientMetadataMutation,
	useLazyGetCoreConfigQuery,
	useGetLatestReleaseQuery,
	useLazyGetLatestReleaseQuery,
} = configApi;