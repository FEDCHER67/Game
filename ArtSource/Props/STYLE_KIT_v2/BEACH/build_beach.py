"""STYLE_KIT_v2 / BEACH: Fedya's beach sheet in the bible's clean toy-town language.

Blender 5.2, from repo root:
  & 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup \
    --python ArtSource/Props/STYLE_KIT_v2/BEACH/build_beach.py -- --revision 1

Shared helpers are imported, never changed. All writes remain inside BEACH/.
--check-only validates without exporting; --preview-existing adds missing previews
after verifying every geometry hash against an existing revision. --force has the
usual kit meaning, but use a NEW revision for any model change.
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beach_support import BeachFamily, bevel, beam, cross, load_preview_assets, palette_fingerprint, sk
from mathutils import Vector

fam = BeachFamily('SK2-BEACH-001', __file__, 'BE_', budget=(1, 1500),
                  description='17 beach props; STYLE_BIBLE_v2b and REF_FEDYA_MASTER_v02_city_beach')


def umbrella(col):
    m = sk.Mesh()
    m.lathe([(0, 0), (0.18, 0), (0.18, 0.10), (0.07, 0.18),
             (0.06, 2.97), (0, 2.97)], 12, 'wood', normals='soft_weighted', member=0.12, name='pole')
    canopy = sk.Mesh()
    # Closed cloth volume, 10-12 cm thick. Eight broad stripes, no separate ribs or texture.
    profile = [(0, 2.88), (0.35, 2.88), (0.95, 2.64), (1.5, 2.37),
               (1.5, 2.48), (0.95, 2.75), (0.35, 3.0), (0, 3.0)]
    canopy.lathe(profile, 16, col, normals='soft', member=0.10, name='canopy')
    canopy.fcol = [col if (i % 16) // 2 % 2 == 0 else 'chalk' for i in range(len(canopy.faces))]
    m.merge(canopy)
    m.lathe([(0, 2.99), (0.09, 2.99), (0.09, 3.06), (0.05, 3.10), (0, 3.10)],
            8, 'wood', normals='soft', member=0.10, name='finial')
    return m


def lounger():
    back = sk.T(0, 0.54, 0.78) @ sk.R(55, 'X')
    # One broad sewn head band, integrated into the palette faces rather than a thin decal shell.
    mesh = sk.Mesh()
    bevel(mesh, (0.76, 0.22, 0.10), 'cobalt', at=(0, 0.29, 0), M=back,
          radius=0.025, name='head_band')
    # Replace the upper part of the white back with the coloured band, without overlapping coplanar faces.
    m = sk.Mesh()
    bevel(m, (0.76, 1.22, 0.10), 'chalk', at=(0, -0.24, 0.43), radius=0.025, name='seat')
    bevel(m, (0.76, 0.64, 0.10), 'chalk', at=(0, -0.12, 0), M=back, radius=0.025, name='backrest')
    m.merge(mesh)
    for x in (-0.43, 0.43):
        beam(m, (x, -0.87, 0.35), (x, 0.40, 0.35), 0.10, 0.10, 'wood', name='seat_rail')
        beam(m, (x, 0.26, 0.37), (x, 0.85, 1.17), 0.10, 0.10, 'wood', name='back_rail')
        beam(m, (x, -0.66, 0.08), (x, -0.51, 0.38), 0.10, 0.10, 'wood', name='front_leg')
        beam(m, (x, 0.73, 0.08), (x, 0.30, 0.41), 0.10, 0.10, 'wood', name='rear_leg')
    for y in (-0.66, 0.73):
        beam(m, (-0.50, y, 0.05), (0.50, y, 0.05), 0.10, 0.10, 'wood', name='ground_foot')
    return m


def side_table():
    m = sk.Mesh()
    m.lathe([(0, 0), (0.28, 0), (0.31, 0.04), (0.28, 0.10),
             (0.10, 0.16), (0.08, 0.53), (0.16, 0.55), (0, 0.55)], 12,
            'wood', normals='soft_weighted', member=0.16, name='pedestal')
    m.lathe([(0, 0.53), (0.38, 0.53), (0.42, 0.56), (0.42, 0.63),
             (0.38, 0.66), (0, 0.66)], 16, 'chalk', normals='soft_weighted', member=0.13, name='tabletop')
    return m


def lifeguard_tower():
    m = sk.Mesh()
    # Broad four-legged observation platform; open undercroft, rear ladder, cloth sunshade.
    for x in (-0.76, 0.76):
        for y in (-0.66, 0.66):
            bevel(m, (0.36, 0.36, 0.12), 'wood', at=(x * 1.2, y * 1.2, 0.06),
                  segments=1, radius=0.03, name='foot')
            beam(m, (x * 1.2, y * 1.2, 0.12), (x, y, 2.0), 0.14, 0.14, 'wood', name='leg')
            top = 3.36 if fam.args.revision == 1 else 3.39 - math.tan(math.radians(7)) * y - 0.055 / math.cos(math.radians(7))
            beam(m, (x, y, 2.02), (x, y, top), 0.12, 0.12, 'wood', name='shade_post')
    bevel(m, (2.0, 1.8, 0.18), 'wood', at=(0, 0, 1.98), radius=0.04, name='platform')
    for y in (-0.72, 0.72):
        beam(m, (-0.85, y, 2.75), (0.85, y, 2.75), 0.12, 0.12, 'wood', name='rail')
    beam(m, (-0.85, -0.72, 2.75), (-0.85, 0.72, 2.75), 0.12, 0.12, 'wood', name='rail')
    beam(m, (0.85, -0.72, 2.75), (0.85, 0.72, 2.75), 0.12, 0.12, 'wood', name='rail')
    # One diagonal brace is the template asymmetry, with no random crookedness.
    beam(m, (-0.90, 0.76, 0.3), (0.76, 0.66, 1.80), 0.12, 0.12, 'wood', name='rear_brace')
    for x in (-0.38, 0.38):
        beam(m, (x, 1.48, 0.14), (x, 0.70, 2.05), 0.12, 0.12, 'wood', name='ladder_rail')
    for i in range(6):
        z = 0.33 + i * 0.29
        y = 1.48 + (z - 0.14) / 1.91 * (0.70 - 1.48)
        beam(m, (-0.4, y, z), (0.4, y, z), 0.10, 0.10, 'wood', name='ladder_rung')
    bevel(m, (2.20, 2.0, 0.12), 'red', radius=0.04,
          name='canvas_sunshade', M=sk.T(0, 0, 3.39) @ sk.R(-7, 'X'))
    bevel(m, (0.76, 0.12, 0.76), 'chalk', at=(0, -0.84, 2.59), radius=0.035, name='sign')
    cross(m, 0.52, 0.06, 'red', (0, -0.94, 2.59))
    return m


def coffee_kiosk():
    m = sk.Mesh()
    bevel(m, (2.90, 2.1, 0.18), 'grey', at=(0, 0, 0.09), radius=0.04, name='plinth')
    for x in (-1.28, 1.28):
        bevel(m, (0.16, 1.85, 2.48), 'teal', at=(x, 0.08, 1.42), segments=1, radius=0.03, name='side_wall')
    bevel(m, (2.6, 0.16, 2.48), 'teal', at=(0, 0.93, 1.42), segments=1, radius=0.03, name='back_wall')
    bevel(m, (2.6, 0.16, 0.86), 'teal', at=(0, -0.82, 0.61), segments=1, radius=0.03, name='front_apron')
    bevel(m, (2.6, 0.16, 0.36), 'teal', at=(0, -0.82, 2.50), segments=1, radius=0.03, name='header')
    for x in (-1.25, 1.25):
        beam(m, (x, -0.85, 0.18), (x, -0.85, 2.68), 0.12, 0.12, 'chalk', name='corner_trim')
    bevel(m, (2.95, 0.62, 0.14), 'chalk', at=(0, -0.96, 1.09), radius=0.03, name='counter')
    bevel(m, (2.85, 2.08, 0.16), 'grey', at=(0, 0.08, 2.73), radius=0.04, name='flat_roof')
    # Chalk roof edge separates grey from the teal booth, bible 2.6 flat-roof rule.
    for y in (-0.93, 1.09):
        beam(m, (-1.4, y, 2.80), (1.4, y, 2.80), 0.10, 0.10, 'chalk', name='roof_trim')
    for x in (-1.4, 1.4):
        beam(m, (x, -0.93, 2.80), (x, 1.09, 2.80), 0.10, 0.10, 'chalk', name='roof_trim')
    for i in range(6):
        x = -1.2 + i * 0.48
        # Closed adjoining canopy strips, not thin overlaid stripe decals.
        m.prism([(-0.85, 2.58), (-1.70, 2.30), (-1.70, 2.43), (-0.85, 2.71)], 0.48,
                'teal' if i % 2 == 0 else 'chalk', M=sk.T(x, 0, 0) @ sk.R(90, 'Z'),
                normals='flat', member=0.13, name='awning')
    # Cup silhouette on an off-centre sign, no text or miniature decoration.
    bevel(m, (0.88, 0.12, 0.76), 'chalk', at=(-0.48, -0.75, 3.16), radius=0.035, name='coffee_sign')
    m.prism([(-0.22, -0.18), (0.17, -0.18), (0.23, 0.17), (-0.28, 0.17)], 0.06,
            'teal', M=sk.T(-0.50, -0.85, 3.12), member=0.06, name='cup_icon')
    m.lathe_loop([(0.09, 0), (0.16, 0), (0.16, 0.06), (0.09, 0.06)], 8,
                 'teal', M=sk.T(-0.26, -0.85, 3.16) @ sk.R(90, 'X'),
                 normals='soft', member=0.06, name='cup_handle')
    beam(m, (-0.76, -0.89, 2.91), (-0.17, -0.89, 2.91), 0.06, 0.06, 'teal', name='saucer_icon')
    beam(m, (-0.54, -0.89, 3.35), (-0.48, -0.89, 3.46), 0.06, 0.06, 'teal', name='steam_icon')
    return m


def shower_toilet():
    m = sk.Mesh()
    bevel(m, (3.65, 2.0, 0.20), 'grey', at=(0, 0, 0.10), radius=0.04, name='plinth')
    bevel(m, (3.45, 1.84, 2.58), 'chalk', at=(0, 0, 1.49), radius=0.05, name='cabin_block')
    bevel(m, (3.75, 2.14, 0.18), 'grey', at=(0, 0, 2.83), radius=0.04, name='roof')
    for y in (-1.02, 1.02):
        beam(m, (-1.84, y, 2.93), (1.84, y, 2.93), 0.10, 0.10, 'chalk', name='roof_trim')
    for x in (-1.84, 1.84):
        beam(m, (x, -1.02, 2.93), (x, 1.02, 2.93), 0.10, 0.10, 'chalk', name='roof_trim')
    for x in (-0.88, 0.88):
        bevel(m, (1.05, 0.12, 2.12), 'cobalt', at=(x, -0.99, 1.30), radius=0.03, name='door')
        bevel(m, (0.67, 0.06, 0.63), 'chalk', at=(x, -1.09, 1.91),
              radius=0.025, segments=1, name='pictogram_board')
        beam(m, (x + 0.32, -1.13, 1.03), (x + 0.32, -1.13, 1.21), 0.06, 0.06,
             'chalk', name='door_handle')
    # Toilet profile (tank, bowl and pedestal), no person pictograms.
    m.prism([(-0.21, 0.21), (-0.07, 0.21), (-0.07, 0.04), (0.20, 0.04),
             (0.16, -0.11), (0.02, -0.17), (0.02, -0.24), (-0.12, -0.24),
             (-0.12, -0.09), (-0.21, -0.09)], 0.06, 'grey',
            M=sk.T(-0.88, -1.16, 1.91), member=0.06, name='toilet_icon')
    # The shower symbol is an elbow and broad shower bell with three drops.
    beam(m, (0.76, -1.16, 1.96), (0.76, -1.16, 2.10), 0.06, 0.06, 'grey', name='shower_icon')
    beam(m, (0.76, -1.16, 2.10), (0.97, -1.16, 2.10), 0.06, 0.06, 'grey', name='shower_icon')
    m.prism([(-0.16, -0.04), (0.16, -0.04), (0.09, 0.07), (-0.09, 0.07)], 0.06,
            'grey', M=sk.T(0.98, -1.16, 1.97), member=0.06, name='shower_icon')
    for x in (0.85, 0.98, 1.11):
        beam(m, (x, -1.16, 1.79), (x, -1.16, 1.86), 0.06, 0.06, 'grey', name='water_drop_icon')
    # Actual shower fitting on the right side, with the pipe fully attached to the block.
    m.tube([(1.75, 0.18, 0.40), (1.75, 0.18, 2.31), (1.98, 0.18, 2.40), (2.12, 0.18, 2.35)],
           [0.06] * 4, 8, 'grey', normals='soft', member=0.12, name='shower_pipe')
    m.lathe([(0, 0), (0.18, 0), (0.20, 0.06), (0.09, 0.14), (0, 0.14)],
            12, 'grey', M=sk.T(2.10, 0.18, 2.22), normals='soft_weighted', member=0.14, name='shower_head')
    return m


def pier_deck():
    """Exactly 2 x 2 m; join along Y at 2 m. No overhanging parts at module boundaries."""
    m = sk.Mesh()
    for i in range(8):
        y = -1 + (i + 0.5) * 0.25
        bevel(m, (2.0, 0.234, 0.12), 'wood.light', at=(0, y, 0.22),
              radius=0.018, segments=1, name='deck_plank')
    for x in (-0.76, 0.76):
        bevel(m, (0.16, 2.0, 0.16), 'wood.dark', at=(x, 0, 0.08),
              radius=0.018, segments=1, name='underbeam')
    return m


def pier_end():
    """T end: 6 x 2 m head with a 2 x 1 m stem. Stem extends towards +Y (shore)."""
    m = sk.Mesh()
    for i in range(8):
        bevel(m, (6, 0.234, 0.12), 'wood.light', at=(0, -1 + (i + 0.5) * 0.25, 0.22),
              radius=0.018, segments=1, name='head_plank')
    for i in range(4):
        bevel(m, (2, 0.234, 0.12), 'wood.light', at=(0, 1 + (i + 0.5) * 0.25, 0.22),
              radius=0.018, segments=1, name='stem_plank')
    for x in (-2.7, -0.76, 0.76, 2.7):
        bevel(m, (0.16, 2.0 if abs(x) > 1 else 3.0, 0.16), 'wood.dark',
              at=(x, 0 if abs(x) > 1 else 0.5, 0.08), radius=0.018,
              segments=1, name='underbeam')
    return m


def pier_post():
    m = sk.Mesh()
    if fam.args.revision >= 3:
        # Short chunky mooring bollard: 70 cm overall, with a 52 cm cap.
        # Mid-grey carries the mass; only the shallow cap uses the darker ramp.
        m.lathe([(0, 0), (0.22, 0), (0.24, 0.04), (0.24, 0.10),
                 (0.18, 0.14), (0.18, 0.54), (0, 0.54)],
                10, 'grey', normals='soft_weighted', member=0.36, name='bollard_body')
        m.lathe([(0, 0.54), (0.23, 0.54), (0.26, 0.58), (0.26, 0.66),
                 (0.22, 0.70), (0, 0.70)],
                10, 'grey.dark', normals='soft_weighted', member=0.16, name='bollard_cap')
        return m
    m.lathe([(0, 0), (0.18, 0), (0.18, 0.10), (0.15, 0.14), (0.15, 0.90),
             (0.21, 0.90), (0.23, 0.94), (0.23, 1.05), (0.19, 1.10), (0, 1.10)],
            10, 'ink', normals='soft_weighted', member=0.30, name='bollard')
    return m


def flag_pole():
    m = sk.Mesh()
    m.lathe([(0, 0), (0.24, 0), (0.24, 0.10), (0.10, 0.18), (0.06, 3.98), (0, 3.98)],
            12, 'wood', normals='soft_weighted', member=0.12, name='flag_pole')
    # A single broad, gently bent pennant; 10 cm volume, no cloth simulation or thin plane.
    stations = [(0.06, 0, 3.72, 0.70), (0.52, 0.06, 3.67, 0.51), (1.13, -0.04, 3.57, 0.10)]
    verts = []
    for x, y, z, h in stations:
        verts += [(x, y - 0.05, z - h / 2), (x, y + 0.05, z - h / 2),
                  (x, y + 0.05, z + h / 2), (x, y - 0.05, z + h / 2)]
    faces = [(3, 2, 1, 0)]
    for i in range(2):
        a, b = 4 * i, 4 * (i + 1)
        faces += [(a + k, a + (k + 1) % 4, b + (k + 1) % 4, b + k) for k in range(4)]
    faces.append((8, 9, 10, 11))
    m.shell(verts, faces, 'cobalt', normals='flat', member=0.10, name='blue_flag')
    return m


def frond(m, centre, angle, length, rise, drop, width, thickness):
    """One closed, broad leaf with a raised centre. Five deliberate stations, no small leaflet noise.
    Its small end caps are thickness geometry, not visible foliage facets (as with the kit's tubes).
    """
    d = Vector((math.cos(angle), math.sin(angle), 0))
    side = Vector((-d.y, d.x, 0))
    origin = Vector(centre)
    rings = []
    for t, w, z in ((0, width * 0.46, 0), (0.22, width * 0.85, rise),
                    (0.52, width, rise * 0.36), (0.81, width * 0.57, -drop * 0.48),
                    (1, 0.09, -drop)):
        p = origin + d * (length * t) + Vector((0, 0, z))
        rings += [tuple(p - side * w / 2), tuple(p + Vector((0, 0, thickness))),
                  tuple(p + side * w / 2), tuple(p - Vector((0, 0, thickness)))]
    faces = [(3, 2, 1, 0)]
    for i in range(4):
        a, b = 4 * i, 4 * (i + 1)
        faces += [(a + k, a + (k + 1) % 4, b + (k + 1) % 4, b + k) for k in range(4)]
    faces.append((16, 17, 18, 19))
    # Cross-section goes left -> up -> right -> down, clockwise seen from +d, so reverse winding.
    faces = [tuple(reversed(f)) for f in faces]
    m.shell(rings, faces, 'leaf.light', normals='smooth', kind='organic', member=thickness,
            facet=False, name='frond')


def palm(variant, small=False):
    m = sk.Mesh()
    # A = high, shallow fan bending right. B = squat, wider-leaf fan bending left.
    if small:
        trunk_h, radius, length, rise, drop, width, thick, count, bend = 1.55, 0.10, 1.12, 0.27, 0.52, 0.43, 0.07, 8, 0.10
    elif variant == 'A':
        trunk_h, radius, length, rise, drop, width, thick, count, bend = 6.38, 0.15, 3.12, 0.55, 1.70, 0.95, 0.08, 10, 0.46
    else:
        trunk_h, radius, length, rise, drop, width, thick, count, bend = 5.0, 0.15, 2.44, 0.42, 0.90, 1.04, 0.08, 8, -0.37
    # Twelve clean segments with a subtle geometric collar, rather than ring textures/noise.
    pts, radii = [(0, 0, 0), (0, 0, 0.22 if small else 0.4)], [radius * 1.3, radius]
    for i in range(1, 7):
        t = i / 6
        pts.append((bend * t * t, 0, (0.22 if small else 0.4) + t * (trunk_h - (0.22 if small else 0.4))))
        radii.append(radius * (1 - 0.15 * t))
    m.tube(pts, radii, 8, 'wood.light', normals='soft', kind='organic', member=2 * min(radii), name='trunk',
           cols_fn=lambda band, k: 'wood.dark' if band == 0 else None)
    hub = (bend, 0, trunk_h)
    for i in range(count):
        # Exactly one long leaf, a deliberate template asymmetry shared by both variants.
        factor = 1.035 if i == 1 else 1.0
        a = math.tau * i / count + (0.17 if variant == 'B' else 0)
        frond(m, hub, a, length * factor, rise, drop, width, thick)
    return m


def planter_palm():
    m = sk.Mesh()
    m.lathe([(0, 0), (0.42, 0), (0.48, 0.08), (0.60, 0.55), (0.65, 0.58),
             (0.65, 0.68), (0.57, 0.71), (0.53, 0.59), (0, 0.59)], 16,
            'chalk', normals='soft_weighted', member=0.12, name='planter')
    m.merge(palm('B', small=True), sk.T(0, 0, 0.59))
    return m


def rock(variant):
    m = sk.Mesh()
    if variant == 'A':
        prims = [('ell', (0, 0, 0.39), (0.85, 0.66, 0.52)),
                 ('ell', (0.44, 0.10, 0.30), (0.48, 0.47, 0.34))]
        fit = (-0.90, 1.0, -0.67, 0.72, 0, 0.86)
        centre = (0, 0, 0.39)
    else:
        prims = [('ell', (0, 0, 0.30), (0.55, 0.52, 0.38)),
                 ('ell', (-0.24, 0.13, 0.25), (0.44, 0.40, 0.30))]
        fit = (-0.71, 0.61, -0.53, 0.62, 0, 0.65)
        centre = (0, 0, 0.30)
    m.blob(prims, 'grey', centre=centre, freq=3, k=0.30, zcut=0.05, kcut=0.12,
           fit=fit, grad=None, name='beach_rock')
    return m


BUILD = {
    'BE_Umbrella_Red': lambda: umbrella('red'),
    'BE_Umbrella_Blue': lambda: umbrella('cobalt'),
    'BE_Umbrella_Orange': lambda: umbrella('terracotta'),
    'BE_Lounger': lounger, 'BE_SideTable': side_table,
    'BE_LifeguardTower': lifeguard_tower, 'BE_Kiosk_Coffee': coffee_kiosk,
    'BE_ShowerToilet': shower_toilet,
    'BE_Pier_Deck': pier_deck, 'BE_Pier_End': pier_end, 'BE_Pier_Post': pier_post,
    'BE_FlagPole': flag_pole, 'BE_Palm_A': lambda: palm('A'), 'BE_Palm_B': lambda: palm('B'),
    'BE_Planter_Palm': planter_palm, 'BE_Rock_A': lambda: rock('A'), 'BE_Rock_B': lambda: rock('B'),
}
BUDGETS = {'BE_Umbrella_Red': 600, 'BE_Umbrella_Blue': 600, 'BE_Umbrella_Orange': 600,
           'BE_Lounger': 1000, 'BE_SideTable': 400, 'BE_LifeguardTower': 1500, 'BE_Kiosk_Coffee': 1500,
           'BE_ShowerToilet': 1500, 'BE_Pier_Deck': 800, 'BE_Pier_End': 1000, 'BE_Pier_Post': 300,
           'BE_FlagPole': 300, 'BE_Palm_A': 900, 'BE_Palm_B': 900, 'BE_Planter_Palm': 900,
           'BE_Rock_A': 300, 'BE_Rock_B': 300}
ROWS = [['BE_Umbrella_Red', 'BE_Umbrella_Blue', 'BE_Umbrella_Orange', 'BE_Lounger', 'BE_SideTable'],
        ['BE_LifeguardTower', 'BE_Kiosk_Coffee', 'BE_ShowerToilet'],
        ['BE_Pier_Deck', 'BE_Pier_End', 'BE_Pier_Post', 'BE_FlagPole'],
        ['BE_Palm_A', 'BE_Palm_B', 'BE_Planter_Palm', 'BE_Rock_A', 'BE_Rock_B']]

for row, names in enumerate(ROWS):
    for name in names:
        fam.add_asset(name, BUILD[name], budget=(1, BUDGETS[name]), max_swatches=3, row=row,
                      source_reference='ArtSource/References/Map/REF_FEDYA_MASTER_v02_city_beach.png',
                      kind='beach-only palm' if 'Palm' in name else 'beach prop',
                      near_player_bevel='2-segment longitudinal bevels + weighted normals; small pier plank end bevels 1 segment')


_kit_validate = fam._validate_asset


def validate_beach(a):
    r = _kit_validate(a)
    mesh = fam.meshes[a['name']]
    checks = r['checks']
    checks['exactly_one_material_no_patterns'] = all(len(o.data.materials) == 1 for o in a['objects'])
    checks['no_animation'] = all(o.animation_data is None and o.data.animation_data is None for o in a['objects'])
    checks['long_structural_members_ge_0.10_m'] = all(
        sh['member'] >= 0.10 - 1e-6 for sh in mesh.shells
        if sh['member'] is not None and sh['kind'] == 'hard' and
        max(max(v[i] for v in mesh.verts[sh['v0']:sh['v1']]) - min(v[i] for v in mesh.verts[sh['v0']:sh['v1']])
            for i in range(3)) > 1.0 + 1e-5)
    if a['name'] == 'BE_Pier_Deck':
        checks['module_exactly_2m_x_2m'] = r['size_m'][:2] == [2.0, 2.0]
    if a['name'] == 'BE_Pier_End':
        checks['T_head_6m_stem_2m'] = r['size_m'][:2] == [6.0, 3.0]
    if fam.args.revision >= 3:
        checks['no_near_black_surface_swatches'] = not any(s.startswith('ink') for s in mesh.fcol)
        if a['name'] == 'BE_Pier_Post':
            checks['bollard_height_0_60_to_0_75_m'] = 0.60 <= r['size_m'][2] <= 0.75
            checks['bollard_mid_grey_body_darker_cap'] = set(mesh.fcol) == {'grey', 'grey.dark'}
    if a['name'] == 'BE_LifeguardTower' and fam.args.revision >= 2:
        posts = [sh for sh in mesh.shells if sh['name'] == 'shade_post']
        clearances = []
        for sh in posts:
            points = mesh.verts[sh['v0']:sh['v1']]
            y = sum(v[1] for v in points) / len(points)
            shade_underside = 3.39 - math.tan(math.radians(7)) * y - 0.06 / math.cos(math.radians(7))
            clearances.append(max(v[2] for v in points) - shade_underside)
        checks['sloped_shade_supported_at_all_four_posts'] = len(posts) == 4 and all(0 <= d <= 0.02 for d in clearances)
    if a['name'] in ('BE_Palm_A', 'BE_Palm_B'):
        fr = [sh for sh in mesh.shells if sh['name'] == 'frond']
        heights = [v[2] for sh in fr for v in mesh.verts[sh['v0']:sh['v1']]]
        checks['palm_8_to_10_fronds'] = 8 <= len(fr) <= 10
        checks['palm_frond_thickness_ge_0.06_m'] = all(sh['member'] >= 0.06 for sh in fr)
        checks['palm_height_5_5_to_8_m'] = 5.5 <= r['size_m'][2] <= 8.0
        checks['palm_crown_width_0_9h_within_15pct'] = abs(max(r['size_m'][:2]) - 0.9 * r['size_m'][2]) <= 0.15 * 0.9 * r['size_m'][2]
        checks['palm_fronds_base_ge_4m'] = min(heights) >= 4.0
        r['foliage_facet_method'] = 'Five broad leaf stations. Small end caps excluded as thickness faces, like tube caps; no leaflet detail.'
    r['all_checks_passed'] = all(checks.values())
    return r


fam._validate_asset = validate_beach
NOTES = ['Shared _lib, bible, other families, Assets/ and WORK_SYNC.md are read-only for this task.',
         'One Look_Palette_v2 material per FBX; the existing atlas is packed in the master .blend, never regenerated.',
         'Orange canopy = terracotta (bible 8.2), blue = cobalt, white = chalk; no additional colours.',
         'Palm fan: 8 / 10 solid broad fronds, >= 6 cm thickness, wood.light trunk. Use only near beach/pier.',
         'Pier: local deck top z=0.28 m. 2m tiling deck, 6m T head with a 2m stem; post is a separate reusable prop.',
         'Preview-only reference SQUARE/TREES/BUSHES objects are not exported or saved in the master.',
         'Cycles previews use the shared kit studio: 45-degree sun, trilight ambient, Standard view, no tonemapping.',
         'LOD1 and Unity integration are outside the requested beach delivery.']
if fam.args.revision >= 3:
    NOTES += ['v03: 0.70m mooring bollard, grey body / grey.dark cap; no ink surfaces in any BEACH asset.',
              'v03 beach layout: six bollards, four on the stem and two on the T head; no added pilings.',
              'v03 style-neighbours sheet includes the bollard beside the lounger for scale comparison.']

if '--check-only' in sys.argv:
    results = {a['name']: fam._validate_asset(a) for a in fam.assets}
    for name, r in results.items():
        print(name, r['triangles'], r['size_m'], [k for k, v in r['checks'].items() if not v])
    if not all(r['all_checks_passed'] for r in results.values()):
        raise RuntimeError('BEACH check-only validation failed')
    print('BEACH_CHECK_ONLY_PASS')
    sys.exit(0)

if fam.preview_existing:
    report = json.loads(fam.json_path.read_text(encoding='utf-8'))
    if not fam.blend_path.is_file() or not report['all_checks_passed']:
        raise RuntimeError('A complete validated model revision is required for --preview-existing')
    for a in fam.assets:
        r = fam._validate_asset(a)
        if r['geometry_sha1'] != report['assets'][a['name']]['geometry_sha1'] or not r['all_checks_passed']:
            raise RuntimeError(f"Source no longer matches {fam.rev}: {a['name']}; create a new revision")
else:
    report = fam.finish(lineup_gap=1.3, row_gap=2.0, extra_notes=NOTES)


def lineup():
    objs = []
    for row, names in enumerate(ROWS):
        x = 0
        for name in names:
            r = report['assets'][name]
            x += -r['bounds_min'][0]
            objs += fam.place(name, x, row * 7.2)
            x += r['bounds_max'][0] + 1.5
    return objs


def preview_lineup(fname, samples=None):
    objs = lineup()
    fam.showcase(True)
    st = fam.studio()
    old_samples = st.scene.cycles.samples
    if samples:
        st.scene.cycles.samples = samples
    fam.shot(fname, objs, az=12, el=38, res=(2200, 1500), lens=50, ground='sand')
    st.scene.cycles.samples = old_samples
    fam.clear_showcase()


def beach_scene():
    objs = []
    # The reference's coffee kiosk is LEFT, cabins RIGHT, pier between them.
    objs += fam.place('BE_Kiosk_Coffee', -6.8, 7.0)
    objs += fam.place('BE_ShowerToilet', 6.8, 7.0)
    objs += fam.place('BE_LifeguardTower', -3.5, -1.2)
    for x, y, name in [(-10, 0, 'BE_Umbrella_Red'), (-8, -4.6, 'BE_Umbrella_Blue'),
                       (-13.7, -4.8, 'BE_Umbrella_Orange'), (9.0, -2.4, 'BE_Umbrella_Orange'),
                       (13, 0.6, 'BE_Umbrella_Red'), (13.8, -5, 'BE_Umbrella_Blue')]:
        objs += fam.place(name, x, y)
        for dx in (-0.91, 0.91):
            objs += fam.place('BE_Lounger', x + dx, y - 1.65)
        objs += fam.place('BE_SideTable', x, y - 2.6)
    for x, y, variant in [(-14, 5.2, 'A'), (-10, 9.3, 'B'), (11.5, 8.9, 'A'), (16.5, 3.1, 'B')]:
        objs += fam.place('BE_Palm_' + variant, x, y)
    for x in (-2.1, 2.1):
        objs += fam.place('BE_Planter_Palm', x, 5.5)
        objs += fam.place('BE_FlagPole', x, -4.9)
    for i in range(6):
        objs += fam.place('BE_Pier_Deck', 0, -7 - i * 2)
        if fam.args.revision < 3 and i in (0, 2, 5):
            for x in (-1.05, 1.05):
                parts = fam.place('BE_Pier_Post', x, -7 - i * 2)
                parts[0].location.z = 0.28
                objs += parts
    objs += fam.place('BE_Pier_End', 0, -19.0)
    if fam.args.revision >= 3:
        # Six evenly paired mooring points; bases/caps remain inside the deck edges.
        bollard_positions = [(x, y) for y in (-8, -14) for x in (-0.72, 0.72)]
        bollard_positions += [(-2.55, -19), (2.55, -19)]
        assert len(bollard_positions) == 6
    else:
        bollard_positions = [(x, y) for x in (-2.65, 2.65) for y in (-19.75, -18.3)]
    for x, y in bollard_positions:
        parts = fam.place('BE_Pier_Post', x, y)
        parts[0].location.z = 0.28
        objs += parts
    for x, y, v in [(-16, -7, 'A'), (-14.2, -8.0, 'B'), (16, -8.0, 'A'), (17.7, -7.2, 'B')]:
        objs += fam.place('BE_Rock_' + v, x, y)
    sand = sk.Mesh()
    sand.box(44, 30, 0.10, 'sand', at=(0, 5, -0.05), member=0.10)
    objs.append(fam.proxy('Preview_Sand', sand))
    water = sk.Mesh()
    water.box(66, 34, 0.10, 'water', at=(0, -27, -0.16), member=0.10)
    objs.append(fam.proxy('Preview_Sea', water))
    shallow = sk.Mesh()
    shallow.box(66, 8, 0.10, 'water.light', at=(0, -14, -0.15), member=0.10)
    objs.append(fam.proxy('Preview_Shallow', shallow))
    path = sk.Mesh()
    path.box(2.4, 15, 0.06, 'paving', at=(0, 1.3, 0.025), member=0.06)
    objs.append(fam.proxy('Preview_Path', path))
    # Round bushes in planters use the existing BUSHES shape; they are only dressing, not new beach assets.
    refs = load_preview_assets(fam, 'BUSHES', 'SK2-BUSHES-001_v02.blend', ['BU_Round'])
    root = refs['BU_Round']
    for i, (x, y) in enumerate([(-2.2, 9), (2.2, 9), (-4.7, 7), (4.7, 7), (-7.3, 3.7), (7.3, 3.7)]):
        pot = sk.Mesh()
        pot.lathe([(0, 0), (0.64, 0), (0.75, 0.12), (0.82, 0.47), (0.74, 0.54), (0, 0.54)],
                  12, 'chalk', normals='soft_weighted', member=0.10, name='preview_planter')
        objs.append(fam.proxy('Preview_RoundBushPlanter', pot, x, y))
        ob = root if i == 0 else root.copy()
        if i:
            root.users_collection[0].objects.link(ob)
        ob.location = (x, y, 0.50)
        objs.append(ob)
    return objs


if not fam.args.no_render:
    if fam.want('00_sample_lineup.png'):
        preview_lineup('00_sample_lineup.png', samples=24)
    for name in BUILD:
        fname = f'01_{name}.png'
        if not fam.want(fname):
            continue
        objs = fam.place(name, 0, 0)
        fam.showcase(True)
        fam.shot(fname, objs, az=28, el=16 if 'Palm' in name else 25,
                 res=(1200, 1100), lens=50, ground='sand', pad=1.18)
        fam.clear_showcase()
    if fam.want('02_lineup.png'):
        preview_lineup('02_lineup.png')
    if fam.want('03_beach_reference_top.png') or fam.want('04_beach_eye_level.png'):
        objs = beach_scene()
        # Ground/sea are background dressing, not framing targets. Hide the infinite studio floor
        # here, since it would occlude the water below the sand level.
        framed = [o for o in objs if not o.name.startswith('Preview_')]
        fam.showcase(True)
        fam.shot('03_beach_reference_top.png', framed, az=0, el=63, ortho=True,
                 res=(2000, 1700), ground=None, pad=1.14, sun_az=-35)
        fam.shot('04_beach_eye_level.png', framed, az=18, el=0, res=(2000, 1100),
                 lens=35, ground=None, eye=1.6, target=(0, -3, 1.5), dist=39, sun_az=-35)
        fam.clear_showcase()
    if fam.want('05_style_neighbours.png'):
        refs = load_preview_assets(fam, 'SQUARE', 'SK2-SQUARE-001_v02.blend', ['SQ_Bench', 'SQ_Planter'])
        refs.update(load_preview_assets(fam, 'TREES', 'SK2-TREES-001_v02.blend', ['TR_Round_B']))
        refs['SQ_Bench'].location = (-3.0, 0, 0)
        refs['SQ_Planter'].location = (-5.0, 0, 0)
        refs['TR_Round_B'].location = (-4.5, 5.6, 0)
        objs = list(refs.values())
        if fam.args.revision >= 3:
            objs += fam.place('BE_Pier_Post', -1.25, -0.2)
        objs += fam.place('BE_Lounger', 0, -0.2)
        objs += fam.place('BE_SideTable', 1.3, -0.2)
        objs += fam.place('BE_Umbrella_Red', 3.2, 0.5)
        objs += fam.place('BE_Planter_Palm', 6, 0)
        objs += fam.place('BE_Palm_B', 5, 6)
        fam.showcase(True)
        fam.shot('05_style_neighbours.png', objs, az=10, el=17, res=(1900, 1250), ground='paving', pad=1.12)
        fam.clear_showcase()
    fam.showcase(False)
print('BEACH_DONE', fam.rev, 'palette_sha256', palette_fingerprint())
