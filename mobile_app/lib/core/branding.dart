import 'package:cached_network_image/cached_network_image.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';
import 'logger.dart';

/// Marca configuravel no portal (apps/branding). Cada slot e uma URL absoluta
/// (ou "" quando nao definido). Cai sempre para o asset embutido na app.
class Branding {
  const Branding(this.platformName, this.logos);

  final String platformName;
  final Map<String, String> logos; // chave = <slot>_url

  static const empty = Branding('BuzUp', {});

  String url(String slot) => logos['${slot}_url'] ?? '';

  static Branding fromJson(Map<String, dynamic> j) {
    final logos = <String, String>{};
    j.forEach((k, v) {
      if (k.endsWith('_url') && v is String) logos[k] = v;
    });
    return Branding((j['platform_name'] as String?) ?? 'BuzUp', logos);
  }
}

const _kCacheKey = 'buzup.branding.cache';

class BrandingController extends StateNotifier<Branding> {
  BrandingController() : super(Branding.empty) {
    _loadCache();
    refresh();
  }

  Future<void> _loadCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_kCacheKey);
      if (raw == null) return;
      // formato: "name\nslot_url=valor\n..."
      final lines = raw.split('\n');
      final name = lines.isNotEmpty ? lines.first : 'BuzUp';
      final logos = <String, String>{};
      for (final l in lines.skip(1)) {
        final i = l.indexOf('=');
        if (i > 0) logos[l.substring(0, i)] = l.substring(i + 1);
      }
      state = Branding(name, logos);
    } catch (_) {/* ignora cache corrompida */}
  }

  Future<void> refresh() async {
    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: AppConfig.apiTimeout,
        receiveTimeout: AppConfig.apiTimeout,
      ));
      final res = await dio.get<Map<String, dynamic>>('/api/branding/');
      if (res.data == null) return;
      final b = Branding.fromJson(res.data!);
      state = b;
      final prefs = await SharedPreferences.getInstance();
      final buf = StringBuffer(b.platformName);
      b.logos.forEach((k, v) => buf.write('\n$k=$v'));
      await prefs.setString(_kCacheKey, buf.toString());
    } catch (e) {
      Log.warn('branding refresh failed', error: e);
    }
  }
}

final brandingProvider =
    StateNotifierProvider<BrandingController, Branding>((ref) => BrandingController());

/// Logo da marca: usa a URL remota (em cache) e cai para o asset embutido.
class BrandLogo extends ConsumerWidget {
  const BrandLogo({
    super.key,
    required this.slot,
    required this.fallbackAsset,
    this.height,
    this.width,
    this.fit = BoxFit.contain,
  });

  final String slot;
  final String fallbackAsset;
  final double? height;
  final double? width;
  final BoxFit fit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final url = ref.watch(brandingProvider).url(slot);
    final fallback = Image.asset(fallbackAsset, height: height, width: width, fit: fit);
    if (url.isEmpty) return fallback;
    return CachedNetworkImage(
      imageUrl: url,
      height: height,
      width: width,
      fit: fit,
      fadeInDuration: const Duration(milliseconds: 150),
      placeholder: (context, url) => fallback,
      errorWidget: (context, url, error) => fallback,
    );
  }
}
