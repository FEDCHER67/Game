"""HAMLET_HOUSE_v02 (= v01 + round-3 fixes: 2 windows on the street gable, no log ends poking out under the roof edges): a CIS khutor log house (izba) for VOLUNTEERS ONLY, One-Armed Robber painted style.

Headless: "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P build_hamlet_house_v02.py [-- --render]
Output: FBX/HH_House_v02.fbx (+ HH_House_v02.blend, preview PNGs with --render).

Footprint 7.0 m (gable front, X) x 8.5 m (depth, Y; ridge along Y). Blender -Y = Unity +Z = street side (front gable).
Material zones (one slot each; Unity maps them to the approved textures, colour per house in the material):
  HH_Plinth   brick plinth 0.7 m          HH_Wall      log wall (logs texture)      HH_LogEnds  corner log joints
  HH_Gable    vertical-board gables        HH_Trim      nalichniki, barge boards, fascia, sill boards (painted)
  HH_Shutter  shutters (painted)           HH_WindowFrame / HH_Glass                 HH_Door
  HH_Roof     wavy slate, 42 deg gable    HH_RoofTrim  ridge cap, chimney cap       HH_Wood   porch deck/posts/steps
  HH_Brick    chimney
UV0: box projection, 1 UV = 1 m (tiling in the material, like FACADE_KIT_v01). Colliders: UCX_HH_House_v01_NN convex hulls.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
(OUT / 'FBX').mkdir(exist_ok=True)
NAME = 'HH_House_v02'

W, D = 7.0, 8.5                     # gable front width (X), depth along the ridge (Y)
HX, HY = W / 2, D / 2
PL, EAVE = .7, 3.5                  # plinth top (floor), wall top
PITCH = math.radians(42)
RISE = HX * math.tan(PITCH)         # 3.15 m
RIDGE = EAVE + RISE
OV_E, OV_R = .5, .45                # eave overhang (X), rake overhang (Y)
SLAB = .1

COLS = {  # preview colours (sRGB) only; Unity assigns its own materials
    'HH_Plinth': (150, 88, 70), 'HH_Wall': (139, 104, 74), 'HH_LogEnds': (190, 150, 105), 'HH_Gable': (118, 150, 132),
    'HH_Trim': (236, 231, 218), 'HH_Shutter': (95, 132, 166), 'HH_WindowFrame': (236, 231, 218), 'HH_Glass': (62, 75, 85),
    'HH_Door': (107, 79, 62), 'HH_Roof': (128, 136, 134), 'HH_RoofTrim': (100, 106, 104), 'HH_Wood': (140, 107, 74),
    'HH_Brick': (150, 88, 70),
}
ORDER = list(COLS)

V, F, M = [], [], []                # vertices, faces, material index per face
HULLS = []


def lin(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= .04045 else ((v / 255 + .055) / 1.055) ** 2.4) for v in c) + (1,)


def add(verts, faces, mat):
    o = len(V)
    V.extend(Vector(v) for v in verts)
    for f in faces:
        F.append(tuple(i + o for i in f)); M.append(ORDER.index(mat))


def box(x0, x1, y0, y1, z0, z1, mat, hull=False):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    add(v, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)], mat)
    if hull:
        HULLS.append(v)


def cbox(cx, cy, cz, sx, sy, sz, mat):
    box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, mat)


def prism(profile, a0, a1, axis, mat):
    """Extrude a 2D convex polygon (u, z) along axis 'x' or 'y' from a0 to a1 (profile CCW seen from +axis)."""
    n = len(profile)
    if axis == 'y':
        v = [(u, a0, z) for u, z in profile] + [(u, a1, z) for u, z in profile]
    else:
        v = [(a0, u, z) for u, z in profile] + [(a1, u, z) for u, z in profile]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if axis == 'x':
        faces = [f[::-1] for f in faces]
    add(v, faces, mat)


def cyl(c, axis, r, length, mat, sides=8):
    """Cylinder centred at c along axis 'x' or 'y'."""
    c = Vector(c)
    ring = [(r * math.cos(2 * math.pi * i / sides + math.pi / sides), r * math.sin(2 * math.pi * i / sides + math.pi / sides)) for i in range(sides)]
    if axis == 'x':
        v = [(c.x - length / 2, c.y + a, c.z + b) for a, b in ring] + [(c.x + length / 2, c.y + a, c.z + b) for a, b in ring]
    else:
        v = [(c.x + a, c.y - length / 2, c.z + b) for a, b in ring] + [(c.x + a, c.y + length / 2, c.z + b) for a, b in ring]
    n = sides
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if axis == 'y':
        faces = [f[::-1] for f in faces]
    add(v, faces, mat)


# ------------------------------------------------------------------ wall-local helper: s along the wall, z up, d outward
class Wall:
    def __init__(self, origin, along, out):
        self.o, self.a, self.n = Vector(origin), Vector(along), Vector(out)

    def p(self, s, z, d):
        return self.o + self.a * s + Vector((0, 0, z)) + self.n * d

    def rect(self, s0, s1, z0, z1, d0, d1, mat):
        pts = [self.p(s, z, d) for d in (d0, d1) for z in (z0, z1) for s in (s0, s1)]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        box(min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), mat)

    def tri(self, s0, s1, z0, apex_z, d0, d1, mat):
        """Triangular board (base s0..s1 at z0, apex at the middle) d0..d1 out of the wall."""
        sm = (s0 + s1) / 2
        prof = [(s0, z0), (s1, z0), (sm, apex_z)]
        v = [self.p(s, z, d) for d in (d0, d1) for s, z in prof]
        faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
        if self.a.cross(self.n).z < 0:
            faces = [f[::-1] for f in faces]
        add([tuple(x) for x in v], faces, mat)


WALLS = {
    'front': Wall((-HX, -HY, 0), (1, 0, 0), (0, -1, 0)),
    'back': Wall((HX, HY, 0), (-1, 0, 0), (0, 1, 0)),
    'east': Wall((HX, -HY, 0), (0, 1, 0), (1, 0, 0)),
    'west': Wall((-HX, HY, 0), (0, -1, 0), (-1, 0, 0)),
}


def window(w, s, sill, ww=1.0, wh=1.3, shutters=True, carved=True):
    """Glazed window with frame, cross mullion, carved nalichnik (crest + skirt) and open shutters."""
    z0, z1 = sill, sill + wh
    w.rect(s - ww / 2 + .05, s + ww / 2 - .05, z0 + .05, z1 - .05, -.02, .02, 'HH_Glass')
    for a, b, c, d in ((s - ww / 2, s + ww / 2, z0, z0 + .07), (s - ww / 2, s + ww / 2, z1 - .07, z1),
                       (s - ww / 2, s - ww / 2 + .07, z0, z1), (s + ww / 2 - .07, s + ww / 2, z0, z1),
                       (s - .025, s + .025, z0, z1), (s - ww / 2, s + ww / 2, z0 + wh * .66 - .025, z0 + wh * .66 + .025)):
        w.rect(a, b, c, d, 0, .05, 'HH_WindowFrame')
    t = .14                                             # nalichnik boards around the opening
    w.rect(s - ww / 2 - t, s - ww / 2, z0, z1, 0, .06, 'HH_Trim')
    w.rect(s + ww / 2, s + ww / 2 + t, z0, z1, 0, .06, 'HH_Trim')
    w.rect(s - ww / 2 - t - .08, s + ww / 2 + t + .08, z1, z1 + .2, 0, .08, 'HH_Trim')          # head board
    w.rect(s - ww / 2 - t - .12, s + ww / 2 + t + .12, z0 - .08, z0, 0, .14, 'HH_Trim')         # sill board
    if carved:
        w.tri(s - ww / 2 - t - .05, s + ww / 2 + t + .05, z1 + .2, z1 + .52, 0, .07, 'HH_Trim')   # kokoshnik crest
        w.rect(s - ww / 2 + .02, s + ww / 2 - .02, z0 - .26, z0 - .08, 0, .05, 'HH_Trim')       # skirt board
        n = 5                                                                                 # carved teeth under it
        span = ww - .04
        for i in range(n):
            a = s - span / 2 + span * i / n
            w.rect(a + .03, a + span / n - .03, z0 - .36, z0 - .26, .005, .045, 'HH_Trim')
    if shutters:
        sw = ww / 2 - .05
        for side in (-1, 1):
            c = s + side * (ww / 2 + t + .02 + sw / 2)
            w.rect(c - sw / 2, c + sw / 2, z0, z1, .02, .06, 'HH_Shutter')
            w.rect(c - sw / 2 + .06, c + sw / 2 - .06, z0 + wh * .52 - .05, z0 + wh * .52 + .05, .06, .08, 'HH_Trim')   # rail
            w.rect(c - sw / 2 + .06, c + sw / 2 - .06, z0 + .12, z0 + .2, .06, .08, 'HH_Trim')
            w.rect(c - sw / 2 + .06, c + sw / 2 - .06, z1 - .2, z1 - .12, .06, .08, 'HH_Trim')


def build():
    # plinth (brick, 0.12 proud of the walls) and the log wall core
    box(-HX - .12, HX + .12, -HY - .12, HY + .12, 0, PL, 'HH_Plinth', hull=False)
    box(-HX - .14, HX + .14, -HY - .14, HY + .14, PL - .06, PL, 'HH_Trim')                  # drip board on the plinth
    box(-HX, HX, -HY, HY, PL, EAVE, 'HH_Wall')
    # corner log joints (v obloh): log ends crossing at every course, alternating directions
    r, step = .12, .24
    z, k = PL + r, 0
    while z < EAVE - .2:                                # v02: no log end reaches the roof edge
        for sx in (-1, 1):
            for sy in (-1, 1):
                if k % 2 == 0:
                    cyl((sx * (HX + .02), sy * (HY + .12), z), 'y', r, .4, 'HH_LogEnds')
                else:
                    cyl((sx * (HX + .12), sy * (HY + .02), z), 'x', r, .4, 'HH_LogEnds')
        z += step; k += 1
    # gables: vertical boards 4 cm proud, trim board at the gable base (material boundary log / boards)
    for y, sgn in ((-HY, -1), (HY, 1)):
        d0, d1 = 0, .04
        prof = [(-HX, EAVE), (HX, EAVE), (0, RIDGE)]
        v = [(u, y + sgn * d, z) for d in (d0, d1) for u, z in prof]
        faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
        if sgn > 0:
            faces = [f[::-1] for f in faces]
        add(v, faces, 'HH_Gable')
        box(-HX - .1, HX + .1, min(y, y + sgn * .1), max(y, y + sgn * .1), EAVE - .12, EAVE + .08, 'HH_Trim')
    # roof: two 42 deg slabs (wavy slate), eave overhang 0.5 m, rake overhang 0.45 m
    ze = EAVE - OV_E * math.tan(PITCH)
    for sx in (-1, 1):
        prof = [(sx * (HX + OV_E), ze), (0, RIDGE), (0, RIDGE + SLAB / math.cos(PITCH)), (sx * (HX + OV_E), ze + SLAB / math.cos(PITCH))]
        if sx > 0:
            prof = prof[::-1]
        prism(prof, -HY - OV_R, HY + OV_R, 'y', 'HH_Roof')
    prism([(-.16, RIDGE + .05), (.16, RIDGE + .05), (0, RIDGE + .2)], -HY - OV_R - .02, HY + OV_R + .02, 'y', 'HH_RoofTrim')   # ridge cap
    # fascia along the eaves, barge boards (prichelina) along the rakes, towel board at the apex
    for sx in (-1, 1):
        box(min(sx * (HX + OV_E), sx * (HX + OV_E - .04)), max(sx * (HX + OV_E), sx * (HX + OV_E - .04)), -HY - OV_R, HY + OV_R, ze - .2, ze + .02, 'HH_Trim')
    for y in (-HY - OV_R, HY + OV_R - .05):
        for sx in (-1, 1):
            a = Vector((sx * (HX + OV_E), y, ze - .02)); b = Vector((0, y, RIDGE + .02))
            down = Vector((0, 0, -1))
            pts = [a, b, b + down * .26, a + down * .26]
            v = [tuple(p + Vector((0, d, 0))) for d in (0, .05) for p in pts]
            add(v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], 'HH_Trim')
        box(-.09, .09, y, y + .05, RIDGE - 1.1, RIDGE - .1, 'HH_Trim')
        add([(-.09, y, RIDGE - 1.1), (.09, y, RIDGE - 1.1), (0, y, RIDGE - 1.3), (-.09, y + .05, RIDGE - 1.1), (.09, y + .05, RIDGE - 1.1), (0, y + .05, RIDGE - 1.3)],
            [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], 'HH_Trim')
    # windows: three to the street (front gable), attic window, two on the west side, one east, one back
    sill = PL + .95
    for s in (2.0, 5.0):                                # v02: max 2 windows on the main front, balanced
        window(WALLS['front'], s, sill - .05, ww=1.1, wh=1.4)
    a = WALLS['front']
    a.rect(3.5 - .32, 3.5 + .32, EAVE + .55, EAVE + 1.35, .04, .07, 'HH_Glass')
    for s0, s1, z0, z1 in ((3.5 - .38, 3.5 + .38, EAVE + .5, EAVE + .58), (3.5 - .38, 3.5 + .38, EAVE + 1.32, EAVE + 1.4),
                           (3.5 - .38, 3.5 - .3, EAVE + .5, EAVE + 1.4), (3.5 + .3, 3.5 + .38, EAVE + .5, EAVE + 1.4), (3.48, 3.52, EAVE + .5, EAVE + 1.4)):
        a.rect(s0, s1, z0, z1, .04, .1, 'HH_Trim')
    a.tri(3.5 - .5, 3.5 + .5, EAVE + 1.4, EAVE + 1.68, .04, .1, 'HH_Trim')
    for s in (2.0, 6.0):
        window(WALLS['west'], s, sill)
    window(WALLS['east'], 6.4, sill)
    window(WALLS['back'], 4.5, sill, shutters=False)
    # door on the east side behind a porch (deck, posts, rails, steps, shed roof)
    e = WALLS['east']
    ds = 2.4
    e.rect(ds - .58, ds + .58, PL, PL + 2.2, 0, .06, 'HH_Trim')
    e.rect(ds - .46, ds + .46, PL + .02, PL + 2.08, .02, .09, 'HH_Door')
    e.rect(ds - .3, ds + .3, PL + 1.1, PL + 1.75, .09, .11, 'HH_Trim')
    y0, y1, x1 = -HY + ds - 1.4, -HY + ds + 1.4, HX + 1.9
    box(HX, x1, y0, y1, PL - .16, PL, 'HH_Wood', hull=True)
    for i in range(3):
        box(x1 + i * .3, x1 + (i + 1) * .3, -HY + ds - .65, -HY + ds + .65, 0, PL - .16 - i * .18, 'HH_Wood')
    for py in (y0 + .08, y1 - .08):
        box(x1 - .2, x1 - .06, py - .07, py + .07, PL, EAVE - .35, 'HH_Wood')
        box(HX, x1 - .06, py - .05, py + .05, PL + .95, PL + 1.03, 'HH_Wood')
        box(HX, x1 - .06, py - .04, py + .04, PL + .35, PL + .41, 'HH_Wood')
        for j in range(4):
            bx = HX + .3 + j * .38
            box(bx - .03, bx + .03, py - .03, py + .03, PL, PL + .95, 'HH_Wood')
    pr_top, pr_low = EAVE - .2, EAVE - .55
    prof = [(HX, pr_top), (x1 + .3, pr_low), (x1 + .3, pr_low + .08), (HX, pr_top + .08)]
    v = [(u, y, z) for y in (y0 - .25, y1 + .25) for u, z in prof]
    add(v, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], 'HH_Roof')
    box(x1 + .26, x1 + .32, y0 - .25, y1 + .25, pr_low - .18, pr_low + .04, 'HH_Trim')
    # brick chimney through the west slope, metal cap
    cx, cy = -.9, 1.6
    box(cx - .28, cx + .28, cy - .28, cy + .28, EAVE + .8, RIDGE + .85, 'HH_Brick')
    box(cx - .36, cx + .36, cy - .36, cy + .36, RIDGE + .85, RIDGE + .93, 'HH_RoofTrim')
    # colliders: plinth+walls body, roof prism, (porch deck added above)
    HULLS.append([(x, y, z) for x in (-HX - .12, HX + .12) for y in (-HY - .12, HY + .12) for z in (0, EAVE)])
    HULLS.append([(x, y, z) for x in (-HX - OV_E, HX + OV_E) for y in (-HY - OV_R, HY + OV_R) for z in (ze - .02, )] +
                 [(0, y, RIDGE + .2) for y in (-HY - OV_R, HY + OV_R)] + [(0, 0, EAVE - .02)])


def make_objects():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    mats = []
    for n in ORDER:
        m = bpy.data.materials.get(n) or bpy.data.materials.new(n)
        m.diffuse_color = lin(COLS[n])
        m.use_nodes = True
        bsdf = next(nd for nd in m.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = m.diffuse_color
        bsdf.inputs['Roughness'].default_value = .2 if n == 'HH_Glass' else .8
        mats.append(m)
    me = bpy.data.meshes.new(NAME + '_Mesh')
    me.from_pydata([tuple(v) for v in V], [], F)
    for m in mats:
        me.materials.append(m)
    for p, mi in zip(me.polygons, M):
        p.material_index = mi
    # box-projection UVs in metres
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            if ax == 0:
                l[uv].uv = (co.y * (1 if n.x > 0 else -1), co.z)
            elif ax == 1:
                l[uv].uv = (co.x * (-1 if n.y > 0 else 1), co.z)
            else:
                l[uv].uv = (co.x, co.y)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)          # every part is a closed solid: outward normals
    bm.normal_update(); bm.to_mesh(me); bm.free()
    root = bpy.data.objects.new(NAME, None)
    bpy.context.scene.collection.objects.link(root)
    ob = bpy.data.objects.new(NAME + '_Mesh', me)
    ob.parent = root
    bpy.context.scene.collection.objects.link(ob)
    objs = [root, ob]
    for i, pts in enumerate(HULLS):
        hm = bpy.data.meshes.new(f'UCX_{NAME}_{i:02d}')
        b2 = bmesh.new()
        for p in pts:
            b2.verts.new(p)
        bmesh.ops.convex_hull(b2, input=b2.verts)
        b2.to_mesh(hm); b2.free()
        o = bpy.data.objects.new(f'UCX_{NAME}_{i:02d}', hm)
        o.display_type = 'WIRE'; o.parent = root
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
    return root, ob, objs


def export(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / 'FBX' / (NAME + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=True,
                             object_types={'EMPTY', 'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False)


def preview(ob):
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
    except TypeError:
        pass
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True; sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1200, 800
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 32
    for o in bpy.data.objects:
        if o.name.startswith('UCX_'):
            o.hide_render = True
    for tag, pos in (('front', (11, -15, 5.5)), ('back', (-12, 13, 7))):
        cam.location = pos
        d = Vector((0, 0, 3.2)) - Vector(pos)
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(OUT / f'HH_House_v02_preview_{tag}.png')
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    root, ob, objs = make_objects()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    export(objs)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (NAME + '.blend')))
    print(f'[HH] {NAME}: {len(ob.data.vertices)} verts, {tris} tris, {len(HULLS)} UCX, ridge {RIDGE:.2f} m')
    if '--render' in sys.argv:
        preview(ob)


main()
