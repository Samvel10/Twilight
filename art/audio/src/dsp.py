"""
dsp.py - small procedural-audio toolkit for "Vahagn: Vishapakagh".

Everything is numpy/scipy (numba optional, only to speed up the time-varying
state-variable filter).  All signals are float64, 48 kHz.  Mono = 1-D array,
stereo = array of shape (2, n).

Key ideas used to make things sound *good* rather than beepy:
  * layered, shaped noise (pink/brown/band-limited) with turbulent modulation
  * band-limited additive oscillators with formant (resonance) weighting,
    vibrato, jitter and amplitude-dependent brightness
  * time-varying resonant filters (TPT state-variable filter)
  * convolution reverb with a synthetic, frequency-dependent-decay impulse
    response (decorrelated L/R for width)
  * soft saturation, a look-ahead brick-wall limiter, BS.1770 loudness
  * "circular" rendering: loops are built in a ring buffer of exactly the loop
    length, reverb is circular convolution, so loop seams are mathematically
    continuous (no crossfade guesswork).
"""
from __future__ import annotations

import math
import wave

import numpy as np
from scipy import signal

SR = 48000

try:  # optional JIT
    from numba import njit
except Exception:  # pragma: no cover
    def njit(*a, **k):
        def deco(f):
            return f
        if a and callable(a[0]):
            return a[0]
        return deco


# --------------------------------------------------------------------------
# basics
# --------------------------------------------------------------------------
def ns(dur: float) -> int:
    return int(round(dur * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def db(x):
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10.0 ** (np.asarray(d) / 20.0)


def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def fit(x: np.ndarray, n: int) -> np.ndarray:
    """Pad with zeros / truncate the last axis to n samples."""
    if x.shape[-1] >= n:
        return x[..., :n]
    pad = [(0, 0)] * (x.ndim - 1) + [(0, n - x.shape[-1])]
    return np.pad(x, pad)


def mix_at(dst: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0):
    """Add src into dst at sample offset start (linear, clipped to dst)."""
    if start >= dst.shape[-1]:
        return dst
    if start < 0:
        src = src[..., -start:]
        start = 0
    m = min(src.shape[-1], dst.shape[-1] - start)
    if m > 0:
        dst[..., start:start + m] += gain * src[..., :m]
    return dst


def ring_add(ring: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0):
    """Add src into a circular buffer (last axis) wrapping around the end."""
    L = ring.shape[-1]
    start %= L
    m = src.shape[-1]
    pos = 0
    while pos < m:
        a = (start + pos) % L
        k = min(m - pos, L - a)
        ring[..., a:a + k] += gain * src[..., pos:pos + k]
        pos += k
    return ring


# --------------------------------------------------------------------------
# envelopes
# --------------------------------------------------------------------------
def env_exp(n, tau, attack=0.0):
    t = tvec(n)
    e = np.exp(-t / max(tau, 1e-6))
    if attack > 0:
        e *= np.clip(t / attack, 0, 1) ** 0.5
    return e


def env_adsr(n, a, d, s, r, total=None, curve=2.0):
    """ADSR where note-off happens at n - r samples."""
    na, nd, nr = ns(a), ns(d), ns(r)
    nsus = max(n - na - nd - nr, 0)
    parts = [
        np.linspace(0, 1, max(na, 1), endpoint=False) ** (1 / curve) if na else np.zeros(0),
        s + (1 - s) * np.exp(-np.linspace(0, 5, max(nd, 1))) if nd else np.zeros(0),
        np.full(nsus, s),
        s * np.linspace(1, 0, max(nr, 1)) ** curve if nr else np.zeros(0),
    ]
    e = np.concatenate(parts)
    return fit(e, n)


def env_points(n, pts, kind="linear"):
    """Piecewise envelope from [(time_s, value), ...]."""
    t = tvec(n)
    tp = np.array([p[0] for p in pts], dtype=float)
    vp = np.array([p[1] for p in pts], dtype=float)
    if kind == "log":
        return np.exp(np.interp(t, tp, np.log(np.maximum(vp, 1e-9))))
    return np.interp(t, tp, vp)


def fade(x, fin=0.002, fout=0.01):
    x = x.copy()
    a, b = ns(fin), ns(fout)
    if a:
        x[..., :a] *= np.linspace(0, 1, a) ** 2
    if b:
        x[..., -b:] *= np.linspace(1, 0, b) ** 2
    return x


# --------------------------------------------------------------------------
# noise & modulators
# --------------------------------------------------------------------------
def spectral_noise(n, rng, slope_db_oct=0.0, lo=None, hi=None, periodic=True):
    """FFT-shaped noise.  Exactly periodic with period n (great for loops).
    slope_db_oct: 0 white, -3 pink, -6 brown."""
    X = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    f1 = np.maximum(f, 1.0)
    g = (f1 / 1000.0) ** (slope_db_oct / 6.0206)
    if lo is not None:
        g *= 1.0 / np.sqrt(1 + (lo / f1) ** 8)
    if hi is not None:
        g *= 1.0 / np.sqrt(1 + (f1 / hi) ** 8)
    g[0] = 0
    x = np.fft.irfft(X * g, n)
    return x / (np.std(x) + 1e-12)


def white(n, rng):
    return rng.standard_normal(n)


def pink(n, rng, **kw):
    return spectral_noise(n, rng, -3.0, **kw)


def brown(n, rng, **kw):
    return spectral_noise(n, rng, -6.0, **kw)


def smooth_noise(n, rate_hz, rng, periodic=False):
    """Slow random modulation signal, roughly unit std, bandwidth ~rate_hz."""
    if periodic:
        return spectral_noise(n, rng, 0.0, hi=rate_hz)
    k = max(int(n * rate_hz / SR) + 4, 4)
    pts = rng.standard_normal(k)
    x = np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
    sos = signal.butter(2, max(rate_hz, 0.05), fs=SR, output="sos")
    y = signal.sosfiltfilt(sos, x)
    return y / (np.std(y) + 1e-12)


def periodic_lfo(n, rng, n_harm=4, cycles_min=1):
    """Smooth random modulator that is exactly periodic over n samples."""
    t = np.arange(n) / n
    y = np.zeros(n)
    for k in range(cycles_min, cycles_min + n_harm):
        y += rng.uniform(0.3, 1.0) / k * np.sin(2 * np.pi * k * t + rng.uniform(0, 2 * np.pi))
    return y / (np.max(np.abs(y)) + 1e-12)


# --------------------------------------------------------------------------
# filters
# --------------------------------------------------------------------------
def _sos(kind, f, order=2, q=None):
    nyq = SR / 2 * 0.98
    if kind in ("lp", "hp"):
        return signal.butter(order, min(f, nyq), btype="low" if kind == "lp" else "high", fs=SR, output="sos")
    lo, hi = f
    return signal.butter(order, [max(lo, 5), min(hi, nyq)], btype="band", fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(_sos("lp", f, order), x, axis=-1)


def hp(x, f, order=2):
    return signal.sosfilt(_sos("hp", f, order), x, axis=-1)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos("bp", (lo, hi), order), x, axis=-1)


def peak_eq(x, f0, gain_db, q=1.0):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=-1)


def shelf(x, f0, gain_db, high=True):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / 2 * np.sqrt(2)
    c = np.cos(w0)
    if high:
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
             (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    else:
        b = [A * ((A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * c),
             A * ((A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * c),
             (A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al]
    b, a = np.array(b), np.array(a)
    return signal.lfilter(b / a[0], a / a[0], x, axis=-1)


def resonator_bank(x, freqs, qs, gains):
    """Parallel band-pass resonators (formants)."""
    y = np.zeros_like(x)
    for f, q, g in zip(freqs, qs, gains):
        b, a = signal.iirpeak(min(f, SR * 0.45), q, fs=SR)
        y += g * signal.lfilter(b, a, x, axis=-1)
    return y


@njit(cache=True)
def _svf(x, fc, res, mode):
    # Zavalishin TPT state-variable filter, per-sample cutoff.
    n = x.shape[0]
    y = np.zeros(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 2.0 - 2.0 * res
    for i in range(n):
        f = fc[i]
        if f > 0.45 * 48000.0:
            f = 0.45 * 48000.0
        if f < 10.0:
            f = 10.0
        g = math.tan(math.pi * f / 48000.0)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = v1 * k  # normalised band-pass (unity peak)
        else:
            y[i] = x[i] - k * v1 - v2
    return y


def svf(x, fc, res=0.2, mode="lp"):
    """Time-varying filter. fc: scalar or per-sample array (Hz). res 0..0.95."""
    x = np.ascontiguousarray(x, dtype=np.float64)
    fc = np.broadcast_to(np.asarray(fc, dtype=np.float64), x.shape).copy()
    m = {"lp": 0, "bp": 1, "hp": 2}[mode]
    return _svf(x, fc, float(res), m)


def svf_circular(x, fc, res=0.2, mode="lp"):
    """Same as svf but for a loop: runs twice around the ring, returns 2nd lap."""
    L = x.shape[-1]
    fc = np.broadcast_to(np.asarray(fc, dtype=np.float64), x.shape)
    y = svf(np.concatenate([x, x]), np.concatenate([fc, fc]), res, mode)
    return y[L:]


def circular(fn, x, laps=2):
    """Apply a (causal, short-memory) processor to a loop seamlessly."""
    L = x.shape[-1]
    y = fn(np.concatenate([x] * laps, axis=-1))
    return y[..., (laps - 1) * L: laps * L]


# --------------------------------------------------------------------------
# non-linear
# --------------------------------------------------------------------------
def saturate(x, drive=1.0, asym=0.0):
    """tanh soft-clip, unity small-signal gain-compensated."""
    y = np.tanh(drive * (x + asym)) - np.tanh(drive * asym)
    return y / max(drive, 1e-9)


def limiter(x, ceiling_db=-1.0, lookahead=0.004, release=0.08):
    """Look-ahead brick-wall peak limiter (mono or stereo-linked)."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    c = undb(ceiling_db)
    peak = np.max(np.abs(np.atleast_2d(x)), axis=0)
    g = np.minimum(1.0, c / np.maximum(peak, 1e-12))
    la = max(ns(lookahead), 1)
    g = minimum_filter1d(g, size=2 * la + 1, mode="nearest")
    # release smoothing (one-pole on the "release" side only)
    a = math.exp(-1.0 / (release * SR))
    g = _release(g, a)
    g = uniform_filter1d(g, size=la, mode="nearest")
    g = np.minimum(g, minimum_filter1d(np.minimum(1.0, c / np.maximum(peak, 1e-12)), size=3, mode="nearest"))
    return x * g


@njit(cache=True)
def _release(g, a):
    y = np.empty_like(g)
    s = 1.0
    for i in range(g.shape[0]):
        v = g[i]
        if v < s:
            s = v
        else:
            s = a * s + (1 - a) * v
        y[i] = s
    return y


def compress(x, thresh_db=-18, ratio=3.0, attack=0.01, release=0.15, makeup_db=0.0):
    """Simple feed-forward RMS-ish compressor (stereo linked)."""
    lvl = np.max(np.abs(np.atleast_2d(x)), axis=0)
    env = _env_follow(lvl, math.exp(-1 / (attack * SR)), math.exp(-1 / (release * SR)))
    ldb = db(env)
    over = np.maximum(ldb - thresh_db, 0)
    gdb = -over * (1 - 1 / ratio) + makeup_db
    return x * undb(gdb)


@njit(cache=True)
def _env_follow(x, aa, ar):
    y = np.empty_like(x)
    s = 0.0
    for i in range(x.shape[0]):
        v = x[i]
        if v > s:
            s = aa * s + (1 - aa) * v
        else:
            s = ar * s + (1 - ar) * v
        y[i] = s
    return y


# --------------------------------------------------------------------------
# oscillators
# --------------------------------------------------------------------------
def phase_from_freq(freq):
    return 2 * np.pi * np.cumsum(freq) / SR


def additive(freq, weights_fn, rng=None, max_harm=200, fmax=16000.0, bright=None, phase0=None):
    """Band-limited additive oscillator.
    freq: per-sample fundamental (Hz).  weights_fn(k, fk_mean) -> amplitude.
    bright: optional per-sample cutoff in Hz (array or scalar); harmonics above it
            roll off at 12 dB/oct, so a moving cutoff = dynamic brightness."""
    freq = np.asarray(freq, dtype=float)
    ph = phase_from_freq(freq)
    f_mean = float(np.mean(freq))
    f_max = float(np.max(freq))
    nh = int(min(max_harm, max(1, fmax // max(f_max, 1))))
    out = np.zeros_like(freq)
    rng = rng or np.random.default_rng(0)
    for k in range(1, nh + 1):
        w = weights_fn(k, k * f_mean)
        if w < 1e-5:
            continue
        p0 = rng.uniform(0, 2 * np.pi) if phase0 is None else phase0
        comp = np.sin(k * ph + p0)
        # fade harmonics that approach Nyquist when freq rises
        top = k * freq
        guard = np.clip((0.45 * SR - top) / 2000.0, 0, 1)
        if bright is not None:  # bright = per-sample brightness cutoff (Hz), 12 dB/oct above it
            comp *= 1.0 / (1.0 + (top / bright) ** 2)
        out += w * comp * guard
    return out


def formant_curve(freqs, centers, widths, gains, base=1.0, rolloff=None):
    """Spectral envelope (linear amp) evaluated at freqs (sum of log-gaussians)."""
    f = np.maximum(np.asarray(freqs, dtype=float), 1.0)
    env = np.full_like(f, base, dtype=float)
    for c, w, g in zip(centers, widths, gains):
        env += g * np.exp(-0.5 * (np.log2(f / c) / w) ** 2)
    if rolloff is not None:
        env /= np.sqrt(1 + (f / rolloff) ** 4)
    return env


def sine_sweep(n, f_pts, amp=None, kind="log"):
    f = env_points(n, f_pts, kind)
    y = np.sin(phase_from_freq(f))
    return y if amp is None else y * amp


# --------------------------------------------------------------------------
# reverb
# --------------------------------------------------------------------------
def make_ir(t60=2.0, dur=None, predelay=0.02, stereo=True, seed=1, damp_hi=0.35, early=True, er_spread=0.06,
            lo_cut=60.0):
    """Synthetic room/hall impulse response with frequency-dependent decay.
    damp_hi: high-frequency T60 as a fraction of t60."""
    rng = np.random.default_rng(seed)
    dur = dur or t60 * 1.2
    n = ns(dur)
    nch = 2 if stereo else 1
    t = tvec(n)
    chans = []
    bands = [(20, 250, 1.15), (250, 1200, 1.0), (1200, 4000, 0.65), (4000, 20000, damp_hi)]
    for ch in range(nch):
        noise = rng.standard_normal(n)
        acc = np.zeros(n)
        for lo, hi, fac in bands:
            bnd = bp(noise, lo, min(hi, 23000), order=3) if hi < 20000 else hp(noise, lo, 3)
            acc += bnd * np.exp(-6.9078 * t / (t60 * fac))
        # smooth onset of the diffuse tail
        acc *= np.clip(t / 0.03, 0, 1) ** 1.5
        if early:
            for _ in range(14):
                d = rng.uniform(0.004, er_spread)
                i = ns(d)
                if i < n:
                    acc[i] += rng.uniform(0.2, 0.6) * rng.choice([-1, 1]) * math.exp(-d * 12)
        acc = hp(acc, lo_cut, 2)
        acc = np.concatenate([np.zeros(ns(predelay)), acc])
        chans.append(acc)
    ir = np.stack(chans)
    ir /= np.sqrt(np.sum(ir ** 2) / nch)
    return ir if stereo else ir[0]


def reverb(x, ir, wet=0.25, dry=1.0):
    """Linear convolution reverb.  mono x + mono ir -> mono; otherwise stereo."""
    if x.ndim == 1 and ir.ndim == 1:
        w = signal.oaconvolve(x, ir)
        return dry * fit(x, w.shape[-1]) + wet * w
    xs = np.atleast_2d(x)
    if xs.shape[0] == 1:
        xs = np.vstack([xs, xs])
    irs = np.atleast_2d(ir)
    if irs.shape[0] == 1:
        irs = np.vstack([irs, irs])
    w = np.stack([signal.oaconvolve(xs[c], irs[c]) for c in range(2)])
    return dry * fit(xs, w.shape[-1]) + wet * w


def reverb_circular(x, ir, wet=0.25, dry=1.0):
    """Circular convolution reverb for loops (tail wraps to the loop start)."""
    L = x.shape[-1]
    irs = np.atleast_2d(ir)
    # fold IR if longer than the loop
    if irs.shape[-1] > L:
        k = int(math.ceil(irs.shape[-1] / L))
        irs = fit(irs, k * L).reshape(irs.shape[0], k, L).sum(axis=1)
    xs = np.atleast_2d(x)
    nch = max(xs.shape[0], irs.shape[0])
    if xs.shape[0] < nch:
        xs = np.repeat(xs, nch, axis=0)
    if irs.shape[0] < nch:
        irs = np.repeat(irs, nch, axis=0)
    X = np.fft.rfft(xs, L, axis=-1)
    H = np.fft.rfft(irs, L, axis=-1)
    w = np.fft.irfft(X * H, L, axis=-1)
    y = dry * xs + wet * w
    return y[0] if (x.ndim == 1 and np.atleast_2d(ir).shape[0] == 1) else y


def delay_echo(x, time, fb=0.3, wet=0.3, lp_hz=3000, taps=4):
    y = x.copy()
    d = ns(time)
    src = x
    g = wet
    for i in range(taps):
        src = lp(np.concatenate([np.zeros(d), src])[: x.shape[-1] + d * (i + 1)], lp_hz)
        y = fit(y, src.shape[-1]) + g * src
        g *= fb
    return y


# --------------------------------------------------------------------------
# stereo
# --------------------------------------------------------------------------
def pan(x, p):
    """Equal-power pan, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def widen(st, amount=1.2):
    m = 0.5 * (st[0] + st[1])
    s = 0.5 * (st[0] - st[1]) * amount
    return np.stack([m + s, m - s])


# --------------------------------------------------------------------------
# loudness / analysis
# --------------------------------------------------------------------------
_K1 = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
       np.array([1.0, -1.69065929318241, 0.73248077421585]))
_K2 = (np.array([1.0, -2.0, 1.0]), np.array([1.0, -1.99004745483398, 0.99007225036621]))


def lufs(x):
    """Integrated loudness, ITU-R BS.1770-4 (48 kHz coefficients)."""
    xs = np.atleast_2d(x)
    y = signal.lfilter(*_K1, xs, axis=-1)
    y = signal.lfilter(*_K2, y, axis=-1)
    blk, hop = ns(0.4), ns(0.1)
    n = y.shape[-1]
    if n < blk:
        ms = np.mean(y ** 2, axis=-1).sum()
        return -0.691 + 10 * math.log10(ms + 1e-20)
    starts = np.arange(0, n - blk + 1, hop)
    cs = np.cumsum(np.concatenate([np.zeros((y.shape[0], 1)), y ** 2], axis=1), axis=1)
    ms = ((cs[:, starts + blk] - cs[:, starts]) / blk).sum(axis=0)
    l = -0.691 + 10 * np.log10(ms + 1e-20)
    g = ms[l > -70]
    if g.size == 0:
        return -70.0
    rel = -0.691 + 10 * math.log10(np.mean(g)) - 10
    g2 = ms[(l > -70) & (l > rel)]
    return -0.691 + 10 * math.log10(np.mean(g2))


def normalize_peak(x, peak_db=-1.0):
    return x * undb(peak_db) / (np.max(np.abs(x)) + 1e-12)


def remove_dc(x, loop=False):
    if loop:
        y = circular(lambda s: hp(s, 18.0, 2), x, laps=3)
    else:
        y = hp(x, 18.0, 2)
    return y - np.mean(y, axis=-1, keepdims=True)


def master_loudness(x, target_lufs=-14.0, ceiling_db=-1.0, loop=False, iters=4):
    """Gain to target LUFS, then limit to ceiling (loop-aware). Iterates."""
    y = x
    for _ in range(iters):
        y = y * undb(target_lufs - lufs(y))
        if loop:
            y = circular(lambda s: limiter(s, ceiling_db - 0.15), y, laps=3)
        else:
            y = limiter(y, ceiling_db - 0.15)
    return y


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------
def write_wav(path, x, seed=0):
    """16-bit PCM with TPDF dither.  x mono 1-D or (2, n)."""
    xs = np.atleast_2d(x)
    nch = xs.shape[0]
    rng = np.random.default_rng(seed)
    d = (rng.random(xs.shape) - rng.random(xs.shape))  # TPDF, +-1 LSB
    q = np.clip(np.round(xs * 32767.0 + d), -32768, 32767).astype("<i2")
    inter = q.T.reshape(-1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(inter.tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        nch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    a = a.reshape(-1, nch).T
    return a, sr, sw
