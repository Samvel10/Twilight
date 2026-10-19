#!/bin/bash
# Reproducible Aralez pipeline.  usage: build_aralez.sh [uproject] [content dest]
#  1) Blender 4.2 (headless): SK_Aralez.glb  = CC-BY Shiba-Inu rig (quander) rescaled 1.35x, source clips dropped, 5 authored clips
#                             SK_AralezWings.glb = procedural feather-card wings + 7-bone rig + 4 baked Wing_* clips
#  2) procedural feather atlas + fur strand mask (numpy/PIL, original work)
#  3) UE Interchange import (Nanite off) + materials + tuned material instances
set -e
H=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$H")
UPROJ=${1:-/var/www/html/Twilight/Game/TwilightAssets.uproject}
DEST=${2:-/Game/Twilight/Aralez}
BLENDER=${BLENDER:-blender}            # Blender 4.2 LTS (download.blender.org, no login)
SRC=${SRC:-$D/src/shiba_inu_quander_original_9abfce88.glb}
OUT=${OUT:-$D/assets}; mkdir -p "$OUT"
python3 -I "$H/make_feathers.py" "$OUT"
python3 -I - "$OUT/T_FurStrands.png" <<'PY'
import numpy as np, sys
from PIL import Image
rng = np.random.default_rng(3); N = 512; img = np.zeros((N, N), np.float32)
for (px, py), v in zip(rng.random((9000, 2)) * N, rng.uniform(0.35, 1.0, 9000)):
    r = rng.uniform(1.2, 2.4)
    for y in range(int(py - 4), int(py + 5)):
        for x in range(int(px - 4), int(px + 5)):
            d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if d < r: img[y % N, x % N] = max(img[y % N, x % N], v * (1 - d / r) ** 0.5)
Image.fromarray((img * 255).astype(np.uint8)).save(sys.argv[1])
PY
# the Blender scripts read SRC_GLB / script paths from bl_common.py: point them at this folder
sed -i "s#^SRC_GLB = .*#SRC_GLB = '$SRC'#" "$H/bl_common.py"
sed -i "s#exec(open('[^']*/scripts/\(bl_common\|poses\|wingflap\).py')#exec(open('$H/\1.py')#g" "$H/bl_dog.py" "$H/bl_wings.py"
"$BLENDER" -b -P "$H/bl_wings.py" -- "$OUT/SK_AralezWings.glb" "$OUT" | grep -E "WINGS|EXPORTED"
"$BLENDER" -b -P "$H/bl_dog.py" -- "$OUT/SK_Aralez.glb" | grep -E "SOCKET|EXPORTED"
mkdir -p "$OUT/../src/glb" "$OUT/../src/tex"
cp "$OUT"/SK_*.glb "$OUT/../src/glb/"; cp "$OUT"/T_*.png "$OUT/../src/tex/"
UE=~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd
ARZ_ROOT="$D" ARZ_DEST="$DEST" ARZ_STEPS=dog,wings,tex,mats,mis "$UE" "$UPROJ" -run=pythonscript -script="$H/ue_import.py" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput | grep -E "ARZ |Error"
