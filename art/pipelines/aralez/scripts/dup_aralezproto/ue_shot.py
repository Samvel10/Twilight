"""runs inside -game: wait ARZ_T seconds, HighResShot to ARZ_OUT, quit."""
import unreal, os, time
T = float(os.environ.get('ARZ_T', '12')); OUT = os.environ['ARZ_OUT']; RES = os.environ.get('ARZ_RES', '1600x900')
st = {'t0': time.time(), 'shot': False}
def tick(dt):
    el = time.time() - st['t0']
    if not st['shot'] and el > T:
        st['shot'] = True
        unreal.SystemLibrary.execute_console_command(None, 'HighResShot %s filename=%s' % (RES, OUT))
    elif st['shot'] and el > T + 4:
        unreal.SystemLibrary.execute_console_command(None, 'quit')
unreal.register_slate_post_tick_callback(tick)
