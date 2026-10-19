#!/bin/bash
# shot.sh <name> [extra serp args...] : runs the proto in -game offscreen, saves shots/<name>.png, prints SERP log lines.
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent
N=$1; shift
mkdir -p $P/shots $P/notes/logs
rm -f $P/shots/$N.png
SHOTAT=${SHOTAT:-12}; QUIT=$(echo "$SHOTAT+3" | bc)
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/SerpentProto/SerpentProto.uproject /Game/Proto/Maps/L_Sky -game ${WINDOW:--RenderOffscreen} \
  -ResX=${RESX:-1600} -ResY=${RESY:-900} -windowed -nosound -nosplash -unattended -NoVerifyGC -NoLiveCoding \
  -SerpShotAt=$SHOTAT -SerpQuitAt=$QUIT -SerpShot=$P/shots/$N.png "$@" -ExecCmds="${EXEC:-r.SetRes 1600x900w,r.ScreenPercentage 100}" > $P/notes/logs/$N.log 2>&1 &
PID=$!; echo $PID > $P/notes/ue.pid
for i in $(seq 1 ${TMO:-400}); do kill -0 $PID 2>/dev/null || break; sleep 1; done
kill $PID 2>/dev/null; sleep 2; kill -9 $PID 2>/dev/null
grep -a "SERP \|Fatal\|Assertion" $P/notes/logs/$N.log | cut -c1-200 | tail -${TAILN:-8}
ls -la $P/shots/$N.png 2>/dev/null
