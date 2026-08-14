import { ConnectorConfig } from "@enterprise/lib/types/workspace";
import { baseApi } from "@/lib/store/apis/baseApi";

export const connectorsApi = baseApi.injectEndpoints({
	endpoints: (builder) => ({
		getConnector: builder.query<ConnectorConfig, string>({
			query: (name) => ({ url: `/connectors/${name}` }),
			providesTags: (_result, _error, name) => [{ type: "Connectors", id: name }],
		}),
		updateConnector: builder.mutation<ConnectorConfig, ConnectorConfig>({
			query: ({ name, ...body }) => ({ url: `/connectors/${name}`, method: "PUT", body: { name, ...body } }),
			invalidatesTags: (_result, _error, arg) => [{ type: "Connectors", id: arg.name }],
		}),
	}),
});

export const { useGetConnectorQuery, useUpdateConnectorMutation } = connectorsApi;
