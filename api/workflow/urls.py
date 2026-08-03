from django.urls import path

from api.workflow.views import WorkflowTransitionAPI

urlpatterns = [
    path("transition/", WorkflowTransitionAPI.as_view(), name="api-workflow-transition"),
]
