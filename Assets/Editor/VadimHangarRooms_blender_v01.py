"""VadimHangarRooms - Blender part (v01, 2026-10-30).

Builds the two hangar rooms of the V2 base from Fedya's v1 assets, re-dressed to docs/specs/HANGAR_ROOMS_STYLE_2026-10-30.md
and the shape rules of docs/ArtDirection.md section 2 (chunky parts, bevelled hard surfaces, real 3D details):

  workshop : VAN UPGRADES bay, 17 x 10 x 6 m, 8 x 4.4 m roller door in the front wall (v1 Workshop_W86 props + a widened copy
             of the two-post lift so the van v05 fits between the posts)
  pharmacy : PHARMACY, 11 x 7 x 4.2 m, sales floor only (v1 Pharmacy_W86 counter line set into the front wall as the
             window-counter, wall shelving, back cabinets, fridge, two stock racks)

Output: one geometry JSON per room (meshes per part with material ROLE names, colliders, lights, anchors) that
Assets/Editor/VadimHangarRooms.cs turns into meshes, materials and the prefab. The v1 FBX files are only read.

Blender frame: origin = the room's floor centre, +Y = front (hall side), Z up.  Unity = (x, z, y) (winding reversed).
Run:  blender -b --factory-startup -P VadimHangarRooms_blender_v01.py -- [workshop|pharmacy|both] [--out ROOMS_DIR] [--preview DIR]
(ROOMS_DIR defaults to Assets/VadimLocal/Hangar/Rooms next to this script's Assets folder.)
"""
import bpy
import bmesh
import sys
import os
import json
import math
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ROOT = r'C:\Users\chern_0eqkb03\Desktop\GAME'
WS_SRC = ROOT + r'\ArtSource\Buildings\Workshop_W86'
PH_SRC = ROOT + r'\ArtSource\Buildings\Pharmacy_W86'
_script = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a in ('-P', '--python')), '')
OUT_DIR = ARGS[ARGS.index('--out') + 1] if '--out' in ARGS else \
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(_script))), 'VadimLocal', 'Hangar', 'Rooms')
PREVIEW = ARGS[ARGS.index('--preview') + 1] if '--preview' in ARGS else None
WHICH = [a for a in ARGS if a in ('workshop', 'pharmacy', 'both')] or ['both']
WHICH = ['workshop', 'pharmacy'] if WHICH[0] == 'both' else WHICH

LOG = []


def log(s):
    LOG.append(s)
    print('[rooms] ' + s)


# ------------------------------------------------------------------------------------------------ material roles
# Every face carries a ROLE; VadimHangarRooms.cs maps it to a shared hangar material (texture set 45) or a per-room colour.
PREVIEW_COL = {
    'Floor': '#76695B', 'Corrugated': '#8C8276', 'Graphite': '#3A3B3D', 'RoofIn': '#3B3835', 'Roller': '#6E6A66',
    'Hazard': '#C89A20', 'Wood': '#8A6646', 'Olive': '#5C5E44', 'LightWood': '#B88A50', 'Sign': '#2A2622',
    'Rubber': '#161616', 'Glass': '#9DB0B4', 'Lamp': '#FFE2B0', 'Fabric': '#61331C', 'Accent': '#9A4A36',
    'OffWhite': '#D9CDB4', 'Steel': '#8E9396', 'Yellow': '#DBF238', 'Cardboard': '#A8895F', 'Labels': '#E8E2D4',
    'CorrWS': '#A3A8AB',
}
# Roles in use (Vadim 30.10 night): the workshop keeps the v1 look, grey corrugated sheet (CorrWS = a copy of Fedya's
# WS86_corrugated_grey_v01, T7_metal_trapez albedo + normal) with oxide-red steel; the pharmacy is its own smooth
# off-white panel box with pharmacy green. No wood cladding and no striped textures (07 wood, 06 hazard, 03 hangar
# corrugated are not used); Yellow is the hall's lemon marking yellow that still reads yellow under 3000 K.

WS_MAP = {  # v1 workshop material -> role
    'MAT_WS_red_steel': 'Accent', 'MAT_WS_metal_dark': 'Graphite', 'MAT_WS_metal_worn': 'Steel',
    'MAT_WS_yellow_rail': 'Yellow', 'MAT_WS_rubber': 'Rubber', 'MAT_WS_wood': 'LightWood', 'MAT_WS_cardboard': 'Cardboard',
    'MAT_WS_paint_white': 'OffWhite', 'MAT_WS_emissive': 'Lamp', 'MAT_WS_fabric': 'Fabric', 'MAT_WS_glass': 'Glass',
    'MAT_WS_corrugated_grey': 'CorrWS', 'MAT_WS_brick': 'Graphite', 'MAT_WS_concrete': 'Floor', 'MAT_WS_oil': None,
}
PH_MAP = {  # v1 pharmacy material -> role (turquoise -> pharmacy green accent, white/cream -> warm off-white)
    'MAT_PH_turquoise_paint': 'Accent', 'MAT_PH_wall_turquoise': 'Accent', 'MAT_PH_green': 'Accent',
    'MAT_PH_offwhite': 'OffWhite', 'MAT_PH_laminate': 'OffWhite', 'MAT_PH_wall_cream': 'OffWhite', 'MAT_PH_ceramic': 'OffWhite',
    'MAT_PH_metal': 'Steel', 'MAT_PH_dark': 'Graphite', 'MAT_PH_glass': 'Glass', 'MAT_PH_emissive': 'Lamp',
    'MAT_PH_rubber': 'Rubber', 'MAT_PH_labels': 'Labels', 'MAT_PH_cardboard': 'Cardboard', 'MAT_PH_wood': 'LightWood',
    'MAT_PH_tile_floor': 'Floor', 'MAT_PH_cross_glow': 'Accent', 'MAT_PH_facade_greyblue': 'Graphite', 'MAT_PH_concrete': 'Floor',
    'MAT_PH_wall_green': 'Accent',
}
NO_CHUNK = {'Labels', 'Glass', 'Lamp', 'Sign'}   # islands with these roles keep their shape (labels, panes, diffusers)


def base_mat_name(n):
    return n.split('.')[0]


# ------------------------------------------------------------------------------------------------ parts
class Part:
    """One output object: a bmesh in its local frame (relative to pivot), faces tagged with role indices."""

    def __init__(self, name, group, layer='room', pivot=(0, 0, 0), hero=False, static=True, smooth=None):
        self.name, self.group, self.layer, self.hero, self.static = name, group, layer, hero, static
        self.pivot = Vector(pivot)
        self.smooth = smooth            # None = flat shading; else sharp-edge angle (deg) + weighted normals
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UV0')
        self.lock = self.bm.faces.layers.int.new('uvlock')
        self.roles = []

    def ri(self, role):
        if role not in self.roles:
            self.roles.append(role)
        return self.roles.index(role)

    def bounds(self):
        cs = [v.co for v in self.bm.verts]
        return (Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs))),
                Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs))))


PARTS, COLLIDERS, LIGHTS, ANCHORS = [], [], [], []


def new_part(*a, **k):
    p = Part(*a, **k)
    if any(q.name == p.name for q in PARTS):
        raise ValueError('duplicate part name ' + p.name)
    PARTS.append(p)
    return p


def planar_uv(p, n):
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        return (p.x, p.y)
    if ax >= ay:
        return (p.y if n.x > 0 else -p.y, p.z)
    return (-p.x if n.y > 0 else p.x, p.z)


def face(part, pts, role, uvs=None):
    bm = part.bm
    vs = [bm.verts.new(Vector(p)) for p in pts]
    f = bm.faces.new(vs)
    f.material_index = part.ri(role)
    f.normal_update()
    if uvs is None:
        for l in f.loops:
            l[part.uv].uv = planar_uv(l.vert.co, f.normal)
    else:
        for l, uv in zip(f.loops, uvs):
            l[part.uv].uv = uv
        f[part.lock] = 1
    return f


PX, NX, PY, NY, PZ, NZ = 1, 2, 4, 8, 16, 32
ALL = 63


def box(part, mn, mx, role, faces=ALL, bevel=0.0, seg=1):
    """Welded axis-aligned box (min, max); faces = which sides; optional chamfer (clamped to 30 % of the thinnest side);
    metric planar UVs per face (1 UV = 1 m)."""
    bm = part.bm
    (x0, y0, z0), (x1, y1, z1) = mn, mx
    if x1 - x0 < 1e-5 or y1 - y0 < 1e-5 or z1 - z0 < 1e-5:
        return []
    co = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    v = [bm.verts.new(c) for c in co]
    spec = [(NZ, (0, 3, 2, 1)), (PZ, (4, 5, 6, 7)), (NY, (0, 1, 5, 4)), (PY, (2, 3, 7, 6)), (NX, (3, 0, 4, 7)), (PX, (1, 2, 6, 5))]
    fs = []
    for bit, idx in spec:
        if faces & bit:
            f = bm.faces.new([v[i] for i in idx])
            f.material_index = part.ri(role)
            fs.append(f)
    for vv in v:
        if not vv.link_faces:
            bm.verts.remove(vv)
    if bevel > 0 and len(fs) >= 2:
        edges = list({e for f in fs for e in f.edges if len(e.link_faces) == 2})
        w = min(bevel, min(x1 - x0, y1 - y0, z1 - z0) * 0.3)
        if w > 0.004 and edges:
            res = bmesh.ops.bevel(bm, geom=edges, offset=w, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
            fs = fs + list(res.get('faces', []))
    for f in fs:
        if f.is_valid:
            f.normal_update()
            for l in f.loops:
                l[part.uv].uv = planar_uv(l.vert.co, f.normal)
    return fs


def cyl(part, base, r0, r1, h, sides, role, top=True, bottom=False, inner=False):
    """Vertical frustum from base (radius r0) to base + h (radius r1); flat facets, metric UVs."""
    def P(a, r, t):
        return Vector((base[0] + math.cos(a) * r, base[1] + math.sin(a) * r, base[2] + t))
    for i in range(sides):
        a0, a1 = i * 2 * math.pi / sides, (i + 1) * 2 * math.pi / sides
        q = [P(a0, r0, 0), P(a1, r0, 0), P(a1, r1, h), P(a0, r1, h)]
        uvs = [(a0 * r0, 0), (a1 * r0, 0), (a1 * r1, h), (a0 * r1, h)]
        face(part, q, role, uvs)
        if inner:
            face(part, [q[0], q[3], q[2], q[1]], role, [uvs[0], uvs[3], uvs[2], uvs[1]])
    if top:
        face(part, [P(i * 2 * math.pi / sides, r1, h) for i in range(sides)], role)
    if bottom:
        face(part, [P(-i * 2 * math.pi / sides, r0, 0) for i in range(sides)], role)


def sheet(part, origin, udir, ndir, u0, u1, z0, z1, period, prof, role, uoff=0.0):
    """Profiled vertical sheet (ribs, boards, panel seams): u along udir (absolute metres from origin), z up, depth along
    ndir (positive = proud, toward the viewer). prof: [(offset 0..period, depth)], first offset 0, last = period.
    UV = (u + uoff, z) in metres, so a texture tiled at world scale lines up with the ribs / boards."""
    o, U, N = Vector(origin), Vector(udir), Vector(ndir)

    def W(u, z, d):
        return o + U * u + N * d + Vector((0, 0, z))

    for k in range(math.floor(u0 / period) - 1, math.ceil(u1 / period) + 1):
        for i in range(len(prof) - 1):
            ua, ub = k * period + prof[i][0], k * period + prof[i + 1][0]
            ca, cb = max(ua, u0), min(ub, u1)
            if cb - ca < 1e-4:
                continue
            da = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * (ca - ua) / (ub - ua)
            db = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * (cb - ua) / (ub - ua)
            pts = [W(ca, z0, da), W(cb, z0, db), W(cb, z1, db), W(ca, z1, da)]
            uvs = [(ca + uoff, z0), (cb + uoff, z0), (cb + uoff, z1), (ca + uoff, z1)]
            if (pts[1] - pts[0]).cross(pts[3] - pts[0]).dot(N) < 0:
                pts, uvs = [pts[0], pts[3], pts[2], pts[1]], [uvs[0], uvs[3], uvs[2], uvs[1]]
            face(part, pts, role, uvs)


def hslats(part, y, ny, x0, x1, z0, n, pitch, role):
    """Horizontal slats (roller-door curtain): n slats of `pitch` from z0 up, real grooves, facing ny (+1 / -1 in y)."""
    prof = [(0.0, -0.012), (0.012, 0.0), (pitch - 0.012, 0.0), (pitch, -0.012)]
    for k in range(n):
        for i in range(len(prof) - 1):
            za, zb = z0 + k * pitch + prof[i][0], z0 + k * pitch + prof[i + 1][0]
            ya, yb = y + ny * prof[i][1], y + ny * prof[i + 1][1]
            pts = [Vector((x0, ya, za)), Vector((x1, ya, za)), Vector((x1, yb, zb)), Vector((x0, yb, zb))]
            uvs = [(x0, za), (x1, za), (x1, zb), (x0, zb)]
            if (pts[1] - pts[0]).cross(pts[3] - pts[0]).y * ny < 0:
                pts, uvs = [pts[0], pts[3], pts[2], pts[1]], [uvs[0], uvs[3], uvs[2], uvs[1]]
            face(part, pts, role, uvs)


CORR = (0.6, [(0.0, 0.0), (0.2, 0.0), (0.3, -0.05), (0.5, -0.05), (0.6, 0.0)])          # hangar corrugated (texture 03 phase)
BOARDS = (0.525, [(0.0, -0.012), (0.008, 0.0), (0.167, 0.0), (0.175, -0.012), (0.183, 0.004), (0.342, 0.004),
                  (0.35, -0.012), (0.358, 0.002), (0.517, 0.002), (0.525, -0.012)])        # 3 boards of 17.5 cm, slight offsets
PANEL = (1.2, [(0.0, -0.01), (0.012, 0.0), (1.188, 0.0), (1.2, -0.01)])                    # panel seams every 1.2 m
FLAT = (10.0, [(0.0, 0.0), (10.0, 0.0)])
# v1 workshop trapezoid sheet (ws_lib_v01.corr_bps): 0.1875 m pitch, valley 40 %, flank 12 %, crown 36 %, 3 cm deep.
# Texture T7_metal_trapez tiles every 1.5 m (material scale 0.66667) = 8 ribs; its crowns are centred at 0.5 pitch,
# the profile's at 0.7 pitch, so the UVs shift by -0.2 pitch and the painted rib shading sits on the modelled ribs.
CORR_WS = (0.1875, [(0.0, 0.0), (0.075, 0.0), (0.0975, 0.03), (0.165, 0.03), (0.1875, 0.0)])
CORR_WS_UOFF = -0.0375


def ceiling_ribs(part, x0, x1, y0, y1, z, role):
    """Corrugated ceiling deck (v1 workshop roof liner): ribs run along x, the profile repeats along y, crowns hang
    down 3 cm from z, faces look down; UV (y + offset, x) so the texture's ribs follow the modelled ones."""
    period, prof = CORR_WS
    for k in range(math.floor(y0 / period) - 1, math.ceil(y1 / period) + 1):
        for i in range(len(prof) - 1):
            ua, ub = k * period + prof[i][0], k * period + prof[i + 1][0]
            ca, cb = max(ua, y0), min(ub, y1)
            if cb - ca < 1e-4:
                continue
            da = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * (ca - ua) / (ub - ua)
            db = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * (cb - ua) / (ub - ua)
            pts = [Vector((x0, ca, z - da)), Vector((x0, cb, z - db)), Vector((x1, cb, z - db)), Vector((x1, ca, z - da))]
            uvs = [(ca + CORR_WS_UOFF, x0), (cb + CORR_WS_UOFF, x0), (cb + CORR_WS_UOFF, x1), (ca + CORR_WS_UOFF, x1)]
            if (pts[1] - pts[0]).cross(pts[3] - pts[0]).z > 0:
                pts, uvs = [pts[0], pts[3], pts[2], pts[1]], [uvs[0], uvs[3], uvs[2], uvs[1]]
            face(part, pts, role, uvs)


def rod(part, p0, p1, w, role):
    """Square bar of side w from p0 to p1 (any direction), side faces only plus end caps; metric UVs."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    a = ax.cross(Vector((0, 0, 1)))
    if a.length < 1e-4:
        a = Vector((1, 0, 0))
    a.normalize()
    b = ax.cross(a).normalized()
    h = w / 2
    ring = [a * h + b * h, -a * h + b * h, -a * h - b * h, a * h - b * h]
    for i in range(4):
        q = [p0 + ring[i], p0 + ring[(i + 1) % 4], p1 + ring[(i + 1) % 4], p1 + ring[i]]
        if (q[1] - q[0]).cross(q[3] - q[0]).dot(ring[i] + ring[(i + 1) % 4]) < 0:
            q.reverse()
        face(part, q, role)
    face(part, [p1 + r for r in ring] if ring[0].cross(ring[1]).dot(ax) > 0 else [p1 + r for r in reversed(ring)], role)
    face(part, [p0 + r for r in reversed(ring)] if ring[0].cross(ring[1]).dot(ax) > 0 else [p0 + r for r in ring], role)


def collider(name, mn, mx, yaw=0.0, centre=None):
    """Box collider in room space (Blender coords), axis-aligned around its centre, optional yaw (deg about Z)."""
    mn, mx = Vector(mn), Vector(mx)
    c = Vector(centre) if centre is not None else (mn + mx) * 0.5
    COLLIDERS.append({'name': name, 'c': [c.x, c.z, c.y], 's': [abs(mx.x - mn.x), abs(mx.z - mn.z), abs(mx.y - mn.y)], 'yaw': -yaw})


def light(name, kind, pos, intensity, rng, angle=0.0, shadows=False, mask='both', color=(1.0, 0.78, 0.52)):
    LIGHTS.append({'name': name, 'type': kind, 'p': [pos[0], pos[2], pos[1]], 'i': intensity, 'r': rng, 'a': angle,
                   'sh': shadows, 'mask': mask, 'col': list(color)})


def anchor(name, pos, yaw=0.0):
    ANCHORS.append({'name': name, 'p': [pos[0], pos[2], pos[1]], 'yaw': -yaw})


# ------------------------------------------------------------------------------------------------ v1 source import
SRC = {}


def import_src(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    for o in bpy.data.objects:
        if o not in before:
            SRC[o.name] = o
            o.hide_render = True


def src_frame(name):
    """World matrix of a v1 prop pivot (location + yaw only)."""
    e = SRC[name]
    yaw = e.matrix_world.to_euler().z
    return Matrix.Translation(e.matrix_world.translation) @ Matrix.Rotation(yaw, 4, 'Z')


def append_mesh(part, ob, M, mapping, keep=None):
    """Copy a v1 mesh object into part.bm through M (applied after the object's world matrix); v1 materials -> roles.
    keep(island centre in v1 world) selects whole connected islands."""
    me = ob.data
    src = bmesh.new()
    src.from_mesh(me)
    src.transform(ob.matrix_world)
    uvl = src.loops.layers.uv.active
    slot = [mapping.get(base_mat_name(m.name)) if m else None for m in me.materials] or [None]
    src.faces.ensure_lookup_table()
    allowed = None
    if keep is not None:
        allowed = set()
        for isl in islands_of(src):
            vs = {v for f in isl for v in f.verts}
            c = sum((v.co for v in vs), Vector()) / len(vs)
            if keep(c):
                allowed.update(f.index for f in isl)
    vmap = {}
    n = 0
    for f in src.faces:
        role = slot[f.material_index] if f.material_index < len(slot) else None
        if role is None or (allowed is not None and f.index not in allowed):
            continue
        vs = []
        for v in f.verts:
            nv = vmap.get(v.index)
            if nv is None:
                nv = vmap[v.index] = part.bm.verts.new(M @ v.co)
            vs.append(nv)
        try:
            nf = part.bm.faces.new(vs)
        except ValueError:
            continue
        nf.material_index = part.ri(role)
        for l, sl in zip(nf.loops, f.loops):
            l[part.uv].uv = sl[uvl].uv if uvl else planar_uv(sl.vert.co, f.normal)
        if role == 'Labels':
            nf[part.lock] = 1
        n += 1
    src.free()
    return n


def prop_meshes(name):
    e = SRC[name]
    kids = [c for c in e.children if c.type == 'MESH' and not c.name.startswith('UCX') and not c.name.endswith('_LOD1')]
    ucx = [c for c in e.children if c.type == 'MESH' and c.name.startswith('UCX')]
    return kids, ucx


def v1_prop(name, pos, yaw, mapping, out=None, hero=False, ucx=True, snap=None, group='Props', layer='room'):
    """A v1 prop (pivot empty `name`) placed with yaw (deg; v1 props face their local -Y) at pos; snap = {'xmin'|'xmax'|
    'ymin'|'ymax': value} moves the part so its bounds touch that line (props stand against the walls)."""
    kids, ucxs = prop_meshes(name)
    part = new_part(out or name.replace('WS_P_', '').replace('PH_P_', ''), group, layer=layer, pivot=pos, hero=hero, smooth=40.0)
    Ml = src_frame(name).inverted()
    R = Matrix.Rotation(math.radians(yaw), 4, 'Z')
    for k in kids:
        append_mesh(part, k, R @ Ml, mapping)
    chunkify(part)
    mn, mx = part.bounds()
    for key, val in (snap or {}).items():
        if key == 'xmin':
            part.pivot.x = val - mn.x
        elif key == 'xmax':
            part.pivot.x = val - mx.x
        elif key == 'ymin':
            part.pivot.y = val - mn.y
        elif key == 'ymax':
            part.pivot.y = val - mx.y
    if ucx:
        for i, u in enumerate(ucxs):
            ws = [R @ Ml @ u.matrix_world @ v.co for v in u.data.vertices]
            a = Vector((min(p.x for p in ws), min(p.y for p in ws), min(p.z for p in ws))) + part.pivot
            b = Vector((max(p.x for p in ws), max(p.y for p in ws), max(p.z for p in ws))) + part.pivot
            collider(f'{part.name}_{i}', a, b)
    return part


# ------------------------------------------------------------------------------------------------ chunky pass
def islands_of(bm):
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    seen = set()
    out = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        out.append(isl)
    return out


def island_axes(isl):
    fs = sorted(isl, key=lambda f: -f.calc_area())
    n1 = fs[0].normal.normalized()
    n2 = None
    for f in fs[1:]:
        if abs(f.normal.dot(n1)) < 0.2 and f.calc_area() > 1e-7:
            n2 = (f.normal - n1 * f.normal.dot(n1)).normalized()
            break
    if n2 is None:
        t = Vector((0, 0, 1)) if abs(n1.z) < 0.9 else Vector((1, 0, 0))
        n2 = (t - n1 * t.dot(n1)).normalized()
    n3 = n1.cross(n2).normalized()
    out = []
    for a in (n1, n2, n3):
        m = max(range(3), key=lambda i: abs(a[i]))
        if abs(a[m]) > 0.995:
            s = Vector((0, 0, 0))
            s[m] = 1.0
            a = s
        out.append(a)
    return out


STATS = {'thickened': 0, 'bevelled': 0}


def chunkify(part, bevel_small=0.02, bevel_big=0.03, min_bevel_len=0.2):
    """Shape-language pass on a v1 part (ArtDirection section 2): islands thinner than 0.06 m (parts < 1 m, and rods) /
    0.10 m (plates >= 1 m) are thickened along their thin axes, growing away from neighbouring geometry (horizontal plates
    downward so what stands on them stays put; never into a neighbour); box-like islands >= 0.2 m get a chamfer of 2 cm
    (3 cm on parts >= 1 m; 2 segments on hero props). UVs of reshaped islands are re-projected in metres."""
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)     # v1 meshes come unwelded (one island per face)
    bm.normal_update()
    isls = islands_of(bm)
    # no fourth detail level (no bolts): drop tiny bits, keep wheels / lamps / labels
    tiny = []
    for isl in isls:
        roles = {part.roles[f.material_index] for f in isl}
        if roles & (NO_CHUNK | {'Rubber'}):
            continue
        vs = {v for f in isl for v in f.verts}
        ext = max(max(v.co[i] for v in vs) - min(v.co[i] for v in vs) for i in range(3))
        if ext < 0.07:
            tiny.extend(isl)
    if tiny:
        bmesh.ops.delete(bm, geom=tiny, context='FACES')
        STATS['dropped'] = STATS.get('dropped', 0) + len(tiny)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    isls = islands_of(bm)
    if not isls:
        return
    allco = np.array([v.co[:] for v in bm.verts])
    vid = np.full(len(bm.verts), -1, dtype=np.int32)
    for k, isl in enumerate(isls):
        for f in isl:
            for v in f.verts:
                vid[v.index] = k
    info = []
    for k, isl in enumerate(isls):
        roles = {part.roles[f.material_index] for f in isl}
        verts = list({v for f in isl for v in f.verts})
        axes = island_axes(isl)
        ext = []
        for a in axes:
            d = [v.co.dot(a) for v in verts]
            ext.append([min(d), max(d)])
        changed = False
        if not (roles & NO_CHUNK) and len(isl) >= 2:
            dims = sorted(e[1] - e[0] for e in ext)
            L = dims[2]
            rod = dims[1] < 0.06
            req = 0.06 if (L < 1.0 or rod) else 0.10
            others = allco[vid != k]
            for ai, a in enumerate(axes):
                lo, hi = ext[ai]
                t = hi - lo
                if t >= req - 1e-4 or t < 0.003:
                    continue
                grow = min(req - t, 0.08)
                oa = [axes[j] for j in range(3) if j != ai]
                oe = [ext[j] for j in range(3) if j != ai]
                room_hi = room_lo = 1.0
                n_hi = n_lo = 0
                if len(others):
                    d = others @ np.array(a[:])
                    m = np.ones(len(others), dtype=bool)
                    for b, (blo, bhi) in zip(oa, oe):
                        db = others @ np.array(b[:])
                        m &= (db > blo - 0.02) & (db < bhi + 0.02)
                    above = d[m & (d >= hi - 1e-4)]
                    below = d[m & (d <= lo + 1e-4)]
                    room_hi = (above.min() - hi - 0.004) if len(above) else 1.0
                    room_lo = (lo - below.max() - 0.004) if len(below) else 1.0
                    n_hi = int(np.sum(m & (d >= hi - 1e-4) & (d < hi + 0.05)))
                    n_lo = int(np.sum(m & (d <= lo + 1e-4) & (d > lo - 0.05)))
                room_hi, room_lo = max(room_hi, 0.0), max(room_lo, 0.0)
                if abs(a.z) > 0.9:                      # horizontal plate: grow down, up only if nothing stands on it
                    g_lo = min(grow, room_lo)
                    g_hi = min(grow - g_lo, room_hi) if n_hi == 0 else 0.0
                elif n_hi > n_lo:
                    g_lo, g_hi = min(grow, room_lo), 0.0
                elif n_lo > n_hi:
                    g_lo, g_hi = 0.0, min(grow, room_hi)
                else:
                    g_lo, g_hi = min(grow / 2, room_lo), min(grow / 2, room_hi)
                if g_lo + g_hi < 0.004:
                    continue
                nlo, nhi = lo - g_lo, hi + g_hi
                s = (nhi - nlo) / t
                for v in verts:
                    d0 = v.co.dot(a)
                    v.co += a * ((nlo + (d0 - lo) * s) - d0)
                ext[ai] = [nlo, nhi]
                changed = True
                STATS['thickened'] += 1
        info.append((isl, roles, ext, changed))
    bm.normal_update()
    for isl, roles, ext, changed in info:
        if changed:
            for f in isl:
                if not f[part.lock]:
                    for l in f.loops:
                        l[part.uv].uv = planar_uv(l.vert.co, f.normal)
    edges = {}
    for isl, roles, ext, changed in info:
        if roles & (NO_CHUNK | {'Cardboard'}) or not (5 <= len(isl) <= 14):
            continue
        dims = sorted(e[1] - e[0] for e in ext)
        if dims[2] < min_bevel_len or dims[0] < 0.035:
            continue
        w = round(min(bevel_big if dims[2] >= 1.0 else bevel_small, dims[0] * 0.3), 3)
        es = [e for f in isl for e in f.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(30)]
        if es:
            edges.setdefault(w, set()).update(es)
            STATS['bevelled'] += 1
    for w, es in sorted(edges.items()):
        es = [e for e in es if e.is_valid]
        if es:
            bmesh.ops.bevel(bm, geom=es, offset=w, segments=2 if part.hero else 1, profile=0.5, affect='EDGES', clamp_overlap=True)
    bm.normal_update()


# ------------------------------------------------------------------------------------------------ shell (both rooms)
def build_shell(W, D, H, wall=0.2, slab=0.2, holes=None, inner='workshop', name='Room'):
    """Walls, ceiling and floor of a room box W x D x H (outer). holes = {'front': [(x0, x1, z0, z1, kind)]} in room x.
    Inside: workshop = graphite panel 0..1.2 m + v1 grey trapezoid sheet above and on the ceiling; pharmacy = green
    dado 0..1.0 m + off-white plaster, off-white ceiling. Outside (front and sides), each room its own style: workshop =
    grey trapezoid sheet over a graphite plinth; pharmacy = off-white panels over a green plinth, green fascia. Back:
    plain. Wall cores carry no visible faces (every face is a finish layer, a trim or a frame), so nothing is coplanar."""
    hx, hy = W / 2, D / 2
    ix, iy = hx - wall, hy - wall
    ceil = H - slab
    holes = holes or {}
    sh_in = new_part(f'{name}_Walls_Inside', 'Shell', layer='room')
    sh_out = new_part(f'{name}_Walls_Outside', 'Shell', layer='hall')
    trims_in = new_part(f'{name}_Trims_Inside', 'Shell', layer='room', smooth=40.0)
    trims_out = new_part(f'{name}_Trims_Outside', 'Shell', layer='hall', smooth=40.0)
    frames = new_part(f'{name}_Frames', 'Shell', layer='both', smooth=40.0)
    ws = inner == 'workshop'
    corner = 0.13 if ws else 0.06
    walls = {   # inner face origin, u direction, inward normal, u range
        'front': (Vector((0, iy, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), (-ix, ix)),
        'back': (Vector((0, -iy, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), (-ix, ix)),
        'left': (Vector((-ix, 0, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), (-iy, iy)),
        'right': (Vector((ix, 0, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)), (-iy, iy)),
    }

    def span_box(p, o, U, N, a, b, d0, d1, z0, z1, role, faces=ALL, bevel=0.015):
        pa, pb = o + U * a + N * d0, o + U * b + N * d1
        box(p, (min(pa.x, pb.x), min(pa.y, pb.y), z0), (max(pa.x, pb.x), max(pa.y, pb.y), z1), role, faces=faces, bevel=bevel)

    for key, (o, U, N, (ua, ub)) in walls.items():
        def to_u(x):
            return x if key in ('front', 'left') else -x
        hu = [(min(to_u(h[0]), to_u(h[1])), max(to_u(h[0]), to_u(h[1])), h[2], h[3]) for h in holes.get(key, [])]
        cuts = sorted({ua, ub, *[h[0] for h in hu], *[h[1] for h in hu]})
        outer_o = o - N * wall
        for i in range(len(cuts) - 1):
            a, b = cuts[i], cuts[i + 1]
            if b - a < 1e-4:
                continue
            spans, z = [], 0.0
            for h in sorted([h for h in hu if h[0] <= a + 1e-4 and h[1] >= b - 1e-4], key=lambda h: h[2]):
                if h[2] > z:
                    spans.append((z, h[2]))
                z = max(z, h[3])
            if z < ceil:
                spans.append((z, ceil))
            for z0, z1 in spans:
                top = z1 >= ceil - 1e-3
                p0, p1, q0, q1 = o + U * a, o + U * b, outer_o + U * a, outer_o + U * b
                xs, ys = [p0.x, p1.x, q0.x, q1.x], [p0.y, p1.y, q0.y, q1.y]
                collider(f'wall_{key}', (min(xs), min(ys), z0), (max(xs), max(ys), H if top else z1))
                lim = 1.2 if ws else 1.0
                lo, hi = (z0, min(z1, lim)), (max(z0, lim), z1)
                if lo[1] > lo[0] + 1e-3:
                    sheet(sh_in, o + N * (0.02 if ws else 0.025), U, N, a, b, lo[0], lo[1], PANEL[0], PANEL[1], 'Graphite' if ws else 'Accent')
                if hi[1] > hi[0] + 1e-3:
                    if ws:
                        sheet(sh_in, o + N * 0.012, U, N, a, b, hi[0], hi[1], CORR_WS[0], CORR_WS[1], 'CorrWS', CORR_WS_UOFF)
                    else:
                        sheet(sh_in, o, U, N, a, b, hi[0], hi[1], FLAT[0], FLAT[1], 'OffWhite')
                zt = H if top else z1
                ea = a - (wall if abs(a - ua) < 1e-4 else 0.0)
                eb = b + (wall if abs(b - ub) < 1e-4 else 0.0)
                if key == 'back':
                    sheet(sh_out, outer_o, U, -N, ea, eb, z0, zt, FLAT[0], FLAT[1], 'Graphite' if ws else 'OffWhite')
                else:
                    # outside, each room in its own style: workshop = v1 grey trapezoid sheet over a graphite panel plinth;
                    # pharmacy = smooth off-white panels (real 12 mm seams every 1.2 m) over a pharmacy-green plinth
                    plinth = 1.2 if ws else 0.9
                    plo, phi = (z0, min(zt, plinth)), (max(z0, plinth), zt)
                    if plo[1] > plo[0] + 1e-3:
                        sheet(sh_out, outer_o - N * 0.02, U, -N, ea, eb, plo[0], plo[1], PANEL[0], PANEL[1], 'Graphite' if ws else 'Accent')
                    if phi[1] > phi[0] + 1e-3:
                        if ws:
                            sheet(sh_out, outer_o - N * 0.012, U, -N, ea, eb, phi[0], phi[1], CORR_WS[0], CORR_WS[1], 'CorrWS', CORR_WS_UOFF)
                        else:
                            sheet(sh_out, outer_o - N * 0.014, U, -N, ea, eb, phi[0], phi[1], PANEL[0], PANEL[1], 'OffWhite')
        # inner trims along the solid stretches: skirting, rail at the finish change, top trim
        segs = [(ua, ub)]
        for h in hu:
            if h[2] < 0.05:
                nsegs = []
                for s0, s1 in segs:
                    if h[1] <= s0 or h[0] >= s1:
                        nsegs.append((s0, s1))
                    else:
                        if h[0] > s0:
                            nsegs.append((s0, h[0]))
                        if h[1] < s1:
                            nsegs.append((h[1], s1))
                segs = nsegs
        rail_z = 1.2 if ws else 1.0
        rail_role = 'Graphite' if ws else 'Accent'
        for s0, s1 in segs:
            if s1 - s0 < 0.02:
                continue
            span_box(trims_in, o, U, N, s0, s1, 0.0, 0.085, 0.0, 0.12, 'Graphite', faces=ALL & ~NZ)
            span_box(trims_in, o, U, N, s0, s1, 0.0, 0.09, rail_z - 0.04, rail_z + 0.05, rail_role)
        span_box(trims_in, o, U, N, ua, ub, 0.0, 0.09, ceil - 0.14, ceil, 'Graphite' if ws else 'Accent', faces=ALL & ~PZ)
        if key != 'back':
            for s0, s1 in segs:
                a2 = s0 - (wall if abs(s0 - ua) < 1e-4 else 0.0)
                b2 = s1 + (wall if abs(s1 - ub) < 1e-4 else 0.0)
                span_box(trims_out, outer_o, U, N, a2, b2, 0.0, -0.05, 0.0, 0.14, 'Graphite', faces=ALL & ~NZ)
                pz = 1.2 if ws else 0.9          # drip ledge over the plinth (covers the finish change)
                span_box(trims_out, outer_o, U, N, a2, b2, 0.0, -0.06, pz - 0.04, pz + 0.05, 'Graphite' if ws else 'Accent', bevel=0.015)
            span_box(trims_out, outer_o, U, N, ua - wall, ub + wall, 0.0, -0.05, H - 0.22, H + 0.03, 'Graphite' if ws else 'Accent',
                     faces=ALL & ~NZ, bevel=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * ix, sy * iy
            box(trims_in, (min(cx, cx - sx * corner), min(cy, cy - sy * corner), 0.0), (max(cx, cx - sx * corner), max(cy, cy - sy * corner), ceil),
                'Graphite', faces=ALL & ~NZ & ~PZ, bevel=0.015)
            ox, oy = sx * hx, sy * hy
            box(trims_out, (min(ox - sx * 0.05, ox + sx * 0.07), min(oy - sy * 0.05, oy + sy * 0.07), 0.0),
                (max(ox - sx * 0.05, ox + sx * 0.07), max(oy - sy * 0.05, oy + sy * 0.07), H + 0.03), 'Graphite', faces=ALL & ~NZ, bevel=0.02)
    ceil_p = new_part(f'{name}_Ceiling', 'Ceiling', layer='room')
    if ws:
        ceiling_ribs(ceil_p, -ix, ix, -iy, iy, ceil, 'CorrWS')      # v1 workshop: the same grey trapezoid deck overhead
    else:
        face(ceil_p, [(-ix, -iy, ceil), (-ix, iy, ceil), (ix, iy, ceil), (ix, -iy, ceil)], 'OffWhite')
    roof_top = new_part(f'{name}_RoofTop', 'Ceiling', layer='hall')
    face(roof_top, [(-hx - 0.07, -hy - 0.07, H + 0.04), (hx + 0.07, -hy - 0.07, H + 0.04), (hx + 0.07, hy + 0.07, H + 0.04),
                    (-hx - 0.07, hy + 0.07, H + 0.04)], 'Graphite')
    collider('ceiling', (-hx, -hy, ceil), (hx, hy, H))
    fl = new_part(f'{name}_Floor', 'Floor', layer='room')
    face(fl, [(-ix, -iy, 0), (ix, -iy, 0), (ix, iy, 0), (-ix, iy, 0)], 'Floor')
    for (a, b, z0, z1, kind) in holes.get('front', []):
        if z0 < 0.05 and kind == 'door':
            face(fl, [(a, iy, 0), (b, iy, 0), (b, hy, 0), (a, hy, 0)], 'Floor')
    collider('floor', (-hx, -hy, -0.3), (hx, hy, 0.0))
    return frames


def opening_frame(frames, x0, x1, z0, z1, y_in, y_out, depth=0.08, width=0.1, sill=False, role='Graphite'):
    """Reveal frame through the front wall around an opening (covers the finish edges on both faces)."""
    ya, yb = y_in - depth, y_out + depth
    box(frames, (x0 - width, ya, z0), (x0, yb, z1 + width), role, faces=ALL & ~NZ, bevel=0.02)
    box(frames, (x1, ya, z0), (x1 + width, yb, z1 + width), role, faces=ALL & ~NZ, bevel=0.02)
    box(frames, (x0, ya, z1), (x1, yb, z1 + width), role, bevel=0.02)
    if sill:
        box(frames, (x0, ya, z0 - width), (x1, yb, z0), role, bevel=0.02)


def sign(part_name, xc, zc, y_face, row, height):
    """Hangar sign style (atlas 14): dark plate 12 cm thick showing one lettering row toward +Y (the hall), graphite frame,
    warm lamp bar on two brackets above, a dim warm glow light (hall layer)."""
    p = new_part(part_name, 'Sign', layer='hall', smooth=40.0)
    w = height * (1024.0 / 341.0)
    x0, x1, z0, z1 = xc - w / 2, xc + w / 2, zc - height / 2, zc + height / 2
    yf, yb = y_face + 0.12, y_face + 0.005
    u0, u1 = 0.5 / 1024, 1 - 0.5 / 1024
    v1, v0 = 1 - (row * 341 + 0.5) / 1024, 1 - ((row + 1) * 341 - 0.5) / 1024
    # seen from +Y the viewer's right is -X: the text starts at x1
    face(p, [(x1, yf, z0), (x0, yf, z0), (x0, yf, z1), (x1, yf, z1)], 'Sign', [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    dark = [(0.02, 0.645), (0.025, 0.645), (0.025, 0.65), (0.02, 0.65)]
    for q in ([(x0, yb, z1), (x1, yb, z1), (x1, yf, z1), (x0, yf, z1)], [(x0, yb, z0), (x0, yf, z0), (x1, yf, z0), (x1, yb, z0)],
              [(x0, yb, z0), (x0, yb, z1), (x0, yf, z1), (x0, yf, z0)], [(x1, yb, z0), (x1, yf, z0), (x1, yf, z1), (x1, yb, z1)]):
        face(p, q, 'Sign', dark)
    fr = 0.05
    for mn, mx in (((x0 - fr, yb, z0 - fr), (x1 + fr, yf + 0.03, z0)), ((x0 - fr, yb, z1), (x1 + fr, yf + 0.03, z1 + fr)),
                   ((x0 - fr, yb, z0), (x0, yf + 0.03, z1)), ((x1, yb, z0), (x1 + fr, yf + 0.03, z1))):
        box(p, mn, mx, 'Graphite', bevel=0.012)
    zl = z1 + fr + 0.06
    box(p, (x0 + 0.2, yb, zl), (x1 - 0.2, yf + 0.1, zl + 0.1), 'Graphite', bevel=0.015)
    box(p, (x0 + 0.26, yb + 0.03, zl - 0.015), (x1 - 0.26, yf + 0.07, zl + 0.001), 'Lamp')
    for x in (x0 + 0.35, x1 - 0.35):
        box(p, (x - 0.03, yb, z1 + fr), (x + 0.03, yb + 0.07, zl), 'Graphite')
    light(part_name + ' glow', 'Point', (xc, y_face + 0.9, zc), 1.2, 3.5, mask='hall')
    collider(part_name, (x0 - fr, yb, z0 - fr), (x1 + fr, yf + 0.1, zl + 0.1))
    return p


# ------------------------------------------------------------------------------------------------ small new 3D props
def crate_3d(name, pos, yaw, size=(0.8, 0.6, 0.5)):
    """Olive crate with real rims, lid step, corner caps, latches and end handles (style spec section 4)."""
    p = new_part(name, 'Props', layer='room', pivot=pos, smooth=40.0)
    sx, sy, sz = size
    hx, hy = sx / 2, sy / 2
    box(p, (-hx, -hy, 0.0), (hx, hy, sz - 0.07), 'Olive', faces=ALL & ~NZ, bevel=0.02)
    box(p, (-hx - 0.012, -hy - 0.012, sz - 0.07), (hx + 0.012, hy + 0.012, sz), 'Olive', bevel=0.02)
    for z0, z1 in ((0.0, 0.06), (sz - 0.15, sz - 0.09)):
        box(p, (-hx - 0.025, -hy - 0.025, z0), (hx + 0.025, hy + 0.025, z1), 'Olive', faces=ALL if z0 > 0 else ALL & ~NZ, bevel=0.015)
    for cx in (-1, 1):
        for cy in (-1, 1):
            xa, xb = (hx - 0.06, hx + 0.035) if cx > 0 else (-hx - 0.035, -hx + 0.06)
            ya, yb = (hy - 0.06, hy + 0.035) if cy > 0 else (-hy - 0.035, -hy + 0.06)
            box(p, (xa, ya, 0.0), (xb, yb, sz + 0.012), 'Graphite', faces=ALL & ~NZ)
    for x in (-hx * 0.55, hx * 0.55):
        box(p, (x - 0.05, -hy - 0.055, sz - 0.2), (x + 0.05, -hy + 0.005, sz - 0.04), 'Graphite')
    for s in (-1, 1):
        xa, xb = (hx - 0.005, hx + 0.06) if s > 0 else (-hx - 0.06, -hx + 0.005)
        box(p, (xa, -0.14, sz * 0.5), (xb, 0.14, sz * 0.5 + 0.06), 'Graphite')
    p.bm.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    c = Vector(pos)
    COLLIDERS.append({'name': name, 'c': [c.x, c.z + sz / 2, c.y], 's': [sx + 0.07, sz + 0.012, sy + 0.07], 'yaw': -yaw})
    return p


def pallet_3d(name, pos, yaw):
    """1.2 x 1.0 m pallet: seven top planks with gaps, three stringer boards, nine blocks (light wood 12)."""
    p = new_part(name, 'Props', layer='room', pivot=pos, smooth=40.0)
    for i in range(7):
        x = -0.55 + i * (1.1 / 6)
        box(p, (x - 0.05, -0.5, 0.122), (x + 0.05, 0.5, 0.144), 'LightWood', faces=ALL & ~NZ)
    for y in (-0.45, 0.0, 0.45):
        box(p, (-0.6, y - 0.05, 0.1), (0.6, y + 0.05, 0.122), 'LightWood', faces=ALL & ~NZ & ~PZ)
        for x in (-0.55, 0.0, 0.55):
            box(p, (x - 0.05, y - 0.05, 0.0), (x + 0.05, y + 0.05, 0.1), 'LightWood', faces=ALL & ~NZ & ~PZ)
    p.bm.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    c = Vector(pos)
    COLLIDERS.append({'name': name, 'c': [c.x, c.z + 0.072, c.y], 's': [1.2, 0.144, 1.0], 'yaw': -yaw})
    return p


def strip_lamp(part, x, y, z_top, length=1.4, drop=0.6):
    """Graphite strip fixture hanging on two rods from z_top, warm diffuser underneath (hangar lamp-panel material)."""
    z = z_top - drop
    box(part, (x - length / 2, y - 0.12, z), (x + length / 2, y + 0.12, z + 0.1), 'Graphite', bevel=0.015)
    box(part, (x - length / 2 + 0.06, y - 0.08, z - 0.02), (x + length / 2 - 0.06, y + 0.08, z + 0.002), 'Lamp')
    for dx in (-length / 2 + 0.15, length / 2 - 0.15):
        box(part, (x + dx - 0.025, y - 0.025, z + 0.1), (x + dx + 0.025, y + 0.025, z_top), 'Graphite', faces=ALL & ~PZ & ~NZ)


def pendant(part, x, y, z_ceiling, z_shade):
    """The hangar pendant: rod, graphite cone shade (inside faces too), glowing disc."""
    box(part, (x - 0.025, y - 0.025, z_shade + 0.24), (x + 0.025, y + 0.025, z_ceiling), 'Graphite', faces=ALL & ~PZ & ~NZ)
    cyl(part, (x, y, z_shade), 0.32, 0.1, 0.24, 14, 'Graphite', top=True, inner=True)
    cyl(part, (x, y, z_shade + 0.05), 0.2, 0.2, 0.02, 14, 'Lamp', top=False, bottom=True)


# ------------------------------------------------------------------------------------------------ WORKSHOP
def build_workshop():
    W, D, H = 17.0, 10.0, 6.0
    ceil = H - 0.2
    ix, iy = W / 2 - 0.2, D / 2 - 0.2
    DOOR = (-4.0, 4.0, 0.0, 4.4)
    import_src(WS_SRC + r'\Workshop_W86_props_v01.fbx')
    import_src(WS_SRC + r'\Workshop_W86_lift_v01.fbx')
    frames = build_shell(W, D, H, holes={'front': [DOOR + ('door',)]}, inner='workshop', name='Workshop')
    opening_frame(frames, DOOR[0], DOOR[1], DOOR[2], DOOR[3], iy, D / 2, depth=0.09, width=0.14, role='Accent')
    anchor('Anchor_Door_Centre', (0.0, D / 2, 0.0))

    # roller door, rolled up: coil box inside above the opening, guide rails, the curtain's last slats + bottom bar
    rd = new_part('RollerDoor', 'Shell', layer='room', smooth=40.0)
    yb = iy - 0.09
    box(rd, (DOOR[0] - 0.3, yb - 0.6, 4.6), (DOOR[1] + 0.3, yb, 5.3), 'Graphite', bevel=0.03)
    for x0 in (DOOR[0] - 0.14, DOOR[1] + 0.02):
        box(rd, (x0, yb - 0.16, 0.0), (x0 + 0.12, yb, 4.6), 'Graphite', faces=ALL & ~NZ, bevel=0.015)
    ys = yb - 0.08
    hslats(rd, ys - 0.006, -1, DOOR[0] - 0.02, DOOR[1] + 0.02, 4.3, 3, 0.1, 'Roller')
    hslats(rd, ys + 0.006, 1, DOOR[0] - 0.02, DOOR[1] + 0.02, 4.3, 3, 0.1, 'Roller')
    box(rd, (DOOR[0] - 0.02, ys - 0.04, 4.22), (DOOR[1] + 0.02, ys + 0.04, 4.3), 'Graphite', bevel=0.015)
    for x in (-1.5, 1.5):
        box(rd, (x - 0.12, ys - 0.11, 4.15), (x + 0.12, ys - 0.04, 4.22), 'Graphite', bevel=0.01)
    collider('roller_coil', (DOOR[0] - 0.3, yb - 0.6, 4.2), (DOOR[1] + 0.3, yb, 5.3))
    sign('Sign_VanUpgrades', 0.0, 5.08, D / 2 + 0.014, 0, 0.78)

    # structure (v1 look): oxide-red steel portal frames, columns on the long walls + ceiling beams, solid yellow foot
    # guards (no hazard-stripe texture); lamps hang from the beams
    st = new_part('Workshop_Structure', 'Shell', layer='room', smooth=40.0)
    for x in (-4.6, 4.6):
        for s in (-1, 1):
            if s > 0:
                ya, yb2, fya, fyb = iy - 0.34, iy - 0.03, iy - 0.40, iy - 0.03
                wallside = PY
            else:
                ya, yb2, fya, fyb = -iy + 0.03, -iy + 0.34, -iy + 0.03, -iy + 0.40
                wallside = NY
            box(st, (x - 0.16, ya, 0.9), (x + 0.16, yb2, ceil - 0.42), 'Accent', faces=ALL & ~NZ & ~PZ & ~wallside, bevel=0.03)
            box(st, (x - 0.22, fya, 0.0), (x + 0.22, fyb, 0.9), 'Yellow', faces=ALL & ~NZ & ~wallside, bevel=0.02)
            collider('column', (x - 0.22, min(fya, fyb), 0.0), (x + 0.22, max(fya, fyb), ceil))
        box(st, (x - 0.15, -iy + 0.03, ceil - 0.42), (x + 0.15, iy - 0.03, ceil), 'Accent', faces=ALL & ~PZ & ~PY & ~NY, bevel=0.03)
    lamps = new_part('Workshop_Lamps', 'Lamps', layer='room', smooth=40.0)
    for x in (-4.6, 4.6):
        for y in (-2.6, 1.8):
            strip_lamp(lamps, x, y, ceil - 0.42, length=1.5, drop=0.5)
    for y in (-2.6, 1.8):
        strip_lamp(lamps, 0.0, y, ceil, length=1.5, drop=0.92)
    for x in (-4.6, 0.0, 4.6):
        light(f'Bay lamp {x:+.1f}', 'Spot', (x, -0.4, 4.85), 22.0, 9.5, angle=120.0, shadows=(x == 0.0))
    light('Bay fill door', 'Point', (0.0, 3.0, 3.8), 3.0, 7.0)

    # floor: lift bay outline as 6 mm raised yellow strips (geometry, nothing coplanar with the floor)
    LIFT = Vector((0.0, -0.4, 0.0))
    mk = new_part('Workshop_FloorMarks', 'Floor', layer='room')
    for (x0, y0, x1, y1) in ((-1.56, -3.9, -1.48, 3.1), (1.48, -3.9, 1.56, 3.1), (-1.48, 3.02, 1.48, 3.1)):
        box(mk, (x0, y0, 0.0), (x1, y1, 0.006), 'Yellow', faces=ALL & ~NZ)

    # ---- lift: Fedya's two-post lift, a stretched copy (posts 0.31 m further apart each side = 3.1 m clear between the
    # carriages, overhead beam 0.45 m higher for the taller van); moving parts keep their own pivots (travel = local +Y)
    DX, DZ, X_SPLIT, Z_SPLIT = 0.31, 0.45, 1.15, 3.9
    R = Matrix.Rotation(math.pi, 4, 'Z')        # v1 'front' arms toward the van nose; the nose faces the back wall (-Y)
    centre_v1 = Vector((0.0, -2.4, 0.0))
    for nm, side in (('Lift_Static', 0), ('Lift_Carriage_L', 1), ('Lift_Carriage_R', -1), ('Lift_Arms_FL', 1), ('Lift_Arms_FR', -1),
                     ('Lift_Arms_RL', 1), ('Lift_Arms_RR', -1)):
        kids, _ = prop_meshes(nm)
        if side == 0:
            piv = LIFT.copy()
        else:
            pr = src_frame(nm).translation - centre_v1
            pr.x += math.copysign(DX, pr.x)
            piv = LIFT + R @ pr
        part = new_part(nm + '_Wide', 'Lift', layer='room', pivot=piv, hero=(side == 0), static=(side == 0), smooth=40.0)
        for k in kids:
            append_mesh(part, k, Matrix.Translation(-centre_v1), WS_MAP)
        for v in part.bm.verts:
            if abs(v.co.x) > X_SPLIT:
                v.co.x += math.copysign(DX, v.co.x)
            if side == 0 and v.co.z > Z_SPLIT:
                v.co.z += DZ
        part.bm.transform(Matrix.Translation(LIFT - piv) @ R)
        chunkify(part)
    for s in (-1, 1):
        x = s * (1.68 + DX)
        collider('lift_post', (x - 0.2, LIFT.y - 0.33, 0.0), (x + 0.2, LIFT.y + 0.33, 4.47 + DZ))
    collider('lift_beam', (-(2.07 + DX), LIFT.y - 0.3, 4.05 + DZ), (2.07 + DX, LIFT.y + 0.3, 4.54 + DZ))
    anchor('Anchor_VanOnLift', (LIFT.x, LIFT.y, 0.0), 180.0)

    # ---- props along the walls (v1 props face local -Y: back wall yaw 180, left wall 90, right wall -90, front wall 0)
    BW, LW, RW, FW = -iy + 0.1, -ix + 0.1, ix - 0.1, iy - 0.1
    v1_prop('WS_P_TyreRack_Indoor', (-6.7, 0, 0), 180, WS_MAP, out='TyreRack', snap={'ymin': BW})
    v1_prop('WS_P_Cabinet_Dark', (-4.75, 0, 0), 180, WS_MAP, out='Cabinet', snap={'ymin': BW + 0.3})
    v1_prop('WS_P_Compressor', (-3.35, 0, 0), 180, WS_MAP, out='Compressor', snap={'ymin': BW})
    v1_prop('WS_P_ToolChest_B', (3.0, 0, 0), 180, WS_MAP, out='ToolChest_Back', snap={'ymin': BW})
    v1_prop('WS_P_TyreStack_Corner', (7.75, -3.9, 0), 0, WS_MAP, out='TyreStack')
    v1_prop('WS_P_Shelving_Parts', (0, -2.6, 0), 90, WS_MAP, out='Shelving_Parts', snap={'xmin': LW})
    v1_prop('WS_P_Workbench_A', (0, -0.1, 0), 90, WS_MAP, out='Workbench', hero=True, snap={'xmin': LW})
    v1_prop('WS_P_ToolBoard_A', (0, -0.1, 1.3), 90, WS_MAP, out='ToolBoard', ucx=False, snap={'xmin': LW - 0.07})
    v1_prop('WS_P_ToolChest_A', (0, 1.55, 0), 90, WS_MAP, out='ToolChest_Left', snap={'xmin': LW})
    v1_prop('WS_P_TrolleyJack', (-6.4, 2.9, 0), 120, WS_MAP, out='TrolleyJack')
    v1_prop('WS_P_Shelving_Boxes_A', (0, -2.3, 0), -90, WS_MAP, out='Shelving_Boxes', snap={'xmax': RW})
    v1_prop('WS_P_Desk', (0, -0.1, 0), -90, WS_MAP, out='Desk', snap={'xmax': RW})
    v1_prop('WS_P_OfficeChair', (RW - 1.05, -0.15, 0), 75, WS_MAP, out='OfficeChair')
    v1_prop('WS_P_Filing', (0, 1.1, 0), -90, WS_MAP, out='FilingCabinet', snap={'xmax': RW})
    v1_prop('WS_P_Sofa', (0, 2.85, 0), -90, WS_MAP, out='Sofa', snap={'xmax': RW})
    # (jerry cans, oil cans and the low tyre stack dropped for the triangle budget: the real-rib walls cost ~2.6 k)
    v1_prop('WS_P_Drum_East_2', (-7.65, 4.05, 0), 40, WS_MAP, out='Drum')
    pallet_3d('Pallet', (6.6, 3.95, 0.0), 0.0)
    crate_3d('Crate_A', (6.32, 3.95, 0.144), 0.0, size=(0.66, 0.6, 0.5))
    crate_3d('Crate_B', (6.98, 3.95, 0.144), 0.0, size=(0.5, 0.6, 0.42))
    crate_3d('Crate_C', (6.45, 3.95, 0.144 + 0.512), 5.0, size=(0.6, 0.5, 0.4))
    v1_prop('WS_P_WasteBin', (7.95, 4.3, 0), 0, WS_MAP, out='WasteBin')
    anchor('Anchor_Eye_Door', (0.0, D / 2 - 0.3, 1.7), 180.0)


# ------------------------------------------------------------------------------------------------ PHARMACY
def build_pharmacy():
    W, D, H = 11.0, 7.0, 4.2
    ceil = H - 0.2
    ix, iy = W / 2 - 0.2, D / 2 - 0.2
    import_src(PH_SRC + r'\Pharmacy_W86_unit_v02.fbx')
    import_src(PH_SRC + r'\Pharmacy_W86_props_v02.fbx')
    DOOR = (-5.1, -3.9, 0.0, 2.3)
    CTR = (-3.62, 3.96, 0.0, 2.4)        # glass counter + cash desk set into the wall: the window-counter
    FRG = (3.96, 4.75, 0.0, 2.4)         # the display fridge beside it (door toward the hall), graphite panel above
    frames = build_shell(W, D, H, holes={'front': [DOOR + ('door',), CTR + ('counter',), FRG + ('fridge',)]}, inner='pharmacy', name='Pharmacy')
    opening_frame(frames, DOOR[0], DOOR[1], DOOR[2], DOOR[3], iy, D / 2, depth=0.06, width=0.1)
    opening_frame(frames, CTR[0], FRG[1], 0.0, 2.4, iy, D / 2, depth=0.06, width=0.1)
    box(frames, (FRG[0], iy - 0.04, 2.03), (FRG[1], D / 2 + 0.04, 2.4), 'Graphite', bevel=0.015)
    box(frames, (FRG[0] - 0.05, iy - 0.06, 0.0), (FRG[0] + 0.0, D / 2 + 0.06, 2.4), 'Graphite', faces=ALL & ~NZ, bevel=0.012)
    collider('above_fridge', (FRG[0], iy, 2.03), (FRG[1], D / 2, 2.4))
    gl = new_part('Pharmacy_Window', 'Shell', layer='both', smooth=40.0)
    yg, yo, yi = D / 2 - 0.1, D / 2 - 0.096, D / 2 - 0.104
    n = 4
    xs = [CTR[0] + i * (CTR[1] - CTR[0]) / n for i in range(n + 1)]
    box(gl, (CTR[0], yg - 0.05, 1.32), (CTR[1], yg + 0.05, 1.38), 'Graphite', bevel=0.012)
    for x in xs[1:-1]:
        box(gl, (x - 0.03, yg - 0.05, 1.38), (x + 0.03, yg + 0.05, 2.4), 'Graphite', bevel=0.012)
    for i in range(n):
        a, b = xs[i] + (0.03 if i > 0 else 0.0), xs[i + 1] - (0.03 if i < n - 1 else 0.0)
        face(gl, [(b, yo, 1.38), (a, yo, 1.38), (a, yo, 2.4), (b, yo, 2.4)], 'Glass')
        face(gl, [(a, yi, 1.38), (b, yi, 1.38), (b, yi, 2.4), (a, yi, 2.4)], 'Glass')
    collider('window_glass', (CTR[0], yg - 0.05, 1.32), (CTR[1], yg + 0.05, 2.4))
    sign('Sign_Pharmacy', (CTR[0] + FRG[1]) / 2, 3.25, D / 2 + 0.014, 1, 0.7)
    # the pharmacy's own street-shop front: a green canopy (10 cm slab + deep front lip) over the door and the window
    # counter, hung from the wall on graphite tie rods with wall plates (rods clear of the sign)
    cn = new_part('Pharmacy_Canopy', 'Shell', layer='hall', smooth=40.0)
    yw, yl = D / 2 + 0.01, D / 2 + 0.80
    box(cn, (-W / 2 - 0.1, yw, 2.64), (W / 2 + 0.1, yl, 2.74), 'Accent', faces=ALL & ~NY, bevel=0.02)
    box(cn, (-W / 2 - 0.1, yl, 2.54), (W / 2 + 0.1, yl + 0.06, 2.78), 'Accent', bevel=0.02)
    for x in (-4.5, -1.7, 2.8, 5.0):
        box(cn, (x - 0.07, yw - 0.004, 3.18), (x + 0.07, yw + 0.04, 3.42), 'Graphite', faces=ALL & ~NY, bevel=0.01)
        rod(cn, (x, yw + 0.03, 3.3), (x, yl - 0.02, 2.74), 0.04, 'Graphite')
    collider('canopy', (-W / 2 - 0.1, D / 2, 2.54), (W / 2 + 0.1, yl + 0.06, 2.78))
    anchor('Anchor_Door_Centre', ((DOOR[0] + DOOR[1]) / 2, D / 2, 0.0))
    anchor('Anchor_Window_Customer', (-2.3, D / 2 + 0.55, 0.0), 180.0)
    anchor('Anchor_Cashier', (-2.35, 2.35, 0.0), 0.0)

    # door leaf standing open into the room along the left wall: green, raised panels both faces, graphite lever
    dl = new_part('Door_Leaf', 'Props', layer='room', pivot=(DOOR[0] + 0.03, iy, 0.0), smooth=40.0)
    wl = DOOR[1] - DOOR[0] - 0.04
    box(dl, (0.0, -wl, 0.01), (0.055, 0.0, 2.25), 'Accent', bevel=0.012)
    for z0, z1 in ((1.25, 2.05), (0.2, 1.05)):
        box(dl, (-0.015, -wl + 0.15, z0), (0.07, -0.15, z1), 'Accent', bevel=0.012)
    box(dl, (0.07, -wl + 0.08, 1.0), (0.12, -wl + 0.13, 1.1), 'Graphite', bevel=0.01)
    box(dl, (0.09, -wl + 0.08, 1.0), (0.13, -wl + 0.34, 1.06), 'Graphite', bevel=0.01)
    collider('door_leaf', (DOOR[0] + 0.01, iy - wl, 0.0), (DOOR[0] + 0.16, iy, 2.25))

    # ---- v1 interior: the merged sales-floor mesh split into groups by island position (v1 Blender, street = -Y)
    unit = SRC['PH_Unit_Interior_LOD0']

    def grp(name, keep, M, hero=False):
        part = new_part(name, 'Furniture', layer='room', hero=hero, smooth=40.0)
        n = append_mesh(part, unit, M, PH_MAP, keep=keep)
        log(f'{name}: {n} faces from the v1 interior')
        chunkify(part)
        return part

    R180 = Matrix.Rotation(math.pi, 4, 'Z')
    T = Matrix.Translation
    M_counter = T(Vector((-0.15, 8.53, 0.0))) @ R180      # counter line faces the hall: v1 front y 5.01 -> 3.52
    M_back = T(Vector((-1.03, 4.84, 0.0))) @ R180         # back cabinets: v1 partition face y 8.04 -> -3.2
    M_left = T(Vector((-0.275, -1.75, 0.0)))              # v1 left-wall shelving -> left wall (x -5.2)
    M_right = T(Vector((0.275, -2.55, 0.0)))              # v1 right-wall shelving -> right wall (x 5.2)
    M_rackA = T(Vector((-2.44, -12.51, 0.0)))             # stock rack A -> left wall, back corner
    M_rackB = T(Vector((5.81, -12.51, 0.0)))              # stock rack B -> right wall, back corner
    grp('Counter_Line', lambda c: 4.85 < c.y < 5.75 and -4.93 < c.x < 3.43, M_counter, hero=True)
    grp('Back_Cabinets', lambda c: 7.4 < c.y < 8.05 and -4.93 < c.x < 2.95 and c.z < 2.5, M_back)
    grp('Shelving_Left', lambda c: c.x < -4.4 and 0.7 < c.y < 3.8 and c.z < 2.3, M_left)
    grp('Shelving_Right', lambda c: c.x > 4.4 and 1.5 < c.y < 4.9 and c.z < 2.3, M_right)
    grp('Stock_Rack_A', lambda c: -2.8 < c.x < -2.15 and 9.2 < c.y < 11.45, M_rackA)
    grp('Stock_Rack_B', lambda c: -1.2 < c.x < -0.55 and 9.2 < c.y < 11.45, M_rackB)

    def ucx(nm, M, label):
        u = SRC[nm]
        ws = [M @ u.matrix_world @ v.co for v in u.data.vertices]
        collider(label, (min(p.x for p in ws), min(p.y for p in ws), min(p.z for p in ws)), (max(p.x for p in ws), max(p.y for p in ws), max(p.z for p in ws)))
    for k, lab in ((17, 'fridge'), (18, 'glass_counter'), (19, 'cash_desk')):
        ucx(f'UCX_PH_Unit_{k:02d}', M_counter, lab)
    for k, lab in ((24, 'back_cabinets'), (25, 'back_cabinets_upper'), (26, 'tall_cabinet')):
        ucx(f'UCX_PH_Unit_{k:02d}', M_back, lab)
    ucx('UCX_PH_Unit_22', M_left, 'shelving_left')
    ucx('UCX_PH_Unit_23', M_right, 'shelving_right')
    ucx('UCX_PH_Unit_31', M_rackA, 'rack_a')
    ucx('UCX_PH_Unit_32', M_rackB, 'rack_b')

    def fill(nm, M, out, props=False):
        e = SRC[nm]
        kids = [c for c in e.children if c.type == 'MESH' and not c.name.startswith('UCX') and not c.name.endswith('_LOD1')]
        part = new_part(out, 'Props' if props else 'Fill', layer='room', smooth=40.0 if props else None)
        for k in kids:
            append_mesh(part, k, M, PH_MAP)
        if props:
            chunkify(part)
        return part
    for b in range(4):
        fill(f'PH_P_Fill_Back_b{b}', M_back, f'Fill_Back_{b}')
    fill('PH_P_Fill_Fridge', M_counter, 'Fill_Fridge')
    fill('PH_P_Fill_Vitrine', M_counter, 'Fill_Vitrine')
    for b in range(3):
        fill(f'PH_P_Fill_ShelfL_b{b}', M_left, f'Fill_ShelfL_{b}')
        fill(f'PH_P_Fill_ShelfR_b{b}', M_right, f'Fill_ShelfR_{b}')
    fill('PH_P_Fill_RackA', M_rackA, 'Fill_RackA')
    fill('PH_P_Fill_RackB', M_rackB, 'Fill_RackB')
    fill('PH_P_CashRegister', M_counter, 'CashRegister', props=True)
    fill('PH_P_MiniCross', M_counter, 'MiniCross', props=True)
    v1_prop('PH_P_Chair', (-2.35, 1.95, 0.0), 200.0, PH_MAP, out='StaffChair')
    v1_prop('PH_P_Extinguisher_Sales', (0, 2.65, 0.55), -90.0, PH_MAP, out='Extinguisher', ucx=False, snap={'xmax': ix})
    pallet_3d('Pallet', (2.3, -1.2, 0.0), 90.0)
    crate_3d('Crate_A', (2.3, -0.92, 0.144), 90.0, size=(0.6, 0.5, 0.45))
    crate_3d('Crate_B', (2.3, -1.5, 0.144), 90.0, size=(0.45, 0.5, 0.35))

    lamps = new_part('Pharmacy_Lamps', 'Lamps', layer='room', smooth=40.0)
    for x in (-3.0, 0.0, 3.0):
        pendant(lamps, x, 0.6, ceil, 2.95)
    for x in (-1.6, 1.6):
        strip_lamp(lamps, x, -2.45, ceil, length=1.5, drop=0.35)
    light('Pharmacy A', 'Point', (-2.7, 0.4, 3.0), 4.5, 7.0)
    light('Pharmacy B', 'Point', (2.7, 0.4, 3.0), 4.5, 7.0)
    light('Pharmacy counter', 'Spot', (0.0, 1.4, 3.85), 9.0, 7.0, angle=115.0, shadows=True)
    anchor('Anchor_Eye_Door', ((DOOR[0] + DOOR[1]) / 2, D / 2 - 0.3, 1.7), 180.0)


# ------------------------------------------------------------------------------------------------ export
def finish_part(p):
    """Blender object for the preview / evaluation: shading by angle + weighted normals on parts with `smooth`."""
    me = bpy.data.meshes.new(p.name)
    bm = p.bm
    if p.smooth is not None:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
        lim = math.radians(p.smooth)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) <= lim
    bm.to_mesh(me)
    for r in p.roles:
        mat = bpy.data.materials.get('R_' + r)
        if mat is None:
            mat = bpy.data.materials.new('R_' + r)
            h = PREVIEW_COL.get(r, '#FF00FF').lstrip('#')
            c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            lin = [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]
            mat.diffuse_color = (*lin, 1.0)
        me.materials.append(mat)
    ob = bpy.data.objects.new(p.name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = p.pivot
    if p.smooth is not None:
        mod = ob.modifiers.new('WN', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
        mod.mode = 'FACE_AREA'
        mod.weight = 50
    return ob


def export_room(room, path):
    dg = bpy.context.evaluated_depsgraph_get()
    out_parts, total, by_group = [], 0, {}
    for p in PARTS:
        ob = bpy.data.objects[p.name]
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        uvl = me.uv_layers.active.data if me.uv_layers.active else None
        cn = me.corner_normals
        key_index, V, N, U, subs = {}, [], [], [], {}
        for tri in me.loop_triangles:
            idx = []
            for li in tri.loops:
                co = me.vertices[me.loops[li].vertex_index].co
                nn = cn[li].vector
                uv = uvl[li].uv if uvl else (0.0, 0.0)
                k = (round(co.x, 4), round(co.y, 4), round(co.z, 4), round(nn.x, 3), round(nn.y, 3), round(nn.z, 3), round(uv[0], 4), round(uv[1], 4))
                j = key_index.get(k)
                if j is None:
                    j = key_index[k] = len(V)
                    V.append((k[0], k[2], k[1]))
                    N.append((k[3], k[5], k[4]))
                    U.append((k[6], k[7]))
                idx.append(j)
            subs.setdefault(tri.material_index, []).extend([idx[0], idx[2], idx[1]])
        ev.to_mesh_clear()
        tris = sum(len(t) for t in subs.values()) // 3
        if not V:
            continue
        total += tris
        by_group[p.group] = by_group.get(p.group, 0) + tris
        out_parts.append({
            'name': p.name, 'group': p.group, 'layer': p.layer, 'static': p.static,
            'pos': [round(p.pivot.x, 4), round(p.pivot.z, 4), round(p.pivot.y, 4)],
            'v': [c for v in V for c in v], 'n': [c for v in N for c in v], 'uv': [c for v in U for c in v],
            'sub': [{'role': p.roles[mi], 't': t} for mi, t in sorted(subs.items())], 'tris': tris,
        })
    data = {'room': room, 'revision': 'v01', 'frame': 'Unity local: origin = floor centre, +Z = front (hall side), metres',
            'tris': total, 'tris_by_group': by_group, 'parts': out_parts, 'colliders': COLLIDERS, 'lights': LIGHTS,
            'anchors': ANCHORS, 'stats': dict(STATS), 'log': LOG}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, separators=(',', ':'))
    log(f'{room}: {len(out_parts)} parts, {total} triangles {by_group}, {len(COLLIDERS)} colliders, {len(LIGHTS)} lights, '
        f'thickened {STATS["thickened"]}, bevelled {STATS["bevelled"]} -> {path}')


def preview(room, folder, size):
    """Quick Blender check renders (Workbench, material colours): cutaway overview, door view, hall view, back view."""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    shd = sc.display.shading
    shd.light = 'STUDIO'
    shd.color_type = 'MATERIAL'
    shd.show_shadows = True
    shd.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    W, D, H = size
    hide = [o for o in sc.objects if o.name.endswith(('_Ceiling', '_RoofTop'))]
    dx = 0.0 if room == 'workshop' else -4.5
    views = [('overview', (W * 0.32, D * 1.15, H * 3.3), (0, -D * 0.05, 0.3), 50, True),
             ('door_eye', (dx, D / 2 - 0.3, 1.7), (dx * 0.4, -D / 2, 1.0), 75, False),
             ('hall_front', (W * 0.1, D / 2 + 7.0, 1.7), (0, 0, 1.8), 60, False),
             ('back_to_front', (0.0, -D / 2 + 0.7, 1.7), (0.0, D / 2, 1.2), 80, False)]
    for nm, pos, tgt, fov, cut in views:
        for o in hide:
            o.hide_render = cut
        cam.location = pos
        cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.angle = math.radians(fov)
        sc.render.filepath = os.path.join(folder, f'{room}_{nm}.png')
        bpy.ops.render.render(write_still=True)


def run():
    for room in WHICH:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for coll in (PARTS, COLLIDERS, LIGHTS, ANCHORS, LOG):
            coll.clear()
        SRC.clear()
        STATS['thickened'] = STATS['bevelled'] = 0
        # preview colour of the room accent (Unity: WorkshopRoom_Accent = oxide red, PharmacyRoom_Accent = pharmacy green)
        PREVIEW_COL['Accent'] = '#9A4A36' if room == 'workshop' else '#4F8A6E'
        if room == 'workshop':
            build_workshop()
            size, path = (17.0, 10.0, 6.0), os.path.join(OUT_DIR, 'Workshop', 'Source', 'WorkshopRoom_geo_v01.json')
        else:
            build_pharmacy()
            size, path = (11.0, 7.0, 4.2), os.path.join(OUT_DIR, 'Pharmacy', 'Source', 'PharmacyRoom_geo_v01.json')
        for o in list(SRC.values()):
            bpy.data.objects.remove(o)
        for p in PARTS:
            finish_part(p)
        export_room(room, path)
        if PREVIEW:
            os.makedirs(PREVIEW, exist_ok=True)
            preview(room, PREVIEW, size)


run()
