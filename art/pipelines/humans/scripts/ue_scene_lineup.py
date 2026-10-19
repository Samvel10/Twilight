import sys,os; sys.path.append(os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U; importlib.reload(U)
import unreal
V=unreal.Vector
KIND=os.environ.get('HUM_MATS','raw')
def mats(n):
    if KIND=='raw': return None
    import json
    return None
names=['hayk','ara','bel','babsold','armsold','shamiram']
U.new_map('L_Lineup')
cam=V(1000,0,130); U.env(cam, U.look(cam,V(0,0,100)), 48)
U.spawn(U.MANNY, U.MA+'Unarmed/MM_Idle', 0.5, V(0,-400,0), 0)
for i,n in enumerate(names):
    U.spawn(U.skm(n), U.anim(n,'MM_Idle'), 0.5, V(0,-260+i*150,0), 0)
U.save_map()
U.new_map('L_Heads')
cam=V(420,0,175); U.env(cam, U.look(cam,V(0,0,160)), 40)
for i,n in enumerate(names):
    U.spawn(U.skm(n), U.anim(n,'MM_Idle'), 0.5, V(0,-260+i*130,-(30 if n in ('hayk','ara') else 0)), 15)
U.save_map()
U.log('DONE')
