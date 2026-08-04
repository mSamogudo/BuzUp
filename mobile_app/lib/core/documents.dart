/// Formatos dos documentos de identificacao, tal como o servidor os define.
///
/// As regras vem de `/api/public/document-types/` — o MESMO sitio que o
/// servidor usa para validar. Escreve-las outra vez aqui garantia que um dia
/// deixavam de concordar, e o campo passava a aceitar o que a compra recusa.
///
/// A lista de recurso abaixo so serve enquanto a resposta nao chega (ou se a
/// rede falhar): deixa o formulario utilizavel em vez de o bloquear.
class DocumentRule {
  const DocumentRule({
    required this.value,
    required this.label,
    required this.pattern,
    required this.maxLength,
    required this.placeholder,
    required this.help,
    required this.digitsOnly,
  });

  final String value;
  final String label;
  final String pattern;
  final int maxLength;
  final String placeholder;
  final String help;
  final bool digitsOnly;

  factory DocumentRule.fromJson(Map<String, dynamic> j) => DocumentRule(
        value: (j['value'] ?? 'other').toString(),
        label: (j['label'] ?? '').toString(),
        pattern: (j['pattern'] ?? r'^[A-Z0-9]{4,32}$').toString(),
        maxLength: (j['max_length'] as num?)?.toInt() ?? 32,
        placeholder: (j['placeholder'] ?? '').toString(),
        help: (j['help'] ?? '').toString(),
        digitsOnly: j['digits_only'] == true,
      );

  /// Este numero serve para este tipo de documento?
  bool accepts(String raw) => RegExp(pattern).hasMatch(normalizeDocument(raw));
}

const kDocumentFallback = <DocumentRule>[
  DocumentRule(value: 'bi', label: 'Bilhete de Identidade',
      pattern: r'^[A-Z0-9]{4,32}$', maxLength: 32,
      placeholder: '', help: '', digitsOnly: false),
  DocumentRule(value: 'passport', label: 'Passaporte',
      pattern: r'^[A-Z0-9]{4,32}$', maxLength: 32,
      placeholder: '', help: '', digitsOnly: false),
  DocumentRule(value: 'dire', label: 'DIRE',
      pattern: r'^[A-Z0-9]{4,32}$', maxLength: 32,
      placeholder: '', help: '', digitsOnly: false),
  DocumentRule(value: 'cedula', label: 'Cedula',
      pattern: r'^[A-Z0-9]{4,32}$', maxLength: 32,
      placeholder: '', help: '', digitsOnly: false),
  DocumentRule(value: 'other', label: 'Outro',
      pattern: r'^[A-Z0-9]{4,32}$', maxLength: 32,
      placeholder: '', help: '', digitsOnly: false),
];

/// Tira o que e so aspecto (espacos, tracos) e poe em maiusculas — a mesma
/// normalizacao que o servidor faz antes de gravar. Sem isto o mesmo documento
/// era guardado de duas maneiras e o passageiro aparecia duas vezes no
/// manifesto.
String normalizeDocument(String raw) =>
    raw.replaceAll(RegExp(r'[\s./-]'), '').toUpperCase();

/// A regra deste tipo, ou a de "Outro" quando o tipo e desconhecido.
DocumentRule ruleFor(List<DocumentRule> rules, String type) {
  for (final r in rules) {
    if (r.value == type) return r;
  }
  return rules.isEmpty ? kDocumentFallback.last : rules.last;
}
