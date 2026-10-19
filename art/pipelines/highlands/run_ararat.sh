#!/bin/bash
# Builds the Ararat-plain (Aralez) highlands level into the Twilight asset project.
set -x
P=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands
cd $P
export HL_SITE=ararat HL_CLON=44.35 HL_CLAT=40.05 HL_LAKE=0 HL_TILES=$P/gen/dem/tiles
python3 -P scripts/dem_build.py gen_ararat heights meshes maps || exit 1
mkdir -p gen_ararat/mesh; [ -f gen_ararat/mesh/water_layout.json ] || echo "{\"tiles\": []}" > gen_ararat/mesh/water_layout.json
python3 -P scripts/cams.py gen_ararat
N_PINE=0 N_JUN=3000 GRASS_DENSITY=0 python3 -P scripts/scatter.py gen_ararat
/var/www/html/Twilight/Game/Tools/cool_wait.sh
UE=~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd; U=/var/www/html/Twilight/Game/TwilightAssets.uproject; A="-unattended -nop4 -nosplash -nosound -nullrhi"
HL_ONLY=terrain $UE $U -ExecutePythonScript=$P/scripts/s1_import.py $A 2>&1 | grep -E "HL |Error" | tail -20
/var/www/html/Twilight/Game/Tools/cool_wait.sh
HL_ONLY=mat,level HL_VEG=1 $UE $U -ExecutePythonScript=$P/scripts/s2_level.py $A 2>&1 | grep -E "HL |Error" | tail -30
echo ARARAT_DONE
