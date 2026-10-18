"""FACADE_KIT_v01 — modular 3D facade/roof pieces for VOLUNTEERS ONLY (Rough / Downtown / Hamlet / Generic).

Run headless:  python3 build_facade_kit_v01.py      (pip install bpy matplotlib)
Outputs next to this script: FBX/<piece>.fbx, FACADE_KIT_v01.blend, FACADE_KIT_v01_manifest.json,
FACADE_KIT_v01_contact_sheet.png.

Conventions (same family as MAP_PROPS/_lib/mapprops.py):
  * 1 unit = 1 m. Blender Z up, -Y = outward from the wall. FBX: axis_forward=-Z, axis_up=Y, bake_space_transform
    -> in Unity the piece's +Z (transform.forward) points out of the wall, +Y up.
  * Pivot on the attach plane (see manifest 'attach'): wall pieces = wall face (Y=0), centre X, bottom Z;
    roof pieces = roof surface, centre; ground pieces = ground, centre of the base.
  * Hierarchy per piece: empty <name> (pivot) -> <name>_LOD0 [, <name>_LOD1] , UCX_<name>_NN (convex colliders).
  * UV0: per-face box projection, 1 UV unit = 1 m (tiling-ready). One placeholder material per kind (FK_*).
"""
import json, math, sys
from pathlib import Path

import bpy, bmesh
from mathutils import Vector

OUT = Path(__file__).resolve().parent
FBX_DIR = OUT / 'FBX'
FBX_DIR.mkdir(exist_ok=True)

MATS = {  # placeholder colours (sRGB 0-255); textures are re-chosen later
    'FK_Concrete': (158, 155, 148), 'FK_Concrete_Dark': (112, 110, 105), 'FK_Metal_Paint': (78, 92, 88),
    'FK_Metal_Dark': (50, 52, 56), 'FK_Metal_Galv': (140, 144, 146), 'FK_Window_Frame': (226, 224, 216),
    'FK_Glass': (120, 150, 165), 'FK_Wood': (140, 102, 66), 'FK_Wood_Paint': (98, 118, 104),
    'FK_Brick': (150, 88, 70), 'FK_Stone': (196, 186, 168), 'FK_Fabric': (110, 72, 64), 'FK_Plastic': (70, 96, 72),
    'FK_Roof_Slate': (72, 78, 88), 'FK_Roof_Metal': (120, 128, 132), 'FK_Roof_Tile': (156, 84, 60),
}


def srgb_lin(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + .055) / 1.055) ** 2.4) for v in c) + (1,)


def material(name):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        m.diffuse_color = srgb_lin(MATS[name])
        m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = m.diffuse_color
    return m


# ------------------------------------------------------------------ geometry builder
class P:
    """Collects quads/ngons per material, convex collider point sets, detail flags for LOD1."""

    def __init__(self, name, region, attach, note=''):
        self.name, self.region, self.attach, self.note = name, region, attach, note
        self.parts = []          # (verts, faces, mat, detail)
        self.cols = []           # lists of points

    def add(self, v, f, mat, d=False):
        self.parts.append((v, f, mat, d))

    def box(self, x0, x1, y0, y1, z0, z1, mat, d=False, col=False):
        v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        self.add(v, f, mat, d)
        if col:
            self.cols.append(v)

    def cbox(self, cx, cy, cz, sx, sy, sz, mat, **k):  # centred box
        self.box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, mat, **k)

    def beam(self, a, b, t, mat, d=False):
        """Square bar of thickness t from point a to b (any direction)."""
        a, b = Vector(a), Vector(b)
        ax = (b - a).normalized()
        up = Vector((0, 0, 1)) if abs(ax.z) < .9 else Vector((1, 0, 0))
        u = ax.cross(up).normalized() * t / 2
        w = ax.cross(u).normalized() * t / 2
        v = [tuple(p + s1 * u + s2 * w) for p in (a, b) for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        f = [(0, 1, 2, 3)[::-1], (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mat, d)

    def cyl(self, cx, cy, z0, z1, r, mat, seg=8, d=False, col=False, axis='Z'):
        def P3(a, b, h):
            return {'Z': (cx + a, cy + b, h), 'X': (h, cx + a, cy + b), 'Y': (cx + a, h, cy + b)}[axis]
        ring = [(r * math.cos(i * math.tau / seg), r * math.sin(i * math.tau / seg)) for i in range(seg)]
        v = [P3(a, b, z0) for a, b in ring] + [P3(a, b, z1) for a, b in ring]
        f = [tuple(range(seg))[::-1], tuple(range(seg, 2 * seg))]
        f += [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
        if axis == 'Y':
            f = [t[::-1] for t in f]
        self.add(v, f, mat, d)
        if col:
            self.cols.append(v)

    def prism(self, x0, x1, prof, mat, d=False, col=False):
        """Extrude a convex YZ profile (CCW seen from +X) along X."""
        n = len(prof)
        v = [(x0, y, z) for y, z in prof] + [(x1, y, z) for y, z in prof]
        f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(v, f, mat, d)
        if col:
            self.cols.append(v)

    def collider(self, x0, x1, y0, y1, z0, z1):
        self.cols.append([(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)])


def make_mesh(name, parts):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UV0')
    mats = []
    for v, f, mat, _ in parts:
        if mat not in mats:
            mats.append(mat)
        bv = [bm.verts.new(p) for p in v]
        for face in f:
            try:
                bf = bm.faces.new([bv[i] for i in face])
            except ValueError:
                continue
            bf.material_index = mats.index(mat)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for bf in bm.faces:  # box projection, 1 UV = 1 m
        n = bf.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in bf.loops:
            c = l.vert.co
            l[uvl].uv = {0: (c.y * (1 if n.x > 0 else -1), c.z), 1: (c.x * (-1 if n.y > 0 else 1), c.z),
                         2: (c.x, c.y * (1 if n.z > 0 else -1))}[ax]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(material(m))
    for p in me.polygons:
        p.use_smooth = False
    return me


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def hull_mesh(name, pts):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


# ------------------------------------------------------------------ piece definitions
PIECES = []


def piece(name, region, attach, note=''):
    p = P(name, region, attach, note)
    PIECES.append(p)
    return p


FH_R, FH_D = 2.8, 3.5     # floor heights
PITCH_R = 3.2             # KH1b: 12.8 m texture = 4 bays x 3.2 m; 11.2 m = 4 floors x 2.8 m


def railing(p, x0, x1, y, z0, h, posts=4, mat='FK_Metal_Paint', along='X', d=False):
    """Thin railing: top rail + bottom rail + posts. along='X' at depth y, or along='Y' at x=y."""
    t = .04
    for i in range(posts + 1):
        s = x0 + (x1 - x0) * i / posts
        a = (s, y, z0) if along == 'X' else (y, s, z0)
        b = (s, y, z0 + h) if along == 'X' else (y, s, z0 + h)
        p.beam(a, b, t, mat, d=d and 0 < i < posts)
    for zz in (z0 + h, z0 + .12):
        a = (x0, y, zz) if along == 'X' else (y, x0, zz)
        b = (x1, y, zz) if along == 'X' else (y, x1, zz)
        p.beam(a, b, .05, mat)


# ---- Rough (khrushchevka) -------------------------------------------------------------
def rough():
    W, D = 2.6, 1.0
    p = piece('FK_R_Balcony_Open', 'Rough', 'wall', 'slab at floor level; pivot = wall face, slab top centre-bottom')
    p.box(-W / 2, W / 2, -D, 0, -.16, 0, 'FK_Concrete', col=True)
    p.box(-W / 2, W / 2, -D, -D + .06, 0, 1.0, 'FK_Metal_Paint')          # sheet front (ribbed look via panels)
    p.box(-W / 2, -W / 2 + .06, -D, 0, 0, 1.0, 'FK_Metal_Paint')
    p.box(W / 2 - .06, W / 2, -D, 0, 0, 1.0, 'FK_Metal_Paint')
    p.box(-W / 2 - .02, W / 2 + .02, -D - .03, 0, 1.0, 1.06, 'FK_Metal_Dark')  # handrail cap
    for i in range(1, 6):
        x = -W / 2 + W * i / 6
        p.box(x - .03, x + .03, -D - .03, -D, .05, .98, 'FK_Metal_Dark', d=True)
    p.collider(-W / 2, W / 2, -D - .03, 0, 0, 1.06)   # solid, not walk-in (spec: impassable)
    q = piece('FK_R_Balcony_Glazed', 'Rough', 'wall', 'glazed loggia-style; frame up to next slab underside')
    q.box(-W / 2, W / 2, -D, 0, -.16, 0, 'FK_Concrete', col=True)
    q.box(-W / 2, W / 2, -D, -D + .08, 0, .95, 'FK_Concrete_Dark')
    for x0 in (-W / 2, W / 2 - .08):
        q.box(x0, x0 + .08, -D, 0, 0, .95, 'FK_Concrete_Dark')
    H = FH_R - .16
    q.box(-W / 2, W / 2, -D, -D + .08, .95, .99, 'FK_Window_Frame')
    q.box(-W / 2, W / 2, -D, 0, H - .06, H, 'FK_Window_Frame')
    q.box(-W / 2, W / 2, -D + .02, -D + .05, .99, H - .06, 'FK_Glass')
    for i in range(5):
        x = -W / 2 + W * i / 4
        q.box(x - .03, x + .03, -D, -D + .08, .99, H - .06, 'FK_Window_Frame')
    for x0 in (-W / 2, W / 2 - .05):
        q.box(x0, x0 + .05, -D, 0, .99, H - .06, 'FK_Glass')
    q.box(-W / 2 - .05, W / 2 + .05, -D - .12, 0, H, H + .05, 'FK_Metal_Galv')   # tin drip roof
    q.collider(-W / 2 - .05, W / 2 + .05, -D - .12, 0, 0, H + .05)
    # entrance canopy (concrete slab on two brackets)
    c = piece('FK_R_Entrance_Canopy', 'Rough', 'wall', 'pivot = wall face, canopy underside centre; mount at 2.4 m')
    c.box(-1.2, 1.2, -1.4, 0, 0, .14, 'FK_Concrete', col=True)
    c.box(-1.22, 1.22, -1.42, 0, .14, .17, 'FK_Metal_Galv')
    for x in (-1.0, 1.0):
        c.prism(x - .06, x + .06, [(0, -.9), (0, 0), (-1.1, 0)], 'FK_Concrete_Dark', col=True)
    for n, k in (('FK_R_Entrance_Steps2', 2), ('FK_R_Entrance_Steps3', 3)):
        s = piece(n, 'Rough', 'wall+ground', 'pivot = wall face at ground; top = door threshold (0.16 m/step)')
        rh, tr = .16, .32
        s.box(-1.1, 1.1, -tr * k - .9, 0, 0, rh * k, 'FK_Concrete', col=False)  # landing+core block below
        s.parts.pop()
        s.box(-1.1, 1.1, -.9, 0, 0, rh * k, 'FK_Concrete', col=True)            # landing 0.9 m deep
        for i in range(k - 1):
            y1 = -.9 - tr * i
            s.box(-1.0, 1.0, y1 - tr, y1, 0, rh * (k - 1 - i), 'FK_Concrete', col=True)
        s.box(-1.1, 1.1, -.9 - .02, 0, rh * k - .03, rh * k, 'FK_Concrete_Dark', d=True)
        if k == 3:
            s.parts[-1] = s.parts[-1]
    dr = piece('FK_R_IronDoor', 'Rough', 'wall', 'door 1.2x2.2 m set 0.1 m into wall; pivot = wall face, sill centre')
    dr.box(-.72, .72, -.06, 0, 0, 2.32, 'FK_Metal_Dark')                     # frame (front plate)
    dr.box(-.6, .6, -.02, .1, 0, 2.2, 'FK_Metal_Paint')                       # leaf, recessed
    dr.box(-.72, .72, -.06, .1, 2.2, 2.32, 'FK_Metal_Dark')
    dr.box(-.5, -.42, -.07, -.02, 1.0, 1.08, 'FK_Metal_Galv', d=True)        # handle
    dr.box(.38, .52, -.07, -.06, 1.35, 1.55, 'FK_Metal_Galv', d=True)        # intercom
    dr.collider(-.72, .72, -.07, .1, 0, 2.32)
    w = piece('FK_R_Window_Frame', 'Rough', 'wall', 'opening 1.5x1.45 m, sill at +0.85 above floor; pivot = wall face, opening bottom centre')
    ww, wh = 1.5, 1.45
    w.box(-ww / 2, ww / 2, -.04, .06, -.06, 0, 'FK_Window_Frame')
    w.box(-ww / 2, ww / 2, -.04, .06, wh, wh + .06, 'FK_Window_Frame')
    for x in (-ww / 2, -.02 - .0, ww / 2 - .06):
        w.box(x, x + .06, -.04, .06, 0, wh, 'FK_Window_Frame')
    w.box(-ww / 2, ww / 2, .04, .05, 0, wh, 'FK_Glass')
    w.box(-ww / 2 - .06, ww / 2 + .06, -.18, .04, -.1, -.06, 'FK_Metal_Galv')  # tin sill
    w.collider(-ww / 2 - .06, ww / 2 + .06, -.18, .06, -.1, wh + .06)
    dp = piece('FK_R_Drainpipe_2m8', 'Rough', 'wall', 'one floor (2.8 m) stackable; pivot = wall face, bottom')
    dp.cyl(0, -.14, 0, FH_R, .055, 'FK_Metal_Galv', seg=8)
    for z in (.3, 2.3):
        dp.box(-.07, .07, -.14, 0, z, z + .04, 'FK_Metal_Dark', d=True)
    dp.collider(-.06, .06, -.2, 0, 0, FH_R)
    pp = piece('FK_R_Parapet_3m2', 'Rough', 'roof-edge', 'one bay (3.2 m); pivot = roof edge top of wall, outer face')
    pp.box(-1.6, 1.6, 0, .2, 0, .6, 'FK_Concrete', col=True)
    pp.box(-1.62, 1.62, -.04, .24, .6, .64, 'FK_Metal_Galv')
    rv = piece('FK_R_Roof_Vent', 'Rough', 'roof', 'brick vent stack with cap; pivot = roof surface centre')
    rv.box(-.4, .4, -.3, .3, 0, 1.1, 'FK_Brick', col=True)
    rv.box(-.5, .5, -.4, .4, 1.3, 1.38, 'FK_Concrete_Dark')
    for x in (-.4, .34):
        rv.box(x, x + .06, -.3, .3, 1.1, 1.3, 'FK_Concrete_Dark')
    rv.collider(-.5, .5, -.4, .4, 1.1, 1.38)


# ---- Downtown --------------------------------------------------------------------------
def downtown():
    LW, LD = 2.8, 1.3      # landing width/depth
    f = piece('FK_D_FireEscape_Landing', 'Downtown', 'wall', 'stack every 3.5 m; landing top at floor+1.0? no: top = pivot Z; pivot = wall face, landing top centre')
    f.box(-LW / 2, LW / 2, -LD, 0, -.08, 0, 'FK_Metal_Dark', col=True)
    for i in range(1, 7):  # grating ribs
        x = -LW / 2 + LW * i / 7
        f.box(x - .015, x + .015, -LD, 0, -.12, -.08, 'FK_Metal_Dark', d=True)
    railing(f, -LW / 2, LW / 2, -LD, 0, 1.0, posts=4, mat='FK_Metal_Dark')
    railing(f, -LD, 0, -LW / 2, 0, 1.0, posts=2, mat='FK_Metal_Dark', along='Y')
    railing(f, -LD, 0, LW / 2, 0, 1.0, posts=2, mat='FK_Metal_Dark', along='Y')
    for x in (-LW / 2 + .1, LW / 2 - .1):
        f.beam((x, -LD + .05, -.08), (x, -.02, -.8), .05, 'FK_Metal_Dark')
    f.collider(-LW / 2, LW / 2, -LD - .03, -LD + .03, 0, 1.0)       # railings as thin boxes
    f.collider(-LW / 2 - .03, -LW / 2 + .03, -LD, 0, 0, 1.0)
    f.collider(LW / 2 - .03, LW / 2 + .03, -LD, 0, 0, 1.0)
    s = piece('FK_D_FireEscape_Stair', 'Downtown', 'wall', 'flight between landings (3.5 m rise, 2.4 m run); pivot = wall face, bottom landing top; place at landing X')
    run, rise, sw = 2.4, FH_D, .7
    y0, y1 = -LD + .05, -LD + .05 + sw
    n = 10
    for side in (y0, y1):
        s.beam((-run / 2, side, 0), (run / 2, side, rise), .08, 'FK_Metal_Dark')
        s.beam((-run / 2, side, 1.0), (run / 2, side, rise + 1.0), .04, 'FK_Metal_Dark')
    for i in range(1, n):
        x, z = -run / 2 + run * i / n, rise * i / n
        s.box(x - .1, x + .1, y0, y1, z - .03, z, 'FK_Metal_Dark', d=True)
    s.cols.append([(-run / 2, y0, -.05), (-run / 2, y1, -.05), (-run / 2, y0, .1), (-run / 2, y1, .1),
                   (run / 2, y0, rise - .05), (run / 2, y1, rise - .05), (run / 2, y0, rise + 1.0), (run / 2, y1, rise + 1.0),
                   (-run / 2, y0, 1.0), (-run / 2, y1, 1.0)])
    l = piece('FK_D_FireEscape_Ladder', 'Downtown', 'wall', 'drop ladder under lowest landing, 3.0 m; pivot = wall face, top; hangs down to -3.0')
    for x in (-.22, .22):
        l.beam((x, -LD + .1, 0), (x, -LD + .1, -3.0), .04, 'FK_Metal_Dark')
    for i in range(1, 10):
        l.beam((-.22, -LD + .1, -i * .3), (.22, -LD + .1, -i * .3), .025, 'FK_Metal_Dark', d=True)
    l.collider(-.25, .25, -LD + .06, -LD + .14, -3.0, 0)
    w = piece('FK_D_Window_Frame', 'Downtown', 'wall', 'opening 1.2x1.8 m, sill +0.9 above floor; stone sill + lintel; pivot = wall face, opening bottom centre')
    ww, wh = 1.2, 1.8
    w.box(-ww / 2, ww / 2, -.03, .08, -.05, 0, 'FK_Window_Frame')
    w.box(-ww / 2, ww / 2, -.03, .08, wh, wh + .05, 'FK_Window_Frame')
    for x in (-ww / 2, ww / 2 - .05):
        w.box(x, x + .05, -.03, .08, 0, wh, 'FK_Window_Frame')
    w.box(-ww / 2, ww / 2, -.03, .03, wh * .55, wh * .55 + .05, 'FK_Window_Frame', d=True)
    w.box(-ww / 2, ww / 2, .05, .06, 0, wh, 'FK_Glass')
    w.box(-ww / 2 - .1, ww / 2 + .1, -.12, .03, -.14, -.05, 'FK_Stone')       # sill
    w.box(-ww / 2 - .15, ww / 2 + .15, -.08, .03, wh + .05, wh + .3, 'FK_Stone')  # lintel
    w.box(-.12, .12, -.1, -.08, wh + .05, wh + .32, 'FK_Stone', d=True)       # keystone
    w.collider(-ww / 2 - .15, ww / 2 + .15, -.12, .08, -.14, wh + .32)
    c = piece('FK_D_Cornice_2m', 'Downtown', 'roof-edge', 'tiles every 2 m along the top of the wall; pivot = wall face, cornice bottom centre')
    c.prism(-1, 1, [(0, 0), (0, .55), (-.55, .55), (-.55, .45), (-.25, .15), (-.12, 0)], 'FK_Stone', col=True)
    for x in (-.75, -.25, .25, .75):
        c.box(x - .06, x + .06, -.3, 0, .05, .3, 'FK_Stone', d=True)           # dentils/brackets
    a = piece('FK_D_AC_Unit', 'Downtown', 'wall', 'window AC box on bracket; pivot = wall face, bottom centre')
    a.box(-.4, .4, -.55, -.05, .05, .5, 'FK_Metal_Galv', col=True)
    a.box(-.35, .35, -.56, -.55, .1, .45, 'FK_Metal_Dark', d=True)
    for x in (-.32, .32):
        a.beam((x, -.5, .05), (x, 0, -.3), .04, 'FK_Metal_Dark')
        a.box(x - .02, x + .02, -.55, 0, .01, .05, 'FK_Metal_Dark')
    t = piece('FK_D_RoofWaterTank', 'Downtown', 'roof', 'wooden tank (D 2.6, H 2.8) on 4-leg stand 2.2 m; pivot = roof surface centre')
    t.cyl(0, 0, 2.3, 5.1, 1.3, 'FK_Wood', seg=12, col=True)
    for z in (2.7, 3.7, 4.7):
        t.cyl(0, 0, z, z + .08, 1.33, 'FK_Metal_Dark', seg=12, d=True)
    t.add([(0, 0, 6.0)] + [(1.45 * math.cos(i * math.tau / 12), 1.45 * math.sin(i * math.tau / 12), 5.1) for i in range(12)],
          [(0, i % 12 + 1, (i + 1) % 12 + 1) for i in range(12)] + [tuple(range(12, 0, -1))], 'FK_Wood')
    t.cols.append([(0, 0, 6.0)] + [(1.45 * math.cos(i * math.tau / 12), 1.45 * math.sin(i * math.tau / 12), 5.1) for i in range(12)])
    t.box(-1.2, 1.2, -1.2, 1.2, 2.15, 2.3, 'FK_Metal_Dark', col=True)
    for x in (-1, 1):
        for y in (-1, 1):
            t.box(x * .95 - .08, x * .95 + .08, y * .95 - .08, y * .95 + .08, 0, 2.15, 'FK_Metal_Dark', col=True)
    for y in (-.95, .95):
        t.beam((-.95, y, .2), (.95, y, 2.0), .05, 'FK_Metal_Dark', d=True)
    pp = piece('FK_D_Parapet_2m', 'Downtown', 'roof-edge', 'brick parapet with stone coping; pivot = wall outer face, roof-edge top')
    pp.box(-1, 1, 0, .3, 0, .9, 'FK_Brick', col=True)
    pp.box(-1, 1, -.05, .35, .9, 1.0, 'FK_Stone')
    aw = piece('FK_D_Storefront_Awning', 'Downtown', 'wall', 'fabric awning 3.0 m wide, 1.2 m projection; pivot = wall face, top centre; mount ~3.0 m')
    aw.prism(-1.5, 1.5, [(0, 0), (-1.2, -.7), (-1.2, -.95), (-1.18, -.95), (-1.18, -.72), (0, -.03)][::-1], 'FK_Fabric')
    aw.box(-1.5, 1.5, -1.22, -1.18, -.98, -.7, 'FK_Fabric')
    for x in (-1.45, 1.45):
        aw.beam((x, -1.2, -.7), (x, 0, -.9), .03, 'FK_Metal_Dark', d=True)
    aw.cols.append([(-1.5, 0, 0), (1.5, 0, 0), (-1.5, 0, -.1), (1.5, 0, -.1), (-1.5, -1.22, -.7), (1.5, -1.22, -.7),
                    (-1.5, -1.22, -.98), (1.5, -1.22, -.98)])
    dm = piece('FK_D_Dumpster', 'Downtown', 'ground', 'alley dumpster 1.9x1.1x1.3; pivot = ground, base centre; front = -Y')
    dm.box(-.95, .95, -.5, .55, .12, 1.15, 'FK_Plastic', col=True)
    dm.prism(-.97, .97, [(-.58, 1.15), (.6, 1.15), (.6, 1.32), (-.58, 1.2)], 'FK_Metal_Dark', col=True)
    dm.box(-.97, .97, -.56, -.5, .9, 1.0, 'FK_Metal_Dark', d=True)
    dm.box(-.97, .97, -.56, -.5, .3, .38, 'FK_Metal_Dark', d=True)
    for x in (-.75, .75):
        for y in (-.35, .4):
            dm.cyl(x, y, 0, .12, .08, 'FK_Metal_Dark', seg=6, d=True)
    dm.collider(-.95, .95, -.5, .55, 0, .12)


# ---- Hamlet -----------------------------------------------------------------------------
def hamlet():
    pr = piece('FK_H_PorchRoof', 'Hamlet', 'wall', '3.0 m wide, 1.8 m deep lean-to with 2 posts; pivot = wall face at ground, centre')
    pr.prism(-1.6, 1.6, [(0, 2.95), (0, 3.05), (-1.95, 2.45), (-1.95, 2.35)], 'FK_Roof_Metal', col=True)
    for x in (-1.4, 1.4):
        pr.box(x - .07, x + .07, -1.77, -1.63, 0, 2.42, 'FK_Wood', col=True)
    pr.box(-1.5, 1.5, -1.78, -1.62, 2.28, 2.42, 'FK_Wood')
    for x in (-1.4, 1.4):
        pr.beam((x, -1.7, 1.95), (x, -1.35, 2.35), .06, 'FK_Wood', d=True)
    sh = piece('FK_H_Window_Shutters', 'Hamlet', 'wall', 'opening 1.0x1.2 m, carved trim + open shutters; pivot = wall face, opening bottom centre')
    sh.box(-.5, .5, -.03, .05, -.04, 0, 'FK_Window_Frame')
    sh.box(-.5, .5, -.03, .05, 1.2, 1.24, 'FK_Window_Frame')
    for x in (-.54, -.02, .5):
        sh.box(x, x + .04, -.03, .05, 0, 1.2, 'FK_Window_Frame')
    sh.box(-.5, .5, .03, .04, 0, 1.2, 'FK_Glass')
    sh.box(-.62, .62, -.08, 0, 1.24, 1.42, 'FK_Wood_Paint')                  # top board
    sh.prism(-.62, .62, [(0, 1.42), (-.08, 1.42), (0, 1.55)][::-1], 'FK_Wood_Paint')
    sh.box(-.62, .62, -.15, 0, -.12, -.04, 'FK_Wood_Paint')                  # sill board
    for x in (-1.06, .56):
        sh.box(x, x + .5, -.06, -.02, 0, 1.2, 'FK_Wood_Paint')
        sh.box(x + .05, x + .45, -.07, -.06, .55, .65, 'FK_Wood', d=True)
    sh.collider(-1.06, 1.06, -.15, .05, -.12, 1.55)
    st = piece('FK_H_Steps', 'Hamlet', 'wall+ground', 'wooden 3-step stoop, rise 0.18; pivot = wall face at ground, centre')
    for i in range(3):
        st.box(-.6, .6, -.3 * (3 - i), -.3 * (2 - i) + (0 if i < 2 else 0), .18 * i, .18 * (i + 1), 'FK_Wood', col=False)
    st.parts.clear()
    for i in range(3):
        y = -.3 * (3 - i)
        st.box(-.6, .6, y, 0, .18 * i, .18 * (i + 1), 'FK_Wood', col=True)
    for x in (-.62, .58):
        st.prism(x, x + .04, [(-.9, 0), (0, 0), (0, .56)][::-1], 'FK_Wood_Paint', d=True)
    ch = piece('FK_H_Chimney', 'Hamlet', 'roof', 'brick chimney 0.6x0.6x1.6 above ridge zone, base sunk 0.6 m into roof; pivot = roof surface centre')
    ch.box(-.3, .3, -.3, .3, -.6, 1.4, 'FK_Brick', col=True)
    ch.box(-.36, .36, -.36, .36, 1.4, 1.52, 'FK_Brick', col=True)
    ch.box(-.2, .2, -.2, .2, 1.52, 1.6, 'FK_Metal_Dark', d=True)
    gt = piece('FK_H_Gutter_2m', 'Hamlet', 'eave', 'half-round (6-seg) gutter 2 m; pivot = eave line, centre')
    prof = [(-.06 * math.cos(a), -.06 * math.sin(a) - .0) for a in (0, .5, 1.0, 1.6, 2.1, 2.6, math.pi)]
    gt.prism(-1, 1, [(y - .07, z) for y, z in [(.06, 0), (-.0, -.06), (-.06, -.03), (-.06, 0)]][::-1], 'FK_Metal_Galv')
    for x in (-.8, .8):
        gt.box(x - .02, x + .02, -.14, 0, -.01, .01, 'FK_Metal_Dark', d=True)
    gt.collider(-1, 1, -.14, 0, -.07, 0)


# ---- Generic ridge caps -------------------------------------------------------------------
def ridges():
    for kind, mat, prof in (
            ('Slate', 'FK_Roof_Slate', [(-.2, -.12), (-.2, -.07), (0, .05), (.2, -.07), (.2, -.12), (0, -.0)]),
            ('Metal', 'FK_Roof_Metal', [(-.22, -.1), (-.22, -.08), (0, .03), (.22, -.08), (.22, -.1), (0, .01)]),
            ('Tile', 'FK_Roof_Tile', None)):
        p = piece(f'FK_G_RidgeCap_{kind}_2m', 'Generic', 'ridge', '2 m segment; pivot = ridge line (roof apex), centre; X = along ridge')
        if prof:
            prof = [prof[0], prof[1], prof[2], prof[3], prof[4]]
            p.prism(-1, 1, prof[::-1] if False else prof, mat)
            p.parts[-1] = (p.parts[-1][0], [f[::-1] for f in p.parts[-1][1]], mat, False)
        else:  # half-round tiles (8-seg arcs), 4 per 2 m with overlaps
            for i in range(4):
                x = -1 + i * .5
                arc = [(.15 * math.cos(a), .15 * math.sin(a) - .07) for a in [k * math.pi / 6 for k in range(7)]]
                p.prism(x, x + .52, arc, mat)
        # collider: wedge matching a 30-45 deg roof apex + cap (the "ridge gap" fix, see ROOF_COLLISION_NOTE.md)
        p.cols.append([(x, y, z) for x in (-1, 1) for y, z in ((-.25, -.2), (.25, -.2), (0, .09))])


# ------------------------------------------------------------------ build / export
def build_object(p, coll):
    root = bpy.data.objects.new(p.name, None)
    root.empty_display_size = .3
    coll.objects.link(root)
    me0 = make_mesh(p.name + '_LOD0', p.parts)
    t0 = tris(me0)
    objs = [root]
    lod0 = bpy.data.objects.new(p.name + ('_LOD0' if t0 > 150 else ''), me0)
    if t0 <= 150:
        lod0.name = p.name + '_Mesh'
    lod0.parent = root
    coll.objects.link(lod0)
    objs.append(lod0)
    t1 = None
    if t0 > 150:
        me1 = make_mesh(p.name + '_LOD1', [x for x in p.parts if not x[3]])
        t1 = tris(me1)
        if t1 > t0 * .8:  # detail flags not enough -> collapse decimate
            o = bpy.data.objects.new('tmp', me1)
            coll.objects.link(o)
            m = o.modifiers.new('d', 'DECIMATE')
            m.ratio = .5
            dg = bpy.context.evaluated_depsgraph_get()
            me1 = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            bpy.data.objects.remove(o)
            t1 = tris(me1)
        lod1 = bpy.data.objects.new(p.name + '_LOD1', me1)
        lod1.parent = root
        coll.objects.link(lod1)
        objs.append(lod1)
    for i, pts in enumerate(p.cols):
        o = bpy.data.objects.new(f'UCX_{p.name}_{i:02d}', hull_mesh(f'UCX_{p.name}_{i:02d}', pts))
        o.display_type = 'WIRE'
        o.parent = root
        coll.objects.link(o)
        objs.append(o)
    bb = [Vector(v) for x in p.parts for v in x[0]]
    mn = Vector([min(v[i] for v in bb) for i in range(3)])
    mx = Vector([max(v[i] for v in bb) for i in range(3)])
    assert t0 <= 600, (p.name, t0)
    assert p.cols, p.name
    return root, objs, dict(
        name=p.name, region=p.region, attach=p.attach, note=p.note, tris_lod0=t0, tris_lod1=t1,
        colliders=len(p.cols), materials=sorted({x[2] for x in p.parts}),
        size_m=[round(mx[i] - mn[i], 3) for i in range(3)],
        bounds_min_blender=[round(v, 3) for v in mn], bounds_max_blender=[round(v, 3) for v in mx],
        pivot='origin = attach plane (see attach); Blender -Y / Unity +Z = outward', fbx=f'FBX/{p.name}.fbx')


def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=True,
                             object_types={'EMPTY', 'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.scale_length = 1
    rough(); downtown(); hamlet(); ridges()
    coll = bpy.data.collections.new('FACADE_KIT_v01')
    bpy.context.scene.collection.children.link(coll)
    manifest, roots = [], []
    for i, p in enumerate(PIECES):
        root, objs, info = build_object(p, coll)
        export(objs, FBX_DIR / f'{p.name}.fbx')
        manifest.append(info)
        roots.append((root, p))
    # lay pieces out in a review row (library .blend), after FBX export so pivots stay at origin in FBX
    for i, (root, p) in enumerate(roots):
        root.location = ((i % 8) * 4.0, -(i // 8) * 8.0, 0)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'FACADE_KIT_v01.blend'), compress=True)
    meta = dict(kit='FACADE_KIT_v01', units='1 unit = 1 m', axes='FBX -Z forward, Y up; Unity +Z = out of wall',
                floor_height=dict(Rough=FH_R, Downtown=FH_D),
                rough_grid=dict(texture='KH1b 12.8 x 11.2 m', bay_pitch_m=PITCH_R, bays_per_tile=4, floors_per_tile=4,
                                window_sill_above_floor=.85, window_centre_in_bay=1.6),
                lod_rule='pieces > 150 tris have _LOD0/_LOD1 children; others a single _Mesh',
                collider_rule='UCX_<piece>_NN = convex hull meshes; Unity builder: MeshCollider(convex) + no renderer',
                pieces=manifest)
    (OUT / 'FACADE_KIT_v01_manifest.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    # triangles for the contact sheet
    dump = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for root, p in roots:
        root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    for root, p in roots:
        ob = [c for c in root.children if not c.name.startswith(('UCX_', p.name + '_LOD1'))][0]
        me = ob.data
        me.calc_loop_triangles()
        cols = [tuple(m.diffuse_color[:3]) for m in me.materials]
        dump[p.name] = [[[tuple(me.vertices[v].co) for v in t.vertices], cols[me.polygons[t.polygon_index].material_index]]
                        for t in me.loop_triangles]
    return dump, manifest


if __name__ == '__main__':
    dump, manifest = main()
    sys.path.insert(0, str(OUT))
    import contact_sheet
    contact_sheet.render(dump, manifest, OUT / 'FACADE_KIT_v01_contact_sheet.png')
    print('pieces', len(manifest), 'max tris', max(m['tris_lod0'] for m in manifest))
