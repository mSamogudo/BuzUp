"""Toda a capacidade que uma view exige tem de caber em algum papel.

O caso que motivou este teste: `agents.manage` existia, a view exigia-a, e
nenhum papel a dava — excepto o Administrador, que tem `*`. Resultado prático
para o cliente: para registar quem vende ao balcao era preciso dar a alguem
acesso a tudo, incluindo utilizadores, tarifas e financas.

Uma capacidade que so o curinga alcanca nao e uma permissao: e uma permissao
que ninguem consegue delegar. E quando delegar da trabalho, a saida e sempre a
mesma — dar o papel de Administrador a mais uma pessoa.

Se uma capacidade for MESMO so para administradores, ponha-a em SO_ADMIN. O
teste passa a exigir que essa decisao esteja escrita, em vez de acontecer por
esquecimento.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from django.test import SimpleTestCase, TestCase

from apps.core.permissions.base import DEFAULT_ROLES

# Capacidades deliberadamente reservadas a quem tem `*`. Gerir utilizadores e
# papeis e mexer em quem pode mexer em tudo o resto — nao se delega a meio.
SO_ADMIN = {
    "users.read",
    "users.manage",
    # Papeis definem quem pode o que. Delegar a edicao de papeis e delegar a
    # atribuicao de todas as outras permissoes de uma vez.
    "roles.read",
    "roles.manage",
}


def _capacidades_exigidas() -> dict[str, set[str]]:
    """Varre as views e devolve {capacidade: {onde aparece}}."""
    import apps

    encontradas: dict[str, set[str]] = {}
    for modulo in pkgutil.walk_packages(apps.__path__, prefix="apps."):
        nome = modulo.name
        if not nome.endswith("views") or ".tests" in nome:
            continue
        try:
            m = importlib.import_module(nome)
        except Exception:
            continue  # views que dependem de contexto de pedido nao interessam aqui
        for _, obj in inspect.getmembers(m, inspect.isclass):
            if getattr(obj, "__module__", "") != nome:
                continue
            grupos = []
            por_accao = getattr(obj, "required_capabilities_by_action", None)
            if isinstance(por_accao, dict):
                grupos.extend(por_accao.values())
            directas = getattr(obj, "required_capabilities", None)
            if directas:
                grupos.append(directas)
            for grupo in grupos:
                for cap in grupo or ():
                    encontradas.setdefault(cap, set()).add(f"{nome}.{obj.__name__}")
    return encontradas


class CapacidadesDelegaveisTests(SimpleTestCase):
    def test_nenhuma_capacidade_depende_so_do_curinga(self):
        exigidas = _capacidades_exigidas()
        self.assertTrue(exigidas, "nao foi encontrada nenhuma view com capacidades")

        concedidas = set()
        for codigo, papel in DEFAULT_ROLES.items():
            permissoes = papel.get("permissions", [])
            if "*" in permissoes:
                continue  # o curinga alcanca tudo; nao conta como delegacao
            concedidas.update(permissoes)

        orfas = {
            cap: sorted(onde)
            for cap, onde in exigidas.items()
            if cap not in concedidas and cap not in SO_ADMIN
        }
        self.assertFalse(
            orfas,
            "capacidades que nenhum papel delegavel concede — quem precisar delas "
            "so as consegue com o papel de Administrador (acesso a tudo):\n"
            + "\n".join(f"  {cap}: exigida por {', '.join(onde)}" for cap, onde in sorted(orfas.items()))
            + "\nAcrescente-as ao papel certo em apps/core/permissions/base.py, "
              "ou a SO_ADMIN se forem mesmo exclusivas de administrador.",
        )

    def test_gestor_operacional_regista_quem_vende_ao_balcao(self):
        """O caso concreto: montar a operacao inclui registar os agentes."""
        permissoes = set(DEFAULT_ROLES["operations_manager"]["permissions"])
        self.assertIn("agents.manage", permissoes)
        self.assertIn("agents.read", permissoes)


class SementeDePapeisTests(TestCase):
    """`seed_roles` corre em cada arranque: tem de manter os papeis em dia."""

    def test_papel_de_sistema_desactualizado_e_corrigido(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.users.models import Role

        Role.objects.create(
            code="operations_manager", name="Gestor Operacional",
            permissions=["routes.read"], is_system=True,
        )
        call_command("seed_roles", stdout=StringIO())

        papel = Role.objects.get(code="operations_manager")
        self.assertIn(
            "agents.manage", papel.permissions,
            "um papel de sistema ja existente tem de receber as permissoes novas — "
            "senao corrigir uma permissao no codigo nunca chega a producao",
        )

    def test_papel_proprio_do_cliente_nao_e_reescrito(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.users.models import Role

        Role.objects.create(
            code="support", name="Balcao da TPM-TUR",
            permissions=["passengers.read"], is_system=False,
        )
        call_command("seed_roles", stdout=StringIO())

        papel = Role.objects.get(code="support")
        self.assertEqual(papel.name, "Balcao da TPM-TUR")
        self.assertEqual(papel.permissions, ["passengers.read"],
                         "o que o cliente personalizou nao se reescreve por baixo dele")
