import ContactUsView from "@enterprise/components/views/contactUsView";
import { Ban } from "lucide-react";

export default function NewrelicView() {
	return (
		<div className="flex min-h-[40vh] items-center justify-center p-6">
			<ContactUsView
				icon={<Ban className="h-10 w-10" strokeWidth={1.5} />}
				title="New Relic connector unavailable"
				description="This connector is not wired in the current build. Use OpenTelemetry, Prometheus, or Maxim for observability exports."
				testIdPrefix="newrelic"
			/>
		</div>
	);
}
