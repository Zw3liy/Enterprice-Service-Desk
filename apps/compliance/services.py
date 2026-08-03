from __future__ import annotations

from django.db.models import Count
from django.utils.text import slugify

from apps.compliance.models import ComplianceEvidence, Control, ControlFramework


class ComplianceService:
    @staticmethod
    def ensure_iso27001(company) -> ControlFramework:
        fw, _ = ControlFramework.objects.get_or_create(
            company=company,
            code="iso27001",
            defaults={
                "name": "ISO/IEC 27001",
                "description": "Information security management controls",
                "version": "2022",
            },
        )
        defaults = [
            ("A.5.1", "Policies for information security"),
            ("A.5.15", "Access control"),
            ("A.5.24", "Information security incident management planning"),
            ("A.8.8", "Management of technical vulnerabilities"),
            ("A.8.15", "Logging"),
        ]
        for cid, title in defaults:
            Control.objects.get_or_create(
                framework=fw, control_id=cid, defaults={"title": title}
            )
        return fw

    @staticmethod
    def scorecard(framework: ControlFramework) -> dict:
        total = framework.controls.count()
        by_status = {
            row["status"]: row["c"]
            for row in framework.controls.values("status").annotate(c=Count("id"))
        }
        compliant = by_status.get(Control.Status.COMPLIANT, 0)
        return {
            "total": total,
            "by_status": by_status,
            "compliance_pct": round((compliant / total) * 100, 1) if total else 0.0,
        }

    @staticmethod
    def add_evidence(control: Control, *, title: str, description: str = "", url: str = "", user=None):
        return ComplianceEvidence.objects.create(
            control=control,
            title=title,
            description=description,
            url=url,
            collected_by=user,
        )

    @staticmethod
    def set_status(control: Control, status: str) -> Control:
        control.status = status
        control.save(update_fields=["status", "updated_at"])
        return control
