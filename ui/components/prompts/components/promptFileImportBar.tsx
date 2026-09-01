import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { MessageContent } from "@/lib/message";
import { Mic, Paperclip, Square } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { fileToAttachment, filesToAttachments, PROMPT_FILE_ACCEPT, PROMPT_FILE_ACCEPT_LABEL } from "../utils/attachment";

interface PromptFileImportBarProps {
	disabled?: boolean;
	onAttachmentsAdded: (attachments: MessageContent[]) => void;
	className?: string;
	compact?: boolean;
}

export function PromptFileImportBar({ disabled, onAttachmentsAdded, className = "", compact = false }: PromptFileImportBarProps) {
	const fileInputRef = useRef<HTMLInputElement>(null);
	const [isRecording, setIsRecording] = useState(false);
	const mediaRecorderRef = useRef<MediaRecorder | null>(null);
	const mediaStreamRef = useRef<MediaStream | null>(null);
	const audioChunksRef = useRef<Blob[]>([]);

	const addFiles = useCallback(
		async (files: FileList | File[]) => {
			const attachments = await filesToAttachments(files);
			if (attachments.length > 0) {
				onAttachmentsAdded(attachments);
			}
		},
		[onAttachmentsAdded],
	);

	const stopRecording = useCallback(() => {
		mediaRecorderRef.current?.stop();
		mediaRecorderRef.current = null;
	}, []);

	const startRecording = useCallback(async () => {
		if (!navigator.mediaDevices?.getUserMedia) {
			toast.error("Voice recording is not supported in this browser");
			return;
		}
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			mediaStreamRef.current = stream;
			const recorder = new MediaRecorder(stream);
			audioChunksRef.current = [];

			recorder.ondataavailable = (event) => {
				if (event.data.size > 0) {
					audioChunksRef.current.push(event.data);
				}
			};

			recorder.onstop = async () => {
				mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
				mediaStreamRef.current = null;
				setIsRecording(false);

				const mimeType = recorder.mimeType || "audio/webm";
				const blob = new Blob(audioChunksRef.current, { type: mimeType });
				if (blob.size === 0) {
					return;
				}

				const ext = mimeType.includes("webm") ? "webm" : mimeType.includes("ogg") ? "ogg" : "wav";
				const file = new File([blob], `voice-${Date.now()}.${ext}`, { type: mimeType });
				const attachment = await fileToAttachment(file);
				if (attachment) {
					onAttachmentsAdded([attachment]);
					toast.success("Voice recording attached");
				}
			};

			recorder.start();
			mediaRecorderRef.current = recorder;
			setIsRecording(true);
		} catch {
			toast.error("Microphone access denied or unavailable");
		}
	}, [onAttachmentsAdded]);

	const toggleRecording = useCallback(() => {
		if (disabled) return;
		if (isRecording) {
			stopRecording();
			return;
		}
		void startRecording();
	}, [disabled, isRecording, startRecording, stopRecording]);

	return (
		<div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
			<input
				ref={fileInputRef}
				type="file"
				multiple
				accept={PROMPT_FILE_ACCEPT}
				className="hidden"
				onChange={(e) => {
					const files = e.target.files;
					if (files && files.length > 0) {
						void addFiles(files);
					}
					e.target.value = "";
				}}
			/>
			<Tooltip>
				<TooltipTrigger asChild>
					<Button
						type="button"
						variant="outline"
						size={compact ? "sm" : "sm"}
						disabled={disabled}
						onClick={() => fileInputRef.current?.click()}
						className={compact ? "h-7 gap-1 px-2 text-xs" : "h-8 gap-1.5 text-xs"}
						data-testid="prompt-import-files-button"
					>
						<Paperclip className="h-3.5 w-3.5" />
						{compact ? "Files" : "Import files"}
					</Button>
				</TooltipTrigger>
				<TooltipContent side="top" className="max-w-xs">
					<p>{PROMPT_FILE_ACCEPT_LABEL}</p>
				</TooltipContent>
			</Tooltip>
			<Tooltip>
				<TooltipTrigger asChild>
					<Button
						type="button"
						variant={isRecording ? "destructive" : "outline"}
						size="sm"
						disabled={disabled}
						onClick={toggleRecording}
						className={compact ? "h-7 gap-1 px-2 text-xs" : "h-8 gap-1.5 text-xs"}
						data-testid="prompt-record-voice-button"
					>
						{isRecording ? <Square className="h-3 w-3 fill-current" /> : <Mic className="h-3.5 w-3.5" />}
						{isRecording ? "Stop" : compact ? "Voice" : "Record voice"}
					</Button>
				</TooltipTrigger>
				<TooltipContent side="top">Record audio from your microphone</TooltipContent>
			</Tooltip>
		</div>
	);
}
