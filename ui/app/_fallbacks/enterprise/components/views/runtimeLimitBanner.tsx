import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Info } from "lucide-react";

interface Props {
	title?: string;
	description: string;
}

/** Honest status for workspace pages that persist config but may lack live runtime enforcement in OSS. */
export default function RuntimeLimitBanner({ title = "Config saves; live enforcement limited", description }: Props) {
	return (
		<Alert className="border-amber-500/40 bg-amber-500/5">
			<Info className="h-4 w-4" />
			<AlertTitle>{title}</AlertTitle>
			<AlertDescription className="text-muted-foreground text-sm">{description}</AlertDescription>
		</Alert>
	);
}
