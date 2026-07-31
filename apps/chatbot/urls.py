from django.urls import path

from apps.chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("api/message/", views.ChatbotAPI.as_view(), name="api-message"),
]
