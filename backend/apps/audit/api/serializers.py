from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id", "actor", "actor_name", "action", "entity_type", "entity_id",
            "before", "after", "ip_address", "device", "created_at",
        )
        read_only_fields = fields

    def get_actor_name(self, obj):
        u = obj.actor
        if not u:
            return ""
        return u.get_full_name() or u.username
