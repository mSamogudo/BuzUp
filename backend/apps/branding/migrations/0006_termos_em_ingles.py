"""Semeia a versao inglesa dos termos, tal como impressa no bilhete.

Só preenche o que estiver vazio, como a semente portuguesa: se alguém já
escreveu a versão inglesa no portal, esta migração não lhe toca.
"""

from django.db import migrations


def semear(apps, schema_editor):
    from apps.branding.termos_tpmtur import FECHO_EN, INTRO_EN, SECCOES_EN

    Branding = apps.get_model("branding", "BrandingSettings")
    marca, _ = Branding.objects.get_or_create(key="default")
    if marca.terms_sections_en:
        return

    marca.terms_sections_en = SECCOES_EN
    marca.terms_intro_en = INTRO_EN
    marca.terms_closing_en = FECHO_EN
    marca.save(update_fields=[
        "terms_sections_en", "terms_intro_en", "terms_closing_en", "updated_at",
    ])


class Migration(migrations.Migration):

    dependencies = [("branding", "0005_termos_em_ingles_campos")]

    operations = [migrations.RunPython(semear, migrations.RunPython.noop)]
