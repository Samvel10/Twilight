#!/usr/bin/env bash
# Monkey test on the PACKAGED build: random real mouse/keyboard input for N seconds, frames every 3 s.
# Usage: chaos_test.sh <L_Map> <seconds> [seed]
G=$(cd "$(dirname "$0")/.." && pwd)
MAP=$1; SECS=$2; SEED=${3:-1}; RANDOM=$SEED
OUT=$G/../docs/capture/chaos_${MAP}_$(date +%H%M%S); mkdir -p "$OUT/f"
"$G/../Build/Linux/Twilight.sh" -TwMap=$MAP -windowed -ResX=1600 -ResY=900 -WinX=0 -WinY=0 -nosound > "$OUT/game.log" 2>&1 &
W=""; for i in $(seq 1 90); do P=$(pidof Twilight-Linux-Shipping); [ -n "$P" ] && W=$(xdotool search --onlyvisible --pid $P 2>/dev/null | tail -1); [ -n "$W" ] && break; sleep 1; done
sleep 4; eval "$(xdotool getwindowgeometry --shell "$W")"; xdotool windowactivate "$W"; sleep 0.5
# press the chapter's first menu button (PLAY / vs bot); START="x y" in window coords
read SX SY <<< "${START:-395 459}"
xdotool mousemove $((X + SX)) $((Y + SY)); sleep 0.3; xdotool mousedown 1; sleep 0.15; xdotool mouseup 1; sleep 6
KEYS=(w a s d space ctrl Shift_L q Escape w w d a)
END=$((SECONDS + SECS)); n=0; LAST=$SECONDS
while [ $SECONDS -lt $END ]; do
  pidof Twilight-Linux-Shipping >/dev/null || { echo "CRASH/EXIT at $((SECS - (END - SECONDS)))s"; break; }
  r=$((RANDOM % 10))
  if [ $r -lt 3 ]; then xdotool mousemove $((X + WIDTH * 2 / 5 + RANDOM % (WIDTH * 3 / 5 - 100))) $((Y + 100 + RANDOM % (HEIGHT - 200)))
  elif [ $r -lt 5 ]; then b=$((RANDOM % 2 == 0 ? 1 : 3)); xdotool mousedown $b; sleep 0.$((RANDOM % 9 + 1)); xdotool mouseup $b
  elif [ $r -lt 6 ]; then xdotool click 1
  else k=${KEYS[$((RANDOM % ${#KEYS[@]}))]}; xdotool keydown $k; sleep 0.$((RANDOM % 9 + 1)); xdotool keyup $k; fi
  sleep 0.1
  if [ $((SECONDS - LAST)) -ge 3 ]; then LAST=$SECONDS; n=$((n+1)); ffmpeg -hide_banner -loglevel error -y -f x11grab -video_size ${WIDTH}x${HEIGHT} -i :0.0+${X},${Y} -frames:v 1 "$OUT/f/$(printf %03d $n).jpg"; fi
done
ALIVE=$(pidof Twilight-Linux-Shipping)
[ -n "$ALIVE" ] && echo "alive after ${SECS}s" && kill $ALIVE
ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$OUT/f/*.jpg" -vf "scale=400:-1,tile=8x6" -frames:v 1 "$OUT/contact.jpg"
echo "OUT=$OUT"
