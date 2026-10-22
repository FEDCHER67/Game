"""Re-import every M2 FBX in a clean scene and compare with build_report_v01.json (names, LODs, UCX, UVs, material, size).
  blender -b --factory-startup --python verify_fbx_m2_v01.py"""
import json, sys
from pathlib import Path
import bpy
from mathutils import Vector
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
rep = json.loads((HERE / 'build_report_v01.json').read_text())
bad, n = [], 0
for t, d in rep.items():
    for v, x in d['variants'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(REPO / x['fbx']))
        obs = list(bpy.context.scene.objects)
        root = f'MW86_{t}_{v}'
        names = {o.name for o in obs}
        meshes = [o for o in obs if o.type == 'MESH' and not o.name.startswith('UCX_')]
        ucx = [o for o in obs if o.name.startswith('UCX_')]
        errs = []
        if root not in names: errs.append('root missing')
        want = [root + '_LOD0', root + '_LOD1'] if x['tris_lod1'] else [root + '_Mesh']
        if sorted(o.name for o in meshes) != sorted(want): errs.append(f'meshes {[o.name for o in meshes]}')
        if len(ucx) != x['ucx']: errs.append(f'ucx {len(ucx)} != {x["ucx"]}')
        m0 = next((o for o in meshes if o.name == want[0]), None)
        if m0:
            if not m0.data.uv_layers: errs.append('no uv')
            if [m.name for m in m0.data.materials] != ['MW86_StaticPalette_v01']: errs.append(f'mat {[m.name for m in m0.data.materials]}')
            tris = sum(len(p.vertices) - 2 for p in m0.data.polygons)
            if tris != x['tris_lod0']: errs.append(f'tris {tris} != {x["tris_lod0"]}')
            pts = [m0.matrix_world @ vv.co for vv in m0.data.vertices]
            mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
            if (mn - Vector(x['bounds_min'])).length > .02 or (mx - Vector(x['bounds_max'])).length > .02:
                errs.append(f'bounds {tuple(round(c, 2) for c in mn)} {tuple(round(c, 2) for c in mx)}')
        n += 1
        if errs: bad.append((root, errs))
print('VERIFY', n, 'fbx checked,', len(bad), 'with problems')
for b in bad: print('  ', b)
