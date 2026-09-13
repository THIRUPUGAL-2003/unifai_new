import { type MessageContent } from "@/lib/message";
import { toast } from "sonner";
import { audioFormatFromMimeOrName, normalizeAudioToWavFile } from "./audioNormalize";
import { extractPromptFileText } from "./extractFileText";
import { transcribeAudioFile, voiceTranscriptAttachment } from "./transcribeAudio";

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
		try {
			const attachment = await fileToAttachment(file);
			if (attachment) {
				attachments.push(attachment);
			}
		} catch (err) {
			const message = err instanceof Error ? err.message : `Failed to import "${file.name}"`;
			toast.error(message);
		}
	}
	return attachments;
}

function textAttachmentFromExtract(fileName: string, extracted: string): MessageContent {
	return {
		type: "text",
		text: `Attached file: ${fileName}\n\n--- extracted content ---\n${extracted.trim()}`,
	};
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
		const normalized = (await normalizeAudioToWavFile(file)) || file;
		toast.message("Transcribing voice with Whisper…");
		const transcript = await transcribeAudioFile(normalized);
		if (transcript?.text) {
			toast.success(`Voice transcribed (${transcript.model})`);
			return voiceTranscriptAttachment(file.name, transcript.text);
		}
		toast.message("Whisper unavailable — attaching raw audio", {
			description: "Configure an OpenAI Whisper key/model, or use an audio-capable chat model.",
		});
		const dataUrl = await fileToBase64(normalized);
		const base64Data = dataUrl.split(",")[1] || "";
		const format = audioFormatFromMimeOrName(normalized.type || mimeType, normalized.name || file.name);
		if (format === "webm" || format === "ogg") {
			toast.message(`"${file.name}" kept as ${format}`, {
				description: "Some models only accept wav/mp3. If run fails, export as WAV/MP3 and re-import.",
			});
		} else if (normalized !== file) {
			toast.success("Voice converted to WAV for model compatibility");
		}
		return {
			type: "input_audio",
			input_audio: { data: base64Data, format },
		};
	}

	const extracted = await extractPromptFileText(file, mimeType);
	if (extracted && extracted.trim()) {
		toast.success(`Extracted text from ${file.name}`);
		return textAttachmentFromExtract(file.name, extracted);
	}

	const lower = file.name.toLowerCase();
	if (
		/\.(pdf|docx|doc|xlsx|xls|csv|txt|md|json|xml|html|htm|pptx|ppt|ppsx|pps)$/i.test(lower) ||
		mimeType.startsWith("text/")
	) {
		toast.error(`Could not extract readable text from "${file.name}"`, {
			description: "File may be empty, image-only, or corrupted. Try re-exporting or paste the content.",
		});
		return null;
	}

	if (/\.(zip)$/i.test(lower)) {
		toast.error(`"${file.name}" is a zip archive`, {
			description: "Unzip and import the document files inside (PDF, DOCX, PPTX, etc.).",
		});
		return null;
	}

	const dataUrl = await fileToBase64(file);
	toast.message(`Attached "${file.name}" as raw file`, {
		description: "This model may ignore raw file blocks. Prefer PDF/DOCX/XLSX/TXT when possible.",
	});
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
	if (attachment.type === "text" && attachment.text?.startsWith("Voice transcript")) return "Voice transcript";
	if (attachment.type === "text" && attachment.text?.startsWith("Attached file:")) {
		const firstLine = attachment.text.split("\n")[0] || "";
		return firstLine.replace(/^Attached file:\s*/i, "").trim() || "File";
	}
	return attachment.file?.filename || "File";
}

export function attachmentNeedsVision(attachments: MessageContent[]): boolean {
	return attachments.some((a) => a.type === "image_url");
}

export function attachmentNeedsAudio(attachments: MessageContent[]): boolean {
	return attachments.some((a) => a.type === "input_audio");
}
