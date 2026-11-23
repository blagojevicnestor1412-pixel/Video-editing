"""Astarta Black Friday reel renderer. Reuses helpers from the skill's reference render.py.
Usage: python3 -I render_astarta.py <ref_render.py> <workdir> [first last]"""
import sys, json
REF = sys.argv.pop(1)
exec(open(REF).read().rsplit('if __name__ == "__main__":', 1)[0])

AMB = (240, 176, 48)          # perfume amber, the one accent
DARK = (14, 14, 16)
TOTAL = 33.10
NFRAMES = round(TOTAL * FPS)
NBASE = len(glob.glob(f"{WD}/base/*.jpg"))
SEGS = [(0.0, TOTAL)]
MAP = [(0.0, TOTAL, 0.0)]
BODY = TOTAL

@lru_cache(maxsize=24)
def base_idx(i):
    i = max(0, min(NBASE - 1, i))
    return Image.open(f"{WD}/base/{i+1:04d}.jpg").convert("RGBA")

# ------------------------------------------------------------ captions (amber pill, ink keyword)
CAPS = [(s, tuple(txt.split()), kw) for s, txt, kw in json.load(open(f"{WD}/caps.json"))]
CAPS = [(s, tuple(w.replace("DOBIJATE", "DOBIJETE") for w in ws), (kw.replace("DOBIJATE", "DOBIJETE") if kw else None))
        for s, ws, kw in CAPS]
CAPS = [(s, ws if ws != ("U", "SVAKOJ", "PORUDŽBINI") else ("U", "SVAKU", "PORUDŽBINU"),
         kw if kw != "PORUDŽBINI" else "PORUDŽBINU") for s, ws, kw in CAPS]
HIDE = [(10.90, 14.12)]       # glass panel carries those words

@lru_cache(maxsize=64)
def cap_layer2(words, hi, size):
    f = font("Black", size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    sp = size * 0.28
    ws = [d0.textlength(w, font=f) for w in words]
    tw = sum(ws) + sp * (len(words) - 1)
    L = Image.new("RGBA", (int(tw + 80), int(size * 1.7)), (0, 0, 0, 0))
    shadow = Image.new("RGBA", L.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    x = 40; pills = []
    for w, wd in zip(words, ws):
        if w == hi: pills.append((x, wd))
        else: sd.text((x, size * 0.22 + 6), w, font=f, fill=(0, 0, 0, 220))
        x += wd + sp
    L.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    for x, wd in pills:
        p = Image.new("RGBA", (int(wd + 36), int(size * 1.24)), (0, 0, 0, 0))
        ImageDraw.Draw(p).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=int(size * 0.2), fill=AMB + (255,))
        p = p.rotate(-2, expand=True, resample=Image.BICUBIC)
        L.alpha_composite(p, (int(x - 18), int(size * 0.14)))
    d = ImageDraw.Draw(L); x = 40
    for w, wd in zip(words, ws):
        d.text((x, size * 0.22), w, font=f, fill=DARK if w == hi else WHITE); x += wd + sp
    return L

def captions2(img, t, y):
    if any(a <= t < b for a, b in HIDE): return
    for k, (st, words, hi) in enumerate(CAPS):
        nxt = CAPS[k + 1][0] if k + 1 < len(CAPS) else TOTAL
        end = min(nxt, st + 1.6)
        if st <= t < end:
            ts = t - st
            p = clamp(ts * FPS / 5)
            sc = 0.72 + 0.28 * back(p, 2.4) if p < 1 else 1.0
            L = cap_layer2(words, hi, 84)
            if L.width > W - 80: L = scaled(L, (W - 80) / L.width)
            put_center(img, L, W / 2, y, sc, clamp(ts * FPS / 2))
            return

# ------------------------------------------------------------ effects
SNAP = 5.42
def snap_zoom(t):
    img = base(t)
    p = prog(t, SNAP, 3 / FPS)
    s = 1 + 0.24 * eo(p)
    s = 1 + (s - 1) * (1 - eio(prog(t, 6.30, 0.30)))           # ease back before the box hits the lens
    blur = 0.07 * (1 - abs(2 * p - 1)) if 0 < p < 1 else 0
    out = zoom(img, s, 0.5, 0.34)
    out = zoom_blur(out, blur, 0.5, 0.34)
    sl = 1 - prog(t, SNAP, 10 / FPS)
    if t >= SNAP and sl > 0: out.alpha_composite(fade(speed_lines(), sl * 0.8))
    return out

GL_IN, GL_OUT = 10.90, 13.78
GL_ROWS = [("MIKROPARFEM", 10.98), ("PREMIUM DEKANT", 11.72), ("GURMANSKI SET", 12.68)]
def glass_panel(img, t):
    p_in = prog(t, GL_IN, 10 / FPS); p_out = prog(t, GL_OUT, 6 / FPS)
    if p_in <= 0 or p_out >= 1: return img
    x0, y0, x1, y1 = 90, 1330, 990, 1760
    dy = 120 * (1 - eo(p_in))
    reg = img.crop((x0 - 40, int(y0 - 40 + dy), x1 + 40, int(y1 + 40 + dy)))
    reg = reg.resize((reg.width // 4, reg.height // 4)).filter(ImageFilter.GaussianBlur(8)).resize(reg.size)
    reg = ImageEnhance.Brightness(reg).enhance(0.55)                 # dark glass: background is bright carpet
    pan = Image.new("RGBA", reg.size, (0, 0, 0, 0))
    pm = Image.new("L", reg.size, 0); ImageDraw.Draw(pm).rounded_rectangle([40, 40, reg.width - 41, reg.height - 41], radius=60, fill=255)
    pan.paste(reg, (0, 0), pm)
    od = ImageDraw.Draw(pan)
    od.rounded_rectangle([40, 40, pan.width - 41, pan.height - 41], radius=60, fill=(10, 10, 14, 70), outline=(255, 255, 255, 110), width=3)
    hl = Image.new("RGBA", pan.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([56, 52, pan.width - 56, 130], radius=46, fill=(255, 255, 255, 30))
    pan.alpha_composite(hl.filter(ImageFilter.GaussianBlur(12)))
    sp = prog(t, GL_IN + 0.2, 0.5)
    if 0 < sp < 1:
        sw = Image.new("L", pan.size, 0); sx = -300 + (pan.width + 600) * sp
        ImageDraw.Draw(sw).polygon([(sx, 0), (sx + 120, 0), (sx - 80, pan.height), (sx - 200, pan.height)], fill=55)
        sw = ImageChops.multiply(sw.filter(ImageFilter.GaussianBlur(20)), pm)
        wl = Image.new("RGBA", pan.size, (255, 255, 255, 0)); wl.putalpha(sw); pan.alpha_composite(wl)
    d = ImageDraw.Draw(pan); ox, oy = 40 + 56, 40 + 40
    d.text((ox, oy), "BESPLATNO UZ SVAKI PARFEM", font=font("Bold", 34, False), fill=AMB + (255,))
    for k, (txt, t0) in enumerate(GL_ROWS):
        a = prog(t, t0, 5 / FPS)
        if a <= 0: continue
        last = k == len(GL_ROWS) - 1
        fsz = 84 if last else 64
        row = Image.new("RGBA", (900, 120), (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        rd.text((0, 6), ("+ " if k else "") + txt, font=font("Black", fsz), fill=(AMB if last else WHITE) + (255,))
        row = fade(row, eo(a))
        pan.alpha_composite(row, (ox + int(30 * (1 - eo(a))), oy + 58 + k * 92 + (0 if not last else 0)))
    s = 1 - 0.08 * eo(p_out)
    pan = fade(scaled(pan, s), clamp(p_in * 2) * (1 - p_out))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + dy
    paste_shadowed(img, pan, (cx - pan.width / 2, cy - pan.height / 2), off=(0, 18), blur=30, alpha=int(110 * (1 - p_out)))
    return img

CUT2 = 14.03                       # source cut back to speaker
# The source uses dip-to-black transitions; replace each with a zoom-through cut.
# (out_last, cut, in_first, focus_out, focus_in) in frame indices
DIPS = [(202, 205, 214, (0.5, 0.45), (0.5, 0.36)),
        (316, 320, 323, (0.5, 0.36), (0.5, 0.55)),
        (420, 422, 429, (0.5, 0.55), (0.5, 0.36)),
        (749, 755, 765, (0.5, 0.36), (0.5, 0.36))]
def dip_frame(fi):
    for o_, c_, i_, fo, fin in DIPS:
        if o_ < fi <= c_:
            q = (fi - o_) / (c_ - o_ + 1)
            return zoom_blur(zoom(base_idx(o_).copy(), 1 + 0.35 * ei(q), *fo), 0.12 * q, *fo)
        if c_ < fi < i_ + 4:
            q = (fi - c_) / (i_ + 4 - c_)
            img = base_idx(max(fi, i_)).copy()
            return zoom_blur(zoom(img, 1.2 - 0.2 * eo(q), *fin), 0.08 * (1 - q), *fin)
    return None

def card2(txt, chk):
    f = font("Black", 50)
    tw = f.getlength(txt)
    c = Image.new("RGBA", (int(tw + (160 if chk else 76)), 108), (0, 0, 0, 0)); cd = ImageDraw.Draw(c)
    cd.rounded_rectangle([0, 0, c.width - 1, 107], radius=30, fill=(255, 255, 255, 245) if chk else AMB + (250,))
    if chk:
        cd.ellipse([22, 22, 86, 86], fill=AMB)
        cd.text((112, 22), txt, font=f, fill=INK)
    else:
        cd.text((38, 22), txt, font=f, fill=INK)
    return c

def check2(c, p):
    c = c.copy(); d = ImageDraw.Draw(c)
    pts = [(38, 55), (51, 68), (72, 40)]
    L1 = math.dist(pts[0], pts[1]); L2 = math.dist(pts[1], pts[2]); tot = (L1 + L2) * p
    if tot <= 0: return c
    if tot <= L1:
        e = (pts[0][0] + (pts[1][0] - pts[0][0]) * tot / L1, pts[0][1] + (pts[1][1] - pts[0][1]) * tot / L1)
        d.line([pts[0], e], fill=WHITE, width=10)
    else:
        k = (tot - L1) / L2
        e = (pts[1][0] + (pts[2][0] - pts[1][0]) * k, pts[1][1] + (pts[2][1] - pts[1][1]) * k)
        d.line([pts[0], pts[1], e], fill=WHITE, width=10, joint="curve")
    return c

STEPS = [("IZABERI PARFEM", True, 16.38), ("PORUČI NA SAJTU", True, 19.26), ("+ GURMANSKI SET GRATIS", False, 21.90)]
EX0 = 22.72
def checklist(img, t):
    la = prog(t, 15.92, 6 / FPS) * (1 - prog(t, EX0, 6 / FPS))
    if la > 0:
        lab = Image.new("RGBA", (600, 56), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lab)
        ld.text((3, 3), "KAKO FUNKCIONIŠE:", font=font("Bold", 36, False), fill=(0, 0, 0, 160))
        ld.text((0, 0), "KAKO FUNKCIONIŠE:", font=font("Bold", 36, False), fill=(255, 255, 255, 235))
        img.alpha_composite(fade(lab, la), (66, int(96 - 300 * prog(t, EX0, 8 / FPS) ** 2)))
    for k, (txt, chk, t0) in enumerate(STEPS):
        if t < t0: continue
        p = prog(t, t0, 8 / FPS)
        c = card2(txt, chk)
        if chk: c = check2(c, eo(prog(t, t0 + 3 / FPS, 6 / FPS)))
        sc = 0.6 + 0.4 * back(p, 2.2)
        a = clamp(p * 3)
        if k < 2 and t > STEPS[2][2]: a *= 1 - 0.35 * prog(t, STEPS[2][2], 6 / FPS)
        q = prog(t, EX0 + k * 2 / FPS, 8 / FPS)
        a *= 1 - q
        if a <= 0: continue
        cc = fade(scaled(c, sc), a)
        y = 156 + k * 124 + (c.height - cc.height) / 2 - 900 * q * q
        paste_shadowed(img, cc, (60 + (c.width - cc.width) / 2, y), off=(0, 16), blur=24, alpha=int(140 * a))
    return img

@lru_cache(maxsize=1)
def avatar():
    im = base_idx(round(29.6 * FPS)).convert("RGB")
    face = im.crop((360, 330, 720, 690)).resize((96, 96), Image.LANCZOS)
    m = Image.new("L", (96, 96), 0); ImageDraw.Draw(m).ellipse([0, 0, 95, 95], fill=255)
    out = Image.new("RGBA", (104, 104), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, 103, 103], fill=AMB + (255,))
    out.paste(face, (4, 4), m)
    return out

CTA = 30.22; PRESS = 30.95
def cta(img, t):
    p = prog(t, CTA, 8 / FPS)
    if p <= 0: return img
    pw, ph = 860, 136
    pil = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(pil)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=68, fill=(255, 255, 255, 245))
    pil.alpha_composite(avatar(), (16, 16))
    d.text((140, 28), "@markovmirisnisvet", font=font("Bold", 40, False), fill=INK)
    d.text((140, 78), "parfemi • recenzije", font=font("Medium", 28, False), fill=(110, 110, 110))
    pressed = t >= PRESS
    bp_ = prog(t, PRESS, 6 / FPS)
    bs = 1 - 0.12 * math.sin(math.pi * bp_) if 0 < bp_ < 1 else 1
    btn = Image.new("RGBA", (190, 76), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    if pressed:
        bd.rounded_rectangle([0, 0, 189, 75], radius=38, fill=(235, 235, 235, 255))
        bd.text((95, 39), "PRATIŠ ✓", font=font("Bold", 30, False), fill=INK, anchor="mm")
    else:
        bd.rounded_rectangle([0, 0, 189, 75], radius=38, fill=AMB + (255,))
        bd.text((95, 39), "ZAPRATI", font=font("Black", 32), fill=INK, anchor="mm")
    btn = scaled(btn, bs)
    pil.alpha_composite(btn, (int(pw - 30 - 95 - btn.width / 2), int(ph / 2 - btn.height / 2)))
    sc = 0.7 + 0.3 * back(p, 2.0)
    pl = fade(scaled(pil, sc), clamp(p * 2))
    paste_shadowed(img, pl, (W / 2 - pl.width / 2, 1560 - pl.height / 2), off=(0, 16), blur=26, alpha=int(130 * clamp(p * 2)))
    return img

def render(fi):
    t = fi / FPS
    d = dip_frame(fi)
    if d is not None:
        img = d
    elif t < 3.75:
        img = zoom(base(t), 1 + 0.05 * eio(prog(t, 0, 3.75)), 0.5, 0.45)
    elif SNAP <= t < 6.78:
        img = snap_zoom(t)
    elif 10.80 <= t < CUT2:
        img = glass_panel(base(t), t)
    elif 15.90 <= t < 23.20:
        img = checklist(base(t), t)
    elif 25.6 <= t < 29.10:
        img = zoom(base(t), 1 + 0.07 * eio(prog(t, 25.6, 3.5)), 0.5, 0.38)
    elif t >= CTA:
        img = cta(base(t), t)
    else:
        img = base(t)
    captions2(img, t, 250 if t < 3.75 else 1320)
    fo = prog(t, 32.85, TOTAL - 32.85)
    if fo > 0: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * eio(fo)))))
    return img.convert("RGB")

def job(fi):
    render(fi).save(f"{WD}/frames/{fi:04d}.png", compress_level=1)

if __name__ == "__main__":
    os.makedirs(f"{WD}/frames", exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[2] == "test":
        ts = [float(x) for x in sys.argv[3].split(",")]
        ims = [render(round(x * FPS)).resize((270, 480)) for x in ts]
        cols = 8; rows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (270 * cols, 480 * rows))
        for k, (im, x) in enumerate(zip(ims, ts)):
            ImageDraw.Draw(im).text((6, 6), f"{x:.2f}", font=font("Bold", 22, False), fill=(255, 255, 0))
            sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(f"{WD}/test.png"); print("test sheet"); sys.exit()
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
    with Pool(4) as pool:
        for k, _ in enumerate(pool.imap_unordered(job, range(a, b), chunksize=4)):
            if k % 100 == 0: print("frame", k, "/", b - a, flush=True)
    print("done", b - a)
