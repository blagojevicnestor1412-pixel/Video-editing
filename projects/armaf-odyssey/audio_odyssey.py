"""Soundtrack for the Astarta Black Friday reel. Reuses instrument/SFX generators from the skill's reference audio.py.
Usage: python3 -I audio_astarta.py <ref_audio.py> <workdir>"""
import sys, subprocess, numpy as np
from scipy import signal
from scipy.io import wavfile

REF, W = sys.argv[1], sys.argv[2]
SR = 48000
TOTAL = 45.33
N = int(TOTAL * SR)
rng = np.random.default_rng(3)

src_txt = open(REF).read()
# helpers (t_, bp, hp, lp, db, norm, place)
exec(src_txt.split("# ------------------------------------------------------------------ dialogue")[0].split("rng = np.random.default_rng(3)")[1])
# instruments
exec(src_txt.split("# ------------------------------------------------------------------ instruments")[1].split("# ------------------------------------------------------------------ music")[0])
# sfx generators (defs only, stop before the placement list)
exec(src_txt.split("# ------------------------------------------------------------------ SFX")[1].split("fx = np.zeros")[0])

# ------------------------------------------------------------------ dialogue (no cuts, just cleanup)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{W}/source.mov", "-t", str(TOTAL), "-ac", "1", "-ar", str(SR),
                "-af", "highpass=f=80,afftdn=nr=8:nf=-40,equalizer=f=3000:t=q:w=1.2:g=2,equalizer=f=250:t=q:w=1:g=-1.5,"
                       "deesser=i=0.3,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2",
                f"{W}/dlg_src.wav"], check=True)
sr, src = wavfile.read(f"{W}/dlg_src.wav"); src = src.astype(np.float32) / 32768
dlg = np.zeros(N, np.float32); dlg[:min(N, len(src))] = src[:N]
f = int(0.25 * SR); dlg[-f:] *= np.linspace(1, 0, f)

# ------------------------------------------------------------------ music: soft 100 BPM bed, A minor-ish, no drops
BPM = 100; B = 60 / BPM
mus = np.zeros(N + 2 * SR, np.float32)
chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]  # Am F C G
bass = [55.0, 43.65, 65.41, 49.0]
bar = 4 * B
nbars = int(TOTAL / bar) + 1
for k in range(nbars):
    at = k * bar
    place(mus, pad(chords[k % 4], bar + 0.4, 1000), at, -15)
    place(mus, e808(bass[k % 4], 0.9, 1.6), at, -11)
for bt in range(int(TOTAL / B)):
    at = bt * B
    if at < 0.8: continue                       # let the hook breathe
    if bt % 2 == 0: place(mus, kick(), at, -12)
    if bt % 4 == 2: place(mus, clap(), at, -21)
    place(mus, hat(), at + 0.5 * B, -25)
mus = mus[:N]
mus[:int(0.6 * SR)] *= np.linspace(0, 1, int(0.6 * SR))
fo = int(0.5 * SR); mus[-fo:] *= np.linspace(1, 0, fo)

# ------------------------------------------------------------------ SFX (subtle)
fx = np.zeros(N + 3 * SR, np.float32)
place(fx, whoosh(0.5, 200, 3000), 0.0, -22)
for k in range(4): place(fx, pop(500 + 120 * k, 1100 + 150 * k), 1.30 + k * 0.1, -22)
place(fx, whoosh(0.3, 400, 5000), 5.05, -24)
for t in (6.33, 12.60, 21.87, 29.47, 39.10): place(fx, whoosh(0.3, 300, 6000), t - 0.12, -20)
for t in (6.37, 14.67, 25.23, 33.63): place(fx, stamp(), t, -22); place(fx, tick(3200), t + 0.25, -24)
place(fx, whoosh(0.9, 150, 2000, rev=True), 11.55, -24)
for k in range(3): place(fx, ping(2400 + 300 * k), 13.86 + k * 0.12, -28)
place(fx, whoosh(0.25, 600, 7000), 16.48, -22); place(fx, ding(1760), 16.75, -26)
place(fx, pop(), 20.40, -18); place(fx, pop(650, 1300), 20.80, -18)
place(fx, pop(500, 1200), 21.95, -18); place(fx, ding(), 22.05, -26)
for k in range(7): place(fx, pop(700 + 60 * k, 1500), 28.28 + k / 15, -24)
place(fx, whoosh(0.3, 400, 5000), 30.05, -22)
place(fx, tick(2600), 30.24, -20); place(fx, tick(3000), 31.50, -20)
place(fx, pop(), 35.96, -18)
place(fx, whoosh(0.5, 300, 6000, rev=True), 37.6, -22); place(fx, subhit(50, 0.6), 38.40, -14)
for k in range(4): place(fx, pop(600, 1300), 39.70 + k / 6, -22)
place(fx, pop(600, 1300), 42.30, -18); place(fx, tick(3000), 42.85, -18)
fx = fx[:N]

# ------------------------------------------------------------------ duck + mix
env = np.convolve(np.abs(dlg), np.ones(int(0.08 * SR)) / int(0.08 * SR), mode="same")
speech = (env > db(-38)).astype(np.float32)
g = np.zeros_like(speech); a_at, a_rl = np.exp(-1 / (0.04 * SR)), np.exp(-1 / (0.3 * SR)); prev = 0.0
for i in range(0, len(speech), 48):
    tgt = speech[i]; c = a_at ** 48 if tgt > prev else a_rl ** 48
    prev = tgt + (prev - tgt) * c; g[i:i + 48] = prev
duck = db(-10) * g + (1 - g)
mus_n = mus * duck / (np.max(np.abs(mus)) + 1e-9) * db(-14)
mix = dlg + mus_n + fx
wavfile.write(f"{W}/mix_pre.wav", SR, (np.clip(mix / max(1, np.max(np.abs(mix))), -1, 1) * 32767).astype(np.int16))
print("ok", TOTAL)
