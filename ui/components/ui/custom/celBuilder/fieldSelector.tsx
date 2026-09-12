/**
 * Field Selector Component for CEL Rule Builder
 * Allows selection of fields for building CEL expressions
 * For keyValue fields (headers/params), renders a smart searchable Combobox
 * with pre-filled suggestions and creatable custom inputs, plus a manual input toggle.
 */

import { Button } from "@/components/ui/button";
import { ComboboxSelect, ComboboxSelectOption } from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useGetCoreConfigQuery } from "@/lib/store/apis/configApi";
import { ListFilter, PenLine } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { FieldSelectorProps, RuleGroupType, RuleType } from "react-querybuilder";

// Popular pre-configured Header suggestions
const COMMON_HEADER_SUGGESTIONS: ComboboxSelectOption[] = [
	// Rate Limit & Quota Headers
	{ label: "x-ratelimit-remaining-requests (Remaining Calls)", value: "x-ratelimit-remaining-requests" },
	{ label: "x-ratelimit-remaining-tokens (Remaining Tokens)", value: "x-ratelimit-remaining-tokens" },
	{ label: "x-ratelimit-limit-requests (RPM Limit)", value: "x-ratelimit-limit-requests" },
	{ label: "x-ratelimit-limit-tokens (TPM Limit)", value: "x-ratelimit-limit-tokens" },
	{ label: "x-ratelimit-reset-requests (Reset Duration)", value: "x-ratelimit-reset-requests" },
	{ label: "x-ratelimit-reset-tokens (Token Reset Duration)", value: "x-ratelimit-reset-tokens" },
	{ label: "retry-after (Rate Limit Retry Seconds)", value: "retry-after" },

	// Gateway & Auth Headers
	{ label: "authorization (Bearer Token / Virtual Key)", value: "authorization" },
	{ label: "x-uf-vk (Virtual Key Header)", value: "x-uf-vk" },
	{ label: "x-uf-api-key-id (Specific Key Pinning)", value: "x-uf-api-key-id" },
	{ label: "x-api-key (API Key)", value: "x-api-key" },
	{ label: "x-environment (dev / staging / prod)", value: "x-environment" },
	{ label: "x-team-id (Team ID)", value: "x-team-id" },
	{ label: "x-customer-id (Customer ID)", value: "x-customer-id" },
	{ label: "x-user-id (User ID)", value: "x-user-id" },
	{ label: "x-purpose (Purpose / Use-case Tag)", value: "x-purpose" },
];

// Popular pre-configured Query Parameter suggestions
const COMMON_PARAM_SUGGESTIONS: ComboboxSelectOption[] = [
	{ label: "env (Environment - staging / prod)", value: "env" },
	{ label: "environment (Environment)", value: "environment" },
	{ label: "tier (User Tier - free / pro / vip)", value: "tier" },
	{ label: "user_tier (User Tier)", value: "user_tier" },
	{ label: "region (Region - us / eu / apac)", value: "region" },
	{ label: "customer_id (Customer ID)", value: "customer_id" },
	{ label: "user_id (User ID)", value: "user_id" },
	{ label: "team_id (Team ID)", value: "team_id" },
	{ label: "version (API Version)", value: "version" },
	{ label: "model (Requested Model)", value: "model" },
	{ label: "stream (Streaming Flag)", value: "stream" },
	{ label: "debug (Debug Mode)", value: "debug" },
];

/**
 * Recursively find and update a rule's value by path in the query tree.
 */
function updateRuleValueAtPath(query: RuleGroupType, targetPath: number[], newValue: string): RuleGroupType {
	if (targetPath.length === 0) return query;

	const [currentIndex, ...restPath] = targetPath;
	const newRules = [...query.rules];

	if (restPath.length === 0) {
		// We're at the target rule
		const rule = newRules[currentIndex] as RuleType;
		newRules[currentIndex] = { ...rule, value: newValue };
	} else {
		// Recurse into nested group
		newRules[currentIndex] = updateRuleValueAtPath(newRules[currentIndex] as RuleGroupType, restPath, newValue);
	}

	return { ...query, rules: newRules };
}

export function FieldSelector({ value, handleOnChange, options, rule, path, schema }: FieldSelectorProps) {
	// Toggle between searchable combobox and manual input
	const [isManualInput, setIsManualInput] = useState(false);

	// Check if this is a keyValue field (headers/params)
	const fieldData = useMemo(() => (schema?.fields?.find((f) => "value" in f && f.value === value) as any) ?? null, [schema?.fields, value]);
	const isKeyValueField = Boolean(fieldData && fieldData.inputType === "keyValue");

	const isHeaderField = fieldData?.name === "headers" || value === "headers";
	const isParamField = fieldData?.name === "params" || value === "params";

	// Dynamically include organization-configured headers from CoreConfig
	const { data: coreConfig } = useGetCoreConfigQuery({});

	const headerOptions = useMemo(() => {
		const rawReq = coreConfig?.client_config?.required_headers || [];
		const rawLog = coreConfig?.client_config?.logging_headers || [];
		const configured = Array.from(new Set([...rawReq, ...rawLog].map((h) => String(h).trim().toLowerCase()))).filter(Boolean);

		const existingKeys = new Set(COMMON_HEADER_SUGGESTIONS.map((s) => s.value));
		const customConfiguredOptions: ComboboxSelectOption[] = configured
			.filter((key) => !existingKeys.has(key))
			.map((key) => ({
				label: `${key} (Configured Header)`,
				value: key,
			}));

		return [...COMMON_HEADER_SUGGESTIONS, ...customConfiguredOptions];
	}, [coreConfig]);

	// Parse the key from the rule's value ("key:value" or just "key")
	const headerKey = useMemo(() => {
		if (!isKeyValueField || !rule?.value || typeof rule.value !== "string") return "";
		const colonIndex = rule.value.indexOf(":");
		if (colonIndex > 0) return rule.value.substring(0, colonIndex).trim();
		return rule.value.trim();
	}, [isKeyValueField, rule?.value]);

	// Prepare selectable suggestions based on whether it's headers or query params
	const keyOptions = useMemo(() => {
		const base = isHeaderField ? headerOptions : COMMON_PARAM_SUGGESTIONS;
		if (headerKey && !base.some((o) => o.value === headerKey)) {
			return [{ label: headerKey, value: headerKey }, ...base];
		}
		return base;
	}, [isHeaderField, headerOptions, headerKey]);

	const handleKeyChange = useCallback(
		(newKey: string) => {
			if (!schema || !path) return;
			// Preserve the existing value part
			const currentValue = typeof rule?.value === "string" ? rule.value : "";
			const colonIndex = currentValue.indexOf(":");
			const valuePart = colonIndex > 0 ? currentValue.substring(colonIndex + 1).trim() : "";

			let updatedValue: string;
			if (newKey && valuePart) {
				updatedValue = `${newKey}:${valuePart}`;
			} else if (newKey) {
				updatedValue = newKey;
			} else {
				updatedValue = "";
			}

			// Update the rule value via query dispatch
			const currentQuery = schema.getQuery() as RuleGroupType;
			const updatedQuery = updateRuleValueAtPath(currentQuery, path, updatedValue);
			schema.dispatchQuery(updatedQuery);
		},
		[schema, path, rule?.value],
	);

	return (
		<div className="flex items-center gap-2">
			<Select value={value || ""} onValueChange={handleOnChange}>
				<SelectTrigger className="w-[180px]" data-testid="cel-builder-field-selector-select">
					<SelectValue placeholder="Select field..." />
				</SelectTrigger>
				<SelectContent>
					{options.map((opt) => {
						const option = opt as any;
						// Handle option groups (not currently used, but type-safe)
						if ("options" in option) {
							return null;
						}
						// Handle regular options - skip empty values
						if (!option.name) {
							return null;
						}
						return (
							<SelectItem key={option.name} value={option.name} disabled={option.disabled}>
								{option.label}
							</SelectItem>
						);
					})}
				</SelectContent>
			</Select>

			{isKeyValueField && (
				<div className="flex items-center gap-1.5">
					<span className="text-muted-foreground text-sm whitespace-nowrap">has key</span>

					{!isManualInput ? (
						<div className="flex items-center gap-1">
							<ComboboxSelect
								options={keyOptions}
								value={headerKey || null}
								onValueChange={(val) => handleKeyChange(val || "")}
								placeholder={isHeaderField ? "Select header key..." : isParamField ? "Select param key..." : "Select key..."}
								searchPlaceholder={isHeaderField ? "Search or type header..." : "Search or type param..."}
								creatable
								createLabel={(typed) => `Use "${typed}"`}
								className="w-[230px]"
								data-testid="cel-builder-field-selector-combobox"
							/>
							<Button
								type="button"
								variant="ghost"
								size="icon"
								className="h-8 w-8 text-muted-foreground hover:text-foreground"
								onClick={() => setIsManualInput(true)}
								title="Switch to manual text typing"
							>
								<PenLine className="h-3.5 w-3.5" />
							</Button>
						</div>
					) : (
						<div className="flex items-center gap-1">
							<Input
								type="text"
								value={headerKey}
								onChange={(e) => handleKeyChange(e.target.value)}
								placeholder={`${fieldData?.label || "Key"} name (e.g., x-api-key)`}
								className="w-[230px]"
								data-testid="cel-builder-field-selector-key-input"
								autoFocus
							/>
							<Button
								type="button"
								variant="ghost"
								size="icon"
								className="h-8 w-8 text-muted-foreground hover:text-foreground"
								onClick={() => setIsManualInput(false)}
								title="Switch to dropdown list"
							>
								<ListFilter className="h-3.5 w-3.5" />
							</Button>
						</div>
					)}
				</div>
			)}
		</div>
	);
}