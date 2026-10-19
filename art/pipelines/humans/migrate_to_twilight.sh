#!/bin/bash
# Copy the finished UE assets from the scratch project into the Twilight content tree (same /Game paths, same engine 5.8).
# DRY RUN by default; pass --apply to copy. Close every editor on the Twilight project first.
# Excluded on purpose: */Rig (IK rigs/retargeters need the IKRig plugin, which Twilight does not enable; the retargeted
# AnimSequences are standalone and do not need them), the look-dev maps, the Huntress test and the Alethea static import.
set -e
S=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/HumansTest/Content
D=${TWILIGHT_CONTENT:-/var/www/html/Twilight/Game/Content}
APPLY=0; [ "$1" = "--apply" ] && APPLY=1
copy(){ echo "  $1"; [ $APPLY = 1 ] && mkdir -p "$D/$(dirname "$1")" && rsync -a "$S/$1" "$D/$(dirname "$1")/"; true; }
echo "source $S -> $D (apply=$APPLY)"
for C in Hayk Ara Bel Babsold Armsold Babsoldc Armsoldc Shamiram; do
  for sub in Mesh Anims Materials; do [ -d "$S/Twilight/Humans/$C/$sub" ] && copy "Twilight/Humans/$C/$sub"; done
done
copy Twilight/Humans/Props/Bow; copy Twilight/Humans/Props/Spear2
copy Twilight/Materials/M_Human.uasset
[ -f "$D/Twilight/Hero/Textures/T_SkinDetail_N.uasset" ] || copy Twilight/Hero/Textures/T_SkinDetail_N.uasset
[ -f "$D/StarterContent/Textures/T_Perlin_Noise_M.uasset" ] || echo "  WARNING: M_Human uses /Game/StarterContent/Textures/T_Perlin_Noise_M (missing in target)"
echo "done. Open the editor once (shaders compile), then use the paths in README.md."
