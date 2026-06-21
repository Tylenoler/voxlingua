import 'dart:async';
import 'package:flutter/material.dart';
import '../models/types.dart';
import '../services/websocket_service.dart';
import '../services/audio_service.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/audio_controls.dart';
import '../widgets/settings_sheet.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final WebSocketService _wsService = WebSocketService();
  final AudioService _audioService = AudioService();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  ConnectionStatus _connStatus = ConnectionStatus.disconnected;
  String _currentScene = "daily_chat";
  String _currentVoice = "new_york";
  CorrectionMode _correctionMode = CorrectionMode();
  String _engineUrl = "ws://localhost:9876/ws/mobile";

  StreamSubscription<ConnectionStatus>? _wsStatusSub;
  StreamSubscription<Map<String, dynamic>>? _wsMsgSub;

  @override
  void initState() {
    super.initState();

    _wsStatusSub = _wsService.statusStream.listen((status) {
      if (mounted) setState(() => _connStatus = status);
    });

    _wsMsgSub = _wsService.messageStream.listen(_handleWSMessage);

    // Auto-connect
    _wsService.connect();
  }

  @override
  void dispose() {
    _wsStatusSub?.cancel();
    _wsMsgSub?.cancel();
    _wsService.dispose();
    _audioService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleWSMessage(Map<String, dynamic> msg) {
    final type = msg["type"] as String?;

    if (type == "audio_stream_start") {
      final text = msg["payload"]?["text"] as String?;
      if (text != null && text.isNotEmpty) {
        setState(() {
          _messages.add(ChatMessage(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            role: "assistant",
            text: text,
          ));
        });
        _scrollToBottom();
      }
    } else if (type == "correction") {
      final payload = msg["payload"] as Map<String, dynamic>?;
      if (payload != null) {
        final correction = CorrectionResult.fromJson(payload);
        setState(() {
          if (_messages.isNotEmpty) {
            _messages.last.correction = correction;
          }
        });
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _onRecordStart() {
    _audioService.startRecording();
  }

  Future<String> _onRecordStop() async {
    final audioB64 = await _audioService.stopRecording();
    if (audioB64.isNotEmpty) {
      setState(() {
        _messages.add(ChatMessage(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          role: "user",
          text: "\ud83c\udfa4 (audio sent)",
        ));
      });
      _wsService.send({
        "type": "audio_input",
        "payload": {
          "data": audioB64,
          "format": "webm",
          "sample_rate": 48000,
        },
      });
    }
    return audioB64;
  }

  void _openSettings() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => SettingsSheet(
        currentScene: _currentScene,
        currentVoice: _currentVoice,
        correctionMode: _correctionMode,
        engineUrl: _engineUrl,
        connectionStatus: _connStatus,
        onSceneChange: (scene) {
          setState(() => _currentScene = scene);
          _wsService.send({"type": "set_scene", "payload": {"scene": scene, "language": "en"}});
          Navigator.pop(context);
        },
        onVoiceChange: (voice) {
          setState(() => _currentVoice = voice);
          _wsService.send({"type": "set_voice", "payload": {"voice_profile_id": voice}});
        },
        onCorrectionModeChange: (mode) {
          setState(() => _correctionMode = mode);
          _wsService.send({"type": "set_correction_mode", "payload": mode.toJson()});
        },
        onEngineUrlChange: (url) {
          setState(() => _engineUrl = url);
          _wsService.setUrl(url);
        },
        onConnect: () => _wsService.connect(),
        onDisconnect: () => _wsService.disconnect(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text("VoxLingua", style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            )),
            const SizedBox(width: 8),
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: switch (_connStatus) {
                  ConnectionStatus.connected => Colors.green,
                  ConnectionStatus.connecting => Colors.orange,
                  _ => Colors.grey,
                },
                boxShadow: [
                  if (_connStatus == ConnectionStatus.connected)
                    BoxShadow(color: Colors.green.withOpacity(0.5), blurRadius: 6),
                ],
              ),
            ),
          ],
        ),
        actions: [
          if (_currentScene != "daily_chat")
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Chip(
                label: Text(_currentScene, style: const TextStyle(fontSize: 11)),
                visualDensity: VisualDensity.compact,
              ),
            ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: _openSettings,
          ),
        ],
      ),
      body: Column(
        children: [
          // Connection prompt
          if (_connStatus != ConnectionStatus.connected)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
              color: switch (_connStatus) {
                ConnectionStatus.connecting => Colors.orange.withOpacity(0.1),
                _ => Colors.red.withOpacity(0.1),
              },
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: _connStatus == ConnectionStatus.connecting ? Colors.orange : Colors.red,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _connStatus == ConnectionStatus.connecting
                        ? "Connecting to engine..."
                        : "Not connected to engine",
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: _connStatus == ConnectionStatus.connecting ? Colors.orange : Colors.red,
                    ),
                  ),
                ],
              ),
            ),

          // Messages
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text("\ud83d\udde3\ufe0f", style: TextStyle(fontSize: 48)),
                        const SizedBox(height: 12),
                        Text("Press the mic and start speaking",
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          )),
                        const SizedBox(height: 4),
                        Text("Your conversation will appear here",
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
                          )),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) => ChatBubble(
                      message: _messages[index],
                    ),
                  ),
          ),

          // Audio controls
          Container(
            padding: EdgeInsets.only(
              top: 12,
              bottom: 12 + MediaQuery.of(context).padding.bottom,
            ),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              border: Border(top: BorderSide(color: theme.colorScheme.outlineVariant)),
            ),
            child: AudioControls(
              audioService: _audioService,
              onRecordStart: _onRecordStart,
              onRecordStop: _onRecordStop,
              disabled: _connStatus != ConnectionStatus.connected,
            ),
          ),
        ],
      ),
    );
  }
}
