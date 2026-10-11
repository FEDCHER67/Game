"""Write getup_manifest_v03.json (the clip manifest for Unity / the ragdoll blend) from the validation report,
the authoring metrics and the beat sheets. Run after build --final and validate_getups_v03.py:
  blender -b --factory-startup --python make_manifest_v03.py      (or: python make_manifest_v03.py with pip bpy)
Refuses to overwrite.
"""
from pathlib import Path
import sys, json
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy  # noqa: F401  (provides mathutils for the choreography module)
import getup_choreo_v03 as C

OUT = HERE / 'getup_manifest_v03.json'
assert not OUT.exists(), 'Refusing overwrite ' + OUT.name
val = json.loads((HERE / 'validation_v03.json').read_text(encoding='utf-8'))
BEATS = {'GetUp_FromBack': C.BEATS_BACK, 'GetUp_FromBelly': C.BEATS_BELLY}
START = {'GetUp_FromBack': 'supine, face up, head toward local +Y, feet -Y; butt and hood on the floor (pelvis pitch -67), '
                           'head resting on the hood, arms along the sides, palms down',
         'GetUp_FromBelly': 'prone, face down, head toward local -Y, feet +Y; right cheek on the floor, head turned left, '
                            'hands beside the chest ready to push, thighs and shoe tops on the floor'}
clips = []
for name, beats in BEATS.items():
    stem = name + '_v03'
    v = val['clips'][stem]
    a = json.loads((HERE / (stem + '_authoring.json')).read_text(encoding='utf-8'))
    n = beats['N']
    clips.append({
        'name': stem, 'action': v['action'], 'blend': stem + '.blend', 'fbx': stem + '.fbx',
        'fps': 30, 'frames_blender': [1, n + 1], 'frame_count': n + 1, 'duration_s': round(n / 30, 4),
        'loop': False, 'applyRootMotion': False, 'in_place': True,
        'hipsStart_m': v['hipsStart_m'],
        'start_head_dir_root_space': a['start_head_dir'],
        'start_pose': START[name],
        'start_hold_frames': v['start_hold_frames'],
        'ragdoll_blend': 'first frame = neutral lying pose held %d frames; blend ragdoll->clip over 0.35 s '
                         '(Neck/Head 0.5 s); the first motion after the hold is slow' % v['start_hold_frames'],
        'stable': {'frame_0based': v['stable_frame_0based'], 'fraction': v['stable_fraction'],
                   'time_s': round(v['stable_frame_0based'] / 30, 4),
                   'meaning': 'from here to the end the character is upright over the root with feet down '
                              '(standing capsule may turn on)'},
        'end_pose': 'exactly SAUSAGE_BUDDY_A_v04 Idle frame 1 (matrix error %.1e)' % v['idle_end_matrix_error'],
        'hips_max_horizontal_excursion_m': round(v['hips_max_horizontal_excursion_m'], 4),
        'max_mesh_height_m': v['max_mesh_height_m'],
        'van_1p2m_first_frame_above_0based': v['van_1p2m_first_frame_above_0based'],
        'beats_0based': [{'from': b[0], 'to': b[1], 'what': b[2]} for b in beats['beats']],
        'validation_pass': v['pass'],
    })
manifest = {'package': 'SAUSAGE_BUDDY_01 GetUp v03', 'rig': 'Buddy_Rig_Mixamo65 (65 bones, root mixamorig:Hips)',
            'units': 'metres; Blender Z up, character faces -Y; FBX -Z forward, Y up',
            'source': 'getup_choreo_v03.py + getup_lib_v03.py via build_getups_v03.py --final (deterministic)',
            'validation': 'validation_v03.json (pass=%s)' % val['pass'], 'clips': clips}
OUT.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('MANIFEST', OUT, flush=True)
