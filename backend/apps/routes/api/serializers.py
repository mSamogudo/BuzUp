from rest_framework import serializers

from apps.routes.models import Route, RouteStop, Stop


class StopSerializer(serializers.ModelSerializer):
    route_count = serializers.SerializerMethodField()

    class Meta:
        model = Stop
        fields = ("id", "uuid", "code", "name", "latitude", "longitude", "status", "route_count", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "code", "created_at", "updated_at")

    def get_route_count(self, obj):
        return obj.route_stops.values("route_id").distinct().count()


class StopRouteLinkSerializer(serializers.ModelSerializer):
    route_id = serializers.IntegerField(source="route.id", read_only=True)
    route_code = serializers.CharField(source="route.code", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = RouteStop
        fields = ("route_id", "route_code", "route_name", "sequence", "distance_from_start_km", "direction")


class StopDetailSerializer(StopSerializer):
    route_links = StopRouteLinkSerializer(source="route_stops", many=True, read_only=True)

    class Meta(StopSerializer.Meta):
        fields = StopSerializer.Meta.fields + ("route_links",)


class RouteStopSerializer(serializers.ModelSerializer):
    stop_code = serializers.CharField(source="stop.code", read_only=True)
    stop_name = serializers.CharField(source="stop.name", read_only=True)

    class Meta:
        model = RouteStop
        fields = (
            "id", "uuid", "stop_id", "stop_code", "stop_name",
            "sequence", "distance_from_start_km", "direction",
        )
        read_only_fields = ("id", "uuid", "stop_code", "stop_name")


class RouteSerializer(serializers.ModelSerializer):
    stop_count = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ("id", "uuid", "code", "name", "description", "status", "stop_count", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "code", "created_at", "updated_at")

    def get_stop_count(self, obj):
        return obj.route_stops.values("direction", "stop_id").distinct().count()


class RouteDetailSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(source="route_stops", many=True, read_only=True)
    stop_count = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ("id", "uuid", "code", "name", "description", "status", "stop_count", "stops", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "code", "created_at", "updated_at")

    def get_stop_count(self, obj):
        return obj.route_stops.values("direction", "stop_id").distinct().count()


class RouteStopWriteSerializer(serializers.Serializer):
    stop_id = serializers.IntegerField()
    sequence = serializers.IntegerField(min_value=1)
    distance_from_start_km = serializers.DecimalField(max_digits=8, decimal_places=2, default=0)
    direction = serializers.ChoiceField(choices=RouteStop.Direction.choices, default=RouteStop.Direction.OUTBOUND)
