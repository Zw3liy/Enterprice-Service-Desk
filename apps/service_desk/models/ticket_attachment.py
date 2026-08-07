from django.conf import settings
from django.db import models
from django.utils import timezone

from .ticket import Ticket


class TicketAttachment(models.Model):
    """
    File attachment linked to a ticket.

    Each attachment records who uploaded it and when, enabling
    per-file audit metadata. Upload and download are scoped
    through the same RBAC policy as the parent ticket
    (see ADR-010, Decision 3).
    """

    # Conservative allowlist — executable/script extensions rejected.
    ALLOWED_EXTENSIONS = frozenset({
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "txt", "csv", "rtf", "odt", "ods", "odp",
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg",
        "zip", "rar", "7z",
        "mp4", "mp3", "wav",
        "md", "html", "json", "xml",
    })

    # 10 MB cap
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="ticket_attachments/%Y/%m/",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_attachments",
    )

    uploaded_at = models.DateTimeField(
        default=timezone.now,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Ticket Attachment"
        verbose_name_plural = "Ticket Attachments"
        indexes = [
            models.Index(fields=["ticket", "uploaded_at"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return f"{self.original_filename or self.file.name} (Ticket #{self.ticket_id})"
