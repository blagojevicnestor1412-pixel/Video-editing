"""High-energy vlog thumbnail style (white cut-out outline, bold italic title, red/blue stage light).

Re-uses the cut-out, retouch and logo prep from make_thumbnails.py.
"""
import os

import cv2
import numpy as np
import skia
from PIL import Image

import make_thumbnails as base
from make_thumbnails import (W, H, LOGO_10P, LOGO_TAT, PEOPLE_ANCHOR, matte, over, paste_logo, photo,
                             place, place_alpha, plate, sharpen, ss)

TF = skia.Typeface.MakeFromFile(os.path.join(base.A, "fonts", "Montserrat_900Black_Italic.ttf"))
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def background(cx_shift=0):
    s = 1.95
    bg = place(plate, s, (W - base.PW * s) / 2 + cx_shift, -150 * s)
    bg = cv2.GaussianBlur(bg, (0, 0), 7)
    lum = bg.mean(2, keepdims=True)
    bg = lum + (bg - lum) * 1.15
    bg = np.clip(bg * 0.62 + 0.03, 0, 1)
    # cool base tint
    bg = bg * np.array([0.85, 0.92, 1.12])
    return np.clip(bg, 0, 1)


def light_leaks(canvas, strength=1.0):
    """Blue light from the left, red from the right - like arena / police lights."""
    def beam(cx, cy, angle, length, width, rgb, a):
        ca, sa = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        dx, dy = XX - cx, YY - cy
        along = dx * ca + dy * sa
        across = -dx * sa + dy * ca
        m = np.exp(-(across / width) ** 2) * np.clip(1 - np.abs(along) / length, 0, 1) ** 1.5
        return m[..., None] * np.array(rgb) * a

    add = np.zeros_like(canvas)
    blue, red = (0.15, 0.45, 1.0), (1.0, 0.12, 0.12)
    # broad colour washes from the sides
    add += np.exp(-((XX / 520) ** 2))[..., None] * np.array(blue) * 0.55
    add += np.exp(-(((W - XX) / 520) ** 2))[..., None] * np.array(red) * 0.55
    # crisp streaks
    add += beam(120, 760, -62, 900, 14, blue, 0.9) + beam(120, 760, -62, 900, 70, blue, 0.35)
    add += beam(60, 1000, -8, 700, 10, blue, 0.6) + beam(60, 1000, -8, 700, 45, blue, 0.25)
    add += beam(1800, 300, 62, 900, 14, red, 0.9) + beam(1800, 300, 62, 900, 70, red, 0.35)
    add += beam(1880, 1010, 172, 700, 10, red, 0.6) + beam(1880, 1010, 172, 700, 45, red, 0.25)
    # screen blend
    return 1 - (1 - canvas) * (1 - np.clip(add * strength, 0, 1))


TF_TITLE = skia.Typeface.MakeFromFile(os.path.join(base.A, "fonts", "Anton_400Regular.ttf"))


def text_layer(lines, size, cx, y0, gap, rot, stroke=18, skew=-0.18):
    """lines: [(runs, line_scale)], run = (text, rgb, scale, extra_bold_px)."""
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    cv.translate(cx, y0)
    cv.rotate(rot)
    cv.skew(skew, 0)
    cv.translate(-cx, -y0)
    layout = []
    y = y0
    for runs, sc in lines:
        items = []
        for t, col, rs, bold in runs:
            f = skia.Font(TF_TITLE, size * sc * rs)
            items.append((t, col, f, bold))
        wtot = sum(f.measureText(t) + bold for t, _, f, bold in items)
        layout.append((items, cx - wtot / 2, y))
        y += gap * sc

    def each(fn):
        for items, x, y in layout:
            xx = x
            for t, col, f, bold in items:
                fn(t, col, f, bold, xx, y)
                xx += f.measureText(t) + bold

    def shadow(t, col, f, bold, x, y):
        p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 180))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        cv.drawString(t, x + 10, y + 16, f, p)

    def outline(t, col, f, bold, x, y):
        p = skia.Paint(AntiAlias=True, Color=skia.Color(12, 10, 20))
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke * f.getSize() / size + bold * 2)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        cv.drawString(t, x, y, f, p)

    def fill(t, col, f, bold, x, y):
        bot = tuple(int(c * 0.82) for c in col)
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear(
            [(0, y - f.getSize() * 0.75), (0, y)], [skia.Color(*col), skia.Color(*bot)]))
        if bold:  # extra weight: grow the glyphs with a same-colour stroke
            p.setStyle(skia.Paint.kStrokeAndFill_Style)
            p.setStrokeWidth(bold)
            p.setStrokeJoin(skia.Paint.kRound_Join)
        cv.drawString(t, x, y, f, p)

    each(shadow)
    each(outline)
    each(fill)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                            alphaType=skia.kUnpremul_AlphaType).astype(np.float32) / 255


def build(v):
    canvas = background(v.get("bg_dx", 0))
    # big 10th Planet badge behind the group (like the club badge in the reference)
    canvas, _ = paste_logo(canvas, LOGO_10P, v["badge_x"], v["badge_y"], v["badge_w"], shadow=0.5, blur=1.6, opacity=0.95)
    canvas = light_leaks(canvas, 1.0)

    s = v["scale"]
    ox = v["cx"] - PEOPLE_ANCHOR[0] * s
    oy = v["heads_y"] - PEOPLE_ANCHOR[1] * s
    ppl = place(photo, s, ox, oy)
    pa = np.clip(place_alpha(matte, s, ox, oy), 0, 1)
    pa = np.clip((pa - 0.04) / 0.96, 0, 1)
    # punchy but natural grade on the people
    p = np.clip(ppl, 0, 1)
    lum = p.mean(2, keepdims=True)
    p = lum + (p - lum) * 1.18
    p = 0.5 + (p - 0.5) * 1.12
    p = np.clip(p * 1.10, 0, 1)
    p = sharpen(p, 1.1, 0.6)
    # colored rim from the stage lights on the people's edges
    edge = np.clip(pa - cv2.GaussianBlur(pa, (0, 0), 5), 0, 1) * 2.2
    side = ss(XX, 300, 1620)[..., None]
    rim = (1 - side) * np.array([0.25, 0.55, 1.0]) + side * np.array([1.0, 0.25, 0.25])
    p = np.clip(p + edge[..., None] * rim * 0.45, 0, 1)

    # drop shadow + white cut-out outline
    sh = cv2.GaussianBlur(np.roll(pa, (14, 10), (0, 1)), (0, 0), 16) * 0.75
    canvas = over(canvas, np.zeros(3), sh)
    outline = cv2.dilate((pa > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    outline = cv2.GaussianBlur(outline.astype(np.float32), (0, 0), 1.0)
    outline = outline * (1 - ss(YY, 820, 1000))
    canvas = over(canvas, np.ones(3), outline)
    canvas = over(canvas, p, pa)

    # TATAMY logo small in a corner
    canvas, _ = paste_logo(canvas, LOGO_TAT, v["tat_x"], v["tat_y"], v["tat_w"], shadow=0.7)

    # bottom darkening so the title pops
    canvas = canvas * (1 - 0.45 * ss(YY, 620, 1080))[..., None]
    # vignette
    d = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
    canvas = canvas * (1 - 0.25 * ss(d, 0.7, 1.5))[..., None]

    t = text_layer(v["lines"], v["size"], v["tx"], v["ty"], v["gap"], v["rot"])
    canvas = over(canvas, t[..., :3], t[..., 3])
    rng = np.random.default_rng(5)
    canvas = np.clip(canvas + rng.normal(0, 0.01, (H, W, 1)), 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)
RED = (240, 36, 36)

VARIANTS = {
    "D_fazon_zuto": {
        "scale": 2.05, "cx": 960, "heads_y": 175,
        "badge_x": 560, "badge_y": 20, "badge_w": 800,
        "tat_x": 40, "tat_y": 40, "tat_w": 330,
        "lines": [([("DOBILI ", WHITE, 1.0, 0), ("BATINE", YELLOW, 1.32, 9)], 1.0),
                  ([("U SLOVAČKOJ?", YELLOW, 1.0, 0)], 1.0)],
        "size": 175, "tx": 960, "ty": 790, "gap": 218, "rot": -4,
    },
    "E_fazon_crveno": {
        "scale": 2.05, "cx": 960, "heads_y": 175,
        "badge_x": 560, "badge_y": 20, "badge_w": 800,
        "tat_x": 1920 - 40 - 330, "tat_y": 40, "tat_w": 330,
        "lines": [([("DOBILI ", WHITE, 1.0, 0), ("BATINE", RED, 1.32, 9)], 1.0),
                  ([("U SLOVAČKOJ?", WHITE, 1.0, 0)], 1.0)],
        "size": 175, "tx": 960, "ty": 790, "gap": 218, "rot": -4,
    },
}

if __name__ == "__main__":
    for name, v in VARIANTS.items():
        img = Image.fromarray(build(v))
        path = os.path.join(base.OUT, f"thumbnail_{name}.jpg")
        img.save(path, quality=93, subsampling=0, optimize=True)
        print(name, os.path.getsize(path) // 1024, "KB")
