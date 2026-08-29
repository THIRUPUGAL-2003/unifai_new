import React, { useState } from "react";
import { Plus, Trash, Edit, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import {
	useGetGuardrailsConfigQuery,
	useUpdateGuardrailsConfigMutation,
	GuardrailProvider,
} from "@/lib/store/apis/guardrailsApi";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { collectGuardrailIds, nextGuardrailId } from "./utils";

export default function GuardrailsProviderView() {
	const { data: config, isLoading } = useGetGuardrailsConfigQuery();
	const [updateConfig] = useUpdateGuardrailsConfigMutation();

	const [isModalOpen, setIsModalOpen] = useState(false);
	const [editingProvider, setEditingProvider] = useState<Partial<GuardrailProvider> | null>(null);

	if (isLoading) return <div className="p-4">Loading providers...</div>;

	const providers = config?.guardrail_providers || [];
	const rules = config?.guardrail_rules || [];

	const handleDeleteProvider = async (providerId: number) => {
		if (!config) return;

		const linkedRule = rules.find((rule) => (rule.provider_config_ids || []).includes(providerId));
		if (linkedRule) {
			toast.error(`Provider is linked to rule "${linkedRule.name}". Remove it from the rule first.`);
			return;
		}

		const updatedProviders = providers.filter((p) => p.id !== providerId);
		try {
			await updateConfig({ ...config, guardrail_providers: updatedProviders }).unwrap();
			toast.success("Provider deleted");
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Failed to delete provider");
		}
	};

	const handleSaveProvider = async () => {
		if (!config || !editingProvider || !editingProvider.policy_name || !editingProvider.id) return;

		const patternText = getRegexPatterns(editingProvider);
		if (!patternText.trim()) {
			toast.error("Add at least one regex pattern");
			return;
		}

		const providerToSave: GuardrailProvider = {
			id: editingProvider.id,
			provider_name: "regex",
			policy_name: editingProvider.policy_name,
			enabled: editingProvider.enabled ?? true,
			config: editingProvider.config || { patterns: [] },
		};

		let updatedProviders = [...providers];
		const existingIndex = updatedProviders.findIndex((p) => p.id === providerToSave.id);

		if (existingIndex >= 0) {
			updatedProviders[existingIndex] = providerToSave;
		} else {
			updatedProviders.push(providerToSave);
		}

		try {
			await updateConfig({ ...config, guardrail_providers: updatedProviders }).unwrap();
			toast.success(existingIndex >= 0 ? "Provider updated" : "Provider created");
			setIsModalOpen(false);
			setEditingProvider(null);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Failed to save provider");
		}
	};

	const getRegexPatterns = (provider: Partial<GuardrailProvider>) => {
		const raw = provider.config?.patterns;
		if (!Array.isArray(raw)) return "";
		return raw
			.map((item) => {
				if (typeof item === "string") return item;
				if (item && typeof item === "object" && "pattern" in item) {
					return String((item as { pattern?: string }).pattern || "");
				}
				return "";
			})
			.filter((p) => p.trim() !== "")
			.join("\n");
	};

	const setRegexPatterns = (val: string) => {
		const patterns = val
			.split("\n")
			.map((p) => p.trim())
			.filter((p) => p !== "")
			.map((pattern) => ({ pattern, description: pattern, flags: "i" }));
		setEditingProvider((prev) => ({
			...prev,
			config: { ...(prev?.config || {}), patterns },
		}));
	};

	const openCreateProvider = () => {
		const nextId = nextGuardrailId(collectGuardrailIds(rules, providers));
		setEditingProvider({
			id: nextId,
			provider_name: "regex",
			policy_name: "",
			enabled: true,
			config: { patterns: [] },
		});
		setIsModalOpen(true);
	};

	const isEditingExisting = editingProvider?.id != null && providers.some((provider) => provider.id === editingProvider.id);

	return (
		<div className="flex h-full flex-col gap-6 p-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold tracking-tight">Guardrail Providers</h1>
					<p className="text-muted-foreground mt-1">Configure backend providers like Regex matchers to evaluate rules.</p>
				</div>
				<Button onClick={openCreateProvider} data-testid="guardrails-create-provider-button">
					<Plus className="mr-2 h-4 w-4" />
					Create Provider
				</Button>
			</div>

			<div className="bg-card rounded-md border">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Provider ID</TableHead>
							<TableHead>Type</TableHead>
							<TableHead>Policy Name</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{providers.length === 0 ? (
							<TableRow>
								<TableCell colSpan={4} className="text-muted-foreground h-32 text-center">
									<div className="flex flex-col items-center justify-center">
										<ShieldAlert className="text-muted-foreground/50 mb-2 h-8 w-8" />
										<p>No guardrail providers configured yet.</p>
									</div>
								</TableCell>
							</TableRow>
						) : (
							providers.map((provider) => (
								<TableRow key={provider.id}>
									<TableCell className="font-mono text-sm font-medium">{provider.id}</TableCell>
									<TableCell className="capitalize">{provider.provider_name}</TableCell>
									<TableCell>{provider.policy_name}</TableCell>
									<TableCell className="text-right">
										<Button
											variant="ghost"
											size="icon"
											onClick={() => {
												setEditingProvider(provider);
												setIsModalOpen(true);
											}}
										>
											<Edit className="h-4 w-4" />
										</Button>
										<Button variant="ghost" size="icon" onClick={() => handleDeleteProvider(provider.id)}>
											<Trash className="text-destructive h-4 w-4" />
										</Button>
									</TableCell>
								</TableRow>
							))
						)}
					</TableBody>
				</Table>
			</div>

			<Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
				<DialogContent className="sm:max-w-[500px]">
					<DialogHeader>
						<DialogTitle>{isEditingExisting ? "Edit Provider" : "Create Provider"}</DialogTitle>
					</DialogHeader>
					<div className="grid gap-4 py-4">
						<div className="grid gap-2">
							<Label htmlFor="id">Provider ID</Label>
							<Input id="id" value={editingProvider?.id ?? ""} disabled className="font-mono" />
							<p className="text-muted-foreground text-xs">Auto-generated ID used when linking providers to rules.</p>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="policy_name">Policy Name</Label>
							<Input
								id="policy_name"
								value={editingProvider?.policy_name || ""}
								onChange={(e) => setEditingProvider({ ...editingProvider, policy_name: e.target.value })}
								placeholder="e.g. PAN Regex Matcher"
								data-testid="guardrails-provider-policy-name-input"
							/>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="provider_name">Type</Label>
							<Input id="provider_name" value="regex" disabled />
						</div>
						<div className="grid gap-2">
							<Label htmlFor="patterns">Regex Patterns (One per line)</Label>
							<Textarea
								id="patterns"
								value={getRegexPatterns(editingProvider || {})}
								onChange={(e) => setRegexPatterns(e.target.value)}
								placeholder="[A-Z]{5}[0-9]{4}[A-Z]"
								className="font-mono text-sm"
								rows={4}
								data-testid="guardrails-provider-patterns-input"
							/>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setIsModalOpen(false)}>
							Cancel
						</Button>
						<Button
							onClick={handleSaveProvider}
							disabled={!editingProvider?.id || !editingProvider?.policy_name}
							data-testid="guardrails-provider-save-button"
						>
							Save Provider
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
