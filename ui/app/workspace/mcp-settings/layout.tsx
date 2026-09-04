import { createFileRoute } from "@tanstack/react-router";
import { NoPermissionView } from "@/components/noPermissionView";
import { RbacOperation, RbacResource, useRbac } from "@enterprise/lib";
import MCPSettingsPage from "./page";

function RouteComponent() {
	// MCP Settings is under MCP Gateway — require MCPGateway update only (not Settings AND).
	const hasMCPGatewayAccess = useRbac(RbacResource.MCPGateway, RbacOperation.Update);
	if (!hasMCPGatewayAccess) {
		return <NoPermissionView entity="MCP gateway settings" />;
	}
	return <MCPSettingsPage />;
}

export const Route = createFileRoute("/workspace/mcp-settings")({
	component: RouteComponent,
});