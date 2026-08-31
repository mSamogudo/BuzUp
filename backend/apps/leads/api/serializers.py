from rest_framework import serializers

from apps.leads.models import ServiceRequest


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    #: As areas que o interessado pediu para ver. Recusa-se o que nao conhecemos
    #: em vez de o guardar: um valor invalido aqui e um formulario dessincronizado
    #: do CMS, e e melhor sabe-lo pelo erro do que descobri-lo na lista comercial.
    topics = serializers.ListField(
        child=serializers.ChoiceField(choices=[c[0] for c in ServiceRequest.TOPICS]),
        required=False, allow_empty=True,
    )

    class Meta:
        model = ServiceRequest
        fields = (
            "name", "role", "organization", "phone", "email",
            "interest", "operation_type", "fleet_size", "topics", "message",
        )

    def validate_phone(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 9:
            raise serializers.ValidationError("Indique um telefone valido.")
        return value.strip()


class ServiceRequestSerializer(serializers.ModelSerializer):
    interest_label = serializers.CharField(source="get_interest_display", read_only=True)
    operation_type_label = serializers.CharField(
        source="get_operation_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    topic_labels = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "uuid", "name", "role", "organization", "phone", "email",
            "interest", "interest_label", "operation_type", "operation_type_label",
            "fleet_size", "topics", "topic_labels", "message",
            "status", "status_label", "source", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")

    def get_topic_labels(self, obj):
        """Rotulos por extenso, para a lista do portal nao mostrar chaves cruas."""
        nomes = dict(ServiceRequest.TOPICS)
        return [nomes.get(t, t) for t in (obj.topics or [])]
