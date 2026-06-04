import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart' show launchUrl, LaunchMode;

import '../../core/api_client.dart';
import '../../core/config.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  Future<void> _editProfile(BuildContext context, WidgetRef ref, Map<String, dynamic> data) async {
    final nameCtrl = TextEditingController(text: data['full_name']?.toString() ?? '');
    final emailCtrl = TextEditingController(text: data['email']?.toString() ?? '');
    String? error;
    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setLocal) {
        bool busy = false;
        Future<void> submit() async {
          if (nameCtrl.text.trim().length < 2) {
            setLocal(() => error = 'Nome deve ter pelo menos 2 caracteres.');
            return;
          }
          setLocal(() {
            busy = true;
            error = null;
          });
          try {
            await ref.read(passengerApiProvider).updateProfile(
                  fullName: nameCtrl.text.trim(),
                  email: emailCtrl.text.trim(),
                );
            if (ctx.mounted) Navigator.pop(ctx, true);
          } on DioException catch (e) {
            setLocal(() {
              busy = false;
              error = ApiClient.extractError(e);
            });
          } catch (e) {
            setLocal(() {
              busy = false;
              error = e.toString();
            });
          }
        }
        return AlertDialog(
          title: const Text('Editar perfil'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(
                controller: nameCtrl,
                autofocus: true,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'Nome completo',
                  prefixIcon: Icon(Icons.person),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email (opcional)',
                  prefixIcon: Icon(Icons.mail_outline),
                ),
              ),
              if (error != null) Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(error!,
                    style: const TextStyle(color: BuzUpColors.danger, fontSize: 12)),
              ),
            ]),
          ),
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: busy ? null : submit,
              child: busy
                  ? const SizedBox(width: 18, height: 18,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('GUARDAR'),
            ),
          ],
        );
      }),
    );
    if (saved == true) {
      ref.invalidate(meProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Perfil actualizado.')),
        );
      }
    }
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Terminar Sessao?'),
        content: const Text('Vai precisar de iniciar sessao com o seu telefone de novo.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('SAIR')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(secureStoreProvider).clearAll();
    if (context.mounted) context.go('/login');
  }

  Future<void> _downloadExtract(BuildContext context, WidgetRef ref) async {
    final token = await ref.read(secureStoreProvider).getAccess();
    if (token == null || token.isEmpty) return;
    // The backend extract endpoint accepts `?token=` (see
    // PassengerPortalExtractView authentication_classes), so the OS browser
    // can fetch the PDF directly without an Authorization header.
    final url = '${AppConfig.apiBaseUrl}/api/auth/me/passenger-portal/extract/'
        '?token=${Uri.encodeQueryComponent(token)}';
    try {
      final ok = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nao foi possivel abrir o navegador.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Funcionalidade indisponivel.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Perfil', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: SafeArea(
        child: me.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Padding(
            padding: const EdgeInsets.all(20),
            child: Text('Erro: $e', style: const TextStyle(color: BuzUpColors.danger)),
          ),
          data: (data) => _content(context, ref, data),
        ),
      ),
    );
  }

  Widget _content(BuildContext context, WidgetRef ref, Map<String, dynamic> data) {
    final fullName = data['full_name']?.toString() ?? '-';
    final phone = data['phone']?.toString() ?? '-';
    final email = data['email']?.toString() ?? '';
    final cardNumber = data['card_number']?.toString() ?? '';
    final balance = data['balance']?.toString() ?? '0';

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      children: [
        // Avatar + name + phone
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: BuzUpColors.border),
          ),
          child: Row(children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: BuzUpColors.orange.withValues(alpha: 0.18),
              child: Text(
                fullName.trim().isNotEmpty ? fullName.trim()[0].toUpperCase() : '?',
                style: const TextStyle(
                    color: BuzUpColors.orange, fontWeight: FontWeight.w900, fontSize: 22),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(fullName,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                const SizedBox(height: 2),
                Text(phone,
                    style: const TextStyle(fontSize: 12.5, color: BuzUpColors.muted)),
                if (email.isNotEmpty)
                  Text(email,
                      style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
              ]),
            ),
            IconButton(
              icon: const Icon(Icons.edit, color: BuzUpColors.orange),
              tooltip: 'Editar perfil',
              onPressed: () => _editProfile(context, ref, data),
            ),
          ]),
        ),
        const SizedBox(height: 14),
        // Account info
        _section(context, 'Conta', [
          _info(Icons.credit_card, 'Cartao', cardNumber.isEmpty ? 'Sem cartao' : cardNumber),
          _info(Icons.account_balance_wallet, 'Saldo', '$balance MZN'),
        ]),
        const SizedBox(height: 14),
        // Actions
        _section(context, 'Documentos', [
          _action(Icons.event_note, 'Extracto da conta',
              () => context.push('/extract')),
          _action(Icons.receipt_long, 'Taxas e tarifas',
              () => context.push('/admin-fees')),
          _action(Icons.picture_as_pdf, 'Descarregar extracto (PDF)',
              () => _downloadExtract(context, ref)),
        ]),
        const SizedBox(height: 14),
        _section(context, 'Preferencias', [
          _themeRow(context, ref),
          _languageRow(context, ref),
        ]),
        const SizedBox(height: 14),
        _section(context, 'Sessao', [
          _action(Icons.logout, 'Terminar sessao',
              () => _logout(context, ref), danger: true),
        ]),
        const SizedBox(height: 24),
        const Center(child: Text('BuzUp Passageiro · v0.3',
            style: TextStyle(fontSize: 11, color: BuzUpColors.muted))),
        const SizedBox(height: 4),
        Center(child: Image.asset(
          Theme.of(context).brightness == Brightness.dark
              ? 'assets/up_digital_dark.png'
              : 'assets/up_digital_light.png',
          height: 18,
          errorBuilder: (_, _, _) => const Text('powered by UpDigital',
              style: TextStyle(fontSize: 11, color: BuzUpColors.muted, letterSpacing: 0.5)),
        )),
      ],
    );
  }

  Widget _themeRow(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeControllerProvider);
    final label = switch (mode) {
      ThemeMode.light => 'Claro',
      ThemeMode.dark => 'Escuro',
      ThemeMode.system => 'Sistema',
    };
    final icon = switch (mode) {
      ThemeMode.light => Icons.light_mode,
      ThemeMode.dark => Icons.dark_mode,
      ThemeMode.system => Icons.brightness_auto,
    };
    return _row(icon, 'Tema', label, () {
      ref.read(themeControllerProvider.notifier).toggle();
    });
  }

  Widget _languageRow(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(localeControllerProvider);
    final label = locale.languageCode == 'en' ? 'English' : 'Portugues';
    return _row(Icons.language, 'Idioma', label, () async {
      final next = locale.languageCode == 'en' ? 'pt' : 'en';
      await ref.read(localeControllerProvider.notifier).set(next);
    });
  }

  Widget _row(IconData icon, String label, String value, VoidCallback onTap) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(children: [
            Icon(icon, size: 18, color: BuzUpColors.orange),
            const SizedBox(width: 10),
            Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text(value, style: const TextStyle(fontSize: 12.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
            const SizedBox(width: 6),
            const Icon(Icons.chevron_right, size: 18, color: BuzUpColors.muted),
          ]),
        ),
      ),
    );
  }

  Widget _section(BuildContext context, String title, List<Widget> rows) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
          child: Text(title.toUpperCase(),
              style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted,
                  fontWeight: FontWeight.w800, letterSpacing: 1.4)),
        ),
        ...rows.expand((w) => [w, const Divider(height: 1, color: BuzUpColors.border)])
            .toList()
          ..removeLast(),
      ]),
    );
  }

  Widget _info(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(children: [
        Icon(icon, size: 18, color: BuzUpColors.muted),
        const SizedBox(width: 10),
        Text(label, style: const TextStyle(fontSize: 12.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        const Spacer(),
        Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
      ]),
    );
  }

  Widget _action(IconData icon, String label, VoidCallback onTap, {bool danger = false}) {
    final color = danger ? BuzUpColors.danger : null;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(children: [
            Icon(icon, size: 18, color: color ?? BuzUpColors.navy),
            const SizedBox(width: 10),
            Expanded(child: Text(label,
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: color))),
            Icon(Icons.chevron_right, size: 18, color: color ?? BuzUpColors.muted),
          ]),
        ),
      ),
    );
  }
}
