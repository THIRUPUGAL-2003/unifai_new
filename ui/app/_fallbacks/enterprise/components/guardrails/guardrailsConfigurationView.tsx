import React, { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Plus, Trash, Edit, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import {
	useGetGuardrailsConfigQuery,
	useUpdateGuardrailsConfigMutation,
	GuardrailRule,
} from "@/lib/store/apis/guardrailsApi";
import { getErrorMessage } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { MultiSelect } from "@/components/ui/multiSelect";
import { ModelMultiselect } from "@/components/ui/modelMultiselect";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
	collectGuardrailIds,
	formatLinkedProviders,
	formatRuleModels,
	mergeGuardrailsConfig,
	nextGuardrailId,
	normalizeRuleModels,
	providerLabel,
} from "./utils";

export default function GuardrailsConfigurationView() {
	const { data: config, isLoading, isError, error, refetch } = useGetGuardrailsConfigQuery();
	const [updateConfig, { isLoading: isSaving }] = useUpdateGuardrailsConfigMutation();

	const [isModalOpen, setIsModalOpen] = useState(false);
	const [editingRule, setEditingRule] = useState<Partial<GuardrailRule> | null>(null);

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
	const selectedModels = normalizeRuleModels(editingRule?.models);
	const modelDropdownValue = selectedModels.length === 0 ? ["*"] : selectedModels;

	if (isLoading) return <div className="p-4">Loading guardrails configuration...</div>;

	if (isError) {
		return (
			<div className="flex h-full flex-col items-center justify-center gap-3 p-6">
				<ShieldAlert className="text-destructive h-8 w-8" />
				<p className="text-destructive font-medium">Failed to load guardrail rules</p>
				<p className="text-muted-foreground text-sm">{getErrorMessage(error)}</p>
				<Button variant="outline" onClick={() => refetch()}>
					Retry
				</Button>
			</div>
		);
	}

	const persistConfig = async (patch: { guardrail_rules?: GuardrailRule[] }) => {
		await updateConfig(mergeGuardrailsConfig(config, patch)).unwrap();
	};

	const handleToggleGuardrails = async (checked: boolean) => {
		if (rules.length === 0) {
			toast.error("Create a guardrail rule before enabling guardrails");
			return;
		}
		if (checked) {
			const missingProvider = rules.find((rule) => (rule.provider_config_ids || []).length === 0);
			if (missingProvider) {
				toast.error(`Rule "${missingProvider.name}" must link at least one provider`);
				return;
			}
		}
		try {
			await persistConfig({ guardrail_rules: rules.map((rule) => ({ ...rule, enabled: checked })) });
			toast.success(checked ? "Guardrails enabled" : "Guardrails disabled");
		} catch (err) {
			toast.error(getErrorMessage(err) || "Failed to update guardrails");
		}
	};

	const handleToggleRule = async (rule: GuardrailRule, enabled: boolean) => {
		if (enabled && (rule.provider_config_ids || []).length === 0) {
			toast.error(`Rule "${rule.name}" must link at least one provider`);
			return;
		}
		try {
			await persistConfig({
				guardrail_rules: rules.map((item) => (item.id === rule.id ? { ...item, enabled } : item)),
			});
		} catch (err) {
			toast.error(getErrorMessage(err) || "Failed to update rule");
		}
	};

	const handleDeleteRule = async (ruleId: number) => {
		try {
			await persistConfig({ guardrail_rules: rules.filter((r) => r.id !== ruleId) });
			toast.success("Rule deleted");
		} catch (err) {
			toast.error(getErrorMessage(err) || "Failed to delete rule");
		}
	};

	const handleSaveRule = async () => {
		if (!editingRule || !editingRule.name) return;

		if ((editingRule.provider_config_ids || []).length === 0) {
			toast.error("Select at least one guardrail provider for this rule");
			return;
		}

		const ruleToSave: GuardrailRule = {
			id: editingRule.id || nextGuardrailId(collectGuardrailIds(rules, providers)),
			name: editingRule.name,
			description: editingRule.description || "",
			cel_expression: editingRule.cel_expression?.trim() || "true",
			apply_to: editingRule.apply_to || "input",
			enabled: editingRule.enabled ?? true,
			provider_config_ids: editingRule.provider_config_ids || [],
			models: normalizeRuleModels(editingRule.models),
		};

		let updatedRules = [...rules];
		if (editingRule.id) {
			updatedRules = updatedRules.map((r) => (r.id === editingRule.id ? ruleToSave : r));
		} else {
			updatedRules.push(ruleToSave);
		}

		try {
			await persistConfig({ guardrail_rules: updatedRules });
			toast.success(editingRule.id ? "Rule updated" : "Rule created");
			setIsModalOpen(false);
			setEditingRule(null);
		} catch (err) {
			toast.error(getErrorMessage(err) || "Failed to save rule");
		}
	};

	const openCreateRule = () => {
		if (providers.length === 0) {
			toast.error("Create a guardrail provider before adding rules");
			return;
		}
		setEditingRule({
			apply_to: "input",
			provider_config_ids: [],
			models: ["*"],
			cel_expression: "true",
			enabled: true,
		});
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
						<Tooltip>
							<TooltipTrigger asChild>
								<span>
									<Switch
										id="guardrails-enabled"
										checked={isEnabled}
										disabled={isSaving || rules.length === 0}
										onAsyncCheckedChange={handleToggleGuardrails}
									/>
								</span>
							</TooltipTrigger>
							{rules.length === 0 && <TooltipContent>Create a rule before enabling guardrails</TooltipContent>}
						</Tooltip>
						<Label htmlFor="guardrails-enabled" className="font-medium">
							Enable Guardrails
						</Label>
					</div>
					<Button onClick={openCreateRule} disabled={isSaving} data-testid="guardrails-create-rule-button">
						<Plus className="mr-2 h-4 w-4" />
						Create Rule
					</Button>
				</div>
			</div>

			<div className="bg-card rounded-md border">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead className="w-[90px]">Enabled</TableHead>
							<TableHead>Rule Name</TableHead>
							<TableHead>Description</TableHead>
							<TableHead>Apply To</TableHead>
							<TableHead>Models</TableHead>
							<TableHead>Providers</TableHead>
							<TableHead>Expression</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{rules.length === 0 ? (
							<TableRow>
								<TableCell colSpan={8} className="text-muted-foreground h-32 text-center">
									<div className="flex flex-col items-center justify-center gap-1">
										<ShieldAlert className="text-muted-foreground/50 mb-2 h-8 w-8" />
										<p>No guardrail rules configured yet.</p>
										{providers.length === 0 ? (
											<p className="text-sm">
												<Link to="/workspace/guardrails/providers" className="text-primary underline">
													Create a provider
												</Link>{" "}
												first, then add a rule.
											</p>
										) : (
											<p className="text-sm">Click Create Rule to inspect prompts and responses.</p>
										)}
									</div>
								</TableCell>
							</TableRow>
						) : (
							rules.map((rule) => (
								<TableRow key={rule.id}>
									<TableCell>
										<Switch
											checked={rule.enabled}
											disabled={isSaving}
											onAsyncCheckedChange={(checked) => handleToggleRule(rule, checked)}
										/>
									</TableCell>
									<TableCell className="font-medium">{rule.name}</TableCell>
									<TableCell>{rule.description}</TableCell>
									<TableCell className="capitalize">{rule.apply_to}</TableCell>
									<TableCell>{formatRuleModels(rule)}</TableCell>
									<TableCell>{formatLinkedProviders(rule, providers)}</TableCell>
									<TableCell className="max-w-[300px] truncate font-mono text-xs">{rule.cel_expression}</TableCell>
									<TableCell className="text-right">
										<Button
											variant="ghost"
											size="icon"
											disabled={isSaving}
											onClick={() => {
												setEditingRule({ ...rule, models: normalizeRuleModels(rule.models) });
												setIsModalOpen(true);
											}}
										>
											<Edit className="h-4 w-4" />
										</Button>
										<Button variant="ghost" size="icon" disabled={isSaving} onClick={() => handleDeleteRule(rule.id)}>
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
				<DialogContent className="sm:max-w-[640px]">
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
							<Label>Models</Label>
							<ModelMultiselect
								value={modelDropdownValue}
								onChange={(models) => setEditingRule({ ...editingRule, models: normalizeRuleModels(models) })}
								placeholder="All models"
								loadModelsOnEmptyProvider
								allowAllOption
								unfiltered
								menuPosition="absolute"
								className="!min-h-9"
								data-testid="guardrails-rule-models-select"
							/>
							<p className="text-muted-foreground text-xs">
								Leave as All models to scan every request, or pick specific catalog models.
							</p>
						</div>
						<div className="grid gap-2">
							<Label>Providers</Label>
							{providerOptions.length === 0 ? (
								<p className="text-muted-foreground text-sm">
									<Link to="/workspace/guardrails/providers" className="text-primary underline">
										Create a guardrail provider
									</Link>{" "}
									before adding rules.
								</p>
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
								Selected providers scan the prompt or response when the rule matches the selected models.
							</p>
						</div>
						<div className="grid gap-2">
							<Label htmlFor="expression">CEL Expression</Label>
							<Textarea
								id="expression"
								value={editingRule?.cel_expression || ""}
								onChange={(e) => setEditingRule({ ...editingRule, cel_expression: e.target.value })}
								placeholder="true"
								className="font-mono text-sm"
								rows={3}
								data-testid="guardrails-rule-expression-input"
							/>
							<p className="text-muted-foreground text-xs">
								Optional extra filter. Model targeting uses the dropdown above. Use <code>true</code> to run on every
								selected model.
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
								isSaving ||
								!editingRule?.name ||
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
