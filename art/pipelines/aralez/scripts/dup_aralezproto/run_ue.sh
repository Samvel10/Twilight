#!/bin/bash
# run_ue.sh <script.py> [timeout] -- headless python in AralezProto (scratch); log -> logs/<name>.log
A=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez
S=$1; NAME=$(basename $S .py); mkdir -p $A/logs
timeout ${2:-2400} ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd $A/AralezProto/AralezProto.uproject -run=pythonscript -script="$S" -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput > $A/logs/$NAME.log 2>&1
echo "exit $?"
grep -E "ARZ |Error|Traceback|error:" $A/logs/$NAME.log | grep -v -E "LogLinux|Fontconfig|LogInit: Display: Log" | sed 's/.*ARZ /ARZ /' | head -${3:-150}
