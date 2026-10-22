"""Checks the W86 opt_v01 derivatives (build_types_opt_v01_w86.py) against Vadim's source revisions. Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/verify_opt_v01_w86.py

1. .blend vs .blend: same objects, rig bones (names, parents, rest matrices), actions, and per skinned mesh the same
   vertex-group names, material slots (names, order), shape keys and armature modifier; no unweighted vertex (deform
   bones, weight > 1e-4) where the source has none; at most 4 influences; combined rest bounds within 1 % of the size.
2. .fbx vs .fbx: verify_fbx_opt_v01.py unchanged, run on the W86 pool.
"""
import runpy, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import build_types_opt_v01 as B            # noqa: E402
from build_types_opt_v01_w86 import POOL_W86   # noqa: E402


def load(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects[B.RIG]
    deform = {b.name for b in rig.data.bones if b.use_deform}
    bones = {b.name: (b.parent.name if b.parent else None, b.matrix_local.copy()) for b in rig.data.bones}
    meshes = {}
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.parent != rig:
            continue
        me = o.data
        names = [g.name for g in o.vertex_groups]
        infl = [len([g for g in v.groups if g.weight > 1e-4 and names[g.group] in deform]) for v in me.vertices]
        arm = [m.object.name if m.object else None for m in o.modifiers if m.type == 'ARMATURE']
        meshes[o.name] = {'groups': names, 'mats': [m.name if m else None for m in me.materials],
                          'used': sorted({p.material_index for p in me.polygons}),
                          'keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
                          'arm': arm, 'tris': sum(len(p.vertices) - 2 for p in me.polygons),
                          'unweighted': infl.count(0), 'max_infl': max(infl) if infl else 0, 'uv': [u.name for u in me.uv_layers]}
        mw = o.matrix_world
        for v in me.vertices:
            p = mw @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return {'objects': sorted(o.name for o in bpy.data.objects), 'bones': bones,
            'actions': sorted(a.name for a in bpy.data.actions), 'meshes': meshes, 'bounds': (lo, hi)}


def close(m1, m2, eps=1e-6):
    return all(abs(a - b) <= eps for r1, r2 in zip(m1, m2) for a, b in zip(r1, r2))


bad = 0
for tid, rev in POOL_W86:
    opt = HERE / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{B.TAG}.blend'
    if not opt.exists():
        print(f'[BLEND] {tid:<22} no opt file')
        continue
    a = load(B.TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}.blend')
    b = load(opt)
    errs = []
    if a['objects'] != b['objects']:
        errs.append(f"objects differ {sorted(set(a['objects']) ^ set(b['objects']))}")
    if list(a['bones']) != list(b['bones']):
        errs.append('bone names/order differ')
    else:
        for n, (par, m) in a['bones'].items():
            if b['bones'][n][0] != par or not close(m, b['bones'][n][1]):
                errs.append(f'bone {n} differs'); break
    if a['actions'] != b['actions']:
        errs.append('actions differ')
    for n, ma in a['meshes'].items():
        mb = b['meshes'].get(n)
        if mb is None:
            errs.append(f'{n} missing'); continue
        for k in ('groups', 'mats', 'used', 'keys', 'arm', 'uv'):
            if ma[k] != mb[k]:
                errs.append(f'{n}: {k} differ')
        if mb['unweighted'] > ma['unweighted'] or mb['max_infl'] > 4:
            errs.append(f"{n}: weights (unweighted {ma['unweighted']}->{mb['unweighted']}, max {mb['max_infl']})")
    sa, sb = a['bounds'][1] - a['bounds'][0], b['bounds'][1] - b['bounds'][0]
    rel = max(max(abs(x - y) for x, y in zip(a['bounds'][0], b['bounds'][0])),
              max(abs(x - y) for x, y in zip(a['bounds'][1], b['bounds'][1]))) / max(sa)
    rel_dim = max(abs(x - y) / x for x, y in zip(sa, sb))
    if rel > 0.01 or rel_dim > 0.01:
        errs.append(f'bounds moved {rel * 100:.2f} % / size {rel_dim * 100:.2f} %')
    tris = (sum(m['tris'] for m in a['meshes'].values()), sum(m['tris'] for m in b['meshes'].values()))
    unw = {n: m['unweighted'] for n, m in b['meshes'].items() if m['unweighted']}
    bad += bool(errs)
    print(f"[BLEND] {tid:<22} {'OK ' if not errs else 'BAD'} bones {len(b['bones'])} groups/mesh "
          f"{ {n: len(m['groups']) for n, m in b['meshes'].items()} } mats {sum(len(m['mats']) for m in b['meshes'].values())} "
          f"actions {len(b['actions'])} bounds {rel * 100:.3f} % size {rel_dim * 100:.3f} % tris {tris[0]} -> {tris[1]} "
          f"unweighted {unw or 0} {errs}", flush=True)
print('[BLEND] failures:', bad)

B.POOL = POOL_W86          # the FBX check imports POOL from the build module
runpy.run_path(str(HERE / 'verify_fbx_opt_v01.py'), run_name='__main__')
