#!/bin/bash
# shoot.sh <map> <out> [wait] -- run -game on /Game/Proto/<map>, grab window to shots/<out>.png, kill by PID. env EXEC = extra console cmds
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans
MAP=$1; OUT=$2; WAIT=${3:-25}
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/HumansTest/HumansTest.uproject /Game/Proto/$MAP -game -windowed -ResX=${RESX:-1600} -ResY=${RESY:-900} -WinX=40 -WinY=40 -nosound -nosplash -unattended -NoVerifyGC -ExecCmds="${EXEC:-r.ScreenPercentage 100}" > $P/logs/game_$OUT.log 2>&1 &
PID=$!; echo $PID > $P/logs/ue.pid
WID=""; for i in $(seq 1 300); do WID=$(xdotool search --pid $PID --onlyvisible --name 'HumansTest' 2>/dev/null | tail -1); [ -n "$WID" ] && break; kill -0 $PID 2>/dev/null || break; sleep 1; done
if [ -z "$WID" ]; then echo "no window"; kill $PID 2>/dev/null; exit 1; fi
sleep $WAIT
eval "$(xdotool getwindowgeometry --shell "$WID")"
xdotool windowactivate $WID 2>/dev/null; xdotool windowraise $WID 2>/dev/null; wmctrl -i -r $WID -b add,above 2>/dev/null; sleep 2
xwd -silent -id $WID -out $P/logs/$OUT.xwd && ffmpeg -hide_banner -loglevel error -y -i $P/logs/$OUT.xwd $P/shots/$OUT.png   # no screen-grab fallback: it can capture other agents windows
rm -f $P/logs/$OUT.xwd
kill $PID; sleep 2; kill -9 $PID 2>/dev/null; wait $PID 2>/dev/null
echo "shot $P/shots/$OUT.png ${WIDTH}x${HEIGHT}"
