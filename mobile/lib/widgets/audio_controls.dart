import 'dart:async';
import 'package:flutter/material.dart';
import '../services/audio_service.dart';

class AudioControls extends StatefulWidget {
  final AudioService audioService;
  final VoidCallback onRecordStart;
  final Future<String> Function() onRecordStop;
  final bool disabled;

  const AudioControls({
    super.key,
    required this.audioService,
    required this.onRecordStart,
    required this.onRecordStop,
    this.disabled = false,
  });

  @override
  State<AudioControls> createState() => _AudioControlsState();
}

class _AudioControlsState extends State<AudioControls> with SingleTickerProviderStateMixin {
  RecorderStatus _status = RecorderStatus.idle;
  StreamSubscription<RecorderStatus>? _sub;
  late AnimationController _pulseAnim;

  @override
  void initState() {
    super.initState();
    _pulseAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _sub = widget.audioService.statusStream.listen((status) {
      if (mounted) setState(() => _status = status);
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _pulseAnim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRecording = _status == RecorderStatus.recording;
    final isProcessing = _status == RecorderStatus.processing;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Waveform visualization
        SizedBox(
          height: 30,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (i) {
              return AnimatedBuilder(
                animation: _pulseAnim,
                builder: (context, child) {
                  final height = isRecording
                      ? 4.0 + _pulseAnim.value * 30.0 * (0.5 + 0.5 * (i / 4))
                      : 4.0;
                  return Container(
                    width: 4,
                    height: height,
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                      color: isRecording ? Colors.red : theme.colorScheme.primary,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  );
                },
              );
            }),
          ),
        ),
        const SizedBox(height: 8),
        // Record button
        GestureDetector(
          onTapDown: widget.disabled || isProcessing
              ? null
              : (_) {
                  widget.onRecordStart();
                },
          onTapUp: widget.disabled || isProcessing
              ? null
              : (_) async {
                  await widget.onRecordStop();
                },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: isRecording ? 60 : 64,
            height: isRecording ? 60 : 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isRecording
                  ? Colors.red
                  : isProcessing
                      ? theme.colorScheme.surfaceContainerHighest
                      : theme.colorScheme.primary,
              boxShadow: [
                BoxShadow(
                  color: (isRecording ? Colors.red : theme.colorScheme.primary).withOpacity(0.4),
                  blurRadius: isRecording ? 24 : 16,
                  spreadRadius: isRecording ? 4 : 0,
                ),
              ],
            ),
            child: Icon(
              isRecording ? Icons.stop : isProcessing ? Icons.hourglass_top : Icons.mic,
              color: theme.colorScheme.onPrimary,
              size: 28,
            ),
          ),
        ),
        const SizedBox(height: 8),
        // Status text
        Text(
          isRecording ? "Recording..." : isProcessing ? "Processing..." : "Tap to speak",
          style: theme.textTheme.bodySmall?.copyWith(
            color: isRecording ? Colors.red : theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext, Widget?) builder;

  const AnimatedBuilder({
    super.key,
    required super.listenable,
    required this.builder,
  });

  @override
  Widget build(BuildContext context) {
    return builder(context, null);
  }
}
