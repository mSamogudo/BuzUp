import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../core/i18n.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Posições das viaturas em viagem (poll 15s). Fonte: `/api/mobile/vehicles/
/// locations/` — só autocarros com viagem activa e GPS fresco (<10 min).
final vehicleLocationsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final res = await ref.watch(passengerApiProvider).vehicleLocations();
  return ((res['results'] as List?) ?? const [])
      .whereType<Map>()
      .map((e) => e.cast<String, dynamic>())
      .toList();
});

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> with WidgetsBindingObserver {
  static const _maputo = LatLng(-25.9692, 32.5732);
  static const _pollInterval = Duration(seconds: 15);

  final _map = MapController();
  final _searchCtrl = TextEditingController();
  Timer? _poll;
  int? _focusedTripId;
  LatLng? _myLocation;
  List<LatLng> _routeLine = const [];
  int? _routeLineRouteId;
  String _query = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _startPolling();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  // O poll para quando a app vai para background (poupa bateria e servidor).
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _startPolling();
      ref.invalidate(vehicleLocationsProvider);
    } else {
      _poll?.cancel();
      _poll = null;
    }
  }

  void _startPolling() {
    _poll ??= Timer.periodic(_pollInterval, (_) => ref.invalidate(vehicleLocationsProvider));
  }

  Future<void> _loadRouteLine(int routeId) async {
    if (_routeLineRouteId == routeId) return;
    try {
      final geo = await ref.read(passengerApiProvider).routeGeometry(routeId);
      final pts = ((geo['stops'] as List?) ?? const [])
          .whereType<Map>()
          .where((s) => s['latitude'] != null && s['longitude'] != null)
          .map((s) => LatLng((s['latitude'] as num).toDouble(), (s['longitude'] as num).toDouble()))
          .toList();
      if (mounted) {
        setState(() {
          _routeLine = pts;
          _routeLineRouteId = routeId;
        });
      }
    } catch (_) {
      // Sem geometria (paragens sem coordenadas): mostra só o pin.
    }
  }

  void _focusBus(Map<String, dynamic> bus) {
    setState(() => _focusedTripId = bus['trip_id'] as int?);
    final routeId = bus['route_id'] as int?;
    if (routeId != null) _loadRouteLine(routeId);
    _map.move(LatLng((bus['latitude'] as num).toDouble(), (bus['longitude'] as num).toDouble()), 15);
    _showBusSheet(bus);
  }

  Future<void> _goToMyLocation() async {
    final tr = ref.read(trProvider);
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('track.locationDenied'))));
      }
      return;
    }
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      ).timeout(const Duration(seconds: 8));
      if (!mounted) return;
      setState(() => _myLocation = LatLng(pos.latitude, pos.longitude));
      _map.move(_myLocation!, 15);
    } catch (_) {}
  }

  bool _matches(Map<String, dynamic> bus) {
    if (_query.isEmpty) return true;
    final q = _query.toLowerCase();
    return [bus['route_code'], bus['route_name'], bus['vehicle_registration']]
        .any((v) => (v ?? '').toString().toLowerCase().contains(q));
  }

  String _ago(String? iso) {
    final t = DateTime.tryParse(iso ?? '');
    if (t == null) return '—';
    final d = DateTime.now().difference(t.toLocal());
    if (d.inSeconds < 60) return 'ha ${d.inSeconds}s';
    if (d.inMinutes < 60) return 'ha ${d.inMinutes} min';
    return 'ha ${d.inHours}h';
  }

  void _showBusSheet(Map<String, dynamic> bus) {
    final tr = ref.read(trProvider);
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: BuzUpColors.orange.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.directions_bus, color: BuzUpColors.orange),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${bus['route_code'] ?? ''} · ${bus['route_name'] ?? ''}',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                    overflow: TextOverflow.ellipsis),
                if ((bus['vehicle_registration'] ?? '').toString().isNotEmpty)
                  Text('${tr('track.vehicle')}: ${bus['vehicle_registration']}',
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
              ]),
            ),
          ]),
          const SizedBox(height: 16),
          Row(children: [
            _stat(tr('track.speed'),
                bus['speed_kmh'] == null ? '—' : '${(bus['speed_kmh'] as num).toStringAsFixed(0)} km/h'),
            const SizedBox(width: 10),
            _stat(tr('track.updated'), _ago(bus['updated_at']?.toString())),
          ]),
        ]),
      ),
    );
  }

  Widget _stat(String label, String value) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.grey.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final busesAsync = ref.watch(vehicleLocationsProvider);
    final buses = (busesAsync.valueOrNull ?? const <Map<String, dynamic>>[]).where(_matches).toList();

    return Scaffold(
      body: Stack(children: [
        FlutterMap(
          mapController: _map,
          options: MapOptions(
            initialCenter: buses.isNotEmpty
                ? LatLng((buses.first['latitude'] as num).toDouble(), (buses.first['longitude'] as num).toDouble())
                : _maputo,
            initialZoom: 13,
            maxZoom: 19,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
              subdomains: const ['a', 'b', 'c', 'd'],
              retinaMode: RetinaMode.isHighDensity(context),
              maxNativeZoom: 20,
              userAgentPackageName: 'mz.coupdigital.buzup_mobile',
            ),
            if (_routeLine.length > 1 && _focusedTripId != null)
              PolylineLayer(polylines: [
                Polyline(points: _routeLine, strokeWidth: 5, color: BuzUpColors.blue.withValues(alpha: 0.55)),
              ]),
            if (_routeLine.isNotEmpty && _focusedTripId != null)
              MarkerLayer(markers: [
                for (final p in _routeLine)
                  Marker(point: p, width: 14, height: 14, child: _StopDot()),
              ]),
            MarkerLayer(markers: [
              if (_myLocation != null)
                Marker(point: _myLocation!, width: 24, height: 24, child: const _UserDot()),
              for (final bus in buses)
                Marker(
                  point: LatLng((bus['latitude'] as num).toDouble(), (bus['longitude'] as num).toDouble()),
                  width: bus['trip_id'] == _focusedTripId ? 54 : 44,
                  height: bus['trip_id'] == _focusedTripId ? 54 : 44,
                  child: GestureDetector(
                    onTap: () => _focusBus(bus),
                    child: _BusPin(
                      focused: bus['trip_id'] == _focusedTripId,
                      heading: (bus['heading'] as num?)?.toDouble(),
                    ),
                  ),
                ),
            ]),
          ],
        ),
        // Barra de pesquisa + contagem
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Column(children: [
              Material(
                elevation: 3,
                borderRadius: BorderRadius.circular(14),
                child: TextField(
                  controller: _searchCtrl,
                  onChanged: (v) => setState(() => _query = v.trim()),
                  decoration: InputDecoration(
                    hintText: tr('track.searchHint'),
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() => _query = '');
                            },
                          ),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                    filled: true,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.92),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    busesAsync.isLoading && buses.isEmpty
                        ? '...'
                        : busesAsync.hasError
                            ? tr('track.loadError')
                            : buses.isEmpty
                                ? tr('track.none')
                                : '${buses.length} ${tr('track.live')} · ${tr('track.tapHint')}',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ]),
          ),
        ),
        // Controlos
        Positioned(
          right: 14,
          bottom: 24,
          child: Column(children: [
            _mapBtn(Icons.add, () => _map.move(_map.camera.center, _map.camera.zoom + 1)),
            const SizedBox(height: 8),
            _mapBtn(Icons.remove, () => _map.move(_map.camera.center, _map.camera.zoom - 1)),
            const SizedBox(height: 8),
            _mapBtn(Icons.my_location, _goToMyLocation),
            const SizedBox(height: 8),
            _mapBtn(Icons.refresh, () => ref.invalidate(vehicleLocationsProvider)),
          ]),
        ),
      ]),
    );
  }

  Widget _mapBtn(IconData icon, VoidCallback onTap) {
    return Material(
      elevation: 3,
      shape: const CircleBorder(),
      color: Theme.of(context).colorScheme.surface,
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: Padding(padding: const EdgeInsets.all(11), child: Icon(icon, size: 21)),
      ),
    );
  }
}

class _BusPin extends StatelessWidget {
  const _BusPin({required this.focused, this.heading});

  final bool focused;
  final double? heading;

  @override
  Widget build(BuildContext context) {
    final color = focused ? BuzUpColors.success : BuzUpColors.blue;
    final icon = heading != null
        ? Transform.rotate(
            angle: heading! * 3.14159265 / 180,
            child: const Icon(Icons.navigation, color: Colors.white, size: 20),
          )
        : const Icon(Icons.directions_bus, color: Colors.white, size: 20);
    return Container(
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 2.5),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 8, offset: const Offset(0, 3))],
      ),
      child: Center(child: icon),
    );
  }
}

class _UserDot extends StatelessWidget {
  const _UserDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1A73E8),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 3),
        boxShadow: [BoxShadow(color: const Color(0xFF1A73E8).withValues(alpha: 0.35), blurRadius: 10, spreadRadius: 4)],
      ),
    );
  }
}

class _StopDot extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        shape: BoxShape.circle,
        border: Border.all(color: BuzUpColors.blue, width: 3),
      ),
    );
  }
}
