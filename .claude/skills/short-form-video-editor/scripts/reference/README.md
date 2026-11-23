# Reference implementation

This is a working pipeline from the first project: a 19 s Serbian jiu-jitsu podcast clip recorded off Instagram at 292×632, rendered to 1080×1920. It was tested again on a second project, a 48 s TikTok ad download. Copy these files and adapt their data tables; don't rewrite them from scratch.

| File | What it does | What to change per project |
|---|---|---|
| `masks.py <workdir>` | rembg person masks at 540×960 for the needed frames → `mask/NNNN.png` | The `need` frame set |
| `mock.py <dir>` | Concept-mockup stills from graded frames (`grd_<t>.png`) | Frame times, coordinates, text |
| `build_page.py <data.py> <out.html>` | Storyboard HTML: timeline SVG, scene cards, specs, effects audit | Nothing. Write a data file instead: copy `data_jiujitsu.py` |
| `data_jiujitsu.py` | Example storyboard data: segments, scenes, effects audit, transcript, page copy | Everything, per project |
| `audio.py <workdir>` | Dialogue edit and cleanup, synthesized music and SFX, ducking → `mix_pre.wav` | `SEGS`, SFX `place(...)` times, key/BPM |
| `render.py <workdir>` | Parallel frame renderer → `frames/NNNN.png` | `SEGS`, `CAPS`, `HIDE`, scene functions, the dispatcher's time ranges |

The workdir needs `source.mov`, `base/NNNN.jpg` (graded 1080×1920 plates, 1-based), and `mask/`.

Base-plate command (set the crop to the measured clean area):
```
ffmpeg -i source.mov -vf "crop=W:H:X:Y,scale=1080:1920:flags=lanczos,unsharp=7:7:0.8:5:5:0.0,curves=all='0/0 0.07/0.02 0.5/0.49 0.9/0.92 1/0.98',eq=contrast=1.06:saturation=1.04,colorbalance=rs=-0.02:bs=0.035:rh=0.02,vignette=PI/4.5" -q:v 2 base/%04d.jpg
```
Loudness, two passes: `loudnorm=I=-14:TP=-1:LRA=11` measure, then apply with `measured_*` values and `linear=true`.

Encode:
```
ffmpeg -framerate 30 -i frames/%04d.png -i mix.wav -vf "noise=alls=3:allf=t,format=yuv420p" -c:v libx264 -preset slow -crf 16 -profile:v high -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart out.mp4
```
