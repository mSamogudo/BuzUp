from django.db import transaction
from rest_framework import serializers

from apps.trips.models import Agent, Driver, RouteSchedule, Trip, Vehicle
from apps.users.models import Role, User, UserRole
from apps.users.otp import normalize_otp_phone


class VehicleSerializer(serializers.ModelSerializer):
    livrete = serializers.FileField(write_only=True, required=False, allow_null=True)
    livrete_url = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ("id", "uuid", "registration", "make", "model_name", "seated_capacity",
                  "standing_capacity", "status", "livrete", "livrete_url", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "livrete_url", "created_at", "updated_at")

    def get_livrete_url(self, obj):
        if not obj.livrete:
            return ""
        request = self.context.get("request")
        url = obj.livrete.url
        return request.build_absolute_uri(url) if request is not None else url


class DriverSerializer(serializers.ModelSerializer):
    """O motorista E um utilizador: o portal envia/edita username, email, nomes,
    password e is_active explicitamente (sem gerar username automaticamente)."""

    USER_FIELDS = ("username", "email", "first_name", "last_name", "password", "is_active")

    user_id = serializers.IntegerField(read_only=True)
    user_display = serializers.SerializerMethodField()
    # Campos do utilizador (write); preenchidos na leitura via to_representation.
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, style={"input_type": "password"})
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Driver
        fields = ("id", "uuid", "user_id", "user_display", "full_name", "phone", "license_number",
                  "status", "username", "email", "first_name", "last_name", "password", "is_active",
                  "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "user_id", "user_display", "created_at", "updated_at")

    def get_user_display(self, obj):
        if not obj.user:
            return ""
        return obj.user.get_full_name() or obj.user.username

    def to_representation(self, instance):
        data = super().to_representation(instance)
        u = instance.user
        data["username"] = u.username if u else ""
        data["email"] = u.email if u else ""
        data["first_name"] = u.first_name if u else ""
        data["last_name"] = u.last_name if u else ""
        data["is_active"] = u.is_active if u else False
        return data

    def _ensure_user(self, driver: Driver, user_data: dict, validated_data: dict) -> User | None:
        username = (user_data.get("username") or "").strip()
        user = driver.user
        if user is None and not username:
            return None  # motorista sem conta de login

        phone = normalize_otp_phone(validated_data.get("phone", "") or (driver.phone or ""))
        full_name = (validated_data.get("full_name") or driver.full_name or "").strip()
        creating = user is None
        if creating:
            user = User(username=username)
        elif username and username != user.username:
            user.username = username

        if username:
            clash = User.all_objects.filter(username=user.username)
            if user.pk:
                clash = clash.exclude(pk=user.pk)
            if clash.exists():
                raise serializers.ValidationError({"username": "Ja existe um utilizador com este username."})

        email = (user_data.get("email") or "").strip()
        if not email:
            email = (user.email or "") or f"{username or phone or 'driver'}@driver.buzup.co.mz"
        user.email = email
        if "first_name" in user_data:
            user.first_name = user_data.get("first_name") or ""
        elif creating and full_name:
            user.first_name = full_name
        if "last_name" in user_data:
            user.last_name = user_data.get("last_name") or ""
        if phone:
            user.phone = phone
        if "is_active" in user_data:
            user.is_active = bool(user_data.get("is_active"))
        elif creating:
            user.is_active = True

        pwd = user_data.get("password")
        if creating and not pwd:
            user.set_unusable_password()
        elif pwd:
            user.set_password(pwd)
        user.save()

        role = Role.objects.filter(code="driver").first()
        if role:
            UserRole.objects.get_or_create(user=user, role=role)
        return user

    @transaction.atomic
    def create(self, validated_data):
        user_data = {k: validated_data.pop(k) for k in self.USER_FIELDS if k in validated_data}
        validated_data["phone"] = normalize_otp_phone(validated_data.get("phone", "")) or validated_data.get("phone", "")
        driver = Driver.objects.create(**validated_data)
        user = self._ensure_user(driver, user_data, validated_data)
        if user:
            driver.user = user
            driver.save(update_fields=["user", "updated_at"])
        return driver

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = {k: validated_data.pop(k) for k in self.USER_FIELDS if k in validated_data}
        if "phone" in validated_data:
            validated_data["phone"] = normalize_otp_phone(validated_data["phone"]) or validated_data["phone"]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        user = self._ensure_user(instance, user_data, validated_data)
        if user and instance.user_id != user.id:
            instance.user = user
            instance.save(update_fields=["user", "updated_at"])
        return instance


class AgentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = ("id", "uuid", "user_id", "user_display", "full_name", "phone", "status", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "user_id", "user_display", "created_at", "updated_at")

    def get_user_display(self, obj):
        if not obj.user:
            return ""
        return obj.user.get_full_name() or obj.user.username

    def _ensure_user(self, validated_data: dict, instance: Agent | None = None) -> User | None:
        phone = normalize_otp_phone(validated_data.get("phone", ""))
        full_name = (validated_data.get("full_name") or "").strip()
        if not phone:
            return instance.user if instance else None

        username = f"agent_{phone}"
        user = (instance.user if instance else None) or User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create(
                username=username,
                email=f"{phone}@agent.buzup.co.mz",
                phone=phone,
                first_name=full_name,
                is_active=True,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])

        user.phone = phone
        if full_name and not user.first_name:
            user.first_name = full_name
        user.is_active = True
        user.save(update_fields=["phone", "first_name", "is_active", "updated_at"])

        role = Role.objects.filter(code="agent").first()
        if role:
            UserRole.objects.get_or_create(user=user, role=role)
        return user

    @transaction.atomic
    def create(self, validated_data):
        validated_data["phone"] = normalize_otp_phone(validated_data.get("phone", "")) or validated_data.get("phone", "")
        agent = Agent.objects.create(**validated_data)
        user = self._ensure_user(validated_data, agent)
        if user:
            agent.user = user
            agent.save(update_fields=["user", "updated_at"])
        return agent

    @transaction.atomic
    def update(self, instance, validated_data):
        if "phone" in validated_data:
            validated_data["phone"] = normalize_otp_phone(validated_data["phone"]) or validated_data["phone"]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        user = self._ensure_user(validated_data, instance)
        if user and instance.user_id != user.id:
            instance.user = user
            instance.save(update_fields=["user", "updated_at"])
        return instance


class RouteScheduleSerializer(serializers.ModelSerializer):
    route_code = serializers.CharField(source="route.code", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)
    vehicle_registration = serializers.CharField(source="vehicle.registration", read_only=True, default="")
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default="")
    agent_name = serializers.CharField(source="agent.full_name", read_only=True, default="")

    class Meta:
        model = RouteSchedule
        fields = (
            "id", "uuid", "route_id", "route_code", "route_name",
            "vehicle_id", "vehicle_registration",
            "driver_id", "driver_name",
            "agent_id", "agent_name",
            "start_time", "end_time", "frequency_minutes",
            "days_of_week", "status", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")


class TripSerializer(serializers.ModelSerializer):
    route_code = serializers.CharField(source="route.code", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)
    vehicle_registration = serializers.CharField(source="vehicle.registration", read_only=True, default="")
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default="")
    agent_name = serializers.CharField(source="agent.full_name", read_only=True, default="")

    class Meta:
        model = Trip
        fields = (
            "id", "uuid",
            "route", "route_id", "route_code", "route_name",
            "vehicle", "vehicle_id", "vehicle_registration",
            "driver", "driver_id", "driver_name",
            "agent", "agent_id", "agent_name",
            "schedule", "schedule_id",
            "planned_departure_at", "actual_departure_at",
            "planned_arrival_at", "actual_arrival_at",
            "activity_started_at", "activity_paused_at", "activity_closed_at",
            "pause_seconds", "closure_summary",
            "status", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "uuid", "route_id", "vehicle_id", "driver_id", "agent_id", "schedule_id",
            "activity_started_at", "activity_paused_at", "activity_closed_at",
            "pause_seconds", "closure_summary", "created_at", "updated_at",
        )


class TripDetailSerializer(TripSerializer):
    purchases = serializers.SerializerMethodField()
    validations = serializers.SerializerMethodField()
    travel_passes = serializers.SerializerMethodField()
    activity_events = serializers.SerializerMethodField()
    revenue_summary = serializers.SerializerMethodField()

    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ("purchases", "validations", "travel_passes", "activity_events", "revenue_summary")

    def get_purchases(self, obj):
        return [
            {
                "reference": checkout.reference,
                "payer_phone": checkout.payer_phone,
                "quantity": checkout.quantity,
                "total_amount": str(checkout.total_amount),
                "status": checkout.status,
                "created_at": checkout.created_at,
            }
            for checkout in obj.guest_checkouts.order_by("-created_at")[:20]
        ]

    def get_travel_passes(self, obj):
        return [
            {
                "uuid": str(travel_pass.uuid),
                "payer_phone": travel_pass.payer_phone,
                "fare_amount": str(travel_pass.fare_amount),
                "status": travel_pass.status,
                "origin_stop": travel_pass.origin_stop,
                "destination_stop": travel_pass.destination_stop,
                "created_at": travel_pass.created_at,
                "used_at": travel_pass.used_at,
            }
            for travel_pass in obj.travel_passes.order_by("-created_at")[:20]
        ]

    def get_validations(self, obj):
        return [
            {
                "id": validation.id,
                "validation_type": validation.validation_type,
                "status": validation.status,
                "failure_reason": validation.failure_reason,
                "amount_debited": str(validation.amount_debited),
                "device_serial": validation.device.serial_number if validation.device else "",
                "created_at": validation.created_at,
            }
            for validation in obj.validation_events.select_related("device").order_by("-created_at")[:20]
        ]

    def get_activity_events(self, obj):
        return [
            {
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "driver_name": event.driver.full_name if event.driver else "",
                "metadata": event.metadata,
            }
            for event in obj.activity_events.select_related("driver").order_by("-occurred_at")[:20]
        ]

    def get_revenue_summary(self, obj):
        from apps.trips.revenue import calculate_trip_revenue

        return calculate_trip_revenue(obj)


class TripSearchSerializer(serializers.Serializer):
    route_id = serializers.IntegerField(required=False)
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    date = serializers.DateField(required=False)

    def validate(self, attrs):
        origin_id = attrs.get("origin_stop_id")
        destination_id = attrs.get("destination_stop_id")
        if origin_id and destination_id and origin_id == destination_id:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})
        return attrs


class GenerateTripsSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()
