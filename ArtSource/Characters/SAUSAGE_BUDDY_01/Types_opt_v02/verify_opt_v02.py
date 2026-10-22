"""Checks the opt_v02 derivatives (build_types_opt_v02.py) against the baseline (opt_v01, or the source for POOL_SOURCE), adapted from verify_opt_v01_w86.py.
Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v02/verify_opt_v02.py -- [--types A,B] [--dir DIR]

1. .blend vs opt_v01 .blend:
   - same objects (plus <mesh>_LOD1 / _LOD2 for every skinned mesh, in collections LOD1 / LOD2), same rig bones (names,
     parents, rest matrices), same actions;
   - per skinned mesh and per LOD level: the opt_v01 vertex-group names, material slots (names, order) and the same used
     materials, shape keys, UV layers (none) and armature modifier; no unweighted vertex (deform bones, weight > 1e-4),
     at most 4 influences;
   - LOD0 unchanged objects identical; changed ones on the opt_v01 surface within 1 mm at rest (removed hidden faces
     aside); Face: every LOD0
     vertex is an opt_v01 vertex (same basis position) with the same offsets in every shape key;
   - combined rest bounds of LOD0 within 0.1 % of opt_v01, of LOD1/LOD2 within 2 %.
2. .fbx vs opt_v01 .fbx (both imported into an empty scene): same armature (bone names, parents, rest matrices), meshes
   = {<mesh>_LOD0, _LOD1, _LOD2} for every opt_v01 mesh with its transform, material slots and shape keys; every vertex
   weighted, at most 4 influences; LOD0 bounds within 1 mm of opt_v01. Prints triangles per level.
"""
import argparse, sys
from pathlib import Path
import bpy
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from build_types_opt_v02 import POOL, POOL_SOURCE, TAG, RIG, baseline   # noqa: E402

LEVELS = (0, 1, 2)


def base_name(n):
    return n.rsplit('_LOD', 1)[0] if '_LOD' in n else n


def level_of(n):
    return int(n.rsplit('_LOD', 1)[1]) if '_LOD' in n else 0


def mesh_info(o, deform):
    me = o.data
    names = [g.name for g in o.vertex_groups]
    infl = [len([g for g in v.groups if g.weight > 1e-4 and names[g.group] in deform]) for v in me.vertices]
    return {'groups': names, 'mats': [m.name if m else None for m in me.materials],
            'used': sorted({p.material_index for p in me.polygons}),
            'keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
            'arm': [m.object.name if m.object else None for m in o.modifiers if m.type == 'ARMATURE'],
            'uv': [u.name for u in me.uv_layers], 'tris': sum(len(p.vertices) - 2 for p in me.polygons),
            'unweighted': infl.count(0), 'max_infl': max(infl) if infl else 0}


def surface(o):
    me = o.data
    me.calc_loop_triangles()
    co = [o.matrix_world @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    return co, tris


def blend_state(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects[RIG]
    deform = {b.name for b in rig.data.bones if b.use_deform}
    st = {'objects': sorted(o.name for o in bpy.data.objects),
          'bones': {b.name: (b.parent.name if b.parent else None, b.matrix_local.copy()) for b in rig.data.bones},
          'actions': sorted(a.name for a in bpy.data.actions), 'meshes': {}, 'surf': {}, 'face': None,
          'collections': {o.name: [c.name for c in o.users_collection] for o in bpy.data.objects}}
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent == rig:
            st['meshes'][o.name] = mesh_info(o, deform)
            st['surf'][o.name] = surface(o)
            if o.name == 'Face' and o.data.shape_keys:
                st['face'] = [[d.co.copy() for d in k.data] for k in o.data.shape_keys.key_blocks]
    return st


def bounds(st, level):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for n, (co, _t) in st['surf'].items():
        if level_of(n) != level:
            continue
        for p in co:
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi


def max_dev(a, b):
    (ca, ta), (cb, tb) = a, b
    ba, bb = BVHTree.FromPolygons(ca, ta), BVHTree.FromPolygons(cb, tb)
    d1 = max(((bb.find_nearest(p)[0] - p).length for p in ca), default=0.0)
    d2 = max(((ba.find_nearest(p)[0] - p).length for p in cb), default=0.0)
    return max(d1, d2)


def one_way(a, b):
    """Largest distance from the vertices and triangle centres of a to the surface of b (removed hidden faces of b
    do not count; everything a has must lie on b)."""
    (ca, ta), (cb, tb) = a, b
    bb = BVHTree.FromPolygons(cb, tb)
    pts = ca + [(ca[i] + ca[j] + ca[k]) / 3 for i, j, k in ta]
    return max(((bb.find_nearest(p)[0] - p).length for p in pts), default=0.0)


def close(m1, m2, eps=1e-6):
    return all(abs(a - b) <= eps for r1, r2 in zip(m1, m2) for a, b in zip(r1, r2))


def check_blend(tid, rev, d):
    a = blend_state(baseline(tid, rev)[0])
    b = blend_state(d / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.blend')
    errs = []
    want = set(a['objects']) | {f'{n}_LOD{lv}' for n in a['meshes'] for lv in (1, 2)}
    if set(b['objects']) != want:
        errs.append(f"objects differ {sorted(want ^ set(b['objects']))}")
    if list(a['bones']) != list(b['bones']):
        errs.append('bone names/order differ')
    else:
        for n, (par, m) in a['bones'].items():
            if b['bones'][n][0] != par or not close(m, b['bones'][n][1]):
                errs.append(f'bone {n} differs'); break
    if a['actions'] != b['actions']:
        errs.append('actions differ')
    for n, ma in a['meshes'].items():
        for lv in LEVELS:
            nb = n if lv == 0 else f'{n}_LOD{lv}'
            mb = b['meshes'].get(nb)
            if mb is None:
                errs.append(f'{nb} missing'); continue
            if lv and b['collections'].get(nb) != [f'LOD{lv}']:
                errs.append(f'{nb} not in collection LOD{lv}')
            for k in ('groups', 'mats', 'used', 'keys', 'arm', 'uv'):
                if ma[k] != mb[k]:
                    errs.append(f'{nb}: {k} differ')
            if mb['unweighted'] or mb['max_infl'] > 4:
                errs.append(f"{nb}: weights (unweighted {mb['unweighted']}, max {mb['max_infl']})")
        if ma['tris'] == b['meshes'][n]['tris']:
            if max_dev(a['surf'][n], b['surf'][n]) > 1e-6:
                errs.append(f'{n}: same triangle count but moved')
        elif n != 'Face':
            dv = one_way(b['surf'][n], a['surf'][n])
            if dv > 0.001:
                errs.append(f'{n}: LOD0 off the opt_v01 surface by {dv * 1000:.2f} mm')
    # Face: every LOD0 vertex is an opt_v01 vertex with the same shape-key offsets
    if a['face'] is not None and b['face'] is not None:
        kd = kdtree.KDTree(len(a['face'][0]))
        for i, p in enumerate(a['face'][0]):
            kd.insert(p, i)
        kd.balance()
        worst = 0.0
        for j, p in enumerate(b['face'][0]):
            _co, i, dist = kd.find(p)
            worst = max(worst, dist)
            for ka, kb in zip(a['face'][1:], b['face'][1:]):
                worst = max(worst, ((kb[j] - b['face'][0][j]) - (ka[i] - a['face'][0][i])).length)
        if worst > 1e-6:
            errs.append(f'Face vertices / shape keys differ by {worst * 1000:.4f} mm')
    lo_a, hi_a = bounds(a, 0)
    size = max(hi_a - lo_a)
    rel = {}
    for lv in LEVELS:
        lo_b, hi_b = bounds(b, lv)
        rel[lv] = max(max(abs(x - y) for x, y in zip(lo_a, lo_b)), max(abs(x - y) for x, y in zip(hi_a, hi_b))) / size
    if rel[0] > 0.001 or rel[1] > 0.02 or rel[2] > 0.02:
        errs.append('bounds ' + ' '.join(f'L{k} {v * 100:.2f} %' for k, v in rel.items()))
    tris = {lv: sum(m['tris'] for n, m in b['meshes'].items() if level_of(n) == lv) for lv in LEVELS}
    v01 = sum(m['tris'] for m in a['meshes'].values())
    print(f"[BLEND] {tid:<22} {'OK ' if not errs else 'BAD'} bones {len(b['bones'])} actions {len(b['actions'])} meshes "
          f"{len(a['meshes'])}x3 tris v01 {v01} -> L0 {tris[0]} L1 {tris[1]} L2 {tris[2]} bounds "
          + ' '.join(f'L{k} {v * 100:.3f}%' for k, v in rel.items()) + f' {errs}', flush=True)
    return not errs


def fbx_state(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bones = {b.name: (b.parent.name if b.parent else None, b.matrix_local.copy()) for b in arm.data.bones}
    meshes = {}
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        me = o.data
        names = [g.name for g in o.vertex_groups]
        infl = [len([g for g in v.groups if g.weight > 1e-4 and names[g.group] in bones]) for v in me.vertices]
        lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
        for v in me.vertices:
            p = o.matrix_world @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
        meshes[o.name] = {'mats': [m.name if m else None for m in me.materials], 'matrix': o.matrix_world.copy(),
                          'tris': sum(len(p.vertices) - 2 for p in me.polygons), 'unweighted': infl.count(0),
                          'max_infl': max(infl) if infl else 0, 'bounds': (lo, hi), 'parent': o.parent.name if o.parent else None,
                          'keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []}
    return {'arm': arm.name, 'arm_matrix': arm.matrix_world.copy(), 'bones': bones, 'meshes': meshes}


def check_fbx(tid, rev, d):
    a = fbx_state(baseline(tid, rev)[1])
    b = fbx_state(d / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.fbx')
    errs = []
    if a['arm'] != b['arm'] or not close(a['arm_matrix'], b['arm_matrix'], 1e-5):
        errs.append('armature object differs')
    if set(a['bones']) != set(b['bones']):
        errs.append('bone names differ')
    else:
        for n, (par, m) in a['bones'].items():
            if b['bones'][n][0] != par or not close(m, b['bones'][n][1], 1e-5):
                errs.append(f'bone {n} differs'); break
    want = {f'{n}_LOD{lv}' for n in a['meshes'] for lv in LEVELS}
    if set(b['meshes']) != want:
        errs.append(f"meshes differ {sorted(want ^ set(b['meshes']))}")
    for n, ma in a['meshes'].items():
        for lv in LEVELS:
            mb = b['meshes'].get(f'{n}_LOD{lv}')
            if mb is None:
                continue
            if ma['mats'] != mb['mats']:
                errs.append(f'{n}_LOD{lv}: materials differ')
            if not close(ma['matrix'], mb['matrix'], 1e-5) or mb['parent'] != ma['parent']:
                errs.append(f'{n}_LOD{lv}: transform/parent differs')
            if ma['keys'] != mb['keys']:
                errs.append(f'{n}_LOD{lv}: shape keys differ')
            if mb['unweighted'] or mb['max_infl'] > 4:
                errs.append(f"{n}_LOD{lv}: weights (unweighted {mb['unweighted']}, max {mb['max_infl']})")
    lo = [Vector((1e9,) * 3), Vector((1e9,) * 3)]
    hi = [Vector((-1e9,) * 3), Vector((-1e9,) * 3)]
    for k, st in enumerate((a, b)):
        for n, m in st['meshes'].items():
            if k == 1 and not n.endswith('_LOD0'):
                continue
            lo[k] = Vector(map(min, lo[k], m['bounds'][0])); hi[k] = Vector(map(max, hi[k], m['bounds'][1]))
    dist = max((lo[0] - lo[1]).length, (hi[0] - hi[1]).length)
    if dist > 0.001:
        errs.append(f'LOD0 bounds moved {dist * 1000:.2f} mm')
    tris = {lv: sum(m['tris'] for n, m in b['meshes'].items() if n.endswith(f'_LOD{lv}')) for lv in LEVELS}
    print(f"[FBX]   {tid:<22} {'OK ' if not errs else 'BAD'} bones {len(b['bones'])} meshes {len(b['meshes'])} "
          f"tris v01 {sum(m['tris'] for m in a['meshes'].values())} -> L0 {tris[0]} L1 {tris[1]} L2 {tris[2]} "
          f"LOD0 bounds d {dist * 1000:.2f} mm {errs}", flush=True)
    return not errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', default='')
    ap.add_argument('--dir', default=str(HERE))
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    want = [t for t in args.types.split(',') if t]
    d = Path(args.dir)
    bad = done = 0
    for tid, rev in POOL + POOL_SOURCE:
        if want and tid not in want:
            continue
        if not (d / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.blend').exists():
            print(f'[BLEND] {tid:<22} no opt_v02 file')
            continue
        done += 1
        bad += not check_blend(tid, rev, d)
        bad += not check_fbx(tid, rev, d)
    print(f'[VERIFY] types {done}, failed checks {bad}')


if __name__ == '__main__':
    main()
