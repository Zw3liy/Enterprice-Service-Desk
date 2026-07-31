from rest_framework.permissions import IsAuthenticated


class IsMonitoringIngest(IsAuthenticated):
    pass
