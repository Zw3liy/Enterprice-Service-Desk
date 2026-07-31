from rest_framework.permissions import IsAuthenticated


class IsForecastViewer(IsAuthenticated):
    pass
