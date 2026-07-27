import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'agent_api.dart';
import 'api_client.dart';
import 'storage.dart';

final secureStoreProvider = Provider<SecureStore>((ref) => SecureStore());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(secureStoreProvider));
});

final agentApiProvider = Provider<AgentApi>((ref) {
  return AgentApi(ref.watch(apiClientProvider));
});

/// Whether the app currently has a stored access token.
final isLoggedInProvider = FutureProvider<bool>((ref) async {
  final tok = await ref.watch(secureStoreProvider).getAccess();
  return tok != null && tok.isNotEmpty;
});

/// Current /me payload.
final agentMeProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final serial = await ref.watch(secureStoreProvider).getDeviceSerial();
  return ref.watch(agentApiProvider).me(serial: serial);
});

/// Feature flags exposed by the backend `/api/agent/me/` payload. Drives
/// production gating (e.g. capture-uid is hidden in prod).
final agentFeaturesProvider = FutureProvider<Map<String, bool>>((ref) async {
  final me = await ref.watch(agentMeProvider.future);
  final feats = (me['features'] as Map?)?.cast<String, dynamic>() ?? const {};
  return feats.map((k, v) => MapEntry(k, v == true));
});

/// Whether the logged-in user also has an active driver profile. Falls back
/// to the value stored at login so the home renders right on first frame.
final isDriverProvider = FutureProvider<bool>((ref) async {
  try {
    final me = await ref.watch(agentMeProvider.future);
    return me['driver'] != null;
  } catch (_) {
    return await ref.watch(secureStoreProvider).getDriverId() != null;
  }
});

/// Estados em que uma viagem conta como "em mao" para o motorista.
const kActiveTripStatuses = {'boarding', 'departed', 'paused'};

/// Viagens alocadas ao motorista (scheduled/boarding/departed/paused).
final driverTripsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final raw = await ref.watch(agentApiProvider).driverTrips();
  return raw.whereType<Map>().map((e) => e.cast<String, dynamic>()).toList();
});

/// A viagem activa do motorista, se existir.
final activeDriverTripProvider = FutureProvider<Map<String, dynamic>?>((ref) async {
  final trips = await ref.watch(driverTripsProvider.future);
  for (final t in trips) {
    if (kActiveTripStatuses.contains(t['status'])) return t;
  }
  return null;
});

/// A proxima viagem agendada do motorista, se existir.
final nextDriverTripProvider = FutureProvider<Map<String, dynamic>?>((ref) async {
  final trips = await ref.watch(driverTripsProvider.future);
  final scheduled = trips.where((t) => t['status'] == 'scheduled').toList()
    ..sort((a, b) => (a['planned_departure_at'] ?? '').toString().compareTo((b['planned_departure_at'] ?? '').toString()));
  return scheduled.isEmpty ? null : scheduled.first;
});
