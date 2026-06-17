/** Engine status response from GET /api/status */
export interface EngineStatus {
  status: string;
  version: string;
  llm_connected: boolean;
  stt_loaded: boolean;
  tts_loaded: boolean;
  aligner_loaded: boolean;
  active_sessions: number;
  connected_devices: number;
}

/** Chat message displayed in the UI */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  correction?: CorrectionResult;
}

/** App status for UI state machine */
export type AppStatus =
  | "connecting"
  | "idle"
  | "recording"
  | "processing"
  | "speaking"
  | "error";

/** Correction result from the engine */
export interface CorrectionResult {
  level: "mild" | "medium" | "severe";
  user_text: string;
  corrected_text: string;
  errors: PhonemeError[];
  overall_score: number;
  dimensions: ScoreDimensions;
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
  grammar?: number;
}

/** App settings stored in localStorage */
export interface AppSettings {
  engineUrl: string;
  wsUrl: string;
  voiceProfile: string;
  correctionMode: "off" | "mild_only" | "medium" | "all";
}

export const DEFAULT_SETTINGS: AppSettings = {
  engineUrl: "http://localhost:9876",
  wsUrl: "ws://localhost:9876/ws/mobile",
  voiceProfile: "new_york",
  correctionMode: "medium",
};
