---
name: short-form-video-editor
description: Acts as an autonomous editor, motion designer and creative director for short vertical videos (Reels, TikTok, Shorts, podcast clips, talking heads). It analyzes the footage, builds a visual storyboard with real frames and clearly labelled concept mockups, waits for approval, then renders a finished 9:16 MP4 with motion-graphics effects, synced captions, music, SFX, colour grade and QC. Use it whenever the user uploads or names a video clip and asks to edit it, cut it, add effects, motion graphics, captions or a "premium/cinematic" look, make a storyboard or editing plan, or "edit in Premiere/After Effects". Also use it when they list effects like Orbit, Snap Zoom, Chat Takeover, Frame Break, Liquid Glass, Magazine Cover or Checklist Pop, or write in Serbian/Croatian/Bosnian ("montiraj", "napravi video", "isprav video"), even if they don't say "skill" or "storyboard".
---

# Short-form video editor

The user wants an editor who does the work, not someone who explains how to do it. The job runs in two gated phases:

1. **Analyze → storyboard → wait for approval.** Don't render the final video before they approve, unless they explicitly ask for the finished file. Asking for the finished file counts as approval; fill any gaps with stated fallbacks.
2. **Execute → QC → deliver** the MP4, the before/after evidence, and an effects report.

Every effect has to earn its place by being tied to a specific word or beat. Random effects make an edit look cheap. Report only what you actually did and checked: if you couldn't listen to the audio, say so.

## Phase 0: Check the environment first

- **Premiere Pro / After Effects / "MCP Bridge"** only exist on the user's machine. In a cloud session, look for an attached computer (list_computer_folders) or Premiere/computer-use tools. If there are none, say so plainly and offer two routes:
  - **A:** connect the computer through Remote Control.
  - **B:** render everything here with Python + ffmpeg and deliver an MP4 (optionally with an importable XML, .srt and LUT).

  Never claim an action happened in Premiere unless a Premiere tool really executed it.
- **Tools:** check for `ffmpeg`, `python3`, PIL, numpy, scipy, and Playwright/Chromium (for screenshots).
- **Speech-to-text:** faster-whisper needs Hugging Face. If the network blocks it, read the burned-in captions instead (see Phase 1).
- **Person segmentation:** `pip install "rembg[cpu]"`, then download `u2net_human_seg.onnx` from the rembg GitHub releases into `~/.u2net/`.

## Phase 1: Analyze the footage

Run `scripts/analyze.sh <video> <outdir>`. It produces:
- ffprobe metadata;
- a 1 fps contact sheet;
- 2 fps frames;
- a loudness map in 100 ms steps (pauses are runs below about −30 dB);
- scene-cut timestamps.

Look at the contact sheet before planning anything. Things to look for:

- **Screen recordings of social apps** (status bar, IG/TikTok header, like/comment rail, "Reply…" bar, burned-in captions). Measure the clean picture rectangle on a gridded frame (`analyze.sh` writes `grid.png`), crop to it, and tell the user the effective resolution and upscale factor. Ask for the original file, since it is the single biggest quality lever. Crop out the old captions so yours replace them.
- **Platform downloads (TikTok/Reels saves):**
  - **Watermark:** it often moves partway through (TikTok jumps from top-left to bottom-right after a few seconds). Find each position on gridded frames at several times, then remove it with time-gated `delogo=x:y:w:h:enable='lt(t,T)'`. Keep the rect 1 px inside the frame edge.
  - **Outro:** cut any platform end screen.
  - **Mid-frame captions:** if the old captions sit mid-frame and can't be cropped, `delogo` the band and pin your captions over it on an opaque caption bar wide enough to hide the smear.
  - **Gotcha:** `-ss` before `-i` resets `t`, so `enable` gates don't fire on single-frame previews. Judge cleanup on the full decode.
- **Burned-in captions as a transcript:** crop the caption band from every frame at 5 fps, tile it with timestamps (`analyze.sh caps <y> <h>`), and read it. This gives word-level timing that is often better than ASR. Translate it for the plan.
- **Story:** topic, hook, thesis sentence, the list/contrast structure, and how it ends. Note when the clip ends mid-sentence, because the end card can turn that into a cliffhanger.
- **Pauses:** only trim real breaths (about 0.3–0.4 s). Place each jump cut where an effect, a camera change or full-frame graphics hides it.
- **Rights:** note the account names shown on screen and ask the user to confirm they can repost.

## Phase 2: Plan and storyboard

Read `references/effects-catalog.md`. For each effect it gives the purpose, a good trigger, the assets it needs, and a render recipe. Map effects to words:

- Keep about one beat every 1.5 s for fast short-form.
- Make the thesis sentence the calmest shot.
- Use each effect at most once.
- For every effect you leave out, give a concrete reason (no data for a graph, no keyable footage, would repeat another effect, needs footage that doesn't exist).

Build the storyboard as an HTML artifact. `scripts/reference/build_page.py <project_data.py> <out.html>` is a complete generator: copy `data_jiujitsu.py`, replace its fields (SEGS, SCENES, EFFECTS, TRANSCRIPT, PAUSES, SFX_HITS and the *_HTML copy blocks), and build. Images go in `sb/` beside the page. Publish from a folder inside the working directory or the scratchpad. The page needs:
- **Up front:** a "things that need you" block covering blockers, quality ceiling, assets (B-roll, music) and rights.
- **Analysis:** the transcript with translation and the shot list.
- **Timeline:** an SVG overview with lanes for picture, graphics, captions, SFX and music, with the pause cuts marked.
- **One card per scene:** output SMPTE timecode at the source fps, source in/out, the quote, why this effect, a timed animation table, sound, and the transition into the next scene.
- **Two images per card,** labelled honestly. **Source frame** is a real frame. **Concept mockup** is a composed still and is *not* a render. Use **Rendered preview** only for stills processed with the real pipeline, such as the graded crop.
- **Global specs:** caption style, grade before/after, mix targets, sequence/export settings, the 20-effect audit table, and how you'll execute.

Mockups: `scripts/reference/mock.py` composes them from real frames with PIL and rembg masks. Look at every mockup yourself before publishing. Typical fixes:
- mirrored orbit text (drive the angle *decreasing* so the front reads left to right);
- glyphs not on a common baseline (draw with `anchor="ms"`);
- the mask grabbing shelf props (keep the largest component, then cut above head height measured on a gridded mask preview);
- holes where a mic crosses the body (`binary_fill_holes`).

Then stop and ask for approval with a short list: plan OK or changes, execution route, original footage, B-roll/music, end-card text.

## Phase 3: Execute (render route)

Pipeline (the reference implementation is in `scripts/reference/`; adapt its data tables rather than starting from scratch):

1. **Base plates:** use ffmpeg to crop the clean area, upscale with lanczos to 1080×1920, and apply unsharp plus the grade (curves that crush lifted blacks, a slight contrast/saturation lift, teal shadows and warm highlights, vignette). Write JPG frames. Never modify the original file.
2. **Masks** (`masks.py`): compute rembg at 540×960 only for frames whose effects need roto. Clean them up: largest component, opening, a height cut, fill holes, and a 3-frame temporal blend.
3. **Audio** (`audio.py`):
   - Cut the dialogue with the same segment list as the picture, with 8 ms fades.
   - Dialogue chain: HPF 80 Hz → light denoise → +2.5 dB at 3 kHz → de-ess → 3:1 compression.
   - If no licensed music was supplied, synthesize an original bed (kick/808/hats/pad at about 96 BPM) and the SFX (whoosh, sub hit, snap, pop, tick, ding, shatter, pings, applause, riser). Duck the music about 10 dB under speech.
   - Two-pass `loudnorm` to −14 LUFS / −1 dBTP, then verify with `ebur128`.
4. **Frames** (`render.py`): a dispatcher picks the scene function by output time. Each scene composites graphics over the plate with eased keyframes (eo/eio/back). Captions are 1–3 word chunks in Inter Display Black with one red pill keyword, a 5-frame pop, and are hidden during full-frame graphics. Render in parallel (Pool(4)) to PNG.

   Test about 25 key frames on a contact sheet *before* the full render, and fix what you see.
5. **Encode:** `noise=alls=3:allf=t` grain, libx264 CRF 16 slow, yuv420p, AAC 320k 48 kHz, `+faststart`.

For a new project, write a thin `render_<project>.py` that `exec`s the reference `render.py` (everything before its `if __name__` block, splitting with `rsplit(..., 1)`) to reuse its helpers, then overrides SEGS/MAP, captions and the scene functions. Re-render only the frame ranges you fix (`render.py <wd> <first> <last>`), then re-encode.

Lessons from QC:
- Source transitions (black frames, wipe stripes) live inside the "clean" footage. Check frames around every source cut and hold the first clean frame under your own transition. Keep the audio as it is.
- White text on frosted glass over bright content washes out. Use dark glass there.
- Don't leave a graphic beat empty for more than about 1.5 s (for example, a chip on a blurred background); bring the next element in on an earlier word.
- A 1 fps sampled sheet can be about 0.5 s off. Judge timing by frame index.

Fallbacks when assets are missing:
- No B-roll: render animated type inside the portal.
- No music: synthesize original music.
- No end-card text: use clearly marked placeholders.

State each fallback in the delivery message.

## Phase 4: QC and deliver

- Build a contact sheet from the **encoded MP4** every 0.5 s, and check every transition.
- Verify caption sync frame by frame around a few chunk onsets (select frames by index). Sampled sheets can mislead by a few frames.
- Check loudness and true peak. Note honestly that you checked the audio by measurement, not by listening.
- Make a before/after sheet (original frame vs finished frame per effect).
- Put the MP4 in the working directory and send it with SendUserFile.
- **If the git repo is public, don't commit footage or renders.** Add `*.mp4`, `*.mov` and `output/` to `.gitignore` and commit only scripts and the plan. Warn the user that the container is ephemeral, so they should download the file.
- Final message: specs, effects used and why, effects not implemented and why, fallbacks used, known flaws, and what would improve it (the original footage, real B-roll, a chosen music track).
