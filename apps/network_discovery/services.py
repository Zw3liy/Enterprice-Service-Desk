"""Network discovery services.

Production environments should replace the simulator with nmap/masscan workers.
The public API stays stable.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.cmdb.services import CMDBService
from apps.network_discovery.models import DiscoveredHost, DiscoveryScan
from apps.service_desk.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class NetworkDiscoveryService:
    @classmethod
    @transaction.atomic
    def create_scan(
        cls, company, *, name: str, cidr: str, created_by=None
    ) -> DiscoveryScan:
        # validate CIDR
        ipaddress.ip_network(cidr, strict=False)
        return DiscoveryScan.objects.create(
            company=company,
            name=name,
            cidr=cidr,
            created_by=created_by,
        )

    @classmethod
    @transaction.atomic
    def run_scan(cls, scan: DiscoveryScan, hosts: Iterable[dict] | None = None) -> DiscoveryScan:
        scan.state = DiscoveryScan.State.RUNNING
        scan.started_at = timezone.now()
        scan.save(update_fields=["state", "started_at", "updated_at"])
        try:
            records = list(hosts) if hosts is not None else cls._simulate(scan.cidr)
            count = 0
            for item in records:
                DiscoveredHost.objects.update_or_create(
                    scan=scan,
                    ip_address=item["ip_address"],
                    defaults={
                        "company": scan.company,
                        "hostname": item.get("hostname") or "",
                        "mac_address": item.get("mac_address") or "",
                        "open_ports": item.get("open_ports") or [],
                        "os_guess": item.get("os_guess") or "",
                        "is_alive": item.get("is_alive", True),
                        "raw": item,
                    },
                )
                CMDBService.ingest_discovery(
                    scan.company,
                    {
                        "hostname": item.get("hostname") or item["ip_address"],
                        "ip_address": item["ip_address"],
                        "mac_address": item.get("mac_address") or "",
                        "os_name": item.get("os_guess") or "",
                    },
                    source=f"discovery:{scan.pk}",
                )
                count += 1
            scan.hosts_found = count
            scan.state = DiscoveryScan.State.COMPLETED
            scan.finished_at = timezone.now()
            scan.save(
                update_fields=["hosts_found", "state", "finished_at", "updated_at"]
            )
            AuditService.log(
                action="discovery.scan_completed",
                company=scan.company,
                actor=scan.created_by,
                message=f"Scan {scan.name} found {count} hosts",
                object_type="discovery_scan",
                object_id=str(scan.pk),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("discovery_scan_failed")
            scan.state = DiscoveryScan.State.FAILED
            scan.error_message = str(exc)
            scan.finished_at = timezone.now()
            scan.save(
                update_fields=["state", "error_message", "finished_at", "updated_at"]
            )
            raise
        return scan

    @staticmethod
    def _simulate(cidr: str) -> list[dict]:
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = []
        for idx, ip in enumerate(network.hosts()):
            if idx >= 5:
                break
            hosts.append(
                {
                    "ip_address": str(ip),
                    "hostname": f"host-{idx+1}.local",
                    "mac_address": f"02:00:00:00:00:{idx+1:02x}",
                    "open_ports": [22, 80, 443] if idx % 2 == 0 else [22],
                    "os_guess": "Linux" if idx % 2 == 0 else "Windows",
                    "is_alive": True,
                }
            )
        if not hosts:
            # single address /32
            hosts.append(
                {
                    "ip_address": str(network.network_address),
                    "hostname": "node-1.local",
                    "mac_address": "02:00:00:00:00:01",
                    "open_ports": [22],
                    "os_guess": "Linux",
                    "is_alive": True,
                }
            )
        return hosts
