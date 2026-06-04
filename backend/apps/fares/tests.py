from decimal import Decimal

from django.test import TestCase

from apps.fares.api.serializers import FareRuleSerializer
from apps.fares.models import FareProduct, FareRule
from apps.fares.services import NoFareFoundError, quote_fare
from apps.routes.models import Route, RouteStop, Stop


class RouteStopFareValidationTests(TestCase):
    def setUp(self):
        self.route = Route.objects.create(name="Linha Centro")
        self.other_route = Route.objects.create(name="Linha Praia")
        self.origin = Stop.objects.create(name="Baixa")
        self.destination = Stop.objects.create(name="Macuti")
        self.foreign_stop = Stop.objects.create(name="Aeroporto")
        RouteStop.objects.create(route=self.route, stop=self.origin, sequence=1, distance_from_start_km=0)
        RouteStop.objects.create(route=self.route, stop=self.destination, sequence=2, distance_from_start_km=8)
        RouteStop.objects.create(route=self.other_route, stop=self.foreign_stop, sequence=1, distance_from_start_km=0)
        self.product = FareProduct.objects.create(
            name="Avulso",
            product_type=FareProduct.ProductType.SINGLE_TRIP,
            status=FareProduct.Status.ACTIVE,
        )

    def test_fare_rule_rejects_stop_outside_selected_route(self):
        serializer = FareRuleSerializer(data={
            "fare_product": self.product.id,
            "route": self.route.id,
            "origin_stop": self.origin.id,
            "destination_stop": self.foreign_stop.id,
            "calculation_method": FareRule.CalculationMethod.ORIGIN_DESTINATION,
            "fixed_amount": "25.00",
            "passenger_class": FareRule.PassengerClass.STANDARD,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("origin_stop", serializer.errors)

    def test_quote_rejects_stop_outside_route(self):
        with self.assertRaises(NoFareFoundError):
            quote_fare(
                route=self.route,
                origin_stop=self.origin,
                destination_stop=self.foreign_stop,
            )

    def test_quote_accepts_stops_linked_to_route(self):
        FareRule.objects.create(
            fare_product=self.product,
            route=self.route,
            origin_stop=self.origin,
            destination_stop=self.destination,
            calculation_method=FareRule.CalculationMethod.ORIGIN_DESTINATION,
            fixed_amount=Decimal("25.00"),
        )

        quote = quote_fare(
            route=self.route,
            origin_stop=self.origin,
            destination_stop=self.destination,
        )

        self.assertEqual(quote.amount, Decimal("25.00"))

    def test_quote_rejects_reverse_direction(self):
        FareRule.objects.create(
            fare_product=self.product,
            route=self.route,
            origin_stop=self.origin,
            destination_stop=self.destination,
            calculation_method=FareRule.CalculationMethod.ORIGIN_DESTINATION,
            fixed_amount=Decimal("25.00"),
        )

        with self.assertRaises(NoFareFoundError):
            quote_fare(
                route=self.route,
                origin_stop=self.destination,
                destination_stop=self.origin,
            )
