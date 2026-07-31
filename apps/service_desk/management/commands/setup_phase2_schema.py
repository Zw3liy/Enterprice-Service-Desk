from django.core.management.base import BaseCommand

from service_desk.models import (
    Department,
    RequestType,
    CustomField
)



class Command(BaseCommand):

    help = (
        "Create Phase 2 Enterprise Service Desk schema data"
    )


    def handle(self,*args,**kwargs):


        it, _ = Department.objects.get_or_create(

            name="Information Technology",

            code="IT"

        )


        hr, _ = Department.objects.get_or_create(

            name="Human Resources",

            code="HR"

        )


        incident, _ = RequestType.objects.get_or_create(

            department=it,

            name="IT Incident"

        )


        CustomField.objects.get_or_create(

            request_type=incident,

            name="Device Type",

            field_type="dropdown",

            options=[
                "Laptop",
                "Desktop",
                "Printer"
            ],

            is_required=True

        )


        CustomField.objects.get_or_create(

            request_type=incident,

            name="Asset Number",

            field_type="text",

            is_required=False

        )


        self.stdout.write(

            self.style.SUCCESS(

                "Phase 2 schema initialized"

            )

        )