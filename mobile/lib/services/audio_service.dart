import 'dart:async';
import 'dart:convert';
import 'dart:io';

enum RecorderStatus { idle, recording, processing }

class AudioService {
  RecorderStatus _status = RecorderStatus.idle;

  final StreamController<RecorderStatus> _statusController = StreamController<RecorderStatus>.broadcast();

  Stream<RecorderStatus> get statusStream => _statusController.stream;
  RecorderStatus get status => _status;

  /// Start recording using platform audio recorder.
  /// Returns true if recording started successfully.
  Future<bool> startRecording() async {
    // Platform-specific recording will use:
    // - Android: MediaRecorder or record package
    // - iOS: AVAudioRecorder
    //
    // For now this is a stub that simulates recording.
    // In production, use the `record` Flutter package:
    //   final recorder = AudioRecorder();
    //   await recorder.start(...)
    _status = RecorderStatus.recording;
    _statusController.add(_status);
    return true;
  }

  /// Stop recording and return base64-encoded audio data.
  Future<String> stopRecording() async {
    _status = RecorderStatus.processing;
    _statusController.add(_status);

    // Stub: in production, read from recorder file and encode to base64
    // final file = await recorder.stop();
    // final bytes = await file.readAsBytes();
    // return base64Encode(bytes);

    // Simulate processing delay
    await Future.delayed(const Duration(milliseconds: 500));

    _status = RecorderStatus.idle;
    _statusController.add(_status);
    return "";
  }

  void dispose() {
    _statusController.close();
  }
}
