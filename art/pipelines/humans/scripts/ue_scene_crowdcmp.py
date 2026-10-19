import sys,os; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U; importlib.reload(U)
import unreal
V=unreal.Vector
U.new_map('L_CrowdCmp')
cam=V(560,0,120); U.env(cam, U.look(cam,V(0,0,95)), 45)
for i,n in enumerate(('armsold','armsoldc','babsold','babsoldc')):
    U.spawn(U.skm(n), U.anim(n,'MM_Idle'), 0.5, V(0,-240+i*160,0), 15)
U.save_map(); U.log('cmp map')
