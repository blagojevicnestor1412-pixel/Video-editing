import sys, json, numpy as np
from PIL import Image
sys.path.insert(0, sys.argv[2]); from capdata import BLOCKS
WD = sys.argv[1]
N = len([1]) and 1970
cache = {}
def wm(k):
    if k not in cache:
        a = np.asarray(Image.open(f"{WD}/base/{k+1:04d}.jpg").convert("RGB").resize((540, 960)), np.int16)
        cache[k] = (a.mean(2) > 200) & ((a.max(2) - a.min(2)) < 50)
    return cache[k]
res = []
for bi, ((a, b), lines) in enumerate(BLOCKS):
    for (x0, y0, x1, y1), txt, kw in lines:
        sl = (slice(y0 // 2, y1 // 2), slice(x0 // 2, x1 // 2))
        ks = list(range(round(a * 30), round(b * 30)))
        R = np.mean([wm(k)[sl] for k in ks], 0) > 0.85
        nR = max(1, R.sum())
        def score(k): return (wm(k)[sl] & R).sum() / nR
        k0 = ks[0]
        while k0 > 0 and score(k0 - 1) > 0.45: k0 -= 1
        k1 = ks[-1]
        while k1 < 1969 and score(k1 + 1) > 0.45: k1 += 1
        res.append(dict(block=bi, rect=[x0, y0, x1, y1], text=txt, kw=kw, k0=k0, k1=k1, n=int(nR)))
        print(bi, f"{k0/30:6.2f}-{k1/30:6.2f}", int(nR), txt)
json.dump(res, open(f"{WD}/an/captimes.json", "w"), ensure_ascii=False)
