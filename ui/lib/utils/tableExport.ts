/**
 * Table export helpers: PDF, Excel (.xlsx), and Word-compatible .doc with logo.
 */

export type ExportTableColumn = { key: string; header: string };
export type ExportTableRow = Record<string, string | number | boolean | null | undefined>;

const LOGO_SRC = "/header_logo.png";

function dateStamp(): string {
	const now = new Date();
	return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function triggerDownload(blob: Blob, filename: string): void {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(url), 0);
}

function escapeHtml(s: string): string {
	return String(s ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

async function loadLogoDataUrl(logoSrc = LOGO_SRC): Promise<string | null> {
	try {
		const res = await fetch(logoSrc);
		if (!res.ok) return null;
		const blob = await res.blob();
		return await new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result || "") || null);
			reader.onerror = () => reject(reader.error);
			reader.readAsDataURL(blob);
		});
	} catch {
		return null;
	}
}

function cellValue(row: ExportTableRow, key: string): string {
	const v = row[key];
	if (v === null || v === undefined) return "";
	return String(v);
}

function buildHtmlDocument(opts: {
	title: string;
	subtitle?: string;
	columns: ExportTableColumn[];
	rows: ExportTableRow[];
	logoDataUrl?: string | null;
}): string {
	const { title, subtitle, columns, rows, logoDataUrl } = opts;
	const headerCells = columns.map((c) => `<th style="border:1px solid #ccc;padding:6px 8px;background:#f3f4f6;text-align:left;font-size:11px;">${escapeHtml(c.header)}</th>`).join("");
	const bodyRows = rows
		.map((row) => {
			const cells = columns
				.map((c) => `<td style="border:1px solid #ddd;padding:5px 8px;font-size:10px;vertical-align:top;">${escapeHtml(cellValue(row, c.key))}</td>`)
				.join("");
			return `<tr>${cells}</tr>`;
		})
		.join("");

	const logoBlock = logoDataUrl
		? `<img src="${logoDataUrl}" alt="Logo" style="height:36px;width:auto;margin-bottom:8px;" />`
		: "";

	return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
</head>
<body style="font-family:Segoe UI,Arial,sans-serif;color:#111;padding:24px;">
${logoBlock}
<h1 style="font-size:18px;margin:0 0 4px 0;">${escapeHtml(title)}</h1>
${subtitle ? `<p style="font-size:11px;color:#666;margin:0 0 16px 0;">${escapeHtml(subtitle)}</p>` : ""}
<p style="font-size:10px;color:#888;margin:0 0 12px 0;">Exported ${new Date().toLocaleString()} · ${rows.length} row(s)</p>
<table style="border-collapse:collapse;width:100%;">
<thead><tr>${headerCells}</tr></thead>
<tbody>${bodyRows || `<tr><td colspan="${columns.length}" style="padding:8px;color:#666;">No data</td></tr>`}</tbody>
</table>
</body>
</html>`;
}

/** Excel (.xlsx) export via SheetJS. */
export async function downloadExcelTable(opts: {
	filename: string;
	sheetName?: string;
	columns: ExportTableColumn[];
	rows: ExportTableRow[];
}): Promise<void> {
	const XLSXmod: any = await import("xlsx");
	const XLSX = XLSXmod.default ?? XLSXmod;
	const headers = opts.columns.map((c) => c.header);
	const data = opts.rows.map((row) => opts.columns.map((c) => cellValue(row, c.key)));
	const aoa = [headers, ...data];
	const ws = XLSX.utils.aoa_to_sheet(aoa);
	const wb = XLSX.utils.book_new();
	XLSX.utils.book_append_sheet(wb, ws, (opts.sheetName || "Export").slice(0, 31));
	const out = XLSX.write(wb, { bookType: "xlsx", type: "array" });
	triggerDownload(
		new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
		`${opts.filename}-${dateStamp()}.xlsx`,
	);
}

/**
 * Word-compatible .doc (HTML Word) with product logo embedded.
 * Opens cleanly in Microsoft Word / LibreOffice.
 */
export async function downloadDocTable(opts: {
	filename: string;
	title: string;
	subtitle?: string;
	columns: ExportTableColumn[];
	rows: ExportTableRow[];
	logoSrc?: string;
}): Promise<void> {
	const logoDataUrl = await loadLogoDataUrl(opts.logoSrc || LOGO_SRC);
	const html = buildHtmlDocument({
		title: opts.title,
		subtitle: opts.subtitle,
		columns: opts.columns,
		rows: opts.rows,
		logoDataUrl,
	});
	const wordHtml = `\uFEFF<html xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:w="urn:schemas-microsoft-com:office:word"
 xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"><title>${escapeHtml(opts.title)}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
</head>
<body>${html.replace(/^[\s\S]*<body[^>]*>/i, "").replace(/<\/body>[\s\S]*$/i, "")}</body></html>`;

	triggerDownload(
		new Blob([wordHtml], { type: "application/msword;charset=utf-8" }),
		`${opts.filename}-${dateStamp()}.doc`,
	);
}

/** PDF export with logo branding (reuses generatePdf). */
export async function downloadPdfTable(opts: {
	filename: string;
	title: string;
	subtitle?: string;
	columns: ExportTableColumn[];
	rows: ExportTableRow[];
	logoSrc?: string;
}): Promise<void> {
	const logoDataUrl = await loadLogoDataUrl(opts.logoSrc || LOGO_SRC);
	const html = buildHtmlDocument({
		title: opts.title,
		subtitle: opts.subtitle,
		columns: opts.columns,
		rows: opts.rows,
		logoDataUrl,
	});

	const host = document.createElement("div");
	host.style.cssText = "position:fixed;left:-10000px;top:0;width:900px;background:#fff;color:#111;";
	host.innerHTML = html;
	document.body.appendChild(host);

	try {
		const { generatePdf } = await import("@/lib/utils/pdf");
		await generatePdf([{ element: host, label: opts.title }], opts.filename, {
			orientation: "landscape",
			branding: {
				logoSrc: opts.logoSrc || LOGO_SRC,
				text: "Powered by",
			},
		});
	} finally {
		host.remove();
	}
}
