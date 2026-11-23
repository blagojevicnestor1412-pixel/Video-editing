"""Renders every frame of the reel at 1080x1920 / 30 fps.
Usage: python3 -I render.py <workdir> [first last]"""
import sys, os, math, random, glob
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
import scipy.ndimage as nd

WD = sys.argv[1]
W, H, FPS = 1080, 1920, 30
RED = (232, 36, 28); WHITE = (255, 255, 255); INK = (16, 16, 16); YEL = (255, 210, 0)
SEGS = [(0.00, 1.62), (2.00, 4.95), (5.25, 8.75), (9.02, 12.25), (12.60, 16.55), (16.82, 19.07)]
MAP = []; _acc = 0.0
for a, b in SEGS:
    MAP.append((a, b, _acc)); _acc += b - a
BODY = _acc            # 17.50
TOTAL = BODY + 2.0     # 19.50
NFRAMES = round(TOTAL * FPS)

def src_of(t):
    for a, b, off in MAP:
        if off - 1e-9 <= t < off + (b - a) - 1e-9:
            return a + (t - off)
    return None

def o(src):
    for a, b, off in MAP:
        if a - 1e-6 <= src <= b + 1e-6: return off + src - a
    raise ValueError(src)

# ------------------------------------------------------------ helpers
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d)
def eo(p): return 1 - (1 - p) ** 3
def ei(p): return p ** 3
def eio(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2

@lru_cache(maxsize=64)
def font(weight, size, display=True):
    fam = "InterDisplay" if display else "Inter"
    c = glob.glob(f"/usr/share/fonts/**/{fam}-{weight}.*tf", recursive=True)
    return ImageFont.truetype(c[0], int(size))

@lru_cache(maxsize=16)
def emoji(ch, size):
    f = ImageFont.truetype(glob.glob("/usr/share/fonts/**/NotoColorEmoji*.ttf", recursive=True)[0], 109)
    im = Image.new("RGBA", (140, 130), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)

@lru_cache(maxsize=24)
def base_idx(i):
    i = max(0, min(571, i))
    return Image.open(f"{WD}/base/{i+1:04d}.jpg").convert("RGBA")

def base(src): return base_idx(round(src * FPS)).copy()

def _raw_mask(i):
    p = f"{WD}/mask/{i:04d}.png"
    return np.asarray(Image.open(p), np.float32) / 255 if os.path.exists(p) else None

@lru_cache(maxsize=24)
def mask_idx(i, cut=None, blend=True):
    m = _raw_mask(i)
    if blend:
        nb = [x for x in (_raw_mask(i - 1), _raw_mask(i + 1)) if x is not None]
        if len(nb) == 2: m = 0.5 * m + 0.25 * (nb[0] + nb[1])
    mb = m > 0.5
    if cut is not None:
        mb = nd.binary_opening(mb, structure=np.ones((9, 9)))
        mb[:cut] = False
        mb = nd.binary_fill_holes(mb)
        lab, n = nd.label(mb)
        if n > 1:
            sz = nd.sum(mb, lab, range(1, n + 1)); mb = lab == 1 + int(np.argmax(sz))
    im = Image.fromarray((mb * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return im.filter(ImageFilter.GaussianBlur(2))

def zoom(img, s, cx=0.5, cy=0.5):
    if abs(s - 1) < 1e-4: return img
    w, h = W / s, H / s
    x0 = clamp(cx * W - w / 2, 0, W - w); y0 = clamp(cy * H - h / 2, 0, H - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

def zoom_blur(img, amount, cx=0.5, cy=0.5, n=6):
    if amount <= 0.002: return img
    acc = np.zeros((H, W, 4), np.float32)
    for k in range(n):
        acc += np.asarray(zoom(img, 1 + amount * k / (n - 1), cx, cy), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8), "RGBA")

def paste_shadowed(base_img, layer, xy, off=(0, 20), blur=30, alpha=140):
    a = layer.split()[-1].point(lambda v: v * alpha // 255)
    pad = blur * 2
    sh = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", layer.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (pad, pad))
    sh = sh.resize((sh.width // 4, sh.height // 4)).filter(ImageFilter.GaussianBlur(blur / 4)).resize(sh.size)
    base_img.alpha_composite(sh, (int(xy[0] - pad + off[0]), int(xy[1] - pad + off[1])))
    base_img.alpha_composite(layer, (int(xy[0]), int(xy[1])))

def fade(layer, a):
    if a >= 1: return layer
    l = layer.copy(); l.putalpha(l.split()[-1].point(lambda v: int(v * a))); return l

def scaled(layer, s):
    s = max(s, 0.01)
    return layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.BICUBIC)

def put_center(img, layer, cx, cy, s=1.0, a=1.0):
    l = fade(scaled(layer, s), a)
    img.alpha_composite(l, (int(cx - l.width / 2), int(cy - l.height / 2)))

# ------------------------------------------------------------ captions
CAPS = [  # (src_start, words, highlighted, size)
    (0.00, ["JER", "JIU-JITSU"], {"JIU-JITSU"}, 80), (0.95, ["NIJE", "NEKA"], set(), 80),
    (3.20, ["AHA"], set(), 80), (3.42, ["SAD", "ĆU", "JA", "DA", "SKOČIM"], {"SKOČIM"}, 74),
    (6.20, ["NA", "BRZAKA"], {"BRZAKA"}, 124),
    (6.80, ["SVI", "ĆE", "ONI", "DA", "MI"], set(), 76), (7.40, ["APLAUDIRAJU"], {"APLAUDIRAJU"}, 96),
    (8.15, ["ZNAŠ"], set(), 80), (8.40, ["KAO", "NA"], set(), 80), (9.10, ["TAKMIČENJU"], {"TAKMIČENJU"}, 88),
    (10.00, ["JER", "MORA", "UVEK"], {"MORA", "UVEK"}, 108), (10.80, ["DA", "SE", "NAPRAVI"], set(), 80),
    (11.40, ["TA", "PARALELA", "IZMEĐU"], {"PARALELA"}, 78),
    (12.80, ["SPORTSKOG", "DELA"], {"SPORTSKOG"}, 82), (14.00, ["REALNOG", "DELA"], {"REALNOG"}, 82),
    (14.45, ["TO", "JEST", "PRIMENE"], {"PRIMENE"}, 82), (15.20, ["TOGA", "SVEGA", "ŠTO"], set(), 80),
    (15.80, ["RADIŠ"], {"RADIŠ"}, 88), (16.15, ["TAKO", "DA"], set(), 80),
    (16.90, ["AKO", "GA", "TRENIRAŠ"], {"TRENIRAŠ"}, 80), (17.95, ["I", "DAN", "DANAS"], {"DANAS"}, 88),
]
CAP_END = {11.40: 12.25, 0.95: 1.62, 16.15: 16.55, 6.20: 6.77, 3.42: 4.20}
HIDE = [(1.62, 2.82), (3.82, 5.52), (11.30, 11.48), (BODY, 99)]

@lru_cache(maxsize=32)
def cap_layer(words, hi, size):
    f = font("Black", size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    sp = size * 0.28
    ws = [d0.textlength(w, font=f) for w in words]
    tw = sum(ws) + sp * (len(words) - 1)
    L = Image.new("RGBA", (int(tw + 80), int(size * 1.7)), (0, 0, 0, 0))
    shadow = Image.new("RGBA", L.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    x = 40
    pills = []
    for w, wd in zip(words, ws):
        if w in hi: pills.append((x, wd))
        else: sd.text((x, size * 0.22 + 6), w, font=f, fill=(0, 0, 0, 210))
        x += wd + sp
    L.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    for x, wd in pills:
        p = Image.new("RGBA", (int(wd + 36), int(size * 1.24)), (0, 0, 0, 0))
        ImageDraw.Draw(p).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=int(size * 0.2), fill=RED + (255,))
        p = p.rotate(-2, expand=True, resample=Image.BICUBIC)
        L.alpha_composite(p, (int(x - 18), int(size * 0.14)))
    d = ImageDraw.Draw(L); x = 40
    for w, wd in zip(words, ws):
        d.text((x, size * 0.22), w, font=f, fill=WHITE); x += wd + sp
    return L

def captions(img, t, y=1320):
    if any(a <= t < b for a, b in HIDE): return
    s = src_of(t)
    if s is None: return
    for k, (st, words, hi, size) in enumerate(CAPS):
        nxt = CAPS[k + 1][0] if k + 1 < len(CAPS) else 99
        end = min(nxt, CAP_END.get(st, st + 1.3))
        if st <= s < end:
            # time since chunk became visible in output time
            try: ts = t - o(st)
            except ValueError: ts = 1
            if ts < 0: ts = 1
            p = clamp(ts * FPS / 5)
            sc = 0.72 + 0.28 * back(p, 2.4) if p < 1 else 1.0
            L = cap_layer(tuple(words), frozenset(hi), size)
            if L.width > W - 60: L = scaled(L, (W - 60) / L.width)
            put_center(img, L, W / 2, y, sc, clamp(ts * FPS / 2))
            return

# ------------------------------------------------------------ S1 ORBIT
RING_TXT = " JIU-JITSU • JIU-JITSU • JIU-JITSU •"
_fref = font("Black", 80)
RING_ADV = [max(_fref.getlength(c), 24) for c in RING_TXT]
RING_TOT = sum(RING_ADV)

@lru_cache(maxsize=256)
def glyph(ch, size, col):
    f = font("Black", size)
    g = Image.new("RGBA", (int(size * 1.6), int(size * 1.6)), (0, 0, 0, 0))
    ImageDraw.Draw(g).text((size * 0.8, size * 1.1), ch, font=f, fill=col, anchor="ms")
    return g

def s1(t):
    src = t
    img = base(src)
    i = round(src * FPS)
    m = mask_idx(i, cut=336 * 1)  # cut in 540-scale rows; mask arrays are 540x960
    pin = eo(prog(t, 0, 10 / FPS))
    cx, cy, rx, ry = 520, 790, 440 * (0.6 + 0.4 * pin), 84 * (0.6 + 0.4 * pin)
    phase = t * 2 * math.pi / 2.4
    tilt = math.radians(-6)
    back_l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); front_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cum = 0
    for k, ch in enumerate(RING_TXT):
        a = math.pi * 0.9 - 2 * math.pi * (cum + RING_ADV[k] / 2) / RING_TOT + phase
        cum += RING_ADV[k]
        if ch == " ": continue
        dx, dy = rx * math.cos(a), ry * math.sin(a)
        x = cx + dx * math.cos(tilt) - dy * math.sin(tilt); y = cy + dx * math.sin(tilt) + dy * math.cos(tilt) - 16
        depth = (math.sin(a) + 1) / 2
        size = int(80 * (2 * math.pi * 440 / RING_TOT) * 0.95 * (0.62 + 0.38 * depth) * (0.4 + 0.6 * pin))
        size = max(8, size // 2 * 2)
        if depth > 0.5:
            col = (255, 255, 255, int((120 + 135 * depth) * pin)); tgt = front_l
        else:
            col = (240, 70, 58, int((90 + 120 * depth) * pin)); tgt = back_l
        g = glyph(ch, size, col)
        tgt.alpha_composite(g, (int(x - g.width / 2), int(y - size * 1.1 + size * 0.36)))
    out = img.copy()
    out.alpha_composite(back_l)
    subj = img.copy(); subj.putalpha(m)
    out.alpha_composite(subj)
    glow = front_l.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(4)).resize((W, H))
    out.alpha_composite(glow); out.alpha_composite(front_l)
    out = zoom(out, 1 + 0.06 * eio(prog(t, 0, 1.62)), 0.5, 0.45)
    return out

# ------------------------------------------------------------ S2 PAPER CUTOUT
@lru_cache(maxsize=1)
def paper_bg():
    rng = np.random.default_rng(5)
    nse = (rng.random((H // 2, W // 2)) * 20).astype(np.uint8)
    nse = np.asarray(Image.fromarray(nse).resize((W, H), Image.BICUBIC))
    arr = np.dstack([236 - nse, 228 - nse, 214 - nse, np.full((H, W), 255, np.uint8)])
    img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    r = random.Random(11)
    strip = Image.new("RGBA", (W + 160, 460), RED + (255,))
    sm = Image.new("L", strip.size, 0); d = ImageDraw.Draw(sm)
    pts = [(0, 60)] + [(x, 36 + r.randint(-28, 28)) for x in range(0, strip.width, 44)] + [(strip.width, 60), (strip.width, 400)] + \
          [(x, 424 + r.randint(-28, 28)) for x in range(strip.width, 0, -44)] + [(0, 400)]
    d.polygon(pts, fill=255); strip.putalpha(sm)
    img.alpha_composite(strip.rotate(-6, expand=True, resample=Image.BICUBIC), (-120, 180))
    return img

@lru_cache(maxsize=4)
def word_tag(txt, fg, bgc, size, rot):
    f = font("Black", size)
    tw = f.getlength(txt)
    t = Image.new("RGBA", (int(tw + 56), int(size * 1.35)), bgc + (255,))
    ImageDraw.Draw(t).text((28, size * 0.08), txt, font=f, fill=fg)
    return t.rotate(rot, expand=True, resample=Image.BICUBIC)

def paper_comp(t):
    src = src_of(t)
    sq = math.floor(src * 12) / 12
    i = round(sq * FPS)
    jit = random.Random(i)
    img = paper_bg().copy()
    b = base_idx(i).copy()
    m = mask_idx(i, cut=284, blend=False)
    border = m.filter(ImageFilter.MaxFilter(31)).point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.GaussianBlur(2))
    st = Image.new("RGBA", (W, H), (250, 248, 242, 255)); st.putalpha(border)
    b.putalpha(m); st.alpha_composite(b)
    bb = st.getbbox(); st = st.crop(bb)
    st = st.rotate(3 + jit.uniform(-0.6, 0.6), expand=True, resample=Image.BICUBIC)
    st = scaled(st, 0.9)
    paste_shadowed(img, st, ((W - st.width) // 2 + 20 + jit.randint(-3, 3), H - st.height + 80 + jit.randint(-3, 3)), off=(12, 24), blur=20, alpha=120)
    for (txt, fg, bgc, size, rot, xy, t0) in [("„SKOČIMIŠ“", WHITE, (18, 18, 18), 116, 4, (80, 300), 1.82),
                                             ("VARIJANTA", (18, 18, 18), YEL, 88, -3, (300, 472), 2.22),
                                             ("?!", WHITE, RED, 100, 8, (840, 240), 2.32)]:
        if t < t0: continue
        p = prog(t, t0, 4 / FPS)
        tag = word_tag(txt, fg, bgc, size, rot)
        sc = 1.35 - 0.35 * eo(p)
        tg = fade(scaled(tag, sc), clamp(p * 2))
        cxy = (xy[0] + tag.width / 2 - tg.width / 2, xy[1] + tag.height / 2 - tg.height / 2)
        paste_shadowed(img, tg, cxy, off=(6, 12), blur=12, alpha=110)
    return img

def s2(t):
    live = base(src_of(t))
    comp = paper_comp(t)
    # tear-wipe in (6 frames)
    p_in = prog(t, 1.62, 6 / FPS)
    if p_in < 1:
        r = random.Random(3)
        edge_y = -120 + (H + 240) * eo(p_in)
        mk = Image.new("L", (W, H), 0)
        pts = [(0, 0), (W, 0)] + [(x, edge_y + r.randint(-40, 40)) for x in range(W, -60, -60)]
        ImageDraw.Draw(mk).polygon(pts, fill=255)
        live.paste(comp, (0, 0), mk)
        return live
    # peel out (last 8 frames)
    p_out = prog(t, 2.82 - 8 / FPS, 8 / FPS)
    if p_out > 0:
        q = p_out ** 2
        c2 = comp.rotate(14 * q, resample=Image.BICUBIC, center=(0, 0), translate=(-1300 * q, -600 * q))
        paste_shadowed(live, c2, (0, 0), off=(0, 30), blur=30, alpha=int(160 * (1 - q)))
        return live
    return comp

# ------------------------------------------------------------ S3 PORTAL + type card
def tunnel(t, w=540, h=960):
    img = Image.new("RGBA", (w, h), (18, 6, 7, 255)); d = ImageDraw.Draw(img)
    cx, cy = w / 2, h / 2
    ph = (t * 1.6) % 1
    for k in range(9, -1, -1):
        r = 22 * 1.55 ** (k + ph)
        a = int(clamp(r / 300) * 220)
        wd = max(2, int(r * 0.05))
        d.rounded_rectangle([cx - r * 0.75, cy - r, cx + r * 0.75, cy + r], radius=int(r * 0.3), outline=(232, 36, 28, a), width=wd)
    g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=(255, 80, 60, 120))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
    return img

@lru_cache(maxsize=4)
def echo_text(txt, size):
    f = font("Black", size)
    tw = f.getlength(txt)
    L = Image.new("RGBA", (int(tw + 60), int(size * 1.4)), (0, 0, 0, 0))
    ImageDraw.Draw(L).text((30, size * 0.1), txt, font=f, fill=WHITE)
    O = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(O).text((30, size * 0.1), txt, font=f, fill=(0, 0, 0, 0), stroke_width=4, stroke_fill=RED + (255,))
    if L.width > 980:
        k = 980 / L.width; L = scaled(L, k); O = scaled(O, k)
    return L, O

def type_card(t):
    img = tunnel(t).resize((W, H), Image.BICUBIC)
    if t < 4.72:
        L, O = echo_text("SKOČIM", 260)
        p = prog(t, 3.92, 0.8)
        for k in range(5, 0, -1):
            put_center(img, O, W / 2, H / 2, 1 + 0.12 * k * (0.4 + p), 0.5 * (1 - k / 6))
        put_center(img, L, W / 2, H / 2, 1.0 + 0.05 * p)
        sub = cap_layer(("I", "DA", "NAPRAVIM", "NEKI…"), frozenset({"NAPRAVIM"}), 62)
        put_center(img, sub, W / 2, H / 2 + 260, 1, prog(t, 4.0, 3 / FPS))
    else:
        p = prog(t, 4.72, 4 / FPS)
        fl = 1 - prog(t, 4.72, 8 / FPS)
        if fl > 0: img.alpha_composite(Image.new("RGBA", (W, H), RED + (int(230 * fl),)))
        L, O = echo_text("SUBMISSION", 176)
        r = random.Random(int(t * FPS))
        sh = 18 * (1 - prog(t, 4.72, 8 / FPS))
        for k in range(4, 0, -1):
            put_center(img, O, W / 2, H / 2, 1 + 0.1 * k, 0.45 * (1 - k / 5))
        put_center(img, L, W / 2 + r.uniform(-sh, sh), H / 2 + r.uniform(-sh, sh), 1.6 - 0.6 * eo(p), clamp(p * 3))
    return img

PCX, PCY, PR = 300, 380, 236
def portal_layer(t, scale_in):
    r = int(PR * scale_in)
    if r < 4: return None, r
    content = tunnel(t, 2 * PR, 2 * PR)
    L, _ = echo_text("SKOK", 150)
    put_center(content, L, PR, PR, 0.9 + 0.08 * math.sin(t * 9), 1)
    cm = Image.new("L", content.size, 0); ImageDraw.Draw(cm).ellipse([0, 0, 2 * PR - 1, 2 * PR - 1], fill=255)
    content.putalpha(cm)
    return scaled(content, scale_in), r

def s3(t):
    img = base(src_of(t)) if t < 3.82 else None
    p_open = back(prog(t, 3.07, 10 / FPS), 1.6) if t >= 3.07 else 0
    if t < 3.82:
        if p_open > 0:
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(ring)
            r = PR * p_open
            for k, a in [(36, 60), (22, 110), (8, 255)]:
                rd.ellipse([PCX - r - k, PCY - r - k, PCX + r + k, PCY + r + k], outline=RED + (a,), width=k)
            img.alpha_composite(ring.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(4)).resize((W, H)))
            img.alpha_composite(ring)
            c, rr = portal_layer(t, p_open)
            if c is not None: img.alpha_composite(c, (int(PCX - c.width / 2), int(PCY - c.height / 2)))
        return img
    # push through (9 frames) then full-frame type card
    p = prog(t, 3.82, 9 / FPS)
    if p < 1:
        img = base(src_of(t))
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(ring)
        for k, a in [(36, 60), (22, 110), (8, 255)]:
            rd.ellipse([PCX - PR - k, PCY - PR - k, PCX + PR + k, PCY + PR + k], outline=RED + (a,), width=k)
        img.alpha_composite(ring)
        c, _ = portal_layer(t, 1)
        img.alpha_composite(c, (PCX - PR, PCY - PR))
        s = 1 + 3.2 * ei(p)
        img = zoom_blur(zoom(img, s, PCX / W, PCY / H), 0.15 * p, 0.5, 0.5)
        if p > 0.55:
            img = Image.blend(img, type_card(t), clamp((p - 0.55) / 0.45))
        return img
    return type_card(t)

# ------------------------------------------------------------ S4 SNAP ZOOM + zoom-through
SPEED = None
def speed_lines():
    global SPEED
    if SPEED is None:
        r = random.Random(4)
        SPEED = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(SPEED)
        for _ in range(60):
            a = r.uniform(0, 2 * math.pi); r0 = r.uniform(600, 720)
            d.line([(540 + r0 * math.cos(a), 800 + r0 * math.sin(a) * 1.4), (540 + 1400 * math.cos(a), 800 + 1400 * math.sin(a) * 1.4)], fill=(255, 255, 255, 110), width=4)
    return SPEED

def s4(t):
    img = base(src_of(t))
    cy = 0.40
    p = prog(t, 5.52, 3 / FPS)
    s = 1 + 0.38 * eo(p)
    blur = 0.10 * (1 - abs(2 * p - 1)) if 0 < p < 1 else 0
    if t >= 5.96:
        q = prog(t, 5.96, 4 / FPS)
        s *= 1 + 0.6 * ei(q); blur = 0.25 * q
    out = zoom(img, s, 0.5, cy)
    out = zoom_blur(out, blur)
    sl = 1 - prog(t, 5.52, 10 / FPS)
    if t >= 5.52 and sl > 0: out.alpha_composite(fade(speed_lines(), sl))
    return out

# ------------------------------------------------------------ S5 CHAT TAKEOVER
MSGS = [("marko_bjj", "BRAVOOO ŠAMPIONE", "🏆", (232, 36, 28)), ("ana.grappling", "legenda", "🔥", (90, 90, 255)),
        ("nikola_92", "kakav submission!!", "😱", (255, 170, 0)), ("jiu_jitsu_bg", "aplauz za majstora", "👏", (60, 200, 120)),
        ("stefan.mma", "10/10", "💯", (200, 80, 200)), ("luka.grappler", "neviđeno", "👏", (40, 170, 220))]

@lru_cache(maxsize=8)
def bubble(k):
    u, m, e, col = MSGS[k]
    fu = font("Bold", 28, False); fm = font("SemiBold", 38, False)
    tw = max(fu.getlength(u), fm.getlength(m) + 68)
    b = Image.new("RGBA", (int(tw + 140), 124), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
    bd.rounded_rectangle([0, 0, b.width - 1, 123], radius=40, fill=(20, 20, 22, 215), outline=(255, 255, 255, 46), width=2)
    bd.ellipse([20, 26, 92, 98], fill=col)
    bd.text((112, 18), u, font=fu, fill=(200, 200, 205)); bd.text((112, 56), m, font=fm, fill=WHITE)
    b.alpha_composite(emoji(e, 46), (int(112 + fm.getlength(m) + 14), 60))
    return b

PARTS = [(random.Random(k).uniform(6.70, 7.70), random.Random(k + 50).uniform(740, 1020), random.Random(k + 90).choice("👏👏👏❤🔥"),
          random.Random(k + 130).randint(56, 96), random.Random(k + 170).uniform(-25, 25)) for k in range(18)]

def s5(t):
    img = base(src_of(t))
    if t < 6.09 + 6 / FPS:
        q = prog(t, 6.09, 6 / FPS)
        img = zoom_blur(zoom(img, 1.6 - 0.6 * eo(q), 0.5, 0.42), 0.2 * (1 - q))
    p_dim = prog(t, 6.15, 6 / FPS); p_ex = prog(t, 7.72, 6 / FPS)
    k_dim = p_dim * (1 - p_ex)
    if k_dim > 0:
        img = Image.blend(img, img.filter(ImageFilter.GaussianBlur(12)), k_dim)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(80 * k_dim))))
    if t < 7.72 + 6 / FPS:
        dx = -1200 * ei(p_ex)
        for k in range(len(MSGS)):
            t0 = 6.15 + k * 5 / FPS
            if t < t0: break
            p = prog(t, t0, 6 / FPS)
            b = bubble(k)
            sc = (0.85 + 0.03 * (k % 3)) * (0.8 + 0.2 * back(p, 1.5))
            bb = fade(scaled(b, sc), clamp(p * 2) * (1 - p_ex))
            paste_shadowed(img, bb, (48 + (k % 2) * 80 + dx, 560 + k * 140 + 40 * (1 - eo(p))), off=(0, 12), blur=20, alpha=int(120 * (1 - p_ex)))
        for (t0, x, ch, sz, rot) in PARTS:
            if t < t0: continue
            age = t - t0
            a = clamp(1 - age / 1.0) * (1 - p_ex)
            if a <= 0: continue
            e = emoji(ch, sz).rotate(rot + 30 * age, expand=True, resample=Image.BICUBIC)
            img.alpha_composite(fade(e, a), (int(x + 30 * math.sin(age * 6)), int(1500 - 620 * age)))
    return img

# ------------------------------------------------------------ S6 LIQUID GLASS
def glass(img, t):
    p_in = prog(t, 7.97, 10 / FPS); p_out = prog(t, 8.85, 6 / FPS)
    if p_in <= 0 or p_out >= 1: return img
    x0, y0, x1, y1 = 80, 1120, 1000, 1580
    dy = 120 * (1 - eo(p_in))
    pan = Image.new("RGBA", (x1 - x0 + 80, y1 - y0 + 80), (0, 0, 0, 0))
    reg = img.crop((x0 - 40, int(y0 - 40 + dy), x1 + 40, int(y1 + 40 + dy)))
    reg = reg.resize((reg.width // 4, reg.height // 4)).filter(ImageFilter.GaussianBlur(8)).resize(reg.size)
    reg = ImageEnhance.Brightness(reg).enhance(1.25)
    pm = Image.new("L", reg.size, 0); ImageDraw.Draw(pm).rounded_rectangle([40, 40, reg.width - 41, reg.height - 41], radius=68, fill=255)
    pan.paste(reg, (0, 0), pm)
    od = ImageDraw.Draw(pan)
    od.rounded_rectangle([40, 40, pan.width - 41, pan.height - 41], radius=68, fill=(255, 255, 255, 34), outline=(255, 255, 255, 130), width=3)
    hl = Image.new("RGBA", pan.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([56, 52, pan.width - 56, 140], radius=52, fill=(255, 255, 255, 44))
    pan.alpha_composite(hl.filter(ImageFilter.GaussianBlur(12)))
    sp = prog(t, 8.15, 0.45)
    if 0 < sp < 1:
        sw = Image.new("L", pan.size, 0)
        sx = -300 + (pan.width + 600) * sp
        ImageDraw.Draw(sw).polygon([(sx, 0), (sx + 120, 0), (sx - 80, pan.height), (sx - 200, pan.height)], fill=70)
        sw = ImageChops.multiply(sw.filter(ImageFilter.GaussianBlur(20)), pm)
        wl = Image.new("RGBA", pan.size, (255, 255, 255, 0)); wl.putalpha(sw); pan.alpha_composite(wl)
    d = ImageDraw.Draw(pan); ox, oy = 40, 40
    d.text((ox + 56, oy + 44), "TAKMIČENJE", font=font("Bold", 36, False), fill=(255, 255, 255, 225))
    secs = 272 - int(max(0, t - 7.97))
    d.text((ox + 700, oy + 44), f"● 0{secs//60}:{secs%60:02d}", font=font("SemiBold", 36, False), fill=RED)
    score = "0" if t < 8.35 else ("1" if t < 8.42 else "2")
    d.text((ox + 56, oy + 120), score, font=font("Black", 192), fill=WHITE)
    d.text((ox + 240, oy + 184), "–", font=font("Black", 100), fill=(255, 255, 255, 150))
    d.text((ox + 340, oy + 120), "0", font=font("Black", 192), fill=(255, 255, 255, 170))
    for i, (k, v) in enumerate([("ADV", "1"), ("PEN", "0"), ("SUB", "?")]):
        a = prog(t, 8.30 + i * 0.07, 4 / FPS)
        d.text((ox + 600, oy + 144 + i * 76), k, font=font("Medium", 34, False), fill=(255, 255, 255, int(180 * a)))
        d.text((ox + 740, oy + 136 + i * 76), v, font=font("Black", 44), fill=(WHITE if v != "?" else RED) + (int(255 * a),))
    s = 1 - 0.1 * eo(p_out)
    pan = fade(scaled(pan, s), clamp(p_in * 2) * (1 - p_out))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + dy
    paste_shadowed(img, pan, (cx - pan.width / 2, cy - pan.height / 2), off=(0, 20), blur=30, alpha=int(110 * (1 - p_out)))
    return img

# ------------------------------------------------------------ S7 DOLLY ZOOM
@lru_cache(maxsize=4)
def s7_frame(fi):
    t = fi / FPS
    src = src_of(t)
    i = round(src * FPS)
    img = base_idx(i).copy()
    m = mask_idx(i)
    # clean plate: normalized blur of the background without the subject (at quarter res)
    small = np.asarray(img.convert("RGB").resize((270, 480)), np.float32)
    ms = np.asarray(m.resize((270, 480)).filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    wgt = 1 - ms
    num = np.stack([nd.gaussian_filter(small[..., c] * wgt, 18) for c in range(3)], -1)
    den = nd.gaussian_filter(wgt, 18)[..., None] + 1e-4
    fill = num / den
    plate = small * wgt[..., None] + fill * ms[..., None]
    bg = Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).convert("RGBA")
    bg = Image.blend(bg, img, 0.0)
    p = eio(prog(t, 9.05, 2.25))
    bg = zoom(bg, 1 + 0.35 * p, 0.5, 0.4).filter(ImageFilter.GaussianBlur(1 + 3 * p))
    bg = ImageEnhance.Brightness(bg).enhance(1 - 0.25 * p)
    out = bg
    rim = Image.new("RGBA", (W, H), RED + (0,))
    rim.putalpha(m.filter(ImageFilter.MaxFilter(15)).point(lambda v: int(v * 0.55 * p)))
    out.alpha_composite(rim.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(6)).resize((W, H)))
    subj = img.copy(); subj.putalpha(m)
    out.alpha_composite(subj)
    return out

def s7(t):
    return s7_frame(round(t * FPS)).copy()

# ------------------------------------------------------------ FRAME BREAK + S8 CHECKLIST
def build_shards():
    r = random.Random(7)
    cx, cy = 560, 860
    rings = [0, 200, 480, 860, 1900]
    angs = sorted(r.uniform(0, 2 * math.pi) for _ in range(11))
    shards = []
    for ri in range(len(rings) - 1):
        for ai in range(len(angs)):
            a0 = angs[ai]; a1 = angs[(ai + 1) % len(angs)] + (2 * math.pi if ai == len(angs) - 1 else 0)
            r0, r1 = rings[ri], rings[ri + 1]
            j = lambda rr: rr * r.uniform(0.9, 1.1)
            poly = [(cx + j(r0) * math.cos(a0), cy + j(r0) * math.sin(a0)), (cx + j(r1) * math.cos(a0), cy + j(r1) * math.sin(a0)),
                    (cx + j(r1) * math.cos(a1), cy + j(r1) * math.sin(a1)), (cx + j(r0) * math.cos(a1), cy + j(r0) * math.sin(a1))]
            shards.append(dict(poly=poly, ri=ri, am=(a0 + a1) / 2, rot=r.uniform(-12, 12), gone=(ri == 0 or r.random() < 0.25), delay=r.uniform(0, 0.25)))
    return shards, (cx, cy)
SHARDS, IMPACT = build_shards()

def frame_break(under, t):
    frozen = s7_frame(round(11.30 * FPS) - 1)
    out = under
    p = prog(t, 11.37, 10 / FPS)
    flash = 1 - prog(t, 11.30, 6 / FPS)
    for sd in SHARDS:
        if p > 0 and sd["gone"]: continue
        pm = Image.new("L", (W, H), 0); ImageDraw.Draw(pm).polygon(sd["poly"], fill=255)
        bb = pm.getbbox()
        if not bb: continue
        q = clamp((p - sd["delay"]) / (1 - sd["delay"])) if p > 0 else 0
        sh = frozen.crop(bb); sh.putalpha(pm.crop(bb))
        edge = Image.new("RGBA", sh.size, (255, 255, 255, 0))
        edge.putalpha(sh.split()[-1].filter(ImageFilter.FIND_EDGES).point(lambda v: min(255, v * 4)))
        sh.alpha_composite(edge)
        if q > 0:
            sh = sh.rotate(sd["rot"] * q, expand=True, resample=Image.BICUBIC)
            sh = scaled(sh, 1 + 0.15 * q)
        push = (40 + sd["ri"] * 60) * (0.3 + 5 * q * q) if p > 0 else 0
        x = bb[0] + push * math.cos(sd["am"]); y = bb[1] + push * math.sin(sd["am"]) + 400 * q * q
        a = 1 - clamp((q - 0.6) / 0.4)
        if a <= 0: continue
        paste_shadowed(out, fade(sh, a), (x, y), off=(0, 16), blur=16, alpha=int(150 * a))
    if flash > 0:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([IMPACT[0] - 160, IMPACT[1] - 160, IMPACT[0] + 160, IMPACT[1] + 160], fill=(255, 255, 255, int(200 * flash)))
        out.alpha_composite(g.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(14)).resize((W, H)))
    return out

@lru_cache(maxsize=4)
def card(txt, chk):
    f = font("Black", 64)
    tw = f.getlength(txt)
    c = Image.new("RGBA", (int(tw + (208 if chk else 96)), 140), (0, 0, 0, 0)); cd = ImageDraw.Draw(c)
    cd.rounded_rectangle([0, 0, c.width - 1, 139], radius=36, fill=(255, 255, 255, 245) if chk else RED + (245,))
    if chk:
        cd.ellipse([28, 28, 112, 112], fill=RED)
        cd.text((144, 26), txt, font=f, fill=INK)
    else:
        cd.text((48, 26), txt, font=f, fill=WHITE)
    return c

def check_mark(c, p):
    c = c.copy(); d = ImageDraw.Draw(c)
    pts = [(48, 72), (66, 90), (94, 50)]
    L1 = math.dist(pts[0], pts[1]); L2 = math.dist(pts[1], pts[2]); tot = (L1 + L2) * p
    if tot <= 0: return c
    if tot <= L1:
        e = (pts[0][0] + (pts[1][0] - pts[0][0]) * tot / L1, pts[0][1] + (pts[1][1] - pts[0][1]) * tot / L1)
        d.line([pts[0], e], fill=WHITE, width=12)
    else:
        k = (tot - L1) / L2
        e = (pts[1][0] + (pts[2][0] - pts[1][0]) * k, pts[1][1] + (pts[2][1] - pts[1][1]) * k)
        d.line([pts[0], pts[1], e], fill=WHITE, width=12, joint="curve")
    return c

CARDS = [("SPORTSKI DEO", True, 11.50), ("REALNI DEO", True, 12.70), ("= PRIMENA", False, 13.30)]
def s8(t):
    img = base(src_of(t))
    img = zoom(img, 1 + 0.12 * eio(prog(t, 11.30, 3.95)), 0.5, 0.42)
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 50)))
    if t < 11.70:
        img = frame_break(img, t)
    ex0 = 15.00
    la = prog(t, 11.45, 6 / FPS) * (1 - prog(t, ex0, 6 / FPS))
    if la > 0:
        lab = Image.new("RGBA", (500, 60), (0, 0, 0, 0))
        ImageDraw.Draw(lab).text((0, 0), "TA PARALELA:", font=font("Bold", 38, False), fill=(255, 255, 255, 220))
        img.alpha_composite(fade(lab, la), (80, int(236 - 300 * prog(t, ex0, 8 / FPS) ** 2)))
    for k, (txt, chk, t0) in enumerate(CARDS):
        if t < t0: continue
        p = prog(t, t0, 8 / FPS)
        c = card(txt, chk)
        if chk: c = check_mark(c, eo(prog(t, t0 + 3 / FPS, 6 / FPS)))
        sc = 0.6 + 0.4 * back(p, 2.2)
        a = clamp(p * 3)
        if k < 2 and t > 13.30: a *= 1 - 0.4 * prog(t, 13.30, 6 / FPS)
        q = prog(t, ex0 + k * 2 / FPS, 8 / FPS)
        a *= 1 - q
        if a <= 0: continue
        cc = fade(scaled(c, sc), a)
        y = 300 + k * 184 + (c.height - cc.height) / 2 - 1100 * q * q
        paste_shadowed(img, cc, (68 + (c.width - cc.width) / 2, y), off=(0, 20), blur=28, alpha=int(150 * a))
    return img

# ------------------------------------------------------------ S9 + END CARD
def s9(t):
    img = base(src_of(t))
    img = zoom(img, 1.08 - 0.08 * eo(prog(t, 15.25, 2.0)), 0.5, 0.42)
    sp = prog(t, 15.45, 0.9)
    if 0 < sp < 1:
        sw = Image.new("L", (W // 4, H // 4), 0)
        sx = -120 + (W // 4 + 240) * eio(sp)
        ImageDraw.Draw(sw).polygon([(sx, 0), (sx + 80, 0), (sx - 10, H // 6), (sx - 90, H // 6)], fill=34)
        sw = sw.filter(ImageFilter.GaussianBlur(14)).resize((W, H))
        img = Image.composite(ImageChops.add(img, Image.new("RGBA", (W, H), (255, 230, 220, 255))), img, sw)
    return img

@lru_cache(maxsize=1)
def cover_parts():
    i = 318
    src = base_idx(i).copy()
    m = mask_idx(i)
    bg = ImageEnhance.Brightness(src).enhance(0.55)
    bg.alpha_composite(Image.new("RGBA", (W, H), (60, 0, 0, 90)))
    person = src.copy(); person.putalpha(m)
    mf = font("Black", 264); tw = mf.getlength("JIU-JITSU")
    mast = Image.new("RGBA", (int(tw + 20), 340), (0, 0, 0, 0))
    ImageDraw.Draw(mast).text((0, 0), "JIU-JITSU", font=mf, fill=WHITE)
    mast = scaled(mast, (W - 60) / tw)
    return bg, person, mast

def end_card(t):
    bg, person, mast = cover_parts()
    img = bg.copy()
    p = prog(t, BODY, 7 / FPS)
    my = -360 + (140 + 360) * back(p, 1.4)
    img.alpha_composite(mast, (30, int(my)))
    img.alpha_composite(person, (0, 140))
    d = ImageDraw.Draw(img)
    a = prog(t, BODY + 0.2, 6 / FPS)
    d.text((600, 44), "BR. 01  ·  JIU-JITSU TALKS", font=font("SemiBold", 26, False), fill=(255, 255, 255, int(220 * a)))
    bar = prog(t, BODY + 0.28, 8 / FPS)
    if bar > 0: d.rectangle([36, 1120, 60, 1120 + int(284 * eo(bar))], fill=RED)
    for txt, f, xy, t0 in [("SPORT", font("Black", 88), (84, 1108), BODY + 0.30), ("vs. REALNOST", font("Black", 68), (84, 1204), BODY + 0.45)]:
        q = prog(t, t0, 5 / FPS)
        if q <= 0: continue
        L = Image.new("RGBA", (700, 120), (0, 0, 0, 0)); ImageDraw.Draw(L).text((0, 0), txt, font=f, fill=WHITE)
        img.alpha_composite(fade(L, q), (int(xy[0] - 40 * (1 - eo(q))), xy[1]))
    ul = prog(t, BODY + 0.55, 6 / FPS)
    if ul > 0: d.rectangle([84, 1292, 84 + int(496 * eo(ul)), 1300], fill=RED)
    line = "Znati tehniku znači razumeti i kada…"
    n = int(len(line) * prog(t, BODY + 0.6, 0.45))
    if n:
        s = line[:n]
        d.text((84, 1320), s[:28], font=font("Medium", 34, False), fill=WHITE)
        if n > 28: d.text((84, 1364), s[28:], font=font("Medium", 34, False), fill=WHITE)
    bc = prog(t, BODY + 0.8, 6 / FPS)
    if bc > 0:
        r = random.Random(2)
        for k in range(28):
            w = r.choice([2, 4, 6]); d.rectangle([48 + k * 8, 1700, 48 + k * 8 + w, 1800], fill=(255, 255, 255, int(255 * bc)))
    pp = prog(t, BODY + 1.0, 8 / FPS)
    if pp > 0:
        pill = Image.new("RGBA", (430, 104), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([0, 0, 429, 103], radius=52, fill=WHITE)
        pd.text((44, 24), "NASTAVAK  →", font=font("Black", 46), fill=INK)
        put_center(img, pill, 815, 1732, 0.6 + 0.4 * back(pp, 2.0), clamp(pp * 3))
    img = zoom(img, 1 + 0.035 * prog(t, BODY, 2.0), 0.5, 0.5)
    fl = 1 - prog(t, BODY, 4 / FPS)
    if fl > 0: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * fl))))
    return img

# ------------------------------------------------------------ dispatcher
def render(fi):
    t = fi / FPS
    if t < 1.62: img = s1(t)
    elif t < 2.82: img = s2(t)
    elif t < 5.25: img = s3(t)
    elif t < 6.09: img = s4(t)
    elif t < 8.07: img = glass(s5(t), t)
    elif t < 9.05: img = glass(base(src_of(t)), t)
    elif t < 11.30: img = s7(t)
    elif t < 15.25: img = s8(t)
    elif t < BODY: img = s9(t)
    else: img = end_card(t)
    if t < BODY:
        y = 1320
        if 6.09 <= t < 8.07: y = 1560
        if 8.07 <= t < 9.05: y = 1720
        captions(img, t, y)
    return img.convert("RGB")

def job(fi):
    out = f"{WD}/frames/{fi:04d}.png"
    render(fi).save(out, compress_level=1)
    return fi

if __name__ == "__main__":
    os.makedirs(f"{WD}/frames", exist_ok=True)
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
    frames = list(range(a, b))
    with Pool(4) as pool:
        for k, fi in enumerate(pool.imap_unordered(job, frames, chunksize=4)):
            if k % 50 == 0: print("frame", k, "/", len(frames), flush=True)
    print("done", len(frames))
