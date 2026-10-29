"""PortableFridge_W86 v01 - portable organ cooler + van mount cradle (procedural).

Blender 5.2, background:  blender -b --factory-startup --python build_portable_fridge_w86_v01.py
Design extends COOLER-ASTRA-001 (white body, blue lid, navy latches/hinges/feet,
front biohazard sticker) to the economy/inventory rules: 8 slots, two side
handles for a two-handed carry, separate hinged lid, van mount cradle.
Axes: Blender metres, Z up, front (sticker, latches) = -Y, origin = floor centre.
Unity (FBX, bake_space_transform) local = (-x, z, -y): front faces Unity +Z.
"""
import bpy, bmesh, json, math, os
from mathutils import Vector, Matrix

ROOT = r"C:\Dev\Game\ArtSource\Props\PortableFridge_W86"
VER = "v01"
OUT = os.environ.get("PF_OUT", ROOT)   # dev runs may write to a scratch folder
ATLAS = os.path.join(ROOT, "Textures", "PortableFridge_W86_Atlas_v01.png")
CELLS = json.load(open(os.path.join(ROOT, "Textures", "PortableFridge_W86_Atlas_v01_cells.json"),
                       encoding="utf-8"))["cells"]

# ---------------------------------------------------------------- dimensions
W, D, R = 0.60, 0.52, 0.05          # body outer footprint and corner radius
WALL = 0.03                          # wall thickness -> cavity 0.54 x 0.46
Z_BOT = 0.015                        # body bottom (feet below)
Z_RIM = 0.33                         # body rim / lid seam
Z_FLOOR = 0.05                       # cavity floor
LID_T = 0.084                        # lid top at 0.414
POCKET = 0.025                       # lid underside recess -> clear height 0.305
HINGE = Vector((0.0, D / 2 + 0.008, Z_RIM))
OPEN_DEG = 95.0                      # lid opening angle (rear hinge); 95 keeps the van mount compact
ZH = 0.255                           # side handle bar height
HANDLE_OUT = 0.032                   # bar centre distance from side wall
HANDLE_R = 0.012
SLOT_COLS = [-0.1365, 0.1365]        # x centres (2 columns)
# rows front -> back: (y centre, usable depth, class). Rows 1-3 thin (all organs but the brain,
# organ bags, blood bags); row 4 deep enough for the brain (0.142 x 0.160 x 0.147).
SLOT_ROWS = [(-0.185, 0.090, "thin"), (-0.089, 0.090, "thin"), (0.007, 0.090, "thin"), (0.144, 0.172, "wide")]
SLOT_W = 0.267
DIV_Y = [-0.137, -0.041, 0.055]
DIV_T, DIV_TOP = 0.006, 0.20

M_INNER_X, M_INNER_Y = W / 2 + 0.01, D / 2 + 0.01   # van mount inner half sizes (10 mm clearance)
M_PAD = 0.010                        # socket height (pad top)
M_WALL_Y = None                      # wall plane (rear face of wall plate); set from the open lid in main()


def unity(v):
    return [round(-v[0], 5), round(v[2], 5), round(-v[1], 5)]


# ---------------------------------------------------------------- mesh builder
class Part:
    def __init__(self):
        self.bm = bmesh.new()
        self.groups = []           # (faces, cell, mode, bounds/explicit)

    def v(self, co):
        return self.bm.verts.new(co)

    def face(self, verts):
        return self.bm.faces.new(verts)

    def add(self, faces, cell, mode="fit", bounds=None, explicit=None):
        self.groups.append((faces, cell, mode, bounds, explicit))
        return faces


def rrect(w, d, r, seg):
    r = max(0.0005, min(r, w / 2 - 1e-4, d / 2 - 1e-4))
    cx, cy = w / 2 - r, d / 2 - r
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            pts.append((sx * cx + r * math.cos(a), sy * cy + r * math.sin(a)))
    return pts


def lathe(p, rings, seg, cap0=True, cap1=True, mat=None, center=(0, 0)):
    """rings: [(w, d, r, z)], profile order defines outward normals (see notes)."""
    mat = mat or Matrix.Identity(4)
    loops = []
    for w, d, r, z in rings:
        loops.append([p.v(mat @ Vector((center[0] + x, center[1] + y, z))) for x, y in rrect(w, d, r, seg)])
    faces = []
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            k = (j + 1) % n
            faces.append(p.face([a[j], a[k], b[k], b[j]]))
    if cap0:
        faces.append(p.face(list(reversed(loops[0]))))
    if cap1:
        faces.append(p.face(loops[-1]))
    return faces


def box(p, x0, x1, y0, y1, z0, z1, mat=None):
    mat = mat or Matrix.Identity(4)
    c = [mat @ Vector(t) for t in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    vs = [p.v(t) for t in c]
    idx = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return [p.face([vs[i] for i in f]) for f in idx]


def rbox(p, cx, cy, sx, sy, z0, z1, r, seg, cz=0.0, mat=None):
    if cz > 0:
        rings = [(sx - 2 * cz, sy - 2 * cz, max(r - cz, r * 0.5), z0), (sx, sy, r, z0 + cz),
                 (sx, sy, r, z1 - cz), (sx - 2 * cz, sy - 2 * cz, max(r - cz, r * 0.5), z1)]
    else:
        rings = [(sx, sy, r, z0), (sx, sy, r, z1)]
    return lathe(p, rings, seg, mat=mat, center=(cx, cy))


def tube(p, pts, radius, sides, up=Vector((0, 0, 1))):
    """Closed tube along a polyline (points in a plane perpendicular to `up`)."""
    pts = [Vector(t) for t in pts]
    rings = []
    for i, c in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        n = up.cross(t).normalized()
        b = up.copy()
        ring = []
        for s in range(sides):
            a = 2 * math.pi * s / sides + math.pi / sides
            ring.append(p.v(c + radius * (math.cos(a) * n + math.sin(a) * b)))
        rings.append(ring)
    faces = []
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            faces.append(p.face([a[j], a[k], b[k], b[j]]))
    faces.append(p.face(list(reversed(rings[0]))))
    faces.append(p.face(rings[-1]))
    return faces


def cylinder(p, a, b, radius, sides):
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    up = axis.cross(ref).normalized()
    return tube(p, [a, b], radius, sides, up=up)


def quad(p, corners, uvs):
    f = p.face([p.v(c) for c in corners])
    return f, uvs


# ---------------------------------------------------------------- UVs, normals
def cell_map(cell, u, v, margin=0.012):
    u0, v0, u1, v1 = CELLS[cell]
    mu, mv = (u1 - u0) * margin, (v1 - v0) * margin
    return (u0 + mu + (u1 - u0 - 2 * mu) * u, v0 + mv + (v1 - v0 - 2 * mv) * v)


def finish(p, name, smooth_angle=50.0):
    bm = p.bm
    bm.verts.index_update()
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    for faces, cell, mode, bounds, explicit in p.groups:
        if mode == "explicit":
            f, uvs = faces, explicit
            for loop, uv in zip(f.loops, uvs):
                loop[uvl].uv = cell_map(cell, *uv, margin=0.0)
            continue
        if bounds is None:
            vs = [v.co for f in faces for v in f.verts]
            bounds = (Vector((min(c.x for c in vs), min(c.y for c in vs), min(c.z for c in vs))),
                      Vector((max(c.x for c in vs), max(c.y for c in vs), max(c.z for c in vs))))
        mn, mx = bounds
        ext = mx - mn
        for f in faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            iu, iv = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
            for loop in f.loops:
                co = loop.vert.co
                uu = (co[iu] - mn[iu]) / ext[iu] if ext[iu] > 1e-6 else 0.5
                vv = (co[iv] - mn[iv]) / ext[iv] if ext[iv] > 1e-6 else 0.5
                loop[uvl].uv = cell_map(cell, min(max(uu, 0), 1), min(max(vv, 0), 1))
    for f in bm.faces:
        f.smooth = True
    lim = math.radians(smooth_angle)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) < lim
        else:
            e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


# ---------------------------------------------------------------- cooler parts
def build_body(lod):
    p = Part()
    S = 4 if lod == 0 else 1
    iw, idp, ir = W - 2 * WALL, D - 2 * WALL, R - WALL
    if lod == 0:
        rings = [(W - 0.024, D - 0.024, R - 0.012, Z_BOT), (W, D, R, Z_BOT + 0.012),
                 (W, D, R, Z_RIM - 0.008), (W - 0.010, D - 0.010, R - 0.005, Z_RIM),
                 (iw + 0.008, idp + 0.008, ir + 0.004, Z_RIM), (iw, idp, ir, Z_RIM - 0.004),
                 (iw, idp, ir, Z_FLOOR + 0.008), (iw - 0.016, idp - 0.016, ir - 0.008, Z_FLOOR)]
    else:
        rings = [(W - 0.02, D - 0.02, R - 0.01, Z_BOT), (W, D, R, Z_BOT + 0.01),
                 (W, D, R, Z_RIM), (iw, idp, ir, Z_RIM), (iw, idp, ir, Z_FLOOR)]
    shell = lathe(p, rings, S)
    body_bounds = (Vector((-W / 2, -D / 2, 0.0)), Vector((W / 2, D / 2, Z_RIM)))
    liner, outer = [], []
    p.bm.normal_update()
    for f in shell:
        inside = all(abs(v.co.x) <= iw / 2 + 0.0045 and abs(v.co.y) <= idp / 2 + 0.0045 and v.co.z <= Z_RIM + 1e-5
                     for v in f.verts)
        (liner if inside else outer).append(f)
    p.add(outer, "BODY_WHITE", "box", body_bounds)
    p.add(liner, "LINER", "box", (Vector((-iw / 2, -idp / 2, Z_FLOOR)), Vector((iw / 2, idp / 2, Z_RIM))))

    # feet (navy)
    for sx in (-1, 1):
        for sy in (-1, 1):
            if lod == 0:
                p.add(rbox(p, sx * 0.22, sy * 0.18, 0.09, 0.06, 0.0, Z_BOT + 0.002, 0.012, 1), "NAVY")
            else:
                p.add(box(p, sx * 0.22 - 0.045, sx * 0.22 + 0.045, sy * 0.18 - 0.03, sy * 0.18 + 0.03,
                          0.0, Z_BOT + 0.002), "NAVY")
    # side handles: blue bar, rubber sleeve, navy bosses
    for sx in (-1, 1):
        xw = sx * W / 2
        xo = sx * (W / 2 + HANDLE_OUT)
        if lod == 0:
            path = [(xw - sx * 0.006, -0.085, ZH), (xw + sx * 0.020, -0.085, ZH), (xo, -0.072, ZH),
                    (xo, 0.072, ZH), (xw + sx * 0.020, 0.085, ZH), (xw - sx * 0.006, 0.085, ZH)]
            p.add(tube(p, path, HANDLE_R, 8), "BLUE_SOLID")
            p.add(tube(p, [(xo, -0.055, ZH), (xo, 0.055, ZH)], HANDLE_R + 0.0025, 8), "RUBBER")
            for yy in (-0.085, 0.085):
                p.add(rbox(p, xw + sx * 0.005, yy, 0.022, 0.036, ZH - 0.026, ZH + 0.026, 0.006, 1), "NAVY")
        else:
            path = [(xw - sx * 0.006, -0.085, ZH), (xo, -0.085, ZH), (xo, 0.085, ZH), (xw - sx * 0.006, 0.085, ZH)]
            p.add(tube(p, path, HANDLE_R, 6), "BLUE_SOLID")
            for yy in (-0.085, 0.085):
                p.add(box(p, min(xw - sx * 0.006, xw + sx * 0.016), max(xw - sx * 0.006, xw + sx * 0.016),
                          yy - 0.018, yy + 0.018, ZH - 0.026, ZH + 0.026), "NAVY")
    # latch keepers (front) and body hinge leaves + knuckles (rear)
    for sx in (-1, 1):
        x = sx * 0.17
        if lod == 0:
            p.add(rbox(p, x, -D / 2 - 0.0035, 0.042, 0.015, 0.283, 0.301, 0.004, 1), "NAVY")
        else:
            p.add(box(p, x - 0.021, x + 0.021, -D / 2 - 0.011, -D / 2 + 0.004, 0.283, 0.301), "NAVY")
        hx = sx * 0.18
        if lod == 0:
            p.add(rbox(p, hx, D / 2 + 0.0025, 0.046, 0.009, 0.288, Z_RIM - 0.004, 0.004, 1), "NAVY")
            p.add(cylinder(p, (hx - 0.012, HINGE.y, HINGE.z), (hx + 0.012, HINGE.y, HINGE.z), 0.0075, 6), "NAVY")
        else:
            p.add(box(p, hx - 0.023, hx + 0.023, D / 2 - 0.002, D / 2 + 0.007, 0.288, Z_RIM), "NAVY")
    # dividers 2 x 4
    p.add(box(p, -DIV_T / 2, DIV_T / 2, -idp / 2 + 0.001, idp / 2 - 0.001, Z_FLOOR - 0.002, DIV_TOP), "DIVIDER")
    for yc in DIV_Y:
        p.add(box(p, -iw / 2 + 0.0005, iw / 2 - 0.0005, yc - DIV_T / 2, yc + DIV_T / 2, Z_FLOOR - 0.002, DIV_TOP),
              "DIVIDER")
    if lod == 0:  # drain plug, front bottom right (viewer's right = +X)
        p.add(cylinder(p, (0.225, -D / 2 + 0.006, 0.055), (0.225, -D / 2 - 0.010, 0.055), 0.013, 8), "NAVY")
    # front sticker decal (2 mm proud of the wall)
    y = -D / 2 - 0.002
    x0, x1, z0, z1 = -0.125, 0.125, 0.075, 0.265
    f, uvs = quad(p, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    p.add(f, "STICKER", "explicit", explicit=uvs)
    return p


def build_lid(lod):
    """Lid in world coordinates; converted to pivot-local afterwards."""
    p = Part()
    S = 4 if lod == 0 else 1
    iw, idp, ir = W - 2 * WALL, D - 2 * WALL, R - WALL
    ZL = Z_RIM
    if lod == 0:
        rings = [(iw - 0.012, idp - 0.012, ir - 0.006, ZL + POCKET), (iw, idp, ir, ZL + POCKET - 0.006),
                 (iw, idp, ir, ZL), (W - 0.008, D - 0.008, R - 0.004, ZL), (W, D, R, ZL + 0.004),
                 (W, D, R, ZL + 0.068), (W - 0.016, D - 0.016, R - 0.008, ZL + 0.078),
                 (W - 0.07, D - 0.07, R - 0.035, ZL + 0.078), (W - 0.08, D - 0.08, R - 0.04, ZL + LID_T)]
    else:
        rings = [(iw, idp, ir, ZL + POCKET), (iw, idp, ir, ZL), (W, D, R, ZL), (W, D, R, ZL + 0.074),
                 (W - 0.02, D - 0.02, R - 0.01, ZL + LID_T)]
    shell = lathe(p, rings, S)
    p.bm.normal_update()
    under, top = [], []
    for f in shell:
        inside = all(abs(v.co.x) <= iw / 2 + 1e-4 and abs(v.co.y) <= idp / 2 + 1e-4 and v.co.z <= ZL + POCKET + 1e-4
                     for v in f.verts)
        (under if (inside or f.normal.z < -0.9) else top).append(f)
    p.add(top, "LID_BLUE", "box", (Vector((-W / 2, -D / 2, ZL)), Vector((W / 2, D / 2, ZL + LID_T))))
    p.add(under, "LINER", "box", (Vector((-W / 2, -D / 2, ZL)), Vector((W / 2, D / 2, ZL + LID_T))))
    for sx in (-1, 1):
        x = sx * 0.17
        if lod == 0:  # latch plate + pivot barrel
            p.add(rbox(p, x, -D / 2 - 0.009, 0.05, 0.008, 0.296, 0.392, 0.006, 1), "NAVY")
            p.add(cylinder(p, (x - 0.026, -D / 2 - 0.006, 0.386), (x + 0.026, -D / 2 - 0.006, 0.386), 0.007, 6), "NAVY")
        else:
            p.add(box(p, x - 0.025, x + 0.025, -D / 2 - 0.013, -D / 2 + 0.001, 0.296, 0.392), "NAVY")
        hx = sx * 0.18
        if lod == 0:  # lid hinge leaf + two knuckles
            p.add(rbox(p, hx, D / 2 + 0.0025, 0.046, 0.009, Z_RIM + 0.004, 0.37, 0.004, 1), "NAVY")
            for a, b in ((-0.024, -0.0125), (0.0125, 0.024)):
                p.add(cylinder(p, (hx + a, HINGE.y, HINGE.z), (hx + b, HINGE.y, HINGE.z), 0.0075, 6), "NAVY")
        else:
            p.add(box(p, hx - 0.023, hx + 0.023, D / 2 - 0.002, D / 2 + 0.007, Z_RIM, 0.37), "NAVY")
    # duct-tape repair on the lid top (decal 1 mm proud)
    z = ZL + LID_T + 0.001
    c, hw, hl, ang = Vector((0.17, -0.08, z)), 0.025, 0.087, math.radians(35)
    ax = Vector((math.cos(ang), math.sin(ang), 0))
    ay = Vector((-math.sin(ang), math.cos(ang), 0))
    # tape cell is portrait: u across the strip, v along it
    corners = [c - ax * hw - ay * hl, c + ax * hw - ay * hl, c + ax * hw + ay * hl, c - ax * hw + ay * hl]
    f, uvs = quad(p, corners, [(0, 0), (1, 0), (1, 1), (0, 1)])
    p.add(f, "TAPE", "explicit", explicit=uvs)
    return p


def build_mount(lod):
    p = Part()
    ix, iy = M_INNER_X, M_INNER_Y
    t = 0.006
    p.add(rbox(p, 0.0, 0.0, 2 * (ix + t), 2 * (iy + t), 0.0, t, 0.012, 1 if lod == 0 else 1), "STEEL")
    for sx in (-1, 1):  # side lips
        p.add(box(p, min(sx * ix, sx * (ix + t)), max(sx * ix, sx * (ix + t)), -iy - t, iy + t, t, 0.076), "STEEL")
    front = box(p, -ix, ix, -iy - t, -iy, t, 0.05)
    p.add(front, "HAZARD", "box", (Vector((-ix, -iy - t, t)), Vector((ix, -iy, 0.05))))
    p.add(box(p, -ix, ix, iy, iy + t, t, 0.076), "STEEL")
    for sx in (-1, 1):  # stand-off arms to the wall plate
        p.add(box(p, sx * 0.22 - 0.015, sx * 0.22 + 0.015, iy + t, M_WALL_Y - t, 0.0, 0.03), "STEEL")
    p.add(box(p, -ix - t, ix + t, M_WALL_Y - t, M_WALL_Y, 0.0, 0.22), "STEEL")
    for sx in (-1, 1):  # gussets
        x0, x1 = (ix - 0.006, ix) if sx > 0 else (-ix, -ix + 0.006)
        prof = [(iy + t, t), (M_WALL_Y - t, t), (M_WALL_Y - t, 0.20), (iy + t, 0.076)]
        a = [p.v((x0, y, z)) for y, z in prof]
        b = [p.v((x1, y, z)) for y, z in prof]
        fs = [p.face(list(reversed(a))), p.face(b)]
        for j in range(4):
            k = (j + 1) % 4
            fs.append(p.face([a[j], a[k], b[k], b[j]]))
        p.add(fs, "STEEL")
    for sx in (-1, 1):  # rubber pads under the cooler feet
        for sy in (-1, 1):
            p.add(box(p, sx * 0.22 - 0.05, sx * 0.22 + 0.05, sy * 0.18 - 0.035, sy * 0.18 + 0.035, t - 0.001, M_PAD),
                  "RUBBER")
    for sx in (-1, 1):  # front toggle clamps: base, yellow lever, hook over the cooler's front foot line
        x = sx * 0.17
        p.add(box(p, x - 0.016, x + 0.016, -iy - t - 0.016, -iy - t, 0.008, 0.036), "STEEL")
        lev = Matrix.Translation((x, -iy - t - 0.014, 0.034)) @ Matrix.Rotation(math.radians(35), 4, 'X')
        p.add(box(p, -0.011, 0.011, -0.006, 0.006, 0.0, 0.07, mat=lev), "YELLOW")
        p.add(box(p, x - 0.009, x + 0.009, -iy - t - 0.004, -iy - t + 0.002, 0.03, 0.062), "METAL")
        p.add(box(p, x - 0.009, x + 0.009, -iy - t - 0.004, -D / 2 - 0.0005, 0.056, 0.062), "METAL")
    if lod == 0:  # hex bolts: wall plate (along -Y) and tray corners (along Z)
        for sx in (-1, 1):
            for z in (0.05, 0.17):
                p.add(cylinder(p, (sx * 0.27, M_WALL_Y - t + 0.0005, z), (sx * 0.27, M_WALL_Y - t - 0.005, z), 0.008, 6),
                      "METAL")
        for sx in (-1, 1):
            for sy in (-1, 1):
                p.add(cylinder(p, (sx * 0.29, sy * (iy - 0.02), t - 0.0005), (sx * 0.29, sy * (iy - 0.02), t + 0.005), 0.008, 6),
                      "METAL")
    return p


# ---------------------------------------------------------------- scene helpers
def material():
    mat = bpy.data.materials.new("M_PortableFridge_W86_Atlas")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = bpy.data.images.load(ATLAS)
    img.name = "PortableFridge_W86_Atlas_v01"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.62
    return mat, img


def mesh_obj(name, me, parent, coll, mat, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.parent = parent
    o.location = loc
    if mat:
        me.materials.append(mat)
        tri = o.modifiers.new("Triangulate", "TRIANGULATE")
        tri.quad_method = "BEAUTY"
        tri.ngon_method = "BEAUTY"
        try:
            tri.keep_custom_normals = True
        except AttributeError:
            pass
    return o


def empty(name, loc, parent, coll, size=0.03, kind="ARROWS"):
    e = bpy.data.objects.new(name, None)
    coll.objects.link(e)
    e.parent = parent
    e.location = loc
    e.empty_display_type = kind
    e.empty_display_size = size
    return e


def ucx(name, x0, x1, y0, y1, z0, z1, parent, coll):
    p = Part()
    box(p, x0, x1, y0, y1, z0, z1)
    me = bpy.data.meshes.new(name)
    p.bm.to_mesh(me)
    p.bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.parent = parent
    o.display_type = "WIRE"
    o.hide_render = True
    return o


def tris(me):
    return sum(len(pl.vertices) - 2 for pl in me.polygons)


def shift(me, off):
    me.transform(Matrix.Translation(-off))


def main():
    for f in ("PortableFridge_W86_v01.blend", "PortableFridge_W86_v01.fbx", "PortableFridge_W86_VanMount_v01.fbx",
              "PortableFridge_W86_v01.json"):
        if os.path.exists(os.path.join(OUT, f)):
            raise SystemExit("refusing to overwrite " + f)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.scale_length = 1.0
    mat, img = material()

    cc = bpy.data.collections.new("PortableFridge_W86")
    mc = bpy.data.collections.new("PortableFridge_W86_VanMount")
    scn.collection.children.link(cc)
    scn.collection.children.link(mc)

    # ---- cooler
    root = empty("PortableFridge_W86", (0, 0, 0), None, cc, 0.1, "PLAIN_AXES")
    body = {}
    for lod in (0, 1):
        body[lod] = mesh_obj("SM_PortableFridge_Body_LOD%d" % lod, finish(build_body(lod), "SM_PortableFridge_Body_LOD%d" % lod),
                             root, cc, mat)
    # Lid objects are direct children of the identity root with their origin on the hinge (same as the VAN
    # doors): FBX bake_space_transform misplaces meshes nested under a translated empty.
    pivot = empty("LID_PIVOT", tuple(HINGE), root, cc, 0.06, "SINGLE_ARROW")  # marker only, no children
    lid = {}
    for lod in (0, 1):
        me = finish(build_lid(lod), "SM_PortableFridge_Lid_LOD%d" % lod)
        shift(me, HINGE)
        lid[lod] = mesh_obj("SM_PortableFridge_Lid_LOD%d" % lod, me, root, cc, mat, loc=tuple(HINGE))
        lid[lod].rotation_mode = "XYZ"
    ucx("UCX_SM_PortableFridge_Body_00", -W / 2, W / 2, -D / 2, D / 2, 0.0, Z_RIM, root, cc)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * W / 2, sx * (W / 2 + HANDLE_OUT + HANDLE_R + 0.003)))
        ucx("UCX_SM_PortableFridge_Body_%02d" % (1 if sx < 0 else 2), x0, x1, -0.095, 0.095, ZH - 0.026, ZH + 0.026, root, cc)
    lid_ucx = ucx("UCX_SM_PortableFridge_Lid_00", -W / 2, W / 2, -D - 0.008, -0.008, 0.0, LID_T, root, cc)
    lid_ucx.location = HINGE

    slots = []
    k = 0
    for yc, depth, cls in SLOT_ROWS:
        for xc in SLOT_COLS:
            k += 1
            nm = "SLOT_%02d" % k
            e = empty(nm, (xc, yc, Z_FLOOR), root, cc, 0.04)
            e["slot_class"] = cls
            e["slot_box"] = [SLOT_W, depth, round(Z_RIM + POCKET - Z_FLOOR, 4)]
            slots.append((nm, Vector((xc, yc, Z_FLOOR)), depth, cls))
    grips = {"GRIP_R": Vector((-(W / 2 + HANDLE_OUT), 0.0, ZH)), "GRIP_L": Vector((W / 2 + HANDLE_OUT, 0.0, ZH))}
    for nm, co in grips.items():
        empty(nm, tuple(co), root, cc, 0.05, "SPHERE")
    # lid front-top-centre point when fully open (for checking the opening direction after import)
    front_closed = Vector((0.0, -D / 2, Z_RIM + LID_T))
    rel = front_closed - HINGE
    rot = Matrix.Rotation(math.radians(-OPEN_DEG), 3, "X")
    front_open = HINGE + rot @ rel
    empty("REF_LidFront_Open", tuple(front_open), root, cc, 0.03, "CUBE")

    # ---- van mount: wall plane = rearmost point of the fully open lid + 15 mm
    global M_WALL_Y
    rot = Matrix.Rotation(math.radians(-OPEN_DEG), 4, 'X')
    open_max_y = max((Matrix.Translation(HINGE) @ rot @ v.co).y for v in lid[0].data.vertices)
    M_WALL_Y = math.ceil((open_max_y + 0.015) * 1000) / 1000
    mroot = empty("PortableFridge_W86_VanMount", (0, 0, 0), None, mc, 0.1, "PLAIN_AXES")
    mount = {}
    for lod in (0, 1):
        mount[lod] = mesh_obj("SM_PortableFridge_VanMount_LOD%d" % lod,
                              finish(build_mount(lod), "SM_PortableFridge_VanMount_LOD%d" % lod), mroot, mc, mat)
    ix, iy, t = M_INNER_X, M_INNER_Y, 0.006
    ucx("UCX_SM_PortableFridge_VanMount_00", -ix - t, ix + t, -iy - t, iy + t, 0.0, M_PAD, mroot, mc)
    ucx("UCX_SM_PortableFridge_VanMount_01", -ix - t, -ix, -iy - t, iy + t, 0.0, 0.076, mroot, mc)
    ucx("UCX_SM_PortableFridge_VanMount_02", ix, ix + t, -iy - t, iy + t, 0.0, 0.076, mroot, mc)
    ucx("UCX_SM_PortableFridge_VanMount_03", -ix, ix, -iy - t - 0.016, -iy, 0.0, 0.05, mroot, mc)
    ucx("UCX_SM_PortableFridge_VanMount_04", -ix - t, ix + t, iy, M_WALL_Y, 0.0, 0.22, mroot, mc)
    empty("COOLER_SOCKET", (0, 0, M_PAD), mroot, mc, 0.08)
    empty("REF_WallPlane", (0, M_WALL_Y, 0.11), mroot, mc, 0.05, "CUBE")
    # mount placed beside the cooler in the blend for editing
    mroot.location = (1.2, 0, 0)

    bpy.context.view_layer.update()

    # ---- export

    def export(path, roots):
        bpy.ops.object.select_all(action="DESELECT")
        for r in roots:
            for o in [r] + list(r.children_recursive):
                o.select_set(True)
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, axis_forward='-Z', axis_up='Y',
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                                 bake_space_transform=True, object_types={'EMPTY', 'MESH'},
                                 mesh_smooth_type='OFF', use_mesh_modifiers=True, use_triangles=True,
                                 add_leaf_bones=False, path_mode='COPY', embed_textures=True,
                                 use_custom_props=False)

    export(os.path.join(OUT, "PortableFridge_W86_v01.fbx"), [root])
    mroot.location = (0, 0, 0)
    bpy.context.view_layer.update()
    export(os.path.join(OUT, "PortableFridge_W86_VanMount_v01.fbx"), [mroot])
    mroot.location = (1.2, 0, 0)
    bpy.context.view_layer.update()

    # ---- stats + json
    def bounds(objs):
        mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
        for o in objs:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
        return mn, mx

    dg = bpy.context.evaluated_depsgraph_get()

    def eval_tris(o):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.polygons)
        ev.to_mesh_clear()
        return n

    st = {o.name: eval_tris(o) for o in (body[0], body[1], lid[0], lid[1], mount[0], mount[1])}
    bmn, bmx = bounds([body[0], lid[0]])
    shell_mn, shell_mx = Vector((-W / 2, -D / 2, 0)), Vector((W / 2, D / 2, Z_RIM + LID_T))
    for o in lid.values():
        o.rotation_euler.x = math.radians(-OPEN_DEG)
    bpy.context.view_layer.update()
    omn, omx = bounds([body[0], lid[0]])
    for o in lid.values():
        o.rotation_euler.x = 0.0
    mroot.location = (0, 0, 0)
    bpy.context.view_layer.update()
    mmn, mmx = bounds([mount[0]])
    mroot.location = (1.2, 0, 0)

    def r3(v):
        return [round(x, 4) for x in v]

    data = {
        "asset": "PortableFridge_W86", "revision": VER, "item_id": 301, "item_key": "container.cooler",
        "status": "review pending (Fedya visual OK); not imported into Unity",
        "design": "Extends COOLER-ASTRA-001 v03 style (white body, blue lid, navy latches/hinges/feet, front sticker "
                  "'ОРГАНЫ / НЕ КАНТОВАТЬ') to the 8-slot two-handed rules; worn finish, duct-tape repair on the lid.",
        "rules_source": ["docs/specs/ECONOMY_SALES_PROGRESSION_SPEC_2026-10-25_v01.md (portable fridge $1 000, 8 items, two hands, "
                         "van storage mounts)", "docs/specs/WORK_INVENTORY_SPEC_2026-10-18_v01.md (id 301, 8 slots, hold E lifts and closes, "
                         "2 van mounts)"],
        "units": "metres",
        "axes": {"blender": "Z up, front (sticker, latches) = -Y, hinge side = +Y, origin = floor centre under the feet",
                 "unity": "local = (-x_blender, z_blender, -y_blender) with the FBX settings below; front faces Unity +Z, "
                          "hinge side Unity -Z. If importer axes differ, trust the SLOT_/GRIP_/REF_ empties in the FBX.",
                 "fbx_export": "axis_forward -Z, axis_up Y, bake_space_transform, FBX_SCALE_UNITS, mesh_smooth_type OFF, "
                               "triangulated, embedded atlas (same as Pharmacy_W86)"},
        "files": {"fbx": os.path.join(ROOT, "PortableFridge_W86_v01.fbx"),
                  "fbx_van_mount": os.path.join(ROOT, "PortableFridge_W86_VanMount_v01.fbx"),
                  "blend": os.path.join(ROOT, "PortableFridge_W86_v01.blend"),
                  "atlas": ATLAS, "material": "M_PortableFridge_W86_Atlas (one material, one 1024 atlas, shared with the mount)"},
        "dimensions": {
            "shell_closed_xyz_blender": r3(shell_mx - shell_mn),
            "overall_closed_with_handles_hardware_xyz_blender": r3(bmx - bmn),
            "overall_open_xyz_blender": r3(omx - omn),
            "unity_size_xyz": [round((bmx - bmn).x, 4), round((bmx - bmn).z, 4), round((bmx - bmn).y, 4)],
            "cavity_inner_xyz": [round(W - 2 * WALL, 4), round(D - 2 * WALL, 4), round(Z_RIM - Z_FLOOR, 4)],
            "clear_height_floor_to_closed_lid": round(Z_RIM + POCKET - Z_FLOOR, 4),
            "body_rim_height": Z_RIM, "lid_top_height": round(Z_RIM + LID_T, 4),
        },
        "lid": {
            "objects": "SM_PortableFridge_Lid_LOD0, SM_PortableFridge_Lid_LOD1 and UCX_SM_PortableFridge_Lid_00 are direct "
                       "children of the root; all three have their origin ON the hinge axis (= LID_PIVOT empty). In Unity "
                       "parent the three under one transform at LID_PIVOT (local transforms become zero) and rotate that.",
            "why_flat": "FBX bake_space_transform (project convention) misplaces meshes nested under a translated empty; "
                        "flat children of an identity root re-import exactly (checked).",
            "pivot_blender": r3(HINGE), "pivot_unity": unity(HINGE),
            "hinge_axis": "local X of the lid objects / LID_PIVOT (Blender X = Unity -X, along the long side)",
            "closed_angle_deg": 0.0, "open_angle_deg": OPEN_DEG,
            "open_rotation_blender": "lid objects rotation_euler.x = -%.0f deg" % OPEN_DEG,
            "open_rotation_unity": "pivot.localEulerAngles = (-%.0f, 0, 0) (verify once against REF_LidFront_Open); the front edge "
                                   "rises and swings to the rear" % OPEN_DEG,
            "ref_empty_open_front_edge": {"name": "REF_LidFront_Open", "blender": r3(front_open), "unity": unity(front_open)},
            "rear_clearance_needed_m": round(open_max_y - D / 2, 3),
            "rear_clearance_note": "the fully open lid reaches this far behind the body's back wall; keep it free of walls",
            "rule": "WORK_INVENTORY: E opens only when set down; lifting closes it; a carried cooler cannot be opened.",
        },
        "grips": {
            "note": "Bar centres of the two side handles. GRIP_R/GRIP_L = right/left hand of a carrier standing behind the cooler "
                    "with its front (sticker) facing away from him (same facing as the cooler). Bar axis = Blender Y / Unity Z; "
                    "palms face the box (inward along X).",
            "GRIP_R": {"blender": r3(grips["GRIP_R"]), "unity": unity(grips["GRIP_R"])},
            "GRIP_L": {"blender": r3(grips["GRIP_L"]), "unity": unity(grips["GRIP_L"])},
            "grip_span_m": round(2 * (W / 2 + HANDLE_OUT), 4), "bar_diameter_m": round(2 * (HANDLE_R + 0.0025), 4),
            "bar_clear_length_m": 0.11, "finger_clearance_m": round(HANDLE_OUT - HANDLE_R, 4),
        },
        "slots": {
            "count": 8, "layout": "2 columns (x) x 4 rows (y), numbered front row first, viewer's left (-X Blender) first; "
                      "rows 1-3 (slots 1-6) thin 0.267 x 0.090, row 4 (slots 7-8) wide 0.267 x 0.172",
            "slot_class_rule": "PROPOSAL for the lead: thin slots take any item up to 0.090 deep (every organ except the brain, "
                               "sealed organ bags, blood bags, syringes); wide slots take anything incl. the bare brain (0.160 deep). "
                               "Server puts deep items into a free wide slot and other items into thin slots first. One NPC's "
                               "seven organs = six thin + brain in a wide slot, one wide slot left. A third bare brain is refused "
                               "(a bagged brain is thin).",
            "anchor": "empty at the slot floor centre (cavity floor z=%.3f); identity rotation; place an item so its bounds bottom "
                      "sits on the anchor, wide face towards the front (organ models are authored front -Y, so no rotation)" % Z_FLOOR,
            "divider_height_m": round(DIV_TOP - Z_FLOOR, 4),
            "fits": "largest items: sealed ORGANBAG 0.256 x 0.075 x 0.287, lungs 0.218 x 0.071 x 0.200, heart 0.202 x 0.087 x 0.200, "
                    "liver 0.205 x 0.066 x 0.153, blood bag 0.160 x 0.033 x 0.274",
            "anchors": [{"name": nm, "class": cls, "box_xyz": [SLOT_W, dep, round(Z_RIM + POCKET - Z_FLOOR, 4)],
                         "blender": r3(co), "unity": unity(co),
                         "centre_blender": r3(co + Vector((0, 0, 0.15))), "centre_unity": unity(co + Vector((0, 0, 0.15)))}
                        for nm, co, dep, cls in slots],
        },
        "colliders": {
            "convention": "UCX_ naming only; Unity does not convert these automatically (same as G34 manifest). Use as BoxColliders.",
            "UCX_SM_PortableFridge_Body_00": "solid body box 0.60 x 0.52 x 0.33 (cavity filled: sockets are picked by aim point)",
            "UCX_SM_PortableFridge_Body_01/_02": "side handles",
            "UCX_SM_PortableFridge_Lid_00": "lid box, origin on the hinge like the lid meshes (rotate it with them)",
        },
        "lods": {"LOD0_tris": st["SM_PortableFridge_Body_LOD0"] + st["SM_PortableFridge_Lid_LOD0"],
                 "LOD1_tris": st["SM_PortableFridge_Body_LOD1"] + st["SM_PortableFridge_Lid_LOD1"],
                 "per_object": st, "budget_LOD0": 2500,
                 "note": "_LOD0/_LOD1 suffixes for Unity; all four LOD meshes are children of the root, so one LODGroup "
                         "covers body and lid (keep it after re-parenting the lid under its pivot)."},
        "van_mount": {
            "fbx": os.path.join(ROOT, "PortableFridge_W86_VanMount_v01.fbx"),
            "objects": "PortableFridge_W86_VanMount (root) -> SM_PortableFridge_VanMount_LOD0/LOD1, UCX_..._00-04, COOLER_SOCKET, REF_WallPlane",
            "origin": "floor level, centre of the cooler footprint",
            "COOLER_SOCKET": {"blender": [0, 0, M_PAD], "unity": unity((0, 0, M_PAD)),
                              "use": "cooler root goes here with identity rotation; front faces into the bay, hinge to the wall"},
            "wall_plane": {"blender_y": M_WALL_Y, "unity_z": -M_WALL_Y,
                           "use": "rear face of the wall plate; bolt the mount with this plane on the bay wall"},
            "dims_xyz_blender": r3(mmx - mmn),
            "lid_clearance_m": round(M_WALL_Y - omx.y, 4), "standoff_m": round(M_WALL_Y - 0.006 - (M_INNER_Y + 0.006), 4),
            "lid_clearance": "fully open lid stays %.3f m in front of the wall plane (stand-off %.3f m)" % (M_WALL_Y - omx.y, M_WALL_Y - 0.006 - (M_INNER_Y + 0.006)),
            "rules": "Storage system $1 500 = 2 open cooler mounts; a mounted cooler keeps its id/contents and can be opened in place; "
                     "nothing falls out while driving.",
        },
    }
    img.pack()
    with open(os.path.join(OUT, "PortableFridge_W86_v01.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "PortableFridge_W86_v01.blend"), compress=True)
    print("STATS", json.dumps(st), "closed", r3(bmx - bmn), "open", r3(omx - omn), "mount", r3(mmx - mmn))


main()
