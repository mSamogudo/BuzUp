"""O sentido em que a partida percorre a rota.

A rota ja tinha dois sentidos nas paragens; a viagem nao tinha nenhum. Sem ele,
pesquisar Maputo->Nelspruit devolvia tambem as partidas Nelspruit->Maputo.

O campo nasce VAZIO em tudo o que ja existe, e de proposito: nao ha na base de
dados nada que diga para onde ia uma partida criada antes deste campo. Um
`default` seria uma invencao, e a invencao punha passageiros no autocarro
errado. Vazio significa "nao declarado" e continua a aparecer nos dois sentidos
— o comportamento de hoje — ate o operador o declarar.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0011_triprevenueclosure_manifest_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="direction",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=8,
                choices=[("outbound", "Ida"), ("inbound", "Volta")],
            ),
        ),
        migrations.AddField(
            model_name="routeschedule",
            name="direction",
            field=models.CharField(
                blank=True, default="", max_length=8,
                choices=[("outbound", "Ida"), ("inbound", "Volta")],
            ),
        ),
    ]
