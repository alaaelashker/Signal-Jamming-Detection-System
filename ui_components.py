import customtkinter as ctk
import tkinter as tk
import math
import time


# ─── Utility: Section Header ──────────────────────────────────────────────────

def _section_header(parent, text: str, colors: dict) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(
        frame, text=text,
        font=("Courier New", 10, "bold"),
        text_color=colors["accent_cyan"]
    ).pack(side="left")
    return frame


# ─── Utility: Separator ──────────────────────────────────────────────────────

def _separator(parent, colors):
    ctk.CTkFrame(
        parent, height=1, fg_color=colors["border"]
    ).pack(fill="x", pady=6)


# ─── Utility: Metric Row ──────────────────────────────────────────────────────

def _metric_row(parent, label: str, colors: dict):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=1)
    ctk.CTkLabel(
        row, text=label,
        font=("Courier New", 9),
        text_color=colors["text_secondary"],
        width=130, anchor="w"
    ).pack(side="left")
    val = ctk.CTkLabel(
        row, text="---",
        font=("Courier New", 9, "bold"),
        text_color=colors["text_primary"],
        anchor="e"
    )
    val.pack(side="right")
    return val


# ═════════════════════════════════════════════════════════════════════════════
# CONTROL PANEL
# ═════════════════════════════════════════════════════════════════════════════

class ControlPanel(ctk.CTkFrame):
    """
    Left panel: sliders for signal parameters + live value readouts.
    """

    def __init__(self, parent, colors: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.colors = colors
        self._build()

    def _build(self):
        C = self.colors

        # Title
        ctk.CTkLabel(
            self, text="◈  SIGNAL PARAMETERS",
            font=("Courier New", 11, "bold"),
            text_color=C["accent_cyan"]
        ).pack(fill="x", padx=8, pady=(12, 4))

        _separator(self, C)

        # ── Carrier Frequency ─────────────────────────────────────────────
        ctk.CTkLabel(self, text="CARRIER FREQUENCY",
                     font=("Courier New", 9, "bold"),
                     text_color=C["text_secondary"]).pack(fill="x", padx=8)

        freq_row = ctk.CTkFrame(self, fg_color="transparent")
        freq_row.pack(fill="x", padx=8)
        self.freq_value_label = ctk.CTkLabel(
            freq_row, text="100.0 Hz",
            font=("Courier New", 14, "bold"),
            text_color=C["accent_blue"]
        )
        self.freq_value_label.pack(side="right")

        self.freq_slider = ctk.CTkSlider(
            self, from_=10, to=500,
            number_of_steps=490,
            button_color=C["accent_blue"],
            button_hover_color="#6090FF",
            progress_color=C["accent_blue"],
            command=lambda v: self.freq_value_label.configure(text=f"{float(v):.1f} Hz")
        )
        self.freq_slider.set(100)
        self.freq_slider.pack(fill="x", padx=8, pady=(2, 8))

        # ── Signal Amplitude ──────────────────────────────────────────────
        ctk.CTkLabel(self, text="SIGNAL AMPLITUDE",
                     font=("Courier New", 9, "bold"),
                     text_color=C["text_secondary"]).pack(fill="x", padx=8)

        amp_row = ctk.CTkFrame(self, fg_color="transparent")
        amp_row.pack(fill="x", padx=8)
        self.amp_value_label = ctk.CTkLabel(
            amp_row, text="1.00 V",
            font=("Courier New", 14, "bold"),
            text_color=C["accent_green"]
        )
        self.amp_value_label.pack(side="right")

        self.amp_slider = ctk.CTkSlider(
            self, from_=0.1, to=5.0,
            number_of_steps=49,
            button_color=C["accent_green"],
            button_hover_color="#40FFA0",
            progress_color=C["accent_green"],
            command=lambda v: self.amp_value_label.configure(text=f"{float(v):.2f} V")
        )
        self.amp_slider.set(1.0)
        self.amp_slider.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Jamming / Noise ───────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="◈  JAMMING SIMULATOR",
            font=("Courier New", 11, "bold"),
            text_color=C["accent_red"]
        ).pack(fill="x", padx=8, pady=(4, 4))

        ctk.CTkLabel(self, text="NOISE INTENSITY  (σ)",
                     font=("Courier New", 9, "bold"),
                     text_color=C["text_secondary"]).pack(fill="x", padx=8)

        noise_row = ctk.CTkFrame(self, fg_color="transparent")
        noise_row.pack(fill="x", padx=8)
        self.noise_value_label = ctk.CTkLabel(
            noise_row, text="0.00",
            font=("Courier New", 14, "bold"),
            text_color=C["accent_red"]
        )
        self.noise_value_label.pack(side="right")

        self.noise_slider = ctk.CTkSlider(
            self, from_=0.0, to=5.0,
            number_of_steps=100,
            button_color=C["accent_red"],
            button_hover_color="#FF6070",
            progress_color=C["accent_red"],
            command=lambda v: self.noise_value_label.configure(text=f"{float(v):.2f}")
        )
        self.noise_slider.set(0.0)
        self.noise_slider.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Detection Threshold ───────────────────────────────────────────
        ctk.CTkLabel(
            self, text="◈  DETECTION ENGINE",
            font=("Courier New", 11, "bold"),
            text_color=C["accent_yellow"]
        ).pack(fill="x", padx=8, pady=(4, 4))

        ctk.CTkLabel(self, text="SNR THRESHOLD  (dB)",
                     font=("Courier New", 9, "bold"),
                     text_color=C["text_secondary"]).pack(fill="x", padx=8)

        thr_row = ctk.CTkFrame(self, fg_color="transparent")
        thr_row.pack(fill="x", padx=8)
        self.threshold_value_label = ctk.CTkLabel(
            thr_row, text="10.0 dB",
            font=("Courier New", 14, "bold"),
            text_color=C["accent_yellow"]
        )
        self.threshold_value_label.pack(side="right")

        self.threshold_slider = ctk.CTkSlider(
            self, from_=-20, to=40,
            number_of_steps=60,
            button_color=C["accent_yellow"],
            button_hover_color="#FFE050",
            progress_color=C["accent_yellow"],
            command=lambda v: self.threshold_value_label.configure(text=f"{float(v):.1f} dB")
        )
        self.threshold_slider.set(10.0)
        self.threshold_slider.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Buttons ───────────────────────────────────────────────────────
        self.start_btn = ctk.CTkButton(
            self,
            text="⬛  STOP MONITORING",
            font=("Courier New", 11, "bold"),
            fg_color="#8B1A2A",
            hover_color="#6B0F1E",
            corner_radius=6,
            height=38
        )
        self.start_btn.pack(fill="x", padx=8, pady=(4, 4))

        self.reset_btn = ctk.CTkButton(
            self,
            text="↺  RESET SYSTEM",
            font=("Courier New", 11, "bold"),
            fg_color="#1A2D4A",
            hover_color="#1E3A5F",
            corner_radius=6,
            height=34
        )
        self.reset_btn.pack(fill="x", padx=8, pady=(0, 8))

        _separator(self, C)

        # ── Live Readouts ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="◈  LIVE TELEMETRY",
            font=("Courier New", 10, "bold"),
            text_color=C["accent_cyan"]
        ).pack(fill="x", padx=8, pady=(4, 4))

        readout_frame = ctk.CTkFrame(
            self, fg_color=C["bg_tertiary"], corner_radius=8
        )
        readout_frame.pack(fill="x", padx=8, pady=4)

        self.readout_snr  = _metric_row(readout_frame, "  SNR:", C)
        self.readout_sig  = _metric_row(readout_frame, "  Signal Power:", C)
        self.readout_nse  = _metric_row(readout_frame, "  Noise Power:", C)
        self.readout_peak = _metric_row(readout_frame, "  Peak Freq:", C)
        self.readout_conf = _metric_row(readout_frame, "  Confidence:", C)

        # Filler
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # Version footer
        ctk.CTkLabel(
            self, text="SJDAS v2.4.1  |  DSP Core",
            font=("Courier New", 8),
            text_color=C["text_secondary"]
        ).pack(pady=(0, 6))

    def update_readouts(self, result: dict):
        """Update live telemetry readouts."""
        snr = result["snr_db"]
        snr_color = (
            self.colors["accent_red"] if result["jamming_detected"]
            else self.colors["accent_green"]
        )
        self.readout_snr.configure(
            text=f"{snr:+.2f} dB",
            text_color=snr_color
        )
        self.readout_sig.configure(
            text=f"{result['signal_power_db']:.2f} dB"
        )
        self.readout_nse.configure(
            text=f"{result['noise_power_db']:.2f} dB"
        )
        self.readout_peak.configure(
            text=f"{result['peak_frequency']:.1f} Hz"
        )
        conf_pct = result["jamming_confidence"] * 100
        self.readout_conf.configure(
            text=f"{conf_pct:.1f} %",
            text_color=(
                self.colors["accent_red"] if conf_pct > 50
                else self.colors["accent_green"]
            )
        )

    def reset_sliders(self):
        self.freq_slider.set(100)
        self.amp_slider.set(1.0)
        self.noise_slider.set(0.0)
        self.threshold_slider.set(10.0)
        self.freq_value_label.configure(text="100.0 Hz")
        self.amp_value_label.configure(text="1.00 V")
        self.noise_value_label.configure(text="0.00")
        self.threshold_value_label.configure(text="10.0 dB")


# ═════════════════════════════════════════════════════════════════════════════
# METRICS PANEL
# ═════════════════════════════════════════════════════════════════════════════

class MetricsPanel(ctk.CTkFrame):
    """
    Right panel: SNR progress bar gauge, power meters.
    """

    def __init__(self, parent, colors: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.colors = colors
        self._build()

    def _build(self):
        C = self.colors

        ctk.CTkLabel(
            self, text="◈  SIGNAL METRICS",
            font=("Courier New", 11, "bold"),
            text_color=C["accent_cyan"]
        ).pack(fill="x", padx=8, pady=(12, 4))

        _separator(self, C)

        # ── SNR Gauge ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="SIGNAL-TO-NOISE RATIO",
            font=("Courier New", 9, "bold"),
            text_color=C["text_secondary"]
        ).pack(fill="x", padx=8)

        # Big SNR number
        self.snr_big = ctk.CTkLabel(
            self, text="-- dB",
            font=("Courier New", 32, "bold"),
            text_color=C["accent_green"]
        )
        self.snr_big.pack(pady=(2, 4))

        # SNR progress bar (maps -40..+60 dB → 0..1)
        ctk.CTkLabel(
            self, text="[-40 dB]──────────────────[+60 dB]",
            font=("Courier New", 7),
            text_color=C["text_secondary"]
        ).pack(padx=8)

        self.snr_bar = ctk.CTkProgressBar(
            self, height=18, corner_radius=4,
            progress_color=C["accent_green"],
            fg_color=C["bg_tertiary"]
        )
        self.snr_bar.set(0.5)
        self.snr_bar.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Signal Power ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="SIGNAL POWER",
            font=("Courier New", 9, "bold"),
            text_color=C["text_secondary"]
        ).pack(fill="x", padx=8)

        self.sig_power_val = ctk.CTkLabel(
            self, text="-- dBm",
            font=("Courier New", 18, "bold"),
            text_color=C["accent_blue"]
        )
        self.sig_power_val.pack()

        self.sig_power_bar = ctk.CTkProgressBar(
            self, height=12, corner_radius=3,
            progress_color=C["accent_blue"],
            fg_color=C["bg_tertiary"]
        )
        self.sig_power_bar.set(0.5)
        self.sig_power_bar.pack(fill="x", padx=8, pady=(2, 8))

        # ── Noise Power ───────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="NOISE POWER",
            font=("Courier New", 9, "bold"),
            text_color=C["text_secondary"]
        ).pack(fill="x", padx=8)

        self.noise_power_val = ctk.CTkLabel(
            self, text="-- dBm",
            font=("Courier New", 18, "bold"),
            text_color=C["accent_red"]
        )
        self.noise_power_val.pack()

        self.noise_power_bar = ctk.CTkProgressBar(
            self, height=12, corner_radius=3,
            progress_color=C["accent_red"],
            fg_color=C["bg_tertiary"]
        )
        self.noise_power_bar.set(0.0)
        self.noise_power_bar.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Jamming Confidence ────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="JAMMING CONFIDENCE",
            font=("Courier New", 9, "bold"),
            text_color=C["text_secondary"]
        ).pack(fill="x", padx=8)

        self.confidence_val = ctk.CTkLabel(
            self, text="0.0 %",
            font=("Courier New", 22, "bold"),
            text_color=C["accent_yellow"]
        )
        self.confidence_val.pack(pady=(2, 4))

        self.confidence_bar = ctk.CTkProgressBar(
            self, height=14, corner_radius=3,
            progress_color=C["accent_yellow"],
            fg_color=C["bg_tertiary"]
        )
        self.confidence_bar.set(0.0)
        self.confidence_bar.pack(fill="x", padx=8, pady=(2, 8))

        _separator(self, C)

        # ── Frequency Readout ─────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="DETECTED CARRIER",
            font=("Courier New", 9, "bold"),
            text_color=C["text_secondary"]
        ).pack(fill="x", padx=8)

        self.freq_readout = ctk.CTkLabel(
            self, text="--- Hz",
            font=("Courier New", 26, "bold"),
            text_color=C["accent_cyan"]
        )
        self.freq_readout.pack(pady=(2, 4))

        # Filler
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

    def update(self, result: dict):
        """Update all metric widgets."""
        C = self.colors
        snr = result["snr_db"]
        jammed = result["jamming_detected"]

        # SNR display
        snr_color = C["accent_red"] if jammed else C["accent_green"]
        self.snr_big.configure(text=f"{snr:+.1f} dB", text_color=snr_color)
        self.snr_bar.configure(progress_color=snr_color)

        # Normalize SNR bar: map [-40, +60] → [0, 1]
        snr_norm = (snr + 40) / 100.0
        self.snr_bar.set(max(0.01, min(1.0, snr_norm)))

        # Signal power bar: map [-60, +30] → [0, 1]
        sig_db = result["signal_power_db"]
        sig_norm = (sig_db + 60) / 90.0
        self.sig_power_val.configure(text=f"{sig_db:.1f} dBm")
        self.sig_power_bar.set(max(0.01, min(1.0, sig_norm)))

        # Noise power bar: map [-60, +30] → [0, 1]
        nse_db = result["noise_power_db"]
        nse_norm = (nse_db + 60) / 90.0
        self.noise_power_val.configure(text=f"{nse_db:.1f} dBm")
        self.noise_power_bar.set(max(0.01, min(1.0, nse_norm)))

        # Confidence
        conf = result["jamming_confidence"]
        conf_color = (
            C["accent_red"] if conf > 0.7
            else C["accent_yellow"] if conf > 0.3
            else C["accent_green"]
        )
        self.confidence_val.configure(
            text=f"{conf*100:.1f} %",
            text_color=conf_color
        )
        self.confidence_bar.configure(progress_color=conf_color)
        self.confidence_bar.set(max(0.01, min(1.0, conf)))

        # Carrier frequency
        self.freq_readout.configure(
            text=f"{result['peak_frequency']:.1f} Hz"
        )


# ═════════════════════════════════════════════════════════════════════════════
# STATUS PANEL
# ═════════════════════════════════════════════════════════════════════════════

class StatusPanel(ctk.CTkFrame):
    """
    Status indicator: big GREEN/RED light + severity label.
    """

    SEVERITY_COLORS = {
        "NONE":     ("#00FF88", "#0A2A18"),
        "LOW":      ("#FFD60A", "#2A2208"),
        "MEDIUM":   ("#FF9500", "#2A1800"),
        "HIGH":     ("#FF2D55", "#2A0A14"),
        "CRITICAL": ("#FF2D55", "#3A0010"),
    }

    def __init__(self, parent, colors: dict, **kwargs):
        super().__init__(
            parent,
            fg_color=colors["bg_tertiary"],
            corner_radius=10,
            border_width=1,
            border_color=colors["border"],
            **kwargs
        )
        self.colors = colors
        self._last_severity = None
        self._blink_state = False
        self._build()

    def _build(self):
        C = self.colors

        # Status dot
        self.status_dot = ctk.CTkLabel(
            self, text="●",
            font=("Courier New", 48, "bold"),
            text_color=C["accent_green"]
        )
        self.status_dot.pack(pady=(12, 2))

        # Status label
        self.status_label = ctk.CTkLabel(
            self, text="SIGNAL  CLEAR",
            font=("Courier New", 16, "bold"),
            text_color=C["accent_green"]
        )
        self.status_label.pack()

        # Severity badge
        self.severity_badge = ctk.CTkLabel(
            self, text="SEVERITY: NONE",
            font=("Courier New", 10, "bold"),
            text_color=C["text_secondary"]
        )
        self.severity_badge.pack(pady=(4, 10))

        # Detection count
        self._detect_count = 0
        self.detect_count_label = ctk.CTkLabel(
            self, text="DETECTIONS THIS SESSION: 0",
            font=("Courier New", 8),
            text_color=C["text_secondary"]
        )
        self.detect_count_label.pack(pady=(0, 10))

    def update(self, result: dict):
        C = self.colors
        severity = result["severity"]
        jammed = result["jamming_detected"]

        dot_color, bg_color = self.SEVERITY_COLORS.get(severity, (C["accent_green"], C["bg_tertiary"]))

        if jammed:
            self.status_dot.configure(text_color=dot_color)
            self.status_label.configure(
                text="⚠  JAMMING  DETECTED",
                text_color=dot_color
            )
            self.configure(fg_color=bg_color)
            if severity != self._last_severity:
                self._detect_count += 1
                self.detect_count_label.configure(
                    text=f"DETECTIONS THIS SESSION: {self._detect_count}"
                )
        else:
            self.status_dot.configure(text_color=C["accent_green"])
            self.status_label.configure(
                text="✓  SIGNAL  CLEAR",
                text_color=C["accent_green"]
            )
            self.configure(fg_color=C["bg_tertiary"])

        self.severity_badge.configure(
            text=f"SEVERITY: {severity}",
            text_color=dot_color
        )
        self._last_severity = severity


# ═════════════════════════════════════════════════════════════════════════════
# ALERT BANNER
# ═════════════════════════════════════════════════════════════════════════════

class AlertBanner(ctk.CTkFrame):
    """
    Full-width alert bar below the header.
    Shows GREEN (clear) or RED (jamming) with animated text.
    """

    def __init__(self, parent, colors: dict, **kwargs):
        super().__init__(
            parent,
            height=34,
            fg_color="#0A2A18",
            corner_radius=6,
            **kwargs
        )
        self.pack_propagate(False)
        self.colors = colors

        self.label = ctk.CTkLabel(
            self,
            text="◉  ALL CLEAR  —  NO JAMMING DETECTED  |  SYSTEM NOMINAL  |  MONITORING ACTIVE",
            font=("Courier New", 10, "bold"),
            text_color=colors["accent_green"]
        )
        self.label.pack(expand=True)

        self._blink = False
        self._blink_job = None

    def update(self, result: dict):
        C = self.colors
        if result["jamming_detected"]:
            sev = result["severity"]
            snr = result["snr_db"]
            freq = result["frequency"]
            text = (
                f"⚠⚠  JAMMING DETECTED  |  SEVERITY: {sev}  |  "
                f"SNR: {snr:+.1f} dB  |  "
                f"CARRIER: {freq:.0f} Hz  |  "
                f"CONFIDENCE: {result['jamming_confidence']*100:.0f}%  ⚠⚠"
            )
            self.configure(fg_color="#2A0A14")
            self.label.configure(text=text, text_color=C["accent_red"])
        else:
            text = (
                f"◉  ALL CLEAR  —  NO JAMMING DETECTED  |  "
                f"SNR: {result['snr_db']:+.1f} dB  |  "
                f"CARRIER: {result['frequency']:.0f} Hz  |  "
                f"SYSTEM NOMINAL"
            )
            self.configure(fg_color="#0A2A18")
            self.label.configure(text=text, text_color=C["accent_green"])