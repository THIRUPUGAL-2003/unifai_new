#!/usr/bin/env python3
"""Generate PDF (+ optional DOCX) from UNIFAI_STATUS_ROADMAP.md"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "UNIFAI_STATUS_ROADMAP.md"
PDF = ROOT / "docs" / "UNIFAI_STATUS_ROADMAP.pdf"
DOCX = ROOT / "docs" / "UNIFAI_STATUS_ROADMAP.docx"


def md_to_flowables(text: str):
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1u", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    h2 = ParagraphStyle("H2u", parent=styles["Heading2"], fontSize=13, spaceAfter=6, spaceBefore=10)
    h3 = ParagraphStyle("H3u", parent=styles["Heading3"], fontSize=11, spaceAfter=4, spaceBefore=8)
    body = ParagraphStyle("Bodyu", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=3)
    code = ParagraphStyle("Codeu", parent=styles["Code"], fontSize=8, leading=10, spaceAfter=3)
    flow = []
    in_code = False
    code_buf: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                flow.append(Paragraph("<br/>".join(code_buf).replace(" ", "&nbsp;"), code))
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            continue
        if not line.strip():
            flow.append(Spacer(1, 4))
            continue
        esc = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("|", "&#124;")
        )
        if line.startswith("# "):
            flow.append(Paragraph(esc[2:], h1))
        elif line.startswith("## "):
            flow.append(Paragraph(esc[3:], h2))
        elif line.startswith("### "):
            flow.append(Paragraph(esc[4:], h3))
        elif line.startswith("- "):
            flow.append(Paragraph("• " + esc[2:], body))
        elif line.startswith("|"):
            flow.append(Paragraph(esc, body))
        else:
            flow.append(Paragraph(esc, body))
    return flow


def write_pdf() -> None:
    doc = SimpleDocTemplate(
        str(PDF),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="UnifAI Status Report & Roadmap",
    )
    doc.build(md_to_flowables(MD.read_text(encoding="utf-8")))
    print("wrote", PDF)


def write_docx() -> None:
    try:
        from docx import Document
    except ImportError:
        # Minimal Word-compatible HTML fallback renamed .doc via plain text
        out = ROOT / "docs" / "UNIFAI_STATUS_ROADMAP.doc"
        out.write_text(MD.read_text(encoding="utf-8"), encoding="utf-8")
        print("wrote_plain_doc", out)
        return
    document = Document()
    document.add_heading("UnifAI Status Report, Feature Map & Roadmap", 0)
    for line in MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            document.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            document.add_heading(line[4:], level=3)
        elif line.strip():
            document.add_paragraph(line)
    document.save(str(DOCX))
    print("wrote", DOCX)


if __name__ == "__main__":
    write_pdf()
    write_docx()
