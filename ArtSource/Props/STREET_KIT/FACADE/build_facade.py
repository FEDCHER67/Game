"""STREET_KIT / FACADE - wall dressing for 9-16-storey Soviet prefab panel blocks: open and self-glazed balconies,
entrance canopy, split-system AC unit, satellite dish and stackable drainpipe modules.

Wall-mounted convention: the building wall is the plane y = 0, pieces stick out towards -Y (street side), the root pivot
(0,0,0) is the attachment point on the wall (horizontally centred, at the bottom of the piece; balconies: bottom of the
floor slab at the wall; entrance canopy: ground level at the wall line). Nothing goes into y > 0.01.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/FACADE/build_facade.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/FACADE/build_facade.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R, S
from mathutils import Vector

fam = sk.Family('SK-FACADE', __file__)
FLOOR_H = 2.8             # floor-to-floor module height
BAL_W, BAL_D = 3.0, 1.1   # balcony slab footprint
SLAB_T = 0.16
PIPE_R, PIPE_Y = 0.06, -0.14   # drainpipe radius and axis distance from the wall (0.08 m gap)


# ---------------------------------------------------------------- balconies
def balcony_slab(m):
    m.bevel_box(BAL_W, BAL_D, SLAB_T, 0.025, 'concrete', at=(0, -BAL_D / 2, 0), base=True)


def balcony_open():
    m = Mesh()
    balcony_slab(m)
    z0, h = SLAB_T, 0.92
    fy = -BAL_D + 0.04                                                         # front parapet plane
    m.box(BAL_W, 0.06, h, 'concrete', at=(0, fy, z0), base=True)              # precast ribbed parapet panel
    for sx in (-1, 1):
        m.box(0.06, BAL_D - 0.02, h, 'concrete', at=(sx * (BAL_W / 2 - 0.03), -BAL_D / 2 - 0.01, z0), base=True)
        for y in (-0.80, -0.45, -0.12):                                        # side ribs
            m.box(0.03, 0.07, h, 'concrete_dark', at=(sx * (BAL_W / 2 + 0.01), y, z0), base=True)
    for k in range(9):                                                         # front ribs
        x = -1.2 + k * 0.3
        m.box(0.07, 0.03, h, 'concrete_dark', at=(x, fy - 0.04, z0), base=True)
    # steel handrail on top
    top = z0 + h
    m.bevel_box(BAL_W + 0.06, 0.10, 0.06, 0.015, 'metal_dark', at=(0, fy, top), base=True)
    for sx in (-1, 1):
        m.bevel_box(0.10, BAL_D - 0.05, 0.06, 0.015, 'metal_dark', at=(sx * (BAL_W / 2 - 0.02), -BAL_D / 2 + 0.005, top), base=True)
    # drying-line brackets sticking out to the street, lines between them, a bit of washing
    ty = top + 0.04
    for x in (-1.25, 1.25):
        m.beam((x, fy, ty), (x, fy - 0.55, ty), 0.04, 0.04, 'metal_dark')
        m.beam((x, fy - 0.02, top - 0.40), (x, fy - 0.40, ty - 0.01), 0.035, 0.03, 'metal_dark')
    for y in (fy - 0.18, fy - 0.34, fy - 0.50):
        m.bar((-1.25, y, ty + 0.02), (1.25, y, ty + 0.02), 0.008, 'white', seg=4)
    m.box(0.45, 0.02, 0.55, 'pink', at=(-0.55, fy - 0.18, ty + 0.03 - 0.55), base=True)        # towel
    m.box(0.35, 0.02, 0.42, 'blue', at=(0.20, fy - 0.34, ty + 0.03 - 0.42), base=True)         # shirt
    m.box(0.30, 0.02, 0.30, 'yellow', at=(0.75, fy - 0.50, ty + 0.03 - 0.30), base=True)
    # clutter on the slab: wooden crate, a bucket, an old ski pair leaning on the wall
    m.bevel_box(0.55, 0.38, 0.36, 0.02, 'wood', at=(0.95, -0.30, z0), base=True)
    m.bevel_box(0.45, 0.32, 0.18, 0.02, 'wood_dark', M=T(0.95, -0.30, z0 + 0.36) @ R(8, 'Z'), base=True)
    m.cyl(0.13, 0.28, 8, 'red', r_top=0.16, at=(-1.05, -0.55, z0))
    for x in (-0.55, -0.45):
        m.beam((x, -0.30, z0), (x, -0.05, z0 + 1.55), 0.07, 0.02, 'blue', up=(0, 1, 0))
    return m


def balcony_glazed():
    m = Mesh()
    balcony_slab(m)
    z0 = SLAB_T
    fy = -BAL_D + 0.04
    hp = 0.90                                                                  # parapet height above the slab
    # front parapet: steel frame clad with wooden boards (vagonka), sides: painted corrugated sheet - mismatched
    m.box(BAL_W, 0.05, hp, 'wood_dark', at=(0, fy, z0), base=True)
    for k in range(7):
        m.box(BAL_W + 0.02, 0.025, 0.11, 'wood', at=(0, fy - 0.03, z0 + 0.02 + k * 0.125), base=True)
    for sx in (-1, 1):
        m.box(0.05, BAL_D - 0.02, hp, 'car_blue', at=(sx * (BAL_W / 2 - 0.025), -BAL_D / 2 - 0.01, z0), base=True)
        for y in (-0.88, -0.66, -0.44, -0.22):
            m.box(0.025, 0.05, hp, 'car_blue', at=(sx * (BAL_W / 2 + 0.01), y, z0), base=True)
    sill = z0 + hp
    m.bevel_box(BAL_W + 0.08, 0.14, 0.05, 0.015, 'white', at=(0, fy - 0.02, sill), base=True)
    for sx in (-1, 1):
        m.bevel_box(0.12, BAL_D - 0.06, 0.05, 0.015, 'white', at=(sx * (BAL_W / 2 - 0.02), -BAL_D / 2 + 0.01, sill), base=True)
    # glazing: front in white PVC frames, left side in old wooden frames, right side white
    g0, g1 = sill + 0.05, 2.58
    gh = g1 - g0
    m.box(BAL_W - 0.06, 0.012, gh, 'glass', at=(0, fy, g0), base=True)
    for k in range(7):                                                          # mullions
        x = -BAL_W / 2 + 0.04 + k * (BAL_W - 0.08) / 6
        m.box(0.06, 0.08, gh, 'white', at=(x, fy, g0), base=True)
    for z, hh in ((g0, 0.06), (g1 - 0.07, 0.07), (g0 + 1.05, 0.05)):            # bottom / top / fanlight transoms
        m.box(BAL_W - 0.04, 0.066, hh, 'white', at=(0, fy, z), base=True)       # thinner than mullions: no coplanar faces
    m.box(0.40, 0.012, 0.98, 'pink', at=(-0.97, fy - 0.016, g0 + 0.06), base=True)     # curtains drawn behind the panes
    m.box(0.40, 0.012, 0.98, 'cream', at=(0.03, fy - 0.016, g0 + 0.06), base=True)
    m.box(0.40, 0.012, 0.30, 'glass_dark', at=(-0.47, fy - 0.016, g0 + 1.11), base=True)  # cardboard-covered fanlight
    for sx, col in ((-1, 'wood'), (1, 'white')):
        x = sx * (BAL_W / 2 - 0.03)
        m.box(0.012, BAL_D - 0.12, gh, 'glass', at=(x, -BAL_D / 2, g0), base=True)
        for y in (fy, -0.55, -0.05):
            m.box(0.08, 0.06, gh, col, at=(x, y, g0), base=True)
        for z, hh in ((g0, 0.06), (g1 - 0.07, 0.07), (g0 + 1.05, 0.05)):
            m.box(0.066, BAL_D - 0.10, hh, col, at=(x, -BAL_D / 2 - 0.02, z), base=True)
    # one open sash on the front (hinged at its left edge, swung out)
    sw, sh = 0.42, 0.95
    M = T(0.83, fy - 0.04, g0 + 0.06) @ R(-35, 'Z')
    s = Mesh()
    s.box(sw, 0.05, 0.05, 'white', at=(sw / 2, 0, 0.025)); s.box(sw, 0.05, 0.05, 'white', at=(sw / 2, 0, sh - 0.025))
    s.box(0.05, 0.05, sh - 0.10, 'white', at=(0.025, 0, sh / 2)); s.box(0.05, 0.05, sh - 0.10, 'white', at=(sw - 0.025, 0, sh / 2))
    s.box(sw - 0.10, 0.01, sh - 0.10, 'glass_dark', at=(sw / 2, 0, sh / 2))
    m.merge(s, M)
    # home-made roof: corrugated sheet sloping to the street with a drip edge
    rd = BAL_D + 0.18
    slope = math.degrees(math.atan2(0.16, rd))
    m.box(BAL_W + 0.20, rd, 0.03, 'rust', M=T(0, -rd / 2, g1 + 0.11) @ R(slope, 'X'))
    m.box(BAL_W + 0.10, 0.10, 0.06, 'metal_dark', at=(0, fy, g1), base=True)    # roof bearer
    for k in range(6):                                                           # corrugation ribs
        x = -1.3 + k * 0.52
        m.box(0.05, rd - 0.02, 0.03, 'rust', M=T(x, -rd / 2, g1 + 0.13) @ R(slope, 'X'))
    return m


# ---------------------------------------------------------------- entrance canopy (pivot on the ground at the wall line)
def entrance_canopy():
    m = Mesh()
    W, D = 2.4, 1.4
    ph, step = 0.45, 0.15
    # porch slab and two steps
    m.bevel_box(W + 0.4, D, ph, 0.03, 'concrete', at=(0, -D / 2, 0), base=True)
    m.bevel_box(W, 0.32, ph - step, 0.03, 'concrete_dark', at=(0, -D - 0.16, 0), base=True)
    m.bevel_box(W, 0.32, ph - 2 * step, 0.03, 'concrete_dark', at=(0, -D - 0.48, 0), base=True)
    m.box(0.9, 0.6, 0.012, 'rubber', at=(0, -0.55, ph), base=True)                # doormat
    # cantilevered slab with roofing felt on top and a dark fascia
    zc = 2.6
    m.box(W, D + 0.1, 0.16, 'concrete', at=(0, -(D + 0.1) / 2, zc), base=True, top='ash')
    m.box(W + 0.04, 0.05, 0.10, 'metal_dark', at=(0, -D - 0.12, zc + 0.08), base=True)     # front drip edge
    for sx in (-1, 1):
        m.box(0.05, D + 0.12, 0.10, 'metal_dark', at=(sx * (W / 2 + 0.005), -(D + 0.12) / 2, zc + 0.08), base=True)
    # two thin steel posts on base plates, with a cross beam under the slab front
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.12)
        m.bar((x, -D + 0.12, ph), (x, -D + 0.12, zc), 0.045, 'metal_dark', seg=8)
        m.box(0.18, 0.18, 0.02, 'metal_dark', at=(x, -D + 0.12, ph), base=True)
    m.box(W - 0.1, 0.10, 0.12, 'metal_dark', at=(0, -D + 0.12, zc - 0.12), base=True)
    # lamp under the slab and a small number plate on the wall
    m.box(0.22, 0.14, 0.10, 'metal_dark', at=(0.55, -0.18, zc - 0.10), base=True)
    m.box(0.18, 0.10, 0.04, 'glow', at=(0.55, -0.18, zc - 0.13), base=True)
    m.box(0.30, 0.02, 0.22, 'sign_blue', at=(-0.85, -0.01, 2.15), base=True)
    m.box(0.12, 0.022, 0.12, 'white', at=(-0.85, -0.012, 2.20), base=True)
    return m


# ---------------------------------------------------------------- AC unit
def ac_unit():
    m = Mesh()
    bx, by, bz = 0.80, 0.30, 0.55
    yb, zb = -0.07 - by / 2, 0.36                                                # body centre y, bottom z
    yf = yb - by / 2                                                             # front face
    for x in (-0.28, 0.28):
        m.box(0.05, 0.01, 0.42, 'metal', at=(x, -0.005, 0), base=True)           # wall plate
        m.beam((x, 0, 0.335), (x, -0.42, 0.335), 0.04, 0.035, 'metal')          # arm
        m.beam((x, -0.01, 0.03), (x, -0.36, 0.32), 0.035, 0.03, 'metal')        # brace
        m.box(0.035, 0.004, 0.30, 'rust', at=(x + 0.01, -0.002, 0.0), base=True) # rust drip on the wall
    m.bevel_box(bx, by, bz, 0.03, 'white', at=(0, yb, zb), base=True)
    for x in (-0.33, 0.33):                                                       # rubber feet
        m.box(0.06, 0.20, 0.02, 'rubber', at=(x, yb, zb - 0.015), base=True)
    # fan grille: dark disc, two rings, cross bars, hub
    cx, cz = -0.10, zb + bz / 2
    Mf = T(cx, yf + 0.005, cz) @ R(90, 'X')
    m.cyl(0.215, 0.02, 16, 'metal_dark', M=Mf)
    for r in (0.20, 0.12):
        pts = [(cx + r * math.cos(TAU_K), yf - 0.02, cz + r * math.sin(TAU_K)) for TAU_K in [math.tau * k / 14 for k in range(14)]]
        m.tube_path(pts, 0.011, 4, 'white', closed=True)
    m.beam((cx - 0.20, yf - 0.02, cz), (cx + 0.20, yf - 0.02, cz), 0.015, 0.02, 'white', up=(0, 1, 0))
    m.beam((cx, yf - 0.02, cz - 0.20), (cx, yf - 0.02, cz + 0.20), 0.015, 0.02, 'white', up=(0, 1, 0))
    m.cyl(0.04, 0.035, 8, 'white', M=T(cx, yf + 0.005, cz) @ R(90, 'X'))
    # side vents on the +X end and a service cover with the pipe outlets
    for k in range(6):
        m.box(0.02, 0.22, 0.025, 'metal_dark', at=(bx / 2 + 0.005, yb, zb + 0.10 + k * 0.065), base=True)
    m.box(0.12, 0.02, 0.18, 'metal', at=(0.30, yf - 0.005, zb + 0.08), base=True)
    for k in range(4):
        m.box(0.02, 0.18, 0.02, 'metal_dark', at=(-bx / 2 - 0.005, yb, zb + 0.15 + k * 0.08), base=True)
    # insulated pipe bundle from the unit's side into the wall, with a seal ring
    m.tube_path([(bx / 2 - 0.02, yb + 0.05, zb + 0.14), (bx / 2 + 0.10, yb + 0.05, zb + 0.14), (bx / 2 + 0.14, yb + 0.10, zb + 0.22),
                 (bx / 2 + 0.14, -0.06, zb + 0.34), (bx / 2 + 0.14, 0.005, zb + 0.34)], 0.028, 6, 'white')
    m.box(0.12, 0.012, 0.12, 'concrete_dark', at=(bx / 2 + 0.14, -0.006, zb + 0.34))
    return m


# ---------------------------------------------------------------- satellite dish
def satellite_dish():
    m = Mesh()
    m.box(0.12, 0.012, 0.26, 'metal', at=(0, -0.006, 0), base=True)              # wall plate
    my = -0.36                                                                   # mast line
    m.bar((0, 0, 0.20), (0, my, 0.20), 0.02, 'metal', seg=6)                     # arm
    m.bar((0, -0.01, 0.04), (0, my + 0.03, 0.19), 0.015, 'metal', seg=6)         # brace
    m.bar((0, my, 0.12), (0, my, 0.46), 0.024, 'metal', seg=6)                   # mast
    for z in (0.04, 0.20):
        m.box(0.06, 0.02, 0.04, 'metal_dark', at=(0, -0.012, z))                 # bolts
    centre = Vector((0.0, -0.46, 0.46))
    Md = T(*centre) @ R(22, 'Z') @ R(63, 'X') @ S(1, 1.1, 1)
    d = Mesh()
    prof = [(0, 0.0), (0.10, 0.006), (0.20, 0.024), (0.30, 0.054), (0.30, 0.066), (0.20, 0.036), (0.10, 0.018), (0, 0.012)]
    d.lathe(prof, 16, 'white', cols=[None, None, None, None, 'chrome', 'chrome', 'chrome', None])   # grey dish face, white back/rim
    d.box(0.10, 0.12, 0.06, 'metal', at=(0, 0, -0.03))                            # back mount
    # LNB arm from the lower rim to the focal point, LNB head facing the dish
    d.beam((0, -0.31, 0.05), (0, -0.25, 0.44), 0.03, 0.02, 'metal', up=(1, 0, 0))
    d.bar((0, -0.25, 0.40), (0, -0.22, 0.52), 0.032, 'metal_dark', seg=8)
    d.bar((0, -0.22, 0.52), (0, -0.21, 0.57), 0.045, 'white', seg=8, r1=0.04)
    m.merge(d, Md)
    m.bar((0, my, 0.44), tuple(Md @ Vector((0, 0, -0.04))), 0.02, 'metal', seg=6)   # mast head to dish back
    # coax cable from the LNB down the arm, mast and into the wall
    p = [Md @ Vector(v) for v in ((0.03, -0.24, 0.40), (0.03, -0.28, 0.12), (0.03, -0.30, 0.02))]
    cable = [tuple(v) for v in p] + [(0.035, my + 0.01, 0.30), (0.035, my + 0.01, 0.16), (0.035, -0.10, 0.14), (0.035, 0.005, 0.14)]
    m.tube_path(cable, 0.006, 4, 'black')
    return m


# ---------------------------------------------------------------- drainpipes (galvanised, stackable, axis 0.14 m off the wall)
def clamp(m, z):
    m.cyl(PIPE_R + 0.012, 0.045, 10, 'metal_dark', at=(0, PIPE_Y, z - 0.0225))
    m.box(0.03, abs(PIPE_Y) - PIPE_R + 0.01, 0.03, 'metal_dark', at=(0, (PIPE_Y + PIPE_R) / 2 - 0.005, z))
    m.box(0.08, 0.012, 0.08, 'metal_dark', at=(0, -0.006, z))                     # wall plate


def drain_straight():
    m = Mesh()
    m.cyl(PIPE_R, FLOOR_H - 0.01, 10, 'metal', at=(0, PIPE_Y, 0))
    m.cyl(PIPE_R + 0.008, 0.14, 10, 'metal', at=(0, PIPE_Y, FLOOR_H - 0.14))      # socket of the joint
    m.cyl(PIPE_R + 0.004, 0.02, 10, 'metal', at=(0, PIPE_Y, FLOOR_H - 0.16), r_top=PIPE_R + 0.008)
    for z in (0.55, 2.15):
        clamp(m, z)
    return m


def drain_bottom():
    m = Mesh()
    H = 1.0
    m.tube_path([(0, PIPE_Y, H - 0.01), (0, PIPE_Y, 0.42), (0, PIPE_Y - 0.03, 0.30), (0, PIPE_Y - 0.12, 0.20),
                 (0, PIPE_Y - 0.26, 0.15), (0, PIPE_Y - 0.36, 0.14)], PIPE_R, 10, 'metal')
    m.cyl(PIPE_R + 0.008, 0.14, 10, 'metal', at=(0, PIPE_Y, H - 0.14))
    m.bar((0, PIPE_Y - 0.33, 0.14), (0, PIPE_Y - 0.42, 0.135), PIPE_R + 0.012, 'metal', seg=10)        # outlet lip
    clamp(m, 0.70)
    # concrete splash tray on the ground
    m.bevel_box(0.30, 0.55, 0.06, 0.015, 'concrete', at=(0, PIPE_Y - 0.36, 0), base=True)
    return m


def drain_top():
    m = Mesh()
    fy = PIPE_Y - 0.20                                                           # funnel sits further out under the eave
    m.tube_path([(0, PIPE_Y, 0.0), (0, PIPE_Y, 0.22), (0, PIPE_Y - 0.05, 0.31), (0, fy, 0.43), (0, fy, 0.56)], PIPE_R, 10, 'metal')
    m.lathe([(0.075, 0.54), (0.075, 0.58), (0.16, 0.70), (0.16, 0.80), (0.175, 0.80), (0.175, 0.83)], 4, 'metal',
            M=T(0, fy, 0), offset=math.pi / 4)                                   # square funnel box with a rim
    m.box(0.20, 0.03, 0.03, 'metal_dark', at=(0, fy + 0.14, 0.78))               # gutter stub entering the funnel
    m.box(0.03, abs(fy) - 0.10, 0.03, 'metal_dark', at=(0, (fy + 0.10) / 2 - 0.0, 0.66))   # funnel hanger to the wall
    clamp(m, 0.12)
    return m


for name, fn, ground, notes in (
        ('SK_Balcony_Open', balcony_open, True, 'Open balcony 3.0 x 1.1 m: ribbed precast parapet, steel handrail, drying-line brackets with washing, crate, bucket, skis. Pivot = bottom of the floor slab at the wall; module height 2.8 m.'),
        ('SK_Balcony_Glazed', balcony_glazed, True, 'Self-glazed balcony: board-clad front, blue sheet sides, white PVC front frames, one side in old wooden frames, an open sash, rusty roof sheet. Pivot = bottom of the floor slab at the wall.'),
        ('SK_EntranceCanopy', entrance_canopy, True, 'Entrance (podezd) canopy: 2.4 x 1.5 m slab at 2.6 m on two steel posts, porch 0.45 m with two steps, lamp, entrance number plate. Pivot = ground at the wall line.'),
        ('SK_AC_Unit', ac_unit, False, 'Split-system outdoor unit 0.8 x 0.3 x 0.55 m on two wall brackets, fan grille, side vents, insulated pipe into the wall, rust drips. Pivot = bottom of the brackets at the wall.'),
        ('SK_SatelliteDish', satellite_dish, False, '0.6 m offset dish on a wall bracket, tilted up and turned, LNB arm and coax cable. Pivot = bottom of the wall plate.'),
        ('SK_Drainpipe_Straight', drain_straight, False, 'One-floor drainpipe module, z 0..2.8 m, stackable; axis 0.14 m off the wall, two clamps, joint socket at the top.'),
        ('SK_Drainpipe_Bottom', drain_bottom, True, 'Lowest drainpipe module (1.0 m) with an elbow outlet kicking away from the wall and a concrete splash tray; top joins SK_Drainpipe_Straight at z 1.0.'),
        ('SK_Drainpipe_Top', drain_top, False, 'Top drainpipe module (0.83 m): offset gooseneck out to a square gutter funnel; bottom joins SK_Drainpipe_Straight top.')):
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', fn(), None, None)], notes=notes, ground=ground, wall_mounted=True)

fam.finish()
