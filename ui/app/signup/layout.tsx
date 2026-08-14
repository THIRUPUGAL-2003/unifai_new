import { ThemeProvider } from "@/components/themeProvider";
import { ReduxProvider } from "@/lib/store/provider";
import { createFileRoute } from "@tanstack/react-router";
import { NuqsAdapter } from "nuqs/adapters/tanstack-router";
import SignupPage from "./page";

function RouteComponent() {
	return (
		<ThemeProvider attribute="class" defaultTheme="system" enableSystem>
			<ReduxProvider>
				<NuqsAdapter>
					<div className="bg-background min-h-screen">
						<SignupPage />
					</div>
				</NuqsAdapter>
			</ReduxProvider>
		</ThemeProvider>
	);
}

export const Route = createFileRoute("/signup")({
	component: RouteComponent,
});
