from django.urls import path

from apps.ai_engine import views

app_name = "ai_engine"

urlpatterns = [
    path("assistant/", views.assistant, name="assistant"),
    path("api/copilot/", views.CopilotAPI.as_view(), name="api-copilot"),
    path("api/classify/", views.ClassifyAPI.as_view(), name="api-classify"),
    path("api/conversations/<int:pk>/", views.ConversationDetailAPI.as_view(), name="api-conversation"),
    path("api/logs/", views.AIRequestLogAPI.as_view(), name="api-logs"),
]