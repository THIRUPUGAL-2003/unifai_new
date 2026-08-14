import { isRateLimitMessage, shortenRateLimitMessage } from "@/lib/constants/logs";
import { Message } from "@/lib/message";
import { cn } from "@/lib/utils";
import { AlertCircle, AlertTriangle, XIcon } from "lucide-react";

/**
 * Render a styled error or warning message block with an optional delete control.
 *
 * @param message - The message object whose `content` is displayed inside the block.
 * @param disabled - When true, the remove button is not rendered.
 * @param onRemove - Callback invoked when the delete button is clicked.
 * @returns The React element that displays the error or warning message view.
 */
export default function ErrorMessageView({ message, disabled, onRemove }: { message: Message; disabled?: boolean; onRemove?: () => void }) {
	const isWarning = isRateLimitMessage(message.content);
	const Icon = isWarning ? AlertTriangle : AlertCircle;
	const text = isWarning ? shortenRateLimitMessage(message.content) : message.content;

	return (
		<div
			className={cn(
				"group rounded-sm border border-transparent transition-colors",
				isWarning
					? "hover:border-amber-500/30 focus-within:border-amber-500/30"
					: "px-3 py-2 hover:border-destructive/30 focus-within:border-destructive/30",
			)}
		>
			{isWarning ? (
				<div className="flex items-center gap-2 rounded-md border border-amber-500/25 bg-amber-500/10 px-2.5 py-1.5">
					<Icon className="size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
					<p className="min-w-0 flex-1 text-xs leading-snug text-amber-800 dark:text-amber-200">{text}</p>
					{!disabled && onRemove && (
						<button
							type="button"
							aria-label="Delete message"
							data-testid="error-msg-delete"
							onClick={onRemove}
							className="hover:bg-amber-500/15 focus:bg-amber-500/15 rounded-sm p-0.5 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 focus:opacity-100"
						>
							<XIcon className="text-muted-foreground hover:text-foreground size-3 shrink-0 cursor-pointer" />
						</button>
					)}
				</div>
			) : (
				<>
					<div className="mb-1 flex h-5 items-center">
						<span className="text-destructive flex items-center gap-1 py-0.5 text-xs font-medium uppercase">
							<Icon className="size-3" />
							Error
						</span>
						<div className="ml-auto">
							{!disabled && onRemove && (
								<button
									type="button"
									aria-label="Delete message"
									data-testid="error-msg-delete"
									onClick={onRemove}
									className="hover:bg-muted focus:bg-muted rounded-sm p-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 focus:opacity-100"
								>
									<XIcon className="text-muted-foreground hover:text-foreground size-3 shrink-0 cursor-pointer" />
								</button>
							)}
						</div>
					</div>
					<div className="bg-destructive/10 rounded-sm px-2.5 py-1.5">
						<p className="text-muted-foreground text-sm whitespace-pre-wrap">{text}</p>
					</div>
				</>
			)}
		</div>
	);
}
