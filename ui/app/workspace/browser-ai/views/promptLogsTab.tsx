import React, { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, Eye, ShieldAlert, ShieldCheck } from "lucide-react";

export interface PromptLogItem {
	id: string;
	timestamp: string;
	platform: string;
	user_prompt_preview: string;
	est_tokens: number;
	client_ip: string;
	status: string;
	is_blocked: boolean;
	blocked_reason?: string;
	full_content?: string;
}

export const initialPromptLogs: PromptLogItem[] = [];

export function PromptLogsTab({ logs }: { logs?: PromptLogItem[] }) {
	const [searchTerm, setSearchTerm] = useState("");
	const [platformFilter, setPlatformFilter] = useState("all");
	const [statusFilter, setStatusFilter] = useState("all");
	const [selectedLog, setSelectedLog] = useState<PromptLogItem | null>(null);
	const [liveLogs, setLiveLogs] = useState<PromptLogItem[]>([]);
	const [activeToast, setActiveToast] = useState<{ id: string; platform: string; prompt: string; reason: string } | null>(null);

	React.useEffect(() => {
		const fetchLiveLogs = async () => {
			try {
				// Query UnifAI backend PostgreSQL API endpoint
				const apiRes = await fetch(`/api/browser-ai/logs?limit=100&t=${Date.now()}`, { cache: "no-store" });
				if (apiRes.ok) {
					const apiData = await apiRes.json();
					if (apiData && Array.isArray(apiData.logs) && apiData.logs.length > 0) {
						const formatted: PromptLogItem[] = apiData.logs.map((item: any, idx: number) => ({
							id: item.id || `api-${idx}`,
							timestamp: item.timestamp || item.created_at || "",
							platform: item.platform || "AI Platform",
							user_prompt_preview: item.user_prompt_preview || item.prompt_preview || item.user_prompt_full || "",
							est_tokens: item.est_tokens || 1,
							client_ip: item.client_ip || "127.0.0.1",
							status: item.action || item.status || "Allowed",
							is_blocked: item.action === "Blocked" || !!item.is_blocked || item.status?.toLowerCase().includes("blocked"),
							blocked_reason: item.rule_triggered || item.blocked_reason || "",
							full_content: item.user_prompt_full || item.full_content || item.prompt_preview || "",
						}));
						setLiveLogs(formatted);
						const blocked = formatted.find(l => l.is_blocked);
						if (blocked) {
							setActiveToast(prev => (!prev || prev.id !== blocked.id ? { id: blocked.id, platform: blocked.platform, prompt: blocked.user_prompt_preview, reason: blocked.blocked_reason || blocked.status } : prev));
						}
					}
				}
			} catch (e) {
				// Ignore fetch error
			}
		};
		fetchLiveLogs();
		const interval = setInterval(fetchLiveLogs, 2000);
		return () => clearInterval(interval);
	}, []);

	const activeLogs = useMemo(() => {
		if (liveLogs && liveLogs.length > 0) return liveLogs;
		return logs || [];
	}, [logs, liveLogs]);

	const filteredLogs = useMemo(() => {
		return activeLogs.filter((item) => {
			const matchesSearch =
				item.user_prompt_preview.toLowerCase().includes(searchTerm.toLowerCase()) ||
				item.platform.toLowerCase().includes(searchTerm.toLowerCase()) ||
				item.status.toLowerCase().includes(searchTerm.toLowerCase()) ||
				item.client_ip.includes(searchTerm);

			const matchesPlatform = platformFilter === "all" || item.platform.toLowerCase() === platformFilter.toLowerCase();
			const matchesStatus =
				statusFilter === "all" ||
				(statusFilter === "allowed" && !item.is_blocked) ||
				(statusFilter === "blocked" && item.is_blocked);

			return matchesSearch && matchesPlatform && matchesStatus;
		});
	}, [activeLogs, searchTerm, platformFilter, statusFilter]);

	const getPlatformBadge = (platform: string) => {
		switch (platform.toLowerCase()) {
			case "chatgpt":
				return <Badge className="bg-teal-500/15 text-teal-400 border-teal-500/30 hover:bg-teal-500/25">ChatGPT</Badge>;
			case "claude":
				return <Badge className="bg-purple-500/15 text-purple-400 border-purple-500/30 hover:bg-purple-500/25">Claude</Badge>;
			case "gemini":
				return <Badge className="bg-blue-500/15 text-blue-400 border-blue-500/30 hover:bg-blue-500/25">Gemini</Badge>;
			case "perplexity":
				return <Badge className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/25">Perplexity</Badge>;
			case "copilot":
				return <Badge className="bg-indigo-500/15 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/25">Copilot</Badge>;
			default:
				return <Badge variant="outline">{platform}</Badge>;
		}
	};

	return (
		<div className="space-y-4 relative">
			{/* Floating Security Toast Notification */}
			{activeToast && (
				<div className="fixed bottom-6 right-6 z-50 max-w-sm bg-red-950/95 border-2 border-red-500/80 text-white p-4 rounded-xl shadow-2xl backdrop-blur-md flex items-start gap-3 animate-in slide-in-from-bottom-5 duration-300">
					<ShieldAlert className="w-6 h-6 text-red-400 shrink-0 mt-0.5 animate-pulse" />
					<div className="flex-1 space-y-1">
						<div className="flex items-center justify-between">
							<h4 className="text-xs font-bold text-red-300 tracking-wide uppercase">🚨 Policy Violation Alert</h4>
							<button onClick={() => setActiveToast(null)} className="text-muted-foreground hover:text-white text-xs font-bold px-1">✕</button>
						</div>
						<p className="text-xs text-red-100">
							Secret key leak blocked on <strong>{activeToast.platform}</strong>!
						</p>
						<div className="bg-black/60 p-2 rounded text-[11px] font-mono text-red-300 truncate border border-red-900/60">
							{activeToast.prompt}
						</div>
					</div>
				</div>
			)}
			{/* Security Violation Alert Banner */}
			{activeLogs.some((l) => l.is_blocked || l.status?.toLowerCase().includes("blocked") || l.status?.toLowerCase().includes("restriction")) && (
				<div className="bg-red-950/60 border border-red-800/80 text-red-200 p-3.5 rounded-lg flex items-center justify-between gap-3 text-xs shadow-lg animate-in fade-in duration-300">
					<div className="flex items-center gap-2.5">
						<ShieldAlert className="w-4 h-4 text-red-400 animate-pulse shrink-0" />
						<span>
							<strong>🚨 COMPANY SECURITY POLICY NOTIFICATION:</strong> High-risk prompt or sensitive secret key leak detected and blocked in Web AI chat!
						</span>
					</div>
					<Badge variant="destructive" className="text-[10px] tracking-wide shrink-0">POLICY ENFORCED</Badge>
				</div>
			)}

			{/* Subheader and Controls */}
			<div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card p-4 rounded-lg border">
				<div>
					<h3 className="text-base font-semibold tracking-tight">Prompt & Chat History</h3>
					<p className="text-xs text-muted-foreground">Live intercepted requests passing through the proxy</p>
				</div>

				<div className="flex flex-wrap items-center gap-2">
					<div className="relative min-w-[240px]">
						<Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
						<Input
							placeholder="Search prompts or domain..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="pl-8 text-xs h-9"
						/>
					</div>

					<Select value={platformFilter} onValueChange={setPlatformFilter}>
						<SelectTrigger className="w-[140px] text-xs h-9">
							<SelectValue placeholder="All Platforms" />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All Platforms</SelectItem>
							<SelectItem value="chatgpt">ChatGPT</SelectItem>
							<SelectItem value="claude">Claude</SelectItem>
							<SelectItem value="gemini">Gemini</SelectItem>
							<SelectItem value="perplexity">Perplexity</SelectItem>
							<SelectItem value="copilot">Copilot</SelectItem>
						</SelectContent>
					</Select>

					<Select value={statusFilter} onValueChange={setStatusFilter}>
						<SelectTrigger className="w-[130px] text-xs h-9">
							<SelectValue placeholder="All Status" />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All Status</SelectItem>
							<SelectItem value="allowed">Allowed</SelectItem>
							<SelectItem value="blocked">Blocked</SelectItem>
						</SelectContent>
					</Select>
				</div>
			</div>

			{/* Logs Data Table */}
			<div className="border rounded-lg overflow-hidden bg-card">
				<div className="overflow-x-auto">
					<table className="w-full text-xs text-left border-collapse">
						<thead>
							<tr className="border-b bg-muted/50 font-medium text-muted-foreground">
								<th className="px-4 py-3 min-w-[150px]">Timestamp</th>
								<th className="px-4 py-3 min-w-[110px]">Platform</th>
								<th className="px-4 py-3 min-w-[280px]">User Prompt Preview</th>
								<th className="px-4 py-3 min-w-[100px]">Est. Tokens</th>
								<th className="px-4 py-3 min-w-[170px]">Status</th>
								<th className="px-4 py-3 text-right min-w-[90px]">Action</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-border">
							{filteredLogs.length === 0 ? (
								<tr>
									<td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
										No prompt logs found matching filters.
									</td>
								</tr>
							) : (
								filteredLogs.map((log) => {
									const isBlocked = log.is_blocked || log.status?.toLowerCase().includes("blocked") || log.status?.toLowerCase().includes("restriction");
									return (
										<tr key={log.id} className="hover:bg-muted/30 transition-colors">
											<td className="px-4 py-3 font-mono text-muted-foreground">{log.timestamp}</td>
											<td className="px-4 py-3">{getPlatformBadge(log.platform)}</td>
											<td className="px-4 py-3 font-mono text-foreground/90 max-w-[320px] truncate" title={log.user_prompt_preview}>
												{log.user_prompt_preview}
											</td>
											<td className="px-4 py-3 font-mono text-muted-foreground">{log.est_tokens} tokens</td>
											<td className="px-4 py-3">
												{isBlocked ? (
													<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-red-950/60 text-red-400 border border-red-800/50">
														<ShieldAlert className="w-3 h-3 text-red-400" />
														{log.status}
													</span>
												) : (
													<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
														<ShieldCheck className="w-3 h-3 text-emerald-400" />
														Allowed
													</span>
												)}
											</td>
											<td className="px-4 py-3 text-right">
												<Button
													variant="ghost"
													size="sm"
													onClick={() => setSelectedLog(log)}
													className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1"
												>
													<Eye className="w-3.5 h-3.5" /> View Full
												</Button>
											</td>
										</tr>
									);
								})
							)}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}
