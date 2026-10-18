#!/usr/bin/env python3
"""
gen_music.py - procedural Armenian-flavoured loops for "Vahagn: Vishapakagh".

  music_menu.wav    72 s  80 BPM  calm, mystical (duduk over dam drone, choir, kanun)
  music_battle.wav  80 s  120 BPM driving (dhol groove, low-string ostinato, duduk/zurna lead)
  music_boss.wav    60 s  128 BPM intense (taiko + dhol, brass braams, zurna, choir)

Mode: D Phrygian dominant ("Hijaz"): D Eb F# G A Bb C.
Every track is rendered into a ring buffer of exactly the loop length; note
tails and the reverb wrap around, so the loop is seamless by construction.
48 kHz / 16-bit / stereo, ~-14 LUFS integrated, peak <= -1 dBFS.
Run: python3 gen_music.py [menu|battle|boss ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from dsp import (SR, ns, tvec, fit, ring_add, env_exp, env_points, spectral_noise, white, pink, brown,
                 smooth_noise, periodic_lfo, lp, hp, bp, peak_eq, shelf, svf, circular, saturate,
                 compress, additive, phase_from_freq, make_ir, reverb_circular, lufs, master_loudness,
                 remove_dc, mtof, pan, widen, write_wav, njit, undb)

OUT = Path(__file__).resolve().parent.parent / "music"

# D Hijaz scale degrees (midi, octave 4)
D4, Eb4, Fs4, G4, A4, Bb4, C5, D5, Eb5 = 62, 63, 66, 67, 69, 70, 72, 74, 75
SCALE = [0, 1, 4, 5, 7, 8, 10]  # semitones from D


def scale_up(m):
    """Next scale tone above midi m (for grace notes / trills)."""
    pc = (m - 62) % 12
    for s in SCALE + [12]:
        if s > pc:
            return m + (s - pc)
    return m + 1


# ==========================================================================
# instruments
# ==========================================================================
class Track:
    def __init__(self, bpm, bars, beats_per_bar=4, seed=0):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.L = ns(bars * beats_per_bar * self.beat)
        self.bars = bars
        self.bpb = beats_per_bar
        self.stems = {}
        self.sends = {}
        self.rng = np.random.default_rng(seed)

    def stem(self, name, send=0.2):
        if name not in self.stems:
            self.stems[name] = np.zeros((2, self.L))
            self.sends[name] = send
        return self.stems[name]

    def s(self, beat):  # beat -> sample index
        return int(round(beat * self.beat * SR))

    def add(self, name, x, beat, gain=1.0, p=0.0, send=0.2, jitter_ms=0.0):
        st = self.stem(name, send)
        if x.ndim == 1:
            x = pan(x, p)
        off = self.s(beat)
        if jitter_ms:
            off += int(self.rng.normal(0, jitter_ms) * SR / 1000)
        ring_add(st, x, off, gain)


# ---------------------------------------------------------------- reeds
def reed_phrase(notes, beat_s, rng, kind="duduk", rel=0.35):
    """Continuous legato reed line.  notes: [(beat, dur, midi, flags)], beats
    relative to the phrase start.  flags: 'g' grace, 'm' mordent, 't' trill,
    'a' accent.  Returns mono array starting at notes[0] beat."""
    notes = [(b, d, m, (f[0] if f else "")) for (b, d, m, *f) in notes]
    b0 = notes[0][0]
    starts = np.array([(b - b0) * beat_s for b, _, _, _ in notes])
    ends = np.array([(b - b0 + d) * beat_s for b, d, _, _ in notes])
    total = ends[-1] + rel
    n = ns(total)
    t = tvec(n)
    # ---- pitch breakpoints with portamento / ornaments
    pts_t, pts_m = [], []
    glide = 0.055 if kind == "duduk" else 0.035
    for i, (b, d, m, fl) in enumerate(notes):
        s0 = starts[i]
        if i == 0:
            pts_t.append(0.0)
            pts_m.append(m - (0.6 if kind == "duduk" else 0.3))  # gentle scoop into first note
            pts_t.append(0.07)
            pts_m.append(m)
        else:
            pts_t.append(s0 - glide * 0.4)
            pts_m.append(notes[i - 1][2])
        if "g" in fl and i > 0:
            u = scale_up(m)
            pts_t += [s0 + 0.005, s0 + 0.06, s0 + 0.085]
            pts_m += [u, u, m]
        elif "m" in fl:
            u = scale_up(m)
            pts_t += [s0 + glide * 0.6, s0 + 0.07, s0 + 0.09, s0 + 0.15, s0 + 0.17]
            pts_m += [m, m, u, u, m]
        else:
            pts_t.append(s0 + glide * 0.6)
            pts_m.append(m)
        if "t" in fl:
            dur = ends[i] - s0
            tt = s0 + 0.4 * dur
            u = scale_up(m)
            k = 0
            while tt < ends[i] - 0.12:
                pts_t += [tt, tt + 0.018]
                v = u if k % 2 == 0 else m
                pts_m += [pts_m[-1], v]
                tt += 1 / 13.0
                k += 1
            pts_t.append(ends[i] - 0.06)
            pts_m.append(m)
    pts_t.append(total)
    pts_m.append(notes[-1][2] - (0.4 if kind == "duduk" else 0.2))  # slight fall-off at release
    order = np.argsort(np.array(pts_t), kind="stable")
    pt = np.maximum.accumulate(np.array(pts_t)[order])
    midi = np.interp(t, pt, np.array(pts_m)[order])
    # ---- vibrato (delayed per note) + drift
    idx = np.clip(np.searchsorted(starts, t, side="right") - 1, 0, len(notes) - 1)
    since = t - starts[idx]
    ndur = (ends - starts)[idx]
    depth = (0.22 if kind == "duduk" else 0.28) * np.clip((since - 0.18) / 0.45, 0, 1) * np.clip(ndur / 0.6, 0, 1)
    rate = 5.3 + 0.4 * smooth_noise(n, 0.5, rng)
    vib = depth * np.sin(phase_from_freq(rate))
    midi = midi + vib + 0.04 * smooth_noise(n, 2.0, rng)
    f = mtof(midi)
    # ---- dynamics
    amp = env_points(n, [(0, 0), (0.07, 0.85), (ends[-1] - 0.02, 0.85), (total, 0)])
    acc = np.zeros(n)
    for i, (b, d, m, fl) in enumerate(notes):
        s0 = starts[i]
        dur = ends[i] - s0
        k = (t >= s0) & (t < ends[i] + 0.1)
        tl = t[k] - s0
        a = 0.12 + (0.2 if "a" in fl else 0.0)
        acc[k] += a * np.exp(-tl / 0.09)
        if dur > 0.9:  # swell on long notes
            acc[k] += 0.18 * np.sin(np.pi * np.clip(tl / dur, 0, 1)) - 0.06
        if i > 0 and notes[i - 1][2] == m:  # re-articulate repeated notes
            acc[k] -= 0.55 * np.exp(-((tl - 0.01) / 0.025) ** 2)
    amp = np.clip(amp * (1 + acc), 0, 1.4)
    # ---- timbre
    if kind == "duduk":
        def w(kk, fk):
            odd = 1.0 if kk % 2 else 0.55
            fm = 1 + 1.8 * np.exp(-0.5 * (np.log2(fk / 1150) / 0.5) ** 2)
            return odd * fm / kk ** 1.15
        cutoff = 900 + 2600 * amp
        breath = 0.045
        blo, bhi = 1200, 4500
    else:  # zurna: shrill, nasal double reed
        def w(kk, fk):
            fm = 1 + 2.5 * np.exp(-0.5 * (np.log2(fk / 2300) / 0.45) ** 2) + \
                1.0 * np.exp(-0.5 * (np.log2(fk / 1100) / 0.4) ** 2)
            return fm / kk ** 0.75
        cutoff = 1800 + 5000 * amp
        breath = 0.03
        blo, bhi = 2500, 7000
    y = additive(f, w, rng, fmax=11000, bright=cutoff)
    y /= np.max(np.abs(y)) + 1e-9
    nz = bp(white(n, rng), blo, bhi) * (0.35 + amp) * breath
    chiff = bp(white(n, rng), 800, 3000) * np.exp(-t / 0.05) * 0.15
    y = (y + nz) * amp + chiff * (amp > 0.01)
    if kind == "zurna":
        y = saturate(y * 1.4, 1.3)
    return y


def phrases_from_notes(notes):
    """Split a note list into legato phrases at rests."""
    out, cur = [], []
    for nt in sorted(notes, key=lambda x: x[0]):
        if cur and nt[0] > cur[-1][0] + cur[-1][1] + 1e-6:
            out.append(cur)
            cur = []
        cur.append(nt)
    if cur:
        out.append(cur)
    return out


def add_reed(tr, name, notes, offset_beat, kind="duduk", gain=1.0, p=0.0, send=0.35, transpose=0):
    for ph in phrases_from_notes(notes):
        ph = [(b, d, m + transpose, *rest) for (b, d, m, *rest) in ph]
        y = reed_phrase(ph, tr.beat, tr.rng, kind)
        tr.add(name, y, offset_beat + ph[0][0], gain, p, send)


# ---------------------------------------------------------------- drone
def drone(L, midis, rng, cutoff=1400.0, breathe=0.25):
    """Exactly periodic dam (drone duduk) for a loop of L samples."""
    dur = L / SR
    t = np.arange(L) / SR
    out = np.zeros(L)
    for j, m in enumerate(midis):
        for dc in (0.0, 0.11):  # two players, slow beating (periodic)
            f = round((mtof(m) + dc) * dur) / dur  # integer cycles per loop
            for k in range(1, int(cutoff * 2.5 // f) + 1):
                fk = k * f
                wgt = (1.0 if k % 2 else 0.6) / k ** 1.1 / (1 + (fk / cutoff) ** 2)
                wgt *= 1 + 1.2 * np.exp(-0.5 * (np.log2(fk / 900) / 0.5) ** 2)
                out += wgt * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    out /= np.max(np.abs(out)) + 1e-9
    am = 1 + breathe * periodic_lfo(L, rng, 4, cycles_min=2)
    nz = spectral_noise(L, rng, 0.0, lo=900, hi=3500) * 0.02
    return out * am + nz


# ---------------------------------------------------------------- choir
VOWELS = {"ah": ([730, 1090, 2440], [1.0, 0.55, 0.3]), "oh": ([570, 840, 2410], [1.0, 0.5, 0.22]),
          "oo": ([320, 800, 2240], [1.0, 0.3, 0.12]), "eh": ([530, 1840, 2480], [1.0, 0.5, 0.3])}


def choir(dur, midis, rng, vowel="ah", att=0.8, rel=1.2, voices=2, spread=0.8):
    n = ns(dur + rel)
    t = tvec(n)
    out = np.zeros((2, n))
    F, G = VOWELS[vowel]
    for m in midis:
        for v in range(voices):
            f = mtof(m) * 2 ** (rng.uniform(-9, 9) / 1200)
            vr = rng.uniform(4.5, 5.6)
            fr = f * 2 ** ((0.13 * np.sin(2 * np.pi * vr * t + rng.uniform(0, 6)) +
                            0.03 * smooth_noise(n, 1.5, rng)) / 12)

            def w(k, fk):
                e = 0.06
                for c, g in zip(F, G):
                    e += g * np.exp(-0.5 * (np.log2(fk / c) / 0.2) ** 2)
                return e / k ** 0.5
            y = additive(fr, w, rng, fmax=7000)
            y += 0.04 * bp(white(n, rng), 500, 3000)
            out += pan(y, rng.uniform(-spread, spread))
    out /= np.max(np.abs(out)) + 1e-9
    env = env_points(n, [(0, 0), (att, 1), (dur, 0.9), (dur + rel, 0)])
    return out * env


# ---------------------------------------------------------------- kanun (Karplus-Strong)
@njit(cache=True)
def _ks(exc, n, P, decay, damp):
    N = int(P - 0.5)
    frac = P - N - 0.5
    if frac < 0.1:
        N -= 1
        frac += 1.0
    C = (1 - frac) / (1 + frac)
    buf = np.zeros(n + N + 2)
    y = np.zeros(n)
    ap_x1 = 0.0
    ap_y1 = 0.0
    for i in range(n):
        j = i + N + 1
        a = buf[j - N - 1] if j - N - 1 >= 0 else 0.0
        b = buf[j - N - 2] if j - N - 2 >= 0 else 0.0
        lpv = decay * ((1 - damp) * a + damp * b)
        # first order allpass for fractional tuning
        ap = C * lpv + ap_x1 - C * ap_y1
        ap_x1 = lpv
        ap_y1 = ap
        v = ap + (exc[i] if i < exc.shape[0] else 0.0)
        buf[j] = v
        y[i] = v
    return y


def kanun(midi, rng, dur=2.5, vel=1.0):
    n = ns(dur)
    f = float(mtof(midi))
    P = SR / f
    L = int(P)
    exc = rng.uniform(-1, 1, L)
    exc = lp(exc, 2000 + 6000 * vel, 1)
    pos = rng.uniform(0.12, 0.2)  # pluck position comb
    d = max(int(pos * L), 1)
    exc = exc - np.concatenate([np.zeros(d), exc[:-d]])
    decay = 0.9985 if f < 300 else 0.997
    y = _ks(exc.astype(np.float64), n, P, decay, 0.5)
    y = peak_eq(y, 260, 3, 1.0)
    y = peak_eq(y, 1800, 2, 1.2)
    y *= env_points(n, [(0, 1), (dur - 0.1, 1), (dur, 0)])
    return y / (np.max(np.abs(y)) + 1e-9) * vel


# ---------------------------------------------------------------- drums
def dhol_dum(rng, vel=1.0):
    n = ns(0.9)
    t = tvec(n)
    f0 = rng.uniform(52, 58)
    f = f0 + 85 * np.exp(-t / 0.025)
    ph = phase_from_freq(f)
    y = np.sin(ph) * env_exp(n, 0.32, 0.001)
    y += 0.3 * np.sin(ph * 1.59) * env_exp(n, 0.09)
    y += 0.12 * np.sin(ph * 2.14) * env_exp(n, 0.05)
    y += lp(white(n, rng), 1800) * env_exp(n, 0.012) * 0.5
    y += bp(white(n, rng), 90, 400) * env_exp(n, 0.06) * 0.35  # skin slap body
    y = saturate(y * (1.2 + 0.6 * vel), 1.5)
    return y * vel


def dhol_tak(rng, vel=1.0):
    n = ns(0.35)
    t = tvec(n)
    f0 = rng.uniform(340, 380)
    y = np.zeros(n)
    for m, g, d in [(1.0, 1.0, 0.06), (1.59, 0.5, 0.04), (2.14, 0.35, 0.03), (2.65, 0.2, 0.02)]:
        y += g * np.sin(2 * np.pi * f0 * m * t * (1 + 0.04 * np.exp(-t / 0.01)) + rng.uniform(0, 6)) * env_exp(n, d)
    y += bp(white(n, rng), 1500, 7000) * env_exp(n, 0.012, 0.0003) * 0.9  # stick snap
    y = saturate(y * 1.2, 1.3)
    return y * vel


def daf(rng, vel=1.0, jingle=1.0):
    """Frame drum with jingles (tambourine-ish)."""
    n = ns(0.4)
    t = tvec(n)
    y = np.sin(2 * np.pi * rng.uniform(150, 175) * t) * env_exp(n, 0.05, 0.001) * 0.4
    jl = np.zeros(n)
    for _ in range(4):
        st = ns(rng.uniform(0, 0.012))
        part = sum(np.sin(2 * np.pi * rng.uniform(4500, 9500) * tvec(n - st) + rng.uniform(0, 6)) for _ in range(3))
        part = part * env_exp(n - st, rng.uniform(0.03, 0.07))
        jl[st:] += part
    jl += hp(white(n, rng), 6000) * env_exp(n, 0.04) * 2
    y += jingle * 0.12 * jl
    return y * vel


def taiko(rng, vel=1.0):
    n = ns(1.8)
    t = tvec(n)
    f = 42 + 60 * np.exp(-t / 0.04)
    ph = phase_from_freq(f)
    y = np.sin(ph) * env_exp(n, 0.65, 0.002) + 0.3 * np.sin(ph * 1.5) * env_exp(n, 0.2)
    y += bp(white(n, rng), 60, 600) * env_exp(n, 0.12) * 0.6
    y += lp(white(n, rng), 3000) * env_exp(n, 0.01) * 0.4
    return saturate(y * 1.6, 1.6) * vel


def cymbal_swell(dur, rng):
    n = ns(dur)
    t = tvec(n)
    y = bp(white(n, rng), 3000, 11000)
    y += 0.4 * sum(np.sin(2 * np.pi * f * t) for f in (3311, 4473, 5639, 6871, 8123)) * 0.25
    return y * (t / dur) ** 3 * 0.25


def riser(dur, rng):
    n = ns(dur)
    t = tvec(n)
    y = svf(pink(n, rng), 300 * (9000 / 300) ** (t / dur), 0.55, "bp")
    return y * (t / dur) ** 2


# ---------------------------------------------------------------- low strings / brass
def string_note(dur, midi, rng, vel=1.0, voices=3, cut=2600.0):
    n = ns(dur + 0.25)
    t = tvec(n)
    out = np.zeros(n)
    for v in range(voices):
        f = mtof(midi) * 2 ** (rng.uniform(-8, 8) / 1200) * np.ones(n)
        c = 250 + cut * vel * np.exp(-t / 0.12) + 300
        out += additive(f, lambda k, fk: 1.0 / k, rng, fmax=8000, bright=c)
    out /= voices
    env = env_points(n, [(0, 0), (0.004, 1), (dur * 0.6, 0.55), (dur, 0.35), (dur + 0.25, 0)])
    return out * env * vel


def braam(dur, midis, rng):
    """Low brass cluster hit (stereo)."""
    n = ns(dur)
    t = tvec(n)
    out = np.zeros((2, n))
    bright = env_points(n, [(0, 300), (0.12, 2400), (0.6, 1200), (dur, 400)], "log")
    for i, m in enumerate(midis):
        for v in range(2):
            f = mtof(m) * 2 ** (rng.uniform(-7, 7) / 1200) * 2 ** (env_points(n, [(0, -0.6), (0.1, 0), (dur, 0)]) / 12)
            y = additive(f, lambda k, fk: (1 / k ** 0.5) * (1 + np.exp(-0.5 * (np.log2(fk / 1000) / 0.6) ** 2)),
                         rng, fmax=7000, bright=bright)
            out += pan(y, (-0.5 + v) * 0.8)
    out /= np.max(np.abs(out)) + 1e-9
    out = saturate(out * 1.8, 1.5)
    return out * env_points(n, [(0, 0), (0.03, 1), (0.4, 0.7), (dur - 0.3, 0.5), (dur, 0)])


def wind_bed(L, rng):
    y = np.zeros(L)
    for lo, hi, g in [(80, 400, 0.6), (300, 1200, 0.35), (1000, 3000, 0.1)]:
        b = spectral_noise(L, rng, -3.0, lo=lo, hi=hi)
        y += g * b * np.clip(0.6 + 0.4 * periodic_lfo(L, rng, 4), 0.05, 2)
    return y


# ==========================================================================
# mixing / mastering
# ==========================================================================
def mixdown(tr, targets, ir, verb_wet=0.35, comp=True, verbose=True):
    """targets: stem -> loudness (LUFS, gated so sparse stems are judged while
    playing) relative to the mix reference.  Stems are auto-gained to these
    targets, which keeps the balance stable whatever the synthesis level."""
    dry = np.zeros((2, tr.L))
    send = np.zeros((2, tr.L))
    for name, st in tr.stems.items():
        g = undb(targets.get(name, -20.0) - 0.0 - lufs(st))
        if verbose:
            print(f"    stem {name:8s} target {targets.get(name, -20.0):6.1f} LUFS  gain {20 * np.log10(g):+6.1f} dB")
        dry += g * st
        send += g * tr.sends[name] * st
    wet = reverb_circular(send, ir, wet=1.0, dry=0.0)
    mix = dry + verb_wet * wet
    mix = remove_dc(mix, loop=True)
    # master EQ: tame sub (inaudible on laptop speakers, eats headroom), add a little presence
    mix = circular(lambda s: peak_eq(shelf(s, 85, -3.0, high=False), 3000, 1.5, 0.8), mix, laps=3)
    if comp:
        mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.7
        mix = circular(lambda s: compress(s, thresh_db=-14, ratio=2.0, attack=0.02, release=0.25), mix, laps=3)
    mix = saturate(mix / (np.max(np.abs(mix)) + 1e-9) * 1.1, 1.15)
    mix = master_loudness(mix, -14.0, -1.0, loop=True)
    return mix


def report(name, mix):
    pk = 20 * np.log10(np.max(np.abs(mix)))
    print(f"{name:18s} {mix.shape[-1] / SR:6.2f}s  peak {pk:6.2f} dBFS  LUFS {lufs(mix):6.2f}")


# ==========================================================================
# MENU  (80 BPM, 24 bars = 72 s)
# ==========================================================================
CH = {  # chord voicings (midi)
    "D": [50, 57, 62, 66], "D5": [50, 57, 62, 69], "Eb": [51, 58, 63, 67], "Cm": [48, 55, 60, 63],
    "Gm": [55, 58, 62, 67], "Bb": [46, 53, 58, 62], "A": [45, 52, 57, 61], "Dm": [50, 57, 62, 65],
}

MENU_A = [(0, 1.5, 69), (1.5, .5, 70), (2, 1, 69), (3, 1, 67), (4, 2, 66, "g"), (6, 1, 67), (7, 4, 69),
          (12, 1, 69), (13, 1, 72, "g"), (14, .5, 70), (14.5, .5, 69), (15, 1, 67), (16, 1, 66), (17, .5, 67),
          (17.5, .5, 66), (18, 1, 63), (19, 5, 62),
          (25, .5, 62), (25.5, .5, 63), (26, 1, 66), (27, 1, 67), (28, 3.5, 69, "t")]
MENU_B = [(0, 2, 74, "g"), (2, 1, 72), (3, 1, 70), (4, 2, 69), (6, .5, 70), (6.5, .5, 69), (7, 1, 67), (8, 4, 69),
          (13, .5, 69), (13.5, .5, 70), (14, 1, 72), (15, 1, 74), (16, 1.5, 75, "m"), (17.5, .5, 74), (18, 1, 72),
          (19, 1, 70), (20, 3, 69), (23, .5, 67), (23.5, .5, 66), (24, 1, 67), (25, 1, 66), (26, 1, 63),
          (27, 4.5, 62)]


def make_menu():
    tr = Track(80, 24, seed=2024)
    rng = tr.rng
    L = tr.L
    # drone D2 + A2 + D3 (dam)
    st = tr.stem("drone", 0.25)
    dr = drone(L, [38, 45, 50], rng, cutoff=1100, breathe=0.2)
    st += np.stack([dr, dr]) * 0.7
    wb = wind_bed(L, rng)
    tr.stem("wind", 0.1)[:] += np.stack([wb, np.roll(wb, ns(0.37))]) * 0.5
    # choir pad, 2 bars per chord
    prog = ["D5", "D5", "Eb", "D", "Cm", "D", "Gm", "Eb", "D", "Cm", "Eb", "D"]
    for i, c in enumerate(prog):
        vowel = "oo" if i < 2 or i >= 10 else ("ah" if i in (4, 5, 6, 7) else "oh")
        tr.add("choir", choir(8 * tr.beat + 0.4, CH[c], rng, vowel, att=1.6, rel=2.0), i * 8, 1.0, send=0.5)
    # kanun arpeggios (bars 5-22)
    for i, c in enumerate(prog):
        if not (2 <= i <= 10):
            continue
        tones = sorted(set([m + 12 for m in CH[c][1:]] + [CH[c][2] + 24]))
        for e in range(16):  # eighth notes
            if rng.random() < (0.55 if e % 2 == 0 else 0.3):
                m = tones[(e * 2 + rng.integers(0, 2)) % len(tones)]
                v = rng.uniform(0.35, 0.6) * (1.0 if e % 4 == 0 else 0.75)
                tr.add("kanun", kanun(m, rng, 2.2, v), i * 8 + e * 0.5, 1.0, rng.uniform(-0.6, 0.6), 0.45,
                       jitter_ms=6)
    # duduk melodies
    add_reed(tr, "duduk", MENU_A, 16, "duduk", 1.0, -0.1, 0.45)
    add_reed(tr, "duduk", MENU_B, 56, "duduk", 1.0, -0.1, 0.45)
    # soft frame-drum heartbeat (bars 9-22)
    for bar in range(8, 22):
        b = bar * 4
        tr.add("drums", dhol_dum(rng, 0.55), b, 1.0, 0.0, 0.3, 3)
        tr.add("drums", dhol_dum(rng, 0.35), b + 1.5, 1.0, 0.0, 0.3, 3)
        if bar % 2 == 1:
            tr.add("drums", daf(rng, 0.35, 0.6), b + 3, 1.0, 0.3, 0.3, 3)
    ir = make_ir(t60=3.6, predelay=0.04, stereo=True, seed=77, damp_hi=0.3, er_spread=0.08)
    targets = {"duduk": -20, "choir": -24.5, "drone": -29, "kanun": -29, "drums": -27, "wind": -36}
    return mixdown(tr, targets, ir, verb_wet=0.45, comp=True)


# ==========================================================================
# BATTLE  (120 BPM, 40 bars = 80 s)
# ==========================================================================
LEAD_A = [(0, 1, 69, "a"), (1, .5, 69), (1.5, .5, 70), (2, .5, 69), (2.5, .5, 67), (3, .5, 66), (3.5, .5, 67),
          (4, 2, 69), (6, .5, 70), (6.5, .5, 72), (7, 1, 74, "a"),
          (8, .5, 72), (8.5, .5, 70), (9, 1, 69), (10, .5, 67), (10.5, .5, 66), (11, 1, 63),
          (12, 3, 62, "t"),
          (16, 1, 74, "a"), (17, .5, 72), (17.5, .5, 70), (18, 1, 72), (19, 1, 69),
          (20, .5, 70), (20.5, .5, 69), (21, 1, 67), (22, 2, 69),
          (24, .5, 67), (24.5, .5, 66), (25, .5, 67), (25.5, .5, 69), (26, 1, 70), (27, 1, 69),
          (28, .5, 66), (28.5, .5, 63), (29, 2.5, 62)]
LEAD_B = [(0, 2, 74, "g"), (2, .5, 75), (2.5, .5, 74), (3, 1, 72), (4, 1, 70), (5, 1, 72), (6, 2, 74),
          (8, .5, 75), (8.5, .5, 74), (9, .5, 72), (9.5, .5, 70), (10, 1, 69), (11, 1, 70), (12, 3.5, 69, "t"),
          (16, 1, 69, "a"), (17, 1, 70), (18, 1, 72), (19, 1, 74), (20, 1.5, 75, "m"), (21.5, .5, 74), (22, 2, 72),
          (24, .5, 70), (24.5, .5, 72), (25, .5, 70), (25.5, .5, 69), (26, 1, 67), (27, 1, 66),
          (28, 1, 67), (29, 2.5, 62)]
SLOW = [(0, 2, 69), (2, 1, 70), (3, 1, 69), (4, 3, 66, "g"), (7, 1, 67), (8, 4, 69), (13, 1, 72), (14, 1, 70),
        (15, 1, 69), (16, 2, 67), (18, 1, 66), (19, 1, 63), (20, 5, 62)]

DRUM_BASS = {0: 1.0, 7: 0.45, 8: 0.9, 10: 0.6}
DRUM_TAK = {4: 1.0, 6: 0.55, 12: 1.0, 14: 0.55, 15: 0.4, 2: 0.22, 9: 0.22, 13: 0.25}


def groove(tr, bar, rng, full=True, fill=False, bass=DRUM_BASS, tak=DRUM_TAK):
    b = bar * 4
    for pos, v in bass.items():
        tr.add("dhol", dhol_dum(rng, v), b + pos / 4, 1.0, -0.05, 0.15, 4)
    if fill:
        for pos in range(16):
            tr.add("dhol", dhol_tak(rng, 0.3 + 0.045 * pos), b + pos / 4, 1.0, 0.15, 0.2, 3)
        tr.add("dhol", dhol_dum(rng, 1.0), b + 3.5, 1.0, -0.05, 0.15)
        return
    if full:
        for pos, v in tak.items():
            tr.add("dhol", dhol_tak(rng, v * rng.uniform(0.85, 1.05)), b + pos / 4, 1.0, 0.15, 0.2, 4)
        for e in range(8):
            tr.add("perc", daf(rng, 0.5 if e % 2 == 0 else 0.3), b + e / 2, 1.0, 0.45, 0.2, 5)
            tr.add("perc", daf(rng, 0.12, 1.0), b + e / 2 + 0.25, 1.0, -0.45, 0.2, 5)


def ostinato(tr, bar, root, rng, vel=1.0, octave_up=False):
    pat = [0, 0, 12, 0, 1, 0, 10, 0]  # D D D' D Eb D C' D (relative to root)
    for e, iv in enumerate(pat):
        m = root + iv
        v = vel * (1.0 if e in (0, 4) else 0.7) * rng.uniform(0.9, 1.05)
        tr.add("strings", string_note(0.22, m, rng, v), bar * 4 + e / 2, 1.0, -0.25, 0.2, 2)
        if octave_up:
            tr.add("strings", string_note(0.22, m + 12, rng, v * 0.6, voices=2), bar * 4 + e / 2, 1.0, 0.3, 0.25, 2)


def make_battle():
    tr = Track(120, 40, seed=777)
    rng = tr.rng
    L = tr.L
    dr = drone(L, [38, 45], rng, cutoff=900, breathe=0.15)
    tr.stem("drone", 0.2)[:] += np.stack([dr, dr]) * 0.6
    roots = {"D": 38, "Eb": 39, "Cm": 36, "Bb": 34}
    prog = ["D", "D", "Eb", "D"] * 2 + ["D", "D", "Cm", "D"] * 2 + ["Eb", "D", "Bb", "D"] * 2 + \
           ["D"] * 8 + ["D", "D", "Eb", "D", "Cm", "D", "Eb", "D"]
    chord_of = {"D": "D5", "Eb": "Eb", "Cm": "Cm", "Bb": "Bb"}
    for bar in range(40):
        sec = bar // 8
        c = prog[bar]
        fill = bar in (7, 15, 23, 39)
        if sec == 3:  # breakdown
            if bar % 2 == 0:
                tr.add("dhol", taiko(rng, 0.8), bar * 4, 1.0, 0.0, 0.3)
            if bar >= 30:
                groove(tr, bar, rng, full=(bar == 31), fill=(bar == 31))
            tr.add("dhol", dhol_dum(rng, 0.6), bar * 4 + 2.5, 1.0, 0, 0.2, 3)
        else:
            groove(tr, bar, rng, full=True, fill=fill)
            ostinato(tr, bar, roots[c], rng, 1.0, octave_up=(sec in (2, 4)))
        if bar % 4 == 0 and sec != 3:
            tr.add("dhol", taiko(rng, 0.9), bar * 4, 1.0, 0.0, 0.35)
        # choir: stabs in sec 0, sustained chords sec 2/3/4
        if sec == 0 and bar % 4 == 0:
            tr.add("choir", choir(1.0, CH["D5"], rng, "ah", att=0.05, rel=0.8), bar * 4, 0.8, send=0.5)
        elif sec in (2, 3, 4) and bar % 2 == 0:
            tr.add("choir", choir(4 * tr.beat * 2, CH[chord_of[c]], rng, "ah" if sec != 3 else "oo",
                                  att=0.5, rel=0.9), bar * 4, 1.0, send=0.5)
    # leads
    add_reed(tr, "lead", LEAD_A, 32, "duduk", 1.0, -0.1, 0.35)
    add_reed(tr, "lead", LEAD_A, 32, "duduk", 0.35, 0.2, 0.35, transpose=-12)  # octave-down double
    add_reed(tr, "lead", LEAD_B, 64, "zurna", 0.75, 0.05, 0.35)
    add_reed(tr, "lead", SLOW, 96, "duduk", 1.0, 0.0, 0.5)
    add_reed(tr, "lead", LEAD_A, 128, "zurna", 0.7, -0.05, 0.35)
    add_reed(tr, "lead", LEAD_A, 128, "duduk", 0.45, 0.25, 0.35, transpose=-12)
    # kanun 16th sparkle in section 2 and 5
    for bar in list(range(16, 24)) + list(range(32, 40)):
        tones = [74, 69, 66, 69, 74, 75, 74, 69] if prog[bar] == "D" else [75, 70, 67, 70, 75, 74, 70, 67]
        for e in range(8):
            tr.add("kanun", kanun(tones[e], rng, 1.0, 0.4 if e % 2 else 0.55), bar * 4 + e / 2, 1.0,
                   0.5 if e % 2 else -0.5, 0.3, 4)
    # transitions
    for bar in (7, 15, 23, 31, 39):
        cs = cymbal_swell(2 * tr.beat * 2, rng)
        tr.add("fx", np.stack([cs, np.roll(cs, 50)]), bar * 4 + 4 - 4, 0.8, send=0.3)
    rs = riser(4 * tr.beat * 2, rng)
    tr.add("fx", np.stack([rs, rs]), 30 * 4, 0.6, send=0.4)
    ir = make_ir(t60=2.4, predelay=0.025, stereo=True, seed=78, damp_hi=0.35)
    targets = {"dhol": -20, "lead": -23, "strings": -25, "choir": -27, "drone": -32, "perc": -31,
             "kanun": -32, "fx": -31}
    return mixdown(tr, targets, ir, verb_wet=0.3)


# ==========================================================================
# BOSS  (128 BPM, 32 bars = 60 s)
# ==========================================================================
BOSS_LEAD = [(0, 1, 74, "a"), (1, .5, 75), (1.5, .5, 74), (2, .5, 72), (2.5, .5, 70), (3, 1, 69),
             (4, .5, 70), (4.5, .5, 69), (5, .5, 67), (5.5, .5, 66), (6, 2, 63, "t"),
             (8, 1, 62, "a"), (9, .5, 63), (9.5, .5, 66), (10, .5, 67), (10.5, .5, 69), (11, 1, 70),
             (12, .5, 72), (12.5, .5, 70), (13, .5, 69), (13.5, .5, 70), (14, 2, 69, "t"),
             (16, 1, 81, "a"), (17, .5, 79), (17.5, .5, 78), (18, 1, 79), (19, 1, 78), (20, .5, 75), (20.5, .5, 74),
             (21, .5, 75), (21.5, .5, 78), (22, 2, 74, "t"),
             (24, .5, 72), (24.5, .5, 74), (25, .5, 72), (25.5, .5, 70), (26, 1, 69), (27, 1, 70),
             (28, .5, 69), (28.5, .5, 66), (29, .5, 63), (29.5, .5, 66), (30, 2, 62)]


def make_boss():
    tr = Track(128, 32, seed=666)
    rng = tr.rng
    L = tr.L
    dr = drone(L, [26, 38, 45], rng, cutoff=800, breathe=0.1)
    tr.stem("drone", 0.2)[:] += np.stack([dr, dr]) * 0.7
    prog = (["D", "D", "Eb", "Eb", "Bb", "Bb", "A", "A"] * 4)
    roots = {"D": 38, "Eb": 39, "Bb": 34, "A": 33}
    tak16 = {p: (0.9 if p % 4 == 0 else 0.45) for p in range(16)}
    bass16 = {0: 1.0, 3: 0.6, 6: 0.7, 8: 1.0, 11: 0.6, 14: 0.7}
    for bar in range(32):
        c = prog[bar]
        sec = bar // 8
        fill = bar % 8 == 7
        groove(tr, bar, rng, full=True, fill=fill, bass=bass16 if sec >= 1 else DRUM_BASS,
               tak=tak16 if sec >= 2 else DRUM_TAK)
        tr.add("dhol", taiko(rng, 1.0), bar * 4, 1.0, -0.2, 0.35)
        tr.add("dhol", taiko(rng, 0.8), bar * 4 + 2, 1.0, 0.2, 0.35)
        # 16th string ostinato
        r = roots[c]
        pat = [0, 12, 0, 1, 0, 12, 0, 10, 0, 12, 0, 1, 0, 7, 0, 1]
        for e, iv in enumerate(pat):
            v = (1.0 if e % 4 == 0 else 0.65) * rng.uniform(0.9, 1.05)
            tr.add("strings", string_note(0.13, r + iv, rng, v, cut=3000), bar * 4 + e / 4, 1.0, -0.2, 0.2, 2)
            if sec >= 2:
                tr.add("strings", string_note(0.13, r + iv + 12, rng, v * 0.5, voices=2), bar * 4 + e / 4, 1.0,
                       0.35, 0.25, 2)
        if bar % 2 == 0:
            br = braam(2 * 4 * tr.beat * 0.95, [r, r + 7, r + 12], rng)
            tr.add("brass", br, bar * 4, 1.0, send=0.4)
            ch = {"D": [62, 63, 69], "Eb": [63, 67, 70], "Bb": [62, 65, 70], "A": [61, 64, 69]}[c]
            tr.add("choir", choir(2 * 4 * tr.beat, [m - 12 for m in ch] + ch, rng, "ah" if sec % 2 else "oh",
                                  att=0.3, rel=0.6), bar * 4, 1.0, send=0.5)
    add_reed(tr, "lead", BOSS_LEAD, 32, "zurna", 0.8, -0.05, 0.3)
    add_reed(tr, "lead", BOSS_LEAD, 32, "duduk", 0.5, 0.2, 0.3, transpose=-12)
    add_reed(tr, "lead", BOSS_LEAD, 96, "zurna", 0.8, 0.05, 0.3)
    add_reed(tr, "lead", BOSS_LEAD, 96, "zurna", 0.4, -0.3, 0.3, transpose=-12)
    for bar in (7, 15, 23, 31):
        cs = cymbal_swell(4 * tr.beat, rng)
        tr.add("fx", np.stack([cs, np.roll(cs, 40)]), bar * 4, 0.9, send=0.3)
    ir = make_ir(t60=2.2, predelay=0.02, stereo=True, seed=79, damp_hi=0.35)
    targets = {"dhol": -20, "lead": -23.5, "strings": -24.5, "brass": -24, "choir": -26.5, "drone": -31,
             "perc": -31, "fx": -30}
    return mixdown(tr, targets, ir, verb_wet=0.28)


def main(argv):
    OUT.mkdir(parents=True, exist_ok=True)
    sel = argv[1:] or ["menu", "battle", "boss"]
    for i, (name, fn) in enumerate([("menu", make_menu), ("battle", make_battle), ("boss", make_boss)]):
        if name not in sel:
            continue
        mix = fn()
        assert np.all(np.isfinite(mix))
        write_wav(OUT / f"music_{name}.wav", mix, seed=100 + i)
        report(f"music_{name}", mix)


if __name__ == "__main__":
    main(sys.argv)
