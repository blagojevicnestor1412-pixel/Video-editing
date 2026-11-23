import sys, os, numpy as np
from PIL import Image, ImageFilter
from rembg import remove, new_session
import scipy.ndimage as nd
W = sys.argv[1]
s = new_session("u2net_human_seg")
need = set(range(0, 50)) | set(range(298, 370)) | {318}
need |= {round(k / 12 * 30) for k in range(24, 40)}
for i in sorted(need):
    out = f"{W}/mask/{i:04d}.png"
    if os.path.exists(out): continue
    im = Image.open(f"{W}/base/{i+1:04d}.jpg").convert("RGB").resize((540, 960), Image.LANCZOS)
    m = np.asarray(remove(im, session=s, only_mask=True)) > 128
    lab, n = nd.label(m)
    if n > 1:
        sz = nd.sum(m, lab, range(1, n + 1)); m = lab == 1 + int(np.argmax(sz))
    Image.fromarray((m * 255).astype(np.uint8)).save(out)
print("masks", len(need))
