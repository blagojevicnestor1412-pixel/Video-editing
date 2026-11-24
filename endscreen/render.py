"""10th Planet Belgrade - YouTube End Screen renderer (3840x2160, 30fps, 15s).

Renders every frame with Skia (CPU) and pipes raw frames into ffmpeg/libx264.
Usage:
    python3 render.py stills            # render key frames as PNG for review
    python3 render.py video             # render the full video (parallel segments)
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia
from PIL import Image, ImageFilter
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)

W, H = 3840, 2160
FPS = 30
DUR = 15.0
NFRAMES = int(DUR * FPS)

# ---------------------------------------------------------------- palette
# sampled from the logo
PURPLE = (157, 114, 239)
CYAN = (158, 225, 234)
INK = (6, 5, 16)
WHITE = (255, 255, 255)
YT_RED = (230, 33, 23)


def c4(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, max(0.0, min(1.0, a)))


def ci(rgb, a=1.0):
    return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(255 * max(0.0, min(1.0, a))))


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.70158):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_in_cubic(x):
    return x ** 3


def lerp(a, b, x):
    return a + (b - a) * x


def mix_rgb(a, b, x):
    return tuple(lerp(a[i], b[i], x) for i in range(3))


SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

# ---------------------------------------------------------------- layout (4K px)
LOGO_W = 1120
LOGO_CX, LOGO_CY = 1920, 450
TITLE_Y = 930  # baseline of THANKS FOR WATCHING
SLOT_W, SLOT_H = 1200, 675
SLOT_Y = 1100
SLOT_L_X = 260
SLOT_R_X = W - 260 - SLOT_W
SUB_CX, SUB_CY, SUB_R = 1920, 1390, 185  # YouTube subscribe element area
ROW_Y = 1960  # centre of the like/subscribe/bell row

FONT_DIR = os.path.join(ASSETS, "fonts")
TF_BOLD = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, "Rajdhani_700Bold.ttf"))
TF_SEMI = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, "Rajdhani_600SemiBold.ttf"))
TF_MONT = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, "Montserrat_800ExtraBold.ttf"))


# ---------------------------------------------------------------- assets
def np_to_image(arr):
    arr = np.ascontiguousarray(arr.astype(np.uint8))
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType,
                                alphaType=skia.kUnpremul_AlphaType)


def build_logo_layers():
    """Returns dict of skia images for the logo (unchanged artwork) + sticker edge + glow."""
    src = Image.open(os.path.join(ASSETS, "logo_source.png")).convert("RGB")
    a = np.array(src).astype(float)
    lum = a.mean(2)
    light = lum > 225
    lab, _ = nd.label(light)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = nd.binary_fill_holes(~np.isin(lab, list(border)))
    ys, xs = np.where(fg)
    y0, y1, x0, x1 = ys.min() - 3, ys.max() + 4, xs.min() - 3, xs.max() + 4
    crop = src.crop((x0, y0, x1, y1))
    cw, ch = crop.size
    tw = LOGO_W
    th = int(round(ch * tw / cw))  # keep original proportions
    up = crop.resize((cw * 6, ch * 6), Image.LANCZOS).resize((tw, th), Image.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=2.0, percent=70, threshold=2))
    mk = Image.fromarray((fg[y0:y1, x0:x1] * 255).astype(np.uint8)).resize((tw, th), Image.BICUBIC)
    mk = mk.filter(ImageFilter.GaussianBlur(1.0)).point(lambda v: max(0, min(255, (v - 100) * 255 // 70)))
    PAD = 120
    logo = np.zeros((th + 2 * PAD, tw + 2 * PAD, 4), np.uint8)
    logo[PAD:PAD + th, PAD:PAD + tw, :3] = np.array(up)
    logo[PAD:PAD + th, PAD:PAD + tw, 3] = np.array(mk)
    alpha = logo[:, :, 3].astype(float) / 255
    # sticker edge: thin white keyline around the badge (artwork itself untouched)
    sil = alpha > 0.5
    dil = nd.binary_dilation(sil, iterations=9)
    edge = Image.fromarray((dil * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    edge_arr = np.zeros_like(logo)
    edge_arr[:, :, :3] = 255
    edge_arr[:, :, 3] = np.array(edge)
    # dark keyline outside the white edge so it reads on any background
    dil2 = nd.binary_dilation(dil, iterations=4)
    ink = Image.fromarray((dil2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    ink_arr = np.zeros_like(logo)
    ink_arr[:, :, :3] = 10
    ink_arr[:, :, 3] = (np.array(ink) * 0.9).astype(np.uint8)
    # glow source mask
    glow = Image.fromarray((dil2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(38))
    glow_arr = np.zeros_like(logo)
    glow_arr[:, :, 0], glow_arr[:, :, 1], glow_arr[:, :, 2] = PURPLE
    glow_arr[:, :, 3] = np.array(glow)
    shadow = Image.fromarray((dil2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(26))
    sh_arr = np.zeros_like(logo)
    sh_arr[:, :, 3] = (np.array(shadow) * 0.85).astype(np.uint8)
    # mask used for the specular sweep
    mask_arr = np.zeros_like(logo)
    mask_arr[:, :, :3] = 255
    mask_arr[:, :, 3] = (dil * 255).astype(np.uint8)
    return {
        "logo": np_to_image(logo), "edge": np_to_image(edge_arr), "ink": np_to_image(ink_arr),
        "glow": np_to_image(glow_arr), "shadow": np_to_image(sh_arr), "mask": np_to_image(mask_arr),
        "w": logo.shape[1], "h": logo.shape[0], "art_h": th,
    }


def svg_icon(path_d, size, rgb, viewbox=24):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
           f'viewBox="0 0 {viewbox} {viewbox}"><path fill="rgb{tuple(rgb)}" d="{path_d}"/></svg>')
    dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg.encode(), True))
    surf = skia.Surface(size, size)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    dom.setContainerSize(skia.Size(size, size))
    dom.render(cv)
    return surf.makeImageSnapshot()


THUMB_D = ("M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 "
           "7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23"
           ".14-.47.14-.73v-2z")
BELL_D = ("M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5"
          "-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z")
PLAY_D = "M8 5v14l11-7z"


def make_grain(seed, size=512):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (size, size))
    n = nd.gaussian_filter(n, 0.6)
    n = n / n.std()
    v = np.clip(128 + n * 40, 0, 255).astype(np.uint8)
    arr = np.zeros((size, size, 4), np.uint8)
    arr[:, :, 0] = arr[:, :, 1] = arr[:, :, 2] = v
    arr[:, :, 3] = 255
    return np_to_image(arr)


class Assets:
    def __init__(self):
        self.logo = build_logo_layers()
        self.thumb_w = svg_icon(THUMB_D, 256, WHITE)
        self.thumb_c = svg_icon(THUMB_D, 256, INK)
        self.bell_w = svg_icon(BELL_D, 256, WHITE)
        self.bell_c = svg_icon(BELL_D, 256, INK)
        self.play = svg_icon(PLAY_D, 128, WHITE)
        self.grain = [make_grain(s) for s in range(6)]
        rng = np.random.default_rng(10)
        n = 520
        self.stars = np.stack([
            rng.uniform(0, W, n), rng.uniform(0, H, n),
            rng.power(3.0, n) * 4.2 + 0.8,          # radius
            rng.uniform(0.15, 1.0, n),              # brightness
            rng.uniform(0, 2 * math.pi, n),         # twinkle phase
            rng.uniform(0.3, 1.2, n),               # twinkle speed
            rng.uniform(0.2, 1.0, n),               # depth (parallax)
            rng.integers(0, 3, n).astype(float),    # colour id
        ], 1)
        # floating dust in the foreground
        m = 70
        self.dust = np.stack([
            rng.uniform(0, W, m), rng.uniform(0, H, m), rng.uniform(2, 7, m),
            rng.uniform(0, 2 * math.pi, m), rng.uniform(10, 40, m),
        ], 1)
        self.burst = rng.uniform(0, 1, (3, 18, 3))


A = None


def get_assets():
    global A
    if A is None:
        A = Assets()
    return A


# ---------------------------------------------------------------- drawing helpers
def fill_paint(rgb, a=1.0, blur=0.0, aa=True):
    p = skia.Paint(AntiAlias=aa)
    p.setColor4f(c4(rgb, a))
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke_paint(rgb, a, width, blur=0.0, cap=skia.Paint.kRound_Cap):
    p = fill_paint(rgb, a, blur)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(width)
    p.setStrokeCap(cap)
    return p


def draw_text_center(cv, text, cx, y, font, paint, tracking=0.0):
    widths = [font.measureText(ch) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        cv.drawString(ch, x, y, font, paint)
        x += w + tracking
    return total


def draw_image_centered(cv, img, cx, cy, scale=1.0, alpha=1.0, rot=0.0, blur=0.0):
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if blur > 0.3:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    cv.save()
    cv.translate(cx, cy)
    if rot:
        cv.rotate(rot)
    cv.scale(scale, scale)
    cv.drawImage(img, -img.width() / 2, -img.height() / 2, SAMPLING, p)
    cv.restore()


# ---------------------------------------------------------------- scene parts
def draw_background(cv, t, a):
    intro = ease_out_cubic(prog(t, 0.0, 1.2))
    # base gradient
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(
        (W * 0.5, H * 0.32), H * 1.25,
        [ci((22, 16, 52)), ci((10, 8, 28)), ci((3, 3, 10))], [0.0, 0.45, 1.0]))
    cv.drawPaint(p)

    # drifting nebula light
    def blob(x, y, r, rgb, alpha):
        bp = skia.Paint()
        bp.setShader(skia.GradientShader.MakeRadial(
            (x, y), r, [ci(rgb, alpha), ci(rgb, alpha * 0.35), ci(rgb, 0)], [0, 0.45, 1]))
        cv.drawCircle(x, y, r, bp)

    blob(700 + 120 * math.sin(t * 0.21), 380 + 60 * math.cos(t * 0.17), 1500, PURPLE, 0.20 * intro)
    blob(3250 + 100 * math.cos(t * 0.19), 1700 + 80 * math.sin(t * 0.23), 1400, CYAN, 0.10 * intro)
    blob(1920, 520, 900, PURPLE, 0.16 * intro)

    # wormhole grid (echoes the logo's warped grid), flowing towards the centre
    draw_wormhole(cv, t, intro)

    # stars
    st = a.stars
    sp = skia.Paint(AntiAlias=True)
    cols = [WHITE, CYAN, (205, 190, 255)]
    for x, y, r, b, ph, spd, d, cid in st:
        tw = 0.55 + 0.45 * math.sin(ph + t * spd * 2.2)
        xx = (x - t * 9 * d) % W
        yy = (y + t * 2.5 * d) % H
        al = b * tw * intro
        if al < 0.03:
            continue
        sp.setColor4f(c4(cols[int(cid)], al * 0.85))
        cv.drawCircle(xx, yy, r * (0.6 + 0.4 * d), sp)
        if r > 3.6:
            sp.setColor4f(c4(cols[int(cid)], al * 0.25))
            cv.drawRect(skia.Rect.MakeXYWH(xx - r * 5, yy - 0.8, r * 10, 1.6), sp)
            cv.drawRect(skia.Rect.MakeXYWH(xx - 0.8, yy - r * 5, 1.6, r * 10), sp)


def draw_wormhole(cv, t, intro):
    cx, cy = 1920, 600
    rings = 22
    flow = (t * 0.11) % 1.0
    path_alpha = 0.0
    for k in range(rings + 1):
        u = (k + flow) / rings  # 0 = outer, 1 = throat
        if u > 1:
            continue
        depth = u ** 1.6
        rx = 3300 * (1 - depth) + 120
        ry = rx * 0.24
        yy = cy + 1150 * depth ** 0.85 - 260 * (1 - u)
        al = (0.10 + 0.20 * u) * (1 - u ** 4) * intro * clamp((u) * 6)
        p = stroke_paint(PURPLE if k % 2 else (120, 100, 230), al, 2.2 + 1.4 * (1 - u))
        cv.drawOval(skia.Rect.MakeXYWH(cx - rx, yy - ry, 2 * rx, 2 * ry), p)
    # radial meridians
    n = 36
    rot = t * 0.035
    p = stroke_paint((130, 110, 235), 0.11 * intro, 2.0)
    for i in range(n):
        ang = rot + i * 2 * math.pi / n
        path = skia.Path()
        first = True
        for s in range(0, 21):
            u = s / 20
            depth = u ** 1.6
            rx = 3300 * (1 - depth) + 120
            ry = rx * 0.24
            yy = cy + 1150 * depth ** 0.85 - 260 * (1 - u)
            x = cx + rx * math.cos(ang)
            y = yy + ry * math.sin(ang)
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        cv.drawPath(path, p)
    # throat glow
    gp = skia.Paint()
    gp.setShader(skia.GradientShader.MakeRadial(
        (cx, cy + 1150), 700, [ci(CYAN, 0.10 * intro), ci(PURPLE, 0.05 * intro), ci(PURPLE, 0)], [0, 0.5, 1]))
    cv.drawCircle(cx, cy + 1150, 700, gp)


def draw_light_streak(cv, cx, cy, strength, length=2600):
    if strength <= 0.01:
        return
    for (h, al, rgb) in [(90, 0.10, PURPLE), (26, 0.35, CYAN), (6, 0.9, WHITE)]:
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear(
            [(cx - length / 2, cy), (cx + length / 2, cy)],
            [ci(rgb, 0), ci(rgb, al * strength), ci(rgb, 0)], [0, 0.5, 1]))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, h * 0.35))
        cv.drawRect(skia.Rect.MakeXYWH(cx - length / 2, cy - h / 2, length, h), p)


def draw_logo(cv, t, a):
    L = a.logo
    p_in = prog(t, 0.45, 1.25)
    if p_in <= 0:
        return
    e = ease_out_expo(p_in)
    scale = lerp(1.18, 1.0, e)
    alpha = clamp(p_in * 2.2)
    blur = lerp(26, 0, ease_out_cubic(clamp(p_in * 1.4)))
    # gentle float once settled
    settle = ease_in_out_cubic(prog(t, 1.4, 3.0))
    fy = math.sin((t - 1.4) * 0.9) * 7 * settle
    fs = 1 + math.sin((t - 1.4) * 0.6) * 0.004 * settle
    # impact shake
    shake = 0.0
    if 1.0 < t < 1.5:
        k = (t - 1.0) / 0.5
        shake = math.sin(k * 40) * 6 * (1 - k) ** 2
    cx, cy = LOGO_CX + shake, LOGO_CY + fy
    s = scale * fs

    draw_image_centered(cv, L["shadow"], cx, cy + 30, s, alpha * 0.9)
    glow_pulse = 0.55 + 0.15 * math.sin(t * 1.3)
    flash = math.exp(-max(0, t - 1.0) * 5) if t > 1.0 else 0
    draw_image_centered(cv, L["glow"], cx, cy, s * 1.03, alpha * (glow_pulse + flash * 0.8))
    draw_image_centered(cv, L["ink"], cx, cy, s, alpha, blur=blur)
    draw_image_centered(cv, L["edge"], cx, cy, s, alpha, blur=blur)
    draw_image_centered(cv, L["logo"], cx, cy, s, alpha, blur=blur)

    # specular sweep clipped to the badge
    for t0 in (1.15, 6.5, 11.5):
        sp = prog(t, t0, t0 + 1.1)
        if 0 < sp < 1:
            draw_sweep(cv, L, cx, cy, s, ease_in_out_cubic(sp), 0.55 if t0 > 2 else 0.8)

    # impact flash + shockwave
    if 0.95 < t < 2.2:
        k = prog(t, 1.0, 2.0)
        r = lerp(400, 2600, ease_out_cubic(k))
        al = (1 - k) ** 2 * 0.6
        for w_, a_, col in [(40, 0.25, PURPLE), (8, 1.0, CYAN)]:
            pp = stroke_paint(col, al * a_, w_, blur=w_ * 0.6)
            cv.drawOval(skia.Rect.MakeXYWH(LOGO_CX - r, LOGO_CY + 40 - r * 0.3, 2 * r, 0.6 * r), pp)
        draw_light_streak(cv, LOGO_CX, LOGO_CY + 40, (1 - ease_out_cubic(prog(t, 1.0, 1.9))) * 1.0, 3600)


def draw_sweep(cv, L, cx, cy, s, k, strength):
    w, h = L["w"], L["h"]
    cv.save()
    cv.translate(cx, cy)
    cv.scale(s, s)
    rect = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    cv.saveLayer(rect, None)
    pos = lerp(-w * 0.9, w * 0.9, k)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear(
        [(pos - 160, -h / 2), (pos + 160, h / 2)],
        [ci(WHITE, 0), ci(WHITE, strength), ci(WHITE, 0)], [0, 0.5, 1]))
    cv.drawRect(rect, p)
    mp = skia.Paint()
    mp.setBlendMode(skia.BlendMode.kDstIn)
    cv.drawImage(L["mask"], -w / 2, -h / 2, SAMPLING, mp)
    cv.restore()
    cv.restore()


def draw_title(cv, t):
    text = "THANKS FOR WATCHING"
    font = skia.Font(TF_BOLD, 118)
    tracking = 30
    widths = [font.measureText(ch) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = 1920 - total / 2
    # flanking lines
    lp = ease_out_expo(prog(t, 1.35, 2.3))
    if lp > 0:
        ln = 330 * lp
        gap = total / 2 + 60
        for sgn in (-1, 1):
            p = skia.Paint(AntiAlias=True)
            x0 = 1920 + sgn * gap
            x1 = x0 + sgn * ln
            p.setShader(skia.GradientShader.MakeLinear(
                [(x0, 0), (x1, 0)], [ci(CYAN, 0.9), ci(PURPLE, 0)]))
            p.setStrokeWidth(4)
            cv.drawLine(x0, TITLE_Y - 40, x1, TITLE_Y - 40, p)
            dp = fill_paint(CYAN, lp)
            cv.save()
            cv.translate(x0 - sgn * 22, TITLE_Y - 40)
            cv.rotate(45)
            cv.drawRect(skia.Rect.MakeXYWH(-7, -7, 14, 14), dp)
            cv.restore()
    grad = skia.GradientShader.MakeLinear(
        [(0, TITLE_Y - 90), (0, TITLE_Y + 5)], [ci((255, 255, 255)), ci((214, 200, 255))])
    clip_top = TITLE_Y - 110
    for i, (ch, w_) in enumerate(zip(text, widths)):
        k = prog(t, 1.3 + i * 0.028, 1.3 + i * 0.028 + 0.55)
        if k > 0:
            e = ease_out_expo(k)
            p = skia.Paint(AntiAlias=True)
            p.setShader(grad)
            p.setAlphaf(clamp(k * 2.5))
            cv.save()
            cv.clipRect(skia.Rect.MakeLTRB(x - 10, clip_top, x + w_ + 10, TITLE_Y + 30))
            cv.drawString(ch, x, TITLE_Y + (1 - e) * 120, font, p)
            cv.restore()
        x += w_ + tracking
    # subtle sub-caption
    k = prog(t, 2.0, 2.8)
    if k > 0:
        f2 = skia.Font(TF_SEMI, 46)
        p = fill_paint(CYAN, 0.75 * ease_out_cubic(k))
        draw_text_center(cv, "10TH PLANET JIU JITSU  •  BELGRADE", 1920, TITLE_Y + 78 + (1 - ease_out_cubic(k)) * 20,
                         f2, p, tracking=14)


def rounded_rect_path(x, y, w, h, r):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return p


def draw_slot(cv, t, x, y, t0, label, side, a):
    k = prog(t, t0, t0 + 0.9)
    if k <= 0:
        return
    e = ease_out_expo(k)
    dx = (1 - e) * 120 * side
    x += dx
    alpha = clamp(k * 2)
    r = 26
    # glass panel
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear(
        [(x, y), (x + SLOT_W, y + SLOT_H)],
        [ci((40, 30, 90), 0.55 * alpha), ci((10, 10, 30), 0.65 * alpha), ci((20, 50, 70), 0.5 * alpha)],
        [0, 0.6, 1]))
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, SLOT_W, SLOT_H), r, r), p)
    # outer glow
    gp = stroke_paint(PURPLE, 0.35 * alpha, 10, blur=22)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, SLOT_W, SLOT_H), r, r), gp)
    # border draw-on
    path = rounded_rect_path(x, y, SLOT_W, SLOT_H, r)
    meas = skia.PathMeasure(path, False)
    length = meas.getLength()
    d = ease_in_out_cubic(prog(t, t0, t0 + 1.1))
    bp = skia.Paint(AntiAlias=True)
    bp.setStyle(skia.Paint.kStroke_Style)
    bp.setStrokeWidth(3)
    bp.setShader(skia.GradientShader.MakeLinear(
        [(x, y), (x + SLOT_W, y + SLOT_H)], [ci(CYAN, 0.95), ci(PURPLE, 0.95), ci(CYAN, 0.6)]))
    bp.setPathEffect(skia.DashPathEffect.Make([length * d, length * 2], 0))
    cv.drawPath(path, bp)
    # corner brackets
    cb = ease_out_back(prog(t, t0 + 0.4, t0 + 1.0))
    if cb > 0:
        L_ = 70 * cb
        off = 22
        bp2 = stroke_paint(WHITE, 0.95 * alpha, 7, cap=skia.Paint.kSquare_Cap)
        for (px, py, sx, sy) in [(x - off, y - off, 1, 1), (x + SLOT_W + off, y - off, -1, 1),
                                 (x - off, y + SLOT_H + off, 1, -1), (x + SLOT_W + off, y + SLOT_H + off, -1, -1)]:
            pa = skia.Path()
            pa.moveTo(px, py + sy * L_)
            pa.lineTo(px, py)
            pa.lineTo(px + sx * L_, py)
            cv.drawPath(pa, bp2)
    # play glyph (will be covered by the YouTube video element)
    pk = ease_out_back(prog(t, t0 + 0.5, t0 + 1.1))
    if pk > 0:
        pcx, pcy = x + SLOT_W / 2, y + SLOT_H / 2
        breathe = 1 + 0.04 * math.sin(t * 2.2)
        cp = fill_paint(WHITE, 0.10 * alpha)
        cv.drawCircle(pcx, pcy, 110 * pk * breathe, cp)
        cv.drawCircle(pcx, pcy, 110 * pk * breathe, stroke_paint(WHITE, 0.45 * alpha, 4))
        draw_image_centered(cv, a.play, pcx + 8, pcy, 1.25 * pk, 0.9 * alpha)
    # scanning shimmer across the glass
    for s0 in (t0 + 0.6, t0 + 6.0):
        sk = prog(t, s0, s0 + 1.4)
        if 0 < sk < 1:
            cv.save()
            cv.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, SLOT_W, SLOT_H), r, r), True)
            pos = lerp(x - 400, x + SLOT_W + 400, ease_in_out_cubic(sk))
            sp = skia.Paint(AntiAlias=True)
            sp.setShader(skia.GradientShader.MakeLinear(
                [(pos - 220, y), (pos + 220, y + SLOT_H * 0.4)],
                [ci(WHITE, 0), ci(WHITE, 0.10), ci(WHITE, 0)], [0, 0.5, 1]))
            cv.drawRect(skia.Rect.MakeXYWH(x, y, SLOT_W, SLOT_H), sp)
            cv.restore()
    # label above slot
    lk = prog(t, t0 + 0.3, t0 + 1.0)
    if lk > 0:
        f = skia.Font(TF_BOLD, 50)
        lp = fill_paint(WHITE, 0.92 * ease_out_cubic(lk))
        tx = x + 8 + (1 - ease_out_expo(lk)) * 40 * side
        ty = y - 34
        acc = fill_paint(CYAN, ease_out_cubic(lk))
        cv.drawRect(skia.Rect.MakeXYWH(tx, ty - 36, 8, 40), acc)
        xx = tx + 30
        for ch in label:
            cv.drawString(ch, xx, ty, f, lp)
            xx += f.measureText(ch) + 9


def draw_subscribe_ring(cv, t):
    k = prog(t, 2.2, 3.2)
    if k <= 0:
        return
    e = ease_out_expo(k)
    cx, cy, r = SUB_CX, SUB_CY, SUB_R
    # soft disk
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(
        (cx, cy), r * 1.9, [ci(PURPLE, 0.28 * e), ci(PURPLE, 0.08 * e), ci(PURPLE, 0)], [0, 0.55, 1]))
    cv.drawCircle(cx, cy, r * 1.9, p)
    cv.drawCircle(cx, cy, r * e, fill_paint((14, 12, 34), 0.85 * e))
    # base ring draw-on
    rect = skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r)
    cv.drawArc(rect, -90, 360 * ease_in_out_cubic(k), False, stroke_paint(WHITE, 0.85, 5))
    # rotating arcs
    rot = t * 40
    r2 = r + 34
    rect2 = skia.Rect.MakeXYWH(cx - r2, cy - r2, 2 * r2, 2 * r2)
    for i in range(3):
        cv.drawArc(rect2, rot + i * 120, 70 * e, False, stroke_paint(CYAN, 0.9 * e, 7))
    r3 = r + 62
    rect3 = skia.Rect.MakeXYWH(cx - r3, cy - r3, 2 * r3, 2 * r3)
    for i in range(4):
        cv.drawArc(rect3, -rot * 0.6 + i * 90 + 20, 30 * e, False, stroke_paint(PURPLE, 0.8 * e, 4))
    # pulse ring every 2.5s
    for base in np.arange(3.2, 15, 2.5):
        pk = prog(t, base, base + 1.6)
        if 0 < pk < 1:
            rr = r + 20 + 160 * ease_out_cubic(pk)
            cv.drawCircle(cx, cy, rr, stroke_paint(CYAN, 0.5 * (1 - pk) ** 2, 4))
    # label
    lk = prog(t, 2.6, 3.4)
    if lk > 0:
        f = skia.Font(TF_BOLD, 46)
        draw_text_center(cv, "JOIN THE TEAM", cx, cy + r + 140 + (1 - ease_out_cubic(lk)) * 20, f,
                         fill_paint(WHITE, 0.85 * ease_out_cubic(lk)), tracking=12)


def press_curve(t, tp):
    """scale curve for a button press at tp: dip then overshoot back."""
    if t < tp:
        return 1.0
    d = t - tp
    if d < 0.09:
        return 1 - 0.12 * ease_out_cubic(d / 0.09)
    d -= 0.09
    return 1 + 0.12 * math.exp(-d * 6) * math.cos(d * 22) * -1 + 0.0 if d < 1.2 else 1.0


def draw_burst(cv, t, tp, cx, cy, seed_row, rgb_list):
    k = prog(t, tp, tp + 0.7)
    if not (0 < k < 1):
        return
    e = ease_out_cubic(k)
    rnd = get_assets().burst[seed_row]
    for i, (ra, rb, rc) in enumerate(rnd):
        ang = i / len(rnd) * 2 * math.pi + ra * 0.3
        dist = 100 + 75 * e * (0.6 + 0.6 * rb)
        sz = (8 + 8 * rc) * (1 - k)
        col = rgb_list[i % len(rgb_list)]
        cv.drawCircle(cx + math.cos(ang) * dist, cy + math.sin(ang) * dist, sz, fill_paint(col, 1 - k))
    cv.drawCircle(cx, cy, 85 + 90 * e, stroke_paint(WHITE, 0.6 * (1 - k) ** 2, 5))


LIKE_X, PILL_CX, BELL_X = 1920 - 520, 1920, 1920 + 520
PILL_W, PILL_H = 600, 150
BTN_R = 80
LIKE_T = [4.0, 9.6]
SUB_T = [4.8, 10.4]
BELL_T = [5.6, 11.2]


def draw_cta_row(cv, t, a):
    # like button
    k = prog(t, 2.7, 3.3)
    if k > 0:
        s = ease_out_back(k, 2.2)
        s *= min(press_curve(t, LIKE_T[0]), 9) if t < LIKE_T[1] else press_curve(t, LIKE_T[1])
        on = ease_out_cubic(prog(t, LIKE_T[0] + 0.05, LIKE_T[0] + 0.25))
        cx, cy = LIKE_X, ROW_Y
        cv.drawCircle(cx, cy, BTN_R * s + 18, fill_paint(CYAN, 0.25 * on, blur=26))
        cv.drawCircle(cx, cy, BTN_R * s, fill_paint(mix_rgb((30, 26, 60), CYAN, on), 0.95))
        cv.drawCircle(cx, cy, BTN_R * s, stroke_paint(mix_rgb(WHITE, CYAN, on), 0.9, 4))
        wob = 0
        for tp in LIKE_T:
            if tp < t < tp + 0.8:
                d = t - tp
                wob = -18 * math.sin(d * 18) * math.exp(-d * 5)
        img = a.thumb_c if on > 0.5 else a.thumb_w
        draw_image_centered(cv, img, cx, cy - 4, 0.36 * s, 1.0, rot=wob)
        for i, tp in enumerate(LIKE_T):
            draw_burst(cv, t, tp + 0.05, cx, cy, 0, [CYAN, WHITE, PURPLE])
        pass  # no label
        if False: draw_text_center(cv, "LIKE", cx, cy + BTN_R + 62, f, fill_paint(WHITE, 0.8 * clamp(k * 2)), 10)

    # subscribe pill
    k = prog(t, 2.85, 3.45)
    if k > 0:
        s = ease_out_back(k, 2.0)
        for tp in SUB_T:
            if t >= tp:
                s *= press_curve(t, tp) if t < tp + 1.2 else 1.0
        cx, cy = PILL_CX, ROW_Y
        w, h = PILL_W * s, PILL_H * s
        rect = skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h)
        glow = 0.35 + 0.15 * math.sin(t * 3.0)
        cv.drawRRect(skia.RRect.MakeRectXY(rect, h / 2, h / 2), fill_paint(YT_RED, glow, blur=34))
        gp = skia.Paint(AntiAlias=True)
        gp.setShader(skia.GradientShader.MakeLinear(
            [(0, cy - h / 2), (0, cy + h / 2)], [ci((255, 64, 52)), ci((205, 18, 14))]))
        cv.drawRRect(skia.RRect.MakeRectXY(rect, h / 2, h / 2), gp)
        # glossy top highlight
        hp = skia.Paint(AntiAlias=True)
        hp.setShader(skia.GradientShader.MakeLinear(
            [(0, cy - h / 2), (0, cy)], [ci(WHITE, 0.28), ci(WHITE, 0)]))
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2 + 10, cy - h / 2 + 6, w - 20, h / 2),
                                           h / 2.4, h / 2.4), hp)
        # click ripple inside
        cv.save()
        cv.clipRRect(skia.RRect.MakeRectXY(rect, h / 2, h / 2), True)
        for tp in SUB_T:
            rk = prog(t, tp + 0.05, tp + 0.75)
            if 0 < rk < 1:
                cv.drawCircle(cx + 120, cy + 10, 30 + 420 * ease_out_cubic(rk), fill_paint(WHITE, 0.35 * (1 - rk)))
        # shine sweep
        for s0 in (3.4, 7.6, 12.6):
            sk = prog(t, s0, s0 + 0.9)
            if 0 < sk < 1:
                pos = lerp(cx - w, cx + w, ease_in_out_cubic(sk))
                sp = skia.Paint(AntiAlias=True)
                sp.setShader(skia.GradientShader.MakeLinear(
                    [(pos - 90, cy - h), (pos + 90, cy + h)], [ci(WHITE, 0), ci(WHITE, 0.45), ci(WHITE, 0)], [0, .5, 1]))
                cv.drawRect(rect, sp)
        cv.restore()
        f = skia.Font(TF_MONT, 58 * s)
        draw_text_center(cv, "SUBSCRIBE", cx, cy + 21 * s, f, fill_paint(WHITE, clamp(k * 2)), tracking=6 * s)

    # bell
    k = prog(t, 3.0, 3.6)
    if k > 0:
        s = ease_out_back(k, 2.2)
        for tp in BELL_T:
            if tp <= t < tp + 1.2:
                s *= press_curve(t, tp)
        on = ease_out_cubic(prog(t, BELL_T[0] + 0.05, BELL_T[0] + 0.25))
        cx, cy = BELL_X, ROW_Y
        cv.drawCircle(cx, cy, BTN_R * s + 18, fill_paint(PURPLE, 0.35 * on, blur=26))
        cv.drawCircle(cx, cy, BTN_R * s, fill_paint(mix_rgb((30, 26, 60), PURPLE, on), 0.95))
        cv.drawCircle(cx, cy, BTN_R * s, stroke_paint(mix_rgb(WHITE, PURPLE, on), 0.9, 4))
        rot = 0
        for tp in BELL_T:
            if tp < t < tp + 1.6:
                d = t - tp
                rot = 26 * math.sin(d * 26) * math.exp(-d * 3.2)
        # rotate around bell top
        cv.save()
        cv.translate(cx, cy - 46 * s)
        cv.rotate(rot)
        img = a.bell_w
        cv.scale(0.36 * s, 0.36 * s)
        bp = skia.Paint(AntiAlias=True)
        cv.drawImage(img, -128, -128 + 46 / 0.36, SAMPLING, bp)
        cv.restore()
        # sound waves
        for tp in BELL_T:
            wk = prog(t, tp + 0.05, tp + 1.2)
            if 0 < wk < 1:
                for j in range(2):
                    rr = 100 + 26 * j + 30 * ease_out_cubic(wk)
                    al = math.sin(wk * math.pi) * 0.9
                    for sgn in (-1, 1):
                        rect = skia.Rect.MakeXYWH(cx - rr, cy - rr, 2 * rr, 2 * rr)
                        start = -90 + sgn * 50 - (20 if sgn < 0 else 0) + (0 if sgn < 0 else -20)
                        cv.drawArc(rect, start + (0 if sgn > 0 else 0), 40, False,
                                   stroke_paint(WHITE, al, 6))
        pass
        if False: draw_text_center(cv, "NOTIFY", cx, cy + BTN_R + 62, f, fill_paint(WHITE, 0.8 * clamp(k * 2)), 10)


def draw_dust(cv, t, a):
    k = ease_out_cubic(prog(t, 0.5, 2.0))
    for x, y, r, ph, sp in a.dust:
        xx = (x + math.sin(t * 0.3 + ph) * sp * 3 + t * 14) % W
        yy = (y - t * sp) % H
        al = 0.18 * k * (0.5 + 0.5 * math.sin(t * 0.8 + ph))
        cv.drawCircle(xx, yy, r, fill_paint(CYAN if ph > 3 else PURPLE, al, blur=r * 0.8))


def draw_post(cv, t, frame_idx, a):
    # vignette
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(
        (W / 2, H / 2), W * 0.62, [ci(INK, 0), ci(INK, 0), ci(INK, 0.55)], [0, 0.6, 1]))
    cv.drawPaint(p)
    # film grain (overlay), keeps the gradients free of banding
    g = a.grain[frame_idx % len(a.grain)]
    gp = skia.Paint()
    rng = np.random.default_rng(frame_idx)
    ox, oy = rng.integers(0, 512, 2)
    m = skia.Matrix()
    m.setTranslate(float(ox), float(oy))
    gp.setShader(g.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, SAMPLING, m))
    gp.setBlendMode(skia.BlendMode.kOverlay)
    gp.setAlphaf(0.10)
    cv.drawPaint(gp)
    # fade from / to black
    fin = 1 - ease_out_cubic(prog(t, 0.0, 0.5))
    fout = ease_in_cubic(prog(t, DUR - 0.6, DUR))
    f = max(fin, fout)
    if f > 0:
        cv.drawPaint(fill_paint((0, 0, 0), f, aa=False))


def render_frame(i):
    a = get_assets()
    t = i / FPS
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorBLACK)
    draw_background(cv, t, a)
    draw_dust(cv, t, a)
    draw_slot(cv, t, SLOT_L_X, SLOT_Y, 1.85, "WATCH NEXT", -1, a)
    draw_slot(cv, t, SLOT_R_X, SLOT_Y, 2.0, "RECOMMENDED", 1, a)
    draw_subscribe_ring(cv, t)
    draw_cta_row(cv, t, a)
    draw_title(cv, t)
    draw_logo(cv, t, a)
    draw_post(cv, t, i, a)
    img = surf.makeImageSnapshot()
    return img.toarray(colorType=skia.kRGBA_8888_ColorType)


# ---------------------------------------------------------------- output
def render_segment(args):
    seg, f0, f1 = args
    path = os.path.join(OUT, f"seg_{seg:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-tune", "film",
           "-profile:v", "high", "-level", "5.1", "-g", "30", "-keyint_min", "30", "-sc_threshold", "0",
           "-x264-params", "threads=2",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-an", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        proc.stdin.write(render_frame(i).tobytes())
        if (i - f0) % 15 == 0:
            print(f"seg {seg}: frame {i}", flush=True)
    proc.stdin.close()
    proc.wait()
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if mode == "stills":
        times = [float(x) for x in sys.argv[2:]] or [0.8, 1.1, 1.6, 2.4, 3.2, 4.15, 5.75, 8.0]
        for tt in times:
            fr = int(round(tt * FPS))
            Image.fromarray(render_frame(fr)).convert("RGB").save(os.path.join(OUT, f"still_{tt:05.2f}.png"))
            print("still", tt)
    elif mode == "video":
        nseg = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        bounds = np.linspace(0, NFRAMES, nseg + 1).astype(int)
        jobs = [(s, bounds[s], bounds[s + 1]) for s in range(nseg)]
        with Pool(int(os.environ.get("WORKERS", "4"))) as pool:
            paths = pool.map(render_segment, jobs, chunksize=1)
        lst = os.path.join(OUT, "segments.txt")
        with open(lst, "w") as fh:
            for p in paths:
                fh.write(f"file '{p}'\n")
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                               "-i", lst, "-c", "copy", os.path.join(OUT, "video_only.mp4")])
        print("done")


if __name__ == "__main__":
    main()
