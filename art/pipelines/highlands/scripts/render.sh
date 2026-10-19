#!/bin/bash
# render.sh <tag> <cams csv> : GUI editor (offscreen) on the scratch map, takes shots, exits (single instance, killed by PID)
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands
export HL_TAG=$1 HL_CAMS=$2 HL_RENDER=1
LOG=$P/render_$1.log; rm -rf $P/ue/Saved/Autosaves/PackageRestoreData.json $P/ue/Saved/Crashes/*
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/ue/Highlands.uproject ${MAP:-/Game/Test/L_Highlands} \
  -unattended -nop4 -nosplash -nosound -RenderOffscreen -windowed -ResX=1280 -ResY=800 > $LOG 2>&1 &
PID=$!
echo "pid $PID"; echo $PID > $P/editor.pid
sleep 15
for i in $(seq 1 ${TMO:-1200}); do
  if ! kill -0 $PID 2>/dev/null; then break; fi
  grep -q "HLR ALLDONE" $P/ue/Saved/Logs/Highlands.log 2>/dev/null && { sleep 5; break; }
  sleep 1
done
kill $PID 2>/dev/null; sleep 3; kill -9 $PID 2>/dev/null
grep "HLR" $P/ue/Saved/Logs/Highlands.log | grep -v "LogInit: Display" | tail -30
