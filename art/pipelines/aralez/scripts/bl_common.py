# shared helpers (exec'd inside Blender)
import bpy, math, mathutils, os
from mathutils import Quaternion, Vector, Matrix, Euler
SRC_GLB = '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/dl/9abfce885a834399b2c3ccaed51cd474/9abfce885a834399b2c3ccaed51cd474.glb'
SCALE = 0.01 * 1.35          # source is in cm-as-metres; Aralez = 1.35x the shiba (~80 cm at the withers)

def load_dog():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=SRC_GLB)
    sc = bpy.context.scene
    arm = [o for o in sc.objects if o.type == 'ARMATURE'][0]
    mesh = [o for o in sc.objects if o.type == 'MESH' and o.name != 'Icosphere'][0]
    # unparent armature from the Sketchfab wrapper empties (all identity), delete junk
    mw = arm.matrix_world.copy(); arm.parent = None; arm.matrix_world = mw
    for o in list(sc.objects):
        if o not in (arm, mesh): bpy.data.objects.remove(o, do_unlink=True)
    arm.name = 'Aralez'; arm.data.name = 'AralezSkel'; mesh.name = 'SK_Aralez'; mesh.data.name = 'SK_Aralez'
    # clean bone names: 'head_jnt.40_038' -> 'head_jnt'
    import re
    for b in arm.data.bones:
        n = re.sub(r'\.\d+_\d+$', '', b.name)
        n = re.sub(r'\.(\d+)_end_\d+$', r'_end', n)
        if n == '_rootJoint': n = 'root_jnt'
        if n == 'root': n = 'root'
        b.name = n
    for a in bpy.data.actions:
        a.name = re.sub(r'^0\|', '', a.name).replace('_0_Object_13', '')
    # scale rig + mesh, rescale location keys
    arm.animation_data_clear()
    bpy.ops.object.select_all(action='DESELECT')
    arm.scale = (SCALE,) * 3
    arm.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for a in bpy.data.actions:
        for f in a.fcurves:
            if f.data_path.endswith('location'):
                for k in f.keyframe_points:
                    k.co[1] *= SCALE; k.handle_left[1] *= SCALE; k.handle_right[1] *= SCALE
    arm.animation_data_create()
    return arm, mesh

def rest3(pb):
    return pb.bone.matrix_local.to_3x3()

def set_delta(arm, bone, q_arm):
    """rotate bone by an armature-space rotation (defined in rest configuration) -> local quaternion"""
    pb = arm.pose.bones[bone]
    R = rest3(pb)
    ql = (R.inverted() @ q_arm.to_matrix() @ R).to_quaternion()
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = ql

def E(x=0, y=0, z=0):
    """armature-space rotation from degrees about X (lateral, +X = dog's left), Y (backward), Z (up)"""
    return Euler((math.radians(x), math.radians(y), math.radians(z)), 'XYZ').to_quaternion()

def apply_pose(arm, pose, base=None):
    """pose: {bone: (x,y,z) degrees}. base: dict bone->local quaternion (e.g. from standing frame) composed first"""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = base.get(pb.name, Quaternion()) if base else Quaternion()
        pb.location = Vector(); pb.scale = Vector((1, 1, 1))
    for b, v in pose.items():
        if b.startswith('@loc:'):
            arm.pose.bones[b[5:]].location = rest3(arm.pose.bones[b[5:]]).inverted() @ Vector(v); continue
        pb = arm.pose.bones[b]
        R = rest3(pb)
        ql = (R.inverted() @ E(*v).to_matrix() @ R).to_quaternion()
        pb.rotation_quaternion = (base.get(b, Quaternion()) if base else Quaternion()) @ ql

def key_pose(arm, frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        pb.keyframe_insert('location', frame=frame)

def setup_render(res=(800, 500), engine='BLENDER_EEVEE_NEXT'):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.6, 0.7, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.35
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 2.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 50; cam.data.clip_start = 0.05; cam.data.clip_end = 200
    sc.render.engine = engine; sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'Standard'
    return cam

def shoot(cam, target, az, el, dist, path):
    t = Vector(target)
    cam.location = t + Vector((math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el)))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def base_from_action(arm, action_name, frame):
    arm.animation_data.action = bpy.data.actions[action_name]
    bpy.context.scene.frame_set(frame)
    base = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}
    locs = {pb.name: pb.location.copy() for pb in arm.pose.bones}
    arm.animation_data.action = None
    return base, locs
