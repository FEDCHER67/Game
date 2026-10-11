"""District pool 'Промзона' (industrial zone, TASK-000277): the migrant foreman in a hard hat and a yellow hi-vis vest
over a track jacket (TASK-000278), the old sea dog (bosun) on the quay (TASK-000279). Out of the pool, still buildable:
the sleepy watchman (TASK-000278) and the dock worker in a life vest with a rope coil (TASK-000279). None of them carries anything in the hands (Vadim: only five types do, see buddy_types.build).
Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS. No bpy calls at import time."""
import math
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Промзона'
GOLD = ((214, 174, 76), 0.28, 'metal')
METAL = 'metal'

TYPES = {
    'PROM_GUARD': dict(
        label='Вахтёр', group=GROUP, body=dict(belly=1.0), arm_down=66.0, face=dict(Blink=0.7, Happy=0.1),
        look=dict(brow=(196, 192, 186)),
        slots={'Jacket': ((30, 32, 36), 0.8), 'Collar': ((26, 28, 32), 0.8), 'Buttons': ((200, 170, 80), 0.3, METAL),
               'Trousers': ((30, 32, 36), 0.85), 'Socks': ((30, 30, 34), 0.9), 'Shoes': ((20, 20, 22), 0.25),
               'Shoe_Sole': ((30, 30, 30), 0.6), 'Cap': ((30, 32, 36), 0.8), 'CapBand': ((90, 96, 104), 0.8),
               'Visor': ((16, 16, 18), 0.2), 'Gold': GOLD, 'Mustache': ((190, 186, 180), 0.95), 'EyeBags': ((168, 130, 146), 0.8),
               'Radio': ((24, 24, 26), 0.5), 'Radio_Light': ((240, 60, 40), 0.3), 'Hair': ((200, 198, 192), 1.0)},
        colourways=[{'Jacket': (40, 60, 48), 'Collar': (34, 52, 42), 'Trousers': (40, 60, 48), 'Cap': (40, 60, 48),
                     'CapBand': (180, 40, 40)},
                    {'Jacket': (40, 48, 80), 'Collar': (34, 40, 70), 'Trousers': (40, 48, 80), 'Cap': (40, 48, 80)}]),
    'PROM_FOREMAN': dict(
        label='Прораб-эмигрант', group=GROUP, body=dict(belly=0.3), face=dict(Happy=0.45, Surprised=0.1),
        look=dict(skin=(196, 136, 92), nose=(184, 116, 80), brow=(30, 26, 24)),
        slots={'Track': ((36, 44, 70), 0.75), 'Track_Rib': ((28, 34, 56), 0.75), 'Stripes': ((236, 236, 232), 0.8),
               'Zip': ((200, 200, 204), 0.3, METAL), 'Vest': ((220, 240, 60), 0.6), 'Reflect': ((210, 214, 220), 0.25),
               'Trousers': ((92, 94, 100), 0.9), 'Dust': ((176, 166, 146), 1.0), 'Socks': ((236, 234, 228), 0.9),
               'Shoe_Upper': ((110, 110, 116), 0.7), 'Shoe_Sole': ((220, 216, 206), 0.6), 'Shoe_Lace': ((60, 60, 64), 0.7),
               'Hat': ((246, 246, 242), 0.35), 'Hair': ((26, 24, 22), 0.85), 'Mustache': ((26, 24, 22), 0.9),
               'Stubble': ((40, 34, 30), 0.95), 'Pencil': ((240, 200, 60), 0.7), 'Pencil_Tip': ((40, 40, 40), 0.6),
               'Tape': ((250, 200, 40), 0.5), 'Tape_Belt': ((30, 30, 32), 0.5)},
        colourways=[{'Vest': (250, 120, 30), 'Hat': (250, 200, 40), 'Track': (30, 30, 34), 'Track_Rib': (24, 24, 28)},
                    {'Track': (120, 30, 40), 'Track_Rib': (96, 24, 32), 'Hat': (230, 70, 50), 'Trousers': (60, 70, 52)}]),
    'PROM_DOCKER': dict(
        label='Работник причала', group=GROUP, body=dict(belly=0.5), arm_down=70.0, face=dict(Happy=0.2, Blink=0.25),
        look=dict(skin=(220, 150, 112), nose=(212, 124, 92), brow=(60, 48, 40)),
        slots={'Jacket': ((34, 44, 70), 0.85), 'Collar': ((28, 36, 58), 0.85), 'Vest': ((236, 70, 40), 0.55),
               'Reflect': ((210, 214, 220), 0.25), 'Buckle': ((24, 24, 26), 0.4), 'Trousers': ((40, 42, 48), 0.9),
               'Boots': ((36, 40, 36), 0.4), 'Boots_Sole': ((22, 22, 22), 0.6), 'Cap': ((176, 40, 40), 0.95),
               'Rope': ((200, 172, 120), 1.0), 'Mustache': ((96, 70, 50), 0.9), 'Stubble': ((90, 72, 60), 0.95)},
        colourways=[{'Jacket': (52, 56, 60), 'Collar': (42, 46, 50), 'Cap': (34, 44, 70), 'Vest': (250, 140, 30)},
                    {'Jacket': (60, 70, 50), 'Collar': (50, 58, 42), 'Cap': (230, 230, 226), 'Rope': (90, 140, 200)}]),
    'PROM_SAILOR': dict(
        label='Морской волк (боцман)', group=GROUP, body=dict(belly=0.6), arm_down=70.0, face=dict(Happy=0.3, Blink=0.35),
        look=dict(skin=(226, 150, 112), nose=(226, 110, 90), brow=(200, 196, 188)),
        slots={'Tel': ((246, 246, 242), 0.85), 'Tel_Stripe': ((34, 52, 110), 0.85), 'Coat': ((26, 30, 44), 0.8),
               'Brass': ((214, 174, 76), 0.28, METAL), 'Trousers': ((26, 30, 44), 0.85), 'Boots': ((20, 20, 22), 0.35),
               'Boots_Sole': ((30, 30, 30), 0.6), 'Cap': ((246, 246, 242), 0.6), 'CapBand': ((26, 30, 44), 0.8),
               'Visor': ((16, 16, 18), 0.2), 'Gold': GOLD, 'Beard': ((200, 196, 188), 0.95), 'Hair': ((200, 196, 188), 1.0),
               'Pipe': ((110, 64, 34), 0.5)},
        colourways=[{'Coat': (40, 44, 40), 'Trousers': (40, 44, 40), 'CapBand': (40, 44, 40)},
                    {'Tel_Stripe': (180, 40, 40), 'Cap': (26, 30, 44), 'Beard': (150, 90, 50), 'Hair': (150, 90, 50)}]),
}


# ------------------------------------------------------------------ shared pieces
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def hard_hat(prefix, shell_m):
    """Construction hard hat: a domed shell wider than the head, a short rim all round, a front peak, a ridge on top."""
    base = W.zprofile([(0, 1.676), (90, 1.664), (180, 1.652)])
    rows = [('fit', base, 0.012), (1.712, 0.168, 0.166, -0.004, 0.0), (1.752, 0.166, 0.164, -0.004, 0.0),
            (1.792, 0.148, 0.146, -0.004, 0.0), (1.824, 0.112, 0.110, -0.004, 0.0), (1.846, 0.060, 0.058, -0.004, 0.0),
            (1.852, 0.018, 0.017, -0.004, 0.0)]
    dome = W.ring_loft(prefix + '_Dome', rows, [shell_m], seg=32)
    rim = W.ring_loft(prefix + '_Rim', [('fit', base, 0.012), ('fit', base, 0.034)], [shell_m], seg=32, cap_top=False)
    G.solidify(rim, 0.006, offset=0.0)
    peak = W.peak(prefix + '_Peak', shell_m, base, length=0.060, droop=0.010, curve=0.010, span=70, off=0.014, thick=0.008)
    ridge = G.ellipsoid(prefix + '_Ridge', (0.0, 0.0, 1.838), (0.020, 0.124, 0.011), shell_m, seg=12, rings=8)
    return [C.rigid(o, 'Head') for o in (dome, rim, peak, ridge)], base


def safety_vest(prefix, M, src, thick=0.004):
    """Sleeveless vest (hi-vis, or a puffy life vest with thick=0.02) with two reflective bands round the body."""
    import buddy_pool_hamlet as HM
    vest = W.top(prefix + '_Vest', HM.VEST, 5, None, (.784, .206, .144, -.012), [M['Vest']])
    G.solidify(vest, thick, offset=1.0)
    _t(vest, src, C.no_head)
    vsrc = C.weight_source([vest])
    bands = []
    for k, z in enumerate((0.900, 0.985)):
        pts = [(-0.27, z - 0.014), (0.27, z - 0.014), (0.27, z + 0.014), (-0.27, z + 0.014)]
        bands.append(W.front_decal(f'{prefix}_BandF_{k}', pts, vest, M['Reflect'], 0.0030, step=0.012))
        bands.append(G.decal(f'{prefix}_BandB_{k}', pts, W.BACK(), [vest], 0.0030, M['Reflect'], step=0.012))
    return vest, [vest] + [_t(o, vsrc) for o in bands]


def work_boots(prefix, M):
    return W.shoes(prefix + '_Boot', M['Boots'], M['Boots_Sole'], high=True) + W.boot_shafts(prefix + '_Boot', M['Boots'], top=0.30)


def _project(bvh, raw, off):
    pts = []
    for p in raw:
        p = Vector(p)
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.3))) >= 0 else -nrm
        pts.append(loc + nrm * off)
    return pts


# ------------------------------------------------------------------ PROM_GUARD
def chest_radio(prefix, M, jacket):
    """Walkie-talkie clipped to the left chest of the uniform, stub antenna up, red light on."""
    import buddy_pool_bad as BD
    bvh = G.bvh_of([jacket])
    loc, nrm, _, _ = bvh.find_nearest(Vector((0.105, -0.25, 1.110)))
    nrm = nrm if nrm.y < 0 else -nrm
    c = loc + nrm * 0.020
    body = BD.rbox(prefix + '_Body', c, (0.026, 0.016, 0.050), M['Radio'], bevel=0.008)
    ant = G.tube(prefix + '_Antenna', [c + Vector((0.012, 0.0, 0.045)), c + Vector((0.012, 0.0, 0.110))], lambda i, n: (0.006, 0.004)[i],
                 M['Radio'], seg=6)
    led = G.ellipsoid(prefix + '_Led', c + Vector((-0.010, -0.016, 0.040)), (0.004, 0.002, 0.004), M['Radio_Light'], seg=8, rings=4)
    return [C.rigid(o, 'Spine2') for o in (body, ant, led)]


def guard(body, face, M, skin):
    pre = 'PROM_GUARD'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Jacket', src)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Collar'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=22, tip=0.030, thick=0.007)
    btns = W.buttons(pre + '_Btn', jacket, M['Buttons'], [(0.0, z) for z in (1.175, 1.075, 0.975, 0.875, 0.775)], r=0.011, offset=0.006)
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in btns]
    out.append(T._trousers(pre, M, 'Trousers', src))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += T._dress_shoes(pre, M)
    out += W.police_cap(pre + '_Cap', M['Cap'], M['CapBand'], M['Visor'], M['Gold'])
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=W.zprofile([(0, 1.680), (90, 1.662), (180, 1.644)])))
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.014, size=1.3)
    out += T._face(skin, lambda head: W.eye_bags(pre + '_EyeBag', M['EyeBags'], head))
    out += chest_radio(pre + '_Radio', M, jacket)
    return out


# ------------------------------------------------------------------ PROM_FOREMAN (migrant foreman)
def tape_measure(prefix, M):
    """Yellow tape measure clipped to the waistband on the right hip."""
    import buddy_pool_bad as BD
    c = Vector((-0.186, -0.060, 0.860))
    rot = Matrix.Rotation(math.radians(-20), 3, 'Z')
    body = BD.rbox(prefix + '_Body', c, (0.012, 0.034, 0.034), M['Tape'], bevel=0.010, rot=rot)
    clip = BD.rbox(prefix + '_Clip', c + rot @ Vector((0.012, 0.0, 0.010)), (0.003, 0.012, 0.026), M['Tape_Belt'], bevel=0.002, rot=rot)
    return [C.rigid(o, 'Hips') for o in (body, clip)]


def foreman(body, face, M, skin):
    import buddy_pool_bad as BD
    import buddy_pool_transit as TR
    pre = 'PROM_FOREMAN'
    src = C.weight_source([body])
    # zipped track jacket with two sleeve stripes under the hi-vis vest
    jacket = W.top(pre + '_Track', W.HOODIE, 7, W.HOODIE_SLEEVE, (.750, .174, .118, -.010), [M['Track'], M['Track_Rib']],
                   row_mat=[1] + [0] * 13, sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(jacket, src, C.no_head)
    out = [jacket, _t(BD._stand_collar(pre + '_Collar', M['Track']), src, C.no_head)]
    out += T._decal_t(BD._sleeve_stripes(pre + '_SleeveStripe', jacket, M['Stripes']), jacket)
    vest, parts = safety_vest(pre, M, src)
    out += parts
    pants = T._trousers(pre, M, 'Trousers', src, legs=W.LEGS_ANKLE, cuff=W.ANKLE_CUFF, cuff_slot='Trousers')
    dust = [W.front_decal(f'{pre}_Dust_{k}', W.blob(x, z, r, seed=70 + k, rough=0.5, sx=1.2), pants, M['Dust'], 0.003)
            for k, (x, z, r) in enumerate(((0.100, 0.520, 0.034), (-0.090, 0.470, 0.030), (0.080, 0.300, 0.024)))]
    out += [pants] + T._decal_t(dust, pants)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.shoes(pre, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    hat, base = hard_hat(pre + '_Hat', M['Hat'])
    out += hat
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=lambda phi: base(phi) + 0.010))
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.004, size=1.25)
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head))
    out += TR.pencil_behind_ear(pre + '_Pencil', M['Pencil'], M['Pencil_Tip'])
    out += tape_measure(pre + '_Tape', M)
    return out


# ------------------------------------------------------------------ PROM_DOCKER (dock worker on the quay)
def rope_coil(prefix, material, target, loops=3):
    """Mooring rope coiled and slung across the body from the left shoulder to the right hip, over the life vest."""
    bvh = G.bvh_of([target])
    out = []
    for k in range(loops):
        d = 0.010 * k
        front = [(0.140 + d, 0.020, 1.278), (0.120 + d, -0.120, 1.215), (0.050 + d, -0.180, 1.120), (-0.040 + d, -0.200, 1.030),
                 (-0.130 + d, -0.190, 0.950), (-0.205, -0.110, 0.905 + d)]
        back = [(-0.215, 0.010, 0.900 + d), (-0.180, 0.140, 0.925 + d), (-0.080 + d, 0.190, 1.010), (0.040 + d, 0.190, 1.110),
                (0.120 + d, 0.140, 1.210), (0.150 + d, 0.060, 1.272)]
        pts = _project(bvh, front + back, 0.016 + 0.004 * k)
        pts.append(pts[0])
        out.append(G.tube(f'{prefix}_{k}', pts, 0.0105, material, seg=8, caps=False))
    return out


def docker(body, face, M, skin):
    pre = 'PROM_DOCKER'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Jacket', src)
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Collar'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=26, tip=0.030, thick=0.007)
    out = [jacket, _t(collar, jsrc, C.no_head)]
    # puffy life vest: thick panels, a collar roll round the neck, a buckle strap across the belly
    vest, parts = safety_vest(pre, M, src, thick=0.020)
    out += parts
    vsrc = C.weight_source([vest])
    roll = [W.head_at(2 * math.pi * k / 24, 1.268, 0.040)[0] for k in range(25)]
    out.append(C.rigid(G.tube(pre + '_VestRoll', roll, 0.030, M['Vest'], seg=10, caps=False), 'Spine2'))
    strap = W.front_decal(pre + '_VestStrap', [(-0.24, 0.835), (0.24, 0.835), (0.24, 0.857), (-0.24, 0.857)], vest, M['Buckle'], 0.0030,
                          step=0.012)
    buckle = W.box(pre + '_VestBuckle', Vector((0.0, -0.200, 0.846)), (0.026, 0.008, 0.018), M['Buckle'])
    out += [_t(strap, vsrc), _t(buckle, vsrc)]
    out += [_t(o, vsrc, C.no_head) for o in rope_coil(pre + '_Rope', M['Rope'], vest)]
    out.append(T._trousers(pre, M, 'Trousers', src, legs=W.LEGS_TUCKED))
    out += work_boots(pre, M)
    out += W.beanie(pre + '_Cap', M['Cap'])
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.012, size=1.4)
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head))
    return out



# ------------------------------------------------------------------ PROM_SAILOR (old sea dog on the quay, TASK-000279)
def telnyashka(prefix, M, src, step=0.030):
    """Striped sailor's vest (only its front shows in the open pea coat): thin horizontal stripes as row materials."""
    lo = [r for r in W.TEE if r[0] < 1.235]
    hi = [r for r in W.TEE if r[0] >= 1.235]
    rows, z = [], lo[0][0]
    while z < 1.235 - step * 0.5:
        rows.append(W.lerp_row(lo + [hi[0]], z))
        z += step
    rows += hi
    ob = W.top(prefix + '_Tel', rows, 0, None, (.806, .184, .124, -.004), [M['Tel'], M['Tel_Stripe']],
               row_mat=[k % 2 for k in range(len(rows) - 1)], armhole=False)
    return _t(ob, src, C.no_head)


def pea_coat(prefix, M, src):
    """Double-breasted pea coat worn open: wide lapels, two rows of brass buttons on the front panels."""
    gap = lambda z: 0.055 + 0.050 * W.smoothstep(1.00, 1.25, z)
    coat = W.top(prefix + '_Coat', W.JACKET, 7, W.JACKET_SLEEVE, (.716, .200, .135, -.012), [M['Coat']],
                 cut=lambda c: c.y < 0 and abs(c.x) < gap(c.z))
    _t(coat, src, C.no_head)
    csrc = C.weight_source([coat])
    collar = W.collar(prefix + '_Collar', M['Coat'], z0=1.256, r0=(0.157, 0.153), z1=1.292, r1=(0.168, 0.163), z2=1.236,
                      r2=(0.212, 0.202), open_deg=42, tip=0.052, thick=0.008)
    btns = W.buttons(prefix + '_Btn', coat, M['Brass'], [(s * 0.112, z) for s in (1, -1) for z in (1.080, 0.985, 0.890)],
                     r=0.012, offset=0.006)
    return coat, [coat, _t(collar, csrc, C.no_head)] + [_t(o, csrc) for o in btns]


def pipe(prefix, M):
    """Tobacco pipe in the left mouth corner, bowl up (a head prop like the shepherd's straw, not a hand prop)."""
    import buddy_pool_bad as BD
    a = Vector((0.046, -0.150, 1.390))
    end = a + Vector((0.034, -0.062, -0.012))
    stem = G.tube(prefix + '_Stem', [a, a.lerp(end, 0.5) + Vector((0, 0, -0.004)), end], 0.0045, M['Pipe'], seg=8)
    bowl = BD.axis_loft(prefix + '_Bowl', end + Vector((0.0, 0.0, -0.014)), end + Vector((0.0, 0.0, 0.040)),
                        [(0.0, 0.013), (0.25, 0.019), (1.0, 0.017)], M['Pipe'], seg=12, cap_start=True, cap_end=False)
    return [W.prop(o, 'Head') for o in (stem, bowl)]


def sailor(body, face, M, skin):
    import buddy_pool_transit as TR
    pre = 'PROM_SAILOR'
    src = C.weight_source([body])
    out = [telnyashka(pre, M, src)]
    coat, parts = pea_coat(pre, M, src)
    out += parts
    out.append(T._trousers(pre, M, 'Trousers', src))
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole'], high=True)
    out += W.police_cap(pre + '_Cap', M['Cap'], M['CapBand'], M['Visor'], M['Gold'])
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=W.zprofile([(0, 1.680), (90, 1.662), (180, 1.644)])))
    out.append(TR.beard(pre + '_Beard', M['Beard']))
    out += pipe(pre + '_Pipe', M)
    return out

BUILDERS = {'PROM_GUARD': guard, 'PROM_FOREMAN': foreman, 'PROM_DOCKER': docker, 'PROM_SAILOR': sailor}
