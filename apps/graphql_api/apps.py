from django.apps import AppConfig


class GraphQLAPIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.graphql_api"
    label = "graphql_api"
    verbose_name = "GraphQL API"