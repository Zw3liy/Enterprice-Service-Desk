from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.models import RoleDefinition, UserRoleAssignment
from apps.rbac.permissions import IsESDAdmin
from apps.rbac.serializers import (
    AssignRoleSerializer,
    RoleDefinitionSerializer,
    UserRoleAssignmentSerializer,
)
from apps.rbac.services import RBACService
from apps.service_desk.tenancy import get_active_company, require_company

User = get_user_model()


class RoleDefinitionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoleDefinitionSerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_active", "is_system")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = RoleDefinition.objects.all()
        if company:
            qs = qs.filter(company=company) | qs.filter(company__isnull=True)
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(company=require_company(self.request))


class UserRoleAssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsESDAdmin]
    serializer_class = UserRoleAssignmentSerializer
    filterset_fields = ("is_active", "role", "user")

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = UserRoleAssignment.objects.select_related("user", "role", "assigned_by")
        if company:
            qs = qs.filter(company=company)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            company=require_company(self.request),
            assigned_by=self.request.user,
        )


class RBACMeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        return Response(
            {
                "username": request.user.get_username(),
                "roles": RBACService.user_roles(request.user),
                "is_staff": request.user.is_staff,
                "company_id": company.pk if company else None,
            }
        )


class RBACAssignAPI(APIView):
    permission_classes = [IsAuthenticated, IsESDAdmin]

    def post(self, request):
        ser = AssignRoleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        user = get_object_or_404(User, pk=ser.validated_data["user_id"])
        role = RBACService.assign_role(
            user,
            ser.validated_data["role_code"],
            company=company,
            assigned_by=request.user,
        )
        if isinstance(role, RoleDefinition):
            return Response(RoleDefinitionSerializer(role).data, status=status.HTTP_201_CREATED)
        return Response({"role": ser.validated_data["role_code"], "group": role.name})


class RBACBootstrapAPI(APIView):
    permission_classes = [IsAuthenticated, IsESDAdmin]

    def post(self, request):
        company = require_company(request)
        RBACService.ensure_groups()
        roles = RBACService.ensure_role_definitions(company)
        return Response(
            {
                "roles_created": len(roles),
                "roles": RoleDefinitionSerializer(
                    RoleDefinition.objects.filter(company=company), many=True
                ).data,
            }
        )
