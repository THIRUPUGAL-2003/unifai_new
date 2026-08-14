import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getErrorMessage } from "@/lib/store";
import { useGetAuditLogsQuery, useLazyExportAuditLogsQuery } from "@enterprise/lib/store/apis/auditLogsApi";
import { Download, ScrollText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function AuditLogsView() {
	const [search, setSearch] = useState("");
	const [action, setAction] = useState("");
	const [outcome, setOutcome] = useState("");
	const { data, isLoading: loading } = useGetAuditLogsQuery({
		search: search || undefined,
		action: action || undefined,
		outcome: outcome || undefined,
	});
	const [exportAuditLogs] = useLazyExportAuditLogsQuery();
	const logs = data?.logs || [];

	const exportLogs = async () => {
		try {
			const result = await exportAuditLogs().unwrap();
			const blob = new Blob([JSON.stringify(result.logs || [], null, 2)], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = "audit-logs.json";
			link.click();
			URL.revokeObjectURL(url);
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="flex h-full w-full flex-col gap-4 p-4">
			<div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
				<div>
					<h1 className="flex items-center gap-2 text-2xl font-semibold">
						<ScrollText className="h-6 w-6" />
						Audit Logs
					</h1>
					<p className="text-muted-foreground text-sm">Administrative create/update/delete activity for this workspace.</p>
				</div>
				<Button variant="outline" onClick={() => void exportLogs()}>
					<Download className="h-4 w-4" />
					Export JSON
				</Button>
			</div>
			<div className="flex flex-wrap gap-2">
				<Input className="max-w-xs" placeholder="Search initiator, path, IP…" value={search} onChange={(e) => setSearch(e.target.value)} />
				<select value={action} onChange={(e) => setAction(e.target.value)} className="border-input bg-background h-9 rounded-md border px-3 text-sm">
					<option value="">All actions</option>
					<option value="create">create</option>
					<option value="update">update</option>
					<option value="delete">delete</option>
				</select>
				<select value={outcome} onChange={(e) => setOutcome(e.target.value)} className="border-input bg-background h-9 rounded-md border px-3 text-sm">
					<option value="">All outcomes</option>
					<option value="success">success</option>
					<option value="failure">failure</option>
				</select>
			</div>
			<div className="min-h-0 flex-1 overflow-auto rounded-xl border">
				{loading ? (
					<p className="text-muted-foreground p-6 text-sm">Loading audit logs…</p>
				) : (
					<Table>
						<TableHeader>
							<TableRow>
								<TableHead>Time</TableHead>
								<TableHead>Action</TableHead>
								<TableHead>Outcome</TableHead>
								<TableHead>Initiator</TableHead>
								<TableHead>Path</TableHead>
								<TableHead>IP</TableHead>
								<TableHead>Duration</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody>
							{logs.map((log) => (
								<TableRow key={log.id}>
									<TableCell className="whitespace-nowrap text-xs">{new Date(log.created_at).toLocaleString()}</TableCell>
									<TableCell>{log.action}</TableCell>
									<TableCell>
										<Badge variant={log.outcome === "success" ? "secondary" : "destructive"}>{log.outcome}</Badge>
									</TableCell>
									<TableCell>{log.initiator}</TableCell>
									<TableCell className="font-mono text-xs">
										{log.method} {log.path}
									</TableCell>
									<TableCell className="font-mono text-xs">{log.ip}</TableCell>
									<TableCell className="text-xs">{log.duration_ms}ms</TableCell>
								</TableRow>
							))}
						</TableBody>
					</Table>
				)}
			</div>
		</div>
	);
}
