"""Generates the storyboard HTML. Usage: python3 -I build_page.py <out.html>"""
import sys, html

FPS = 30
def tc(s):
    f = round(s * FPS); return f"{f//(FPS*3600):02d}:{f//(FPS*60)%60:02d}:{f//FPS%60:02d}:{f%FPS:02d}"
def sh(s):
    return f"{s:05.2f}s"
E = html.escape

# Kept source ranges (src_in, src_out) -> output is contiguous
SEGS = [(0.00, 1.62), (2.00, 4.95), (5.25, 8.75), (9.02, 12.25), (12.60, 16.55), (16.82, 19.07)]
OUTMAP = []
acc = 0
for a, b in SEGS:
    OUTMAP.append((a, b, acc)); acc += b - a
BODY_END = acc
END_CARD = 2.0
TOTAL = BODY_END + END_CARD
def o(src):
    for a, b, off in OUTMAP:
        if a - 1e-6 <= src <= b + 1e-6:
            return off + src - a
    raise ValueError(src)

SCENES = [
 dict(id="S1", name="Hook", src=(0.00, 1.62), shot="Wide A", fx=["Orbit"], frame="1.0", mock="mock_s1_orbit",
      sr='„Jer jiu-jitsu nije neka…“', en="“Because jiu-jitsu isn't some…”",
      why="The first frame has to stop the scroll. The topic word orbits the speaker's head, so the viewer knows what this is about before he finishes the first word.",
      anim=[("00:00:00:00", "Ring of “JIU-JITSU •” scales 0→100% (8 fr, ease-out back). 12° tilt, one revolution per 2.4 s."),
            ("00:00:00:00 → end", "Back half of the ring passes behind the head (roto mask on a duplicate V2 layer). Slow push on V1, 100→106%."),
            ("Captions", "“JER” then “JIU-JITSU” pops in a red pill.")],
      sfx="Sub hit + airy swirl whoosh on frame 0. Music bed starts with a downbeat.",
      nxt="Paper-tear wipe (6 fr) on the camera change. The 0.38 s breath between “neka” and “skočimiš” is cut here, so the jump cut lands on a real angle change and disappears."),
 dict(id="S2", name="The mocking quote", src=(2.00, 3.20), shot="Wide B", fx=["Paper Cutout"], frame="2.6", mock="mock_s2_paper",
      sr='„…„skočimiš“ varijanta.“', en="“…some ‘jump-on-me’ kind of thing.”",
      why="He's quoting a cliché sarcastically. A hand-made collage look marks the phrase as a quote and changes the texture early, which keeps the edit fresh.",
      anim=[(tc(o(2.00)), "Background swaps to a paper texture with a torn red strip. The speaker becomes a sticker (roto, 8 px white border, drop shadow). Posterize Time 12 fps gives a stop-motion feel."),
            (tc(o(2.20)), "„SKOČIMIŠ“ black label slams in: scale 130→100%, +4° rotation, 4 fr."),
            (tc(o(2.60)), "VARIJANTA yellow label and a “?!” sticker slam in, offset by 3 fr.")],
      sfx="Paper rustle under the swap, two rubber-stamp thuds on the labels.",
      nxt="The sticker peels off the top-left corner and reveals live video underneath (8 fr), straight into S3."),
 dict(id="S3", name="The imagined move", src=(3.20, 4.95), shot="Wide B", fx=["Zoom Portal", "B-roll Overlay"], frame="4.2", mock="mock_s3_portal",
      sr='„Aha, sad ću ja da skočim i da napravim neki…“', en="“Aha, now I'll jump in and pull off some…”",
      why="He describes a fantasy move. Showing that move is the most direct visual. The portal sits in the dark shelf area, so it never covers his face.",
      anim=[(tc(o(3.45)), "On “sad ću”, a red-rimmed circular portal opens in the dark shelf area (scale 0→100%, 10 fr), with a B-roll flying armbar playing inside."),
            (tc(o(4.20)), "On “napravim”, the camera pushes through the portal (V1 + portal 100→420%, ease-in, 9 fr). The B-roll fills the frame."),
            (tc(o(4.95)) + " (jump cut)", "The 0.30 s hesitation (“neki … submission”) is removed while the B-roll is full-frame, so nobody sees the cut.")],
      sfx="Low portal hum, then a reverse-suck whoosh into the push.",
      nxt="B-roll runs full-frame through “submission” and snaps back to the speaker on “na brzaka” (S4)."),
 dict(id="S4", name="“Real quick”", src=(5.25, 6.77), shot="Wide B", fx=["Snap Zoom"], frame="6.3", mock="mock_s4_snap",
      sr='„…submission onako na brzaka,“', en="“…some submission, real quick,”",
      why="“Na brzaka” means fast. A 3-frame punch-in is the visual version of that word and the punchline of his sarcasm.",
      anim=[(tc(o(5.25)), "B-roll is full-frame under “submission”."),
            (tc(o(5.95)), "Hard cut back to the speaker at 100%, then a 3-frame snap to 138% (center on face) with a radial blur on frames 1–2, and hold."),
            ("Caption", "“NA BRZAKA” at 64 px, the largest caption in the video.")],
      sfx="Camera-shutter snap + short tight whoosh, timed to the first frame of the punch.",
      nxt="Zoom-through cut at " + tc(o(6.77)) + ": the wide shot keeps zooming 138→220% with motion blur over 4 fr. The close-up enters at 160% and settles to 100% over 6 fr."),
 dict(id="S5", name="Imaginary applause", src=(6.77, 8.75), shot="Close-up", fx=["Zoom Through Cut (in)", "Chat Takeover"], frame="7.6", mock="mock_s5_chat",
      sr='„…svi će oni da mi aplaudiraju, znaš,“', en="“…and they'll all applaud me, you know,”",
      why="The applause is imagined and ironic. A flood of over-the-top comments plays the irony the way the target audience sees it every day.",
      anim=[(tc(o(6.85)), "Background dims 30% with a 6 px blur. Comment bubbles rise from the lower left, one every 5 fr, each scaling 80→100%."),
            (tc(o(7.40)), "On “aplaudiraju”, 👏/🔥/❤ particles burst from the right edge, peak density."),
            (tc(o(8.40)), "On “znaš”, every bubble swipes off left in 6 fr and the blur clears.")],
      sfx="Rising-pitch notification pings, one per bubble. A light crowd-applause bed at −24 dB fades out on “znaš”.",
      nxt="The Liquid Glass panel slides up as the bubbles leave (4 fr overlap), hiding the 0.27 s pause cut after “znaš”."),
 dict(id="S6", name="Competition", src=(9.02, 10.00), shot="Close-up", fx=["Liquid Glass"], frame="9.4", mock="mock_s6_glass",
      sr='„…kao na takmičenju.“', en="“…like at a competition.”",
      why="It names the context: the scoreboard world of sport jiu-jitsu. Frosted glass keeps his face visible behind the panel and looks premium without heavy colour.",
      anim=[(tc(o(9.02)), "Frosted panel (40 px background blur, 14% white, 1 px highlight stroke) rises 60 px with ease-out over 10 fr. A specular light sweep crosses it once."),
            (tc(o(9.30)), "Score ticks 0→2 and the match timer runs. ADV / PEN / SUB rows fade in, with SUB shown as “?” in red.")],
      sfx="Glass tick on entry, scoreboard beep on the score tick, short referee whistle at −18 dB.",
      nxt="The panel scales to 90% and dissolves (6 fr) as “JER MORA UVEK” comes up. Every graphic clears for the thesis."),
 dict(id="S7", name="The thesis", src=(10.00, 12.25), shot="Close-up", fx=["Dolly Zoom"], frame="10.6", mock="mock_s7_dolly",
      sr='„Jer mora uvek da se napravi ta paralela između…“', en="“Because you always have to draw that parallel between…”",
      why="This is the most important sentence. A slow vertigo pull with no other graphics gives it weight. It is the calmest shot in the edit, on purpose.",
      anim=[(tc(o(10.00)) + " → " + tc(o(12.25)), "Subject layer (roto) holds at 100%. The background plate scales 100→135% with ease-in-out. A soft red rim glow builds around the subject."),
            ("Caption", "“MORA UVEK” in a double red pill at 56 px.")],
      sfx="Low sub drone with a reverse-cymbal riser that peaks into the frame break.",
      nxt="Frame Break at " + tc(o(12.25)) + ": the close-up freezes for 2 fr, cracks from an impact point near the mouth, and the shards fly outward (10 fr) to reveal the wide shot. This also hides the 0.35 s pause cut."),
 dict(id="S8", name="Sport vs. reality", src=(12.60, 16.55), shot="Wide B", fx=["Frame Break (in)", "Checklist Pop", "Digital Zoom"], frame="14.8", mock="mock_s8_checklist", extra_mock="mock_t2_framebreak", extra_frame="13.5",
      sr='„…sportskog dela, realnog dela, to jest primene toga svega što radiš.“', en="“…the sport side and the real side, meaning the application of everything you do.”",
      why="He lists the two halves of the parallel, then the conclusion. A checklist that builds item by item turns his structure into something the viewer can see.",
      anim=[(tc(o(12.60)), "Shards clear. “TA PARALELA:” label fades in. Slow digital push 100→112% across the whole scene (keyframed Scale, ease)."),
            (tc(o(12.80)), "Card 1 “✓ SPORTSKI DEO” pops 0→108→100% (8 fr). The check stroke draws on in 6 fr."),
            (tc(o(14.00)), "Card 2 “✓ REALNI DEO” pops."),
            (tc(o(14.60)), "Card 3 “= PRIMENA” pops in solid red. Cards 1–2 dim to 60%.")],
      sfx="Glass shatter + bass hit on the break. Two soft pop + check ticks, and a bright ding on PRIMENA.",
      nxt="Cards fly off upward, staggered (2 fr each), as he says “tako da”. The cut over the 0.27 s pause lands under the card exit."),
 dict(id="S9", name="Payoff → end card", src=(16.82, 19.07), shot="Wide C", fx=["Magazine Cover"], frame="18.4", mock="mock_end_magazine",
      sr='„Tako da, ako ga treniraš i dan danas…“', en="“So if you train it, even to this day…”",
      why="The clip ends mid-sentence. Instead of cutting off abruptly, it freezes into a cover that reframes the cutoff as a cliffhanger (“NASTAVAK →”) and a strong loop point.",
      anim=[(tc(o(16.82)), "Push back out 112→100% while a light sweep crosses the red neon. Music swells."),
            (tc(BODY_END) + " → " + tc(TOTAL), "On “danas”: white flash (2 fr) and a freeze on the close-up portrait. “JIU-JITSU” masthead slams down behind the head (roto overlap). Cover lines type on and the “NASTAVAK →” pill pops last.")],
      sfx="Camera-flash pop + impact hit on the freeze. The music lands its final hit and rings out.",
      nxt="End of video. The final cover frame works as a loop back into the S1 hook."),
]

EFFECTS = [
 ("Orbit", "used", "S1", "Hook. The topic word circles the speaker."),
 ("Chat Takeover", "used", "S5", "Plays the ironic “everyone will applaud me”."),
 ("Frame Escape", "no", "—", "It would be the fourth roto effect in 4 seconds. At this resolution, the mask edges breaking the frame look rough."),
 ("Snap Zoom", "used", "S4", "Visualises “na brzaka” (real quick)."),
 ("Checklist Pop", "used", "S8", "Builds sport → reality → application."),
 ("Headline Storm", "no", "—", "There are no headlines in a personal opinion clip. Made-up press headlines would be misleading."),
 ("Zoom Portal", "used", "S3", "Opens into the imagined flying submission."),
 ("Growth Curve", "no", "—", "No data, numbers or progress in the speech, so a curve would be decoration."),
 ("Studio Reveal", "no", "—", "Needs footage wider than the shot. Our crop is already tighter than the source. Possible with the original master."),
 ("B-roll Overlay", "used", "S3–S4", "Shows the move he describes. Needs a clip from you (see decisions)."),
 ("Paper Cutout", "used", "S2", "Marks the sarcastic quote “skočimiš varijanta”."),
 ("Dolly Zoom", "used", "S7", "Gives weight to the thesis sentence."),
 ("Magazine Cover", "used", "End", "Turns the mid-sentence cutoff into a cliffhanger end card."),
 ("Liquid Glass", "used", "S6", "Scoreboard for “kao na takmičenju”."),
 ("Zoom Through Cut", "used", "S4→S5", "Carries energy across the wide → close-up angle change."),
 ("Green Screen", "no", "—", "No keyable footage. Replacing the real studio would hurt authenticity."),
 ("Frame Break", "used", "S7→S8", "Breaks out of the thesis into the explanation, and hides a pause cut."),
 ("Digital Zoom", "used", "S8", "Slow push that keeps the long wide shot alive."),
 ("Phone Mockup", "no", "—", "The source is already a phone screen recording. Framing it in a phone again draws attention to the low resolution."),
 ("Checklist", "no", "—", "Same job as Checklist Pop. One checklist per 19 s."),
]

TRANSCRIPT = [
 (0.00, "Jer jiu-jitsu nije neka", "Because jiu-jitsu isn't some"),
 (2.20, "„skočimiš“ varijanta —", "“jump-on-me” kind of thing —"),
 (3.20, "aha, sad ću ja da skočim i da napravim", "“aha, now I'll jump in and pull off"),
 (4.80, "neki submission onako na brzaka,", "some submission real quick,"),
 (6.80, "svi će oni da mi aplaudiraju, znaš,", "and they'll all applaud me,” you know,"),
 (8.40, "kao na takmičenju.", "like at a competition."),
 (10.00, "Jer mora uvek da se napravi ta paralela između", "Because you always have to draw that parallel between"),
 (12.80, "sportskog dela, realnog dela,", "the sport side and the real side,"),
 (14.40, "to jest primene toga svega što radiš.", "meaning the application of everything you do."),
 (16.00, "Tako da, ako ga treniraš i dan danas…", "So if you train it, even to this day…"),
]

PAUSES = [(1.62, 2.00), (4.95, 5.25), (8.75, 9.02), (12.25, 12.60), (16.55, 16.82)]

# ---------- timeline SVG ----------
def timeline_svg():
    Wd, X0 = 980, 92
    sc = (Wd - X0 - 10) / TOTAL
    x = lambda t: X0 + t * sc
    rows = [("V5 Captions", 18), ("V3–V4 Graphics", 50), ("V1 Picture", 82), ("A2–A3 SFX", 114), ("A4 Music", 146)]
    out = [f'<svg viewBox="0 0 {Wd} 196" role="img" aria-label="Timeline overview">']
    for lab, y in rows:
        out.append(f'<text x="0" y="{y+17}" class="tl-lab">{E(lab)}</text>')
        out.append(f'<rect x="{X0}" y="{y}" width="{Wd-X0-10}" height="26" rx="3" class="tl-lane"/>')
    # picture segments
    for a, b, off in OUTMAP:
        out.append(f'<rect x="{x(off):.1f}" y="82" width="{(b-a)*sc-1.5:.1f}" height="26" rx="3" class="tl-clip"/>')
        out.append(f'<text x="{x(off)+4:.1f}" y="99" class="tl-txt">{a:.2f}–{b:.2f}</text>')
    out.append(f'<rect x="{x(BODY_END):.1f}" y="82" width="{END_CARD*sc-1:.1f}" height="26" rx="3" class="tl-end"/>')
    out.append(f'<text x="{x(BODY_END)+4:.1f}" y="99" class="tl-txt-on">freeze</text>')
    # graphics
    for s in SCENES:
        a = o(s["src"][0]); b = o(s["src"][1]) if s["id"] != "S9" else TOTAL
        out.append(f'<rect x="{x(a)+1:.1f}" y="50" width="{(b-a)*sc-3:.1f}" height="26" rx="3" class="tl-fx"/>')
        out.append(f'<text x="{x(a)+5:.1f}" y="67" class="tl-txt-on">{s["id"]}</text>')
    # captions chunks
    for t, *_ in TRANSCRIPT:
        try: tt = o(t)
        except ValueError: tt = o(t + 0.4)
        out.append(f'<rect x="{x(tt):.1f}" y="18" width="{1.2*sc:.1f}" height="26" rx="3" class="tl-cap"/>')
    # sfx hits
    for t in [0, o(2.0), o(3.45), o(4.2), o(5.95), o(6.77), o(6.9), o(7.4), o(9.02), o(9.3), o(12.25), o(12.8), o(14.0), o(14.6), BODY_END]:
        out.append(f'<rect x="{x(t)-1.5:.1f}" y="118" width="3" height="18" rx="1.5" class="tl-hit"/>')
    out.append(f'<rect x="{X0}" y="146" width="{(TOTAL)*sc:.1f}" height="26" rx="3" class="tl-music"/>')
    for t, l in [(0, "downbeat"), (o(12.25), "drop"), (BODY_END, "final hit")]:
        out.append(f'<text x="{x(t)+4:.1f}" y="163" class="tl-txt">▲ {l}</text>')
    # cuts (pause removals)
    for a, b in PAUSES:
        t = o(a)
        out.append(f'<line x1="{x(t):.1f}" y1="12" x2="{x(t):.1f}" y2="176" class="tl-cut"/>')
    # ruler
    for s in range(0, int(TOTAL) + 1):
        out.append(f'<line x1="{x(s):.1f}" y1="178" x2="{x(s):.1f}" y2="{184 if s%5 else 188}" class="tl-tick"/>')
        if s % 2 == 0:
            out.append(f'<text x="{x(s):.1f}" y="196" class="tl-ruler" text-anchor="middle">{s}s</text>')
    out.append('</svg>')
    return "\n".join(out)

def scene_card(s):
    a, b = s["src"]
    oa, ob = o(a), (o(b) if s["id"] != "S9" else TOTAL)
    fx = "".join(f'<span class="chip">{E(f)}</span>' for f in s["fx"])
    rows = "".join(f'<tr><td class="mono">{E(t)}</td><td>{E(d)}</td></tr>' for t, d in s["anim"])
    extra = ""
    if s.get("extra_mock"):
        extra = f'''<figure><img src="sb/{s["extra_mock"]}.jpg" alt="Concept mockup of the frame break transition" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-mock">Concept mockup</b> Frame Break transition</figcaption></figure>'''
    return f'''
<article class="scene" id="{s["id"].lower()}">
  <header class="scene-head">
    <div class="scene-id">{s["id"]}</div>
    <div class="scene-title"><h3>{E(s["name"])}</h3><div class="fxrow">{fx}</div></div>
    <dl class="tcs">
      <div><dt>Output</dt><dd class="mono">{tc(oa)} → {tc(ob)}</dd></div>
      <div><dt>Source</dt><dd class="mono">{sh(a)} → {sh(b)} · {E(s["shot"])}</dd></div>
    </dl>
  </header>
  <div class="scene-body">
    <div class="frames">
      <figure><img class="src" src="sb/orig_{s["frame"]}.jpg" alt="Original frame from the source recording at {s["frame"]} seconds" loading="lazy" width="438" height="948"><figcaption><b class="tag tag-real">Source frame</b> {s["frame"]} s, unedited</figcaption></figure>
      <figure><img src="sb/{s["mock"]}.jpg" alt="Concept mockup of {E(s["fx"][-1])}" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-mock">Concept mockup</b> still, not a render</figcaption></figure>
      {extra}
    </div>
    <div class="notes">
      <blockquote><p lang="sr">{E(s["sr"])}</p><p class="en">{E(s["en"])}</p></blockquote>
      <h4>Why this effect</h4><p>{E(s["why"])}</p>
      <h4>Animation &amp; timing</h4>
      <div class="tbl"><table class="anim">{rows}</table></div>
      <h4>Sound</h4><p>{E(s["sfx"])}</p>
      <h4>Into the next scene</h4><p>{E(s["nxt"])}</p>
    </div>
  </div>
</article>'''

def transcript_rows():
    r = []
    for t, sr, en in TRANSCRIPT:
        r.append(f'<tr><td class="mono">{sh(t)}</td><td lang="sr">{E(sr)}</td><td class="en">{E(en)}</td></tr>')
    return "\n".join(r)

def effects_rows():
    r = []
    for i, (n, st, where, why) in enumerate(EFFECTS, 1):
        cls = "ok" if st == "used" else "no"
        lab = "Used" if st == "used" else "Not used"
        r.append(f'<tr><td class="mono num">{i}</td><td><b>{E(n)}</b></td><td><span class="state {cls}">{lab}</span></td><td class="mono">{E(where)}</td><td>{E(why)}</td></tr>')
    return "\n".join(r)

used = sum(1 for e in EFFECTS if e[1] == "used")
cut_total = sum(b - a for a, b in PAUSES)

page = f'''<title>Jiu-Jitsu Reel Storyboard</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500;62..125,800;62..125,900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* Layout: an edit-suite document. A narrow reading column for decisions, wide scene sheets that pair the real frame with the mockup, and a timeline band styled like a sequence panel. */
:root {{
  --bg: #F5F4F3; --surface: #FFFFFF; --sunk: #ECEAE8; --fg: #171314; --muted: #675E60; --line: #DDD8D6;
  --accent: #C81E17; --accent-ink: #FFFFFF; --real: #1F7A4D; --mock: #9A6A00; --mock-bg: #FFE7A8; --real-bg: #D8F0E2;
  --clip: #3C5A8C; --fx: #C81E17; --cap: #6F6A6B; --music: #2F6E5A;
  --f-display: "Archivo", "Arial Narrow", system-ui, sans-serif;
  --f-body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #121011; --surface: #1B1819; --sunk: #0D0B0C; --fg: #EEEAEA; --muted: #A39A9C; --line: #2E292B;
  --accent: #F0372E; --accent-ink: #FFFFFF; --real: #5BD49A; --mock: #FFC53D; --mock-bg: #3A2C05; --real-bg: #0F3324;
  --clip: #5B7DB8; --fx: #E8342B; --cap: #8D8789; --music: #3F8F75; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #121011; --surface: #1B1819; --sunk: #0D0B0C; --fg: #EEEAEA; --muted: #A39A9C; --line: #2E292B;
  --accent: #F0372E; --accent-ink: #FFFFFF; --real: #5BD49A; --mock: #FFC53D; --mock-bg: #3A2C05; --real-bg: #0F3324;
  --clip: #5B7DB8; --fx: #E8342B; --cap: #8D8789; --music: #3F8F75; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-body); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 80px; display: grid; gap: 56px; }}
h1, h2, h3 {{ font-family: var(--f-display); text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(34px, 6vw, 60px); font-weight: 900; font-stretch: 72%; line-height: .95; letter-spacing: -.01em; text-transform: uppercase; }}
h2 {{ font-size: clamp(22px, 3vw, 30px); font-weight: 800; font-stretch: 85%; text-transform: uppercase; letter-spacing: .01em; }}
h3 {{ font-size: 22px; font-weight: 800; font-stretch: 90%; }}
h4 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 18px 0 4px; font-weight: 600; }}
p {{ margin: 0; max-width: 68ch; }}
.mono {{ font-family: var(--f-mono); font-size: 12.5px; font-variant-numeric: tabular-nums; }}
.eyebrow {{ font-family: var(--f-mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
.hero {{ display: grid; gap: 18px; }}
.status {{ display: inline-flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13px; padding: 6px 12px; border-radius: 99px; background: var(--accent); color: var(--accent-ink); justify-self: start; }}
.status::before {{ content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }}
.facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
.facts div {{ background: var(--surface); padding: 12px 14px; min-width: 0; }}
.facts dt {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
.facts dd {{ margin: 2px 0 0; font-family: var(--f-mono); font-size: 14px; font-weight: 600; }}
section {{ display: grid; gap: 18px; }}
.sec-head {{ display: grid; gap: 6px; border-top: 2px solid var(--fg); padding-top: 12px; }}
.decisions {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
.decision {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 8px; align-content: start; min-width: 0; }}
.decision h3 {{ font-size: 17px; font-stretch: 100%; }}
.decision .sev {{ font-family: var(--f-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--accent); font-weight: 600; }}
.decision ul {{ margin: 0; padding-left: 18px; display: grid; gap: 4px; }}
.tbl {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ text-align: left; vertical-align: top; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 600; }}
td.en, .en {{ color: var(--muted); }}
.timeline {{ background: var(--sunk); border: 1px solid var(--line); border-radius: 10px; padding: 16px; overflow-x: auto; }}
.timeline svg {{ min-width: 760px; width: 100%; height: auto; display: block; }}
.tl-lab {{ font: 600 11px var(--f-body); fill: var(--muted); }}
.tl-lane {{ fill: var(--surface); }}
.tl-clip {{ fill: var(--clip); }} .tl-end {{ fill: var(--accent); }} .tl-fx {{ fill: var(--fx); opacity: .85; }}
.tl-cap {{ fill: var(--cap); }} .tl-hit {{ fill: var(--fg); }} .tl-music {{ fill: var(--music); opacity: .8; }}
.tl-txt {{ font: 500 10px var(--f-mono); fill: #FFFFFF; }} .tl-txt-on {{ font: 600 10px var(--f-mono); fill: #FFFFFF; }}
.tl-cut {{ stroke: var(--accent); stroke-width: 1.2; stroke-dasharray: 3 3; }}
.tl-tick {{ stroke: var(--muted); }} .tl-ruler {{ font: 500 10px var(--f-mono); fill: var(--muted); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; color: var(--muted); }}
.legend span {{ display: inline-flex; gap: 6px; align-items: center; }}
.legend i {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
.scenes {{ display: grid; gap: 28px; }}
.scene {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }}
.scene-head {{ display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--line); }}
.scene-id {{ font-family: var(--f-display); font-weight: 900; font-stretch: 70%; font-size: 40px; line-height: 1; color: var(--accent); }}
.scene-title {{ min-width: 0; display: grid; gap: 6px; }}
.fxrow {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 99px; border: 1px solid var(--accent); color: var(--accent); }}
.tcs {{ margin: 0; display: grid; gap: 4px; text-align: right; }}
.tcs dt {{ display: inline; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-right: 8px; }}
.tcs dd {{ display: inline; margin: 0; }}
.scene-body {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 22px; padding: 18px; }}
.frames {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; align-content: start; }}
figure {{ margin: 0; display: grid; gap: 6px; min-width: 0; }}
figure img {{ width: 100%; height: auto; aspect-ratio: 9 / 16; object-fit: cover; border-radius: 8px; background: var(--sunk); }}
figure img.src {{ aspect-ratio: 292 / 632; object-fit: contain; }}
.frames {{ align-items: start; }}
figcaption {{ font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
.tag {{ font-family: var(--f-mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; padding: 2px 7px; border-radius: 4px; font-weight: 600; }}
.tag-real {{ background: var(--real-bg); color: var(--real); }}
.tag-mock {{ background: var(--mock-bg); color: var(--mock); }}
.tag-render {{ background: var(--sunk); color: var(--fg); border: 1px solid var(--line); }}
.notes {{ min-width: 0; }}
blockquote {{ margin: 0; padding: 12px 14px; border-left: 3px solid var(--accent); background: var(--sunk); border-radius: 0 8px 8px 0; display: grid; gap: 4px; }}
blockquote p:first-child {{ font-weight: 600; font-size: 16px; }}
table.anim td:first-child {{ white-space: nowrap; color: var(--accent); }}
.specs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }}
.spec {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 10px; align-content: start; min-width: 0; }}
.spec h3 {{ font-size: 18px; font-stretch: 100%; }}
.spec ul {{ margin: 0; padding-left: 18px; display: grid; gap: 4px; }}
.kv {{ display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; font-size: 14px; }}
.kv dt {{ color: var(--muted); }} .kv dd {{ margin: 0; font-family: var(--f-mono); font-size: 12.5px; }}
.capdemo {{ background: #141112; border-radius: 8px; padding: 22px 12px; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; font-family: "Inter", sans-serif; font-weight: 900; font-size: 26px; letter-spacing: -.01em; color: #FFFFFF; }}
.capdemo .k {{ background: #E8241C; padding: 0 8px; border-radius: 6px; transform: rotate(-2deg); display: inline-block; }}
.swatches {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.sw {{ display: grid; gap: 4px; font-size: 11px; font-family: var(--f-mono); color: var(--muted); }}
.sw i {{ width: 56px; height: 36px; border-radius: 6px; border: 1px solid var(--line); display: block; }}
.grade {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
.state {{ font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }}
.state.ok {{ background: var(--real-bg); color: var(--real); }}
.state.no {{ background: var(--sunk); color: var(--muted); border: 1px solid var(--line); }}
td.num {{ color: var(--muted); }}
ol.steps {{ margin: 0; padding-left: 22px; display: grid; gap: 6px; max-width: 80ch; }}
.approve {{ background: var(--surface); border: 2px solid var(--accent); border-radius: 12px; padding: 20px; display: grid; gap: 10px; }}
.approve ul {{ margin: 0; padding-left: 18px; display: grid; gap: 6px; }}
a {{ color: var(--accent); }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
@media (max-width: 760px) {{
  .scene-head {{ grid-template-columns: auto 1fr; }}
  .tcs {{ grid-column: 1 / -1; text-align: left; }}
  .scene-body {{ grid-template-columns: 1fr; }}
}}
</style>

<div class="wrap">

<header class="hero">
  <span class="eyebrow">Edit plan v1 · 9:16 short · Serbian dialogue</span>
  <h1>Jiu-jitsu: sport vs. reality</h1>
  <p>A storyboard for a 19.5-second vertical reel built from your clip. It covers the analysis, nine scenes with exact timecodes, {used} of the 20 requested effects, and the captions, sound, and grade. Nothing has been changed in Premiere Pro.</p>
  <span class="status">Waiting for your approval</span>
  <dl class="facts">
    <div><dt>Source</dt><dd>19.07 s · 30 fps</dd></div>
    <div><dt>Source size</dt><dd>292 × 632</dd></div>
    <div><dt>Usable picture</dt><dd>≈ 201 × 357</dd></div>
    <div><dt>Pauses cut</dt><dd>{len(PAUSES)} · {cut_total:.2f} s</dd></div>
    <div><dt>Planned length</dt><dd>{TOTAL:.2f} s</dd></div>
    <div><dt>Delivery</dt><dd>1080 × 1920</dd></div>
  </dl>
</header>

<section id="decisions">
  <div class="sec-head"><span class="eyebrow">Read first</span><h2>Four things that need you</h2></div>
  <div class="decisions">
    <div class="decision"><span class="sev">Blocker for execution</span><h3>Premiere Pro isn't reachable from this session</h3>
      <p>This session runs in a cloud container. It has no Premiere Pro or MCP Bridge tools, and no computer is attached.</p>
      <ul><li><b>Option A:</b> In the Claude desktop app, open Settings → Claude Code → Remote Control and share the project folder. I can then work on your machine where Premiere runs.</li>
      <li><b>Option B (works now):</b> I build every layer here and give you a Premiere-importable XML timeline. That includes the cuts, keyframed zooms, alpha-channel motion graphics, SFX, captions (.srt), and a grade LUT, plus a finished MP4.</li></ul></div>
    <div class="decision"><span class="sev">Quality ceiling</span><h3>The clip is a screen recording of an Instagram story</h3>
      <p>The IG header, like rail, reply bar, and burned-in captions are all part of the pixels. After cropping them out, about 201 × 357 px is left, which means roughly a 5.4× upscale to 1080 × 1920.</p>
      <ul><li><b>Best:</b> send the original podcast file. Every effect will look sharper and Studio Reveal becomes possible.</li>
      <li><b>Fallback:</b> crop + Lanczos upscale + sharpening + grain (shown below). An AI video upscale through Higgsfield is possible but costs credits.</li></ul></div>
    <div class="decision"><span class="sev">Assets</span><h3>B-roll and music</h3>
      <ul><li><b>B-roll (S3–S4):</b> about 2 s of a flying armbar or jumping guard, ideally from your own gym. If there's no clip, I'll replace the portal content with a kinetic-type animation.</li>
      <li><b>Music:</b> I can't download licensed tracks here. Pick a track from Premiere's Essential Sound or Adobe Stock (dark minimal trap, 95–100 BPM), or approve an original bed generated with Higgsfield (uses credits).</li>
      <li><b>SFX:</b> I'll synthesise original whooshes, hits, pops, and the shatter, so no licensing is needed.</li></ul></div>
    <div class="decision"><span class="sev">Rights</span><h3>Account on screen: gbbelgrade &amp; danijelbrajcic</h3>
      <p>Please confirm you have the right to re-edit and repost this clip. The end card handle and CTA text are placeholders until you confirm them.</p></div>
  </div>
</section>

<section id="analysis">
  <div class="sec-head"><span class="eyebrow">1 · Analysis</span><h2>What the clip says</h2></div>
  <p><b>Topic:</b> a coach on a podcast arguing that jiu-jitsu isn't about flashy, fast submissions done for applause like at a competition. You always have to connect the sport side to real-world application.</p>
  <p><b>Structure:</b> setup with a sarcastic quote (0–9 s) → thesis (“mora uvek”, 10–12 s) → the two-part parallel (12.6–16.5 s) → an open ending that stops mid-sentence (“i dan danas…”).</p>
  <p><b>Pace:</b> fast, conversational, almost no dead air. I'll trim only the five breaths of about 0.3 s, and each cut is hidden under a planned effect or camera change. The thesis is deliberately left clean and slow.</p>
  <p><b>Shots in the source:</b> wide A 0–2.0 s · wide B 2.0–6.77 s · close-up 6.77–12.6 s · wide B 12.6–16.5 s · wide C 16.5–19.07 s.</p>
  <h4>Transcript (read from the word-synced captions; speech-to-text models were blocked by this session's network)</h4>
  <div class="tbl"><table><thead><tr><th>Source</th><th>Serbian</th><th>English</th></tr></thead><tbody>
  {transcript_rows()}
  </tbody></table></div>
</section>

<section id="timeline">
  <div class="sec-head"><span class="eyebrow">2 · Structure</span><h2>Sequence at a glance</h2></div>
  <div class="timeline">{timeline_svg()}</div>
  <div class="legend">
    <span><i style="background:var(--clip)"></i>Kept dialogue (source in–out)</span>
    <span><i style="background:var(--fx)"></i>Scene graphics</span>
    <span><i style="background:var(--cap)"></i>Caption chunks</span>
    <span><i style="background:var(--fg)"></i>SFX hit</span>
    <span><i style="background:var(--music)"></i>Music bed</span>
    <span><i style="background:var(--accent)"></i>Dashed: pause removed</span>
  </div>
</section>

<section id="scenes">
  <div class="sec-head"><span class="eyebrow">3 · Storyboard</span><h2>Scene by scene</h2>
  <p>Output timecodes are SMPTE at 30 fps on the edited sequence. Source times are seconds into your .mov. <b class="tag tag-real">Source frame</b> is a real frame from your footage. <b class="tag tag-mock">Concept mockup</b> is a still I composed from that frame to show intent. It is not a render of the final effect.</p></div>
  <div class="scenes">
  {"".join(scene_card(s) for s in SCENES)}
  </div>
</section>

<section id="specs">
  <div class="sec-head"><span class="eyebrow">4 · Look &amp; sound</span><h2>Global specs</h2></div>
  <div class="specs">
    <div class="spec"><h3>Captions &amp; type</h3>
      <div class="capdemo"><span>JER</span><span class="k">MORA UVEK</span></div>
      <ul><li>Inter Display Black, uppercase, 64 px at 1080 width. 1–3 words per chunk, timed to the speaker's original caption sync.</li>
      <li>White with a soft shadow. One keyword per chunk sits on a crimson pill rotated −2°. Each word pops 100→110→100% over 4 fr.</li>
      <li>Placed at about 68% of frame height, clear of the Reels/TikTok UI (bottom 20%, right 12%). Č Ć Š Ž Đ are fully supported.</li>
      <li>Graphics use Inter Display for headlines, Inter SemiBold for labels, and JetBrains Mono only for the match timer.</li></ul>
      <div class="swatches"><span class="sw"><i style="background:#E8241C"></i>Crimson</span><span class="sw"><i style="background:#FFFFFF"></i>White</span><span class="sw"><i style="background:#111111"></i>Ink</span><span class="sw"><i style="background:#FFD200"></i>Sticker</span><span class="sw"><i style="background:#ECE4D6"></i>Paper</span></div>
    </div>
    <div class="spec"><h3>Colour grade</h3>
      <div class="grade">
        <figure><img src="sb/grade_before_10.6.jpg" alt="Close-up before grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-real">Before</b> crop + upscale</figcaption></figure>
        <figure><img src="sb/grade_after_10.6.jpg" alt="Close-up after grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-render">Rendered preview</b> graded still</figcaption></figure>
        <figure><img src="sb/grade_before_14.8.jpg" alt="Wide shot before grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-real">Before</b></figcaption></figure>
        <figure><img src="sb/grade_after_14.8.jpg" alt="Wide shot after grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-render">Rendered preview</b></figcaption></figure>
      </div>
      <ul><li>Crush the lifted blacks to true black, apply a gentle S-curve, and roll off the highlights.</li>
      <li>Slight teal in the deep shadows for separation and a touch of warmth in the highlights. Skin protected with an HSL qualifier.</li>
      <li>Keep the studio's crimson neon as the hero colour, which ties it to the graphics palette.</li>
      <li>Vignette −0.6 and 4–5% animated grain to hide upscale and compression artefacts. Match the wide and close-up exposure.</li></ul>
      <p class="en">These previews were rendered here with the exact crop and grade filters I'd use. In Premiere, I'll rebuild them as a Lumetri adjustment layer plus a .cube LUT.</p>
    </div>
    <div class="spec"><h3>Sound design &amp; mix</h3>
      <dl class="kv">
        <dt>Dialogue</dt><dd>HPF 80 Hz · denoise 20% · +2 dB @ 3 kHz · de-ess · 3:1 comp · −14 LUFS</dd>
        <dt>Music</dt><dd>Dark minimal trap 95–100 BPM · −26 LUFS under speech, auto-ducked · swells to −16 on the end card</dd>
        <dt>Hits</dt><dd>Downbeat 0:00 · drop on the Frame Break · final hit on the freeze</dd>
        <dt>SFX</dt><dd>Peaks −18 to −10 dBFS · applause bed −24 dB</dd>
        <dt>Master</dt><dd>−1 dBTP true-peak limit</dd>
      </dl>
      <p class="en">The source audio is 48 kbps AAC from a screen recording. Cleanup helps, but the original file would sound clearly better.</p>
    </div>
    <div class="spec"><h3>Sequence &amp; project</h3>
      <dl class="kv">
        <dt>Sequence</dt><dd>1080 × 1920 · 30 fps · Rec.709 · square px</dd>
        <dt>Video tracks</dt><dd>V1 dialogue · V2 roto subject · V3 graphics · V4 B-roll · V5 captions · V6 grade + grain</dd>
        <dt>Audio tracks</dt><dd>A1 dialogue · A2–A3 SFX · A4 music</dd>
        <dt>Bins</dt><dd>01_Source · 02_Graphics · 03_SFX · 04_Music · 05_B-roll · 06_Captions · 07_Exports</dd>
        <dt>Export</dt><dd>H.264 VBR 2-pass 16 Mbps + AAC 320k · ProRes 422 HQ master</dd>
        <dt>Safety</dt><dd>Original .mov never modified · versioned saves (v01, v02 …)</dd>
      </dl>
    </div>
  </div>
</section>

<section id="effects">
  <div class="sec-head"><span class="eyebrow">5 · Effects audit</span><h2>{used} of 20 used, and why</h2>
  <p>About one visual beat every 1.5 s suits fast short-form, but only because each effect is tied to a specific word. The seven left out would be forced, would repeat another effect, or would need footage that doesn't exist.</p></div>
  <div class="tbl"><table><thead><tr><th>#</th><th>Effect</th><th>Status</th><th>Where</th><th>Reason</th></tr></thead><tbody>
  {effects_rows()}
  </tbody></table></div>
</section>

<section id="execution">
  <div class="sec-head"><span class="eyebrow">6 · After approval</span><h2>How I'll execute</h2></div>
  <ol class="steps">
    <li>Copy the source into a project folder and leave the original untouched. Build the bins and the 1080 × 1920 / 30 fps sequence.</li>
    <li>Lay down the six dialogue segments with the five pause cuts and check every cut at frame level.</li>
    <li>Rotoscope the speaker for S1, S2, S7, and the end card (frame-by-frame segmentation, exported as alpha mattes).</li>
    <li>Render each motion graphic as a ProRes 4444 clip with alpha, timed to the word timecodes above. Keyframe the zooms and pushes on the clips so they stay editable.</li>
    <li>Build the captions as an .srt plus styled graphic clips, synthesise and place the SFX, and add the music bed with ducking.</li>
    <li>Add the grade adjustment layer, LUT, and grain, then mix to −14 LUFS / −1 dBTP.</li>
    <li>Export, run QC on every transition, caption, level, and colour match, and send you before/after frames and the effects report.</li>
  </ol>
  <p>With <b>Option B</b>, steps 1–7 produce a Premiere XML you import with File → Import. Every cut, layer, and zoom keyframe stays editable. Effects built in After Effects in a native workflow (Orbit, Frame Break) arrive as pre-rendered alpha clips rather than live AE comps.</p>
</section>

<section id="approve">
  <div class="approve">
    <h2>To approve, reply with</h2>
    <ul>
      <li><b>Plan:</b> approve as is, or list the scenes or effects to change.</li>
      <li><b>Execution route:</b> A (connect your computer for Premiere) or B (I build the importable timeline and MP4 here).</li>
      <li><b>Footage:</b> the original high-res file if you have it, otherwise I'll use the screen recording.</li>
      <li><b>B-roll &amp; music:</b> your clip and track, or permission to use generated or fallback options.</li>
      <li><b>End card text:</b> confirm “NASTAVAK →” and the handle, or give me your own.</li>
    </ul>
  </div>
</section>

</div>
'''
open(sys.argv[1], "w").write(page)
print("ok", round(TOTAL, 2), [round(o(t), 2) for t in (2.0, 6.77, 9.02, 12.25, 12.6, 16.82)])
