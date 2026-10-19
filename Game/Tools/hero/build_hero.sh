#!/bin/bash
# Reproducible Vahagn hero pipeline (run from anywhere). Target project defaults to the real Twilight asset twin.
# 1) clean + bake the CC-BY Spartan GLB, 2) procedural skin-detail normal, 3) UE: import + IK rigs + retarget the 7 Manny clips,
# 4) UE: hero materials (M_HeroSkin/M_HeroPBR + MI_Vahagn_*) assigned to the mesh.
set -e
H=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$H")
UPROJ=${UPROJ:-/var/www/html/Twilight/Game/TwilightAssets.uproject}
OUT=${OUT:-/var/www/html/Twilight/art/models/hero}; mkdir -p "$OUT"
SRC=${SRC:-$D/spartan_original_666f4851.glb}
python3 -I "$H/prep_spartan.py" "$SRC" "$OUT/spartan_tmp.glb" "Shield,Sword"
python3 -I "$H/bake_gltf_root.py" "$OUT/spartan_tmp.glb" "$OUT/spartan_vahagn.glb" && rm -f "$OUT/spartan_tmp.glb"
python3 -I "$H/make_skin_detail.py" "$OUT/T_SkinDetail_N.png"
UE=~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd
HERO_GLB="$OUT/spartan_vahagn.glb" HERO_DEST=/Game/Twilight/Hero \
  "$UE" "$UPROJ" -run=pythonscript -script="$H/ue_hero_build.py" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput | grep -E "HERO|Error"
HERO_DETAIL_PNG="$OUT/T_SkinDetail_N.png" \
  "$UE" "$UPROJ" -run=pythonscript -script="$H/hero_materials.py" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput | grep -E "HERO|TwilightMat\] (built|MI|assigned)|Error"
