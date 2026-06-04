import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class VerifyScreen extends ConsumerStatefulWidget {
  const VerifyScreen({super.key});

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> with SingleTickerProviderStateMixin {
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  late TabController _tabs;
  final _shortcodeCtrl = TextEditingController();
  final _routeCtrl = TextEditingController();
  bool _checking = false;
  Map<String, dynamic>? _last;
  String? _error;
  bool _torch = false;
  bool _nfcArmed = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _tabs.addListener(() {
      if (_tabs.index == 2) {
        _armNfc();
      } else {
        NfcCardReader.stop();
        _nfcArmed = false;
      }
      setState(() {});
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _tabs.dispose();
    _shortcodeCtrl.dispose();
    _routeCtrl.dispose();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _armNfc() async {
    if (_nfcArmed) return;
    _nfcArmed = true;
    try {
      await NfcCardReader.startStream((uid) async {
        if (_routeCtrl.text.trim().isEmpty) {
          await AppFeedback.error();
          setState(() => _error = 'Indique o ID da rota antes de validar.');
          return;
        }
        await AppFeedback.softBeep();
        await _validateCard(uid);
      });
    } on NfcUnavailableException catch (e) {
      setState(() => _error = e.message);
      _nfcArmed = false;
    } catch (e) {
      setState(() => _error = e.toString());
      _nfcArmed = false;
    }
  }

  Future<void> _validateCard(String uid) async {
    final routeId = int.tryParse(_routeCtrl.text.trim());
    if (routeId == null) return;
    setState(() {
      _checking = true;
      _last = null;
      _error = null;
    });
    try {
      final serial = await ref.read(secureStoreProvider).getDeviceSerial();
      final res = await ref.read(agentApiProvider).validateCard(
            cardUid: uid,
            routeId: routeId,
            deviceSerial: serial,
          );
      await (res['valid'] == true ? AppFeedback.success() : AppFeedback.error());
      setState(() => _last = res);
    } on DioException catch (e) {
      await AppFeedback.error();
      final body = e.response?.data;
      if (body is Map) {
        setState(() => _last = Map<String, dynamic>.from(body));
      } else {
        setState(() => _error = ApiClient.extractError(e));
      }
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_checking) return;
    final raw = capture.barcodes.first.rawValue;
    if (raw == null || raw.isEmpty) return;
    await _verifyToken(raw);
  }

  Future<void> _verifyToken(String token) async {
    setState(() {
      _checking = true;
      _error = null;
      _last = null;
    });
    try {
      final res = await ref.read(agentApiProvider).verifyTicket(token);
      _handleResult(res);
    } on DioException catch (e) {
      await _handleError(e);
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Future<void> _verifyShortcode() async {
    final code = _shortcodeCtrl.text.trim().toUpperCase();
    if (code.length != 4) {
      setState(() => _error = 'O codigo deve ter exactamente 4 caracteres.');
      return;
    }
    setState(() {
      _checking = true;
      _error = null;
      _last = null;
    });
    try {
      final res = await ref.read(agentApiProvider).verifyTicketByShortcode(code);
      _handleResult(res);
    } on DioException catch (e) {
      await _handleError(e);
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Future<void> _handleResult(Map<String, dynamic> res) async {
    final valid = res['valid'] == true;
    if (valid) {
      await AppFeedback.success();
    } else {
      await AppFeedback.error();
    }
    setState(() => _last = res);
  }

  Future<void> _handleError(DioException e) async {
    await AppFeedback.error();
    final body = e.response?.data;
    if (body is Map) {
      setState(() => _last = Map<String, dynamic>.from(body));
    } else {
      setState(() => _error = ApiClient.extractError(e));
    }
  }

  void _reset() {
    setState(() {
      _last = null;
      _error = null;
      _shortcodeCtrl.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0E1216) : const Color(0xFFF7F4EE),
      appBar: AppBar(
        title: Text('Validar Bilhete', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        elevation: 0,
        iconTheme: IconThemeData(color: fg),
        actionsIconTheme: IconThemeData(color: fg),
        bottom: TabBar(
          controller: _tabs,
          labelColor: BuzUpColors.orange,
          indicatorColor: BuzUpColors.orange,
          unselectedLabelColor: isDark ? Colors.white60 : const Color(0xFF6B6356),
          tabs: const [
            Tab(icon: Icon(Icons.qr_code_scanner), text: 'QR'),
            Tab(icon: Icon(Icons.dialpad), text: 'Codigo'),
            Tab(icon: Icon(Icons.nfc), text: 'Cartao'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Flash',
            icon: Icon(_torch ? Icons.flash_on : Icons.flash_off, color: fg),
            onPressed: () async {
              await _controller.toggleTorch();
              setState(() => _torch = !_torch);
            },
          ),
        ],
      ),
      body: Stack(children: [
        TabBarView(
          controller: _tabs,
          children: [
            _qrTab(),
            _shortcodeTab(isDark),
            _cardTab(isDark),
          ],
        ),
        if (_last != null || _error != null) _resultOverlay(isDark),
      ]),
    );
  }

  /// Full-screen dimmed overlay with the validation result centered.
  /// Tap-outside dismisses; agent can then proceed to the next ticket.
  Widget _resultOverlay(bool isDark) {
    return Positioned.fill(
      child: GestureDetector(
        onTap: _reset,
        behavior: HitTestBehavior.opaque,
        child: Container(
          color: Colors.black.withValues(alpha: 0.72),
          alignment: Alignment.center,
          padding: const EdgeInsets.all(20),
          child: GestureDetector(
            onTap: () {}, // swallow taps on the card itself
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 360),
              child: Material(
                color: isDark ? const Color(0xFF161B22) : Colors.white,
                borderRadius: BorderRadius.circular(20),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
                  child: _buildResult(),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _cardTab(bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('Validacao pay-as-you-go',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        const SizedBox(height: 8),
        const Text(
          'Indique a rota actual. Quando o passageiro tocar o cartao, a tarifa sera descontada da carteira.',
          style: TextStyle(fontSize: 12, color: Color(0xFF6B6356)),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _routeCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            labelText: 'ID da rota',
            prefixIcon: Icon(Icons.route),
          ),
        ),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: BuzUpColors.orange.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
          ),
          child: Row(children: [
            const Icon(Icons.nfc, color: BuzUpColors.orange, size: 26),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                _checking
                    ? 'A processar...'
                    : _nfcArmed
                        ? 'Aproxime o cartao do passageiro.'
                        : 'Indique a rota para activar o leitor NFC.',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
              ),
            ),
            if (_checking) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
        ),
        const SizedBox(height: 14),
        // Result is rendered as a centered full-screen overlay by the parent
        // Scaffold (see `_resultOverlay`). No inline duplicate here.
      ]),
    );
  }

  // ---------- QR tab ----------

  Widget _qrTab() {
    return Column(children: [
      Expanded(
        flex: 3,
        child: Stack(children: [
          MobileScanner(controller: _controller, onDetect: _onDetect),
          Center(
            child: Container(
              width: 240, height: 240,
              decoration: BoxDecoration(
                border: Border.all(color: BuzUpColors.orange, width: 3),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          if (_checking) const Center(child: CircularProgressIndicator(color: BuzUpColors.orange)),
        ]),
      ),
      Expanded(
        flex: 2,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Center(child: Text(
            _checking ? 'A validar...' : 'Aponte o QR ao centro do enquadramento.',
            style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5),
            textAlign: TextAlign.center,
          )),
        ),
      ),
    ]);
  }

  // ---------- Shortcode tab ----------

  Widget _shortcodeTab(bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: BuzUpColors.orange.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
            ),
            child: const Row(children: [
              Icon(Icons.info_outline, color: BuzUpColors.orange, size: 18),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Para passageiros sem smartphone: pergunte os ultimos 4 caracteres da referencia do bilhete.',
                  style: TextStyle(fontSize: 12, height: 1.35),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 24),
          Text(
            'CODIGO DO BILHETE',
            style: TextStyle(
              fontSize: 11,
              letterSpacing: 1.6,
              color: isDark ? Colors.white60 : const Color(0xFF6B6356),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _shortcodeCtrl,
            autofocus: true,
            textAlign: TextAlign.center,
            textCapitalization: TextCapitalization.characters,
            maxLength: 4,
            style: const TextStyle(fontSize: 36, letterSpacing: 12, fontWeight: FontWeight.w800),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
              TextInputFormatter.withFunction((old, fresh) =>
                  fresh.copyWith(text: fresh.text.toUpperCase())),
            ],
            decoration: InputDecoration(
              counterText: '',
              hintText: 'A1B2',
              hintStyle: TextStyle(letterSpacing: 12, color: isDark ? Colors.white24 : Colors.black26),
              filled: true,
              fillColor: isDark ? const Color(0xFF1A1F26) : Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4)),
              ),
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 56,
            child: FilledButton.icon(
              icon: _checking
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.verified),
              label: Text(_checking ? 'A VERIFICAR...' : 'VERIFICAR BILHETE'),
              style: FilledButton.styleFrom(
                backgroundColor: BuzUpColors.orange,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.5),
              ),
              onPressed: _checking ? null : _verifyShortcode,
            ),
          ),
          const SizedBox(height: 18),
          // Result is shown by the centered overlay in the parent Scaffold.
        ],
      ),
    );
  }

  // ---------- Result ----------

  Widget _buildResult() {
    if (_error != null) {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.error_outline, color: BuzUpColors.danger, size: 56),
          const SizedBox(height: 8),
          Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: BuzUpColors.danger)),
          const SizedBox(height: 12),
          OutlinedButton.icon(icon: const Icon(Icons.refresh), label: const Text('Tentar de novo'), onPressed: _reset),
        ]),
      );
    }
    if (_last == null) {
      return const SizedBox.shrink();
    }
    final valid = _last!['valid'] == true;
    final consumed = _last!['consumed'] == true;
    final ticket = (_last!['ticket'] as Map?)?.cast<String, dynamic>() ?? const {};
    final reason = (_last!['reason'] as String?) ?? '';
    final candidates = (_last!['candidates'] as List?) ?? const [];

    if (candidates.isNotEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Icon(Icons.help_outline, color: Colors.amber, size: 48),
        const SizedBox(height: 6),
        Text(reason, textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        for (final c in candidates.cast<Map>())
          Card(
            child: ListTile(
              dense: true,
              title: Text('${c['route_code']} · ${c['origin_stop']} -> ${c['destination_stop']}'),
              subtitle: Text('Ref ${c['sale_reference'] ?? ''} · ${c['fare_amount']} MZN'),
              trailing: const Icon(Icons.touch_app, color: BuzUpColors.orange),
              onTap: () async {
                // Disambiguate by re-querying the shortcode derived from the
                // candidate's full sale reference. Backend re-checks status.
                final saleRef = c['sale_reference']?.toString() ?? '';
                if (saleRef.length < 4) return;
                setState(() {
                  _checking = true;
                  _last = null;
                  _error = null;
                });
                try {
                  final res = await ref
                      .read(agentApiProvider)
                      .verifyTicketByShortcode(saleRef.substring(saleRef.length - 4).toUpperCase());
                  await _handleResult(res);
                } on DioException catch (e) {
                  await _handleError(e);
                } finally {
                  if (mounted) setState(() => _checking = false);
                }
              },
            ),
          ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          icon: const Icon(Icons.refresh),
          label: const Text('Tentar outro codigo'),
          onPressed: _reset,
        ),
      ]);
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Icon(valid ? Icons.check_circle : Icons.cancel,
          color: valid ? BuzUpColors.success : BuzUpColors.danger, size: 56),
      const SizedBox(height: 4),
      Center(
        child: Text(
          valid
              ? (consumed ? 'BILHETE VALIDADO · EMBARQUE PERMITIDO' : 'BILHETE VALIDO')
              : 'BILHETE INVALIDO',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold,
              color: valid ? BuzUpColors.success : BuzUpColors.danger),
        ),
      ),
      if (!valid && reason.isNotEmpty)
        Center(child: Text(reason, style: const TextStyle(color: BuzUpColors.danger))),
      const SizedBox(height: 8),
      if (ticket.isNotEmpty) ...[
        Text('${ticket['route_code']} · ${ticket['origin_stop']} -> ${ticket['destination_stop']}',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        Text('${ticket['fare_amount']} MZN · ${ticket['payer_phone_masked'] ?? ''}'),
        if (ticket['used_at'] != null)
          Text('Usado em: ${ticket['used_at']}', style: const TextStyle(color: Colors.grey, fontSize: 11)),
      ],
      const SizedBox(height: 12),
      FilledButton.icon(
        icon: const Icon(Icons.refresh),
        label: const Text('VALIDAR PROXIMO'),
        onPressed: _reset,
      ),
    ]);
  }
}
