"""Excel export using openpyxl when available; CSV fallback otherwise."""

from __future__ import annotations

from io import BytesIO

from apps.service_desk.reporting.exports import tickets_csv


def tickets_excel(queryset=None) -> bytes:
    csv_text = tickets_csv(queryset)
    try:
        from openpyxl import Workbook
    except ImportError:
        return csv_text.encode("utf-8")

    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"
    for row in csv_text.splitlines():
        # naive CSV split sufficient for our exporter (no embedded commas in fields currently critical)
        ws.append(next(csv_row_parser(row)))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def csv_row_parser(row: str):
    import csv
    from io import StringIO

    yield from csv.reader(StringIO(row))
