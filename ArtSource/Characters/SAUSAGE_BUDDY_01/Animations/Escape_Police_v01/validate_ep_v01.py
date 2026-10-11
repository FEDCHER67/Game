"""Validation of saved Escape_Police_v01 deliverables (pip `bpy` 5.2 or Blender 5.2, headless).

  python validate_ep_v01.py --dir <folder with the saved <Clip>_v01.blend/.fbx> [--clips a,b|all] --out validation_v01.json
  (Blender: blender -b --factory-startup --python validate_ep_v01.py -- <args>)

Opens every saved .blend (not the authoring code), samples the action at 120 Hz and checks:
  frame range / fps; 65 bones in the rig-JSON order; NaN / reflected bones; quaternion sign flips
  between adjacent keys; largest key-to-key local rotation; exact loop seam; start / end contract
  poses (Idle frame 1 from the rig JSON, or the frame of another saved clip); skinned-mesh floor
  penetration and contact slide in the clip's ground frame (every vertex within 2 mm of the floor at
  two consecutive samples, horizontal drift minus the ground motion); cargo height limit.
Then reimports each FBX: bone order and hierarchy vs the rig JSON, bind matrices, animated matrix
error vs the .blend, reimported seam, one take, armature only. Refuses to overwrite its report.
The ground speed / floor height per clip (review-stage geometry) come from the clip registry.
"""
from pathlib import Path
import sys, json, math, argparse, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_core as E
import bpy
import numpy as np
from mathutils import Quaternion
import acting_core as C
import clips_police as CP
import clips_escape as CE

REG = {}
REG.update(CE.CLIPS)
REG.update(CP.CLIPS)
REV = 'v01'

# start / end contract per clip: 'idle' (A v04 Idle frame 1), ('clip', name, 'first'|'last'), or None
CONTRACT = {
    'Cop_Run': ('loop', 'loop'), 'Cop_Run_Fat': ('loop', 'loop'), 'Flee_Run': ('loop', 'loop'),
    'Cop_Aim': ('loop', 'loop'), 'Escape_Scramble': ('loop', 'loop'), 'Struggle_Carried': ('idle', 'idle'),
    'Cop_Punch': ('idle', 'idle'), 'Cop_ShakeFist': ('idle', 'idle'), 'Hit_React_Front': ('idle', 'idle'),
    'Hit_React_Back': ('idle', 'idle'), 'Hit_React_Head': ('idle', 'idle'), 'Stagger': ('idle', 'idle'),
    'Cop_Aim_Raise': ('idle', ('Cop_Aim', 'first')), 'Cop_Trip': (('Cop_Run', 'first'), None),
    'JumpOut': (('Escape_Scramble', 'first', E.VAN_FLOOR), ('Flee_Run', 'first')),
    'Escape_Scramble_Start': (None, ('Escape_Scramble', 'first')),
}
TH = {'contract_matrix': 1e-5, 'seam': 1e-6, 'key_step_deg': 25.0, 'penetration_m': 0.002, 'slide_m': 0.002,
      'cargo_height_m': E.CARGO_LIMIT, 'fbx_bind': 1e-4, 'fbx_anim': 1.5e-4, 'fbx_seam': 1e-5}


def mat(m):
    return [list(r) for r in m]


def err(a, b):
    return max(abs(a[n][r][c] - b[n][r][c]) for n in a for r in range(4) for c in range(4))


def pose(rig):
    return {b.name: mat(rig.matrix_world @ b.matrix) for b in rig.pose.bones}


def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.fbx(filepath=str(path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--clips', default='all')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    D = Path(a.dir)
    out = Path(a.out)
    assert not out.exists(), 'Refusing overwrite ' + str(out)
    names = list(REG) if a.clips == 'all' else a.clips.split(',')
    rigj = json.loads(C.RIG_JSON.read_text(encoding='utf-8'))
    ref_bones = {b['name']: (b['parent'], b['matrix_local']) for b in rigj['armature']['bones']}
    ref_order = [b['name'] for b in rigj['armature']['bones']]
    B = C.Buddy()
    idle = {n: mat(m) for n, m in B.idle.items()}
    first_last = {}

    def endpoints(clip):
        if clip not in first_last:
            bpy.ops.wm.open_mainfile(filepath=str(D / ('%s_%s.blend' % (clip, REV))))
            rig = bpy.data.objects[C.RIG_NAME]
            f0, f1 = (int(round(x)) for x in rig.animation_data.action.frame_range)
            bpy.context.scene.frame_set(f0)
            p0 = pose(rig)
            bpy.context.scene.frame_set(f1)
            first_last[clip] = (p0, pose(rig))
        return first_last[clip]

    def reference(spec):
        if spec in (None, 'loop'):
            return None
        if spec == 'idle':
            return idle
        clip, which = spec[0], spec[1]
        p = endpoints(clip)[0 if which == 'first' else 1]
        if len(spec) > 2:   # raised by a floor offset (JumpOut starts on the van floor)
            p = {n: [r[:3] + [r[3] + (spec[2] if i == 2 else 0.0)] for i, r in enumerate(m)] for n, m in p.items()}
        return p

    report = {'revision': REV, 'fps': C.FPS, 'sample_rate_hz': 120, 'rig_reference': C.RIG_JSON.name,
              'rig_source': 'json' if B.from_json else 'blend', 'thresholds': TH, 'clips': {}}
    for name in names:
        spec = REG[name]
        stem = '%s_%s' % (name, REV)
        refs = [reference(x) for x in CONTRACT[name]]
        bpy.ops.wm.open_mainfile(filepath=str(D / (stem + '.blend')))
        scene = bpy.context.scene
        rig = bpy.data.objects[C.RIG_NAME]
        act = rig.animation_data.action
        f0, f1 = (int(round(x)) for x in act.frame_range)
        N = f1 - f0
        loop = spec['loop']
        r = {'action': act.name, 'frames': [f0, f1], 'fps': scene.render.fps, 'duration_s': N / C.FPS, 'loop': loop,
             'bone_count': len(rig.data.bones), 'bone_order_matches_rig_json': list(rig.data.bones.keys()) == ref_order,
             'nonfinite': 0, 'reflected': 0, 'quat_sign_flips': 0, 'max_key_step_deg': 0.0, 'max_key_step_at': None}
        curves = C.fcurves_of(act)
        for n in rig.pose.bones.keys():
            fc = [next(x for x in curves if x.data_path == 'pose.bones["%s"].rotation_quaternion' % n and x.array_index == c)
                  for c in range(4)]
            for i in range(len(fc[0].keyframe_points) - 1):
                q0 = Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
                q1 = Quaternion([x.keyframe_points[i + 1].co.y for x in fc]).normalized()
                d = q0.dot(q1)
                r['quat_sign_flips'] += int(d < 0)
                ang = math.degrees(2 * math.acos(min(1.0, abs(d))))
                if ang > r['max_key_step_deg']:
                    r['max_key_step_deg'] = ang
                    r['max_key_step_at'] = [fc[0].keyframe_points[i].co.x, n]
        g = spec.get('ground')
        floor = spec.get('floor')
        top_ref = spec.get('height_ref')
        poses = {}
        pen, slide, hmax, slide_at = 0.0, 0.0, 0.0, None
        prev = None
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
            pts = []
            for o in (bpy.data.objects[n] for n in C.MESH_NAMES):
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                arr = np.empty(len(me.vertices) * 3)
                me.vertices.foreach_get('co', arr)
                M = np.array(o.matrix_world)
                pts.append(arr.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
                ev.to_mesh_clear()
            pts = np.concatenate(pts)
            G = g(t) if g else 0.0
            fl = np.array([floor(x, y - G, t) for x, y in pts[:, :2]]) if floor else 0.0
            h = pts[:, 2] - fl
            pen = max(pen, float(-h.min()))
            if top_ref:
                hmax = max(hmax, float(pts[:, 2].max() - top_ref(t)))
            touch = h < 0.002
            if prev is not None:
                pp, pt, pG = prev
                both = touch & pt
                if both.any():
                    dd = pts[both, :2] - pp[both, :2]
                    dd[:, 1] -= (G - pG)
                    s = float(np.sqrt((dd * dd).sum(1)).max())
                    if s > slide:
                        slide, slide_at = s, f
            prev = (pts, touch, G)
        r['seam_matrix_error'] = err(poses[f0], poses[f1]) if loop else None
        r['start_contract'] = str(CONTRACT[name][0])
        r['end_contract'] = str(CONTRACT[name][1])
        r['start_contract_error'] = err(poses[f0], refs[0]) if refs[0] else None
        r['end_contract_error'] = err(poses[f1], refs[1]) if refs[1] else None
        r['max_floor_penetration_m'] = pen
        r['max_contact_slide_m_per_120hz_sample'] = slide
        r['max_contact_slide_at_frame'] = slide_at
        r['ground_note'] = spec.get('ground_note', 'static floor')
        if top_ref:
            r['max_mesh_height_above_cargo_floor_m'] = hmax
        r['hips_first'] = [x[3] for x in poses[f0][C.P + 'Hips'][:3]]
        r['hips_last'] = [x[3] for x in poses[f1][C.P + 'Hips'][:3]]
        r['events'] = spec.get('events', {})
        # --- FBX reimport
        irig = import_rig(D / (stem + '.fbx'))
        bones = {b.name: (b.parent.name if b.parent else None, mat(b.matrix_local)) for b in irig.data.bones}
        worst, ends = 0.0, {}
        for f, p in poses.items():
            bpy.context.scene.frame_set(int(f), subframe=f % 1)
            q = pose(irig)
            worst = max(worst, err(q, p))
            if f in (f0, f1):
                ends[f] = q
        r['fbx'] = {'bone_count': len(bones), 'bone_order_matches': list(bones) == ref_order,
                    'hierarchy_matches': {k: v[0] for k, v in bones.items()} == {k: v[0] for k, v in ref_bones.items()},
                    'max_bind_error': max(abs(ref_bones[n][1][i][j] - bones[n][1][i][j]) for n in ref_bones for i in range(4) for j in range(4)),
                    'max_animated_matrix_error': worst, 'seam_error': err(ends[f0], ends[f1]) if loop else None,
                    'actions': {x.name: list(x.frame_range) for x in bpy.data.actions},
                    'only_armature': all(o.type == 'ARMATURE' for o in bpy.data.objects)}
        ok = {'fps_30': r['fps'] == 30, 'bones_65': r['bone_count'] == 65, 'bone_order': r['bone_order_matches_rig_json'],
              'finite': r['nonfinite'] == 0, 'no_reflection': r['reflected'] == 0, 'no_sign_flips': r['quat_sign_flips'] == 0,
              'key_step': r['max_key_step_deg'] < TH['key_step_deg'],
              'seam': (not loop) or r['seam_matrix_error'] <= TH['seam'],
              'start_contract': r['start_contract_error'] is None or r['start_contract_error'] < TH['contract_matrix'],
              'end_contract': r['end_contract_error'] is None or r['end_contract_error'] < TH['contract_matrix'],
              'floor_penetration': pen <= TH['penetration_m'], 'contact_slide': slide <= TH['slide_m'],
              'cargo_height': (not top_ref) or hmax <= TH['cargo_height_m'],
              'fbx_bone_order': r['fbx']['bone_order_matches'], 'fbx_hierarchy': r['fbx']['hierarchy_matches'],
              'fbx_bind': r['fbx']['max_bind_error'] < TH['fbx_bind'], 'fbx_anim': worst < TH['fbx_anim'],
              'fbx_one_take': len(r['fbx']['actions']) == 1, 'fbx_armature_only': r['fbx']['only_armature'],
              'fbx_seam': (not loop) or r['fbx']['seam_error'] < TH['fbx_seam']}
        r['checks'] = ok
        r['checks_passed'] = sum(ok.values())
        r['checks_total'] = len(ok)
        r['pass'] = all(ok.values())
        report['clips'][stem] = r
        print('VALIDATED', stem, r['checks_passed'], '/', r['checks_total'], [k for k, v in ok.items() if not v], flush=True)
    report['pass'] = all(c['pass'] for c in report['clips'].values())
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('REPORT', out, 'PASS' if report['pass'] else 'FAIL', flush=True)


if __name__ == '__main__':
    main()
