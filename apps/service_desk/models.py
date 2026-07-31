from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone


# =====================================================
# DEPARTMENT
# =====================================================

class Department(models.Model):

    name = models.CharField(
        max_length=100
    )

    code = models.CharField(
        max_length=10,
        unique=True
    )

    ticket_counter = models.PositiveIntegerField(
        default=0
    )


    class Meta:
        ordering = ["name"]


    def __str__(self):
        return self.name



# =====================================================
# REQUEST TYPE
# =====================================================

class RequestType(models.Model):

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="request_types"
    )

    name = models.CharField(
        max_length=150
    )


    description = models.TextField(
        blank=True
    )


    is_active = models.BooleanField(
        default=True
    )


    def __str__(self):
        return self.name



# =====================================================
# CUSTOM FIELD
# =====================================================

class CustomField(models.Model):

    FIELD_TYPES = [

        ("text", "Text"),

        ("number", "Number"),

        ("dropdown", "Dropdown"),

        ("date", "Date"),

        ("boolean", "Boolean"),

    ]


    request_type = models.ForeignKey(

        RequestType,

        on_delete=models.CASCADE,

        related_name="custom_fields"

    )


    name = models.CharField(
        max_length=100
    )


    field_type = models.CharField(

        max_length=20,

        choices=FIELD_TYPES

    )


    options = models.JSONField(
        default=list,
        blank=True
    )


    is_required = models.BooleanField(
        default=False
    )


    def __str__(self):

        return self.name



# =====================================================
# TICKET
# =====================================================

class Ticket(models.Model):


    title = models.CharField(
        max_length=200
    )


    description = models.TextField()


    requester = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        related_name="tickets"

    )


    department = models.ForeignKey(

        Department,

        on_delete=models.PROTECT,

        related_name="tickets"

    )


    request_type = models.ForeignKey(
    RequestType,
    on_delete=models.PROTECT,
    related_name="tickets",
    null=True,
    blank=True,
)


    ticket_number = models.CharField(

        max_length=50,

        unique=True,

        blank=True

    )


    custom_field_values = models.JSONField(

        default=dict,

        blank=True

    )


    created_at = models.DateTimeField(

        auto_now_add=True

    )


    def generate_ticket_number(self):

        year = timezone.now().year


        department = (
            Department.objects
            .select_for_update()
            .get(pk=self.department.pk)
        )


        department.ticket_counter += 1

        department.save(
            update_fields=[
                "ticket_counter"
            ]
        )


        return (
            f"{department.code}-"
            f"{year}-"
            f"{department.ticket_counter:04d}"
        )



    def save(self,*args,**kwargs):

        if not self.ticket_number:

            with transaction.atomic():

                self.ticket_number = (
                    self.generate_ticket_number()
                )

                super().save(
                    *args,
                    **kwargs
                )

        else:

            super().save(
                *args,
                **kwargs
            )


    def __str__(self):

        return self.ticket_number or self.title