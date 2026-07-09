import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.leads.api.serializers import ContactLeadSerializer
from apps.leads.models import ContactLead

logger = logging.getLogger(__name__)


class ContactLeadCreateView(APIView):
    """Public endpoint for the marketing site contact form and app waitlist."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def post(self, request):
        serializer = ContactLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead = serializer.save(
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:400],
        )

        _notify_sales(lead)

        return Response(
            {"detail": "Mensagem recebida. Entraremos em contacto em breve."},
            status=status.HTTP_201_CREATED,
        )


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def _notify_sales(lead: ContactLead) -> None:
    """Best-effort email to sales. The lead is already persisted; never fail the
    request because the mail server hiccuped."""
    recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", "") or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not recipient:
        return

    label = lead.get_source_display()
    subject = f"[BuzUp] {label}: {lead.name or lead.email}"
    body = "\n".join(
        line for line in [
            f"Origem: {label}",
            f"Perfil: {lead.get_profile_display()}" if lead.profile else "",
            f"Nome: {lead.name}" if lead.name else "",
            f"Organização: {lead.organization}" if lead.organization else "",
            f"Email: {lead.email}",
            f"Telefone: {lead.phone}" if lead.phone else "",
            f"Idioma: {lead.locale}" if lead.locale else "",
            "",
            lead.message or "(sem mensagem)",
        ] if line != ""
    )
    try:
        from django.core.mail import EmailMessage

        EmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[recipient],
            reply_to=[lead.email] if lead.email else None,
        ).send(fail_silently=False)
    except Exception:  # pragma: no cover - notification must not break intake
        logger.exception("Failed to send contact-lead notification for lead #%s", lead.pk)
