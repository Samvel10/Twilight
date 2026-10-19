# Aralez key poses: {bone: (x, y, z) degrees, armature-space, applied on the REST pose}
# axes: X lateral (+X = dog's left side), Y = backward (head is at -Y), Z = up.  +X rot: nose down / leg swings back / tail up.
# '@loc:bone': (x,y,z) metres, armature space.
def sym(d):
    out = dict(d)
    for k, v in d.items():
        if k.startswith('L_'): out['R_' + k[2:]] = (v[0], -v[1], -v[2])
        if k.startswith('@loc:L_'): out['@loc:R_' + k[7:]] = (-v[0], v[1], v[2])
    return out
def mix(a, b, t):
    ks = set(a) | set(b); o = {}
    for k in ks:
        va = a.get(k, (0, 0, 0)); vb = b.get(k, (0, 0, 0)); o[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
    return o
def add(a, b):
    ks = set(a) | set(b); return {k: tuple(x + y for x, y in zip(a.get(k, (0, 0, 0)), b.get(k, (0, 0, 0)))) for k in ks}

STAND = sym({'neck_base_jnt': (4, 0, 0), 'head_jnt': (-2, 0, 0), 'tail_1_jnt': (8, 0, 0), 'L_ear_base_jnt': (6, 0, 0), 'jaw_jnt': (-6, 0, 0)})
GLIDE = sym({
    'spine_1_jnt': (-3, 0, 0), 'spine_2_jnt': (-3, 0, 0), 'chest_jnt': (-2, 0, 0),
    'neck_base_jnt': (26, 0, 0), 'neck_mid_jnt': (6, 0, 0), 'head_jnt': (-30, 0, 0),
    'L_clavicle_jnt': (-12, 0, 0), 'L_shoulder_jnt': (-55, 0, 0), 'L_elbow_jnt': (80, 0, 0), 'L_wrist_jnt': (-55, 0, 0), 'L_hand_jnt': (-20, 0, 0),
    'L_hip_jnt': (65, 0, 0), 'L_knee_jnt': (-25, 0, 0), 'L_ankle_jnt': (45, 0, 0), 'L_foot_jnt': (30, 0, 0),
    'tail_1_jnt': (22, 0, 0), 'tail_2_jnt': (-4, 0, 0), 'tail_3_jnt': (-3, 0, 0), 'tail_4_jnt': (-2, 0, 0),
    'L_ear_base_jnt': (35, 0, 0), 'jaw_jnt': (-6, 0, 0),
})
# flap body response: on the downstroke the chest lifts and the legs swing a bit
FLAP_DOWN = add(GLIDE, sym({'chest_jnt': (-6, 0, 0), 'neck_base_jnt': (-5, 0, 0), 'head_jnt': (5, 0, 0), 'L_shoulder_jnt': (-10, 0, 0), 'L_hip_jnt': (-12, 0, 0), 'tail_1_jnt': (-8, 0, 0), 'tail_3_jnt': (6, 0, 0)}))
FLAP_UP = add(GLIDE, sym({'chest_jnt': (5, 0, 0), 'neck_base_jnt': (4, 0, 0), 'head_jnt': (-4, 0, 0), 'L_shoulder_jnt': (8, 0, 0), 'L_hip_jnt': (10, 0, 0), 'tail_1_jnt': (8, 0, 0), 'tail_3_jnt': (-6, 0, 0)}))
# landing: forelegs reach forward/down, hind legs swing under the body
LAND_REACH = sym({
    'spine_1_jnt': (4, 0, 0), 'chest_jnt': (-6, 0, 0),
    'neck_base_jnt': (10, 0, 0), 'head_jnt': (-14, 0, 0),
    'L_shoulder_jnt': (-38, 0, 0), 'L_elbow_jnt': (12, 0, 0), 'L_wrist_jnt': (-10, 0, 0),
    'L_hip_jnt': (-25, 0, 0), 'L_knee_jnt': (-10, 0, 0), 'L_ankle_jnt': (15, 0, 0),
    'tail_1_jnt': (30, 0, 0), 'tail_2_jnt': (5, 0, 0), 'L_ear_base_jnt': (25, 0, 0), 'jaw_jnt': (-6, 0, 0)})
LAND_CROUCH = sym({
    'COG_jnt': (0, 0, 0), '@loc:root': (0, 0, -0.10),
    'spine_1_jnt': (2, 0, 0), 'chest_jnt': (4, 0, 0), 'neck_base_jnt': (16, 0, 0), 'head_jnt': (-10, 0, 0),
    'L_shoulder_jnt': (-18, 0, 0), 'L_elbow_jnt': (34, 0, 0), 'L_wrist_jnt': (-24, 0, 0),
    'L_hip_jnt': (-22, 0, 0), 'L_knee_jnt': (30, 0, 0), 'L_ankle_jnt': (-24, 0, 0),
    'tail_1_jnt': (14, 0, 0), 'L_ear_base_jnt': (15, 0, 0), 'jaw_jnt': (-6, 0, 0)})
TONGUE_OUT = {'jaw_jnt': (20, 0, 0), 'tongue_1_jnt': (-8, 0, 0), 'tongue_2_jnt': (10, 0, 0), 'tongue_3_jnt': (14, 0, 0), 'tongue_4_jnt': (16, 0, 0), 'tongue_5_jnt': (16, 0, 0),
              '@loc:tongue_1_jnt': (0, -0.045, -0.025)}
LICK_A = add(sym({  # head down at the warrior's face, tongue out
    'spine_1_jnt': (4, 0, 0), 'spine_2_jnt': (4, 0, 0), 'chest_jnt': (6, 0, 0),
    'neck_base_jnt': (58, 0, 0), 'neck_mid_jnt': (16, 0, 0), 'head_jnt': (8, 0, 0),
    'L_shoulder_jnt': (-14, 0, 0), 'L_elbow_jnt': (22, 0, 0), 'L_wrist_jnt': (-12, 0, 0),
    'L_hip_jnt': (-4, 0, 0), 'tail_1_jnt': (4, 0, 0), 'L_ear_base_jnt': (-8, 0, 0)}), TONGUE_OUT)
LICK_B = add(LICK_A, {'neck_base_jnt': (-6, 0, 0), 'head_jnt': (-14, 0, 0), 'tongue_3_jnt': (-10, 0, 0), 'tongue_4_jnt': (-14, 0, 0), 'tongue_5_jnt': (-16, 0, 0)})
GALLOP_1 = sym({'L_shoulder_jnt': (-40, 0, 0), 'L_elbow_jnt': (10, 0, 0), 'L_hip_jnt': (40, 0, 0), 'L_knee_jnt': (-10, 0, 0), 'L_ankle_jnt': (20, 0, 0),
                'spine_1_jnt': (-6, 0, 0), 'spine_2_jnt': (-4, 0, 0), 'neck_base_jnt': (20, 0, 0), 'head_jnt': (-18, 0, 0), 'tail_1_jnt': (30, 0, 0), 'L_ear_base_jnt': (30, 0, 0)})
GALLOP_2 = sym({'L_shoulder_jnt': (35, 0, 0), 'L_elbow_jnt': (70, 0, 0), 'L_wrist_jnt': (-40, 0, 0), 'L_hip_jnt': (-45, 0, 0), 'L_knee_jnt': (35, 0, 0), 'L_ankle_jnt': (-20, 0, 0),
                'spine_1_jnt': (8, 0, 0), 'spine_2_jnt': (6, 0, 0), 'neck_base_jnt': (28, 0, 0), 'head_jnt': (-22, 0, 0), 'tail_1_jnt': (24, 0, 0), 'L_ear_base_jnt': (30, 0, 0)})
