#!/usr/bin/env bash
# Footage analysis for the short-form-video-editor skill.
#   analyze.sh <video> <outdir>                    metadata, contact sheet, frames, loudness map, scene cuts, grid frame
#   analyze.sh caps <video> <outdir> <y> <h> [x w]  timestamped strip sheet of a burned-in caption band (source pixels)
set -euo pipefail

if [[ "${1:-}" == "caps" ]]; then
  V="$2"; O="$3"; Y="$4"; HH="$5"; X="${6:-0}"
  WW="${7:-$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$V")}"
  mkdir -p "$O"
  ffmpeg -v error -y -i "$V" -vf "fps=5,crop=${WW}:${HH}:${X}:${Y},scale=390:-1,drawtext=text='%{pts\:flt}':x=2:y=2:fontsize=13:fontcolor=yellow:box=1:boxcolor=black,tile=4x24" -frames:v 1 "$O/caps.png"
  echo "wrote $O/caps.png (read it; 96 rows of 0.2 s each — make more sheets with -ss for longer clips)"
  exit 0
fi

V="$1"; O="$2"; mkdir -p "$O/frames"
echo "== metadata"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of compact "$V"
W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$V")
ffmpeg -v error -y -i "$V" -vf "fps=1,scale=${W}:-1,tile=10x3" -frames:v 1 "$O/contact.png"
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
