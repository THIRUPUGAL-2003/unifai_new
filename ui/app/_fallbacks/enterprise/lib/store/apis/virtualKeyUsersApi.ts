import { User } from "@enterprise/lib/types/user";
import { baseApi } from "@/lib/store/apis/baseApi";

export interface GetVirtualKeyUsersResponse {
	users: User[];
}

export const virtualKeyUsersApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		getVirtualKeyUsers: builder.query<GetVirtualKeyUsersResponse, string>({
			query: (vkId) => ({ url: `/governance/virtual-keys/${vkId}/users` }),
			providesTags: (_result, _error, vkId) => [{ type: "VirtualKeys", id: vkId }],
		}),
		setVirtualKeyUser: builder.mutation<GetVirtualKeyUsersResponse, { vkId: string; user_id: string }>({
			query: ({ vkId, user_id }) => ({
				url: `/governance/virtual-keys/${vkId}/users`,
				method: "PUT",
				body: { user_id },
			}),
			invalidatesTags: (_result, _error, { vkId }) => [{ type: "VirtualKeys", id: vkId }],
		}),
	}),
});

export const { useGetVirtualKeyUsersQuery, useSetVirtualKeyUserMutation } = virtualKeyUsersApi;
