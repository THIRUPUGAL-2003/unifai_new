import React, { useMemo, useState } from "react";
import { Plus, Trash, Edit, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import {
	useGetGuardrailsConfigQuery,
	useUpdateGuardrailsConfigMutation,
	GuardrailRule,
} from "@/lib/store/apis/guardrailsApi";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { MultiSelect } from "@/components/ui/multiSelect";
import { collectGuardrailIds, formatLinkedProviders, nextGuardrailId, providerLabel } from "./utils";

export default function GuardrailsConfigurationView() {
	const { data: config, isLoading } = useGetGuardrailsConfigQuery();
	const [updateConfig] = useUpdateGuardrailsConfigMutation();

	const [isModalOpen, setIsModalOpen] = useState(false);
	const [editingRule, setEditingRule] = useState<Partial<GuardrailRule> | null>(null);

	if (isLoading) return <div className="p-4">Loading guardrails configuration...</div>;

	const rules = config?.guardrail_rules || [];
	const providers = config?.guardrail_providers || [];
	const isEnabled = rules.length > 0 && rules.some((r) => r.enabled);

	const providerOptions = useMemo(
		() =>
			providers.map((provider) => ({
				label: providerLabel(provider),
				value: String(provider.id),
			})),
		[providers],
	);

	const selectedProviderIds = (editingRule?.provider_config_ids || []).map(String);

	const handleToggleGuardrails = async (checked: boolean) => {
		if (!config) return;
		const updatedRules = rules.map((r) => ({ ...r, enabled: checked }));
		try {
			await updateConfig({ ...config, guardrail_rules: updatedRules }).unwrap();
			toast.success(checked ? "Guardrails enabled" : "Guardrails disabled");
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Failed to update guardrails");
		}
	};

	const handleDeleteRule = async (ruleId: number) => {
		if (!config) return;
		const updatedRules = rules.filter((r) => r.id !== ruleId);
		try {
			await updateConfig({ ...config, guardrail_rules: updatedRules }).unwrap();
			toast.success("Rule deleted");
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Failed to delete rule");
		}
	};

	const handleSaveRule = async () => {
		if (!config || !editingRule || !editingRule.name || !editingRule.cel_expression) return;

		if ((editingRule.provider_config_ids || []).length === 0) {
			toast.error("Select at least one guardrail provider for this rule");
			return;
		}

		let updatedRules = [...rules];
		if (editingRule.id) {
			updatedRules = updatedRules.map((r) => (r.id === editingRule.id ? (editingRule as GuardrailRule) : r));
		} else {
			updatedRules.push({
				...editingRule,
				id: nextGuardrailId(collectGuardrailIds(rules, providers)),
				provider_config_ids: editingRule.provider_config_ids || [],
				enabled: true,
			} as GuardrailRule);
		}

		try {
			await updateConfig({ ...config, guardrail_rules: updatedRules }).unwrap();
			toast.success(editingRule.id ? "Rule updated" : "Rule created");
			setIsModalOpen(false);
			setEditingRule(null);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Failed to save rule");
		}
	};

	const openCreateRule = () => {
		setEditingRule({ apply_to: "input", provider_config_ids: [], enabled: true });
		setIsModalOpen(true);
	};

	return (
		<div className="flex h-full flex-col gap-6 p-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold tracking-tight">Guardrails Rules</h1>
					<p className="text-muted-foreground mt-1">Configure global rules to inspect AI prompts and responses.</p>
				</div>
				<div className="flex items-center gap-4">
					<div className="flex items-center gap-2">
						<Switch id="guardrails-enabled" checked={isEnabled} onCheckedChange={handleToggleGuardrails} />
						<Label htmlFor="guardrails-enabled" className="font-medium">
							Enable Guardrails
						</Label>
					</div>
					<Button onClick={openCreateRule} data-testid="guardrails-create-rule-button">
						<Plus className="mr-2 h-4 w-4" />
						Create Rule
					</Button>
				</div>
			</div>

			<div className="bg-card rounded-md border">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Rule Name</TableHead>
							<TableHead>Description</TableHead>
							<TableHead>Apply To</TableHead>
							<TableHead>Providers</TableHead>
							<TableHead>Expression</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{rules.length === 0 ? (
							<TableRow>
								<TableCell colSpan={6} className="text-muted-foreground h-32 text-center">
									<div className="flex flex-col items-center justify-center">
										<ShieldAlert className="text-muted-foreground/50 mb-2 h-8 w-8" />
										<p>No guardrail rules configured yet.</p>
									</div>
								</TableCell>
							</TableRow>
						) : (
							rules.map((rule) => (
								<TableRow key={rule.id}>
									<TableCell className="font-medium">{rule.name}</TableCell>
									<TableCell>{rule.description}</TableCell>
									<TableCell className="capitalize">{rule.apply_to}</TableCell>
									<TableCell>{formatLinkedProviders(rule, providers)}</TableCell>
									<TableCell className="max-w-[300px] truncate font-mono text-xs">{rule.cel_expression}</TableCell>
									<TableCell className="text-right">
										<Button
											variant="ghost"
											size="icon"
											onClick={() => {
												setEditingRule(rule);
												setIsModalOpen(true);
											}}
										>
											<Edit className="h-4 w-4" />
										</Button>
										<Button variant="ghost" size="icon" onClick={() => handleDeleteRule(rule.id)}>
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
				<DialogContent className="sm:max-w-[560px]">
					<DialogHeader>
						<DialogTitle>{editingRule?.id ? "Edit Rule" : "Create Rule"}</DialogTitle>
					</DialogHeader>
					<div className="grid gap-4 py-4">
						<div className="grid gap-2">
							<Label htmlFor="name">Rule Name</Label>
							<Input
								id="name"
								value={editingRule?.name || ""}
								onChange={(e) => setEditingRule({ ...editingRule, name: e.target.value })}
								placeholder="e.g. Block PII"
								data-testid="guardrails-rule-name-input"
							/>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="description">Description</Label>
							<Input
								id="description"
								value={editingRule?.description || ""}
								onChange={(e) => setEditingRule({ ...editingRule, description: e.target.value })}
								placeholder="e.g. Blocks sensitive information"
							/>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="apply_to">Apply To</Label>
							<Select
								value={editingRule?.apply_to || "input"}
								onValueChange={(val: "input" | "output" | "both") => setEditingRule({ ...editingRule, apply_to: val })}
							>
								<SelectTrigger data-testid="guardrails-rule-apply-to-select">
									<SelectValue placeholder="Select target phase" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="input">Input (Prompt)</SelectItem>
									<SelectItem value="output">Output (Response)</SelectItem>
									<SelectItem value="both">Both</SelectItem>
								</SelectContent>
							</Select>
						</div>
						<div className="grid gap-2">
							<Label>Providers</Label>
							{providerOptions.length === 0 ? (
								<p className="text-muted-foreground text-sm">Create a guardrail provider before adding rules.</p>
							) : (
								<MultiSelect
									options={providerOptions}
									defaultValue={selectedProviderIds}
									resetOnDefaultValueChange
									onValueChange={(values) =>
										setEditingRule({
											...editingRule,
											provider_config_ids: values.map((value) => Number.parseInt(value, 10)).filter(Number.isFinite),
										})
									}
									placeholder="Select providers to run when this rule matches"
									emptyIndicator="No guardrail providers configured."
									maxCount={2}
									className="border-input text-foreground hover:bg-accent hover:text-accent-foreground h-9 rounded-sm bg-transparent font-normal"
									popoverClassName="w-[var(--radix-popover-trigger-width)]"
									data-testid="guardrails-rule-providers-select"
								/>
							)}
							<p className="text-muted-foreground text-xs">
								Selected providers scan the prompt or response when the CEL expression matches.
							</p>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="expression">CEL Expression</Label>
							<Textarea
								id="expression"
								value={editingRule?.cel_expression || ""}
								onChange={(e) => setEditingRule({ ...editingRule, cel_expression: e.target.value })}
								placeholder="e.g. request.model == 'gpt-4' or true"
								className="font-mono text-sm"
								rows={4}
								data-testid="guardrails-rule-expression-input"
							/>
							<p className="text-muted-foreground text-xs">
								Use CEL to define when this rule runs. Use <code>true</code> to apply on every request for the selected model path.
							</p>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setIsModalOpen(false)}>
							Cancel
						</Button>
						<Button
							onClick={handleSaveRule}
							disabled={
								!editingRule?.name ||
								!editingRule?.cel_expression ||
								(editingRule.provider_config_ids || []).length === 0 ||
								providerOptions.length === 0
							}
							data-testid="guardrails-rule-save-button"
						>
							Save Rule
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
