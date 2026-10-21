"""District pool 'Неблагополучный район', part 3 (TASK-000511): the homeless man (bomzh), the homeless-looking woman (TASK-000535) and the vaper, who moved here from
the old town (Vadim); the alt girl (TASK-000529). Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS (after the old town
module, whose OLD_VAPER spec BAD_VAPER copies). No bpy calls at import time."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Неблагополучный район'

TYPES = {
    'BAD_BOMZH': dict(
        label='Бомж', group=GROUP, hand_props=True, body=dict(thin=0.4), arm_down=70.0, face=dict(Blink=0.35, Happy=0.3, Worried=0.15),
        own_eyes=True,
        look=dict(skin=(226, 156, 124), nose=(196, 84, 100), rim=(186, 100, 100), brow=(150, 140, 128)),
        slots={'Coat': ((104, 92, 74), 0.95), 'Coat_Dark': ((84, 74, 58), 0.95), 'Patch': ((150, 60, 50), 0.95),
               'Patch_2': ((70, 100, 130), 0.95), 'Dirt': ((70, 60, 48), 1.0), 'Rope': ((196, 170, 110), 0.95),
               'Buttons': ((40, 40, 44), 0.5), 'Button_Odd': ((200, 60, 50), 0.4), 'Trousers': ((58, 58, 66), 0.95),
               'Boots': ((76, 56, 40), 0.6), 'Boots_Sole': ((40, 34, 28), 0.7), 'Sock': ((140, 130, 118), 1.0),
               'Hat': ((96, 104, 112), 0.95), 'Hat_Hole': ((40, 36, 32), 1.0), 'Hair': ((150, 140, 128), 0.95),
               'Beard': ((150, 140, 128), 0.95), 'EyeBags': ((156, 112, 134), 0.8), 'Blush': ((216, 100, 100), 0.6),
               'Net': ((96, 84, 66), 0.8), 'Bottle': ((40, 124, 58), 0.12), 'Bottle_2': ((122, 74, 34), 0.12),
               'Bottle_3': ((220, 232, 236), 0.08)},
        colourways=[{'Coat': (70, 72, 78), 'Coat_Dark': (54, 56, 62), 'Hat': (120, 40, 40), 'Trousers': (90, 76, 60)},
                    {'Coat': (110, 104, 60), 'Coat_Dark': (88, 82, 46), 'Hat': (40, 60, 90), 'Patch': (200, 170, 60)}]),
    'BAD_ALTGIRL': dict(
        label='Свити Фокс (альтушка)', group='VIP Элиты', no_ears=True,   # only Elite, not the rough district (TASK-000883)
        body=dict(thin=0.8, bust=4.1, glutes=1.0), preserve_animation_revision=3, face=dict(Happy=0.35),
        look=dict(skin=(250, 226, 214), nose=(246, 198, 186), brow=(40, 30, 30), rim=(40, 30, 34), mouth=(214, 120, 134)),
        eyes=dict(iris=(112, 150, 176), iris_r=0.037, lash=(22, 18, 20), pupil_in=0.0),
        slots={'Jacket': ((22, 22, 26), 0.6), 'Zip': ((96, 96, 104), 0.3, 'metal'), 'Band': ((244, 244, 240), 0.6),
               'Leggings': ((20, 20, 24), 0.55), 'Shoes': ((24, 24, 28), 0.5), 'Shoe_Sole': ((240, 240, 236), 0.6),
               'Shoe_Lace': ((240, 240, 236), 0.7), 'Hair': ((22, 20, 24), 0.68), 'Hair_Dye': ((206, 82, 30), 0.64), 'Freckles': ((206, 140, 112), 0.8), 'Blush': ((244, 172, 170), 0.7),
               'Liner': ((20, 18, 20), 0.5),
               'Eye_Inner': ((65,108,127), .4), 'Eye_Light': ((112,165,177), .4), 'Eye_Outer': ((42,67,79), .42),
               'Tail_Fur': ((206, 82, 30), 0.8), 'Tail_Tip': ((244, 238, 222), 0.85),
               'Ear_Fur': ((181, 85, 36), 0.8), 'Ear_Inner': ((237, 214, 184), 0.85),
               'Ear_Tip': ((24, 20, 24), 0.78), 'Ear_Band': ((22, 20, 24), 0.7), 'Tail_Mount': ((22, 20, 24), 0.75)},
        colourways=[{'Hair_Dye': (200, 40, 60)}, {'Jacket': (52, 54, 60), 'Hair_Dye': (236, 160, 60)}]),
}

TYPES['BAD_BOMZHIHA'] = dict(
    label='Бомжиха', group=GROUP, hand_props=True, own_eyes=True, body=dict(thin=0.2, belly=0.4), arm_down=72.0,
    face=dict(Worried=0.75, Blink=0.45),
    look=dict(skin=(224, 178, 154), nose=(214, 148, 132), brow=(96, 76, 62), rim=(168, 106, 100), mouth=(132, 78, 80)),
    slots={'Hoodie': ((116, 104, 116), 0.95), 'Hoodie_Rib': ((96, 86, 98), 0.95), 'Dirt': ((84, 72, 58), 1.0),
           'Stain': ((150, 132, 92), 1.0), 'Pants': ((58, 66, 72), 0.95), 'Pants_Rib': ((46, 52, 58), 0.95),
           'Shoe_Upper': ((128, 124, 118), 0.85), 'Shoe_Sole': ((70, 66, 60), 0.8), 'Shoe_Lace': ((90, 86, 80), 0.9),
           'Hair': ((128, 106, 78), 0.95), 'Hair_Dirty': ((96, 80, 60), 0.95), 'Hair_Grey': ((168, 164, 156), 0.9),
           'Hair_Tie': ((196, 40, 80), 0.6), 'EyeBags': ((128, 84, 110), 0.8), 'Bruise': ((70, 36, 96), 0.85),
           'Bruise_Edge': ((140, 138, 62), 0.9), 'Lip': ((168, 70, 84), 0.5), 'Frown': ((140, 96, 86), 0.9),
           'Bag': ((240, 238, 230), 0.8), 'Bag_Red': ((196, 40, 50), 0.8), 'Bag_Blue': ((40, 70, 160), 0.8),
           'Bag_Handle': ((36, 36, 40), 0.7), 'Pin': ((214, 172, 116), 0.75), 'Pin_Handle': ((172, 124, 78), 0.7),
           'Pin_Flour': ((240, 236, 226), 0.95)},
    colourways=[{'Hoodie': (80, 92, 76), 'Hoodie_Rib': (66, 76, 62), 'Hair': (110, 72, 52)},
                {'Hoodie': (150, 120, 96), 'Hoodie_Rib': (128, 100, 80), 'Pants': (40, 40, 46), 'Hair': (190, 168, 120)}])

_t = T._t
COAT_LONG = [(.450, .262, .190, -.014), (.470, .262, .190, -.014), (.55, .254, .184, -.014), (.65, .244, .176, -.013),
             (.74, .236, .170, -.013), (.80, .228, .164, -.013), (.86, .220, .156, -.013), (.94, .214, .150, -.012)] + \
            [r for r in W.JACKET if r[0] >= 1.02]               # overcoat to the knees, too big; arm row 10 (z 1.10)


def _coat_weights(p, w):
    """Torso weights above the waist; the long skirt of the coat follows the hips and both thighs like a skirt."""
    w = C.no_head(p, w)
    t = G.smoothstep(0.92, 0.80, p.z)
    if t <= 0.0:
        return w
    u = 0.62 * G.smoothstep(0.84, 0.40, p.z)
    k = G.smoothstep(-0.07, 0.07, p.x)
    return G.mix(w, {P + 'Hips': 1 - u, P + 'LeftUpLeg': u * k, P + 'RightUpLeg': u * (1 - k)}, t)


def hungry_boot(boots, sock_m, s=-1):
    """'The boot asks for porridge': the toe cap of one boot torn off the sole and lifted, the sock showing in the gap."""
    up = next(o for o in boots if o.name.endswith(f'_Shoe_{s}_Upper'))
    cx = s * B.LEG_X
    piv = Vector((cx, -0.140, 0.046))
    R = Matrix.Rotation(math.radians(-20), 3, 'X')
    for v in up.data.vertices:
        if v.co.y < -0.140:
            v.co = piv + R @ (v.co - piv)
    up.data.update()
    sock = G.ellipsoid(f'{up.name}_Sock', (cx - s * 0.004, -0.200, 0.052), (0.028, 0.032, 0.013), sock_m, seg=12, rings=6)
    C.set_weights(sock, [C.shoe_weights(s)(sock.matrix_world @ v.co) for v in sock.data.vertices])
    return [sock]


def bottle_bag(prefix, M, arm_down):
    """String bag (avoska) of empty bottles hanging from the left fist; dropped at the slightest danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    import buddy_pool_bad as BD
    fist, _, _ = HM.grip('Left', arm_down)
    top = fist + Vector((0.0, 0.0, -0.040))
    prof = [(0.0, 0.032), (0.04, 0.034), (0.60, 0.034), (0.70, 0.024), (0.78, 0.015), (0.98, 0.013), (1.0, 0.011)]
    parts = []
    for k, (dx, dy, slot) in enumerate(((0.0, -0.030, 'Bottle'), (0.034, 0.018, 'Bottle_2'), (-0.032, 0.020, 'Bottle_3'))):
        base = top + Vector((dx, dy, -0.300))
        parts.append(BD.axis_loft(f'{prefix}_Bottle_{k}', base, base + Vector((dx * 0.3, dy * 0.3, 0.260)), prof, M[slot], seg=12))
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 0.0))
        parts.append(G.tube(f'{prefix}_String_{k}', [top, top + d * 0.040 + Vector((0, 0, -0.10)), top + d * 0.072 + Vector((0, 0, -0.20)),
                                                     top + d * 0.070 + Vector((0, 0, -0.29)), top + Vector((0, 0, -0.31))], 0.0022, M['Net'], seg=4))
    for k, (z, r) in enumerate(((-0.17, 0.068), (-0.24, 0.073))):
        ring = [top + Vector((r * math.cos(2 * math.pi * q / 20), r * math.sin(2 * math.pi * q / 20), z)) for q in range(21)]
        parts.append(G.tube(f'{prefix}_Ring_{k}', ring, 0.0022, M['Net'], seg=4, caps=False))
    parts.append(G.tube(prefix + '_Handle', [top, fist + Vector((0.0, 0.012, 0.022)), fist + Vector((0.0, -0.012, 0.022)), top], 0.0035,
                        M['Net'], seg=4))
    return HM.hold(parts, 'Left', arm_down)


def bomzh(body, face, M, skin):
    """The homeless man: an old overcoat to the knees, too big, collar up, a rope for a belt, patches, odd buttons and
    dirt; trousers, one boot 'asking for porridge'; a knitted hat with a hole, long grey hair, a big bushy beard, a red
    nose, rosy cheeks and eye bags; a string bag of empty bottles in the left hand."""
    import buddy_pool_transit as TR
    pre = 'BOMZH'
    src = C.weight_source([body])
    coat = W.top(pre + '_Coat', COAT_LONG, 10, W.JACKET_SLEEVE, (.470, .252, .180, -.014), [M['Coat'], M['Coat_Dark']],
                 row_mat=[1] + [0] * (len(COAT_LONG) - 2), sleeve_mat=[0] * 7 + [1] * 3, hem_mat=1)
    _t(coat, src, _coat_weights)
    csrc = C.weight_source([coat])
    collar = W.collar(pre + '_Collar', M['Coat_Dark'], z0=1.258, r0=(0.160, 0.156), z1=1.318, r1=(0.170, 0.165), z2=1.300,
                      r2=(0.186, 0.180), open_deg=18, tip=0.020, thick=0.008)
    deco = [W.front_decal(pre + '_Patch_0', [(0.060, 0.600), (0.140, 0.594), (0.146, 0.676), (0.064, 0.682)], coat, M['Patch'], 0.004,
                          thickness=0.003, step=0.012),
            W.front_decal(pre + '_Patch_1', [(-0.150, 1.020), (-0.090, 1.026), (-0.094, 1.084), (-0.152, 1.078)], coat, M['Patch_2'], 0.004,
                          thickness=0.003, step=0.012),
            G.decal(pre + '_Patch_2', [(-0.120, 0.700), (-0.030, 0.706), (-0.034, 0.790), (-0.118, 0.784)], W.BACK(), [coat], 0.004, M['Patch'],
                    thickness=0.003, step=0.014)]
    deco += [W.front_decal(f'{pre}_Dirt_{k}', W.blob(x, z, r, seed=130 + k, rough=0.55, sx=1.3), coat, M['Dirt'], 0.0028)
             for k, (x, z, r) in enumerate(((-0.090, 0.560, 0.034), (0.120, 0.850, 0.028), (-0.040, 0.980, 0.022), (0.150, 0.500, 0.026)))]
    deco += W.buttons(pre + '_Btn', coat, M['Buttons'], [(0.004, 1.120), (0.0, 0.800)], r=0.012, offset=0.006)
    deco += W.buttons(pre + '_BtnOdd', coat, M['Button_Odd'], [(-0.006, 1.030)], r=0.015, offset=0.006)
    out = [coat, _t(collar, csrc, C.no_head)] + [_t(o, csrc) for o in deco]
    # rope for a belt, knotted on the left with the ends hanging
    rx, ry, dy, z = 0.224, 0.160, -0.013, 0.900
    ring = [Vector((rx * math.sin(2 * math.pi * k / 32), dy - ry * math.cos(2 * math.pi * k / 32), z)) for k in range(33)]
    a = math.radians(35)
    knot_c = Vector((rx * math.sin(a), dy - ry * math.cos(a), z)) + Vector((math.sin(a), -math.cos(a), 0.0)) * 0.010
    rope = [G.tube(pre + '_Rope', ring, 0.0085, M['Rope'], seg=6, caps=False),
            G.ellipsoid(pre + '_RopeKnot', knot_c, (0.020, 0.014, 0.017), M['Rope'], seg=10, rings=6)]
    for k, (dx, ln) in enumerate(((-0.010, 0.120), (0.012, 0.090))):
        p0 = knot_c + Vector((dx, -0.004, -0.010))
        rope.append(G.tube(f'{pre}_RopeEnd_{k}', [p0, p0 + Vector((dx * 0.5, -0.010, -ln * 0.5)), p0 + Vector((dx, -0.006, -ln))], 0.0075,
                           M['Rope'], seg=6))
    out += [_t(o, csrc) for o in rope]
    out.append(_t(W.bottoms(pre + '_Trousers', W.LEGS_LONG, [M['Trousers']]), src))
    boots = W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole'], high=True)
    out += boots + hungry_boot(boots, M['Sock'])
    # head: hat with a hole, long grey hair, beard, face
    hat = W.beanie(pre + '_Hat', M['Hat'])
    hole = G.decal(pre + '_HatHole', W.blob(-0.030, 1.740, 0.018, seed=141, rough=0.5), G.SIDE(1), [hat[0]], 0.0025, M['Hat_Hole'], step=0.008)
    out += hat + [C.rigid(hole, 'Head')]
    hat_base = W.zprofile([(0, 1.668), (90, 1.640), (180, 1.616)])
    lower = lambda phi: W.zprofile([(50, 1.560), (90, 1.440), (130, 1.360), (180, 1.340)])(phi) - 0.012 * abs(2 * ((math.degrees(phi) / 9.0) % 1.0) - 1)
    hair, _ = W.shell(pre + '_Hair', M['Hair'], lower, lambda phi: hat_base(phi) + 0.006, off=lambda phi, u: 0.012 + 0.010 * (1 - u),
                      thick=0.008, seg=32, rows=4, arc=(math.radians(48), math.radians(312)))
    out.append(C.rigid(hair, 'Head'))
    out.append(TR.beard(pre + '_Beard', M['Beard']))
    out += T._face(skin, lambda head: W.eye_bags(pre + '_EyeBag', M['EyeBags'], head) + W.blush(pre + '_Blush', M['Blush'], head))
    out += bottle_bag(pre + '_Bag', M, TYPES['BAD_BOMZH']['arm_down'])
    return out


# ------------------------------------------------------------------ BAD_VAPER (moved from the old town, TASK-000511)
def _vaper_spec():
    """Vadim moved the vaper to this district: OLD_VAPER's slots, colourways and hand props under this district's group."""
    import buddy_pool_oldtown as O
    spec = dict(O.TYPES['OLD_VAPER'])
    spec['group'] = GROUP
    return spec


def bad_vaper(body, face, M, skin):
    import buddy_pool_transit2 as V2
    return V2.transit_vaper(body, face, M, skin)


# ------------------------------------------------------------------ BAD_ALTGIRL (TASK-000529)
def _hair_weights(ob, z_lo=1.28, z_hi=1.38):
    """Long hair: the head carries the top, the chest the lower part, blended over the neck."""
    def w(p):
        t = G.smoothstep(z_lo, z_hi, p.z)
        return {P + 'Head': t, P + 'Spine2': 1.0 - t}
    C.set_weights(ob, [w(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return ob


def _hair_curve(knots, t):
    """Uniform cubic interpolation; every lock keeps a continuous tangent."""
    pts = [Vector(p) for p in knots]
    u = min(1.0, max(0.0, t)) * (len(pts) - 1)
    i = min(int(u), len(pts) - 2)
    q = u - i
    a, b, c, d = (pts[max(0, i-1)], pts[i], pts[i+1], pts[min(len(pts)-1, i+2)])
    return 0.5 * ((2*b) + (-a+c)*q + (2*a-5*b+4*c-d)*q*q + (-a+3*b-3*c+d)*q*q*q)


def _soft_hair_lock(name, knots, material, width, thick, normal=(0, -1, 0), rows=40, root=0.6, tip_material=None, tip_start=.85, scalp=False):
    """Rounded sculpted lock with a continuous taper, rather than a flat panel."""
    def position(t):
        p = _hair_curve(knots, t)
        if scalp and p.z > 1.56:
            phi = math.atan2(p.x, -p.y)
            attached, _ = W.head_at(phi, W.h_of(min(B.HEAD_TOP, p.z - .018)), .023)
            p = p.lerp(attached, G.smoothstep(1.56, 1.65, p.z))
        return p
    sections = []
    for i in range(rows + 1):
        t = i / rows
        p = position(t)
        tangent = (position(min(1, t + 0.002)) - position(max(0, t - 0.002))).normalized()
        n = normal(p) if callable(normal) else Vector(normal)
        u = n.cross(tangent).normalized()
        if u.length < 0.5:
            u = tangent.orthogonal().normalized()
        v = tangent.cross(u).normalized()
        taper = (root + (1-root) * G.smoothstep(0, 0.19, t)) * (1 - 0.98 * G.smoothstep(0.70, 1, t))
        width_at = width * taper * (1 + 0.09 * math.sin(math.pi * t))
        thickness_at = thick * taper * (0.75 + 0.25 * math.sin(math.pi * t))
        sections.append((p, u, v, max(0.00065, width_at), max(0.0005, thickness_at)))
    mat_rows = [int(i / rows >= tip_start) for i in range(rows)] if tip_material else None
    ob = G.loft(name, sections, material, seg=12, mat_rows=mat_rows, extra=(tip_material,) if tip_material else ())
    return _hair_weights(ob, z_lo=1.21, z_hi=1.43)


def fox_hair(prefix, M, targets, skin):
    """v11 layered black/copper alt hair: a continuous crown/back envelope and soft overlapping waves.

    No surface projection onto the collar or shoulder edges: it caused the old
    locks to kink and split. Dense cubic curves and gradual Head/Spine2 weights
    make the transition from scalp to hanging lengths continuous.
    """
    out = []
    # One surface from the crown down the back; there is no horizontal cap seam.
    # The fringe belongs to this same surface; no separate short triangular locks.
    low = W.profile([(0, 1.657), (13, 1.643), (27, 1.650), (38, 1.647), (49, 1.54), (64, 1.07), (90, .995), (180, .940)])
    seg, rows = 100, 46
    vs, fs, grid = [], [], []
    for j in range(seg):
        phi = -math.pi + 2 * math.pi * j / seg
        bottom = low(phi) + (0.017 * math.cos(9 * phi) + 0.008 * math.sin(5 * phi)) * G.smoothstep(45, 75, abs(math.degrees(phi)))
        column = []
        for i in range(rows):
            t = (i + 1) / rows
            z = B.HEAD_TOP + 0.024 - (B.HEAD_TOP + 0.024 - bottom) * t
            crown_z = min(B.HEAD_TOP, z - 0.023)
            p, n = W.head_at(phi, W.h_of(crown_z), 0.022)
            # Loose volume follows an uninterrupted envelope below the skull.
            blend = G.smoothstep(1.61, 1.46, z)
            down = min(1.0, max(0.0, (1.53-z) / 0.63))
            rx = 0.170 + 0.042 * math.sin(math.pi * down * 0.87)
            ry = 0.155 + 0.023 * math.sin(math.pi * down)
            wave = 0.007 * math.sin(2.4*math.pi*down + 0.5*math.sin(phi)) * math.sin(math.pi*down)
            free = Vector(((rx+wave)*math.sin(phi), -(ry+wave)*math.cos(phi), z))
            p = p.lerp(free, blend)
            # Broad flow ridges break the cast-plastic crown without noisy individual hairs.
            ridge = (0.0023 * math.cos(18*phi + 0.7*math.sin(3*t)) + 0.0011 * math.sin(29*phi-2*t)) * math.sin(math.pi*t)**0.6
            p += n * ridge
            column.append(len(vs)); vs.append(p)
        grid.append(column)
    for j in range(seg):
        for i in range(rows-1):
            fs.append((grid[j][i], grid[(j+1)%seg][i], grid[(j+1)%seg][i+1], grid[j][i+1]))
    top = len(vs); vs.append(Vector((0, 0, B.HEAD_TOP + 0.024)))
    for j in range(seg):
        fs.append((top, grid[(j+1)%seg][0], grid[j][0]))
    mantle = G.from_data(prefix + '_ContinuousMass', vs, fs, M['Hair'])
    G.solidify(mantle, 0.009, offset=-1.0)
    out.append(_hair_weights(mantle, z_lo=1.21, z_hi=1.43))

    for s in (-1, 1):
        def points(items):
            return [(s*x, y, z) for x, y, z in items]
        # Copper is an underlayer: several rounded, differently sized waves, not painted flat strips.
        specs = [
            ([(.142,-.080,1.565),(.153,-.098,1.44),(.184,-.105,1.33),(.179,-.184,1.20),(.150,-.206,1.09),(.174,-.193,.966)], .029, .018),
            ([(.155,-.047,1.52),(.174,-.067,1.40),(.198,-.088,1.29),(.217,-.181,1.17),(.190,-.204,1.005)], .024, .014),
        ]
        for k, (path, width, thick) in enumerate(specs):
            out.append(_soft_hair_lock(prefix+f'_CopperFront_{s}_{k}', points(path), M['Hair_Dye'], width, thick))
        dark_specs = [
            ([(.095,-.105,1.722),(.146,-.117,1.606),(.164,-.109,1.49),(.188,-.096,1.37),(.202,-.122,1.265)], .031, .010),
            ([(.116,-.025,1.708),(.166,-.028,1.555),(.183,-.042,1.405),(.218,-.068,1.285),(.223,-.165,1.17),(.188,-.201,1.025)], .035, .013),
            ([(.130,.056,1.69),(.165,.039,1.54),(.194,.014,1.40),(.217,-.011,1.27),(.233,-.066,1.15),(.220,-.130,1.025)], .035, .014),
        ]
        for k, (path, width, thick) in enumerate(dark_specs):
            azimuth = math.atan2(path[0][0], -path[0][1])
            root, _ = W.head_at(azimuth, W.H_POLE - .006, .019)
            upper, _ = W.head_at(azimuth, W.h_of(1.739), .025)
            path = [tuple(root), tuple(upper)] + path
            normal = lambda p: Vector((p.x, p.y, max(0, p.z-1.608))).normalized().lerp(Vector((0,-1,0)), G.smoothstep(1.67,1.46,p.z)).normalized()
            out.append(_soft_hair_lock(prefix+f'_FaceFrame_{s}_{k}', points(path), M['Hair'], width, thick, normal=normal, root=.015,
                                      tip_material=M['Hair_Dye'] if k > 0 else None, tip_start=.86, scalp=True))

    # Broad crown-to-back waves overlap the continuous mass all the way down.
    # Alternating lengths expose the copper underside only at the lower edges.
    for k, deg in enumerate((78, 100, 124, 149, 174, 198, 222, 246, 271, 289)):
        phi = math.radians(deg)
        normal = Vector((math.sin(phi), -math.cos(phi), 0))
        end = .955 + 0.036 * math.sin(k*1.7)
        root, _ = W.head_at(phi, W.H_POLE - .007, .019)
        upper, _ = W.head_at(phi, W.h_of(1.739), .025)
        path = [root, upper]
        for j, z in enumerate((1.719, 1.625, 1.50, 1.36, 1.235, 1.12, end)):
            a = phi + 0.13 * math.sin(j*1.35 + k*0.47) * math.sin(math.pi*j/7)
            if j < 2:
                p, n = W.head_at(a, W.h_of(z), 0.028)
            else:
                down = (1.53-z) / 0.63
                rx = 0.173 + 0.043*math.sin(math.pi*down*.87)
                ry = 0.160 + 0.023*math.sin(math.pi*down)
                p = Vector((rx*math.sin(a), -ry*math.cos(a), z))
            path.append(p)
        # The occasional lower copper lock sits under the outer black sweep.
        if k % 2 == 0 and 95 < deg < 265:
            under = [p-normal*.010 for p in path[4:]]
            under[-1].z -= 0.035
            out.append(_soft_hair_lock(prefix+f'_CopperBack_{k}', under, M['Hair_Dye'], .032, .011, normal=normal))
        out.append(_soft_hair_lock(prefix+f'_BackWave_{k}', path, M['Hair'], .028 + .005*math.sin(k*1.8), .013, normal=normal, root=.015,
                                  tip_material=M['Hair_Dye'] if k in (1, 3, 5, 7, 8) else None, tip_start=.86, scalp=True))
    return out


def refine_altgirl_eyes(face, M):
    """v14 centred forward gaze with the v13 eye refinement, applied identically to all existing expression keys.

    Softer, slightly lifted eye outline; shallow pupils and layered blue-grey
    irises. Mouth, brows, vertex groups, key names and animation data stay intact.
    """
    mesh = face.data
    ids = {}
    for poly in mesh.polygons:
        name = mesh.materials[poly.material_index].name
        if name.startswith(('Buddy_Eye_', 'Buddy_Pupil')):
            ids.setdefault(name, set()).update(poly.vertices)
    keys = mesh.shape_keys.key_blocks
    basis = keys['Basis']
    sides = {i: (1 if basis.data[i].co.x > 0 else -1) for indices in ids.values() for i in indices}
    iris_ring = {}

    for key in keys:
        expr = key.name
        eye_scale = 1.12 if expr == 'Surprised' else 1.0
        pupil_scale = {'Surprised': .72, 'Worried': .88}.get(expr, 1.0)
        for s in (-1, 1):
            blink = expr == 'Blink' or (expr == 'Blink_L' and s > 0) or (expr == 'Blink_R' and s < 0)
            squash = .10 if blink else (.72 if expr == 'Happy' else 1.0)
            rx, ry, rz = (v * eye_scale for v in B.EYE_R)
            rz_eff = rz * squash
            center = Vector((s*B.EYE_C[0], B.EYE_C[1], B.EYE_C[2] - (rz-rz_eff)*(.55 if expr == 'Happy' else 0)))
            yaw = Matrix.Rotation(math.radians(-14*s), 3, 'Z')
            inv = yaw.inverted()
            pupil_dz = .006 if expr == 'Worried' else (0 if expr == 'Surprised' else -.002)
            pc = yaw @ Vector((0, -(ry-.0045), 0)) + Vector((-s*TYPES['BAD_ALTGIRL']['eyes']['pupil_in'], 0, pupil_dz*squash))
            lp = inv @ pc
            # The template eyes yaw 14 degrees towards the nose. Local x=0
            # would therefore still look cross-eyed. Intersect a straight -Y
            # ray through each eye's world-space centre with its final surface.
            # Account for the v13 flattening and lid tilt as well as that yaw.
            warp = yaw @ Matrix(((1.025,0,0), (0,.90,0), (.068*s,0,.88)))
            forward = warp.inverted() @ Vector((0,-1,0))
            distance = 1.0/math.sqrt((forward.x/rx)**2 + (forward.y/ry)**2 + (forward.z/rz_eff)**2)
            target = forward*(distance+.0011)
            for material, indices in ids.items():
                for i in indices:
                    if sides[i] != s:
                        continue
                    p = inv @ (key.data[i].co-center)
                    if material == 'Buddy_Pupil':
                        d = p-lp
                        p = target + Vector((d.x*.79, d.y*.43, d.z*.82))
                    elif material == 'Buddy_Eye_Shine':
                        d = p-lp
                        p = target + Vector((d.x*.79, d.y*.52-.0008, d.z*.82))
                    elif material == 'Buddy_Eye_Iris':
                        dx, dz = p.x-lp.x, (p.z-lp.z)/(1.12*max(squash,.12))
                        radius = math.hypot(dx,dz)
                        ring = min(4, max(0, round(radius/.037*4)))
                        if expr == 'Basis':
                            iris_ring[i] = ring
                        # A narrow outer ring avoids a broad flat blue disc.
                        r = (0, .48, .73, .945, 1)[ring] * .0335
                        if radius > 1e-8:
                            p.x = target.x + dx/radius*r
                            p.z = target.z + dz/radius*r*1.12*max(squash,.12)
                        else:
                            p.x, p.z = target.x, target.z
                        q = (p.x/rx)**2 + (p.z/rz_eff)**2
                        p.y = -ry*math.sqrt(max(.04,1-q))-.00085
                    elif material == 'Buddy_Eye_Rim' and p.z < 0:
                        p.x *= .993
                        p.z *= .989
                    # Shared warp keeps the whites, rims, iris, pupils and lashes aligned.
                    p = Vector((1.025*p.x, .90*p.y, .88*p.z+.068*s*p.x))
                    key.data[i].co = center+yaw@p

    for v in mesh.vertices:
        v.co = basis.data[v.index].co
    shades = {}
    for slot in ('Eye_Inner', 'Eye_Light', 'Eye_Outer'):
        mesh.materials.append(M[slot])
        shades[slot] = len(mesh.materials)-1
    for poly in mesh.polygons:
        if mesh.materials[poly.material_index].name != 'Buddy_Eye_Iris':
            continue
        row = max(iris_ring[i] for i in poly.vertices)
        if row <= 1:
            poly.material_index = shades['Eye_Inner']
        elif row == 2:
            poly.material_index = shades['Eye_Light']
        elif row == 4:
            poly.material_index = shades['Eye_Outer']
    for name, rgb, rough in (('Buddy_Eye_Iris', (94,145,162), .38),
                             ('Buddy_Pupil', (20,24,29), .30),
                             ('Buddy_Eye_White', (245,245,239), .30),
                             ('Buddy_Eye_Shine', (255,255,251), .20)):
        mat = bpy.data.materials[name]
        W.set_color(mat, rgb)
        shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        shader.inputs['Roughness'].default_value = rough
    mesh.update()


def fox_face(prefix, M, head):
    """Her face in the common style: dark eye rims like eyeliner with short winged flicks at the outer corners (the lashes
    and the blue-grey irises are built with the face), a light blush, freckles over the cheeks and the nose."""
    import random
    rnd = random.Random(17)
    out = W.blush(prefix + '_Blush', M['Blush'], head)
    for s in (1, -1):
        cx, cz = s * B.EYE_C[0], B.EYE_C[2]
        wing = [(cx + s * 0.0447, cz + 0.0170), (cx + s * 0.0580, cz + 0.0390), (cx + s * 0.0360, cz + 0.0325)]
        out.append(C.rigid(G.decal(f'{prefix}_Liner_{s}', wing, W.FRONT(), [head], 0.0024, M['Liner'], step=0.004), 'Head'))
        spots = []
        for _ in range(80):
            x, z = s * rnd.uniform(0.052, 0.112), rnd.uniform(1.446, 1.500)
            if ((abs(x) - 0.051) / 0.052) ** 2 + ((z - 1.556) / 0.060) ** 2 > 1.0 and all((x - a) ** 2 + (z - b) ** 2 > 0.010 ** 2 for a, b in spots):
                spots.append((x, z))                      # not under the eye, not touching another freckle
            if len(spots) == 8:
                break
        out += [C.rigid(G.decal(f'{prefix}_Freckle_{s}_{k}', C.ellipse(x, z, 0.0032, 0.0028, 8), W.FRONT(), [head], 0.0018, M['Freckles'],
                                step=0.003), 'Head') for k, (x, z) in enumerate(spots)]
    (nx, ny, nz), (rx, ry, rz) = B.NOSE_C, B.NOSE_R
    for k, (u, w) in enumerate(((-0.40, 0.34), (0.36, 0.38), (-0.10, 0.50), (0.20, 0.16), (-0.32, 0.02))):
        d = Vector((u, -math.sqrt(max(0.0, 1.0 - u * u - w * w)), w))
        c = Vector((nx + rx * d.x, ny + ry * d.y, nz + rz * d.z))
        out.append(C.rigid(G.ellipsoid(f'{prefix}_NoseFreckle_{k}', c, (0.0025, 0.0025, 0.0023), M['Freckles'], seg=6, rings=4), 'Head'))
    return out


def zip_jacket(prefix, M, src):
    """The fitted black zip-up sports jacket of the photo: long tight sleeves, a stand collar zipped almost to the top,
    the zip down the middle with its pull at the upper chest, a white elastic band round the waist."""
    import buddy_pool_oldtown2 as O2
    import buddy_pool_bad as BD
    jacket = _t(W.top(prefix + '_Jacket', W.TEE, 6, W.SLEEVE_LONG, (.806, .184, .124, -.004), [M['Jacket']]), src, C.no_head)
    jsrc = C.weight_source([jacket])
    collar = _t(O2._stand_collar(prefix + '_Collar', M['Jacket'], open_deg=10.0), jsrc, C.no_head)
    zipper = W.front_decal(prefix + '_Zip', BD.stripe_outline(-0.0035, 0.0035, 0.812, 1.246), jacket, M['Zip'], 0.0030, step=0.01)
    hit = G.bvh_of([jacket]).ray_cast(Vector((0.0, -0.6, 1.190)), Vector((0.0, 1.0, 0.0)), 1.0)
    pull = W.box(prefix + '_ZipPull', Vector((0.0, hit[0].y - 0.0055, 1.182)), (0.0070, 0.0022, 0.0150), M['Zip'])
    z = 0.862                                              # waistband: an elastic strap just outside the jacket
    vs = [jacket.matrix_world @ v.co for v in jacket.data.vertices if abs(v.co.z - z) < 0.03 and abs(v.co.x) < 0.30]
    rx = max(abs(p.x) for p in vs) + 0.004
    y0, y1 = min(p.y for p in vs), max(p.y for p in vs)
    ry, dy = (y1 - y0) / 2 + 0.004, (y1 + y0) / 2
    ring = [Vector((rx * math.sin(a), dy - ry * math.cos(a), z)) for a in [2 * math.pi * k / 40 for k in range(41)]]
    band = C.strap(prefix + '_Waistband', ring, M['Band'], width=0.040, thick=0.006,
                   normal_fn=lambda p: Vector((p.x / rx, (p.y - dy) / ry, 0.0)).normalized())
    return jacket, collar, [jacket, collar] + [_t(o, jsrc) for o in (zipper, pull, band)]


def fox_ears(prefix, M):
    """Small padded fox ears on a discreet cosplay headband; existing Head bone only."""
    band_path = [Vector((.163*math.sin(a), .012, 1.608+.173*math.cos(a)))
                 for a in [math.radians(-77+154*i/36) for i in range(37)]]
    out = [C.rigid(G.tube(prefix+'_Headband', band_path, .004, M['Ear_Band'], seg=8), 'Head')]

    def section(s, t):
        center = Vector((s*(.114+.035*t), .009-.006*t, 1.709+.148*t))
        width = .058*(1-t)**.9+.0007
        depth = .022*(1-t)**.7+.0006
        return center, width, depth

    for s in (-1,1):
        sections = []
        for i in range(25):
            t = .992*i/24
            p, width, depth = section(s,t)
            sections.append((p, Vector((1,0,0)), Vector((0,1,0)), width, depth))
        ear = G.loft(prefix+f'_Outer_{s}', sections, M['Ear_Fur'], seg=24,
                     mat_rows=[int(i >= 20) for i in range(24)], extra=(M['Ear_Tip'],))
        out.append(C.rigid(ear,'Head'))
        # Warm cream inset follows the padded front instead of floating in front.
        vs, fs = [], []
        across, rows = 12, 20
        for i in range(rows+1):
            v = i/rows
            t = .14+.70*v
            center, width, depth = section(s,t)
            spread = .67 * max(.04, math.sin(math.pi*v))**.32
            for j in range(across+1):
                u = spread*(-1+2*j/across)
                vs.append(center+Vector((width*u, -depth*math.sqrt(1-u*u)-.0012, 0)))
        for i in range(rows):
            for j in range(across):
                a=i*(across+1)+j
                fs.append((a,a+1,a+across+2,a+across+1))
        inset=G.from_data(prefix+f'_Inset_{s}',vs,fs,M['Ear_Inner'])
        G.solidify(inset,.001,offset=-1)
        out.append(C.rigid(inset,'Head'))
    return out


def fox_tail(prefix, M):
    """v13: a smaller belt-mounted copper cosplay fox-tail accessory, with a cream tip, on the existing pelvis bone.

    The curved, tapered volume is real geometry. Separate materials keep it out
    of the clothing-only pelvis deformation; no new rig bones or actions.
    """
    controls = [Vector(p) for p in ((0.0, 0.160, 0.846), (0.0, 0.290, 0.835),
                                  (0.028, 0.376, 0.610), (0.083, 0.411, 0.544))]

    def frame(t):
        a, b, c, d = controls
        q = 1.0 - t
        center = q**3 * a + 3*q*q*t*b + 3*q*t*t*c + t**3*d
        tangent = (3*q*q*(b-a) + 6*q*t*(c-b) + 3*t*t*(d-c)).normalized()
        u = (Vector((1, 0, 0)) - tangent * tangent.x).normalized()
        return center, u, tangent.cross(u).normalized()

    rings, seg = 29, 24
    vs, fs, indices = [], [], []
    for i in range(rings):
        base_t = i / (rings - 1) * 0.985
        for j in range(seg):
            angle = 2 * math.pi * j / seg
            # A small irregular edge between copper fur and the white tip.
            boundary = math.exp(-((base_t - 0.739) / 0.085)**2)
            t = max(0.0, min(0.999, base_t + boundary * (0.016 * math.cos(5 * angle) + 0.005 * math.sin(3 * angle))))
            center, u, v = frame(t)
            r = 0.017 * (1-t)**2 + 0.067 * math.sin(math.pi*t)**1.08 * (0.7 + 0.3*t)
            fur = 1.0 + 0.035 * math.cos(5*angle + 1.5*t) * math.sin(math.pi*t)
            vs.append(center + r*fur*(u*math.cos(angle) + 0.94*v*math.sin(angle)))
    for i in range(rings - 1):
        for j in range(seg):
            fs.append((i*seg+j, i*seg+(j+1)%seg, (i+1)*seg+(j+1)%seg, (i+1)*seg+j))
            indices.append(1 if i >= 21 else 0)
    for row, center, material in ((0, controls[0], 0), (rings-1, controls[-1], 1)):
        end = len(vs)
        vs.append(center)
        for j in range(seg):
            fs.append((row*seg+j, row*seg+(j+1)%seg, end))
            indices.append(material)
    tail = G.from_data(prefix, vs, fs, M['Tail_Fur'], mat_index=indices, extra=(M['Tail_Tip'],))
    mount = W.box(prefix+'_BeltClip', Vector((0,.162,.855)), (.018,.011,.022), M['Tail_Mount'])
    G.join(tail,[mount])
    return C.rigid(tail, 'Hips')


def altgirl(body, face, M, skin):
    """The fictional alt girl keeps the established v03 look (TASK-000529; the game data calls her only
    'Альтушка'): her hairstyle - a full fringe, long layered black hair with copper underneath showing at the sides of
    the face and under the back lengths; pale skin, dark brows, prettier eyes than the BASE (blue-grey irises, lashes,
    dark rims with winged liner flicks), freckles, a light blush, a pink smile; her outfit from the second photo:
    a fitted black zip-up sports jacket with a stand collar, a white waistband, black leggings, black sneakers on
    white soles. This is the fictional game NPC 'Альтушка': v04 changes only the clothed bust and glute volumes
    through W.reshape; the closed outfit, hairstyle, face and remaining proportions stay as in v03."""
    pre = 'ALTGIRL'
    refine_altgirl_eyes(face, M)
    src = C.weight_source([body])
    jacket, collar, out = zip_jacket(pre, M, src)
    out.append(_t(W.bottoms(pre + '_Leggings', W.LEGS_TIGHTS, [M['Leggings']]), src))
    out += W.shoes(pre + '_Shoe', M['Shoes'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += fox_hair(pre + '_Hair', M, [jacket, collar], skin)
    out += T._face(skin, lambda head: fox_face(pre + '_Face', M, head))
    out += fox_ears(pre + '_FoxEars', M)
    out.append(fox_tail(pre + '_FoxTail', M))
    return out

# ------------------------------------------------------------------ BAD_BOMZHIHA (TASK-000535)
def plaid_box(name, c, half, mats, cell=0.03):
    """Box whose six faces carry a woven plaid (white ground, red and blue stripes), wound to face outward."""
    hx, hy, hz = half
    vs, fs, idx = [], [], []

    def face(o, u, v):
        nu = max(2, int(round(u.length / cell)))
        nv = max(2, int(round(v.length / cell)))
        base = len(vs)
        for j in range(nv + 1):
            for i in range(nu + 1):
                vs.append(c + o + u * (i / nu) + v * (j / nv))
        for j in range(nv):
            for i in range(nu):
                a = base + j * (nu + 1) + i
                fs.append((a, a + 1, a + nu + 2, a + nu + 1))
                idx.append(1 if i % 4 == 1 else 2 if i % 4 == 3 else 1 if j % 4 == 1 else 2 if j % 4 == 3 else 0)
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    face(Vector((hx, -hy, -hz)), Y * 2 * hy, Z * 2 * hz)
    face(Vector((-hx, hy, -hz)), -Y * 2 * hy, Z * 2 * hz)
    face(Vector((hx, hy, -hz)), -X * 2 * hx, Z * 2 * hz)
    face(Vector((-hx, -hy, -hz)), X * 2 * hx, Z * 2 * hz)
    face(Vector((-hx, -hy, hz)), X * 2 * hx, Y * 2 * hy)
    face(Vector((-hx, hy, -hz)), X * 2 * hx, -Y * 2 * hy)
    return G.from_data(name, vs, fs, mats[0], False, idx, list(mats[1:]), fix_normals=False)


def market_bag(prefix, M, arm_down):
    """The big checked 'shuttle trader' bag (red and blue stripes on white) hanging from the left fist by its two
    handles, long side front to back so it clears the leg; dropped at the slightest danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    fist, _, _ = HM.grip('Left', arm_down)
    half = (0.075, 0.170, 0.140)
    c = fist + Vector((0.020, 0.0, -0.090 - half[2]))
    body = plaid_box(prefix + '_Body', c, half, [M['Bag'], M['Bag_Red'], M['Bag_Blue']])
    top = c.z + half[2]
    parts = [body, G.tube(prefix + '_Zip', [c + Vector((0.0, -half[1] + 0.012, half[2] + 0.002)), c + Vector((0.0, half[1] - 0.012, half[2] + 0.002))],
                          0.0040, M['Bag_Handle'], seg=6)]
    for s in (1, -1):
        a = Vector((c.x + s * 0.050, c.y - 0.070, top))
        b = Vector((c.x + s * 0.050, c.y + 0.070, top))
        parts.append(G.tube(f'{prefix}_Handle_{s}', [a, a.lerp(fist, 0.6) + Vector((0, -0.010, 0.0)), fist + Vector((s * 0.006, 0.0, -0.006)),
                                                     b.lerp(fist, 0.6) + Vector((0, 0.010, 0.0)), b], 0.0060, M['Bag_Handle'], seg=6))
    return HM.hold(parts, 'Left', arm_down)


def rolling_pin(prefix, M, arm_down, tilt_deg=28.0):
    """v02 (TASK-000539, Vadim: give her a rolling pin): a wooden rolling pin gripped by one handle in the right fist,
    the barrel pointing forward and down, ready to swing; a smear of flour on the barrel. Dropped at the slightest
    danger like the bag (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    fist, _, thumb = HM.grip('Right', arm_down)
    fwd = Vector((thumb.x, thumb.y, 0.0)).normalized()
    t = math.radians(tilt_deg)
    d = (fwd * math.cos(t) + Vector((0.0, 0.0, -math.sin(t)))).normalized()
    at = lambda s: fist + d * s
    parts = [G.tube(prefix + '_HandleA', [at(-0.052), at(-0.046), at(0.040), at(0.056)],
                    lambda i, n: (0.0105, 0.0150, 0.0130, 0.0100)[i], M['Pin_Handle'], seg=10),
             G.ellipsoid(prefix + '_KnobA', at(-0.056), (0.016, 0.016, 0.016), M['Pin_Handle'], seg=10, rings=6),
             G.tube(prefix + '_Barrel', [at(0.056), at(0.064), at(0.072), at(0.310), at(0.318), at(0.326)],
                    lambda i, n: (0.0230, 0.0330, 0.0360, 0.0360, 0.0330, 0.0230)[i], M['Pin'], seg=14),
             G.tube(prefix + '_HandleB', [at(0.326), at(0.342), at(0.400), at(0.408)],
                    lambda i, n: (0.0100, 0.0130, 0.0150, 0.0105)[i], M['Pin_Handle'], seg=10),
             G.ellipsoid(prefix + '_KnobB', at(0.412), (0.016, 0.016, 0.016), M['Pin_Handle'], seg=10, rings=6)]
    # a smear of flour: a thin white band wrapped round part of the barrel, a bit thicker than the wood
    side = d.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = side.cross(d).normalized()
    arc = [at(0.150 + 0.050 * k / 6) + (up * math.cos(a) + side * math.sin(a)) * 0.0366
           for k, a in enumerate(math.radians(x) for x in (-70, -45, -20, 5, 30, 55, 80))]
    parts.append(G.tube(prefix + '_Flour', arc, 0.0040, M['Pin_Flour'], seg=6))
    return HM.hold(parts, 'Right', arm_down)


def bun_hair(prefix, M):
    """Greasy hair pulled back into a messy bun on the crown: the combed-back helmet with grey streaks, the lumpy bun with
    a pink tie, a few loose strands by the temples and on the neck."""
    hair = W.hair(prefix + '_Base', M['Hair'], 'slick')
    out = [hair]
    for k, (x, a, slot) in enumerate(((-0.090, 0.3, 'Hair_Dirty'), (-0.055, 0.0, 'Hair_Grey'), (-0.020, 0.8, 'Hair_Dirty'),
                                      (0.012, 0.6, 'Hair_Grey'), (0.046, -0.4, 'Hair_Dirty'), (0.080, 0.2, 'Hair_Grey'))):
        pts = []
        for i in range(9):
            t = i / 8
            b = math.radians(78 + 84 * t)
            kx = math.sqrt(max(0.05, 1.0 - (x / B.HEAD_R) ** 2))
            pts.append(Vector((x + 0.004 * math.sin(6 * t + a), -B.HEAD_RY * kx * math.cos(b) * 1.09, B.HEAD_CYL_TOP + B.HEAD_R * kx * math.sin(b) * 1.09)))
        out.append(C.rigid(G.tube(f'{prefix}_Streak_{k}', pts, 0.0058, M[slot], seg=5), 'Head'))
    c = Vector((0.004, 0.030, 1.792))
    out.append(C.rigid(G.ellipsoid(prefix + '_Bun', c, (0.050, 0.045, 0.040), M['Hair'], seg=16, rings=10), 'Head'))
    for k, (dx, dy, dz, r) in enumerate(((0.032, -0.010, 0.020, 0.020), (-0.030, 0.012, 0.018, 0.018), (0.008, 0.030, 0.030, 0.016))):
        out.append(C.rigid(G.ellipsoid(f'{prefix}_BunLump_{k}', c + Vector((dx, dy, dz)), (r, r * 0.9, r * 0.8), M['Hair'], seg=10, rings=6), 'Head'))
    tie = [c + Vector((0.044 * math.cos(2 * math.pi * q / 16), 0.040 * math.sin(2 * math.pi * q / 16) - 0.004, -0.026)) for q in range(17)]
    out.append(C.rigid(G.tube(prefix + '_Tie', tie, 0.0065, M['Hair_Tie'], seg=6, caps=False), 'Head'))
    for k, (x0, y0, z0, dz) in enumerate(((0.136, -0.050, 1.640, 0.140), (-0.136, -0.040, 1.630, 0.120), (0.092, 0.112, 1.560, 0.110))):
        s = 1 if x0 > 0 else -1
        pts = [Vector((x0, y0, z0)), Vector((x0 + s * 0.010, y0 - 0.008, z0 - dz * 0.4)), Vector((x0 + s * 0.004, y0 - 0.012, z0 - dz * 0.75)),
               Vector((x0 + s * 0.012, y0 - 0.010, z0 - dz))]
        out.append(C.rigid(G.tube(f'{prefix}_Strand_{k}', pts, lambda i, n: 0.0042 - 0.0008 * i, M['Hair'], seg=5), 'Head'))
    return out


def bomzhiha(body, face, M, skin):
    """BAD_BOMZHIHA (TASK-000535, Vadim): a middle-aged woman who looks like a homeless one, unhappy with life and it
    shows - a baggy dirty hoodie (hood down) with stains, old sweatpants with dirty knees, worn grey sneakers; greasy
    hair pulled into a messy bun with grey streaks and loose strands; a scary face: tired half-shut eyes and dark eye
    bags, a dark bruise under the left eye, frown lines, the lower lip swollen much bigger than the thin upper one,
    the mouth turned down; a checked market bag in the left hand (dropped at the slightest danger)."""
    import buddy_pool_transit2 as TR2
    pre = 'BOMZHIHA'
    src = C.weight_source([body])
    hoodie = W.top(pre + '_Hoodie', TR2.HOODIE_BIG, 7, TR2.HOODIE_BIG_SLEEVE, (.716, .186, .128, -.010), [M['Hoodie'], M['Hoodie_Rib']],
                   row_mat=[1] + [0] * (len(TR2.HOODIE_BIG) - 2), sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(hoodie, src, C.no_head)
    hsrc = C.weight_source([hoodie])
    out = [hoodie, T._hood_down(pre, M['Hoodie'])]
    deco = [G.decal(pre + '_Pocket', [(-0.150, 0.765), (0.150, 0.765), (0.120, 0.950), (-0.120, 0.950)], W.FRONT(), [hoodie], 0.004,
                    M['Hoodie'], thickness=0.010, step=0.012)]
    deco += [W.front_decal(f'{pre}_Dirt_{k}', W.blob(x, z, r, seed=210 + k, rough=0.55, sx=1.3), hoodie, M['Dirt'], 0.0030)
             for k, (x, z, r) in enumerate(((-0.110, 1.040, 0.026), (0.140, 0.880, 0.022), (0.030, 1.150, 0.016)))]
    deco.append(W.front_decal(pre + '_Stain', W.blob(-0.060, 0.900, 0.036, seed=233, rough=0.6, sx=1.4), hoodie, M['Stain'], 0.0034))
    deco.append(G.decal(pre + '_DirtBack', W.blob(0.060, 1.000, 0.030, seed=241, rough=0.55), W.BACK(), [hoodie], 0.003, M['Dirt'], step=0.012))
    out += [_t(o, hsrc) for o in deco]
    pants = _t(W.bottoms(pre + '_Pants', W.LEGS_SWEAT, [M['Pants'], M['Pants_Rib']], cuff=W.SWEAT_CUFF), src)
    knees = [W.front_decal(f'{pre}_Knee_{s}', W.blob(s * 0.100, 0.440, 0.030, seed=250 + (s > 0), rough=0.5), pants, M['Dirt'], 0.003)
             for s in (1, -1)]
    out += [pants] + T._decal_t(knees, pants)
    out += W.shoes(pre + '_Shoe', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += bun_hair(pre + '_Hair', M)
    # the swollen lower lip under the thin upper one, a little to one side
    lip_c = Vector((0.008, B.head_surface_y(0.008, 1.391, 0.004), 1.391))
    lip = G.ellipsoid(pre + '_Lip', lip_c, (0.031, 0.012, 0.013), M['Lip'], rot=Matrix.Rotation(math.radians(8), 3, 'Y'), seg=14, rings=8)
    out.append(C.rigid(lip, 'Head'))

    def face_paint(head):
        res = W.eye_bags(pre + '_EyeBag', M['EyeBags'], head)
        res.append(C.rigid(G.decal(pre + '_BruiseEdge', C.ellipse(0.090, 1.466, 0.040, 0.028, 20), W.FRONT(), [head], 0.0018, M['Bruise_Edge'],
                                   step=0.006), 'Head'))
        res.append(C.rigid(G.decal(pre + '_Bruise', W.blob(0.090, 1.468, 0.030, seed=261, rough=0.35, sx=1.35), W.FRONT(), [head], 0.0024,
                                   M['Bruise'], step=0.005), 'Head'))
        for k, x in enumerate((-0.012, 0.010)):
            res.append(C.rigid(G.decal(f'{pre}_Frown_{k}', [(x - 0.0018, 1.612), (x + 0.0018, 1.612), (x + 0.0030, 1.644), (x - 0.0006, 1.644)],
                                       W.FRONT(), [head], 0.0016, M['Frown'], step=0.004), 'Head'))
        return res
    out += T._face(skin, face_paint)
    # v02 (TASK-000539, Vadim): the checked market bag is gone, the rolling pin is her only hand prop
    out += rolling_pin(pre + '_Pin', M, TYPES['BAD_BOMZHIHA']['arm_down'])     # v02 (TASK-000539)
    return out


TYPES['BAD_VAPER'] = _vaper_spec()
BUILDERS = {'BAD_BOMZH': bomzh, 'BAD_VAPER': bad_vaper, 'BAD_ALTGIRL': altgirl, 'BAD_BOMZHIHA': bomzhiha}
