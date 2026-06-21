import 'dart:convert';

class CorrectionMode {
  final String mode;
  final bool interruptOnSevere;

  CorrectionMode({this.mode = "medium", this.interruptOnSevere = true});

  Map<String, dynamic> toJson() => {"mode": mode, "interrupt_on_severe": interruptOnSevere};

  factory CorrectionMode.fromJson(Map<String, dynamic> json) => CorrectionMode(
    mode: json["mode"] ?? "medium",
    interruptOnSevere: json["interrupt_on_severe"] ?? true,
  );
}

class PhonemeError {
  final String phoneme;
  final String expected;
  final String actual;
  final String word;
  final String severity;
  final String feedback;

  PhonemeError({
    required this.phoneme,
    required this.expected,
    required this.actual,
    this.word = "",
    required this.severity,
    this.feedback = "",
  });

  factory PhonemeError.fromJson(Map<String, dynamic> json) => PhonemeError(
    phoneme: json["phoneme"] ?? "",
    expected: json["expected"] ?? "",
    actual: json["actual"] ?? "",
    word: json["word"] ?? "",
    severity: json["severity"] ?? "mild",
    feedback: json["feedback"] ?? "",
  );
}

class ScoreDimensions {
  final double phonemeAccuracy;
  final double fluency;
  final double prosody;
  final double completeness;

  ScoreDimensions({
    this.phonemeAccuracy = 0,
    this.fluency = 0,
    this.prosody = 0,
    this.completeness = 0,
  });

  factory ScoreDimensions.fromJson(Map<String, dynamic> json) => ScoreDimensions(
    phonemeAccuracy: (json["phoneme_accuracy"] ?? 0).toDouble(),
    fluency: (json["fluency"] ?? 0).toDouble(),
    prosody: (json["prosody"] ?? 0).toDouble(),
    completeness: (json["completeness"] ?? 0).toDouble(),
  );
}

class CorrectionResult {
  final String level;
  final String userText;
  final String correctedText;
  final List<PhonemeError> errors;
  final double overallScore;
  final ScoreDimensions dimensions;

  CorrectionResult({
    required this.level,
    this.userText = "",
    this.correctedText = "",
    this.errors = const [],
    this.overallScore = 0,
    ScoreDimensions? dimensions,
  }) : dimensions = dimensions ?? ScoreDimensions();

  factory CorrectionResult.fromJson(Map<String, dynamic> json) => CorrectionResult(
    level: json["level"] ?? "mild",
    userText: json["user_text"] ?? "",
    correctedText: json["corrected_text"] ?? "",
    errors: (json["errors"] as List<dynamic>?)
        ?.map((e) => PhonemeError.fromJson(e as Map<String, dynamic>))
        .toList() ?? [],
    overallScore: (json["overall_score"] ?? 0).toDouble(),
    dimensions: json["dimensions"] != null
        ? ScoreDimensions.fromJson(json["dimensions"] as Map<String, dynamic>)
        : null,
  );
}

class ChatMessage {
  final String id;
  final String role; // "user" | "assistant"
  final String text;
  final CorrectionResult? correction;
  final DateTime timestamp;

  ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    this.correction,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

class SceneInfo {
  final String id;
  final String name;
  final String description;

  SceneInfo({required this.id, required this.name, this.description = ""});
}

class VoiceProfile {
  final String profileId;
  final String name;
  final String language;
  final bool isDefault;

  VoiceProfile({
    required this.profileId,
    required this.name,
    this.language = "en",
    this.isDefault = false,
  });
}

enum ConnectionStatus { disconnected, connecting, connected, error }
