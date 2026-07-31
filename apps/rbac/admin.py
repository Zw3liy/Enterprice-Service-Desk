from django.contrib import admin

from apps.rbac.models import RoleDefinition, UserRoleAssignment


@admin.register(RoleDefinition)
class RoleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "company", "is_system", "is_active")
    list_filter = ("is_system", "is_active", "company")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "company", "is_active", "assigned_by", "created_at")
    list_filter = ("is_active", "company", "role")
    search_fields = ("user__username", "role__code")
    raw_id_fields = ("user", "role", "company", "assigned_by")
