import 'package:dio/dio.dart' show Options;

import 'api_client.dart';

/// Maps each passenger-facing backend endpoint to a Dart method.
class PassengerApi {
  PassengerApi(this._http);
  final ApiClient _http;

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

  /// Public list of routes + stops + active trips. Used by the buy-ticket flow.
  Future<Map<String, dynamic>> publicTrips({int? routeId}) async {
    final res = await _http.get<Map<String, dynamic>>(
      '/api/public/trips/',
      query: routeId != null ? {'route_id': routeId} : null,
    );
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
    int? passengerPackageId,
    bool usePackage = true,
  }) async {
    final res = await _http.post<Map<String, dynamic>>(
      '/api/travel-passes/purchase/',
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
