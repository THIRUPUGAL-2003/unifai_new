import { AlertTriangle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scrollArea";
import { useGetVirtualKeysQuery, useIsAuthEnabledQuery } from "@/lib/store";
import { MessagesView } from "../components/messagesView/rootMessageView";
import { NewMessageInputView } from "../components/newMessageInputView";

export function PlaygroundPanel() {
	const { data: authStatus } = useIsAuthEnabledQuery();
	const isMemberOnly = Boolean(authStatus?.role && authStatus.role !== "admin");
	const { data: virtualKeysData, isLoading: vksLoading } = useGetVirtualKeysQuery(undefined, {
		skip: !isMemberOnly,
	});
	const assignedVKs = virtualKeysData?.virtual_keys ?? [];
	const showNoVkBanner = isMemberOnly && !vksLoading && assignedVKs.length === 0;

	return (
		<div className="custom-scrollbar relative flex h-full flex-col overscroll-none">
			{showNoVkBanner ? (
				<div
					className="border-destructive/40 bg-destructive/10 text-destructive mx-4 mt-3 flex items-start gap-2 rounded-md border px-3 py-2 text-sm"
					data-testid="prompt-repo-no-vk-banner"
				>
					<AlertTriangle className="mt-0.5 size-4 shrink-0" />
					<div>
						<p className="font-medium">No Virtual Key assigned</p>
						<p className="text-destructive/90 text-xs">
							You can open prompts, but chat will not run until an admin assigns a Virtual Key to your user
							(Governance → Users → Edit, or Virtual Keys → Assigned user).
						</p>
					</div>
				</div>
			) : null}
			<ScrollArea className="flex-1 scroll-mb-12 overflow-y-auto" viewportClassName="no-table">
				<MessagesView />
			</ScrollArea>
			<NewMessageInputView />
		</div>
	);
}
