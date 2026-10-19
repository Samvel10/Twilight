# perf_set.py: move PerfCam (auto-activated for player 0 in -game) to view HL_PERFVIEW from gen/cams.json, toggle groups, save the map
import unreal, os, json
P = '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/'
v = os.environ['HL_PERFVIEW']; c = json.load(open(P + 'gen/cams.json'))[v]
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Test/L_Highlands')
hide = [h for h in os.environ.get('HL_HIDE', '').split(',') if h]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    lab = a.get_actor_label()
    if lab == 'PerfCam':
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*c['pos']), unreal.Vector(*c['tgt']))
        a.set_actor_location_and_rotation(unreal.Vector(*c['pos']), rot, False, False)
        a.camera_component.set_editor_property('field_of_view', c['fov'])
        a.camera_component.set_editor_property('constrain_aspect_ratio', False)
    a.set_is_temporarily_hidden_in_editor(False)
    for h in hide:
        if lab.startswith(h):
            a.set_actor_hidden_in_game(True)
            unreal.log_warning('PERF hide %s' % lab)
    if not any(lab.startswith(h) for h in hide) and (lab.startswith('Veg_') or lab.startswith('Rocks_')):
        a.set_actor_hidden_in_game(False)
unreal.EditorLoadingAndSavingUtils.save_map(unreal.EditorLevelLibrary.get_editor_world(), '/Game/Test/L_Highlands')
unreal.log_warning('PERF set %s' % v)
unreal.SystemLibrary.quit_editor()
