import sys, wave, json, numpy as np, sherpa_onnx
M = sys.argv[1]; wav = sys.argv[2]; out = sys.argv[3]
w = wave.open(wav); sr = w.getframerate()
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
a = a[: int(float(sys.argv[4]) * sr)] if len(sys.argv) > 4 else a
hop = int(0.02 * sr)
db = np.array([20 * np.log10(np.sqrt(np.mean(a[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(a) - hop, hop)])
quiet = db < -30
# segments: split at quiet runs >= 0.12 s, then merge to min 1.2 s chunks
cuts = []; i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]: j += 1
        if j - i >= 6: cuts.append(((i + j) / 2) * 0.02)
        i = j
    else: i += 1
bounds = [0.0] + cuts + [len(a) / sr]
segs = []
s = bounds[0]
for b in bounds[1:]:
    if b - s >= 0.9 or b == bounds[-1]:
        segs.append((s, b)); s = b
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{M}/medium-encoder.onnx",
    decoder=f"{M}/medium-decoder.onnx", tokens=f"{M}/medium-tokens.txt",
    language="sr", task="transcribe", num_threads=4)
res = []
for s, e in segs:
    st = rec.create_stream(); st.set_option("max_tokens_per_second","30"); st.accept_waveform(sr, a[int(s * sr):int(e * sr)])
    rec.decode_stream(st)
    t = st.result.text.strip()
    # voiced frames inside the segment, for word timing
    print(f"{s:6.2f}-{e:6.2f}: {t}", flush=True)
    res.append({"s": s, "e": e, "text": t})
json.dump({"segs": res, "db": db.tolist()}, open(out, "w"), ensure_ascii=False)
