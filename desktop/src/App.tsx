import React, { useCallback, useEffect, useRef, useState } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { AudioControls } from "./components/AudioControls";
import { SettingsPanel } from "./components/SettingsPanel";
import { useAudioRecorder } from "./hooks/useAudioRecorder";
import { useWebSocket } from "./hooks/useWebSocket";
import type { ChatMessage, ConnectionStatus, CorrectionMode, CorrectionResult, SceneInfo, VoiceProfile, WSMessage } from "./types";
import "./App.css";

const DEFAULT_SCENES: SceneInfo[] = [
  { id: "daily_chat", name: "Daily Chat", description: "Casual everyday conversation" },
  { id: "restaurant", name: "Restaurant", description: "Ordering food and drinks" },
  { id: "travel", name: "Travel", description: "Airport, hotel, directions" },
  { id: "interview", name: "Job Interview", description: "Professional interview practice" },
];

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [currentScene, setCurrentScene] = useState("daily_chat");
  const [currentVoice, setCurrentVoice] = useState("new_york");
  const [availableVoices, setAvailableVoices] = useState<VoiceProfile[]>([]);
  const [correctionMode, setCorrectionMode] = useState<CorrectionMode>({
    mode: "medium",
    interrupt_on_severe: true,
  });
  const [llmApiKey, setLlmApiKey] = useState(() => localStorage.getItem("voxlingua_api_key") || "");
  const [engineUrl, setEngineUrl] = useState(() => localStorage.getItem("voxlingua_engine_url") || "ws://localhost:9876/ws/mobile");
  const [isPlaying, setIsPlaying] = useState(false);
  const sessionIdRef = useRef<string>("");

  // Fetch available voices from engine REST API
  useEffect(() => {
    const httpUrl = engineUrl.replace(/^ws:/, "http:").replace(/\/ws\/.*$/, "");
    fetch(`${httpUrl}/api/tts/voices`)
      .then((r) => r.json())
      .then((data) => {
        if (data.voices && data.voices.length > 0) {
          setAvailableVoices(data.voices);
          const def = data.voices.find((v: VoiceProfile) => v.is_default);
          if (def) setCurrentVoice(def.profile_id);
        }
      })
      .catch(() => {
        // Engine not running yet, use fallback
        setAvailableVoices([
          { profile_id: "new_york", name: "New York Accent (default)", language: "en", is_default: true },
        ]);
      });
  }, []);

  const handleWSMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "handshake_ack": {
        sessionIdRef.current = msg.payload.session_id as string;
        break;
      }
      case "audio_stream_start": {
        const text = msg.payload.text as string;
        if (text) {
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              role: "assistant",
              text,
              timestamp: Date.now(),
            },
          ]);
        }
        break;
      }
      case "correction": {
        const correction = msg.payload as unknown as CorrectionResult;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant") {
            return prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, correction } : m
            );
          }
          return prev;
        });
        break;
      }
      case "stt_result": {
        const transcript = msg.payload.text as string;
        if (transcript) {
          setMessages((prev) => {
            const lastUserIdx = [...prev].reverse().findIndex((m) => m.role === "user");
            if (lastUserIdx >= 0) {
              const idx = prev.length - 1 - lastUserIdx;
              return prev.map((m, i) =>
                i === idx ? { ...m, text: transcript } : m
              );
            }
            return prev;
          });
        }
        break;
      }
      case "error": {
        console.error("[Engine Error]", msg.payload.message);
        break;
      }
    }
  }, []);

  const { status: wsStatus, connect, disconnect, send } = useWebSocket({
    url: engineUrl,
    onMessage: handleWSMessage,
  });

  const { status: recStatus, startRecording, stopRecording } = useAudioRecorder();

  const urlRef = useRef(engineUrl);
  urlRef.current = engineUrl;

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, []); // eslint-disable-line

  // Save settings
  useEffect(() => { localStorage.setItem("voxlingua_api_key", llmApiKey); }, [llmApiKey]);
  useEffect(() => { localStorage.setItem("voxlingua_engine_url", engineUrl); }, [engineUrl]);

  // Send scene/voice/mode changes
  useEffect(() => {
    if (wsStatus === "connected") {
      send({ type: "set_scene", payload: { scene: currentScene, language: "en" } });
    }
  }, [currentScene, wsStatus]); // eslint-disable-line

  useEffect(() => {
    if (wsStatus === "connected") {
      send({ type: "set_voice", payload: { voice_profile_id: currentVoice } });
    }
  }, [currentVoice, wsStatus]); // eslint-disable-line

  useEffect(() => {
    if (wsStatus === "connected") {
      send({ type: "set_correction_mode", payload: correctionMode as unknown as Record<string, unknown> });
    }
  }, [correctionMode, wsStatus]); // eslint-disable-line

  const handleRecordStart = useCallback(() => {
    startRecording();
  }, [startRecording]);

  const handleRecordStop = useCallback(async (): Promise<string> => {
    try {
      const audioB64 = await stopRecording();
      // Show a placeholder while waiting for engine response
      const userMsgId = `user-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: userMsgId,
          role: "user",
          text: "🎤 (processing...)",
          timestamp: Date.now(),
        },
      ]);
      send({
        type: "audio_input",
        payload: {
          data: audioB64,
          format: "webm",
          sample_rate: 48000,
        },
      });
      return audioB64;
    } catch (err) {
      console.error("Recording failed:", err);
      return "";
    }
  }, [stopRecording, send]);

  // Play TTS audio via engine REST API
  const synthRef = useRef<HTMLAudioElement | null>(null);

  const handlePlayAudio = useCallback(async (text: string) => {
    setIsPlaying(true);
    try {
      const engineHttpUrl = engineUrl.replace(/^ws:/, "http:").replace(/\/ws\/.*$/, "");
      const resp = await fetch(`${engineHttpUrl}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice_profile: currentVoice, stream: false }),
      });
      if (resp.ok) {
        const result = await resp.json();
        // Decode base64 PCM data and play
        const binaryStr = atob(result.data);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        // Convert PCM f32le to WAV blob for playback
        const sampleRate = result.sample_rate || 24000;
        const numSamples = bytes.byteLength / 4;
        const wavHeader = new ArrayBuffer(44);
        const dv = new DataView(wavHeader);
        const writeStr = (off: number, s: string) => {
          for (let i = 0; i < s.length; i++) dv.setUint8(off + i, s.charCodeAt(i));
        };
        writeStr(0, "RIFF");
        dv.setUint32(4, 36 + bytes.byteLength, true);
        writeStr(8, "WAVE");
        writeStr(12, "fmt ");
        dv.setUint32(16, 16, true);
        dv.setUint16(20, 1, true); // PCM
        dv.setUint16(22, 1, true); // mono
        dv.setUint32(24, sampleRate, true);
        dv.setUint32(28, sampleRate * 2, true);
        dv.setUint16(32, 2, true);
        dv.setUint16(34, 16, true);
        writeStr(36, "data");
        dv.setUint32(40, bytes.byteLength, true);

        const wavBlob = new Blob([wavHeader, bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(wavBlob);
        const audio = new Audio(url);
        audio.onended = () => { setIsPlaying(false); URL.revokeObjectURL(url); };
        audio.onerror = () => { setIsPlaying(false); URL.revokeObjectURL(url); };
        synthRef.current = audio;
        audio.play();
        return;
      }
    } catch (e) {
      console.warn("[TTS] Engine REST failed, using browser fallback:", e);
    }

    // Browser SpeechSynthesis fallback
    if (!window.speechSynthesis) {
      setIsPlaying(false);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const englishVoice = voices.find((v) => v.lang.startsWith("en"));
    if (englishVoice) utterance.voice = englishVoice;
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);
    window.speechSynthesis.speak(utterance);
  }, [engineUrl, currentVoice]);

  useEffect(() => {
    return () => {
      if (synthRef.current) { synthRef.current.pause(); synthRef.current = null; }
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  const handleConnect = useCallback(() => { connect(); }, [connect]);
  const handleDisconnect = useCallback(() => { disconnect(); }, [disconnect]);

  const correctionStatusText = () => {
    if (!wsStatus) return "";
    return correctionMode.mode === "off"
      ? "Correction OFF"
      : `Correction: ${correctionMode.mode}`;
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <h1 className="logo">VoxLingua</h1>
          <span className="badge scene-badge">
            {DEFAULT_SCENES.find((s) => s.id === currentScene)?.name || "Daily Chat"}
          </span>
          <span className="badge correction-badge-status">{correctionStatusText()}</span>
        </div>
        <div className="topbar-right">
          <span className={`connection-dot ${wsStatus}`} title={`${wsStatus}`} />
          <button className="settings-btn" onClick={() => setSettingsOpen(true)}>
            ⚙️
          </button>
        </div>
      </header>

      <main className="main-content">
        <ChatPanel
          messages={messages}
          onPlayAudio={handlePlayAudio}
          isPlaying={isPlaying}
        />
      </main>

      <footer className="bottom-bar">
        <AudioControls
          status={recStatus}
          onStart={handleRecordStart}
          onStop={handleRecordStop}
          disabled={wsStatus !== "connected"}
        />
        {wsStatus !== "connected" && (
          <div className="connect-prompt">
            {wsStatus === "disconnected" && (
              <button className="connect-btn" onClick={handleConnect}>
                Connect to Engine
              </button>
            )}
            {wsStatus === "connecting" && <span>Connecting to engine...</span>}
            {wsStatus === "error" && (
              <div>
                <span>Connection failed. </span>
                <button className="connect-btn" onClick={handleConnect}>
                  Retry
                </button>
              </div>
            )}
          </div>
        )}
      </footer>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        scenes={DEFAULT_SCENES}
        voices={availableVoices}
        currentScene={currentScene}
        currentVoice={currentVoice}
        correctionMode={correctionMode}
        llmApiKey={llmApiKey}
        engineUrl={engineUrl}
        connectionStatus={wsStatus}
        onSceneChange={setCurrentScene}
        onVoiceChange={setCurrentVoice}
        onCorrectionModeChange={setCorrectionMode}
        onApiKeyChange={setLlmApiKey}
        onEngineUrlChange={setEngineUrl}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />
    </div>
  );
}
