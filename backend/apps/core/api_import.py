from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.import_csv import IMPORTERS, generate_card_template_excel
from apps.core.permissions import HasCapabilities


class ExcelImportView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("imports.manage",)
    parser_classes = [MultiPartParser]

    def post(self, request, resource):
        if resource not in IMPORTERS:
            return Response(
                {"detail": f"Recurso '{resource}' nao suportado. Disponiveis: {', '.join(IMPORTERS.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Ficheiro nao enviado."}, status=status.HTTP_400_BAD_REQUEST)

        content = uploaded.read()
        try:
            result = IMPORTERS[resource](content)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)


class CardTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        excel_content = generate_card_template_excel()
        response = HttpResponse(
            excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="template_cartoes.xlsx"'
        return response
