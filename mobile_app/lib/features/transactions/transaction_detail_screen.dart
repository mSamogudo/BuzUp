import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/bus_loader.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class TransactionDetailScreen extends ConsumerStatefulWidget {
  const TransactionDetailScreen({super.key, required this.txId});

  final int txId;

  @override
  ConsumerState<TransactionDetailScreen> createState() => _TransactionDetailScreenState();
}

class _TransactionDetailScreenState extends ConsumerState<TransactionDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    Log.info('tx.detail.load id=${widget.txId}');
    _future = ref.read(passengerApiProvider).transactionDetail(widget.txId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalhe do movimento'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/transactions'),
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (ctx, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: BusLoader(label: 'A carregar...'));
            }
            if (snap.hasError) {
              return Center(child: Text('Erro: ${snap.error}',
                  style: const TextStyle(color: BuzUpColors.danger)));
            }
            return _body(snap.data ?? const {});
          },
        ),
      ),
    );
  }

  Widget _body(Map<String, dynamic> tx) {
    final isCredit = tx['direction'] == 'credit';
    final color = isCredit ? BuzUpColors.success : BuzUpColors.danger;
    final amount = _money(tx['amount']);
    final type = (tx['type'] ?? '-').toString();
    final channelLabel = (tx['channel_label'] ?? '').toString();
    final provider = (tx['payment_provider_label'] ?? '').toString();
    final agent = (tx['agent_name'] ?? '').toString();
    final paymentRef = (tx['payment_reference'] ?? '').toString();
    final ref = (tx['reference'] ?? '').toString();
    final status = (tx['status'] ?? '-').toString();
    final balBefore = _money(tx['balance_before']);
    final balAfter = _money(tx['balance_after']);
    final createdAt = (tx['created_at'] ?? '').toString();
    final metadata = (tx['metadata'] as Map?)?.cast<String, dynamic>() ?? const {};

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        // Hero amount card
        Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isCredit
                  ? [const Color(0xFF1FB04A), const Color(0xFF24C757)]
                  : [BuzUpColors.navy, BuzUpColors.navyDark],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(isCredit ? Icons.arrow_downward : Icons.arrow_upward,
                  color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Text(isCredit ? 'CREDITO' : 'DEBITO',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      letterSpacing: 1.6,
                      fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 4),
            Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
              Text('${isCredit ? '+' : '-'}$amount',
                  style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: -0.4)),
              const SizedBox(width: 6),
              const Text('MZN', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 4),
            Text(_typeLabel(type),
                style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w700)),
          ]),
        ),
        const SizedBox(height: 14),

        // Channel + agent + payment
        _section(context, 'Canal', [
          if (channelLabel.isNotEmpty) _row(Icons.alt_route, 'Origem', channelLabel),
          if (provider.isNotEmpty) _row(Icons.account_balance, 'Provedor', provider),
          if (agent.isNotEmpty) _row(Icons.support_agent, 'Agente', agent),
          if (paymentRef.isNotEmpty) _row(Icons.tag, 'Ref. pagamento', paymentRef, copyable: true),
        ]),
        const SizedBox(height: 14),

        _section(context, 'Saldo', [
          _row(Icons.history, 'Saldo anterior', '$balBefore MZN', color: color),
          _row(Icons.bolt, 'Movimento', '${isCredit ? '+' : '-'}$amount MZN', color: color),
          _row(Icons.account_balance_wallet, 'Saldo final', '$balAfter MZN', strong: true),
        ]),
        const SizedBox(height: 14),

        _section(context, 'Detalhes', [
          _row(Icons.confirmation_number, 'Referencia', ref, copyable: true),
          _row(Icons.schedule, 'Data/hora', _formatDate(createdAt)),
          _row(Icons.check_circle_outline, 'Estado', status.toUpperCase()),
        ]),

        if (metadata.isNotEmpty) ...[
          const SizedBox(height: 14),
          _section(context, 'Metadata',
              metadata.entries.take(8).map((e) =>
                  _row(Icons.label_outline, e.key, e.value?.toString() ?? '-')).toList()),
        ],
      ],
    );
  }

  Widget _section(BuildContext context, String title, List<Widget> rows) {
    if (rows.isEmpty) return const SizedBox.shrink();
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
          child: Text(title.toUpperCase(),
              style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted,
                  fontWeight: FontWeight.w800, letterSpacing: 1.4)),
        ),
        for (int i = 0; i < rows.length; i++) ...[
          rows[i],
          if (i < rows.length - 1) const Divider(height: 1),
        ],
      ]),
    );
  }

  Widget _row(IconData icon, String label, String value,
      {bool copyable = false, Color? color, bool strong = false}) {
    final widget = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(children: [
        Icon(icon, size: 17, color: BuzUpColors.muted),
        const SizedBox(width: 10),
        Expanded(
          child: Text(label,
              style: const TextStyle(fontSize: 12.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        ),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: TextStyle(
                fontSize: strong ? 14.5 : 13,
                fontWeight: strong ? FontWeight.w900 : FontWeight.w800,
                color: color),
          ),
        ),
        if (copyable) IconButton(
          tooltip: 'Copiar',
          icon: const Icon(Icons.copy, size: 14),
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: value));
            if (!context.mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Copiado.')),
            );
          },
        ),
      ]),
    );
    return widget;
  }

  String _money(dynamic v) {
    final n = double.tryParse('${v ?? 0}') ?? 0;
    return NumberFormat('#,##0.00', 'pt_PT').format(n);
  }

  String _typeLabel(String t) => switch (t) {
        'topup' => 'Recarga de carteira',
        'fare_debit' => 'Pagamento de viagem',
        'refund' => 'Reembolso',
        'reversal' => 'Reversao',
        'adjustment' => 'Ajuste',
        'card_transfer' => 'Transferencia entre cartoes',
        'fee' => 'Taxa',
        _ => t,
      };

  String _formatDate(String iso) {
    try {
      return DateFormat('dd/MM/yyyy HH:mm:ss', 'pt_PT').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }
}
