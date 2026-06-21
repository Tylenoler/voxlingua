import React from "react";
import type { ChatMessage, CorrectionResult } from "../types";

interface Props {
  messages: ChatMessage[];
  onPlayAudio?: (text: string) => void;
  isPlaying?: boolean;
}

export function ChatPanel({ messages, onPlayAudio, isPlaying }: Props) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-empty">
        <div className="chat-empty-icon">🗣️</div>
        <p>Press the microphone button and start speaking</p>
        <p className="chat-empty-hint">Your conversation with AI will appear here</p>
      </div>
    );
  }

  return (
    <div className="chat-panel">
      {messages.map((msg) => (
        <div key={msg.id} className={`chat-bubble ${msg.role}`}>
          <div className="chat-bubble-header">
            <span className="chat-bubble-avatar">
              {msg.role === "user" ? "👤" : "🤖"}
            </span>
            <span className="chat-bubble-role">
              {msg.role === "user" ? "You" : "VoxLingua"}
            </span>
            <span className="chat-bubble-time">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="chat-bubble-text">{msg.text}</div>

          {msg.role === "assistant" && onPlayAudio && (
            <button
              className="chat-play-btn"
              onClick={() => onPlayAudio(msg.text)}
              disabled={isPlaying}
              title="Play audio"
            >
              {isPlaying ? "🔊 Playing..." : "🔈 Play"}
            </button>
          )}

          {msg.correction && (
            <CorrectionBadge correction={msg.correction} />
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function CorrectionBadge({ correction }: { correction: CorrectionResult }) {
  const levelColor =
    correction.level === "severe"
      ? "var(--error)"
      : correction.level === "medium"
        ? "var(--warning)"
        : "var(--success)";

  return (
    <div className="correction-badge" style={{ borderLeftColor: levelColor }}>
      <div className="correction-badge-header">
        <span>Pronunciation Score: {correction.overall_score.toFixed(0)}</span>
        <span className="correction-level" style={{ color: levelColor }}>
          {correction.level.toUpperCase()}
        </span>
      </div>
      {correction.errors.length > 0 && (
        <div className="correction-errors">
          {correction.errors.slice(0, 3).map((err, i) => (
            <div key={i} className="correction-error-item">
              <span className="phoneme-tag">{err.phoneme}</span>
              <span className="phoneme-arrow">→</span>
              <span className="phoneme-wrong">{err.actual}</span>
              <span className="phoneme-feedback">{err.feedback}</span>
            </div>
          ))}
          {correction.errors.length > 3 && (
            <div className="correction-more">
              +{correction.errors.length - 3} more errors
            </div>
          )}
        </div>
      )}
      <div className="correction-dims">
        {[
          { label: "Accuracy", value: correction.dimensions.phoneme_accuracy },
          { label: "Fluency", value: correction.dimensions.fluency },
          { label: "Prosody", value: correction.dimensions.prosody },
          { label: "Complete", value: correction.dimensions.completeness },
        ].map((d) => (
          <div key={d.label} className="dim-bar">
            <span className="dim-label">{d.label}</span>
            <div className="dim-track">
              <div
                className="dim-fill"
                style={{ width: `${Math.min(d.value, 100)}%` }}
              />
            </div>
            <span className="dim-value">{d.value.toFixed(0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
