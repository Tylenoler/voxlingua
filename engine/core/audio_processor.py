# Audio processing utilities for VoxLingua

import base64
from io import BytesIO
import numpy as np
import soundfile as sf


def decode_base64_audio(data_b64: str, sample_rate: int = 16000, dtype: type = np.float64) -> np.ndarray:
    """Decode base64-encoded audio to numpy array.

    Supports WAV (RIFF header), WebM/Opus, and raw PCM (f32le).
    """
    raw = base64.b64decode(data_b64)
    buf = BytesIO(raw)

    # WAV with RIFF header
    if raw[:4] == b"RIFF":
        try:
            audio, sr = sf.read(buf)
            if sr != sample_rate:
                from librosa import resample
                audio = resample(audio, orig_sr=sr, target_sr=sample_rate)
            return audio.astype(dtype)
        except Exception:
            pass

    # WebM/Opus or other container formats — use pydub + ffmpeg
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(buf)
        if seg.channels > 1:
            seg = seg.set_channels(1)
        if seg.frame_rate != sample_rate:
            seg = seg.set_frame_rate(sample_rate)
        raw_audio = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
        return raw_audio.astype(dtype)
    except Exception:
        pass

    # Fallback: treat as raw PCM f32le
    audio = np.frombuffer(raw, dtype=np.float32)
    return audio.astype(dtype)
def encode_pcm_f32le(audio: np.ndarray, sample_rate: int = 24000) -> str:
    """Encode numpy audio array to base64 PCM f32le."""
    pcm = audio.astype(np.float32).tobytes()
    return base64.b64encode(pcm).decode("utf-8")


def encode_wav(audio: np.ndarray, sample_rate: int = 24000) -> str:
    """Encode numpy audio array to base64 WAV."""
    buf = BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def chunk_audio(audio: np.ndarray, chunk_size_ms: int = 200, sample_rate: int = 24000) -> list[np.ndarray]:
    """Split audio into fixed-size chunks for streaming."""
    chunk_samples = int(sample_rate * chunk_size_ms / 1000)
    chunks = []
    for start in range(0, len(audio), chunk_samples):
        chunk = audio[start:start + chunk_samples]
        chunks.append(chunk)
    return chunks


def audio_duration(audio: np.ndarray, sample_rate: int) -> float:
    """Get audio duration in seconds."""
    return len(audio) / sample_rate


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """Normalize audio to [-1, 1] range."""
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        return audio / max_val
    return audio

