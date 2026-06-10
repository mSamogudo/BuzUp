import 'dart:io' show Platform;

import 'package:crypto/crypto.dart';
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
    // Split-per-ABI builds offset the versionCode (abi*1000 + buildNumber),
    // e.g. arm64 -> 2001. Strip the ABI offset so we compare the logical
    // build number the portal admin actually enters.
    final code = (int.tryParse(info.buildNumber) ?? 0) % 1000;
    final res = await ref.read(agentApiProvider).checkUpdate(currentVersionCode: code);
    if (res['update_available'] != true) return;
    if (!context.mounted) return;
    await _showUpdateDialog(context, res, info.version);
  } catch (e) {
    Log.warn('app update check failed', error: e);
  }
}

Future<List<int>> _downloadApk(String url, void Function(int, int) onProgress) async {
  final dio = Dio(BaseOptions(receiveTimeout: const Duration(minutes: 5)));
  final res = await dio.get<List<int>>(
    url,
    options: Options(responseType: ResponseType.bytes),
    onReceiveProgress: onProgress,
  );
  return res.data ?? const [];
}

/// Confirma que o APK descarregado e exactamente o que o backend publicou
/// (tamanho + SHA-256). Devolve null se OK, ou uma mensagem de erro a mostrar.
/// Impede instalar um ficheiro corrompido ou adulterado (MITM).
String? _verifyApk(List<int> bytes, Map<String, dynamic> r) {
  final expectedSize = (r['file_size_bytes'] as num?)?.toInt();
  if (expectedSize != null && expectedSize > 0 && bytes.length != expectedSize) {
    Log.warn('APK size mismatch: got ${bytes.length} expected $expectedSize');
    return 'Ficheiro corrompido (tamanho). Atualizacao cancelada.';
  }
  final expectedSha = (r['checksum'] ?? '').toString().toLowerCase().trim();
  if (expectedSha.isNotEmpty) {
    final actualSha = sha256.convert(bytes).toString();
    if (actualSha != expectedSha) {
      Log.warn('APK checksum mismatch: got $actualSha expected $expectedSha');
      return 'Ficheiro inseguro (checksum). Atualizacao cancelada.';
    }
  }
  return null;
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
      var progress = 0.0;
      String? error;
      return StatefulBuilder(builder: (ctx, setLocal) {
        Future<void> doUpdate() async {
          setLocal(() {
            busy = true;
            progress = 0;
            error = null;
          });
          try {
            if (Platform.isAndroid) {
              final bytes = await _downloadApk(url, (received, total) {
                if (total > 0) setLocal(() => progress = received / total);
              });
              if (bytes.isEmpty) throw Exception('download vazio');
              final integrityError = _verifyApk(bytes, r);
              if (integrityError != null) {
                setLocal(() => error = integrityError);
                return;
              }
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
                  Text(progress > 0
                      ? 'A descarregar... ${(progress * 100).toStringAsFixed(0)}%'
                      : 'A descarregar...'),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: progress > 0 ? progress : null,
                      minHeight: 8,
                    ),
                  ),
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
