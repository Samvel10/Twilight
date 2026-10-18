#!/usr/bin/env python3
"""
gen_chapters23.py - procedural audio for chapter 2 «Hayk» and chapter 3 «Aralez».

Reuses the chapter-1 toolkit (dsp.py) plus instruments from gen_music.py
(reed_phrase/add_reed duduk+zurna, dhol, taiko, daf, choir, string_note,
mixdown) and the SFX mastering chain from gen_sfx.py (finish / finish_loop /
glottal_roar / choir).  Same deliverable spec as chapter 1:
48 kHz / 16-bit, SFX mono (cave ambience stereo), peaks <= -1 dBFS,
music stereo ~-14 LUFS, loops seamless by construction (ring buffers +
circular reverb / filtering; no crossfade guesswork).

New here: IFFT "spectral additive" oscillators (ifft_partials / brass /
pad_chord / ifft_drone) - every partial sits on an exact FFT bin, so a
drone or pad spanning the whole loop is periodic and costs one irfft
instead of millions of sin() calls (the build machine is busy).

Run:  python3 gen_chapters23.py                 all 15 files + verify table
      python3 gen_chapters23.py howl chime       only names containing these
      python3 gen_chapters23.py --verify          only print the verify table
Deterministic: fixed seeds everywhere.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from dsp import (SR, ns, tvec, fit, mix_at, ring_add, env_exp, env_points, spectral_noise, white,  # noqa: E402
                 pink, brown, smooth_noise, periodic_lfo, lp, hp, bp, peak_eq, shelf, resonator_bank, svf,
                 circular, saturate, limiter, additive, phase_from_freq, make_ir, reverb, reverb_circular,
                 delay_echo, lufs, normalize_peak, mtof, pan, write_wav, read_wav, undb)
import gen_sfx as gs  # noqa: E402
import gen_music as gm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "sfx"
MUS = ROOT / "music"

# extra impulse responses
IR_HOWL = make_ir(t60=4.2, predelay=0.06, stereo=False, seed=31, damp_hi=0.4, er_spread=0.1)
IR_CAVE_M = make_ir(t60=2.2, predelay=0.025, stereo=False, seed=32, damp_hi=0.3, er_spread=0.05)
IR_CAVE_ST = make_ir(t60=3.2, predelay=0.03, stereo=True, seed=33, damp_hi=0.28, er_spread=0.06)
IR_DUSK = make_ir(t60=2.8, predelay=0.045, stereo=False, seed=34, damp_hi=0.3, er_spread=0.12)


# ==========================================================================
# shared building blocks
# ==========================================================================
def ifft_partials(n, partials, rng):
    """Sum of sines [(freq_hz, amp)] snapped to FFT bins of length n -> exactly
    n-periodic.  Returns (n,) array; amp is the sine amplitude."""
    X = np.zeros(n // 2 + 1, dtype=complex)
    for f, a in partials:
        b = int(round(f * n / SR))
        if 0 < b < n // 2 and a > 0:
            X[b] += a * np.exp(1j * rng.uniform(0, 2 * np.pi))
    return np.fft.irfft(X, n) * (n / 2)


def _brass_w(k, fk):
    return (1.0 / k ** 0.5) * (1 + 1.2 * np.exp(-0.5 * (np.log2(fk / 1000.0) / 0.6) ** 2))


def brass(dur, midis, rng, bright_pts, amp_pts, cut_dark=280.0, cut_bright=2400.0, detune=(0, -7, 6),
          fmax=6000.0, drive=1.5):
    """Brass ensemble (IFFT additive).  Brightness = crossfade between a dark and a
    bright spectrum with identical phases (no comb artefacts).  bright_pts 0..1."""
    n = ns(dur)
    dark = np.zeros(n)
    bright = np.zeros(n)
    for m in midis:
        for c in detune:
            f0 = float(mtof(m)) * 2 ** (c / 1200)
            X1, X2 = [], []
            for k in range(1, int(fmax // f0) + 1):
                fk = k * f0
                w = _brass_w(k, fk)
                X1.append((fk, w / (1 + (fk / cut_dark) ** 2)))
                X2.append((fk, w / (1 + (fk / cut_bright) ** 2)))
            seed = int(rng.integers(1 << 30))
            dark += ifft_partials(n, X1, np.random.default_rng(seed))
            bright += ifft_partials(n, X2, np.random.default_rng(seed))
    s = np.max(np.abs(bright)) + 1e-9
    e = np.clip(env_points(n, bright_pts), 0, 1)
    y = (dark * (1 - e) * 2.2 + bright * e) / s
    y = saturate(y * drive, 1.4)
    return y * env_points(n, amp_pts)


def ifft_drone(L, midis, rng, weight, detune_hz=(0.0, 0.11), breathe=0.2, periodic=True):
    """Loop-length drone (dam / brass).  weight(k, fk) -> amp."""
    out = np.zeros(L)
    for m in midis:
        for d in detune_hz:
            f0 = float(mtof(m)) + d
            parts = [(k * f0, weight(k, k * f0)) for k in range(1, int(7000 // f0) + 1)]
            out += ifft_partials(L, parts, rng)
    out /= np.max(np.abs(out)) + 1e-9
    return out * (1 + breathe * periodic_lfo(L, rng, 4, cycles_min=2))


def pad_chord(dur, midis, rng, att=2.0, rel=3.0, cut=900.0, detune=(-9, 0, 8), air=0.08):
    """Airy stereo pad: detuned saw spectra (IFFT), soft low-pass, breathy top."""
    n = ns(dur + rel)
    out = np.zeros((2, n))
    for ch in range(2):
        acc = np.zeros(n)
        for m in midis:
            for c in detune:
                f0 = float(mtof(m)) * 2 ** ((c + rng.uniform(-3, 3)) / 1200)
                parts = [(k * f0, (1.0 / k) / (1 + (k * f0 / cut) ** 2)) for k in range(1, int(6000 // f0) + 1)]
                acc += ifft_partials(n, parts, rng)
        acc /= np.max(np.abs(acc)) + 1e-9
        acc *= 1 + 0.15 * smooth_noise(n, 0.4, rng)
        acc += air * bp(white(n, rng), 3000, 9000) * (1 + 0.5 * smooth_noise(n, 0.8, rng))
        out[ch] = acc
    return out * env_points(n, [(0, 0), (att, 1), (dur, 0.85), (dur + rel, 0)])


GLASS = [(1.0, 1.0, 0.35), (2.0, 0.16, 0.22), (2.756, 0.42, 0.16), (4.07, 0.10, 0.09), (5.404, 0.20, 0.07),
         (8.933, 0.07, 0.035)]


def bell(f, dur, ring=1.0, partials=GLASS, beat=1.0016):
    """Crystalline glass/celesta bell.  Fully deterministic (no random phases)."""
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    for i, (r, a, tau) in enumerate(partials):
        fk = f * r
        if fk > 0.42 * SR:
            continue
        e = np.exp(-t / (tau * ring))
        y += a * np.sin(2 * np.pi * fk * t + 0.7 * i) * e
        y += 0.3 * a * np.sin(2 * np.pi * fk * beat * t + 1.9 * i) * e  # slow shimmer beating
    # strike: two very high, very short partials
    for r, a in ((11.7, 0.08), (15.2, 0.05)):
        if f * r < 0.42 * SR:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / 0.004)
    return y * np.clip(t / 0.0012, 0, 1)


def finish_loop_st(y, peak_db=-3.0, hp_hz=25.0, air_hz=11000.0):
    """Stereo-safe loop mastering (circular processing, per-channel DC removal)."""
    y = circular(lambda s: lp(s, air_hz, 2), y, laps=3)
    y = circular(lambda s: hp(s, hp_hz, 2), y, laps=3)
    y = y - np.mean(y, axis=-1, keepdims=True)
    y = normalize_peak(y, peak_db + 0.3)
    return circular(lambda s: limiter(s, peak_db), y, laps=3)


# ==========================================================================
# CHAPTER 2 - «Hayk» SFX
# ==========================================================================
def sfx_bow_draw():
    """0.9 s: creaking wooden limbs (stick-slip impulse train through wood modes)
    + rising string-tension tone + string/glove friction."""
    rng = np.random.default_rng(2101)
    dur = 0.9
    n = ns(dur)
    t = tvec(n)
    p = np.clip(t / 0.78, 0, 1) ** 1.2  # draw progress
    # stick-slip creak: impulses at an accelerating, jittery rate, gated in bursts
    imp = np.zeros(n)
    gate = np.clip(0.25 + 0.8 * smooth_noise(n, 7, rng), 0, 1)
    tt = 0.03
    while tt < dur - 0.04:
        i = ns(tt)
        rate = 22 + 110 * p[i]
        if gate[i] > 0.3:
            imp[i] += rng.uniform(0.4, 1.0) * (0.35 + 0.65 * p[i]) * gate[i]
        tt += (1.0 / rate) * rng.uniform(0.6, 1.4)
    creak = resonator_bank(imp, [185, 410, 730, 1240, 2050, 3150], [9, 11, 13, 15, 18, 20],
                           [1.0, 0.9, 0.7, 0.5, 0.3, 0.15])
    creak = saturate(creak * 3, 1.3)
    # string tension: faint pitched tone rising as the string stretches
    f = 120 + 170 * p
    ten = additive(f, lambda k, fk: 1.0 / k ** 1.3, rng, max_harm=12, fmax=3000)
    ten = bp(ten, 150, 2500) * (0.05 + 0.25 * p)
    # friction of string on glove + leather rustle at the start
    fr = bp(white(n, rng), 1500, 6000) * (0.1 + 0.4 * p) * np.clip(1 + 0.5 * smooth_noise(n, 30, rng), 0, 2)
    rustle = lp(white(n, rng), 2500) * env_points(n, [(0, 0), (0.02, 1), (0.15, 0.2), (0.3, 0)])
    y = 1.0 * creak + 0.5 * ten + 0.18 * fr + 0.25 * rustle
    y *= env_points(n, [(0, 0), (0.02, 1), (0.84, 1), (dur, 0.3)])
    return gs.finish(y, -1.0, gs.IR_SMALL, 0.1, tail=0.9, fade_out=0.04)


def sfx_bow_release():
    """0.5 s: sharp string twang (Karplus-Strong) + snap + limb thump + arrow fwip."""
    rng = np.random.default_rng(2102)
    dur = 0.5
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    y += hp(white(n, rng), 2500) * env_exp(n, 0.0035) * 1.0  # snap
    # twang: KS string at ~118 Hz, bright, short decay
    f = 118.0
    P = SR / f
    exc = rng.uniform(-1, 1, int(P))
    exc = lp(exc - np.concatenate([np.zeros(6), exc[:-6]]), 3500, 2)
    tw = gm._ks(exc.astype(np.float64), n, P, 0.988, 0.5)
    tw = tw / (np.max(np.abs(tw)) + 1e-9) * env_exp(n, 0.12)
    tw = svf(tw, 900 + 5000 * np.exp(-t / 0.03), 0.1, "lp")  # highs die first
    y += 1.0 * peak_eq(tw, 700, 4, 1.0)
    # string slap pitch drop + buzz against the bracer
    y += 0.5 * np.sin(phase_from_freq(120 + 260 * np.exp(-t / 0.012))) * env_exp(n, 0.05, 0.0005)
    buzz = hp(white(n, rng), 1200) * (0.5 + 0.5 * np.sin(2 * np.pi * f * t)) ** 4 * env_exp(n, 0.06)
    y += 0.25 * buzz
    # limb thump (wood recoil)
    y += 0.45 * np.sin(phase_from_freq(78 + 50 * np.exp(-t / 0.02))) * env_exp(n, 0.06, 0.001)
    y += 0.3 * lp(white(n, rng), 600) * env_exp(n, 0.03)
    # arrow leaving: short air fwip
    y += 0.3 * svf(white(n, rng), env_points(n, [(0, 4000), (0.12, 1500), (dur, 900)], "log"), 0.4, "bp") * \
        env_points(n, [(0, 0), (0.015, 1), (0.14, 0)])
    return gs.finish(saturate(y, 1.3), -1.0, gs.IR_SMALL, 0.12, tail=0.5, fade_out=0.04)


def sfx_arrow_whoosh():
    """1.2 s pass-by: physically driven doppler (v=55 m/s, 2.5 m miss distance),
    1/r gain, distance-dependent air absorption, fletching flutter + whistle."""
    rng = np.random.default_rng(2103)
    dur = 1.2
    n = ns(dur)
    t = tvec(n)
    v, d, tc, c = 55.0, 2.5, 0.58, 343.0
    x = v * (t - tc)
    r = np.sqrt(x ** 2 + d ** 2)
    vr = v * x / r  # + receding
    D = c / (c + vr)
    g = (d / r) ** 1.3
    nz = pink(n, rng) * 0.6 + white(n, rng) * 0.4
    air = svf(nz, 1700 * D, 0.55, "bp") + 0.6 * svf(nz, 3900 * D, 0.35, "bp")
    flutter = 1 + 0.45 * np.sin(phase_from_freq(92 * D))  # fletching vanes
    whistle = np.sin(phase_from_freq(2150 * D * (1 + 0.004 * smooth_noise(n, 8, rng)))) * 0.22
    body = bp(white(n, rng), 150, 700) * 0.35
    y = (air * flutter + whistle + body) * g
    y = svf(y, 2500 + 9000 * (d / r), 0.1, "lp")  # air absorption with distance
    y *= env_points(n, [(0, 0), (0.08, 1), (1.12, 1), (dur, 0)])
    return gs.finish(saturate(y * 1.2, 1.2), -1.0, gs.IR_SKY, 0.15, tail=1.2, fade_out=0.05)


def sfx_arrow_hit_flesh():
    """0.6 s: dull muffled impact + low thud + short shaft quiver + muffled grunt.
    No gore: no wet/squelch layers."""
    rng = np.random.default_rng(2104)
    dur = 0.6
    n = ns(dur)
    t = tvec(n)
    y = np.sin(phase_from_freq(64 + 70 * np.exp(-t / 0.02))) * env_exp(n, 0.07, 0.001) * 1.0
    y += lp(white(n, rng), 500) * env_exp(n, 0.03, 0.0005) * 0.8
    y += bp(white(n, rng), 160, 900) * env_exp(n, 0.02, 0.0005) * 0.6  # "thwap" of leather/cloth
    y += bp(white(n, rng), 2000, 5000) * env_exp(n, 0.003) * 0.2  # arrowhead tick
    q = np.sin(2 * np.pi * 300 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 26 * t)) ** 2 * env_exp(n, 0.12, 0.01)
    y += 0.12 * q
    grunt = gs.glottal_roar(0.34, [(0, 138), (0.05, 125), (0.34, 84)], rng,
                            [(0, 0), (0.03, 1), (0.12, 0.7), (0.34, 0)], fscale=1.55, growl=0.2, rasp=0.55,
                            rough=0.2, jitter=0.02, sub_oct=0.15, open_pts=[(0, 0.3), (0.08, 0.5), (0.34, 0.15)])
    mix_at(y, lp(grunt, 2800), ns(0.03), 0.45)
    return gs.finish(saturate(y, 1.3), -1.0, gs.IR_SMALL, 0.1, tail=0.6, fade_out=0.05)


def sfx_arrow_hit_wood():
    """0.5 s: sharp wooden thunk (modal wood resonances) + shaft quiver 'brrr'."""
    rng = np.random.default_rng(2105)
    dur = 0.5
    n = ns(dur)
    t = tvec(n)
    y = hp(white(n, rng), 1500) * env_exp(n, 0.002) * 0.8
    for f, tau, a in [(205, 0.09, 1.0), (470, 0.06, 0.8), (830, 0.045, 0.6), (1370, 0.03, 0.45),
                      (2250, 0.02, 0.3), (3400, 0.012, 0.2)]:
        y += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * env_exp(n, tau, 0.0004)
    y += 0.7 * np.sin(phase_from_freq(70 + 50 * np.exp(-t / 0.01))) * env_exp(n, 0.05, 0.0008)
    am = (0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)) ** 2
    qv = (np.sin(2 * np.pi * 255 * t) + 0.4 * np.sin(2 * np.pi * 510 * t)) * am * env_exp(n, 0.17, 0.008)
    qv += 0.5 * bp(white(n, rng), 600, 2500) * am * env_exp(n, 0.1)
    mix_at(y, qv, ns(0.01), 0.3)
    return gs.finish(saturate(y * 0.8, 1.4), -1.0, gs.IR_SMALL, 0.12, tail=0.5, fade_out=0.04)


def sfx_arrow_hit_ground():
    """0.4 s: dirt thud + gritty crunch + scattering soil grains + pebble ticks."""
    rng = np.random.default_rng(2106)
    dur = 0.4
    n = ns(dur)
    t = tvec(n)
    y = np.sin(phase_from_freq(58 + 50 * np.exp(-t / 0.015))) * env_exp(n, 0.05, 0.0008) * 0.9
    y += lp(white(n, rng), 350) * env_exp(n, 0.035, 0.0005) * 0.9
    y += saturate(bp(white(n, rng), 400, 2500) * env_exp(n, 0.02, 0.0005) * 4, 2.5) * 0.35
    for _ in range(45):  # soil grains, density decays
        tt = rng.exponential(0.05) + 0.005
        if tt > 0.3:
            continue
        L = ns(rng.uniform(0.001, 0.004))
        g = bp(white(L, rng), rng.uniform(1200, 3000), rng.uniform(3500, 7000)) * np.exp(-tvec(L) / 0.0012)
        mix_at(y, g, ns(tt), rng.uniform(0.05, 0.25) * np.exp(-tt / 0.1))
    for _ in range(3):  # pebble ticks
        f = rng.uniform(2200, 4200)
        L = ns(0.03)
        mix_at(y, np.sin(2 * np.pi * f * tvec(L)) * np.exp(-tvec(L) / 0.008), ns(rng.uniform(0.03, 0.2)),
               rng.uniform(0.04, 0.1))
    return gs.finish(y, -1.0, gs.IR_SMALL, 0.08, tail=0.4, fade_out=0.03)


def sfx_crowd_cheer():
    """3 s distant army roar: 56 shouting voices (pitch contour 'hoo-RAAH', jitter)
    grouped into 4 vowels through formant resonators + formant-filtered noise
    bursts + low rumble; far-away low-pass and big valley reverb."""
    rng = np.random.default_rng(2107)
    dur = 3.0
    n = ns(dur)
    vowels = {"ah": ([750, 1150, 2500], [1.0, 0.6, 0.28]), "eh": ([560, 1800, 2550], [1.0, 0.5, 0.3]),
              "oh": ([560, 860, 2450], [1.0, 0.55, 0.2]), "ay": ([660, 1700, 2500], [1.0, 0.5, 0.3])}
    names = list(vowels)
    groups = {v: np.zeros(n) for v in names}
    for i in range(56):
        v = names[i % 4]
        f0 = rng.uniform(105, 230) * (1.3 if rng.random() < 0.2 else 1.0)
        on = rng.uniform(0.0, 0.5)
        off = rng.uniform(on + 1.2, 2.6)
        f = env_points(n, [(0, f0 * 0.8), (on, f0 * 0.8), (on + 0.25, f0 * 1.14), (on + 0.6, f0 * 1.05),
                           (off, f0 * 0.93), (dur, f0 * 0.85)], "log")
        f = f * (1 + 0.012 * smooth_noise(n, 18, rng)) * \
            (1 + 0.006 * np.sin(2 * np.pi * rng.uniform(4.5, 6.5) * tvec(n)))
        ph = np.cumsum(f) / SR
        src = 2 * (ph % 1.0) - 1 + 0.35 * white(n, rng)
        a = env_points(n, [(0, 0), (on, 0), (on + 0.12, 1), (off, 0.8), (off + 0.35, 0), (dur, 0)])
        a *= np.clip(1 + 0.3 * smooth_noise(n, 4, rng), 0.2, 2) * rng.uniform(0.5, 1.0)
        groups[v] += src * a
    y = np.zeros(n)
    for v in names:
        F, G = vowels[v]
        y += resonator_bank(groups[v], F, [5, 7, 9], G) + 0.05 * groups[v]
    crowd = env_points(n, [(0, 0), (0.15, 0.3), (0.6, 1), (1.8, 0.9), (2.6, 0.4), (dur, 0.15)])
    breath = pink(n, rng) * crowd
    y += 0.25 * resonator_bank(breath, [700, 1200, 2500], [3, 4, 5], [1, 0.6, 0.3])
    y += 0.35 * brown(n, rng, lo=40, hi=250) * crowd  # stamping / rumble
    y = lp(hp(y, 110, 2), 2600, 3)  # distance
    return gs.finish(y, -1.0, gs.IR_VALLEY, 0.5, tail=3.0, fade_out=0.3)


def davul_dum(rng, vel=1.0, dur=1.3):
    """Big deep davul bass head: lower and longer than the chapter-1 dhol."""
    n = ns(dur)
    t = tvec(n)
    f0 = rng.uniform(44, 48)
    f = f0 + 70 * np.exp(-t / 0.03)
    ph = phase_from_freq(f)
    y = np.sin(ph) * env_exp(n, 0.45, 0.0015)
    y += 0.28 * np.sin(ph * 1.59 + 1) * env_exp(n, 0.12) + 0.12 * np.sin(ph * 2.14 + 2) * env_exp(n, 0.06)
    y += bp(white(n, rng), 70, 450) * env_exp(n, 0.08) * 0.45  # skin body
    y += lp(white(n, rng), 1600) * env_exp(n, 0.012) * 0.45  # beater
    return saturate(y * (1.2 + 0.6 * vel), 1.5) * vel


def sfx_war_drums_loop():
    """8 s seamless (60 BPM, 2 bars): slow deep davul + taiko + stick taks,
    rendered in a ring buffer with circular valley reverb."""
    rng = np.random.default_rng(2108)
    L = ns(8.0)
    y = np.zeros(L)

    def hit(x, beat, g=1.0):
        ring_add(y, x, ns(beat) + int(rng.normal(0, 4) * SR / 1000), g)

    for bar in range(2):
        b = bar * 4
        hit(gm.taiko(rng, 1.0 if bar == 0 else 0.85), b, 0.9)
        hit(davul_dum(rng, 1.0), b)
        hit(davul_dum(rng, 0.55), b + 1.5)
        hit(davul_dum(rng, 0.85), b + 2)
        if bar == 1:
            hit(davul_dum(rng, 0.45), b + 1.75)
        hit(gm.dhol_tak(rng, 0.5), b + 3, 0.7)
    for k, v in enumerate((0.3, 0.38, 0.46, 0.55)):  # pickup into the downbeat
        hit(gm.dhol_tak(rng, v), 7 + k * 0.25, 0.7)
    y = circular(lambda s: peak_eq(peak_eq(shelf(s, 90, -4.0, high=False), 190, 5.0, 0.9), 2500, 3.0, 1.0), y,
                 laps=3)
    return gs.finish_loop(saturate(y * 0.8, 1.2), -1.5, gs.IR_VALLEY, 0.22)


# ==========================================================================
# CHAPTER 3 - «Aralez» SFX
# ==========================================================================
def sfx_aralez_howl():
    """2 s ethereal spirit-dog howl: near-sinusoidal voice with 'oo-AH-oo' moving
    formants, detuned + fifth 'ghost' voices, whistling breath, echo and a long
    4.2 s reverb (tail faded to fit 2.0 s)."""
    rng = np.random.default_rng(3101)
    dv = 1.72
    n = ns(dv)
    t = tvec(n)
    f0 = env_points(n, [(0, 330), (0.12, 470), (0.35, 565), (1.1, 545), (1.45, 470), (dv, 370)], "log")
    vib = 1 + 0.006 * np.clip((t - 0.3) / 0.3, 0, 1) * np.sin(2 * np.pi * 5.4 * t)
    f0 = f0 * vib * (1 + 0.003 * smooth_noise(n, 6, rng))
    amp = env_points(n, [(0, 0), (0.15, 0.8), (0.4, 1), (1.2, 0.9), (1.55, 0.4), (dv, 0)])
    o = env_points(n, [(0, 0.1), (0.4, 1.0), (1.1, 0.9), (dv, 0.15)])
    y = np.zeros(n)
    for ratio, g in ((1.0, 1.0), (1.004, 0.6), (1.498, 0.16)):
        f = f0 * ratio
        fund = np.sin(phase_from_freq(f))
        src = additive(f, lambda k, fk: 1.0 / k ** 1.4, rng, max_harm=16, fmax=9000)
        tract = svf(src, 380 + 520 * o, 0.8, "bp") + 0.5 * svf(src, 880 + 450 * o, 0.8, "bp")
        y += g * (0.65 * fund + 0.45 * tract)
    breath = svf(white(n, rng), 2 * f0, 0.9, "bp") * 0.12 + bp(white(n, rng), 1500, 5000) * 0.03
    y = (y + breath) * amp
    y = delay_echo(y, 0.23, fb=0.35, wet=0.22, lp_hz=2500, taps=3)
    return gs.finish(y, -1.0, IR_HOWL, 0.55, tail=2.0, fade_out=0.35)


def sfx_soul_chime():
    """0.6 s crystalline pickup chime, C6 then G6 (a fifth), glass partials.
    No random elements at all (deterministic phases, seeded IR)."""
    dur = 0.6
    n = ns(dur)
    y = np.zeros(n)
    mix_at(y, bell(1046.5, dur, ring=0.8), 0, 0.8)
    mix_at(y, bell(1568.0, dur - 0.07, ring=0.9), ns(0.07), 1.0)
    t = tvec(n)
    y += 0.06 * sum(np.sin(2 * np.pi * f * t) for f in (6271.9, 7040.0, 8372.0)) * np.exp(-np.maximum(t - 0.07, 0) / 0.05) \
        * np.clip((t - 0.07) / 0.002, 0, 1)
    return gs.finish(y, -1.0, gs.IR_SMALL, 0.15, tail=0.6, fade_out=0.08, hp_hz=200)


def sfx_wraith_hiss():
    """1.2 s: three layered whispers (noise through moving formants) + 'sss'
    sibilance + low period-doubled growl, small cave reverb."""
    rng = np.random.default_rng(3103)
    dur = 1.2
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    for k, (off, sc, g) in enumerate([(0.0, 1.0, 1.0), (0.04, 0.88, 0.7), (0.09, 1.12, 0.55)]):
        m = n - ns(off)
        nz = white(m, rng)
        F1 = env_points(m, [(0, 600), (0.3, 900), (dur, 500)], "log") * sc
        F2 = env_points(m, [(0, 1500), (0.3, 2200), (dur, 1200)], "log") * sc
        w = svf(nz, F1, 0.85, "bp") + 0.7 * svf(nz, F2, 0.85, "bp") + 0.4 * svf(nz, 2700 * sc, 0.8, "bp")
        s = bp(nz, 4200 * sc, 9000) * env_points(m, [(0, 0), (0.45, 0.1), (0.8, 1), (1.1 - off, 0.6), (dur - off, 0)])
        a = env_points(m, [(0, 0), (0.25, 0.9), (0.6, 1.0), (1.05 - off, 0.6), (dur - off, 0)])
        a *= np.clip(1 + 0.35 * smooth_noise(m, 9, rng), 0.1, 2)
        mix_at(y, (w + 0.3 * s) * a, ns(off), g)
    growl = gs.glottal_roar(1.1, [(0, 46), (0.3, 58), (0.8, 52), (1.1, 38)], rng,
                            [(0, 0), (0.25, 0.8), (0.8, 0.7), (1.1, 0)], fscale=0.8, growl=0.9, rasp=0.5,
                            rough=0.5, sub_oct=0.5, open_pts=[(0, 0.2), (0.4, 0.7), (1.1, 0.2)])
    mix_at(y, lp(growl, 1500), ns(0.05), 1.0)
    y = lp(y, 6000, 2)
    return gs.finish(y, -1.0, IR_CAVE_M, 0.25, tail=1.2, fade_out=0.15)


def drip(rng, f0, plop=0.0):
    n = ns(0.1)
    t = tvec(n)
    f = f0 * (1 + 0.9 * (1 - np.exp(-t / 0.008)))  # rising bubble resonance
    y = np.sin(phase_from_freq(f)) * env_exp(n, 0.011, attack=0.0006)
    y += 0.25 * hp(white(n, rng), 3000) * env_exp(n, 0.0008)
    if plop:
        y += plop * np.sin(2 * np.pi * rng.uniform(250, 420) * t) * env_exp(n, 0.03, 0.001)
    return y


def sfx_cave_ambience_loop():
    """12 s seamless STEREO cave bed: deep wind bands + cave-mouth moans + sub
    rumble swells (all exactly periodic noise) + dripping water (two regular
    drip spots with periods 12/7 s and 12/5 s, plus scattered drips), drips in
    a wet circular cave reverb."""
    rng = np.random.default_rng(3104)
    L = ns(12.0)
    wind = np.zeros((2, L))
    for lo, hi, g in [(30, 150, 0.9), (100, 450, 0.6), (400, 1200, 0.16), (1500, 4000, 0.03)]:
        am = np.clip(0.55 + 0.45 * periodic_lfo(L, rng, 4, cycles_min=1), 0.05, 2)
        for ch in range(2):
            wind[ch] += g * spectral_noise(L, rng, -3.0, lo=lo, hi=hi) * am
    for fc in (92, 138, 205, 310):  # cave-mouth moans
        sw = np.clip(periodic_lfo(L, rng, 3, cycles_min=1), 0, 1) ** 2
        p = rng.uniform(-0.6, 0.6)
        wind += pan(0.22 * spectral_noise(L, rng, 0.0, lo=fc * 0.96, hi=fc * 1.04) * sw, p)
    rum = brown(L, rng, lo=18, hi=80) * (0.6 + 0.4 * periodic_lfo(L, rng, 2, cycles_min=1))
    wind += 0.8 * np.stack([rum, rum])
    wind = reverb_circular(wind, IR_CAVE_ST, wet=0.2, dry=1.0)

    drips = np.zeros((2, L))
    f_a, f_b = 1380.0, 2050.0
    for k in range(7):
        ring_add(drips, pan(drip(rng, f_a * rng.uniform(0.99, 1.01), 0.3), -0.55), ns(0.4 + k * 12 / 7),
                 rng.uniform(0.75, 1.0))
    for k in range(5):
        ring_add(drips, pan(drip(rng, f_b * rng.uniform(0.99, 1.01)), 0.6), ns(1.1 + k * 12 / 5),
                 rng.uniform(0.5, 0.7))
    for _ in range(9):
        ring_add(drips, pan(drip(rng, rng.uniform(900, 3000), rng.uniform(0, 0.4)), rng.uniform(-0.9, 0.9)),
                 int(rng.integers(0, L)), rng.uniform(0.25, 0.6))
    drips = reverb_circular(drips, IR_CAVE_ST, wet=0.45, dry=1.0)
    y = wind / (np.std(wind) + 1e-9) + 0.55 * drips / (np.max(np.abs(drips)) + 1e-9) * 6.0
    return finish_loop_st(y, -3.0)


def sfx_gate_open():
    """3 s triumphant spirit gate: stone rumble, choir swell 'oo'->'ah' on D major
    with high voices entering, rising crystalline arpeggio + shimmer, low boom."""
    rng = np.random.default_rng(3105)
    dur = 3.0
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    y += gs.choir(dur, [38, 50, 57, 62], rng, "oo", [(0, 0), (0.35, 0.6), (1.2, 0.55), (1.9, 0.15), (dur, 0)],
                  voices=2) * 0.7
    y += gs.choir(dur, [50, 57, 62, 66, 69], rng, "ah", [(0, 0), (0.6, 0.2), (1.6, 1), (2.4, 0.9), (dur, 0)],
                  voices=2) * 0.9
    hi = gs.choir(1.7, [74, 78, 81], rng, "ah", [(0, 0), (0.5, 1), (1.1, 0.9), (1.7, 0)], voices=2)
    mix_at(y, hi, ns(1.3), 0.4)
    for k, m in enumerate((86, 90, 93, 98, 102)):  # D6 F#6 A6 D7 F#7
        mix_at(y, bell(float(mtof(m)), 1.4, ring=2.0), ns(0.95 + 0.13 * k), 0.16)
    for _ in range(8):
        m = int(rng.choice([86, 90, 93, 98]))
        mix_at(y, bell(float(mtof(m)), 0.9, ring=1.2), ns(rng.uniform(1.5, 2.4)), rng.uniform(0.04, 0.09))
    sh = bp(white(n, rng), 5000, 11000) * (0.6 + 0.4 * np.sin(2 * np.pi * 13 * t))
    y += 0.12 * sh * env_points(n, [(0, 0), (1.0, 0.2), (1.6, 1), (2.4, 0.4), (dur, 0)]) ** 1.5
    y += 0.3 * lp(brown(n, rng), 220) * env_points(n, [(0, 0), (0.2, 1), (1.3, 0.6), (1.7, 0)])  # stone grind
    mix_at(y, gs.drum_hit(1.4, 110, 38, 0.5, 0.4, seed=3), ns(1.5), 0.55)
    y += 0.25 * np.sin(2 * np.pi * mtof(26) * t) * env_points(n, [(0, 0), (1.5, 0.6), (2.4, 0.4), (dur, 0)])
    return gs.finish(saturate(y * 0.8, 1.2), -1.0, gs.IR_VALLEY, 0.35, tail=3.0, fade_out=0.35)


# ==========================================================================
# MUSIC
# ==========================================================================
def _set_mode(scale):
    """gen_music.scale_up (grace notes / trills) reads gen_music.SCALE."""
    gm.SCALE = list(scale)


# ---------------- «Hayk»: 80 BPM, 24 bars = 72 s, A Phrygian (A Bb C D E F G)
HAYK_A = [(0, 1.5, 64, "a"), (1.5, .5, 65), (2, 2, 69), (4, 1, 67), (5, .5, 65), (5.5, .5, 64), (6, 2, 65, "g"),
          (8, 1, 65), (9, .5, 64), (9.5, .5, 65), (10, 2, 69), (12, 1, 67), (13, 1, 65), (14, 2, 62, "g"),
          (16, 1.5, 69, "a"), (17.5, .5, 70), (18, 2, 72), (20, 1, 72), (21, .5, 70), (21.5, .5, 69), (22, 2, 67),
          (24, 1.5, 70, "a"), (25.5, .5, 69), (26, 1, 67), (27, 1, 65), (28, 3.5, 64, "t")]
HAYK_B = [(0, 2, 74, "g"), (2, 1, 72), (3, 1, 70), (4, 2, 69), (6, .5, 70), (6.5, .5, 69), (7, 1, 65),
          (8, 3, 74, "a"), (11, .5, 72), (11.5, .5, 74), (12, 1, 77, "m"), (13, 1, 74), (14, 2, 70),
          (16, 1.5, 72, "a"), (17.5, .5, 70), (18, 2, 69), (20, 1, 67), (21, 1, 70), (22, 1, 74), (23, 1, 72),
          (24, 4, 76, "t"), (28, .5, 74), (28.5, .5, 72), (29, 1, 70), (30, 1.5, 69)]
HAYK_CALL = [(0, 1, 69, "a"), (1, 1, 72), (2, 2, 76), (4, 1, 77, "g"), (5, 1, 76), (6, 2, 74),
             (8, 1.5, 76, "a"), (9.5, .5, 74), (10, 2, 72), (12, 1, 70), (13, 1, 69), (14, 1.5, 70)]
H_PROG = ["Am", "Am", "Bb", "Am", "Am", "Am", "F", "G", "Am", "Am", "Bb", "Am",
          "Dm", "Dm", "Bb", "Bb", "F", "G", "Am", "Am", "Am", "Bb", "Am", "Bb"]
H_ROOT = {"Am": 45, "Bb": 46, "F": 41, "G": 43, "Dm": 38}
H_CHOIR = {"Am": [45, 52, 57, 60], "Bb": [46, 53, 58, 62], "F": [41, 48, 53, 57], "G": [43, 50, 55, 62],
           "Dm": [50, 57, 62, 65]}


def make_hayk():
    _set_mode([0, 2, 3, 5, 7, 8, 10])  # pitch set of A Phrygian expressed from D
    tr = gm.Track(80, 24, seed=2200)
    rng = tr.rng
    L = tr.L
    bt = tr.beat
    # low brass drone (A1 E2 A2) + dam duduk drone (A2 E3), both loop-periodic
    bd = ifft_drone(L, [33, 40, 45], rng, lambda k, fk: _brass_w(k, fk) / (1 + (fk / 650) ** 2),
                    detune_hz=(0.0, 0.13, -0.09), breathe=0.25)
    tr.stem("drone", 0.25)[:] += np.stack([bd, bd])
    dam = ifft_drone(L, [45, 52], rng, lambda k, fk: (1.0 if k % 2 else 0.6) / k ** 1.1 / (1 + (fk / 1000) ** 2) *
                     (1 + 1.2 * np.exp(-0.5 * (np.log2(fk / 900) / 0.5) ** 2)), breathe=0.2)
    tr.stem("dam", 0.3)[:] += np.stack([dam, dam])
    wb = gm.wind_bed(L, rng)
    tr.stem("wind", 0.1)[:] += np.stack([wb, np.roll(wb, ns(0.41))])

    for bar in range(24):
        b = bar * 4
        c = H_PROG[bar]
        r = H_ROOT[c]
        if bar < 4:  # intro: lone taiko, then davul answers
            tr.add("drums", gm.taiko(rng, 0.95 if bar % 2 == 0 else 0.75), b, 1.0, 0.0, 0.35, 3)
            if bar >= 2:
                tr.add("drums", davul_dum(rng, 0.6), b + 2.5, 1.0, -0.1, 0.25, 4)
                tr.add("drums", davul_dum(rng, 0.75), b + 3, 1.0, -0.1, 0.25, 4)
        elif bar < 20:  # slow war groove
            tr.add("drums", gm.taiko(rng, 1.0), b, 1.0, 0.0, 0.35, 3)
            tr.add("drums", davul_dum(rng, 1.0), b, 1.0, -0.1, 0.25, 3)
            tr.add("drums", davul_dum(rng, 0.55), b + 1.5, 1.0, -0.1, 0.25, 4)
            tr.add("drums", davul_dum(rng, 0.85), b + 2, 1.0, -0.1, 0.25, 4)
            tr.add("drums", gm.dhol_tak(rng, 0.5), b + 3, 1.0, 0.2, 0.25, 4)
            if bar >= 12:
                tr.add("drums", gm.dhol_tak(rng, 0.4), b + 1, 1.0, 0.2, 0.25, 4)
                tr.add("drums", gm.dhol_tak(rng, 0.3), b + 3.5, 1.0, 0.2, 0.25, 4)
                for e in range(8):
                    tr.add("perc", gm.daf(rng, 0.35 if e % 2 == 0 else 0.2, 0.7), b + e / 2, 1.0,
                           0.4 if e % 2 else -0.4, 0.25, 5)
            if bar % 4 == 3:
                for k, v in enumerate((0.3, 0.4, 0.5)):
                    tr.add("drums", gm.dhol_tak(rng, v), b + 3.25 + k * 0.25, 1.0, 0.2, 0.25, 3)
        else:  # build: davul on every beat, then a tak roll into the loop downbeat
            for q in range(4):
                tr.add("drums", davul_dum(rng, 0.65 + 0.03 * ((bar - 20) * 4 + q)), b + q, 1.0, -0.1, 0.25, 3)
            tr.add("drums", gm.taiko(rng, 0.9), b, 1.0, 0.0, 0.35, 3)
            tr.add("drums", gm.taiko(rng, 0.7), b + 2, 1.0, 0.0, 0.35, 3)
            if bar == 23:
                for s16 in range(8, 16):
                    tr.add("drums", gm.dhol_tak(rng, 0.25 + 0.05 * (s16 - 8)), b + s16 / 4, 1.0, 0.2, 0.25, 3)
        # brass: long swells in the intro, braam-like hits every 2 bars after
        if bar % 2 == 0:
            if bar < 4:
                br = brass(2 * 4 * bt + 0.3, [r - 12, r, r + 7], rng, [(0, 0), (3.5, 0.7), (6.3, 0.2)],
                           [(0, 0), (2.5, 0.8), (5.0, 1.0), (6.3, 0)])
            else:
                br = brass(2 * 4 * bt, [r - 12, r, r + 7, r + 12], rng,
                           [(0, 0), (0.12, 1), (0.8, 0.45), (6.0, 0.1)],
                           [(0, 0), (0.03, 1), (0.5, 0.7), (5.5, 0.45), (6.0, 0)], drive=1.8)
            g = 0.6 if 4 <= bar < 12 else 1.0
            tr.add("brass", br, b, g, 0.0, 0.45)  # mono-centred: a sample-offset copy would comb in mono
        # low strings ostinato (tension) in B and the build
        if bar >= 12:
            pat = [0, 0, 12, 0, 1, 0, 10, 0]  # A A A' A Bb A G' A
            for e, iv in enumerate(pat):
                v = (1.0 if e in (0, 4) else 0.7) * rng.uniform(0.9, 1.05) * (1.1 if bar >= 20 else 0.9)
                tr.add("strings", gm.string_note(0.24, r + iv, rng, v), b + e / 2, 1.0, -0.25, 0.2, 2)
        if 12 <= bar < 20 and bar % 2 == 0:
            tr.add("choir", gm.choir(2 * 4 * bt, H_CHOIR[c], rng, "oh" if bar < 16 else "ah", att=0.8, rel=1.0,
                                     voices=2), b, 1.0, send=0.5)
    gm.add_reed(tr, "lead", HAYK_A, 16, "duduk", 1.0, -0.1, 0.4)
    gm.add_reed(tr, "lead", HAYK_B, 48, "duduk", 1.0, -0.1, 0.4)
    gm.add_reed(tr, "lead", HAYK_B, 48, "duduk", 0.35, 0.2, 0.4, transpose=-12)
    gm.add_reed(tr, "lead", HAYK_CALL, 80, "zurna", 0.6, 0.05, 0.35)
    gm.add_reed(tr, "lead", HAYK_CALL, 80, "duduk", 0.45, -0.2, 0.35, transpose=-12)
    for bar in (11, 23):
        cs = gm.cymbal_swell(4 * bt, rng)
        tr.add("fx", np.stack([cs, np.roll(cs, 45)]), bar * 4, 0.8, send=0.3)
    rs = gm.riser(4 * 4 * bt, rng)
    tr.add("fx", np.stack([rs, rs]), 80, 0.5, send=0.4)
    ir = make_ir(t60=3.0, predelay=0.04, stereo=True, seed=80, damp_hi=0.3, er_spread=0.12)
    targets = {"drums": -20, "lead": -22, "brass": -24, "strings": -27, "choir": -28, "drone": -28,
               "dam": -33, "perc": -32, "fx": -31, "wind": -37}
    return gm.mixdown(tr, targets, ir, verb_wet=0.35)


# ---------------- «Aralez»: 60 BPM, 18 bars = 72 s, D double-harmonic (D Eb F# G A Bb C#)
ARALEZ_A = [(0, 3, 62), (3, 1, 63), (4, 2, 66, "g"), (6, 2, 69),
            (8, 4, 70, "t"), (12, 2, 67), (14, 1.5, 63),
            (16, 1, 73), (17, 3, 74, "g"), (20, 1, 73), (21, 1, 70), (22, 2, 69),
            (24, 2, 67), (26, 1, 70), (27, 1, 69), (28, 3.5, 67, "t")]
ARALEZ_B = [(0, 2, 75, "g"), (2, 1, 74), (3, 1, 70), (4, 3.5, 67, "t"),
            (8, 2, 70), (10, 1, 69), (11, 1, 70), (12, 1.5, 74, "m"), (13.5, .5, 73), (14, 2, 70),
            (16, 1, 67), (17, 1, 66), (18, 1, 63), (19, 4.5, 62)]
A_PROG = ["D", "D", "Eb", "D", "Gm", "Eb", "Bb", "Eb", "D"]  # one chord per 2 bars
A_PAD = {"D": [50, 57, 62, 66], "Eb": [51, 58, 63, 67], "Gm": [55, 58, 62, 67], "Bb": [46, 53, 58, 62]}


def make_aralez():
    _set_mode([0, 1, 4, 5, 7, 8, 11])
    tr = gm.Track(60, 18, seed=3300)
    rng = tr.rng
    L = tr.L
    bt = tr.beat
    dr = ifft_drone(L, [38, 45], rng, lambda k, fk: (1.0 / k ** 1.2) / (1 + (fk / 500) ** 2),
                    detune_hz=(0.0, 0.07), breathe=0.3)
    tr.stem("drone", 0.35)[:] += np.stack([dr, dr])
    wb = gm.wind_bed(L, rng)
    tr.stem("wind", 0.2)[:] += np.stack([wb, np.roll(wb, ns(0.53))])
    for i, c in enumerate(A_PROG):
        vowel = ["oo", "oo", "oh", "ah", "ah", "oh", "ah", "oh", "oo"][i]
        tr.add("pad", pad_chord(2 * 4 * bt, A_PAD[c], rng, att=2.5, rel=3.0), i * 8, 1.0, send=0.5)
        tr.add("choir", gm.choir(2 * 4 * bt, [m + 12 for m in A_PAD[c][1:]], rng, vowel, att=2.0, rel=2.5,
                                 voices=2), i * 8, 1.0, send=0.6)
    # slow pulse: soft heartbeat lub-dub every 2 beats (bars 2-15), sub underneath
    for bar in range(2, 16):
        for hb in (0, 2):
            b = bar * 4 + hb
            v = 0.55 if hb == 0 else 0.4
            tr.add("pulse", lp(gm.dhol_dum(rng, v), 500), b, 1.0, 0.0, 0.3, 3)
            tr.add("pulse", lp(gm.dhol_dum(rng, v * 0.6), 400), b + 0.35, 1.0, 0.0, 0.3, 3)
    # crystalline spirit bells (scale tones, octave 6)
    bell_notes = [86, 87, 90, 91, 93, 94, 97, 98]
    for bar in range(2, 17):
        for e in range(8):
            if rng.random() < 0.13:
                m = int(rng.choice(bell_notes))
                x = bell(float(mtof(m)), 2.5, ring=4.0)
                tr.add("bells", x, bar * 4 + e / 2, rng.uniform(0.4, 1.0), rng.uniform(-0.7, 0.7), 0.7, 5)
    gm.add_reed(tr, "duduk", ARALEZ_A, 8, "duduk", 1.0, -0.1, 0.55)
    gm.add_reed(tr, "duduk", ARALEZ_B, 40, "duduk", 1.0, 0.1, 0.55)
    gm.add_reed(tr, "duduk", ARALEZ_B, 40, "duduk", 0.3, -0.25, 0.55, transpose=-12)
    ir = make_ir(t60=4.8, predelay=0.05, stereo=True, seed=81, damp_hi=0.3, er_spread=0.08)
    targets = {"duduk": -21, "choir": -24.5, "pad": -25, "drone": -29, "pulse": -27, "bells": -29.5,
               "wind": -34}
    return gm.mixdown(tr, targets, ir, verb_wet=0.5)


# ==========================================================================
# driver + verification
# ==========================================================================
SFX_ALL = [sfx_bow_draw, sfx_bow_release, sfx_arrow_whoosh, sfx_arrow_hit_flesh, sfx_arrow_hit_wood,
           sfx_arrow_hit_ground, sfx_crowd_cheer, sfx_war_drums_loop,
           sfx_aralez_howl, sfx_soul_chime, sfx_wraith_hiss, sfx_cave_ambience_loop, sfx_gate_open]
MUSIC_ALL = [("music_hayk", make_hayk), ("music_aralez", make_aralez)]

EXPECTED = {"sfx_bow_draw": 0.9, "sfx_bow_release": 0.5, "sfx_arrow_whoosh": 1.2, "sfx_arrow_hit_flesh": 0.6,
            "sfx_arrow_hit_wood": 0.5, "sfx_arrow_hit_ground": 0.4, "sfx_crowd_cheer": 3.0,
            "sfx_war_drums_loop": 8.0, "sfx_aralez_howl": 2.0, "sfx_soul_chime": 0.6, "sfx_wraith_hiss": 1.2,
            "sfx_cave_ambience_loop": 12.0, "sfx_gate_open": 3.0, "music_hayk": 72.0, "music_aralez": 72.0}


def seam(x):
    """Loop seam: |last-first| jump / 99th-pct sample step (worst channel), and
    the RMS of 20 ms either side of the seam, in dB."""
    jumps = []
    for ch in x:
        d = np.abs(np.diff(ch))
        jumps.append(abs(ch[0] - ch[-1]) / (np.percentile(d, 99) + 1e-9))
    w = ns(0.02)
    m = x.mean(axis=0)
    r = 20 * np.log10((np.sqrt(np.mean(m[-w:] ** 2)) + 1e-9) / (np.sqrt(np.mean(m[:w] ** 2)) + 1e-9))
    return max(jumps), r


def verify():
    hdr = f"{'file':28s} {'ch':>2s} {'sr':>6s} {'bit':>3s} {'dur s':>6s} {'want':>6s} {'peak':>6s} {'clip':>4s} " \
          f"{'DC':>8s} {'LUFS':>6s} {'seam':>14s}"
    print(hdr)
    print("-" * len(hdr))
    ok = True
    for name, want in EXPECTED.items():
        p = (MUS if name.startswith("music_") else SFX) / f"{name}.wav"
        if not p.exists():
            print(f"{name:28s} MISSING")
            ok = False
            continue
        x, sr, sw = read_wav(p)
        dur = x.shape[1] / sr
        pk = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
        clip = int(np.sum(np.abs(x) >= 32767 / 32768))
        dc = float(np.max(np.abs(x.mean(axis=1))))
        L = lufs(x)
        s = ""
        bad = sr != 48000 or sw != 2 or clip or pk > -0.99 or dc > 1e-3 or abs(dur - want) > 1e-3
        if "loop" in name or name.startswith("music_"):
            j, r = seam(x)
            s = f"{j:4.2f}x {r:+5.1f}dB"
            bad |= j > 1.0
        ok &= not bad
        print(f"{name:28s} {x.shape[0]:2d} {sr:6d} {sw * 8:3d} {dur:6.2f} {want:6.2f} {pk:6.2f} {clip:4d} "
              f"{dc:8.6f} {L:6.1f} {s:>14s}{'  <-- CHECK' if bad else ''}")
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    return ok


def main(argv):
    SFX.mkdir(parents=True, exist_ok=True)
    MUS.mkdir(parents=True, exist_ok=True)
    if "--verify" in argv:
        return 0 if verify() else 1
    sel = [a for a in argv[1:] if not a.startswith("-")]
    for i, fn in enumerate(SFX_ALL):
        name = fn.__name__
        if sel and not any(s in name for s in sel):
            continue
        y = fn()
        assert np.all(np.isfinite(y)), name
        write_wav(SFX / f"{name}.wav", y, seed=500 + i)
        print(f"{name:26s} {y.shape[-1] / SR:6.2f}s  peak {20 * np.log10(np.max(np.abs(y))):6.2f} dBFS  "
              f"LUFS {lufs(y):6.1f}", flush=True)
    for i, (name, fn) in enumerate(MUSIC_ALL):
        if sel and not any(s in name for s in sel):
            continue
        mix = fn()
        assert np.all(np.isfinite(mix)), name
        write_wav(MUS / f"{name}.wav", mix, seed=600 + i)
        gm.report(name, mix)
    print()
    return 0 if verify() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
