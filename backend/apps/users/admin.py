from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import Role, User, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "phone", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("BuzUp", {"fields": ("phone",)}),
    )
    inlines = [UserRoleInline]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system", "created_at")
    list_filter = ("is_system",)
    search_fields = ("name", "code")
