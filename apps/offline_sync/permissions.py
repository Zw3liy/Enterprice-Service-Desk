from rest_framework.permissions import IsAuthenticated


class IsSyncClient(IsAuthenticated):
    pass
