from django.urls import path

from api.itil.views import ITILIndexAPI

urlpatterns = [
    path("", ITILIndexAPI.as_view(), name="api-itil-index"),
]
