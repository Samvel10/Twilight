#!/bin/bash
# iterate.sh <outdir> <Map,Map..> [steps]  -- regenerate mesh (blender), rebuild UE assets, rebuild maps, shoot them into <outdir>
F=$(cd "$(dirname "$0")/../.." && pwd); S=$F/deliver/scripts; B=$F/../../tools/blender-4.2.3-linux-x64/blender
OUT=$1; MAPS=${2:-Menu}; STEPS=${3:-mesh,mat}; mkdir -p $OUT
if [[ $STEPS == *mesh* ]]; then $B -b -P $S/gen_firehair.py -- $F/work $F/deliver/assets/SM_VahagnFireHair.glb 2>&1 | grep -E "LOCKS|rror"; fi
FH_STEPS=$STEPS $S/run_ue.sh $S/ue_build.py 1800 | grep -E "Error|FAILED|mesh " | head -5
FH_MAPS=$MAPS $S/run_ue.sh $S/ue_scenes.py 1800 | grep -E "Error|Traceback" | head -5
for m in ${MAPS//,/ }; do l=$(echo $m | tr A-Z a-z); OUTD=$OUT $S/shoot.sh L_FH_$m $l ${WAIT:-25} | tail -1; done
