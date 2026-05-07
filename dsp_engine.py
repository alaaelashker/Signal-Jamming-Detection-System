import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import threading
 
 
# ─── Result Container ─────────────────────────────────────────────────────────
 
@dataclass
class DSPResult:
    """Encapsulates one frame of DSP output for UI consumption."""
    # Time domain
    time_axis: np.ndarray = field(default_factory=lambda: np.array([]))
    clean_signal: np.ndarray = field(default_factory=lambda: np.array([]))
    jammed_signal: np.ndarray = field(default_factory=lambda: np.array([]))
    noise_signal: np.ndarray = field(default_factory=lambda: np.array([]))
 
    # Frequency domain
    freq_axis: np.ndarray = field(default_factory=lambda: np.array([]))
    power_spectrum_clean: np.ndarray = field(default_factory=lambda: np.array([]))
    power_spectrum_jammed: np.ndarray = field(default_factory=lambda: np.array([]))
 
    # Metrics
    snr_db: float = 0.0
    signal_power_db: float = 0.0
    noise_power_db: float = 0.0
    peak_frequency: float = 0.0
    snr_threshold: float = 10.0
 
    # Detection
    jamming_detected: bool = False
    jamming_confidence: float = 0.0   # 0.0 → 1.0
    severity: str = "NONE"            # NONE / LOW / MEDIUM / HIGH / CRITICAL
 
    # Parameters snapshot
    frequency: float = 100.0
    amplitude: float = 1.0
    noise_intensity: float = 0.0
 
 
# ─── DSP Engine ───────────────────────────────────────────────────────────────

class DSPEngine:
    def __init__(
        self,
        sample_rate: int = 2000,
        duration: float = 0.5,
        base_freq: float = 100.0,
        amplitude: float = 1.0,
        noise_intensity: float = 0.0,
        snr_threshold: float = 10.0
    ):
        # ── Sampling Parameters ──────────────────────────────────────────
        self.sample_rate = sample_rate       # Hz — samples per second
        self.duration = duration             # seconds per analysis window
        self.n_samples = int(sample_rate * duration)  # total sample count
 
        # ── Signal Parameters (thread-safe with lock) ─────────────────────
        self._lock = threading.Lock()
        self._frequency = base_freq          # carrier frequency [Hz]
        self._amplitude = amplitude          # signal amplitude [linear]
        self._noise_intensity = noise_intensity  # Gaussian noise σ
        self._snr_threshold = snr_threshold  # detection threshold [dB]
 
        # ── Time axis (constant for this window size) ─────────────────────
        # t = [0, 1/fs, 2/fs, ..., (N-1)/fs]
        self.time_axis = np.linspace(0, duration, self.n_samples, endpoint=False)
 
        # ── Frequency axis for FFT output ─────────────────────────────────
        # rfftfreq returns N//2 + 1 unique positive frequencies
        self.freq_axis = np.fft.rfftfreq(self.n_samples, d=1.0 / sample_rate)
 
        # ── History for smoothing (exponential moving average) ────────────
        self._snr_history = []
        self._ema_alpha = 0.25   # smoothing factor
 
    # ─────────────────────────────────────────────────────────────────────────
    # Parameter Setters (thread-safe)
    # ─────────────────────────────────────────────────────────────────────────
 
    def set_frequency(self, freq: float):
        with self._lock:
            # Clamp to valid range (Nyquist limit: fs/2)
            self._frequency = np.clip(freq, 10.0, self.sample_rate / 2 - 10)
 
    def set_amplitude(self, amp: float):
        with self._lock:
            self._amplitude = np.clip(amp, 0.1, 5.0)
 
    def set_noise_intensity(self, intensity: float):
        with self._lock:
            self._noise_intensity = np.clip(intensity, 0.0, 5.0)
 
    def set_snr_threshold(self, threshold: float):
        with self._lock:
            self._snr_threshold = np.clip(threshold, -20.0, 40.0)
 
    def reset(self):
        with self._lock:
            self._frequency = 100.0
            self._amplitude = 1.0
            self._noise_intensity = 0.0
            self._snr_threshold = 10.0
            self._snr_history.clear()
 
    # ─────────────────────────────────────────────────────────────────────────
    # Core DSP Pipeline
    # ─────────────────────────────────────────────────────────────────────────
 
    def process(self) -> dict:
        """
        Run one complete DSP frame. Returns a dict mirroring DSPResult.
        Pipeline: Generate → Add Noise → FFT → SNR → Detect
        """
        with self._lock:
            freq = self._frequency
            amp = self._amplitude
            noise_sigma = self._noise_intensity
            threshold = self._snr_threshold
 
        # ── Step 1: Signal Generation ─────────────────────────────────────
        # x(t) = A · sin(2π f t)
        clean_signal = amp * np.sin(2 * np.pi * freq * self.time_axis)
 
        # ── Step 2: Jamming / Noise Addition (AWGN) ───────────────────────
        # η ~ N(0, σ²) — Gaussian white noise
        noise = np.random.normal(loc=0.0, scale=max(noise_sigma, 1e-9),
                                  size=self.n_samples)
        jammed_signal = clean_signal + noise
 
        # ── Step 3: FFT Analysis ──────────────────────────────────────────
        # rfft: efficient FFT for real-valued signals
        # Output: N//2 + 1 complex coefficients (positive freqs only)
        fft_clean  = np.fft.rfft(clean_signal)
        fft_jammed = np.fft.rfft(jammed_signal)
 
        # Power Spectrum (normalized): P[k] = |X[k]|² / N
        eps = 1e-12   # prevent log(0)
        power_clean  = (np.abs(fft_clean)  ** 2) / self.n_samples
        power_jammed = (np.abs(fft_jammed) ** 2) / self.n_samples
 
        # Convert to dB scale: 10 · log10(P)
        psd_clean_db  = 10 * np.log10(power_clean  + eps)
        psd_jammed_db = 10 * np.log10(power_jammed + eps)
 
        # ── Step 4: SNR Calculation ───────────────────────────────────────
        # Signal power = mean(x²)  — RMS power of clean signal
        # Noise power  = mean(η²)  — RMS power of noise
        signal_power = np.mean(clean_signal ** 2)
        noise_power  = np.mean(noise ** 2) if noise_sigma > 0 else 1e-12
 
        # SNR in dB = 10 · log10(P_s / P_n)
        snr_db = 10 * np.log10(signal_power / max(noise_power, 1e-12))
 
        # Smooth SNR with exponential moving average
        if self._snr_history:
            snr_db = self._ema_alpha * snr_db + (1 - self._ema_alpha) * self._snr_history[-1]
        self._snr_history.append(snr_db)
        if len(self._snr_history) > 20:
            self._snr_history.pop(0)
 
        # dB values for display
        signal_power_db = 10 * np.log10(signal_power + eps)
        noise_power_db  = 10 * np.log10(noise_power  + eps)
 
        # Peak frequency from FFT (should match carrier)
        peak_idx = np.argmax(power_jammed)
        peak_frequency = self.freq_axis[peak_idx]
 
        # ── Step 5: Detection Logic ───────────────────────────────────────
        jamming_detected = snr_db < threshold
        confidence = self._compute_confidence(snr_db, threshold)
        severity = self._classify_severity(snr_db, threshold)
 
        return {
            # Time domain arrays
            "time_axis":          self.time_axis,
            "clean_signal":       clean_signal,
            "jammed_signal":      jammed_signal,
            "noise_signal":       noise,
 
            # Frequency domain arrays
            "freq_axis":          self.freq_axis,
            "power_spectrum_clean":  psd_clean_db,
            "power_spectrum_jammed": psd_jammed_db,
 
            # Metrics
            "snr_db":             snr_db,
            "signal_power_db":    signal_power_db,
            "noise_power_db":     noise_power_db,
            "peak_frequency":     peak_frequency,
            "snr_threshold":      threshold,
 
            # Detection
            "jamming_detected":   jamming_detected,
            "jamming_confidence": confidence,
            "severity":           severity,
 
            # Params snapshot
            "frequency":          freq,
            "amplitude":          amp,
            "noise_intensity":    noise_sigma,
        }
 
    # ─────────────────────────────────────────────────────────────────────────
    # Detection Helpers
    # ─────────────────────────────────────────────────────────────────────────
 
    def _compute_confidence(self, snr_db: float, threshold: float) -> float:
        """
        Jamming confidence [0.0–1.0] based on how far SNR is below threshold.
        Uses a sigmoid-like mapping for smooth transitions.
        """
        if snr_db >= threshold:
            # Below threshold → confidence of clean signal
            margin = snr_db - threshold
            return max(0.0, 1.0 - margin / 20.0)   # fades at +20 dB above threshold
        else:
            # Above threshold → jamming confidence rises
            deficit = threshold - snr_db
            return min(1.0, deficit / 25.0 + 0.1)
 
    def _classify_severity(self, snr_db: float, threshold: float) -> str:
        """Classify jamming severity based on SNR deficit."""
        if snr_db >= threshold:
            return "NONE"
        deficit = threshold - snr_db
        if deficit < 5:
            return "LOW"
        elif deficit < 15:
            return "MEDIUM"
        elif deficit < 30:
            return "HIGH"
        else:
            return "CRITICAL"