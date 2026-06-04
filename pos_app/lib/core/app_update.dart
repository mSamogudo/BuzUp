import 'dart:io' show Platform;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'logger.dart';
import 'providers.dart';

const _installerChannel = MethodChannel('buzup/installer');

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

Future<List<int>> _downloadApk(String url) async {
  final dio = Dio(BaseOptions(receiveTimeout: const Duration(minutes: 5)));
  final res = await dio.get<List<int>>(url, options: Options(responseType: ResponseType.bytes));
  return res.data ?? const [];
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
    builder: (ctx) {
      var busy = false;
      String? error;
      return StatefulBuilder(builder: (ctx, setLocal) {
        Future<void> doUpdate() async {
          setLocal(() {
            busy = true;
            error = null;
          });
          try {
            if (Platform.isAndroid) {
              final bytes = await _downloadApk(url);
              if (bytes.isEmpty) throw Exception('download vazio');
              await _installerChannel.invokeMethod('installApk', {
                'bytes': Uint8List.fromList(bytes),
                'fileName': 'buzup-pos-$newVersion.apk',
              });
            } else {
              await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
              if (!mandatory && ctx.mounted) Navigator.pop(ctx);
            }
          } catch (e) {
            Log.warn('update install failed', error: e);
            setLocal(() => error = 'Nao foi possivel instalar. Tente de novo.');
          } finally {
            setLocal(() => busy = false);
          }
        }

        return PopScope(
          canPop: !mandatory && !busy,
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
                if (busy) ...[
                  const SizedBox(height: 14),
                  Row(children: const [
                    SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                    SizedBox(width: 10),
                    Text('A descarregar...'),
                  ]),
                ],
                if (error != null) ...[
                  const SizedBox(height: 10),
                  Text(error!, style: const TextStyle(color: Colors.red, fontSize: 12.5)),
                ],
              ],
            ),
            actions: [
              if (!mandatory)
                TextButton(
                  onPressed: busy ? null : () => Navigator.pop(ctx),
                  child: const Text('Agora nao'),
                ),
              FilledButton(
                onPressed: (busy || url.isEmpty) ? null : doUpdate,
                child: const Text('Atualizar'),
              ),
            ],
          ),
        );
      });
    },
  );
}
