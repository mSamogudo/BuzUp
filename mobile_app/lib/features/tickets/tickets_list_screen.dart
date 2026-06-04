import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/bus_loader.dart';
import '../../core/i18n.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

final _ticketsTabProvider = StateProvider<int>((_) => 0);

class TicketsListScreen extends ConsumerWidget {
  const TicketsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = ref.watch(trProvider);
    final tab = ref.watch(_ticketsTabProvider);
    final filter = tab == 0 ? 'active' : 'used,expired,cancelled';
    final futureKey = ValueKey(filter);
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('tickets.title')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: BuzUpColors.orange,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: Text(tr('tickets.buy'),
            style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.6)),
        onPressed: () => context.push('/tickets/buy'),
      ),
      body: SafeArea(
        child: Column(children: [
          _tabs(context, ref, tab),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              key: futureKey,
              future: ref.read(passengerApiProvider).myTickets(statusFilter: filter, limit: 80),
              builder: (ctx, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return Center(child: BusLoader(label: tr('tickets.loading')));
                }
                if (snap.hasError) {
                  return Center(child: Text('Erro: ${snap.error}',
                      style: const TextStyle(color: BuzUpColors.danger)));
                }
                final items = snap.data ?? const [];
                if (items.isEmpty) {
                  return _empty(context, tab, tr);
                }
                return RefreshIndicator(
                  onRefresh: () async {
                    // Bump the tab provider to force-rebuild the FutureBuilder.
                    final cur = ref.read(_ticketsTabProvider);
                    ref.read(_ticketsTabProvider.notifier).state = -1;
                    await Future<void>.delayed(const Duration(milliseconds: 50));
                    ref.read(_ticketsTabProvider.notifier).state = cur;
                  },
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: items.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (_, i) => _row(context, items[i]),
                  ),
                );
              },
            ),
          ),
        ]),
      ),
    );
  }

  Widget _tabs(BuildContext context, WidgetRef ref, int tab) {
    final tr = ref.watch(trProvider);
    final outline = Theme.of(context).colorScheme.outline;
    Widget btn(int i, String label) {
      final selected = tab == i;
      return Expanded(
        child: GestureDetector(
          onTap: () => ref.read(_ticketsTabProvider.notifier).state = i,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: selected ? BuzUpColors.orange : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: Text(label,
                  style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.6,
                      color: selected ? Colors.white : BuzUpColors.muted)),
            ),
          ),
        ),
      );
    }
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: outline),
      ),
      child: Row(children: [btn(0, tr('tickets.tabActive')), btn(1, tr('tickets.tabHistory'))]),
    );
  }

  Widget _empty(BuildContext context, int tab, dynamic tr) {
    final msg = tab == 0 ? tr('tickets.empty.active') : tr('tickets.empty.history');
    return ListView(children: [
      const SizedBox(height: 80),
      const Icon(Icons.confirmation_number_outlined,
          size: 64, color: BuzUpColors.muted),
      const SizedBox(height: 12),
      Center(child: Text(msg, style: const TextStyle(color: BuzUpColors.muted))),
      const SizedBox(height: 16),
      if (tab == 0)
        Center(
          child: FilledButton.icon(
            onPressed: () => context.push('/tickets/buy'),
            icon: const Icon(Icons.add),
            label: Text(tr('tickets.buy')),
          ),
        ),
    ]);
  }

  Widget _row(BuildContext context, Map<String, dynamic> tp) {
    final outline = Theme.of(context).colorScheme.outline;
    final surface = Theme.of(context).colorScheme.surface;
    final route = (tp['route_name'] ?? tp['route_code'] ?? '-').toString();
    final origin = (tp['origin_stop'] ?? '').toString();
    final dest = (tp['destination_stop'] ?? '').toString();
    final fare = tp['fare_amount']?.toString() ?? '0';
    final status = (tp['status'] ?? 'active').toString();
    final createdAt = tp['created_at']?.toString();
    final id = tp['id'] as int?;

    return Material(
      color: surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: id == null ? null : () => context.push('/tickets/$id'),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: outline),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: status == 'active'
                    ? BuzUpColors.orange.withValues(alpha: 0.14)
                    : BuzUpColors.muted.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.confirmation_number,
                  color: status == 'active' ? BuzUpColors.orange : BuzUpColors.muted),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(route,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                const SizedBox(height: 2),
                Text('${origin.isEmpty ? "?" : origin}  →  ${dest.isEmpty ? "?" : dest}',
                    style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
                if (createdAt != null) Text(_fmt(createdAt),
                    style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted)),
              ]),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
              Text('$fare MZN',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _statusColor(status).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(status.toUpperCase(),
                    style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w900,
                        color: _statusColor(status),
                        letterSpacing: 0.6)),
              ),
            ]),
            const SizedBox(width: 4),
            const Icon(Icons.chevron_right, color: BuzUpColors.muted),
          ]),
        ),
      ),
    );
  }

  static Color _statusColor(String s) => switch (s) {
    'active' => BuzUpColors.success,
    'used' => BuzUpColors.muted,
    _ => BuzUpColors.danger,
  };

  String _fmt(String iso) {
    try {
      return DateFormat('dd/MM/yyyy HH:mm', 'pt_PT').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }
}
