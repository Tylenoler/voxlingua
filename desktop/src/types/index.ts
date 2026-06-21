// VoxLingua — TypeScript type definitions

export interface CorrectionMode {
  mode: "off" | "mild_only" | "medium" | "all";
  interrupt_on_severe: boolean;
}

export interface PhonemeError {
  phoneme: string;
  expected: string;
  actual: string;
  word: string;
  severity: "mild" | "medium" | "severe";
  feedback: string;
}

export interface ScoreDimensions {
  phoneme_accuracy: number;
  fluency: number;
  prosody: number;
  completeness: number;
}

export interface CorrectionResult {
  level: "mild" | "medium" | "severe";
  user_text: string;
  corrected_text: string;
  errors: PhonemeError[];
  overall_score: number;
  dimensions: ScoreDimensions;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  correction?: CorrectionResult;
  timestamp: number;
}

export interface SceneInfo {
  id: string;
  name: string;
  description: string;
}

export interface VoiceProfile {
  profile_id: string;
  name: string;
  language: string;
  is_default: boolean;
}

export interface EngineStatus {
  status: string;
  version: string;
  llm_connected: boolean;
  active_sessions: number;
  connected_devices: number;
}

export type WSMessageType =
  | "handshake"
  | "handshake_ack"
  | "audio_input"
  | "audio_stream_start"
  | "audio_stream_chunk"
  | "audio_stream_end"
  | "correction"
  | "set_scene"
  | "scene_updated"
  | "set_voice"
  | "voice_updated"
  | "stt_result"
  | "set_correction_mode"
  | "correction_mode_updated"
  | "error";

export interface WSMessage {
  type: WSMessageType;
  payload: Record<string, unknown>;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";
export type RecorderStatus = "idle" | "recording" | "processing" | "error";

