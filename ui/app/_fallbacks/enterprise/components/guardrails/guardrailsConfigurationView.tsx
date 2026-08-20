import React, { useState } from "react";
import { Plus, Trash, Edit, ShieldAlert } from "lucide-react";
import { useGetGuardrailsConfigQuery, useUpdateGuardrailsConfigMutation, GuardrailRule } from "@/lib/store/apis/guardrailsApi";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export default function GuardrailsConfigurationView() {
	const { data: config, isLoading } = useGetGuardrailsConfigQuery();
	const [updateConfig] = useUpdateGuardrailsConfigMutation();

	const [isModalOpen, setIsModalOpen] = useState(false);
	const [editingRule, setEditingRule] = useState<Partial<GuardrailRule> | null>(null);

	if (isLoading) return <div className="p-4">Loading guardrails configuration...</div>;

	const rules = config?.guardrail_rules || [];
	const isEnabled = rules.length > 0 && rules.some((r) => r.enabled);

	const handleToggleGuardrails = async (checked: boolean) => {
		if (!config) return;
		const updatedRules = rules.map((r) => ({ ...r, enabled: checked }));
		await updateConfig({ ...config, guardrail_rules: updatedRules });
	};

	const handleDeleteRule = async (ruleId: number) => {
		if (!config) return;
		const updatedRules = rules.filter((r) => r.id !== ruleId);
		await updateConfig({ ...config, guardrail_rules: updatedRules });
	};

	const handleSaveRule = async () => {
		if (!config || !editingRule || !editingRule.name || !editingRule.cel_expression) return;

		let updatedRules = [...rules];
		if (editingRule.id) {
			updatedRules = updatedRules.map((r) => (r.id === editingRule.id ? (editingRule as GuardrailRule) : r));
		} else {
			updatedRules.push({
				...editingRule,
				id: Math.floor(Math.random() * 100000), // Generate a random int ID
				provider_config_ids: editingRule.provider_config_ids || [],
				enabled: true,
			} as GuardrailRule);
		}

		await updateConfig({ ...config, guardrail_rules: updatedRules });
		setIsModalOpen(false);
		setEditingRule(null);
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
					<Button
						onClick={() => {
							setEditingRule({ apply_to: "input", provider_config_ids: [] });
							setIsModalOpen(true);
						}}
					>
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
							<TableHead>Expression</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{rules.length === 0 ? (
							<TableRow>
								<TableCell colSpan={5} className="text-muted-foreground h-32 text-center">
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
				<DialogContent className="sm:max-w-[500px]">
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
								<SelectTrigger>
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
							<Label htmlFor="expression">CEL Expression</Label>
							<Textarea
								id="expression"
								value={editingRule?.cel_expression || ""}
								onChange={(e) => setEditingRule({ ...editingRule, cel_expression: e.target.value })}
								placeholder="e.g. request.model == 'gpt-4'"
								className="font-mono text-sm"
								rows={4}
							/>
							<p className="text-muted-foreground text-xs">
								Use Common Expression Language (CEL) to define when this rule runs. (e.g., `request.model == 'gpt-4'`)
							</p>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setIsModalOpen(false)}>
							Cancel
						</Button>
						<Button onClick={handleSaveRule} disabled={!editingRule?.name || !editingRule?.cel_expression}>
							Save Rule
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}