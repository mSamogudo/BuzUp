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

class PassengerOnboardScreen extends ConsumerStatefulWidget {
  const PassengerOnboardScreen({super.key});

  @override
  ConsumerState<PassengerOnboardScreen> createState() => _PassengerOnboardScreenState();
}

class _PassengerOnboardScreenState extends ConsumerState<PassengerOnboardScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _docNumberCtrl = TextEditingController();
  final _feeCtrl = TextEditingController(text: '50.00');
  final _payerCtrl = TextEditingController();
  String _docType = '';

  int _step = 0; // 0 = data, 1 = card, 2 = pay, 3 = success
  String? _cardUid;
  String? _qrToken;
  Map<String, dynamic>? _cardInfo;
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _docNumberCtrl.dispose();
    _feeCtrl.dispose();
    _payerCtrl.dispose();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _startNfcScan() async {
    setState(() {
      _error = null;
      _cardUid = null;
      _cardInfo = null;
    });
    try {
      await NfcCardReader.startStream((uid) async {
        await AppFeedback.softBeep();
        // Show preview from lookup so the agent sees if card is already used
        Map<String, dynamic>? card;
        try {
          final res = await ref.read(agentApiProvider).cardLookup(cardUid: uid);
          card = (res['card'] as Map?)?.cast<String, dynamic>();
        } on DioException {/* ignore lookup errors — backend re-validates */}
        if (!mounted) return;
        setState(() {
          _cardUid = uid;
          _cardInfo = card;
        });
      });
    } on NfcUnavailableException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final serial = await ref.read(secureStoreProvider).getDeviceSerial();
      final res = await ref.read(agentApiProvider).onboardPassenger(
            fullName: _nameCtrl.text.trim(),
            phone: _phoneCtrl.text.trim(),
            email: _emailCtrl.text.trim().isEmpty ? null : _emailCtrl.text.trim(),
            documentType: _docType.isEmpty ? null : _docType,
            documentNumber: _docNumberCtrl.text.trim().isEmpty ? null : _docNumberCtrl.text.trim(),
            cardUid: _cardUid,
            qrToken: _qrToken,
            payerPhone: _payerCtrl.text.trim(),
            fee: _feeCtrl.text.trim(),
            deviceSerial: serial,
          );
      await AppFeedback.success();
      await NfcCardReader.stop();
      setState(() {
        _result = res;
        _step = 3;
      });
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      setState(() => _error = e.toString());
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
        title: Text('Novo Passageiro', style: TextStyle(color: fg, fontWeight: FontWeight.w700)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: fg,
        iconTheme: IconThemeData(color: fg),
      ),
      body: SafeArea(
        child: _busy
            ? Center(child: BusLoader(label: 'A registar passageiro...'))
            : _step == 3 ? _successView() : _stepView(),
      ),
    );
  }

  Widget _stepView() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _stepIndicator(),
        const SizedBox(height: 12),
        Expanded(
          child: IndexedStack(
            index: _step,
            children: [
              _dataForm(),
              _cardStep(),
              _payStep(),
            ],
          ),
        ),
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger, fontSize: 12)),
        ),
        const SizedBox(height: 10),
        _bottomButtons(),
      ]),
    );
  }

  Widget _stepIndicator() {
    final labels = ['Dados', 'Cartao', 'Pagamento'];
    return Row(children: List.generate(3, (i) {
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
            child: Text('${i + 1}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(labels[i],
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 11.5,
                    color: active ? BuzUpColors.orange : Colors.grey)),
          ),
          if (i < 2)
            Container(width: 18, height: 1, color: done ? BuzUpColors.orange : Colors.grey.shade300),
        ]),
      );
    }));
  }

  Widget _dataForm() {
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        child: Column(children: [
          TextFormField(
            controller: _nameCtrl,
            decoration: const InputDecoration(labelText: 'Nome completo'),
            validator: (v) => (v?.trim().isEmpty ?? true) ? 'Obrigatorio' : null,
            textCapitalization: TextCapitalization.words,
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _phoneCtrl,
            decoration: const InputDecoration(labelText: 'Telefone (9 digitos)', prefixText: '+258 '),
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(9)],
            validator: (v) => !RegExp(r'^[0-9]{9}$').hasMatch(v?.trim() ?? '') ? '9 digitos' : null,
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _emailCtrl,
            decoration: const InputDecoration(labelText: 'Email (opcional)'),
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              flex: 2,
              child: DropdownButtonFormField<String>(
                value: _docType.isEmpty ? null : _docType,
                decoration: const InputDecoration(labelText: 'Documento'),
                items: const [
                  DropdownMenuItem(value: '', child: Text('-')),
                  DropdownMenuItem(value: 'bi', child: Text('B.I.')),
                  DropdownMenuItem(value: 'passport', child: Text('Passaporte')),
                  DropdownMenuItem(value: 'driving_license', child: Text('Carta')),
                ],
                onChanged: (v) => setState(() => _docType = v ?? ''),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              flex: 3,
              child: TextFormField(
                controller: _docNumberCtrl,
                decoration: const InputDecoration(labelText: 'Numero (opcional)'),
              ),
            ),
          ]),
        ]),
      ),
    );
  }

  Widget _cardStep() {
    final card = _cardInfo;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(_cardUid == null ? 'Aproxime o cartao do leitor' : 'Cartao lido',
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      if (_cardUid != null) Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE7E1D4)),
        ),
        child: Row(children: [
          const Icon(Icons.credit_card, color: BuzUpColors.orange, size: 32),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('UID', style: TextStyle(color: Colors.grey.shade700, fontSize: 10)),
              Text(_cardUid!, style: const TextStyle(fontWeight: FontWeight.w800, fontFamily: 'monospace')),
              if (card != null) Text(
                'Numero: ${card['card_number']} · Status: ${card['status']}',
                style: TextStyle(color: Colors.grey.shade700, fontSize: 11),
              ),
            ]),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      TextButton.icon(
        icon: const Icon(Icons.refresh),
        label: const Text('Ler outro cartao'),
        onPressed: _startNfcScan,
      ),
    ]);
  }

  Widget _payStep() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        TextField(
          controller: _feeCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
          decoration: const InputDecoration(labelText: 'Taxa do cartao', suffixText: 'MZN'),
        ),
        const SizedBox(height: 10),
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
                'Apos confirmar, o passageiro recebera um SMS com instrucoes de acesso e cartao digital paralelo.',
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
          onPressed: () {
            setState(() => _step--);
            if (_step == 1) _startNfcScan();
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
              if (_formKey.currentState?.validate() != true) return;
              setState(() => _step = 1);
              _startNfcScan();
            } else if (_step == 1) {
              if (_cardUid == null) {
                setState(() => _error = 'Aproxime o cartao do leitor antes de continuar.');
                return;
              }
              await NfcCardReader.stop();
              setState(() => _step = 2);
            } else if (_step == 2) {
              if (_payerCtrl.text.trim().length < 9) {
                setState(() => _error = 'Telefone do pagador invalido.');
                return;
              }
              await _submit();
            }
          },
          child: Text(_step == 2 ? 'COBRAR E CRIAR CONTA' : 'CONTINUAR',
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
    final userAcc = (r['user_account'] as Map?)?.cast<String, dynamic>() ?? const {};
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Icon(Icons.check_circle, color: BuzUpColors.success, size: 64),
        const SizedBox(height: 6),
        const Center(child: Text('PASSAGEIRO CRIADO',
            style: TextStyle(fontWeight: FontWeight.w800, color: BuzUpColors.success, fontSize: 16))),
        const SizedBox(height: 14),
        _detailRow('Nome', passenger['full_name']?.toString() ?? '-'),
        _detailRow('Telefone', passenger['phone_masked']?.toString() ?? '-'),
        _detailRow('Cartao', card['card_number']?.toString() ?? '-'),
        _detailRow('UID', card['card_uid']?.toString() ?? '-'),
        const Divider(),
        _detailRow('Taxa', '${payment['amount']} MZN'),
        _detailRow('Estado', payment['status']?.toString().toUpperCase() ?? '-'),
        _detailRow('Conta', userAcc['username']?.toString() ?? '-'),
        _detailRow('SMS', userAcc['sms_sent'] == true ? 'Enviado' : 'Nao enviado'),
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
          icon: const Icon(Icons.person_add_alt),
          label: const Text('NOVO PASSAGEIRO'),
          onPressed: () {
            setState(() {
              _step = 0;
              _result = null;
              _cardUid = null;
              _qrToken = null;
              _cardInfo = null;
              _nameCtrl.clear();
              _phoneCtrl.clear();
              _emailCtrl.clear();
              _docNumberCtrl.clear();
              _docType = '';
              _payerCtrl.clear();
              _error = null;
            });
          },
        ),
        TextButton(
          onPressed: () => context.go('/home'),
          child: const Text('Voltar ao inicio'),
        ),
      ]),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(width: 90, child: Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12))),
        Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w700))),
      ]),
    );
  }
}
