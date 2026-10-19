#!/bin/bash
# perf.sh <view> [hide-prefixes] [tag] : -game 1600x900 (game scalability), CSV profile with GPU pass stats, prints steady-state frame/GPU ms
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands
E=~/UnrealEngine-5.8/Engine/Binaries/Linux; CSVD=~/UnrealEngine-5.8/Engine/Saved/Profiling/CSV
TAG=${3:-$1}
HL_PERFVIEW=$1 HL_HIDE=$2 timeout 900 $E/UnrealEditor-Cmd $P/ue/Highlands.uproject -ExecutePythonScript=$P/scripts/perf_set.py -unattended -nop4 -nosplash -nosound -nullrhi > $P/perf_set.log 2>&1
grep -q "PERF set" $P/perf_set.log || { echo "perf_set failed"; exit 1; }
T0=$(date +%s); L=$P/perf/$TAG.log; mkdir -p $P/perf
$E/UnrealEditor $P/ue/Highlands.uproject /Game/Test/L_Highlands -game -windowed -ResX=1600 -ResY=900 -nosplash -unattended -nosound -csvCaptureFrames=2100 -csvGpuStats > $L 2>&1 &
PID=$!; echo $PID > $P/editor.pid
for i in $(seq 1 420); do sleep 1; grep -q "Writing CSV to file" $L && break; kill -0 $PID 2>/dev/null || break; done
sleep 2; kill $PID 2>/dev/null; sleep 3; kill -9 $PID 2>/dev/null
F=$(find $CSVD -name '*.csv' -newermt "@$T0" | head -1)
[ -n "$F" ] && mv "$F" $P/perf/$TAG.csv && python3 -I $P/scripts/csvstat.py $P/perf/$TAG.csv 1200 | tail -3
