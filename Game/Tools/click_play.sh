#!/usr/bin/env bash
# Launch Vahagn, click PLAY with the real mouse, play a short scripted sequence, grab frames + log.
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
S=${OUT:-$G/../docs/capture/click_$(date +%H%M%S)}; mkdir -p "$S"
"$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -NoSplash -unattended -nosound "$@" > "$S/game.log" 2>&1 &
PID=$!
for i in $(seq 1 120); do grep -q "LogLoad: Took" "$S/game.log" && break; sleep 1; done; sleep 5
WID=$(xdotool search --onlyvisible --name 'SF_VULKAN' | tail -1); eval "$(xdotool getwindowgeometry --shell $WID)"
grab(){ ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 0 -video_size ${WIDTH}x${HEIGHT} -i :0.0+${X},${Y} -frames:v 1 "$S/$1.jpg"; }
xdotool windowactivate $WID; sleep 0.5
xdotool mousemove $((X+395)) $((Y+459)); sleep 0.5; xdotool mousedown 1; sleep 0.15; xdotool mouseup 1
for t in 1 2 3 4 5 6 7 8 9 10 11 12; do sleep 1; grab t$t; done
xdotool keydown w; sleep 1.5; grab fly; for i in $(seq 1 15); do xdotool mousemove_relative -- 30 0; sleep 0.04; done; xdotool keyup w
xdotool mousedown 1; sleep 1.5; grab fire; xdotool mouseup 1
xdotool keydown w keydown Shift_L; sleep 1.2; grab boost; xdotool keyup Shift_L keyup w
xdotool mousedown 3; sleep 1.0; grab charge; xdotool mouseup 3; sleep 0.4; grab charged
sleep 8; grab later
kill $PID 2>/dev/null; wait $PID 2>/dev/null
echo "OUT=$S"; grep -E "TwDmg|TwTest|TwUi" "$S/game.log" | head -20
