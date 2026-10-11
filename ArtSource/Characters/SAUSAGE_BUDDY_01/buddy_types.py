"""NPC types on the base Sausage Buddy (TASK-000246): junkie, villagers, city people, the rich, police, FSB guard.
Every garment has its own material named <TYPE>_<Slot>; TYPES holds the default colours and two alternative
colourways per type (the game recolours a slot by tinting that material)."""
import importlib
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W

P = 'mixamorig:'
GOLD = ((214, 174, 76), 0.28, 'metal')

# slot: (rgb, roughness[, 'metal']). colourways only list the slots they change.
TYPES = {
    'JUNKIE': dict(
        label='Наркоман (первая жертва)', group='Старт', body=dict(thin=1.0), no_ears=True, face=dict(Blink=0.5, Worried=0.45),
        look=dict(skin=(226, 178, 152), nose=(214, 150, 130), brow=(88, 72, 62), rim=(184, 98, 98)),
        slots={'Hoodie': ((112, 117, 99), 0.95), 'Hoodie_Rib': ((95, 100, 84), 0.95), 'Pants': ((132, 132, 138), 0.95),
               'Pants_Rib': ((112, 112, 118), 0.95), 'Socks': ((206, 202, 190), 0.9), 'Slides': ((40, 42, 46), 0.55),
               'Dirt': ((98, 88, 72), 1.0), 'Hair': ((66, 56, 48), 0.8), 'EyeBags': ((156, 112, 134), 0.8),
               'Stubble': ((96, 80, 74), 0.95)},
        colourways=[{'Hoodie': (74, 76, 84), 'Hoodie_Rib': (62, 64, 72), 'Pants': (54, 58, 74), 'Pants_Rib': (46, 50, 64),
                     'Socks': (186, 186, 180), 'Slides': (156, 44, 42)},
                    {'Hoodie': (130, 98, 74), 'Hoodie_Rib': (112, 84, 64), 'Pants': (92, 98, 82), 'Pants_Rib': (80, 86, 72),
                     'Socks': (222, 218, 206), 'Slides': (42, 62, 122)}]),
    'VILLAGE_GRANDPA': dict(
        label='Сельский дед', group='Деревня', look=dict(brow=(200, 198, 192)),
        slots={'Jacket': ((66, 74, 64), 0.95), 'Stitch': ((44, 50, 44), 0.95), 'Collar': ((54, 60, 52), 0.95),
               'Buttons': ((30, 30, 30), 0.5), 'Trousers': ((80, 78, 82), 0.9), 'Boots': ((54, 78, 54), 0.42),
               'Boots_Sole': ((36, 40, 36), 0.6), 'Cap': ((108, 98, 86), 0.95), 'Hair': ((186, 184, 178), 1.0)},
        colourways=[{'Jacket': (44, 50, 72), 'Stitch': (30, 34, 50), 'Collar': (36, 40, 58), 'Trousers': (60, 60, 64),
                     'Boots': (36, 36, 38), 'Boots_Sole': (24, 24, 26), 'Cap': (70, 70, 74)},
                    {'Jacket': (112, 98, 72), 'Stitch': (84, 72, 52), 'Collar': (96, 82, 60), 'Trousers': (98, 88, 72),
                     'Boots': (60, 92, 124), 'Cap': (132, 112, 82)}]),
    'VILLAGE_GRANDMA': dict(
        label='Сельская бабка', group='Деревня', no_ears=True, look=dict(brow=(192, 188, 182)),
        slots={'Scarf': ((192, 56, 52), 0.9), 'Scarf_Dots': ((246, 242, 234), 0.9), 'Cardigan': ((122, 86, 66), 1.0),
               'Cardigan_Rib': ((104, 72, 54), 1.0), 'Blouse': ((234, 228, 212), 0.85), 'Buttons': ((238, 230, 214), 0.5),
               'Skirt': ((56, 74, 100), 0.95), 'Apron': ((232, 216, 160), 0.9), 'Apron_Trim': ((196, 74, 64), 0.9),
               'Tights': ((122, 94, 74), 0.85), 'Shoes': ((38, 38, 42), 0.3), 'Blush': ((236, 132, 122), 0.6)},
        colourways=[{'Scarf': (56, 94, 162), 'Cardigan': (98, 106, 86), 'Cardigan_Rib': (82, 90, 72), 'Skirt': (92, 42, 48),
                     'Apron': (222, 222, 216), 'Apron_Trim': (56, 94, 162), 'Tights': (92, 86, 82), 'Shoes': (62, 42, 32)},
                    {'Scarf': (230, 188, 62), 'Scarf_Dots': (192, 62, 52), 'Cardigan': (152, 62, 68), 'Cardigan_Rib': (130, 52, 58),
                     'Skirt': (42, 42, 46), 'Apron': (198, 222, 198), 'Apron_Trim': (152, 62, 68), 'Tights': (142, 110, 86)}]),
    'VILLAGE_MAN': dict(
        label='Деревенский мужик', group='Деревня', body=dict(belly=0.7), arm_down=70.0,
        slots={'Tank': ((238, 236, 228), 0.85), 'Pants': ((42, 46, 62), 0.9), 'Stripes': ((230, 230, 226), 0.9),
               'Boots': ((62, 86, 54), 0.42), 'Boots_Sole': ((36, 40, 34), 0.6), 'Hat': ((152, 142, 102), 0.95),
               'Hair': ((82, 66, 52), 0.9)},
        colourways=[{'Tank': (62, 72, 92), 'Pants': (30, 30, 34), 'Boots': (36, 36, 38), 'Boots_Sole': (24, 24, 26),
                     'Hat': (232, 230, 222)},
                    {'Tank': (152, 162, 172), 'Pants': (62, 82, 62), 'Stripes': (222, 202, 82), 'Boots': (132, 62, 42),
                     'Hat': (92, 112, 72)}]),
    'CITY_CLERK': dict(
        label='Офисник', group='Город',
        slots={'Shirt': ((178, 206, 234), 0.8), 'Tie': ((40, 52, 98), 0.6), 'Trousers': ((86, 90, 98), 0.85),
               'Belt': ((36, 32, 30), 0.5), 'Buckle': ((198, 198, 204), 0.3, 'metal'), 'Socks': ((40, 40, 46), 0.9),
               'Shoes': ((30, 28, 28), 0.25), 'Shoe_Sole': ((46, 40, 36), 0.6), 'Glasses': ((24, 24, 26), 0.35),
               'Hair': ((90, 64, 46), 0.75), 'HairPart': ((60, 42, 30), 0.8)},
        colourways=[{'Shirt': (242, 242, 238), 'Tie': (152, 36, 42), 'Trousers': (42, 46, 58), 'Shoes': (72, 46, 32)},
                    {'Shirt': (234, 198, 204), 'Tie': (62, 62, 66), 'Trousers': (112, 102, 86)}]),
    'CITY_STUDENT': dict(
        label='Студент', group='Город',
        slots={'Hoodie': ((216, 170, 54), 0.9), 'Hoodie_Rib': ((192, 150, 46), 0.9), 'Cords': ((240, 236, 228), 0.7),
               'Jeans': ((72, 100, 148), 0.9), 'Jeans_Cuff': ((94, 124, 170), 0.9), 'Socks': ((232, 230, 224), 0.9),
               'Shoe_Upper': ((236, 236, 232), 0.7), 'Shoe_Sole': ((250, 248, 244), 0.6), 'Shoe_Lace': ((230, 230, 226), 0.7),
               'Beanie': ((56, 58, 64), 0.95), 'Backpack': ((54, 86, 74), 0.8), 'Backpack_Straps': ((34, 38, 40), 0.8)},
        colourways=[{'Hoodie': (78, 122, 172), 'Hoodie_Rib': (66, 106, 152), 'Jeans': (42, 44, 52), 'Jeans_Cuff': (58, 60, 68),
                     'Beanie': (192, 62, 52), 'Backpack': (62, 62, 66), 'Shoe_Upper': (42, 42, 46)},
                    {'Hoodie': (132, 162, 112), 'Hoodie_Rib': (114, 142, 96), 'Jeans': (152, 172, 198), 'Jeans_Cuff': (172, 190, 212),
                     'Beanie': (232, 202, 122), 'Backpack': (152, 62, 62)}]),
    'CITY_JOGGER': dict(
        label='Бегунья', group='Город', look=dict(mouth=(196, 58, 82)),
        slots={'Top': ((234, 76, 106), 0.8), 'Shorts': ((42, 46, 58), 0.85), 'Headband': ((246, 244, 238), 0.9),
               'Bands': ((246, 244, 238), 0.9), 'Socks': ((246, 244, 238), 0.9), 'Shoe_Upper': ((122, 212, 92), 0.6),
               'Shoe_Sole': ((246, 244, 238), 0.6), 'Shoe_Lace': ((246, 244, 238), 0.7), 'Hair': ((122, 74, 42), 0.7),
               'HairTie': ((234, 76, 106), 0.6), 'Blush': ((240, 128, 128), 0.6)},
        colourways=[{'Top': (62, 172, 202), 'Shorts': (30, 30, 34), 'Headband': (62, 172, 202), 'Bands': (62, 172, 202),
                     'Shoe_Upper': (250, 142, 42), 'HairTie': (62, 172, 202)},
                    {'Top': (250, 222, 62), 'Shorts': (82, 52, 122), 'Headband': (82, 52, 122), 'Bands': (82, 52, 122),
                     'Shoe_Upper': (240, 240, 236), 'HairTie': (82, 52, 122)}]),
    'RICH_BUSINESS': dict(
        label='Миллионер-бизнесмен', group='Элита',
        slots={'Suit': ((42, 52, 80), 0.6), 'Lapel': ((32, 40, 64), 0.45), 'Shirt': ((246, 246, 242), 0.7),
               'Tie': ((172, 34, 44), 0.5), 'Button': ((24, 24, 28), 0.4), 'Square': ((246, 246, 242), 0.6),
               'Socks': ((30, 30, 34), 0.9), 'Shoes': ((22, 20, 20), 0.2), 'Shoe_Sole': ((42, 34, 30), 0.6), 'Gold': GOLD,
               'WatchFace': ((30, 34, 48), 0.2), 'Hair': ((122, 118, 112), 0.6), 'HairPart': ((84, 80, 76), 0.7)},
        colourways=[{'Suit': (62, 62, 66), 'Lapel': (48, 48, 52), 'Tie': (42, 82, 152), 'Square': (172, 34, 44)},
                    {'Suit': (182, 162, 122), 'Lapel': (162, 142, 106), 'Tie': (62, 102, 72), 'Shirt': (202, 222, 240),
                     'Square': (62, 102, 72)}]),
    'RICH_NEWRUSSIAN': dict(
        label='Новый русский', group='Элита',
        slots={'Blazer': ((172, 30, 62), 0.6), 'Lapel': ((142, 24, 52), 0.45), 'Shirt': ((24, 24, 28), 0.6),
               'Trousers': ((24, 24, 28), 0.7), 'Socks': ((24, 24, 28), 0.9), 'Shoes': ((20, 20, 22), 0.18),
               'Shoe_Sole': ((30, 30, 30), 0.6), 'Gold': GOLD, 'WatchFace': ((24, 24, 28), 0.2), 'Hair': ((42, 36, 32), 0.9)},
        colourways=[{'Blazer': (62, 122, 62), 'Lapel': (48, 100, 48)},
                    {'Blazer': (236, 234, 228), 'Lapel': (212, 208, 200), 'Trousers': (236, 234, 228)}]),
    'RICH_YACHT': dict(
        label='Мажор с яхты', group='Элита', look=dict(skin=(230, 140, 92), nose=(218, 118, 82)),
        slots={'Polo': ((246, 246, 242), 0.8), 'Buttons': ((232, 232, 228), 0.5), 'Sweater': ((240, 170, 180), 0.95),
               'Chinos': ((216, 198, 162), 0.85), 'Loafers': ((120, 72, 42), 0.45), 'Loafer_Sole': ((62, 42, 30), 0.6),
               'Shades_Frame': ((44, 32, 28), 0.3), 'Shades_Lens': ((26, 32, 42), 0.08), 'Gold': GOLD,
               'WatchFace': ((242, 242, 238), 0.2), 'Hair': ((228, 198, 122), 0.6), 'HairPart': ((192, 162, 98), 0.7)},
        colourways=[{'Polo': (42, 62, 112), 'Sweater': (242, 242, 238), 'Chinos': (242, 240, 232), 'Loafers': (42, 32, 28)},
                    {'Polo': (162, 202, 232), 'Sweater': (232, 202, 92), 'Chinos': (122, 142, 162)}]),
    'POLICE_THIN': dict(
        label='Полицейский худой', group='Полиция', body=dict(thin=1.0)),
    'POLICE_FAT': dict(
        label='Полицейский толстый', group='Полиция', body=dict(belly=1.0), arm_down=66.0),
    'FSB_GUARD': dict(
        label='Телохранитель ФСБ', group='ФСБ',
        slots={'Suit': ((24, 24, 28), 0.55), 'Lapel': ((14, 14, 16), 0.4), 'Shirt': ((246, 246, 242), 0.7),
               'Tie': ((16, 16, 18), 0.5), 'Button': ((14, 14, 16), 0.4), 'Socks': ((16, 16, 18), 0.9),
               'Shoes': ((14, 14, 16), 0.16), 'Shoe_Sole': ((20, 20, 20), 0.6), 'Shades_Frame': ((14, 14, 16), 0.3),
               'Shades_Lens': ((10, 12, 16), 0.06), 'Earpiece': ((14, 14, 16), 0.4), 'Hair': ((38, 34, 32), 0.9)},
        colourways=[{'Suit': (52, 56, 64), 'Lapel': (40, 44, 50), 'Tie': (42, 50, 72)},
                    {'Suit': (32, 38, 56), 'Lapel': (24, 28, 44), 'Tie': (112, 26, 32)}]),
}
_POLICE_SLOTS = {'Uniform': ((46, 60, 88), 0.8), 'Uniform_Dark': ((34, 46, 70), 0.8), 'Trousers': ((38, 48, 72), 0.85),
                 'Piping': ((192, 40, 46), 0.7), 'Boards': ((38, 48, 72), 0.8), 'Gold': GOLD, 'Belt': ((24, 24, 26), 0.45),
                 'Buckle': ((196, 196, 202), 0.3, 'metal'), 'Holster': ((26, 26, 28), 0.5), 'Baton': ((20, 20, 22), 0.4),
                 'Cap': ((38, 48, 72), 0.8), 'CapBand': ((188, 36, 44), 0.75), 'Visor': ((16, 16, 18), 0.18),
                 'Boots': ((20, 20, 22), 0.35), 'Boot_Sole': ((30, 30, 30), 0.6), 'Boot_Lace': ((22, 22, 24), 0.7),
                 'Hair': ((62, 52, 46), 0.9)}
_POLICE_CW = [{'Uniform': (112, 118, 122), 'Uniform_Dark': (92, 98, 102), 'Trousers': (98, 102, 108), 'Boards': (98, 102, 108),
               'Cap': (102, 108, 114)},
              {'Uniform': (152, 192, 222), 'Uniform_Dark': (122, 162, 198), 'Boards': (38, 48, 72)}]
for _k in ('POLICE_THIN', 'POLICE_FAT'):
    TYPES[_k]['slots'] = dict(_POLICE_SLOTS)
    TYPES[_k]['colourways'] = [dict(c) for c in _POLICE_CW]

# ------------------------------------------------------------------ helpers
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _decal_t(pieces, garment):
    src = C.weight_source([garment])
    return [C.transfer(o, src) for o in pieces]


def _face(skin, fn):
    head = W.head_target(skin)
    try:
        return fn(head)
    finally:
        me = head.data
        bpy.data.objects.remove(head)
        bpy.data.meshes.remove(me)


def _hoodie(prefix, M, src):
    hoodie = W.top(prefix + '_Hoodie', W.HOODIE, 7, W.HOODIE_SLEEVE, (.750, .174, .118, -.010), [M['Hoodie'], M['Hoodie_Rib']],
                   row_mat=[1] + [0] * 13, sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(hoodie, src, C.no_head)
    pocket = G.decal(prefix + '_Pocket', [(-0.135, 0.795), (0.135, 0.795), (0.108, 0.975), (-0.108, 0.975)], W.FRONT(), [hoodie], 0.004,
                     M['Hoodie'], thickness=0.010, **G.res('big_decal', step=0.010))
    out = [hoodie] + _decal_t([pocket], hoodie)
    for s in (1, -1):
        slot = G.decal(f'{prefix}_PocketSlot_{s}', [(s * 0.126, 0.822), (s * 0.136, 0.822), (s * 0.111, 0.970), (s * 0.101, 0.970)], W.FRONT(),
                       [pocket, hoodie], 0.0025, M['Hoodie_Rib'])
        out += _decal_t([slot], hoodie)
    return hoodie, pocket, out


def _hood_down(prefix, material):
    """Fedya's variant A hood: a soft roll round the back of the neck."""
    rh = G.res('hood', seg=14, subdiv=1)
    vs, fs, rings = [], [], []
    for k in range(27):
        phi = math.radians(-152 + 304 * k / 26)
        t = math.cos(phi / 2) ** 2
        R = 0.176 + 0.050 * t
        c = Vector((R * math.sin(phi), 0.004 + R * math.cos(phi) * 1.02, 1.268 - 0.068 * t))
        radial = Vector((math.sin(phi), math.cos(phi), 0))
        a, b = 0.026 + 0.046 * t, 0.034 + 0.066 * t
        ring = []
        for j in range(rh['seg']):
            ang = 2 * math.pi * j / rh['seg']
            ring.append(len(vs)); vs.append(c + radial * (a * math.cos(ang)) + Vector((0, 0, b * math.sin(ang))))
        rings.append(ring)
    for a_, b_ in zip(rings, rings[1:]):
        G.bridge(fs, a_, b_)
    fs.append(tuple(reversed(rings[0]))); fs.append(tuple(rings[-1]))
    hood = G.from_data(prefix + '_Hood', vs, fs, material, True, subdiv=rh['subdiv'])
    pouch = G.ellipsoid(prefix + '_HoodPouch', (0, 0.170, 1.165), (0.125, 0.032, 0.100), material, **G.res('hood_pouch', seg=20, rings=12))
    G.join(hood, [pouch])
    return C.rigid(hood, 'Spine2')


def _jacket(prefix, M, slot, src, cuff_slot=None, quilted=False):
    """Long jacket (suit, uniform, telogreika). cuff_slot: shirt cuff showing past the sleeve."""
    rows, row_mat, arm = W.JACKET, None, 7
    sleeve, sleeve_mat = list(W.JACKET_SLEEVE), None
    mats = [M[slot]]
    if quilted:
        rows, row_mat, arm = W.quilt(W.JACKET, 1.10)
        sleeve, sleeve_mat = W.quilt_sleeve(W.JACKET_SLEEVE, 0.555)
        mats.append(M['Stitch'])
    if cuff_slot:
        sleeve += [(.590, .046), (.603, .045), (.606, .040)]
        sleeve_mat = (sleeve_mat or [0] * len(W.JACKET_SLEEVE)) + [len(mats)] * 3
        mats.append(M[cuff_slot])
    j = W.top(prefix + '_Jacket', rows, arm, sleeve, (.716, .200, .135, -.012), mats, row_mat=row_mat, sleeve_mat=sleeve_mat)
    return _t(j, src, C.no_head)


def _suit(prefix, M, src, jacket_slot, tie_slot, button_slot, square_slot=None):
    jacket = _jacket(prefix, M, jacket_slot, src, cuff_slot='Shirt')
    collar = W.collar(prefix + '_ShirtCollar', M['Shirt'], z0=1.258, r0=(0.156, 0.152), z1=1.284, r1=(0.160, 0.156), z2=1.250,
                      r2=(0.172, 0.166), open_deg=22, tip=0.026, thick=0.004)
    front = W.suit_front(prefix, jacket, M, tie_slot=tie_slot, button_slot=button_slot, square_slot=square_slot)
    jsrc = C.weight_source([jacket])
    return jacket, [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in front]


def _trousers(prefix, M, slot, src, legs=W.LEGS_LONG, cuff=None, cuff_slot=None):
    mats = [M[slot]] + ([M[cuff_slot]] if cuff_slot else [])
    return _t(W.bottoms(prefix + '_' + slot, legs, mats, cuff=cuff), src)


def _dress_shoes(prefix, M, upper='Shoes', sole='Shoe_Sole'):
    return W.shoes(prefix, M[upper], M[sole])

# ------------------------------------------------------------------ types
def junkie(body, face, M, skin):
    src = C.weight_source([body])
    hoodie, pocket, out = _hoodie('JUNKIE', M, src)
    out += W.hood_up('JUNKIE', M['Hoodie'])
    pants = _trousers('JUNKIE', M, 'Pants', src, legs=W.LEGS_SWEAT, cuff=W.SWEAT_CUFF, cuff_slot='Pants_Rib')
    out.append(pants)
    # dirt on the hoodie and the trousers, a hole at the right knee
    stains = [W.front_decal('JUNKIE_Dirt_0', W.blob(-0.070, 1.060, 0.030, seed=1), hoodie, M['Dirt'], 0.0025),
              W.front_decal('JUNKIE_Dirt_1', W.blob(0.112, 1.150, 0.018, seed=2), hoodie, M['Dirt'], 0.0025),
              G.decal('JUNKIE_Dirt_2', W.blob(0.060, 0.900, 0.022, seed=3), W.FRONT(), [pocket, hoodie], 0.0025, M['Dirt'])]
    out += _decal_t(stains, hoodie)
    knee = [W.front_decal('JUNKIE_Dirt_3', W.blob(0.115, 0.610, 0.024, seed=4), pants, M['Dirt'], 0.0025),
            W.front_decal('JUNKIE_HoleRim', W.blob(-0.100, 0.445, 0.032, seed=5, rough=0.5), pants, M['Dirt'], 0.0025),
            W.front_decal('JUNKIE_Hole', W.blob(-0.100, 0.447, 0.024, seed=6, rough=0.55), pants, skin, 0.0040)]
    out += _decal_t(knee, pants)
    out.append(_t(W.plain_socks('JUNKIE_Socks', M['Socks'], top=0.24), src))
    out += W.slides('JUNKIE', M['Socks'], M['Slides'])
    out += W.fringe('JUNKIE_Fringe', M['Hair'])
    out += _face(skin, lambda head: W.eye_bags('JUNKIE_EyeBag', M['EyeBags'], head)
                 + W.stubble('JUNKIE_Stubble', M['Stubble'], head))
    return out


def village_grandpa(body, face, M, skin):
    src = C.weight_source([body])
    jacket = _jacket('GRANDPA', M, 'Jacket', src, quilted=True)
    jsrc = C.weight_source([jacket])
    collar = W.collar('GRANDPA_Collar', M['Collar'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=26, tip=0.030, thick=0.007)
    placket = W.front_decal('GRANDPA_Placket', [(-0.004, 0.705), (0.004, 0.705), (0.004, 1.252), (-0.004, 1.252)], jacket, M['Stitch'], 0.004)
    btns = W.buttons('GRANDPA_Btn', jacket, M['Buttons'], [(0.0, z) for z in (1.175, 1.075, 0.975, 0.875, 0.775)], r=0.011, offset=0.006)
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in [placket] + btns]
    out.append(_trousers('GRANDPA', M, 'Trousers', src, legs=W.LEGS_TUCKED))
    out += W.shoes('GRANDPA_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts('GRANDPA_Boot', M['Boots'])
    out += W.flat_cap('GRANDPA_Cap', M['Cap'])
    out += [W.hair_ring('GRANDPA_Hair', M['Hair'])] + W.mustache('GRANDPA_Mustache', M['Hair'], droop=0.012, size=1.15)
    return out


CARDIGAN = [(.760, .214, .150, -.012), (.776, .216, .151, -.012), (.82, .214, .150, -.013), (.86, .210, .146, -.013)] + \
           [r for r in W.JACKET if r[0] >= .94]                       # arm row 7
CARDIGAN_SLEEVE = [(.222, .080), (.26, .074), (.31, .069), (.37, .065), (.43, .062), (.50, .059), (.555, .056), (.585, .054),
                   (.600, .052), (.606, .047)]


def village_grandma(body, face, M, skin):
    src = C.weight_source([body])
    out = W.headscarf('GRANDMA', M['Scarf'], M['Scarf_Dots'])
    cardigan = W.top('GRANDMA_Cardigan', CARDIGAN, 7, CARDIGAN_SLEEVE, (.776, .206, .142, -.012), [M['Cardigan'], M['Cardigan_Rib']],
                     row_mat=[1] + [0] * (len(CARDIGAN) - 2), sleeve_mat=[0] * 7 + [1] * 3, hem_mat=1)
    _t(cardigan, src, C.no_head)
    csrc = C.weight_source([cardigan])
    deco = [W.front_decal('GRANDMA_Blouse', [(-0.062, 1.258), (0.062, 1.258), (0.0, 1.110)], cardigan, M['Blouse'], 0.0025, step=0.008)]
    deco += W.buttons('GRANDMA_Btn', cardigan, M['Buttons'], [(0.0, z) for z in (1.075, 1.000, 0.925, 0.850)], r=0.010)
    for s in (1, -1):
        deco.append(W.front_decal(f'GRANDMA_Pocket_{s}', [(s * 0.075, 0.790), (s * 0.165, 0.790), (s * 0.165, 0.880), (s * 0.075, 0.880)][::s],
                                  cardigan, M['Cardigan_Rib'], 0.003, thickness=0.004))
    out += [cardigan] + [_t(o, csrc) for o in deco]
    sk = W.skirt('GRANDMA_Skirt', M['Skirt'])
    apron = W.front_decal('GRANDMA_Apron', [(-0.150, 0.880), (0.150, 0.880), (0.168, 0.520), (0.150, 0.470), (0.100, 0.455), (-0.100, 0.455),
                                            (-0.150, 0.470), (-0.168, 0.520)], sk, M['Apron'], 0.004, thickness=0.004, step=0.014)
    apk = G.decal('GRANDMA_ApronPocket', [(-0.070, 0.580), (0.070, 0.580), (0.070, 0.650), (-0.070, 0.650)], W.FRONT(), [apron], 0.0025,
                  M['Apron_Trim'], thickness=0.003)
    ssrc = C.weight_source([sk])
    out += [sk, _t(apron, ssrc), _t(apk, ssrc)]
    out.append(_trousers('GRANDMA', M, 'Tights', src, legs=W.LEGS_TIGHTS))
    out += W.shoes('GRANDMA_Galosh', M['Shoes'], M['Shoes'])
    out += _face(skin, lambda head: W.blush('GRANDMA_Blush', M['Blush'], head))
    return out


def village_man(body, face, M, skin):
    src = C.weight_source([body])
    out = [_t(o, src, C.no_head) for o in W.tank_top('MAN_Tank', M['Tank'], body)]
    pants = _trousers('MAN', M, 'Pants', src, legs=W.LEGS_TUCKED)
    out += [pants] + _decal_t(W.leg_stripes('MAN_Stripe', pants, M['Stripes'], z0=0.36), pants)
    out += W.shoes('MAN_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts('MAN_Boot', M['Boots'])
    out += W.bucket_hat('MAN_Hat', M['Hat'])
    out.append(W.hair('MAN_Hair', M['Hair'], 'buzz'))
    return out


def city_clerk(body, face, M, skin):
    src = C.weight_source([body])
    shirt = _t(W.top('CLERK_Shirt', W.TUCKED, 6, W.SLEEVE_LONG, (.844, .166, .110, -.006), [M['Shirt']]), src, C.no_head)
    ssrc = C.weight_source([shirt])
    out = [shirt, _t(W.collar('CLERK_Collar', M['Shirt']), ssrc, C.no_head)] + [_t(o, ssrc) for o in W.tie('CLERK_Tie', shirt, M['Tie'], z_tip=0.960)]
    out.append(_trousers('CLERK', M, 'Trousers', src))
    out += [_t(o, src) for o in W.belt('CLERK', M['Belt'], M['Buckle'])]
    out.append(_t(W.plain_socks('CLERK_Socks', M['Socks']), src))
    out += _dress_shoes('CLERK', M)
    out += W.glasses('CLERK_Glasses', M['Glasses'])
    hair = W.hair('CLERK_Hair', M['Hair'], 'slick')
    out += [hair, W.hair_part('CLERK_HairPart', M['HairPart'], hair)]
    return out


def city_student(body, face, M, skin):
    src = C.weight_source([body])
    hoodie, pocket, out = _hoodie('STUDENT', M, src)
    out.append(_hood_down('STUDENT', M['Hoodie']))
    hsrc = C.weight_source([hoodie])
    for s in (1, -1):
        path = [(s * 0.040, -0.168, 1.236), (s * 0.044, -0.192, 1.17), (s * 0.046, -0.198, 1.10), (s * 0.045, -0.199, 1.045)]
        out.append(_t(G.tube(f'STUDENT_Cord_{s}', path, 0.0062, M['Cords'], **G.res('cord', seg=8)), src,
                      lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else w))
    out.append(_trousers('STUDENT', M, 'Jeans', src, legs=W.LEGS_ANKLE, cuff=W.ANKLE_CUFF, cuff_slot='Jeans_Cuff'))
    out.append(_t(W.plain_socks('STUDENT_Socks', M['Socks']), src))
    out += W.shoes('STUDENT', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += W.beanie('STUDENT_Beanie', M['Beanie'])
    out += [_t(o, hsrc, C.no_head) for o in W.backpack('STUDENT_Backpack', M['Backpack'], M['Backpack_Straps'], hoodie)]
    return out


def city_jogger(body, face, M, skin):
    src = C.weight_source([body])
    out = [_t(o, src, C.no_head) for o in W.tank_top('JOGGER_Top', M['Top'], body)]
    out.append(_trousers('JOGGER', M, 'Shorts', src, legs=W.LEGS_RUN))
    out.append(_t(W.plain_socks('JOGGER_Socks', M['Socks'], top=0.170), src))
    out += W.shoes('JOGGER', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += W.headband('JOGGER_Headband', M['Headband']) + W.wristbands('JOGGER_Band', M['Bands'])
    out += W.ponytail('JOGGER', M['Hair'], M['HairTie'])
    out += _face(skin, lambda head: W.blush('JOGGER_Blush', M['Blush'], head))
    return out


def rich_business(body, face, M, skin):
    src = C.weight_source([body])
    jacket, out = _suit('BIZ', M, src, 'Suit', 'Tie', 'Button', square_slot='Square')
    out.append(_trousers('BIZ', M, 'Suit', src))
    out.append(_t(W.plain_socks('BIZ_Socks', M['Socks']), src))
    out += _dress_shoes('BIZ', M)
    out += W.watch('BIZ_Watch', M['Gold'], M['WatchFace'], x=0.612)
    hair = W.hair('BIZ_Hair', M['Hair'], 'slick')
    out += [hair, W.hair_part('BIZ_HairPart', M['HairPart'], hair, x=-0.052)]
    return out


def rich_newrussian(body, face, M, skin):
    src = C.weight_source([body])
    jacket, out = _suit('NR', M, src, 'Blazer', None, 'Gold')
    out += [C.transfer(o, C.weight_source([jacket])) for o in W.gold_chain('NR_Chain', M['Gold'], [jacket])]
    out.append(_trousers('NR', M, 'Trousers', src))
    out.append(_t(W.plain_socks('NR_Socks', M['Socks']), src))
    out += _dress_shoes('NR', M)
    out += W.watch('NR_Watch', M['Gold'], M['WatchFace'], x=0.612)
    out.append(W.hair('NR_Hair', M['Hair'], 'buzz'))
    return out


def rich_yacht(body, face, M, skin):
    src = C.weight_source([body])
    polo = _t(W.top('YACHT_Polo', W.TEE, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Polo']]), src, C.no_head)
    psrc = C.weight_source([polo])
    out = [polo, _t(W.collar('YACHT_Collar', M['Polo'], open_deg=30, tip=0.012), psrc, C.no_head)]
    out += [_t(o, psrc) for o in W.buttons('YACHT_Btn', polo, M['Buttons'], [(0.0, 1.232), (0.0, 1.196)], r=0.008)]
    out += [_t(o, psrc, C.no_head) for o in W.sweater_on_shoulders('YACHT_Sweater', M['Sweater'], polo)]
    out.append(_trousers('YACHT', M, 'Chinos', src, legs=W.LEGS_ANKLE, cuff=W.ANKLE_CUFF, cuff_slot='Chinos'))
    shoes = W.shoes('YACHT_Loafer', M['Loafers'], M['Loafer_Sole'])
    out += shoes
    for o in shoes:
        if o.name.endswith('_Upper'):
            s = -1 if '_Shoe_-1' in o.name else 1
            cx = s * B.LEG_X
            st = G.decal(f'YACHT_Penny_{s}', [(cx - 0.070, 0.040), (cx + 0.070, 0.040), (cx + 0.070, 0.058), (cx - 0.070, 0.058)],
                         W.TOP(0.6), [o], 0.003, M['Loafer_Sole'], step=0.010, thickness=0.004)
            C.set_weights(st, [C.shoe_weights(s)(st.matrix_world @ v.co) for v in st.data.vertices])
            out.append(st)
    out += W.sunglasses_on_head('YACHT_Shades', M['Shades_Frame'], M['Shades_Lens'])
    out += W.watch('YACHT_Watch', M['Gold'], M['WatchFace'], x=0.596)
    hair = W.hair('YACHT_Hair', M['Hair'], 'slick')
    out += [hair, W.hair_part('YACHT_HairPart', M['HairPart'], hair)]
    return out


def police(body, face, M, skin, fat=False):
    src = C.weight_source([body])
    jacket = _jacket('COP', M, 'Uniform', src)
    jsrc = C.weight_source([jacket])
    collar = W.collar('COP_Collar', M['Uniform'], z0=1.258, r0=(0.157, 0.153), z1=1.286, r1=(0.162, 0.157), z2=1.246,
                      r2=(0.190, 0.183), open_deg=26, tip=0.026, thick=0.005)
    deco = W.shoulder_boards('COP_Board', jacket, M['Boards'], M['Gold'])
    deco.append(W.front_decal('COP_Badge', [(0.078, 1.152), (0.112, 1.152), (0.114, 1.124), (0.095, 1.100), (0.076, 1.124)], jacket, M['Gold'],
                              0.006, step=0.006))
    for s in (1, -1):
        deco.append(W.front_decal(f'COP_PocketFlap_{s}', [(s * 0.060, 1.058), (s * 0.130, 1.058), (s * 0.130, 1.084), (s * 0.060, 1.084)][::s],
                                  jacket, M['Uniform_Dark'], 0.0035, thickness=0.003))
    deco += W.buttons('COP_Btn', jacket, M['Gold'], [(0.0, z) for z in (1.190, 1.110, 1.030, 0.950, 0.790)], r=0.0095)
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]
    out += [_t(o, jsrc) for o in W.belt('COP', M['Belt'], M['Buckle'], z=0.882, rx=0.214, ry=0.149, dy=-0.013, width=0.040)]
    out += W.holster_baton('COP', M['Holster'], M['Baton'])
    trousers = _trousers('COP', M, 'Trousers', src)
    out += [trousers] + _decal_t(W.leg_stripes('COP_Piping', trousers, M['Piping'], offsets=(0.0,), width=0.006, z0=0.13, z1=0.70), trousers)
    out += W.shoes('COP_Boot', M['Boots'], M['Boot_Sole'], M['Boot_Lace'], high=True)
    out += W.police_cap('COP_Cap', M['Cap'], M['CapBand'], M['Visor'], M['Gold'])
    out.append(W.hair('COP_Hair', M['Hair'], 'buzz'))
    if fat:
        out += W.mustache('COP_Mustache', M['Hair'], droop=0.004, size=1.1)
    return out


def fsb_guard(body, face, M, skin):
    src = C.weight_source([body])
    jacket, out = _suit('FSB', M, src, 'Suit', 'Tie', 'Button')
    out.append(_trousers('FSB', M, 'Suit', src))
    out.append(_t(W.plain_socks('FSB_Socks', M['Socks']), src))
    out += _dress_shoes('FSB', M)
    out += W.glasses('FSB_Shades', M['Shades_Frame'], M['Shades_Lens'], rx=0.052, rz=0.054, round_k=0.75)
    out += W.earpiece('FSB_Earpiece', M['Earpiece'])
    out.append(W.hair('FSB_Hair', M['Hair'], 'buzz'))
    return out


BUILDERS = {'JUNKIE': junkie, 'VILLAGE_GRANDPA': village_grandpa, 'VILLAGE_GRANDMA': village_grandma, 'VILLAGE_MAN': village_man,
            'CITY_CLERK': city_clerk, 'CITY_STUDENT': city_student, 'CITY_JOGGER': city_jogger, 'RICH_BUSINESS': rich_business,
            'RICH_NEWRUSSIAN': rich_newrussian, 'RICH_YACHT': rich_yacht,
            'POLICE_THIN': lambda b, f, M, s: police(b, f, M, s, fat=False), 'POLICE_FAT': lambda b, f, M, s: police(b, f, M, s, fat=True),
            'FSB_GUARD': fsb_guard}


def build(name, body, face, skin):
    """Dress the base body as type `name`; returns the garment objects (joined into 'Outfit' by the builder)."""
    spec = TYPES[name]
    M = W.make_mats(name, spec['slots'])
    if spec.get('no_ears'):
        W.remove_ears(body)
    objs = BUILDERS[name](body, face, M, skin)
    if spec.get('hand_props'):
        return objs
    # TASK-000277: only the types marked hand_props carry things in their hands (and drop them at the slightest
    # danger); for every other type the hand props its builder makes are left out. Head props (a straw in the teeth)
    # and gear on the body stay.
    out = []
    for o in objs:
        if o.get('ov_prop') and W.prop_group(o.get('ov_prop_bone', '')).endswith('Hand'):
            me = o.data
            bpy.data.objects.remove(o)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
            continue
        out.append(o)
    return out


def reshape(name, objs):
    W.reshape(objs, **TYPES[name].get('body', {}))


def look(name):
    return TYPES[name].get('look', {})


def face_defaults(name):
    """Resting expression weights for this type (the game's face script holds them between reactions)."""
    return TYPES[name].get('face', {})


def set_face(face_ob, name):
    keys = face_ob.data.shape_keys
    if keys.animation_data:
        keys.animation_data.action = None
    for kb in keys.key_blocks[1:]:
        kb.value = face_defaults(name).get(kb.name, 0.0)


def arm_down(name):
    """Idle arm angle (degrees below horizontal); fat types hold the arms a little away from the belly."""
    return TYPES[name].get('arm_down')


def apply_colourway(name, k):
    """k = 0: default colours; 1, 2: the alternative colourways (materials looked up by name)."""
    spec = TYPES[name]
    colours = {s: v[0] for s, v in spec['slots'].items()}
    if k:
        colours.update(spec['colourways'][k - 1])
    for slot, rgb in colours.items():
        m = bpy.data.materials.get(f'{name}_{slot}')
        if m is not None:
            W.set_color(m, rgb)


def manifest(name):
    spec = TYPES[name]
    return {'label': spec['label'], 'group': spec['group'], 'body': spec.get('body', {}), 'idle_arm_down_deg': spec.get('arm_down', 74.0),
            'hand_props': bool(spec.get('hand_props')),
            'hand_props_note': 'Props_LeftHand / Props_RightHand meshes: dropped to the floor at the slightest danger (NpcHeldProps)'
            if spec.get('hand_props') else 'carries nothing in the hands',
            'face_defaults': spec.get('face', {}),
            'slots': {f'{name}_{s}': {'default': '#%02X%02X%02X' % v[0], 'metal': len(v) > 2 and v[2] == 'metal'}
                      for s, v in spec['slots'].items()},
            'colourways': [{f'{name}_{s}': '#%02X%02X%02X' % rgb for s, rgb in cw.items()} for cw in spec['colourways']]}


# ------------------------------------------------------------------ district pools (TASK-000270)
# The approved NPC pool by district lives in buddy_pool_*.py; each module adds its own TYPES and BUILDERS here.
POOLS = ('buddy_pool_forest', 'buddy_pool_hamlet', 'buddy_pool_transit', 'buddy_pool_transit2', 'buddy_pool_bad',
         'buddy_pool_bad2', 'buddy_pool_oldtown', 'buddy_pool_oldtown2', 'buddy_pool_prom')
for _name in POOLS:
    try:
        _pool = importlib.import_module(_name)
    except ModuleNotFoundError as _e:
        if _e.name != _name:
            print(f'[BUDDY] pool {_name} skipped: {_e!r}')
        continue
    except Exception as _e:            # a broken pool must not stop the other pools from building
        print(f'[BUDDY] pool {_name} skipped: {_e!r}')
        continue
    TYPES.update(_pool.TYPES)
    BUILDERS.update(_pool.BUILDERS)
