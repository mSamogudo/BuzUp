"""A posicao do autocarro tem de chegar ao servidor.

O defeito: `latitude`/`longitude` eram `DecimalField(max_digits=9,
decimal_places=6)` e o DRF valida os DIGITOS DO VALOR RECEBIDO antes de o
quantizar. O GPS de um telemovel devolve `-25.891234567890` — catorze digitos —
e o heartbeat inteiro era recusado com 400.

Entre 18 e 26 de Agosto de 2026 nenhuma posicao chegou ao servidor. O autocarro
esteve invisivel no mapa dos passageiros durante oito dias e ninguem deu por
isso, porque a app engole o erro do heartbeat — e faz bem: uma falha de
telemetria nao pode parar uma venda. Mas um erro engolido tambem nao aparece a
ninguem, e por isso e que este teste existe.

A regra: um sensor da o que tem. Quem grava e que decide quantas casas guarda.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.agent_api.serializers import AgentDeviceHeartbeatSerializer


class HeartbeatGpsTests(TestCase):
    def _valida(self, **dados):
        s = AgentDeviceHeartbeatSerializer(data={"serial_number": "SN-1", **dados})
        self.assertTrue(s.is_valid(), s.errors)
        return s.validated_data

    # --- o caso reportado -------------------------------------------------

    def test_gps_de_telemovel_com_precisao_maxima_e_aceite(self):
        """Era este o valor que dava 400 a cada minuto."""
        d = self._valida(latitude=-25.891234567890, longitude=32.583712345678)
        self.assertEqual(d["latitude"], Decimal("-25.891235"))
        self.assertEqual(d["longitude"], Decimal("32.583712"))

    def test_velocidade_em_bruto_do_android_e_aceite(self):
        """`speed` vem em m/s com toda a mantissa: 13.399999618530273."""
        d = self._valida(speed=13.399999618530273 * 3.6)
        self.assertEqual(d["speed"], Decimal("48.24"))

    def test_rumo_em_bruto_e_aceite(self):
        d = self._valida(heading=187.2549896240234)
        self.assertEqual(d["heading"], Decimal("187.25"))

    # --- o arredondamento e correcto --------------------------------------

    def test_arredonda_e_nao_trunca(self):
        d = self._valida(latitude=-25.8912355)
        self.assertEqual(d["latitude"], Decimal("-25.891236"))

    def test_precisao_guardada_chega_para_localizar_um_autocarro(self):
        """Seis casas sao cerca de 11 cm — mais do que suficiente."""
        a = self._valida(latitude=-25.891234)["latitude"]
        b = self._valida(latitude=-25.891235)["latitude"]
        self.assertNotEqual(a, b)

    # --- o que continua a ser recusado ------------------------------------

    def test_um_valor_que_nao_e_numero_continua_a_ser_recusado(self):
        s = AgentDeviceHeartbeatSerializer(
            data={"serial_number": "SN-1", "latitude": "para norte"})
        self.assertFalse(s.is_valid())
        self.assertIn("latitude", s.errors)

    def test_uma_latitude_impossivel_continua_a_ser_recusada(self):
        """Arredondar nao e aceitar tudo: 4 digitos antes da virgula nao cabem
        no campo, e nenhuma coordenada real tem isso."""
        s = AgentDeviceHeartbeatSerializer(
            data={"serial_number": "SN-1", "latitude": 1234.5})
        self.assertFalse(s.is_valid())

    def test_heartbeat_sem_posicao_continua_a_passar(self):
        """O terminal dentro de um edificio nao tem GPS e continua vivo."""
        self._valida()
