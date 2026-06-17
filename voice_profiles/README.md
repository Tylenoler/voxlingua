# Voice Profiles

Each sub-directory here is a **voice profile** that the TTS engine uses for
**zero-shot voice cloning** with CosyVoice.

A voice profile = a short reference recording of a person speaking +
the text transcription of that recording.  The model uses this to clone the
speaker's voice, accent, and prosody.

## How to create a profile

### 1. Record reference audio

- **Duration:** 3–10 seconds (shorter = less accurate, longer ≠ better)
- **Format:** WAV, mono, any sample rate
- **Content:** A single clean sentence.  Read it naturally — this is what the
  model will use to learn the voice.
- **Environment:** Quiet room, no background noise or music

### 2. Save the files

For a profile called `new_york`, create:

```
voice_profiles/
└── new_york/
    ├── reference.wav      # The recording (WAV, mono, any sample rate)
    └── reference.txt      # The exact words spoken in reference.wav
```

### 3. Example

**`reference.txt`** (must match the audio exactly):
```
Hey, how you doin'? I'm from New York and I love this city.
```

**`reference.wav`** — the recording of that sentence.

### 4. Restart the engine

The engine scans `voice_profiles/` at startup and registers each valid profile.
Check readiness:

```bash
curl http://localhost:9876/api/voices
```

If the profile appears in the response with `method: "zero_shot"` it's ready to use.

## Getting a New York accent voice

Since the project focuses on **New York accent practice**, you'll want a
reference recording of a person with a clear NYC accent.  Options:

1. **Record yourself** if you already have the target accent.
2. **Use a public-domain clip** from sources like:
   - [LibriVox](https://librivox.org) — public-domain audiobooks
   - [The Public Domain Review](https://publicdomainreview.org) — historical recordings
3. **Commission or find** a short voice sample from a voice actor with a NYC accent.

The default profile the engine expects is `new_york`.  If no profiles are
registered, the engine falls back to CosyVoice's built-in SFT speakers.
