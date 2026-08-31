import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage } from "@/lib/store";
import RuntimeLimitBanner from "@enterprise/components/views/runtimeLimitBanner";
import {
	useCreateCircuitBreakerPolicyMutation,
	useDeleteCircuitBreakerPolicyMutation,
	useGetCircuitBreakerPoliciesQuery,
	useGetCircuitBreakerStateQuery,
	useResetCircuitBreakerPolicyMutation,
	useUpdateCircuitBreakerPolicyMutation,
} from "@enterprise/lib/store/apis/circuitBreakerApi";
import { CircuitBreakerPolicy } from "@enterprise/lib/types/workspace";
import { Plus, RotateCcw, Shield, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

const emptyPolicy = (): CircuitBreakerPolicy => ({
	name: "",
	enabled: true,
	primary_provider: "",
	primary_model: "",
	fallback_provider: "",
	fallback_model: "",
	condition: { operator: "OR", signals: [{ source: "response_header", header_name: "" }] },
	default_cooldown: "30s",
});

function validatePolicyForm(form: CircuitBreakerPolicy): string | null {
	if (!form.name.trim()) return "Policy name is required";
	if (!form.primary_provider.trim() || !form.primary_model.trim()) {
		return "Primary provider and model are required";
	}
	if (!form.fallback_provider.trim() || !form.fallback_model.trim()) {
		return "Fallback provider and model are required";
	}
	const headerName = form.condition.signals[0]?.header_name?.trim();
	if (!headerName) {
		return "Header name is required — this is the provider response header that trips the circuit";
	}
	return null;
}

export default function CircuitBreakerView() {
	const [open, setOpen] = useState(false);
	const [form, setForm] = useState<CircuitBreakerPolicy>(emptyPolicy());
	const [editing, setEditing] = useState(false);
	const { data: policyData, isLoading: loading } = useGetCircuitBreakerPoliciesQuery();
	const { data: stateData } = useGetCircuitBreakerStateQuery(undefined, { pollingInterval: 8000 });
	const [createPolicy, { isLoading: creating }] = useCreateCircuitBreakerPolicyMutation();
	const [updatePolicy, { isLoading: updating }] = useUpdateCircuitBreakerPolicyMutation();
	const [deletePolicy] = useDeleteCircuitBreakerPolicyMutation();
	const [resetPolicy] = useResetCircuitBreakerPolicyMutation();
	const policies = policyData?.policies || [];
	const states = stateData?.circuits || {};

	const formError = useMemo(() => validatePolicyForm(form), [form]);
	const saving = creating || updating;

	const updatePrimarySignal = useCallback(
		(patch: Partial<CircuitBreakerPolicy["condition"]["signals"][number]>) => {
			setForm((prev) => {
				const current = prev.condition.signals[0] ?? { source: "response_header", header_name: "" };
				return {
					...prev,
					condition: {
						...prev.condition,
						operator: prev.condition.operator || "OR",
						signals: [{ ...current, ...patch, source: "response_header" }],
					},
				};
			});
		},
		[],
	);

	const save = async () => {
		const validationError = validatePolicyForm(form);
		if (validationError) {
			toast.error(validationError);
			return;
		}
		const payload: CircuitBreakerPolicy = {
			...form,
			name: form.name.trim(),
			primary_provider: form.primary_provider.trim(),
			primary_model: form.primary_model.trim(),
			fallback_provider: form.fallback_provider.trim(),
			fallback_model: form.fallback_model.trim(),
			default_cooldown: (form.default_cooldown || "30s").trim(),
			condition: {
				operator: form.condition.operator || "OR",
				signals: [
					{
						source: "response_header",
						header_name: form.condition.signals[0]?.header_name?.trim() || "",
						...(form.condition.signals[0]?.header_value?.trim()
							? { header_value: form.condition.signals[0]?.header_value?.trim() }
							: {}),
						...(form.condition.signals[0]?.header_contains?.trim()
							? { header_contains: form.condition.signals[0]?.header_contains?.trim() }
							: {}),
					},
				],
			},
		};
		try {
			if (editing) {
				await updatePolicy(payload).unwrap();
			} else {
				await createPolicy(payload).unwrap();
			}
			toast.success(editing ? "Policy updated" : "Policy created");
			setOpen(false);
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const remove = async (name: string) => {
		try {
			await deletePolicy(name).unwrap();
			toast.success("Policy deleted");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const reset = async (name: string) => {
		try {
			await resetPolicy(name).unwrap();
			toast.success("Circuit reset");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="flex w-full flex-col gap-6 p-1">
			<RuntimeLimitBanner description="Policies trip on provider response headers and fail over to the configured fallback until cooldown expires." />
			<div className="flex items-center justify-between">
				<div>
					<h1 className="flex items-center gap-2 text-2xl font-semibold">
						<Shield className="h-6 w-6" />
						Circuit Breaker
					</h1>
					<p className="text-muted-foreground mt-1 text-sm">
						Trip a primary provider+model to a fallback when a response header signal matches.
					</p>
				</div>
				<Button
					onClick={() => {
						setForm(emptyPolicy());
						setEditing(false);
						setOpen(true);
					}}
				>
					<Plus className="h-4 w-4" />
					New policy
				</Button>
			</div>

			{loading ? (
				<p className="text-muted-foreground text-sm">Loading policies…</p>
			) : policies.length === 0 ? (
				<div className="rounded-xl border border-dashed p-10 text-center">
					<p className="font-medium">No circuit breaker policies</p>
					<p className="text-muted-foreground mt-1 text-sm">Create a policy to fail over a degraded endpoint.</p>
				</div>
			) : (
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Name</TableHead>
							<TableHead>Primary</TableHead>
							<TableHead>Fallback</TableHead>
							<TableHead>Signal</TableHead>
							<TableHead>State</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{policies.map((policy) => {
							const state = states[policy.name];
							return (
								<TableRow key={policy.name}>
									<TableCell className="font-medium">
										<div className="flex items-center gap-2">
											{policy.name}
											<Badge variant={policy.enabled === false ? "outline" : "secondary"}>
												{policy.enabled === false ? "disabled" : "enabled"}
											</Badge>
										</div>
									</TableCell>
									<TableCell className="font-mono text-xs">
										{policy.primary_provider}/{policy.primary_model}
									</TableCell>
									<TableCell className="font-mono text-xs">
										{policy.fallback_provider}/{policy.fallback_model}
									</TableCell>
									<TableCell className="text-xs">
										{policy.condition.signals
											.map((signal) => {
												if (!signal.header_name) return "—";
												if (signal.header_value) return `${signal.header_name}=${signal.header_value}`;
												return signal.header_name;
											})
											.join(", ")}
									</TableCell>
									<TableCell>
										<Badge variant={state?.status === "open" ? "destructive" : "secondary"}>{state?.status || "closed"}</Badge>
									</TableCell>
									<TableCell className="text-right">
										<Button size="icon" variant="ghost" onClick={() => void reset(policy.name)}>
											<RotateCcw className="h-4 w-4" />
										</Button>
										<Button
											size="icon"
											variant="ghost"
											onClick={() => {
												setForm(policy);
												setEditing(true);
												setOpen(true);
											}}
										>
											<Shield className="h-4 w-4" />
										</Button>
										<Button size="icon" variant="ghost" onClick={() => void remove(policy.name)}>
											<Trash2 className="h-4 w-4" />
										</Button>
									</TableCell>
								</TableRow>
							);
						})}
					</TableBody>
				</Table>
			)}

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent className="max-w-lg">
					<DialogHeader>
						<DialogTitle>{editing ? "Edit policy" : "Create policy"}</DialogTitle>
					</DialogHeader>
					<div className="grid gap-3 py-2">
						<div className="space-y-1">
							<Label>Name</Label>
							<Input disabled={editing} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
						</div>
						<div className="flex items-center justify-between rounded-lg border p-3">
							<Label>Enabled</Label>
							<Switch checked={form.enabled !== false} onCheckedChange={(enabled) => setForm({ ...form, enabled })} />
						</div>
						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1">
								<Label>Primary provider</Label>
								<Input value={form.primary_provider} onChange={(e) => setForm({ ...form, primary_provider: e.target.value })} />
							</div>
							<div className="space-y-1">
								<Label>Primary model</Label>
								<Input value={form.primary_model} onChange={(e) => setForm({ ...form, primary_model: e.target.value })} />
							</div>
							<div className="space-y-1">
								<Label>Fallback provider</Label>
								<Input value={form.fallback_provider} onChange={(e) => setForm({ ...form, fallback_provider: e.target.value })} />
							</div>
							<div className="space-y-1">
								<Label>Fallback model</Label>
								<Input value={form.fallback_model} onChange={(e) => setForm({ ...form, fallback_model: e.target.value })} />
							</div>
						</div>
						<div className="space-y-1">
							<Label>Header name</Label>
							<Input
								placeholder="e.g. x-circuit-breaker or X-Ms-Is-Spilled-Over"
								value={form.condition.signals[0]?.header_name || ""}
								onChange={(e) => updatePrimarySignal({ header_name: e.target.value })}
							/>
							<p className="text-muted-foreground text-xs">
								UnifAI watches this header on the primary provider response. When it matches, traffic fails over to the fallback until cooldown
								expires.
							</p>
						</div>
						<div className="space-y-1">
							<Label>Header value (optional)</Label>
							<Input
								placeholder="Leave empty to trip when the header exists"
								value={form.condition.signals[0]?.header_value || ""}
								onChange={(e) => updatePrimarySignal({ header_value: e.target.value })}
							/>
						</div>
						<div className="space-y-1">
							<Label>Default cooldown</Label>
							<Input value={form.default_cooldown || "30s"} onChange={(e) => setForm({ ...form, default_cooldown: e.target.value })} />
						</div>
						{formError ? <p className="text-destructive text-xs">{formError}</p> : null}
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setOpen(false)}>
							Cancel
						</Button>
						<Button disabled={!!formError || saving} onClick={() => void save()}>
							{saving ? "Saving…" : "Save policy"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
