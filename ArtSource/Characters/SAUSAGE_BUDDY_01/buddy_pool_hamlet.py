"""Hamlet ('Хутор') NPC pool (TASK-000270): the granny (TASK-000510: the village fashionista, v03), the kolkhoz bodybuilder in
bib overalls with a milk churn as a dumbbell; TASK-000509: the shepherd remade as the village fool (v03) and the grandpa
in family boxers and a vest top as the accordion player (v02, kartuz and garmon); the simpleton (plain BASE) left the pool.
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
        label='Бабка-модница', group=GROUP, no_ears=True, hand_props=True, body=dict(belly=0.8), arm_down=66.0,
        look=dict(brow=(192, 188, 182), mouth=(196, 30, 60)), face=dict(Happy=0.75, Blink=0.2),
        slots={'Scarf': ((206, 30, 44), 0.9), 'Scarf_Rose': ((250, 236, 214), 0.9), 'Scarf_Rose_2': ((252, 200, 50), 0.9),
               'Scarf_Rose_Heart': ((150, 20, 40), 0.9), 'Scarf_Leaf': ((40, 120, 60), 0.9),
               'Dress': ((50, 176, 186), 0.8), 'Dress_Flower': ((250, 120, 170), 0.8), 'Dress_Flower_2': ((255, 226, 80), 0.8),
               'Dress_Flower_Heart': ((246, 246, 240), 0.8), 'Coat': ((52, 70, 58), 0.95), 'Stitch': ((36, 50, 42), 0.95),
               'Track': ((36, 52, 120), 0.8), 'Stripes': ((246, 246, 240), 0.8), 'Socks': ((150, 146, 140), 1.0),
               'Galosh': ((30, 64, 44), 0.18), 'Glasses': ((214, 26, 50), 0.2), 'Gem': ((236, 242, 252), 0.05),
               'Mole': ((120, 78, 56), 0.6), 'Mole_Hair': ((40, 34, 30), 0.9), 'Blush': ((236, 120, 120), 0.6),
               'Bucket': ((244, 244, 240), 0.22), 'Bucket_Rim': ((44, 76, 156), 0.25), 'Bucket_Handle': ALU,
               'Potato': ((178, 134, 86), 0.9), 'Hen': ((246, 242, 232), 0.9), 'Hen_Wing': ((176, 112, 64), 0.9),
               'Comb': ((222, 40, 40), 0.6), 'Beak': ((242, 184, 42), 0.6), 'Hen_Eye': ((16, 14, 14), 0.2),
               'Net': ((232, 112, 36), 0.9), 'Milk': ((246, 246, 242), 0.25), 'Milk_Cap': ((40, 140, 70), 0.3),
               'Loaf': ((200, 140, 74), 0.8), 'Loaf_Cut': ((236, 196, 130), 0.85), 'Onion': ((206, 146, 70), 0.6)},
        colourways=[{'Scarf': (40, 80, 160), 'Dress': (236, 120, 60), 'Coat': (60, 60, 66), 'Stitch': (44, 44, 50), 'Track': (120, 30, 40),
                     'Glasses': (120, 40, 160)},
                    {'Scarf': (240, 196, 40), 'Scarf_Rose': (206, 30, 44), 'Dress': (150, 80, 170), 'Coat': (90, 70, 50), 'Stitch': (70, 54, 38),
                     'Track': (30, 30, 34), 'Glasses': (40, 40, 44)}]),
    'HAMLET_SHEPHERD': dict(
        label='Пастух-дурачок', group=GROUP, body=dict(thin=0.8, belly=0.45), look=dict(skin=(236, 160, 116), brow=(196, 150, 80)),
        face=dict(Blink_L=0.55, Surprised=0.4, Happy=0.35), own_eyes=True,
        slots={'Shirt': ((204, 96, 72), 0.9), 'Shirt_Roll': ((184, 84, 62), 0.9), 'Buttons': ((236, 226, 200), 0.5),
               'Trousers': ((96, 112, 146), 0.95), 'Patch': ((222, 196, 90), 0.95), 'Patch_2': ((120, 160, 90), 0.95),
               'Suspenders': ((122, 82, 50), 0.6), 'Clip': ALU, 'Boots': ((40, 44, 40), 0.42), 'Boots_Sole': ((28, 30, 28), 0.6),
               'Sock': ((196, 190, 176), 1.0), 'Sock_Rim': ((150, 142, 128), 1.0), 'Hat': ((206, 172, 100), 0.95),
               'HatBand': ((150, 120, 70), 0.95), 'Hair': ((218, 176, 92), 0.9), 'Tongue': ((226, 112, 120), 0.4),
               'Tongue_Groove': ((176, 74, 84), 0.5), 'Freckles': ((196, 112, 70), 0.8), 'Snot': ((214, 236, 226), 0.05),
               'Daisy': ((248, 248, 244), 0.7), 'Daisy_Eye': ((250, 204, 40), 0.6), 'Daisy_Stem': ((90, 150, 60), 0.7),
               'Straw': ((240, 214, 104), 0.7), 'Crook': ((132, 92, 54), 0.75)},
        colourways=[{'Shirt': (120, 150, 190), 'Shirt_Roll': (104, 132, 172), 'Trousers': (110, 96, 74), 'Patch': (200, 70, 60),
                     'Suspenders': (40, 40, 44), 'Hair': (120, 84, 50)},
                    {'Shirt': (226, 210, 120), 'Shirt_Roll': (206, 190, 104), 'Trousers': (70, 80, 64), 'Patch': (90, 130, 190),
                     'Patch_2': (220, 120, 60), 'Hair': (238, 214, 150)}]),
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
        label='Дед-гармонист', group=GROUP, body=dict(belly=1.0), arm_down=66.0, face=dict(Happy=0.7, Surprised=0.25, Blink=0.2),
        look=dict(skin=(238, 160, 120), nose=(232, 120, 96), brow=(220, 216, 208)),
        slots={'Tank': ((240, 238, 230), 0.85), 'Stain': ((196, 180, 140), 0.9), 'Shorts': ((110, 160, 225), 0.8),
               'Print': ((250, 226, 110), 0.7), 'Print2': ((246, 246, 240), 0.7), 'Valenki': ((128, 122, 114), 1.0),
               'Galosh': ((24, 24, 26), 0.3), 'Cap': ((52, 56, 66), 0.85), 'CapBand': ((40, 42, 50), 0.85),
               'Visor': ((16, 16, 18), 0.15), 'Flower': ((220, 30, 40), 0.6), 'Leaf': ((60, 130, 60), 0.7),
               'Hair': ((226, 222, 214), 0.95), 'Mustache': ((226, 222, 214), 0.95), 'Stubble': ((200, 196, 188), 0.95),
               'Blush': ((236, 110, 100), 0.6), 'Garmon_Wood': ((34, 28, 28), 0.3), 'Garmon_Bellows': ((196, 36, 44), 0.7),
               'Garmon_Fold': ((30, 26, 26), 0.6), 'Garmon_Metal': ((206, 208, 214), 0.25, 'metal'),
               'Garmon_Button': ((242, 236, 220), 0.35), 'Garmon_Strap': ((110, 70, 40), 0.6)},
        colourways=[{'Shorts': (200, 50, 50), 'Print': (250, 250, 246), 'Print2': (250, 210, 60), 'Garmon_Bellows': (40, 90, 170)},
                    {'Shorts': (70, 140, 90), 'Print': (250, 200, 210), 'Print2': (250, 250, 246), 'Valenki': (60, 58, 56),
                     'Cap': (120, 100, 70), 'Garmon_Wood': (120, 40, 30)}]),
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


# ------------------------------------------------------------------ granny
COAT = [(.660, .246, .176, -.012), (.676, .248, .178, -.012), (.74, .240, .172, -.013), (.80, .230, .164, -.013),
        (.86, .220, .156, -.013), (.94, .214, .150, -.012)] + [r for r in W.JACKET if r[0] >= 1.02]   # long flared telogreika


DRESS_KNEE = [(0.892, 0.186, 0.127, -0.004), (0.86, 0.193, 0.132, -0.006), (0.80, 0.207, 0.143, -0.008), (0.70, 0.224, 0.158, -0.010),
              (0.60, 0.236, 0.168, -0.010), (0.50, 0.244, 0.176, -0.010), (0.445, 0.247, 0.179, -0.010), (0.452, 0.239, 0.171, -0.010)]
TRACK_INTO_SOCKS = [(.70, .084), (.60, .082), (.50, .078), (.43, .075), (.36, .071), (.31, .066), (.27, .058), (.26, .052)]


def _coat_gap(z):
    return 0.052 + 0.040 * G.smoothstep(0.75, 1.25, z)


def _flower_decals(prefix, target, M, spots, petal_slots, centre_slot, leaf_slot=None):
    """Big flowers (and leaves) printed on a garment: spots = [(axes, cx, cz, r, rot)]."""
    import buddy_pool_oldtown2 as O2
    out = []
    for k, (axes, cx, cz, r, rot) in enumerate(spots):
        if leaf_slot:
            ang = rot * 2.0 + 2.3
            lx, lz = cx + math.cos(ang) * r * 0.95, cz + math.sin(ang) * r * 0.95
            out.append(G.decal(f'{prefix}_Leaf_{k}', O2._leaf_outline(lx, lz, r * 1.4, r * 0.7, ang), axes, [target], 0.0022, M[leaf_slot],
                               step=0.020))
        out.append(G.decal(f'{prefix}_Petals_{k}', O2._flower_outline(cx, cz, r, rot), axes, [target], 0.0034,
                           M[petal_slots[k % len(petal_slots)]], step=0.016))
        out.append(G.decal(f'{prefix}_Centre_{k}', C.ellipse(cx, cz, r * 0.30, r * 0.30, 8), axes, [target], 0.0046, M[centre_slot], step=0.05))
    return out


def rose_headscarf(prefix, M):
    """The babushka headscarf in Pavlovo Posad style: red with big cream and yellow roses and green leaves instead of the
    polka dots of W.headscarf."""
    parts = W.headscarf(prefix, M['Scarf'], M['Scarf_Rose'])
    scarf, keep = parts[0], []
    for o in parts:
        if '_Dot' in o.name:
            bpy.data.objects.remove(o)
        else:
            keep.append(o)
    spots = [(G.SIDE(s), u * s, v, r, rot) for s in (1, -1) for (u, v, r, rot) in ((-0.050, 1.420, 0.030, 0.2), (0.010, 1.560, 0.026, 0.9),
                                                                                 (-0.085, 1.600, 0.022, 0.5))]
    spots += [(G.BACK(), u, v, r, rot) for (u, v, r, rot) in ((0.0, 1.420, 0.034, 0.4), (-0.085, 1.560, 0.026, 1.1), (0.085, 1.560, 0.026, 0.7),
                                                            (0.0, 1.680, 0.024, 0.3))]
    spots.append((W.TOP(), 0.0, 0.0, 0.028, 0.6))
    roses = _flower_decals(prefix + '_Rose', scarf, M, spots, ['Scarf_Rose', 'Scarf_Rose_2'], 'Scarf_Rose_Heart', leaf_slot='Scarf_Leaf')
    return keep + [C.rigid(o, 'Head') for o in roses]


def cat_eye_glasses(prefix, M):
    """Big red cat-eye glasses with rhinestones on the swept-up outer corners (frames only, the eyes stay readable);
    the temples go back under the headscarf."""
    out = []
    for s in (1, -1):
        c = Vector((s * 0.062, -0.166, 1.560))
        ring = []
        for k in range(28):
            a = 2 * math.pi * k / 28
            ex, ez = math.cos(a), math.sin(a)
            out_side = ex * s > 0
            wing = max(0.0, ex * s) ** 2 * max(0.0, ez) ** 0.6             # the outer upper corner sweeps up and out
            wrap = 0.012 * max(0.0, ex * s) ** 2
            ring.append(c + Vector(((0.066 if out_side else 0.052) * ex + s * 0.034 * wing, wrap, 0.054 * ez + 0.040 * wing)))
        tip = max(ring, key=lambda p: (p.x - c.x) * s + (p.z - c.z))
        ring += ring[:2]
        out.append(G.tube(f'{prefix}_Rim_{s}', ring, 0.0062, M['Glasses'], seg=6))
        for k, (dx, dz) in enumerate(((0.0, 0.0), (-0.013, -0.006), (-0.006, -0.016))):
            out.append(G.ellipsoid(f'{prefix}_Gem_{s}_{k}', tip + Vector((s * dx, -0.007, dz)), (0.0055, 0.0040, 0.0055), M['Gem'], seg=4, rings=2))
        hinge = c + Vector((s * 0.068, 0.014, 0.012))
        temple = [hinge, hinge + Vector((s * 0.022, 0.040, -0.002)), Vector((s * 0.150, -0.030, 1.556)), Vector((s * 0.153, 0.010, 1.536))]
        out.append(G.tube(f'{prefix}_Temple_{s}', temple, 0.0040, M['Glasses'], seg=6))
    out.append(G.tube(prefix + '_Bridge', [Vector((0.010, -0.170, 1.574)), Vector((0, -0.176, 1.582)), Vector((-0.010, -0.170, 1.574))],
                      0.0048, M['Glasses'], seg=6))
    return [C.rigid(o, 'Head') for o in out]


def hamlet_granny(body, face, M, skin):
    """v03 (TASK-000510, Vadim: funnier clothes, a better face, funny glasses): the village fashionista - a red Pavlovo
    Posad headscarf with roses, a long quilted telogreika worn open over a turquoise floral housedress, track pants with
    stripes tucked into thick wool socks, shiny galoshes; red cat-eye glasses with rhinestones, red lipstick, rosy cheeks,
    a hairy mole on the chin, a squinting grin; plump. The bucket of potatoes and the live hen stay hand props
    (dropped: the granny is not a hand_props type)."""
    pre = 'HAMLET_GRANNY'
    src = C.weight_source([body])
    out = rose_headscarf(pre + '_Scarf', M)
    bodice = _t(W.top(pre + '_Bodice', W.TEE, 6, None, (.806, .184, .124, -.004), [M['Dress']]), src, C.no_head)
    sk = W.skirt(pre + '_Skirt', M['Dress'], rows=DRESS_KNEE)          # housedress to the knee: the track pants show under it
    dress_spots = [(G.FRONT(), x, z, r, rot) for (x, z, r, rot) in ((-0.120, 0.520, 0.038, 0.3), (0.110, 0.580, 0.034, 1.1), (0.020, 0.500, 0.030, 0.7),
                                                                    (-0.040, 0.615, 0.026, 0.2), (0.160, 0.500, 0.030, 0.9))]
    dress_spots += [(G.BACK(), x, z, r, rot) for (x, z, r, rot) in ((-0.100, 0.520, 0.038, 0.5), (0.120, 0.590, 0.034, 0.1), (0.030, 0.500, 0.030, 0.8))]
    dress_spots += [(G.SIDE(s), -0.020 * s, 0.540, 0.032, 0.4 + s) for s in (1, -1)]
    sflowers = _flower_decals(pre + '_DressFlower', sk, M, dress_spots, ['Dress_Flower', 'Dress_Flower_2'], 'Dress_Flower_Heart')
    bflowers = _flower_decals(pre + '_BodiceFlower', bodice, M, [(G.FRONT(), 0.0, 1.000, 0.026, 0.3), (G.FRONT(), -0.010, 1.120, 0.022, 0.8)],
                              ['Dress_Flower_2', 'Dress_Flower'], 'Dress_Flower_Heart')
    ssrc = C.weight_source([sk])
    out += [bodice, sk] + [_t(o, ssrc) for o in sflowers] + [_t(o, C.weight_source([bodice])) for o in bflowers]
    # the long quilted telogreika worn open
    rows, row_mat, arm = W.quilt(COAT, 1.10)
    sleeve, sleeve_mat = W.quilt_sleeve(W.JACKET_SLEEVE, 0.555)
    coat = W.top(pre + '_Coat', rows, arm, sleeve, (.676, .236, .168, -.012), [M['Coat'], M['Stitch']], row_mat=row_mat, sleeve_mat=sleeve_mat,
                 cut=lambda c: c.y < 0 and abs(c.x) < _coat_gap(c.z))
    _t(coat, src, C.no_head)
    csrc = C.weight_source([coat])
    collar = W.collar(pre + '_Collar', M['Coat'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.196, 0.189), open_deg=40, tip=0.030, thick=0.007)
    pockets = [W.front_decal(f'{pre}_CoatPocket_{s}', [(s * 0.100, 0.720), (s * 0.185, 0.720), (s * 0.185, 0.800), (s * 0.100, 0.800)][::s],
                             coat, M['Stitch'], 0.004, thickness=0.004) for s in (1, -1)]
    out += [coat, _t(collar, csrc, C.no_head)] + [_t(o, csrc) for o in pockets]
    # track pants with stripes tucked into thick wool socks, galoshes
    pants = _t(W.bottoms(pre + '_Track', TRACK_INTO_SOCKS, [M['Track']]), src)
    out += [pants] + T._decal_t(W.leg_stripes(pre + '_Lampas', pants, M['Stripes'], z0=0.26, z1=0.70), pants)
    out += W.boot_shafts(pre + '_Sock', M['Socks'], top=0.30) + W.shoes(pre + '_Galosh', M['Galosh'], M['Galosh'])
    # face: glasses, lipstick (look mouth), blush, a hairy mole on the chin
    out += cat_eye_glasses(pre + '_Glasses', M)
    mole_c = Vector((0.050, B.head_surface_y(0.050, 1.362, 0.004), 1.362))
    mole = G.ellipsoid(pre + '_Mole', mole_c, (0.0085, 0.006, 0.0085), M['Mole'], seg=10, rings=6)
    hair = G.tube(pre + '_MoleHair', [mole_c + Vector((0.0, -0.005, 0.0)), mole_c + Vector((0.006, -0.012, 0.006)), mole_c + Vector((0.002, -0.018, 0.014))],
                  0.0012, M['Mole_Hair'], seg=4)
    out += [C.rigid(mole, 'Head'), C.rigid(hair, 'Head')]
    out += T._face(skin, lambda head: W.blush(pre + '_Blush', M['Blush'], head))
    # v07 (TASK-000539, Vadim: give her a string bag): the avoska in the left hand is her only hand prop; since v07 the
    # granny is a hand_props type, so it stays in the game and drops at the slightest danger. The old bucket and hen
    # (never in the game: she was not a hand_props type) are no longer added.
    ad = TYPES['HAMLET_GRANNY']['arm_down']
    gl, _, _ = grip('Left', ad)
    out += hold(avoska(pre, M, gl), 'Left', ad)
    return out


def avoska(prefix, M, fist):
    """Soviet string bag (avoska) hanging from the left fist: an orange diamond-mesh net bulging round its load - potatoes
    and onions at the bottom, a glass milk bottle with a green foil cap and a long loaf poking out of the top - two
    string handles gathered in the fist. Long side front to back so it clears the leg."""
    c = fist + Vector((0.030, 0.0, -0.250))
    zb, zt = c.z - 0.120, c.z + 0.105                            # net bottom and the top ring
    rx, ry = 0.088, 0.112

    def prof(v):                                                 # radius factor along the height (0 bottom, 1 top)
        return 0.18 + 0.82 * math.sin(0.5 * math.pi * v / 0.55) ** 0.6 if v < 0.55 else 1.0 - 0.30 * ((v - 0.55) / 0.45) ** 1.4

    def net_pt(a, v, grow=1.0):
        k = prof(v) * grow
        return Vector((c.x + rx * k * math.cos(a), c.y + ry * k * math.sin(a), zb + (zt - zb) * v))
    out = []
    n, rows = 10, 12
    for s in (1, -1):                                            # two families of helical strings = diamond mesh
        for k in range(n):
            pts = [net_pt(2 * math.pi * k / n + s * 0.62 * math.pi * (j / rows), j / rows) for j in range(rows + 1)]
            out.append(G.tube(f'{prefix}_Net_{"ab"[s < 0]}{k}', pts, 0.0022, M['Net'], seg=4, caps=False))
    out.append(G.tube(prefix + '_NetTop', [net_pt(2 * math.pi * q / 24, 1.0, 1.04) for q in range(25)], 0.0034, M['Net'], seg=5, caps=False))
    out.append(G.ellipsoid(prefix + '_NetKnot', Vector((c.x, c.y, zb + 0.004)), (0.014, 0.014, 0.008), M['Net'], seg=8, rings=5))
    # two string handles from the top ring up into the fist (front pair and back pair)
    top = zt + 0.004
    for s in (1, -1):
        a = net_pt(math.radians(90 + s * 30) if s > 0 else math.radians(-90 + 30), 1.0, 1.04)
        b = net_pt(math.radians(90 - s * 30) if s > 0 else math.radians(-90 - 30), 1.0, 1.04)
        out.append(G.tube(f'{prefix}_NetHandle_{s}', [a, a.lerp(fist, 0.55) + Vector((0.0, 0.0, 0.010)), fist + Vector((0.0, s * 0.008, -0.004)),
                                                      b.lerp(fist, 0.55) + Vector((0.0, 0.0, 0.010)), b], 0.0040, M['Net'], seg=5))
    # the load: potatoes and onions low in the bag, the milk bottle and the loaf standing up out of the top
    for k, (dx, dy, dz, r, slot) in enumerate(((0.0, 0.0, 0.030, 0.040, 'Potato'), (0.034, 0.046, 0.044, 0.036, 'Potato'),
                                               (-0.030, -0.048, 0.046, 0.037, 'Onion'), (0.030, -0.040, 0.090, 0.034, 'Potato'),
                                               (-0.034, 0.040, 0.092, 0.035, 'Onion'), (0.006, 0.006, 0.110, 0.033, 'Potato'))):
        out.append(G.ellipsoid(f'{prefix}_Veg_{k}', Vector((c.x + dx, c.y + dy, zb + dz)), (r * 1.12, r, r * 0.9), M[slot],
                               rot=Matrix.Rotation(k * 1.1, 3, 'Z'), seg=9, rings=6))
    bot = Vector((c.x - 0.022, c.y - 0.020, zb + 0.120))
    axis = Vector((0.04, -0.08, 1.0)).normalized()
    out.append(G.tube(prefix + '_Milk', [bot, bot + axis * 0.120, bot + axis * 0.150, bot + axis * 0.185, bot + axis * 0.200],
                      lambda i, n: (0.030, 0.030, 0.021, 0.014, 0.014)[i], M['Milk'], seg=12))
    out.append(G.tube(prefix + '_MilkCap', [bot + axis * 0.198, bot + axis * 0.212], 0.0160, M['Milk_Cap'], seg=12))
    lc = Vector((c.x + 0.022, c.y + 0.025, zb + 0.200))
    lax = Vector((0.06, 0.15, 1.0)).normalized()
    rot = Vector((0.0, 0.0, 1.0)).rotation_difference(lax).to_matrix()
    out.append(G.ellipsoid(prefix + '_Loaf', lc, (0.036, 0.032, 0.125), M['Loaf'], rot=rot, seg=12, rings=10))
    side = lax.cross(Vector((1.0, 0.0, 0.0))).normalized()
    for k in range(3):                                           # the diagonal cuts on the crust
        p = lc + lax * (0.040 * (k - 1) + 0.030) - side * 0.031
        out.append(G.tube(f'{prefix}_LoafCut_{k}', [p - lax * 0.016 + Vector((0.012, 0, 0)), p + lax * 0.016 - Vector((0.012, 0, 0))],
                          0.0040, M['Loaf_Cut'], seg=5))
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


SHIRT_SLEEVE = [(.212, .074), (.25, .069), (.30, .064), (.36, .060), (.42, .057), (.455, .056), (.462, .062), (.480, .064),
                (.496, .062), (.500, .052)]
VEST = [(.770, .214, .150, -.012), (.784, .216, .152, -.012), (.86, .214, .150, -.013), (.94, .214, .150, -.012),
        (1.02, .215, .151, -.008), (1.08, .219, .157, -.002), (1.10, .221, .161, 0.0), (1.17, .219, .166, .002),
        (1.235, .207, .170, .002), (1.250, .183, .175, .002), (1.262, .173, .172, .002), (1.266, .167, .166, 0.0),
        (1.258, .163, .160, 0.0)]              # arm row 5


def _vest_gap(z):
    return 0.030 + 0.070 * W.smoothstep(0.95, 1.24, z)


FOOL_WAIST = [(1.010, .206, .148), (0.980, .210, .150), (0.930, .212, .150), (0.880, .206, .144), (0.830, .200, .136),
              (0.784, .192, .128)]                     # trousers hitched up to the chest (z, rx, ry)
BOWL_CUT = W.zprofile([(0, 1.632), (45, 1.622), (80, 1.586), (120, 1.572), (180, 1.560)])


def fool_hat(prefix, M):
    """The straw hat a size too small, perched on the bowl cut and tipped to one side, a bite torn out of the brim with
    straws sticking out of the tear."""
    import bmesh
    crown, brim = straw_hat(prefix, M['Hat'], M['HatBand'], brim_w=0.150)
    bm = bmesh.new(); bm.from_mesh(brim.data)
    kill = [f for f in bm.faces if 95 < math.degrees(math.atan2(f.calc_center_median().x, -f.calc_center_median().y)) < 140
            and math.hypot(f.calc_center_median().x, f.calc_center_median().y) > 0.20]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(brim.data); bm.free(); brim.data.update()
    parts = [crown, brim]
    for k, (a, ln) in enumerate(((100, 0.050), (112, 0.040), (124, 0.055), (134, 0.035))):
        r = math.radians(a)
        p0 = Vector((0.20 * math.sin(r), -0.20 * math.cos(r), 1.670))
        d = Vector((math.sin(r), -math.cos(r), -0.25)).normalized()
        parts.append(C.rigid(G.tube(f'{prefix}_TornStraw_{k}', [p0, p0 + d * ln], lambda i, n: (0.0022, 0.0012)[i], M['Hat'], seg=5), 'Head'))
    m = (Matrix.Translation((0.010, 0.0, 1.762)) @ Matrix.Rotation(math.radians(-14), 4, 'Y') @ Matrix.Scale(0.80, 4)
         @ Matrix.Translation((0.0, 0.0, -1.750)))
    for o in parts:
        o.data.transform(m); o.data.update()
    return parts


def straw(prefix, material, start, end, seed_head=True):
    """Grass stalk held in the mouth corner (a head prop, rigid on the head)."""
    a, b = Vector(start), Vector(end)
    mid = a.lerp(b, 0.55) + Vector((0, 0, 0.012))
    out = [G.tube(prefix + '_Straw', [a, mid, b], lambda i, n: (0.0042, 0.0036, 0.0028)[i], material, seg=6)]
    if seed_head:
        d = (b - mid).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix()
        out.append(G.ellipsoid(prefix + '_StrawHead', b + d * 0.018, (0.0065, 0.0065, 0.024), material, rot=rot, seg=8, rings=6))
    return [W.prop(o, 'Head') for o in out]


def flower(prefix, c, n_dir, petal_m, eye_m, petals=10, r=0.017, petal=(0.011, 0.0045, 0.002), eye=(0.010, 0.010, 0.005)):
    """Flat flower facing n_dir: petals round an eye (daisy behind the ear, the accordion player's carnation)."""
    rot = Vector((0, 0, 1)).rotation_difference(Vector(n_dir).normalized()).to_matrix()
    parts = [G.ellipsoid(prefix + '_Eye', c, eye, eye_m, rot=rot, seg=10, rings=6)]
    for k in range(petals):
        a = 2 * math.pi * k / petals
        parts.append(G.ellipsoid(f'{prefix}_Petal_{k}', c + rot @ Vector((math.cos(a), math.sin(a), 0.0)) * r, petal, petal_m,
                                 rot=rot @ Matrix.Rotation(a, 3, 'Z'), seg=6, rings=4))
    return parts


def suspenders(prefix, M, shirt, collar, pants):
    """Braces on the hitched-up trousers: the left one over the shoulder and across the back, the right one slipped off
    and hanging in a loop by the hip; metal clips on the waistband."""
    import buddy_pool_construction as CN
    raw = [(0.085, -0.152, 0.995), (0.100, -0.146, 1.060), (0.120, -0.120, 1.140), (0.140, -0.060, 1.195), (0.146, 0.010, 1.212),
           (0.130, 0.080, 1.190), (0.090, 0.128, 1.130), (0.030, 0.146, 1.060), (-0.050, 0.152, 0.995)]
    ps, ns = CN.on_surface([shirt, collar], raw, 0.007, step=0.014)
    left = _t(CN.ribbon(prefix + '_Brace_L', ps, ns, 0.030, [M['Suspenders']], lambda i, j: 0, cols=1, thick=0.005), C.weight_source([shirt]),
              C.no_head)
    loop = CN._resample([(-0.090, -0.154, 0.998), (-0.150, -0.142, 0.930), (-0.207, -0.090, 0.850), (-0.228, -0.020, 0.800),
                         (-0.226, 0.050, 0.800), (-0.202, 0.110, 0.860), (-0.142, 0.152, 0.940), (-0.060, 0.158, 0.998)], 0.014)
    right = C.rigid(CN.ribbon(prefix + '_Brace_R', loop, [Vector((p.x, p.y, 0.0)).normalized() for p in loop], 0.030, [M['Suspenders']],
                              lambda i, j: 0, cols=1, thick=0.005), 'Hips')
    clips = [W.box(f'{prefix}_Clip_{k}', Vector(c), (0.016, 0.004, 0.013), M['Clip'])
             for k, c in enumerate(((0.085, -0.160, 1.004), (-0.050, 0.160, 1.004), (-0.090, -0.162, 1.004), (-0.060, 0.166, 1.004)))]
    return [left, right] + [_t(o, C.weight_source([pants])) for o in clips]


def hamlet_shepherd(body, face, M, skin):
    """v03 (TASK-000509, Vadim: 'a dumber fool, now he looks too prestigious'): the village fool - a straw hat too small
    and torn, bowl cut, freckles, one eye drooping, mouth open, tongue out, a snot bubble, a daisy behind the ear; a red
    shirt buttoned wrong, tucked into trousers hitched up to the chest on braces (one slipped off), a pot belly, one
    rubber boot and one holey sock with the big toe out. The crook stays a hand prop (dropped: not a hand_props type).
    v04 (TASK-000510): the straw in the teeth again, in the left mouth corner (the tongue hangs out of the right one)."""
    import buddy_pool_forest as F
    pre = 'HAMLET_SHEPHERD'
    src = C.weight_source([body])
    shirt = W.top(pre + '_Shirt', W.TUCKED, 6, SHIRT_SLEEVE, (.844, .166, .110, -.006), [M['Shirt'], M['Shirt_Roll']],
                  sleeve_mat=[0] * 5 + [1] * 5)
    _t(shirt, src, C.no_head)
    ssrc = C.weight_source([shirt])
    collar = W.collar(pre + '_Collar', M['Shirt'], open_deg=30, tip=0.034, thick=0.005)
    btns = W.buttons(pre + '_Btn', shirt, M['Buttons'], [(0.016, 1.150), (-0.008, 1.072), (0.013, 0.998)], r=0.009)   # buttoned wrong
    out = [shirt, _t(collar, ssrc, C.no_head)] + [_t(o, ssrc) for o in btns]
    pants = _t(C.legwear(pre + '_Trousers', FOOL_WAIST, .742, W.LEGS_ANKLE, [M['Trousers']], **G.res('bottoms', n=16, subdiv=1)), src)
    patches = [W.front_decal(pre + '_Patch_0', [(0.056, 0.470), (0.134, 0.462), (0.140, 0.540), (0.062, 0.548)], pants, M['Patch'], 0.003,
                             thickness=0.003, step=0.012),
               W.front_decal(pre + '_Patch_1', [(-0.146, 0.640), (-0.080, 0.646), (-0.084, 0.710), (-0.148, 0.704)], pants, M['Patch_2'],
                             0.003, thickness=0.003, step=0.012),
               G.decal(pre + '_Patch_2', [(-0.120, 0.700), (-0.030, 0.706), (-0.034, 0.790), (-0.118, 0.784)], W.BACK(), [pants], 0.003,
                       M['Patch'], thickness=0.003, step=0.014)]
    out += [pants] + [_t(o, C.weight_source([pants])) for o in patches]
    out += suspenders(pre, M, shirt, out[1], pants)
    # one rubber boot (left), one holey sock (right)
    up, so, _, _ = C.sneaker(pre + '_Boot_1', 1, M['Boots'], M['Boots_Sole'])
    wf = C.shoe_weights(1)
    for o in (up, so):
        C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
    shaft_l, shaft_r = W.boot_shafts(pre + '_Boot', M['Boots'])
    bpy.data.objects.remove(shaft_r)
    out += [up, so, shaft_l] + F._bare_sock_foot(pre, -1, M['Sock'], M['Sock_Rim'], skin)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Sock'], top=0.270), src))
    # head: hat, bowl cut, tongue, snot bubble, daisy, freckles
    out += fool_hat(pre + '_Hat', M)
    hair, edge = W.shell(pre + '_Hair', M['Hair'], BOWL_CUT, None, off=0.006, thick=0.008, seg=32, rows=6)
    out += [C.rigid(hair, 'Head'), C.rigid(G.tube(pre + '_HairEdge', edge + [edge[0]], 0.0065, M['Hair'], seg=6, caps=False), 'Head')]
    tongue = G.ellipsoid(pre + '_Tongue', (-0.031, B.head_surface_y(-0.031, 1.388, 0.014), 1.382), (0.0175, 0.0075, 0.025), M['Tongue'],
                         rot=Matrix.Rotation(math.radians(-58), 3, 'X') @ Matrix.Rotation(math.radians(16), 3, 'Y'), seg=16, rings=10)
    groove = G.tube(pre + '_TongueGroove', [(-0.031, B.head_surface_y(-0.031, 1.383, 0.024), 1.383),
                                            (-0.032, B.head_surface_y(-0.032, 1.370, 0.026), 1.369)], 0.0016, M['Tongue_Groove'], seg=6)
    snot = G.ellipsoid(pre + '_Snot', (0.020, -0.192, 1.428), (0.013, 0.012, 0.013), M['Snot'], seg=12, rings=8)
    daisy = flower(pre + '_Daisy', Vector((-0.168, 0.030, 1.535)), (-0.8, -0.4, 0.45), M['Daisy'], M['Daisy_Eye'])
    stem = G.tube(pre + '_DaisyStem', [(-0.160, 0.034, 1.530), (-0.152, 0.060, 1.500), (-0.146, 0.074, 1.470)], 0.0018, M['Daisy_Stem'], seg=5)
    out += [C.rigid(o, 'Head') for o in [tongue, groove, snot, stem] + daisy]
    out += straw(pre, M['Straw'], (0.026, -0.118, 1.412), (0.190, -0.236, 1.452))     # v04: the straw back, in the left corner

    def freckles(head):
        spots = ((0.0, 0.0), (0.016, 0.008), (-0.014, 0.010), (0.008, -0.012), (-0.010, -0.010), (0.022, -0.004), (-0.022, 0.0))
        return [C.rigid(G.decal(f'{pre}_Freckle_{s}_{k}', C.ellipse(s * (0.096 + dx), 1.452 + dz, 0.0036, 0.0036, 6), G.FRONT(), [head], 0.0014,
                                M['Freckles']), 'Head') for s in (1, -1) for k, (dx, dz) in enumerate(spots)]
    out += T._face(skin, freckles)
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


def kartuz(prefix, M):
    """Peaked cloth cap (kartuz) with a red carnation tucked into the band on the left: the village accordion player's."""
    base = W.zprofile([(0, 1.667), (90, 1.656), (180, 1.642)])
    rows = [('fit', base, 0.004), (1.700, 0.152, 0.148, 0.0, 0.010), (1.716, 0.170, 0.176, -0.008, 0.014),
            (1.736, 0.180, 0.188, -0.012, 0.018), (1.754, 0.168, 0.176, -0.012, 0.020), (1.766, 0.112, 0.118, -0.010, 0.020),
            (1.771, 0.040, 0.042, -0.008, 0.020)]
    crown = W.ring_loft(prefix + '_Crown', rows, [M['Cap'], M['CapBand']], row_mat=[1, 0, 0, 0, 0, 0], seg=32)
    visor = W.peak(prefix + '_Visor', M['Visor'], base, length=0.060, droop=0.022, curve=0.016, span=62, off=0.006, thick=0.007)
    p, nrm = W.head_at(math.radians(48), W.h_of(1.692), 0.034)
    n_dir = (nrm + Vector((0.0, -0.6, 0.3))).normalized()
    bloom = flower(prefix + '_Carnation', p, n_dir, M['Flower'], M['Flower'], petals=9, r=0.022, petal=(0.019, 0.012, 0.008),
                   eye=(0.021, 0.021, 0.017))
    leaf = G.ellipsoid(prefix + '_Leaf', p + Vector((0.010, 0.030, -0.014)), (0.008, 0.032, 0.004), M['Leaf'],
                       rot=Matrix.Rotation(math.radians(-20), 3, 'X') @ Matrix.Rotation(math.radians(-30), 3, 'Z'), seg=8, rings=4)
    return [C.rigid(o, 'Head') for o in [crown, visor, leaf] + bloom]


def garmon(prefix, M, targets, c=Vector((0.0, -0.352, 0.968))):
    """Garmon (button accordion) resting on the fat belly: black lacquered ends with metal corners, red bellows folded
    black at every pleat, a double column of melody buttons on the right end, bass buttons on the left end; two leather
    straps over the shoulders, crossed on the back. A Spine2 prop, so it is not reshaped with the belly: placed in front
    of the reshaped (belly 1.0) tank top."""
    import buddy_pool_bad as BD
    import buddy_pool_construction as CN
    hy, hz = 0.064, 0.118
    parts = []
    for s in (1, -1):
        parts.append(BD.rbox(f'{prefix}_End_{s}', c + Vector((s * 0.160, 0.0, 0.0)), (0.024, hy, hz), M['Garmon_Wood'], bevel=0.010))
        for zz in (1, -1):
            parts.append(BD.rbox(f'{prefix}_Corner_{s}_{zz}', c + Vector((s * 0.1855, 0.0, zz * (hz - 0.018))), (0.002, hy - 0.008, 0.015),
                                 M['Garmon_Metal'], bevel=0.0015))
    secs = []
    for k in range(15):
        x = -0.136 + 0.272 * k / 14
        A, Bz = (hy - 0.004, hz - 0.006) if k % 2 == 0 else (hy - 0.013, hz - 0.017)
        L = math.hypot(A, Bz)
        secs.append((c + Vector((x, 0.0, 0.0)), Vector((0.0, A, Bz)) / L, Vector((0.0, -A, Bz)) / L, L, L))   # rectangular pleat
    parts.append(G.loft(prefix + '_Bellows', secs, M['Garmon_Bellows'], seg=4, cap_start=False, cap_end=False, smooth=False,
                        mat_rows=[k % 2 for k in range(14)], extra=[M['Garmon_Fold']]))
    front = c.y - hy - 0.002
    for col, (x, n, z0) in enumerate(((-0.169, 8, -0.091), (-0.151, 7, -0.078))):
        for k in range(n):
            parts.append(G.ellipsoid(f'{prefix}_Key_{col}_{k}', (x, front, c.z + z0 + 0.026 * k), (0.0065, 0.0035, 0.0065),
                                     M['Garmon_Button'], seg=8, rings=4))
    for k, (dy, dz) in enumerate(((dy, dz) for dy in (-0.030, 0.0, 0.030) for dz in (-0.040, 0.0, 0.040))):
        parts.append(G.ellipsoid(f'{prefix}_Bass_{k}', (c.x + 0.1855 + 0.003, c.y + dy, c.z + dz), (0.003, 0.0065, 0.0065), M['Garmon_Button'],
                                 seg=8, rings=4))
    for s in (1, -1):        # straps from the top back corners over the shoulders, crossing on the back
        corner = c + Vector((s * 0.118, hy - 0.010, hz - 0.004))
        raw = [(s * 0.122, -0.128, 1.160), (s * 0.140, -0.060, 1.200), (s * 0.148, 0.010, 1.214), (s * 0.130, 0.080, 1.195),
               (s * 0.090, 0.125, 1.140), (0.0, 0.140, 1.060), (-s * 0.080, 0.138, 0.990)]
        ps, ns = CN.on_surface(targets, raw, 0.008, step=0.014)
        path = [corner, corner.lerp(ps[0], 0.5)] + ps
        parts.append(CN.ribbon(f'{prefix}_Strap_{s}', path, [ns[0], ns[0]] + ns, 0.036, [M['Garmon_Strap']], lambda i, j: 0, cols=1,
                               thick=0.005))
    return [W.prop(o, 'Spine2') for o in parts]


def hamlet_boxers_grandpa(body, face, M, skin):
    """v02 (TASK-000509): the accordion player - family boxers and the vest top kept (Vadim), a kartuz with a red
    carnation instead of the ushanka, white hair round the back, the garmon on the belly."""
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
    out += kartuz(pre + '_Kartuz', M)
    out.append(W.hair_ring(pre + '_Hair', M['Hair']))
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.016, size=1.6)
    out += T._face(skin, lambda head: W.blush(pre + '_Blush', M['Blush'], head) + W.stubble(pre + '_Stubble', M['Stubble'], head))
    out += garmon(pre + '_Garmon', M, tank + [body])
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


# ------------------------------------------------------------------ HAMLET_MUZHIK (TASK-000891..000892: a funny old-style peasant)
TYPES['HAMLET_MUZHIK'] = dict(
    label='Сельский мужик (крестьянин)', group=GROUP, hand_props=True, body=dict(belly=0.7), arm_down=68.0,
    face=dict(Happy=0.45, Blink=0.25), own_eyes=True,
    look=dict(skin=(240, 182, 146), nose=(226, 104, 90), brow=(206, 160, 90), rim=(176, 116, 92)),
    slots={'Linen': ((232, 220, 196), 0.95), 'Trim': ((196, 40, 52), 0.7), 'Trim_Dot': ((246, 240, 226), 0.7),
           'Rope': ((176, 92, 52), 0.9), 'Trousers': ((112, 82, 62), 0.95), 'Wrap': ((156, 176, 162), 0.95),
           'Cord': ((150, 120, 80), 0.9), 'Lapti': ((196, 160, 100), 0.95), 'Lapti_Weave': ((150, 116, 66), 0.95),
           'Hair': ((222, 186, 110), 0.8), 'Beard': ((206, 140, 80), 0.9), 'Stick': ((128, 86, 48), 0.6),
           'Basket': ((180, 132, 74), 0.9), 'Basket_Band': ((134, 94, 50), 0.9)},
    colourways=[{'Linen': (210, 214, 200), 'Trousers': (80, 80, 76), 'Trim': (40, 70, 150)},
                {'Linen': (226, 206, 176), 'Trousers': (70, 90, 70), 'Rope': (120, 120, 110)}])


def bowl_cut(prefix, M):
    """The pot haircut: straight bangs across the forehead, a level edge round the head just above the ears."""
    lower = W.zprofile([(0, 1.625), (40, 1.615), (80, 1.540), (180, 1.520)])
    off = lambda phi, u: 0.010 + 0.010 * math.sin(math.pi * min(1.0, u * 1.4))
    cap, _ = W.shell(prefix, M['Hair'], lower, None, off=off, thick=0.008, seg=36, rows=6)
    return [C.rigid(cap, 'Head')]


def crook_stick(prefix, M, arm_down):
    """Wooden walking stick held in the right fist, the curved handle on top."""
    fist, _, _ = grip('Right', arm_down)
    bottom = fist + Vector((0.0, -0.090, -0.760))
    path = [bottom, fist + Vector((0.0, -0.010, -0.050)), fist + Vector((0.0, 0.0, 0.080)),
            fist + Vector((0.0, -0.030, 0.140)), fist + Vector((0.0, -0.075, 0.120)), fist + Vector((0.0, -0.085, 0.080))]
    return hold([G.tube(prefix, path, 0.013, M['Stick'], seg=8)], 'Right', arm_down)


def bast_basket(prefix, M, arm_down):
    """Bast basket hanging from its rope handle in the left fist: an open woven tub with darker bands."""
    fist, _, _ = grip('Left', arm_down)
    c = fist + Vector((0.040, 0.0, -0.230))
    r, h = 0.115, 0.190
    body = G.tube(prefix + '_Body', [c + Vector((0, 0, -h / 2)), c + Vector((0, 0, h / 2))], lambda i, n: (r * 0.88, r)[i], M['Basket'],
                  seg=16, caps=False)
    G.solidify(body, 0.008, offset=0.0)
    bottom = G.ellipsoid(prefix + '_Bottom', c + Vector((0, 0, -h / 2)), (r * 0.88, r * 0.88, 0.006), M['Basket'], seg=16, rings=4)
    parts = [body, bottom]
    for k, z in enumerate((-0.060, 0.000, 0.060)):
        ring = [c + Vector((0, 0, z)) + Vector((math.cos(a), math.sin(a), 0)) * (r * (0.94 + 0.06 * (z + h / 2) / h) + 0.004)
                for a in [2 * math.pi * i / 20 for i in range(21)]]
        parts.append(G.tube(f'{prefix}_Band_{k}', ring, 0.006, M['Basket_Band'], seg=5))
    rim = [c + Vector((0, 0, h / 2)) + Vector((math.cos(a), math.sin(a), 0)) * r for a in [2 * math.pi * i / 20 for i in range(21)]]
    parts.append(G.tube(prefix + '_Rim', rim, 0.010, M['Basket_Band'], seg=6))
    parts.append(G.tube(prefix + '_Rope', [c + Vector((-r, 0, h / 2)), fist + Vector((-0.010, 0, -0.010)), fist + Vector((0.010, 0, 0.012)),
                                           c + Vector((r, 0, h / 2))], 0.0045, M['Cord'], seg=5))
    return hold(parts, 'Left', arm_down)


def onuchi_lapti(prefix, M):
    """Grey-green foot wraps to mid-shin bound with criss-cross cords, and woven bast shoes."""
    prof = [(0.090, 0.0475), (0.120, 0.0470), (0.170, 0.0480), (0.220, 0.0490), (0.300, 0.0505)]
    vs, fs, seg = [], [], 14
    for sgn in (1, -1):
        rings = []
        for z, r in prof:
            ring = []
            for j in range(seg):
                a = 2 * math.pi * j / seg
                ring.append(len(vs)); vs.append(Vector((sgn * B.LEG_X + r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)
        for a_, b_ in zip(rings, rings[1:]):
            G.bridge(fs, a_, b_)
    wraps = G.from_data(prefix + '_Wrap', vs, fs, M['Wrap'], True)
    out = [wraps]
    for s in (1, -1):
        cx = s * B.LEG_X
        for k in range(2):
            pts = []
            for i in range(25):
                u = i / 24
                a = 2 * math.pi * 2.2 * u + k * math.pi
                pts.append(Vector((cx + 0.050 * math.cos(a), 0.050 * math.sin(a), 0.110 + 0.180 * u)))
            out.append(G.tube(f'{prefix}_Cord_{s}_{k}', pts, 0.0028, M['Cord'], seg=4))
    shoes = W.shoes(prefix + '_Lapti', M['Lapti'], M['Lapti_Weave'])
    out += shoes
    return out, shoes


def hamlet_muzhik(body, face, M, skin):
    """Funny old-style village muzhik after Vadim's reference: a loose cream linen kosovorotka to the hips with red
    embroidered trim down the collar slit, a rope belt with two tassels, baggy brown trousers gathered at the shins,
    grey-green foot wraps bound with cords, woven bast shoes, a blond pot haircut, a scruffy ginger goatee, a red nose and
    a dumb grin and a bast basket in the left hand."""
    import buddy_pool_vip as V
    import buddy_pool_construction as CN
    pre = 'HAMLET_MUZHIK'
    src = C.weight_source([body])
    shirt = _t(W.top(pre + '_Shirt', W.JACKET, 7, W.JACKET_SLEEVE, (.716, .210, .145, -.012), [M['Linen']]), src, C.no_head)
    ssrc = C.weight_source([shirt])
    out = [shirt]
    trim = []
    for s in (1, -1):
        x0 = s * 0.026
        trim.append(W.front_decal(f'{pre}_Trim_{s}', [(x0 - 0.009, 1.120), (x0 + 0.009, 1.120), (x0 + 0.009, 1.255), (x0 - 0.009, 1.255)], shirt,
                                  M['Trim'], 0.0035, step=0.008))
        for k in range(5):
            z = 1.135 + 0.026 * k
            trim.append(W.front_decal(f'{pre}_TrimDot_{s}_{k}', C.ellipse(x0, z, 0.004, 0.004, 6), shirt, M['Trim_Dot'], 0.0050, step=0.004))
    out += [_t(o, ssrc) for o in trim]
    neck = [Vector((0.152 * math.sin(a), -0.148 * math.cos(a) + 0.002, 1.256)) for a in [2 * math.pi * i / 32 for i in range(33)]]
    out.append(_t(G.tube(pre + '_NeckTrim', neck, 0.0070, M['Trim'], seg=6), ssrc, C.no_head))
    raw = [Vector((0.230 * math.sin(a), -0.160 * math.cos(a) - 0.012, 0.860)) for a in [2 * math.pi * i / 40 for i in range(40)]]
    ps, _ = CN.on_surface([shirt], raw, 0.010, step=0.015, smooth=2, closed=True)
    out.append(_t(G.tube(pre + '_Belt', ps + [ps[0]], 0.0105, M['Rope'], seg=6), ssrc))
    knot = min(ps, key=lambda p: (p - Vector((0.090, -0.30, 0.86))).length)
    for k, dx in enumerate((-0.010, 0.016)):
        tail = [knot, knot + Vector((dx, -0.010, -0.080)), knot + Vector((dx * 1.5, -0.012, -0.150))]
        out.append(_t(G.tube(f'{pre}_Tassel_{k}', tail, lambda i, n: (0.010, 0.008, 0.016)[i], M['Rope'], seg=6), ssrc))
    out.append(_t(G.ellipsoid(pre + '_Knot', knot + Vector((0, -0.006, 0)), (0.020, 0.014, 0.018), M['Rope'], seg=10, rings=6), ssrc))
    baggy = [(.70, .098), (.60, .106), (.50, .108), (.42, .104), (.35, .090), (.320, .064), (.310, .056)]
    out.append(_t(W.bottoms(pre + '_Trousers', baggy, [M['Trousers']]), src))
    feet, shoes = onuchi_lapti(pre, M)
    out += [_t(o, src) if o not in shoes else o for o in feet]
    out += bowl_cut(pre + '_Hair', M)
    out.append(V.jaw_beard(pre + '_Goatee', M['Beard'], top=[(0, 1.385), (18, 1.390), (30, 1.380)], bot=[(0, 1.315), (18, 1.322), (30, 1.350)],
                           bulge=0.006, rows=3, base=0.004, thick=0.004, arc_deg=30.0, cols=12))
    out += W.mustache(pre + '_Mustache', M['Beard'], droop=0.006, size=0.7)
    # no walking stick (Vadim, TASK-000896)
    out += bast_basket(pre + '_Basket', M, TYPES[pre]['arm_down'])
    return out


BUILDERS['HAMLET_MUZHIK'] = hamlet_muzhik
