from rest_framework.permissions import IsAuthenticated


class IsITILUser(IsAuthenticated):
    pass
