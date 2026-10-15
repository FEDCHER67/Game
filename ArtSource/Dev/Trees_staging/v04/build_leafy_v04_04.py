"""G23: poplar-only candidate. Read v04_03; never rebuild/export other families.

Run with installed Blender --background --python <this file>.
The original 48 clusters are translated rigidly, preserving every leaf shape.
Six new clusters reuse the same folded leaves, placed in angular canopy gaps.
"""
import ast
import bpy
import bmesh
import hashlib
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).parent
OUT = ROOT / 'Leafy_Trees_v04_04.blend'
assert not OUT.exists(), 'Existing deliverable: use a new revision'
for letter in 'ABC':
    assert not (ROOT / 'Models' / f'Poplar_{letter}_v04_04.fbx').exists()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
             if p.is_file() and 'v04_04' not in str(p) and '__pycache__' not in str(p)}
old_sheet = ROOT.parents[3] / 'Working/Reviews/Trees/leafy_trees_v04.png'
old_sheet_hash = sha(old_sheet)
baseline = json.loads((ROOT / 'validation_v04_03.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Leafy_Trees_v04_03.blend'))
scene = bpy.context.scene
assert scene.unit_settings.scale_length == 1

def geometry_signature(ob):
    values = {'vertices': [list(v.co) for v in ob.data.vertices],
              'faces': [(list(p.vertices), p.material_index) for p in ob.data.polygons],
              'uv': [[list(v.uv) for v in uv.data] for uv in ob.data.uv_layers],
              'materials': [m.name for m in ob.data.materials],
              'matrix': [list(row) for row in ob.matrix_world],
              'properties': {k: str(ob[k]) for k in ob.keys()}}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

originals = {o.name: geometry_signature(o) for o in bpy.data.objects
             if o.type == 'MESH' and (o.name.startswith('SM_') or o.name.startswith('COL_'))}

# Reuse just the original mesh helper definition. No builder, materials,
# exports, rendering, or other-family authoring from the old script executes.
tree = ast.parse((ROOT / 'build_leafy_v04_03.py').read_text())
helper = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Mesh')
exec(compile(ast.Module(body=[helper], type_ignores=[]), 'v04_03_Mesh_helper', 'exec'))
MATS = [bpy.data.materials['MAT_' + key + '_v04_03'] for key in ('Bark', 'LeafDark', 'Leaf', 'LeafLight')]

collection = bpy.data.collections.new('COL_Poplars_v04_04')
bpy.data.collections['COL_Geo'].children.link(collection)
preview = bpy.data.collections.new('COL_Comparison_v04_04')
scene.collection.children.link(preview)
models = {}
rows = []
metrics = []

def triangle_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

def dimensions(vertices):
    return [max(v[k] for v in vertices) - min(v[k] for v in vertices) for k in range(3)]

def leaf_centres(ob, lod):
    sides = (8, 6, 5)[lod]
    wood = 5 * sides + 24 * (3 * (4, 3, 3)[lod] + 18)
    keep = (1, .49, .23)[lod]
    ids = [i for i in range(576) if ((i * 73) % 101) / 101 <= keep]
    assert len(ob.data.vertices) == wood + len(ids) * 6
    components = {}
    for j, leaf in enumerate(ids):
        indices = list(range(wood + j * 6, wood + (j + 1) * 6))
        components[leaf] = indices
    return wood, components

def profile(z, low, high):
    q = max(0, min(1, (z - low) / (high - low)))
    return 1 + .08 * math.sin(math.pi * q) ** 2

for spec in [s for s in baseline['variants'] if s['family'] == 'Poplar']:
    name = spec['id']
    source0 = bpy.data.objects[f'SM_{name}_v04_03_LOD0']
    wood0, leaves0 = leaf_centres(source0, 0)
    v0 = [v.co.copy() for v in source0.data.vertices]
    crown_low = min(v.z for v in v0[wood0:])
    crown_high = max(v.z for v in v0[wood0:])
    centers = [sum((v0[j] for i in range(c * 12, (c + 1) * 12)
                    for j in leaves0[i]), Vector()) / 72 for c in range(48)]
    # New clusters occupy gaps at six heights rather than piling onto the top.
    additions = []
    for source_cluster in (4, 12, 20, 27, 35, 41):
        center = centers[source_cluster]
        neighbours = [p for p in centers if abs(p.z - center.z) < spec['height'] * .075]
        angles = sorted(math.atan2(p.y, p.x) % math.tau for p in neighbours)
        pairs = [(a, angles[(i + 1) % len(angles)] + (math.tau if i == len(angles) - 1 else 0))
                 for i, a in enumerate(angles)]
        start, end = max(pairs, key=lambda p: p[1] - p[0])
        angle = (start + end) / 2
        turn = angle - math.atan2(center.y, center.x)
        rotation = Matrix.Rotation(turn, 3, 'Z')
        radius = math.hypot(center.x, center.y) * .65
        target = Vector((math.cos(angle) * radius, math.sin(angle) * radius, center.z))
        additions.append((source_cluster, center, target, rotation))

    lod_metrics = []
    for lod in range(3):
        old = bpy.data.objects[f'SM_{name}_v04_03_LOD{lod}']
        wood, old_leaves = leaf_centres(old, lod)
        original = [v.co.copy() for v in old.data.vertices]
        faces = [tuple(p.vertices) for p in old.data.polygons]
        mats = [p.material_index for p in old.data.polygons]
        uv = [tuple(d.uv) for d in old.data.uv_layers.active.data]
        vertices = [v.copy() for v in original]
        cluster_for_vertex = {}
        for leaf, indices in old_leaves.items():
            for index in indices:
                cluster_for_vertex[index] = leaf // 12
        lod_centers = {}
        for cluster in range(48):
            inds = [v for leaf, group in old_leaves.items() if leaf // 12 == cluster for v in group]
            lod_centers[cluster] = sum((original[i] for i in inds), Vector()) / len(inds)

        new_cluster_centers = {}
        for extra, (source_cluster, src, target, rotation) in enumerate(additions):
            cluster = 48 + extra
            new_cluster_centers[cluster] = target
            for leaf_local in range(12):
                leaf_id = 576 + extra * 12 + leaf_local
                if ((leaf_id * 73) % 101) / 101 > (1, .49, .23)[lod]:
                    continue
                old_indices = leaves0[source_cluster * 12 + leaf_local]
                leaf_center = sum((v0[i] for i in old_indices), Vector()) / 6
                new_center = target + rotation @ ((leaf_center - src) * .88)
                size = (1, 1.17, 1.46)[lod]
                new_points = [new_center + rotation @ ((v0[i] - leaf_center) * size) for i in old_indices]
                assert min(v.z for v in new_points) > crown_low
                assert max(v.z for v in new_points) < spec['height']
                offset = len(vertices)
                vertices.extend(new_points)
                for i in range(6):
                    cluster_for_vertex[offset + i] = cluster
                lookup = {old_index: offset + j for j, old_index in enumerate(old_indices)}
                for p in source0.data.polygons:
                    if p.vertices[0] not in lookup:
                        continue
                    assert all(v in lookup for v in p.vertices)
                    faces.append(tuple(lookup[v] for v in p.vertices))
                    mats.append(p.material_index)
                    uv.extend(tuple(source0.data.uv_layers.active.data[li].uv) for li in p.loop_indices)

        all_centers = {**lod_centers, **new_cluster_centers}
        all_points = [v.copy() for v in vertices]
        foliage_indices = list(cluster_for_vertex)
        old_dims = dimensions(original[wood:])
        strengths = []
        # Each horizontal envelope axis is precisely 22.5% wider. Only cluster
        # centres move: original leaf vertices retain all pairwise distances.
        for axis in (0, 1):
            low, high = 0.0, 1.0
            desired = old_dims[axis] * 1.225
            def coord(index, strength):
                c = all_centers[cluster_for_vertex[index]]
                return all_points[index][axis] + c[axis] * strength * profile(c.z, crown_low, crown_high)
            for _ in range(35):
                middle = (low + high) / 2
                width = max(coord(i, middle) for i in foliage_indices) - min(coord(i, middle) for i in foliage_indices)
                if width < desired:
                    low = middle
                else:
                    high = middle
            strength = (low + high) / 2
            strengths.append(strength)
            for i in foliage_indices:
                vertices[i][axis] = coord(i, strength)

        def shift(point):
            p = point.copy()
            weight = profile(p.z, crown_low, crown_high)
            p.x += p.x * strengths[0] * weight
            p.y += p.y * strengths[1] * weight
            return p

        # Preserve trunk rings exactly; reposition branch ring centres without
        # thickening branches. Primary branch roots stay fixed to the trunk.
        trunk_count = 5 * (8, 6, 5)[lod]
        cursor = trunk_count
        branch_centers = []
        for branch in range(24):
            for shoot in range(3):
                sides = (4, 3, 3)[lod] if shoot == 0 else 3
                rings = []
                for ring in range(3):
                    indices = list(range(cursor, cursor + sides))
                    c = sum((original[i] for i in indices), Vector()) / sides
                    moved = c if shoot == 0 and ring == 0 else shift(c)
                    for i in indices:
                        vertices[i] = original[i] + (moved - c)
                    rings.append(moved)
                    cursor += sides
                if shoot == 0:
                    branch_centers.append(rings)
        assert cursor == wood
        for extra, (source_cluster, src, target, rotation) in enumerate(additions):
            center = shift(target)
            start = branch_centers[source_cluster // 2][1]
            tip = center + Vector((0, 0, .16))
            twig = Mesh()
            twig.tube([start, center - Vector((0, 0, .15)), tip], [.018, .010, .004], 3, 0)
            offset = len(vertices)
            vertices.extend(Vector(v) for v in twig.v)
            faces.extend(tuple(offset + i for i in f) for f in twig.f)
            mats.extend(twig.m)
            uv.extend(twig.uv[i] for f in twig.f for i in f)

        mesh = bpy.data.meshes.new(f'SM_{name}_v04_04_LOD{lod}')
        mesh.from_pydata(vertices, [], faces)
        for material in old.data.materials:
            mesh.materials.append(material)
        for poly, mat in zip(mesh.polygons, mats):
            poly.material_index = mat
        uv_layer = mesh.uv_layers.new(name='UVMap')
        assert len(uv) == len(uv_layer.data)
        for loop, val in zip(uv_layer.data, uv):
            loop.uv = val
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bad = sum(not e.is_manifold for e in bm.edges)
        loose = sum(not v.link_edges for v in bm.verts)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        ob = bpy.data.objects.new(mesh.name, mesh)
        collection.objects.link(ob)
        ob['wind'] = old['wind']
        ob['source_revision'] = old.name
        ob['clusters'] = 54
        ob['collider_source'] = name + ' v04_03 unchanged; validation JSON'
        ob.hide_set(True)
        ob.hide_render = True
        models[(name, lod)] = ob
        degenerate = sum(p.area < 1e-10 for p in mesh.polygons)
        assert not (bad or loose or degenerate)
        assert triangle_count(ob) <= 7000
        actual = [v.co.copy() for v in mesh.vertices]
        assert actual[:trunk_count] == original[:trunk_count], 'Trunk changed'
        assert abs(dimensions(actual)[2] - spec['height']) < 1e-5
        # Every original leaf is a rigid translation, including LOD variants.
        max_leaf_error = max(((actual[i] - actual[indices[0]]) -
                              (original[i] - original[indices[0]])).length
                             for indices in old_leaves.values() for i in indices)
        assert max_leaf_error < 2e-6
        foliage_dims = dimensions([actual[i] for i in foliage_indices])
        assert all(abs(foliage_dims[k] / old_dims[k] - 1.225) < 1e-5 for k in (0, 1))
        record = dict(variant=name, lod=lod, triangles=triangle_count(ob), dimensions_m=dimensions(actual),
                      crown_dimensions_m=foliage_dims, source_crown_dimensions_m=old_dims,
                      nonmanifold=bad, loose_vertices=loose, degenerate_faces=degenerate,
                      original_leaf_shape_max_error_m=max_leaf_error, trunk_vertices_identical=True,
                      original_leaves=len(old_leaves), leaves=len(foliage_indices)//6,
                      base_pivot=list(ob.location), scale=list(ob.scale), material_slots=[m.name for m in mesh.materials])
        rows.append(record)
        lod_metrics.append(record)
        print('VALIDATED', json.dumps(record), flush=True)

    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):
        ob = models[(name, lod)]
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = models[(name, 0)]
    bpy.ops.export_scene.fbx(filepath=str(ROOT / 'Models' / f'{name}_v04_04.fbx'),
        use_selection=True, object_types={'MESH'}, global_scale=1, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
        add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=True, path_mode='AUTO')
    for lod in range(3):
        models[(name, lod)].hide_set(True)
    record = lod_metrics[0]
    metrics.append(dict(variant=name, height_m=spec['height'],
        crown_width_before_m=max(record['source_crown_dimensions_m'][:2]),
        crown_width_after_m=max(record['crown_dimensions_m'][:2]),
        clusters_before=48, clusters_after=54, leaves_before=576, leaves_after=648,
        lod_triangles=[r['triangles'] for r in lod_metrics], collider=spec['collider']))

# All approved originals, including their colliders, survive byte-equivalent
# geometry/data signatures inside the new native file. No other family export.
assert all(geometry_signature(bpy.data.objects[n]) == sig for n, sig in originals.items())
for ob in scene.objects:
    if ob.type == 'MESH' and ob.name != 'Hamlet_Ground':
        ob.hide_render = True
cam = scene.camera
def pose_cam(center, width, rx, ry):
    target = Vector(center)
    cam.location = target + Vector((0, -36, 6))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = width
    scene.render.resolution_x = rx
    scene.render.resolution_y = ry
    scene.render.resolution_percentage = 100

try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    if any(d.use for d in prefs.devices):
        scene.cycles.device = 'GPU'
except Exception as exc:
    print('CPU fallback', exc, flush=True)

lineup = []
sources = [bpy.data.objects['CURRENT_Poplar']]
sources += [bpy.data.objects[f'SM_Poplar_{letter}_v04_03_LOD0'] for letter in 'ABC']
sources += [models[(f'Poplar_{letter}', 0)] for letter in 'ABC']
for index, source in enumerate(sources):
    ob = bpy.data.objects.new('COMPARE_' + source.name, source.data)
    preview.objects.link(ob)
    ob.location = (-16.2 + index * 5.4, 0, 0)
    lineup.append(ob)
pose_cam((0, 0, 8.7), 39, 3900, 1800)
scene.render.filepath = str(ROOT / 'Preview/Poplars_lineup_v04_04.png')
bpy.ops.render.render(write_still=True)
for ob in lineup:
    ob.hide_render = True
hero = bpy.data.objects.new('DETAIL_Poplar_A_v04_04', models[('Poplar_A', 0)].data)
preview.objects.link(hero)
pose_cam((0, -.18, 12.5 * .67), 3, 1100, 800)
scene.render.filepath = str(ROOT / 'Preview/Poplar_A_detail_v04_04.png')
bpy.ops.render.render(write_still=True)
hero.hide_render = True
for ob in lineup:
    ob.hide_render = False
pose_cam((0, 0, 8.7), 39, 3900, 1800)
scene['Approval'] = 'G23 poplar-only v04_04; approval sheet; no Unity edits'
scene['PoplarRevision'] = '54 clusters; +22.5% XY envelope; original leaf shapes/trunks/materials/colliders'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
assert all(sha(ROOT / path) == digest for path, digest in protected.items())
assert sha(old_sheet) == old_sheet_hash
report = dict(status='PASS', variants=metrics, lods=rows, original_objects_unchanged=len(originals),
    protected_files=protected, approved_sheet_sha256=old_sheet_hash,
    material_bindings_source='wind_bindings_v04_03.json',
    shared_wind_materials='Reuse existing WindMaterials/*_v04_03.mat exactly; no new shader/material settings',
    current_i05=dict(height_m=dimensions([v.co for v in sources[0].data.vertices])[2], triangles=triangle_count(sources[0])),
    preview=dict(raw_px_per_m=100, final_sheet_px_per_m=93.75, orthographic_width_m=39,
                 positions_x_m=[o.location.x for o in lineup], lighting='Unchanged saved v04_03 Hamlet studio',
                 closeup_width_m=3),
    checks=dict(topology='PASS', leaf_shapes='PASS', heights='PASS', trunks='PASS', old_files='PASS',
                original_native_geometry='PASS', collider_recipe='UNCHANGED', unity='NOT RUN - Blender only'))
(ROOT / 'validation_v04_04.json').write_text(json.dumps(report, indent=2))
print('POPLARS_v04_04_COMPLETE', json.dumps(metrics), flush=True)
