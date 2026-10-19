#!/bin/bash
# full offline mesh pipeline: scan GLB -> merged -> welded -> straightened -> decimated -> unwrapped+baked -> rigged GLB
set -e
D=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent; cd $D
SCAN=${SCAN:-dl/glb/18858ce6cc7c4a74b7f208a1c3a7b195.glb}; FACES=${FACES:-40000}; TAG=${TAG:-40k}
[ -f src/okinawa_merged.glb ] || python3 -I scripts/merge.py $D/scripts $SCAN src/okinawa_merged.glb
[ -f src/ok_weld.glb ] || node/node_modules/.bin/gltf-transform weld src/okinawa_merged.glb src/ok_weld.glb
[ -n "$SKIP_STRAIGHT" ] || STRETCH=${STRETCH:-1.25} LTARGET=${LTARGET:-10.0} venv/bin/python -I scripts/straighten.py src/ok_weld.glb src/straight_hi.npz
[ -n "$SKIP_STRAIGHT" ] || venv/bin/python -I scripts/decimate.py src/straight_hi.npz src/low$TAG.npz $FACES
RES=${RES:-2048} venv/bin/python -I scripts/bake.py src/straight_hi.npz src/low$TAG.npz src/okinawa_merged.glb.albedo.jpg src/bake$TAG
NBONES=${NBONES:-48} venv/bin/python -I scripts/rig.py src/bake${TAG}_mesh.npz src/vishap_serpent_$TAG.glb
for n in 12000 4000; do
  venv/bin/python -I scripts/lod.py src/bake${TAG}_mesh.npz src/lod_$n.npz $n
  NBONES=${NBONES:-48} venv/bin/python -I scripts/rig.py src/lod_$n.npz src/vishap_serpent_lod$n.glb
done
cp src/vishap_serpent_$TAG.glb deliver/SK_VishapSerpent.glb
cp src/vishap_serpent_lod12000.glb deliver/SK_VishapSerpent_LOD1.glb
cp src/vishap_serpent_lod4000.glb deliver/SK_VishapSerpent_LOD2.glb
for k in D N M; do cp src/bake${TAG}_$k.png deliver/textures/T_VishapSerpent_$k.png; done
venv/bin/python -I scripts/scales.py deliver/textures/T_VishapScales 1024 40
HK=$(venv/bin/python -I -c "import numpy as np;print(float(np.load('src/straight_hi.npz')['headlen'])/0.426)") venv/bin/python -I scripts/horns.py deliver/SM_VishapHorns.glb
