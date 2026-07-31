def validate_custom_fields(
        request_type,
        values
):

    errors = {}

    for field in request_type.custom_fields.all():

        value = values.get(field.name)


        if field.is_required and not value:

            errors[field.name] = (
                "This field is required."
            )


    return errors