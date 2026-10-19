"""Rename Maya HumanIK / Mixamo-style joints to UE4 mannequin names (so IK-Rig auto-characterisation and the game's
socket names work), strip Sketchfab '_<n>' suffixes, '_rootJoint' -> 'root', merge all skinned meshes into one.
usage: python3 -I prep_rename_hik.py in.glb out.glb [drop1,drop2] [MeshName]"""
import json, struct, sys, re
src, dst = sys.argv[1], sys.argv[2]
drop = [d for d in (sys.argv[3] if len(sys.argv) > 3 else '').split(',') if d]
mname = sys.argv[4] if len(sys.argv) > 4 else 'SK_Char'
M = {'Hips': 'pelvis', 'Spine': 'spine_01', 'Spine1': 'spine_02', 'Spine2': 'spine_03', 'Neck': 'neck_01', 'Head': 'head'}
for s, u in (('Left', 'l'), ('Right', 'r')):
    M.update({s+'UpLeg': 'thigh_'+u, s+'Leg': 'calf_'+u, s+'Foot': 'foot_'+u, s+'ToeBase': 'ball_'+u, s+'Shoulder': 'clavicle_'+u,
              s+'Arm': 'upperarm_'+u, s+'ForeArm': 'lowerarm_'+u, s+'Hand': 'hand_'+u})
FING = {'Index': 'index', 'MiddleF': 'middle', 'Middle': 'middle', 'Ring': 'ring', 'Pinky': 'pinky', 'Thumb': 'thumb'}
b = open(src, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20+n]); rest = b[20+n:]
N = j['nodes']; skin = j['skins'][0]; joints = skin['joints']; par = {c: i for i, nd in enumerate(N) for c in nd.get('children', [])}
base = {k: re.sub(r'_\d+$', '', N[k].get('name', '')) for k in joints}
for k in joints:
    nm = re.sub(r'^(QuickRigCharacter_|mixamorig:|mixamorig_)', '', base[k])
    if base[k] == '_rootJoint': N[k]['name'] = 'root'; continue
    if nm in M: N[k]['name'] = M[nm]; continue
    m = re.match(r'^[LR]_([A-Za-z]+?)(\d?)$', nm)
    if m and m.group(1) in FING:      # side from the hand it hangs under (this rig's L_/R_ prefixes are mirrored)
        p = par.get(k); side = None
        while p is not None and side is None:
            pn = re.sub(r'^(QuickRigCharacter_)', '', re.sub(r'_\d+$', '', N[p].get('name', '')))
            side = 'l' if pn in ('LeftHand', 'hand_l') else 'r' if pn in ('RightHand', 'hand_r') else None; p = par.get(p)
        idx = int(m.group(2) or 0); f = FING[m.group(1)]
        N[k]['name'] = ('%s_metacarpal_%s' % (f, side)) if idx == 0 else '%s_%02d_%s' % (f, idx, side); continue
    N[k]['name'] = nm
for i, nd in enumerate(N):
    if i not in joints and nd.get('name') == 'root': nd['name'] = 'Armature'
prims = []; first = None
for i, nd in enumerate(N):
    if 'mesh' not in nd: continue
    m = j['meshes'][nd['mesh']]
    if any(d in m.get('name', '') for d in drop) or 'skin' not in nd: print('drop', m.get('name'))
    else:
        prims += m['primitives']
        if first is None: first = i
    if i != first: del nd['mesh']; nd.pop('skin', None)
j['meshes'] = [{'name': mname, 'primitives': prims}]; N[first]['mesh'] = 0; N[first]['name'] = mname
j.pop('animations', None)
names = [N[k]['name'] for k in joints]; dup = {x for x in names if names.count(x) > 1}
for k in joints:
    if N[k]['name'] in dup: N[k]['name'] += '_%d' % k
print('core bones:', [x for x in names if x in M.values()])
js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
open(dst, 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + len(rest)) + struct.pack('<I', len(js)) + b'JSON' + js + rest)
print('wrote', dst, 'prims', len(prims), 'bones', len(names))
