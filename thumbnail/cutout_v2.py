"""Cut-out v2: higher-resolution segmentation + closed-form alpha matting + foreground colour estimation.

1. crop the group from the photo so the model sees the people at ~1:1 resolution
2. BiRefNet (portrait + general) -> rough mask
3. trimap from the mask -> closed-form alpha matting (pymatting) for real soft edges (hair, ears)
4. multi-level foreground estimation -> edge colours without backdrop spill (logos/letters behind)
Writes assets/people_alpha_v2.png and assets/people_fg_v2.png in photo coordinates.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")

src = Image.open(os.path.join(A, "source_photo.png")).convert("RGB").crop((0, 500, 1179, 2060))
photo = np.array(src).astype(np.float64) / 255
PH, PW = photo.shape[:2]

# group region (heads to hips + margin)
X0, X1, Y0, Y1 = 100, 1150, 380, 1320
crop = src.crop((X0, Y0, X1, Y1))
cw, ch = crop.size
side = max(cw, ch)
sq = Image.new("RGB", (side, side))
sq.paste(crop, ((side - cw) // 2, (side - ch) // 2))
arr = np.array(sq)
# replicate edges into the padding instead of black bars
padx, pady = (side - cw) // 2, (side - ch) // 2
if pady:
    arr[:pady] = arr[pady:pady + 1]
    arr[pady + ch:] = arr[pady + ch - 1:pady + ch]
if padx:
    arr[:, :padx] = arr[:, padx:padx + 1]
    arr[:, padx + cw:] = arr[:, padx + cw - 1:padx + cw]
sq = Image.fromarray(arr)

from rembg import new_session, remove  # noqa: E402

masks = []
for model in ("birefnet-portrait", "birefnet-general"):
    sess = new_session(model)
    m = np.array(remove(sq, session=sess, only_mask=True)).astype(np.float64) / 255
    masks.append(m[pady:pady + ch, padx:padx + cw])
    Image.fromarray((masks[-1] * 255).astype(np.uint8)).save(os.path.join("/tmp", "build_mask_" + model + ".png"))
    print("mask", model, flush=True)

# the portrait model is used (it knows what a person is); the general mask is saved for comparison
mask = masks[0]
lab, n = nd.label(mask > 0.5)
sizes = nd.sum(np.ones_like(mask), lab, range(1, n + 1))
keep = nd.binary_dilation(lab == (np.argmax(sizes) + 1), iterations=8)
mask = mask * keep

# trimap
fg = nd.binary_erosion(mask > 0.92, iterations=4)
bg = ~nd.binary_dilation(mask > 0.08, iterations=4)
trimap = np.full(mask.shape, 0.5)
trimap[fg] = 1.0
trimap[bg] = 0.0
Image.fromarray((trimap * 255).astype(np.uint8)).save(os.path.join("/tmp", "build_trimap.png"))

from pymatting import estimate_alpha_cf, estimate_foreground_ml  # noqa: E402

img = photo[Y0:Y1, X0:X1]
alpha = estimate_alpha_cf(img, trimap)
alpha = np.clip(alpha, 0, 1)
print("alpha done", flush=True)
fgc = estimate_foreground_ml(img, alpha)
fgc = np.clip(fgc, 0, 1)
print("foreground done", flush=True)

full_a = np.zeros((PH, PW))
full_a[Y0:Y1, X0:X1] = alpha
full_f = photo.copy()
full_f[Y0:Y1, X0:X1] = fgc
Image.fromarray((full_a * 255 + 0.5).astype(np.uint8)).save(os.path.join(A, "people_alpha_v2.png"))
Image.fromarray((full_f * 255 + 0.5).astype(np.uint8)).save(os.path.join(A, "people_fg_v2.png"))
print("saved")
