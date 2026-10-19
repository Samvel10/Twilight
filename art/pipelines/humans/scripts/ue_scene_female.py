import sys,os; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U; importlib.reload(U)
import unreal
V=unreal.Vector
n=os.environ.get('HUM_F','shamiram')
U.new_map('L_Female')
cam=V(560,0,115); U.env(cam, U.look(cam,V(0,0,92)), 42)
for i,(clip,t) in enumerate((('MM_Idle',0.5),('MF_Unarmed_Walk_Fwd',0.25),('MF_Unarmed_Walk_Fwd',0.75),('MM_Attack_01',0.45),('MM_Death_Front_01',0.3))):
    U.spawn(U.skm(n), U.anim(n,clip), -t, V(0,-260+i*130,0), 20)
U.save_map(); U.log('female map')
