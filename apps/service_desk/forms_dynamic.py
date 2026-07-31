from django import forms



def build_dynamic_form(request_type):


    fields = {}


    for custom in request_type.custom_fields.all():


        if custom.field_type == "text":

            fields[custom.name] = forms.CharField()


        elif custom.field_type == "number":

            fields[custom.name] = forms.IntegerField()


        elif custom.field_type == "dropdown":

            fields[custom.name] = forms.ChoiceField(

                choices=[
                    (x,x)
                    for x in custom.options
                ]

            )


        elif custom.field_type == "date":

            fields[custom.name] = forms.DateField()


        elif custom.field_type == "boolean":

            fields[custom.name] = forms.BooleanField(
                required=False
            )


        if custom.is_required:

            fields[custom.name].required=True



    return type(
        "DynamicTicketForm",
        (forms.Form,),
        fields
    )