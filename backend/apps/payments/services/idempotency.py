"""Criação de PaymentIntent à prova de pedidos simultâneos.

O padrão que estava espalhado pelas views — ler pela `idempotency_key`, e se
não existir criar — tem uma janela entre a leitura e a escrita. Com a rede
instável que estas apps enfrentam, o cliente repete o pedido e as duas
tentativas passam a leitura ao mesmo tempo: a segunda rebenta na unique
constraint e o utilizador vê 500 numa recarga que na verdade está em curso.
Quem vê 500 tenta outra vez com chave nova — e aí sim paga duas vezes.

`get_or_create_payment_intent` fecha essa janela: deixa a base de dados
decidir quem ganha e devolve a intenção existente ao perdedor.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.payments.models import PaymentIntent


def get_or_create_payment_intent(*, idempotency_key: str, **fields) -> tuple[PaymentIntent, bool]:
    """(intenção, criada_agora). `created=False` significa pedido repetido.

    Quem receber `created=False` NÃO deve contactar o gateway outra vez — o
    primeiro pedido já o fez.
    """
    existing = PaymentIntent.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing, False

    try:
        # savepoint próprio: sem isto, a IntegrityError aborta a transacção
        # exterior e o `filter` seguinte falharia com "current transaction is
        # aborted" em vez de devolver a intenção do vencedor.
        with transaction.atomic():
            return PaymentIntent.objects.create(
                idempotency_key=idempotency_key, **fields,
            ), True
    except IntegrityError:
        winner = PaymentIntent.objects.filter(idempotency_key=idempotency_key).first()
        if winner:
            return winner, False
        raise


def agent_scoped_key(user_id, raw_key: str, *, prefix: str = "agent-idem") -> str:
    """Prefixa a chave do cliente com quem a enviou.

    A chave vem do POS e o POS não sabe o que os outros POS estão a enviar. Sem
    o prefixo, dois operadores que por acaso repitam a mesma chave — um cliente
    com contador em vez de aleatório, um device restaurado a partir de uma cópia
    — passavam a partilhar a mesma operação: o segundo recebia a venda do
    primeiro em vez da sua. Com o prefixo, a chave só colide com ela própria.
    """
    return f"{prefix}-{user_id}-{raw_key}"
