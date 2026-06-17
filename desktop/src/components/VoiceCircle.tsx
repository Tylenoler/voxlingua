/**
 * VoiceCircle — animated glow circle that responds to app state and audio level.
 *
 * States:
 *   idle       → gentle breathing pulse, blue
 *   recording  → fast pulse + red glow, expands with audio level
 *   processing → rotating ring, orange/yellow
 *   speaking   → pulse with playback, green
 *   error      → static red
 *   connecting → slow pulse, dim blue
 */

import { useEffect, useRef } from "react";
import type { AppStatus } from "../types";

interface Props {
  status: AppStatus;
  audioLevel: number; // 0–1
  onToggle: () => void;
  engineConnected: boolean;
}

export default function VoiceCircle({ status, audioLevel, onToggle, engineConnected }: Props) {
  const circleRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  // ── animation loop ────────────────────────────────────────

  useEffect(() => {
    const circle = circleRef.current;
    const glow = glowRef.current;
    if (!circle || !glow) return;

    let running = true;

    const animate = (ts: number) => {
      if (!running) return;
      timeRef.current = ts / 1000;

      const s = getScale(ts);
      circle.style.transform = `scale(${s})`;

      const { color, shadowSize, opacity } = getVisuals(ts);
      circle.style.backgroundColor = color;
      circle.style.boxShadow = `0 0 ${shadowSize}px ${color}`;
      glow.style.opacity = String(opacity);

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => {
      running = false;
      cancelAnimationFrame(animRef.current);
    };
  }, [status, audioLevel]);

  // ── visual parameter computation ──────────────────────────

  function getScale(ts: number): number {
    const t = ts / 1000;
    switch (status) {
      case "idle": {
        // gentle breathing: 0.95 ↔ 1.05
        const breathe = 0.95 + 0.1 * (Math.sin(t * 1.5) * 0.5 + 0.5);
        return breathe;
      }
      case "recording": {
        // base pulse faster, plus audio level expansion
        const pulse = 0.9 + 0.2 * (Math.sin(t * 6) * 0.5 + 0.5);
        return pulse + audioLevel * 0.3;
      }
      case "processing": {
        // slight pulse
        return 0.95 + 0.05 * Math.sin(t * 4);
      }
      case "speaking": {
        // pulse with playback
        return 0.9 + 0.15 * (Math.sin(t * 5) * 0.5 + 0.5) + audioLevel * 0.2;
      }
      case "connecting":
        return 0.9 + 0.1 * Math.sin(t * 0.8);
      case "error":
        return 1.0;
      default:
        return 1.0;
    }
  }

  function getVisuals(ts: number): { color: string; shadowSize: number; opacity: number } {
    const t = ts / 1000;
    switch (status) {
      case "idle":
        return {
          color: "#4a9eff",
          shadowSize: 20 + 10 * Math.sin(t * 1.5),
          opacity: 0.4 + 0.2 * Math.sin(t * 1.5),
        };
      case "recording":
        return {
          color: "#ff4444",
          shadowSize: 30 + 20 * Math.sin(t * 6) + audioLevel * 40,
          opacity: 0.6 + 0.3 * Math.sin(t * 6),
        };
      case "processing":
        return {
          color: "#ffaa00",
          shadowSize: 25 + 10 * Math.sin(t * 4),
          opacity: 0.5 + 0.2 * Math.sin(t * 4),
        };
      case "speaking":
        return {
          color: "#44ff88",
          shadowSize: 25 + 15 * Math.sin(t * 5),
          opacity: 0.5 + 0.3 * Math.sin(t * 5),
        };
      case "connecting":
        return {
          color: "#3a7ecc",
          shadowSize: 15,
          opacity: 0.3,
        };
      case "error":
        return {
          color: "#ff3333",
          shadowSize: 10,
          opacity: 0.5,
        };
      default:
        return { color: "#4a9eff", shadowSize: 15, opacity: 0.3 };
    }
  }

  // ── label ─────────────────────────────────────────────────

  const labels: Record<AppStatus, string> = {
    connecting: "Connecting…",
    idle: "Tap to speak",
    recording: "Listening…",
    processing: "Thinking…",
    speaking: "Speaking…",
    error: "Error",
  };

  return (
    <div className="voice-circle-container" onClick={onToggle}>
      <div className="voice-circle-glow" ref={glowRef} />
      <div className="voice-circle" ref={circleRef}>
        {status === "recording" && <div className="voice-circle-pulse-ring" />}
        {status === "processing" && (
          <div className="voice-circle-spinner" />
        )}
      </div>
      <span className="voice-circle-label">
        {status === "idle" && !engineConnected
          ? "Disconnected"
          : labels[status]}
      </span>
    </div>
  );
}
