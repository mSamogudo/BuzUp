def generate_sequential_code(prefix: str, model, field: str = "code") -> str:
    from django.db.models import Max

    last = model.all_objects.aggregate(max_val=Max(field))["max_val"] or ""
    if last.startswith(prefix):
        try:
            num = int(last[len(prefix):].lstrip("-").lstrip("0") or "0")
        except ValueError:
            num = 0
    else:
        num = model.all_objects.count()

    next_num = num + 1
    return f"{prefix}-{next_num:04d}"


def generate_code_from_name(
    name: str,
    prefix: str,
    model,
    field: str = "code",
    instance=None,
    separator: str = "-",
    uppercase: bool = True,
) -> str:
    from django.core.exceptions import FieldDoesNotExist
    from django.utils.text import slugify

    normalized_separator = separator or "-"
    slug = slugify(name or "", allow_unicode=False).replace("-", normalized_separator).strip(normalized_separator)
    if not slug:
        slug = "item"

    prefix_part = str(prefix or "").strip().strip(normalized_separator)
    code_base = f"{prefix_part}{normalized_separator}{slug}" if prefix_part else slug
    code_base = code_base.upper() if uppercase else code_base.lower()

    model_field = model._meta.get_field(field)
    max_length = getattr(model_field, "max_length", None) or 32

    def truncate(value: str, suffix: str = "") -> str:
        room = max_length - len(suffix)
        return f"{value[:room].rstrip(normalized_separator)}{suffix}"[:max_length]

    queryset = model.all_objects.all()
    if not getattr(model_field, "unique", False):
        try:
            model._meta.get_field("deleted_at")
        except FieldDoesNotExist:
            pass
        else:
            queryset = queryset.filter(deleted_at__isnull=True)

    if instance is not None and getattr(instance, "pk", None):
        queryset = queryset.exclude(pk=instance.pk)

    candidate = truncate(code_base)
    if not queryset.filter(**{field: candidate}).exists():
        return candidate

    for index in range(2, 1000):
        suffix = f"{normalized_separator}{index:02d}"
        candidate = truncate(code_base, suffix)
        if not queryset.filter(**{field: candidate}).exists():
            return candidate

    return generate_sequential_code((prefix_part or slug[:3]).upper(), model, field)
