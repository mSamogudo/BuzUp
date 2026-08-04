from django.conf import settings
from rest_framework import serializers

from apps.guest_checkouts.documents import DocumentError, validate_document
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout


class GuestCheckoutSerializer(serializers.ModelSerializer):
    origin_stop_ref_id = serializers.IntegerField(read_only=True)
    destination_stop_ref_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = GuestCheckout
        fields = (
            "id", "uuid", "reference", "payer_phone", "buyer_name",
            "route_code", "route_name", "origin_stop", "destination_stop",
            "origin_stop_ref_id", "destination_stop_ref_id",
            "quantity", "unit_amount", "total_amount", "status", "trip_id",
            "display_currency", "display_total_amount", "exchange_rate",
            "expires_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class PassengerInputSerializer(serializers.Serializer):
    """Passageiro nominal (viagens interurbanas/transfronteiricas)."""

    name = serializers.CharField(max_length=255)
    document_type = serializers.ChoiceField(
        choices=DigitalTravelPass.DocumentType.choices, required=False, allow_blank=True, default="",
    )
    document_number = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    seat = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        """Valida a FORMA do documento; se ele e sequer preciso decide-se na
        vista, que e quem conhece a rota.

        O numero fica normalizado (sem espacos nem tracos, em maiusculas) para
        o mesmo documento nao aparecer de duas maneiras no manifesto.
        """
        numero = attrs.get("document_number") or ""
        if not numero.strip():
            # Tipo sem numero NAO e erro aqui: quem decide se o documento e
            # sequer preciso e a vista, que conhece a rota. O portal manda
            # sempre o tipo (o select tem "bi" por omissao) e, numa carreira
            # urbana, o campo do numero nem aparece — recusar ai partia a
            # compra publica inteira nas rotas que nao pedem documento.
            attrs["document_type"] = ""
            attrs["document_number"] = ""
            return attrs

        try:
            attrs["document_number"] = validate_document(
                attrs.get("document_type") or "other", numero)
        except DocumentError as e:
            raise serializers.ValidationError({"document_number": str(e)})
        return attrs


class GuestCheckoutCreateSerializer(serializers.Serializer):
    payer_phone = serializers.CharField(max_length=20)
    buyer_name = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)
    buyer_email = serializers.EmailField(required=False, allow_blank=True, default="")
    passengers = PassengerInputSerializer(many=True, required=False, default=list)
    # Contacto de emergencia da compra: obrigatorio nas rotas com manifesto
    # de bordo (interprovincial/internacional). Validado na vista, que resolve
    # a rota.
    emergency_contact_name = serializers.CharField(max_length=120, required=False, default="", allow_blank=True)
    emergency_contact_phone = serializers.CharField(max_length=20, required=False, default="", allow_blank=True)
    # Opcional: a app do passageiro só escolhe origem + destino e o backend
    # infere o corredor (como na compra por carteira).
    route_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    route_name = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)
    origin_stop = serializers.CharField(max_length=255)
    destination_stop = serializers.CharField(max_length=255)
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)
    unit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    # Moeda em que o comprador viu o preco (ex.: ZAR). So exibicao — a
    # cobranca e sempre em MZN; a taxa e congelada no servidor.
    display_currency = serializers.CharField(
        max_length=3, required=False, allow_blank=True, default="MZN",
    )

    def validate(self, attrs):
        origin_id = attrs.get("origin_stop_id")
        destination_id = attrs.get("destination_stop_id")
        if origin_id and destination_id and origin_id == destination_id:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})

        origin_name = str(attrs.get("origin_stop") or "").strip().lower()
        destination_name = str(attrs.get("destination_stop") or "").strip().lower()
        if origin_name and destination_name and origin_name == destination_name:
            raise serializers.ValidationError({"destination_stop": "Destino deve ser diferente da origem."})
        return attrs


class DigitalTravelPassSerializer(serializers.ModelSerializer):
    origin_stop_ref_id = serializers.IntegerField(read_only=True)
    destination_stop_ref_id = serializers.IntegerField(read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = DigitalTravelPass
        fields = (
            "id", "uuid", "route_code", "route_name",
            "origin_stop", "destination_stop", "fare_amount",
            "display_currency", "display_fare_amount",
            "passenger_name", "document_type", "document_number", "seat_number",
            "origin_stop_ref_id", "destination_stop_ref_id",
            "status", "delivery_channel", "trip_id",
            "valid_from", "valid_until", "used_at", "pdf_url", "created_at",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        if not obj.token:
            return ""
        base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        return f"{base}/api/public/ticket/{obj.token}/" if base else f"/api/public/ticket/{obj.token}/"


class PublicTravelPassSerializer(serializers.ModelSerializer):
    """Bilhete visto pelo canal PÚBLICO (lookup por referência, sem sessão).

    Deliberadamente mais pobre que `DigitalTravelPassSerializer`: a referência
    circula por SMS, aparece impressa no bilhete e no ecrã do agente, portanto
    não é um segredo. O `pdf_url` (que carrega o token) fica, porque é o próprio
    meio de entrega ao comprador — mas o número do documento não: quem consiga
    uma referência não tem de levar com ele a identificação do passageiro.
    """

    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = DigitalTravelPass
        fields = (
            "uuid", "route_code", "route_name",
            "origin_stop", "destination_stop", "fare_amount",
            "display_currency", "display_fare_amount",
            "passenger_name", "seat_number",
            "status", "valid_from", "valid_until", "used_at", "pdf_url",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        if not obj.token:
            return ""
        base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        return f"{base}/api/public/ticket/{obj.token}/" if base else f"/api/public/ticket/{obj.token}/"


class GuestCheckoutPublicSerializer(serializers.ModelSerializer):
    passes = PublicTravelPassSerializer(source="travel_passes", many=True, read_only=True)

    class Meta:
        model = GuestCheckout
        fields = (
            "reference", "route_code", "route_name",
            "origin_stop", "destination_stop",
            "quantity", "total_amount",
            "display_currency", "display_total_amount",
            "status", "passes",
        )
        read_only_fields = fields
