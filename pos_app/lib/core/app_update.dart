import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'logger.dart';
import 'providers.dart';

/// Asks the backend if a newer published POS release exists and, if so, shows
/// an update prompt. Mandatory updates cannot be dismissed. Failures are
/// swallowed so a check never blocks the terminal.
Future<void> checkForAppUpdate(BuildContext context, WidgetRef ref) async {
  try {
    final info = await PackageInfo.fromPlatform();
    final code = int.tryParse(info.buildNumber) ?? 0;
    final res = await ref.read(agentApiProvider).checkUpdate(currentVersionCode: code);
    if (res['update_available'] != true) return;
    if (!context.mounted) return;
    await _showUpdateDialog(context, res, info.version);
  } catch (e) {
    Log.warn('app update check failed', error: e);
  }
}

Future<void> _showUpdateDialog(
  BuildContext context,
  Map<String, dynamic> r,
  String currentVersion,
) async {
  final mandatory = r['is_mandatory'] == true;
  final newVersion = (r['version_name'] ?? '').toString();
  final notes = (r['release_notes'] ?? '').toString();
  final url = (r['download_url'] ?? '').toString();

  await showDialog<void>(
    context: context,
    barrierDismissible: !mandatory,
    builder: (ctx) => PopScope(
      canPop: !mandatory,
      child: AlertDialog(
        title: const Text('Nova versao disponivel'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Versao $newVersion disponivel (tem a $currentVersion).'),
            if (mandatory) ...[
              const SizedBox(height: 8),
              const Text('Esta actualizacao e obrigatoria.',
                  style: TextStyle(fontWeight: FontWeight.w700)),
            ],
            if (notes.trim().isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(notes, style: const TextStyle(fontSize: 12.5)),
            ],
          ],
        ),
        actions: [
          if (!mandatory)
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Agora nao')),
          FilledButton(
            onPressed: url.isEmpty
                ? null
                : () async {
                    final ok = await launchUrl(Uri.parse(url),
                        mode: LaunchMode.externalApplication);
                    if (!ok) Log.warn('could not open update url: $url');
                    if (!mandatory && ctx.mounted) Navigator.pop(ctx);
                  },
            child: const Text('Atualizar'),
          ),
        ],
      ),
    ),
  );
}
