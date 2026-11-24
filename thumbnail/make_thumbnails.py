"""BJJ competition vlog thumbnails - classic compositing (no generative edits of people).

People are cut out of the original photo with a segmentation matte, the original
backdrop is reused (people painted out, blurred, darkened) and everything is graded
together. Output: 3 JPG variants, 1920x1080, < 2 MB.
"""
import os

import cv2
import numpy as np
import skia
from PIL import Image, ImageFilter
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080

FONTS = {
    "anton": skia.Typeface.MakeFromFile(os.path.join(A, "fonts", "Anton_400Regular.ttf")),
    "montserrat": skia.Typeface.MakeFromFile(os.path.join(A, "fonts", "Montserrat_900Black.ttf")),
}


def ss(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ source
src = Image.open(os.path.join(A, "source_photo.png")).convert("RGB")
photo = np.array(src.crop((0, 500, 1179, 2060))).astype(np.float32) / 255  # strip phone UI / black bars
PH, PW = photo.shape[:2]
matte = np.array(Image.open(os.path.join(A, "people_mask_photo.png")).convert("L")).astype(np.float32) / 255

# keep only the big connected people blob (drops stray bits of backdrop)
lab, n = nd.label(matte > 0.5)
sizes = nd.sum(np.ones_like(matte), lab, range(1, n + 1))
main = lab == (np.argmax(sizes) + 1)
main = nd.binary_dilation(main, iterations=6)
matte = matte * main
matte = ss(matte, 0.08, 0.92)

# remove backdrop pieces the matte caught: blue sponsor logo in the hair of the middle
# guy and the red sign fragment by the right guy's hand
R, G, B = photo[..., 0], photo[..., 1], photo[..., 2]
yy_, xx_ = np.mgrid[0:PH, 0:PW]
blue = (B - R > 0.08) & (B > 0.30)
box_head = (xx_ > 600) & (xx_ < 700) & (yy_ > 520) & (yy_ < 620)
red = ((R - G > 0.30) & (G < 0.36)) | ((R + G + B > 2.0) & (np.ptp(photo, axis=2) < 0.16))
box_hand = (xx_ > 950) & (xx_ < 990) & (yy_ > 835) & (yy_ < 890)
kill = nd.binary_dilation((blue & box_head) | (red & box_hand), iterations=2)
matte = matte * (1 - cv2.GaussianBlur(kill.astype(np.float32), (0, 0), 1.0))

# ------------------------------------------------------------------ background plate
hole = nd.binary_dilation(matte > 0.05, iterations=14).astype(np.uint8) * 255
bg8 = (photo * 255).astype(np.uint8)
small = cv2.resize(bg8, (PW // 2, PH // 2), interpolation=cv2.INTER_AREA)
small_hole = cv2.resize(hole, (PW // 2, PH // 2), interpolation=cv2.INTER_NEAREST)
plate_small = cv2.inpaint(small, small_hole, 12, cv2.INPAINT_TELEA)
plate = cv2.resize(plate_small, (PW, PH), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
hm = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 6)[..., None]
plate = photo * (1 - hm) + plate * hm


def place(img, scale, ox, oy, interp=cv2.INTER_LANCZOS4):
    """scale image and place so that photo pixel (0,0) lands at (ox, oy) on the canvas."""
    M = np.float32([[scale, 0, ox], [0, scale, oy]])
    return cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=cv2.BORDER_REFLECT)


def place_alpha(a, scale, ox, oy):
    M = np.float32([[scale, 0, ox], [0, scale, oy]])
    return cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def grade_background(bg):
    bg = cv2.GaussianBlur(bg, (0, 0), 9)
    lum = bg.mean(2, keepdims=True)
    bg = lum + (bg - lum) * 0.75          # mild desaturation
    bg = bg * 0.42                        # darken
    bg = bg * np.array([0.92, 0.98, 1.08])  # cool shadows
    return np.clip(bg, 0, 1)


def grade_people(p):
    # gentle contrast + warmth, keep skin natural
    p = np.clip(p, 0, 1)
    p = 0.5 + (p - 0.5) * 1.08
    p = p * np.array([1.03, 1.0, 0.97]) * 1.06
    return np.clip(p, 0, 1)


def sharpen(img, sigma=1.4, amount=0.7):
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    return np.clip(img + (img - blur) * amount, 0, 1)


def global_grade(img):
    # soft S-curve
    x = np.clip(img, 0, 1)
    x = x + 0.10 * (x - 0.5) * (1 - np.abs(2 * x - 1))
    # split tone: teal shadows, warm highlights
    lum = x.mean(2, keepdims=True)
    x = x + (1 - lum) * np.array([-0.012, 0.004, 0.018]) + lum * np.array([0.02, 0.008, -0.012])
    # vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    x = x * (1 - 0.30 * ss(d, 0.55, 1.45))[..., None]
    return np.clip(x, 0, 1)


def over(dst, rgb, a):
    a = a[..., None] if a.ndim == 2 else a
    return dst * (1 - a) + rgb * a


# ------------------------------------------------------------------ logos
def load_10p_logo():
    im = Image.open(os.path.join(A, "10p_belgrade_logo.png")).convert("RGB")
    a = np.array(im).astype(float)
    light = a.mean(2) > 225
    lab_, _ = nd.label(light)
    border = set(np.unique(np.concatenate([lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]]))) - {0}
    fg = nd.binary_fill_holes(~np.isin(lab_, list(border)))
    ys, xs = np.where(fg)
    box = (xs.min() - 2, ys.min() - 2, xs.max() + 3, ys.max() + 3)
    crop = im.crop(box)
    S = 4
    up = crop.resize((crop.width * S, crop.height * S), Image.LANCZOS)
    m = Image.fromarray((fg[box[1]:box[3], box[0]:box[2]] * 255).astype(np.uint8)).resize(up.size, Image.BICUBIC)
    m = m.filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: max(0, min(255, (v - 100) * 255 // 70)))
    rgba = np.dstack([np.array(up), np.array(m)]).astype(np.float32) / 255
    return rgba


def load_tatamy():
    rgba = np.array(Image.open(os.path.join(A, "tatamy_logo_from_banner.png")).convert("RGBA")).astype(np.float32) / 255
    # drop a tiny fleck left over from the banner fabric
    h, w = rgba.shape[:2]
    rgba[:100, int(w * 0.71):int(w * 0.76), 3] = 0
    return rgba


LOGO_10P = load_10p_logo()
LOGO_TAT = load_tatamy()


def paste_logo(canvas, rgba, x, y, width, keyline=False, shadow=0.55, blur=0.0, opacity=1.0):
    h = int(round(rgba.shape[0] * width / rgba.shape[1]))
    r = cv2.resize(rgba, (width, h), interpolation=cv2.INTER_AREA)
    pad = 60
    full = np.zeros((H + 2 * pad, W + 2 * pad, 4), np.float32)
    full[y + pad:y + pad + h, x + pad:x + pad + width] = r
    full = full[pad:pad + H, pad:pad + W]
    full_a = full[..., 3]
    full_rgb = full[..., :3]
    if blur > 0:  # premultiplied blur -> defocused, sits in the backdrop
        pm = cv2.GaussianBlur(full_rgb * full_a[..., None], (0, 0), blur)
        full_a = cv2.GaussianBlur(full_a, (0, 0), blur)
        full_rgb = pm / np.maximum(full_a[..., None], 1e-4)
    full_a = full_a * opacity
    if shadow:
        sh = cv2.GaussianBlur(np.roll(full_a, (6, 4), (0, 1)), (0, 0), 8 + blur) * shadow
        canvas = over(canvas, np.zeros(3), sh)
    canvas = over(canvas, full_rgb, full_a)
    return canvas, h


# ------------------------------------------------------------------ text (skia)
def hex_rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


def render_text_layer(lines, font_name, size, align, x, y0, line_gap, colors, tracking=0,
                      highlight=None, rotate=0.0, max_width=None):
    """lines: list of list of (text, colorkey). returns RGBA float array."""
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    tf = FONTS[font_name]

    def measure(font, runs):
        total = 0
        for txt, _ in runs:
            for ch in txt:
                total += font.measureText(ch) + tracking
        return total - tracking

    # auto-fit
    font = skia.Font(tf, size)
    if max_width:
        widest = max(measure(font, r) for r in lines)
        if widest > max_width:
            size = size * max_width / widest
            font = skia.Font(tf, size)
            line_gap = line_gap * max_width / widest

    cv.save()
    if rotate:
        cv.rotate(rotate, x, y0)
    y = y0
    layout = []
    for runs in lines:
        wtot = measure(font, runs)
        if align == "center":
            xx = x - wtot / 2
        else:
            xx = x
        layout.append((runs, xx, y, wtot))
        y += line_gap

    # highlight boxes behind a run
    if highlight:
        for runs, xx, yy, _ in layout:
            cx_ = xx
            for txt, ck in runs:
                wrun = sum(font.measureText(ch) + tracking for ch in txt) - (tracking if txt else 0)
                if ck == highlight["key"] and txt.strip():
                    pad_x, cap = size * 0.16, size * 0.74
                    path = skia.Path()
                    sk = size * 0.10
                    l, r_ = cx_ - pad_x, cx_ + wrun + pad_x
                    t, b = yy - cap - size * 0.11, yy + size * 0.13
                    path.moveTo(l + sk, t)
                    path.lineTo(r_ + sk, t)
                    path.lineTo(r_ - sk, b)
                    path.lineTo(l - sk, b)
                    path.close()
                    sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 130))
                    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
                    cv.save()
                    cv.translate(5, 8)
                    cv.drawPath(path, sp)
                    cv.restore()
                    c = hex_rgb(highlight["box"])
                    cv.drawPath(path, skia.Paint(AntiAlias=True, Color=skia.Color(*c)))
                cx_ += wrun + tracking

    # shadow pass (discreet), then fill
    for pass_ in ("shadow", "fill"):
        for runs, xx, yy, _ in layout:
            cx_ = xx
            for txt, ck in runs:
                for ch in txt:
                    if pass_ == "shadow":
                        p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 150))
                        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.06))
                        cv.drawString(ch, cx_ + size * 0.025, yy + size * 0.045, font, p)
                    else:
                        c = hex_rgb(colors[ck])
                        cv.drawString(ch, cx_, yy, font, skia.Paint(AntiAlias=True, Color=skia.Color(*c)))
                    cx_ += font.measureText(ch) + tracking
    cv.restore()
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                            alphaType=skia.kUnpremul_AlphaType).astype(np.float32) / 255
    return arr


# ------------------------------------------------------------------ build
PEOPLE_ANCHOR = (636, 528)  # photo coords: group centre x, top of heads y


def build(v):
    s_bg = v.get("bg_scale", 1.80)
    bg = place(plate, s_bg, (W - PW * s_bg) / 2 + v.get("bg_dx", 0), -v.get("bg_top", 170) * s_bg)
    canvas = grade_background(bg)

    s = v["people_scale"]
    ox = v["people_cx"] - PEOPLE_ANCHOR[0] * s
    oy = v["heads_y"] - PEOPLE_ANCHOR[1] * s
    ppl = place(photo, s, ox, oy)
    pa = place_alpha(matte, s, ox, oy)
    pa = np.clip(pa, 0, 1)
    ppl = sharpen(grade_people(ppl), 1.2, 0.55)

    # depth: soft dark halo behind the group so it lifts off the backdrop
    # logos sit in the backdrop: big, slightly defocused, behind the group
    for spec in v["logos"]:
        rgba = LOGO_10P if spec["which"] == "10p" else LOGO_TAT
        canvas, _ = paste_logo(canvas, rgba, spec["x"], spec["y"], spec["w"], shadow=0.45,
                               blur=spec.get("blur", 3.2), opacity=spec.get("opacity", 0.92))
    halo = cv2.GaussianBlur(pa, (0, 0), 40) * 0.55
    canvas = over(canvas, np.zeros(3), halo)
    # slight light falloff on the backdrop behind them (natural stage light feel)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    spot = np.exp(-(((xx - v["people_cx"]) / 900) ** 2 + ((yy - 520) / 520) ** 2))
    canvas = canvas * (1 + 0.28 * spot[..., None])
    # edge refinement: a hair of choke to avoid backdrop fringe
    pa = np.clip((pa - 0.04) / 0.96, 0, 1)
    canvas = over(canvas, ppl, pa)

    # darken the top band a touch for title legibility
    top = (1 - ss(yy, 0, 560))[..., None]
    canvas = canvas * (1 - 0.30 * top)

    canvas = global_grade(canvas)


    # title
    t = v["title"]
    layer = render_text_layer(t["lines"], t["font"], t["size"], t["align"], t["x"], t["y"], t["gap"],
                              t["colors"], t.get("tracking", 0), t.get("highlight"), t.get("rotate", 0.0),
                              t.get("max_width"))
    canvas = over(canvas, layer[..., :3], layer[..., 3])

    # fine grain so it reads as photo, not render
    rng = np.random.default_rng(3)
    g = rng.normal(0, 1, (H, W, 1)).astype(np.float32)
    canvas = np.clip(canvas + g * 0.012, 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


TITLE_LINES = [[("DOBILI ", "w"), ("BATINE", "hi")], [("U SLOVAČKOJ?", "w")]]

VARIANTS = {
    "A_crveno_centar": {
        "people_cx": 960, "heads_y": 430, "people_scale": 1.78,
        "logos": [{"which": "10p", "x": 10, "y": 400, "w": 700},
                  {"which": "tat", "x": 1190, "y": 455, "w": 720}],
        "title": {"lines": TITLE_LINES, "font": "anton", "size": 190, "align": "center", "x": 960, "y": 210,
                  "gap": 222, "colors": {"w": "#FFFFFF", "hi": "#E8262B"}, "tracking": 2, "max_width": 1240},
    },
    "B_zuto_levo": {
        "people_cx": 1150, "heads_y": 445, "people_scale": 1.80, "bg_dx": 120,
        "logos": [{"which": "10p", "x": 30, "y": 560, "w": 720},
                  {"which": "tat", "x": 1235, "y": 262, "w": 670}],
        "title": {"lines": TITLE_LINES, "font": "anton", "size": 205, "align": "left", "x": 64, "y": 222,
                  "gap": 238, "colors": {"w": "#FFFFFF", "hi": "#FFD21F"}, "tracking": 2, "max_width": 1180},
    },
    "C_crvena_traka": {
        "people_cx": 960, "heads_y": 450, "people_scale": 1.74,
        "logos": [{"which": "10p", "x": 0, "y": 520, "w": 720},
                  {"which": "tat", "x": 1215, "y": 420, "w": 700}],
        "title": {"lines": TITLE_LINES, "font": "montserrat", "size": 150, "align": "center", "x": 960, "y": 200,
                  "gap": 180, "colors": {"w": "#FFFFFF", "hi": "#FFFFFF"}, "tracking": 0, "rotate": -2.5,
                  "highlight": {"key": "hi", "box": "#E21F26"}, "max_width": 1500},
    },
}

if __name__ == "__main__":
    for name, v in VARIANTS.items():
        img = Image.fromarray(build(v))
        path = os.path.join(OUT, f"thumbnail_{name}.jpg")
        q = 95
        while True:
            img.save(path, quality=q, subsampling=0, optimize=True)
            if os.path.getsize(path) < 1_900_000 or q < 80:
                break
            q -= 3
        print(name, img.size, os.path.getsize(path) // 1024, "KB", "q", q)
