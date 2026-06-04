from django.core.exceptions import FieldDoesNotExist, ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.permissions import HasCapabilities


class BaseModelViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities_by_action = {}
    allow_restore_action = True

    def get_required_capabilities(self):
        if self.action == "restore":
            return self.required_capabilities_by_action.get("destroy", ())
        return self.required_capabilities_by_action.get(self.action, ())

    def _has_soft_delete_field(self, model):
        try:
            model._meta.get_field("deleted_at")
            return True
        except FieldDoesNotExist:
            return False

    def _soft_delete_scope(self):
        scope = str(self.request.query_params.get("scope") or "active").lower()
        if scope not in {"active", "archived", "all"}:
            return "active"
        return scope

    def _apply_soft_delete_scope(self, queryset):
        if not self._has_soft_delete_field(queryset.model):
            return queryset

        scope = "all" if self.action == "restore" else self._soft_delete_scope()
        if scope == "archived":
            return queryset.filter(deleted_at__isnull=False)
        if scope == "all":
            return queryset
        return queryset.filter(deleted_at__isnull=True)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.none()
        return self._apply_soft_delete_scope(queryset)

    def _raise_model_validation_error(self, exc: DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict) from exc
        if getattr(exc, "messages", None):
            messages = [str(message) for message in exc.messages if str(message).strip()]
            if len(messages) == 1:
                raise ValidationError({"detail": messages[0]}) from exc
            raise ValidationError({"detail": messages}) from exc
        raise ValidationError({"detail": str(exc)}) from exc

    def perform_create(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as exc:
            self._raise_model_validation_error(exc)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as exc:
            self._raise_model_validation_error(exc)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, *args, **kwargs):
        if not self.allow_restore_action:
            raise ValidationError({"detail": "Restore is not available for this resource."})

        instance = self.get_object()
        if not self._has_soft_delete_field(instance.__class__):
            raise ValidationError({"detail": "Restore is not available for this resource."})

        if instance.deleted_at is None:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        try:
            instance.restore()
        except IntegrityError as exc:
            raise ValidationError(
                {"detail": "Unable to restore this record because one or more active identifiers are already in use."}
            ) from exc

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
