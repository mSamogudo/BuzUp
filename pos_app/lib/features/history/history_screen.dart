import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _items = const [];
  String _filter = 'all'; // all | sale | topup

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await ref.read(agentApiProvider).salesHistory();
      final list = ((res['results'] as List?) ?? const [])
          .cast<Map<String, dynamic>>();
      setState(() => _items = list);
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'confirmed':
        return BuzUpColors.success;
      case 'pending':
        return Colors.orange;
      case 'failed':
      case 'cancelled':
        return BuzUpColors.danger;
      default:
        return Colors.grey;
    }
  }

  IconData _kindIcon(String kind) =>
      kind == 'topup' ? Icons.account_balance_wallet : Icons.confirmation_number;

  Color _kindAccent(String kind) =>
      kind == 'topup' ? const Color(0xFF0B6FE0) : const Color(0xFF1FB04A);

  List<Map<String, dynamic>> get _filtered {
    if (_filter == 'all') return _items;
    return _items.where((it) => (it['kind'] as String?) == _filter).toList();
  }

  int get _salesCount => _items.where((it) => it['kind'] == 'sale').length;
  int get _topupsCount => _items.where((it) => it['kind'] == 'topup').length;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    final muted = isDark ? Colors.white60 : const Color(0xFF6B6356);
    final cardBg = isDark ? const Color(0xFF1A1F26) : Colors.white;
    final border = isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0E1216) : const Color(0xFFF7F4EE),
      appBar: AppBar(
        title: Text('Historico', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
        elevation: 0,
        actions: [IconButton(onPressed: _loading ? null : _load, icon: Icon(Icons.refresh, color: fg))],
      ),
      body: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
            child: _filterBar(fg, muted, cardBg, border),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(child: Padding(padding: const EdgeInsets.all(16), child: Text(_error!)))
                    : _filtered.isEmpty
                        ? Center(child: Text('Sem registos.', style: TextStyle(color: muted)))
                        : RefreshIndicator(
                            onRefresh: _load,
                            child: ListView.separated(
                              padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                              itemCount: _filtered.length,
                              separatorBuilder: (_, __) => const SizedBox(height: 6),
                              itemBuilder: (_, i) => _row(_filtered[i], cardBg, border, fg, muted),
                            ),
                          ),
          ),
        ]),
      ),
    );
  }

  Widget _filterBar(Color fg, Color muted, Color cardBg, Color border) {
    Widget chip(String key, String label, int count) {
      final selected = _filter == key;
      return Expanded(
        child: GestureDetector(
          onTap: () => setState(() => _filter = key),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            margin: const EdgeInsets.symmetric(horizontal: 3),
            padding: const EdgeInsets.symmetric(vertical: 9),
            decoration: BoxDecoration(
              color: selected ? BuzUpColors.orange : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: selected ? BuzUpColors.orange : border),
            ),
            alignment: Alignment.center,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label,
                    style: TextStyle(
                      color: selected ? Colors.white : muted,
                      fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.3,
                    )),
                if (count > 0) ...[
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: selected ? Colors.white24 : muted.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text('$count',
                        style: TextStyle(
                          color: selected ? Colors.white : muted,
                          fontSize: 10, fontWeight: FontWeight.w800,
                        )),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }
    return Row(children: [
      chip('all', 'Todos', _items.length),
      chip('sale', 'Vendas', _salesCount),
      chip('topup', 'Recargas', _topupsCount),
    ]);
  }

  Widget _row(Map<String, dynamic> it, Color cardBg, Color border, Color fg, Color muted) {
    final kind = (it['kind'] as String?) ?? 'sale';
    final accent = _kindAccent(kind);
    final status = (it['status'] as String?) ?? '';
    final isSale = kind == 'sale';
    final title = isSale
        ? '${it['route_code'] ?? '-'} · ${it['quantity'] ?? 1}x'
        : (it['label']?.toString().isNotEmpty == true
            ? it['label'].toString()
            : 'Recarga de carteira');
    final subtitle = isSale
        ? '${it['origin'] ?? '-'} → ${it['destination'] ?? '-'} · ${it['payer_phone_masked'] ?? '-'}'
        : 'Ref: ${(it['payment_reference'] ?? '').toString().split('-').last} · ${it['payer_phone_masked'] ?? '-'}';
    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: border),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(children: [
        Container(
          width: 36, height: 36,
          decoration: BoxDecoration(
            color: accent.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(9),
          ),
          child: Icon(_kindIcon(kind), color: accent, size: 18),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(title,
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: TextStyle(color: fg, fontSize: 13.5, fontWeight: FontWeight.w800)),
            const SizedBox(height: 1),
            Text(subtitle,
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: TextStyle(color: muted, fontSize: 11)),
          ]),
        ),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
          Text('${it['amount']} MZN',
              style: TextStyle(color: fg, fontSize: 13.5, fontWeight: FontWeight.w800)),
          Text(status.toUpperCase(),
              style: TextStyle(color: _statusColor(status), fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
        ]),
      ]),
    );
  }
}
