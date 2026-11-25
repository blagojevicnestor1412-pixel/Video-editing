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


# ====================================================================== version F
# - title same size everywhere, red box only behind BATINE
# - red "T" mark from the TATAMY logo + 10th Planet logo, both behind the group, blurred
# - Slovak flag sticker next to "U SLOVAČKOJ?"
from scipy import ndimage as _nd


def load_t_mark():
    rgba = np.array(Image.open(os.path.join(base.A, "tatamy_T_mark.png")).convert("RGBA")).astype(np.float32) / 255
    solid = _nd.binary_fill_holes(rgba[..., 3] > 0.5)
    a = np.maximum(rgba[..., 3], cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 1.0))
    inside = (rgba[..., 3] < 0.5)[..., None]
    rgb = np.where(inside, np.array([0.06, 0.06, 0.08]), rgba[..., :3])  # the "T" itself, dark like the banner
    return np.dstack([rgb, a]).astype(np.float32)


T_MARK = load_t_mark()


def slovak_flag(width=330, wave=True):
    """Slovak flag drawn from its geometry (white/blue/red + coat of arms), returns RGBA float."""
    fw, fh = width, int(width * 2 / 3)
    surf = skia.Surface(fw, fh)
    cv = surf.getCanvas()
    white, blue, red = skia.Color(255, 255, 255), skia.Color(11, 78, 162), skia.Color(238, 28, 37)
    for i, c in enumerate([white, blue, red]):
        cv.drawRect(skia.Rect.MakeXYWH(0, i * fh / 3, fw, fh / 3 + 1), skia.Paint(Color=c, AntiAlias=True))
    # coat of arms: shield towards the hoist
    sw, sh_ = fh * 0.43, fh * 0.56
    sx, sy = fw * 0.36 - sw / 2, fh / 2 - sh_ / 2
    shield = skia.Path()
    shield.moveTo(sx, sy)
    shield.lineTo(sx + sw, sy)
    shield.lineTo(sx + sw, sy + sh_ * 0.55)
    shield.cubicTo(sx + sw, sy + sh_ * 0.85, sx + sw * 0.62, sy + sh_ * 0.95, sx + sw / 2, sy + sh_)
    shield.cubicTo(sx + sw * 0.38, sy + sh_ * 0.95, sx, sy + sh_ * 0.85, sx, sy + sh_ * 0.55)
    shield.close()
    pw = skia.Paint(AntiAlias=True, Color=white)
    pw.setStyle(skia.Paint.kStroke_Style)
    pw.setStrokeWidth(fh * 0.022)
    cv.drawPath(shield, pw)
    cv.drawPath(shield, skia.Paint(AntiAlias=True, Color=red))
    cv.save()
    cv.clipPath(shield, doAntiAlias=True)
    # three blue hills
    hb = skia.Paint(AntiAlias=True, Color=blue)
    base_y = sy + sh_
    for cx_, r_ in [(sx + sw * 0.5, sw * 0.24), (sx + sw * 0.18, sw * 0.20), (sx + sw * 0.82, sw * 0.20)]:
        top = base_y - sh_ * (0.30 if r_ > sw * 0.22 else 0.22)
        cv.drawOval(skia.Rect.MakeLTRB(cx_ - r_, top, cx_ + r_, base_y + r_), hb)
    cv.restore()
    # white double cross
    cxs = sx + sw / 2
    cw = sw * 0.11
    cr = skia.Paint(AntiAlias=True, Color=white)
    cv.drawRect(skia.Rect.MakeLTRB(cxs - cw / 2, sy + sh_ * 0.10, cxs + cw / 2, sy + sh_ * 0.74), cr)
    cv.drawRect(skia.Rect.MakeLTRB(cxs - sw * 0.24, sy + sh_ * 0.22, cxs + sw * 0.24, sy + sh_ * 0.22 + cw), cr)
    cv.drawRect(skia.Rect.MakeLTRB(cxs - sw * 0.33, sy + sh_ * 0.40, cxs + sw * 0.33, sy + sh_ * 0.40 + cw), cr)
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32) / 255
    if wave:  # gentle cloth wave: displacement + shading
        yy, xx = np.mgrid[0:fh, 0:fw].astype(np.float32)
        ph = xx / fw * 2 * np.pi * 1.3
        dy = np.sin(ph) * fh * 0.035
        arr = cv2.remap(arr, xx, yy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        shade = 1 + 0.16 * np.cos(ph)
        arr[..., :3] = np.clip(arr[..., :3] * shade[..., None], 0, 1)
    return arr


def paste_rgba_rot(canvas, rgba, cx, cy, angle, border=0, shadow=0.6):
    h, w = rgba.shape[:2]
    pad = border + 40
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    big[pad:pad + h, pad:pad + w] = rgba
    if border:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * border + 1, 2 * border + 1))
        ring = cv2.dilate((big[..., 3] > 0.5).astype(np.uint8), k).astype(np.float32)
        ring = cv2.GaussianBlur(ring, (0, 0), 0.8)
        a = big[..., 3:4]
        big[..., :3] = big[..., :3] * a + (1 - a) * 1.0
        big[..., 3] = np.maximum(ring, big[..., 3])
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), angle, 1.0)
    M[0, 2] += cx - big.shape[1] / 2
    M[1, 2] += cy - big.shape[0] / 2
    lay = cv2.warpAffine(big, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    sh = cv2.GaussianBlur(np.roll(lay[..., 3], (12, 8), (0, 1)), (0, 0), 10) * shadow
    canvas = over(canvas, np.zeros(3), sh)
    return over(canvas, lay[..., :3], lay[..., 3])


def title_f(lines, size, cx, y0, gap, rot, box_rgb, skew=-0.18, stroke=18, tf=None):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    cv.translate(cx, y0)
    cv.rotate(rot)
    cv.skew(skew, 0)
    cv.translate(-cx, -y0)
    f = skia.Font(tf or TF_TITLE, size)
    layout, y = [], y0
    for runs in lines:
        wtot = sum(f.measureText(t) for t, _ in runs)
        layout.append((runs, cx - wtot / 2, y))
        y += gap
    cap = size * 0.80
    # red box behind the highlighted word
    for runs, x, y in layout:
        for t, hl in runs:
            w = f.measureText(t)
            if hl:
                l, r = x - size * 0.10, x + w + size * 0.08
                top, bot = y - cap - size * 0.16, y + size * 0.10
                sp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 200))
                sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
                cv.drawRect(skia.Rect.MakeLTRB(l + 14, top + 20, r + 14, bot + 22), sp)
                cv.drawRect(skia.Rect.MakeLTRB(l, top, r, bot), skia.Paint(AntiAlias=True, Color=skia.Color(*box_rgb)))
            x += w
    for pass_ in ("shadow", "outline", "fill"):
        for runs, x, y in layout:
            for t, hl in runs:
                w = f.measureText(t)
                if pass_ == "shadow" and not hl:
                    p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 215))
                    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
                    cv.drawString(t, x + 12, y + 18, f, p)
                    p2 = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 120))
                    p2.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 28))
                    cv.drawString(t, x + 18, y + 30, f, p2)
                elif pass_ == "outline" and not hl:
                    p = skia.Paint(AntiAlias=True, Color=skia.Color(12, 10, 20))
                    p.setStyle(skia.Paint.kStroke_Style)
                    p.setStrokeWidth(stroke)
                    p.setStrokeJoin(skia.Paint.kRound_Join)
                    cv.drawString(t, x, y, f, p)
                elif pass_ == "outline" and hl:
                    p = skia.Paint(AntiAlias=True, Color=skia.Color(90, 0, 0, 200))
                    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
                    cv.drawString(t, x + 6, y + 8, f, p)
                elif pass_ == "fill":
                    p = skia.Paint(AntiAlias=True)
                    # metallic sheen: diagonal multi-stop gradient with bright glints
                    p.setShader(skia.GradientShader.MakeLinear(
                        [(x, y - cap * 1.1), (x + cap * 1.6, y + cap * 0.4)],
                        [skia.Color(255, 255, 255), skia.Color(226, 232, 242), skia.Color(255, 255, 255),
                         skia.Color(218, 224, 236), skia.Color(255, 255, 255), skia.Color(234, 238, 246)],
                        [0.0, 0.22, 0.40, 0.58, 0.78, 1.0], skia.TileMode.kMirror))
                    cv.drawString(t, x, y, f, p)
                    # thin top highlight
                    hp = skia.Paint(AntiAlias=True)
                    hp.setShader(skia.GradientShader.MakeLinear(
                        [(0, y - cap), (0, y - cap * 0.55)], [skia.Color(255, 255, 255, 150), skia.Color(255, 255, 255, 0)]))
                    hp.setBlendMode(skia.BlendMode.kSrcATop)
                    cv.drawString(t, x, y, f, hp)
                x += w
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                           alphaType=skia.kUnpremul_AlphaType).astype(np.float32) / 255
    return arr, layout, f


def build_f():
    canvas = background(0)
    # logos in the backdrop, behind the group, defocused
    canvas, _ = paste_logo(canvas, LOGO_10P, 60, 30, 860, shadow=0.45, blur=4.0, opacity=0.95)
    canvas, _ = paste_logo(canvas, T_MARK, 1180, 20, 520, shadow=0.45, blur=4.0, opacity=0.95)
    canvas = light_leaks(canvas, 1.0)

    s, cxp, hy = 2.05, 960, 175
    ox, oy = cxp - PEOPLE_ANCHOR[0] * s, hy - PEOPLE_ANCHOR[1] * s
    ppl = place(photo, s, ox, oy)
    pa = np.clip(place_alpha(matte, s, ox, oy), 0, 1)
    pa = np.clip((pa - 0.04) / 0.96, 0, 1)
    p = np.clip(ppl, 0, 1)
    lum = p.mean(2, keepdims=True)
    p = lum + (p - lum) * 1.18
    p = 0.5 + (p - 0.5) * 1.12
    p = sharpen(np.clip(p * 1.10, 0, 1), 1.1, 0.6)
    edge = np.clip(pa - cv2.GaussianBlur(pa, (0, 0), 5), 0, 1) * 2.2
    side = ss(XX, 300, 1620)[..., None]
    rim = (1 - side) * np.array([0.25, 0.55, 1.0]) + side * np.array([1.0, 0.25, 0.25])
    p = np.clip(p + edge[..., None] * rim * 0.45, 0, 1)
    sh = cv2.GaussianBlur(np.roll(pa, (14, 10), (0, 1)), (0, 0), 16) * 0.75
    canvas = over(canvas, np.zeros(3), sh)
    outline = cv2.dilate((pa > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    outline = cv2.GaussianBlur(outline.astype(np.float32), (0, 0), 1.0) * (1 - ss(YY, 820, 1000))
    canvas = over(canvas, np.ones(3), outline)
    canvas = over(canvas, p, pa)

    canvas = canvas * (1 - 0.45 * ss(YY, 620, 1080))[..., None]
    d = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
    canvas = canvas * (1 - 0.25 * ss(d, 0.7, 1.5))[..., None]

    lines = [[("DOBILI ", False), ("BATINE", True)], [("U SLOVAČKOJ?", False)]]
    t, layout, f = title_f(lines, 178, 1010, 790, 222, -4, (226, 24, 30))
    # Slovak flag sticker left of the second line
    canvas = paste_rgba_rot(canvas, slovak_flag(300), 330, 915, 8, border=8, shadow=0.7)
    canvas = over(canvas, t[..., :3], t[..., 3])
    rng = np.random.default_rng(5)
    canvas = np.clip(canvas + rng.normal(0, 0.01, (H, W, 1)), 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


TF_ARCHIVO = skia.Typeface.MakeFromFile(os.path.join(base.A, "fonts", "ArchivoBlack_400Regular.ttf"))


def build_g():
    """Title on top, new font, no coloured stage lights."""
    s_bg = 1.95
    bg = place(plate, s_bg, (W - base.PW * s_bg) / 2, -150 * s_bg)
    canvas = background(0)
    canvas, _ = paste_logo(canvas, LOGO_10P, 70, 330, 800, shadow=0.45, blur=4.0, opacity=0.95)
    canvas, _ = paste_logo(canvas, T_MARK, 1250, 330, 430, shadow=0.45, blur=4.0, opacity=0.95)

    s, cxp, hy = 1.85, 960, 455
    ox, oy = cxp - PEOPLE_ANCHOR[0] * s, hy - PEOPLE_ANCHOR[1] * s
    ppl = place(photo, s, ox, oy)
    pa = np.clip(place_alpha(matte, s, ox, oy), 0, 1)
    pa = np.clip((pa - 0.04) / 0.96, 0, 1)
    p = np.clip(ppl, 0, 1)
    lum = p.mean(2, keepdims=True)
    p = lum + (p - lum) * 1.15
    p = 0.5 + (p - 0.5) * 1.10
    p = sharpen(np.clip(p * 1.08, 0, 1), 1.1, 0.6)
    sh = cv2.GaussianBlur(np.roll(pa, (14, 10), (0, 1)), (0, 0), 16) * 0.75
    canvas = over(canvas, np.zeros(3), sh)
    outline = cv2.dilate((pa > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    outline = cv2.GaussianBlur(outline.astype(np.float32), (0, 0), 1.0) * (1 - ss(YY, 950, 1070))
    canvas = over(canvas, np.ones(3), outline)
    canvas = over(canvas, p, pa)

    canvas = canvas * (1 - 0.40 * (1 - ss(YY, 0, 470)))[..., None]   # darker top band for the title
    d = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
    canvas = canvas * (1 - 0.28 * ss(d, 0.7, 1.5))[..., None]

    lines = [[("DOBILI ", False), ("BATINE", True)], [("U SLOVAČKOJ?", False)]]
    t, layout, f = title_f(lines, 132, 880, 190, 172, -2, (226, 24, 30), skew=-0.12, stroke=14, tf=TF_ARCHIVO)
    canvas = paste_rgba_rot(canvas, slovak_flag(240), 1665, 300, -8, border=7, shadow=0.7)
    canvas = over(canvas, t[..., :3], t[..., 3])
    rng = np.random.default_rng(5)
    canvas = np.clip(canvas + rng.normal(0, 0.01, (H, W, 1)), 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    img = Image.fromarray(build_g())
    path = os.path.join(base.OUT, "thumbnail_G_tekst_gore.jpg")
    img.save(path, quality=93, subsampling=0, optimize=True)
    print("G", os.path.getsize(path) // 1024, "KB")

if __name__ == "__main__":
    img = Image.fromarray(build_f())
    path = os.path.join(base.OUT, "thumbnail_F_zastava.jpg")
    img.save(path, quality=93, subsampling=0, optimize=True)
    print("F", os.path.getsize(path) // 1024, "KB")
