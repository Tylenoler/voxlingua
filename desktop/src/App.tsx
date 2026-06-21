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

const DEFAULT_VOICES: VoiceProfile[] = [
  { profile_id: "new_york", name: "New York Accent (default)", language: "en", is_default: true },
];

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [currentScene, setCurrentScene] = useState("daily_chat");
  const [currentVoice, setCurrentVoice] = useState("new_york");
  const [correctionMode, setCorrectionMode] = useState<CorrectionMode>({
    mode: "medium",
    interrupt_on_severe: true,
  });
  const [llmApiKey, setLlmApiKey] = useState(() => localStorage.getItem("voxlingua_api_key") || "");
  const [engineUrl, setEngineUrl] = useState(() => localStorage.getItem("voxlingua_engine_url") || "ws://localhost:9876/ws/mobile");
  const [isPlaying, setIsPlaying] = useState(false);
  const sessionIdRef = useRef<string>("");

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

  // Save API key
  useEffect(() => {
    localStorage.setItem("voxlingua_api_key", llmApiKey);
  }, [llmApiKey]);

  useEffect(() => {
    localStorage.setItem("voxlingua_engine_url", engineUrl);
  }, [engineUrl]);

  // Send scene change
  useEffect(() => {
    if (wsStatus === "connected") {
      send({ type: "set_scene", payload: { scene: currentScene, language: "en" } });
    }
  }, [currentScene, wsStatus]); // eslint-disable-line

  // Send voice change
  useEffect(() => {
    if (wsStatus === "connected") {
      send({ type: "set_voice", payload: { voice_profile_id: currentVoice } });
    }
  }, [currentVoice, wsStatus]); // eslint-disable-line

  // Send correction mode change
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
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: "user",
          text: "🎤 (audio sent to engine)",
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

  const handlePlayAudio = useCallback((_text: string) => {
    setIsPlaying(true);
    setTimeout(() => setIsPlaying(false), 2000);
  }, []);

  const handleConnect = useCallback(() => {
    connect();
  }, [connect]);

  const handleDisconnect = useCallback(() => {
    disconnect();
  }, [disconnect]);

  const correctionStatusText = () => {
    if (!wsStatus) return "";
    return correctionMode.mode === "off"
      ? "Correction OFF"
      : `Correction: ${correctionMode.mode}`;
  };

  return (
    <div className="app">
      {/* Top Bar */}
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

      {/* Main Content */}
      <main className="main-content">
        <ChatPanel
          messages={messages}
          onPlayAudio={handlePlayAudio}
          isPlaying={isPlaying}
        />
      </main>

      {/* Bottom Controls */}
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

      {/* Settings */}
      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        scenes={DEFAULT_SCENES}
        voices={DEFAULT_VOICES}
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
