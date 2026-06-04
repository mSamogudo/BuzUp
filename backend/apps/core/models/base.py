from uuid import uuid4

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        update_kwargs = {"deleted_at": timezone.now()}
        for field_name, value in (("updated_at", timezone.now()), ("is_active", False)):
            try:
                self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            update_kwargs[field_name] = value
        return super().update(**update_kwargs)

    def hard_delete(self):
        return super().delete()

    def restore(self):
        update_kwargs = {"deleted_at": None}
        for field_name, value in (("updated_at", timezone.now()), ("is_active", True)):
            try:
                self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            update_kwargs[field_name] = value
        return super().update(**update_kwargs)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().alive()


class SoftDeleteAllManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


def active_unique_constraint(*fields, name):
    return models.UniqueConstraint(fields=fields, condition=Q(deleted_at__isnull=True), name=name)


class BaseModel(models.Model):
    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def get_soft_delete_updates(self):
        return {}

    def delete(self, using=None, keep_parents=False, hard=False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        if self.deleted_at is not None:
            return
        from django.db import transaction

        with transaction.atomic():
            soft_delete_updates = self.get_soft_delete_updates() or {}
            self.deleted_at = timezone.now()
            update_fields = ["deleted_at", "updated_at"]
            if hasattr(self, "is_active"):
                self.is_active = False
                update_fields.append("is_active")
            for field_name, value in soft_delete_updates.items():
                setattr(self, field_name, value)
                update_fields.append(field_name)
            self.save(update_fields=update_fields)
            self._cascade_soft_delete()

    def _cascade_soft_delete(self):
        """Soft-delete alive children reached through on_delete=CASCADE FKs.

        Mirrors the developer's declared CASCADE intent under soft-delete so a
        soft-deleted parent doesn't leave dangling active children (which would
        also keep occupying active unique constraints). SET_NULL/PROTECT FKs are
        intentionally left untouched — historical/financial records (tickets,
        payments, wallet transactions) use those, so they are never auto-removed.
        """
        for rel in self._meta.related_objects:
            if getattr(rel, "on_delete", None) is not models.CASCADE:
                continue
            related_model = rel.related_model
            if not (isinstance(related_model, type) and issubclass(related_model, BaseModel)):
                continue
            for child in related_model.objects.filter(**{rel.field.name: self}):
                child.delete()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        update_fields = ["deleted_at", "updated_at"]
        if hasattr(self, "is_active"):
            self.is_active = True
            update_fields.append("is_active")
        self.save(update_fields=update_fields)
