/** Sidebar sections admins can grant to non-admin users. Keys must stay stable in DB. */
export const WORKSPACE_SECTIONS = [
	{ key: "observability", label: "Observability", defaultPath: "/workspace/logs" },
	{ key: "models", label: "Models", defaultPath: "/workspace/providers" },
	{ key: "mcp-gateway", label: "MCP Gateway", defaultPath: "/workspace/mcp-gateway" },
	{ key: "plugins", label: "Plugins", defaultPath: "/workspace/plugins" },
	{ key: "governance", label: "Governance", defaultPath: "/workspace/governance" },
	{ key: "guardrails", label: "Guardrails", defaultPath: "/workspace/guardrails" },
	{ key: "cluster-config", label: "Cluster Config", defaultPath: "/workspace/cluster" },
	{ key: "adaptive-routing", label: "Adaptive Routing", defaultPath: "/workspace/adaptive-routing" },
	{ key: "prompt-repository", label: "Prompt Repository", defaultPath: "/workspace/prompt-repo" },
	{ key: "skills-repository", label: "Skills Repository", defaultPath: "/workspace/skills-repo" },
	{ key: "settings", label: "Settings", defaultPath: "/workspace/config" },
] as const;

export type WorkspaceSectionKey = (typeof WORKSPACE_SECTIONS)[number]["key"];

export const DEFAULT_USER_SECTIONS = "prompt-repository";

export const SECTION_KEY_BY_TITLE: Record<string, WorkspaceSectionKey> = Object.fromEntries(
	WORKSPACE_SECTIONS.map((s) => [s.label, s.key]),
) as Record<string, WorkspaceSectionKey>;

const SECTION_PATH_PREFIXES: Record<WorkspaceSectionKey, string[]> = {
	observability: [
		"/workspace/dashboard",
		"/workspace/logs",
		"/workspace/mcp-logs",
		"/workspace/browser-ai",
		"/workspace/observability",
		"/workspace/config/logging",
	],
	models: [
		"/workspace/model-catalog",
		"/workspace/providers",
		"/workspace/model-limits",
		"/workspace/routing-rules",
		"/workspace/complexity-router",
		"/workspace/circuit-breaker",
		"/workspace/custom-pricing",
	],
	"mcp-gateway": [
		"/workspace/mcp-gateway",
		"/workspace/mcp-registry",
		"/workspace/mcp-tool-groups",
		"/workspace/mcp-sessions",
		"/workspace/oauth-grants",
		"/workspace/mcp-settings",
	],
	plugins: ["/workspace/plugins"],
	governance: ["/workspace/governance", "/workspace/scim", "/workspace/audit-logs"],
	guardrails: ["/workspace/guardrails"],
	"cluster-config": ["/workspace/cluster"],
	"adaptive-routing": ["/workspace/adaptive-routing"],
	"prompt-repository": ["/workspace/prompt-repo"],
	"skills-repository": ["/workspace/skills-repo"],
	settings: ["/workspace/config"],
};

export function parseAllowedSections(raw?: string | null): Set<WorkspaceSectionKey> {
	const trimmed = (raw || "").trim();
	if (!trimmed) {
		return new Set([DEFAULT_USER_SECTIONS]);
	}
	const keys = trimmed
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean) as WorkspaceSectionKey[];
	return new Set(keys.length > 0 ? keys : [DEFAULT_USER_SECTIONS]);
}

export function allowedSectionsToString(sections: Set<WorkspaceSectionKey>): string {
	return Array.from(sections).join(",");
}

export function isPathAllowedForUser(pathname: string, allowedSections: Set<WorkspaceSectionKey>): boolean {
	for (const section of allowedSections) {
		const prefixes = SECTION_PATH_PREFIXES[section];
		if (!prefixes) continue;
		for (const prefix of prefixes) {
			if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
				return true;
			}
		}
	}
	return false;
}

export function getDefaultPathForSections(allowedSections: Set<WorkspaceSectionKey>): string {
	const first = WORKSPACE_SECTIONS.find((s) => allowedSections.has(s.key));
	return first?.defaultPath ?? "/workspace/prompt-repo";
}
