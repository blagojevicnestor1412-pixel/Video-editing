import sys,json
from faster_whisper import WhisperModel
m=WhisperModel(sys.argv[2],device="cpu",compute_type="int8")
segs,info=m.transcribe(sys.argv[1],language="sr",word_timestamps=True,beam_size=5)
out=[]
for s in segs:
    for w in s.words: out.append([round(w.start,2),round(w.end,2),w.word])
    print(f"[{s.start:5.2f}-{s.end:5.2f}] {s.text}")
json.dump(out,open(sys.argv[3],"w"),ensure_ascii=False)
