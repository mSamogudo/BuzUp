import 'package:dio/dio.dart';

import 'config.dart';
import 'logger.dart';
import 'storage.dart';

/// Dio wrapper that injects JWT, fires the unauthorised callback on 401,
/// and surfaces backend error messages in Portuguese.
class ApiClient {
  /// Set by `app.dart` so the router can redirect to /login on token expiry.
  static void Function()? onUnauthorized;

  ApiClient(this._store)
      : _dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiBaseUrl,
          connectTimeout: AppConfig.apiTimeout,
          receiveTimeout: AppConfig.apiTimeout,
          contentType: Headers.jsonContentType,
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final access = await _store.getAccess();
        if (access != null && access.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $access';
        }
        Log.debug('http ${options.method} ${options.path}');
        handler.next(options);
      },
      onResponse: (response, handler) {
        Log.info(
          'http ${response.requestOptions.method} ${response.requestOptions.path} -> ${response.statusCode}',
        );
        handler.next(response);
      },
      onError: (e, handler) async {
        Log.warn(
          'http ${e.requestOptions.method} ${e.requestOptions.path} FAILED',
          data: 'status=${e.response?.statusCode} type=${e.type.name}',
          error: e.message,
        );
        final req = e.requestOptions;
        final is401 = e.response?.statusCode == 401;
        final alreadyRetried = req.extra['__retried'] == true;
        final isRefreshCall = req.path.contains('/auth/token/refresh');
        if (is401 && !alreadyRetried && !isRefreshCall) {
          // Try to silently refresh the access token before logging out.
          final newAccess = await _tryRefresh();
          if (newAccess != null) {
            req.extra['__retried'] = true;
            req.headers['Authorization'] = 'Bearer $newAccess';
            try {
              final retried = await _dio.fetch<dynamic>(req);
              return handler.resolve(retried);
            } on DioException catch (err) {
              return handler.next(err);
            }
          }
          // Refresh failed -> session is really over.
          await _store.clearAll();
          onUnauthorized?.call();
        } else if (is401) {
          await _store.clearAll();
          onUnauthorized?.call();
        }
        handler.next(e);
      },
    ));
  }

  final Dio _dio;
  final SecureStore _store;
  Future<String?>? _refreshing; // single-flight so concurrent 401s refresh once

  /// Returns a fresh access token (refreshing at most once concurrently), or
  /// null if there's no usable refresh token / the refresh failed.
  Future<String?> _tryRefresh() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<String?> _doRefresh() async {
    final refresh = await _store.getRefresh();
    if (refresh == null || refresh.isEmpty) return null;
    try {
      // Bare Dio (no interceptors) to avoid recursion on the refresh call.
      final bare = Dio(BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: AppConfig.apiTimeout,
        receiveTimeout: AppConfig.apiTimeout,
        contentType: Headers.jsonContentType,
      ));
      final res = await bare.post<Map<String, dynamic>>(
        '/api/auth/token/refresh/',
        data: {'refresh': refresh},
      );
      final access = res.data?['access'] as String?;
      if (access == null || access.isEmpty) return null;
      final newRefresh = (res.data?['refresh'] as String?) ?? refresh;
      await _store.saveTokens(access: access, refresh: newRefresh);
      Log.info('token refreshed');
      return access;
    } catch (err) {
      Log.warn('token refresh failed', error: err);
      return null;
    }
  }

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? query, Options? options}) {
    return _dio.get<T>(path, queryParameters: query, options: options);
  }

  Future<Response<T>> post<T>(String path, {dynamic data, Options? options}) {
    return _dio.post<T>(path, data: data, options: options);
  }

  static String extractError(DioException e) {
    final data = e.response?.data;
    if (data is Map) {
      if (data['detail'] is String) return data['detail'] as String;
      if (data['non_field_errors'] is List && (data['non_field_errors'] as List).isNotEmpty) {
        return (data['non_field_errors'] as List).first.toString();
      }
      for (final v in data.values) {
        if (v is List && v.isNotEmpty) return v.first.toString();
        if (v is String) return v;
      }
    }
    if (e.type == DioExceptionType.connectionTimeout || e.type == DioExceptionType.receiveTimeout) {
      return 'Servidor demorou a responder. Tente de novo.';
    }
    if (e.type == DioExceptionType.connectionError) {
      return 'Sem ligacao a internet ou servidor inacessivel.';
    }
    return 'Erro ${e.response?.statusCode ?? ''}: ${e.message ?? 'desconhecido'}'.trim();
  }
}
