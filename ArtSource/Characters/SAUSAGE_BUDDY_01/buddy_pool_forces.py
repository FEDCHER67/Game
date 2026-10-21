"""Forces (TASK-000876..000877, Vadim 2026-10-21): the classic American fat-and-thin police duo instead of the
Soviet-style militia (POLICE_THIN / POLICE_FAT from revision 02 on; revision 01 was built by buddy_types.police), the
FBI agent of Elite Hill in a working agent's suit, and the US-style island soldier. No real agency seals or logos;
plain words (POLICE, ARMY) and a generic stars-and-stripes patch only. Same format as buddy_types.TYPES / BUILDERS;
registered from buddy_types.POOLS after the base types, so the police entries here replace the old ones.
No bpy calls at import time."""
import math
import random
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T
from buddy_geo import smoothstep

P = 'mixamorig:'
GROUP = 'Силовики'
SILVER = ((214, 216, 222), 0.22, 'metal')
GOLD = ((214, 174, 76), 0.28, 'metal')

_US_POLICE = {'Shirt': ((34, 44, 74), 0.75), 'Shirt_Dark': ((24, 32, 56), 0.75), 'Trousers': ((26, 32, 52), 0.8),
              'Patch': ((214, 180, 80), 0.6), 'Patch_Core': ((40, 70, 140), 0.6), 'Badge': SILVER, 'Plate': SILVER,
              'Letters': ((240, 240, 236), 0.6), 'Belt': ((16, 16, 18), 0.4), 'Buckle': SILVER, 'Holster': ((18, 18, 20), 0.45),
              'Gun': ((40, 40, 44), 0.35), 'Cuffs': SILVER, 'Baton': ((16, 16, 18), 0.4), 'Radio': ((22, 22, 24), 0.5),
              'Radio_Light': ((230, 40, 40), 0.3), 'Socks': ((16, 16, 18), 0.9), 'Shoes': ((10, 10, 12), 0.12),
              'Shoe_Sole': ((22, 22, 22), 0.6), 'Cap': ((26, 32, 52), 0.7), 'CapBand': ((16, 16, 18), 0.5),
              'Visor': ((10, 10, 12), 0.12), 'Hair': ((60, 48, 40), 0.85)}
_US_POLICE_CW = [{'Shirt': (82, 112, 160), 'Shirt_Dark': (64, 92, 136)},
                 {'Shirt': (120, 120, 112), 'Shirt_Dark': (96, 96, 90), 'Trousers': (70, 66, 56)}]

TYPES = {
    'POLICE_THIN': dict(
        label='Полицейский США, худой', group=GROUP, body=dict(thin=1.0), game_scale=1.06, face=dict(Worried=0.25, Blink=0.2),
        slots=dict(_US_POLICE, Mustache=((60, 48, 40), 0.8)), colourways=[dict(c) for c in _US_POLICE_CW]),
    'POLICE_FAT': dict(
        label='Полицейский США, толстый, с пончиком', group=GROUP, hand_props=True, body=dict(belly=1.6), arm_down=60.0,
        face=dict(Happy=0.35, Blink=0.25),
        slots=dict(_US_POLICE, **{'Aviator_Frame': GOLD, 'Aviator_Lens': ((150, 120, 70), 0.04, 'metal'),
                                  'Mustache': ((70, 52, 40), 0.8), 'Donut': ((214, 160, 96), 0.7), 'Glaze': ((240, 130, 180), 0.25),
                                  'Sprinkle': ((250, 240, 120), 0.4)}),
        colourways=[dict(c) for c in _US_POLICE_CW]),
    'FBI_AGENT': dict(
        label='Агент ФБР', group=GROUP, face=dict(Worried=0.15),
        slots={'Suit': ((18, 18, 22), 0.5), 'Lapel': ((10, 10, 12), 0.35), 'Shirt': ((248, 248, 246), 0.7),
               'Tie': ((12, 12, 14), 0.45), 'Button': ((12, 12, 14), 0.4), 'Socks': ((14, 14, 16), 0.9),
               'Shoes': ((10, 10, 12), 0.1), 'Shoe_Sole': ((20, 20, 20), 0.6), 'Shades_Frame': ((12, 12, 14), 0.25),
               'Shades_Lens': ((8, 10, 14), 0.04), 'Earpiece': ((20, 20, 22), 0.4), 'Hair': ((40, 34, 30), 0.85)},
        colourways=[{'Suit': (58, 62, 72), 'Lapel': (46, 50, 58)}, {'Suit': (28, 34, 54), 'Lapel': (22, 26, 44), 'Tie': (24, 32, 62)}]),
    'ARMY_SOLDIER': dict(
        label='Военный США (остров)', group=GROUP, body=dict(muscle=1.2, belly=0.15), game_scale=1.1,
        face=dict(Worried=0.3, Blink=0.3),
        slots={'Camo': ((104, 114, 70), 0.9), 'Camo_Dark': ((58, 68, 40), 0.9), 'Camo_Brown': ((88, 76, 52), 0.9),
               'Camo_Light': ((146, 152, 104), 0.9), 'Vest': ((84, 96, 58), 0.85), 'Pouch': ((72, 84, 50), 0.85),
               'Strap': ((58, 66, 40), 0.8), 'Tape': ((40, 44, 30), 0.8), 'Boots': ((40, 36, 32), 0.6),
               'Boots_Sole': ((24, 22, 20), 0.7), 'Helmet': ((86, 98, 60), 0.8), 'Goggle_Band': ((26, 26, 28), 0.7),
               'Goggle_Lens': ((40, 60, 70), 0.05), 'Mount': ((30, 30, 32), 0.5), 'Belt': ((110, 96, 72), 0.8),
               'Buckle': ((70, 70, 66), 0.4, 'metal'), 'Hair': ((50, 40, 32), 0.9), 'Flag_Red': ((178, 36, 44), 0.6),
               'Flag_White': ((236, 234, 226), 0.6), 'Flag_Blue': ((40, 52, 110), 0.6), 'Rifle': ((34, 34, 36), 0.45),
               'Rifle_Tan': ((70, 76, 50), 0.7)},
        colourways=[{'Camo': (156, 146, 116), 'Camo_Dark': (98, 92, 66), 'Camo_Brown': (126, 102, 76), 'Camo_Light': (192, 182, 150),
                     'Vest': (150, 132, 100), 'Pouch': (132, 116, 86), 'Helmet': (142, 128, 96), 'Boots': (150, 124, 90)},
                    {'Camo': (120, 124, 130), 'Camo_Dark': (70, 74, 80), 'Camo_Brown': (96, 98, 104), 'Camo_Light': (170, 174, 178),
                     'Vest': (46, 48, 52), 'Pouch': (40, 42, 46), 'Helmet': (60, 62, 68)}]),
}

_t = T._t


# ------------------------------------------------------------------ American police
def star(cx, cz, r_out, r_in, n=6, rot=0.0):
    return [(cx + (r_out if k % 2 == 0 else r_in) * math.sin(rot + math.pi * k / n),
             cz + (r_out if k % 2 == 0 else r_in) * math.cos(rot + math.pi * k / n)) for k in range(2 * n)]


def us_police_cap(prefix, M):
    """Round American police cap: navy crown, black band and visor, silver star badge in front (no lettering)."""
    base = W.zprofile([(0, 1.667), (90, 1.656), (180, 1.642)])
    rows = [('fit', base, 0.004), (1.700, 0.150, 0.146, 0.0, 0.010), (1.712, 0.162, 0.159, -0.003, 0.012),
            (1.732, 0.196, 0.200, -0.008, 0.016), (1.744, 0.198, 0.202, -0.009, 0.018), (1.756, 0.186, 0.190, -0.009, 0.020),
            (1.764, 0.110, 0.114, -0.008, 0.020), (1.766, 0.030, 0.032, -0.006, 0.020)]
    crown = W.ring_loft(prefix + '_Crown', rows, [M['Cap'], M['CapBand']], row_mat=[1, 1, 0, 0, 0, 0, 0, 0], seg=32)
    visor = W.peak(prefix + '_Visor', M['Visor'], base, length=0.060, droop=0.022, curve=0.014, span=62, off=0.006, thick=0.007)
    badge = G.decal(prefix + '_Badge', star(0.0, 1.714, 0.022, 0.012), W.FRONT(), [crown], 0.004, M['Badge'], step=0.004, thickness=0.003)
    return [C.rigid(o, 'Head') for o in (crown, visor, badge)]


def donut(prefix, M, arm_down):
    """Pink-glazed donut in the right fist (dropped at the slightest danger)."""
    import buddy_pool_hamlet as HM
    fist, _, _ = HM.grip('Right', arm_down)
    c = fist + Vector((0.0, -0.050, 0.020))
    ring = [c + Vector((0.034 * math.cos(a), 0.0, 0.034 * math.sin(a))) for a in [2 * math.pi * k / 14 for k in range(15)]]
    dough = G.tube(prefix + '_Dough', ring, 0.019, M['Donut'], seg=10, caps=False)
    glaze_ring = [c + Vector((0.034 * math.cos(a), -0.007, 0.034 * math.sin(a))) for a in [2 * math.pi * k / 14 for k in range(15)]]
    glaze = G.tube(prefix + '_Glaze', glaze_ring, 0.0165, M['Glaze'], seg=10, caps=False)
    rnd = random.Random(5)
    bits = []
    for k in range(10):
        a = 2 * math.pi * k / 10 + rnd.uniform(-0.2, 0.2)
        q = c + Vector((0.034 * math.cos(a), -0.026, 0.034 * math.sin(a))) + Vector((rnd.uniform(-0.006, 0.006), 0, rnd.uniform(-0.006, 0.006)))
        bits.append(G.ellipsoid(f'{prefix}_Sprinkle_{k}', q, (0.0045, 0.0015, 0.0015), M['Sprinkle'],
                                rot=Matrix.Rotation(rnd.uniform(0, math.pi), 3, 'Y'), seg=4, rings=3))
    return HM.hold([dough, glaze] + bits, 'Right', arm_down)


def duty_belt(prefix, M, rx, ry, fat):
    """Black duty belt with a silver buckle, a holster with the pistol grip showing (right hip), a handcuff case and a
    radio (left hip front), the baton (left side)."""
    import buddy_pool_bad as BD
    out = W.belt(prefix, M['Belt'], M['Buckle'], z=0.872, rx=rx, ry=ry, dy=-0.010, width=0.048)
    hx = rx + 0.014
    out += [BD.rbox(prefix + '_Holster', Vector((-hx, 0.020, 0.820)), (0.020, 0.040, 0.075), M['Holster'], bevel=0.008),
            BD.rbox(prefix + '_GunGrip', Vector((-hx, 0.045, 0.900)), (0.016, 0.020, 0.040), M['Gun'], bevel=0.006,
                    rot=Matrix.Rotation(math.radians(-14), 3, 'X')),
            BD.rbox(prefix + '_CuffCase', Vector((rx * 0.55, -ry - 0.006, 0.866)), (0.026, 0.014, 0.024), M['Holster'], bevel=0.006),
            BD.rbox(prefix + '_BeltRadio', Vector((rx * 0.88, -ry * 0.55, 0.850)), (0.020, 0.016, 0.040), M['Radio'], bevel=0.006)]
    out += [G.tube(prefix + '_Baton', [(hx, 0.050, 0.876), (hx + 0.008, 0.064, 0.600)], 0.0145, M['Baton'], seg=10),
            G.tube(prefix + '_BatonGrip', [(hx, 0.050, 0.884), (hx - 0.003, 0.046, 0.924)], 0.016, M['Baton'], seg=10)]
    return out


def us_police(body, face, M, skin, fat=False):
    """American patrol cop, the classic duo: the fat one (big belly, bareheaded, gold aviators, walrus moustache, a
    donut in the fist) and the thin lanky one (round cap, thin moustache). Navy short-sleeve shirt tucked in, a silver
    star badge, a name plate, gold shoulder patches, POLICE in big white letters on the back, a chest radio, a duty belt
    with holster, cuffs, radio and baton, navy trousers, black shoes."""
    import buddy_pool_prom as PR
    import buddy_pool_oldtown3 as O3
    import buddy_pool_vip as V
    pre = 'POLICE_FAT' if fat else 'POLICE_THIN'
    src = C.weight_source([body])
    rows, arm = (O3.belly_rows(W.TUCKED, 6, z0=0.86) if fat else (W.TUCKED, 6))
    shirt = _t(W.top(pre + '_Shirt', rows, arm, W.SLEEVE_SHORT, (.844, .166, .110, -.006), [M['Shirt']]), src, C.no_head)
    ssrc = C.weight_source([shirt])
    out = [shirt, _t(W.collar(pre + '_Collar', M['Shirt'], open_deg=26, tip=0.022), ssrc, C.no_head)]
    deco = [W.front_decal(pre + '_Badge', star(0.098, 1.124, 0.030, 0.016), shirt, M['Badge'], 0.005, thickness=0.003, step=0.004),
            W.front_decal(pre + '_Plate', [(-0.134, 1.096), (-0.070, 1.096), (-0.070, 1.112), (-0.134, 1.112)], shirt, M['Plate'], 0.004,
                          thickness=0.002, step=0.006),
            W.front_decal(pre + '_Placket', [(-0.007, 0.86), (0.007, 0.86), (0.007, 1.24), (-0.007, 1.24)], shirt, M['Shirt_Dark'], 0.0026)]
    for s in (1, -1):
        deco.append(W.front_decal(f'{pre}_PocketFlap_{s}', [(s * 0.060, 1.066), (s * 0.140, 1.066), (s * 0.140, 1.088), (s * 0.060, 1.088)][::s],
                                  shirt, M['Shirt_Dark'], 0.0035, thickness=0.003))
        for k, (r_x, r_y, mat, off) in enumerate(((0.036, 0.042, 'Patch', 0.003), (0.024, 0.029, 'Patch_Core', 0.0045))):
            deco.append(G.decal(f'{pre}_Patch_{s}_{k}', C.ellipse(s * 0.300, 0.010, r_x, r_y, 16), W.TOP(), [shirt], off, M[mat], step=0.006))
        deco.append(G.decal(f'{pre}_PatchStar_{s}', star(s * 0.300, 0.010, 0.016, 0.008, n=5), W.TOP(), [shirt], 0.0058, M['Patch'], step=0.004))
    deco.append(V.back_text(pre + '_Police', 'POLICE', 1.110, M['Letters'], shirt, size=0.085, off=0.004))
    out += [_t(o, ssrc) for o in deco]
    out += PR.chest_radio(pre + '_Radio', M, shirt)
    rx, ry = (0.236, 0.172) if fat else (0.190, 0.130)
    out += [_t(o, ssrc) for o in duty_belt(pre, M, rx, ry, fat)]
    out.append(T._trousers(pre, M, 'Trousers', src))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.shoes(pre, M['Shoes'], M['Shoe_Sole'])
    if fat:
        out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz'))
        out += W.glasses(pre + '_Aviators', M['Aviator_Frame'], M['Aviator_Lens'], rx=0.054, rz=0.050, round_k=0.85)
        out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.012, size=1.45)
        out += donut(pre + '_Donut', M, TYPES[pre]['arm_down'])
    else:
        out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=W.zprofile([(0, 1.664), (180, 1.640)])))
        out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.002, size=0.55)
        out += us_police_cap(pre + '_Cap', M)
    return out


# ------------------------------------------------------------------ FBI agent
def neck_badge(prefix, M, jacket):
    """Gold shield badge hanging on a ball chain over the jacket front (raid style)."""
    import buddy_pool_bad2 as BD2
    import buddy_pool_bad as BD
    chain, pts = BD2._chain(prefix + '_Chain', M['Badge_Chain'], [jacket], drop=0.200, rad=0.168, off=0.010, link=0.0030)
    low = min(pts, key=lambda p: p.z)
    shield = [(0.0, -0.034), (0.024, -0.016), (0.026, 0.020), (0.012, 0.030), (0.0, 0.024), (-0.012, 0.030), (-0.026, 0.020), (-0.024, -0.016)]
    c = low + Vector((0, -0.006, -0.030))
    vs = [c + Vector((x, 0.0, z)) for x, z in shield]
    plate = G.from_data(prefix + '_Shield', vs, [tuple(range(len(vs)))[::-1]], M['Badge'], False, fix_normals=False)
    G.solidify(plate, 0.004, offset=0.0)
    return [chain, plate]


def square_shades(prefix, M, rx=0.056, rz=0.050):
    """Square agent sunglasses: a thin square frame (buddy_wear glasses with a near-square rim) and flat square
    lenses filling it, instead of the round lens ellipsoids."""
    import buddy_pool_bad as BD
    out = W.glasses(prefix, M['Shades_Frame'], None, rx=rx, rz=rz, round_k=0.22)
    for s in (1, -1):
        c = Vector((s * (B.EYE_C[0] + 0.006), -0.163, B.EYE_C[2]))
        out.append(C.rigid(BD.rbox(f'{prefix}_Lens_{s}', c, (rx * 0.96, 0.0035, rz * 0.94), M['Shades_Lens'], bevel=0.003), 'Head'))
    return out


def fbi_agent(body, face, M, skin):
    """Federal agent (Vadim, TASK-000880: the black suit is the main look, no badge chain): black suit, white shirt,
    thin black tie, square black sunglasses, an earpiece with the coiled wire into the collar, black shoes, a bald head."""
    pre = 'FBI_AGENT'
    src = C.weight_source([body])
    jacket, out = T._suit(pre, M, src, 'Suit', 'Tie', 'Button')
    out.append(T._trousers(pre, M, 'Suit', src))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += T._dress_shoes(pre, M)
    out += square_shades(pre + '_Shades', M)
    out += W.earpiece(pre + '_Earpiece', M['Earpiece'])
    return out                                                                                  # bald (Vadim, TASK-000881)


# ------------------------------------------------------------------ US soldier
def helmet(prefix, M):
    """Combat helmet with a tan cover, a night-vision mount plate in front, goggles strapped round it, a chin strap."""
    import buddy_pool_bad as BD
    base = W.zprofile([(0, 1.648), (70, 1.590), (110, 1.560), (180, 1.560)])
    rows = [('fit', base, 0.024), ('fit', lambda phi: base(phi) + 0.004, 0.030), (1.720, 0.176, 0.182, 0.004, 0.0),
            (1.775, 0.160, 0.168, 0.004, 0.0), (1.818, 0.118, 0.126, 0.004, 0.0), (1.838, 0.048, 0.052, 0.004, 0.0)]
    shell = W.ring_loft(prefix + '_Shell', rows, [M['Helmet']], seg=32)
    band_rows = [(1.700, 0.182, 0.188, 0.004, 0.0), (1.724, 0.180, 0.186, 0.004, 0.0)]
    band = W.ring_loft(prefix + '_GoggleBand', band_rows, [M['Goggle_Band']], seg=32, cap_top=False)
    G.solidify(band, 0.004, offset=0.0)
    out = [shell, band, BD.rbox(prefix + '_Mount', Vector((0.0, -0.186, 1.742)), (0.022, 0.008, 0.016), M['Mount'], bevel=0.004)]
    for s in (1, -1):
        out.append(G.ellipsoid(f'{prefix}_Goggle_{s}', (s * 0.052, -0.180, 1.712), (0.036, 0.016, 0.022), M['Goggle_Lens'], seg=12, rings=6))
        path = [(s * 0.168, -0.004, 1.585), (s * 0.150, -0.060, 1.450), (s * 0.090, -0.110, 1.345), (0.0, -0.118, 1.318)]
        out.append(G.tube(f'{prefix}_Strap_{s}', path, 0.0055, M['Strap'], seg=6))
    return [C.rigid(o, 'Head') for o in out]


def camo(prefix, target, M, axes_list, area, n=14, seed=3):
    """Multi-tone camo blotches projected onto a garment from several directions."""
    rnd = random.Random(seed)
    out = []
    (x0, x1), (z0, z1) = area
    slots = ('Camo_Dark', 'Camo_Brown', 'Camo_Light')
    for a_i, axes in enumerate(axes_list):
        for k in range(n):
            pts = W.blob(rnd.uniform(x0, x1), rnd.uniform(z0, z1), rnd.uniform(0.020, 0.036), n=10, seed=seed * 100 + a_i * 20 + k,
                         rough=0.6, rot=rnd.uniform(0, 3.1), sx=rnd.uniform(1.2, 1.9))
            out.append(G.decal(f'{prefix}_{a_i}_{k}', pts, axes, [target], 0.0025 + 0.0006 * (k % 3), M[slots[k % 3]], step=0.012))
    return out


def leg_camo(prefix, target, M, side, n=7, seed=7):
    """Camo blotches on one trouser leg only, small enough never to span the gap between the legs."""
    rnd = random.Random(seed)
    slots = ('Camo_Dark', 'Camo_Brown', 'Camo_Light')
    out = []
    for a_i, axes in enumerate((W.FRONT(), W.BACK())):
        for k in range(n):
            cx = side * B.LEG_X + rnd.uniform(-0.030, 0.030)
            pts = W.blob(cx, rnd.uniform(0.36, 0.80), rnd.uniform(0.016, 0.026), n=10, seed=seed * 100 + a_i * 20 + k, rough=0.55,
                         rot=rnd.uniform(0, 3.1), sx=rnd.uniform(0.8, 1.3))
            out.append(G.decal(f'{prefix}_{a_i}_{k}', pts, axes, [target], 0.0025 + 0.0006 * (k % 3), M[slots[k % 3]], step=0.012))
    return out


def _panel(name, jacket, material, a0, a1, z0, z1, push, cols=14, rows=4):
    """A stiff panel following the torso between azimuths a0..a1 (deg, 0 = front) and heights z0..z1, pushed `push`
    out from the jacket surface (plate carrier plates, cummerbund)."""
    bvh = G.bvh_of([jacket])
    vs, fs = [], []
    for j in range(cols + 1):
        phi = math.radians(a0 + (a1 - a0) * j / cols)
        for i in range(rows + 1):
            z = z0 + (z1 - z0) * i / rows
            probe = Vector((0.40 * math.sin(phi), -0.40 * math.cos(phi), z))
            hit = bvh.ray_cast(probe, (Vector((0, 0, z)) - probe).normalized(), 0.5)
            if hit[0] is not None:
                p = hit[0] + Vector((math.sin(phi), -math.cos(phi), 0)) * push
            else:
                p = Vector((0.22 * math.sin(phi), -0.16 * math.cos(phi), z))
            vs.append(p)
    for j in range(cols):
        for i in range(rows):
            a = j * (rows + 1) + i
            fs.append((a, a + 1, a + rows + 2, a + rows + 1))
    ob = G.from_data(name, vs, fs, material, True, fix_normals=False)
    G.solidify(ob, 0.018, offset=-1.0)
    return ob


def plate_carrier(prefix, M, jacket):
    """Plate carrier hugging the torso: front and back plates, a cummerbund round the sides, shoulder straps, a row of
    three magazine pouches and an admin pouch, an ARMY name tape."""
    import buddy_pool_bad as BD
    front = _panel(prefix + '_Front', jacket, M['Vest'], -62, 62, 0.930, 1.215, 0.018)
    back = _panel(prefix + '_Back', jacket, M['Vest'], 118, 242, 0.930, 1.225, 0.018)
    cumm = [_panel(f'{prefix}_Cummerbund_{s}', jacket, M['Vest'], s * 58, s * 122, 0.930, 1.040, 0.016, cols=8, rows=2) for s in (1, -1)]
    parts = [front, back] + cumm
    bvh = G.bvh_of([front])

    def on_front(x, z, push):
        hit = bvh.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)), 1.0)
        return (hit[0] + hit[1] * push) if hit[0] is not None else Vector((x, -0.19, z))
    for k, x in enumerate((-0.078, 0.0, 0.078)):
        parts.append(BD.rbox(f'{prefix}_Mag_{k}', on_front(x, 0.990, 0.016), (0.032, 0.016, 0.046), M['Pouch'], bevel=0.006))
        parts.append(BD.rbox(f'{prefix}_MagFlap_{k}', on_front(x, 1.034, 0.034), (0.034, 0.006, 0.010), M['Pouch'], bevel=0.003))
    parts.append(BD.rbox(prefix + '_Admin', on_front(0.0, 1.110, 0.012), (0.070, 0.010, 0.036), M['Pouch'], bevel=0.006))
    tape = BD.rbox(prefix + '_Tape', on_front(0.0, 1.170, 0.006), (0.060, 0.004, 0.012), M['Tape'], bevel=0.002)
    parts.append(tape)
    tc = on_front(0.0, 1.170, 0.0115)
    import buddy_pool_vip as V
    parts.append(V.flat_text(prefix + '_ArmyWord', 'ARMY', 0.020, tc, (1, 0, 0), (0, 0, 1), M['Camo_Light']))
    for s in (1, -1):
        path = [on_front(s * 0.100, 1.205, 0.008), Vector((s * 0.112, -0.080, 1.262)), Vector((s * 0.116, 0.050, 1.266)),
                Vector((s * 0.100, 0.150, 1.215))]
        parts.append(G.tube(f'{prefix}_Shoulder_{s}', path, 0.018, M['Vest'], seg=6))
    return [C.rigid(o, 'Spine2') for o in parts]


def flag_patch(prefix, target, M, side=-1):
    """Generic stars-and-stripes patch on the shoulder (projected from above onto the T-pose sleeve)."""
    cx, cy = side * 0.300, 0.010
    out = [G.decal(prefix + '_Base', [(cx - 0.030, cy - 0.020), (cx + 0.030, cy - 0.020), (cx + 0.030, cy + 0.020), (cx - 0.030, cy + 0.020)],
                   W.TOP(), [target], 0.0030, M['Flag_White'], step=0.006)]
    for k in range(3):
        y0 = cy - 0.020 + k * 0.0135
        out.append(G.decal(f'{prefix}_Stripe_{k}', [(cx - 0.030, y0), (cx + 0.030, y0), (cx + 0.030, y0 + 0.0065), (cx - 0.030, y0 + 0.0065)],
                           W.TOP(), [target], 0.0040, M['Flag_Red'], step=0.006))
    out.append(G.decal(prefix + '_Canton', [(cx - 0.030, cy), (cx - 0.004, cy), (cx - 0.004, cy + 0.020), (cx - 0.030, cy + 0.020)], W.TOP(),
                       [target], 0.0050, M['Flag_Blue'], step=0.006))
    return out


def rifle(prefix, M):
    """Cartoon carbine slung across the back, muzzle up behind the right shoulder (no real model)."""
    import buddy_pool_bad as BD
    rot = Matrix.Rotation(math.radians(-38), 3, 'Y')
    c = Vector((0.0, 0.205, 1.030))
    ax = rot @ Vector((0, 0, 1))
    parts = [BD.rbox(prefix + '_Receiver', c, (0.020, 0.024, 0.120), M['Rifle'], bevel=0.006, rot=rot),
             BD.rbox(prefix + '_Handguard', c + ax * 0.190, (0.022, 0.026, 0.080), M['Rifle_Tan'], bevel=0.008, rot=rot),
             BD.rbox(prefix + '_Stock', c - ax * 0.190, (0.018, 0.030, 0.075), M['Rifle_Tan'], bevel=0.008, rot=rot),
             BD.rbox(prefix + '_Mag', c + ax * 0.040 + Vector((0, 0.040, 0)), (0.014, 0.030, 0.040), M['Rifle'], bevel=0.004, rot=rot)]
    parts.append(G.tube(prefix + '_Barrel', [c + ax * 0.260, c + ax * 0.380], 0.008, M['Rifle'], seg=8))
    parts.append(G.tube(prefix + '_Sling', [c - ax * 0.240 + Vector((0, -0.020, 0)), Vector((-0.170, 0.120, 0.930)), Vector((-0.190, -0.050, 0.980)),
                                           Vector((0.0, -0.200, 1.060)), Vector((0.150, -0.120, 1.220)), c + ax * 0.230 + Vector((0, -0.024, 0))],
                        0.007, M['Strap'], seg=6))
    return [C.rigid(o, 'Spine2') for o in parts]


def army_soldier(body, face, M, skin):
    """US-style soldier of the island garrison: multi-tone camo uniform with a stand collar and a stars-and-stripes
    patch on the right shoulder, trousers tucked into coyote boots, a tan plate carrier with magazine and admin pouches
    and an ARMY tape, a web belt, a combat helmet with goggles, a mount plate and a chin strap, a carbine slung on the
    back. Everything sits on the body where it belongs (Vadim: arrange the gear properly)."""
    import buddy_pool_prom as PR
    pre = 'ARMY_SOLDIER'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Camo', src)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Camo'], z0=1.258, r0=(0.157, 0.153), z1=1.290, r1=(0.162, 0.157), z2=1.250,
                      r2=(0.186, 0.180), open_deg=20, tip=0.020, thick=0.005)
    blots = camo(pre + '_CamoJ', jacket, M, [W.FRONT(), W.BACK()], ((-0.19, 0.19), (0.72, 1.24)), n=13, seed=3)
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in blots + flag_patch(pre + '_Flag', jacket, M)]
    trousers = T._trousers(pre, M, 'Camo', src, legs=W.LEGS_TUCKED)
    leg_blots = []
    for s in (1, -1):
        leg_blots += leg_camo(f'{pre}_CamoT_{s}', trousers, M, s, seed=7 + (s > 0))
    out += [trousers] + T._decal_t(leg_blots, trousers)
    out += PR.work_boots(pre, M)
    out += plate_carrier(pre + '_Carrier', M, jacket)
    out += [_t(o, jsrc) for o in W.belt(pre, M['Belt'], M['Buckle'], z=0.872, rx=0.214, ry=0.150, dy=-0.012, width=0.042)]
    out += rifle(pre + '_Rifle', M)
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz'))
    out += helmet(pre + '_Helmet', M)
    return out


BUILDERS = {'POLICE_THIN': lambda b, f, M, s: us_police(b, f, M, s, fat=False),
            'POLICE_FAT': lambda b, f, M, s: us_police(b, f, M, s, fat=True),
            'FBI_AGENT': fbi_agent, 'ARMY_SOLDIER': army_soldier}


# ------------------------------------------------------------------ the hamlet's old hunter (TASK-000888/000888)
TYPES['HAMLET_HUNTER_GRANDPA'] = dict(
    label='Дед-охотник (охрана хутора)', group=GROUP,   # Силовики (Vadim, TASK-000894)
    hand_props=True, body=dict(thin=0.7, belly=0.35), arm_down=70.0,
    face=dict(Worried=0.35, Blink=0.45), own_eyes=True,
    look=dict(skin=(232, 176, 146), nose=(222, 136, 116), brow=(150, 146, 140), rim=(176, 120, 104)),
    slots={'Jacket': ((104, 104, 74), 0.95), 'Stitch': ((80, 80, 56), 0.95), 'Collar': ((92, 92, 64), 0.95),
           'Buttons': ((40, 36, 30), 0.5), 'Patch': ((76, 70, 52), 0.95), 'Trousers': ((84, 88, 64), 0.95),
           'Boots': ((38, 44, 36), 0.4), 'Boots_Sole': ((24, 24, 22), 0.6), 'Hat': ((96, 76, 56), 0.95),
           'Fur': ((150, 120, 86), 1.0), 'Hair': ((168, 164, 158), 0.9), 'Beard': ((176, 172, 166), 0.95), 'Bandolier': ((100, 70, 42), 0.6), 'Shells': ((176, 40, 36), 0.6),
           'Shell_Brass': ((196, 160, 80), 0.3, 'metal'), 'Gun_Metal': ((52, 54, 58), 0.35), 'Gun_Wood': ((128, 82, 44), 0.6)},
    colourways=[{'Jacket': (70, 74, 60), 'Stitch': (52, 56, 44), 'Collar': (62, 66, 52), 'Hat': (60, 56, 50)},
                {'Jacket': (120, 96, 64), 'Stitch': (96, 76, 50), 'Collar': (108, 86, 58), 'Trousers': (60, 62, 52)}])


def shotgun(prefix, M, arm_down):
    """Old double-barrelled shotgun held at the middle in the right fist, barrels down and forward, wooden stock up
    behind the arm (a prop the game swaps for the comic aim-and-recoil)."""
    import buddy_pool_hamlet as HM
    import buddy_pool_bad as BD
    fist, _, _ = HM.grip('Right', arm_down)
    ax = Vector((0.0, -0.45, -1.0)).normalized()           # muzzle direction: down and a bit forward
    rot = ax.to_track_quat('Z', 'Y').to_matrix()
    parts = [BD.rbox(prefix + '_Receiver', fist, (0.018, 0.022, 0.050), M['Gun_Metal'], bevel=0.006, rot=rot)]
    for s in (1, -1):
        base = fist + rot @ Vector((s * 0.0105, 0.0, 0.045))
        parts.append(G.tube(f'{prefix}_Barrel_{s}', [base, base + ax * 0.520], 0.0105, M['Gun_Metal'], seg=8))
    parts.append(BD.rbox(prefix + '_Forend', fist + ax * 0.120, (0.020, 0.026, 0.070), M['Gun_Wood'], bevel=0.008, rot=rot))
    parts.append(BD.rbox(prefix + '_Stock', fist - ax * 0.190 + Vector((0, 0.012, 0)), (0.020, 0.034, 0.150), M['Gun_Wood'],
                         bevel=0.012, rot=rot))
    parts.append(G.tube(prefix + '_Trigger', [fist - ax * 0.030 + Vector((0, 0.020, 0)), fist - ax * 0.010 + Vector((0, 0.030, 0))],
                        0.004, M['Gun_Metal'], seg=5))
    return HM.hold(parts, 'Right', arm_down)


def bandolier(prefix, M, jacket):
    """Leather bandolier across the chest from the left shoulder to the right hip, a row of red shells with brass caps."""
    import buddy_pool_construction as CN
    raw = [Vector((0.120, -0.150, 1.250)), Vector((0.040, -0.205, 1.140)), Vector((-0.060, -0.215, 1.020)), Vector((-0.160, -0.185, 0.910)),
           Vector((-0.215, -0.060, 0.860)), Vector((-0.190, 0.120, 0.900)), Vector((-0.020, 0.200, 1.060)), Vector((0.120, 0.140, 1.250)),
           Vector((0.150, 0.000, 1.290))]
    ps, ns = CN.on_surface([jacket], raw, 0.010, step=0.020, smooth=2, closed=True)
    strap = G.tube(prefix + '_Strap', ps + [ps[0]], 0.016, M['Bandolier'], seg=6)
    out = [strap]
    front = [(p, n) for p, n in zip(ps, ns) if p.y < -0.12 and 0.92 < p.z < 1.22]
    for k, (p, n) in enumerate(front[::2]):
        up = Vector((0, 0, 1))
        out.append(G.tube(f'{prefix}_Shell_{k}', [p + n * 0.010 - up * 0.020, p + n * 0.010 + up * 0.012], 0.0075, M['Shells'], seg=6))
        out.append(G.tube(f'{prefix}_Cap_{k}', [p + n * 0.010 + up * 0.012, p + n * 0.010 + up * 0.020], 0.0080, M['Shell_Brass'], seg=6))
    return out


def hamlet_hunter_grandpa(body, face, M, skin):
    """The hamlet's old hunter who guards it instead of the police (Vadim, TASK-000889: not a policeman, a local old
    hunter): a frail old man in a faded quilted khaki work jacket with patched elbows, a leather bandolier of red shells
    across the chest, baggy trousers tucked into tall rubber boots, a worn ushanka with the flaps tied up, a white
    horseshoe of hair and a big bushy grey beard (Vadim: clearly unlike the accordion grandpa), an old double-barrelled shotgun in the right
    hand (he talks first, then fires wide on purpose - an easy comic mini-boss)."""
    import buddy_pool_transit as TR
    pre = 'HAMLET_HUNTER_GRANDPA'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Jacket', src, quilted=True)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Collar'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=26, tip=0.030, thick=0.007)
    deco = W.buttons(pre + '_Btn', jacket, M['Buttons'], [(0.0, z) for z in (1.175, 1.075, 0.975, 0.875, 0.775)], r=0.011, offset=0.006)
    for s in (1, -1):
        deco.append(W.front_decal(f'{pre}_Patch_{s}', W.blob(s * 0.120, 0.840, 0.026, seed=40 + s, rough=0.3), jacket, M['Patch'], 0.004))
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]
    out += [_t(o, jsrc, C.no_head) for o in bandolier(pre + '_Bandolier', M, jacket)]
    out.append(T._trousers(pre, M, 'Trousers', src, legs=W.LEGS_TUCKED))
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts(pre + '_Boot', M['Boots'], top=0.42)
    out += TR.ushanka(pre + '_Ushanka', M)
    out.append(W.hair_ring(pre + '_Hair', M['Hair']))
    out.append(TR.beard(pre + '_Beard', M['Beard']))                       # a grey bushy beard: unlike the accordion grandpa
    out += W.mustache(pre + '_Mustache', M['Beard'], droop=0.010, size=1.3)
    out += shotgun(pre + '_Shotgun', M, TYPES[pre]['arm_down'])
    return out


BUILDERS['HAMLET_HUNTER_GRANDPA'] = hamlet_hunter_grandpa
