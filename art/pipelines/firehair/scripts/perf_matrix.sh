#!/bin/bash
# perf_matrix.sh [repeats] -- interleaved profilegpu captures: fire vs current helmeted hero, menu (3 m) and chase (6 m) cameras
F=$(cd "$(dirname "$0")/../.." && pwd); S=$F/deliver/scripts
for r in $(seq 1 ${1:-3}); do for m in ${MAPS:-Menu Orig Chase ChaseOrig}; do
  others=$(pgrep -f 'UnrealEditor' | xargs -r ps -o args= -p 2>/dev/null | grep -vc FireHair.uproject)
  $S/perf.sh L_FH_$m ${m}_$r 30 >/dev/null
  echo "$m $r others=$others $(python3 -P $S/gpuprof.py $F/logs/perf_${m}_$r.log 0 | grep -E '== profile 1|Frame [0-9]+$| BasePass$|BatchedLights$|Translucency\(AfterDOF' | head -5 | tr -s ' ' | tr '\n' ';')"
done; done
