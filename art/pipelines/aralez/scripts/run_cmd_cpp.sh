#!/bin/bash
# run_cmd.sh <script.py> <logname> [env...]: UE commandlet python run on the Aralez scratch project (one process, killed on timeout)
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez
S=$1; L=$P/logs/$2.log; shift 2
env "$@" timeout ${TMO:-2400} ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd $P/cpp_test/AralezCpp.uproject -run=pythonscript -script=$S -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput > $L 2>&1
echo "exit $?"; grep -a -E "ARZ |Error:|Traceback|Exception" $L | grep -v "LogInit" | cut -c1-400 | tail -${N:-40}
