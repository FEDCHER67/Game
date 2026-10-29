"""MECHANIC_W86: the workshop mechanic (Fedya 2026-10-29, reference variant B:
Working/Reviews/Mechanic_2026-10-29/mechanic_reference_B_chosen.webp).

A Sausage Buddy NPC type in the buddy_types format (TYPES / BUILDERS entry). build_mechanic_w86.py registers it into
buddy_types at run time; nothing in SAUSAGE_BUDDY_01 is modified. Base build: TRANSIT_TRUCKER (pot belly, open shirt
with rolled sleeves over a top, moustache, stubble), here:
- slightly pot-bellied (real geometry: buddy_wear.reshape belly, body and every garment displaced together);
- olive work jacket (#646C50) worn open, short sleeves rolled above the elbow, two chest pockets with flaps, dark oil
  stains front and back, fold-down collar;
- grey tee (#A3A8AB) tucked in;
- dark grey cargo trousers (#373631) with turned-up cuffs, side cargo pockets with flaps, back pockets, oil stains;
- brown belt (#75604D) with a steel buckle, a leather tool pouch on the right hip with a pair of yellow work gloves
  tucked in and hanging out, a small pouch on the left back hip, a grey rag hanging from the left back pocket;
- dark work boots (high, laced);
- red bandana (#B23A2C) round the head above the brows, knotted at the back with two tails;
- bald top, grey hair on the sides and back under the bandana, big dark-grey moustache, stubble;
- skin #D59A72, round red-orange nose, dark-grey brows; the Sausage Buddy eyes (big round);
- the wrench: a double open-ended spanner rigid on the RightHand bone, exported as its own mesh 'Wrench_RightHand'
  (NOT 'Props_RightHand': the game's NpcHeldProps drops every Props_*Hand mesh at the first danger; the mechanic never
  lets go of his wrench). It sits in the fist of the Grip_R finger pose (mechanic_w86_anim.GRIP_R).
Z up, -Y forward, left = +X, metres (as the whole Sausage Buddy pipeline)."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T
import buddy_pool_transit as TR
import buddy_pool_bad as BD

P = 'mixamorig:'
TID = 'MECHANIC_W86'
METAL = 'metal'


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


TYPE = dict(
    label='Механик мастерской (W86)', group='W86 мастерская', hand_props=True, body=dict(belly=1.25), arm_down=62.0,
    look=dict(skin=hexrgb('#D59A72'), nose=(222, 100, 66), brow=(74, 72, 72), rim=(178, 112, 80)),
    slots={'Jacket': (hexrgb('#646C50'), 0.92), 'Jacket_Roll': ((88, 95, 70), 0.92), 'Jacket_Dark': ((80, 87, 63), 0.92),
           'Jacket_Oil': ((62, 66, 50), 0.6),
           'Tee': (hexrgb('#A3A8AB'), 0.9),
           'Trousers': (hexrgb('#373631'), 0.92), 'Trousers_Cuff': ((48, 47, 43), 0.92), 'Trousers_Pocket': ((46, 45, 41), 0.92),
           'Oil': ((28, 27, 25), 0.45),
           'Belt': (hexrgb('#75604D'), 0.6), 'Buckle': ((150, 152, 156), 0.32, METAL), 'Pouch': ((104, 84, 66), 0.62),
           'Gloves': ((222, 168, 48), 0.85), 'Gloves_Cuff': ((196, 142, 36), 0.85),
           'Rag': ((168, 168, 164), 0.95),
           'Boots': ((58, 52, 47), 0.5), 'Boots_Sole': ((30, 28, 27), 0.7), 'Boot_Lace': ((40, 37, 34), 0.7),
           'Bandana': (hexrgb('#B23A2C'), 0.85),
           'Hair': ((126, 128, 130), 0.95), 'Mustache': ((84, 84, 86), 0.9), 'Stubble': ((124, 88, 70), 0.95),
           'Wrench': ((150, 154, 160), 0.36, METAL)},
    colourways=[{'Jacket': (52, 66, 98), 'Jacket_Roll': (44, 56, 84), 'Jacket_Dark': (44, 56, 84), 'Jacket_Oil': (34, 40, 54),
                 'Bandana': (40, 70, 150), 'Trousers': (44, 46, 52)},
                {'Jacket': (122, 94, 64), 'Jacket_Roll': (106, 80, 54), 'Jacket_Dark': (106, 80, 54), 'Jacket_Oil': (76, 58, 40),
                 'Bandana': (214, 162, 40), 'Trousers': (60, 66, 56)}])

# ------------------------------------------------------------------ profiles
# jacket: worn open over the tucked tee, hem just above the belt, a size bigger than the tee (outer layer); arm row 5
JACKET_ROWS = [(.896, .206, .142, -.012), (.906, .208, .144, -.012), (.95, .207, .143, -.012), (1.02, .206, .143, -.008),
               (1.08, .210, .149, -.002), (1.10, .212, .153, 0.0), (1.17, .210, .159, .002), (1.235, .198, .163, .002),
               (1.248, .173, .167, .002), (1.257, .165, .163, 0.0), (1.259, .160, .157, 0.0), (1.250, .157, .153, 0.0)]
JACKET_ARM_ROW = 5
JACKET_HEM = (.908, .198, .136, -.010)
# rolled short sleeve, ends above the elbow (the shepherd's / trucker's roll, a bit roomier for a work jacket)
JACKET_SLEEVE = [(.212, .080), (.25, .075), (.30, .070), (.36, .066), (.41, .063), (.438, .062), (.445, .069), (.463, .071),
                 (.479, .069), (.483, .058)]
LEGS = [(.70, .096), (.60, .094), (.50, .091), (.43, .088), (.34, .086), (.26, .086), (.20, .087), (.178, .088)]
CUFF = [(.166, .097), (.214, .098), (.219, .091)]       # turned-up hem over the boots
TEE_SLEEVE = [(.212, .064), (.24, .060), (.27, .057), (.285, .055), (.288, .051)]   # short, stays inside the jacket sleeve


def jacket_gap(z):
    """Half width of the open front at height z (open all the way down, wider at the collar)."""
    return 0.060 + 0.050 * G.smoothstep(1.00, 1.25, z)


def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _decal_t(pieces, garment):
    return T._decal_t(pieces, garment)

# ------------------------------------------------------------------ head
BAND_LO = W.zprofile([(0, 1.684), (90, 1.660), (180, 1.626)])
BAND_HI = W.zprofile([(0, 1.724), (90, 1.702), (180, 1.668)])


def bandana(prefix, M):
    """Red bandana tied round the head above the brows (the brows move under its lower edge when raised), knotted
    at the back with two short tails flaring out and down."""
    band, _ = W.shell(prefix, M['Bandana'], BAND_LO, BAND_HI,
                      off=lambda phi, u: 0.010 + 0.004 * math.sin(math.pi * u), thick=0.007, seg=32, rows=3)
    out = [band]
    kp, kn = W.head_at(math.pi, (BAND_LO(math.pi) + BAND_HI(math.pi)) / 2, 0.022)
    out.append(G.ellipsoid(prefix + '_Knot', kp, (0.026, 0.017, 0.021), M['Bandana'], seg=12, rings=6))
    for s in (1, -1):
        d = Vector((s * 0.62, 0.22, -0.75)).normalized()             # down and outwards, a little away from the neck
        side = Vector((0, 1, 0)).cross(d).normalized()
        nrm = d.cross(side).normalized()
        c = kp + d * 0.044 + Vector((0, 0.004, 0))
        rot = Matrix((side, d, nrm)).transposed()
        out.append(G.ellipsoid(f'{prefix}_Tail_{s}', c, (0.019, 0.042, 0.0045), M['Bandana'], rot=rot, seg=10, rings=6))
    return [C.rigid(o, 'Head') for o in out]


def side_hair(prefix, M):
    """Receding grey hair: sides and back under the bandana, bald on top, a slightly ragged lower edge over the ears."""
    base = W.zprofile([(62, 1.585), (78, 1.552), (96, 1.530), (130, 1.505), (180, 1.494)])
    lo = lambda phi: base(phi) + 0.006 * abs(2 * ((math.degrees(phi) / 8.0) % 1.0) - 1)
    hi = lambda phi: BAND_LO(phi) + 0.010                           # tucked under the band
    ob, _ = W.shell(prefix, M['Hair'], lo, hi, off=lambda phi, u: 0.004 + 0.007 * math.sin(math.pi * min(1.0, u * 1.4)),
                    thick=0.008, seg=32, rows=3, arc=(math.radians(62), math.radians(298)))
    return [C.rigid(ob, 'Head')]

# ------------------------------------------------------------------ belt gear
def gloves(prefix, M, anchor):
    """A pair of yellow work gloves tucked into the pouch top: cuffs inside, palms and fingers hanging out in front."""
    out = []
    for k, (dx, dy, tilt) in enumerate(((0.000, 0.0, 6.0), (0.020, 0.010, -10.0))):
        rot = Matrix.Rotation(math.radians(tilt), 3, 'Y') @ Matrix.Rotation(math.radians(-24 + 4 * k), 3, 'Z')
        top = anchor + Vector((dx, dy, 0.0))
        def at(x, y, z):
            return top + rot @ Vector((x, y, z))
        out.append(G.ellipsoid(f'{prefix}_Cuff_{k}', at(0, 0, -0.004), (0.032, 0.011, 0.020), M['Gloves_Cuff'], rot=rot, seg=10, rings=5))
        out.append(G.ellipsoid(f'{prefix}_Palm_{k}', at(0, -0.002, -0.044), (0.031, 0.010, 0.036), M['Gloves'], rot=rot, seg=10, rings=6))
        for j, (fx, ln) in enumerate(((-0.019, 0.044), (-0.006, 0.050), (0.007, 0.048), (0.019, 0.040))):
            a = at(fx, -0.002, -0.070)
            b = at(fx * 1.25, -0.006 - 0.004 * j, -0.070 - ln)
            out.append(G.tube(f'{prefix}_Finger_{k}_{j}', [a, a.lerp(b, 0.55) + Vector((0, -0.004, 0)), b],
                              lambda i, n: (0.0078, 0.0075, 0.0065)[i], M['Gloves'], seg=6))
        tb = at(-0.032, -0.004, -0.030)
        out.append(G.tube(f'{prefix}_Thumb_{k}', [tb, tb + rot @ Vector((-0.016, -0.004, -0.030))], lambda i, n: (0.009, 0.007)[i],
                          M['Gloves'], seg=8))
    return out


def belt_gear(prefix, M):
    """Brown belt with a rectangular steel buckle, a leather tool pouch on the right hip (gloves hanging out of it) and
    a small pouch on the left back hip; the pouches and gloves are rigid on the hips like the builders' tool belt."""
    out = W.belt(prefix, M['Belt'], M['Buckle'], z=0.874, rx=0.197, ry=0.137, dy=-0.004, width=0.040)
    bk = out.pop()                                                   # bigger buckle: frame + bar
    bpy.data.objects.remove(bk)
    by = -0.004 - 0.137 - 0.010
    out.append(BD.rbox(prefix + '_Buckle', Vector((0.0, by, 0.874)), (0.030, 0.0045, 0.025), M['Buckle'], bevel=0.004))
    out.append(BD.rbox(prefix + '_BuckleBar', Vector((0.0, by - 0.005, 0.874)), (0.004, 0.003, 0.020), M['Belt'], bevel=0.002))
    gear = []
    rot = Matrix.Rotation(math.radians(30), 3, 'Z')
    pc = Vector((-0.226, -0.072, 0.812))
    gear.append(BD.rbox(prefix + '_Pouch', pc, (0.022, 0.058, 0.064), M['Pouch'], bevel=0.012, rot=rot))
    gear.append(BD.rbox(prefix + '_PouchFlap', pc + rot @ Vector((-0.012, 0.0, 0.050)), (0.016, 0.060, 0.022), M['Pouch'], bevel=0.008, rot=rot))
    gear.append(BD.rbox(prefix + '_PouchStrap', pc + rot @ Vector((-0.020, 0.0, 0.020)), (0.004, 0.016, 0.040), M['Belt'], bevel=0.002, rot=rot))
    gear += gloves(prefix + '_Glove', M, pc + rot @ Vector((-0.030, -0.006, 0.060)))
    rot2 = Matrix.Rotation(math.radians(-150), 3, 'Z')
    pc2 = Vector((0.196, 0.112, 0.826))
    gear.append(BD.rbox(prefix + '_PouchB', pc2, (0.018, 0.040, 0.046), M['Pouch'], bevel=0.010, rot=rot2))
    gear.append(BD.rbox(prefix + '_PouchBFlap', pc2 + rot2 @ Vector((0.010, 0.0, 0.036)), (0.012, 0.042, 0.016), M['Pouch'], bevel=0.006,
                        rot=rot2))
    return out, [C.rigid(o, 'Hips') for o in gear]


def rag(prefix, M, trousers):
    """Grey rag stuffed in the left back pocket, hanging down over the back of the thigh in two loose folds; weights
    from the trousers so it follows the hip and thigh."""
    bvh = G.bvh_of([trousers])
    cols, rows = 7, 9
    vs, fs = [], []
    for i in range(rows):
        t = i / (rows - 1)
        z = 0.838 - 0.205 * t
        w = 0.074 - 0.020 * t
        for j in range(cols):
            u = j / (cols - 1) - 0.5
            x = 0.098 + u * w + 0.010 * t
            y0 = 0.30
            hit = bvh.ray_cast(Vector((x, y0, z)), Vector((0, -1, 0)), 0.5)
            ys = hit[0].y if hit[0] is not None else 0.16
            fold = 0.006 * math.sin(2 * math.pi * (u * 1.6 + 0.3 * t)) * (0.3 + t)
            vs.append(Vector((x, ys + 0.008 + 0.010 * t * t + fold, z)))
    for i in range(rows - 1):
        for j in range(cols - 1):
            a = i * cols + j
            fs.append((a, a + 1, a + cols + 1, a + cols))
    ob = G.from_data(prefix, vs, fs, M['Rag'], True)
    G.solidify(ob, 0.004, offset=0.0)
    return ob

# ------------------------------------------------------------------ the wrench (rigid on RightHand)
def _jaw_outline(c, a, w, R, hw, open_deg, n_arc=22):
    """2D-in-3D outline of an open spanner end: a disc of radius R round c with a parallel slot of half width hw
    opening along a turned by open_deg; returns points (counter-clockwise in the a/w plane)."""
    d = (a * math.cos(math.radians(open_deg)) + w * math.sin(math.radians(open_deg))).normalized()
    e = (w * math.cos(math.radians(open_deg)) - a * math.sin(math.radians(open_deg))).normalized()
    t = math.sqrt(R * R - hw * hw)
    ang = lambda p: math.atan2((p - c).dot(e), (p - c).dot(d))
    p1 = c + d * t + e * hw
    p2 = c + d * t - e * hw
    a1, a2 = ang(p1), ang(p2) + 2 * math.pi
    pts = []
    for k in range(n_arc + 1):
        th = a1 + (a2 - a1) * k / n_arc
        pts.append(c + (d * math.cos(th) + e * math.sin(th)) * R)
    # the slot: in along the lower jaw, round the bottom, out along the upper jaw
    bottom = c - d * 0.002
    pts.append(bottom - e * hw + d * 0.0)
    for k in range(1, 6):
        th = -math.pi / 2 - math.pi * k / 6
        pts.append(bottom + (d * math.cos(th) * 0.9 + e * math.sin(th)) * hw)
    pts.append(bottom + e * hw)
    return pts


def _slab(name, pts, nrm, half, material):
    """Extrude a planar outline by +-half along nrm; ngons ear-clipped (concave jaws)."""
    bm = bmesh.new()
    top = [bm.verts.new(p + nrm * half) for p in pts]
    bot = [bm.verts.new(p - nrm * half) for p in pts]
    f1 = bm.faces.new(top)
    f2 = bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for k in range(n):
        bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f1, f2], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    return G.from_bm(name, bm, material, smooth=False)


def wrench(prefix, M, center, axis, flat):
    """Cartoon double open-ended spanner (about 1.25x a real 22 mm one, ~0.27 m): an oval shank through the fist, two
    open jaws in one plane. center: point in the fist; axis: shank direction toward the big jaw (thumb side);
    flat: normal of the spanner's plane."""
    a = Vector(axis).normalized()
    n = (Vector(flat) - a * Vector(flat).dot(a)).normalized()
    w = n.cross(a).normalized()
    c0 = Vector(center)
    sec = lambda s, half_w, half_t: (c0 + a * s, w, n, half_w, half_t)
    shank = G.loft(prefix + '_Shank', [sec(-0.100, 0.0165, 0.0068), sec(-0.084, 0.0124, 0.0066), sec(-0.054, 0.0122, 0.0070),
                                       sec(-0.036, 0.0145, 0.0112), sec(0.000, 0.0148, 0.0118), sec(0.036, 0.0145, 0.0112),
                                       sec(0.056, 0.0124, 0.0070), sec(0.098, 0.0138, 0.0068), sec(0.118, 0.0200, 0.0070)],
                   M['Wrench'], seg=10)
    big = _slab(prefix + '_JawBig', _jaw_outline(c0 + a * 0.140, a, w, 0.034, 0.0135, 15.0), n, 0.0070, M['Wrench'])
    small = _slab(prefix + '_JawSmall', _jaw_outline(c0 - a * 0.120, -a, -w, 0.027, 0.0105, 15.0), n, 0.0066, M['Wrench'])
    return [shank, big, small]


# Grip of the wrench in the RightHand at the T-pose (armature space), measured on the Grip_R finger pose
# (mechanic_w86_anim.GRIP_R): the shank runs front-back under the knuckle line (the mitten fingers wrap round it, the
# thumb closes it from the front; 36 of 320 finger vertices within 4 mm of the shank, deepest overlap 3.3 mm), the big
# jaw forward (out on the thumb side); the spanner plane lies against the palm.
WRENCH_GRIP = dict(center=(-0.738, -0.004, 1.119), axis=(0.0, -1.0, 0.0), flat=(0.0, 0.0, 1.0))


def hand_wrench(prefix, M):
    g = WRENCH_GRIP
    return [W.prop(o, 'RightHand') for o in wrench(prefix, M, Vector(g['center']), Vector(g['axis']), Vector(g['flat']))]

# ------------------------------------------------------------------ builder
def mechanic(body, face, M, skin):
    pre = TID
    src = C.weight_source([body])
    # grey tee, tucked in
    tee = W.top(pre + '_Tee', W.TUCKED, 6, TEE_SLEEVE, (.852, .166, .110, -.006), [M['Tee']])
    out = [_t(tee, src, C.no_head)]
    # open olive work jacket with rolled short sleeves
    jacket, parts = TR.open_shirt(pre, {'Shirt': M['Jacket'], 'Shirt_Roll': M['Jacket_Roll']}, src, rows=JACKET_ROWS,
                                  arm_row=JACKET_ARM_ROW, hem=JACKET_HEM, mats=[M['Jacket'], M['Jacket_Roll']],
                                  sleeve_mat=[0] * 5 + [1] * 5, gap=jacket_gap, edge_slot='Shirt')
    out += parts
    jsrc = C.weight_source([jacket])
    deco = []
    for s in (1, -1):
        x0, x1 = 0.104, 0.168
        deco.append(W.front_decal(f'{pre}_ChestPocket_{s}', [(s * x0, 1.058), (s * x1, 1.058), (s * x1, 1.142), (s * x0, 1.142)][::s],
                                  jacket, M['Jacket_Dark'], 0.0035, thickness=0.004, step=0.012))
        deco.append(W.front_decal(f'{pre}_ChestFlap_{s}', [(s * (x0 - 0.004), 1.130), (s * (x1 + 0.004), 1.130), (s * (x1 + 0.004), 1.166),
                                                          (s * (x0 - 0.004), 1.166)][::s], jacket, M['Jacket'], 0.0085, thickness=0.004,
                                  step=0.012))
    stains = [((0.142, 0.985, 0.022), 41), ((-0.150, 1.030, 0.017), 42), ((0.120, 1.200, 0.012), 43), ((-0.176, 0.940, 0.014), 44)]
    for (x, z, r), seed in stains:
        deco.append(W.front_decal(f'{pre}_JacketOil_{seed}', W.blob(x, z, r, seed=seed, rough=0.6), jacket, M['Jacket_Oil'], 0.0028))
    for k, (x, z, r) in enumerate(((0.070, 1.020, 0.026), (-0.100, 0.960, 0.020), (-0.040, 1.150, 0.014))):
        deco.append(G.decal(f'{pre}_JacketOilB_{k}', W.blob(x, z, r, seed=50 + k, rough=0.6), W.BACK(), [jacket], 0.0028, M['Jacket_Oil']))
    deco.append(G.decal(pre + '_Yoke', [(-0.170, 1.172), (0.170, 1.172), (0.170, 1.180), (-0.170, 1.180)], W.BACK(), [jacket], 0.0025,
                        M['Jacket_Dark'], step=0.012))
    out += [_t(o, jsrc) for o in deco]
    # dark cargo trousers with turned-up cuffs
    trousers = T._trousers(pre, M, 'Trousers', src, legs=LEGS, cuff=CUFF, cuff_slot='Trousers_Cuff')
    out.append(trousers)
    tdeco = []
    for s in (1, -1):
        axes = ((s * 0.7 + s * B.LEG_X, 0, 0), (0, -s, 0), (0, 0, 1), (-s, 0, 0))
        tdeco.append(G.decal(f'{pre}_CargoPocket_{s}', [(-0.054, 0.420), (0.054, 0.420), (0.054, 0.540), (-0.054, 0.540)], axes, [trousers],
                             0.004, M['Trousers_Pocket'], thickness=0.008, step=0.020))
        tdeco.append(G.decal(f'{pre}_CargoFlap_{s}', [(-0.058, 0.528), (0.058, 0.528), (0.058, 0.560), (-0.058, 0.560)], axes, [trousers],
                             0.012, M['Trousers'], thickness=0.005, step=0.020))
        tdeco.append(G.decal(f'{pre}_BackPocket_{s}', [(s * 0.040, 0.730), (s * 0.140, 0.730), (s * 0.146, 0.818), (s * 0.036, 0.818)][::s],
                             W.BACK(), [trousers], 0.0035, M['Trousers_Pocket'], thickness=0.003, step=0.020))
    for (x, z, r), seed in (((0.130, 0.560, 0.030), 61), ((0.090, 0.330, 0.022), 62), ((-0.120, 0.640, 0.020), 63),
                            ((-0.080, 0.300, 0.026), 64), ((0.060, 0.760, 0.014), 65)):
        tdeco.append(W.front_decal(f'{pre}_Oil_{seed}', W.blob(x, z, r, seed=seed, rough=0.6), trousers, M['Oil'], 0.0028))
    for k, (x, z, r) in enumerate(((-0.110, 0.420, 0.026), (0.120, 0.250, 0.020))):
        tdeco.append(G.decal(f'{pre}_OilB_{k}', W.blob(x, z, r, seed=70 + k, rough=0.6), W.BACK(), [trousers], 0.0028, M['Oil']))
    out += _decal_t(tdeco, trousers)
    tsrc = C.weight_source([trousers])
    out.append(_t(rag(pre + '_Rag', M, trousers), tsrc))
    belt, gear = belt_gear(pre, M)
    out += [_t(o, src) for o in belt] + gear
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole'], M['Boot_Lace'], high=True)
    out += bandana(pre + '_Bandana', M)
    out += side_hair(pre + '_Hair', M)
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.012, size=1.9)
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head, dots=95, seed=86))
    out += hand_wrench(pre + '_Wrench', M)
    return out


def register():
    """Add the type to buddy_types (in memory only)."""
    T.TYPES[TID] = TYPE
    T.BUILDERS[TID] = mechanic
