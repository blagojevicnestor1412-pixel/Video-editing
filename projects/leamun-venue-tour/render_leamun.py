"""LEAMUN venue-tour reel renderer (3D motion graphics). Reuses helpers from the skill's reference render.py.
Usage: python3 -I render_leamun.py <ref_render.py> <workdir> [first last | test t1,t2,...]"""
import sys
REF = sys.argv.pop(1)
exec(open(REF).read().rsplit('if __name__ == "__main__":', 1)[0])

BODY = 65.65                 # spliced reel length (s)
END = 2.5                    # added end card
TOTAL = BODY + END
NFRAMES = round(TOTAL * FPS)
NBASE = len(glob.glob(f"{WD}/base/*.jpg"))
NAVY = (22, 36, 92); NAVY2 = (12, 20, 56); GOLD = (232, 184, 74); GOLD_D = (150, 108, 30); RED2 = (214, 40, 40)

@lru_cache(maxsize=32)
def base_idx(i):
    i = max(0, min(NBASE - 1, i))
    return Image.open(f"{WD}/base/{i+1:04d}.jpg").convert("RGBA")
def plate(t):
    k = round(t * FPS); img = base_idx(k).copy()
    if 40 <= k <= 90:          # hide the "screen recording not available" toast at the bottom edge
        z = 1.04 if t < 2.5 else 1.04 - 0.04 * eio(clamp((t - 2.5) / 0.4))
        img = zoom(img, z, 0.5, 0.45)
    return img

# ------------------------------------------------------------ 3D helpers
def _coeffs(dst, src):
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def warp(layer, quad):
    """Map layer corners (TL,TR,BR,BL) onto quad (output coords). Returns (image, (x0,y0))."""
    xs = [p[0] for p in quad]; ys = [p[1] for p in quad]
    x0, y0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
    x1, y1 = int(math.ceil(max(xs))), int(math.ceil(max(ys)))
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    dst = [(px - x0, py - y0) for px, py in quad]
    src = [(0, 0), (layer.width, 0), (layer.width, layer.height), (0, layer.height)]
    im = layer.transform((w, h), Image.PERSPECTIVE, _coeffs(dst, src), Image.BICUBIC)
    return im, (x0, y0)

def rot3(p, rx, ry, rz):
    x, y, z = p
    if rz: c, s = math.cos(rz), math.sin(rz); x, y = x * c - y * s, x * s + y * c
    if rx: c, s = math.cos(rx), math.sin(rx); y, z = y * c - z * s, y * s + z * c
    if ry: c, s = math.cos(ry), math.sin(ry); x, z = x * c + z * s, -x * s + z * c
    return x, y, z

def proj(p, cx, cy, f=1700):
    x, y, z = p; k = f / (f + z)
    return cx + x * k, cy + y * k

def place3d(img, layer, cx, cy, rx=0.0, ry=0.0, rz=0.0, s=1.0, a=1.0, z=0.0, shadow=True, f=1700):
    """Rotate a flat layer in 3D about its centre (degrees) and composite it at (cx,cy)."""
    if a <= 0.01 or s <= 0.01: return
    w, h = layer.width * s / 2, layer.height * s / 2
    rr = [math.radians(v) for v in (rx, ry, rz)]
    pts = [rot3(p, *rr) for p in [(-w, -h, 0), (w, -h, 0), (w, h, 0), (-w, h, 0)]]
    pts = [(x, y, zz + z) for x, y, zz in pts]
    quad = [proj(p, cx, cy, f) for p in pts]
    L = fade(layer, a)
    im, (x0, y0) = warp(L, quad)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[-1].point(lambda v: v * 120 // 255))
        sh = sh.resize((max(1, sh.width // 4), max(1, sh.height // 4))).filter(ImageFilter.GaussianBlur(5)).resize(im.size)
        _paste_clip(img, sh, x0 + 6, y0 + 22)
    _paste_clip(img, im, x0, y0)

def _paste_clip(img, im, x, y):
    if x >= img.width or y >= img.height or x + im.width <= 0 or y + im.height <= 0: return
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, img.width - x), min(im.height, img.height - y)
    img.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))

def facing(quad):
    (x0, y0), (x1, y1), (x2, y2) = quad[:3]
    return (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) > 0

def cube_roll(img, face_a, face_b, ang, cx, cy, f=1700):
    """Roll a cube about X: face_a (front) goes up/away, face_b (top) comes to the front. ang 0..90."""
    w, h = face_a.width / 2, face_a.height / 2; d = h
    a = math.radians(ang)
    FA = [(-w, -h, -d), (w, -h, -d), (w, h, -d), (-w, h, -d)]
    FB = [(-w, -h, d), (w, -h, d), (w, -h, -d), (-w, -h, -d)]
    faces = []
    for lay, P in ((face_a, FA), (face_b, FB)):
        R = [rot3(p, a, 0, 0) for p in P]
        R = [(x, y, zz + d) for x, y, zz in R]
        q = [proj(p, cx, cy, f) for p in R]
        if facing(q): faces.append((sum(p[2] for p in R), lay, q))
    for _, lay, q in sorted(faces, key=lambda t: -t[0]):
        shade = 1.0
        im, (x0, y0) = warp(lay, q)
        _paste_clip(img, im, x0, y0)

@lru_cache(maxsize=32)
def ext_text(txt, size, face=GOLD, side=GOLD_D, depth=12, weight="Black", stroke=0):
    """Extruded 3D lettering (stacked offset copies + lit face)."""
    f = font(weight, size)
    tw = int(f.getlength(txt)); hh = int(size * 1.3)
    L = Image.new("RGBA", (tw + depth + 40, hh + depth + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for k in range(depth, 0, -1):
        t_ = k / depth
        col = tuple(int(c * (0.55 + 0.25 * (1 - t_))) for c in side)
        d.text((20 + k, 6 + k), txt, font=f, fill=col + (255,))
    d.text((20, 6), txt, font=f, fill=face + (255,))
    # top-light gradient on the face
    g = Image.new("L", L.size, 0); gd = ImageDraw.Draw(g)
    for yy in range(L.height): gd.line([(0, yy), (L.width, yy)], fill=int(70 * max(0, 1 - yy / (hh * 0.6))))
    face_mask = Image.new("L", L.size, 0); ImageDraw.Draw(face_mask).text((20, 6), txt, font=f, fill=255)
    hl = Image.new("RGBA", L.size, (255, 255, 255, 0)); hl.putalpha(ImageChops.multiply(g, face_mask))
    L.alpha_composite(hl)
    return L

def rrect(w, h, r, fill, outline=None, width=0):
    L = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(L).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], radius=r, fill=fill, outline=outline, width=width)
    return L

def env_in_out(t, t0, t1, din=10, dout=8):
    p = prog(t, t0, din / FPS); q = prog(t, t1, dout / FPS)
    return p, q

# ------------------------------------------------------------ 0. intro: plate inside a 3D card
INTRO_END, EXP_END = 1.40, 1.80
CARD_W = 880
CROP_H = 1528                      # plate rows shown in the card (Instagram UI lives below)
@lru_cache(maxsize=1)
def intro_bg():
    bg = Image.new("RGBA", (W, H), NAVY2 + (255,)); d = ImageDraw.Draw(bg)
    for yy in range(H):
        u = yy / H; c = tuple(int(NAVY2[i] * (1 - u) + NAVY[i] * u * 0.9) for i in range(3))
        d.line([(0, yy), (W, yy)], fill=c + (255,))
    # perspective floor grid
    hor = 1180; vx = W / 2
    for k in range(-12, 13):
        d.line([(vx, hor), (vx + k * 260, H + 200)], fill=(80, 110, 200, 70), width=2)
    for k in range(1, 16):
        yy = hor + (H - hor) * (k / 15) ** 2.2
        d.line([(0, yy), (W, yy)], fill=(80, 110, 200, 60), width=2)
    return bg

def card_layer(t):
    pl = plate(t).crop((0, 0, W, CROP_H))
    s = CARD_W / W
    pl = pl.resize((CARD_W, int(CROP_H * s)), Image.BICUBIC)
    m = Image.new("L", pl.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, pl.width - 1, pl.height - 1], radius=40, fill=255)
    out = Image.new("RGBA", pl.size, (0, 0, 0, 0)); out.paste(pl, (0, 0), m)
    ImageDraw.Draw(out).rounded_rectangle([0, 0, pl.width - 1, pl.height - 1], radius=40, outline=GOLD + (255,), width=5)
    return out

def intro(t):
    if t >= INTRO_END:
        # expand: window grows from the card rect to full frame while the plate scale goes to 1
        p = eio(prog(t, INTRO_END, EXP_END - INTRO_END))
        img = intro_bg().copy()
        s0 = CARD_W / W; sc = s0 + (1 - s0) * p
        cw0, ch0 = CARD_W, CROP_H * s0
        cx0, cy0 = W / 2, 980
        pl = plate(t)
        pw, ph = int(W * sc), int(H * sc)
        pls = pl.resize((pw, ph), Image.BICUBIC)
        left = (cx0 - cw0 / 2) * (1 - p); top = (cy0 - ch0 / 2) * (1 - p)
        win_w = cw0 + (W - cw0) * p; win_h = ch0 + (H - ch0) * p
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle([left, top, left + win_w, top + win_h], radius=int(40 * (1 - p)), fill=255)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lay.paste(pls, (int(left), int(top)))
        img.paste(lay, (0, 0), m)
        if p < 1:
            ImageDraw.Draw(img).rounded_rectangle([left, top, left + win_w, top + win_h], radius=int(40 * (1 - p)), outline=GOLD + (int(255 * (1 - p)),), width=5)
        intro_text(img, t, 1 - p)
        return img
    img = intro_bg().copy()
    p = eo(prog(t, 0, 0.9))
    ry = -26 * (1 - p) + 2 * math.sin(t * 2.2) * (1 - p)
    rx = 10 * (1 - p)
    place3d(img, card_layer(t), W / 2, 980, rx=rx, ry=ry, s=0.86 + 0.14 * eo(prog(t, 0, 0.6)), a=clamp(t * FPS / 3 + 0.4))
    intro_text(img, t, 1.0)
    return img

def intro_text(img, t, a):
    if a <= 0: return
    p = eo(prog(t, 0.05, 0.5))
    T = ext_text("LEAMUN 2026", 112, depth=14)
    place3d(img, T, W / 2, 150 - 40 * (1 - p), rx=-18 * (1 - p), ry=0, s=0.9 + 0.1 * p, a=p * a)
    q = eo(prog(t, 0.25, 0.4))
    sub = Image.new("RGBA", (600, 50), (0, 0, 0, 0))
    ImageDraw.Draw(sub).text((300, 25), "V E N U E   T O U R", font=font("Bold", 34, False), fill=(255, 255, 255, 230), anchor="mm")
    put_center(img, sub, W / 2, 260, 1, q * a)
    # name tag (from the creator's own lower third)
    r = prog(t, 0.35, 12 / FPS)
    if r > 0:
        tag = Image.new("RGBA", (640, 132), (0, 0, 0, 0)); d = ImageDraw.Draw(tag)
        d.rounded_rectangle([0, 0, 639, 131], radius=26, fill=(255, 255, 255, 245))
        d.rounded_rectangle([0, 0, 18, 131], radius=8, fill=GOLD + (255,))
        d.text((44, 22), "ALEKSA POPOVIĆ", font=font("Black", 48), fill=NAVY)
        d.text((46, 82), "Secretary General", font=font("SemiBold", 30, False), fill=(90, 96, 120))
        place3d(img, tag, W / 2, 1790, rx=80 * (1 - eo(r)), s=1.0, a=clamp(r * 2) * a)

# ------------------------------------------------------------ itinerary panel (3.0 – 5.1)
ITIN = [("01", "VENUE", 3.05), ("02", "REGISTRATION", 3.35), ("03", "COMMITTEES", 3.65), ("04", "BREAK", 3.95)]
@lru_cache(maxsize=8)
def itin_tile(n, lab):
    f = font("Black", 34)
    w = max(220, int(f.getlength(lab) + 40)); h = 120
    L = rrect(w, h, 24, NAVY + (240,), outline=GOLD + (220,), width=3); d = ImageDraw.Draw(L)
    d.text((w / 2, 36), n, font=font("Black", 30), fill=GOLD, anchor="mm")
    d.text((w / 2, 82), lab, font=f, fill=WHITE, anchor="mm")
    return L

def itinerary(img, t, t0=3.0, t1=5.05):
    if t < t0 or t >= t1 + 12 / FPS: return img
    tiles = [itin_tile(n, lab) for n, lab, _ in ITIN]
    gap = 16; tot = sum(x.width for x in tiles) + gap * 3
    x = W / 2 - tot / 2
    lab_p, lab_q = env_in_out(t, t0, t1, 10, 8)
    if lab_p > 0 and lab_q < 1:
        hd = Image.new("RGBA", (600, 50), (0, 0, 0, 0)); hdd = ImageDraw.Draw(hd)
        hdd.text((302, 27), "A DAY AT LEAMUN", font=font("Black", 36), fill=(0, 0, 0, 150), anchor="mm")
        hdd.text((300, 25), "A DAY AT LEAMUN", font=font("Black", 36), fill=GOLD, anchor="mm")
        put_center(img, hd, W / 2, 1660, 1, lab_p * (1 - lab_q))
    for k, ((n, lab, tk), tile) in enumerate(zip(ITIN, tiles)):
        cx = x + tile.width / 2; x += tile.width + gap
        p, q = env_in_out(t, tk, t1 + k * 2 / FPS, 10, 6)
        if p <= 0 or q >= 1: continue
        place3d(img, tile, cx, 1770 + 40 * ei(q), rx=28 + 62 * (1 - eo(p)), s=0.95, a=clamp(p * 2) * (1 - q))
    return img

# ------------------------------------------------------------ 3D location pin (7.5 – 10.3)
@lru_cache(maxsize=1)
def pin_img():
    S = 220
    L = Image.new("RGBA", (S, int(S * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    cx, cy, r = S / 2, S / 2, S * 0.42
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED2 + (255,))
    d.polygon([(cx - r * 0.72, cy + r * 0.55), (cx + r * 0.72, cy + r * 0.55), (cx, S * 1.32)], fill=RED2 + (255,))
    d.ellipse([cx - r * 0.42, cy - r * 0.42, cx + r * 0.42, cy + r * 0.42], fill=(255, 255, 255, 255))
    hl = Image.new("RGBA", L.size, (0, 0, 0, 0)); ImageDraw.Draw(hl).ellipse([cx - r * 0.7, cy - r * 0.85, cx - r * 0.1, cy - r * 0.35], fill=(255, 255, 255, 90))
    L.alpha_composite(hl.filter(ImageFilter.GaussianBlur(6)))
    return L

def location(img, t, t0=7.55, t1=10.25):
    p, q = env_in_out(t, t0, t1, 14, 8)
    if p <= 0 or q >= 1: return img
    a = 1 - q
    card = rrect(700, 170, 40, (255, 255, 255, 246)); d = ImageDraw.Draw(card)
    d.text((176, 30), "TERAZIJE 23", font=font("Black", 66), fill=NAVY)
    d.text((178, 108), "Belgrade · International School", font=font("SemiBold", 30, False), fill=(90, 96, 120))
    cr = eo(prog(t, t0 + 0.2, 10 / FPS))
    place3d(img, card, W / 2 + 30, 200 - 40 * ei(q), rx=0, ry=-70 * (1 - cr), s=1.0, a=clamp(cr * 2) * a)
    # pin drops onto the card's left end with a bounce and spins in Y
    dp = prog(t, t0, 14 / FPS)
    yb = -300 * (1 - dp) ** 2 if dp < 1 else -16 * abs(math.sin((t - t0 - 14 / FPS) * 9)) * math.exp(-(t - t0 - 14 / FPS) * 4)
    spin = 360 * (1 - eo(dp)) + 18 * math.sin(t * 3)
    place3d(img, pin_img(), 250, 150 + yb - 40 * ei(q), ry=spin, s=0.62, a=clamp(dp * 3) * a)
    return img

# ------------------------------------------------------------ floor counter cube (11.0 – 15.4)
@lru_cache(maxsize=8)
def floor_face(n):
    L = rrect(220, 220, 34, NAVY + (250,), outline=GOLD + (255,), width=5); d = ImageDraw.Draw(L)
    d.text((110, 52), "FLOOR", font=font("Bold", 30, False), fill=GOLD, anchor="mm")
    d.text((110, 135), str(n), font=font("Black", 128), fill=WHITE, anchor="mm")
    return L

FLIPS = [(14.05, 0, 1), (14.85, 1, 2)]
def floor_counter(img, t, t0=11.0, t1=15.35):
    p, q = env_in_out(t, t0, t1, 12, 8)
    if p <= 0 or q >= 1: return img
    cx, cy = 190, 250 - 40 * ei(q)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cur = 0; done = False
    for tf, a_, b_ in FLIPS:
        r = prog(t, tf, 10 / FPS)
        if 0 < r < 1:
            cube_roll(lay, floor_face(a_), floor_face(b_), 90 * eio(r), cx, cy); done = True; break
        if r >= 1: cur = b_
    if not done:
        place3d(lay, floor_face(cur), cx, cy, rx=-14 * (1 - eo(p)), ry=40 * (1 - eo(p)), s=0.6 + 0.4 * back(p, 2.0), shadow=False)
    img.alpha_composite(fade(lay, clamp(p * 2) * (1 - q)))
    # small arrow pointing up next to the cube
    if p > 0.5:
        ar = Image.new("RGBA", (70, 90), (0, 0, 0, 0)); ad = ImageDraw.Draw(ar)
        ad.polygon([(35, 0), (70, 40), (48, 40), (48, 90), (22, 90), (22, 40), (0, 40)], fill=GOLD + (255,))
        bob = 8 * math.sin(t * 8)
        put_center(img, ar, cx + 150, cy - 10 + bob, 1, clamp(p * 2) * (1 - q))
    return img

# ------------------------------------------------------------ registration chips + 3D accreditation badge
@lru_cache(maxsize=8)
def check_chip(txt):
    f = font("Black", 46)
    w = int(f.getlength(txt) + 150); h = 96
    c = rrect(w, h, 48, (255, 255, 255, 246)); d = ImageDraw.Draw(c)
    d.ellipse([16, 14, 84, 82], fill=(40, 170, 90))
    d.line([(32, 49), (45, 62), (68, 36)], fill=WHITE, width=9, joint="curve")
    d.text((104, h / 2 + 2), txt, font=f, fill=NAVY, anchor="lm")
    return c

def reg_chips(img, t, items=(("REGISTRATION", 16.10), ("PAYMENT", 16.75)), t1=20.0):
    for k, (txt, tk) in enumerate(items):
        p, q = env_in_out(t, tk, t1 + k * 2 / FPS, 8, 6)
        if p <= 0 or q >= 1: continue
        c = check_chip(txt)
        place3d(img, c, 60 + c.width / 2, 1610 + k * 116 - 30 * ei(q), ry=-80 * (1 - eo(p)), s=0.95, a=clamp(p * 2) * (1 - q))
    return img

@lru_cache(maxsize=2)
def badge_faces():
    w, h = 300, 420
    fr = rrect(w, h, 28, (255, 255, 255, 255)); d = ImageDraw.Draw(fr)
    d.rounded_rectangle([0, 0, w - 1, 120], radius=28, fill=NAVY + (255,)); d.rectangle([0, 90, w - 1, 120], fill=NAVY + (255,))
    d.rounded_rectangle([w / 2 - 34, 18, w / 2 + 34, 34], radius=8, fill=(255, 255, 255, 255))
    d.text((w / 2, 76), "LEAMUN 2026", font=font("Black", 40), fill=GOLD, anchor="mm")
    d.ellipse([w / 2 - 62, 140, w / 2 + 62, 264], fill=(220, 224, 236))
    d.ellipse([w / 2 - 26, 160, w / 2 + 26, 212], fill=(170, 176, 196)); d.pieslice([w / 2 - 50, 212, w / 2 + 50, 300], 180, 360, fill=(170, 176, 196))
    d.text((w / 2, 300), "DELEGATE", font=font("Black", 46), fill=NAVY, anchor="mm")
    d.rounded_rectangle([40, 340, w - 40, 386], radius=23, fill=GOLD + (255,))
    d.text((w / 2, 364), "ACCREDITED", font=font("Black", 26), fill=NAVY, anchor="mm")
    bk = rrect(w, h, 28, NAVY + (255,)); bd = ImageDraw.Draw(bk)
    bd.text((w / 2, h / 2), "L", font=font("Black", 200), fill=GOLD, anchor="mm")
    return fr, bk

def badge(img, t, t0=18.25, t1=20.0):
    p, q = env_in_out(t, t0, t1, 18, 8)
    if p <= 0 or q >= 1: return img
    fr, bk = badge_faces()
    ry = 540 * (1 - eo(p)) + 10 * math.sin(t * 2.5)
    side = fr if math.cos(math.radians(ry)) >= 0 else bk.transpose(Image.FLIP_LEFT_RIGHT)
    cx, cy = 840, 700 - 30 * ei(q)
    # lanyard
    if p > 0.3:
        ln = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(ln)
        ld.line([(cx - 60, 0), (cx - 8, cy - 210)], fill=NAVY + (230,), width=14)
        ld.line([(cx + 60, 0), (cx + 8, cy - 210)], fill=NAVY + (230,), width=14)
        img.alpha_composite(fade(ln, clamp((p - 0.3) * 3) * (1 - q)))
    place3d(img, side, cx, cy, ry=ry, rx=6, s=0.9 + 0.1 * back(p, 1.6), a=clamp(p * 3) * (1 - q))
    return img

# ------------------------------------------------------------ "Now, quick!" snap + debate timer
SNAP = 21.0
def snap_zoom(img, t):
    if not (SNAP <= t < 21.75): return img
    pz = prog(t, SNAP, 3 / FPS); back_ = eio(prog(t, 21.45, 0.3))
    s = (1 + 0.12 * eo(pz)) * 1 + 0 * back_
    s = 1 + (s - 1) * (1 - back_)
    out = zoom(img, s, 0.5, 0.45)
    blur = 0.06 * (1 - abs(2 * pz - 1)) if 0 < pz < 1 else 0
    out = zoom_blur(out, blur, 0.5, 0.45)
    sl = 1 - prog(t, SNAP, 10 / FPS)
    if sl > 0: out.alpha_composite(fade(speed_lines(), sl * 0.7))
    return out

def timer_panel(t, label, secs_txt, ring, warn=False):
    w, h = 640, 190
    P = rrect(w, h, 40, (12, 16, 36, 235), outline=(RED2 if warn else GOLD) + (220,), width=4); d = ImageDraw.Draw(P)
    cx, cy, r = 100, h / 2, 62
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 60), width=12)
    d.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=-90 + 360 * ring, fill=(RED2 if warn else GOLD) + (255,), width=12)
    d.line([(cx, cy), (cx, cy - 36)], fill=WHITE, width=6); d.line([(cx, cy), (cx + 26, cy + 8)], fill=WHITE, width=6)
    d.text((196, 46), label, font=font("Bold", 32, False), fill=(255, 255, 255, 220))
    d.text((194, 84), secs_txt, font=font("Black", 78), fill=(RED2 if warn else WHITE))
    return P

def debate_timer(img, t, t0=21.75, t1=23.95):
    p, q = env_in_out(t, t0, t1, 12, 8)
    if p <= 0 or q >= 1: return img
    rem = max(0, 10 - (t - t0) * 2.2)
    P = timer_panel(t, "DEBATE STARTS IN", f"00:{int(math.ceil(rem)):02d}", rem / 10)
    place3d(img, P, W / 2, 250 - 30 * ei(q), rx=-60 * (1 - eo(p)) + 8, s=1.0, a=clamp(p * 2) * (1 - q))
    return img

def session_end(img, t, t0=38.5, t1=39.95):
    p, q = env_in_out(t, t0, t1, 12, 8)
    if p <= 0 or q >= 1: return img
    P = timer_panel(t, "COMMITTEE SESSION", "00:00", 1.0, warn=True)
    sh = 6 * math.sin(t * 70) * (1 - prog(t, t0 + 0.3, 0.35)) if t > t0 + 0.3 else 0
    place3d(img, P, W / 2 + sh, 250 - 30 * ei(q), rx=-60 * (1 - eo(p)) + 8, a=clamp(p * 2) * (1 - q))
    return img

# ------------------------------------------------------------ France placard + OUT OF ORDER stamp
@lru_cache(maxsize=1)
def placard():
    w, h = 460, 250
    L = rrect(w, h, 18, (255, 255, 255, 255)); d = ImageDraw.Draw(L)
    fx0, fy0 = 40, 40
    for k, col in enumerate([(0, 85, 164), (255, 255, 255), (239, 65, 53)]):
        d.rectangle([fx0 + k * 50, fy0, fx0 + (k + 1) * 50, fy0 + 100], fill=col + (255,))
    d.rectangle([fx0, fy0, fx0 + 150, fy0 + 100], outline=(200, 200, 200), width=2)
    d.text((216, 90), "FRANCE", font=font("Black", 62), fill=NAVY, anchor="lm")
    d.text((w / 2, 196), "DELEGATION", font=font("Bold", 32, False), fill=(120, 126, 150), anchor="mm")
    return L

def france(img, t, t0=32.3, t1=34.05):
    p, q = env_in_out(t, t0, t1, 14, 8)
    if p <= 0 or q >= 1: return img
    rx = 88 * (1 - eo(p)) - 6
    place3d(img, placard(), 780, 300 - 30 * ei(q), rx=rx, ry=-14, rz=4, s=0.95, a=clamp(p * 3) * (1 - q))
    return img

@lru_cache(maxsize=1)
def stamp_img():
    f = font("Black", 92)
    tw = int(f.getlength("OUT OF ORDER"))
    L = Image.new("RGBA", (tw + 80, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([6, 6, L.width - 7, L.height - 7], radius=20, outline=RED2 + (255,), width=10)
    d.text((L.width / 2, L.height / 2 + 4), "OUT OF ORDER", font=f, fill=RED2 + (255,), anchor="mm")
    rng = np.random.default_rng(2)
    a = np.asarray(L).copy(); holes = rng.random(a.shape[:2]) < 0.06
    a[..., 3] = np.where(holes, (a[..., 3] * 0.35).astype(np.uint8), a[..., 3])
    return Image.fromarray(a).rotate(8, expand=True, resample=Image.BICUBIC)

def out_of_order(img, t, t0=35.3, t1=36.65):
    p, q = env_in_out(t, t0, t1, 5, 8)
    if p <= 0 or q >= 1: return img
    s = 1.8 - 0.8 * eo(p)
    place3d(img, stamp_img(), W / 2, 300, rx=30 * (1 - eo(p)), s=s * 0.92, a=clamp(p * 2) * (1 - q), shadow=False)
    return img

# ------------------------------------------------------------ chips (break, food/drinks, OVS)
@lru_cache(maxsize=16)
def chip3(txt, em, bg, fg):
    f = font("Black", 52)
    e = emoji(em, 64) if em else None
    w = int(f.getlength(txt) + 70 + (86 if e else 0)); h = 104
    c = rrect(w, h, 52, bg + (248,)); d = ImageDraw.Draw(c)
    x = 34
    if e: c.alpha_composite(e, (x - 4, (h - e.height) // 2)); x += 86
    d.text((x, h / 2 + 2), txt, font=f, fill=fg, anchor="lm")
    return c

def chips_row(img, t, items, t_out, y):
    cs = [chip3(*it[1:]) for it in items]
    gap = 26; tot = sum(c.width for c in cs) + gap * (len(cs) - 1); x = W / 2 - tot / 2
    for k, (it, c) in enumerate(zip(items, cs)):
        cx = x + c.width / 2; x += c.width + gap
        p, q = env_in_out(t, it[0], t_out + k * 2 / FPS, 10, 6)
        if p <= 0 or q >= 1: continue
        place3d(img, c, cx, y - 30 * ei(q), rx=-75 * (1 - eo(p)), s=0.7 + 0.3 * back(p, 2.2), a=clamp(p * 2) * (1 - q))
    return img

# ------------------------------------------------------------ Belgrade street sign (56.5 – 58.6)
@lru_cache(maxsize=1)
def street_sign():
    w, h = 560, 200
    L = rrect(w, h, 16, (18, 64, 150, 255)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([10, 10, w - 11, h - 11], radius=10, outline=(255, 255, 255, 255), width=5)
    d.text((w / 2, 72), "ТЕРАЗИЈЕ", font=font("Black", 74), fill=WHITE, anchor="mm")
    d.text((w / 2, 148), "TERAZIJE", font=font("Bold", 52, False), fill=WHITE, anchor="mm")
    return L

def street(img, t, t0=56.5, t1=58.55):
    p, q = env_in_out(t, t0, t1, 14, 8)
    if p <= 0 or q >= 1: return img
    tt = t - t0
    swing = 70 * math.exp(-tt * 3.2) * math.cos(tt * 9)
    place3d(img, street_sign(), W / 2, 260 - 30 * ei(q), ry=swing, rx=-6, s=0.6 + 0.4 * back(p, 1.8), a=clamp(p * 2) * (1 - q))
    return img

# ------------------------------------------------------------ map pin pulse (58.8 – 60.6)
MAP_TRACK = [(58.85, 640, 785), (59.5, 670, 760), (60.3, 652, 775), (60.6, 652, 775)]
def map_pulse(img, t, t0=58.85, t1=60.55):
    if not (t0 <= t < t1): return img
    for (ta, xa, ya), (tb, xb, yb) in zip(MAP_TRACK, MAP_TRACK[1:]):
        if ta <= t <= tb: u = (t - ta) / (tb - ta); MAP_PIN = (xa + (xb - xa) * u, ya + (yb - ya) * u); break
    else: MAP_PIN = MAP_TRACK[-1][1:]
    a = prog(t, t0, 6 / FPS) * (1 - prog(t, t1 - 6 / FPS, 6 / FPS))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for k in range(3):
        ph = ((t - t0) * 1.2 + k / 3) % 1
        r = 30 + 130 * ph
        d.ellipse([MAP_PIN[0] - r, MAP_PIN[1] - r, MAP_PIN[0] + r, MAP_PIN[1] + r], outline=(214, 40, 40, int(220 * (1 - ph) * a)), width=8)
    img.alpha_composite(L)
    lab = chip3("LEAMUN VENUE", None, NAVY, WHITE)
    place3d(img, lab, MAP_PIN[0], MAP_PIN[1] - 190, rx=-70 * (1 - eo(prog(t, t0 + 0.15, 10 / FPS))), s=0.8, a=clamp(prog(t, t0 + 0.15, 10 / FPS) * 2) * a)
    return img

# ------------------------------------------------------------ calendar (64.0 – 65.65) and end card
@lru_cache(maxsize=1)
def calendar():
    w, h = 300, 300
    L = rrect(w, h, 34, (255, 255, 255, 255)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([0, 0, w - 1, 96], radius=34, fill=RED2 + (255,)); d.rectangle([0, 60, w - 1, 96], fill=RED2 + (255,))
    d.text((w / 2, 50), "NOVEMBER", font=font("Black", 44), fill=WHITE, anchor="mm")
    d.text((w / 2, 190), "20–22", font=font("Black", 92), fill=NAVY, anchor="mm")
    for k in range(2): d.ellipse([70 + k * 140, -14, 92 + k * 140, 8], fill=(60, 60, 70))
    return L

def cal(img, t, t0=64.0):
    p = prog(t, t0, 14 / FPS)
    if p <= 0 or t >= BODY: return img
    place3d(img, calendar(), 250, 270, rx=85 * (1 - eo(p)), ry=14, rz=4, s=0.8, a=clamp(p * 2))
    return img

@lru_cache(maxsize=1)
def end_bg():
    last = base_idx(NBASE - 1).convert("RGB")
    bg = last.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BICUBIC)
    bg = ImageEnhance.Brightness(bg).enhance(0.35).convert("RGBA")
    tint = Image.new("RGBA", (W, H), NAVY2 + (130,)); bg.alpha_composite(tint)
    return bg

def end_card(t):
    tt = t - BODY
    img = end_bg().copy()
    p = eo(prog(tt, 0, 0.5))
    T = ext_text("LEAMUN", 190, depth=20)
    place3d(img, T, W / 2, 640, rx=-30 * (1 - p) + 4 * math.sin(tt * 1.6), ry=12 * math.sin(tt * 1.1), s=0.7 + 0.3 * back(prog(tt, 0, 0.5), 1.6), a=clamp(p * 2))
    T2 = ext_text("2026", 150, face=WHITE, side=(150, 160, 200), depth=16)
    q = prog(tt, 0.18, 0.45)
    place3d(img, T2, W / 2, 850, rx=-30 * (1 - eo(q)) + 4 * math.sin(tt * 1.6 + 0.4), ry=12 * math.sin(tt * 1.1 + 0.3), s=0.7 + 0.3 * back(q, 1.6), a=clamp(q * 2))
    r = prog(tt, 0.45, 12 / FPS)
    info = Image.new("RGBA", (900, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(info)
    d.text((450, 34), "NOVEMBER 20–22", font=font("Black", 60), fill=GOLD, anchor="mm")
    d.text((450, 96), "Terazije 23 · Belgrade", font=font("SemiBold", 38, False), fill=(230, 232, 245), anchor="mm")
    put_center(img, info, W / 2, 1050 + 30 * (1 - eo(r)), 1, eo(r))
    c = prog(tt, 0.8, 12 / FPS)
    if c > 0:
        pulse = 1 + 0.04 * math.sin(max(0, tt - 1.2) * 6)
        btn = rrect(640, 130, 65, GOLD + (255,)); bd = ImageDraw.Draw(btn)
        bd.text((320, 66), "APPLY · LINK IN BIO", font=font("Black", 54), fill=NAVY, anchor="mm")
        place3d(img, btn, W / 2, 1290, rx=-70 * (1 - eo(c)), s=(0.7 + 0.3 * back(c, 2.0)) * pulse, a=clamp(c * 2))
        lim = Image.new("RGBA", (600, 60), (0, 0, 0, 0))
        ImageDraw.Draw(lim).text((300, 30), "Spots are limited", font=font("Bold", 36, False), fill=(255, 255, 255, 210), anchor="mm")
        put_center(img, lim, W / 2, 1410, 1, clamp(c * 2))
    # gold sparkles
    rnd = random.Random(7)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for k in range(40):
        x = rnd.uniform(60, W - 60); y0 = rnd.uniform(300, 1700); sp = rnd.uniform(30, 90); ph = rnd.uniform(0, 6)
        y = y0 - sp * tt; a = 0.5 + 0.5 * math.sin(tt * 4 + ph)
        r_ = rnd.uniform(2, 5)
        d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=GOLD + (int(200 * a * p),))
    img.alpha_composite(L)
    # fade in from the reel, fade out at the very end
    fin = prog(tt, 0, 8 / FPS)
    if fin < 1:
        img = Image.blend(plate(BODY - 1 / FPS).convert("RGBA"), img, fin)
    fo = prog(tt, END - 0.3, 0.3)
    if fo > 0: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo))))
    return img

# ------------------------------------------------------------ cut settles, slow pushes
CUTS = [15.5, 54.0]
def settle(img, t):
    for c in CUTS:
        if c <= t < c + 8 / FPS:
            q = prog(t, c, 8 / FPS)
            return zoom_blur(zoom(img, 1.1 - 0.1 * eo(q), 0.5, 0.45), 0.06 * (1 - q), 0.5, 0.45)
    return img

def pushes(img, t):
    for a_, b_, amt in [(25.75, 28.5, 0.06), (45.0, 52.5, 0.05)]:
        if a_ <= t < b_: return zoom(img, 1 + amt * eio(prog(t, a_, b_ - a_)), 0.5, 0.45)
    return img

# ------------------------------------------------------------ frame assembly
def render(fi):
    t = fi / FPS
    if t >= BODY: return end_card(t).convert("RGB")
    if t < EXP_END:
        img = intro(t)
    else:
        img = plate(t)
        img = settle(img, t); img = pushes(img, t); img = snap_zoom(img, t)
    img = itinerary(img, t); img = location(img, t); img = floor_counter(img, t)
    img = reg_chips(img, t); img = badge(img, t); img = debate_timer(img, t)
    img = france(img, t); img = out_of_order(img, t); img = session_end(img, t)
    img = chips_row(img, t, [(40.30, "BREAK TIME", "☕", GOLD, NAVY)], 41.35, 1500)
    img = chips_row(img, t, [(42.40, "FOOD", "🍕", (255, 255, 255), NAVY), (42.90, "DRINKS", "🥤", (255, 255, 255), NAVY)], 44.45, 1500)
    img = street(img, t); img = map_pulse(img, t)
    img = chips_row(img, t, [(61.0, "LEAMUN IS RIGHT NEXT DOOR", "📍", NAVY, WHITE)], 63.35, 760)
    img = cal(img, t)
    return img.convert("RGB")

def job(fi):
    render(fi).save(f"{WD}/frames/{fi:04d}.png", compress_level=1)

if __name__ == "__main__":
    os.makedirs(f"{WD}/frames", exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[2] == "test":
        ts = [float(x) for x in sys.argv[3].split(",")]
        with Pool(4) as pool: ims = pool.map(render, [round(x * FPS) for x in ts])
        ims = [im.resize((270, 480)) for im in ims]
        cols = 8; rows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (270 * cols, 480 * rows))
        for k, (im, x) in enumerate(zip(ims, ts)):
            ImageDraw.Draw(im).text((6, 452), f"{x:.2f}", font=font("Bold", 22, False), fill=(255, 255, 0))
            sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(f"{WD}/test.png"); print("test sheet"); sys.exit()
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
    with Pool(4) as pool:
        for k, _ in enumerate(pool.imap_unordered(job, range(a, b), chunksize=4)):
            if k % 300 == 0: print("frame", k, "/", b - a, flush=True)
    print("done", b - a)
