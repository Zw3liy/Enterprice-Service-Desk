"""
Enterprise Service Desk
RBAC Role Bootstrap

Creates standard Django Groups and assigns
service desk permissions.

Usage:

python manage.py create_roles

"""

from django.core.management.base import BaseCommand

from django.contrib.auth.models import (
    Group,
    Permission,
)

from django.contrib.contenttypes.models import ContentType

from apps.service_desk.models import Ticket



class Command(BaseCommand):

    help = "Create Enterprise Service Desk RBAC roles"


    def handle(self, *args, **options):

        ticket_content_type = ContentType.objects.get_for_model(
            Ticket
        )


        permissions = {
            "view": Permission.objects.get(
                content_type=ticket_content_type,
                codename="view_ticket",
            ),

            "add": Permission.objects.get(
                content_type=ticket_content_type,
                codename="add_ticket",
            ),

            "change": Permission.objects.get(
                content_type=ticket_content_type,
                codename="change_ticket",
            ),

            "delete": Permission.objects.get(
                content_type=ticket_content_type,
                codename="delete_ticket",
            ),
        }


        roles = {

            "Requester": [
                permissions["view"],
                permissions["add"],
            ],


            "Technician": [
                permissions["view"],
                permissions["change"],
            ],


            "Manager": [
                permissions["view"],
                permissions["change"],
            ],


            "Administrator": [
                permissions["view"],
                permissions["add"],
                permissions["change"],
                permissions["delete"],
            ],

        }


        for role, perms in roles.items():

            group, created = Group.objects.get_or_create(
                name=role
            )


            group.permissions.set(
                perms
            )


            group.save()


            status = "created" if created else "updated"


            self.stdout.write(
                self.style.SUCCESS(
                    f"{role}: {status}"
                )
            )


        self.stdout.write(
            self.style.SUCCESS(
                "RBAC bootstrap completed successfully."
            )
        )