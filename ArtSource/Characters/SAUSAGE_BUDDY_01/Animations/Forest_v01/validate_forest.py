"""Independent validation of the saved Forest_v01 deliverables (Junkie_Walk, Inject, High_Lie_Loop).

  blender -b --factory-startup --python validate_forest.py -- [--clips all|A,B] [--dir <folder>] [--out <abs json>]

The 18 checks and thresholds of Crowd_v01/validate_crowd.py (unchanged; its helpers are imported, its main loop is
copied here with this set's registry and stems): 30 fps, 65 bones in rig order, rig/mesh data unchanged, one action,
finite, no reflection, no quaternion sign flips, key step < 25 deg, loop seam exact, sole penetration <= 1.1 mm,
planted slide <= 1 mm (keyed half-frames; treadmill frame for the walk; feet_free windows for the sit-down, the
lying legs' kick and twitch), body vs floor >= -1 cm (the lying clips are judged like BeachLie: every non-sole
vertex), props (none here), FBX bones/hierarchy, FBX bind, FBX animated error < 1.5e-4, one take + armature only,
FBX seam. Contract chains: idle == A v04 Idle frame 1; every clip end that claims junkie_walk / high_lie equal.

Information blocks (not pass/fail): the same body/sole floor numbers measured on the FOREST_OD_JUNKIE meshes (the
contact solve uses the A v04 meshes), and how far high_lie is from GetUp_FromBack_v02 frame 1 (the supine get-up).
Refuses to overwrite its report.
"""
from pathlib import Path
import sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CROWD = HERE.parent / 'Crowd_v01'
for _p in (str(CROWD), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
import numpy as np
from mathutils import Quaternion, Matrix, Vector
import crowd_core as K
import acting_core as C
import clips_forest as F
from validate_crowd import mat, err, pose, digest, mesh_signature, import_rig, bone_sig, in_windows

REV = F.REV
JUNKIE = C.CHAR / 'Types' / 'FOREST_OD_JUNKIE' / 'SAUSAGE_BUDDY_FOREST_OD_JUNKIE_v01.blend'


def args_():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--clips', default='all')
    ap.add_argument('--dir', default=str(HERE))
    ap.add_argument('--out', default='')
    return ap.parse_args(argv)


def junkie_floor(rig, f0, f1, free):
    """Lowest non-shoe vertex and deepest shoe vertex of the FOREST_OD_JUNKIE meshes bound to `rig` (30 Hz)."""
    with bpy.data.libraries.load(str(JUNKIE), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in C.MESH_NAMES]
    objs = []
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
        o.parent = rig
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Identity(4)
        for m in o.modifiers:
            if m.type == 'ARMATURE':
                m.object = rig
        objs.append(o)
    out = next(o for o in objs if o.name.startswith('Outfit'))
    names = [vg.name for vg in out.vertex_groups]
    shoe = {}
    for s, sgn in (('Left', 1), ('Right', -1)):
        shoe[s] = [v.index for v in out.data.vertices if v.co.z < .19 and v.co.x * sgn > 0 and any(
            names[g.group] in (C.P + s + 'Foot', C.P + s + 'ToeBase') and g.weight > .5 for g in v.groups)]
    sc = bpy.context.scene
    low_body, low_shoe, at_b, at_s = 1e9, 1e9, None, None
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for o in objs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            a = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get('co', a)
            P3 = a.reshape(-1, 3) @ np.array(o.matrix_world)[:3, :3].T + np.array(o.matrix_world)[:3, 3]
            ev.to_mesh_clear()
            mask = np.ones(len(P3), bool)
            if o is out:
                for s in shoe:
                    mask[shoe[s]] = False
                z = float(P3[~mask, 2].min())
                if z < low_shoe:
                    low_shoe, at_s = z, round((f - f0) / C.FPS, 3)
            z = float(P3[mask, 2].min())
            if z < low_body:
                low_body, at_b = z, round((f - f0) / C.FPS, 3)
    for o in objs:
        bpy.data.objects.remove(o)
    return {'min_body_z_m': low_body, 'min_body_z_at': at_b, 'min_shoe_z_m': low_shoe, 'min_shoe_z_at': at_s,
            'note': 'FOREST_OD_JUNKIE Body/Face/Outfit on the same keys (identical rig); shoes = its slide/sock-foot '
                    'vertices; floor contact was solved on the A v04 meshes'}


def supine_compare(B, lie_world):
    """high_lie (world matrices of the delivered clip) vs GetUp_FromBack_v02 frame 1 (acting_core's supine)."""
    sup = {n: Matrix(m) for n, m in B.supine.items()}       # the A v04 rig object sits at the world origin
    lie = {n: Matrix(v) for n, v in lie_world.items()}
    ang, pos = {}, {}
    for n in sup:
        q1, q2 = sup[n].to_quaternion(), lie[n].to_quaternion()
        ang[n] = math.degrees(q1.rotation_difference(q2).angle)
        pos[n] = (sup[n].translation - lie[n].translation).length
    worst = sorted(ang.items(), key=lambda kv: -kv[1])[:8]
    hs, hl = sup[C.P + 'Hips'].translation, lie[C.P + 'Hips'].translation
    return {'reference': 'GetUp_Idle_v01/GetUp_FromBack_v02.blend frame 1 (supine, head toward +Y)',
            'hips_supine_m': [round(x, 4) for x in hs], 'hips_high_lie_m': [round(x, 4) for x in hl],
            'hips_offset_m': [round(x, 4) for x in (hl - hs)],
            'hips_rotation_diff_deg': round(ang[C.P + 'Hips'], 2),
            'max_bone_rotation_diff_deg': round(max(ang.values()), 2),
            'mean_bone_rotation_diff_deg': round(sum(ang.values()) / len(ang), 2),
            'max_joint_position_diff_m': round(max(pos.values()), 4),
            'largest_rotation_diffs_deg': {n[len(C.P):]: round(a, 1) for n, a in worst},
            'hands_m': {s: [round(x, 3) for x in lie[C.P + s + 'Hand'].translation] for s in ('Left', 'Right')},
            'feet_m': {s: [round(x, 3) for x in lie[C.P + s + 'Foot'].translation] for s in ('Left', 'Right')}}


def main():
    a = args_()
    DIR = Path(a.dir)
    names = list(F.CLIPS) if a.clips == 'all' else a.clips.split(',')
    out = Path(a.out) if a.out else DIR / ('validation_forest_%s.json' % REV)
    assert not out.exists(), 'Refusing overwrite ' + str(out)
    B = C.Buddy()                                   # reference rig (A v04), read-only
    idle_ref = {n: mat(B.rig.matrix_world @ m) for n, m in B.idle.items()}
    original_sig = mesh_signature()
    order = list(B.rig.data.bones.keys())
    sole = B.sole
    outfit0 = B.meshes[2]
    gname = [vg.name for vg in outfit0.vertex_groups]
    toe_pad = {}
    for s_, idx in sole.items():
        toe_pad[s_] = [k for k, i in enumerate(idx) if outfit0.data.vertices[i].groups and
                       gname[max(outfit0.data.vertices[i].groups, key=lambda g: g.weight).group].endswith('ToeBase')]
    rest_rel = {s_: (B.idle[C.P + s_ + 'Foot'].to_3x3().inverted() @ B.idle[C.P + s_ + 'ToeBase'].to_3x3()).to_quaternion()
                for s_ in sole}
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
    report = {'package': 'Forest_' + REV, 'fps': C.FPS, 'sample_rate_hz': 120, 'bind_reference': bind_ref,
              'rig_source': 'json' if B.from_json else 'blend', 'thresholds': TH,
              'note': 'the A v04 rest sole sits 1.0 mm below z = 0, so planted soles read ~1 mm penetration by design',
              'clips': {}, 'contracts': {}}
    ends = {}
    for name in names:
        spec = F.CLIPS[name]
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
        poses = {}
        pen = slide = 0.0
        pen_k = slide_k = 0.0
        slide_at = None
        low_body, low_at = 1e9, None
        prev = {}
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
                if i % 2 == 0:
                    pen_k = max(pen_k, float(-sp[:, 2].min()))
                if in_windows(t, free.get(s, [])):
                    prev[s] = {}
                    continue
                g = sp.copy()
                g[:, 1] -= v_run * t                      # ground frame (treadmill)
                touch = g[:, 2] < 0.002
                fm = rig.pose.bones[C.P + s + 'Foot'].matrix.to_3x3()
                tm = rig.pose.bones[C.P + s + 'ToeBase'].matrix.to_3x3()
                bend = math.degrees((fm.inverted() @ tm).to_quaternion().rotation_difference(rest_rel[s]).angle)
                if bend > 1.0:                            # shoe bent at the ball: heel peeling, toe pad planted
                    only = np.zeros(len(idx), bool)
                    only[toe_pad[s]] = True
                    touch &= only
                nd = {}
                for j in np.nonzero(touch)[0]:
                    if j in prev.get(s, {}):              # net drift since this vertex touched down
                        p0 = prev[s][j]
                        d = float(np.hypot(*(g[j, :2] - p0[:2])))
                        if d > slide:
                            slide, slide_at = d, [round(t, 3), s]
                        if i % 2 == 0:
                            slide_k = max(slide_k, d)
                        nd[j] = p0
                    else:
                        nd[j] = g[j].copy()
                prev[s] = nd
            body = np.ones(len(P3), bool)
            body[off + np.array(sole['Left'] + sole['Right'])] = False
            lb = float(P3[body, 2].min())
            if lb < low_body:
                low_body, low_at = lb, round(t, 3)
        r.update({'max_sole_penetration_m': pen_k, 'max_planted_slide_m': slide_k,
                  'subframe_120hz': {'max_sole_penetration_m': pen, 'max_planted_slide_m': slide, 'max_planted_slide_at': slide_at},
                  'min_body_z_m': low_body, 'min_body_z_at': low_at, 'max_prop_penetration_m': None,
                  'feet_free': free, 'ground_speed_m_s': v_run or None,
                  'hips_first_m': [poses[f0]['mixamorig:Hips'][k][3] for k in range(3)],
                  'seam_matrix_error': err(poses[f0], poses[f1]) if loop else None})
        ends[name] = (poses[f0], poses[f1])
        r['junkie_mesh_info'] = junkie_floor(rig, f0, f1, free)
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
              'sole_penetration': pen_k <= TH['sole_penetration_m'], 'planted_slide': slide_k <= TH['planted_slide_m'],
              'body_floor': low_body >= TH['body_floor_m'],
              'props': True,
              'fbx_bones': r['fbx']['bone_order_matches'] and r['fbx']['hierarchy_matches'] and r['fbx']['bone_count'] == 65,
              'fbx_bind': r['fbx']['max_bind_error'] < TH['fbx_bind'], 'fbx_anim': r['fbx']['max_animated_matrix_error'] < TH['fbx_anim'],
              'fbx_one_take': len(r['fbx']['actions']) == 1 and r['fbx']['only_armature'],
              'fbx_seam': (not loop) or r['fbx']['seam_error'] < TH['fbx_seam']}
        r['checks'] = ok
        r['pass'] = all(ok.values())
        report['clips'][name] = r
        print('VALIDATED', name, r['pass'], [k for k, v in ok.items() if not v], flush=True)
    claims = {}
    for name, (p0, p1) in ends.items():
        spec = F.CLIPS[name]
        claims.setdefault(spec['start'], []).append((name + '_v01:first', p0))
        claims.setdefault(spec['end'], []).append((name + '_v01:last', p1))
    for cname, lst in claims.items():
        ref = idle_ref if cname == 'idle' else lst[0][1]
        e = {who: err(p, ref) for who, p in lst}
        report['contracts'][cname] = {'reference': 'A v04 Idle frame 1' if cname == 'idle' else lst[0][0], 'errors': e,
                                      'pass': max(e.values()) < TH['contract']}
    if 'high_lie' in claims:
        report['high_lie_vs_getup_from_back_v02'] = supine_compare(B, claims['high_lie'][0][1])
    report['pass'] = all(c['pass'] for c in report['clips'].values()) and all(c['pass'] for c in report['contracts'].values())
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('REPORT', out, 'PASS' if report['pass'] else 'FAIL', flush=True)


if __name__ == '__main__':
    main()
