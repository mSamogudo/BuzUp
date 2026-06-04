import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/theme_controller.dart';

class ActivationCodeScreen extends ConsumerStatefulWidget {
  const ActivationCodeScreen({super.key});

  @override
  ConsumerState<ActivationCodeScreen> createState() => _ActivationCodeScreenState();
}

class _ActivationCodeScreenState extends ConsumerState<ActivationCodeScreen> {
  final _codeCtrl = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _serial;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      final serial = await ref.read(secureStoreProvider).getDeviceSerial();
      if (mounted) setState(() => _serial = serial);
    });
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _codeCtrl.text.trim().toUpperCase();
    if (_serial == null) {
      setState(() => _error = 'Serial nao encontrado.');
      return;
    }
    if (code.length < 6) {
      setState(() => _error = 'Introduza o codigo completo.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(agentApiProvider).activateDevice(serial: _serial!, code: code);
      await AppFeedback.success();
      if (mounted) context.go('/login');
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
    final bg = isDark ? const Color(0xFF1A2A4E) : const Color(0xFFF7F4EE);
    final mainColor = isDark ? Colors.white : BuzUpColors.navy;

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: mainColor,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/onboarding'),
        ),
        actions: [
          IconButton(
            icon: Icon(_themeIcon(ref.watch(themeControllerProvider))),
            onPressed: () => ref.read(themeControllerProvider.notifier).toggle(),
            tooltip: 'Mudar tema',
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Column(
            children: [
              Image.asset(isDark ? 'assets/tpm_tur_dark.png' : 'assets/tpm_tur_light.png',
                  height: 60,
                  errorBuilder: (_, __, ___) => Text('TPM-TUR',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: mainColor))),
              const SizedBox(height: 16),
              Icon(Icons.key, color: BuzUpColors.orange, size: 48),
              const SizedBox(height: 8),
              Text('Codigo de Activacao',
                  style: TextStyle(color: mainColor, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(
                'Introduza o codigo fornecido pelo administrador.',
                textAlign: TextAlign.center,
                style: TextStyle(color: mainColor.withValues(alpha: 0.7), fontSize: 12),
              ),
              if (_serial != null) ...[
                const SizedBox(height: 6),
                Text('Serial: $_serial',
                    style: TextStyle(color: mainColor.withValues(alpha: 0.5), fontSize: 10)),
              ],
              const SizedBox(height: 18),
              if (_error != null) ...[
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(color: Colors.red.shade50,
                      border: Border.all(color: Colors.red.shade300),
                      borderRadius: BorderRadius.circular(8)),
                  child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                ),
                const SizedBox(height: 12),
              ],
              TextField(
                controller: _codeCtrl,
                enabled: !_busy,
                autofocus: true,
                textAlign: TextAlign.center,
                textCapitalization: TextCapitalization.characters,
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
                  LengthLimitingTextInputFormatter(12),
                ],
                style: TextStyle(
                    fontSize: 26, fontWeight: FontWeight.bold,
                    color: mainColor, letterSpacing: 6),
                decoration: InputDecoration(
                  hintText: 'XXXXXXXX',
                  hintStyle: TextStyle(color: mainColor.withValues(alpha: 0.3), letterSpacing: 6),
                  enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: mainColor.withValues(alpha: 0.3))),
                  focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: BuzUpColors.orange, width: 2)),
                  filled: false,
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  icon: const Icon(Icons.lock_open),
                  label: Text(_busy ? 'A activar...' : 'ACTIVAR'),
                  onPressed: _busy ? null : _submit,
                ),
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text('powered by ',
                      style: TextStyle(color: mainColor.withValues(alpha: 0.6), fontSize: 11)),
                  Image.asset(isDark ? 'assets/up_digital_dark.png' : 'assets/up_digital_light.png',
                      height: 18,
                      errorBuilder: (_, __, ___) => Text('UpDigital',
                          style: TextStyle(color: mainColor, fontWeight: FontWeight.bold))),
                ]),
              ),
            ],
          ),
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
