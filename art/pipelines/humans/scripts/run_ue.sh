#!/bin/bash
# run_ue.sh <script.py> [timeout] -- headless python in the scratch project; ONE editor at a time; log -> logs/<name>.log
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans
S=$1; NAME=$(basename $S .py); mkdir -p $P/logs
timeout ${2:-2400} ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd $P/HumansTest/HumansTest.uproject -run=pythonscript -script="$S" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput > $P/logs/$NAME.log 2>&1 &
PID=$!; echo $PID > $P/logs/ue.pid; wait $PID; echo "exit $?"
grep -E "HUM |Error|Traceback|error:" $P/logs/$NAME.log | grep -v -E "LogLinux|Fontconfig|LogInit: Display: Log" | head -${3:-120}
