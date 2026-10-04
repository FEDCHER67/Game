"""Procedural WATER-TOWER-ASTRA-001 builder - village water tower of the Rozhnovsky type (Blender 5.2, background).

Steel cylindrical tank on a tall tubular column, outer ladders, ring walkway with railing, low conical roof,
flat colours with a few rust / peeled-paint patches (moderate low-poly, no textures, no external assets).

Blender Z up, metres. Every exported object has its pivot at the centre of the base on the ground (0,0,0).
Run:  blender -b --factory-startup --python build_water_tower.py -- [--revision N] [--no-render] [--force] [--samples N]
Writes WATER-TOWER-ASTRA-001_vNN.blend / .fbx, validation_vNN.json and Previews/vNN/*.png next to the script.
Existing revision files are never overwritten unless --force is passed.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
NAME = 'WATER-TOWER-ASTRA-001'
ROOT_NAME = 'WT_WaterTower_01'
TRI_BUDGET = 1500

ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, default=1)
ap.add_argument('--no-render', action='store_true')
ap.add_argument('--force', action='store_true', help='overwrite an existing revision')
ap.add_argument('--samples', type=int, default=48)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args, _ = ap.parse_known_args(argv)
REV = f'v{args.revision:02d}'
blend_path = HERE / f'{NAME}_{REV}.blend'
fbx_path = HERE / f'{NAME}_{REV}.fbx'
json_path = HERE / f'validation_{REV}.json'
preview_dir = HERE / 'Previews' / REV
if not args.force:
    for p in (blend_path, fbx_path, json_path):
        if p.exists():
            sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision or pass --force')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
TAU = math.tau

# ---------------------------------------------------------------- dimensions (metres)
SEG = 16                                   # radial segments of body, walkway and rails
PLINTH_R, PLINTH_H = 1.45, 0.40            # octagonal concrete footing (circumradius)
COL_R = 0.70                               # support column radius (1.4 m dia)
COL_Z0, COL_Z1 = 0.25, 14.30               # column starts inside the footing, ends where the cone begins
CONE_Z1 = 15.60                            # conical tank bottom: COL_R -> TANK_R
TANK_R = 1.70                              # tank radius (3.4 m dia)
TANK_Z1 = 20.60                            # top of the tank wall
ROOF_Z = 21.30                             # roof apex
BELT_Z0, BELT_Z1, BELT_T = 17.75, 18.15, 0.07   # stiffening belt around the tank
PLAT_Z0, PLAT_Z1 = 13.80, 13.90            # walkway slab
PLAT_RI, PLAT_RO = 0.74, 2.40              # slab from (almost) the column to 0.7 m beyond the tank wall
NOTCH_RI, NOTCH_SECTORS = 1.50, (11, 12)   # hatch bite in the slab where the lower ladder arrives (azimuth 270)
RAIL_R, RAIL_H, RAIL_T, POST_T = 2.35, 1.10, 0.035, 0.07   # RAIL_T = half thickness of the rail bars
LADDER_LO_AZ, LADDER_UP_AZ = 270.0, 225.0  # degrees, counter-clockwise from +X
LADDER_HALF_W, STRINGER, RUNG_R, RUNG_STEP, STANDOFF = 0.30, 0.10, 0.055, 0.50, 0.25
DOOR_AZ = 225.0
ROOF_SLOPE = (ROOF_Z - TANK_Z1) / TANK_R   # dz per metre of radius


def srgb(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


MATS = {}


def mat(name, rgb, rough=0.85):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = srgb(rgb)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.25
    m.diffuse_color = srgb(rgb)
    MATS[name] = m
    return m


mat('WT_Paint', (118, 146, 152), 0.70)        # faded blue-grey paint of column, tank and roof
mat('WT_Paint_Old', (178, 180, 172), 0.80)    # older light paint layer showing where the top coat peeled
mat('WT_Rust', (124, 68, 42), 0.95)           # rust streaks, column base, brackets
mat('WT_Steel_Dark', (66, 68, 72), 0.80)      # ladders, railing, walkway, door, vent
mat('WT_Concrete', (152, 149, 140), 1.00)     # footing

col = bpy.data.collections.new(NAME)
scene.collection.children.link(col)

# ---------------------------------------------------------------- bmesh helpers
def new_object(name, bm, materials):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(MATS[m])
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def faces_of(verts):
    return {f for v in verts for f in v.link_faces}


def add_box(bm, sx, sy, sz, M, mi=0):
    verts = bmesh.ops.create_cube(bm, size=1.0)['verts']
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=verts)
    bmesh.ops.transform(bm, matrix=M, verts=verts)
    for f in faces_of(verts):
        f.material_index = mi
    return verts


def add_prism(bm, length, r, M, mi=0):
    """Closed triangular bar along local X (8 triangles) - cheap rung that still reads thick."""
    ends = []
    for x in (-length / 2, length / 2):
        ends.append([bm.verts.new(M @ Vector((x, r * math.cos(a), r * math.sin(a))))
                     for a in (math.radians(90), math.radians(210), math.radians(330))])
    a, b = ends
    fs = [bm.faces.new(a[::-1]), bm.faces.new(b)]
    for i in range(3):
        j = (i + 1) % 3
        fs.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in fs:
        f.material_index = mi


def ring_verts(bm, r, z, segments, offset=0.0):
    return [bm.verts.new((r * math.cos(offset + TAU * k / segments), r * math.sin(offset + TAU * k / segments), z))
            for k in range(segments)]


def add_lathe(bm, profile, segments, mat_fn, offset=0.0, cap_bottom=True, cap_top=True):
    """profile = [(r, z), ...] bottom to top; r == 0 makes a single apex vertex. mat_fn(band, sector) -> material index."""
    rings = [ring_verts(bm, r, z, segments, offset) if r > 1e-6 else bm.verts.new((0, 0, z)) for r, z in profile]
    for b in range(len(rings) - 1):
        lo, hi = rings[b], rings[b + 1]
        for k in range(segments):
            k1 = (k + 1) % segments
            if isinstance(lo, list) and isinstance(hi, list):
                f = bm.faces.new((lo[k], lo[k1], hi[k1], hi[k]))
            elif isinstance(lo, list):
                f = bm.faces.new((lo[k], lo[k1], hi))
            else:
                f = bm.faces.new((lo, hi[k1], hi[k]))
            f.material_index = mat_fn(b, k)
    if cap_bottom and isinstance(rings[0], list):
        bm.faces.new(rings[0][::-1]).material_index = mat_fn(0, 0)
    if cap_top and isinstance(rings[-1], list):
        bm.faces.new(rings[-1]).material_index = mat_fn(len(rings) - 2, 0)
    return rings


def add_sweep(bm, profile, segments, mi=0):
    """Closed (r, z) polygon swept around Z: a mitred ring with a solid cross-section (rails)."""
    rings = [ring_verts(bm, r, z, segments) for r, z in profile]
    n = len(rings)
    for i in range(n):
        lo, hi = rings[i], rings[(i + 1) % n]
        for k in range(segments):
            k1 = (k + 1) % segments
            bm.faces.new((lo[k], lo[k1], hi[k1], hi[k])).material_index = mi


def add_walkway(bm, ri, ro, z0, z1, segments, notch, notch_ri, mi=0):
    """Flat annular slab; in the `notch` sectors the inner radius is widened to notch_ri (ladder hatch).
    Sectors next to the notch get an extra vertex so every edge stays manifold."""
    cache = {}

    def V(k, r, z):
        key = (k % segments, round(r, 5), round(z, 5))
        if key not in cache:
            a = TAU * (k % segments) / segments
            cache[key] = bm.verts.new((r * math.cos(a), r * math.sin(a), z))
        return cache[key]

    for k in range(segments):
        in_notch = k in notch
        prev_in, next_in = (k - 1) % segments in notch, (k + 1) % segments in notch
        rin = notch_ri if in_notch else ri
        for z, flip in ((z1, False), (z0, True)):
            poly = [V(k, rin, z)]
            if not in_notch and prev_in:
                poly.append(V(k, notch_ri, z))
            poly += [V(k, ro, z), V(k + 1, ro, z)]
            if not in_notch and next_in:
                poly.append(V(k + 1, notch_ri, z))
            poly.append(V(k + 1, rin, z))
            bm.faces.new(poly[::-1] if flip else poly).material_index = mi
        bm.faces.new((V(k, ro, z0), V(k + 1, ro, z0), V(k + 1, ro, z1), V(k, ro, z1))).material_index = mi
        bm.faces.new((V(k, rin, z0), V(k, rin, z1), V(k + 1, rin, z1), V(k + 1, rin, z0))).material_index = mi
        if in_notch != prev_in:                        # radial wall where the inner radius steps
            a, b = sorted((ri, notch_ri))
            bm.faces.new((V(k, a, z0), V(k, b, z0), V(k, b, z1), V(k, a, z1))).material_index = mi


def add_ladder(bm, az, r_off, z0, z1, rung_z0, rung_z1, bracket_zs, bracket_r0, mi_steel, mi_bracket):
    R = Matrix.Rotation(math.radians(az), 4, 'Z')
    for s in (-1, 1):
        add_box(bm, STRINGER, STRINGER, z1 - z0, R @ Matrix.Translation((r_off, s * LADDER_HALF_W, (z0 + z1) / 2)), mi_steel)
    z, n = rung_z0, 0
    while z <= rung_z1 + 1e-6:
        add_prism(bm, 2 * LADDER_HALF_W, RUNG_R, R @ Matrix.Translation((r_off, 0, z)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'), mi_steel)
        z += RUNG_STEP
        n += 1
    for bz in bracket_zs:                              # flat bracket plates tying the stringers to the wall
        add_box(bm, r_off - bracket_r0, 2 * LADDER_HALF_W + STRINGER, 0.08,
                R @ Matrix.Translation(((r_off + bracket_r0) / 2, 0, bz)), mi_bracket)
    return n


# ---------------------------------------------------------------- tower body (one lathe, per-face paint/rust/peel)
PAINT, OLD, RUST = 0, 1, 2
STREAK = {1, 6, 10, 13}        # vertical rust streaks running from the tank wall down the cone
PEEL = {3, 8, 14}              # peeled-paint strips on the tank
BODY_PROFILE = [
    (COL_R, COL_Z0), (COL_R, 1.60), (COL_R, 13.60), (COL_R, COL_Z1),      # column: rusty base, main, under walkway
    (TANK_R, CONE_Z1), (TANK_R, 16.40), (TANK_R, BELT_Z0),                 # cone, tank bottom band, tank
    (TANK_R + BELT_T, BELT_Z0 + 0.05), (TANK_R + BELT_T, BELT_Z1 - 0.05), (TANK_R, BELT_Z1),   # belt
    (TANK_R, 19.90), (TANK_R, TANK_Z1), (0.0, ROOF_Z)]                     # upper tank, band under the roof, roof


def body_mat(band, k):
    if band == 0:
        return RUST
    if band == 1:
        return OLD if k == 8 else PAINT
    if band == 2:
        return RUST if k in STREAK else PAINT
    if band == 3:
        return RUST if k in STREAK else (OLD if k == 4 else PAINT)
    if band == 4:
        return RUST if k in STREAK else PAINT
    if band == 5:
        return OLD if k in PEEL else PAINT
    if band in (6, 7, 8):
        return RUST if k == 6 else PAINT
    if band == 9:
        return OLD if k in (3, 8) else PAINT
    if band == 10:
        return RUST if k in (2, 7, 11) else PAINT
    return OLD if k in (4, 12) else (RUST if k == 9 else PAINT)   # roof


bm = bmesh.new()
add_lathe(bm, BODY_PROFILE, SEG, body_mat)
body = new_object('WT_Body', bm, ['WT_Paint', 'WT_Paint_Old', 'WT_Rust'])

# ---------------------------------------------------------------- footing
bm = bmesh.new()
add_lathe(bm, [(PLINTH_R, 0.0), (PLINTH_R, PLINTH_H)], 8, lambda b, k: 0, offset=math.radians(22.5))
base = new_object('WT_Base', bm, ['WT_Concrete'])

# ---------------------------------------------------------------- walkway slab + railing
bm = bmesh.new()
add_walkway(bm, PLAT_RI, PLAT_RO, PLAT_Z0, PLAT_Z1, SEG, set(NOTCH_SECTORS), NOTCH_RI)
platform = new_object('WT_Platform', bm, ['WT_Steel_Dark'])

bm = bmesh.new()
for k in range(0, SEG, 2):
    add_box(bm, POST_T, POST_T, RAIL_H, Matrix.Rotation(TAU * k / SEG, 4, 'Z') @ Matrix.Translation((RAIL_R, 0, PLAT_Z1 + RAIL_H / 2)))
for z in (PLAT_Z1 + RAIL_H, PLAT_Z1 + RAIL_H / 2):
    add_sweep(bm, [(RAIL_R - RAIL_T, z - RAIL_T), (RAIL_R + RAIL_T, z - RAIL_T), (RAIL_R + RAIL_T, z + RAIL_T), (RAIL_R - RAIL_T, z + RAIL_T)], SEG)
railing = new_object('WT_Railing', bm, ['WT_Steel_Dark'])

# ---------------------------------------------------------------- ladders
bm = bmesh.new()
n_lo = add_ladder(bm, LADDER_LO_AZ, COL_R + STANDOFF, PLINTH_H - 0.02, PLAT_Z1 + 0.50, 0.80, PLAT_Z1 + 0.40,
                  (2.05, 5.05, 8.05, 11.05, 13.55), COL_R - 0.15, 0, 1)
ladder_lo = new_object('WT_Ladder_Lower', bm, ['WT_Steel_Dark', 'WT_Rust'])
bm = bmesh.new()
n_up = add_ladder(bm, LADDER_UP_AZ, TANK_R + STANDOFF, PLAT_Z1 - 0.02, TANK_Z1 + 0.60, PLAT_Z1 + 0.50, TANK_Z1 + 0.30,
                  (16.65, 19.15), TANK_R - 0.15, 0, 1)
ladder_up = new_object('WT_Ladder_Upper', bm, ['WT_Steel_Dark', 'WT_Rust'])

# ---------------------------------------------------------------- details: door, roof hatch, vent cap
bm = bmesh.new()
Rd = Matrix.Rotation(math.radians(DOOR_AZ), 4, 'Z')
add_box(bm, 0.06, 0.80, 1.90, Rd @ Matrix.Translation((COL_R - 0.01, 0, PLINTH_H + 0.95)))          # door, 3 cm proud
phi = math.atan(ROOF_SLOPE)
hr = 1.20
n_roof = Vector((math.sin(phi), 0, math.cos(phi)))                                                   # roof surface normal
centre = Vector((hr, 0, TANK_Z1 + (TANK_R - hr) * ROOF_SLOPE)) + n_roof * (0.09 - 0.04)
add_box(bm, 0.70, 0.70, 0.18, Rd @ Matrix.Translation(centre) @ Matrix.Rotation(phi, 4, 'Y'))        # hatch, 4 cm sunk
add_lathe(bm, [(0.22, ROOF_Z - 0.45), (0.22, ROOF_Z + 0.30)], 8, lambda b, k: 0)                     # vent pipe over the apex
add_lathe(bm, [(0.32, ROOF_Z + 0.28), (0.32, ROOF_Z + 0.36)], 8, lambda b, k: 0)                     # vent cap disc
details = new_object('WT_Details', bm, ['WT_Steel_Dark'])

# ---------------------------------------------------------------- finish: root, flat shading, box UVs
root = bpy.data.objects.new(ROOT_NAME, None)
root.empty_display_type = 'PLAIN_AXES'
col.objects.link(root)
parts = [body, base, platform, railing, ladder_lo, ladder_up, details]
for p in parts:
    p.parent = root                          # root at world origin: pivot = centre of the footing on the ground
    for poly in p.data.polygons:
        poly.use_smooth = False
    bm = bmesh.new()
    bm.from_mesh(p.data)
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(p.data)
    bm.free()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- validation
def analyse(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)      # "recalculate outside" on a scratch copy
    bm.normal_update()
    flipped = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0)
    zero_area = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    volume = bm.calc_volume(signed=True)
    bm.free()
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return {
        'triangles': tris, 'vertices': len(ob.data.vertices), 'faces': len(ob.data.polygons),
        'materials': [m.name for m in ob.data.materials],
        'origin': [round(v, 4) for v in ob.matrix_world.translation],
        'bounds_min': [round(min(v[i] for v in bb), 4) for i in range(3)],
        'bounds_max': [round(max(v[i] for v in bb), 4) for i in range(3)],
        'non_manifold_edges': nonman, 'boundary_edges': boundary,
        'flipped_faces': flipped, 'zero_area_faces': zero_area,
        'signed_volume_m3': round(volume, 4),
        'mesh_validate_changed': ob.data.validate(verbose=False)}


report = {'asset': NAME, 'revision': REV, 'blender': bpy.app.version_string,
          'axes': 'Blender Z up, metres; FBX exported with axis_forward=-Z, axis_up=Y, apply_unit_scale=True',
          'pivot': 'all objects: centre of the footing on the ground (0,0,0), parented to empty ' + ROOT_NAME,
          'objects': {}}
total = 0
for p in parts:
    report['objects'][p.name] = analyse(p)
    total += report['objects'][p.name]['triangles']
allbb = [p.matrix_world @ Vector(c) for p in parts for c in p.bound_box]
mn = [min(v[i] for v in allbb) for i in range(3)]
mx = [max(v[i] for v in allbb) for i in range(3)]
height = mx[2] - mn[2]
mats_used = sorted({m.name for p in parts for m in p.data.materials})
report['total_triangles'] = total
report['triangle_budget'] = TRI_BUDGET
report['materials'] = mats_used
report['dimensions_m'] = {
    'height_total': round(height, 3), 'height_tank_wall_top': TANK_Z1, 'height_roof_apex': ROOF_Z,
    'size_x': round(mx[0] - mn[0], 3), 'size_y': round(mx[1] - mn[1], 3),
    'bounds_min': [round(v, 3) for v in mn], 'bounds_max': [round(v, 3) for v in mx],
    'tank_diameter': 2 * TANK_R, 'tank_wall_height': round(TANK_Z1 - CONE_Z1, 2),
    'column_diameter': 2 * COL_R, 'column_height': round(COL_Z1 - PLINTH_H, 2),
    'footing_diameter_across_corners': 2 * PLINTH_R, 'footing_height': PLINTH_H,
    'walkway_level': PLAT_Z1, 'walkway_outer_diameter': 2 * PLAT_RO, 'railing_height': RAIL_H,
    'ladder_stringer_section': STRINGER, 'ladder_rung_step': RUNG_STEP, 'ladder_rungs': {'lower': n_lo, 'upper': n_up}}
objs = report['objects']
report['checks'] = {
    'triangles_within_budget': total <= TRI_BUDGET,
    'height_18_24_m': 18.0 <= height <= 24.0,
    'tank_diameter_3_4_m': 3.0 <= 2 * TANK_R <= 4.0,
    'materials_max_5': len(mats_used) <= 5,
    'all_names_prefixed_WT_': all(n.startswith('WT_') for n in list(objs) + mats_used + [ROOT_NAME]),
    'all_meshes_manifold': all(o['non_manifold_edges'] == 0 and o['boundary_edges'] == 0 for o in objs.values()),
    'all_normals_outward': all(o['flipped_faces'] == 0 and o['signed_volume_m3'] > 0 for o in objs.values()),
    'no_zero_area_faces': all(o['zero_area_faces'] == 0 for o in objs.values()),
    'mesh_validate_clean': all(not o['mesh_validate_changed'] for o in objs.values()),
    'stands_on_ground_min_z_0': abs(mn[2]) < 1e-4,
    'pivots_at_origin': all(o['origin'] == [0.0, 0.0, 0.0] for o in objs.values())}
report['all_checks_passed'] = all(report['checks'].values())
report['notes'] = [
    'Intentional shallow embeddings (hidden, no visible intersection): column bottom 15 cm inside the footing; '
    'ladder stringers 2 cm into footing / walkway; bracket plates 15 cm into column / tank wall; door back face 3 cm '
    'inside the column; roof hatch sunk 4 cm into the roof; vent pipe bottom inside the roof cone; rails pass through posts.',
    'Rust / peeled paint are flat per-face material patches on the lathe body (no textures); UVs are a metre-scale box projection.',
    'Lower ladder at azimuth 270 (-Y) rises through a hatch bite in the walkway; upper ladder at azimuth 225 climbs the tank wall to the roof edge.']

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.object.select_all(action='DESELECT')
for o in [root, *parts]:
    o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'EMPTY', 'MESH'},
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                         mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
report['files'] = {'blend': blend_path.name, 'fbx': fbx_path.name, 'fbx_size_bytes': fbx_path.stat().st_size}
json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'[WT] triangles {total}/{TRI_BUDGET}  height {height:.2f} m  checks_ok={report["all_checks_passed"]}')
for k, v in objs.items():
    print(f'[WT] {k:18s} tris {v["triangles"]:5d}  nonmanifold {v["non_manifold_edges"]}  flipped {v["flipped_faces"]}  vol {v["signed_volume_m3"]}')
for k, v in report['checks'].items():
    print(f'[WT] check {k}: {"OK" if v else "FAIL"}')

if args.no_render:
    sys.exit(0)

# ---------------------------------------------------------------- review renders (not part of the .blend / FBX)
preview_dir.mkdir(parents=True, exist_ok=True)
studio = bpy.data.collections.new('Studio_NotExported')
scene.collection.children.link(studio)
world = bpy.data.worlds.new('Sky')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = srgb((158, 186, 210))
bg.inputs[1].default_value = 1.0
sun_d = bpy.data.lights.new('Sun', 'SUN')
sun_d.energy = 4.0
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new('Sun', sun_d)
sun_dir = Vector((math.cos(math.radians(300)), math.sin(math.radians(300)), math.tan(math.radians(52))))
sun.rotation_euler = (-sun_dir).to_track_quat('-Z', 'Y').to_euler()
studio.objects.link(sun)


def studio_mat(name, rgb):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = srgb(rgb)
    b.inputs['Roughness'].default_value = 1.0
    return m


bm = bmesh.new()
add_box(bm, 240, 240, 0.02, Matrix.Translation((0, 0, -0.01)))
me = bpy.data.meshes.new('Ground'); bm.to_mesh(me); bm.free(); me.materials.append(studio_mat('Ground', (104, 118, 78)))
ground = bpy.data.objects.new('Ground', me); studio.objects.link(ground)
bm = bmesh.new()                                                       # scale reference: grey 0.5 x 0.3 x 1.8 m person box
add_box(bm, 0.5, 0.3, 1.8, Matrix.Translation((3.4, -2.4, 0.9)) @ Matrix.Rotation(math.radians(25), 4, 'Z'))
me = bpy.data.meshes.new('ScalePerson'); bm.to_mesh(me); bm.free(); me.materials.append(studio_mat('ScalePerson', (128, 128, 128)))
person = bpy.data.objects.new('ScalePerson_0.5x0.3x1.8', me); studio.objects.link(person)

scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dev
            prefs.get_devices()
            if any(d.type == dev for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = 'GPU'
                break
        except Exception:
            continue
except Exception:
    pass
scene.view_settings.view_transform = 'Standard'
cd = bpy.data.cameras.new('Cam')
cam = bpy.data.objects.new('Cam', cd)
studio.objects.link(cam)
scene.camera = cam


def render(fname, loc, target, lens, res=(1448, 1086)):
    scene.render.resolution_x, scene.render.resolution_y = res
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.type = 'PERSP'
    cd.lens = lens
    cd.clip_end = 500
    scene.render.filepath = str(preview_dir / fname)
    bpy.ops.render.render(write_still=True)
    print('[WT] rendered', fname)


az = math.radians(225)
az_eye = math.radians(250)
render('01_front.png', (0, -58, 11.0), (0, 0, 10.8), 62)
render('02_three_quarter.png', (55 * math.cos(az), 55 * math.sin(az), 16.0), (0, 0, 10.5), 58)
render('03_eye_level_25m.png', (25 * math.cos(az_eye), 25 * math.sin(az_eye), 1.7), (0, 0, 10.5), 36, res=(1086, 1448))
print('[WT] previews in', preview_dir)
