"use client";

import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdownMenu";
import {
	downloadDocTable,
	downloadExcelTable,
	downloadPdfTable,
	type ExportTableColumn,
	type ExportTableRow,
} from "@/lib/utils/tableExport";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { useCallback, useState } from "react";

export type ExportFormatsPayload = {
	filename: string;
	title: string;
	subtitle?: string;
	columns: ExportTableColumn[];
	rows: ExportTableRow[];
};

interface ExportFormatsDropdownProps {
	/** Resolve rows/columns when the user picks a format (can be async). */
	getPayload: () => ExportFormatsPayload | Promise<ExportFormatsPayload>;
	disabled?: boolean;
	size?: "default" | "sm" | "lg" | "icon";
	className?: string;
	testId?: string;
}

export function ExportFormatsDropdown({
	getPayload,
	disabled,
	size = "default",
	className,
	testId = "export-formats-trigger",
}: ExportFormatsDropdownProps) {
	const [exporting, setExporting] = useState(false);

	const run = useCallback(
		async (format: "pdf" | "excel" | "doc") => {
			setExporting(true);
			await new Promise((r) => requestAnimationFrame(r));
			try {
				const payload = await getPayload();
				if (!payload.columns.length) return;
				if (format === "pdf") {
					await downloadPdfTable(payload);
				} else if (format === "excel") {
					await downloadExcelTable(payload);
				} else {
					await downloadDocTable(payload);
				}
			} finally {
				setExporting(false);
			}
		},
		[getPayload],
	);

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					variant="outline"
					size={size}
					disabled={disabled || exporting}
					className={className}
					data-testid={testId}
				>
					{exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
					{exporting ? "Exporting..." : "Export"}
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end">
				<DropdownMenuItem onClick={() => run("pdf")} data-testid="export-pdf-item">
					<FileText className="h-4 w-4" />
					PDF
				</DropdownMenuItem>
				<DropdownMenuItem onClick={() => run("excel")} data-testid="export-excel-item">
					<FileSpreadsheet className="h-4 w-4" />
					Excel
				</DropdownMenuItem>
				<DropdownMenuItem onClick={() => run("doc")} data-testid="export-doc-item">
					<FileText className="h-4 w-4" />
					DOC
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
