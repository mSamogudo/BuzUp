"""Endpoints da tabela de precos de uma rota.

O portal trata a tabela como uma grelha origem x destino; estes endpoints
traduzem-na para as regras que o motor de tarifas ja usa (ver
`apps/fares/matrix.py`).
"""

from django.http import HttpResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.fares import matrix as tabela
from apps.fares.services import FareConflictError, NoFareFoundError, quote_fare
from apps.routes.models import Route

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _rota(route_id: int) -> Route | None:
    return Route.objects.filter(pk=route_id).first()


class FareMatrixView(APIView):
    """Ler e gravar a tabela de precos de uma rota."""

    permission_classes = [IsAuthenticated, HasCapabilities]

    def get_required_capabilities(self):
        # Ler a tabela e uma coisa; mudar precos e outra. Gravar exige
        # `fares.manage` mesmo a quem so pode consultar.
        return ("fares.manage",) if self.request.method == "POST" else ("fares.read",)

    def get(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        dados = tabela.read_matrix(rota)
        # Quantos trajectos NAO se vendem hoje. E o numero que interessa a
        # operacao: um par sem preco e uma viagem que o passageiro nao compra.
        dados["unsellable"] = _contar_sem_preco(rota)
        return Response(dados)

    def post(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        try:
            resultado = tabela.write_matrix(
                rota,
                request.data.get("prices") or {},
                fallback_amount=request.data.get("fallback_amount"),
            )
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        dados = tabela.read_matrix(rota)
        dados["saved"] = resultado
        dados["unsellable"] = _contar_sem_preco(rota)
        return Response(dados)


class FareMatrixFillView(APIView):
    """Pre-preenche a grelha por numero de paragens. NAO grava."""

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("fares.read",)

    def post(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        try:
            precos = tabela.fill_by_distance(
                rota, request.data.get("base"), request.data.get("per_stop"),
            )
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        # Devolve para o portal MOSTRAR antes de gravar: uma sugestao aplicada
        # em silencio a 812 pares e impossivel de rever depois.
        return Response({"prices": precos})


class FareMatrixReturnView(APIView):
    """Cria o sentido de VOLTA da rota, espelhando a ida.

    Sem paragens de volta o regresso nao e sequer um trajecto valido — a
    compra e recusada antes de se falar de precos. Era o caso da MZ-NEL: um
    autocarro internacional que so se podia vender num sentido.
    """

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("routes.manage",)

    def post(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        try:
            resultado = tabela.ensure_return_direction(rota)
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        dados = tabela.read_matrix(rota)
        dados["return_created"] = resultado
        dados["unsellable"] = _contar_sem_preco(rota)
        return Response(dados)


class FareMatrixTemplateView(APIView):
    """Descarrega o modelo em Excel, com os pares da rota ja preenchidos."""

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("fares.read",)

    def get(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        metodo = request.query_params.get("method") or "origin_destination"
        try:
            conteudo = tabela.template_xlsx(rota, method=metodo)
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        resposta = HttpResponse(conteudo, content_type=_XLSX)
        nome = f"precos-{rota.code}-{metodo}.xlsx".replace(" ", "-")
        resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
        return resposta


class FareMatrixImportView(APIView):
    """Importa um Excel preenchido.

    Por omissao apenas PRE-VISUALIZA: devolve os precos lidos sem gravar, para
    o operador ver o que vai mudar. So grava com `apply=true`. Uma tabela de
    precos aplicada as cegas e dinheiro cobrado a mais ou a menos em todas as
    viagens ate alguem reparar.
    """

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("fares.manage",)
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, route_id: int):
        rota = _rota(route_id)
        if not rota:
            return Response({"detail": "Rota nao encontrada."}, status=404)
        ficheiro = request.FILES.get("file")
        if not ficheiro:
            return Response({"detail": "Envie o ficheiro Excel preenchido."}, status=400)
        if ficheiro.size > 5 * 1024 * 1024:
            return Response({"detail": "Ficheiro demasiado grande (max. 5 MB)."}, status=400)

        try:
            lido = tabela.parse_xlsx(rota, ficheiro.read())
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        precos = lido["prices"]
        recurso = lido["fallback_amount"]

        aplicar = str(request.data.get("apply") or "").lower() in ("1", "true", "sim")
        if not aplicar:
            antiga = tabela.read_matrix(rota)
            mudam = {k: v for k, v in precos.items() if antiga["prices"].get(k, "") != (v or "")}
            if recurso is not None and antiga["fallback_amount"] != recurso:
                mudam["__recurso__"] = recurso
            return Response({
                "preview": True,
                "prices": precos,
                "fallback_amount": recurso,
                "rows": len(precos) or (1 if recurso is not None else 0),
                "changes": len(mudam),
            })

        try:
            resultado = tabela.write_matrix(rota, precos, fallback_amount=recurso)
        except tabela.MatrixError as e:
            return Response({"detail": str(e)}, status=400)
        dados = tabela.read_matrix(rota)
        dados["saved"] = resultado
        dados["unsellable"] = _contar_sem_preco(rota)
        return Response(dados)


def _contar_sem_preco(rota: Route) -> int:
    """Trajectos validos que hoje nao se conseguem vender."""
    from apps.routes.services import RouteSegmentError, resolve_route_segment

    paragens = tabela.route_stops(rota)
    sem = 0
    for a in paragens:
        for b in paragens:
            if a.id == b.id:
                continue
            try:
                resolve_route_segment(rota, a.id, b.id)
            except RouteSegmentError:
                continue
            try:
                quote_fare(route=rota, origin_stop=a, destination_stop=b)
            except (NoFareFoundError, FareConflictError):
                sem += 1
    return sem
