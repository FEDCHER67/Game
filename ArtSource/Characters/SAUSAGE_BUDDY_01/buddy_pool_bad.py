"""District pool 'Неблагополучный район' (TASK-000270): the courtyard gopnik, the drunk and the hustler on the base Sausage
Buddy. TASK-000511: the gopnik in a blue tracksuit with three white stripes, the hustler (v03) back in his dark leather jacket
with new accessories, so the two no longer look alike. Same format as buddy_types.TYPES / BUILDERS; every garment and prop has its own
<TYPE>_<Slot> material. Carried props (seed cone, bottle) are rigid on a hand bone and exported as the separate 'Props' mesh."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T
from buddy_geo import smoothstep

P = 'mixamorig:'
GROUP = 'Неблагополучный район'
GOLD = ((214, 174, 76), 0.28, 'metal')

TYPES = {
    'BAD_GOPNIK': dict(
        label='Гопник', group=GROUP, hand_props=True, body=dict(thin=0.5), face=dict(Blink=0.25, Happy=0.15),
        slots={'Jacket': ((36, 66, 168), 0.7), 'Jacket_Rib': ((26, 48, 128), 0.8), 'Stripes': ((242, 242, 238), 0.7),
               'Zip': ((196, 196, 202), 0.3, 'metal'), 'Pants': ((36, 66, 168), 0.7), 'Pants_Rib': ((26, 48, 128), 0.8),
               'Socks': ((246, 246, 242), 0.9), 'Shoes': ((18, 18, 20), 0.14), 'Shoe_Sole': ((34, 30, 28), 0.6),
               'Cap': ((112, 100, 84), 0.95), 'Hair': ((54, 44, 38), 0.9), 'Husk': ((34, 32, 32), 0.6),
               'Bag': ((198, 162, 110), 0.95), 'Seeds': ((38, 36, 34), 0.55)},
        colourways=[{'Jacket': (30, 32, 40), 'Jacket_Rib': (22, 24, 30), 'Pants': (30, 32, 40), 'Pants_Rib': (22, 24, 30),
                     'Cap': (72, 72, 76)},
                    {'Jacket': (168, 34, 42), 'Jacket_Rib': (128, 26, 32), 'Pants': (30, 32, 36), 'Pants_Rib': (22, 24, 28),
                     'Cap': (40, 40, 44), 'Shoes': (232, 232, 228)}]),
    'BAD_DRUNK': dict(
        label='Алкаш', group=GROUP, hand_props=True, body=dict(belly=0.6), arm_down=70.0, face=dict(Blink=0.4, Happy=0.2), own_eyes=True,
        look=dict(skin=(238, 160, 124), nose=(222, 52, 58), rim=(196, 92, 92), brow=(120, 108, 100)),
        slots={'Tank': ((240, 238, 230), 0.85), 'Stains': ((198, 168, 92), 0.9), 'Pants': ((92, 104, 134), 0.95),
               'Pants_Rib': ((78, 90, 118), 0.95), 'Socks': ((96, 88, 82), 0.95), 'Slides': ((46, 46, 50), 0.55),
               'Navel': ((176, 98, 74), 0.7), 'Hair': ((126, 118, 108), 0.9), 'Stubble': ((92, 82, 78), 0.95),
               'EyeBags': ((152, 102, 122), 0.8), 'Bottle': ((40, 124, 58), 0.12)},
        colourways=[{'Tank': (232, 224, 198), 'Pants': (52, 54, 60), 'Pants_Rib': (44, 46, 52), 'Socks': (58, 60, 92),
                     'Slides': (40, 90, 160)},
                    {'Pants': (104, 110, 86), 'Pants_Rib': (88, 94, 72), 'Socks': (190, 184, 172), 'Slides': (150, 54, 44),
                     'Bottle': (122, 74, 34)}]),
    'BAD_HUSTLER': dict(
        label='Темщик', group=GROUP, face=dict(Blink=0.3, Happy=0.35),
        slots={'Leather': ((30, 28, 28), 0.32), 'Leather_Rib': ((22, 20, 20), 0.6), 'Lapel': ((40, 36, 36), 0.28),
               'Button': ((18, 18, 20), 0.4), 'Turtleneck': ((44, 44, 52), 0.9), 'Jeans': ((112, 138, 178), 0.9),
               'Socks': ((30, 30, 34), 0.9), 'Shoes': ((16, 16, 18), 0.14), 'Shoe_Sole': ((30, 26, 24), 0.6),
               'Hair': ((34, 30, 28), 0.22), 'HairComb': ((18, 16, 16), 0.3), 'Gold': GOLD, 'WatchFace': ((24, 24, 28), 0.2),
               'Shades_Frame': GOLD, 'Shades_Lens': ((20, 22, 30), 0.06), 'Pack': ((64, 42, 30), 0.35), 'Pack_Strap': ((40, 28, 22), 0.45)},
        colourways=[{'Leather': (90, 54, 34), 'Leather_Rib': (70, 42, 26), 'Lapel': (102, 62, 40), 'Turtleneck': (20, 20, 24),
                     'Jeans': (30, 30, 34)},
                    {'Leather': (44, 44, 48), 'Leather_Rib': (34, 34, 38), 'Lapel': (54, 54, 58), 'Turtleneck': (122, 32, 42),
                     'Jeans': (66, 84, 124), 'Pack': (24, 22, 22)}]),
}

# ------------------------------------------------------------------ helpers
_t = T._t
_decal_t = T._decal_t


def axis_loft(name, a, b, prof, material, seg=16, cap_start=True, cap_end=True):
    """Round loft along the segment a -> b; prof = [(t 0..1, radius)] (radius may be (ru, rv))."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    u = d.orthogonal().normalized()
    v = d.cross(u).normalized()
    secs = []
    for t, r in prof:
        ru, rv = r if isinstance(r, tuple) else (r, r)
        secs.append((a + (b - a) * t, u, v, ru, rv))
    return G.loft(name, secs, material, seg=seg, cap_start=cap_start, cap_end=cap_end)


def rbox(name, center, half, material, bevel=0.006, rot=None):
    """Bevelled box (phone, pouch)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((*half, 1.0)), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, 0.9 * min(half)), segments=2, affect='EDGES', profile=0.5)
    m = Matrix.Translation(center) @ (rot or Matrix.Identity(3)).to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return G.from_bm(name, bm, material, smooth=False)


def pointy(objs, sign, extend=0.075, pinch=0.62, flatten=0.40, curl=0.016):
    """Turn the chunky sneaker into a pointy 'tufli' dress shoe: the toe stretched forward, pinched to a point,
    flattened and curled up a little (shoe frame un-yawed first)."""
    cx = sign * B.LEG_X
    yaw = Matrix.Rotation(math.radians(-6 * sign), 3, 'Z')
    inv = yaw.inverted()
    piv = Vector((cx, 0, 0))
    for o in objs:
        for v in o.data.vertices:
            p = piv + inv @ (v.co - piv)
            t = smoothstep(-0.080, -0.236, p.y)
            if t > 0:
                p.y -= extend * t ** 1.3
                p.x = cx + (p.x - cx) * (1 - pinch * t)
                z0 = 0.036
                if p.z > z0:
                    p.z = z0 + (p.z - z0) * (1 - flatten * t)
                p.z += curl * t ** 3
            v.co = piv + yaw @ (p - piv)
        o.data.update()


def pointy_shoes(prefix, M, upper='Shoes', sole='Shoe_Sole'):
    out = W.shoes(prefix, M[upper], M[sole])
    for s in (1, -1):
        pointy([o for o in out if f'_Shoe_{s}_' in o.name], s)
    return out


def head_pt(x, z, extra):
    return Vector((x, B.head_surface_y(x, z, extra), z))

# ------------------------------------------------------------------ BAD_GOPNIK
GOP_LEGS = [(.70, .090), (.60, .088), (.50, .084), (.43, .081), (.34, .076), (.27, .070), (.236, .064)]
GOP_CUFF = [(.226, .054), (.214, .051), (.212, .047)]
CAP_BASE = W.zprofile([(0, 1.668), (90, 1.650), (180, 1.632)])


def _stand_collar(name, material, dy=0.002):
    rows = [(1.250, .172, .167), (1.290, .163, .158), (1.318, .158, .152), (1.323, .153, .147), (1.317, .149, .143), (1.255, .151, .145)]
    secs = [((0, dy, z), (1, 0, 0), (0, 1, 0), rx, ry) for z, rx, ry in rows]
    return G.loft(name, secs, material, seg=32, cap_start=False, cap_end=False)


def _sleeve_stripes(prefix, jacket, material, offsets=(-0.013, 0.013), width=0.009, x0=0.165, x1=0.568):
    out = []
    for s in (1, -1):
        for k, c in enumerate(offsets):
            pts = [(s * x0, c - width / 2), (s * x1, c - width / 2), (s * x1, c + width / 2), (s * x0, c + width / 2)]
            out.append(G.decal(f'{prefix}_{s}_{k}', pts, W.TOP(1.6), [jacket], 0.0025, material, step=0.012))
    return out


def seed_cone(prefix, M):
    """Kraft-paper cone of sunflower seeds held in the right hand (T-pose armature space, palm faces -Z)."""
    tip = Vector((-0.800, -0.020, 1.112))
    mouth = Vector((-0.610, -0.070, 1.092))
    prof = [(0.0, 0.004), (0.10, 0.012), (0.35, 0.026), (0.70, 0.040), (0.93, 0.048), (1.0, 0.050)]
    cone = axis_loft(prefix + '_Cone', tip, mouth, prof, M['Bag'], seg=14, cap_end=False)
    d = (mouth - tip).normalized()
    # crumpled paper rim: alternate rim vertices pushed in / out
    me = cone.data
    for v in me.vertices:
        t = (v.co - tip).dot(d) / (mouth - tip).length
        if t > 0.97:
            r = v.co - (tip + d * (v.co - tip).dot(d))
            ang = math.atan2(r.dot(d.orthogonal().normalized().cross(d)), r.dot(d.orthogonal().normalized()))
            v.co += d * (0.008 * math.sin(ang * 5)) + r.normalized() * 0.004 * math.cos(ang * 7)
    G.solidify(cone, 0.003, offset=1.0)
    out = [cone]
    mound_c = mouth - d * 0.010
    out.append(G.ellipsoid(prefix + '_Mound', mound_c, (0.044, 0.044, 0.014), M['Seeds'],
                           rot=d.to_track_quat('Z', 'Y').to_matrix(), seg=12, rings=6))
    rnd = [(0.0, 0.0), (0.020, 0.012), (-0.018, 0.010), (0.010, -0.020), (-0.012, -0.018), (0.028, -0.006)]
    q = d.to_track_quat('Z', 'Y').to_matrix()
    for k, (a, b) in enumerate(rnd):
        c = mound_c + q @ Vector((a, b, 0.012))
        rot = q @ Matrix.Rotation(k * 1.1, 3, 'Z')
        out.append(G.ellipsoid(f'{prefix}_Seed_{k}', c, (0.010, 0.0055, 0.004), M['Seeds'], rot=rot, seg=8, rings=5))
    return [W.prop(o, 'RightHand') for o in out]


def stripe_outline(u0, u1, v0, v1, step=0.02):
    """Thin rectangle [u0, u1] x [v0, v1] with points every `step` along its long sides: G.decal adds no interior points
    to a stripe narrower than two steps, so a plain 4-corner stripe was a flat chord cutting through the leg or sleeve and
    only its ends showed (TASK-000511)."""
    if u1 - u0 >= v1 - v0:
        n = max(2, int(round((u1 - u0) / step)))
        a = [(u0 + (u1 - u0) * k / n, v0) for k in range(n + 1)]
        b = [(u0 + (u1 - u0) * k / n, v1) for k in range(n + 1)]
    else:
        n = max(2, int(round((v1 - v0) / step)))
        a = [(u1, v0 + (v1 - v0) * k / n) for k in range(n + 1)]
        b = [(u0, v0 + (v1 - v0) * k / n) for k in range(n + 1)]
    return a + b[::-1]


def tracksuit_stripes(prefix, jacket, pants, material, offsets=(-0.018, 0.0, 0.018), width=0.009):
    """Three bold stripes down the outer side of each sleeve (T-pose top) and each trouser leg."""
    out = []
    for s in (1, -1):
        x0, x1 = sorted((s * 0.165, s * 0.568))
        for k, c in enumerate(offsets):
            out.append(G.decal(f'{prefix}_Sleeve_{s}_{k}', stripe_outline(x0, x1, c - width / 2, c + width / 2), W.TOP(1.6), [jacket], 0.0025,
                               material, step=0.02))
            out.append(G.decal(f'{prefix}_Leg_{s}_{k}', stripe_outline(c - width / 2, c + width / 2, 0.25, 0.80), G.SIDE(s), [pants], 0.0025,
                               material, step=0.02))
    return out


def gopnik(body, face, M, skin):
    src = C.weight_source([body])
    jacket = W.top('GOP_Jacket', W.HOODIE, 7, W.HOODIE_SLEEVE, (.750, .174, .118, -.010), [M['Jacket'], M['Jacket_Rib']],
                   row_mat=[1] + [0] * 13, sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(jacket, src, C.no_head)
    collar = _t(_stand_collar('GOP_Collar', M['Jacket']), src, C.no_head)
    out = [jacket, collar]
    deco = []
    deco.append(W.front_decal('GOP_Zip', [(-0.0045, 0.752), (0.0045, 0.752), (0.0045, 1.250), (-0.0045, 1.250)], jacket, M['Zip'], 0.003))
    out += _decal_t(deco, jacket)
    czip = W.front_decal('GOP_CollarZip', [(-0.0045, 1.250), (0.0045, 1.250), (0.0045, 1.318), (-0.0045, 1.318)], collar, M['Zip'], 0.0025)
    pull = W.box('GOP_ZipPull', Vector((0.0, -0.160, 1.296)), (0.0065, 0.003, 0.013), M['Zip'])
    out += [C.rigid(czip, 'Spine2'), C.rigid(pull, 'Spine2')]
    pants = _t(W.bottoms('GOP_Pants', GOP_LEGS, [M['Pants'], M['Pants_Rib']], cuff=GOP_CUFF), src)
    stripes = tracksuit_stripes('GOP_Stripe', jacket, pants, M['Stripes'])
    out += [pants] + _decal_t([o for o in stripes if '_Sleeve_' in o.name], jacket) + _decal_t([o for o in stripes if '_Leg_' in o.name], pants)
    out.append(_t(W.plain_socks('GOP_Socks', M['Socks'], top=0.27), src))
    out += pointy_shoes('GOP', M)
    out += W.flat_cap('GOP_Cap', M['Cap'])
    lower = lambda phi: min(W.HAIRLINE(phi), CAP_BASE(phi))
    hair, _ = W.shell('GOP_Hair', M['Hair'], lower, lambda phi: CAP_BASE(phi) + 0.012, off=0.0015, thick=0.0035, seg=32, rows=3)
    out.append(C.rigid(hair, 'Head'))
    # sunflower-seed husks stuck on the lower lip
    for k, (x, z, ang) in enumerate(((0.030, 1.391, 30), (-0.046, 1.380, -40))):
        p = head_pt(x, z, 0.004)
        out.append(C.rigid(G.ellipsoid(f'GOP_Husk_{k}', p, (0.0085, 0.0035, 0.0055), M['Husk'],
                                       rot=Matrix.Rotation(math.radians(ang), 3, 'Y'), seg=8, rings=5), 'Head'))
    out += seed_cone('GOP_Seeds', M)
    return out

# ------------------------------------------------------------------ BAD_DRUNK
DRUNK_LEGS = [(.70, .096), (.60, .093), (.53, .094), (.47, .104), (.42, .100), (.35, .086), (.28, .078), (.21, .070)]
DRUNK_CUFF = [(.196, .056), (.172, .052), (.170, .047)]


def hike_front(ob, lift, z0=0.795, z1=1.02):
    """Ride the hem up at the front (the tank top too short for the belly)."""
    for v in ob.data.vertices:
        p = v.co
        if p.z >= z1:
            continue
        r = math.hypot(p.x, p.y + 0.004)
        front = max(0.0, -(p.y + 0.004) / max(r, 1e-4)) ** 1.6
        t = min(1.0, (z1 - p.z) / (z1 - z0))
        p.z += lift * t * front
    ob.data.update()


def knee_bags(ob, amount=0.020):
    for v in ob.data.vertices:
        p = v.co
        if p.y < 0:
            k = math.exp(-((p.z - 0.455) / 0.060) ** 2)
            p.y -= amount * k * min(1.0, -p.y / 0.06)
    ob.data.update()


def drunk_hair(prefix, M):
    out = [W.hair_ring(prefix + '_Ring', M['Hair'])]
    # messy tufts over the ears and at the back
    for k, (deg, z, out_len, up) in enumerate(((84, 1.560, 0.050, 0.012), (100, 1.548, 0.044, -0.006), (-84, 1.560, 0.050, 0.014),
                                               (-100, 1.546, 0.046, -0.004), (150, 1.560, 0.034, 0.010), (-150, 1.556, 0.034, 0.008))):
        phi = math.radians(deg)
        p, n = W.head_at(phi, W.h_of(z), 0.004)
        tip = p + n * out_len + Vector((0, 0, up))
        out.append(G.tube(f'{prefix}_Tuft_{k}', [p - n * 0.004, p + n * out_len * 0.55 + Vector((0, 0, up * 0.4)), tip],
                          lambda i, m: (0.016, 0.011, 0.002)[i], M['Hair'], seg=8))
    # three lonely hairs standing up on the bald top
    for k, (x, y, bend) in enumerate(((-0.020, -0.012, -1), (0.004, 0.004, 1), (0.026, -0.006, 1))):
        base = Vector((x, y, B.HEAD_TOP - 0.004))
        pts = [base, base + Vector((0, 0, 0.030)), base + Vector((bend * 0.012, -0.004, 0.052)), base + Vector((bend * 0.028, -0.006, 0.058))]
        out.append(G.tube(f'{prefix}_Wisp_{k}', pts, 0.0028, M['Hair'], seg=6))
    return [C.rigid(o, 'Head') for o in out]


def bottle(prefix, M):
    """Green glass bottle held by the neck in the right hand, hanging down past the fingertips."""
    a = Vector((-0.640, -0.014, 1.142))          # lip end, inside the fist
    b = Vector((-1.020, -0.014, 1.142))          # bottom
    prof = [(0.0, 0.0175), (0.025, 0.0185), (0.045, 0.0160), (0.30, 0.0165), (0.36, 0.024), (0.43, 0.036), (0.48, 0.040),
            (0.95, 0.040), (0.985, 0.037), (1.0, 0.030)]
    return [W.prop(axis_loft(prefix + '_Bottle', a, b, prof, M['Bottle'], seg=16), 'RightHand')]


def drunk(body, face, M, skin):
    src = C.weight_source([body])
    parts = W.tank_top('DRUNK_Tank', M['Tank'], body)
    hike_front(parts[0], 0.125)
    out = [_t(o, src, C.no_head) for o in parts]
    tank = parts[0]
    stains = [W.front_decal('DRUNK_Stain_0', W.blob(0.060, 1.010, 0.030, seed=11), tank, M['Stains'], 0.0025),
              W.front_decal('DRUNK_Stain_1', W.blob(-0.075, 0.975, 0.020, seed=12), tank, M['Stains'], 0.0025),
              W.front_decal('DRUNK_Stain_2', W.blob(-0.020, 1.070, 0.016, seed=13), tank, M['Stains'], 0.0025),
              W.front_decal('DRUNK_Stain_3', W.blob(0.090, 0.930, 0.014, seed=14), tank, M['Stains'], 0.0025)]
    out += _decal_t(stains, tank)
    out.append(_t(W.front_decal('DRUNK_Navel', C.ellipse(0.0, 0.902, 0.009, 0.012, 10), body, M['Navel'], 0.0015), src))
    pants = W.bottoms('DRUNK_Pants', DRUNK_LEGS, [M['Pants'], M['Pants_Rib']], cuff=DRUNK_CUFF)
    knee_bags(pants)
    out.append(_t(pants, src))
    out.append(_t(W.plain_socks('DRUNK_Socks', M['Socks'], top=0.22), src))
    slides = W.slides('DRUNK', M['Socks'], M['Slides'])
    out += slides
    # the big toe through a hole in the left sock
    toe = G.ellipsoid('DRUNK_Toe', (B.LEG_X - 0.012, -0.226, 0.052), (0.015, 0.014, 0.013), skin, seg=10, rings=6)
    C.set_weights(toe, [C.shoe_weights(1)(toe.matrix_world @ v.co) for v in toe.data.vertices])
    out.append(toe)
    out += drunk_hair('DRUNK_Hair', M)
    out += T._face(skin, lambda head: W.eye_bags('DRUNK_EyeBag', M['EyeBags'], head) + W.stubble('DRUNK_Stubble', M['Stubble'], head, seed=21))
    out += bottle('DRUNK', M)
    return out

# ------------------------------------------------------------------ BAD_HUSTLER
SHORT_JACKET = [(.800, .206, .142, -.012), (.818, .210, .145, -.012), (.86, .209, .144, -.013), (.94, .208, .142, -.012)] + \
               [r for r in W.JACKET if r[0] >= 1.02]                 # arm row 6


def _turtleneck(name, material, dy=0.0):
    rows = [(1.200, .152, .146), (1.250, .152, .144), (1.282, .156, .148), (1.300, .160, .152), (1.318, .158, .150),
            (1.326, .151, .143), (1.318, .146, .138), (1.250, .146, .138)]
    secs = [((0, dy, z), (1, 0, 0), (0, 1, 0), rx, ry) for z, rx, ry in rows]
    return G.loft(name, secs, material, seg=32, cap_start=False, cap_end=False)


def thin_chain(prefix, material, targets, seg=56, radius=0.0042):
    bvh = G.bvh_of(targets)
    pts = []
    for k in range(seg + 1):
        a = 2 * math.pi * k / seg
        f = ((1 + math.cos(a)) / 2) ** 3
        p = Vector((0.175 * math.sin(a), -0.168 * math.cos(a), 1.266 - 0.175 * f))
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None:
            nrm = nrm if nrm.dot(Vector((p.x, p.y, 0))) >= 0 else -nrm
            p = loc + nrm * 0.008
        pts.append(p)
    return [G.tube(prefix, pts, lambda i, n: radius + 0.0018 * (i % 2), material, seg=6)]


def man_bag(prefix, M):
    """Barsetka: small leather pouch clutched in the left hand, a wrist strap looped round the wrist (the out-of-pool
    TRANSIT_FLIPPER carries it; the v03 hustler wears a cross-body bag instead)."""
    c = Vector((0.780, -0.010, 1.110))
    out = [rbox(prefix + '_Pouch', c, (0.085, 0.050, 0.024), M['Bag'], bevel=0.016)]
    out.append(rbox(prefix + '_Flap', c + Vector((-0.037, 0.0, -0.024)), (0.050, 0.052, 0.003), M['Bag_Strap'], bevel=0.003))
    loop = []
    for k in range(17):
        a = 2 * math.pi * k / 16
        loop.append(Vector((0.618 + 0.006 * math.sin(a), 0.047 * math.cos(a), B.arm_z(0.618) + 0.047 * math.sin(a))))
    strap_pts = [c + Vector((-0.085, -0.010, 0.040)), Vector((0.660, -0.030, 1.150)), Vector((0.624, -0.040, 1.170))]
    out.append(G.tube(prefix + '_Tab', strap_pts, 0.006, M['Bag_Strap'], seg=6))
    ring = G.tube(prefix + '_Loop', loop, 0.0055, M['Bag_Strap'], seg=6)
    return [W.prop(o, 'LeftHand') for o in out] + [W.prop(ring, 'LeftForeArm')]


def crossbody_bag(prefix, M, jacket, src):
    """Small leather bag on a strap from the right shoulder across the chest to the left hip, a gold clasp."""
    import buddy_pool_construction as CN
    raw = [(-0.140, 0.000, 1.222), (-0.110, -0.110, 1.180), (-0.040, -0.170, 1.080), (0.060, -0.180, 0.980), (0.150, -0.150, 0.905),
           (0.205, -0.060, 0.870), (0.210, 0.040, 0.878), (0.160, 0.130, 0.935), (0.060, 0.170, 1.030), (-0.060, 0.160, 1.130),
           (-0.130, 0.090, 1.200)]
    ps, ns = CN.on_surface([jacket], raw, 0.007, step=0.016, smooth=3, closed=True)
    strap = CN.ribbon(prefix + '_Strap', ps, ns, 0.024, [M['Pack_Strap']], lambda i, j: 0, cols=1, thick=0.005, closed=True)
    bvh = G.bvh_of([jacket])
    loc, nrm, _, _ = bvh.find_nearest(Vector((0.175, -0.25, 0.880)))
    nrm = nrm if nrm.y < 0 else -nrm
    flat = Vector((nrm.x, nrm.y, 0.0)).normalized()
    rot = Vector((0.0, -1.0, 0.0)).rotation_difference(flat).to_matrix()
    c = loc + flat * 0.034
    bag = rbox(prefix + '_Pouch', c, (0.072, 0.026, 0.052), M['Pack'], bevel=0.012, rot=rot)
    flap = rbox(prefix + '_Flap', c + rot @ Vector((0.0, -0.024, 0.022)), (0.070, 0.004, 0.028), M['Pack_Strap'], bevel=0.004, rot=rot)
    clasp = rbox(prefix + '_Clasp', c + rot @ Vector((0.0, -0.030, 0.000)), (0.012, 0.003, 0.008), M['Gold'], bevel=0.002, rot=rot)
    return [_t(o, src, lambda p, w: {P + 'Hips': 0.5, P + 'Spine': 0.5}) for o in (bag, flap, clasp)] + [_t(strap, src, C.no_head)]


def hustler(body, face, M, skin):
    """v03 (TASK-000511): Vadim wanted the darker clothes back - the v02 black leather jacket with lapels over a dark
    turtleneck, jeans, black pointy shoes, the thin gold chain, glossy combed-back hair and the thin moustache; new:
    sunglasses pushed up onto the head, a leather cross-body bag and a big gold watch. Nothing in the hands.
    (TASK-000512 tried a 2000s look with gelled spikes and a long leather coat; Vadim kept this one.)"""
    import buddy_pool_bad2 as BD2
    src = C.weight_source([body])
    jacket = W.top('HUSTLER_Jacket', SHORT_JACKET, 6, W.JACKET_SLEEVE, (.818, .198, .134, -.012), [M['Leather'], M['Leather_Rib']],
                   row_mat=[1] + [0] * (len(SHORT_JACKET) - 2), hem_mat=1)
    _t(jacket, src, C.no_head)
    jsrc = C.weight_source([jacket])
    tn = _t(_turtleneck('HUSTLER_Turtleneck', M['Turtleneck']), src)
    collar = W.collar('HUSTLER_Collar', M['Lapel'], z0=1.258, r0=(0.164, 0.159), z1=1.300, r1=(0.172, 0.166), z2=1.236,
                      r2=(0.214, 0.204), open_deg=34, tip=0.040, thick=0.006)
    mm = {'Shirt': M['Turtleneck'], 'Lapel': M['Lapel'], 'Button': M['Button']}
    front = W.suit_front('HUSTLER', jacket, mm, tie_slot=None, v_tip=1.060)
    out = [jacket, tn, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in front]
    out += [C.transfer(o, jsrc) for o in thin_chain('HUSTLER_Chain', M['Gold'], [jacket])]
    out += BD2._big_watch('HUSTLER_Watch', M, x=0.600, side=1)
    out += crossbody_bag('HUSTLER_Bag', M, jacket, jsrc)
    out.append(_t(W.bottoms('HUSTLER_Jeans', W.LEGS_LONG, [M['Jeans']]), src))
    out.append(_t(W.plain_socks('HUSTLER_Socks', M['Socks']), src))
    out += pointy_shoes('HUSTLER', M)
    hair = W.hair('HUSTLER_Hair', M['Hair'], 'slick')
    out.append(hair)
    for k, x in enumerate((-0.060, -0.030, 0.0, 0.030, 0.060)):
        pts = [(x - 0.0022, 0.112), (x + 0.0022, 0.112), (x + 0.0022 + x * 0.25, -0.070), (x - 0.0022 + x * 0.25, -0.070)]
        out.append(C.rigid(G.decal(f'HUSTLER_Comb_{k}', pts, W.TOP(), [hair], 0.0015, M['HairComb'], step=0.010), 'Head'))
    out += W.sunglasses_on_head('HUSTLER_Shades', M['Shades_Frame'], M['Shades_Lens'])
    out += W.mustache('HUSTLER_Mustache', M['Hair'], droop=0.0, size=0.62)
    return out


BUILDERS = {'BAD_GOPNIK': gopnik, 'BAD_DRUNK': drunk, 'BAD_HUSTLER': hustler}
