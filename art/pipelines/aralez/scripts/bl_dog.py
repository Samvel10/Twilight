"""Build SK_Aralez: quander's CC-BY Shiba Inu rig rescaled to an Armenian-gampr-sized Aralez, source clips removed,
authored clips: Aralez_Idle, Aralez_Glide, Aralez_Flap, Aralez_Land, Aralez_Lick. Export GLB (+ optional preview with wings).
blender -b -P bl_dog.py -- out.glb [wings.glb preview_prefix]"""
import sys, math
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/bl_common.py').read())
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/poses.py').read())
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; WINGS = argv[1] if len(argv) > 1 else None; PREV = argv[2] if len(argv) > 2 else None
arm, mesh = load_dog()
sc = bpy.context.scene; sc.render.fps = 30
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
FPS = 30
def bake(name, dur, fn):
    act = bpy.data.actions.new(name); arm.animation_data.action = act
    n = int(round(dur * FPS))
    for f in range(n + 1):
        apply_pose(arm, fn(f / FPS, f / n)); key_pose(arm, f)
    act.use_fake_user = True
    return act
def wave(t, hz, ph=0.0): return math.sin(2 * math.pi * (hz * t + ph))
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
TAILW = lambda t, amp, hz: {('tail_%d_jnt' % i): (0, 0, amp * wave(t, hz, -0.08 * i)) for i in range(2, 7)}
# Idle 4 s: breathing, slow head turn, tail sway, ear flick
def idle(t, a):
    p = add(STAND, {'chest_jnt': (1.2 * wave(t, 0.5), 0, 0), 'spine_2_jnt': (-0.8 * wave(t, 0.5), 0, 0),
                    'neck_base_jnt': (2 * wave(t, 0.25, .1), 0, 0), 'head_jnt': (0, 0, 6 * wave(t, 0.25)),
                    'L_ear_base_jnt': (4 * max(0, wave(t, 0.5, .3)) ** 8, 0, 0)})
    return add(p, TAILW(t, 5, 0.5))
# Glide 3 s: flight pose + slow undulation
def glide(t, a):
    p = add(GLIDE, {'spine_1_jnt': (1.5 * wave(t, 1 / 3), 0, 0), 'chest_jnt': (-1.5 * wave(t, 1 / 3), 0, 0), 'head_jnt': (2 * wave(t, 1 / 3, .2), 0, 2 * wave(t, 1 / 6)),
                    'L_ear_base_jnt': (3 * wave(t, 2), 0, 0), 'R_ear_base_jnt': (3 * wave(t, 2, .4), 0, 0)})
    return add(p, TAILW(t, 6, 2 / 3))
# Flap 1 s: phase locked to Wing_Flap (wing top at phase .25, bottom at .75)
def flap(t, a):
    k = 0.5 + 0.5 * math.cos(2 * math.pi * (a - 0.25 - 0.08))   # 1 near the top of the stroke
    return add(mix(FLAP_DOWN, FLAP_UP, k), TAILW(t, 5, 1))
# Land 1.6 s one-shot: glide -> reach -> touch -> crouch -> stand
def land(t, a):
    if t < 0.45: return mix(GLIDE, LAND_REACH, smooth(t / 0.45))
    if t < 0.75: return LAND_REACH
    if t < 0.95: return mix(LAND_REACH, LAND_CROUCH, smooth((t - 0.75) / 0.2))
    return mix(LAND_CROUCH, STAND, smooth((t - 0.95) / 0.65))
# Lick 1.6 s loop: two licks per cycle
def lick(t, a):
    k = 0.5 + 0.5 * math.cos(2 * math.pi * 2 * a)
    return add(mix(LICK_B, LICK_A, k), TAILW(t, 9, 1.25))
bake('Aralez_Idle', 4.0, idle)
bake('Aralez_Glide', 3.0, glide)
bake('Aralez_Flap', 1.0, flap)
bake('Aralez_Land', 1.6, land)
bake('Aralez_Lick', 1.6, lick)
arm.animation_data.action = None; apply_pose(arm, {})
# wing socket: on the back between the shoulder blades
import numpy as np
co = np.array([v.co[:] for v in mesh.data.vertices])
m = (np.abs(co[:, 0]) < 0.04) & (co[:, 1] > -0.33) & (co[:, 1] < -0.20)
top = co[m][co[m][:, 2].argmax()]
sock = Vector((0.0, float(top[1]), float(top[2]) - 0.035))
ch = arm.data.bones['chest_jnt']
local = ch.matrix_local.inverted() @ sock
print('SOCKET armature-space', tuple(round(x, 4) for x in sock), 'chest_jnt-local', tuple(round(x, 4) for x in local))
open(OUT + '.socket.txt', 'w').write('armature %s\nchest_local %s\n' % (tuple(sock), tuple(local)))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='ACTIONS',
                          export_skins=True, export_yup=True, export_apply=False, export_force_sampling=True)
print('EXPORTED', OUT)
if WINGS and PREV:
    bpy.ops.import_scene.gltf(filepath=WINGS)
    warm = [o for o in sc.objects if o.type == 'ARMATURE' and o.name.startswith('AralezWings')][0]
    warm.parent = arm; warm.parent_type = 'BONE'; warm.parent_bone = 'chest_jnt'
    # place at the socket in rest: parent matrix = bone tail-based; set world then let Blender compute
    bpy.context.view_layer.update()
    warm.matrix_world = Matrix.Translation(sock)
    bpy.context.view_layer.update()
    warm.animation_data_create()
    cam = setup_render((900, 560))
    def show(dog_act, wing_act, t, name, az, el, dist, tgt=(0, 0, 0.7)):
        arm.animation_data.action = bpy.data.actions[dog_act]; warm.animation_data.action = [x for x in bpy.data.actions if x.name.startswith(wing_act)][0]
        sc.frame_set(int(t * FPS)); bpy.context.view_layer.update()
        shoot(cam, tgt, az, el, dist, '%s_%s.png' % (PREV, name))
    show('Aralez_Glide', 'Wing_Glide', 0.3, 'glide_34', -60, 25, 6.5)
    show('Aralez_Flap', 'Wing_Flap', 0.25, 'flapTop_side', 180, 10, 6.5)
    show('Aralez_Flap', 'Wing_Flap', 0.75, 'flapBot_front', -90, 5, 6.5)
    show('Aralez_Land', 'Wing_Mantle', 0.6, 'land_34', -40, 10, 6.5)
    show('Aralez_Lick', 'Wing_Fold', 0.3, 'lick_34', -40, 20, 6.0, (0, -0.2, 0.5))
    show('Aralez_Idle', 'Wing_Fold', 1.0, 'idle_back', 120, 25, 6.0, (0, -0.2, 0.6))
