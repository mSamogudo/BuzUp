import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Smooth fade+slide page transition used across the app for a premium feel.
CustomTransitionPage<T> fadePage<T>({required Widget child, LocalKey? key}) {
  return CustomTransitionPage<T>(
    key: key,
    child: child,
    transitionDuration: const Duration(milliseconds: 320),
    reverseTransitionDuration: const Duration(milliseconds: 220),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final curve = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
      return FadeTransition(
        opacity: curve,
        child: SlideTransition(
          position: Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero).animate(curve),
          child: child,
        ),
      );
    },
  );
}

/// Drop-in fade-in container for content entrances inside screens.
class FadeIn extends StatefulWidget {
  const FadeIn({super.key, required this.child, this.delay = Duration.zero, this.offset = 12});
  final Widget child;
  final Duration delay;
  final double offset;

  @override
  State<FadeIn> createState() => _FadeInState();
}

class _FadeInState extends State<FadeIn> with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _a;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 350));
    _a = CurvedAnimation(parent: _c, curve: Curves.easeOutCubic);
    Future.delayed(widget.delay, () { if (mounted) _c.forward(); });
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _a,
      builder: (_, __) => Opacity(
        opacity: _a.value,
        child: Transform.translate(
          offset: Offset(0, widget.offset * (1 - _a.value)),
          child: widget.child,
        ),
      ),
    );
  }
}

/// Skeleton placeholder with shimmer effect.
class Skeleton extends StatefulWidget {
  const Skeleton({super.key, this.height = 16, this.width = double.infinity, this.radius = 6});
  final double height;
  final double width;
  final double radius;

  @override
  State<Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<Skeleton> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final base = isDark ? Colors.white.withValues(alpha: 0.06) : Colors.black.withValues(alpha: 0.06);
    final highlight = isDark ? Colors.white.withValues(alpha: 0.13) : Colors.black.withValues(alpha: 0.04);
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        return Container(
          height: widget.height,
          width: widget.width,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 + 2 * _c.value, 0),
              end: Alignment(1 + 2 * _c.value, 0),
              colors: [base, highlight, base],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
        );
      },
    );
  }
}
