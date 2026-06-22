import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'theme.dart';

/// Animated bus loader used while waiting for a payment confirmation.
/// Combines a bouncing bus, rolling wheels, motion lines and a dotted progress
/// arc to give the agent rich pending-state feedback (vs a generic spinner).
class BusLoader extends StatefulWidget {
  const BusLoader({
    super.key,
    this.size = 200,
    this.label = 'A processar pagamento...',
  });

  final double size;
  final String label;

  @override
  State<BusLoader> createState() => _BusLoaderState();
}

class _BusLoaderState extends State<BusLoader> with TickerProviderStateMixin {
  late final AnimationController _ring;
  late final AnimationController _wheel;
  late final AnimationController _bounce;

  @override
  void initState() {
    super.initState();
    _ring = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat();
    _wheel = AnimationController(vsync: this, duration: const Duration(milliseconds: 800))..repeat();
    _bounce = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ring.dispose();
    _wheel.dispose();
    _bounce.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: widget.size,
          height: widget.size,
          child: AnimatedBuilder(
            animation: Listenable.merge([_ring, _wheel, _bounce]),
            builder: (_, __) {
              return CustomPaint(
                painter: _BusPainter(
                  ring: _ring.value,
                  wheel: _wheel.value * 2 * math.pi,
                  bounce: Curves.easeInOut.transform(_bounce.value),
                  accent: BuzUpColors.orange,
                  body: isDark ? const Color(0xFF2D8CF0) : BuzUpColors.orange,
                  outline: isDark ? Colors.white : const Color(0xFF15191E),
                  bg: isDark ? const Color(0xFF1A1F26) : Colors.white,
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 12),
        Text(
          widget.label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: isDark ? Colors.white : const Color(0xFF15191E),
            letterSpacing: 0.4,
          ),
        ),
      ],
    );
  }
}

class _BusPainter extends CustomPainter {
  _BusPainter({
    required this.ring,
    required this.wheel,
    required this.bounce,
    required this.accent,
    required this.body,
    required this.outline,
    required this.bg,
  });

  final double ring;
  final double wheel;
  final double bounce;
  final Color accent;
  final Color body;
  final Color outline;
  final Color bg;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final r = size.shortestSide / 2;

    // Background circle.
    final bgPaint = Paint()..color = bg;
    canvas.drawCircle(c, r, bgPaint);

    // Dotted ring (12 dots, 3 highlighted by ring progress).
    const dotCount = 12;
    final dotR = r * 0.04;
    for (int i = 0; i < dotCount; i++) {
      final a = (i / dotCount) * 2 * math.pi - math.pi / 2;
      final p = Offset(c.dx + math.cos(a) * (r - r * 0.08), c.dy + math.sin(a) * (r - r * 0.08));
      final delta = ((i / dotCount) - ring) % 1.0;
      final active = delta >= 0.0 && delta < 0.25;
      final col = active ? accent : accent.withValues(alpha: 0.15);
      canvas.drawCircle(p, dotR, Paint()..color = col);
    }

    // Road
    final roadY = c.dy + r * 0.42;
    final road = Paint()
      ..color = outline.withValues(alpha: 0.12)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(Offset(c.dx - r * 0.7, roadY), Offset(c.dx + r * 0.7, roadY), road);

    // Bus container
    final busOffsetY = -bounce * 4.0;
    final busW = r * 1.1;
    final busH = r * 0.55;
    final busX = c.dx - busW / 2;
    final busY = c.dy - busH / 2 + busOffsetY;
    final busRect = RRect.fromLTRBAndCorners(busX, busY, busX + busW, busY + busH,
        topLeft: const Radius.circular(10),
        topRight: const Radius.circular(18),
        bottomLeft: const Radius.circular(4),
        bottomRight: const Radius.circular(4));

    final busPaint = Paint()..color = body;
    canvas.drawRRect(busRect, busPaint);

    // Window strip
    final winR = RRect.fromLTRBAndCorners(busX + busW * 0.10, busY + busH * 0.15,
        busX + busW * 0.85, busY + busH * 0.45,
        topLeft: const Radius.circular(4), topRight: const Radius.circular(8),
        bottomLeft: const Radius.circular(2), bottomRight: const Radius.circular(2));
    canvas.drawRRect(winR, Paint()..color = bg);
    // Window dividers
    final divPaint = Paint()..color = body.withValues(alpha: 0.6)..strokeWidth = 1.6;
    for (int i = 1; i < 4; i++) {
      final x = busX + busW * 0.10 + (busW * 0.75) * (i / 4);
      canvas.drawLine(Offset(x, busY + busH * 0.15), Offset(x, busY + busH * 0.45), divPaint);
    }

    // Head light
    canvas.drawCircle(Offset(busX + busW - 6, busY + busH * 0.62), 3, Paint()..color = const Color(0xFFFFE08A));

    // Door
    final doorR = RRect.fromLTRBAndCorners(busX + busW * 0.10, busY + busH * 0.50,
        busX + busW * 0.22, busY + busH * 0.92,
        topLeft: const Radius.circular(2), topRight: const Radius.circular(2),
        bottomLeft: const Radius.circular(2), bottomRight: const Radius.circular(2));
    canvas.drawRRect(doorR, Paint()..color = bg.withValues(alpha: 0.85));

    // Side bands (Buzup orange stripe at the bottom)
    final stripe = Rect.fromLTRB(busX, busY + busH * 0.65, busX + busW, busY + busH * 0.72);
    canvas.drawRect(stripe, Paint()..color = accent);

    // Wheels (rotating)
    final wheelY = busY + busH + 4;
    _drawWheel(canvas, Offset(busX + busW * 0.22, wheelY), r * 0.10, outline);
    _drawWheel(canvas, Offset(busX + busW * 0.78, wheelY), r * 0.10, outline);

    // Motion lines behind bus
    final mPaint = Paint()
      ..color = accent.withValues(alpha: 0.5)
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    final phase = (ring * 60) % 24;
    for (int i = 0; i < 4; i++) {
      final dx = -r * 0.55 - i * 8 + phase;
      final dy = c.dy - r * 0.10 + i * 6;
      canvas.drawLine(Offset(c.dx + dx, dy), Offset(c.dx + dx + 14, dy), mPaint);
    }
  }

  void _drawWheel(Canvas canvas, Offset center, double radius, Color outline) {
    canvas.drawCircle(center, radius, Paint()..color = outline);
    canvas.drawCircle(center, radius * 0.55, Paint()..color = bg);
    final spokes = Paint()
      ..color = outline
      ..strokeWidth = 1.4
      ..strokeCap = StrokeCap.round;
    for (int i = 0; i < 4; i++) {
      final a = wheel + (i * math.pi / 2);
      canvas.drawLine(
        Offset(center.dx + math.cos(a) * radius * 0.20, center.dy + math.sin(a) * radius * 0.20),
        Offset(center.dx + math.cos(a) * radius * 0.55, center.dy + math.sin(a) * radius * 0.55),
        spokes,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _BusPainter old) =>
      old.ring != ring || old.wheel != wheel || old.bounce != bounce;
}
