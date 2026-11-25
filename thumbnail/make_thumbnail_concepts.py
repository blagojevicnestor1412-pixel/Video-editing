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


# ====================================================================== round 2
def serbian_flag(width=300):
    """Serbian civil flag (red/blue/white tricolour), with the same cloth wave as the Slovak one."""
    fw, fh = width, int(width * 2 / 3)
    arr = np.zeros((fh, fw, 4), np.float32)
    for i, c in enumerate([(198, 54, 60), (12, 64, 118), (255, 255, 255)]):
        arr[int(i * fh / 3):int((i + 1) * fh / 3) + 1, :, :3] = np.array(c) / 255
    arr[..., 3] = 1
    yy, xx = np.mgrid[0:fh, 0:fw].astype(np.float32)
    ph = xx / fw * 2 * np.pi * 1.3
    arr = cv2.remap(arr, xx, yy - np.sin(ph) * fh * 0.035, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    arr[..., :3] = np.clip(arr[..., :3] * (1 + 0.16 * np.cos(ph))[..., None], 0, 1)
    return arr


def c6_route():
    canvas = bg_plate(gain=0.30, sat=0.7, blur=10)
    p, a = people(1.55, 1340, 480)
    canvas = composite_people(canvas, p, a, outline=6)
    canvas = canvas * (1 - 0.55 * (1 - ss(XX, 350, 820)))[..., None]
    canvas = v2.paste_rgba_rot(canvas, serbian_flag(200), 190, 190, -6, border=6, shadow=0.7)
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(200), 760, 150, 6, border=6, shadow=0.7)

    def draw(cv):
        path = skia.Path()
        path.moveTo(300, 150)
        path.quadTo(475, -10, 640, 120)
        p = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255))
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(7)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setPathEffect(skia.DashPathEffect.Make([22, 18], 0))
        cv.drawPath(path, p)
        head = skia.Path()
        head.moveTo(662, 138); head.lineTo(618, 132); head.lineTo(646, 98); head.close()
        cv.drawPath(head, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        text_run(cv, "SRBIJA", 120, 330, skia.Font(ARCHIVO, 44), (220, 222, 230), stroke=6)
        text_run(cv, "SLOVAČKA", 640, 300, skia.Font(ARCHIVO, 44), (220, 222, 230), stroke=6)
        text_run(cv, "DOBILI", 80, 540, skia.Font(ANTON, 150), WHITE, stroke=14)
        text_run(cv, "BATINE?", 80, 735, skia.Font(ANTON, 190), WHITE, stroke=0, box=RED)
    canvas = put(canvas, skia_layer(draw))
    canvas, _ = paste_logo(canvas, LOGO_10P, 60, 900, 200, shadow=0.6)
    return finish(canvas)


def c7_polaroid():
    canvas = bg_plate(gain=0.25, sat=0.5, blur=16) * np.array([1.05, 1.0, 0.92])
    # the "photo" inside the polaroid
    inner = bg_plate(gain=0.55, sat=1.0, blur=6)
    p, a = people(1.30, 960, 300)
    inner = composite_people(inner, p, a, outline=0, shadow=0.6)
    ph = inner[170:790, 410:1510]
    ph = np.clip(0.04 + ph * 0.96, 0, 1)
    pw, phh = ph.shape[1], ph.shape[0]
    m = 34
    card = np.ones((phh + m + 150, pw + 2 * m, 4), np.float32)
    card[..., :3] = np.array([0.97, 0.96, 0.93])
    card[m:m + phh, m:m + pw, :3] = ph
    pil = Image.fromarray((card * 255).astype(np.uint8))
    card = np.array(pil.resize((int(pil.width * 0.92), int(pil.height * 0.92)), Image.LANCZOS)).astype(np.float32) / 255

    def caption(cv):
        pass
    canvas = v2.paste_rgba_rot(canvas, card, 700, 545, 4, border=0, shadow=0.85)

    def draw(cv):
        cv.save(); cv.rotate(4, 700, 545)
        f = skia.Font(ARCHIVO, 36)
        t = "10TH PLANET BELGRADE  ×  TATAMY"
        cv.drawString(t, 700 - f.measureText(t) / 2, 545 + card.shape[0] / 2 - 52, f,
                      skia.Paint(AntiAlias=True, Color=skia.Color(40, 40, 46)))
        for (tx, ty, ang) in [(290, 545 - card.shape[0] / 2 + 6, -30), (1110, 545 - card.shape[0] / 2 + 6, 28)]:
            cv.save(); cv.rotate(ang, tx, ty)
            cv.drawRect(skia.Rect.MakeXYWH(tx - 90, ty - 26, 180, 52),
                        skia.Paint(AntiAlias=True, Color=skia.Color(235, 225, 196, 210)))
            cv.restore()
        cv.restore()
        x = 1360
        text_run(cv, "DOBILI", x, 330, skia.Font(ANTON, 150), WHITE, stroke=12)
        text_run(cv, "BATINE", x, 530, skia.Font(ANTON, 190), RED, stroke=14)
        text_run(cv, "U SLOVAČKOJ?", x, 650, skia.Font(ANTON, 92), WHITE, stroke=10)
        u = skia.Paint(AntiAlias=True, Color=skia.Color(*RED))
        u.setStyle(skia.Paint.kStroke_Style); u.setStrokeWidth(12); u.setStrokeCap(skia.Paint.kRound_Cap)
        path = skia.Path(); path.moveTo(x, 690); path.quadTo(x + 230, 668, x + 470, 694)
        cv.drawPath(path, u)
    canvas = put(canvas, skia_layer(draw))
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(190), 1590, 860, -8, border=6, shadow=0.7)
    return finish(canvas, vignette=0.4, grain=0.018)


def c8_giant_word():
    canvas = bg_plate(gain=0.32, sat=0.8, blur=9)

    def word(cv):
        f = skia.Font(ANTON, 560)
        t = "BATINE"
        w = f.measureText(t)
        x = 960 - w / 2
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear([(0, 60), (0, 560)],
                                                    [skia.Color(240, 40, 44), skia.Color(170, 12, 20)]))
        cv.drawString(t, x, 600, f, p)
    wl = skia_layer(word)
    sh = cv2.GaussianBlur(np.roll(wl[..., 3], (18, 12), (0, 1)), (0, 0), 16) * 0.7
    canvas = over(canvas, np.zeros(3), sh)
    canvas = put(canvas, wl)
    p, a = people(1.65, 960, 470)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.95)
    canvas = canvas * (1 - 0.7 * ss(YY, 820, 1080))[..., None]

    def draw(cv):
        text_run(cv, "DOBILI", 150, 150, skia.Font(ARCHIVO, 84), WHITE, stroke=12)
        f = skia.Font(ARCHIVO, 92)
        t = "U SLOVAČKOJ?"
        text_run(cv, t, 960 - f.measureText(t) / 2, 1030, f, WHITE, stroke=12)
    canvas = put(canvas, skia_layer(draw))
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(170), 1740, 105, 8, border=5, shadow=0.7)
    canvas, _ = paste_logo(canvas, LOGO_10P, 40, 930, 190, shadow=0.6)
    return finish(canvas)


def c9_torn_paper():
    canvas = bg_plate(gain=0.45, sat=1.0, blur=8)
    canvas, _ = paste_logo(canvas, LOGO_10P, 80, 60, 700, shadow=0.4, blur=4, opacity=0.9)
    canvas, _ = paste_logo(canvas, T_MARK, 1350, 50, 420, shadow=0.4, blur=4, opacity=0.9)
    p, a = people(1.85, 960, 300)
    canvas = composite_people(canvas, p, a, outline=7)
    rng = np.random.default_rng(11)

    def paper(cv):
        cv.save(); cv.rotate(-3, 960, 860)
        top, bot = 730, 1000
        path = skia.Path()
        xs = np.arange(-60, W + 80, 26)
        path.moveTo(-60, top)
        for x in xs:
            path.lineTo(float(x), float(top + rng.uniform(-14, 14)))
        for x in xs[::-1]:
            path.lineTo(float(x), float(bot + rng.uniform(-14, 14)))
        path.close()
        sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 170))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        cv.save(); cv.translate(8, 14); cv.drawPath(path, sp); cv.restore()
        cv.drawPath(path, skia.Paint(AntiAlias=True, Color=skia.Color(244, 241, 232)))
        f = skia.Font(ANTON, 150)
        parts = [("DOBILI ", (18, 18, 22)), ("BATINE ", RED), ("U SLOVAČKOJ?", (18, 18, 22))]
        total = sum(f.measureText(t) for t, _ in parts)
        x = 960 - total / 2
        for t, c in parts:
            x += text_run(cv, t, x, 925, f, c, shadow=False)
        cv.restore()
    layer = skia_layer(paper)
    # paper grain
    noise = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.2) * 0.035
    layer[..., :3] = np.clip(layer[..., :3] + noise[..., None] * (layer[..., :3] > 0.8), 0, 1)
    canvas = put(canvas, layer)
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(170), 1760, 690, 10, border=5, shadow=0.7)
    return finish(canvas)


def c10_broadcast():
    canvas = bg_plate(gain=0.42, sat=1.0, blur=8)
    canvas, _ = paste_logo(canvas, T_MARK, 1320, 120, 430, shadow=0.4, blur=4.5, opacity=0.9)
    p, a = people(1.80, 960, 330)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)
    canvas = canvas * (1 - 0.5 * ss(YY, 700, 1080))[..., None]

    def draw(cv):
        # lower-third: red tab + white bar
        tab = skia.Rect.MakeXYWH(120, 760, 560, 70)
        cv.drawRect(tab, skia.Paint(AntiAlias=True, Color=skia.Color(*RED)))
        f_tab = skia.Font(ARCHIVO, 40)
        cv.drawString("10TH PLANET BELGRADE", 190, 810, f_tab, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        bar = skia.Rect.MakeXYWH(120, 830, 1680, 170)
        sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 160))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
        cv.drawRect(skia.Rect.MakeXYWH(132, 846, 1680, 170), sp)
        g = skia.Paint(AntiAlias=True)
        g.setShader(skia.GradientShader.MakeLinear([(0, 830), (0, 1000)],
                                                    [skia.Color(255, 255, 255), skia.Color(228, 230, 236)]))
        cv.drawRect(bar, g)
        cv.drawRect(skia.Rect.MakeXYWH(120, 830, 18, 170), skia.Paint(Color=skia.Color(*RED)))
        f = skia.Font(ANTON, 128)
        x = 330
        for t, c in [("DOBILI ", (16, 16, 20)), ("BATINE ", RED), ("U SLOVAČKOJ?", (16, 16, 20))]:
            x += text_run(cv, t, x, 970, f, c, shadow=False)
    canvas = put(canvas, skia_layer(draw))
    canvas, _ = paste_logo(canvas, LOGO_10P, 132, 776 + 70, 180, shadow=0.0)
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(150), 1720, 770, 0, border=5, shadow=0.6)
    return finish(canvas, vignette=0.3)


CONCEPTS2 = {
    "6_ruta_srbija_slovacka": c6_route,
    "7_polaroid": c7_polaroid,
    "8_ogromna_rec": c8_giant_word,
    "9_pocepan_papir": c9_torn_paper,
    "10_tv_prenos": c10_broadcast,
}

if __name__ == "__main__":
    os.makedirs(os.path.join(base.OUT, "concepts"), exist_ok=True)
    import sys
    todo = CONCEPTS2 if "round2" in sys.argv else CONCEPTS
    for name, fn in todo.items():
        img = Image.fromarray(fn())
        path = os.path.join(base.OUT, "concepts", f"koncept_{name}.jpg")
        img.save(path, quality=93, subsampling=0, optimize=True)
        print(name, os.path.getsize(path) // 1024, "KB")
