import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage, useGetTeamsQuery } from "@/lib/store";
import {
	useAssignBusinessUnitTeamMutation,
	useCreateBusinessUnitMutation,
	useDeleteBusinessUnitMutation,
	useGetBusinessUnitTeamsQuery,
	useGetBusinessUnitsQuery,
	useRemoveBusinessUnitTeamMutation,
} from "@enterprise/lib/store/apis/businessUnitsApi";
import { BusinessUnit } from "@enterprise/lib/types/workspace";
import { Building2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export function BusinessUnitsView() {
	const [selected, setSelected] = useState<BusinessUnit | null>(null);
	const [name, setName] = useState("");
	const [open, setOpen] = useState(false);
	const [teamId, setTeamId] = useState("");
	const { data: unitData } = useGetBusinessUnitsQuery();
	const { data: teamData } = useGetTeamsQuery();
	const { data: assignedData } = useGetBusinessUnitTeamsQuery(selected?.id ?? "", { skip: !selected });
	const [createUnit] = useCreateBusinessUnitMutation();
	const [deleteUnit] = useDeleteBusinessUnitMutation();
	const [assignTeam] = useAssignBusinessUnitTeamMutation();
	const [removeTeam] = useRemoveBusinessUnitTeamMutation();
	const units = unitData?.business_units || [];
	const teams = teamData?.teams || [];
	const assigned = assignedData?.teams || [];

	const create = async () => {
		try {
			await createUnit({ name }).unwrap();
			toast.success("Business unit created");
			setOpen(false);
			setName("");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const remove = async (id: string) => {
		try {
			await deleteUnit(id).unwrap();
			if (selected?.id === id) setSelected(null);
			toast.success("Business unit deleted");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const assign = async () => {
		if (!selected || !teamId) return;
		try {
			await assignTeam({ id: selected.id, team_id: teamId }).unwrap();
			toast.success("Team assigned");
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	const unassign = async (id: string) => {
		if (!selected) return;
		try {
			await removeTeam({ id: selected.id, team_id: id }).unwrap();
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
			<div className="flex flex-col gap-4">
				<div className="flex items-center justify-between">
					<div>
						<h1 className="flex items-center gap-2 text-2xl font-semibold">
							<Building2 className="h-6 w-6" />
							Business Units
						</h1>
						<p className="text-muted-foreground text-sm">Group teams under an organizational unit with its own governance.</p>
					</div>
					<Button onClick={() => setOpen(true)}>
						<Plus className="h-4 w-4" />
						New unit
					</Button>
				</div>
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Name</TableHead>
							<TableHead>Teams</TableHead>
							<TableHead />
						</TableRow>
					</TableHeader>
					<TableBody>
						{units.map((unit) => (
							<TableRow key={unit.id} className={selected?.id === unit.id ? "bg-muted/40" : ""} onClick={() => setSelected(unit)}>
								<TableCell className="font-medium">{unit.name}</TableCell>
								<TableCell>{unit.team_count}</TableCell>
								<TableCell className="text-right">
									<Button
										size="icon"
										variant="ghost"
										onClick={(e) => {
											e.stopPropagation();
											void remove(unit.id);
										}}
									>
										<Trash2 className="h-4 w-4" />
									</Button>
								</TableCell>
							</TableRow>
						))}
					</TableBody>
				</Table>
			</div>

			<div className="rounded-xl border p-4">
				{!selected ? (
					<p className="text-muted-foreground text-sm">Select a business unit to assign teams.</p>
				) : (
					<div className="space-y-4">
						<h2 className="text-lg font-semibold">{selected.name}</h2>
						<div className="flex gap-2">
							<select value={teamId} onChange={(e) => setTeamId(e.target.value)} className="border-input bg-background h-9 flex-1 rounded-md border px-3 text-sm">
								<option value="">Select team</option>
								{teams.map((team) => (
									<option key={team.id} value={team.id}>
										{team.name}
									</option>
								))}
							</select>
							<Button onClick={() => void assign()}>Assign</Button>
						</div>
						<div className="space-y-2">
							{assigned.map((team) => (
								<div key={team.id} className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm">
									<span>{team.name}</span>
									<Button size="icon" variant="ghost" onClick={() => void unassign(team.id)}>
										<Trash2 className="h-4 w-4" />
									</Button>
								</div>
							))}
						</div>
					</div>
				)}
			</div>

			<Dialog open={open} onOpenChange={setOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Create business unit</DialogTitle>
					</DialogHeader>
					<div className="space-y-1 py-2">
						<Label>Name</Label>
						<Input value={name} onChange={(e) => setName(e.target.value)} />
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
