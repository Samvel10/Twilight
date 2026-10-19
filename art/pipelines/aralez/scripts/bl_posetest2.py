import sys
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/bl_common.py').read())
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/poses.py').read())
a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]; names = a[1].split(',')
arm, mesh = load_dog()
cam = setup_render()
for n in names:
    apply_pose(arm, globals()[n]); bpy.context.view_layer.update()
    shoot(cam, (0, -0.1, 0.6), 0, 5, 3.6, '%s_%s_side.png' % (out, n))
    shoot(cam, (0, -0.1, 0.6), -55, 25, 3.6, '%s_%s_34.png' % (out, n))
