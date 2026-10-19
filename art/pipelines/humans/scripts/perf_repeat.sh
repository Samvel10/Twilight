#!/bin/bash
# interleaved repeats of the perf maps (stat unit); crops into shots/pf3_*_s.png
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans; cd $P/scripts
for r in 1 2 3; do for m in L_P0:env L_Army:full30 L_ArmyC:crowd30 L_ArmyC60:crowd60; do
  map=${m%%:*}; tag=${m##*:}; EXEC="r.ScreenPercentage 100, stat unit" ./shoot.sh $map pf3_${tag}_$r 40 >/dev/null
  ffmpeg -hide_banner -loglevel error -y -i $P/shots/pf3_${tag}_$r.png -vf "crop=300:170:1300:175" $P/shots/pf3_${tag}_${r}_s.png
  echo "$tag $r $(date +%T) others=$(ps aux | grep -E 'UnrealEditor' | grep -v grep | grep -v HumansTest | wc -l)"
done; done
cd $P/shots; ../scripts/grid.sh perf_matrix3.jpg 4 300 170 pf3_env_1_s.png pf3_full30_1_s.png pf3_crowd30_1_s.png pf3_crowd60_1_s.png pf3_env_2_s.png pf3_full30_2_s.png pf3_crowd30_2_s.png pf3_crowd60_2_s.png pf3_env_3_s.png pf3_full30_3_s.png pf3_crowd30_3_s.png pf3_crowd60_3_s.png
