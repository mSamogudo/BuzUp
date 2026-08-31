import 'dart:io';

import 'package:dio/dio.dart';
import 'package:dio/io.dart';

import 'config.dart';
import 'logger.dart';
import 'storage.dart';

/// Mantém a ligação ao servidor aberta entre pedidos.
///
/// O `HttpClient` do Dart fecha uma ligação inactiva ao fim de **15
/// segundos**. O heartbeat do terminal é de 60 em 60, e as acções do agente
/// são ainda mais espaçadas — ou seja, quase todos os pedidos pagavam um
/// aperto de mão TLS novo.
///
/// Medido contra o servidor: o trabalho do backend leva ~0,26 s, mas o TLS
/// variava entre 0,3 e 1,6 s. Era daí que vinha a sensação de que "os ecrãs
/// demoram a processar" — o tempo não estava a ser gasto a processar nada.
///
/// 90 s cobrem o intervalo do heartbeat, que assim serve também para manter a
/// ligação quente: quando o agente toca em algo, o canal já está aberto.
void _reaproveitarLigacoes(Dio dio) {
  dio.httpClientAdapter = IOHttpClientAdapter(
    createHttpClient: () => HttpClient()
      ..idleTimeout = const Duration(seconds: 90)
      // O terminal fala com um só servidor; mais do que isto não ajuda e
      // multiplica apertos de mão em paralelo no arranque.
      ..maxConnectionsPerHost = 4
      ..connectionTimeout = AppConfig.connectTimeout,
  );
}

/// Thin wrapper around Dio that injects JWT, parses backend errors and
/// auto-clears tokens on 401 then redirects to /login (when set).
class ApiClient {
  /// Set by `app.dart` so 401 responses can navigate to the login screen.
  static void Function()? onUnauthorized;

  ApiClient(this._store) : _dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiBaseUrl,
          // Ligar não é responder. Estabelecer TCP+TLS leva menos de dois
          // segundos mesmo com o servidor sob carga; esperar 25 por isso era
          // deixar o agente 25 segundos a olhar para um ecrã parado quando a
          // rede está morta. O tempo de RESPOSTA fica generoso, porque um
          // pedido de pagamento demora mesmo.
          connectTimeout: AppConfig.connectTimeout,
          receiveTimeout: AppConfig.apiTimeout,
          sendTimeout: AppConfig.apiTimeout,
          contentType: Headers.jsonContentType,
        )) {
    _reaproveitarLigacoes(_dio);
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
        // Falha no PROPRIO login (credenciais/OTP errados) nao e sessao
        // expirada — deixar o ecra de login mostrar o erro, sem limpar tokens
        // nem redirecionar (que recarregava o ecra).
        final isLoginAttempt =
            req.path.contains('/agent/auth/login') || req.path.contains('/auth/otp');
        if (is401 && isLoginAttempt) {
          handler.next(e);
          return;
        }
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
          await _store.clearAll();
          final cb = onUnauthorized;
          if (cb != null) cb();
        } else if (is401) {
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
  Future<String?>? _refreshing; // single-flight so concurrent 401s refresh once

  Future<String?> _tryRefresh() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<String?> _doRefresh() async {
    final refresh = await _store.getRefresh();
    if (refresh == null || refresh.isEmpty) return null;
    try {
      final bare = Dio(BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.apiTimeout,
        contentType: Headers.jsonContentType,
      ));
      // Também aqui: a renovação do token acontece a meio de outra coisa, e
      // um aperto de mão TLS extra nesse momento é tempo que o agente sente.
      _reaproveitarLigacoes(bare);
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
    // Daqui para baixo não há mensagem do servidor para mostrar: ou ele não
    // respondeu, ou respondeu algo que não é um erro nosso (uma página HTML do
    // nginx, por exemplo). O agente tem um passageiro à frente — precisa de
    // saber o que fazer, não de ler o nome de uma classe do Dart.
    //
    // Antes acabava em `'Erro : ${e.message}'`, que punha "DioException
    // [bad response]: ..." no ecrã. Isso não é uma mensagem: é um despejo.
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'O servidor demorou a responder. Verifique a rede e tente de novo.';
      case DioExceptionType.connectionError:
        return 'Sem ligação ao servidor. Verifique a internet do terminal.';
      case DioExceptionType.badCertificate:
        return 'Ligação ao servidor não confiável. Contacte o suporte.';
      case DioExceptionType.cancel:
        return 'Operação cancelada.';
      case DioExceptionType.badResponse:
      case DioExceptionType.unknown:
        break;
    }
    final codigo = e.response?.statusCode;
    if (codigo == null) {
      return 'Não foi possível falar com o servidor. Tente de novo.';
    }
    // Os códigos que o agente pode mesmo resolver, ditos por palavras.
    return switch (codigo) {
      401 || 403 => 'Sessão expirada ou sem permissão. Entre de novo.',
      404 => 'Não encontrado. Actualize e tente de novo.',
      409 => 'Este pedido já não é válido. Actualize e tente de novo.',
      >= 500 => 'O servidor falhou a responder ($codigo). '
          'Se continuar, contacte o suporte.',
      _ => 'Não foi possível concluir a operação (erro $codigo). Tente de novo.',
    };
  }
}
