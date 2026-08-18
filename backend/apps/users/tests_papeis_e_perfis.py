"""Um papel do portal tem de valer exactamente o que diz — nem mais nem menos.

Dois defeitos que apareceram juntos em producao, ambos invisiveis a quem
usava o portal:

1. Retirar um papel a alguem nao lhe retirava as permissoes. O vinculo era
   marcado como apagado, mas a relacao many-to-many junta a tabela intermedia
   directamente e continuava a contar. Quem tinha sido despromovido continuava
   a poder tudo o que podia antes.

2. Marcar alguem como Motorista nao o punha na lista de motoristas. O papel
   ficava no utilizador; o selector da viagem le a tabela `Driver`, que
   continuava vazia. O cliente marcou duas pessoas como motoristas e depois nao
   as encontrou para alocar a viagem, sem nenhuma mensagem a explicar porque.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.trips.models import Agent, Driver
from apps.users.models import Role, UserRole


class PapeisTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="raiz", password="x", email="raiz@x.mz")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        # Papeis de sistema: ja vêm das migracoes, por isso reutiliza-se.
        self.motorista = self.papel("driver", "Motorista", [])
        self.gestor = self.papel("operations_manager", "Gestor Operacional", ["trips.manage"])
        self.alvo = User.objects.create_user(
            username="ajoaquim", password="x", email="a@x.mz",
            first_name="Antonio", last_name="Joaquim", phone="841112222")

    @staticmethod
    def papel(code, name, permissions):
        papel, _ = Role.objects.get_or_create(
            code=code, defaults={"name": name, "permissions": permissions, "is_system": True})
        if papel.permissions != permissions:
            papel.permissions = permissions
            papel.save(update_fields=["permissions", "updated_at"])
        return papel

    def poe_papeis(self, *papeis):
        r = self.client.patch(
            f"/api/admin/users/{self.alvo.id}/",
            {"role_ids": [p.id for p in papeis]}, format="json",
        )
        self.assertIn(r.status_code, (200, 202), r.content)
        self.alvo.refresh_from_db()

    def test_papel_retirado_deixa_de_dar_permissao(self):
        self.poe_papeis(self.gestor)
        self.assertIn("trips.manage", self.alvo.get_capabilities())

        self.poe_papeis()
        self.assertNotIn(
            "trips.manage", self.alvo.get_capabilities(),
            "retirar o papel no portal tem de retirar mesmo a permissao",
        )

    def test_vinculos_nao_se_acumulam_a_cada_gravacao(self):
        for _ in range(3):
            self.poe_papeis(self.gestor)
        self.assertEqual(
            UserRole.all_objects.filter(user=self.alvo).count(), 1,
            "gravar o mesmo utilizador tres vezes nao pode deixar tres vinculos",
        )

    def test_papel_de_motorista_cria_o_motorista(self):
        self.poe_papeis(self.motorista)
        perfil = Driver.objects.filter(user=self.alvo).first()
        self.assertIsNotNone(
            perfil, "marcar alguem como Motorista tem de o pôr na lista de motoristas")
        self.assertEqual(perfil.full_name, "Antonio Joaquim")
        self.assertEqual(perfil.phone, "841112222")
        self.assertEqual(perfil.status, Driver.Status.ACTIVE)

    def test_motorista_aparece_no_selector_da_viagem(self):
        """O sintoma tal como o cliente o viu."""
        self.poe_papeis(self.motorista)
        r = self.client.get("/api/drivers/")
        self.assertEqual(r.status_code, 200, r.content)
        corpo = r.json()
        nomes = [d["full_name"] for d in (corpo.get("results") or corpo)]
        self.assertIn("Antonio Joaquim", nomes)

    def test_tirar_o_papel_inactiva_em_vez_de_apagar(self):
        """Um motorista tem viagens atras dele: nao se apaga por uma caixa."""
        self.poe_papeis(self.motorista)
        self.poe_papeis()
        perfil = Driver.all_objects.filter(user=self.alvo).first()
        self.assertIsNotNone(perfil, "o registo do motorista nao se apaga")
        self.assertEqual(perfil.status, Driver.Status.INACTIVE)

    def test_repor_o_papel_reactiva_o_mesmo_registo(self):
        self.poe_papeis(self.motorista)
        primeiro = Driver.objects.get(user=self.alvo).id
        self.poe_papeis()
        self.poe_papeis(self.motorista)
        self.assertEqual(
            Driver.all_objects.filter(user=self.alvo).count(), 1,
            "ir e voltar nao pode deixar dois motoristas para a mesma pessoa",
        )
        self.assertEqual(Driver.objects.get(user=self.alvo).id, primeiro)

    def test_papel_de_agente_cria_o_agente(self):
        agente = self.papel("pos_agent", "Agente POS", ["pos.operate"])
        self.poe_papeis(agente)
        self.assertTrue(Agent.objects.filter(user=self.alvo).exists())
