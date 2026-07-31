from rest_framework.permissions import IsAuthenticated


class IsChatbotUser(IsAuthenticated):
    pass
