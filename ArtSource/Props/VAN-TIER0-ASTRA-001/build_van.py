"""Procedural VAN-TIER0-ASTRA-001 builder (Blender 5.2, background).

Blender Z up, -Y forward, metres. Vehicle left = +X (driver side), right = -X (sliding door side).
Proportions measured from Source/TripoViews/Rev01 (owner-approved REV07 views).
Run:  blender -b --factory-startup --python build_van.py -- --revision N [--no-render]
Every revision writes new numbered .blend/.fbx/validation/previews; existing files are never overwritten.
v01 was built by the previous version of this script (closed cab, three opening doors).
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
NAME = 'VAN-TIER0-ASTRA-001'
ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--no-render', action='store_true')
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = f'v{args.revision:02d}'
blend_path = HERE / f'{NAME}_{REV}.blend'
fbx_path = HERE / f'{NAME}_{REV}.fbx'
json_path = HERE / f'validation_{REV}.json'
preview_dir = HERE / 'Previews' / REV
for p in (blend_path, fbx_path, json_path):
    if p.exists():
        sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ---------------------------------------------------------------- dimensions
HALF_W = 0.94            # body half width below the belt
BELT_Z = 1.30            # sides lean inward above this height
ROOF_Z = 2.08
ROOF_HALF_W = 0.80       # half width at roof height (tumblehome)
BODY_BOTTOM = 0.35
FRONT_Y, REAR_Y = -2.29, 2.19
WHEEL_R, WHEEL_W = 0.37, 0.24
AXLES = (-1.60, 1.56)    # front, rear (y)
WALL = 0.05
FLOOR_Z = 0.55
GAP = 0.006              # visible door gap
SIDE_PROFILE = [         # (y, z) outer outline seen from the side
    (REAR_Y, BODY_BOTTOM), (REAR_Y, ROOF_Z), (-0.99, ROOF_Z),
    (-1.69, 1.38), (-2.22, 1.08), (FRONT_Y, 0.98), (FRONT_Y, BODY_BOTTOM)]
# hollow cab + cargo: rear wall, roof, windshield inner face, footwell front
CAVITY_PROFILE = [
    (REAR_Y - 0.06, FLOOR_Z), (REAR_Y - 0.06, ROOF_Z - 0.10), (-1.019, ROOF_Z - 0.10),
    (-1.699, 1.30), (-1.70, FLOOR_Z)]
FRONT_DOOR_POLY = [(-1.48, 0.40), (-0.44, 0.40), (-0.44, 1.97), (-1.04, 1.97), (-1.65, 1.36)]
CAB_WINDOW = [(-1.61, 1.36), (-0.55, 1.36), (-0.55, 1.92), (-1.05, 1.92)]
SLIDE_RECT = (-0.42, 0.90, 0.40, 1.93)   # y0, y1, z0, z1
REAR_DOOR_Z = (0.62, 1.94)
DRIVER_EYE = (0.48, -0.78, 1.60)


def hw(z):
    """Outer half width of the body at height z."""
    if z <= BELT_Z:
        return HALF_W
    t = min(1.0, (z - BELT_Z) / (ROOF_Z - BELT_Z))
    return HALF_W + (ROOF_HALF_W - HALF_W) * t


def srgb(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


MATS = {}


def mat(name, rgb, rough=0.85, alpha=1.0):
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
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    m.diffuse_color = srgb(rgb)[:3] + (alpha,)
    MATS[name] = m
    return m


mat('VAN_Body_Cream', (233, 222, 203))
mat('VAN_Body_Crease', (196, 184, 163))
mat('VAN_Interior', (150, 144, 134))
mat('VAN_Trim_Dark', (62, 63, 66))
mat('VAN_Grille_Black', (34, 35, 37))
mat('VAN_Glass', (58, 66, 80), rough=0.15, alpha=0.45)
mat('VAN_Light_White', (236, 236, 232), rough=0.4)
mat('VAN_Indicator_Orange', (226, 128, 28), rough=0.5)
mat('VAN_Tail_Red', (204, 38, 38), rough=0.5)
mat('VAN_Hub_Cream', (214, 205, 186))
mat('VAN_Tire', (44, 44, 46), rough=0.95)
mat('VAN_Seat', (70, 72, 78), rough=0.95)

col = bpy.data.collections.new(NAME)
scene.collection.children.link(col)
cutters = bpy.data.collections.new('Cutters_NotExported')
scene.collection.children.link(cutters)


def obj_from_bm(name, bm, material, collection=col):
    # mirrored construction can leave closed meshes inside-out; booleans then imprint without removing
    if bm.faces and all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MATS[material])
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, material, collection=col):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return obj_from_bm(name, bm, material, collection)


def cyl(name, r, depth, center, axis, material, segments=16, collection=col):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r, radius2=r, depth=depth)
    rot = {'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X'), 'Z': Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ rot, verts=bm.verts)
    return obj_from_bm(name, bm, material, collection)


def side_prism(name, poly, inner_offset, outer, side, material, collection=cutters):
    """(y,z) polygon extruded across X; inner face follows the leaning body side.
    side=+1/-1: x from side*(hw(z)-inner_offset) to side*outer. side=0: symmetric slab between both inner walls."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((0.0, y, z)) for y, z in poly])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(1.0, 0, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    zs = [z for _, z in poly]
    if min(zs) < BELT_Z < max(zs):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                               plane_co=(0, 0, BELT_Z), plane_no=(0, 0, 1))
    for v in bm.verts:
        inner = hw(v.co.z) - inner_offset
        if side == 0:
            v.co.x = -inner if v.co.x < 0.5 else inner
        else:
            v.co.x = side * (inner if v.co.x < 0.5 else outer)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)


def rect(y0, y1, z0, z1):
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def inset_convex(poly, d):
    """Shrink a convex counter-clockwise (y,z) polygon by distance d."""
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))            # inward for CCW
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        p1, t1 = lines[i - 1]
        p2, t2 = lines[i]
        den = t1.x * t2.y - t1.y * t2.x
        s = ((p2 - p1).x * t2.y - (p2 - p1).y * t2.x) / den
        q = p1 + t1 * s
        out.append((q.x, q.y))
    return out


def through_prism(name, pts, direction, depth, material, collection=cutters):
    """Planar polygon pts (3D) extruded +-depth along direction (window openings)."""
    d = Vector(direction).normalized() * depth
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new(Vector(p) - d) for p in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=d * 2, verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)


def pane(name, pts, normal, material='VAN_Glass'):
    """Double-sided glass: outward quad plus an inward-facing copy 3 mm inside."""
    n = Vector(normal).normalized()
    bm = bmesh.new()
    outer = bm.faces.new([bm.verts.new(Vector(p)) for p in pts])
    inner = bm.faces.new([bm.verts.new(Vector(p) - n * 0.003) for p in reversed(pts)])
    bm.normal_update()
    if outer.normal.dot(n) < 0:
        bmesh.ops.reverse_faces(bm, faces=[outer, inner])
    return obj_from_bm(name, bm, material)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)


def boolean(target, cutter, op='DIFFERENCE'):
    m = target.modifiers.new(f'{op}_{cutter.name}', 'BOOLEAN')
    m.operation = op
    m.solver = 'EXACT'
    m.object = cutter
    m.material_mode = 'TRANSFER'
    apply_mods(target)


def join(target, parts):
    for p in parts:
        mw = target.matrix_world.inverted() @ p.matrix_world
        bm = bmesh.new()
        bm.from_mesh(p.data)
        bmesh.ops.transform(bm, matrix=mw, verts=bm.verts)
        for m in p.data.materials:
            if m.name not in [t.name for t in target.data.materials]:
                target.data.materials.append(m)
        remap = [[t.name for t in target.data.materials].index(m.name) for m in p.data.materials]
        for f in bm.faces:
            f.material_index = remap[f.material_index]
        tmp = bpy.data.meshes.new('tmp')
        bm.to_mesh(tmp)
        bm.free()
        tb = bmesh.new()
        tb.from_mesh(target.data)
        tb.from_mesh(tmp)
        tb.to_mesh(target.data)
        tb.free()
        bpy.data.meshes.remove(tmp)
        bpy.data.objects.remove(p)


def set_origin(ob, point):
    point = Vector(point)
    ob.data.transform(Matrix.Translation(-point))
    ob.location = point


def profile_solid(name, profile, inset, material, collection):
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((-1.0, y, z)) for y, z in profile])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(2.0, 0, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6, plane_co=(0, 0, BELT_Z), plane_no=(0, 0, 1))
    for v in bm.verts:
        v.co.x = math.copysign(hw(v.co.z) - inset, v.co.x)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)

# ---------------------------------------------------------------- outer shell
body = profile_solid('VAN_Body', SIDE_PROFILE, 0.0, 'VAN_Body_Cream', col)
bev = body.modifiers.new('Chamfer', 'BEVEL')
bev.width = 0.045
bev.segments = 1
bev.limit_method = 'ANGLE'
bev.angle_limit = math.radians(30)
bev.use_clamp_overlap = True
apply_mods(body)

for i, y in enumerate(AXLES):                      # wheel arches, per side so the cab is not tunnelled
    for s in (1, -1):
        boolean(body, cyl(f'Cut_Arch_{i}_{s}', 0.44, 0.75, Vector((s * 0.925, y, WHEEL_R)), 'X', 'VAN_Trim_Dark', 16, cutters))
for s in (1, -1):                                   # side crease line
    boolean(body, box(f'Cut_Crease_{s}', s * 0.93, s * 1.2, -2.25, 2.25, 0.994, 1.006, 'VAN_Body_Crease', cutters))

# one hollow space for cab and cargo, with wheel housings
cavity = profile_solid('Cut_Cavity', CAVITY_PROFILE, WALL, 'VAN_Interior', cutters)
for i, y in enumerate(AXLES):
    for s in (1, -1):
        boolean(cavity, cyl(f'Cut_Housing_{i}_{s}', 0.48, 0.80, Vector((s * 0.92, y, WHEEL_R)), 'X', 'VAN_Interior', 16, cutters))
boolean(body, cavity)

# windshield opening
n_ws = Vector((0, -1, 1)).normalized()
ws_pts = []
for z, sgn in ((2.00, 1), (2.00, -1), (1.44, -1), (1.44, 1)):
    y = -0.99 - (ROOF_Z - z)
    ws_pts.append(Vector((sgn * (hw(z) - 0.08), y, z)))
boolean(body, through_prism('Cut_Windshield', ws_pts, n_ws, 0.2, 'VAN_Trim_Dark'))

# ---------------------------------------------------------------- doors cut from the shell
doors = {}
specs = [
    ('VAN_Door_Front_Left', FRONT_DOOR_POLY, 1),
    ('VAN_Door_Front_Right', FRONT_DOOR_POLY, -1),
    ('VAN_Door_Slide', rect(*SLIDE_RECT), -1),
]
for name, poly, s in specs:
    hole = side_prism('Cut_Hole_' + name, poly, WALL + 0.006, 1.3, s, 'VAN_Interior')
    keep = side_prism('Keep_' + name, inset_convex(poly, GAP), WALL + 0.006, 1.3, s, 'VAN_Interior')
    door = body.copy(); door.data = body.data.copy(); door.name = name; col.objects.link(door)
    boolean(door, keep, 'INTERSECT')
    doors[name] = (door, hole)
for name, x0, x1 in (('VAN_Door_Rear_Left', 0.0, 0.80), ('VAN_Door_Rear_Right', -0.80, 0.0)):
    z0, z1 = REAR_DOOR_Z
    hole = box('Cut_Hole_' + name, x0, x1, REAR_Y - 0.09, REAR_Y + 0.3, z0, z1, 'VAN_Interior', cutters)
    sx0 = x0 + (GAP if x0 != 0 else GAP / 2)
    sx1 = x1 - (GAP if x1 != 0 else GAP / 2)
    keep = box('Keep_' + name, sx0, sx1, REAR_Y - 0.09, REAR_Y + 0.3, z0 + GAP, z1 - GAP, 'VAN_Interior', cutters)
    door = body.copy(); door.data = body.data.copy(); door.name = name; col.objects.link(door)
    boolean(door, keep, 'INTERSECT')
    doors[name] = (door, hole)
for name, (door, hole) in doors.items():
    boolean(body, hole)
fl, fr = doors['VAN_Door_Front_Left'][0], doors['VAN_Door_Front_Right'][0]
slide = doors['VAN_Door_Slide'][0]
rl, rr = doors['VAN_Door_Rear_Left'][0], doors['VAN_Door_Rear_Right'][0]

# cab door windows: opening + glass, mirror and handle travel with the door
for door, s in ((fl, 1), (fr, -1)):
    win = [Vector((s * hw(z), y, z)) for y, z in inset_convex(CAB_WINDOW, 0.0)]
    boolean(door, through_prism(f'Cut_CabWin_{s}', win, (s, 0, 0), 0.25, 'VAN_Trim_Dark'))
    glass = pane(f'Glass_Cab_{s}', [Vector((s * (hw(z) + 0.004), y, z)) for y, z in inset_convex(CAB_WINDOW, -0.02)], (s, 0, 0))
    join(door, [glass,
                box(f'MirrorArm_{s}', s * (hw(1.40) - 0.02), s * 1.01, -1.33, -1.29, 1.36, 1.41, 'VAN_Trim_Dark'),
                box(f'Mirror_{s}', s * 1.00, s * 1.07, -1.37, -1.25, 1.30, 1.57, 'VAN_Trim_Dark'),
                box(f'Handle_Front_{s}', s * 0.935, s * 0.958, -0.70, -0.58, 1.19, 1.24, 'VAN_Trim_Dark')])

join(slide, [box('Handle_Slide', -0.958, -0.935, -0.37, -0.32, 1.10, 1.27, 'VAN_Trim_Dark')])
for door, s in ((rl, 1), (rr, -1)):
    pts = [(s * 0.07, 1.36), (s * 0.70, 1.36), (s * 0.70, 1.86), (s * 0.07, 1.86)]
    boolean(door, through_prism(f'Cut_RearWin_{s}', [Vector((x, REAR_Y, z)) for x, z in pts], (0, 1, 0), 0.2, 'VAN_Trim_Dark'))
    big = [(s * 0.05, 1.34), (s * 0.72, 1.34), (s * 0.72, 1.88), (s * 0.05, 1.88)]
    join(door, [pane(f'Glass_Rear_{s}', [Vector((x, REAR_Y + 0.004, z)) for x, z in big], (0, 1, 0))])
join(rr, [box('Handle_Rear', -0.10, -0.06, REAR_Y, REAR_Y + 0.025, 1.08, 1.22, 'VAN_Trim_Dark')])

# ---------------------------------------------------------------- body details
details = [pane('Glass_Windshield', [p + n_ws * 0.006 + (Vector((math.copysign(0.02, p.x), 0, 0))) for p in ws_pts], n_ws)]
details.append(box('Fascia', -0.80, 0.80, FRONT_Y - 0.02, FRONT_Y + 0.02, 0.70, 1.02, 'VAN_Trim_Dark'))
details.append(box('Grille', -0.40, 0.40, FRONT_Y - 0.028, FRONT_Y, 0.735, 0.985, 'VAN_Grille_Black'))
for z in (0.79, 0.86, 0.93):
    details.append(box(f'Slat_{z}', -0.38, 0.38, FRONT_Y - 0.036, FRONT_Y - 0.02, z - 0.016, z + 0.016, 'VAN_Trim_Dark'))
for s in (1, -1):
    details.append(cyl(f'Headlight_{s}', 0.105, 0.03, Vector((s * 0.61, FRONT_Y - 0.03, 0.86)), 'Y', 'VAN_Light_White', 16))
    details.append(box(f'Indicator_{s}', s * 0.52, s * 0.72, FRONT_Y - 0.012, FRONT_Y + 0.01, 0.635, 0.685, 'VAN_Indicator_Orange'))
    for z0, z1, m in ((0.84, 0.98, 'VAN_Tail_Red'), (0.98, 1.10, 'VAN_Indicator_Orange'), (1.10, 1.24, 'VAN_Tail_Red')):
        details.append(box(f'Tail_{s}_{z0}', s * 0.81, s * 0.915, REAR_Y - 0.01, REAR_Y + 0.02, z0, z1, m))
for nm, y0, y1 in (('Bumper_Front', -2.42, FRONT_Y + 0.06), ('Bumper_Rear', REAR_Y - 0.06, 2.36)):
    b = box(nm, -0.97, 0.97, y0, y1, 0.28, 0.62, 'VAN_Trim_Dark')
    m = b.modifiers.new('Chamfer', 'BEVEL'); m.width = 0.03; m.segments = 1
    apply_mods(b)
    details.append(b)
details.append(box('Rail_Slide', -0.962, -0.935, 0.95, 1.98, 1.15, 1.21, 'VAN_Trim_Dark'))
# cab interior: driver seat (left), two-seat bench (right), dashboard, steering column
for nm, x0, x1 in (('Seat_Driver', 0.26, 0.72), ('Seat_Bench', -0.82, -0.10)):
    details.append(box(nm + '_Base', x0, x1, -1.06, -0.62, FLOOR_Z, 0.98, 'VAN_Seat'))
    details.append(box(nm + '_Back', x0, x1, -0.62, -0.50, 0.98, 1.66, 'VAN_Seat'))
dash_w = hw(1.25) - WALL - 0.01
details.append(box('Dashboard', -dash_w, dash_w, -1.70, -1.40, 0.95, 1.30, 'VAN_Trim_Dark'))
details.append(box('SteeringColumn', 0.455, 0.505, -1.44, -1.32, 1.04, 1.14, 'VAN_Trim_Dark'))
join(body, details)

# steering wheel as its own object so the game can turn it
bpy.ops.mesh.primitive_torus_add(major_radius=0.165, minor_radius=0.022, major_segments=14, minor_segments=6)
sw = bpy.context.active_object
sw.name = 'VAN_SteeringWheel'
for c in sw.users_collection:
    c.objects.unlink(sw)
col.objects.link(sw)
sw.data.materials.append(MATS['VAN_Trim_Dark'])
hub = cyl('SW_Hub', 0.05, 0.03, Vector((0, 0, 0)), 'Z', 'VAN_Trim_Dark', 8)
spoke = box('SW_Spoke', -0.155, 0.155, -0.015, 0.015, -0.01, 0.01, 'VAN_Trim_Dark')
join(sw, [hub, spoke])
SW_CENTER = Vector((0.48, -1.30, 1.17))
sw.data.transform(Matrix.Rotation(math.radians(-62), 4, 'X'))   # tilt the rim towards the driver
sw.location = SW_CENTER

# ---------------------------------------------------------------- pivots
set_origin(fl, (hw(0.9), -1.55, 0.40))
set_origin(fr, (-hw(0.9), -1.55, 0.40))
set_origin(slide, (-HALF_W, SLIDE_RECT[0], SLIDE_RECT[2]))
set_origin(rl, (0.80, REAR_Y, REAR_DOOR_Z[0]))
set_origin(rr, (-0.80, REAR_Y, REAR_DOOR_Z[0]))

# ---------------------------------------------------------------- wheels
wheels = []
for i, y in enumerate(AXLES):
    for s in (1, -1):
        nm = f"VAN_Wheel_{'Front' if i == 0 else 'Rear'}_{'Left' if s > 0 else 'Right'}"
        tire = cyl(nm, WHEEL_R, WHEEL_W, Vector((s * 0.80, y, WHEEL_R)), 'X', 'VAN_Tire', 16)
        hubc = cyl(nm + '_Hub', 0.215, 0.02, Vector((s * (0.80 + WHEEL_W / 2 + 0.008), y, WHEEL_R)), 'X', 'VAN_Hub_Cream', 16)
        cap = cyl(nm + '_Cap', 0.08, 0.02, Vector((s * (0.80 + WHEEL_W / 2 + 0.022), y, WHEEL_R)), 'X', 'VAN_Grille_Black', 12)
        join(tire, [hubc, cap])
        set_origin(tire, (s * 0.80, y, WHEEL_R))
        wheels.append(tire)

# ---------------------------------------------------------------- finish
root = bpy.data.objects.new(NAME, None)
root.empty_display_type = 'PLAIN_AXES'
col.objects.link(root)
eye = bpy.data.objects.new('SOCKET_DriverEye', None)
eye.empty_display_type = 'SPHERE'; eye.empty_display_size = 0.08
eye.location = DRIVER_EYE
col.objects.link(eye)
door_objs = [fl, fr, slide, rl, rr]
parts = [body, *door_objs, sw, *wheels]
for p in parts + [eye]:
    p.parent = root          # root sits at the world origin, so local == world placement
for p in parts:
    for poly in p.data.polygons:
        poly.use_smooth = False
    bm = bmesh.new(); bm.from_mesh(p.data)
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(p.data); bm.free()
for c in list(cutters.objects):
    bpy.data.objects.remove(c)
bpy.data.collections.remove(cutters)
for m in bpy.data.meshes:
    if m.users == 0:
        bpy.data.meshes.remove(m)

# ---------------------------------------------------------------- review animation (kept in .blend, not exported)
OPEN = {  # name: (kind, value) -- hinge angle in degrees about world Z, or slide path
    'VAN_Door_Front_Left': ('hinge', -70), 'VAN_Door_Front_Right': ('hinge', 70),
    'VAN_Door_Rear_Left': ('hinge', -100), 'VAN_Door_Rear_Right': ('hinge', 100),
    'VAN_Door_Slide': ('slide', (Vector((-0.07, 0.0, 0)), Vector((-0.07, 1.02, 0)))),
}
scene.frame_start, scene.frame_end = 1, 110
for d in door_objs:
    kind, val = OPEN[d.name]
    base_loc, base_rot = d.location.copy(), d.rotation_euler.copy()
    if kind == 'hinge':
        for f, a in ((1, 0), (35, val), (70, val), (105, 0)):
            d.rotation_euler.z = math.radians(a); d.keyframe_insert('rotation_euler', index=2, frame=f)
        d.rotation_euler = base_rot
    else:
        pop, slid = val
        for f, off in ((1, Vector()), (10, pop), (35, slid), (70, slid), (95, pop), (105, Vector())):
            d.location = base_loc + off; d.keyframe_insert('location', frame=f)
        d.location = base_loc
scene.frame_set(1)

# ---------------------------------------------------------------- validation
bpy.context.view_layer.update()
report = {'asset': NAME, 'revision': REV, 'axes': 'Blender Z up, -Y forward, metres; vehicle left=+X (driver)', 'objects': {}}
total = 0
for p in parts:
    bm = bmesh.new(); bm.from_mesh(p.data)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    bb = [p.matrix_world @ Vector(c) for c in p.bound_box]
    report['objects'][p.name] = {
        'triangles': tris, 'vertices': len(p.data.vertices), 'open_edges': nonman,
        'materials': [m.name for m in p.data.materials], 'origin': [round(v, 4) for v in p.location],
        'bounds_min': [round(min(v[i] for v in bb), 4) for i in range(3)],
        'bounds_max': [round(max(v[i] for v in bb), 4) for i in range(3)]}
    total += tris
report['total_triangles'] = total
allbb = [p.matrix_world @ Vector(c) for p in parts for c in p.bound_box]
report['overall_size_m'] = [round(max(v[i] for v in allbb) - min(v[i] for v in allbb), 3) for i in range(3)]
report['sockets'] = {'SOCKET_DriverEye': list(DRIVER_EYE)}
report['door_motion_blender'] = {k: (v[0], v[1] if v[0] == 'hinge' else [list(v[1][0]), list(v[1][1])]) for k, v in OPEN.items()}
report['note'] = 'Glass panes are intentionally open double-sided quads (open_edges). Door motions are review keyframes only; the FBX is exported closed and without animation.'

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.object.select_all(action='DESELECT')
for o in [root, eye, *parts]:
    o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'EMPTY', 'MESH'},
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                         mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('[VAN] triangles', total, 'size', report['overall_size_m'])
for k, v in report['objects'].items():
    print('[VAN]', k, v['triangles'], 'open_edges', v['open_edges'])

if args.no_render:
    sys.exit(0)

# ---------------------------------------------------------------- review renders (not part of the FBX)
preview_dir.mkdir(parents=True, exist_ok=True)
studio = bpy.data.collections.new('Studio_NotExported'); scene.collection.children.link(studio)
world = bpy.data.worlds.new('Studio'); scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = srgb((70, 76, 84)); bg.inputs[1].default_value = 0.9


def light(name, loc, power, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = (Vector((0, 0, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    studio.objects.link(o)


light('Key', (-6, -7, 8), 2600, 6)
light('Fill', (7, 5, 5), 1100, 6)
light('Rim', (0, 9, 6), 700, 5)
fm = bpy.data.materials.new('Floor')
try:
    fm.use_nodes = True
except Exception:
    pass
fb = next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
fb.inputs['Base Color'].default_value = srgb((70, 76, 84)); fb.inputs['Roughness'].default_value = 1
bpy.ops.mesh.primitive_plane_add(size=60)
floor = bpy.context.active_object; floor.data.materials.append(fm)
for c in floor.users_collection:
    c.objects.unlink(floor)
studio.objects.link(floor)

scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
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
scene.render.resolution_x, scene.render.resolution_y = 1448, 1086
scene.view_settings.view_transform = 'Standard'
cd = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cd); studio.objects.link(cam); scene.camera = cam


def render(fname, loc, target=(0, 0, 1.05), ortho=None, lens=50, frame=1):
    scene.frame_set(frame)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.type = 'PERSP'; cd.lens = lens
    scene.render.filepath = str(preview_dir / fname)
    bpy.ops.render.render(write_still=True)


render('01_front.png', (0, -14, 1.05), ortho=3.3)
render('02_left.png', (14, 0, 1.05), ortho=5.6)
render('03_right.png', (-14, 0, 1.05), ortho=5.6)
render('04_back.png', (0, 14, 1.05), ortho=3.3)
render('05_three_quarter_right.png', (-6.8, -7.8, 3.2), target=(0, 0, 0.95), lens=45)
render('06_three_quarter_left.png', (6.8, -7.8, 3.2), target=(0, 0, 0.95), lens=45)
render('07_open_rear.png', (-5.5, 9.0, 3.4), target=(0, 0.8, 0.95), lens=40, frame=50)
render('08_open_right.png', (-8.5, -3.0, 2.8), target=(0, -0.2, 0.95), lens=40, frame=50)
render('09_open_left.png', (8.0, -5.0, 2.8), target=(0, -0.6, 0.95), lens=40, frame=50)
render('10_driver_view.png', (DRIVER_EYE[0], DRIVER_EYE[1], DRIVER_EYE[2]), target=(DRIVER_EYE[0], -6, 1.25), lens=20)
print('[VAN] previews in', preview_dir)
