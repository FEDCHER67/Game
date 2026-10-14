"""District pool 'Даунтаун' (the old town became the American Downtown, TASK-000514), part 3: the pompous businessman
(replaces the tourist) and Karen. Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS.
No bpy calls at import time."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Даунтаун'
GOLD = ((214, 174, 76), 0.28, 'metal')
METAL = 'metal'

TYPES = {
    'OLD_BUSINESSMAN': dict(
        label='Бизнесмен', group=GROUP, hand_props=True, body=dict(belly=0.8), arm_down=66.0, face=dict(Blink=0.35, Happy=0.5),
        look=dict(skin=(240, 170, 140), nose=(236, 128, 108), brow=(170, 168, 164)),
        slots={'Suit': ((28, 34, 58), 0.55), 'Lapel': ((22, 26, 46), 0.4), 'Pinstripe': ((150, 156, 180), 0.6),
               'Shirt': ((246, 246, 242), 0.7), 'Tie': ((176, 24, 36), 0.4), 'Button': ((20, 20, 24), 0.4),
               'Square': ((176, 24, 36), 0.5), 'Socks': ((24, 24, 28), 0.9), 'Shoes': ((14, 12, 12), 0.12),
               'Shoe_Sole': ((40, 30, 26), 0.6), 'Gold': GOLD, 'WatchFace': ((24, 24, 28), 0.2), 'Hair': ((200, 200, 204), 0.3),
               'HairPart': ((150, 150, 156), 0.5), 'Mustache': ((200, 200, 204), 0.7), 'Cigar': ((110, 66, 36), 0.7),
               'Cigar_Band': ((214, 174, 76), 0.4), 'Ember': ((250, 110, 40), 0.3), 'Ash': ((160, 156, 150), 0.9),
               'Case': ((96, 54, 30), 0.35), 'Case_Trim': ((70, 40, 22), 0.4)},
        colourways=[{'Suit': (44, 44, 48), 'Lapel': (34, 34, 38), 'Tie': (40, 70, 150), 'Square': (40, 70, 150)},
                    {'Suit': (200, 190, 160), 'Lapel': (180, 170, 140), 'Pinstripe': (120, 110, 90), 'Tie': (60, 110, 70),
                     'Square': (60, 110, 70), 'Case': (30, 28, 28)}]),
    'OLD_KAREN': dict(
        label='Карен', group=GROUP, hand_props=True, no_ears=True, body=dict(belly=1.3), arm_down=62.0,
        face=dict(Blink_R=0.4, Worried=0.5, Surprised=0.25),
        look=dict(skin=(244, 196, 172), nose=(238, 160, 140), brow=(244, 196, 172), mouth=(196, 70, 90)),   # default brows hidden
        slots={'Tee': ((248, 246, 240), 0.8), 'Print': ((34, 30, 32), 0.6), 'Cardigan': ((44, 150, 152), 0.9),
               'Cardigan_Rib': ((34, 126, 128), 0.9), 'Leggings': ((32, 32, 36), 0.7), 'Shoe_Upper': ((244, 244, 240), 0.6),
               'Shoe_Sole': ((236, 234, 228), 0.6), 'Shoe_Accent': ((206, 168, 200), 0.6), 'Shoe_Lace': ((240, 240, 236), 0.7),
               'Hair': ((236, 214, 150), 0.6), 'Hair_Streak': ((196, 160, 90), 0.6), 'Brows': ((120, 86, 52), 0.6),
               'Pearl': ((248, 246, 240), 0.2), 'Bag': ((214, 186, 140), 0.4), 'Bag_Trim': ((150, 100, 60), 0.45), 'Gold': GOLD,
               'Phone': ((240, 200, 210), 0.3), 'Screen': ((38, 56, 88), 0.1), 'Dog': ((216, 170, 112), 0.7),
               'Dog_Ear': ((238, 170, 166), 0.7), 'Dog_Eye': ((18, 16, 18), 0.08), 'Dog_Nose': ((34, 26, 26), 0.3),
               'Dog_Collar': ((236, 60, 150), 0.3)},
        colourways=[{'Cardigan': (150, 100, 168), 'Cardigan_Rib': (128, 84, 146), 'Leggings': (60, 66, 90)},
                    {'Cardigan': (226, 126, 120), 'Cardigan_Rib': (204, 106, 100), 'Hair': (250, 236, 190), 'Bag': (40, 36, 36)}]),}

_t = T._t


# ------------------------------------------------------------------ OLD_BUSINESSMAN
def pinstripes(prefix, jacket, material, xs, z0=0.735, z1=1.180, width=0.0028):
    """Thin vertical pinstripes, front and back (dense edge points so they lie on the cloth)."""
    import buddy_pool_bad as BD
    out = []
    for k, x in enumerate(xs):
        pts = BD.stripe_outline(x - width / 2, x + width / 2, z0, z1)
        out.append(W.front_decal(f'{prefix}_F_{k}', pts, jacket, material, 0.0026, step=0.02))
        out.append(G.decal(f'{prefix}_B_{k}', pts, W.BACK(), [jacket], 0.0026, material, step=0.02))
    return out


def cigar(prefix, M):
    """Fat cigar in the left mouth corner with a gold band, a glowing tip and a bit of ash (a head prop)."""
    a, b = Vector((0.026, -0.122, 1.404)), Vector((0.118, -0.212, 1.390))
    d = (b - a).normalized()
    parts = [G.tube(prefix + '_Body', [a, b], lambda i, n: (0.0090, 0.0100)[i], M['Cigar'], seg=10),
             G.tube(prefix + '_Band', [a + d * 0.030, a + d * 0.044], 0.0102, M['Cigar_Band'], seg=10),
             G.tube(prefix + '_Ember', [b, b + d * 0.008], 0.0098, M['Ember'], seg=10),
             G.ellipsoid(prefix + '_Ash', b + d * 0.016, (0.009, 0.009, 0.009), M['Ash'], seg=8, rings=5)]
    return [W.prop(o, 'Head') for o in parts]


def briefcase(prefix, M, arm_down):
    """Leather briefcase hanging from its handle in the left fist: gold clasps and corner caps; dropped at the slightest
    danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    import buddy_pool_bad as BD
    fist, _, _ = HM.grip('Left', arm_down)
    c = fist + Vector((0.0, 0.0, -0.036 - 0.135))
    parts = [BD.rbox(prefix + '_Case', c, (0.036, 0.190, 0.135), M['Case'], bevel=0.014),
             BD.rbox(prefix + '_Seam', c + Vector((0.0, 0.0, 0.098)), (0.038, 0.192, 0.004), M['Case_Trim'], bevel=0.002)]
    top = c.z + 0.135
    parts.append(G.tube(prefix + '_Handle', [Vector((fist.x, fist.y - 0.050, top)), Vector((fist.x, fist.y - 0.040, fist.z + 0.010)),
                                              Vector((fist.x, fist.y + 0.040, fist.z + 0.010)), Vector((fist.x, fist.y + 0.050, top))],
                        0.0075, M['Case_Trim'], seg=8))
    for s in (1, -1):
        for side in (1, -1):
            parts.append(BD.rbox(f'{prefix}_Clasp_{s}_{side}', Vector((fist.x + side * 0.038, fist.y + s * 0.110, top - 0.022)),
                                 (0.003, 0.014, 0.010), M['Gold'], bevel=0.002))
    return HM.hold(parts, 'Left', arm_down)


def businessman(body, face, M, skin):
    """The pompous rich businessman (TASK-000514, replaces the tourist): a navy pinstripe suit with a red silk tie and a
    pocket square, a well-fed belly, slicked-back silver hair and a grey moustache, a fat cigar, a big gold watch, a
    leather briefcase in the left hand (dropped at the slightest danger), a smug squint."""
    import buddy_pool_bad2 as BD2
    pre = 'OLD_BUSINESSMAN'
    src = C.weight_source([body])
    jacket, out = T._suit(pre, M, src, 'Suit', 'Tie', 'Button', square_slot='Square')
    jsrc = C.weight_source([jacket])
    xs = [x / 1000 for x in range(-195, 200, 30) if abs(x) > 70]          # not under the lapels and the tie
    out += [_t(o, jsrc) for o in pinstripes(pre + '_Pin', jacket, M['Pinstripe'], xs)]
    trousers = T._trousers(pre, M, 'Suit', src)
    out += [trousers] + T._decal_t(pinstripes(pre + '_PinLeg', trousers, M['Pinstripe'], [-0.135, -0.105, -0.075, 0.075, 0.105, 0.135],
                                              z0=0.150, z1=0.700), trousers)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += T._dress_shoes(pre, M)
    out += BD2._big_watch(pre + '_Watch', M, x=0.600, side=1)
    hair = W.hair(pre + '_Hair', M['Hair'], 'slick')
    out += [hair, W.hair_part(pre + '_HairPart', M['HairPart'], hair, x=-0.052)]
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.006, size=1.15)
    out += cigar(pre + '_Cigar', M)
    out += briefcase(pre + '_Case', M, TYPES[pre]['arm_down'])
    return out


# ------------------------------------------------------------------ OLD_KAREN
def karen_bob(prefix, M, cols=40, rows=7):
    """The 'can I speak to the manager' cut: a short blonde bob, chin length at the sides, a swept fringe, a short
    stacked back with a few spikes on the crown, darker streaks (highlights) every few strands."""
    import random
    lower = W.zprofile([(0, 1.700), (25, 1.690), (45, 1.600), (60, 1.470), (95, 1.420), (130, 1.520), (180, 1.560)])   # the brows show
    back = lambda phi: (1 - math.cos(phi)) / 2
    off = lambda phi, u: 0.010 + 0.034 * back(phi) * math.sin(math.pi * min(1.0, u * 1.3)) + 0.010 * (1 - u)
    vs, fs, idx, grid = [], [], [], []
    for j in range(cols):
        phi = -math.pi + 2 * math.pi * j / cols
        col = []
        for i in range(rows):
            u = i / rows
            p, _ = W.head_at(phi, lower(phi) + (W.H_POLE - lower(phi)) * u, off(phi, u))
            col.append(len(vs)); vs.append(p)
        grid.append(col)
    top = len(vs); vs.append(Vector((0, 0, B.HEAD_TOP + off(0.0, 1.0))))
    for j in range(cols):
        a_, b_ = grid[j], grid[(j + 1) % cols]
        for i in range(rows - 1):
            fs.append((a_[i], b_[i], b_[i + 1], a_[i + 1])); idx.append(1 if j % 4 == 1 else 0)
        fs.append((a_[-1], b_[-1], top)); idx.append(0)
    ob = G.from_data(prefix + '_Bob', vs, fs, M['Hair'], True, idx, [M['Hair_Streak']], fix_normals=False)
    G.solidify(ob, 0.008, offset=1.0)
    out = [ob]
    rnd = random.Random(11)
    for k in range(9):                                       # the stacked, spiky crown at the back
        phi = math.radians(rnd.uniform(135, 225))
        z = rnd.uniform(1.670, 1.735)
        u = (W.h_of(z) - lower(phi)) / (W.H_POLE - lower(phi))
        p, nrm = W.head_at(phi, W.h_of(z), off(phi, u))
        d = (nrm + Vector((0.0, 0.5, 0.6))).normalized()
        out.append(G.tube(f'{prefix}_Spike_{k}', [p - d * 0.006, p + d * rnd.uniform(0.026, 0.040)], lambda i, n: (0.010, 0.0012)[i],
                          M['Hair'], seg=6))
    return [C.rigid(o, 'Head') for o in out]


def angry_brows(prefix, material):
    """Thick drawn-on brows the shape keys alone cannot make: the right one pulled down to the nose, the left one
    arched high - the 'excuse me?' look (static, they do not follow the expression keys)."""
    out = []
    for s, line in ((-1, ((0.094, 1.642), (0.070, 1.636), (0.046, 1.624), (0.022, 1.610))),
                    (1, ((0.016, 1.640), (0.034, 1.662), (0.056, 1.674), (0.080, 1.660)))):
        pts = [Vector((s * x, B.head_surface_y(s * x, z, 0.010), z)) for x, z in line]
        out.append(C.rigid(G.tube(f'{prefix}_{s}', pts, lambda i, n: (0.0085, 0.0110, 0.0105, 0.0080)[i], material, seg=8), 'Head'))
    return out


def pearls(prefix, M, targets, r=0.0085):
    """String of pearls round the neck (v01-v02 over the collar of the gilet, v03 over the tee)."""
    import buddy_pool_construction as CN
    raw = [Vector((0.160 * math.sin(2 * math.pi * k / 48), -0.155 * math.cos(2 * math.pi * k / 48) + 0.004,
                   1.262 - 0.040 * ((1 + math.cos(2 * math.pi * k / 48)) / 2) ** 2)) for k in range(48)]
    ps, _ = CN.on_surface(targets, raw, 0.010, step=0.018, smooth=2, closed=True)
    return [G.ellipsoid(f'{prefix}_{k}', p, (r, r, r), M['Pearl'], seg=8, rings=5) for k, p in enumerate(ps)]


def handbag(prefix, M, arm_down):
    """Big designer handbag hanging from its two handles in the left fist: a gold clasp and trim; dropped at the
    slightest danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    import buddy_pool_bad as BD
    fist, _, _ = HM.grip('Left', arm_down)
    c = fist + Vector((0.0, 0.0, -0.090 - 0.100))
    bag = BD.rbox(prefix + '_Bag', c, (0.050, 0.150, 0.100), M['Bag'], bevel=0.022)
    for v in bag.data.vertices:                  # a trapezoid: wider at the bottom
        k = 1.0 + 0.18 * (c.z - v.co.z) / 0.100
        v.co.y = c.y + (v.co.y - c.y) * k
    bag.data.update()
    parts = [bag, BD.rbox(prefix + '_Trim', c + Vector((0.0, 0.0, 0.080)), (0.052, 0.140, 0.005), M['Bag_Trim'], bevel=0.003),
             BD.rbox(prefix + '_Clasp', c + Vector((0.052, 0.0, 0.070)), (0.004, 0.020, 0.014), M['Gold'], bevel=0.003)]
    top = c.z + 0.100
    for k, dy in enumerate((-0.010, 0.010)):
        handle = [Vector((fist.x + dy, fist.y - 0.080, top)), Vector((fist.x + dy, fist.y - 0.050, fist.z - 0.010)),
                  Vector((fist.x + dy, fist.y, fist.z + 0.012)), Vector((fist.x + dy, fist.y + 0.050, fist.z - 0.010)),
                  Vector((fist.x + dy, fist.y + 0.080, top))]
        parts.append(G.tube(f'{prefix}_Handle_{k}', handle, 0.0060, M['Bag_Trim'], seg=6))
    parts += chihuahua(prefix + '_Dog', M, Vector((c.x, c.y - 0.050, top)), Vector((0.45, -1.0, 0.0)))
    return HM.hold(parts, 'Left', arm_down)


def chihuahua(prefix, M, rim, facing, size=1.35):
    """Chihuahua peeking out of the handbag (idle world frame): an apple head, huge bulging eyes, bat ears, a pink
    rhinestone collar, both front paws over the rim; modelled at size 1 and scaled about the rim."""
    f = facing.normalized()
    u = Vector((0, 0, 1))
    r = f.cross(u).normalized()
    h = rim + u * 0.040
    rot = Matrix((r, f, u)).transposed()
    out = [G.ellipsoid(prefix + '_Head', h, (0.031, 0.029, 0.027), M['Dog'], rot=rot, seg=14, rings=10),
           G.ellipsoid(prefix + '_Snout', h + f * 0.026 - u * 0.009, (0.013, 0.015, 0.010), M['Dog'], rot=rot, seg=10, rings=7),
           G.ellipsoid(prefix + '_Nose', h + f * 0.040 - u * 0.005, (0.0055, 0.004, 0.0045), M['Dog_Nose'], rot=rot, seg=8, rings=5),
           G.ellipsoid(prefix + '_Neck', h - u * 0.034 - f * 0.004, (0.022, 0.022, 0.026), M['Dog'], rot=rot, seg=12, rings=8)]
    for s in (1, -1):
        e = h + f * 0.019 + r * (s * 0.016) + u * 0.006
        out.append(G.ellipsoid(f'{prefix}_Eye_{s}', e, (0.0095, 0.0085, 0.0095), M['Dog_Eye'], rot=rot, seg=10, rings=7))
        out.append(G.ellipsoid(f'{prefix}_Shine_{s}', e + f * 0.0080 + u * 0.0035 + r * (s * 0.002), (0.0024, 0.0012, 0.0024), M['Pearl'],
                               rot=rot, seg=6, rings=4))
        tilt = Matrix.Rotation(math.radians(s * 28), 3, f)
        er = tilt @ rot
        ec = h + r * (s * 0.020) + u * 0.030 - f * 0.004
        out.append(G.ellipsoid(f'{prefix}_Ear_{s}', ec + tilt @ (u * 0.004), (0.012, 0.0045, 0.026), M['Dog'], rot=er, seg=10, rings=7))
        out.append(G.ellipsoid(f'{prefix}_EarIn_{s}', ec + tilt @ (u * 0.004) + f * 0.0030, (0.0075, 0.0025, 0.018), M['Dog_Ear'], rot=er,
                               seg=10, rings=6))
        out.append(G.ellipsoid(f'{prefix}_Paw_{s}', rim + f * 0.024 + r * (s * 0.014) + u * 0.006, (0.008, 0.012, 0.0065), M['Dog'], rot=rot,
                               seg=8, rings=5))
    ring = [h - u * 0.022 - f * 0.002 + (r * math.cos(a) * 0.024 + f * math.sin(a) * 0.023) for a in [2 * math.pi * k / 16 for k in range(18)]]
    out.append(G.tube(prefix + '_Collar', ring, 0.0042, M['Dog_Collar'], seg=6))
    k = Matrix.Translation(rim) @ Matrix.Scale(size, 4) @ Matrix.Translation(-rim)
    for o in out:
        o.data.transform(k)
        o.data.update()
    return out


CARDIGAN = [(.480, .236, .170, -.013), (.495, .236, .170, -.013), (.56, .230, .166, -.013), (.65, .224, .160, -.013),
            (.74, .217, .154, -.013), (.80, .213, .150, -.013), (.86, .210, .146, -.013), (.94, .209, .144, -.012)] + \
           [r for r in W.JACKET if r[0] >= 1.02]              # long open knit cardigan to the knees; arm row 10 (z 1.10)
CAPRI = [(.70, .074), (.60, .066), (.50, .060), (.43, .056), (.36, .054), (.33, .053), (.325, .049)]


def belly_rows(rows, arm_row, z0=0.80, z1=1.08, step=0.025):
    """Garment rows with an extra ring every `step` over the belly, so a big reshaped belly stays round instead of
    angular (TASK-000516). Returns the rows and the arm row index shifted by the added rings."""
    low, high = list(rows[:arm_row]), list(rows[arm_row:])
    zs = [r[0] for r in low]
    n = int(round((z1 - z0) / step))
    extra = [W.lerp_row(low + [high[0]], z0 + step * k) for k in range(n + 1)
             if all(abs(z0 + step * k - q) >= step / 2 for q in zs)]
    low = sorted(low + extra, key=lambda r: r[0])
    return low + high, len(low)


def karen(body, face, M, skin):
    """Karen v04 (TASK-000516, Vadim: no painted face, a bit fatter, more characteristic clothes; v03 had belly 1.1,
    which the long cardigan hid in profile - v04 has 1.3, and the tee and the cardigan get extra rings over the belly so
    it stays round, Vadim: 'что за угловатый живот'): a big round belly, the
    short blonde 'speak to the manager' bob with highlights and a high fringe, drawn-on brows (one pulled down, one
    arched up), a squinting eye, a pursed rose mouth - no eyeshadow, no blush; a long open teal knit cardigan with
    patch pockets over a white 'LIVE LAUGH LOVE' tee, chunky pearls, black capri leggings, white chunky 'mom'
    sneakers; the designer handbag with a chihuahua peeking out in the left hand and the phone in the right (both
    dropped at the slightest danger). v02 had blue eyeshadow, hot-pink lips and the pink quilted gilet over light
    skinny jeans; v01 big sunglasses and a thin waist."""
    import buddy_pool_bad2 as BD2
    import buddy_pool_bad3 as BD3
    import buddy_pool_oldtown2 as O2
    pre = 'OLD_KAREN'
    src = C.weight_source([body])
    tee_rows, tee_arm = belly_rows(W.TEE, 6)
    tee = _t(W.top(pre + '_Tee', tee_rows, tee_arm, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Tee']]), src, C.no_head)
    tsrc = C.weight_source([tee])
    words = []
    for k, (word, z) in enumerate((('LIVE', 1.118), ('LAUGH', 1.058), ('LOVE', 0.998))):
        span = 0.58 * len(word)
        words += C.text_arc(f'{pre}_Print_{k}', word, z + 3.0, 3.0, 270.0 - span / 2, 270.0 + span / 2, False, M['Print'], tee, size=0.040)
    out = [tee] + [_t(o, tsrc) for o in words]
    card_rows, card_arm = belly_rows(CARDIGAN, 10)
    card = W.top(pre + '_Cardigan', card_rows, card_arm, W.JACKET_SLEEVE, (.495, .226, .162, -.013), [M['Cardigan'], M['Cardigan_Rib']],
                 row_mat=[1] + [0] * (len(card_rows) - 2), sleeve_mat=[0] * 7 + [1] * 3, hem_mat=1,
                 cut=lambda c: c.y < 0 and abs(c.x) < 0.085)
    _t(card, src, BD3._coat_weights)
    csrc = C.weight_source([card])
    pockets = []
    for s in (1, -1):
        x0, x1 = (0.125, 0.205) if s > 0 else (-0.205, -0.125)
        pockets.append(W.front_decal(f'{pre}_Pocket_{s}', [(x0, 0.600), (x1, 0.600), (x1, 0.715), (x0, 0.715)], card, M['Cardigan_Rib'], 0.004,
                                     thickness=0.003, step=0.012))
    out += [card] + [_t(o, csrc) for o in pockets]
    out += [_t(o, C.weight_source([tee, card]), C.no_head) for o in pearls(pre + '_Pearl', M, [tee, card], r=0.0105)]
    out.append(_t(W.bottoms(pre + '_Leggings', CAPRI, [M['Leggings']]), src))
    out += BD2._chunky_sneakers(pre, M)
    out += karen_bob(pre + '_Hair', M)
    out += angry_brows(pre + '_Brow', M['Brows'])
    out += handbag(pre + '_Handbag', M, TYPES[pre]['arm_down'])
    out += O2._phone_in_hand(pre + '_Phone', M)
    return out


# ------------------------------------------------------------------ OLD_RAPPER (TASK-000535: the Snoop moved from the rough district)
TYPES['OLD_RAPPER'] = dict(
    label='Рэпер', group=GROUP, body=dict(thin=1.0), face=dict(Happy=0.35),
    look=dict(skin=(104, 70, 50), nose=(94, 62, 44), brow=(16, 12, 12), rim=(70, 44, 32), mouth=(52, 26, 22)),
    slots={'Tee': ((246, 246, 242), 0.85), 'Coat': ((84, 38, 122), 0.55), 'Fur': ((244, 240, 232), 1.0),
           'Jeans': ((96, 130, 180), 0.9), 'Boots': ((206, 150, 70), 0.85), 'Boots_Sole': ((70, 50, 34), 0.6),
           'Boot_Lace': ((150, 110, 60), 0.7), 'Gold': GOLD, 'Dollar': ((48, 178, 84), 0.2), 'WatchFace': ((236, 240, 246), 0.15),
           'Scalp': ((20, 18, 18), 0.8), 'Braid': ((26, 22, 22), 0.75), 'Shades_Frame': ((24, 24, 26), 0.3),
           'Shades_Lens': ((18, 20, 26), 0.06), 'Mustache': ((20, 16, 16), 0.8), 'Joint': ((240, 236, 226), 0.8),
           'Ember': ((250, 110, 40), 0.3), 'Ash': ((160, 156, 150), 0.9)},
    colourways=[{'Coat': (34, 34, 38), 'Fur': (196, 160, 112)}, {'Coat': (150, 30, 44), 'Tee': (34, 34, 38)}])


def old_rapper(body, face, M, skin):
    import buddy_pool_bad2 as BD2
    return BD2.snoop(body, face, M, skin)


BUILDERS = {'OLD_BUSINESSMAN': businessman, 'OLD_KAREN': karen, 'OLD_RAPPER': old_rapper}
