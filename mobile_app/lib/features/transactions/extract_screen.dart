import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart' show launchUrl, LaunchMode;

import '../../core/bus_loader.dart';
import '../../core/config.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Account extract: credit/debit list with running balance, date range filter,
/// summary header (totais) and link to download the PDF version.
class ExtractScreen extends ConsumerStatefulWidget {
  const ExtractScreen({super.key});

  @override
  ConsumerState<ExtractScreen> createState() => _ExtractScreenState();
}

class _ExtractScreenState extends ConsumerState<ExtractScreen> {
  DateTimeRange _range = DateTimeRange(
    start: DateTime.now().subtract(const Duration(days: 30)),
    end: DateTime.now(),
  );
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    // For now we filter client-side because the existing transactions endpoint
    // doesn't take date params. We can add them server-side later if the
    // 60-row default cap becomes a problem.
    Log.info('extract.load range=${_range.start.toIso8601String()}->${_range.end.toIso8601String()}');
    final all = await ref.read(passengerApiProvider).transactions(limit: 200);
    return all.where((tx) {
      try {
        final dt = DateTime.parse(tx['created_at'] as String).toLocal();
        return !dt.isBefore(_range.start) &&
            !dt.isAfter(_range.end.add(const Duration(days: 1)));
      } catch (_) {
        return false;
      }
    }).toList();
  }

  Future<void> _pickRange() async {
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now().subtract(const Duration(days: 365 * 2)),
      lastDate: DateTime.now(),
      initialDateRange: _range,
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: Theme.of(ctx).colorScheme.copyWith(primary: BuzUpColors.orange),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _range = picked;
        _future = _load();
      });
    }
  }

  Future<void> _downloadPdf() async {
    final token = await ref.read(secureStoreProvider).getAccess();
    if (token == null || token.isEmpty) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sessao expirada.')),
      );
      return;
    }
    final df = DateFormat('yyyy-MM-dd');
    final url =
        '${AppConfig.apiBaseUrl}/api/auth/me/passenger-portal/extract/'
        '?token=${Uri.encodeQueryComponent(token)}'
        '&date_from=${df.format(_range.start)}'
        '&date_to=${df.format(_range.end)}';
    final ok = await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nao foi possivel abrir o PDF.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Extracto'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/profile'),
        ),
        actions: [
          IconButton(
            tooltip: 'PDF',
            icon: const Icon(Icons.picture_as_pdf),
            onPressed: _downloadPdf,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          _rangeBar(),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: _future,
              builder: (ctx, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: BusLoader(label: 'A calcular...'));
                }
                if (snap.hasError) {
                  return Center(child: Text('Erro: ${snap.error}',
                      style: const TextStyle(color: BuzUpColors.danger)));
                }
                final txs = snap.data ?? const [];
                final totals = _totals(txs);
                if (txs.isEmpty) {
                  return _empty();
                }
                return Column(children: [
                  _summary(totals),
                  Expanded(
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                      itemCount: txs.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 6),
                      itemBuilder: (_, i) => _row(txs[i]),
                    ),
                  ),
                ]);
              },
            ),
          ),
        ]),
      ),
    );
  }

  Widget _rangeBar() {
    final df = DateFormat('dd MMM yyyy', 'pt_PT');
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 6),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Row(children: [
        const Icon(Icons.calendar_today, size: 18, color: BuzUpColors.orange),
        const SizedBox(width: 10),
        Expanded(
          child: Text('${df.format(_range.start)} - ${df.format(_range.end)}',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
        ),
        TextButton.icon(
          onPressed: _pickRange,
          icon: const Icon(Icons.edit_calendar, size: 16),
          label: const Text('Alterar'),
        ),
      ]),
    );
  }

  Widget _summary(_Totals t) {
    Widget pill(String label, String value, Color color, IconData icon) {
      return Expanded(
        child: Container(
          padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Row(children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 6),
              Text(label.toUpperCase(),
                  style: const TextStyle(fontSize: 9.5, letterSpacing: 1.0, fontWeight: FontWeight.w800, color: BuzUpColors.muted)),
            ]),
            const SizedBox(height: 4),
            Text(value,
                style: TextStyle(color: color, fontSize: 14.5, fontWeight: FontWeight.w900)),
          ]),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(children: [
        pill('Creditos', '+${_money(t.credit)}', BuzUpColors.success, Icons.arrow_downward),
        const SizedBox(width: 8),
        pill('Debitos', '-${_money(t.debit)}', BuzUpColors.danger, Icons.arrow_upward),
        const SizedBox(width: 8),
        pill('Saldo', _money(t.net), BuzUpColors.orange, Icons.account_balance_wallet),
      ]),
    );
  }

  Widget _empty() {
    return ListView(children: [
      const SizedBox(height: 80),
      const Icon(Icons.event_note_outlined, size: 64, color: BuzUpColors.muted),
      const SizedBox(height: 10),
      const Center(child: Text('Sem movimentos no periodo seleccionado.',
          style: TextStyle(color: BuzUpColors.muted))),
    ]);
  }

  Widget _row(Map<String, dynamic> tx) {
    final isCredit = tx['direction'] == 'credit';
    final color = isCredit ? BuzUpColors.success : BuzUpColors.danger;
    final type = (tx['type'] ?? '-').toString();
    final ref = (tx['reference'] ?? '').toString();
    final id = tx['id'] as int?;
    final balAfter = _money(tx['balance_after']);
    final amount = _money(tx['amount']);
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        borderRadius: BorderRadius.circular(11),
        onTap: id == null ? null : () => context.push('/transactions/$id'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
            border: Border.all(color: Theme.of(context).colorScheme.outline),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(isCredit ? Icons.arrow_downward : Icons.arrow_upward,
                  color: color, size: 16),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(_typeLabel(type),
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                Text(_fmtDate(tx['created_at']?.toString() ?? ''),
                    style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted)),
                if (ref.isNotEmpty)
                  Text(ref, style: const TextStyle(fontSize: 10, color: BuzUpColors.muted)),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
              Text('${isCredit ? '+' : '-'}$amount',
                  style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 13.5)),
              Text('Saldo $balAfter',
                  style: const TextStyle(fontSize: 10, color: BuzUpColors.muted)),
            ]),
            const SizedBox(width: 4),
            const Icon(Icons.chevron_right, size: 18, color: BuzUpColors.muted),
          ]),
        ),
      ),
    );
  }

  _Totals _totals(List<Map<String, dynamic>> txs) {
    double credit = 0, debit = 0;
    for (final t in txs) {
      final amt = double.tryParse('${t['amount'] ?? 0}') ?? 0;
      if (t['direction'] == 'credit') {
        credit += amt;
      } else {
        debit += amt;
      }
    }
    return _Totals(credit: credit, debit: debit, net: credit - debit);
  }

  String _money(dynamic v) {
    final n = v is num ? v : double.tryParse('${v ?? 0}') ?? 0;
    return NumberFormat('#,##0.00', 'pt_PT').format(n);
  }

  String _typeLabel(String t) => switch (t) {
        'topup' => 'Recarga',
        'fare_debit' => 'Viagem',
        'refund' => 'Reembolso',
        'reversal' => 'Reversao',
        'adjustment' => 'Ajuste',
        'card_transfer' => 'Transferencia',
        'fee' => 'Taxa',
        _ => t,
      };

  String _fmtDate(String iso) {
    try {
      return DateFormat('dd/MM/yyyy HH:mm', 'pt_PT').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }
}

class _Totals {
  _Totals({required this.credit, required this.debit, required this.net});
  final double credit;
  final double debit;
  final double net;
}
