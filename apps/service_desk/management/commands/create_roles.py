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

from apps.service_desk.models import (
    CatalogItem,
    Problem,
    ServiceRequest,
    SLAPolicy,
    Supplier,
    Ticket,
)



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

        sla_policy_content_type = ContentType.objects.get_for_model(
            SLAPolicy
        )

        catalog_item_content_type = ContentType.objects.get_for_model(
            CatalogItem
        )

        service_request_content_type = ContentType.objects.get_for_model(
            ServiceRequest
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

            # SLA policy administration. Technicians work *under* the
            # SLA (they see their tickets' clocks through the scoped
            # SLA dashboard, which only needs view_ticket) but do not
            # get to change the targets they are measured against.
            "view_slapolicy": Permission.objects.get(
                content_type=sla_policy_content_type,
                codename="view_slapolicy",
            ),

            "add_slapolicy": Permission.objects.get(
                content_type=sla_policy_content_type,
                codename="add_slapolicy",
            ),

            "change_slapolicy": Permission.objects.get(
                content_type=sla_policy_content_type,
                codename="change_slapolicy",
            ),

            "delete_slapolicy": Permission.objects.get(
                content_type=sla_policy_content_type,
                codename="delete_slapolicy",
            ),

            # Service Catalogue. Everyone may browse (view_catalogitem);
            # only Manager/Administrator administer items. Requesters
            # may submit requests (add_servicerequest); Technician/
            # Manager/Administrator may act on the workflow
            # (change_servicerequest) — see security.policies.
            # get_service_request_queryset for the object-level scope
            # this permission operates within.
            "view_catalogitem": Permission.objects.get(
                content_type=catalog_item_content_type,
                codename="view_catalogitem",
            ),

            "add_catalogitem": Permission.objects.get(
                content_type=catalog_item_content_type,
                codename="add_catalogitem",
            ),

            "change_catalogitem": Permission.objects.get(
                content_type=catalog_item_content_type,
                codename="change_catalogitem",
            ),

            "delete_catalogitem": Permission.objects.get(
                content_type=catalog_item_content_type,
                codename="delete_catalogitem",
            ),

            "view_servicerequest": Permission.objects.get(
                content_type=service_request_content_type,
                codename="view_servicerequest",
            ),

            "add_servicerequest": Permission.objects.get(
                content_type=service_request_content_type,
                codename="add_servicerequest",
            ),

            "change_servicerequest": Permission.objects.get(
                content_type=service_request_content_type,
                codename="change_servicerequest",
            ),

            "delete_servicerequest": Permission.objects.get(
                content_type=service_request_content_type,
                codename="delete_servicerequest",
            ),
        }


        roles = {

            # Requesters get no Problem permissions at all — ADR-010,
            # Decision 1: Requesters cannot access Problem records.
            "Requester": [
                permissions["view"],
                permissions["add"],
                permissions["view_catalogitem"],
                permissions["add_servicerequest"],
                permissions["view_servicerequest"],
            ],


            # Technicians may open tickets on behalf of end users
            # (phone/walk-up intake) in addition to working assigned ones.
            "Technician": [
                permissions["view"],
                permissions["add"],
                permissions["change"],
                permissions["view_problem"],
                permissions["add_problem"],
                permissions["change_problem"],
                permissions["view_catalogitem"],
                permissions["view_servicerequest"],
                permissions["change_servicerequest"],
            ],


            # Managers inherit technician ticket powers plus supplier/SLA
            # administration for the departments they manage.
            "Manager": [
                permissions["view"],
                permissions["add"],
                permissions["change"],
                permissions["view_problem"],
                permissions["add_problem"],
                permissions["change_problem"],
                permissions["view_supplier"],
                permissions["add_supplier"],
                permissions["change_supplier"],
                permissions["view_slapolicy"],
                permissions["add_slapolicy"],
                permissions["change_slapolicy"],
                permissions["view_catalogitem"],
                permissions["add_catalogitem"],
                permissions["change_catalogitem"],
                permissions["view_servicerequest"],
                permissions["change_servicerequest"],
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
                permissions["view_slapolicy"],
                permissions["add_slapolicy"],
                permissions["change_slapolicy"],
                permissions["delete_slapolicy"],
                permissions["view_catalogitem"],
                permissions["add_catalogitem"],
                permissions["change_catalogitem"],
                permissions["delete_catalogitem"],
                permissions["view_servicerequest"],
                permissions["add_servicerequest"],
                permissions["change_servicerequest"],
                permissions["delete_servicerequest"],
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