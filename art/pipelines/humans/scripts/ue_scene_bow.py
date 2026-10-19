import sys,os; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U, ue_props as PR; importlib.reload(U); importlib.reload(PR)
import unreal
V=unreal.Vector
U.new_map('L_Bow')
cam=V(330,-60,170); U.env(cam, U.look(cam,V(0,40,140)), 55)
clip='MF_Rifle_Idle_ADS'; an=unreal.load_asset(U.anim('hayk',clip))
for i,sg in enumerate((1,-1)):
    h=U.spawn(U.skm('hayk'), U.anim('hayk',clip), 0.0, V(0,-120+i*240,0), 0)
    # comp space: forward +Y, up +Z; bow long axis up (tilted 10 deg forward), depth axis along forward
    PR.attach(h, PR.BOW, an, 0.0, 'hand_l', 165.0, V(0,0.17,0.985), V(0,1,0), depth_sign=sg, grip_frac=0.5)
U.save_map(); U.log('bow map')
