#!/usr/bin/env bash
# shot.sh <name> <wait-seconds> [extra args]: launches the game, grabs a frame after N s of autoplay, quits.
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
NAME=$1; WAIT=$2; shift 2
OUT=$G/../docs/capture/shots; mkdir -p "$OUT"
LOG=$OUT/$NAME.log
"$(dirname "$0")/cool_wait.sh" >&2
"$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" ${MAP:-/Game/Twilight/Maps/L_Vahagn} -game -windowed -ResX=1600 -ResY=900 -WinX=0 -WinY=40 \
  -NoSplash -unattended -nosound ${NOAUTO:+-TwNoAuto} $([ -z "$NOAUTO" ] && echo "-TwAutoPlay=$((WAIT+20)) -TwGodPilot") "$@" > "$LOG" 2>&1 &
PID=$!
for i in $(seq 1 180); do grep -q "\[TwTest\]\|LogLoad: Took" "$LOG" 2>/dev/null && break; sleep 1; done
sleep "$WAIT"
WID=$(xdotool search --onlyvisible --pid $PID 2>/dev/null | tail -1); [ -z "$WID" ] && WID=$(xdotool search --onlyvisible --name 'SF_VULKAN' | tail -1)
eval "$(xdotool getwindowgeometry --shell "$WID")"
ffmpeg -hide_banner -loglevel error -y -f x11grab -video_size ${WIDTH}x${HEIGHT} -i :0.0+${X},${Y} -frames:v 1 "$OUT/$NAME.jpg"
kill $PID 2>/dev/null; wait $PID 2>/dev/null
echo "$OUT/$NAME.jpg"
