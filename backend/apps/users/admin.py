from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import PortalLoginChallenge, Role, User, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "phone", "is_2fa_enabled", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_2fa_enabled")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("BuzUp", {"fields": ("phone", "is_2fa_enabled")}),
    )
    inlines = [UserRoleInline]

    def get_readonly_fields(self, request, obj=None):
        """Desligar o segundo factor e um acto de superadministrador.

        Sem isto, qualquer conta com acesso ao painel e permissao de alterar
        utilizadores podia desligar o 2FA — a si propria ou a outros — e a
        proteccao passava a valer o que vale o elo mais fraco.
        """
        campos = tuple(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            campos += ("is_2fa_enabled",)
        return campos


@admin.register(PortalLoginChallenge)
class PortalLoginChallengeAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "phone", "failed_attempts", "expires_at", "consumed_at", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "phone")
    # O hash do codigo nunca se edita: e a prova de que o codigo foi aquele.
    readonly_fields = ("uuid", "user", "code_hash", "phone", "expires_at",
                       "consumed_at", "failed_attempts", "ip_address", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system", "created_at")
    list_filter = ("is_system",)
    search_fields = ("name", "code")
