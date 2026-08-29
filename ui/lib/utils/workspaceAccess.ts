import {
	getDefaultPathForSections,
	isPathAllowedForUser,
	parseAdminAllowedSections,
} from "@/lib/constants/workspaceSections";
import { DEFAULT_POST_LOGIN_PATH } from "@/lib/utils/loginGoto";
import { getApiBaseUrl } from "@/lib/utils/port";

export interface SessionAuth {
	is_auth_enabled: boolean;
	has_valid_token: boolean;
	role?: string;
	allowed_sections?: string;
}

export async function fetchSessionAuth(): Promise<SessionAuth | null> {
	try {
		const res = await fetch(`${getApiBaseUrl()}/session/is-auth-enabled`, {
			credentials: "include",
		});
		if (res.ok) {
			return res.json();
		}
	} catch {
		// fall through
	}
	return null;
}

export function getDefaultWorkspacePath(auth: SessionAuth | null | undefined): string {
	if (auth?.role === "user") {
		return "/workspace/prompt-repo";
	}
	if (auth?.role === "admin") {
		const limited = parseAdminAllowedSections(auth.allowed_sections);
		if (limited) {
			return getDefaultPathForSections(limited);
		}
	}
	return "/workspace/dashboard";
}

export function resolvePostLoginPath(
	auth: Pick<SessionAuth, "role" | "allowed_sections"> | null | undefined,
	goto?: string | null,
): string {
	const defaultPath = auth?.role ? getDefaultWorkspacePath(auth as SessionAuth) : DEFAULT_POST_LOGIN_PATH;

	if (!goto || goto === "/workspace" || goto === "/workspace/") {
		return defaultPath;
	}

	if (auth?.role === "user") {
		if (goto.startsWith("/workspace/prompt-repo")) {
			return goto;
		}
		return defaultPath;
	}

	if (auth?.role === "admin") {
		const limited = parseAdminAllowedSections(auth.allowed_sections);
		if (limited) {
			if (isPathAllowedForUser(goto, limited)) {
				return goto;
			}
			return defaultPath;
		}
	}

	if (goto.startsWith("/workspace")) {
		return goto;
	}

	return defaultPath;
}

/** Non-null when the current workspace path must be replaced for this session. */
export function getWorkspaceAccessRedirect(
	auth: SessionAuth | null | undefined,
	pathname: string,
): string | null {
	if (auth?.role === "user") {
		if (!pathname.startsWith("/workspace/prompt-repo")) {
			return "/workspace/prompt-repo";
		}
		return null;
	}

	if (auth?.role === "admin") {
		const limited = parseAdminAllowedSections(auth.allowed_sections);
		if (limited && !isPathAllowedForUser(pathname, limited)) {
			return getDefaultPathForSections(limited);
		}
	}

	if (pathname === "/workspace" || pathname === "/workspace/") {
		return getDefaultWorkspacePath(auth);
	}

	return null;
}
