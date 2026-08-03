from django.urls import path

from apps.service_desk import views

urlpatterns = [
    path("", views.asset_list, name="cmdb_asset_list"),
    path("new/", views.asset_create, name="cmdb_asset_create"),
    path("<int:pk>/", views.asset_detail, name="cmdb_asset_detail"),
]
