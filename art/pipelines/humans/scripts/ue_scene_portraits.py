import sys,os; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U; importlib.reload(U)
import unreal
V=unreal.Vector
names=[n for n in os.environ.get('HUM_CHARS','hayk,ara,bel,babsold,armsold').split(',') if n]
HEAD={'hayk':192,'ara':194,'bel':160,'babsold':160,'armsold':160,'shamiram':155,'ara2':160,'ara3':192}
for n in names:
    U.new_map('L_Por_'+n)
    h=HEAD.get(n,160); cam=V(150,95,h+5)
    U.env(cam, U.look(cam,V(0,0,h-12)), 38)
    U.spawn(U.skm(n), U.anim(n,'MM_Idle'), 0.5, V(0,0,0), 25)
    U.save_map()
U.log('DONE')
