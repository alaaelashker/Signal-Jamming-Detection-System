import numpy as np
import wave
import os

SR = 44100   # sample rate Hz

def save_wav(path: str, data: np.ndarray, sr: int = SR):
    """Write a mono 16-bit PCM WAV file."""
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)    # mono
        wf.setsampwidth(2)    # 16-bit
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())
    size = os.path.getsize(path)
    print(f"  Saved: {path}  ({size:,} bytes)")


def make_alarm(path: str):
    """
    Pulsing siren: frequency sweeps between 800 Hz and 1000 Hz at 3 Hz rate.
    Duration: 1.0 s  (loops seamlessly in pygame)
    """
    duration = 1.0
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)

    # Sinusoidal frequency modulation creates a classic siren sweep
    freq_mod = 800 + 100 * np.sin(2 * np.pi * 3 * t)

    # Integrate frequency to get instantaneous phase (avoids phase jumps)
    phase = np.cumsum(2 * np.pi * freq_mod / SR)

    # Short fade-in / fade-out so the loop clicks are silent
    signal = np.sin(phase)
    fade_n = int(SR * 0.02)   # 20 ms
    signal[:fade_n]  *= np.linspace(0, 1, fade_n)
    signal[-fade_n:] *= np.linspace(1, 0, fade_n)

    data = (signal * 28000).astype(np.int16)
    save_wav(path, data)


def make_hum(path: str):
    """
    Gentle ambient hum: 60 Hz fundamental + harmonics, 2 s loop.
    Very soft volume — just enough to indicate 'system running' state.
    """
    duration = 2.0
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)

    # Layered harmonics of 60 Hz for a realistic electrical-equipment hum
    hum = (
        np.sin(2 * np.pi * 60  * t) * 0.55 +
        np.sin(2 * np.pi * 120 * t) * 0.25 +
        np.sin(2 * np.pi * 180 * t) * 0.12 +
        np.sin(2 * np.pi * 240 * t) * 0.06
    )

    # Smooth fade so the loop is seamless
    fade_n = int(SR * 0.05)   # 50 ms
    fade   = np.ones(len(t))
    fade[:fade_n]  = np.linspace(0, 1, fade_n)
    fade[-fade_n:] = np.linspace(1, 0, fade_n)

    data = (hum * fade * 7000).astype(np.int16)
    save_wav(path, data)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    print("Generating SJDAS audio files...")
    make_alarm(os.path.join(base, "alarm.wav"))
    make_hum(os.path.join(base, "normal_hum.wav"))
    print("Done.  Both files are ready for use with main.py.")