#!/usr/bin/env python3
"""
analyze.py - "listen-check by analysis" for every WAV in ../sfx and ../music.

Checks: format (48 kHz / 16-bit), channels, duration, sample peak, clipped
samples, DC offset, integrated loudness (BS.1770), and for *_loop / music
files the loop seam (jump between last and first sample vs. typical
sample-to-sample step, and RMS continuity across the seam).
Optional:  --png DIR   writes a spectrogram per file (matplotlib).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from dsp import SR, read_wav, lufs

ROOT = Path(__file__).resolve().parent.parent
LOOPS = ("loop", "music_", "sfx_fire_breath")


def seam_metrics(x):
    m = x.mean(axis=0)
    d = np.abs(np.diff(m))
    typical = np.percentile(d, 99) + 1e-9
    jump = abs(m[0] - m[-1])
    w = int(0.05 * SR)
    r_end = np.sqrt(np.mean(m[-w:] ** 2))
    r_beg = np.sqrt(np.mean(m[:w] ** 2))
    rms_ratio_db = 20 * np.log10((r_end + 1e-9) / (r_beg + 1e-9))
    return jump / typical, rms_ratio_db


def main(argv):
    png_dir = None
    if "--png" in argv:
        png_dir = Path(argv[argv.index("--png") + 1])
        png_dir.mkdir(parents=True, exist_ok=True)
    files = sorted((ROOT / "sfx").glob("*.wav")) + sorted((ROOT / "music").glob("*.wav"))
    hdr = f"{'file':28s} {'ch':>2s} {'sr':>6s} {'bits':>4s} {'dur s':>7s} {'peak dBFS':>9s} {'clip':>5s} " \
          f"{'DC':>9s} {'LUFS':>6s} {'seam':>12s}"
    print(hdr)
    print("-" * len(hdr))
    ok = True
    rows = []
    for f in files:
        x, sr, sw = read_wav(f)
        n = x.shape[1]
        peak = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
        clip = int(np.sum(np.abs(x) >= 32767 / 32768))
        dc = float(np.max(np.abs(x.mean(axis=1))))
        L = lufs(x)
        seam = ""
        if any(k in f.name for k in LOOPS):
            j, r = seam_metrics(x)
            seam = f"{j:4.2f}x {r:+5.1f}dB"
            # flag on the sample jump only; the RMS ratio is informative (a downbeat
            # at t=0 legitimately makes the first 50 ms louder than the last 50 ms)
            if j > 1.0:
                ok = False
                seam += " !"
        bad = sr != 48000 or sw != 2 or clip > 0 or peak > -0.99 or dc > 1e-3
        ok &= not bad
        print(f"{f.name:28s} {x.shape[0]:2d} {sr:6d} {sw * 8:4d} {n / sr:7.2f} {peak:9.2f} {clip:5d} "
              f"{dc:9.6f} {L:6.1f} {seam:>12s}{'  <-- CHECK' if bad else ''}")
        rows.append((f, x))
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    if png_dir:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for f, x in rows:
            m = x.mean(axis=0)
            fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
            t = np.arange(m.size) / SR
            ax[0].plot(t, x.T, lw=0.3)
            ax[0].set_title(f.name)
            ax[1].specgram(m + 1e-9, NFFT=2048, Fs=SR, noverlap=1536, cmap="magma", vmin=-140)
            ax[1].set_ylim(0, 12000)
            fig.tight_layout()
            fig.savefig(png_dir / (f.stem + ".png"), dpi=70)
            plt.close(fig)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
