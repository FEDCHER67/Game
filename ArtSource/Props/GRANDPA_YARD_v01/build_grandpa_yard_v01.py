"""GRANDPA_YARD_v01 - grandpa's yard props (base 2, Hamlet) for VOLUNTEERS ONLY.

All props are modelled procedurally here (no external sources).
Run headless (Blender 5.2):
  blender --background --factory-startup --python build_grandpa_yard_v01.py -- [--render DIR]
Outputs next to this script:
  FBX/<prop>.fbx, GRANDPA_YARD_v01.blend, GRANDPA_YARD_v01_manifest.json
  with --render DIR: review renders + labels json into DIR (compose_contact_sheet_v01.py makes the sheet).

Conventions (same family as FACADE_KIT_v01):
  * 1 unit = 1 m. Blender Z up, front of a prop = -Y. FBX axis_forward=-Z, axis_up=Y, bake_space_transform
    -> in Unity the prop's front is +Z (transform.forward), +Y up.
  * Pivot = centre of the base on the ground (rocking chair: the rockers' contact point).
  * Hierarchy: empty <prop> -> <prop>_Mesh (one mesh, flat painted materials GY_*) + UCX_<prop>_NN convex hulls.
  * Stylized look: chamfered edges + weighted normals ("soft volume"), flat colours, no textures.
    UV0 = box projection, 1 UV = 1 m (in case textures are added later).
"""
import json, math, sys
sys.dont_write_bytecode = True
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix

OUT = Path(__file__).resolve().parent
FBX_DIR = OUT / 'FBX'
KIT = 'GRANDPA_YARD_v01'
TRI_BUDGET = 1500
UCX_TRI_LIMIT = 255  # Unity convex MeshCollider limit

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER_DIR = Path(ARGS[ARGS.index('--render') + 1]) if '--render' in ARGS else None

MATS = {  # sRGB 0-255, roughness, metallic
    'GY_Paint_Red': ((196, 52, 42), .5, 0),
    'GY_Cushion': ((232, 206, 150), .9, 0),
    'GY_Wood_Stave_A': ((172, 117, 68), .75, 0),
    'GY_Wood_Stave_B': ((148, 98, 57), .75, 0),
    'GY_Wood_Lid': ((186, 136, 84), .75, 0),
    'GY_Metal_Dark': ((70, 66, 66), .55, .3),
    'GY_Drum_Blue': ((58, 110, 150), .5, .1),
    'GY_Rust': ((166, 90, 50), .85, 0),
    'GY_Drum_Inside': ((44, 54, 62), .8, 0),
    'GY_Water': ((58, 104, 112), .06, 0),
    'GY_Tin': ((190, 194, 196), .4, .35),
    'GY_Label_White': ((240, 236, 226), .6, 0),
    'GY_Paint_Green': ((72, 120, 60), .22, 0),
    'GY_Paint_Ochre': ((226, 166, 52), .28, 0),
    'GY_Paint_Blue': ((58, 112, 186), .28, 0),
    'GY_Brush_Handle': ((180, 116, 62), .5, 0),
    'GY_Bristle': ((230, 206, 154), .85, 0),
}


def srgb_lin(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + .055) / 1.055) ** 2.4) for v in c) + (1,)


def material(name):
    m = bpy.data.materials.get(name)
    if not m:
        rgb, rough, metal = MATS[name]
        m = bpy.data.materials.new(name)
        m.diffuse_color = srgb_lin(rgb)
        m.roughness, m.metallic = rough, metal
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = m.diffuse_color
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal
    return m


# ------------------------------------------------------------------ bmesh primitives
def bm_box(sx, sy, sz, c=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    return bm


def bm_xform(bm, rot_x=0.0, c=(0, 0, 0)):
    M = Matrix.Translation(c) @ Matrix.Rotation(rot_x, 4, 'X')
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def bm_beam(a, b, w, t, side=(1, 0, 0)):
    """Box from a to b; w along `side` (projected), t across."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    z = d.normalized()
    x = Vector(side)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    bm = bm_box(w, t, L, (0, 0, L / 2))
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = a
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def bm_cyl_x(r, length, seg, c):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=length)
    M = Matrix.Translation(c) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def bm_lathe(profile, seg, mat_of=lambda i, j: 0, cap_bottom=None, cap_top=None, phase=0.0, closed=False):
    """Revolve [(r, z), ...] around Z. Winding gives outward normals for an upward profile.
    mat_of(segment_index, angle_index) -> local material index; cap_* = material index or None."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg + phase),
                                    r * math.sin(2 * math.pi * j / seg + phase), z)) for j in range(seg)])
    n = len(rings) if closed else len(rings) - 1
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % len(rings)]
        for j in range(seg):
            j2 = (j + 1) % seg
            f = bm.faces.new((r0[j], r0[j2], r1[j2], r1[j]))
            f.material_index = mat_of(i, j)
    if cap_bottom is not None:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = cap_bottom
    if cap_top is not None:
        f = bm.faces.new(rings[-1])
        f.material_index = cap_top
    return bm


def bm_loft_rect(stations, mats=None):
    """stations: [(y, w, t, zc)] rectangles across X/Z along +Y; closed with caps. mats: per segment index."""
    bm = bmesh.new()
    rings = []
    for y, w, t, zc in stations:
        rings.append([bm.verts.new(p) for p in ((-w / 2, y, zc - t / 2), (w / 2, y, zc - t / 2),
                                                (w / 2, y, zc + t / 2), (-w / 2, y, zc + t / 2))])
    for i in range(len(rings) - 1):
        for j in range(4):
            j2 = (j + 1) % 4
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            f.material_index = mats[i] if mats else 0
    f0 = bm.faces.new(rings[0])
    f0.material_index = mats[0] if mats else 0
    f1 = bm.faces.new(list(reversed(rings[-1])))
    f1.material_index = mats[-1] if mats else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_tube(path, rad, nseg=6):
    bm = bmesh.new()
    path = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < .9 else Vector((1, 0, 0))
        n1 = t.cross(ref).normalized()
        n2 = t.cross(n1)
        rings.append([bm.verts.new(p + rad * (math.cos(2 * math.pi * k / nseg) * n1 + math.sin(2 * math.pi * k / nseg) * n2))
                      for k in range(nseg)])
    for i in range(len(rings) - 1):
        for k in range(nseg):
            k2 = (k + 1) % nseg
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_rocker(x, R, h, w, y0, y1, n):
    """Curved rocker: bottom arc radius R touching the ground at y=0, height h (radial), thickness w."""
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        th = math.asin(y / R)
        zb = R - R * math.cos(th)
        yt, zt = (R - h) * math.sin(th), R - (R - h) * math.cos(th)
        rings.append([bm.verts.new(p) for p in ((x - w / 2, y, zb), (x + w / 2, y, zb), (x + w / 2, yt, zt), (x - w / 2, yt, zt))])
    for i in range(n):
        for j in range(4):
            j2 = (j + 1) % 4
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_sphere(c, radii, u=8, v=4):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    return bm


def bm_blob(c, radii, h, n=16, seed=1.0):
    """Flat irregular puddle: extruded wobbly ngon, top at c.z + h."""
    bm = bmesh.new()
    bot, top = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        s = 1 + .16 * math.sin(3 * a + seed) + .09 * math.sin(5 * a + 2 * seed)
        x, y = c[0] + radii[0] * s * math.cos(a), c[1] + radii[1] * s * math.sin(a)
        bot.append(bm.verts.new((x, y, c[2])))
        top.append(bm.verts.new((x, y, c[2] + h)))
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((bot[k], bot[k2], top[k2], top[k]))
    bm.faces.new(top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def ring_pts(r, z, seg=12, phase=0.0):
    return [Vector((r * math.cos(2 * math.pi * j / seg + phase), r * math.sin(2 * math.pi * j / seg + phase), z)) for j in range(seg)]


# ------------------------------------------------------------------ prop assembly
SCRATCH = None


class Prop:
    def __init__(self, name, desc, kind):
        self.name, self.desc, self.kind = name, desc, kind
        self.parts, self.cols = [], []

    def add(self, bm, mats, bevel=0.0, seg=1, smooth=True, col=None):
        """bm faces carry material_index into `mats`. bevel = chamfer width (modifier, applied in finalize).
        col = index of the convex collider that takes this part's (unbevelled) vertices."""
        mats = [mats] if isinstance(mats, str) else mats
        pts = [v.co.copy() for v in bm.verts]
        me = bpy.data.meshes.new(f'{self.name}_p{len(self.parts):02d}')
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(material(m))
        for p in me.polygons:
            p.use_smooth = smooth
        ob = bpy.data.objects.new(me.name, me)
        SCRATCH.objects.link(ob)
        if bevel:
            md = ob.modifiers.new('bevel', 'BEVEL')
            md.width, md.segments = bevel, seg
            md.limit_method = 'ANGLE'
            md.angle_limit = math.radians(30)
        self.parts.append(ob)
        if col is not None:
            while len(self.cols) <= col:
                self.cols.append([])
            self.cols[col] += pts

    def add_col(self, pts):
        self.cols.append([Vector(p) for p in pts])


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def box_uv(me):
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = {0: (co.y, co.z), 1: (co.x, co.z), 2: (co.x, co.y)}[ax]


def hull_mesh(name, pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    drop = {g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert)}
    bmesh.ops.delete(bm, geom=list(drop), context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def finalize(p, coll):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    names = []
    for ob in p.parts:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        remap = []
        for m in me.materials:
            if m.name not in names:
                names.append(m.name)
            remap.append(names.index(m.name))
        for poly in me.polygons:
            poly.material_index = remap[poly.material_index]
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for ob in p.parts:
        bpy.data.objects.remove(ob)
    me = bpy.data.meshes.new(p.name + '_Mesh')
    bm.to_mesh(me)
    bm.free()
    for n in names:
        me.materials.append(bpy.data.materials[n])
    me.set_sharp_from_angle(angle=math.radians(62))  # 90 deg steps hard; chamfers (45) and tube facets (60) soft
    vis = bpy.data.objects.new(p.name + '_Mesh', me)
    coll.objects.link(vis)
    wn = vis.modifiers.new('wn', 'WEIGHTED_NORMAL')
    wn.mode, wn.weight, wn.keep_sharp = 'FACE_AREA', 50, True
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(vis.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    vis.modifiers.clear()
    vis.data = me2
    bpy.data.meshes.remove(me)
    me2.name = p.name + '_Mesh'
    box_uv(me2)

    root = bpy.data.objects.new(p.name, None)
    root.empty_display_size = .25
    coll.objects.link(root)
    vis.parent = root
    objs = [root, vis]
    ucx = []
    for i, pts in enumerate(p.cols):
        hm = hull_mesh(f'UCX_{p.name}_{i:02d}', pts)
        o = bpy.data.objects.new(hm.name, hm)
        o.display_type = 'WIRE'
        o.parent = root
        coll.objects.link(o)
        objs.append(o)
        ucx.append(o)
    t = tris(me2)
    vs = [v.co for v in me2.vertices]
    mn = Vector([min(v[i] for v in vs) for i in range(3)])
    mx = Vector([max(v[i] for v in vs) for i in range(3)])
    assert t <= TRI_BUDGET, (p.name, t)
    assert ucx, p.name
    for o in ucx:
        assert tris(o.data) <= UCX_TRI_LIMIT, (o.name, tris(o.data))
    assert abs(mn.z) < 2e-3, (p.name, 'base not on ground', mn.z)
    info = dict(name=p.name, kind=p.kind, desc=p.desc, tris=t, verts=len(me2.vertices),
                size_m=[round(mx[i] - mn[i], 3) for i in range(3)],
                bounds_min_blender=[round(v, 3) for v in mn], bounds_max_blender=[round(v, 3) for v in mx],
                materials=names, colliders=[dict(name=o.name, tris=tris(o.data)) for o in ucx],
                custom_normals=bool(me2.has_custom_normals), fbx=f'FBX/{p.name}.fbx')
    return root, objs, info


# ------------------------------------------------------------------ props
RED = 'GY_Paint_Red'


def rocking_chair():
    p = Prop('GY_RockingChair_Red', 'Grandpa\'s red wooden rocking chair (porch rocker), cream seat cushion. '
             'Pivot = rockers\' ground contact point.', 'furniture')
    R, hr, wr, xr = 1.25, .06, .042, .265

    def rocker_top(y):
        return R - math.sqrt((R - hr) ** 2 - y * y)

    for s in (-1, 1):
        p.add(bm_rocker(s * xr, R, hr, wr, -.40, .60, 10), RED, bevel=.009, col=0)  # y=0 is a station
    yf, yb, z_top = -.245, .19, 1.05
    zb0 = rocker_top(yb) - .01
    k = (.37 - yb) / (z_top - zb0)  # back post lean (y per z)

    def post_y(z):
        return yb + (z - zb0) * k

    lean = -math.atan(k)
    for s in (-1, 1):
        p.add(bm_beam((s * xr, yf, rocker_top(yf) - .01), (s * xr, yf, .656), .046, .046), RED, bevel=.008, col=0)
        p.add(bm_beam((s * xr, yb, zb0), (s * xr, .37, z_top), .046, .046), RED, bevel=.008, col=1)
        p.add(bm_box(.032, .50, .05, (s * .25, -.02, .362)), RED, bevel=.006, col=0)                 # seat side rail
        p.add(bm_box(.085, .65, .03, (s * .277, -.012, .671)), RED, bevel=.01, col=0)              # armrest
    p.add(bm_box(.50, .032, .05, (0, yf, .362)), RED, bevel=.006, col=0)                          # front seat rail
    p.add(bm_box(.50, .032, .05, (0, .205, .362)), RED, bevel=.006, col=0)                         # back seat rail
    for i in range(3):                                                                              # seat slats
        p.add(bm_box(.56, .138, .03, (0, -.187 + i * .156, .401)), RED, bevel=.007, col=0)
    for z, h in ((.995, .115),):                                                                    # top (crest) rail
        p.add(bm_xform(bm_box(.62, .036, h), lean, (0, post_y(z), z)), RED, bevel=.012, seg=2, col=1)
    p.add(bm_xform(bm_box(.52, .028, .05), lean, (0, post_y(.47), .47)), RED, bevel=.006, col=1)  # low back rail
    for x in (-.145, 0, .145):                                                                      # back slats
        p.add(bm_beam((x, post_y(.47), .47), (x, post_y(.97), .97), .08, .02), RED, bevel=.005, col=1)
    p.add(bm_cyl_x(.016, .53, 8, (0, yf, .20)), RED)                                                # stretchers
    p.add(bm_cyl_x(.016, .53, 8, (0, post_y(.20), .20)), RED)
    p.add(bm_box(.47, .41, .05, (0, -.035, .44)), 'GY_Cushion', bevel=.02, seg=2)                 # cushion
    return p


def barrel_wood():
    p = Prop('GY_Barrel_Wood', 'Old oak barrel with dark metal hoops and a wooden lid with a batten (rain/pickle barrel).',
             'container')
    seg = 16
    prof = [(.245, 0), (.262, .10), (.280, .24), (.290, .40), (.280, .56), (.262, .70), (.245, .80), (.226, .80), (.226, .772)]
    mats = ['GY_Wood_Stave_A', 'GY_Wood_Stave_B', 'GY_Wood_Lid', 'GY_Metal_Dark']
    p.add(bm_lathe(prof, seg, mat_of=lambda i, j: (2 if i == 7 else (j + (1 if j in (5, 12) else 0)) % 2),
                   cap_bottom=0, cap_top=2), mats)

    def rad(z):
        for (r0, z0), (r1, z1) in zip(prof, prof[1:7]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return prof[0][0]

    for z0 in (.06, .20, .555, .695):
        z1 = z0 + .045
        hoop = [(rad(z0) - .004, z0), (rad(z0) + .008, z0), (rad(z1) + .008, z1), (rad(z1) - .004, z1)]
        p.add(bm_lathe(hoop, seg, phase=math.pi / seg), 'GY_Metal_Dark')
    p.add(bm_box(.36, .05, .028, (0, 0, .786)), 'GY_Wood_Lid', bevel=.006)
    p.add_col(ring_pts(.245, 0) + ring_pts(.29, .40) + ring_pts(.245, .80))
    return p


def drum_rain():
    p = Prop('GY_Drum_Rain', 'Old 200 L steel drum, open, used as a rainwater barrel: faded blue paint, worn rusty '
             'chimes/ribs, water inside.', 'container')
    seg = 20
    prof = [(.278, 0), (.293, .006), (.293, .03), (.287, .04), (.287, .12), (.287, .27), (.298, .285), (.287, .30),
            (.287, .58), (.298, .595), (.287, .61), (.287, .845), (.294, .858), (.294, .874), (.285, .885),
            (.277, .885), (.277, .80)]
    mats = ['GY_Drum_Blue', 'GY_Rust', 'GY_Drum_Inside', 'GY_Water']
    rust_patch = {(3, 3), (3, 4), (3, 12), (3, 13), (3, 14)}  # short rust tabs creeping up from the bottom chime
    worn_rib = {0, 1, 2, 3, 4, 9, 10, 15, 16}

    def mat_of(i, j):
        if i <= 2 or i in (11, 12, 13, 14):
            return 1 if (i <= 2 or j in worn_rib or i in (13, 14)) else 0
        if i in (5, 6, 8, 9):
            return 1 if j in worn_rib and i in (5, 6) else 0
        if i == 15:
            return 2
        return 1 if (i, j) in rust_patch else 0

    p.add(bm_lathe(prof, seg, mat_of=mat_of, cap_bottom=1, cap_top=3), mats)
    p.add_col(ring_pts(.294, 0) + ring_pts(.298, .885))
    return p


def bm_drip(r, a, h, length, w, t):
    """Paint drip on a can (radius r, height h) at angle a: flows from the lip over the top bead and down `length`,
    tapering, and ends in a flattened teardrop bulb. Everything hugs the surface (max ~4 mm proud)."""
    bm = bmesh.new()
    z_top, z_end = h - .013, h - .003 - length
    spec = [(r - .004, h + .0008, 1.15, 'up'), (r + .0026, h - .004, 1.1, 'out')]
    for i in range(4):
        spec.append((r + .0006, z_top + (z_end - z_top) * i / 3, 1 - .3 * i / 3, 'out'))
    rows = []
    for rr, z, f, bulge in spec:
        da = (w / 2) * f / rr
        cen = (rr, z + t * .6) if bulge == 'up' else (rr + t, z)
        rows.append([bm.verts.new((rr * math.cos(a - da), rr * math.sin(a - da), z)),
                     bm.verts.new((cen[0] * math.cos(a), cen[0] * math.sin(a), cen[1])),
                     bm.verts.new((rr * math.cos(a + da), rr * math.sin(a + da), z))])
    for i in range(len(rows) - 1):
        for k in range(2):
            bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
    bm.normal_update()
    ref = Vector((math.cos(a), math.sin(a), 1))
    for f in bm.faces:  # open strip: face outward/up
        if f.normal.dot(ref) < 0:
            f.normal_flip()
    bulb = bm_sphere((0, 0, 0), (t * 1.1, w * .42, w * .55), 6, 4)
    bmesh.ops.transform(bulb, matrix=Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((r + .0008, 0, z_end)), verts=bulb.verts)
    me = bpy.data.meshes.new('tmp')
    bulb.to_mesh(me)
    bulb.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def paint_can(name, desc, r, h, paint, opened=False, drips=(), handle_side=-1, puddle=None, seg=20):
    p = Prop(name, desc, 'paint')
    l0, l3 = .022 * h / .19 + .004, h - .022 * h / .19 - .004
    l1 = l0 + (l3 - l0) * .42
    l2 = l1 + (l3 - l0) * .2
    prof = [(r - .003, 0), (r + .002, .003), (r + .002, .010), (r, .013), (r, l0), (r, l1), (r, l2), (r, l3),
            (r, h - .013), (r + .002, h - .010), (r + .002, h - .002), (r - .003, h)]
    if opened:
        prof += [(r - .007, h), (r - .007, h - .032)]
    else:
        prof += [(r - .009, h), (r - .011, h - .005)]
    mats = ['GY_Tin', paint, 'GY_Label_White']
    p.add(bm_lathe(prof, seg, mat_of=lambda i, j: {4: 1, 5: 2, 6: 1}.get(i, 0), cap_bottom=0, cap_top=1 if opened else 0),
          mats)

    for a, length, w in drips:
        p.add(bm_drip(r, math.radians(a), h, length, w, .0032), paint)
    # bail handle: ears on +-X, wire hanging down on the `handle_side` (Y) side
    ze = h - .03
    for s in (-1, 1):
        p.add(bm_box(.007, .02, .024, (s * (r + .0025), 0, ze)), 'GY_Tin', bevel=.002)
    R, d = r + .008, .028 if r > .07 else .02
    path = [(R * math.cos(t), handle_side * R * math.sin(t), ze - d * math.sin(t))
            for t in [math.pi * i / 10 for i in range(11)]]
    p.add(bm_tube(path, .0022, 5), 'GY_Metal_Dark')
    if puddle:
        p.add(bm_blob((puddle[0], puddle[1], 0), (puddle[2], puddle[2] * .8), .003, seed=puddle[3]), paint)
    p.add_col(ring_pts(r + .003, 0, 10) + ring_pts(r + .003, h, 10))
    return p


def paint_lid():
    p = Prop('GY_PaintCan_Lid_Green', 'Lid of the open green can, lying upside down, paint side up.', 'paint')
    prof = [(.0845, 0), (.0845, .0025), (.079, .003), (.077, .011), (.071, .011), (.069, .004)]
    mats = ['GY_Tin', 'GY_Paint_Green']
    p.add(bm_lathe(prof, 20, mat_of=lambda i, j: 1 if i == 4 or (i == 3 and j % 5 in (0, 1)) else 0, cap_bottom=0, cap_top=1),
          mats)
    p.add_col(ring_pts(.0845, 0, 10) + ring_pts(.0845, .0025, 10) + ring_pts(.077, .011, 10))
    return p


def paint_brush():
    p = Prop('GY_PaintBrush_Green', 'Flat 70 mm paint brush lying flat, bristle tips dipped in green paint.', 'paint')
    dy = .0125  # recentre: bristle tip y=-0.15 .. handle end y=0.125
    p.add(bm_loft_rect([(-.085 + dy, .064, .016, .011), (-.118 + dy, .066, .013, .0095), (-.15 + dy, .068, .008, .007)],
                       mats=[0, 1]), ['GY_Bristle', 'GY_Paint_Green'], col=0)
    p.add(bm_box(.072, .046, .022, (0, -.062 + dy, .011)), 'GY_Tin', bevel=.004, col=0)
    p.add(bm_loft_rect([(-.04 + dy, .025, .016, .011), (-.01 + dy, .023, .016, .011), (.06 + dy, .033, .018, .011),
                        (.11 + dy, .037, .018, .011), (.125 + dy, .029, .016, .011)]),
          'GY_Brush_Handle', bevel=.005, seg=2, col=0)
    return p


def build_props():
    return [
        rocking_chair(),
        barrel_wood(),
        drum_rain(),
        paint_can('GY_PaintCan_Open_Green', 'Open 2.7 L can of green paint, drips down the front, small spill.',
                  .0825, .19, 'GY_Paint_Green', opened=True, drips=((-114, .08, .02), (-86, .118, .024), (-58, .05, .017)),
                  handle_side=1, puddle=(.045, -.085, .05, 1.3)),
        paint_can('GY_PaintCan_Ochre', 'Closed 2.7 L can of ochre paint, one dried drip.', .0825, .19, 'GY_Paint_Ochre',
                  drips=((-70, .06, .018),), handle_side=-1),
        paint_can('GY_PaintCan_Small_Blue', 'Closed 0.9 L can of blue paint, one dried drip.', .0525, .12, 'GY_Paint_Blue',
                  drips=((-105, .035, .014),), handle_side=-1, seg=16),
        paint_lid(),
        paint_brush(),
    ]


# ------------------------------------------------------------------ export
def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=True,
                             object_types={'EMPTY', 'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False)


LAYOUT = {  # library .blend / review layout (x, y, rot_z deg)
    'GY_RockingChair_Red': (-.55, .05, 0), 'GY_Barrel_Wood': (.55, .25, 0), 'GY_Drum_Rain': (1.35, .25, 0),
    'GY_PaintBrush_Green': (1.75, -.45, 31), 'GY_PaintCan_Open_Green': (2.03, -.285, 0),
    'GY_PaintCan_Lid_Green': (2.31, -.12, 0), 'GY_PaintCan_Ochre': (2.59, .045, 0),
    'GY_PaintCan_Small_Blue': (2.87, .21, 0),
}


def main():
    global SCRATCH
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.scale_length = 1
    SCRATCH = bpy.data.collections.new('_scratch')
    bpy.context.scene.collection.children.link(SCRATCH)
    coll = bpy.data.collections.new(KIT)
    bpy.context.scene.collection.children.link(coll)
    manifest, roots = [], []
    for p in build_props():
        root, objs, info = finalize(p, coll)
        export(objs, FBX_DIR / f'{p.name}.fbx')
        manifest.append(info)
        roots.append(root)
        print(f'PROP {p.name}: {info["tris"]} tris, size {info["size_m"]}, UCX {[c["tris"] for c in info["colliders"]]}')
    bpy.data.collections.remove(SCRATCH)
    for r in roots:  # library layout (after FBX export, so FBX pivots stay at the origin)
        x, y, rz = LAYOUT[r.name]
        r.location = (x, y, 0)
        r.rotation_euler = (0, 0, math.radians(rz))
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'{KIT}.blend'), compress=True)
    meta = dict(kit=KIT, units='1 unit = 1 m', axes='FBX -Z forward, Y up; Unity +Z = prop front, +Y up',
                pivot='centre of the base on the ground (rocking chair: rockers\' ground contact point)',
                hierarchy='<prop> (empty) -> <prop>_Mesh + UCX_<prop>_NN (convex hulls; builder: convex MeshCollider, no renderer)',
                look='flat painted colours (materials GY_*, sRGB below), chamfers + weighted normals, no textures; UV0 box 1 UV = 1 m',
                source='procedural bpy (build_grandpa_yard_v01.py); no external models',
                tri_budget=TRI_BUDGET,
                materials={k: dict(srgb='#%02X%02X%02X' % v[0], roughness=v[1], metallic=v[2]) for k, v in MATS.items()},
                props=manifest)
    (OUT / f'{KIT}_manifest.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding='utf-8')
    return roots, manifest


if __name__ == '__main__':
    roots, manifest = main()
    if RENDER_DIR:
        sys.path.insert(0, str(OUT))
        import render_review_v01
        render_review_v01.render(roots, manifest, RENDER_DIR)
    print('DONE', len(manifest), 'props; max tris', max(m['tris'] for m in manifest))
