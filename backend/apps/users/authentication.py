"""Autenticacao JWT que repara na mudanca de senha.

Ver `apps.users.tokens` para o porque. Aqui so se faz a comparacao, no unico
sitio por onde todos os pedidos autenticados passam.
"""

from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from apps.users.tokens import marca_confere


class JWTComMarcaDeSenha(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not marca_confere(validated_token, user):
            # A mesma mensagem que o SimpleJWT da a um token invalido: quem
            # tem o token nao precisa de saber *porque* deixou de servir.
            raise AuthenticationFailed("Token invalido ou expirado.", code="token_not_valid")
        return user
