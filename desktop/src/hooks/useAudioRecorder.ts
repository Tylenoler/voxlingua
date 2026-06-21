import { useCallback, useRef, useState } from "react";

export function useAudioRecorder() {
  const [status, setStatus] = useState<"idle" | "recording" | "processing">("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      chunks.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      recorder.start(100); // collect data every 100ms
      mediaRecorder.current = recorder;
      setStatus("recording");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Microphone access denied";
      setError(msg);
      setStatus("idle");
    }
  }, []);

  const stopRecording = useCallback(
    (): Promise<string> => {
      return new Promise((resolve, reject) => {
        const recorder = mediaRecorder.current;
        if (!recorder || recorder.state === "inactive") {
          reject(new Error("No active recording"));
          return;
        }

        recorder.onstop = async () => {
          const blob = new Blob(chunks.current, { type: recorder.mimeType });
          chunks.current = [];

          // Stop all audio tracks
          recorder.stream.getTracks().forEach((t) => t.stop());

          // Convert to base64
          const buffer = await blob.arrayBuffer();
          const bytes = new Uint8Array(buffer);
          let binary = "";
          for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          const base64 = btoa(binary);
          setStatus("idle");
          resolve(base64);
        };

        recorder.stop();
        setStatus("processing");
      });
    },
    []
  );

  const stopTracks = useCallback(() => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      mediaRecorder.current.stream.getTracks().forEach((t) => t.stop());
      mediaRecorder.current = null;
    }
    setStatus("idle");
  }, []);

  return { status, error, startRecording, stopRecording, stopTracks };
}
