#!/usr/bin/env bash
# Footage analysis for the short-form-video-editor skill.
#   analyze.sh <video> <outdir>                    metadata, contact sheet, frames, loudness map, scene cuts, grid frame
#   analyze.sh caps <video> <outdir> <y> <h> [x w]  timestamped strip sheet of a burned-in caption band (source pixels)
set -euo pipefail

if [[ "${1:-}" == "caps" ]]; then
  V="$2"; O="$3"; Y="$4"; HH="$5"; X="${6:-0}"
  WW="${7:-$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$V")}"
  mkdir -p "$O"
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
  N=$(python3 -c "import math;print(math.ceil(float('$DUR')/15))")
  for k in $(seq 0 $((N-1))); do
    ffmpeg -v error -y -ss $((k*15)) -t 15 -i "$V" -vf "fps=5,crop=${WW}:${HH}:${X}:${Y},scale=400:-1,drawtext=text='%{eif\\:t+$((k*15))\\:d}.%{eif\\:mod(t*10\\,10)\\:d}':x=2:y=2:fontsize=14:fontcolor=yellow:box=1:boxcolor=black,tile=5x15" -frames:v 1 "$O/caps_$k.png"
  done
  echo "wrote $O/caps_0..$((N-1)).png (15 s per sheet, 0.2 s per cell, timestamps in source seconds)"
  exit 0
fi

V="$1"; O="$2"; mkdir -p "$O/frames"
echo "== metadata"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of compact "$V"
W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$V")
DUR0=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
ROWS=$(python3 -c "import math;print(max(1,math.ceil(float('$DUR0')/10)))")
ffmpeg -v error -y -i "$V" -vf "fps=1,scale=180:-1,drawtext=text='%{pts\\:flt}':x=3:y=3:fontsize=13:fontcolor=yellow:box=1:boxcolor=black,tile=10x${ROWS}" -frames:v 1 "$O/contact.png"
ffmpeg -v error -y -i "$V" -vf fps=2 "$O/frames/f_%04d.png"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
MID=$(python3 -c "print(float('$DUR')/2)")
ffmpeg -v error -y -ss "$MID" -i "$V" -frames:v 1 -vf "scale=iw*2:ih*2,drawgrid=w=iw/10:h=ih/20:color=yellow@0.5" "$O/grid.png"
echo "== scene cuts (seconds)"
ffmpeg -i "$V" -vf "select='gt(scene,0.08)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | cut -d: -f2 | tr '\n' ' '; echo
echo "== loudness per 100 ms (dB); runs below about -30 are pauses"
ffmpeg -v error -y -i "$V" -ac 1 -ar 16000 "$O/audio.wav"
python3 -I - "$O/audio.wav" <<'EOF'
import sys, wave, numpy as np
w = wave.open(sys.argv[1]); a = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
n = 1600
print(" ".join(f"{i/10:.1f}:{20*np.log10(np.sqrt(np.mean(a[i*n:(i+1)*n]**2))+1e-9):.0f}" for i in range(len(a)//n)))
EOF
echo "wrote $O/contact.png, $O/grid.png (2x, 10x20 grid for measuring crop), $O/frames/, $O/audio.wav"
