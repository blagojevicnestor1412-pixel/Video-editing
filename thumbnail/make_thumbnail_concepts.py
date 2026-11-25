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


# ====================================================================== round 3
def centered_line(cv, parts, y, font, stroke=12, shadow=True):
    total = sum(font.measureText(t) for t, *_ in parts)
    x = 960 - total / 2
    for part in parts:
        t, c = part[0], part[1]
        box = part[2] if len(part) > 2 else None
        x += text_run(cv, t, x, y, font, c, stroke=0 if box else stroke, box=box, shadow=shadow)


def c11_lineup():
    g = 0.16 + 0.10 * np.exp(-(((XX - 960) / 900) ** 2 + ((YY - 500) / 600) ** 2))
    canvas = np.repeat(g[..., None], 3, 2) * np.array([0.95, 0.97, 1.0])

    def chart(cv):
        f = skia.Font(ARCHIVO, 30)
        for k, y in enumerate(range(240, 1080, 70)):
            cm = 210 - k * 10
            major = True
            lp = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 120))
            cv.drawRect(skia.Rect.MakeXYWH(0, y, W, 3), lp)
            for xx in (24, W - 90):
                cv.drawString(str(cm), xx, y - 10, f, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 170)))
            for j in range(1, 5):
                cv.drawRect(skia.Rect.MakeXYWH(0, y + j * 14, 40, 2), lp)
                cv.drawRect(skia.Rect.MakeXYWH(W - 40, y + j * 14, 40, 2), lp)
    canvas = put(canvas, skia_layer(chart))
    p, a = people(1.62, 960, 420)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)

    def draw(cv):
        centered_line(cv, [("DOBILI ", WHITE), ("BATINE", WHITE, RED), (" U SLOVAČKOJ?", WHITE)], 175, skia.Font(ANTON, 132))
        r = skia.Rect.MakeXYWH(560, 930, 800, 120)
        cv.drawRect(skia.Rect.MakeXYWH(572, 946, 800, 120), skia.Paint(Color=skia.Color(0, 0, 0, 150)))
        cv.drawRect(r, skia.Paint(Color=skia.Color(14, 14, 18)))
        f = skia.Font(ARCHIVO, 40)
        for t, y, c in [("10TH PLANET BELGRADE", 980, (255, 255, 255)), ("TATAMY  •  SLOVAČKA", 1032, (230, 40, 46))]:
            cv.drawString(t, 960 - f.measureText(t) / 2, y, f, skia.Paint(AntiAlias=True, Color=skia.Color(*c)))
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas, vignette=0.35)


def duotone(img, dark=(0.05, 0.0, 0.02), mid=(0.80, 0.07, 0.12), light=(1.0, 0.93, 0.90)):
    l = (img * np.array([0.30, 0.59, 0.11])).sum(2, keepdims=True)
    l = np.clip(0.5 + (l - 0.5) * 1.3, 0, 1)
    d, m, li = (np.array(c) for c in (dark, mid, light))
    lo = d + (m - d) * np.clip(l * 2, 0, 1)
    hi = m + (li - m) * np.clip(l * 2 - 1, 0, 1)
    return np.where(l < 0.5, lo, hi)


def c12_duotone():
    canvas = duotone(bg_plate(gain=0.6, blur=10)) * 0.55
    p, a = people(1.80, 960, 455)
    p = duotone(p)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)

    def draw(cv):
        centered_line(cv, [("DOBILI ", WHITE), ("BATINE", (16, 10, 12), WHITE)], 205, skia.Font(ANTON, 175), stroke=14)
        centered_line(cv, [("U SLOVAČKOJ?", WHITE)], 405, skia.Font(ANTON, 150), stroke=14)
    canvas = put(canvas, skia_layer(draw))
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(190), 1730, 300, -8, border=6, shadow=0.7)
    canvas = v2.paste_rgba_rot(canvas, LOGO_10P[::2, ::2], 170, 300, 6, border=0, shadow=0.6) if False else canvas
    canvas, _ = paste_logo(canvas, LOGO_10P, 60, 210, 230, shadow=0.6)
    return finish(canvas, vignette=0.35, grain=0.02)


def c13_magazine():
    canvas = bg_plate(gain=0.40, sat=0.9, blur=10) * np.array([0.95, 0.97, 1.04])

    def mast(cv):
        f = skia.Font(ANTON, 330)
        t = "10TH PLANET"
        w = f.measureText(t)
        sx = (W - 80) / w
        cv.save(); cv.translate(40, 320); cv.scale(sx, 1)
        cv.drawString(t, 0, 0, f, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        cv.restore()
    m = skia_layer(mast)
    canvas = over(canvas, np.zeros(3), cv2.GaussianBlur(np.roll(m[..., 3], (10, 6), (0, 1)), (0, 0), 10) * 0.5)
    canvas = put(canvas, m)
    p, a = people(1.75, 1080, 300)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.9)
    canvas = canvas * (1 - 0.6 * (1 - ss(XX, 250, 700)) * ss(YY, 340, 470))[..., None] * (1 - 0.55 * ss(YY, 700, 1080))[..., None]

    def draw(cv):
        f = skia.Font(ARCHIVO, 34)
        cv.drawString("BELGRADE  •  JIU JITSU  •  VLOG", 46, 372, f, skia.Paint(AntiAlias=True, Color=skia.Color(230, 40, 46)))
        x = 60
        text_run(cv, "TATAMY", x, 520, skia.Font(ARCHIVO, 58), RED, stroke=8)
        text_run(cv, "TURNIR U", x, 580, skia.Font(ARCHIVO, 44), WHITE, stroke=7)
        text_run(cv, "SLOVAČKOJ", x, 632, skia.Font(ARCHIVO, 44), WHITE, stroke=7)
        text_run(cv, "DOBILI BATINE", x, 900, skia.Font(ANTON, 140), WHITE, stroke=14)
        text_run(cv, "U SLOVAČKOJ?", x, 1035, skia.Font(ANTON, 120), YELLOW, stroke=14)
        # barcode
        rng = np.random.default_rng(3)
        bx, by = 1690, 900
        cv.drawRect(skia.Rect.MakeXYWH(bx - 14, by - 14, 210, 150), skia.Paint(Color=skia.Color(255, 255, 255)))
        xx = bx
        while xx < bx + 180:
            wbar = int(rng.integers(2, 7))
            if rng.random() > 0.4:
                cv.drawRect(skia.Rect.MakeXYWH(xx, by, wbar, 100), skia.Paint(Color=skia.Color(0, 0, 0)))
            xx += wbar + 2
        cv.drawString("10P-BGD", bx + 30, by + 128, skia.Font(ARCHIVO, 22), skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0)))
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas, vignette=0.25)


def c14_scoreboard():
    canvas = bg_plate(gain=0.42, sat=1.0, blur=8)
    canvas, _ = paste_logo(canvas, T_MARK, 1380, 300, 380, shadow=0.4, blur=4.5, opacity=0.85)
    canvas, _ = paste_logo(canvas, LOGO_10P, 60, 320, 600, shadow=0.4, blur=4.5, opacity=0.85)
    p, a = people(1.70, 960, 330)
    canvas = composite_people(canvas, p, a, outline=6)
    canvas = canvas * (1 - 0.65 * ss(YY, 760, 1080))[..., None]

    def draw(cv):
        bar = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(440, 40, 1040, 150), 26, 26)
        sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 160))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
        cv.save(); cv.translate(8, 14); cv.drawRRect(bar, sp); cv.restore()
        cv.drawRRect(bar, skia.Paint(AntiAlias=True, Color=skia.Color(16, 16, 22)))
        cv.drawRect(skia.Rect.MakeXYWH(830, 40, 260, 150), skia.Paint(Color=skia.Color(*RED)))
        f = skia.Font(ANTON, 120)
        t = "? : ?"
        cv.drawString(t, 960 - f.measureText(t) / 2, 160, f, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        f2 = skia.Font(ARCHIVO, 70)
        cv.drawString("SRB", 625, 142, f2, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        cv.drawString("SVK", 1112, 142, f2, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        centered_line(cv, [("DOBILI ", WHITE), ("BATINE", YELLOW), (" U SLOVAČKOJ?", WHITE)], 1015, skia.Font(ANTON, 128))
    canvas = put(canvas, skia_layer(draw))
    canvas = v2.paste_rgba_rot(canvas, serbian_flag(130), 530, 115, 0, border=4, shadow=0.5)
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(130), 1390, 115, 0, border=4, shadow=0.5)
    return finish(canvas)


def c15_camcorder():
    canvas = bg_plate(gain=0.55, sat=1.0, blur=6) * np.array([1.05, 1.0, 0.94])
    p, a = people(1.80, 960, 330)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.8)
    canvas = canvas * (1 - 0.55 * ss(YY, 650, 1000))[..., None]
    # slight chromatic aberration + scanlines for the camcorder feel
    ca = canvas.copy()
    ca[..., 0] = np.roll(canvas[..., 0], 3, 1)
    ca[..., 2] = np.roll(canvas[..., 2], -3, 1)
    canvas = ca * (1 - 0.06 * (np.floor(YY / 3) % 2 == 0))[..., None]

    def draw(cv):
        wp = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 235))
        wp.setStyle(skia.Paint.kStroke_Style); wp.setStrokeWidth(8)
        L, m = 120, 60
        for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
            path = skia.Path(); path.moveTo(x, y + sy * L); path.lineTo(x, y); path.lineTo(x + sx * L, y)
            cv.drawPath(path, wp)
        cv.drawCircle(130, 130, 20, skia.Paint(AntiAlias=True, Color=skia.Color(*RED)))
        f = skia.Font(ARCHIVO, 54)
        cv.drawString("REC", 168, 150, f, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        bp = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)); bp.setStyle(skia.Paint.kStroke_Style); bp.setStrokeWidth(5)
        cv.drawRect(skia.Rect.MakeXYWH(W - 250, 105, 120, 54), bp)
        cv.drawRect(skia.Rect.MakeXYWH(W - 130, 120, 12, 24), skia.Paint(Color=skia.Color(255, 255, 255)))
        for k in range(3):
            cv.drawRect(skia.Rect.MakeXYWH(W - 240 + k * 36, 115, 28, 34), skia.Paint(Color=skia.Color(255, 255, 255)))
        cp = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 160)); cp.setStrokeWidth(3)
        
        centered_line(cv, [("DOBILI ", WHITE), ("BATINE", WHITE, RED)], 860, skia.Font(ANTON, 150))
        centered_line(cv, [("U SLOVAČKOJ?", WHITE)], 1000, skia.Font(ANTON, 120))
    canvas = put(canvas, skia_layer(draw))
    canvas, _ = paste_logo(canvas, LOGO_10P, W - 290, 190, 200, shadow=0.6)
    canvas = v2.paste_rgba_rot(canvas, v2.slovak_flag(140), 190, 250, -6, border=4, shadow=0.6)
    return finish(canvas, vignette=0.4, grain=0.022)


CONCEPTS3 = {
    "11_policijski_lineup": c11_lineup,
    "12_duotone_crveno": c12_duotone,
    "13_magazin": c13_magazine,
    "14_semafor": c14_scoreboard,
    "15_kamera_rec": c15_camcorder,
}


# ====================================================================== round 4
def head_pos(scale, cx, heads_y, photo_xy=(628, 590)):
    """thumbnail position of a photo point (default: middle guy's face)."""
    return cx + (photo_xy[0] - PEOPLE_ANCHOR[0]) * scale, heads_y + (photo_xy[1] - PEOPLE_ANCHOR[1]) * scale


def decontaminate(p, a, sigma=3.0):
    """push interior colours outwards over the matte edge (removes dark backdrop fringe)."""
    core = (a > 0.97).astype(np.float32)
    num = cv2.GaussianBlur(p * core[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(core, (0, 0), sigma)[..., None]
    est = num / np.maximum(den, 1e-4)
    edge = ((a > 0.01) & (a < 0.97)).astype(np.float32)[..., None] * (den > 0.02)
    return p * (1 - edge) + est * edge


def tracked(cv, txt, x, y, font, paint, tracking):
    for ch in txt:
        cv.drawString(ch, x, y, font, paint)
        x += font.measureText(ch) + tracking
    return x


def tracked_width(txt, font, tracking):
    return sum(font.measureText(ch) for ch in txt) + tracking * (len(txt) - 1)


def c16_light_mode():
    d = np.sqrt(((XX - 960) / 1100) ** 2 + ((YY - 520) / 800) ** 2)
    canvas = (0.97 - 0.14 * ss(d, 0.2, 1.3))[..., None] * np.array([1.0, 0.99, 0.97])
    canvas = np.repeat(canvas, 1, 2) if canvas.shape[2] == 3 else canvas
    p, a = people(1.75, 960, 470)
    p = decontaminate(p, a)
    a = ss(a, 0.25, 0.95)
    sh = cv2.GaussianBlur(np.roll(a, (22, 0), (0, 1)), (0, 0), 28) * 0.35
    canvas = over(canvas, np.zeros(3), sh)
    canvas = over(canvas, p, a)
    ink = (18, 18, 22)

    def draw(cv):
        f = skia.Font(ANTON, 185)
        parts = [("DOBILI ", ink), ("BATINE", RED)]
        x = 960 - sum(f.measureText(t) for t, _ in parts) / 2
        for t, c in parts:
            x += text_run(cv, t, x, 215, f, c, shadow=False)
        f2 = skia.Font(ANTON, 150)
        t = "U SLOVAČKOJ?"
        text_run(cv, t, 960 - f2.measureText(t) / 2, 405, f2, ink, shadow=False)
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas, vignette=0.08, grain=0.008)


def bandaid(cv, cx, cy, angle, length=300, width=86):
    cv.save()
    cv.translate(cx, cy)
    cv.rotate(angle)
    sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 120))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-length / 2, -width / 2, length, width), width / 2, width / 2)
    cv.save(); cv.translate(5, 8); cv.drawRRect(r, sp); cv.restore()
    g = skia.Paint(AntiAlias=True)
    g.setShader(skia.GradientShader.MakeLinear([(0, -width / 2), (0, width / 2)],
                                               [skia.Color(240, 204, 168), skia.Color(214, 170, 130)]))
    cv.drawRRect(r, g)
    pad = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-length * 0.17, -width * 0.36, length * 0.34, width * 0.72), 8, 8)
    cv.drawRRect(pad, skia.Paint(AntiAlias=True, Color=skia.Color(236, 222, 206)))
    dots = skia.Paint(AntiAlias=True, Color=skia.Color(190, 148, 110))
    for sx in (-1, 1):
        for i in range(3):
            for j in range(2):
                cv.drawCircle(sx * (length * 0.27 + i * 16), -12 + j * 24, 3.2, dots)
    cv.restore()


def c17_bandaid():
    canvas = bg_plate(gain=0.32, sat=0.8, blur=9)
    p, a = people(1.82, 960, 460)
    canvas = composite_people(canvas, p, a, outline=6)
    canvas = canvas * (1 - 0.45 * (1 - ss(YY, 0, 450)))[..., None]

    def draw(cv):
        f = skia.Font(ANTON, 185)
        parts = [("DOBILI ", None), ("BATINE", RED)]
        total = sum(f.measureText(t) for t, _ in parts) + 20
        x = 960 - total / 2
        box_x = None
        for t, box in parts:
            if box:
                box_x = (x + 20, x + 20 + f.measureText(t))
                text_run(cv, t, x + 20, 225, f, WHITE, box=box)
            else:
                x += text_run(cv, t, x, 225, f, WHITE, stroke=16)
        f2 = skia.Font(ANTON, 150)
        t = "U SLOVAČKOJ?"
        text_run(cv, t, 960 - f2.measureText(t) / 2, 415, f2, WHITE, stroke=14)
        # band-aids stuck on the red box
        bandaid(cv, box_x[1] + 62, 80, 36, 200, 62)
        bandaid(cv, box_x[1] + 62, 80, -36, 200, 62)
        bandaid(cv, box_x[0] - 10, 250, -14, 210, 64)
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas)


def c18_focus():
    s_, cx_, hy_ = 1.95, 1120, 330
    canvas = bg_plate(gain=0.35, sat=0.8, blur=12)
    p, a = people(s_, cx_, hy_)
    full = composite_people(canvas, p, a, outline=0, shadow=0.85)
    hx, hy = head_pos(s_, cx_, hy_, (621, 641))
    focus = np.exp(-(((XX - hx) / 300) ** 2 + ((YY - hy - 130) / 560) ** 2))
    focus = np.clip(focus * 1.6, 0, 1)[..., None]
    blurred = cv2.GaussianBlur(full, (0, 0), 7)
    lum = blurred.mean(2, keepdims=True)
    blurred = (lum + (blurred - lum) * 0.4) * 0.55
    canvas = full * focus + blurred * (1 - focus)
    canvas = canvas * (1 - 0.45 * (1 - ss(XX, 250, 800)))[..., None]

    def draw(cv):
        x = 70
        text_run(cv, "DOBILI", x, 300, skia.Font(ANTON, 160), WHITE, stroke=14)
        text_run(cv, "BATINE?", x, 520, skia.Font(ANTON, 205), WHITE, box=RED)
        text_run(cv, "U SLOVAČKOJ", x, 650, skia.Font(ANTON, 110), WHITE, stroke=12)
        # hand-drawn circle around his face + arrow
        rp = skia.Paint(AntiAlias=True, Color=skia.Color(*RED))
        rp.setStyle(skia.Paint.kStroke_Style); rp.setStrokeWidth(11); rp.setStrokeCap(skia.Paint.kRound_Cap)
        for k, (dx, dy, rx, ry) in enumerate([(0, 0, 135, 165), (6, -4, 128, 160)]):
            path = skia.Path()
            n = 60
            for j in range(n + 8):
                t_ = j / n * 2 * np.pi
                px = hx + dx + rx * np.cos(t_) * (1 + 0.03 * np.sin(3 * t_ + k))
                py = hy - 10 + dy + ry * np.sin(t_)
                (path.moveTo if j == 0 else path.lineTo)(float(px), float(py))
            rp.setAlphaf(1.0 if k == 0 else 0.6)
            cv.drawPath(path, rp)
        rp.setAlphaf(1.0)
        arrow = skia.Path()
        ax0, ay0 = 560, 700
        ax1, ay1 = hx - 150, hy + 60
        arrow.moveTo(ax0, ay0)
        arrow.quadTo(ax0 + 150, ay1 + 140, ax1, ay1)
        cv.drawPath(arrow, rp)
        ang = np.arctan2(ay1 - (ay1 + 140), ax1 - (ax0 + 150))
        for da in (2.6, -2.6):
            cv.drawLine(ax1, ay1, float(ax1 + 45 * np.cos(ang + da)), float(ay1 + 45 * np.sin(ang + da)), rp)
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas)


def c19_comic():
    cx0, cy0 = 980, 560
    ang = np.arctan2(YY - cy0, XX - cx0)
    rays = (np.floor((ang + np.pi) / (2 * np.pi) * 28) % 2)[..., None]
    canvas = rays * np.array([1.0, 0.84, 0.05]) + (1 - rays) * np.array([1.0, 0.62, 0.02])

    def dots(cv):
        p = skia.Paint(AntiAlias=True, Color=skia.Color(220, 70, 0, 120))
        for y in range(0, H + 24, 24):
            for x in range(0, W + 24, 24):
                d = np.hypot(x - cx0, y - cy0) / 1100
                r = 1.0 + 6.5 * min(1, d)
                cv.drawCircle(x + (12 if (y // 24) % 2 else 0), y, r, p)
    canvas = put(canvas, skia_layer(dots))
    s_, cx_, hy_ = 1.75, 1000, 480
    p, a = people(s_, cx_, hy_)
    lum = p.mean(2, keepdims=True)
    p = np.clip(lum + (p - lum) * 1.25, 0, 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    blk = cv2.GaussianBlur(cv2.dilate((a > 0.5).astype(np.uint8), k).astype(np.float32), (0, 0), 0.8)
    canvas = over(canvas, np.zeros(3), cv2.GaussianBlur(np.roll(blk, (16, 12), (0, 1)), (0, 0), 3) * 0.6)
    canvas = over(canvas, np.array([0.04, 0.04, 0.05]), blk)
    canvas = over(canvas, p, a)
    hx, hy = head_pos(s_, cx_, hy_, (628, 560))

    def bubble(cv):
        rect = skia.Rect.MakeXYWH(150, 40, 1250, 380)
        tail = skia.Path()
        tail.moveTo(820, 380); tail.lineTo(float(hx - 10), float(hy - 60)); tail.lineTo(960, 360); tail.close()
        oval = skia.Path(); oval.addOval(rect)
        shape = skia.Op(oval, tail, skia.PathOp.kUnion_PathOp)
        sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 150))
        cv.save(); cv.translate(14, 18); cv.drawPath(shape, sp); cv.restore()
        cv.drawPath(shape, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)))
        bp = skia.Paint(AntiAlias=True, Color=skia.Color(10, 10, 12))
        bp.setStyle(skia.Paint.kStroke_Style); bp.setStrokeWidth(10); bp.setStrokeJoin(skia.Paint.kRound_Join)
        cv.drawPath(shape, bp)
        f = skia.Font(ANTON, 120)
        ink = (14, 14, 18)
        parts = [("DOBILI ", ink), ("BATINE", RED)]
        x = 775 - sum(f.measureText(t) for t, _ in parts) / 2
        for t, c in parts:
            x += text_run(cv, t, x, 215, f, c, shadow=False)
        f2 = skia.Font(ANTON, 100)
        t = "U SLOVAČKOJ?!"
        text_run(cv, t, 775 - f2.measureText(t) / 2, 335, f2, ink, shadow=False)
    canvas = put(canvas, skia_layer(bubble))
    return finish(canvas, vignette=0.15, grain=0.006)


def c20_cinema():
    canvas = bg_plate(gain=0.45, sat=0.8, blur=10)
    p, a = people(1.55, 960, 300)
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.85)
    # teal & orange grade
    lum = canvas.mean(2, keepdims=True)
    canvas = canvas + (1 - lum) * np.array([-0.03, 0.02, 0.05]) * 1.2 + lum * np.array([0.05, 0.01, -0.04])
    canvas = np.clip(0.5 + (canvas - 0.5) * 1.12, 0, 1)
    canvas = canvas * (1 - 0.7 * ss(YY, 620, 930))[..., None]
    bar = 132
    canvas[:bar] = 0
    canvas[H - bar:] = 0

    def draw(cv):
        f = skia.Font(ARCHIVO, 30)
        pg = skia.Paint(AntiAlias=True, Color=skia.Color(200, 200, 205))
        t = "10TH PLANET BELGRADE PREDSTAVLJA"
        tracked(cv, t, 960 - tracked_width(t, f, 12) / 2, 80, f, pg, 12)
        f1 = skia.Font(ANTON, 170)
        w1 = tracked_width("DOBILI BATINE", f1, 10)
        x = 960 - w1 / 2
        sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 200))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12))
        tracked(cv, "DOBILI BATINE", x + 6, 818, f1, sh, 10)
        x = tracked(cv, "DOBILI ", x, 810, f1, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255)), 10)
        tracked(cv, "BATINE", x, 810, f1, skia.Paint(AntiAlias=True, Color=skia.Color(*RED)), 10)
        f2 = skia.Font(ANTON, 92)
        t2 = "U SLOVAČKOJ?"
        tracked(cv, t2, 960 - tracked_width(t2, f2, 26) / 2 + 4, 928, f2, sh, 26)
        tracked(cv, t2, 960 - tracked_width(t2, f2, 26) / 2, 920, f2,
                skia.Paint(AntiAlias=True, Color=skia.Color(235, 235, 240)), 26)
        f3 = skia.Font(ARCHIVO, 24)
        t3 = "TATAMY   •   SLOVAČKA   •   BJJ VLOG"
        tracked(cv, t3, 960 - tracked_width(t3, f3, 8) / 2, H - 58, f3, pg, 8)
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas, vignette=0.2, grain=0.025)


CONCEPTS4 = {
    "16_svetla_pozadina": c16_light_mode,
    "17_flasteri": c17_bandaid,
    "18_fokus_i_krug": c18_focus,
    "19_strip": c19_comic,
    "20_film": c20_cinema,
}


# ====================================================================== film series (based on concept 20)
def laurel(cv, cx, cy, size, lines):
    """film-festival style laurel wreath (two leafy branches) with text inside."""
    gold = skia.Color(226, 204, 150)
    leaf = skia.Paint(AntiAlias=True, Color=gold)
    stem = skia.Paint(AntiAlias=True, Color=gold)
    stem.setStyle(skia.Paint.kStroke_Style); stem.setStrokeWidth(size * 0.012)
    R = size * 0.5
    for side in (-1, 1):
        # angles in screen coords (y down): 90 = bottom; left branch 105 -> 245, right branch 75 -> -65
        a0, a1 = (105, 245) if side < 0 else (75, -65)
        rect = skia.Rect.MakeLTRB(cx - R, cy - R, cx + R, cy + R)
        cv.drawArc(rect, a0, a1 - a0, False, stem)
        n = 8
        for k in range(n):
            t = k / (n - 1)
            th = a0 + (a1 - a0) * t
            sz = size * (0.11 - 0.045 * t)
            for off, tilt in ((+1, 32), (-1, -32)):
                rr = R + off * sz * 0.55
                x = cx + rr * np.cos(np.radians(th))
                y = cy + rr * np.sin(np.radians(th))
                cv.save()
                cv.translate(float(x), float(y))
                base_rot = th + (180 if side > 0 else 0)
                cv.rotate(float(base_rot + side * tilt * off * -1))
                cv.drawOval(skia.Rect.MakeXYWH(-sz * 0.28, -sz * 0.75, sz * 0.56, sz * 1.5), leaf)
                cv.restore()
        tip_th = np.radians(a1)
        cv.drawCircle(float(cx + R * np.cos(tip_th)), float(cy + R * np.sin(tip_th)), size * 0.02, leaf)
    f1 = skia.Font(ARCHIVO, size * 0.115)
    y = cy - (len(lines) - 1) * size * 0.075 + size * 0.04
    for t in lines:
        w = tracked_width(t, f1, 3)
        tracked(cv, t, cx - w / 2, y, f1, skia.Paint(AntiAlias=True, Color=skia.Color(240, 228, 196)), 3)
        y += size * 0.15


def film(bars=True, top_text=None, bottom_text="TATAMY   •   SLOVAČKA   •   BJJ VLOG", grade="teal",
         layout="center", ppl=(1.55, 960, 300), laurels=False, bar=132):
    canvas = bg_plate(gain=0.45, sat=0.8, blur=10)
    s_, cx_, hy_ = ppl
    p, a = people(s_, cx_, hy_, "bw" if grade == "bw" else "color")
    canvas = composite_people(canvas, p, a, outline=0, shadow=0.85)
    if grade == "bw":
        l = canvas.mean(2, keepdims=True)
        canvas = np.repeat(np.clip(0.5 + (l - 0.5) * 1.15, 0, 1), 3, 2)
    else:
        lum = canvas.mean(2, keepdims=True)
        if grade == "teal":
            canvas = canvas + (1 - lum) * np.array([-0.036, 0.024, 0.06]) + lum * np.array([0.05, 0.01, -0.04])
        else:  # warm / golden
            canvas = canvas + (1 - lum) * np.array([0.02, 0.0, -0.03]) + lum * np.array([0.08, 0.035, -0.06])
        canvas = np.clip(0.5 + (canvas - 0.5) * 1.12, 0, 1)
    if layout == "left":
        canvas = canvas * (1 - 0.6 * (1 - ss(XX, 300, 900)))[..., None]
        canvas = canvas * (1 - 0.35 * ss(YY, 750, 1000))[..., None]
    elif layout == "center":
        canvas = canvas * (1 - 0.7 * ss(YY, 620, 930))[..., None]
    else:
        canvas = canvas * (1 - 0.6 * ss(YY, 560, 780))[..., None]
    if bars:
        canvas[:bar] = 0
        canvas[H - (bar if layout != "bar" else 300):] = 0

    def draw(cv):
        pg = skia.Paint(AntiAlias=True, Color=skia.Color(200, 200, 205))
        white = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255))
        red = skia.Paint(AntiAlias=True, Color=skia.Color(*RED))
        sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 200))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12))
        light = skia.Paint(AntiAlias=True, Color=skia.Color(235, 235, 240))
        if top_text:
            f = skia.Font(ARCHIVO, 30)
            tracked(cv, top_text, 960 - tracked_width(top_text, f, 12) / 2, 80, f, pg, 12)
        if layout == "center":
            f1 = skia.Font(ANTON, 170)
            x = 960 - tracked_width("DOBILI BATINE", f1, 10) / 2
            tracked(cv, "DOBILI BATINE", x + 6, 818, f1, sh, 10)
            x = tracked(cv, "DOBILI ", x, 810, f1, white, 10)
            tracked(cv, "BATINE", x, 810, f1, red, 10)
            f2 = skia.Font(ANTON, 92)
            t2 = "U SLOVAČKOJ?"
            tracked(cv, t2, 960 - tracked_width(t2, f2, 26) / 2 + 4, 928, f2, sh, 26)
            tracked(cv, t2, 960 - tracked_width(t2, f2, 26) / 2, 920, f2, light, 26)
            by = H - 58
        elif layout == "left":
            x0 = 110
            for t, f, y, pnt, tr in [("DOBILI", skia.Font(ANTON, 175), 430, white, 10),
                                     ("BATINE", skia.Font(ANTON, 175), 625, red, 10),
                                     ("U SLOVAČKOJ?", skia.Font(ANTON, 72), 750, light, 12)]:
                tracked(cv, t, x0 + 6, y + 8, f, sh, tr)
                tracked(cv, t, x0, y, f, pnt, tr)
            cv.drawRect(skia.Rect.MakeXYWH(x0, 790, 120, 6), red)
            by = H - 58
        else:  # title inside a tall bottom bar
            f1 = skia.Font(ANTON, 128)
            parts = [("DOBILI ", white), ("BATINE ", red), ("U SLOVAČKOJ?", white)]
            total = sum(tracked_width(t, f1, 6) + 6 for t, _ in parts)
            x = 960 - total / 2
            for t, pnt in parts:
                x = tracked(cv, t, x, 945, f1, pnt, 6) + 6
            by = H - 38
        if bottom_text:
            f3 = skia.Font(ARCHIVO, 24)
            tracked(cv, bottom_text, 960 - tracked_width(bottom_text, f3, 8) / 2, by, f3, pg, 8)
        if laurels:
            laurel(cv, 1680, 330, 330, ["TATAMY", "SLOVAČKA"])
    canvas = put(canvas, skia_layer(draw))
    return finish(canvas, vignette=0.2, grain=0.025)


FILM = {
    "0_bez_teksta_gore": dict(),
    "1_bez_traka": dict(bars=False),
    "2_crno_belo": dict(grade="bw"),
    "3_naslov_levo": dict(layout="left", ppl=(1.62, 1290, 300)),
    "4_veci_ljudi_naslov_u_traci": dict(layout="bar", ppl=(1.95, 960, 190), bar=70),
    "5_zlatni_lovor": dict(grade="warm", laurels=True, ppl=(1.55, 860, 300)),
}

if __name__ == "__main__":
    os.makedirs(os.path.join(base.OUT, "concepts"), exist_ok=True)
    import sys
    if "film" in sys.argv:
        os.makedirs(os.path.join(base.OUT, "film"), exist_ok=True)
        for name, kw in FILM.items():
            img = Image.fromarray(film(**kw))
            path = os.path.join(base.OUT, "film", f"film_{name}.jpg")
            img.save(path, quality=93, subsampling=0, optimize=True)
            print(name, os.path.getsize(path) // 1024, "KB")
        sys.exit(0)
    todo = CONCEPTS4 if "round4" in sys.argv else CONCEPTS3 if "round3" in sys.argv else CONCEPTS2 if "round2" in sys.argv else CONCEPTS
    for name, fn in todo.items():
        img = Image.fromarray(fn())
        path = os.path.join(base.OUT, "concepts", f"koncept_{name}.jpg")
        img.save(path, quality=93, subsampling=0, optimize=True)
        print(name, os.path.getsize(path) // 1024, "KB")
