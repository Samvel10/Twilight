#!/bin/bash
# shot.sh <map> <out> [secs] -- -game offscreen render of /Game/Proto/<map>, HighResShot -> shots/<out>.png
A=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez
export ARZ_OUT=$A/shots/$2.png ARZ_T=${3:-12}; rm -f $ARZ_OUT
timeout 400 ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor $A/AralezProto/AralezProto.uproject /Game/Proto/$1 -game -RenderOffscreen -windowed -ResX=1600 -ResY=900 -nosound -nosplash -unattended -NoVerifyGC -NoLiveCoding -ExecCmds="r.ScreenPercentage 100" > $A/logs/game_$2.log 2>&1
ls -la $ARZ_OUT 2>/dev/null || { echo "NO SHOT"; grep -E "Error|Python|HighRes" $A/logs/game_$2.log | head; }
