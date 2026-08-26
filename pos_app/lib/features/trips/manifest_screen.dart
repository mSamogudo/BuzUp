import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme.dart';

/// Cinzento de apoio. O tema do POS nao define um `muted`; este e o
/// mesmo tom ja usado nos restantes ecrans do terminal.
const _muted = Color(0xFF6B7A8F);

/// Manifesto de bordo, ao vivo.
///
/// O motorista precisa de responder a duas perguntas sem contar cabeças:
/// *quantos vão a bordo* e *quem falta embarcar*. Por isso os números estão
/// no topo e a lista está agrupada por estado, com quem falta primeiro — é
/// nesses que ele tem de reparar antes de fechar as portas.
///
/// Actualiza-se sozinho de 15 em 15 segundos enquanto a viagem decorre: os
/// passageiros vão sendo validados nas paragens e a lista cresce sem ninguém
/// carregar em nada.
class ManifestScreen extends ConsumerStatefulWidget {
  const ManifestScreen({super.key, required this.tripId, required this.title});

  final int tripId;
  final String title;

  static Future<void> open(BuildContext context, {required int tripId, required String title}) {
    return Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ManifestScreen(tripId: tripId, title: title),
    ));
  }

  @override
  ConsumerState<ManifestScreen> createState() => _ManifestScreenState();
}

class _ManifestScreenState extends ConsumerState<ManifestScreen> {
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    // A lista cresce ao longo do percurso; sem isto o motorista teria de
    // sair e voltar a entrar para ver quem embarcou na ultima paragem.
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    try {
      final d = await ref.read(agentApiProvider).driverTripManifest(widget.tripId);
      if (!mounted) return;
      setState(() {
        _data = d;
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Nao foi possivel carregar o manifesto.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final totals = (_data?['totals'] as Map?)?.cast<String, dynamic>() ?? const {};
    final entries = ((_data?['entries'] as List?) ?? const [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    final formal = _data?['formal'] == true;

    // Quem falta primeiro: e a informacao accionavel antes de partir.
    final ordem = {'expected': 0, 'no_show': 1, 'aboard': 2};
    entries.sort((a, b) =>
        (ordem[a['boarding']] ?? 3).compareTo(ordem[b['boarding']] ?? 3));

    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          const Text('Manifesto de bordo',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          Text(widget.title,
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11.5, color: Colors.white70)),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _load(),
            tooltip: 'Actualizar',
          ),
        ],
      ),
      body: _loading && _data == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _data == null
              ? Center(child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    // Rola sempre, para o gesto pegar num manifesto vazio.
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
                    children: [
                      _resumo(totals),
                      if (!formal) ...[
                        const SizedBox(height: 10),
                        _aviso(),
                      ],
                      const SizedBox(height: 12),
                      if (entries.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 40),
                          child: Center(
                            child: Text('Ainda nao ha passageiros nesta viagem.',
                                style: TextStyle(color: _muted)),
                          ),
                        )
                      else
                        ...entries.map(_linha),
                    ],
                  ),
                ),
    );
  }

  Widget _resumo(Map<String, dynamic> t) {
    Widget caixa(String label, String valor, Color cor) => Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
            decoration: BoxDecoration(
              color: cor.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: cor.withValues(alpha: 0.28)),
            ),
            child: Column(children: [
              Text(valor, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: cor)),
              Text(label,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700,
                      color: _muted)),
            ]),
          ),
        );

    final capacidade = t['capacity'];
    return Column(children: [
      Row(children: [
        caixa('A BORDO', '${t['aboard'] ?? 0}', BuzUpColors.success),
        const SizedBox(width: 8),
        caixa('POR EMBARCAR', '${t['expected'] ?? 0}', const Color(0xFFB58900)),
        const SizedBox(width: 8),
        caixa('FALTAS', '${t['no_show'] ?? 0}', BuzUpColors.danger),
      ]),
      if (capacidade != null && capacidade != 0) ...[
        const SizedBox(height: 8),
        Row(children: [
          const Icon(Icons.event_seat, size: 15, color: _muted),
          const SizedBox(width: 6),
          Text('${t['aboard'] ?? 0} de $capacidade lugares',
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
          const Spacer(),
          Text('${t['fare_total'] ?? '0.00'} MZN',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900,
                  color: BuzUpColors.navy)),
        ]),
      ],
    ]);
  }

  Widget _aviso() {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF4FA),
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Row(children: [
        Icon(Icons.info_outline, size: 16, color: _muted),
        SizedBox(width: 8),
        Expanded(
          child: Text(
            'Carreira urbana: registo de bordo, sem dados nominais. O manifesto '
            'formal existe nas rotas interprovinciais e internacionais.',
            style: TextStyle(fontSize: 11.5, color: _muted, height: 1.3),
          ),
        ),
      ]),
    );
  }

  Widget _linha(Map<String, dynamic> e) {
    final estado = (e['boarding'] ?? '').toString();
    final (cor, etiqueta) = switch (estado) {
      'aboard' => (BuzUpColors.success, 'A bordo'),
      'no_show' => (BuzUpColors.danger, 'Faltou'),
      _ => (const Color(0xFFB58900), 'Aguarda'),
    };
    final lugar = (e['seat'] ?? '').toString();
    final nome = (e['passenger_name'] ?? '').toString();
    final emergencia = '${e['emergency_name'] ?? ''} ${e['emergency_phone'] ?? ''}'.trim();

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 42,
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              color: cor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(lugar.isEmpty ? '—' : lugar,
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: cor)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(nome.isEmpty ? 'Passageiro avulso' : nome,
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text(
                [
                  if ((e['phone'] ?? '').toString().isNotEmpty) e['phone'],
                  e['payment_label'],
                  '${e['fare_amount']} MZN',
                ].where((x) => (x ?? '').toString().isNotEmpty).join(' · '),
                style: const TextStyle(fontSize: 11.5, color: _muted),
              ),
              if (emergencia.isNotEmpty) ...[
                const SizedBox(height: 3),
                Row(children: [
                  const Icon(Icons.emergency_share_outlined, size: 12,
                      color: Color(0xFFB07B24)),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(emergencia,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11, color: Color(0xFFB07B24),
                            fontWeight: FontWeight.w600)),
                  ),
                ]),
              ],
            ]),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: cor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(etiqueta,
                style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: cor)),
          ),
        ]),
      ),
    );
  }
}
