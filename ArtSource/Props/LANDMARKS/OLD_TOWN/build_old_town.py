"""LANDMARKS / OLD_TOWN - old-town square landmarks: market stall with a striped awning, church bell with a swinging
clapper, small onion-dome cupola, square fountain, stylised clock tower top with movable hands.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/LANDMARKS/OLD_TOWN/build_old_town.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/LANDMARKS/OLD_TOWN/build_old_town.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import landmarks as lm
from landmarks import Mesh, T, R

fam = lm.Family('LM-OLD_TOWN', __file__)


# ---------------------------------------------------------------- market stall
def market_stall():
    """Wooden stall 2.4 x 1.2 m: counter with produce crates, four posts, red-white striped awning sloping to the
    front, scales on the counter, price board on a post."""
    m = Mesh()
    W, D = 2.4, 1.2
    for x in (-W / 2 + 0.06, W / 2 - 0.06):
        for y in (-D / 2 + 0.06, D / 2 - 0.06):
            h = 2.32 if y < 0 else 2.58                                                             # awning slopes to -Y
            m.box(0.09, 0.09, h, 'wood_dark', at=(x, y, 0), base=True)
    m.bevel_box(W, D, 0.82, 0.03, 'wood', at=(0, 0, 0.08), base=True)                               # counter body
    m.box(W + 0.10, D + 0.10, 0.06, 'wood_dark', at=(0, 0, 0.90), base=True)                        # counter top
    for x in (-0.8, 0.0, 0.8):                                                                      # front planks
        m.box(0.05, 0.03, 0.80, 'wood_dark', at=(x, -D / 2 - 0.01, 0.09), base=True)
    # produce crates on the counter: crate box + 4 low-poly 'fruits' in a row
    fruit = (('red', 0.075), ('orange', 0.08), ('green', 0.09), ('yellow', 0.07))
    for i, (col, r) in enumerate(fruit):
        cx = -0.85 + i * 0.52
        m.box(0.44, 0.34, 0.14, 'wood', at=(cx, -0.20, 0.96), base=True)
        for k in range(4):
            lm.ball(m, r, col, at=(cx - 0.12 + 0.08 * k, -0.22 + 0.06 * (k % 2), 1.10 + r * 0.4), seg=6, rings=3)
    m.box(0.30, 0.22, 0.10, 'metal', at=(0.80, 0.25, 0.96), base=True)                              # scales
    m.cyl(0.12, 0.02, 8, 'chrome', at=(0.80, 0.25, 1.12))
    m.box(0.04, 0.04, 0.08, 'metal', at=(0.80, 0.25, 1.05), base=True)
    m.box(0.36, 0.03, 0.26, 'black', at=(-W / 2 - 0.02, -D / 2 - 0.02, 1.55))                       # chalk price board
    # striped awning: 8 alternating slats from back (2.55) to front (2.25), with a scalloped valance
    n = 8
    zb, zf = 2.58, 2.20
    yb, yf = D / 2 + 0.05, -D / 2 - 0.35
    for i in range(n):
        x0 = -W / 2 - 0.10 + (W + 0.20) * i / n
        x1 = x0 + (W + 0.20) / n
        col = 'sign_red' if i % 2 == 0 else 'white'
        m.prism_xy([(x0, yb), (x1, yb), (x1, yf), (x0, yf)], 0, 0.04, col,
                   M=T(0, 0, 0) @ _shear_awning(yb, yf, zb, zf))
        xm = (x0 + x1) / 2
        m.prism([(x0, zf - 0.02), (x1, zf - 0.02), (xm, zf - 0.20)], 0.03, col, M=T(0, yf, 0))       # valance tooth
    return m


def _shear_awning(yb, yf, zb, zf):
    """Matrix that turns the flat slab z in [0, 0.04] into a slope from (yb, zb) to (yf, zf)."""
    k = (zb - zf) / (yb - yf)
    M = T(0, 0, zf - k * yf)
    M[2][1] = k
    return M


# ---------------------------------------------------------------- church bell (hangs in a belfry)
def church_bell():
    """Bronze bell 1.0 m across on a wooden headstock with iron straps; pivot = axle centre. Returns (bell, clapper)."""
    b, c = Mesh(), Mesh()
    zl = -1.10                                                                                    # lip height below axle
    # solid bell, bottom to top; the black bottom disc reads as the open mouth, a gold sound-bow band near the lip
    prof = [(0.0, zl), (0.53, zl), (0.52, zl + 0.04), (0.46, zl + 0.15), (0.37, zl + 0.38), (0.33, zl + 0.65),
            (0.30, zl + 0.88), (0.20, zl + 0.95), (0.0, zl + 0.95)]
    b.lathe(prof, 12, 'wood', cols=['black', 'yellow', 'wood', 'wood', 'wood', 'wood', 'wood', 'wood'])
    b.lathe([(0.0, zl + 0.95), (0.08, zl + 1.02), (0.08, zl + 1.08), (0.0, zl + 1.10)], 6, 'wood')  # canons stub
    # headstock: oak beam across the axle, iron straps over the crown, axle stubs
    b.bevel_box(1.20, 0.22, 0.24, 0.03, 'wood_dark', at=(0, 0, -0.02))
    for x in (-0.16, 0.16):
        b.box(0.05, 0.26, 0.28, 'metal_dark', at=(x, 0, -0.10))
        b.beam((x, 0, -0.20), (x * 1.3, 0, zl + 0.90), 0.05, 0.04, 'metal_dark', up=(0, 1, 0))
    for x in (-0.66, 0.66):
        b.cyl(0.05, 0.12, 6, 'metal', M=T(x, 0, 0) @ R(90, 'Y'), at=(0, 0, -0.06))
    # clapper: iron rod + ball, hinge just under the crown inside the bell
    hz = zl + 0.86
    c.bar((0, 0, hz), (0, 0, zl + 0.20), 0.025, 'metal_dark', seg=6)
    lm.ball(c, 0.09, 'metal_dark', at=(0, 0, zl + 0.20), seg=6, rings=4)
    c.box(0.06, 0.06, 0.06, 'metal', at=(0, 0, hz))
    return b, c, (0, 0, hz)


# ---------------------------------------------------------------- onion dome cupola (sits on a roof ridge)
def onion_cupola():
    """Small cupola 2.6 m: square roof plinth, octagonal drum with arched window niches, blue onion dome with gold
    stars band, gilded neck and an Orthodox cross."""
    m = Mesh()
    m.bevel_box(1.40, 1.40, 0.35, 0.04, 'white', base=True)                                         # plinth on the ridge
    m.box(1.46, 1.46, 0.06, 'cream', at=(0, 0, 0.35), base=True)
    m.cyl(0.55, 0.80, 8, 'white', at=(0, 0, 0.41), offset=math.pi / 8)                              # drum
    for k in range(8):                                                                              # window niches
        a = math.tau * k / 8
        Mw = T(0.53 * math.cos(a), 0.53 * math.sin(a), 0.80) @ R(math.degrees(a) + 90, 'Z')
        m.prism([(-0.10, -0.22), (0.10, -0.22), (0.10, 0.12), (0.0, 0.22), (-0.10, 0.12)], 0.06, 'glass_dark', M=Mw)
    m.cyl(0.62, 0.08, 8, 'cream', at=(0, 0, 1.21), offset=math.pi / 8)                              # cornice
    prof = [(0.0, 1.29), (0.50, 1.29), (0.66, 1.45), (0.70, 1.62), (0.62, 1.82), (0.44, 2.00), (0.22, 2.18),
            (0.08, 2.32), (0.05, 2.40), (0.0, 2.42)]
    cols = ['blue'] * (len(prof) - 1)
    cols[2] = 'yellow'                                                                              # gold band
    cols[-2] = cols[-1] = 'yellow'
    m.lathe(prof, 12, 'blue', cols=cols)
    m.lathe([(0.0, 2.38), (0.07, 2.38), (0.09, 2.46), (0.05, 2.52), (0.0, 2.52)], 6, 'yellow')       # ball
    zc = 2.50
    m.box(0.04, 0.04, 0.70, 'yellow', at=(0, 0, zc), base=True)                                     # cross: post
    m.box(0.30, 0.04, 0.04, 'yellow', at=(0, 0, zc + 0.48))                                         # main bar
    m.box(0.16, 0.04, 0.035, 'yellow', at=(0, 0, zc + 0.62))                                        # title bar
    m.box(0.22, 0.04, 0.035, 'yellow', M=T(0, 0, zc + 0.18) @ R(-20, 'Y'))                           # slanted foot bar
    return m


# ---------------------------------------------------------------- fountain (old town square)
def fountain():
    """Octagonal basin 5.0 m with a low rim seat, central column with a lower and an upper bowl, finial; water
    surfaces are LM_Fountain_Water. Returns (stone, water)."""
    s, w = Mesh(), Mesh()
    Rb = 2.5
    off = math.pi / 8
    s.cyl(Rb + 0.25, 0.10, 8, 'concrete_dark', offset=off)                                         # paving step
    # basin wall: one square-section tube around the octagon (mitred corners), coping ring on top
    rim = [((Rb - 0.22) * math.cos(off + math.tau * k / 8), (Rb - 0.22) * math.sin(off + math.tau * k / 8), 0.32)
           for k in range(8)]
    s.tube_path(rim, 0.21 * math.sqrt(2), 4, 'concrete', closed=True)
    s.tube_path([(x, y, 0.56) for x, y, _ in rim], 0.06 * math.sqrt(2), 4, 'cream', closed=True)
    s.cyl(Rb - 0.30, 0.12, 8, 'concrete_dark', at=(0, 0, 0.10), offset=off)                        # basin floor
    w.cyl(Rb - 0.28, 0.06, 8, 'glass', at=(0, 0, 0.36), offset=off)                                # basin water
    # column and bowls
    s.cyl(0.55, 0.30, 8, 'concrete', at=(0, 0, 0.10), offset=off)
    s.cyl(0.24, 1.10, 8, 'concrete', r_top=0.20, at=(0, 0, 0.40), offset=off)
    s.lathe([(0.0, 1.30), (0.30, 1.30), (1.10, 1.62), (1.15, 1.72), (0.0, 1.72)], 12, 'concrete')    # lower bowl
    w.cyl(1.02, 0.03, 12, 'glass', at=(0, 0, 1.70))
    s.cyl(0.14, 0.75, 8, 'concrete', at=(0, 0, 1.72), offset=off)
    s.lathe([(0.0, 2.40), (0.16, 2.40), (0.58, 2.62), (0.60, 2.70), (0.0, 2.70)], 10, 'concrete')    # upper bowl
    w.cyl(0.52, 0.03, 10, 'glass', at=(0, 0, 2.68))
    s.lathe([(0.0, 2.70), (0.10, 2.70), (0.13, 2.85), (0.06, 3.00), (0.10, 3.10), (0.0, 3.22)], 8, 'cream')  # finial
    # four spouts on the column, facing out (water jets are VFX in Unity)
    for k in range(4):
        a = math.tau * k / 4 + math.pi / 4
        c, si = math.cos(a), math.sin(a)
        s.bevel_box(0.16, 0.16, 0.20, 0.03, 'cream', M=T(0.24 * c, 0.24 * si, 0.72) @ R(math.degrees(a), 'Z'))
        s.bar((0.28 * c, 0.28 * si, 0.74), (0.46 * c, 0.46 * si, 0.70), 0.03, 'metal', seg=6)
    return s, w


# ---------------------------------------------------------------- clock tower top
def clock_tower_top():
    """Top of a 3.2 m square tower: cornice, clock stage with four faces, open belfry arches, tented roof with a
    spire and a weather vane. Hands are separate objects. Returns (body, emissive faces, hands [(name, mesh, pivot)])."""
    m, e = Mesh(), Mesh()
    hands = []
    Wt = 3.2
    m.bevel_box(Wt + 0.2, Wt + 0.2, 0.30, 0.04, 'cream', base=True)                                  # band on the shaft
    m.box(Wt, Wt, 2.4, 'brick', at=(0, 0, 0.30), base=True)                                          # clock stage
    for x in (-1, 1):                                                                               # corner pilasters
        for y in (-1, 1):
            m.box(0.30, 0.30, 2.4, 'cream', at=(x * (Wt / 2 - 0.10), y * (Wt / 2 - 0.10), 0.30), base=True)
    m.bevel_box(Wt + 0.36, Wt + 0.36, 0.22, 0.05, 'cream', at=(0, 0, 2.70), base=True)                # cornice
    zc = 1.50
    for k in range(4):                                                                              # four clock faces
        a = 90 * k
        Mf = R(a, 'Z') @ T(0, -Wt / 2, zc) @ R(90, 'X')                                             # local +Z -> -Y
        m.lathe([(0.0, 0.0), (0.98, 0.0), (0.98, 0.10), (0.0, 0.10)], 12, 'metal_dark', Mf)          # bezel
        e.lathe([(0.0, 0.10), (0.86, 0.10), (0.86, 0.13), (0.0, 0.13)], 12, 'cream', Mf)             # dial (lit)
        for h in range(4):                                                                          # 12 / 3 / 6 / 9 marks
            ang = math.tau * h / 4
            m.box(0.08, 0.20, 0.03, 'black',
                  M=Mf @ T(0.72 * math.sin(ang), 0.72 * math.cos(ang), 0.145) @ R(-math.degrees(ang), 'Z'))
        # hands: hour 10 o'clock, minute 2 o'clock -> 10:10; pivot at the dial centre on the face
        piv = Mf @ T(0, 0, 0.17)
        for hn, L, wdt, ang in (('Hour', 0.48, 0.09, -60), ('Minute', 0.74, 0.06, 60)):
            hm = Mesh()
            hm.prism([(-wdt / 2, -0.10), (wdt / 2, -0.10), (wdt / 2, L - 0.12), (0, L), (-wdt / 2, L - 0.12)], 0.03,
                     'black', M=piv @ R(-ang, 'Z') @ R(-90, 'X'))
            if hn == 'Minute':
                hm.cyl(0.07, 0.04, 6, 'yellow', M=piv, at=(0, 0, -0.02))                            # hub
            hands.append((f'Hand_{hn}_{"SENW"[k]}', hm, tuple(piv.translation)))
    # belfry stage: four corner piers with round arches between them, open in the middle
    zb = 2.92
    m.box(Wt - 0.2, Wt - 0.2, 0.12, 'cream', at=(0, 0, zb), base=True)
    for x in (-1, 1):
        for y in (-1, 1):
            m.box(0.55, 0.55, 1.50, 'brick', at=(x * (Wt / 2 - 0.37), y * (Wt / 2 - 0.37), zb + 0.12), base=True)
    for k in range(4):
        Ma = R(90 * k, 'Z') @ T(0, -(Wt / 2 - 0.37), 0)
        # arch head: a fan of convex trapezoid prisms between an elliptic arch and the top, plus a keystone
        n = 6
        curve = [(-0.96 * math.cos(math.pi * i / n), zb + 1.0 + 0.44 * math.sin(math.pi * i / n)) for i in range(n + 1)]
        for (x0, z0), (x1, z1) in zip(curve, curve[1:]):
            m.prism([(x0, z0), (x1, z1), (x1, zb + 1.62), (x0, zb + 1.62)], 0.45, 'brick', M=Ma)
        m.box(0.18, 0.49, 0.22, 'cream', M=Ma, at=(0, 0, zb + 1.36), base=True)
    m.bevel_box(Wt + 0.10, Wt + 0.10, 0.20, 0.04, 'cream', at=(0, 0, zb + 1.62), base=True)          # top cornice
    # tented roof, spire with a ball and a weather vane
    zr = zb + 1.82
    m.lathe([(2.45, zr), (0.18, zr + 2.60), (0.0, zr + 2.70)], 4, 'green', offset=math.pi / 4)
    m.cyl(0.10, 0.90, 6, 'yellow', at=(0, 0, zr + 2.60), r_top=0.03)
    lm.ball(m, 0.16, 'yellow', at=(0, 0, zr + 3.0), seg=8, rings=4)
    m.prism([(0.0, zr + 3.35), (0.70, zr + 3.35), (0.80, zr + 3.55), (0.55, zr + 3.62), (0.0, zr + 3.62)], 0.02,
            'yellow')                                                                               # vane flag
    m.box(0.03, 0.03, 0.40, 'yellow', at=(0, 0, zr + 3.30), base=True)
    return m, e, hands


# ---------------------------------------------------------------- assets
if fam.wants('LM_MarketStall'):
    fam.asset('LM_MarketStall', [('LM_MarketStall_Mesh', market_stall(), None, None)],
              sockets=[('SOCKET_Interact', (0.0, -1.10, 1.0)), ('SOCKET_Seller', (0.0, 0.95, 0.0))],
              notes='Market stall 2.4 x 1.2 m, awning slopes to the front (-Y). SOCKET_Interact = buyer, '
                    'SOCKET_Seller = where the seller NPC stands behind the counter.')
if fam.wants('LM_ChurchBell'):
    bell, clapper, hinge = church_bell()
    fam.asset('LM_ChurchBell', [('LM_ChurchBell_Mesh', bell, None, None), ('LM_ChurchBell_Clapper', clapper, hinge, None)],
              ground=False,
              notes='Bell 1.06 m across on a 1.2 m headstock (1.44 m with the axle stubs). Pivot = axle centre (rotate the root about X to swing). '
                    'LM_ChurchBell_Clapper has its pivot on its hinge under the crown. Hangs in a belfry, not on the ground.')
if fam.wants('LM_OnionCupola'):
    fam.asset('LM_OnionCupola', [('LM_OnionCupola_Mesh', onion_cupola(), None, None)],
              notes='Small cupola 1.46 m wide, 3.2 m tall incl. cross; pivot = plinth centre at the bottom (put it on '
                    'a roof ridge or a flat roof, the plinth may sink into the roof).')
if fam.wants('LM_Fountain'):
    stone, water = fountain()
    fam.asset('LM_Fountain', [('LM_Fountain_Mesh', stone, None, None), ('LM_Fountain_Water', water, None, None)],
              sockets=[('SOCKET_JetTop', (0.0, 0.0, 3.22))],
              notes='Octagonal fountain 5.1 m across, rim height 0.6 m (sitting edge). LM_Fountain_Water = three water '
                    'surfaces for a water material. Jets/splashes are VFX; SOCKET_JetTop at the finial.')
if fam.wants('LM_ClockTowerTop'):
    body, emis, hands = clock_tower_top()
    parts = [('LM_ClockTowerTop_Mesh', body, None, None), ('LM_ClockTowerTop_Emissive', emis, None, None)]
    parts += [(f'LM_ClockTowerTop_{n}', hm, piv, None) for n, hm, piv in hands]
    fam.asset('LM_ClockTowerTop', parts,
              notes='Top of a 3.2 m square tower (8.4 m tall piece): clock stage, open belfry arches, tented roof and '
                    'spire. Pivot = centre of the bottom band, put it on a 3.2 x 3.2 m shaft. Dials = '
                    'LM_ClockTowerTop_Emissive. Hands (hour/minute x S, W, N, E faces) have their pivot on the dial '
                    'centre; rotate about the local axis normal to the face. Built at 10:10.')

fam.finish()
