"""Hamlet ('Хутор') NPC pool (TASK-000270): the overloaded granny with a bucket and a live hen, the lazy shepherd
with a straw in his teeth and a crook, the kolkhoz bodybuilder in bib overalls with a milk churn as a dumbbell;
TASK-000278: the grandpa in family boxers, a vest top and felt boots with galoshes, a lopsided ushanka.
Same format as buddy_types.TYPES / BUILDERS; registered through buddy_types.POOLS. No bpy calls at import time.

Hand props are modelled where they hang in the idle pose (world frame, gravity -Z) and mapped back to the hand bone's
T-pose frame (hold()), so the bucket / hen / crook / churn hang straight in the idle stand."""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Хутор'
ALU = ((196, 200, 206), 0.32, 'metal')

TYPES = {
    'HAMLET_GRANNY': dict(
        label='Бабка с хозяйством', group=GROUP, no_ears=True, arm_down=62.0, look=dict(brow=(192, 188, 182)),
        face=dict(Worried=0.35, Happy=0.15),
        slots={'Scarf': ((192, 56, 52), 0.9), 'Scarf_Dots': ((246, 242, 234), 0.9), 'Cardigan': ((122, 86, 66), 1.0),
               'Cardigan_Rib': ((104, 72, 54), 1.0), 'Blouse': ((234, 228, 212), 0.85), 'Buttons': ((238, 230, 214), 0.5),
               'Skirt': ((56, 74, 100), 0.95), 'Apron': ((232, 216, 160), 0.9), 'Apron_Trim': ((196, 74, 64), 0.9),
               'Tights': ((122, 94, 74), 0.85), 'Shoes': ((38, 38, 42), 0.3), 'Blush': ((236, 132, 122), 0.6),
               'Bucket': ((244, 244, 240), 0.22), 'Bucket_Rim': ((44, 76, 156), 0.25), 'Bucket_Handle': ALU,
               'Potato': ((178, 134, 86), 0.9), 'Hen': ((246, 242, 232), 0.9), 'Hen_Wing': ((176, 112, 64), 0.9),
               'Comb': ((222, 40, 40), 0.6), 'Beak': ((242, 184, 42), 0.6), 'Hen_Eye': ((16, 14, 14), 0.2)},
        colourways=[{'Scarf': (56, 94, 162), 'Cardigan': (98, 106, 86), 'Cardigan_Rib': (82, 90, 72), 'Skirt': (92, 42, 48),
                     'Apron': (222, 222, 216), 'Apron_Trim': (56, 94, 162), 'Tights': (92, 86, 82), 'Shoes': (62, 42, 32),
                     'Bucket_Rim': (182, 46, 42), 'Hen': (170, 98, 52), 'Hen_Wing': (112, 60, 34)},
                    {'Scarf': (230, 188, 62), 'Scarf_Dots': (192, 62, 52), 'Cardigan': (152, 62, 68), 'Cardigan_Rib': (130, 52, 58),
                     'Skirt': (42, 42, 46), 'Apron': (198, 222, 198), 'Apron_Trim': (152, 62, 68), 'Tights': (142, 110, 86),
                     'Bucket': (232, 236, 214), 'Bucket_Rim': (52, 112, 72), 'Hen': (60, 58, 62), 'Hen_Wing': (32, 30, 34)}]),
    'HAMLET_SHEPHERD': dict(
        label='Пастух со соломинкой в зубах', group=GROUP, body=dict(thin=1.0), look=dict(skin=(232, 150, 104), brow=(120, 92, 58)),
        face=dict(Blink=0.4, Happy=0.3),
        slots={'Shirt': ((150, 176, 196), 0.9), 'Shirt_Roll': ((132, 158, 180), 0.9), 'Vest': ((136, 92, 56), 0.95),
               'Fur': ((236, 226, 202), 1.0), 'Trousers': ((96, 92, 74), 0.95), 'Patch': ((150, 118, 74), 0.95),
               'Boots': ((40, 44, 40), 0.42), 'Boots_Sole': ((28, 30, 28), 0.6), 'Hat': ((226, 196, 118), 0.9),
               'HatBand': ((150, 52, 44), 0.8), 'Hair': ((150, 112, 66), 0.9), 'Straw': ((240, 214, 104), 0.7),
               'Crook': ((132, 92, 54), 0.75)},
        colourways=[{'Shirt': (198, 92, 78), 'Shirt_Roll': (176, 78, 66), 'Vest': (82, 66, 52), 'Trousers': (62, 70, 88),
                     'Patch': (126, 146, 92), 'Boots': (52, 82, 52), 'HatBand': (44, 62, 112)},
                    {'Shirt': (226, 222, 202), 'Shirt_Roll': (206, 200, 180), 'Vest': (170, 128, 82), 'Fur': (92, 84, 76),
                     'Trousers': (72, 92, 66), 'Patch': (176, 82, 62), 'Hat': (206, 170, 96), 'HatBand': (60, 92, 58)}]),
    'HAMLET_BODYBUILDER': dict(
        label='Колхозный бодибилдер', group=GROUP, body=dict(muscle=1.7), arm_down=64.0,
        look=dict(skin=(222, 136, 90), nose=(208, 116, 80), brow=(70, 50, 38)),
        face=dict(Happy=0.55, Blink=0.2),
        slots={'Denim': ((62, 92, 146), 0.9), 'Denim_Dark': ((48, 72, 118), 0.9), 'Stitch': ((226, 160, 70), 0.8),
               'Clasp': ((206, 208, 212), 0.3, 'metal'), 'Boots': ((36, 38, 40), 0.4), 'Boots_Sole': ((24, 24, 26), 0.6),
               'Hair': ((52, 40, 32), 0.9), 'ChestHair': ((60, 44, 34), 0.95), 'Churn': ALU, 'Churn_Band': ((150, 154, 160), 0.3, 'metal')},
        colourways=[{'Denim': (110, 112, 70), 'Denim_Dark': (88, 90, 56), 'Stitch': (232, 220, 190), 'Boots': (54, 82, 54)},
                    {'Denim': (176, 70, 52), 'Denim_Dark': (146, 56, 42), 'Stitch': (240, 230, 210), 'Boots': (196, 152, 42),
                     'Boots_Sole': (60, 48, 30)}]),
    'HAMLET_BOXERS_GRANDPA': dict(
        label='Дед в семейниках', group=GROUP, body=dict(belly=1.0), arm_down=66.0, no_ears=True, face=dict(Happy=0.6, Blink=0.25),
        look=dict(skin=(238, 160, 120), nose=(232, 120, 96), brow=(220, 216, 208)),
        slots={'Tank': ((240, 238, 230), 0.85), 'Stain': ((196, 180, 140), 0.9), 'Shorts': ((110, 160, 225), 0.8),
               'Print': ((250, 226, 110), 0.7), 'Print2': ((246, 246, 240), 0.7), 'Valenki': ((128, 122, 114), 1.0),
               'Galosh': ((24, 24, 26), 0.3), 'Hat': ((70, 60, 52), 0.95), 'Fur': ((120, 100, 78), 1.0),
               'Mustache': ((226, 222, 214), 0.95), 'Stubble': ((200, 196, 188), 0.95), 'Blush': ((236, 110, 100), 0.6)},
        colourways=[{'Shorts': (200, 50, 50), 'Print': (250, 250, 246), 'Print2': (250, 210, 60)},
                    {'Shorts': (70, 140, 90), 'Print': (250, 200, 210), 'Print2': (250, 250, 246), 'Valenki': (60, 58, 56)}]),
}


# ------------------------------------------------------------------ helpers
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def idle_bone(bone, arm_down=74.0):
    """Armature-space transform the idle stand (buddy_anim.idle_joints, t = 0) applies to an arm-chain bone."""
    import buddy_anim as A
    J = A.idle_joints(0.0, arm_down)
    side = 'Left' if bone.startswith('Left') else 'Right'
    M = Matrix()
    for b in (side + 'Shoulder', side + 'Arm', side + 'ForeArm', side + 'Hand'):
        q = J.get(b)
        if q is not None:
            h = M @ W.bone_rest(b).translation
            M = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
        if b == bone:
            return M
    raise ValueError(bone)


def grip(side, arm_down, rest_pt=None):
    """Idle-pose fist centre of a hand plus its axes: (point, fingers dir, thumb dir)."""
    s = 1 if side == 'Left' else -1
    M = idle_bone(side + 'Hand', arm_down)
    p = M @ Vector(rest_pt or (s * 0.738, -0.004, 1.128))
    R3 = M.to_3x3()
    return p, (R3 @ Vector((s, 0, 0))).normalized(), (R3 @ Vector((0, -1, 0))).normalized()


def hold(objs, side, arm_down):
    """Props modelled in the idle pose -> rigid on <side>Hand at the T-pose (W.to_bone), exported as 'Props'."""
    bone = side + 'Hand'
    local = W.bone_rest(bone).inverted() @ idle_bone(bone, arm_down).inverted()
    return [W.prop(W.to_bone(o, bone, local), bone) for o in objs]


def _rename(objs, prefix):
    for o in objs:
        o.name = prefix + '_' + o.name
    return objs

# ------------------------------------------------------------------ props
def bucket(prefix, M, top_c, r_top=0.118, r_bot=0.090, h=0.215, fill=True):
    """Enamel bucket hanging under a handle apex at top_c (idle world frame): white wall, blue rim and foot band,
    a wire handle, a heap of potatoes."""
    cx, cy = top_c.x, top_c.y
    z_rim = top_c.z - 0.135
    z0 = z_rim - h
    r = lambda z: r_bot + (r_top - r_bot) * (z - z0) / h
    rows = [(z0 + 0.000, r_bot - 0.010, 1), (z0 + 0.004, r_bot, 1), (z0 + 0.026, r(z0 + 0.026), 0), (z_rim - 0.016, r(z_rim - 0.016), 0),
            (z_rim - 0.004, r_top + 0.003, 1), (z_rim + 0.006, r_top + 0.006, 1), (z_rim + 0.010, r_top - 0.006, 1),
            (z_rim - 0.030, r_top - 0.014, 0)]
    secs = [((cx, cy, z), (1, 0, 0), (0, 1, 0), rr, rr) for z, rr, _ in rows]
    mats = [m for _, _, m in rows][:-1]
    ob = G.loft(prefix + '_Bucket', secs, M['Bucket'], seg=20, mat_rows=mats + [0], extra=[M['Bucket_Rim']])
    out = [ob]
    # ears and the wire handle in the front-back plane (the bar runs across the fist)
    pts = []
    for k in range(13):
        a = math.pi * k / 12
        y = -math.cos(a) * (r_top + 0.010)
        z = z_rim - 0.018 + math.sin(a) ** 0.8 * (top_c.z - (z_rim - 0.018))
        pts.append(Vector((cx, cy + y, z)))
    out.append(G.tube(prefix + '_BucketHandle', pts, 0.0045, M['Bucket_Handle'], seg=6))
    for s in (1, -1):
        out.append(G.ellipsoid(f'{prefix}_BucketEar_{s}', (cx, cy + s * (r_top + 0.002), z_rim - 0.020), (0.016, 0.008, 0.016),
                               M['Bucket_Rim'], seg=8, rings=5))
    if fill:
        spots = [(0.0, 0.0, 0.040, 0.012), (0.052, 0.030, 0.034, 0.000), (-0.050, 0.026, 0.036, -0.004), (0.040, -0.048, 0.033, -0.006),
                 (-0.046, -0.040, 0.035, -0.002), (0.004, 0.064, 0.032, -0.010)]
        for k, (dx, dy, rr, dz) in enumerate(spots):
            out.append(G.ellipsoid(f'{prefix}_Potato_{k}', (cx + dx, cy + dy, z_rim - 0.004 + dz),
                                   (rr * 1.15, rr, rr * 0.85), M['Potato'], rot=Matrix.Rotation(k * 1.3, 3, 'Z'), seg=8, rings=6))
    return out


def hen_upside_down(prefix, M, feet_c, facing=Vector((0, -1, 0))):
    """Live hen carried by the feet, head down, wings flapping: modelled standing (feet at the origin, facing -Y),
    then flipped and hung from feet_c."""
    parts = []
    for s in (1, -1):
        x = s * 0.024
        parts.append(G.tube(f'{prefix}_HenLeg_{s}', [(x, 0.004, -0.030), (x, 0.004, 0.030), (x, 0.010, 0.085)], 0.0075, M['Beak'], seg=6))
        for k, ang in enumerate((-35, 0, 35)):
            d = Vector((math.sin(math.radians(ang)), -math.cos(math.radians(ang)), 0.25))
            parts.append(G.tube(f'{prefix}_HenToe_{s}_{k}', [(x, 0.004, -0.030), Vector((x, 0.004, -0.030)) + d * 0.040], 0.0055, M['Beak'], seg=5))
    parts.append(G.ellipsoid(prefix + '_HenBody', (0, 0.012, 0.165), (0.082, 0.120, 0.090), M['Hen'], seg=14, rings=10))
    parts.append(G.ellipsoid(prefix + '_HenBreast', (0, -0.060, 0.185), (0.066, 0.060, 0.072), M['Hen'], seg=12, rings=8))
    parts.append(G.tube(prefix + '_HenNeck', [(0, -0.070, 0.215), (0, -0.098, 0.262), (0, -0.104, 0.292)], lambda i, n: (0.040, 0.034, 0.030)[i],
                        M['Hen'], seg=10))
    parts.append(G.ellipsoid(prefix + '_HenHead', (0, -0.108, 0.306), (0.034, 0.040, 0.036), M['Hen'], seg=12, rings=8))
    parts.append(G.tube(prefix + '_HenBeak', [(0, -0.142, 0.304), (0, -0.172, 0.297)], lambda i, n: (0.012, 0.002)[i], M['Beak'], seg=6))
    for k, (y, z, r) in enumerate(((-0.124, 0.344, 0.013), (-0.104, 0.350, 0.015), (-0.084, 0.343, 0.013))):
        parts.append(G.ellipsoid(f'{prefix}_HenComb_{k}', (0, y, z), (0.006, r, r * 1.1), M['Comb'], seg=8, rings=6))
    parts.append(G.ellipsoid(prefix + '_HenWattle', (0, -0.142, 0.276), (0.007, 0.010, 0.016), M['Comb'], seg=8, rings=6))
    for s in (1, -1):
        parts.append(G.ellipsoid(f'{prefix}_HenEye_{s}', (s * 0.031, -0.122, 0.314), (0.006, 0.008, 0.009), M['Hen_Eye'], seg=8, rings=6))
        # wings spread (flapping), feathers on the tips in the wing colour
        rot = Matrix.Rotation(math.radians(-s * 58), 3, 'Y') @ Matrix.Rotation(math.radians(10), 3, 'X')
        parts.append(G.ellipsoid(f'{prefix}_HenWing_{s}', Vector((s * 0.115, 0.020, 0.180)), (0.075, 0.095, 0.016), M['Hen_Wing'],
                                 rot=rot, seg=12, rings=8))
    for k, (ang, ln) in enumerate(((-26, 0.080), (0, 0.095), (26, 0.080))):
        rot = Matrix.Rotation(math.radians(ang), 3, 'Y') @ Matrix.Rotation(math.radians(-38), 3, 'X')
        parts.append(G.ellipsoid(f'{prefix}_HenTail_{k}', Vector((math.sin(math.radians(ang)) * 0.03, 0.125, 0.235)), (0.020, 0.030, ln),
                                 M['Hen_Wing'] if k != 1 else M['Hen'], rot=rot, seg=8, rings=6))
    # flip: feet up, head down; face the requested direction; hang the shanks in the fist
    yaw = Vector((0, -1, 0)).rotation_difference(Vector((facing.x, facing.y, 0)).normalized()).to_matrix().to_4x4()
    flip = Matrix.Rotation(math.pi, 4, 'Y')
    m = Matrix.Translation(feet_c) @ yaw @ flip @ Matrix.Translation((0, -0.006, -0.040))
    for o in parts:
        o.data.transform(m); o.data.update()
    return parts


def crook(prefix, material, fist, top=1.80, hook_r=0.062, out_dir=Vector((-1, 0, 0))):
    """Shepherd's crook standing on the floor through the fist: straight staff, a hook curling outward at the top."""
    x, y = fist.x, fist.y
    staff = [Vector((x, y, 0.012)), Vector((x, y, 0.40)), Vector((x, y, 0.90)), Vector((x, y, top))]
    d = Vector((out_dir.x, out_dir.y, 0)).normalized()
    c = Vector((x, y, top)) + d * hook_r
    hook = []
    for k in range(1, 12):
        a = math.pi * k / 10.5
        hook.append(c - d * (hook_r * math.cos(a)) + Vector((0, 0, hook_r * math.sin(a) * 1.05)))
    hook.append(hook[-1] + Vector((0, 0, -0.030)) + d * 0.004)
    pts = staff + hook
    return [G.tube(prefix + '_Crook', pts, lambda i, n: 0.0150 if i < len(staff) else 0.0135, material, seg=8),
            G.ellipsoid(prefix + '_CrookTip', (x, y, 0.014), (0.017, 0.017, 0.012), material, seg=8, rings=5)]


def churn(prefix, M, top_c):
    """40 l aluminium milk churn hanging from its lid handle (top_c = fist centre): cylinder with two raised hoops,
    shoulder, neck, mushroom lid, two side handles."""
    cx, cy = top_c.x, top_c.y
    z_top = top_c.z - 0.030
    prof = [(0.000, 0.110), (0.006, 0.124), (0.020, 0.130), (0.050, 0.130), (0.056, 0.137), (0.072, 0.137), (0.078, 0.130),
            (0.270, 0.130), (0.276, 0.137), (0.292, 0.137), (0.298, 0.130), (0.330, 0.128), (0.370, 0.110), (0.400, 0.082),
            (0.440, 0.074), (0.456, 0.074), (0.462, 0.090), (0.478, 0.092), (0.492, 0.086), (0.506, 0.060), (0.512, 0.030)]
    hgt = prof[-1][0]
    z0 = z_top - hgt
    band = {4, 5, 11, 12, 15, 16, 17}
    secs = [((cx, cy, z0 + z), (1, 0, 0), (0, 1, 0), r, r) for z, r in prof]
    mats = [1 if k in band else 0 for k in range(len(prof) - 1)]
    body = G.loft(prefix + '_Churn', secs, M['Churn'], seg=20, mat_rows=mats, extra=[M['Churn_Band']])
    out = [body]
    # lid handle: a bar the fist closes round
    out.append(G.tube(prefix + '_ChurnGrip', [(cx, cy - 0.040, z_top - 0.004), (cx, cy - 0.034, z_top + 0.026), (cx, cy + 0.034, z_top + 0.026),
                                              (cx, cy + 0.040, z_top - 0.004)], 0.0085, M['Churn_Band'], seg=6))
    for s in (1, -1):
        zc = z0 + 0.335
        pts = [Vector((cx + s * 0.124, cy - 0.034, zc - 0.012)), Vector((cx + s * 0.158, cy - 0.030, zc + 0.006)),
               Vector((cx + s * 0.162, cy, zc + 0.012)), Vector((cx + s * 0.158, cy + 0.030, zc + 0.006)), Vector((cx + s * 0.124, cy + 0.034, zc - 0.012))]
        out.append(G.tube(f'{prefix}_ChurnEar_{s}', pts, 0.0090, M['Churn_Band'], seg=6))
    return out


def straw(prefix, material, start, end, seed_head=True):
    """Grass stalk held in the mouth corner (rigid on the head)."""
    a, b = Vector(start), Vector(end)
    mid = a.lerp(b, 0.55) + Vector((0, 0, 0.012))
    out = [G.tube(prefix + '_Straw', [a, mid, b], lambda i, n: (0.0042, 0.0036, 0.0028)[i], material, seg=6)]
    if seed_head:
        d = (b - mid).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix()
        out.append(G.ellipsoid(prefix + '_StrawHead', b + d * 0.018, (0.0065, 0.0065, 0.024), material, rot=rot, seg=8, rings=6))
    return [W.prop(o, 'Head') for o in out]

# ------------------------------------------------------------------ granny
def hamlet_granny(body, face, M, skin):
    """T.village_grandma's outfit (headscarf, cardigan, blouse, skirt, apron, tights, galoshes, blush) with a lighter
    apron decal, plus the farm load: enamel bucket of potatoes in the left hand, a live hen by the feet in the right."""
    pre = 'HAMLET_GRANNY'
    src = C.weight_source([body])
    out = W.headscarf(pre, M['Scarf'], M['Scarf_Dots'])
    cardigan = W.top(pre + '_Cardigan', T.CARDIGAN, 7, T.CARDIGAN_SLEEVE, (.776, .206, .142, -.012), [M['Cardigan'], M['Cardigan_Rib']],
                     row_mat=[1] + [0] * (len(T.CARDIGAN) - 2), sleeve_mat=[0] * 7 + [1] * 3, hem_mat=1)
    _t(cardigan, src, C.no_head)
    csrc = C.weight_source([cardigan])
    deco = [W.front_decal(pre + '_Blouse', [(-0.062, 1.258), (0.062, 1.258), (0.0, 1.110)], cardigan, M['Blouse'], 0.0025, step=0.008)]
    deco += W.buttons(pre + '_Btn', cardigan, M['Buttons'], [(0.0, z) for z in (1.075, 1.000, 0.925, 0.850)], r=0.010)
    for s in (1, -1):
        deco.append(W.front_decal(f'{pre}_Pocket_{s}', [(s * 0.075, 0.790), (s * 0.165, 0.790), (s * 0.165, 0.880), (s * 0.075, 0.880)][::s],
                                  cardigan, M['Cardigan_Rib'], 0.003, thickness=0.004))
    out += [cardigan] + [_t(o, csrc) for o in deco]
    sk = W.skirt(pre + '_Skirt', M['Skirt'])
    apron = W.front_decal(pre + '_Apron', [(-0.150, 0.880), (0.150, 0.880), (0.168, 0.520), (0.150, 0.470), (0.100, 0.455), (-0.100, 0.455),
                                           (-0.150, 0.470), (-0.168, 0.520)], sk, M['Apron'], 0.004, thickness=0.004, step=0.026)
    apk = G.decal(pre + '_ApronPocket', [(-0.070, 0.580), (0.070, 0.580), (0.070, 0.650), (-0.070, 0.650)], W.FRONT(), [apron], 0.0025,
                  M['Apron_Trim'], thickness=0.003, step=0.020)
    ssrc = C.weight_source([sk])
    out += [sk, _t(apron, ssrc), _t(apk, ssrc)]
    out.append(_t(W.bottoms(pre + '_Tights', W.LEGS_TIGHTS, [M['Tights']]), src))
    out += W.shoes(pre + '_Galosh', M['Shoes'], M['Shoes'])
    out += T._face(skin, lambda head: W.blush(pre + '_Blush', M['Blush'], head))
    # the farm load
    ad = TYPES['HAMLET_GRANNY']['arm_down']
    gl, _, _ = grip('Left', ad)
    out += hold(bucket(pre, M, gl), 'Left', ad)
    gr, _, _ = grip('Right', ad)
    out += hold(hen_upside_down(pre, M, gr, facing=Vector((-0.5, -1, 0))), 'Right', ad)
    return out

# ------------------------------------------------------------------ shepherd
HAT_BASE = W.zprofile([(0, 1.678), (90, 1.664), (180, 1.650)])


def straw_hat(prefix, hat_m, band_m, brim_w=0.175):
    rows = [('fit', HAT_BASE, 0.006), (1.712, 0.153, 0.149, 0.0, 0.010), (1.722, 0.153, 0.149, 0.0, 0.010),
            (1.772, 0.146, 0.142, 0.0, 0.006), (1.800, 0.122, 0.118, 0.0, 0.004), (1.810, 0.050, 0.048, 0.0, 0.002)]
    crown = W.ring_loft(prefix + '_HatCrown', rows, [hat_m, band_m], row_mat=[1, 0, 0, 0, 0], seg=32)
    seg = 40
    vs, fs = [], []
    rings = [[] for _ in range(4)]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        p0, _ = W.head_at(phi, HAT_BASE(phi), 0.006)
        out = Vector((math.sin(phi), -math.cos(phi), 0))
        wave = 0.010 * math.sin(3 * phi + 0.6)                    # floppy, uneven straw brim
        rag = 0.008 * (j % 2)
        for k, (w, dz) in enumerate(((0.0, 0.0), (0.06, -0.010), (0.13, -0.020 + wave * 0.5), (brim_w + rag, -0.016 + wave))):
            rings[k].append(len(vs)); vs.append(p0 + out * w + Vector((0, 0, dz)))
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    brim = G.from_data(prefix + '_HatBrim', vs, fs, hat_m, True, fix_normals=False)
    G.solidify(brim, 0.007, offset=0.0)
    return [C.rigid(o, 'Head') for o in (crown, brim)]


def shaggy_hair(prefix, material):
    """Straw-coloured hair sticking out under the hat at the back and over the ears, ragged ends."""
    lo = lambda phi: W.h_of(1.505 + 0.050 * max(0.0, math.cos(phi)) ** 2) - 0.010 * abs(2 * ((math.degrees(phi) / 10.0) % 1.0) - 1)
    hi = lambda phi: HAT_BASE(phi) + 0.004
    ob, _ = W.shell(prefix + '_Hair', material, lo, hi, off=lambda phi, u: 0.006 + 0.010 * (1 - u), thick=0.007, seg=30, rows=3,
                    arc=(math.radians(62), math.radians(298)))
    return [C.rigid(ob, 'Head')]


SHIRT_SLEEVE = [(.212, .074), (.25, .069), (.30, .064), (.36, .060), (.42, .057), (.455, .056), (.462, .062), (.480, .064),
                (.496, .062), (.500, .052)]
VEST = [(.770, .214, .150, -.012), (.784, .216, .152, -.012), (.86, .214, .150, -.013), (.94, .214, .150, -.012),
        (1.02, .215, .151, -.008), (1.08, .219, .157, -.002), (1.10, .221, .161, 0.0), (1.17, .219, .166, .002),
        (1.235, .207, .170, .002), (1.250, .183, .175, .002), (1.262, .173, .172, .002), (1.266, .167, .166, 0.0),
        (1.258, .163, .160, 0.0)]              # arm row 5


def _vest_gap(z):
    return 0.030 + 0.070 * W.smoothstep(0.95, 1.24, z)


def hamlet_shepherd(body, face, M, skin):
    pre = 'HAMLET_SHEPHERD'
    src = C.weight_source([body])
    shirt = W.top(pre + '_Shirt', C.BASE_TEE_ROWS, 6, SHIRT_SLEEVE, (.806, .184, .124, -.004), [M['Shirt'], M['Shirt_Roll']],
                  sleeve_mat=[0] * 5 + [1] * 5)
    _t(shirt, src, C.no_head)
    ssrc = C.weight_source([shirt])
    out = [shirt, _t(W.collar(pre + '_Collar', M['Shirt'], open_deg=34, tip=0.030), ssrc, C.no_head)]
    out += [_t(o, ssrc) for o in W.buttons(pre + '_Btn', shirt, M['Shirt_Roll'], [(0.0, z) for z in (1.150, 1.060, 0.970, 0.880)], r=0.008)]
    # sheepskin vest, open at the front, fur trim on the opening and a fur collar
    cut = lambda p: p.y < 0 and abs(p.x) < _vest_gap(p.z)
    vest = W.top(pre + '_Vest', VEST, 5, None, (.784, .206, .144, -.012), [M['Vest'], M['Fur']], hem_mat=1, cut=cut)
    G.solidify(vest, 0.005, offset=1.0)
    _t(vest, src, C.no_head)
    vsrc = C.weight_source([vest])
    trims = []
    for s in (1, -1):
        pts = []
        for z in (0.778, 0.82, 0.88, 0.94, 1.00, 1.06, 1.12, 1.17, 1.21, 1.240):
            r = W.lerp_row(VEST, z)
            x = _vest_gap(z) + 0.004
            a = math.asin(max(-1.0, min(1.0, x / r[1])))
            pts.append(Vector((s * x, r[3] - r[2] * math.cos(a) - 0.004, z)))
        trims.append(G.tube(f'{pre}_FurTrim_{s}', pts, 0.013, M['Fur'], seg=8))
    collar = W.collar(pre + '_FurCollar', M['Fur'], z0=1.262, r0=(0.168, 0.165), z1=1.292, r1=(0.176, 0.172), z2=1.240,
                      r2=(0.206, 0.198), open_deg=36, tip=0.020, thick=0.014)
    out += [vest, _t(collar, vsrc, C.no_head)] + [_t(o, vsrc, C.no_head) for o in trims]
    # patched trousers tucked into rubber boots
    pants = _t(W.bottoms(pre + '_Trousers', W.LEGS_TUCKED, [M['Trousers']]), src)
    patches = [W.front_decal(pre + '_Patch_0', [(0.060, 0.470), (0.134, 0.462), (0.140, 0.540), (0.066, 0.548)], pants, M['Patch'], 0.003,
                             thickness=0.003, step=0.012),
               W.front_decal(pre + '_Patch_1', [(-0.140, 0.640), (-0.080, 0.646), (-0.084, 0.700), (-0.142, 0.694)], pants, M['Patch'], 0.003,
                             thickness=0.003, step=0.012),
               G.decal(pre + '_Patch_2', [(-0.120, 0.700), (-0.030, 0.706), (-0.034, 0.780), (-0.118, 0.774)], W.BACK(), [pants], 0.003,
                       M['Patch'], thickness=0.003, step=0.014)]
    psrc = C.weight_source([pants])
    out += [pants] + [_t(o, psrc) for o in patches]
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts(pre + '_Boot', M['Boots'])
    out += straw_hat(pre, M['Hat'], M['HatBand'])
    out += shaggy_hair(pre, M['Hair'])
    # props: straw in the right mouth corner, crook in the right hand
    out += straw(pre, M['Straw'], (-0.026, -0.118, 1.412), (-0.190, -0.236, 1.452))
    ad = TYPES['HAMLET_SHEPHERD'].get('arm_down', 74.0)
    gr, _, _ = grip('Right', ad)
    out += hold(crook(pre, M['Crook'], gr, out_dir=Vector((-0.6, -0.8, 0))), 'Right', ad)
    return out

# ------------------------------------------------------------------ bodybuilder
def hamlet_bodybuilder(body, face, M, skin):
    pre = 'HAMLET_BODYBUILDER'
    src = C.weight_source([body])
    pants = _t(W.bottoms(pre + '_Denim', W.LEGS_TUCKED, [M['Denim']]), src)
    out = [pants]
    # bib on the bare chest, straps over the shoulders crossing on the back
    bib = W.front_decal(pre + '_Bib', [(-0.118, 0.850), (0.118, 0.850), (0.112, 1.090), (-0.112, 1.090)], body, M['Denim'], 0.006,
                        thickness=0.006, step=0.020)
    _t(bib, src, C.no_head)
    bsrc = C.weight_source([bib])
    deco = [G.decal(pre + '_BibPocket', [(-0.070, 0.960), (0.070, 0.960), (0.066, 1.050), (-0.066, 1.050)], W.FRONT(), [bib], 0.002,
                    M['Denim_Dark'], thickness=0.003, step=0.020),
            G.decal(pre + '_BibStitch', [(-0.070, 1.050), (0.070, 1.050), (0.070, 1.058), (-0.070, 1.058)], W.FRONT(), [bib], 0.0045,
                    M['Stitch'], step=0.020)]
    out += [bib] + [_t(o, bsrc) for o in deco]
    bvh = G.bvh_of([body])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    for s in (1, -1):
        raw = [(0.094, -0.150, 1.080), (0.112, -0.132, 1.140), (0.134, -0.090, 1.188), (0.148, -0.030, 1.206), (0.146, 0.030, 1.200),
               (0.126, 0.090, 1.166), (0.080, 0.122, 1.090), (0.000, 0.126, 1.000), (-0.070, 0.124, 0.920), (-0.090, 0.124, 0.872)]
        pts = [on(Vector((s * x, y, z)), 0.007)[0] for x, y, z in raw]
        st = C.strap(f'{pre}_Strap_{s}', pts, M['Denim'], width=0.040, thick=0.006, normal_fn=lambda q: on(q, 0.0)[1])
        out.append(_t(st, src, C.no_head))
        clasp_p, n = on(Vector((s * 0.096, -0.150, 1.080)), 0.016)
        cl = G.ellipsoid(f'{pre}_Clasp_{s}', clasp_p, (0.018, 0.007, 0.014), M['Clasp'], seg=10, rings=6)
        out.append(_t(cl, src, C.no_head))
        bt = G.ellipsoid(f'{pre}_HipButton_{s}', on(Vector((s * 0.150, -0.110, 0.872)), 0.012)[0], (0.012, 0.006, 0.012), M['Clasp'],
                         seg=10, rings=6)
        out.append(_t(bt, src))
    # chest hair tuft peeking over the bib
    hair = W.front_decal(pre + '_ChestHair', W.blob(0.0, 1.122, 0.030, n=14, seed=11, rough=0.6, sx=1.4), body, M['ChestHair'], 0.003,
                         step=0.012)
    out.append(_t(hair, src, C.no_head))
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts(pre + '_Boot', M['Boots'])
    ad = TYPES['HAMLET_BODYBUILDER']['arm_down']
    gr, _, _ = grip('Right', ad)
    out += hold(churn(pre, M, gr), 'Right', ad)
    return out


# ------------------------------------------------------------------ mushroom picker (TASK-000276)
def _mushroomer_spec():
    """The old mushroom picker back in the hamlet as he was: buddy_pool_forest's FOREST_MUSHROOMER slots and builder."""
    import buddy_pool_forest as F
    spec = dict(F.TYPES['FOREST_MUSHROOMER'])
    spec['group'] = GROUP
    return spec


def hamlet_mushroomer(body, face, M, skin):
    import buddy_pool_forest as F
    return F.mushroomer(body, face, M, skin)


TYPES['HAMLET_MUSHROOMER'] = _mushroomer_spec()


# ------------------------------------------------------------------ grandpa in family boxers (TASK-000278)
LEGS_BOXERS = [(.70, .100), (.65, .110), (.60, .117), (.565, .120), (.552, .114)]     # wide 'family' boxers to mid-thigh


def lopsided_ushanka(prefix, M):
    """Fur hat with one ear flap hanging down over the left ear and the right one sticking out sideways like a wing."""
    crown = W.beanie(prefix + '_Crown', M['Hat'])
    h = W.h_of(1.668)
    band = [W.head_at(2 * math.pi * k / 32, h, 0.026)[0] for k in range(33)]
    out = crown + [C.rigid(G.tube(prefix + '_Band', band, 0.026, M['Fur'], seg=10, caps=False), 'Head')]
    down = Matrix.Rotation(math.radians(8), 3, 'Y')
    out.append(C.rigid(G.ellipsoid(prefix + '_FlapDown', (0.158, 0.010, 1.560), (0.022, 0.070, 0.088), M['Fur'], rot=down,
                                   seg=14, rings=8), 'Head'))
    wing = Matrix.Rotation(math.radians(-24), 3, 'Y')
    out.append(C.rigid(G.ellipsoid(prefix + '_FlapUp', (-0.205, 0.010, 1.668), (0.078, 0.062, 0.018), M['Fur'], rot=wing,
                                   seg=14, rings=8), 'Head'))
    out.append(C.rigid(G.ellipsoid(prefix + '_FrontFlap', (0.0, -0.152, 1.708), (0.118, 0.020, 0.050), M['Fur'], seg=16, rings=8), 'Head'))
    return out


def hamlet_boxers_grandpa(body, face, M, skin):
    import buddy_pool_oldtown2 as O2
    pre = 'HAMLET_BOXERS_GRANDPA'
    src = C.weight_source([body])
    tank = [_t(o, src, C.no_head) for o in W.tank_top(pre + '_Tank', M['Tank'], body)]
    stain = W.front_decal(pre + '_Stain', W.blob(0.050, 0.980, 0.030, seed=91, rough=0.45), tank[0], M['Stain'], 0.0030)
    out = tank + [_t(stain, C.weight_source([tank[0]]))]
    shorts = _t(W.bottoms(pre + '_Shorts', LEGS_BOXERS, [M['Shorts']]), src)
    flowers = []
    spots = [(0.070, 0.690), (0.140, 0.620), (0.040, 0.590), (0.120, 0.760), (-0.060, 0.700), (-0.130, 0.640), (-0.050, 0.600),
             (-0.120, 0.770), (0.000, 0.800)]
    for k, (x, z) in enumerate(spots):
        slot = 'Print' if k % 2 == 0 else 'Print2'
        flowers.append(W.front_decal(f'{pre}_FlowerF_{k}', O2._flower_outline(x, z, 0.020, rot=0.4 * k), shorts, M[slot], 0.0030, step=0.008))
        flowers.append(G.decal(f'{pre}_FlowerB_{k}', O2._flower_outline(-x, z + 0.010, 0.020, rot=0.3 * k), W.BACK(), [shorts], 0.0030,
                               M[slot], step=0.008))
    out += [shorts] + T._decal_t(flowers, shorts)
    out += W.shoes(pre + '_Valenok', M['Valenki'], M['Galosh']) + W.boot_shafts(pre + '_Valenok', M['Valenki'], top=0.42)
    out += lopsided_ushanka(pre + '_Ushanka', M)
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.016, size=1.6)
    out += T._face(skin, lambda head: W.blush(pre + '_Blush', M['Blush'], head) + W.stubble(pre + '_Stubble', M['Stubble'], head))
    return out



def _drop_slots(type_id, *slots):
    """TASK-000281: slots of garments a type no longer wears (bald: no hat, no hair)."""
    spec = TYPES[type_id]
    for k in slots:
        spec['slots'].pop(k, None)
        for cw in spec['colourways']:
            cw.pop(k, None)

_drop_slots('HAMLET_BODYBUILDER', 'Hair')

BUILDERS = {'HAMLET_GRANNY': hamlet_granny, 'HAMLET_SHEPHERD': hamlet_shepherd, 'HAMLET_BODYBUILDER': hamlet_bodybuilder, 'HAMLET_MUSHROOMER': hamlet_mushroomer, 'HAMLET_BOXERS_GRANDPA': hamlet_boxers_grandpa}
