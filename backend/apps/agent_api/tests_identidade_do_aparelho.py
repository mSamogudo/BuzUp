"""Cada aparelho tem de ser um aparelho.

Em producao encontrou-se um unico dispositivo registado com o serial
`unknown` — e era o terminal SUNMI que estava a ser usado a serio. Desde o
Android 10 a plataforma responde a string literal `"unknown"` quando a
aplicacao nao tem direito ao numero de serie, e o registo aceitava-a como se
fosse um identificador.

Consequencia: o segundo aparelho a instalar a app nao criava dispositivo
nenhum — entrava no do primeiro. Bloquear um bloqueava todos; a posicao GPS do
autocarro no mapa dos passageiros vinha do ultimo a fazer ping; e nenhuma venda
ficava atribuivel ao terminal onde foi feita. Era tambem o que impedia a app de
servir telemoveis, onde o serial nunca se le.
"""

from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from apps.devices.models import Device


class RegistoDeAparelhoTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def registar(self, serial):
        return self.client.post(
            "/api/agent/devices/self-onboard/",
            {"serial_number": serial, "device_type": "mobile_app"},
            format="json",
        )

    def test_serial_proprio_e_aceite(self):
        r = self.registar("V2S1234567890")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(Device.objects.filter(serial_number="V2S1234567890").exists())

    def test_serial_de_recurso_do_android_e_recusado(self):
        for placeholder in ["unknown", "UNKNOWN", " unknown ", "null", "0"]:
            with self.subTest(placeholder=placeholder):
                r = self.registar(placeholder)
                self.assertEqual(r.status_code, 400, f"{placeholder!r} nao e um identificador")
        self.assertEqual(Device.all_objects.count(), 0)

    def test_dois_telemoveis_ficam_dois_dispositivos(self):
        """Sem identidade propria, o segundo entrava no dispositivo do primeiro."""
        self.assertEqual(self.registar("INS-aaaaaaaaaaaaaaaaaaaaaa").status_code, 201)
        self.assertEqual(self.registar("INS-bbbbbbbbbbbbbbbbbbbbbb").status_code, 201)
        self.assertEqual(Device.objects.count(), 2)
