"""Os pacotes especiais so valem em carreiras urbanas e interurbanas.

Um pacote e um passe do dia-a-dia — o trajecto de casa para o trabalho,
comprado ao mes com desconto por volume. Uma viagem interprovincial ou
internacional e outra coisa: bilhete nominal, lugar marcado, preco por
trajecto. Deixar um passe mensal cobrir Maputo-Joanesburgo era vender a viagem
longa ao preco da curta — e ninguem daria pelo buraco na receita ate ao fecho.

A regra vive no servidor porque tem de valer igual nos quatro caminhos por onde
uma viagem pode ser paga: orcamento, compra pela carteira, venda no POS e
consumo no momento da validacao. Esconder o interruptor na app nao chega — quem
falar com a API a mao continuava a conseguir.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.packages.models import Package, PackageRoute, PassengerPackage
from apps.packages.services import find_active_package_for_route
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route, RouteStop, Stop


class PackageScopeBase(TestCase):
    def setUp(self):
        self.urbana = Route.objects.create(
            code="R-URB", name="Circular da Baixa",
            service_type=Route.ServiceType.URBAN, status=Route.Status.ACTIVE,
        )
        self.interprovincial = Route.objects.create(
            code="R-INT", name="Maputo - Xai-Xai",
            service_type=Route.ServiceType.INTERPROVINCIAL, status=Route.Status.ACTIVE,
        )
        self.internacional = Route.objects.create(
            code="R-SA", name="Maputo - Joanesburgo",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE,
        )

        self.origem = Stop.objects.create(code="ST-PA", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="ST-PB", name="Paragem B", status="active")
        for rota in (self.urbana, self.interprovincial, self.internacional):
            RouteStop.objects.create(route=rota, stop=self.origem, sequence=1, direction="outbound")
            RouteStop.objects.create(route=rota, stop=self.destino, sequence=2, direction="outbound")

        self.passageiro = PassengerAccount.objects.create(
            full_name="Ana Cossa", phone_number="849111222",
            status=PassengerAccount.Status.ACTIVE,
        )

        # Pacote SEM rotas associadas: vale, em principio, para qualquer rota.
        # E precisamente o caso perigoso — e o que o tipo de servico tem de
        # travar sozinho.
        self.pacote = Package.objects.create(
            name="Passe Mensal", discount_type=Package.DiscountType.PERCENTAGE,
            discount_value=Decimal("50.00"), price=Decimal("1000.00"),
            validity_days=30, status=Package.Status.ACTIVE,
        )
        self.subscricao = PassengerPackage.objects.create(
            passenger_account=self.passageiro, package=self.pacote,
            activated_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            status=PassengerPackage.Status.ACTIVE,
        )

    def _tarifa(self, rota, valor):
        produto = FareProduct.objects.create(
            name=f"Avulso {rota.code}",
            product_type=FareProduct.ProductType.SINGLE_TRIP,
            status=FareProduct.Status.ACTIVE,
        )
        FareRule.objects.create(
            fare_product=produto, route=rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal(valor),
        )


class FindActivePackageScopeTests(PackageScopeBase):
    def test_pacote_vale_na_carreira_urbana(self):
        achado = find_active_package_for_route(self.passageiro, self.urbana)
        self.assertIsNotNone(achado)
        self.assertEqual(achado.pk, self.subscricao.pk)

    def test_pacote_nao_vale_na_interprovincial(self):
        self.assertIsNone(find_active_package_for_route(self.passageiro, self.interprovincial))

    def test_pacote_nao_vale_na_internacional(self):
        self.assertIsNone(find_active_package_for_route(self.passageiro, self.internacional))

    def test_a_rota_e_que_decide_nao_o_pacote(self):
        # Mesmo um pacote explicitamente associado a rota interprovincial nao
        # passa: quem manda e o tipo de servico.
        PackageRoute.objects.create(package=self.pacote, route=self.interprovincial)
        self.assertIsNone(find_active_package_for_route(self.passageiro, self.interprovincial))


class RoutePropertyTests(PackageScopeBase):
    def test_propriedade_por_tipo_de_servico(self):
        self.assertTrue(self.urbana.allows_package_discounts)
        self.assertFalse(self.interprovincial.allows_package_discounts)
        self.assertFalse(self.internacional.allows_package_discounts)

    def test_e_o_inverso_de_marcar_lugar(self):
        # As duas regras derivam do mesmo tipo de servico. Se um dia deixarem
        # de concordar, e sinal de que alguem separou o que devia andar junto.
        for rota in (self.urbana, self.interprovincial, self.internacional):
            self.assertEqual(
                rota.allows_package_discounts,
                not rota.requires_seat_selection,
                msg=f"rota {rota.code}",
            )


class QuoteScopeTests(PackageScopeBase):
    """O orcamento nao pode prometer um desconto que a compra vai recusar."""

    def test_orcamento_urbano_aplica_desconto(self):
        from apps.guest_checkouts.purchase import quote_for_passenger

        self._tarifa(self.urbana, "100.00")
        q = quote_for_passenger(
            passenger=self.passageiro, route=self.urbana,
            origin=self.origem, destination=self.destino,
        )
        self.assertEqual(q["base_fare"], "100.00")
        self.assertEqual(q["wallet_amount"], "50.00")
        self.assertEqual(q["package_id"], self.subscricao.pk)

    def test_orcamento_interprovincial_paga_tarifa_cheia(self):
        from apps.guest_checkouts.purchase import quote_for_passenger

        self._tarifa(self.interprovincial, "750.00")
        q = quote_for_passenger(
            passenger=self.passageiro, route=self.interprovincial,
            origin=self.origem, destination=self.destino,
        )
        self.assertEqual(q["base_fare"], "750.00")
        self.assertEqual(q["wallet_amount"], "750.00")
        self.assertIsNone(q["package_id"])

    def test_indicar_o_pacote_pelo_id_nao_furа_a_regra(self):
        # O caminho que passa ao lado de find_active_package_for_route.
        from apps.guest_checkouts.purchase import quote_for_passenger

        self._tarifa(self.interprovincial, "750.00")
        q = quote_for_passenger(
            passenger=self.passageiro, route=self.interprovincial,
            origin=self.origem, destination=self.destino,
            passenger_package_id=self.subscricao.pk,
        )
        self.assertEqual(q["wallet_amount"], "750.00")
        self.assertIsNone(q["package_id"])


class PurchaseScopeTests(PackageScopeBase):
    def test_compra_interprovincial_com_pacote_pelo_id_e_recusada(self):
        from apps.guest_checkouts.purchase import PurchaseError, _resolve_passenger_package

        with self.assertRaises(PurchaseError) as ctx:
            _resolve_passenger_package(
                passenger=self.passageiro, route=self.interprovincial,
                passenger_package_id=self.subscricao.pk, use_package=True,
            )
        self.assertIn("urbanas", str(ctx.exception).lower())

    def test_compra_interprovincial_sem_id_simplesmente_nao_usa_pacote(self):
        from apps.guest_checkouts.purchase import _resolve_passenger_package

        self.assertIsNone(_resolve_passenger_package(
            passenger=self.passageiro, route=self.interprovincial,
            passenger_package_id=None, use_package=True,
        ))

    def test_compra_urbana_continua_a_usar_o_pacote(self):
        from apps.guest_checkouts.purchase import _resolve_passenger_package

        achado = _resolve_passenger_package(
            passenger=self.passageiro, route=self.urbana,
            passenger_package_id=self.subscricao.pk, use_package=True,
        )
        self.assertEqual(achado.pk, self.subscricao.pk)
