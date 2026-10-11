"""Validate the saved GetUp_From{Back,Belly}_v03 deliverables at 120 Hz, then independently reimport each FBX.

  blender -b --factory-startup --python validate_getups_v03.py -- [--dir <folder with the .blend/.fbx>] [--out <json>]

Checks (HANDOFF.md contracts + acceptance criteria): one action named after the file, 30 fps, frames 1..N+1,
duration 2.0-2.8 s; first frame held >= 5 frames; hipsStart; Stable (frame/fraction, held to the end); last
frame = Idle frame 1 (< 1e-5); hips net horizontal drift 0; standing soles (after Stable) penetration <= 1 mm and
support error <= 5 mm; whole skinned mesh never more than 1 cm under the floor (aim 2 mm), hands/body per region;
no NaN, no reflected bones, no adjacent quaternion key sign flips, max half-frame local rotation < 25 deg;
bone names/order/parents/rest identical to rig_Buddy_Mixamo65.json (= A v04 = GPT v02 FBX = Walk_v02) and, when
the binaries are present (not Git LFS pointers), to the v02 FBX; FBX: armature only, exactly one action,
reimport world-matrix error < 1.5e-4, bind error < 1e-4. Also reports the max mesh height per sample and the
first frame where the body rises above the van's 1.2 m cargo height (information only: get-ups are not van clips).
Refuses to overwrite --out.
"""
from pathlib import Path
import sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent
sys.path.insert(0, str(SRC))
import bpy
import numpy as np
from mathutils import Matrix

P = 'mixamorig:'
CLIPS = ('GetUp_FromBack', 'GetUp_FromBelly')
ap = argparse.ArgumentParser()
ap.add_argument('--dir', default=str(HERE))
ap.add_argument('--out', default=str(HERE / 'validation_v03.json'))
ap.add_argument('--revision', type=int, default=3)
ap.add_argument('--ref-fbx', default=str(HERE.parent / 'GetUp_Idle_v01' / 'GetUp_FromBack_v02.fbx'))
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
VERSION = 'v%02d' % args.revision
D = Path(args.dir)
OUT = Path(args.out)
assert not OUT.exists(), 'Refusing overwrite ' + str(OUT)
RIG = json.loads((HERE / 'rig_Buddy_Mixamo65.json').read_text(encoding='utf-8'))
REF_BONES = [(b['name'], b['parent']) for b in RIG['bones']]
REF_REST = {b['name']: b['matrix_local'] for b in RIG['bones']}
IDLE = {n: v['matrix_armature'] for n, v in RIG['idle_frame1']['bones'].items()}


def mat(m):
    return [list(r) for r in m]


def max_err(a, b):
    return max(abs(a[n][r][c] - b[n][r][c]) for n in b for r in range(4) for c in range(4))


def is_lfs_pointer(p):
    return p.exists() and p.read_bytes()[:40].startswith(b'version https://git-lfs')


def bone_sig(rig):
    return [(b.name, b.parent.name if b.parent else None) for b in rig.data.bones], \
           {b.name: mat(b.matrix_local) for b in rig.data.bones}


def import_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.fbx(filepath=str(path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def region_tables(objs):
    """Vertex index sets: soles (shoe vertices low in rest), hands, everything."""
    out = {}
    for o in objs:
        names = [g.name for g in o.vertex_groups]
        hands, soles = [], {'Left': [], 'Right': []}
        for v in o.data.vertices:
            acc = {}
            for g in v.groups:
                acc[names[g.group]] = acc.get(names[g.group], 0.0) + g.weight
            if sum(w for n, w in acc.items() if 'Hand' in n) > 0.5:
                hands.append(v.index)
            if o.name == 'Outfit' and (o.matrix_world @ v.co).z < 0.19:
                for s in soles:
                    if acc.get(P + s + 'Foot', 0) + acc.get(P + s + 'ToeBase', 0) > 0.5:
                        soles[s].append(v.index)
        out[o.name] = {'hands': np.array(hands, dtype=int), 'soles': {s: np.array(i, dtype=int) for s, i in soles.items()}}
    return out


def validate_clip(name):
    stem = name + '_' + VERSION
    r = {'file': stem + '.blend'}
    bpy.ops.wm.open_mainfile(filepath=str(D / (stem + '.blend')))
    sc = bpy.context.scene
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    objs = [bpy.data.objects[n] for n in ('Body', 'Face', 'Outfit')]
    act = rig.animation_data.action
    N = int(round(sc.frame_end - sc.frame_start))
    r.update({'action': act.name, 'actions_in_file': [a.name for a in bpy.data.actions], 'fps': sc.render.fps,
              'frames': [sc.frame_start, sc.frame_end], 'duration_s': N / 30.0,
              'face_or_shape_key_animation': any(o.data.shape_keys and o.data.shape_keys.animation_data and
                                                 o.data.shape_keys.animation_data.action for o in objs)})
    sig, rest = bone_sig(rig)
    r['bones'] = {'count': len(sig), 'names_order_parents_match_rig_json': sig == REF_BONES,
                  'rest_max_error_vs_rig_json': max(abs(rest[n][i][j] - REF_REST[n][i][j]) for n in REF_REST
                                                    for i in range(4) for j in range(4))}
    # quaternion keys: sign flips and max half-frame step (local rotations)
    import buddy_rig as RG
    curves = RG.fcurves_of(act)
    flips, step = 0, (0.0, None, None)
    for b in rig.pose.bones:
        ch = [next(fc for fc in curves if fc.data_path == 'pose.bones["%s"].rotation_quaternion' % b.name and
                   fc.array_index == c) for c in range(4)]
        kp = [[fc.keyframe_points[i].co.y for fc in ch] for i in range(len(ch[0].keyframe_points))]
        fr = [ch[0].keyframe_points[i].co.x for i in range(len(kp))]
        for i in range(len(kp) - 1):
            a, c = np.array(kp[i]), np.array(kp[i + 1])
            dot = float(a @ c / (np.linalg.norm(a) * np.linalg.norm(c)))
            flips += dot < 0
            ang = math.degrees(2 * math.acos(min(1.0, abs(dot))))
            if ang > step[0]:
                step = (ang, fr[i + 1], b.name)
    r['negative_adjacent_quaternion_key_dots'] = flips
    r['max_half_frame_local_rotation_deg'] = round(step[0], 3)
    r['max_half_frame_rotation_at'] = [step[1], step[2]]
    tables = region_tables(objs)
    hips, sole_low, hand_low, body_low, top, nan, refl, poses = [], [], [], [], [], 0, 0, {}
    spine_up = []
    for i in range(4 * N + 1):
        f = 1 + i / 4
        sc.frame_set(int(f), subframe=f - int(f))
        hb = rig.pose.bones[P + 'Hips']
        hips.append(list(rig.matrix_world @ hb.head))
        s2 = rig.matrix_world @ rig.pose.bones[P + 'Spine2'].head
        up = (s2 - rig.matrix_world @ hb.head).normalized()
        spine_up.append(up.z)
        for b in rig.pose.bones:
            m = b.matrix
            if m.to_3x3().determinant() <= 0:
                refl += 1
            nan += sum(not math.isfinite(x) for row in m for x in row)
        if i % 4 == 0:
            poses[1 + i // 4] = {b.name: mat(rig.matrix_world @ b.matrix) for b in rig.pose.bones}
        dg = bpy.context.evaluated_depsgraph_get()
        lows = {'Left': 9.0, 'Right': 9.0}
        hl, bl, tp = 9.0, 9.0, -9.0
        for o in objs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get('co', co)
            ev.to_mesh_clear()
            M = np.array(o.matrix_world)
            z = co.reshape(-1, 3) @ M[2, :3] + M[2, 3]
            bl, tp = min(bl, float(z.min())), max(tp, float(z.max()))
            t = tables[o.name]
            if len(t['hands']):
                hl = min(hl, float(z[t['hands']].min()))
            for s, idx in t['soles'].items():
                if len(idx):
                    lows[s] = min(lows[s], float(z[idx].min()))
        sole_low.append(lows)
        hand_low.append(hl)
        body_low.append(bl)
        top.append(tp)
    # Stable: hips > 0.6 m, within 0.35 m of the root, spine within 35 deg of vertical, holding to the end
    stable = None
    for i, (h, u) in enumerate(zip(hips, spine_up)):
        ok = h[2] > 0.6 and math.hypot(h[0], h[1]) < 0.35 and u > math.cos(math.radians(35))
        if ok and stable is None:
            stable = i
        elif not ok:
            stable = None
    st_f = None if stable is None else stable / 4
    stand = range(stable, len(hips)) if stable is not None else range(0)
    first = poses[1]
    hold = 0
    for f in range(2, N + 1):
        if max_err(poses[f], first) < 1e-6:
            hold = f - 1
        else:
            break
    over = [i / 4 for i, t in enumerate(top) if t > 1.2]
    r.update({
        'hipsStart_m': [round(c, 6) for c in hips[0]],
        'start_hold_frames': hold,
        'stable_frame_0based': st_f, 'stable_fraction': None if st_f is None else round(st_f / N, 4),
        'idle_end_matrix_error': max_err(poses[N + 1], IDLE),
        'hips_net_horizontal_drift_m': math.hypot(hips[-1][0] - hips[0][0], hips[-1][1] - hips[0][1]),
        'hips_max_horizontal_excursion_m': max(math.hypot(h[0], h[1]) for h in hips),
        'standing_max_sole_penetration_m': max([max(0.0, -min(sole_low[i].values())) for i in stand] or [None]),
        'standing_support_max_ground_error_m': max([abs(min(sole_low[i].values())) for i in stand] or [None]),
        'all_frames_max_sole_penetration_m': max(max(0.0, -min(s.values())) for s in sole_low),
        'all_mesh_max_floor_penetration_m': max(0.0, -min(body_low)),
        'hands_max_floor_penetration_m': max(0.0, -min(hand_low)),
        'nan_or_infinite_components': nan, 'reflected_bone_samples': refl,
        'max_mesh_height_m': round(max(top), 4),
        'van_1p2m_first_frame_above_0based': over[0] if over else None,
        'sample_rate_hz': 120,
    })
    return r, poses, N


import os
report = {'version': VERSION, 'validator': 'validate_getups_v03.py', 'source_rig': RIG['source_blend'],
          'built_from': ('rig/mesh rebuilt from rig_Buddy_Mixamo65.json + mesh_proxy_Buddy_A_v04.json '
                         '(GETUP_SOURCE_BLEND; no Git LFS)') if os.environ.get('GETUP_SOURCE_BLEND')
                        else 'SAUSAGE_BUDDY_A_v04.blend (Git LFS source)',
          'source_sha256': RIG['source_sha256'], 'clips': {}}
src_poses = {}
for name in CLIPS:
    r, poses, N = validate_clip(name)
    report['clips'][name + '_' + VERSION] = r
    src_poses[name] = (poses, N)
ref_ok = None
ref = Path(args.ref_fbx)
ref_sig = None
if ref.exists() and not is_lfs_pointer(ref):
    ref_sig = bone_sig(import_fbx(ref))
for name in CLIPS:
    stem = name + '_' + VERSION
    r = report['clips'][stem]
    rig = import_fbx(D / (stem + '.fbx'))
    sig, rest = bone_sig(rig)
    poses, N = src_poses[name]
    err = 0.0
    for f, pose in poses.items():
        bpy.context.scene.frame_set(f)
        err = max(err, max_err({b.name: mat(rig.matrix_world @ b.matrix) for b in rig.pose.bones}, pose))
    fb = {'bone_count': len(sig), 'names_order_parents_match_rig_json': sig == REF_BONES,
          'max_animated_world_matrix_error': err,
          'actions': {a.name: list(a.frame_range) for a in bpy.data.actions},
          'only_armature_objects': all(o.type == 'ARMATURE' for o in bpy.data.objects)}
    if ref_sig is not None:
        fb['names_order_parents_match_v02_fbx'] = sig == ref_sig[0]
        fb['max_bind_matrix_error_vs_v02_fbx'] = max_err(rest, ref_sig[1])
    else:
        fb['v02_fbx_reference'] = 'not available (Git LFS pointer or missing); compared with rig_Buddy_Mixamo65.json'
    r['fbx_reimport'] = fb
    checks = {
        'one_action_named': r['action'] == stem and len(r['actions_in_file']) == 1,
        'fps_30': r['fps'] == 30, 'duration_2_to_2p8': 2.0 - 1e-9 <= r['duration_s'] <= 2.8 + 1e-9,
        'start_hold_ge_5': r['start_hold_frames'] >= 5,
        'stable_found': r['stable_frame_0based'] is not None,
        'idle_end': r['idle_end_matrix_error'] < 1e-5,
        'in_place': r['hips_net_horizontal_drift_m'] < 1e-6,
        'standing_soles': (r['standing_max_sole_penetration_m'] or 0) <= 0.001 and
                          (r['standing_support_max_ground_error_m'] or 0) <= 0.005,
        'floor_1cm': r['all_mesh_max_floor_penetration_m'] <= 0.01,
        'no_nan_or_reflection': r['nan_or_infinite_components'] == 0 and r['reflected_bone_samples'] == 0,
        'no_quat_flips': r['negative_adjacent_quaternion_key_dots'] == 0,
        'rot_step_lt_25': r['max_half_frame_local_rotation_deg'] < 25,
        'no_face_curves': not r['face_or_shape_key_animation'],
        'bones_identical': r['bones']['count'] == 65 and r['bones']['names_order_parents_match_rig_json'] and
                           r['bones']['rest_max_error_vs_rig_json'] < 1e-5 and fb['names_order_parents_match_rig_json'],
        'fbx_one_action_armature_only': len(fb['actions']) == 1 and fb['only_armature_objects'],
        'fbx_reimport_error': err < 1.5e-4,
        'fbx_bind_vs_v02': fb.get('max_bind_matrix_error_vs_v02_fbx', 0.0) < 1e-4 and
                           fb.get('names_order_parents_match_v02_fbx', True),
    }
    r['checks'] = checks
    r['pass'] = all(checks.values())
report['pass'] = all(r['pass'] for r in report['clips'].values())
OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
