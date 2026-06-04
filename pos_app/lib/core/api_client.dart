import 'package:dio/dio.dart';

import 'config.dart';
import 'logger.dart';
import 'storage.dart';

/// Thin wrapper around Dio that injects JWT, parses backend errors and
/// auto-clears tokens on 401 then redirects to /login (when set).
class ApiClient {
  /// Set by `app.dart` so 401 responses can navigate to the login screen.
  static void Function()? onUnauthorized;

  ApiClient(this._store) : _dio = Dio(BaseOptions(
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
        if (e.response?.statusCode == 401) {
          await _store.clearAll();
          final cb = onUnauthorized;
          if (cb != null) cb();
        }
        handler.next(e);
      },
    ));
  }

  final Dio _dio;
  final SecureStore _store;

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? query, Options? options}) {
    return _dio.get<T>(path, queryParameters: query, options: options);
  }

  Future<Response<T>> post<T>(String path, {dynamic data, Options? options}) {
    return _dio.post<T>(path, data: data, options: options);
  }

  Future<Response<List<int>>> download(String path) {
    return _dio.get<List<int>>(
      path,
      options: Options(responseType: ResponseType.bytes),
    );
  }

  /// Convert a Dio error into a human-friendly Portuguese message based on
  /// the backend error format: {"detail": "..."} or field-level errors.
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
