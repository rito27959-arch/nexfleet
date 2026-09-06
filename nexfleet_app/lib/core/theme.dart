import 'package:flutter/material.dart';

/// Design system « NexFleet Aurora » — sombre, verre, dégradés néon.
class Palette {
  Palette._();

  static const Color bg = Color(0xFF05070F);
  static const Color bgDeep = Color(0xFF02040A);
  static const Color teal = Color(0xFF2DD4BF);
  static const Color cyan = Color(0xFF38BDF8);
  static const Color indigo = Color(0xFF818CF8);
  static const Color violet = Color(0xFFC084FC);
  static const Color magenta = Color(0xFFE879F9);

  static const Color success = Color(0xFF34D399);
  static const Color warning = Color(0xFFFBBF24);
  static const Color danger = Color(0xFFF87171);

  static const Color text = Color(0xFFE8EDF8);
  static const Color textDim = Color(0xFF9AA7BD);
  static const Color textMute = Color(0xFF5E6B85);

  static const List<Color> aurora = [teal, cyan, indigo, violet, magenta];

  static const LinearGradient accent = LinearGradient(
    colors: [cyan, indigo, violet],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accentSoft = LinearGradient(
    colors: [teal, cyan],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static Color level(String level) => switch (level) {
        'danger' => danger,
        'warning' => warning,
        _ => success,
      };
}

/// Courbes sur-mesure pour un rendu « plus fluide que natif ».
class Motion {
  Motion._();

  static const Curve springOut = Cubic(0.34, 1.4, 0.64, 1);
  static const Curve soft = Cubic(0.22, 1, 0.36, 1);
  static const Curve breathe = Cubic(0.65, 0, 0.35, 1);
  static const Curve press = Cubic(0.25, 0.8, 0.35, 1);
  static const Curve pop = Curves.easeOutBack;
  static const Curve elastic = Curves.elasticOut;

  /// Séquence « bounce » iOS : part vite, dépasse, stabilise.
  static Animation<double> bounce(Animation<double> source) =>
      CurvedAnimation(
        parent: source,
        curve: const Interval(0, 0.7, curve: Curves.easeOutBack),
      );
}

ThemeData buildTheme() {
  final scheme = ColorScheme.dark(
    primary: Palette.cyan,
    secondary: Palette.violet,
    surface: Palette.bg,
    error: Palette.danger,
    onSurface: Palette.text,
  );
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: Colors.transparent,
    splashFactory: NoSplash.splashFactory,
    highlightColor: Colors.transparent,
    hoverColor: Colors.transparent,
  );

  return base.copyWith(
    textTheme: base.textTheme
        .apply(
          bodyColor: Palette.text,
          displayColor: Palette.text,
        )
        .copyWith(
          displaySmall: base.textTheme.displaySmall?.copyWith(
              fontSize: 34, fontWeight: FontWeight.w800, letterSpacing: -0.5),
          headlineMedium: base.textTheme.headlineMedium
              ?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.3),
          titleLarge: base.textTheme.titleLarge
              ?.copyWith(fontWeight: FontWeight.w700),
          titleMedium: base.textTheme.titleMedium
              ?.copyWith(fontWeight: FontWeight.w600),
          bodyLarge: base.textTheme.bodyLarge?.copyWith(
              fontSize: 15.5, height: 1.35, color: Palette.text),
          bodyMedium: base.textTheme.bodyMedium?.copyWith(
              fontSize: 14, height: 1.3, color: Palette.textDim),
          labelLarge: base.textTheme.labelLarge
              ?.copyWith(fontSize: 14, fontWeight: FontWeight.w700),
        ),
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: Color(0x14FFFFFF),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        borderSide: BorderSide(color: Color(0x1FFFFFFF)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        borderSide: BorderSide(color: Color(0x1FFFFFFF)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        borderSide: BorderSide(color: Palette.cyan, width: 1.4),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        borderSide: BorderSide(color: Palette.danger),
      ),
      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 15),
      hintStyle: TextStyle(color: Palette.textMute),
      labelStyle: TextStyle(color: Palette.textDim),
    ),
    dividerTheme:
        const DividerThemeData(color: Color(0x14FFFFFF), thickness: 1),
    switchTheme: const SwitchThemeData(
      thumbColor: WidgetStatePropertyAll(Palette.cyan),
      trackColor: WidgetStatePropertyAll(Color(0x33FFFFFF)),
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: _NexPageTransitionsBuilder(),
        TargetPlatform.iOS: _NexPageTransitionsBuilder(),
        TargetPlatform.macOS: _NexPageTransitionsBuilder(),
        TargetPlatform.windows: _NexPageTransitionsBuilder(),
        TargetPlatform.linux: _NexPageTransitionsBuilder(),
      },
    ),
  );
}

/// Transition de page personnalisée : glissement + fondu + léger zoom.
class _NexPageTransitionsBuilder extends PageTransitionsBuilder {
  const _NexPageTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    final curved = CurvedAnimation(parent: animation, curve: Motion.soft);
    return FadeTransition(
      opacity: curved,
      child: SlideTransition(
        position: Tween<Offset>(begin: const Offset(0.04, 0), end: Offset.zero)
            .animate(curved),
        child: ScaleTransition(
          scale: Tween<double>(begin: 0.985, end: 1).animate(curved),
          child: child,
        ),
      ),
    );
  }
}