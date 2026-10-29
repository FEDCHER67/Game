"""Workshop_W86 vehicle lift v01 - two-post overhead (clear-floor) lift over the middle-bay pit, palette A.

Run headless:
  blender -b --factory-startup -noaudio --python build_workshop_w86_lift_v01.py -- [--force]
Outputs (ArtSource/Buildings/Workshop_W86/):
  Workshop_W86_lift_v01.fbx    Lift_Static, Lift_Carriage_L/R, Lift_Arms_FL/FR/RL/RR (top-level nodes, children
                               *_LOD0 / *_LOD1 / UCX_*), same root transform as the building (place like the props FBX)
  Workshop_W86_lift_v01.json   placement, moving parts, travel, arm pads / van contact points, control box, checks
  Workshop_W86_lift_v01.blend  lift objects only (the checks load the building from Workshop_W86_v01.blend, read-only)
Blender: Z up, front of the building = -Y, metres.  Unity local: (x, y, z) = (-bx, bz, -by).
Naming: L / R = the van driver's left / right with the van parked nose to the back wall (L = Unity +X, east side;
R = Unity -X, west side, power unit + control box).  F / R in arm names = front (van nose, back wall, Unity -Z) / rear (door).
"""
import json
import math
import os
import sys
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ws_lib_v01 import MB  # noqa: E402
import build_workshop_w86_v01 as B  # noqa: E402
import check_workshop_w86_v01 as C  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FORCE = '--force' in ARGS
REV = 'v01'
OUT = ARGS[ARGS.index('--out') + 1] if '--out' in ARGS else B.OUT   # --out <dir>: test runs outside the deliverable folder
SRC_BLEND = os.path.join(B.OUT, 'Workshop_W86_v01.blend')

M_RED, M_YEL, M_DARK, M_WORN = B.M_RED, B.M_YEL, B.M_DARK, B.M_WORN
M_RUB, M_WHITE, M_EMIT = B.M_RUB, B.M_WHITE, B.M_EMIT
M_BLK = B.M_RUB          # black of the yellow/black hazard stripes (plain #2B2B2E)

# ============================================================================ layout (Blender, relative to the lift centre)
LC = Vector((0.0, B.VAN['centre'][1], 0.0))      # lift centre on the floor = van park point (Blender (0, -2.4, 0))
PXC = 1.68                 # post centre |x|
XI, XO = 1.53, 1.83        # post inner (lip) face / outer (web) face |x|
HYP = 0.18                 # post half depth (y)
TW = 0.02                  # sheet thickness of the C-section
SL = 0.10                  # half width of the slot facing the van
CH = 0.015                 # outer corner chamfer
BAND = (0.022, 0.55)       # hazard stripe band on the post foot
STRIPE = 0.10              # stripe width (45 deg)
POST_TOP = 4.45
BP = (1.45, 1.96, 0.30, 0.022)    # base plate: x0, x1, half y, thickness
BEAM = (4.22, 4.42, 0.07)         # overhead beam z0, z1, half y
BAR = (4.10, 4.15, 0.025, 1.25)   # shut-off bar z0, z1, half y, half length
CYL_X = 1.66               # hydraulic cylinder axis |x| (inside the post channel)
TRAVEL = 1.6
CAR = dict(x0=1.36, x1=1.525, hy=0.17, z0=0.035, z1=1.04)   # carriage front plate (|x| range)
PIN_X, PIN_DY = 1.28, 0.13        # arm hinge pins (|x|, +-y from the post centre line)
PAD_X, PAD_DY = 0.62, 0.90        # engaged pad centres (|x|, +-y from the lift centre)
PAD_TOP = 0.30
ARM_L = math.hypot(PIN_X - PAD_X, PAD_DY - PIN_DY)
ARM_PHI = math.degrees(math.atan2(PIN_X - PAD_X, PAD_DY - PIN_DY))   # swing from stowed (parallel to the van) to engaged
VAN_CONTACT_Y = 0.35       # underside of the team van at its sills (VAN-TIER0-ASTRA-001 BODY_BOTTOM)
VAN_ENV = dict(half_w=1.0, half_l=2.6, h=2.4, bottom=0.36)   # brief envelope 5.2 x 2.0 x 2.4 (render dummy)
ASTRA = dict(axles=(1.60, -1.56), wheel_x=0.80, wheel_w=0.24, wheel_r=0.37)  # van-local fwd axle +1.60 toward the nose


# ============================================================================ geometry helpers
def mirror_merge(dst, src, M):
    """Merge src into dst with matrix M; mirrored transforms (det < 0) get their winding reversed."""
    R = M.to_3x3()
    Rn = R.inverted().transposed()
    flip = R.determinant() < 0
    for f, m in zip(src.F, src.M):
        pts = [M @ src.P[i] for i in f]
        nl = [(Rn @ src.N[i]).normalized() for i in f]
        if flip:
            pts.reverse()
            nl.reverse()
        dst.face(pts, m, normals=nl)


SX = Matrix.Scale(-1, 4, Vector((1, 0, 0)))
SY = Matrix.Scale(-1, 4, Vector((0, 1, 0)))


def cbox(mb, mn, mx, c, mat, sharp=(), skip=(), mats=None):
    """Box with 45-degree chamfered edges.  sharp: faces whose edges stay square (contact faces); skip: faces not emitted."""
    X, Y, Z = (mn[0], mx[0]), (mn[1], mx[1]), (mn[2], mx[2])
    nm = {('x', 0): 'x-', ('x', 1): 'x+', ('y', 0): 'y-', ('y', 1): 'y+', ('z', 0): 'z-', ('z', 1): 'z+'}
    nv = {'x-': (-1, 0, 0), 'x+': (1, 0, 0), 'y-': (0, -1, 0), 'y+': (0, 1, 0), 'z-': (0, 0, -1), 'z+': (0, 0, 1)}
    axes = 'xyz'

    def ce(f1, f2):
        return 0.0 if (f1 in sharp or f2 in sharp) else c

    def fv(axis, s):
        p = [X[s[0]], Y[s[1]], Z[s[2]]]
        fa = nm[(axis, s[axes.index(axis)])]
        for k, ax in enumerate(axes):
            if ax == axis:
                continue
            fb = nm[(ax, s[k])]
            p[k] += (1 if s[k] == 0 else -1) * ce(fa, fb)
        return Vector(p)

    def mat_of(f):
        return (mats or {}).get(f, mat)
    # main faces
    for k, ax in enumerate(axes):
        for sd in (0, 1):
            f = nm[(ax, sd)]
            if f in skip:
                continue
            o = [a for a in range(3) if a != k]
            corners = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                s = [0, 0, 0]
                s[k] = sd
                s[o[0]], s[o[1]] = a, b
                corners.append(fv(ax, s))
            mb.face(corners, mat_of(f), want=nv[f])
    # edge bevels
    for k1 in range(3):
        for k2 in range(k1 + 1, 3):
            k3 = 3 - k1 - k2
            for s1 in (0, 1):
                for s2 in (0, 1):
                    f1, f2 = nm[(axes[k1], s1)], nm[(axes[k2], s2)]
                    if ce(f1, f2) == 0.0 or f1 in skip or f2 in skip:
                        continue
                    pts = []
                    for s3, which in ((0, k1), (1, k1), (1, k2), (0, k2)):
                        s = [0, 0, 0]
                        s[k1], s[k2], s[k3] = s1, s2, s3
                        pts.append(fv(axes[which], s))
                    w = Vector(nv[f1]) + Vector(nv[f2])
                    mb.face(pts, mat_of(f1), want=w)
    # corner triangles
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                s = (sx, sy, sz)
                fs = [nm[(axes[k], s[k])] for k in range(3)]
                if any(f in sharp or f in skip for f in fs):
                    continue
                w = sum((Vector(nv[f]) for f in fs), Vector())
                mb.face([fv('x', s), fv('y', s), fv('z', s)], mat, want=w)


def clip_half(poly, fn):
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = fn(*p), fn(*q)
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def poly_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def stripes_rect(mb, O, eu, ev, u0, u1, v0, v1, mats, want, uoff=0.0, w=STRIPE, slope=1.0):
    """Planar rectangle O + eu*u + ev*v split into 45-degree hazard stripes (no overlays -> no z-fighting)."""
    O, eu, ev = Vector(O), Vector(eu), Vector(ev)
    base = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    vals = [u + uoff + slope * v for u, v in base]
    for k in range(math.floor(min(vals) / w), math.ceil(max(vals) / w)):
        p = clip_half(base, lambda u, v, k=k: (u + uoff + slope * v) - k * w)
        p = clip_half(p, lambda u, v, k=k: (k + 1) * w - (u + uoff + slope * v)) if len(p) >= 3 else []
        if len(p) < 3 or abs(poly_area(p)) < 1e-6:
            continue
        mb.face([O + eu * u + ev * v for u, v in p], mats[k % 2], want=want)


def hexbolt(mb, p, d, r=0.011, h=0.011, mat=M_WORN):
    """Hex bolt head sitting on a surface at p, protruding along d."""
    p, d = Vector(p), Vector(d).normalized()
    mb.cyl(p, p + d * h, r, mat, n=6, caps=(False, True), smooth=False)


def anchor_bolt(mb, x, y, z):
    mb.cyl((x, y, z), (x, y, z + 0.018), 0.02, M_WORN, n=6, caps=(False, True), smooth=False)
    mb.cyl((x, y, z + 0.018), (x, y, z + 0.03), 0.009, M_WORN, n=6, caps=(False, True))


ZV = Vector((0, 0, 1))


# ============================================================================ static part
def post_poly():
    xi, xo, hy, t, sl, c = XI, XO, HYP, TW, SL, CH
    return [(xi, -sl), (xi, -hy + c), (xi + c, -hy), (xo - c, -hy), (xo, -hy + c), (xo, hy - c), (xo - c, hy),
            (xi + c, hy), (xi, hy - c), (xi, sl), (xi + t, sl), (xi + t, hy - t), (xo - t, hy - t), (xo - t, -hy + t),
            (xi + t, -hy + t), (xi + t, -sl)]


OUTER_EDGES = [15] + list(range(10))   # visible chain (slot face, front lip, ..., back lip, slot face)
INNER_EDGES = list(range(10, 15))       # inside of the channel


def post_sides(mb, z0, z1, band, lod):
    P = post_poly()
    n = len(P)
    sg = 1.0 if poly_area(P) > 0 else -1.0
    u = 0.0
    for i in OUTER_EDGES + INNER_EDGES:
        a = Vector((P[i][0], P[i][1], 0.0))
        b = Vector((P[(i + 1) % n][0], P[(i + 1) % n][1], 0.0))
        d = b - a
        ln = d.length
        nrm = Vector((d.y, -d.x, 0.0)).normalized() * sg
        if i in INNER_EDGES:
            mb.face([a + ZV * z0, b + ZV * z0, b + ZV * z1, a + ZV * z1], M_DARK, want=nrm)
            continue
        if band:
            stripes_rect(mb, a, d / ln, ZV, 0.0, ln, z0, z1, (M_YEL, M_BLK), nrm, uoff=u)
        else:
            mb.face([a + ZV * z0, b + ZV * z0, b + ZV * z1, a + ZV * z1], M_RED, want=nrm)
        u += ln


def post_assembly(lod):
    """One post with base plate, cylinder, beam mounting plate, top cap and labels (R side, +X)."""
    mb = MB('post')
    x0, x1, hy, t = BP
    if lod == 0:
        cbox(mb, (x0, -hy, 0.0), (x1, hy, t), 0.006, M_DARK, sharp=('z-',), skip=('z-',))
        for bx in (x0 + 0.05, x1 - 0.05):
            for by in (-hy + 0.05, hy - 0.05):
                anchor_bolt(mb, bx, by, t)
        post_sides(mb, BAND[0], BAND[1], True, lod)
        post_sides(mb, BAND[1], POST_TOP, False, lod)
        # top cap plate
        o = 0.008
        cbox(mb, (XI - o, -HYP - o, POST_TOP), (XO + o, HYP + o, POST_TOP + 0.02), 0.004, M_RED)
        # safety-lock ladder on the web inside the channel (seen through the slot)
        z = 0.5
        while z < 2.55:
            mb.box((XO - TW - 0.025, -0.05, z), (XO - TW, 0.05, z + 0.025), M_WORN, skip=('x+',))
            z += 0.2
        # hydraulic cylinder (pull type, hangs from the top of the post; the rod belongs to the carriage)
        mb.cyl((CYL_X, 0, 2.72), (CYL_X, 0, 2.80), 0.065, M_WORN, n=10)
        mb.cyl((CYL_X, 0, 2.80), (CYL_X, 0, 4.30), 0.055, M_DARK, n=10, caps=(False, False))
        mb.cyl((CYL_X, 0, 4.30), (CYL_X, 0, 4.42), 0.065, M_WORN, n=10)
        mb.box((CYL_X + 0.065, -0.03, 4.33), (XO - TW, 0.03, 4.40), M_DARK, skip=('x+',))
        # beam mounting plate on the lips + bolts
        cbox(mb, (XI - 0.02, -0.17, 4.15), (XI, 0.17, 4.44), 0.005, M_RED, sharp=('x+',), skip=('x+',))
        for by in (-0.12, 0.12):
            for bz in (4.19, 4.40):
                hexbolt(mb, (XI - 0.02, by, bz), (-1, 0, 0))
        # hose fitting on the top cap
        cbox(mb, (1.705, -0.035, POST_TOP + 0.02), (1.775, 0.035, POST_TOP + 0.085), 0.006, M_WORN, sharp=('z-',), skip=('z-',))
        # warning label + capacity plate on the front face (toward the door)
        yf = -HYP
        tri = [(1.64 - 0.065, 1.63), (1.64 + 0.065, 1.63), (1.64, 1.745)]                                  # warning triangle
        mb.prism(tri, 0.0, 0.004, M_YEL, lambda s, tt, w: Vector((s, yf - w, tt)), caps=(False, True))
        mb.box((1.57, yf - 0.003, 1.43), (1.71, yf, 1.59), M_WHITE, skip=('y+',))                           # instruction plate
        mb.box((1.58, yf - 0.003, 1.28), (1.70, yf, 1.38), M_WORN, skip=('y+',))                            # capacity plate
        for rx in (1.59, 1.69):
            for rz in (1.29, 1.37):
                mb.cyl((rx, yf - 0.003, rz), (rx, yf - 0.008, rz), 0.004, M_WORN, n=6, caps=(False, True))   # rivets
    else:
        mb.box((x0, -hy, 0.0), (x1, hy, t), M_DARK, skip=('z-',))
        mb.box((XI, -HYP, t), (XO, HYP, BAND[1]), M_YEL, skip=('z-', 'z+'))
        mb.box((XI, -HYP, BAND[1]), (XO, HYP, POST_TOP + 0.02), M_RED, skip=('z-',))
        mb.box((XI - 0.02, -0.17, 4.15), (XI, 0.17, 4.44), M_RED, skip=('x+',))
    return mb


def static_mesh(lod):
    mb = MB('Lift_Static_LOD%d' % lod)
    post = post_assembly(lod)
    mirror_merge(mb, post, Matrix.Identity(4))
    mirror_merge(mb, post, SX)
    z0, z1, hy = BEAM
    if lod == 0:
        # overhead beam
        cbox(mb, (-XI + 0.02, -hy, z0), (XI - 0.02, hy, z1), 0.01, M_RED, sharp=('x-', 'x+'), skip=('x-', 'x+'))
        # lift sign on the beam (white plate with dark "lettering" bars)
        mb.box((-0.26, -hy - 0.003, 4.26), (0.26, -hy, 4.38), M_WHITE, skip=('y+',))
        for zz, w in ((4.335, 0.20), (4.30, 0.13)):
            mb.box((-w, -hy - 0.008, zz), (w, -hy - 0.003, zz + 0.022), M_BLK, skip=('y+',))
        # shut-off bar (yellow/black bands) on two hangers + limit switch
        bz0, bz1, bhy, bhl = BAR
        nseg = 20
        for i in range(nseg):
            xa = -bhl + 2 * bhl * i / nseg
            xb = -bhl + 2 * bhl * (i + 1) / nseg
            sk = tuple(s for s, cond in (('x-', i > 0), ('x+', i < nseg - 1)) if cond)
            mb.box((xa, -bhy, bz0), (xb, bhy, bz1), M_YEL if i % 2 == 0 else M_BLK, skip=sk)
        for hx in (-1.10, 1.10):
            mb.box((hx - 0.012, -0.012, bz1), (hx + 0.012, 0.012, z0), M_DARK, skip=('z-', 'z+'))
        mb.box((1.27, -0.05, 4.12), (1.40, 0.05, z0), M_DARK, skip=('z+',))
        mb.cyl((1.27, 0, 4.135), (bhl + 0.005, 0, 4.135), 0.008, M_WORN, n=6, caps=(False, True))
        # equaliser cables along the back of the beam, with guides
        for cz in (4.27, 4.37):
            mb.cyl((-XI + 0.02, hy + 0.008, cz), (XI - 0.02, hy + 0.008, cz), 0.006, M_WORN, n=4, caps=(False, False))
        for gx in (-0.8, 0.0, 0.8):
            mb.box((gx - 0.015, hy, 4.255), (gx + 0.015, hy + 0.02, 4.385), M_DARK, skip=('y-',))
        # hydraulic crossover hose over the beam, clipped to it
        mb.cyl((-1.705, 0, POST_TOP + 0.05), (1.705, 0, POST_TOP + 0.05), 0.012, M_RUB, n=6, caps=(False, False))
        for cx in (-1.2, -0.4, 0.4, 1.2):
            mb.box((cx - 0.012, -0.02, z1), (cx + 0.012, 0.02, POST_TOP + 0.072), M_DARK, skip=('z-',))
        # ---- power unit + control box on the R post (outer face, +X)
        cbox(mb, (XO, -0.15, 0.25), (XO + 0.02, 0.15, 1.65), 0.005, M_DARK, sharp=('x-',), skip=('x-',))
        for by in (-0.13, 0.13):
            for bz in (0.28, 1.625):
                hexbolt(mb, (XO + 0.02, by, bz), (1, 0, 0), r=0.009, h=0.008)
        xm = XO + 0.02
        cbox(mb, (xm, -0.10, 0.30), (2.03, 0.10, 0.60), 0.015, M_WHITE, sharp=('x-',), skip=('x-',))      # oil tank
        mb.cyl((1.97, 0.08, 0.60), (1.97, 0.08, 0.625), 0.015, M_DARK, n=8, caps=(False, True))          # filler cap
        cbox(mb, (xm, -0.06, 0.60), (1.99, 0.06, 0.70), 0.008, M_WORN, sharp=('x-', 'z-'), skip=('x-', 'z-'))  # pump block
        mb.cyl((1.94, 0, 0.70), (1.94, 0, 1.02), 0.08, M_DARK, n=16)                                      # motor
        for fz in (0.76, 0.84, 0.92):
            mb.cyl((1.94, 0, fz), (1.94, 0, fz + 0.012), 0.086, M_DARK, n=16, caps=(True, True))
        mb.cyl((1.99, 0.02, 0.65), (2.005, 0.02, 0.65), 0.012, M_WORN, n=6, caps=(False, True))          # lowering lever
        mb.cyl((2.0, 0.02, 0.65), (2.05, 0.02, 0.74), 0.007, M_RED, n=6, caps=(False, False))
        mb.cyl((2.05, 0.02, 0.74), (2.06, 0.02, 0.76), 0.014, M_RUB, n=8)
        # control box (galvanised) with door, hinges and buttons, facing +X
        cbox(mb, (xm, -0.12, 1.20), (1.99, 0.12, 1.60), 0.01, M_WORN, sharp=('x-',), skip=('x-',))
        cbox(mb, (1.99, -0.105, 1.215), (1.996, 0.105, 1.585), 0.002, M_WORN, sharp=('x-',), skip=('x-',))
        for hz in (1.26, 1.50):
            mb.cyl((1.993, -0.112, hz), (1.993, -0.112, hz + 0.05), 0.006, M_DARK, n=6)
        xf = 1.996
        mb.cyl((xf, 0.0, 1.50), (xf + 0.006, 0.0, 1.50), 0.042, M_YEL, n=12, caps=(False, True))          # E-stop
        mb.cyl((xf + 0.006, 0.0, 1.50), (xf + 0.02, 0.0, 1.50), 0.014, M_DARK, n=8, caps=(False, False))
        mb.cyl((xf + 0.02, 0.0, 1.50), (xf + 0.036, 0.0, 1.50), 0.032, M_RED, n=12, caps=(True, True))
        for by, m in ((-0.05, M_WHITE), (0.05, M_BLK)):                                                    # up / down
            mb.cyl((xf, by, 1.37), (xf + 0.005, by, 1.37), 0.026, M_DARK, n=10, caps=(False, True))
            mb.cyl((xf + 0.005, by, 1.37), (xf + 0.015, by, 1.37), 0.018, m, n=10, caps=(False, True))
        mb.cyl((xf, 0.0, 1.27), (xf + 0.01, 0.0, 1.27), 0.014, M_WORN, n=8, caps=(False, True))           # key switch
        mb.box((xf + 0.01, -0.003, 1.255), (xf + 0.016, 0.003, 1.285), M_DARK, skip=('x-',))
        mb.cyl((xf, 0.07, 1.27), (xf + 0.008, 0.07, 1.27), 0.009, M_EMIT, n=8, caps=(False, True))         # pilot lamp
        mb.box((xf, -0.075, 1.42), (xf + 0.005, 0.075, 1.445), M_WHITE, skip=('x-',))                      # label strip
        # motor conduit, supply cable to the floor gland, cable clips
        mb.cyl((1.94, 0, 1.02), (1.94, 0, 1.20), 0.012, M_DARK, n=6, caps=(False, False))
        mb.tube([(1.92, 0.09, 1.20), (1.92, 0.13, 1.16), (1.92, 0.13, 0.06)], 0.009, M_RUB, n=6, caps=(False, False))
        mb.box((1.89, 0.10, BP[3]), (1.95, 0.16, 0.06), M_DARK, skip=('z-',))
        for cz in (0.40, 0.90):
            mb.box((xm, 0.12, cz - 0.01), (1.93, 0.14, cz + 0.01), M_DARK, skip=('x-',))
        # hydraulic hose: pump -> up the front face of the R post -> fitting on the top cap
        hp = [(1.93, -0.06, 0.66), (1.93, -0.205, 0.66), (1.93, -0.205, 1.62), (1.74, -0.205, 1.80),
              (1.74, -0.205, POST_TOP + 0.05), (1.74, -0.035, POST_TOP + 0.05)]
        mb.tube(hp, 0.012, M_RUB, n=6, caps=(False, False))
        mb.cyl((1.93, -0.06, 0.66), (1.93, -0.085, 0.66), 0.018, M_WORN, n=6, caps=(False, True))          # port fitting
        for cz in (2.3, 3.1, 3.9):
            mb.box((1.725, -0.22, cz - 0.012), (1.755, -HYP, cz + 0.012), M_DARK, skip=('y+',))
    else:
        mb.box((-XI, -hy, z0), (XI, hy, z1), M_RED, skip=('x-', 'x+'))
        bz0, bz1, bhy, bhl = BAR
        mb.box((-bhl, -bhy, bz0), (bhl, bhy, bz1), M_YEL)
        mb.box((XO, -0.10, 0.30), (2.03, 0.10, 1.02), M_DARK, skip=('x-',))
        mb.box((XO, -0.12, 1.20), (1.99, 0.12, 1.60), M_WORN, skip=('x-',))
        mb.tube([(1.93, -0.06, 0.66), (1.93, -0.205, 0.66), (1.93, -0.205, 1.62), (1.74, -0.205, 1.80),
                 (1.74, -0.205, POST_TOP + 0.02)], 0.014, M_RUB, n=4, caps=(False, True))
    return mb


STATIC_UCX = [((XI, -HYP, 0.0), (XO, HYP, POST_TOP + 0.02)),          # R post
              ((-XO, -HYP, 0.0), (-XI, HYP, POST_TOP + 0.02)),        # L post
              ((XO, -0.15, 0.25), (2.04, 0.15, 1.65))]                # R power unit + control box (on the post)


# ============================================================================ carriage (R, local to its pivot = post centre on the floor)
def carriage_mesh(lod):
    mb = MB('carriage')
    ox = PXC
    x0, x1 = CAR['x0'] - ox, CAR['x1'] - ox
    hy, z0, z1 = CAR['hy'], CAR['z0'], CAR['z1']
    px = PIN_X - ox
    if lod == 0:
        cbox(mb, (x0, -hy, z0), (x1, hy, z1), 0.012, M_RED)
        mb.box((x1, -0.085, 0.10), (XI + TW + 0.01 - ox, 0.085, 1.00), M_DARK, skip=('x-', 'x+'))            # neck through the slot
        mb.box((XI + TW + 0.01 - ox, -0.14, 0.10), (XI + TW + 0.01 - ox + 0.20, 0.14, 1.00), M_DARK)         # slider block
        mb.cyl((CYL_X - ox, 0, 1.05), (CYL_X - ox, 0, 2.79), 0.022, M_WORN, n=8, caps=(False, True))       # cylinder rod
        mb.box((CYL_X - ox - 0.03, -0.03, 1.00), (CYL_X - ox + 0.03, 0.03, 1.05), M_WORN, skip=('z-',))     # rod clevis
        for dy in (PIN_DY, -PIN_DY):
            dpl = [(x0, dy - 0.04)] + [(px + 0.04 * math.cos(math.radians(a)), dy + 0.04 * math.sin(math.radians(a)))
                                        for a in range(-90, -271, -30)] + [(x0, dy + 0.04)]
            mb.prism(dpl, 0.155, 0.185, M_RED, lambda s, tt, w: Vector((s, tt, w)), skip_sides=(len(dpl) - 1,))  # hinge bracket
            mb.cyl((px, dy, 0.185), (px, dy, 0.205), 0.028, M_WORN, n=8, caps=(False, True))             # pin head
            mb.cyl((px, dy, 0.022), (px, dy, 0.04), 0.024, M_WORN, n=6, caps=(True, False), smooth=False)  # pin nut
            mb.cyl((px, dy, 0.04), (px, dy, 0.155), 0.02, M_WORN, n=8, caps=(False, False))               # pin (through the arm boss)
        mb.box((x0 - 0.015, -0.10, 0.45), (x0, 0.10, 0.85), M_RUB, skip=('x+',))                          # door guard
        for by in (-0.135, 0.135):
            for bz in (0.30, 0.95):
                hexbolt(mb, (x0, by, bz), (-1, 0, 0))
        mb.box((x0 + 0.02, -0.08, z1), (x1 - 0.02, 0.08, z1 + 0.02), M_RUB, skip=('z-',))                 # top bumper
        mb.cyl((x0 + 0.05, 0.125, z1), (x0 + 0.05, 0.125, z1 + 0.07), 0.007, M_RED, n=6, caps=(False, False))  # lock release
        mb.cyl((x0 + 0.05, 0.125, z1 + 0.07), (x0 + 0.05, 0.125, z1 + 0.095), 0.016, M_RUB, n=8)
    else:
        mb.box((x0, -hy, z0), (x1, hy, z1), M_RED)
        for dy in (PIN_DY, -PIN_DY):
            mb.box((px - 0.04, dy - 0.04, 0.155), (x0, dy + 0.04, 0.205), M_RED, skip=('x+',))
    return mb


CARRIAGE_UCX = [((CAR['x0'] - PXC, -CAR['hy'], CAR['z0']), (CAR['x1'] - PXC, CAR['hy'], CAR['z1'] + 0.02))]


# ============================================================================ arm (FR, local to its pin on the floor, stowed along +Y)
def arm_mesh(lod):
    mb = MB('arm')
    L = ARM_L
    if lod == 0:
        mb.cyl((0, 0, 0.04), (0, 0, 0.15), 0.07, M_RED, n=12)                                          # boss
        cbox(mb, (-0.065, 0.0, 0.045), (0.065, 0.72, 0.125), 0.01, M_RED, sharp=('y-',), skip=('y-',))  # outer arm
        cbox(mb, (-0.048, 0.60, 0.06), (0.048, L, 0.112), 0.006, M_YEL, sharp=('y-', 'y+'), skip=('y-', 'y+'))  # telescopic tip
        mb.cyl((0, L, 0.045), (0, L, 0.145), 0.075, M_RED, n=12)                                       # pad cup
        mb.cyl((0, L, 0.145), (0, L, 0.255), 0.032, M_WORN, n=8, caps=(False, False))                  # screw
        for rz in (0.175, 0.21):
            mb.cyl((0, L, rz), (0, L, rz + 0.008), 0.037, M_WORN, n=8)
        mb.cyl((0, L, 0.255), (0, L, 0.268), 0.065, M_DARK, n=12, caps=(True, False))                  # pad plate
        mb.cyl((0, L, 0.268), (0, L, PAD_TOP), 0.062, M_RUB, n=12, caps=(False, True))                 # rubber pad
        mb.tube([(0.065, 0.48, 0.085), (0.10, 0.50, 0.085), (0.10, 0.62, 0.085), (0.065, 0.64, 0.085)],
                0.008, M_WORN, n=6, caps=(False, False))                                               # pull handle
        mb.box((-0.04, 0.70, 0.125), (0.04, 0.72, 0.135), M_DARK, skip=('z-',))                         # stop collar
    else:
        mb.cyl((0, 0, 0.04), (0, 0, 0.15), 0.07, M_RED, n=6)
        mb.box((-0.065, 0.0, 0.045), (0.065, 0.72, 0.125), M_RED, skip=('y-',))
        mb.box((-0.048, 0.72, 0.06), (0.048, L, 0.112), M_YEL, skip=('y-', 'y+'))
        mb.cyl((0, L, 0.045), (0, L, 0.255), 0.07, M_RED, n=6)
        mb.cyl((0, L, 0.255), (0, L, PAD_TOP), 0.062, M_RUB, n=6, caps=(False, True))
    return mb


ARM_UCX = [((-0.07, -0.07, 0.04), (0.07, ARM_L - 0.07, 0.15)), ((-0.075, ARM_L - 0.075, 0.04), (0.075, ARM_L + 0.075, PAD_TOP))]

# arm id -> (side sign x, side sign y, mirror matrix)
ARMS = {'FR': (1, 1, Matrix.Identity(4)), 'FL': (-1, 1, SX), 'RR': (1, -1, SY), 'RL': (-1, -1, SX @ SY)}


def arm_engaged_blender_deg(aid):
    sx, sy, _ = ARMS[aid]
    # stowed direction (0, sy); engaged direction (-sx*(PIN_X-PAD_X), sy*(PAD_DY-PIN_DY)); CCW positive about +Z
    a0 = math.atan2(sy, 0.0)
    a1 = math.atan2(sy * (PAD_DY - PIN_DY), -sx * (PIN_X - PAD_X))
    d = math.degrees(a1 - a0)
    d = (d + 180) % 360 - 180
    return d


# ============================================================================ build
def link_new(coll, name, data=None):
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    return ob


def make_part(coll, lib, name, loc, mb0, mb1, ucx_boxes):
    holder = link_new(coll, name)
    holder.location = loc
    holder.empty_display_size = 0.25
    o0 = mb0.build(lib, coll, name=name + '_LOD0')
    o0.parent = holder
    o1 = mb1.build(lib, coll, name=name + '_LOD1')
    o1.parent = holder
    for j, (mn, mx) in enumerate(ucx_boxes):
        pts = [(x, y, z) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
        B.hull_object('UCX_%s_%02d' % (name, j + 1), pts, coll, holder)
    return holder, o0, o1


def mesh_from(mb_src, M, name):
    mb = MB(name)
    mirror_merge(mb, mb_src, M)
    return mb


def build_lift(lib, coll):
    parts = {}
    # static
    s0, s1 = static_mesh(0), static_mesh(1)
    parts['Lift_Static'] = make_part(coll, lib, 'Lift_Static', LC.copy(), s0, s1, STATIC_UCX)
    # carriages
    c0, c1 = carriage_mesh(0), carriage_mesh(1)
    for side, sx in (('R', 1), ('L', -1)):
        M = Matrix.Identity(4) if sx > 0 else SX
        ucx = []
        for mn, mx in CARRIAGE_UCX:
            a, b = M @ Vector(mn), M @ Vector(mx)
            ucx.append((tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3))))
        parts['Lift_Carriage_' + side] = make_part(coll, lib, 'Lift_Carriage_' + side, LC + Vector((sx * PXC, 0, 0)),
                                                   mesh_from(c0, M, 'c0'), mesh_from(c1, M, 'c1'), ucx)
    # arms (stowed: parallel to the van, pointing away from the post centre line)
    a0, a1 = arm_mesh(0), arm_mesh(1)
    for aid, (sx, sy, M) in ARMS.items():
        ucx = []
        for mn, mx in ARM_UCX:
            a, b = M @ Vector(mn), M @ Vector(mx)
            ucx.append((tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3))))
        parts['Lift_Arms_' + aid] = make_part(coll, lib, 'Lift_Arms_' + aid, LC + Vector((sx * PIN_X, sy * PIN_DY, 0)),
                                              mesh_from(a0, M, 'a0'), mesh_from(a1, M, 'a1'), ucx)
    return parts


def set_pose(parts, lift=0.0, engaged=False):
    for name, (h, o0, o1) in parts.items():
        base = h.get('rest_loc')
        if base is None:
            h['rest_loc'] = list(h.location)
            base = h['rest_loc']
        if name == 'Lift_Static':
            continue
        h.location = (base[0], base[1], base[2] + lift)
        if name.startswith('Lift_Arms_'):
            h.rotation_euler = (0, 0, math.radians(arm_engaged_blender_deg(name[-2:])) if engaged else 0.0)
    bpy.context.view_layer.update()


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def U(p):
    return [round(-p[0], 4), round(p[2], 4), round(-p[1], 4)]


def uyaw(bdeg):
    return round(-bdeg, 2)


# ============================================================================ checks
def world_verts(o):
    M = o.matrix_world
    return [M @ v.co for v in o.data.vertices]


def world_tri_list(objs):
    vs, ts = [], []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        M = o.matrix_world
        base = len(vs)
        vs += [M @ v.co for v in me.vertices]
        ts += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
    return vs, ts


def islands_floating(o, seeds_fn, tol=0.004):
    """Weld coincident verts, find solid islands, flood from the seed islands through touching/overlapping AABBs."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.verts.ensure_lookup_table()
    seen, isl = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            comp.append(a.co.copy())
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        lo = Vector((min(p.x for p in comp), min(p.y for p in comp), min(p.z for p in comp)))
        hi = Vector((max(p.x for p in comp), max(p.y for p in comp), max(p.z for p in comp)))
        isl.append((lo, hi))
    bm.free()
    reached = set(i for i, (lo, hi) in enumerate(isl) if seeds_fn(lo, hi))
    if not reached:
        big = max(range(len(isl)), key=lambda i: (isl[i][1] - isl[i][0]).length)
        reached.add(big)
    frontier = list(reached)
    while frontier:
        i = frontier.pop()
        lo, hi = isl[i]
        for j, (lo2, hi2) in enumerate(isl):
            if j in reached:
                continue
            if all(lo[k] - tol <= hi2[k] and lo2[k] <= hi[k] + tol for k in range(3)):
                reached.add(j)
                frontier.append(j)
    return [dict(lo=[round(c, 3) for c in isl[i][0]], hi=[round(c, 3) for c in isl[i][1]]) for i in range(len(isl)) if i not in reached], len(isl)


def run_checks(parts, bobjs, props):
    res = {}
    lod0 = {n: p[1] for n, p in parts.items()}
    static0 = lod0['Lift_Static']
    moving0 = [o for n, o in lod0.items() if n != 'Lift_Static']
    bvs, bts = world_tri_list(bobjs)
    bvh_b = BVHTree.FromPolygons(bvs, bts)
    building_verts = bvs

    def lift_vs(objs):
        out = []
        for o in objs:
            out += world_verts(o)
        return out

    # ---- z-fighting: lift vs lift and lift vs building interior, in three poses
    zf = {}
    for pose, (lift, eng) in (('rest_stowed', (0.0, False)), ('rest_engaged', (0.0, True)), ('raised_engaged', (TRAVEL, True))):
        set_pose(parts, lift, eng)
        found = C.coplanar_check(list(lod0.values()) + [bobjs[1]])
        found = [f for f in found if f['a'].startswith('Lift_') or f['b'].startswith('Lift_')]
        zf[pose] = found[:10]
        zf[pose + '_count'] = len(found)
    res['coplanar_same_facing_overlaps'] = zf
    # ---- floating islands (rest pose)
    set_pose(parts, 0.0, False)
    fl = {}
    for n, o in lod0.items():
        if n == 'Lift_Static':
            seeds = lambda lo, hi: lo.z <= 0.0005
        else:
            seeds = None
        if seeds is None:
            # moving parts: seed = the largest island (front plate / boss); also allow touching the static part
            lost, total = islands_floating(o, lambda lo, hi: False)
        else:
            lost, total = islands_floating(o, seeds)
        fl[n] = dict(islands=total, unattached=lost[:6], unattached_count=len(lost))
    res['floating_islands'] = fl
    # base plates resting on the floor: rays from just above the floor under the plate corners
    sup = []
    for sx in (-1, 1):
        for x in (BP[0] + 0.02, BP[1] - 0.02):
            for y in (-BP[2] + 0.02, BP[2] - 0.02):
                p = LC + Vector((sx * x, y, 0.05))
                hit = bvh_b.ray_cast(p, Vector((0, 0, -1)), 0.3)
                sup.append(None if hit[0] is None else round(hit[3] - 0.05, 4))
    res['base_plate_floor_gap'] = sup
    res['lift_min_z_rest'] = round(min(v.z for v in lift_vs([static0])), 4)
    # ---- moving parts never cut the building (rest + raised); lift vs building triangle intersections
    inter = {}
    for pose, (lift, eng) in (('rest_stowed', (0.0, False)), ('rest_engaged', (0.0, True)), ('raised_engaged', (TRAVEL, True))):
        set_pose(parts, lift, eng)
        lvs, lts = world_tri_list(list(lod0.values()))
        bvh_l = BVHTree.FromPolygons(lvs, lts)
        pairs = bvh_l.overlap(bvh_b)
        real = []
        for i, j in pairs:
            tri = [lvs[k] for k in lts[i]]
            if max(p.z for p in tri) <= 0.0006:   # base plate / floor edge contact
                continue
            btri = [bvs[k] for k in bts[j]]
            if all(abs(p.z) < 1e-5 for p in btri) and min(p.z for p in tri) >= -1e-5:
                continue                         # touching the floor plane from above (plate sides, edges)
            real.append([round(c, 3) for c in tri[0]])
        inter[pose] = dict(count=len(real), sample=real[:5])
    res['lift_vs_building_intersections'] = inter
    # ---- raised van envelope: building or lift parts inside it, headroom above it
    set_pose(parts, TRAVEL, True)
    vx, vl, vh, vb = VAN_ENV['half_w'], VAN_ENV['half_l'], VAN_ENV['h'], VAN_ENV['bottom']
    lo = LC + Vector((-vx, -vl, vb + TRAVEL))
    hi = LC + Vector((vx, vl, vh + TRAVEL))
    inside_b = [p for p in building_verts if all(lo[i] < p[i] < hi[i] for i in range(3))]
    inside_l = [p for p in lift_vs(list(lod0.values())) if all(lo[i] < p[i] < hi[i] for i in range(3))]
    lvs, lts = world_tri_list([static0])
    bvh_s = BVHTree.FromPolygons(lvs, lts)
    head_b, head_l = 99.0, 99.0
    nx, ny = 9, 27
    for i in range(nx):
        for j in range(ny):
            p = Vector((lo.x + (hi.x - lo.x) * i / (nx - 1), lo.y + (hi.y - lo.y) * j / (ny - 1), hi.z + 0.001))
            h1 = bvh_b.ray_cast(p, ZV, 5.0)
            h2 = bvh_s.ray_cast(p, ZV, 5.0)
            if h1[0] is not None:
                head_b = min(head_b, h1[3])
            if h2[0] is not None:
                head_l = min(head_l, h2[3])
    # nearest lamp housing to the raised van (horizontal / vertical separation)
    lamp_gap = []
    for x, y in B.LAMPS[:4]:
        lx0, lx1, ly0, ly1, lz0, lz1 = x - 0.08, x + 0.08, y - 0.62, y + 0.62, B.LAMP_Z - 0.075, B.LAMP_Z
        dx = max(lx0 - hi.x, lo.x - lx1, 0.0)
        dy = max(ly0 - hi.y, lo.y - ly1, 0.0)
        dz = max(lz0 - hi.z, lo.z - lz1, 0.0)
        lamp_gap.append(round(math.sqrt(dx * dx + dy * dy + dz * dz), 3))
    ua, ub = U(lo), U(hi)
    res['raised_van'] = dict(envelope_unity_min=[min(ua[i], ub[i]) for i in range(3)], envelope_unity_max=[max(ua[i], ub[i]) for i in range(3)], top_y=round(hi.z, 3),
                             building_verts_inside=len(inside_b), lift_verts_inside=len(inside_l),
                             headroom_to_building_m=round(head_b, 3), headroom_to_lift_shutoff_bar_m=round(head_l, 3),
                             min_distance_to_middle_bay_lamps_m=min(lamp_gap))
    # lamps vs lift (static, and moving parts raised)
    lv = lift_vs(list(lod0.values()))
    dmin = 99.0
    for x, y in B.LAMPS:
        lx0, lx1, ly0, ly1, lz0, lz1 = x - 0.08, x + 0.08, y - 0.62, y + 0.62, B.LAMP_Z - 0.075, B.LAMP_Z
        for p in lv:
            dx = max(lx0 - p.x, p.x - lx1, 0.0)
            dy = max(ly0 - p.y, p.y - ly1, 0.0)
            dz = max(lz0 - p.z, p.z - lz1, 0.0)
            dmin = min(dmin, math.sqrt(dx * dx + dy * dy + dz * dz))
    res['lift_to_lamp_housing_min_m'] = round(dmin, 3)
    # ---- pit: nothing of the lift inside the pit or over its opening below 4 m (all poses)
    pit = B.PIT
    pit_hits = {}
    for pose, (lift, eng) in (('rest_stowed', (0.0, False)), ('rest_engaged', (0.0, True)), ('raised_engaged', (TRAVEL, True))):
        set_pose(parts, lift, eng)
        hits = [p for p in lift_vs(list(lod0.values())) if pit[0] < p.x < pit[1] and pit[2] < p.y < pit[3] and p.z < 4.0]
        pit_hits[pose] = len(hits)
    res['pit_opening_hits_below_4m'] = pit_hits
    # ---- drive-in path with arms stowed: nothing within the van width (+0.1 m) between the door and the pit stairs
    set_pose(parts, 0.0, False)
    lv = lift_vs(list(lod0.values()))
    path = [p for p in lv if abs(p.x) < VAN_ENV['half_w'] + 0.1 and -6.0 < p.y < B.STAIR_Y0 and p.z < 4.0]
    bands = {}
    for name, (za, zb) in (('floor_to_0.31', (0.0, 0.31)), ('0.31_to_4.0', (0.31, 4.0))):
        xs = [abs(p.x) for p in lv if za <= p.z < zb and -5.75 < p.y < 0.3]
        bands[name] = round(2 * min(xs), 3) if xs else None
    res['drive_in'] = dict(lift_verts_in_van_path=len(path), clear_width_by_height=bands,
                           clear_height_under_shutoff_bar=BAR[0], note='arms stowed (FBX rest pose)')
    # ---- props: AABB overlap with lift parts (rest stowed, rest engaged, raised)
    clash = set()
    for pose, (lift, eng) in (('rest_stowed', (0.0, False)), ('rest_engaged', (0.0, True)), ('raised_engaged', (TRAVEL, True))):
        set_pose(parts, lift, eng)
        for n, o in lod0.items():
            vs = world_verts(o)
            a = (Vector([min(p[i] for p in vs) for i in range(3)]), Vector([max(p[i] for p in vs) for i in range(3)]))
            for pr in props:
                bb = C.bbox(pr)
                if bb and C.aabb_overlap(a, bb[0] - Vector((0.02,) * 3), bb[1] + Vector((0.02,) * 3)):
                    clash.add((pose, n, pr.name))
    res['prop_aabb_clashes'] = sorted(['%s: %s ~ %s' % c for c in clash])
    # ---- arm swing sweep vs the tyres of the team van (Astra) and of the render dummy (wheelbase 3.16)
    set_pose(parts, 0.0, False)
    tyres = {}
    for label, (fwd, rear, wx, ww, wr) in (('astra', (ASTRA['axles'][0], ASTRA['axles'][1], ASTRA['wheel_x'], ASTRA['wheel_w'], ASTRA['wheel_r'])),
                                           ('dummy_wb3.16', (1.58, -1.58, 0.89, 0.22, 0.35))):
        worst = 99.0
        for aid in ARMS:
            h, o0, _ = parts['Lift_Arms_' + aid]
            target = arm_engaged_blender_deg(aid)
            for k in range(0, 21):
                h.rotation_euler = (0, 0, math.radians(target * k / 20))
                bpy.context.view_layer.update()
                for p in world_verts(o0):
                    for ay in (fwd, rear):
                        cy, cz = LC.y + ay, wr
                        for sx in (-1, 1):
                            cx = sx * wx
                            if abs(p.x - cx) > ww / 2 + 0.05:
                                continue
                            dr = math.hypot(p.y - cy, p.z - cz) - wr
                            dxo = abs(p.x - cx) - ww / 2
                            d = dr if dxo <= 0 else (math.hypot(max(dr, 0), dxo))
                            worst = min(worst, d)
            h.rotation_euler = (0, 0, 0)
        tyres[label] = round(worst, 3)
    bpy.context.view_layer.update()
    res['arm_swing_min_gap_to_tyres_m'] = tyres
    set_pose(parts, 0.0, False)
    return res


# ============================================================================ main
def guard(path):
    if os.path.exists(path) and not FORCE:
        raise SystemExit('refusing to overwrite existing revision: ' + path)


def main():
    outs = dict(fbx=os.path.join(OUT, 'Workshop_W86_lift_%s.fbx' % REV), json=os.path.join(OUT, 'Workshop_W86_lift_%s.json' % REV),
                blend=os.path.join(OUT, 'Workshop_W86_lift_%s.blend' % REV))
    for p in outs.values():
        guard(p)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    # building + props from the approved workshop (read-only) for the checks
    with bpy.data.libraries.load(SRC_BLEND, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c in ('WS_Building', 'WS_Props')]
    chk = []
    for c in dst.collections:
        sc.collection.children.link(c)
        chk.append(c)
    lib = B.make_materials()   # reuses the appended MAT_WS_* materials (same names)
    coll = bpy.data.collections.new('WS_Lift')
    sc.collection.children.link(coll)
    parts = build_lift(lib, coll)
    bpy.context.view_layer.update()
    bobjs = [bpy.data.objects['WS_Building_Shell_LOD0'], bpy.data.objects['WS_Building_Interior_LOD0']]
    props = [o for o in bpy.data.collections['WS_Props'].objects if o.parent is None]
    checks = run_checks(parts, bobjs, props)
    # ---- remove the workshop again (lift file only)
    for c in chk:
        for o in list(c.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in list(blk):
            if d.users == 0:
                blk.remove(d)
    set_pose(parts, 0.0, False)
    for n, (h, o0, o1) in parts.items():
        if 'rest_loc' in h:
            del h['rest_loc']
    # ---- report numbers
    tris = {n: dict(lod0=tri_count(o0), lod1=tri_count(o1)) for n, (h, o0, o1) in parts.items()}
    lod0_total = sum(v['lod0'] for v in tris.values())
    lod1_total = sum(v['lod1'] for v in tris.values())
    roots = [p[0] for p in parts.values()]
    B.export_fbx(outs['fbx'], roots)
    bpy.ops.wm.save_as_mainfile(filepath=outs['blend'])

    def pad_world(aid, engaged, lift):
        sx, sy, _ = ARMS[aid]
        pin = LC + Vector((sx * PIN_X, sy * PIN_DY, 0))
        ang = math.radians(arm_engaged_blender_deg(aid)) if engaged else 0.0
        d = Vector((0, sy * ARM_L, 0))
        d = Matrix.Rotation(ang, 3, 'Z') @ d
        return pin + d + Vector((0, 0, PAD_TOP + lift))

    arms = {}
    for aid in ARMS:
        sx, sy, _ = ARMS[aid]
        arms['Lift_Arms_' + aid] = dict(
            pivot=U(LC + Vector((sx * PIN_X, sy * PIN_DY, 0))), side='L' if sx < 0 else 'R', end='front' if sy > 0 else 'rear',
            stowed_local_yaw=0.0, engaged_local_yaw=uyaw(arm_engaged_blender_deg(aid)),
            pad_top_stowed_rest=U(pad_world(aid, False, 0.0)), pad_top_engaged_rest=U(pad_world(aid, True, 0.0)),
            pad_top_engaged_raised=U(pad_world(aid, True, TRAVEL)))
    contacts = {}
    for aid in ARMS:
        p = pad_world(aid, True, 0.0)
        sx, sy, _ = ARMS[aid]
        contacts[aid] = dict(building_rest=U(Vector((p.x, p.y, VAN_CONTACT_Y))), building_raised=U(Vector((p.x, p.y, VAN_CONTACT_Y + TRAVEL))),
                             van_local=[round(sx * PAD_X, 3), VAN_CONTACT_Y, round(sy * PAD_DY, 3)])
    ctrl_face = LC + Vector((1.996, 0.0, 1.40))
    ctrl_stand = LC + Vector((2.55, 0.0, 0.0))
    J = dict(
        revision=REV, units='metres', asset='Workshop_W86 vehicle lift (two-post, overhead beam, clear floor)',
        coordinate_system='Unity local space of the building root (same as Workshop_W86_anchors_v01.json): +Y up, +Z = front (door side), '
                          'pivot = floor level at the footprint centre. Converted from Blender (x, y, z) as (-x, z, -y).',
        file='Workshop_W86_lift_v01.fbx',
        placement=dict(fbx_root='Place the imported model at the building root transform (like Workshop_W86_props_v01.fbx). '
                                'Every part is a top-level node at its pivot with identity-transform children *_LOD0, *_LOD1, UCX_*.',
                       lift_centre=U(LC), lift_centre_note='= van_park_point; posts straddle the van at mid wheelbase, the pit stays open between them',
                       yaw=0.0),
        naming='L = Unity +X side (east, van driver left with the nose to the back wall), R = Unity -X side (west, power unit + control box). '
               'Arms: F = front (van nose, back wall, -Z), R = rear (door side, +Z).',
        travel=dict(min=0.0, max=TRAVEL, axis='local +Y translation of every moving part, same value for all six',
                    suggested_duration_s=8.0,
                    note='Moving parts: Lift_Carriage_L/R and Lift_Arms_FL/FR/RL/RR. They are separate top-level nodes (2-level hierarchy rule); '
                         'move them together (or re-parent the arms under their carriage in the prefab).'),
        moving_parts=dict(
            Lift_Carriage_L=dict(pivot=U(LC + Vector((-PXC, 0, 0))), rest_local_y=0.0, raised_local_y=TRAVEL,
                                 pivot_note='post centre on the floor (pivot is below the carriage on purpose: local y = lift height)'),
            Lift_Carriage_R=dict(pivot=U(LC + Vector((PXC, 0, 0))), rest_local_y=0.0, raised_local_y=TRAVEL,
                                 pivot_note='post centre on the floor'),
            **arms),
        arm_swing=dict(axis='local Y rotation about the hinge pin (= the node pivot)', stowed='FBX rest pose: arms parallel to the van, outside the wheel track',
                       engaged_abs_deg=round(ARM_PHI, 2), arm_length_pin_to_pad=round(ARM_L, 3),
                       sequence=['van parked at van_park_point (yaw 180)', 'arms swing from stowed (yaw 0) to engaged_local_yaw (about 1.5 s)',
                                 'carriages + arms translate local y 0 -> 1.6', 'lowering: reverse, then swing the arms back to 0 before the van drives out'],
                       note='The arms must be stowed whenever the van drives in or out: engaged arms lie across the wheel path.'),
        arm_pads=dict(top_y_rest=PAD_TOP, top_y_raised=round(PAD_TOP + TRAVEL, 3), radius=0.062,
                      engaged_centres_rest={k: v['pad_top_engaged_rest'] for k, v in arms.items()}),
        van_contact_points=dict(
            van_contact_y_rest=VAN_CONTACT_Y,
            gap_pad_to_van_at_rest=round(VAN_CONTACT_Y - PAD_TOP, 3),
            points=contacts,
            van_local_note='van_local = (x, y, z) in a van root frame with forward = local +Z and right = local +X (the van parked with yaw 180): '
                           'x = +0.62 right (R arms) / -0.62 left (L arms), y = sill height, z = +0.90 front / -0.90 rear. The points are symmetric.',
            rule='Pads start 0.05 m under the sills. Either start moving the van once the carriages pass 0.05 m (van rises 1.55 m, top at 3.95 m), '
                 'or move it with the carriages from the start (rises 1.6 m, top at 4.0 m). Clearances below are for the second (worst) case.'),
        van=dict(envelope=[VAN_ENV['half_w'] * 2, VAN_ENV['h'], VAN_ENV['half_l'] * 2], wheelbase=3.16, mass_t=2.5, lift_capacity_label_t=4.0,
                 raised_top_y=round(VAN_ENV['h'] + TRAVEL, 3)),
        control_box=dict(post='R (Unity -X)', face_centre=U(ctrl_face), buttons=dict(estop=U(LC + Vector((2.03, 0.0, 1.50))),
                                                                                  up=U(LC + Vector((2.01, -0.05, 1.37))),
                                                                                  down=U(LC + Vector((2.01, 0.05, 1.37)))),
                         interaction_point=U(ctrl_stand), interaction_yaw=uyaw(-90.0),
                         note='Operator (mechanic) stands 0.55 m outside the R post, facing Unity +X toward the box; the van is beyond the post, '
                              'visible past its front (door-side) edge. Box face at 1.2-1.6 m: E-stop on top, up (white) / down (black) below, key switch + pilot lamp at the bottom.'),
        clearances=dict(
            between_posts=round(2 * XI, 3), between_carriages_incl_door_guards=round(2 * (CAR['x0'] - 0.015), 3),
            between_stowed_arm_pads_floor_level=round(2 * (PIN_X - 0.075), 3),
            shutoff_bar_bottom_y=BAR[0], beam_bottom_y=BEAM[0], lift_top_y=round(POST_TOP + 0.085, 3),
            raised_van_top_y=round(VAN_ENV['h'] + TRAVEL, 3),
            raised_van_to_shutoff_bar=round(BAR[0] - (VAN_ENV['h'] + TRAVEL), 3),
            note='Building purlins over the van are at y >= 4.85, rafters/lamps sit at x = +-2.055 (outside the van width).'),
        objects={n: dict(pivot=U(p[0].location), lod0_tris=tris[n]['lod0'], lod1_tris=tris[n]['lod1'],
                         colliders=[c.name for c in p[0].children if c.name.startswith('UCX_')]) for n, p in parts.items()},
        tris=dict(lod0_total=lod0_total, lod1_total=lod1_total, lod0_limit=6000),
        materials=sorted({m.name for p in parts.values() for o in p[1:] for m in o.data.materials}),
        materials_note='All materials are the existing workshop set (Workshop_W86_materials_v01.json); no new textures. '
                       'Hazard-stripe black uses MAT_WS_rubber (#2B2B2E).',
        unity_notes=[
            'Animate: arms localEulerAngles.y 0 -> engaged_local_yaw, then localPosition.y of the six moving nodes 0 -> 1.6 (same value).',
            'Moving UCX colliders (UCX_Lift_Carriage_*, UCX_Lift_Arms_*) must never push or lift the player: put them on a layer that ignores the player '
            'or disable them while the lift moves; the van should be kinematic and follow the carriages.',
            'Lift_Static UCX_01/02 = posts, UCX_03 = power unit + control box block on the R post (part of that post). No colliders on hoses, beam (>= 4.1 m) or the 22 mm base plates.',
            'LODGroup: one group on the model root with all *_LOD0 renderers in LOD0 and all *_LOD1 renderers in LOD1.',
        ],
        clashes_with_workshop=[
            'Base plates (22 mm) stand over the white bay guide lines (Unity x +-1.55..1.65) for 0.6 m at z 2.1..2.7; the lines run under the plates, no coplanar faces (plate bottoms omitted).',
            'The posts lie inside the old van_path_middle_bay check box (x +-1.85): at the lift the drive-in width is 2.69 m between the carriages (door guards) '
            'and 2.41 m at floor level between the stowed arm pads; van width 2.0 m. Door and pit clear zones untouched.',
            'middle_bay_repair_zone (x +-1.6) overlaps the inner 0.07 m of both posts.',
            'Post tops stand 0.22 m from the housings of Light_Strip_01 (L) and Light_Strip_02 (R) at y 3.83-3.90; no contact, lamps keep lighting the van sides.',
            'Raised van (top 4.0) clears the building by 0.85 m (purlins) and the lift shut-off bar by 0.10 m; no travel reduction needed.',
        ],
        checks=checks,
    )
    with open(outs['json'], 'w', encoding='utf-8') as f:
        json.dump(J, f, indent=1)
    print('LIFT_REPORT', json.dumps(dict(tris=tris, lod0_total=lod0_total, lod1_total=lod1_total), indent=1))
    print('LIFT_CHECKS', json.dumps(checks, indent=1))
    return outs


if __name__ == '__main__':
    main()
