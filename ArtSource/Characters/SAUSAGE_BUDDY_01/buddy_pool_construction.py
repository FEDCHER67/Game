"""District pool 'Интернациональная стройка' (TASK-000508, replaces the 'Переход' pool): four migrant builders, each
made as recognisable as possible through clothing, headwear, moustaches, props and build (Vadim):
- CONSTR_INDIAN (v06, TASK-000535: traditional and funny, not like the Uzbek; v07 coloured as a mix of Bollywood and
  the building site): a hard-hat-yellow head-cloth wrapped like a turban with hot-pink wraps, a hi-vis orange
  half-sleeve shirt with a reflective chest band untucked over a magenta lungi with gold checks folded up to the knees,
  a turquoise checked gamcha over the shoulder, gold-strap flip-flops, a thick moustache, an intense stare, a phone in
  the right hand (v06: white shirt, maroon lungi; v04-v05: the 'shh' meme cricket jersey and the hard hat; v02
  "Bollywood on the building site"; v01 the brick pan);
- CONSTR_UZBEK: stocky, navy work suit with orange inserts and a reflective band, black cap, stubble;
- CONSTR_MEXICAN: big drooping moustache, straw sombrero, striped serape across the chest, open work shirt over a
  hairy chest, jeans with a rodeo buckle, pointed boots;
- CONSTR_AFROAMERICAN: very dark skin, massive (and taller in the game: game_scale 1.05 since v03), plain work clothes, nothing
  fashionable (Vadim): white vest top, open orange hi-vis vest, brown double-knee work pants, tool belt with a hammer,
  wheat work boots; black durag with tails under a white hard hat, a diamond stud, a basketball in a net bag (v05:
  nothing on the neck - the gold chain and the dollar medallion went, Vadim);
- CONSTR_ARAB (TASK-000513): red-and-white keffiyeh with a black agal, big black beard, a white thobe (v03: the hi-vis
  vest taken off), white socks in sandals, gold watch, a shawarma in the right hand.
Faces keep the common Sausage Buddy style (skin, nose, brow colours only); no caricature of facial features.
Props in the hands (phone, basketball, shawarma) are dropped at the slightest danger like the other hand_props types.
Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS. No bpy calls at import time."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Интернациональная стройка'
GOLD = ((214, 174, 76), 0.28, 'metal')
METAL = 'metal'

TYPES = {
    'CONSTR_INDIAN': dict(
        label='Индус', group=GROUP, body=dict(thin=0.6), face=dict(Surprised=0.35, Worried=0.35),
        look=dict(skin=(146, 92, 58), nose=(134, 80, 50), brow=(22, 18, 16), rim=(98, 58, 38), mouth=(66, 28, 24)),
        slots={'Shirt': ((86, 150, 214), 0.75), 'Shirt_Button': ((232, 186, 70), 0.3, METAL), 'Pocket': ((66, 124, 186), 0.75),   # v08: not orange (Vadim, TASK-000876)
               'Reflect': ((206, 210, 216), 0.25),
               'Lungi': ((196, 32, 112), 0.6), 'Lungi_Check': ((242, 192, 52), 0.5), 'Lungi_Line': ((22, 168, 180), 0.5),
               'Turban': ((250, 204, 30), 0.6), 'Turban_Fold': ((228, 46, 136), 0.5),
               'Gamcha': ((22, 168, 180), 0.8), 'Gamcha_Check': ((246, 214, 90), 0.8),
               'Cement': ((168, 164, 156), 1.0), 'Sole_Dirt': ((92, 70, 52), 0.9), 'Thong': ((232, 186, 70), 0.3, METAL),
               'Hair': ((18, 16, 18), 0.25), 'Mustache': ((22, 20, 22), 0.6), 'Phone': ((24, 24, 28), 0.35),
               'Screen': ((30, 40, 60), 0.1)},
        colourways=[{'Shirt': (206, 226, 40), 'Pocket': (160, 180, 30), 'Turban': (246, 112, 26), 'Turban_Fold': (22, 168, 180),
                     'Lungi': (14, 130, 96), 'Lungi_Line': (228, 46, 136), 'Gamcha': (196, 32, 112)},
                    {'Shirt': (250, 190, 40), 'Pocket': (214, 150, 20), 'Turban': (246, 112, 26), 'Turban_Fold': (206, 210, 216),
                     'Lungi': (96, 44, 156), 'Lungi_Line': (246, 112, 26), 'Gamcha': (214, 36, 44), 'Gamcha_Check': (246, 246, 240)}]),
    'CONSTR_UZBEK': dict(
        label='Узбек', group=GROUP, body=dict(belly=0.5, muscle=0.6), arm_down=68.0, face=dict(Happy=0.45),
        look=dict(skin=(172, 112, 72), nose=(160, 96, 60), brow=(26, 22, 20), rim=(110, 70, 46)),
        slots={'Jacket': ((40, 54, 92), 0.85), 'Insert': ((240, 120, 30), 0.8), 'Reflect': ((206, 210, 216), 0.25),
               'Zip': ((196, 198, 204), 0.3, METAL), 'Trousers': ((40, 54, 92), 0.88), 'Knee': ((240, 120, 30), 0.8),
               'Dust': ((176, 166, 146), 1.0), 'Boots': ((36, 34, 32), 0.45), 'Boots_Sole': ((24, 24, 24), 0.6),
               'Boot_Lace': ((70, 64, 56), 0.7), 'Cap': ((28, 28, 32), 0.85), 'Cap_Peak': ((28, 28, 32), 0.85),
               'Hair': ((24, 22, 20), 0.85), 'Mustache': ((24, 22, 20), 0.9), 'Stubble': ((40, 34, 30), 0.95)},
        colourways=[{'Jacket': (64, 68, 74), 'Trousers': (64, 68, 74), 'Insert': (250, 200, 40), 'Knee': (250, 200, 40),
                     'Cap': (230, 228, 222), 'Cap_Peak': (64, 68, 74)},
                    {'Jacket': (52, 74, 52), 'Trousers': (52, 74, 52), 'Insert': (230, 70, 50), 'Knee': (230, 70, 50),
                     'Cap': (40, 52, 96), 'Cap_Peak': (40, 52, 96)}]),
    'CONSTR_MEXICAN': dict(
        label='Мексиканец', group=GROUP, body=dict(belly=0.6), arm_down=70.0, face=dict(Happy=0.5),
        look=dict(skin=(160, 100, 62), nose=(150, 88, 54), brow=(30, 24, 20), rim=(104, 64, 42)),
        slots={'Shirt': ((238, 228, 204), 0.85), 'Shirt_Roll': ((222, 210, 184), 0.85), 'ChestHair': ((34, 26, 22), 0.95),
               'Serape': ((196, 40, 52), 0.9), 'Serape_Y': ((250, 196, 40), 0.9), 'Serape_G': ((40, 140, 90), 0.9),
               'Serape_B': ((40, 70, 150), 0.9), 'Serape_W': ((246, 240, 226), 0.9),
               'Jeans': ((62, 88, 136), 0.9), 'Belt': ((96, 56, 30), 0.5), 'Buckle': GOLD,
               'Boots': ((120, 70, 36), 0.45), 'Boots_Sole': ((60, 36, 22), 0.6),
               'Hat': ((224, 190, 116), 0.9), 'HatBand': ((186, 40, 50), 0.8), 'HatDeco': ((36, 124, 80), 0.8),
               'Hair': ((26, 22, 20), 0.8), 'Mustache': ((26, 22, 20), 0.9)},
        colourways=[{'Shirt': (150, 180, 210), 'Shirt_Roll': (132, 162, 194), 'Serape': (40, 70, 150), 'Serape_B': (196, 40, 52),
                     'Jeans': (52, 54, 62), 'Hat': (236, 220, 180)},
                    {'Shirt': (246, 246, 242), 'Shirt_Roll': (230, 230, 226), 'Serape': (40, 140, 90), 'Serape_G': (196, 40, 52),
                     'Jeans': (110, 80, 56), 'Boots': (40, 30, 26), 'HatBand': (30, 30, 34)}]),
    'CONSTR_AFROAMERICAN': dict(
        label='Афроамериканец', group=GROUP, hand_props=True, body=dict(muscle=1.5), arm_down=64.0, face=dict(Happy=0.6),
        game_scale=1.05,                                 # v03 (TASK-000516): x1.05, was x1.08
        look=dict(skin=(58, 38, 28), nose=(66, 42, 30), brow=(12, 10, 10), rim=(40, 26, 20), mouth=(30, 12, 10)),
        slots={'Tee': ((240, 238, 232), 0.85), 'Dust': ((176, 166, 146), 1.0),
               'Vest': ((250, 120, 30), 0.6), 'Vest_Trim': ((214, 96, 24), 0.6), 'Reflect': ((210, 214, 220), 0.25),
               'Pants': ((128, 92, 56), 0.9), 'Knee': ((108, 76, 46), 0.9), 'Leather': ((92, 58, 32), 0.55),
               'Buckle': ((196, 196, 202), 0.3, METAL), 'Hammer': ((168, 120, 70), 0.6), 'Hammer_Head': ((150, 154, 162), 0.3, METAL),
               'Boots': ((200, 142, 70), 0.85), 'Boots_Sole': ((74, 54, 36), 0.6), 'Boot_Lace': ((140, 96, 50), 0.7),
               'Hat': ((246, 246, 242), 0.35), 'Durag': ((26, 26, 30), 0.22), 'Earring': ((236, 240, 246), 0.08),
               'Ball': ((226, 110, 40), 0.6), 'Ball_Seam': ((24, 22, 22), 0.6), 'Net': ((236, 236, 230), 0.8)},
        colourways=[{'Tee': (150, 150, 154), 'Vest': (220, 240, 60), 'Vest_Trim': (190, 210, 50), 'Hat': (250, 200, 40),
                     'Pants': (60, 66, 76), 'Knee': (48, 54, 62)},
                    {'Tee': (52, 54, 60), 'Vest': (250, 90, 40), 'Vest_Trim': (214, 72, 30), 'Hat': (40, 90, 170),
                     'Pants': (150, 136, 104), 'Knee': (130, 116, 88), 'Durag': (246, 246, 242)}]),
    'CONSTR_ARAB': dict(
        label='Араб', group=GROUP, hand_props=True, no_ears=True, body=dict(belly=0.4), arm_down=70.0, face=dict(Happy=0.55),
        look=dict(skin=(196, 138, 96), nose=(184, 118, 80), brow=(16, 14, 14), rim=(128, 84, 56)),
        slots={'Keffiyeh': ((246, 244, 238), 0.9), 'Keffiyeh_Check': ((196, 30, 40), 0.9), 'Agal': ((20, 20, 22), 0.6),
               'Thobe': ((246, 246, 242), 0.85), 'Thobe_Cuff': ((232, 232, 226), 0.85), 'Buttons': ((214, 174, 76), 0.3, METAL),
               'Dust': ((176, 166, 146), 1.0), 'Socks': ((246, 246, 242), 0.9), 'Sandal_Strap': ((120, 78, 44), 0.5),
               'Sandal_Sole': ((70, 48, 30), 0.6), 'Beard': ((22, 18, 16), 0.9), 'Mustache': ((22, 18, 16), 0.85), 'Gold': GOLD,
               'WatchFace': ((24, 24, 28), 0.2), 'Lavash': ((226, 192, 136), 0.8), 'Foil': ((206, 208, 214), 0.25, METAL),
               'Meat': ((140, 82, 46), 0.8), 'Greens': ((70, 150, 60), 0.7), 'Tomato': ((210, 50, 40), 0.6), 'Sauce': ((246, 244, 236), 0.4)},
        colourways=[{'Keffiyeh_Check': (20, 20, 22), 'Thobe': (220, 206, 176), 'Thobe_Cuff': (204, 190, 160)},
                    {'Keffiyeh': (226, 214, 180), 'Thobe': (196, 202, 208), 'Thobe_Cuff': (180, 186, 192)}]),
}


# ------------------------------------------------------------------ shared pieces
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _resample(pts, step):
    """Polyline -> points every ~step metres (both ends kept)."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(round((b - a).length / step)))
        out += [a.lerp(b, k / n) for k in range(1, n + 1)]
    return out


def on_surface(targets, raw, off, step=0.018, smooth=2, closed=False):
    """A band's centre line laid on garments: resampled every ~step, each point moved to the nearest surface point + off
    along the outward normal, smoothed (so it bridges dips such as an open shirt front), then pushed out again where
    smoothing sank it. Returns (points, normals)."""
    bvh = G.bvh_of(targets)

    def nearest(p):
        loc, nrm, _, _ = bvh.find_nearest(p)
        return loc, (nrm if nrm.dot(Vector((p.x, p.y, 0.4))) >= 0 else -nrm)
    pts = _resample(list(raw) + ([raw[0]] if closed else []), step)
    if closed:
        pts = pts[:-1]
    ps, ns = [], []
    for p in pts:
        loc, nrm = nearest(p)
        ps.append(loc + nrm * off); ns.append(nrm)
    n = len(ps)
    for _ in range(smooth):
        if closed:
            ps = [(ps[i - 1] + ps[i] * 2 + ps[(i + 1) % n]) / 4 for i in range(n)]
            ns = [(ns[i - 1] + ns[i] * 2 + ns[(i + 1) % n]).normalized() for i in range(n)]
        else:
            ps = [ps[0]] + [(ps[i - 1] + ps[i] * 2 + ps[i + 1]) / 4 for i in range(1, n - 1)] + [ps[-1]]
            ns = [ns[0]] + [(ns[i - 1] + ns[i] * 2 + ns[i + 1]).normalized() for i in range(1, n - 1)] + [ns[-1]]
    for i, p in enumerate(ps):
        loc, nrm = nearest(p)
        if (p - loc).length < off * 0.85 or (p - loc).dot(nrm) < 0:
            ps[i] = loc + nrm * off
    return ps, ns


def ribbon(name, ps, ns, width, mats, pattern, cols=3, thick=0.006, closed=False):
    """Thick flat band along points ps (outward normals ns), `cols` faces across; pattern(i, j) is the material index
    of the faces at segment i, column j (stripes, checks). The thickness is built here, not with a Solidify modifier:
    even-thickness solidify throws spikes off near-degenerate sections."""
    kp, kn = [ps[0]], [ns[0]]
    for p, nrm in zip(ps[1:], ns[1:]):
        if (p - kp[-1]).length > 0.002:
            kp.append(p); kn.append(nrm)
    if closed and (kp[-1] - kp[0]).length <= 0.002:
        kp.pop(); kn.pop()
    ps, ns, n = kp, kn, len(kp)
    vs, fs, idx = [], [], []
    last_side = None
    for i, p in enumerate(ps):
        t = (ps[(i + 1) % n] - ps[i - 1]) if closed else (ps[min(i + 1, n - 1)] - ps[max(i - 1, 0)])
        side = t.cross(ns[i])
        side = last_side if side.length < 1e-7 and last_side is not None else side.normalized()
        last_side = side
        up = side.cross(t).normalized()
        if up.dot(ns[i]) < 0:
            up = -up
        for layer in (-0.5, 0.5):
            for j in range(cols + 1):
                vs.append(p + side * (width * (j / cols - 0.5)) + up * (thick * layer))
    vid = lambda i, layer, j: i * 2 * (cols + 1) + layer * (cols + 1) + j
    for i in range(n if closed else n - 1):
        i2 = (i + 1) % n
        for j in range(cols):
            m = pattern(i, j)
            fs.append((vid(i, 1, j), vid(i, 1, j + 1), vid(i2, 1, j + 1), vid(i2, 1, j))); idx.append(m)
            fs.append((vid(i, 0, j), vid(i2, 0, j), vid(i2, 0, j + 1), vid(i, 0, j + 1))); idx.append(m)
        fs.append((vid(i, 0, 0), vid(i, 1, 0), vid(i2, 1, 0), vid(i2, 0, 0))); idx.append(pattern(i, 0))
        fs.append((vid(i, 1, cols), vid(i, 0, cols), vid(i2, 0, cols), vid(i2, 1, cols))); idx.append(pattern(i, cols - 1))
    if not closed:
        for i in (0, n - 1):
            for j in range(cols):
                fs.append((vid(i, 0, j), vid(i, 0, j + 1), vid(i, 1, j + 1), vid(i, 1, j))); idx.append(pattern(i, j))
    return G.from_data(name, vs, fs, mats[0], True, idx, list(mats[1:]))


def _hard_hat(prefix, M, hat_slot='Hat'):
    import buddy_pool_prom as PR
    return PR.hard_hat(prefix + '_Hat', M[hat_slot])


def _ring_pts(c, r, z, n=32):
    return [Vector((c.x + r * math.sin(2 * math.pi * k / n), c.y - r * math.cos(2 * math.pi * k / n), z)) for k in range(n + 1)]


# ------------------------------------------------------------------ CONSTR_INDIAN (v04: Vadim's "shh" meme)
LEGS_KNEE = [(.70, .088), (.60, .086), (.50, .082), (.455, .080)]
KNEE_CUFF = [(.444, .089), (.502, .089), (.506, .082)]                          # trousers rolled up to the knees


def cricket_jersey(prefix, M, src):
    """The India cricket jersey of the meme: royal blue, an orange shoulder yoke, orange sleeves and side panels, a
    blue polo collar (no lettering, Vadim)."""
    rows = W.TEE
    jersey = W.top(prefix + '_Jersey', rows, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Jersey'], M['Jersey_Orange']],
                   row_mat=[1 if r[0] >= 1.17 else 0 for r in rows[:-1]], sleeve_mat=[1] * len(W.SLEEVE_SHORT))
    _t(jersey, src, C.no_head)
    jsrc = C.weight_source([jersey])
    collar = _t(W.collar(prefix + '_Collar', M['Jersey'], open_deg=30, tip=0.024), jsrc, C.no_head)
    deco = [G.decal(f'{prefix}_SidePanel_{s}', [(-0.045, 0.812), (0.045, 0.812), (0.045, 1.085), (-0.045, 1.085)], G.SIDE(s), [jersey], 0.003,
                    M['Jersey_Orange'], step=0.012) for s in (1, -1)]
    deco += [W.front_decal(f'{prefix}_JerseyCement_{k}', W.blob(x, z, r, seed=90 + k, rough=0.55, sx=1.3), jersey, M['Cement'], 0.0045)
             for k, (x, z, r) in enumerate(((-0.130, 0.860, 0.022), (0.150, 0.900, 0.016)))]
    return jersey, [jersey, collar] + [_t(o, jsrc) for o in deco]


def bare_feet(prefix, skin, sole_m, dirt_m=None, thong_m=None):
    """Bare feet: the shoe-shaped foot in skin colour with five toes over the front, on a sole as thick as the sneaker
    sole (the shared clips keep the feet on the floor); dirt_m: cement dust on top; thong_m: a flip-flop V strap."""
    toes = [(-0.021, -0.220, 0.084, (0.0150, 0.0175, 0.0145)), (-0.002, -0.224, 0.078, (0.0095, 0.0120, 0.0100)),
            (0.013, -0.219, 0.073, (0.0090, 0.0110, 0.0095)), (0.026, -0.211, 0.069, (0.0085, 0.0100, 0.0090)),
            (0.037, -0.200, 0.065, (0.0075, 0.0090, 0.0080))]
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Foot_{s}', s, skin, sole_m)
        cx = s * B.LEG_X
        piv = Vector((cx, 0, 0))
        place = lambda q: piv + yaw @ (Vector(q) - piv)
        parts = [up, so]
        for k, (dx, y, z, r) in enumerate(toes):
            parts.append(G.ellipsoid(f'{prefix}_Toe_{s}_{k}', place((cx + s * dx, y, z)), r, skin, rot=yaw, seg=10, rings=6))
        if dirt_m is not None:
            for k, (dx, fw, r) in enumerate(((0.004, 0.070, 0.020), (-0.012, 0.150, 0.016))):
                parts.append(G.decal(f'{prefix}_FootDust_{s}_{k}', W.blob(cx + s * dx, fw, r, seed=120 + k + (s > 0) * 5, rough=0.5),
                                     W.TOP(0.6), [up], 0.0018, dirt_m))
        if thong_m is not None:
            bvh = G.bvh_of([up])
            legs = []
            for end in (math.radians(6), math.radians(174)):
                pts = []
                for k in range(9):
                    u = k / 8
                    a = math.radians(90) + (end - math.radians(90)) * u
                    d = yaw @ Vector((math.cos(a), 0.0, math.sin(a)))
                    axis = place((cx - s * 0.012 * (1 - u), -0.192 + 0.078 * u, 0.050))
                    hit = bvh.ray_cast(axis + d * 0.3, -d, 0.6)
                    pts.append(hit[0] + hit[1] * 0.0045 if hit[0] is not None else axis + d * 0.06)
                legs.append(pts)
            parts.append(G.tube(f'{prefix}_Thong_{s}', list(reversed(legs[0])) + legs[1][1:], 0.0058, thong_m, seg=6))
        wf = C.shoe_weights(s)
        for o in parts:
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += parts
    return out


def hat_pushed_back(prefix, M, tilt=24.0):
    """The yellow hard hat pushed back onto the back of the head (tilted about its back rim), so the quiff shows."""
    hat, _ = _hard_hat(prefix, M)
    piv = Vector((0.0, 0.148, 1.652))
    m = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-tilt), 4, 'X') @ Matrix.Translation(-piv)
    for o in hat:
        o.data.transform(m)
        o.data.update()
    return hat


TURBAN_LOW = W.zprofile([(0, 1.668), (30, 1.662), (55, 1.636), (90, 1.612), (130, 1.600), (180, 1.596)])
LUNGI = [(0.880, .184, .124, -.004), (0.840, .190, .129, -.005), (0.800, .198, .135, -.006), (0.760, .206, .142, -.007),
         (0.720, .213, .148, -.008), (0.680, .219, .153, -.009), (0.640, .224, .157, -.010), (0.600, .228, .160, -.010),
         (0.560, .232, .163, -.010), (0.520, .235, .166, -.010), (0.480, .238, .168, -.010), (0.440, .240, .170, -.010),
         (0.400, .242, .172, -.010), (0.380, .243, .173, -.010), (0.387, .235, .165, -.010)]     # folded up to the knee
SHIRT_LOOSE = [(0.780, .214, .150, -.012), (0.795, .216, .151, -.012), (0.86, .208, .143, -.012), (0.94, .200, .137, -.012)] + \
              [r for r in W.TEE if r[0] >= 1.02]                                               # untucked over the lungi; arm row 6


def wrapped_turban(prefix, M):
    """A saffron cloth wrapped round the head like a turban (the head-cloth of Indian builders): a puffy dome from just
    above the brows, three darker wrap ridges crossing at the front and the tucked-in end hanging at the back."""
    def off(phi, u):
        return 0.018 + 0.060 * G.smoothstep(0.0, 0.60, u) - 0.010 * G.smoothstep(0.75, 1.0, u)
    dome, _ = W.shell(prefix + '_Dome', M['Turban'], TURBAN_LOW, None, off=off, thick=0.012, seg=40, rows=12)
    out = [C.rigid(dome, 'Head')]
    for k, (u0, a) in enumerate(((0.16, 0.08), (0.34, -0.12), (0.50, 0.12), (0.66, -0.10))):
        ring = []
        for q in range(49):
            phi = -math.pi + 2 * math.pi * q / 48
            u = u0 + a * math.cos(phi)
            lo = TURBAN_LOW(phi)
            ring.append(W.head_at(phi, lo + (W.H_POLE - lo) * u, off(phi, u) + 0.004)[0])
        out.append(C.rigid(G.tube(f'{prefix}_Wrap_{k}', ring, 0.0135, M['Turban_Fold'], seg=8, caps=False), 'Head'))
    top = W.head_at(math.pi, TURBAN_LOW(math.pi) + 0.020, off(math.pi, 0.1) + 0.004)[0]
    path = [top, top + Vector((0.006, 0.010, -0.050)), top + Vector((0.004, 0.016, -0.110)), top + Vector((0.0, 0.020, -0.160))]
    tail = C.strap(prefix + '_End', path, M['Turban'], width=0.060, thick=0.005, normal_fn=lambda p: Vector((0, 1, 0)))
    C.set_weights(tail, [{P + 'Head': G.smoothstep(1.36, 1.50, q.z), P + 'Neck': 1 - G.smoothstep(1.36, 1.50, q.z)}
                         for q in (tail.matrix_world @ v.co for v in tail.data.vertices)])
    return out + [tail]


def lungi(prefix, M, seg=40):
    """The lungi: a madras-check cloth wrapped round the hips and folded up to the knees (W.skirt geometry and weights;
    the checks are face materials: the ground, the check stripes and their crossings)."""
    sk = W.skirt(prefix + '_Lungi', M['Lungi'], rows=LUNGI, seg=seg)
    me = sk.data
    me.materials.append(M['Lungi_Check'])
    me.materials.append(M['Lungi_Line'])
    for f, poly in enumerate(me.polygons):
        row, col = divmod(f, seg)
        a, b = col % 4 == 0, row % 2 == 1
        poly.material_index = 2 if (a and b) else 1 if (a or b) else 0
    me.update()
    return sk


def gamcha(prefix, M, targets):
    """The checked gamcha towel thrown over the left shoulder: down the chest in front, down the back behind."""
    raw = [Vector((0.085, -0.170, 0.980)), Vector((0.100, -0.168, 1.100)), Vector((0.128, -0.120, 1.200)), Vector((0.150, -0.020, 1.244)),
           Vector((0.140, 0.080, 1.214)), Vector((0.112, 0.150, 1.120)), Vector((0.096, 0.160, 1.000))]
    ps, ns = on_surface(targets, raw, 0.010, step=0.022, smooth=2)
    return ribbon(prefix + '_Gamcha', ps, ns, 0.100, [M['Gamcha'], M['Gamcha_Check']], lambda i, j: (i // 2 + j) % 2, cols=4, thick=0.007)


def indian(body, face, M, skin):
    """v06 (TASK-000535, Vadim: more Indian - traditional and funny but not absurd, and not like the Uzbek migrant):
    a head-cloth wrapped like a turban (the way Indian builders wrap their heads), a half-sleeve shirt with a chest
    pocket untucked over a check lungi folded up to the knees (bare shins), a checked gamcha towel over the left
    shoulder, flip-flops with cement dust; the thick moustache, the intense wide-eyed stare and the phone in the right
    hand stay (dropped at the slightest danger). v07 (Vadim: the colours a mix of Bollywood and the building site):
    a hard-hat-yellow turban with hot-pink wraps, a hi-vis orange shirt with a reflective chest band and gold buttons,
    a magenta lungi with gold checks and turquoise crossings, a turquoise gamcha with gold checks, gold flip-flop
    straps (v06: white shirt, maroon lungi with mustard checks, red gamcha).
    v04-v05 were the 'shh' meme (India cricket jersey, the hard hat pushed back, rolled-up khaki trousers), v02
    'Bollywood on the building site', v01 the brick pan."""
    import buddy_pool_oldtown2 as O2
    import buddy_pool_bad as BD
    pre = 'CONSTR_INDIAN'
    src = C.weight_source([body])
    shirt = _t(W.top(pre + '_Shirt', SHIRT_LOOSE, 6, W.SLEEVE_SHORT, (.795, .208, .145, -.012), [M['Shirt']]), src, C.no_head)
    ssrc = C.weight_source([shirt])
    collar = _t(W.collar(pre + '_Collar', M['Shirt'], open_deg=28, tip=0.026), ssrc, C.no_head)
    deco = [W.front_decal(pre + '_Placket', BD.stripe_outline(-0.008, 0.008, 0.790, 1.235), shirt, M['Pocket'], 0.0026, step=0.012),
            W.front_decal(pre + '_Pocket', [(0.058, 1.060), (0.128, 1.060), (0.128, 1.132), (0.058, 1.132)], shirt, M['Pocket'], 0.0034,
                          thickness=0.003, step=0.012)]
    deco += W.buttons(pre + '_Button', shirt, M['Shirt_Button'], [(0.0, z) for z in (1.190, 1.110, 1.030, 0.950, 0.870)], r=0.0075,
                      offset=0.0046)
    band = BD.stripe_outline(-0.200, 0.200, 0.982, 1.012)       # hi-vis: a reflective band round the chest (no flat chord)
    deco += [W.front_decal(pre + '_BandF', band, shirt, M['Reflect'], 0.0032, step=0.012),
             G.decal(pre + '_BandB', band, W.BACK(), [shirt], 0.0032, M['Reflect'], step=0.012)]
    deco += [W.front_decal(f'{pre}_ShirtCement_{k}', W.blob(x, z, r, seed=90 + k, rough=0.55, sx=1.3), shirt, M['Cement'], 0.0045)
             for k, (x, z, r) in enumerate(((-0.140, 0.860, 0.020), (0.150, 0.900, 0.014)))]
    out = [shirt, collar] + [_t(o, ssrc) for o in deco]
    out.append(lungi(pre, M))
    out.append(_t(gamcha(pre, M, [shirt, collar]), ssrc, C.no_head))
    out += bare_feet(pre, skin, M['Sole_Dirt'], dirt_m=M['Cement'], thong_m=M['Thong'])
    out += wrapped_turban(pre + '_Turban', M)
    out.append(W.hair(pre + '_Hair', M['Hair'], 'slick', upper=lambda phi: TURBAN_LOW(phi) + 0.012))
    out += handlebar_moustache(pre + '_Mustache', M['Mustache'])              # v09: curled handlebar (TASK-000896)
    # v08 (Vadim, TASK-000877): no phone in the hand any more
    return out


# ------------------------------------------------------------------ CONSTR_UZBEK
def uzbek(body, face, M, skin):
    import buddy_pool_oldtown2 as O2
    pre = 'CONSTR_UZBEK'
    src = C.weight_source([body])
    jacket = T._jacket(pre, M, 'Jacket', src, cuff_slot='Insert')
    jsrc = C.weight_source([jacket])
    collar = W.collar(pre + '_Collar', M['Jacket'], z0=1.258, r0=(0.157, 0.153), z1=1.288, r1=(0.164, 0.159), z2=1.246,
                      r2=(0.194, 0.187), open_deg=20, tip=0.028, thick=0.007)
    deco = [W.front_decal(pre + '_YokeF', [(-0.196, 1.150), (0.196, 1.150), (0.180, 1.226), (-0.180, 1.226)], jacket, M['Insert'], 0.003,
                          step=0.014),
            G.decal(pre + '_YokeB', [(-0.196, 1.140), (0.196, 1.140), (0.180, 1.226), (-0.180, 1.226)], W.BACK(), [jacket], 0.003,
                    M['Insert'], step=0.014)]
    band = [(-0.200, 0.985), (0.200, 0.985), (0.200, 1.015), (-0.200, 1.015)]
    deco += [W.front_decal(pre + '_BandF', band, jacket, M['Reflect'], 0.0032, step=0.012),
             G.decal(pre + '_BandB', band, W.BACK(), [jacket], 0.0032, M['Reflect'], step=0.012)]
    for s in (1, -1):
        deco.append(W.front_decal(f'{pre}_Flap_{s}', [(s * 0.050, 1.068), (s * 0.140, 1.068), (s * 0.140, 1.104), (s * 0.050, 1.104)][::s],
                                  jacket, M['Insert'], 0.0036, thickness=0.003))
    deco.append(W.front_decal(pre + '_Zip', [(-0.006, 0.705), (0.006, 0.705), (0.006, 1.250), (-0.006, 1.250)], jacket, M['Zip'], 0.0045,
                              step=0.008))
    out = [jacket, _t(collar, jsrc, C.no_head)] + [_t(o, jsrc) for o in deco]
    pants = T._trousers(pre, M, 'Trousers', src)
    knees = [W.front_decal(f'{pre}_Knee_{s}', [(s * 0.058, 0.400), (s * 0.142, 0.400), (s * 0.142, 0.505), (s * 0.058, 0.505)][::s],
                           pants, M['Knee'], 0.003, thickness=0.004, step=0.012) for s in (1, -1)]
    knees += [W.front_decal(f'{pre}_Dust_{k}', W.blob(x, z, r, seed=60 + k, rough=0.5, sx=1.2), pants, M['Dust'], 0.0034)
              for k, (x, z, r) in enumerate(((0.110, 0.300, 0.026), (-0.080, 0.620, 0.024)))]
    out += [pants] + T._decal_t(knees, pants)
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole'], M['Boot_Lace'], high=True)
    cap, base = O2.baseball_cap(pre + '_Cap', M['Cap'], M['Cap_Peak'])
    out += cap
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=lambda phi: base(phi) + 0.010))
    out += droopy_moustache_goatee(pre + '_Mustache', M['Mustache'])          # v05: thin droopy + chin beard (TASK-000896)
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head, dots=150, seed=23))
    return out


# ------------------------------------------------------------------ CONSTR_MEXICAN
SOMBRERO_BASE = W.zprofile([(0, 1.680), (90, 1.666), (180, 1.652)])


def sombrero(prefix, M, seg=48):
    """Straw sombrero: tall rounded crown with a red band, wide brim that dips a little and curls up at the edge,
    a rolled rim and a ring of green and red embroidery on the brim."""
    rows = [('fit', SOMBRERO_BASE, 0.006), (1.716, 0.150, 0.146, 0.0, 0.0), (1.744, 0.146, 0.142, 0.0, 0.0),
            (1.800, 0.126, 0.123, 0.0, 0.0), (1.856, 0.106, 0.104, 0.0, 0.0), (1.900, 0.088, 0.086, 0.0, 0.0),
            (1.932, 0.064, 0.062, 0.0, 0.0), (1.948, 0.032, 0.031, 0.0, 0.0)]
    crown = W.ring_loft(prefix + '_Crown', rows, [M['Hat'], M['HatBand']], row_mat=[1, 1, 0, 0, 0, 0, 0], seg=32)
    prof = [(0.0, 0.0), (0.050, -0.007), (0.110, -0.012), (0.160, -0.008), (0.195, 0.010), (0.214, 0.030), (0.222, 0.048)]
    vs, fs, rings = [], [], [[] for _ in prof]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        p0, _ = W.head_at(phi, SOMBRERO_BASE(phi), 0.006)
        outv = Vector((math.sin(phi), -math.cos(phi), 0))
        for k, (w, dz) in enumerate(prof):
            rings[k].append(len(vs)); vs.append(p0 + outv * w + Vector((0, 0, dz)))
    for a_, b_ in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a_[j], a_[(j + 1) % seg], b_[(j + 1) % seg], b_[j]))
    brim = G.from_data(prefix + '_Brim', vs, fs, M['Hat'], True, fix_normals=False)
    G.solidify(brim, 0.007, offset=0.0)
    edge = [vs[i] + Vector((0, 0, 0.004)) for i in rings[-1]]
    rim = G.tube(prefix + '_Rim', edge + [edge[0]], 0.0085, M['Hat'], seg=8, caps=False)
    deco = []
    for k in range(18):
        phi = 2 * math.pi * (k + 0.5) / 18 - math.pi
        p0, _ = W.head_at(phi, SOMBRERO_BASE(phi), 0.006)
        R = Vector((p0.x, p0.y, 0)).length + 0.118
        fx, fy = math.sin(phi), math.cos(phi)            # outline space: (x, forward = -y)
        if k % 2 == 0:
            r = 0.018
            pts = [(R * fx + r * c, R * fy + r * s_) for c, s_ in ((fx, fy), (fy, -fx), (-fx, -fy), (-fy, fx))]
            m = M['HatDeco']
        else:
            pts = [(R * fx + 0.009 * math.cos(a), R * fy + 0.009 * math.sin(a)) for a in [2 * math.pi * q / 8 for q in range(8)]]
            m = M['HatBand']
        deco.append(G.decal(f'{prefix}_Deco_{k}', pts, W.TOP(), [brim], 0.0025, m, step=0.008))
    return [C.rigid(o, 'Head') for o in [crown, brim, rim] + deco]


SERAPE_SEQ = [0, 0, 0, 4, 1, 4, 0, 0, 0, 2, 3, 2]          # red body, white-yellow and green-blue stripe groups


def serape(prefix, M, targets, src):
    """Striped blanket rolled into a band and slung from the left shoulder across the chest to the right hip and back."""
    raw = [(0.150, 0.010, 1.268), (0.130, -0.110, 1.215), (0.070, -0.170, 1.130), (-0.010, -0.185, 1.050), (-0.090, -0.175, 0.975),
           (-0.165, -0.130, 0.915), (-0.200, -0.070, 0.892), (-0.214, 0.000, 0.888), (-0.200, 0.070, 0.900), (-0.170, 0.120, 0.925),
           (-0.080, 0.160, 1.010), (0.030, 0.165, 1.100), (0.110, 0.130, 1.190), (0.150, 0.070, 1.255)]
    ps, ns = on_surface(targets, raw, 0.024, step=0.020, smooth=3, closed=True)
    mats = [M['Serape'], M['Serape_Y'], M['Serape_G'], M['Serape_B'], M['Serape_W']]
    ob = ribbon(prefix + '_Serape', ps, ns, 0.096, mats, lambda i, j: SERAPE_SEQ[i % len(SERAPE_SEQ)], cols=3, thick=0.014, closed=True)
    return _t(ob, src, C.no_head)


def mexican(body, face, M, skin):
    import buddy_pool_transit as TR
    import buddy_pool_transit2 as TR2
    pre = 'CONSTR_MEXICAN'
    src = C.weight_source([body])
    gap = lambda z: TR.v_gap(z, z0=1.060, top=0.082)
    shirt, out = TR.open_shirt(pre, M, src, gap=gap)
    bsrc = C.weight_source([body])
    out += [_t(o, bsrc) for o in TR.chest_hair(pre + '_ChestHair', M['ChestHair'], body, gap=gap, n=40, seed=17)]
    jeans = T._trousers(pre, M, 'Jeans', src)
    belt = W.belt(pre, M['Belt'], M['Buckle'])
    bpy.data.objects.remove(belt.pop())
    belt.append(G.ellipsoid(pre + '_Buckle', (0.0, -0.002 - 0.130 - 0.011, 0.872), (0.040, 0.009, 0.028), M['Buckle'], seg=16, rings=8))
    out += [jeans] + [_t(o, src) for o in belt]
    out.append(serape(pre, M, [shirt, jeans], C.weight_source([shirt, jeans])))
    out += TR2._shoe_pair(pre + '_Boot', M['Boots'], M['Boots_Sole'], point=0.9)
    out += sombrero(pre + '_Sombrero', M)
    out.append(W.hair(pre + '_Hair', M['Hair'], 'buzz', upper=lambda phi: SOMBRERO_BASE(phi) + 0.010))
    out += horseshoe_moustache(pre + '_Mustache', M['Mustache'])              # v05: bushy horseshoe (TASK-000896)
    return out


# ------------------------------------------------------------------ CONSTR_AFROAMERICAN
def _vest_gap(z):
    return 0.072 + 0.050 * G.smoothstep(1.00, 1.25, z)


VEST_Z_TOP = 1.150


def _vest_rows(grow=0.014):
    return [(z, rx + grow, ry + grow, dy) for z, rx, ry, dy in [r for r in W.TEE if r[0] <= 1.10] + [W.lerp_row(W.TEE, VEST_Z_TOP)]]


def open_vest(prefix, M, body, src, grow=0.014, strap_targets=None):
    """Hi-vis vest worn open over the white vest top, cut like it: deep armholes and wide straps over the bare shoulders
    (a sleeveless yoke would float over them); two reflective bands round the body, binding along the opening."""
    def cut(p):
        a = math.degrees(math.atan2(abs(p.y + 0.004), abs(p.x) * 1.45))     # 0 at the side, 90 front / back
        return (p.z > 1.03 and a < 52) or (p.y < 0 and abs(p.x) < _vest_gap(p.z))
    rows = _vest_rows(grow)
    vest = W.top(prefix + '_Vest', rows, 0, None, (.806, .184 + grow, .124 + grow, -.004), [M['Vest']], cut=cut, armhole=False)
    G.solidify(vest, 0.004, offset=1.0)
    _t(vest, src, C.no_head)
    bvh = G.bvh_of(strap_targets or [body])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    straps = []
    for s in (1, -1):
        raw = [(0.112, -0.156, 1.100), (0.134, -0.118, 1.160), (0.154, -0.052, 1.200), (0.160, 0.008, 1.210),
               (0.152, 0.064, 1.198), (0.132, 0.110, 1.158), (0.112, 0.146, 1.100)]
        pts = [on(Vector((s * x, y, z)), 0.009)[0] for x, y, z in raw]
        st = C.strap(f'{prefix}_VestStrap_{s}', pts, M['Vest'], width=0.072, thick=0.006, normal_fn=lambda q: on(q, 0.0)[1])
        straps.append(_t(st, src, C.no_head))
    vsrc = C.weight_source([vest])
    parts = []
    for k, z in enumerate((0.900, 0.985)):
        for s in (1, -1):
            x0 = _vest_gap(z) + 0.014
            pts = [(s * x0, z - 0.014), (s * 0.27, z - 0.014), (s * 0.27, z + 0.014), (s * x0, z + 0.014)][::s]
            parts.append(W.front_decal(f'{prefix}_BandF_{k}_{s}', pts, vest, M['Reflect'], 0.0030, step=0.012))
        pts = [(-0.27, z - 0.014), (0.27, z - 0.014), (0.27, z + 0.014), (-0.27, z + 0.014)]
        parts.append(G.decal(f'{prefix}_BandB_{k}', pts, W.BACK(), [vest], 0.0030, M['Reflect'], step=0.012))
    for s in (1, -1):
        pts = []
        for z in (0.800, 0.84, 0.90, 0.96, 1.02, 1.08, 1.140):
            r = W.lerp_row(rows, z)
            x = _vest_gap(z) + 0.003
            a = math.asin(max(-1.0, min(1.0, x / r[1])))
            pts.append(Vector((s * x, r[3] - r[2] * math.cos(a) - 0.004, z)))
        parts.append(G.tube(f'{prefix}_Binding_{s}', pts, 0.0065, M['Vest_Trim'], seg=8))
    return vest, [vest] + straps + [_t(o, vsrc, C.no_head) for o in parts]


def durag(prefix, M, base):
    """Durag under the hard hat: shiny cloth round the head from a straight forehead edge up into the hat, a knot at
    the back and the two long tails hanging down over the neck."""
    lower = W.zprofile([(0, 1.652), (40, 1.640), (75, 1.600), (110, 1.560), (180, 1.530)])
    band, _ = W.shell(prefix + '_Band', M['Durag'], lower, lambda phi: base(phi) + 0.012, off=0.0035, thick=0.004, seg=32, rows=3)
    out = [C.rigid(band, 'Head'),
           C.rigid(G.ellipsoid(prefix + '_Knot', (0.0, 0.148, 1.566), (0.026, 0.013, 0.016), M['Durag'], seg=12, rings=6), 'Head')]
    for s in (1, -1):
        path = [Vector((s * 0.014, 0.146, 1.560)), Vector((s * 0.020, 0.152, 1.480)), Vector((s * 0.026, 0.162, 1.400)),
                Vector((s * 0.032, 0.176, 1.330)), Vector((s * 0.036, 0.188, 1.270))]
        tail = C.strap(f'{prefix}_Tail_{s}', path, M['Durag'], width=0.046, thick=0.004, normal_fn=lambda p: Vector((0, 1, 0)))
        C.set_weights(tail, [{P + 'Head': G.smoothstep(1.30, 1.46, q.z), P + 'Neck': 1 - G.smoothstep(1.30, 1.46, q.z)}
                             for q in (tail.matrix_world @ v.co for v in tail.data.vertices)])
        out.append(tail)
    return out


def gold_chain(name, material, targets, drop=0.205, rad=0.178, off=0.013, link=0.0078, seg=64):
    """Thick gold chain round the neck, over the vest at the shoulders and down onto the chest in the open front;
    laid with on_surface (smoothed), so it does not zigzag where it crosses the vest edge. Returns (tube, lowest point)."""
    raw = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        f = ((1 + math.cos(a)) / 2) ** 3
        raw.append(Vector((rad * math.sin(a), -rad * math.cos(a), 1.262 - drop * f)))
    ps, _ = on_surface(targets, raw, off, step=0.012, smooth=3, closed=True)
    low = min(ps, key=lambda p: p.z)
    return G.tube(name, ps + [ps[0]], lambda i, n: link + 0.0034 * (i % 2), material, seg=8), low


def dollar_medallion(prefix, M, low):
    """Big gold medallion with a raised dollar sign, hanging under the lowest point of the chain."""
    c = low + Vector((0.0, -0.012, -0.046))
    f = c + Vector((0.0, -0.011, 0.0))
    s_pts = [(0.015, 0.016), (0.006, 0.021), (-0.008, 0.019), (-0.014, 0.010), (-0.006, 0.002), (0.008, -0.004),
             (0.014, -0.013), (0.006, -0.021), (-0.010, -0.019)]
    return [G.ellipsoid(prefix + '_Medal', c, (0.042, 0.010, 0.042), M['Gold'], seg=20, rings=8),
            G.tube(prefix + '_Dollar', [f + Vector((x, 0.0, z)) for x, z in s_pts], 0.0042, M['Medal_Sign'], seg=6),
            G.tube(prefix + '_DollarBar', [f + Vector((0.0, 0.0, 0.030)), f + Vector((0.0, 0.0, -0.030))], 0.0034, M['Medal_Sign'], seg=6)]


def tool_belt(prefix, M):
    """Leather tool belt over the vest: two pouches on the hips and a hammer hanging from a loop on the left side."""
    import buddy_pool_bad as BD
    out = W.belt(prefix, M['Leather'], M['Buckle'], z=0.872, rx=0.232, ry=0.172, dy=-0.006, width=0.046)
    for s in (1, -1):
        rot = Matrix.Rotation(math.radians(-s * 24), 3, 'Z')
        out.append(BD.rbox(f'{prefix}_Pouch_{s}', Vector((s * 0.246, -0.070, 0.815)), (0.016, 0.050, 0.056), M['Leather'], bevel=0.010, rot=rot))
    out.append(G.tube(prefix + '_HammerHandle', [(0.246, 0.040, 0.862), (0.250, 0.046, 0.690)], lambda i, n: (0.0110, 0.0125)[i],
                      M['Hammer'], seg=8))
    out.append(BD.rbox(prefix + '_HammerHead', Vector((0.246, 0.040, 0.878)), (0.013, 0.050, 0.014), M['Hammer_Head'], bevel=0.004))
    return [C.rigid(o, 'Hips') for o in out]


def basketball(prefix, M, arm_down):
    """Basketball in a string net bag hanging from the right fist; dropped at the slightest danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    fist, _, _ = HM.grip('Right', arm_down)
    R = 0.118
    c = fist + Vector((0.0, 0.0, -0.050 - R))
    parts = [G.ellipsoid(prefix + '_Ball', c, (R, R, R), M['Ball'], seg=20, rings=12)]
    seams = []
    for a0 in (0.0, math.pi / 2):         # two great circles through the poles
        seams.append([c + Vector((math.cos(a0) * math.sin(t), math.sin(a0) * math.sin(t), math.cos(t))) * (R + 0.0015)
                      for t in [2 * math.pi * q / 24 for q in range(25)]])
    for s in (1, -1):                     # the two curved side seams: small circles left and right
        seams.append([c + Vector((s * 0.62, 0.785 * math.cos(t), 0.785 * math.sin(t))) * (R + 0.0015)
                      for t in [2 * math.pi * q / 18 for q in range(19)]])
    for k, ring in enumerate(seams):
        parts.append(G.tube(f'{prefix}_Seam_{k}', ring, 0.0028, M['Ball_Seam'], seg=4, caps=False))
    knot = fist + Vector((0.0, 0.0, -0.030))
    parts.append(G.tube(prefix + '_NetLoop', [knot, fist + Vector((0.0, 0.010, 0.022)), fist + Vector((0.0, -0.010, 0.022)), knot], 0.0030,
                        M['Net'], seg=4))
    for k in range(6):                    # net: strings from the knot over the ball, and two rings round it
        a = 2 * math.pi * k / 6 + 0.3
        pts = [knot] + [c + Vector((math.cos(a) * math.sin(t), math.sin(a) * math.sin(t), math.cos(t))) * (R + 0.006)
                        for t in [math.radians(d) for d in (12, 40, 70, 100, 130, 160)]]
        parts.append(G.tube(f'{prefix}_Net_{k}', pts, 0.0022, M['Net'], seg=4))
    for k, t in enumerate((math.radians(90), math.radians(135))):
        parts.append(G.tube(f'{prefix}_NetRing_{k}', _ring_pts(Vector((c.x, c.y, 0.0)), (R + 0.006) * math.sin(t), c.z + (R + 0.006) * math.cos(t), n=28),
                            0.0022, M['Net'], seg=4, caps=False))
    return HM.hold(parts, 'Right', arm_down)


def afroamerican(body, face, M, skin):
    import buddy_pool_transit2 as TR2
    pre = 'CONSTR_AFROAMERICAN'
    src = C.weight_source([body])
    tank = W.tank_top(pre + '_Tank', M['Tee'], body)          # white vest top, bare massive arms
    for strap in tank[1:]:                                      # the hi-vis vest covers the shoulders: no straps
        bpy.data.objects.remove(strap)
    tee = _t(tank[0], src, C.no_head)
    tsrc = C.weight_source([tee])
    out = [tee] + [_t(W.front_decal(f'{pre}_TeeDust_{k}', W.blob(x, z, r, seed=80 + k, rough=0.5, sx=1.2), tee, M['Dust'], 0.0028), tsrc)
                   for k, (x, z, r) in enumerate(((0.030, 0.930, 0.022), (-0.040, 1.040, 0.016)))]
    vest, parts = open_vest(pre, M, body, src)
    out += parts
    pants = T._trousers(pre, M, 'Pants', src)
    knees = [W.front_decal(f'{pre}_Knee_{s}', [(s * 0.052, 0.360), (s * 0.150, 0.360), (s * 0.150, 0.560), (s * 0.052, 0.560)][::s],
                           pants, M['Knee'], 0.003, thickness=0.003, step=0.012) for s in (1, -1)]
    out += [pants] + T._decal_t(knees, pants)
    out += tool_belt(pre, M)
    out += W.shoes(pre + '_Boot', M['Boots'], M['Boots_Sole'], M['Boot_Lace'], high=True)
    # v05 (TASK-000535, Vadim): nothing on the neck - the gold chain and the dollar medallion are gone
    hat, base = _hard_hat(pre, M)
    out += hat + durag(pre + '_Durag', M, base)
    ex, ey, ez = B.EAR_C
    out.append(C.rigid(G.ellipsoid(pre + '_Stud', (ex + 0.026, ey - 0.004, ez - 0.038), (0.0065, 0.0065, 0.0065), M['Earring'], seg=4, rings=2),
                       'Head'))
    # v02: no goatee - on the very dark skin the black tuft under the mouth read as an open 'o' mouth
    out += basketball(pre, M, TYPES[pre]['arm_down'])
    return out


# ------------------------------------------------------------------ CONSTR_ARAB (TASK-000513)
def keffiyeh(prefix, M, cols=48, rows=16):
    """Red-and-white checked keffiyeh draped over the head: it frames the face and falls over the shoulders and the back
    (flaring out at the bottom); a double black agal cord round the crown. The top follows the head, the bottom the
    upper back (hood_up weights)."""
    lower = W.zprofile([(0, 1.690), (34, 1.684), (52, 1.560), (66, 1.420), (82, 1.300), (180, 1.200)])
    back = lambda phi: (1 - math.cos(phi)) / 2
    off = lambda phi, u: 0.012 + 0.010 * u * back(phi) + 0.050 * (1 - u) ** 2 * (0.4 + 0.6 * back(phi))
    vs, fs, idx, grid = [], [], [], []
    for j in range(cols):
        phi = -math.pi + 2 * math.pi * j / cols
        col = []
        for i in range(rows):                                   # the pole closes the top
            u = i / rows
            h = lower(phi) + (W.H_POLE - lower(phi)) * u
            p, _ = W.head_at(phi, h, off(phi, u))
            col.append(len(vs)); vs.append(p)
        grid.append(col)
    top = len(vs); vs.append(Vector((0, 0, B.HEAD_TOP + off(0.0, 1.0))))
    for j in range(cols):
        a_, b_ = grid[j], grid[(j + 1) % cols]
        for i in range(rows - 1):                               # the lower profile leaves the face open
            fs.append((a_[i], b_[i], b_[i + 1], a_[i + 1])); idx.append((i + j) % 2)
        fs.append((a_[-1], b_[-1], top)); idx.append(0)
    ob = G.from_data(prefix + '_Keffiyeh', vs, fs, M['Keffiyeh'], True, idx, [M['Keffiyeh_Check']], fix_normals=False)
    G.solidify(ob, 0.005, offset=1.0)
    C.set_weights(ob, [{P + 'Head': G.smoothstep(1.27, 1.40, p.z), P + 'Spine2': 1 - G.smoothstep(1.27, 1.40, p.z)}
                       for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
    out = [ob]
    def at(phi, z):
        u = max(0.0, min(1.0, (W.h_of(z) - lower(phi)) / (W.H_POLE - lower(phi))))
        return W.head_at(phi, W.h_of(z), off(phi, u) + 0.014)[0]
    for k, z in enumerate((1.702, 1.724)):
        ring = [at(2 * math.pi * q / 40, z) for q in range(41)]
        out.append(C.rigid(G.tube(f'{prefix}_Agal_{k}', ring, 0.0085, M['Agal'], seg=8, caps=False), 'Head'))
    return out


def shawarma(prefix, M, arm_down):
    """Shawarma held upright in the right fist: lavash roll in silver foil at the bottom, meat, greens and tomato
    sticking out of the top, a drip of white garlic sauce; dropped at the slightest danger (NpcHeldProps)."""
    import buddy_pool_hamlet as HM
    fist, _, _ = HM.grip('Right', arm_down)
    z0 = fist.z - 0.060
    sec = lambda z, r: ((fist.x, fist.y, z0 + z), (1, 0, 0), (0, 1, 0), r, r)
    roll = G.loft(prefix + '_Lavash', [sec(0.000, 0.026), sec(0.010, 0.032), sec(0.170, 0.039), sec(0.200, 0.040)], M['Lavash'], seg=14,
                  cap_start=True, cap_end=False)
    foil = G.loft(prefix + '_Foil', [sec(-0.004, 0.028), sec(0.010, 0.035), sec(0.085, 0.040), sec(0.090, 0.036)], M['Foil'], seg=14,
                  cap_start=True, cap_end=False)
    top = Vector((fist.x, fist.y, z0 + 0.200))
    parts = [roll, foil, G.ellipsoid(prefix + '_Meat', top + Vector((0, 0, 0.004)), (0.034, 0.034, 0.016), M['Meat'], seg=12, rings=6)]
    for k, (dx, dy, slot) in enumerate(((0.016, -0.010, 'Greens'), (-0.014, 0.012, 'Tomato'), (0.004, 0.018, 'Greens'), (-0.016, -0.014, 'Tomato'))):
        parts.append(G.ellipsoid(f'{prefix}_Bit_{k}', top + Vector((dx, dy, 0.016)), (0.011, 0.008, 0.006), M[slot], seg=8, rings=4))
    drip = top + Vector((0.0, -0.038, -0.010))
    parts.append(G.tube(prefix + '_Sauce', [drip, drip + Vector((0.0, -0.002, -0.030))], lambda i, n: (0.006, 0.004)[i], M['Sauce'], seg=8))
    parts.append(G.ellipsoid(prefix + '_SauceDrop', drip + Vector((0.0, -0.002, -0.034)), (0.006, 0.006, 0.008), M['Sauce'], seg=8, rings=5))
    return HM.hold(parts, 'Right', arm_down)


THOBE = [(0.140, .262, .190, -.014), (0.160, .262, .190, -.014), (0.300, .254, .184, -.014), (0.450, .244, .176, -.013),
         (0.600, .232, .166, -.013), (0.740, .218, .156, -.012), (0.860, .206, .146, -.012), (0.940, .200, .140, -.012)] +         [r for r in W.TEE if r[0] >= 1.02]                          # ankle-length robe; arm row 10 (z 1.10)


def arab(body, face, M, skin):
    """The Arab builder (TASK-000513, Vadim: stereotypes to the max; the face and the beard are right, the clothes more
    traditional and funnier): a red-and-white keffiyeh with a black agal, a big bushy black beard and moustache; a white
    ankle-length thobe with a stand collar and a buttoned placket, its hem grey with cement dust, white socks in leather
    sandals, a gold watch, and a shawarma in the right hand. v02 wore an orange hi-vis vest over the thobe; v03 without it
    (Vadim)."""
    import buddy_pool_transit as TR
    import buddy_pool_bad as BD
    import buddy_pool_bad2 as BD2
    import buddy_pool_bad3 as BD3
    import buddy_pool_oldtown2 as O2
    pre = 'CONSTR_ARAB'
    src = C.weight_source([body])
    thobe = W.top(pre + '_Thobe', THOBE, 10, W.SLEEVE_LONG, (.160, .252, .180, -.014), [M['Thobe'], M['Thobe_Cuff']],
                  row_mat=[1] + [0] * (len(THOBE) - 2), sleeve_mat=[0] * 7 + [1] * 3, hem_mat=1)
    _t(thobe, src, BD3._coat_weights)
    tsrc = C.weight_source([thobe])
    collar = _t(BD._stand_collar(pre + '_Collar', M['Thobe']), src, C.no_head)
    deco = [W.front_decal(pre + '_Placket', [(-0.012, 1.020), (0.012, 1.020), (0.012, 1.250), (-0.012, 1.250)], thobe, M['Thobe_Cuff'], 0.003,
                          thickness=0.003)]
    deco += W.buttons(pre + '_Btn', thobe, M['Buttons'], [(0.0, z) for z in (1.210, 1.150, 1.090)], r=0.007, offset=0.006)
    deco += [W.front_decal(f'{pre}_HemDust_{k}', W.blob(x, z, r, seed=170 + k, rough=0.55, sx=1.6), thobe, M['Dust'], 0.003)
             for k, (x, z, r) in enumerate(((-0.140, 0.220, 0.050), (0.060, 0.190, 0.040), (0.170, 0.260, 0.034), (-0.020, 0.330, 0.026)))]
    deco += [G.decal(f'{pre}_HemDustB_{k}', W.blob(x, z, r, seed=180 + k, rough=0.55, sx=1.6), W.BACK(), [thobe], 0.003, M['Dust'])
             for k, (x, z, r) in enumerate(((-0.100, 0.210, 0.046), (0.120, 0.240, 0.040)))]
    out = [thobe, collar] + [_t(o, tsrc) for o in deco]
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks'], top=0.250), src))
    out += O2._sandals(pre + '_Sandal', M['Socks'], M['Sandal_Strap'], M['Sandal_Sole'])
    out += BD2._big_watch(pre + '_Watch', M, x=0.600, side=1)
    out += keffiyeh(pre, M)
    out.append(TR.beard(pre + '_Beard', M['Beard']))
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.010, size=1.45)
    out += shawarma(pre + '_Shawarma', M, TYPES[pre]['arm_down'])
    return out


BUILDERS = {'CONSTR_INDIAN': indian, 'CONSTR_UZBEK': uzbek, 'CONSTR_MEXICAN': mexican, 'CONSTR_AFROAMERICAN': afroamerican,
            'CONSTR_ARAB': arab}


# ------------------------------------------------------------------ national moustaches (TASK-000896, Vadim: not the same moustache on everybody)
def _lip_tube(name, line, radii, material):
    pts = [Vector((x, B.head_surface_y(x, z, 0.004 + radii[i]), z)) for i, (x, z) in enumerate(line)]
    return C.rigid(G.tube(name, pts, lambda i, n: radii[i], material, seg=10), 'Head')


def handlebar_moustache(prefix, material):
    """Thick glossy handlebar moustache with the tips curled up (the Indian builder)."""
    out = []
    line = [(0.004, 1.447), (0.024, 1.448), (0.046, 1.441), (0.066, 1.432), (0.082, 1.438), (0.090, 1.455), (0.084, 1.470), (0.072, 1.466)]
    radii = [0.0105, 0.0120, 0.0110, 0.0090, 0.0072, 0.0058, 0.0046, 0.0036]
    for s in (1, -1):
        out.append(_lip_tube(f'{prefix}_{s}', [(s * x, z) for x, z in line], radii, material))
    return out


def horseshoe_moustache(prefix, material):
    """Huge bushy horseshoe moustache over the mouth, the ends hanging down to the chin (the Mexican builder)."""
    out = []
    line = [(0.004, 1.452), (0.030, 1.450), (0.056, 1.438), (0.074, 1.414), (0.080, 1.382), (0.080, 1.350), (0.077, 1.326)]
    radii = [0.0140, 0.0150, 0.0145, 0.0130, 0.0115, 0.0100, 0.0075]
    for s in (1, -1):
        out.append(_lip_tube(f'{prefix}_{s}', [(s * x, z) for x, z in line], radii, material))
    return out


def droopy_moustache_goatee(prefix, material):
    """Thin moustache drooping past the mouth corners and a short pointed chin beard (the Uzbek builder)."""
    out = []
    line = [(0.004, 1.446), (0.028, 1.443), (0.050, 1.432), (0.062, 1.410), (0.066, 1.386)]
    radii = [0.0060, 0.0064, 0.0056, 0.0045, 0.0030]
    for s in (1, -1):
        out.append(_lip_tube(f'{prefix}_{s}', [(s * x, z) for x, z in line], radii, material))
    chin = [Vector((0.0, B.head_surface_y(0.0, z, 0.006 + r), z)) for z, r in ((1.372, 0.012), (1.345, 0.014), (1.318, 0.011), (1.296, 0.004))]
    out.append(C.rigid(G.tube(prefix + '_Goatee', chin, lambda i, n: (0.012, 0.014, 0.011, 0.004)[i], material, seg=10), 'Head'))
    return out
