/**
 * useVoxLingua — main hook orchestrating WebSocket, audio, and UI state.
 *
 * State machine: connecting → idle → recording → processing → speaking → idle
 */

import { useState, useRef, useCallback, useEffect } from "react";
import type {
  ChatMessage,
  AppStatus,
  AppSettings,
  CorrectionResult,
} from "../types";
import { DEFAULT_SETTINGS } from "../types";
import { apiClient } from "../services/api";
import {
  startRecording,
  encodePcmF32,
  playAudioChunk,
  resumeAudio,
} from "../services/audio";

const SETTINGS_KEY = "voxlingua-settings";
const RECORDING_SAMPLE_RATE = 16000;

function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return DEFAULT_SETTINGS;
}

function saveSettings(s: AppSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

let msgId = 0;

export interface VoxLinguaState {
  status: AppStatus;
  messages: ChatMessage[];
  sessionId: string | null;
  audioLevel: number;
  correction: CorrectionResult | null;
  settings: AppSettings;
  error: string | null;
  engineConnected: boolean;
  toggleRecord: () => void;
  updateSettings: (patch: Partial<AppSettings>) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useVoxLingua(): VoxLinguaState {
  const [status, setStatus] = useState<AppStatus>("connecting");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [correction, setCorrection] = useState<CorrectionResult | null>(null);
  const [settings, setSettings] = useState<AppSettings>(loadSettings);
  const [error, setError] = useState<string | null>(null);
  const [engineConnected, setEngineConnected] = useState(false);

  const ws = useRef<WebSocket | null>(null);
  const stopRec = useRef<(() => void) | null>(null);
  const isRec = useRef(false);
  const audioBuf = useRef<Float32Array[]>([]);
  const flushTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── WebSocket ──────────────────────────────────────────────

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    setStatus("connecting");

    const sock = new WebSocket(settings.wsUrl);
    ws.current = sock;

    sock.onopen = () => {
      sock.send(
        JSON.stringify({
          type: "handshake",
          payload: { client: "voxlingua-desktop", version: "1.0.0" },
        })
      );
    };

    sock.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        handleMsg(msg);
      } catch {
        /* skip malformed */
      }
    };

    sock.onclose = () => {
      setStatus("idle");
      setSessionId(null);
      setEngineConnected(false);
      ws.current = null;
    };

    sock.onerror = () => {
      setError("Cannot reach engine — ensure the Python server is running");
      setStatus("error");
      setEngineConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.wsUrl]);

  const disconnect = useCallback(() => {
    ws.current?.close();
    ws.current = null;
    setSessionId(null);
    setEngineConnected(false);
    setStatus("idle");
  }, []);

  // ── message handler ───────────────────────────────────────

  const handleMsg = useCallback((msg: any) => {
    const t = msg.type || "";
    const p = msg.payload || {};

    switch (t) {
      case "handshake_ack": {
        const sid: string = p.session_id || "";
        setSessionId(sid);
        setEngineConnected(true);
        setStatus("idle");
        apiClient.getStatus().catch(() => {});
        break;
      }
      case "audio_stream_start": {
        setStatus("speaking");
        const text: string = p.text || "";
        setMessages((prev) => [
          ...prev,
          { id: `m-${++msgId}`, role: "assistant", text, timestamp: Date.now() },
        ]);
        if (p.data) playAudioChunk(p.data, p.sample_rate || 24000).catch(() => {});
        break;
      }
      case "audio_stream_chunk": {
        if (p.data) playAudioChunk(p.data, 24000).catch(() => {});
        break;
      }
      case "audio_stream_end": {
        setStatus("idle");
        if (p.data) playAudioChunk(p.data, 24000).catch(() => {});
        break;
      }
      case "correction": {
        const cr: CorrectionResult = p;
        setCorrection(cr);
        setMessages((prev) => {
          const copy = [...prev];
          for (let i = copy.length - 1; i >= 0; i--) {
            if (copy[i].role === "assistant") {
              copy[i] = { ...copy[i], correction: cr };
              break;
            }
          }
          return copy;
        });
        break;
      }
      case "error": {
        setError(p.message || "Engine error");
        setStatus("idle");
        break;
      }
      // acknowledgements — no UI action
      default:
        break;
    }
  }, []);

  // ── flush accumulated audio over WS ───────────────────────

  const flushAudio = useCallback(() => {
    if (!audioBuf.current.length) return;
    if (ws.current?.readyState !== WebSocket.OPEN) return;

    let total = 0;
    for (const c of audioBuf.current) total += c.length;
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of audioBuf.current) {
      merged.set(c, off);
      off += c.length;
    }
    audioBuf.current = [];

    ws.current.send(
      JSON.stringify({
        type: "audio_input",
        payload: {
          data: encodePcmF32(merged),
          format: "pcm_f32le",
          sample_rate: RECORDING_SAMPLE_RATE,
          session_id: sessionId,
        },
      })
    );
  }, [sessionId]);

  // ── recording ─────────────────────────────────────────────

  const startRecord = useCallback(async () => {
    try {
      await resumeAudio();
      audioBuf.current = [];

      const stop = await startRecording(
        (samples) => {
          audioBuf.current.push(samples);
          // RMS → audio level (0–1)
          let sum = 0;
          for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
          setAudioLevel(Math.min(1, Math.sqrt(sum / samples.length) * 3));
        },
        (err) => setError(err.message)
      );

      stopRec.current = stop;
      isRec.current = true;
      setStatus("recording");

      // Flush to engine every 500ms
      flushTimer.current = setInterval(() => flushAudio(), 500);
    } catch (err: any) {
      setError(err.message || "Microphone access denied");
      setStatus("idle");
    }
  }, [flushAudio]);

  const stopRecord = useCallback(() => {
    isRec.current = false;
    if (flushTimer.current) {
      clearInterval(flushTimer.current);
      flushTimer.current = null;
    }
    stopRec.current?.();
    stopRec.current = null;
    flushAudio();
    setAudioLevel(0);
    setStatus("processing");
  }, [flushAudio]);

  const toggleRecord = useCallback(() => {
    if (isRec.current) stopRecord();
    else startRecord();
  }, [startRecord, stopRecord]);

  // ── settings ──────────────────────────────────────────────

  const updateSettings = useCallback(
    (patch: Partial<AppSettings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...patch };
        saveSettings(next);
        if (ws.current?.readyState === WebSocket.OPEN && sessionId) {
          if (patch.voiceProfile) {
            ws.current.send(
              JSON.stringify({
                type: "set_voice",
                payload: { voice_profile_id: patch.voiceProfile },
              })
            );
          }
          if (patch.correctionMode) {
            ws.current.send(
              JSON.stringify({
                type: "set_correction_mode",
                payload: { mode: patch.correctionMode },
              })
            );
          }
        }
        return next;
      });
    },
    [sessionId]
  );

  // ── lifecycle ─────────────────────────────────────────────

  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  return {
    status,
    messages,
    sessionId,
    audioLevel,
    correction,
    settings,
    error,
    engineConnected,
    toggleRecord,
    updateSettings,
    connect,
    disconnect,
  };
}
