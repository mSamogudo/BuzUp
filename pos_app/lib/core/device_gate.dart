import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers.dart';

/// Polls the backend every [pollInterval] for the current device status.
/// When status leaves "active", redirects the user to /onboarding.
///
/// Wrap any authenticated screen (home, sale, verify, ...) with this widget
/// so the device acts as a hard gate: portal admin can revoke a POS at any
/// time and the app reacts immediately.
class DeviceGate extends ConsumerStatefulWidget {
  const DeviceGate({super.key, required this.child, this.pollInterval = const Duration(seconds: 30)});

  final Widget child;
  final Duration pollInterval;

  @override
  ConsumerState<DeviceGate> createState() => _DeviceGateState();
}

class _DeviceGateState extends ConsumerState<DeviceGate> with WidgetsBindingObserver {
  Timer? _timer;
  bool _checked = false;
  bool _gateOpen = true;
  String? _lastStatus;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(_check);
    _timer = Timer.periodic(widget.pollInterval, (_) => _check());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _check();
  }

  Future<void> _check() async {
    final serial = await ref.read(secureStoreProvider).getDeviceSerial();
    if (serial == null) {
      _redirectOut();
      return;
    }
    try {
      final res = await ref.read(agentApiProvider).deviceStatus(serial);
      final status = (res['status'] as String?) ?? '';
      final isActive = status == 'active';
      _lastStatus = status;
      if (!mounted) return;

      if (!isActive) {
        // Device was de-activated/blocked: kick the user out.
        final store = ref.read(secureStoreProvider);
        final keepSerial = serial;
        await store.clearAll();
        await store.saveDeviceSerial(keepSerial);
        ref.invalidate(isLoggedInProvider);

        setState(() => _gateOpen = false);
        if (!_checked) {
          _checked = true;
          // First check finished -> route accordingly.
          final route = status == 'pending_activation' ? '/activation-code' : '/onboarding';
          if (mounted) context.go(route);
        } else {
          // Subsequent check: device was revoked while using.
          final route = status == 'pending_activation' ? '/activation-code' : '/onboarding';
          if (mounted) context.go(route);
        }
      } else {
        setState(() {
          _gateOpen = true;
          _checked = true;
        });
      }
    } catch (_) {
      // network errors don't immediately revoke - keep current state.
      setState(() => _checked = true);
    }
  }

  void _redirectOut() {
    if (!mounted) return;
    context.go('/onboarding');
  }

  @override
  Widget build(BuildContext context) {
    if (!_checked) {
      return Scaffold(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (!_gateOpen) {
      return Scaffold(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    return widget.child;
  }
}
