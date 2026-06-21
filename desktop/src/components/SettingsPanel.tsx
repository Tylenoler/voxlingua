import React from "react";
import type { SceneInfo, VoiceProfile, ConnectionStatus, CorrectionMode } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  scenes: SceneInfo[];
  voices: VoiceProfile[];
  currentScene: string;
  currentVoice: string;
  correctionMode: CorrectionMode;
  llmApiKey: string;
  engineUrl: string;
  connectionStatus: ConnectionStatus;
  onSceneChange: (id: string) => void;
  onVoiceChange: (id: string) => void;
  onCorrectionModeChange: (mode: CorrectionMode) => void;
  onApiKeyChange: (key: string) => void;
  onEngineUrlChange: (url: string) => void;
  onConnect: () => void;
  onDisconnect: () => void;
}

export function SettingsPanel({
  open, onClose, scenes, voices, currentScene, currentVoice,
  correctionMode, llmApiKey, engineUrl, connectionStatus,
  onSceneChange, onVoiceChange, onCorrectionModeChange,
  onApiKeyChange, onEngineUrlChange, onConnect, onDisconnect,
}: Props) {
  if (!open) return null;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>⚙️ Settings</h2>
          <button className="settings-close" onClick={onClose}>✕</button>
        </div>

        <div className="settings-body">
          {/* Connection */}
          <section className="settings-section">
            <h3>Connection</h3>
            <div className="setting-row">
              <label>Engine URL</label>
              <input
                type="text"
                value={engineUrl}
                onChange={(e) => onEngineUrlChange(e.target.value)}
                placeholder="ws://localhost:9876/ws/mobile"
              />
            </div>
            <div className="setting-row">
              <label>Status</label>
              <span className={`conn-status ${connectionStatus}`}>
                {connectionStatus === "connected" && "✅ Connected"}
                {connectionStatus === "connecting" && "🔄 Connecting..."}
                {connectionStatus === "disconnected" && "❌ Disconnected"}
                {connectionStatus === "error" && "⚠️ Error"}
              </span>
              <button
                className="btn-sm"
                onClick={connectionStatus === "connected" ? onDisconnect : onConnect}
              >
                {connectionStatus === "connected" ? "Disconnect" : "Connect"}
              </button>
            </div>
          </section>

          {/* LLM API Key */}
          <section className="settings-section">
            <h3>LLM API Key</h3>
            <div className="setting-row">
              <label>OpenAI / Compatible Key</label>
              <input
                type="password"
                value={llmApiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder="sk-..."
              />
            </div>
          </section>

          {/* Conversation Scene */}
          <section className="settings-section">
            <h3>Conversation Scene</h3>
            <div className="scene-grid">
              {scenes.map((s) => (
                <button
                  key={s.id}
                  className={`scene-btn ${currentScene === s.id ? "active" : ""}`}
                  onClick={() => onSceneChange(s.id)}
                >
                  <span className="scene-name">{s.name}</span>
                  <span className="scene-desc">{s.description}</span>
                </button>
              ))}
            </div>
          </section>

          {/* Voice Profile */}
          <section className="settings-section">
            <h3>Voice Profile</h3>
            <select
              value={currentVoice}
              onChange={(e) => onVoiceChange(e.target.value)}
              className="select-full"
            >
              {voices.map((v) => (
                <option key={v.profile_id} value={v.profile_id}>
                  {v.name} {v.is_default ? "(default)" : ""}
                </option>
              ))}
            </select>
          </section>

          {/* Correction Mode */}
          <section className="settings-section">
            <h3>Correction Mode</h3>
            <div className="correction-options">
              {([
                { value: "off", label: "Off", desc: "No correction feedback" },
                { value: "mild_only", label: "Mild", desc: "Only minor hints" },
                { value: "medium", label: "Medium", desc: "Visual corrections" },
                { value: "all", label: "All", desc: "Full correction + interruption" },
              ] as const).map((opt) => (
                <button
                  key={opt.value}
                  className={`correction-opt ${correctionMode.mode === opt.value ? "active" : ""}`}
                  onClick={() => onCorrectionModeChange({ ...correctionMode, mode: opt.value })}
                >
                  <span className="opt-label">{opt.label}</span>
                  <span className="opt-desc">{opt.desc}</span>
                </button>
              ))}
            </div>
            <div className="setting-row" style={{ marginTop: 8 }}>
              <label>Interrupt on severe errors</label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={correctionMode.interrupt_on_severe}
                  onChange={(e) =>
                    onCorrectionModeChange({ ...correctionMode, interrupt_on_severe: e.target.checked })
                  }
                />
                <span className="toggle-slider" />
              </label>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
