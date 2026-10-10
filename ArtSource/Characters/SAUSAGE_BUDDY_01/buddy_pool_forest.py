"""District pool 'Лесная полоса' (forest strip, TASK-000270): the overdosed junkie and the stash courier ("закладчик",
TASK-000271, replaces the mushroom picker in the pool; FOREST_MUSHROOMER stays buildable for its v01 files).
Same format as buddy_types.TYPES / BUILDERS; every garment and prop has its own material slot <TYPE>_<Slot>."""
import math, random
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Лесная полоса'
OD = 'FOREST_OD_JUNKIE'
MUSH = 'FOREST_MUSHROOMER'
STASH = 'FOREST_STASHER'

TYPES = {
    OD: dict(
        label='Передознутый торчок', group=GROUP, body=dict(thin=1.0), no_ears=True,
        face=dict(Blink=0.65, Worried=0.3),
        look=dict(skin=(198, 206, 172), nose=(184, 192, 158), brow=(78, 72, 62), rim=(196, 92, 96)),
        slots={'Hoodie': ((104, 112, 92), 0.95), 'Hoodie_Rib': ((88, 95, 78), 0.95), 'Cords': ((214, 210, 196), 0.85),
               'Pants': ((128, 128, 134), 0.95), 'Pants_Rib': ((108, 108, 114), 0.95), 'Socks': ((198, 192, 176), 0.9),
               'Slides': ((40, 42, 46), 0.55), 'Dirt': ((96, 86, 70), 1.0),
               'Hair': ((62, 54, 46), 0.8), 'EyeBags': ((138, 112, 146), 0.8), 'Stubble': ((90, 80, 72), 0.95),
               'Drool': ((196, 226, 240), 0.05)},
        colourways=[{'Hoodie': (70, 72, 80), 'Hoodie_Rib': (58, 60, 68), 'Cords': (182, 182, 176), 'Pants': (52, 56, 72),
                     'Pants_Rib': (44, 48, 62), 'Slides': (152, 44, 42)},
                    {'Hoodie': (134, 100, 76), 'Hoodie_Rib': (114, 84, 64), 'Cords': (232, 222, 196), 'Pants': (90, 96, 80),
                     'Pants_Rib': (78, 84, 70), 'Socks': (224, 220, 208), 'Slides': (42, 62, 122)}]),
    MUSH: dict(
        label='Грибник', group=GROUP, body=dict(belly=0.4), face=dict(Happy=0.35),
        look=dict(brow=(206, 204, 198)),
        slots={'Anorak': ((126, 122, 78), 0.95), 'Anorak_Dark': ((100, 96, 60), 0.95), 'Zip': ((52, 50, 40), 0.6),
               'Trousers': ((92, 94, 74), 0.9), 'Boots': ((36, 38, 40), 0.4), 'Boots_Sole': ((24, 24, 26), 0.6),
               'Beanie': ((60, 92, 156), 0.95), 'Pompom': ((238, 236, 228), 1.0), 'Hair': ((206, 204, 198), 1.0),
               'Basket': ((196, 150, 86), 0.85), 'Basket_Dark': ((150, 106, 56), 0.85), 'Moss': ((92, 120, 60), 1.0),
               'Cap_Red': ((214, 40, 34), 0.45), 'Cap_Dots': ((250, 248, 240), 0.6), 'Stem': ((244, 236, 214), 0.8),
               'Gills': ((236, 222, 190), 0.9), 'Cap_Brown': ((128, 76, 40), 0.55)},
        colourways=[{'Anorak': (70, 84, 62), 'Anorak_Dark': (54, 66, 48), 'Trousers': (60, 66, 54), 'Boots': (54, 84, 54),
                     'Beanie': (176, 52, 48), 'Pompom': (236, 214, 92)},
                    {'Anorak': (156, 142, 110), 'Anorak_Dark': (128, 114, 86), 'Trousers': (64, 66, 74),
                     'Boots': (42, 52, 82), 'Beanie': (232, 196, 70), 'Pompom': (60, 92, 156), 'Basket': (172, 128, 72)}]),
    STASH: dict(
        label='Закладчик', group=GROUP, hand_props=True, body=dict(thin=0.6), no_ears=True, face=dict(Worried=0.35, Blink=0.15),
        slots={'Hoodie': ((34, 36, 40), 0.9), 'Hoodie_Rib': ((26, 28, 32), 0.9), 'Pants': ((30, 32, 36), 0.9),
               'Pants_Rib': ((24, 26, 30), 0.9), 'Socks': ((230, 230, 226), 0.9), 'Shoe_Upper': ((28, 28, 30), 0.6),
               'Shoe_Sole': ((240, 240, 236), 0.6), 'Shoe_Lace': ((240, 240, 236), 0.7), 'Shades_Frame': ((16, 16, 18), 0.3),
               'Shades_Lens': ((12, 14, 18), 0.06), 'Backpack': ((52, 58, 50), 0.8), 'Backpack_Straps': ((30, 32, 30), 0.8),
               'Phone': ((20, 20, 22), 0.3), 'Screen': ((120, 200, 255), 0.2), 'Tape_Blue': ((40, 90, 200), 0.45),
               'Tape_Red': ((200, 40, 40), 0.45), 'Tape_Yellow': ((240, 200, 40), 0.45)},
        colourways=[{'Hoodie': (52, 62, 46), 'Hoodie_Rib': (42, 50, 38), 'Pants': (44, 46, 40), 'Pants_Rib': (36, 38, 32),
                     'Backpack': (30, 30, 34)},
                    {'Hoodie': (60, 66, 84), 'Hoodie_Rib': (50, 54, 70), 'Pants': (34, 36, 42), 'Shoe_Upper': (240, 240, 236),
                     'Shoe_Sole': (40, 40, 42), 'Backpack': (120, 40, 36)}]),
}


# ------------------------------------------------------------------ shared helpers
def _frame(d):
    """Orthonormal (u, v, d) with d along the given direction."""
    d = Vector(d).normalized()
    u = d.orthogonal().normalized()
    return u, d.cross(u).normalized(), d


def _idle_delta(side='Right'):
    """Armature-space transform taking T-pose points of the <side>Hand bone to the idle pose (idle_joints at t = 0,
    the same chain pose_from_joints composes; Spine rotations are zero at t = 0). build_buddy patches the idle
    arm angle into idle_joints' defaults before dressing, so this follows the type's arm_down."""
    import buddy_anim as A
    J = A.idle_joints()
    Tm = Matrix()
    for b in ('Shoulder', 'Arm', 'ForeArm', 'Hand'):
        name = side + b
        h = Tm @ W.bone_rest(name).translation
        q = J.get(name)
        if q is not None:
            Tm = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ Tm
    return Tm


def _hand_prop(objs, side='Right'):
    """Props modelled where they hang in the idle pose (armature space): bake them back to the hand bone's T-pose
    frame and make them rigid on the hand."""
    Tm = _idle_delta(side)
    local = W.bone_rest(side + 'Hand').inverted() @ Tm.inverted()
    return [W.prop(W.to_bone(o, side + 'Hand', local), side + 'Hand') for o in objs]


def _idle_point(p, side='Right'):
    return _idle_delta(side) @ Vector(p)


def _tris(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


# ------------------------------------------------------------------ overdosed junkie
OD_SLEEVE = [(.22, .080), (.25, .078), (.29, .076), (.34, .074), (.39, .072), (.44, .070), (.49, .068), (.54, .067),
             (.585, .067), (.625, .069), (.660, .069), (.676, .066), (.684, .060), (.678, .054)]


def _od_hoodie(prefix, M, src):
    """Oversized hoodie: the sleeves swallow half of each hand."""
    hoodie = W.top(prefix + '_Hoodie', W.HOODIE, 7, OD_SLEEVE, (.750, .174, .118, -.010), [M['Hoodie'], M['Hoodie_Rib']],
                   row_mat=[1] + [0] * 13, sleeve_mat=[0] * 10 + [1] * 4, hem_mat=1)
    T._t(hoodie, src, C.no_head)
    pocket = G.decal(prefix + '_Pocket', [(-0.135, 0.795), (0.135, 0.795), (0.108, 0.975), (-0.108, 0.975)], W.FRONT(), [hoodie], 0.004,
                     M['Hoodie'], thickness=0.010, **G.res('big_decal', step=0.010))
    out = [hoodie] + T._decal_t([pocket], hoodie)
    for s in (1, -1):
        slot = G.decal(f'{prefix}_PocketSlot_{s}', [(s * 0.126, 0.822), (s * 0.136, 0.822), (s * 0.111, 0.970), (s * 0.101, 0.970)],
                       W.FRONT(), [pocket, hoodie], 0.0025, M['Hoodie_Rib'])
        out += T._decal_t([slot], hoodie)
    return hoodie, pocket, out


def _hood_cords(prefix, M, hoodie, src):
    """Hood drawstrings: the left one hangs to mid-chest, the right one was pulled out to the belly."""
    bvh = G.bvh_of([hoodie])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.2))) >= 0 else -nrm
        return loc + nrm * off
    out = []
    for s, z_end in ((1, 1.150), (-1, 0.930)):
        top = [Vector((s * 0.112, -0.112, 1.300)), Vector((s * 0.088, -0.146, 1.262))]
        n = max(3, int((1.240 - z_end) / 0.035))
        low = [on(Vector((s * (0.074 - 0.006 * k / n), -0.20, 1.240 - (1.240 - z_end) * k / n)), 0.0075) for k in range(n + 1)]
        path = top + low
        cord = G.tube(f'{prefix}_Cord_{s}', path, 0.0055, M['Cords'], **G.res('cord', seg=8))
        tip = path[-1]
        d = (path[-1] - path[-2]).normalized()
        aglet = G.tube(f'{prefix}_Aglet_{s}', [tip - d * 0.004, tip + d * 0.020], 0.0072, M['Hoodie_Rib'], seg=8)
        for o in (cord, aglet):
            out.append(T._t(o, src, lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else C.no_head(p, w)))
    return out


def _bare_sock_foot(prefix, s, sock_m, rim_m, skin):
    """Lost slide: a fat sock foot (shoe-shaped and as thick as the slide sole, so both feet stand on the floor),
    the big toe poking out of a hole at the front."""
    up, so, top_h, yaw = C.sneaker(f'{prefix}_SockFoot_{s}', s, sock_m, sock_m)
    cx = s * B.LEG_X
    for o in (up, so):                      # a little slimmer and flatter than a shoe
        for v in o.data.vertices:
            v.co.x = cx + (v.co.x - cx) * 0.92
            v.co.z *= 0.86
    piv = Vector((cx, 0, 0))
    tx, ty, tz = cx - s * 0.022, -0.232, 0.050
    toe_c = piv + yaw @ (Vector((tx, ty - 0.011, tz + 0.002)) - piv)
    toe = G.ellipsoid(f'{prefix}_Toe_{s}', toe_c, (0.026, 0.025, 0.023), skin, seg=12, rings=8)
    rim_pts = []
    for k in range(13):
        a = 2 * math.pi * k / 12
        rim_pts.append(piv + yaw @ (Vector((tx + 0.028 * math.cos(a), ty + 0.003, tz + 0.002 + 0.025 * math.sin(a))) - piv))
    rim = G.tube(f'{prefix}_ToeHole_{s}', rim_pts, 0.0045, rim_m, seg=6, caps=False)
    wf = C.shoe_weights(s)
    out = [up, so, toe, rim]
    for o in out:
        C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
    return out


def _one_slide(prefix, s, sock_m, slide_m):
    up, so, top_h, yaw = C.sneaker(f'{prefix}_Foot_{s}', s, sock_m, slide_m)
    cx = s * B.LEG_X
    strap = W.wrap_band(f'{prefix}_Strap_{s}', up, cx - s * 0.006, [-0.022, -0.050, -0.078, -0.104], slide_m, zc=0.047)
    wf = C.shoe_weights(s)
    for o in (up, so, strap):
        C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
    return [up, so, strap]


def _drool(prefix, M):
    x0 = -0.033
    pts = []
    for k, (dx, z) in enumerate(((0.000, 1.404), (-0.002, 1.390), (-0.003, 1.372), (-0.002, 1.356), (0.000, 1.346))):
        x = x0 + dx
        pts.append(Vector((x, B.head_surface_y(x, z, 0.0045 + 0.002 * k), z)))
    string = G.tube(prefix + '_Drool', pts, lambda i, n: 0.0050 - 0.0014 * i / (n - 1), M['Drool'], seg=8)
    drop = G.ellipsoid(prefix + '_DroolDrop', pts[-1] + Vector((0, -0.003, -0.008)), (0.0085, 0.0080, 0.0110), M['Drool'], seg=10, rings=6)
    return [C.rigid(string, 'Head'), C.rigid(drop, 'Head')]


def od_junkie(body, face, M, skin):
    ID = OD
    src = C.weight_source([body])
    hoodie, pocket, out = _od_hoodie(ID, M, src)
    out += W.hood_up(ID, M['Hoodie'])
    out += _hood_cords(ID, M, hoodie, src)
    pants = T._trousers(ID, M, 'Pants', src, legs=W.LEGS_SWEAT, cuff=W.SWEAT_CUFF, cuff_slot='Pants_Rib')
    out.append(pants)
    stains = [W.front_decal(ID + '_Dirt_0', W.blob(-0.070, 1.060, 0.030, seed=1), hoodie, M['Dirt'], 0.0025),
              W.front_decal(ID + '_Dirt_1', W.blob(0.112, 1.150, 0.018, seed=2), hoodie, M['Dirt'], 0.0025),
              G.decal(ID + '_Dirt_2', W.blob(0.060, 0.900, 0.022, seed=3), W.FRONT(), [pocket, hoodie], 0.0025, M['Dirt'])]
    out += T._decal_t(stains, hoodie)
    knee = [W.front_decal(ID + '_Dirt_3', W.blob(0.115, 0.610, 0.024, seed=4), pants, M['Dirt'], 0.0025),
            W.front_decal(ID + '_HoleRim', W.blob(-0.100, 0.445, 0.032, seed=5, rough=0.5), pants, M['Dirt'], 0.0025),
            W.front_decal(ID + '_Hole', W.blob(-0.100, 0.447, 0.024, seed=6, rough=0.55), pants, skin, 0.0040)]
    out += T._decal_t(knee, pants)
    out.append(T._t(W.plain_socks(ID + '_Socks', M['Socks'], top=0.24), src))
    out += _one_slide(ID, 1, M['Socks'], M['Slides'])
    out += _bare_sock_foot(ID, -1, M['Socks'], M['Dirt'], skin)
    out += W.fringe(ID + '_Fringe', M['Hair'])
    out += T._face(skin, lambda head: W.eye_bags(ID + '_EyeBag', M['EyeBags'], head)
                   + W.stubble(ID + '_Stubble', M['Stubble'], head))
    out += _drool(ID, M)
    print(f'[BUDDY] {ID} outfit tris (pre-join): {_tris(out)}')
    return out


# ------------------------------------------------------------------ mushroom picker
def _mushroom(name, base, d, stem_len, stem_r, cap_r, cap_h, cap_m, stem_m, gill_m, dot_m=None, dots=(), seg=16, stem_seg=10,
              fat=False):
    """Cartoon mushroom from `base` along d: a stem (fat=True: boletus barrel) and a domed cap with a gill
    underside; dots = [(height fraction 0..1, azimuth deg, radius)] white flakes on the cap."""
    u, v, d = _frame(d)
    base = Vector(base)
    prof = ((0.0, 1.35), (0.45, 1.30), (0.85, 1.0), (1.0, 0.9)) if fat else ((0.0, 1.15), (0.5, 1.0), (1.0, 0.92))
    stem = G.loft(name + '_Stem', [(base + d * (stem_len * t), u, v, stem_r * k, stem_r * k) for t, k in prof], stem_m, seg=stem_seg)
    top = base + d * stem_len
    rows = [(-0.10, stem_r * 1.02), (-0.06, 0.78), (0.0, 1.0), (0.30, 0.95), (0.62, 0.76), (0.86, 0.46), (0.97, 0.16)]
    secs = []
    for i, (h, r) in enumerate(rows):
        rr = r if i == 0 else cap_r * r
        secs.append((top + d * (cap_h * h), u, v, rr, rr))
    cap = G.loft(name + '_Cap', secs, gill_m, seg=seg, mat_rows=[0, 0] + [1] * 4, extra=(cap_m,))
    out = [stem, cap]
    for k, (hf, az, r) in enumerate(dots):
        a = math.radians(az)
        # surface point of the dome at height fraction hf (piecewise from the cap rows above the rim)
        hs = [h for h, _ in rows[2:]]
        rs = [rr for _, rr in rows[2:]]
        hh = hf * hs[-1]
        for (h0, r0), (h1, r1) in zip(zip(hs, rs), zip(hs[1:], rs[1:])):
            if h0 <= hh <= h1:
                rad = r0 + (r1 - r0) * (hh - h0) / (h1 - h0)
                break
        else:
            rad = rs[-1]
        radial = u * math.cos(a) + v * math.sin(a)
        p = top + d * (cap_h * hh) + radial * (cap_r * rad)
        n = (radial * (1.0 - hf) * cap_h / cap_r + d * (0.3 + hf)).normalized()
        nu, nv, nn = _frame(n)
        rot = Matrix((nu, nv, nn)).transposed()
        out.append(G.ellipsoid(f'{name}_Dot_{k}', p + n * (r * 0.05), (r, r * 0.85, r * 0.32), dot_m, rot=rot, seg=7, rings=4))
    return out


def _hood_roll(prefix, material):
    """Anorak hood down: buddy_types._hood_down (soft roll round the back of the neck) at crowd budget."""
    vs, fs, rings, seg = [], [], [], 12
    n = 15
    for k in range(n):
        phi = math.radians(-152 + 304 * k / (n - 1))
        t = math.cos(phi / 2) ** 2
        R = 0.176 + 0.050 * t
        c = Vector((R * math.sin(phi), 0.004 + R * math.cos(phi) * 1.02, 1.268 - 0.068 * t))
        radial = Vector((math.sin(phi), math.cos(phi), 0))
        a, b = 0.026 + 0.046 * t, 0.034 + 0.066 * t
        ring = []
        for j in range(seg):
            ang = 2 * math.pi * j / seg
            ring.append(len(vs)); vs.append(c + radial * (a * math.cos(ang)) + Vector((0, 0, b * math.sin(ang))))
        rings.append(ring)
    for a_, b_ in zip(rings, rings[1:]):
        G.bridge(fs, a_, b_)
    fs.append(tuple(reversed(rings[0]))); fs.append(tuple(rings[-1]))
    hood = G.from_data(prefix + '_Hood', vs, fs, material, True)
    pouch = G.ellipsoid(prefix + '_HoodPouch', (0, 0.170, 1.165), (0.125, 0.032, 0.100), material, seg=12, rings=8)
    G.join(hood, [pouch])
    return C.rigid(hood, 'Spine2')


def _basket(prefix, M, grip, s_out):
    """Wicker basket hanging under the grip point (idle pose, armature space), overflowing with mushrooms and one
    absurd fly agaric. s_out: the side away from the body (-1 for the right hand)."""
    cx, cy = grip.x, grip.y
    rim_z = grip.z - 0.170
    hgt = 0.175
    rx, ry = 0.124, 0.176
    secs, mats = [], []
    n_rows = 7
    for k in range(n_rows + 1):
        t = k / n_rows
        z = rim_z - hgt * (1 - t)
        kk = 0.80 + 0.20 * math.sin(math.pi / 2 * t) ** 0.7
        secs.append(((cx, cy, z), (1, 0, 0), (0, 1, 0), rx * kk, ry * kk))
    body = G.loft(prefix + '_Basket', secs, M['Basket'], seg=16, cap_start=True, cap_end=False,
                  mat_rows=[k % 2 for k in range(n_rows)], extra=(M['Basket_Dark'],))
    rim_pts = [Vector((cx + rx * 1.02 * math.cos(a), cy + ry * 1.02 * math.sin(a), rim_z)) for a in
               [2 * math.pi * k / 16 for k in range(17)]]
    rim = G.tube(prefix + '_BasketRim', rim_pts, 0.012, M['Basket_Dark'], seg=6, caps=False)
    hp = []
    for k in range(11):
        a = math.pi * k / 10
        hp.append(Vector((cx, cy - ry * math.cos(a), rim_z + (grip.z - rim_z) * math.sin(a) ** 0.8)))
    handle = G.tube(prefix + '_BasketHandle', hp, 0.011, M['Basket_Dark'], seg=8)
    moss = G.ellipsoid(prefix + '_Moss', (cx, cy, rim_z - 0.012), (rx * 0.97, ry * 0.97, 0.030), M['Moss'], seg=12, rings=5)
    out = [body, rim, handle, moss]
    red, brown, stem, gill, dot = M['Cap_Red'], M['Cap_Brown'], M['Stem'], M['Gills'], M['Cap_Dots']
    # small ones round the handle
    out += _mushroom(prefix + '_Bolete_0', (cx - s_out * 0.055, cy + 0.090, rim_z - 0.010), (-s_out * 0.30, 0.30, 1.0), 0.068, 0.025,
                     0.062, 0.048, brown, stem, gill, fat=True, seg=12, stem_seg=8)
    out += _mushroom(prefix + '_Bolete_1', (cx + s_out * 0.050, cy - 0.040, rim_z - 0.010), (s_out * 0.40, -0.15, 1.0), 0.062, 0.023,
                     0.056, 0.044, brown, stem, gill, fat=True, seg=12, stem_seg=8)
    out += _mushroom(prefix + '_Bolete_2', (cx - s_out * 0.060, cy - 0.070, rim_z - 0.010), (-s_out * 0.35, -0.25, 1.0), 0.055, 0.020,
                     0.048, 0.038, brown, stem, gill, fat=True, seg=12, stem_seg=8)
    out += _mushroom(prefix + '_Agaric_0', (cx + s_out * 0.040, cy + 0.120, rim_z - 0.010), (s_out * 0.45, 0.35, 1.0), 0.072, 0.014,
                     0.052, 0.036, red, stem, gill, dot, dots=((0.50, 30, 0.010), (0.45, 170, 0.010), (0.80, 280, 0.009)),
                     seg=12, stem_seg=8)
    # the joke: a fly agaric bigger than his head, leaning out of the front of the basket
    out += _mushroom(prefix + '_BigAgaric', (cx + s_out * 0.020, cy - 0.050, rim_z - 0.090), (s_out * 0.55, -0.42, 1.0), 0.40, 0.034,
                     0.165, 0.110, red, stem, gill, dot, seg=20, stem_seg=10,
                     dots=((0.30, 0, 0.020), (0.35, 72, 0.018), (0.32, 144, 0.021), (0.30, 216, 0.018), (0.36, 288, 0.020),
                           (0.64, 60, 0.017), (0.62, 180, 0.016), (0.66, 300, 0.017), (0.95, 0, 0.015)))
    return out


def mushroomer(body, face, M, skin):
    ID = MUSH
    src = C.weight_source([body])
    jacket = T._jacket(ID, M, 'Anorak', src)
    jsrc = C.weight_source([jacket])
    deco = [W.front_decal(ID + '_Pouch', [(-0.135, 0.930), (0.135, 0.930), (0.128, 1.075), (-0.128, 1.075)], jacket, M['Anorak_Dark'],
                          0.004, thickness=0.006, step=0.036),
            W.front_decal(ID + '_PouchFlap', [(-0.140, 1.050), (0.140, 1.050), (0.136, 1.092), (-0.136, 1.092)], jacket, M['Anorak_Dark'],
                          0.0105, thickness=0.004, step=0.036),
            W.front_decal(ID + '_Zip', [(-0.005, 1.095), (0.005, 1.095), (0.005, 1.258), (-0.005, 1.258)], jacket, M['Zip'], 0.004)]
    out = [jacket] + [T._t(o, jsrc) for o in deco]
    out.append(_hood_roll(ID, M['Anorak']))
    out.append(T._trousers(ID, M, 'Trousers', src, legs=W.LEGS_TUCKED))
    out += W.shoes(ID + '_Boot', M['Boots'], M['Boots_Sole']) + W.boot_shafts(ID + '_Boot', M['Boots'])
    out += W.beanie(ID + '_Beanie', M['Beanie'])
    out.append(C.rigid(G.ellipsoid(ID + '_Pompom', (0, 0.012, 1.792), (0.040, 0.040, 0.034), M['Pompom'], seg=12, rings=8), 'Head'))
    out += [W.hair_ring(ID + '_Hair', M['Hair'])] + W.mustache(ID + '_Mustache', M['Hair'], droop=0.010, size=1.25)
    # basket in the right hand: grip in the middle of the fingers
    grip = _idle_point((-0.752, 0.0, 1.152), 'Right')
    props = _basket(ID, M, grip, -1)
    print('[BUDDY] parts', sorted(((_tris([o]), o.name) for o in out), reverse=True)[:14])
    print(f'[BUDDY] {ID} grip (idle) {tuple(round(c, 3) for c in grip)}; outfit tris {_tris(out)}; props tris {_tris(props)}')
    out += _hand_prop(props, 'Right')
    return out


# ------------------------------------------------------------------ stash courier ("закладчик", TASK-000271)
def stasher(body, face, M, skin):
    """Hood up and dark shades in the woods, a small backpack, a phone in the right hand (he photographs the spot) and a
    fistful of tape-wrapped bundles in the left: suspicious at a glance."""
    ID = STASH
    src = C.weight_source([body])
    hoodie, pocket, out = T._hoodie(ID, M, src)
    out += W.hood_up(ID, M['Hoodie'])
    out.append(T._trousers(ID, M, 'Pants', src, legs=W.LEGS_SWEAT, cuff=W.SWEAT_CUFF, cuff_slot='Pants_Rib'))
    out.append(T._t(W.plain_socks(ID + '_Socks', M['Socks']), src))
    out += W.shoes(ID, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += W.glasses(ID + '_Shades', M['Shades_Frame'], M['Shades_Lens'], rx=0.052, rz=0.054, round_k=0.75)
    hsrc = C.weight_source([hoodie])
    out += [T._t(o, hsrc, C.no_head) for o in W.backpack(ID + '_Backpack', M['Backpack'], M['Backpack_Straps'], hoodie)]
    g = _idle_point((-0.752, 0.0, 1.152), 'Right')
    phone = W.box(ID + '_Phone', (g.x, g.y - 0.030, g.z - 0.040), (0.036, 0.006, 0.072), M['Phone'])
    screen = W.box(ID + '_Screen', (g.x, g.y - 0.0365, g.z - 0.040), (0.031, 0.0012, 0.064), M['Screen'])
    gl = _idle_point((0.752, 0.0, 1.152), 'Left')
    bundles = [G.ellipsoid(f'{ID}_Bundle_{k}', (gl.x + dx, gl.y + dy, gl.z + dz), (0.029, 0.023, 0.025), M[slot], seg=10, rings=6)
               for k, (dx, dy, dz, slot) in enumerate(((0.0, -0.048, -0.014, 'Tape_Blue'), (0.032, -0.036, -0.050, 'Tape_Red'),
                                                       (-0.030, -0.040, -0.052, 'Tape_Yellow'), (0.004, -0.066, -0.040, 'Tape_Blue')))]
    print(f'[BUDDY] {ID} grips (idle) R {tuple(round(c, 3) for c in g)} L {tuple(round(c, 3) for c in gl)}; outfit tris {_tris(out)}')
    out += _hand_prop([phone, screen], 'Right') + _hand_prop(bundles, 'Left')
    return out


BUILDERS = {OD: od_junkie, MUSH: mushroomer, STASH: stasher}
