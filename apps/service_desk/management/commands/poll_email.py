"""Poll IMAP mailbox and create/update tickets."""

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.email_inbound import EmailInboundService, settings_imap_config
from apps.service_desk.models import Company


class Command(BaseCommand):
    help = "Poll configured IMAP mailbox for new support emails."

    def add_arguments(self, parser):
        parser.add_argument("--company-slug", default="default")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        cfg = settings_imap_config()
        if not cfg or not cfg.get("host"):
            raise CommandError(
                "EMAIL_IMAP_HOST / EMAIL_IMAP_USER / EMAIL_IMAP_PASSWORD are not configured"
            )
        company = Company.objects.filter(slug=options["company_slug"]).first()
        if company is None:
            raise CommandError("Company not found")
        tickets = EmailInboundService.poll_imap(
            company=company,
            host=cfg["host"],
            username=cfg["username"],
            password=cfg["password"],
            mailbox=cfg.get("mailbox") or "INBOX",
            limit=options["limit"],
        )
        self.stdout.write(self.style.SUCCESS(f"Processed {len(tickets)} message(s)"))
