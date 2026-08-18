import React, { useState, useEffect, useRef } from "react";
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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ModelMultiselect } from "@/components/ui/modelMultiselect";
import { normalizeTargetDomain, groupTargetsByParent, relatedHostsForDomain, relatedHostOptions } from "./relatedHosts";

import {
	useGetBrowserAiLogsQuery,
	useClearBrowserAiLogsMutation,
	useGetBrowserAiRulesQuery,
	useCreateBrowserAiRuleMutation,
	useUpdateBrowserAiRuleMutation,
	useDeleteBrowserAiRuleMutation,
	useGetBrowserAiControlsQuery,
	useUpdateBrowserAiControlsMutation,
	useGetBrowserAiTargetsQuery,
	useCreateBrowserAiTargetMutation,
	useUpdateBrowserAiTargetMutation,
	useDeleteBrowserAiTargetMutation,
	useGetBrowserAiAgentsQuery,
	useGetBrowserAiAgentSettingsQuery,
	useSaveBrowserAiUninstallKeyMutation,
	BrowserAILogEntry,
	BrowserGuardRule,
	BrowserControlSettings,
	BrowserTargetWebsite,
} from "@/lib/store/apis/browserAiApi";
import { useGetProvidersQuery } from "@/lib/store/apis/providersApi";
import { getApiBaseUrl } from "@/lib/utils/port";

const DEFAULT_PROVIDER_MODELS: Record<string, string[]> = {
	openai: ["gpt-4o-mini", "gpt-4o", "o3-mini", "gpt-4-turbo"],
	anthropic: ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
	gemini: ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
	groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
	bedrock: ["anthropic.claude-3-haiku-20240307-v1:0", "anthropic.claude-3-5-sonnet-20240620-v1:0"],
	deepseek: ["deepseek-chat", "deepseek-reasoner"],
	cohere: ["command-r", "command-r-plus"],
	mistral: ["mistral-small-latest", "mistral-large-latest", "codestral-latest"],
	ollama: ["llama3.2", "qwen2.5", "mistral"],
};

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
	const [selectedLog, setSelectedLog] = useState<BrowserAILogEntry | null>(null);
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

	// Dialog states
	const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
	const [targetDialogOpen, setTargetDialogOpen] = useState(false);
	const [ruleError, setRuleError] = useState("");
	const [targetError, setTargetError] = useState("");

	// New Rule Form
	const [newRuleName, setNewRuleName] = useState("");
	const [newRuleType, setNewRuleType] = useState<"regex" | "ai_bot">("regex");
	const [newRuleBotProvider, setNewRuleBotProvider] = useState("openai");
	const [newRuleBotModel, setNewRuleBotModel] = useState("gpt-4o-mini");
	const [newRuleBotPrompt, setNewRuleBotPrompt] = useState("");
	const [newRuleSeverity, setNewRuleSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("CRITICAL");
	const [newRuleAction, setNewRuleAction] = useState<"BLOCK" | "WARN" | "REDACT">("BLOCK");
	const [newRulePattern, setNewRulePattern] = useState("");
	const [newRuleDescription, setNewRuleDescription] = useState("");
	const [newRuleWarningMessage, setNewRuleWarningMessage] = useState("");

	// New Target Form
	const [newTargetDomain, setNewTargetDomain] = useState("");
	const [newTargetPlatform, setNewTargetPlatform] = useState("");
	const [newTargetBlockSite, setNewTargetBlockSite] = useState(false);
	const [customRelatedHosts, setCustomRelatedHosts] = useState<string[]>([""]);
	const [extraHostDrafts, setExtraHostDrafts] = useState<Record<string, string>>({});

	// Edit Target Form
	const [editTarget, setEditTarget] = useState<BrowserTargetWebsite | null>(null);
	const [editTargetDomain, setEditTargetDomain] = useState("");
	const [editTargetPlatform, setEditTargetPlatform] = useState("");
	const [editTargetBlockSite, setEditTargetBlockSite] = useState(false);
	const [editTargetDialogOpen, setEditTargetDialogOpen] = useState(false);

	// Edit Rule Form
	const [editRule, setEditRule] = useState<BrowserGuardRule | null>(null);
	const [editRuleName, setEditRuleName] = useState("");
	const [editRuleType, setEditRuleType] = useState<"regex" | "ai_bot">("regex");
	const [editRuleBotProvider, setEditRuleBotProvider] = useState("openai");
	const [editRuleBotModel, setEditRuleBotModel] = useState("gpt-4o-mini");
	const [editRuleBotPrompt, setEditRuleBotPrompt] = useState("");
	const [editRuleSeverity, setEditRuleSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("CRITICAL");
	const [editRuleAction, setEditRuleAction] = useState<"BLOCK" | "WARN" | "REDACT">("BLOCK");
	const [editRulePattern, setEditRulePattern] = useState("");
	const [editRuleDescription, setEditRuleDescription] = useState("");
	const [editRuleWarningMessage, setEditRuleWarningMessage] = useState("");
	const [editRuleDialogOpen, setEditRuleDialogOpen] = useState(false);

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
	const { data: savedProviders = [] } = useGetProvidersQuery();
	const availableProviderKeys = Object.keys(DEFAULT_PROVIDER_MODELS);
	const allProviderNames = Array.from(
		new Set([
			...(Array.isArray(savedProviders) ? savedProviders.map((p: any) => p?.name || p) : []),
			...availableProviderKeys,
		])
	).filter(Boolean);
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

	const [clearLogs] = useClearBrowserAiLogsMutation();
	const [createRule] = useCreateBrowserAiRuleMutation();
	const [updateRule] = useUpdateBrowserAiRuleMutation();
	const [deleteRule] = useDeleteBrowserAiRuleMutation();
	const [updateControls] = useUpdateBrowserAiControlsMutation();
	const [createTarget] = useCreateBrowserAiTargetMutation();
	const [updateTarget] = useUpdateBrowserAiTargetMutation();
	const [deleteTarget] = useDeleteBrowserAiTargetMutation();

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
			if (!newRuleBotPrompt.trim()) {
				setRuleError("Evaluation instruction/prompt is required for AI Guard Bot.");
				return;
			}
			if (!newRuleBotProvider.trim() || !newRuleBotModel.trim()) {
				setRuleError("Provider and Model are required for AI Guard Bot.");
				return;
			}
		} else {
			if (!newRulePattern.trim()) {
				setRuleError("Regex pattern is required for Regex rule.");
				return;
			}
		}
		try {
			await createRule({
				name: newRuleName.trim(),
				rule_type: newRuleType,
				pattern: newRuleType === "regex" ? newRulePattern.trim() : "",
				bot_provider: newRuleType === "ai_bot" ? newRuleBotProvider.trim() : "",
				bot_model: newRuleType === "ai_bot" ? newRuleBotModel.trim() : "",
				bot_prompt: newRuleType === "ai_bot" ? newRuleBotPrompt.trim() : "",
				severity: newRuleSeverity,
				action: newRuleAction,
				description: newRuleDescription.trim(),
				warning_message: newRuleWarningMessage.trim(),
				active: true,
			}).unwrap();
			setRuleDialogOpen(false);
			setNewRuleName("");
			setNewRulePattern("");
			setNewRuleBotPrompt("");
			setNewRuleDescription("");
			setNewRuleWarningMessage("");
			setNewRuleType("regex");
		} catch (e: any) {
			setRuleError(e?.data?.message || "Failed to create rule");
		}
	};

	const handleEditRuleSubmit = async () => {
		if (!editRule || !editRuleName.trim()) return;
		setRuleError("");
		if (editRuleType === "ai_bot") {
			if (!editRuleBotPrompt.trim()) {
				setRuleError("Evaluation instruction/prompt is required for AI Guard Bot.");
				return;
			}
			if (!editRuleBotProvider.trim() || !editRuleBotModel.trim()) {
				setRuleError("Provider and Model are required for AI Guard Bot.");
				return;
			}
		} else {
			if (!editRulePattern.trim()) {
				setRuleError("Regex pattern is required for Regex rule.");
				return;
			}
		}
		try {
			const updates: Record<string, any> = {
				name: editRuleName.trim(),
				rule_type: editRuleType,
				severity: editRuleSeverity,
				action: editRuleAction,
				description: editRuleDescription.trim(),
				warning_message: editRuleWarningMessage.trim(),
			};
			if (editRuleType === "ai_bot") {
				updates.bot_provider = editRuleBotProvider.trim();
				updates.bot_model = editRuleBotModel.trim();
				updates.bot_prompt = editRuleBotPrompt.trim();
				updates.pattern = "";
			} else {
				updates.pattern = editRulePattern.trim();
				updates.bot_provider = "";
				updates.bot_model = "";
				updates.bot_prompt = "";
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
	const redactedCount = logs.filter((l) => l.action === "Redacted").length;
	const warnedCount = logs.filter((l) => l.action === "Warned").length;
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
			const created = await createTarget({ domain, ...payload }).unwrap();
			const parentId = created?.target?.id || "";
			for (const extra of customRelatedHosts) {
				const host = normalizeTargetDomain(extra);
				if (!host || host === domain) continue;
				try {
					await createTarget({ domain: host, ...payload, parent_id: parentId }).unwrap();
				} catch {
					const existing = targets.find((t) => normalizeTargetDomain(t.domain) === host);
					if (existing && parentId) {
						try {
							await updateTarget({ id: existing.id, updates: { parent_id: parentId } }).unwrap();
						} catch {
							// already in the list — skip
						}
					}
				}
			}
			setNewTargetDomain("");
			setNewTargetPlatform("");
			setNewTargetBlockSite(false);
			setCustomRelatedHosts([""]);
			setTargetDialogOpen(false);
		} catch (err: any) {
			setTargetError(err?.data?.message || err?.message || "Failed to create target domain");
		}
	};

	const fillSuggestedRelatedHost = (host: string) => {
		const n = normalizeTargetDomain(host);
		if (!n) return;
		setCustomRelatedHosts((prev) => {
			if (prev.some((v) => normalizeTargetDomain(v) === n)) return prev;
			const emptyIdx = prev.findIndex((v) => !v.trim());
			if (emptyIdx >= 0) {
				const next = [...prev];
				next[emptyIdx] = n;
				return next;
			}
			return [...prev, n];
		});
	};

	const handleAddRelatedHost = async (parent: BrowserTargetWebsite, host: string) => {
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

	const getPlatformBadge = (platform: string) => {
		const p = platform.toLowerCase();
		if (p.includes("claude")) {
			return <Badge className="bg-purple-950/60 text-purple-300 border border-purple-700/60">Claude</Badge>;
		} else if (p.includes("chatgpt") || p.includes("openai")) {
			return <Badge className="bg-emerald-950/60 text-emerald-300 border border-emerald-700/60">ChatGPT</Badge>;
		} else if (p.includes("gemini") || p.includes("google")) {
			return <Badge className="bg-blue-950/60 text-blue-300 border border-blue-700/60">Gemini</Badge>;
		} else if (p.includes("copilot") || p.includes("microsoft")) {
			return <Badge className="bg-cyan-950/60 text-cyan-300 border border-cyan-700/60">Copilot</Badge>;
		} else if (p.includes("perplexity")) {
			return <Badge className="bg-amber-950/60 text-amber-300 border border-amber-700/60">Perplexity</Badge>;
		} else if (p.includes("deepseek")) {
			return <Badge className="bg-indigo-950/60 text-indigo-300 border border-indigo-700/60">DeepSeek</Badge>;
		}
		return <Badge className="bg-slate-800 text-slate-300 border border-slate-700">{platform || "AI Platform"}</Badge>;
	};

	const getAgentStatusBadge = (status: string) => {
		const s = (status || "").toLowerCase();
		if (s === "uninstalled") return <Badge className="bg-slate-800 text-slate-300 border border-slate-700">Uninstalled</Badge>;
		return <Badge className="bg-emerald-950 text-emerald-400 border border-emerald-800">Active</Badge>;
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
	const visibleTargetRows: { tgt: BrowserTargetWebsite; isChild: boolean }[] = [];
	for (const group of groupTargetsByParent(targets)) {
		const parentHit = targetMatchesSearch(group.parent);
		const childHits = group.children.filter(targetMatchesSearch);
		if (!targetSearchLower || parentHit || childHits.length > 0) {
			visibleTargetRows.push({ tgt: group.parent, isChild: false });
			const kids = !targetSearchLower || parentHit ? group.children : childHits;
			for (const child of kids) {
				visibleTargetRows.push({ tgt: child, isChild: true });
			}
		}
	}

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
						Monitor browser AI prompts, predict security threat levels, auto-redact secrets in-flight, and control DLP guardrails.
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
									<ShieldCheck className="h-3.5 w-3.5 text-purple-400" /> In-Flight Redactions
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-purple-400">{redactedCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Secrets sanitized before AI model</p>
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
								<Table className="table-fixed min-w-[980px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[160px]">Timestamp</TableHead>
											<TableHead className="w-[110px]">Platform</TableHead>
											<TableHead className="w-[120px]">Guard</TableHead>
											<TableHead className="w-[280px]">User Prompt Preview</TableHead>
											<TableHead className="w-[90px] text-right">Est. Tokens</TableHead>
											<TableHead className="w-[120px]">Action</TableHead>
											<TableHead className="w-[70px] text-right">Details</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{logs.slice(0, 5).map((log) => (
											<TableRow
												key={log.id}
												onClick={() => setSelectedLog(log)}
												className="cursor-pointer border-border hover:bg-accent/50 transition-colors"
											>
												<TableCell className="text-xs text-muted-foreground font-mono truncate" title={new Date(log.timestamp).toLocaleString()}>
													{new Date(log.timestamp).toLocaleString()}
												</TableCell>
												<TableCell className="overflow-hidden">{getPlatformBadge(log.platform)}</TableCell>
												<TableCell className="text-xs text-muted-foreground truncate" title={log.agent_hostname || log.agent_id || ""}>
													{log.agent_hostname || log.agent_id || "—"}
												</TableCell>
												<TableCell className="font-mono text-xs truncate" title={log.user_prompt_preview || ""}>
													{log.user_prompt_preview}
												</TableCell>
												<TableCell className="text-right text-xs font-mono truncate">{log.est_tokens}</TableCell>
												<TableCell className="overflow-hidden">
													{log.action === "Blocked" ? (
														<Badge className="bg-red-950/80 text-red-400 border-red-700/60 gap-1 text-[11px]">
															<AlertTriangle className="h-3 w-3" /> Blocked
														</Badge>
													) : log.action === "Bot Answered" ? (
														<Badge className="bg-sky-950/80 text-sky-300 border-sky-700/60 gap-1 text-[11px]">
															<Bot className="h-3 w-3" /> Bot Answered
														</Badge>
													) : log.action === "Redacted" ? (
														<Badge className="bg-purple-950/80 text-purple-300 border-purple-700/60 gap-1 text-[11px]">
															<ShieldCheck className="h-3 w-3" /> Redacted
														</Badge>
													) : log.action === "Warned" ? (
														<Badge className="bg-amber-950/80 text-amber-300 border-amber-700/60 gap-1 text-[11px]">
															<AlertCircle className="h-3 w-3" /> Warned
														</Badge>
													) : (
														<Badge className="bg-emerald-950/80 text-emerald-400 border-emerald-700/60 gap-1 text-[11px]">
															<CheckCircle2 className="h-3 w-3" /> Allowed
														</Badge>
													)}
												</TableCell>
												<TableCell className="text-right">
													<Button
														variant="ghost"
														size="icon"
														onClick={(e) => {
															e.stopPropagation();
															setSelectedLog(log);
														}}
														className="h-8 w-8 text-muted-foreground hover:text-foreground"
													>
														<Eye className="h-4 w-4" />
													</Button>
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
										<SelectItem value="Blocked">Blocked</SelectItem>
										<SelectItem value="Bot Answered">Bot Answered</SelectItem>
									</SelectContent>
								</Select>
							</div>
						</CardHeader>

						<CardContent>
							<div className="rounded-md border border-border overflow-x-auto">
								<Table className="table-fixed min-w-[980px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[160px]">Timestamp</TableHead>
											<TableHead className="w-[110px]">Platform</TableHead>
											<TableHead className="w-[120px]">Guard</TableHead>
											<TableHead className="w-[280px]">User Prompt Preview</TableHead>
											<TableHead className="w-[90px] text-right">Est. Tokens</TableHead>
											<TableHead className="w-[120px]">Action</TableHead>
											<TableHead className="w-[70px] text-right">Details</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{logs.map((log) => (
											<TableRow
												key={log.id}
												onClick={() => setSelectedLog(log)}
												className="cursor-pointer border-border hover:bg-accent/50 transition-colors"
											>
												<TableCell className="text-xs text-muted-foreground font-mono truncate" title={new Date(log.timestamp).toLocaleString()}>
													{new Date(log.timestamp).toLocaleString()}
												</TableCell>
												<TableCell className="overflow-hidden">{getPlatformBadge(log.platform)}</TableCell>
												<TableCell className="text-xs text-muted-foreground truncate" title={log.agent_hostname || log.agent_id || ""}>
													{log.agent_hostname || log.agent_id || "—"}
												</TableCell>
												<TableCell className="font-mono text-xs truncate" title={log.user_prompt_preview || ""}>
													{log.user_prompt_preview}
												</TableCell>
												<TableCell className="text-right text-xs font-mono truncate">{log.est_tokens}</TableCell>
												<TableCell className="overflow-hidden">
													{log.action === "Blocked" ? (
														<Badge className="bg-red-950/80 text-red-400 border-red-700/60 gap-1 text-[11px]">
															<AlertTriangle className="h-3 w-3" /> Blocked
														</Badge>
													) : log.action === "Bot Answered" ? (
														<Badge className="bg-sky-950/80 text-sky-300 border-sky-700/60 gap-1 text-[11px]">
															<Bot className="h-3 w-3" /> Bot Answered
														</Badge>
													) : log.action === "Redacted" ? (
														<Badge className="bg-purple-950/80 text-purple-300 border-purple-700/60 gap-1 text-[11px]">
															<ShieldCheck className="h-3 w-3" /> Redacted
														</Badge>
													) : log.action === "Warned" ? (
														<Badge className="bg-amber-950/80 text-amber-300 border-amber-700/60 gap-1 text-[11px]">
															<AlertCircle className="h-3 w-3" /> Warned
														</Badge>
													) : (
														<Badge className="bg-emerald-950/80 text-emerald-400 border-emerald-700/60 gap-1 text-[11px]">
															<CheckCircle2 className="h-3 w-3" /> Allowed
														</Badge>
													)}
												</TableCell>
												<TableCell className="text-right">
													<Button
														variant="ghost"
														size="icon"
														onClick={(e) => {
															e.stopPropagation();
															setSelectedLog(log);
														}}
														className="h-8 w-8 text-muted-foreground hover:text-foreground"
													>
														<Eye className="h-4 w-4" />
													</Button>
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
										Control uploads on monitored AI sites. Prompts and PDF content still use Guard Rules below.
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
									<CardDescription>Real-time regular expressions matched against browser prompts</CardDescription>
								</div>
								<Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
									<DialogTrigger asChild>
										<Button className="gap-2">
											<Plus className="h-4 w-4" /> Add Rule
										</Button>
									</DialogTrigger>
									<DialogContent className="bg-card border-border text-foreground sm:max-w-lg max-h-[88vh] flex flex-col p-0 overflow-hidden">
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

										<div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
											{/* Rule Engine Type Toggle */}
											<div className="space-y-1.5">
												<Label>Rule Engine Type</Label>
												<div className="grid grid-cols-2 gap-2 p-1 bg-muted/40 rounded-lg border border-border">
													<button
														type="button"
														onClick={() => {
															setNewRuleType("regex");
															if (newRuleAction === "REDACT") setNewRuleAction("BLOCK");
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
															if (newRuleAction === "REDACT") setNewRuleAction("BLOCK");
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

											<div className="grid grid-cols-2 gap-3">
												<div className="space-y-1.5">
													<Label>Severity</Label>
													<Select value={newRuleSeverity} onValueChange={(v: any) => setNewRuleSeverity(v)}>
														<SelectTrigger>
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="CRITICAL">CRITICAL</SelectItem>
															<SelectItem value="HIGH">HIGH</SelectItem>
															<SelectItem value="MEDIUM">MEDIUM</SelectItem>
														</SelectContent>
													</Select>
												</div>
												<div className="space-y-1.5">
													<Label>Action</Label>
													<Select value={newRuleAction} onValueChange={(v: any) => setNewRuleAction(v)}>
														<SelectTrigger>
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="BLOCK">BLOCK (Security Reject)</SelectItem>
															{newRuleType === "regex" && (
																<SelectItem value="REDACT">REDACT (In-Flight Auto Sanitize)</SelectItem>
															)}
															<SelectItem value="WARN">WARN (Log Alert Only)</SelectItem>
														</SelectContent>
													</Select>
												</div>
											</div>

											{newRuleType === "regex" ? (
												<div className="space-y-1.5">
													<Label>Regex Pattern</Label>
													<Input
														placeholder="e.g. sk-[a-zA-Z0-9]{32} or \b\d{10,12}\b"
														value={newRulePattern}
														onChange={(e) => setNewRulePattern(e.target.value)}
													/>
													<p className="text-[11px] text-muted-foreground">
														Evaluated in microseconds using Golang RE2 regular expressions.
													</p>
												</div>
											) : (
												<div className="space-y-3 p-3 bg-purple-950/20 border border-purple-900/40 rounded-lg">
													<div className="flex items-center gap-1.5 text-xs font-semibold text-purple-300">
														<Bot className="h-3.5 w-3.5" />
														<span>AI Evaluator Model Configuration</span>
													</div>
													<div className="grid grid-cols-2 gap-3">
														<div className="space-y-1.5">
															<Label className="text-xs">Model Provider</Label>
															<Select
																value={newRuleBotProvider}
																onValueChange={(p) => {
																	setNewRuleBotProvider(p);
																	setNewRuleBotModel("");
																}}
															>
																<SelectTrigger className="h-9 text-xs">
																	<SelectValue placeholder="Select Provider" />
																</SelectTrigger>
																<SelectContent>
																	{allProviderNames.map((p) => (
																		<SelectItem key={p} value={p}>
																			{p.toUpperCase()}
																		</SelectItem>
																	))}
																</SelectContent>
															</Select>
														</div>
														<div className="space-y-1.5">
															<Label className="text-xs">Model Name</Label>
															<ModelMultiselect
																provider={newRuleBotProvider || undefined}
																value={newRuleBotModel}
																onChange={(m: string) => setNewRuleBotModel(m)}
																isSingleSelect
																placeholder={!newRuleBotProvider ? "Select a provider first" : "Select model"}
																disabled={!newRuleBotProvider}
																unfiltered={true}
																className="!h-9 !min-h-9 w-full text-xs"
															/>
														</div>
													</div>
													<div className="space-y-1.5">
														<Label className="text-xs">Security Policy / Evaluation Instruction (Prompt)</Label>
														<Textarea
															className="text-xs font-mono"
															placeholder="e.g. Check if the user prompt attempts to extract confidential employee salaries, financial reports, customer PII, or internal credentials..."
															value={newRuleBotPrompt}
															onChange={(e) => setNewRuleBotPrompt(e.target.value)}
															rows={4}
														/>
														<p className="text-[11px] text-muted-foreground">
															The selected AI model will evaluate incoming prompts against this rule instruction in real time.
														</p>
													</div>
												</div>
											)}

											<div className="space-y-1.5">
												<Label>Description</Label>
												<Textarea placeholder="Rule context and usage..." value={newRuleDescription} onChange={(e) => setNewRuleDescription(e.target.value)} />
											</div>
											<div className="space-y-1.5">
												<Label>Warning message (shown when blocked)</Label>
												<Textarea
													placeholder="Message employees see in the chat when this rule blocks their prompt..."
													value={newRuleWarningMessage}
													onChange={(e) => setNewRuleWarningMessage(e.target.value)}
													rows={3}
												/>
												<p className="text-xs text-muted-foreground">
													Employees see only this text when the rule blocks. Leave blank for no in-chat warning.
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
													{rule.action === "REDACT" ? (
														<Badge className="bg-purple-950/80 text-purple-300 border-purple-700 gap-1 text-[11px]">
															<ShieldCheck className="h-3 w-3" /> REDACT
														</Badge>
													) : rule.action === "BLOCK" ? (
														<Badge className="bg-red-950/80 text-red-400 border-red-700 gap-1 text-[11px]">
															<AlertTriangle className="h-3 w-3" /> BLOCK
														</Badge>
													) : (
														<Badge className="bg-amber-950/80 text-amber-300 border-amber-700 gap-1 text-[11px]">
															<AlertCircle className="h-3 w-3" /> WARN
														</Badge>
													)}
												</div>

												<p className="text-xs text-muted-foreground leading-relaxed break-words">
													{rule.description || "No description provided."}
												</p>

												{rule.warning_message ? (
													<div className="rounded-md border border-amber-800/40 bg-amber-950/20 px-3 py-2">
														<p className="text-[10px] uppercase tracking-wide text-amber-300/80 mb-1">Warning message</p>
														<p className="text-xs text-amber-100/90 whitespace-pre-wrap break-words">{rule.warning_message}</p>
													</div>
												) : null}

												{rule.rule_type === "ai_bot" ? (
													<div className="rounded-md border border-purple-900/40 bg-purple-950/20 px-3 py-2 space-y-1">
														<div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-purple-300/80">
															<span>AI Security Policy (Prompt)</span>
															<Badge variant="outline" className="text-[10px] py-0 px-1.5 text-purple-300 border-purple-800">
																{rule.bot_provider} / {rule.bot_model}
															</Badge>
														</div>
														<p className="text-xs text-purple-100/90 whitespace-pre-wrap break-words font-mono">
															{rule.bot_prompt}
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
															setEditRuleBotProvider(rule.bot_provider || "openai");
															setEditRuleBotModel(rule.bot_model || "gpt-4o-mini");
															setEditRuleBotPrompt(rule.bot_prompt || "");
															setEditRuleSeverity(rule.severity);
															setEditRuleAction(rule.action);
															setEditRulePattern(rule.pattern || "");
															setEditRuleDescription(rule.description || "");
															setEditRuleWarningMessage(rule.warning_message || "");
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
										proxy.pac includes monitored and locked domains.
									</CardDescription>
								</div>
								<Dialog
									open={targetDialogOpen}
									onOpenChange={(open) => {
										setTargetDialogOpen(open);
										if (!open) {
											setCustomRelatedHosts([""]);
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
												<p className="text-[11px] text-muted-foreground">Examples: gemini.google.com, copilot.microsoft.com, deepseek.com</p>
											</div>
											<div className="space-y-2 rounded-md border border-border p-3">
												<p className="text-sm font-medium">Add related host</p>
												<p className="text-[11px] text-muted-foreground">
													Subdomains of the domain you add already get full Guard access. Add a related host only when it is a different hostname you want nested under this domain. Names below are suggestions — nothing is added until you choose it.
												</p>
												{newTargetRelatedGroup ? (
													<div className="space-y-1.5 rounded-md border border-dashed border-border bg-muted/20 p-2">
														<p className="text-[11px] font-medium">{newTargetRelatedGroup.label}</p>
														<p className="text-[10px] text-muted-foreground">{newTargetRelatedGroup.reason}</p>
														<div className="flex flex-wrap gap-1.5 pt-1">
															{newTargetRelatedGroup.hosts.map((host) => {
																const picked = customRelatedHosts.some((v) => normalizeTargetDomain(v) === host);
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
													{customRelatedHosts.map((value, idx) => (
														<div key={idx} className="flex items-center gap-2">
															<Input
																placeholder="e.g. api.example.com"
																className="font-mono text-sm"
																value={value}
																onChange={(e) => {
																	const next = [...customRelatedHosts];
																	next[idx] = e.target.value;
																	setCustomRelatedHosts(next);
																}}
															/>
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
														onClick={() => setCustomRelatedHosts([...customRelatedHosts, ""])}
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
											<TableHead className="w-[260px]">Domain</TableHead>
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
															<p className="text-[10px] text-muted-foreground pl-5">Related host</p>
														) : (
														<div className="space-y-1.5 pt-0.5">
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
														<div className="flex items-center gap-1">
															<Input
																placeholder="Add related host"
																className="h-6 text-[10px] font-mono max-w-[180px]"
																value={extraHostDrafts[tgt.id] || ""}
																onChange={(e) => setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: e.target.value }))}
																onKeyDown={(e) => {
																	if (e.key === "Enter") {
																		e.preventDefault();
																		const host = extraHostDrafts[tgt.id];
																		if (host?.trim()) {
																			handleAddRelatedHost(tgt, host);
																			setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: "" }));
																		}
																	}
																}}
															/>
															<Button
																type="button"
																variant="outline"
																size="sm"
																className="h-6 px-2 text-[10px]"
																onClick={() => {
																	const host = extraHostDrafts[tgt.id];
																	if (host?.trim()) {
																		handleAddRelatedHost(tgt, host);
																		setExtraHostDrafts((prev) => ({ ...prev, [tgt.id]: "" }));
																	}
																}}
															>
																<Plus className="h-3 w-3" />
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
														<Button
															variant="ghost"
															size="icon"
															onClick={() => {
																setEditTarget(tgt);
																setEditTargetDomain(tgt.domain);
																setEditTargetPlatform(tgt.platform_name);
																setEditTargetBlockSite(!!tgt.block_site);
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
					<DialogContent className="bg-card border-border text-foreground sm:max-w-lg max-h-[88vh] flex flex-col p-0 overflow-hidden">
						<DialogHeader className="p-5 pb-3 shrink-0 border-b border-border/60">
							<DialogTitle className="flex items-center gap-2 text-base">
								<Pencil className="h-5 w-5 text-primary" />
								Edit Guard Rule
							</DialogTitle>
							<DialogDescription className="text-xs">Modify rule engine parameters, action, and notification messages.</DialogDescription>
						</DialogHeader>

						{ruleError && <div className="mx-5 mt-3 p-3 bg-red-950/60 border border-red-800 text-red-400 rounded-md text-xs">{ruleError}</div>}

						<div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
							{/* Rule Engine Type Toggle */}
							<div className="space-y-1.5">
								<Label>Rule Engine Type</Label>
								<div className="grid grid-cols-2 gap-2 p-1 bg-muted/40 rounded-lg border border-border">
									<button
										type="button"
										onClick={() => {
											setEditRuleType("regex");
											if (editRuleAction === "REDACT") setEditRuleAction("BLOCK");
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
											if (editRuleAction === "REDACT") setEditRuleAction("BLOCK");
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

							<div className="grid grid-cols-2 gap-3">
								<div className="space-y-1.5">
									<Label>Severity</Label>
									<Select value={editRuleSeverity} onValueChange={(v: any) => setEditRuleSeverity(v)}>
										<SelectTrigger>
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="CRITICAL">CRITICAL</SelectItem>
											<SelectItem value="HIGH">HIGH</SelectItem>
											<SelectItem value="MEDIUM">MEDIUM</SelectItem>
										</SelectContent>
									</Select>
								</div>
								<div className="space-y-1.5">
									<Label>Action</Label>
									<Select value={editRuleAction} onValueChange={(v: any) => setEditRuleAction(v)}>
										<SelectTrigger>
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="BLOCK">BLOCK (Security Reject)</SelectItem>
											{editRuleType === "regex" && (
												<SelectItem value="REDACT">REDACT (In-Flight Auto Sanitize)</SelectItem>
											)}
											<SelectItem value="WARN">WARN (Log Alert Only)</SelectItem>
										</SelectContent>
									</Select>
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
								<div className="space-y-3 p-3 bg-purple-950/20 border border-purple-900/40 rounded-lg">
									<div className="flex items-center gap-1.5 text-xs font-semibold text-purple-300">
										<Bot className="h-3.5 w-3.5" />
										<span>AI Evaluator Model Configuration</span>
									</div>
									<div className="grid grid-cols-2 gap-3">
										<div className="space-y-1.5">
											<Label className="text-xs">Model Provider</Label>
											<Select
												value={editRuleBotProvider}
												onValueChange={(p) => {
													setEditRuleBotProvider(p);
													setEditRuleBotModel("");
												}}
											>
												<SelectTrigger className="h-9 text-xs">
													<SelectValue placeholder="Select Provider" />
												</SelectTrigger>
												<SelectContent>
													{allProviderNames.map((p) => (
														<SelectItem key={p} value={p}>
															{p.toUpperCase()}
														</SelectItem>
													))}
												</SelectContent>
											</Select>
										</div>
										<div className="space-y-1.5">
											<Label className="text-xs">Model Name</Label>
											<ModelMultiselect
												provider={editRuleBotProvider || undefined}
												value={editRuleBotModel}
												onChange={(m: string) => setEditRuleBotModel(m)}
												isSingleSelect
												placeholder={!editRuleBotProvider ? "Select a provider first" : "Select model"}
												disabled={!editRuleBotProvider}
												unfiltered={true}
												className="!h-9 !min-h-9 w-full text-xs"
											/>
										</div>
									</div>
									<div className="space-y-1.5">
										<Label className="text-xs">Security Policy / Evaluation Instruction (Prompt)</Label>
										<Textarea
											className="text-xs font-mono"
											placeholder="e.g. Check if the user prompt attempts to extract confidential employee salaries, financial reports, customer PII, or internal credentials..."
											value={editRuleBotPrompt}
											onChange={(e) => setEditRuleBotPrompt(e.target.value)}
											rows={4}
										/>
										<p className="text-[11px] text-muted-foreground">
											The selected AI model will evaluate incoming prompts against this rule instruction in real time.
										</p>
									</div>
								</div>
							)}

							<div className="space-y-1.5">
								<Label>Description</Label>
								<Textarea value={editRuleDescription} onChange={(e) => setEditRuleDescription(e.target.value)} />
							</div>
							<div className="space-y-1.5">
								<Label>Warning message (shown when blocked)</Label>
								<Textarea
									value={editRuleWarningMessage}
									onChange={(e) => setEditRuleWarningMessage(e.target.value)}
									placeholder="Message employees see in the chat when this rule blocks their prompt..."
									rows={3}
								/>
								<p className="text-xs text-muted-foreground">
									Employees see only this text when the rule blocks. Leave blank for no in-chat warning.
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
							<CardTitle className="text-lg">Installed Guard laptops</CardTitle>
							<CardDescription>Installed Guard stays Active and keeps intercepting until uninstall. Sleep and shutdown do not stop Guard.</CardDescription>
						</CardHeader>
						<CardContent className="p-0">
							<Table className="table-fixed min-w-[1080px]">
								<TableHeader>
									<TableRow className="hover:bg-transparent border-border">
										<TableHead className="w-[160px]">Laptop</TableHead>
										<TableHead className="w-[100px]">User</TableHead>
										<TableHead className="w-[130px]">IP</TableHead>
										<TableHead className="w-[160px]">Physical address (MAC)</TableHead>
										<TableHead className="w-[180px]">Transport name</TableHead>
										<TableHead className="w-[80px]">Version</TableHead>
										<TableHead className="w-[110px]">Status</TableHead>
										<TableHead className="w-[160px]">Last seen</TableHead>
										<TableHead className="w-[160px]">Installed</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{agents.map((agent) => (
										<TableRow key={agent.id} className="border-border">
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
											<TableCell className="text-xs truncate">{agent.agent_version || "—"}</TableCell>
											<TableCell>{getAgentStatusBadge(agent.status)}</TableCell>
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
												<TableCell colSpan={9} className="text-center py-10 text-muted-foreground text-sm">
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
										<CardDescription>Download a ZIP that contains the Guard installer, backend config, and employee setup guide.</CardDescription>
									</div>
								</div>
								<div className="flex items-center gap-2">
									<Badge className="bg-emerald-950 text-emerald-400 border-emerald-700 px-3 py-1 text-xs">Status: Ready</Badge>
									<Button onClick={handleDownloadSetupPackage} disabled={setupPackageDownloading} className="gap-2">
										<Download className="h-4 w-4" />
										{setupPackageDownloading ? "Preparing..." : "Download Setup ZIP"}
									</Button>
								</div>
							</div>
						</CardHeader>
						<CardContent className="pt-0">
							<p className="text-sm text-muted-foreground">
								Use this ZIP for employee rollout. It bundles the Windows setup EXE with the same backend configuration used by this Browser AI workspace.
							</p>
							{setupPackageError ? <p className="mt-3 text-sm text-red-400">{setupPackageError}</p> : null}
						</CardContent>
					</Card>

					<Card className="bg-card border-border">
						<CardHeader>
							<CardTitle className="text-lg">Install Steps</CardTitle>
							<CardDescription>Old certificate-only setup has been replaced with a single ZIP download and guided Windows installation.</CardDescription>
						</CardHeader>
						<CardContent className="space-y-6">
							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">1</span>
									<span>Download the ZIP package</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Click <strong>Download Setup ZIP</strong> above. The ZIP includes the installer EXE, employee README, and the backend config for this environment.
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
									<li><code>UnifAI_Guard_Setup.exe</code> for employee installation</li>
									<li><code>unifai_guard_config.json</code> with backend URL</li>
									<li><code>EMPLOYEE_README.txt</code> with install/support instructions</li>
								</ul>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>

			{/* Log Details Side Sheet */}
			<Sheet open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
				<SheetContent className="bg-card border-border text-foreground sm:max-w-xl overflow-y-auto">
					<SheetHeader className="pb-4 border-b border-border">
						<div className="flex items-center justify-between">
							<SheetTitle className="flex items-center gap-2 text-lg">
								Prompt Details
								{selectedLog && getPlatformBadge(selectedLog.platform)}
							</SheetTitle>
						</div>
						<SheetDescription>
							Captured {selectedLog && new Date(selectedLog.timestamp).toLocaleString()}
						</SheetDescription>
					</SheetHeader>

					{selectedLog && (
						<div className="space-y-5 py-4">
							<div className="grid grid-cols-2 gap-4">
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">Action / Status</Label>
									<div>
										{selectedLog.action === "Blocked" ? (
											<Badge className="bg-red-950 text-red-400 border-red-800 gap-1">
												<AlertTriangle className="h-3.5 w-3.5" />
												{selectedLog.status}
											</Badge>
										) : selectedLog.action === "Bot Answered" ? (
											<Badge className="bg-sky-950 text-sky-300 border-sky-800 gap-1">
												<Bot className="h-3.5 w-3.5" />
												Bot Answered
											</Badge>
										) : selectedLog.action === "Redacted" ? (
											<Badge className="bg-purple-950 text-purple-300 border-purple-800 gap-1">
												<ShieldCheck className="h-3.5 w-3.5" />
												{selectedLog.status}
											</Badge>
										) : selectedLog.action === "Warned" ? (
											<Badge className="bg-amber-950 text-amber-300 border-amber-800 gap-1">
												<AlertCircle className="h-3.5 w-3.5" />
												{selectedLog.status}
											</Badge>
										) : (
											<Badge className="bg-emerald-950 text-emerald-400 border-emerald-800 gap-1">
												<CheckCircle2 className="h-3.5 w-3.5" />
												Allowed
											</Badge>
										)}
									</div>
								</div>
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">Guard laptop</Label>
									<p className="text-sm font-medium">{selectedLog.agent_hostname || "—"}</p>
									<p className="text-[11px] text-muted-foreground font-mono truncate">{selectedLog.agent_id || selectedLog.client_ip || ""}</p>
								</div>
							</div>

							{/* Predictive Risk Scoring */}
							<div className="p-3.5 bg-background border border-border rounded-md space-y-2">
								<div className="flex justify-between items-center text-xs font-semibold">
									<span className="flex items-center gap-1.5 text-purple-300">
										<BrainCircuit className="h-4 w-4" /> Predictive Risk Score
									</span>
									<span className={(selectedLog.risk_score || 0) >= 70 ? "text-red-400 font-bold" : (selectedLog.risk_score || 0) >= 40 ? "text-amber-400" : "text-emerald-400"}>
										{selectedLog.risk_score || 10}% ({selectedLog.predictive_risk || "LOW"})
									</span>
								</div>
								<div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
									<div
										className={`h-full rounded-full transition-all ${
											(selectedLog.risk_score || 0) >= 70 ? "bg-red-500" : (selectedLog.risk_score || 0) >= 40 ? "bg-amber-500" : "bg-emerald-500"
										}`}
										style={{ width: `${Math.min(100, Math.max(5, selectedLog.risk_score || 10))}%` }}
									/>
								</div>
								<div className="flex justify-between items-center text-[11px] text-muted-foreground pt-1">
									<span>Category: <code className="text-foreground">{selectedLog.predicted_category || "SAFE"}</code></span>
									<span>Threat Level: {selectedLog.predictive_risk || "LOW"}</span>
								</div>
							</div>

							<div className="space-y-2">
								<div className="flex justify-between items-center">
									<Label className="text-xs text-muted-foreground">
										{selectedLog.action === "Redacted" ? "Sanitized Intercepted Prompt Text" : "Full Intercepted Prompt Text"}
									</Label>
									<Button variant="ghost" size="sm" onClick={() => handleCopyPrompt(selectedLog.user_prompt_full)} className="h-7 text-xs gap-1">
										{copiedPrompt ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
										{copiedPrompt ? "Copied" : "Copy"}
									</Button>
								</div>
								<div className="p-3 bg-background border border-border rounded-md font-mono text-xs max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed">
									{selectedLog.user_prompt_full}
								</div>
							</div>

							<div className="grid grid-cols-2 gap-4">
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">Estimated Token Usage</Label>
									<p className="text-sm font-semibold">{selectedLog.est_tokens} tokens</p>
								</div>
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">Rule Triggered</Label>
									<p className={`text-sm font-semibold ${selectedLog.rule_triggered ? "text-purple-300" : "text-muted-foreground"}`}>
										{selectedLog.rule_triggered || "None"}
									</p>
								</div>
							</div>

							{selectedLog.metadata && (
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">Metadata Payload</Label>
									<pre className="p-3 bg-background border border-border rounded-md font-mono text-[11px] max-h-40 overflow-auto">
										{JSON.stringify(JSON.parse(selectedLog.metadata || "{}"), null, 2)}
									</pre>
								</div>
							)}
						</div>
					)}
				</SheetContent>
			</Sheet>
		</div>
	);
}
