from rest_framework import serializers

from apps.fares.models import AdminFee, FareProduct, FareRule
from apps.fares.services import find_conflicts


class AdminFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminFee
        fields = (
            "id", "uuid", "code", "name", "kind", "amount", "currency",
            "description", "is_active", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")


class FareProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = FareProduct
        fields = ("id", "uuid", "name", "product_type", "status", "created_at", "updated_at")
        read_only_fields = ("id", "uuid", "created_at", "updated_at")


class FareRuleSerializer(serializers.ModelSerializer):
    fare_product_name = serializers.CharField(source="fare_product.name", read_only=True)
    route_code = serializers.CharField(source="route.code", read_only=True, default="")
    origin_stop_name = serializers.CharField(source="origin_stop.name", read_only=True, default="")
    destination_stop_name = serializers.CharField(source="destination_stop.name", read_only=True, default="")

    class Meta:
        model = FareRule
        fields = (
            "id", "uuid",
            "fare_product", "fare_product_id", "fare_product_name",
            "route", "route_id", "route_code",
            "origin_stop", "origin_stop_id", "origin_stop_name",
            "destination_stop", "destination_stop_id", "destination_stop_name",
            "zone", "passenger_class", "calculation_method",
            "fixed_amount", "amount_per_km", "min_amount", "max_amount",
            "distance_min_km", "distance_max_km",
            "valid_from", "valid_until", "priority",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "fare_product_id", "route_id", "origin_stop_id", "destination_stop_id", "created_at", "updated_at")

    def validate(self, attrs):
        route = attrs.get("route", getattr(self.instance, "route", None))
        origin_stop = attrs.get("origin_stop", getattr(self.instance, "origin_stop", None))
        destination_stop = attrs.get("destination_stop", getattr(self.instance, "destination_stop", None))
        calculation_method = attrs.get(
            "calculation_method",
            getattr(self.instance, "calculation_method", FareRule.CalculationMethod.FIXED),
        )

        if not route:
            raise serializers.ValidationError({"route": "A rota e obrigatoria."})

        if calculation_method == FareRule.CalculationMethod.FIXED:
            attrs["origin_stop"] = None
            attrs["destination_stop"] = None
            attrs["distance_min_km"] = None
            attrs["distance_max_km"] = None
            attrs.setdefault("amount_per_km", 0)
            origin_stop = None
            destination_stop = None

        elif calculation_method == FareRule.CalculationMethod.ORIGIN_DESTINATION:
            if not origin_stop or not destination_stop:
                raise serializers.ValidationError({"origin_stop": "Origem e destino sao obrigatorios para Origem/Destino."})
            if origin_stop.pk == destination_stop.pk:
                raise serializers.ValidationError({"destination_stop": "Destino deve ser diferente da origem."})
            attrs["distance_min_km"] = None
            attrs["distance_max_km"] = None

            requested_ids = [origin_stop.pk, destination_stop.pk]
            linked_ids = set(route.route_stops.filter(stop_id__in=requested_ids).values_list("stop_id", flat=True))
            missing_names = [
                stop.name for stop in (origin_stop, destination_stop)
                if stop.pk not in linked_ids
            ]
            if missing_names:
                raise serializers.ValidationError({
                    "origin_stop": f"Paragem fora da rota {route.code}: {', '.join(missing_names)}."
                })

        elif calculation_method == FareRule.CalculationMethod.DISTANCE:
            d_min = attrs.get("distance_min_km", getattr(self.instance, "distance_min_km", None))
            d_max = attrs.get("distance_max_km", getattr(self.instance, "distance_max_km", None))
            if d_min is None or d_max is None:
                raise serializers.ValidationError({
                    "distance_min_km": "Faixa minima e maxima sao obrigatorias para Distancia.",
                })
            if d_min >= d_max:
                raise serializers.ValidationError({
                    "distance_max_km": "Distancia maxima deve ser maior que a minima.",
                })
            attrs["origin_stop"] = None
            attrs["destination_stop"] = None

        valid_from = attrs.get("valid_from", getattr(self.instance, "valid_from", None))
        valid_until = attrs.get("valid_until", getattr(self.instance, "valid_until", None))
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError({
                "valid_until": "Fim do periodo deve ser depois do inicio.",
            })

        provisional = FareRule(
            id=self.instance.id if self.instance else None,
            route=route,
            calculation_method=calculation_method,
            passenger_class=attrs.get("passenger_class", getattr(self.instance, "passenger_class", FareRule.PassengerClass.STANDARD)),
            origin_stop=origin_stop,
            destination_stop=destination_stop,
            distance_min_km=attrs.get("distance_min_km", getattr(self.instance, "distance_min_km", None)),
            distance_max_km=attrs.get("distance_max_km", getattr(self.instance, "distance_max_km", None)),
            valid_from=valid_from,
            valid_until=valid_until,
        )

        conflicts = find_conflicts(provisional, exclude_pk=self.instance.id if self.instance else None)
        if conflicts:
            ref = conflicts[0]
            method_label = dict(FareRule.CalculationMethod.choices).get(ref.calculation_method, ref.calculation_method)
            raise serializers.ValidationError({
                "non_field_errors": _conflict_message(provisional, ref, method_label),
            })

        return attrs


def _conflict_message(new_rule: FareRule, conflict: FareRule, method_label: str) -> str:
    if new_rule.calculation_method == FareRule.CalculationMethod.ORIGIN_DESTINATION:
        return (
            f"Ja existe uma regra activa para esta origem e destino nesta rota "
            f"(categoria {new_rule.passenger_class}). Edite a regra existente em vez de criar outra."
        )
    if new_rule.calculation_method == FareRule.CalculationMethod.FIXED:
        return (
            f"Ja existe uma regra activa de Preco Fixo para esta rota e categoria "
            f"({new_rule.passenger_class}). Nao e possivel criar duas regras activas "
            "que possam cobrar precos diferentes para a mesma viagem."
        )
    if new_rule.calculation_method == FareRule.CalculationMethod.DISTANCE:
        return (
            f"Esta faixa de distancia ({new_rule.distance_min_km}-{new_rule.distance_max_km} km) "
            f"sobrepoe-se a uma regra ja cadastrada ({conflict.distance_min_km}-{conflict.distance_max_km} km) "
            f"para a mesma rota e categoria."
        )
    return f"Ja existe uma regra activa para esta rota e categoria com o metodo {method_label}."


class FareQuoteRequestSerializer(serializers.Serializer):
    route_id = serializers.IntegerField()
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    passenger_class = serializers.ChoiceField(
        choices=FareRule.PassengerClass.choices,
        default=FareRule.PassengerClass.STANDARD,
    )
