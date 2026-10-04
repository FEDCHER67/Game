"""MAP-FENCES-001 - tileable fence modules, posts and gates (bpy 5.0.1 / Blender 5.x, background).

Four fence types, each = Panel (tileable module between two post centres), Post (placed at every joint) and Gate
(includes its own two posts; gate leaves are child objects with the pivot on the hinge, rotate about local Z/Unity Y):
  * Concrete  - post-Soviet PO-2 style panel fence with rhombus relief, 2.5 m, panel pitch 3.0 m, steel double gate
  * Wood      - village picket fence, 1.6 m, pitch 2.5 m, single wicket gate
  * Elite     - stone plinth + wrought bars with gold spear tips between stone pillars, 2.4 m, pitch 3.0 m, double gate
  * Railing   - canal embankment pipe railing, 1.1 m, pitch 2.0 m, single swing gate to the steps

Tiling rule: a Panel spans x in [-L/2, +L/2] between post centres. Place panels at x = k*L and a Post at every
x = k*L + L/2. A Gate spans [-G/2, +G/2] between the centres of its own posts; continue panels from those centres.
Run:  python3 build_fences.py -- [--revision N] [--no-render] [--force] [--samples N]
"""
import math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp
from mapprops import T, R

fam = mp.Family('MAP-FENCES-001', __file__, prefix='FN_', tri_budget_default=1200,
                description='Tileable fence modules + posts + gates: Soviet concrete panel, village picket, elite stone/metal, canal railing.')


ROWS = {'Railing': 0, 'Wood': 1, 'Elite': 2, 'Concrete': 3}      # short fences in front for the review renders


def asset(name, mesh, budget, notes='', leaves=(), **meta):
    """leaves: [(child_name, Mesh, hinge_xy, closed_rotation_deg)]"""
    root = fam.make_object(name, mesh)
    objs = [root]
    for cname, cm, hinge, rot in leaves:
        c = fam.make_object(cname, cm, parent=root, pivot=(hinge[0], hinge[1], 0.0))
        c.rotation_euler.z = math.radians(rot)
        objs.append(c)
    fam.add_asset(name, objs, budget=budget, notes=notes, row=ROWS[name.split('_')[1]], **meta)


# =============================================================== 1. CONCRETE (PO-2 style), 2.5 m, pitch 3.0 m
CL, CH = 3.0, 2.5                 # pitch, post height
C_POST = 0.24                     # post section (square)
C_PANEL_T, C_PANEL_Z0, C_PANEL_Z1 = 0.12, 0.0, 2.40


def concrete_post(m, x, h=CH, s=C_POST):
    m.bevel_box(s, s, h - 0.04, 0.03, 'MP_Concrete_Dark', at=(x, 0, 0), base=True)
    m.bevel_box(s + 0.06, s + 0.06, 0.07, 0.04, 'MP_Concrete', at=(x, 0, h - 0.07), base=True)      # cap


def concrete_panel(seed, stained=True):
    rnd = random.Random(seed)
    m = mp.Mesh()
    w = CL - C_POST + 0.08                                                            # panel ends 4 cm inside each post
    m.box(w, C_PANEL_T, C_PANEL_Z1 - C_PANEL_Z0, 'MP_Concrete', at=(0, 0, C_PANEL_Z0), base=True)
    # frame band on the street side (-Y) top and bottom
    for z0, z1 in ((C_PANEL_Z0, C_PANEL_Z0 + 0.14), (C_PANEL_Z1 - 0.14, C_PANEL_Z1)):
        m.box(w - 0.02, 0.03, z1 - z0, 'MP_Concrete', at=(0, -C_PANEL_T / 2 - 0.01, z0), base=True)
    # rhombus relief: raised diamond frustums in a 7 x 4 grid on the street side
    cols, rows = 7, 4
    dx = (w - 0.2) / cols
    z_lo, z_hi = C_PANEL_Z0 + 0.20, C_PANEL_Z1 - 0.20
    dz = (z_hi - z_lo) / rows
    y0 = -C_PANEL_T / 2 + 0.01
    for i in range(cols):
        for j in range(rows):
            cx = -w / 2 + 0.1 + dx * (i + 0.5)
            cz = z_lo + dz * (j + 0.5)
            hx, hz = dx * 0.46, dz * 0.46
            ix, iz = hx * 0.55, hz * 0.55
            d = 0.035
            outer = [(cx + hx, cz), (cx, cz + hz), (cx - hx, cz), (cx, cz - hz)]
            inner = [(cx + ix, cz), (cx, cz + iz), (cx - ix, cz), (cx, cz - iz)]
            v = [(x, y0, z) for x, z in outer] + [(x, y0 - d, z) for x, z in inner]
            f = [(3, 2, 1, 0), (4, 5, 6, 7)] + [(k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k) for k in range(4)]
            mat = 'MP_Concrete_Stain' if stained and rnd.random() < 0.18 else 'MP_Concrete'
            m._shell(v, [ff[::-1] for ff in f], mat)
    # rust/rain stain streak under the top band
    if stained:
        for _ in range(2):
            sx = rnd.uniform(-w / 2 + 0.3, w / 2 - 0.3)
            m.box(rnd.uniform(0.12, 0.25), 0.012, rnd.uniform(0.5, 1.0), 'MP_Concrete_Stain',
                  at=(sx, C_PANEL_T / 2 + 0.004, C_PANEL_Z1 - 0.6), base=False)
    return m


m = concrete_panel(11)
asset('FN_Concrete_Panel', m, 600, 'Panel only; posts are FN_Concrete_Post. Relief on the -Y (street) side.',
      tile_length_m=CL, height_m=CH)
m = mp.Mesh(); concrete_post(m, 0)
asset('FN_Concrete_Post', m, 100, 'Place at every panel joint (x = k*3.0 + 1.5).', height_m=CH)

# gate: two heavy posts + two painted steel leaves (frame, sheet, diagonal brace), opening 4.0 m
CG_OPEN = 4.0
CG_POST = 0.40
CG = CG_OPEN + CG_POST                       # centre-to-centre
m = mp.Mesh()
for s in (-1, 1):
    concrete_post(m, s * CG / 2, h=2.7, s=CG_POST)
    m.cyl(0.03, 0.12, 6, 'MP_Metal_Dark', at=(s * (CG_OPEN / 2 + 0.01), -0.08, 0.35))   # hinge knuckles on the posts
    m.cyl(0.03, 0.12, 6, 'MP_Metal_Dark', at=(s * (CG_OPEN / 2 + 0.01), -0.08, 1.95))
leaves = []
LW, LH, LZ = CG_OPEN / 2 - 0.03, 2.2, 0.08
for side, colour in ((-1, 'MP_Paint_Green'), (1, 'MP_Paint_Green')):
    lm = mp.Mesh()
    hinge_x = side * (CG_OPEN / 2 + 0.01)
    cx = hinge_x - side * (LW / 2 + 0.02)
    fr = 0.06
    lm.box(LW, 0.03, LH, colour, at=(cx, -0.08, LZ), base=True)                                   # sheet
    for zz in (LZ, LZ + LH - fr):
        lm.box(LW, 0.07, fr, 'MP_Metal_Dark', at=(cx, -0.08, zz), base=True)                      # top/bottom frame
    for xx in (cx - LW / 2 + fr / 2, cx + LW / 2 - fr / 2):
        lm.box(fr, 0.07, LH, 'MP_Metal_Dark', at=(xx, -0.08, LZ), base=True)                      # side frame
    lm.box(LW - 0.1, 0.06, 0.05, 'MP_Metal_Dark', at=(cx, -0.08, LZ + LH / 2), base=False)        # mid rail
    # diagonal brace on both faces (rotated thin box)
    diag = math.hypot(LW - 0.12, LH / 2 - 0.08)
    ang = math.degrees(math.atan2(LH / 2 - 0.08, LW - 0.12)) * side
    lm.box(diag, 0.065, 0.05, 'MP_Metal_Dark', M=T(cx, -0.08, LZ + LH * 0.75) @ R(-ang, 'Y'))
    lm.box(diag, 0.065, 0.05, 'MP_Metal_Dark', M=T(cx, -0.08, LZ + LH * 0.25) @ R(-ang, 'Y'))
    # rust patches near the bottom
    lm.box(LW * 0.35, 0.036, 0.25, 'MP_Rust', at=(cx + side * 0.2, -0.08, LZ + 0.08), base=True)
    if side == 1:
        lm.box(0.04, 0.10, 0.25, 'MP_Metal_Grey', at=(cx - LW / 2 + 0.05, -0.08, 1.05), base=True)   # bolt latch
    leaves.append((f'FN_Concrete_Gate_Leaf{"L" if side < 0 else "R"}', lm, (hinge_x, -0.08), 0))
asset('FN_Concrete_Gate', m, 1000, f'Opening {CG_OPEN} m; leaves pivot on the hinge; rotating the left leaf +Z and the '
      'right leaf -Z (Blender) opens them inwards (+Y), negative angles open outwards (-Y); up to ~100 deg.', leaves=leaves, gate_pitch_m=CG, opening_m=CG_OPEN)

# =============================================================== 2. WOOD picket fence, 1.6 m, pitch 2.5 m
WL, WH = 2.5, 1.6
W_POST = 0.12


def wood_post(m, x, h=WH + 0.08, s=W_POST, mat='MP_Wood_Dark'):
    m.box(s, s, h - 0.08, mat, at=(x, 0, 0), base=True)
    v = [(x - s / 2, -s / 2, h - 0.08), (x + s / 2, -s / 2, h - 0.08), (x + s / 2, s / 2, h - 0.08), (x - s / 2, s / 2, h - 0.08), (x, 0, h)]
    m._shell(v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)], mat)                 # pyramid top


def picket(m, x, h, seed, z0=0.06, y=-0.075, mats=('MP_Wood_Grey', 'MP_Wood_Grey', 'MP_Wood_Grey', 'MP_Wood')):
    rnd = random.Random(seed)
    w = 0.085
    tip = 0.08
    h = h + rnd.uniform(-0.04, 0.03)
    tilt = rnd.uniform(-2.0, 2.0)
    poly = [(-w / 2, 0), (w / 2, 0), (w / 2, h - tip), (0, h), (-w / 2, h - tip)]
    m.extrude_xz(poly, -0.011, 0.011, rnd.choice(mats), M=T(x, y, z0) @ R(tilt, 'Y'))


def wood_rails(m, x0, x1, y=-0.03, zs=(0.35, 1.25)):
    for z in zs:
        m.box(x1 - x0, 0.045, 0.09, 'MP_Wood', at=((x0 + x1) / 2, y, z), base=True)


m = mp.Mesh()
wood_rails(m, -WL / 2 + 0.06, WL / 2 - 0.06)
n = 17
for i in range(n):
    x = -WL / 2 + 0.12 + (WL - 0.24) * (i + 0.5) / n
    picket(m, x, WH - 0.06, 100 + i)
asset('FN_Wood_Panel', m, 600, 'Pickets + two rails; posts are FN_Wood_Post. Pickets on the -Y side, 6 cm above the ground.',
      ground_contact=False, tile_length_m=WL, height_m=WH)
m = mp.Mesh(); wood_post(m, 0)
asset('FN_Wood_Post', m, 60, 'Place at every joint (x = k*2.5 + 1.25).', height_m=WH + 0.08)

WG_OPEN = 1.0
WG = WG_OPEN + W_POST
m = mp.Mesh()
for s in (-1, 1):
    wood_post(m, s * WG / 2, h=WH + 0.2, s=0.14)
lm = mp.Mesh()
hx = -WG_OPEN / 2
lw = WG_OPEN - 0.04
cx = hx + 0.02 + lw / 2
wood_rails(lm, cx - lw / 2, cx + lw / 2, y=-0.03, zs=(0.30, 1.20))
diag = math.hypot(lw - 0.1, 0.85)
lm.box(diag, 0.04, 0.08, 'MP_Wood', M=T(cx, -0.03, 0.30 + 0.09 + 0.43) @ R(-math.degrees(math.atan2(0.85, lw - 0.1)), 'Y'))   # Z brace
for i in range(7):
    picket(lm, cx - lw / 2 + lw * (i + 0.5) / 7, WH - 0.12, 300 + i, z0=0.10, mats=('MP_Wood',))
lm.box(0.05, 0.05, 0.12, 'MP_Metal_Dark', at=(cx + lw / 2 - 0.06, -0.1, 0.95), base=True)                    # latch
asset('FN_Wood_Gate', m, 600, f'Wicket gate, opening {WG_OPEN} m, hinge on the left post; +Z rotation opens it inwards (+Y), -Z outwards.',
      leaves=[('FN_Wood_Gate_Leaf', lm, (hx, -0.03), 0)], gate_pitch_m=WG, opening_m=WG_OPEN)

# =============================================================== 3. ELITE stone + wrought metal, 2.4 m, pitch 3.0 m
EL, EH = 3.0, 2.4
E_PIL = 0.56
E_PLINTH_H, E_PLINTH_T = 0.62, 0.38


def stone_pillar(m, x, h=EH, s=E_PIL, ball=True):
    m.bevel_box(s + 0.06, s + 0.06, 0.25, 0.03, 'MP_Stone_Grey', at=(x, 0, 0), base=True)            # foot
    m.bevel_box(s, s, h - 0.40, 0.03, 'MP_Stone_Light', at=(x, 0, 0.25), base=True)                  # shaft
    m.box(s * 0.92, s + 0.012, 0.06, 'MP_Stone_Grey', at=(x, 0, h - 0.62), base=True)     # band
    m.bevel_box(s + 0.10, s + 0.10, 0.10, 0.04, 'MP_Stone_Grey', at=(x, 0, h - 0.15), base=True)     # cornice
    m.lathe([(s * 0.42, h - 0.05), (s * 0.30, h + 0.02), (0.0, h + 0.05)], 8, 'MP_Stone_Grey', M=T(x, 0, 0), offset=math.pi / 8)
    if ball:
        m.cyl(0.05, 0.06, 6, 'MP_Stone_Grey', at=(x, 0, h + 0.03))
        m.blob(0.13, 'MP_Stone_Light', M=T(x, 0, h + 0.2), subdiv=1, jitter=0.0)


def spear(m, x, z, w=0.028, hgt=0.12, mat='MP_Gold'):
    v = [(x - w, -w, z), (x + w, -w, z), (x + w, w, z), (x - w, w, z), (x, 0, z + hgt)]
    m._shell(v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)], mat)


def bars(m, x0, x1, z0, tops, rails=(0.12, None)):
    n = len(tops)
    for i, top in enumerate(tops):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        m.box(0.026, 0.026, top - z0, 'MP_Metal_Black', at=(x, 0, z0), base=True)
        spear(m, x, top - 0.01)


def elite_panel():
    m = mp.Mesh()
    w = EL - E_PIL + 0.06
    m.box(w, E_PLINTH_T, E_PLINTH_H - 0.08, 'MP_Stone_Grey', at=(0, 0, 0), base=True)              # plinth
    m.box(w, E_PLINTH_T + 0.06, 0.08, 'MP_Stone_Light', at=(0, 0, E_PLINTH_H - 0.08), base=True)   # coping
    x0, x1 = -w / 2 + 0.03, w / 2 - 0.03
    for z in (E_PLINTH_H + 0.12, EH - 0.42):
        m.box(x1 - x0, 0.04, 0.045, 'MP_Metal_Black', at=(0, 0, z), base=True)
    # decorative ring row between the two rails (octagonal rings as closed tubes)
    tops = []
    n = 16
    for i in range(n):
        tops.append(EH - 0.18 + (0.06 if i % 2 == 0 else 0.0))
    bars(m, x0, x1, E_PLINTH_H - 0.02, tops)
    for i in range(0, n, 4):
        cx = x0 + (x1 - x0) * (i + 1.0) / n
        m.lathe([(0.0, -0.025), (0.08, -0.025), (0.08, 0.025), (0.0, 0.025)], 6, 'MP_Gold',
                M=T(cx, 0, EH - 0.62) @ R(90, 'X'), offset=math.pi / 6)                              # gold rosettes
    return m


asset('FN_Elite_Panel', elite_panel(), 1000, 'Stone plinth with coping + wrought bars and gold spear tips; pillars are FN_Elite_Post.',
      tile_length_m=EL, height_m=EH)
m = mp.Mesh(); stone_pillar(m, 0)
asset('FN_Elite_Post', m, 300, 'Stone pillar with cornice and ball; place at every joint (x = k*3.0 + 1.5).', height_m=EH + 0.33)

EG_OPEN = 4.2
EG_PIL = 0.72
EG = EG_OPEN + EG_PIL
m = mp.Mesh()
for s in (-1, 1):
    stone_pillar(m, s * EG / 2, h=EH + 0.4, s=EG_PIL)
leaves = []
for side in (-1, 1):
    lm = mp.Mesh()
    hinge_x = side * (EG_OPEN / 2 - 0.02)
    lw = EG_OPEN / 2 - 0.04
    xa, xb = (hinge_x, hinge_x - side * lw)
    x0, x1 = min(xa, xb), max(xa, xb)
    z0 = 0.06
    lm.box(lw, 0.05, 0.06, 'MP_Metal_Black', at=((x0 + x1) / 2, 0, z0), base=True)
    lm.box(lw, 0.05, 0.05, 'MP_Metal_Black', at=((x0 + x1) / 2, 0, 0.75), base=True)
    lm.box(0.06, 0.06, EH + 0.05, 'MP_Metal_Black', at=(hinge_x - side * 0.03, 0, z0), base=True)  # hinge stile
    n = 11
    tops = []
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        t = abs(x) / (EG_OPEN / 2)                                                              # 0 at centre -> 1 at hinge
        tops.append(EH + 0.15 + 0.45 * math.cos(t * math.pi / 2) ** 0.8 - 0.05)                 # arched top, high in the middle
    bars(lm, x0, x1, z0, tops)
    # arched top rail following the bar tops
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        t = abs(x) / (EG_OPEN / 2)
        pts.append((x, 0, EH + 0.15 + 0.45 * math.cos(min(t, 1) * math.pi / 2) ** 0.8 - 0.28))
    lm.tube_path(pts, [0.03] * len(pts), 4, 'MP_Metal_Black')
    lm.box(lw * 0.9, 0.05, 0.04, 'MP_Metal_Black', at=((x0 + x1) / 2, 0, 1.45), base=True)
    # gold scroll: a ring at the leaf centre
    cx = (x0 + x1) / 2
    lm.lathe([(0.0, -0.03), (0.22, -0.03), (0.22, 0.03), (0.0, 0.03)], 8, 'MP_Gold', M=T(cx, 0, 1.1) @ R(90, 'X'), offset=math.pi / 8)
    lm.lathe([(0.0, -0.035), (0.10, -0.035), (0.10, 0.035), (0.0, 0.035)], 8, 'MP_Metal_Black', M=T(cx, 0, 1.1) @ R(90, 'X'), offset=math.pi / 8)
    leaves.append((f'FN_Elite_Gate_Leaf{"L" if side < 0 else "R"}', lm, (hinge_x, 0.0), 0))
asset('FN_Elite_Gate', m, 1500, f'Double wrought gate with arched top, opening {EG_OPEN} m; left leaf +Z / right leaf -Z rotation (Blender) '
      'opens them inwards (+Y).', leaves=leaves, gate_pitch_m=EG, opening_m=EG_OPEN)

# =============================================================== 4. CANAL railing, 1.1 m, pitch 2.0 m
RL, RH = 2.0, 1.1
R_PIPE = 0.035


def rail_post(m, x, h=RH):
    m.box(0.16, 0.16, 0.02, 'MP_Metal_Dark', at=(x, 0, 0), base=True)                                # base plate
    m.cyl(0.04, h - 0.03, 8, 'MP_Paint_Green', at=(x, 0, 0.02))
    m.lathe([(0.0, h - 0.03), (0.055, h - 0.02), (0.055, h + 0.01), (0.0, h + 0.03)], 8, 'MP_Paint_Green', M=T(x, 0, 0))   # cap


def rail_section(m, x0, x1, h=RH, seed=0):
    rnd = random.Random(seed)
    m.cyl_between((x0, 0, h - 0.04), (x1, 0, h - 0.04), R_PIPE, 8, 'MP_Paint_Green')                # handrail
    m.box(x1 - x0, 0.03, 0.03, 'MP_Paint_Green', at=((x0 + x1) / 2, 0, 0.62), base=True)              # mid rail
    m.box(x1 - x0, 0.03, 0.03, 'MP_Paint_Green', at=((x0 + x1) / 2, 0, 0.12), base=True)              # low rail
    n = 12
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        mat = 'MP_Rust' if rnd.random() < 0.15 else 'MP_Paint_Green'
        m.box(0.018, 0.018, h - 0.20, mat, at=(x, 0, 0.12), base=True)


m = mp.Mesh()
rail_section(m, -RL / 2 + 0.03, RL / 2 - 0.03, seed=5)
asset('FN_Railing_Panel', m, 400, 'Painted pipe railing for the concrete canal edge; posts are FN_Railing_Post.',
      ground_contact=False, tile_length_m=RL, height_m=RH)
m = mp.Mesh(); rail_post(m, 0)
asset('FN_Railing_Post', m, 120, 'Round post on a base plate; place at every joint (x = k*2.0 + 1.0).', height_m=RH + 0.03)

RG_OPEN = 1.2
RG = RG_OPEN + 0.08
m = mp.Mesh()
for s in (-1, 1):
    rail_post(m, s * RG / 2, h=RH + 0.1)
lm = mp.Mesh()
hx = -RG_OPEN / 2 + 0.01
gx0, gx1 = hx + 0.03, RG_OPEN / 2 - 0.03
lm.cyl_between((hx + 0.02, 0, 0.10), (hx + 0.02, 0, RH - 0.02), 0.025, 6, 'MP_Paint_Green')                  # hinge stile
lm.cyl_between((gx1, 0, 0.10), (gx1, 0, RH - 0.02), 0.025, 6, 'MP_Paint_Green')                              # latch stile
rail_section(lm, gx0, gx1, h=RH - 0.02, seed=9)
lm.box(0.06, 0.08, 0.06, 'MP_Metal_Dark', at=(gx1, 0, 0.85), base=True)                                         # latch
asset('FN_Railing_Gate', m, 600, f'Swing gate to canal steps, opening {RG_OPEN} m; hinge on the left post; +Z rotation opens it towards +Y.',
      leaves=[('FN_Railing_Gate_Leaf', lm, (hx, 0.0), 0)], gate_pitch_m=RG, opening_m=RG_OPEN)

fam.finish(lineup_gap=1.2, row_gap=2.0, render=False,
           extra_notes=['Overlapping closed shells (pickets on rails, bars through rails, panel ends inside posts) are intentional.'])
if not fam.args.no_render:
    fam.render_previews(camera=[('01_pieces_front.png', 270, 8, (1800, 1000), 50),
                                ('02_pieces_three_quarter.png', 240, 22, (1800, 1100), 50)], person_at=(-1.4, -0.5, 0))
    # assembled runs: post | panel | post | panel | post | gate (half open) | post | panel | post, one fence type per row
    kinds = [('Railing', RL, RG, 0.0, {'FN_Railing_Gate_Leaf': 70}),
             ('Wood', WL, WG, 3.0, {'FN_Wood_Gate_Leaf': 60}),
             ('Elite', EL, EG, 6.5, {'FN_Elite_Gate_LeafL': 55, 'FN_Elite_Gate_LeafR': -55}),
             ('Concrete', CL, CG, 11.0, {'FN_Concrete_Gate_LeafL': 70, 'FN_Concrete_Gate_LeafR': -70})]
    for kind, L, G, y, pose in kinds:
        x = 0.0
        for _ in range(2):
            fam.place_copy(f'FN_{kind}_Post', x, y)
            fam.place_copy(f'FN_{kind}_Panel', x + L / 2, y)
            x += L
        fam.place_copy(f'FN_{kind}_Gate', x + G / 2, y, child_rot=pose)
        x += G
        fam.place_copy(f'FN_{kind}_Panel', x + L / 2, y)
        fam.place_copy(f'FN_{kind}_Post', x + L, y)
    shown = fam.showcase_only(True)
    fam.render_previews(camera=[('03_assembled_three_quarter.png', 245, 20, (1800, 1100), 50),
                                ('04_assembled_eye_level.png', 290, 4, (1800, 900), 40)],
                        frame_objects=shown, person_at=(3.0, -1.0, 0))
