# Motion-graphics effects catalog

Twenty effects that users commonly request. For each one: what it communicates, a good trigger in speech, what it needs, and how to build it with PIL/numpy (coordinates assume 1080×1920 at 30 fps). The "Ref" column points to the function in `scripts/reference/render.py`.

| # | Effect | Use it when… | Needs | Recipe | Ref |
|---|---|---|---|---|---|
| 1 | Orbit | Hook: the topic word should circle the speaker | Roto mask | Text ring on an ellipse around the head (rx≈440, ry≈84, tilt −6°). Glyph size ∝ ring circumference / text width, so letters don't crowd. Back half (sin<0) drawn red and dim *under* the masked subject; front half white with glow on top. Rotate one turn per ~2.4 s and scale in over 10 fr. | `s1` |
| 2 | Chat Takeover | Ironic or social-reaction lines ("everyone will applaud") | — | Dim 30% + 12 px blur on the plate. Comment bubbles (avatar, username, message + emoji) pop in every 5 fr, emoji particles rise, everything swipes off left in 6 fr on the next beat. Pair with a rising notification ping per bubble. | `s5` |
| 3 | Frame Escape | Subject "breaks out" of a framed card | Good roto | Put the plate in an inset card and draw the masked head/hand over the card border. Skip it if roto is weak or other roto effects are nearby. | — |
| 4 | Snap Zoom | Words meaning fast or sudden, punchlines | — | 3-frame scale 100→138% (ease-out) centred on the face, zoom blur on frames 1–2, speed lines fading over 10 fr, oversized caption. SFX: snap plus a tight whoosh. | `s4` |
| 5 | Checklist Pop | The speaker enumerates or contrasts items | — | White cards with a red check circle pop (0.6→1.08→1.0, 8 fr) on each item's word. The check stroke draws on over 6 fr. The conclusion card is solid red and earlier cards dim to 60%. Staggered fly-off exit. | `s8` |
| 6 | Headline Storm | The speaker cites news, press or public claims | Real headlines | Headline cards fly in from multiple directions. Never invent headlines; skip if none exist. | — |
| 7 | Zoom Portal | Imagined or hypothetical scenario, "what if" | B-roll or a type fallback | Circular portal with a red glow ring opens (back-ease, 10 fr) in empty background space, never over the face. Push through it (scale 1→4.2, ease-in, 9 fr) and cross-fade to full-frame content, which hides a jump cut. | `s3` |
| 8 | Growth Curve | Numbers, progress, before/after metrics | Data | Animated line/area chart drawing on with a counter. Skip without real numbers. | — |
| 9 | Studio Reveal | Establishing the setting | Footage wider than the crop | Pull back from tight to wide with a light sweep. You can't reveal pixels you don't have, so skip it on cropped screen recordings. | — |
| 10 | B-roll Overlay | The speaker describes an action or object | B-roll clip | Full-frame or picture-in-picture cutaway over continuous dialogue. Good for hiding jump cuts. Ask the user for the clip; fall back to kinetic type (`type_card`). | `type_card` |
| 11 | Paper Cutout | Quotes, sarcasm, a texture change | Roto mask | Paper-noise background with a torn red strip. Speaker becomes a sticker (dilated white border plus shadow) posterized to 12 fps with ±3 px jitter. Ransom-note word labels slam in (1.35→1.0, 4 fr). Tear-wipe in, peel-off out. SFX: rustle plus stamps. | `s2` |
| 12 | Dolly Zoom | The thesis or a moment of realisation | Roto mask | Clean plate by normalised blur fill of the masked area; background scales 1→1.35 (ease-in-out) with growing blur and darkening; subject stays 100%; red rim glow. Keep all other graphics off. SFX: sub drone plus riser. | `s7` |
| 13 | Magazine Cover | End card, recap, cliffhanger | Roto mask | Freeze on the best portrait. Masthead slams down *behind* the head (subject composited over it). Cover lines type on, barcode, CTA pill pops. White flash in, slow 3.5% push. | `end_card` |
| 14 | Liquid Glass | Stats or context panel that shouldn't hide the speaker | — | Frosted panel: crop the region, blur it, brighten 1.25×, add a 14% white fill, a 1 px highlight stroke, a top specular band and one diagonal light sweep. Rise 120 px with ease-out over 10 fr. | `glass` |
| 15 | Zoom Through Cut | Camera-angle change between shots | — | Outgoing shot zooms 1→1.6× with blur over the last 4 fr. Incoming shot starts at 160% and settles to 100% over 6 fr. Whoosh. | `s4`/`s5` |
| 16 | Green Screen | Footage shot on green, or the subject needs a new world | Keyable footage | Chroma key plus a new background. Don't replace a real studio just to use the effect. | — |
| 17 | Frame Break | Breaking out of a calm moment, often a thesis followed by its explanation | — | Freeze the last frame for 2 fr. Radial shards (rings × random angles) with white edges; the centre shards are already gone. Shards fly out with push ∝ q², gravity and rotation over 10 fr, revealing the next shot. Impact flash. SFX: shatter plus sub hit. Hides a jump cut. | `frame_break` |
| 18 | Digital Zoom | Long static shots that need life | — | Slow keyframed scale of 100→112% (ease-in-out) across the shot. Reverse it on the next shot for continuity. | `s8`/`s9` |
| 19 | Phone Mockup | Showing an app, a post or a DM | Screen content | Composite the content into a phone frame with a reflection. Avoid it when the source already *is* a phone screen recording, because it emphasises the low resolution. | — |
| 20 | Checklist | Same job as Checklist Pop | — | Use only one checklist-type effect per short video. | — |

## Rules of thumb

- Fast short-form gets one visual beat per ~1.5 s, each tied to a word. Leave the thesis clean.
- Limit roto-dependent effects to what the mask quality supports. At low resolution, two or three is plenty.
- Place every pause cut under something: a camera change, a full-frame graphic, a shatter, or a panel entrance.
- Palette: one hero accent taken from the footage (for example, the studio's neon), plus white, ink, and at most one sticker colour.
- Captions: Inter Display Black, uppercase, 1–3 words, one keyword in a −2° accent pill, at about 68% of frame height (clear of platform UI in the bottom 20% and right 12%).
