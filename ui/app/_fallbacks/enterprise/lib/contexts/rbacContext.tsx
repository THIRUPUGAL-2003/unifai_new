"use client";

import { IS_ENTERPRISE } from "@/lib/constants/config";
import { useGetMyRBACPermissionsQuery } from "@enterprise/lib/store/apis/rbacApi";
import { createContext, useCallback, useContext, useMemo } from "react";

// RBAC Resource Names (must match backend definitions)
export enum RbacResource {
	GuardrailsConfig = "GuardrailsConfig",
	GuardrailsProviders = "GuardrailsProviders",
	GuardrailRules = "GuardrailRules",
	UserProvisioning = "UserProvisioning",
	Cluster = "Cluster",
	Settings = "Settings",
	Users = "Users",
	Logs = "Logs",
	Observability = "Observability",
	Dashboard = "Dashboard",
	VirtualKeys = "VirtualKeys",
	ModelProvider = "ModelProvider",
	Plugins = "Plugins",
	MCPGateway = "MCPGateway",
	MCPToolGroups = "MCPToolGroups",
	MCPLogs = "MCPLogs",
	AdaptiveRouter = "AdaptiveRouter",
	AuditLogs = "AuditLogs",
	Customers = "Customers",
	Teams = "Teams",
	RBAC = "RBAC",
	Governance = "Governance",
	RoutingRules = "RoutingRules",
	PromptRepository = "PromptRepository",
	PromptDeploymentStrategy = "PromptDeploymentStrategy",
	SkillsRepository = "SkillsRepository",
	AccessProfiles = "AccessProfiles",
	APIKeys = "APIKeys",
	Inference = "Inference",
	Metrics = "Metrics",
	FeatureFlags = "FeatureFlags",
	CircuitBreaker = "CircuitBreaker",
}

// RBAC Operation Names (must match backend definitions)
export enum RbacOperation {
	Read = "Read",
	View = "View",
	Create = "Create",
	Update = "Update",
	Delete = "Delete",
	Download = "Download",
}

interface RbacContextType {
	isAllowed: (resource: RbacResource, operation: RbacOperation) => boolean;
	permissions: Record<string, Record<string, boolean>>;
	isLoading: boolean;
	refetch: () => void;
}

const RbacContext = createContext<RbacContextType | null>(null);

function hasPermission(
	permissions: Record<string, Record<string, boolean>>,
	resource: RbacResource,
	operation: RbacOperation,
): boolean {
	const ops = permissions[resource];
	if (!ops) {
		return false;
	}
	if (ops[operation]) {
		return true;
	}
	if (operation === RbacOperation.View && ops[RbacOperation.Read]) {
		return true;
	}
	if (operation === RbacOperation.Read && ops[RbacOperation.View]) {
		return true;
	}
	return false;
}

export function RbacProvider({ children }: { children: React.ReactNode }) {
	const { data, isLoading, refetch } = useGetMyRBACPermissionsQuery(undefined, { skip: !IS_ENTERPRISE });
	const permissions = data?.permissions ?? {};
	const role = data?.role ?? "admin";

	const isAllowed = useCallback(
		(resource: RbacResource, operation: RbacOperation) => {
			if (!IS_ENTERPRISE) {
				return true;
			}
			if (role === "admin") {
				return true;
			}
			return hasPermission(permissions, resource, operation);
		},
		[permissions, role],
	);

	const value = useMemo(
		() => ({
			isAllowed,
			permissions,
			isLoading: IS_ENTERPRISE ? isLoading : false,
			refetch,
		}),
		[isAllowed, permissions, isLoading, refetch],
	);

	return <RbacContext.Provider value={value}>{children}</RbacContext.Provider>;
}

export function useRbac(resource: RbacResource, operation: RbacOperation): boolean {
	const context = useContext(RbacContext);
	if (!context) {
		return true;
	}
	if (context.isLoading) {
		return true;
	}
	return context.isAllowed(resource, operation);
}

export function useRbacContext() {
	const context = useContext(RbacContext);
	if (!context) {
		return {
			isAllowed: () => true,
			permissions: {},
			isLoading: false,
			refetch: () => {},
		};
	}
	return context;
}
