import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/app_version.dart';
import '../../core/bus_loader.dart';
import '../../core/feedback.dart';
import '../../core/labels.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Cinzento de apoio — BuzUpColors nao expoe um `muted`.
const _muted = Color(0xFF6B7A8F);

/// Perfil do agente/motorista: quem está sessão, em que terminal, e a senha.
///
/// Estes dados já vinham todos em `/api/agent/me/` mas nunca eram mostrados —
/// quem operava o terminal não tinha como confirmar com que conta estava a
/// vender, nem como trocar a senha sem pedir a um administrador.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final me = ref.watch(agentMeProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Perfil'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: me.when(
          loading: () => const Center(child: BusLoader(label: 'A carregar perfil...')),
          error: (e, _) => _ErrorState(message: '$e', onRetry: () => ref.refresh(agentMeProvider.future)),
          data: (data) {
            final agent = (data['agent'] as Map?) ?? const {};
            final driver = data['driver'] as Map?;
            final user = (data['user'] as Map?) ?? const {};
            final device = data['device'] as Map?;
            final session = data['session'] as Map?;

            return RefreshIndicator(
              onRefresh: () => ref.refresh(agentMeProvider.future),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
                children: [
                  _Identity(
                    name: (agent['full_name'] ?? user['username'] ?? '—').toString(),
                    role: driver != null ? 'Agente e motorista' : 'Agente',
                    isDark: isDark,
                  ),
                  const SizedBox(height: 16),
                  _Section(title: 'Conta', rows: [
                    ('Nome', (agent['full_name'] ?? '—').toString()),
                    ('Utilizador', (user['username'] ?? '—').toString()),
                    ('Telefone', (agent['phone'] ?? '—').toString()),
                    ('Estado', ticketStatusLabel((agent['status'] ?? '').toString())),
                    if ((user['email'] ?? '').toString().isNotEmpty)
                      ('Email', user['email'].toString()),
                  ]),
                  if (driver != null) ...[
                    const SizedBox(height: 12),
                    _Section(title: 'Motorista', rows: [
                      ('Nome', (driver['full_name'] ?? '—').toString()),
                      ('Carta de conducao', (driver['license_number'] ?? '—').toString()),
                      ('Estado', ticketStatusLabel((driver['status'] ?? '').toString())),
                    ]),
                  ],
                  const SizedBox(height: 12),
                  _Section(title: 'Terminal', rows: [
                    ('Numero de serie', (device?['serial_number'] ?? '—').toString()),
                    ('Modelo', (device?['model_name'] ?? '—').toString()),
                    ('Estado', ticketStatusLabel((device?['status'] ?? '').toString())),
                    ('Versao da app', AppVersion.label.isEmpty ? '—' : AppVersion.label),
                    if (session?['allocated_route_code'] != null)
                      ('Rota alocada', session!['allocated_route_code'].toString()),
                  ]),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    icon: const Icon(Icons.lock_reset),
                    label: const Text('ALTERAR SENHA'),
                    style: FilledButton.styleFrom(
                      backgroundColor: BuzUpColors.blue,
                      minimumSize: const Size.fromHeight(50),
                    ),
                    onPressed: () {
                      AppFeedback.click();
                      showModalBottomSheet(
                        context: context,
                        isScrollControlled: true,
                        useSafeArea: true,
                        builder: (_) => const _ChangePasswordSheet(),
                      );
                    },
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.logout, color: BuzUpColors.danger),
                    label: const Text('TERMINAR SESSAO', style: TextStyle(color: BuzUpColors.danger)),
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                    onPressed: () => _confirmLogout(context, ref),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Terminar sessao'),
        content: const Text('Vai precisar de entrar outra vez para vender.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Terminar')),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;

    final store = ref.read(secureStoreProvider);
    try {
      final refresh = await store.getRefresh();
      if (refresh != null && refresh.isNotEmpty) {
        await ref.read(agentApiProvider).logout(refresh);
      }
    } catch (_) {
      // Sessao local termina de qualquer forma: o token expira no servidor.
    }
    final serial = await store.getDeviceSerial();
    await store.clearAll();
    if (serial != null && serial.isNotEmpty) {
      // Preserva o onboarding do terminal — quem sai da conta nao tem de
      // registar o aparelho outra vez.
      await store.saveDeviceSerial(serial);
    }
    // Sem isto, o perfil e as viagens do utilizador anterior ficavam em cache
    // e apareciam ao proximo que entrasse neste terminal.
    ref.invalidate(agentMeProvider);
    ref.invalidate(isLoggedInProvider);
    if (context.mounted) context.go('/login');
  }
}

class _Identity extends StatelessWidget {
  const _Identity({required this.name, required this.role, required this.isDark});

  final String name;
  final String role;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final initials = name.trim().isEmpty
        ? '?'
        : name.trim().split(RegExp(r'\s+')).take(2).map((w) => w[0].toUpperCase()).join();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [BuzUpColors.navy, BuzUpColors.navyDark],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(children: [
        Container(
          width: 52, height: 52,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.16),
            shape: BoxShape.circle,
          ),
          child: Text(initials,
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name,
                maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 2),
            Text(role, style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600)),
          ]),
        ),
      ]),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.rows});

  final String title;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title.toUpperCase(),
            style: const TextStyle(fontSize: 10.5, letterSpacing: 1.4,
                fontWeight: FontWeight.w800, color: _muted)),
        const SizedBox(height: 8),
        for (final (label, value) in rows)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: Text(label, style: const TextStyle(fontSize: 12.5, color: _muted)),
              ),
              const SizedBox(width: 10),
              Expanded(
                flex: 2,
                child: Text(value,
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
              ),
            ]),
          ),
      ]),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.cloud_off, size: 40, color: _muted),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: _muted)),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: const Text('Tentar de novo')),
        ]),
      ),
    );
  }
}

class _ChangePasswordSheet extends ConsumerStatefulWidget {
  const _ChangePasswordSheet();

  @override
  ConsumerState<_ChangePasswordSheet> createState() => _ChangePasswordSheetState();
}

class _ChangePasswordSheetState extends ConsumerState<_ChangePasswordSheet> {
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;
  bool _obscure = true;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final next = _next.text;
    if (next.length < 8) {
      // O backend exige 8 neste endpoint; dizê-lo aqui evita uma ida ao
      // servidor só para receber a mesma recusa.
      setState(() => _error = 'A nova senha precisa de pelo menos 8 caracteres.');
      return;
    }
    if (next != _confirm.text) {
      setState(() => _error = 'A confirmacao nao coincide com a nova senha.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(agentApiProvider).changePassword(
            oldPassword: _current.text,
            newPassword: next,
          );
      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Senha alterada.')),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Expanded(
            child: Text('Alterar senha',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ),
          IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
        ]),
        const SizedBox(height: 4),
        TextField(
          controller: _current,
          obscureText: _obscure,
          decoration: const InputDecoration(labelText: 'Senha actual'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _next,
          obscureText: _obscure,
          decoration: InputDecoration(
            labelText: 'Nova senha',
            helperText: 'Minimo 8 caracteres',
            suffixIcon: IconButton(
              icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
              onPressed: () => setState(() => _obscure = !_obscure),
            ),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _confirm,
          obscureText: _obscure,
          decoration: const InputDecoration(labelText: 'Confirmar nova senha'),
        ),
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5)),
        ),
        const SizedBox(height: 16),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: BuzUpColors.blue,
            minimumSize: const Size.fromHeight(50),
          ),
          onPressed: _busy ? null : _submit,
          child: _busy
              ? const SizedBox(width: 22, height: 22,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Text('GUARDAR', style: TextStyle(fontWeight: FontWeight.w800)),
        ),
        const SizedBox(height: 6),
        const Text(
          'Esqueceu-se da senha actual? Peca ao administrador para a repor no portal.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11.5, color: _muted),
        ),
      ]),
    );
  }
}
