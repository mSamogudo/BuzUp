import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/i18n.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

/// Three-step passenger onboarding:
///   0 = phone entry  ->  checks if an account exists
///   1 = registration (new passengers only: name + optional email)
///   2 = OTP code     ->  verifies and logs in (creates the account when new)
class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phoneCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();

  String? _challengeId;
  String? _phoneE164; // 258XXXXXXXXX format kept for verify call
  String? _phoneMasked;
  bool _busy = false;
  String? _error;
  int _step = 0; // 0 = phone, 1 = register, 2 = OTP
  bool _isNewUser = false; // drives whether we send name/email on verify
  int _resendSeconds = 0;

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _otpCtrl.dispose();
    super.dispose();
  }

  bool _phoneValid(String phone) =>
      RegExp(r'^[0-9]{9}$').hasMatch(phone) && '89'.contains(phone[0]);

  /// Step 0 -> decide between login (account exists) and registration (new).
  Future<void> _continueFromPhone() async {
    final tr = ref.read(trProvider);
    final phone = _phoneCtrl.text.trim();
    if (!_phoneValid(phone)) {
      setState(() => _error = tr('login.phoneError'));
      return;
    }
    final phoneE164 = '258$phone';
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      Log.info('passenger/check phone=$phoneE164');
      final check = await ref.read(passengerApiProvider).checkPhone(phoneE164);
      final exists = check['exists'] == true;
      _phoneE164 = phoneE164;
      _phoneMasked = '***${phone.substring(5)}';
      if (exists) {
        // Returning user: send the OTP straight away and go to the code step.
        await _requestOtp(isNew: false);
      } else {
        // Brand-new passenger: collect name (and optional email) first.
        setState(() {
          _isNewUser = true;
          _step = 1;
        });
      }
    } on DioException catch (e) {
      Log.warn('passenger/check failed', error: e.message);
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Step 1 -> validate the registration form, then request the OTP.
  Future<void> _submitRegistration() async {
    final tr = ref.read(trProvider);
    if (_nameCtrl.text.trim().length < 3) {
      setState(() => _error = tr('login.nameError'));
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _requestOtp(isNew: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Sends the SMS code and advances to the OTP step. Shared by both paths.
  Future<void> _requestOtp({required bool isNew}) async {
    final phoneE164 = _phoneE164;
    if (phoneE164 == null) return;
    Log.info('otp/request phone=$phoneE164');
    try {
      final res = await ref.read(passengerApiProvider).requestOtp(phoneE164);
      Log.info('otp/request ok', data: 'challenge=${res['challenge_id']}');
      await ref.read(secureStoreProvider).savePhone(phoneE164);
      if (!mounted) return;
      setState(() {
        _challengeId = res['challenge_id'] as String?;
        _isNewUser = isNew;
        _step = 2;
        _resendSeconds = 60;
      });
      _tickResend();
    } on DioException catch (e) {
      Log.warn('otp/request failed', error: e.message);
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    }
  }

  Future<void> _resendOtp() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _requestOtp(isNew: _isNewUser);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _changePhone() {
    setState(() {
      _step = 0;
      _isNewUser = false;
      _challengeId = null;
      _resendSeconds = 0;
      _error = null;
    });
    _otpCtrl.clear();
  }

  void _tickResend() async {
    while (_resendSeconds > 0 && mounted) {
      await Future<void>.delayed(const Duration(seconds: 1));
      if (mounted) setState(() => _resendSeconds--);
    }
  }

  /// Step 2 -> verify the code; the backend creates the account when new.
  Future<void> _verifyOtp() async {
    final tr = ref.read(trProvider);
    final code = _otpCtrl.text.trim();
    if (code.length != 6 || _challengeId == null || _phoneE164 == null) {
      setState(() => _error = tr('login.otpError'));
      return;
    }
    Log.info('otp/verify challenge=$_challengeId new=$_isNewUser');
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(passengerApiProvider).verifyOtp(
            challengeId: _challengeId!,
            code: code,
            phone: _phoneE164!,
            fullName: _isNewUser ? _nameCtrl.text.trim() : null,
            email: _isNewUser ? _emailCtrl.text.trim() : null,
          );
      final access = res['access'] as String?;
      final refresh = res['refresh'] as String?;
      if (access == null || refresh == null) {
        Log.error('otp/verify response without tokens', data: res);
        throw Exception('Resposta sem tokens.');
      }
      await ref.read(secureStoreProvider).saveTokens(access: access, refresh: refresh);
      Log.info('otp/verify ok', data: 'is_new=${res['is_new']}');
      if (mounted) context.go('/home');
    } on DioException catch (e) {
      Log.warn('otp/verify failed', error: e.message);
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      Log.error('otp/verify unexpected', error: e);
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _subtitle(String Function(String) tr) {
    switch (_step) {
      case 1:
        return tr('login.subtitleRegister');
      case 2:
        return '${tr('login.subtitleOtp')} $_phoneMasked';
      default:
        return tr('login.subtitlePhone');
    }
  }

  String _primaryLabel(String Function(String) tr) {
    switch (_step) {
      case 1:
        return tr('login.createAccount');
      case 2:
        return tr('login.enter');
      default:
        return tr('common.continue');
    }
  }

  VoidCallback _primaryAction() {
    switch (_step) {
      case 1:
        return _submitRegistration;
      case 2:
        return _verifyOtp;
      default:
        return _continueFromPhone;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final upLogo = isDark ? 'assets/up_digital_dark.png' : 'assets/up_digital_light.png';
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Spacer(),
            Image.asset(
              isDark ? 'assets/tpm_tur_dark.png' : 'assets/tpm_tur_light.png',
              height: 72,
              errorBuilder: (_, __, ___) => const SizedBox(height: 72),
            ),
            const SizedBox(height: 24),
            Center(
              child: Text(
                tr('login.title'),
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: -0.4),
              ),
            ),
            const SizedBox(height: 6),
            Center(
              child: Text(
                _subtitle(tr),
                style: const TextStyle(color: BuzUpColors.muted, fontSize: 13),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 32),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              child: KeyedSubtree(
                key: ValueKey(_step),
                child: _step == 0
                    ? _phoneInput(tr)
                    : _step == 1
                        ? _registerInputs(tr)
                        : _otpInput(tr),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(_error!,
                    style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5),
                    textAlign: TextAlign.center),
              ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _primaryAction(),
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : Text(_primaryLabel(tr)),
            ),
            if (_step == 1) ...[
              const SizedBox(height: 6),
              Center(
                child: TextButton(
                  onPressed: _busy ? null : _changePhone,
                  child: Text(tr('login.changePhone')),
                ),
              ),
            ],
            if (_step == 2) ...[
              const SizedBox(height: 6),
              Center(
                child: TextButton(
                  onPressed: (_resendSeconds > 0 || _busy) ? null : _resendOtp,
                  child: Text(_resendSeconds > 0
                      ? '${tr('login.resendIn')} $_resendSeconds s'
                      : tr('login.resend')),
                ),
              ),
              Center(
                child: TextButton(
                  onPressed: _busy ? null : _changePhone,
                  child: Text(tr('login.changePhone')),
                ),
              ),
            ],
            const Spacer(),
            Center(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('${tr('login.poweredBy')} ',
                      style: const TextStyle(color: BuzUpColors.muted, fontSize: 11, letterSpacing: 0.6)),
                  Image.asset(
                    upLogo,
                    height: 18,
                    errorBuilder: (_, __, ___) => const Text(
                      'UpDigital',
                      style: TextStyle(
                          color: BuzUpColors.muted,
                          fontSize: 11,
                          letterSpacing: 0.6,
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
          ]),
        ),
      ),
    );
  }

  Widget _phoneInput(String Function(String) tr) {
    return TextField(
      controller: _phoneCtrl,
      keyboardType: TextInputType.phone,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(9)],
      style: const TextStyle(fontSize: 18, letterSpacing: 1, fontWeight: FontWeight.w700),
      decoration: InputDecoration(
        labelText: tr('login.phoneLabel'),
        hintText: tr('login.phoneHint'),
        prefixText: '+258 ',
        prefixIcon: const Icon(Icons.phone_iphone),
      ),
      onSubmitted: (_) => _continueFromPhone(),
    );
  }

  Widget _registerInputs(String Function(String) tr) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _nameCtrl,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            labelText: tr('login.nameLabel'),
            hintText: tr('login.nameHint'),
            prefixIcon: const Icon(Icons.person_outline),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _emailCtrl,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(
            labelText: '${tr('login.emailLabel')} ${tr('common.optional')}',
            prefixIcon: const Icon(Icons.alternate_email),
          ),
          onSubmitted: (_) => _submitRegistration(),
        ),
      ],
    );
  }

  Widget _otpInput(String Function(String) tr) {
    return TextField(
      controller: _otpCtrl,
      autofocus: true,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
      textAlign: TextAlign.center,
      style: const TextStyle(fontSize: 32, letterSpacing: 12, fontWeight: FontWeight.w800),
      decoration: const InputDecoration(
        hintText: '------',
      ),
      onChanged: (v) {
        // Auto-submit as soon as the 6 digits are typed — no extra tap.
        if (v.trim().length == 6 && !_busy) _verifyOtp();
      },
      onSubmitted: (_) => _verifyOtp(),
    );
  }
}
