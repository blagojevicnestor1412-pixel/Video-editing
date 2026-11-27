"""10th Planet Belgrade - Instagram Reel outro (1080x1920, 30 fps, 7 s).

Same motion language as the YouTube end screen (render.py): space backdrop with the logo's warped grid,
logo reveal with flash/shockwave/light streak, letter-rise title, glass card, specular sweeps.
Content: logo -> "CEO VLOG NA YOUTUBE-U" -> vlog thumbnail as an animated video card ->
"LINK U BIO" and "@10pbelgrade" buttons that get tapped.
Key content stays inside the Reels safe area (top ~250 px and bottom ~420 px are covered by the app UI).

Usage: python3 reel_outro.py stills [t ...] | python3 reel_outro.py video
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as R  # noqa: E402
from render import (CYAN, PURPLE, SAMPLING, TF_BOLD, TF_MONT, WHITE, YT_RED, c4, ci, clamp,  # noqa: E402
                    draw_image_centered, draw_light_streak, draw_sweep, draw_text_center, ease_in_out_cubic,
                    ease_out_back, ease_out_cubic, ease_out_expo, fill_paint, lerp, np_to_image, press_curve, prog,
                    stroke_paint)

W, H = 1080, 1920
FPS = 30
DUR = 7.0
NFRAMES = int(DUR * FPS)
OUT = os.path.join(HERE, "build_reel")
os.makedirs(OUT, exist_ok=True)
THUMB = os.path.join(HERE, "..", "thumbnail", "output", "film", "film_8_svinjac_goofy.jpg")

INK = (14, 10, 24)
HEART_D = ("M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 "
           "3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z")

# layout
LX, LY, LS = 540, 395, 0.45            # logo centre + scale (logo layers are built 1120 px wide)
TITLE_Y = 705
CARD = (120, 818, 840, 472)            # x, y, w, h (16:9)
PILL_Y, PILL_H = 1400, 96
# LINK_BUTTON=1 brings back the "LINK U BIO" button next to the Instagram one
LINK_BUTTON = os.environ.get("LINK_BUTTON", "0") == "1"
PILL_L = (120, 520)
PILL_R = (560, 960) if LINK_BUTTON else (290, 790)
TAP_L, TAP_R = 3.5, 4.3


class Assets:
    def __init__(self):
        R.LOGO_W = 1120
        self.logo = R.build_logo_layers()
        im = Image.open(THUMB).convert("RGB").resize((1280, 720), Image.LANCZOS)
        self.thumb = np_to_image(np.dstack([np.array(im), np.full((720, 1280), 255, np.uint8)]))
        self.play = R.svg_icon(R.PLAY_D, 96, WHITE)
        self.heart_p = R.svg_icon(HEART_D, 128, (255, 70, 120))
        self.heart_w = R.svg_icon(HEART_D, 128, (255, 255, 255))
        self.grain = [R.make_grain(s) for s in range(6)]
        rng = np.random.default_rng(21)
        n = 260
        self.stars = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n), rng.power(3.0, n) * 3.0 + 0.6,
                               rng.uniform(0.15, 1.0, n), rng.uniform(0, 2 * math.pi, n), rng.uniform(0.3, 1.2, n),
                               rng.uniform(0.2, 1.0, n), rng.integers(0, 3, n).astype(float)], 1)
        m = 40
        self.dust = np.stack([rng.uniform(0, W, m), rng.uniform(0, H, m), rng.uniform(2, 6, m),
                              rng.uniform(0, 2 * math.pi, m), rng.uniform(10, 35, m)], 1)
        self.hearts = rng.uniform(0, 1, (8, 4))


_A = None


def assets():
    global _A
    if _A is None:
        _A = Assets()
    return _A


# ------------------------------------------------------------------ background
def draw_background(cv, t, a):
    intro = ease_out_cubic(prog(t, 0.0, 0.8))
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial((W * 0.5, H * 0.30), H * 1.0,
                                               [ci((22, 16, 52)), ci((10, 8, 28)), ci((3, 3, 10))], [0, 0.45, 1]))
    cv.drawPaint(p)

    def blob(x, y, r, rgb, al):
        bp = skia.Paint()
        bp.setShader(skia.GradientShader.MakeRadial((x, y), r, [ci(rgb, al), ci(rgb, al * 0.35), ci(rgb, 0)],
                                                    [0, 0.45, 1]))
        cv.drawCircle(x, y, r, bp)

    blob(180 + 60 * math.sin(t * 0.4), 380 + 40 * math.cos(t * 0.3), 900, PURPLE, 0.22 * intro)
    blob(920 + 50 * math.cos(t * 0.35), 1500 + 50 * math.sin(t * 0.4), 900, CYAN, 0.11 * intro)
    blob(LX, LY, 560, PURPLE, 0.18 * intro)

    # warped grid flowing towards a throat at the bottom (echo of the logo's grid)
    cx, cy = W / 2, 300
    rings, flow = 20, (t * 0.14) % 1.0

    def ring_geo(u):
        depth = u ** 1.6
        rx = 1500 * (1 - depth) + 70
        return rx, rx * 0.30, cy + 1350 * depth ** 0.85 - 200 * (1 - u)

    for k in range(rings + 1):
        u = (k + flow) / rings
        if u > 1:
            continue
        rx, ry, yy = ring_geo(u)
        al = (0.10 + 0.20 * u) * (1 - u ** 4) * intro * clamp(u * 6)
        cv.drawOval(skia.Rect.MakeXYWH(cx - rx, yy - ry, 2 * rx, 2 * ry),
                    stroke_paint(PURPLE if k % 2 else (120, 100, 230), al, 1.6 + 1.0 * (1 - u)))
    mp = stroke_paint((130, 110, 235), 0.10 * intro, 1.4)
    for i in range(30):
        ang = t * 0.05 + i * 2 * math.pi / 30
        path = skia.Path()
        for s_ in range(21):
            rx, ry, yy = ring_geo(s_ / 20)
            x, y = cx + rx * math.cos(ang), yy + ry * math.sin(ang)
            (path.moveTo if s_ == 0 else path.lineTo)(x, y)
        cv.drawPath(path, mp)
    blob(W / 2, cy + 1350, 520, CYAN, 0.10 * intro)

    sp = skia.Paint(AntiAlias=True)
    cols = [WHITE, CYAN, (205, 190, 255)]
    for x, y, r, b, ph, spd, d, cid in a.stars:
        al = b * (0.55 + 0.45 * math.sin(ph + t * spd * 2.2)) * intro
        if al < 0.03:
            continue
        xx, yy = (x - t * 7 * d) % W, (y + t * 3 * d) % H
        sp.setColor4f(c4(cols[int(cid)], al * 0.85))
        cv.drawCircle(xx, yy, r * (0.6 + 0.4 * d), sp)


def draw_dust(cv, t, a):
    k = ease_out_cubic(prog(t, 0.3, 1.5))
    for x, y, r, ph, spd in a.dust:
        xx = (x + math.sin(t * 0.3 + ph) * spd * 3 + t * 10) % W
        yy = (y - t * spd * 1.5) % H
        cv.drawCircle(xx, yy, r, fill_paint(CYAN if ph > 3 else PURPLE, 0.18 * k * (0.5 + 0.5 * math.sin(t + ph)),
                                            blur=r * 0.8))


# ------------------------------------------------------------------ logo
def draw_logo(cv, t, a):
    L = a.logo
    p_in = prog(t, 0.10, 0.75)
    if p_in <= 0:
        return
    e = ease_out_expo(p_in)
    alpha = clamp(p_in * 2.2)
    blur = lerp(22, 0, ease_out_cubic(clamp(p_in * 1.4)))
    settle = ease_in_out_cubic(prog(t, 1.0, 2.4))
    fy = math.sin((t - 1.0) * 1.1) * 5 * settle
    shake = math.sin((t - 0.7) / 0.35 * 40) * 5 * (1 - (t - 0.7) / 0.35) ** 2 if 0.7 < t < 1.05 else 0.0
    s = lerp(1.25, 1.0, e) * LS * (1 + math.sin((t - 1.0) * 0.8) * 0.005 * settle)
    cx, cy = LX + shake, LY + fy
    draw_image_centered(cv, L["shadow"], cx, cy + 16, s, alpha * 0.9)
    flash = math.exp(-(t - 0.7) * 5) if t > 0.7 else 0
    draw_image_centered(cv, L["glow"], cx, cy, s * 1.03, alpha * (0.55 + 0.15 * math.sin(t * 1.6) + flash * 0.8))
    for key in ("ink", "edge", "logo"):
        draw_image_centered(cv, L[key], cx, cy, s, alpha, blur=blur)
    for t0, st in ((0.80, 0.8), (5.2, 0.55)):
        sk = prog(t, t0, t0 + 1.0)
        if 0 < sk < 1:
            draw_sweep(cv, L, cx, cy, s, ease_in_out_cubic(sk), st)
    if 0.68 < t < 1.9:
        k = prog(t, 0.70, 1.6)
        r = lerp(140, 1250, ease_out_cubic(k))
        al = (1 - k) ** 2 * 0.6
        for w_, a_, col in ((24, 0.25, PURPLE), (5, 1.0, CYAN)):
            cv.drawOval(skia.Rect.MakeXYWH(LX - r, LY + 20 - r * 0.32, 2 * r, 0.64 * r),
                        stroke_paint(col, al * a_, w_, blur=w_ * 0.6))
        draw_light_streak(cv, LX, LY + 20, 1 - ease_out_cubic(prog(t, 0.7, 1.5)), 1500)


# ------------------------------------------------------------------ title
def draw_title(cv, t):
    text = "CEO VLOG"
    font = skia.Font(TF_MONT, 112)
    tracking = 6
    widths = [font.measureText(ch) for ch in text]
    x = W / 2 - (sum(widths) + tracking * (len(text) - 1)) / 2
    grad = skia.GradientShader.MakeLinear([(0, TITLE_Y - 90), (0, TITLE_Y)], [ci(WHITE), ci((214, 200, 255))])
    for i, (ch, w) in enumerate(zip(text, widths)):
        k = prog(t, 0.92 + i * 0.035, 0.92 + i * 0.035 + 0.5)
        if k > 0:
            e = ease_out_expo(k)
            p = skia.Paint(AntiAlias=True)
            p.setShader(grad)
            p.setAlphaf(clamp(k * 2.5))
            cv.save()
            cv.clipRect(skia.Rect.MakeLTRB(x - 10, TITLE_Y - 130, x + w + 10, TITLE_Y + 25))
            cv.drawString(ch, x, TITLE_Y + (1 - e) * 110, font, p)
            cv.restore()
        x += w + tracking
    k = prog(t, 1.25, 1.85)
    if k > 0:
        e = ease_out_cubic(k)
        f2 = skia.Font(TF_BOLD, 60)
        y2 = TITLE_Y + 74
        tw = draw_text_center(cv, "NA YOUTUBE-U", W / 2, y2 + (1 - e) * 18, f2, fill_paint(CYAN, e), tracking=14)
        lp = ease_out_expo(prog(t, 1.4, 2.2))
        if lp > 0:
            gap, ln = tw / 2 + 34, 120 * lp
            for sgn in (-1, 1):
                x0 = W / 2 + sgn * gap
                p = skia.Paint(AntiAlias=True)
                p.setShader(skia.GradientShader.MakeLinear([(x0, 0), (x0 + sgn * ln, 0)], [ci(CYAN, 0.9), ci(PURPLE, 0)]))
                p.setStrokeWidth(3)
                cv.drawLine(x0, y2 - 20, x0 + sgn * ln, y2 - 20, p)
                cv.save()
                cv.translate(x0 - sgn * 16, y2 - 20)
                cv.rotate(45)
                cv.drawRect(skia.Rect.MakeXYWH(-5, -5, 10, 10), fill_paint(CYAN, lp))
                cv.restore()


# ------------------------------------------------------------------ video card
def draw_card(cv, t, a):
    t0 = 1.45
    k = prog(t, t0, t0 + 0.9)
    if k <= 0:
        return
    e = ease_out_expo(k)
    al = clamp(k * 2)
    x, y0, w, h = CARD
    y = y0 + (1 - e) * 150
    r = 24
    rect = skia.Rect.MakeXYWH(x, y, w, h)
    rr = skia.RRect.MakeRectXY(rect, r, r)
    cv.save(); cv.translate(0, 24); cv.drawRRect(rr, fill_paint((0, 0, 0), 0.55 * al, blur=30)); cv.restore()
    cv.drawRRect(rr, stroke_paint(PURPLE, (0.40 + 0.10 * math.sin(t * 2.0)) * al, 12, blur=26))

    cv.save()
    cv.clipRRect(rr, True)
    img = a.thumb
    sc = w / img.width() * (1.0 + 0.05 * clamp((t - t0) / (DUR - t0)))
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(al)
    cv.save(); cv.translate(x + w / 2, y + h / 2); cv.scale(sc, sc)
    cv.drawImage(img, -img.width() / 2, -img.height() / 2, SAMPLING, p)
    cv.restore()
    gp = skia.Paint()
    gp.setShader(skia.GradientShader.MakeLinear([(0, y + h - 110), (0, y + h)], [ci((0, 0, 0), 0), ci((0, 0, 0), 0.6 * al)]))
    cv.drawRect(rect, gp)
    # player controls: play icon + progress bar
    ck = ease_out_cubic(prog(t, t0 + 0.55, t0 + 1.0))
    if ck > 0:
        by = y + h - 30
        draw_image_centered(cv, a.play, x + 44, by, 0.46, ck)
        bx0, bx1 = x + 80, x + w - 28
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(bx0, by - 3, bx1, by + 3), 3, 3), fill_paint(WHITE, 0.35 * ck))
        pk = clamp((t - (t0 + 0.6)) / (DUR - (t0 + 0.6)))
        bx = bx0 + (bx1 - bx0) * (0.03 + 0.40 * pk)
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(bx0, by - 3, bx, by + 3), 3, 3), fill_paint(YT_RED, ck))
        cv.drawCircle(bx, by, 9 * ck, fill_paint(YT_RED, ck))
    for s0 in (t0 + 0.55, 5.6):
        sk = prog(t, s0, s0 + 1.1)
        if 0 < sk < 1:
            pos = lerp(x - 300, x + w + 300, ease_in_out_cubic(sk))
            sp = skia.Paint(AntiAlias=True)
            sp.setShader(skia.GradientShader.MakeLinear([(pos - 160, y), (pos + 160, y + h * 0.5)],
                                                        [ci(WHITE, 0), ci(WHITE, 0.16), ci(WHITE, 0)], [0, 0.5, 1]))
            cv.drawRect(rect, sp)
    cv.restore()

    path = skia.Path()
    path.addRRect(rr)
    length = skia.PathMeasure(path, False).getLength()
    d = ease_in_out_cubic(prog(t, t0, t0 + 1.1))
    bp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3)
    bp.setShader(skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [ci(CYAN, 0.95), ci(PURPLE, 0.95), ci(CYAN, 0.6)]))
    bp.setPathEffect(skia.DashPathEffect.Make([length * d, length * 2], 0))
    cv.drawPath(path, bp)
    cb = ease_out_back(prog(t, t0 + 0.35, t0 + 0.95))
    if cb > 0:
        L_, off = 56 * cb, 18
        bp2 = stroke_paint(WHITE, 0.95 * al, 6, cap=skia.Paint.kSquare_Cap)
        for px, py, sx, sy in ((x - off, y - off, 1, 1), (x + w + off, y - off, -1, 1),
                               (x - off, y + h + off, 1, -1), (x + w + off, y + h + off, -1, -1)):
            pa = skia.Path(); pa.moveTo(px, py + sy * L_); pa.lineTo(px, py); pa.lineTo(px + sx * L_, py)
            cv.drawPath(pa, bp2)
    # "NOVI VLOG" tag
    tk = prog(t, 2.15, 2.55)
    if tk > 0:
        s = ease_out_back(tk, 2.2)
        f = skia.Font(TF_BOLD, 40)
        label = "NOVI VLOG"
        tw = sum(f.measureText(ch) + 4 for ch in label)
        cv.save(); cv.translate(x + 24, y + 24); cv.scale(s, s)
        r2 = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(0, 0, tw + 70, 58), 12, 12)
        cv.save(); cv.translate(4, 6); cv.drawRRect(r2, fill_paint((0, 0, 0), 0.5, blur=8)); cv.restore()
        cv.drawRRect(r2, fill_paint(YT_RED, 1.0))
        cv.drawCircle(26, 29, 8, fill_paint(WHITE, 0.6 + 0.4 * math.sin(t * 6)))
        xx = 46
        for ch in label:
            cv.drawString(ch, xx, 43, f, fill_paint(WHITE))
            xx += f.measureText(ch) + 4
        cv.restore()


# ------------------------------------------------------------------ CTA buttons
def yt_logo(cv, cx, cy, s=1.0):
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 33 * s, cy - 23 * s, 66 * s, 46 * s), 13 * s, 13 * s),
                 fill_paint(YT_RED))
    tri = skia.Path()
    tri.moveTo(cx - 9 * s, cy - 12 * s); tri.lineTo(cx + 14 * s, cy); tri.lineTo(cx - 9 * s, cy + 12 * s); tri.close()
    cv.drawPath(tri, fill_paint(WHITE))


def pill(cv, t, t_in, t_tap, span, kind):
    k = prog(t, t_in, t_in + 0.5)
    if k <= 0:
        return
    s = ease_out_back(k, 2.0) * press_curve(t, t_tap)
    x0, x1 = span
    cx = (x0 + x1) / 2
    w, h = (x1 - x0) * s, PILL_H * s
    rect = skia.Rect.MakeXYWH(cx - w / 2, PILL_Y - h / 2, w, h)
    rr = skia.RRect.MakeRectXY(rect, h / 2, h / 2)
    glow_col = WHITE if kind == "yt" else (214, 41, 118)
    cv.drawRRect(rr, fill_paint(glow_col, 0.22 + 0.10 * math.sin(t * 3.0 + (0 if kind == "yt" else 1.5)), blur=28))
    cv.save(); cv.translate(0, 10); cv.drawRRect(rr, fill_paint((0, 0, 0), 0.45, blur=14)); cv.restore()
    p = skia.Paint(AntiAlias=True)
    if kind == "yt":
        p.setShader(skia.GradientShader.MakeLinear([(0, PILL_Y - h / 2), (0, PILL_Y + h / 2)],
                                                   [ci((255, 255, 255)), ci((226, 228, 236))]))
    else:
        p.setShader(skia.GradientShader.MakeLinear(
            [(cx - w / 2, PILL_Y + h / 2), (cx + w / 2, PILL_Y - h / 2)],
            [ci((254, 218, 117)), ci((250, 126, 30)), ci((214, 41, 118)), ci((150, 47, 191)), ci((79, 91, 213))],
            [0, 0.25, 0.5, 0.75, 1]))
    cv.drawRRect(rr, p)
    cv.save()
    cv.clipRRect(rr, True)
    hp = skia.Paint(AntiAlias=True)
    hp.setShader(skia.GradientShader.MakeLinear([(0, PILL_Y - h / 2), (0, PILL_Y)], [ci(WHITE, 0.30), ci(WHITE, 0)]))
    cv.drawRect(skia.Rect.MakeXYWH(cx - w / 2, PILL_Y - h / 2, w, h / 2), hp)
    rk = prog(t, t_tap + 0.04, t_tap + 0.7)
    if 0 < rk < 1:
        cv.drawCircle(cx, PILL_Y, 20 + 330 * ease_out_cubic(rk),
                      fill_paint((0, 0, 0) if kind == "yt" else WHITE, 0.22 * (1 - rk)))
    for s0 in ((3.05, 6.1) if kind == "yt" else (3.2, 6.3)):
        sk = prog(t, s0, s0 + 0.8)
        if 0 < sk < 1:
            pos = lerp(cx - w, cx + w, ease_in_out_cubic(sk))
            sp = skia.Paint(AntiAlias=True)
            sp.setShader(skia.GradientShader.MakeLinear([(pos - 70, PILL_Y - h), (pos + 70, PILL_Y + h)],
                                                        [ci(WHITE, 0), ci(WHITE, 0.55), ci(WHITE, 0)], [0, 0.5, 1]))
            cv.drawRect(rect, sp)
    cv.restore()
    # content (icon + label), laid out at unit scale then scaled with the pill
    cv.save()
    cv.translate(cx, PILL_Y)
    cv.scale(s, s)
    if kind == "yt":
        f = skia.Font(TF_MONT, 38)
        label, icon_w = "LINK U BIO", 66
        tw = f.measureText(label)
        x = -(icon_w + 18 + tw) / 2
        yt_logo(cv, x + icon_w / 2, 0)
        cv.drawString(label, x + icon_w + 18, 14, f, fill_paint(INK))
    else:
        f = skia.Font(TF_BOLD, 44 if LINK_BUTTON else 54)
        label, icon_w = "@10pbelgrade", (52 if LINK_BUTTON else 62)
        tw = f.measureText(label)
        x = -(icon_w + 16 + tw) / 2
        R.draw_instagram_glyph(cv, x + icon_w / 2, 0, 0.85 if LINK_BUTTON else 1.0, 1.0)
        cv.drawString(label, x + icon_w + 16, 15 if LINK_BUTTON else 18, f, fill_paint(WHITE))
    cv.restore()


def draw_hearts(cv, t, a):
    x0, x1 = PILL_R
    cx = (x0 + x1) / 2
    for i, (r1, r2, r3, r4) in enumerate(a.hearts):
        t0 = TAP_R + 0.05 + i * 0.06
        k = prog(t, t0, t0 + 1.3)
        if not (0 < k < 1):
            continue
        x = cx + (r1 - 0.5) * 260 + math.sin(k * 6 + r2 * 6) * 26
        y = PILL_Y - 40 - (200 + 160 * r3) * ease_out_cubic(k)
        sc = (0.30 + 0.18 * r4) * min(1, ease_out_back(clamp(k * 4), 2.5))
        al = 1 - ease_out_cubic(prog(k, 0.6, 1.0))
        draw_image_centered(cv, a.heart_w if i % 3 == 2 else a.heart_p, x, y, sc, al, rot=(r2 - 0.5) * 40)


def draw_touch(cv, t):
    """a finger-tap dot that taps both buttons."""
    if not (3.2 < t < 4.9):
        return
    lx, rx = (PILL_L[0] + PILL_L[1]) / 2 + 40, (PILL_R[0] + PILL_R[1]) / 2 + 60
    if not LINK_BUTTON:   # single button: the dot comes in from below and taps it once
        if t < 3.9:
            return
        k = ease_out_cubic(prog(t, 3.9, 4.22))
        x, y = lerp(rx + 70, rx, k), lerp(PILL_Y + 150, PILL_Y + 6, k)
        al = ease_out_cubic(prog(t, 3.9, 4.05)) * (1 - ease_out_cubic(prog(t, 4.55, 4.85)))
    elif t < 3.45:
        k = ease_out_cubic(prog(t, 3.2, 3.45)); x, y = lerp(lx + 60, lx, k), lerp(PILL_Y + 110, PILL_Y + 6, k)
    elif t < 3.85:
        x, y = lx, PILL_Y + 6
    else:
        k = ease_in_out_cubic(prog(t, 3.85, 4.25)); x, y = lerp(lx, rx, k), PILL_Y + 6 - math.sin(k * math.pi) * 60
    if LINK_BUTTON:
        al = ease_out_cubic(prog(t, 3.2, 3.35)) * (1 - ease_out_cubic(prog(t, 4.55, 4.85)))
    press = 1.0
    for tp in ((TAP_L, TAP_R) if LINK_BUTTON else (TAP_R,)):
        d = t - tp
        if -0.06 < d < 0.25:
            press = min(press, 0.70 + 0.30 * min(1, abs(d) / 0.12))
    cv.drawCircle(x + 4, y + 8, 28 * press, fill_paint((0, 0, 0), 0.35 * al, blur=8))
    cv.drawCircle(x, y, 40 * press, stroke_paint(WHITE, 0.45 * al, 4))
    cv.drawCircle(x, y, 26 * press, fill_paint(WHITE, 0.85 * al))


# ------------------------------------------------------------------ frame
def draw_post(cv, t, i, a):
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial((W / 2, H * 0.45), H * 0.75,
                                               [ci((6, 5, 16), 0), ci((6, 5, 16), 0), ci((6, 5, 16), 0.55)], [0, 0.6, 1]))
    cv.drawPaint(p)
    g = a.grain[i % len(a.grain)]
    rng = np.random.default_rng(i)
    ox, oy = rng.integers(0, 512, 2)
    m = skia.Matrix()
    m.setTranslate(float(ox), float(oy))
    gp = skia.Paint()
    gp.setShader(g.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, SAMPLING, m))
    gp.setBlendMode(skia.BlendMode.kOverlay)
    gp.setAlphaf(0.07)
    cv.drawPaint(gp)
    fin = 1 - ease_out_cubic(prog(t, 0.0, 0.25))
    if fin > 0:
        cv.drawPaint(fill_paint((0, 0, 0), fin, aa=False))


def render_frame(i):
    return render_at(i / FPS, i)


def render_at(t, grain_idx):
    i = grain_idx
    a = assets()
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorBLACK)
    draw_background(cv, t, a)
    draw_dust(cv, t, a)
    draw_card(cv, t, a)
    if LINK_BUTTON:
        pill(cv, t, 2.65, TAP_L, PILL_L, "yt")
    pill(cv, t, 2.80, TAP_R, PILL_R, "ig")
    draw_hearts(cv, t, a)
    draw_title(cv, t)
    draw_logo(cv, t, a)
    draw_touch(cv, t)
    draw_post(cv, t, i, a)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def render_segment(args):
    seg, f0, f1 = args
    path = os.path.join(OUT, f"seg_{seg:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-tune", "film", "-profile:v", "high",
           "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-x264-params", "threads=2",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-an", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        proc.stdin.write(render_frame(i).tobytes())
    proc.stdin.close()
    proc.wait()
    return path


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if mode == "stills":
        for tt in [float(x) for x in sys.argv[2:]] or [0.5, 0.9, 1.6, 2.4, 3.0, 3.55, 4.5, 6.5]:
            Image.fromarray(render_frame(int(round(tt * FPS)))).convert("RGB").save(
                os.path.join(OUT, f"still_{tt:05.2f}.png"))
            print("still", tt, flush=True)
    else:
        nseg = 6
        b = np.linspace(0, NFRAMES, nseg + 1).astype(int)
        with Pool(3) as pool:
            paths = pool.map(render_segment, [(s, b[s], b[s + 1]) for s in range(nseg)], chunksize=1)
        lst = os.path.join(OUT, "segments.txt")
        with open(lst, "w") as fh:
            fh.writelines(f"file '{p}'\n" for p in paths)
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                               "-c", "copy", os.path.join(OUT, "video_only.mp4")])
        print("done")
