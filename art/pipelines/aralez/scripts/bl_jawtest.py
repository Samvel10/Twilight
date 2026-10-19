import sys
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/bl_common.py').read())
out = sys.argv[sys.argv.index('--') + 1]
arm, mesh = load_dog(); cam = setup_render((600, 400))
h = arm.data.bones['head_jnt'].head_local
for ang in (0, -6, -10, -14):
    apply_pose(arm, {'jaw_jnt': (ang, 0, 0), 'L_mouth_corner_jnt': (0, 0, 0)}); bpy.context.view_layer.update()
    shoot(cam, (h.x, h.y - 0.15, h.z - 0.05), 180 + 90, 5, 1.1, '%s_jaw%d.png' % (out, ang))
