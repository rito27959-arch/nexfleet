import 'api_client.dart';
import 'session.dart';

/// Accès global (single) à la session et au client API NexFleet.
class AppScope {
  final Session session = Session();
  late final ApiClient api = ApiClient(session);
}

final AppScope app = AppScope();