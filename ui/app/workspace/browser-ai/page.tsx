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
	Loader2,
	Compass,
} from "lucide-react";
import { getProviderLabel } from "@/lib/constants/logs";
import { useGetProvidersQuery } from "@/lib/store/apis/providersApi";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { normalizeTargetDomain, groupTargetsByParent, relatedHostsForDomain, relatedHostOptions, HOST_ROLE_OPTIONS, hostRoleLabel, type HostRole } from "./relatedHosts";
import { buildAttachmentPreview, type AttachmentPreviewKind, type AttachmentSheetPreview } from "./attachmentPreview";
import {
	GUARD_BOT_OLLAMA_PROVIDER,
	GUARD_BOT_OLLAMA_MODEL,
} from "./browserAiConstants";
import type { RelatedHostEntry } from "./browserAiTypes";
import {
	predictReasonLabel,
	logFileStatusLine,
	logExtractedTextFromPrompt,
	logExtractedText,
	isFileUploadLog,
	logHasStoredAttachment,
	logAttachmentLabel,
	securityVerdictFromLog,
} from "./browserAiLogHelpers";
import {
	isDownloadGuardSource,
	guardRuleNoticeCopy,
	guardRuleActionHint,
	referenceImageDataUrl,
	readReferenceImageFile,
} from "./browserAiGuardHelpers";
import { ExportFormatsDropdown } from "@/components/exportFormatsDropdown";
import type { ExportFormatsPayload } from "@/components/exportFormatsDropdown";

import {
	useGetBrowserAiLogsQuery,
	useClearBrowserAiLogsMutation,
	useGetBrowserAiSearchLogsQuery,
	useClearBrowserAiSearchLogsMutation,
	useGetBrowserAiRulesQuery,
	useCreateBrowserAiRuleMutation,
	useUpdateBrowserAiRuleMutation,
	useDeleteBrowserAiRuleMutation,
	useGenerateBrowserAiRegexFromPolicyMutation,
	useTestBrowserAiGuardBotMutation,
	useGetBrowserAiControlsQuery,
	useUpdateBrowserAiControlsMutation,
	useGetBrowserAiTargetsQuery,
	useCreateBrowserAiTargetMutation,
	useUpdateBrowserAiTargetMutation,
	useDeleteBrowserAiTargetMutation,
	useGetBrowserAiAgentsQuery,
	useGetBrowserAiAgentSettingsQuery,
	useGetBrowserAiFleetConfigQuery,
	useSaveBrowserAiFleetConfigMutation,
	useSaveBrowserAiUninstallKeyMutation,
	useBulkDeleteBrowserAiAgentsMutation,
	BrowserAILogEntry,
	BrowserAISearchLogEntry,
	BrowserGuardRule,
	BrowserControlSettings,
	BrowserTargetWebsite,
	BrowserAIAgent,
} from "@/lib/store/apis/browserAiApi";
import { getApiBaseUrl } from "@/lib/utils/port";
import { GuardRuleAIEvaluatorFields } from "./guardRuleAIEvaluatorFields";
import { logActionBadge, getPlatformBadge } from "./logBadges";
import { LogPromptPreviewCell } from "./logPromptPreviewCell";
import { RegexLiveTestPanel } from "./regexLiveTestPanel";

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
	const [rulesPageLimit, setRulesPageLimit] = useState(10);
	const [rulesPageOffset, setRulesPageOffset] = useState(0);
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
	const [attachmentBlob, setAttachmentBlob] = useState<Blob | null>(null);
	const [attachmentSheets, setAttachmentSheets] = useState<AttachmentSheetPreview[]>([]);
	const [attachmentSheetIndex, setAttachmentSheetIndex] = useState(0);
	const [attachmentTruncated, setAttachmentTruncated] = useState(false);
	const [attachmentShowAll, setAttachmentShowAll] = useState(false);
	const [extractedTextExpanded, setExtractedTextExpanded] = useState(false);
	const [pdfLoading, setPdfLoading] = useState(false);
	const [pdfError, setPdfError] = useState("");
	const [copiedPrompt, setCopiedPrompt] = useState(false);
	const [downloadingPlatform, setDownloadingPlatform] = useState<"windows" | "mac" | null>(null);
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
	const [agentTypeFilter, setAgentTypeFilter] = useState("all");
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
			agent_type: agentTypeFilter !== "all" ? agentTypeFilter : undefined,
			search: agentSearch || undefined,
			limit: agentPageLimit,
			offset: agentPageOffset,
		},
		{ pollingInterval: activePolling }
	);

	// Search Logs State & Query (in-memory live observability)
	const [searchLogQuery, setSearchLogQuery] = useState("");
	const [searchEngineFilter, setSearchEngineFilter] = useState("all");
	const [searchBrowserFilter, setSearchBrowserFilter] = useState("all");
	const [searchIncognitoFilter, setSearchIncognitoFilter] = useState("all");
	const [selectedSearchLog, setSelectedSearchLog] = useState<BrowserAISearchLogEntry | null>(null);

	const {
		data: searchLogsData,
		refetch: refetchSearchLogs,
		isFetching: searchLogsLoading,
	} = useGetBrowserAiSearchLogsQuery(
		{
			engine: searchEngineFilter !== "all" ? searchEngineFilter : undefined,
			browser: searchBrowserFilter !== "all" ? searchBrowserFilter : undefined,
			is_incognito: searchIncognitoFilter !== "all" ? searchIncognitoFilter : undefined,
			search: searchLogQuery || undefined,
			limit: 50,
			offset: 0,
		},
		{ pollingInterval: activePolling }
	);

	const [clearSearchLogs, { isLoading: isClearingSearchLogs }] = useClearBrowserAiSearchLogsMutation();

	const searchLogs = searchLogsData?.logs || [];
	const totalSearchLogs = searchLogsData?.total || 0;
	const incognitoSearchCount = searchLogsData?.incognito_count || 0;
	const queriesSearchCount = searchLogsData?.queries_count || 0;
	const clicksSearchCount = searchLogsData?.clicks_count || 0;

	const { data: agentSettingsData, refetch: refetchAgentSettings } = useGetBrowserAiAgentSettingsQuery();
	const { data: fleetConfigData, refetch: refetchFleetConfig } = useGetBrowserAiFleetConfigQuery();
	const [saveUninstallKey, { isLoading: savingUninstallKey }] = useSaveBrowserAiUninstallKeyMutation();
	const [saveFleetConfig, { isLoading: savingFleetConfig }] = useSaveBrowserAiFleetConfigMutation();
	const [fleetDraft, setFleetDraft] = useState({
		default_proxy_addr: "127.0.0.1:8085",
		pac_advertise_addr: "127.0.0.1:8085",
		pac_sync_seconds: 3,
		agent_type_default: "endpoint",
		listen_host_policy: "127.0.0.1",
		server_mode_policy: "endpoint_default",
		backend_url_hint: "",
		notes: "",
	});
	const [fleetSaveError, setFleetSaveError] = useState("");
	const [fleetSaveOk, setFleetSaveOk] = useState(false);
	useEffect(() => {
		const f = fleetConfigData?.fleet_config;
		if (!f) return;
		setFleetDraft({
			default_proxy_addr: f.default_proxy_addr || "127.0.0.1:8085",
			pac_advertise_addr: f.pac_advertise_addr || f.default_proxy_addr || "127.0.0.1:8085",
			pac_sync_seconds: f.pac_sync_seconds || 3,
			agent_type_default: f.agent_type_default || "endpoint",
			listen_host_policy: f.listen_host_policy || "127.0.0.1",
			server_mode_policy: f.server_mode_policy || "endpoint_default",
			backend_url_hint: f.backend_url_hint || "",
			notes: f.notes || "",
		});
	}, [fleetConfigData]);

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
	}, [agentPageOffset, agentSearch, agentStatusFilter, agentTypeFilter]);

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
			setAttachmentBlob(null);
			setAttachmentSheets([]);
			setAttachmentSheetIndex(0);
			setAttachmentTruncated(false);
			setAttachmentShowAll(false);
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
		setAttachmentBlob(null);
		setAttachmentSheets([]);
		setAttachmentSheetIndex(0);
		setAttachmentTruncated(false);
		setAttachmentShowAll(false);
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
				setAttachmentBlob(blob);
				const preview = await buildAttachmentPreview(
					blob,
					logAttachmentLabel(pdfViewerLog),
					pdfViewerLog.attachment_content_type || blob.type,
					{ showAll: false },
				);
				if (cancelled) return;
				setAttachmentPreviewKind(preview.kind);
				setAttachmentSheets(preview.sheets || []);
				setAttachmentSheetIndex(0);
				setAttachmentTruncated(!!preview.truncated);
				if (preview.blobUrl) {
					objectUrl = preview.blobUrl;
					setPdfBlobUrl(preview.blobUrl);
				}
				if (preview.sheets?.length) {
					setAttachmentPreviewHtml(preview.sheets[0].html);
				} else if (preview.html) {
					setAttachmentPreviewHtml(preview.html);
				}
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

	const reloadAttachmentPreview = async (showAll: boolean) => {
		if (!pdfViewerLog || !attachmentBlob) return;
		setPdfLoading(true);
		setPdfError("");
		try {
			const preview = await buildAttachmentPreview(
				attachmentBlob,
				logAttachmentLabel(pdfViewerLog),
				pdfViewerLog.attachment_content_type || attachmentBlob.type,
				{ showAll },
			);
			setAttachmentShowAll(showAll);
			setAttachmentPreviewKind(preview.kind);
			setAttachmentSheets(preview.sheets || []);
			setAttachmentSheetIndex(0);
			setAttachmentTruncated(!!preview.truncated);
			if (preview.sheets?.length) {
				setAttachmentPreviewHtml(preview.sheets[0].html);
			} else if (preview.html) {
				setAttachmentPreviewHtml(preview.html);
			}
			if (preview.text) setAttachmentPreviewText(preview.text);
		} catch (e) {
			setPdfError(e instanceof Error ? e.message : "Failed to expand preview");
		} finally {
			setPdfLoading(false);
		}
	};

	const openPdfViewer = (log: BrowserAILogEntry, e?: React.MouseEvent) => {
		e?.stopPropagation();
		setPdfViewerTab("preview");
		setAttachmentShowAll(false);
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
	const [testGuardBot, { isLoading: testingGuardBot }] = useTestBrowserAiGuardBotMutation();
	const [newRuleTestSample, setNewRuleTestSample] = useState("");
	const [newRuleTestResult, setNewRuleTestResult] = useState("");
	const [editRuleTestSample, setEditRuleTestSample] = useState("");
	const [editRuleTestResult, setEditRuleTestResult] = useState("");
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
			if (newRuleBotEvalMode === "ai" && newRuleBotPrompt.trim() && newRuleBotPrompt.trim().split(/\s+/).length < 2) {
				setRuleError("Security policy is too short. Describe clearly what should be blocked.");
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

	const runTestEvaluate = async (which: "new" | "edit") => {
		const policy = which === "new" ? newRuleBotPrompt.trim() : editRuleBotPrompt.trim();
		const sample = which === "new" ? newRuleTestSample.trim() : editRuleTestSample.trim();
		const provider = which === "new" ? newRuleBotProvider : editRuleBotProvider;
		const model = which === "new" ? newRuleBotModel : editRuleBotModel;
		const action = which === "new" ? newRuleAction : editRuleAction;
		const setResult = which === "new" ? setNewRuleTestResult : setEditRuleTestResult;
		setResult("");
		if (!policy) {
			setResult("Enter a security policy first.");
			return;
		}
		if (!sample) {
			setResult("Enter a sample Browser AI prompt to evaluate.");
			return;
		}
		try {
			const res = await testGuardBot({
				bot_provider: provider || GUARD_BOT_OLLAMA_PROVIDER,
				bot_model: model || GUARD_BOT_OLLAMA_MODEL,
				bot_prompt: policy,
				sample_prompt: sample,
				action,
				name: which === "new" ? newRuleName.trim() || "Test" : editRuleName.trim() || "Test",
			}).unwrap();
			if (res.eval_error) {
				setResult(`EVAL FAILED: ${res.eval_error}`);
				return;
			}
			let outcome = `OK — ${res.security_message || "no violation"}`;
			if (res.would_block) {
				outcome = `BLOCK — ${res.security_message || "policy violation"}`;
			} else if (res.would_warn) {
				outcome = `REDACT — ${res.security_message || "policy match"}`;
			}
			if (res.model_raw?.trim()) {
				outcome = `${outcome}\n\nmodel_raw: ${res.model_raw}`;
			}
			setResult(outcome);
		} catch (e: any) {
			setResult(
				e?.data?.error?.message ||
					e?.data?.message ||
					e?.message ||
					"Model evaluate request failed.",
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
			if (editRuleBotEvalMode === "ai" && editRuleBotPrompt.trim() && editRuleBotPrompt.trim().split(/\s+/).length < 2) {
				setRuleError("Security policy is too short. Describe clearly what should be blocked.");
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

	const handleDownloadSetupPackage = async (platform: "windows" | "mac") => {
		setDownloadingPlatform(platform);
		setSetupPackageError("");
		try {
			const res = await fetch(`${getApiBaseUrl()}/browser-ai/setup/download.zip?platform=${platform}`, {
				credentials: "include",
			});
			if (!res.ok) {
				let msg = `Download failed (${res.status})`;
				try {
					const errJson = await res.json();
					if (errJson?.error || errJson?.message) {
						msg = errJson.error || errJson.message;
					}
				} catch {
					// fallback
				}
				throw new Error(msg);
			}
			const blob = await res.blob();
			const url = window.URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = platform === "mac" ? "UnifAI_Guard_macOS.zip" : "UnifAI_Guard_Windows.zip";
			document.body.appendChild(link);
			link.click();
			link.remove();
			window.URL.revokeObjectURL(url);
		} catch (error) {
			setSetupPackageError(error instanceof Error ? error.message : `Failed to download ${platform} setup package`);
		} finally {
			setDownloadingPlatform(null);
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
			setTargetError("Enter a domain only, e.g. chat.example.com (no https://).");
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

	useEffect(() => {
		setRulesPageOffset(0);
	}, [ruleSearch, rulesPageLimit]);

	const rulesTotalPages = Math.ceil(filteredRules.length / rulesPageLimit) || 1;
	const rulesCurrentPage = Math.floor(rulesPageOffset / rulesPageLimit) + 1;
	const pagedRules = filteredRules.slice(rulesPageOffset, rulesPageOffset + rulesPageLimit);

	const getBrowserAiExportPayload = (): ExportFormatsPayload => {
		if (activeTab === "rules") {
			return {
				filename: "browser-ai-guard-rules",
				title: "Browser AI — Guard Rules",
				subtitle: `${filteredRules.length} rule(s)`,
				columns: [
					{ key: "name", header: "Name" },
					{ key: "rule_type", header: "Type" },
					{ key: "severity", header: "Severity" },
					{ key: "action", header: "Action" },
					{ key: "active", header: "Active" },
					{ key: "pattern", header: "Pattern / Policy" },
					{ key: "description", header: "Description" },
				],
				rows: filteredRules.map((r) => ({
					name: r.name,
					rule_type: r.rule_type === "ai_bot" ? "AI Guard Bot" : "Regex",
					severity: r.severity,
					action: r.action,
					active: r.active ? "Yes" : "No",
					pattern: r.rule_type === "ai_bot" ? (r.bot_prompt || "").slice(0, 500) : r.pattern || "",
					description: r.description || "",
				})),
			};
		}
		if (activeTab === "targets") {
			return {
				filename: "browser-ai-targets",
				title: "Browser AI — Target Websites",
				subtitle: `${targets.length} target(s)`,
				columns: [
					{ key: "domain", header: "Domain" },
					{ key: "platform", header: "Platform" },
					{ key: "status", header: "Status" },
					{ key: "host_role", header: "Host role" },
				],
				rows: targets.map((t) => ({
					domain: t.domain,
					platform: t.platform_name || "",
					status: t.block_site ? "Blocked" : t.monitored ? "Monitored" : "Paused",
					host_role: t.host_role || "",
				})),
			};
		}
		if (activeTab === "agents") {
			return {
				filename: "browser-ai-agents",
				title: "Browser AI — Guard Agents",
				subtitle: `${agents.length} agent(s)`,
				columns: [
					{ key: "hostname", header: "Hostname" },
					{ key: "agent_id", header: "Agent ID" },
					{ key: "agent_type", header: "Source" },
					{ key: "status", header: "Status" },
					{ key: "last_seen", header: "Last seen" },
				],
				rows: agents.map((a) => ({
					hostname: a.hostname || "",
					agent_id: a.id || "",
					agent_type: a.agent_type || "endpoint",
					status: a.status || "",
					last_seen: a.last_seen_at || "",
				})),
			};
		}
		// overview + logs
		const logPage = Math.floor(pageOffset / pageLimit) + 1;
		return {
			filename: "browser-ai-prompt-logs",
			title: "Browser AI — Prompt Logs",
			subtitle: `Page ${logPage} · ${logs.length} of ${totalLogs} shown`,
			columns: [
				{ key: "timestamp", header: "Timestamp" },
				{ key: "platform", header: "Platform" },
				{ key: "prompt", header: "Prompt" },
				{ key: "action", header: "Action" },
				{ key: "rule", header: "Rule" },
				{ key: "risk", header: "Risk" },
				{ key: "tokens", header: "Est. Tokens" },
				{ key: "attachment", header: "Attachment" },
			],
			rows: logs.map((log) => ({
				timestamp: log.timestamp ? new Date(log.timestamp).toLocaleString() : "",
				platform: log.platform || "",
				prompt: (log.user_prompt_full || log.user_prompt_preview || "").slice(0, 500),
				action: log.action || "",
				rule: log.rule_triggered || "",
				risk: log.predictive_risk || log.risk_score || "",
				tokens: log.est_tokens ?? "",
				attachment: log.attachment_name || "",
			})),
		};
	};

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

					{activeTab !== "setup" ? (
						<ExportFormatsDropdown
							size="sm"
							className="h-8 text-xs gap-2 border-border"
							getPayload={getBrowserAiExportPayload}
							testId="browser-ai-export-trigger"
						/>
					) : null}

					<Button
						variant="outline"
						size="sm"
						onClick={() => {
							refetchLogs();
							refetchSearchLogs();
							refetchRules();
							refetchTargets();
							refetchAgents();
						}}
						className="gap-2 border-border hover:bg-accent h-8 text-xs"
					>
						<RefreshCw className={`h-3.5 w-3.5 ${logsLoading || agentsLoading || searchLogsLoading ? "animate-spin" : ""}`} />
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
					<TabsTrigger value="search-logs" className="gap-2 text-emerald-400 data-[state=active]:text-emerald-400">
						<Search className="h-4 w-4" /> Search Logs ({totalSearchLogs})
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
						<CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
							<div>
								<CardTitle className="text-lg">Recent Intercepted Activity</CardTitle>
								<CardDescription>Real-time prompt stream captured from browser sessions</CardDescription>
							</div>
							<Button variant="outline" size="sm" className="h-8 text-xs shrink-0" onClick={() => setActiveTab("logs")}>
								Show all
							</Button>
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
													No prompts intercepted yet. Guard agent must be running (v1.6.2+),
													Target site Monitoring ON and Block Website OFF, then fully quit and reopen
													the browser so PAC hits 127.0.0.1:8085. If the AI site opens but logs stay 0,
													traffic is bypassing the proxy — check Guard Agents health / local
													http://127.0.0.1:18085/status.
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

				{/* TAB: SEARCH LOGS */}
				<TabsContent value="search-logs" className="space-y-4">
					{/* KPI Summary Cards */}
					<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<Search className="h-3.5 w-3.5 text-muted-foreground" /> Total Searches Monitored
								</CardDescription>
								<CardTitle className="text-3xl font-bold">{totalSearchLogs}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Google, Bing, DDG, Yahoo — Chrome / Edge / Firefox / Brave / Safari</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<EyeOff className="h-3.5 w-3.5 text-purple-400" /> Incognito &amp; InPrivate
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-purple-400">{incognitoSearchCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Private browsing sessions inspected</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<FileText className="h-3.5 w-3.5 text-emerald-400" /> Search Queries Logged
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-emerald-400">{queriesSearchCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Direct keyword prompts and search intent</p>
							</CardContent>
						</Card>

						<Card className="bg-card border-border">
							<CardHeader className="pb-2">
								<CardDescription className="flex items-center gap-1.5">
									<ExternalLink className="h-3.5 w-3.5 text-blue-400" /> Result Links Clicked
								</CardDescription>
								<CardTitle className="text-3xl font-bold text-blue-400">{clicksSearchCount}</CardTitle>
							</CardHeader>
							<CardContent>
								<p className="text-xs text-muted-foreground">Destination URLs navigated from search</p>
							</CardContent>
						</Card>
					</div>

					{/* Main Search Logs Card */}
					<Card className="bg-card border-border">
						<CardHeader className="pb-4">
							<div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
								<div>
									<CardTitle className="text-lg flex items-center gap-2">
										<Search className="h-5 w-5 text-emerald-400" />
										Search Engine Activity &amp; Privacy Audit
									</CardTitle>
									<CardDescription>
										Real-time search queries and clicked links from any Guard browser (Chrome, Edge, Firefox, Brave, Opera, Safari) — Google, Bing/MSN, DuckDuckGo, Yahoo — including Incognito/InPrivate. Saved to Postgres.
									</CardDescription>
								</div>
								<div className="flex items-center gap-2">
									<Button
										variant="outline"
										size="sm"
										onClick={() => clearSearchLogs()}
										disabled={isClearingSearchLogs || totalSearchLogs === 0}
										className="text-destructive hover:bg-destructive/10 border-destructive/30 text-xs"
									>
										<Trash2 className="h-3.5 w-3.5 mr-1" />
										Clear Search Logs
									</Button>
								</div>
							</div>

							{/* Search & Filter Toolbar */}
							<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
								<div className="relative">
									<Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
									<Input
										placeholder="Filter query, URL, host..."
										value={searchLogQuery}
										onChange={(e) => setSearchLogQuery(e.target.value)}
										className="pl-9 bg-background border-border text-xs"
									/>
								</div>
								<Select value={searchEngineFilter} onValueChange={setSearchEngineFilter}>
									<SelectTrigger className="bg-background border-border text-xs">
										<SelectValue placeholder="All Engines" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="all">All Engines</SelectItem>
										<SelectItem value="google">Google</SelectItem>
										<SelectItem value="bing">Bing</SelectItem>
										<SelectItem value="safari">Safari / Apple</SelectItem>
										<SelectItem value="duck">DuckDuckGo</SelectItem>
										<SelectItem value="brave">Brave Search</SelectItem>
										<SelectItem value="yahoo">Yahoo</SelectItem>
									</SelectContent>
								</Select>
								<Select value={searchBrowserFilter} onValueChange={setSearchBrowserFilter}>
									<SelectTrigger className="bg-background border-border text-xs">
										<SelectValue placeholder="All Browsers" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="all">All Browsers</SelectItem>
										<SelectItem value="chrome">Chrome</SelectItem>
										<SelectItem value="edge">Edge</SelectItem>
										<SelectItem value="safari">Safari</SelectItem>
										<SelectItem value="firefox">Firefox</SelectItem>
										<SelectItem value="brave">Brave</SelectItem>
										<SelectItem value="opera">Opera</SelectItem>
										<SelectItem value="vivaldi">Vivaldi</SelectItem>
									</SelectContent>
								</Select>
								<Select value={searchIncognitoFilter} onValueChange={setSearchIncognitoFilter}>
									<SelectTrigger className="bg-background border-border text-xs">
										<SelectValue placeholder="All Privacy Modes" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="all">All Modes</SelectItem>
										<SelectItem value="true">Incognito / InPrivate Only</SelectItem>
										<SelectItem value="false">Normal Browsing Only</SelectItem>
									</SelectContent>
								</Select>
							</div>
						</CardHeader>

						<CardContent>
							<div className="rounded-md border border-border overflow-x-auto">
								<Table className="w-full min-w-[980px]">
									<TableHeader>
										<TableRow className="border-border hover:bg-transparent">
											<TableHead className="w-[160px]">Timestamp &amp; Agent</TableHead>
											<TableHead className="w-[130px]">Search Engine</TableHead>
											<TableHead className="w-[100px]">Browser</TableHead>
											<TableHead className="w-[160px]">Privacy Mode</TableHead>
											<TableHead className="w-[auto]">Search Query / Prompt</TableHead>
											<TableHead className="w-[220px]">Clicked Result Link</TableHead>
											<TableHead className="w-[150px]">Threat Risk</TableHead>
											<TableHead className="w-[80px] text-right">Inspect</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{searchLogs.length === 0 ? (
											<TableRow>
												<TableCell colSpan={8} className="h-32 text-center text-muted-foreground">
													<div className="flex flex-col items-center justify-center gap-2">
														<Search className="h-6 w-6 text-muted-foreground/50" />
														<p>No search events logged yet.</p>
														<p className="text-xs text-muted-foreground/70">
															Searches in Google, Bing, DuckDuckGo, or Yahoo from Chrome/Edge/Firefox/Brave appear here in real-time.
														</p>
													</div>
												</TableCell>
											</TableRow>
										) : (
											searchLogs.map((log) => {
												const e = log.engine.toLowerCase();
												return (
													<TableRow key={log.id} className="border-border hover:bg-muted/30">
														<TableCell className="font-mono text-xs">
															<div>{new Date(log.timestamp).toLocaleTimeString()}</div>
															<div className="text-[10px] text-muted-foreground">
																{log.agent_hostname || log.client_ip || "Endpoint"}
															</div>
														</TableCell>
														<TableCell>
															{e.includes("google") ? (
																<Badge className="bg-blue-950/80 text-blue-300 border-blue-800/80 gap-1 font-medium text-xs">
																	<Globe className="h-3 w-3 text-blue-400" /> Google
																</Badge>
															) : e.includes("bing") ? (
																<Badge className="bg-cyan-950/80 text-cyan-300 border-cyan-800/80 gap-1 font-medium text-xs">
																	<Compass className="h-3 w-3 text-cyan-400" /> Bing
																</Badge>
															) : e.includes("safari") || e.includes("apple") ? (
																<Badge className="bg-sky-950/80 text-sky-300 border-sky-800/80 gap-1 font-medium text-xs">
																	<Compass className="h-3 w-3 text-sky-400" /> Safari
																</Badge>
															) : e.includes("duck") ? (
																<Badge className="bg-amber-950/80 text-amber-300 border-amber-800/80 gap-1 font-medium text-xs">
																	<Globe className="h-3 w-3 text-amber-400" /> DuckDuckGo
																</Badge>
															) : e.includes("brave") ? (
																<Badge className="bg-orange-950/80 text-orange-300 border-orange-800/80 gap-1 font-medium text-xs">
																	<Globe className="h-3 w-3 text-orange-400" /> Brave Search
																</Badge>
															) : (
																<Badge className="bg-purple-950/80 text-purple-300 border-purple-800/80 gap-1 font-medium text-xs">
																	<Globe className="h-3 w-3 text-purple-400" /> Yahoo
																</Badge>
															)}
														</TableCell>
														<TableCell>
															<Badge variant="outline" className="text-xs bg-black/20">
																{log.browser}
															</Badge>
														</TableCell>
														<TableCell>
															{log.is_incognito ? (
																<Badge className="bg-purple-950/80 text-purple-300 border-purple-800/80 gap-1 font-medium text-xs">
																	<EyeOff className="h-3 w-3 text-purple-400" /> Incognito / InPrivate
																</Badge>
															) : (
																<Badge variant="outline" className="text-muted-foreground gap-1 text-xs">
																	<Eye className="h-3 w-3" /> Normal
																</Badge>
															)}
														</TableCell>
														<TableCell>
															{log.query ? (
																<div className="flex items-start gap-1.5 font-medium text-xs text-foreground max-w-[360px]">
																	<Search className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
																	<span className="break-words line-clamp-2">{log.query}</span>
																</div>
															) : (
																<span className="text-xs italic text-muted-foreground flex items-center gap-1">
																	<ExternalLink className="h-3 w-3" /> [Result Click Navigation]
																</span>
															)}
														</TableCell>
														<TableCell>
															{log.clicked_url ? (
																<a
																	href={log.clicked_url}
																	target="_blank"
																	rel="noopener noreferrer"
																	className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 hover:underline max-w-[200px] truncate"
																	title={log.clicked_url}
																>
																	<ExternalLink className="h-3 w-3 shrink-0" />
																	<span className="truncate">{log.clicked_title || log.clicked_url}</span>
																</a>
															) : (
																<span className="text-xs text-muted-foreground">—</span>
															)}
														</TableCell>
														<TableCell>
															<div className="space-y-0.5">
																{log.predictive_risk === "CRITICAL" ? (
																	<Badge className="bg-red-950/80 text-red-400 border-red-800/80 text-[10px] font-semibold">
																		CRITICAL ({log.risk_score}%)
																	</Badge>
																) : log.predictive_risk === "HIGH" ? (
																	<Badge className="bg-amber-950/80 text-amber-400 border-amber-800/80 text-[10px] font-semibold">
																		HIGH ({log.risk_score}%)
																	</Badge>
																) : log.predictive_risk === "MEDIUM" ? (
																	<Badge className="bg-yellow-950/80 text-yellow-400 border-yellow-800/80 text-[10px] font-semibold">
																		MEDIUM ({log.risk_score}%)
																	</Badge>
																) : (
																	<Badge variant="outline" className="text-muted-foreground text-[10px]">
																		LOW ({log.risk_score}%)
																	</Badge>
																)}
																<div className="text-[10px] text-muted-foreground">{log.risk_category || "General"}</div>
															</div>
														</TableCell>
														<TableCell className="text-right">
															<Button
																variant="ghost"
																size="sm"
																onClick={() => setSelectedSearchLog(log)}
																className="h-7 text-xs hover:bg-accent"
															>
																Inspect
															</Button>
														</TableCell>
													</TableRow>
												);
											})
										)}
									</TableBody>
								</Table>
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
										No built-in DLP patterns. Only rules you create here apply on Target Websites you monitor. Toggle Active to enable/disable without deleting.
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
												Add your own regex or AI policy. UnifAI does not ship default guard patterns — only what you save here is enforced.
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
													placeholder="Rule name"
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
														placeholder="Enter the regex you want to match"
														value={newRulePattern}
														onChange={(e) => setNewRulePattern(e.target.value)}
													/>
													<p className="text-[11px] text-muted-foreground">
														One RE2 regex per rule. Empty form = no rule. Only patterns you save here are enforced (no built-in list).
													</p>
													<RegexLiveTestPanel pattern={newRulePattern} />
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
													onTestEvaluate={() => runTestEvaluate("new")}
													testSample={newRuleTestSample}
													onTestSampleChange={setNewRuleTestSample}
													testResult={newRuleTestResult}
													testing={testingGuardBot}
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
								{pagedRules.map((rule) => (
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

								{filteredRules.length > 0 && (
									<div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-border">
										<div className="flex items-center gap-2 text-xs text-muted-foreground">
											<span>Rows per page</span>
											<Select
												value={rulesPageLimit.toString()}
												onValueChange={(v) => {
													setRulesPageLimit(Number(v));
													setRulesPageOffset(0);
												}}
											>
												<SelectTrigger className="h-8 w-[72px]">
													<SelectValue />
												</SelectTrigger>
												<SelectContent>
													<SelectItem value="10">10</SelectItem>
													<SelectItem value="25">25</SelectItem>
													<SelectItem value="50">50</SelectItem>
												</SelectContent>
											</Select>
											<span>
												Showing {filteredRules.length ? rulesPageOffset + 1 : 0}–
												{Math.min(rulesPageOffset + rulesPageLimit, filteredRules.length)} of {filteredRules.length}
											</span>
										</div>
										<div className="flex items-center gap-2">
											<span className="text-xs text-muted-foreground">
												Page {rulesCurrentPage} of {rulesTotalPages}
											</span>
											<Button
												variant="outline"
												size="sm"
												className="h-8"
												disabled={rulesPageOffset <= 0}
												onClick={() => setRulesPageOffset(Math.max(0, rulesPageOffset - rulesPageLimit))}
											>
												<ChevronLeft className="h-4 w-4" />
											</Button>
											<Button
												variant="outline"
												size="sm"
												className="h-8"
												disabled={rulesPageOffset + rulesPageLimit >= filteredRules.length}
												onClick={() => setRulesPageOffset(rulesPageOffset + rulesPageLimit)}
											>
												<ChevronRight className="h-4 w-4" />
											</Button>
										</div>
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
													placeholder="e.g. chat.example.com"
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
																placeholder="e.g. docs.example.com"
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
										Evaluated in microseconds using Golang RE2 regular expressions. BLOCK wins over REDACT if both match.
									</p>
									<RegexLiveTestPanel pattern={editRulePattern} />
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
									onTestEvaluate={() => runTestEvaluate("edit")}
									testSample={editRuleTestSample}
									onTestSampleChange={setEditRuleTestSample}
									testResult={editRuleTestResult}
									testing={testingGuardBot}
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
					<Card className="bg-card border-border">
						<CardHeader>
							<CardTitle className="text-lg">Fleet defaults (Postgres)</CardTitle>
							<CardDescription>
								Stored in the same company DB. Laptop and network Guard pull these on heartbeat — one dashboard, shared defaults.
							</CardDescription>
						</CardHeader>
						<CardContent className="grid gap-3 sm:grid-cols-2">
							<div className="space-y-1">
								<label className="text-xs text-muted-foreground">Default proxy addr</label>
								<Input
									value={fleetDraft.default_proxy_addr}
									onChange={(e) => setFleetDraft((d) => ({ ...d, default_proxy_addr: e.target.value }))}
								/>
							</div>
							<div className="space-y-1">
								<label className="text-xs text-muted-foreground">PAC advertise addr</label>
								<Input
									value={fleetDraft.pac_advertise_addr}
									onChange={(e) => setFleetDraft((d) => ({ ...d, pac_advertise_addr: e.target.value }))}
								/>
							</div>
							<div className="space-y-1">
								<label className="text-xs text-muted-foreground">PAC sync seconds</label>
								<Input
									type="number"
									value={fleetDraft.pac_sync_seconds}
									onChange={(e) =>
										setFleetDraft((d) => ({ ...d, pac_sync_seconds: Number(e.target.value) || 3 }))
									}
								/>
							</div>
							<div className="space-y-1">
								<label className="text-xs text-muted-foreground">Default agent type</label>
								<Select
									value={fleetDraft.agent_type_default}
									onValueChange={(v) => setFleetDraft((d) => ({ ...d, agent_type_default: v }))}
								>
									<SelectTrigger>
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="endpoint">endpoint (laptop)</SelectItem>
										<SelectItem value="network">network (server)</SelectItem>
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-1 sm:col-span-2">
								<label className="text-xs text-muted-foreground">Notes</label>
								<Input
									value={fleetDraft.notes}
									onChange={(e) => setFleetDraft((d) => ({ ...d, notes: e.target.value }))}
									placeholder="Optional IT notes"
								/>
							</div>
							<div className="sm:col-span-2 flex flex-col gap-2 sm:flex-row sm:items-center">
								<Button
									disabled={savingFleetConfig}
									onClick={async () => {
										setFleetSaveError("");
										setFleetSaveOk(false);
										try {
											await saveFleetConfig(fleetDraft).unwrap();
											setFleetSaveOk(true);
											refetchFleetConfig();
										} catch (err) {
											setFleetSaveError(err instanceof Error ? err.message : "Failed to save fleet config");
										}
									}}
								>
									{savingFleetConfig ? "Saving…" : "Save fleet defaults"}
								</Button>
								{fleetSaveOk ? <p className="text-xs text-emerald-500">Saved to Postgres.</p> : null}
								{fleetSaveError ? <p className="text-xs text-destructive">{fleetSaveError}</p> : null}
							</div>
						</CardContent>
					</Card>

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
						<Select
							value={agentTypeFilter}
							onValueChange={(v) => {
								setAgentTypeFilter(v);
								setAgentPageOffset(0);
							}}
						>
							<SelectTrigger className="w-[160px]">
								<SelectValue placeholder="Source" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">All sources</SelectItem>
								<SelectItem value="endpoint">Laptop Guard</SelectItem>
								<SelectItem value="network">Network / server</SelectItem>
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
									<CardTitle className="text-lg">Guard Agents (laptop + network)</CardTitle>
									<CardDescription>
										Same Browser AI dashboard for laptop Guard EXE and shared server/network proxy. Rules and Prompt Logs are shared.
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
										<TableHead className="w-[160px]">Host</TableHead>
										<TableHead className="w-[100px]">Source</TableHead>
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
											<TableCell className="text-sm">
												{(agent.agent_type || "endpoint") === "network" ? "Network" : "Laptop"}
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
												No Guard agents yet. Install UnifAI_Guard_Setup.exe (Windows) or UnifAI_Guard_macOS.zip (Mac) on laptops and/or run the network proxy (docker compose unifai_broswer_proxy or Guard with server_mode). Same dashboard for both.
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
									<p className="text-xs text-muted-foreground">When off, Windows/macOS uninstall proceeds without a key check.</p>
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
							<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
								<div className="flex items-center gap-3">
									<CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
									<div>
										<CardTitle className="text-lg">Employee Setup Packages</CardTitle>
										<CardDescription>
											Choose Windows or macOS to download the Guard installer package for employee laptops.
										</CardDescription>
									</div>
								</div>
								<div className="flex flex-wrap items-center gap-2.5">
									<Button
										onClick={() => handleDownloadSetupPackage("windows")}
										disabled={downloadingPlatform !== null}
										variant="outline"
										className="gap-2 border-border hover:border-sky-500/60 hover:bg-sky-500/10 transition-colors"
									>
										<svg className="h-4 w-4 fill-current text-sky-400" viewBox="0 0 24 24">
											<path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.949-1.95" />
										</svg>
										{downloadingPlatform === "windows" ? "Preparing Windows..." : "Download for Windows"}
									</Button>
									<Button
										onClick={() => handleDownloadSetupPackage("mac")}
										disabled={downloadingPlatform !== null}
										className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
									>
										<svg className="h-4 w-4 fill-current" viewBox="0 0 170 170">
											<path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.7-3.04-7.7-7.9-11.99-14.57-6.09-9.46-10.9-20.2-14.42-32.22-3.52-12.01-5.28-23.23-5.28-33.64 0-14.78 3.82-27.17 11.45-37.19 7.63-10.01 17.1-15.13 28.4-15.35 4.35 0 9.29 1.14 14.81 3.42 5.53 2.29 9.38 3.48 11.56 3.59 1.74 0 5.86-1.25 12.38-3.76 6.52-2.5 12.16-3.6 16.92-3.3 12.51.98 22.37 5.76 29.57 14.34-11.09 6.74-16.53 16.09-16.32 28.05.22 9.57 3.91 17.61 11.09 24.13 7.18 6.52 15.66 10.11 25.44 10.76-2.28 7.07-5.22 14.67-8.81 22.8zM119.22 31.84c0-7.18 2.61-13.91 7.83-20.19 5.22-6.28 11.52-10.22 18.91-11.83 1.09 6.74-.22 13.48-3.91 20.22-3.7 6.74-9.35 11.3-16.96 13.7-1.09-.76-2.93-1.3-5.52-1.63-.22-.11-.35-.27-.35-.27z" />
										</svg>
										{downloadingPlatform === "mac" ? "Preparing Mac..." : "Download for Mac"}
									</Button>
								</div>
							</div>
						</CardHeader>
						<CardContent className="pt-0 space-y-3">
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
								<div className="rounded-md border border-border/80 p-3 bg-muted/20">
									<div className="flex items-center gap-2 font-medium text-xs text-foreground mb-1">
										<span className="h-2 w-2 rounded-full bg-sky-400"></span>
										Windows Package (<code className="bg-black/40 px-1 rounded text-[11px]">UnifAI_Guard_Windows.zip</code>)
									</div>
									<p className="text-xs text-muted-foreground">
										Includes <code className="bg-black/40 px-1 rounded">UnifAI_Guard_Setup.exe</code> installer with auto-start and enterprise proxy routing.
									</p>
								</div>
								<div className="rounded-md border border-border/80 p-3 bg-muted/20">
									<div className="flex items-center gap-2 font-medium text-xs text-foreground mb-1">
										<span className="h-2 w-2 rounded-full bg-primary"></span>
										macOS Package (<code className="bg-black/40 px-1 rounded text-[11px]">UnifAI_Guard_macOS.zip</code>)
									</div>
									<p className="text-xs text-muted-foreground">
										Includes <code className="bg-black/40 px-1 rounded">UnifAI_Guard.app</code> + <code className="bg-black/40 px-1 rounded">Install_UnifAI_Guard.command</code>.
									</p>
								</div>
							</div>
							{setupPackageError ? <p className="mt-2 text-sm text-red-400">{setupPackageError}</p> : null}
						</CardContent>
					</Card>

					<Card className="bg-card border-border">
						<CardHeader>
							<CardTitle className="text-lg">Install Steps</CardTitle>
							<CardDescription>Download the package for your OS and install Guard on Windows or Mac laptops.</CardDescription>
						</CardHeader>
						<CardContent className="space-y-6">
							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">1</span>
									<span>Download the package for your OS</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Click <strong>Download for Windows</strong> or <strong>Download for Mac</strong> above based on your device.
								</p>
							</div>

							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 min-w-6 px-1.5 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">Win</span>
									<span>Windows</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Run <code className="bg-black/40 px-1 rounded">UnifAI_Guard_Setup.exe</code>. Keep autostart enabled so Guard starts at Windows login.
									To turn OFF / uninstall: Windows Settings → Apps → UnifAI Guard → Uninstall (company uninstall key).
								</p>
							</div>

							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 min-w-6 px-1.5 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">Mac</span>
									<span>Mac</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Unzip <code className="bg-black/40 px-1 rounded">UnifAI_Guard_macOS.zip</code>, then double-click{" "}
									<code className="bg-black/40 px-1 rounded">Install_UnifAI_Guard.command</code>
									{" "}(Right-click → Open if Gatekeeper blocks). See <code className="bg-black/40 px-1 rounded">INSTALL_MACOS.txt</code>.
									To turn OFF / uninstall: double-click <code className="bg-black/40 px-1 rounded">Uninstall_UnifAI_Guard.command</code>
									{" "}and enter the same company uninstall key (<code className="bg-black/40 px-1 rounded">UNINSTALL_MACOS.txt</code>).
								</p>
							</div>

							<div className="space-y-4">
								<div className="flex items-center gap-2 font-semibold">
									<span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">3</span>
									<span>Open monitored AI websites and verify logs</span>
								</div>
								<p className="text-xs text-muted-foreground pl-8">
									Fully quit browsers, reopen, visit a monitored AI site, send a test prompt.
									Confirm in Prompt Logs and Agents.
								</p>
							</div>

							<div className="rounded-md border border-border bg-background p-4 text-xs space-y-2">
								<p className="font-semibold text-foreground">Package contents</p>
								<ul className="list-disc pl-5 text-muted-foreground space-y-1">
									<li><code>UnifAI_Guard_Windows.zip</code> — Windows <code>UnifAI_Guard_Setup.exe</code> installer &amp; docs</li>
									<li><code>UnifAI_Guard_macOS.zip</code> — macOS <code>UnifAI_Guard.app</code> + Install &amp; Uninstall scripts</li>
									<li><code>INSTALL_WINDOWS.txt</code> / <code>INSTALL_MACOS.txt</code> / <code>UNINSTALL_MACOS.txt</code></li>
									<li><code>VERSION.txt</code></li>
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

								<div className="rounded-lg border border-border/80 bg-background/60 p-3.5 space-y-1">
									<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Guard decision (predict)</Label>
									<p className="text-sm font-semibold break-words">{predictReasonLabel(selectedLog)}</p>
									<p className="text-[11px] text-muted-foreground">
										Risk: {selectedLog.predictive_risk || "LOW"}
										{selectedLog.risk_score != null ? ` · score ${selectedLog.risk_score}` : ""}
										{selectedLog.predicted_category ? ` · ${selectedLog.predicted_category}` : ""}
									</p>
								</div>

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
										<div className="flex items-center justify-between gap-2">
											<Label className="text-[11px] uppercase tracking-wide text-muted-foreground">Extracted file text (used for bot check)</Label>
											{logExtractedText(selectedLog).length > 4000 ? (
												<Button
													type="button"
													variant="ghost"
													size="sm"
													className="h-7 text-xs"
													onClick={() => setExtractedTextExpanded((v) => !v)}
												>
													{extractedTextExpanded ? "Show less" : "Show all"}
												</Button>
											) : null}
										</div>
										<pre className="p-3.5 bg-background border border-border rounded-lg font-mono text-[11px] max-h-64 overflow-auto whitespace-pre-wrap break-words">
											{extractedTextExpanded
												? logExtractedText(selectedLog)
												: logExtractedText(selectedLog).slice(0, 4000)}
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
						setAttachmentBlob(null);
						setAttachmentSheets([]);
						setAttachmentSheetIndex(0);
						setAttachmentTruncated(false);
						setAttachmentShowAll(false);
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
								{attachmentTruncated && attachmentBlob ? (
									<Button
										size="sm"
										variant="outline"
										className="h-8 gap-1.5"
										disabled={pdfLoading}
										onClick={() => reloadAttachmentPreview(true)}
									>
										{pdfLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
										Show all
									</Button>
								) : null}
								{attachmentShowAll ? (
									<Button
										size="sm"
										variant="ghost"
										className="h-8 text-xs"
										disabled={pdfLoading}
										onClick={() => reloadAttachmentPreview(false)}
									>
										Show less
									</Button>
								) : null}
								{attachmentSheets.length > 1 ? (
									<div className="flex flex-wrap items-center gap-1.5">
										{attachmentSheets.map((sheet, idx) => (
											<Button
												key={`${sheet.name}-${idx}`}
												size="sm"
												variant={idx === attachmentSheetIndex ? "secondary" : "outline"}
												className="h-7 text-[11px]"
												onClick={() => {
													setAttachmentSheetIndex(idx);
													setAttachmentPreviewHtml(sheet.html);
												}}
											>
												{sheet.name}
												<span className="opacity-70 ml-1">({sheet.rowCount})</span>
											</Button>
										))}
									</div>
								) : null}
								<div className="flex rounded-md border border-border overflow-hidden ml-auto">
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

			{/* Search Log Inspection Dialog */}
			<Dialog open={selectedSearchLog !== null} onOpenChange={(open) => !open && setSelectedSearchLog(null)}>
				<DialogContent className="max-w-xl bg-card border-border">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2 text-base font-semibold">
							<Search className="h-4 w-4 text-emerald-400" />
							Search Event Inspection
						</DialogTitle>
						<DialogDescription>
							Detailed telemetry captured from search engine session
						</DialogDescription>
					</DialogHeader>

					{selectedSearchLog && (
						<div className="space-y-4 text-xs">
							{/* Query box */}
							<div className="rounded-md border border-border bg-background p-3 space-y-1">
								<p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Search Query / Prompt</p>
								<p className="font-mono text-sm text-foreground font-semibold">
									{selectedSearchLog.query || "[Direct Result Navigation without Query]"}
								</p>
							</div>

							{/* Clicked link if any */}
							{selectedSearchLog.clicked_url && (
								<div className="rounded-md border border-border bg-background p-3 space-y-1">
									<p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Clicked Destination Link</p>
									<a
										href={selectedSearchLog.clicked_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-1.5 text-blue-400 hover:underline font-mono text-xs break-all"
									>
										<ExternalLink className="h-3 w-3 shrink-0" />
										{selectedSearchLog.clicked_url}
									</a>
								</div>
							)}

							{/* Threat Assessment */}
							<div className="grid grid-cols-2 gap-3">
								<div className="rounded-md border border-border bg-background p-3 space-y-1">
									<p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Predictive Threat Risk</p>
									<div className="flex items-center gap-2">
										<Badge
											className={
												selectedSearchLog.predictive_risk === "CRITICAL"
													? "bg-red-950/80 text-red-400 border-red-800/80 font-bold"
													: selectedSearchLog.predictive_risk === "HIGH"
													? "bg-amber-950/80 text-amber-400 border-amber-800/80 font-bold"
													: "bg-emerald-950/80 text-emerald-400 border-emerald-800/80"
											}
										>
											{selectedSearchLog.predictive_risk} ({selectedSearchLog.risk_score}%)
										</Badge>
										<span className="text-muted-foreground">{selectedSearchLog.risk_category}</span>
									</div>
								</div>

								<div className="rounded-md border border-border bg-background p-3 space-y-1">
									<p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Privacy Mode</p>
									<div>
										{selectedSearchLog.is_incognito ? (
											<Badge className="bg-purple-950/80 text-purple-300 border-purple-800/80 gap-1 font-medium">
												<EyeOff className="h-3 w-3 text-purple-400" /> Incognito / InPrivate Mode
											</Badge>
										) : (
											<Badge variant="outline" className="text-muted-foreground gap-1">
												<Eye className="h-3 w-3" /> Normal Browsing
											</Badge>
										)}
									</div>
								</div>
							</div>

							{/* Technical Details */}
							<div className="rounded-md border border-border bg-background p-3 space-y-2">
								<p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Technical Metadata</p>
								<div className="grid grid-cols-2 gap-2 text-muted-foreground font-mono text-[11px]">
									<div><span className="text-foreground font-semibold">Engine:</span> {selectedSearchLog.engine}</div>
									<div><span className="text-foreground font-semibold">Browser:</span> {selectedSearchLog.browser}</div>
									<div><span className="text-foreground font-semibold">Client IP:</span> {selectedSearchLog.client_ip}</div>
									<div><span className="text-foreground font-semibold">Device:</span> {selectedSearchLog.agent_hostname || "Local Endpoint"}</div>
									<div className="col-span-2 break-all"><span className="text-foreground font-semibold">Host:</span> {selectedSearchLog.host}</div>
									<div className="col-span-2"><span className="text-foreground font-semibold">Timestamp:</span> {new Date(selectedSearchLog.timestamp).toLocaleString()}</div>
								</div>
							</div>
						</div>
					)}

					<DialogFooter>
						<Button variant="outline" size="sm" onClick={() => setSelectedSearchLog(null)}>
							Close
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
