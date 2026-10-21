"""Checks every opt_v01 FBX against its source FBX (both imported into an empty Blender scene):
same armature (bone names, parents, rest matrices), same mesh objects and transforms, same material slots in the same
order, every vertex weighted with at most 4 influences, combined bounds within 1 cm.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/verify_fbx_opt_v01.py
"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from build_types_opt_v01 import POOL, TYPES_DIR, TAG   # noqa: E402


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bones = {b.name: (b.parent.name if b.parent else None, b.matrix_local.copy()) for b in arm.data.bones}
    meshes = {}
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        me = o.data
        names = [g.name for g in o.vertex_groups]
        infl = [len([g for g in v.groups if g.weight > 1e-4 and names[g.group] in bones]) for v in me.vertices]
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        meshes[o.name] = {'mats': [m.name if m else None for m in me.materials], 'matrix': o.matrix_world.copy(), 'tris': tris,
                          'unweighted': infl.count(0), 'max_infl': max(infl) if infl else 0,
                          'shape_keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []}
        for v in me.vertices:
            p = o.matrix_world @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return {'arm': arm.name, 'arm_matrix': arm.matrix_world.copy(), 'bones': bones, 'meshes': meshes, 'bounds': (lo, hi)}


def close(m1, m2, eps=1e-5):
    return all(abs(a - b) <= eps for r1, r2 in zip(m1, m2) for a, b in zip(r1, r2))


bad = 0
for tid, rev in POOL:
    opt = HERE / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.fbx'
    if not opt.exists():
        continue
    a = load(TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}.fbx')
    b = load(opt)
    errs = []
    if a['arm'] != b['arm'] or not close(a['arm_matrix'], b['arm_matrix']):
        errs.append('armature object differs')
    if set(a['bones']) != set(b['bones']):
        errs.append('bone names differ')
    else:
        for n, (par, m) in a['bones'].items():
            if b['bones'][n][0] != par or not close(m, b['bones'][n][1]):
                errs.append(f'bone {n} differs'); break
    if set(a['meshes']) != set(b['meshes']):
        errs.append(f"mesh objects differ {sorted(set(a['meshes']) ^ set(b['meshes']))}")
    for n, ma in a['meshes'].items():
        mb = b['meshes'].get(n)
        if mb is None:
            continue
        if ma['mats'] != mb['mats']:
            errs.append(f'{n}: materials differ')
        if not close(ma['matrix'], mb['matrix']):
            errs.append(f'{n}: transform differs')
        if ma['shape_keys'] != mb['shape_keys']:
            errs.append(f'{n}: shape keys differ')
        if mb['unweighted'] or mb['max_infl'] > 4:
            errs.append(f"{n}: weights (unweighted {mb['unweighted']}, max {mb['max_infl']})")
    d = max((a['bounds'][0] - b['bounds'][0]).length, (a['bounds'][1] - b['bounds'][1]).length)
    if d > 0.01:
        errs.append(f'bounds moved {d * 1000:.1f} mm')
    tri = {n: (a['meshes'][n]['tris'], b['meshes'].get(n, {}).get('tris')) for n in a['meshes']}
    bad += bool(errs)
    print(f"[VERIFY] {tid:<22} {'OK ' if not errs else 'BAD'} bones {len(b['bones'])} bounds d {d * 1000:.2f} mm tris {tri} {errs}", flush=True)
print('[VERIFY] failures:', bad)
