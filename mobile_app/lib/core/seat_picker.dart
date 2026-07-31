import 'package:flutter/material.dart';

import "theme.dart";

/// Planta de lugares do autocarro, com a disposição real dos bancos.
///
/// O corredor não está numa posição fixa: há autocarros 2+2, 1+2 (banco
/// individual de um lado, comum nos interprovinciais) e 3+2. Quem sabe a
/// disposição é o servidor — manda cada fila já dividida em `left` e `right`,
/// e aqui só se põe o corredor entre as duas. Desenhar sempre 2+2 mostraria
/// lugares que não existem no autocarro, e o agente atribuiria um assento que
/// o passageiro não vai encontrar.
class SeatPicker extends StatelessWidget {
  const SeatPicker({
    super.key,
    required this.seatMap,
    required this.picked,
    required this.maxPick,
    required this.onToggle,
  });

  /// Payload de `seat_map` do backend.
  final Map<String, dynamic> seatMap;
  final List<String> picked;
  final int maxPick;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    final rows = (seatMap['rows'] as List?) ?? const [];
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: scheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Expanded(
            child: Text('FRENTE DO AUTOCARRO',
                style: TextStyle(fontSize: 10.5, letterSpacing: 1.2,
                    fontWeight: FontWeight.w800, color: Color(0xFF6B7A8F))),
          ),
          Text('${picked.length}/$maxPick',
              style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
        ]),
        const Divider(height: 14),
        // A planta rola dentro da sua própria caixa: o ecrã do terminal é
        // pequeno e o botão de continuar tem de continuar visível.
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 260),
          child: SingleChildScrollView(
            child: Column(
              children: [
                for (final row in rows) _SeatRow(
                  row: row as Map,
                  picked: picked,
                  maxPick: maxPick,
                  onToggle: onToggle,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
          _LegendDot(color: Colors.white, label: 'Livre', bordered: true),
          SizedBox(width: 14),
          _LegendDot(color: BuzUpColors.blue, label: 'Escolhido'),
          SizedBox(width: 14),
          _LegendDot(color: Color(0xFFE7ECF2), label: 'Ocupado'),
        ]),
      ]),
    );
  }
}

class _SeatRow extends StatelessWidget {
  const _SeatRow({
    required this.row,
    required this.picked,
    required this.maxPick,
    required this.onToggle,
  });

  final Map row;
  final List<String> picked;
  final int maxPick;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    final left = (row['left'] as List?) ?? const [];
    final right = (row['right'] as List?) ?? const [];
    final fullWidth = row['full_width'] == true;

    Widget seat(dynamic s) => Expanded(
          child: _SeatButton(
            label: (s as Map)['label']?.toString() ?? '',
            occupied: s['occupied'] == true,
            picked: picked,
            maxPick: maxPick,
            onToggle: onToggle,
          ),
        );

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(children: [
        for (final s in left) seat(s),
        if (!fullWidth)
          // O corredor: um espaço estreito com o número da fila, para o agente
          // e o passageiro se orientarem.
          SizedBox(
            width: 22,
            child: Text('${row['row']}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 10, color: Color(0xFFB7C4D3))),
          ),
        for (final s in right) seat(s),
      ]),
    );
  }
}

class _SeatButton extends StatelessWidget {
  const _SeatButton({
    required this.label,
    required this.occupied,
    required this.picked,
    required this.maxPick,
    required this.onToggle,
  });

  final String label;
  final bool occupied;
  final List<String> picked;
  final int maxPick;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    final isPicked = picked.contains(label);
    // Bloqueia lugares novos quando já se escolheram todos os necessários —
    // evita atribuir 3 lugares a 2 passageiros.
    final full = !isPicked && picked.length >= maxPick;
    final disabled = occupied || full;

    final bg = occupied
        ? const Color(0xFFE7ECF2)
        : isPicked
            ? BuzUpColors.blue
            : Colors.white;
    final fg = occupied
        ? const Color(0xFFA9B7C6)
        : isPicked
            ? Colors.white
            : const Color(0xFF0F1B2D);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 3),
      child: AspectRatio(
        aspectRatio: 1,
        child: Material(
          color: bg,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: disabled ? null : () => onToggle(label),
            child: Container(
              alignment: Alignment.center,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isPicked ? BuzUpColors.blue : const Color(0xFFE4EBF3),
                  width: 1.5,
                ),
              ),
              child: Text(label,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: fg)),
            ),
          ),
        ),
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label, this.bordered = false});

  final Color color;
  final String label;
  final bool bordered;

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(
        width: 12, height: 12,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(4),
          border: bordered ? Border.all(color: const Color(0xFFE4EBF3), width: 1.5) : null,
        ),
      ),
      const SizedBox(width: 5),
      Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7A8F))),
    ]);
  }
}
