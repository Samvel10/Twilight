#!/bin/bash
# GPU A/B (serpent visible vs hidden, same camera) when no other agent is rendering with Unreal; 3 rounds.
D=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent
OUT=$D/notes/perf_results.txt; echo "# $(date) perf A/B" >> $OUT
busy(){ ps aux | grep "[U]nrealEditor" | grep -v "nullrhi\|-run=pythonscript\|ExecutePythonScript\|SerpentProto" | grep -q "game\|RenderOffscreen\|uproject"; }
for r in 1 2 3; do
  for i in $(seq 1 180); do busy || break; sleep 10; done
  busy && echo "round $r: GPU still shared (other agents rendering)" >> $OUT
  for h in vis hide; do
    A=""; [ $h = hide ] && A=-SerpHide
    SHOTAT=30 TAILN=12 $D/scripts/shotr.sh perf_${h}_$r -SerpCamDist=${CAMD:-3000} -SerpCamYaw=250 -SerpCamPitch=-6 -SerpCamAt=0.3 $A ${EXTRA} > /dev/null
    echo "round $r $h: $(grep -a 'SERP perf' $D/notes/logs/perf_${h}_$r.log | tail -6 | head -5 | sed 's/.*gpu=\([0-9.]*\)ms.*/\1/' | tr '\n' ' ') (gpu ms, 3s windows) | other UE: $(ps aux | grep '[U]nrealEditor' | grep -v SerpentProto | grep -c 'game\|RenderOffscreen')" >> $OUT
  done
done
echo done >> $OUT
