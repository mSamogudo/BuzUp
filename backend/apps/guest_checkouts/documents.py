"""Formatos dos documentos de identificacao aceites na compra de bilhete.

Um so sitio para as regras, porque sao lidas em tres lugares: o portal web (que
formata o campo enquanto se escreve), o servidor (que valida antes de gravar) e
o bilhete em PDF (que imprime o numero). Ter a mesma regra escrita em Python e
em TypeScript garantia que um dia deixavam de concordar — e o passageiro ficava
com o campo a aceitar o que o servidor recusa.

O portal le estas regras de `/api/public/document-types/`.

**Onde e que o documento e pedido.** So em viagens interprovinciais e
internacionais, onde o bilhete e nominal, entra no manifesto de bordo e pode
ser conferido na fronteira. Numa carreira urbana ninguem mostra o BI para
apanhar o autocarro do bairro — pedi-lo seria guardar dados pessoais sem
necessidade, e travar uma compra que tem de ser rapida.
"""

import re

# Cada tipo declara:
#   label       — como aparece ao passageiro
#   pattern     — o que o servidor aceita (sobre o valor JA normalizado)
#   max_length  — limite do campo no formulario
#   placeholder — exemplo com a forma certa
#   help        — a regra por palavras, para quando o valor nao passa
#   digits_only — se o teclado do telemovel deve abrir numerico
#
# Todos os formatos sao fixos e vem do documento real:
#   BI          12 digitos + letra de controlo
#   DIRE        12 digitos
#   Cedula      9 digitos
#   Passaporte  ate 9 alfanumericos (norma ICAO) — e o unico que e um
#               intervalo, porque numa rota internacional viajam passaportes
#               de varios paises e cada um tem o seu comprimento.
# "Outro" fica largo por definicao: e a saida para o documento que nao cabe em
# nenhuma destas caixas, e recusa-lo era impedir alguem de comprar bilhete.
DOCUMENT_RULES: dict[str, dict] = {
    "bi": {
        "label": "Bilhete de Identidade",
        "pattern": r"^\d{12}[A-Z]$",
        "max_length": 13,
        "placeholder": "110100123456A",
        "help": "13 caracteres: 12 digitos seguidos de uma letra.",
        "digits_only": False,
    },
    "passport": {
        "label": "Passaporte",
        "pattern": r"^[A-Z0-9]{6,9}$",
        "max_length": 9,
        "placeholder": "AB1234567",
        "help": "6 a 9 caracteres, so letras e numeros.",
        "digits_only": False,
    },
    "dire": {
        "label": "DIRE",
        "pattern": r"^\d{12}$",
        "max_length": 12,
        "placeholder": "123456789012",
        "help": "12 digitos.",
        "digits_only": True,
    },
    "cedula": {
        "label": "Cedula",
        "pattern": r"^\d{9}$",
        "max_length": 9,
        "placeholder": "123456789",
        "help": "9 digitos.",
        "digits_only": True,
    },
    "other": {
        "label": "Outro",
        "pattern": r"^[A-Z0-9]{4,32}$",
        "max_length": 32,
        "placeholder": "Numero do documento",
        "help": "4 a 32 caracteres, so letras e numeros.",
        "digits_only": False,
    },
}


class DocumentError(ValueError):
    """Numero de documento que nao serve para o tipo indicado."""


def normalize_document(raw: str) -> str:
    """Tira o que e so aspecto e deixa o que identifica.

    As pessoas escrevem o BI com espacos e tracos ("1101 0012 3456 A") e ora em
    maiusculas ora em minusculas. Guardar as duas formas do mesmo documento
    faria o mesmo passageiro parecer dois no manifesto.
    """
    return re.sub(r"[\s.\-/]", "", str(raw or "")).upper()


def validate_document(document_type: str, raw: str) -> str:
    """Devolve o numero normalizado ou levanta `DocumentError`.

    Um tipo desconhecido cai na regra de "Outro" em vez de rebentar: e melhor
    aceitar um documento invulgar do que recusar a compra por causa de uma
    lista desactualizada.
    """
    numero = normalize_document(raw)
    regra = DOCUMENT_RULES.get(document_type) or DOCUMENT_RULES["other"]
    if not numero:
        raise DocumentError(f"Indique o numero do documento ({regra['label']}).")
    if not re.match(regra["pattern"], numero):
        raise DocumentError(f"{regra['label']}: {regra['help']}")
    return numero


# Que documentos servem em cada tipo de carreira.
#
# Numa rota INTERNACIONAL atravessa-se uma fronteira, e a fronteira so aceita
# passaporte. Oferecer BI, DIRE ou cedula na compra e deixar o passageiro
# escolher um documento com que nao vai passar — descobre-o em Ressano Garcia,
# com o autocarro a espera e sem reembolso (ver os termos, seccao da bagagem).
#
# Numa interprovincial viaja-se dentro de Mocambique e qualquer identificacao
# serve. Numa urbana nao se pede documento nenhum.
DOCUMENTOS_POR_SERVICO: dict[str, tuple] = {
    "international": ("passport",),
}


def allowed_document_types(service_type: str | None) -> tuple:
    """Tipos aceites nesta carreira. Sem tipo indicado, todos."""
    if not service_type:
        return tuple(DOCUMENT_RULES.keys())
    return DOCUMENTOS_POR_SERVICO.get(str(service_type), tuple(DOCUMENT_RULES.keys()))


def validate_document_for(service_type: str | None, document_type: str, raw: str) -> str:
    """Valida a FORMA e tambem se o tipo serve nesta carreira."""
    permitidos = allowed_document_types(service_type)
    if document_type and document_type not in permitidos:
        nomes = ", ".join(DOCUMENT_RULES[t]["label"] for t in permitidos)
        raise DocumentError(
            f"Nesta viagem so e aceite: {nomes}. Numa rota internacional a "
            f"fronteira nao aceita outro documento."
        )
    return validate_document(document_type, raw)


def public_rules(service_type: str | None = None) -> list[dict]:
    """As regras como o portal as consome, por ordem de uso em Mocambique."""
    permitidos = allowed_document_types(service_type)
    return [
        {"value": chave, **{k: v for k, v in regra.items()}}
        for chave, regra in DOCUMENT_RULES.items()
        if chave in permitidos
    ]
