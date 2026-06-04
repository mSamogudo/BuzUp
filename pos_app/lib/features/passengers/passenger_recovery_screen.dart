import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/feedback.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class PassengerRecoveryScreen extends ConsumerStatefulWidget {
  const PassengerRecoveryScreen({super.key});

  @override
  ConsumerState<PassengerRecoveryScreen> createState() => _PassengerRecoveryScreenState();
}

class _PassengerRecoveryScreenState extends ConsumerState<PassengerRecoveryScreen> {
  int _step = 0; // 0 phone+reason, 1 OTP, 2 scan card, 3 pay, 4 success
  final _phoneCtrl = TextEditingController();
  final _reasonCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  final _payerCtrl = TextEditingController();
  String? _challengeId;
  String? _phoneMasked;
  String? _recoveryToken;
  Map<String, dynamic>? _passenger;
  List<dynamic> _existingCards = const [];
  String? _newCardUid;
  Map<String, dynamic>? _newCardInfo;
  Map<String, dynamic>? _result;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _reasonCtrl.dispose();
    _otpCtrl.dispose();
    _payerCtrl.dispose();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _requestOtp() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(agentApiProvider).recoverCardRequestOtp(
            passengerPhone: _phoneCtrl.text.trim(),
            reason: _reasonCtrl.text.trim(),
          );
      setState(() {
        _challengeId = res['challenge_id'] as String?;
        _phoneMasked = res['phone_masked'] as String?;
        _step = 1;
      });
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verifyOtp() async {
    if (_challengeId == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(agentApiProvider).recoverCardVerifyOtp(
            challengeId: _challengeId!,
            otpCode: _otpCtrl.text.trim(),
          );
      setState(() {
        _recoveryToken = res['recovery_token'] as String?;
        _passenger = (res['passenger'] as Map?)?.cast<String, dynamic>();
        _existingCards = (res['existing_physical_cards'] as List?) ?? const [];
        _step = 2;
      });
      _startCardScan();
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _startCardScan() async {
    setState(() {
      _newCardUid = null;
      _newCardInfo = null;
    });
    try {
      await NfcCardReader.startStream((uid) async {
        await AppFeedback.softBeep();
        Map<String, dynamic>? card;
        try {
          final res = await ref.read(agentApiProvider).cardLookup(cardUid: uid);
          card = (res['card'] as Map?)?.cast<String, dynamic>();
        } on DioException {/* ignore — backend re-validates */}
        if (!mounted) return;
        setState(() {
          _newCardUid = uid;
          _newCardInfo = card;
        });
      });
    } on NfcUnavailableException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  bool get _cardEligible {
    final c = _newCardInfo;
    if (c == null) return _newCardUid != null; // we'll let backend judge
    final status = (c['status'] as String?)?.toLowerCase() ?? '';
    final hasPassenger = c['passenger_name']?.toString().isNotEmpty == true;
    return status == 'inactive' && !hasPassenger;
  }

  Future<void> _associate() async {
    if (_recoveryToken == null || _newCardUid == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await NfcCardReader.stop();
      final res = await ref.read(agentApiProvider).recoverCardAssociate(
            recoveryToken: _recoveryToken!,
            newCardUid: _newCardUid,
            payerPhone: _payerCtrl.text.trim(),
          );
      await AppFeedback.success();
      setState(() {
        _result = res;
        _step = 4;
      });
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
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
        title: Text('Recuperar Cartao',
            style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
      ),
      body: SafeArea(
        child: _busy
            ? Center(child: BusLoader(label: 'A processar...'))
            : _step == 4
                ? _successView()
                : Padding(
                    padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      _stepIndicator(),
                      const SizedBox(height: 12),
                      Expanded(
                        child: IndexedStack(index: _step, children: [
                          _phoneStep(),
                          _otpStep(),
                          _cardScanStep(),
                          _payStep(),
                        ]),
                      ),
                      if (_error != null) Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger, fontSize: 12)),
                      ),
                      const SizedBox(height: 10),
                      _bottomButtons(),
                    ]),
                  ),
      ),
    );
  }

  Widget _stepIndicator() {
    const labels = ['Identificar', 'OTP', 'Cartao', 'Pagamento'];
    return Row(children: List.generate(4, (i) {
      final active = i == _step;
      final done = i < _step;
      return Expanded(
        child: Row(children: [
          Container(
            width: 22, height: 22,
            decoration: BoxDecoration(
              color: done || active ? BuzUpColors.orange : Colors.grey.shade400,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text('${i + 1}',
                style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Text(labels[i],
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 11,
                    color: active ? BuzUpColors.orange : Colors.grey)),
          ),
          if (i < 3) Container(width: 12, height: 1, color: done ? BuzUpColors.orange : Colors.grey.shade300),
        ]),
      );
    }));
  }

  Widget _phoneStep() {
    return SingleChildScrollView(
      child: Column(children: [
        TextField(
          controller: _phoneCtrl,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(9)],
          decoration: const InputDecoration(
            labelText: 'Telefone do passageiro (9 digitos)',
            prefixText: '+258 ',
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _reasonCtrl,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Motivo (opcional)',
            hintText: 'Ex.: cartao roubado / perdido',
          ),
        ),
      ]),
    );
  }

  Widget _otpStep() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(
          'OTP enviado a ${_phoneMasked ?? "passageiro"}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        const Text('Peca o codigo de 6 digitos e introduza abaixo.',
            style: TextStyle(fontSize: 12, color: Color(0xFF6B6356))),
        const SizedBox(height: 16),
        SizedBox(
          width: 200,
          child: TextField(
            controller: _otpCtrl,
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 28, letterSpacing: 6, fontWeight: FontWeight.w800),
            decoration: const InputDecoration(hintText: '------'),
          ),
        ),
      ]),
    );
  }

  Widget _cardScanStep() {
    final p = _passenger;
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (p != null) Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.green.shade50,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.green.shade200),
          ),
          child: Row(children: [
            const Icon(Icons.verified_user, color: Colors.green),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(p['full_name']?.toString() ?? '-',
                    style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('Tel ${p['phone_masked']}',
                    style: const TextStyle(fontSize: 11, color: Color(0xFF6B6356))),
              ]),
            ),
          ]),
        ),
        const SizedBox(height: 10),
        const Text('Aproxime um cartao fisico NOVO ao leitor.',
            style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        if (_newCardUid != null) Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: _cardEligible ? Colors.green : BuzUpColors.danger, width: 2),
          ),
          child: Row(children: [
            Icon(_cardEligible ? Icons.check_circle : Icons.error_outline,
                color: _cardEligible ? Colors.green : BuzUpColors.danger),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(_newCardInfo?['card_number']?.toString() ?? _newCardUid!,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontFamily: 'monospace')),
                Text(
                  _cardEligible
                      ? 'Cartao disponivel para associacao.'
                      : 'Cartao nao pode ser usado (${_newCardInfo?['status'] ?? 'verificar status'})',
                  style: TextStyle(fontSize: 11,
                      color: _cardEligible ? Colors.green.shade800 : BuzUpColors.danger),
                ),
              ]),
            ),
          ]),
        ),
        if (_existingCards.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('CARTOES EXISTENTES (${_existingCards.length})',
              style: const TextStyle(fontSize: 10, letterSpacing: 1.2,
                  color: Color(0xFF6B6356), fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          for (final c in _existingCards.cast<Map>())
            Container(
              margin: const EdgeInsets.only(bottom: 4),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(children: [
                Expanded(child: Text('${c['card_number']}',
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12))),
                Text('${c['status']}',
                    style: TextStyle(fontSize: 10, color: Colors.grey.shade700)),
              ]),
            ),
          const SizedBox(height: 4),
          const Text('Os cartoes acima serao marcados como PERDIDO apos a associacao.',
              style: TextStyle(fontSize: 11, color: Color(0xFF6B6356))),
        ],
      ]),
    );
  }

  Widget _payStep() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        TextField(
          controller: _payerCtrl,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(12)],
          decoration: const InputDecoration(
            labelText: 'Telefone do pagador (M-Pesa / E-Mola)',
            prefixIcon: Icon(Icons.phone_iphone),
          ),
        ),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: BuzUpColors.orange.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
          ),
          child: Row(children: [
            const Icon(Icons.info_outline, color: BuzUpColors.orange, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'A taxa de recuperacao sera cobrada via M-Pesa ou E-Mola. O passageiro recebera um pedido no telefone para introduzir o PIN.',
                style: TextStyle(color: Colors.grey.shade800, fontSize: 11.5, height: 1.35),
              ),
            ),
          ]),
        ),
      ]),
    );
  }

  Widget _bottomButtons() {
    return Row(children: [
      if (_step > 0) Expanded(
        child: OutlinedButton(
          onPressed: () async {
            await NfcCardReader.stop();
            setState(() => _step--);
            if (_step == 2) _startCardScan();
          },
          child: const Text('VOLTAR'),
        ),
      ),
      if (_step > 0) const SizedBox(width: 8),
      Expanded(
        flex: 2,
        child: FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: BuzUpColors.orange, minimumSize: const Size.fromHeight(48),
          ),
          onPressed: () async {
            if (_step == 0) {
              if (_phoneCtrl.text.trim().length != 9) {
                setState(() => _error = 'Telefone deve ter 9 digitos.');
                return;
              }
              await _requestOtp();
            } else if (_step == 1) {
              if (_otpCtrl.text.trim().length < 4) {
                setState(() => _error = 'Introduza o codigo OTP.');
                return;
              }
              await _verifyOtp();
            } else if (_step == 2) {
              if (_newCardUid == null) {
                setState(() => _error = 'Aproxime um cartao novo do leitor.');
                return;
              }
              if (!_cardEligible) {
                setState(() => _error = 'Cartao nao elegivel. Use um cartao inactivo sem dono.');
                return;
              }
              await NfcCardReader.stop();
              setState(() => _step = 3);
            } else if (_step == 3) {
              if (_payerCtrl.text.trim().length < 9) {
                setState(() => _error = 'Telefone do pagador invalido.');
                return;
              }
              await _associate();
            }
          },
          child: Text(_step == 3 ? 'COBRAR E ASSOCIAR' : 'CONTINUAR',
              style: const TextStyle(fontWeight: FontWeight.w800)),
        ),
      ),
    ]);
  }

  Widget _successView() {
    final r = _result ?? const {};
    final passenger = (r['passenger'] as Map?)?.cast<String, dynamic>() ?? const {};
    final card = (r['card'] as Map?)?.cast<String, dynamic>() ?? const {};
    final payment = (r['payment'] as Map?)?.cast<String, dynamic>() ?? const {};
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Icon(Icons.check_circle, color: BuzUpColors.success, size: 64),
        const SizedBox(height: 6),
        const Center(child: Text('CARTAO RECUPERADO',
            style: TextStyle(fontWeight: FontWeight.w800, color: BuzUpColors.success, fontSize: 16))),
        const SizedBox(height: 14),
        _detail('Passageiro', passenger['full_name']?.toString() ?? '-'),
        _detail('Telefone', passenger['phone_masked']?.toString() ?? '-'),
        _detail('Cartao novo', card['card_number']?.toString() ?? '-'),
        _detail('UID', card['card_uid']?.toString() ?? '-'),
        _detail('Cartoes a bloquear',
            '${(r['old_card_ids'] as List?)?.length ?? 0}'),
        _detail('Bloqueados agora',
            '${r['blocked_now'] ?? 0}${(payment['status'] == 'pending') ? ' (apos confirmacao)' : ''}'),
        const Divider(),
        _detail('Taxa', '${payment['amount']} MZN'),
        _detail('Pagamento', (payment['status']?.toString() ?? '-').toUpperCase()),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: BuzUpColors.success.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: BuzUpColors.success.withValues(alpha: 0.4)),
          ),
          child: const Row(children: [
            Icon(Icons.sms, color: BuzUpColors.success),
            SizedBox(width: 10),
            Expanded(child: Text(
              'Comprovativo enviado por SMS ao passageiro.',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5),
            )),
          ]),
        ),
        const SizedBox(height: 10),
        FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: BuzUpColors.orange, minimumSize: const Size.fromHeight(50)),
          icon: const Icon(Icons.home),
          label: const Text('VOLTAR AO INICIO'),
          onPressed: () => context.go('/home'),
        ),
      ]),
    );
  }

  Widget _detail(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(width: 110, child: Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12))),
        Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w700))),
      ]),
    );
  }
}
