"""District pool 'Переход' (TASK-000270): the fat bearded kiosk seller and the funny taxi driver.
Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS. No bpy calls at import time.
TASK-000276: the car flipper, the garage drunk and the long-haul trucker (made for the hamlet in TASK-000272) live here now."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T
from buddy_geo import smoothstep

P = 'mixamorig:'
GOLD = ((214, 174, 76), 0.28, 'metal')

TYPES = {
    'TRANSIT_SELLER': dict(
        label='Толстый продавец с бородой', group='Переход', body=dict(belly=1.0), arm_down=66.0,
        look=dict(skin=(238, 156, 112), nose=(226, 112, 92), brow=(46, 34, 28)),
        face=dict(Happy=0.35),
        slots={'Tee': ((132, 168, 206), 0.85), 'Apron': ((236, 230, 214), 0.9), 'Apron_Pocket': ((214, 206, 186), 0.9),
               'Apron_Strap': ((206, 196, 172), 0.9), 'Stains': ((176, 136, 92), 1.0), 'Trousers': ((96, 94, 90), 0.9),
               'Socks': ((232, 230, 222), 0.9), 'Sandals': ((112, 70, 42), 0.6), 'Sandal_Strap': ((88, 54, 32), 0.6),
               'Beard': ((48, 36, 30), 0.95), 'Hair': ((48, 36, 30), 0.9), 'Pencil': ((236, 188, 52), 0.6),
               'Pencil_Tip': ((222, 190, 140), 0.8)},
        colourways=[{'Tee': (204, 74, 66), 'Apron': (62, 92, 152), 'Apron_Pocket': (52, 78, 132), 'Apron_Strap': (46, 70, 120),
                     'Trousers': (52, 54, 62), 'Socks': (120, 120, 124), 'Beard': (118, 64, 38), 'Hair': (118, 64, 38)},
                    {'Tee': (236, 234, 226), 'Apron': (150, 40, 52), 'Apron_Pocket': (128, 34, 44), 'Apron_Strap': (118, 30, 40),
                     'Trousers': (118, 102, 78), 'Sandals': (40, 40, 44), 'Sandal_Strap': (30, 30, 34), 'Beard': (150, 148, 144),
                     'Hair': (150, 148, 144)}]),
    'TRANSIT_TAXI': dict(
        label='Смешной таксист', group='Переход', body=dict(belly=1.0), arm_down=66.0,
        look=dict(skin=(240, 186, 160), nose=(232, 160, 136), brow=(96, 56, 30)),
        face=dict(Happy=0.5),
        slots={'Shirt': ((246, 246, 242), 0.8), 'Shirt_Roll': ((232, 232, 228), 0.8), 'Buttons': ((214, 214, 210), 0.5),
               'ChestHair': ((60, 40, 30), 0.95), 'Gold': GOLD, 'Pants': ((52, 92, 56), 0.85), 'Belt': ((24, 24, 26), 0.45),
               'Buckle': ((236, 168, 60), 0.25, 'metal'), 'Socks': ((248, 248, 244), 0.9), 'Loafers': ((96, 56, 34), 0.35),
               'Loafer_Sole': ((44, 30, 24), 0.6), 'Hair': ((122, 72, 40), 0.75), 'Glasses_Frame': ((24, 24, 26), 0.3),
               'Earpiece': ((22, 22, 26), 0.35), 'Earpiece_Light': ((40, 120, 255), 0.2),
               'Keys': ((196, 198, 204), 0.3, 'metal'), 'Key_Fob': ((26, 26, 28), 0.45), 'Keychain': ((206, 40, 46), 0.9)},
        colourways=[{'Shirt': (236, 222, 196), 'Shirt_Roll': (222, 208, 182), 'Pants': (40, 42, 50), 'Hair': (40, 34, 30)},
                    {'Shirt': (170, 206, 236), 'Shirt_Roll': (152, 190, 222), 'Pants': (110, 96, 72), 'Loafers': (24, 22, 22),
                     'Keychain': (62, 142, 210)}]),
    'TRANSIT_FLIPPER': dict(
        label='Перекуп', group='Переход', hand_props=True, body=dict(belly=0.4), face=dict(Blink=0.25, Happy=0.35),
        look=dict(brow=(46, 38, 32)),
        slots={'Puffer': ((30, 32, 38), 0.45), 'Stitch': ((20, 22, 26), 0.6), 'Collar': ((24, 26, 30), 0.5),
               'Pants': ((40, 42, 50), 0.85), 'Stripes': ((236, 236, 232), 0.85), 'Socks': ((240, 240, 236), 0.9),
               'Shoe_Upper': ((30, 30, 34), 0.6), 'Shoe_Sole': ((240, 240, 236), 0.6), 'Shoe_Lace': ((240, 240, 236), 0.7),
               'Cap': ((24, 24, 28), 0.8), 'Cap_Peak': ((24, 24, 28), 0.8), 'Hair': ((40, 34, 30), 0.9),
               'Stubble': ((60, 48, 40), 0.95), 'Bag': ((34, 26, 22), 0.4), 'Bag_Strap': ((24, 18, 16), 0.5),
               'Gauge': ((250, 200, 40), 0.4), 'Gauge_Screen': ((40, 64, 54), 0.2), 'Gauge_Probe': ((30, 30, 34), 0.4),
               'Cable': ((20, 20, 22), 0.5)},
        colourways=[{'Puffer': (62, 74, 60), 'Stitch': (46, 56, 44), 'Collar': (50, 60, 48), 'Cap': (62, 74, 60), 'Cap_Peak': (40, 46, 38)},
                    {'Puffer': (40, 52, 96), 'Stitch': (28, 38, 72), 'Collar': (32, 42, 80), 'Pants': (24, 24, 28),
                     'Cap': (236, 236, 232), 'Cap_Peak': (40, 52, 96)}]),
    'TRANSIT_GARAGE_DRUNK': dict(
        label='Гаражный алкаш', group='Переход', hand_props=True, body=dict(belly=0.7), arm_down=70.0, no_ears=True,
        face=dict(Blink=0.45, Happy=0.3),
        look=dict(skin=(232, 150, 120), nose=(222, 60, 60), brow=(92, 80, 70)),
        slots={'Jacket': ((54, 62, 72), 0.95), 'Stitch': ((38, 44, 52), 0.95), 'Collar': ((44, 50, 58), 0.95),
               'Buttons': ((20, 20, 20), 0.5), 'Oil': ((26, 24, 22), 0.35), 'Trousers': ((40, 46, 64), 0.9),
               'Boots': ((40, 44, 40), 0.4), 'Boots_Sole': ((24, 24, 24), 0.6), 'Hat': ((64, 58, 52), 0.95),
               'Fur': ((112, 94, 72), 1.0), 'Stubble': ((90, 80, 74), 0.95), 'EyeBags': ((156, 112, 134), 0.8),
               'Bottle': ((226, 236, 240), 0.05), 'Bottle_Cap': ((200, 40, 40), 0.35), 'Label': ((196, 210, 230), 0.6)},
        colourways=[{'Jacket': (36, 40, 46), 'Stitch': (24, 28, 32), 'Collar': (30, 34, 40), 'Hat': (40, 40, 44), 'Fur': (70, 62, 54)},
                    {'Jacket': (82, 72, 56), 'Stitch': (60, 52, 40), 'Collar': (70, 60, 46), 'Trousers': (52, 52, 56),
                     'Hat': (92, 70, 50), 'Fur': (150, 130, 104)}]),
    'TRANSIT_TRUCKER': dict(
        label='Дальнобой', group='Переход', body=dict(belly=1.0), arm_down=66.0, face=dict(Happy=0.25, Blink=0.3),
        look=dict(skin=(226, 150, 108), nose=(214, 126, 92), brow=(60, 50, 42)),
        slots={'Shirt': ((178, 40, 44), 0.9), 'Check': ((40, 30, 30), 0.9), 'Shirt_Roll': ((160, 36, 40), 0.9),
               'Tank': ((238, 236, 228), 0.85), 'Jeans': ((62, 84, 130), 0.9), 'Belt': ((40, 30, 24), 0.5),
               'Buckle': ((196, 196, 202), 0.3, 'metal'), 'Socks': ((240, 240, 236), 0.9), 'Slides': ((40, 42, 46), 0.55),
               'Cap': ((240, 240, 236), 0.8), 'Cap_Peak': ((40, 60, 120), 0.6), 'Hair': ((60, 50, 42), 0.9),
               'Mustache': ((60, 50, 42), 0.9), 'Stubble': ((80, 70, 64), 0.95), 'Thermos': ((60, 120, 80), 0.4),
               'Thermos_Cap': ((40, 40, 44), 0.4), 'Thermos_Steel': ((200, 202, 206), 0.25, 'metal')},
        colourways=[{'Shirt': (40, 90, 150), 'Shirt_Roll': (34, 78, 132), 'Cap_Peak': (178, 40, 44), 'Thermos': (200, 60, 50)},
                    {'Shirt': (60, 110, 60), 'Shirt_Roll': (52, 96, 52), 'Jeans': (40, 42, 50), 'Cap': (250, 200, 40),
                     'Cap_Peak': (40, 42, 50)}]),
}


def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _decal_t(pieces, garment):
    src = C.weight_source([garment])
    return [C.transfer(o, src) for o in pieces]


def _delete_faces(ob, pred):
    """Delete the faces whose centre satisfies pred(centre) (open jacket front)."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    kill = [f for f in bm.faces if pred(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data); bm.free()
    ob.data.update()
    return ob


def _interp(table, x):
    """Piecewise-linear lookup in [(x, value)] (sorted)."""
    if x <= table[0][0]:
        return table[0][1]
    for (x0, v0), (x1, v1) in zip(table, table[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return table[-1][1]


# ------------------------------------------------------------------ beard (TRANSIT_SELLER)
def beard(prefix, material, cols=40, rows=9):
    """Big bushy cartoon beard: a thick shell round the jaw from ear to ear that hangs over the chest at the front,
    with tufted lower edge; the upper edge runs under the mouth so the mouth stays readable."""
    arc = math.radians(80)
    top = [(0, 1.383), (12, 1.388), (20, 1.405), (28, 1.432), (38, 1.458), (52, 1.484), (66, 1.515), (80, 1.548)]
    bot = [(0, 1.196), (14, 1.204), (26, 1.226), (38, 1.262), (52, 1.302), (66, 1.338), (80, 1.372)]
    vs, fs, grid = [], [], []

    def z_bot(d):
        lobe = abs(math.sin(math.pi * (d + 80.0) / 17.0)) ** 0.7     # rounded tufts hanging down
        return _interp(bot, abs(d)) - 0.016 * lobe

    def surf(phi, z, off):
        s, c = math.sin(phi), math.cos(phi)
        n = Vector((s / B.HEAD_R, -c / B.HEAD_RY, 0.0)).normalized()
        return Vector((B.HEAD_R * s, -B.HEAD_RY * c, z)) + n * off

    for j in range(cols + 1):
        phi = -arc + 2 * arc * j / cols
        d = math.degrees(phi)
        f = max(0.0, math.cos(phi)) ** 1.6
        zb, zt = z_bot(d), _interp(top, abs(d))
        col = []
        # curled underside (tucks back toward the neck / chest) then the outer face up to the edge under the mouth
        bulge = 0.016 + 0.046 * f
        col.append((zb + 0.020, 0.010 + 0.016 * f))
        for i in range(rows + 1):
            u = i / rows
            g = math.sin(math.pi / 2 * min(1.0, (u + 0.18) / 0.40)) * (1 - smoothstep(0.35, 1.0, u) * 0.92)
            col.append((zb + (zt - zb) * u, 0.005 + bulge * g))
        ids = []
        for z, off in col:
            ids.append(len(vs)); vs.append(surf(phi, z, off))
        grid.append(ids)
    for a, b in zip(grid, grid[1:]):
        for i in range(len(a) - 1):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    ob = G.from_data(prefix, vs, fs, material, True)
    G.solidify(ob, 0.010, offset=0.0)
    C.set_weights(ob, [{P + 'Head': smoothstep(1.22, 1.34, p.z), P + 'Neck': 1 - smoothstep(1.22, 1.34, p.z)}
                       for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
    return ob


# ------------------------------------------------------------------ apron (TRANSIT_SELLER)
def _apron_angle(z):
    """Half-width of the apron (parametric angle, degrees): narrow bib on the chest, wide skirt below the belly."""
    return _interp([(0.97, 66.0), (1.00, 60.0), (1.04, 44.0), (1.08, 32.0), (1.12, 27.0), (1.17, 26.0)], z)


def apron(prefix, M, off=0.011, cols=16):
    zs = [1.170, 1.150, 1.120, 1.090, 1.060, 1.030, 1.000, 0.970, 0.940, 0.910, 0.880, 0.850, 0.820, 0.790, 0.760, 0.730,
          0.700, 0.670, 0.640, 0.610, 0.585]
    vs, fs, grid = [], [], []
    for z in zs:
        zz = max(z, 0.860)
        _, rx, ry, dy = W.lerp_row(W.TEE, zz)
        A = math.radians(_apron_angle(z))
        row = []
        for j in range(cols + 1):
            u = -1 + 2 * j / cols
            a = A * u
            zc = z - (0.012 * u * u if z < 0.6 else 0.0)        # hem curves up a little at the sides
            row.append(len(vs)); vs.append(Vector(((rx + off) * math.sin(a), dy - (ry + off) * math.cos(a), zc)))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(cols):
            fs.append((a[j], a[j + 1], b[j + 1], b[j]))
    ob = G.from_data(prefix + '_Apron', vs, fs, M['Apron'], True)
    G.solidify(ob, 0.005, offset=0.0)

    def w(p):
        t = 0.55 * smoothstep(0.80, 0.58, p.z)
        k = smoothstep(-0.07, 0.07, p.x)
        sp = G.chain(p.z, [(0.84, 'Hips'), (0.93, 'Spine'), (1.02, 'Spine1'), (1.11, 'Spine2')])
        out = {P + b: x * (1 - t) for b, x in sp.items()}
        out[P + 'LeftUpLeg'] = out.get(P + 'LeftUpLeg', 0.0) + t * k
        out[P + 'RightUpLeg'] = out.get(P + 'RightUpLeg', 0.0) + t * (1 - k)
        return out
    C.set_weights(ob, [w(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return ob


def apron_straps(prefix, M, tee, apron_ob):
    """Neck loop from the bib corners round the back of the neck, waist ties round the back with a bow."""
    bvh = G.bvh_of([tee])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.5))) >= 0 else -nrm
        return loc + nrm * off, nrm
    out = []
    raw = [(0.082, -0.150, 1.165), (0.100, -0.128, 1.212), (0.116, -0.080, 1.242), (0.124, -0.010, 1.252),
           (0.110, 0.060, 1.250), (0.070, 0.118, 1.240), (0.0, 0.142, 1.236)]
    for s in (1, -1):
        pts = [on(Vector((s * x, y, z)), 0.006)[0] for x, y, z in raw]
        out.append(C.strap(f'{prefix}_NeckStrap_{s}', pts, M['Apron_Strap'], width=0.022, thick=0.004,
                           normal_fn=lambda q: on(q, 0.0)[1]))
    # waist ties: round the back at the belt line
    z = 0.905
    _, rx, ry, dy = W.lerp_row(W.TEE, z)
    rx, ry = rx + 0.010, ry + 0.010
    pts = [Vector((rx * math.sin(a), dy - ry * math.cos(a), z)) for a in [math.radians(d) for d in range(62, 299, 8)]]
    out.append(C.strap(prefix + '_Ties', pts, M['Apron_Strap'], width=0.022, thick=0.004,
                       normal_fn=lambda p: Vector((p.x / rx, (p.y - dy) / ry, 0)).normalized()))
    by = dy + ry + 0.012
    out.append(G.ellipsoid(prefix + '_BowKnot', (0, by, z), (0.016, 0.010, 0.014), M['Apron_Strap'], seg=10, rings=6))
    for s in (1, -1):
        out.append(G.ellipsoid(f'{prefix}_BowLoop_{s}', (s * 0.034, by - 0.002, z + 0.004), (0.026, 0.008, 0.016), M['Apron_Strap'],
                               rot=Matrix.Rotation(math.radians(-s * 12), 3, 'Y'), seg=10, rings=6))
        out.append(G.tube(f'{prefix}_BowTail_{s}', [(s * 0.008, by, z - 0.006), (s * 0.020, by + 0.004, z - 0.050),
                                                     (s * 0.028, by + 0.002, z - 0.090)], 0.007, M['Apron_Strap'], seg=6))
    return out


def sandals(prefix, sock_m, sole_m, strap_m):
    """Socks in sandals: the shoe-shaped foot in the sock colour on a sandal sole, toe / instep / heel straps."""
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Foot_{s}', s, sock_m, sole_m)
        cx = s * B.LEG_X
        parts = [up, so]
        parts.append(W.wrap_band(f'{prefix}_ToeStrap_{s}', up, cx - s * 0.008, [-0.140, -0.156, -0.172], strap_m, zc=0.042, n=11))
        parts.append(W.wrap_band(f'{prefix}_InstepStrap_{s}', up, cx - s * 0.004, [-0.040, -0.058, -0.076], strap_m, zc=0.050, n=11))
        parts.append(W.wrap_band(f'{prefix}_HeelStrap_{s}', up, cx, [0.040, 0.056], strap_m, zc=0.060, n=11))
        wf = C.shoe_weights(s)
        for o in parts:
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += parts
    return out


def pencil_behind_ear(prefix, body_m, tip_m):
    a = Vector((-0.158, 0.082, 1.528))
    b = Vector((-0.160, -0.022, 1.508))
    d = (b - a).normalized()
    body = G.tube(prefix + '_Body', [a, b], 0.0058, body_m, seg=6)
    tip = G.tube(prefix + '_Tip', [b, b + d * 0.020], lambda i, n: (0.0058, 0.0012)[i], tip_m, seg=6)
    return [C.rigid(o, 'Head') for o in (body, tip)]


def transit_seller(body, face, M, skin):
    src = C.weight_source([body])
    tee = _t(W.top('TSELL_Tee', W.TEE, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Tee']]), src, C.no_head)
    out = [tee]
    ap = apron('TSELL', M)
    asrc = C.weight_source([ap])
    deco = [W.front_decal('TSELL_Pocket', [(-0.112, 0.800), (0.112, 0.800), (0.118, 0.905), (-0.118, 0.905)], ap, M['Apron_Pocket'],
                          0.004, thickness=0.004, step=0.016),
            W.front_decal('TSELL_PocketSeam', [(-0.003, 0.806), (0.003, 0.806), (0.003, 0.902), (-0.003, 0.902)], ap, M['Apron_Strap'],
                          0.0085, step=0.010),
            W.front_decal('TSELL_Stain_0', W.blob(-0.060, 1.045, 0.024, seed=11), ap, M['Stains'], 0.0035),
            W.front_decal('TSELL_Stain_1', W.blob(0.085, 0.700, 0.019, seed=12), ap, M['Stains'], 0.0035),
            W.front_decal('TSELL_Stain_2', W.blob(-0.120, 0.650, 0.012, seed=13), ap, M['Stains'], 0.0035)]
    out += [ap] + [_t(o, asrc) for o in deco]
    tsrc = C.weight_source([tee])
    out += [_t(o, tsrc, C.no_head) for o in apron_straps('TSELL_Apron', M, tee, ap)]
    out.append(_t(W.bottoms('TSELL_Trousers', W.LEGS_ANKLE, [M['Trousers'], M['Trousers']], cuff=W.ANKLE_CUFF), src))
    out.append(_t(W.plain_socks('TSELL_Socks', M['Socks'], top=0.260), src))
    out += sandals('TSELL_Sandal', M['Socks'], M['Sandals'], M['Sandal_Strap'])
    out.append(W.hair_ring('TSELL_Hair', M['Hair']))
    out.append(beard('TSELL_Beard', M['Beard']))
    out += W.mustache('TSELL_Mustache', M['Beard'], droop=0.010, size=1.45)
    out += pencil_behind_ear('TSELL_Pencil', M['Pencil'], M['Pencil_Tip'])
    return out


# ------------------------------------------------------------------ taxi driver
TAXI_LEGS = [(.70, .094), (.60, .092), (.50, .088), (.43, .085), (.34, .080), (.27, .075), (.235, .070)]
TAXI_CUFF = [(.222, .060), (.208, .056), (.206, .051)]


def key_bunch(prefix, M):
    """Car keys dangling from the right fist (T-pose world coords: the hand points along -X)."""
    ring_c = Vector((-0.806, -0.050, 1.150))
    parts = []
    ring = [ring_c + Vector((0.017 * math.cos(a), 0.017 * math.sin(a), 0)) for a in [2 * math.pi * k / 12 for k in range(13)]]
    parts.append(G.tube(prefix + '_Ring', ring, 0.0022, M['Keys'], seg=5, caps=False))
    hang = ring_c + Vector((-0.016, 0, 0))
    # car-key fob, two flat keys fanned out, a fluffy pompom
    parts.append(G.ellipsoid(prefix + '_Fob', hang + Vector((-0.034, 0.006, 0)), (0.026, 0.017, 0.009), M['Key_Fob'], seg=12, rings=6))
    parts.append(W.box(prefix + '_FobBlade', hang + Vector((-0.074, 0.006, 0)), (0.018, 0.005, 0.002), M['Keys']))
    for k, ang in enumerate((-28, 22)):
        r = Matrix.Rotation(math.radians(ang), 3, 'Z')
        parts.append(W.box(f'{prefix}_Key_{k}', hang + r @ Vector((-0.026, 0, 0.003 * (k * 2 - 1))), (0.026, 0.007, 0.0018), M['Keys'], rot=r))
        parts.append(G.ellipsoid(f'{prefix}_KeyHead_{k}', hang + r @ Vector((-0.004, 0, 0.003 * (k * 2 - 1))), (0.010, 0.010, 0.003), M['Keys'],
                                 seg=10, rings=4))
    parts.append(G.ellipsoid(prefix + '_Pompom', hang + Vector((-0.030, -0.034, 0)), (0.016, 0.016, 0.016), M['Keychain'], seg=10, rings=6))
    parts.append(G.tube(prefix + '_PomCord', [hang, hang + Vector((-0.016, -0.024, 0))], 0.0018, M['Keychain'], seg=4))
    return [W.prop(o, 'RightHand') for o in parts]


# ------------------------------------------------------------------ open shirt + chest hair (TASK-000272, taxi v02 / trucker)
OPEN_SLEEVE = [(.212, .074), (.25, .069), (.30, .064), (.36, .060), (.42, .057), (.455, .056), (.462, .062), (.480, .064),
               (.496, .062), (.500, .052)]                  # rolled up above the elbow (the shepherd's sleeve)


def v_gap(z, z0=0.955, z1=1.255, top=0.112):
    """Half width of the open front of the shirt at height z: closed below z0, widening to `top` at the collar."""
    t = max(0.0, min(1.0, (z - z0) / (z1 - z0)))
    return top * t ** 0.85


def open_shirt(prefix, M, src, rows=None, arm_row=6, hem=(.844, .166, .110, -.006), mats=None, row_mat=None, sleeve_mat=None,
               gap=v_gap, edge_slot='Shirt'):
    """Shirt unbuttoned down to the belly: the V is cut out of the front, piped edges, a wide-open fold-down collar."""
    rows = rows or W.TUCKED
    mats = mats or [M['Shirt'], M['Shirt_Roll']]
    sleeve_mat = sleeve_mat or [0] * 5 + [1] * 5
    cut = lambda c: c.y < 0 and abs(c.x) < gap(c.z)
    shirt = W.top(prefix + '_Shirt', rows, arm_row, OPEN_SLEEVE, hem, mats, row_mat=row_mat, sleeve_mat=sleeve_mat, cut=cut)
    _t(shirt, src, C.no_head)
    edges = []
    zs = [z for z in (0.95, 0.99, 1.03, 1.07, 1.11, 1.15, 1.19, 1.22, 1.245) if rows[0][0] <= z <= rows[-1][0]]
    for s in (1, -1):
        pts = []
        for z in zs:
            r = W.lerp_row(rows, z)
            x = gap(z) + 0.002
            a = math.asin(max(-1.0, min(1.0, x / r[1])))
            pts.append(Vector((s * x, r[3] - r[2] * math.cos(a) - 0.003, z)))
        edges.append(G.tube(f'{prefix}_ShirtEdge_{s}', pts, 0.0045, M[edge_slot], seg=6))
    ssrc = C.weight_source([shirt])
    collar = W.collar(prefix + '_Collar', M[edge_slot], open_deg=62, tip=0.044, thick=0.005)
    return shirt, [shirt, _t(collar, ssrc, C.no_head)] + [_t(o, ssrc) for o in edges]


def chest_hair(prefix, material, body, gap=v_gap, n=64, seed=5):
    """Curly chest hair in the open V: little crescent curls projected on the chest skin."""
    import random
    rnd = random.Random(seed)
    out = []
    k = 0
    while len(out) < n and k < n * 20:
        k += 1
        z = rnd.uniform(0.975, 1.235)
        w = gap(z) - 0.010
        if w < 0.008:
            continue
        x = rnd.uniform(-w, w)
        a0 = rnd.uniform(0, 2 * math.pi)
        ro, ri = rnd.uniform(0.0055, 0.0075), 0.0030
        arc = [a0 + math.radians(270) * j / 9 for j in range(10)]
        pts = [(x + ro * math.cos(a), z + ro * math.sin(a)) for a in arc] + [(x + ri * math.cos(a), z + ri * math.sin(a)) for a in reversed(arc)]
        out.append(W.front_decal(f'{prefix}_{len(out)}', pts, body, material, 0.0016, step=0.006))
    return out


def bt_earpiece(prefix, M):
    """Bluetooth headset on the right ear: an elongated bud pointing at the mouth, a hook over the ear, a blue light."""
    d = Vector((0.0, -1.0, -0.55)).normalized()
    u = Vector((1.0, 0.0, 0.0))
    v = d.cross(u).normalized()
    rot = Matrix((u, v, d)).transposed()
    c = Vector((-0.188, -0.020, 1.460))
    out = [G.ellipsoid(prefix + '_Body', c, (0.012, 0.013, 0.036), M['Earpiece'], rot=rot, seg=14, rings=8),
           G.ellipsoid(prefix + '_Light', c + Vector((-0.012, 0.010, 0.010)), (0.003, 0.007, 0.007), M['Earpiece_Light'], seg=10, rings=6),
           G.tube(prefix + '_Hook', [Vector((-0.182, 0.004, 1.486)), Vector((-0.178, 0.014, 1.522)), Vector((-0.160, 0.030, 1.528)),
                                     Vector((-0.150, 0.040, 1.500))], 0.0035, M['Earpiece'], seg=6)]
    return [C.rigid(o, 'Head') for o in out]


def transit_taxi(body, face, M, skin):
    """v02 (TASK-000272): the reference picture's look - open white shirt over a hairy chest, a thick gold chain, a
    Bluetooth earpiece, combed brown hair with a quiff, round glasses, black belt with a gold buckle, green trousers;
    still the taxi driver's car keys in the fist."""
    src = C.weight_source([body])
    shirt, out = open_shirt('TTAXI', M, src)
    bsrc = C.weight_source([body])
    out += [_t(o, bsrc) for o in chest_hair('TTAXI_Hair', M['ChestHair'], body)]
    out += [_t(o, bsrc, C.no_head) for o in W.gold_chain('TTAXI_Chain', M['Gold'], [body, shirt])]
    ssrc = C.weight_source([shirt])
    out += [_t(o, ssrc) for o in W.buttons('TTAXI_Btn', shirt, M['Buttons'], [(0.0, z) for z in (0.925, 0.880)], r=0.0085)]
    pants = _t(W.bottoms('TTAXI_Pants', TAXI_LEGS, [M['Pants'], M['Pants']], cuff=TAXI_CUFF), src)
    out.append(pants)
    belt = W.belt('TTAXI', M['Belt'], M['Buckle'])
    bpy.data.objects.remove(belt.pop())
    belt.append(G.ellipsoid('TTAXI_Buckle', (0.0, -0.002 - 0.130 - 0.010, 0.872), (0.036, 0.008, 0.023), M['Buckle'], seg=16, rings=8))
    out += [_t(o, src) for o in belt]
    out.append(_t(W.plain_socks('TTAXI_Socks', M['Socks'], top=0.255), src))
    shoes = W.shoes('TTAXI_Loafer', M['Loafers'], M['Loafer_Sole'])
    out += shoes
    for o in shoes:
        if o.name.endswith('_Upper'):
            s = -1 if '_Shoe_-1' in o.name else 1
            cx = s * B.LEG_X
            st = G.decal(f'TTAXI_Penny_{s}', [(cx - 0.070, 0.040), (cx + 0.070, 0.040), (cx + 0.070, 0.058), (cx - 0.070, 0.058)],
                         W.TOP(0.6), [o], 0.003, M['Loafer_Sole'], step=0.010, thickness=0.004)
            C.set_weights(st, [C.shoe_weights(s)(st.matrix_world @ v.co) for v in st.data.vertices])
            out.append(st)
    out.append(W.hair('TTAXI_HairTop', M['Hair'], 'slick'))
    out.append(C.rigid(G.ellipsoid('TTAXI_Quiff', (0.022, -0.072, 1.736), (0.092, 0.056, 0.034), M['Hair'], seg=16, rings=8), 'Head'))
    out += W.glasses('TTAXI_Glasses', M['Glasses_Frame'], rx=0.052, rz=0.052, round_k=1.0)
    out += bt_earpiece('TTAXI_Earpiece', M)
    out += key_bunch('TTAXI_Keys', M)
    return out

# ------------------------------------------------------------------ car flipper, garage drunk, trucker (TASK-000272, moved here in TASK-000276)
def thickness_gauge(prefix, M):
    """Paint-thickness gauge (the car flipper's badge) in the right fist, probe dangling on its cable (T-pose coords:
    the right hand points along -X)."""
    import buddy_pool_bad as BD
    c = Vector((-0.742, -0.026, 1.106))
    rot = Matrix(((0, -1, 0), (1, 0, 0), (0, 0, 1)))
    out = [BD.rbox(prefix + '_Gauge', c, (0.030, 0.062, 0.017), M['Gauge'], bevel=0.010, rot=rot),
           BD.rbox(prefix + '_GaugeScreen', c + Vector((-0.020, 0.0, -0.0165)), (0.022, 0.018, 0.002), M['Gauge_Screen'], bevel=0.002, rot=rot)]
    a = c + Vector((-0.060, 0.0, 0.0))
    probe = Vector((-0.900, -0.040, 1.070))
    out.append(G.tube(prefix + '_Cable', [a, a + Vector((-0.040, -0.010, -0.025)), probe + Vector((0.030, 0.0, 0.010)), probe],
                      0.0035, M['Cable'], seg=6))
    out.append(G.ellipsoid(prefix + '_Probe', probe + Vector((-0.012, 0, 0)), (0.016, 0.016, 0.016), M['Gauge_Probe'], seg=12, rings=6))
    return [W.prop(o, 'RightHand') for o in out]


def transit_flipper(body, face, M, skin):
    import buddy_pool_oldtown2 as O2
    import buddy_pool_bad as BD
    pre = 'TRANSIT_FLIPPER'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Puffer', src, quilted=True)
    jsrc = C.weight_source([jacket])
    out = [jacket, _t(O2._stand_collar(pre + '_Collar', M['Collar'], open_deg=10.0), jsrc, C.no_head)]
    out.append(_t(W.front_decal(pre + '_Zip', [(-0.004, 0.705), (0.004, 0.705), (0.004, 1.262), (-0.004, 1.262)], jacket, M['Stitch'],
                                0.005), jsrc))
    pants = T._trousers(pre, M, 'Pants', src, legs=W.LEGS_SWEAT, cuff=W.SWEAT_CUFF, cuff_slot='Pants')
    out += [pants] + T._decal_t(W.leg_stripes(pre + '_Stripe', pants, M['Stripes'], z0=0.20, z1=0.86), pants)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.shoes(pre, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    cap, base = O2.baseball_cap(pre + '_Cap', M['Cap'], M['Cap_Peak'])
    out += cap
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=base))
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head))
    out += BD.man_bag(pre + '_ManBag', M)
    out += thickness_gauge(pre, M)
    return out


def ushanka(prefix, M):
    """Fur hat with the ear flaps tied up on top: knitted crown, a fur band round the forehead, two flaps folded up."""
    crown = W.beanie(prefix + '_Crown', M['Hat'])
    band = []
    h = W.h_of(1.668)
    for k in range(33):
        phi = 2 * math.pi * k / 32
        band.append(W.head_at(phi, h, 0.026)[0])
    out = crown + [C.rigid(G.tube(prefix + '_Band', band, 0.026, M['Fur'], seg=10, caps=False), 'Head')]
    for s in (1, -1):              # ear flaps folded up flat against the crown sides
        rot = Matrix.Rotation(math.radians(s * 22), 3, 'Y')
        out.append(C.rigid(G.ellipsoid(f'{prefix}_Flap_{s}', (s * 0.122, 0.012, 1.738), (0.020, 0.074, 0.060), M['Fur'], rot=rot,
                                       seg=14, rings=8), 'Head'))
    out.append(C.rigid(G.ellipsoid(prefix + '_FrontFlap', (0.0, -0.152, 1.708), (0.118, 0.020, 0.050), M['Fur'], seg=16, rings=8), 'Head'))
    return out


def vodka_bottle(prefix, M):
    """Vodka bottle held by the neck in the left fist (T-pose: the left hand points along +X): clear glass, a red cap
    poking out above the fist, a plain label band (no text). Dropped at the slightest danger (NpcHeldProps)."""
    import buddy_pool_bad as BD
    a, b = Vector((0.640, -0.014, 1.142)), Vector((1.000, -0.014, 1.142))
    d, L = (b - a).normalized(), (b - a).length
    prof = [(0.0, 0.0150), (0.06, 0.0150), (0.30, 0.0155), (0.40, 0.026), (0.47, 0.034), (0.97, 0.034), (1.0, 0.030)]
    glass = BD.axis_loft(prefix + '_Vodka', a, b, prof, M['Bottle'], seg=16)
    cap = BD.axis_loft(prefix + '_VodkaCap', a - d * 0.022, a + d * 0.010, [(0.0, 0.0168), (1.0, 0.0168)], M['Bottle_Cap'], seg=14)
    label = BD.axis_loft(prefix + '_VodkaLabel', a + d * (0.60 * L), a + d * (0.82 * L), [(0.0, 0.0353), (1.0, 0.0353)], M['Label'],
                         seg=16, cap_start=False, cap_end=False)
    return [W.prop(o, 'LeftHand') for o in (glass, cap, label)]


def transit_garage_drunk(body, face, M, skin):
    pre = 'TRANSIT_GDRUNK'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Jacket', src, quilted=True)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Collar'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=30, tip=0.030, thick=0.007)
    deco = [W.front_decal(pre + '_Placket', [(-0.004, 0.705), (0.004, 0.705), (0.004, 1.252), (-0.004, 1.252)], jacket, M['Stitch'], 0.004)]
    deco += W.buttons(pre + '_Btn', jacket, M['Buttons'], [(0.0, z) for z in (1.175, 1.075, 0.975)], r=0.011, offset=0.006)
    for k, (x, z, r) in enumerate(((-0.090, 0.920, 0.040), (0.110, 1.060, 0.028), (0.040, 0.790, 0.030), (-0.130, 1.150, 0.020))):
        deco.append(W.front_decal(f'{pre}_Oil_{k}', W.blob(x, z, r, seed=30 + k, rough=0.45), jacket, M['Oil'], 0.0045))
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]
    pants = T._trousers(pre, M, 'Trousers', src, legs=W.LEGS_TUCKED)
    oil = [W.front_decal(pre + '_OilKnee', W.blob(0.100, 0.560, 0.030, seed=41, rough=0.5), pants, M['Oil'], 0.003)]
    out += [pants] + T._decal_t(oil, pants)
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts(pre + '_Boot', M['Boots'])
    out += ushanka(pre + '_Ushanka', M)
    out += T._face(skin, lambda head: W.eye_bags(pre + '_EyeBag', M['EyeBags'], head) + W.stubble(pre + '_Stubble', M['Stubble'], head))
    out += vodka_bottle(pre, M)
    return out


def thermos(prefix, M):
    """Big thermos hanging from the left fist by its cup lid (T-pose: the left hand points along +X)."""
    import buddy_pool_bad as BD
    a = Vector((0.650, -0.014, 1.142))
    lid = BD.axis_loft(prefix + '_Lid', a, a + Vector((0.085, 0, 0)), [(0.0, 0.030), (0.1, 0.038), (1.0, 0.040)], M['Thermos_Cap'], seg=16)
    ring = BD.axis_loft(prefix + '_Ring', a + Vector((0.085, 0, 0)), a + Vector((0.105, 0, 0)), [(0.0, 0.043), (1.0, 0.043)],
                        M['Thermos_Steel'], seg=16)
    body = BD.axis_loft(prefix + '_Body', a + Vector((0.105, 0, 0)), a + Vector((0.390, 0, 0)), [(0.0, 0.043), (0.9, 0.043), (1.0, 0.036)],
                        M['Thermos'], seg=16)
    return [W.prop(o, 'LeftHand') for o in (lid, ring, body)]


def transit_trucker(body, face, M, skin):
    import buddy_pool_oldtown2 as O2
    pre = 'TRANSIT_TRUCKER'
    src = C.weight_source([body])
    out = [_t(o, src, C.no_head) for o in W.tank_top(pre + '_Tank', M['Tank'], body)]
    # buffalo-check flannel worn open over the tank top: dark bands across, dark stripes down the front panels and the back
    rows = C.BASE_TEE_ROWS
    row_mat = [(k % 2) for k in range(len(rows) - 1)]
    gap = lambda z: v_gap(z, z0=0.80, z1=1.255, top=0.120)
    shirt, parts = open_shirt(pre, M, src, rows=rows, arm_row=6, hem=(.806, .184, .124, -.004),
                                 mats=[M['Shirt'], M['Check'], M['Shirt_Roll']], row_mat=row_mat,
                                 sleeve_mat=[0, 1, 0, 1, 0] + [2] * 5, gap=gap)
    out += parts
    ssrc = C.weight_source([shirt])
    stripes = []
    for s in (1, -1):
        for x in (0.150, 0.195):
            stripes.append(W.front_decal(f'{pre}_CheckF_{s}_{x:.3f}', [(s * x - 0.008, 0.80), (s * x + 0.008, 0.80), (s * x + 0.008, 1.22),
                                                                       (s * x - 0.008, 1.22)], shirt, M['Check'], 0.0030, step=0.012))
    for x in (-0.12, -0.06, 0.0, 0.06, 0.12):
        stripes.append(G.decal(f'{pre}_CheckB_{x:+.2f}', [(x - 0.008, 0.80), (x + 0.008, 0.80), (x + 0.008, 1.22), (x - 0.008, 1.22)],
                               W.BACK(), [shirt], 0.0030, M['Check'], step=0.012))
    out += [_t(o, ssrc) for o in stripes]
    jeans = T._trousers(pre, M, 'Jeans', src)
    out.append(jeans)
    out += [_t(o, src) for o in W.belt(pre, M['Belt'], M['Buckle'])]
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks'], top=0.24), src))
    out += W.slides(pre, M['Socks'], M['Slides'])
    cap, base = O2.baseball_cap(pre + '_Cap', M['Cap'], M['Cap_Peak'])
    out += cap
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=base))
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.012, size=1.6)
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head))
    out += thermos(pre + '_Thermos', M)
    return out


BUILDERS = {'TRANSIT_SELLER': transit_seller, 'TRANSIT_TAXI': transit_taxi, 'TRANSIT_FLIPPER': transit_flipper, 'TRANSIT_GARAGE_DRUNK': transit_garage_drunk, 'TRANSIT_TRUCKER': transit_trucker}
