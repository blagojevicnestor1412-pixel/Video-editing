"""Five different thumbnail concepts for the same video.

1 editorial   - black & white documentary look, one red word, text left / people right
2 flag        - waving Slovak flag fills the backdrop, sticker cut-out, title on top
3 red_slash   - aggressive diagonal red band, huge stacked title on the left
4 spotlight   - dark arena, single spotlight, giant red "?" behind the group
5 behind_text - big "SLOVAČKA" word placed BEHIND the group (depth layering)
"""
import os

import cv2
import numpy as np
import skia
from PIL import Image

import make_thumbnails as base
import make_thumbnail_v2 as v2
from make_thumbnails import W, H, LOGO_10P, PEOPLE_ANCHOR, matte, over, paste_logo, photo, place, place_alpha, plate, sharpen, ss

F = os.path.join(base.A, "fonts")
ANTON = skia.Typeface.MakeFromFile(os.path.join(F, "Anton_400Regular.ttf"))
ARCHIVO = skia.Typeface.MakeFromFile(os.path.join(F, "ArchivoBlack_400Regular.ttf"))
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
T_MARK = v2.T_MARK


# ------------------------------------------------------------------ helpers
def bg_plate(scale=1.95, dx=0, top=150, blur=7, gain=0.55, sat=1.0):
    bg = place(plate, scale, (W - base.PW * scale) / 2 + dx, -top * scale)
    bg = cv2.GaussianBlur(bg, (0, 0), blur)
    lum = bg.mean(2, keepdims=True)
    bg = lum + (bg - lum) * sat
    return np.clip(bg * gain, 0, 1)


def people(scale, cx, heads_y, mode="color"):
    ox, oy = cx - PEOPLE_ANCHOR[0] * scale, heads_y - PEOPLE_ANCHOR[1] * scale
    p = np.clip(place(photo, scale, ox, oy), 0, 1)
    a = np.clip(place_alpha(matte, scale, ox, oy), 0, 1)
    a = np.clip((a - 0.04) / 0.96, 0, 1)
    if mode == "bw":
        l = (p * np.array([0.30, 0.59, 0.11])).sum(2, keepdims=True)
        l = np.clip(0.5 + (l - 0.5) * 1.25, 0, 1) ** 0.95
        p = np.repeat(l, 3, 2)
    else:
        lum = p.mean(2, keepdims=True)
        p = lum + (p - lum) * 1.15
        p = np.clip(0.5 + (p - 0.5) * 1.10, 0, 1) * 1.06
    return sharpen(np.clip(p, 0, 1), 1.1, 0.6), a


def composite_people(canvas, p, a, outline=0, shadow=0.75, outline_fade=(950, 1070)):
    sh = cv2.GaussianBlur(np.roll(a, (14, 10), (0, 1)), (0, 0), 16) * shadow
    canvas = over(canvas, np.zeros(3), sh)
    if outline:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1))
        o = cv2.GaussianBlur(cv2.dilate((a > 0.5).astype(np.uint8), k).astype(np.float32), (0, 0), 1.0)
        o = o * (1 - ss(YY, *outline_fade))
        canvas = over(canvas, np.ones(3), o)
    return over(canvas, p, a)


def skia_layer(draw):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    draw(cv)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                            alphaType=skia.kUnpremul_AlphaType).astype(np.float32) / 255


def put(canvas, layer):
    return over(canvas, layer[..., :3], layer[..., 3])


def text_run(cv, txt, x, y, font, fill, stroke=0, stroke_rgb=(10, 10, 16), shadow=True, box=None, sheen=False):
    """Draws text at (x, y) baseline. fill: rgb tuple. box: rgb behind text."""
    w = font.measureText(txt)
    size = font.getSize()
    cap = size * 0.74
    if box:
        l, r, t, b = x - size * 0.10, x + w + size * 0.10, y - cap - size * 0.14, y + size * 0.12
        sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 190))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        cv.drawRect(skia.Rect.MakeLTRB(l + 12, t + 18, r + 12, b + 18), sp)
        cv.drawRect(skia.Rect.MakeLTRB(l, t, r, b), skia.Paint(AntiAlias=True, Color=skia.Color(*box)))
    if shadow and not box:
        p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 200))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.06))
        cv.drawString(txt, x + size * 0.04, y + size * 0.07, font, p)
    if stroke:
        p = skia.Paint(AntiAlias=True, Color=skia.Color(*stroke_rgb))
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        cv.drawString(txt, x, y, font, p)
    p = skia.Paint(AntiAlias=True, Color=skia.Color(*fill))
    if sheen:
        lo = tuple(int(c * 0.86) for c in fill)
        p.setShader(skia.GradientShader.MakeLinear(
            [(x, y - cap), (x + cap * 1.4, y + cap * 0.3)],
            [skia.Color(*fill), skia.Color(*lo), skia.Color(*fill)], [0, 0.5, 1], skia.TileMode.kMirror))
    cv.drawString(txt, x, y, font, p)
    return w


def finish(canvas, vignette=0.28, grain=0.012, seed=5):
    d = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
    canvas = canvas * (1 - vignette * ss(d, 0.7, 1.5))[..., None]
    rng = np.random.default_rng(seed)
    canvas = np.clip(canvas + rng.normal(0, grain, (H, W, 1)), 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


WHITE, RED, YELLOW = (255, 255, 255), (228, 30, 36), (255, 210, 20)


# ------------------------------------------------------------------ 1 editorial
def c1_editorial():
    canvas = bg_plate(dx=-250, gain=0.30, sat=0.0, blur=9)
    # soft light falloff behind the group on the right
    canvas = canvas * (1 + 0.9 * np.exp(-(((XX - 1300) / 700) ** 2 + ((YY - 520) / 500) ** 2)))[..., None]
    p, a = people(1.62, 1285, 430, "bw")
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.85)
    # darken left for type
    canvas = canvas * (1 - 0.55 * (1 - ss(XX, 380, 900)))[..., None]

    def draw(cv):
        cv.drawRect(skia.Rect.MakeXYWH(78, 118, 12, 560), skia.Paint(Color=skia.Color(*RED)))
        x = 122
        text_run(cv, "DOBILI", x, 300, skia.Font(ANTON, 200), WHITE)
        text_run(cv, "BATINE", x, 525, skia.Font(ANTON, 230), RED)
        text_run(cv, "U SLOVAČKOJ?", x, 675, skia.Font(ANTON, 120), WHITE)
    canvas = put(canvas, skia_layer(draw))
    canvas, _ = paste_logo(canvas, LOGO_10P, 86, 860, 250, shadow=0.6)
    canvas, _ = paste_logo(canvas, T_MARK, 360, 862, 120, shadow=0.6)
    return finish(canvas, vignette=0.35, grain=0.02)


# ------------------------------------------------------------------ 2 flag
def c2_flag():
    flag = v2.slovak_flag(2600)
    fh, fw = flag.shape[:2]
    canvas = np.zeros((H, W, 3), np.float32)
    x0, y0 = (W - fw) // 2 + 250, (H - fh) // 2 - 60
    big = np.zeros((H, W, 4), np.float32)
    ys, xs = max(0, y0), max(0, x0)
    big[ys:min(H, y0 + fh), xs:min(W, x0 + fw)] = flag[ys - y0:min(H, y0 + fh) - y0, xs - x0:min(W, x0 + fw) - x0]
    canvas = over(canvas, big[..., :3], big[..., 3])
    canvas = cv2.GaussianBlur(canvas, (0, 0), 5) * 0.55
    canvas, _ = paste_logo(canvas, LOGO_10P, 40, 360, 560, shadow=0.4, blur=3.5, opacity=0.9)
    p, a = people(1.85, 960, 455)
    canvas = composite_people(canvas, p, a, outline=7)
    canvas = canvas * (1 - 0.35 * (1 - ss(YY, 0, 430)))[..., None]
    t, _, _ = v2.title_f([[("DOBILI ", False), ("BATINE", True)], [("U SLOVAČKOJ?", False)]], 132, 960, 190, 172, -2,
                         (226, 24, 30), skew=-0.12, stroke=14, tf=ARCHIVO)
    canvas = put(canvas, t)
    canvas, _ = paste_logo(canvas, T_MARK, 1770, 940, 110, shadow=0.6)
    return finish(canvas)


# ------------------------------------------------------------------ 3 red slash
def c3_red_slash():
    canvas = bg_plate(gain=0.28, sat=0.6, blur=10)

    def band(cv):
        path = skia.Path()
        path.moveTo(560, 1080); path.lineTo(1180, 0); path.lineTo(1720, 0); path.lineTo(1100, 1080); path.close()
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear([(560, 1080), (1720, 0)],
                                                    [skia.Color(170, 10, 18), skia.Color(235, 32, 40)]))
        cv.drawPath(path, p)
        lp = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 200))
        for off in (-60, 600):
            q = skia.Path()
            q.moveTo(560 + off, 1080); q.lineTo(1180 + off, 0); q.lineTo(1192 + off, 0); q.lineTo(572 + off, 1080); q.close()
            cv.drawPath(q, lp)
    canvas = put(canvas, skia_layer(band))
    p, a = people(1.55, 1395, 450)
    canvas = composite_people(canvas, p, a, outline=6)
    canvas = canvas * (1 - 0.5 * (1 - ss(XX, 300, 760)))[..., None]

    def draw(cv):
        cv.save()
        cv.skew(-0.10, 0)
        x = 150
        text_run(cv, "DOBILI", x, 260, skia.Font(ARCHIVO, 120), WHITE, stroke=14)
        text_run(cv, "BATINE", x, 500, skia.Font(ANTON, 270), YELLOW, stroke=20)
        text_run(cv, "U SLOVAČKOJ?", x + 10, 630, skia.Font(ARCHIVO, 80), WHITE, stroke=11)
        cv.restore()
    canvas = put(canvas, skia_layer(draw))
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(210), 260, 830, -7, border=6, shadow=0.7)
    canvas, _ = paste_logo(canvas, LOGO_10P, 40, 960, 170, shadow=0.6)
    return finish(canvas)


# ------------------------------------------------------------------ 4 spotlight
def c4_spotlight():
    canvas = bg_plate(gain=0.22, sat=0.4, blur=12)

    def qmark(cv):
        f = skia.Font(ANTON, 1100)
        p = skia.Paint(AntiAlias=True, Color=skia.Color(200, 20, 30, 235))
        w = f.measureText("?")
        cv.save()
        cv.rotate(10, 1560, 560)
        cv.drawString("?", 1560 - w / 2, 1000, f, p)
        cv.restore()
    q = skia_layer(qmark)
    q[..., 3] = cv2.GaussianBlur(q[..., 3], (0, 0), 3)
    canvas = put(canvas, q)
    # spotlight cone from above
    cone = np.exp(-(((XX - 800) / (360 + 0.55 * YY)) ** 2)) * ss(YY, -100, 300)
    pool = np.exp(-(((XX - 800) / 820) ** 2 + ((YY - 700) / 420) ** 2))
    light = 0.20 * cone + 0.55 * pool
    canvas = 1 - (1 - canvas) * (1 - light[..., None] * np.array([1.0, 0.95, 0.85]))
    p, a = people(1.55, 800, 330)
    spot = 0.55 + 0.6 * np.exp(-(((XX - 800) / 900) ** 2 + ((YY - 450) / 650) ** 2))
    p = np.clip(p * spot[..., None], 0, 1)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)
    canvas = canvas * (1 - 0.75 * ss(YY, 760, 1080))[..., None]

    def draw(cv):
        f = skia.Font(ANTON, 128)
        parts = [("DOBILI ", WHITE), ("BATINE ", YELLOW), ("U SLOVAČKOJ?", WHITE)]
        total = sum(f.measureText(t) for t, _ in parts)
        x = 960 - total / 2
        for t, c in parts:
            x += text_run(cv, t, x, 1010, f, c, stroke=12)
    canvas = put(canvas, skia_layer(draw))
    canvas, _ = paste_logo(canvas, LOGO_10P, 40, 36, 220, shadow=0.6)
    canvas, _ = paste_logo(canvas, T_MARK, 1790, 36, 92, shadow=0.6)
    return finish(canvas, vignette=0.45)


# ------------------------------------------------------------------ 5 text behind
def c5_behind_text():
    canvas = bg_plate(gain=0.42, sat=0.9, blur=9)
    canvas = canvas * np.array([1.06, 0.98, 0.90])   # warm

    def big_word(cv):
        f = skia.Font(ANTON, 430)
        t = "SLOVAČKA"
        w = f.measureText(t)
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear([(0, 260), (0, 640)],
                                                    [skia.Color(255, 255, 255), skia.Color(225, 228, 236)]))
        cv.drawString(t, 960 - w / 2, 640, f, p)
    bw = skia_layer(big_word)
    sh = cv2.GaussianBlur(np.roll(bw[..., 3], (16, 10), (0, 1)), (0, 0), 14) * 0.6
    canvas = over(canvas, np.zeros(3), sh)
    canvas = put(canvas, bw)
    p, a = people(1.70, 960, 500)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)
    canvas = canvas * (1 - 0.6 * ss(YY, 780, 1080))[..., None]

    def front(cv):
        f = skia.Font(ARCHIVO, 104)
        parts = [("DOBILI ", None), ("BATINE?", RED)]
        total = sum(f.measureText(t) for t, _ in parts) + 30
        x = 960 - total / 2
        for t, box in parts:
            x += text_run(cv, t, x, 1000, f, WHITE, stroke=0 if box else 12, box=box) + (30 if box is None else 0)
    canvas = put(canvas, skia_layer(front))
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(170), 1760, 110, -8, border=5, shadow=0.6)
    canvas, _ = paste_logo(canvas, LOGO_10P, 40, 36, 220, shadow=0.6)
    return finish(canvas)


CONCEPTS = {
    "1_editorial_cb": c1_editorial,
    "2_zastava": c2_flag,
    "3_crvena_dijagonala": c3_red_slash,
    "4_reflektor": c4_spotlight,
    "5_tekst_iza_nas": c5_behind_text,
}

if __name__ == "__main__":
    os.makedirs(os.path.join(base.OUT, "concepts"), exist_ok=True)
    for name, fn in CONCEPTS.items():
        img = Image.fromarray(fn())
        path = os.path.join(base.OUT, "concepts", f"koncept_{name}.jpg")
        img.save(path, quality=93, subsampling=0, optimize=True)
        print(name, os.path.getsize(path) // 1024, "KB")
