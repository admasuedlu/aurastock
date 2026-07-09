import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

class Env {
  /// Android emulators can't reach the host machine via `localhost`; they
  /// use the special alias `10.0.2.2` instead. Everything else (web,
  /// desktop, iOS simulator) talks to the backend directly.
  static String get apiBaseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api/v1';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api/v1';
    return 'http://127.0.0.1:8000/api/v1';
  }

  static String get wsBaseUrl {
    if (kIsWeb) return 'ws://127.0.0.1:8000';
    if (Platform.isAndroid) return 'ws://10.0.2.2:8000';
    return 'ws://127.0.0.1:8000';
  }
}
