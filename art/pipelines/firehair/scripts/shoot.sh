#!/bin/bash
# shoot.sh <map> <out> [wait] -- run -game on /Game/Proto/<map>, grab ONLY our window (xwd by window id) to deliver/shots/<out>.png, kill by PID.
# env EXEC = extra console commands, RESX/RESY. -ExecutePythonScript does not work in -game: scenes are built by the editor-cmd scripts.
F=$(cd "$(dirname "$0")/../.." && pwd); P=$F/FireHair; OUTD=${OUTD:-$F/deliver/shots}; mkdir -p $OUTD $F/logs
MAP=$1; OUT=$2; WAIT=${3:-25}
/var/www/html/Twilight/Game/Tools/cool_wait.sh
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/FireHair.uproject /Game/Proto/$MAP -game -windowed -ResX=${RESX:-1600} -ResY=${RESY:-900} -WinX=40 -WinY=40 -nosound -nosplash -unattended -NoVerifyGC -ExecCmds="${EXEC:-r.ScreenPercentage 100}" > $F/logs/game_$OUT.log 2>&1 &
PID=$!; echo $PID > $F/logs/ue.pid
WID=""; for i in $(seq 1 300); do WID=$(xdotool search --all --pid $PID --onlyvisible --name '^FireHair ' 2>/dev/null | tail -1); [ -n "$WID" ] && break; kill -0 $PID 2>/dev/null || break; sleep 1; done
if [ -z "$WID" ]; then echo "no window"; kill $PID 2>/dev/null; exit 1; fi
sleep $WAIT
W2=$(xdotool search --all --pid $PID --onlyvisible --name '^FireHair ' 2>/dev/null | tail -1); [ -n "$W2" ] && WID=$W2
xdotool windowactivate $WID 2>/dev/null; xdotool windowraise $WID 2>/dev/null; wmctrl -i -r $WID -b add,above 2>/dev/null; sleep 2
for k in ${SHOTS:-0}; do [ "$k" != 0 ] && sleep $k; xwd -silent -id $WID -out $F/logs/$OUT.xwd && ffmpeg -hide_banner -loglevel error -y -i $F/logs/$OUT.xwd $OUTD/$OUT${SHOTS:+_$k}.png; done
rm -f $F/logs/$OUT.xwd
kill $PID; sleep 2; kill -9 $PID 2>/dev/null; wait $PID 2>/dev/null
echo "shot $OUTD/$OUT.png"
