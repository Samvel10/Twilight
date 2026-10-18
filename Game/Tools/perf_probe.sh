#!/usr/bin/env bash
# Quick perf probe: perf_probe.sh <label> <seconds> "<ExecCmds>" [extra args]
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
LABEL=$1; SECS=$2; CMDS=$3; shift 3
OUT=$G/../docs/capture/perf; mkdir -p "$OUT"
"$UE/Engine/Binaries/Linux/UnrealEditor" "$G/Twilight.uproject" ${MAP:-/Game/Twilight/Maps/L_Vahagn} -game -windowed -ResX=${RESX:-1600} -ResY=${RESY:-900} \
  -NoSplash -unattended -nosound -TwAutoPlay=$SECS -TwGodPilot ${CMDS:+-ExecCmds="$CMDS"} "$@" > "$OUT/$LABEL.log" 2>&1
echo "== $LABEL: $(grep -o 'avg_fps=[0-9.]* p95_fps=[0-9.]* p99_fps=[0-9.]*' "$OUT/$LABEL.log" | tail -1)  $(grep -o '\[TwTest\] t=[0-9]* fps=[0-9.]*' "$OUT/$LABEL.log" | tail -3 | tr '\n' ' ')"
