# Voice Profiles

Place your speaker reference audio files here for CosyVoice voice cloning.

## Format

- **Format**: WAV, 16kHz, mono, 16-bit PCM
- **Duration**: 5-30 seconds of clean speech
- **Content**: A short paragraph of natural speech in the target language
- **Naming**: `{profile_name}.wav` (e.g., `new_york.wav`)

## Built-in Profiles

| File | Profile ID | Description |
|------|-----------|-------------|
| `new_york.wav` | `new_york` | New York accent (default) |
| `default.wav` | `default` | Neutral English speaker |

## Creating a Profile

1. Record 10-20 seconds of clean speech in a quiet environment
2. Convert to the required format using FFmpeg:
   ```bash
   ffmpeg -i input.mp3 -ar 16000 -ac 1 -sample_fmt s16 output.wav
   ```
3. Place the `.wav` file in this directory
4. The profile will appear in the app's voice selection menu

## Notes

- For best voice cloning results, use audio that matches:
  - The same language you want to practice
  - The speaking style you want the AI to use
  - Consistent background conditions
- The `new_york` profile is the default. If missing, the engine falls
  back to the CosyVoice built-in speaker embedding.
