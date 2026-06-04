from decimal import Decimal

from rest_framework import serializers

from apps.packages.models import Package, PackageRoute, PassengerPackage


class PackageRouteSerializer(serializers.ModelSerializer):
    route_code = serializers.CharField(source="route.code", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = PackageRoute
        fields = ("id", "route_id", "route_code", "route_name")


class PackageSerializer(serializers.ModelSerializer):
    routes = PackageRouteSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = (
            "id", "uuid", "name", "description", "discount_type",
            "discount_value", "price", "validity_days", "max_trips",
            "status", "routes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")


class PackageCreateSerializer(serializers.ModelSerializer):
    route_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    class Meta:
        model = Package
        fields = (
            "name", "description", "discount_type", "discount_value",
            "price", "validity_days", "max_trips", "status", "route_ids",
        )

    def validate(self, attrs):
        if attrs.get("discount_type") == "percentage":
            value = attrs.get("discount_value")
            if value is not None and value != int(value):
                raise serializers.ValidationError({"discount_value": "Percentagem deve ser um numero inteiro."})
        return attrs


class PassengerPackageSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source="passenger_account.full_name", read_only=True)
    passenger_phone = serializers.CharField(source="passenger_account.phone_number", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True)
    discount_type = serializers.CharField(source="package.discount_type", read_only=True)

    class Meta:
        model = PassengerPackage
        fields = (
            "id", "uuid", "passenger_account_id", "passenger_name",
            "passenger_phone", "package_id", "package_name",
            "discount_type", "special_balance", "trips_used",
            "trips_remaining", "status", "activated_at", "expires_at",
        )
        read_only_fields = fields


class SubscribeSerializer(serializers.Serializer):
    passenger_id = serializers.IntegerField()
    package_id = serializers.IntegerField()
    pay_from_wallet = serializers.BooleanField(default=True)


class TopupPackageSerializer(serializers.Serializer):
    subscription_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
