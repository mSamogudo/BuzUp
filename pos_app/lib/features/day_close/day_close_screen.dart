import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class DayCloseScreen extends ConsumerStatefulWidget {
  const DayCloseScreen({super.key});

  @override
  ConsumerState<DayCloseScreen> createState() => _DayCloseScreenState();
}

class _KpiData {
  final IconData icon;
  final String label;
  final String value;
  final String footer;
  final Color accent;
  const _KpiData({
    required this.icon,
    required this.label,
    required this.value,
    required this.footer,
    required this.accent,
  });
}

class _DayCloseScreenState extends ConsumerState<DayCloseScreen> {
  bool _loading = true;
  bool _closing = false;
  String? _error;
  Map<String, dynamic> _data = {};
  int _detailTab = 0;

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
      final res = await ref.read(agentApiProvider).dayClosePreview();
      setState(() => _data = res);
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _close() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Fechar Dia'),
        content: const Text(
          'Vai encerrar a sua sessao e submeter a receita do dia ao sistema.\n\n'
          'Esta accao nao pode ser desfeita. Continuar?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('FECHAR DIA')),
        ],
      ),
    );
    if (confirm != true) return;
    setState(() => _closing = true);
    try {
      await ref.read(agentApiProvider).dayClose();
      await AppFeedback.success();
      // Session stays open: agent continues working after submitting the day-close.
      // Reset local view to zeroed payload so KPI cards show 0 until next refresh.
      if (mounted) {
        setState(() => _data = {});
        await _load();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Dia fechado e submetido. Pode continuar a vender.')),
        );
        await Future<void>.delayed(const Duration(milliseconds: 700));
        if (mounted) context.go('/home');
      }
    } on DioException catch (e) {
      await AppFeedback.error();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ApiClient.extractError(e))));
      }
    } finally {
      if (mounted) setState(() => _closing = false);
    }
  }

  int _mainTab = 0; // 0 = resumo financeiro, 1 = transacoes

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    final totals = (_data['totals'] as Map?) ?? const {};
    final sales = (_data['sales'] as List?) ?? const [];
    final topups = (_data['topups'] as List?) ?? const [];
    final validations = (_data['validations'] as List?) ?? const [];

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0E1216) : const Color(0xFFF7F4EE),
      appBar: AppBar(
        title: Text('Fecho do Dia', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
        actionsIconTheme: IconThemeData(color: fg),
        actions: [
          IconButton(
            tooltip: 'Recarregar',
            onPressed: _loading ? null : _load,
            icon: Icon(Icons.refresh, color: fg),
          ),
        ],
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Padding(padding: const EdgeInsets.all(16), child: Text(_error!)))
                : Padding(
                    padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _mainTabs(),
                        const SizedBox(height: 10),
                        Expanded(
                          child: _mainTab == 0
                              ? _summaryView(context, totals)
                              : _transactionsView(context, sales, topups, validations),
                        ),
                        const SizedBox(height: 8),
                        _closeButton(context),
                      ],
                    ),
                  ),
      ),
    );
  }

  Widget _mainTabs() {
    const labels = ['Resumo financeiro', 'Ver transacoes'];
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1A1F26) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4)),
      ),
      padding: const EdgeInsets.all(4),
      child: Row(
        children: List.generate(2, (i) {
          final active = i == _mainTab;
          return Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _mainTab = i),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: active ? BuzUpColors.orange : Colors.transparent,
                  borderRadius: BorderRadius.circular(9),
                ),
                alignment: Alignment.center,
                child: Text(
                  labels[i],
                  style: TextStyle(
                    color: active ? Colors.white : (isDark ? Colors.white70 : const Color(0xFF6B6356)),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _summaryView(BuildContext context, Map totals) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _heroTotal(context, totals, compact: false),
          const SizedBox(height: 12),
          _kpiGrid(context, totals, compact: false),
        ],
      ),
    );
  }

  Widget _transactionsView(BuildContext context, List sales, List topups, List validations) {
    final counts = [sales.length, topups.length, validations.length];
    return Column(
      children: [
        _segmentedTabs(counts),
        const SizedBox(height: 8),
        Expanded(child: _detailList(context, sales, topups, validations)),
      ],
    );
  }

  // ---------- Hero (revenue) ----------

  Widget _heroTotal(BuildContext context, Map totals, {required bool compact}) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: compact ? 12 : 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          colors: [Color(0xFFFF6B00), Color(0xFFFF8C2E)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(color: BuzUpColors.orange.withValues(alpha: 0.32), blurRadius: 18, offset: const Offset(0, 6)),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.account_balance_wallet, color: Colors.white, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'RECEITA EM CAIXA',
                  style: TextStyle(color: Colors.white70, fontSize: 11, letterSpacing: 1.4, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${totals['revenue'] ?? '0.00'} MZN',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: compact ? 26 : 30,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.4,
                    ),
                  ),
                ),
                const Text(
                  'Vendas + Recargas',
                  style: TextStyle(color: Colors.white70, fontSize: 10.5, letterSpacing: 0.4),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const Text('DATA', style: TextStyle(color: Colors.white70, fontSize: 9, letterSpacing: 1.3, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(
                  _data['date']?.toString() ?? '',
                  style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------- KPI grid ----------
  // 2 colunas: cards mais largos para o texto caber inteiro, sem reticencias.

  Widget _kpiGrid(BuildContext context, Map totals, {required bool compact}) {
    final tiles = [
      _kpiData(
        icon: Icons.confirmation_number,
        label: 'VENDAS',
        value: '${totals['sales'] ?? '0.00'} MZN',
        footer: '${totals['tickets'] ?? 0} bilhetes emitidos',
        accent: const Color(0xFF1FB04A),
      ),
      _kpiData(
        icon: Icons.credit_card,
        label: 'RECARGAS',
        value: '${totals['topups'] ?? '0.00'} MZN',
        footer: 'Saldo carregado em carteiras',
        accent: const Color(0xFF0B6FE0),
      ),
      _kpiData(
        icon: Icons.qr_code_scanner,
        label: 'VALIDACOES',
        value: '${totals['validations'] ?? 0}',
        footer: '${totals['validations_revenue'] ?? '0.00'} MZN debitados',
        accent: const Color(0xFF8B5CF6),
      ),
      _kpiData(
        icon: Icons.account_balance_wallet,
        label: 'A ENTREGAR',
        value: '${totals['revenue'] ?? '0.00'} MZN',
        footer: 'Vendas + Recargas (em caixa)',
        accent: const Color(0xFFEAB308),
      ),
    ];
    return Column(
      children: [
        Row(children: [
          Expanded(child: _kpiTile(context, tiles[0], compact: compact)),
          const SizedBox(width: 8),
          Expanded(child: _kpiTile(context, tiles[1], compact: compact)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _kpiTile(context, tiles[2], compact: compact)),
          const SizedBox(width: 8),
          Expanded(child: _kpiTile(context, tiles[3], compact: compact)),
        ]),
      ],
    );
  }

  _KpiData _kpiData({
    required IconData icon,
    required String label,
    required String value,
    required String footer,
    required Color accent,
  }) => _KpiData(icon: icon, label: label, value: value, footer: footer, accent: accent);

  Widget _kpiTile(BuildContext context, _KpiData k, {required bool compact}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: compact ? 10 : 13),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1A1F26) : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: k.accent.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(k.icon, size: 16, color: k.accent),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                k.label,
                style: TextStyle(
                  color: isDark ? Colors.white70 : const Color(0xFF6B6356),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
            ),
          ]),
          const SizedBox(height: 8),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              k.value,
              style: TextStyle(
                color: isDark ? Colors.white : const Color(0xFF15191E),
                fontSize: compact ? 18 : 21,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            k.footer,
            style: TextStyle(
              color: isDark ? Colors.white54 : const Color(0xFF8C8475),
              fontSize: 10.5,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }

  // ---------- Segmented tabs ----------

  Widget _segmentedTabs(List<int> counts) {
    const labels = ['Vendas', 'Recargas', 'Validacoes'];
    return Container(
      height: 38,
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark ? const Color(0xFF1A1F26) : const Color(0xFFEFE9DD),
        borderRadius: BorderRadius.circular(10),
      ),
      padding: const EdgeInsets.all(3),
      child: Row(
        children: List.generate(3, (i) {
          final isActive = i == _detailTab;
          return Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _detailTab = i),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: isActive ? BuzUpColors.orange : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text('${labels[i]} (${counts[i]})',
                    style: TextStyle(
                      color: isActive ? Colors.white : (Theme.of(context).brightness == Brightness.dark ? Colors.white70 : const Color(0xFF6B6356)),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                    )),
              ),
            ),
          );
        }),
      ),
    );
  }

  // ---------- Detail lists ----------

  Widget _detailList(BuildContext context, List sales, List topups, List validations) {
    final list = [sales, topups, validations][_detailTab];
    if (list.isEmpty) {
      final empty = ['Sem vendas hoje.', 'Sem recargas hoje.', 'Sem validacoes hoje.'][_detailTab];
      return _emptyHint(context, empty);
    }
    if (_detailTab == 0) return _salesList(sales);
    if (_detailTab == 1) return _topupsList(topups);
    return _validationsList(validations);
  }

  Widget _emptyHint(BuildContext context, String text) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1A1F26) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4)),
      ),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Text(text,
              style: TextStyle(color: isDark ? Colors.white54 : const Color(0xFF8C8475), fontSize: 12.5)),
        ),
      ),
    );
  }

  Widget _wrap(BuildContext context, List<Widget> rows) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1A1F26) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4)),
      ),
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
        itemCount: rows.length,
        separatorBuilder: (_, __) => Divider(height: 1, color: isDark ? const Color(0xFF252B33) : const Color(0xFFEFE9DD)),
        itemBuilder: (_, i) => rows[i],
      ),
    );
  }

  Widget _row({
    required Color accent,
    required IconData icon,
    required String title,
    required String subtitle,
    required String trailing,
    required String trailingSmall,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      dense: true,
      visualDensity: const VisualDensity(horizontal: -2, vertical: -2),
      leading: CircleAvatar(
        radius: 14,
        backgroundColor: accent.withValues(alpha: 0.18),
        child: Icon(icon, color: accent, size: 14),
      ),
      title: Text(title,
          maxLines: 1, overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: isDark ? Colors.white : const Color(0xFF15191E))),
      subtitle: Text(subtitle,
          maxLines: 1, overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 10.5, color: isDark ? Colors.white54 : const Color(0xFF8C8475))),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(trailing, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: accent)),
          Text(trailingSmall, style: TextStyle(fontSize: 9.5, color: isDark ? Colors.white38 : const Color(0xFF8C8475))),
        ],
      ),
    );
  }

  Widget _salesList(List items) {
    return _wrap(context, items.map((it) {
      final m = it as Map<String, dynamic>;
      final ok = m['status'] == 'confirmed';
      return _row(
        accent: ok ? const Color(0xFF1FB04A) : (m['status'] == 'pending' ? const Color(0xFFEAB308) : BuzUpColors.danger),
        icon: ok ? Icons.check_circle : (m['status'] == 'pending' ? Icons.access_time : Icons.error_outline),
        title: '${m['amount']} MZN · ${m['quantity'] ?? 1} bilhete(s)',
        subtitle: '${m['payer_phone_masked'] ?? ''} · ${m['sale_reference'] ?? ''}',
        trailing: (m['status'] ?? '').toString().toUpperCase(),
        trailingSmall: '',
      );
    }).toList());
  }

  Widget _topupsList(List items) {
    return _wrap(context, items.map((it) {
      final m = it as Map<String, dynamic>;
      return _row(
        accent: const Color(0xFF0B6FE0),
        icon: Icons.account_balance_wallet,
        title: '${m['amount']} MZN',
        subtitle: '${m['payer_phone_masked'] ?? ''} · ${m['reference'] ?? ''}',
        trailing: (m['status'] ?? '').toString().toUpperCase(),
        trailingSmall: '',
      );
    }).toList());
  }

  Widget _validationsList(List items) {
    return _wrap(context, items.map((it) {
      final m = it as Map<String, dynamic>;
      final ok = m['status'] == 'approved';
      return _row(
        accent: ok ? const Color(0xFF8B5CF6) : BuzUpColors.danger,
        icon: ok ? Icons.verified : Icons.error_outline,
        title: '${m['amount_debited'] ?? '0.00'} MZN · ${m['route'] ?? ''}',
        subtitle: '${m['validation_type'] ?? ''}',
        trailing: (m['status'] ?? '').toString().toUpperCase(),
        trailingSmall: '',
      );
    }).toList());
  }

  // ---------- Close button ----------

  Widget _closeButton(BuildContext context) {
    return SizedBox(
      height: 52,
      child: FilledButton.icon(
        style: FilledButton.styleFrom(
          backgroundColor: BuzUpColors.danger,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.5),
        ),
        icon: _closing ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Icon(Icons.lock),
        label: Text(_closing ? 'A FECHAR DIA...' : 'FECHAR DIA E SUBMETER'),
        onPressed: _closing || _loading ? null : _close,
      ),
    );
  }
}
