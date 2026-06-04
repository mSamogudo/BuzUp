import 'package:dio/dio.dart' show DioException, Options;

import 'api_client.dart';

/// Maps each backend endpoint under /api/agent/* to a Dart method.
/// Returns raw JSON maps; feature layers convert into models.
class AgentApi {
  AgentApi(this._http);

  final ApiClient _http;

  // ----- App update (OTA) -----

  /// Asks the backend whether a newer published POS release exists.
  /// Public endpoint; returns {update_available, version_name, version_code,
  /// is_mandatory, release_notes, download_url, ...}.
  Future<Map<String, dynamic>> checkUpdate({
    required int currentVersionCode,
    String? deviceType,
    String? manufacturer,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/app-releases/check/',
      data: {
        'app_type': 'pos',
        'current_version_code': currentVersionCode,
        if (deviceType != null && deviceType.isNotEmpty) 'device_type': deviceType,
        if (manufacturer != null && manufacturer.isNotEmpty) 'manufacturer': manufacturer,
      },
    );
    return res.data ?? const {};
  }

  // ----- Auth -----
  Future<Map<String, dynamic>> login({
    String? username,
    String? password,
    String? phone,
    String? otpCode,
    String? challengeId,
    String? deviceSerial,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/auth/login/',
      data: {
        if (username != null) 'username': username,
        if (password != null) 'password': password,
        if (phone != null) 'phone': phone,
        if (otpCode != null) 'otp_code': otpCode,
        if (challengeId != null) 'challenge_id': challengeId,
        if (deviceSerial != null) 'device_serial': deviceSerial,
      },
    );
    return res.data ?? const {};
  }

  // ----- Device onboarding -----
  Future<Map<String, dynamic>> selfOnboard({
    required String serialNumber,
    String? deviceType,
    String? modelName,
    String? manufacturer,
    String? androidId,
    String? appVersion,
    List<String>? capabilities,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/devices/self-onboard/',
      data: {
        'serial_number': serialNumber,
        if (deviceType != null) 'device_type': deviceType,
        if (modelName != null) 'model_name': modelName,
        if (manufacturer != null) 'manufacturer': manufacturer,
        if (androidId != null) 'android_id': androidId,
        if (appVersion != null) 'app_version': appVersion,
        if (capabilities != null) 'capabilities': capabilities,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> deviceStatus(String serial) async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/devices/status/$serial/');
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> activateDevice({required String serial, required String code}) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/devices/activate/',
      data: {'serial_number': serial, 'activation_code': code},
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> dayClosePreview() async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/day-close/');
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> dayClose() async {
    final res = await _http.post<Map<String, dynamic>>('/api/agent/day-close/');
    return res.data ?? const {};
  }

  Future<void> logout(String refresh) async {
    await _http.post('/api/agent/auth/logout/', data: {'refresh': refresh});
  }

  Future<Map<String, dynamic>> me() async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/me/');
    return res.data ?? const {};
  }

  // ----- Device -----
  Future<Map<String, dynamic>> registerDevice({
    required String serialNumber,
    String? deviceType,
    String? modelName,
    String? manufacturer,
    String? imei,
    String? androidId,
    String? appVersion,
    int? appVersionCode,
    List<String>? capabilities,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/devices/register/',
      data: {
        'serial_number': serialNumber,
        if (deviceType != null) 'device_type': deviceType,
        if (modelName != null) 'model_name': modelName,
        if (manufacturer != null) 'manufacturer': manufacturer,
        if (imei != null) 'imei': imei,
        if (androidId != null) 'android_id': androidId,
        if (appVersion != null) 'app_version': appVersion,
        if (appVersionCode != null) 'app_version_code': appVersionCode,
        if (capabilities != null) 'capabilities': capabilities,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>?> currentDevice() async {
    try {
      final res = await _http.get<Map<String, dynamic>>('/api/agent/devices/current/');
      return res.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<void> heartbeat({String? serialNumber, double? latitude, double? longitude, String? appVersion}) async {
    await _http.post(
      '/api/agent/devices/heartbeat/',
      data: {
        if (serialNumber != null) 'serial_number': serialNumber,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
        if (appVersion != null) 'app_version': appVersion,
      },
    );
  }

  // ----- Trips -----
  Future<List<dynamic>> trips({int? routeId}) async {
    final res = await _http.get<List<dynamic>>(
      '/api/agent/trips/',
      query: routeId != null ? {'route': routeId} : null,
    );
    return res.data ?? const [];
  }

  Future<Map<String, dynamic>> trip(int tripId) async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/trips/$tripId/');
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> quoteFare({
    required int tripId,
    required int originStopId,
    required int destinationStopId,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/trips/$tripId/fare/',
      data: {
        'origin_stop_id': originStopId,
        'destination_stop_id': destinationStopId,
      },
    );
    return res.data ?? const {};
  }

  // ----- Sales / Payments -----
  Future<Map<String, dynamic>> createSale({
    required int tripId,
    required int originStopId,
    required int destinationStopId,
    String paymentMethod = 'mobile_money',
    String? passengerPhone,
    String? cardUid,
    String? qrToken,
    int quantity = 1,
    String? deviceSerial,
    bool autoRequestPayment = true,
    String? idempotencyKey,
  }) async {
    final headers = <String, String>{};
    if (idempotencyKey != null && idempotencyKey.isNotEmpty) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/sales/',
      data: {
        'trip_id': tripId,
        'origin_stop_id': originStopId,
        'destination_stop_id': destinationStopId,
        'payment_method': paymentMethod,
        if (passengerPhone != null && passengerPhone.isNotEmpty) 'passenger_phone': passengerPhone,
        if (cardUid != null && cardUid.isNotEmpty) 'card_uid': cardUid,
        if (qrToken != null && qrToken.isNotEmpty) 'qr_token': qrToken,
        'quantity': quantity,
        if (deviceSerial != null) 'device_serial': deviceSerial,
        'auto_request_payment': autoRequestPayment,
      },
      options: headers.isEmpty ? null : Options(headers: headers),
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> paymentStatus(String reference) async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/payments/$reference/status/');
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> salesHistory({String? since}) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/agent/sales/history/',
      query: since != null ? {'since': since} : null,
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> salesSummary({String? date}) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/agent/sales/summary/',
      query: date != null ? {'date': date} : null,
    );
    return res.data ?? const {};
  }

  // ----- Tickets -----
  Future<Map<String, dynamic>> ticketDetail(String ref) async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/tickets/$ref/');
    return res.data ?? const {};
  }

  Future<List<int>> ticketPdf(String ref) async {
    final res = await _http.download('/api/agent/tickets/$ref/pdf/');
    return res.data ?? const <int>[];
  }

  Future<Map<String, dynamic>> verifyTicket(String token, {bool consume = true}) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/tickets/verify/',
      data: {'token': token, 'consume': consume},
    );
    return res.data ?? const {};
  }

  /// Verify by shortcode (last 4 chars of GuestCheckout reference).
  Future<Map<String, dynamic>> verifyTicketByShortcode(String shortcode, {bool consume = true}) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/tickets/verify/',
      data: {'shortcode': shortcode.toUpperCase(), 'consume': consume},
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> markTicketUsed(String ref) async {
    final res = await _http.post<Map<String, dynamic>>('/api/agent/tickets/$ref/mark-used/');
    return res.data ?? const {};
  }

  // ----- Cards / wallet / packages -----

  Future<Map<String, dynamic>> cardLookup({String? cardUid, String? qrToken}) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/cards/lookup/',
      data: {
        if (cardUid != null) 'card_uid': cardUid,
        if (qrToken != null) 'qr_token': qrToken,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> walletTopup({
    String? cardUid,
    String? qrToken,
    required String amount,
    required String method, // cash | mobile_money
    String? payerPhone,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/topups/wallet/',
      data: {
        if (cardUid != null) 'card_uid': cardUid,
        if (qrToken != null) 'qr_token': qrToken,
        'amount': amount,
        'method': method,
        if (payerPhone != null) 'payer_phone': payerPhone,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> packageTopup({
    String? cardUid,
    String? qrToken,
    required int packageId,
    required String method,
    String? payerPhone,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/topups/package/',
      data: {
        if (cardUid != null) 'card_uid': cardUid,
        if (qrToken != null) 'qr_token': qrToken,
        'package_id': packageId,
        'method': method,
        if (payerPhone != null) 'payer_phone': payerPhone,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> walletDebit({
    String? cardUid,
    String? qrToken,
    required String amount,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/payments/wallet/',
      data: {
        if (cardUid != null) 'card_uid': cardUid,
        if (qrToken != null) 'qr_token': qrToken,
        'amount': amount,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> captureCardUid({
    required String cardUid,
    String? batch,
    String? manufacturer,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/cards/capture-uid/',
      data: {
        'card_uid': cardUid,
        if (batch != null && batch.isNotEmpty) 'batch': batch,
        if (manufacturer != null && manufacturer.isNotEmpty) 'manufacturer': manufacturer,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> onboardPassenger({
    required String fullName,
    required String phone,
    String? email,
    String? documentType,
    String? documentNumber,
    String? cardUid,
    String? qrToken,
    required String payerPhone,
    String? fee,
    bool notifySms = true,
    String? deviceSerial,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/passengers/onboard/',
      data: {
        'full_name': fullName,
        'phone': phone,
        if (email != null && email.isNotEmpty) 'email': email,
        if (documentType != null && documentType.isNotEmpty) 'document_type': documentType,
        if (documentNumber != null && documentNumber.isNotEmpty) 'document_number': documentNumber,
        if (cardUid != null && cardUid.isNotEmpty) 'card_uid': cardUid,
        if (qrToken != null && qrToken.isNotEmpty) 'qr_token': qrToken,
        'payer_phone': payerPhone,
        if (fee != null && fee.isNotEmpty) 'fee': fee,
        'notify_sms': notifySms,
        if (deviceSerial != null && deviceSerial.isNotEmpty) 'device_serial': deviceSerial,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> recoverCardRequestOtp({
    required String passengerPhone,
    String? reason,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/passengers/recover-card/request-otp/',
      data: {
        'passenger_phone': passengerPhone,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> recoverCardVerifyOtp({
    required String challengeId,
    required String otpCode,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/passengers/recover-card/verify-otp/',
      data: {'challenge_id': challengeId, 'otp_code': otpCode},
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> recoverCardAssociate({
    required String recoveryToken,
    String? newCardUid,
    String? newQrToken,
    required String payerPhone,
    String? feeAmount,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/passengers/recover-card/associate/',
      data: {
        'recovery_token': recoveryToken,
        if (newCardUid != null && newCardUid.isNotEmpty) 'new_card_uid': newCardUid,
        if (newQrToken != null && newQrToken.isNotEmpty) 'new_qr_token': newQrToken,
        'payer_phone': payerPhone,
        if (feeAmount != null && feeAmount.isNotEmpty) 'fee_amount': feeAmount,
      },
    );
    return res.data ?? const {};
  }

  Future<Map<String, dynamic>> validateCard({
    String? cardUid,
    String? qrToken,
    int? routeId,
    int? tripId,
    int? originStopId,
    int? destinationStopId,
    String? deviceSerial,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/agent/validations/card/',
      data: {
        if (cardUid != null && cardUid.isNotEmpty) 'card_uid': cardUid,
        if (qrToken != null && qrToken.isNotEmpty) 'qr_token': qrToken,
        if (routeId != null) 'route_id': routeId,
        if (tripId != null) 'trip_id': tripId,
        if (originStopId != null) 'origin_stop_id': originStopId,
        if (destinationStopId != null) 'destination_stop_id': destinationStopId,
        if (deviceSerial != null && deviceSerial.isNotEmpty) 'device_serial': deviceSerial,
      },
    );
    return res.data ?? const {};
  }

  Future<List<Map<String, dynamic>>> listPackages() async {
    final res = await _http.get<Map<String, dynamic>>('/api/agent/packages/');
    final results = (res.data?['results'] as List?) ?? const [];
    return results.cast<Map<String, dynamic>>();
  }
}
