import 'package:flutter/material.dart';

import '../../core/branding.dart';
import '../../core/theme.dart';

/// Termos e Condicoes do operador, na integra.
///
/// Cada seccao e um titulo e uma lista de paragrafos — texto, nunca marcacao.
/// Os termos sao editaveis no portal, e interpretar HTML vindo dali seria abrir
/// o ecra do passageiro ao que la for escrito.
Future<void> mostrarTermos(BuildContext context, Branding marca) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => _FolhaDeTermos(marca: marca),
  );
}

class _FolhaDeTermos extends StatelessWidget {
  const _FolhaDeTermos({required this.marca});

  final Branding marca;

  @override
  Widget build(BuildContext context) {
    final escuro = Theme.of(context).brightness == Brightness.dark;
    final fundo = escuro ? const Color(0xFF141C2E) : Colors.white;
    final texto = escuro ? Colors.white70 : const Color(0xFF33404F);
    final titulo = escuro ? Colors.white : BuzUpColors.navy;

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (ctx, scrollController) => Container(
        decoration: BoxDecoration(
          color: fundo,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(children: [
          const SizedBox(height: 10),
          Container(
            width: 40, height: 4,
            decoration: BoxDecoration(
              color: escuro ? Colors.white24 : const Color(0xFFD9E2EC),
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 10),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Termos e Condições',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: titulo)),
                  if (marca.companyName.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(marca.companyName,
                          style: const TextStyle(fontSize: 12, color: BuzUpColors.muted)),
                    ),
                ]),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(ctx).pop(),
                tooltip: 'Fechar',
              ),
            ]),
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
              children: [
                if (marca.termsIntro.isNotEmpty) ...[
                  Text(marca.termsIntro,
                      style: TextStyle(fontSize: 14, height: 1.6, color: texto)),
                  const SizedBox(height: 18),
                ],
                for (var i = 0; i < marca.terms.length; i++) ...[
                  Text('${i + 1}. ${marca.terms[i].title}',
                      style: TextStyle(
                          fontSize: 14.5, fontWeight: FontWeight.w800, color: titulo)),
                  const SizedBox(height: 6),
                  for (final item in marca.terms[i].items)
                    Padding(
                      padding: const EdgeInsets.only(left: 4, bottom: 7),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Padding(
                          padding: const EdgeInsets.only(top: 7, right: 8),
                          child: Container(
                            width: 4, height: 4,
                            decoration: BoxDecoration(
                              color: BuzUpColors.blue, borderRadius: BorderRadius.circular(999)),
                          ),
                        ),
                        Expanded(
                          child: Text(item,
                              style: TextStyle(fontSize: 13.5, height: 1.55, color: texto)),
                        ),
                      ]),
                    ),
                  const SizedBox(height: 14),
                ],
                if (marca.termsClosing.isNotEmpty) ...[
                  const Divider(height: 28),
                  Text(marca.termsClosing,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          fontSize: 14, fontWeight: FontWeight.w800, color: titulo)),
                ],
                if (marca.termsVersion.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 14),
                    child: Text('Versão ${marca.termsVersion}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 11, color: BuzUpColors.muted)),
                  ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 12),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: BuzUpColors.blue,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Li e compreendi',
                      style: TextStyle(fontWeight: FontWeight.w900)),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
