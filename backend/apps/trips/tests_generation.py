"""Programacao de viagens: intervalo de datas, pre-visualizacao e idempotencia.

O numero que a pre-visualizacao mostra tem de ser exactamente o numero de
viagens que a geracao cria a seguir — senao o operador aprova uma coisa e
recebe outra.
"""

from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.routes.models import Route
from apps.trips.models import RouteSchedule, Trip
from apps.trips.services import count_daily_trips, generate_daily_trips


class GenerationBase(TestCase):
    def setUp(self):
        self.route = Route.objects.create(code="R-GEN", name="Rota Geracao",
                                          status=Route.Status.ACTIVE)
        # 06:00 -> 10:00 de 60 em 60 = 5 partidas por dia (inclui as pontas).
        self.schedule = RouteSchedule.objects.create(
            route=self.route, start_time=time(6, 0), end_time=time(10, 0),
            frequency_minutes=60, days_of_week=[], status=RouteSchedule.Status.ACTIVE,
        )

    def _client(self):
        User = get_user_model()
        user = User.objects.create_superuser(username="op_gen", password="x",
                                             email="op@x.mz")
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return client


class CountMatchesGenerationTests(GenerationBase):
    def test_preview_count_equals_what_generation_creates(self):
        dia = timezone.now().date() + timedelta(days=3)
        previsto = count_daily_trips(self.schedule, dia)
        criadas = generate_daily_trips(self.schedule, dia)
        self.assertEqual(previsto, 5)
        self.assertEqual(len(criadas), previsto,
                         "a pre-visualizacao anunciou um numero diferente do criado")

    def test_second_run_creates_nothing_and_preview_says_zero(self):
        dia = timezone.now().date() + timedelta(days=3)
        generate_daily_trips(self.schedule, dia)
        self.assertEqual(count_daily_trips(self.schedule, dia), 0,
                         "ja estao criadas: a pre-visualizacao tinha de dizer 0")
        self.assertEqual(len(generate_daily_trips(self.schedule, dia)), 0)

    def test_weekday_filter_is_respected(self):
        # So segundas (0).
        self.schedule.days_of_week = [0]
        self.schedule.save(update_fields=["days_of_week"])
        segunda = date(2026, 8, 3)          # uma segunda-feira
        terca = date(2026, 8, 4)
        self.assertEqual(count_daily_trips(self.schedule, segunda), 5)
        self.assertEqual(count_daily_trips(self.schedule, terca), 0)

    def test_inactive_schedule_generates_nothing(self):
        self.schedule.status = RouteSchedule.Status.INACTIVE
        self.schedule.save(update_fields=["status"])
        dia = timezone.now().date()
        self.assertEqual(count_daily_trips(self.schedule, dia), 0)
        self.assertEqual(len(generate_daily_trips(self.schedule, dia)), 0)


class GenerateEndpointTests(GenerationBase):
    def test_preview_does_not_create_anything(self):
        client = self._client()
        res = client.post("/api/trips/generate/", {
            "schedule_id": self.schedule.id, "days": 7, "preview": True,
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["generated"], 0)
        self.assertEqual(res.data["would_generate"], 35)  # 5 partidas x 7 dias
        self.assertEqual(len(res.data["by_day"]), 7)
        self.assertEqual(Trip.objects.count(), 0,
                         "a pre-visualizacao criou viagens")

    def test_range_generation_creates_for_every_day(self):
        client = self._client()
        res = client.post("/api/trips/generate/", {
            "schedule_id": self.schedule.id, "days": 3,
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["generated"], 15)
        self.assertEqual(Trip.objects.count(), 15)
        dias = {t.planned_departure_at.date() for t in Trip.objects.all()}
        self.assertEqual(len(dias), 3)

    def test_preview_number_matches_the_real_run(self):
        client = self._client()
        prev = client.post("/api/trips/generate/", {
            "days": 5, "preview": True,
        }, format="json").data["would_generate"]
        real = client.post("/api/trips/generate/", {"days": 5}, format="json").data["generated"]
        self.assertEqual(prev, real,
                         "o assistente prometeu um numero e criou outro")

    def test_without_schedule_id_uses_all_active_schedules(self):
        outra = Route.objects.create(code="R-GEN2", name="Segunda",
                                     status=Route.Status.ACTIVE)
        RouteSchedule.objects.create(
            route=outra, start_time=time(7, 0), end_time=time(8, 0),
            frequency_minutes=60, days_of_week=[], status=RouteSchedule.Status.ACTIVE,
        )
        client = self._client()
        res = client.post("/api/trips/generate/", {"days": 1}, format="json")
        self.assertEqual(res.data["schedules_considered"], 2)
        self.assertEqual(res.data["generated"], 5 + 2)
        self.assertEqual(len(res.data["by_schedule"]), 2)

    def test_days_above_the_cap_are_refused(self):
        client = self._client()
        res = client.post("/api/trips/generate/", {"days": 60}, format="json")
        self.assertEqual(res.status_code, 400,
                         "60 dias devia ser recusado pelo tecto de 30")

    def test_old_call_shape_still_works(self):
        """Sem `days` nem `date_from`: um dia, como era antes."""
        client = self._client()
        res = client.post("/api/trips/generate/",
                          {"schedule_id": self.schedule.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["generated"], 5)
