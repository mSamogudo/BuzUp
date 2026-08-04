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
# NOTA sobre o rigor de cada um: o BI mocambicano tem forma fixa (12 digitos e
# uma letra de controlo) e o passaporte segue a norma ICAO (ate 9 caracteres
# alfanumericos), por isso esses sao validados com rigor. Para o DIRE e a
# cedula nao ha uma forma unica publicada que se possa impor sem risco de
# recusar documentos legitimos, por isso ficam com limites largos: mais vale
# aceitar um numero estranho do que impedir alguem de comprar bilhete.
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
        "pattern": r"^[A-Z0-9]{6,20}$",
        "max_length": 20,
        "placeholder": "Numero do DIRE",
        "help": "6 a 20 caracteres, so letras e numeros.",
        "digits_only": False,
    },
    "cedula": {
        "label": "Cedula",
        "pattern": r"^[A-Z0-9]{4,20}$",
        "max_length": 20,
        "placeholder": "Numero da cedula",
        "help": "4 a 20 caracteres, so letras e numeros.",
        "digits_only": False,
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


def public_rules() -> list[dict]:
    """As regras como o portal as consome, por ordem de uso em Mocambique."""
    return [
        {"value": chave, **{k: v for k, v in regra.items()}}
        for chave, regra in DOCUMENT_RULES.items()
    ]
