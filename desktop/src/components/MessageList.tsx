/**
 * MessageList — scrollable chat bubble display with correction annotations.
 */

import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="message-list-empty">
        <p>Your conversation will appear here</p>
        <p className="hint">Tap the circle and start speaking</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <div key={m.id} className={`message message-${m.role}`}>
          <div className="message-bubble">
            <p>{m.text}</p>
            {m.correction && m.correction.errors.length > 0 && (
              <div className="message-correction">
                <div className="correction-score">
                  Score: {m.correction.overall_score}
                </div>
                {m.correction.errors.slice(0, 3).map((e, i) => (
                  <div key={i} className={`correction-item severity-${e.severity}`}>
                    <span className="phoneme">{e.phoneme}</span>
                    <span className="arrow">→</span>
                    <span className="actual">{e.actual}</span>
                    <span className="word">&nbsp;in&nbsp;<em>{e.word}</em></span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <span className="message-time">
            {new Date(m.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
