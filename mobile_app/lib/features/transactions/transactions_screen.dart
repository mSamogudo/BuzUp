import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/i18n.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

final _transactionsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  return ref.watch(passengerApiProvider).transactions();
});

class TransactionsScreen extends ConsumerWidget {
  const TransactionsScreen({super.key});

  String _money(dynamic v) {
    final n = double.tryParse('${v ?? 0}') ?? 0;
    return NumberFormat('#,##0.00', 'pt_PT').format(n);
  }

  String _dateLabel(String iso) {
    try {
      final d = DateTime.parse(iso).toLocal();
      return DateFormat('dd MMM, HH:mm', 'pt_PT').format(d);
    } catch (_) {
      return iso;
    }
  }

  String _typeLabel(String t, dynamic tr) {
    final key = 'tx.type.$t';
    final lookup = tr(key);
    return lookup == key ? t : lookup;
  }

  IconData _typeIcon(String t) {
    switch (t) {
      case 'topup': return Icons.arrow_downward;
      case 'fare_debit': return Icons.directions_bus;
      case 'refund': return Icons.replay;
      case 'reversal': return Icons.undo;
      case 'fee': return Icons.payments;
      default: return Icons.swap_horiz;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = ref.watch(trProvider);
    final txs = ref.watch(_transactionsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('tx.title'), style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          IconButton(
            tooltip: tr('extract.title'),
            icon: const Icon(Icons.event_note),
            onPressed: () => context.push('/extract'),
          ),
          IconButton(
            tooltip: tr('common.refresh'),
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_transactionsProvider),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => ref.invalidate(_transactionsProvider),
          child: txs.when(
            loading: () => Center(child: BusLoader(label: tr('tx.loading'))),
            error: (e, _) {
              final msg = e is DioException ? ApiClient.extractError(e) : e.toString();
              return ListView(children: [
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Text(msg, style: const TextStyle(color: BuzUpColors.danger)),
                ),
              ]);
            },
            data: (list) {
              if (list.isEmpty) {
                return ListView(children: [
                  const SizedBox(height: 60),
                  const Icon(Icons.receipt_long, size: 64, color: BuzUpColors.muted),
                  const SizedBox(height: 12),
                  Center(child: Text(tr('tx.empty'),
                      style: TextStyle(color: BuzUpColors.muted.withValues(alpha: 0.9)))),
                ]);
              }
              return ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                itemCount: list.length,
                separatorBuilder: (_, _) => const SizedBox(height: 6),
                itemBuilder: (ctx, i) => _row(ctx, list[i], tr),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _row(BuildContext context, Map<String, dynamic> tx, dynamic tr) {
    final isCredit = tx['direction'] == 'credit';
    final type = tx['type']?.toString() ?? '-';
    final color = isCredit ? BuzUpColors.success : BuzUpColors.navy;
    final id = tx['id'] as int?;
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        borderRadius: BorderRadius.circular(11),
        onTap: id == null ? null : () => context.push('/transactions/$id'),
        child: Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Row(children: [
        Container(
          width: 38, height: 38,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(_typeIcon(type), color: color, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(_typeLabel(type, tr),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
            const SizedBox(height: 2),
            Text(_dateLabel(tx['created_at']?.toString() ?? ''),
                style: const TextStyle(fontSize: 11, color: BuzUpColors.muted)),
          ]),
        ),
        Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
          Text('${isCredit ? '+' : '-'}${_money(tx['amount'])}',
              style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 14)),
          Text('Saldo ${_money(tx['balance_after'])}',
              style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted)),
        ]),
        const SizedBox(width: 4),
        const Icon(Icons.chevron_right, size: 18, color: BuzUpColors.muted),
      ]),
        ),
      ),
    );
  }
}
