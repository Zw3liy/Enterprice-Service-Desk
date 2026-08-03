from rest_framework.permissions import IsAuthenticated


class IsSearchUser(IsAuthenticated):
    pass
