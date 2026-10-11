"""Independent validation of saved Idle_Knock_v03 deliverables (Blender 5.2, headless).

  blender -b --factory-startup --python validate_v03.py -- --clips Idle_Stand[,Idle_Bored,...]
          [--dir <folder with the saved .blend/.fbx>] [--out validation_<tag>.json]

Opens each saved <stem>.blend, samples at 120 Hz and checks: frame range / fps, 65 bones in the
original order, unchanged rig/mesh data, contract poses (Idle frame 1, GetUp_FromBack_v02 frame 1,
Cargo_Sit_Idle_v04 frame 1), exact loop seams, NaN/inf, reflected bones, quaternion key sign flips,
largest key-to-key rotation, planted-foot sole contact and sliding (standing clips), floor / wall /
1.2 m limits (cargo clips); then reimports the FBX: bone order, hierarchy, bind matrices vs
Walk_v02 (or the rig JSON in LFS-less checkouts), one take, armature only, animated matrix error
and reimported seam. Refuses to overwrite its report.
"""
from pathlib import Path
import sys, json, math, argparse, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Quaternion
import acting_core as C

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clips', required=True)
ap.add_argument('--dir', default=str(HERE))
ap.add_argument('--out', default='')
args = ap.parse_args(argv)
DIR = Path(args.dir)
STEMS = {'Idle_Stand': 'Idle_Stand_v03', 'Idle_Bored': 'Idle_Bored_v03', 'Cargo_Sit_Idle': 'Cargo_Sit_Idle_v04',
         'Cargo_Knock': 'Cargo_Knock_v03b', 'SitUp_Cargo': 'SitUp_Cargo_v04'}
# start/end contracts and stage per clip
SPEC = {'Idle_Stand': ('idle', 'idle', 'stand', True), 'Idle_Bored': ('idle', 'idle', 'stand', True),
        'Cargo_Sit_Idle': ('sit', 'sit', 'cargo', True), 'Cargo_Knock': ('sit', 'sit', 'cargo', True),
        'SitUp_Cargo': ('supine', 'sit', 'cargo', False)}
# planted-foot exclusions (seconds) for standing clips whose feet leave the floor on purpose
FOOT_FREE = {'Idle_Bored': {}}
clips = args.clips.split(',')
out = Path(args.out) if args.out else DIR / ('validation_%s.json' % '_'.join(clips))
assert not out.exists(), 'Refusing overwrite ' + str(out)


def mat(m):
    return [list(r) for r in m]


def err(a, b):
    return max(abs(a[n][r][c] - b[n][r][c]) for n in a for r in range(4) for c in range(4))


def pose(rig):
    return {b.name: mat(rig.matrix_world @ b.matrix) for b in rig.pose.bones}


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()


def mesh_signature():
    sig = {}
    for n in C.MESH_NAMES:
        o = bpy.data.objects[n]
        sig[n] = digest({'v': [[round(x, 5) for x in v.co] for v in o.data.vertices],
                         'p': [list(p.vertices) for p in o.data.polygons],
                         'w': [sorted((o.vertex_groups[g.group].name, round(g.weight, 5)) for g in v.groups)
                               for v in o.data.vertices]})
    rig = bpy.data.objects[C.RIG_NAME]
    sig['bones'] = digest([(b.name, b.parent.name if b.parent else None,
                            [[round(x, 6) for x in r] for r in b.matrix_local]) for b in rig.data.bones])
    return sig


def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.fbx(filepath=str(path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def bone_sig(rig):
    return {b.name: (b.parent.name if b.parent else None, mat(b.matrix_local)) for b in rig.data.bones}


# --- references ------------------------------------------------------------------------------
B = C.Buddy()                       # A v04 (or rig JSON), read-only; gives Idle / supine contracts
reference = {'idle': B.idle, 'supine': B.supine}
original_sig = mesh_signature()
order = list(B.rig.data.bones.keys())
sole = B.sole
WALK_FBX = C.ANIM / 'Locomotion_v01' / 'Walk_v02.fbx'
if WALK_FBX.exists() and WALK_FBX.read_bytes()[:18] == b'Kaydara FBX Binary':   # not an LFS pointer
    walk = bone_sig(import_rig(WALK_FBX))
    bind_ref = 'Walk_v02.fbx'
else:
    data = json.loads(C.RIG_JSON.read_text(encoding='utf-8'))
    walk = {b['name']: (b['parent'], b['matrix_local']) for b in data['armature']['bones']}
    bind_ref = C.RIG_JSON.name
sit_blend = DIR / (STEMS['Cargo_Sit_Idle'] + '.blend')
if sit_blend.exists():
    bpy.ops.wm.open_mainfile(filepath=str(sit_blend))
    bpy.context.scene.frame_set(1)
    reference['sit'] = pose(bpy.data.objects[C.RIG_NAME])

report = {'fps': C.FPS, 'sample_rate_hz': 120, 'bind_reference': bind_ref, 'rig_source': 'json' if B.from_json else 'blend',
          'thresholds': {'seam_source': 0.0, 'contract_matrix': 1e-5, 'sole_penetration_m': 0.001,
                         'support_ground_error_m': 0.001, 'planted_foot_slide_m': 0.001, 'key_step_deg': 25,
                         'height_m': C.HEIGHT_LIMIT, 'floor_m': -1e-6, 'wall_x_m': C.WALL_X,
                         'fbx_bind': 1e-4, 'fbx_anim': 1.5e-4, 'fbx_seam': 1e-5},
          'clips': {}}
for name in clips:
    stem = STEMS[name]
    start_c, end_c, stage, loop = SPEC[name]
    bpy.ops.wm.open_mainfile(filepath=str(DIR / (stem + '.blend')))
    scene = bpy.context.scene
    rig = bpy.data.objects[C.RIG_NAME]
    act = rig.animation_data.action
    f0, f1 = (int(round(x)) for x in act.frame_range)
    N = f1 - f0
    r = {'action': act.name, 'frames': [f0, f1], 'fps': scene.render.fps, 'duration_s': N / C.FPS, 'loop': loop,
         'bone_count': len(rig.data.bones), 'bone_order_matches_a_v04': list(rig.data.bones.keys()) == order,
         'rig_mesh_data_unchanged': mesh_signature() == original_sig,
         'nonfinite': 0, 'reflected': 0, 'quat_sign_flips': 0, 'max_key_step_deg': 0.0}
    curves = C.fcurves_of(act)
    for n in rig.pose.bones.keys():
        fc = [next(x for x in curves if x.data_path == f'pose.bones["{n}"].rotation_quaternion' and x.array_index == c)
              for c in range(4)]
        for i in range(len(fc[0].keyframe_points) - 1):
            a = Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
            b = Quaternion([x.keyframe_points[i + 1].co.y for x in fc]).normalized()
            d = a.dot(b)
            r['quat_sign_flips'] += int(d < 0)
            r['max_key_step_deg'] = max(r['max_key_step_deg'], math.degrees(2 * math.acos(min(1, abs(d)))))
    outfit = bpy.data.objects['Outfit']
    planted = {}
    poses = {}
    lows, highs, minx = [], [], []
    ground, pen, slide = 0.0, 0.0, 0.0
    first_feet = None
    for i in range(N * 4 + 1):
        f = f0 + i / 4
        t = (f - f0) / C.FPS
        scene.frame_set(int(f), subframe=f % 1)
        for b in rig.pose.bones:
            m = b.matrix
            r['nonfinite'] += sum(not math.isfinite(x) for row in m for x in row)
            r['reflected'] += int(m.to_3x3().determinant() <= 0)
        if i % 2 == 0:
            poses[f] = pose(rig)
        dg = bpy.context.evaluated_depsgraph_get()
        if stage == 'stand':
            ev = outfit.evaluated_get(dg)
            me = ev.to_mesh()
            feet = {s: [rig.matrix_world @ rig.pose.bones[C.P + s + p].head for p in ('Foot', 'ToeBase')] +
                       [rig.matrix_world @ rig.pose.bones[C.P + s + 'ToeBase'].tail] for s in ('Left', 'Right')}
            if first_feet is None:
                first_feet = feet
            for s in ('Left', 'Right'):
                low = min((outfit.matrix_world @ me.vertices[j].co).z for j in sole[s])
                pen = max(pen, -low)
                free = any(a <= t <= b for a, b in FOOT_FREE.get(name, {}).get(s, []))
                if not free:
                    ground = max(ground, abs(low))
                    slide = max(slide, max((p - q).length for p, q in zip(feet[s], first_feet[s])))
            ev.to_mesh_clear()
        else:
            pts = []
            for o in (bpy.data.objects[n] for n in C.MESH_NAMES):
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                a = np.empty(len(me.vertices) * 3)
                me.vertices.foreach_get('co', a)
                M = np.array(o.matrix_world)
                pts.append(a.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
                ev.to_mesh_clear()
            pts = np.concatenate(pts)
            lows.append(float(pts[:, 2].min()))
            highs.append(float(pts[:, 2].max()))
            minx.append(float(pts[:, 0].min()))
    r['seam_matrix_error'] = err(poses[f0], poses[f1]) if loop else None
    r['start_contract'] = start_c
    r['end_contract'] = end_c
    r['start_contract_error'] = err(poses[f0], reference[start_c]) if start_c in reference else 'reference missing'
    r['end_contract_error'] = err(poses[f1], reference[end_c]) if end_c in reference else 'reference missing'
    if stage == 'stand':
        r.update({'max_sole_penetration_m': pen, 'max_support_ground_error_m': ground,
                  'max_planted_foot_slide_m': slide})
    else:
        r.update({'max_mesh_height_m': max(highs), 'min_mesh_z_m': min(lows), 'min_mesh_x_m': min(minx),
                  'wall_clearance_m': min(minx) - C.WALL_X})
    r['hips_first_height_m'] = poses[f0][C.P + 'Hips'][2][3]
    # --- FBX reimport
    irig = import_rig(DIR / (stem + '.fbx'))
    bones = bone_sig(irig)
    worst, ends = 0.0, {}
    for f, p in poses.items():
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        a = pose(irig)
        worst = max(worst, err(a, p))
        if f in (f0, f1):
            ends[f] = a
    r['fbx'] = {'bone_count': len(bones), 'bone_order_matches': list(bones) == list(walk),
                'hierarchy_matches': {k: v[0] for k, v in bones.items()} == {k: v[0] for k, v in walk.items()},
                'max_bind_error': max(abs(walk[n][1][a][b] - bones[n][1][a][b]) for n in walk for a in range(4) for b in range(4)),
                'max_animated_matrix_error': worst,
                'seam_error': err(ends[f0], ends[f1]) if loop else None,
                'actions': {a.name: list(a.frame_range) for a in bpy.data.actions},
                'only_armature': all(o.type == 'ARMATURE' for o in bpy.data.objects)}
    th = report['thresholds']
    ok = [r['fps'] == 30, r['bone_count'] == 65, r['bone_order_matches_a_v04'], r['rig_mesh_data_unchanged'],
          r['nonfinite'] == 0, r['reflected'] == 0, r['quat_sign_flips'] == 0, r['max_key_step_deg'] < th['key_step_deg'],
          not loop or r['seam_matrix_error'] == 0.0,
          isinstance(r['start_contract_error'], float) and r['start_contract_error'] < th['contract_matrix'],
          isinstance(r['end_contract_error'], float) and r['end_contract_error'] < th['contract_matrix'],
          r['fbx']['bone_order_matches'], r['fbx']['hierarchy_matches'], r['fbx']['max_bind_error'] < th['fbx_bind'],
          r['fbx']['max_animated_matrix_error'] < th['fbx_anim'], len(r['fbx']['actions']) == 1, r['fbx']['only_armature'],
          not loop or r['fbx']['seam_error'] < th['fbx_seam']]
    if stage == 'stand':
        ok += [r['max_sole_penetration_m'] < th['sole_penetration_m'], r['max_support_ground_error_m'] < th['support_ground_error_m'],
               r['max_planted_foot_slide_m'] < th['planted_foot_slide_m']]
    else:
        ok += [r['max_mesh_height_m'] <= th['height_m'], r['min_mesh_z_m'] >= th['floor_m'], r['min_mesh_x_m'] >= C.WALL_X - 1e-6]
    r['checks_passed'] = sum(ok)
    r['checks_total'] = len(ok)
    r['pass'] = all(ok)
    report['clips'][stem] = r
report['pass'] = all(c['pass'] for c in report['clips'].values())
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
