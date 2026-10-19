# gpuprof.py - GUI-editor GPU profiling sequencer (started from init_unreal.py when HL_PROF=1).
# For each "view|cvars;cvars|hide-prefixes" entry in HL_PROF_SET: pilot the viewport to CAM_<view>, apply cvars, hide actors,
# warm up, then run ProfileGPU (hierarchical GPU timings written to the log, parsed by gpuprof_parse.py).
import unreal, os
SETS = [s for s in os.environ.get('HL_PROF_SET', '').split('#') if s]
def log(m): unreal.log_warning('HLP ' + str(m))
st = {'t': 0.0, 'i': -1, 'phase': 'boot', 'wait': 0.0, 'hidden': []}
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def cmd(c):
    unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(), c)

def actors():
    return EAS.get_all_level_actors()

def tick(dt):
    st['t'] += dt
    if st.get('busy'): return
    st['busy'] = True
    try: _tick()
    except Exception:
        import traceback; unreal.log_error('HLP ' + traceback.format_exc()); unreal.SystemLibrary.quit_editor()
    finally: st['busy'] = False

def _tick():
    if st['phase'] == 'boot':
        if st['t'] < 10.0: return
        LES.editor_set_game_view(True)
        for c in ('r.ScreenPercentage 100', 't.MaxFPS 0', 'r.VSync 0'):
            cmd(c)
        st['phase'] = 'next'; return
    if st['t'] < st['wait']: return
    if st['phase'] == 'next':
        for a in st['hidden']:
            a.set_is_temporarily_hidden_in_editor(False)
        st['hidden'] = []
        st['i'] += 1
        if st['i'] >= len(SETS):
            log('ALLDONE'); unreal.unregister_slate_post_tick_callback(st['h']); unreal.SystemLibrary.quit_editor(); return
        view, cv, hide = (SETS[st['i']].split('|') + ['', ''])[:3]
        acts = actors()
        cam = [a for a in acts if a.get_actor_label() == 'CAM_' + view]
        if cam:
            LES.pilot_level_actor(cam[0])
        for c in [c for c in cv.split(';') if c]:
            cmd(c.split('=')[0])
        for h in [h for h in hide.split(',') if h]:
            for a in acts:
                if a.get_actor_label().startswith(h):
                    a.set_is_temporarily_hidden_in_editor(True); st['hidden'].append(a)
        log('SET %d %s' % (st['i'], SETS[st['i']]))
        st['phase'] = 'prof'; st['wait'] = st['t'] + float(os.environ.get('HL_PROF_WARM', '8')); return
    if st['phase'] == 'prof':
        cmd('ProfileGPU')
        log('PROFILED %d' % st['i'])
        st['phase'] = 'undo'; st['wait'] = st['t'] + 2.0; return
    if st['phase'] == 'undo':
        view, cv, hide = (SETS[st['i']].split('|') + ['', ''])[:3]
        for c in [c for c in cv.split(';') if c]:      # restore: '<cvar> <v>' entries must carry their default after '='
            if '=' in c:
                cmd(c.split('=')[1])
        st['phase'] = 'next'; return

st['h'] = unreal.register_slate_post_tick_callback(tick)
