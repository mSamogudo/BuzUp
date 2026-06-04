from rest_framework import serializers


class DateRangeSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    route_id = serializers.IntegerField(required=False)
    device_id = serializers.IntegerField(required=False)
    agent_id = serializers.IntegerField(required=False)
    vehicle_id = serializers.IntegerField(required=False)
    driver_id = serializers.IntegerField(required=False)
    stop_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
