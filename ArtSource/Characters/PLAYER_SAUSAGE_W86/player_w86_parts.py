"""PLAYER_SAUSAGE_W86: the player as a customisable Sausage Buddy (Fedya 2026-10-29: the player is a sausage like the
NPCs, one the player configures). Part library + option tables; build_player_w86.py registers the type into
buddy_types at run time (nothing in SAUSAGE_BUDDY_01 is modified).

Same body, face and 65-bone Mixamo rig as every Sausage Buddy NPC (neutral build: no belly / thin / muscle reshape), so
every shared NPC clip plays on the player. Every option is its own skinned mesh on that rig, named per aspect:
  Hair_02..05 (+ Hair_02..05_Hat, the same style cut to the sides and back for wearing under a cap, beanie or bandana),
  Beard_02..05, Top_01..05, Bottom_01..05, Head_02..05; option 01 of hair, beard and headwear is "none" (no mesh).
  Shoes and Socks are fixed base pieces (always on). The base Body is cut into regions (Body_*, post_player_w86.py) that
  a top or bottom switches off where it covers them.
Parts are built from the existing helpers (buddy_wear, buddy_types, the district pools, the mechanic) wherever one
exists; nothing joke-like. Colours are material tints: one material per slot (PLAYER_<Slot>), shared by every option of
an aspect (Top_Main, Top_Trim, Top_Accent / Bottom_Main, ...), so the game tints the active option with a swatch.
Z up, -Y forward, left = +X, metres (as the whole Sausage Buddy pipeline)."""
import math
from contextlib import contextmanager
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T
import buddy_pool_bad as BD
import buddy_pool_oldtown2 as OT2
import buddy_pool_vip as VIP
import buddy_pool_transit as TR
from buddy_geo import smoothstep

P = 'mixamorig:'
TID = 'PLAYER'                       # buddy_types key and material prefix (PLAYER_<Slot>)
ASSET = 'PLAYER_SAUSAGE_W86'

# ------------------------------------------------------------------ palettes (data for the manifest and the defaults)
# skin tones: Buddy_Skin, Buddy_Skin_Nose, Buddy_Skin_Inner (mouth inside), Buddy_Eye_Rim tinted together
SKIN_TONES = [
    ('Skin_01', 'Светлая', dict(skin=(244, 176, 148), nose=(236, 140, 116), inner=(212, 114, 90), rim=(184, 112, 90))),
    ('Skin_02', 'Сосисочная (как у NPC)', dict(skin=(236, 152, 106), nose=(226, 128, 94), inner=(204, 112, 80), rim=(150, 92, 70))),
    ('Skin_03', 'Смуглая', dict(skin=(206, 138, 96), nose=(212, 112, 80), inner=(178, 96, 70), rim=(136, 82, 60))),
    ('Skin_04', 'Тёмная', dict(skin=(160, 102, 70), nose=(168, 90, 64), inner=(140, 76, 56), rim=(102, 60, 42))),
    ('Skin_05', 'Очень тёмная', dict(skin=(104, 66, 46), nose=(116, 66, 48), inner=(96, 54, 40), rim=(66, 40, 28))),
]
DEFAULT_SKIN = 'Skin_02'
# clothing swatches: main / trim (cuffs, ribs, pockets, turn-ups) / accent (stripes, zip, buttons, cords: contrasts)
SWATCHES = [
    ('Sw_01', 'Белый', (234, 232, 226), (206, 204, 198), (52, 54, 58)),
    ('Sw_02', 'Серый', (128, 132, 138), (104, 108, 114), (236, 236, 232)),
    ('Sw_03', 'Чёрный', (44, 46, 50), (30, 32, 36), (236, 236, 232)),
    ('Sw_04', 'Красный', (178, 58, 44), (146, 44, 34), (240, 238, 232)),
    ('Sw_05', 'Синий', (58, 86, 146), (44, 66, 116), (236, 236, 232)),
    ('Sw_06', 'Зелёный', (82, 110, 70), (64, 88, 54), (236, 236, 232)),
    ('Sw_07', 'Жёлтый', (232, 184, 54), (204, 154, 38), (48, 50, 54)),
    ('Sw_08', 'Бежевый', (176, 156, 116), (148, 130, 94), (56, 54, 50)),
]
SWATCH = {k: (name, m, t, a) for k, name, m, t, a in SWATCHES}

SLOTS = {
    'Top_Main': (SWATCH['Sw_01'][1], 0.85), 'Top_Trim': (SWATCH['Sw_01'][2], 0.85), 'Top_Accent': (SWATCH['Sw_01'][3], 0.6),
    'Bottom_Main': (SWATCH['Sw_05'][1], 0.9), 'Bottom_Trim': (SWATCH['Sw_05'][2], 0.9), 'Bottom_Accent': (SWATCH['Sw_05'][3], 0.7),
    'Hair': ((92, 64, 46), 0.8), 'Hair_Part': ((70, 48, 34), 0.8), 'Stubble': ((110, 82, 66), 0.95),
    'Cap': ((52, 66, 104), 0.8), 'Cap_Peak': ((40, 52, 84), 0.8), 'Beanie': ((60, 62, 68), 0.95),
    'Bandana': ((178, 58, 44), 0.85), 'Bandana_Dots': ((244, 240, 232), 0.85), 'Glasses': ((34, 34, 38), 0.35),
    'Socks': ((236, 234, 228), 0.9), 'Shoe_Upper': ((226, 226, 222), 0.7), 'Shoe_Sole': ((70, 72, 78), 0.6),
    'Shoe_Lace': ((244, 244, 240), 0.7),
}
TYPE = dict(label='Игрок: настраиваемая сосиска (W86)', group='Игрок', hand_props=False, slots=SLOTS, colourways=[],
            look=dict(skin=SKIN_TONES[1][2]['skin'], nose=SKIN_TONES[1][2]['nose'], rim=SKIN_TONES[1][2]['rim']))

# ------------------------------------------------------------------ helpers
def tag(objs, part):
    for o in objs:
        o['pl_part'] = part
    return objs


def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _dt(pieces, garment):
    return T._decal_t(pieces, garment)


def _widen(rows, z0=0.95, z1=0.80, extra=0.004):
    """Tops worn loose over the trousers: the lower rows a little wider and deeper so the hem hangs clear of every
    waistband (the shared tee rows clear the plain waistband by only ~0.5 mm at the sides)."""
    out = []
    for z, rx, ry, dy in rows:
        k = smoothstep(z0, z1, z)
        out.append((z, rx + extra * k, ry + extra * k, dy))
    return out

@contextmanager
def lighter(**parts):
    """Temporarily lower the crowd resolution of some procedural parts (G.LOD, in memory only) for the player's
    tri budget: the heaviest full outfit must stay under the crowd LOD0 average."""
    old = {k: G.LOD.get(k) for k in parts}
    G.LOD.update(parts)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                G.LOD.pop(k, None)
            else:
                G.LOD[k] = v


def waist_on_hips(objs, z_lo=0.720, z_hi=0.805):
    """The waistband and seat of a bottom follow the pelvis (mixamorig:Hips) only, as a real waistband does: the
    weights transferred from the body gave the waist rows thigh influence near the hip joint, so they bulged out
    through every top's hem when the hip flexed (sitting, crouching). Below z_lo the transferred weights stay."""
    for ob in objs:
        names = {g.index: g.name for g in ob.vertex_groups}
        per = []
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            w = {names[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
            h = smoothstep(z_lo, z_hi, p.z)
            if h > 1e-4:
                w = {b: x * (1 - h) for b, x in w.items()}
                w[P + 'Hips'] = w.get(P + 'Hips', 0.0) + h
            per.append(w)
        ob.vertex_groups.clear()
        C.set_weights(ob, per)
    return objs

def hem_on_hips(objs, z_lo=0.800, z_hi=0.880, front_lo=0.700, front=0.6):
    """A top's lower part follows the pelvis like the waistband under it (same layer order in every pose): the body
    transfer gave its sides ~50 % thigh weight, so the sides folded in through the waistband when the hip flexed.
    Below the hips the front of a long top blends toward the thighs (left / right by x), so it rides up on them when
    the player sits or crouches instead of letting the trouser legs through it."""
    for ob in objs:
        names = {g.index: g.name for g in ob.vertex_groups}
        per = []
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            w = {names[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
            h = smoothstep(z_hi, z_lo, p.z)
            if h > 1e-4:
                w = {b: x * (1 - h) for b, x in w.items()}
                w[P + 'Hips'] = w.get(P + 'Hips', 0.0) + h
            t = front * smoothstep(z_lo, front_lo, p.z) * smoothstep(0.05, -0.05, p.y)      # front and sides
            if t > 1e-4:
                k = smoothstep(-0.07, 0.07, p.x)
                w = {b: x * (1 - t) for b, x in w.items()}
                w[P + 'LeftUpLeg'] = w.get(P + 'LeftUpLeg', 0.0) + t * k
                w[P + 'RightUpLeg'] = w.get(P + 'RightUpLeg', 0.0) + t * (1 - k)
            per.append(w)
        ob.vertex_groups.clear()
        C.set_weights(ob, per)
    return objs

# ------------------------------------------------------------------ base pieces (always on)
def base_shoes(M):
    return W.shoes(ASSET + '_Shoe', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])


def base_socks(M, src):
    return [_t(W.plain_socks(ASSET + '_Socks', M['Socks'], top=0.270), src)]

# ------------------------------------------------------------------ tops
TEE_ROWS = _widen(C.BASE_TEE_ROWS)                     # arm row 6
SHIRT_ROWS = _widen([(.776, .192, .130, -.010), (.788, .196, .132, -.010)] + [r for r in C.BASE_TEE_ROWS if r[0] >= 0.86],
                    z0=0.95, z1=0.80, extra=0.004)      # arm row 6, a little longer than the tee
# low stand collar of the tracksuit top (the gopnik's, 2 cm lower so a beard clears it when the head drops)
TRACK_COLLAR = [(1.250, .172, .167), (1.276, .163, .158), (1.296, .158, .152), (1.300, .153, .147), (1.295, .149, .143), (1.255, .151, .145)]


def top_tee(pid, M, src):
    """Crew-neck tee, short sleeves, rib neckband and sleeve hems in the trim colour."""
    tee = W.top(f'{ASSET}_{pid}_Tee', TEE_ROWS, 6, C.TEE_SLEEVE, (.806, .188, .128, -.004), [M['Top_Main'], M['Top_Trim']],
                row_mat=[0] * 9 + [1] * 3, sleeve_mat=[0] * 4 + [1] * 2)
    return [_t(tee, src, C.no_head)]


def top_hoodie(pid, M, src):
    """The city student's hoodie (Fedya's A hoodie): kangaroo pocket, hood down round the neck, rib cuffs and hem,
    drawcords in the accent colour."""
    pre = f'{ASSET}_{pid}'
    with lighter(big_decal=dict(step=0.032), hood=dict(seg=10, subdiv=0), hood_pouch=dict(seg=12, rings=8), cord=dict(seg=5)):
        hoodie, pocket, out = T._hoodie(pre, {'Hoodie': M['Top_Main'], 'Hoodie_Rib': M['Top_Trim']}, src)
        out.append(T._hood_down(pre, M['Top_Main']))
        for s in (1, -1):
            path = [(s * 0.040, -0.168, 1.236), (s * 0.044, -0.192, 1.17), (s * 0.046, -0.198, 1.10), (s * 0.045, -0.199, 1.045)]
            out.append(_t(G.tube(f'{pre}_Cord_{s}', path, 0.0062, M['Top_Accent'], **G.res('cord', seg=8)), src,
                          lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else w))
    return out


WORK_JACKET = [(.742, .209, .143, -.012), (.756, .210, .144, -.012)] + W.JACKET[2:]    # hip length; arm row 7 as W.JACKET


def top_work_jacket(pid, M, src):
    """Hip-length canvas work jacket (buddy_types._jacket cut at the hip: a mid-thigh hem let the trouser legs through
    it when sitting): fold-down collar, button placket, two chest pockets with flaps and two lower patch pockets in
    the trim colour, buttons in the accent colour."""
    pre = f'{ASSET}_{pid}'
    jacket = _t(W.top(pre + '_Jacket', WORK_JACKET, 7, W.JACKET_SLEEVE, (.756, .200, .135, -.012), [M['Top_Main']]), src, C.no_head)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Top_Trim'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=26, tip=0.030, thick=0.007)
    deco = [W.front_decal(pre + '_Placket', [(-0.010, 0.747), (0.010, 0.747), (0.010, 1.250), (-0.010, 1.250)], jacket, M['Top_Trim'],
                          0.0035, step=0.012)]
    for s in (1, -1):
        x0, x1 = 0.064, 0.142
        deco.append(W.front_decal(f'{pre}_ChestPocket_{s}', [(s * x0, 1.050), (s * x1, 1.050), (s * x1, 1.130), (s * x0, 1.130)][::s],
                                  jacket, M['Top_Trim'], 0.0035, thickness=0.004, step=0.012))
        deco.append(W.front_decal(f'{pre}_ChestFlap_{s}', [(s * (x0 - 0.004), 1.120), (s * (x1 + 0.004), 1.120),
                                                          (s * (x1 + 0.004), 1.154), (s * (x0 - 0.004), 1.154)][::s],
                                  jacket, M['Top_Main'], 0.0085, thickness=0.004, step=0.012))
        deco.append(W.front_decal(f'{pre}_Pocket_{s}', [(s * 0.050, 0.790), (s * 0.160, 0.790), (s * 0.160, 0.900), (s * 0.050, 0.900)][::s],
                                  jacket, M['Top_Trim'], 0.0035, thickness=0.004, step=0.012))
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]
    btn = W.buttons(pre + '_Btn', jacket, M['Top_Accent'], [(0.0, z) for z in (1.190, 1.095, 1.000, 0.905, 0.810)], r=0.0085,
                    offset=0.0070)
    return out + [_t(o, jsrc) for o in btn]


def top_tracksuit(pid, M, src):
    """Zip-up tracksuit top (the gopnik's cut): rib hem and cuffs in the trim colour, a low stand collar, the zip and
    three stripes down each sleeve in the accent colour."""
    pre = f'{ASSET}_{pid}'
    jacket = W.top(pre + '_Jacket', W.HOODIE, 7, W.HOODIE_SLEEVE, (.750, .174, .118, -.010), [M['Top_Main'], M['Top_Trim']],
                   row_mat=[1] + [0] * 13, sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(jacket, src, C.no_head)
    secs = [((0, 0.002, z), (1, 0, 0), (0, 1, 0), rx, ry) for z, rx, ry in TRACK_COLLAR]
    collar = _t(G.loft(pre + '_Collar', secs, M['Top_Main'], seg=32, cap_start=False, cap_end=False), src, C.no_head)
    out = [jacket, collar]
    out += _dt([W.front_decal(pre + '_Zip', [(-0.0045, 0.752), (0.0045, 0.752), (0.0045, 1.250), (-0.0045, 1.250)], jacket,
                              M['Top_Accent'], 0.003)], jacket)
    czip = W.front_decal(pre + '_CollarZip', [(-0.0045, 1.250), (0.0045, 1.250), (0.0045, 1.296), (-0.0045, 1.296)], collar,
                         M['Top_Accent'], 0.0025)
    pull = W.box(pre + '_ZipPull', Vector((0.0, -0.158, 1.280)), (0.0065, 0.003, 0.012), M['Top_Accent'])
    out += [C.rigid(czip, 'Spine2'), C.rigid(pull, 'Spine2')]
    stripes = []
    for s in (1, -1):
        x0, x1 = sorted((s * 0.165, s * 0.568))
        for k, c in enumerate((-0.018, 0.0, 0.018)):
            stripes.append(G.decal(f'{pre}_Stripe_{s}_{k}', BD.stripe_outline(x0, x1, c - 0.0045, c + 0.0045, step=0.03), W.TOP(1.6),
                                   [jacket], 0.0025, M['Top_Accent'], step=0.03))
    return out + _dt(stripes, jacket)


def top_shirt(pid, M, src):
    """Untucked button shirt with a fold-down collar, sleeves rolled above the elbow (trim colour), a chest pocket,
    placket and buttons."""
    pre = f'{ASSET}_{pid}'
    shirt = W.top(pre + '_Shirt', SHIRT_ROWS, 6, TR.OPEN_SLEEVE, (.790, .186, .126, -.006), [M['Top_Main'], M['Top_Trim']],
                  sleeve_mat=[0] * 5 + [1] * 5)
    _t(shirt, src, C.no_head)
    ssrc = C.weight_source([shirt])
    collar = _t(W.collar(pre + '_Collar', M['Top_Main'], thick=0.005), ssrc, C.no_head)
    deco = [W.front_decal(pre + '_Placket', [(-0.011, 0.780), (0.011, 0.780), (0.011, 1.246), (-0.011, 1.246)], shirt, M['Top_Trim'],
                          0.0030, step=0.012),
            W.front_decal(pre + '_Pocket', [(0.058, 1.050), (0.128, 1.050), (0.128, 1.130), (0.058, 1.130)], shirt, M['Top_Trim'],
                          0.0030, thickness=0.003, step=0.012)]
    deco += W.buttons(pre + '_Btn', shirt, M['Top_Accent'], [(0.0, z) for z in (1.200, 1.115, 1.030, 0.945, 0.860)], r=0.0070,
                      offset=0.0055)
    return [shirt, collar] + [_t(o, ssrc) for o in deco]

# ------------------------------------------------------------------ bottoms
JEANS_LEGS, JEANS_CUFF = W.LEGS_ANKLE, W.ANKLE_CUFF          # the student's jeans with a turn-up
TRACK_LEGS, TRACK_CUFF = BD.GOP_LEGS, BD.GOP_CUFF              # the gopnik's track pants, rib cuffs
CARGO_LEGS = [(.70, .096), (.60, .094), (.50, .091), (.43, .088), (.34, .086), (.26, .086), (.20, .087), (.178, .088)]   # mechanic
CARGO_CUFF = [(.166, .097), (.214, .098), (.219, .091)]
SHORTS_LEGS = [(.70, .092), (.62, .092), (.555, .091), (.505, .090)]     # loose knee-length shorts, turned-up hem
SHORTS_CUFF = [(.494, .097), (.540, .097), (.544, .091)]
WORK_LEGS = [r for r in W.LEGS_LONG if r[0] >= 0.26] + [(.200, .074), (.160, .078), (.152, .073)]   # hem clear of the heel


def _back_pockets(pre, target, M, slot='Bottom_Trim'):
    out = []
    for s in (1, -1):
        out.append(G.decal(f'{pre}_BackPocket_{s}', [(s * 0.040, 0.730), (s * 0.140, 0.730), (s * 0.146, 0.818), (s * 0.036, 0.818)][::s],
                           W.BACK(), [target], 0.0035, M[slot], step=0.020))
    return out


def bottom_jeans(pid, M, src):
    pre = f'{ASSET}_{pid}'
    jeans = _t(W.bottoms(pre + '_Jeans', JEANS_LEGS, [M['Bottom_Main'], M['Bottom_Trim']], cuff=JEANS_CUFF), src)
    return [jeans] + _dt(_back_pockets(pre, jeans, M), jeans)


def bottom_track(pid, M, src):
    pre = f'{ASSET}_{pid}'
    pants = _t(W.bottoms(pre + '_Pants', TRACK_LEGS, [M['Bottom_Main'], M['Bottom_Trim']], cuff=TRACK_CUFF), src)
    stripes = []
    for s in (1, -1):
        for k, c in enumerate((-0.018, 0.0, 0.018)):
            stripes.append(G.decal(f'{pre}_Stripe_{s}_{k}', BD.stripe_outline(c - 0.0045, c + 0.0045, 0.25, 0.80, step=0.03), G.SIDE(s),
                                   [pants], 0.0025, M['Bottom_Accent'], step=0.03))
    return [pants] + _dt(stripes, pants)


def bottom_cargo(pid, M, src):
    pre = f'{ASSET}_{pid}'
    tr = _t(W.bottoms(pre + '_Cargo', CARGO_LEGS, [M['Bottom_Main'], M['Bottom_Trim']], cuff=CARGO_CUFF), src)
    deco = []
    for s in (1, -1):
        axes = ((s * 0.7 + s * B.LEG_X, 0, 0), (0, -s, 0), (0, 0, 1), (-s, 0, 0))
        deco.append(G.decal(f'{pre}_CargoPocket_{s}', [(-0.054, 0.420), (0.054, 0.420), (0.054, 0.540), (-0.054, 0.540)], axes, [tr],
                            0.004, M['Bottom_Trim'], thickness=0.008, step=0.020))
        deco.append(G.decal(f'{pre}_CargoFlap_{s}', [(-0.058, 0.528), (0.058, 0.528), (0.058, 0.560), (-0.058, 0.560)], axes, [tr],
                            0.012, M['Bottom_Main'], thickness=0.005, step=0.020))
    return [tr] + _dt(deco + _back_pockets(pre, tr, M), tr)


def bottom_shorts(pid, M, src):
    pre = f'{ASSET}_{pid}'
    sh = _t(W.bottoms(pre + '_Shorts', SHORTS_LEGS, [M['Bottom_Main'], M['Bottom_Trim']], cuff=SHORTS_CUFF), src)
    return [sh] + _dt(_back_pockets(pre, sh, M), sh)


def bottom_work(pid, M, src):
    """Straight work trousers: reinforced knee patches, back pockets and a rule pocket on the right thigh."""
    pre = f'{ASSET}_{pid}'
    tr = _t(W.bottoms(pre + '_Work', WORK_LEGS, [M['Bottom_Main']]), src)
    deco = []
    for s in (1, -1):
        deco.append(W.front_decal(f'{pre}_Knee_{s}', [(s * 0.052, 0.385), (s * 0.148, 0.385), (s * 0.148, 0.505), (s * 0.052, 0.505)][::s],
                                  tr, M['Bottom_Trim'], 0.0040, step=0.015))
    axes = ((-0.7 - B.LEG_X, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))
    deco.append(G.decal(pre + '_RulePocket', [(-0.030, 0.560), (0.030, 0.560), (0.030, 0.700), (-0.030, 0.700)], axes, [tr], 0.0035,
                        M['Bottom_Trim'], thickness=0.004, step=0.020))
    return [tr] + _dt(deco + _back_pockets(pre, tr, M), tr)

# ------------------------------------------------------------------ hair (rigid on Head)
FRINGE_LOWER = W.zprofile([(0, 1.692), (30, 1.684), (55, 1.640), (80, 1.575), (100, 1.540), (130, 1.488), (180, 1.455)])   # longer mop
QUIFF_LOWER = W.zprofile([(0, 1.692), (30, 1.684), (55, 1.650), (80, 1.600), (100, 1.578), (130, 1.530), (180, 1.502)])    # faded sides
# Hat lines: the lower edges of the three hats (cap, beanie, bandana); the under-hat hair reaches HAT_TUCK, 8 mm
# above the highest of them, so no bald strip shows between hair and hat and the hair stays inside every hat.
CAP_BASE = W.zprofile([(0, 1.662), (90, 1.646), (180, 1.626)])              # buddy_pool_oldtown2.baseball_cap
BEANIE_BASE = W.zprofile([(0, 1.668), (90, 1.640), (180, 1.616)])           # buddy_wear.beanie
BANDANA_BASE = W.zprofile([(0, 1.672), (90, 1.650), (180, 1.624)])


def HAT_TUCK(phi):
    return max(CAP_BASE(phi), BEANIE_BASE(phi), BANDANA_BASE(phi)) + 0.008


def hair_buzz(pid, M):
    return [W.hair(f'{ASSET}_{pid}_Buzz', M['Hair'], 'buzz')]


def hair_side_part(pid, M):
    h = W.hair(f'{ASSET}_{pid}_Slick', M['Hair'], 'slick')
    return [h, W.hair_part(f'{ASSET}_{pid}_Part', M['Hair_Part'], h, x=-0.050)]


def hair_fringe(pid, M):
    """A mop: longer at the sides and back, a ragged fringe over the forehead (the junkie's fringe band over a thin
    base so the two layers never cross)."""
    base, _ = W.shell(f'{ASSET}_{pid}_Mop', M['Hair'], FRINGE_LOWER,
                      off=lambda phi, u: 0.0015 + 0.008 * smoothstep(0.15, 0.55, u) * (0.6 + 0.4 * max(0.0, math.cos(phi))),
                      thick=0.007, seg=32, rows=6)
    return [C.rigid(base, 'Head')] + _fringe(f'{ASSET}_{pid}_Fringe', M['Hair'])


def _fringe(prefix, material, ragged=((1.664, 1.682), 11.0), seg=22):
    """buddy_wear.fringe (the junkie's ragged fringe band) with 22 columns instead of 28 (tri budget)."""
    (lo_a, lo_b), period = ragged

    def lower(phi):
        t = (math.degrees(phi) / period) % 1.0
        return W.h_of(lo_a + (lo_b - lo_a) * abs(2 * t - 1))
    # the band sinks into the mop toward its upper edge (same material): no ledge where it ends
    ob, _ = W.shell(prefix, material, lower, lambda phi: W.h_of(1.716), off=lambda phi, u: 0.006 - 0.0065 * u, thick=0.007, seg=seg,
                    rows=3, arc=(math.radians(-48), math.radians(48)))
    return [C.rigid(ob, 'Head')]


def hair_quiff(pid, M):
    """Short faded sides and a combed-up quiff at the front."""
    def off(phi, u):
        front = max(0.0, math.cos(phi)) ** 2
        bump = math.sin(math.pi * min(1.0, u / 0.8)) ** 0.8
        return 0.002 + 0.006 * smoothstep(0.0, 0.4, u) + 0.026 * front * bump
    ob, _ = W.shell(f'{ASSET}_{pid}_Quiff', M['Hair'], QUIFF_LOWER, off=off, thick=0.008, seg=32, rows=8)
    return [C.rigid(ob, 'Head')]


def hair_under_hat(pid, M, lower):
    """The style's sides and back under a hat: a thin band from its own lower edge up to HAT_TUCK (open at the front,
    where every hat covers the hairline)."""
    hi = lambda phi: max(HAT_TUCK(phi), lower(phi) + 0.004)
    ob, _ = W.shell(f'{ASSET}_{pid}_Hat', M['Hair'], lower, hi, off=0.0015, thick=0.0030, seg=32, rows=3,
                    arc=(math.radians(40), math.radians(320)))
    return [C.rigid(ob, 'Head')]

# ------------------------------------------------------------------ facial hair (rigid on Head; beards Head/Neck)
def beard_stubble(pid, M, skin):
    return T._face(skin, lambda head: W.stubble(f'{ASSET}_{pid}_Stubble', M['Stubble'], head, dots=110, seed=86))


def beard_mustache(pid, M, skin):
    return W.mustache(f'{ASSET}_{pid}_Mustache', M['Hair'], droop=0.004, size=1.35)


def beard_full(pid, M, skin):
    """Short trimmed beard along the jaw (the VIP beard, a little fuller) with a moustache."""
    b = VIP.jaw_beard(f'{ASSET}_{pid}_Beard', M['Hair'], top=[(0, 1.382), (14, 1.386), (28, 1.396), (46, 1.420), (66, 1.452), (80, 1.480)],
                      bot=[(0, 1.318), (20, 1.322), (40, 1.342), (60, 1.380), (80, 1.430)], bulge=0.006, rows=3, base=0.004,
                      thick=0.005, arc_deg=80.0, cols=26)
    return [b] + W.mustache(f'{ASSET}_{pid}_Mustache', M['Hair'], droop=0.004, size=0.95)


def beard_goatee(pid, M, skin):
    """Chin goatee (the hamlet one) and a light moustache."""
    g = VIP.jaw_beard(f'{ASSET}_{pid}_Goatee', M['Hair'], top=[(0, 1.385), (18, 1.390), (30, 1.380)], bot=[(0, 1.315), (18, 1.322), (30, 1.350)],
                      bulge=0.006, rows=3, base=0.004, thick=0.004, arc_deg=30.0, cols=12)
    return [g] + W.mustache(f'{ASSET}_{pid}_Mustache', M['Hair'], droop=0.006, size=0.8)

# ------------------------------------------------------------------ headwear / accessory (rigid on Head)
def head_cap(pid, M):
    objs, _base = OT2.baseball_cap(f'{ASSET}_{pid}_Cap', M['Cap'], M['Cap_Peak'])
    return objs


def head_beanie(pid, M):
    return W.beanie(f'{ASSET}_{pid}_Beanie', M['Beanie'])


def head_bandana(pid, M):
    """Bandana tied over the whole head (a head wrap) with the classic white dots (the babushka headscarf's decal dots),
    knotted at the back with two short tails (the mechanic's knot)."""
    pre = f'{ASSET}_{pid}_Bandana'
    wrap, _ = W.shell(pre, M['Bandana'], BANDANA_BASE, None, off=lambda phi, u: 0.008 + 0.003 * math.sin(math.pi * min(1.0, u * 1.3)),
                      thick=0.006, seg=28, rows=5)
    out = [wrap]
    dots = []
    for u, v in ((-0.064, 1.706), (0.0, 1.724), (0.064, 1.706), (-0.034, 1.746), (0.034, 1.746)):
        dots.append(G.decal(f'{pre}_DotF_{len(dots)}', C.ellipse(u, v, 0.0105, 0.0105, 8), W.FRONT(), [wrap], 0.0018, M['Bandana_Dots']))
    for s in (1, -1):
        for u, v in ((-0.050, 1.690), (0.030, 1.700), (-0.010, 1.736)):
            dots.append(G.decal(f'{pre}_DotS_{s}_{len(dots)}', C.ellipse(u * s, v, 0.0105, 0.0105, 8), G.SIDE(s), [wrap], 0.0018,
                                M['Bandana_Dots']))
    for u, v in ((-0.050, 0.020), (0.050, 0.020), (0.0, -0.050), (0.0, 0.080)):
        dots.append(G.decal(f'{pre}_DotT_{len(dots)}', C.ellipse(u, v, 0.0105, 0.0105, 8), W.TOP(), [wrap], 0.0018, M['Bandana_Dots']))
    for u, v in ((-0.060, 1.680), (0.060, 1.680)):
        dots.append(G.decal(f'{pre}_DotB_{len(dots)}', C.ellipse(u, v, 0.0105, 0.0105, 8), W.BACK(), [wrap], 0.0018, M['Bandana_Dots']))
    out += dots
    kp, _ = W.head_at(math.pi, BANDANA_BASE(math.pi) + 0.022, 0.022)
    out.append(G.ellipsoid(pre + '_Knot', kp, (0.026, 0.017, 0.021), M['Bandana'], seg=10, rings=6))
    for s in (1, -1):
        d = Vector((s * 0.62, 0.22, -0.75)).normalized()
        side = Vector((0, 1, 0)).cross(d).normalized()
        nrm = d.cross(side).normalized()
        c = kp + d * 0.044 + Vector((0, 0.004, 0))
        rot = Matrix((side, d, nrm)).transposed()
        out.append(G.ellipsoid(f'{pre}_Tail_{s}', c, (0.019, 0.042, 0.0045), M['Bandana'], rot=rot, seg=8, rings=5))
    return [C.rigid(o, 'Head') for o in out]


def head_glasses(pid, M, rx=0.056, rz=0.062, n=16, seg=5):
    """buddy_wear.glasses (the clerk's frames) with 16-point rims and 5-sided tubes (tri budget)."""
    pre = f'{ASSET}_{pid}_Glasses'
    fm = M['Glasses']
    out = []
    for s in (1, -1):
        c = Vector((s * (B.EYE_C[0] + 0.006), -0.162, B.EYE_C[2]))
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            ca, sa = math.cos(a), math.sin(a)
            wrap = 0.010 * max(0.0, ca * s) ** 2
            ring.append(c + Vector((rx * ca, wrap, rz * sa)))
        ring += ring[:2]
        out.append(G.tube(f'{pre}_Rim_{s}', ring, 0.0042, fm, seg=seg))
        hinge = c + Vector((s * rx, 0.010, 0.006))
        temple = [hinge, hinge + Vector((s * 0.024, 0.040, -0.002)), Vector((s * 0.150, -0.030, 1.552)), Vector((s * 0.153, 0.010, 1.532))]
        out.append(G.tube(f'{pre}_Temple_{s}', temple, 0.0035, fm, seg=seg))
    gap = B.EYE_C[0] + 0.006 - rx
    out.append(G.tube(pre + '_Bridge', [Vector((gap, -0.163, 1.574)), Vector((0, -0.167, 1.580)), Vector((-gap, -0.163, 1.574))],
                      0.0038, fm, seg=seg))
    return [C.rigid(o, 'Head') for o in out]

# ------------------------------------------------------------------ option tables
# (id, display name RU, builder, hides: body regions switched off while the option is worn)
TOPS = [('Top_01', 'Футболка', top_tee, ['Body_Torso', 'Body_ArmUpper']),
        ('Top_02', 'Худи', top_hoodie, ['Body_Torso', 'Body_ArmUpper', 'Body_ArmMid', 'Body_ArmLower']),
        ('Top_03', 'Рабочая куртка', top_work_jacket, ['Body_Torso', 'Body_ArmUpper', 'Body_ArmMid', 'Body_ArmLower']),
        ('Top_04', 'Олимпийка', top_tracksuit, ['Body_Torso', 'Body_ArmUpper', 'Body_ArmMid', 'Body_ArmLower']),
        ('Top_05', 'Рубашка', top_shirt, ['Body_Torso', 'Body_ArmUpper', 'Body_ArmMid'])]
BOTTOMS = [('Bottom_01', 'Джинсы', bottom_jeans, ['Body_Pelvis', 'Body_Thigh', 'Body_Knee', 'Body_Shin']),
           ('Bottom_02', 'Спортивные штаны', bottom_track, ['Body_Pelvis', 'Body_Thigh', 'Body_Knee', 'Body_Shin']),
           ('Bottom_03', 'Карго', bottom_cargo, ['Body_Pelvis', 'Body_Thigh', 'Body_Knee', 'Body_Shin']),
           ('Bottom_04', 'Шорты', bottom_shorts, ['Body_Pelvis', 'Body_Thigh']),
           ('Bottom_05', 'Рабочие брюки', bottom_work, ['Body_Pelvis', 'Body_Thigh', 'Body_Knee', 'Body_Shin'])]
HAIRS = [('Hair_01', 'Лысый', None, None),
         ('Hair_02', 'Ёжик', hair_buzz, W.HAIRLINE),
         ('Hair_03', 'Пробор', hair_side_part, W.HAIRLINE),
         ('Hair_04', 'Чёлка', hair_fringe, FRINGE_LOWER),
         ('Hair_05', 'Кок', hair_quiff, QUIFF_LOWER)]
BEARDS = [('Beard_01', 'Без бороды', None),
          ('Beard_02', 'Щетина', beard_stubble),
          ('Beard_03', 'Усы', beard_mustache),
          ('Beard_04', 'Борода', beard_full),
          ('Beard_05', 'Эспаньолка', beard_goatee)]
# under_hat: the hair option swaps to its Hair_NN_Hat mesh while this is worn
HEADS = [('Head_01', 'Ничего', None, False),
         ('Head_02', 'Кепка', head_cap, True),
         ('Head_03', 'Шапка', head_beanie, True),
         ('Head_04', 'Бандана', head_bandana, True),
         ('Head_05', 'Очки', head_glasses, False)]
DEFAULTS = {'hair': 'Hair_03', 'beard': 'Beard_01', 'top': 'Top_01', 'bottom': 'Bottom_01', 'head': 'Head_01', 'skin': DEFAULT_SKIN,
            'top_swatch': 'Sw_01', 'bottom_swatch': 'Sw_05'}
OPTION_SWATCH = {'Top_01': 'Sw_01', 'Top_02': 'Sw_02', 'Top_03': 'Sw_08', 'Top_04': 'Sw_03', 'Top_05': 'Sw_05',
                 'Bottom_01': 'Sw_05', 'Bottom_02': 'Sw_03', 'Bottom_03': 'Sw_06', 'Bottom_04': 'Sw_08', 'Bottom_05': 'Sw_02'}
# base body regions (post_player_w86.split_body): name, RU description
BODY_REGIONS = [('Body_Head', 'Голова, уши, нос (никогда не скрывается)'),
                ('Body_Hands', 'Кисти и запястья (никогда не скрываются)'),
                ('Body_Torso', 'Грудь, живот, спина'),
                ('Body_Pelvis', 'Таз и верх бёдер'),
                ('Body_ArmUpper', 'Плечи'),
                ('Body_ArmMid', 'Руки от плеча до локтя'),
                ('Body_ArmLower', 'Предплечья'),
                ('Body_Thigh', 'Верх бёдер'),
                ('Body_Knee', 'Бёдра над коленом (под шортами остаются видны в штанине)'),
                ('Body_Shin', 'Колени и голени (ниже верха носков тело удалено: там всегда носки и кеды)')]


def player(body, face, M, skin):
    src = C.weight_source([body])
    out = tag(base_shoes(M), 'Shoes') + tag(base_socks(M, src), 'Socks')
    for pid, _n, fn, _h in TOPS:
        out += tag(hem_on_hips(fn(pid, M, src)), pid)
    for pid, _n, fn, _h in BOTTOMS:
        out += tag(waist_on_hips(fn(pid, M, src)), pid)
    for pid, _n, fn, lower in HAIRS:
        if fn is not None:
            out += tag(fn(pid, M), pid)
            out += tag(hair_under_hat(pid, M, lower), pid + '_Hat')
    for pid, _n, fn in BEARDS:
        if fn is not None:
            out += tag(fn(pid, M, skin), pid)
    for pid, _n, fn, _u in HEADS:
        if fn is not None:
            out += tag(fn(pid, M), pid)
    return out


def register():
    """Add the type to buddy_types (in memory only)."""
    T.TYPES[TID] = TYPE
    T.BUILDERS[TID] = player
