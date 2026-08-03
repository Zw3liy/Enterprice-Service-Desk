from django.urls import path

from apps.service_desk import views

urlpatterns = [
    path("", views.knowledge_list, name="kb_list"),
    path("new/", views.knowledge_create, name="kb_create"),
    path("<slug:slug>/", views.knowledge_detail, name="kb_detail"),
]
