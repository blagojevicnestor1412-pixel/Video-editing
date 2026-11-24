import sys, wave, numpy as np, sherpa_onnx
M=sys.argv[1]; w=wave.open(sys.argv[2]); sr=w.getframerate()
a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
rec=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f"{M}/medium-encoder.onnx",decoder=f"{M}/medium-decoder.onnx",tokens=f"{M}/medium-tokens.txt",language="en",num_threads=4)
for x in sys.argv[3:]:
    s,e=map(float,x.split('-'))
    st=rec.create_stream(); st.set_option("max_tokens_per_second","30"); st.accept_waveform(sr,a[int(s*sr):int(e*sr)]); rec.decode_stream(st)
    print(f"{s:6.2f}-{e:6.2f}: {st.result.text.strip()}",flush=True)
