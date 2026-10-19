#!/bin/bash
# build_all.sh -- full reproducible pipeline (scratch project FireHair/; never touches /var/www/html/Twilight):
#  1 Blender: extract head polygons + Body base colour from the CC-BY Spartan hero GLB
#  2 numpy:   procedural noise / fire LUT / body fire mask   -> deliver/assets
#  3 Blender: procedural flame-lock mesh (SM_VahagnFireHair.glb) -> deliver/assets
#  4 UE:      import + materials (ue_build.py), look-dev maps (ue_scenes.py)
#  5 UE -game: screenshots (final_shots.sh) and GPU profile (perf_matrix.sh)
set -e
F=$(cd "$(dirname "$0")/../.." && pwd); S=$F/deliver/scripts; A=$F/deliver/assets; B=$F/../../tools/blender-4.2.3-linux-x64/blender
HERO_GLB=${HERO_GLB:-/var/www/html/Twilight/art/models/hero/spartan_vahagn.glb}
mkdir -p $F/work $A
$B -b -P $S/bl_extract.py -- $HERO_GLB $F/work | grep -E "BASE|POLYS"
python3 -P $S/gen_textures.py $F/work $A
$B -b -P $S/gen_firehair.py -- $F/work $A/SM_VahagnFireHair.glb | grep -E "LOCKS|EXPORTED"
FH_STEPS=tex,mesh,mat $S/run_ue.sh $S/ue_build.py 1800 | grep -E "FH (tex|mesh|materials)|FAILED|Error"
[ "${SHOTS:-1}" = 1 ] && $S/final_shots.sh
[ "${PERF:-0}" = 1 ] && $S/perf_matrix.sh 3
echo done
