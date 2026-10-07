"""Independent validation of the saved Crowd_v01 deliverables (Blender 5.2 or the PyPI `bpy` module).

  python validate_crowd.py [--clips all|A,B] [--dir <folder with <clip>_v01.blend/.fbx>] [--out validation_crowd_v01.json]

Opens every saved <clip>_v01.blend, samples it at 120 Hz and checks:
  * 30 fps, whole-frame range, 65 bones in the rig order, rig/mesh data unchanged, one action
  * no NaN/inf, no reflected bones, no adjacent quaternion sign flips, largest key-to-key rotation < 25 deg
  * loops: last frame == first frame exactly; contract chains: every clip end that claims a contract pose equals
    every other one exactly (Enter end == Loop start == Loop end == Exit start), and 'idle' == A v04 Idle frame 1
  * feet: soles never more than 1 mm into the floor; planted soles (outside each clip's feet_free windows) do not
    slide: net drift of each touching sole vertex (z < 2 mm) since it touched down, in the ground frame (treadmill speed for the run) <= 1 mm
  * body: lowest vertex >= -1 cm (design limit), props: no vertex more than 5 mm into the bench seat / backrest / wall
then re-imports the FBX: bone order, hierarchy, bind matrices vs the rig JSON (or Walk_v02.fbx when real), one take,
armature only, animated world-matrix error < 1.5e-4, reimported seam < 1e-5. Refuses to overwrite its report.
"""
from pathlib import Path
import sys, json, math, argparse, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Quaternion
import crowd_core as K
import acting_core as C
import clips_crowd as CC
import clips_props as CP
import clips_floor as CF

REV = 'v01'


def args_():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--clips', default='all')
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--out', default='')
    return ap.parse_args(argv)


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
                         'p': [list(p.vertices) for p in o.data.polygons]})
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


def in_windows(t, wins):
    return any(a - 1e-9 <= t <= b + 1e-9 for a, b in wins)


def main():
    a = args_()
    DIR = Path(a.dir)
    names = list(CC.CLIPS) if a.clips == 'all' else a.clips.split(',')
    out = Path(a.out) if a.out else DIR / ('validation_crowd_%s.json' % REV)
    assert not out.exists(), 'Refusing overwrite ' + str(out)
    B = C.Buddy()                                   # reference rig (A v04 or its JSON), read-only
    idle_ref = {n: mat(B.rig.matrix_world @ m) for n, m in B.idle.items()}
    original_sig = mesh_signature()
    order = list(B.rig.data.bones.keys())
    sole = B.sole
    walk_fbx = C.ANIM / 'Locomotion_v01' / 'Walk_v02.fbx'
    if walk_fbx.exists() and walk_fbx.read_bytes()[:18] == b'Kaydara FBX Binary':
        bind = bone_sig(import_rig(walk_fbx))
        bind_ref = 'Walk_v02.fbx'
    else:
        data = json.loads(C.RIG_JSON.read_text(encoding='utf-8'))
        bind = {b['name']: (b['parent'], b['matrix_local']) for b in data['armature']['bones']}
        bind_ref = C.RIG_JSON.name
    TH = {'key_step_deg': 25.0, 'sole_penetration_m': 0.001 + 1e-4, 'planted_slide_m': 0.001, 'body_floor_m': -0.01,
          'prop_penetration_m': 0.005, 'fbx_bind': 1e-4, 'fbx_anim': 1.5e-4, 'fbx_seam': 1e-5, 'contract': 1e-5}
    report = {'package': 'Crowd_' + REV, 'fps': C.FPS, 'sample_rate_hz': 120, 'bind_reference': bind_ref,
              'rig_source': 'json' if B.from_json else 'blend', 'thresholds': TH,
              'note': 'the A v04 rest sole sits 1.0 mm below z = 0, so planted soles read ~1 mm penetration by design',
              'clips': {}, 'contracts': {}}
    ends = {}
    for name in names:
        spec = CC.CLIPS[name]
        stem = '%s_%s' % (name, REV)
        bpy.ops.wm.open_mainfile(filepath=str(DIR / (stem + '.blend')))
        scene = bpy.context.scene
        rig = bpy.data.objects[C.RIG_NAME]
        act = rig.animation_data.action
        f0, f1 = (int(round(x)) for x in act.frame_range)
        N = f1 - f0
        loop = spec['loop']
        r = {'action': act.name, 'frames': [f0, f1], 'fps': scene.render.fps, 'duration_s': N / C.FPS, 'loop': loop,
             'start_contract': spec['start'], 'end_contract': spec['end'], 'actions_in_file': len(bpy.data.actions),
             'bone_count': len(rig.data.bones), 'bone_order_matches': list(rig.data.bones.keys()) == order,
             'rig_mesh_data_unchanged': mesh_signature() == original_sig,
             'nonfinite': 0, 'reflected': 0, 'quat_sign_flips': 0, 'max_key_step_deg': 0.0, 'max_key_step_at': None}
        curves = C.fcurves_of(act)
        for n in rig.pose.bones.keys():
            fc = [next(x for x in curves if x.data_path == 'pose.bones["%s"].rotation_quaternion' % n and x.array_index == c)
                  for c in range(4)]
            for i in range(len(fc[0].keyframe_points) - 1):
                qa = Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
                qb = Quaternion([x.keyframe_points[i + 1].co.y for x in fc]).normalized()
                d = qa.dot(qb)
                r['quat_sign_flips'] += int(d < 0)
                ang = math.degrees(2 * math.acos(min(1, abs(d))))
                if ang > r['max_key_step_deg']:
                    r['max_key_step_deg'], r['max_key_step_at'] = ang, [fc[0].keyframe_points[i + 1].co.x, n[len(C.P):]]
        free = spec.get('feet_free', {})
        v_run = spec.get('run_speed', 0.0)
        objs = [bpy.data.objects[n] for n in C.MESH_NAMES]
        outfit = bpy.data.objects['Outfit']
        poses = {}
        pen = slide = 0.0
        slide_at = None
        low_body, prop_pen, low_at = 1e9, 0.0, None
        prev = {}
        drift = {s: {} for s in sole}
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
            for o in objs:
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                arr = np.empty(len(me.vertices) * 3)
                me.vertices.foreach_get('co', arr)
                M = np.array(o.matrix_world)
                pts.append(arr.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
                ev.to_mesh_clear()
            off = len(pts[0]) + len(pts[1])
            P3 = np.concatenate(pts)
            for s, idx in sole.items():
                sp = P3[off + np.array(idx)]
                pen = max(pen, float(-sp[:, 2].min()))
                if in_windows(t, free.get(s, [])):
                    drift[s] = {}
                    continue
                g = sp.copy()
                g[:, 1] -= v_run * t                      # ground frame (treadmill)
                touch = g[:, 2] < 0.002
                nd = {}
                for j in np.nonzero(touch)[0]:
                    if j in prev.get(s, {}):              # net drift since this vertex touched down
                        p0 = prev[s][j]
                        d = float(np.hypot(*(g[j, :2] - p0[:2])))
                        if d > slide:
                            slide, slide_at = d, [round(t, 3), s]
                        nd[j] = p0
                    else:
                        nd[j] = g[j].copy()
                prev[s] = nd
            body = np.ones(len(P3), bool)
            body[off + np.array(sole['Left'] + sole['Right'])] = False
            lb = float(P3[body, 2].min())
            if lb < low_body:
                low_body, low_at = lb, round(t, 3)
            if spec.get('activity') == 'BenchSit':
                b_ = CF.BENCH
                m = (P3[:, 1] > b_['front_y'] + 0.01) & (P3[:, 1] < b_['back_y']) & (P3[:, 2] < b_['seat_top']) & (P3[:, 2] > 0.39)
                if m.any():
                    prop_pen = max(prop_pen, float(b_['seat_top'] - P3[m, 2].min()))
                m = (P3[:, 2] > 0.62) & (P3[:, 2] < 0.95)            # backrest board (front face at backrest_y)
                if m.any():
                    prop_pen = max(prop_pen, float(P3[m, 1].max() - b_['backrest_y']))
            if spec.get('activity') == 'BarDoor':
                prop_pen = max(prop_pen, float(P3[:, 1].max() - CP.WALL_Y))
        r.update({'max_sole_penetration_m': pen, 'max_planted_slide_m': slide, 'max_planted_slide_at': slide_at,
                  'min_body_z_m': low_body, 'min_body_z_at': low_at, 'max_prop_penetration_m': prop_pen if spec.get('activity') in ('BenchSit', 'BarDoor') else None,
                  'hips_first_m': [poses[f0]['mixamorig:Hips'][k][3] for k in range(3)],
                  'seam_matrix_error': err(poses[f0], poses[f1]) if loop else None})
        ends[name] = (poses[f0], poses[f1])
        # FBX reimport
        irig = import_rig(DIR / (stem + '.fbx'))
        bones = bone_sig(irig)
        worst, fe = 0.0, {}
        for f, p in poses.items():
            bpy.context.scene.frame_set(int(f), subframe=f % 1)
            q = pose(irig)
            worst = max(worst, err(q, p))
            if f in (f0, f1):
                fe[f] = q
        r['fbx'] = {'bone_count': len(bones), 'bone_order_matches': list(bones) == list(bind),
                    'hierarchy_matches': {k: v[0] for k, v in bones.items()} == {k: v[0] for k, v in bind.items()},
                    'max_bind_error': max(abs(bind[n][1][i][j] - bones[n][1][i][j]) for n in bind for i in range(4) for j in range(4)),
                    'max_animated_matrix_error': worst, 'seam_error': err(fe[f0], fe[f1]) if loop else None,
                    'actions': {x.name: list(x.frame_range) for x in bpy.data.actions},
                    'only_armature': all(o.type == 'ARMATURE' for o in bpy.data.objects)}
        ok = {'fps': r['fps'] == 30, 'bones': r['bone_count'] == 65 and r['bone_order_matches'],
              'rig_unchanged': r['rig_mesh_data_unchanged'], 'one_action': r['actions_in_file'] == 1,
              'finite': r['nonfinite'] == 0, 'no_reflection': r['reflected'] == 0, 'no_sign_flips': r['quat_sign_flips'] == 0,
              'key_step': r['max_key_step_deg'] < TH['key_step_deg'], 'seam': (not loop) or r['seam_matrix_error'] == 0.0,
              'sole_penetration': pen <= TH['sole_penetration_m'], 'planted_slide': slide <= TH['planted_slide_m'],
              'body_floor': low_body >= TH['body_floor_m'],
              'props': r['max_prop_penetration_m'] is None or r['max_prop_penetration_m'] <= TH['prop_penetration_m'],
              'fbx_bones': r['fbx']['bone_order_matches'] and r['fbx']['hierarchy_matches'] and r['fbx']['bone_count'] == 65,
              'fbx_bind': r['fbx']['max_bind_error'] < TH['fbx_bind'], 'fbx_anim': r['fbx']['max_animated_matrix_error'] < TH['fbx_anim'],
              'fbx_one_take': len(r['fbx']['actions']) == 1 and r['fbx']['only_armature'],
              'fbx_seam': (not loop) or r['fbx']['seam_error'] < TH['fbx_seam']}
        r['checks'] = ok
        r['pass'] = all(ok.values())
        report['clips'][name] = r
        print('VALIDATED', name, r['pass'], [k for k, v in ok.items() if not v], flush=True)
    # contract chains
    claims = {}
    for name, (p0, p1) in ends.items():
        spec = CC.CLIPS[name]
        claims.setdefault(spec['start'], []).append((name + ':first', p0))
        claims.setdefault(spec['end'], []).append((name + ':last', p1))
    for cname, lst in claims.items():
        ref = idle_ref if cname == 'idle' else lst[0][1]
        e = {who: err(p, ref) for who, p in lst}
        report['contracts'][cname] = {'reference': 'A v04 Idle frame 1' if cname == 'idle' else lst[0][0], 'errors': e,
                                      'pass': max(e.values()) < TH['contract']}
    report['pass'] = all(c['pass'] for c in report['clips'].values()) and all(c['pass'] for c in report['contracts'].values())
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('REPORT', out, 'PASS' if report['pass'] else 'FAIL', flush=True)


if __name__ == '__main__':
    main()
