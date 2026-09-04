import { baseApi } from "./baseApi";

export interface SessionUser {
	id: string;
	username: string;
	email?: string;
	role: string;
	status?: string;
	budget: number;
	rate_limit: number;
	allowed_prompt_repos?: string;
	allowed_sections?: string;
	created_at: string;
}

export interface SessionUserPayload {
	username: string;
	email?: string;
	password?: string;
	role: string;
	budget?: number;
	rate_limit?: number;
	allowed_prompt_repos?: string;
	allowed_sections?: string;
}

export const sessionUsersApi = baseApi.injectEndpoints({
	overrideExisting: false,
	endpoints: (builder) => ({
		getSessionUsers: builder.query<SessionUser[], void>({
			query: () => ({ url: "/session/users" }),
			providesTags: ["Users"],
		}),
		createSessionUser: builder.mutation<SessionUser, SessionUserPayload>({
			query: (body) => ({ url: "/session/users", method: "POST", body }),
			invalidatesTags: ["Users"],
		}),
		updateSessionUser: builder.mutation<SessionUser, { id: string; updates: SessionUserPayload }>({
			query: ({ id, updates }) => ({ url: `/session/users/${id}`, method: "PUT", body: updates }),
			invalidatesTags: ["Users"],
		}),
		deleteSessionUser: builder.mutation<void, string>({
			query: (id) => ({ url: `/session/users/${id}`, method: "DELETE" }),
			invalidatesTags: ["Users"],
		}),
		approveSessionUser: builder.mutation<void, string>({
			query: (id) => ({ url: `/session/users/${id}/approve`, method: "POST" }),
			invalidatesTags: ["Users"],
		}),
		rejectSessionUser: builder.mutation<void, string>({
			query: (id) => ({ url: `/session/users/${id}/reject`, method: "POST" }),
			invalidatesTags: ["Users"],
		}),
	}),
});

export const {
	useGetSessionUsersQuery,
	useCreateSessionUserMutation,
	useUpdateSessionUserMutation,
	useDeleteSessionUserMutation,
	useApproveSessionUserMutation,
	useRejectSessionUserMutation,
} = sessionUsersApi;
