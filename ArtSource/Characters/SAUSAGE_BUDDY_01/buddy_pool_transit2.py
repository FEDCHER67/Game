"""District pool 'Переход' (part 2, TASK-000270): the cheerful dancer guy and the vaper, dressed on the BASE Sausage
Buddy. Same format as buddy_types.TYPES / BUILDERS; every garment has its own material slot <TYPE>_<Slot>.
Carried props (phone, vape) are rigid on the right hand and exported as the separate 'Props' mesh."""
import math
import bmesh
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GOLD = ((222, 178, 72), 0.26, 'metal')

TYPES = {
    'TRANSIT_INDIAN': dict(
        label='Угарный индус', group='Переход', face=dict(Happy=0.6),
        look=dict(skin=(164, 104, 68), nose=(148, 88, 56), brow=(26, 22, 20), rim=(112, 66, 44), mouth=(70, 30, 26)),
        slots={'Shirt': ((214, 38, 128), 0.75), 'Pattern': ((252, 146, 30), 0.7), 'Dots': ((255, 222, 70), 0.7),
               'Trim': ((252, 146, 30), 0.7), 'Buttons': ((255, 236, 180), 0.4), 'Trousers': ((240, 234, 218), 0.8),
               'Belt': ((96, 52, 30), 0.4), 'Buckle': GOLD, 'Socks': ((240, 234, 218), 0.9),
               'Shoes': ((150, 74, 34), 0.12), 'Shoe_Sole': ((60, 34, 22), 0.5), 'Gold': GOLD,
               'WatchFace': ((246, 244, 236), 0.2), 'Hair': ((22, 20, 22), 0.45), 'HairPart': ((60, 56, 58), 0.6),
               'Mustache': ((22, 20, 22), 0.7), 'Phone': ((222, 182, 86), 0.3, 'metal'), 'Screen': ((96, 186, 250), 0.15)},
        colourways=[{'Shirt': (30, 156, 160), 'Pattern': (255, 222, 70), 'Dots': (246, 246, 240), 'Trim': (255, 222, 70),
                     'Trousers': (226, 206, 160), 'Shoes': (240, 240, 236), 'Shoe_Sole': (200, 196, 190), 'Phone': (40, 40, 46)},
                    {'Shirt': (252, 182, 30), 'Pattern': (150, 40, 150), 'Dots': (220, 40, 60), 'Trim': (150, 40, 150),
                     'Trousers': (246, 244, 238), 'Belt': (30, 28, 28), 'Shoes': (30, 28, 28), 'Phone': (200, 60, 120)}]),
    'TRANSIT_VAPER': dict(
        label='Вейпер', group='Переход', body=dict(thin=1.0), face=dict(Happy=0.2, Blink=0.3),
        look=dict(brow=(70, 52, 40)),
        slots={'Hoodie': ((122, 82, 186), 0.9), 'Hoodie_Rib': ((104, 68, 162), 0.9), 'Cords': ((246, 244, 238), 0.7),
               'Print': ((150, 240, 220), 0.8), 'Jeans': ((92, 128, 182), 0.9), 'Jeans_Cuff': ((140, 172, 214), 0.9),
               'Rip': ((240, 240, 236), 0.9), 'Shoe_Upper': ((246, 246, 242), 0.7), 'Shoe_Sole': ((236, 234, 228), 0.6),
               'Shoe_Lace': ((240, 64, 120), 0.7), 'Shoe_Accent': ((240, 64, 120), 0.6), 'Cap': ((30, 30, 34), 0.8),
               'Cap_Peak': ((240, 64, 120), 0.6), 'Snap': ((16, 16, 18), 0.5), 'Hair': ((92, 66, 46), 0.8),
               'Goatee': ((92, 66, 46), 0.9), 'Vape': ((60, 210, 200), 0.25, 'metal'), 'Vape_Tip': ((24, 24, 28), 0.3),
               'Vape_Light': ((255, 90, 170), 0.2)},
        colourways=[{'Hoodie': (36, 36, 40), 'Hoodie_Rib': (28, 28, 32), 'Print': (246, 120, 60), 'Jeans': (56, 60, 72),
                     'Jeans_Cuff': (84, 88, 100), 'Cap': (240, 64, 120), 'Cap_Peak': (30, 30, 34), 'Vape': (246, 120, 60)},
                    {'Hoodie': (150, 222, 196), 'Hoodie_Rib': (126, 200, 174), 'Print': (122, 82, 186), 'Jeans': (40, 44, 52),
                     'Jeans_Cuff': (64, 68, 78), 'Cap': (246, 246, 242), 'Cap_Peak': (60, 210, 200), 'Shoe_Accent': (60, 140, 230),
                     'Vape': (240, 64, 120)}]),
}

_t, _decal_t, _face = T._t, T._decal_t, T._face


# ------------------------------------------------------------------ local primitives
def _rbox(name, center, half, axes, material, bevel=0.004, segs=2):
    """Rounded box: half extents along the three unit axes (columns), centred at `center` (armature space)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.scale(bm, vec=half, verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, affect='EDGES', profile=0.5)
    R = Matrix((axes[0], axes[1], axes[2])).transposed().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ R, verts=bm.verts)
    return G.from_bm(name, bm, material, smooth=False)


def _hand_frame(bone='RightHand'):
    """T-pose hand frame in armature space: (wrist point, fingers direction, palm normal, thumb side)."""
    M = W.bone_rest(bone)
    hd = M.to_3x3().col[1].normalized()
    palm = Vector((0, 0, -1))
    palm = (palm - hd * palm.dot(hd)).normalized()
    side = hd.cross(palm).normalized()
    return M.translation.copy(), hd, palm, side


def _shoe_pair(prefix, upper_m, sole_m, lace_m=None, point=0.0, chunky=0.0):
    """Sneaker-based shoes: point > 0 narrows and lengthens the toe (pointed dress shoe), chunky > 0 makes the
    sole taller / wider (dad sneaker; the bottom stays on the floor)."""
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Shoe_{s}', s, upper_m, sole_m)
        cx = s * B.LEG_X
        piv = Vector((cx, 0, 0))
        inv = yaw.inverted()
        for o, is_sole in ((up, False), (so, True)):
            for v in o.data.vertices:
                q = inv @ (v.co - piv) + piv
                if point:
                    t = G.smoothstep(-0.120, -0.236, q.y)
                    q.x = cx + (q.x - cx) * (1 - 0.55 * point * t)
                    q.y -= 0.034 * point * t * t
                    if not is_sole:
                        q.z = 0.036 + (q.z - 0.036) * (1 - 0.30 * point * t)
                if chunky and is_sole:
                    q.x = cx + (q.x - cx) * (1 + 0.10 * chunky)
                    q.y = -0.067 + (q.y + 0.067) * (1 + 0.035 * chunky)
                    q.z = q.z * (1 + 0.55 * chunky)
                v.co = yaw @ (q - piv) + piv
            o.data.update()
        parts = [up, so]
        if lace_m is not None:
            parts += C.laces(f'{prefix}_Lace_{s}', s, top_h, yaw, lace_m)
        wf = C.shoe_weights(s)
        for o in parts:
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += parts
    return out


def _big_watch(prefix, band_m, face_m, x=0.600, side=1):
    s = side
    r = 0.041
    z = B.arm_z(x)
    band = G.loft(prefix + '_Band', [((s * (x - 0.012), 0, z), (0, 1, 0), (0, 0, 1), r, r),
                                     ((s * (x + 0.012), 0, z), (0, 1, 0), (0, 0, 1), r, r)], band_m, seg=16)
    case = G.ellipsoid(prefix + '_Case', (s * x, 0, z + r + 0.003), (0.025, 0.025, 0.009), band_m, seg=16, rings=6)
    dial = G.ellipsoid(prefix + '_Dial', (s * x, 0, z + r + 0.008), (0.019, 0.019, 0.004), face_m, seg=16, rings=6)
    return [C.rigid(o, ('Left' if s > 0 else 'Right') + 'ForeArm') for o in (band, case, dial)]


def _diamond(cx, cz, r, k=1.0):
    return [(cx, cz - r), (cx + r * k, cz), (cx, cz + r), (cx - r * k, cz)]


# ------------------------------------------------------------------ TRANSIT_INDIAN
def transit_indian(body, face, M, skin):
    ID = 'TRANSIT_INDIAN'
    src = C.weight_source([body])
    shirt = W.top(ID + '_Shirt', W.TUCKED, 6, W.SLEEVE_SHORT, (.844, .166, .110, -.006), [M['Shirt'], M['Trim']],
                  sleeve_mat=[0, 0, 0, 1, 1, 1])
    _t(shirt, src, C.no_head)
    ssrc = C.weight_source([shirt])
    collar = W.collar(ID + '_Collar', M['Trim'], open_deg=34, tip=0.050, r2=(0.184, 0.176), thick=0.005)
    out = [shirt, _t(collar, ssrc, C.no_head)]
    deco = [W.front_decal(ID + '_OpenNeck', [(-0.048, 1.262), (0.048, 1.262), (0.0, 1.180)], shirt, skin, 0.0025, step=0.008),
            W.front_decal(ID + '_Placket', [(-0.006, 0.850), (0.006, 0.850), (0.006, 1.182), (-0.006, 1.182)], shirt, M['Trim'], 0.003)]
    deco += W.buttons(ID + '_Btn', shirt, M['Buttons'], [(0.0, z) for z in (1.140, 1.060, 0.980, 0.900)], r=0.0085, offset=0.005)
    # bold geometric print: orange diamonds with yellow dots between them, front and back
    k = 0
    for row, z in enumerate((0.930, 1.010, 1.090, 1.170)):
        xs = (-0.130, -0.065, 0.065, 0.130) if row % 2 == 0 else (-0.160, -0.098, 0.098, 0.160)
        for x in xs:
            if z > 1.13 and abs(x) < 0.08:
                continue
            deco.append(W.front_decal(f'{ID}_Dia_{k}', _diamond(x, z, 0.026, 0.8), shirt, M['Pattern'], 0.0028, step=0.012)); k += 1
            deco.append(G.decal(f'{ID}_DiaB_{k}', _diamond(x, z, 0.026, 0.8), W.BACK(), [shirt], 0.0028, M['Pattern'], step=0.012)); k += 1
        for x in ((-0.098, -0.032, 0.032, 0.098) if row % 2 == 0 else (-0.130, -0.065, 0.065, 0.130)):
            if abs(x) < 0.04:
                continue
            deco.append(W.front_decal(f'{ID}_Dot_{k}', C.ellipse(x, z + 0.040, 0.010, 0.010, 8), shirt, M['Dots'], 0.0028)); k += 1
            deco.append(G.decal(f'{ID}_DotB_{k}', C.ellipse(x, z + 0.040, 0.010, 0.010, 8), W.BACK(), [shirt], 0.0028, M['Dots'])); k += 1
    for x in (-0.032, 0.032):
        deco.append(G.decal(f'{ID}_DotB_{k}', C.ellipse(x, 1.050, 0.010, 0.010, 8), W.BACK(), [shirt], 0.0028, M['Dots'])); k += 1
    out += [_t(o, ssrc) for o in deco]
    out.append(T._trousers(ID, M, 'Trousers', src))
    out += [_t(o, src) for o in W.belt(ID, M['Belt'], M['Buckle'])]
    out.append(_t(W.plain_socks(ID + '_Socks', M['Socks']), src))
    out += _shoe_pair(ID, M['Shoes'], M['Shoe_Sole'], point=1.0)
    out += _big_watch(ID + '_Watch', M['Gold'], M['WatchFace'], x=0.598, side=1)
    # neat black hair with a side part and a little volume over the forehead
    hair = W.hair(ID + '_Hair', M['Hair'], 'slick')
    out += [hair, W.hair_part(ID + '_HairPart', M['HairPart'], hair, x=0.058)]
    quiff = G.ellipsoid(ID + '_Quiff', (-0.016, -0.036, 1.736), (0.124, 0.090, 0.036), M['Hair'],
                        rot=Matrix.Rotation(math.radians(-18), 3, 'X') @ Matrix.Rotation(math.radians(-5), 3, 'Y'), seg=20, rings=10)
    out.append(C.rigid(quiff, 'Head'))
    out += _mustache(ID + '_Mustache', M['Mustache'], size=1.45)
    out += _phone(ID + '_Phone', M['Phone'], M['Screen'])
    return out


def _mustache(prefix, material, size=1.0):
    """Thick black mustache under the nose, ends turned slightly up (a happy one)."""
    out = []
    for s in (1, -1):
        base = [(0.004, 1.440), (0.024, 1.438), (0.046, 1.432), (0.064, 1.428), (0.078, 1.432), (0.086, 1.442)]
        n = len(base)
        rad = [(0.0125, 0.0135, 0.0125, 0.010, 0.0075, 0.0045)[i] * size for i in range(n)]
        pts = [Vector((s * x, B.head_surface_y(s * x, z, 0.003 + rad[i]), z)) for i, (x, z) in enumerate(base)]
        out.append(C.rigid(G.tube(f'{prefix}_{s}', pts, lambda i, k: rad[i], material, seg=10), 'Head'))
    return out


def _phone(prefix, case_m, screen_m):
    """Big cartoon smartphone pinched in the right hand: it stands in front of the fingers with the screen facing
    forward (the thumb crosses it), so it reads from the front and the 3/4 view in idle."""
    wrist, hd, palm, side = _hand_frame('RightHand')
    fwd = -side if side.y > 0 else side                      # rest -Y (forward in idle)
    L, Wd, Th = 0.170, 0.084, 0.013
    c = wrist + hd * 0.110 + fwd * 0.067
    ob = _rbox(prefix, c, (Wd / 2, L / 2, Th / 2), (-palm, hd, fwd), case_m, bevel=0.007)
    scr = _rbox(prefix + '_Screen', c + fwd * (Th / 2 + 0.0004), (Wd / 2 - 0.007, L / 2 - 0.010, 0.0012), (-palm, hd, fwd), screen_m,
                bevel=0.0)
    G.join(ob, [scr])
    return [W.prop(ob, 'RightHand')]


# ------------------------------------------------------------------ TRANSIT_VAPER
HOODIE_BIG = [(z, rx + 0.024 * G.smoothstep(1.24, 1.10, z), ry + 0.020 * G.smoothstep(1.24, 1.10, z), dy)
              for z, rx, ry, dy in W.HOODIE]
HOODIE_BIG[0] = (.700, .196, .136, -.012)
HOODIE_BIG[1] = (.716, .206, .144, -.012)
HOODIE_BIG_SLEEVE = [(x, r + 0.014 * G.smoothstep(0.62, 0.50, x)) for x, r in W.HOODIE_SLEEVE]
LEGS_SKINNY = [(.70, .074), (.60, .066), (.50, .060), (.43, .056), (.34, .053), (.26, .051), (.228, .051)]
SKINNY_CUFF = [(.214, .061), (.252, .061), (.256, .055)]


def transit_vaper(body, face, M, skin):
    ID = 'TRANSIT_VAPER'
    src = C.weight_source([body])
    hoodie = W.top(ID + '_Hoodie', HOODIE_BIG, 7, HOODIE_BIG_SLEEVE, (.716, .186, .128, -.010), [M['Hoodie'], M['Hoodie_Rib']],
                   row_mat=[1] + [0] * (len(HOODIE_BIG) - 2), sleeve_mat=[0] * 9 + [1] * 5, hem_mat=1)
    _t(hoodie, src, C.no_head)
    hsrc = C.weight_source([hoodie])
    out = [hoodie, T._hood_down(ID, M['Hoodie'])]
    pocket = G.decal(ID + '_Pocket', [(-0.150, 0.765), (0.150, 0.765), (0.120, 0.950), (-0.120, 0.950)], W.FRONT(), [hoodie], 0.004,
                     M['Hoodie'], thickness=0.010, **G.res('big_decal', step=0.010))
    deco = [pocket]
    for s in (1, -1):
        deco.append(G.decal(f'{ID}_PocketSlot_{s}', [(s * 0.140, 0.792), (s * 0.150, 0.792), (s * 0.124, 0.944), (s * 0.114, 0.944)],
                            W.FRONT(), [pocket, hoodie], 0.0025, M['Hoodie_Rib']))
    # chest print: a puffy cloud (overlapping round blobs, same colour)
    for k, (x, z, r) in enumerate(((-0.040, 1.060, 0.030), (0.0, 1.075, 0.036), (0.042, 1.062, 0.029), (-0.068, 1.044, 0.020),
                                   (0.070, 1.046, 0.020), (0.0, 1.044, 0.030))):
        deco.append(W.front_decal(f'{ID}_Cloud_{k}', C.ellipse(x, z, r * 1.15, r, 14), hoodie, M['Print'], 0.0028 + 0.0002 * k, step=0.012))
    out += [_t(o, hsrc) for o in deco]
    for s in (1, -1):
        path = [(s * 0.040, -0.168, 1.236), (s * 0.046, -0.200, 1.17), (s * 0.048, -0.214, 1.10), (s * 0.047, -0.216, 1.030)]
        out.append(_t(G.tube(f'{ID}_Cord_{s}', path, 0.0062, M['Cords'], **G.res('cord', seg=8)), src,
                      lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else w))
    # skinny ripped jeans rolled up at the ankle, bare ankles
    jeans = T._trousers(ID, M, 'Jeans', src, legs=LEGS_SKINNY, cuff=SKINNY_CUFF, cuff_slot='Jeans_Cuff')
    out.append(jeans)
    rips = []
    for k, (x, z, r) in enumerate(((0.100, 0.450, 0.026), (-0.100, 0.468, 0.030), (0.112, 0.640, 0.018))):
        rips.append(W.front_decal(f'{ID}_RipRim_{k}', W.blob(x, z, r + 0.006, seed=11 + k, rough=0.45, sx=1.3), jeans, M['Rip'], 0.0025))
        rips.append(W.front_decal(f'{ID}_Rip_{k}', W.blob(x, z, r, seed=21 + k, rough=0.5, sx=1.3), jeans, skin, 0.0038))
        for j, dz in enumerate((-0.45, 0.0, 0.45)):
            zz = z + dz * r
            rips.append(W.front_decal(f'{ID}_Thread_{k}_{j}', [(x - r * 1.2, zz - 0.0022), (x + r * 1.2, zz - 0.0022), (x + r * 1.2, zz + 0.0022),
                                                               (x - r * 1.2, zz + 0.0022)], jeans, M['Rip'], 0.0050, step=0.008))
    out += _decal_t(rips, jeans)
    out += _shoe_pair(ID, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'], chunky=1.0)
    for s in (1, -1):
        cx = s * B.LEG_X
        tab = G.ellipsoid(f'{ID}_HeelTab_{s}', (cx + s * 0.004, 0.104, 0.092), (0.032, 0.012, 0.034), M['Shoe_Accent'], seg=12, rings=8)
        C.set_weights(tab, [C.shoe_weights(s)(tab.matrix_world @ v.co) for v in tab.data.vertices])
        out.append(tab)
    out += _snapback(ID, M)
    out += _goatee(ID + '_Goatee', M['Goatee'])
    out += _vape(ID + '_Vape', M['Vape'], M['Vape_Tip'], M['Vape_Light'])
    return out


def _snapback(ID, M):
    """Snapback cap worn backwards: tall crown, flat peak over the back of the neck, the snap strap opening over the
    forehead; a short hair band shows under it at the sides and the back."""
    base = W.zprofile([(0, 1.664), (90, 1.648), (180, 1.640)])
    up = lambda dz: (lambda phi: base(phi) + dz)
    rows = [('fit', base, 0.006), ('fit', up(0.030), 0.010), (1.722, 0.150, 0.150, -0.004, 0.0), (1.756, 0.138, 0.140, -0.006, 0.0),
            (1.784, 0.108, 0.112, -0.008, 0.0), (1.802, 0.060, 0.064, -0.008, 0.0), (1.808, 0.016, 0.018, -0.008, 0.0)]
    crown = W.ring_loft(ID + '_Crown', rows, [M['Cap']], seg=32)
    # flat peak growing backwards from the cap base
    vs, fs = [], []
    u, v, span = 12, 4, math.radians(60)
    for i in range(u + 1):
        t = i / u * 2 - 1
        phi = math.pi + span * t
        rim, _ = W.head_at(phi, base(phi), 0.008)
        outv = Vector((math.sin(phi), -math.cos(phi), 0))
        Lp = 0.088 * math.sqrt(max(0.0, 1 - t * t)) + 0.014
        for j in range(v + 1):
            w = j / v
            vs.append(rim + outv * (Lp * w) + Vector((0, 0, -0.026 * w * w - 0.010 * t * t * w)))
    for i in range(u):
        for j in range(v):
            a = i * (v + 1) + j
            fs.append((a, a + v + 1, a + v + 2, a + 1))
    peak = G.from_data(ID + '_CapPeak', vs, fs, M['Cap_Peak'], True)
    G.solidify(peak, 0.008, offset=0.0)
    btn = G.ellipsoid(ID + '_CapButton', (0, -0.008, 1.810), (0.014, 0.014, 0.006), M['Cap'], seg=10, rings=6)
    parts = [crown, peak, btn]
    # snap opening over the forehead (hair shows through) and the strap across it
    arch = [(0.040 * math.cos(math.radians(a)), 1.668 + 0.034 * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    parts.append(G.decal(ID + '_SnapHole', arch, W.FRONT(), [crown], 0.0018, M['Hair'], step=0.008))
    parts.append(G.decal(ID + '_SnapStrap', [(-0.048, 1.670), (0.048, 1.670), (0.048, 1.684), (-0.048, 1.684)], W.FRONT(), [crown], 0.0032,
                         M['Snap'], step=0.008, thickness=0.003))
    for x in (-0.020, 0.0, 0.020):
        parts.append(G.decal(f'{ID}_SnapDot_{x:+.2f}', C.ellipse(x, 1.677, 0.0045, 0.0045, 8), W.FRONT(), [crown], 0.0068, M['Cap_Peak']))
    # short hair under the cap at the sides and the back
    hair, _ = W.shell(ID + '_Hair', M['Hair'], W.HAIRLINE, lambda phi: base(phi) + 0.012, off=0.0015, thick=0.0035, seg=28, rows=4,
                      arc=(math.radians(50), math.radians(310)))
    parts.append(hair)
    return [C.rigid(o, 'Head') for o in parts]


def _goatee(prefix, material):
    pts = [Vector((0, B.head_surface_y(0, z, 0.0), z)) for z in (1.388, 1.372, 1.352, 1.330)]
    pts = [p + Vector((0, -d, 0)) for p, d in zip(pts, (0.004, 0.010, 0.012, 0.010))]
    tube = G.tube(prefix, pts, lambda i, n: (0.010, 0.017, 0.015, 0.006)[i], material, seg=10)
    return [C.rigid(tube, 'Head')]


def _vape(prefix, body_m, tip_m, light_m):
    """Pocket vape: a chunky rounded box pinched in front of the right fingers, broad face forward, the dark
    mouthpiece sticking out past the fingertips."""
    wrist, hd, palm, side = _hand_frame('RightHand')
    fwd = -side if side.y > 0 else side
    c = wrist + hd * 0.118 + fwd * 0.071
    ob = _rbox(prefix, c, (0.019, 0.048, 0.011), (-palm, hd, fwd), body_m, bevel=0.008)
    tip = G.tube(prefix + '_Tip', [c + hd * 0.044, c + hd * 0.074], lambda i, n: (0.0095, 0.0065)[i], tip_m, seg=12)
    led = G.ellipsoid(prefix + '_Led', c + fwd * 0.0105 - hd * 0.026, (0.0065, 0.0065, 0.0022), light_m,
                      rot=Matrix((-palm, hd, fwd)).transposed(), seg=10, rings=6)
    G.join(ob, [tip, led])
    return [W.prop(ob, 'RightHand')]


BUILDERS = {'TRANSIT_INDIAN': transit_indian, 'TRANSIT_VAPER': transit_vaper}
