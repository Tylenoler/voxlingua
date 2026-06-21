import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/types.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  ConnectionStatus _status = ConnectionStatus.disconnected;
  String? _sessionId;
  String _url;
  Timer? _reconnectTimer;
  bool _autoReconnect = true;

  final StreamController<ConnectionStatus> _statusController = StreamController<ConnectionStatus>.broadcast();
  final StreamController<Map<String, dynamic>> _messageController = StreamController<Map<String, dynamic>>.broadcast();

  WebSocketService({String url = "ws://localhost:9876/ws/mobile"}) : _url = url;

  Stream<ConnectionStatus> get statusStream => _statusController.stream;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  ConnectionStatus get status => _status;
  String? get sessionId => _sessionId;

  void setUrl(String url) {
    _url = url;
  }

  void connect() {
    if (_status == ConnectionStatus.connected || _status == ConnectionStatus.connecting) return;

    _setStatus(ConnectionStatus.connecting);

    try {
      final uri = Uri.parse(_url);
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        (data) {
          try {
            final msg = jsonDecode(data as String) as Map<String, dynamic>;
            final type = msg["type"] as String?;

            if (type == "handshake_ack") {
              _sessionId = msg["payload"]?["session_id"] as String?;
              _setStatus(ConnectionStatus.connected);
            }

            _messageController.add(msg);
          } catch (e) {
            print("Failed to parse message: $e");
          }
        },
        onDone: () {
          _setStatus(ConnectionStatus.disconnected);
          if (_autoReconnect) {
            _scheduleReconnect();
          }
        },
        onError: (error) {
          _setStatus(ConnectionStatus.error);
          if (_autoReconnect) {
            _scheduleReconnect();
          }
        },
      );

      // Send handshake
      send({"type": "handshake", "payload": {}});
    } catch (e) {
      _setStatus(ConnectionStatus.error);
      if (_autoReconnect) {
        _scheduleReconnect();
      }
    }
  }

  void disconnect() {
    _autoReconnect = false;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _setStatus(ConnectionStatus.disconnected);
  }

  void send(Map<String, dynamic> message) {
    if (_channel != null && _status == ConnectionStatus.connected) {
      _channel!.sink.add(jsonEncode(message));
    }
  }

  void _setStatus(ConnectionStatus newStatus) {
    _status = newStatus;
    _statusController.add(newStatus);
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      print("Reconnecting...");
      connect();
    });
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _statusController.close();
    _messageController.close();
  }
}
