"""Instagram Reel cover (1080x1920) in the goofy pink "SVINJAC" style.

Key content stays inside the centre 1080x1350 band, so the cover also reads in the profile-grid crop.
"""
import os
import sys

import cv2
import numpy as np
import skia
from PIL import Image

import make_thumbnails as base
import make_thumbnail_concepts as cc
from make_thumbnails import PEOPLE_ANCHOR, matte, over, photo, plate, sharpen, ss

CW, CH = 1080, 1920
YY, XX = np.mgrid[0:CH, 0:CW].astype(np.float32)
GRID = (285, 1635)   # centre band that survives the profile-grid crop


def place2(img, s, ox, oy, interp=cv2.INTER_LANCZOS4, border=cv2.BORDER_REFLECT):
    M = np.float32([[s, 0, ox], [0, s, oy]])
    return cv2.warpAffine(img, M, (CW, CH), flags=interp, borderMode=border)


def layer(draw):
    surf = skia.Surface(CW, CH)
    cv = surf.getCanvas()
    cv.clear(skia.ColorTRANSPARENT)
    draw(cv)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                            alphaType=skia.kUnpremul_AlphaType).astype(np.float32) / 255


def tag(cv, cx, top, rot=4):
    ft = skia.Font(cc.LUCKY, 50)
    t = "BJJ VLOG"
    tw = ft.measureText(t)
    cv.save()
    cv.rotate(rot, cx, top + 40)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - tw / 2 - 30, top, tw + 60, 80), 16, 16)
    shp = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 150))
    shp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    cv.save(); cv.translate(6, 8); cv.drawRRect(rr, shp); cv.restore()
    cv.drawRRect(rr, skia.Paint(AntiAlias=True, Color=skia.Color(255, 214, 20)))
    cv.drawRRect(rr, skia.Paint(AntiAlias=True, Color=cc.INK, StrokeWidth=7, Style=skia.Paint.kStroke_Style))
    cv.drawString(t, cx - tw / 2, top + 62, ft, skia.Paint(AntiAlias=True, Color=cc.INK))
    cv.restore()


def cover(layout):
    # backdrop: same plate, blur and grade as the landscape thumbnail
    sb = 1.95
    bg = place2(plate, sb, CW / 2 - 636 * sb, -60 * sb)
    bg = cv2.GaussianBlur(bg, (0, 0), 10)
    lum = bg.mean(2, keepdims=True)
    canvas = np.clip((lum + (bg - lum) * 0.8) * 0.45, 0, 1)

    s = 1.55
    hy = 560 if layout == "A" else 820
    ox, oy = CW / 2 - PEOPLE_ANCHOR[0] * s, hy - PEOPLE_ANCHOR[1] * s
    p = np.clip(place2(photo, s, ox, oy), 0, 1)
    a = np.clip(place2(matte, s, ox, oy, cv2.INTER_CUBIC, cv2.BORDER_CONSTANT), 0, 1)
    a = np.clip((a - 0.04) / 0.96, 0, 1)
    lum = p.mean(2, keepdims=True)
    p = lum + (p - lum) * 1.15
    p = sharpen(np.clip(np.clip(0.5 + (p - 0.5) * 1.10, 0, 1) * 1.06, 0, 1), 1.1, 0.6)
    sh = cv2.GaussianBlur(np.roll(a, (14, 10), (0, 1)), (0, 0), 16) * 0.85
    canvas = over(canvas, np.zeros(3), sh)
    canvas = over(canvas, p, a)
    lum = canvas.mean(2, keepdims=True)
    canvas = canvas + (1 - lum) * np.array([-0.036, 0.024, 0.06]) + lum * np.array([0.05, 0.01, -0.04])
    canvas = np.clip(0.5 + (canvas - 0.5) * 1.12, 0, 1)

    if layout == "A":     # title over the bodies (like the landscape thumbnail)
        canvas = canvas * (1 - 0.65 * ss(YY, 820, 1300))[..., None]
        word_y, line2_y, tag_y = 1060, 1215, 1290
    else:                 # title on top, people below
        canvas = canvas * (1 - 0.55 * (1 - ss(YY, 380, 760)))[..., None]
        canvas = canvas * (1 - 0.55 * ss(YY, 1350, 1700))[..., None]
        word_y, line2_y, tag_y = 565, 715, 1500

    def draw(cv):
        probe = skia.Font(cc.LUCKY, 100)
        size = 100 * 880 / (sum(probe.measureText(ch) for ch in "SVINJAC") + 6 * 6)
        f1 = skia.Font(cc.LUCKY, size)
        w1 = cc.bouncy_word(cv, "SVINJAC", CW / 2 - 20, word_y, f1, cc.PIG, cc.PIG_DK,
                            rots=[-8, 6, -5, 7, -6, 5, -4], dys=[0, -16, 8, -10, 10, -8, 4],
                            ink_w=22, white_w=40, spacing=6)
        f2 = skia.Font(cc.LUCKY, 100)
        cv.save(); cv.rotate(-4, CW / 2, line2_y)
        cc.bouncy_word(cv, "U SLOVAČKOJ!", CW / 2, line2_y, f2, (255, 255, 255), (232, 232, 240),
                       rots=[-3, 3, -2, 2], dys=[0, -6, 3, -4], ink_w=15, white_w=0, spacing=4)
        cv.restore()
        # pig sticker slapped on the top-right corner of the word
        cc.pig_face(cv, CW / 2 - 20 + w1 / 2 - 30, max(word_y - size * 0.95, GRID[0] + 118), 82, angle=16)
        tag(cv, CW / 2, tag_y)
    canvas = over(canvas, *(lambda l: (l[..., :3], l[..., 3]))(layer(draw)))

    d = np.sqrt(((XX - CW / 2) / (CW / 2)) ** 2 + ((YY - CH / 2) / (CH / 2)) ** 2)
    canvas = canvas * (1 - 0.2 * ss(d, 0.7, 1.5))[..., None]
    rng = np.random.default_rng(5)
    canvas = np.clip(canvas + rng.normal(0, 0.02, (CH, CW, 1)), 0, 1)
    return (canvas * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    out = os.path.join(base.OUT, "reel")
    os.makedirs(out, exist_ok=True)
    for lay, name in (("A", "naslov_preko_nas"), ("B", "naslov_gore")):
        if len(sys.argv) > 1 and lay not in sys.argv[1:]:
            continue
        path = os.path.join(out, f"reel_naslovna_{name}.jpg")
        Image.fromarray(cover(lay)).save(path, quality=93, subsampling=0, optimize=True)
        print(name, os.path.getsize(path) // 1024, "KB")
