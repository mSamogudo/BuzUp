"""Semeia — e mantem alinhados — os papeis de sistema.

Antes so criava. Como corre em cada arranque do backend, dava a impressao de
manter os papeis em dia, mas um papel que ja existisse ficava congelado com as
permissoes do dia em que foi criado. Consequencia pratica: corrigir uma
permissao no codigo nao chegava a nenhum sistema ja instalado, e ninguem dava
por isso — a saida dizia "Role exists" e seguia em frente.

Os papeis de sistema (`is_system=True`) pertencem ao codigo e sao sincronizados.
Os papeis que o cliente criar de raiz nao sao tocados.
"""

from django.core.management.base import BaseCommand

from apps.core.permissions.base import DEFAULT_ROLES
from apps.users.models import Role


class Command(BaseCommand):
    help = "Cria e sincroniza os papeis de sistema."

    def handle(self, *args, **options):
        for code, data in DEFAULT_ROLES.items():
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    "name": data["name"],
                    "permissions": data["permissions"],
                    "is_system": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Papel criado: {role.name}"))
                continue

            if not role.is_system:
                # Alguem transformou este codigo num papel proprio: nao mexer.
                self.stdout.write(f"Papel {role.code} nao e de sistema — deixado como esta")
                continue

            antes = set(role.permissions or [])
            agora = set(data["permissions"])
            mudou = []
            if antes != agora:
                role.permissions = data["permissions"]
                ganhou = sorted(agora - antes)
                perdeu = sorted(antes - agora)
                if ganhou:
                    mudou.append(f"+{', '.join(ganhou)}")
                if perdeu:
                    mudou.append(f"-{', '.join(perdeu)}")
            if role.name != data["name"]:
                mudou.append(f"nome: {role.name} -> {data['name']}")
                role.name = data["name"]

            if mudou:
                role.save(update_fields=["name", "permissions", "updated_at"])
                self.stdout.write(self.style.SUCCESS(
                    f"Papel actualizado: {role.name} ({'; '.join(mudou)})"))
            else:
                self.stdout.write(f"Papel em dia: {role.name}")
