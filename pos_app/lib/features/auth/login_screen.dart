import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/theme_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _userFocus = FocusNode();
  final _passFocus = FocusNode();
  final _scrollCtrl = ScrollController();
  bool _busy = false;
  bool _obscure = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _passFocus.addListener(_onPassFocus);
  }

  void _onPassFocus() {
    if (_passFocus.hasFocus) {
      // Wait for the keyboard to appear, then scroll the password field into view.
      Future.delayed(const Duration(milliseconds: 250), () {
        if (mounted) {
          _scrollCtrl.animateTo(
            _scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _passFocus.removeListener(_onPassFocus);
    _userCtrl.dispose();
    _passCtrl.dispose();
    _userFocus.dispose();
    _passFocus.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(agentApiProvider);
      final store = ref.read(secureStoreProvider);
      final serial = await store.getDeviceSerial();
      final res = await api.login(
        username: _userCtrl.text.trim(),
        password: _passCtrl.text,
        deviceSerial: serial,
      );
      final access = res['access'] as String?;
      final refresh = res['refresh'] as String?;
      final agentId = res['agent_id'] as int?;
      final agentName = res['agent_name'] as String? ?? '';
      if (access == null || refresh == null || agentId == null) {
        setState(() => _error = 'Resposta invalida do servidor.');
        return;
      }
      await store.saveTokens(access: access, refresh: refresh);
      await store.saveAgent(id: agentId, name: agentName);
      await AppFeedback.success();
      ref.invalidate(isLoggedInProvider);
      ref.invalidate(agentMeProvider);
      if (mounted) context.go('/home');
    } on DioException catch (e) {
      await AppFeedback.error();
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      await AppFeedback.error();
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final keyboardOpen = MediaQuery.of(context).viewInsets.bottom > 0;

    // tpm_tur_light.png has a DARK logo (used on light backgrounds).
    // tpm_tur_dark.png has a LIGHT/white logo (used on dark backgrounds).
    final tpmLogo = isDark ? 'assets/tpm_tur_dark.png' : 'assets/tpm_tur_light.png';
    final upLogo = isDark ? 'assets/up_digital_dark.png' : 'assets/up_digital_light.png';

    final bg = isDark ? const Color(0xFF1A2A4E) : const Color(0xFFF7F4EE);
    final mainColor = isDark ? Colors.white : BuzUpColors.navy;
    final mutedColor = mainColor.withValues(alpha: 0.6);

    return Scaffold(
      backgroundColor: bg,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Stack(
          children: [
            SingleChildScrollView(
              controller: _scrollCtrl,
              padding: EdgeInsets.fromLTRB(
                20, 8, 20,
                keyboardOpen ? 16 : 56,  // leaves room for the footer when closed
              ),
              child: Column(
                children: [
                  // Theme toggle (small)
                  Align(
                    alignment: Alignment.topRight,
                    child: IconButton(
                      iconSize: 22,
                      icon: Icon(_themeIcon(ref.watch(themeControllerProvider)),
                          color: mutedColor),
                      onPressed: () => ref.read(themeControllerProvider.notifier).toggle(),
                      tooltip: 'Mudar tema',
                    ),
                  ),
                  // TPM-TUR logo
                  Image.asset(tpmLogo,
                      height: 78,
                      fit: BoxFit.contain,
                      errorBuilder: (_, __, ___) => Text('TPM-TUR S.A.',
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: mainColor))),
                  const SizedBox(height: 4),
                  Text('TRANSPORTE & TURISMO',
                      style: TextStyle(fontSize: 9, letterSpacing: 1.8, color: mutedColor)),
                  const SizedBox(height: 12),
                  Container(width: 50, height: 2, color: BuzUpColors.orange),
                  const SizedBox(height: 22),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 360),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          if (_error != null) ...[
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                border: Border.all(color: Colors.red.shade300),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(children: [
                                const Icon(Icons.error_outline, color: Colors.red, size: 18),
                                const SizedBox(width: 8),
                                Expanded(child: Text(_error!,
                                    style: const TextStyle(color: Colors.red, fontSize: 12))),
                              ]),
                            ),
                            const SizedBox(height: 12),
                          ],
                          TextFormField(
                            controller: _userCtrl,
                            focusNode: _userFocus,
                            enabled: !_busy,
                            textInputAction: TextInputAction.next,
                            onFieldSubmitted: (_) => _passFocus.requestFocus(),
                            decoration: const InputDecoration(
                              labelText: 'Utilizador',
                              prefixIcon: Icon(Icons.person),
                              isDense: true,
                            ),
                            validator: (v) => (v ?? '').trim().isEmpty ? 'Obrigatorio' : null,
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _passCtrl,
                            focusNode: _passFocus,
                            enabled: !_busy,
                            obscureText: _obscure,
                            textInputAction: TextInputAction.done,
                            onFieldSubmitted: (_) => _submit(),
                            decoration: InputDecoration(
                              labelText: 'Senha',
                              prefixIcon: const Icon(Icons.lock),
                              isDense: true,
                              suffixIcon: IconButton(
                                icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off, size: 18),
                                onPressed: () => setState(() => _obscure = !_obscure),
                              ),
                            ),
                            validator: (v) => (v ?? '').isEmpty ? 'Obrigatorio' : null,
                          ),
                          const SizedBox(height: 18),
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: FilledButton(
                              onPressed: _busy ? null : _submit,
                              child: _busy
                                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                  : const Text('ENTRAR', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Footer "powered by UpDigital" — only visible when keyboard is hidden.
            if (!keyboardOpen)
              Positioned(
                bottom: 8,
                left: 0,
                right: 0,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('powered by ',
                        style: TextStyle(color: mutedColor, fontSize: 11)),
                    Image.asset(upLogo,
                        height: 22,
                        errorBuilder: (_, __, ___) => Text('UpDigital',
                            style: TextStyle(color: mainColor, fontWeight: FontWeight.bold))),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  IconData _themeIcon(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light: return Icons.light_mode;
      case ThemeMode.dark: return Icons.dark_mode;
      case ThemeMode.system: return Icons.brightness_auto;
    }
  }
}
