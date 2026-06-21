import React from "react";

interface Props {
  status: "idle" | "recording" | "processing";
  onStart: () => void;
  onStop: () => Promise<string>;
  disabled?: boolean;
}

export function AudioControls({ status, onStart, onStop, disabled }: Props) {
  const [audioLevel, setAudioLevel] = React.useState(0);
  const animRef = React.useRef<number>();

  // Simulate audio level visualization while recording
  React.useEffect(() => {
    if (status === "recording") {
      const animate = () => {
        setAudioLevel(0.3 + Math.random() * 0.7);
        animRef.current = requestAnimationFrame(animate);
      };
      animRef.current = requestAnimationFrame(animate);
    } else {
      setAudioLevel(0);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    }
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [status]);

  const handleClick = async () => {
    if (status === "recording") {
      await onStop();
    } else {
      onStart();
    }
  };

  const bars = 5;
  const waveform = Array.from({ length: bars }, (_, i) => {
    const center = (i + 0.5) / bars;
    const height = status === "recording" ? Math.sin(center * Math.PI) * audioLevel * 40 + 4 : 4;
    return height;
  });

  return (
    <div className="audio-controls">
      <button
        className={`record-btn ${status}`}
        onClick={handleClick}
        disabled={disabled || status === "processing"}
        title={status === "recording" ? "Stop recording" : "Start recording"}
      >
        {status === "recording" ? (
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
            <rect x="6" y="6" width="4" height="12" rx="1" />
            <rect x="14" y="6" width="4" height="12" rx="1" />
          </svg>
        ) : status === "processing" ? (
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor" className="spin">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6l5.25 3.15L17 12.23l-4-2.37V7z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
        )}
      </button>

      <div className="waveform">
        {waveform.map((h, i) => (
          <div
            key={i}
            className="waveform-bar"
            style={{ height: `${h}px` }}
          />
        ))}
      </div>

      <div className="audio-status">
        {status === "idle" && <span>Tap to speak</span>}
        {status === "recording" && <span className="recording-indicator">● Recording...</span>}
        {status === "processing" && <span>Processing...</span>}
      </div>
    </div>
  );
}
