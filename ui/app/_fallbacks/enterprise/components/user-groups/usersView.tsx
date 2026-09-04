import { useState } from "react";
import { Users, Plus, Search, Edit2, Trash2, Shield, Check, X, Clock, Key, DollarSign, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
	WORKSPACE_SECTIONS,
	adminSectionsFromStorage,
	allowedSectionsToString,
	type WorkspaceSectionKey,
} from "@/lib/constants/workspaceSections";
import {
	getErrorMessage,
	useApproveSessionUserMutation,
	useCreateSessionUserMutation,
	useDeleteSessionUserMutation,
	useGetPromptsQuery,
	useGetSessionUsersQuery,
	useRejectSessionUserMutation,
	useUpdateSessionUserMutation,
	type SessionUser,
} from "@/lib/store";

export default function UsersView() {
	const [searchQuery, setSearchQuery] = useState("");
	const [actionBusyId, setActionBusyId] = useState<string | null>(null);

	const { data: users = [], isLoading: loading } = useGetSessionUsersQuery();
	const { data: promptsData } = useGetPromptsQuery();
	const [createUser] = useCreateSessionUserMutation();
	const [updateUser] = useUpdateSessionUserMutation();
	const [deleteUser] = useDeleteSessionUserMutation();
	const [approveUser] = useApproveSessionUserMutation();
	const [rejectUser] = useRejectSessionUserMutation();
	const allPrompts = promptsData?.prompts || [];

	// Dialog states
	const [isCreateOpen, setIsCreateOpen] = useState(false);
	const [isEditOpen, setIsEditOpen] = useState(false);
	const [isDeleteOpen, setIsDeleteOpen] = useState(false);
	const [selectedUser, setSelectedUser] = useState<SessionUser | null>(null);

	// Form states
	const [username, setUsername] = useState("");
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [role, setRole] = useState("user");
	const [budget, setBudget] = useState(0);
	const [rateLimit, setRateLimit] = useState(0);
	const [allowedPromptRepos, setAllowedPromptRepos] = useState("");
	const [allowedSections, setAllowedSections] = useState<Set<WorkspaceSectionKey>>(new Set());

	const toggleSection = (key: WorkspaceSectionKey, checked: boolean) => {
		setAllowedSections((prev) => {
			const next = new Set(prev);
			if (checked) {
				next.add(key);
			} else {
				next.delete(key);
			}
			return next;
		});
	};

	const workspaceAccessPicker =
		role === "admin" ? (
			<div className="space-y-2">
				<label className="text-muted-foreground text-sm font-medium">Workspace Access</label>
				<p className="text-muted-foreground text-xs">
					Choose sidebar sections for this sub-admin. Leave all unchecked for full workspace access (super admin).
				</p>
				<div className="border-border/50 bg-muted/10 max-h-48 space-y-2 overflow-y-auto rounded-lg border p-3">
					{WORKSPACE_SECTIONS.map((section) => (
						<label key={section.key} className="text-foreground flex cursor-pointer items-center gap-2 text-sm select-none">
							<input
								type="checkbox"
								checked={allowedSections.has(section.key)}
								onChange={(e) => toggleSection(section.key, e.target.checked)}
								className="border-border mr-1 rounded text-teal-500 focus:ring-teal-500/50"
							/>
							{section.label}
						</label>
					))}
				</div>
			</div>
		) : null;

	const promptReposPicker =
		role === "user" ? (
			<div className="space-y-2">
				<label className="text-muted-foreground text-sm font-medium">Allowed Prompt Repositories</label>
				<p className="text-muted-foreground text-xs">Basic users can only open Prompt Repository — pick which repos they may use.</p>
				<div className="border-border/50 bg-muted/10 max-h-40 space-y-2 overflow-y-auto rounded-lg border p-3">
					{allPrompts.map((p) => {
						const isChecked = allowedPromptRepos
							.split(",")
							.map((id) => id.trim())
							.includes(p.id);
						return (
							<label key={p.id} className="text-foreground flex cursor-pointer items-center gap-2 text-sm select-none">
								<input
									type="checkbox"
									checked={isChecked}
									onChange={(e) => {
										let ids = allowedPromptRepos
											.split(",")
											.map((id) => id.trim())
											.filter(Boolean);
										if (e.target.checked) {
											ids.push(p.id);
										} else {
											ids = ids.filter((id) => id !== p.id);
										}
										setAllowedPromptRepos(ids.join(","));
									}}
									className="border-border mr-1 rounded text-teal-500 focus:ring-teal-500/50"
								/>
								{p.name}
							</label>
						);
					})}
					{allPrompts.length === 0 && <p className="text-muted-foreground text-xs">No prompt repositories found</p>}
				</div>
			</div>
		) : null;

	const userPayload = () => ({
		username,
		email: email.trim() || undefined,
		password: password || undefined,
		role,
		budget,
		rate_limit: rateLimit,
		allowed_prompt_repos: role === "user" ? allowedPromptRepos : "",
		allowed_sections: role === "admin" ? allowedSectionsToString(allowedSections) : "",
	});

	const handleCreateUser = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!username || !password) {
			toast.error("Username and password are required");
			return;
		}
		try {
			await createUser({ ...userPayload(), password }).unwrap();
			toast.success("User created successfully");
			setIsCreateOpen(false);
			resetForm();
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const handleEditUser = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!selectedUser) return;
		try {
			await updateUser({ id: selectedUser.id, updates: userPayload() }).unwrap();
			toast.success("User updated successfully");
			setIsEditOpen(false);
			resetForm();
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const handleDeleteUser = async () => {
		if (!selectedUser) return;
		try {
			await deleteUser(selectedUser.id).unwrap();
			toast.success("User deleted successfully");
			setIsDeleteOpen(false);
			setSelectedUser(null);
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const handleApprove = async (user: SessionUser) => {
		setActionBusyId(user.id);
		try {
			await approveUser(user.id).unwrap();
			toast.success(`${user.username} approved`);
		} catch (err) {
			toast.error(getErrorMessage(err));
		} finally {
			setActionBusyId(null);
		}
	};

	const handleReject = async (user: SessionUser) => {
		setActionBusyId(user.id);
		try {
			await rejectUser(user.id).unwrap();
			toast.success(`${user.username} denied — they cannot log in`);
		} catch (err) {
			toast.error(getErrorMessage(err));
		} finally {
			setActionBusyId(null);
		}
	};

	const resetForm = () => {
		setUsername("");
		setEmail("");
		setPassword("");
		setRole("user");
		setBudget(0);
		setRateLimit(0);
		setAllowedPromptRepos("");
		setAllowedSections(new Set());
		setSelectedUser(null);
	};

	const openEditModal = (user: SessionUser) => {
		setSelectedUser(user);
		setUsername(user.username);
		setEmail(user.email || "");
		setPassword("");
		setRole(user.role);
		setBudget(user.budget);
		setRateLimit(user.rate_limit);
		setAllowedPromptRepos(user.allowed_prompt_repos || "");
		setAllowedSections(user.role === "admin" ? adminSectionsFromStorage(user.allowed_sections) : new Set());
		setIsEditOpen(true);
	};

	const openDeleteModal = (user: SessionUser) => {
		setSelectedUser(user);
		setIsDeleteOpen(true);
	};

	const matchesSearch = (u: SessionUser) => {
		const q = searchQuery.toLowerCase();
		return u.username.toLowerCase().includes(q) || (u.email || "").toLowerCase().includes(q) || u.id.toLowerCase().includes(q);
	};

	const pendingUsers = users.filter((u) => (u.status || "approved") === "pending" && matchesSearch(u));
	const activeUsers = users.filter((u) => (u.status || "approved") === "approved" && matchesSearch(u));

	return (
		<div className="text-foreground bg-background border-border/40 flex w-full flex-col gap-6 rounded-lg border p-6 shadow-xl backdrop-blur-sm">
			{/* Header Section */}
			<div className="border-border/40 flex flex-col items-start justify-between gap-4 border-b pb-6 md:flex-row md:items-center">
				<div>
					<h1 className="text-primary flex items-center gap-2 text-2xl font-semibold tracking-tight">
						<Users className="h-6 w-6 text-teal-400" />
						User Governance
					</h1>
					<p className="text-muted-foreground mt-1 text-sm">
						Manage users, approve registrations, set budgets, rate limits, and permission roles.
					</p>
				</div>
				<Button
					onClick={() => {
						resetForm();
						setIsCreateOpen(true);
					}}
					className="flex items-center gap-2 rounded-lg bg-teal-500 px-4 py-2 font-medium text-white shadow-lg shadow-teal-500/20 transition-all duration-200 hover:bg-teal-600 active:scale-95"
				>
					<Plus className="h-4 w-4" /> Add New User
				</Button>
			</div>

			{/* Search Control */}
			<div className="relative w-full max-w-sm">
				<Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
				<Input
					placeholder="Search users..."
					value={searchQuery}
					onChange={(e) => setSearchQuery(e.target.value)}
					className="bg-muted/30 border-border/50 rounded-lg pl-9 focus:border-teal-500/50"
				/>
			</div>

			{loading ? (
				<div className="flex items-center justify-center py-20">
					<div className="h-8 w-8 animate-spin rounded-full border-t-2 border-b-2 border-teal-400"></div>
				</div>
			) : (
				<>
					{/* Pending registrations */}
					<div className="space-y-3">
						<div className="flex items-center gap-2">
							<Clock className="h-4 w-4 text-amber-400" />
							<h2 className="text-sm font-semibold text-amber-300">
								Pending approvals ({pendingUsers.length})
							</h2>
						</div>
						{pendingUsers.length === 0 ? (
							<p className="text-muted-foreground text-sm pl-6">No registration requests waiting.</p>
						) : (
							<div className="border-amber-500/20 bg-amber-500/5 overflow-hidden rounded-xl border shadow-sm">
								<Table>
									<TableHeader className="bg-muted/30">
										<TableRow>
											<TableHead className="text-foreground/90 font-semibold">ID</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Username</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Email</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Requested role</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Requested At</TableHead>
											<TableHead className="text-foreground/90 text-right font-semibold">Actions</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{pendingUsers.map((user) => (
											<TableRow key={user.id} className="hover:bg-muted/20 transition-colors">
												<TableCell className="font-mono text-[11px] text-muted-foreground max-w-[140px] truncate" title={user.id}>
													{user.id}
												</TableCell>
												<TableCell className="font-medium">{user.username}</TableCell>
												<TableCell className="text-sm text-muted-foreground">{user.email || "—"}</TableCell>
												<TableCell>
													<span
														className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
															user.role === "admin"
																? "border-teal-500/20 bg-teal-500/10 text-teal-400"
																: "border-blue-500/20 bg-blue-500/10 text-blue-400"
														}`}
													>
														<Shield className="h-3 w-3" />
														{user.role}
													</span>
												</TableCell>
												<TableCell className="text-muted-foreground text-xs">
													{new Date(user.created_at).toLocaleString()}
												</TableCell>
												<TableCell className="text-right">
													<div className="flex justify-end gap-2">
														<Button
															size="sm"
															disabled={actionBusyId === user.id}
															onClick={() => handleApprove(user)}
															className="h-8 gap-1 bg-emerald-600 hover:bg-emerald-500 text-white"
															data-testid="user-registration-accept"
														>
															<Check className="h-3.5 w-3.5" />
															Accept
														</Button>
														<Button
															size="sm"
															variant="outline"
															disabled={actionBusyId === user.id}
															onClick={() => handleReject(user)}
															className="h-8 gap-1 border-red-500/40 text-red-400 hover:bg-red-950/40"
															data-testid="user-registration-deny"
														>
															<X className="h-3.5 w-3.5" />
															Deny
														</Button>
													</div>
												</TableCell>
											</TableRow>
										))}
									</TableBody>
								</Table>
							</div>
						)}
					</div>

					{/* Active users */}
					<div className="space-y-3">
						<h2 className="text-sm font-semibold text-foreground/90">Active users ({activeUsers.length})</h2>
						{activeUsers.length === 0 ? (
							<div className="border-border/40 bg-muted/10 flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
								<Users className="text-muted-foreground/60 mb-3 h-12 w-12" />
								<p className="text-foreground/80 text-base font-medium">No Active Users</p>
								<p className="text-muted-foreground mt-1 max-w-xs text-sm">
									{searchQuery ? "No users match your search query." : "Approve a registration or click Add New User."}
								</p>
							</div>
						) : (
							<div className="border-border/40 bg-muted/5 overflow-hidden rounded-xl border shadow-sm">
								<Table>
									<TableHeader className="bg-muted/30">
										<TableRow>
											<TableHead className="text-foreground/90 font-semibold">Username</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Email</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Role</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Budget (USD)</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Rate Limit (RPM)</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Allowed Repositories</TableHead>
											<TableHead className="text-foreground/90 font-semibold">Created At</TableHead>
											<TableHead className="text-foreground/90 text-right font-semibold">Actions</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{activeUsers.map((user) => (
											<TableRow key={user.id} className="hover:bg-muted/20 transition-colors">
												<TableCell className="flex items-center gap-2 font-medium">
													<div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-500/10 text-xs font-bold text-teal-400 uppercase">
														{user.username.slice(0, 2)}
													</div>
													{user.username}
												</TableCell>
												<TableCell className="text-sm text-muted-foreground">{user.email || "—"}</TableCell>
												<TableCell>
													<span
														className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
															user.role === "admin"
																? "border-teal-500/20 bg-teal-500/10 text-teal-400"
																: "border-blue-500/20 bg-blue-500/10 text-blue-400"
														}`}
													>
														<Shield className="h-3 w-3" />
														{user.role}
													</span>
												</TableCell>
												<TableCell className="font-mono text-xs">{user.budget > 0 ? `$${user.budget.toFixed(2)}` : "Unlimited"}</TableCell>
												<TableCell className="font-mono text-xs">{user.rate_limit > 0 ? `${user.rate_limit} RPM` : "Unlimited"}</TableCell>
												<TableCell
													className="max-w-[200px] truncate text-xs"
													title={
														user.allowed_prompt_repos
															? user.allowed_prompt_repos
																	.split(",")
																	.map((id) => allPrompts.find((p) => p.id === id.trim())?.name || id)
																	.join(", ")
															: "None"
													}
												>
													{user.allowed_prompt_repos
														? user.allowed_prompt_repos
																.split(",")
																.map((id) => allPrompts.find((p) => p.id === id.trim())?.name || id)
																.join(", ")
														: "None"}
												</TableCell>
												<TableCell className="text-muted-foreground text-xs">{new Date(user.created_at).toLocaleDateString()}</TableCell>
												<TableCell className="text-right">
													<div className="flex justify-end gap-2">
														<Button
															size="icon"
															variant="ghost"
															onClick={() => openEditModal(user)}
															className="text-muted-foreground h-8 w-8 rounded-lg transition-colors hover:text-teal-400"
														>
															<Edit2 className="h-4 w-4" />
														</Button>
														<Button
															size="icon"
															variant="ghost"
															onClick={() => openDeleteModal(user)}
															className="text-muted-foreground h-8 w-8 rounded-lg transition-colors hover:text-red-400"
														>
															<Trash2 className="h-4 w-4" />
														</Button>
													</div>
												</TableCell>
											</TableRow>
										))}
									</TableBody>
								</Table>
							</div>
						)}
					</div>
				</>
			)}

			{/* Create User Dialog */}
			<Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
				<DialogContent className="bg-background border-border/80 text-foreground sm:max-w-[520px]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2 text-teal-400">
							<Users className="h-5 w-5" /> Add New User
						</DialogTitle>
					</DialogHeader>
					<form onSubmit={handleCreateUser} className="space-y-4 py-4">
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Username</label>
							<Input
								required
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								placeholder="e.g. janesmith"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Email (Optional)</label>
							<Input
								type="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								placeholder="e.g. janesmith@company.com"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Password</label>
							<Input
								type="password"
								required
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								placeholder="••••••••"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Role</label>
							<select
								value={role}
								onChange={(e) => {
									const nextRole = e.target.value;
									setRole(nextRole);
									if (nextRole === "admin") {
										setAllowedPromptRepos("");
									} else {
										setAllowedSections(new Set());
									}
								}}
								className="bg-muted/20 border-border/50 text-foreground w-full rounded-lg border p-2.5 text-sm focus:border-teal-500/50 focus:outline-none"
							>
								<option value="user">User (Prompt Repository only)</option>
								<option value="admin">Admin (choose workspace sections)</option>
							</select>
						</div>
						{workspaceAccessPicker}
						{promptReposPicker}
						<div className="grid grid-cols-2 gap-4">
							<div className="space-y-2">
								<label className="text-muted-foreground flex items-center gap-1 text-sm font-medium">
									<DollarSign className="text-muted-foreground/60 h-3.5 w-3.5" /> Budget Limit
								</label>
								<Input
									type="number"
									step="0.01"
									value={budget || ""}
									onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
									placeholder="USD / Month"
									className="bg-muted/20 border-border/50 focus:border-teal-500/50"
								/>
							</div>
							<div className="space-y-2">
								<label className="text-muted-foreground flex items-center gap-1 text-sm font-medium">
									<Activity className="text-muted-foreground/60 h-3.5 w-3.5" /> Rate Limit
								</label>
								<Input
									type="number"
									value={rateLimit || ""}
									onChange={(e) => setRateLimit(parseInt(e.target.value) || 0)}
									placeholder="RPM Limit"
									className="bg-muted/20 border-border/50 focus:border-teal-500/50"
								/>
							</div>
						</div>
						<DialogFooter className="pt-4">
							<Button
								type="button"
								variant="outline"
								onClick={() => setIsCreateOpen(false)}
								className="border-border/80 text-foreground hover:bg-muted"
							>
								Cancel
							</Button>
							<Button type="submit" className="bg-teal-500 font-medium text-white hover:bg-teal-600">
								Create User
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>

			{/* Edit User Dialog */}
			<Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
				<DialogContent className="bg-background border-border/80 text-foreground sm:max-w-[520px]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2 text-teal-400">
							<Key className="h-5 w-5" /> Edit User Settings
						</DialogTitle>
					</DialogHeader>
					<form onSubmit={handleEditUser} className="space-y-4 py-4">
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Username</label>
							<Input
								required
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								placeholder="e.g. janesmith"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Email</label>
							<Input
								type="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								placeholder="e.g. janesmith@company.com"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">New Password (Leave blank to keep same)</label>
							<Input
								type="password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								placeholder="••••••••"
								className="bg-muted/20 border-border/50 focus:border-teal-500/50"
							/>
						</div>
						<div className="space-y-2">
							<label className="text-muted-foreground text-sm font-medium">Role</label>
							<select
								value={role}
								onChange={(e) => {
									const nextRole = e.target.value;
									setRole(nextRole);
									if (nextRole === "admin") {
										setAllowedPromptRepos("");
									} else {
										setAllowedSections(new Set());
									}
								}}
								className="bg-muted/20 border-border/50 text-foreground w-full rounded-lg border p-2.5 text-sm focus:border-teal-500/50 focus:outline-none"
							>
								<option value="user">User (Prompt Repository only)</option>
								<option value="admin">Admin (choose workspace sections)</option>
							</select>
						</div>
						{workspaceAccessPicker}
						{promptReposPicker}
						<div className="grid grid-cols-2 gap-4">
							<div className="space-y-2">
								<label className="text-muted-foreground flex items-center gap-1 text-sm font-medium">
									<DollarSign className="text-muted-foreground/60 h-3.5 w-3.5" /> Budget Limit
								</label>
								<Input
									type="number"
									step="0.01"
									value={budget || ""}
									onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
									placeholder="USD / Month"
									className="bg-muted/20 border-border/50 focus:border-teal-500/50"
								/>
							</div>
							<div className="space-y-2">
								<label className="text-muted-foreground flex items-center gap-1 text-sm font-medium">
									<Activity className="text-muted-foreground/60 h-3.5 w-3.5" /> Rate Limit
								</label>
								<Input
									type="number"
									value={rateLimit || ""}
									onChange={(e) => setRateLimit(parseInt(e.target.value) || 0)}
									placeholder="RPM Limit"
									className="bg-muted/20 border-border/50 focus:border-teal-500/50"
								/>
							</div>
						</div>
						<DialogFooter className="pt-4">
							<Button
								type="button"
								variant="outline"
								onClick={() => setIsEditOpen(false)}
								className="border-border/80 text-foreground hover:bg-muted"
							>
								Cancel
							</Button>
							<Button type="submit" className="bg-teal-500 font-medium text-white hover:bg-teal-600">
								Save Changes
							</Button>
						</DialogFooter>
					</form>
				</DialogContent>
			</Dialog>

			{/* Delete User Confirm Dialog */}
			<Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
				<DialogContent className="bg-background border-border/80 text-foreground sm:max-w-[400px]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2 text-red-400">
							<Trash2 className="h-5 w-5" /> Delete User Account
						</DialogTitle>
					</DialogHeader>
					<div className="py-4">
						<p className="text-muted-foreground text-sm">
							Are you sure you want to permanently delete the user account{" "}
							<span className="text-foreground font-semibold">"{selectedUser?.username}"</span>? This action cannot be undone and they will
							lose access immediately.
						</p>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setIsDeleteOpen(false)} className="border-border/80 text-foreground hover:bg-muted">
							Cancel
						</Button>
						<Button onClick={handleDeleteUser} className="bg-red-500 font-medium text-white hover:bg-red-600">
							Delete Account
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}