"""Minimal PDF export for KPI summary (reportlab optional)."""

from __future__ import annotations


def kpi_pdf(summary: dict) -> bytes:
    lines = ["Enterprise Service Desk — KPI Report", ""]
    for key in (
        "total_tickets",
        "open_tickets",
        "resolved_tickets",
        "breached_tickets",
        "sla_compliance_pct",
        "avg_csat",
    ):
        lines.append(f"{key}: {summary.get(key)}")
    text = "\n".join(lines)
    try:
        from io import BytesIO

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        y = 800
        for line in lines:
            c.drawString(50, y, line[:100])
            y -= 16
        c.save()
        return buf.getvalue()
    except Exception:
        return text.encode("utf-8")
