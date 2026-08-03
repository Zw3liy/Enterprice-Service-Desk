"""Inbound email → ticket ingestion."""

from __future__ import annotations

import email
import imaplib
import logging
import re
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from typing import Optional

from django.conf import settings

from apps.service_desk.models import Company, Ticket
from apps.service_desk.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


@dataclass
class InboundEmail:
    message_id: str
    subject: str
    body: str
    from_address: str
    to_addresses: list[str]


class EmailInboundService:
    # Matches [IT-2026-00001], [MAIL-CO-2026-00001], [ESD-2026-ab12cd34]
    TICKET_REF = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_-]*-\d{4}-[A-Za-z0-9]+)\]")

    @classmethod
    def parse_message(cls, raw: bytes | Message) -> InboundEmail:
        if isinstance(raw, bytes):
            msg = email.message_from_bytes(raw)
        else:
            msg = raw
        subject = cls._decode_header(msg.get("Subject", ""))
        from_addr = email.utils.parseaddr(msg.get("From", ""))[1]
        to_field = msg.get_all("To", [])
        to_addrs = []
        for item in to_field:
            to_addrs.extend([a for _, a in email.utils.getaddresses([item]) if a])
        body = cls._extract_body(msg)
        message_id = msg.get("Message-ID") or msg.get("Message-Id") or ""
        return InboundEmail(
            message_id=message_id.strip(),
            subject=subject.strip() or "(no subject)",
            body=body.strip(),
            from_address=from_addr,
            to_addresses=to_addrs,
        )

    @staticmethod
    def _decode_header(value: str) -> str:
        parts = decode_header(value or "")
        out = []
        for text, enc in parts:
            if isinstance(text, bytes):
                out.append(text.decode(enc or "utf-8", errors="replace"))
            else:
                out.append(text)
        return "".join(out)

    @staticmethod
    def _extract_body(msg: Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "")
                if ctype == "text/plain" and "attachment" not in disp:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
            return ""
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    @classmethod
    def ingest(
        cls,
        inbound: InboundEmail,
        *,
        company: Company,
        actor=None,
    ) -> Ticket:
        match = cls.TICKET_REF.search(inbound.subject)
        if match:
            existing = Ticket.objects.filter(
                company=company, ticket_number=match.group(1)
            ).first()
            if existing:
                TicketService.add_comment(
                    existing,
                    body=f"Email from {inbound.from_address}:\n\n{inbound.body}",
                    author=actor,
                    is_internal=False,
                )
                return existing
        return TicketService.create_ticket(
            title=inbound.subject[:240],
            description=f"From: {inbound.from_address}\n\n{inbound.body}",
            company=company,
            channel=Ticket.Channel.EMAIL,
            ticket_type=Ticket.TicketType.INCIDENT,
            actor=actor,
            run_ai=True,
            auto_assign=True,
        )

    @classmethod
    def poll_imap(
        cls,
        *,
        company: Company,
        host: str,
        username: str,
        password: str,
        mailbox: str = "INBOX",
        limit: int = 20,
        actor=None,
    ) -> list[Ticket]:
        tickets: list[Ticket] = []
        conn = imaplib.IMAP4_SSL(host)
        try:
            conn.login(username, password)
            conn.select(mailbox)
            _, data = conn.search(None, "UNSEEN")
            ids = (data[0] or b"").split()
            for num in ids[-limit:]:
                _, msg_data = conn.fetch(num, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                inbound = cls.parse_message(raw)
                ticket = cls.ingest(inbound, company=company, actor=actor)
                tickets.append(ticket)
                conn.store(num, "+FLAGS", "\\Seen")
        finally:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001
                pass
        logger.info("imap_poll company=%s created_or_updated=%s", company.slug, len(tickets))
        return tickets


def settings_imap_config() -> Optional[dict]:
    host = getattr(settings, "EMAIL_IMAP_HOST", "") or ""
    if not host:
        return None
    return {
        "host": host,
        "username": getattr(settings, "EMAIL_IMAP_USER", "") or "",
        "password": getattr(settings, "EMAIL_IMAP_PASSWORD", "") or "",
        "mailbox": getattr(settings, "EMAIL_IMAP_MAILBOX", "INBOX") or "INBOX",
    }
