"""Build Walk v03 for the Sausage Buddy (Buddy_Rig_Mixamo65) and save the editable blend.

Blender 5.2 background (from any folder):
  blender -b --factory-startup --python build_walk_v03.py -- [--source blend|json] [--out PATH] [--report PATH]

--source blend (default) opens SAUSAGE_BUDDY_A_v04.blend read-only; the saved blend keeps the original
  A v04 Body, Face and Outfit meshes for review renders.
--source json needs no Git LFS file: it rebuilds the armature from rig_Buddy_Mixamo65.json and reads the
  shoe soles from shoe_soles_v04.json; the saved blend holds the armature and the action only.
Both sources give a bit-identical action (see action_digest in the report).
--out defaults to Walk_v03.blend next to this script. Existing files are never overwritten.
Motion design: walk_v03_motion.py. No downloaded motion, Mixamo take, generator or paid service is used.
"""
from pathlib import Path
import sys
import json
import hashlib
import argparse
sys.dont_write_bytecode = True
import bpy

HERE = Path(__file__).resolve().parent
CHAR = HERE.parent.parent
sys.path.insert(0, str(CHAR))
sys.path.insert(0, str(HERE))
import buddy_anim as A          # noqa: E402  (read-only helpers of the character build)
import buddy_rig as RG          # noqa: E402
import walk_v03_motion as W     # noqa: E402
import rebuild_rig_from_json as RR  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--source', choices=('blend', 'json'), default='blend')
ap.add_argument('--out', default=str(HERE / 'Walk_v03.blend'))
ap.add_argument('--report', default='')
args = ap.parse_args(argv)
OUT = Path(args.out)
assert not OUT.exists(), f'Refusing to overwrite {OUT}'

SUB = 2                       # keys per frame: half-frame keys keep the rolling contacts exact


def rigid_parts(verts):
    """verts: [(co, {bone: weight})]. Heel part = only Foot, toe part = only ToeBase (z < 0.08)."""
    shoe = {}
    for side in ('Left', 'Right'):
        heel, toe = [], []
        for co, w in verts[side]:
            if co[2] > 0.08:
                continue
            total = sum(w.values())
            if total and w.get(W.P + side + 'Foot', 0.0) >= 0.999 * total:
                heel.append(tuple(co))
            elif total and w.get(W.P + side + 'ToeBase', 0.0) >= 0.999 * total:
                toe.append(tuple(co))
        shoe[side] = (heel, toe)
    return shoe


if args.source == 'blend':
    bpy.ops.wm.open_mainfile(filepath=str(CHAR / 'SAUSAGE_BUDDY_A_v04.blend'))
    scene = bpy.context.scene
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    meshes = [bpy.data.objects[n] for n in ('Body', 'Face', 'Outfit')]
    rig.animation_data_clear()
    for o in meshes:
        if o.data.shape_keys:
            o.data.shape_keys.animation_data_clear()
            for k in o.data.shape_keys.key_blocks:
                k.value = 0.0
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    outfit = bpy.data.objects['Outfit']
    names = {g.index: g.name for g in outfit.vertex_groups}
    verts = {side: [(tuple(outfit.matrix_world @ v.co), {names[g.group]: g.weight for g in v.groups if g.weight > 0.0})
                     for v in outfit.data.vertices] for side in ('Left', 'Right')}
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rig = RR.build(HERE / 'rig_Buddy_Mixamo65.json')
    soles = json.loads((HERE / 'shoe_soles_v04.json').read_text())['A']['soles']
    verts = {side: [(tuple(v['co']), v['w']) for v in soles[side]] for side in ('Left', 'Right')}
shoe = rigid_parts(verts)
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
    pb.rotation_mode = 'QUATERNION'
rig.data.pose_position = 'POSE'
scene.render.fps = W.FPS
scene.frame_start, scene.frame_end = 1, W.N + 1

walk = W.Walk(rig, rest, shoe, RG.ordered, A.pose_from_joints, A.rotate_subtree)

frames, infos = {}, []
for i in range(W.N * SUB):
    f = 1 + i / SUB
    desired, info = walk.pose((f - 1) / W.N)
    frames[f] = desired
    info['frame'] = f
    infos.append(info)
frames[W.N + 1] = {n: m.copy() for n, m in frames[1].items()}   # exact loop seam
action = RG.key_frames(rig, rest, frames, 'Walk')
action['nominal_ground_speed_m_s'] = W.SPEED
action['loop_duration_s'] = W.CYCLE_S
action['frames_per_cycle'] = W.N
action['stride_m'] = W.TRAVEL
action['step_m'] = W.TRAVEL / 2
action['stance_fraction'] = W.T_OFF
action['heel_strike_phase_left_right'] = [0.0, 0.5]
action['authoring'] = ('Walk v03: original key-curve cartoon walk on the Buddy v04 skeleton; heel-toe roll '
                       'over the real sole hull, hinge IK, overlapping spine/head/arms; no source motion reused')
rig.animation_data.action = action

# Self-check: the keyed action must reproduce every designed matrix (non-root bones are keyed
# by rotation only, so a joint that drifted from its parent would show up here).
key_error = 0.0
for f in range(1, W.N + 2):
    scene.frame_set(f)
    for name, m in frames[f].items():
        pm = rig.pose.bones[name].matrix
        key_error = max(key_error, max(abs(pm[r][c] - m[r][c]) for r in range(4) for c in range(4)))
print('KEYED_MATRIX_MAX_ERROR', key_error, flush=True)
assert key_error < 1e-4, key_error

# Digest of every key (exact float values) to prove both sources and reruns give the same action.
digest = hashlib.sha256()
for fc in sorted(RG.fcurves_of(action), key=lambda c: (c.data_path, c.array_index)):
    digest.update(f'{fc.data_path}[{fc.array_index}]'.encode())
    for k in fc.keyframe_points:
        digest.update(repr((float(k.co[0]), float(k.co[1]))).encode())
action['key_digest_sha256'] = digest.hexdigest()
print('ACTION_DIGEST', digest.hexdigest(), flush=True)

# Design diagnostics (rigid shoe points; the validator measures the skinned meshes).
def rigid_low(foot, Mf, Mt):
    heel, toe = shoe[foot.side]
    return min(min((Mf @ W.Vector(p)).z for p in heel), min((Mt @ W.Vector(p)).z for p in toe))

samples = []
for i in range(W.N * 8):
    t = i / (W.N * 8)
    row = {'t': t}
    for side, offset in (('Left', 0.0), ('Right', 0.5)):
        foot = walk.feet[side]
        Mf, Mt, phase = foot.at(t - offset)
        row[side] = {'phase': phase, 'low': rigid_low(foot, Mf, Mt)}
    samples.append(row)
swing_low = {s: min((r[s]['low'], round(((r['t'] - (0.0 if s == 'Left' else 0.5)) % 1.0 - W.T_OFF) / (1 - W.T_OFF), 3))
                    for r in samples if r[s]['phase'] == 'swing') for s in ('Left', 'Right')}   # (low m, swing fraction)
stance_low = {s: (min(r[s]['low'] for r in samples if r[s]['phase'] != 'swing'),
                  max(r[s]['low'] for r in samples if r[s]['phase'] != 'swing')) for s in ('Left', 'Right')}
report = {
    'source': args.source,
    'action_digest': digest.hexdigest(),
    'keyed_matrix_max_error': key_error,
    'y0': walk.y0,
    'heel_chain': walk.feet['Left'].heel_chain,
    'toe_chain': walk.feet['Left'].toe_chain,
    'max_reach': {s: max(i[s]['reach'] for i in infos) for s in ('Left', 'Right')},
    'knee_range_deg': {s: (min(i[s]['knee'] for i in infos), max(i[s]['knee'] for i in infos)) for s in ('Left', 'Right')},
    'rigid_stance_low_m': stance_low,
    'rigid_swing_low_m': swing_low,
    'per_frame': [{'frame': i['frame'], 'root': i['root'],
                   'L': (i['Left']['phase'], round(i['Left']['reach'], 4), round(i['Left']['knee'], 1)),
                   'R': (i['Right']['phase'], round(i['Right']['reach'], 4), round(i['Right']['knee'], 1))}
                  for i in infos],
}
print('DESIGN', json.dumps({k: v for k, v in report.items() if k != 'per_frame'}, indent=1), flush=True)
for row in report['per_frame']:
    print('  f%5.1f root z %+.4f x %+.4f  L %-5s reach %.3f knee %5.1f  R %-5s reach %.3f knee %5.1f' % (
        row['frame'], row['root'][2], row['root'][0], row['L'][0], row['L'][1], row['L'][2],
        row['R'][0], row['R'][1], row['R'][2]))
if args.report:
    Path(args.report).write_text(json.dumps(report, indent=1))

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('BLEND_READY', OUT, flush=True)
