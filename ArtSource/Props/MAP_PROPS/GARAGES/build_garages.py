"""MAP-GARAGES-001 - Soviet metal garage row modules (bpy 5.0.1 / Blender 5.x, background).

One unit = one welded sheet-metal garage, 3.0 m wide (tile pitch along X), 5.6 m deep, 2.45 m at the front,
single-pitch roof falling to the back, double swing doors on the -Y front. Units placed side by side every 3.0 m
form a garage row (walls are 2.5 cm inside the tile edge, so neighbours never z-fight).
The garage is hollow (floor slab, walls, roof); door leaves are child objects with the pivot on the hinge.
  * GR_MetalGarage_Green / _Blue / _Rust - closed, three paint schemes and wear levels
  * GR_MetalGarage_Open                  - blue unit with both doors open (~105 deg) and a few things inside
Run:  python3 build_garages.py -- [--revision N] [--no-render] [--force] [--samples N]
"""
import math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp
from mapprops import T, R

fam = mp.Family('MAP-GARAGES-001', __file__, prefix='GR_', tri_budget_default=1500,
                description='Tileable Soviet metal garage units (3.0 m pitch) with hinged double doors; closed variants and one open.')

W, D = 3.0, 5.6               # tile pitch, depth
HF, HB = 2.45, 2.15           # wall height front / back
WT = 0.04                     # sheet wall thickness (stylised, thicker than real)
XW = W / 2 - 0.025 - WT / 2   # wall centre x
DOOR_W, DOOR_H = 2.5, 2.05    # opening
LEAF_W = DOOR_W / 2 - 0.015
FLOOR_H = 0.12
Y0, Y1 = -D / 2, D / 2        # front / back


def wall_height(y):
    return HF + (HB - HF) * (y - Y0) / (Y1 - Y0)


def side_wall(m, sx, paint, rnd):
    # trapezoid in (y, z), extruded along X: poly given as (px=y, pz=z) for extrude_xz, rotated so px -> world Y
    poly = [(Y0, 0.0), (Y1, 0.0), (Y1, HB), (Y0, HF)]
    m.extrude_xz(poly, -WT / 2, WT / 2, paint, M=T(sx, 0, 0) @ R(90, 'Z'))
    # vertical corrugation ribs on the outside face
    n = 15
    for i in range(n):
        y = Y0 + 0.25 + (D - 0.5) * i / (n - 1)
        h = wall_height(y) - 0.12
        mat = 'MP_Rust' if rnd.random() < 0.2 else paint
        m.box(0.03, 0.06, h - 0.10, mat, at=(sx + math.copysign(WT / 2 + 0.012, sx), y, 0.10), base=True)
    # rust skirt along the bottom
    m.box(WT + 0.012, D - 0.2, 0.22, 'MP_Rust', at=(sx, 0, 0.0), base=True)


def unit(paint, seed, open_deg=0.0, stuff=False, rust_level=0.2):
    rnd = random.Random(seed)
    m = mp.Mesh()
    # floor slab (concrete) with a small front lip
    m.box(W - 0.05, D + 0.25, FLOOR_H, 'MP_Concrete', at=(0, -0.125, 0), base=True)
    side_wall(m, -XW, paint, rnd)
    side_wall(m, XW, paint, rnd)
    # back wall with ribs
    m.box(2 * XW - WT, WT, HB, paint, at=(0, Y1 - WT / 2, 0), base=True)
    for i in range(7):
        x = -XW + 0.35 + (2 * XW - 0.7) * i / 6
        m.box(0.06, 0.03, HB - 0.25, paint, at=(x, Y1 + 0.012, 0.10), base=True)
    # front frame: header above the door, two piers
    pier = (2 * XW - DOOR_W) / 2
    for s in (-1, 1):
        m.box(pier + WT, WT, HF, paint, at=(s * (DOOR_W / 2 + pier / 2), Y0 + WT / 2, 0), base=True)
    m.box(2 * XW + WT, WT, HF - DOOR_H, paint, at=(0, Y0 + WT / 2, DOOR_H), base=True)
    m.box(DOOR_W + 0.1, 0.08, 0.08, 'MP_Metal_Dark', at=(0, Y0 - 0.02, DOOR_H), base=True)              # door lintel angle
    # roof: one sloped sheet with overhang, plus a rust patch and a dented tar-paper strip
    slope = math.atan2(HF - HB, D)
    roof_len = math.hypot(D, HF - HB) + 0.45
    rz = (HF + HB) / 2 + 0.04
    RM = T(0, -0.15, rz) @ R(-math.degrees(slope), 'X')
    m.box(W - 0.02, roof_len, 0.05, paint, M=RM)
    for _ in range(3 if rust_level > 0.3 else 1):
        m.box(rnd.uniform(0.5, 1.2), rnd.uniform(0.6, 1.4), 0.02, 'MP_Rust',
              M=RM @ T(rnd.uniform(-0.8, 0.8), rnd.uniform(-1.8, 1.8), 0.03))
    m.box(W - 0.02, 0.06, 0.10, 'MP_Metal_Dark', M=RM @ T(0, -roof_len / 2 + 0.03, -0.05))                # front drip edge
    # number plate above the door (white with a dark stripe)
    m.box(0.36, 0.02, 0.18, 'MP_White', at=(0.6, Y0 - 0.01, DOOR_H + 0.12), base=True)
    m.box(0.26, 0.022, 0.05, 'MP_Metal_Black', at=(0.6, Y0 - 0.012, DOOR_H + 0.18), base=True)
    # wear on the front piers
    for s in (-1, 1):
        if rnd.random() < 0.5 + rust_level:
            m.box(pier * 0.7, WT + 0.01, rnd.uniform(0.3, 0.9), 'MP_Rust', at=(s * (DOOR_W / 2 + pier / 2), Y0 + WT / 2, 0.0), base=True)
    if stuff:
        # tyre stack, shelf with cans, a jerrycan - read through the open door
        for i in range(3):
            m.lathe([(0.20, 0.0), (0.32, 0.03), (0.33, 0.10), (0.32, 0.17), (0.20, 0.20), (0.0, 0.20)], 8, 'MP_Metal_Black',
                    M=T(-0.85, 1.6, FLOOR_H + 0.205 * i))
        m.box(1.4, 0.35, 0.03, 'MP_Wood', at=(0.4, Y1 - 0.25, 1.30), base=True)
        m.box(1.4, 0.35, 0.03, 'MP_Wood', at=(0.4, Y1 - 0.25, 0.70), base=True)
        for xx in (-0.28, 1.08):
            m.box(0.04, 0.35, 1.40, 'MP_Wood_Dark', at=(xx, Y1 - 0.25, FLOOR_H), base=True)
        for i, c in enumerate(('MP_Red', 'MP_Teal', 'MP_Yellow', 'MP_Metal_Grey')):
            m.cyl(0.07, 0.20, 6, c, at=(-0.05 + 0.3 * i, Y1 - 0.25, 1.33))
        m.bevel_box(0.20, 0.45, 0.45, 0.04, 'MP_Red', at=(0.9, 0.6, FLOOR_H), base=True)
        m.box(1.2, 0.8, 0.01, 'MP_Concrete_Stain', at=(0, -0.6, FLOOR_H), base=True)                     # oil stain
    leaves = []
    for side in (-1, 1):
        lm = mp.Mesh()
        hinge_x = side * DOOR_W / 2
        cx = hinge_x - side * (LEAF_W / 2 + 0.01)
        y = Y0 - 0.03
        lm.box(LEAF_W, 0.035, DOOR_H - 0.06, paint, at=(cx, y, FLOOR_H - 0.06), base=True)
        for z in (0.45, 1.15, 1.75):                                                                 # stiffener ribs
            lm.box(LEAF_W - 0.12, 0.05, 0.06, paint, at=(cx, y - 0.01, z), base=True)
        lm.box(LEAF_W, 0.04, 0.22, 'MP_Rust', at=(cx, y - 0.002, FLOOR_H - 0.06), base=True)          # rusty bottom
        for z in (0.35, DOOR_H - 0.35):                                                              # hinges
            lm.cyl(0.03, 0.16, 6, 'MP_Metal_Dark', at=(hinge_x, y - 0.03, z))
        if side == 1:                                                                                # hasp + padlock
            lm.box(0.16, 0.05, 0.05, 'MP_Metal_Grey', at=(cx - LEAF_W / 2 + 0.06, y - 0.04, 1.0), base=True)
            if open_deg == 0.0:
                lm.bevel_box(0.08, 0.04, 0.10, 0.015, 'MP_Metal_Grey', at=(cx - LEAF_W / 2 + 0.01, y - 0.07, 0.88), base=True)
        else:
            lm.box(0.05, 0.05, 0.25, 'MP_Metal_Grey', at=(cx + LEAF_W / 2 - 0.06, y - 0.03, 0.9), base=True)    # handle
        leaves.append((f'Leaf{"L" if side < 0 else "R"}', lm, (hinge_x, y), side * open_deg))
    return m, leaves


def add(name, paint, seed, open_deg=0.0, stuff=False, rust_level=0.2, notes=''):
    m, leaves = unit(paint, seed, open_deg, stuff, rust_level)
    root = fam.make_object(name, m)
    objs = [root]
    for suffix, lm, hinge, rot in leaves:
        c = fam.make_object(f'{name}_Door{suffix}', lm, parent=root, pivot=(hinge[0], hinge[1], 0.0))
        c.rotation_euler.z = math.radians(rot)
        objs.append(c)
    fam.add_asset(name, objs, budget=1500, tile_length_m=W, depth_m=D, opening_m=[DOOR_W, DOOR_H],
                  notes=notes + ' Doors open outwards: left leaf -Z, right leaf +Z rotation (Blender), up to ~110 deg.')


add('GR_MetalGarage_Green', 'MP_Paint_Green', 1, notes='Closed, padlocked.')
add('GR_MetalGarage_Blue', 'MP_Paint_Blue', 2, notes='Closed, padlocked.')
add('GR_MetalGarage_Rust', 'MP_Paint_Rust', 3, rust_level=0.6, notes='Closed, heavily rusted.')
add('GR_MetalGarage_Open', 'MP_Paint_Blue', 4, open_deg=105.0, stuff=True, notes='Doors open 105 deg, tyres/shelf/jerrycan inside.')

fam.finish(lineup_gap=0.6, render=False)
if not fam.args.no_render:
    fam.render_previews(camera=[('01_units_front.png', 270, 8, (1800, 800), 50),
                                ('02_units_three_quarter.png', 235, 20, (1800, 1000), 50)], person_at=(-1.0, -3.6, 0))
    # a row of 6 units as they will be placed in the map, plus a close look into the open garage
    order = ['GR_MetalGarage_Green', 'GR_MetalGarage_Rust', 'GR_MetalGarage_Blue', 'GR_MetalGarage_Open',
             'GR_MetalGarage_Green', 'GR_MetalGarage_Rust']
    for i, n in enumerate(order):
        fam.place_copy(n, i * W, 30.0)
    shown = fam.showcase_only(True)
    fam.render_previews(camera=[('03_row_three_quarter.png', 240, 16, (1800, 1000), 45),
                                ('04_row_eye_level.png', 285, 4, (1800, 900), 35)], frame_objects=shown, person_at=(4.5, 25.5, 0))
