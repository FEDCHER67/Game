"""Read-only FBX/master inspection; writes one numbered audit file inside BEACH/."""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from beach_support import sk
import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--revision', type=int, default=1)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
rev = f'v{args.revision:02d}'
destination = HERE / f'export_audit_{rev}.json'
if destination.exists():
    raise RuntimeError(f'Refusing to replace {destination.name}')
report = json.loads((HERE / f'validation_{rev}.json').read_text(encoding='utf-8'))
checks = {}
for name, expected in report['assets'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / expected['fbx']), use_anim=False)
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    bounds_min = [min(p[i] for p in points) for i in range(3)]
    bounds_max = [max(p[i] for p in points) for i in range(3)]
    triangles = 0
    uv_bad = 0
    degenerate = 0
    allowed_uv = [sk.swatch_uv(sw) for sw in expected['swatches']]
    for ob in meshes:
        ob.data.calc_loop_triangles()
        triangles += len(ob.data.loop_triangles)
        for t in ob.data.loop_triangles:
            pts = [ob.matrix_world @ ob.data.vertices[i].co for i in t.vertices]
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).length < 1e-9:
                degenerate += 1
        uv = ob.data.uv_layers.active
        if uv is None:
            uv_bad += 1
        else:
            uv_bad += sum(1 for item in uv.data if not any(
                abs(item.uv.x - u) < 1e-5 and abs(item.uv.y - v) < 1e-5 for u, v in allowed_uv))
    c = {
        'one_root_mesh': len(meshes) == 1 and meshes[0].parent is None,
        'one_palette_material': all(len(o.data.materials) == 1 and o.data.materials[0].name == sk.PALETTE_NAME for o in meshes),
        'triangle_count_matches': triangles == expected['triangles'],
        'bounds_match_within_1mm': all(abs(bounds_min[i] - expected['bounds_min'][i]) <= 0.001 and
                                    abs(bounds_max[i] - expected['bounds_max'][i]) <= 0.001 for i in range(3)),
        'pivot_origin': all(o.matrix_world.translation.length < 1e-5 for o in meshes),
        'base_on_ground': abs(bounds_min[2]) < 1e-5,
        'uv_palette_cells_preserved': uv_bad == 0,
        'custom_normals_preserved': all(o.data.has_custom_normals for o in meshes),
        'no_degenerate_triangles': degenerate == 0,
        'no_animation_or_armatures': not any(o.type == 'ARMATURE' or o.animation_data is not None for o in bpy.context.scene.objects),
    }
    checks[name] = {'triangles': triangles, 'uv_bad_loops': uv_bad, 'degenerate_triangles': degenerate,
                    'checks': c, 'all_checks_passed': all(c.values())}
    print(name, triangles, [k for k, v in c.items() if not v])

bpy.ops.wm.open_mainfile(filepath=str(HERE / report['files']['blend']))
roots = [o for o in bpy.context.scene.objects if o.type == 'MESH']
master = {
    'exact_requested_17_meshes': sorted(o.name for o in roots) == sorted(report['assets']),
    'no_cameras_people_or_preview_geometry': len(roots) == 17 and all(o.name.startswith('BE_') for o in bpy.context.scene.objects),
    'one_shared_material': len({o.data.materials[0].name for o in roots}) == 1,
    'palette_packed': any(i.name.startswith(sk.PALETTE_NAME) and i.packed_file for i in bpy.data.images),
    'no_actions': len(bpy.data.actions) == 0,
    'metric_units': bpy.context.scene.unit_settings.system == 'METRIC' and bpy.context.scene.unit_settings.scale_length == 1,
}
audit = {'family': report['family'], 'revision': rev, 'method': 'Blender FBX reimport plus master inspection',
         'assets': checks, 'master_checks': master,
         'all_checks_passed': all(r['all_checks_passed'] for r in checks.values()) and all(master.values())}
destination.write_text(json.dumps(audit, indent=2), encoding='utf-8')
print('BEACH_EXPORT_AUDIT', audit['all_checks_passed'])
if not audit['all_checks_passed']:
    raise RuntimeError('Export audit failed')
