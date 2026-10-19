#!/bin/bash
# run_ue.sh <script.py> [timeout] -- headless editor python in the FireHair scratch project (ONE UE at a time); log -> logs/<name>.log
F=$(cd "$(dirname "$0")/../.." && pwd); P=$F/FireHair
S=$(readlink -f $1); NAME=$(basename $S .py); mkdir -p $F/logs
/var/www/html/Twilight/Game/Tools/cool_wait.sh
timeout ${2:-2400} ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd $P/FireHair.uproject -run=pythonscript -script="$S" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput > $F/logs/$NAME.log 2>&1 &
PID=$!; echo $PID > $F/logs/ue.pid; wait $PID; echo "exit $?"
grep -E "FH |Error|Traceback|error:" $F/logs/$NAME.log | grep -v -E "LogLinux|Fontconfig|LogInit: Display: Log" | head -${3:-120}
