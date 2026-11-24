"""Opening frames: swap menu frames for pass-B equivalents, inpaint the static Instagram rail icons."""
import sys, os, shutil, numpy as np, cv2
WD = sys.argv[1]
B = f"{WD}/base"
os.makedirs(f"{WD}/base_orig", exist_ok=True)
def path(k): return f"{B}/{k+1:04d}.jpg"
for k in range(0, 60):
    if not os.path.exists(f"{WD}/base_orig/{k+1:04d}.jpg"): shutil.copy(path(k), f"{WD}/base_orig/{k+1:04d}.jpg")
def orig(k): return cv2.imread(f"{WD}/base_orig/{k+1:04d}.jpg")
for k in range(0, 60): shutil.copy(f"{WD}/base_orig/{k+1:04d}.jpg", path(k))
# 2) static-UI mask from caption-free frames (k=1..7: UI on, caption not yet)
g = np.stack([cv2.cvtColor(orig(k), cv2.COLOR_BGR2GRAY) for k in range(1, 8)])
static = g.min(0) > 185
m = np.zeros_like(static)
S = 1080 / 886
def rect(x0, y0, x1, y1):  # source coords -> plate coords
    return int(x0 * S), int((y0 - 146) * S), int(x1 * S), int((y1 - 146) * S)
for r in [rect(780, 860, 860, 1710), rect(800, 160, 880, 230), rect(20, 160, 100, 230)]:
    x0, y0, x1, y1 = r; y0 = max(0, y0); m[y0:y1, x0:x1] = static[y0:y1, x0:x1]
for r in [rect(810, 150, 875, 225), rect(30, 150, 100, 225)]:
    x0, y0, x1, y1 = r; y0 = max(0, y0); m[y0:y1, x0:x1] = True
m = cv2.dilate(m.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
cv2.imwrite(f"{WD}/an/railmask.png", m)
for k in range(0, int(sys.argv[2])):
    im = cv2.imread(path(k))
    out = cv2.inpaint(im, m, 5, cv2.INPAINT_TELEA)
    cv2.imwrite(path(k), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
print("mask px", int((m > 0).sum()))
