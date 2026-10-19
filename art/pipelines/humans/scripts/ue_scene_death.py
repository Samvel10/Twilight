import sys,os; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U; importlib.reload(U)
import unreal
V=unreal.Vector
U.new_map('L_Death')
cam=V(900,0,350); U.env(cam, U.look(cam,V(0,0,0)), 50)
for i,f in enumerate((0.3,0.6,0.9,0.99)):
    a=U.spawn(U.MANNY, U.MA+'Death/MM_Death_Back_01', -f, V(-200,-450+i*300,0), 0)
    an=unreal.load_asset(U.MA+'Death/MM_Death_Back_01'); U.log('len %.3f frames? %s'%(an.get_play_length(), an.get_editor_property('rate_scale') if hasattr(an,'rate_scale') else ''))
    U.spawn(U.skm('armsoldc'), U.anim('armsoldc','MM_Death_Back_01'), -f, V(200,-450+i*300,0), 0)
U.save_map()
