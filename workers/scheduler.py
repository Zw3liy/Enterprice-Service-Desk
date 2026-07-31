"""Simple in-process scheduler hooks for SLA scans."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_sla_scan(company_id=None) -> int:
    from apps.service_desk.services.sla_service import SLAService

    count = SLAService.scan_open_tickets(company_id=company_id)
    logger.info("scheduled sla scan complete count=%s", count)
    return count
