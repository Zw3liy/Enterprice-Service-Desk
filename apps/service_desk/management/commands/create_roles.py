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

from apps.service_desk.models import Problem, Supplier, Ticket



class Command(BaseCommand):

    help = "Create Enterprise Service Desk RBAC roles"


    def handle(self, *args, **options):

        ticket_content_type = ContentType.objects.get_for_model(
            Ticket
        )

        problem_content_type = ContentType.objects.get_for_model(
            Problem
        )

        supplier_content_type = ContentType.objects.get_for_model(
            Supplier
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

            "view_problem": Permission.objects.get(
                content_type=problem_content_type,
                codename="view_problem",
            ),

            "add_problem": Permission.objects.get(
                content_type=problem_content_type,
                codename="add_problem",
            ),

            "change_problem": Permission.objects.get(
                content_type=problem_content_type,
                codename="change_problem",
            ),

            "delete_problem": Permission.objects.get(
                content_type=problem_content_type,
                codename="delete_problem",
            ),

            # Supplier Management (ITSM-08). Requesters and
            # Technicians get nothing: supplier records are
            # commercial data, scoped to Managers (own departments)
            # and Administrators (all) by
            # security.policies.get_supplier_queryset.
            "view_supplier": Permission.objects.get(
                content_type=supplier_content_type,
                codename="view_supplier",
            ),

            "add_supplier": Permission.objects.get(
                content_type=supplier_content_type,
                codename="add_supplier",
            ),

            "change_supplier": Permission.objects.get(
                content_type=supplier_content_type,
                codename="change_supplier",
            ),

            "delete_supplier": Permission.objects.get(
                content_type=supplier_content_type,
                codename="delete_supplier",
            ),
        }


        roles = {

            # Requesters get no Problem permissions at all — ADR-010,
            # Decision 1: Requesters cannot access Problem records.
            "Requester": [
                permissions["view"],
                permissions["add"],
            ],


            "Technician": [
                permissions["view"],
                permissions["change"],
                permissions["view_problem"],
                permissions["add_problem"],
                permissions["change_problem"],
            ],


            "Manager": [
                permissions["view"],
                permissions["change"],
                permissions["view_problem"],
                permissions["add_problem"],
                permissions["change_problem"],
                permissions["view_supplier"],
                permissions["add_supplier"],
                permissions["change_supplier"],
            ],


            "Administrator": [
                permissions["view"],
                permissions["add"],
                permissions["change"],
                permissions["delete"],
                permissions["view_problem"],
                permissions["add_problem"],
                permissions["change_problem"],
                permissions["delete_problem"],
                permissions["view_supplier"],
                permissions["add_supplier"],
                permissions["change_supplier"],
                permissions["delete_supplier"],
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