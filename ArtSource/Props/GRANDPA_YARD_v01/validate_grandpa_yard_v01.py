"""Re-imports every FBX of GRANDPA_YARD_v01 into an empty scene and checks it against the manifest.
Run: blender --background --factory-startup --python validate_grandpa_yard_v01.py
Checks: hierarchy (<prop> empty -> <prop>_Mesh + UCX_<prop>_NN), size vs manifest (1 cm), base on the ground,
pivot at base centre (XY within the footprint), tris <= 1500, UCX convex + closed + <= 255 tris, normals, materials."""
import json, sys
from pathlib import Path

import bpy, bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
man = json.loads((HERE / 'GRANDPA_YARD_v01_manifest.json').read_text(encoding='utf-8'))
results, ok_all = [], True


def convex(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    closed = all(e.is_manifold for e in bm.edges)
    worst = max((v.co - f.calc_center_median()).dot(f.normal) for f in bm.faces for v in bm.verts)
    bm.free()
    return closed, worst


for p in man['props']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / p['fbx']))
    bpy.context.view_layer.update()
    objs = {o.name: o for o in bpy.context.scene.objects}
    root = objs.get(p['name'])
    vis = objs.get(p['name'] + '_Mesh')
    ucx = sorted(n for n in objs if n.startswith('UCX_' + p['name'] + '_'))
    err = []
    if not root or root.type != 'EMPTY':
        err.append('root empty missing')
    if not vis or vis.parent != root:
        err.append('visual mesh missing / not parented')
    if len(ucx) != len(p['colliders']):
        err.append(f'UCX count {len(ucx)} != {len(p["colliders"])}')
    pts = [vis.matrix_world @ v.co for v in vis.data.vertices]
    mn = Vector([min(q[i] for q in pts) for i in range(3)])
    mx = Vector([max(q[i] for q in pts) for i in range(3)])
    size = [mx[i] - mn[i] for i in range(3)]
    if any(abs(a - b) > .01 for a, b in zip(size, p['size_m'])):
        err.append(f'size {size} != manifest {p["size_m"]}')
    if abs(mn.z) > .002:
        err.append(f'base z {mn.z:.4f}')
    if not (mn.x < 0 < mx.x and mn.y < 0 < mx.y):
        err.append('pivot outside footprint')
    t = sum(len(f.vertices) - 2 for f in vis.data.polygons)
    if t > 1500:
        err.append(f'tris {t}')
    ucx_rows = []
    for n in ucx:
        o = objs[n]
        closed, worst = convex(o.data)
        ut = sum(len(f.vertices) - 2 for f in o.data.polygons)
        ucx_rows.append(dict(name=n, tris=ut, closed=closed, max_outside_m=round(worst, 5)))
        if not closed or worst > 1e-4 or ut > 255:
            err.append(f'{n} not a closed convex hull <=255 tris')
    mats = [m.name for m in vis.data.materials]
    if sorted(mats) != sorted(p['materials']):
        err.append(f'materials {mats}')
    ok_all &= not err
    results.append(dict(name=p['name'], ok=not err, errors=err, tris=t, size_m=[round(s, 3) for s in size],
                        min_z=round(mn.z, 4), materials=len(mats), custom_normals=vis.data.has_custom_normals,
                        root_scale=[round(s, 4) for s in root.matrix_world.to_scale()], ucx=ucx_rows))
    print('CHECK', p['name'], 'OK' if not err else err, f'tris={t}', f'size={[round(s, 3) for s in size]}',
          f'ucx={[r["tris"] for r in ucx_rows]}', f'custom_normals={vis.data.has_custom_normals}')

(HERE / 'GRANDPA_YARD_v01_validation.json').write_text(json.dumps(dict(all_ok=ok_all, props=results), indent=1),
                                                         encoding='utf-8')
print('VALIDATION', 'PASS' if ok_all else 'FAIL')
