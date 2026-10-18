#!/usr/bin/env python3
"""
gen_sfx.py - procedural SFX for "Vahagn: Vishapakagh".

Writes 48 kHz / 16-bit / mono WAVs to ../sfx/.  Deterministic (fixed seeds).
Run:  python3 gen_sfx.py            (all)
      python3 gen_sfx.py roar boost (only names containing these substrings)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from dsp import (SR, ns, tvec, fit, mix_at, ring_add, env_exp, env_adsr, env_points, fade,
                 spectral_noise, white, pink, brown, smooth_noise, periodic_lfo,
                 lp, hp, bp, peak_eq, shelf, resonator_bank, svf, svf_circular, circular,
                 saturate, limiter, compress, additive, sine_sweep, phase_from_freq,
                 make_ir, reverb, reverb_circular, delay_echo, lufs, normalize_peak, remove_dc,
                 mtof, write_wav, undb)

OUT = Path(__file__).resolve().parent.parent / "sfx"
CC0 = Path(__file__).resolve().parent / "cc0_sources" / "kenney"  # CC0 recordings (see CREDITS.md)


def cc0(name, pitch=1.0):
    """Load a CC0 Kenney sample (pre-decoded 48 kHz mono WAV); pitch<1 = slower/lower.
    Returns None if the file is missing so every sound still has a procedural path."""
    from dsp import read_wav
    p = CC0 / f"{name}.wav"
    if not p.exists():
        return None
    x, sr, _ = read_wav(p)
    x = x[0]
    if pitch != 1.0:
        n_out = int(len(x) / pitch)
        x = np.interp(np.arange(n_out) * pitch, np.arange(len(x)), x)
    return x / (np.max(np.abs(x)) + 1e-9)

# Shared impulse responses (mono): open-air mountain/sky ambience
IR_SKY = make_ir(t60=2.6, predelay=0.03, stereo=False, seed=11, damp_hi=0.3, er_spread=0.09)
IR_SMALL = make_ir(t60=0.9, predelay=0.008, stereo=False, seed=12, damp_hi=0.45, er_spread=0.03)
IR_VALLEY = make_ir(t60=3.6, predelay=0.05, stereo=False, seed=13, damp_hi=0.25, er_spread=0.12)


# ==========================================================================
# building blocks
# ==========================================================================
def _crackle_kernels(rng, bright=1.0, k=8):
    ks = []
    for i in range(k):
        L = ns(rng.uniform(0.002, 0.014))
        t = tvec(L)
        tau = rng.uniform(0.0006, 0.004)
        nz = rng.standard_normal(L) * np.exp(-t / tau)
        lo = rng.uniform(900, 3500) * bright
        nz = hp(nz, min(lo, 12000), 2)
        if rng.random() < 0.55:  # resonant "ping" of a burst ember
            f = rng.uniform(1800, 7500) * bright
            nz += 0.5 * np.sin(2 * np.pi * min(f, 15000) * t) * np.exp(-t / (tau * 1.6))
        nz = lp(nz, 9000, 2)
        ks.append(nz / (np.max(np.abs(nz)) + 1e-9))
    return ks


def _pop_kernels(rng, k=4):
    ks = []
    for i in range(k):
        L = ns(0.05)
        t = tvec(L)
        nz = bp(rng.standard_normal(L), rng.uniform(120, 300), rng.uniform(600, 1500), 2)
        nz *= np.exp(-t / rng.uniform(0.006, 0.015))
        ks.append(nz / (np.max(np.abs(nz)) + 1e-9))
    return ks


def crackles(n, rng, rate=40.0, density=None, bright=1.0, pops=0.15, periodic=False):
    """Fire crackle layer: Poisson events, heavy-tailed amplitudes, varied kernels.
    density: optional per-sample 0..1 weighting of event probability."""
    out = np.zeros(n)
    dur = n / SR
    count = rng.poisson(rate * dur)
    kers = _crackle_kernels(rng, bright)
    popk = _pop_kernels(rng)
    if density is not None:
        cdf = np.cumsum(density + 1e-9)
        cdf /= cdf[-1]
        pos = np.searchsorted(cdf, rng.random(count))
    else:
        pos = rng.integers(0, n, count)
    amps = np.minimum(rng.pareto(2.2, count) + 0.15, 6.0) * rng.choice([-1, 1], count)
    for p, a in zip(pos, amps):
        if rng.random() < pops:
            k = popk[rng.integers(len(popk))] * 1.4
        else:
            k = kers[rng.integers(len(kers))]
        if periodic:
            ring_add(out, k, int(p), a)
        else:
            mix_at(out, k, int(p), a)
    return out / 4.0


def fire_bed(n, rng, periodic=False, flicker_rate=9.0, body=1.0, hiss=0.12, low_hz=900.0):
    """Roaring flame body: brown/pink noise, turbulent AM, airy hiss."""
    roar = brown(n, rng, lo=35, hi=low_hz) * 0.8 + pink(n, rng, lo=180, hi=2600) * 0.35
    turb = smooth_noise(n, flicker_rate, rng, periodic=True if periodic else False)
    slow = smooth_noise(n, 1.2, rng, periodic=True if periodic else False)
    am = np.clip(0.75 + 0.22 * turb + 0.18 * slow, 0.15, 2.0)
    h = spectral_noise(n, rng, 0.0, lo=2500, hi=9500)
    am2 = np.clip(0.7 + 0.35 * smooth_noise(n, 25.0, rng, periodic=periodic), 0.05, 2)
    return body * roar * am + hiss * h * am2


def explosion(dur=2.5, size=1.0, seed=1, tail_fire=0.6, debris=1.0, bright=1.0):
    rng = np.random.default_rng(seed)
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    # 1) transient crack
    tr = white(ns(0.012), rng) * env_exp(ns(0.012), 0.0025)
    tr = hp(tr, 700) * 0.9
    mix_at(y, tr, 0, 0.9)
    # 2) body: noise through a falling resonant lowpass
    body = white(n, rng)
    env = env_exp(n, 0.16 * size, attack=0.003) * 0.7 + env_exp(n, 0.55 * size) * 0.3
    fc = 220 + 7800 * bright * np.exp(-t / (0.09 * size))
    body = svf(body * env, fc, res=0.25, mode="lp") * 1.4
    y += body
    # 3) sub boom with pitch drop, gently saturated
    f = 32 + 70 * np.exp(-t / (0.07 * size))
    sub = np.sin(phase_from_freq(f)) * env_exp(n, 0.32 * size, attack=0.004)
    y += saturate(sub * 1.6, 1.8) * 0.9 * min(size, 1.3)
    # 3b) mid "punch" (120-500 Hz) so the blast reads on laptop speakers
    y += bp(white(n, rng), 110, 520, 2) * env_exp(n, 0.07 * size, attack=0.002) * 1.3
    # 4) rumble tail
    rum = brown(n, rng, lo=25, hi=260) * env_exp(n, 0.7 * size, attack=0.05)
    y += rum * 0.55
    # 5) debris crackle (density decays)
    dens = np.exp(-t / (0.5 * size)) * np.clip(t / 0.03, 0, 1)
    y += crackles(n, rng, rate=140 * size * debris, density=dens, bright=1.0) * 0.55 * np.sqrt(dens + 0.02)
    # 6) fire after-burn
    fb = fire_bed(n, rng) * env_points(n, [(0, 0), (0.06, 1), (0.35 * size, 0.6), (dur, 0)])
    y += lp(fb, 3000) * 0.35 * tail_fire
    y = saturate(y * 0.9, 1.6)
    return y


def whoosh(dur, rng, f_pts, a_pts, res=0.55, gain=1.0):
    n = ns(dur)
    nz = pink(n, rng) * 0.7 + white(n, rng) * 0.3
    fc = env_points(n, f_pts, "log")
    y = svf(nz, fc, res=res, mode="bp")
    y += 0.4 * svf(nz, fc * 1.9, res=0.3, mode="bp")
    flutter = 1 + 0.18 * smooth_noise(n, 22, rng)
    return gain * y * env_points(n, a_pts) * flutter


def glottal_roar(dur, f0_pts, rng, amp_pts, formants=(300, 620, 1350, 2300), fscale=1.0,
                 growl=0.6, rasp=0.6, rough=0.35, jitter=0.03, bright=0.8, sub_oct=0.5, open_pts=None):
    """Monster vocalisation: band-limited pulse source + period-doubling growl +
    pulsed (glottal-synchronous) noise rasp, shaped by moving formants."""
    n = ns(dur)
    t = tvec(n)
    f0 = env_points(n, f0_pts, "log")
    f0 = f0 * (1 + jitter * smooth_noise(n, 28, rng)) * (1 + 0.012 * smooth_noise(n, 4, rng))
    ph = phase_from_freq(f0)
    # source: sawtooth-ish glottal spectrum k^-1 up to ~6.5 kHz
    nh = int(6500 // np.max(f0))
    src = np.zeros(n)
    for k in range(1, nh + 1):
        src += (1.0 / k ** (1.15 - 0.35 * bright)) * np.sin(k * ph + rng.uniform(0, 6.28))
    src /= np.max(np.abs(src)) + 1e-9
    # period doubling growl (sub-harmonic) + rough AM flutter
    src *= (1 + growl * np.sin(ph / 2 + 0.3))
    src *= (1 + rough * smooth_noise(n, 38, rng))
    # glottal-synchronous noise (rasp/hiss of a huge throat)
    pulse = (0.5 + 0.5 * np.cos(ph)) ** 6
    nz = lp(white(n, rng), 4500, 2) * (0.25 + pulse) * rasp
    exc = src + nz
    # formants: closed vs open mouth, morph by open envelope
    F = np.array(formants) * fscale
    closed = resonator_bank(exc, F * 0.8, [4, 5, 6, 7], [1.0, 0.7, 0.35, 0.2])
    opened = resonator_bank(exc, F * 1.15, [3.5, 4.5, 5.5, 6], [1.0, 0.9, 0.55, 0.35])
    o = env_points(n, open_pts or [(0, 0.2), (dur * 0.35, 1.0), (dur, 0.3)])
    voice = closed * (1 - o) + opened * o
    voice += 0.12 * lp(exc, 3000, 2) * o  # a little raw edge
    # deep body / chest resonance an octave down
    if sub_oct:
        sub = np.sin(ph * 0.5) * 0.5 + 0.25 * np.sin(ph)
        voice += sub_oct * lp(sub, 180)
    voice *= env_points(n, amp_pts)
    voice = peak_eq(voice, 850, 4.0, 0.7)
    voice = saturate(voice / (np.max(np.abs(voice)) + 1e-9) * 2.2, 1.5)
    voice = lp(voice, 7000, 2)
    return voice


def drum_hit(dur=0.8, f_hi=140, f_lo=52, decay=0.35, click=0.5, seed=0, modes=(1.0, 1.58, 2.13), mode_gain=0.25):
    rng = np.random.default_rng(seed)
    n = ns(dur)
    t = tvec(n)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.028)
    ph = phase_from_freq(f)
    y = np.sin(ph) * env_exp(n, decay, attack=0.0015)
    for m in modes[1:]:
        y += mode_gain * np.sin(ph * m + rng.uniform(0, 6)) * env_exp(n, decay * 0.35)
    beat = lp(white(n, rng), 2500) * env_exp(n, 0.008) * click
    y += beat
    return saturate(y * 1.3, 1.4)


def horn(dur, midi, rng, scoop=-1.5, bright_pts=None, amp_pts=None, detune=(0, -9, 8), vib=0.12, rasp=0.3):
    """Brass/war-horn ensemble via additive synthesis with opening brightness."""
    n = ns(dur)
    t = tvec(n)
    out = np.zeros(n)
    b = env_points(n, bright_pts or [(0, 350), (0.25, 2600), (dur * 0.7, 2200), (dur, 700)], "log")
    for i, dc in enumerate(detune):
        f0 = mtof(midi) * 2 ** (dc / 1200)
        pitch = f0 * 2 ** (env_points(n, [(0, scoop), (0.18, -0.15), (0.35, 0), (dur, 0)]) / 12)
        vib_env = np.clip((t - 0.6) / 0.8, 0, 1) * vib
        pitch *= 2 ** (vib_env * np.sin(2 * np.pi * (5.1 + 0.3 * i) * t) / 12)
        pitch *= 1 + 0.003 * smooth_noise(n, 3, rng)
        w = lambda k, fk: (1.0 / k ** 0.5) * (1 + 1.2 * np.exp(-0.5 * (np.log2(fk / 1100) / 0.6) ** 2))
        out += additive(pitch, w, rng, fmax=9000, bright=b)
    out /= len(detune)
    # lip buzz rasp at the attack
    nz = bp(white(n, rng), 300, 2500) * env_points(n, [(0, 0), (0.05, 1), (0.4, 0.2), (dur, 0.05)]) * rasp
    out = out / (np.max(np.abs(out)) + 1e-9) + nz * 0.3
    out = peak_eq(out, 900, 3.0, 0.8)
    out *= env_points(n, amp_pts or [(0, 0), (0.12, 0.8), (0.4, 1.0), (dur - 0.5, 0.9), (dur, 0)])
    return saturate(out * 1.5, 1.6)


def reedy(dur, midi_pts, rng, bright=0.9, vib_depth=0.22, vib_rate=5.3, breath=0.05, amp_pts=None, formant=1200.0):
    """Duduk/zurna-ish reed voice (additive with formant), used by stingers."""
    n = ns(dur)
    t = tvec(n)
    m = env_points(n, midi_pts)
    f = mtof(m)
    vib = np.clip((t - 0.2) / 0.4, 0, 1) * vib_depth
    f = f * 2 ** (vib * np.sin(2 * np.pi * vib_rate * t) / 12) * (1 + 0.002 * smooth_noise(n, 5, rng))
    amp = env_points(n, amp_pts or [(0, 0), (0.06, 1), (dur - 0.3, 0.85), (dur, 0)])

    def w(k, fk):
        odd = 1.0 if k % 2 else 0.6
        fm = 1 + 1.6 * np.exp(-0.5 * (np.log2(fk / formant) / 0.45) ** 2)
        return odd * fm / k ** 1.1 / np.sqrt(1 + (fk / (3500 * bright)) ** 4)
    y = additive(f, w, rng, fmax=10000, bright=(1200 + 3000 * amp) * bright)
    y /= np.max(np.abs(y)) + 1e-9
    y += breath * bp(white(n, rng), 1500, 5000) * (0.4 + amp)
    return y * amp


def choir(dur, midis, rng, vowel="ah", amp_pts=None, voices=3):
    F = {"ah": ([730, 1090, 2440], [1.0, 0.6, 0.3]), "oh": ([570, 840, 2410], [1.0, 0.5, 0.25]),
         "oo": ([300, 870, 2240], [1.0, 0.35, 0.15])}[vowel]
    n = ns(dur)
    t = tvec(n)
    out = np.zeros(n)
    for m in midis:
        for v in range(voices):
            f = mtof(m) * 2 ** (rng.uniform(-10, 10) / 1200)
            fr = f * 2 ** (0.12 * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * t + rng.uniform(0, 6)) / 12)

            def w(k, fk):
                e = 0.08
                for c, g in zip(*F):
                    e += g * np.exp(-0.5 * (np.log2(fk / c) / 0.22) ** 2)
                return e / k ** 0.6
            out += additive(fr, w, rng, fmax=8000)
    out /= np.max(np.abs(out)) + 1e-9
    out += 0.03 * bp(white(n, rng), 600, 3000)
    return out * env_points(n, amp_pts or [(0, 0), (0.6, 1), (dur - 0.8, 0.9), (dur, 0)])


def finish(y, peak_db=-1.0, ir=None, wet=0.0, tail=None, hp_hz=32.0, fade_out=0.02, air_hz=11000.0,
           low_shelf_db=-3.0):
    if air_hz:
        y = lp(y, air_hz, 2)
    if ir is not None and wet > 0:
        y = reverb(y, ir, wet=wet, dry=1.0)
        if tail is not None:
            y = fit(y, ns(tail))
    y = hp(y, hp_hz, 2)
    y = shelf(y, 90, low_shelf_db, high=False)  # keep sub energy from eating headroom on small speakers
    y = y - np.mean(y)
    y = fade(y, 0.0005, fade_out)
    y = normalize_peak(y, peak_db + 0.3)
    y = limiter(y, peak_db)
    y = fade(y, 0.0005, fade_out)
    return y


def finish_loop(y, peak_db=-3.0, ir=None, wet=0.0, hp_hz=30.0, air_hz=11000.0):
    """Loop-safe mastering (all processing circular)."""
    if air_hz:
        y = circular(lambda s: lp(s, air_hz, 2), y, laps=3)
    if ir is not None and wet > 0:
        y = reverb_circular(y, ir, wet=wet, dry=1.0)
    y = circular(lambda s: hp(s, hp_hz, 2), y, laps=3)
    y = y - np.mean(y)
    y = normalize_peak(y, peak_db + 0.3)
    y = circular(lambda s: limiter(s, peak_db), y, laps=3)
    return y


# ==========================================================================
# the sounds
# ==========================================================================
def sfx_fireball_cast():
    rng = np.random.default_rng(101)
    dur = 1.1
    n = ns(dur)
    t = tvec(n)
    y = whoosh(dur, rng, [(0, 350), (0.18, 1800), (0.45, 2600), (dur, 900)],
               [(0, 0), (0.12, 0.9), (0.22, 1.0), (0.6, 0.25), (dur, 0)], res=0.5) * 1.1
    # ignition "fwoomp": opening lowpass on noise
    ig = white(n, rng) * env_points(n, [(0, 0), (0.035, 1), (0.25, 0.45), (0.8, 0)])
    ig = svf(ig, 180 + 4200 * np.clip(t / 0.12, 0, 1) ** 1.5 * np.exp(-np.maximum(t - 0.12, 0) / 0.3), 0.35, "lp")
    y += ig * 1.2
    # low thump
    y += np.sin(phase_from_freq(45 + 70 * np.exp(-t / 0.04))) * env_exp(n, 0.12, 0.003) * 0.9
    # fire bed + sparkly crackle
    fb = fire_bed(n, rng) * env_points(n, [(0, 0), (0.06, 1), (0.4, 0.4), (dur, 0)])
    y += fb * 0.45
    y += crackles(n, rng, rate=110, density=np.exp(-t / 0.35), bright=1.2) * 0.5
    y = saturate(y * 0.8, 1.5)
    return finish(y, -1.0, IR_SMALL, 0.18, tail=1.4)


def sfx_fireball_impact():
    y = explosion(1.6, size=0.65, seed=202, tail_fire=0.9, debris=1.2, bright=1.1)
    rng = np.random.default_rng(203)
    n = y.shape[0]
    t = tvec(n)
    y += crackles(n, rng, rate=90, density=np.exp(-t / 0.6), bright=1.3) * 0.35  # sizzle
    return finish(y, -1.0, IR_SKY, 0.22, tail=2.0)


def sfx_big_explosion():
    y = explosion(4.2, size=1.7, seed=303, tail_fire=0.8, debris=1.6, bright=1.0)
    y2 = explosion(4.2, size=1.1, seed=304, tail_fire=0.4, debris=0.7, bright=0.8)
    out = y.copy()
    mix_at(out, y2, ns(0.14), 0.6)  # secondary blast
    rng = np.random.default_rng(305)
    n = out.shape[0]
    t = tvec(n)
    # long sub pressure wave
    out += np.sin(phase_from_freq(28 + 30 * np.exp(-t / 0.25))) * env_exp(n, 0.9, 0.01) * 0.6
    out = saturate(out * 0.8, 1.6)
    return finish(out, -1.0, IR_VALLEY, 0.3, tail=5.0)


def sfx_vishap_roar():
    rng = np.random.default_rng(404)
    dur = 3.2
    main = glottal_roar(dur, [(0, 48), (0.35, 70), (1.4, 78), (2.3, 60), (dur, 38)], rng,
                        [(0, 0), (0.18, 0.8), (0.6, 1.0), (2.2, 0.9), (3.0, 0.25), (dur, 0)],
                        fscale=0.9, growl=0.7, rasp=0.8, rough=0.4)
    rng2 = np.random.default_rng(405)
    low = glottal_roar(dur, [(0, 26), (0.4, 36), (1.4, 39), (2.3, 30), (dur, 20)], rng2,
                       [(0, 0), (0.25, 0.9), (0.7, 1.0), (2.3, 0.9), (dur, 0)],
                       fscale=0.62, growl=0.9, rasp=0.5, rough=0.5, sub_oct=0.8)
    rng3 = np.random.default_rng(406)
    n = ns(dur)
    # reptilian hiss/screech layer
    hiss = svf(white(n, rng3), env_points(n, [(0, 2400), (1.2, 3400), (dur, 2000)], "log"), 0.6, "bp")
    hiss *= env_points(n, [(0, 0), (0.3, 0.5), (1.3, 0.8), (2.4, 0.4), (dur, 0)])
    y = 0.75 * main + 0.7 * low + 0.18 * hiss
    y = peak_eq(y, 120, 4.0, 0.9)
    y = saturate(y * 1.2, 1.3)
    return finish(y, -1.0, IR_VALLEY, 0.28, tail=4.4)


def sfx_vishap_hit():
    rng = np.random.default_rng(505)
    dur = 0.75
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    # meaty impact
    y += np.sin(phase_from_freq(55 + 110 * np.exp(-t / 0.03))) * env_exp(n, 0.09, 0.001) * 1.0
    slap = bp(white(n, rng), 700, 3500) * env_exp(n, 0.018, 0.0005)
    y += slap * 0.9
    crunch = saturate(bp(white(n, rng), 200, 1500) * env_exp(n, 0.05) * 4, 3)
    y += crunch * 0.35
    # pained yelp-snarl
    yelp = glottal_roar(0.6, [(0, 95), (0.08, 140), (0.3, 110), (0.6, 70)], rng,
                        [(0, 0), (0.04, 1), (0.25, 0.7), (0.6, 0)], fscale=1.05, growl=0.5, rasp=0.9,
                        rough=0.5, sub_oct=0.2, open_pts=[(0, 0.6), (0.1, 1), (0.6, 0.3)])
    mix_at(y, yelp, ns(0.03), 0.8)
    punch = cc0("impactPunch_heavy_000", pitch=0.72)
    if punch is not None:
        mix_at(y, punch, 0, 0.9)
    y += crackles(n, rng, 60, density=np.exp(-t / 0.2)) * 0.25
    return finish(y, -1.0, IR_SKY, 0.15, tail=1.1)


def sfx_vishap_death():
    rng = np.random.default_rng(606)
    dur = 4.4
    n = ns(dur)
    t = tvec(n)
    cry = glottal_roar(3.0, [(0, 60), (0.3, 95), (0.9, 88), (1.8, 55), (3.0, 28)], rng,
                       [(0, 0), (0.12, 1), (1.2, 0.9), (2.4, 0.45), (3.0, 0)], fscale=0.95, growl=0.9,
                       rasp=1.0, rough=0.7, jitter=0.06,
                       open_pts=[(0, 0.4), (0.3, 1.0), (1.5, 0.8), (3.0, 0.1)])
    rng2 = np.random.default_rng(607)
    low = glottal_roar(3.0, [(0, 30), (0.3, 46), (1.5, 30), (3.0, 16)], rng2,
                       [(0, 0), (0.2, 1), (1.5, 0.8), (3.0, 0)], fscale=0.6, growl=1.0, rasp=0.6, rough=0.8)
    y = np.zeros(n)
    mix_at(y, 0.8 * cry + 0.6 * low, 0)
    # gurgling death rattle: AM'd low noise
    gur = bp(white(n, rng), 150, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * (14 - 6 * t / dur) * t)) ** 3
    y += gur * env_points(n, [(0, 0), (1.4, 0), (2.2, 0.5), (3.0, 0.2), (3.4, 0)]) * 0.5
    # body crashes down + fire burst
    crash = explosion(1.8, size=0.8, seed=608, tail_fire=0.7, debris=1.0, bright=0.7)
    mix_at(y, crash, ns(2.55), 0.75)
    y = saturate(y * 1.1, 1.3)
    return finish(y, -1.0, IR_VALLEY, 0.27, tail=5.2)


def sfx_fire_breath():
    """2.0 s seamless loop of a roaring flame jet."""
    rng = np.random.default_rng(707)
    L = ns(2.0)
    jet = spectral_noise(L, rng, -3.0, lo=120, hi=3200)
    turb = smooth_noise(L, 18, rng, periodic=True)
    slow = periodic_lfo(L, rng, 3)
    jet *= np.clip(0.8 + 0.25 * turb + 0.1 * slow, 0.2, 2)
    roar = spectral_noise(L, rng, -6.0, lo=40, hi=500) * np.clip(1 + 0.3 * smooth_noise(L, 7, rng, True), 0.2, 2)
    hiss = spectral_noise(L, rng, 0.0, lo=3000, hi=11000) * np.clip(0.7 + 0.4 * smooth_noise(L, 30, rng, True), 0, 2)
    cr = crackles(L, rng, rate=70, bright=1.1, periodic=True)
    y = 0.9 * jet + 0.9 * roar + 0.18 * hiss + 0.3 * cr
    y = circular(lambda s: peak_eq(s, 700, 4, 0.7), y, 3)
    y = saturate(y / np.std(y) * 0.35, 1.7)
    return finish_loop(y, -2.0, IR_SMALL, 0.2)


def sfx_player_hurt():
    rng = np.random.default_rng(808)
    dur = 0.85
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    y += np.sin(phase_from_freq(48 + 90 * np.exp(-t / 0.035))) * env_exp(n, 0.14, 0.001) * 1.0
    crunch = saturate(bp(white(n, rng), 250, 2800) * env_exp(n, 0.04, 0.0005) * 5, 3.5)
    y += crunch * 0.5
    # muffled concussion: lowpassed noise swell
    y += lp(white(n, rng), 700) * env_points(n, [(0, 0), (0.02, 1), (0.3, 0.2), (dur, 0)]) * 0.6
    # dissonant ring ("ears ringing" hint), short and quiet
    ring = (np.sin(2 * np.pi * 1180 * t) + 0.7 * np.sin(2 * np.pi * 1253 * t)) * env_exp(n, 0.18, 0.01)
    y += ring * 0.06
    # fire sizzle on the armour
    y += hp(crackles(n, rng, 120, density=np.exp(-t / 0.25), bright=1.3), 2000) * 0.35
    punch = cc0("impactPunch_heavy_002", pitch=0.85)
    plate = cc0("impactPlate_heavy_000", pitch=0.9)
    if punch is not None:
        mix_at(y, punch, 0, 1.0)
    if plate is not None:
        mix_at(y, plate, ns(0.004), 0.35)
    y = saturate(y, 1.4)
    return finish(y, -1.0, IR_SMALL, 0.15, tail=1.0)


def sfx_boost():
    rng = np.random.default_rng(909)
    dur = 1.6
    n = ns(dur)
    t = tvec(n)
    y = whoosh(dur, rng, [(0, 250), (0.25, 1400), (0.7, 2600), (dur, 1200)],
               [(0, 0), (0.08, 0.8), (0.3, 1.0), (0.9, 0.5), (dur, 0)], res=0.45)
    y += 0.6 * whoosh(dur, rng, [(0, 120), (0.3, 500), (dur, 300)],
                      [(0, 0), (0.1, 1), (0.6, 0.6), (dur, 0)], res=0.3)
    # wind buffeting (low AM rumble)
    buff = lp(white(n, rng), 300) * (1 + 0.8 * smooth_noise(n, 14, rng)) * env_points(n, [(0, 0), (0.1, 1), (dur, 0)])
    y += buff * 0.5
    # flame flare ignition
    y += fire_bed(n, rng) * env_points(n, [(0, 0), (0.05, 0.6), (0.4, 0.2), (dur, 0)]) * 0.35
    y += np.sin(phase_from_freq(40 + 50 * np.exp(-t / 0.06))) * env_exp(n, 0.2, 0.01) * 0.6
    y = saturate(y, 1.3)
    return finish(y, -1.0, IR_SKY, 0.15, tail=2.0)


def sfx_wind_loop():
    """8 s seamless high-altitude wind (all components exactly periodic)."""
    rng = np.random.default_rng(1001)
    L = ns(8.0)
    y = np.zeros(L)
    # broadband gusts
    for lo, hi, g in [(60, 300, 0.9), (250, 900, 0.6), (800, 2500, 0.25), (2500, 7000, 0.07)]:
        band = spectral_noise(L, rng, -3.0, lo=lo, hi=hi)
        am = 0.55 + 0.45 * periodic_lfo(L, rng, 5, cycles_min=1)
        am *= 1 + 0.15 * spectral_noise(L, rng, 0.0, hi=6.0)
        y += g * band * np.clip(am, 0.05, 2)
    # moving whistles: narrow bands with independent periodic swells
    for fc in (520, 610, 700, 820, 950, 1100):
        nb = spectral_noise(L, rng, 0.0, lo=fc * 0.97, hi=fc * 1.03)
        sw = np.clip(periodic_lfo(L, rng, 3, cycles_min=1), 0, 1) ** 2
        y += 0.09 * nb * sw
    return finish_loop(y, -3.0, IR_SKY, 0.12)


def sfx_flame_aura_loop():
    """6 s seamless crackling fire around Vahagn."""
    rng = np.random.default_rng(1101)
    L = ns(6.0)
    bed = fire_bed(L, rng, periodic=True, flicker_rate=7, body=0.6, hiss=0.15, low_hz=700)
    cr = crackles(L, rng, rate=55, bright=1.0, pops=0.2, periodic=True)
    cr2 = crackles(L, rng, rate=25, bright=0.7, pops=0.35, periodic=True)
    y = 0.6 * bed + 0.9 * cr + 0.6 * cr2
    y = circular(lambda s: shelf(s, 150, -4, high=False), y, 3)
    return finish_loop(y, -4.0, IR_SMALL, 0.12)


def sfx_ui_click():
    rng = np.random.default_rng(1201)
    dur = 0.12
    n = ns(dur)
    t = tvec(n)
    y = np.sin(2 * np.pi * 1650 * t + 0.4 * np.sin(2 * np.pi * 3300 * t)) * env_exp(n, 0.012, 0.0004)
    y += 0.6 * np.sin(2 * np.pi * 420 * t) * env_exp(n, 0.02, 0.0005)
    y += 0.5 * bp(white(n, rng), 3000, 9000) * env_exp(n, 0.0025)
    y += 0.25 * np.sin(2 * np.pi * 2475 * t) * env_exp(n, 0.03, 0.001)  # soft metallic tail (fire-forged)
    clk = cc0("click_001")
    if clk is not None:
        y = 0.45 * y
        mix_at(y, clk, 0, 1.0)
    return finish(y, -6.0, IR_SMALL, 0.06, tail=0.2, hp_hz=120, fade_out=0.01)


def sfx_ui_hover():
    rng = np.random.default_rng(1301)
    dur = 0.09
    n = ns(dur)
    t = tvec(n)
    f = 2400 + 600 * (1 - np.exp(-t / 0.02))
    y = np.sin(phase_from_freq(f)) * env_points(n, [(0, 0), (0.004, 1), (0.08, 0)]) ** 2
    y += 0.25 * bp(white(n, rng), 4000, 10000) * env_exp(n, 0.01, 0.002)
    return finish(y, -12.0, IR_SMALL, 0.08, tail=0.14, hp_hz=300, fade_out=0.01)


def sfx_wave_start():
    rng = np.random.default_rng(1401)
    dur = 3.6
    n = ns(dur)
    y = np.zeros(n)
    # two-horn call: low D, then rising to A (a fifth) - karnay / war-horn style
    h1 = horn(1.6, 38, rng, scoop=-2.0, amp_pts=[(0, 0), (0.1, 0.8), (0.3, 1), (1.3, 0.9), (1.6, 0)])
    h2 = horn(2.0, 45, rng, scoop=-1.0, amp_pts=[(0, 0), (0.1, 0.8), (0.3, 1), (1.5, 0.85), (2.0, 0)])
    h_oct = horn(2.0, 33, rng, scoop=-1.0, rasp=0.5, amp_pts=[(0, 0), (0.15, 0.7), (1.4, 0.7), (2.0, 0)])
    mix_at(y, h1, 0, 0.8)
    mix_at(y, h2, ns(1.45), 0.8)
    mix_at(y, h_oct, ns(1.45), 0.45)
    # war drums
    for tm, g in [(0.0, 1.0), (1.45, 1.0), (1.45 + 0.375, 0.6), (1.45 + 0.75, 0.75)]:
        mix_at(y, drum_hit(1.0, 150, 50, 0.4, 0.6, seed=int(tm * 100)), ns(tm), g)
    y = saturate(y * 0.8, 1.2)
    y = delay_echo(y, 0.42, fb=0.35, wet=0.22, lp_hz=2200, taps=3)  # mountain echo
    return finish(y, -1.0, IR_VALLEY, 0.3, tail=5.5)


def sfx_victory():
    rng = np.random.default_rng(1501)
    dur = 5.0
    n = ns(dur)
    y = np.zeros(n)
    # drum roll into big hit
    for i, tm in enumerate(np.arange(0, 0.5, 0.0625)):
        mix_at(y, drum_hit(0.4, 320, 180, 0.08, 0.7, seed=i, modes=(1, 1.5, 2.1)), ns(tm), 0.25 + 0.06 * i)
    mix_at(y, drum_hit(1.5, 140, 45, 0.6, 0.6, seed=99), ns(0.55), 1.2)
    # ascending horn fanfare D major (D Hijaz has F#): D3 A3 D4 F#4 -> A4
    for i, (tm, m, d) in enumerate([(0.55, 50, 1.0), (0.8, 57, 0.9), (1.05, 62, 0.8), (1.3, 66, 3.4)]):
        mix_at(y, horn(d, m, rng, scoop=-0.6, vib=0.15, rasp=0.15,
                       amp_pts=[(0, 0), (0.05, 1), (d - 0.4, 0.8), (d, 0)]), ns(tm), 0.35)
    # reed flourish (zurna-like) climbing to D5 with trill
    pts = [(0, 69), (0.12, 69), (0.14, 71), (0.26, 71), (0.28, 73), (0.4, 73), (0.42, 74), (0.9, 74),
           (0.95, 76), (1.0, 74), (1.05, 76), (1.1, 74), (1.15, 76), (1.2, 74), (2.4, 74)]
    mix_at(y, reedy(2.4, pts, rng, bright=1.3, formant=1700, amp_pts=[(0, 0), (0.04, 0.8), (1.0, 1), (2.0, 0.7), (2.4, 0)]),
           ns(1.3), 0.4)
    mix_at(y, choir(3.6, [50, 57, 62, 66, 69], rng, "ah", [(0, 0), (0.5, 1), (2.6, 0.8), (3.6, 0)]), ns(1.05), 0.45)
    # cymbal swell+crash
    cym = bp(white(n, rng), 3500, 9000) + 0.3 * sum(np.sin(2 * np.pi * f * tvec(n)) for f in (3420, 4710, 5930, 7340))
    cym = cym * env_points(n, [(0, 0), (0.5, 0.3), (0.56, 1), (1.5, 0.35), (dur, 0)]) ** 1.5 * 0.08
    y += cym
    y = saturate(y * 0.7, 1.2)
    return finish(y, -1.0, IR_VALLEY, 0.3, tail=6.0)


def sfx_defeat():
    rng = np.random.default_rng(1601)
    dur = 5.5
    n = ns(dur)
    y = np.zeros(n)
    mix_at(y, drum_hit(2.0, 110, 38, 0.9, 0.4, seed=7), 0, 1.0)
    mix_at(y, drum_hit(2.0, 100, 34, 0.9, 0.3, seed=8), ns(1.2), 0.7)
    # mournful duduk: A4 Bb4 A4 G4 F4 E4 D4 with slides
    pts = [(0, 69), (0.35, 69), (0.42, 70), (0.8, 70), (0.88, 69), (1.4, 69), (1.5, 67), (1.9, 67),
           (2.0, 65), (2.5, 65), (2.6, 64), (3.0, 64), (3.2, 62), (4.6, 62)]
    mix_at(y, reedy(4.6, pts, rng, bright=0.8, vib_depth=0.28, formant=1100,
                    amp_pts=[(0, 0), (0.1, 0.9), (3.0, 0.8), (4.0, 0.6), (4.6, 0)]), ns(0.1), 0.55)
    mix_at(y, choir(5.0, [38, 45, 50, 53], rng, "oo", [(0, 0), (1.0, 1), (3.5, 0.7), (5.0, 0)]), 0, 0.4)
    y += np.sin(2 * np.pi * mtof(38) * tvec(n)) * env_points(n, [(0, 0), (0.5, 0.25), (4.5, 0.2), (dur, 0)])
    y = saturate(y * 0.8, 1.2)
    return finish(y, -1.0, IR_VALLEY, 0.35, tail=6.5)


def sfx_special_nova():
    rng = np.random.default_rng(1701)
    dur = 4.4
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    ch = 0.75  # charge time
    # charge: rising filtered noise + rising tone with accelerating tremolo
    nc = ns(ch)
    tc = tvec(nc)
    riser = svf(pink(nc, rng), 300 * (12000 / 300) ** (tc / ch), 0.6, "bp") * (tc / ch) ** 1.5
    tone = np.sin(phase_from_freq(180 * (8) ** (tc / ch))) * (tc / ch) ** 2
    trem = 0.5 + 0.5 * np.sin(phase_from_freq(6 + 40 * (tc / ch) ** 2))
    charge = riser * 0.9 + tone * 0.25 * trem
    charge += crackles(nc, rng, 260, density=(tc / ch) ** 2, bright=1.3) * 0.5
    mix_at(y, charge, 0, 1.0)
    # the nova: big fiery blast
    blast = explosion(dur - ch, size=1.4, seed=1702, tail_fire=1.5, debris=1.3, bright=1.2)
    mix_at(y, blast, nc, 1.1)
    # expanding fire ring whoosh
    ring = whoosh(2.5, rng, [(0, 3000), (0.3, 1500), (2.5, 400)], [(0, 1), (0.4, 0.6), (2.5, 0)], res=0.4)
    mix_at(y, ring, nc, 0.6)
    # shimmer
    sh = bp(white(n, rng), 6000, 12000) * env_points(n, [(0, 0), (ch, 0), (ch + 0.02, 1), (dur, 0)]) ** 2
    y += sh * 0.2
    y += np.sin(phase_from_freq(22 + 60 * np.exp(-np.maximum(t - ch, 0) / 0.12))) * \
        env_points(n, [(0, 0), (ch, 0), (ch + 0.01, 1), (dur, 0)]) ** 2 * 0.8
    y = saturate(y * 0.8, 1.5)
    return finish(y, -1.0, IR_VALLEY, 0.28, tail=5.4)


ALL = [
    sfx_fireball_cast, sfx_fireball_impact, sfx_big_explosion, sfx_vishap_roar, sfx_vishap_hit,
    sfx_vishap_death, sfx_fire_breath, sfx_player_hurt, sfx_boost, sfx_wind_loop, sfx_flame_aura_loop,
    sfx_ui_click, sfx_ui_hover, sfx_wave_start, sfx_victory, sfx_defeat, sfx_special_nova,
]


def main(argv):
    OUT.mkdir(parents=True, exist_ok=True)
    sel = argv[1:]
    for i, fn in enumerate(ALL):
        name = fn.__name__
        if sel and not any(s in name for s in sel):
            continue
        y = fn()
        assert np.all(np.isfinite(y)), name
        path = OUT / f"{name}.wav"
        write_wav(path, y, seed=i)
        print(f"{name:24s} {y.shape[-1] / SR:6.2f}s  peak {20 * np.log10(np.max(np.abs(y))):6.2f} dBFS  "
              f"LUFS {lufs(y):6.1f}")


if __name__ == "__main__":
    main(sys.argv)
