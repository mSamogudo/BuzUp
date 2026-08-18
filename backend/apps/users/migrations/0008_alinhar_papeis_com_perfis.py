"""Poe a base de dados de acordo com o que o portal sempre aparentou.

Duas heranças de defeitos corrigidos no codigo, que so o codigo novo nao
desfaz nos sistemas ja instalados:

1. Vinculos de papel marcados como apagados. Retirar um papel a alguem nao lhe
   retirava as permissoes — a relacao many-to-many junta a tabela intermedia
   directamente e continuava a contar. Estas linhas nao guardam historico
   nenhum: apagam-se mesmo, senao a proxima gravacao do utilizador tropeca
   nelas.

2. Utilizadores marcados como Motorista (ou Agente) sem o registo operacional
   correspondente. E por isso que o cliente marcou duas pessoas como motoristas
   e nao as encontrou no selector da viagem.
"""

from django.db import migrations


PAPEIS_DE_MOTORISTA = {"driver"}
PAPEIS_DE_AGENTE = {"agent", "pos_agent"}


def alinhar(apps, schema_editor):
    UserRole = apps.get_model("users", "UserRole")
    User = apps.get_model("users", "User")
    Driver = apps.get_model("trips", "Driver")
    Agent = apps.get_model("trips", "Agent")

    UserRole.objects.filter(deleted_at__isnull=False).delete()

    # Duplicados vivos do mesmo par: sobra o mais antigo, que e o que a
    # atribuicao original criou.
    vistos = set()
    for vinculo in UserRole.objects.filter(deleted_at__isnull=True).order_by("id"):
        chave = (vinculo.user_id, vinculo.role_id)
        if chave in vistos:
            vinculo.delete()
        else:
            vistos.add(chave)

    for user in User.objects.all():
        codigos = {
            v.role.code
            for v in UserRole.objects.filter(user=user, deleted_at__isnull=True).select_related("role")
        }
        nome = f"{user.first_name} {user.last_name}".strip() or user.username
        telefone = (user.phone or "").strip()
        if codigos & PAPEIS_DE_MOTORISTA:
            _garantir(Driver, user, nome, telefone)
        if codigos & PAPEIS_DE_AGENTE:
            _garantir(Agent, user, nome, telefone)


def _garantir(modelo, user, nome, telefone):
    if modelo.objects.filter(user=user).exists():
        return
    modelo.objects.create(user=user, full_name=nome, phone=telefone, status="active")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_is_2fa_enabled_portalloginchallenge"),
        ("trips", "0011_triprevenueclosure_manifest_and_more"),
    ]

    operations = [
        # Sem inverso: nao ha maneira honesta de adivinhar que vinculos apagados
        # existiam antes, nem faria sentido voltar a esconder motoristas.
        migrations.RunPython(alinhar, migrations.RunPython.noop),
    ]
