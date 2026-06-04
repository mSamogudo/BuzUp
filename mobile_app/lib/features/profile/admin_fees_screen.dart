import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/bus_loader.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Shows the operator's administrative fees (card issuance, recovery, fines)
/// so the passenger can see ahead of time what to expect on non-trip
/// operations. Comes from /api/auth/me/passenger-portal/admin-fees/ filtered
/// to is_active=True.
class AdminFeesScreen extends ConsumerWidget {
  const AdminFeesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Taxas e tarifas'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/profile'),
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: ref.read(passengerApiProvider).adminFees(),
          builder: (ctx, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: BusLoader(label: 'A carregar taxas...'));
            }
            if (snap.hasError) {
              return Center(child: Text('Erro: ${snap.error}',
                  style: const TextStyle(color: BuzUpColors.danger)));
            }
            final fees = snap.data ?? const [];
            if (fees.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Icon(Icons.receipt_long_outlined, size: 64, color: BuzUpColors.muted),
                SizedBox(height: 12),
                Center(child: Text('Sem taxas activas no momento.',
                    style: TextStyle(color: BuzUpColors.muted))),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              itemCount: fees.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _feeCard(context, fees[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _feeCard(BuildContext context, Map<String, dynamic> fee) {
    final name = (fee['name'] ?? '-').toString();
    final kind = (fee['kind'] ?? '').toString();
    final kindLabel = (fee['kind_label'] ?? '').toString();
    final amount = double.tryParse('${fee['amount'] ?? 0}') ?? 0;
    final currency = (fee['currency'] ?? 'MZN').toString();
    final description = (fee['description'] ?? '').toString();
    final money = NumberFormat('#,##0.00', 'pt_PT').format(amount);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 42, height: 42,
          decoration: BoxDecoration(
            color: _color(kind).withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Icon(_icon(kind), color: _color(kind), size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(name, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5)),
            const SizedBox(height: 2),
            Text(kindLabel.isEmpty ? kind : kindLabel,
                style: const TextStyle(fontSize: 11, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
            if (description.isNotEmpty) Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(description,
                  style: const TextStyle(fontSize: 12, color: BuzUpColors.muted)),
            ),
          ]),
        ),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
          Text(money,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: _color(kind))),
          Text(currency,
              style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        ]),
      ]),
    );
  }

  Color _color(String kind) => switch (kind) {
        'card_issuance' => BuzUpColors.orange,
        'card_recovery' => BuzUpColors.navy,
        'fine' => BuzUpColors.danger,
        _ => BuzUpColors.muted,
      };

  IconData _icon(String kind) => switch (kind) {
        'card_issuance' => Icons.add_card,
        'card_recovery' => Icons.find_replace,
        'fine' => Icons.gavel,
        _ => Icons.receipt_long,
      };
}
