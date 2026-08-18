"""Programar partidas marcando os dias, sem horario recorrente.

O `RouteSchedule` descreve uma carreira urbana — de 30 em 30 minutos, das 06h
as 20h, nestes dias da semana. Numa carreira internacional ha uma partida por
dia, em dias que nao seguem regra: feriados, epoca alta, o dia em que o
autocarro esta na oficina. Exprimir isso como frequencia obrigava a inventar
uma hora de fim e uma cadencia para uma unica saida, e ainda assim nao deixava
saltar um dia a meio.

E havia um beco: sem nenhum horario criado, o assistente de programacao abria
com a lista vazia e nao havia caminho nenhum a partir dali.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route
from apps.trips.models import Driver, Trip, Vehicle


class ProgramarPorCalendarioTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="planeador", password="x", email="p@x.mz")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        self.rota = Route.objects.create(
            code="RT-MPM-NLP", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.viatura = Vehicle.objects.create(registration="LJP-553-MP", seated_capacity=52)
        self.motorista = Driver.objects.create(full_name="Antonio Joaquim")

    def programar(self, **corpo):
        corpo.setdefault("route_id", self.rota.id)
        return self.client.post("/api/trips/schedule-days/", corpo, format="json")

    def dias(self, quantos, inicio=1):
        base = timezone.localdate()
        return [(base + timedelta(days=inicio + i)).isoformat() for i in range(quantos)]

    def test_dias_marcados_viram_partidas(self):
        r = self.programar(
            dates=self.dias(3), times=["05:00"],
            vehicle_id=self.viatura.id, driver_id=self.motorista.id,
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["created"], 3)
        self.assertEqual(Trip.objects.count(), 3)
        for viagem in Trip.objects.all():
            self.assertEqual(viagem.status, Trip.Status.SCHEDULED)
            self.assertEqual(viagem.vehicle_id, self.viatura.id)
            self.assertEqual(viagem.driver_id, self.motorista.id)
            self.assertEqual(timezone.localtime(viagem.planned_departure_at).hour, 5)

    def test_dias_salteados_sao_respeitados(self):
        """O que a frequencia semanal nao sabia fazer: saltar um dia a meio."""
        base = timezone.localdate()
        escolhidos = [(base + timedelta(days=d)).isoformat() for d in (1, 2, 5, 9)]
        r = self.programar(dates=escolhidos, times=["05:00"])
        self.assertEqual(r.status_code, 201, r.content)
        partidas = sorted(
            timezone.localdate(t.planned_departure_at).isoformat() for t in Trip.objects.all())
        self.assertEqual(partidas, sorted(escolhidos))

    def test_ida_e_volta_no_mesmo_dia(self):
        r = self.programar(dates=self.dias(2), times=["05:00", "15:30"])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["created"], 4)

    def test_duracao_preenche_a_chegada_prevista(self):
        r = self.programar(dates=self.dias(1), times=["05:00"], duration_minutes=270)
        self.assertEqual(r.status_code, 201, r.content)
        viagem = Trip.objects.get()
        self.assertEqual(
            viagem.planned_arrival_at - viagem.planned_departure_at, timedelta(minutes=270))

    def test_repetir_a_mesma_marcacao_nao_duplica(self):
        """O operador carrega duas vezes; nao pode acabar com duas partidas."""
        escolhidos = self.dias(3)
        self.programar(dates=escolhidos, times=["05:00"], vehicle_id=self.viatura.id)
        r = self.programar(dates=escolhidos, times=["05:00"], vehicle_id=self.viatura.id)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["created"], 0)
        self.assertEqual(r.json()["already_scheduled"], 3)
        self.assertEqual(Trip.objects.count(), 3)

    def test_previsualizacao_nao_cria_nada(self):
        r = self.programar(dates=self.dias(4), times=["05:00", "15:00"], preview=True)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["would_generate"], 8)
        self.assertEqual(r.json()["created"], 0)
        self.assertEqual(Trip.objects.count(), 0)
        self.assertEqual(len(r.json()["by_day"]), 4)

    def test_rota_inactiva_e_recusada(self):
        self.rota.status = Route.Status.INACTIVE
        self.rota.save(update_fields=["status", "updated_at"])
        self.assertEqual(self.programar(dates=self.dias(1), times=["05:00"]).status_code, 404)

    def test_nao_se_programa_um_ano_por_engano(self):
        r = self.programar(dates=self.dias(120), times=["05:00"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(Trip.objects.count(), 0)

    def test_sem_permissao_nao_programa(self):
        User = get_user_model()
        ze = User.objects.create_user(username="ze", password="x", email="ze@x.mz")
        self.client.force_authenticate(ze)
        self.assertEqual(self.programar(dates=self.dias(1), times=["05:00"]).status_code, 403)
