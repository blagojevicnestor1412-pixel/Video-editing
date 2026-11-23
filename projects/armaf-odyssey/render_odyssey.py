"""Armaf Odyssey review reel renderer. Reuses helpers from the skill's reference render.py.
Usage: python3 -I render_odyssey.py <ref_render.py> <workdir> [first last | test t1,t2,...]"""
import sys, json
REF = sys.argv.pop(1)
exec(open(REF).read().rsplit('if __name__ == "__main__":', 1)[0])

TOTAL = 45.33
NFRAMES = round(TOTAL * FPS)
NBASE = len(glob.glob(f"{WD}/base/*.jpg"))
SEGS = [(0.0, TOTAL)]; MAP = [(0.0, TOTAL, 0.0)]; BODY = TOTAL
GOLD = (246, 190, 60); DARK = (16, 16, 18)

@lru_cache(maxsize=24)
def base_idx(i):
    i = max(0, min(NBASE - 1, i))
    return Image.open(f"{WD}/base/{i+1:04d}.jpg").convert("RGBA")

# ------------------------------------------------------------ product sections
# name, card bg, accent, text colour, section start/end (s), title window (frames, = where old label was removed),
# card rect y0,y1 (covers the cleaned band with margin)
P = [
    dict(name="BAHAMAS",       bg=(22, 22, 26),   acc=(255, 86, 150), fg=WHITE, s=6.33,  e=12.60, win=(191, 280),   y=(1404, 1572)),
    dict(name="TOFFEE COFFEE", bg=(86, 46, 28),   acc=(246, 214, 182), fg=WHITE, s=12.60, e=21.87, win=(440, 529),   y=(1456, 1622)),
    dict(name="LIMONI",        bg=(170, 214, 46), acc=(255, 204, 0),  fg=DARK,  s=21.87, e=29.47, win=(757, 846),   y=(1546, 1716)),
    dict(name="MANDARIN SKY",  bg=(34, 172, 196), acc=(255, 122, 34), fg=WHITE, s=29.47, e=39.10, win=(1009, 1098), y=(1446, 1610)),
]
CARD_X = (64, 1016)

def section(t):
    for k, p in enumerate(P):
        if p["s"] <= t < p["e"]: return k
    return None

def accent_for(t):
    k = section(t)
    return GOLD if k is None else P[k]["acc"]

# ------------------------------------------------------------ captions
raw = json.load(open(f"{WD}/caps.json"))
CAPS = []
for s, txt, kw in raw:
    if txt == "SKY": continue
    if txt == "MANDARIN": txt, kw = "MANDARIN SKY", "MANDARIN"
    CAPS.append((s, tuple(txt.split()), kw))

@lru_cache(maxsize=96)
def cap_layer2(words, hi, size, acc, ink):
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
        else: sd.text((x, size * 0.22 + 6), w, font=f, fill=(0, 0, 0, 230))
        x += wd + sp
    L.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    for x, wd in pills:
        p = Image.new("RGBA", (int(wd + 36), int(size * 1.24)), (0, 0, 0, 0))
        ImageDraw.Draw(p).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=int(size * 0.2), fill=acc + (255,))
        p = p.rotate(-2, expand=True, resample=Image.BICUBIC)
        L.alpha_composite(p, (int(x - 18), int(size * 0.14)))
    d = ImageDraw.Draw(L); x = 40
    for w, wd in zip(words, ws):
        d.text((x, size * 0.22), w, font=f, fill=(ink if w == hi else WHITE)); x += wd + sp
    return L

def ink_on(c): return DARK if (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) > 150 else WHITE

def captions2(img, t, y=1290):
    for k, (st, words, hi) in enumerate(CAPS):
        nxt = CAPS[k + 1][0] if k + 1 < len(CAPS) else TOTAL
        end = min(nxt, st + 1.6)
        if st <= t < end:
            ts = t - st
            p = clamp(ts * FPS / 5)
            sc = 0.72 + 0.28 * back(p, 2.4) if p < 1 else 1.0
            acc = accent_for(st)
            L = cap_layer2(words, hi, 82, acc, ink_on(acc))
            if L.width > W - 80: L = scaled(L, (W - 80) / L.width)
            put_center(img, L, W / 2, y, sc, clamp(ts * FPS / 2))
            return

# ------------------------------------------------------------ title cards (opaque: they also hide the removed labels)
def rainbow_bar(w, h, shift):
    cols = [(255, 86, 150), (255, 200, 40), (40, 200, 220), (140, 90, 255), (255, 86, 150)]
    xs = np.linspace(0, 1, w)[None, :] + shift
    xs = xs % 1.0
    seg = xs * (len(cols) - 1); i = np.floor(seg).astype(int); fr = seg - i
    c0 = np.array(cols)[i]; c1 = np.array(cols)[np.minimum(i + 1, len(cols) - 1)]
    rgb = (c0 * (1 - fr[..., None]) + c1 * fr[..., None]).astype(np.uint8)
    rgb = np.repeat(rgb, h, axis=0)
    return Image.fromarray(np.dstack([rgb, np.full((h, w), 255, np.uint8)]), "RGBA")

def title_card(k, t, local):
    """local: seconds since title window start (may be negative = before)."""
    p = P[k]; y0, y1 = p["y"]; x0, x1 = CARD_X
    w, h = x1 - x0, y1 - y0
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=34, fill=p["bg"] + (255,))
    # accent bar sweeping in along the left edge
    if k == 0:
        bar = rainbow_bar(w, 12, t * 0.35)
    else:
        bar = Image.new("RGBA", (w, 12), p["acc"] + (255,))
    reveal = eo(clamp(local / (10 / FPS)))
    bm = Image.new("L", (w, 12), 0); ImageDraw.Draw(bm).rectangle([0, 0, int(w * reveal), 11], fill=255)
    cm = Image.new("L", (w, h), 0); ImageDraw.Draw(cm).rounded_rectangle([0, 0, w - 1, h - 1], radius=34, fill=255)
    bl = Image.new("RGBA", (w, h), (0, 0, 0, 0)); bl.paste(bar, (0, h - 12), bm)
    bl.putalpha(ImageChops.multiply(bl.split()[-1], cm)); c.alpha_composite(bl)
    # text: small label + big name, sliding up
    a1 = eo(clamp((local + 2 / FPS) / (7 / FPS))); a2 = eo(clamp((local + 1 / FPS) / (8 / FPS)))
    fg = p["fg"]
    lab = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
    ImageDraw.Draw(lab).text((0, 0), "ARMAF ODYSSEY", font=font("Bold", 32, False), fill=((p["acc"] if k in (0, 1) else (DARK if k == 2 else WHITE))) + (255,))
    c.alpha_composite(fade(lab, a1), (46, int(26 + 20 * (1 - a1))))
    nm = Image.new("RGBA", (w, 110), (0, 0, 0, 0))
    ImageDraw.Draw(nm).text((0, 0), p["name"], font=font("Black", 78), fill=fg + (255,))
    c.alpha_composite(fade(nm, a2), (44, int(64 + 26 * (1 - a2))))
    # counter on the right
    num = Image.new("RGBA", (200, 110), (0, 0, 0, 0)); nd_ = ImageDraw.Draw(num)
    nd_.text((200, 55), f"0{k+1}/04", font=font("Black", 44), fill=fg + (200,), anchor="rm")
    c.alpha_composite(fade(num, a1), (w - 236, (h - 110) // 2))
    # light sweep
    sp = clamp((local - 0.25) / 0.6)
    if 0 < sp < 1:
        sw = Image.new("L", (w, h), 0); sx = -200 + (w + 400) * sp
        ImageDraw.Draw(sw).polygon([(sx, 0), (sx + 90, 0), (sx - 40, h), (sx - 130, h)], fill=60)
        sw = ImageChops.multiply(sw.filter(ImageFilter.GaussianBlur(14)), cm)
        wl = Image.new("RGBA", (w, h), (255, 255, 255, 0)); wl.putalpha(sw); c.alpha_composite(wl)
    return c

def draw_title(img, t):
    fi = round(t * FPS)
    for k, p in enumerate(P):
        a, b = p["win"]
        if a <= fi <= b + 8:
            local = t - a / FPS
            c = title_card(k, t, local)
            out = prog(fi, b + 1, 8)                      # exit only after the window (plate clean again)
            sc = 1 - 0.12 * ei(out)
            c = fade(scaled(c, sc), 1 - ei(out))
            y0 = p["y"][0]; x0 = CARD_X[0]
            cx = x0 + (CARD_X[1] - x0) / 2; cy = (y0 + p["y"][1]) / 2 + 60 * ei(out)
            paste_shadowed(img, c, (cx - c.width / 2, cy - c.height / 2), off=(0, 14), blur=24, alpha=int(120 * (1 - out)))
    return img

# intro card (frames 0-190 cover the old "Armaf Odyssey parfemi" title)
DOTS = [P[0]["acc"], (140, 80, 50), P[2]["bg"], P[3]["bg"]]
def intro_card(img, t):
    fi = round(t * FPS)
    if fi > 198: return img
    x0, x1, y0, y1 = 96, 984, 1380, 1690
    w, h = x1 - x0, y1 - y0
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=40, fill=(250, 248, 244, 255))
    a1 = 1.0 if t < 0.5 else 1.0; a2 = eo(clamp((t - 0.15) / 0.35))
    l1 = Image.new("RGBA", (w, 120), (0, 0, 0, 0))
    ImageDraw.Draw(l1).text((w / 2, 60), "ARMAF ODYSSEY", font=font("Black", 104), fill=DARK, anchor="mm")
    c.alpha_composite(fade(l1, a1), (0, int(34 + 30 * (1 - a1))))
    l2 = Image.new("RGBA", (w, 70), (0, 0, 0, 0))
    ImageDraw.Draw(l2).text((w / 2, 35), "4 PARFEMA IZ MOJE KOLEKCIJE", font=font("Bold", 40, False), fill=(90, 90, 96), anchor="mm")
    c.alpha_composite(fade(l2, a2), (0, int(150 + 20 * (1 - a2))))
    # four product-colour dots pop on "ČETIRI"
    for k, col in enumerate(DOTS):
        q = prog(t, 1.30 + k * 3 / FPS, 8 / FPS)
        if q <= 0: continue
        r = 22 * (0.6 + 0.4 * back(q, 2.4))
        cx = w / 2 + (k - 1.5) * 70; cy = 250
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))
    out = prog(fi, 191, 7)
    c = fade(scaled(c, 1 - 0.1 * ei(out)), 1 - ei(out))
    paste_shadowed(img, c, ((x0 + x1) / 2 - c.width / 2, (y0 + y1) / 2 - c.height / 2 + 40 * ei(out)), off=(0, 16), blur=28, alpha=int(110 * (1 - out)))
    return img

# ------------------------------------------------------------ progress tracker (top)
TR_IN, TR_OUT = 5.08, 39.10
def tracker(img, t):
    a = prog(t, TR_IN, 10 / FPS) * (1 - prog(t, TR_OUT - 8 / FPS, 8 / FPS))
    if a <= 0: return img
    seg_w, gap, hh = 214, 18, 14
    tot = 4 * seg_w + 3 * gap
    L = Image.new("RGBA", (tot + 40, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for k, p in enumerate(P):
        x = 20 + k * (seg_w + gap)
        d.rounded_rectangle([x, 56, x + seg_w, 56 + hh], radius=7, fill=(255, 255, 255, 110))
        fillp = clamp((t - p["s"]) / (p["e"] - p["s"]))
        if fillp > 0:
            col = p["acc"] if k != 2 else p["bg"]
            d.rounded_rectangle([x, 56, x + max(hh, seg_w * fillp), 56 + hh], radius=7, fill=col + (255,))
        act = p["s"] <= t < p["e"]
        nm = p["name"].split()[0]
        d.text((x + seg_w / 2 + 2, 30 + 2), nm, font=font("Bold", 26, False), fill=(0, 0, 0, 120), anchor="mm")
        d.text((x + seg_w / 2, 30), nm, font=font("Bold", 26, False), fill=(255, 255, 255, 255 if act else 150), anchor="mm")
    L = fade(L, a)
    img.alpha_composite(L, (int(W / 2 - L.width / 2), int(70 - 30 * (1 - eo(a)))))
    return img

# ------------------------------------------------------------ mood effects
def waves(img, t, t0=11.55, t1=12.60):
    if not (t0 <= t < t1): return img
    rise = eo(prog(t, t0, 0.45))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for k, (col, amp, base_y, sp) in enumerate([((70, 180, 240, 110), 28, 1560, 1.6), ((30, 140, 215, 140), 34, 1660, -1.2), ((20, 110, 195, 170), 24, 1770, 2.0)]):
        by = H + 40 - (H + 40 - base_y) * rise
        pts = [(x, by + amp * math.sin(x / 140 + t * sp * 2 + k)) for x in range(0, W + 20, 20)]
        d.polygon(pts + [(W, H), (0, H)], fill=col)
    img.alpha_composite(L)
    return img

SNOW = None
def snow(img, t, t0=13.80, t1=15.30):
    global SNOW
    if not (t0 <= t < t1): return img
    if SNOW is None:
        r = random.Random(9); SNOW = [(r.uniform(0, W), r.uniform(-H, 0), r.uniform(4, 11), r.uniform(220, 420), r.uniform(0, 6)) for _ in range(90)]
    a = prog(t, t0, 0.25) * (1 - prog(t, t1 - 0.35, 0.35))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for x, y, r_, v, ph in SNOW:
        yy = (y + v * (t - t0) * 1.6) % (H + 40) - 20
        xx = x + 30 * math.sin(t * 1.5 + ph)
        if 1390 < yy < 1720: continue                     # keep snow off the title card
        d.ellipse([xx - r_, yy - r_, xx + r_, yy + r_], fill=(255, 255, 255, int(200 * a)))
    img.alpha_composite(L.filter(ImageFilter.GaussianBlur(1)))
    return img

CAP_TRACK = [(16.45, 442, 900), (16.70, 499, 941), (16.90, 487, 961), (17.10, 474, 941), (17.30, 524, 879), (17.50, 470, 920), (17.62, 470, 900)]
def cap_ring(img, t):
    t0, t1 = 16.50, 17.60
    if not (t0 <= t < t1): return img
    for (ta, xa, ya), (tb, xb, yb) in zip(CAP_TRACK, CAP_TRACK[1:]):
        if ta <= t <= tb:
            q = (t - ta) / (tb - ta); cx, cy = xa + (xb - xa) * q, ya + (yb - ya) * q; break
    else: cx, cy = CAP_TRACK[-1][1:]
    draw_p = eo(prog(t, t0, 10 / FPS)); a = 1 - prog(t, t1 - 6 / FPS, 6 / FPS)
    R = 190
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.arc([cx - R, cy - R, cx + R, cy + R], start=-90, end=-90 + 360 * draw_p, fill=(255, 255, 255, int(255 * a)), width=12)
    for k in range(4):
        ang = math.radians(-60 + k * 30); q = prog(t, t0 + 0.25 + k * 0.04, 8 / FPS)
        if q <= 0: continue
        r0, r1 = R + 22, R + 22 + 46 * eo(q)
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)), (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))], fill=(255, 255, 255, int(240 * a * (1 - 0.6 * q))), width=8)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(L.split()[-1].point(lambda v: v * 140 // 255))
    sh = sh.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(3)).resize((W, H))
    img.alpha_composite(sh, (0, 6)); img.alpha_composite(L)
    return img

@lru_cache(maxsize=16)
def chip(txt, em, bgc, fgc):
    f = font("Black", 54)
    tw = f.getlength(txt)
    e = emoji(em, 64) if em else None
    w = int(tw + 70 + (84 if e else 0)); h = 100
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=50, fill=bgc + (250,))
    x = 34
    if e: c.alpha_composite(e, (x - 6, (h - e.height) // 2)); x += 84
    d.text((x, h / 2 + 2), txt, font=f, fill=fgc, anchor="lm")
    return c

def chips(img, t, items, t_out, y=330):
    """items: [(t_in, txt, emoji, bg, fg)] laid out centred in one row."""
    vis = [it for it in items if t >= it[0]]
    if not vis or t >= t_out + 8 / FPS: return img
    cs = [chip(it[1], it[2], it[3], it[4]) for it in items]
    gap = 26; tot = sum(c.width for c in cs) + gap * (len(cs) - 1)
    x = W / 2 - tot / 2
    for k, (it, c) in enumerate(zip(items, cs)):
        cx = x + c.width / 2; x += c.width + gap
        if t < it[0]: continue
        p = prog(t, it[0], 8 / FPS); q = prog(t, t_out + k * 2 / FPS, 6 / FPS)
        if q >= 1: continue
        sc = (0.5 + 0.5 * back(p, 2.6)) * (1 - 0.3 * q)
        put_center(img, c, cx, y - 40 * ei(q), sc, clamp(p * 3) * (1 - q))
    return img

def sun_badge(img, t, t0=21.95, t1=23.80):
    if not (t0 <= t < t1 + 8 / FPS): return img
    p = prog(t, t0, 10 / FPS); q = prog(t, t1, 8 / FPS)
    a = clamp(p * 2) * (1 - q)
    S = 300
    L = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    rot = t * 40
    for k in range(12):
        ang = math.radians(rot + k * 30)
        pts = [(S / 2 + 140 * math.cos(ang - 0.09), S / 2 + 140 * math.sin(ang - 0.09)), (S / 2 + 140 * math.cos(ang + 0.09), S / 2 + 140 * math.sin(ang + 0.09)), (S / 2, S / 2)]
        d.polygon(pts, fill=(255, 210, 40, 170))
    d.ellipse([S / 2 - 98, S / 2 - 98, S / 2 + 98, S / 2 + 98], fill=(255, 204, 0, 255))
    d.text((S / 2, S / 2 - 22), "#1", font=font("Black", 76), fill=DARK, anchor="mm")
    d.text((S / 2, S / 2 + 42), "ZA LETO", font=font("Black", 30), fill=DARK, anchor="mm")
    sc = (0.4 + 0.6 * back(p, 2.2)) * (1 - 0.3 * q)
    put_center(img, L, 860, 380, sc, a)
    return img

LEMONS = None
def lemons(img, t, t0=28.28, t1=29.45):
    global LEMONS
    if not (t0 <= t < t1): return img
    if LEMONS is None:
        r = random.Random(3); LEMONS = [(r.uniform(120, 960), r.uniform(260, 700), r.uniform(110, 160), k * 2 / FPS, r.uniform(-25, 25)) for k in range(7)]
    for x, y, s, dl, rot in LEMONS:
        p = prog(t, t0 + dl, 8 / FPS)
        if p <= 0: continue
        q = prog(t, t1 - 8 / FPS, 8 / FPS)
        e = emoji("🍋", int(s)).rotate(rot + 20 * (t - t0), expand=True, resample=Image.BICUBIC)
        put_center(img, e, x, y - 60 * (t - t0), 0.4 + 0.6 * back(p, 2.6), clamp(p * 2) * (1 - q))
    return img

def ratings(img, t, t0=30.10, t1=33.45):
    if not (t0 <= t < t1 + 8 / FPS): return img
    p = prog(t, t0, 10 / FPS); q = prog(t, t1, 8 / FPS)
    x0, y0, x1, y1 = 90, 230, 990, 590
    reg = img.crop((x0, y0, x1, y1)).resize(((x1 - x0) // 4, (y1 - y0) // 4)).filter(ImageFilter.GaussianBlur(6)).resize((x1 - x0, y1 - y0))
    reg = ImageEnhance.Brightness(reg).enhance(0.5)
    w, h = reg.size
    pan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=44, fill=255)
    pan.paste(reg, (0, 0), m)
    d = ImageDraw.Draw(pan)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=44, fill=(10, 10, 14, 80), outline=(255, 255, 255, 110), width=3)
    d.text((44, 36), "POBEDNIK U DVE KATEGORIJE", font=font("Bold", 34, False), fill=GOLD)
    rows = [("TRAJANJE", 30.24), ("SLATKOĆA", 31.50)]
    for k, (lab, ts) in enumerate(rows):
        yy = 112 + k * 112
        d.text((44, yy), lab, font=font("Black", 48), fill=WHITE)
        bx0, bx1 = 380, w - 190
        d.rounded_rectangle([bx0, yy + 14, bx1, yy + 44], radius=15, fill=(255, 255, 255, 50))
        f = eo(prog(t, ts, 0.6))
        if f > 0:
            d.rounded_rectangle([bx0, yy + 14, bx0 + max(30, (bx1 - bx0) * f), yy + 44], radius=15, fill=GOLD + (255,))
        d.text((w - 44, yy + 30), f"{round(10 * f)}/10", font=font("Black", 40), fill=WHITE, anchor="rm")
    pan = fade(scaled(pan, (0.9 + 0.1 * eo(p)) * (1 - 0.08 * q)), clamp(p * 2) * (1 - q))
    paste_shadowed(img, pan, ((x0 + x1) / 2 - pan.width / 2, (y0 + y1) / 2 - pan.height / 2 + 60 * (1 - eo(p))), off=(0, 16), blur=26, alpha=int(110 * (1 - q)))
    return img

def meter(img, t, t0=37.60, t1=39.02):
    if not (t0 <= t < t1): return img
    p = prog(t, t0, 8 / FPS); q = prog(t, t1 - 5 / FPS, 5 / FPS)
    w, h = 820, 150
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=34, fill=(16, 16, 20, 225))
    d.text((36, 26), "JAČINA", font=font("Black", 42), fill=WHITE)
    f = eo(prog(t, 37.94, 0.45))
    bx0, bx1 = 36, w - 36
    d.rounded_rectangle([bx0, 92, bx1, 122], radius=15, fill=(255, 255, 255, 50))
    if f > 0:
        n = 24
        for i in range(int(n * f)):
            u = i / (n - 1)
            col = (int(80 + 175 * u), int(220 - 170 * u), 60)
            xx = bx0 + (bx1 - bx0) * i / n
            d.rounded_rectangle([xx + 2, 92, xx + (bx1 - bx0) / n - 2, 122], radius=6, fill=col + (255,))
    if f > 0.98:
        d.text((w - 36, 50), "MAX", font=font("Black", 44), fill=(255, 70, 50), anchor="rm")
    jit = 0
    if t > 38.40: jit = 6 * math.sin(t * 90) * (1 - prog(t, 38.40, 0.4))
    put_center(img, c, W / 2 + jit, 360, 0.6 + 0.4 * back(p, 2.2), clamp(p * 2) * (1 - q))
    return img

def recap(img, t, t0=39.70, t1=42.20):
    if not (t0 <= t < t1 + 10 / FPS): return img
    for k, pr in enumerate(P):
        p = prog(t, t0 + k * 5 / FPS, 8 / FPS)
        q = prog(t, t1 + k * 2 / FPS, 6 / FPS)
        if p <= 0 or q >= 1: continue
        txt = pr["name"]
        f = font("Black", 46)
        w = int(f.getlength(txt) + 60); h = 86
        c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=43, fill=pr["bg"] + (250,))
        d.text((w / 2, h / 2 + 2), txt, font=f, fill=pr["fg"], anchor="mm")
        cx = W / 2 + (-230 if k % 2 == 0 else 230); cy = 1520 + (k // 2) * 112
        put_center(img, c, cx, cy + 40 * ei(q), (0.5 + 0.5 * back(p, 2.4)) * (1 - 0.2 * q), clamp(p * 3) * (1 - q))
    return img

@lru_cache(maxsize=1)
def avatar():
    im = base_idx(round(40.2 * FPS)).convert("RGB")
    face = im.crop((360, 180, 760, 580)).resize((96, 96), Image.LANCZOS)
    m = Image.new("L", (96, 96), 0); ImageDraw.Draw(m).ellipse([0, 0, 95, 95], fill=255)
    out = Image.new("RGBA", (104, 104), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, 103, 103], fill=GOLD + (255,))
    out.paste(face, (4, 4), m)
    return out

CTA, PRESS = 42.30, 42.85
def cta(img, t):
    p = prog(t, CTA, 8 / FPS)
    if p <= 0: return img
    pw, ph = 880, 140
    pil = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(pil)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=70, fill=(255, 255, 255, 248))
    pil.alpha_composite(avatar(), (18, 18))
    d.text((142, 30), "@markovmirisnisvet", font=font("Bold", 40, False), fill=INK)
    d.text((142, 80), "parfemi • recenzije", font=font("Medium", 28, False), fill=(110, 110, 110))
    bp_ = prog(t, PRESS, 6 / FPS)
    bs = 1 - 0.12 * math.sin(math.pi * bp_) if 0 < bp_ < 1 else 1
    btn = Image.new("RGBA", (196, 78), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    if t >= PRESS:
        bd.rounded_rectangle([0, 0, 195, 77], radius=39, fill=(235, 235, 235, 255))
        bd.text((98, 40), "PRATIŠ ✓", font=font("Bold", 30, False), fill=INK, anchor="mm")
    else:
        bd.rounded_rectangle([0, 0, 195, 77], radius=39, fill=GOLD + (255,))
        bd.text((98, 40), "ZAPRATI", font=font("Black", 32), fill=INK, anchor="mm")
    btn = scaled(btn, bs)
    pil.alpha_composite(btn, (int(pw - 30 - 98 - btn.width / 2), int(ph / 2 - btn.height / 2)))
    pl = fade(scaled(pil, 0.7 + 0.3 * back(p, 2.0)), clamp(p * 2))
    paste_shadowed(img, pl, (W / 2 - pl.width / 2, 1600 - pl.height / 2), off=(0, 16), blur=26, alpha=int(130 * clamp(p * 2)))
    return img

# ------------------------------------------------------------ frame assembly
CUTS = [12.60, 21.87, 29.47, 39.10]        # hard source cuts that get an incoming zoom settle (6.33 is skipped: title card there)
def plate(t):
    img = base(t)
    for c in CUTS:
        if c - 1e-6 <= t < c + 7 / FPS:
            q = prog(t, c, 7 / FPS)
            return zoom_blur(zoom(img, 1.10 - 0.10 * eo(q), 0.5, 0.45), 0.06 * (1 - q), 0.5, 0.45)
    return img

def render(fi):
    t = fi / FPS
    img = plate(t)
    img = waves(img, t); img = snow(img, t); img = cap_ring(img, t)
    img = intro_card(img, t); img = draw_title(img, t)
    img = chips(img, t, [(20.40, "TOFI", "🍬", (246, 214, 182), INK), (20.80, "KAFA", "☕", (86, 46, 28), WHITE)], 21.70)
    img = sun_badge(img, t); img = lemons(img, t); img = ratings(img, t)
    img = chips(img, t, [(35.96, "KARAMELA", "🍮", (255, 122, 34), WHITE)], 36.80)
    img = meter(img, t); img = recap(img, t); img = cta(img, t)
    img = tracker(img, t)
    captions2(img, t)
    fo = prog(t, 45.00, TOTAL - 45.00)
    if fo > 0: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * eio(fo)))))
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
            ImageDraw.Draw(im).text((6, 450), f"{x:.2f}", font=font("Bold", 22, False), fill=(255, 255, 0))
            sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(f"{WD}/test.png"); print("test sheet"); sys.exit()
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else NFRAMES
    with Pool(4) as pool:
        for k, _ in enumerate(pool.imap_unordered(job, range(a, b), chunksize=4)):
            if k % 200 == 0: print("frame", k, "/", b - a, flush=True)
    print("done", b - a)
