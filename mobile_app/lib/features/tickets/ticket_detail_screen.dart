import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/bus_loader.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Pixel-for-pixel mirror of the backend PDF (`apps/guest_checkouts/ticket_pdf.py`).
///
/// Uses the same `ticket_template_clean.jpg` (now `assets/ticket_template.jpg`)
/// as background and overlays text + QR + short_code at the exact same
/// design-space coordinates as the PDF. The whole 1024x1535 canvas is wrapped
/// in a FittedBox so it scales uniformly to the device width without losing
/// the layout match.
class TicketDetailScreen extends ConsumerStatefulWidget {
  const TicketDetailScreen({super.key, required this.ticketId});

  final int ticketId;

  @override
  ConsumerState<TicketDetailScreen> createState() => _TicketDetailScreenState();
}

// PDF design constants — keep in sync with backend `ticket_pdf.py`.
const double _designWidth = 1024;
const double _designHeight = 1535;
const Color _navy = Color(0xFF071E49);
const Color _orange = Color(0xFFE47B11);
const Color _red = Color(0xFFD32F2F);

class _TicketDetailScreenState extends ConsumerState<TicketDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    Log.info('ticket.detail.load id=${widget.ticketId}');
    _future = ref.read(passengerApiProvider).ticketDetail(widget.ticketId);
  }

  @override
  Widget build(BuildContext context) {
    // No AppBar — the ticket consumes the full screen (status bar to bottom
    // safe area). Back/copy controls float as overlay icons so they don't
    // eat ticket real estate.
    return Scaffold(
      backgroundColor: BuzUpColors.scaffoldDark,
      extendBodyBehindAppBar: true,
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (ctx, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: BusLoader(label: 'A carregar bilhete...'));
          }
          if (snap.hasError) {
            return Center(child: Text('Erro: ${snap.error}',
                style: const TextStyle(color: BuzUpColors.danger)));
          }
          final token = (snap.data?['token'] ?? '').toString();
          return Stack(children: [
            // The ticket itself — sized to the screen width and stretched
            // vertically using the PDF aspect ratio. If the resulting height
            // exceeds the screen, the SingleChildScrollView lets the user
            // pan to see the rest (rare on tall phones; common on
            // landscape).
            Positioned.fill(
              child: SingleChildScrollView(
                child: AspectRatio(
                  aspectRatio: _designWidth / _designHeight,
                  child: _TicketCanvas(data: snap.data ?? const {}),
                ),
              ),
            ),
            // Floating back button (top-left).
            Positioned(
              top: MediaQuery.of(context).padding.top + 4,
              left: 6,
              child: _FloatingIconButton(
                icon: Icons.arrow_back,
                onPressed: () =>
                    context.canPop() ? context.pop() : context.go('/tickets'),
              ),
            ),
            // Floating copy-token button (top-right).
            if (token.isNotEmpty) Positioned(
              top: MediaQuery.of(context).padding.top + 4,
              right: 6,
              child: _FloatingIconButton(
                icon: Icons.copy,
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: token));
                  if (!mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Token copiado.')),
                  );
                },
              ),
            ),
          ]);
        },
      ),
    );
  }
}

class _FloatingIconButton extends StatelessWidget {
  const _FloatingIconButton({required this.icon, required this.onPressed});

  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black.withValues(alpha: 0.45),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Icon(icon, color: Colors.white, size: 20),
        ),
      ),
    );
  }
}

class _TicketCanvas extends StatelessWidget {
  const _TicketCanvas({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final route = _routeLabel(data);
    final reference = (data['reference'] ?? '').toString();
    final shortCode = (data['short_code'] ?? '').toString().toUpperCase();
    final token = (data['token'] ?? '').toString();
    final fare = _money(data['fare_amount']);
    final originStop = (data['origin_stop'] ?? '-').toString();
    final destinationStop = (data['destination_stop'] ?? '-').toString();
    final status = (data['status'] ?? 'active').toString();
    final validUntilIso = data['valid_until']?.toString();
    final issuedAtIso = (data['valid_from'] ?? data['created_at'])?.toString();
    final issuedAt = _parseLocal(issuedAtIso ?? '');
    final validUntil = _parseLocal(validUntilIso ?? '');

    return FittedBox(
      fit: BoxFit.fill,
      child: SizedBox(
        width: _designWidth,
        height: _designHeight,
        child: Stack(children: [
          // Background template (same JPG the PDF uses).
          Positioned.fill(
            child: Image.asset(
              'assets/ticket_template.jpg',
              fit: BoxFit.fill,
              errorBuilder: (_, _, _) => Container(color: const Color(0xFFF7F4EE)),
            ),
          ),

          // Reference (x=199, y_top=467, size=25, NAVY).
          _PdfText(left: 199, top: 467, size: 25, color: _navy,
              value: reference.isEmpty ? '-' : reference),

          // Issued date (x=674, y_top=437) and time (x=674, y_top=467).
          _PdfText(left: 674, top: 437, size: 28, color: _navy,
              value: issuedAt != null ? DateFormat('dd/MM/yyyy').format(issuedAt) : '-'),
          _PdfText(left: 674, top: 467, size: 28, color: _navy,
              value: issuedAt != null ? DateFormat('HH:mm').format(issuedAt) : '--:--'),

          // Route label centered (center_x=526, top_y=555, max_size=68, NAVY).
          _PdfCenteredText(centerX: 526, top: 555, maxSize: 68, minSize: 36,
              maxWidth: 720, color: _navy, value: route),

          // Origin (x=192, y=762) and destination (right edge x=856, y=762).
          _PdfText(left: 192, top: 762, size: 45, minSize: 28,
              maxWidth: 255, color: _navy, value: originStop),
          _PdfText(left: 192, top: 762, size: 45, minSize: 28,
              maxWidth: 0, color: Colors.transparent, value: ''), // anchor
          _PdfRightText(right: 856, top: 762, size: 45, minSize: 28,
              maxWidth: 205, color: _navy, value: destinationStop),

          // Fare (x=282, y=901) + " MZN", status (x=689, y=911).
          _PdfText(left: 282, top: 901, size: 45, minSize: 31,
              maxWidth: 245, color: _navy, value: '$fare MZN'),
          _PdfText(left: 689, top: 911, size: 40, minSize: 28,
              maxWidth: 178,
              color: status == 'active'
                  ? _orange
                  : (status == 'used' ? _red : _navy),
              value: _statusLabel(status)),

          // Valid until (x=446, y=1013).
          _PdfText(left: 446, top: 1013, size: 34, minSize: 25, maxWidth: 295,
              color: _navy,
              value: validUntil != null
                  ? DateFormat('dd/MM/yyyy HH:mm').format(validUntil)
                  : '-'),

          // QR — kept at the original size but centred in the white card
          // (354..666) so it fills the old right-side gap WITHOUT touching the
          // yellow border that frames the card.
          Positioned(
            left: 366, top: 1072, width: 287, height: 287,
            child: Container(
              color: Colors.white,
              padding: const EdgeInsets.all(4),
              child: QrImageView(
                data: token.isEmpty ? '-' : token,
                version: QrVersions.auto,
                backgroundColor: Colors.white,
                padding: EdgeInsets.zero,
                eyeStyle: const QrEyeStyle(eyeShape: QrEyeShape.square, color: _navy),
                dataModuleStyle: const QrDataModuleStyle(
                    dataModuleShape: QrDataModuleShape.square, color: _navy),
              ),
            ),
          ),

          // Short code centered below QR (center_x=512, top_y=1365).
          _PdfCenteredText(centerX: 512, top: 1365, maxSize: 35, minSize: 28,
              maxWidth: 112, color: _navy,
              value: shortCode.isEmpty ? '----' : shortCode),

          // "USADO" stamp — only when the ticket was already validated, to make
          // a spent ticket obvious at a glance. Kept translucent so the data
          // underneath stays readable.
          if (status == 'used')
            Positioned(
              left: 0, right: 0, top: 600,
              child: Transform.rotate(
                angle: -0.32,
                child: Center(
                  child: Text(
                    'USADO',
                    style: TextStyle(
                      fontSize: 200,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 8,
                      color: _red.withValues(alpha: 0.18),
                    ),
                  ),
                ),
              ),
            ),
        ]),
      ),
    );
  }

  String _routeLabel(Map<String, dynamic> tp) {
    // Only the route at the top — origin/destination already appear below, so
    // we drop the "code - name" pairing that restated them on one line.
    final code = (tp['route_code'] ?? '').toString();
    final name = (tp['route_name'] ?? '').toString();
    if (code.isNotEmpty) return code;
    if (name.isNotEmpty) return name;
    return 'BuzUp';
  }

  String _money(dynamic v) {
    final n = double.tryParse('${v ?? 0}') ?? 0;
    return n.toStringAsFixed(2).replaceAll('.', ',');
  }

  String _statusLabel(String s) => switch (s) {
        'active' => 'ACTIVO',
        'used' => 'USADO',
        'expired' => 'EXPIRADO',
        'cancelled' => 'CANCELADO',
        'refunded' => 'REEMBOLSADO',
        _ => s.toUpperCase(),
      };

  DateTime? _parseLocal(String iso) {
    if (iso.isEmpty) return null;
    try {
      return DateTime.parse(iso).toLocal();
    } catch (_) {
      return null;
    }
  }
}

/// Left-anchored bold text that auto-shrinks to fit `maxWidth`.
class _PdfText extends StatelessWidget {
  const _PdfText({
    required this.left,
    required this.top,
    required this.size,
    required this.color,
    required this.value,
    this.minSize,
    this.maxWidth,
  });

  final double left;
  final double top;
  final double size;
  final double? minSize;
  final double? maxWidth;
  final Color color;
  final String value;

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
        fontSize: size,
        color: color,
        fontWeight: FontWeight.w900,
        height: 1.0);
    return Positioned(
      left: left,
      top: top,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth ?? double.infinity),
        child: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(value, style: style, maxLines: 1, softWrap: false),
        ),
      ),
    );
  }
}

/// Right-anchored bold text that auto-shrinks to fit `maxWidth`.
class _PdfRightText extends StatelessWidget {
  const _PdfRightText({
    required this.right,
    required this.top,
    required this.size,
    required this.color,
    required this.value,
    this.minSize,
    this.maxWidth,
  });

  final double right;
  final double top;
  final double size;
  final double? minSize;
  final double? maxWidth;
  final Color color;
  final String value;

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
        fontSize: size,
        color: color,
        fontWeight: FontWeight.w900,
        height: 1.0);
    return Positioned(
      left: right - (maxWidth ?? 200),
      top: top,
      width: maxWidth,
      child: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.centerRight,
        child: Text(value, style: style, maxLines: 1, softWrap: false),
      ),
    );
  }
}

/// Center-anchored bold text that auto-shrinks to fit `maxWidth`.
class _PdfCenteredText extends StatelessWidget {
  const _PdfCenteredText({
    required this.centerX,
    required this.top,
    required this.maxSize,
    required this.minSize,
    required this.maxWidth,
    required this.color,
    required this.value,
  });

  final double centerX;
  final double top;
  final double maxSize;
  final double minSize;
  final double maxWidth;
  final Color color;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: centerX - maxWidth / 2,
      top: top,
      width: maxWidth,
      child: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.center,
        child: Text(value,
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: maxSize,
                color: color,
                fontWeight: FontWeight.w900,
                height: 1.0),
            maxLines: 1,
            softWrap: false),
      ),
    );
  }
}
