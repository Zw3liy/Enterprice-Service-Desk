from django.urls import path

from apps.ai_engine.views import ClassifyAPI, CopilotAPI

urlpatterns = [
    path("copilot/", CopilotAPI.as_view(), name="api-ai-gw-copilot"),
    path("classify/", ClassifyAPI.as_view(), name="api-ai-gw-classify"),
]
