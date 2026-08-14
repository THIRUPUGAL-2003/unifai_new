import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getApiBaseUrl } from "@/lib/utils/port";
import { useEffect, useState } from "react";

interface User {
	id: string;
	username: string;
	role: string;
	budget: number;
	rate_limit: number;
}

export default function UserRankingsTab() {
	const [users, setUsers] = useState<User[]>([]);

	useEffect(() => {
		fetch(`${getApiBaseUrl()}/session/users`, { credentials: "include" })
			.then((res) => (res.ok ? res.json() : []))
			.then((data) => setUsers(Array.isArray(data) ? data : []))
			.catch(() => undefined);
	}, []);

	return (
		<div className="space-y-3 p-2">
			<p className="text-muted-foreground text-sm">Users ranked by configured budget, then rate limit.</p>
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead>User</TableHead>
						<TableHead>Role</TableHead>
						<TableHead>Budget</TableHead>
						<TableHead>Rate limit</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{[...users]
						.sort((a, b) => b.budget - a.budget || b.rate_limit - a.rate_limit)
						.map((user) => (
							<TableRow key={user.id}>
								<TableCell className="font-medium">{user.username}</TableCell>
								<TableCell>{user.role}</TableCell>
								<TableCell>{user.budget > 0 ? `$${user.budget.toFixed(2)}` : "Unlimited"}</TableCell>
								<TableCell>{user.rate_limit > 0 ? `${user.rate_limit} RPM` : "Unlimited"}</TableCell>
							</TableRow>
						))}
				</TableBody>
			</Table>
		</div>
	);
}
