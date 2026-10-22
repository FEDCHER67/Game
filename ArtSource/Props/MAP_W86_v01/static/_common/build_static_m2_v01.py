"""MAP_W86_v01 static props (agent M2) - build driver.

  blender -b --factory-startup --python build_static_m2_v01.py -- [--only T1,T2] [--render] [--force]

Per type: ArtSource/Props/MAP_W86_v01/static/<type>/MW86_<type>_v01.blend + SOURCES.md (+ previews/ with --render)
FBX:      Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/FBX/MW86_<type>_<variant>.fbx
Atlas:    Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/Textures/MW86_StaticPalette_v01_{Albedo,MetallicSmoothness,Emission}.png
Report:   _common/build_report_v01.json (per variant tris / bounds / checks)
"""
import sys, json, math, time, zlib
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy
from mathutils import Vector
import m2lib as L
from m2reg import TYPES
import importlib
for _m in ('props_rural', 'props_city', 'props_site', 'props_port', 'props_state'):   # register types
    if (HERE / f'{_m}.py').exists():
        importlib.import_module(_m)

REPO = HERE.parents[4]
SRC = HERE.parent
ASSETS = REPO / 'Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static'
FBX_DIR, TEX_DIR = ASSETS / 'FBX', ASSETS / 'Textures'
REV = 'v01'

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
RENDER = '--render' in ARGS
FORCE = '--force' in ARGS
RENDER_DIR = REPO / 'Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/renders'


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    return sc


def build_variant(spec, tname, var, col):
    root_name = f'MW86_{tname}_{var}'
    root = bpy.data.objects.new(root_name, None)
    col.objects.link(root); root.empty_display_size = .5
    A0 = L.Asset(root_name, lod=0, seed=zlib.crc32(f'{tname}_{var}'.encode()) & 0xffff)
    spec['fn'](A0, var)
    ob0 = A0.to_object(root_name + '_LOD0', col)
    t0 = L.tri_count(ob0)
    meshes = [ob0]
    t1 = None
    if t0 > spec['lod_over']:
        A1 = L.Asset(root_name, lod=1, seed=zlib.crc32(f'{tname}_{var}'.encode()) & 0xffff)
        spec['fn'](A1, var)
        ob1 = A1.to_object(root_name + '_LOD1', col)
        t1 = L.tri_count(ob1)
        if t1 > .75 * t0:        # builder could not simplify enough -> decimate a copy of LOD0
            bpy.data.meshes.remove(ob1.data)
            ob1 = bpy.data.objects.new(root_name + '_LOD1', ob0.data.copy()); col.objects.link(ob1)
            m = ob1.modifiers.new('dec', 'DECIMATE'); m.ratio = .5
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(ob1.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            ob1.modifiers.clear(); old = ob1.data; ob1.data = me; bpy.data.meshes.remove(old)
            t1 = L.tri_count(ob1)
        meshes.append(ob1)
    else:
        ob0.name = root_name + '_Mesh'; ob0.data.name = ob0.name
    ucx = A0.ucx_objects(root_name, col)
    for o in meshes + ucx:
        o.parent = root
    mn, mx = L.bounds([ob0])
    return dict(root=root, meshes=meshes, ucx=ucx, tris_lod0=t0, tris_lod1=t1, bmin=mn, bmax=mx, notes=A0.notes)


def checks_for(spec, r):
    mn, mx = r['bmin'], r['bmax']
    c = {
        'pivot_on_ground': abs(mn.z) < .02 or spec.get('below_ground_ok', False) or mn.z < 0,
        'base_not_floating': mn.z < .05,
        'tris_within_budget': r['tris_lod0'] <= spec['budget'],
        'lod1_when_over_1k': r['tris_lod0'] <= 1000 or r['tris_lod1'] is not None,
        'no_empty_mesh': r['tris_lod0'] > 0,
    }
    ok = True
    for o in r['meshes']:
        me = o.data
        if any(p.area < 1e-9 for p in me.polygons):
            c['no_zero_area_faces'] = False; ok = False
    c.setdefault('no_zero_area_faces', True)
    return c


def setup_render(sc):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = 420
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'Standard'
    except TypeError:
        pass
    w = bpy.data.worlds.new('W'); sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.62, .68, .76, 1); bg.inputs[1].default_value = .9
    sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(6)
    so = bpy.data.objects.new('Sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    cam = bpy.data.cameras.new('Cam'); cam.lens = 50
    co = bpy.data.objects.new('Cam', cam); sc.collection.objects.link(co); sc.camera = co
    gm = bpy.data.materials.new('REVIEW_Ground')
    bsdf = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (.42, .44, .45, 1); bsdf.inputs['Roughness'].default_value = .95
    bpy.ops.mesh.primitive_plane_add(size=400)
    g = bpy.context.active_object; g.name = 'REVIEW_Ground'; g.data.materials.append(gm)
    return co, g


def render_variant(sc, cam, ground, r, out_png, view=(1.0, -1.35, .8)):
    mn, mx = r['bmin'], r['bmax']
    c = (mn + mx) / 2
    size = (mx - mn)
    rad = max(.25, size.length / 2)
    d = Vector(view).normalized()
    fov = 2 * math.atan(18 / cam.data.lens)
    dist = rad / math.sin(fov / 2) * 1.02
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = dist * 4 + 100
    ground.location = (c.x, c.y, mn.z - .002)
    sc.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)


def sources_md(tname, spec, results, fbx_paths):
    lines = [f'# MW86_{tname} - sources', '',
             f'Original procedural low-poly model made by agent M2 (Claude, Opus 5.5) on 2026-10-22 for VOLUNTEERS ONLY,',
             'built headless in Blender 5.2 by `../_common/build_static_m2_v01.py` (type builder in `../_common/props_*.py`,',
             'shared geometry library `../_common/m2lib.py`).', '',
             '- Third-party assets: none (no downloaded geometry or textures).',
             '- Colours: own flat palette atlas `MW86_StaticPalette_v01` (Albedo / MetallicSmoothness / Emission, 256 px),',
             '  generated by the same script; shared by every M2 static prop.',
             '- Licence: project-owned original work.', '',
             f'Data kinds replaced: {", ".join(spec["kinds"])}; W85 placeholder box size {spec["data_size"]}.', '',
             '| variant | FBX | tris LOD0 | tris LOD1 | size (m, Blender X x Y x Z) |', '|---|---|---|---|---|']
    for var, r in results.items():
        s = r['bmax'] - r['bmin']
        lines.append(f'| {var} | `{fbx_paths[var]}` | {r["tris_lod0"]} | {r["tris_lod1"] or "-"} | {s.x:.2f} x {s.y:.2f} x {s.z:.2f} |')
    if spec['notes']:
        lines += ['', 'Notes: ' + spec['notes']]
    return '\n'.join(lines) + '\n'


def main():
    t_start = time.time()
    names = [n for n in TYPES if not ONLY or n in ONLY]
    report_path = HERE / f'build_report_{REV}.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    reset_scene()
    atlas = L.write_atlases(TEX_DIR)
    (HERE / 'palette_v01.json').write_text(json.dumps(L.palette_json(), indent=1))
    for tname in names:
        spec = TYPES[tname]
        sc = reset_scene()
        L.make_material({k: v for k, v in atlas.items()})
        col = sc.collection
        results, fbx_paths = {}, {}
        for var in spec['variants']:
            r = build_variant(spec, tname, var, col)
            results[var] = r
        # export each variant (root at origin)
        for var, r in results.items():
            fbx = FBX_DIR / f'MW86_{tname}_{var}.fbx'
            if fbx.exists() and not FORCE:
                raise SystemExit(f'Refusing to overwrite {fbx} (use --force only for your own same-revision rebuild)')
            L.export_fbx([r['root']] + r['meshes'] + r['ucx'], fbx)
            fbx_paths[var] = str(fbx.relative_to(REPO)).replace('\\', '/')
        # previews
        if RENDER:
            RENDER_DIR.mkdir(parents=True, exist_ok=True)
            cam, ground = setup_render(sc)
            for var, r in results.items():
                for o in col.objects:
                    if o.type == 'MESH' and o.name != 'REVIEW_Ground':
                        o.hide_render = not (o in r['meshes'][:1])
                render_variant(sc, cam, ground, r, RENDER_DIR / f'MW86_{tname}_{var}.png', view=spec['view'] or (1.0, -1.35, .8))
            for o in col.objects:
                if o.type == 'MESH' and not o.name.startswith('UCX_'):
                    o.hide_render = False
            bpy.data.objects.remove(ground); bpy.data.objects.remove(cam)
        # lay variants out side by side, save the .blend
        x = 0.0
        for var, r in results.items():
            w = r['bmax'].x - r['bmin'].x
            r['root'].location.x = x - r['bmin'].x
            x += w + 1.0
        folder = SRC / spec['folder']
        folder.mkdir(parents=True, exist_ok=True)
        blend = folder / f'MW86_{tname}_{REV}.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
        (folder / 'SOURCES.md').write_text(sources_md(tname, spec, results, fbx_paths), encoding='utf-8')
        rep = {}
        for var, r in results.items():
            rep[var] = dict(fbx=fbx_paths[var], tris_lod0=r['tris_lod0'], tris_lod1=r['tris_lod1'],
                            bounds_min=[round(v, 3) for v in r['bmin']], bounds_max=[round(v, 3) for v in r['bmax']],
                            ucx=len(r['ucx']), checks=checks_for(spec, r), notes=r['notes'])
        report[tname] = dict(kinds=spec['kinds'], data_size=spec['data_size'], placement=spec['placement'],
                             front=spec['front'], rotation_offset_y=spec['rotation_offset_y'], y_offset=spec['y_offset'],
                             scale_rule=spec['scale_rule'], collider_note=spec['collider_note'], notes=spec['notes'],
                             variant_rule=spec['variant_rule'], blend=str(blend.relative_to(REPO)).replace('\\', '/'),
                             variants=rep)
        print(f'[M2] {tname}: ' + ', '.join(f'{v} {r["tris_lod0"]}/{r["tris_lod1"] or "-"}' for v, r in results.items()))
    report_path.write_text(json.dumps(report, indent=1))
    print(f'[M2] done {len(names)} types in {time.time() - t_start:.0f} s')


main()
