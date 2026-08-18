"""Ver a planta antes de gravar a viatura.

O operador escolhia "2+2" numa lista e nunca via o resultado — tinha de o
imaginar. Num autocarro de 50 lugares engana-se pouco; num minibus de 15, a
diferenca entre 2+2 e 1+2 e a diferenca entre uma planta que existe e uma que o
passageiro nao vai encontrar a bordo.

A pre-visualizacao e calculada no servidor de proposito: a regra da planta e
uma so, e escreve-la outra vez no browser era garantir que um dia deixavam de
concordar — e o operador via uma planta e o passageiro outra.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class PrevisualizacaoDaPlantaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username="raiz", password="x", email="r@x.mz")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def previa(self, **params):
        return self.client.get("/api/vehicles/seat-preview/", params)

    def test_minibus_de_quinze_em_dois_mais_dois(self):
        r = self.previa(capacity=15, layout="2+2")
        self.assertEqual(r.status_code, 200, r.content)
        corpo = r.json()
        self.assertEqual(corpo["seats"], 15)
        self.assertEqual(len(corpo["rows"]), 4)
        # A ultima fila tem um banco a direita onde as outras tem dois — e e
        # exactamente isso que o operador precisa de ver antes de gravar.
        self.assertEqual(len(corpo["rows"][-1]["right"]), 1)

    def test_o_mesmo_minibus_em_um_mais_dois_fecha_certo(self):
        corpo = self.previa(capacity=15, layout="1+2").json()
        self.assertEqual(corpo["seats"], 15)
        self.assertEqual(len(corpo["rows"]), 5)
        self.assertTrue(all(len(f["left"]) == 1 and len(f["right"]) == 2 for f in corpo["rows"]))

    def test_fila_do_fundo_corrida(self):
        corpo = self.previa(capacity=15, layout="2+2", last_row=3).json()
        self.assertTrue(corpo["rows"][-1]["full_width"])
        self.assertEqual(len(corpo["rows"][-1]["left"]), 3)
        self.assertEqual(corpo["seats"], 15)

    def test_a_previa_nunca_perde_nem_inventa_lugares(self):
        for capacidade in (1, 7, 12, 15, 28, 52):
            for layout in ("1+1", "1+2", "2+1", "2+2", "2+3", "3+2"):
                with self.subTest(capacidade=capacidade, layout=layout):
                    self.assertEqual(
                        self.previa(capacity=capacidade, layout=layout).json()["seats"],
                        capacidade,
                    )

    def test_sem_lotacao_devolve_planta_vazia(self):
        corpo = self.previa(capacity=0, layout="2+2").json()
        self.assertEqual(corpo["rows"], [])

    def test_valores_absurdos_sao_recusados(self):
        """Um engano num campo nao pode devolver mil filas."""
        self.assertEqual(self.previa(capacity=5000, layout="2+2").status_code, 400)
        self.assertEqual(self.previa(capacity=-3, layout="2+2").status_code, 400)
        self.assertEqual(self.previa(capacity="abc", layout="2+2").status_code, 400)

    def test_layout_invalido_cai_no_de_omissao(self):
        corpo = self.previa(capacity=8, layout="isto-nao-e-layout").json()
        self.assertEqual(corpo["seats"], 8)
        self.assertEqual(len(corpo["rows"]), 2)

    def test_sem_permissao_nao_ve(self):
        User = get_user_model()
        ze = User.objects.create_user(username="ze", password="x", email="z@x.mz")
        self.client.force_authenticate(ze)
        self.assertEqual(self.previa(capacity=15, layout="2+2").status_code, 403)
