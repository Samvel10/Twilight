#!/bin/bash
# perf.sh <map> <tag> [wait] -- run -game, then type 'profilegpu' (x3) into the console; the per-pass GPU profile lands in logs/perf_<tag>.log
F=$(cd "$(dirname "$0")/../.." && pwd); P=$F/FireHair; MAP=$1; TAG=$2; WAIT=${3:-30}
/var/www/html/Twilight/Game/Tools/cool_wait.sh >/dev/null
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/FireHair.uproject /Game/Proto/$MAP -game -windowed -ResX=1600 -ResY=900 -WinX=40 -WinY=40 -nosound -nosplash -unattended -NoVerifyGC -ExecCmds="r.ScreenPercentage 100" > $F/logs/perf_$TAG.log 2>&1 &
PID=$!; echo $PID > $F/logs/ue.pid
for i in $(seq 1 300); do WID=$(xdotool search --all --pid $PID --onlyvisible --name '^FireHair ' 2>/dev/null | tail -1); [ -n "$WID" ] && break; sleep 1; done
sleep $WAIT; WID=$(xdotool search --all --pid $PID --onlyvisible --name '^FireHair ' 2>/dev/null | tail -1)
xdotool windowactivate --sync $WID 2>/dev/null; sleep 1
xdotool key --window $WID grave; sleep 0.5; for k in 1 2 3; do xdotool type --window $WID --delay 40 "profilegpu"; xdotool key --window $WID Return; sleep 4; done
kill $PID; sleep 2; kill -9 $PID 2>/dev/null; wait $PID 2>/dev/null
grep -c "Perf: " $F/logs/perf_$TAG.log
