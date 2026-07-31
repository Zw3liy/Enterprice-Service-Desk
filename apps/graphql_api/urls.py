from django.urls import path

from apps.graphql_api.views import GraphQLAPI

app_name = "graphql_api"

urlpatterns = [
    path("", GraphQLAPI.as_view(), name="graphql"),
]
