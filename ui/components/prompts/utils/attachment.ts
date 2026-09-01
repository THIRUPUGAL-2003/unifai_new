import { MessageContent } from "@/lib/message";
import { toast } from "sonner";

/** Accepted file types for prompt repository attachments */
export const PROMPT_FILE_ACCEPT =
	"image/*,audio/*,.pdf,.txt,.csv,.json,.xml,.md,.html,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.mp3,.wav,.m4a,.webm,.ogg";

export const PROMPT_FILE_ACCEPT_LABEL = "Images, PDF, Excel, Word, audio, voice, and more";

export const MAX_PROMPT_ATTACHMENT_BYTES = 20 * 1024 * 1024; // 20 MB

const EXTENSION_MIME: Record<string, string> = {
	pdf: "application/pdf",
	txt: "text/plain",
	csv: "text/csv",
	json: "application/json",
	xml: "application/xml",
	md: "text/markdown",
	html: "text/html",
	doc: "application/msword",
	docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	xls: "application/vnd.ms-excel",
	xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	ppt: "application/vnd.ms-powerpoint",
	pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
	zip: "application/zip",
	mp3: "audio/mpeg",
	wav: "audio/wav",
	m4a: "audio/mp4",
	webm: "audio/webm",
	ogg: "audio/ogg",
};

export function resolveFileMimeType(file: File): string {
	if (file.type && file.type !== "application/octet-stream") {
		return file.type;
	}
	const ext = file.name.split(".").pop()?.toLowerCase() || "";
	return EXTENSION_MIME[ext] || "application/octet-stream";
}

export function validatePromptAttachmentFile(file: File): string | null {
	if (file.size > MAX_PROMPT_ATTACHMENT_BYTES) {
		return `"${file.name}" is too large (max ${Math.round(MAX_PROMPT_ATTACHMENT_BYTES / (1024 * 1024))} MB)`;
	}
	return null;
}

export function fileToBase64(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as string);
		reader.onerror = reject;
		reader.readAsDataURL(file);
	});
}

export async function filesToAttachments(files: FileList | File[]): Promise<MessageContent[]> {
	const attachments: MessageContent[] = [];
	for (const file of Array.from(files)) {
		const error = validatePromptAttachmentFile(file);
		if (error) {
			toast.error(error);
			continue;
		}
		const attachment = await fileToAttachment(file);
		if (attachment) {
			attachments.push(attachment);
		}
	}
	return attachments;
}

export async function fileToAttachment(file: File): Promise<MessageContent | null> {
	const mimeType = resolveFileMimeType(file);

	if (mimeType.startsWith("image/")) {
		const dataUrl = await fileToBase64(file);
		return {
			type: "image_url",
			image_url: { url: dataUrl, detail: "auto" },
		};
	}

	if (mimeType.startsWith("audio/")) {
		const dataUrl = await fileToBase64(file);
		const base64Data = dataUrl.split(",")[1] || "";
		const format = file.name.split(".").pop() || mimeType.split("/")[1] || "wav";
		return {
			type: "input_audio",
			input_audio: { data: base64Data, format },
		};
	}

	const dataUrl = await fileToBase64(file);
	return {
		type: "file",
		file: {
			file_data: dataUrl,
			filename: file.name,
			file_type: mimeType,
		},
	};
}

export function getAttachmentDisplayName(attachment: MessageContent): string {
	if (attachment.type === "image_url") return "Image";
	if (attachment.type === "input_audio") return attachment.input_audio?.format?.toUpperCase() || "Voice";
	return attachment.file?.filename || "File";
}
