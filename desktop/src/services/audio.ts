/**
 * Audio recording and playback utilities.
 *
 * Recording: captures 16 kHz PCM f32 mono via AudioContext.
 * Playback: decodes base64 PCM f32le and plays via AudioContext.
 */

const TARGET_SAMPLE_RATE = 16000;

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  }
  return audioCtx;
}

/** Start recording, yielding PCM f32 chunks via callback. */
export async function startRecording(
  onChunk: (samples: Float32Array) => void,
  onError: (err: Error) => void,
): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const ctx = getAudioContext();
  const source = ctx.createMediaStreamSource(stream);

  // ScriptProcessorNode (deprecated but universal fallback)
  const processor = ctx.createScriptProcessor(2048, 1, 1);
  source.connect(processor);
  processor.connect(ctx.destination);

  const handleAudio = (e: AudioProcessingEvent) => {
    const input = e.inputBuffer.getChannelData(0);
    // input is Float32Array at ctx.sampleRate
    onChunk(new Float32Array(input));
  };

  processor.onaudioprocess = handleAudio;

  return () => {
    processor.onaudioprocess = null;
    source.disconnect();
    processor.disconnect();
    stream.getTracks().forEach((t) => t.stop());
  };
}

/** Float32Array → base64 PCM f32le string */
export function encodePcmF32(samples: Float32Array): string {
  const bytes = new Uint8Array(samples.buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/** base64 PCM f32le → AudioBuffer, then play immediately */
export function playAudioChunk(base64: string, sampleRate = 24000): Promise<void> {
  const ctx = getAudioContext();
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const floats = new Float32Array(bytes.buffer);

  const buffer = ctx.createBuffer(1, floats.length, sampleRate);
  buffer.getChannelData(0).set(floats);

  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(ctx.destination);
  source.start();

  return new Promise((resolve) => {
    source.onended = () => resolve();
  });
}

/** Resume AudioContext (must be called from user gesture) */
export function resumeAudio(): Promise<void> {
  const ctx = getAudioContext();
  if (ctx.state === "suspended") {
    return ctx.resume();
  }
  return Promise.resolve();
}
