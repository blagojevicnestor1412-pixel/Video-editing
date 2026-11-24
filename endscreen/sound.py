"""Synthesized, subtle sound design for the end screen (48 kHz stereo WAV)."""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
mix = np.zeros((N, 2))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(x, t0, gain=1.0, pan=0.0):
    if x.ndim == 1:
        l, r = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
        x = np.stack([x * l, x * r], 1)
    i = int(t0 * SR)
    j = min(N, i + len(x))
    mix[i:j] += x[: j - i] * gain


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x)


def sweep_noise(d, f0, f1, env):
    """noise through a band-pass whose centre sweeps f0->f1 (block processed)."""
    n = rng.normal(0, 1, int(d * SR))
    out = np.zeros_like(n)
    blk = 512
    zi = None
    for k in range(0, len(n), blk):
        u = k / len(n)
        fc = f0 * (f1 / f0) ** u
        sos = signal.butter(2, [fc * 0.6, min(fc * 1.6, SR / 2 - 100)], "bandpass", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[k:k + blk], zi = signal.sosfilt(sos, n[k:k + blk], zi=zi)
    return out * env(np.linspace(0, 1, len(n)))


def reverb_ir(d=2.2, decay=3.5):
    t = tt(d)
    ir = np.stack([rng.normal(0, 1, len(t)), rng.normal(0, 1, len(t))], 1)
    ir *= np.exp(-t * decay)[:, None]
    ir = np.stack([lp(ir[:, 0], 6000), lp(ir[:, 1], 6000)], 1)
    return ir / np.abs(ir).sum(0).max() * 6


# --- ambient pad (very low) --------------------------------------------------
t = tt(DUR)
pad = np.zeros((N, 2))
for f, a in [(55, 0.5), (82.4, 0.35), (110, 0.25), (164.8, 0.12), (220, 0.06)]:
    for ch, det in ((0, 0.997), (1, 1.003)):
        pad[:, ch] += a * np.sin(2 * np.pi * f * det * t + rng.uniform(0, 6))
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.12 * t)
env = np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
mix += pad * (lfo * env)[:, None] * 0.045
air = np.stack([hp(lp(rng.normal(0, 1, N), 9000), 3000) for _ in range(2)], 1)
mix += air * (env * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)))[:, None] * 0.006

# --- intro riser into logo impact ------------------------------------------
r = sweep_noise(1.05, 300, 7000, lambda u: u ** 2.2)
place(r, 0.0, 0.16, -0.2)
place(sweep_noise(1.05, 280, 6500, lambda u: u ** 2.2), 0.0, 0.16, 0.2)
d = tt(1.0)
sub = np.sin(2 * np.pi * (40 * d + 25 * d ** 2)) * (d / 1.0) ** 2
place(sub, 0.0, 0.25)

# impact at 1.0 s
d = tt(2.0)
f = 34 + 60 * np.exp(-d * 9)
boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * 2.4)
place(boom, 1.0, 0.7)
crack = hp(rng.normal(0, 1, len(d)), 1500) * np.exp(-d * 28)
place(crack, 1.0, 0.18, -0.1)
place(hp(rng.normal(0, 1, len(d)), 1500) * np.exp(-d * 28), 1.0, 0.18, 0.1)
# shimmer
d = tt(2.5)
sh = sum(np.sin(2 * np.pi * fr * d + p) * a for fr, a, p in
         [(1318.5, 0.5, 0), (1975.5, 0.35, 1), (2637, 0.25, 2), (3951, 0.12, 3)])
sh *= np.exp(-d * 1.8) * np.clip(d / 0.03, 0, 1) * (1 + 0.3 * np.sin(2 * np.pi * 6 * d))
place(sh, 1.05, 0.07)

# --- title whoosh + slot swooshes ---------------------------------------------
place(sweep_noise(0.7, 2500, 600, lambda u: np.sin(np.pi * u) ** 2), 1.3, 0.10)
place(sweep_noise(0.6, 900, 3500, lambda u: np.sin(np.pi * u) ** 3), 1.75, 0.13, -0.6)
place(sweep_noise(0.6, 900, 3500, lambda u: np.sin(np.pi * u) ** 3), 1.9, 0.13, 0.6)
# ring power-up
d = tt(0.9)
tone = np.sin(2 * np.pi * np.cumsum(300 + 500 * d / 0.9) / SR) * np.sin(np.pi * d / 0.9) ** 2
place(tone, 2.2, 0.035)


# --- UI pops & clicks --------------------------------------------------------
def pop(freq=520, d_=0.18):
    d = tt(d_)
    f = freq * (1 + 1.2 * np.exp(-d * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * 30) * np.clip(d / 0.002, 0, 1)


def click():
    d = tt(0.05)
    return hp(rng.normal(0, 1, len(d)), 2500) * np.exp(-d * 220) * 0.6 + \
        np.sin(2 * np.pi * 2200 * d) * np.exp(-d * 160) * 0.4


def pluck(freq, d_=0.6):
    d = tt(d_)
    x = sum(np.sin(2 * np.pi * freq * k * d) / k ** 1.4 for k in range(1, 5))
    return x * np.exp(-d * 9) * np.clip(d / 0.003, 0, 1)


def bell(freq=1046.5, d_=2.0):
    d = tt(d_)
    mod = np.sin(2 * np.pi * freq * 1.4 * d) * 2.2 * np.exp(-d * 3)
    x = np.sin(2 * np.pi * freq * d + mod) * np.exp(-d * 2.6)
    x += 0.4 * np.sin(2 * np.pi * freq * 2.76 * d) * np.exp(-d * 5)
    return x * np.clip(d / 0.002, 0, 1)


place(pop(480), 2.75, 0.18, -0.3)
place(pop(560), 2.9, 0.18, 0.0)
place(pop(640), 3.05, 0.18, 0.3)

for t0, g in [(4.0, 1.0), (9.6, 0.6)]:
    place(click(), t0, 0.22 * g, -0.3)
    place(pluck(784), t0 + 0.06, 0.10 * g, -0.3)
    place(pluck(1175), t0 + 0.11, 0.06 * g, -0.3)
for t0, g in [(4.8, 1.0), (10.4, 0.6)]:
    place(click(), t0, 0.22 * g)
    place(pluck(659), t0 + 0.06, 0.10 * g)
    place(pluck(988), t0 + 0.12, 0.07 * g)
for t0, g in [(5.6, 1.0), (11.2, 0.6)]:
    place(click(), t0, 0.2 * g, 0.3)
    place(bell(1046.5), t0 + 0.05, 0.09 * g, 0.3)
    place(bell(1318.5), t0 + 0.17, 0.06 * g, 0.3)

# light sweeps across the logo
for t0 in (6.5, 11.5):
    place(sweep_noise(1.1, 3000, 9000, lambda u: np.sin(np.pi * u) ** 2), t0, 0.035)

# --- reverb, master ---------------------------------------------------------
ir = reverb_ir()
wet = np.stack([signal.fftconvolve(mix[:, c], ir[:, c])[:N] for c in range(2)], 1)
out = mix + wet * 0.22
out = hp(out.T, 25).T
fade = np.clip((DUR - t) / 0.6, 0, 1) ** 2
out *= fade[:, None]
peak = np.abs(out).max()
out = out / peak * 10 ** (-3 / 20)  # -3 dBFS peak, subtle overall
out = np.tanh(out * 1.1) / np.tanh(1.1)
wavfile.write(os.path.join(OUT, "sfx.wav"), SR, (out * 32767 * 0.85).astype(np.int16))
print("peak", peak, "rms dB", 20 * np.log10(np.sqrt((out ** 2).mean())))
