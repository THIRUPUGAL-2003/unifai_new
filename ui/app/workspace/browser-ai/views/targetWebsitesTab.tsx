import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Globe, ExternalLink, Plus, Target, Pencil, Trash2 } from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

export interface TargetDomain {
	id: string;
	domain: string;
	platform: string;
	status: "MONITORED" | "PAUSED";
	interceptedCount: number;
}

export const initialTargetDomains: TargetDomain[] = [];

export function TargetWebsitesTab() {
	const [domains, setDomains] = useState<TargetDomain[]>(initialTargetDomains);
	const [isAddOpen, setIsAddOpen] = useState(false);
	const [editTarget, setEditTarget] = useState<TargetDomain | null>(null);

	// Form State
	const [newDomain, setNewDomain] = useState("");
	const [newPlatform, setNewPlatform] = useState("");

	// Edit Form State
	const [editDomain, setEditDomain] = useState("");
	const [editPlatform, setEditPlatform] = useState("");

	// Load target domains from backend DB API
	useEffect(() => {
		const loadTargets = async () => {
			try {
				const res = await fetch(`/api/browser-ai/targets?t=${Date.now()}`);
				if (res.ok) {
					const data = await res.json();
					if (data && Array.isArray(data.targets)) {
						const formatted: TargetDomain[] = data.targets.map((t: any) => ({
							id: t.id,
							domain: t.domain || "",
							platform: t.platform_name || t.platform || "AI Platform",
							status: t.status === "MONITORED" || t.monitored ? "MONITORED" : "PAUSED",
							interceptedCount: t.intercepted_count || 0,
						}));
						setDomains(formatted);
					}
				}
			} catch (e) {
				// Ignore fetch error, fallback to initial state
			}
		};
		loadTargets();
	}, []);

	const toggleDomain = async (id: string) => {
		const target = domains.find((d) => d.id === id);
		if (!target) return;
		const nextStatus = target.status === "MONITORED" ? "PAUSED" : "MONITORED";

		setDomains((prev) =>
			prev.map((d) => (d.id === id ? { ...d, status: nextStatus } : d))
		);

		try {
			await fetch(`/api/browser-ai/targets/${id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ status: nextStatus, monitored: nextStatus === "MONITORED" }),
			});
		} catch (e) {
			// Ignore update error
		}
	};

	const handleAddDomain = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!newDomain.trim()) return;

		let cleanDomain = newDomain.trim().toLowerCase();
		cleanDomain = cleanDomain.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
		const platformName = newPlatform.trim() || "Custom AI Platform";

		const createdDomain: TargetDomain = {
			id: `tgt-${Date.now()}`,
			domain: cleanDomain,
			platform: platformName,
			status: "MONITORED",
			interceptedCount: 0,
		};

		setDomains([createdDomain, ...domains]);
		setNewDomain("");
		setNewPlatform("");
		setIsAddOpen(false);

		try {
			await fetch(`/api/browser-ai/targets`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					id: createdDomain.id,
					domain: cleanDomain,
					platform_name: platformName,
					status: "MONITORED",
					monitored: true,
				}),
			});
		} catch (e) {
			// Ignore create error
		}
	};

	const handleEditDomain = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!editTarget || !editDomain.trim()) return;

		let cleanDomain = editDomain.trim().toLowerCase();
		cleanDomain = cleanDomain.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
		const platformName = editPlatform.trim() || "Custom AI Platform";

		setDomains((prev) =>
			prev.map((d) => (d.id === editTarget.id ? { ...d, domain: cleanDomain, platform: platformName } : d))
		);

		const targetId = editTarget.id;
		setEditTarget(null);

		try {
			await fetch(`/api/browser-ai/targets/${targetId}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ domain: cleanDomain, platform_name: platformName }),
			});
		} catch (e) {
			// Ignore update error
		}
	};

	const handleDeleteDomain = async (id: string) => {
		setDomains((prev) => prev.filter((d) => d.id !== id));
		try {
			await fetch(`/api/browser-ai/targets/${id}`, { method: "DELETE" });
		} catch (e) {
			// Ignore delete error
		}
	};

	return (
		<div className="space-y-4">
			<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card p-4 rounded-lg border">
				<div>
					<h3 className="text-base font-semibold tracking-tight">
						Target Web AI Platforms ({domains.filter((d) => d.status === "MONITORED").length} Monitored)
					</h3>
					<p className="text-xs text-muted-foreground">Browser domains automatically intercepted by HTTPS SSL Proxy</p>
				</div>
				<Button
					size="sm"
					onClick={() => setIsAddOpen(true)}
					className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground"
				>
					<Plus className="w-3.5 h-3.5" /> Add Target Domain
				</Button>
			</div>

			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{domains.map((item) => (
					<div
						key={item.id}
						className="p-4 rounded-lg border bg-card hover:border-primary/40 transition-colors flex flex-col justify-between gap-3 group relative"
					>
						<div className="flex items-start justify-between">
							<div className="flex items-center gap-2">
								<div className="p-2 rounded-md bg-muted text-primary">
									<Globe className="w-4 h-4" />
								</div>
								<div>
									<h4 className="font-semibold text-sm flex items-center gap-1.5">
										{item.domain}
										<a
											href={`https://${item.domain}`}
											target="_blank"
											rel="noreferrer"
											className="text-muted-foreground hover:text-primary"
										>
											<ExternalLink className="w-3 h-3" />
										</a>
									</h4>
									<p className="text-xs text-muted-foreground">{item.platform}</p>
								</div>
							</div>
							<div className="flex items-center gap-1">
								<Badge
									variant="outline"
									className={
										item.status === "MONITORED"
											? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-[10px]"
											: "bg-muted text-muted-foreground text-[10px]"
									}
								>
									{item.status}
								</Badge>
							</div>
						</div>

						<div className="flex items-center justify-between pt-2 border-t text-xs">
							<span className="text-muted-foreground">Intercepted Prompts</span>
							<span className="font-mono font-medium">{item.interceptedCount} requests</span>
						</div>

						<div className="flex items-center justify-between pt-1">
							<div className="flex items-center gap-1">
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 text-muted-foreground hover:text-foreground"
									title="Edit Domain"
									onClick={() => {
										setEditTarget(item);
										setEditDomain(item.domain);
										setEditPlatform(item.platform);
									}}
								>
									<Pencil className="w-3.5 h-3.5" />
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 text-muted-foreground hover:text-red-400"
									title="Delete Target Domain"
									onClick={() => handleDeleteDomain(item.id)}
								>
									<Trash2 className="w-3.5 h-3.5" />
								</Button>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-xs text-muted-foreground font-medium">Monitoring</span>
								<Switch checked={item.status === "MONITORED"} onCheckedChange={() => toggleDomain(item.id)} />
							</div>
						</div>
					</div>
				))}
			</div>

			{/* Add Target Domain Modal */}
			<Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
				<DialogContent className="sm:max-w-md bg-card">
					<form onSubmit={handleAddDomain}>
						<DialogHeader>
							<DialogTitle className="flex items-center gap-2">
								<Target className="w-5 h-5 text-primary" />
								Add New Target Domain
							</DialogTitle>
							<DialogDescription className="text-xs">
								Add a web AI platform domain to automatically monitor and intercept browser prompts.
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4 text-xs">
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Domain Name</label>
								<Input
									placeholder="e.g. groq.com or hf.co"
									value={newDomain}
									onChange={(e) => setNewDomain(e.target.value)}
									required
									className="text-xs h-9"
								/>
							</div>

							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Platform / Service Name</label>
								<Input
									placeholder="e.g. Groq AI Platform"
									value={newPlatform}
									onChange={(e) => setNewPlatform(e.target.value)}
									className="text-xs h-9"
								/>
							</div>
						</div>

						<DialogFooter className="gap-2 sm:gap-0">
							<Button type="button" variant="outline" size="sm" onClick={() => setIsAddOpen(false)}>
								Cancel
							</Button>
							<Button type="submit" size="sm" className="bg-primary text-primary-foreground">
								Add Domain
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>

			{/* Edit Target Domain Modal */}
			<Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
				<DialogContent className="sm:max-w-md bg-card">
					<form onSubmit={handleEditDomain}>
						<DialogHeader>
							<DialogTitle className="flex items-center gap-2">
								<Pencil className="w-5 h-5 text-primary" />
								Edit Target Domain
							</DialogTitle>
							<DialogDescription className="text-xs">
								Update domain details for browser prompt interception.
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4 text-xs">
							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Domain Name</label>
								<Input
									value={editDomain}
									onChange={(e) => setEditDomain(e.target.value)}
									required
									className="text-xs h-9"
								/>
							</div>

							<div className="space-y-1.5">
								<label className="font-semibold text-muted-foreground">Platform / Service Name</label>
								<Input
									value={editPlatform}
									onChange={(e) => setEditPlatform(e.target.value)}
									className="text-xs h-9"
								/>
							</div>
						</div>

						<DialogFooter className="gap-2 sm:gap-0">
							<Button type="button" variant="outline" size="sm" onClick={() => setEditTarget(null)}>
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
