import logging

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Estado real do serviço, não um "ok" fixo.

    A versão anterior devolvia sempre 200 sem tocar em nada. Como este endpoint
    alimenta o healthcheck do contentor, o gate de deploy e o monitor externo,
    o resultado era que com o Postgres em baixo tudo continuava a dizer
    "healthy": a operação estava parada e nenhum alarme tocava.

    `?deep=0` faz a verificação mínima (só processo vivo), para quem quiser um
    ping barato.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    # Um healthcheck que o throttle pode recusar deixa de ser um healthcheck.
    throttle_classes = []

    def get(self, request):
        if request.query_params.get("deep") == "0":
            return Response({"status": "ok", "service": "buzup-backend"})

        checks: dict[str, str] = {}
        healthy = True

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception as exc:
            healthy = False
            checks["database"] = "erro"
            logger.error("health: base de dados inacessivel: %s", exc)

        # A cache guarda os limites de OTP; sem ela o login por código falha.
        # Não é fatal para vender bilhetes, por isso é reportada mas não
        # derruba o estado geral.
        try:
            cache.set("health:ping", "1", 10)
            checks["cache"] = "ok" if cache.get("health:ping") == "1" else "degradado"
        except Exception as exc:
            checks["cache"] = "erro"
            logger.warning("health: cache inacessivel: %s", exc)

        return Response(
            {
                "status": "ok" if healthy else "erro",
                "service": "buzup-backend",
                "checks": checks,
            },
            status=200 if healthy else 503,
        )
