"""LEAMUN reel soundtrack: the reel's own mix (already has music) + subtle SFX on our graphics + end-card sting."""
import sys, numpy as np
from scipy import signal
from scipy.io import wavfile
REF, W = sys.argv[1], sys.argv[2]
SR = 48000; BODY = 65.65; TOTAL = BODY + 2.5; N = int(TOTAL * SR)
rng = np.random.default_rng(3)
src = open(REF).read()
exec(src.split("# ------------------------------------------------------------------ dialogue")[0].split("rng = np.random.default_rng(3)")[1])
exec(src.split("# ------------------------------------------------------------------ instruments")[1].split("# ------------------------------------------------------------------ music")[0])
exec(src.split("# ------------------------------------------------------------------ SFX")[1].split("fx = np.zeros")[0])
sr, d = wavfile.read(f"{W}/dlg_edit.wav"); d = d.astype(np.float32) / 32768
mix = np.zeros((N, 2), np.float32); n = min(len(d), int(BODY * SR)); mix[:n] = d[:n]
f = int(0.35 * SR); mix[n - f:n] *= np.linspace(1, 0.15, f)[:, None]          # dip the reel audio under the end card
fx = np.zeros(N + 3 * SR, np.float32)
place(fx, whoosh(0.6, 200, 4000), 0.0, -20); place(fx, subhit(48, 0.9), 0.05, -16)
place(fx, whoosh(0.4, 300, 6000), 1.38, -20)
for k in range(4): place(fx, pop(600 + 90 * k, 1300), 3.05 + 0.3 * k, -24)
place(fx, whoosh(0.3, 400, 6000), 7.5, -22); place(fx, stamp(), 7.98, -22)          # pin drop
place(fx, pop(), 11.0, -22)
for t in (14.05, 14.85): place(fx, whoosh(0.18, 800, 8000), t, -24); place(fx, tick(3200), t + 0.3, -22)
for t in (16.10, 16.75): place(fx, pop(600, 1300), t, -22); place(fx, tick(2800), t + 0.12, -24)
place(fx, whoosh(0.5, 300, 7000), 18.25, -22); place(fx, ding(1568), 18.8, -28)
place(fx, snap(), 21.0, -20)
for k in range(5): place(fx, tick(2600), 21.8 + k * 0.45, -26)
place(fx, whoosh(0.3, 400, 6000), 32.3, -24)
place(fx, stamp(), 35.38, -16); place(fx, subhit(55, 0.5), 35.38, -18)
place(fx, ding(1046), 38.6, -24)
place(fx, pop(), 40.3, -22)
place(fx, pop(600, 1300), 42.4, -22); place(fx, pop(700, 1400), 42.9, -22)
place(fx, whoosh(0.35, 300, 6000), 53.92, -22)
place(fx, whoosh(0.4, 200, 4000), 56.5, -24)
for k in range(3): place(fx, ping(1800 + 200 * k), 58.9 + k * 0.4, -30)
place(fx, pop(), 61.0, -22)
place(fx, whoosh(0.35, 400, 6000), 64.0, -22)
place(fx, whoosh(0.8, 150, 3000, rev=True), BODY - 0.6, -18); place(fx, subhit(45, 1.4), BODY, -12)
place(fx, ding(1318.5), BODY + 0.5, -22); place(fx, pop(600, 1300), BODY + 0.8, -18)
fx = fx[:N]
mix += fx[:, None] * 0.9
wavfile.write(f"{W}/mix_pre.wav", SR, (np.clip(mix / max(1, np.abs(mix).max()), -1, 1) * 32767).astype(np.int16))
print("ok", TOTAL)
