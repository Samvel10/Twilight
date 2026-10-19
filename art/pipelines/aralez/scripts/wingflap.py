# Procedural wing pose (identical maths in C++: AralezWingComponent.cpp). Returns per-bone armature-space Euler (deg)
# for the LEFT wing; the right wing uses (x, -y, -z).  Axes: X = span (out), Y = back, Z = up.
#  +Y rotation pushes the left tip DOWN (so elevation e -> rotY = -e); +Z sweeps the tip BACK; +X pitches the leading edge DOWN.
import math
def wing_pose(phase, flap=1.0, glide=0.0, mantle=0.0, fold=0.0, t=0.0):
    th = 2 * math.pi * phase
    s = math.sin(th); up = max(0.0, math.cos(th))          # up>0 while the wing rises
    dn = max(0.0, -math.cos(th))
    F = {  # flapping
        'humerus': (6 * math.cos(th), -(12 + 40 * s), 4 - 8 * dn + 6 * up),
        'forearm': (0, -(10 * math.sin(th - 0.5)), 16 * up),
        'hand':    (-10 * math.cos(th) * 0.8, -(16 * math.sin(th - 0.9) - 4), 34 * up + 4),
    }
    br = math.sin(t * 2 * math.pi * 0.35)
    G = {  # gliding: dihedral, tips curled up, slow breathing of the span
        'humerus': (2, -(9 + 2 * br), 6),
        'forearm': (0, -(2 + br), 2),
        'hand':    (-3, -(8 + 2 * br), 6),
    }
    M = {  # mantling / landing air-brake: raised, swept forward, leading edge up
        'humerus': (-24, -(52 + 6 * math.sin(th)), -22),
        'forearm': (-8, -(6), 14),
        'hand':    (-16, -(14 + 8 * math.sin(th - 0.6)), 20),
    }
    D = {  # raised arch (standing guard over the fallen hero): lifted, swept back, tips lowered like a canopy
        'humerus': (-4, -(32 + 2 * math.sin(t * 1.3)), 42),
        'forearm': (2, 14, 30),
        'hand':    (6, 30 + 3 * math.sin(t * 1.3 + 1), 30),
    }
    w = [flap, glide, mantle, fold]; tot = max(1e-4, sum(w))
    out = {}
    for b in ('humerus', 'forearm', 'hand'):
        out[b] = tuple(sum(wi * P[b][k] for wi, P in zip(w, (F, G, M, D))) / tot for k in range(3))
    return out
