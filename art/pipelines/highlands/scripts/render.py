# GUI-editor screenshot sequencer: for each CameraActor CAM_<col>_<view> matching HL_CAMS, take a high-res shot, then quit.
import unreal, os, re
OUT = os.environ.get('HL_OUT', '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/shots/raw/')
CAMS = [c for c in os.environ.get('HL_CAMS', '').split(',') if c]
TAG = os.environ.get('HL_TAG', 'a')
RES = [int(x) for x in os.environ.get('HL_RES', '1600x900').split('x')]
os.makedirs(OUT, exist_ok=True)
def log(m): unreal.log_warning('HLR ' + str(m))

st = {'t': 0.0, 'i': -1, 'task': None, 'cams': None, 'phase': 'boot', 'wait': 0.0}

def cams():
    acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    d = {a.get_actor_label()[4:]: a for a in acts if isinstance(a, unreal.CameraActor) and a.get_actor_label().startswith('CAM_')}
    names = CAMS or sorted(d)
    return [(n, d[n]) for n in names if n in d]

def tick(dt):
    st['t'] += dt
    if st.get('busy'): return
    st['busy'] = True
    try:
        _tick()
    finally:
        st['busy'] = False

def _tick():
    try:
        if st['phase'] == 'boot':
            if st['t'] < 8.0: return
            for c in os.environ.get('HL_CVARS', 'r.TextureStreaming 0').split(';'):
                if c.strip(): unreal.SystemLibrary.execute_console_command(None, c.strip())
            try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
            except Exception as e: log('game view: %s' % e)
            st['cams'] = cams(); log('cams %s' % [n for n, _ in st['cams']])
            st['phase'] = 'next'; return
        if st['phase'] == 'shot':
            if st['task'] is not None and not st['task'].is_task_done(): return
            st['phase'] = 'next'; st['wait'] = st['t'] + 1.0; return
        if st['phase'] == 'next':
            if st['t'] < st['wait']: return
            st['i'] += 1
            if st['i'] >= len(st['cams']):
                log('ALLDONE'); unreal.unregister_slate_post_tick_callback(st['h']); unreal.SystemLibrary.quit_editor(); return
            n, c = st['cams'][st['i']]
            f = OUT + '%s_%s.png' % (n, TAG)
            st['task'] = unreal.AutomationLibrary.take_high_res_screenshot(RES[0], RES[1], f, camera=c, delay=float(os.environ.get('HL_DELAY', '3.0')), force_game_view=True)
            log('shot %s -> %s' % (n, f)); st['phase'] = 'shot'
    except Exception as e:
        import traceback; unreal.log_error('HLR ' + traceback.format_exc()); unreal.SystemLibrary.quit_editor()

st['h'] = unreal.register_slate_post_tick_callback(tick)
