#!/bin/bash
# headless import + material + level build in the scratch project
D=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent
timeout 1200 ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd $D/SerpentProto/SerpentProto.uproject -ExecutePythonScript=$D/scripts/ue_build.py -unattended -nop4 -nosplash -nosound -nullrhi -stdout > $D/notes/ue_build.log 2>&1
echo "exit $?"; grep -a "SERPB\|Traceback\|Error:" $D/notes/ue_build.log | grep -v LogInit | cut -c1-220 | tail -${TAILN:-6}
