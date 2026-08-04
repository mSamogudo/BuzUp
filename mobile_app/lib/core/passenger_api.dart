import 'package:dio/dio.dart' show Options;

import 'api_client.dart';

/// Maps each passenger-facing backend endpoint to a Dart method.
class PassengerApi {
  PassengerApi(this._http);
  final ApiClient _http;

  // ----- App update (OTA) -----

  /// Asks the backend whether a newer published release exists for this app.
  /// Public endpoint; returns {update_available, version_name, version_code,
  /// is_mandatory, release_notes, download_url, ...}.
  Future<Map<String, dynamic>> checkUpdate({required int currentVersionCode}) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/app-releases/check/',
      data: {'app_type': 'passenger', 'current_version_code': currentVersionCode},
    );
    return res.data ?? const {};
  }

  // ----- OTP login -----

  /// Checks whether a phone already has an account before sending an OTP.
  /// Returns `{exists: bool, role: 'passenger'|'driver'|'agent'|null}`.
  /// Lets the app show a quick registration form to brand-new passengers.
  Future<Map<String, dynamic>> checkPhone(String phone) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/passenger/check/',
      data: {'phone': phone},
    );
    return res.data ?? const {};
  }

  /// Send the 6-digit OTP via SMS. Returns the challenge id needed for verify.
  Future<Map<String, dynamic>> requestOtp(String phone) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/otp/request/',
      data: {'phone': phone},
    );
    return res.data ?? const {};
  }

  /// Verify the OTP code. Returns access+refresh tokens on success.
  /// Backend expects keys: challenge_id, code, phone (full ITU like 258840000000).
  Future<Map<String, dynamic>> verifyOtp({
    required String challengeId,
    required String code,
    required String phone,
    String? fullName,
    String? email,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/otp/verify/',
      data: {
        'challenge_id': challengeId,
        'code': code,
        'phone': phone,
        if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
        if (email != null && email.isNotEmpty) 'email': email,
      },
    );
    return res.data ?? const {};
  }

  // ----- Portal data -----

  /// Returns the full passenger portal payload (wallet, card, packages, etc.)
  Future<Map<String, dynamic>> me() async {
    final res = await _http.get<Map<String, dynamic>>('/api/auth/me/passenger-portal/');
    return res.data ?? const {};
  }

  /// Updates the passenger's editable profile fields (name + email).
  Future<Map<String, dynamic>> updateProfile({
    required String fullName,
    String? email,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/',
      data: {
        'full_name': fullName,
        if (email != null) 'email': email,
      },
      options: Options(method: 'PATCH'),
    );
    return res.data ?? const {};
  }

  /// Polls the status of a passenger's own pending PaymentIntent.
  Future<Map<String, dynamic>> paymentStatus(String reference) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/payments/$reference/status/',
    );
    return res.data ?? const {};
  }

  Future<List<Map<String, dynamic>>> transactions({int? limit}) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/transactions/',
      query: limit != null ? {'limit': limit} : null,
    );
    final results = (res.data?['results'] as List?) ?? const [];
    return results.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> transactionDetail(int txId) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/transactions/$txId/',
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> topup({
    required String amount,
    required String payerPhone,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/topup/',
      data: {'amount': amount, 'payer_phone': payerPhone},
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> subscribePackage(int packageId) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/packages/subscribe/',
      data: {'package_id': packageId},
    );
    return res.data ?? const {};
  }

  // ----- Tickets (travel passes) -----

  // ----- Mapa de rastreio -----

  /// Posicoes das viaturas com viagem activa (para o mapa).
  Future<Map<String, dynamic>> vehicleLocations() async {
    final res = await _http.get<Map<String, dynamic>>('/api/mobile/vehicles/locations/');
    return res.data ?? const {};
  }

  /// Paragens ordenadas de uma rota (lat/lng) para desenhar a polyline.
  Future<Map<String, dynamic>> routeGeometry(int routeId) async {
    final res = await _http.get<Map<String, dynamic>>('/api/mobile/routes/$routeId/geometry/');
    return res.data ?? const {};
  }

  /// Public list of routes + stops + active trips. Used by the buy-ticket flow.
  Future<Map<String, dynamic>> publicTrips({int? routeId}) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/public/trips/',
      query: routeId != null ? {'route_id': routeId} : null,
    );
    return res.data ?? const {};
  }

  /// Partidas publicas para um par origem/destino numa data. Usado quando a
  /// rota marca lugar: o passageiro escolhe a partida antes do assento.
  Future<List<Map<String, dynamic>>> searchDepartures({
    required int originStopId,
    required int destinationStopId,
    required String date,
  }) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/public/trips/',
      query: {
        'origin': originStopId,
        'destination': destinationStopId,
        'date': date,
      },
    );
    final items = (res.data?['trips'] as List?) ?? const [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// Planta de lugares de uma partida, com os ja ocupados.
  Future<Map<String, dynamic>> tripSeats(int tripId) async {
    final res = await _http.get<Map<String, dynamic>>('/api/public/trips/$tripId/seats/');
    return res.data ?? const {};
  }

  /// Quote a fare without committing: returns amount, discount, package usage.
  /// `routeId` is optional — the backend infers the route from origin+destination.
  Future<Map<String, dynamic>> quoteTicket({
    int? routeId,
    int? originStopId,
    int? destinationStopId,
    int? tripId,
    int? passengerPackageId,
    bool usePackage = true,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/travel-passes/quote/',
      data: {
        if (routeId != null) 'route_id': routeId,
        if (originStopId != null) 'origin_stop_id': originStopId,
        if (destinationStopId != null) 'destination_stop_id': destinationStopId,
        if (tripId != null) 'trip_id': tripId,
        if (passengerPackageId != null) 'passenger_package_id': passengerPackageId,
        'use_package': usePackage,
      },
    );
    return res.data ?? const {};
  }

  /// Commit the ticket purchase. Wallet/package is debited and a
  /// DigitalTravelPass is issued (`id`, `token` for QR, `route_*`, etc.).
  Future<Map<String, dynamic>> purchaseTicket({
    int? routeId,
    int? originStopId,
    int? destinationStopId,
    int? tripId,
    String? seat,
    int? passengerPackageId,
    bool usePackage = true,
    String displayCurrency = 'MZN',
    String? emergencyName,
    String? emergencyPhone,
    String documentType = '',
    String documentNumber = '',
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/travel-passes/purchase/',
      data: {
        if (routeId != null) 'route_id': routeId,
        if (originStopId != null) 'origin_stop_id': originStopId,
        if (destinationStopId != null) 'destination_stop_id': destinationStopId,
        if (tripId != null) 'trip_id': tripId,
        if (seat != null && seat.isNotEmpty) 'seat': seat,
        if (passengerPackageId != null) 'passenger_package_id': passengerPackageId,
        if (emergencyName != null && emergencyName.isNotEmpty)
          'emergency_contact_name': emergencyName,
        if (emergencyPhone != null && emergencyPhone.isNotEmpty)
          'emergency_contact_phone': emergencyPhone,
        // O bilhete das rotas com lugar marcado e nominal: sem o documento
        // sai com o campo vazio e nao serve na fronteira.
        if (documentType.isNotEmpty) 'document_type': documentType,
        if (documentNumber.isNotEmpty) 'document_number': documentNumber,
        'use_package': usePackage,
        'display_currency': displayCurrency,
      },
    );
    return res.data ?? const {};
  }

  /// Bilhete de curta duracao para abrir um ficheiro protegido por link.
  ///
  /// O browser do sistema nao envia o cabecalho `Authorization`, por isso o
  /// acesso tem de ir no URL. O que ia antes era o token de acesso completo —
  /// e um URL fica gravado no log do servidor e no historico do browser. O
  /// bilhete vale minutos e so serve para aquele tipo de ficheiro.
  Future<String> downloadTicket(String scope) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/auth/download-ticket/',
      data: {'scope': scope},
    );
    return (res.data?['ticket'] ?? '').toString();
  }

  /// Taxas de cambio de exibicao configuradas no portal (ex.: {"ZAR": "4.10"}).
  /// A cobranca e sempre em MZN — isto so alimenta a visualizacao de precos.
  Future<Map<String, dynamic>> exchangeRates() async {
    final res = await _http.get<Map<String, dynamic>>('/api/public/exchange-rate/');
    return res.data ?? const {};
  }

  /// Formatos aceites de documento de identificacao, tal como o servidor os
  /// valida. A app le daqui em vez de os ter escritos outra vez em Dart.
  Future<List<Map<String, dynamic>>> documentTypes() async {
    final res = await _http.get<Map<String, dynamic>>('/api/public/document-types/');
    final items = (res.data?['document_types'] as List?) ?? const [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// Compra directa com M-Pesa/e-Mola (sem passar pela carteira): cria um
  /// checkout ligado a conta autenticada e dispara o pedido de PIN no numero
  /// indicado. Devolve {checkout_reference, status, payment_status, ...}.
  Future<Map<String, dynamic>> directCheckout({
    required int originStopId,
    required int destinationStopId,
    required String originName,
    required String destinationName,
    required String payerPhone,
    int? tripId,
    String? seat,
    String displayCurrency = 'MZN',
    String? emergencyName,
    String? emergencyPhone,
    String passengerName = '',
    String documentType = '',
    String documentNumber = '',
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/guest-checkouts/',
      data: {
        'payer_phone': payerPhone,
        if (passengerName.isNotEmpty) 'buyer_name': passengerName,
        'origin_stop': originName,
        'destination_stop': destinationName,
        'origin_stop_id': originStopId,
        'destination_stop_id': destinationStopId,
        'quantity': 1,
        if (tripId != null) 'trip_id': tripId,
        // O bilhete das rotas com lugar marcado e NOMINAL: o servidor exige
        // o nome do passageiro. Sem isto a compra por M-Pesa/e-Mola numa
        // rota interprovincial era recusada.
        if (seat != null && seat.isNotEmpty)
          'passengers': [
            {
              'seat': seat,
              'name': passengerName,
              if (documentType.isNotEmpty) 'document_type': documentType,
              if (documentNumber.isNotEmpty) 'document_number': documentNumber,
            }
          ],
        if (emergencyName != null && emergencyName.isNotEmpty)
          'emergency_contact_name': emergencyName,
        if (emergencyPhone != null && emergencyPhone.isNotEmpty)
          'emergency_contact_phone': emergencyPhone,
        'display_currency': displayCurrency,
      },
    );
    return res.data ?? const {};
  }

  /// Estado de um checkout directo ({status, passes: [...]}) para fazer
  /// polling enquanto o passageiro confirma o PIN na carteira movel.
  Future<Map<String, dynamic>> checkoutStatus(String reference) async {
    final res = await _http.get<Map<String, dynamic>>('/api/guest-checkouts/$reference/');
    return res.data ?? const {};
  }

  Future<List<Map<String, dynamic>>> myTickets({String? statusFilter, int? limit}) async {
    final query = <String, dynamic>{};
    if (statusFilter != null && statusFilter.isNotEmpty) query['status_filter'] = statusFilter;
    if (limit != null) query['limit'] = limit;
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/tickets/',
      query: query.isEmpty ? null : query,
    );
    final results = (res.data?['results'] as List?) ?? const [];
    return results.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> ticketDetail(int ticketId) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/tickets/$ticketId/',
    );
    return res.data ?? const {};
  }

  Future<List<Map<String, dynamic>>> adminFees() async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/auth/me/passenger-portal/admin-fees/',
    );
    final results = (res.data?['results'] as List?) ?? const [];
    return results.cast<Map<String, dynamic>>();
  }
}
