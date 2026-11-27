"""Synthesized sound design for the Instagram Reel outro (7 s, 48 kHz stereo). Timings match reel_outro.py."""
import os

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR, DUR = 48000, 7.0
N = int(SR * DUR)
rng = np.random.default_rng(11)
mix = np.zeros((N, 2))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_reel")


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(x, t0, gain=1.0, pan=0.0):
    if x.ndim == 1:
        x = np.stack([x * np.sqrt((1 - pan) / 2), x * np.sqrt((1 + pan) / 2)], 1)
    i = int(t0 * SR)
    j = min(N, i + len(x))
    mix[i:j] += x[:j - i] * gain


def flt(x, kind, f, order=2):
    return signal.sosfilt(signal.butter(order, f, kind, fs=SR, output="sos"), x)


def sweep_noise(d, f0, f1, env):
    n = rng.normal(0, 1, int(d * SR))
    out, zi, blk = np.zeros_like(n), None, 512
    for k in range(0, len(n), blk):
        fc = f0 * (f1 / f0) ** (k / len(n))
        sos = signal.butter(2, [fc * 0.6, min(fc * 1.6, SR / 2 - 100)], "bandpass", fs=SR, output="sos")
        zi = np.zeros((sos.shape[0], 2)) if zi is None else zi
        out[k:k + blk], zi = signal.sosfilt(sos, n[k:k + blk], zi=zi)
    return out * env(np.linspace(0, 1, len(n)))


def pop(freq=520, d_=0.18):
    d = tt(d_)
    f = freq * (1 + 1.2 * np.exp(-d * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * 30) * np.clip(d / 0.002, 0, 1)


def click():
    d = tt(0.05)
    return flt(rng.normal(0, 1, len(d)), "highpass", 2500) * np.exp(-d * 220) * 0.6 + \
        np.sin(2 * np.pi * 2200 * d) * np.exp(-d * 160) * 0.4


def pluck(freq, d_=0.6):
    d = tt(d_)
    return sum(np.sin(2 * np.pi * freq * k * d) / k ** 1.4 for k in range(1, 5)) * np.exp(-d * 9) * np.clip(d / 0.003, 0, 1)


def chime(freq, d_=1.6):
    d = tt(d_)
    x = np.sin(2 * np.pi * freq * d + 1.8 * np.exp(-d * 3) * np.sin(2 * np.pi * freq * 1.4 * d)) * np.exp(-d * 3)
    return x * np.clip(d / 0.002, 0, 1)


# ambient pad
t = tt(DUR)
pad = np.zeros((N, 2))
for f, a in [(55, 0.5), (82.4, 0.35), (110, 0.25), (164.8, 0.12)]:
    for ch, det in ((0, 0.997), (1, 1.003)):
        pad[:, ch] += a * np.sin(2 * np.pi * f * det * t + rng.uniform(0, 6))
env = np.clip(t / 0.8, 0, 1) * np.clip((DUR - t) / 0.6, 0, 1)
mix += pad * (env * (0.8 + 0.2 * np.sin(2 * np.pi * 0.2 * t)))[:, None] * 0.045

# riser -> logo impact at 0.72 s
place(sweep_noise(0.72, 400, 7000, lambda u: u ** 2), 0.0, 0.16, -0.2)
place(sweep_noise(0.72, 380, 6500, lambda u: u ** 2), 0.0, 0.16, 0.2)
d = tt(0.72)
place(np.sin(2 * np.pi * (45 * d + 40 * d ** 2)) * (d / 0.72) ** 2, 0.0, 0.22)
d = tt(1.8)
place(np.sin(2 * np.pi * np.cumsum(34 + 60 * np.exp(-d * 9)) / SR) * np.exp(-d * 2.6), 0.72, 0.7)
place(flt(rng.normal(0, 1, len(d)), "highpass", 1500) * np.exp(-d * 28), 0.72, 0.2)
d = tt(2.0)
sh = sum(np.sin(2 * np.pi * fr * d + p) * a for fr, a, p in [(1318.5, 0.5, 0), (1975.5, 0.35, 1), (2637, 0.25, 2)])
place(sh * np.exp(-d * 2.0) * np.clip(d / 0.03, 0, 1), 0.76, 0.06)

# title, card, tag, buttons
place(sweep_noise(0.6, 2600, 700, lambda u: np.sin(np.pi * u) ** 2), 0.90, 0.10)
place(sweep_noise(0.7, 800, 3600, lambda u: np.sin(np.pi * u) ** 3), 1.40, 0.14)
place(pop(700), 2.15, 0.16, -0.4)
place(pop(480), 2.65, 0.18, -0.3)
place(pop(600), 2.80, 0.18, 0.3)
# tap 1: LINK U BIO
place(click(), 3.5, 0.24, -0.25)
place(pluck(784), 3.56, 0.10, -0.25)
place(pluck(1175), 3.62, 0.07, -0.25)
# tap 2: @10pbelgrade + hearts
place(click(), 4.3, 0.24, 0.25)
for k, f in enumerate((1046.5, 1318.5, 1568.0, 2093.0)):
    place(chime(f), 4.36 + k * 0.07, 0.06, 0.25 - k * 0.12)
# logo sweep / card shimmer
place(sweep_noise(1.0, 3000, 9000, lambda u: np.sin(np.pi * u) ** 2), 5.2, 0.035)
place(sweep_noise(1.0, 2500, 8000, lambda u: np.sin(np.pi * u) ** 2), 5.6, 0.03)

# reverb + master
ir_t = tt(1.8)
ir = np.stack([flt(rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 3.8), "lowpass", 6000) for _ in range(2)], 1)
ir /= np.abs(ir).sum(0).max() / 6
wet = np.stack([signal.fftconvolve(mix[:, c], ir[:, c])[:N] for c in range(2)], 1)
out = flt((mix + wet * 0.22).T, "highpass", 25).T
out *= np.clip((DUR - t) / 0.35, 0, 1)[:, None]
out = out / np.abs(out).max() * 10 ** (-3 / 20)
out = np.tanh(out * 1.1) / np.tanh(1.1)
wavfile.write(os.path.join(OUT, "sfx.wav"), SR, (out * 32767 * 0.85).astype(np.int16))
print("sound ok")
