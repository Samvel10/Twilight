#!/bin/bash
# shoot.sh <map> <out name> [wait secs] [extra frames]: launch the scratch project in -game on the map, grab the window with xwd, kill by PID
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez
MAP=$1; OUT=$2; WAIT=${3:-25}; FR=${4:-0}
mkdir -p $P/shots $P/logs
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/ue/AralezTest.uproject /Game/Aralez/Maps/$MAP -game -windowed -ResX=${RX:-1600} -ResY=${RY:-900} -WinX=40 -WinY=40 -nosound -nosplash -unattended -NoVerifyGC -ExecCmds="${EXEC:-r.ScreenPercentage 100}" > $P/logs/game_$OUT.log 2>&1 &
PID=$!; echo $PID > $P/logs/ue.pid
WID=""; for i in $(seq 1 300); do WID=$(xdotool search --pid $PID --onlyvisible --name 'AralezTest' 2>/dev/null | tail -1); [ -n "$WID" ] && break; kill -0 $PID 2>/dev/null || break; sleep 1; done
if [ -z "$WID" ]; then echo "no window"; kill $PID 2>/dev/null; sleep 2; kill -9 $PID 2>/dev/null; exit 1; fi
sleep $WAIT
eval "$(xdotool getwindowgeometry --shell "$WID")"
xdotool windowactivate $WID 2>/dev/null; xdotool windowraise $WID 2>/dev/null; wmctrl -i -r $WID -b add,above 2>/dev/null; sleep 2
grab() { xwd -silent -id $WID -out /dev/shm/arz_$1.xwd && ffmpeg -hide_banner -loglevel error -y -i /dev/shm/arz_$1.xwd $P/shots/$1.png; rm -f /dev/shm/arz_$1.xwd; }
grab $OUT
for k in $(seq 1 $FR); do sleep ${FSTEP:-0.25}; grab ${OUT}_f$k; done
grep -a "Failed to compile" $P/logs/game_$OUT.log | cut -c1-250 | sort -u | head -5
kill $PID; sleep 3; kill -9 $PID 2>/dev/null; wait $PID 2>/dev/null
echo "shot $P/shots/$OUT.png ${WIDTH}x${HEIGHT}"
