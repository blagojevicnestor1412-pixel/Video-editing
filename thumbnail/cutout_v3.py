"""Cut-out v3: per-person high-resolution segmentation.

Each person's head + shoulders is cut from the photo, enlarged ~3x (Lanczos) and segmented on its own
with BiRefNet-portrait, so the model sees hair/ears/hands at high resolution. The windows are blended
into one matte (feathered), the body/legs come from a whole-group pass. Foreground colours are then
re-estimated (pymatting) so no backdrop colour sits on the edges. No generative editing of people.
Writes assets/people_alpha_v3.png and assets/people_fg_v3.png (photo coordinates).
"""
import os

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
DBG = "/tmp"

src = Image.open(os.path.join(A, "source_photo.png")).convert("RGB").crop((0, 500, 1179, 2060))
photo = np.array(src).astype(np.float64) / 255
PH, PW = photo.shape[:2]

from rembg import new_session, remove  # noqa: E402

import onnxruntime as ort  # noqa: E402
from rembg.sessions import sessions_class  # noqa: E402

_opts = ort.SessionOptions()
_opts.enable_cpu_mem_arena = False      # release memory between windows (avoids OOM)
_opts.enable_mem_pattern = False
_cls = [c for c in sessions_class if c.name() == "birefnet-portrait"][0]
sess = _cls("birefnet-portrait", _opts)


def seg_window(x0, y0, size, model_px=1024):
    """segment a square window (photo coords) at model resolution, return mask at window size."""
    x1, y1 = x0 + size, y0 + size
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(PW, x1), min(PH, y1)
    tile = np.zeros((size, size, 3), np.uint8)
    tile[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0] = np.array(src)[cy0:cy1, cx0:cx1]
    big = Image.fromarray(tile).resize((model_px, model_px), Image.LANCZOS)
    m = remove(big, session=sess, only_mask=True)
    m = np.array(m.resize((size, size), Image.BOX)).astype(np.float64) / 255
    out = np.zeros((PH, PW))
    out[cy0:cy1, cx0:cx1] = m[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    win = np.zeros((PH, PW))
    # feathered weight: 1 in the middle, falling to 0 at the window border
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    e = np.minimum.reduce([xx, yy, size - 1 - xx, size - 1 - yy]) / (size * 0.18)
    w = np.clip(e, 0, 1) ** 2
    win[cy0:cy1, cx0:cx1] = w[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    return out, win


# 1) whole group pass (body, legs) at ~1:1
X0, X1, Y0, Y1 = 100, 1150, 380, 1320
gm, gw = seg_window(X0, Y0 - (X1 - X0 - (Y1 - Y0)) // 2, X1 - X0)
group = gm
print("group", flush=True)

# 2) per-person head/shoulder windows (photo coords of each head centre) + the right hand
heads = [(377, 612), (505, 567), (617, 590), (727, 557), (868, 548)]
acc = np.zeros((PH, PW))
wsum = np.zeros((PH, PW))
for hx, hy in heads:
    size = 300
    m, w = seg_window(int(hx - size / 2), int(hy - 90), size)
    acc += m * w
    wsum += w
    print("head", hx, hy, flush=True)
for (cx, cy, size) in [(960, 860, 240), (330, 820, 260), (620, 800, 280)]:   # hands / arms
    m, w = seg_window(int(cx - size / 2), int(cy - size / 2), size)
    acc += m * w
    wsum += w
detail = acc / np.maximum(wsum, 1e-6)
wd = np.clip(wsum, 0, 1)
mask = detail * wd + group * (1 - wd)

# keep the main blob only (no floating backdrop bits)
lab, n = nd.label(mask > 0.5)
sizes = nd.sum(np.ones_like(mask), lab, range(1, n + 1))
keep = nd.binary_dilation(lab == (np.argmax(sizes) + 1), iterations=6)
mask = np.clip(mask * keep, 0, 1)
Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(DBG, "v3_mask_raw.png"))

# 3) spill-free foreground colours on the edges
from pymatting import estimate_foreground_ml  # noqa: E402

img = photo[Y0:Y1, X0:X1]
al = mask[Y0:Y1, X0:X1]
fgc = np.clip(estimate_foreground_ml(img, al), 0, 1)
full_f = photo.copy()
full_f[Y0:Y1, X0:X1] = fgc
Image.fromarray((mask * 255 + 0.5).astype(np.uint8)).save(os.path.join(A, "people_alpha_v3.png"))
Image.fromarray((full_f * 255 + 0.5).astype(np.uint8)).save(os.path.join(A, "people_fg_v3.png"))
print("saved")
