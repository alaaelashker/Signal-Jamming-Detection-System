import numpy as np
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec


class SignalVisualizer(ctk.CTkFrame):
    """
    Embeds two matplotlib figures into the CustomTkinter dashboard:
      • Top:    Time Domain — clean (blue) vs jammed (red) waveforms
      • Bottom: Frequency Domain — Power Spectrum (FFT magnitude in dB)

    Uses blitting for performance: only redraws changed artists,
    not the full figure on every frame.
    """

    def __init__(self, parent, colors: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.colors = colors
        self._first_draw = True

        # Section header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            header,
            text="◈  SIGNAL ANALYSIS DISPLAY",
            font=("Courier New", 12, "bold"),
            text_color=colors["accent_cyan"]
        ).pack(side="left")

        self.frame_counter = ctk.CTkLabel(
            header,
            text="FRAME: 0",
            font=("Courier New", 10),
            text_color=colors["text_secondary"]
        )
        self.frame_counter.pack(side="right")

        self._frame_count = 0

        # Build the matplotlib figure
        self._build_figure()

    def _build_figure(self):
        """Create and style the two-subplot matplotlib figure."""
        C = self.colors
        bg = "#0A0E1A"

        # Figure with dark background
        self.fig = plt.Figure(figsize=(10, 7), dpi=96, facecolor=bg)
        self.fig.subplots_adjust(
            left=0.07, right=0.97,
            top=0.93, bottom=0.08,
            hspace=0.42
        )

        # ── Subplot 1: Time Domain ────────────────────────────────────────
        self.ax_time = self.fig.add_subplot(2, 1, 1)
        self._style_axes(self.ax_time, "TIME DOMAIN  —  Waveform Analysis", "Time (ms)", "Amplitude (V)")

        # Plot lines (empty data initially)
        self.line_clean, = self.ax_time.plot(
            [], [], color="#3A7EFF", lw=1.4, alpha=0.95,
            label="Original Signal", zorder=3
        )
        self.line_jammed, = self.ax_time.plot(
            [], [], color="#FF2D55", lw=1.0, alpha=0.75,
            label="Jammed Signal", zorder=2
        )
        self.line_noise, = self.ax_time.plot(
            [], [], color="#FFD60A", lw=0.6, alpha=0.35,
            label="Noise Floor", zorder=1
        )

        # Legend
        legend = self.ax_time.legend(
            handles=[
                mpatches.Patch(color="#3A7EFF", label="Original Signal"),
                mpatches.Patch(color="#FF2D55", label="Jammed Signal"),
                mpatches.Patch(color="#FFD60A", label="Noise Component"),
            ],
            loc="upper right",
            facecolor="#0F1626",
            edgecolor="#1E2D47",
            labelcolor="#E8F4FD",
            fontsize=8.5,
            framealpha=0.85
        )

        # ── Subplot 2: Frequency Domain ───────────────────────────────────
        self.ax_freq = self.fig.add_subplot(2, 1, 2)
        self._style_axes(
            self.ax_freq,
            "FREQUENCY DOMAIN  —  Power Spectral Density (FFT)",
            "Frequency (Hz)", "Power (dB)"
        )

        # Power spectrum lines
        self.line_psd_clean, = self.ax_freq.plot(
            [], [], color="#00FF88", lw=1.3, alpha=0.9,
            label="Clean PSD", zorder=3
        )
        self.line_psd_jammed, = self.ax_freq.plot(
            [], [], color="#FF6B35", lw=1.0, alpha=0.75,
            label="Jammed PSD", zorder=2
        )

        # Fill under the jammed PSD for visual effect
        self.fill_psd = self.ax_freq.fill_between(
            [], [], y2=-120,
            color="#FF6B35", alpha=0.06, zorder=1
        )

        # Peak frequency vertical marker
        self.vline_peak = self.ax_freq.axvline(
            x=100, color="#00D4FF", lw=1.0, alpha=0.5,
            linestyle="--", label="Carrier"
        )

        # Freq domain legend
        self.ax_freq.legend(
            handles=[
                mpatches.Patch(color="#00FF88", label="Clean PSD"),
                mpatches.Patch(color="#FF6B35", label="Jammed PSD"),
                mpatches.Patch(color="#00D4FF", label="Carrier Frequency"),
            ],
            loc="upper right",
            facecolor="#0F1626",
            edgecolor="#1E2D47",
            labelcolor="#E8F4FD",
            fontsize=8.5,
            framealpha=0.85
        )

        # Embed in CustomTkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

        # Store background for blit optimization
        self._bg_time = None
        self._bg_freq = None

    def _style_axes(self, ax, title: str, xlabel: str, ylabel: str):
        """Apply dark theme styling to a matplotlib Axes object."""
        C = self.colors
        bg_ax = "#0D1220"

        ax.set_facecolor(bg_ax)
        ax.tick_params(colors="#5A7A9F", labelsize=8)
        ax.xaxis.label.set_color(C["text_secondary"])
        ax.yaxis.label.set_color(C["text_secondary"])
        ax.set_xlabel(xlabel, fontsize=9, labelpad=4)
        ax.set_ylabel(ylabel, fontsize=9, labelpad=4)
        ax.set_title(title, color=C["accent_cyan"], fontsize=10,
                     fontweight="bold", pad=8, fontfamily="monospace")

        # Grid styling
        ax.grid(True, color="#1A2540", linewidth=0.5, alpha=0.8, linestyle="-")
        ax.set_axisbelow(True)

        # Spine styling
        for spine in ax.spines.values():
            spine.set_edgecolor("#1E2D47")
            spine.set_linewidth(0.8)

    # ─────────────────────────────────────────────────────────────────────────
    # Update (called every frame)
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, result: dict):
        """
        Update both plots with the latest DSP frame.
        Uses matplotlib's blit for efficient partial redraws.
        """
        self._frame_count += 1
        self.frame_counter.configure(text=f"FRAME: {self._frame_count:,}")

        t = result["time_axis"] * 1000   # convert s → ms for display

        # ── Time Domain Update ────────────────────────────────────────────
        clean   = result["clean_signal"]
        jammed  = result["jammed_signal"]
        noise   = result["noise_signal"]

        self.line_clean.set_data(t, clean)
        self.line_jammed.set_data(t, jammed)
        self.line_noise.set_data(t, noise)

        # Auto-scale Y axis with some padding
        y_max = max(np.max(np.abs(jammed)) * 1.3, 0.5)
        self.ax_time.set_xlim(t[0], t[-1])
        self.ax_time.set_ylim(-y_max, y_max)

        # Color the title based on jamming state
        title_color = (
            self.colors["accent_red"]
            if result["jamming_detected"]
            else self.colors["accent_cyan"]
        )
        self.ax_time.set_title(
            "TIME DOMAIN  —  " + (
                "⚠  JAMMING DETECTED" if result["jamming_detected"]
                else "WAVEFORM ANALYSIS"
            ),
            color=title_color,
            fontsize=10, fontweight="bold", pad=8, fontfamily="monospace"
        )

        # ── Frequency Domain Update ───────────────────────────────────────
        freqs = result["freq_axis"]
        psd_clean  = result["power_spectrum_clean"]
        psd_jammed = result["power_spectrum_jammed"]

        # Limit display to 0–600 Hz for clarity
        max_freq_display = min(600, freqs[-1])
        mask = freqs <= max_freq_display

        self.line_psd_clean.set_data(freqs[mask], psd_clean[mask])
        self.line_psd_jammed.set_data(freqs[mask], psd_jammed[mask])

        # Update fill
        self.fill_psd.remove()
        self.fill_psd = self.ax_freq.fill_between(
            freqs[mask], psd_jammed[mask], y2=-120,
            color="#FF6B35", alpha=0.08, zorder=1
        )

        # Update peak frequency marker
        self.vline_peak.set_xdata([result["peak_frequency"], result["peak_frequency"]])

        # Y axis bounds
        all_psd = np.concatenate([psd_clean[mask], psd_jammed[mask]])
        valid = all_psd[np.isfinite(all_psd)]
        if len(valid) > 0:
            y_min_db = max(np.percentile(valid, 5) - 10, -120)
            y_max_db = np.max(valid) + 10
        else:
            y_min_db, y_max_db = -120, 20

        self.ax_freq.set_xlim(0, max_freq_display)
        self.ax_freq.set_ylim(y_min_db, y_max_db)

        # Redraw
        self.canvas.draw_idle()

    def clear(self):
        """Reset plots to empty state."""
        for line in [self.line_clean, self.line_jammed, self.line_noise,
                     self.line_psd_clean, self.line_psd_jammed]:
            line.set_data([], [])
        self.canvas.draw_idle()
        self._frame_count = 0