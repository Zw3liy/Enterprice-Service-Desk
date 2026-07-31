from rest_framework.permissions import IsAuthenticated


class IsEventReader(IsAuthenticated):
    pass
