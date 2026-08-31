import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage, useGetMCPClientsQuery } from "@/lib/store";
import RuntimeLimitBanner from "@enterprise/components/views/runtimeLimitBanner";
import {
	useCreateMCPToolGroupMutation,
	useDeleteMCPToolGroupMutation,
	useGetMCPToolGroupsQuery,
	useUpdateMCPToolGroupMutation,
} from "@enterprise/lib/store/apis/mcpToolGroupsApi";
import { MCPToolGroup } from "@enterprise/lib/types/workspace";
import { Boxes, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function MCPToolGroups() {
	const { data } = useGetMCPClientsQuery({ limit: 200, offset: 0 });
	const clients = data?.clients || [];
	const { data: groupData } = useGetMCPToolGroupsQuery();
	const [createGroup] = useCreateMCPToolGroupMutation();
	const [updateGroup] = useUpdateMCPToolGroupMutation();
	const [deleteGroup] = useDeleteMCPToolGroupMutation();
	const groups = groupData?.tool_groups || [];
	const [open, setOpen] = useState(false);
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [clientId, setClientId] = useState("");
	const [toolNames, setToolNames] = useState("");
	const enabled = true;

	const create = async () => {
		try {
			await createGroup({
				name,
				description,
				enabled,
				tools: clientId
					? [
							{
								mcp_client_id: clientId,
								tool_names: toolNames
									.split(",")
									.map((tool) => tool.trim())
									.filter(Boolean),
							},
						]
					: [],
			}).unwrap();
			toast.success("Tool group created");
			setOpen(false);
			setName("");
			setDescription("");
			setToolNames("");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const toggle = async (group: MCPToolGroup) => {
		try {
			await updateGroup({ ...group, enabled: !group.enabled }).unwrap();
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const remove = async (id: number) => {
		try {
			await deleteGroup(id).unwrap();
			toast.success("Tool group deleted");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="flex w-full flex-col gap-6 p-1">
			<RuntimeLimitBanner description="Tool groups filter MCP tool execution at request time for matching virtual keys, users, teams, and customers." />
			<div className="flex items-center justify-between">
				<div>
					<h1 className="flex items-center gap-2 text-2xl font-semibold">
						<Boxes className="h-6 w-6" />
						MCP Tool Groups
					</h1>
					<p className="text-muted-foreground mt-1 text-sm">Bundle tools from one or more MCP clients and attach them to keys or teams.</p>
				</div>
				<Button onClick={() => setOpen(true)}>
					<Plus className="h-4 w-4" />
					New group
				</Button>
			</div>

			{groups.length === 0 ? (
				<div className="rounded-xl border border-dashed p-10 text-center">
					<p className="font-medium">No tool groups</p>
					<p className="text-muted-foreground mt-1 text-sm">Create a group to share a curated tool set.</p>
				</div>
			) : (
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Name</TableHead>
							<TableHead>Tools</TableHead>
							<TableHead>Enabled</TableHead>
							<TableHead />
						</TableRow>
					</TableHeader>
					<TableBody>
						{groups.map((group) => (
							<TableRow key={group.id}>
								<TableCell>
									<div className="font-medium">{group.name}</div>
									<div className="text-muted-foreground text-xs">{group.description}</div>
								</TableCell>
								<TableCell>
									<Badge variant="secondary">{group.tools?.length || 0} client(s)</Badge>
								</TableCell>
								<TableCell>
									<Switch checked={group.enabled} onCheckedChange={() => void toggle(group)} />
								</TableCell>
								<TableCell className="text-right">
									<Button size="icon" variant="ghost" onClick={() => void remove(group.id)}>
										<Trash2 className="h-4 w-4" />
									</Button>
								</TableCell>
							</TableRow>
						))}
					</TableBody>
				</Table>
			)}

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Create tool group</DialogTitle>
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
							<Label>MCP client</Label>
							<select value={clientId} onChange={(e) => setClientId(e.target.value)} className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm">
								<option value="">Select client</option>
								{clients.map((client) => (
									<option key={client.config.client_id} value={client.config.client_id}>
										{client.config.name}
									</option>
								))}
							</select>
						</div>
						<div className="space-y-1">
							<Label>Tool names (blank = all)</Label>
							<Input value={toolNames} onChange={(e) => setToolNames(e.target.value)} placeholder="search, fetch" />
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
