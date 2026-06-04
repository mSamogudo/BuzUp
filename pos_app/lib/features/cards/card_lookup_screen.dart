import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import 'card_actions_screen.dart';

class CardLookupScreen extends ConsumerStatefulWidget {
  const CardLookupScreen({super.key});

  @override
  ConsumerState<CardLookupScreen> createState() => _CardLookupScreenState();
}

class _CardLookupScreenState extends ConsumerState<CardLookupScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  final _scanner = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  bool _busy = false;
  bool _torch = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    // Start NFC polling automatically when the user opens the screen on NFC tab.
    _tabs.addListener(() {
      if (_tabs.index == 0) {
        _startNfc();
      } else {
        NfcCardReader.stop();
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _startNfc());
  }

  @override
  void dispose() {
    _tabs.dispose();
    _scanner.dispose();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _startNfc() async {
    if (!mounted) return;
    setState(() {
      _error = null;
    });
    try {
      await NfcCardReader.startStream((uid) async {
        await AppFeedback.softBeep();
        await _lookup(cardUid: uid);
      });
    } on NfcUnavailableException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _onQr(BarcodeCapture capture) async {
    if (_busy) return;
    final raw = capture.barcodes.first.rawValue;
    if (raw == null || raw.isEmpty) return;
    await _lookup(qrToken: raw);
  }

  Future<void> _lookup({String? cardUid, String? qrToken}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(agentApiProvider).cardLookup(cardUid: cardUid, qrToken: qrToken);
      final card = (res['card'] as Map?)?.cast<String, dynamic>();
      if (card == null) {
        await AppFeedback.error();
        setState(() => _error = 'Cartao nao encontrado.');
        return;
      }
      await AppFeedback.softBeep();
      if (mounted) {
        await NfcCardReader.stop();
        await Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => CardActionsScreen(card: card, cardUid: cardUid, qrToken: qrToken)),
        );
        // re-arm reader after returning
        if (mounted) _startNfc();
      }
    } on DioException catch (e) {
      await AppFeedback.error();
      final body = e.response?.data;
      String msg = ApiClient.extractError(e);
      if (body is Map && body['detail'] is String) msg = body['detail'];
      setState(() => _error = msg);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0E1216) : const Color(0xFFF7F4EE),
      appBar: AppBar(
        title: Text('Cartao do Passageiro', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
        actionsIconTheme: IconThemeData(color: fg),
        elevation: 0,
        actions: [
          Consumer(builder: (ctx, ref, _) {
            final features = ref.watch(agentFeaturesProvider).maybeWhen(
                  data: (m) => m,
                  orElse: () => const <String, bool>{},
                );
            if (features['card_capture'] != true) return const SizedBox.shrink();
            return IconButton(
              tooltip: 'Capturar UID de novos cartoes',
              icon: Icon(Icons.add_card, color: fg),
              onPressed: () async {
                await NfcCardReader.stop();
                if (!mounted) return;
                await context.push('/cards/capture');
                if (mounted && _tabs.index == 0) _startNfc();
              },
            );
          }),
        ],
        bottom: TabBar(
          controller: _tabs,
          labelColor: BuzUpColors.orange,
          indicatorColor: BuzUpColors.orange,
          unselectedLabelColor: isDark ? Colors.white60 : const Color(0xFF6B6356),
          tabs: const [
            Tab(icon: Icon(Icons.nfc), text: 'NFC'),
            Tab(icon: Icon(Icons.qr_code_scanner), text: 'QR'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _nfcTab(isDark, fg),
          _qrTab(),
        ],
      ),
    );
  }

  Widget _nfcTab(bool isDark, Color fg) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 180, height: 180,
              decoration: BoxDecoration(
                color: BuzUpColors.orange.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30), width: 2),
              ),
              child: const Icon(Icons.nfc, size: 96, color: BuzUpColors.orange),
            ),
            const SizedBox(height: 24),
            Text(
              _busy ? 'Aproxime o cartao do leitor...' : 'Toque novamente para ler',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: fg),
            ),
            const SizedBox(height: 8),
            Text(
              'Coloque o cartao fisico sobre a area NFC do POS.',
              textAlign: TextAlign.center,
              style: TextStyle(color: isDark ? Colors.white54 : const Color(0xFF8C8475)),
            ),
            const SizedBox(height: 24),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(_error!, textAlign: TextAlign.center,
                    style: const TextStyle(color: BuzUpColors.danger)),
              ),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                icon: const Icon(Icons.refresh),
                label: const Text('REINICIAR LEITURA NFC'),
                style: FilledButton.styleFrom(
                  backgroundColor: BuzUpColors.orange,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.4),
                ),
                onPressed: _busy ? null : _startNfc,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _qrTab() {
    return Column(children: [
      Expanded(
        flex: 3,
        child: Stack(children: [
          MobileScanner(controller: _scanner, onDetect: _onQr),
          Center(
            child: Container(
              width: 240, height: 240,
              decoration: BoxDecoration(
                border: Border.all(color: BuzUpColors.orange, width: 3),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          if (_busy) const Center(child: CircularProgressIndicator(color: BuzUpColors.orange)),
          Positioned(
            right: 12, top: 12,
            child: IconButton(
              icon: Icon(_torch ? Icons.flash_on : Icons.flash_off, color: Colors.white),
              onPressed: () async {
                await _scanner.toggleTorch();
                setState(() => _torch = !_torch);
              },
            ),
          ),
        ]),
      ),
      Expanded(
        flex: 1,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('Aponte para o QR do cartao digital.',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, textAlign: TextAlign.center,
                    style: const TextStyle(color: BuzUpColors.danger)),
              ],
            ],
          ),
        ),
      ),
    ]);
  }
}
