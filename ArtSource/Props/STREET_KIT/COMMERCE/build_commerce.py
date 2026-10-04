"""STREET_KIT / COMMERCE - empty shop sign boards for the signage atlas, a Soviet newspaper kiosk, a street ATM pavilion.

Sign faces use the material SK_Signage with UVs into the 2048 x 2048 signage atlas (layout: ../_lib/signage_atlas_layout.json,
README of this family). Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/COMMERCE/build_commerce.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/COMMERCE/build_commerce.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-COMMERCE', __file__)


def gooseneck(m, x, z_top, reach=0.55):
    """Wall lamp arm over a sign: wall plate, bent tube, conical shade with a glowing lens."""
    m.box(0.10, 0.03, 0.12, 'metal_dark', at=(x, -0.015, z_top + 0.10))
    m.tube_path([(x, -0.03, z_top + 0.10), (x, -0.20, z_top + 0.30), (x, -reach + 0.10, z_top + 0.34), (x, -reach, z_top + 0.26)], 0.018, 6, 'metal_dark')
    m.lathe([(0.0, 0.0), (0.09, 0.0), (0.04, 0.10), (0.0, 0.11)], 8, 'metal_dark', M=T(x, -reach, z_top + 0.12))
    m.lathe([(0.0, -0.005), (0.07, -0.005), (0.07, 0.0), (0.0, 0.0)], 8, 'glow', M=T(x, -reach, z_top + 0.12))


def wall_board(w, h, kind, slot, lamps):
    """Flat facade board: back against the wall plane y = 0, face to -Y, bottom edge at z = 0 (pivot)."""
    m = Mesh()
    d = 0.12
    m.bevel_box(w + 0.10, d, h + 0.10, 0.025, 'metal_dark', at=(0, -d / 2, (h + 0.10) / 2 - 0.05 + 0.05))       # frame / box
    m.sign_face_box(w, h, 0.02, 'metal_dark', kind, slot, M=T(0, -d - 0.008, h / 2 + 0.05))
    for x in (-w / 2 + 0.15, w / 2 - 0.15):                                                               # wall brackets
        m.box(0.06, 0.04, 0.10, 'metal', at=(x, -0.02, 0.0), base=True)
        m.box(0.06, 0.04, 0.10, 'metal', at=(x, -0.02, h), base=True)
    for i in range(lamps):
        gooseneck(m, -w / 2 + w * (i + 0.5) / lamps, h + 0.10)
    return m


def projecting_board(w, h, kind, slot):
    """Double-sided board hanging from a wall arm, faces to +X and -X; wall plate at y = 0, pivot at the plate bottom."""
    m = Mesh()
    reach = w + 0.25
    zb = 0.0
    m.bevel_box(0.08, 0.04, h + 0.30, 0.01, 'metal_dark', at=(0, -0.02, zb), base=True)                     # wall plate
    m.beam((0, -0.04, zb + h + 0.22), (0, -reach, zb + h + 0.22), 0.05, 0.05, 'metal_dark')                  # top arm
    m.beam((0, -0.04, zb + h * 0.35), (0, -reach * 0.55, zb + h + 0.20), 0.035, 0.035, 'metal_dark', up=(1, 0, 0))  # strut
    m.tube_path([(0, -0.30, zb + h + 0.24), (0, -0.40, zb + h + 0.40), (0, -0.55, zb + h + 0.38), (0, -0.58, zb + h + 0.26)], 0.015, 6, 'metal_dark')  # scroll
    yc = -0.12 - w / 2 - 0.05
    for y in (yc - w / 2 + 0.08, yc + w / 2 - 0.08):
        m.bar((0, y, zb + h + 0.2), (0, y, zb + h + 0.06), 0.012, 'metal', seg=4)                             # hangers
    m.bevel_box(0.16, w + 0.06, h + 0.06, 0.02, 'metal_dark', at=(0, yc, zb + 0.06 + h / 2))                # lightbox body
    m.sign_face_box(w, h, 0.18, 'metal_dark', kind, slot, M=T(0, yc, zb + 0.06 + h / 2) @ R(90, 'Z'), both=True)
    m.box(0.20, w + 0.10, 0.03, 'glow', at=(0, yc, zb + 0.015 + 0.0))                                       # light strip underneath
    return m


def kiosk():
    """Soviet 'Soyuzpechat' newspaper kiosk: painted lower panels, glazed upper body with magazines, overhanging roof,
    sign band (signage wide_4x1 slot 1) on the front, service window with a small counter."""
    m = Mesh()
    W, D, H = 2.6, 1.8, 2.5
    m.bevel_box(W + 0.1, D + 0.1, 0.10, 0.02, 'concrete_dark', base=True)                                    # plinth
    m.bevel_box(W, D, 0.95, 0.02, 'teal', at=(0, 0, 0.10), base=True)                                       # lower body
    m.box(W + 0.02, D + 0.02, 0.05, 'white', at=(0, 0, 1.05), base=True)                                     # sill band
    m.box(W - 0.06, D - 0.06, H - 1.10, 'glass', at=(0, 0, 1.10), base=True)                                 # glazing block
    for x in (-W / 2, -W / 6, W / 6, W / 2):                                                                   # mullions
        for y in (-D / 2, D / 2):
            m.box(0.06, 0.06, H - 1.10, 'white', at=(x, y, 1.10), base=True)
    for y in (-D / 6, D / 6):
        for x in (-W / 2, W / 2):
            m.box(0.06, 0.06, H - 1.10, 'white', at=(x, y, 1.10), base=True)
    m.box(W + 0.02, D + 0.02, 0.05, 'white', at=(0, 0, 1.85))                                                 # transom
    # magazines on display behind the front glass
    cols = ['red', 'yellow', 'sign_blue', 'white', 'orange', 'green', 'pink', 'cream']
    for i in range(8):
        x = -1.05 + i * 0.30
        if abs(x - 0.45) < 0.25:
            continue                                                                                           # service window
        m.box(0.20, 0.012, 0.26, cols[i], M=T(x, -D / 2 + 0.015, 1.42 + 0.06 * (i % 2)))      # pressed to the glass
    # service window: dark opening, small counter, price card
    m.box(0.42, 0.02, 0.36, 'glass_dark', at=(0.45, -D / 2 - 0.005, 1.30))
    m.bevel_box(0.60, 0.22, 0.04, 0.01, 'white', at=(0.45, -D / 2 - 0.10, 1.08))
    m.box(0.12, 0.012, 0.08, 'white', at=(0.10, -D / 2 - 0.01, 1.70))
    # roof: overhanging slab + sign band on the front and back
    m.bevel_box(W + 0.40, D + 0.40, 0.14, 0.04, 'white', at=(0, 0, H), base=True)
    m.bevel_box(W + 0.20, D + 0.10, 0.10, 0.02, 'teal', at=(0, 0, H + 0.14), base=True)
    m.sign_face_box(2.4, 0.6, 0.12, 'teal', 'wide_4x1', 1, M=T(0, -D / 2 + 0.05, H + 0.24 + 0.32))
    m.box(2.5, 0.10, 0.06, 'teal', at=(0, -D / 2 + 0.05, H + 0.24 + 0.64))
    # newspaper rack by the side and a rubbish bin hint
    m.box(0.06, 0.40, 0.90, 'metal_dark', at=(W / 2 + 0.25, -0.3, 0), base=True)
    m.box(0.06, 0.40, 0.90, 'metal_dark', at=(W / 2 + 0.55, -0.3, 0), base=True)
    for k, z in enumerate((0.35, 0.60, 0.85)):
        m.box(0.36, 0.36, 0.03, 'metal_dark', M=T(W / 2 + 0.40, -0.3, z) @ R(-12, 'Y'))
        m.box(0.30, 0.30, 0.03, ('white', 'cream', 'white')[k], M=T(W / 2 + 0.40, -0.3, z + 0.03) @ R(-12, 'Y'))
    return m


def atm_pavilion():
    """Street ATM booth: plinth, painted body, recessed ATM front with screen and keypad, canopy, sign band
    (signage wide_4x1 slot 2) and a lamp over the machine."""
    m = Mesh()
    W, D, H = 1.4, 1.1, 2.35
    m.bevel_box(W + 0.2, D + 0.2, 0.12, 0.03, 'concrete', base=True)
    m.bevel_box(W, D, H, 0.04, 'white', at=(0, 0, 0.12), base=True)
    m.box(W + 0.02, D + 0.02, 0.18, 'green', at=(0, 0, 0.12), base=True)                                    # coloured skirting
    m.box(W + 0.02, D + 0.02, 0.10, 'green', at=(0, 0, 1.95), base=True)                                    # coloured belt
    # recessed ATM front (machine fascia proud of a dark niche)
    m.box(0.90, 0.04, 1.30, 'black', at=(0, -D / 2 - 0.005, 0.55), base=True)                               # niche frame
    m.bevel_box(0.78, 0.10, 1.18, 0.02, 'metal', at=(0, -D / 2 - 0.03, 0.60), base=True)                    # fascia
    m.box(0.40, 0.02, 0.30, 'glass_dark', M=T(0, -D / 2 - 0.085, 1.42) @ R(-10, 'X'))                       # screen
    m.box(0.30, 0.02, 0.24, 'glass', M=T(0, -D / 2 - 0.08, 1.42) @ R(-10, 'X'))                             # lit screen area
    m.box(0.62, 0.20, 0.05, 'metal_dark', M=T(0, -D / 2 - 0.13, 1.10) @ R(14, 'X'))                         # keypad shelf
    for i in range(3):
        for j in range(4):
            m.box(0.05, 0.04, 0.02, 'chrome', M=T(-0.08 + i * 0.07, -D / 2 - 0.13 + (j - 1.5) * 0.04, 1.13 + (1.5 - j) * 0.01) @ R(14, 'X'))
    m.box(0.12, 0.03, 0.03, 'black', at=(0.24, -D / 2 - 0.095, 1.23))                                       # card slot
    m.box(0.36, 0.03, 0.04, 'black', at=(0, -D / 2 - 0.095, 0.90))                                          # cash slot
    m.box(0.06, 0.03, 0.03, 'green', at=(0.32, -D / 2 - 0.095, 1.23))                                       # card light
    # canopy + sign band on top
    m.bevel_box(W + 0.30, D + 0.30, 0.10, 0.03, 'green', at=(0, -0.05, 0.12 + H), base=True)
    m.sign_face_box(1.6, 0.4, 0.14, 'green', 'wide_4x1', 2, M=T(0, -0.05, 0.12 + H + 0.10 + 0.22))
    gooseneck(m, 0, 1.92, reach=0.40)
    # a side vent and a sticker-y vandal touch
    for z in (0.5, 0.6, 0.7):
        m.box(0.02, 0.40, 0.04, 'metal_dark', at=(W / 2 + 0.01, 0.15, z))
    return m


boards = (
    ('SK_ShopSign_Wide_4x1', lambda: wall_board(4.0, 1.0, 'wide_4x1', 0, 3), 'Facade board 4.0 x 1.0 m, signage wide_4x1 slot 0, three gooseneck lamps.'),
    ('SK_ShopSign_Medium_2x1', lambda: wall_board(2.0, 1.0, 'medium_2x1', 0, 2), 'Facade board 2.0 x 1.0 m, signage medium_2x1 slot 0, two gooseneck lamps.'),
    ('SK_ShopSign_Lightbox_1x1', lambda: projecting_board(0.8, 0.8, 'square_1x1', 1), 'Projecting double-sided lightbox 0.8 x 0.8 m on a wall arm, faces +X/-X, signage square_1x1 slot 1.'),
    ('SK_ShopSign_Vertical_1x4', lambda: projecting_board(0.5, 2.0, 'vertical_1x4', 0), 'Projecting double-sided vertical board 0.5 x 2.0 m (e.g. APTEKA), faces +X/-X, signage vertical_1x4 slot 0.'),
)
for name, fn, notes in boards:
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', fn(), None, None)], notes=notes + ' Wall-mounted: wall plane y = 0, pivot at the bottom of the piece on the wall.',
                  wall_mounted=True)
if fam.wants('SK_NewsKiosk'):
    fam.asset('SK_NewsKiosk', [('SK_NewsKiosk_Mesh', kiosk(), None, None)],
              sockets=[('SOCKET_Interact', (0.45, -1.25, 1.2))],
              notes='Newspaper kiosk 2.6 x 1.8 m, roof band 2.4 x 0.6 m = signage wide_4x1 slot 1; service window on the front (-Y), SOCKET_Interact where the buyer stands.')
if fam.wants('SK_ATM_Pavilion'):
    fam.asset('SK_ATM_Pavilion', [('SK_ATM_Pavilion_Mesh', atm_pavilion(), None, None)],
              sockets=[('SOCKET_Interact', (0.0, -1.05, 1.2))],
              notes='Street ATM booth 1.4 x 1.1 m, machine on the front (-Y), sign band 1.6 x 0.4 m = signage wide_4x1 slot 2, SOCKET_Interact in front of the screen.')

fam.finish()
