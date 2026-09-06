/// Formatage français des nombres, montants (FCFA) et dates.
library;

String _group(String s) {
  final out = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) out.write(' ');
    out.write(s[i]);
  }
  return out.toString();
}

/// 75000 -> "75 000"
String inr(num v) {
  final neg = v < 0;
  final s = v.abs().toStringAsFixed(0);
  return (neg ? '-' : '') + _group(s);
}

/// 75000 -> "75 000 FCFA"
String money(num v, {bool decimals = false}) {
  final s = decimals ? v.toStringAsFixed(2) : v.toStringAsFixed(0);
  return _group(s) + '\u00A0FCFA';
}

/// "2026-08-14" -> "14/08/2026". "" -> "".
String frDate(String? iso) {
  if (iso == null || iso.isEmpty) return '—';
  final p = iso.split('T').first.split('-');
  if (p.length != 3) return iso;
  return '${p[2]}/${p[1]}/${p[0]}';
}

/// "2026-08" -> "Août".
String frMonth(String ym) {
  if (ym.length < 7) return ym;
  final m = int.tryParse(ym.substring(5, 7)) ?? 0;
  const months = [
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc',
  ];
  if (m < 1 || m > 12) return ym;
  return months[m - 1];
}

/// Jours restants relatif à aujourd'hui (dates ISO).
int? daysUntil(String? iso) {
  if (iso == null || iso.isEmpty) return null;
  final p = iso.split('T').first.split('-');
  if (p.length != 3) return null;
  final y = int.tryParse(p[0]);
  final mo = int.tryParse(p[1]);
  final d = int.tryParse(p[2]);
  if (y == null || mo == null || d == null) return null;
  final target = DateTime(y, mo, d);
  final today = DateTime.now();
  return target.difference(DateTime(today.year, today.month, today.day)).inDays;
}

/// "2026-08-14" (local) valable comme valeur `date` pour le backend.
String todayIso() {
  final n = DateTime.now();
  return '${n.year.toString().padLeft(4, '0')}-'
      '${n.month.toString().padLeft(2, '0')}-'
      '${n.day.toString().padLeft(2, '0')}';
}