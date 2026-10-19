import sys
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/bl_common.py').read())
out = sys.argv[sys.argv.index('--') + 1]
arm, mesh = load_dog()
cam = setup_render()
print('ACTS', [a.name for a in bpy.data.actions])
for b in ('root','COG_jnt','head_jnt','L_hand_jnt','tail_7_jnt','chest_jnt'):
    print('B', b, arm.data.bones[b].head_local)
apply_pose(arm, {})
shoot(cam, (0, -0.25, 0.55), 0, 5, 3.0, out + '_rest_side.png')
base, locs = base_from_action(arm, 'standing', 1)
apply_pose(arm, {}, base)
for pb in arm.pose.bones: pb.location = locs[pb.name]
bpy.context.view_layer.update()
shoot(cam, (0, -0.25, 0.55), 0, 5, 3.0, out + '_stand_side.png')
shoot(cam, (0, -0.25, 0.55), -50, 15, 3.0, out + '_stand_34.png')
