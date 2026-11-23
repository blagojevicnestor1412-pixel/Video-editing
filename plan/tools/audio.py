"""Builds the reel's soundtrack: edited dialogue, original music bed, synthesized SFX, mix.
Usage: python3 -I audio.py <workdir>"""
import sys, subprocess, numpy as np
from scipy import signal
from scipy.io import wavfile

W = sys.argv[1]
SR = 48000
TOTAL = 19.5
N = int(TOTAL * SR)
SEGS = [(0.00, 1.62), (2.00, 4.95), (5.25, 8.75), (9.02, 12.25), (12.60, 16.55), (16.82, 19.07)]
rng = np.random.default_rng(3)

def t_(d): return np.arange(int(d * SR)) / SR
def bp(x, lo, hi, o=2): return signal.sosfilt(signal.butter(o, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, "highpass", fs=SR, output="sos"), x)
def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, "lowpass", fs=SR, output="sos"), x)
def db(v): return 10 ** (v / 20)
def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
def place(buf, x, at, gain_db=0.0):
    i = int(at * SR)
    if i >= len(buf): return
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += x * db(gain_db)

# ------------------------------------------------------------------ dialogue
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{W}/source.mov", "-ac", "1", "-ar", str(SR),
                "-af", "highpass=f=80,afftdn=nr=10:nf=-40,equalizer=f=3000:t=q:w=1.2:g=2.5,equalizer=f=250:t=q:w=1:g=-2,"
                       "deesser=i=0.3,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=3",
                f"{W}/dlg_src.wav"], check=True)
sr, src = wavfile.read(f"{W}/dlg_src.wav"); src = src.astype(np.float32) / 32768
dlg = np.zeros(N, np.float32)
pos = 0
fade = int(0.008 * SR)
for a, b in SEGS:
    seg = src[int(a * SR): int(b * SR)].copy()
    seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    dlg[pos: pos + len(seg)] += seg[: N - pos]
    pos += len(seg)
dlg_end = pos / SR

# ------------------------------------------------------------------ instruments
def e808(f, dur=0.7, drive=2.0):
    t = t_(dur)
    fr = f * (1 + 1.6 * np.exp(-t / 0.025))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.sin(ph) * np.exp(-t / (dur * 0.45))
    return np.tanh(x * drive) / np.tanh(drive)

def kick():
    t = t_(0.35); fr = 48 * (1 + 3 * np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.09)
    x[:200] += rng.normal(0, 0.4, 200) * np.linspace(1, 0, 200)
    return np.tanh(2 * x)

def hat(open_=False):
    d = 0.18 if open_ else 0.045
    x = hp(rng.normal(0, 1, int(d * SR)), 7000, 4) * np.exp(-t_(d) / (d / 4))
    return norm(x)

def clap():
    out = np.zeros(int(0.3 * SR))
    for k, off in enumerate([0, 0.011, 0.022]):
        b = bp(rng.normal(0, 1, int(0.2 * SR)), 900, 2600) * np.exp(-t_(0.2) / (0.012 if k < 2 else 0.06))
        i = int(off * SR); out[i:i + len(b)] += b[: len(out) - i]
    return norm(out)

def pad(freqs, dur, cutoff=900):
    t = t_(dur); x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0, 0.11):
            ff = f * 2 ** (det / 12)
            x += signal.sawtooth(2 * np.pi * ff * t + rng.uniform(0, 6))
    x = lp(x, cutoff, 2)
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.5)
    return norm(x) * env

# ------------------------------------------------------------------ music (96 BPM, D minor)
BPM = 96; B = 60 / BPM
mus = np.zeros(N + SR, np.float32)
D2, F2, Bb1, A1, C2 = 73.42, 87.31, 58.27, 55.0, 65.41
bass_prog = [D2, D2, Bb1, C2]                  # per 2-bar (8 beats) block
place(mus, pad([146.83, 174.61, 220.0], 11.25, 700), 0, -14)          # Dm
place(mus, pad([116.54, 146.83, 174.61], 6.25, 1100), 11.25, -13)     # Bb
place(mus, pad([146.83, 174.61, 220.0, 293.66], 2.6, 1400), 17.5, -12)
nbeats = int(17.5 / B)
for bt in range(nbeats):
    at = bt * B
    bar_beat = bt % 4
    sect2 = at >= 11.25
    if bar_beat == 0 or (bar_beat == 2 and bt % 8 == 6):
        place(mus, kick(), at, -6)
        place(mus, e808(bass_prog[(bt // 8) % 4]), at, -7)
    if sect2 and bar_beat == 2:
        place(mus, clap(), at, -12)
    # hats: 8ths, 16th roll before section changes
    for h in (0, 0.5):
        place(mus, hat(), at + h * B, -22 if h else -19)
    if bt % 8 == 7:
        for r in range(4):
            place(mus, hat(), at + 0.5 * B + r * B / 8, -24 + r)
# riser into the final hit
rt = t_(2.2)
riser = bp(rng.normal(0, 1, len(rt)), 400, 6000) * (rt / rt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 600 * (rt / rt[-1]) ** 2) / SR) * (rt / rt[-1]) ** 2
place(mus, riser, 17.5 - 2.2, -20)
# final hit + ring out
place(mus, e808(D2, 2.0, 2.5), 17.5, -4)
place(mus, kick(), 17.5, -4)
cr = hp(rng.normal(0, 1, int(2 * SR)), 3000) * np.exp(-t_(2) / 0.5)
place(mus, cr, 17.5, -20)
mus = mus[:N]
# fade tail at very end
mus[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))

# ------------------------------------------------------------------ SFX
def whoosh(d=0.45, lo=300, hi=4000, rev=False):
    t = t_(d); x = rng.normal(0, 1, len(t))
    env = np.sin(np.pi * t / d) ** 2
    if rev: env = (t / d) ** 3
    # sweep: blend lowpassed / highpassed versions
    a, b = lp(x, lo * 3), bp(x, lo * 2, hi)
    k = t / d if not rev else (t / d) ** 2
    return norm((a * (1 - k) + b * k) * env)

def subhit(f=45, d=1.0):
    t = t_(d); fr = f * (1 + 2 * np.exp(-t / 0.04))
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.35))

def snap():
    t = t_(0.12); x = rng.normal(0, 1, len(t)) * np.exp(-t / 0.008)
    x += 0.6 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.01)
    return norm(hp(x, 1200))

def pop(f0=500, f1=1100):
    t = t_(0.09); fr = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.025)

def tick(f=3500):
    t = t_(0.04); return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006)

def ding(f=1318.5):
    t = t_(1.2)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (0.5 / m)) for m, a in [(1, 1), (2.01, 0.4), (3.02, 0.2)])
    return norm(x)

def ping(f):
    t = t_(0.22)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.06) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / 0.04) * (t > 0.05)
    return norm(x)

def stamp():
    t = t_(0.25); x = np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.04)
    x += lp(rng.normal(0, 1, len(t)), 2500) * np.exp(-t / 0.015) * 0.7
    return norm(np.tanh(2 * x))

def rustle(d=0.5):
    t = t_(d); x = bp(rng.normal(0, 1, len(t)), 2000, 9000)
    am = (rng.random(len(t)) < 0.004).astype(float); am = signal.lfilter([1], [1, -0.995], am)
    return norm(x * np.clip(am, 0, 1) * np.sin(np.pi * t / d))

def shatter():
    out = np.zeros(int(1.2 * SR))
    out[: int(0.3 * SR)] += hp(rng.normal(0, 1, int(0.3 * SR)), 2500) * np.exp(-t_(0.3) / 0.05)
    for _ in range(70):
        at = rng.exponential(0.18); f = rng.uniform(2500, 9000)
        t = t_(0.08); s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012) * rng.uniform(0.2, 1)
        i = int(at * SR)
        if i + len(s) < len(out): out[i:i + len(s)] += s
    return norm(out)

def applause(d=1.4):
    out = np.zeros(int(d * SR))
    for _ in range(int(d * 140)):
        at = rng.uniform(0, d - 0.05); t = t_(0.03)
        c = bp(rng.normal(0, 1, len(t)), 800, 3500) * np.exp(-t / 0.006) * rng.uniform(0.3, 1)
        i = int(at * SR); out[i:i + len(c)] += c
    env = np.minimum(1, t_(d) / 0.25) * np.minimum(1, (d - t_(d)) / 0.5)
    return norm(out * env)

def whistle(d=0.35):
    t = t_(d); f = 2900 + 60 * np.sin(2 * np.pi * 28 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05)
    return x + 0.15 * bp(rng.normal(0, 1, len(t)), 2500, 3500)

def drone(d):
    t = t_(d); x = np.sin(2 * np.pi * 41.2 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.3)
    return x * (t / d) ** 1.5

def hum(d):
    t = t_(d); x = np.sin(2 * np.pi * 110 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t)) + 0.3 * bp(rng.normal(0, 1, len(t)), 200, 900)
    return norm(x) * np.minimum(1, t / 0.2) * np.minimum(1, (d - t) / 0.1)

fx = np.zeros(N + 3 * SR, np.float32)
place(fx, subhit(), 0.0, -8); place(fx, whoosh(0.6, 200, 3000), 0.0, -16)
place(fx, rustle(0.45), 1.60, -20); place(fx, stamp(), 1.82, -12); place(fx, stamp(), 2.22, -12); place(fx, pop(700, 1400), 2.32, -16)
place(fx, whoosh(0.3, 400, 6000), 2.62, -18)
place(fx, hum(0.8), 3.05, -24); place(fx, whoosh(0.35, 200, 5000, rev=True), 3.50, -14)
place(fx, stamp(), 3.88, -12); place(fx, subhit(55, 0.6), 4.72, -10); place(fx, whoosh(0.25, 500, 7000), 4.70, -18)
place(fx, snap(), 5.52, -10); place(fx, whoosh(0.2, 800, 8000), 5.50, -18)
place(fx, whoosh(0.3, 300, 6000), 5.93, -14)
for k in range(6): place(fx, ping(1300 + 120 * k), 6.15 + k * 5 / 30, -22)
place(fx, applause(1.3), 6.65, -26)
place(fx, whoosh(0.22, 600, 6000), 7.70, -20)
place(fx, tick(4200), 7.98, -16); place(fx, tick(2000), 8.35, -18); place(fx, tick(2400), 8.42, -18); place(fx, whistle(), 8.62, -24)
place(fx, drone(2.25), 9.05, -20)
place(fx, whoosh(1.2, 300, 8000, rev=True), 10.10, -22)
place(fx, shatter(), 11.30, -12); place(fx, subhit(42, 1.2), 11.30, -7)
place(fx, pop(), 11.50, -14); place(fx, tick(), 11.62, -18)
place(fx, pop(), 12.70, -14); place(fx, tick(), 12.82, -18)
place(fx, ding(), 13.30, -18)
place(fx, whoosh(0.35, 400, 6000), 14.98, -18)
place(fx, snap(), 17.50, -12); place(fx, subhit(40, 1.6), 17.50, -9); place(fx, whoosh(0.4, 300, 7000), 17.62, -18)
place(fx, pop(600, 1300), 18.50, -14)
fx = fx[:N]

# ------------------------------------------------------------------ duck music under dialogue
env = np.abs(dlg)
win = int(0.08 * SR)
env = np.convolve(env, np.ones(win) / win, mode="same")
speech = (env > db(-38)).astype(np.float32)
# attack 40 ms / release 300 ms smoothing
g = np.zeros_like(speech); a_at, a_rl = np.exp(-1 / (0.04 * SR)), np.exp(-1 / (0.3 * SR)); prev = 0.0
for i in range(0, len(speech), 48):  # 1 ms steps
    tgt = speech[i]; c = a_at ** 48 if tgt > prev else a_rl ** 48
    prev = tgt + (prev - tgt) * c; g[i:i + 48] = prev
duck = db(-10) * g + (1 - g)

mix_music = mus * duck
wavfile.write(f"{W}/dlg.wav", SR, (np.clip(dlg, -1, 1) * 32767).astype(np.int16))
# Stems at nominal level; music bed sits well under dialogue
mus_n = mix_music / (np.max(np.abs(mus)) + 1e-9) * db(-8)
fx_n = fx  # already scaled per event
mix = dlg + mus_n + fx_n
wavfile.write(f"{W}/mix_pre.wav", SR, (np.clip(mix / max(1, np.max(np.abs(mix))), -1, 1) * 32767).astype(np.int16))
wavfile.write(f"{W}/music.wav", SR, (np.clip(mus_n, -1, 1) * 32767).astype(np.int16))
wavfile.write(f"{W}/sfx.wav", SR, (np.clip(fx_n, -1, 1) * 32767).astype(np.int16))
print("dialogue ends at", round(dlg_end, 3))
