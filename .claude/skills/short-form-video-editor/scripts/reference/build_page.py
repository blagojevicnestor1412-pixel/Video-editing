"""Generates the storyboard HTML from a per-project data file.
Usage: python3 -I build_page.py <project_data.py> <out.html>
See data_jiujitsu.py for the fields a data file defines."""
import sys, html

FPS = 30
def tc(s):
    f = round(s * FPS); return f"{f//(FPS*3600):02d}:{f//(FPS*60)%60:02d}:{f//FPS%60:02d}:{f%FPS:02d}"
def sh(s):
    return f"{s:05.2f}s"
E = html.escape


def derive():
    """Called by the data file right after SEGS/END_CARD: builds the source->output time map."""
    g = globals(); outmap = []; acc = 0.0
    for a, b in g["SEGS"]:
        outmap.append((a, b, acc)); acc += b - a
    g["OUTMAP"] = outmap; g["BODY_END"] = acc; g["TOTAL"] = acc + g.get("END_CARD", 0.0)

def o(src):
    for a, b, off in OUTMAP:
        if a - 1e-6 <= src <= b + 1e-6:
            return off + src - a
    raise ValueError(src)

GRAPHICS_END = {}
exec(open(sys.argv[1]).read(), globals())

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
        a = o(s["src"][0]); b = GRAPHICS_END.get(s["id"], o(s["src"][1]))
        out.append(f'<rect x="{x(a)+1:.1f}" y="50" width="{(b-a)*sc-3:.1f}" height="26" rx="3" class="tl-fx"/>')
        out.append(f'<text x="{x(a)+5:.1f}" y="67" class="tl-txt-on">{s["id"]}</text>')
    # captions chunks
    for t, *_ in TRANSCRIPT:
        try: tt = o(t)
        except ValueError: tt = o(t + 0.4)
        out.append(f'<rect x="{x(tt):.1f}" y="18" width="{1.2*sc:.1f}" height="26" rx="3" class="tl-cap"/>')
    # sfx hits
    for t in SFX_HITS:
        out.append(f'<rect x="{x(t)-1.5:.1f}" y="118" width="3" height="18" rx="1.5" class="tl-hit"/>')
    out.append(f'<rect x="{X0}" y="146" width="{(TOTAL)*sc:.1f}" height="26" rx="3" class="tl-music"/>')
    for t, l in MUSIC_MARKS:
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
    oa, ob = o(a), GRAPHICS_END.get(s["id"], o(b))
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

CSS = '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500;62..125,800;62..125,900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">\n<style>\n/* Layout: an edit-suite document. A narrow reading column for decisions, wide scene sheets that pair the real frame with the mockup, and a timeline band styled like a sequence panel. */\n:root {\n  --bg: #F5F4F3; --surface: #FFFFFF; --sunk: #ECEAE8; --fg: #171314; --muted: #675E60; --line: #DDD8D6;\n  --accent: #C81E17; --accent-ink: #FFFFFF; --real: #1F7A4D; --mock: #9A6A00; --mock-bg: #FFE7A8; --real-bg: #D8F0E2;\n  --clip: #3C5A8C; --fx: #C81E17; --cap: #6F6A6B; --music: #2F6E5A;\n  --f-display: "Archivo", "Arial Narrow", system-ui, sans-serif;\n  --f-body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;\n  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;\n}\n@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {\n  --bg: #121011; --surface: #1B1819; --sunk: #0D0B0C; --fg: #EEEAEA; --muted: #A39A9C; --line: #2E292B;\n  --accent: #F0372E; --accent-ink: #FFFFFF; --real: #5BD49A; --mock: #FFC53D; --mock-bg: #3A2C05; --real-bg: #0F3324;\n  --clip: #5B7DB8; --fx: #E8342B; --cap: #8D8789; --music: #3F8F75; color-scheme: dark; } }\n:root[data-theme="dark"] {\n  --bg: #121011; --surface: #1B1819; --sunk: #0D0B0C; --fg: #EEEAEA; --muted: #A39A9C; --line: #2E292B;\n  --accent: #F0372E; --accent-ink: #FFFFFF; --real: #5BD49A; --mock: #FFC53D; --mock-bg: #3A2C05; --real-bg: #0F3324;\n  --clip: #5B7DB8; --fx: #E8342B; --cap: #8D8789; --music: #3F8F75; color-scheme: dark; }\n* { box-sizing: border-box; }\nbody { background: var(--bg); color: var(--fg); font-family: var(--f-body); font-size: 15px; line-height: 1.55; }\n.wrap { max-width: 1120px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 80px; display: grid; gap: 56px; }\nh1, h2, h3 { font-family: var(--f-display); text-wrap: balance; margin: 0; }\nh1 { font-size: clamp(34px, 6vw, 60px); font-weight: 900; font-stretch: 72%; line-height: .95; letter-spacing: -.01em; text-transform: uppercase; }\nh2 { font-size: clamp(22px, 3vw, 30px); font-weight: 800; font-stretch: 85%; text-transform: uppercase; letter-spacing: .01em; }\nh3 { font-size: 22px; font-weight: 800; font-stretch: 90%; }\nh4 { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 18px 0 4px; font-weight: 600; }\np { margin: 0; max-width: 68ch; }\n.mono { font-family: var(--f-mono); font-size: 12.5px; font-variant-numeric: tabular-nums; }\n.eyebrow { font-family: var(--f-mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }\n.hero { display: grid; gap: 18px; }\n.status { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13px; padding: 6px 12px; border-radius: 99px; background: var(--accent); color: var(--accent-ink); justify-self: start; }\n.status::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }\n.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }\n.facts div { background: var(--surface); padding: 12px 14px; min-width: 0; }\n.facts dt { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }\n.facts dd { margin: 2px 0 0; font-family: var(--f-mono); font-size: 14px; font-weight: 600; }\nsection { display: grid; gap: 18px; }\n.sec-head { display: grid; gap: 6px; border-top: 2px solid var(--fg); padding-top: 12px; }\n.decisions { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }\n.decision { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 8px; align-content: start; min-width: 0; }\n.decision h3 { font-size: 17px; font-stretch: 100%; }\n.decision .sev { font-family: var(--f-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--accent); font-weight: 600; }\n.decision ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }\n.tbl { overflow-x: auto; }\ntable { border-collapse: collapse; width: 100%; }\ntd, th { text-align: left; vertical-align: top; padding: 8px 10px; border-bottom: 1px solid var(--line); }\nth { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 600; }\ntd.en, .en { color: var(--muted); }\n.timeline { background: var(--sunk); border: 1px solid var(--line); border-radius: 10px; padding: 16px; overflow-x: auto; }\n.timeline svg { min-width: 760px; width: 100%; height: auto; display: block; }\n.tl-lab { font: 600 11px var(--f-body); fill: var(--muted); }\n.tl-lane { fill: var(--surface); }\n.tl-clip { fill: var(--clip); } .tl-end { fill: var(--accent); } .tl-fx { fill: var(--fx); opacity: .85; }\n.tl-cap { fill: var(--cap); } .tl-hit { fill: var(--fg); } .tl-music { fill: var(--music); opacity: .8; }\n.tl-txt { font: 500 10px var(--f-mono); fill: #FFFFFF; } .tl-txt-on { font: 600 10px var(--f-mono); fill: #FFFFFF; }\n.tl-cut { stroke: var(--accent); stroke-width: 1.2; stroke-dasharray: 3 3; }\n.tl-tick { stroke: var(--muted); } .tl-ruler { font: 500 10px var(--f-mono); fill: var(--muted); }\n.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; color: var(--muted); }\n.legend span { display: inline-flex; gap: 6px; align-items: center; }\n.legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }\n.scenes { display: grid; gap: 28px; }\n.scene { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }\n.scene-head { display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--line); }\n.scene-id { font-family: var(--f-display); font-weight: 900; font-stretch: 70%; font-size: 40px; line-height: 1; color: var(--accent); }\n.scene-title { min-width: 0; display: grid; gap: 6px; }\n.fxrow { display: flex; flex-wrap: wrap; gap: 6px; }\n.chip { font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 99px; border: 1px solid var(--accent); color: var(--accent); }\n.tcs { margin: 0; display: grid; gap: 4px; text-align: right; }\n.tcs dt { display: inline; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-right: 8px; }\n.tcs dd { display: inline; margin: 0; }\n.scene-body { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 22px; padding: 18px; }\n.frames { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; align-content: start; }\nfigure { margin: 0; display: grid; gap: 6px; min-width: 0; }\nfigure img { width: 100%; height: auto; aspect-ratio: 9 / 16; object-fit: cover; border-radius: 8px; background: var(--sunk); }\nfigure img.src { aspect-ratio: auto; height: auto; }\n.frames { align-items: start; }\nfigcaption { font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }\n.tag { font-family: var(--f-mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; padding: 2px 7px; border-radius: 4px; font-weight: 600; }\n.tag-real { background: var(--real-bg); color: var(--real); }\n.tag-mock { background: var(--mock-bg); color: var(--mock); }\n.tag-render { background: var(--sunk); color: var(--fg); border: 1px solid var(--line); }\n.notes { min-width: 0; }\nblockquote { margin: 0; padding: 12px 14px; border-left: 3px solid var(--accent); background: var(--sunk); border-radius: 0 8px 8px 0; display: grid; gap: 4px; }\nblockquote p:first-child { font-weight: 600; font-size: 16px; }\ntable.anim td:first-child { white-space: nowrap; color: var(--accent); }\n.specs { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }\n.spec { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 10px; align-content: start; min-width: 0; }\n.spec h3 { font-size: 18px; font-stretch: 100%; }\n.spec ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }\n.kv { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; font-size: 14px; }\n.kv dt { color: var(--muted); } .kv dd { margin: 0; font-family: var(--f-mono); font-size: 12.5px; }\n.capdemo { background: #141112; border-radius: 8px; padding: 22px 12px; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; font-family: "Inter", sans-serif; font-weight: 900; font-size: 26px; letter-spacing: -.01em; color: #FFFFFF; }\n.capdemo .k { background: #E8241C; padding: 0 8px; border-radius: 6px; transform: rotate(-2deg); display: inline-block; }\n.swatches { display: flex; gap: 8px; flex-wrap: wrap; }\n.sw { display: grid; gap: 4px; font-size: 11px; font-family: var(--f-mono); color: var(--muted); }\n.sw i { width: 56px; height: 36px; border-radius: 6px; border: 1px solid var(--line); display: block; }\n.grade { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }\n.state { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }\n.state.ok { background: var(--real-bg); color: var(--real); }\n.state.no { background: var(--sunk); color: var(--muted); border: 1px solid var(--line); }\ntd.num { color: var(--muted); }\nol.steps { margin: 0; padding-left: 22px; display: grid; gap: 6px; max-width: 80ch; }\n.approve { background: var(--surface); border: 2px solid var(--accent); border-radius: 12px; padding: 20px; display: grid; gap: 10px; }\n.approve ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }\na { color: var(--accent); }\n:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }\n@media (max-width: 760px) {\n  .scene-head { grid-template-columns: auto 1fr; }\n  .tcs { grid-column: 1 / -1; text-align: left; }\n  .scene-body { grid-template-columns: 1fr; }\n}\n</style>\n\n'

page = f"""<title>{E(TITLE)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
{CSS}
<div class="wrap">
{HERO_HTML}
<section id="decisions">
  <div class="sec-head"><span class="eyebrow">Read first</span><h2>Things that need you</h2></div>
  {DECISIONS_HTML}
</section>
<section id="analysis">
  <div class="sec-head"><span class="eyebrow">1 · Analysis</span><h2>What the clip says</h2></div>
  {ANALYSIS_HTML}
  <h4>Transcript</h4>
  <div class="tbl"><table><thead><tr><th>Source</th><th>Original</th><th>English</th></tr></thead><tbody>
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
  <p>Output timecodes are SMPTE at {FPS} fps on the edited sequence. Source times are seconds into the original file. <b class="tag tag-real">Source frame</b> is a real frame from the footage. <b class="tag tag-mock">Concept mockup</b> is a still composed from that frame to show intent. It is not a render.</p></div>
  <div class="scenes">
  {"".join(scene_card(s) for s in SCENES)}
  </div>
</section>
<section id="specs">
  <div class="sec-head"><span class="eyebrow">4 · Look &amp; sound</span><h2>Global specs</h2></div>
  {SPECS_HTML}
</section>
<section id="effects">
  <div class="sec-head"><span class="eyebrow">5 · Effects audit</span><h2>{used} of {len(EFFECTS)} used, and why</h2>
  {EFFECTS_INTRO_HTML}</div>
  <div class="tbl"><table><thead><tr><th>#</th><th>Effect</th><th>Status</th><th>Where</th><th>Reason</th></tr></thead><tbody>
  {effects_rows()}
  </tbody></table></div>
</section>
<section id="execution">
  <div class="sec-head"><span class="eyebrow">6 · After approval</span><h2>How I'll execute</h2></div>
  {EXEC_HTML}
</section>
<section id="approve">
  <div class="approve">
    <h2>To approve, reply with</h2>
    {APPROVE_HTML}
  </div>
</section>
</div>
"""
open(sys.argv[2], "w").write(page)
print("ok", round(TOTAL, 2))
