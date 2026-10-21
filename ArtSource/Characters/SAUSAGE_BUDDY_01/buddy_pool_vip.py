"""VIP parodies of Elite Hill and the island's president (TASK-000875..000876, Vadim 2026-10-21): the king of pop, the
mega-youtuber philanthropist, the blindfolded strongest sorcerer, the screaming streamer and Tramduro.
Original cartoon parodies in the Sausage Buddy style: no real names and no copies of real logos, crests or emblems;
our own look-alike marks (Vadim: «не повторяющие, но похожие») plus a recognisable silhouette, colours and props.
Crowd budget (~13-20k triangles per type). Same format as buddy_types.TYPES / BUILDERS; registered from
buddy_types.POOLS. No bpy calls at import time."""
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
GROUP = 'VIP Элиты'
GOLD = ((214, 174, 76), 0.28, 'metal')

TYPES = {
    'OLD_POPKING': dict(
        label='Король попа (пародия)', group='Даунтаун',   # street NPC, not Elite (Vadim, TASK-000878)
        body=dict(thin=0.9), face=dict(Happy=0.15, Blink=0.2),
        look=dict(skin=(246, 228, 214), nose=(240, 210, 194), brow=(24, 20, 20), rim=(200, 160, 150), mouth=(176, 60, 72)),
        slots={'Jacket': ((20, 20, 24), 0.35), 'Lapel': ((10, 10, 12), 0.2), 'Shirt': ((246, 246, 242), 0.7),
               'Button': GOLD, 'Gold': GOLD, 'Trousers': ((20, 20, 24), 0.6), 'Socks': ((252, 252, 252), 0.6),
               'Shoes': ((12, 12, 14), 0.1), 'Shoe_Sole': ((30, 28, 28), 0.6), 'Hat': ((22, 22, 26), 0.7),
               'HatBand': ((240, 240, 236), 0.6), 'Hair': ((14, 12, 14), 0.3), 'Glove': ((236, 238, 246), 0.12, 'metal'),
               'Armband': ((196, 28, 36), 0.6)},
        colourways=[{'Jacket': (196, 28, 36), 'Lapel': (150, 20, 28)},
                    {'Jacket': (240, 238, 232), 'Lapel': (212, 208, 200), 'Trousers': (240, 238, 232), 'Hat': (240, 238, 232),
                     'HatBand': (22, 22, 26)}]),
    'VIP_BEASTMAN': dict(
        label='Мега-ютубер с чеком (пародия)', group=GROUP, hand_props=True, body=dict(belly=0.3, muscle=0.4), arm_down=68.0,
        game_scale=1.05, face=dict(Happy=0.85, Surprised=0.1),
        look=dict(skin=(244, 196, 168), nose=(236, 166, 140), brow=(120, 82, 52), mouth=(110, 40, 36)),
        slots={'Hoodie': ((64, 156, 232), 0.85), 'Hoodie_Rib': ((50, 132, 206), 0.85), 'Cords': ((246, 246, 242), 0.7),
               'Logo_Ring': ((232, 40, 92), 0.45), 'Logo': ((124, 58, 214), 0.45), 'Logo_Bg': ((22, 26, 70), 0.5),
               'Logo_Kitten': ((64, 168, 255), 0.4), 'Logo_EarIn': ((236, 54, 112), 0.4), 'Logo_Mark': ((150, 80, 230), 0.4),
               'Logo_Eye': ((22, 26, 70), 0.3), 'Logo_Shine': ((250, 250, 255), 0.3), 'Logo_Nose': ((255, 120, 170), 0.4),
               'Cap': ((20, 24, 40), 0.7), 'Cap_Visor': ((20, 24, 40), 0.6),
               'Jeans': ((52, 70, 104), 0.9), 'Jeans_Cuff': ((64, 84, 120), 0.9), 'Socks': ((240, 240, 236), 0.9),
               'Shoe_Upper': ((246, 246, 244), 0.6), 'Shoe_Sole': ((250, 250, 248), 0.6), 'Shoe_Lace': ((236, 236, 232), 0.7),
               'Hair': ((122, 88, 58), 0.75), 'Beard': ((150, 94, 60), 0.9), 'Cheque': ((250, 250, 246), 0.6),
               'Cheque_Frame': ((124, 58, 214), 0.5), 'Ink': ((30, 30, 70), 0.5)},
        colourways=[{'Hoodie': (30, 30, 34), 'Hoodie_Rib': (24, 24, 28)}, {'Hoodie': (230, 70, 140), 'Hoodie_Rib': (206, 56, 120)}]),
    'VIP_BLINDFOLD': dict(
        label='Сильнейший маг в повязке (пародия)', group=GROUP, body=dict(thin=0.9), game_scale=1.08, face=dict(Happy=0.4),
        look=dict(skin=(246, 222, 202), nose=(240, 200, 180), brow=(236, 236, 240), mouth=(150, 70, 70)),
        slots={'Coat': ((24, 26, 40), 0.55), 'Coat_Dark': ((16, 18, 28), 0.5), 'Trousers': ((24, 26, 40), 0.6),
               'Socks': ((20, 20, 24), 0.9), 'Shoes': ((14, 14, 16), 0.2), 'Shoe_Sole': ((24, 24, 26), 0.6),
               'Hair': ((246, 248, 252), 0.4), 'Hair_Shade': ((204, 214, 232), 0.45), 'Blindfold': ((14, 14, 18), 0.5)},
        colourways=[{'Coat': (40, 40, 44), 'Coat_Dark': (28, 28, 32), 'Trousers': (40, 40, 44)},
                    {'Coat': (236, 236, 240), 'Coat_Dark': (206, 206, 214), 'Trousers': (40, 40, 44)}]),
    'VIP_SPEEDSTER': dict(
        label='Орущий стример ISHOWMEET (пародия)', group=GROUP, body=dict(thin=0.5), face=dict(Surprised=1.0, Happy=0.2),
        look=dict(skin=(112, 74, 52), nose=(100, 64, 44), brow=(18, 14, 14), rim=(76, 48, 34), mouth=(58, 26, 22)),
        slots={'Jersey': ((198, 28, 40), 0.6), 'Jersey_Trim': ((20, 112, 62), 0.55), 'Letters': ((246, 230, 150), 0.5),
               'Shorts': ((20, 112, 62), 0.7), 'Shorts_Stripe': ((198, 28, 40), 0.6),
               'Socks': ((246, 246, 242), 0.9), 'Shoe_Upper': ((246, 246, 244), 0.55), 'Shoe_Sole': ((246, 246, 244), 0.6),
               'Shoe_Accent': ((246, 246, 244), 0.55), 'Shoe_Lace': ((240, 240, 236), 0.7), 'Gold': GOLD,
               'Hair': ((20, 16, 14), 0.75), 'Hair_Fade': ((24, 19, 16), 0.85)},
        colourways=[{'Jersey': (246, 246, 242), 'Jersey_Trim': (20, 112, 62), 'Letters': (198, 28, 40), 'Shorts': (246, 246, 242)},
                    {'Jersey': (24, 24, 28), 'Jersey_Trim': (252, 210, 40), 'Letters': (252, 210, 40), 'Shorts': (24, 24, 28)}]),
    'TRAMDURO': dict(
        label='Трамдуро (пародийный президент)', group='Трамдуро', body=dict(belly=1.1), arm_down=64.0,
        face=dict(Worried=0.55, Surprised=0.25, Blink=0.35),
        look=dict(skin=(240, 150, 84), nose=(232, 134, 72), brow=(240, 210, 140), rim=(252, 222, 196), mouth=(150, 70, 60)),
        slots={'Suit': ((26, 34, 64), 0.55), 'Lapel': ((20, 26, 52), 0.4), 'Shirt': ((248, 248, 246), 0.7),
               'Tie': ((200, 22, 34), 0.35), 'Button': ((26, 34, 64), 0.55), 'Socks': ((20, 20, 24), 0.9),
               'Shoes': ((12, 12, 14), 0.12), 'Shoe_Sole': ((30, 26, 24), 0.6), 'Hair': ((248, 222, 140), 0.45),
               'Hair_Streak': ((226, 190, 104), 0.5), 'Pin_Blue': ((30, 50, 140), 0.3), 'Pin_Red': ((200, 22, 34), 0.3),
               'Tan': ((252, 226, 200), 0.55), 'Chin': ((240, 150, 84), 0.5)},
        colourways=[{'Suit': (30, 30, 34), 'Lapel': (22, 22, 26), 'Tie': (40, 70, 160)},
                    {'Suit': (110, 110, 118), 'Lapel': (90, 90, 98), 'Tie': (200, 22, 34)}]),
}

_t = T._t


# ------------------------------------------------------------------ shared helpers
def _text_mesh(name, text, size):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = 2
    tmp = bpy.data.objects.new(name + '_tmp', cu); G.COLLECTION.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    return me


def flat_text(name, text, size, origin, xdir, ydir, material):
    """Flat glyph mesh in the plane (xdir, ydir) centred on origin (props: cheque, signs)."""
    me = _text_mesh(name, text, size)
    vs = [Vector(origin) + Vector(xdir) * v.co.x + Vector(ydir) * v.co.y for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    o = G.from_data(name, vs, fs, material, False, fix_normals=False)
    nrm = Vector(xdir).cross(Vector(ydir))
    if o.data.polygons and o.data.polygons[0].normal.dot(nrm) < 0:
        o.data.flip_normals()
    return o


def back_text(name, text, cz, material, target, size=0.16, off=0.004):
    """Lettering on the back of a garment, read from behind, projected onto the cloth."""
    me = _text_mesh(name, text, size)
    bvh = G.bvh_of([target])
    vs = []
    for v in me.vertices:
        x, z = -v.co.x, cz + v.co.y                 # mirrored: the viewer stands behind the character
        hit = bvh.ray_cast(Vector((x, 0.7, z)), Vector((0, -1, 0)), 1.6)
        vs.append(hit[0] + hit[1] * off if hit[0] is not None else Vector((x, 0.14, z)))
    fs = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    o = G.from_data(name, vs, fs, material, False, fix_normals=False)
    if o.data.polygons and o.data.polygons[0].normal.y < 0:
        o.data.flip_normals()
    return o


def _hair_weights(ob, z_lo=1.28, z_hi=1.38):
    C.set_weights(ob, [{P + 'Head': smoothstep(z_lo, z_hi, p.z), P + 'Spine2': 1.0 - smoothstep(z_lo, z_hi, p.z)}
                       for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
    return ob


def spikes(prefix, material, specs, seg=6):
    """Cone spikes of hair: specs = [(phi_deg, z, length, radius, up, back, side)], each from the head surface along the
    surface normal bent upward / backward / sideways."""
    out = []
    for k, (deg, z, length, r, up, back, side) in enumerate(specs):
        phi = math.radians(deg)
        p, n = W.head_at(phi, W.h_of(z), 0.004)
        d = (n + Vector((0, 0, up)) + Vector((0, back, 0)) + Vector((side, 0, 0))).normalized()
        mid = p + d * length * 0.55 + Vector((0, 0, 0.010 * up))
        out.append(G.tube(f'{prefix}_{k}', [p - d * 0.008, mid, p + d * length], lambda i, nn: (r, r * 0.62, 0.0015)[i], material, seg=seg))
    return [C.rigid(o, 'Head') for o in out]


def glove(prefix, body, material, side='Right', off=0.0030):
    """A glove over one hand: a copy of the body's hand faces pushed out along the normals, same skin weights."""
    names = {g.index: g.name for g in body.vertex_groups}
    me = body.data
    hand = P + side + 'Hand'

    def hand_w(v):
        return sum(g.weight for g in v.groups if names.get(g.group, '').startswith(hand))
    keep = {v.index for v in me.vertices if hand_w(v) > 0.55}
    faces = [p for p in me.polygons if all(i in keep for i in p.vertices)]
    remap, vs, ws = {}, [], []
    mw = body.matrix_world
    for p in faces:
        for i in p.vertices:
            if i not in remap:
                v = me.vertices[i]
                remap[i] = len(vs)
                vs.append(mw @ (v.co + v.normal * off))
                ws.append({names[g.group]: g.weight for g in v.groups if g.weight > 1e-4 and g.group in names})
    fs = [tuple(remap[i] for i in p.vertices) for p in faces]
    ob = G.from_data(prefix, vs, fs, material, True)
    C.set_weights(ob, ws)
    return ob


def jaw_beard(prefix, material, top, bot, bulge=0.010, cols=34, rows=5, arc_deg=82.0, base=0.007, thick=0.006):
    """Short trimmed beard hugging the jaw from ear to ear (top / bot: [(azimuth deg, z)] edges)."""
    def interp(table, x):
        if x <= table[0][0]:
            return table[0][1]
        for (x0, v0), (x1, v1) in zip(table, table[1:]):
            if x <= x1:
                return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
        return table[-1][1]
    arc = math.radians(arc_deg)
    vs, fs, grid = [], [], []
    for j in range(cols + 1):
        phi = -arc + 2 * arc * j / cols
        d = abs(math.degrees(phi))
        f = max(0.0, math.cos(phi)) ** 1.4
        zb, zt = interp(bot, d), interp(top, d)
        col = []
        for i in range(rows + 1):
            u = i / rows
            off = base + bulge * f * math.sin(math.pi * min(1.0, 0.15 + u * 0.95))
            p, _ = W.head_at(phi, zb + (zt - zb) * u, off)
            col.append(len(vs)); vs.append(p)
        grid.append(col)
    for a, b in zip(grid, grid[1:]):
        for i in range(rows):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    ob = G.from_data(prefix, vs, fs, material, True, fix_normals=False)
    G.solidify(ob, thick, offset=1.0)
    C.set_weights(ob, [{P + 'Head': smoothstep(1.22, 1.34, p.z), P + 'Neck': 1 - smoothstep(1.22, 1.34, p.z)}
                       for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
    return ob


# ------------------------------------------------------------------ OLD_POPKING
FEDORA_BASE = W.zprofile([(0, 1.664), (90, 1.652), (180, 1.640)])


def fedora(prefix, M, tilt_deg=10.0):
    """Black fedora with a white band, pinched crown and a snap brim (down at the front, up at the sides and back),
    tilted forward over the eyes."""
    rows = [('fit', FEDORA_BASE, 0.006), (1.692, 0.156, 0.160, 0.0, 0.0), (1.716, 0.154, 0.158, 0.0, 0.0),
            (1.786, 0.141, 0.150, 0.004, -0.004), (1.826, 0.120, 0.136, 0.006, -0.010), (1.842, 0.064, 0.104, 0.008, -0.013)]
    crown = W.ring_loft(prefix + '_Crown', rows, [M['Hat'], M['HatBand']], row_mat=[1, 1, 0, 0, 0, 0], seg=32)
    curl = W.profile([(0, -0.014), (60, 0.004), (100, 0.016), (180, 0.012)])
    vs, fs, seg = [], [], 32
    rings = [[], [], []]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        p0, _ = W.head_at(phi, FEDORA_BASE(phi), 0.006)
        outv = Vector((math.sin(phi), -math.cos(phi), 0))
        for k, (w, d) in enumerate(((0.0, 0.0), (0.036, 0.35), (0.070, 1.0))):
            rings[k].append(len(vs)); vs.append(p0 + outv * w + Vector((0, 0, curl(phi) * d)))
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    brim = G.from_data(prefix + '_Brim', vs, fs, M['Hat'], True, fix_normals=False)
    G.solidify(brim, 0.006, offset=0.0)
    pivot = Vector((0, 0, 1.66))
    m = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(tilt_deg), 4, 'X') @ Matrix.Rotation(math.radians(-8), 4, 'Z') @ \
        Matrix.Translation(-pivot)
    for o in (crown, brim):
        o.data.transform(m); o.data.update()
    return [C.rigid(o, 'Head') for o in (crown, brim)]


def long_hair(prefix, M):
    """Long glossy black hair to the shoulders in loose waves (cap under the hat, locks framing the face and falling
    over the collar at the back), plus the single curl on the forehead."""
    import buddy_pool_bad2 as BD2
    lower = W.zprofile([(0, 1.676), (35, 1.660), (55, 1.585), (80, 1.500), (180, 1.440)])
    upper = lambda phi: FEDORA_BASE(phi) + 0.030
    cap, _ = W.shell(prefix + '_Cap', M['Hair'], lower, upper, off=0.010, thick=0.006, seg=32, rows=3)
    out = [C.rigid(cap, 'Head')]
    rnd = random.Random(23)
    for k, deg in enumerate([48, 62, 78, 96, 116, 136, 158, 180, 202, 224, 244, 264, 282, 298, 312]):
        phi = math.radians(deg)
        radial = Vector((math.sin(phi), -math.cos(phi), 0.0))
        p0, n0 = W.head_at(phi, lower(phi) + 0.030, 0.016)
        front = max(0.0, math.cos(phi))
        z_end = 1.215 + 0.090 * front + rnd.uniform(-0.015, 0.015)
        pts, nrms = [p0], [n0]
        for i in range(1, 7):
            u = i / 6
            z = p0.z + (z_end - p0.z) * u
            push = 0.030 + 0.030 * smoothstep(0.35, 1.0, u)
            q = Vector((p0.x, p0.y, 0)) * (1.0 + 0.10 * u) + radial * push
            pts.append(Vector((q.x, q.y, z))); nrms.append(radial)
        lock = BD2._wavy_lock(f'{prefix}_Lock_{k}', pts, nrms, 0.040 if front < 0.3 else 0.030, 0.010, M['Hair'], wave=0.012)
        out.append(lock)
    c0, _ = W.head_at(math.radians(-22), W.h_of(1.652), 0.016)
    pts = [c0 + Vector((0.020 * math.sin(a) * (1 - a / 9), -0.004, -0.010 * a / 1.6 - 0.012 * math.cos(a) * (1 - a / 9)))
           for a in [i * 0.5 for i in range(15)]]
    out.append(C.rigid(G.tube(prefix + '_ForeheadCurl', pts, lambda i, nn: 0.0065 - 0.0035 * i / max(1, nn - 1), M['Hair'], seg=6), 'Head'))
    return out


def armband(prefix, material, side=1, x=0.300, r=0.076, width=0.038):
    path = [Vector((side * (x - width / 2), 0, 1.164)), Vector((side * (x + width / 2), 0, 1.163))]
    return C.rigid(G.tube(prefix, path, r, material, seg=16), ('Left' if side > 0 else 'Right') + 'Arm')


def popking(body, face, M, skin):
    """King-of-pop parody: black fedora with a white band tipped over the eyes, long glossy black hair to the shoulders
    and the forehead curl, a pale face with red lips, a black military-cut jacket with two rows of gold buttons and gold
    epaulettes, a red armband, one silver sequin glove on the right hand, high-water black trousers flashing white
    socks, black loafers."""
    pre = 'OLD_POPKING'
    src = C.weight_source([body])
    jacket, out = T._suit(pre, M, src, 'Jacket', None, 'Button')
    jsrc = C.weight_source([jacket])
    btns = W.buttons(pre + '_Row', jacket, M['Gold'], [(s * 0.072, z) for s in (1, -1) for z in (1.150, 1.080, 1.010, 0.940)], r=0.009)
    import buddy_pool_bad as BD
    epa = []
    for s in (1, -1):
        epa.append(BD.rbox(f'{pre}_Epaulette_{s}', Vector((s * 0.205, 0.0, 1.238)), (0.058, 0.050, 0.008), M['Gold'], bevel=0.006))
        for k in range(7):
            x = s * (0.250 + 0.004 * k)
            epa.append(G.tube(f'{pre}_Fringe_{s}_{k}', [(x, -0.044 + 0.0145 * k, 1.236), (x + s * 0.010, -0.044 + 0.0145 * k, 1.205)],
                              0.0032, M['Gold'], seg=5))
    out += [_t(o, jsrc) for o in btns + epa]
    out.append(T._trousers(pre, M, 'Trousers', src, legs=W.LEGS_ANKLE))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks'], top=0.30), src))
    out += T._dress_shoes(pre, M)
    out.append(armband(pre + '_Armband', M['Armband'], side=1))
    out.append(glove(pre + '_Glove', body, M['Glove'], 'Right'))
    out += fedora(pre + '_Hat', M)
    out += long_hair(pre + '_Hair', M)
    return out


# ------------------------------------------------------------------ VIP_BEASTMAN
def kitten_logo(prefix, M, place, k=1.0):
    """Our own channel mark in the look-alike palette of the original (Vadim, TASK-000895: blue, purple, red): a red outer
    ring, a purple ring and a dark navy disc with an angular blue kitten head (sharp ears with red-pink insides, purple
    forehead markings, slanted navy eyes with shines, a pink nose). Not the original panther: a kitten, our own shapes.
    place(name, outline, material, offset) projects one outline in logo space (x right, z up, metres)."""
    def ell(cx, cz, rx, rz, n=18):
        return [((cx + rx * math.cos(a)) * k, (cz + rz * math.sin(a)) * k) for a in [2 * math.pi * i / n for i in range(n)]]

    def sc(pts):
        return [(x * k, z * k) for x, z in pts]

    def mir(pts, s):
        q = [(s * x, z) for x, z in pts]
        return q if s > 0 else q[::-1]
    out = [place(prefix + '_Ring', ell(0.0, 0.0, 0.080, 0.080, 30), M['Logo_Ring'], 0.0026),
           place(prefix + '_Disc', ell(0.0, 0.0, 0.072, 0.072, 30), M['Logo'], 0.0032),
           place(prefix + '_Bg', ell(0.0, 0.0, 0.062, 0.062, 30), M['Logo_Bg'], 0.0038)]
    head = [(0.000, -0.046), (0.018, -0.040), (0.036, -0.024), (0.048, -0.002), (0.046, 0.022), (0.052, 0.058), (0.030, 0.038),
            (0.012, 0.042), (0.000, 0.040), (-0.012, 0.042), (-0.030, 0.038), (-0.052, 0.058), (-0.046, 0.022), (-0.048, -0.002),
            (-0.036, -0.024), (-0.018, -0.040)]
    out.append(place(prefix + '_Head', sc(head), M['Logo_Kitten'], 0.0046))
    for s in (1, -1):
        out.append(place(f'{prefix}_EarIn_{s}', sc(mir([(0.032, 0.036), (0.046, 0.050), (0.042, 0.022)], s)), M['Logo_EarIn'], 0.0054))
        out.append(place(f'{prefix}_Eye_{s}', sc(mir([(0.008, 0.000), (0.034, 0.014), (0.036, 0.000), (0.020, -0.010)], s)), M['Logo_Eye'],
                         0.0056))
        out.append(place(f'{prefix}_Shine_{s}', ell(s * 0.026, 0.006, 0.0040, 0.0040, 8), M['Logo_Shine'], 0.0064))
        out.append(place(f'{prefix}_Mark_{s}', sc(mir([(0.006, 0.040), (0.016, 0.040), (0.010, 0.022)], s)), M['Logo_Mark'], 0.0056))
    out.append(place(prefix + '_Mark_0', sc([(-0.004, 0.040), (0.004, 0.040), (0.0, 0.026)]), M['Logo_Mark'], 0.0056))
    out.append(place(prefix + '_Nose', sc([(-0.007, -0.016), (0.007, -0.016), (0.0, -0.025)]), M['Logo_Nose'], 0.0058))
    return out


def big_cheque(prefix, M, arm_down):
    """Giant novelty cheque hanging from the right fist by its top edge: white board, green frame, the channel mark,
    '$1 000 000' and 'PAY TO: YOU' on both faces."""
    import buddy_pool_hamlet as HM
    import buddy_pool_bad as BD
    fist, _, _ = HM.grip('Right', arm_down)
    c = fist + Vector((0.0, 0.130, -0.150))
    parts = [BD.rbox(prefix + '_Frame', c, (0.006, 0.310, 0.140), M['Cheque_Frame'], bevel=0.004),
             BD.rbox(prefix + '_Board', c, (0.0085, 0.290, 0.122), M['Cheque'], bevel=0.004)]
    for s in (1, -1):
        o = c + Vector((s * 0.0095, 0, 0))
        xd = Vector((0, s, 0))                  # reads left-to-right for a viewer on that side
        parts.append(flat_text(f'{prefix}_Sum_{s}', '$1 000 000', 0.072, o + Vector((0, s * 0.040, -0.010)), xd, Vector((0, 0, 1)), M['Ink']))
        parts.append(flat_text(f'{prefix}_Pay_{s}', 'PAY TO: YOU', 0.030, o + Vector((0, s * 0.060, 0.075)), xd, Vector((0, 0, 1)), M['Ink']))
        parts.append(BD.rbox(f'{prefix}_Line_{s}', o + Vector((0, s * 0.140, -0.085)), (0.0008, 0.080, 0.0025), M['Ink'], bevel=0.0005))
        lc = o + Vector((0, -s * 0.215, 0.030))

        def place(name, outline, mat, off, lc=lc, s=s, xd=xd):
            vs = [lc + xd * x + Vector((0, 0, z)) + Vector((s * off * 0.3, 0, 0)) for x, z in outline]
            ob = G.from_data(name, vs, [tuple(range(len(vs)))], mat, False, fix_normals=False)
            if ob.data.polygons and ob.data.polygons[0].normal.x * s < 0:
                ob.data.flip_normals()
            return ob
        parts += kitten_logo(f'{prefix}_Logo_{s}', M, place, k=0.95)
    return HM.hold(parts, 'Right', arm_down)


def beastman(body, face, M, skin):
    """Mega-youtuber philanthropist parody (after Vadim's photo): big friendly guy with a wide toothy grin, short
    light-brown hair falling forward in a side-swept fringe under a dark baseball cap, a short trimmed ginger-brown beard
    along the jaw with a thin moustache, a light-blue hoodie with our kitten channel mark on the chest and the same mark
    on the cap, dark jeans, white sneakers, a giant novelty cheque in the right hand."""
    import buddy_pool_beach as BE
    pre = 'VIP_BEASTMAN'
    src = C.weight_source([body])
    hoodie, pocket, out = T._hoodie(pre, M, src)
    out.append(T._hood_down(pre, M['Hoodie']))
    hsrc = C.weight_source([hoodie])
    out += [_t(o, hsrc) for o in kitten_logo(pre + '_Logo', M, lambda n, pts, m, off: W.front_decal(
        n, [(x, 1.108 + z) for x, z in pts], hoodie, m, off, step=0.006), k=1.12)]
    for s in (1, -1):
        path = [(s * 0.040, -0.168, 1.236), (s * 0.044, -0.192, 1.17), (s * 0.046, -0.198, 1.10), (s * 0.045, -0.199, 1.045)]
        out.append(_t(G.tube(f'{pre}_Cord_{s}', path, 0.0062, M['Cords'], seg=8), src,
                      lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else w))
    out.append(T._trousers(pre, M, 'Jeans', src, legs=W.LEGS_ANKLE, cuff=W.ANKLE_CUFF, cuff_slot='Jeans_Cuff'))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.shoes(pre, M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    cap = BE.baseball_cap(pre + '_Cap', M['Cap'], M['Cap_Visor'])
    crown = cap[0]
    out += cap
    out += [C.rigid(o, 'Head') for o in kitten_logo(pre + '_CapLogo', M, lambda n, pts, m, off: G.decal(
        n, [(x, 1.728 + z) for x, z in pts], W.FRONT(), [crown], off, m, step=0.004), k=0.42)]
    cap_low = W.zprofile([(0, 1.676), (90, 1.664), (180, 1.652)])
    out.append(W.hair(pre + '_Hair', M['Hair'], 'slick', upper=lambda phi: cap_low(phi) - 0.002))
    out += spikes(pre + '_Fringe', M['Hair'], [(d, 1.652, 0.026, 0.012, -2.2, -0.6, s) for d, s in
                                              ((-36, -0.3), (-20, -0.2), (-4, -0.1), (12, 0.0))], seg=6)
    out.append(jaw_beard(pre + '_Beard', M['Beard'], top=[(0, 1.382), (14, 1.386), (28, 1.396), (46, 1.420), (66, 1.452), (80, 1.480)],
                         bot=[(0, 1.318), (20, 1.322), (40, 1.342), (60, 1.380), (80, 1.430)], bulge=0.002, rows=4, base=0.003,
                         thick=0.0035, arc_deg=80.0))
    out += W.mustache(pre + '_Mustache', M['Beard'], droop=0.004, size=0.62)
    out += big_cheque(pre + '_Cheque', M, TYPES[pre]['arm_down'])
    return out


# ------------------------------------------------------------------ VIP_BLINDFOLD
def blindfold(prefix, material, z0=1.494, z1=1.634, seg=36):
    """Black cloth band wrapped all the way round the head over the eyes, proud of the eyeballs at the front and of
    the hair at the back, knotted at the back with two short tails."""
    rows = [(z0, 0.160, 0.166, -0.008, 0.0), (z0 + 0.012, 0.166, 0.171, -0.008, 0.0), (z1 - 0.012, 0.166, 0.171, -0.008, 0.0),
            (z1, 0.160, 0.166, -0.008, 0.0)]
    band = W.ring_loft(prefix, rows, [material], seg=seg, cap_top=False)
    G.solidify(band, 0.005, offset=0.0)
    knot = G.ellipsoid(prefix + '_Knot', (0.0, 0.170, 1.566), (0.032, 0.018, 0.026), material, seg=10, rings=6)
    tails = [G.tube(f'{prefix}_Tail_{s}', [(s * 0.010, 0.178, 1.560), (s * 0.026, 0.192, 1.500), (s * 0.036, 0.204, 1.440)],
                    lambda i, n: (0.015, 0.012, 0.008)[i], material, seg=6) for s in (1, -1)]
    return [C.rigid(o, 'Head') for o in [band, knot] + tails]


def _lock(name, root, nrm, d, length, r0, material, bend=0.35, seg=6):
    """One soft curved spike: from the scalp along d, the tip bending further up/back by `bend`, tapering to a point."""
    pts = [root - nrm * 0.006]
    for i in range(1, 6):
        u = i / 5
        q = root + d * length * u + Vector((0, 0.35 * bend, 0.6 * bend)) * length * u * u
        pts.append(q)
    return G.tube(name, pts, lambda i, n: r0 * (1.0 - 0.80 * (i / max(1, n - 1)) ** 1.4) + 0.0030, material, seg=seg)


def snow_hair(prefix, M, seed=17):
    """Snow-white hair pushed up by the blindfold (Vadim, TASK-000895: prettier): a soft cap from just above the band,
    an inner layer of short pale-blue-shaded locks for depth and an outer crown of long soft curved spikes swept up and
    back, fanning out at the sides, a few locks falling forward over the band, a short undercut below the band at the
    back."""
    import random as _r
    rnd = _r.Random(seed)
    lower = W.zprofile([(0, 1.640), (90, 1.642), (180, 1.642)])
    cap, _ = W.shell(prefix + '_Cap', M['Hair'], lower, None, off=0.012, thick=0.008, seg=32, rows=6)
    under, _ = W.shell(prefix + '_Under', M['Hair'], W.zprofile([(70, 1.430), (180, 1.410)]), lambda phi: W.h_of(1.496),
                       off=0.006, thick=0.005, seg=24, rows=2, arc=(math.radians(70), math.radians(290)))
    out = [C.rigid(cap, 'Head'), C.rigid(under, 'Head')]
    k = 0
    for layer, (count, zr, lr, rr, mat) in enumerate(((26, (1.650, 1.745), (0.050, 0.072), 0.026, 'Hair_Shade'),
                                                      (36, (1.648, 1.750), (0.080, 0.120), 0.032, 'Hair'))):
        placed = []
        tries = 0
        while len(placed) < count and tries < count * 60:
            tries += 1
            phi = math.radians(rnd.uniform(-180, 180))
            z = rnd.uniform(*zr)
            p, nrm = W.head_at(phi, W.h_of(min(z, B.HEAD_TOP - 0.002)), 0.010)
            if any((p - q).length < (0.026 if layer else 0.024) for q in placed):
                continue
            placed.append(p)
            back = (1 - math.cos(phi)) / 2
            side = math.sin(phi)
            d = (nrm * 0.8 + Vector((0, 0, 0.9 - 0.3 * back)) + Vector((0, 0.45 + 0.4 * back, 0)) + Vector((0.25 * side, 0, 0))).normalized()
            length = rnd.uniform(*lr) * (1.0 - 0.25 * back)
            out.append(C.rigid(_lock(f'{prefix}_L{layer}_{k}', p, nrm, d, length, rr, M[mat], bend=0.25 + 0.2 * rnd.random()), 'Head'))
            k += 1
    for j, deg in enumerate((-34, -16, 2, 20, 36)):                 # a few locks falling forward over the band
        phi = math.radians(deg)
        p, nrm = W.head_at(phi, W.h_of(1.668), 0.012)
        d = (nrm * 0.7 + Vector((0, 0, -0.9)) + Vector((0.15 * math.sin(phi), 0, 0))).normalized()
        out.append(C.rigid(_lock(f'{prefix}_Bang_{j}', p, nrm, d, rnd.uniform(0.050, 0.064), 0.016, M['Hair'], bend=-0.15), 'Head'))
    return out


def tall_collar(name, material, open_deg=6.0, seg=28):
    """High stand-up uniform collar reaching up under the chin."""
    vs, fs, cols = [], [], []
    a0, a1 = math.radians(open_deg), math.radians(360 - open_deg)
    rows = ((1.236, 0.170, 0.166), (1.300, 0.166, 0.162), (1.352, 0.164, 0.160), (1.362, 0.158, 0.154))
    for j in range(seg + 1):
        phi = a0 + (a1 - a0) * j / seg
        col = []
        for z, rx, ry in rows:
            col.append(len(vs)); vs.append(Vector((rx * math.sin(phi), -ry * math.cos(phi), z)))
        cols.append(col)
    for j in range(seg):
        a, b = cols[j], cols[j + 1]
        for i in range(len(rows) - 1):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    ob = G.from_data(name, vs, fs, material, True, fix_normals=False)
    G.solidify(ob, 0.007, offset=0.0)
    C.set_weights(ob, [{P + 'Neck': smoothstep(1.24, 1.34, p.z), P + 'Spine2': 1 - smoothstep(1.24, 1.34, p.z)}
                       for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
    return ob


def blindfold_mage(body, face, M, skin):
    """Strongest-sorcerer parody: tall and slim, spiky snow-white hair, a black blindfold wrapped round the whole head
    over the eyes, a dark navy-black high-collared uniform jacket closed with a hidden fly (no emblem, no buttons),
    black trousers and shoes."""
    pre = 'VIP_BLINDFOLD'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Coat', src)
    jsrc = C.weight_source([jacket])
    fly = W.front_decal(pre + '_Fly', [(-0.006, 0.705), (0.006, 0.705), (0.006, 1.240), (-0.006, 1.240)], jacket, M['Coat_Dark'], 0.0030)
    out = [jacket, tall_collar(pre + '_Collar', M['Coat']), _t(fly, jsrc)]
    out.append(T._trousers(pre, M, 'Trousers', src))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += T._dress_shoes(pre, M)
    out += blindfold(pre + '_Blindfold', M['Blindfold'])
    out += snow_hair(pre + '_Hair', M)
    return out


# ------------------------------------------------------------------ VIP_SPEEDSTER
def curly_mound(prefix, M, n=118, seed=31):
    """The streamer's hair (after Vadim's reference): a tight taper on the sides and the back and a big springy mound
    of tight curls on top, swept up and back, the hairline at the forehead raised; clumps of curl blobs."""
    fade, _ = W.shell(prefix + '_Fade', M['Hair_Fade'], W.HAIRLINE, None, off=0.0015, thick=0.0035, seg=32, rows=8)
    low = W.profile([(0, 1.665), (45, 1.650), (80, 1.630), (120, 1.610), (180, 1.600)])
    lowm = lambda phi: W.h_of(low(phi)) + 0.006
    mound, _ = W.shell(prefix + '_Mound', M['Hair'], lowm, None, off=lambda phi, u: 0.010 + 0.040 * smoothstep(0.0, 0.7, u)
                       + 0.016 * (1 - math.cos(phi)) / 2 * u, thick=0.0, seg=28, rows=6)
    out = [C.rigid(fade, 'Head'), C.rigid(mound, 'Head')]
    rnd = random.Random(seed)
    tries = 0
    k = 0
    while k < n and tries < n * 40:
        tries += 1
        phi = math.radians(rnd.uniform(-180, 180))
        z = rnd.uniform(low(phi), B.HEAD_TOP)
        back = (1 - math.cos(phi)) / 2
        u = (z - low(phi)) / max(0.01, B.HEAD_TOP - low(phi))
        p, nrm = W.head_at(phi, W.h_of(min(z, B.HEAD_TOP - 0.002)), 0.0)
        lift = 0.016 + 0.050 * smoothstep(0.0, 0.7, u) + 0.020 * back * u
        c = p + nrm * lift + Vector((0, 0.020 * u + 0.012 * back, 0.012 * u))
        r = rnd.uniform(0.022, 0.032)
        rot = Matrix.Rotation(rnd.uniform(0, 3.14), 3, 'Z') @ Matrix.Rotation(rnd.uniform(-0.6, 0.6), 3, 'X')
        out.append(C.rigid(G.ellipsoid(f'{prefix}_Curl_{k}', c, (r, r * 0.92, r * 0.85), M['Hair'], rot=rot, seg=7, rings=4), 'Head'))
        k += 1
    return out


def mini_locs(prefix, M, seed=31):
    """The streamer's hair (after Vadim's references): short twisted mini dreads all over the head, swept up and back
    and sticking out behind the head, the forehead clear, over a dark scalp layer."""
    scalp, _ = W.shell(prefix + '_Scalp', M['Hair_Fade'], W.HAIRLINE, None, off=0.004, thick=0.004, seg=32, rows=7)
    out = [C.rigid(scalp, 'Head')]
    rnd = random.Random(seed)
    roots = []
    tries = 0
    while len(roots) < 78 and tries < 6000:
        tries += 1
        phi = math.radians(rnd.uniform(-180, 180))
        z = rnd.uniform(1.600, B.HEAD_TOP)
        if W.h_of(z) < W.HAIRLINE(phi) + 0.012:
            continue
        p, n = W.head_at(phi, W.h_of(min(z, B.HEAD_TOP - 0.002)), 0.006)
        if any((p - q).length < 0.024 for q, _, _ in roots):
            continue
        roots.append((p, n, phi))
    for k, (p, n, phi) in enumerate(roots):
        back = (1 - math.cos(phi)) / 2
        # swept up and back, sticking out behind the head (Vadim's 3rd reference): forehead stays clear
        d = (n * 0.55 + Vector((0, 0, 0.55 - 0.35 * back)) + Vector((0, 0.95, 0))).normalized()
        side = Vector((math.cos(phi), math.sin(phi), 0.0))
        length = 0.050 + 0.035 * back + 0.015 * rnd.random()
        pts = [p - n * 0.004]
        for i2 in range(1, 6):
            u = i2 / 5
            q = p + d * length * u + n * 0.010 * math.sin(math.pi * u) + side * 0.005 * math.sin(5.0 * u + k)
            q += Vector((0, 0, -0.010 * u * u * back))
            pts.append(q)
        rr = rnd.uniform(0.0085, 0.0110)
        lock = G.tube(f'{prefix}_Loc_{k}', pts, lambda i, nn, rr=rr: rr * (1.0 - 0.35 * i / max(1, nn - 1)), M['Hair'], seg=5)
        out.append(_hair_weights(lock, z_lo=1.30, z_hi=1.40))
    return out


def sponge_twists(prefix, M, n=96, seed=41):
    """The streamer's signature cut, chosen as the most recognisable one (Vadim, TASK-000887): a crisp line-up at the
    forehead, a tight taper on the sides and the back, and a compact high top of short coiled sponge twists standing up
    and leaning slightly back."""
    fade, _ = W.shell(prefix + '_Fade', M['Hair_Fade'], W.HAIRLINE, None, off=0.0015, thick=0.0035, seg=32, rows=8)
    out = [C.rigid(fade, 'Head')]
    low = W.profile([(0, 1.676), (40, 1.668), (80, 1.652), (130, 1.640), (180, 1.636)])
    lowm = lambda phi: W.h_of(low(phi))
    top_off = lambda phi, u: 0.010 + 0.020 * smoothstep(0.0, 0.5, u) + 0.006 * (1 - math.cos(phi)) / 2
    mound, _ = W.shell(prefix + '_Top', M['Hair'], lowm, None, off=top_off, thick=0.0, seg=32, rows=6)
    out.append(C.rigid(mound, 'Head'))
    rnd = random.Random(seed)
    roots = []
    tries = 0
    while len(roots) < n and tries < n * 80:
        tries += 1
        phi = math.radians(rnd.uniform(-180, 180))
        z = rnd.uniform(low(phi) + 0.004, B.HEAD_TOP)
        h = W.h_of(min(z, B.HEAD_TOP - 0.002))
        u = (h - lowm(phi)) / max(0.01, W.H_POLE - lowm(phi))
        p, nrm = W.head_at(phi, h, top_off(phi, min(1.0, u)) - 0.004)
        if any((p - q).length < 0.019 for q, _, _ in roots):
            continue
        roots.append((p, nrm, u))
    for k, (p, nrm, u) in enumerate(roots):
        d = (nrm + Vector((0, 0, 0.9)) + Vector((0, 0.35, 0))).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a).normalized()
        length = rnd.uniform(0.030, 0.046) * (0.75 + 0.35 * min(1.0, u * 1.5))
        pts = []
        for i in range(7):
            s = i / 6
            ang = 2 * math.pi * 1.0 * s + k
            pts.append(p + d * length * s + (a * math.cos(ang) + b * math.sin(ang)) * 0.0022)
        out.append(C.rigid(G.tube(f'{prefix}_Twist_{k}', pts, lambda i, nn: 0.0120 - 0.0040 * i / max(1, nn - 1), M['Hair'], seg=6),
                           'Head'))
    return out


def sport_jersey(prefix, M, src):
    """Sport jersey in colours that recall the Portugal kit (Vadim, TASK-000881) but no crest, no number, no sponsor:
    red, a green neck band, green sleeve hems and side stripes, ISHOWMEET in big letters across the back."""
    rows = W.TEE
    jersey = W.top(prefix + '_Jersey', rows, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Jersey'], M['Jersey_Trim']],
                   row_mat=[0] * (len(rows) - 1), sleeve_mat=[0] * (len(W.SLEEVE_SHORT) - 2) + [1, 1])
    _t(jersey, src, C.no_head)
    jsrc = C.weight_source([jersey])
    band = G.tube(prefix + '_Neckband', [Vector((0.150 * math.sin(a), -0.146 * math.cos(a) + 0.002, 1.252 - 0.010 * (1 + math.cos(a)) / 2))
                                         for a in [2 * math.pi * i / 32 for i in range(33)]], 0.0075, M['Jersey_Trim'], seg=6)
    deco = [G.decal(f'{prefix}_Side_{s}', [(-0.012, 0.812), (0.012, 0.812), (0.012, 1.085), (-0.012, 1.085)], G.SIDE(s), [jersey], 0.003,
                    M['Jersey_Trim'], step=0.012) for s in (1, -1)]
    deco.append(back_text(prefix + '_Name', 'ISHOWMEET', 1.150, M['Letters'], jersey, size=0.048))
    return jersey, [jersey, _t(band, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]


def speedster(body, face, M, skin):
    """Screaming-streamer parody (after Vadim's reference): a big springy mound of curls swept up and back over a tight
    taper, the mouth wide open, a red-and-green sport jersey with ISHOWMEET across the back, a gold chain, green sport
    shorts with red side stripes, white crew socks, chunky white sneakers (no crest, no football kit)."""
    import buddy_pool_bad2 as BD2
    pre = 'VIP_SPEEDSTER'
    src = C.weight_source([body])
    jersey, out = sport_jersey(pre, M, src)
    chain, _ = BD2._chain(pre + '_Chain', M['Gold'], [jersey], drop=0.150, rad=0.166, off=0.012)
    out.append(_t(chain, C.weight_source([jersey]), C.no_head))
    shorts = W.bottoms(pre + '_Shorts', [(.70, .094), (.640, .096), (.600, .090)], [M['Shorts']])
    _t(shorts, src)
    out += [shorts] + T._decal_t(W.leg_stripes(pre + '_Stripe', shorts, M['Shorts_Stripe'], offsets=(0.0,), width=0.012, z0=0.605, z1=0.86),
                                 shorts)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks'], top=0.22), src))
    out += BD2._chunky_sneakers(pre, M)
    out += sponge_twists(pre + '_Hair', M)
    return out


# ------------------------------------------------------------------ TRAMDURO
def president_hair(prefix, M):
    """The famous golden swoop: a thick combed helmet, swept from the back-left over the crown to a big wave hanging
    over the forehead, sides combed back over the ears, a few darker streaks."""
    import buddy_pool_bad2 as BD2
    lower = W.zprofile([(0, 1.660), (30, 1.650), (60, 1.580), (85, 1.500), (120, 1.460), (180, 1.440)])
    front = lambda phi: max(0.0, math.cos(phi)) ** 1.4

    def off(phi, u):
        return 0.014 + 0.046 * front(phi) * math.sin(math.pi * min(1.0, 0.20 + u * 0.85)) + 0.016 * smoothstep(0.3, 1.0, u)
    helmet, _ = W.shell(prefix + '_Helmet', M['Hair'], lower, None, off=off, thick=0.010, seg=36, rows=8)
    out = [C.rigid(helmet, 'Head')]
    for k, (a0, a1, w) in enumerate(((150, -34, 0.100), (118, -10, 0.080), (178, 12, 0.070), (-120, -40, 0.060))):
        pts, nrms = [], []
        for i in range(9):
            u = i / 8
            phi = math.radians(a0 + (a1 - a0) * u)
            h = W.h_of(1.735 - 0.020 * k) + 0.020 * math.sin(math.pi * u) - (0.050 * smoothstep(0.75, 1.0, u))
            p, n = W.head_at(phi, min(h, W.H_POLE - 0.004), 0.040 + 0.016 * math.sin(math.pi * u) + 0.030 * smoothstep(0.6, 1.0, u))
            pts.append(p); nrms.append(n)
        lock = BD2._wavy_lock(f'{prefix}_Swoop_{k}', pts, nrms, w, 0.016, M['Hair'] if k != 1 else M['Hair_Streak'], wave=0.004)
        out.append(C.rigid(lock, 'Head'))
    return out


def flag_pin(prefix, jacket, M):
    """Little flag pin on the left lapel: a blue square and red stripes (no real flag)."""
    x0, z0 = 0.092, 1.176
    out = [W.front_decal(prefix + '_Blue', [(x0, z0), (x0 + 0.012, z0), (x0 + 0.012, z0 + 0.012), (x0, z0 + 0.012)], jacket, M['Pin_Blue'],
                         0.0060, step=0.004)]
    for k in range(3):
        z = z0 + k * 0.0040
        out.append(W.front_decal(f'{prefix}_Stripe_{k}', [(x0 + 0.012, z), (x0 + 0.030, z), (x0 + 0.030, z + 0.0020), (x0 + 0.012, z + 0.0020)],
                                 jacket, M['Pin_Red'], 0.0060, step=0.004))
    return out


def shrink_hands(body, k=0.70):
    """The 'tiny hands' gag: the body's hands scaled toward the wrists (skin weights untouched)."""
    names = {g.index: g.name for g in body.vertex_groups}
    for v in body.data.vertices:
        for side, s in (('Left', 1), ('Right', -1)):
            w = sum(g.weight for g in v.groups if names.get(g.group, '').startswith(P + side + 'Hand'))
            if w > 0.0:
                pivot = Vector((s * 0.645, 0.0, 1.158))
                v.co = pivot + (v.co - pivot) * (1.0 - (1.0 - k) * min(1.0, w))
    body.data.update()


def tramduro(body, face, M, skin):
    """President Tramduro: an unmistakable cartoon caricature (no name, no real flag): orange tan with pale goggle rings
    round the eyes, the golden combed swoop, a pouty squint, a soft double chin, comically tiny hands, a navy suit
    stretched over a big belly, a white shirt and an extra-long red tie hanging below the belt, a flag pin."""
    pre = 'TRAMDURO'
    shrink_hands(body)
    src = C.weight_source([body])
    jacket, out = T._suit(pre, M, src, 'Suit', None, 'Button')
    jsrc = C.weight_source([jacket])
    knot = [(-0.017, 1.258), (0.017, 1.258), (0.012, 1.230), (-0.012, 1.230)]
    blade = [(-0.011, 1.234), (0.011, 1.234), (0.030, 0.840), (0.0, 0.800), (-0.030, 0.840)]
    tie = [W.front_decal(pre + '_TieKnot', knot, jacket, M['Tie'], 0.0065, step=0.006),
           W.front_decal(pre + '_TieBlade', blade, jacket, M['Tie'], 0.0058, thickness=0.003, step=0.010)]
    out += [_t(o, jsrc) for o in tie + flag_pin(pre + '_Pin', jacket, M)]
    out.append(T._trousers(pre, M, 'Suit', src))
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += T._dress_shoes(pre, M)
    out += president_hair(pre + '_Hair', M)

    def tan(head):
        rings = []
        for s in (1, -1):
            cx, cz = s * B.EYE_C[0], B.EYE_C[2]
            pts = [(cx + 0.060 * math.cos(a), cz - 0.004 + 0.070 * math.sin(a)) for a in [2 * math.pi * i / 24 for i in range(24)]]
            rings.append(C.rigid(G.decal(f'{pre}_Tan_{s}', pts, W.FRONT(), [head], 0.0014, M['Tan'], step=0.006), 'Head'))
        return rings
    out += T._face(skin, tan)
    chin = G.ellipsoid(pre + '_DoubleChin', (0.0, -0.104, 1.322), (0.092, 0.046, 0.036), M['Chin'], seg=16, rings=8)
    C.set_weights(chin, [{P + 'Head': 0.7, P + 'Neck': 0.3} for _ in chin.data.vertices])
    out.append(chin)
    return out


BUILDERS = {'OLD_POPKING': popking, 'VIP_BEASTMAN': beastman, 'VIP_BLINDFOLD': blindfold_mage, 'VIP_SPEEDSTER': speedster,
            'TRAMDURO': tramduro}
