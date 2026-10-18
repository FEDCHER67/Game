"""Machine-readable summary of the Escape_v01 clips (from the *_authoring.json files), never overwrites.
  python make_manifest_esc.py   ->  escape_clips_manifest_v01.json"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
out = HERE / 'escape_clips_manifest_v01.json'
assert not out.exists(), 'Refusing overwrite'
clips = {}
for f in sorted(HERE.glob('Esc_*_authoring.json')):
    j = json.loads(f.read_text(encoding='utf-8'))
    clips[j['clip']] = {k: j[k] for k in ('take', 'frames', 'duration_s', 'loop', 'start_pose_key', 'end_pose_key', 'preconditions',
                                          'straps_after', 'strap_animation', 'events', 'next', 'root_motion')}
keys = json.loads((HERE / 'esc_pose_keys_v01.json').read_text(encoding='utf-8'))
man = {'version': 'escape_clips_manifest_v01', 'fps': 30, 'rig': 'Buddy_Rig_Mixamo65 (65 bones, mixamorig, unchanged)',
       'pose_keys': list(keys['keys']), 'run0_root': keys['run0_root_patientrest_unity'],
       'run0_root_L': keys['run0_root_L_patientrest_unity'], 'clips': clips}
out.write_text(json.dumps(man, indent=1), encoding='utf-8')
print(out)
