"""Concept mockups for the storyboard. Usage: python3 -I mock.py <scratchpad_dir>"""
import sys, math, random, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageOps, ImageEnhance
from rembg import remove, new_session

D = sys.argv[1]
OUT = f"{D}/sb"
W, H = 540, 960
RED = (232, 36, 28)
WHITE = (255, 255, 255)
FD = "/usr/share/fonts/truetype"
random.seed(7)


def font(weight="Black", size=40, display=True):
    import glob
    fam = "InterDisplay" if display else "Inter"
    c = glob.glob(f"/usr/share/fonts/**/{fam}-{weight}.*tf", recursive=True)
    if not c:
        c = glob.glob(f"/usr/share/fonts/**/*Inter*{weight}*.*tf", recursive=True)
    return ImageFont.truetype(c[0], size)


EMOJI = None
def emoji(ch, size):
    global EMOJI
    import glob
    if EMOJI is None:
        EMOJI = glob.glob("/usr/share/fonts/**/NotoColorEmoji*.ttf", recursive=True)[0]
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)


def load(t, graded=True):
    return Image.open(f"{D}/{'grd' if graded else 'raw'}_{t}.png").convert("RGBA")


def largest(m):
    import scipy.ndimage as nd
    a = np.asarray(m) > 128
    lab, n = nd.label(a)
    if n > 1:
        sizes = nd.sum(a, lab, range(1, n + 1))
        a = lab == (1 + int(np.argmax(sizes)))
    return Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))


SESSION = new_session("u2net_human_seg")
def mask(img):
    m = remove(img.convert("RGB"), session=SESSION, only_mask=True)
    return m.filter(ImageFilter.GaussianBlur(1.2))


def shadow(layer, off=(0, 10), blur=18, alpha=150):
    a = layer.split()[-1].point(lambda v: v * alpha // 255)
    s = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    s.putalpha(a)
    s = s.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (layer.width + abs(off[0]) * 2, layer.height + abs(off[1]) * 2), (0, 0, 0, 0))
    return s, off


def paste_shadowed(base, layer, xy, off=(0, 10), blur=16, alpha=140):
    a = layer.split()[-1].point(lambda v: v * alpha // 255)
    s = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    s.putalpha(a)
    pad = blur * 3
    big = Image.new("RGBA", (layer.width + pad * 2, layer.height + pad * 2), (0, 0, 0, 0))
    big.paste(s, (pad, pad), s)
    big = big.filter(ImageFilter.GaussianBlur(blur))
    xy = (int(xy[0]), int(xy[1]))
    base.alpha_composite(big, (xy[0] - pad + off[0], xy[1] - pad + off[1]))
    base.alpha_composite(layer, xy)


def caption(img, words, y=700, hi=(), size=46):
    """Word-by-word caption: white Inter Display Black, keywords red pill."""
    d = ImageDraw.Draw(img)
    f = font("Black", size)
    space = size * 0.28
    widths = [d.textlength(w, font=f) for w in words]
    total = sum(widths) + space * (len(words) - 1)
    x = (W - total) / 2
    for w, wd in zip(words, widths):
        if w in hi:
            pill = Image.new("RGBA", (int(wd + 20), int(size * 1.25)), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=10, fill=RED + (255,))
            img.alpha_composite(pill.rotate(-2, expand=True, resample=Image.BICUBIC), (int(x - 10), int(y - size * 0.05)))
        else:
            # soft shadow for legibility
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((x, y + 3), w, font=f, fill=(0, 0, 0, 200))
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
        d.text((x, y), w, font=f, fill=WHITE)
        x += wd + space
    return img


def label(img, text, sub=None):
    """Corner badge marking this image as a conceptual mockup."""
    d = ImageDraw.Draw(img)
    f = font("Bold", 15, display=False)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([12, 12, 12 + tw + 20, 40], radius=6, fill=(255, 196, 0, 235))
    d.text((22, 17), text, font=f, fill=(20, 20, 20))
    return img


def save(img, name, tag="CONCEPT MOCKUP"):
    img = label(img.copy(), tag)
    img.convert("RGB").save(f"{OUT}/{name}.jpg", quality=84)


# ---------------------------------------------------------------- S1 ORBIT
def orbit():
    bg = load("1.0")
    m = mask(bg)
    subj = bg.copy(); subj.putalpha(m)
    cx, cy, rx, ry = 262, 418, 175, 34
    text = "  JIU-JITSU  •  JIU-JITSU  •  "
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    n = len(text)
    fref = font("Black", 40)
    adv = [max(fref.getlength(c), 12) for c in text]
    tot = sum(adv); cum = 0
    for i, ch in enumerate(text):
        a = math.pi * 0.9 - 2 * math.pi * (cum + adv[i] / 2) / tot
        cum += adv[i]
        x = cx + rx * math.cos(a)
        y = cy + ry * math.sin(a) - 8
        depth = (math.sin(a) + 1) / 2  # 0 back .. 1 front
        size = int(24 + 26 * depth)
        f = font("Black", size)
        col = (255, 255, 255, int(110 + 145 * depth)) if depth > 0.5 else (232, 60, 50, int(90 + 120 * depth))
        tgt = front if depth > 0.5 else back
        g = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((size // 2, size // 3), ch, font=f, fill=col)
        tgt.alpha_composite(g, (int(x - size), int(y - size)))
    img = bg.copy()
    img.alpha_composite(back.filter(ImageFilter.GaussianBlur(0.8)))
    img.alpha_composite(subj)
    glow = front.filter(ImageFilter.GaussianBlur(8))
    img.alpha_composite(glow); img.alpha_composite(front)
    caption(img, ["JER", "JIU-JITSU"], hi=("JIU-JITSU",))
    save(img, "mock_s1_orbit")


# ---------------------------------------------------------- S2 PAPER CUTOUT
def paper():
    src = load("2.6")
    m = mask(src).point(lambda v: 255 if v > 140 else 0).filter(ImageFilter.GaussianBlur(1.2))
    ImageDraw.Draw(m).rectangle([0, 0, W, 284], fill=0)
    m = largest(m)
    # paper background: warm off-white with fibre noise + blurred red studio bleeding at edges
    noise = (np.random.rand(H, W) * 18).astype(np.uint8)
    paper = np.dstack([236 - noise, 228 - noise, 214 - noise, np.full((H, W), 255, np.uint8)])
    img = Image.fromarray(paper, "RGBA")
    # torn red strip
    strip = Image.new("RGBA", (W + 80, 230), RED + (255,))
    sm = Image.new("L", strip.size, 0); d = ImageDraw.Draw(sm)
    pts = [(0, 30)] + [(x, 18 + random.randint(-14, 14)) for x in range(0, strip.width, 22)] + [(strip.width, 30), (strip.width, 200)] + \
          [(x, 212 + random.randint(-14, 14)) for x in range(strip.width, 0, -22)] + [(0, 200)]
    d.polygon(pts, fill=255); strip.putalpha(sm)
    img.alpha_composite(strip.rotate(-6, expand=True, resample=Image.BICUBIC), (-60, 90))
    # sticker cutout of speaker: white border via dilated mask
    border = m.filter(ImageFilter.MaxFilter(15)).point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.GaussianBlur(1))
    sticker = Image.new("RGBA", (W, H), (250, 248, 242, 255)); sticker.putalpha(border)
    person = src.copy(); person.putalpha(m)
    sticker.alpha_composite(person)
    sticker = sticker.crop(sticker.getbbox())
    sticker = sticker.rotate(3, expand=True, resample=Image.BICUBIC)
    sticker = sticker.resize((int(sticker.width * 0.9), int(sticker.height * 0.9)), Image.LANCZOS)
    paste_shadowed(img, sticker, ((W - sticker.width) // 2 + 10, H - sticker.height + 40), off=(6, 12), blur=10, alpha=120)
    # ransom-note word stickers
    def tag(txt, fg, bgc, size, rot, xy, fw="Black"):
        f = font(fw, size)
        tw = ImageDraw.Draw(img).textlength(txt, font=f)
        t = Image.new("RGBA", (int(tw + 28), int(size * 1.35)), bgc + (255,))
        ImageDraw.Draw(t).text((14, size * 0.08), txt, font=f, fill=fg)
        t = t.rotate(rot, expand=True, resample=Image.BICUBIC)
        paste_shadowed(img, t, xy, off=(3, 6), blur=6, alpha=110)
    tag("„SKOČIMIŠ“", WHITE, (18, 18, 18), 58, 4, (40, 150))
    tag("VARIJANTA", (18, 18, 18), (255, 214, 0), 44, -3, (150, 236))
    tag("?!", WHITE, RED, 50, 8, (420, 120))
    save(img, "mock_s2_paper")


# ------------------------------------------------------- S3 ZOOM PORTAL + B-ROLL
def portal():
    img = load("4.2")
    # portal in the dark shelf area upper-left
    cx, cy, r = 150, 190, 118
    broll = Image.new("RGBA", (r * 2, r * 2), (30, 30, 34, 255))
    d = ImageDraw.Draw(broll)
    for i in range(0, r * 2, 18):
        d.line([(i, 0), (i - 60, r * 2)], fill=(44, 44, 50, 255), width=8)
    # stylised grappler silhouettes as placeholder art
    d.ellipse([70, 40, 110, 80], fill=(210, 210, 210, 255))
    d.polygon([(80, 80), (130, 100), (175, 60), (190, 72), (140, 125), (150, 190), (120, 190), (110, 140), (70, 170), (55, 150), (90, 120)], fill=(210, 210, 210, 255))
    d.ellipse([140, 120, 175, 155], fill=(150, 150, 150, 255))
    d.polygon([(150, 155), (190, 210), (100, 236), (90, 220), (150, 195)], fill=(150, 150, 150, 255))
    f = font("Bold", 15, display=False)
    d.rounded_rectangle([34, 188, 202, 226], radius=6, fill=(0, 0, 0, 170))
    d.text((44, 192), "B-ROLL PLACEHOLDER", font=f, fill=(255, 196, 0))
    d.text((44, 208), "flying armbar / jump guard", font=font("Medium", 12, display=False), fill=WHITE)
    cm = Image.new("L", broll.size, 0); ImageDraw.Draw(cm).ellipse([0, 0, r * 2 - 1, r * 2 - 1], fill=255)
    broll.putalpha(cm)
    # glow ring
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    for k, a in [(16, 60), (10, 110), (4, 255)]:
        rd.ellipse([cx - r - k, cy - r - k, cx + r + k, cy + r + k], outline=RED + (a,), width=k)
    img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(6))); img.alpha_composite(ring)
    img.alpha_composite(broll, (cx - r, cy - r))
    # zoom direction chevrons
    dd = ImageDraw.Draw(img)
    for s in (1.55, 1.3):
        rr = int(r * s)
        dd.arc([cx - rr, cy - rr, cx + rr, cy + rr], 20, 70, fill=(255, 255, 255, 140), width=3)
        dd.arc([cx - rr, cy - rr, cx + rr, cy + rr], 200, 250, fill=(255, 255, 255, 140), width=3)
    caption(img, ["SAD", "ĆU", "JA", "DA", "SKOČIM"], hi=("SKOČIM",))
    save(img, "mock_s3_portal")


# ---------------------------------------------------------------- S4 SNAP ZOOM
def snap():
    base = load("6.3")
    z = 1.38
    big = base.resize((int(W * z), int(H * z)), Image.LANCZOS)
    ox, oy = (big.width - W) // 2, int((big.height - H) * 0.32)
    img = big.crop((ox, oy, ox + W, oy + H))
    # radial motion blur approximation: blend progressively scaled copies
    acc = np.zeros((H, W, 4), np.float32)
    for i in range(8):
        s = 1 + i * 0.012
        t = img.resize((int(W * s), int(H * s)), Image.BILINEAR)
        x0, y0 = (t.width - W) // 2, (t.height - H) // 2
        acc += np.asarray(t.crop((x0, y0, x0 + W, y0 + H)), np.float32)
    blurred = Image.fromarray((acc / 8).astype(np.uint8), "RGBA")
    cm = Image.new("L", (W, H), 255); ImageDraw.Draw(cm).ellipse([110, 150, 430, 560], fill=0)
    img = Image.composite(blurred, img, cm.filter(ImageFilter.GaussianBlur(60)))
    # speed lines
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lines)
    for _ in range(46):
        a = random.uniform(0, 2 * math.pi); r0 = random.uniform(300, 360)
        ld.line([(270 + r0 * math.cos(a), 400 + r0 * math.sin(a) * 1.4), (270 + 700 * math.cos(a), 400 + 700 * math.sin(a) * 1.4)], fill=(255, 255, 255, 90), width=2)
    img.alpha_composite(lines)
    # inset: before frame
    ins = base.resize((120, 213), Image.LANCZOS)
    dd = ImageDraw.Draw(img)
    img.alpha_composite(ins, (W - 140, 60)); dd.rectangle([W - 141, 59, W - 20, 273], outline=WHITE, width=2)
    dd.text((W - 140, 278), "100% → 138% in 3 frames", font=font("SemiBold", 12, display=False), fill=WHITE)
    caption(img, ["NA", "BRZAKA"], hi=("BRZAKA",), size=64, y=660)
    save(img, "mock_s4_snap")


# ----------------------------------------------------------- S5 CHAT TAKEOVER
def chat():
    img = load("7.6")
    img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 70)))
    msgs = [("marko_bjj", "BRAVOOO ŠAMPIONE", "🏆"), ("ana.grappling", "legenda", "🔥"),
            ("nikola_92", "kakav submission!!", "😱"), ("jiu_jitsu_bg", "aplauz za majstora", "👏"),
            ("stefan.mma", "10/10", "💯")]
    y = 300
    fu = font("Bold", 14, display=False); fm = font("SemiBold", 19, display=False)
    for i, (u, m, e) in enumerate(msgs):
        d0 = ImageDraw.Draw(img)
        tw = max(d0.textlength(u, font=fu), d0.textlength(m, font=fm) + 34)
        b = Image.new("RGBA", (int(tw + 70), 62), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([0, 0, b.width - 1, 61], radius=20, fill=(20, 20, 22, 205), outline=(255, 255, 255, 40))
        bd.ellipse([10, 13, 46, 49], fill=[(232, 36, 28), (90, 90, 255), (255, 170, 0), (60, 200, 120), (200, 80, 200)][i])
        bd.text((56, 9), u, font=fu, fill=(200, 200, 205))
        bd.text((56, 29), m, font=fm, fill=WHITE)
        b.alpha_composite(emoji(e, 24), (int(56 + bd.textlength(m, font=fm) + 8), 30))
        sc = 0.88 + 0.03 * i
        b = b.resize((int(b.width * sc), int(b.height * sc)), Image.LANCZOS)
        paste_shadowed(img, b, (24 + (i % 2) * 40, y), off=(0, 6), blur=10, alpha=120)
        y += 70
    for k in range(9):
        e = emoji(random.choice("👏👏👏❤🔥"), random.randint(26, 46))
        e = e.rotate(random.randint(-25, 25), expand=True)
        img.alpha_composite(e, (random.randint(360, 500), random.randint(160, 650)))
    caption(img, ["APLAUDIRAJU"], hi=("APLAUDIRAJU",), size=52, y=740)
    save(img, "mock_s5_chat")


# ------------------------------------------------------------ S6 LIQUID GLASS
def glass():
    img = load("9.4")
    x0, y0, x1, y1 = 40, 560, 500, 790
    region = img.crop((x0 - 20, y0 - 20, x1 + 20, y1 + 20)).filter(ImageFilter.GaussianBlur(16))
    region = ImageEnhance.Brightness(region).enhance(1.25)
    pm = Image.new("L", region.size, 0); ImageDraw.Draw(pm).rounded_rectangle([20, 20, region.width - 21, region.height - 21], radius=34, fill=255)
    sh = Image.new("RGBA", region.size, (0, 0, 0, 0)); sh.putalpha(pm)
    paste_shadowed(img, Image.new("RGBA", region.size, (0, 0, 0, 0)), (x0 - 20, y0 - 20))
    img.paste(region, (x0 - 20, y0 - 20), pm)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle([x0, y0, x1, y1], radius=34, fill=(255, 255, 255, 34), outline=(255, 255, 255, 120), width=2)
    # specular highlight
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); hd = ImageDraw.Draw(hl)
    hd.rounded_rectangle([x0 + 8, y0 + 6, x1 - 8, y0 + 50], radius=26, fill=(255, 255, 255, 46))
    ov.alpha_composite(hl.filter(ImageFilter.GaussianBlur(6)))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    d.text((x0 + 28, y0 + 22), "TAKMIČENJE", font=font("Bold", 18, display=False), fill=(255, 255, 255, 220))
    d.text((x1 - 110, y0 + 22), "● 04:32", font=font("SemiBold", 18, display=False), fill=RED)
    d.text((x0 + 28, y0 + 60), "2", font=font("Black", 96), fill=WHITE)
    d.text((x0 + 120, y0 + 92), "–", font=font("Black", 50), fill=(255, 255, 255, 150))
    d.text((x0 + 170, y0 + 60), "0", font=font("Black", 96), fill=(255, 255, 255, 170))
    for i, (k, v) in enumerate([("ADV", "1"), ("PEN", "0"), ("SUB", "?")]):
        d.text((x0 + 300, y0 + 72 + i * 38), k, font=font("Medium", 17, display=False), fill=(255, 255, 255, 170))
        d.text((x0 + 370, y0 + 68 + i * 38), v, font=font("Black", 22), fill=WHITE if v != "?" else RED)
    caption(img, ["KAO", "NA", "TAKMIČENJU"], hi=("TAKMIČENJU",), y=820, size=42)
    save(img, "mock_s6_glass")


# ------------------------------------------------------------- S7 DOLLY ZOOM
def dolly():
    src = load("10.6")
    m = mask(src)
    # background (clean plate approximation): blur + stretch outward
    bgp = src.filter(ImageFilter.GaussianBlur(3))
    bg2 = bgp.resize((int(W * 1.35), int(H * 1.35)), Image.LANCZOS)
    bg2 = bg2.crop(((bg2.width - W) // 2, (bg2.height - H) // 3, (bg2.width - W) // 2 + W, (bg2.height - H) // 3 + H))
    bg2 = ImageEnhance.Brightness(bg2).enhance(0.75)
    # warp streaks to suggest the vertigo pull
    acc = np.zeros((H, W, 4), np.float32)
    for i in range(6):
        s = 1 + i * 0.025
        t = bg2.resize((int(W * s), int(H * s)), Image.BILINEAR)
        acc += np.asarray(t.crop(((t.width - W) // 2, (t.height - H) // 2, (t.width - W) // 2 + W, (t.height - H) // 2 + H)), np.float32)
    bg2 = Image.fromarray((acc / 6).astype(np.uint8), "RGBA")
    img = bg2
    person = src.copy(); person.putalpha(m)
    rim = Image.new("RGBA", (W, H), RED + (0,)); rim.putalpha(m.filter(ImageFilter.MaxFilter(9)).point(lambda v: v // 2))
    img.alpha_composite(rim.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(person)
    d = ImageDraw.Draw(img)
    for (a, b) in [((40, 120), (12, 80)), ((500, 120), (528, 80)), ((40, 880), (12, 920)), ((500, 880), (528, 920))]:
        d.line([a, b], fill=(255, 255, 255, 200), width=3)
    d.text((22, 56), "BG ↗ 135%   SUBJECT = 100%", font=font("SemiBold", 13, display=False), fill=WHITE)
    caption(img, ["JER", "MORA", "UVEK"], hi=("MORA", "UVEK"), y=760, size=56)
    save(img, "mock_s7_dolly")


# ------------------------------------------------------------- T2 FRAME BREAK
def frame_break():
    close = load("10.6"); wide = load("13.5")
    img = wide.copy()
    cx, cy = 300, 380
    rings = [0, 90, 230, 420, 900]
    angs = sorted(random.uniform(0, 2 * math.pi) for _ in range(11))
    for ri in range(len(rings) - 1):
        for ai in range(len(angs)):
            a0, a1 = angs[ai], angs[(ai + 1) % len(angs)] + (2 * math.pi if ai == len(angs) - 1 else 0)
            r0, r1 = rings[ri], rings[ri + 1]
            j = lambda r: r * random.uniform(0.9, 1.1)
            poly = [(cx + j(r0) * math.cos(a0), cy + j(r0) * math.sin(a0)), (cx + j(r1) * math.cos(a0), cy + j(r1) * math.sin(a0)),
                    (cx + j(r1) * math.cos(a1), cy + j(r1) * math.sin(a1)), (cx + j(r0) * math.cos(a1), cy + j(r0) * math.sin(a1))]
            pm = Image.new("L", (W, H), 0); ImageDraw.Draw(pm).polygon(poly, fill=255)
            if ri == 0 or random.random() < 0.25:
                continue  # shards already gone -> wide shot shows through
            shard = close.copy(); shard.putalpha(pm)
            bb = pm.getbbox()
            if not bb: continue
            shard = shard.crop(bb)
            am = (a0 + a1) / 2; push = 14 + ri * 22
            sr = shard.rotate(random.uniform(-9, 9), expand=True, resample=Image.BICUBIC)
            edge = Image.new("RGBA", sr.size, (255, 255, 255, 0)); edge.putalpha(sr.split()[-1].filter(ImageFilter.FIND_EDGES).point(lambda v: min(255, v * 3)))
            pos = (int(bb[0] + push * math.cos(am)), int(bb[1] + push * math.sin(am)))
            paste_shadowed(img, sr, pos, off=(0, 8), blur=8, alpha=160)
            img.alpha_composite(edge, pos)
    flash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(flash).ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(255, 255, 255, 110))
    img.alpha_composite(flash.filter(ImageFilter.GaussianBlur(30)))
    save(img, "mock_t2_framebreak")


# ------------------------------------------------------------ S8 CHECKLIST POP
def checklist():
    base = load("14.8")
    z = 1.1
    big = base.resize((int(W * z), int(H * z)), Image.LANCZOS)
    img = big.crop(((big.width - W) // 2, 30, (big.width - W) // 2 + W, 30 + H))
    img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 40)))
    items = [("SPORTSKI DEO", True, 1.0), ("REALNI DEO", True, 1.08), ("= PRIMENA", None, 1.0)]
    y = 150
    for txt, chk, sc in items:
        f = font("Black", 32)
        tw = ImageDraw.Draw(img).textlength(txt, font=f)
        card = Image.new("RGBA", (int(tw + 104), 70), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, card.width - 1, 69], radius=18, fill=(255, 255, 255, 245) if chk else (232, 36, 28, 245))
        if chk:
            cd.ellipse([14, 14, 56, 56], fill=RED)
            cd.line([(24, 36), (33, 45), (47, 25)], fill=WHITE, width=6, joint="curve")
            cd.text((72, 13), txt, font=f, fill=(16, 16, 16))
        else:
            cd.text((24, 13), txt, font=f, fill=WHITE)
        card = card.resize((int(card.width * sc), int(card.height * sc)), Image.LANCZOS)
        paste_shadowed(img, card, (34, y), off=(0, 10), blur=14, alpha=150)
        y += 92
    d = ImageDraw.Draw(img)
    d.text((40, 120), "TA PARALELA:", font=font("Bold", 18, display=False), fill=(255, 255, 255, 210))
    caption(img, ["REALNOG", "DELA"], hi=("REALNOG",), y=760, size=48)
    save(img, "mock_s8_checklist")


# ------------------------------------------------------------ END MAGAZINE COVER
def magazine():
    src = load("10.6")
    m = mask(src)
    img = ImageEnhance.Brightness(src).enhance(0.55)
    img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (60, 0, 0, 90)))
    d = ImageDraw.Draw(img)
    mf = font("Black", 132)
    tw = d.textlength("JIU-JITSU", font=mf)
    sc = (W - 30) / tw
    mast = Image.new("RGBA", (int(tw + 10), 170), (0, 0, 0, 0))
    ImageDraw.Draw(mast).text((0, 0), "JIU-JITSU", font=mf, fill=WHITE)
    mast = mast.resize((int(mast.width * sc), int(mast.height * sc)), Image.LANCZOS)
    img.alpha_composite(mast, (15, 70))
    person = src.copy(); person.putalpha(m.point(lambda v: v if v > 0 else 0))
    # only let the head overlap the masthead (classic cover depth)
    pt = Image.new('RGBA', (W, H), (0, 0, 0, 0)); pt.alpha_composite(person, (0, 70))
    img.alpha_composite(pt)
    d = ImageDraw.Draw(img)
    d.text((300, 22), "BR. 01  ·  JIU-JITSU TALKS", font=font("SemiBold", 13, display=False), fill=(255, 255, 255, 220))
    d.rectangle([18, 560, 30, 702], fill=RED)
    d.text((42, 556), "SPORT", font=font("Black", 44), fill=WHITE)
    d.text((42, 604), "vs. REALNOST", font=font("Black", 34), fill=WHITE)
    d.rectangle([42, 646, 290, 650], fill=RED)
    d.text((42, 660), "Znati tehniku znači razumeti", font=font("Medium", 17, display=False), fill=WHITE)
    d.text((42, 682), "i kada…", font=font("Medium", 17, display=False), fill=WHITE)
    pill = [300, 840, 515, 892]
    d.rounded_rectangle(pill, radius=26, fill=WHITE)
    d.text((322, 853), "NASTAVAK  →", font=font("Black", 22), fill=(16, 16, 16))
    for i in range(28):  # barcode
        w = random.choice([1, 2, 3])
        d.rectangle([24 + i * 4, 850, 24 + i * 4 + w, 900], fill=WHITE)
    save(img, "mock_end_magazine")


for fn in (orbit, paper, portal, snap, chat, glass, dolly, frame_break, checklist, magazine):
    fn(); print("done", fn.__name__)
