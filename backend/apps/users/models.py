from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel, active_unique_constraint
from apps.core.models.base import SoftDeleteAllManager
from apps.users.managers import UserManager


class Role(BaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=32, db_index=True)
    permissions = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)
        constraints = [
            active_unique_constraint("code", name="uq_role_code_active"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not str(self.code or "").strip():
            from apps.core.utils import generate_code_from_name
            self.code = generate_code_from_name(
                self.name,
                "",
                Role,
                "code",
                instance=self,
                separator="_",
                uppercase=False,
            )
        super().save(*args, **kwargs)


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    user_roles = models.ManyToManyField(Role, through="UserRole", blank=True, related_name="users")

    objects = UserManager()
    all_objects = SoftDeleteAllManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ("username",)

    def __str__(self):
        return self.get_full_name() or self.username

    def get_capabilities(self):
        if self.is_superuser:
            return ["*"]
        caps = set()
        for role in self.user_roles.all():
            for perm in (role.permissions or []):
                caps.add(perm)
        return list(caps)

    def get_soft_delete_updates(self):
        token = str(self.pk or self.uuid.hex[:8])
        username_prefix = f"deleted-{token}-"
        username_body = (self.username or "user")[: max(150 - len(username_prefix), 0)]
        email_value = f"deleted-{token}@deleted.local"
        return {
            "username": f"{username_prefix}{username_body}"[:150],
            "email": email_value[:254],
        }


class OtpChallenge(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        VERIFIED = "verified", "Verificado"
        EXPIRED = "expired", "Expirado"

    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["phone", "status"])]

    def __str__(self):
        return f"OTP {self.phone} [{self.status}]"


class UserRole(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_assignments")

    class Meta:
        constraints = [
            active_unique_constraint("user", "role", name="uq_user_role_active"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.role}"
