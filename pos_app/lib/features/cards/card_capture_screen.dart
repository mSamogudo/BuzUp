import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class _CapturedCard {
  final String uid;
  final String? cardNumber;
  final bool created;
  final String status;
  _CapturedCard({required this.uid, required this.created, required this.status, this.cardNumber});
}

/// Continuous NFC capture mode: agent taps each new card and it's immediately
/// registered on the backend (status=inactive) so it appears on the portal.
class CardCaptureScreen extends ConsumerStatefulWidget {
  const CardCaptureScreen({super.key});

  @override
  ConsumerState<CardCaptureScreen> createState() => _CardCaptureScreenState();
}

class _CardCaptureScreenState extends ConsumerState<CardCaptureScreen> {
  final _batchCtrl = TextEditingController();
  final List<_CapturedCard> _captured = [];
  bool _waiting = false;
  String? _error;
  String? _hint;
  bool _autoLoop = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startStream());
  }

  @override
  void dispose() {
    _batchCtrl.dispose();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _startStream() async {
    if (!mounted) return;
    setState(() {
      _error = null;
      _hint = 'Aproxime o cartao do leitor...';
    });
    try {
      await NfcCardReader.startStream(_onCard);
    } on NfcUnavailableException catch (e) {
      await AppFeedback.error();
      if (mounted) setState(() => _error = e.message);
      _autoLoop = false;
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _onCard(String uid) async {
    if (!mounted) return;
    setState(() {
      _waiting = true;
      _hint = 'A registar...';
    });
    try {
      if (_captured.any((c) => c.uid == uid)) {
        setState(() => _hint = 'Cartao $uid ja lido nesta sessao.');
        await AppFeedback.softBeep();
        return;
      }
      final res = await ref.read(agentApiProvider).captureCardUid(
            cardUid: uid,
            batch: _batchCtrl.text.trim(),
          );
      final created = res['created'] == true;
      await AppFeedback.softBeep();
      if (!mounted) return;
      setState(() {
        _captured.insert(0, _CapturedCard(
          uid: uid,
          cardNumber: res['card_number'] as String?,
          created: created,
          status: (res['status'] as String?) ?? 'inactive',
        ));
        _hint = created ? 'Registado no portal.' : 'Cartao ja existia no portal.';
      });
    } on DioException catch (e) {
      await AppFeedback.error();
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _waiting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    final muted = isDark ? Colors.white60 : const Color(0xFF6B6356);
    final cardBg = isDark ? const Color(0xFF1A1F26) : Colors.white;
    final border = isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4);
    final createdCount = _captured.where((c) => c.created).length;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0E1216) : const Color(0xFFF7F4EE),
      appBar: AppBar(
        title: Text('Capturar UID', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0),
            child: Center(
              child: Row(children: [
                const Icon(Icons.loop, size: 18),
                const SizedBox(width: 4),
                Switch(
                  value: _autoLoop,
                  activeColor: BuzUpColors.orange,
                  onChanged: (v) async {
                    setState(() => _autoLoop = v);
                    if (v) {
                      await _startStream();
                    } else {
                      await NfcCardReader.stop();
                    }
                  },
                ),
              ]),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            // Batch input
            TextField(
              controller: _batchCtrl,
              decoration: InputDecoration(
                labelText: 'Lote (opcional)',
                hintText: 'Ex.: LOT-2026-001',
                filled: true,
                fillColor: cardBg,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: border),
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Status hero
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFFF6B00), Color(0xFFFF8C2E)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [BoxShadow(color: BuzUpColors.orange.withValues(alpha: 0.30), blurRadius: 16, offset: const Offset(0, 6))],
              ),
              child: Row(children: [
                Container(
                  width: 56, height: 56,
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(14)),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: _waiting
                        ? const SizedBox(
                            width: 24, height: 24,
                            child: CircularProgressIndicator(strokeWidth: 3, color: Colors.white),
                          )
                        : const Icon(Icons.nfc, color: Colors.white, size: 28),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_hint ?? 'Pronto para ler', style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text('${_captured.length} lidos | $createdCount novos no portal',
                        style: const TextStyle(color: Colors.white70, fontSize: 11.5)),
                  ]),
                ),
              ]),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: BuzUpColors.danger.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: BuzUpColors.danger.withValues(alpha: 0.30)),
                ),
                child: Row(children: [
                  const Icon(Icons.error_outline, color: BuzUpColors.danger),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger))),
                ]),
              ),
            ],
            const SizedBox(height: 12),
            // Manual read button (when auto-loop off)
            if (!_autoLoop)
              SizedBox(
                height: 50,
                child: FilledButton.icon(
                  icon: const Icon(Icons.touch_app),
                  label: const Text('REINICIAR LEITOR'),
                  style: FilledButton.styleFrom(
                    backgroundColor: BuzUpColors.orange,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.4),
                  ),
                  onPressed: _startStream,
                ),
              ),
            const SizedBox(height: 12),
            Text('CARTOES NESTA SESSAO',
                style: TextStyle(fontSize: 11, letterSpacing: 1.4, color: muted, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Expanded(
              child: _captured.isEmpty
                  ? Container(
                      decoration: BoxDecoration(
                        color: cardBg,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: border),
                      ),
                      child: Center(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Text('Toque um cartao no leitor para comecar.',
                              style: TextStyle(color: muted), textAlign: TextAlign.center),
                        ),
                      ),
                    )
                  : Container(
                      decoration: BoxDecoration(
                        color: cardBg,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: border),
                      ),
                      child: ListView.separated(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        itemCount: _captured.length,
                        separatorBuilder: (_, __) => Divider(height: 1, color: border),
                        itemBuilder: (_, i) {
                          final c = _captured[i];
                          return ListTile(
                            dense: true,
                            visualDensity: const VisualDensity(horizontal: -1, vertical: -1),
                            leading: CircleAvatar(
                              radius: 14,
                              backgroundColor: c.created
                                  ? BuzUpColors.success.withValues(alpha: 0.18)
                                  : Colors.amber.withValues(alpha: 0.18),
                              child: Icon(c.created ? Icons.fiber_new : Icons.replay,
                                  size: 14,
                                  color: c.created ? BuzUpColors.success : Colors.amber.shade700),
                            ),
                            title: Text(c.uid,
                                style: TextStyle(fontFamily: 'monospace', color: fg, fontSize: 13, fontWeight: FontWeight.w700)),
                            subtitle: Text(c.cardNumber ?? '-',
                                style: TextStyle(color: muted, fontSize: 11)),
                            trailing: Text(c.created ? 'NOVO' : 'EXISTIA',
                                style: TextStyle(
                                  color: c.created ? BuzUpColors.success : Colors.amber.shade700,
                                  fontSize: 10, fontWeight: FontWeight.w800,
                                )),
                          );
                        },
                      ),
                    ),
            ),
          ]),
        ),
      ),
    );
  }
}
