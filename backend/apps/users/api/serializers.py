from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import Role, User, UserRole


class BuzUpTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["name"] = user.get_full_name() or user.username
        token["capabilities"] = user.get_capabilities()
        roles = list(user.user_roles.values_list("code", flat=True))
        token["roles"] = roles
        return token


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "uuid", "name", "code", "permissions", "description", "is_system", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "code", "is_system", "created_at", "updated_at")


class RoleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "uuid", "name", "code", "permissions", "description", "is_system", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "code", "is_system", "created_at", "updated_at")


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = UserRole
        fields = ("id", "role_id", "role_name", "role_code")
        read_only_fields = ("id",)


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "uuid", "username", "email", "phone", "first_name", "last_name", "is_active", "is_superuser", "roles", "capabilities")
        read_only_fields = fields

    def get_roles(self, obj):
        return list(obj.user_roles.values("id", "name", "code"))

    def get_capabilities(self, obj):
        return obj.get_capabilities()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Senha actual incorrecta.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


class UserSerializer(serializers.ModelSerializer):
    roles = UserRoleSerializer(source="role_assignments", many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "uuid", "username", "email", "phone",
            "first_name", "last_name", "is_active", "roles",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "first_name", "last_name", "password", "role_ids")

    def create(self, validated_data):
        role_ids = validated_data.pop("role_ids", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        for rid in role_ids:
            UserRole.objects.create(user=user, role_id=rid)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)
    role_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    class Meta:
        model = User
        fields = (
            "username", "email", "phone", "first_name", "last_name",
            "is_active", "password", "role_ids",
        )

    def update(self, instance, validated_data):
        role_ids = validated_data.pop("role_ids", None)
        password = validated_data.pop("password", "")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if role_ids is not None:
            UserRole.objects.filter(user=instance).delete()
            for rid in role_ids:
                UserRole.objects.get_or_create(user=instance, role_id=rid)

        return instance


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role_id = serializers.IntegerField()
