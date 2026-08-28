/** Client-side preview helpers for Browser AI attachment viewer. */

export type AttachmentPreviewKind = "pdf" | "image" | "html" | "text" | "unsupported";

export function attachmentExt(name?: string, contentType?: string): string {
	const n = (name || "").toLowerCase();
	const dot = n.lastIndexOf(".");
	if (dot >= 0) return n.slice(dot);
	const ct = (contentType || "").toLowerCase();
	if (ct.includes("pdf")) return ".pdf";
	if (ct.includes("png")) return ".png";
	if (ct.includes("jpeg") || ct.includes("jpg")) return ".jpg";
	if (ct.includes("gif")) return ".gif";
	if (ct.includes("webp")) return ".webp";
	if (ct.includes("wordprocessingml") || ct.includes("msword")) return ".docx";
	if (ct.includes("spreadsheetml") || ct.includes("excel")) return ".xlsx";
	if (ct.includes("text/plain")) return ".txt";
	if (ct.includes("csv")) return ".csv";
	if (ct.includes("json")) return ".json";
	return "";
}

export function classifyAttachmentPreview(name?: string, contentType?: string): AttachmentPreviewKind {
	const ext = attachmentExt(name, contentType);
	const ct = (contentType || "").toLowerCase();
	if (ct.startsWith("image/") || [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"].includes(ext)) return "image";
	if (ct.includes("pdf") || ext === ".pdf") return "pdf";
	if (ext === ".docx" || ct.includes("wordprocessingml")) return "html";
	if ([".xlsx", ".xls", ".csv"].includes(ext) || ct.includes("spreadsheetml") || ct.includes("csv")) return "html";
	if ([".txt", ".md", ".log", ".json", ".xml", ".html", ".htm"].includes(ext) || ct.startsWith("text/")) return "text";
	return "unsupported";
}

function escapeHtml(s: string): string {
	return s
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

/** Office Open XML (.docx/.xlsx) are ZIP archives — reject HTML/JSON error bodies early. */
async function looksLikeZip(blob: Blob): Promise<boolean> {
	if (!blob.size) return false;
	const head = new Uint8Array(await blob.slice(0, 4).arrayBuffer());
	return head.length >= 4 && head[0] === 0x50 && head[1] === 0x4b;
}

export async function buildAttachmentPreview(
	blob: Blob,
	name?: string,
	contentType?: string,
): Promise<{ kind: AttachmentPreviewKind; blobUrl?: string; html?: string; text?: string }> {
	const kind = classifyAttachmentPreview(name, contentType || blob.type);
	const ext = attachmentExt(name, contentType || blob.type);

	if (kind === "image" || kind === "pdf") {
		return { kind, blobUrl: URL.createObjectURL(blob) };
	}

	if (kind === "text" || ext === ".csv") {
		const text = await blob.text();
		if (ext === ".csv") {
			const rows = text.split(/\r?\n/).filter((l) => l.length > 0).slice(0, 200);
			const table = rows
				.map((row, i) => {
					const cells = row.split(",").map((c) => `<td class="border border-border px-2 py-1 text-xs">${escapeHtml(c)}</td>`);
					return `<tr class="${i === 0 ? "bg-muted/40 font-medium" : ""}">${cells.join("")}</tr>`;
				})
				.join("");
			return {
				kind: "html",
				html: `<div class="overflow-auto"><table class="w-full border-collapse">${table}</table></div>`,
			};
		}
		return { kind: "text", text };
	}

	if (ext === ".docx" || (contentType || "").includes("wordprocessingml")) {
		if (!(await looksLikeZip(blob))) return { kind: "unsupported" };
		try {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const mammoth: any = await import("mammoth");
			const api = mammoth.default ?? mammoth;
			const buf = await blob.arrayBuffer();
			const result = await api.convertToHtml({ arrayBuffer: buf });
			const html = result.value?.trim()
				? `<div class="prose prose-invert max-w-none text-sm leading-relaxed p-2">${result.value}</div>`
				: `<p class="text-muted-foreground text-sm">Empty document.</p>`;
			return { kind: "html", html };
		} catch {
			return { kind: "unsupported" };
		}
	}

	if ([".xlsx", ".xls"].includes(ext) || (contentType || "").includes("spreadsheetml")) {
		if (!(await looksLikeZip(blob))) return { kind: "unsupported" };
		try {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const XLSXmod: any = await import("xlsx");
			const XLSX = XLSXmod.default ?? XLSXmod;
			const buf = await blob.arrayBuffer();
			const wb = XLSX.read(buf, { type: "array" });
			const sheetName = wb.SheetNames[0];
			if (!sheetName) {
				return { kind: "html", html: `<p class="text-sm text-muted-foreground">Workbook has no sheets.</p>` };
			}
			const sheet = wb.Sheets[sheetName];
			const htmlTable = XLSX.utils.sheet_to_html(sheet, { id: "unifai-xlsx-preview", editable: false });
			const wrapped = `<div class="overflow-auto text-xs [&_table]:w-full [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted/40">
			<p class="text-[11px] text-muted-foreground mb-2">Sheet: ${escapeHtml(sheetName)}${wb.SheetNames.length > 1 ? ` (+${wb.SheetNames.length - 1} more)` : ""}</p>
			${htmlTable}
		</div>`;
			return { kind: "html", html: wrapped };
		} catch {
			return { kind: "unsupported" };
		}
	}

	return { kind: "unsupported" };
}
