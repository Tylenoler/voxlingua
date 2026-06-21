import 'package:flutter/material.dart';
import '../models/types.dart';

class SettingsSheet extends StatefulWidget {
  final String currentScene;
  final String currentVoice;
  final CorrectionMode correctionMode;
  final String engineUrl;
  final ConnectionStatus connectionStatus;
  final ValueChanged<String> onSceneChange;
  final ValueChanged<String> onVoiceChange;
  final ValueChanged<CorrectionMode> onCorrectionModeChange;
  final ValueChanged<String> onEngineUrlChange;
  final VoidCallback onConnect;
  final VoidCallback onDisconnect;

  const SettingsSheet({
    super.key,
    required this.currentScene,
    required this.currentVoice,
    required this.correctionMode,
    required this.engineUrl,
    required this.connectionStatus,
    required this.onSceneChange,
    required this.onVoiceChange,
    required this.onCorrectionModeChange,
    required this.onEngineUrlChange,
    required this.onConnect,
    required this.onDisconnect,
  });

  @override
  State<SettingsSheet> createState() => _SettingsSheetState();
}

class _SettingsSheetState extends State<SettingsSheet> {
  late TextEditingController _urlController;

  static const _scenes = [
    {"id": "daily_chat", "name": "Daily Chat", "desc": "Casual everyday conversation"},
    {"id": "restaurant", "name": "Restaurant", "desc": "Ordering food and drinks"},
    {"id": "travel", "name": "Travel", "desc": "Airport, hotel, directions"},
    {"id": "interview", "name": "Job Interview", "desc": "Professional interview practice"},
  ];

  static const _voices = [
    {"id": "new_york", "name": "New York Accent (default)"},
  ];

  static const _correctionModes = [
    {"value": "off", "name": "Off", "desc": "No correction feedback"},
    {"value": "mild_only", "name": "Mild", "desc": "Only minor hints"},
    {"value": "medium", "name": "Medium", "desc": "Visual corrections"},
    {"value": "all", "name": "All", "desc": "Full correction + interruption"},
  ];

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: widget.engineUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) {
          return Container(
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: ListView(
              controller: scrollController,
              padding: const EdgeInsets.all(20),
              children: [
                // Handle
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.onSurfaceVariant.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                Text("Settings", style: theme.textTheme.titleLarge),
                const SizedBox(height: 20),

                // Connection
                _section("Connection", children: [
                  TextField(
                    controller: _urlController,
                    decoration: const InputDecoration(
                      labelText: "Engine URL",
                      border: OutlineInputBorder(),
                    ),
                    onChanged: widget.onEngineUrlChange,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _connStatusChip(widget.connectionStatus, theme),
                      const Spacer(),
                      FilledButton.tonal(
                        onPressed: widget.connectionStatus == ConnectionStatus.connected
                            ? widget.onDisconnect
                            : widget.onConnect,
                        child: Text(widget.connectionStatus == ConnectionStatus.connected
                            ? "Disconnect" : "Connect"),
                      ),
                    ],
                  ),
                ]),

                const SizedBox(height: 20),

                // Scenes
                _section("Conversation Scene", children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _scenes.map((s) {
                      final active = widget.currentScene == s["id"];
                      return ChoiceChip(
                        label: Text(s["name"]!),
                        selected: active,
                        onSelected: (_) => widget.onSceneChange(s["id"]!),
                      );
                    }).toList(),
                  ),
                ]),

                const SizedBox(height: 20),

                // Voice
                _section("Voice Profile", children: [
                  DropdownButtonFormField<String>(
                    value: widget.currentVoice,
                    decoration: const InputDecoration(
                      labelText: "Voice",
                      border: OutlineInputBorder(),
                    ),
                    items: _voices.map((v) => DropdownMenuItem(
                      value: v["id"],
                      child: Text(v["name"]!),
                    )).toList(),
                    onChanged: (val) {
                      if (val != null) widget.onVoiceChange(val);
                    },
                  ),
                ]),

                const SizedBox(height: 20),

                // Correction Mode
                _section("Correction Mode", children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _correctionModes.map((m) {
                      final active = widget.correctionMode.mode == m["value"];
                      return ChoiceChip(
                        label: Text(m["name"]!),
                        selected: active,
                        onSelected: (_) {
                          widget.onCorrectionModeChange(CorrectionMode(
                            mode: m["value"]!,
                            interruptOnSevere: widget.correctionMode.interruptOnSevere,
                          ));
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile(
                    title: const Text("Interrupt on severe errors"),
                    value: widget.correctionMode.interruptOnSevere,
                    onChanged: (val) {
                      widget.onCorrectionModeChange(CorrectionMode(
                        mode: widget.correctionMode.mode,
                        interruptOnSevere: val,
                      ));
                    },
                    contentPadding: EdgeInsets.zero,
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _section(String title, {required List<Widget> children}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: Theme.of(context).colorScheme.primary,
        )),
        const SizedBox(height: 8),
        ...children,
      ],
    );
  }

  Widget _connStatusChip(ConnectionStatus status, ThemeData theme) {
    final (label, color) = switch (status) {
      ConnectionStatus.connected => ("Connected", Colors.green),
      ConnectionStatus.connecting => ("Connecting...", Colors.orange),
      ConnectionStatus.disconnected => ("Disconnected", Colors.grey),
      ConnectionStatus.error => ("Error", Colors.red),
    };
    return Chip(
      avatar: Icon(Icons.circle, size: 8, color: color),
      label: Text(label, style: const TextStyle(fontSize: 12)),
    );
  }
}
