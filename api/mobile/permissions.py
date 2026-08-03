from rest_framework.permissions import IsAuthenticated


class IsMobileUser(IsAuthenticated):
    pass
