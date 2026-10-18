#!/usr/bin/env bash
# Automated play-test: runs the game with the autopilot for N seconds, records the screen, extracts frames.
# Usage: Tools/run_test.sh [seconds=90] [extra args...]   (e.g. -TwGodPilot)
set -u
SECS=${1:-90}; shift || true
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
OUT=$G/../docs/capture/$(date +%m%d_%H%M%S); mkdir -p "$OUT"
RESX=${RESX:-1600}; RESY=${RESY:-900}
LOG="$OUT/game.log"
"$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" ${MAP:-/Game/Twilight/Maps/L_Vahagn} -game -windowed \
  -ResX=$RESX -ResY=$RESY -WinX=0 -WinY=0 -NoSplash -nosound -unattended -log=TwTest.log \
  -TwAutoPlay=$SECS "$@" > "$LOG" 2>&1 &
PID=$!
# wait for the window
for i in $(seq 1 240); do
  WID=$( (xdotool search --onlyvisible --pid $PID 2>/dev/null; xdotool search --onlyvisible --name 'SF_VULKAN' 2>/dev/null) | head -1)
  [ -n "$WID" ] && grep -q "\[TwTest\] t=" "$LOG" 2>/dev/null && break
  kill -0 $PID 2>/dev/null || break
  sleep 1
done
if [ -n "${WID:-}" ]; then
  eval "$(xdotool getwindowgeometry --shell "$WID")"
  W=$(( WIDTH / 2 * 2 )); H=$(( HEIGHT / 2 * 2 ))
  ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 0 -framerate 20 -video_size ${W}x${H} -i :0.0+${X},${Y} \
    -t "$SECS" -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p "$OUT/run.mp4" &
  FF=$!
fi
wait $PID
[ -n "${FF:-}" ] && { kill -INT $FF 2>/dev/null; wait $FF 2>/dev/null; }
if [ -f "$OUT/run.mp4" ]; then
  mkdir -p "$OUT/frames"
  ffmpeg -hide_banner -loglevel error -y -i "$OUT/run.mp4" -vf fps=1/4 "$OUT/frames/f_%03d.jpg"
  ffmpeg -hide_banner -loglevel error -y -i "$OUT/run.mp4" -vf "fps=1/6,scale=480:-1,tile=4x3" -frames:v 1 "$OUT/contact.jpg"
fi
cp "$G/Saved/TwTestSummary.txt" "$OUT/" 2>/dev/null
grep -E "\[TwTest\]|Error|error:|Ensure|Fatal|crash" "$LOG" | grep -v "LogPython" | tail -60 > "$OUT/highlights.txt"
echo "OUT=$OUT"
cat "$OUT/TwTestSummary.txt" 2>/dev/null
