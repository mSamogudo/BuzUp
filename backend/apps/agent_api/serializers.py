import decimal

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


#: Serials que o Android devolve quando NAO tem numero de serie para dar.
#:
#: Nao sao identificadores: sao a maneira da plataforma dizer "nao sei". Aceitar
#: um destes fazia com que todos os aparelhos partilhassem o MESMO dispositivo —
#: o primeiro criava-o e os seguintes entravam por cima. Bloquear um bloqueava
#: todos, e nenhuma venda ficava atribuivel ao terminal onde foi feita.
SERIAIS_SEM_VALOR = {"unknown", "android", "null", "none", "0", "unavailable", "-"}


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

    def validate_serial_number(self, value: str) -> str:
        serial = (value or "").strip()
        if not serial or serial.lower() in SERIAIS_SEM_VALOR:
            raise serializers.ValidationError(
                "Este aparelho nao devolveu um numero de serie proprio. "
                "Actualize a aplicacao para a versao mais recente."
            )
        return serial


class _ValorArredondado(serializers.DecimalField):
    """Numero de sensor: arredonda-se, nao se recusa.

    O GPS de um telemovel devolve `-25.891234567890` — 14 digitos. O campo
    exigia no maximo 9 e recusava o heartbeat inteiro com 400. Resultado: entre
    18 e 26 de Agosto de 2026, NENHUMA posicao chegou ao servidor. O autocarro
    esteve invisivel no mapa dos passageiros durante oito dias, e ninguem deu
    por isso porque a app engole o erro do heartbeat (e bem: uma falha de
    telemetria nao pode parar uma venda).

    Exigir do cliente a precisao exacta era pedir-lhe que soubesse a forma da
    coluna da base de dados. Um sensor da o que tem; quem grava e que decide
    quantas casas guarda. Seis casas sao cerca de 11 cm.

    O arredondamento acontece ANTES da validacao porque o DRF valida os digitos
    do valor recebido e so depois quantiza — pela ordem inversa, o `rounding`
    do proprio campo nunca chegaria a salvar nada.
    """

    def to_internal_value(self, data):
        if data is None or data == "":
            return super().to_internal_value(data)
        try:
            valor = decimal.Decimal(str(data).strip())
        except (decimal.InvalidOperation, ValueError, TypeError):
            # Nao e um numero: deixa a mensagem normal do DRF explicar porque.
            return super().to_internal_value(data)
        casas = decimal.Decimal(1).scaleb(-self.decimal_places)
        return super().to_internal_value(
            valor.quantize(casas, rounding=decimal.ROUND_HALF_UP))


class AgentDeviceHeartbeatSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=128, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    latitude = _ValorArredondado(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = _ValorArredondado(max_digits=9, decimal_places=6, required=False, allow_null=True)
    speed = _ValorArredondado(max_digits=6, decimal_places=2, required=False, allow_null=True)
    heading = _ValorArredondado(max_digits=6, decimal_places=2, required=False, allow_null=True)
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
        choices=["mobile_money", "card", "cash"], default="mobile_money",
    )
    # mobile_money: required (phone of M-Pesa / E-Mola wallet)
    passenger_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # card: one of these — physical NFC UID or digital QR token
    card_uid = serializers.CharField(max_length=64, required=False, allow_blank=True)
    qr_token = serializers.CharField(max_length=256, required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)
    device_serial = serializers.CharField(max_length=128, required=False, allow_blank=True)
    auto_request_payment = serializers.BooleanField(default=True)
    # Moeda em que o agente mostrou o preco ao passageiro (ex.: ZAR nas rotas
    # p/ Africa do Sul). So exibicao — a cobranca e sempre em MZN.
    display_currency = serializers.CharField(
        max_length=3, required=False, allow_blank=True, default="MZN",
    )
    # Lugares escolhidos, quando a rota os marca (interprovincial e
    # internacional). Vazio nas carreiras urbanas, onde ninguem escolhe.
    # Contacto de emergencia: obrigatorio nas rotas com manifesto de bordo.
    # A validacao vive na venda, que e quem sabe a rota.
    emergency_contact_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    emergency_contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    seats = serializers.ListField(
        child=serializers.CharField(max_length=8),
        required=False, allow_empty=True, default=list,
    )
    # Identificacao de quem viaja, um por bilhete. Obrigatoria nas rotas com
    # manifesto de bordo (interprovincial e internacional): o bilhete e nominal
    # e, na fronteira, e conferido contra o documento. O portal publico ja a
    # pedia; a venda ao balcao nao — e era ao balcao que o passageiro estava
    # mesmo a frente do agente, com o passaporte na mao.
    #
    # A validacao vive na venda, que e quem conhece a rota. Ver
    # `apps.guest_checkouts.documents`.
    passengers = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_blank=True, max_length=255)),
        required=False, allow_empty=True, default=list,
    )

    def validate(self, attrs):
        if not attrs.get("trip_id") and not attrs.get("route_id"):
            raise serializers.ValidationError("Forneca trip_id ou route_id.")
        if attrs["origin_stop_id"] == attrs["destination_stop_id"]:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})
        method = attrs.get("payment_method", "mobile_money")
        if method == "mobile_money":
            if not attrs.get("passenger_phone"):
                raise serializers.ValidationError({"passenger_phone": "Obrigatorio para pagamento via Mobile Money."})
        elif method == "cash":
            # O telefone continua obrigatorio, mas por outra razao: ja nao e
            # uma carteira a debitar — e para onde o bilhete vai por SMS. Sem
            # ele o passageiro paga e nao leva bilhete nenhum.
            if not attrs.get("passenger_phone"):
                raise serializers.ValidationError(
                    {"passenger_phone": "Indique o telefone do passageiro — o bilhete vai por SMS."})
        elif method == "card":
            if not attrs.get("card_uid") and not attrs.get("qr_token"):
                raise serializers.ValidationError("Indique card_uid ou qr_token para pagamento por cartao.")

        seats = attrs.get("seats") or []
        if seats:
            if len(set(seats)) != len(seats):
                raise serializers.ValidationError({"seats": "Lugar repetido na mesma venda."})
            if len(seats) != attrs.get("quantity", 1):
                raise serializers.ValidationError({"seats": "Indique um lugar por bilhete."})
        return attrs


class AgentTicketVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
