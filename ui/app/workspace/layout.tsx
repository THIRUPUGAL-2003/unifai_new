import FullPageLoader from "@/components/fullPageLoader";
import { fetchSessionAuth, getWorkspaceAccessRedirect } from "@/lib/utils/workspaceAccess";
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { ClientLayout } from "../clientLayout";

function WorkspaceLayout({ children }: { children: React.ReactNode }) {
	return <ClientLayout>{children}</ClientLayout>;
}

function RouteComponent() {
	return (
		<WorkspaceLayout>
			<Outlet />
		</WorkspaceLayout>
	);
}

function PendingComponent() {
	return <FullPageLoader />;
}

export const Route = createFileRoute("/workspace")({
	beforeLoad: async ({ location }) => {
		const auth = await fetchSessionAuth();
		const redirectTo = getWorkspaceAccessRedirect(auth, location.pathname);
		if (redirectTo) {
			throw redirect({ to: redirectTo, replace: true });
		}
	},
	pendingComponent: PendingComponent,
	pendingMs: 800,
	component: RouteComponent,
});
