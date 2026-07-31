from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ITILIndexAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "modules": ["incidents", "problems", "changes"],
                "paths": {
                    "incidents": "/incidents/api/",
                    "problems": "/problems/api/",
                    "changes": "/changes/api/",
                },
            }
        )
