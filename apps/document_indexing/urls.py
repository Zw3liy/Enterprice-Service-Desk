from django.urls import path

from apps.document_indexing import views

app_name = "document_indexing"

urlpatterns = [
    path("api/search/", views.DocumentSearchAPI.as_view(), name="api-search"),
    path("api/reindex/", views.DocumentReindexAPI.as_view(), name="api-reindex"),
]
