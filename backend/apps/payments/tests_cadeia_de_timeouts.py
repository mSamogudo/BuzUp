"""A cadeia de timeouts, travada por um teste.

Isto nao testa codigo: testa um acordo entre quatro sitios que nao se
compilam juntos — as definicoes do Django, o nginx, o gunicorn e uma
aplicacao Flutter noutro repositorio. Um acordo desses nao se mantem por
boa vontade. Mantem-se porque alguem o quebra e um teste fica vermelho.

A regra e uma so: **quem espera pela resposta tem de desistir DEPOIS de quem
a produz.**

Ja falhou nos dois sentidos. A 2026-09-12, as 06:32, a cobranca do e-Mola
podia demorar 60s e o POS desistia aos 25: a operadora respondeu aos 30,6s,
o servidor confirmou o pagamento e emitiu o bilhete, e o agente ficou a olhar
para um erro enquanto o passageiro era debitado.
"""

from __future__ import annotations

from django.conf import settings
from django.test import SimpleTestCase

#: Quanto o POS espera pela resposta da venda.
#: Fonte: `pos_app/lib/core/config.dart`, `AppConfig.saleTimeout`.
#: Mudar la obriga a mudar aqui — e e esse o ponto.
POS_ESPERA_PELA_VENDA_S = 80

#: Durante quanto tempo o POS continua a perguntar pelo estado do pagamento.
#: Fonte: `pos_app/lib/core/config.dart`, `AppConfig.paymentPollTimeout`.
POS_SONDA_DURANTE_S = 180

#: `proxy_read_timeout` do nginx, em `docker/prod/nginx.conf` e no snippet do
#: edge. O nginx corta a ligacao antes de o POS desistir, se for mais curto.
NGINX_PROXY_READ_S = 75

#: Margem para o que nao e a operadora: rede, Django, base de dados, nginx.
#: Sete segundos e muito mais do que se mediu, e e de proposito: uma margem
#: apertada volta a partir-se na primeira tarde em que a rede estiver lenta.
MARGEM_S = 7


class CadeiaDeTimeoutsTests(SimpleTestCase):
    def cobrancas(self) -> dict[str, int]:
        return {
            "MPESA": int(settings.PAYMENT_WALLET_CHARGE_TIMEOUT_MPESA),
            "EMOLA": int(settings.PAYMENT_WALLET_CHARGE_TIMEOUT_EMOLA),
        }

    def test_the_app_always_outwaits_the_charge(self):
        """Se a cobranca puder demorar mais do que o POS espera, ha um
        intervalo em que o servidor confirma e cobra enquanto o agente ve um
        erro. Foi exactamente o que aconteceu a 2026-09-12."""
        tecto = POS_ESPERA_PELA_VENDA_S - MARGEM_S
        for provider, segundos in self.cobrancas().items():
            with self.subTest(provider=provider):
                self.assertLess(
                    segundos, tecto,
                    f"{provider} espera {segundos}s pela operadora, mas o POS desiste aos "
                    f"{POS_ESPERA_PELA_VENDA_S}s. Baixar aqui ou subir o `saleTimeout` em "
                    f"pos_app/lib/core/config.dart — os dois numeros andam juntos.",
                )

    def test_nginx_outwaits_the_charge_too(self):
        """O nginx esta no meio. Se cortar primeiro, o POS recebe 504 e a
        resposta da operadora perde-se — que foi a avaria anterior a esta."""
        tecto = NGINX_PROXY_READ_S - MARGEM_S
        for provider, segundos in self.cobrancas().items():
            with self.subTest(provider=provider):
                self.assertLess(
                    segundos, tecto,
                    f"{provider} espera {segundos}s, mas o nginx corta aos {NGINX_PROXY_READ_S}s "
                    "(docker/prod/nginx.conf).",
                )

    def test_the_app_outwaits_nginx(self):
        """O POS e o ultimo a desistir. Assim um 504 do nginx chega-lhe como
        resposta — que se pode ler e explicar — e nao como silencio."""
        self.assertGreater(POS_ESPERA_PELA_VENDA_S, NGINX_PROXY_READ_S)

    def test_the_status_query_never_holds_the_line(self):
        """A consulta de estado e um GET que nao espera por ninguem: corre
        dentro da sondagem do POS, de 3 em 3 segundos. Se demorar mais do que
        esse intervalo, as sondagens empilham-se."""
        self.assertLessEqual(int(settings.PAYMENT_WALLET_QUERY_TIMEOUT_SECONDS), 15)

    def test_the_deadline_shown_matches_how_long_the_app_keeps_asking(self):
        """`PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS` nao e um timeout de
        servidor: e o prazo que o passageiro **ve** para confirmar na
        carteira. Tem de ser o mesmo tempo durante o qual o POS continua a
        perguntar (`AppConfig.paymentPollTimeout`).

        Se o prazo mostrado for maior, a aplicacao desiste enquanto o
        passageiro ainda acredita que tem tempo — e o bilhete que ele paga a
        seguir nao aparece no ecra do agente. Se for menor, diz-se que acabou
        o tempo a alguem que ainda o tem.
        """
        self.assertEqual(
            int(settings.PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS),
            POS_SONDA_DURANTE_S,
            "o prazo mostrado ao passageiro e a janela de sondagem do POS tem "
            "de ser o mesmo numero. Ver `AppConfig.paymentPollTimeout`.",
        )
