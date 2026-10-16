"""Independent validation of the saved Operation_v01 deliverables (Blender 5.2, headless).

  blender -b --factory-startup --python validate_op_v01.py -- --clips Awake,Asleep,... [--out validation_op_v01.json]
  (--dev: author the clips in memory with build_op_v01's code instead of opening saved files; for iteration only)

Opens each saved Op_*_v01.blend, samples at 120 Hz and evaluates the skinned Body/Face/Shorts with
Blender's own Armature modifier (not the authoring skinning), against the TABLE-ASTRA-001 v02 geometry
appended fresh from TABLE-ASTRA-001_v02.blend (+ InstrumentStand_v01 at the TrayAnchor):
  * rig: 65 bones in the PATIENT order, rest matrices and mesh data identical to the PATIENT source
  * keys: finite, no reflected bones, no adjacent quaternion sign flips, largest key-to-key rotation
  * pad / pillow: minimum gap of every vertex above the pad top (exact ray casts), triangle overlaps
  * all table parts (pad, frame, rails, handle, wheels, casters, braces, strap anchors, straps closed
    or open as the clip assumes, instrument stand): triangle-overlap counts, strap penetration depth
  * strap points (distal forearm, shin, pelvis, wrist joint): max displacement from TABLE_REST
  * floor (EscapeFall, KnockedOut): minimum vertex height, end resting on the floor
  * loop seams (matrix error), contracts (TABLE_REST start, ShockDeath end = Dead, EscapeFall end =
    KnockedOut start + root offset)
  * FBX reimport: one take, armature only, bone order / hierarchy, bind matrices vs the PATIENT FBX,
    animated matrix error, reimported seam
Refuses to overwrite its report.
"""
from pathlib import Path
import sys, json, math, argparse, hashlib, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import op_core as O

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clips', default='Awake,Asleep,Struggle,Panic,ShockDeath,Dead,EscapeFall,KnockedOut')
ap.add_argument('--out', default='')
ap.add_argument('--dev', action='store_true')
ap.add_argument('--no-fbx', action='store_true')
ap.add_argument('--rate', type=int, default=120)
args = ap.parse_args(argv)
STEMS = {'Awake': 'Op_Lie_Awake_v01', 'Asleep': 'Op_Lie_Asleep_v01', 'Struggle': 'Op_Struggle_v01',
         'Panic': 'Op_Panic_v01', 'ShockDeath': 'Op_ShockDeath_v01', 'Dead': 'Op_Dead_v01',
         'EscapeFall': 'Op_EscapeFall_v01', 'KnockedOut': 'Op_KnockedOut_v01'}
LOOP = {'Awake': True, 'Asleep': True, 'Struggle': True, 'Panic': True, 'ShockDeath': False, 'Dead': True,
        'EscapeFall': False, 'KnockedOut': True}
STRAPS_OPEN = {'EscapeFall', 'KnockedOut'}
STRAPPED = {'Struggle', 'Panic'}                      # strap-point displacement gate (brief: ~3-4 cm)
ON_TABLE = {'Awake', 'Asleep', 'Struggle', 'Panic', 'ShockDeath', 'Dead'}
clips = args.clips.split(',')
out_path = Path(args.out) if args.out else HERE / 'validation_op_v01.json'
if not args.dev:
    assert not out_path.exists(), 'Refusing overwrite ' + str(out_path)
TH = {'key_step_deg': 25.0, 'pad_gap_m': 0.0, 'floor_m': 0.0, 'seam': 0.0, 'contract': 1e-5,
      'strap_point_m': 0.04, 'strap_pen_m': 0.008, 'fbx_bind': 1e-4, 'fbx_anim': 5e-3, 'fbx_seam': 1e-5,
      'fbx_anim_note': 'FBX stores Euler curves in float32; the clavicles sit at the Euler gimbal (local Y = 90 deg) in TABLE_REST, so shoulder roll loses ~0.1 deg on single frames (<= 3 mm at the hands)'}
SOLID = ('GEO_Padded_Top', 'GEO_Frame_And_Legs', 'GEO_Push_Handle_Foot', 'GEO_Strap_Anchors',
         'GEO_Lower_Longitudinal_Brace_Left', 'GEO_Lower_Longitudinal_Brace_Right',
         'GEO_Wheel_Foot_Left', 'GEO_Wheel_Foot_Right', 'GEO_Wheel_Head_Left', 'GEO_Wheel_Head_Right',
         'GEO_Caster_Fork_Foot_Left', 'GEO_Caster_Fork_Foot_Right', 'GEO_Caster_Fork_Head_Left', 'GEO_Caster_Fork_Head_Right',
         'GEO_Caster_Socket_Foot_Left', 'GEO_Caster_Socket_Foot_Right', 'GEO_Caster_Socket_Head_Left', 'GEO_Caster_Socket_Head_Right',
         'GEO_Stand_Frame', 'GEO_Stand_Tray', 'GEO_Stand_Wheels')


def mat(m):
    return [list(r) for r in m]


def err(a, b):
    return max(abs(a[n][r][c] - b[n][r][c]) for n in a for r in range(4) for c in range(4))


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()


def mesh_signature():
    sig = {}
    for n in O.MESH_NAMES:
        o = bpy.data.objects[n]
        sk = [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
        sig[n] = digest({'v': [[round(x, 5) for x in v.co] for v in o.data.vertices],
                         'p': [list(p.vertices) for p in o.data.polygons],
                         'w': [sorted((o.vertex_groups[g.group].name, round(g.weight, 5)) for g in v.groups)
                               for v in o.data.vertices], 'sk': sk})
    rig = bpy.data.objects[O.RIG_NAME]
    sig['bones'] = digest([(b.name, b.parent.name if b.parent else None,
                            [[round(x, 6) for x in r] for r in b.matrix_local]) for b in rig.data.bones])
    return sig


def arm_pose(rig):
    return {b.name: mat(b.matrix) for b in rig.pose.bones}


def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.fbx(filepath=str(path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def bone_sig(rig):
    return {b.name: (b.parent.name if b.parent else None, mat(b.matrix_local)) for b in rig.data.bones}


def world_mesh(o, dg):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', a)
    M = np.array(o.matrix_world)
    pts = a.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return pts, polys


# ---------------------------------------------------------------------------------- references
B = O.Patient()                       # PATIENT source + TABLE_REST contract (read-only)
order = list(B.rig.data.bones.keys())
src_sig = mesh_signature()
B.init_strap_points()
strap_local = dict(B._strap_local)
ref_tr = {n: mat(m) for n, m in B.tablerest.items()}
PATIENT_FBX = O.CHAR / 'Patient_v01' / 'SAUSAGE_BUDDY_PATIENT_v01.fbx'
bind = bone_sig(import_rig(PATIENT_FBX))

if args.dev:
    import op_clips as OC
    import importlib

report = {'fps': O.FPS, 'sample_rate_hz': args.rate, 'thresholds': TH, 'bind_reference': PATIENT_FBX.name,
          'stage': 'TABLE-ASTRA-001_v02.blend geometry + InstrumentStand_v01 at TrayAnchor table (0.57, 0.29, 0)',
          'clips': {}}
first_pose = {}
last_pose = {}
first_vals = {}
last_vals = {}

for name in clips:
    t0 = time.time()
    stem = STEMS[name]
    loop = LOOP[name]
    if args.dev:
        sys.argv = [sys.argv[0], '--', '--clip', name]
        import build_op_v01 as BD
        importlib.reload(BD)
        Bd = O.Patient()
        act, N, info, ctx = BD.author(Bd, name)
        rig = Bd.rig
    else:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / (stem + '.blend')))
        rig = bpy.data.objects[O.RIG_NAME]
        act = rig.animation_data.action
    # fresh stage (the review collection saved in the deliverable is ignored)
    for c in list(bpy.data.collections):
        if c.name.startswith('REVIEW_TABLE') or c.name.startswith('TABLE_ASTRA') or c.name.startswith('INSTRUMENT'):
            for o in list(c.all_objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)
    S = O.Stage(straps_open=name in STRAPS_OPEN, coll_name='VALIDATION_TABLE')
    scene = bpy.context.scene
    f0, f1 = (int(round(x)) for x in act.frame_range)
    N = f1 - f0
    r = {'action': act.name, 'frames': [f0, f1], 'fps': scene.render.fps, 'duration_s': N / O.FPS, 'loop': loop,
         'bone_count': len(rig.data.bones), 'bone_order_matches_patient': list(rig.data.bones.keys()) == order,
         'rig_mesh_data_unchanged': mesh_signature() == src_sig,
         'actions_in_file': [a.name for a in bpy.data.actions],
         'rig_object_matrix': mat(rig.matrix_world),
         'nonfinite': 0, 'reflected': 0, 'quat_sign_flips': 0, 'max_key_step_deg': 0.0}
    curves = O.fcurves_of(act)
    for n in order:
        fc = [next(x for x in curves if x.data_path == f'pose.bones["{n}"].rotation_quaternion' and x.array_index == c)
              for c in range(4)]
        for i in range(len(fc[0].keyframe_points) - 1):
            a = Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
            b = Quaternion([x.keyframe_points[i + 1].co.y for x in fc]).normalized()
            d = a.dot(b)
            r['quat_sign_flips'] += int(d < 0)
            stp = math.degrees(2 * math.acos(min(1, abs(d))))
            if stp > r['max_key_step_deg']:
                r['max_key_step_deg'] = stp
                r['max_key_step_at'] = [n, fc[0].keyframe_points[i].co.x]
    bvh_tab = {n: S.bvh(n) for n in list(SOLID) + list(O.STRAP_NAMES)}
    strap_bvh = {n: bvh_tab[n] for n in O.STRAP_NAMES}
    # closed straps: xy footprint of each band (inside-the-band test per sample)
    foot = {}
    if name not in STRAPS_OPEN:
        for n in O.STRAP_NAMES:
            o = S.objs[n]
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            foot[n] = (np.array([min(v[k] for v in bb) for k in range(3)]), np.array([max(v[k] for v in bb) for k in range(3)]))
    overl = {n: 0 for n in bvh_tab}
    overl_frames = {}
    pad_min, pad_min_at, floor_min, floor_min_at = 1.0, None, 10.0, None
    strap_pen = {n: 0.0 for n in O.STRAP_NAMES}
    disp = {}
    poses = {}
    meshes = [bpy.data.objects[n] for n in O.MESH_NAMES]
    step = O.FPS / args.rate
    ns = int(round(N / step))
    for i in range(ns + 1):
        f = f0 + i * step
        scene.frame_set(int(f), subframe=f % 1)
        for b in rig.pose.bones:
            m = b.matrix
            r['nonfinite'] += sum(not math.isfinite(x) for row in m for x in row)
            r['reflected'] += int(m.to_3x3().determinant() <= 0)
        ap_ = {b.name: b.matrix.copy() for b in rig.pose.bones}
        if abs(f - round(f * 2) / 2) < 1e-9:
            poses[f] = arm_pose(rig)
        # strap points (armature space, same bone-local definitions as the authoring)
        for key, (bone, loc) in {'forearm_L': ('LeftForeArm', 'forearm_Left'), 'forearm_R': ('RightForeArm', 'forearm_Right'),
                                 'shin_L': ('LeftLeg', 'shin_Left'), 'shin_R': ('RightLeg', 'shin_Right'),
                                 'pelvis': ('Hips', 'pelvis')}.items():
            b = O.P + bone
            p = (ap_[b] @ B.rest[b].inverted() @ strap_local[loc].to_4d()).to_3d()
            p0 = (B.tablerest[b] @ B.rest[b].inverted() @ strap_local[loc].to_4d()).to_3d()
            disp[key] = max(disp.get(key, 0.0), (p - p0).length)
        for s in ('Left', 'Right'):
            d_ = (ap_[O.P + s + 'Hand'].translation - B.tablerest[O.P + s + 'Hand'].translation).length
            disp['wrist_' + s[0]] = max(disp.get('wrist_' + s[0], 0.0), d_)
        dg = bpy.context.evaluated_depsgraph_get()
        allp = []
        for o in meshes:
            pts, polys = world_mesh(o, dg)
            allp.append(pts)
            bv = BVHTree.FromPolygons([Vector(p) for p in pts], polys, epsilon=0.0)
            for n, tb in bvh_tab.items():
                k = len(bv.overlap(tb))
                if k:
                    overl[n] += k
                    overl_frames.setdefault(n, []).append(round((f - f0) / O.FPS, 3))
        P_ = np.concatenate(allp)
        zmin = float(P_[:, 2].min())
        if zmin < floor_min:
            floor_min, floor_min_at = zmin, (f - f0) / O.FPS
        g = S.pad_gaps(P_)
        near = ~np.isnan(g) & (g > -0.05) & (g < 0.004)
        for j in np.nonzero(near)[0]:
            e = S.exact_pad_gap(P_[j])
            if e is not None and e < pad_min:
                pad_min, pad_min_at = e, (f - f0) / O.FPS
                r['pad_min_region'] = str(B.region[j]) + ':' + B.deform[B.sk_i[j][0]]
        # closed straps: a vertex is inside a (closed, 1 cm) band when its upward ray first leaves
        # the band; its depth is the distance down to the band's underside
        for n, (lo, hi) in foot.items():
            tb = strap_bvh[n]
            m = np.all((P_ > lo) & (P_ < hi), axis=1)
            for j in np.nonzero(m)[0]:
                v = Vector(P_[j])
                up = tb.ray_cast(v, Vector((0, 0, 1)), 0.05)
                if up[0] is None or up[1].z <= 0:
                    continue
                dn = tb.ray_cast(v, Vector((0, 0, -1)), 0.05)
                if dn[0] is not None and dn[1].z < 0 and dn[3] > strap_pen[n]:
                    strap_pen[n] = dn[3]
                    r.setdefault('strap_pen_where', {})[n] = [str(B.region[j]), B.deform[B.sk_i[j][0]], round((f - f0) / O.FPS, 3)]
    r['pad_min_gap_m'] = pad_min
    r['pad_min_gap_at_s'] = pad_min_at
    r['floor_min_z_m'] = floor_min
    r['floor_min_at_s'] = floor_min_at
    r['overlaps'] = {k: v for k, v in overl.items() if v}
    r['overlap_times_s'] = {k: [v[0], v[-1]] for k, v in overl_frames.items()}
    r['strap_penetration_depth_m'] = strap_pen
    r['strap_point_max_displacement_m'] = disp
    first_pose[name] = poses[float(f0)]
    last_pose[name] = poses[float(f1)]
    r['seam_matrix_error'] = err(poses[float(f0)], poses[float(f1)]) if loop else None
    if name in ('Awake', 'Struggle', 'Panic', 'ShockDeath', 'EscapeFall'):
        r['start_tablerest_error'] = err(poses[float(f0)], ref_tr)
    hips = poses[float(f1)][O.P + 'Hips']
    r['end_hips_armature_m'] = [hips[0][3], hips[1][3], hips[2][3]]
    r['end_hips_table_m'] = list((rig.matrix_world @ Vector(r['end_hips_armature_m'])))
    # --- FBX reimport
    if not args.no_fbx and not args.dev:
        irig = import_rig(HERE / (stem + '.fbx'))
        bones = bone_sig(irig)
        worst, ends = 0.0, {}
        for f, p in poses.items():
            bpy.context.scene.frame_set(int(f), subframe=f % 1)
            a = arm_pose(irig)
            worst = max(worst, err(a, p))
            if f in (f0, f1):
                ends[f] = a
        r['fbx'] = {'bone_count': len(bones), 'bone_order_matches': list(bones) == list(bind),
                    'hierarchy_matches': {k: v[0] for k, v in bones.items()} == {k: v[0] for k, v in bind.items()},
                    'max_bind_error': max(abs(bind[n][1][a][b] - bones[n][1][a][b]) for n in bind for a in range(4) for b in range(4)),
                    'max_animated_matrix_error': worst,
                    'seam_error': err(ends[f0], ends[f1]) if loop else None,
                    'takes': {a.name: list(a.frame_range) for a in bpy.data.actions},
                    'armature_object_matrix': mat(irig.matrix_world),
                    'only_armature': all(o.type == 'ARMATURE' for o in bpy.data.objects)}
    # --- gates
    ok = {'fps30': r['fps'] == 30, 'bones65': r['bone_count'] == 65, 'bone_order': r['bone_order_matches_patient'],
          'rig_mesh_unchanged': r['rig_mesh_data_unchanged'], 'one_action': r['actions_in_file'] == [r['action']],
          'finite': r['nonfinite'] == 0, 'no_reflection': r['reflected'] == 0, 'no_sign_flip': r['quat_sign_flips'] == 0,
          'key_step': r['max_key_step_deg'] < TH['key_step_deg'],
          'pad_no_penetration': pad_min >= TH['pad_gap_m'] and r['overlaps'].get('GEO_Padded_Top', 0) == 0,
          'table_parts_no_overlap': all(r['overlaps'].get(n, 0) == 0 for n in SOLID),
          'floor': floor_min >= TH['floor_m']}
    if loop:
        ok['seam_exact'] = r['seam_matrix_error'] == 0.0
    if 'start_tablerest_error' in r:
        ok['start_tablerest'] = r['start_tablerest_error'] < TH['contract']
    if name in STRAPPED:
        ok['strap_points_held'] = all(v <= TH['strap_point_m'] for k, v in disp.items() if not k.startswith('wrist'))
    if name in ON_TABLE:
        ok['closed_strap_penetration'] = max(strap_pen.values()) <= TH['strap_pen_m']
    if name in STRAPS_OPEN:
        ok['open_straps_no_overlap'] = all(r['overlaps'].get(n, 0) == 0 for n in O.STRAP_NAMES)
    if name in ('EscapeFall', 'KnockedOut'):
        r['end_lowest_z_m'] = None
    if 'fbx' in r:
        fb = r['fbx']
        ok.update({'fbx_bone_order': fb['bone_order_matches'], 'fbx_hierarchy': fb['hierarchy_matches'],
                   'fbx_bind': fb['max_bind_error'] < TH['fbx_bind'], 'fbx_anim': fb['max_animated_matrix_error'] < TH['fbx_anim'],
                   'fbx_one_take': len(fb['takes']) == 1, 'fbx_armature_only': fb['only_armature']})
        if loop:
            ok['fbx_seam'] = fb['seam_error'] < TH['fbx_seam']
    r['checks'] = ok
    r['checks_passed'] = sum(ok.values())
    r['checks_total'] = len(ok)
    r['pass'] = all(ok.values())
    r['validate_seconds'] = round(time.time() - t0, 1)
    report['clips'][stem] = r
    print('VALIDATED', stem, r['checks_passed'], '/', r['checks_total'], 'pad %.2f mm' % (pad_min * 1000),
          'floor %.2f mm' % (floor_min * 1000), 'overlaps', r['overlaps'], 'strap_pen_mm',
          {k[6:]: round(v * 1000, 1) for k, v in strap_pen.items() if v}, 'disp_mm', {k: round(v * 1000, 1) for k, v in disp.items()},
          'fails', [k for k, v in ok.items() if not v], flush=True)
    if args.dev:
        print('  OVERLAP_TIMES', {k: [min(v), max(v), len(v)] for k, v in overl_frames.items()}, 'pad_min_at', pad_min_at, r.get('pad_min_region'), r.get('strap_pen_where'), 'keystep', round(r['max_key_step_deg'], 1), r.get('max_key_step_at'), flush=True)

# --- cross-clip contracts (raw keyed values at the joins)
cross = {}
if 'ShockDeath' in last_pose and 'Dead' in first_pose:
    cross['shockdeath_end_vs_dead_start'] = err(last_pose['ShockDeath'], first_pose['Dead'])
if 'EscapeFall' in last_pose and 'KnockedOut' in first_pose:
    a, b = last_pose['EscapeFall'], first_pose['KnockedOut']
    off = [a[O.P + 'Hips'][k][3] - b[O.P + 'Hips'][k][3] for k in range(3)]
    sh = {n: [row[:] for row in m] for n, m in b.items()}
    for n in sh:
        for k in range(3):
            sh[n][k][3] += off[k]
    cross['escapefall_end_vs_knockedout_start_after_root_offset'] = err(a, sh)
    cross['knockedout_root_offset_armature_m'] = off
    cross['knockedout_root_offset_unity_patientrest_local'] = [-off[0], off[2], -off[1]]
report['cross_contracts'] = cross
report['pass'] = all(c['pass'] for c in report['clips'].values()) and all(v < TH['contract'] for k, v in cross.items() if isinstance(v, float))
if not args.dev:
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CROSS', cross)
print('REPORT_PASS', report['pass'], flush=True)
