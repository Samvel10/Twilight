#!/usr/bin/env bash
# Drives the real UI and controls with xdotool (menu click, fly, look, fire, boost, pause) while recording.
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
OUT=$G/../docs/capture/input_$(date +%H%M%S); mkdir -p "$OUT"
"$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -WinX=0 -WinY=40 -NoSplash -unattended -nosound "$@" > "$OUT/game.log" 2>&1 &
PID=$!
for i in $(seq 1 120); do grep -q "LogLoad: Took" "$OUT/game.log" && break; sleep 1; done
sleep 6
WID=$(xdotool search --onlyvisible --name 'SF_VULKAN' | tail -1)
eval "$(xdotool getwindowgeometry --shell "$WID")"
ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 1 -framerate 20 -video_size $((WIDTH/2*2))x$((HEIGHT/2*2)) -i :0.0+${X},${Y} -t 60 -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p "$OUT/run.mp4" < /dev/null &
FF=$!
xdotool windowactivate --sync "$WID"; sleep 1
# click PLAY (menu button, left panel)
xdotool mousemove --window "$WID" 395 459 click 1; sleep 7
# fly forward and look around
xdotool keydown w; sleep 2
for i in $(seq 1 20); do xdotool mousemove_relative -- 25 0; sleep 0.05; done
for i in $(seq 1 10); do xdotool mousemove_relative -- 0 -15; sleep 0.05; done
xdotool keyup w
# fire for 3 s
xdotool mousedown 1; sleep 3; xdotool mouseup 1
# charged shot
xdotool mousedown 3; sleep 1.2; xdotool mouseup 3; sleep 1
# boost forward
xdotool keydown w keydown shift_l; sleep 2; xdotool keyup shift_l keyup w
# climb
xdotool keydown space; sleep 1.5; xdotool keyup space
# turn around and fire
for i in $(seq 1 30); do xdotool mousemove_relative -- -40 0; sleep 0.03; done
xdotool mousedown 1; sleep 3; xdotool mouseup 1
# pause, wait, resume
xdotool key Escape; sleep 2; xdotool key Escape; sleep 2
xdotool mousedown 1; sleep 4; xdotool mouseup 1
sleep 2
kill $PID 2>/dev/null; wait $PID 2>/dev/null
kill -INT $FF 2>/dev/null; wait $FF 2>/dev/null
mkdir -p "$OUT/frames"; ffmpeg -hide_banner -loglevel error -y -i "$OUT/run.mp4" -vf fps=1/2 "$OUT/frames/f_%03d.jpg"
ffmpeg -hide_banner -loglevel error -y -i "$OUT/run.mp4" -vf "fps=1/3,scale=480:-1,tile=4x4" -frames:v 1 "$OUT/contact.jpg"
echo "OUT=$OUT"
