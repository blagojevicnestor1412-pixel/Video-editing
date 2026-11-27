"""Finish an Instagram snippet: burn in word-by-word subtitles and swap in the updated outro.

    python3 reel_snippet.py SNIPPET.mp4 WORDS.json OUT.mp4 [OUTRO_START_SECONDS]

* WORDS.json: [{"text", "start", "end"}, ...] (word timings from Whisper, text checked by hand)
* every frame from OUTRO_START on is re-rendered with reel_outro.render_at() (native frame rate)
* the old outro's "LINK U BIO" sounds are cancelled from the snippet's audio by subtracting
  (old outro SFX - new outro SFX), aligned to the sample; music and the other sounds stay untouched.
"""
import json
import math
import subprocess
import sys

import numpy as np
import skia
from scipy import signal
from scipy.io import wavfile

import reel_outro as RO
from render import TF_MONT, clamp, ease_out_back, ease_out_cubic, prog

W, H = 1080, 1920
SUB_Y = 1330            # subtitle baseline (inside the Reels safe area)
MAX_W = 860
WHITE, YELLOW = (255, 255, 255), (255, 210, 31)
CHUNKS = [2, 2, 2, 3, 1, 2, 3, 1, 2, 1, 3, 2, 1, 4, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2]
SHOUT_FROM = 33          # word index where the "udavi ga" shouting starts


def clean(t):
    t = t.upper()
    if t.endswith("!"):
        return t
    if t.rstrip(",").isdigit():      # keep the commas in "83, 77, 91"
        return t.rstrip(".")
    return t.rstrip(".,")


def build_chunks(words):
    chunks, i = [], 0
    for n in CHUNKS:
        ws = words[i:i + n]
        chunks.append({"words": ws, "start": ws[0]["start"], "end": ws[-1]["end"], "shout": i >= SHOUT_FROM})
        i += n
    assert i == len(words), (i, len(words))
    for k, c in enumerate(chunks):
        nxt = chunks[k + 1]["start"] if k + 1 < len(chunks) else c["end"] + 0.5
        c["show_from"] = max(0.0, c["start"] - 0.05)
        c["show_to"] = nxt - 0.05 if nxt - c["end"] < 0.6 else c["end"] + 0.35
    if chunks:
        last = chunks[-1]["words"][-1]
        last["text"] = last["text"].rstrip(".,") + "!"
    return chunks


def draw_chunk(cv, c, t):
    k_in = prog(t, c["show_from"], c["show_from"] + 0.14)
    k_out = prog(t, c["show_to"] - 0.06, c["show_to"])
    if k_in <= 0 or k_out >= 1:
        return
    size = 106 if c["shout"] else 96
    font = skia.Font(TF_MONT, size)
    texts = [clean(w["text"]) for w in c["words"]]
    space = font.measureText(" ")
    widths = [font.measureText(x) for x in texts]
    total = sum(widths) + space * (len(texts) - 1)
    fit = min(1.0, MAX_W / total)
    s = ease_out_back(k_in, 2.2) * fit * (1 - 0.15 * k_out)
    al = clamp(k_in * 3) * (1 - k_out)
    cv.save()
    cv.translate(W / 2, SUB_Y - size * 0.35)
    if c["shout"]:
        cv.rotate(math.sin(t * 38) * 1.6 * (1 - ease_out_cubic(prog(t, c["start"], c["start"] + 0.35))) + (-2 if c["start"] % 1 > 0.5 else 2))
    cv.scale(s, s)
    x = -total / 2
    for txt, w, wd in zip(texts, widths, c["words"]):
        active = wd["start"] - 0.03 <= t < max(wd["end"], wd["start"] + 0.12)
        pk = prog(t, wd["start"] - 0.03, wd["start"] + 0.09)
        ws = 1 + 0.10 * math.sin(pk * math.pi) if active else 1.0
        col = YELLOW if (active or t >= wd["end"] and c["shout"]) else WHITE
        cv.save()
        cv.translate(x + w / 2, 0)
        cv.scale(ws, ws)
        ox, oy = -w / 2, size * 0.35
        sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, int(160 * al)))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        sh.setStyle(skia.Paint.kStrokeAndFill_Style)
        sh.setStrokeWidth(18)
        cv.drawString(txt, ox + 3, oy + 9, font, sh)
        st = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, int(255 * al)), Style=skia.Paint.kStroke_Style,
                        StrokeWidth=17, StrokeJoin=skia.Paint.kRound_Join)
        cv.drawString(txt, ox, oy, font, st)
        cv.drawString(txt, ox, oy, font, skia.Paint(AntiAlias=True, Color=skia.Color(*col, int(255 * al))))
        cv.restore()
        x += w + space
    cv.restore()


def write_srt(chunks, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w", encoding="utf-8") as fh:
        for n, c in enumerate(chunks, 1):
            fh.write(f"{n}\n{ts(c['show_from'])} --> {ts(c['show_to'])}\n{' '.join(clean(w['text']) for w in c['words'])}\n\n")


def fix_audio(snippet, out_wav):
    wav = out_wav + ".in.wav"
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", snippet, "-vn", "-ac", "2", "-ar", "48000", wav])
    sr, a = wavfile.read(wav)
    a = a.astype(np.float64) / 32768
    _, old = wavfile.read(f"{RO.OUT}/sfx_link.wav")
    _, new = wavfile.read(f"{RO.OUT}/sfx.wav")
    old, new = old.astype(np.float64) / 32768, new.astype(np.float64) / 32768
    m, r = a.mean(1), old.mean(1)
    c = signal.correlate(m, r[:sr * 3], mode="valid", method="fft")
    lag = int(np.argmax(c))
    seg = a[lag:lag + len(old)]
    n = len(seg)
    g = float((seg * old[:n]).sum() / (old[:n] ** 2).sum())
    diff = (old - new)[:n]
    a[lag:lag + n] -= g * diff
    print(f"outro SFX found at {lag / sr:.4f}s, gain {g:.3f}; removed LINK-button sounds")
    wavfile.write(out_wav, sr, (np.clip(a, -1, 1) * 32767).astype(np.int16))
    return lag / sr


def main():
    snippet, words_json, out = sys.argv[1:4]
    outro_start = float(sys.argv[4]) if len(sys.argv) > 4 else None
    words = json.load(open(words_json, encoding="utf-8"))
    chunks = build_chunks(words)
    write_srt(chunks, out.rsplit(".", 1)[0] + ".srt")
    fps_num, fps_den = 60000, 1001
    probe = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                     "stream=r_frame_rate,nb_frames", "-of", "csv=p=0", snippet]).decode().strip()
    rate, nb = probe.split(",")
    fps_num, fps_den = (int(x) for x in rate.split("/"))
    nb = int(nb)
    audio = out + ".audio.wav"
    fix_audio(snippet, audio)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", snippet, "-vf",
                            "scale=in_color_matrix=bt709:in_range=tv,format=rgba", "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", f"{fps_num}/{fps_den}", "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest", out],
                           stdin=subprocess.PIPE)
    fsz = W * H * 4
    prev_dark = None
    for i in range(nb):
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        t = i * fps_den / fps_num
        frame = np.frombuffer(buf, np.uint8).reshape(H, W, 4).copy()
        if outro_start is None and t > 15:
            # first near-black frame after the footage = outro fade-in
            if frame[::8, ::8, :3].mean() < 18:
                outro_start = t
                print(f"outro starts at {t:.3f}s (frame {i})")
        if outro_start is not None and t >= outro_start - 1e-6:
            to = t - outro_start
            frame = RO.render_at(to, int(to * 30))
        else:
            surf = skia.Surface(frame, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
            cv = surf.getCanvas()
            for c in chunks:
                if c["show_from"] <= t < c["show_to"]:
                    draw_chunk(cv, c, t)
            del cv, surf
        enc.stdin.write(np.ascontiguousarray(frame).tobytes())
        if i % 120 == 0:
            print("frame", i, flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("done")


if __name__ == "__main__":
    main()
