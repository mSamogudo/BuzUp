import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class TopupScreen extends ConsumerStatefulWidget {
  const TopupScreen({super.key});

  @override
  ConsumerState<TopupScreen> createState() => _TopupScreenState();
}

class _TopupScreenState extends ConsumerState<TopupScreen> {
  final _amountCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;
  Timer? _poller;
  int _pollSeconds = 0;

  // Quick-pick amounts so the user can tap instead of typing.
  static const _quickAmounts = [50, 100, 200, 500, 1000];

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      final phone = await ref.read(secureStoreProvider).getPhone();
      if (mounted && phone != null) {
        _phoneCtrl.text = phone;
      }
    });
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    _phoneCtrl.dispose();
    _poller?.cancel();
    super.dispose();
  }

  /// While the PaymentIntent is pending, poll its status every 4 seconds for
  /// up to 3 minutes. As soon as it flips to confirmed the UI swaps to the
  /// success screen automatically and the wallet provider is invalidated.
  void _startPolling(String reference) {
    _poller?.cancel();
    _pollSeconds = 0;
    _poller = Timer.periodic(const Duration(seconds: 4), (timer) async {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() => _pollSeconds += 4);
      if (_pollSeconds > 180) {
        // Stop polling after 3 minutes; the user can leave and the webhook
        // will still confirm in the background.
        timer.cancel();
        return;
      }
      try {
        final res = await ref.read(passengerApiProvider).paymentStatus(reference);
        final status = res['status']?.toString();
        if (status == 'confirmed' || status == 'failed') {
          timer.cancel();
          if (mounted) {
            setState(() => _result = res);
            ref.invalidate(meProvider);
          }
        }
      } catch (_) {/* keep polling silently */}
    });
  }

  bool get _canSubmit {
    final amt = double.tryParse(_amountCtrl.text.trim());
    final phone = _phoneCtrl.text.trim();
    return amt != null && amt > 0 && phone.length >= 9;
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final res = await ref.read(passengerApiProvider).topup(
            amount: _amountCtrl.text.trim(),
            payerPhone: _phoneCtrl.text.trim(),
          );
      setState(() => _result = res);
      // Refresh wallet so the home screen reflects the new balance on return.
      ref.invalidate(meProvider);
      // If the gateway came back pending, start polling so the screen flips
      // to "confirmed" automatically once the webhook arrives.
      final status = res['status']?.toString();
      final ref0 = res['reference']?.toString();
      if (status == 'pending' && ref0 != null && ref0.isNotEmpty) {
        _startPolling(ref0);
      }
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Recarregar', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: SafeArea(
        child: _result != null ? _success() : _form(),
      ),
    );
  }

  Widget _form() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      children: [
        const Text('Valor a recarregar',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: BuzUpColors.muted)),
        const SizedBox(height: 8),
        TextField(
          controller: _amountCtrl,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
          style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
          decoration: const InputDecoration(
            hintText: '0.00',
            suffixText: 'MZN',
            suffixStyle: TextStyle(fontWeight: FontWeight.w700, color: BuzUpColors.muted),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final amt in _quickAmounts)
            GestureDetector(
              onTap: () {
                _amountCtrl.text = amt.toString();
                setState(() {});
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: BuzUpColors.orange.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
                ),
                child: Text('$amt MZN',
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 12.5, color: BuzUpColors.orange)),
              ),
            ),
        ]),
        const SizedBox(height: 24),
        const Text('Telefone do pagador (M-Pesa / E-Mola)',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: BuzUpColors.muted)),
        const SizedBox(height: 8),
        TextField(
          controller: _phoneCtrl,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(12)],
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, letterSpacing: 0.5),
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.phone_iphone),
            hintText: '258XXXXXXXXX',
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 20),
        if (_error != null)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 14),
            decoration: BoxDecoration(
              color: BuzUpColors.danger.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: BuzUpColors.danger.withValues(alpha: 0.30)),
            ),
            child: Row(children: [
              const Icon(Icons.error_outline, color: BuzUpColors.danger),
              const SizedBox(width: 8),
              Expanded(child: Text(_error!,
                  style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5))),
            ]),
          ),
        FilledButton(
          onPressed: (_busy || !_canSubmit) ? null : _submit,
          child: _busy
              ? const SizedBox(width: 22, height: 22,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Text('SOLICITAR PAGAMENTO'),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: BuzUpColors.navy.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Row(children: [
            Icon(Icons.info_outline, color: BuzUpColors.muted, size: 18),
            SizedBox(width: 8),
            Expanded(child: Text(
              'Vai receber um pedido no telefone para confirmar o pagamento com o seu PIN M-Pesa ou E-Mola.',
              style: TextStyle(fontSize: 11.5, color: BuzUpColors.muted, height: 1.4),
            )),
          ]),
        ),
      ],
    );
  }

  Widget _success() {
    final r = _result ?? const {};
    final status = (r['payment'] as Map?)?['status']?.toString() ?? r['status']?.toString() ?? 'pending';
    final isConfirmed = status == 'confirmed';
    final isFailed = status == 'failed';
    final isPolling = _poller?.isActive == true;

    final color = isConfirmed
        ? BuzUpColors.success
        : isFailed
            ? BuzUpColors.danger
            : BuzUpColors.orange;
    final icon = isConfirmed
        ? Icons.check_circle
        : isFailed
            ? Icons.cancel
            : Icons.hourglass_top;
    final title = isConfirmed
        ? 'PAGAMENTO CONFIRMADO'
        : isFailed
            ? 'PAGAMENTO RECUSADO'
            : 'PEDIDO ENVIADO';
    final subtitle = isConfirmed
        ? 'O saldo foi adicionado a sua carteira.'
        : isFailed
            ? 'O pagamento foi recusado pela operadora. Tente novamente.'
            : 'Verifique o seu telefone para confirmar com o PIN.';

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(children: [
        const Spacer(),
        Icon(icon, color: color, size: 96),
        const SizedBox(height: 16),
        Text(title,
            style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.w800),
            textAlign: TextAlign.center),
        const SizedBox(height: 8),
        Text(subtitle,
            style: const TextStyle(color: BuzUpColors.muted, fontSize: 13),
            textAlign: TextAlign.center),
        const SizedBox(height: 16),
        if (isPolling) Column(children: [
          const SizedBox(
            width: 22, height: 22,
            child: CircularProgressIndicator(color: BuzUpColors.orange, strokeWidth: 2),
          ),
          const SizedBox(height: 8),
          Text('A verificar... ($_pollSeconds s)',
              style: const TextStyle(fontSize: 12, color: BuzUpColors.muted)),
        ]),
        const SizedBox(height: 12),
        if (r['reference'] != null) Text('Ref: ${r['reference']}',
            style: const TextStyle(fontSize: 11, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        const Spacer(),
        if (!isConfirmed && !isFailed)
          TextButton.icon(
            onPressed: () async {
              final ref0 = r['reference']?.toString();
              if (ref0 == null) return;
              try {
                final st = await ref.read(passengerApiProvider).paymentStatus(ref0);
                if (mounted) {
                  setState(() => _result = st);
                  ref.invalidate(meProvider);
                }
              } catch (_) {}
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Verificar agora'),
          ),
        const SizedBox(height: 4),
        FilledButton.icon(
          onPressed: () => context.pop(),
          icon: const Icon(Icons.home),
          label: const Text('VOLTAR'),
        ),
      ]),
    );
  }
}
