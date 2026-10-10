"""District pool 'Неблагополучный район', part 2 (TASK-000270): the rapper and the girl of easy virtue.
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
        label='Рэпер', group=GROUP, body=dict(thin=1.0), arm_down=62.0, face=dict(Happy=0.30),
        slots={'Tee': ((240, 238, 232), 0.85), 'Jeans': ((70, 102, 160), 0.9), 'Shoe_Upper': ((244, 244, 240), 0.6),
               'Shoe_Sole': ((206, 48, 46), 0.55), 'Shoe_Accent': ((206, 48, 46), 0.6), 'Shoe_Lace': ((244, 244, 240), 0.7),
               'Cap': ((30, 30, 34), 0.75), 'Cap_Peak': ((206, 48, 46), 0.7), 'Hair': ((40, 32, 28), 0.9), 'Gold': GOLD,
               'Medal_Gem': ((40, 120, 232), 0.15), 'WatchFace': ((236, 240, 246), 0.15), 'Shades_Frame': GOLD,
               'Shades_Lens': ((18, 20, 26), 0.06), 'Mic': ((36, 36, 40), 0.45), 'Mic_Grille': ((190, 192, 198), 0.35, 'metal')},
        colourways=[{'Tee': (34, 34, 38), 'Jeans': (152, 176, 210), 'Cap': (206, 48, 46), 'Cap_Peak': (30, 30, 34),
                     'Shoe_Sole': (30, 30, 34), 'Shoe_Accent': (240, 196, 52), 'Medal_Gem': (206, 40, 52)},
                    {'Tee': (246, 186, 46), 'Jeans': (40, 44, 58), 'Cap': (240, 238, 232), 'Cap_Peak': (52, 132, 92),
                     'Shoe_Upper': (40, 42, 48), 'Shoe_Sole': (240, 238, 232), 'Shoe_Accent': (52, 132, 92),
                     'Shoe_Lace': (240, 238, 232), 'Medal_Gem': (52, 172, 92)}]),
    'BAD_GIRL': dict(
        label='Девушка лёгкого поведения', group=GROUP, body=dict(thin=1.0), no_ears=True, face=dict(Blink=0.35),
        look=dict(mouth=(206, 24, 64), rim=(62, 112, 222), brow=(52, 36, 30)),
        slots={'Hair': ((246, 226, 150), 0.65), 'Jacket': ((218, 164, 86), 1.0), 'Spots': ((72, 46, 28), 1.0),
               'Fur': ((240, 226, 200), 1.0), 'Top': ((236, 64, 142), 0.6), 'Skirt': ((28, 26, 30), 0.3),
               'Tights': ((44, 38, 50), 0.6), 'Boots': ((150, 22, 44), 0.2), 'Boot_Sole': ((26, 24, 26), 0.5),
               'Hoops': GOLD, 'Lips': ((214, 26, 66), 0.3), 'Eyeshadow': ((70, 132, 236), 0.4), 'Blush': ((242, 112, 146), 0.6),
               'Bag': ((236, 64, 142), 0.25), 'Bag_Flap': ((196, 40, 112), 0.3), 'Clasp': GOLD},
        colourways=[{'Hair': (40, 30, 30), 'Jacket': (236, 236, 232), 'Spots': (36, 36, 40), 'Fur': (36, 36, 40),
                     'Top': (122, 52, 170), 'Skirt': (122, 52, 170), 'Boots': (28, 26, 30), 'Bag': (36, 36, 40),
                     'Bag_Flap': (122, 52, 170)},
                    {'Hair': (178, 42, 52), 'Jacket': (236, 140, 172), 'Spots': (150, 40, 90), 'Fur': (250, 240, 246),
                     'Top': (52, 192, 214), 'Skirt': (226, 226, 230), 'Tights': (240, 214, 196), 'Boots': (240, 238, 234),
                     'Bag': (52, 192, 214), 'Bag_Flap': (36, 150, 172), 'Lips': (236, 60, 120), 'Eyeshadow': (62, 192, 122)}]),
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
# Oversized tee: boxy, down to mid-thigh, dropped shoulders, wide elbow-length sleeves. Arm row 6 (z 1.06).
TEE_XL = [(.600, .252, .174, -.012), (.640, .254, .176, -.012), (.72, .254, .176, -.012), (.82, .252, .175, -.012),
          (.92, .250, .174, -.012), (1.00, .248, .172, -.008), (1.06, .246, .170, -.004), (1.15, .244, .170, 0.0),
          (1.225, .232, .171, .002), (1.252, .196, .170, .002), (1.264, .164, .160, .002), (1.268, .157, .151, 0.0),
          (1.262, .153, .146, 0.0), (1.252, .151, .144, 0.0)]
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


def bad_rapper(body, face, M, skin):
    src = C.weight_source([body])
    tee = W.top('RAPPER_Tee', TEE_XL, 6, TEE_XL_SLEEVE, (.616, .238, .162, -.012), [M['Tee']])
    _t(tee, src, _tee_weights)
    out = [tee]
    tsrc = C.weight_source([tee])
    jeans = C.legwear('RAPPER_Jeans', W.WAIST, .700, JEANS_LEGS, [M['Jeans']], **G.res('bottoms', n=16, subdiv=1))
    out.append(_t(jeans, src, _baggy_weights))
    out += _chunky_sneakers('RAPPER', M)
    # three thick gold chains, the longest with a big medallion
    for k, (drop, rad, off) in enumerate(((0.085, 0.166, 0.010), (0.180, 0.174, 0.019), (0.285, 0.182, 0.028))):
        ch, pts = _chain(f'RAPPER_Chain_{k}', M['Gold'], [tee], drop, rad, off, link=0.0064 + 0.0008 * k)
        out.append(_t(ch, tsrc, C.no_head))
        if k == 2:
            low = pts[0]
            medal = G.ellipsoid('RAPPER_Medal', low + Vector((0, -0.010, -0.040)), (0.044, 0.009, 0.044), M['Gold'], seg=20, rings=8)
            gem = G.ellipsoid('RAPPER_MedalGem', low + Vector((0, -0.018, -0.040)), (0.020, 0.006, 0.020), M['Medal_Gem'], seg=12, rings=6)
            out += [_t(medal, tsrc, C.no_head), _t(gem, tsrc, C.no_head)]
    cap, base = _backwards_cap('RAPPER_Cap', M)
    out += cap
    base_r = lambda phi: base(phi + math.pi)
    out.append(W.hair('RAPPER_Hair', M['Hair'], 'buzz', upper=lambda phi: base_r(phi) + 0.012))
    out += W.glasses('RAPPER_Shades', M['Shades_Frame'], M['Shades_Lens'], rx=0.058, rz=0.050, round_k=0.6)
    out += _big_watch('RAPPER_Watch', M)
    out += _microphone('RAPPER', M)
    _report('BAD_RAPPER', out)
    return out

# ------------------------------------------------------------------ BAD_GIRL
FUR_JACKET = [(.840, .218, .156, -.012), (.856, .224, .160, -.012), (.94, .222, .158, -.012), (1.02, .222, .158, -.008),
              (1.08, .224, .162, -.002), (1.10, .226, .165, 0.0), (1.17, .224, .170, .002), (1.235, .211, .173, .002),
              (1.250, .185, .176, .002), (1.262, .172, .172, .002), (1.268, .165, .166, 0.0), (1.260, .160, .158, 0.0)]  # arm row 5
FUR_SLEEVE = [(.232, .086), (.27, .082), (.32, .077), (.38, .073), (.44, .069), (.50, .066), (.540, .063), (.556, .060), (.552, .054)]
MINI_SKIRT = [(0.892, .186, .127, -.004), (0.86, .194, .133, -.006), (0.80, .206, .143, -.008), (0.73, .216, .152, -.010),
              (0.668, .222, .158, -.010), (0.674, .213, .150, -.010)]


def _spots(prefix, jacket, material, seed=11):
    """Leopard spots: irregular blobs on the front, back and sleeves (kept off the open front and the collar)."""
    rnd = random.Random(seed)
    out = []
    front = [(x, z) for x in (-0.19, -0.13, 0.13, 0.19) for z in (0.90, 0.99, 1.08, 1.17)]
    back = [(x, z) for x in (-0.17, -0.085, 0.0, 0.085, 0.17) for z in (0.90, 1.00, 1.10, 1.19)]
    sleeve = [(s * x, B.arm_z(x) + dz) for s in (1, -1) for x, dz in ((0.29, 0.03), (0.37, -0.03), (0.45, 0.025), (0.51, -0.02))]
    for kind, pts, axes in (('F', front + sleeve, FRONT()), ('B', back + sleeve, BACK())):
        for k, (x, z) in enumerate(pts):
            jx, jz = rnd.uniform(-0.018, 0.018), rnd.uniform(-0.018, 0.018)
            r = rnd.uniform(0.015, 0.022)
            u = (x + jx) if kind == 'F' else -(x + jx)
            o = G.decal(f'{prefix}_{kind}_{k}', W.blob(u, z + jz, r, n=9, seed=seed * 100 + k + (50 if kind == 'B' else 0), rough=0.45),
                        axes, [jacket], 0.0025, material, step=0.02)
            out.append(o)
    return out


def _girl_hair(prefix, M):
    """Big teased bleach-blonde hair: a puffy bob that frames the face and covers the ears, and a beehive on top."""
    lower = W.zprofile([(0, 1.700), (30, 1.690), (50, 1.585), (62, 1.440), (78, 1.360), (180, 1.340)])
    back = lambda phi: (1 - math.cos(phi)) / 2
    off = lambda phi, u: 0.010 + 0.026 * smoothstep(0.0, 0.45, u) + 0.010 * back(phi) + 0.008 * (1 - u) * back(phi)
    bob, _ = W.shell(prefix + '_Bob', M['Hair'], lower, off=off, thick=0.009, seg=32, rows=8)
    hive = G.ellipsoid(prefix + '_Beehive', (0, 0.018, 1.838), (0.118, 0.124, 0.098), M['Hair'], seg=20, rings=12)
    pouf = G.ellipsoid(prefix + '_Pouf', (0, -0.088, 1.760), (0.098, 0.060, 0.050), M['Hair'], seg=16, rings=10)
    return [C.rigid(o, 'Head') for o in (bob, hive, pouf)]


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
    src = C.weight_source([body])
    jacket = W.top('GIRL_Jacket', FUR_JACKET, 5, FUR_SLEEVE, (.856, .204, .142, -.012), [M['Jacket']])
    _t(jacket, src, C.no_head)
    jsrc = C.weight_source([jacket])
    deco = [W.front_decal('GIRL_Top', [(-0.056, 1.266), (0.056, 1.266), (0.056, 0.846), (-0.056, 0.846)], jacket, M['Top'], 0.0028, step=0.02)]
    deco += _spots('GIRL_Spot', jacket, M['Spots'])
    out = [jacket] + [_t(o, jsrc) for o in deco]
    # fur: shawl collar, the two front edges, cuffs
    collar = _ring('GIRL_FurCollar', lambda a: Vector((0.186 * math.sin(a), -0.178 * math.cos(a) + 0.004,
                                                         1.262 - 0.030 * ((1 + math.cos(a)) / 2) ** 2)),
                   40, lambda i, n: 0.026 + 0.007 * (i % 2), M['Fur'], seg=8)
    out.append(_t(collar, jsrc, C.no_head))
    for s in (1, -1):
        pts = C.projected_path([jacket], [(s * 0.058, z) for z in (1.215, 1.17, 1.12, 1.07, 1.02, 0.97, 0.92, 0.875, 0.846)], FRONT(), 0.006)
        out.append(_t(G.tube(f'GIRL_FurEdge_{s}', pts, lambda i, n: 0.012 + 0.004 * (i % 2), M['Fur'], seg=8), jsrc))
        x = 0.548
        cuff = _ring(f'GIRL_FurCuff_{s}', lambda a: Vector((s * x, 0.068 * math.cos(a), B.arm_z(x) + 0.070 * math.sin(a))), 22,
                     lambda i, n: 0.015 + 0.005 * (i % 2), M['Fur'], seg=6)
        out.append(_t(cuff, jsrc))
    out.append(W.skirt('GIRL_Skirt', M['Skirt'], MINI_SKIRT))
    out.append(_t(W.bottoms('GIRL_Tights', W.LEGS_TIGHTS, [M['Tights']]), src))
    boots = W.shoes('GIRL_Boot', M['Boots'], M['Boot_Sole'], high=True)
    for o in boots:
        if o.name.endswith('_Sole'):
            _scale_about(o, (0, 0, 0), (1.0, 1.0, 1.7))        # platform sole
    out += boots
    for s in (1, -1):
        side = 'Left' if s > 0 else 'Right'
        cx = s * B.LEG_X
        rows = [(0.095, 0.054), (0.16, 0.056), (0.24, 0.056), (0.32, 0.059), (0.40, 0.062), (0.432, 0.067), (0.437, 0.062), (0.428, 0.057)]
        sh = G.loft(f'GIRL_Shaft_{s}', [((cx, 0.004, z), (1, 0, 0), (0, 1, 0), r, r * 0.97) for z, r in rows], M['Boots'], seg=16,
                    cap_start=False, cap_end=False)
        wf = C.shoe_weights(s)
        C.set_weights(sh, [mix(wf(p), {P + side + 'Leg': 1.0}, smoothstep(0.15, 0.26, p.z))
                           for p in (sh.matrix_world @ v.co for v in sh.data.vertices)])
        out.append(sh)
    out += _girl_hair('GIRL_Hair', M)
    out += _hoops('GIRL_Hoop', M['Hoops'])

    def face_paint(head):
        res = W.blush('GIRL_Blush', M['Blush'], head)
        lips = [(0.040 * math.cos(a), 1.407 + (0.012 if math.sin(a) > 0 else 0.013) * math.sin(a)
                 - (0.004 * (1 - abs(math.cos(a))) ** 3 if math.sin(a) > 0 and abs(math.cos(a)) < 0.25 else 0.0))
                for a in [2 * math.pi * k / 20 for k in range(20)]]
        res.append(C.rigid(G.decal('GIRL_Lips', lips, FRONT(), [head], 0.0016, M['Lips'], step=0.006), 'Head'))
        for s in (1, -1):
            cx, cz = s * B.EYE_C[0], B.EYE_C[2]
            arc = [(cx + 0.058 * math.cos(a), cz + 0.070 * math.sin(a)) for a in [math.pi * k / 12 for k in range(13)]]
            res.append(C.rigid(G.decal(f'GIRL_Shadow_{s}', arc, FRONT(), [head], 0.0016, M['Eyeshadow'], step=0.008), 'Head'))
        return res
    out += _face(skin, face_paint)
    out += _handbag('GIRL', M)
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
