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
  return ref.watch(agentApiProvider).me();
});

/// Feature flags exposed by the backend `/api/agent/me/` payload. Drives
/// production gating (e.g. capture-uid is hidden in prod).
final agentFeaturesProvider = FutureProvider<Map<String, bool>>((ref) async {
  final me = await ref.watch(agentMeProvider.future);
  final feats = (me['features'] as Map?)?.cast<String, dynamic>() ?? const {};
  return feats.map((k, v) => MapEntry(k, v == true));
});
