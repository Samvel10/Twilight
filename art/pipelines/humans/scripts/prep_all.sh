#!/bin/bash
# prep + bake every character in chars.json -> src/<name>.glb (Interchange-ready, UE4 mannequin bone names, root identity),
# then rigidly attach the listed props (glb_attach_prop.py). env ONLY=comma list
set -e
P=$(cd "$(dirname "$0")/.." && pwd); mkdir -p $P/src
for name in $(python3 -I -c "import json;print(' '.join(json.load(open('$P/scripts/chars.json'))))"); do
  [ -n "$ONLY" ] && [[ ",$ONLY," != *",$name,"* ]] && continue
  read src drop < <(python3 -I -c "import json;c=json.load(open('$P/scripts/chars.json'))['$name'];print(c['src'],c['drop'])")
  python3 -I $P/scripts/prep_char.py $P/dl/glb/$src.glb $P/src/${name}_tmp.glb "$drop" SK_$name | tail -1
  python3 -I $P/scripts/bake_gltf_root.py $P/src/${name}_tmp.glb $P/src/$name.glb | tail -1 && rm -f $P/src/${name}_tmp.glb
  python3 -I -c "import json;[print(p[0],p[1],p[2]) for p in json.load(open('$P/scripts/chars.json'))['$name'].get('props',[])]" | while read puid pname pargs; do
    python3 -I $P/scripts/glb_attach_prop.py $P/src/$name.glb $P/dl/props/$puid.glb $P/src/${name}_p.glb --name $pname $pargs | tail -1 && mv $P/src/${name}_p.glb $P/src/$name.glb
  done
done
