"""
Reporting and analytics support: safe CSV export and date-range
parsing shared by every export/dashboard view in reporting_views.py.

Every report and export in this module reads through the same
RBAC-scoped queryset functions the rest of the application uses
(get_ticket_queryset, get_change_queryset, ...) — there is no
separate, wider "reporting" data path. This file only adds the two
concerns unique to reporting: CSV formula-injection safety and
bounded, streamed export.
"""

from __future__ import annotations

import csv
import datetime

from django.http import StreamingHttpResponse
from django.utils import timezone

# Leading characters a spreadsheet application (Excel, Google Sheets,
# LibreOffice) will interpret as the start of a formula if a CSV cell
# is opened directly — the classic CSV/formula injection vector.
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value) -> str:
    """
    Neutralise spreadsheet-formula injection in one CSV cell.

    A cell whose text begins with any of ``_FORMULA_TRIGGER_CHARS``
    is prefixed with a single quote, which every major spreadsheet
    application treats as "force plain text" and never renders in
    the resulting cell — the OWASP-recommended mitigation for CSV
    injection.
    """

    text = "" if value is None else str(value)

    if text.startswith(_FORMULA_TRIGGER_CHARS):
        return "'" + text

    return text


class _EchoBuffer:
    """A write-only, in-memory-free target for csv.writer, per the
    Django-documented streaming CSV pattern — each write just returns
    the string handed to it, which StreamingHttpResponse then flushes
    to the client immediately rather than buffering the whole file.
    """

    def write(self, value):
        return value


def stream_csv(filename: str, header: list, rows) -> StreamingHttpResponse:
    """
    Stream a CSV file without materialising it in memory.

    ``rows`` must be an iterable of iterables (e.g. a queryset
    ``.values_list()`` call, or a generator) — every cell is passed
    through ``sanitize_csv_cell`` before being written. Streaming
    (rather than building a list of rows first) is what keeps a large
    export from being an unbounded-memory operation.
    """

    writer = csv.writer(_EchoBuffer())

    def generate():
        yield writer.writerow(header)
        for row in rows:
            yield writer.writerow(sanitize_csv_cell(cell) for cell in row)

    response = StreamingHttpResponse(generate(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def parse_date_range(request):
    """
    Parse ``date_from``/``date_to`` query params (YYYY-MM-DD) into a
    ``(start, end)`` tuple of timezone-aware datetimes, or ``None``
    for either side that is absent or unparsable. ``end`` is bumped
    to the end of that calendar day so a same-day range is inclusive.
    """

    def _parse(value):
        if not value:
            return None
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    start_date = _parse(request.GET.get("date_from", ""))
    end_date = _parse(request.GET.get("date_to", ""))

    tz = timezone.get_current_timezone()

    start = (
        timezone.make_aware(
            datetime.datetime.combine(start_date, datetime.time.min), tz
        )
        if start_date
        else None
    )
    end = (
        timezone.make_aware(
            datetime.datetime.combine(end_date, datetime.time.max), tz
        )
        if end_date
        else None
    )

    return start, end
