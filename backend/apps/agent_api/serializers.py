from rest_framework import serializers


class AgentLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    otp_code = serializers.CharField(required=False, allow_blank=True)
    challenge_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        has_password = bool(attrs.get("username") and attrs.get("password"))
        has_otp = bool(attrs.get("phone") and attrs.get("otp_code"))
        if not (has_password or has_otp):
            raise serializers.ValidationError("Forneca username/password ou phone/otp_code.")
        return attrs


class AgentDeviceRegisterSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=128)
    device_type = serializers.CharField(max_length=64, required=False, allow_blank=True)
    model_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    manufacturer = serializers.CharField(max_length=255, required=False, allow_blank=True)
    imei = serializers.CharField(max_length=64, required=False, allow_blank=True)
    android_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    capabilities = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    app_version_code = serializers.IntegerField(required=False, default=0)


class AgentDeviceHeartbeatSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=128, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)


class AgentFareSerializer(serializers.Serializer):
    origin_stop_id = serializers.IntegerField()
    destination_stop_id = serializers.IntegerField()


class AgentSaleSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField(required=False, allow_null=True)
    route_id = serializers.IntegerField(required=False, allow_null=True)
    origin_stop_id = serializers.IntegerField()
    destination_stop_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=["mobile_money", "card"], default="mobile_money",
    )
    # mobile_money: required (phone of M-Pesa / E-Mola wallet)
    passenger_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # card: one of these — physical NFC UID or digital QR token
    card_uid = serializers.CharField(max_length=64, required=False, allow_blank=True)
    qr_token = serializers.CharField(max_length=256, required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)
    device_serial = serializers.CharField(max_length=128, required=False, allow_blank=True)
    auto_request_payment = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if not attrs.get("trip_id") and not attrs.get("route_id"):
            raise serializers.ValidationError("Forneca trip_id ou route_id.")
        if attrs["origin_stop_id"] == attrs["destination_stop_id"]:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})
        method = attrs.get("payment_method", "mobile_money")
        if method == "mobile_money":
            if not attrs.get("passenger_phone"):
                raise serializers.ValidationError({"passenger_phone": "Obrigatorio para pagamento via Mobile Money."})
        elif method == "card":
            if not attrs.get("card_uid") and not attrs.get("qr_token"):
                raise serializers.ValidationError("Indique card_uid ou qr_token para pagamento por cartao.")
        return attrs


class AgentTicketVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
