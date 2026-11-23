"""Storyboard data for project 1 (jiu-jitsu podcast clip). Used by build_page.py."""
SEGS = [(0.00, 1.62), (2.00, 4.95), (5.25, 8.75), (9.02, 12.25), (12.60, 16.55), (16.82, 19.07)]
END_CARD = 2.0
derive()  # defines o(), BODY_END, TOTAL from SEGS

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

SFX_HITS = [0, o(2.0), o(3.45), o(4.2), o(5.95), o(6.77), o(6.9), o(7.4), o(9.02), o(9.3), o(12.25), o(12.8), o(14.0), o(14.6), BODY_END]
MUSIC_MARKS = [(0, "downbeat"), (o(12.25), "drop"), (BODY_END, "final hit")]
GRAPHICS_END = {"S9": TOTAL}
TITLE = 'Jiu-Jitsu Reel Storyboard'
HERO_HTML = '<header class="hero">\n  <span class="eyebrow">Edit plan v1 · 9:16 short · Serbian dialogue</span>\n  <h1>Jiu-jitsu: sport vs. reality</h1>\n  <p>A storyboard for a 19.5-second vertical reel built from your clip. It covers the analysis, nine scenes with exact timecodes, 13 of the 20 requested effects, and the captions, sound, and grade. Nothing has been changed in Premiere Pro.</p>\n  <span class="status">Waiting for your approval</span>\n  <dl class="facts">\n    <div><dt>Source</dt><dd>19.07 s · 30 fps</dd></div>\n    <div><dt>Source size</dt><dd>292 × 632</dd></div>\n    <div><dt>Usable picture</dt><dd>≈ 201 × 357</dd></div>\n    <div><dt>Pauses cut</dt><dd>5 · 1.57 s</dd></div>\n    <div><dt>Planned length</dt><dd>19.50 s</dd></div>\n    <div><dt>Delivery</dt><dd>1080 × 1920</dd></div>\n  </dl>\n</header>'
DECISIONS_HTML = '<div class="decisions">\n    <div class="decision"><span class="sev">Blocker for execution</span><h3>Premiere Pro isn\'t reachable from this session</h3>\n      <p>This session runs in a cloud container. It has no Premiere Pro or MCP Bridge tools, and no computer is attached.</p>\n      <ul><li><b>Option A:</b> In the Claude desktop app, open Settings → Claude Code → Remote Control and share the project folder. I can then work on your machine where Premiere runs.</li>\n      <li><b>Option B (works now):</b> I build every layer here and give you a Premiere-importable XML timeline. That includes the cuts, keyframed zooms, alpha-channel motion graphics, SFX, captions (.srt), and a grade LUT, plus a finished MP4.</li></ul></div>\n    <div class="decision"><span class="sev">Quality ceiling</span><h3>The clip is a screen recording of an Instagram story</h3>\n      <p>The IG header, like rail, reply bar, and burned-in captions are all part of the pixels. After cropping them out, about 201 × 357 px is left, which means roughly a 5.4× upscale to 1080 × 1920.</p>\n      <ul><li><b>Best:</b> send the original podcast file. Every effect will look sharper and Studio Reveal becomes possible.</li>\n      <li><b>Fallback:</b> crop + Lanczos upscale + sharpening + grain (shown below). An AI video upscale through Higgsfield is possible but costs credits.</li></ul></div>\n    <div class="decision"><span class="sev">Assets</span><h3>B-roll and music</h3>\n      <ul><li><b>B-roll (S3–S4):</b> about 2 s of a flying armbar or jumping guard, ideally from your own gym. If there\'s no clip, I\'ll replace the portal content with a kinetic-type animation.</li>\n      <li><b>Music:</b> I can\'t download licensed tracks here. Pick a track from Premiere\'s Essential Sound or Adobe Stock (dark minimal trap, 95–100 BPM), or approve an original bed generated with Higgsfield (uses credits).</li>\n      <li><b>SFX:</b> I\'ll synthesise original whooshes, hits, pops, and the shatter, so no licensing is needed.</li></ul></div>\n    <div class="decision"><span class="sev">Rights</span><h3>Account on screen: gbbelgrade &amp; danijelbrajcic</h3>\n      <p>Please confirm you have the right to re-edit and repost this clip. The end card handle and CTA text are placeholders until you confirm them.</p></div>\n  </div>'
ANALYSIS_HTML = "<p><b>Topic:</b> a coach on a podcast arguing that jiu-jitsu isn't about flashy, fast submissions done for applause like at a competition. You always have to connect the sport side to real-world application.</p>\n  <p><b>Structure:</b> setup with a sarcastic quote (0–9 s) → thesis (“mora uvek”, 10–12 s) → the two-part parallel (12.6–16.5 s) → an open ending that stops mid-sentence (“i dan danas…”).</p>\n  <p><b>Pace:</b> fast, conversational, almost no dead air. I'll trim only the five breaths of about 0.3 s, and each cut is hidden under a planned effect or camera change. The thesis is deliberately left clean and slow.</p>\n  <p><b>Shots in the source:</b> wide A 0–2.0 s · wide B 2.0–6.77 s · close-up 6.77–12.6 s · wide B 12.6–16.5 s · wide C 16.5–19.07 s.</p>\n  "
SPECS_HTML = '<div class="specs">\n    <div class="spec"><h3>Captions &amp; type</h3>\n      <div class="capdemo"><span>JER</span><span class="k">MORA UVEK</span></div>\n      <ul><li>Inter Display Black, uppercase, 64 px at 1080 width. 1–3 words per chunk, timed to the speaker\'s original caption sync.</li>\n      <li>White with a soft shadow. One keyword per chunk sits on a crimson pill rotated −2°. Each word pops 100→110→100% over 4 fr.</li>\n      <li>Placed at about 68% of frame height, clear of the Reels/TikTok UI (bottom 20%, right 12%). Č Ć Š Ž Đ are fully supported.</li>\n      <li>Graphics use Inter Display for headlines, Inter SemiBold for labels, and JetBrains Mono only for the match timer.</li></ul>\n      <div class="swatches"><span class="sw"><i style="background:#E8241C"></i>Crimson</span><span class="sw"><i style="background:#FFFFFF"></i>White</span><span class="sw"><i style="background:#111111"></i>Ink</span><span class="sw"><i style="background:#FFD200"></i>Sticker</span><span class="sw"><i style="background:#ECE4D6"></i>Paper</span></div>\n    </div>\n    <div class="spec"><h3>Colour grade</h3>\n      <div class="grade">\n        <figure><img src="sb/grade_before_10.6.jpg" alt="Close-up before grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-real">Before</b> crop + upscale</figcaption></figure>\n        <figure><img src="sb/grade_after_10.6.jpg" alt="Close-up after grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-render">Rendered preview</b> graded still</figcaption></figure>\n        <figure><img src="sb/grade_before_14.8.jpg" alt="Wide shot before grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-real">Before</b></figcaption></figure>\n        <figure><img src="sb/grade_after_14.8.jpg" alt="Wide shot after grading" loading="lazy" width="540" height="960"><figcaption><b class="tag tag-render">Rendered preview</b></figcaption></figure>\n      </div>\n      <ul><li>Crush the lifted blacks to true black, apply a gentle S-curve, and roll off the highlights.</li>\n      <li>Slight teal in the deep shadows for separation and a touch of warmth in the highlights. Skin protected with an HSL qualifier.</li>\n      <li>Keep the studio\'s crimson neon as the hero colour, which ties it to the graphics palette.</li>\n      <li>Vignette −0.6 and 4–5% animated grain to hide upscale and compression artefacts. Match the wide and close-up exposure.</li></ul>\n      <p class="en">These previews were rendered here with the exact crop and grade filters I\'d use. In Premiere, I\'ll rebuild them as a Lumetri adjustment layer plus a .cube LUT.</p>\n    </div>\n    <div class="spec"><h3>Sound design &amp; mix</h3>\n      <dl class="kv">\n        <dt>Dialogue</dt><dd>HPF 80 Hz · denoise 20% · +2 dB @ 3 kHz · de-ess · 3:1 comp · −14 LUFS</dd>\n        <dt>Music</dt><dd>Dark minimal trap 95–100 BPM · −26 LUFS under speech, auto-ducked · swells to −16 on the end card</dd>\n        <dt>Hits</dt><dd>Downbeat 0:00 · drop on the Frame Break · final hit on the freeze</dd>\n        <dt>SFX</dt><dd>Peaks −18 to −10 dBFS · applause bed −24 dB</dd>\n        <dt>Master</dt><dd>−1 dBTP true-peak limit</dd>\n      </dl>\n      <p class="en">The source audio is 48 kbps AAC from a screen recording. Cleanup helps, but the original file would sound clearly better.</p>\n    </div>\n    <div class="spec"><h3>Sequence &amp; project</h3>\n      <dl class="kv">\n        <dt>Sequence</dt><dd>1080 × 1920 · 30 fps · Rec.709 · square px</dd>\n        <dt>Video tracks</dt><dd>V1 dialogue · V2 roto subject · V3 graphics · V4 B-roll · V5 captions · V6 grade + grain</dd>\n        <dt>Audio tracks</dt><dd>A1 dialogue · A2–A3 SFX · A4 music</dd>\n        <dt>Bins</dt><dd>01_Source · 02_Graphics · 03_SFX · 04_Music · 05_B-roll · 06_Captions · 07_Exports</dd>\n        <dt>Export</dt><dd>H.264 VBR 2-pass 16 Mbps + AAC 320k · ProRes 422 HQ master</dd>\n        <dt>Safety</dt><dd>Original .mov never modified · versioned saves (v01, v02 …)</dd>\n      </dl>\n    </div>\n  </div>'
EFFECTS_INTRO_HTML = "<p>About one visual beat every 1.5 s suits fast short-form, but only because each effect is tied to a specific word. The seven left out would be forced, would repeat another effect, or would need footage that doesn't exist.</p>"
EXEC_HTML = '<ol class="steps">\n    <li>Copy the source into a project folder and leave the original untouched. Build the bins and the 1080 × 1920 / 30 fps sequence.</li>\n    <li>Lay down the six dialogue segments with the five pause cuts and check every cut at frame level.</li>\n    <li>Rotoscope the speaker for S1, S2, S7, and the end card (frame-by-frame segmentation, exported as alpha mattes).</li>\n    <li>Render each motion graphic as a ProRes 4444 clip with alpha, timed to the word timecodes above. Keyframe the zooms and pushes on the clips so they stay editable.</li>\n    <li>Build the captions as an .srt plus styled graphic clips, synthesise and place the SFX, and add the music bed with ducking.</li>\n    <li>Add the grade adjustment layer, LUT, and grain, then mix to −14 LUFS / −1 dBTP.</li>\n    <li>Export, run QC on every transition, caption, level, and colour match, and send you before/after frames and the effects report.</li>\n  </ol>\n  <p>With <b>Option B</b>, steps 1–7 produce a Premiere XML you import with File → Import. Every cut, layer, and zoom keyframe stays editable. Effects built in After Effects in a native workflow (Orbit, Frame Break) arrive as pre-rendered alpha clips rather than live AE comps.</p>'
APPROVE_HTML = "<ul>\n      <li><b>Plan:</b> approve as is, or list the scenes or effects to change.</li>\n      <li><b>Execution route:</b> A (connect your computer for Premiere) or B (I build the importable timeline and MP4 here).</li>\n      <li><b>Footage:</b> the original high-res file if you have it, otherwise I'll use the screen recording.</li>\n      <li><b>B-roll &amp; music:</b> your clip and track, or permission to use generated or fallback options.</li>\n      <li><b>End card text:</b> confirm “NASTAVAK →” and the handle, or give me your own.</li>\n    </ul>"
