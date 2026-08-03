from rest_framework.permissions import IsAuthenticated


class IsAIUser(IsAuthenticated):
    pass
