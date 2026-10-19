#!/bin/bash
# prof.sh <tag> "<set1>#<set2>..."  each set = view|cvar a=cvar restore;...|hidePrefix,...   -> per-set GPU pass table
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands
export HL_PROF=1 HL_PROF_SET="$2"
LOG=$P/ue/Saved/Logs/Highlands.log; rm -f $P/ue/Saved/Autosaves/PackageRestoreData.json
~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $P/ue/Highlands.uproject /Game/Test/L_Highlands -unattended -nop4 -nosplash -nosound -RenderOffscreen -windowed -ResX=1920 -ResY=1080 > $P/prof_$1.out 2>&1 &
PID=$!; echo $PID > $P/editor.pid; sleep 15
for i in $(seq 1 1500); do kill -0 $PID 2>/dev/null || break; grep -q "HLP ALLDONE" $LOG 2>/dev/null && { sleep 3; break; }; sleep 1; done
kill $PID 2>/dev/null; sleep 3; kill -9 $PID 2>/dev/null
cp $LOG $P/perf/prof_$1.log; python3 -I $P/scripts/gpuprof_parse.py $P/perf/prof_$1.log
