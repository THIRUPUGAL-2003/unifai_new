import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { getErrorMessage } from "@/lib/store";
import RuntimeLimitBanner from "@enterprise/components/views/runtimeLimitBanner";
import { useGetConnectorQuery, useUpdateConnectorMutation } from "@enterprise/lib/store/apis/connectorsApi";
import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface ConnectorFormProps {
	name: "datadog" | "kafka" | "bigquery" | "pubsub";
	title: string;
	description: string;
	fields: { key: string; label: string; type?: string; placeholder?: string }[];
	onDelete?: () => void;
	isDeleting?: boolean;
}

export function ConnectorForm({ name, title, description, fields, onDelete, isDeleting }: ConnectorFormProps) {
	const { data } = useGetConnectorQuery(name);
	const [updateConnector, { isLoading: saving }] = useUpdateConnectorMutation();
	const [enabled, setEnabled] = useState(false);
	const [config, setConfig] = useState<Record<string, string>>({});

	useEffect(() => {
		if (!data) return;
		setEnabled(!!data.enabled);
		setConfig(data.config || {});
	}, [data]);

	const save = async () => {
		try {
			await updateConnector({ name, enabled, config }).unwrap();
			toast.success(`${title} connector saved`);
		} catch (err) {
			toast.error(getErrorMessage(err));
		}
	};

	return (
		<div className="flex w-full flex-col gap-4">
			<RuntimeLimitBanner
				title="Settings save only"
				description="This connector stores credentials in the workspace DB. Live export for Datadog/Kafka/BigQuery/PubSub is not started from this form in the OSS build — use OpenTelemetry, Prometheus, or Maxim for working exports."
			/>
			<div>
				<h2 className="text-lg font-semibold">{title}</h2>
				<p className="text-muted-foreground text-sm">{description}</p>
			</div>
			<div className="flex items-center justify-between rounded-lg border p-3">
				<Label>Enable connector</Label>
				<Switch checked={enabled} onCheckedChange={setEnabled} />
			</div>
			{fields.map((field) => (
				<div key={field.key} className="space-y-1">
					<Label>{field.label}</Label>
					<Input
						type={field.type || "text"}
						placeholder={field.placeholder}
						value={config[field.key] || ""}
						onChange={(e) => setConfig((current) => ({ ...current, [field.key]: e.target.value }))}
					/>
				</div>
			))}
			<div className="flex justify-end gap-2">
				{onDelete && (
					<Button variant="outline" onClick={onDelete} disabled={isDeleting}>
						Remove
					</Button>
				)}
				<Button onClick={() => void save()} disabled={saving}>
					<Save className="h-4 w-4" />
					{saving ? "Saving…" : "Save connector"}
				</Button>
			</div>
		</div>
	);
}
