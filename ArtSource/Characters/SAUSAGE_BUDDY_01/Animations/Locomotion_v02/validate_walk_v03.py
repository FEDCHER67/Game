"""Validate a Walk revision of this folder (default v03) and write validation_<rev>.json.

Blender 5.2 background:
  blender -b --factory-startup --python validate_walk_v03.py -- [--rev v03] [--source blend|json] [--out PATH]

--source blend (default) also needs the Git LFS files SAUSAGE_BUDDY_A/B_v04.blend/.fbx and
  Locomotion_v01/Walk_v02.fbx: skinned meshes are evaluated by Blender itself.
--source json needs only this folder: shoe contact is skinned in Python (linear blend skinning,
  normalised deform weights, as Blender's armature modifier) from shoe_soles_v04.json, and the FBX
  skeleton is compared with rig_Buddy_Mixamo65.json. In blend mode the same Python skinning is run
  as a cross-check against Blender's meshes.

Checks
- Action: one take 'Walk', frames 1..N+1, finite keys, unit quaternions, no sign flips, rotation step
  per half frame, exact loop seam (frame N+1 == frame 1) and the velocity jump across the seam.
- Shoe contact for A and B at 120 Hz over two cycles:
  lowest vertex (penetration); sole height during the designed stance windows (support error);
  support slide = ground-frame drift of sole vertices touching the floor (<= 1 mm) while inside a
  stance window; touchdown/lift-off skim = the same drift for touching runs in any phase, i.e. also
  the heel arriving or the toe leaving while still within 1 mm of the floor.
- FBX re-import: 65 bones, names/parents/order like Walk_v02.fbx (or the rig JSON), bind matrices,
  one take, animated world matrices vs the blend.
"""
from pathlib import Path
import sys
import json
import math
import hashlib
import argparse
sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
CHAR = HERE.parent.parent
sys.path.insert(0, str(CHAR))
sys.path.insert(0, str(HERE))
import buddy_rig as RG          # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--rev', default='v03')
ap.add_argument('--source', choices=('blend', 'json'), default='blend')
ap.add_argument('--out', default='')
ap.add_argument('--v02-fbx', default=str(CHAR / 'Animations' / 'Locomotion_v01' / 'Walk_v02.fbx'))
args = ap.parse_args(argv)
REV = args.rev
OUT = Path(args.out) if args.out else HERE / f'validation_{REV}.json'
assert not OUT.exists(), f'Refusing to overwrite {OUT}'
P = 'mixamorig:'
CONTACT = 0.001                 # a sole vertex within 1 mm of the floor counts as touching
FBX_POSE_TOL = 2e-3             # FBX stores Euler angles; ~0.1 deg conversion noise is acceptable
rig_doc = json.loads((HERE / 'rig_Buddy_Mixamo65.json').read_text())
soles_doc = json.loads((HERE / 'shoe_soles_v04.json').read_text())
DEFORM = {b['name'] for b in rig_doc['bones'] if b['use_deform']}
report = {'revision': REV, 'source': args.source}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mat(m):
    return [[float(x) for x in row] for row in m]


def real(path):
    """True for a real file; False if absent or only a Git LFS pointer stub (LFS not fetched)."""
    path = Path(path)
    if not path.is_file():
        return False
    if path.stat().st_size < 1024 and path.read_bytes().startswith(b'version https://git-lfs'):
        return False
    return True


present = all(real(CHAR / n) for n in rig_doc['source_sha256'])
report['source_sha256_unchanged'] = (all(sha(CHAR / n) == h for n, h in rig_doc['source_sha256'].items())
                                     if present else 'skipped: LFS sources absent')

# ------------------------------------------------------------------ action and curves
bpy.ops.wm.open_mainfile(filepath=str(HERE / f'Walk_{REV}.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
act = rig.animation_data.action
N = int(act['frames_per_cycle'])
SPEED = float(act['nominal_ground_speed_m_s'])
STANCE = float(act['stance_fraction'])
FPS = scene.render.fps
fcs = RG.fcurves_of(act)
keys = {(fc.data_path, fc.array_index): [(k.co[0], k.co[1]) for k in fc.keyframe_points] for fc in fcs}
finite = all(math.isfinite(v) for ks in keys.values() for _, v in ks)
seam = max(abs(dict(ks)[1.0] - dict(ks)[float(N + 1)]) for ks in keys.values())
seam_jump, interior_jump = 0.0, 0.0
for ks in keys.values():
    v = [val for _, val in ks]                      # half-frame keys, last == first
    d = [b - a for a, b in zip(v, v[1:])]
    seam_jump = max(seam_jump, abs(d[0] - d[-1]))   # velocity change across the loop seam
    interior_jump = max(interior_jump, max(abs(b - a) for a, b in zip(d, d[1:])))
quat_flip, quat_norm, quat_step, quat_step_bone = 0, 0.0, 0.0, ''
for pb in rig.pose.bones:
    path = f'pose.bones["{pb.name}"].rotation_quaternion'
    q = list(zip(*[[val for _, val in keys[(path, i)]] for i in range(4)]))
    for a, b in zip(q, q[1:]):
        dot = sum(x * y for x, y in zip(a, b))
        quat_flip += dot < 0
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        step = math.degrees(2 * math.acos(min(1.0, abs(dot) / (na * nb))))
        if step > quat_step:
            quat_step, quat_step_bone = step, pb.name
        quat_norm = max(quat_norm, abs(na - 1.0))
report['action'] = {
    'name': act.name, 'actions_in_blend': [a.name for a in bpy.data.actions],
    'frame_range': list(act.frame_range), 'fps': FPS, 'frames_per_cycle': N, 'loop_s': N / FPS,
    'nominal_speed_m_s': SPEED, 'stride_m': SPEED * N / FPS, 'step_m': SPEED * N / FPS / 2,
    'stance_fraction_per_leg': STANCE, 'double_support_fraction_total': 2 * (STANCE - 0.5),
    'fcurves': len(fcs), 'keys_per_curve': len(next(iter(keys.values()))),
    'all_keys_finite': finite, 'quaternion_sign_flips': quat_flip, 'max_quaternion_norm_error': quat_norm,
    'max_rotation_step_per_half_frame_deg': quat_step, 'max_rotation_step_bone': quat_step_bone,
    'seam_max_key_difference': seam,
    'seam_velocity_jump_max': seam_jump, 'interior_velocity_change_max': interior_jump,
    'key_digest_sha256': act.get('key_digest_sha256', ''),
}

source_pose = {}
for f in range(1, N + 2):
    scene.frame_set(f)
    source_pose[f] = {pb.name: mat(rig.matrix_world @ pb.matrix) for pb in rig.pose.bones}
hips = [source_pose[f][P + 'Hips'] for f in range(1, N + 1)]
report['hips_motion_m'] = {
    'lateral_sway_range': max(m[0][3] for m in hips) - min(m[0][3] for m in hips),
    'forward_range': max(m[1][3] for m in hips) - min(m[1][3] for m in hips),
    'vertical_range': max(m[2][3] for m in hips) - min(m[2][3] for m in hips),
    'mean_xy': [sum(m[0][3] for m in hips) / N, sum(m[1][3] for m in hips) / N],
    'height_min_max': [min(m[2][3] for m in hips), max(m[2][3] for m in hips)],
}


# ------------------------------------------------------------------ shoe contact
def sample_frames():
    for j in range(4 * N):
        f = 1 + j / 4
        scene.frame_set(int(f), subframe=f - int(f))
        yield j


def lbs_samples(variant, rig):
    """Python skinning of the shoe vertices: {j: (lowest z, {side: [sole points]})}."""
    rest_inv = {b.name: b.matrix_local.inverted() for b in rig.data.bones}
    soles = soles_doc[variant]['soles']
    out = {}
    for j in sample_frames():
        deform = {pb.name: rig.matrix_world @ pb.matrix @ rest_inv[pb.name] for pb in rig.pose.bones}
        low, feet = 1e9, {}
        for side in ('Left', 'Right'):
            pts = []
            for v in soles[side]:
                w = {n: x for n, x in v['w'].items() if n in DEFORM}
                total = sum(w.values())
                co = Vector(v['co'])
                p = sum((deform[n] @ co * x for n, x in w.items()), Vector()) / total
                low = min(low, p.z)
                if v['co'][2] < 0.03:
                    pts.append(tuple(p))
            feet[side] = pts
        out[j] = (low, feet)
    return out


def mesh_samples(variant, objects, outfit):
    """Blender-evaluated meshes: lowest vertex of all meshes and the sole points of the outfit."""
    soles = soles_doc[variant]['soles']
    idx = {s: [v['i'] for v in soles[s] if v['co'][2] < 0.03] for s in ('Left', 'Right')}
    out = {}
    for j in sample_frames():
        dg = bpy.context.evaluated_depsgraph_get()
        low, feet = 1e9, {}
        for o in objects:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            mw = o.matrix_world
            low = min(low, min((mw @ v.co).z for v in me.vertices))
            if o == outfit:
                feet = {s: [tuple(mw @ me.vertices[i].co) for i in idx[s]] for s in idx}
            ev.to_mesh_clear()
        out[j] = (low, feet)
    return out


def metrics(cache):
    res = {'lowest_vertex_m': min(c[0] for c in cache.values())}
    height, support, skim = {}, {}, {}
    for side, offset in (('Left', 0.0), ('Right', 0.5)):
        errs, drift_stance, drift_any, runs_stance, runs_any = [], 0.0, 0.0, {}, {}
        for j in range(8 * N + 1):                 # two cycles: every stance is seen whole
            q = (j / (4 * N) - offset) % 1.0
            in_stance = q <= STANCE + 1e-9
            pts = cache[j % (4 * N)][1][side]
            if in_stance:
                errs.append(abs(min(p[2] for p in pts)))
            time = j / (4 * FPS)
            for i, p in enumerate(pts):
                if p[2] <= CONTACT:
                    g = (p[0], p[1] - SPEED * time)    # ground frame: planted points stay put
                    start = runs_any.setdefault(i, g)
                    drift_any = max(drift_any, math.hypot(g[0] - start[0], g[1] - start[1]))
                    if in_stance:
                        start = runs_stance.setdefault(i, g)
                        drift_stance = max(drift_stance, math.hypot(g[0] - start[0], g[1] - start[1]))
                    else:
                        runs_stance.pop(i, None)
                else:
                    runs_any.pop(i, None)
                    runs_stance.pop(i, None)
        height[side], support[side], skim[side] = max(errs), drift_stance, drift_any
    res['stance_sole_height_error_m'] = height
    res['support_slide_m'] = support
    res['touchdown_liftoff_skim_m'] = skim
    return res


def append_walk():
    with bpy.data.libraries.load(str(HERE / f'Walk_{REV}.blend'), link=False) as (src, dst):
        dst.actions = ['Walk']
    r = bpy.data.objects['Buddy_Rig_Mixamo65']
    walk = next(a for a in bpy.data.actions if a.name.startswith('Walk') and a.get('frames_per_cycle'))
    r.animation_data_create()
    r.animation_data.action = walk
    if hasattr(r.animation_data, 'action_slot') and r.animation_data.action_slot is None and len(walk.slots):
        r.animation_data.action_slot = walk.slots[0]
    return r


if args.source == 'blend':
    meshes_a = [bpy.data.objects[n] for n in ('Body', 'Face', 'Outfit')]
    report['contact_A'] = metrics(mesh_samples('A', meshes_a, bpy.data.objects['Outfit']))
    report['contact_A_python_skinning'] = metrics(lbs_samples('A', rig))
    bpy.ops.wm.open_mainfile(filepath=str(CHAR / 'SAUSAGE_BUDDY_B_v04.blend'))
    scene = bpy.context.scene
    rig_b = append_walk()
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.shape_keys:
            if o.data.shape_keys.animation_data:
                o.data.shape_keys.animation_data_clear()
            for k in o.data.shape_keys.key_blocks:
                k.value = 0.0
    meshes_b = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig_b]
    report['contact_B'] = metrics(mesh_samples('B', meshes_b, bpy.data.objects['Outfit']))
else:
    report['contact_A'] = metrics(lbs_samples('A', rig))
    report['contact_B'] = metrics(lbs_samples('B', rig))


# ------------------------------------------------------------------ FBX re-import
def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    bpy.ops.import_scene.fbx(filepath=str(path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def bones_of(r):
    return {b.name: (b.parent.name if b.parent else None, mat(b.matrix_local)) for b in r.data.bones}


def max_diff(a, b):
    return max(abs(a[n][1][r][c] - b[n][1][r][c]) for n in a for r in range(4) for c in range(4))


json_bones = {b['name']: (b['parent'], b['matrix_local']) for b in rig_doc['bones']}
fbx = {}
if real(args.v02_fbx):
    v02_bones = bones_of(import_rig(Path(args.v02_fbx)))
    fbx['reference'] = 'Walk_v02.fbx'
else:
    v02_bones = None
    fbx['reference'] = 'rig_Buddy_Mixamo65.json (Walk_v02.fbx absent)'
if real(CHAR / 'SAUSAGE_BUDDY_A_v04.fbx'):
    char_bones = bones_of(import_rig(CHAR / 'SAUSAGE_BUDDY_A_v04.fbx'))
    fbx['max_bind_matrix_error_vs_original_character_fbx'] = max_diff(char_bones, bones_of(import_rig(HERE / f'Walk_{REV}.fbx')))
new = import_rig(HERE / f'Walk_{REV}.fbx')
new_bones = bones_of(new)
reference = v02_bones if v02_bones is not None else json_bones
pose_err, pose_bone = 0.0, ''
for f, ref_pose in source_pose.items():
    bpy.context.scene.frame_set(f)
    for b in new.pose.bones:
        m = new.matrix_world @ b.matrix
        e = max(abs(m[r][c] - ref_pose[b.name][r][c]) for r in range(4) for c in range(4))
        if e > pose_err:
            pose_err, pose_bone = e, f'{b.name} @ frame {f}'
fbx.update({
    'armature': new.name, 'bones': len(new_bones),
    'root_bones': [n for n, v in new_bones.items() if v[0] is None],
    'actions': {a.name: list(a.frame_range) for a in bpy.data.actions},
    'only_armature_objects': all(o.type == 'ARMATURE' for o in bpy.data.objects),
    'bone_names_and_parents_identical_to_reference': {n: v[0] for n, v in reference.items()} == {n: v[0] for n, v in new_bones.items()},
    'bone_order_identical_to_reference': list(reference) == list(new_bones) if v02_bones is not None else 'n/a for JSON',
    'max_bind_matrix_error_vs_reference': max_diff(reference, new_bones),
    'max_world_pose_matrix_error_vs_blend': pose_err, 'worst_pose_bone': pose_bone,
})
report['fbx_reimport'] = fbx

contacts = [report['contact_A'], report['contact_B']]
checks = {
    'sources_unchanged': report['source_sha256_unchanged'] if present else 'skipped',
    'single_take_walk': report['action']['actions_in_blend'] == ['Walk'] and len(fbx['actions']) == 1,
    'finite_keys': finite,
    'no_quaternion_flips': quat_flip == 0,
    'exact_loop_seam': seam == 0.0,
    'seam_velocity_jump_le_interior': seam_jump <= interior_jump + 1e-9,
    'no_penetration_le_1mm': min(c['lowest_vertex_m'] for c in contacts) >= -0.001,
    'support_sole_height_error_le_1mm': max(max(c['stance_sole_height_error_m'].values()) for c in contacts) <= 0.001,
    'support_slide_le_1mm': max(max(c['support_slide_m'].values()) for c in contacts) <= 0.001,
    'touchdown_liftoff_skim_le_1mm': max(max(c['touchdown_liftoff_skim_m'].values()) for c in contacts) <= 0.001,
    'fbx_65_bones_same_as_reference': fbx['bone_names_and_parents_identical_to_reference'] and fbx['bones'] == 65,
    'fbx_pose_matches_blend': pose_err < FBX_POSE_TOL,
}
report['checks'] = checks
report['all_pass'] = all(v is True or v == 'skipped' for v in checks.values())
OUT.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
print('VALIDATION', 'PASS' if report['all_pass'] else 'FAIL', OUT, flush=True)
