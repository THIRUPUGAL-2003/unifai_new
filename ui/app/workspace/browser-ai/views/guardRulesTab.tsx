import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ShieldCheck, Plus, Search, Pencil, Trash2, Upload } from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

export interface GuardRule {
	id: string;
	name: string;
	pattern: string;
	severity: "CRITICAL" | "HIGH" | "MEDIUM";
	enabled: boolean;
	action: "BLOCK" | "ALERT";
	description: string;
}

export interface BrowserControls {
	enabled: boolean;
	block_upload: boolean;
}

export const initialGuardRules: GuardRule[] = [];

export function GuardRulesTab() {
	const [rules, setRules] = useState<GuardRule[]>(initialGuardRules);
	const [controls, setControls] = useState<BrowserControls>({
		enabled: true,
		block_upload: false,
	});
	const [search, setSearch] = useState("");
	const [isAddOpen, setIsAddOpen] = useState(false);
	const [editRule, setEditRule] = useState<GuardRule | null>(null);

	const [newRuleName, setNewRuleName] = useState("");
	const [newPattern, setNewPattern] = useState("");
	const [newSeverity, setNewSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("HIGH");
	const [newDescription, setNewDescription] = useState("");
	const [newAction, setNewAction] = useState<"BLOCK" | "ALERT">("BLOCK");

	const [editRuleName, setEditRuleName] = useState("");
	const [editPattern, setEditPattern] = useState("");
	const [editSeverity, setEditSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM">("HIGH");
	const [editDescription, setEditDescription] = useState("");
	const [editAction, setEditAction] = useState<"BLOCK" | "ALERT">("BLOCK");

	useEffect(() => {
		const load = async () => {
			try {
				const [rulesRes, controlsRes] = await Promise.all([
					fetch(`/api/browser-ai/rules?t=${Date.now()}`),
					fetch(`/api/browser-ai/controls?t=${Date.now()}`),
				]);
				if (rulesRes.ok) {
					const data = await rulesRes.json();
					if (data && Array.isArray(data.rules)) {
						setRules(
							data.rules.map((r: any) => ({
								id: r.id,
								name: r.name || "Rule",
								pattern: r.pattern || "",
								severity: (r.severity as any) || "HIGH",
								enabled: r.active !== false,
								action: r.action === "WARN" || r.action === "ALERT" ? "ALERT" : "BLOCK",
								description: r.description || "",
							}))
						);
					}
				}
				if (controlsRes.ok) {
					const data = await controlsRes.json();
					if (data?.controls) {
						setControls({
							enabled: !!data.controls.enabled,
							block_upload: !!data.controls.block_upload,
						});
					}
				}
			} catch {
				// keep defaults
			}
		};
		load();
	}, []);

	const patchControl = async (patch: Partial<BrowserControls>) => {
		const next = { ...controls, ...patch };
		setControls(next);
		try {
			await fetch(`/api/browser-ai/controls`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(patch),
			});
		} catch {
			// ignore
		}
	};

	const toggleRule = async (id: string) => {
		const target = rules.find((r) => r.id === id);
		if (!target) return;
		const nextEnabled = !target.enabled;
		setRules((prev) => prev.map((r) => (r.id === id ? { ...r, enabled: nextEnabled } : r)));
		try {
			await fetch(`/api/browser-ai/rules/${id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ active: nextEnabled }),
			});
		} catch {
			// ignore
		}
	};

	const handleAddRule = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!newRuleName.trim() || !newPattern.trim()) return;
		const createdRule: GuardRule = {
			id: `rule-${Date.now()}`,
			name: newRuleName.trim(),
			pattern: newPattern.trim(),
			severity: newSeverity,
			enabled: true,
			action: newAction,
			description: newDescription.trim() || "Custom DLP security guardrail rule.",
		};
		setRules([createdRule, ...rules]);
		setNewRuleName("");
		setNewPattern("");
		setNewDescription("");
		setNewSeverity("HIGH");
		setNewAction("BLOCK");
		setIsAddOpen(false);
		try {
			await fetch(`/api/browser-ai/rules`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					id: createdRule.id,
					name: createdRule.name,
					pattern: createdRule.pattern,
					severity: createdRule.severity,
					active: true,
					action: createdRule.action,
					description: createdRule.description,
				}),
			});
		} catch {
			// ignore
		}
	};

	const handleEditRuleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!editRule || !editRuleName.trim() || !editPattern.trim()) return;
		setRules((prev) =>
			prev.map((r) =>
				r.id === editRule.id
					? {
							...r,
							name: editRuleName.trim(),
							pattern: editPattern.trim(),
							severity: editSeverity,
							action: editAction,
							description: editDescription.trim(),
					  }
					: r
			)
		);
		const ruleId = editRule.id;
		setEditRule(null);
		try {
			await fetch(`/api/browser-ai/rules/${ruleId}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					name: editRuleName.trim(),
					pattern: editPattern.trim(),
					severity: editSeverity,
					action: editAction,
					description: editDescription.trim(),
				}),
			});
		} catch {
			// ignore
		}
	};

	const handleDeleteRule = async (id: string) => {
		setRules((prev) => prev.filter((r) => r.id !== id));
		try {
			await fetch(`/api/browser-ai/rules/${id}`, { method: "DELETE" });
		} catch {
			// ignore
		}
	};

	const filteredRules = rules.filter(
		(r) =>
			r.name.toLowerCase().includes(search.toLowerCase()) ||
			r.description.toLowerCase().includes(search.toLowerCase()) ||
			r.pattern.toLowerCase().includes(search.toLowerCase())
	);

	return (
		<div className="space-y-4">
			{/* Browser Interaction Controls */}
			<div className="bg-card p-4 rounded-lg border space-y-4">
				<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
					<div>
						<h3 className="text-base font-semibold tracking-tight">Browser Interaction Controls</h3>
						<p className="text-xs text-muted-foreground">
							Enable/disable file upload blocking on AI websites
						</p>
					</div>
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground font-medium">Master Enable</span>
						<Switch checked={controls.enabled} onCheckedChange={(v) => patchControl({ enabled: v })} />
						<span className="text-xs font-semibold">{controls.enabled ? "Enabled" : "Disabled"}</span>
					</div>
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-xl">
					<div className="rounded-lg border p-3 flex items-start justify-between gap-3">
						<div className="flex items-start gap-2">
							<Upload className="w-4 h-4 mt-0.5 text-red-400" />
							<div>
								<p className="text-sm font-semibold">Block Upload</p>
								<p className="text-[11px] text-muted-foreground">Block file uploads to AI chats</p>
							</div>
						</div>
						<Switch
							checked={controls.block_upload}
							disabled={!controls.enabled}
							onCheckedChange={(v) => patchControl({ block_upload: v })}
						/>
					</div>
				</div>
			</div>

			{/* Top Bar */}
			<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card p-4 rounded-lg border">
				<div>
					<h3 className="text-base font-semibold tracking-tight">DLP Guard Rules ({rules.filter((r) => r.enabled).length} Active)</h3>
					<p className="text-xs text-muted-foreground">Real-time regular expressions matched against browser prompts</p>
				</div>
				<div className="flex items-center gap-3">
					<div className="relative">
						<Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
						<Input
							placeholder="Search guard rules..."
							value={search}
							onChange={(e) => setSearch(e.target.value)}
							className="pl-8 text-xs h-9 w-[220px]"
						/>
					</div>
					<Button size="sm" onClick={() => setIsAddOpen(true)} className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground">
						<Plus className="w-3.5 h-3.5" /> Add Rule
					</Button>
				</div>
			</div>

			{/* Rules List */}
			<div className="space-y-3">
				{filteredRules.map((rule) => (
					<div
						key={rule.id}
						className="p-4 rounded-lg border bg-card hover:border-primary/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
					>
						<div className="space-y-1 max-w-2xl">
							<div className="flex items-center gap-2">
								<h4 className="font-semibold text-sm">{rule.name}</h4>
								<Badge
									variant="outline"
									className={
										rule.severity === "CRITICAL"
											? "bg-red-500/10 text-red-400 border-red-500/30 text-[10px]"
											: rule.severity === "HIGH"
											? "bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px]"
											: "bg-blue-500/10 text-blue-400 border-blue-500/30 text-[10px]"
									}
								>
									{rule.severity}
								</Badge>
								<Badge className="bg-destructive text-destructive-foreground text-[10px]">{rule.action}</Badge>
							</div>
							<p className="text-xs text-muted-foreground">{rule.description}</p>
							<div className="pt-1">
								<code className="bg-muted px-2 py-0.5 rounded text-[11px] font-mono text-muted-foreground block w-fit truncate max-w-xl">
									{rule.pattern}
								</code>
							</div>
						</div>
						<div className="flex items-center gap-4 border-t md:border-t-0 pt-2 md:pt-0">
							<div className="flex items-center gap-1">
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 text-muted-foreground hover:text-foreground"
									title="Edit Rule"
									onClick={() => {
										setEditRule(rule);
										setEditRuleName(rule.name);
										setEditPattern(rule.pattern);
										setEditSeverity(rule.severity);
										setEditAction(rule.action);
										setEditDescription(rule.description);
									}}
								>
									<Pencil className="w-3.5 h-3.5" />
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 text-muted-foreground hover:text-red-400"
									title="Delete Rule"
									onClick={() => handleDeleteRule(rule.id)}
								>
									<Trash2 className="w-3.5 h-3.5" />
								</Button>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-xs text-muted-foreground font-medium">{rule.enabled ? "Active" : "Disabled"}</span>
								<Switch checked={rule.enabled} onCheckedChange={() => toggleRule(rule.id)} />
							</div>
						</div>
					</div>
				))}
			</div>

			{/* Add Rule Dialog */}
			<Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
				<DialogContent className="sm:max-w-md bg-card">
					<form onSubmit={handleAddRule}>
						<DialogHeader>
							<DialogTitle className="flex items-center gap-2">
								<ShieldCheck className="w-5 h-5 text-primary" />
								Add New DLP Guard Rule
							</DialogTitle>
							<DialogDescription className="text-xs">
								Create a custom regular expression rule to block or flag sensitive secrets in browser prompts.
							</DialogDescription>
						</DialogHeader>
						<div className="space-y-4 py-4 text-xs">
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Rule Name</label>
								<Input placeholder="e.g. GitHub Personal Access Token" value={newRuleName} onChange={(e) => setNewRuleName(e.target.value)} required className="text-xs h-9" />
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Regex Pattern</label>
								<Input placeholder="e.g. ghp_[a-zA-Z0-9]{36}" value={newPattern} onChange={(e) => setNewPattern(e.target.value)} required className="text-xs h-9 font-mono" />
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Severity</label>
								<Select value={newSeverity} onValueChange={(val: any) => setNewSeverity(val)}>
									<SelectTrigger className="h-9 text-xs">
										<SelectValue placeholder="Select Severity" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="CRITICAL">CRITICAL</SelectItem>
										<SelectItem value="HIGH">HIGH</SelectItem>
										<SelectItem value="MEDIUM">MEDIUM</SelectItem>
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Action</label>
								<Select value={newAction} onValueChange={(val: any) => setNewAction(val)}>
									<SelectTrigger className="h-9 text-xs">
										<SelectValue placeholder="Select Action" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="BLOCK">BLOCK</SelectItem>
										<SelectItem value="ALERT">ALERT</SelectItem>
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Description</label>
								<Textarea placeholder="Describe what this rule detects..." value={newDescription} onChange={(e) => setNewDescription(e.target.value)} className="text-xs resize-none h-20" />
							</div>
						</div>
						<DialogFooter className="gap-2 sm:gap-0">
							<Button type="button" variant="outline" size="sm" onClick={() => setIsAddOpen(false)}>
								Cancel
							</Button>
							<Button type="submit" size="sm" className="bg-primary text-primary-foreground">
								Save Rule
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>

			{/* Edit Rule Dialog */}
			<Dialog open={!!editRule} onOpenChange={(open) => !open && setEditRule(null)}>
				<DialogContent className="sm:max-w-md bg-card">
					<form onSubmit={handleEditRuleSubmit}>
						<DialogHeader>
							<DialogTitle className="flex items-center gap-2">
								<Pencil className="w-5 h-5 text-primary" />
								Edit DLP Guard Rule
							</DialogTitle>
							<DialogDescription className="text-xs">Modify rule pattern, severity, and action enforcement.</DialogDescription>
						</DialogHeader>
						<div className="space-y-4 py-4 text-xs">
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Rule Name</label>
								<Input value={editRuleName} onChange={(e) => setEditRuleName(e.target.value)} required className="text-xs h-9" />
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Regex Pattern</label>
								<Input value={editPattern} onChange={(e) => setEditPattern(e.target.value)} required className="text-xs h-9 font-mono" />
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Severity</label>
								<Select value={editSeverity} onValueChange={(val: any) => setEditSeverity(val)}>
									<SelectTrigger className="h-9 text-xs">
										<SelectValue placeholder="Select Severity" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="CRITICAL">CRITICAL</SelectItem>
										<SelectItem value="HIGH">HIGH</SelectItem>
										<SelectItem value="MEDIUM">MEDIUM</SelectItem>
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Action</label>
								<Select value={editAction} onValueChange={(val: any) => setEditAction(val)}>
									<SelectTrigger className="h-9 text-xs">
										<SelectValue placeholder="Select Action" />
									</SelectTrigger>
									<SelectContent>
										<SelectItem value="BLOCK">BLOCK</SelectItem>
										<SelectItem value="ALERT">ALERT</SelectItem>
									</SelectContent>
								</Select>
							</div>
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Description</label>
								<Textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} className="text-xs resize-none h-20" />
							</div>
						</div>
						<DialogFooter className="gap-2 sm:gap-0">
							<Button type="button" variant="outline" size="sm" onClick={() => setEditRule(null)}>
								Cancel
							</Button>
							<Button type="submit" size="sm" className="bg-primary text-primary-foreground">
								Save Changes
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>
		</div>
	);
}
