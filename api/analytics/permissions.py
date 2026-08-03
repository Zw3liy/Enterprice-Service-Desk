from rest_framework.permissions import IsAuthenticated


class IsAnalyticsViewer(IsAuthenticated):
    pass
