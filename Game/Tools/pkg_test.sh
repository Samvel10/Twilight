#!/usr/bin/env bash
# Autoplay test of the PACKAGED Shipping build: pkg_test.sh <L_Map> <seconds> [extra args]
# Records the window, writes frames + contact sheet + the harness summary into docs/capture/pkg_<map>_<time>.
G=$(cd "$(dirname "$0")/.." && pwd)
MAP=$1; SECS=$2; shift 2
OUT=${OUT:-$G/../docs/capture/pkg_${MAP}_$(date +%H%M%S)}; mkdir -p "$OUT"
SUM=$HOME/.config/Epic/Twilight/Saved/TwTestSummary.txt; rm -f "$SUM"
"$(dirname "$0")/cool_wait.sh" >&2
"$G/../Build/Linux/Twilight.sh" -TwMap=$MAP -windowed -ResX=1600 -ResY=900 -WinX=0 -WinY=0 -nosound -TwAutoPlay=$SECS "$@" > "$OUT/game.log" 2>&1 &
W=""; for i in $(seq 1 90); do P=$(pidof Twilight-Linux-Shipping); [ -n "$P" ] && W=$(xdotool search --onlyvisible --pid $P 2>/dev/null | tail -1); [ -n "$W" ] && break; sleep 1; done
sleep 2; xdotool windowactivate --sync "$W" 2>/dev/null; xdotool windowraise "$W"; sleep 0.5; eval "$(xdotool getwindowgeometry --shell "$W")"
ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 0 -framerate 20 -video_size $((WIDTH/2*2))x$((HEIGHT/2*2)) -i :0.0+${X},${Y} -t $((SECS + 15)) -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p "$OUT/run.mp4" < /dev/null
for i in $(seq 1 20); do pidof Twilight-Linux-Shipping >/dev/null || break; sleep 1; done
P=$(pidof Twilight-Linux-Shipping); [ -n "$P" ] && { echo "WARN: still running, killing"; kill $P; }
ffmpeg -hide_banner -loglevel error -y -i "$OUT/run.mp4" -vf "fps=1/5,scale=400:-1,tile=6x6" -frames:v 1 "$OUT/contact.jpg"
cp "$SUM" "$OUT/" 2>/dev/null; echo "OUT=$OUT"; cat "$SUM" 2>/dev/null || echo "no summary"
