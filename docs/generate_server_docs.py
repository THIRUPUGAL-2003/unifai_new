#!/usr/bin/env python3
"""Customer-clear UnifAI Server Hosting PDF + DOCX."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "SERVER_IMPLEMENTATION.md"
PDF = ROOT / "docs" / "SERVER_IMPLEMENTATION.pdf"
DOCX = ROOT / "docs" / "SERVER_IMPLEMENTATION.docx"

BRAND = colors.HexColor("#0f172a")
ACCENT = colors.HexColor("#2563eb")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#e2e8f0")
ALT = colors.HexColor("#f8fafc")
CODE_BG = colors.HexColor("#f1f5f9")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<font face='Courier' size='8'>\1</font>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


def parse(text: str):
    lines = text.splitlines()
    i, blocks = 0, []
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", buf))
            continue
        if line.strip() == "---":
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if all(set(c) <= set("-: ") and c for c in cells):
                    i += 1
                    continue
                rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
            continue
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if line.startswith("That is all") or line.startswith("End of"):
            blocks.append(("end", line.strip()))
            i += 1
            continue
        blocks.append(("p", line.strip()))
        i += 1
    return blocks


def styles():
    b = getSampleStyleSheet()
    return {
        "cover": ParagraphStyle(
            "cover", parent=b["Title"], fontSize=26, leading=32, textColor=BRAND,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "h2": ParagraphStyle(
            "h2", parent=b["Heading2"], fontSize=12, leading=15, textColor=BRAND,
            spaceBefore=0, spaceAfter=6, fontName="Helvetica-Bold", keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "h3", parent=b["Heading3"], fontSize=10.5, leading=13,
            textColor=colors.HexColor("#334155"), spaceBefore=6, spaceAfter=4,
            fontName="Helvetica-Bold", keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body", parent=b["BodyText"], fontSize=9.5, leading=14, spaceAfter=6,
            textColor=colors.HexColor("#1e293b"),
        ),
        "code": ParagraphStyle(
            "code", parent=b["Code"], fontName="Courier-Bold", fontSize=9, leading=13,
            textColor=colors.HexColor("#dc2626"),
            backColor=None,
            borderPadding=0,
            spaceBefore=6,
            spaceAfter=8,
            leftIndent=8,
        ),
        "cell": ParagraphStyle("cell", parent=b["Normal"], fontSize=8.5, leading=11,
                               textColor=colors.HexColor("#0f172a")),
        "cell_h": ParagraphStyle(
            "cell_h", parent=b["Normal"], fontSize=8.5, leading=11,
            textColor=colors.white, fontName="Helvetica-Bold",
        ),
        "end": ParagraphStyle(
            "end", parent=b["Normal"], fontSize=9, textColor=MUTED,
            alignment=TA_CENTER, spaceBefore=10,
        ),
    }


def make_table(rows, st):
    n = max(len(r) for r in rows)
    total = 170 * mm
    if n == 2:
        widths = [total * 0.34, total * 0.66]
    elif n == 3:
        widths = [total * 0.28, total * 0.36, total * 0.36]
    else:
        widths = [total / n] * n
    data = []
    for ri, row in enumerate(rows):
        style = st["cell_h"] if ri == 0 else st["cell"]
        data.append([Paragraph(md(c), style) for c in (row + [""] * n)[:n]])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def flow_item(kind, data, st):
    if kind == "h3":
        return [Paragraph(md(data), st["h3"]), Spacer(1, 2 * mm)]
    if kind == "p":
        return [Paragraph(md(data), st["body"])]
    if kind == "code":
        # No gray box — dark clear monospace only
        lines = "<br/>".join(esc(x).replace(" ", "&nbsp;") for x in data)
        return [
            Spacer(1, 2 * mm),
            Paragraph(f'<font color="#dc2626" face="Courier" size="9"><b>{lines}</b></font>', st["code"]),
            Spacer(1, 3 * mm),
        ]
    if kind == "table":
        return [Spacer(1, 2 * mm), make_table(data, st), Spacer(1, 4 * mm)]
    if kind == "end":
        return [Spacer(1, 3 * mm), Paragraph(md(data), st["end"])]
    return []


def build_story(blocks, st):
    story = []
    story.append(Spacer(1, 95 * mm))
    story.append(Paragraph("UnifAI Server Hosting", st["cover"]))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="28%", thickness=2, color=ACCENT, hAlign="CENTER"))
    story.append(PageBreak())

    section: list = []

    def flush():
        nonlocal section
        if not section:
            return
        if len(section) <= 3:
            story.append(KeepTogether(section))
        else:
            story.append(KeepTogether(section[:3]))
            story.extend(section[3:])
        story.append(Spacer(1, 7 * mm))
        section = []

    for kind, data in blocks:
        if kind == "h1":
            continue
        if kind == "h2":
            flush()
            section = [
                Paragraph(md(data), st["h2"]),
                HRFlowable(width="100%", thickness=0.45, color=LINE, spaceAfter=6),
            ]
            continue
        section.extend(flow_item(kind, data, st))
    flush()
    return story


def footer(c, doc):
    if doc.page == 1:
        return
    c.saveState()
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(16 * mm, 7 * mm, "UnifAI Server Hosting")
    c.drawRightString(A4[0] - 16 * mm, 7 * mm, f"Page {doc.page}")
    c.restoreState()


def build_pdf(blocks):
    st = styles()
    SimpleDocTemplate(
        str(PDF),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="UnifAI Server Hosting",
    ).build(build_story(blocks, st), onFirstPage=footer, onLaterPages=footer)


def set_run(run, size=10, bold=False, color=None, name="Calibri"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color


def build_docx(blocks):
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    for _ in range(10):
        doc.add_paragraph("")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("UnifAI Server Hosting")
    set_run(r, size=28, bold=True, color=RGBColor(15, 23, 42))
    doc.add_page_break()

    for kind, data in blocks:
        if kind == "h1":
            continue
        clean = re.sub(r"[*`]", "", data if isinstance(data, str) else "")
        if kind == "h2":
            doc.add_heading(clean, level=1)
        elif kind == "h3":
            doc.add_heading(clean, level=2)
        elif kind == "p":
            p = doc.add_paragraph(clean)
            for run in p.runs:
                set_run(run, size=10)
        elif kind == "code":
            p = doc.add_paragraph("\n".join(data))
            for run in p.runs:
                set_run(run, size=8, name="Consolas")
        elif kind == "table":
            n = max(len(r) for r in data)
            t = doc.add_table(rows=len(data), cols=n)
            t.style = "Table Grid"
            for ri, row in enumerate(data):
                for ci in range(n):
                    t.cell(ri, ci).text = re.sub(r"[*`]", "", row[ci] if ci < len(row) else "")
            doc.add_paragraph("")
        elif kind == "end":
            p = doc.add_paragraph(clean)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.save(str(DOCX))


def main():
    blocks = parse(MD.read_text(encoding="utf-8"))
    build_pdf(blocks)
    build_docx(blocks)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"ok PDF={PDF.stat().st_size} DOCX={DOCX.stat().st_size}")


if __name__ == "__main__":
    main()
