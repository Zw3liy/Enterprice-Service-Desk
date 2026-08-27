from django.urls import path

from apps.service_desk.views.sla import (
    SLAPolicyListView,
    SLAPolicyCreateView,
    SLABreachListView,
)

app_name = "sla"

urlpatterns = [
    path(
        "policies/",
        SLAPolicyListView.as_view(),
        name="policy_list",
    ),
    path(
        "policies/new/",
        SLAPolicyCreateView.as_view(),
        name="policy_create",
    ),
    path(
        "breaches/",
        SLABreachListView.as_view(),
        name="breach_list",
    ),
]
