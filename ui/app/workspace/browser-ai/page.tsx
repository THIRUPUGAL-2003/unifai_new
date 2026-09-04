import React, { useState, useEffect, useMemo, useRef } from "react";
import {
	Globe,
	RefreshCw,
	Shield,
	ShieldCheck,
	Plus,
	Search,
	CheckCircle2,
	AlertTriangle,
	AlertCircle,
	Copy,
	Check,
	Eye,
	EyeOff,
	Download,
	ExternalLink,
	Activity,
	Terminal,
	FileText,
	ChevronLeft,
	ChevronRight,
	CornerDownRight,
	Trash2,
	Pencil,
	X,
	SlidersHorizontal,
	Zap,
	BrainCircuit,
	Radio,
	FileKey,
	Upload,
	Bot,
	Save,
	Paperclip,
	Sparkles,
	Loader2,
	Cloud,
} from "lucide-react";
import { getProviderLabel } from "@/lib/constants/logs";
import { useGetModelsQuery, useGetProvidersQuery } from "@/lib/store/apis/providersApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alertDialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ComboboxSelect } from "@/components/ui/combobox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { normalizeTargetDomain, groupTargetsByParent, relatedHostsForDomain, relatedHostOptions, HOST_ROLE_OPTIONS, hostRoleLabel, type HostRole } from "./relatedHosts";
import { buildAttachmentPreview, pickBestExtractedText, type AttachmentPreviewKind } from "./attachmentPreview";

import {
	useGetBrowserAiLogsQuery,
	useClearBrowserAiLogsMutation,
	useGetBrowserAiRulesQuery,
	useGetBrowserAiOllamaModelsQuery,
	useCreateBrowserAiRuleMutation,
	useUpdateBrowserAiRuleMutation,
	useDeleteBrowserAiRuleMutation,
	useGenerateBrowserAiRegexFromPolicyMutation,
	useGetBrowserAiControlsQuery,
	useUpdateBrowserAiControlsMutation,
	useGetBrowserAiTargetsQuery,
	useCreateBrowserAiTargetMutation,
	useUpdateBrowserAiTargetMutation,
	useDeleteBrowserAiTargetMutation,
	useGetBrowserAiAgentsQuery,
	useGetBrowserAiAgentSettingsQuery,
	useSaveBrowserAiUninstallKeyMutation,
	useBulkDeleteBrowserAiAgentsMutation,
	BrowserAILogEntry,
	BrowserGuardRule,
	BrowserControlSettings,
	BrowserTargetWebsite,
	BrowserAIAgent,
} from "@/lib/store/apis/browserAiApi";
import { getApiBaseUrl } from "@/lib/utils/port";

function GuardBotModelPicker({
	provider,
	value,
	onChange,
	disabled,
}: {
	provider: string;
	value: string;
	onChange: (model: string) => void;
	disabled?: boolean;
}) {
	const isOllama = (provider || "").toLowerCase() === "ollama";
	const { data, isFetching, isError } = useGetBrowserAiOllamaModelsQuery(undefined, { skip: !isOllama });
	const options = useMemo(() => {
		const seen = new Set<string>();
		const opts: { label: string; value: string }[] = [];
		for (const name of data?.models || []) {
			const trimmed = String(name || "").trim().replace(/:latest$/i, "");
			if (!trimmed || seen.has(trimmed)) continue;
			seen.add(trimmed);
			opts.push({ label: trimmed, value: trimmed });
		}
		const current = String(value || "").trim();
		if (current && !seen.has(current)) {
			opts.unshift({ label: current, value: current });
		}
		return opts;
	}, [data, value]);

	return (
		<ComboboxSelect
			options={options}
			value={value || null}
			onValueChange={(v) => onChange(String(v || ""))}
			placeholder={!isOllama ? "Select Download model source first" : isFetching ? "Loading models from server..." : isError ? "Could not reach Ollama server" : "Select model"}
			hideClear
			disabled={disabled || !isOllama}
			emptyMessage={isError ? "Ollama server unreachable — check server Ollama" : "No models on Ollama server"}
			searchPlaceholder="Search models..."
			data-testid="browser-ai-guard-bot-model"
		/>
	);
}

function GuardBotOutsourceModelPicker({
	provider,
	value,
	onChange,
	disabled,
}: {
	provider: string;
	value: string;
	onChange: (model: string) => void;
	disabled?: boolean;
}) {
	const { data, isFetching, isError } = useGetModelsQuery(
		{ provider: provider || undefined, limit: 1000, unfiltered: true },
		{ skip: !provider },
	);
	const options = useMemo(() => {
		const seen = new Set<string>();
		const opts: { label: string; value: string }[] = [];
		for (const m of data?.models || []) {
			const name = String(m?.name || "").trim();
			if (!name || seen.has(name)) continue;
			seen.add(name);
			opts.push({ label: name, value: name });
		}
		const current = String(value || "").trim();
		if (current && !seen.has(current)) {
			opts.unshift({ label: current, value: current });
		}
		return opts;
	}, [data, value]);

	return (
		<ComboboxSelect
			options={options}
			value={value || null}
			onValueChange={(v) => onChange(String(v || ""))}
			placeholder={!provider ? "Select provider first" : isFetching ? "Loading catalog models..." : isError ? "Could not load models" : "Select model"}
			hideClear
			disabled={disabled || !provider}
			emptyMessage={!provider ? "Pick a provider" : "No models — add API keys under Model Providers"}
			searchPlaceholder="Search catalog models..."
			data-testid="browser-ai-guard-bot-outsource-model"
		/>
	);
}

const GUARD_BOT_OLLAMA_PROVIDER = "ollama";
const GUARD_BOT_OLLAMA_MODEL = "llama3.2";
const GUARD_BOT_OLLAMA_ENDPOINT = "http://76.13.243.253:11434";
const GUARD_BOT_REFERENCE_IMAGE_MAX_BYTES = 512 * 1024;

function isDownloadGuardSource(provider: string): boolean {
	const p = (provider || "").trim().toLowerCase();
	return !p || p === GUARD_BOT_OLLAMA_PROVIDER;
}

function guardRuleNoticeCopy(action: "BLOCK" | "REDACT") {
	if (action === "BLOCK") {
		return {
			label: "Block message (shown when rejected)",
			placeholder: "Message employees see when this rule blocks their prompt...",
			hint: "Shown in chat when the rule blocks. Leave blank for the default block message.",
			listLabel: "Block message",
		};
	}
	return {
		label: "Redaction notice (appended in chat)",
		placeholder: "Notice appended when this rule redacts — e.g. Sensitive data detected. Do not share API keys.",
		hint: "Prompt is still sent; this notice is appended as [UNIFAI REDACTED]. Leave blank for the default notice.",
		listLabel: "Redaction notice",
	};
}

function guardRuleActionHint(action: "BLOCK" | "REDACT") {
	if (action === "BLOCK") {
		return "Stops the prompt or file send and shows a block message.";
	}
	return "Allows send; appends a [UNIFAI REDACTED] notice in chat.";
}

function isSiteBlockLog(log: {
	user_prompt_preview?: string;
	user_prompt_full?: string;
	rule_triggered?: string;
	predicted_category?: string;
}): boolean {
	const preview = `${log.user_prompt_preview || ""} ${log.user_prompt_full || ""}`.toUpperCase();
	if (preview.includes("[SITE BLOCKED]")) return true;
	if ((log.predicted_category || "").toUpperCase() === "SITE_BLOCK") return true;
	return (log.rule_triggered || "").toLowerCase() === "block entire website";
}

function logActionBadge(log: {
	action?: string;
	user_prompt_preview?: string;
	user_prompt_full?: string;
	rule_triggered?: string;
	predicted_category?: string;
}) {
	// Fixed-width chip so Action column stays the same size every row.
	const chip = (className: string, icon: React.ReactNode, label: string) => (
		<Badge className={`inline-flex h-6 w-[108px] shrink-0 items-center justify-center gap-1 px-1.5 text-[10px] font-medium ${className}`}>
			{icon}
			<span className="truncate">{label}</span>
		</Badge>
	);
	if (isSiteBlockLog(log)) {
		return chip("bg-rose-950/80 text-rose-300 border-rose-700/60", <Globe className="h-3 w-3 shrink-0" />, "Site Block");
	}
	if (log.action === "Blocked") {
		return chip("bg-red-950/80 text-red-400 border-red-700/60", <AlertTriangle className="h-3 w-3 shrink-0" />, "Blocked");
	}
	if (log.action === "Bot Answered") {
		return chip("bg-sky-950/80 text-sky-300 border-sky-700/60", <Bot className="h-3 w-3 shrink-0" />, "Bot");
	}
	if (log.action === "Redacted" || log.action === "Warned") {
		return chip("bg-amber-950/80 text-amber-300 border-amber-700/60", <AlertCircle className="h-3 w-3 shrink-0" />, "Redacted");
	}
	return chip("bg-emerald-950/80 text-emerald-400 border-emerald-700/60", <CheckCircle2 className="h-3 w-3 shrink-0" />, "Allowed");
}

function platformBadgeLabel(platform: string): { label: string; className: string } {
	const p = (platform || "").toLowerCase();
	if (p.includes("claude")) return { label: "Claude", className: "bg-purple-950/60 text-purple-300 border-purple-700/60" };
	if (p.includes("chatgpt") || p.includes("openai")) return { label: "ChatGPT", className: "bg-emerald-950/60 text-emerald-300 border-emerald-700/60" };
	// Only real Gemini/Bard — do NOT map every "google" host (Drive/Docs) to Gemini
	if (p.includes("gemini") || p.includes("bard")) return { label: "Gemini", className: "bg-blue-950/60 text-blue-300 border-blue-700/60" };
	if (p.includes("copilot") || (p.includes("microsoft") && !p.includes("google"))) return { label: "Copilot", className: "bg-cyan-950/60 text-cyan-300 border-cyan-700/60" };
	if (p.includes("perplexity")) return { label: "Perplexity", className: "bg-amber-950/60 text-amber-300 border-amber-700/60" };
	if (p.includes("deepseek")) return { label: "DeepSeek", className: "bg-indigo-950/60 text-indigo-300 border-indigo-700/60" };
	const raw = (platform || "AI").trim();
	const label = raw.length > 14 ? `${raw.slice(0, 12)}…` : raw || "AI";
	return { label, className: "bg-slate-800 text-slate-300 border-slate-700" };
}

function getPlatformBadge(platform: string) {
	const { label, className } = platformBadgeLabel(platform);
	return (
		<Badge className={`inline-flex h-6 max-w-full items-center border px-2 text-[10px] font-medium ${className}`} title={platform || ""}>
			<span className="truncate">{label}</span>
		</Badge>
	);
}

function oneLinePreview(text?: string) {
	return (text || "").replace(/\s+/g, " ").trim();
}

function parseBrowserAiLogMetadata(log: BrowserAILogEntry): Record<string, unknown> {
	try {
		return JSON.parse(log.metadata || "{}") as Record<string, unknown>;
	} catch {
		return {};
	}
}

function logFileStatusLine(log: BrowserAILogEntry): string {
	const full = (log.user_prompt_full || log.user_prompt_preview || "").trim();
	if (!full) return "";
	const pipe = full.indexOf(" | ");
	const head = pipe >= 0 ? full.slice(0, pipe) : full;
	if (head.startsWith("[FILE UPLOAD]") || head.startsWith("[VOICE UPLOAD]")) return head;
	return head;
}

function logExtractedTextFromPrompt(log: BrowserAILogEntry): string {
	const full = (log.user_prompt_full || log.user_prompt_preview || "").trim();
	const pipe = full.indexOf(" | ");
	if (pipe >= 0) return full.slice(pipe + 3).trim();
	return "";
}

function logExtractedText(log: BrowserAILogEntry, attachmentText = ""): string {
	const meta = parseBrowserAiLogMetadata(log);
	const fromMeta = typeof meta.extracted_text === "string" ? meta.extracted_text.trim() : "";
	const legacy = logExtractedTextFromPrompt(log);
	// Prefer client-side PDF parse (pdfjs) over regex garbage stored in metadata.
	return pickBestExtractedText(attachmentText, fromMeta, legacy);
}

function isFileUploadLog(log: BrowserAILogEntry | null | undefined) {
	if (!log) return false;
	if (log.attachment_name || log.attachment_stored_name) return true;
	const p = (log.user_prompt_full || log.user_prompt_preview || "").trim();
	if (p.startsWith("[FILE UPLOAD]") || p.startsWith("[VOICE UPLOAD]")) return true;
	const meta = parseBrowserAiLogMetadata(log);
	return meta.upload_scan === true;
}

function logHasStoredAttachment(log: BrowserAILogEntry | null | undefined) {
	return !!(log?.attachment_stored_name);
}

function logAttachmentLabel(log: BrowserAILogEntry) {
	const name = (log.attachment_name || "").trim();
	if (name && name.toLowerCase() !== "attachment") return name;
	const full = (log.user_prompt_full || log.user_prompt_preview || "").trim();
	// [FILE UPLOAD] name.pdf — message   OR   name.pdf - message
	const m = full.match(/^\[(?:FILE|VOICE) UPLOAD\]\s+(.+?)(?:\s+[—–-]\s+|\s+--\s+|$)/i);
	if (m?.[1]) {
		const label = m[1].trim();
		if (label && label.toLowerCase() !== "attachment") return label;
	}
	return name || "attachment";
}

/** Clear security pass/fail wording for Prompt Details (AI Guard Bot + categories). */
function securityVerdictFromLog(log: BrowserAILogEntry): { title: string; detail: string; tone: "ok" | "bad" | "warn" | "neutral" } {
	const cat = (log.predicted_category || "").toUpperCase();
	const status = (log.status || "").toLowerCase();
	const action = (log.action || "").toLowerCase();
	if (cat === "AI_GUARD_BOT_CLEAR" || status.includes("security ok")) {
		return {
			title: "Security OK — policy met",
			detail: "AI Guard Bot analysed this prompt and found no security-policy violation.",
			tone: "ok",
		};
	}
	if (cat === "AI_GUARD_BOT_VIOLATION") {
		return {
			title: "Security NOT met — blocked",
			detail: `AI Guard Bot found a policy violation${log.rule_triggered ? ` (${log.rule_triggered})` : ""}.`,
			tone: "bad",
		};
	}
	if (cat === "AI_GUARD_BOT_REDACT" || cat === "AI_GUARD_BOT_WARNING") {
		return {
			title: "Security notice — allowed with redaction",
			detail: `AI Guard Bot flagged this prompt${log.rule_triggered ? ` (${log.rule_triggered})` : ""}.`,
			tone: "warn",
		};
	}
	if (cat === "AI_GUARD_BOT_EVAL_ERROR" || cat === "AI_GUARD_BOT_MISCONFIGURED") {
		return {
			title: "Security check failed",
			detail: status || "AI Guard Bot could not finish evaluation.",
			tone: "bad",
		};
	}
	if (action === "blocked" || cat === "SECURITY_POLICY_VIOLATION") {
		return {
			title: "Security NOT met — blocked",
			detail: log.rule_triggered ? `Blocked by rule: ${log.rule_triggered}` : (log.status || "Blocked by Guard policy."),
			tone: "bad",
		};
	}
	if (action === "redacted" || action === "warned") {
		return {
			title: "Security redaction",
			detail: log.rule_triggered ? `Redacted by rule: ${log.rule_triggered}` : (log.status || "Redacted by Guard policy."),
			tone: "warn",
		};
	}
	if (action === "allowed") {
		return {
			title: "Allowed",
			detail: status.includes("security ok")
				? "AI Guard Bot: security OK."
				: "No blocking Guard rule matched this prompt.",
			tone: "ok",
		};
	}
	return {
		title: log.action || "Logged",
		detail: log.status || "",
		tone: "neutral",
	};
}

function LogPromptPreviewCell({ log }: { log: BrowserAILogEntry }) {
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

function isMultimodalGuardModel(model: string): boolean {
	const m = (model || "").toLowerCase();
	return m.includes("gemma4") || m.includes("gemma-4");
}

function isVisionOnlyGuardModel(model: string): boolean {
	const m = (model || "").toLowerCase();
	if (isMultimodalGuardModel(m)) return false;
	return m.includes("llava") || m.includes("vision") || m.includes("bakllava");
}

function isVisionGuardModel(model: string): boolean {
	return isVisionOnlyGuardModel(model) || isMultimodalGuardModel(model);
}

function referenceImageDataUrl(base64: string, contentType = "image/png"): string {
	if (!base64) return "";
	if (base64.startsWith("data:")) return base64;
	return `data:${contentType || "image/png"};base64,${base64}`;
}

async function readReferenceImageFile(file: File): Promise<{ data: string; type: string }> {
	if (!file.type.startsWith("image/")) {
		throw new Error("Reference template must be an image (PNG, JPG, WebP).");
	}
	if (file.size > GUARD_BOT_REFERENCE_IMAGE_MAX_BYTES) {
		throw new Error(`Reference image must be under ${Math.round(GUARD_BOT_REFERENCE_IMAGE_MAX_BYTES / 1024)} KB.`);
	}
	const dataUrl = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(String(reader.result || ""));
		reader.onerror = () => reject(new Error("Failed to read image file."));
		reader.readAsDataURL(file);
	});
	const comma = dataUrl.indexOf("base64,");
	const data = comma >= 0 ? dataUrl.slice(comma + 7) : dataUrl;
	return { data, type: file.type || "image/png" };
}

function GuardRuleAIEvaluatorFields({
	botProvider,
	botModel,
	botPrompt,
	referenceImagePreview,
	evalMode,
	generatedPattern,
	generateError,
	generating,
	onProviderChange,
	onModelChange,
	onPromptChange,
	onEvalModeChange,
	onGeneratedPatternChange,
	onGenerateRegex,
	onReferenceImageChange,
	onReferenceImageClear,
	outsourceProviderOptions,
}: {
	botProvider: string;
	botModel: string;
	botPrompt: string;
	referenceImagePreview: string;
	evalMode: "ai" | "regex";
	generatedPattern: string;
	generateError?: string;
	generating?: boolean;
	onProviderChange: (value: string) => void;
	onModelChange: (value: string) => void;
	onPromptChange: (value: string) => void;
	onEvalModeChange: (mode: "ai" | "regex") => void;
	onGeneratedPatternChange: (value: string) => void;
	onGenerateRegex: () => void;
	onReferenceImageChange: (file: File) => void;
	onReferenceImageClear: () => void;
	outsourceProviderOptions: { label: string; value: string }[];
}) {
	const visionModel = isVisionGuardModel(botModel);
	const multimodalModel = isMultimodalGuardModel(botModel);
	const modelSource: "download" | "outsource" = isDownloadGuardSource(botProvider) ? "download" : "outsource";
	const activeOutsourceProvider =
		botProvider && !isDownloadGuardSource(botProvider)
			? botProvider
			: outsourceProviderOptions[0]?.value || "";

	const setModelSource = (source: "download" | "outsource") => {
		if (source === "download") {
			onProviderChange(GUARD_BOT_OLLAMA_PROVIDER);
			onModelChange(GUARD_BOT_OLLAMA_MODEL);
			return;
		}
		const first = outsourceProviderOptions[0]?.value || "";
		if (isDownloadGuardSource(botProvider) || !botProvider) {
			onProviderChange(first);
			onModelChange("");
		}
	};

	return (
		<div className="space-y-3 rounded-lg border border-purple-900/40 bg-purple-950/20 p-3">
			<div className="flex items-center gap-1.5 text-xs font-semibold text-purple-300">
				<Bot className="h-3.5 w-3.5" />
				<span>AI Evaluator</span>
			</div>

			<div className="space-y-1.5">
				<Label className="text-xs">Model source</Label>
				<div className="grid grid-cols-2 gap-2 p-1 bg-background/50 rounded-lg border border-border">
					<button
						type="button"
						onClick={() => setModelSource("download")}
						className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-[11px] font-semibold transition-all ${
							modelSource === "download" ? "bg-purple-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
						}`}
					>
						<Download className="h-3.5 w-3.5" />
						Download model
					</button>
					<button
						type="button"
						onClick={() => setModelSource("outsource")}
						className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-[11px] font-semibold transition-all ${
							modelSource === "outsource" ? "bg-purple-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
						}`}
					>
						<Cloud className="h-3.5 w-3.5" />
						Outsource model
					</button>
				</div>
				<p className="text-[11px] text-muted-foreground">
					{modelSource === "download"
						? "Uses Ollama models pulled on the Guard server (llama3.2, gemma4, llava, …)."
						: "Uses Model Providers + API keys from this UnifAI workspace (OpenRouter, OpenAI, etc.)."}
				</p>
			</div>

			{modelSource === "download" ? (
				<div className="space-y-1.5">
					<Label className="text-xs">Ollama model</Label>
					<GuardBotModelPicker provider={GUARD_BOT_OLLAMA_PROVIDER} value={botModel} onChange={onModelChange} />
				</div>
			) : (
				<div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<div className="space-y-1.5">
						<Label className="text-xs">Provider</Label>
						<Select
							value={activeOutsourceProvider}
							onValueChange={(v) => {
								onProviderChange(v);
								onModelChange("");
							}}
						>
							<SelectTrigger>
								<SelectValue placeholder="Select provider" />
							</SelectTrigger>
							<SelectContent>
								{outsourceProviderOptions.length === 0 ? (
									<SelectItem value="__none" disabled>
										No providers configured
									</SelectItem>
								) : (
									outsourceProviderOptions.map((opt) => (
										<SelectItem key={opt.value} value={opt.value}>
											{opt.label}
										</SelectItem>
									))
								)}
							</SelectContent>
						</Select>
						{outsourceProviderOptions.length === 0 ? (
							<p className="text-[11px] text-amber-400">
								Add a provider and API key under{" "}
								<a href="/workspace/providers" className="underline underline-offset-2">
									Model Providers
								</a>
								.
							</p>
						) : null}
					</div>
					<div className="space-y-1.5">
						<Label className="text-xs">Model</Label>
						<GuardBotOutsourceModelPicker
							provider={activeOutsourceProvider}
							value={botModel}
							onChange={onModelChange}
						/>
					</div>
				</div>
			)}

			<p className="text-[11px] text-muted-foreground">
				{multimodalModel
					? "Gemma 4 multimodal — evaluates prompts, extracted file text, and image uploads (PDF pages, photos)."
					: visionModel
						? "LLaVA vision model — compares uploaded PDF/image content against your policy and reference template."
						: "Text model — evaluates prompts and extracted file text."}
			</p>

			<div className="space-y-1.5">
				<Label className="text-xs">Check mode</Label>
				<div className="grid grid-cols-2 gap-2 p-1 bg-background/50 rounded-lg border border-border">
					<button
						type="button"
						onClick={() => onEvalModeChange("ai")}
						className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-[11px] font-semibold transition-all ${
							evalMode === "ai" ? "bg-purple-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
						}`}
					>
						<Bot className="h-3.5 w-3.5" />
						AI Prompt evaluate
					</button>
					<button
						type="button"
						onClick={() => onEvalModeChange("regex")}
						className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-[11px] font-semibold transition-all ${
							evalMode === "regex" ? "bg-cyan-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
						}`}
					>
						<Zap className="h-3.5 w-3.5" />
						Generated Regex
					</button>
				</div>
				<p className="text-[11px] text-muted-foreground">
					{evalMode === "ai"
						? "Selected model checks every prompt/file extract against your policy (slower, meaning-aware)."
						: "Model writes a regex from your policy; that regex matches prompts + extracted file/audio text (fast, like Regex rules)."}
				</p>
			</div>

			<div className="space-y-1.5">
				<Label className="text-xs">Security Policy / Evaluation Instruction (Prompt)</Label>
				<Textarea
					className="font-mono text-xs"
					placeholder="Write a clear policy, e.g. Block personal human names (my name is X). Block phone numbers. Block API keys / passwords. Block salary or bank account numbers..."
					value={botPrompt}
					onChange={(e) => onPromptChange(e.target.value)}
					rows={4}
				/>
				<p className="text-[11px] text-muted-foreground">
					This text is what the model enforces on every prompt / file / audio extract. Be specific — short vague lines like &quot;mobile names not allowed&quot; often miss. Say what to block and give 1 example.
				</p>
			</div>

			<div className="space-y-1.5">
				<div className="flex flex-wrap items-center justify-between gap-2">
					<Label className="text-xs">Generated Regex</Label>
					<Button
						type="button"
						variant="outline"
						size="sm"
						className="h-8 gap-1.5 text-xs"
						disabled={generating || !botPrompt.trim()}
						onClick={onGenerateRegex}
					>
						{generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
						{generating ? "Generating…" : "Generate Regex from policy"}
					</Button>
				</div>
				<Input
					className="font-mono text-xs"
					placeholder="Click Generate — or paste/edit a regex here"
					value={generatedPattern}
					onChange={(e) => onGeneratedPatternChange(e.target.value)}
				/>
				{generateError ? <p className="text-[11px] text-red-400">{generateError}</p> : null}
				<p className="text-[11px] text-muted-foreground">
					Review/edit before save. Applies to typed prompts and extracted file/audio text.
					{evalMode === "regex" ? " Saving in Generated Regex mode creates a fast Regex rule." : " Optional while using AI Prompt mode."}
				</p>
			</div>

			{(visionModel || referenceImagePreview) && evalMode === "ai" && (
				<div className="space-y-1.5">
					<Label className="text-xs">Reference Template Image {visionModel ? "" : "(optional)"}</Label>
					<div className="flex flex-wrap items-start gap-3">
						<label className="border-input bg-background hover:bg-muted/40 inline-flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium">
							<FileText className="h-3.5 w-3.5" />
							Upload template
							<input
								type="file"
								accept="image/png,image/jpeg,image/webp,image/gif"
								className="sr-only"
								onChange={(e) => {
									const file = e.target.files?.[0];
									if (file) onReferenceImageChange(file);
									e.target.value = "";
								}}
							/>
						</label>
						{referenceImagePreview ? (
							<div className="relative">
								<img
									src={referenceImagePreview}
									alt="Reference template preview"
									className="border-border h-20 w-auto max-w-[160px] rounded border object-contain"
								/>
								<Button
									type="button"
									variant="destructive"
									size="icon"
									className="absolute -top-2 -right-2 h-6 w-6"
									onClick={onReferenceImageClear}
								>
									<X className="h-3 w-3" />
								</Button>
							</div>
						) : null}
					</div>
					<p className="text-[11px] text-muted-foreground">
						Stored in the rule (DB) as a small reference only — not employee uploads. Max{" "}
						{Math.round(GUARD_BOT_REFERENCE_IMAGE_MAX_BYTES / 1024)} KB.
					</p>
				</div>
			)}
		</div>
	);
}

export default function BrowserAiPage() {
	const [activeTab, setActiveTab] = useState("overview");

	// Live updates & Polling control
	const [liveUpdatesEnabled, setLiveUpdatesEnabled] = useState(true);

	// Pagination & Filters state
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPlatform, setSelectedPlatform] = useState("all");
	const [selectedAction, setSelectedAction] = useState("all");
	const [pageLimit, setPageLimit] = useState(25);
	const [pageOffset, setPageOffset] = useState(0);

	const [ruleSearch, setRuleSearch] = useState("");
	const [targetSearch, setTargetSearch] = useState("");
	const [targetPageLimit, setTargetPageLimit] = useState(10);
	const [targetPageOffset, setTargetPageOffset] = useState(0);
	const [selectedLog, setSelectedLog] = useState<BrowserAILogEntry | null>(null);
	const [pdfViewerLog, setPdfViewerLog] = useState<BrowserAILogEntry | null>(null);
	const [pdfViewerTab, setPdfViewerTab] = useState<"preview" | "extracted" | "details">("preview");
	const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
	const [attachmentPreviewKind, setAttachmentPreviewKind] = useState<AttachmentPreviewKind | null>(null);
	const [attachmentPreviewHtml, setAttachmentPreviewHtml] = useState("");
	const [attachmentPreviewText, setAttachmentPreviewText] = useState("");
	const [pdfLoading, setPdfLoading] = useState(false);
	const [pdfError, setPdfError] = useState("");
	const [copiedPrompt, setCopiedPrompt] = useState(false);
	const [setupPackageDownloading, setSetupPackageDownloading] = useState(false);
	const [setupPackageError, setSetupPackageError] = useState("");
	const [uninstallKeyInput, setUninstallKeyInput] = useState("");
	const [uninstallKeyMessage, setUninstallKeyMessage] = useState("");
	const [uninstallKeyError, setUninstallKeyError] = useState("");
	// Plaintext is hashed server-side; keep last saved value only for this browser session.
	const [savedUninstallKeyDisplay, setSavedUninstallKeyDisplay] = useState("");
	const [uninstallKeyEditing, setUninstallKeyEditing] = useState(false);
	const [showUninstallKey, setShowUninstallKey] = useState(false);
	const [agentSearch, setAgentSearch] = useState("");
	const [agentStatusFilter, setAgentStatusFilter] = useState("all");
	const [agentPageOffset, setAgentPageOffset] = useState(0);
	const agentPageLimit = 50;
	const [selectedAgentIds, setSelectedAgentIds] = useState<Set<string>>(new Set());
	const [showAgentDeleteDialog, setShowAgentDeleteDialog] = useState(false);
	const [agentDeleteError, setAgentDeleteError] = useState("");
	const [agentBulkAction, setAgentBulkAction] = useState("");

	// Dialog states
	const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
	const [targetDialogOpen, setTargetDialogOpen] = useState(false);
	const [ruleError, setRuleError] = useState("");
	const [targetError, setTargetError] = useState("");

	// New Rule Form
	const [newRuleName, setNewRuleName] = useState("");
	const [newRuleType, setNewRuleType] = useState<"regex" | "ai_bot">("regex");
	const [newRuleBotProvider, setNewRuleBotProvider] = useState(GUARD_BOT_OLLAMA_PROVIDER);
	const [newRuleBotModel, setNewRuleBotModel] = useState(GUARD_BOT_OLLAMA_MODEL);
	const [newRuleBotPrompt, setNewRuleBotPrompt] = useState("");
	const [newRuleBotReferenceImage, setNewRuleBotReferenceImage] = useState("");
	const [newRuleBotReferenceImageType, setNewRuleBotReferenceImageType] = useState("");
	const [newRuleBotReferenceImagePreview, setNewRuleBotReferenceImagePreview] = useState("");
	const [newRuleSeverity, setNewRuleSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("CRITICAL");
	const [newRuleAction, setNewRuleAction] = useState<"BLOCK" | "REDACT">("BLOCK");
	const [newRulePattern, setNewRulePattern] = useState("");
	const [newRuleDescription, setNewRuleDescription] = useState("");
	const [newRuleWarningMessage, setNewRuleWarningMessage] = useState("");
	const [newRuleBotEvalMode, setNewRuleBotEvalMode] = useState<"ai" | "regex">("ai");
	const [newRuleGeneratedPattern, setNewRuleGeneratedPattern] = useState("");
	const [newRuleGenerateError, setNewRuleGenerateError] = useState("");

type RelatedHostEntry = { host: string; role: HostRole };

	// New Target Form
	const [newTargetDomain, setNewTargetDomain] = useState("");
	const [newTargetPlatform, setNewTargetPlatform] = useState("");
	const [newTargetHostRole, setNewTargetHostRole] = useState<HostRole>("ui");
	const [newTargetBlockSite, setNewTargetBlockSite] = useState(false);
	const [customRelatedHosts, setCustomRelatedHosts] = useState<RelatedHostEntry[]>([{ host: "", role: "" }]);
	const [extraHostDrafts, setExtraHostDrafts] = useState<Record<string, string>>({});
	const [extraHostRoleDrafts, setExtraHostRoleDrafts] = useState<Record<string, HostRole>>({});

	// Edit Target Form
	const [editTarget, setEditTarget] = useState<BrowserTargetWebsite | null>(null);
	const [editTargetDomain, setEditTargetDomain] = useState("");
	const [editTargetPlatform, setEditTargetPlatform] = useState("");
	const [editTargetBlockSite, setEditTargetBlockSite] = useState(false);
	const [editTargetHostRole, setEditTargetHostRole] = useState<HostRole>("");
	const [editTargetDialogOpen, setEditTargetDialogOpen] = useState(false);

	// Edit Rule Form
	const [editRule, setEditRule] = useState<BrowserGuardRule | null>(null);
	const [editRuleName, setEditRuleName] = useState("");
	const [editRuleType, setEditRuleType] = useState<"regex" | "ai_bot">("regex");
	const [editRuleBotProvider, setEditRuleBotProvider] = useState("");
	const [editRuleBotModel, setEditRuleBotModel] = useState("");
	const [editRuleBotPrompt, setEditRuleBotPrompt] = useState("");
	const [editRuleBotReferenceImage, setEditRuleBotReferenceImage] = useState("");
	const [editRuleBotReferenceImageType, setEditRuleBotReferenceImageType] = useState("");
	const [editRuleBotReferenceImagePreview, setEditRuleBotReferenceImagePreview] = useState("");
	const [editRuleSeverity, setEditRuleSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("CRITICAL");
	const [editRuleAction, setEditRuleAction] = useState<"BLOCK" | "REDACT">("BLOCK");
	const [editRulePattern, setEditRulePattern] = useState("");
	const [editRuleDescription, setEditRuleDescription] = useState("");
	const [editRuleWarningMessage, setEditRuleWarningMessage] = useState("");
	const [editRuleDialogOpen, setEditRuleDialogOpen] = useState(false);
	const [editRuleBotEvalMode, setEditRuleBotEvalMode] = useState<"ai" | "regex">("ai");
	const [editRuleGeneratedPattern, setEditRuleGeneratedPattern] = useState("");
	const [editRuleGenerateError, setEditRuleGenerateError] = useState("");

	const activePolling = liveUpdatesEnabled ? 3000 : undefined;

	// --- Violation Notification State ---
	const [violationToasts, setViolationToasts] = useState<
		Array<{ id: string; platform: string; reason: string; prompt: string; time: string }>
	>([]);
	const seenBlockedIds = useRef<Set<string>>(new Set());
	const notifPermission = useRef<NotificationPermission>("default");

	// Request browser notification permission on mount
	useEffect(() => {
		if (typeof window !== "undefined" && "Notification" in window) {
			Notification.requestPermission().then((perm) => {
				notifPermission.current = perm;
			});
		}
	}, []);

	// RTK Queries with auto-polling for real-time live updates
	const {
		data: logsData,
		refetch: refetchLogs,
		isFetching: logsLoading,
	} = useGetBrowserAiLogsQuery(
		{
			platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
			action: selectedAction !== "all" ? selectedAction : undefined,
			search: searchQuery || undefined,
			limit: pageLimit,
			offset: pageOffset,
		},
		{ pollingInterval: activePolling }
	);

	const { data: rulesData, refetch: refetchRules } = useGetBrowserAiRulesQuery(undefined, { pollingInterval: activePolling });
	const { data: targetsData, refetch: refetchTargets } = useGetBrowserAiTargetsQuery(undefined, { pollingInterval: activePolling });
	const { data: controlsData } = useGetBrowserAiControlsQuery(undefined, { pollingInterval: activePolling });
	const { data: providersData } = useGetProvidersQuery();
	// Outsource = configured Model Providers (OpenRouter, OpenAI, …). Download = Ollama on server.
	const outsourceProviderOptions = useMemo(() => {
		const opts = (providersData || [])
			.map((p) => String(p?.name || "").trim())
			.filter((name) => name && name.toLowerCase() !== GUARD_BOT_OLLAMA_PROVIDER)
			.map((name) => ({ label: getProviderLabel(name), value: name }));
		opts.sort((a, b) => a.label.localeCompare(b.label));
		return opts;
	}, [providersData]);
	const {
		data: agentsData,
		refetch: refetchAgents,
		isFetching: agentsLoading,
	} = useGetBrowserAiAgentsQuery(
		{
			status: agentStatusFilter !== "all" ? agentStatusFilter : undefined,
			search: agentSearch || undefined,
			limit: agentPageLimit,
			offset: agentPageOffset,
		},
		{ pollingInterval: activePolling }
	);
	const { data: agentSettingsData, refetch: refetchAgentSettings } = useGetBrowserAiAgentSettingsQuery();
	const [saveUninstallKey, { isLoading: savingUninstallKey }] = useSaveBrowserAiUninstallKeyMutation();

	const controls: BrowserControlSettings = controlsData?.controls || {
		id: "browser-controls-default",
		enabled: true,
		block_upload: false,
		upload_warning: "",
	};
	const [uploadWarningDraft, setUploadWarningDraft] = useState("");
	const [uploadWarningEditing, setUploadWarningEditing] = useState(false);
	const [uploadWarningSaving, setUploadWarningSaving] = useState(false);
	const [uploadWarningError, setUploadWarningError] = useState("");
	useEffect(() => {
		if (!uploadWarningEditing) {
			setUploadWarningDraft(controls.upload_warning || "");
		}
	}, [controls.upload_warning, uploadWarningEditing]);
	const agents = agentsData?.agents || [];
	const totalAgents = agentsData?.total || 0;
	const activeAgentsCount = agents.filter((a) => a.status === "active").length;
	const agentSettings = agentSettingsData?.settings;
	const visibleAgentIds = useMemo(() => agents.map((a) => a.id), [agents]);
	const selectedVisibleAgentIds = useMemo(
		() => visibleAgentIds.filter((id) => selectedAgentIds.has(id)),
		[selectedAgentIds, visibleAgentIds],
	);
	const selectedAgentCount = selectedAgentIds.size;
	const allVisibleAgentsSelected = visibleAgentIds.length > 0 && selectedVisibleAgentIds.length === visibleAgentIds.length;
	const someVisibleAgentsSelected = selectedVisibleAgentIds.length > 0 && selectedVisibleAgentIds.length < visibleAgentIds.length;

	useEffect(() => {
		setSelectedAgentIds(new Set());
		setAgentBulkAction("");
	}, [agentPageOffset, agentSearch, agentStatusFilter]);

	// --- Detect new blocked violations and fire notifications ---
	useEffect(() => {
		if (!logsData?.logs) return;
		const newBlocked = logsData.logs.filter(
			(l) => l.action === "Blocked" && l.id && !seenBlockedIds.current.has(l.id)
		);
		if (newBlocked.length === 0) return;
		newBlocked.forEach((log) => {
			seenBlockedIds.current.add(log.id);
			const toastId = log.id;
			const platform = log.platform || "AI Platform";
			const reason = log.rule_triggered || "Security Rule Violation";
			const prompt = log.user_prompt_full?.slice(0, 60) || log.risk_score?.toString() || "";
			const time = new Date().toLocaleTimeString();

			// Show browser system notification
			if (typeof window !== "undefined" && "Notification" in window && notifPermission.current === "granted") {
				try {
					new Notification("🚨 AI Guard: Security Violation Blocked!", {
						body: `[${platform}] ${reason}`,
						icon: "/favicon.ico",
						tag: toastId,
					});
				} catch {}
			}

			// Show in-page toast
			setViolationToasts((prev) => [
				{ id: toastId, platform, reason, prompt, time },
				...prev.slice(0, 4),
			]);
			// Auto-dismiss after 8 seconds
			setTimeout(() => {
				setViolationToasts((prev) => prev.filter((t) => t.id !== toastId));
			}, 8000);
		});
	}, [logsData]);

	useEffect(() => {
		if (!pdfViewerLog?.id || !logHasStoredAttachment(pdfViewerLog)) {
			if (pdfBlobUrl) {
				URL.revokeObjectURL(pdfBlobUrl);
				setPdfBlobUrl(null);
			}
			setAttachmentPreviewKind(null);
			setAttachmentPreviewHtml("");
			setAttachmentPreviewText("");
			setPdfLoading(false);
			setPdfError("");
			return;
		}
		let cancelled = false;
		let objectUrl: string | null = null;
		setPdfLoading(true);
		setPdfError("");
		setAttachmentPreviewKind(null);
		setAttachmentPreviewHtml("");
		setAttachmentPreviewText("");
		if (pdfBlobUrl) {
			URL.revokeObjectURL(pdfBlobUrl);
			setPdfBlobUrl(null);
		}
		(async () => {
			try {
				const res = await fetch(`${getApiBaseUrl()}/browser-ai/attachments/${encodeURIComponent(pdfViewerLog.id)}`, {
					credentials: "include",
				});
				if (!res.ok) {
					if (res.status === 410) {
						throw new Error("File expired (kept 10 minutes for View). Log and filename remain.");
					}
					throw new Error(res.status === 404 ? "File not found on server" : `Failed to load file (${res.status})`);
				}
				const blob = await res.blob();
				if (cancelled) return;
				const preview = await buildAttachmentPreview(
					blob,
					logAttachmentLabel(pdfViewerLog),
					pdfViewerLog.attachment_content_type || blob.type,
				);
				if (cancelled) return;
				setAttachmentPreviewKind(preview.kind);
				if (preview.blobUrl) {
					objectUrl = preview.blobUrl;
					setPdfBlobUrl(preview.blobUrl);
				}
				if (preview.html) setAttachmentPreviewHtml(preview.html);
				if (preview.text) setAttachmentPreviewText(preview.text);
				if (preview.kind === "unsupported") {
					objectUrl = URL.createObjectURL(blob);
					setPdfBlobUrl(objectUrl);
				}
			} catch (e) {
				if (!cancelled) {
					setPdfError(e instanceof Error ? e.message : "Failed to load file");
					setPdfBlobUrl(null);
					setAttachmentPreviewKind(null);
				}
			} finally {
				if (!cancelled) setPdfLoading(false);
			}
		})();
		return () => {
			cancelled = true;
			if (objectUrl) URL.revokeObjectURL(objectUrl);
		};
		// eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when log id changes
	}, [pdfViewerLog?.id]);

	const openPdfViewer = (log: BrowserAILogEntry, e?: React.MouseEvent) => {
		e?.stopPropagation();
		setPdfViewerTab("preview");
		setPdfViewerLog(log);
	};

	const downloadPdfAttachment = async (log: BrowserAILogEntry) => {
		try {
			const res = await fetch(
				`${getApiBaseUrl()}/browser-ai/attachments/${encodeURIComponent(log.id)}?download=1`,
				{ credentials: "include" },
			);
			if (!res.ok) {
				if (res.status === 410) {
					setPdfError("File expired (kept 10 minutes for View). Log and filename remain.");
					return;
				}
				throw new Error("Download failed");
			}
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = logAttachmentLabel(log);
			document.body.appendChild(a);
			a.click();
			a.remove();
			URL.revokeObjectURL(url);
		} catch {
			setPdfError("Download failed");
		}
	};

	const [clearLogs] = useClearBrowserAiLogsMutation();
	const [createRule] = useCreateBrowserAiRuleMutation();
	const [updateRule] = useUpdateBrowserAiRuleMutation();
	const [deleteRule] = useDeleteBrowserAiRuleMutation();
	const [generateRegexFromPolicy, { isLoading: generatingRegex }] = useGenerateBrowserAiRegexFromPolicyMutation();
	const [updateControls] = useUpdateBrowserAiControlsMutation();
	const [createTarget] = useCreateBrowserAiTargetMutation();
	const [updateTarget] = useUpdateBrowserAiTargetMutation();
	const [deleteTarget] = useDeleteBrowserAiTargetMutation();
	const [bulkDeleteAgents, { isLoading: deletingAgents }] = useBulkDeleteBrowserAiAgentsMutation();

	const toggleSelectAllVisibleAgents = (checked: boolean) => {
		setSelectedAgentIds((prev) => {
			const next = new Set(prev);
			for (const id of visibleAgentIds) {
				if (checked) {
					next.add(id);
				} else {
					next.delete(id);
				}
			}
			return next;
		});
	};

	const toggleSelectAgent = (agentId: string, checked: boolean) => {
		setSelectedAgentIds((prev) => {
			const next = new Set(prev);
			if (checked) {
				next.add(agentId);
			} else {
				next.delete(agentId);
			}
			return next;
		});
	};

	const handleAgentBulkAction = (action: string) => {
		setAgentBulkAction(action);
		if (action === "delete") {
			if (selectedAgentCount === 0) {
				setAgentBulkAction("");
				return;
			}
			setAgentDeleteError("");
			setShowAgentDeleteDialog(true);
		}
	};

	const handleDeleteSelectedAgents = async () => {
		const ids = Array.from(selectedAgentIds);
		if (ids.length === 0) return;
		setAgentDeleteError("");
		try {
			await bulkDeleteAgents({ ids }).unwrap();
			setSelectedAgentIds(new Set());
			setAgentBulkAction("");
			setShowAgentDeleteDialog(false);
			refetchAgents();
		} catch {
			setAgentDeleteError("Could not delete selected agents. Try again.");
		}
	};

	const patchControl = async (patch: Partial<BrowserControlSettings>) => {
		try {
			await updateControls(patch).unwrap();
			return true;
		} catch {
			return false;
		}
	};

	const saveUploadWarning = async () => {
		setUploadWarningError("");
		setUploadWarningSaving(true);
		const text = uploadWarningDraft.trim();
		const ok = await patchControl({ upload_warning: text });
		setUploadWarningSaving(false);
		if (!ok) {
			setUploadWarningError("Could not save warning. Try again.");
			return;
		}
		setUploadWarningDraft(text);
		setUploadWarningEditing(false);
	};

	const handleEditTarget = async () => {
		if (!editTarget || !editTargetDomain.trim()) return;
		try {
			await updateTarget({
				id: editTarget.id,
				updates: {
					domain: editTargetDomain.trim(),
					platform_name: editTargetPlatform.trim() || "AI Platform",
					block_site: editTargetBlockSite,
					status: editTargetBlockSite ? "BLOCKED" : editTarget.monitored ? "MONITORED" : "PAUSED",
					host_role: editTargetHostRole || "",
				},
			}).unwrap();
			setEditTargetDialogOpen(false);
			setEditTarget(null);
		} catch (e) {
			// error
		}
	};

	const handleCreateRule = async () => {
		setRuleError("");
		if (!newRuleName.trim()) {
			setRuleError("Rule name is required.");
			return;
		}
		if (newRuleType === "ai_bot") {
			if (!newRuleBotPrompt.trim() && !newRuleBotReferenceImage.trim()) {
				setRuleError("Security policy prompt or reference template image is required for AI Guard Bot.");
				return;
			}
			if (newRuleBotEvalMode === "ai" && newRuleBotPrompt.trim() && newRuleBotPrompt.trim().split(/\s+/).length < 4) {
				setRuleError(
					"Security policy is too short/vague. Write a clear rule (e.g. \"Block personal human names such as my name is X\").",
				);
				return;
			}
			if (newRuleBotEvalMode === "regex" && !newRuleGeneratedPattern.trim()) {
				setRuleError("Generate or enter a regex pattern, or switch to AI Prompt evaluate mode.");
				return;
			}
			if (newRuleBotEvalMode === "ai") {
				if (!isDownloadGuardSource(newRuleBotProvider) && !newRuleBotProvider.trim()) {
					setRuleError("Select an Outsource provider (or switch to Download model).");
					return;
				}
				if (!newRuleBotModel.trim()) {
					setRuleError("Select a model for AI Guard Bot.");
					return;
				}
			}
		} else {
			if (!newRulePattern.trim()) {
				setRuleError("Regex pattern is required for Regex rule.");
				return;
			}
		}
		try {
			const saveAsGeneratedRegex = newRuleType === "ai_bot" && newRuleBotEvalMode === "regex";
			const policyNote = newRuleBotPrompt.trim()
				? `Generated from policy: ${newRuleBotPrompt.trim().slice(0, 500)}`
				: "";
			await createRule({
				name: newRuleName.trim(),
				rule_type: saveAsGeneratedRegex ? "regex" : newRuleType,
				pattern: saveAsGeneratedRegex
					? newRuleGeneratedPattern.trim()
					: newRuleType === "regex"
						? newRulePattern.trim()
						: newRuleGeneratedPattern.trim(),
				bot_provider: newRuleType === "ai_bot" && !saveAsGeneratedRegex ? newRuleBotProvider || GUARD_BOT_OLLAMA_PROVIDER : "",
				bot_model:
					newRuleType === "ai_bot" && !saveAsGeneratedRegex
						? newRuleBotModel || (isDownloadGuardSource(newRuleBotProvider) ? GUARD_BOT_OLLAMA_MODEL : "")
						: "",
				bot_prompt: newRuleType === "ai_bot" && !saveAsGeneratedRegex ? newRuleBotPrompt.trim() : "",
				bot_reference_image: newRuleType === "ai_bot" && !saveAsGeneratedRegex ? newRuleBotReferenceImage : "",
				bot_reference_image_type: newRuleType === "ai_bot" && !saveAsGeneratedRegex ? newRuleBotReferenceImageType : "",
				severity: newRuleSeverity,
				action: newRuleAction,
				description: (newRuleDescription.trim() || (saveAsGeneratedRegex ? policyNote : "")).trim(),
				warning_message: newRuleWarningMessage.trim(),
				active: true,
			}).unwrap();
			setRuleDialogOpen(false);
			setNewRuleName("");
			setNewRulePattern("");
			setNewRuleBotPrompt("");
			setNewRuleBotReferenceImage("");
			setNewRuleBotReferenceImageType("");
			setNewRuleBotReferenceImagePreview("");
			setNewRuleDescription("");
			setNewRuleWarningMessage("");
			setNewRuleType("regex");
			setNewRuleBotEvalMode("ai");
			setNewRuleGeneratedPattern("");
			setNewRuleGenerateError("");
		} catch (e: any) {
			setRuleError(e?.data?.message || "Failed to create rule");
		}
	};

	const runGenerateRegex = async (which: "new" | "edit") => {
		const prompt = which === "new" ? newRuleBotPrompt.trim() : editRuleBotPrompt.trim();
		const provider = which === "new" ? newRuleBotProvider : editRuleBotProvider;
		const model = which === "new" ? newRuleBotModel : editRuleBotModel;
		const setErr = which === "new" ? setNewRuleGenerateError : setEditRuleGenerateError;
		const setPat = which === "new" ? setNewRuleGeneratedPattern : setEditRuleGeneratedPattern;
		setErr("");
		if (!prompt) {
			setErr("Enter a security policy prompt first.");
			return;
		}
		try {
			const res = await generateRegexFromPolicy({
				bot_provider: provider || GUARD_BOT_OLLAMA_PROVIDER,
				bot_model: model || GUARD_BOT_OLLAMA_MODEL,
				bot_prompt: prompt,
			}).unwrap();
			const pat = (res.pattern || "").trim();
			if (!pat) {
				setErr("Model returned an empty pattern.");
				return;
			}
			setPat(pat);
			if (res.focus || res.notes) {
				setErr([res.focus && `Focus: ${res.focus}`, res.notes].filter(Boolean).join(" — "));
			}
		} catch (e: any) {
			setErr(
				e?.data?.error?.message ||
					e?.data?.message ||
					e?.message ||
					"Failed to generate regex from policy.",
			);
		}
	};

	const handleEditRuleSubmit = async () => {
		if (!editRule || !editRuleName.trim()) return;
		setRuleError("");
		if (editRuleType === "ai_bot") {
			if (!editRuleBotPrompt.trim() && !editRuleBotReferenceImage.trim()) {
				setRuleError("Security policy prompt or reference template image is required for AI Guard Bot.");
				return;
			}
			if (editRuleBotEvalMode === "ai" && editRuleBotPrompt.trim() && editRuleBotPrompt.trim().split(/\s+/).length < 4) {
				setRuleError(
					"Security policy is too short/vague. Write a clear rule (e.g. \"Block personal human names such as my name is X\").",
				);
				return;
			}
			if (editRuleBotEvalMode === "regex" && !editRuleGeneratedPattern.trim()) {
				setRuleError("Generate or enter a regex pattern, or switch to AI Prompt evaluate mode.");
				return;
			}
			if (editRuleBotEvalMode === "ai") {
				if (!isDownloadGuardSource(editRuleBotProvider) && !editRuleBotProvider.trim()) {
					setRuleError("Select an Outsource provider (or switch to Download model).");
					return;
				}
				if (!editRuleBotModel.trim()) {
					setRuleError("Select a model for AI Guard Bot.");
					return;
				}
			}
		} else {
			if (!editRulePattern.trim()) {
				setRuleError("Regex pattern is required for Regex rule.");
				return;
			}
		}
		try {
			const saveAsGeneratedRegex = editRuleType === "ai_bot" && editRuleBotEvalMode === "regex";
			const updates: Record<string, any> = {
				name: editRuleName.trim(),
				rule_type: saveAsGeneratedRegex ? "regex" : editRuleType,
				severity: editRuleSeverity,
				action: editRuleAction,
				description: editRuleDescription.trim(),
				warning_message: editRuleWarningMessage.trim(),
			};
			if (saveAsGeneratedRegex) {
				updates.pattern = editRuleGeneratedPattern.trim();
				updates.bot_provider = "";
				updates.bot_model = "";
				updates.bot_prompt = "";
				updates.bot_reference_image = "";
				updates.bot_reference_image_type = "";
				if (!updates.description && editRuleBotPrompt.trim()) {
					updates.description = `Generated from policy: ${editRuleBotPrompt.trim().slice(0, 500)}`;
				}
			} else if (editRuleType === "ai_bot") {
				updates.bot_provider = editRuleBotProvider || GUARD_BOT_OLLAMA_PROVIDER;
				updates.bot_model = editRuleBotModel || (isDownloadGuardSource(editRuleBotProvider) ? GUARD_BOT_OLLAMA_MODEL : "");
				updates.bot_prompt = editRuleBotPrompt.trim();
				updates.bot_reference_image = editRuleBotReferenceImage;
				updates.bot_reference_image_type = editRuleBotReferenceImageType;
				updates.pattern = editRuleGeneratedPattern.trim();
			} else {
				updates.pattern = editRulePattern.trim();
				updates.bot_provider = "";
				updates.bot_model = "";
				updates.bot_prompt = "";
				updates.bot_reference_image = "";
				updates.bot_reference_image_type = "";
			}
			await updateRule({
				id: editRule.id,
				updates,
			}).unwrap();
			setEditRuleDialogOpen(false);
			setEditRule(null);
		} catch (e: any) {
			setRuleError(e?.data?.message || "Failed to update rule");
		}
	};

	const logs = logsData?.logs || [];
	const totalLogs = logsData?.total || logs.length;
	const rules = rulesData?.rules || [];
	const targets = targetsData?.targets || [];
	const addedTargetDomains = targets.map((t) => t.domain);
	const newTargetRelatedGroup = relatedHostsForDomain(newTargetDomain);

	const activeRulesCount = rules.filter((r) => r.active).length;
	const monitoredTargetsCount = targets.filter((t) => t.monitored).length;
	const blockedCount = logs.filter((l) => l.action === "Blocked").length;
	const warnedCount = logs.filter((l) => l.action === "Redacted" || l.action === "Warned").length;
	const highRiskCount = logs.filter((l) => (l.risk_score || 0) >= 70 || l.predictive_risk === "HIGH" || l.predictive_risk === "CRITICAL").length;
	const avgRiskScore = logs.length > 0 ? Math.round(logs.reduce((acc, curr) => acc + (curr.risk_score || 10), 0) / logs.length) : 0;

	const handleCopyPrompt = (text: string) => {
		navigator.clipboard.writeText(text);
		setCopiedPrompt(true);
		setTimeout(() => setCopiedPrompt(false), 2000);
	};

	const handleDownloadSetupPackage = async () => {
		setSetupPackageDownloading(true);
		setSetupPackageError("");
		try {
			const res = await fetch(`${getApiBaseUrl()}/browser-ai/setup/download.zip`, {
				credentials: "include",
			});
			if (!res.ok) {
				throw new Error(`Download failed (${res.status})`);
			}
			const blob = await res.blob();
			const url = window.URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = "unifai-browser-ai-setup.zip";
			document.body.appendChild(link);
			link.click();
			link.remove();
			window.URL.revokeObjectURL(url);
		} catch (error) {
			setSetupPackageError(error instanceof Error ? error.message : "Failed to download setup package");
		} finally {
			setSetupPackageDownloading(false);
		}
	};

	const handleSaveUninstallKey = async () => {
		setUninstallKeyMessage("");
		setUninstallKeyError("");
		const nextKey = uninstallKeyInput.trim();
		if (!nextKey) {
			setUninstallKeyError("Enter a new uninstall key to save");
			return;
		}
		try {
			await saveUninstallKey({
				key: nextKey,
				require_uninstall_key: agentSettings?.require_uninstall_key ?? true,
				updated_by: "admin",
			}).unwrap();
			setSavedUninstallKeyDisplay(nextKey);
			setUninstallKeyInput("");
			setUninstallKeyEditing(false);
			setShowUninstallKey(true);
			setUninstallKeyMessage("Uninstall key saved. Share this key with IT — server stores only a hash.");
			refetchAgentSettings();
		} catch (error) {
			setUninstallKeyError(error instanceof Error ? error.message : "Failed to save uninstall key");
		}
	};

	const handleToggleRequireUninstallKey = async (checked: boolean) => {
		setUninstallKeyMessage("");
		setUninstallKeyError("");
		try {
			await saveUninstallKey({
				require_uninstall_key: checked,
				updated_by: "admin",
			}).unwrap();
			setUninstallKeyMessage(checked ? "Uninstall key is now required." : "Uninstall key requirement disabled.");
			refetchAgentSettings();
		} catch (error) {
			setUninstallKeyError(error instanceof Error ? error.message : "Failed to update uninstall policy");
		}
	};

	const handleCreateTarget = async () => {
		const domain = normalizeTargetDomain(newTargetDomain);
		if (!domain) {
			setTargetError("Enter a domain only, e.g. gemini.google.com (no https://).");
			return;
		}
		setTargetError("");
		const platformName = newTargetPlatform.trim() || domain;
		const payload = {
			platform_name: platformName,
			monitored: true,
			block_site: newTargetBlockSite,
			status: newTargetBlockSite ? "BLOCKED" : "MONITORED",
		};
		try {
			const created = await createTarget({ domain, ...payload, host_role: newTargetHostRole || "" }).unwrap();
			const parentId = created?.target?.id || "";
			for (const extra of customRelatedHosts) {
				const host = normalizeTargetDomain(extra.host);
				if (!host || host === domain) continue;
				try {
					await createTarget({
						domain: host,
						...payload,
						parent_id: parentId,
						host_role: extra.role || "",
					}).unwrap();
				} catch {
					const existing = targets.find((t) => normalizeTargetDomain(t.domain) === host);
					if (existing && parentId) {
						try {
							await updateTarget({
								id: existing.id,
								updates: { parent_id: parentId, host_role: extra.role || "" },
							}).unwrap();
						} catch {
							// already in the list — skip
						}
					}
				}
			}
			setNewTargetDomain("");
			setNewTargetPlatform("");
			setNewTargetHostRole("ui");
			setNewTargetBlockSite(false);
			setCustomRelatedHosts([{ host: "", role: "" }]);
			setTargetDialogOpen(false);
		} catch (err: any) {
			setTargetError(err?.data?.message || err?.message || "Failed to create target domain");
		}
	};

	const fillSuggestedRelatedHost = (host: string) => {
		const n = normalizeTargetDomain(host);
		if (!n) return;
		setCustomRelatedHosts((prev) => {
			if (prev.some((v) => normalizeTargetDomain(v.host) === n)) return prev;
			const emptyIdx = prev.findIndex((v) => !v.host.trim());
			if (emptyIdx >= 0) {
				const next = [...prev];
				next[emptyIdx] = { host: n, role: "" };
				return next;
			}
			return [...prev, { host: n, role: "" }];
		});
	};

	const handleAddRelatedHost = async (parent: BrowserTargetWebsite, host: string, role: HostRole = "") => {
		const domain = normalizeTargetDomain(host);
		if (!domain || domain === normalizeTargetDomain(parent.domain)) return;
		const parentId = parent.parent_id || parent.id;
		const payload = {
			domain,
			platform_name: parent.platform_name || domain,
			monitored: parent.monitored,
			block_site: !!parent.block_site,
			status: parent.block_site ? "BLOCKED" : parent.monitored ? "MONITORED" : "PAUSED",
			parent_id: parentId,
			host_role: role || "",
		};
		try {
			await createTarget(payload).unwrap();
		} catch (err: any) {
			const existing = targets.find((t) => normalizeTargetDomain(t.domain) === domain);
			if (existing) {
				try {
					await updateTarget({ id: existing.id, updates: { parent_id: parentId } }).unwrap();
					return;
				} catch {
					// fall through
				}
			}
			setTargetError(err?.data?.message || err?.message || "Failed to add related host");
		}
	};

	const getAgentStatusBadge = (status: string, uninstallRequested?: boolean) => {
		const s = (status || "").toLowerCase();
		if (s === "uninstalled") return <Badge className="bg-slate-800 text-slate-300 border border-slate-700">Uninstalled</Badge>;
		if (s === "uninstall_pending" || uninstallRequested) {
			return <Badge className="bg-amber-950 text-amber-300 border border-amber-800">Uninstall pending</Badge>;
		}
		if (s === "active") return <Badge className="bg-emerald-950 text-emerald-400 border border-emerald-800">Active</Badge>;
		return <Badge className="bg-slate-800 text-slate-300 border border-slate-700">{status || "unknown"}</Badge>;
	};

	const nicGuidOnly = (raw?: string) => {
		const m = (raw || "").match(/\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}/);
		return m ? m[0].toUpperCase() : "";
	};

	const filteredRules = rules.filter(
		(r) =>
			r.name.toLowerCase().includes(ruleSearch.toLowerCase()) ||
			(r.pattern || "").toLowerCase().includes(ruleSearch.toLowerCase()) ||
			(r.bot_prompt || "").toLowerCase().includes(ruleSearch.toLowerCase()) ||
			(r.description || "").toLowerCase().includes(ruleSearch.toLowerCase())
	);

	const targetSearchLower = targetSearch.toLowerCase().trim();
	const targetMatchesSearch = (tgt: BrowserTargetWebsite) => {
		if (!targetSearchLower) return true;
		const statusLabel = tgt.block_site ? "blocked" : tgt.monitored ? "monitored" : "paused";
		return (
			(tgt.domain || "").toLowerCase().includes(targetSearchLower) ||
			(tgt.platform_name || "").toLowerCase().includes(targetSearchLower) ||
			statusLabel.includes(targetSearchLower)
		);
	};

	const filteredTargetGroups = useMemo(() => {
		const groups = groupTargetsByParent(targets);
		if (!targetSearchLower) return groups;
		return groups.filter((group) => {
			const parentHit = targetMatchesSearch(group.parent);
			const childHits = group.children.filter(targetMatchesSearch);
			return parentHit || childHits.length > 0;
		});
	}, [targets, targetSearchLower]);

	const totalTargetParents = filteredTargetGroups.length;
	const targetCurrentPage = Math.floor(targetPageOffset / targetPageLimit) + 1;
	const targetTotalPages = Math.ceil(totalTargetParents / targetPageLimit) || 1;

	const visibleTargetRows: { tgt: BrowserTargetWebsite; isChild: boolean }[] = useMemo(() => {
		const pageGroups = filteredTargetGroups.slice(targetPageOffset, targetPageOffset + targetPageLimit);
		const rows: { tgt: BrowserTargetWebsite; isChild: boolean }[] = [];
		for (const group of pageGroups) {
			rows.push({ tgt: group.parent, isChild: false });
			const kids =
				!targetSearchLower || targetMatchesSearch(group.parent)
					? group.children
					: group.children.filter(targetMatchesSearch);
			for (const child of kids) {
				rows.push({ tgt: child, isChild: true });
			}
		}
		return rows;
	}, [filteredTargetGroups, targetPageOffset, targetPageLimit, targetSearchLower]);

	useEffect(() => {
		setTargetPageOffset(0);
	}, [targetSearch, targetPageLimit]);

	// Pagination calculations
	const currentPage = Math.floor(pageOffset / pageLimit) + 1;
	const totalPages = Math.ceil(totalLogs / pageLimit) || 1;

	return (
		<div className="space-y-6 p-2 md:p-6 text-foreground max-w-7xl mx-auto">
			{/* Header View */}
			<div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-5">
				<div>
					<div className="flex items-center gap-3">
						<Globe className="h-6 w-6 text-primary" />
						<h1 className="text-2xl font-bold tracking-tight">Browser AI Observability</h1>
					</div>
					<p className="text-muted-foreground text-sm mt-1">
						Monitor browser AI prompts, predict security threat levels, warn or block policy hits, and control DLP guardrails.
					</p>
				</div>
				<div className="flex items-center gap-3 flex-wrap sm:flex-nowrap">
					<div className="flex items-center gap-2 bg-card border border-border px-3 py-1.5 rounded-md text-xs">
						<Switch
							checked={liveUpdatesEnabled}
							onCheckedChange={setLiveUpdatesEnabled}
							id="live-update-switch"
						/>
						<Label htmlFor="live-update-switch" className="cursor-pointer font-medium text-xs">
							Live Update
						</Label>
					</div>

					<Button
						variant="outline"
						size="sm"
						onClick={() => {
							refetchLogs();
							refetchRules();
							refetchTargets();
							refetchAgents();
						}}
						className="gap-2 border-border hover:bg-accent h-8 text-xs"
					>
						<RefreshCw className={`h-3.5 w-3.5 ${logsLoading || agentsLoading ? "animate-spin" : ""}`} />
						Refresh
					</Button>
				</div>
			</div>

			{/* Sub-navigation Tabs */}
			<Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
				<TabsList className="bg-card border border-border p-1">
					<TabsTrigger value="overview" className="gap-2">
						<Activity className="h-4 w-4" /> Overview
					</TabsTrigger>
					<TabsTrigger value="logs" className="gap-2">
						<FileText className="h-4 w-4" /> Prompt Logs ({totalLogs})
					</TabsTrigger>
					<TabsTrigger value="rules" className="gap-2">
						<Shield className="h-4 w-4" /> Guard Rules ({rules.length})
					</TabsTrigger>
					<TabsTrigger value="targets" className="gap-2">
						<Globe className="h-4 w-4" /> Target Websites ({targets.length})
					</TabsTrigger>
					<TabsTrigger value="agents" className="gap-2">
						<Radio className="h-4 w-4" /> Guard Agents ({totalAgents})
					</TabsTrigger>
					<TabsTrigger value="setup" className="gap-2">
						<Terminal className="h-4 w-4" /> Setup
					</TabsTrigger>
				</TabsList>

				{/* TAB 1: OVERVIEW */}
				<TabsContent value="overview" className="space-y-6">
					<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<Globe className="h-3.5 w-3.5 text-muted-foreground" /> Total Prompts Intercepted
								</CardDescription>
								<CardTitle className="text-3xl font-bold">{totalLogs}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Passing through HTTPS proxy</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<AlertCircle className="h-3.5 w-3.5 text-amber-400" /> Redacted
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-amber-400">{warnedCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Prompt forwarded with redaction notice</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<BrainCircuit className="h-3.5 w-3.5 text-amber-400" /> Predictive High Risk
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-amber-400">{highRiskCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Avg Risk Score: {avgRiskScore}%</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<AlertTriangle className="h-3.5 w-3.5 text-red-400" /> Blocked Violations
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-red-400">{blockedCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Security policy breaches blocked</p>
							</CardContent>
						</Card>
					</div>

					<Card className="bg-card border-border">
						<CardHeader>
							<CardTitle className="text-lg">Recent Intercepted Activity</CardTitle>
							<CardDescription>Real-time prompt stream captured from browser sessions</CardDescription>
						</CardHeader>
						<CardContent>
							<div className="rounded-md border border-border overflow-x-auto">
								<Table className="table-fixed w-full min-w-[960px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[150px]">Timestamp</TableHead>
											<TableHead className="w-[100px]">Platform</TableHead>
											<TableHead className="w-[110px]">Guard</TableHead>
											<TableHead className="w-[auto]">User Prompt Preview</TableHead>
											<TableHead className="w-[80px] text-right">Est. Tokens</TableHead>
											<TableHead className="w-[120px]">Action</TableHead>
											<TableHead className="w-[64px] text-right">Details</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{logs.slice(0, 5).map((log) => (
											<TableRow
												key={log.id}
												onClick={() => setSelectedLog(log)}
												className="h-12 cursor-pointer border-border hover:bg-accent/50 transition-colors"
											>
												<TableCell className="max-w-0 py-0">
													<div className="truncate text-xs font-mono text-muted-foreground" title={new Date(log.timestamp).toLocaleString()}>
														{new Date(log.timestamp).toLocaleString()}
													</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<div className="min-w-0 truncate">{getPlatformBadge(log.platform)}</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<div className="truncate text-xs text-muted-foreground" title={log.agent_hostname || log.agent_id || ""}>
														{log.agent_hostname || log.agent_id || "—"}
													</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<LogPromptPreviewCell log={log} />
												</TableCell>
												<TableCell className="py-0 text-right text-xs font-mono">{log.est_tokens}</TableCell>
												<TableCell className="py-0">{logActionBadge(log)}</TableCell>
												<TableCell className="py-0 text-right">
													<div className="inline-flex items-center justify-end gap-0.5">
														{logHasStoredAttachment(log) ? (
															<Button
																variant="ghost"
																size="sm"
																onClick={(e) => openPdfViewer(log, e)}
																className="h-8 px-2 text-xs text-sky-400 hover:text-sky-300"
																title="View file"
															>
																View
															</Button>
														) : null}
														<Button
															variant="ghost"
															size="icon"
															onClick={(e) => {
																e.stopPropagation();
																setSelectedLog(log);
															}}
															className="h-8 w-8 text-muted-foreground hover:text-foreground"
															title="Prompt details"
														>
															<Eye className="h-4 w-4" />
														</Button>
													</div>
												</TableCell>
											</TableRow>
										))}
										{logs.length === 0 && (
											<TableRow>
												<TableCell colSpan={7} className="text-center py-6 text-muted-foreground">
													No prompts intercepted yet. Start browsing AI platforms via proxy.
												</TableCell>
											</TableRow>
										)}
									</TableBody>
								</Table>
							</div>
						</CardContent>
					</Card>
				</TabsContent>

				{/* TAB 2: PROMPT LOGS */}
				<TabsContent value="logs" className="space-y-4">
					<Card className="bg-card border-border">
						<CardHeader className="pb-4">
							<div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
								<div>
									<CardTitle className="text-lg">Prompt & Chat History</CardTitle>
									<CardDescription>Live intercepted requests passing through the proxy</CardDescription>
								</div>
								<div className="flex items-center gap-2">
									<Button variant="outline" size="sm" onClick={() => clearLogs()} className="text-destructive hover:bg-destructive/10 border-destructive/30">
										Clear Logs
									</Button>
								</div>
							</div>

							{/* Search & Filter Toolbar */}
							<div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
								<div className="relative">
									<Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
									<Input
										placeholder="Search prompts or domain..."
										value={searchQuery}
										onChange={(e) => {
											setSearchQuery(e.target.value);
											setPageOffset(0);
										}}
										className="pl-9 bg-background border-border"
									/>
								</div>
								<Select
									value={selectedPlatform}
									onValueChange={(val) => {
										setSelectedPlatform(val);
										setPageOffset(0);
									}}
								>
									<SelectTrigger className="bg-background border-border">
										<SelectValue placeholder="All Platforms" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="all">All Platforms</SelectItem>
										<SelectItem value="ChatGPT">ChatGPT</SelectItem>
										<SelectItem value="Claude">Claude</SelectItem>
										<SelectItem value="Gemini">Gemini</SelectItem>
										<SelectItem value="Copilot">Copilot</SelectItem>
										<SelectItem value="Perplexity">Perplexity</SelectItem>
										<SelectItem value="DeepSeek">DeepSeek</SelectItem>
									</SelectContent>
								</Select>
								<Select
									value={selectedAction}
									onValueChange={(val) => {
										setSelectedAction(val);
										setPageOffset(0);
									}}
								>
									<SelectTrigger className="bg-background border-border">
										<SelectValue placeholder="All Status" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="all">All Status</SelectItem>
										<SelectItem value="Allowed">Allowed</SelectItem>
										<SelectItem value="Redacted">Redacted</SelectItem>
										<SelectItem value="Warned">Warned (legacy)</SelectItem>
										<SelectItem value="Blocked">Blocked (DLP / rules)</SelectItem>
										<SelectItem value="SiteBlocked">Site Blocked (full website)</SelectItem>
										<SelectItem value="Bot Answered">Bot Answered</SelectItem>
									</SelectContent>
								</Select>
							</div>
						</CardHeader>

						<CardContent>
							<div className="rounded-md border border-border overflow-x-auto">
								<Table className="table-fixed w-full min-w-[960px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[150px]">Timestamp</TableHead>
											<TableHead className="w-[100px]">Platform</TableHead>
											<TableHead className="w-[110px]">Guard</TableHead>
											<TableHead className="w-[auto]">User Prompt Preview</TableHead>
											<TableHead className="w-[80px] text-right">Est. Tokens</TableHead>
											<TableHead className="w-[120px]">Action</TableHead>
											<TableHead className="w-[64px] text-right">Details</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{logs.map((log) => (
											<TableRow
												key={log.id}
												onClick={() => setSelectedLog(log)}
												className="h-12 cursor-pointer border-border hover:bg-accent/50 transition-colors"
											>
												<TableCell className="max-w-0 py-0">
													<div className="truncate text-xs font-mono text-muted-foreground" title={new Date(log.timestamp).toLocaleString()}>
														{new Date(log.timestamp).toLocaleString()}
													</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<div className="min-w-0 truncate">{getPlatformBadge(log.platform)}</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<div className="truncate text-xs text-muted-foreground" title={log.agent_hostname || log.agent_id || ""}>
														{log.agent_hostname || log.agent_id || "—"}
													</div>
												</TableCell>
												<TableCell className="max-w-0 py-0">
													<LogPromptPreviewCell log={log} />
												</TableCell>
												<TableCell className="py-0 text-right text-xs font-mono">{log.est_tokens}</TableCell>
												<TableCell className="py-0">{logActionBadge(log)}</TableCell>
												<TableCell className="py-0 text-right">
													<div className="inline-flex items-center justify-end gap-0.5">
														{logHasStoredAttachment(log) ? (
															<Button
																variant="ghost"
																size="sm"
																onClick={(e) => openPdfViewer(log, e)}
																className="h-8 px-2 text-xs text-sky-400 hover:text-sky-300"
																title="View file"
															>
																View
															</Button>
														) : null}
														<Button
															variant="ghost"
															size="icon"
															onClick={(e) => {
																e.stopPropagation();
																setSelectedLog(log);
															}}
															className="h-8 w-8 text-muted-foreground hover:text-foreground"
															title="Prompt details"
														>
															<Eye className="h-4 w-4" />
														</Button>
													</div>
												</TableCell>
											</TableRow>
										))}
										{logs.length === 0 && (
											<TableRow>
												<TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
													No prompt logs match your filter criteria.
												</TableCell>
											</TableRow>
										)}
									</TableBody>
								</Table>
							</div>

							{/* Standard Pagination Controls */}
							<div className="flex flex-col sm:flex-row justify-between items-center gap-4 mt-4 text-xs text-muted-foreground">
								<div className="flex items-center gap-2">
									<span>Rows per page</span>
									<Select
										value={pageLimit.toString()}
										onValueChange={(val) => {
											setPageLimit(Number(val));
											setPageOffset(0);
										}}
									>
										<SelectTrigger className="h-8 w-[70px] bg-background border-border">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="10">10</SelectItem>
											<SelectItem value="25">25</SelectItem>
											<SelectItem value="50">50</SelectItem>
											<SelectItem value="100">100</SelectItem>
										</SelectContent>
									</Select>
									<span>
										Showing {totalLogs > 0 ? pageOffset + 1 : 0} to {Math.min(pageOffset + pageLimit, totalLogs)} of {totalLogs} entries
									</span>
								</div>

								<div className="flex items-center gap-2">
									<span>
										Page {currentPage} of {totalPages}
									</span>
									<div className="flex items-center gap-1">
										<Button
											variant="outline"
											size="icon"
											disabled={pageOffset === 0}
											onClick={() => setPageOffset(Math.max(0, pageOffset - pageLimit))}
											className="h-8 w-8 border-border"
										>
											<ChevronLeft className="h-4 w-4" />
										</Button>
										<Button
											variant="outline"
											size="icon"
											disabled={pageOffset + pageLimit >= totalLogs}
											onClick={() => setPageOffset(pageOffset + pageLimit)}
											className="h-8 w-8 border-border"
										>
											<ChevronRight className="h-4 w-4" />
										</Button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>

				{/* TAB 3: GUARD RULES */}
				<TabsContent value="rules" className="space-y-4">
					{/* Browser Interaction Controls */}
					<Card className="bg-card border-border overflow-hidden">
						<CardHeader className="pb-4">
							<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
								<div className="space-y-1">
									<div className="flex flex-wrap items-center gap-2">
										<CardTitle className="text-lg">File upload policy</CardTitle>
										<Badge
											variant="outline"
											className={
												controls.enabled
													? "border-emerald-700/70 bg-emerald-950/40 text-emerald-400"
													: "border-border text-muted-foreground"
											}
										>
											{controls.enabled ? "Active" : "Paused"}
										</Badge>
									</div>
									<CardDescription>
										Control uploads on monitored AI sites. Each Guard Rule below has its own Active/Disabled toggle — off skips that pattern in prompts and inside uploaded files (PDF/text).
									</CardDescription>
								</div>
							</div>
						</CardHeader>
						<CardContent className="pt-0">
							<div className="overflow-hidden rounded-lg border border-border divide-y divide-border">
								{/* Master */}
								<div className="flex items-center justify-between gap-4 bg-background/50 px-4 py-3.5">
									<div className="min-w-0 flex items-start gap-3">
										<div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-card">
											<SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
										</div>
										<div className="min-w-0">
											<p className="text-sm font-medium">Upload controls</p>
											<p className="text-xs text-muted-foreground mt-0.5">
												Turn off to pause all upload enforcement on employee browsers.
											</p>
										</div>
									</div>
									<Switch
										checked={!!controls.enabled}
										onCheckedChange={(val) => patchControl({ enabled: val })}
										aria-label="Enable upload controls"
									/>
								</div>

								{/* Block every file */}
								<div
									className={`flex items-center justify-between gap-4 px-4 py-3.5 transition-opacity ${
										controls.enabled ? "bg-card" : "bg-muted/20 opacity-60"
									}`}
								>
									<div className="min-w-0 flex items-start gap-3">
										<div
											className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border ${
												controls.enabled && controls.block_upload
													? "border-rose-800/50 bg-rose-950/30"
													: "border-border bg-background"
											}`}
										>
											<Upload
												className={`h-4 w-4 ${
													controls.enabled && controls.block_upload ? "text-rose-400" : "text-muted-foreground"
												}`}
											/>
										</div>
										<div className="min-w-0 space-y-1.5">
											<div className="flex flex-wrap items-center gap-2">
												<p className="text-sm font-medium">Block all uploads</p>
												{controls.enabled && controls.block_upload ? (
													<Badge className="bg-rose-950/70 text-rose-300 border-rose-800/60 text-[10px] px-1.5 py-0">
														Blocking
													</Badge>
												) : (
													<Badge variant="outline" className="text-[10px] px-1.5 py-0 text-muted-foreground">
														Allow clean files
													</Badge>
												)}
											</div>
											<p className="text-xs text-muted-foreground leading-relaxed">
												{controls.block_upload
													? "Every file/attachment to AI chats is blocked."
													: "Clean files are allowed. Files that match Guard Rules inside PDF/text are still blocked."}
											</p>
										</div>
									</div>
									<Switch
										checked={!!controls.block_upload}
										disabled={!controls.enabled}
										onCheckedChange={(val) => patchControl({ block_upload: val })}
										aria-label="Block all uploads"
									/>
								</div>

								<div className="space-y-2 bg-card px-4 py-3.5">
									<div className="flex items-center justify-between gap-2">
										<Label>Upload policy warning</Label>
										{!uploadWarningEditing && (controls.upload_warning || "").trim() ? (
											<Button
												type="button"
												size="sm"
												variant="ghost"
												className="h-8 shrink-0 text-muted-foreground hover:text-foreground"
												onClick={() => {
													setUploadWarningError("");
													setUploadWarningDraft(controls.upload_warning || "");
													setUploadWarningEditing(true);
												}}
											>
												<Pencil className="h-3.5 w-3.5 mr-1.5" />
												Edit
											</Button>
										) : null}
									</div>
									{uploadWarningEditing || !(controls.upload_warning || "").trim() ? (
										<>
											<Textarea
												placeholder="e.g. UPLOAD BLOCK — shown in Prompt Logs and to employees..."
												value={uploadWarningDraft}
												onChange={(e) => setUploadWarningDraft(e.target.value)}
												rows={3}
											/>
											<div className="flex items-center justify-between gap-2">
												<p className="text-xs text-muted-foreground">
													Block all uploads → this text in Prompt Logs. A Guard Rule hit inside a file → this text (or that rule&apos;s warning) plus &quot; -- policy name&quot;. Leave blank to use &quot;Upload block&quot;.
												</p>
												<div className="flex items-center gap-2 shrink-0">
													{uploadWarningEditing && (controls.upload_warning || "").trim() ? (
														<Button
															type="button"
															size="sm"
															variant="ghost"
															disabled={uploadWarningSaving}
															onClick={() => {
																setUploadWarningError("");
																setUploadWarningDraft(controls.upload_warning || "");
																setUploadWarningEditing(false);
															}}
														>
															Cancel
														</Button>
													) : null}
													<Button
														type="button"
														size="sm"
														variant="outline"
														className="shrink-0"
														disabled={uploadWarningSaving}
														onClick={saveUploadWarning}
													>
														<Save className="h-3.5 w-3.5 mr-1.5" />
														{uploadWarningSaving ? "Saving..." : "Save warning"}
													</Button>
												</div>
											</div>
											{uploadWarningError ? (
												<p className="text-xs text-destructive">{uploadWarningError}</p>
											) : null}
										</>
									) : (
										<div className="rounded-md border border-amber-800/40 bg-amber-950/20 px-3 py-2">
											<p className="text-xs text-amber-100/90 whitespace-pre-wrap break-words">
												{(controls.upload_warning || "").trim()}
											</p>
										</div>
									)}
								</div>
							</div>
						</CardContent>
					</Card>

					<Card className="bg-card border-border">
						<CardHeader>
							<div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
								<div>
									<CardTitle className="text-lg">DLP Guard Rules ({rules.length} Configured)</CardTitle>
									<CardDescription>
										Matched against prompts and text inside uploaded files (PDF/text). Use each rule&apos;s Active toggle to enable or disable without deleting.
									</CardDescription>
								</div>
								<Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
									<DialogTrigger asChild>
										<Button className="gap-2">
											<Plus className="h-4 w-4" /> Add Rule
										</Button>
									</DialogTrigger>
									<DialogContent className="bg-card border-border text-foreground w-[calc(100%-2rem)] sm:max-w-xl max-h-[88vh] flex flex-col p-0 overflow-hidden">
										<DialogHeader className="p-5 pb-3 shrink-0 border-b border-border/60">
											<DialogTitle className="flex items-center gap-2 text-base">
												<Shield className="h-5 w-5 text-primary" />
												Create Guard Rule
											</DialogTitle>
											<DialogDescription className="text-xs">
												Configure a real-time regex DLP rule or an AI Guard Bot evaluation prompt.
											</DialogDescription>
										</DialogHeader>

										{ruleError && <div className="mx-5 mt-3 p-3 bg-red-950/60 border border-red-800 text-red-400 rounded-md text-xs">{ruleError}</div>}

										<div className="flex-1 overflow-y-auto overflow-x-hidden px-5 py-4 space-y-4 min-w-0">
											{/* Rule Engine Type Toggle */}
											<div className="space-y-1.5">
												<Label>Rule Engine Type</Label>
												<div className="grid grid-cols-2 gap-2 p-1 bg-muted/40 rounded-lg border border-border">
													<button
														type="button"
														onClick={() => {
															setNewRuleType("regex");
														}}
														className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
															newRuleType === "regex"
																? "bg-primary text-primary-foreground shadow-sm"
																: "text-muted-foreground hover:text-foreground"
														}`}
													>
														<Zap className="h-3.5 w-3.5" />
														Regex Pattern Rule
													</button>
													<button
														type="button"
														onClick={() => {
															setNewRuleType("ai_bot");
															setNewRuleBotProvider(GUARD_BOT_OLLAMA_PROVIDER);
															setNewRuleBotModel(GUARD_BOT_OLLAMA_MODEL);
														}}
														className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
															newRuleType === "ai_bot"
																? "bg-purple-600 text-white shadow-sm"
																: "text-muted-foreground hover:text-foreground"
														}`}
													>
														<Bot className="h-3.5 w-3.5" />
														AI Guard Bot (Prompt Rule)
													</button>
												</div>
											</div>

											<div className="space-y-1.5">
												<Label>Rule Name</Label>
												<Input
													placeholder={newRuleType === "ai_bot" ? "e.g. Detect Salary & Financial Queries" : "e.g. OpenAI API Key"}
													value={newRuleName}
													onChange={(e) => setNewRuleName(e.target.value)}
												/>
											</div>

											<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
												<div className="space-y-1.5 min-w-0">
													<Label>Severity</Label>
													<Select value={newRuleSeverity} onValueChange={(v: any) => setNewRuleSeverity(v)}>
														<SelectTrigger className="w-full">
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="CRITICAL">CRITICAL</SelectItem>
															<SelectItem value="HIGH">HIGH</SelectItem>
															<SelectItem value="MEDIUM">MEDIUM</SelectItem>
														</SelectContent>
													</Select>
												</div>
												<div className="space-y-1.5 min-w-0">
													<Label>Action</Label>
													<Select value={newRuleAction} onValueChange={(v: any) => setNewRuleAction(v)}>
														<SelectTrigger className="w-full">
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="BLOCK">BLOCK</SelectItem>
															<SelectItem value="REDACT">REDACT</SelectItem>
														</SelectContent>
													</Select>
													<p className="text-[11px] text-muted-foreground break-words">
														{guardRuleActionHint(newRuleAction)}
													</p>
												</div>
											</div>

											{newRuleType === "regex" ? (
												<div className="space-y-1.5">
													<Label>Regex Pattern</Label>
													<Input
														placeholder="e.g. sk-[a-zA-Z0-9]{20,}"
														value={newRulePattern}
														onChange={(e) => setNewRulePattern(e.target.value)}
													/>
													<p className="text-[11px] text-muted-foreground">
														One RE2 regex per rule. Example:{" "}
														<code className="text-[10px]">{"\\b\\d{10,12}\\b"}</code> for phone numbers.
													</p>
												</div>
											) : (
												<GuardRuleAIEvaluatorFields
													botProvider={newRuleBotProvider}
													botModel={newRuleBotModel}
													botPrompt={newRuleBotPrompt}
													referenceImagePreview={newRuleBotReferenceImagePreview}
													evalMode={newRuleBotEvalMode}
													generatedPattern={newRuleGeneratedPattern}
													generateError={newRuleGenerateError}
													generating={generatingRegex}
													outsourceProviderOptions={outsourceProviderOptions}
													onProviderChange={setNewRuleBotProvider}
													onModelChange={setNewRuleBotModel}
													onPromptChange={setNewRuleBotPrompt}
													onEvalModeChange={setNewRuleBotEvalMode}
													onGeneratedPatternChange={setNewRuleGeneratedPattern}
													onGenerateRegex={() => runGenerateRegex("new")}
													onReferenceImageClear={() => {
														setNewRuleBotReferenceImage("");
														setNewRuleBotReferenceImageType("");
														setNewRuleBotReferenceImagePreview("");
													}}
													onReferenceImageChange={async (file) => {
														try {
															const { data, type } = await readReferenceImageFile(file);
															setNewRuleBotReferenceImage(data);
															setNewRuleBotReferenceImageType(type);
															setNewRuleBotReferenceImagePreview(referenceImageDataUrl(data, type));
														} catch (err: any) {
															setRuleError(err?.message || "Failed to load reference image.");
														}
													}}
												/>
											)}

											<div className="space-y-1.5">
												<Label>Description</Label>
												<Textarea placeholder="Rule context and usage..." value={newRuleDescription} onChange={(e) => setNewRuleDescription(e.target.value)} />
											</div>
											<div className="space-y-1.5">
												<Label>{guardRuleNoticeCopy(newRuleAction).label}</Label>
												<Textarea
													placeholder={guardRuleNoticeCopy(newRuleAction).placeholder}
													value={newRuleWarningMessage}
													onChange={(e) => setNewRuleWarningMessage(e.target.value)}
													rows={3}
												/>
												<p className="text-xs text-muted-foreground break-words">
													{guardRuleNoticeCopy(newRuleAction).hint}
												</p>
											</div>
										</div>
										<DialogFooter className="p-4 px-5 shrink-0 border-t border-border/60 bg-card">
											<Button variant="outline" onClick={() => setRuleDialogOpen(false)}>
												Cancel
											</Button>
											<Button onClick={handleCreateRule}>Create Guard Rule</Button>
										</DialogFooter>
									</DialogContent>
								</Dialog>
							</div>

							<div className="relative mt-3">
								<Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
								<Input placeholder="Search guard rules..." value={ruleSearch} onChange={(e) => setRuleSearch(e.target.value)} className="pl-9 bg-background border-border" />
							</div>
						</CardHeader>
						<CardContent>
							<div className="space-y-3">
								{filteredRules.map((rule) => (
									<div
										key={rule.id}
										className="rounded-xl border border-border bg-background/40 p-4 hover:border-primary/30 transition-colors"
									>
										<div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
											<div className="min-w-0 flex-1 space-y-2">
												<div className="flex flex-wrap items-center gap-2">
													<h4 className="text-sm font-semibold text-foreground">{rule.name}</h4>
													{rule.rule_type === "ai_bot" ? (
														<Badge className="bg-purple-950/90 text-purple-300 border-purple-700 gap-1 text-[11px] font-semibold">
															<Bot className="h-3 w-3 text-purple-400" /> AI GUARD BOT
														</Badge>
													) : (
														<Badge className="bg-cyan-950/90 text-cyan-300 border-cyan-700 gap-1 text-[11px] font-semibold">
															<Zap className="h-3 w-3 text-cyan-400" /> REGEX RULE
														</Badge>
													)}
													<Badge
														className={
															rule.severity === "CRITICAL"
																? "bg-red-950/80 text-red-400 border-red-800"
																: rule.severity === "HIGH"
																? "bg-amber-950/80 text-amber-400 border-amber-800"
																: "bg-blue-950/80 text-blue-300 border-blue-800"
														}
													>
														{rule.severity}
													</Badge>
													{rule.action === "BLOCK" ? (
														<Badge className="bg-red-950/80 text-red-400 border-red-700 gap-1 text-[11px]">
															<AlertTriangle className="h-3 w-3" /> BLOCK
														</Badge>
													) : (
														<Badge className="bg-amber-950/80 text-amber-300 border-amber-700 gap-1 text-[11px]">
															<AlertCircle className="h-3 w-3" /> REDACT
														</Badge>
													)}
												</div>

												<p className="text-xs text-muted-foreground leading-relaxed break-words">
													{rule.description || "No description provided."}
												</p>

												{rule.warning_message ? (
													<div className="rounded-md border border-amber-800/40 bg-amber-950/20 px-3 py-2">
														<p className="text-[10px] uppercase tracking-wide text-amber-300/80 mb-1">
															{guardRuleNoticeCopy(rule.action === "BLOCK" ? "BLOCK" : "REDACT").listLabel}
														</p>
														<p className="text-xs text-amber-100/90 whitespace-pre-wrap break-words">{rule.warning_message}</p>
													</div>
												) : null}

												{rule.rule_type === "ai_bot" ? (
													<div className="rounded-md border border-purple-900/40 bg-purple-950/20 px-3 py-2 space-y-1">
														{!rule.bot_prompt && !rule.bot_reference_image ? (
															<p className="text-xs text-red-300 font-medium">
																Incomplete — set the Security Policy prompt and/or reference template, then Save.
															</p>
														) : null}
														<div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-purple-300/80">
															<span>AI Security Policy (Prompt)</span>
															<Badge variant="outline" className="text-[10px] py-0 px-1.5 text-purple-300 border-purple-800">
																{rule.bot_provider || GUARD_BOT_OLLAMA_PROVIDER} / {rule.bot_model || GUARD_BOT_OLLAMA_MODEL}
															</Badge>
														</div>
														<p className="text-xs text-purple-100/90 whitespace-pre-wrap break-words font-mono">
															{rule.bot_prompt || "(empty)"}
														</p>
													</div>
												) : (
													<div className="rounded-md border border-border bg-muted/30 px-3 py-2">
														<p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Regex Pattern</p>
														<code className="block text-xs font-mono text-emerald-400 whitespace-pre-wrap break-all">
															{rule.pattern}
														</code>
													</div>
												)}
											</div>

											<div className="flex items-center justify-between gap-3 lg:flex-col lg:items-end lg:justify-start shrink-0 border-t border-border pt-3 lg:border-t-0 lg:pt-0 lg:pl-4">
												<div className="flex items-center gap-2">
													<span className={`text-xs font-medium ${rule.active ? "text-emerald-400" : "text-muted-foreground"}`}>
														{rule.active ? "Active" : "Disabled"}
													</span>
													<Switch
														checked={rule.active}
														onCheckedChange={(val) => updateRule({ id: rule.id, updates: { active: val } })}
													/>
												</div>
												<div className="flex items-center gap-1">
													<Button
														variant="ghost"
														size="icon"
														onClick={() => {
															setEditRule(rule);
															setEditRuleName(rule.name);
															setEditRuleType(rule.rule_type === "ai_bot" ? "ai_bot" : "regex");
															setEditRuleBotProvider(rule.bot_provider || GUARD_BOT_OLLAMA_PROVIDER);
															setEditRuleBotModel(rule.bot_model || GUARD_BOT_OLLAMA_MODEL);
															setEditRuleBotPrompt(rule.bot_prompt || "");
															setEditRuleBotReferenceImage(rule.bot_reference_image || "");
															setEditRuleBotReferenceImageType(rule.bot_reference_image_type || "");
															setEditRuleBotReferenceImagePreview(
																rule.bot_reference_image
																	? referenceImageDataUrl(rule.bot_reference_image, rule.bot_reference_image_type || "image/png")
																	: "",
															);
															setEditRuleSeverity(rule.severity);
															setEditRuleAction(rule.action === "BLOCK" ? "BLOCK" : "REDACT");
															setEditRulePattern(rule.pattern || "");
															setEditRuleDescription(rule.description || "");
															setEditRuleWarningMessage(rule.warning_message || "");
															setEditRuleBotEvalMode("ai");
															setEditRuleGeneratedPattern(rule.pattern || "");
															setEditRuleGenerateError("");
															setEditRuleDialogOpen(true);
														}}
														className="h-8 w-8 text-muted-foreground hover:text-foreground"
														title="Edit Guard Rule"
													>
														<Pencil className="h-4 w-4" />
													</Button>
													<Button
														variant="ghost"
														size="icon"
														onClick={() => deleteRule(rule.id)}
														className="h-8 w-8 text-muted-foreground hover:text-destructive"
														title="Delete Guard Rule"
													>
														<Trash2 className="h-4 w-4" />
													</Button>
												</div>
											</div>
										</div>
									</div>
								))}

								{filteredRules.length === 0 && (
									<div className="rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
										No guard rules found matching your search.
									</div>
								)}
							</div>
						</CardContent>
					</Card>
				</TabsContent>

				{/* TAB 4: TARGET WEBSITES */}
				<TabsContent value="targets" className="space-y-4">
					<Card className="bg-card border-border">
						<CardHeader>
							<div className="flex justify-between items-center">
								<div>
									<CardTitle className="text-lg">Target Web AI Platforms ({targets.length} Monitored)</CardTitle>
									<CardDescription>
										Add domains to monitor prompts, or turn on <strong>Block entire website</strong> to lock the site completely.
										Each parent row keeps <strong>Add subdomain / related host</strong> — use pagination below when you have many platforms.
										proxy.pac includes monitored and locked domains.
									</CardDescription>
								</div>
								<Dialog
									open={targetDialogOpen}
									onOpenChange={(open) => {
										setTargetDialogOpen(open);
										if (!open) {
											setCustomRelatedHosts([{ host: "", role: "" }]);
											setTargetError("");
										}
									}}
								>
									<DialogTrigger asChild>
										<Button className="gap-2">
											<Plus className="h-4 w-4" /> Add Target Domain
										</Button>
									</DialogTrigger>
									<DialogContent className="bg-card border-border text-foreground">
										<DialogHeader>
											<DialogTitle>Add Target Web Domain</DialogTitle>
											<DialogDescription>
												Any domain you add gets the same rules: exact prompt logging, DLP guardrails, and optional upload blocking. Enter hostname only (no https://).
											</DialogDescription>
										</DialogHeader>

										{targetError && <div className="p-3 bg-red-950/60 border border-red-800 text-red-400 rounded-md text-xs">{targetError}</div>}

										<div className="space-y-4 py-3">
											<div className="space-y-2">
												<Label>Domain Name</Label>
												<Input
													placeholder="e.g. gemini.google.com"
													value={newTargetDomain}
													onChange={(e) => setNewTargetDomain(e.target.value)}
												/>
												<p className="text-[11px] text-muted-foreground">
													Subdomains are covered automatically. Label each host: Main UI, Chat domain, or File domain so Guard knows what to intercept.
												</p>
											</div>
											<div className="space-y-2">
												<Label>Host role (main domain)</Label>
												<Select value={newTargetHostRole || "auto"} onValueChange={(v) => setNewTargetHostRole(v === "auto" ? "" : (v as HostRole))}>
													<SelectTrigger>
														<SelectValue placeholder="Auto" />
													</SelectTrigger>
													<SelectContent>
														{HOST_ROLE_OPTIONS.map((opt) => (
															<SelectItem key={opt.value || "auto"} value={opt.value || "auto"}>
																{opt.label}
															</SelectItem>
														))}
													</SelectContent>
												</Select>
											</div>
											<div className="space-y-2 rounded-md border border-border p-3">
												<p className="text-sm font-medium">Add related host</p>
												<p className="text-[11px] text-muted-foreground">
													Add related hosts with a role: Chat domain (prompts), File domain (uploads). Leave Auto if unsure.
												</p>
												{newTargetRelatedGroup ? (
													<div className="space-y-1.5 rounded-md border border-dashed border-border bg-muted/20 p-2">
														<p className="text-[11px] font-medium">{newTargetRelatedGroup.label}</p>
														<p className="text-[10px] text-muted-foreground">{newTargetRelatedGroup.reason}</p>
														<div className="flex flex-wrap gap-1.5 pt-1">
															{newTargetRelatedGroup.hosts.map((host) => {
																const picked = customRelatedHosts.some((v) => normalizeTargetDomain(v.host) === host);
																const already = addedTargetDomains.some((d) => normalizeTargetDomain(d) === host);
																return (
																	<Button
																		key={host}
																		type="button"
																		size="sm"
																		variant={picked || already ? "secondary" : "outline"}
																		className="h-6 px-2 text-[10px] font-mono"
																		disabled={already}
																		onClick={() => fillSuggestedRelatedHost(host)}
																	>
																		{already ? host : picked ? host : `+ ${host}`}
																	</Button>
																);
															})}
														</div>
													</div>
												) : null}
												<div className="space-y-2 pt-1">
													{customRelatedHosts.map((entry, idx) => (
														<div key={idx} className="flex items-center gap-2">
															<Input
																placeholder="e.g. openai.com"
																className="font-mono text-sm flex-1"
																value={entry.host}
																onChange={(e) => {
																	const next = [...customRelatedHosts];
																	next[idx] = { ...next[idx], host: e.target.value };
																	setCustomRelatedHosts(next);
																}}
															/>
															<Select
																value={entry.role || "auto"}
																onValueChange={(v) => {
																	const next = [...customRelatedHosts];
																	next[idx] = { ...next[idx], role: v === "auto" ? "" : (v as HostRole) };
																	setCustomRelatedHosts(next);
																}}
															>
																<SelectTrigger className="w-[130px]">
																	<SelectValue />
																</SelectTrigger>
																<SelectContent>
																	{HOST_ROLE_OPTIONS.map((opt) => (
																		<SelectItem key={opt.value || "auto"} value={opt.value || "auto"}>
																			{opt.label}
																		</SelectItem>
																	))}
																</SelectContent>
															</Select>
															{customRelatedHosts.length > 1 && (
																<Button
																	type="button"
																	variant="ghost"
																	size="icon"
																	onClick={() => setCustomRelatedHosts(customRelatedHosts.filter((_, i) => i !== idx))}
																>
																	<X className="h-4 w-4" />
																</Button>
															)}
														</div>
													))}
													<Button
														type="button"
														variant="outline"
														size="sm"
														className="gap-1"
														onClick={() => setCustomRelatedHosts([...customRelatedHosts, { host: "", role: "" }])}
													>
														<Plus className="h-3.5 w-3.5" /> Add related host
													</Button>
												</div>
											</div>
											<div className="space-y-2">
												<Label>Platform Name</Label>
												<Input placeholder="e.g. Gemini" value={newTargetPlatform} onChange={(e) => setNewTargetPlatform(e.target.value)} />
											</div>
											<div className="flex items-center justify-between gap-4 rounded-md border border-border p-3">
												<div>
													<p className="text-sm font-medium">Block entire website</p>
													<p className="text-xs text-muted-foreground">
														ON = employees cannot open this domain at all. OFF = only filter/block prompts (current Guard mode).
													</p>
												</div>
												<Switch checked={newTargetBlockSite} onCheckedChange={setNewTargetBlockSite} />
											</div>
										</div>
										<DialogFooter>
											<Button variant="outline" onClick={() => setTargetDialogOpen(false)}>
												Cancel
											</Button>
											<Button onClick={handleCreateTarget}>Add Domain</Button>
										</DialogFooter>
									</DialogContent>
								</Dialog>
							</div>

							<div className="relative mt-3">
								<Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
								<Input
									placeholder="Search target websites..."
									value={targetSearch}
									onChange={(e) => setTargetSearch(e.target.value)}
									className="pl-9 bg-background border-border"
								/>
							</div>
						</CardHeader>
						<CardContent>
							<div className="rounded-md border border-border overflow-x-auto">
								<Table className="table-fixed min-w-[980px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[320px]">Domain</TableHead>
											<TableHead className="w-[120px]">Platform Name</TableHead>
											<TableHead className="w-[110px]">Intercepted</TableHead>
											<TableHead className="w-[100px]">Status</TableHead>
											<TableHead className="w-[120px]">Monitoring</TableHead>
											<TableHead className="w-[130px]">Block Website</TableHead>
											<TableHead className="w-[90px] text-right">Actions</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{visibleTargetRows.map(({ tgt, isChild }) => (
											<TableRow key={tgt.id} className={`border-border transition-colors ${isChild ? "bg-muted/15" : "hover:bg-accent/50"}`}>
												<TableCell className="align-top whitespace-normal">
													<div className={isChild ? "pl-5 space-y-1" : "space-y-1.5"}>
														<div className="flex items-center gap-1.5 font-semibold text-sm font-mono min-w-0">
															{isChild ? (
																<CornerDownRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
															) : null}
															<span className="truncate" title={tgt.domain}>{tgt.domain}</span>
															<ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
														</div>
														{isChild ? (
															<p className="text-[10px] text-muted-foreground pl-5">{hostRoleLabel(tgt.host_role)}</p>
														) : (
															<div className="space-y-1.5 pt-0.5">
																{tgt.host_role ? (
																	<p className="text-[10px] text-muted-foreground">{hostRoleLabel(tgt.host_role)}</p>
																) : null}
																{(() => {
																	const leftover = relatedHostOptions(tgt.domain, addedTargetDomains);
																	if (leftover.length === 0) return null;
																	return (
																		<div className="flex flex-wrap gap-1">
																			{leftover.map((host) => (
																				<Button
																					key={host}
																					type="button"
																					variant="outline"
																					size="sm"
																					className="h-6 px-2 text-[10px] font-mono"
																					onClick={() => handleAddRelatedHost(tgt, host)}
																				>
																					+ {host}
																				</Button>
																			))}
																		</div>
																	);
																})()}
																<p className="text-[10px] font-medium text-muted-foreground">Add subdomain / related host</p>
																<div className="flex items-center gap-1 flex-wrap">
																	<Select
																		value={extraHostRoleDrafts[tgt.id] || "auto"}
																		onValueChange={(v) =>
																			setExtraHostRoleDrafts((prev) => ({
																				...prev,
																				[tgt.id]: v === "auto" ? "" : (v as HostRole),
																			}))
																		}
																	>
																		<SelectTrigger className="h-7 text-[10px] w-[110px]">
																			<SelectValue />
																		</SelectTrigger>
																		<SelectContent>
																			{HOST_ROLE_OPTIONS.map((opt) => (
																				<SelectItem key={opt.value || "auto"} value={opt.value || "auto"}>
																					{opt.label}
																				</SelectItem>
																			))}
																		</SelectContent>
																	</Select>
																	<Input
																		id={`subdomain-input-${tgt.id}`}
																		placeholder="e.g. clients6.google.com"
																		className="h-7 text-[10px] font-mono max-w-[200px]"
																		value={extraHostDrafts[tgt.id] || ""}
																		onChange={(e) => setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: e.target.value }))}
																		onKeyDown={(e) => {
																			if (e.key === "Enter") {
																				e.preventDefault();
																				const host = extraHostDrafts[tgt.id];
																				if (host?.trim()) {
																					handleAddRelatedHost(tgt, host, extraHostRoleDrafts[tgt.id] || "");
																					setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: "" }));
																				}
																			}
																		}}
																	/>
																	<Button
																		type="button"
																		variant="secondary"
																		size="sm"
																		className="h-7 px-2 text-[10px] gap-1"
																		onClick={() => {
																			const host = extraHostDrafts[tgt.id];
																			if (host?.trim()) {
																				handleAddRelatedHost(tgt, host, extraHostRoleDrafts[tgt.id] || "");
																				setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: "" }));
																			}
																		}}
																	>
																		<Plus className="h-3 w-3" />
																		Add
																	</Button>
																</div>
															</div>
														)}
													</div>
												</TableCell>
												<TableCell className="text-sm text-muted-foreground truncate" title={tgt.platform_name || ""}>{tgt.platform_name}</TableCell>
												<TableCell className="font-mono text-sm truncate">{tgt.intercepted_count} requests</TableCell>
												<TableCell className="overflow-hidden">
													<Badge
														className={
															tgt.block_site
																? "bg-red-950/80 text-red-400 border-red-800 text-[11px]"
																: tgt.monitored
																	? "bg-emerald-950/80 text-emerald-400 border-emerald-800 text-[11px]"
																	: "bg-slate-800 text-slate-400 border-slate-700 text-[11px]"
														}
													>
														{tgt.block_site ? "BLOCKED" : tgt.monitored ? "MONITORED" : "PAUSED"}
													</Badge>
												</TableCell>
												<TableCell className="overflow-hidden">
													<div className="flex items-center gap-2 min-w-0">
														<Switch
															checked={tgt.monitored}
															onCheckedChange={(val) =>
																updateTarget({
																	id: tgt.id,
																	updates: {
																		monitored: val,
																		status: tgt.block_site ? "BLOCKED" : val ? "MONITORED" : "PAUSED",
																	},
																})
															}
														/>
														<span className="text-xs text-muted-foreground truncate">{tgt.monitored ? "Active" : "Paused"}</span>
													</div>
												</TableCell>
												<TableCell className="overflow-hidden">
													<div className="flex items-center gap-2 min-w-0">
														<Switch
															checked={!!tgt.block_site}
															onCheckedChange={(val) =>
																updateTarget({
																	id: tgt.id,
																	updates: {
																		block_site: val,
																		status: val ? "BLOCKED" : tgt.monitored ? "MONITORED" : "PAUSED",
																	},
																})
															}
														/>
														<span className={`text-xs truncate ${tgt.block_site ? "text-red-400" : "text-muted-foreground"}`}>
															{tgt.block_site ? "Locked" : "Off"}
														</span>
													</div>
												</TableCell>
												<TableCell className="text-right">
													<div className="flex items-center justify-end gap-1">
														{!isChild ? (
															<Button
																variant="ghost"
																size="icon"
																onClick={() => {
																	const el = document.getElementById(`subdomain-input-${tgt.id}`) as HTMLInputElement | null;
																	el?.focus();
																	el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
																}}
																className="h-8 w-8 text-muted-foreground hover:text-foreground"
																title="Add subdomain / related host"
															>
																<Plus className="h-4 w-4" />
															</Button>
														) : null}
														<Button
															variant="ghost"
															size="icon"
															onClick={() => {
																setEditTarget(tgt);
																setEditTargetDomain(tgt.domain);
																setEditTargetPlatform(tgt.platform_name);
																setEditTargetBlockSite(!!tgt.block_site);
																setEditTargetHostRole((tgt.host_role as HostRole) || "");
																setEditTargetDialogOpen(true);
															}}
															className="h-8 w-8 text-muted-foreground hover:text-foreground"
															title="Edit Target Domain"
														>
															<Pencil className="h-4 w-4" />
														</Button>
														<Button
															variant="ghost"
															size="icon"
															onClick={() => deleteTarget(tgt.id)}
															className="h-8 w-8 text-muted-foreground hover:text-destructive"
															title="Delete Target Domain"
														>
															<Trash2 className="h-4 w-4" />
														</Button>
													</div>
												</TableCell>
											</TableRow>
										))}
										{visibleTargetRows.length === 0 && (
											<TableRow>
												<TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
													{targets.length === 0
														? "No target web domains configured."
														: "No target websites found matching your search."}
												</TableCell>
											</TableRow>
										)}
									</TableBody>
								</Table>
							</div>

							{targets.length > 0 ? (
								<div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-border mt-4 text-xs text-muted-foreground">
									<div className="flex items-center gap-2">
										<span className="whitespace-nowrap">Parent domains per page</span>
										<Select
											value={String(targetPageLimit)}
											onValueChange={(v) => setTargetPageLimit(Number(v))}
										>
											<SelectTrigger className="h-8 w-[72px] bg-background border-border">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value="5">5</SelectItem>
												<SelectItem value="10">10</SelectItem>
												<SelectItem value="25">25</SelectItem>
												<SelectItem value="50">50</SelectItem>
											</SelectContent>
										</Select>
										<span>
											Showing {totalTargetParents > 0 ? targetPageOffset + 1 : 0} to{" "}
											{Math.min(targetPageOffset + targetPageLimit, totalTargetParents)} of {totalTargetParents} parent domains
										</span>
									</div>
									<div className="flex items-center gap-2">
										<span>
											Page {targetCurrentPage} of {targetTotalPages}
										</span>
										<div className="flex items-center gap-1">
											<Button
												variant="outline"
												size="icon"
												disabled={targetPageOffset === 0}
												onClick={() => setTargetPageOffset(Math.max(0, targetPageOffset - targetPageLimit))}
												className="h-8 w-8 border-border"
											>
												<ChevronLeft className="h-4 w-4" />
											</Button>
											<Button
												variant="outline"
												size="icon"
												disabled={targetPageOffset + targetPageLimit >= totalTargetParents}
												onClick={() => setTargetPageOffset(targetPageOffset + targetPageLimit)}
												className="h-8 w-8 border-border"
											>
												<ChevronRight className="h-4 w-4" />
											</Button>
										</div>
									</div>
								</div>
							) : null}
						</CardContent>
					</Card>
				</TabsContent>

				{/* EDIT TARGET DIALOG */}
				<Dialog open={editTargetDialogOpen} onOpenChange={setEditTargetDialogOpen}>
					<DialogContent className="bg-card border-border text-foreground">
						<DialogHeader>
							<DialogTitle>Edit Target Web Domain</DialogTitle>
							<DialogDescription>Modify domain, platform name, or full-site lock.</DialogDescription>
						</DialogHeader>
						<div className="space-y-4 py-3">
							<div className="space-y-2">
								<Label>Domain Name</Label>
								<Input value={editTargetDomain} onChange={(e) => setEditTargetDomain(e.target.value)} />
							</div>
							<div className="space-y-2">
								<Label>Platform Name</Label>
								<Input value={editTargetPlatform} onChange={(e) => setEditTargetPlatform(e.target.value)} />
							</div>
							<div className="space-y-2">
								<Label>Host role</Label>
								<Select value={editTargetHostRole || "auto"} onValueChange={(v) => setEditTargetHostRole(v === "auto" ? "" : (v as HostRole))}>
									<SelectTrigger>
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										{HOST_ROLE_OPTIONS.map((opt) => (
											<SelectItem key={opt.value || "auto"} value={opt.value || "auto"}>
												{opt.label}
											</SelectItem>
										))}
									</SelectContent>
								</Select>
							</div>
							<div className="flex items-center justify-between gap-4 rounded-md border border-border p-3">
								<div>
									<p className="text-sm font-medium">Block entire website</p>
									<p className="text-xs text-muted-foreground">
										ON = cannot open this domain. OFF = prompt Guard only.
									</p>
								</div>
								<Switch checked={editTargetBlockSite} onCheckedChange={setEditTargetBlockSite} />
							</div>
						</div>
						<DialogFooter>
							<Button variant="outline" onClick={() => setEditTargetDialogOpen(false)}>
								Cancel
							</Button>
							<Button onClick={handleEditTarget}>Save Changes</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>

				{/* EDIT RULE DIALOG */}
				<Dialog open={editRuleDialogOpen} onOpenChange={setEditRuleDialogOpen}>
					<DialogContent className="bg-card border-border text-foreground w-[calc(100%-2rem)] sm:max-w-xl max-h-[88vh] flex flex-col p-0 overflow-hidden">
						<DialogHeader className="p-5 pb-3 shrink-0 border-b border-border/60">
							<DialogTitle className="flex items-center gap-2 text-base">
								<Pencil className="h-5 w-5 text-primary" />
								Edit Guard Rule
							</DialogTitle>
							<DialogDescription className="text-xs">Modify rule engine parameters, action, and notification messages.</DialogDescription>
						</DialogHeader>

						{ruleError && <div className="mx-5 mt-3 p-3 bg-red-950/60 border border-red-800 text-red-400 rounded-md text-xs">{ruleError}</div>}

						<div className="flex-1 overflow-y-auto overflow-x-hidden px-5 py-4 space-y-4 min-w-0">
							{/* Rule Engine Type Toggle */}
							<div className="space-y-1.5">
								<Label>Rule Engine Type</Label>
								<div className="grid grid-cols-2 gap-2 p-1 bg-muted/40 rounded-lg border border-border">
									<button
										type="button"
										onClick={() => {
											setEditRuleType("regex");
										}}
										className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
											editRuleType === "regex"
												? "bg-primary text-primary-foreground shadow-sm"
												: "text-muted-foreground hover:text-foreground"
										}`}
									>
										<Zap className="h-3.5 w-3.5" />
										Regex Pattern Rule
									</button>
									<button
										type="button"
										onClick={() => {
											setEditRuleType("ai_bot");
											setEditRuleBotProvider(GUARD_BOT_OLLAMA_PROVIDER);
											setEditRuleBotModel(GUARD_BOT_OLLAMA_MODEL);
										}}
										className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
											editRuleType === "ai_bot"
												? "bg-purple-600 text-white shadow-sm"
												: "text-muted-foreground hover:text-foreground"
										}`}
									>
										<Bot className="h-3.5 w-3.5" />
										AI Guard Bot (Prompt Rule)
									</button>
								</div>
							</div>

							<div className="space-y-1.5">
								<Label>Rule Name</Label>
								<Input value={editRuleName} onChange={(e) => setEditRuleName(e.target.value)} />
							</div>

							<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
								<div className="space-y-1.5 min-w-0">
									<Label>Severity</Label>
									<Select value={editRuleSeverity} onValueChange={(v: any) => setEditRuleSeverity(v)}>
										<SelectTrigger className="w-full">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="CRITICAL">CRITICAL</SelectItem>
											<SelectItem value="HIGH">HIGH</SelectItem>
											<SelectItem value="MEDIUM">MEDIUM</SelectItem>
										</SelectContent>
									</Select>
								</div>
								<div className="space-y-1.5 min-w-0">
									<Label>Action</Label>
									<Select value={editRuleAction} onValueChange={(v: any) => setEditRuleAction(v)}>
										<SelectTrigger className="w-full">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="BLOCK">BLOCK</SelectItem>
											<SelectItem value="REDACT">REDACT</SelectItem>
										</SelectContent>
									</Select>
									<p className="text-[11px] text-muted-foreground break-words">
										{guardRuleActionHint(editRuleAction)}
									</p>
								</div>
							</div>

							{editRuleType === "regex" ? (
								<div className="space-y-1.5">
									<Label>Regex Pattern</Label>
									<Input value={editRulePattern} onChange={(e) => setEditRulePattern(e.target.value)} />
									<p className="text-[11px] text-muted-foreground">
										Evaluated in microseconds using Golang RE2 regular expressions.
									</p>
								</div>
							) : (
								<GuardRuleAIEvaluatorFields
									botProvider={editRuleBotProvider}
									botModel={editRuleBotModel}
									botPrompt={editRuleBotPrompt}
									referenceImagePreview={editRuleBotReferenceImagePreview}
									evalMode={editRuleBotEvalMode}
									generatedPattern={editRuleGeneratedPattern}
									generateError={editRuleGenerateError}
									generating={generatingRegex}
									outsourceProviderOptions={outsourceProviderOptions}
									onProviderChange={setEditRuleBotProvider}
									onModelChange={setEditRuleBotModel}
									onPromptChange={setEditRuleBotPrompt}
									onEvalModeChange={setEditRuleBotEvalMode}
									onGeneratedPatternChange={setEditRuleGeneratedPattern}
									onGenerateRegex={() => runGenerateRegex("edit")}
									onReferenceImageClear={() => {
										setEditRuleBotReferenceImage("");
										setEditRuleBotReferenceImageType("");
										setEditRuleBotReferenceImagePreview("");
									}}
									onReferenceImageChange={async (file) => {
										try {
											const { data, type } = await readReferenceImageFile(file);
											setEditRuleBotReferenceImage(data);
											setEditRuleBotReferenceImageType(type);
											setEditRuleBotReferenceImagePreview(referenceImageDataUrl(data, type));
										} catch (err: any) {
											setRuleError(err?.message || "Failed to load reference image.");
										}
									}}
								/>
							)}

							<div className="space-y-1.5">
								<Label>Description</Label>
								<Textarea value={editRuleDescription} onChange={(e) => setEditRuleDescription(e.target.value)} />
							</div>
							<div className="space-y-1.5">
								<Label>{guardRuleNoticeCopy(editRuleAction).label}</Label>
								<Textarea
									value={editRuleWarningMessage}
									onChange={(e) => setEditRuleWarningMessage(e.target.value)}
									placeholder={guardRuleNoticeCopy(editRuleAction).placeholder}
									rows={3}
								/>
								<p className="text-xs text-muted-foreground break-words">
									{guardRuleNoticeCopy(editRuleAction).hint}
								</p>
							</div>
						</div>
						<DialogFooter className="p-4 px-5 shrink-0 border-t border-border/60 bg-card">
							<Button variant="outline" onClick={() => setEditRuleDialogOpen(false)}>
								Cancel
							</Button>
							<Button onClick={handleEditRuleSubmit}>Save Changes</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>

				{/* TAB 5: GUARD AGENTS */}
				<TabsContent value="agents" className="space-y-6">
					<div className="flex flex-col sm:flex-row gap-3">
						<div className="relative flex-1 max-w-md">
							<Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
							<Input
								placeholder="Search hostname, user, IP, MAC, agent id..."
								className="pl-9"
								value={agentSearch}
								onChange={(e) => {
									setAgentSearch(e.target.value);
									setAgentPageOffset(0);
								}}
							/>
						</div>
						<Select
							value={agentStatusFilter}
							onValueChange={(v) => {
								setAgentStatusFilter(v);
								setAgentPageOffset(0);
							}}
						>
							<SelectTrigger className="w-[160px]">
								<SelectValue placeholder="Status" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">All statuses</SelectItem>
								<SelectItem value="active">Active</SelectItem>
								<SelectItem value="uninstall_pending">Uninstall pending</SelectItem>
								<SelectItem value="uninstalled">Uninstalled</SelectItem>
							</SelectContent>
						</Select>
					</div>

					<div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription>Total registered</CardDescription>
								<CardTitle className="text-2xl">{totalAgents}</CardTitle>
							</CardHeader>
						</Card>
						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription>Active (this page)</CardDescription>
								<CardTitle className="text-2xl text-emerald-400">{activeAgentsCount}</CardTitle>
							</CardHeader>
						</Card>
						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription>Uninstall key</CardDescription>
								<CardTitle className="text-lg">
									{agentSettings?.key_configured ? "Configured" : "Not set"}
									{agentSettings?.require_uninstall_key ? " · Required" : " · Optional"}
								</CardTitle>
							</CardHeader>
						</Card>
					</div>

					<Card className="bg-card border-border">
						<CardHeader>
							<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
								<div>
									<CardTitle className="text-lg">Installed Guard laptops</CardTitle>
									<CardDescription>
										Chrome, Edge, Brave, Opera, Vivaldi, and Firefox — same Guard behavior. Fully quit & reopen after install. Safari is macOS-only.
									</CardDescription>
								</div>
								<div className="flex items-center gap-2">
									{selectedAgentCount > 0 ? (
										<span className="text-xs text-muted-foreground whitespace-nowrap">
											{selectedAgentCount} selected
										</span>
									) : null}
									<Select
										value={agentBulkAction}
										onValueChange={handleAgentBulkAction}
										disabled={selectedAgentCount === 0 || deletingAgents}
									>
										<SelectTrigger className="w-[160px]">
											<SelectValue placeholder="Choose option" />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="delete" className="text-destructive focus:text-destructive">
												Delete
											</SelectItem>
										</SelectContent>
									</Select>
								</div>
							</div>
						</CardHeader>
						<CardContent className="p-0">
							<Table className="table-fixed min-w-[1100px]">
								<TableHeader>
									<TableRow className="hover:bg-transparent border-border">
										<TableHead className="w-[44px]">
											<Checkbox
												checked={allVisibleAgentsSelected || (someVisibleAgentsSelected ? "indeterminate" : false)}
												onCheckedChange={(checked) => toggleSelectAllVisibleAgents(checked === true)}
												aria-label="Select all Guard agents on this page"
												disabled={agents.length === 0}
											/>
										</TableHead>
										<TableHead className="w-[160px]">Laptop</TableHead>
										<TableHead className="w-[100px]">User</TableHead>
										<TableHead className="w-[120px]">IP</TableHead>
										<TableHead className="w-[140px]">Physical address (MAC)</TableHead>
										<TableHead className="w-[140px]">Transport name</TableHead>
										<TableHead className="w-[80px]">Version</TableHead>
										<TableHead className="w-[120px]">Status</TableHead>
										<TableHead className="w-[150px]">Last seen</TableHead>
										<TableHead className="w-[150px]">Installed</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{agents.map((agent) => (
										<TableRow key={agent.id} className="border-border">
											<TableCell>
												<Checkbox
													checked={selectedAgentIds.has(agent.id)}
													onCheckedChange={(checked) => toggleSelectAgent(agent.id, checked === true)}
													aria-label={`Select ${agent.hostname || agent.id}`}
												/>
											</TableCell>
											<TableCell className="align-top whitespace-normal">
												<div className="font-medium text-sm truncate" title={agent.hostname || ""}>
													{agent.hostname || "—"}
												</div>
												<div className="text-[11px] text-muted-foreground font-mono truncate" title={agent.id}>
													{agent.id}
												</div>
											</TableCell>
											<TableCell className="text-sm truncate">{agent.username || "—"}</TableCell>
											<TableCell className="text-xs font-mono truncate">{agent.ip_address || "—"}</TableCell>
											<TableCell className="text-xs font-mono truncate" data-testid="guard-agent-mac-cell" title={agent.mac_address || ""}>
												{agent.mac_address || "—"}
											</TableCell>
											<TableCell className="text-[11px] font-mono text-muted-foreground truncate" data-testid="guard-agent-transport-cell" title={nicGuidOnly(agent.transport_name) || ""}>
												{nicGuidOnly(agent.transport_name) || "—"}
											</TableCell>
											<TableCell className="text-xs truncate font-medium">{agent.agent_version || "—"}</TableCell>
											<TableCell>{getAgentStatusBadge(agent.status, agent.uninstall_requested)}</TableCell>
											<TableCell className="text-xs text-muted-foreground truncate">
												{agent.last_seen_at ? new Date(agent.last_seen_at).toLocaleString() : "—"}
											</TableCell>
											<TableCell className="text-xs text-muted-foreground truncate">
												{agent.installed_at ? new Date(agent.installed_at).toLocaleString() : "—"}
											</TableCell>
										</TableRow>
									))}
									{agents.length === 0 && (
										<TableRow>
											<TableCell colSpan={10} className="text-center py-10 text-muted-foreground text-sm">
												No Guard agents registered yet. Install UnifAI_Guard_Setup.exe on employee laptops.
											</TableCell>
										</TableRow>
									)}
								</TableBody>
							</Table>
						</CardContent>
					</Card>

					{totalAgents > agentPageLimit && (
						<div className="flex items-center justify-end gap-2">
							<Button
								variant="outline"
								size="sm"
								disabled={agentPageOffset === 0}
								onClick={() => setAgentPageOffset(Math.max(0, agentPageOffset - agentPageLimit))}
							>
								<ChevronLeft className="h-4 w-4" />
							</Button>
							<span className="text-xs text-muted-foreground">
								{agentPageOffset + 1}–{Math.min(agentPageOffset + agentPageLimit, totalAgents)} of {totalAgents}
							</span>
							<Button
								variant="outline"
								size="sm"
								disabled={agentPageOffset + agentPageLimit >= totalAgents}
								onClick={() => setAgentPageOffset(agentPageOffset + agentPageLimit)}
							>
								<ChevronRight className="h-4 w-4" />
							</Button>
						</div>
					)}

					<AlertDialog
						open={showAgentDeleteDialog}
						onOpenChange={(open) => {
							setShowAgentDeleteDialog(open);
							if (!open) {
								setAgentBulkAction("");
								setAgentDeleteError("");
							}
						}}
					>
						<AlertDialogContent>
							<AlertDialogHeader>
								<AlertDialogTitle>Delete selected Guard agents?</AlertDialogTitle>
								<AlertDialogDescription>
									This removes {selectedAgentCount} selected {selectedAgentCount === 1 ? "record" : "records"} from the Guard Agents list.
									Installed agents on employee laptops are not uninstalled automatically.
								</AlertDialogDescription>
							</AlertDialogHeader>
							{agentDeleteError ? <p className="text-sm text-red-400">{agentDeleteError}</p> : null}
							<AlertDialogFooter>
								<AlertDialogCancel disabled={deletingAgents}>Cancel</AlertDialogCancel>
								<AlertDialogAction
									onClick={(e) => {
										e.preventDefault();
										void handleDeleteSelectedAgents();
									}}
									disabled={deletingAgents || selectedAgentCount === 0}
									className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
								>
									{deletingAgents ? "Deleting..." : "Delete"}
								</AlertDialogAction>
							</AlertDialogFooter>
						</AlertDialogContent>
					</AlertDialog>
				</TabsContent>

				{/* TAB 6: SETUP */}
				<TabsContent value="setup" className="space-y-6">
					<Card className="bg-card border-border">
						<CardHeader>
							<div className="flex items-center gap-3">
								<FileKey className="h-6 w-6 text-amber-400" />
								<div>
									<CardTitle className="text-lg">Uninstall Key</CardTitle>
									<CardDescription>
										Employees can remove Guard only when this key matches (if required). Key is stored hashed in unifai_new.
									</CardDescription>
								</div>
							</div>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="flex items-center justify-between gap-4 rounded-md border border-border p-3">
								<div>
									<p className="text-sm font-medium">Require uninstall key</p>
									<p className="text-xs text-muted-foreground">When off, Windows uninstall proceeds without a key check.</p>
								</div>
								<Switch
									checked={!!agentSettings?.require_uninstall_key}
									onAsyncCheckedChange={async (checked) => {
										await handleToggleRequireUninstallKey(checked);
									}}
								/>
							</div>
							<div className="space-y-3">
								{agentSettings?.key_configured && !uninstallKeyEditing ? (
									<div className="space-y-2 rounded-md border border-border p-3">
										<div className="flex items-center justify-between gap-2">
											<Label>Saved uninstall key</Label>
											<p className="text-xs text-muted-foreground">
												{agentSettings?.updated_at ? `Updated ${new Date(agentSettings.updated_at).toLocaleString()}` : "Configured"}
											</p>
										</div>
										<div className="flex flex-col sm:flex-row gap-2">
											<div className="relative min-w-0 flex-1">
												<Input
													readOnly
													type={showUninstallKey && savedUninstallKeyDisplay ? "text" : "password"}
													value={
														showUninstallKey && savedUninstallKeyDisplay
															? savedUninstallKeyDisplay
															: savedUninstallKeyDisplay || "••••••••••••••••••••"
													}
													className="pr-10 font-mono"
												/>
												<Button
													type="button"
													variant="ghost"
													size="icon"
													className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-muted-foreground hover:text-foreground"
													onClick={() => {
														if (!savedUninstallKeyDisplay) {
															setUninstallKeyMessage(
																"Full key is not stored in plain text. Click Edit, enter the key again, then Save — eye can show it in this session.",
															);
															return;
														}
														setShowUninstallKey((v) => !v);
													}}
													title={
														!savedUninstallKeyDisplay
															? "Key hashed — re-save to view"
															: showUninstallKey
																? "Hide key"
																: "Show key"
													}
												>
													{showUninstallKey && savedUninstallKeyDisplay ? (
														<EyeOff className="h-4 w-4" />
													) : (
														<Eye className="h-4 w-4" />
													)}
												</Button>
											</div>
											<Button
												variant="outline"
												className="gap-2 shrink-0"
												onClick={() => {
													setUninstallKeyEditing(true);
													setUninstallKeyInput("");
													setUninstallKeyMessage("");
													setUninstallKeyError("");
													setShowUninstallKey(false);
												}}
											>
												<Pencil className="h-4 w-4" />
												Edit
											</Button>
										</div>
										{!savedUninstallKeyDisplay ? (
											<p className="text-xs text-muted-foreground">
												Key is stored hashed on the server. Full value is shown only right after you Save in this session — use Edit to rotate.
											</p>
										) : null}
									</div>
								) : (
									<div className="space-y-2">
										<Label>{agentSettings?.key_configured ? "Edit / rotate uninstall key" : "Set uninstall key"}</Label>
										<div className="flex flex-col sm:flex-row gap-2">
											<div className="relative min-w-0 flex-1">
												<Input
													type={showUninstallKey ? "text" : "password"}
													placeholder={agentSettings?.key_configured ? "Enter new key to rotate…" : "Enter company uninstall key…"}
													value={uninstallKeyInput}
													onChange={(e) => setUninstallKeyInput(e.target.value)}
													autoComplete="new-password"
													className="pr-10 font-mono"
												/>
												<Button
													type="button"
													variant="ghost"
													size="icon"
													className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-muted-foreground hover:text-foreground"
													onClick={() => setShowUninstallKey((v) => !v)}
													title={showUninstallKey ? "Hide key" : "Show key"}
												>
													{showUninstallKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
												</Button>
											</div>
											<Button onClick={handleSaveUninstallKey} disabled={savingUninstallKey || !uninstallKeyInput.trim()} className="gap-2 shrink-0">
												<Save className="h-4 w-4" />
												{savingUninstallKey ? "Saving…" : "Save"}
											</Button>
											{agentSettings?.key_configured ? (
												<Button
													type="button"
													variant="outline"
													className="shrink-0"
													onClick={() => {
														setUninstallKeyEditing(false);
														setUninstallKeyInput("");
														setUninstallKeyError("");
													}}
													disabled={savingUninstallKey}
												>
													Cancel
												</Button>
											) : null}
										</div>
									</div>
								)}
								{uninstallKeyMessage ? <p className="text-sm text-emerald-400">{uninstallKeyMessage}</p> : null}
								{uninstallKeyError ? <p className="text-sm text-red-400">{uninstallKeyError}</p> : null}
							</div>
						</CardContent>
					</Card>

					<Card className="bg-card border-border">
						<CardHeader>
							<div className="flex justify-between items-center gap-4">
								<div className="flex items-center gap-3">
									<CheckCircle2 className="h-6 w-6 text-emerald-400" />
									<div>
										<CardTitle className="text-lg">Employee Setup Package</CardTitle>
										<CardDescription>Download a ZIP with the Guard Windows installer only.</CardDescription>
									</div>
								</div>
								<Button onClick={handleDownloadSetupPackage} disabled={setupPackageDownloading} className="gap-2">
									<Download className="h-4 w-4" />
									{setupPackageDownloading ? "Preparing..." : "Download Setup ZIP"}
								</Button>
							</div>
						</CardHeader>
						<CardContent className="pt-0">
							<p className="text-sm text-muted-foreground">
								ZIP contains <code className="bg-black/40 px-1 rounded">UnifAI_Guard_Setup.exe</code> only. Backend config is already inside the installer.
							</p>
							{setupPackageError ? <p className="mt-3 text-sm text-red-400">{setupPackageError}</p> : null}
						</CardContent>
					</Card>

					<Card className="bg-card border-border">
						<CardHeader>
							<CardTitle className="text-lg">Install Steps</CardTitle>
							<CardDescription>Download the ZIP, extract the installer, and run it on the employee laptop.</CardDescription>
						</CardHeader>
						<CardContent className="space-y-6">
							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">1</span>
									<span>Download the ZIP package</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Click <strong>Download Setup ZIP</strong> above. The ZIP includes only <code className="bg-black/40 px-1 rounded">UnifAI_Guard_Setup.exe</code>.
								</p>
							</div>

							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">2</span>
									<span>Extract and run the installer</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Extract the ZIP, then run <code className="bg-black/40 px-1 rounded">UnifAI_Guard_Setup.exe</code>. Keep the autostart option enabled so Guard runs automatically at Windows login.
								</p>
							</div>

							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">3</span>
									<span>Open monitored AI websites and verify logs</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Have the employee open ChatGPT, Gemini, Claude, Copilot, or DeepSeek and send a test prompt. Use Prompt Logs above to confirm interception.
								</p>
							</div>

							<div className="rounded-md border border-border bg-background p-4 text-xs space-y-2">
								<p className="font-semibold text-foreground">ZIP contents</p>
								<ul className="list-disc pl-5 text-muted-foreground space-y-1">
									<li><code>UnifAI_Guard_Setup.exe</code> — employee installer (only file)</li>
								</ul>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>

			{/* Prompt Details — centered modal */}
			<Dialog
				open={!!selectedLog}
				onOpenChange={(open) => {
					if (!open) setSelectedLog(null);
				}}
			>
				<DialogContent
					disableOutsideClick={false}
					className="bg-card border-border text-foreground sm:max-w-2xl w-[calc(100%-2rem)] p-0 gap-0 overflow-hidden flex flex-col max-h-[min(88vh,860px)]"
				>
					{selectedLog && (
						<>
							<DialogHeader className="px-6 pt-5 pb-4 shrink-0 border-b border-border/70 space-y-1.5 text-left">
								<DialogTitle className="flex flex-wrap items-center gap-2 text-lg pr-8">
									Prompt Details
									{getPlatformBadge(selectedLog.platform)}
								</DialogTitle>
								<DialogDescription className="text-xs">
									Captured {new Date(selectedLog.timestamp).toLocaleString()}
								</DialogDescription>
							</DialogHeader>

							<div className="px-6 py-5 space-y-5 overflow-y-auto flex-1 min-h-0">
								<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
									<div className="rounded-lg border border-border/80 bg-background/60 p-3.5 space-y-1.5">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Action / Status</Label>
										<div className="space-y-1">
											{logActionBadge(selectedLog)}
											{selectedLog.status ? (
												<p className="text-[11px] text-muted-foreground leading-snug">{selectedLog.status}</p>
											) : null}
										</div>
									</div>
									<div className="rounded-lg border border-border/80 bg-background/60 p-3.5 space-y-1.5">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Guard laptop</Label>
										<p className="text-sm font-medium truncate">{selectedLog.agent_hostname || "—"}</p>
										<p className="text-[11px] text-muted-foreground font-mono truncate">
											{selectedLog.agent_id || selectedLog.client_ip || ""}
										</p>
									</div>
								</div>

								{(() => {
									const v = securityVerdictFromLog(selectedLog);
									const tone =
										v.tone === "ok"
											? "border-emerald-800 bg-emerald-950/30 text-emerald-100"
											: v.tone === "bad"
												? "border-red-800 bg-red-950/30 text-red-100"
												: v.tone === "warn"
													? "border-amber-800 bg-amber-950/30 text-amber-100"
													: "border-border bg-background/60 text-foreground";
									return (
										<div className={`rounded-lg border p-3.5 space-y-1 ${tone}`}>
											<p className="text-[11px] uppercase tracking-wide opacity-80">Security analysis</p>
											<p className="text-sm font-semibold">{v.title}</p>
											{v.detail ? <p className="text-xs opacity-90">{v.detail}</p> : null}
										</div>
									);
								})()}

								<div className="rounded-lg border border-border/80 bg-background/60 p-4 space-y-2.5">
									<div className="flex justify-between items-center text-xs font-semibold gap-3">
										<span className="flex items-center gap-1.5 text-purple-300">
											<BrainCircuit className="h-4 w-4 shrink-0" /> Predictive Risk Score
										</span>
										<span
											className={
												(selectedLog.risk_score || 0) >= 70
													? "text-red-400 font-bold"
													: (selectedLog.risk_score || 0) >= 40
														? "text-amber-400"
														: "text-emerald-400"
											}
										>
											{selectedLog.risk_score || 10}% ({selectedLog.predictive_risk || "LOW"})
										</span>
									</div>
									<div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
										<div
											className={`h-full rounded-full transition-all ${
												(selectedLog.risk_score || 0) >= 70
													? "bg-red-500"
													: (selectedLog.risk_score || 0) >= 40
														? "bg-amber-500"
														: "bg-emerald-500"
											}`}
											style={{ width: `${Math.min(100, Math.max(5, selectedLog.risk_score || 10))}%` }}
										/>
									</div>
									<div className="flex flex-wrap justify-between gap-2 text-[11px] text-muted-foreground pt-0.5">
										<span>
											Category: <code className="text-foreground">{selectedLog.predicted_category || "SAFE"}</code>
										</span>
										<span>Threat Level: {selectedLog.predictive_risk || "LOW"}</span>
									</div>
								</div>

								<div className="space-y-2">
									<div className="flex justify-between items-center gap-2">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">
											{isFileUploadLog(selectedLog) ? "File upload event" : "Full Intercepted Prompt Text"}
										</Label>
										<Button
											variant="ghost"
											size="sm"
											onClick={() =>
												handleCopyPrompt(
													isFileUploadLog(selectedLog)
														? logFileStatusLine(selectedLog)
														: selectedLog.user_prompt_full,
												)
											}
											className="h-7 text-xs gap-1 shrink-0"
										>
											{copiedPrompt ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
											{copiedPrompt ? "Copied" : "Copy"}
										</Button>
									</div>
									<div className="p-3.5 bg-background border border-border rounded-lg font-mono text-xs max-h-52 overflow-y-auto whitespace-pre-wrap leading-relaxed">
										{isFileUploadLog(selectedLog)
											? logFileStatusLine(selectedLog)
											: selectedLog.user_prompt_full}
									</div>
									{isFileUploadLog(selectedLog) && logExtractedTextFromPrompt(selectedLog) ? (
										<p className="text-[11px] text-muted-foreground">
											Extracted file text is available under <strong className="font-medium text-foreground">View → Extracted text</strong>.
										</p>
									) : null}
								</div>

								{isFileUploadLog(selectedLog) ? (
									<div className="rounded-lg border border-sky-900/50 bg-sky-950/20 p-3.5 flex flex-wrap items-center justify-between gap-3">
										<div className="flex min-w-0 items-center gap-2">
											<Paperclip className="h-4 w-4 shrink-0 text-sky-400" />
											<div className="min-w-0">
												<p className="text-[11px] uppercase tracking-wide text-muted-foreground">Attached file</p>
												<p className="text-sm font-medium truncate">{logAttachmentLabel(selectedLog)}</p>
											</div>
										</div>
										{logHasStoredAttachment(selectedLog) ? (
											<div className="flex items-center gap-2 shrink-0">
												<Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={() => openPdfViewer(selectedLog)}>
													<Eye className="h-3.5 w-3.5" /> View
												</Button>
												<Button size="sm" className="h-8 gap-1.5" onClick={() => downloadPdfAttachment(selectedLog)}>
													<Download className="h-3.5 w-3.5" /> Download
												</Button>
											</div>
										) : (
											<p className="text-xs text-muted-foreground shrink-0 max-w-[14rem] text-right leading-snug">
												{(selectedLog.action || "").toLowerCase() === "blocked"
													? "File bytes not stored — View unavailable for this block event"
													: "Filename logged — file bytes not stored yet"}
											</p>
										)}
									</div>
								) : null}

								<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
									<div className="rounded-lg border border-border/80 bg-background/60 p-3.5 space-y-1">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Estimated Tokens</Label>
										<p className="text-sm font-semibold">{selectedLog.est_tokens} tokens</p>
									</div>
									<div className="rounded-lg border border-border/80 bg-background/60 p-3.5 space-y-1">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Violated Rule</Label>
										<p className={`text-sm font-semibold ${selectedLog.rule_triggered && selectedLog.action !== "Allowed" ? "text-purple-300" : "text-muted-foreground"}`}>
											{selectedLog.action === "Allowed" && (selectedLog.predicted_category || "").toUpperCase() === "AI_GUARD_BOT_CLEAR"
												? "None (checked — no violation)"
												: (selectedLog.rule_triggered || "None")}
										</p>
									</div>
								</div>

								{isFileUploadLog(selectedLog) && logExtractedText(selectedLog) ? (
									<div className="space-y-2">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Extracted file text (used for bot check)</Label>
										<pre className="p-3.5 bg-background border border-border rounded-lg font-mono text-[11px] max-h-36 overflow-auto whitespace-pre-wrap break-words">
											{logExtractedText(selectedLog).slice(0, 4000)}
										</pre>
									</div>
								) : null}

								{selectedLog.metadata ? (
									<div className="space-y-2">
										<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Metadata Payload</Label>
										<pre className="p-3.5 bg-background border border-border rounded-lg font-mono text-[11px] max-h-36 overflow-auto">
											{(() => {
												try {
													return JSON.stringify(JSON.parse(selectedLog.metadata || "{}"), null, 2);
												} catch {
													return selectedLog.metadata;
												}
											})()}
										</pre>
									</div>
								) : null}
							</div>
						</>
					)}
				</DialogContent>
			</Dialog>

			{/* Attachment viewer — centered popup (PDF / image / download others) */}
			<Dialog
				open={!!pdfViewerLog}
				onOpenChange={(open) => {
					if (!open) {
						setPdfViewerLog(null);
						setPdfViewerTab("preview");
						setPdfError("");
						setAttachmentPreviewKind(null);
						setAttachmentPreviewHtml("");
						setAttachmentPreviewText("");
					}
				}}
			>
				<DialogContent
					disableOutsideClick={false}
					className="bg-card border-border text-foreground sm:max-w-4xl w-[calc(100%-2rem)] p-0 gap-0 overflow-hidden flex flex-col max-h-[min(92vh,920px)]"
				>
					{pdfViewerLog && (
						<>
							<DialogHeader className="px-5 pt-4 pb-3 shrink-0 border-b border-border/70 space-y-1 text-left">
								<DialogTitle className="flex flex-wrap items-center gap-2 text-base pr-8">
									<FileText className="h-4 w-4 text-sky-400" />
									{logAttachmentLabel(pdfViewerLog)}
								</DialogTitle>
								<DialogDescription className="text-xs">
									{pdfViewerLog.platform} · {pdfViewerLog.action || "—"} · Captured{" "}
									{new Date(pdfViewerLog.timestamp).toLocaleString()}
								</DialogDescription>
							</DialogHeader>
							<div className="px-5 py-3 flex flex-wrap items-center gap-2 shrink-0 border-b border-border/50">
								<Button size="sm" className="h-8 gap-1.5" onClick={() => downloadPdfAttachment(pdfViewerLog)} disabled={pdfLoading}>
									<Download className="h-3.5 w-3.5" /> Download
								</Button>
								<div className="flex rounded-md border border-border overflow-hidden">
									<Button
										size="sm"
										variant={pdfViewerTab === "preview" ? "default" : "ghost"}
										className="h-8 rounded-none"
										onClick={() => setPdfViewerTab("preview")}
									>
										Preview
									</Button>
									{(isFileUploadLog(pdfViewerLog) || logExtractedText(pdfViewerLog, attachmentPreviewText)) && (
										<Button
											size="sm"
											variant={pdfViewerTab === "extracted" ? "default" : "ghost"}
											className="h-8 rounded-none"
											onClick={() => setPdfViewerTab("extracted")}
										>
											Extracted text
										</Button>
									)}
									<Button
										size="sm"
										variant={pdfViewerTab === "details" ? "default" : "ghost"}
										className="h-8 rounded-none"
										onClick={() => setPdfViewerTab("details")}
									>
										Prompt details
									</Button>
								</div>
							</div>
							<div className="flex-1 min-h-0 bg-black/40 flex items-center justify-center p-3 overflow-auto">
								{pdfViewerTab === "details" ? (
									<div className="w-full max-h-[min(70vh,720px)] overflow-auto rounded-md border border-border bg-background p-4 space-y-3">
										<div className="flex flex-wrap items-center justify-between gap-2">
											<p className="text-xs text-muted-foreground">
												{pdfViewerLog.platform} · {pdfViewerLog.action || "—"}
												{pdfViewerLog.rule_triggered ? ` · ${pdfViewerLog.rule_triggered}` : ""}
											</p>
											<Button
												variant="ghost"
												size="sm"
												onClick={() =>
													handleCopyPrompt(
														isFileUploadLog(pdfViewerLog)
															? logFileStatusLine(pdfViewerLog)
															: pdfViewerLog.user_prompt_full || pdfViewerLog.user_prompt_preview || "",
													)
												}
												className="h-7 text-xs gap-1 shrink-0"
											>
												{copiedPrompt ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
												{copiedPrompt ? "Copied" : "Copy"}
											</Button>
										</div>
										<pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed">
											{isFileUploadLog(pdfViewerLog)
												? logFileStatusLine(pdfViewerLog) || "File upload event."
												: pdfViewerLog.user_prompt_full || pdfViewerLog.user_prompt_preview || "No prompt text captured."}
										</pre>
									</div>
								) : pdfViewerTab === "extracted" ? (
									<div className="w-full max-h-[min(70vh,720px)] overflow-auto rounded-md border border-border bg-background p-4 space-y-2">
										<p className="text-xs text-muted-foreground">
											Text extracted from the uploaded file for DLP / rule scanning (not shown in the main log table).
										</p>
										<pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed">
											{logExtractedText(pdfViewerLog, attachmentPreviewText) ||
												(pdfLoading ? "Loading…" : "No text could be extracted from this file.")}
										</pre>
									</div>
								) : pdfLoading ? (
									<p className="text-sm text-muted-foreground">Loading document…</p>
								) : pdfError ? (
									<p className="text-sm text-red-400">{pdfError}</p>
								) : attachmentPreviewKind === "image" && pdfBlobUrl ? (
									<img
										src={pdfBlobUrl}
										alt={logAttachmentLabel(pdfViewerLog)}
										className="max-h-[min(70vh,720px)] max-w-full rounded-md border border-border object-contain bg-black/20"
									/>
								) : attachmentPreviewKind === "pdf" && pdfBlobUrl ? (
									<embed
										title={logAttachmentLabel(pdfViewerLog)}
										src={pdfBlobUrl}
										type="application/pdf"
										className="w-full h-[min(70vh,720px)] rounded-md border border-border bg-neutral-900"
									/>
								) : attachmentPreviewKind === "html" && attachmentPreviewHtml ? (
									<div
										className="w-full max-h-[min(70vh,720px)] overflow-auto rounded-md border border-border bg-background p-4 text-foreground"
										dangerouslySetInnerHTML={{ __html: attachmentPreviewHtml }}
									/>
								) : attachmentPreviewKind === "text" && attachmentPreviewText ? (
									<pre className="w-full max-h-[min(70vh,720px)] overflow-auto rounded-md border border-border bg-background p-4 text-xs font-mono whitespace-pre-wrap">
										{attachmentPreviewText}
									</pre>
								) : (
									<div className="text-center space-y-3 p-6">
										<p className="text-sm text-muted-foreground">
											In-browser preview is not available for this file type. Download to open it locally.
										</p>
										<Button size="sm" className="gap-1.5" onClick={() => downloadPdfAttachment(pdfViewerLog)}>
											<Download className="h-3.5 w-3.5" /> Download
										</Button>
									</div>
								)}
							</div>
						</>
					)}
				</DialogContent>
			</Dialog>
		</div>
	);
}
