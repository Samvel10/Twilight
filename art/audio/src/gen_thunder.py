"""Procedural thunder for Vahagn's lightning (CC0, no samples): a close crack, then a long rolling rumble.
Writes sfx/sfx_thunder.wav (48 kHz, mono, 16-bit, peak -1 dBFS)."""
import os
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
rng = np.random.default_rng(1937)
dur = 5.5
n = int(SR * dur)
t = np.arange(n) / SR

def bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)

def lp(x, f, order=4):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)

noise = rng.standard_normal(n)
# 1) the crack: a few very short broadband snaps within 60 ms
crack = np.zeros(n)
for k in range(5):
    t0 = 0.005 + 0.012 * k + rng.uniform(0, 0.006)
    env = np.exp(-np.clip(t - t0, 0, None) / (0.012 + 0.01 * k)) * (t >= t0)
    crack += env * bp(noise, 1500 + 600 * k, 9000) * (1.0 - 0.15 * k)
crack += np.exp(-t / 0.18) * bp(noise, 300, 3000) * 0.8
# 2) rolling rumble: low-passed noise with slow random swells (echoes off the mountains)
rumble = lp(noise, 160) * 6.0
swell = np.zeros(n)
for k in range(9):
    c = 0.15 + rng.uniform(0, 3.8)
    w = rng.uniform(0.25, 0.9)
    swell += rng.uniform(0.4, 1.0) * np.exp(-0.5 * ((t - c) / w) ** 2)
swell += 1.2 * np.exp(-0.5 * ((t - 0.35) / 0.35) ** 2)
fade = np.clip(1.0 - (t - 4.2) / 1.3, 0, 1) ** 2
rumble *= swell * fade * np.clip(t / 0.08, 0, 1)
# a mid-band "tearing" layer between crack and rumble
tear = bp(noise, 120, 900) * np.exp(-np.clip(t - 0.05, 0, None) / 0.9) * (t >= 0.05) * 0.7
x = crack * 0.9 + rumble + tear
x -= x.mean()
x /= np.max(np.abs(x)) / 10 ** (-1 / 20)
d = (rng.uniform(-1, 1, n) + rng.uniform(-1, 1, n)) / 32768.0  # TPDF dither
out = np.clip(x + d, -1, 1)
dst = os.path.join(os.path.dirname(__file__), "..", "sfx", "sfx_thunder.wav")
wavfile.write(dst, SR, (out * 32767).astype(np.int16))
print("wrote", os.path.abspath(dst), "%.2fs" % dur)
