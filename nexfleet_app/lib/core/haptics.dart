import 'package:flutter/services.dart';

/// Retours haptiques intelligents, style iOS (UIFeedbackGenerator).
Future<void> pulseLight() => HapticFeedback.lightImpact();
Future<void> pulseMedium() => HapticFeedback.mediumImpact();
Future<void> pulseHeavy() => HapticFeedback.heavyImpact();
Future<void> pulseSelect() => HapticFeedback.selectionClick();
Future<void> pulseVibrate() => HapticFeedback.vibrate();