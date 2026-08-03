import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'theme.dart';

/// Ecrã de escolha de lugares a ecrã inteiro — um passo próprio do fluxo.
///
/// Antes a planta vivia embutida no formulário e obrigava a rolar; aqui o
/// autocarro é desenhado de uma vez: o tamanho de cada banco é calculado para
/// a planta caber no ecrã (só rola em autocarros invulgarmente longos). O
/// corredor não é fixo — o servidor manda cada fila dividida em `left`/`right`
/// conforme a disposição real (1+2, 2+2, 3+2...).
///
/// Devolve a lista de lugares escolhidos via `Navigator.pop`.
class SeatMapScreen extends StatefulWidget {
  const SeatMapScreen({
    super.key,
    required this.seatMap,
    required this.maxPick,
    this.initialPicked = const [],
    this.title = 'Escolha de lugares',
    this.subtitle = '',
  });

  final Map<String, dynamic> seatMap;
  final int maxPick;
  final List<String> initialPicked;
  final String title;
  final String subtitle;

  /// Abre o ecrã e devolve os lugares escolhidos (null = cancelado).
  static Future<List<String>?> pick(
    BuildContext context, {
    required Map<String, dynamic> seatMap,
    required int maxPick,
    List<String> initialPicked = const [],
    String title = 'Escolha de lugares',
    String subtitle = '',
  }) {
    return Navigator.of(context).push<List<String>>(
      MaterialPageRoute(
        builder: (_) => SeatMapScreen(
          seatMap: seatMap,
          maxPick: maxPick,
          initialPicked: initialPicked,
          title: title,
          subtitle: subtitle,
        ),
      ),
    );
  }

  @override
  State<SeatMapScreen> createState() => _SeatMapScreenState();
}

class _SeatMapScreenState extends State<SeatMapScreen> {
  late final List<String> _picked = List.of(widget.initialPicked);

  List get _rows => (widget.seatMap['rows'] as List?) ?? const [];

  void _toggle(String label) {
    setState(() {
      if (_picked.contains(label)) {
        _picked.remove(label);
        HapticFeedback.selectionClick();
      } else if (_picked.length < widget.maxPick) {
        _picked.add(label);
        HapticFeedback.selectionClick();
      } else if (widget.maxPick == 1) {
        // Com um só lugar a escolher, tocar noutro troca em vez de exigir
        // desmarcar primeiro.
        _picked
          ..clear()
          ..add(label);
        HapticFeedback.selectionClick();
      }
    });
  }

  bool get _complete => _picked.length == widget.maxPick;

  @override
  Widget build(BuildContext context) {
    final missing = widget.maxPick - _picked.length;
    return Scaffold(
      backgroundColor: const Color(0xFFF2F5FA),
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(widget.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          if (widget.subtitle.isNotEmpty)
            Text(widget.subtitle,
                style: const TextStyle(fontSize: 11.5, color: Colors.white70, fontWeight: FontWeight.w600)),
        ]),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [BuzUpColors.navy, BuzUpColors.navyDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
        foregroundColor: Colors.white,
        actions: [
          Center(
            child: Container(
              margin: const EdgeInsets.only(right: 14),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text('${_picked.length}/${widget.maxPick}',
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w900, color: Colors.white)),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          Expanded(child: Center(child: _bus(context))),
          const SizedBox(height: 4),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
            _LegendDot(kind: _SeatKind.free, label: 'Livre'),
            SizedBox(width: 16),
            _LegendDot(kind: _SeatKind.picked, label: 'Escolhido'),
            SizedBox(width: 16),
            _LegendDot(kind: _SeatKind.occupied, label: 'Ocupado'),
          ]),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            child: Row(children: [
              if (_picked.isNotEmpty)
                Expanded(
                  child: Text(
                    _picked.join('  ·  '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900, color: BuzUpColors.navy),
                  ),
                )
              else
                const Expanded(
                  child: Text('Toque num lugar livre para o escolher.',
                      style: TextStyle(fontSize: 12, color: Color(0xFF6B7A8F))),
                ),
              const SizedBox(width: 12),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: BuzUpColors.blue,
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: _complete ? () => Navigator.pop(context, List<String>.of(_picked)) : null,
                child: Text(
                  _complete
                      ? 'CONFIRMAR'
                      : 'FALTA${missing == 1 ? '' : 'M'} $missing',
                  style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.6),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _bus(BuildContext context) {
    final rows = _rows;
    if (rows.isEmpty) {
      return const Text('Sem planta de lugares para esta viagem.',
          style: TextStyle(color: Color(0xFF6B7A8F)));
    }

    // Quantos bancos tem a fila mais larga (para dimensionar as células).
    var maxAcross = 1;
    for (final r in rows) {
      final m = r as Map;
      final across = ((m['left'] as List?)?.length ?? 0) +
          ((m['right'] as List?)?.length ?? 0);
      if (across > maxAcross) maxAcross = across;
    }

    return LayoutBuilder(builder: (context, box) {
      const aisle = 26.0;
      const chrome = 96.0; // frente do autocarro + margens internas
      final maxW = math.min(box.maxWidth - 32, 360.0);
      final byWidth = (maxW - aisle - 24 - maxAcross * 6) / maxAcross;
      final byHeight = (box.maxHeight - chrome - rows.length * 6) / rows.length;
      final cell = math.max(30.0, math.min(46.0, math.min(byWidth, byHeight)));
      final busW = maxAcross * (cell + 6) + aisle + 24;
      final fits = byHeight >= 30.0;

      final plan = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: _seatRow(row as Map, cell),
            ),
        ],
      );

      return Container(
        width: busW,
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Colors.white, Color(0xFFF6F9FD)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
          // Frente arredondada: o desenho lê-se como um autocarro visto de
          // cima, não como uma grelha qualquer.
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(46),
            bottom: Radius.circular(18),
          ),
          border: Border.all(color: const Color(0xFFD8E2EE), width: 1.5),
          boxShadow: [
            BoxShadow(
              color: BuzUpColors.navy.withValues(alpha: 0.10),
              blurRadius: 22,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 8, 6, 6),
            child: Row(children: [
              const Expanded(
                child: Text('FRENTE',
                    style: TextStyle(
                        fontSize: 10, letterSpacing: 2.4,
                        fontWeight: FontWeight.w800, color: Color(0xFF9AA9BC))),
              ),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF4FA),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFD8E2EE)),
                ),
                child: const Icon(Icons.directions_bus_filled,
                    size: 14, color: Color(0xFF6B7A8F)),
              ),
            ]),
          ),
          const Divider(height: 12, color: Color(0xFFE3EAF3)),
          if (fits)
            plan
          else
            Flexible(child: SingleChildScrollView(child: plan)),
        ]),
      );
    });
  }

  Widget _seatRow(Map row, double cell) {
    final left = (row['left'] as List?) ?? const [];
    final right = (row['right'] as List?) ?? const [];
    final fullWidth = row['full_width'] == true;

    Widget seat(dynamic s) {
      final m = s as Map;
      final label = m['label']?.toString() ?? '';
      final occupied = m['occupied'] == true;
      final picked = _picked.contains(label);
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 3),
        child: _Seat(
          label: label,
          size: cell,
          kind: occupied
              ? _SeatKind.occupied
              : picked
                  ? _SeatKind.picked
                  : _SeatKind.free,
          onTap: occupied ? null : () => _toggle(label),
        ),
      );
    }

    return Row(mainAxisSize: MainAxisSize.min, children: [
      for (final s in left) seat(s),
      if (!fullWidth)
        SizedBox(
          width: 26,
          child: Text('${row['row']}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 10, color: Color(0xFFB7C4D3), fontWeight: FontWeight.w700)),
        ),
      for (final s in right) seat(s),
    ]);
  }
}

enum _SeatKind { free, picked, occupied }

/// Um banco visto de cima: encosto (barra) + assento, com estados animados.
class _Seat extends StatelessWidget {
  const _Seat({
    required this.label,
    required this.size,
    required this.kind,
    this.onTap,
  });

  final String label;
  final double size;
  final _SeatKind kind;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final picked = kind == _SeatKind.picked;
    final occupied = kind == _SeatKind.occupied;

    final backrest = occupied
        ? const Color(0xFFD4DCE6)
        : picked
            ? BuzUpColors.blueDark
            : const Color(0xFFC9D7E7);
    final fg = occupied
        ? const Color(0xFFA9B7C6)
        : picked
            ? Colors.white
            : const Color(0xFF13294B);

    return GestureDetector(
      onTap: onTap,
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // Encosto do banco.
        AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          width: size * 0.78,
          height: math.max(3.0, size * 0.12),
          decoration: BoxDecoration(
            color: backrest,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          ),
        ),
        const SizedBox(height: 1.5),
        AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          width: size,
          height: size * 0.82,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            gradient: picked
                ? const LinearGradient(
                    colors: [BuzUpColors.blue, BuzUpColors.blueDeep],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  )
                : null,
            color: picked
                ? null
                : occupied
                    ? const Color(0xFFEDF1F6)
                    : Colors.white,
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: picked
                  ? BuzUpColors.blueDeep
                  : occupied
                      ? const Color(0xFFE0E7EF)
                      : const Color(0xFFD5E0EC),
              width: 1.4,
            ),
            boxShadow: picked
                ? [
                    BoxShadow(
                      color: BuzUpColors.blue.withValues(alpha: 0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: occupied
              ? Icon(Icons.close, size: math.max(11.0, size * 0.32), color: fg)
              : Text(label,
                  style: TextStyle(
                      fontSize: math.max(9.5, size * 0.26),
                      fontWeight: FontWeight.w800,
                      color: fg)),
        ),
      ]),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.kind, required this.label});

  final _SeatKind kind;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      IgnorePointer(child: _Seat(label: '', size: 16, kind: kind)),
      const SizedBox(width: 6),
      Text(label, style: const TextStyle(fontSize: 11.5, color: Color(0xFF6B7A8F))),
    ]);
  }
}
