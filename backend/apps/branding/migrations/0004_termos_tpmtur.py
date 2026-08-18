"""Semeia os termos e os contactos da TPM-TUR.

Só preenche o que estiver vazio: se alguém já escreveu termos no portal, esta
migração não lhes toca. Semear por cima seria substituir a política do cliente
pela transcrição de um papel.
"""

from django.db import migrations
from django.utils import timezone


def semear(apps, schema_editor):
    from apps.branding.termos_tpmtur import EMPRESA, FECHO, INTRO, SECCOES, VERSAO

    Branding = apps.get_model("branding", "BrandingSettings")
    marca, _ = Branding.objects.get_or_create(key="default")

    campos = []
    if not marca.terms_sections:
        marca.terms_sections = SECCOES
        marca.terms_intro = INTRO
        marca.terms_closing = FECHO
        marca.terms_version = VERSAO
        marca.terms_updated_at = timezone.now()
        campos += ["terms_sections", "terms_intro", "terms_closing",
                   "terms_version", "terms_updated_at"]

    for campo, valor in EMPRESA.items():
        if not getattr(marca, campo, None):
            setattr(marca, campo, valor)
            campos.append(campo)

    if campos:
        marca.save(update_fields=[*set(campos), "updated_at"])


class Migration(migrations.Migration):

    dependencies = [("branding", "0003_termos_e_contactos")]

    operations = [
        # Sem inverso: apagar os termos do cliente porque se reverteu uma
        # migração seria destruir o que ele escreveu.
        migrations.RunPython(semear, migrations.RunPython.noop),
    ]
