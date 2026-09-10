import React from "react";
import { Paperclip } from "lucide-react";
import type { BrowserAILogEntry } from "@/lib/store/apis/browserAiApi";
import { oneLinePreview } from "./browserAiFormat";
import { isFileUploadLog, logAttachmentLabel } from "./browserAiLogHelpers";

export function LogPromptPreviewCell({ log }: { log: BrowserAILogEntry }) {
	if (isFileUploadLog(log)) {
		const label = logAttachmentLabel(log);
		return (
			<div className="flex min-w-0 items-center gap-1.5" title={label}>
				<Paperclip className="h-3.5 w-3.5 shrink-0 text-sky-400" />
				<span className="truncate font-mono text-xs">{label}</span>
			</div>
		);
	}
	let preview = oneLinePreview(log.user_prompt_preview);
	if (
		preview.includes(" | ") &&
		(preview.startsWith("[FILE UPLOAD]") || preview.startsWith("[VOICE UPLOAD]"))
	) {
		preview = preview.split(" | ")[0].trim();
	}
	return (
		<div className="truncate font-mono text-xs" title={preview || log.user_prompt_preview || ""}>
			{preview || "—"}
		</div>
	);
}
