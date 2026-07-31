from rest_framework.permissions import IsAuthenticated


class IsMFAOwner(IsAuthenticated):
    pass