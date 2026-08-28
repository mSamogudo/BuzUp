"""O terminal: quem e, e quando deixa de poder vender.

A app `devices` nao tinha um unico teste, e e ela que responde a duas
perguntas com consequencias no terreno:

* **quem e este aparelho?** — se dois terminais partilharem identidade, nenhuma
  venda fica atribuivel a quem a fez, e bloquear um bloqueia os dois;
* **ainda pode vender?** — um terminal roubado tem de parar no instante em que
  o operador o bloqueia no portal.

Ambas ja falharam em producao, e por isso estao aqui:

1. O Android devolve `unknown` quando nao ha numero de serie. Aceitar isso fazia
   com que todos os aparelhos entrassem por cima do mesmo registo.
2. `get_authorized_device` devolvia `None` para um terminal bloqueado, e a
   verificacao a jusante era `if device and device.status == BLOCKED`. Sem
   dispositivo, a condicao era falsa e a venda passava — bloquear um terminal
   roubado nao o impedia de continuar a vender.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.agent_api.permissions import DeviceBlocked, get_authorized_device
from apps.agent_api.serializers import SERIAIS_SEM_VALOR, AgentDeviceRegisterSerializer
from apps.devices.models import Device
from apps.trips.models import Agent


def _terminal(serial, status=Device.Status.ACTIVE, agente=None):
    return Device.objects.create(
        serial_number=serial,
        device_type=Device.DeviceType.SUNMI_V2S_POS,
        status=status,
        assigned_agent=agente,
        activation_code=Device.generate_activation_code(),
    )


class SerialSemValorTests(TestCase):
    """"unknown" nao e um identificador: e a plataforma a dizer "nao sei"."""

    def test_recusa_os_serials_que_significam_nao_sei(self):
        for serial in SERIAIS_SEM_VALOR:
            s = AgentDeviceRegisterSerializer(data={
                "serial_number": serial, "device_type": "sunmi_v2s_pos"})
            self.assertFalse(s.is_valid(), f"{serial!r} devia ter sido recusado")
            self.assertIn("serial_number", s.errors)

    def test_recusa_independentemente_das_maiusculas(self):
        for serial in ("UNKNOWN", "Unknown", " unknown "):
            s = AgentDeviceRegisterSerializer(data={
                "serial_number": serial, "device_type": "sunmi_v2s_pos"})
            self.assertFalse(s.is_valid(), f"{serial!r} devia ter sido recusado")

    def test_recusa_serial_vazio(self):
        s = AgentDeviceRegisterSerializer(data={
            "serial_number": "   ", "device_type": "sunmi_v2s_pos"})
        self.assertFalse(s.is_valid())

    def test_aceita_um_serial_a_serio(self):
        s = AgentDeviceRegisterSerializer(data={
            "serial_number": " 80042514040013 ", "device_type": "sunmi_v2s_pos"})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["serial_number"], "80042514040013")


class TerminalBloqueadoParaTests(TestCase):
    """Bloquear no portal tem de parar o aparelho, nao so escondê-lo."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="agente", email="a@x.mz", password="x", phone="849002000")
        Agent.objects.create(user=self.user, full_name="Agente", status=Agent.Status.ACTIVE)

    def test_bloqueado_levanta_em_vez_de_devolver_nada(self):
        """O ponto exacto do defeito antigo.

        Devolver `None` fazia a chamada seguir "sem dispositivo", e a guarda a
        jusante (`if device and ...`) dava falso. A venda passava.
        """
        _terminal("SN-ROUBADO", status=Device.Status.BLOCKED)
        with self.assertRaises(DeviceBlocked):
            get_authorized_device(self.user, "SN-ROUBADO")

    def test_bloqueado_tambem_levanta_quando_esta_alocado_ao_agente(self):
        """Sem serial no pedido, resolve-se pela alocacao — e a regra e a mesma."""
        _terminal("SN-ALOCADO", status=Device.Status.BLOCKED, agente=self.user)
        with self.assertRaises(DeviceBlocked):
            get_authorized_device(self.user)

    def test_um_terminal_activo_resolve_normalmente(self):
        d = _terminal("SN-BOM")
        self.assertEqual(get_authorized_device(self.user, "SN-BOM"), d)

    def test_serial_desconhecido_nao_levanta_e_nao_inventa_terminal(self):
        self.assertIsNone(get_authorized_device(self.user, "SN-QUE-NAO-EXISTE"))

    def test_sem_sessao_nao_ha_terminal(self):
        self.assertIsNone(get_authorized_device(None, "SN-BOM"))


class RegistoDoTerminalTests(TestCase):
    """O que acontece quando um aparelho se apresenta ao servidor."""

    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ag2", email="a2@x.mz", password="x", phone="849002001")
        Agent.objects.create(user=self.user, full_name="Agente 2", status=Agent.Status.ACTIVE)
        # O registo e sem sessao: o aparelho apresenta-se ANTES de alguem
        # poder entrar nele.

    def _registar(self, serial, **extra):
        corpo = {"serial_number": serial, "device_type": "sunmi_v2s_pos"}
        corpo.update(extra)
        return self.client.post("/api/agent/devices/self-onboard/", corpo, format="json")

    def test_um_terminal_bloqueado_nao_se_volta_a_registar(self):
        """Reinstalar a app nao pode ser a maneira de contornar um bloqueio."""
        _terminal("SN-BLOQ-REG", status=Device.Status.BLOCKED)
        r = self._registar("SN-BLOQ-REG")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(
            Device.objects.get(serial_number="SN-BLOQ-REG").status,
            Device.Status.BLOCKED)

    def test_registar_com_serial_sem_valor_e_recusado(self):
        r = self._registar("unknown")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(Device.objects.filter(serial_number="unknown").exists())

    def test_o_mesmo_serial_nao_cria_um_segundo_registo(self):
        """Senao cada arranque da app duplicava o terminal."""
        self._registar("SN-REPETIDO")
        self._registar("SN-REPETIDO")
        self.assertEqual(
            Device.objects.filter(serial_number="SN-REPETIDO").count(), 1)

    def test_o_registo_guarda_a_versao_que_o_aparelho_diz_ter(self):
        """E dela que depende exigir identidade do passageiro (>= 1.8.0)."""
        self._registar("SN-VERSAO", app_version="1.9.0", app_version_code=37)
        d = Device.objects.get(serial_number="SN-VERSAO")
        self.assertEqual(d.app_version, "1.9.0")
        self.assertEqual(d.app_version_code, 37)

    def test_um_terminal_apagado_que_volta_pede_aprovacao_outra_vez(self):
        """Apagar e voltar a instalar nao devolve o acesso que se tinha."""
        d = _terminal("SN-VOLTOU")
        d.delete()  # soft delete
        self._registar("SN-VOLTOU")
        d = Device.all_objects.get(serial_number="SN-VOLTOU")
        self.assertIsNone(d.deleted_at)
        self.assertEqual(d.status, Device.Status.SELF_ONBOARDED)
        self.assertIsNone(d.assigned_agent_id)


class CodigoDeActivacaoTests(TestCase):
    def test_cada_terminal_nasce_com_o_seu_codigo(self):
        a = _terminal("SN-COD-A", status=Device.Status.PENDING_ACTIVATION)
        b = _terminal("SN-COD-B", status=Device.Status.PENDING_ACTIVATION)
        self.assertTrue(a.activation_code)
        self.assertNotEqual(a.activation_code, b.activation_code)

    def test_o_codigo_nao_e_adivinhavel_por_ser_curto(self):
        """8 caracteres hexadecimais: 4 mil milhoes de hipoteses.

        Curto o suficiente para se ditar ao telefone, longo o suficiente para
        nao se acertar por tentativa.
        """
        c = Device.generate_activation_code()
        self.assertEqual(len(c), 8)
        self.assertTrue(all(ch in "0123456789ABCDEF" for ch in c), c)
