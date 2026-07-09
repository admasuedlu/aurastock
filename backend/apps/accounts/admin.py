from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Permission, Role, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["username", "email", "company", "role", "is_active", "is_staff"]
    list_filter = ["company", "role", "is_active", "is_staff"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Tenant", {"fields": ("company", "branch", "role", "is_company_owner",
                                "phone", "preferred_language", "avatar")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "is_system"]
    list_filter = ["company", "is_system"]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "module", "description"]
    list_filter = ["module"]
