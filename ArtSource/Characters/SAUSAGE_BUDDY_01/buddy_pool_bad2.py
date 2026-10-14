"""District pool 'Неблагополучный район', part 2 (TASK-000270): the rapper and the girl of easy virtue. TASK-000535: the
Snoop Dogg rapper (BAD_RAPPER v07) moved to Downtown as OLD_RAPPER (its builder `snoop` stays here); BAD_RAPPER is now a
different, loser rapper (v10: the skinny 'runt' in a faded smiley tee with a novelty willy on the chain, acne and a wispy moustache; v08 was a
cocky one in a red puffer).
Same format as buddy_types.TYPES / BUILDERS; every garment has its own material slot <TYPE>_<Slot>.
Carried props are modelled in armature space at the T-pose (rig at the origin) and made rigid on the hand bone."""
import math
import random
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
from buddy_geo import smoothstep, mix, chain, FRONT, BACK

P = 'mixamorig:'
GOLD = ((214, 174, 76), 0.28, 'metal')
GROUP = 'Неблагополучный район'

TYPES = {
    'BAD_RAPPER': dict(
        label='Рэпер-неудачник', group=GROUP, hand_props=True, body=dict(thin=0.9), face=dict(Worried=0.75, Blink=0.25),
        look=dict(skin=(226, 166, 132), nose=(214, 140, 112), brow=(120, 90, 66), rim=(170, 110, 90)),
        slots={'Tee': ((84, 88, 70), 0.95), 'Smiley': ((186, 158, 66), 0.9), 'Print': ((36, 34, 32), 0.9), 'Stain': ((54, 52, 40), 0.95),
               'Boxers': ((214, 168, 176), 0.9), 'Hearts': ((176, 40, 52), 0.85), 'Jeans': ((52, 60, 80), 0.95),
               'Shoe_Upper': ((170, 166, 156), 0.85), 'Shoe_Sole': ((104, 100, 96), 0.8), 'Shoe_Accent': ((120, 40, 44), 0.8),
               'Shoe_Lace': ((150, 146, 138), 0.9), 'Cap': ((62, 62, 66), 0.9), 'Cap_Peak': ((104, 38, 42), 0.85),
               'Hair': ((120, 90, 66), 0.9), 'Fluff': ((128, 98, 72), 0.9), 'Acne': ((200, 92, 92), 0.6),
               'Gold': ((186, 156, 84), 0.5, 'metal'), 'Peel': ((92, 86, 76), 0.8), 'Shades_Frame': ((196, 168, 80), 0.5),
               'Shades_Lens': ((50, 36, 70), 0.1), 'Mic': ((36, 36, 40), 0.45), 'Mic_Grille': ((190, 192, 198), 0.35, 'metal'),
               'Tattoo': ((40, 46, 80), 0.8)},
        colourways=[{'Tee': (92, 44, 48), 'Stain': (58, 34, 34)},
                    {'Tee': (56, 56, 58), 'Stain': (36, 36, 34), 'Cap': (40, 40, 44)}]),
    'BAD_GIRL': dict(
        label='Девушка лёгкого поведения', group=GROUP, body=dict(thin=1.0), no_ears=True, face=dict(Happy=0.4),
        look=dict(mouth=(236, 64, 132), rim=(62, 112, 222), brow=(170, 130, 90)),
        slots={'Hair': ((236, 200, 124), 0.45), 'Top': ((242, 84, 164), 0.5), 'Print': ((250, 250, 255), 0.2),
               'Bolero': ((252, 244, 248), 1.0), 'Skirt': ((18, 18, 22), 0.15), 'Stockings': ((58, 46, 48), 0.38),
               'Lace': ((84, 78, 88), 0.8), 'Seam': ((20, 16, 18), 0.6), 'Frill': ((242, 84, 164), 0.6),
               'Boots': ((16, 16, 18), 0.1), 'Boot_Sole': ((26, 24, 26), 0.4), 'Hoops': GOLD,
               'Eyeshadow': ((236, 150, 196), 0.5), 'Blush': ((246, 150, 172), 0.6),
               'Bag': ((242, 84, 164), 0.25), 'Bag_Flap': ((200, 50, 120), 0.3), 'Clasp': GOLD},
        colourways=[{'Hair': (60, 40, 34), 'Top': (130, 60, 190), 'Bag': (130, 60, 190), 'Bag_Flap': (100, 40, 150)},
                    {'Hair': (200, 50, 60), 'Top': (52, 192, 214), 'Bolero': (24, 24, 28), 'Bag': (52, 192, 214),
                     'Bag_Flap': (36, 150, 172)}]),
}


def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _report(prefix, objs):
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print(f'[BUDDY] {prefix} outfit+props triangles before join: {tris}')


def _scale_about(ob, pivot, k):
    pv = Vector(pivot)
    for v in ob.data.vertices:
        d = v.co - pv
        v.co = pv + Vector((d.x * k[0], d.y * k[1], d.z * k[2]))
    ob.data.update()
    return ob


def _ring(name, centre_fn, n, radius, material, seg=8):
    """Closed bumpy torus through n + 1 points (first == last)."""
    pts = [centre_fn(2 * math.pi * k / n) for k in range(n + 1)]
    return G.tube(name, pts, radius, material, seg=seg)

# ------------------------------------------------------------------ BAD_RAPPER
# Oversized tee sleeves: wide, elbow length (v03 crops the body of the tee, TEE_CROP below).
TEE_XL_SLEEVE = [(.262, .098), (.30, .097), (.35, .096), (.40, .094), (.445, .093), (.468, .092), (.462, .085)]
JEANS_LEGS = [(.66, .095), (.56, .095), (.46, .094), (.36, .093), (.28, .092), (.225, .091),
              (.200, .098), (.182, .088), (.166, .097), (.150, .087), (.134, .096), (.118, .088), (.104, .094), (.090, .088)]


def _tee_weights(p, w):
    """Torso weights above the waist; below it the long hem hangs like a skirt (hips + a little of each thigh)."""
    w = C.no_head(p, w)
    t = smoothstep(0.92, 0.80, p.z)
    if t <= 0.0:
        return w
    u = 0.50 * smoothstep(0.80, 0.60, p.z)
    k = smoothstep(-0.08, 0.08, p.x)
    return mix(w, {P + 'Hips': 1 - u, P + 'LeftUpLeg': u * k, P + 'RightUpLeg': u * (1 - k)}, t)


def _leg_side(p, side):
    c = chain(p.z, [(.38, side + 'Leg'), (.48, side + 'UpLeg')])
    return {P + k: v for k, v in mix(c, {'Hips': 1.0}, smoothstep(.74, .86, p.z)).items()}


def _baggy_weights(p, w):
    """Wide trouser legs reach nearer the other leg than their own: weigh them by height and side instead of the
    nearest skin; the waistband keeps the transferred weights."""
    k = smoothstep(-0.04, 0.04, p.x)
    legs = mix(_leg_side(p, 'Right'), _leg_side(p, 'Left'), k)
    return mix(legs, w, smoothstep(0.74, 0.82, p.z))


def _chain(name, material, targets, drop, rad, off, link=0.0068, seg=64):
    bvh = G.bvh_of(targets)
    pts = []
    for k in range(seg + 1):
        a = 2 * math.pi * k / seg
        f = ((1 + math.cos(a)) / 2) ** 3
        p = Vector((rad * math.sin(a), -rad * math.cos(a), 1.262 - drop * f))
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None:
            nrm = nrm if nrm.dot(Vector((p.x, p.y, 0))) >= 0 else -nrm
            p = loc + nrm * off
        pts.append(p)
    return G.tube(name, pts, lambda i, n: link + 0.0034 * (i % 2), material, seg=8), pts


def _backwards_cap(prefix, M):
    """Baseball cap built facing forward, then turned 180 degrees: the peak over the neck, the strap opening over
    the forehead."""
    base_f = W.zprofile([(0, 1.648), (90, 1.664), (180, 1.694)])
    rows = [('fit', base_f, 0.006), ('fit', lambda phi: base_f(phi) + 0.006, 0.013),
            ('fit', lambda phi: max(base_f(phi) + 0.020, W.h_of(1.718)), 0.016), ('fit', lambda phi: 1.762, 0.017),
            ('fit', lambda phi: 1.796, 0.016), ('fit', lambda phi: 1.818, 0.015)]
    crown = W.ring_loft(prefix + '_Crown', rows, [M['Cap']], seg=32)
    peak = W.peak(prefix + '_Peak', M['Cap_Peak'], base_f, length=0.078, droop=0.006, curve=0.014, span=60, off=0.008, thick=0.008)
    btn = G.ellipsoid(prefix + '_Button', (0, 0, B.HEAD_TOP + 0.016), (0.013, 0.013, 0.006), M['Cap_Peak'], seg=10, rings=6)
    turn = Matrix.Rotation(math.pi, 4, 'Z')
    for o in (crown, peak):
        o.data.transform(turn); o.data.update()
    # strap opening over the forehead: a hair-coloured arch with the strap across its bottom
    arch = [(0.030 * math.cos(a), 1.704 + 0.026 * math.sin(a)) for a in [math.pi * k / 10 for k in range(11)]]
    hole = G.decal(prefix + '_Opening', arch, FRONT(), [crown], 0.0025, M['Hair'], step=0.008)
    strap = G.decal(prefix + '_Strap', [(-0.036, 1.702), (0.036, 1.702), (0.036, 1.712), (-0.036, 1.712)], FRONT(), [crown], 0.0040,
                    M['Cap_Peak'], step=0.008, thickness=0.003)
    return [C.rigid(o, 'Head') for o in (crown, peak, btn, hole, strap)], base_f


def _chunky_sneakers(prefix, M):
    out = W.shoes(prefix, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    for o in out:
        s = -1 if '_-1' in o.name else 1
        _scale_about(o, (s * B.LEG_X, -0.065, 0.0), (1.15, 1.25, 1.50))
    for s in (1, -1):        # heel counter in the accent colour (outer side)
        up = next(o for o in out if o.name == f'{prefix}_Shoe_{s}_Upper')
        outline = [(-s * y, z) for y, z in ((0.020, 0.060), (0.075, 0.060), (0.132, 0.080), (0.135, 0.170), (0.090, 0.200), (0.040, 0.150))]
        if s < 0:
            outline = outline[::-1]
        d = G.decal(f'{prefix}_Heel_{s}', outline, G.SIDE(s), [up], 0.003, M['Shoe_Accent'], step=0.012, thickness=0.003)
        wf = C.shoe_weights(s)
        C.set_weights(d, [wf(d.matrix_world @ v.co) for v in d.data.vertices])
        out.append(d)
    return out


def _big_watch(prefix, M, x=0.600, side=1):
    s, r, zc = side, 0.042, B.arm_z(x)
    band = G.loft(prefix + '_Band', [((s * (x - 0.011), 0, zc), (0, 1, 0), (0, 0, 1), r, r),
                                     ((s * (x + 0.011), 0, zc), (0, 1, 0), (0, 0, 1), r, r)], M['Gold'], seg=14)
    case = G.ellipsoid(prefix + '_Case', (s * x, 0, zc + r + 0.003), (0.027, 0.027, 0.010), M['Gold'], seg=16, rings=6)
    dial = G.ellipsoid(prefix + '_Dial', (s * x, 0, zc + r + 0.009), (0.020, 0.020, 0.006), M['WatchFace'], seg=16, rings=6)
    return [C.rigid(o, ('Left' if s > 0 else 'Right') + 'ForeArm') for o in (band, case, dial)]


def _microphone(prefix, M, tilt_deg=22.0):
    """Hand-held mic through the right palm (T-pose: right hand along -X, palm down). It points forward and, with
    the arm hanging, tilts up toward the face."""
    t = math.radians(tilt_deg)
    c = Vector((-0.692, -0.004, 1.156))
    d = Vector((math.sin(t), -math.cos(t), 0.0))
    handle = G.tube(prefix + '_MicHandle', [c - d * 0.050, c, c + d * 0.074], lambda i, n: (0.0125, 0.0150, 0.0185)[i], M['Mic'], seg=12)
    band = G.tube(prefix + '_MicBand', [c + d * 0.070, c + d * 0.084], 0.0215, M['Mic'], seg=12)
    head = G.ellipsoid(prefix + '_MicHead', c + d * 0.108, (0.032, 0.032, 0.032), M['Mic_Grille'], seg=14, rings=10)
    return [W.prop(o, 'RightHand') for o in (handle, band, head)]


TEE_CROP = [(.840, .250, .174, -.012), (.880, .250, .174, -.012), (.92, .250, .174, -.012), (1.00, .248, .172, -.008),
            (1.06, .246, .170, -.004), (1.15, .244, .170, 0.0), (1.225, .232, .171, .002), (1.252, .196, .170, .002),
            (1.264, .164, .160, .002), (1.268, .157, .151, 0.0), (1.262, .153, .146, 0.0), (1.252, .151, .144, 0.0)]   # arm row 4
SAG_WAIST = [(0.768, .200, .138), (0.756, .202, .139), (0.700, .206, .140), (0.640, .208, .140)]   # jeans hanging off the butt
SAG_LEGS = [(.54, .100), (.46, .097), (.38, .095), (.30, .093), (.24, .092), (.20, .098), (.182, .088), (.166, .097), (.150, .087),
            (.134, .096), (.118, .088), (.104, .094), (.090, .088)]
BOXER_LEGS = [(.70, .100), (.66, .104), (.62, .104), (.605, .098)]


def heart(cx, cz, r, n=20):
    """Heart outline (the classic parametric curve), r = half height."""
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * r / 17, cz + z * r / 17))
    return pts


def clock_medallion(prefix, M, low):
    """A wall-clock-size medallion on the longest chain: gold rim, white dial, twelve hour marks, two black hands."""
    c = low + Vector((0.0, -0.012, -0.062))
    f = c + Vector((0.0, -0.016, 0.0))
    out = [G.ellipsoid(prefix + '_Rim', c, (0.060, 0.012, 0.060), M['Gold'], seg=24, rings=8),
           G.ellipsoid(prefix + '_Dial', c + Vector((0.0, -0.007, 0.0)), (0.050, 0.008, 0.050), M['Clock_Face'], seg=24, rings=8)]
    for k in range(12):
        a = 2 * math.pi * k / 12
        out.append(G.ellipsoid(f'{prefix}_Mark_{k}', f + Vector((0.040 * math.sin(a), 0.0, 0.040 * math.cos(a))), (0.0035, 0.002, 0.0035),
                               M['Clock_Hands'], seg=6, rings=3))
    out.append(G.tube(prefix + '_HourHand', [f, f + Vector((0.016, 0.0, 0.018))], 0.0030, M['Clock_Hands'], seg=4))
    out.append(G.tube(prefix + '_MinuteHand', [f, f + Vector((-0.004, 0.0, 0.034))], 0.0022, M['Clock_Hands'], seg=4))
    return out


def star_shades(prefix, M, lenses=(1, -1)):
    """Gold star-shaped party shades with dark star lenses; `lenses` - the sides that still have one (a lens popped out
    of the cheap pair on the loser rapper)."""
    import bmesh
    out = []
    for s in (1, -1):
        c = Vector((s * 0.058, -0.168, 1.560))
        pts = [c + Vector(((0.050 if k % 2 == 0 else 0.022) * math.cos(math.pi / 2 + 2 * math.pi * k / 10), 0.0,
                           (0.050 if k % 2 == 0 else 0.022) * math.sin(math.pi / 2 + 2 * math.pi * k / 10))) for k in range(10)]
        bm = bmesh.new()
        vf = [bm.verts.new(p + Vector((0.0, -0.002, 0.0))) for p in pts]
        vb = [bm.verts.new(p + Vector((0.0, 0.003, 0.0))) for p in pts]
        bm.faces.new(vf)
        bm.faces.new(list(reversed(vb)))
        for i in range(10):
            bm.faces.new((vf[i], vb[i], vb[(i + 1) % 10], vf[(i + 1) % 10]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.ops.triangulate(bm, faces=bm.faces[:])                 # the star polygon is concave
        if s in lenses:
            out.append(G.from_bm(f'{prefix}_Lens_{s}', bm, M['Shades_Lens'], smooth=False))
        else:
            bm.free()
        out.append(G.tube(f'{prefix}_Rim_{s}', pts + pts[:2], 0.0036, M['Shades_Frame'], seg=5))
        hinge = c + Vector((s * 0.048, 0.008, 0.016))
        temple = [hinge, hinge + Vector((s * 0.026, 0.040, -0.002)), Vector((s * 0.150, -0.030, 1.552)), Vector((s * 0.153, 0.010, 1.532))]
        out.append(G.tube(f'{prefix}_Temple_{s}', temple, 0.0035, M['Shades_Frame'], seg=6))
    out.append(G.tube(prefix + '_Bridge', [Vector((0.016, -0.170, 1.570)), Vector((0.0, -0.174, 1.576)), Vector((-0.016, -0.170, 1.570))],
                      0.0036, M['Shades_Frame'], seg=6))
    return [C.rigid(o, 'Head') for o in out]


TALL_TEE = [(.620, .232, .160, -.012), (.635, .234, .162, -.012), (.70, .232, .160, -.012), (.78, .228, .158, -.012)] + \
           [(z, rx * 1.15, ry * 1.15, dy) for z, rx, ry, dy in W.TEE if z >= 0.86]           # XXL tall tee to the knees; arm row 8
XL_SLEEVE = [(.212, .094), (.25, .092), (.30, .089), (.35, .087), (.40, .085), (.430, .084), (.425, .076)]   # past the elbow
LEGS_BAGGY = [(.70, .098), (.60, .097), (.50, .096), (.43, .095), (.34, .094), (.26, .094), (.19, .094), (.14, .096), (.128, .090)]


def tall_tee(prefix, M, src):
    """The rapper's XXL white tall tee: wide, sleeves past the elbows, the hem down to the knees."""
    tee = W.top(prefix + '_TallTee', TALL_TEE, 8, XL_SLEEVE, (.635, .224, .154, -.012), [M['Tee']])
    return _t(tee, src, _tee_weights)


def paw_pendant(prefix, M, low, k=1.0):
    """Big gold dog-paw pendant (the 'Dogg') hanging at the lowest point of the long chain."""
    c = Vector(low) + Vector((0.0, -0.010, -0.032 * k))
    out = [G.ellipsoid(prefix + '_Pad', c, (0.024 * k, 0.008 * k, 0.020 * k), M['Gold'], seg=14, rings=8)]
    for j, (dx, dz) in enumerate(((-0.026, 0.024), (-0.010, 0.036), (0.010, 0.036), (0.026, 0.024))):
        out.append(G.ellipsoid(f'{prefix}_Toe_{j}', c + Vector((dx * k, -0.002, dz * k)), (0.0085 * k, 0.006 * k, 0.010 * k), M['Gold'],
                               seg=10, rings=6))
    return out


def _braid_weights(ob):
    def w(p):
        t = smoothstep(1.30, 1.40, p.z)
        return {P + 'Head': t, P + 'Spine2': 1.0 - t}
    C.set_weights(ob, [w(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return ob


def snoop_braids(prefix, M, targets):
    """Long thin braids pulled back from a cornrowed scalp: over the crown and the back of the head, the side ones
    falling over the shoulders onto the chest, the back ones down to the shoulder blades (laid on `targets`)."""
    import buddy_pool_construction as CN
    rnd = random.Random(42)
    scalp, _ = W.shell(prefix + '_Scalp', M['Scalp'], W.HAIRLINE, None, off=0.004, thick=0.004, seg=32, rows=6)
    out = [C.rigid(scalp, 'Head')]
    n = 26
    for k in range(n):
        deg = -125 + 250 * (k + rnd.uniform(-0.3, 0.3)) / (n - 1)          # 0 = the back of the head
        phi = math.radians(deg + 180)
        s = 1 if math.sin(phi) > 0 else -1
        front = abs(deg) > 70                                             # behind the ears: over the shoulders to the chest
        z_root = rnd.uniform(1.680, 1.730)
        pts = [W.head_at(phi, W.h_of(z), 0.014 + 0.004 * (z < 1.6))[0] for z in (z_root, 1.640, 1.580, 1.510, 1.450)]
        radial = Vector((math.sin(phi), -math.cos(phi), 0.0))
        low = pts[-1] + radial * 0.022 + Vector((0, 0, 1.385 - pts[-1].z))
        if front:
            xe = rnd.uniform(0.100, 0.150)
            raw = [Vector((s * 0.165, 0.000, 1.300)), Vector((s * 0.150, -0.110, 1.240)), Vector((s * xe, -0.170, 1.160)),
                   Vector((s * xe, -0.180, rnd.uniform(1.060, 1.110)))]
        else:
            xe = math.sin(phi) * 0.16
            raw = [Vector((xe * 1.05, 0.150, 1.300)), Vector((xe, 0.180, 1.200)), Vector((xe * 0.95, 0.180, rnd.uniform(1.060, 1.120)))]
        ps, _ = CN.on_surface(targets, raw, 0.012, step=0.035, smooth=1)
        pts += [low] + list(ps)
        braid = G.tube(f'{prefix}_Braid_{k}', pts, lambda i, n_: 0.0068 + 0.0016 * (i % 2), M['Braid'], seg=6)
        out.append(_braid_weights(braid))
    return out


def cornrows(prefix, M, n=7):
    """Cornrows over the top of the head: braided ridges from the forehead hairline back over the crown to where the long
    braids hang from (no cap, so the braids read like Snoop's)."""
    out = []
    k_head = lambda x0: math.sqrt(max(0.05, 1.0 - (x0 / B.HEAD_R) ** 2))
    for r in range(n):
        x0 = (r - (n - 1) / 2) * 0.031
        k = k_head(x0)
        pts = []
        for i in range(17):
            b = math.radians(38 + 132 * i / 16)                      # forehead hairline -> over the top -> the back
            pts.append(Vector((x0, -B.HEAD_RY * k * math.cos(b), B.HEAD_CYL_TOP + B.HEAD_R * k * math.sin(b))))
        pts = [p + (p - Vector((0.0, 0.0, B.HEAD_CYL_TOP))).normalized() * 0.008 for p in pts]
        out.append(C.rigid(G.tube(f'{prefix}_Row_{r}', pts, lambda i, n_: 0.0072 + 0.0022 * (i % 2), M['Braid'], seg=6), 'Head'))
    return out


def dollar_pendant(prefix, M, low, k=1.6):
    """A big money-green dollar sign on the long gold chain: an S of two arcs with a bar through it, on a gold bail."""
    c = Vector(low) + Vector((0.0, -0.014, -0.095 * k / 1.6))
    s_pts = [(0.020 * math.cos(math.radians(a)), 0.020 + 0.020 * math.sin(math.radians(a))) for a in range(25, 271, 15)]
    s_pts += [(0.020 * math.cos(math.radians(a)), -0.020 + 0.020 * math.sin(math.radians(a))) for a in range(90, -161, -15)]
    return [G.tube(prefix + '_S', [c + Vector((x * k, 0.0, z * k)) for x, z in s_pts], 0.0050 * k, M['Dollar'], seg=8),
            G.tube(prefix + '_Bar', [c + Vector((0.0, -0.002, 0.050 * k)), c + Vector((0.0, -0.002, -0.050 * k))], 0.0036 * k, M['Dollar'], seg=8),
            G.ellipsoid(prefix + '_Bail', c + Vector((0.0, 0.0, 0.056 * k)), (0.008, 0.006, 0.009), M['Gold'], seg=8, rings=4)]


def neck_chain(name, material, targets, drop, rad, off, link, base_z=1.222, seg=64):
    """Gold chain round the neck below the coat collar (sides and back under the coat), dropping on the tee in front."""
    import buddy_pool_construction as CN
    raw = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        f = ((1 + math.cos(a)) / 2) ** 3
        raw.append(Vector((rad * math.sin(a), -rad * math.cos(a), base_z - drop * f)))
    ps, _ = CN.on_surface(targets, raw, off, step=0.012, smooth=3, closed=True)
    low = min(ps, key=lambda p: p.z)
    return G.tube(name, ps + [ps[0]], lambda i, n: link + 0.0030 * (i % 2), material, seg=8), low


SNOOP_COAT = [(0.400, .262, .186, -.012), (0.415, .264, .188, -.012), (0.50, .260, .184, -.012), (0.62, .256, .182, -.012),
              (0.70, .252, .180, -.012), (0.78, .248, .176, -.012), (0.86, .244, .172, -.012), (0.94, .243, .171, -.012),
              (1.02, .243, .169, -.008), (1.08, .247, .174, -.002), (1.10, .249, .178, 0.0), (1.17, .246, .184, .002),
              (1.235, .230, .188, .002), (1.250, .200, .192, .002), (1.262, .186, .188, .002), (1.268, .180, .182, 0.0),
              (1.260, .176, .176, 0.0)]                                     # long coat to mid-calf over the tall tee; arm row 10
SNOOP_COAT_SLEEVE = [(.230, .110), (.27, .108), (.32, .104), (.38, .100), (.44, .096), (.50, .090), (.545, .086), (.560, .084), (.556, .078)]


def _coat_gap(z):
    return 0.120 - 0.050 * smoothstep(0.90, 1.25, z)


def fur_coat(prefix, M, src):
    """A long purple coat worn open over the tall tee, down to mid-calf, with a white faux-fur shawl collar running down
    the front edges and fur cuffs (the long skirt follows the hips and thighs like the homeless man's coat)."""
    import buddy_pool_bad3 as B3
    import buddy_pool_construction as CN
    coat = W.top(prefix + '_Coat', SNOOP_COAT, 10, SNOOP_COAT_SLEEVE, (.415, .254, .180, -.012), [M['Coat']],
                 cut=lambda c: c.y < 0 and abs(c.x) < _coat_gap(c.z))
    _t(coat, src, B3._coat_weights)
    csrc = C.weight_source([coat])
    raw = [Vector((-_coat_gap(0.95) - 0.016, -0.200, 0.950)), Vector((-0.100, -0.196, 1.080)), Vector((-0.092, -0.180, 1.190)),
           Vector((-0.120, -0.110, 1.262)), Vector((-0.060, 0.120, 1.280)), Vector((0.060, 0.120, 1.280)), Vector((0.120, -0.110, 1.262)),
           Vector((0.092, -0.180, 1.190)), Vector((0.100, -0.196, 1.080)), Vector((_coat_gap(0.95) + 0.016, -0.200, 0.950))]
    ps, _ = CN.on_surface([coat], raw, 0.020, step=0.014, smooth=3)
    collar = G.tube(prefix + '_FurCollar', ps, lambda i, n: 0.024 + 0.008 * (i % 2), M['Fur'], seg=8)
    out = [coat, _t(collar, csrc, C.no_head)]
    for s in (1, -1):
        x = 0.548
        cuff = _ring(f'{prefix}_FurCuff_{s}', lambda a: Vector((s * x, 0.092 * math.cos(a), B.arm_z(x) + 0.092 * math.sin(a))), 22,
                     lambda i, n: 0.017 + 0.006 * (i % 2), M['Fur'], seg=6)
        out.append(_t(cuff, csrc))
    return coat, out


def _joint(prefix, M):
    """A joint in the left corner of the mouth with a glowing tip and a bit of ash (a head prop)."""
    a, b = Vector((0.028, -0.124, 1.404)), Vector((0.094, -0.196, 1.392))
    d = (b - a).normalized()
    parts = [G.tube(prefix + '_Body', [a, b], lambda i, n: (0.0042, 0.0050)[i], M['Joint'], seg=8),
             G.tube(prefix + '_Ember', [b, b + d * 0.006], 0.0050, M['Ember'], seg=8),
             G.ellipsoid(prefix + '_Ash', b + d * 0.011, (0.0045, 0.0045, 0.0045), M['Ash'], seg=6, rings=4)]
    return [W.prop(o, 'Head') for o in parts]


def snoop(body, face, M, skin):
    """OLD_RAPPER (TASK-000535; BAD_RAPPER v07 before): in the look of Snoop Dogg, a bit more like him and a bit richer
    for Downtown (Vadim): no cap - cornrows over the top and long thin braids over the shoulders and down the back; dark
    shades, a thin drooping moustache and a chin goatee, a joint in the corner of the mouth; the huge white tall tee
    under a long open purple coat with a white faux-fur shawl collar and fur cuffs, two thick gold chains with a big
    money-green dollar sign on the longest, a gold watch, baggy light jeans stacked over wheat work boots. Very thin,
    normal height; the face stays the common Sausage Buddy one."""
    import buddy_pool_construction as CN
    src = C.weight_source([body])
    tee = tall_tee('RAPPER', M, src)
    coat, out = fur_coat('RAPPER', M, src)
    out = [tee] + out
    tsrc = C.weight_source([tee])
    for k, (drop, rad, off) in enumerate(((0.100, 0.200, 0.005), (0.270, 0.204, 0.006))):     # under the coat collar at the sides
        ch, low = neck_chain(f'RAPPER_Chain_{k}', M['Gold'], [tee], drop, rad, off, 0.0044 + 0.0008 * k)
        out.append(_t(ch, tsrc, C.no_head))
        if k == 1:
            out += [_t(o, tsrc, C.no_head) for o in dollar_pendant('RAPPER_Dollar', M, low)]
    out += _big_watch('RAPPER_Watch', M, x=0.600, side=1)
    jeans = W.bottoms('RAPPER_Jeans', LEGS_BAGGY, [M['Jeans']])
    out.append(_t(jeans, src, _baggy_weights))
    out += W.shoes('RAPPER_Timb', M['Boots'], M['Boots_Sole'], M['Boot_Lace'], high=True)
    out += snoop_braids('RAPPER_Hair', M, [coat, tee])
    out += cornrows('RAPPER_Cornrow', M)
    out += W.glasses('RAPPER_Shades', M['Shades_Frame'], M['Shades_Lens'], rx=0.060, rz=0.046, round_k=0.6)
    out += W.mustache('RAPPER_Mustache', M['Mustache'], droop=0.014, size=0.8)
    goatee = G.ellipsoid('RAPPER_Goatee', (0.0, B.head_surface_y(0.0, 1.362, 0.003), 1.362), (0.011, 0.005, 0.024), M['Mustache'], seg=10, rings=6)
    out.append(C.rigid(goatee, 'Head'))
    out += _joint('RAPPER_Joint', M)
    return out


SAG2_WAIST = [(0.720, .204, .140), (0.708, .206, .141), (0.650, .208, .141), (0.600, .209, .141)]     # sagging below the butt
SAG2_LEGS = [(.48, .100), (.40, .097), (.32, .095), (.26, .093), (.22, .092), (.20, .098), (.182, .088), (.166, .097), (.150, .087),
             (.134, .096), (.118, .088), (.104, .094), (.090, .088)]


# A plain tee one size too big (the BASE tee rows a little wider, wider and longer sleeves; arm row 6). The extra rows at
# 1.135 and 1.20 let the tee follow W.reshape's 'thin' falloff (1.10-1.20) under the chest print: over rows 7-9 cm apart
# the flat faces sank a print or let it float by up to 6 mm. The oversized TEE_CROP + TEE_XL_SLEEVE folded at the
# shoulders in idle.
LOSER_TEE = [(z, rx * 1.04, ry * 1.08, dy) for z, rx, ry, dy in W.TEE[:7]] + [(1.135, .2070, .1550, .0010)] + \
            [(z, rx * 1.04, ry * 1.08, dy) for z, rx, ry, dy in W.TEE[7:8]] + [(1.200, .2010, .1600, .0020)] + W.TEE[8:]
LOSER_SLEEVE = [(.212, .084), (.24, .081), (.28, .079), (.32, .077), (.36, .076), (.39, .075), (.385, .067)]


LOSER_ACNE = [(0.096, 1.452, 0.0045), (0.072, 1.438, 0.0035), (-0.088, 1.462, 0.0050), (-0.100, 1.440, 0.0035),
              (-0.064, 1.446, 0.0030), (0.030, 1.632, 0.0040), (-0.026, 1.648, 0.0035), (0.012, 1.346, 0.0045),
              (-0.040, 1.358, 0.0030)]                                            # acne: cheeks, forehead, chin


def willy_pendant(prefix, M, low):
    """A big fake-gold novelty willy on the thin chain (Vadim), cartoon-simple: two balls on top by the bail, the
    shaft hanging down with a rounded tip; the cheap plating already peeling."""
    bc = Vector(low) + Vector((0.0, -0.002, -0.006))
    bail = [bc + Vector((0.0, 0.0070 * math.cos(2 * math.pi * q / 16), 0.0070 * math.sin(2 * math.pi * q / 16))) for q in range(17)]
    out = [G.tube(prefix + '_Bail', bail, 0.0024, M['Gold'], seg=6, caps=False)]
    top = Vector(low) + Vector((0.0, -0.012, -0.028))
    for k, s in enumerate((1, -1)):
        out.append(G.ellipsoid(f'{prefix}_Ball_{k}', top + Vector((s * 0.0155, 0.002, 0.0)), (0.0165, 0.0145, 0.0165), M['Gold'],
                               seg=14, rings=8))
    tip = top + Vector((0.0, -0.004, -0.074))
    out.append(G.tube(prefix + '_Shaft', [top + Vector((0.0, -0.002, -0.004)), tip + Vector((0.0, 0.0, 0.010))], 0.0135, M['Gold'], seg=14))
    out.append(G.ellipsoid(prefix + '_Tip', tip, (0.0155, 0.0145, 0.0170), M['Gold'], seg=14, rings=8))
    for k, (dx, dy, dz, r) in enumerate(((0.020, -0.0135, -0.004, 0.006), (-0.006, -0.0165, -0.046, 0.005))):
        out.append(G.ellipsoid(f'{prefix}_Peel_{k}', top + Vector((dx, dy, dz)), (r, 0.003, r * 0.8), M['Peel'], seg=8, rings=4))
    return out


def smiley_print(prefix, M, tee, cx=0.0, cz=1.090):
    """One big dumb yellow smiley on the chest (Vadim: a dorkier tee, nothing detailed): a black rim, the yellow face,
    two oval eyes and a wide grin - five flat shapes that read from far away."""
    out = [W.front_decal(prefix + '_Rim', C.ellipse(cx, cz, 0.076, 0.076, 32), tee, M['Print'], 0.0040, step=0.012),
           W.front_decal(prefix + '_Face', C.ellipse(cx, cz, 0.069, 0.069, 32), tee, M['Smiley'], 0.0048, step=0.012)]
    for k, s in enumerate((1, -1)):
        out.append(W.front_decal(f'{prefix}_Eye_{k}', C.ellipse(cx + s * 0.024, cz + 0.018, 0.008, 0.014, 14), tee, M['Print'], 0.0056,
                                 step=0.006))
    arc = lambda r, a: (cx + r * math.cos(math.radians(a)), cz - 0.004 + r * math.sin(math.radians(a)))
    grin = [arc(0.047, a) for a in range(200, 341, 10)] + [arc(0.035, a) for a in range(340, 199, -10)]
    out.append(W.front_decal(prefix + '_Grin', grin, tee, M['Print'], 0.0056, step=0.006))
    return out


def bad_rapper(body, face, M, skin):
    """v10 (TASK-000535, Vadim: bring the runt back, only another thing on the chain and a palette that suits the rough
    district; then 'something shaped like a willy' on the chain and a dorkier tee, nothing detailed; then darker, more
    rough district and uglier - he was starting to look a bit cool): a skinny pathetic wannabe in cheap bling - a sad,
    sleepy face with acne spots, a wispy teen moustache and a crooked teardrop 'tattoo' under the eye; a faded dark olive
    tee a size too big with a faded mustard smiley and grease stains; dirty dark denim sagging below the butt over faded
    pink boxers with red hearts; a long thin fake-gold chain with a big novelty willy (the plating peeling); cheap
    plastic-gold star party shades with one lens popped out; a faded backwards cap; dirty grey chunky trainers; a
    microphone in the right hand (dropped at the slightest danger). The bright acid-green tee with a yellow smiley
    stayed a render. v09 wore a dirty-white tee with the 'THUG LIFE' meme print (pixel 'deal with it' shades over the words; too
    detailed, Vadim). The first try of this look (a red tank jersey '00', white boxers, a clock on the chain) and the
    pacifier on the chain were never built; v08 was a cocky wannabe in a red puffer with a crown on the chain, v07 the
    Snoop (now OLD_RAPPER), v03 the first sagging-jeans rapper."""
    pre = 'LOSER'
    src = C.weight_source([body])
    tee = _t(W.top(pre + '_Tee', LOSER_TEE, 6, LOSER_SLEEVE, (.806, .188, .134, -.004), [M['Tee']]), src, _tee_weights)
    tsrc = C.weight_source([tee])
    deco = smiley_print(pre + '_Smiley', M, tee)
    deco += [W.front_decal(f'{pre}_Stain_{k}', W.blob(x, z, r, seed=440 + k, rough=0.5, sx=1.3), tee, M['Stain'], 0.0045)
             for k, (x, z, r) in enumerate(((-0.120, 0.880, 0.026), (0.140, 0.960, 0.018), (0.050, 0.840, 0.014)))]
    out = [tee] + [_t(o, tsrc) for o in deco]
    boxers = C.legwear(pre + '_Boxers', W.WAIST, .700, BOXER_LEGS, [M['Boxers']], **G.res('bottoms', n=16, subdiv=1))
    _t(boxers, src)
    hearts = []
    for axes, tag in ((FRONT(), 'F'), (BACK(), 'B')):
        for k, (x, z) in enumerate(((-0.150, 0.748), (-0.060, 0.760), (0.040, 0.746), (0.130, 0.758))):
            hearts.append(G.decal(f'{pre}_Heart{tag}_{k}', heart(x, z, 0.014), axes, [boxers], 0.0022, M['Hearts'], step=0.006))
    out += [boxers] + [_t(o, C.weight_source([boxers])) for o in hearts]
    jeans = C.legwear(pre + '_Jeans', SAG2_WAIST, .500, SAG2_LEGS, [M['Jeans']], **G.res('bottoms', n=16, subdiv=1))
    out.append(_t(jeans, src, _baggy_weights))
    out += _chunky_sneakers(pre, M)
    ch, pts = _chain(f'{pre}_Chain', M['Gold'], [tee, body], 0.330, 0.172, 0.010, link=0.0040)     # runs under the smiley
    out.append(_t(ch, tsrc, C.no_head))
    out += [_t(o, tsrc, C.no_head) for o in willy_pendant(pre + '_Willy', M, pts[0])]
    cap, base = _backwards_cap(pre + '_Cap', M)
    out += cap
    base_r = lambda phi: base(phi + math.pi)
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=lambda phi: base_r(phi) + 0.012))
    out += star_shades(pre + '_Shades', M, lenses=(1,))
    out += _microphone(pre, M)

    def face_paint(head):
        drop = [(0.080, 1.483)] + [(0.080 + 0.0058 * math.cos(math.radians(d)), 1.471 + 0.0058 * math.sin(math.radians(d)))
                                   for d in range(150, 391, 20)]                  # a teardrop: the tip up, round at the bottom
        res = [C.rigid(G.decal(pre + '_Tear', drop, FRONT(), [head], 0.0016, M['Tattoo'], step=0.003), 'Head')]
        spots = [G.decal(f'{pre}_Acne_{k}', C.ellipse(x, z, r, r * 0.9, 8), FRONT(), [head], 0.0016, M['Acne'], step=0.01)
                 for k, (x, z, r) in enumerate(LOSER_ACNE)]
        G.join(spots[0], spots[1:])
        res.append(C.rigid(spots[0], 'Head'))
        rnd = random.Random(447)                 # a wispy teen moustache: sparse light fuzz over the upper lip
        fuzz, tries = [], 0
        while len(fuzz) < 36 and tries < 4000:
            tries += 1
            q = Vector((rnd.uniform(-0.048, 0.048), rnd.uniform(1.416, 1.438)))
            if q.y > 1.438 - 0.010 * (q.x / 0.048) ** 2 or any((q - o).length < 0.0050 for o in fuzz):
                continue
            fuzz.append(q)
        dots = [G.decal(f'{pre}_Fuzz_{k}', C.ellipse(q.x, q.y, 0.0014, 0.0019, 5), FRONT(), [head], 0.0016, M['Fluff'], step=0.01)
                for k, q in enumerate(fuzz)]
        G.join(dots[0], dots[1:])
        res.append(C.rigid(dots[0], 'Head'))
        return res
    out += _face(skin, face_paint)
    return out


FUR_JACKET = [(.840, .218, .156, -.012), (.856, .224, .160, -.012), (.94, .222, .158, -.012), (1.02, .222, .158, -.008),
              (1.08, .224, .162, -.002), (1.10, .226, .165, 0.0), (1.17, .224, .170, .002), (1.235, .211, .173, .002),
              (1.250, .185, .176, .002), (1.262, .172, .172, .002), (1.268, .165, .166, 0.0), (1.260, .160, .158, 0.0)]  # arm row 5
FUR_SLEEVE = [(.232, .086), (.27, .082), (.32, .077), (.38, .073), (.44, .069), (.50, .066), (.540, .063), (.556, .060), (.552, .054)]
MINI_SKIRT = [(0.892, .186, .127, -.004), (0.86, .194, .133, -.006), (0.80, .206, .143, -.008), (0.73, .216, .152, -.010),
              (0.668, .222, .158, -.010), (0.674, .213, .150, -.010)]


CROP_TEE = [W.lerp_row(W.TEE, 1.000)] + [r for r in W.TEE if r[0] > 1.000]       # baby tee cropped above the navel; arm row 3
BOLERO = [r for r in FUR_JACKET if r[0] >= 1.02]                                  # short faux-fur bolero; arm row 2
FLARED_MINI = [(0.892, .186, .127, -.004), (0.86, .196, .134, -.006), (0.80, .214, .148, -.008), (0.73, .232, .162, -.010),
               (0.672, .244, .172, -.010), (0.678, .235, .164, -.010)]                # skater mini, flared
STOCKING_TOP = 0.600                                                               # stocking tops at mid-thigh
HEEL_PITCH = 40.0                                                                  # feet tilted toes-down for the stilettos


def _hair_weights(ob, z_lo=1.28, z_hi=1.38):
    """Long hair: the head carries the top, the chest the lower part, blended over the neck."""
    def w(p):
        t = smoothstep(z_lo, z_hi, p.z)
        return {P + 'Head': t, P + 'Spine2': 1.0 - t}
    C.set_weights(ob, [w(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return ob


def _wavy_lock(name, pts, nrms, width, thick, material, wave=0.010):
    """One flat lock along a polyline, its flat side to `nrms`, waving sideways, thinning to a soft tip."""
    Pts = [Vector(p) for p in pts]
    n = len(Pts) - 1
    secs = []
    for i, p in enumerate(Pts):
        t = (Pts[min(i + 1, n)] - Pts[max(i - 1, 0)]).normalized()
        a = Vector(nrms[i]).cross(t)
        if a.length < 1e-4:
            a = t.orthogonal()
        a.normalize()
        k = i / n
        w = width * (0.85 + 0.25 * math.sin(math.pi * min(1.0, k * 1.4))) * (1.0 if k < 0.8 else 1.0 - 2.0 * (k - 0.8))
        secs.append((p + a * wave * math.sin(2.6 * math.pi * k) * min(1.0, k * 3), a, t.cross(a).normalized(), max(w, width * 0.55), thick))
    return _hair_weights(G.loft(name, secs, material, seg=8))


def glam_hair(prefix, M, targets):
    """Long voluminous platinum hair in big glam waves: a deep side parting with a bang swept across the forehead,
    volume on top, full sides, a fall round the neck, wavy locks over the shoulders onto the chest and down the back."""
    import buddy_pool_construction as CN
    lower = W.zprofile([(0, 1.668), (25, 1.640), (45, 1.540), (60, 1.450), (90, 1.420), (180, 1.400)])
    off = lambda phi, u: 0.012 + 0.022 * smoothstep(0.0, 0.5, u) + 0.018 * (1 - u) * min(1.0, abs(math.degrees(phi)) / 45.0)
    top, _ = W.shell(prefix + '_Top', M['Hair'], lower, None, off=off, thick=0.010, seg=40, rows=8)
    out = [C.rigid(top, 'Head')]
    pts, nrms = [], []
    for u in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):                       # the bang: from the parting across to the left temple
        p, nrm = W.head_at(math.radians(-16 + 72 * u), W.h_of(1.716 - 0.092 * u ** 1.3), 0.024)
        pts.append(p)
        nrms.append(nrm)
    out.append(C.rigid(_wavy_lock(prefix + '_Bang', pts, nrms, 0.046, 0.011, M['Hair'], wave=0.0), 'Head'))
    neck = W.zprofile([(0, 1.310), (180, 1.310)])
    fall, _ = W.shell(prefix + '_Fall', M['Hair'], neck, lambda phi: lower(phi) + 0.02, off=lambda phi, u: 0.034 - 0.010 * u, thick=0.010,
                      seg=24, rows=4, arc=(math.radians(50), math.radians(310)))
    out.append(_hair_weights(fall))
    for k, (s, deg, xe, side, ze) in enumerate([(s, d, x, sd, z) for s in (1, -1) for d, x, sd, z in
                                               ((44, 0.060, 'F', 1.000), (56, 0.090, 'F', 0.995), (68, 0.122, 'F', 1.015),
                                                (90, 0.155, 'B', 1.020), (110, 0.136, 'B', 0.990), (130, 0.108, 'B', 0.975),
                                                (150, 0.074, 'B', 0.965), (168, 0.032, 'B', 0.960))]):
        phi = math.radians(s * deg)
        p0, _ = W.head_at(phi, lower(phi) + 0.012, off(phi, 0.0) - 0.003)
        radial = Vector((math.sin(phi), -math.cos(phi), 0.0))
        drop = Vector((p0.x, p0.y, 1.335)) + radial * 0.024
        yb = -1 if side == 'F' else 1
        raw = [Vector((s * (xe + 0.050), yb * 0.060, 1.272)), Vector((s * (xe + 0.028), yb * 0.130, 1.215)),
               Vector((s * (xe + 0.012), yb * 0.155, 1.150)), Vector((s * xe, yb * 0.160, 1.080)), Vector((s * xe, yb * 0.158, ze))]
        ps, ns = CN.on_surface(targets, raw, 0.022, step=0.032, smooth=1)
        out.append(_wavy_lock(f'{prefix}_Lock_{k}', [p0, drop] + list(ps), [radial, radial] + list(ns), 0.026 if side == 'F' else 0.046,
                              0.012, M['Hair']))
    return out


def stockings(prefix, M, src):
    """Sheer-black stockings from the ankles to mid-thigh: the tights cut below the hips (so they sit on the legs like
    tights), a lace top band with a scalloped edge, a seam up the back of each leg."""
    import bmesh
    import buddy_pool_bad as BD
    ob = _t(W.bottoms(prefix, W.LEGS_TIGHTS, [M['Stockings']]), src)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > STOCKING_TOP], context='FACES')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.append(M['Lace'])
    for poly in ob.data.polygons:
        if poly.center.z > STOCKING_TOP - 0.035:
            poly.material_index = len(ob.data.materials) - 1
    ob.data.update()
    deco = []
    for s in (1, -1):
        u = -s * B.LEG_X                                    # the back view mirrors x
        deco.append(G.decal(f'{prefix}_Seam_{s}', BD.stripe_outline(u - 0.0018, u + 0.0018, 0.125, STOCKING_TOP - 0.038), BACK(), [ob], 0.0018,
                            M['Seam'], step=0.02))
        top = [ob.matrix_world @ v.co for v in ob.data.vertices if v.co.z > STOCKING_TOP - 0.006 and v.co.x * s > 0]
        cx = sum(p.x for p in top) / max(1, len(top))
        cy = sum(p.y for p in top) / max(1, len(top))
        top.sort(key=lambda p: math.atan2(p.y - cy, p.x - cx))
        for k, p in enumerate(top[::2]):
            d = Vector((p.x - cx, p.y - cy, 0.0)).normalized()
            deco.append(G.ellipsoid(f'{prefix}_Scallop_{s}_{k}', p + d * 0.002 + Vector((0, 0, 0.003)), (0.0065, 0.0040, 0.0060), M['Lace'],
                                    seg=6, rings=4))
    return [ob] + _decal_t(deco, ob)


def _decal_t(pieces, garment):
    src = C.weight_source([garment])
    return [C.transfer(o, src) for o in pieces]


def stiletto_pumps(prefix, M):
    """Glossy black pumps: the cartoon shoe made a little sleeker (narrower, lower); tilted with the feet later."""
    shoes = W.shoes(prefix, M['Boots'], M['Boot_Sole'])
    for o in shoes:
        s = -1 if '_-1_' in o.name else 1
        _scale_about(o, (s * B.LEG_X, -0.040, 0.0), (0.92, 0.90, 0.85))
    return shoes


def tilt_feet(objs, pitch=HEEL_PITCH):
    """High heels on the shared skeleton: everything weighted to the feet (the body's feet, the stockings, the shoes)
    is tilted toes-down about the ankles in the rest pose, then the toes are turned back flat about the balls of the
    feet, as in a real high-heeled shoe. The clips stay shared; their grounding puts the lowest point - the platform
    under the toes and the heel tips - on the floor, which lifts the whole figure onto the heels."""
    R = Matrix.Rotation(math.radians(pitch), 3, 'X')
    Ri = R.inverted()
    for ob in objs:
        names = {g.index: g.name for g in ob.vertex_groups}
        for side in ('Left', 'Right'):
            a = W.bone_rest(side + 'Foot').translation
            ball = a + R @ (W.bone_rest(side + 'ToeBase').translation - a)
            foot, toe = P + side + 'Foot', P + side + 'ToeBase'
            for v in ob.data.vertices:
                wf = sum(g.weight for g in v.groups if names.get(g.group) == foot)
                wt = sum(g.weight for g in v.groups if names.get(g.group) == toe)
                if wf + wt > 1e-3:
                    q = v.co.lerp(a + R @ (v.co - a), min(1.0, wf + wt))
                    v.co = q.lerp(ball + Ri @ (q - ball), min(1.0, wt))
        ob.data.update()


def stilettos(prefix, M, shoes, platform=0.026):
    """Very high thin stilettos: the front of each (tilted) sole made into a platform under the flat toes (its bottom
    lowered, blended in over the ball of the foot), and a long heel from the back of the shoe down to the floor."""
    out = []
    for s in (1, -1):
        side = 'Left' if s > 0 else 'Right'
        sole = next(o for o in shoes if o.name.endswith(f'_Shoe_{s}_Sole'))
        y_front = min(v.co.y for v in sole.data.vertices)
        y_back = max(v.co.y for v in sole.data.vertices)
        toe = [v for v in sole.data.vertices if v.co.y < y_front + 0.10]
        z_bot = min(v.co.z for v in toe)
        z_mid = (max(v.co.z for v in toe) + z_bot) / 2
        for v in sole.data.vertices:
            t = 1.0 - smoothstep(y_front + 0.085, y_front + 0.120, v.co.y)
            if t > 0.0 and v.co.z < z_mid:
                v.co.z -= platform * t
        sole.data.update()
        floor = z_bot - platform
        back = [v.co for v in sole.data.vertices if v.co.y > y_back - 0.022]
        z_att = min(p.z for p in back)
        hx = sum(p.x for p in back) / len(back)
        hy = y_back - 0.016
        heel = G.tube(f'{prefix}_{s}', [Vector((hx, hy - 0.004, z_att + 0.006)), Vector((hx, hy + 0.010, floor + 0.004))],
                      lambda i, n: (0.0110, 0.0040)[i], M['Boot_Sole'], seg=10)
        tip = G.ellipsoid(f'{prefix}_Tip_{s}', Vector((hx, hy + 0.010, floor + 0.004)), (0.0050, 0.0050, 0.004), M['Boot_Sole'], seg=8, rings=4)
        for o in (heel, tip):
            C.set_weights(o, [{P + side + 'Foot': 1.0} for _ in o.data.vertices])
        out += [heel, tip]
    return out


def skirt_trim(prefix, M, skirt):
    """A pink ruffle round the hem of the mini (the chain belt was dropped: it read as a stray hoop, Vadim)."""
    ssrc = C.weight_source([skirt])
    frill = _ring(prefix + '_Frill', lambda a: Vector((0.250 * math.sin(a), -0.010 - 0.178 * math.cos(a), 0.668 + 0.005 * math.sin(14 * a))),
                  56, lambda i, n: 0.0095 + 0.0035 * (i % 2), M['Frill'], seg=6)
    return [_t(frill, ssrc)]


def _hoops(prefix, material):
    out = []
    for s in (1, -1):
        c = Vector((s * 0.166, 0.010, 1.330))
        ring = _ring(f'{prefix}_{s}', lambda a: c + Vector((0, 0.034 * math.sin(a), 0.034 * math.cos(a))), 20, 0.0045, material, seg=6)
        out.append(C.rigid(ring, 'Head'))
    return out


def _handbag(prefix, M):
    """Small handbag hanging from the left hand by its short handle (T-pose: left hand along +X, palm down; the bag
    sits past the fingertips, so it hangs under the hand in the idle pose)."""
    secs = []
    for x, hw, hd, k in ((0.826, 0.062, 0.022, 0.0), (0.832, 0.070, 0.028, 1), (0.880, 0.080, 0.032, 1), (0.930, 0.088, 0.032, 1),
                         (0.946, 0.084, 0.028, 1), (0.952, 0.070, 0.020, 0.0)):
        secs.append(((x, 0.0, 1.156), (0, 1, 0), (0, 0, 1), hw, hd))
    bag = G.loft(prefix + '_Bag', secs, M['Bag'], seg=16)
    flap = G.decal(prefix + '_Flap', [(0.830, -0.070), (0.830, 0.070), (0.880, 0.050), (0.900, 0.0), (0.880, -0.050)],
                   W.TOP(1.5), [bag], 0.0025, M['Bag_Flap'], step=0.010, thickness=0.003)
    clasp = G.ellipsoid(prefix + '_Clasp', (0.894, 0.0, 1.156 + 0.034), (0.010, 0.010, 0.006), M['Clasp'], seg=10, rings=6)
    path = [(0.836, -0.050), (0.800, -0.046), (0.770, -0.030), (0.756, 0.0), (0.770, 0.030), (0.800, 0.046), (0.836, 0.050)]
    handle = G.tube(prefix + '_Handle', [Vector((x, y, 1.156)) for x, y in path], 0.0065, M['Bag'], seg=8)
    return [W.prop(o, 'LeftHand') for o in (bag, flap, clasp, handle)]


def bad_girl(body, face, M, skin):
    """v06 (TASK-000525/526, Vadim: prettier and a bit sexier, stockings, a better skirt, real high stilettos; a fictional character, nothing
    explicit): long voluminous honey-blonde hair in glam waves with a side-swept bang; a hot-pink cropped baby tee with
    a rhinestone heart (bare midriff) under a short white faux-fur bolero; a flared glossy black mini with a pink ruffle
    hem; sheer-black stockings with a back seam and scalloped lace tops to mid-thigh; glossy black platform pumps on very
    high thin stilettos (the feet are tilted toes-down in the rest pose, the grounding lifts her onto the heels); gold
    hoops; soft pink eyeshadow, blush and a pink smile. v04 had black tights and thigh-high boots; v03 the bleach-blonde
    beehive, the leopard jacket and red knee boots."""
    src = C.weight_source([body])
    r0 = CROP_TEE[0]
    top = _t(W.top('GIRL_Top', CROP_TEE, 3, W.SLEEVE_SHORT, (1.008, r0[1] - 0.006, r0[2] - 0.006, r0[3]), [M['Top']]), src, C.no_head)
    tsrc = C.weight_source([top])
    out = [top, _t(W.front_decal('GIRL_Heart', heart(0.0, 1.120, 0.026), top, M['Print'], 0.003, step=0.006), tsrc)]
    b0 = BOLERO[0]
    bolero = W.top('GIRL_Bolero', BOLERO, 2, FUR_SLEEVE, (b0[0] + 0.008, b0[1] - 0.008, b0[2] - 0.008, b0[3]), [M['Bolero']],
                   cut=lambda c: c.y < 0 and abs(c.x) < 0.090)
    _t(bolero, src, C.no_head)
    bsrc = C.weight_source([bolero])
    out.append(bolero)
    collar = _ring('GIRL_FurCollar', lambda a: Vector((0.186 * math.sin(a), -0.178 * math.cos(a) + 0.004,
                                                         1.262 - 0.030 * ((1 + math.cos(a)) / 2) ** 2)),
                   40, lambda i, n: 0.024 + 0.007 * (i % 2), M['Bolero'], seg=8)
    out.append(_t(collar, bsrc, C.no_head))
    for s in (1, -1):
        x = 0.548
        cuff = _ring(f'GIRL_FurCuff_{s}', lambda a: Vector((s * x, 0.068 * math.cos(a), B.arm_z(x) + 0.070 * math.sin(a))), 22,
                     lambda i, n: 0.015 + 0.005 * (i % 2), M['Bolero'], seg=6)
        out.append(_t(cuff, bsrc))
    skirt = W.skirt('GIRL_Skirt', M['Skirt'], FLARED_MINI)
    out += [skirt] + skirt_trim('GIRL_Skirt', M, skirt)
    out += stockings('GIRL_Stocking', M, src)
    shoes = stiletto_pumps('GIRL_Shoe', M)
    out += shoes
    out += glam_hair('GIRL_Hair', M, [bolero, collar, top])
    out += _hoops('GIRL_Hoop', M['Hoops'])

    def face_paint(head):
        res = W.blush('GIRL_Blush', M['Blush'], head)
        for s in (1, -1):
            cx, cz = s * B.EYE_C[0], B.EYE_C[2]
            arc = [(cx + 0.056 * math.cos(a), cz + 0.064 * math.sin(a)) for a in [math.pi * k / 12 for k in range(13)]]
            res.append(C.rigid(G.decal(f'GIRL_Shadow_{s}', arc, FRONT(), [head], 0.0016, M['Eyeshadow'], step=0.008), 'Head'))
        return res
    out += _face(skin, face_paint)
    out += _handbag('GIRL', M)
    feet = {P + n for n in ('LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase')}
    tilt_feet([body] + [o for o in out if o.type == 'MESH' and any(g.name in feet for g in o.vertex_groups)])
    out += stilettos('GIRL_Heel', M, shoes)
    _report('BAD_GIRL', out)
    return out


def _face(skin, fn):
    import bpy
    head = W.head_target(skin)
    try:
        return fn(head)
    finally:
        me = head.data
        bpy.data.objects.remove(head)
        bpy.data.meshes.remove(me)


BUILDERS = {'BAD_RAPPER': bad_rapper, 'BAD_GIRL': bad_girl}
