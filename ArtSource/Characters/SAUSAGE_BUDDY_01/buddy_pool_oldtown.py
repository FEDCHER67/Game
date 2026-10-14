"""District pool 'Старый город' (TASK-000270) on the base Sausage Buddy - the American Downtown since TASK-000514:
the IRL streamer (v08, after Ivan Zolo), the college kid (the old student, v07 = the v03 design), the office worker; the vaper moved here
from 'Переход' in TASK-000272 and on to the rough district in TASK-000511 (OLD_VAPER stays buildable, out of the pool).
Same format as buddy_types.TYPES / BUILDERS; every garment and prop has its own material slot <TYPE>_<Slot>.
Carried props are modelled in the idle pose (world space, arms hanging) and baked back to the hand's T-pose frame,
so they sit in the hand exactly where the idle renders show them."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_anim as A
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Даунтаун'                 # was 'Старый город' until TASK-000514
METAL = 'metal'

TYPES = {
    'OLD_STREAMER': dict(
        label='IRL-стример', group=GROUP, hand_props=True, body=dict(thin=0.2), face=dict(Happy=0.4, Blink=0.15),
        look=dict(skin=(248, 214, 196), nose=(242, 170, 150), brow=(70, 52, 40)),
        slots={'Blazer': ((200, 32, 44), 0.6), 'Lapel': ((160, 22, 34), 0.5), 'Button': ((214, 174, 76), 0.3, METAL),
               'Tee': ((244, 244, 240), 0.85), 'Print_Skin': ((250, 222, 206), 0.8), 'Print_Hair': ((26, 24, 30), 0.8),
               'Print_Hair_2': ((240, 70, 150), 0.8), 'Print_Ink': ((24, 24, 26), 0.6), 'Print_Blush': ((240, 130, 160), 0.8),
               'Print_Lips': ((96, 20, 64), 0.5), 'Print_Shine': ((255, 255, 255), 0.6), 'Print_Bg': ((204, 172, 236), 0.8),
               'Print_Metal': ((206, 208, 216), 0.4), 'Sweats': ((150, 150, 158), 0.9), 'Sweats_Rib': ((132, 132, 140), 0.9),
               'Socks': ((250, 250, 246), 0.9), 'Slides': ((130, 210, 60), 0.5), 'Scalp': ((24, 26, 84), 0.9),
               'Dread': ((44, 42, 200), 0.9), 'Dread_Mid': ((140, 40, 180), 0.9), 'Dread_Tip': ((242, 52, 132), 0.9),
               'Stick': ((30, 30, 34), 0.4), 'Stick_Grip': ((20, 20, 22), 0.8), 'Phone': ((30, 30, 34), 0.4),
               'Screen': ((120, 200, 255), 0.1)},
        colourways=[{'Blazer': (40, 90, 200), 'Lapel': (30, 66, 160), 'Scalp': (90, 20, 16), 'Dread': (226, 70, 30),
                     'Dread_Mid': (240, 120, 40), 'Dread_Tip': (250, 170, 60)},
                    {'Blazer': (236, 196, 40), 'Lapel': (200, 160, 30), 'Slides': (236, 60, 140), 'Scalp': (20, 60, 30),
                     'Dread': (40, 160, 70), 'Dread_Mid': (150, 120, 60), 'Dread_Tip': (220, 40, 40)}]),
    'OLD_STUDENT': dict(
        label='College kid', group=GROUP, face=dict(Surprised=0.3),
        slots=dict(T.TYPES['CITY_STUDENT']['slots'],
                   **{'Phones': ((236, 66, 58), 0.4), 'Phones_Pad': ((40, 40, 44), 0.9), 'Phones_Plate': ((240, 238, 232), 0.35)}),
        colourways=[dict(T.TYPES['CITY_STUDENT']['colourways'][0], Phones=(240, 240, 236), Phones_Plate=(40, 40, 44)),
                    dict(T.TYPES['CITY_STUDENT']['colourways'][1], Phones=(40, 40, 44), Phones_Plate=(236, 66, 58))]),
    'OLD_OFFICE': dict(
        label='Работник офиса', group=GROUP, face=dict(Worried=0.35, Blink=0.3),
        slots=dict(T.TYPES['CITY_CLERK']['slots'],
                   **{'Lanyard': ((40, 92, 186), 0.7), 'Clip': ((196, 198, 204), 0.3, METAL), 'Badge': ((248, 248, 244), 0.4),
                      'Badge_Stripe': ((40, 92, 186), 0.5), 'Badge_Photo': ((236, 170, 128), 0.6), 'Badge_Line': ((60, 62, 70), 0.6),
                      'EyeBags': ((168, 130, 146), 0.8), 'Cup': ((246, 244, 238), 0.6), 'Cup_Sleeve': ((150, 104, 64), 0.85),
                      'Cup_Lid': ((40, 36, 34), 0.45)}),
        colourways=[dict(T.TYPES['CITY_CLERK']['colourways'][0], Lanyard=(196, 40, 48), Badge_Stripe=(196, 40, 48),
                         Cup_Lid=(246, 244, 238), Cup_Sleeve=(60, 120, 80)),
                    dict(T.TYPES['CITY_CLERK']['colourways'][1], Lanyard=(42, 140, 96), Badge_Stripe=(42, 140, 96),
                         Cup=(232, 206, 160), Cup_Sleeve=(232, 206, 160), Cup_Lid=(246, 244, 238))]),
}

# ------------------------------------------------------------------ prop helpers (idle pose <-> T-pose)
def _idle(bone):
    """Armature-space matrix of a bone in the idle pose (frame 1 of 'Idle')."""
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    return A.pose_from_joints(rig, W.REST, A.idle_joints())[P + bone]


def _hand_frame(side):
    """Idle-pose palm centre and axes of a hand: finger direction (down), palm normal, thumb direction (forward)."""
    bone = side + 'Hand'
    K = _idle(bone) @ W.bone_rest(bone).inverted()          # T-pose -> idle
    s = 1 if side == 'Left' else -1
    R3 = K.to_3x3()
    return (K @ Vector((s * 0.690, 0.0, 1.157)), (R3 @ Vector((s, 0, 0))).normalized(),
            (R3 @ Vector((0, 0, -1))).normalized(), (R3 @ Vector((0, -1, 0))).normalized())


def _held(objs, side):
    """Meshes modelled in the idle pose -> baked to the T-pose, rigid on the hand bone, flagged as carried props."""
    bone = side + 'Hand'
    K = W.bone_rest(bone) @ _idle(bone).inverted()
    for ob in objs:
        ob.data.transform(K)
        ob.data.update()
        W.prop(ob, bone)
    return objs


def _frame(axis, ref=Vector((0, 0, 1))):
    """3x3 matrix whose Z column is `axis`."""
    z = Vector(axis).normalized()
    x = ref.cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def _lathe(name, base, axis, rows, mats, seg=16, cap_start=True, cap_end=True):
    """Body of revolution: rows (h, r, mat index of the band from this row to the next) along `axis` from `base`."""
    F = _frame(axis)
    u, v, a = F.col[0], F.col[1], F.col[2]
    secs = [(Vector(base) + a * h, u, v, r, r) for h, r, _ in rows]
    return G.loft(name, secs, mats[0], seg=seg, cap_start=cap_start, cap_end=cap_end, mat_rows=[m for _, _, m in rows[:-1]],
                  extra=list(mats[1:]))


def _rename(objs, old, new):
    for o in objs:
        if o.name.startswith(old):
            o.name = new + o.name[len(old):]
        elif not o.name.startswith(new):
            o.name = new + '_' + o.name
    return objs


def _dread(name, pts, r, M):
    """One thick dreadlock along a polyline: blue from the root, a purple band, a hot-pink rounded tip."""
    P = [Vector(p) for p in pts]
    secs = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.95 else Vector((1, 0, 0))
        a = up.cross(t).normalized()
        rr = r * (0.85 if i == 0 else 1.0)
        secs.append((p, a, t.cross(a).normalized(), rr, rr))
    n = len(P) - 1
    rows = [0] * (n - 2) + [1, 2]
    ob = G.loft(name, secs, M['Dread'], seg=6, mat_rows=rows, extra=[M['Dread_Mid'], M['Dread_Tip']])
    tip = G.ellipsoid(name + '_Tip', P[-1], (r, r, r), M['Dread_Tip'], seg=6, rings=4)
    return [ob, tip]


def _zolo_dreads(prefix, M):
    """The Ivan Zolo hair of Vadim's reference photo: short thick dreadlocks springing from the crown in every
    direction - blue with hot-pink tips - over a dark-navy braided base; the front ones arc over the forehead and end
    above the eyes, the sides of the head stay bare."""
    import random
    rnd = random.Random(23)
    base = W.zprofile([(0, 1.684), (40, 1.672), (90, 1.650), (140, 1.640), (180, 1.640)])
    scalp, _ = W.shell(prefix + '_Base', M['Scalp'], base, None, off=0.004, thick=0.004, seg=32, rows=5)
    out = [scalp]
    specs = []
    for ring, (count, z_lo, z_hi) in enumerate(((22, 1.672, 1.690), (14, 1.708, 1.722))):     # lower and upper ring of roots
        for k in range(count):
            deg = -180 + 360 * (k + 0.5 * ring + rnd.uniform(-0.3, 0.3)) / count
            a = abs(deg)
            z = rnd.uniform(z_lo, z_hi)
            if a < 35:      # front: arcs over the forehead, ends at the brows
                specs.append((deg, rnd.uniform(16, 24), rnd.uniform(24, 28), rnd.uniform(0.100, 0.118) - 0.012 * ring, max(z, 1.696)))
            elif a < 130:   # sides: stick far out and droop a little
                specs.append((deg, rnd.uniform(22, 38) - 10 * ring, rnd.uniform(6, 10), rnd.uniform(0.160, 0.190), z))
            else:           # back
                specs.append((deg, rnd.uniform(30, 44) - 10 * ring, rnd.uniform(6, 10), rnd.uniform(0.150, 0.180), z))
    for k in range(5):      # a few from the very top stand up and out
        specs.append((-180 + 72 * k + rnd.uniform(-20, 20), rnd.uniform(-30, -12), 14.0, rnd.uniform(0.110, 0.130), 1.738))
    up = Vector((0, 0, 1))
    n = 6
    for k, (deg, tilt, droop, length, z) in enumerate(specs):
        phi = math.radians(deg)
        root, nrm = W.head_at(phi, W.h_of(z), 0.002)
        out_dir = Vector((math.sin(phi), -math.cos(phi), 0.0))
        pts, p = [root], root.copy()
        for i in range(n):
            th = math.radians(tilt + 2 * droop * i / (n - 1))          # bends down more and more
            d = (out_dir * math.cos(th) - up * math.sin(th)).normalized()
            if i == 0:
                d = (d + nrm * 0.6).normalized()                         # leave the scalp first
            p = p + d * (length / n)
            pts.append(p.copy())
        out += _dread(f'{prefix}_Dread_{k}', pts, rnd.uniform(0.0115, 0.0135), M)
    return [C.rigid(o, 'Head') for o in out]


BLAZER = [(z, rx * 1.07, ry * 1.08, dy) for z, rx, ry, dy in W.JACKET]                  # oversized, arm row 7
BIG_SLEEVE = [(x, r * 1.08) for x, r in W.JACKET_SLEEVE[:7]] + [(.600, .061), (.626, .060), (.633, .055), (.629, .050)]   # past the wrists
LEGS_SHORT_SWEAT = [(.70, .094), (.60, .092), (.50, .088), (.43, .085), (.34, .080), (.31, .078)]
SHORT_SWEAT_CUFF = [(.296, .060), (.272, .056), (.270, .052)]


def _ccw(pts):
    """Outline turned counter-clockwise (the winding the decals expect)."""
    area = sum(x0 * z1 - x1 * z0 for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 0 else pts[::-1]


def _altushka_print(prefix, tee, M):
    """Print on the tee (Vadim: an 'altushka' like in his song, big and expressive): a lilac sticker disc with a
    cartoon alt girl - split-dyed hair, black and hot pink, a blunt fringe, a cat-ear headband, big eyes with heavy
    winged eyeliner, a little heart under one eye, blush, dark lips with a lip ring, a choker with a ring."""
    cx, cz = -0.002, 1.000
    out = []

    def dec(name, pts, slot, off, step=0.006):
        out.append(W.front_decal(f'{prefix}_{name}', _ccw([(cx + x, cz + z) for x, z in pts]), tee, M[slot], off, step=step))

    def heart(x0, z0, k):
        return [(x0 + k * 16 * math.sin(t) ** 3, z0 + k * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
                for t in [2 * math.pi * q / 24 for q in range(24)]]
    dec('Disc', C.ellipse(0.0, 0.018, 0.098, 0.106, 32), 'Print_Bg', 0.0026, step=0.010)
    arc = [(-0.072 * math.sin(math.pi / 2 * k / 8), 0.018 + 0.085 * math.cos(math.pi / 2 * k / 8)) for k in range(9)]
    dec('HairL', [(0.0, -0.080)] + arc + [(-0.070, -0.080)], 'Print_Hair', 0.0034)
    dec('HairR', [(-x, z) for x, z in [(0.0, -0.080)] + arc + [(-0.070, -0.080)]], 'Print_Hair_2', 0.0034)
    for s in (1, -1):
        dec(f'Ear_{s}', [(s * 0.024, 0.090), (s * 0.064, 0.064), (s * 0.060, 0.132)], 'Print_Hair', 0.0034)
        dec(f'EarIn_{s}', [(s * 0.034, 0.088), (s * 0.056, 0.074), (s * 0.055, 0.115)], 'Print_Hair_2', 0.0042, step=0.004)
    dec('Neck', [(-0.016, -0.080), (0.016, -0.080), (0.016, -0.050), (-0.016, -0.050)], 'Print_Skin', 0.0042)
    dec('Face', C.ellipse(0.0, 0.004, 0.050, 0.060, 24), 'Print_Skin', 0.0046)
    fringe = [(-0.056, 0.034), (0.0, 0.034), (0.0, 0.100), (-0.044, 0.090), (-0.062, 0.062)]
    dec('FringeL', fringe, 'Print_Hair', 0.0058)
    dec('FringeR', [(-x, z) for x, z in fringe], 'Print_Hair_2', 0.0058)
    for s in (1, -1):
        ex, ez = s * 0.021, 0.006
        dec(f'Liner_{s}', C.ellipse(ex, ez, 0.0115, 0.0145, 16), 'Print_Ink', 0.0066, step=0.004)
        dec(f'Wing_{s}', [(ex + s * 0.008, ez + 0.006), (ex + s * 0.024, ez + 0.017), (ex + s * 0.009, ez + 0.012)], 'Print_Ink', 0.0066, step=0.003)
        dec(f'White_{s}', C.ellipse(ex, ez - 0.001, 0.0085, 0.0112, 16), 'Print_Shine', 0.0072, step=0.003)
        dec(f'Pupil_{s}', C.ellipse(ex - s * 0.001, ez - 0.002, 0.0058, 0.0080, 14), 'Print_Ink', 0.0078, step=0.003)
        dec(f'Shine_{s}', C.ellipse(ex - s * 0.003, ez + 0.002, 0.0022, 0.0022, 8), 'Print_Shine', 0.0084, step=0.002)
        dec(f'Blush_{s}', C.ellipse(s * 0.033, -0.020, 0.010, 0.0055, 12), 'Print_Blush', 0.0066, step=0.004)
    dec('EyeHeart', heart(0.037, -0.027, 0.00040), 'Print_Ink', 0.0074, step=0.002)
    dec('Lips', C.ellipse(0.0, -0.036, 0.0095, 0.0042, 12), 'Print_Lips', 0.0066, step=0.003)
    dec('LipRing', C.ellipse(0.008, -0.041, 0.0026, 0.0026, 8), 'Print_Metal', 0.0074, step=0.002)
    dec('Choker', [(-0.020, -0.068), (0.020, -0.068), (0.020, -0.058), (-0.020, -0.058)], 'Print_Ink', 0.0058, step=0.004)
    dec('ChokerRing', C.ellipse(0.0, -0.073, 0.0045, 0.0045, 10), 'Print_Metal', 0.0066, step=0.003)
    return out


def _blazer_front(prefix, blazer, M):
    """Wide notched lapels beside the open front, two gold buttons on the left panel, pocket flaps."""
    out = []
    for s in (1, -1):
        lap = [(0.122, 1.000), (0.150, 1.100), (0.172, 1.160), (0.152, 1.176), (0.160, 1.196), (0.128, 1.214), (0.120, 1.150), (0.120, 1.060)]
        lap = [(s * x, z) for x, z in lap]
        out.append(W.front_decal(f'{prefix}_Lapel_{s}', lap if s > 0 else lap[::-1], blazer, M['Lapel'], 0.0035, step=0.008))
        flap = [(0.135, 0.800), (0.205, 0.800), (0.205, 0.824), (0.135, 0.824)]
        flap = [(s * x, z) for x, z in flap]
        out.append(W.front_decal(f'{prefix}_Flap_{s}', flap if s > 0 else flap[::-1], blazer, M['Lapel'], 0.0035, thickness=0.003))
    out += W.buttons(prefix + '_Btn', blazer, M['Button'], [(0.132, 0.930), (0.132, 0.860)], r=0.011)
    return out


def old_streamer(body, face, M, skin):
    """v08 (TASK-000516/517, Vadim: like the streamer Ivan Zolo, with a selfie stick, the hair as on Vadim's reference
    photo; the clothes more ridiculous; an 'altushka' on the tee, then bigger and more expressive - v08): short thick blue dreadlocks with hot-pink tips over
    a dark braided base, bare sides; a pale face with a goofy half-smile; an oversized red blazer (one of his photos)
    worn open, the sleeves past the wrists, over a white tee with a cartoon alt-girl print; grey sweatpants cut at
    mid-shin, white socks pulled up, lime slides; the phone on a long selfie stick in the right hand (dropped at the
    slightest danger). The face stays the common Sausage Buddy one. v06 had a cartoon cat on the tee, v05 a black tee
    with a grey-white print and black baggy jeans; v04 was the generic 2026 streamer (hoodie, IRL backpack, gimbal)."""
    import buddy_pool_oldtown2 as O2
    pre = 'OLD_STREAMER'
    src = C.weight_source([body])
    tee = T._t(W.top(pre + '_Tee', W.TEE, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Tee']]), src, C.no_head)
    out = [tee] + T._decal_t(_altushka_print(pre + '_Alt', tee, M), tee)
    blazer = W.top(pre + '_Blazer', BLAZER, 7, BIG_SLEEVE, (.716, .214, .146, -.012), [M['Blazer']],
                   cut=lambda c: c.y < 0 and abs(c.x) < 0.095)
    T._t(blazer, src, C.no_head)
    out += [blazer] + T._decal_t(_blazer_front(pre + '_Blazer', blazer, M), blazer)
    out.append(T._t(W.bottoms(pre + '_Sweats', LEGS_SHORT_SWEAT, [M['Sweats'], M['Sweats_Rib']], cuff=SHORT_SWEAT_CUFF), src))
    out.append(T._t(W.plain_socks(pre + '_Socks', M['Socks'], top=0.300), src))
    out += W.slides(pre, M['Socks'], M['Slides'])
    out += _zolo_dreads(pre + '_Hair', M)
    out += O2._selfie_stick(pre + '_Selfie', M, TYPES[pre].get('arm_down', 74.0))
    return out

# ------------------------------------------------------------------ OLD_VAPER (TASK-000272)
def _vaper_spec():
    """The vaper moved from 'Переход' to the old town: Vadim kept his first design, so the same slots and colourways."""
    import buddy_pool_transit2 as V2
    spec = dict(V2.TYPES['TRANSIT_VAPER'])
    spec['group'] = GROUP
    spec['hand_props'] = True
    return spec


def old_vaper(body, face, M, skin):
    import buddy_pool_transit2 as V2
    return V2.transit_vaper(body, face, M, skin)


TYPES['OLD_VAPER'] = _vaper_spec()

# ------------------------------------------------------------------ OLD_STUDENT
def _ear_cup(prefix, center, axis, M, shell, pad, plate, r=0.050, depth=0.040):
    """Headphone cup: soft pad on the inner side (toward -axis), hard shell, a coloured plate on the outer face."""
    rows = [(0.0, r * 0.70, 1), (0.004, r * 0.92, 1), (0.012, r * 0.98, 1), (0.014, r * 0.96, 0), (0.018, r * 1.0, 0),
            (depth - 0.006, r * 0.98, 0), (depth, r * 0.82, 0)]
    cup = _lathe(prefix + '_Cup', Vector(center) - Vector(axis).normalized() * (depth / 2), axis, rows, [M[shell], M[pad]], seg=18)
    a = Vector(axis).normalized()
    pl = G.ellipsoid(prefix + '_Plate', Vector(center) + a * (depth / 2 + 0.001), (r * 0.62, r * 0.62, 0.005), M[plate],
                     rot=_frame(a), seg=16, rings=6)
    return [cup, pl]

def _neck_headphones(prefix, M, targets):
    """Big headphones resting round the neck: band over the hood roll at the back, cups on the collarbones."""
    bvh = G.bvh_of(targets)

    def over(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.5))) >= 0 else -nrm
        return loc + nrm * off
    out = []
    for s in (1, -1):
        cc = Vector((s * 0.118, -0.182, 1.262))
        axis = Vector((s * 0.42, -0.62, 0.66)).normalized()
        out += _ear_cup(f'{prefix}_Cup_{s}', cc, axis, M, 'Phones', 'Phones_Pad', 'Phones_Plate', r=0.058, depth=0.044)
    pts = []
    for k in range(25):                                   # azimuth from the back (+y): the band runs round behind the neck
        a = math.radians(-138 + 276 * k / 24)
        pts.append(over(Vector((0.215 * math.sin(a), 0.020 + 0.205 * math.cos(a), 1.316)), 0.014))
    path = ([Vector((math.copysign(0.140, pts[0].x), -0.172, 1.296))] + pts
            + [Vector((math.copysign(0.140, pts[-1].x), -0.172, 1.296))])
    out.append(G.tube(prefix + '_Band', path, 0.013, M['Phones'], seg=10))
    return [C.rigid(o, 'Spine2') for o in out]


def old_student(body, face, M, skin):
    """v07 (TASK-000516, Vadim: keep the student as he was long ago): the old-town student v03 again - the yellow
    hoodie with the hood down, red headphones round the neck, a backpack, rolled jeans, white sneakers, bald
    (TASK-000281) - now in the Downtown group. v04-v06 (varsity jacket; basketball shorts; the plain schoolkid with
    books) are not used."""
    M = dict(M, Beanie=M['Hoodie'])        # city_student still makes the beanie; it is removed right below
    out = _rename(T.city_student(body, face, M, skin), 'STUDENT', 'OLD_STUDENT')
    for o in [o for o in out if o.name.startswith('OLD_STUDENT_Beanie')]:      # TASK-000281: bald, no beanie
        out.remove(o)
        me = o.data
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    hood = [o for o in out if o.name.startswith('OLD_STUDENT_Hood') and 'Pouch' not in o.name]
    hoodie = [o for o in out if o.name == 'OLD_STUDENT_Hoodie']
    out += _neck_headphones('OLD_STUDENT_Phones', M, hood + hoodie)
    return out

# ------------------------------------------------------------------ OLD_OFFICE
def _lanyard_badge(prefix, M, shirt, collar):
    bvh = G.bvh_of([shirt, collar])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    out = []
    for s in (1, -1):
        raw = [(0.168 * math.sin(math.radians(a)), 0.164 * math.cos(math.radians(a)), 1.276 - 0.012 * a / 90) for a in range(0, 91, 10)]
        raw += [(0.150, -0.060, 1.246), (0.116, -0.132, 1.198), (0.064, -0.162, 1.128), (0.016, -0.172, 1.074)]
        pts = [on(Vector((s * x, y, z)), 0.005)[0] for x, y, z in raw]
        out.append(C.strap(f'{prefix}_Lanyard_{s}', pts, M['Lanyard'], width=0.018, thick=0.003, normal_fn=lambda q: on(q, 0.0)[1]))
    cp, cn = on(Vector((0.0, -0.17, 1.062)), 0.011)
    out.append(W.box(prefix + '_Clip', cp, (0.010, 0.004, 0.012), M['Clip']))
    card = W.front_decal(prefix + '_Badge', [(-0.044, 0.928), (0.044, 0.928), (0.044, 1.054), (-0.044, 1.054)], shirt, M['Badge'], 0.011,
                         thickness=0.003, step=0.008)
    out.append(card)
    for name, rect, m in (('Stripe', (-0.044, 1.030, 0.044, 1.054), 'Badge_Stripe'), ('Photo', (-0.033, 0.968, -0.004, 1.018), 'Badge_Photo'),
                          ('Line_0', (0.006, 1.004, 0.034, 1.012), 'Badge_Line'), ('Line_1', (0.006, 0.986, 0.026, 0.994), 'Badge_Line'),
                          ('Line_2', (-0.033, 0.944, 0.033, 0.952), 'Badge_Line')):
        x0, z0, x1, z1 = rect
        out.append(G.decal(f'{prefix}_Badge{name}', [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], W.FRONT(), [card], 0.0012, M[m], step=0.008))
    return out


def _coffee(prefix, M):
    c, down, palm, fwd = _hand_frame('Left')
    base = c + palm * 0.050 + fwd * 0.016 + Vector((0, 0, -0.090))
    k = 1.25                                               # a big 'grande' cup: he needs it
    rows = [(0.0, 0.029, 0), (0.030, 0.0322, 0), (0.030, 0.0342, 1), (0.078, 0.0378, 1), (0.078, 0.0362, 0), (0.112, 0.0392, 0),
            (0.112, 0.0418, 2), (0.122, 0.0418, 2), (0.126, 0.0380, 2), (0.136, 0.0330, 2), (0.138, 0.012, 2)]
    rows = [(h * k, r * k, m) for h, r, m in rows]
    cup = _lathe(prefix + '_Cup', base, (0, 0, 1), rows, [M['Cup'], M['Cup_Sleeve'], M['Cup_Lid']], seg=18)
    sip = G.ellipsoid(prefix + '_Sip', base + Vector((0, -0.030, 0.137 * k)), (0.009, 0.006, 0.004), M['Cup_Lid'], seg=8, rings=4)
    return _held([cup, sip], 'Left')


def old_office(body, face, M, skin):
    out = _rename(T.city_clerk(body, face, M, skin), 'CLERK', 'OLD_OFFICE')
    shirt = next(o for o in out if o.name == 'OLD_OFFICE_Shirt')
    collar = next(o for o in out if o.name == 'OLD_OFFICE_Collar')
    ssrc = C.weight_source([shirt])
    out += [T._t(o, ssrc, C.no_head) for o in _lanyard_badge('OLD_OFFICE', M, shirt, collar)]
    out += T._face(skin, lambda head: W.eye_bags('OLD_OFFICE_EyeBag', M['EyeBags'], head))
    out += _coffee('OLD_OFFICE_Prop', M)
    return out



def _drop_slots(type_id, *slots):
    """TASK-000281: slots of garments a type no longer wears (bald: no hat, no hair)."""
    spec = TYPES[type_id]
    for k in slots:
        spec['slots'].pop(k, None)
        for cw in spec['colourways']:
            cw.pop(k, None)

_drop_slots('OLD_STUDENT', 'Beanie')

BUILDERS = {'OLD_STREAMER': old_streamer, 'OLD_STUDENT': old_student, 'OLD_OFFICE': old_office, 'OLD_VAPER': old_vaper}
