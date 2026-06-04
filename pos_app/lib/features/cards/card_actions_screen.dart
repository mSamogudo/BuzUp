import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Shown after a successful card lookup. Single viewport, no scroll.
/// All operations are done via mobile money (M-Pesa / E-Mola). No cash.
class CardActionsScreen extends ConsumerStatefulWidget {
  const CardActionsScreen({
    super.key,
    required this.card,
    this.cardUid,
    this.qrToken,
  });

  final Map<String, dynamic> card;
  final String? cardUid;
  final String? qrToken;

  @override
  ConsumerState<CardActionsScreen> createState() => _CardActionsScreenState();
}

enum _OperationMode { none, topupWallet, package, debitWallet }

class _CardActionsScreenState extends ConsumerState<CardActionsScreen> {
  _OperationMode _mode = _OperationMode.none;
  final _amountCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  Map<String, dynamic>? _selectedPackage;
  List<Map<String, dynamic>>? _packages;

  bool _busy = false;
  String? _busyLabel;
  String? _error;
  String? _success;

  late Map<String, dynamic> _cardData = Map<String, dynamic>.from(widget.card);
  Map<String, dynamic> get _card => _cardData;
  Map<String, dynamic>? get _wallet => (_card['wallet'] as Map?)?.cast<String, dynamic>();
  Map<String, dynamic>? get _passenger => (_card['passenger'] as Map?)?.cast<String, dynamic>();

  Future<void> _refreshCard() async {
    try {
      final res = await ref.read(agentApiProvider).cardLookup(
            cardUid: widget.cardUid,
            qrToken: widget.qrToken,
          );
      final fresh = (res['card'] as Map?)?.cast<String, dynamic>();
      if (fresh != null && mounted) {
        setState(() => _cardData = fresh);
      }
    } catch (_) {/* keep previous state */}
  }

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  bool get _amountValid {
    final n = double.tryParse(_amountCtrl.text.trim());
    return n != null && n > 0;
  }

  bool get _phoneValid {
    final t = _phoneCtrl.text.trim();
    return t.length >= 9;
  }

  bool get _canSubmit {
    switch (_mode) {
      case _OperationMode.none:
        return false;
      case _OperationMode.topupWallet:
        return _amountValid && _phoneValid;
      case _OperationMode.package:
        return _selectedPackage != null && _phoneValid;
      case _OperationMode.debitWallet:
        return _amountValid;
    }
  }

  Future<void> _ensurePackagesLoaded() async {
    if (_packages != null) return;
    try {
      final pkgs = await ref.read(agentApiProvider).listPackages();
      if (!mounted) return;
      setState(() => _packages = pkgs);
    } on DioException catch (e) {
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    }
  }

  Future<void> _submit() async {
    if (!_canSubmit) return;
    switch (_mode) {
      case _OperationMode.topupWallet:
        await _runTopup();
        break;
      case _OperationMode.package:
        await _runPackage();
        break;
      case _OperationMode.debitWallet:
        await _runDebit();
        break;
      case _OperationMode.none:
        break;
    }
  }

  Future<void> _runTopup() async {
    await _run('Recarga em curso...', () async {
      final res = await ref.read(agentApiProvider).walletTopup(
            cardUid: widget.cardUid,
            qrToken: widget.qrToken,
            amount: _amountCtrl.text.trim(),
            method: 'mobile_money',
            payerPhone: _phoneCtrl.text.trim(),
          );
      _handlePaymentResponse(res, 'Recarga');
    });
  }

  Future<void> _runPackage() async {
    final pkg = _selectedPackage!;
    await _run('A activar pacote...', () async {
      final res = await ref.read(agentApiProvider).packageTopup(
            cardUid: widget.cardUid,
            qrToken: widget.qrToken,
            packageId: (pkg['id'] as num).toInt(),
            method: 'mobile_money',
            payerPhone: _phoneCtrl.text.trim(),
          );
      _handlePaymentResponse(res, 'Pacote');
    });
  }

  Future<void> _runDebit() async {
    await _run('A debitar carteira...', () async {
      final res = await ref.read(agentApiProvider).walletDebit(
            cardUid: widget.cardUid,
            qrToken: widget.qrToken,
            amount: _amountCtrl.text.trim(),
          );
      await AppFeedback.success();
      setState(() {
        _success = 'Debitado. Novo saldo: ${res['balance_after'] ?? '-'} MZN';
        _error = null;
        _resetForm();
      });
      await _refreshCard();
    });
  }

  Future<void> _handlePaymentResponse(Map<String, dynamic> res, String label) async {
    final status = (res['status'] as String?) ?? '';
    if (status == 'confirmed') {
      AppFeedback.success();
      setState(() {
        _success = '$label confirmado. A actualizar saldo...';
        _error = null;
        _resetForm();
      });
      await _refreshCard();
    } else if (status == 'pending') {
      setState(() {
        _success = 'Pedido enviado ao telefone. Aguarde a confirmacao do passageiro.';
        _error = null;
        _resetForm();
      });
      await _refreshCard();
    } else {
      AppFeedback.error();
      setState(() => _error = 'Estado: $status');
    }
  }

  void _resetForm() {
    _amountCtrl.clear();
    _selectedPackage = null;
    _mode = _OperationMode.none;
  }

  Future<void> _run(String label, Future<void> Function() task) async {
    setState(() {
      _busy = true;
      _busyLabel = label;
      _error = null;
      _success = null;
    });
    try {
      await task();
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      await AppFeedback.error();
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _busyLabel = null;
        });
      }
    }
  }

  // ---------- Build ----------

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
        title: Text(_card['card_number']?.toString() ?? 'Cartao', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
        elevation: 0,
      ),
      body: SafeArea(
        child: _busy
            ? Center(child: BusLoader(label: _busyLabel ?? 'A processar...'))
            : Padding(
                padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  _identityHero(fg, muted),
                  const SizedBox(height: 10),
                  if (_error != null) _banner(_error!, BuzUpColors.danger, Icons.error_outline),
                  if (_success != null) _banner(_success!, BuzUpColors.success, Icons.check_circle),
                  if (_error == null && _success == null) const SizedBox(height: 0),
                  const SizedBox(height: 6),
                  Expanded(
                    child: _mode == _OperationMode.none
                        ? _operationGrid(cardBg, border, fg, muted)
                        : _operationForm(cardBg, border, fg, muted),
                  ),
                ]),
              ),
      ),
    );
  }

  Widget _banner(String text, Color color, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.40)),
      ),
      child: Row(children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 12.5, fontWeight: FontWeight.w700))),
      ]),
    );
  }

  // ---------- Identity (card + passenger compact) ----------

  Map<String, dynamic>? get _activePackage {
    final list = (_card['active_packages'] as List?) ?? const [];
    if (list.isEmpty) return null;
    return (list.first as Map).cast<String, dynamic>();
  }

  Widget _identityHero(Color fg, Color muted) {
    final p = _passenger;
    final pkg = _activePackage;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFF6B00), Color(0xFFFF8C2E)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          Container(
            padding: const EdgeInsets.all(7),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(9)),
            child: const Icon(Icons.credit_card, color: Colors.white, size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(
                p?['full_name']?.toString().isNotEmpty == true ? p!['full_name'].toString() : 'Sem passageiro',
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800),
              ),
              Text(
                '${_card['card_number']} · ${p?['phone_masked'] ?? '-'}',
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: const TextStyle(color: Colors.white70, fontSize: 10.5),
              ),
            ]),
          ),
          const SizedBox(width: 6),
          _statusPill(_card['status']?.toString() ?? ''),
        ]),
        const SizedBox(height: 8),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          _balanceBlock('SALDO', '${_wallet?['balance'] ?? '0.00'}', _wallet?['currency']?.toString() ?? 'MZN'),
          const SizedBox(width: 10),
          Container(width: 1, height: 30, color: Colors.white24),
          const SizedBox(width: 10),
          if (pkg != null)
            Expanded(child: _packageInline(pkg))
          else
            Expanded(
              child: Text('Sem pacote activo',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.55), fontSize: 10.5, fontStyle: FontStyle.italic)),
            ),
        ]),
      ]),
    );
  }

  Widget _balanceBlock(String label, String value, String unit) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      Text(label,
          style: const TextStyle(color: Colors.white70, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
      Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
        Text(value,
            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: -0.3)),
        const SizedBox(width: 3),
        Text(unit, style: const TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.w700)),
      ]),
    ]);
  }

  Widget _packageInline(Map<String, dynamic> pkg) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      Row(children: [
        const Icon(Icons.card_giftcard, color: Colors.white, size: 11),
        const SizedBox(width: 3),
        const Text('PACOTE',
            style: TextStyle(color: Colors.white70, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
      ]),
      Text(pkg['package_name']?.toString() ?? '-',
          maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
      Text('${pkg['trips_remaining']} viagens | exp. ${(pkg['expires_at'] ?? '').toString().split('T').first}',
          style: const TextStyle(color: Colors.white70, fontSize: 10)),
    ]);
  }

  Widget _statusPill(String status) {
    final lower = status.toLowerCase();
    String label;
    switch (lower) {
      case 'active': label = 'ACTIVO'; break;
      case 'blocked': label = 'BLOQ.'; break;
      case 'inactive': label = 'INACTIVO'; break;
      case 'lost': label = 'PERDIDO'; break;
      default: label = lower.toUpperCase();
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.20),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
    );
  }

  String _docLabel(String code) {
    switch (code) {
      case 'bi': return 'BI';
      case 'passport': return 'Passaporte';
      case 'driving_license': return 'Carta';
      default: return 'Doc.';
    }
  }

  // ---------- Operation grid (idle) ----------

  Widget _operationGrid(Color cardBg, Color border, Color fg, Color muted) {
    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        _opRow(fg, muted,
            icon: Icons.account_balance_wallet, accent: const Color(0xFF1FB04A),
            title: 'Recarregar carteira', subtitle: 'Saldo via M-Pesa / E-Mola',
            onTap: () => setState(() => _mode = _OperationMode.topupWallet)),
        Divider(height: 1, color: border),
        _opRow(fg, muted,
            icon: Icons.card_giftcard, accent: const Color(0xFF8B5CF6),
            title: 'Comprar pacote', subtitle: 'Plano de viagens',
            onTap: () async {
              setState(() => _mode = _OperationMode.package);
              await _ensurePackagesLoaded();
            }),
        Divider(height: 1, color: border),
        _opRow(fg, muted,
            icon: Icons.payments, accent: const Color(0xFFEAB308),
            title: 'Cobrar da carteira', subtitle: 'Debitar valor especifico',
            onTap: () => setState(() => _mode = _OperationMode.debitWallet)),
        Divider(height: 1, color: border),
        _opRow(fg, muted,
            icon: Icons.list_alt, accent: const Color(0xFF0B6FE0),
            title: 'Transacoes do cartao', subtitle: 'Em breve',
            onTap: () {
              setState(() => _error = 'Historico do cartao em breve.');
            }),
      ]),
    );
  }

  Widget _opRow(Color fg, Color muted, {
    required IconData icon, required String title, required String subtitle, required Color accent, required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
          child: Row(children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(color: accent.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, color: accent, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(title, style: TextStyle(color: fg, fontSize: 14, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(subtitle, style: TextStyle(color: muted, fontSize: 11)),
              ]),
            ),
            Icon(Icons.chevron_right, color: muted, size: 18),
          ]),
        ),
      ),
    );
  }

  // ---------- Operation form (active mode) ----------

  Widget _operationForm(Color cardBg, Color border, Color fg, Color muted) {
    final hasActivePkg = _activePackage != null;
    final title = switch (_mode) {
      _OperationMode.topupWallet => 'Recarregar carteira',
      _OperationMode.package => hasActivePkg ? 'Renovar pacote activo' : 'Comprar pacote',
      _OperationMode.debitWallet => 'Cobrar da carteira',
      _OperationMode.none => '',
    };
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        IconButton(
          icon: Icon(Icons.arrow_back, color: fg),
          onPressed: () => setState(() => _resetForm()),
        ),
        Expanded(child: Text(title, style: TextStyle(color: fg, fontSize: 15, fontWeight: FontWeight.w800))),
      ]),
      const SizedBox(height: 6),
      if (_mode == _OperationMode.package) _packagePicker(cardBg, border, fg, muted),
      if (_mode == _OperationMode.topupWallet || _mode == _OperationMode.debitWallet)
        _amountField(cardBg, border, fg, muted),
      if (_mode == _OperationMode.topupWallet || _mode == _OperationMode.package) ...[
        const SizedBox(height: 10),
        _phoneField(cardBg, border, fg, muted),
      ],
      if (_mode == _OperationMode.topupWallet || _mode == _OperationMode.package) ...[
        const SizedBox(height: 6),
        Row(children: [
          Icon(Icons.phone_iphone, size: 14, color: muted),
          const SizedBox(width: 4),
          Text('Pagamento via M-Pesa ou E-Mola.',
              style: TextStyle(color: muted, fontSize: 11)),
        ]),
      ],
      const SizedBox(height: 16),
      SizedBox(
        height: 48,
        child: FilledButton.icon(
          icon: const Icon(Icons.check_circle),
          label: const Text('CONFIRMAR'),
          style: FilledButton.styleFrom(
            backgroundColor: BuzUpColors.orange,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
            textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          onPressed: _canSubmit ? _submit : null,
        ),
      ),
      const Spacer(),
    ]);
  }

  Widget _amountField(Color cardBg, Color border, Color fg, Color muted) {
    return TextField(
      controller: _amountCtrl,
      autofocus: true,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
      style: TextStyle(color: fg, fontSize: 22, fontWeight: FontWeight.w800),
      onChanged: (_) => setState(() {}),
      decoration: InputDecoration(
        labelText: 'Valor',
        hintText: '0.00',
        suffixText: 'MZN',
        suffixStyle: TextStyle(color: muted, fontWeight: FontWeight.w700),
        filled: true,
        fillColor: cardBg,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: BuzUpColors.orange, width: 2),
        ),
      ),
    );
  }

  Widget _phoneField(Color cardBg, Color border, Color fg, Color muted) {
    return TextField(
      controller: _phoneCtrl,
      keyboardType: TextInputType.phone,
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9+]'))],
      style: TextStyle(color: fg, fontSize: 16, fontWeight: FontWeight.w700),
      onChanged: (_) => setState(() {}),
      decoration: InputDecoration(
        labelText: 'Telefone a cobrar',
        hintText: '258XXXXXXXXX',
        filled: true,
        fillColor: cardBg,
        prefixIcon: Icon(Icons.phone_iphone, color: muted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: BuzUpColors.orange, width: 2),
        ),
      ),
    );
  }

  Widget _packagePicker(Color cardBg, Color border, Color fg, Color muted) {
    if (_packages == null) {
      return const SizedBox(height: 60, child: Center(child: CircularProgressIndicator()));
    }
    if (_packages!.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: cardBg, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border),
        ),
        child: Center(child: Text('Sem pacotes activos.', style: TextStyle(color: muted))),
      );
    }
    return SizedBox(
      height: 230,
      child: ListView.separated(
        padding: EdgeInsets.zero,
        itemCount: _packages!.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (_, i) {
          final p = _packages![i];
          final selected = _selectedPackage != null && _selectedPackage!['id'] == p['id'];
          return _packageCard(p, selected, cardBg, border, fg, muted);
        },
      ),
    );
  }

  Widget _packageCard(Map<String, dynamic> p, bool selected, Color bg, Color border, Color fg, Color muted) {
    final accent = BuzUpColors.orange;
    return Material(
      color: selected ? accent.withValues(alpha: 0.08) : bg,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => setState(() => _selectedPackage = p),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? accent : border,
              width: selected ? 2 : 1,
            ),
          ),
          child: Row(children: [
            Container(
              width: 44, height: 44,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: selected ? 0.20 : 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.card_giftcard, color: accent, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(p['name']?.toString() ?? '-',
                    maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                    style: TextStyle(color: fg, fontSize: 14, fontWeight: FontWeight.w800)),
                const SizedBox(height: 3),
                Row(children: [
                  _pkgChip(Icons.calendar_today, '${p['validity_days']} dias', muted),
                  const SizedBox(width: 6),
                  _pkgChip(Icons.directions_bus, '${p['max_trips']} viagens', muted),
                ]),
              ]),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('${p['price']}',
                  style: TextStyle(color: accent, fontSize: 18, fontWeight: FontWeight.w800)),
              Text('MZN', style: TextStyle(color: muted, fontSize: 9.5, fontWeight: FontWeight.w700, letterSpacing: 0.8)),
            ]),
            const SizedBox(width: 6),
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 22, height: 22,
              decoration: BoxDecoration(
                color: selected ? accent : Colors.transparent,
                shape: BoxShape.circle,
                border: Border.all(color: selected ? accent : muted),
              ),
              child: selected ? const Icon(Icons.check, color: Colors.white, size: 14) : null,
            ),
          ]),
        ),
      ),
    );
  }

  Widget _pkgChip(IconData icon, String text, Color muted) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: muted.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 10, color: muted),
        const SizedBox(width: 3),
        Text(text, style: TextStyle(color: muted, fontSize: 10, fontWeight: FontWeight.w700)),
      ]),
    );
  }
}
