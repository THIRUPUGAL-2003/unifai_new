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
	useActivateAccessProfileMutation,
	useCloneAccessProfileMutation,
	useCreateAccessProfileMutation,
	useDeleteAccessProfileMutation,
	useGetAccessProfilesQuery,
} from "@enterprise/lib/store/apis/accessProfileApi";
import { AccessProfile } from "@enterprise/lib/types/workspace";
import { Copy, IdCard, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function AccessProfilesIndexView() {
	const [search, setSearch] = useState("");
	const [open, setOpen] = useState(false);
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [tags, setTags] = useState("");
	const [providerName, setProviderName] = useState("");
	const [allowedModels, setAllowedModels] = useState("");

	const { data, isLoading } = useGetAccessProfilesQuery({ search: search || undefined });
	const [createProfile] = useCreateAccessProfileMutation();
	const [activateProfile] = useActivateAccessProfileMutation();
	const [cloneProfile] = useCloneAccessProfileMutation();
	const [deleteProfile] = useDeleteAccessProfileMutation();

	const profiles = data?.access_profiles || [];

	const create = async () => {
		try {
			await createProfile({
				name,
				description,
				is_active: true,
				tags: tags
					.split(",")
					.map((tag) => tag.trim())
					.filter(Boolean),
				provider_configs: providerName
					? [
							{
								provider_name: providerName,
								all_models_allowed: !allowedModels,
								allowed_models: allowedModels
									.split(",")
									.map((model) => model.trim())
									.filter(Boolean),
							},
						]
					: [],
			}).unwrap();
			toast.success("Access profile created");
			setOpen(false);
			setName("");
			setDescription("");
			setTags("");
			setProviderName("");
			setAllowedModels("");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="flex h-full w-full flex-col gap-4">
			<RuntimeLimitBanner description="Profiles save and activate in the DB. Applying profile policies onto virtual keys / users at request time needs Enterprise access-profile propagation." />
			<div className="flex items-center justify-between">
				<div>
					<h1 className="flex items-center gap-2 text-2xl font-semibold">
						<IdCard className="h-6 w-6" />
						Access Profiles
					</h1>
					<p className="text-muted-foreground text-sm">Reusable provider, model, budget, and MCP policy templates.</p>
				</div>
				<Button data-testid="access-profiles-create" onClick={() => setOpen(true)}>
					<Plus className="h-4 w-4" />
					New profile
				</Button>
			</div>
			<Input className="max-w-sm" placeholder="Search profiles…" value={search} onChange={(e) => setSearch(e.target.value)} />
			{isLoading ? (
				<p className="text-muted-foreground text-sm">Loading profiles…</p>
			) : profiles.length === 0 ? (
				<div className="rounded-xl border border-dashed p-10 text-center">
					<p className="font-medium">No access profiles</p>
					<p className="text-muted-foreground mt-1 text-sm">Create a template to auto-issue virtual keys later.</p>
				</div>
			) : (
				<TableView
					profiles={profiles}
					onToggle={async (profile) => {
						try {
							await activateProfile({ id: profile.id, activate: !profile.is_active }).unwrap();
						} catch (err) {
							toast.error(getErrorMessage(err));
						}
					}}
					onClone={async (id) => {
						try {
							await cloneProfile(id).unwrap();
							toast.success("Profile cloned");
						} catch (err) {
							toast.error(getErrorMessage(err));
						}
					}}
					onDelete={async (id) => {
						try {
							await deleteProfile(id).unwrap();
							toast.success("Profile deleted");
						} catch (err) {
							toast.error(getErrorMessage(err));
						}
					}}
				/>
			)}

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Create access profile</DialogTitle>
					</DialogHeader>
					<div className="space-y-3 py-2">
						<div className="space-y-1">
							<Label>Name</Label>
							<Input value={name} onChange={(e) => setName(e.target.value)} />
						</div>
						<div className="space-y-1">
							<Label>Description</Label>
							<Input value={description} onChange={(e) => setDescription(e.target.value)} />
						</div>
						<div className="space-y-1">
							<Label>Tags (comma separated)</Label>
							<Input value={tags} onChange={(e) => setTags(e.target.value)} />
						</div>
						<div className="space-y-1">
							<Label>Provider</Label>
							<Input value={providerName} onChange={(e) => setProviderName(e.target.value)} placeholder="openai" />
						</div>
						<div className="space-y-1">
							<Label>Allowed models (blank = all)</Label>
							<Input value={allowedModels} onChange={(e) => setAllowedModels(e.target.value)} placeholder="gpt-4o, gpt-4o-mini" />
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setOpen(false)}>
							Cancel
						</Button>
						<Button onClick={() => void create()}>Create</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}

function TableView({
	profiles,
	onToggle,
	onClone,
	onDelete,
}: {
	profiles: AccessProfile[];
	onToggle: (profile: AccessProfile) => void;
	onClone: (id: number) => void;
	onDelete: (id: number) => void;
}) {
	return (
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Name</TableHead>
					<TableHead>Providers</TableHead>
					<TableHead>Active</TableHead>
					<TableHead>Version</TableHead>
					<TableHead className="text-right">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{profiles.map((profile) => (
					<TableRow key={profile.id}>
						<TableCell>
							<div className="font-medium">{profile.name}</div>
							<div className="text-muted-foreground text-xs">{profile.description}</div>
						</TableCell>
						<TableCell className="text-xs">{profile.provider_configs?.map((cfg) => cfg.provider_name).join(", ") || "—"}</TableCell>
						<TableCell>
							<Switch checked={profile.is_active} onCheckedChange={() => onToggle(profile)} />
						</TableCell>
						<TableCell>
							<Badge variant="secondary">v{profile.version}</Badge>
						</TableCell>
						<TableCell className="text-right">
							<Button size="icon" variant="ghost" onClick={() => onClone(profile.id)}>
								<Copy className="h-4 w-4" />
							</Button>
							<Button size="icon" variant="ghost" onClick={() => onDelete(profile.id)}>
								<Trash2 className="h-4 w-4" />
							</Button>
						</TableCell>
					</TableRow>
				))}
			</TableBody>
		</Table>
	);
}
