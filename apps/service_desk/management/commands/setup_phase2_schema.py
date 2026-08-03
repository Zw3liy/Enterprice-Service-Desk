"""Compatibility wrapper — delegates to bootstrap_esd."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Legacy alias for bootstrap_esd."

    def handle(self, *args, **options):
        call_command("bootstrap_esd", with_demo=True)
