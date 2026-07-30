"""Paginação por omissão da API.

Sem paginação, `/api/validations/` devolvia a tabela inteira: com um milhão de
linhas o worker esgotava a memória do contentor e era morto — e com ele ia o
backend de todos os terminais. Um clique no portal chegava para parar a
operação.

O tecto existe para que o cliente possa pedir páginas maiores quando precisa
(o portal mostra listas longas de rotas e paragens) sem que ninguém consiga
pedir "tudo" e repetir o problema.
"""

from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    # 200 cobre com folga as listas de configuração do portal (rotas, paragens,
    # tarifas, viaturas) sem obrigar a paginar o que hoje já funciona.
    page_size = 200
    page_size_query_param = "page_size"
    # Tecto: acima disto a resposta começa a ser um risco de memória.
    max_page_size = 1000
