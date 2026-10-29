"""Machine-readable summary of the Escape_Panic_v02 clips (from the *_authoring.json files). Never overwrites.
  python make_manifest_panic_v02.py   ->  escape_clips_manifest_v02.json
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
out = HERE / 'escape_clips_manifest_v02.json'
assert not out.exists(), 'Refusing overwrite'
V01 = HERE.parent / 'Escape_v01'
k1 = json.loads((V01 / 'esc_pose_keys_v01.json').read_text(encoding='utf-8'))
k2 = json.loads((HERE / 'esc_pose_keys_v02.json').read_text(encoding='utf-8'))
INTERRUPT = {
    'Esc_Lie_UnbuckleArmR_ByL_Panic_v02': 'any time -> Esc_Slump_LieReachR_v01 (crossfade 0.15-0.25 s)',
    'Esc_Lie_UnbuckleArmL_ByR_Panic_v02': 'any time -> Esc_Slump_LieReachL_v01',
    'Esc_Lie_TugArmR_Loop_Panic_v02': 'any time -> Esc_Slump_LieReachR_v01',
    'Esc_Lie_TugArmL_Loop_Panic_v02': 'any time -> Esc_Slump_LieReachL_v01',
    'Esc_SitUp_Panic_v02': 'any time -> Esc_Slump_Sit_v01',
    'Esc_Sit_UnbuckleLegL_Panic_v02': 'any time -> Esc_Slump_Sit_v01',
    'Esc_Sit_UnbuckleLegR_Panic_v02': 'any time -> Esc_Slump_Sit_v01',
    'Esc_Sit_UnbuckleLegsBoth_Panic_v02': 'any time -> Esc_Slump_Sit_v01',
    'Esc_SwingOff_R_Panic_v02': 't < 0.76 -> Esc_Slump_Sit_v01; t >= 0.76 -> Esc_Slump_Edge_R_v01 (same split as v01)',
    'Esc_SwingOff_L_Panic_v02': 't < 0.76 -> Esc_Slump_Sit_v01; t >= 0.76 -> Esc_Slump_Edge_L_v01',
    'Esc_HopRun_R_BellyClutch_v02': 't < 0.30 -> Esc_Slump_Edge_R_v01; 0.47 <= t <= 0.98 -> Esc_Stumble_Off_R_Panic_v02 (or _v01); 0.30-0.47 and > 0.98: ragdoll / capture flow (same windows as v01)',
    'Esc_HopRun_L_BellyClutch_v02': 't < 0.30 -> Esc_Slump_Edge_L_v01; 0.47 <= t <= 0.98 -> Esc_Stumble_Off_L_Panic_v02 (or _v01); 0.30-0.47 and > 0.98: ragdoll / capture flow',
    'Esc_Run_BellyClutch_Loop_Panic_v02': 'as Flee_Run_v01 (ragdoll / capture flow)',
    'Esc_Stumble_Off_R_Panic_v02': 'is itself the interrupt clip (ends on DOWN_R = ragdoll start)',
    'Esc_Stumble_Off_L_Panic_v02': 'is itself the interrupt clip (ends on DOWN_L = ragdoll start)',
}
clips = {}
for f in sorted(HERE.glob('Esc_*_authoring.json')):
    j = json.loads(f.read_text(encoding='utf-8'))
    v = j['validation']
    contacts = [{k: e[k] for k in ('name', 'strap', 'hand', 't', 'frame', 'norm') if k in e}
                for e in j['events'] if e['name'] in ('Grab', 'StrapOpen', 'Release')]
    clips[j['clip']] = {
        'fbx': j['clip'] + '.fbx', 'take': j['take'], 'unity_state_suggestion': j['clip'][:-4],
        'variant_of': j['variant_of'], 'v01_duration_s': j['v01_duration_s'], 'duration_s': j['duration_s'],
        'duration_vs_v01_pct': j['duration_vs_v01_pct'], 'frames': j['frames'], 'fps': j['fps'], 'loop': j['loop'],
        'start_pose_key': j['start_pose_key'], 'end_pose_key': j['end_pose_key'], 'chains_to': j['next'],
        'buckle_contacts': contacts,
        'strap_open': [{'strap': e['strap'], 't': e['t'], 'frame': e['frame'], 'norm': e['norm']} for e in j['events'] if e['name'] == 'StrapOpen'],
        'preconditions': j['preconditions'], 'straps_after': j['straps_after'], 'strap_animation': j['strap_animation'],
        'events': j['events'], 'interrupt': INTERRUPT.get(j['clip'], ''), 'root_motion': j['root_motion'],
        'checks': {
            'seam_vs_esc_pose_keys_v01_raw_max': v.get('seam_vs_esc_pose_keys_v01_raw_max'),
            'seam_eval_vs_pose_key_mm': j['authoring_stats'].get('seam_eval_vs_pose_key_mm'),
            'seam_step_start_mm': v.get('seam_step_start_mm'), 'seam_step_end_mm': v.get('seam_step_end_mm'),
            'buckle_contact_err_max_mm': v.get('buckle_contact_err_max_mm'),
            'pad_gap_min_mm': v.get('pad_gap_min_mm'), 'floor_min_mm': v.get('floor_min_mm'),
            'closed_strap_drift_mm': v.get('closed_strap_drift_mm'), 'self_penetration_mm': v.get('self_penetration_mm'),
            'max_key_step_deg': v.get('max_key_step_deg'), 'fbx_bone_pos_err_m': v.get('fbx_bone_pos_err_m'), 'fbx_bones': v.get('fbx_bones'),
        },
    }
man = {
    'version': 'escape_clips_manifest_v02', 'package': 'Escape_Panic_v02 (panic variants of Escape_v01, K10 case)',
    'fps': 30, 'rig': 'Buddy_Rig_Mixamo65 (65 bones, mixamorig, unchanged)',
    'unity_import': 'same as Escape_v01: Generic, Copy From Other Avatar = SAUSAGE_BUDDY_A_v04Avatar, Anim. Compression Off; Loop Time on only for *_Loop_* clips',
    'authoring_space': 'PatientRest (as v01): head +Y, face +Z, his LEFT = +X; Unity PatientRest-local = (-x, z, -y). Root motion: none (Apply Root Motion off), except the HopRun hand-off and the in-place run loop (see root_motion per clip)',
    'pose_keys': {'unchanged_from_v01': list(k1['keys']), 'new_in_v02': list(k2['keys']),
                  'files': ['../Escape_v01/esc_pose_keys_v01.json', 'esc_pose_keys_v02.json']},
    'run0_root': k1['run0_root_patientrest_unity'], 'run0_root_L': k1['run0_root_L_patientrest_unity'],
    'chaining': ['Every v02 clip starts and ends on the same pose keys as its v01 counterpart (seam error 0), so v01 and v02 clips can be mixed freely in one escape.',
                 'Panic chain: [Esc_Lie_TugArmX_Loop_Panic_v02 x n] -> Esc_Lie_UnbuckleArmX_ByY_Panic_v02 -> Esc_SitUp_Panic_v02 -> [Esc_Sit_UnbuckleLeg(L|R|sBoth)_Panic_v02] -> Esc_SwingOff_(R|L)_Panic_v02 -> Esc_HopRun_(R|L)_BellyClutch_v02 -> Esc_Run_BellyClutch_Loop_Panic_v02 (free NPC root at RUN0 / RUN0_L, 3.2 m/s; or Flee_Run_v01 with a ~0.2 s crossfade).',
                 'Esc_HopRun_*_BellyClutch_v02 ends on RUN0_BC / RUN0_BC_L = Esc_Run_BellyClutch_Loop_Panic_v02 frame 1 at the v01 RUN0 / RUN0_L root (same root, yaw and 3.2 m/s as v01).',
                 'StrapOpen times are identical to v01 (only the clip lengths changed): ARM 1.40 s, LEG one 1.35 s, LegsBoth R 1.08 s / L 1.42 s.'],
    'clips': clips,
}
out.write_text(json.dumps(man, indent=1), encoding='utf-8')
print(out)
