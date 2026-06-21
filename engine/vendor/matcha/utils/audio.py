import torch
import numpy as np
import librosa

def mel_spectrogram(audio, n_fft=1024, hop_length=256, win_length=1024, n_mels=80, sample_rate=22050, fmin=0.0, fmax=8000.0,
                    num_mels=None, sampling_rate=None, hop_size=None, win_size=None, center=True):
    if num_mels is not None:
        n_mels = num_mels
    if sampling_rate is not None:
        sample_rate = sampling_rate
    if hop_size is not None:
        hop_length = hop_size
    if win_size is not None:
        win_length = win_size
    if isinstance(audio, torch.Tensor):
        audio_np = audio.cpu().numpy()
    else:
        audio_np = np.asarray(audio)
    mel = librosa.feature.melspectrogram(y=audio_np.astype(np.float64), sr=sample_rate, n_fft=n_fft,
                                         hop_length=hop_length, win_length=win_length, n_mels=n_mels,
                                         fmin=fmin, fmax=fmax, center=center)
    mel_db = librosa.power_to_db(mel, ref=1.0, top_db=None).astype(np.float32)
    if isinstance(audio, torch.Tensor):
        return torch.from_numpy(mel_db)
    return mel_db
