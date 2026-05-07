"""
╔══════════════════════════════════════════════════════════════════╗
║     SIGNAL JAMMING DETECTION & ANALYSIS SYSTEM (SJDAS)          ║
║     Electronic Warfare / Telecommunications DSP Suite            ║
╠══════════════════════════════════════════════════════════════════╣
║  Architecture : Modular DSP Pipeline                             ║
║  DSP Concepts : FFT, SNR, Sampling Theorem, Gaussian Noise       ║
║  GUI          : CustomTkinter Dark Dashboard + Matplotlib Plots  ║
║  Audio        : pygame-based Audio Feedback System  v2.5.0       ║
╚══════════════════════════════════════════════════════════════════╝

Audio Feedback Overview
───────────────────────
Two WAV files are used (place them next to main.py):

  alarm.wav      → looping siren that plays while jamming is active
  normal_hum.wav → quiet ambient hum that plays while signal is clean

The AudioManager class owns two pygame.mixer.Channel objects so both
sounds can coexist and cross-fade independently.  The state machine
ensures a sound is never restarted mid-loop; it only reacts when the
detection state actually changes.
"""

import customtkinter as ctk
import threading
import time
import os

# ─── Optional pygame import ───────────────────────────────────────────────────
# Wrapped so the application still runs (silently) if pygame is missing.
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[AUDIO] pygame not installed — audio disabled.\n"
          "        Run:  pip install pygame")

from dsp_engine    import DSPEngine
from visualizer    import SignalVisualizer
from ui_components import StatusPanel, ControlPanel, MetricsPanel, AlertBanner

# ─── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Colour Palette ───────────────────────────────────────────────────────────
COLORS = {
    "bg_primary":    "#0A0E1A",
    "bg_secondary":  "#0F1626",
    "bg_tertiary":   "#141C30",
    "accent_cyan":   "#00D4FF",
    "accent_green":  "#00FF88",
    "accent_red":    "#FF2D55",
    "accent_yellow": "#FFD60A",
    "accent_blue":   "#3A7EFF",
    "text_primary":  "#E8F4FD",
    "text_secondary":"#7B9CBF",
    "border":        "#1E2D47",
    "grid":          "#1A2540",
}

# ─── WAV file paths ───────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALARM_WAV = os.path.join(_BASE_DIR, "alarm.wav")
HUM_WAV   = os.path.join(_BASE_DIR, "normal_hum.wav")


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class AudioManager:
    """
    Manages all audio feedback for SJDAS using pygame.mixer.

    Architecture
    ────────────
    Channel 0  →  alarm / siren  (loops while jamming_detected == True)
    Channel 1  →  ambient hum    (loops while signal is clean)

    Keeping two independent channels means we can cross-fade between
    states in a single call without any stop/start gaps.

    State Machine
    ─────────────
    _current_state ∈ { None, "normal", "jamming", "stopped" }

    The state is only changed (and pygame only touched) when the
    incoming state differs from _current_state.  At ~12.5 FPS this
    means the vast majority of update() calls are a single comparison
    and return — negligible overhead on the UI thread.

    Thread Safety
    ─────────────
    _lock guards _current_state and _muted so that toggle_mute()
    (called from the UI thread) and update() (also UI thread but
    conceptually separate) cannot race.
    """

    # Milliseconds for a graceful fade-out when switching states
    FADE_OUT_MS = 400

    def __init__(self):
        self._ready          = False
        self._current_state  = None   # last applied state string
        self._muted          = False
        self._lock           = threading.Lock()

        # These are set in _initialise() if pygame is available
        self._snd_alarm = None   # pygame.mixer.Sound
        self._snd_hum   = None   # pygame.mixer.Sound
        self._ch_alarm  = None   # pygame.mixer.Channel  (index 0)
        self._ch_hum    = None   # pygame.mixer.Channel  (index 1)

        if PYGAME_AVAILABLE:
            self._initialise()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _initialise(self):
        """
        Initialise pygame.mixer and pre-load WAV files.
        Uses a small buffer (512 samples ≈ 11 ms) for low latency.
        mono output (channels=1) matches our mono WAV files.
        """
        try:
            pygame.mixer.init(
                frequency=44100,   # CD-quality sample rate
                size=-16,          # 16-bit signed PCM
                channels=1,        # mono
                buffer=512         # low-latency buffer
            )
            pygame.mixer.set_num_channels(2)   # ch0 = alarm, ch1 = hum

            self._ch_alarm = pygame.mixer.Channel(0)
            self._ch_hum   = pygame.mixer.Channel(1)

            # Alarm is prominent; hum is subtle background
            self._ch_alarm.set_volume(0.85)
            self._ch_hum.set_volume(0.30)

            self._snd_alarm = self._load("alarm",      ALARM_WAV)
            self._snd_hum   = self._load("normal_hum", HUM_WAV)

            self._ready = True
            print("[AUDIO] Initialised OK")
            print(f"[AUDIO]   alarm.wav      → {ALARM_WAV}")
            print(f"[AUDIO]   normal_hum.wav → {HUM_WAV}")

        except Exception as exc:
            self._ready = False
            print(f"[AUDIO] Init failed — audio disabled.  ({exc})")

    @staticmethod
    def _load(label: str, path: str):
        """Load a WAV file, returning a Sound object or None."""
        if not os.path.isfile(path):
            print(f"[AUDIO] WARNING '{label}' not found: {path}")
            return None
        return pygame.mixer.Sound(path)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def muted(self) -> bool:
        return self._muted

    def toggle_mute(self):
        """Called by the mute button in the header bar."""
        with self._lock:
            self._muted = not self._muted
            if not self._ready:
                return
            if self._muted:
                # Gracefully fade out all channels
                self._ch_alarm.fadeout(self.FADE_OUT_MS)
                self._ch_hum.fadeout(self.FADE_OUT_MS)
            else:
                # Resume the last known state immediately
                self._apply(self._current_state)

    def update(self, jamming_detected: bool, monitoring_active: bool):
        """
        Called from _apply_results() on every DSP frame (~12.5 FPS).

        This is intentionally lightweight:
          • No state change  →  one comparison, immediate return
          • State change     →  one pygame Channel call (non-blocking)

        Parameters
        ──────────
        jamming_detected  : True when SNR < threshold
        monitoring_active : False when the user paused monitoring
        """
        if not self._ready:
            return

        # Map inputs to a state string
        if not monitoring_active:
            desired = "stopped"
        elif jamming_detected:
            desired = "jamming"
        else:
            desired = "normal"

        # Only act when state changes — critical for avoiding per-frame restarts
        with self._lock:
            if desired == self._current_state:
                return                      # nothing to do
            self._current_state = desired
            if not self._muted:
                self._apply(desired)

    def _apply(self, state: str):
        """
        Start/stop channels for the given state.
        Called while _lock is held (or from toggle_mute with lock held).

        pygame.Channel.play(sound, loops=-1)  →  loops forever
        pygame.Channel.fadeout(ms)            →  non-blocking smooth stop
        pygame.Channel.get_busy()             →  True if already playing
        """
        if state == "jamming":
            # ── Activate alarm, silence hum ───────────────────────────────
            self._ch_hum.fadeout(self.FADE_OUT_MS)
            if self._snd_alarm and not self._ch_alarm.get_busy():
                # loops=-1 means infinite loop until explicitly stopped
                self._ch_alarm.play(self._snd_alarm, loops=-1)

        elif state == "normal":
            # ── Activate hum, silence alarm ───────────────────────────────
            self._ch_alarm.fadeout(self.FADE_OUT_MS)
            if self._snd_hum and not self._ch_hum.get_busy():
                self._ch_hum.play(self._snd_hum, loops=-1)

        elif state == "stopped":
            # ── Silence everything ────────────────────────────────────────
            self._ch_alarm.fadeout(self.FADE_OUT_MS)
            self._ch_hum.fadeout(self.FADE_OUT_MS)

    def shutdown(self):
        """Hard-stop all audio and release pygame.mixer. Called on app exit."""
        if not self._ready:
            return
        try:
            self._ch_alarm.stop()
            self._ch_hum.stop()
            pygame.mixer.quit()
            print("[AUDIO] pygame.mixer shut down cleanly.")
        except Exception as exc:
            print(f"[AUDIO] Shutdown warning: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class SJDASApplication(ctk.CTk):
    """
    Main Application Window.
    Coordinates: DSP Engine · Visualizer · UI Components · AudioManager.

    Audio integration summary
    ─────────────────────────
    __init__          → AudioManager() created before first DSP frame
    _build_header()   → mute toggle button added to header bar
    _apply_results()  → audio.update() called at end of every frame
    _toggle_monitoring() → audio.update(monitoring_active=False) on pause
    _on_close()       → audio.shutdown() before window destroy
    """

    def __init__(self):
        super().__init__()

        # ── Window ────────────────────────────────────────────────────────
        self.title("SJDAS — Signal Jamming Detection & Analysis System  |  v2.5.0")
        self.geometry("1520x940")
        self.minsize(1280, 800)
        self.configure(fg_color=COLORS["bg_primary"])

        # ── DSP Engine ────────────────────────────────────────────────────
        self.dsp = DSPEngine(
            sample_rate=2000,
            duration=0.5,
            base_freq=100.0,
            amplitude=1.0,
            noise_intensity=0.0
        )

        # ── Audio Manager ─────────────────────────────────────────────────
        # Created before the UI loop starts so sounds are ready on frame 1.
        self.audio = AudioManager()

        # ── State ─────────────────────────────────────────────────────────
        self.is_running         = False
        self.update_interval_ms = 80    # ~12.5 FPS
        self._lock              = threading.Lock()

        # ── Build UI ──────────────────────────────────────────────────────
        self._build_layout()
        self._bind_controls()

        # ── Start ─────────────────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_monitoring()

    # ─────────────────────────────────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self):
        self._build_header()

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.main_frame.columnconfigure(0, weight=0, minsize=270)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=0, minsize=270)
        self.main_frame.rowconfigure(0, weight=1)

        # LEFT
        lp = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_secondary"],
                           corner_radius=12, border_width=1,
                           border_color=COLORS["border"])
        lp.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.control_panel = ControlPanel(lp, colors=COLORS)
        self.control_panel.pack(fill="both", expand=True, padx=8, pady=8)

        # CENTER
        cp = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_secondary"],
                           corner_radius=12, border_width=1,
                           border_color=COLORS["border"])
        cp.grid(row=0, column=1, sticky="nsew", padx=6)
        self.visualizer = SignalVisualizer(cp, colors=COLORS)
        self.visualizer.pack(fill="both", expand=True, padx=4, pady=4)

        # RIGHT
        rp = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_secondary"],
                           corner_radius=12, border_width=1,
                           border_color=COLORS["border"])
        rp.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self.metrics_panel = MetricsPanel(rp, colors=COLORS)
        self.metrics_panel.pack(fill="both", expand=True, padx=8, pady=8)
        self.status_panel = StatusPanel(rp, colors=COLORS)
        self.status_panel.pack(fill="x", padx=8, pady=(0, 8))

    def _build_header(self):
        """Header bar — includes the new 🔊 mute toggle button."""
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                               height=62, corner_radius=0, border_width=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Left group (logo + title)
        lg = ctk.CTkFrame(header, fg_color="transparent")
        lg.pack(side="left", padx=18, pady=0)

        self.header_dot = ctk.CTkLabel(
            lg, text="●", font=("Courier New", 16, "bold"),
            text_color=COLORS["accent_green"])
        self.header_dot.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(lg, text="SJDAS",
                     font=("Courier New", 22, "bold"),
                     text_color=COLORS["accent_cyan"]).pack(side="left")
        ctk.CTkLabel(lg, text="  Signal Jamming Detection & Analysis System",
                     font=("Courier New", 11),
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=(4, 0))

        # Right group (clock + mute btn + sys info)
        rg = ctk.CTkFrame(header, fg_color="transparent")
        rg.pack(side="right", padx=18)

        self.clock_label = ctk.CTkLabel(
            rg, text="00:00:00  UTC",
            font=("Courier New", 11),
            text_color=COLORS["text_secondary"])
        self.clock_label.pack(side="right", padx=(12, 0))

        # ── 🔊 Audio Mute Toggle ──────────────────────────────────────────
        # Clicking toggles AudioManager._muted and updates button appearance.
        self.mute_btn = ctk.CTkButton(
            rg,
            text="🔊  AUDIO ON",
            font=("Courier New", 9, "bold"),
            width=108,
            height=26,
            corner_radius=5,
            fg_color="#1A2D4A",
            hover_color="#1E3A5F",
            border_width=1,
            border_color=COLORS["border"],
            command=self._toggle_audio       # ← wired to AudioManager
        )
        self.mute_btn.pack(side="right", padx=(0, 8))

        ctk.CTkLabel(rg,
                     text="SYSTEM ONLINE  |  FREQ BAND: 50–1000 Hz  |",
                     font=("Courier New", 10),
                     text_color=COLORS["text_secondary"]).pack(side="right")

        # Alert banner
        self.alert_banner = AlertBanner(self, colors=COLORS)
        self.alert_banner.pack(fill="x", padx=12, pady=(6, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # Audio Toggle
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_audio(self):
        """
        Flip the mute state in AudioManager and update button visuals.
        Called exclusively from the UI thread (button click).
        """
        self.audio.toggle_mute()

        if self.audio.muted:
            # Red-tinted button to signal "audio off"
            self.mute_btn.configure(
                text="🔇  AUDIO OFF",
                fg_color="#2A0A14",
                hover_color="#3A0F1E"
            )
        else:
            # Back to neutral blue
            self.mute_btn.configure(
                text="🔊  AUDIO ON",
                fg_color="#1A2D4A",
                hover_color="#1E3A5F"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Control Bindings
    # ─────────────────────────────────────────────────────────────────────────

    def _bind_controls(self):
        cp = self.control_panel
        cp.freq_slider.configure(
            command=lambda v: self.dsp.set_frequency(float(v)))
        cp.amp_slider.configure(
            command=lambda v: self.dsp.set_amplitude(float(v)))
        cp.noise_slider.configure(
            command=lambda v: self.dsp.set_noise_intensity(float(v)))
        cp.threshold_slider.configure(
            command=lambda v: self.dsp.set_snr_threshold(float(v)))
        cp.start_btn.configure(command=self._toggle_monitoring)
        cp.reset_btn.configure(command=self._reset_system)

    # ─────────────────────────────────────────────────────────────────────────
    # Monitoring Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _start_monitoring(self):
        self.is_running = True
        self.control_panel.start_btn.configure(
            text="⬛  STOP MONITORING",
            fg_color="#8B1A2A",
            hover_color="#6B0F1E"
        )
        self._update_loop()
        self._update_clock()

    def _toggle_monitoring(self):
        if self.is_running:
            self.is_running = False
            self.control_panel.start_btn.configure(
                text="▶  START MONITORING",
                fg_color="#1A4A2A",
                hover_color="#145020"
            )
            # Notify audio manager → fades out all sounds gracefully
            self.audio.update(jamming_detected=False, monitoring_active=False)
        else:
            self._start_monitoring()

    def _update_loop(self):
        """DSP runs in a daemon thread; result is scheduled back to UI thread."""
        if not self.is_running:
            return

        def compute_and_update():
            result = self.dsp.process()
            self.after(0, lambda: self._apply_results(result))

        threading.Thread(target=compute_and_update, daemon=True).start()
        self.after(self.update_interval_ms, self._update_loop)

    def _apply_results(self, result: dict):
        """
        Apply one DSP frame to all UI panels, then update audio.

        Audio is updated last so that:
          1. All visual indicators already show the new state.
          2. The sound change feels synchronised with the visual alarm.

        Performance note
        ────────────────
        audio.update() costs ~1 µs when the state hasn't changed
        (single dict-key comparison + return).  When the state changes,
        pygame's SDL thread does the actual audio work asynchronously,
        so this call still returns in < 1 ms.
        """
        # ── Visuals ───────────────────────────────────────────────────────
        self.visualizer.update(result)
        self.metrics_panel.update(result)
        self.status_panel.update(result)
        self.alert_banner.update(result)
        self.control_panel.update_readouts(result)

        # ── Audio ─────────────────────────────────────────────────────────
        # Only triggers a pygame call when jamming_detected flips value.
        self.audio.update(
            jamming_detected=result["jamming_detected"],
            monitoring_active=self.is_running
        )

    def _update_clock(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%H:%M:%S  UTC")
        self.clock_label.configure(text=now)
        if self.is_running:
            self.after(1000, self._update_clock)

    def _reset_system(self):
        self.dsp.reset()
        self.control_panel.reset_sliders()
        self.visualizer.clear()
        # Noise → 0 after reset, so next frame will flip audio to "normal"

    def _on_close(self):
        """Orderly shutdown: stop loop → silence audio → destroy window."""
        self.is_running = False
        self.audio.shutdown()   # ← stops pygame.mixer cleanly
        time.sleep(0.15)
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SJDASApplication()
    app.mainloop()