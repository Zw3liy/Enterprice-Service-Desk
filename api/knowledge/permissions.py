from rest_framework.permissions import IsAuthenticated


class IsKnowledgeReader(IsAuthenticated):
    pass
