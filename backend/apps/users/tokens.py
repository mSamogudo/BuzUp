"""Tokens que morrem quando a senha muda.

Por um refresh token na lista negra nao chega — e nem sequer o faziamos. O
token de *acesso* e auto-suficiente: nao consulta a base, nao consulta nada, e
vale ate expirar, 30 minutos depois de emitido (`ACCESS_TOKEN_LIFETIME`).

Consequencia, antes disto: um administrador que repunha a senha de uma conta
comprometida **nao expulsava ninguem**. O intruso continuava a vender no POS
durante meia hora, com a senha ja trocada e o SMS da senha temporaria ja
enviado. O mesmo valia para quem mudava a sua propria senha por desconfiar de
uma sessao.

A solucao e a que o Django usa na sua propria autenticacao por sessao:
`get_session_auth_hash()`, um HMAC do campo da senha. Vai dentro do token como
uma marca; a autenticacao compara-a com a do utilizador em cada pedido. Mudar
a senha muda o HMAC, e todos os tokens emitidos antes deixam de servir no
pedido seguinte.

Tambem fecha a renovacao: o `TokenRefreshView` copia as claims do refresh para
o acesso novo, por isso o token que sai de um refresh velho nasce com a marca
velha e e recusado na mesma.

Nao guarda a senha nem nada que se aproxime dela: e um HMAC com a
`SECRET_KEY`, truncado, e serve so para comparar consigo proprio.
"""

from __future__ import annotations

from rest_framework_simplejwt.tokens import RefreshToken

MARCA = "pwh"
TAMANHO = 16


def marca_da_senha(user) -> str:
    """A marca actual do utilizador. Vazia se o modelo nao souber calcula-la."""
    obter = getattr(user, "get_session_auth_hash", None)
    if obter is None:
        return ""
    return str(obter())[:TAMANHO]


def marcar(token, user):
    """Carimba um token com a marca da senha de quem o recebe."""
    marca = marca_da_senha(user)
    if marca:
        token[MARCA] = marca
    return token


def token_para(user) -> RefreshToken:
    """Um par novo, ja carimbado. Usar sempre em vez de `RefreshToken.for_user`.

    Um sitio que emita token sem passar por aqui deixa o buraco aberto por
    inteiro para quem entra por essa porta.
    """
    return marcar(RefreshToken.for_user(user), user)


def marca_confere(token_payload, user) -> bool:
    """Um token sem marca passa.

    E deliberado: os tokens que ja andam por ai — e ha terminais POS em campo
    com sessao aberta — nao a trazem, e recusa-los deitava toda a gente fora no
    momento do deploy, a meio de vendas. Expiram sozinhos em 30 minutos, e a
    partir dai todos vem marcados.
    """
    trazida = token_payload.get(MARCA)
    if not trazida:
        return True
    return str(trazida) == marca_da_senha(user)
