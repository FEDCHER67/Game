"""STYLE_KIT_v2 / HOUSES - reference buildings for the facade grammar (style bible v2, section 7).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/HOUSES/build_houses.py -- --revision 2

These are hand-assembled reference buildings for bible 7.1-7.4 (the trial frame and the ProceduralBuilding roll-out
are measured against them). Since v02 the geometry kit lives in _lib/sk2_house.py (shared with HOUSES_PLAN):
  * the body is ONE closed box whose walls are cut into a grid; window and door cells are pushed in (reveal 0.15 m),
    so windows are real recesses;
  * every edge is drawn by a chalk trim: corner pilasters 0.40, floor bands 0.22, casings 0.12, sills 0.10 x 0.12,
    lintels, mullion crosses, roof fascia 0.18 and soffits, parapet caps 0.40;
  * colours follow the district recipe and the wall -> roof pairs (bible 2.5-2.6); no textures but the bible-3.3
    pattern maps (roof tiles, brick, panel seams);
  * houses are not bevelled (bible 3.5): flat faces, edges drawn by trims.

v02 (critique of the 2026-10-07 trial frame):
  * panelled doors (two recessed panels, stiles, rails, brass handle), one accent per house (flower boxes or shutters);
  * the second pair of old-town houses gets other recipes and storey counts: HS_OldTown_C (ochre + slate, 4 floors,
    gable to the street) and HS_OldTown_D (mint + terracotta, 2 floors, hipped);
  * HS_OldTown_B: the pediment is a closed dormer volume (cheeks, back wall) - no floating ridge bar or white wedge;
  * HS_MidRise: the cornice is a ring around the walls, not a slab through the roof deck (the v01 z-fight);
  * HS_PanelSection: open balconies with panel parapets, a third glazed, ink door under a concrete canopy, dark asphalt
    plinth, PT_PanelSeams_v2 seams, blank end walls (the v01 cobalt glazed front read as a Euro new-build);
  * terracotta slopes carry PT_RoofTile_v2 (mip-mapped line map) instead of 5 cm geometry strips (moire).
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
import sk2_house as hk                                   # noqa: E402

fam = sk.Family('SK2-HOUSES-001', __file__, 'HS_', budget=(1, 3500),
                description='Houses v2: old-town houses A (2 floors), B (3 floors), C (4 floors, gable to the street), '
                            'D (2 floors, hipped), mid-rise block (5 floors), panel-block section (5 floors) - bible 7')
PAIRS = {p['wall']: p['roofs'] for p in sk.BIBLE_DATA['wall_roof_pairs']}
lstar = hk.lstar

OLD_A = {'district': 'old_town', 'style': 'oldtown', 'wall': 'cream', 'roof': 'terracotta', 'roof_c': 'terracotta',
         'trim': 'chalk', 'plinth': 'asphalt', 'door': 'red', 'accent': 'red'}
OLD_B = {'district': 'old_town', 'style': 'oldtown', 'wall': 'coral', 'roof': 'slate', 'roof_c': 'slate', 'trim': 'chalk',
         'plinth': 'asphalt', 'door': 'wood', 'accent': 'cobalt'}
OLD_C = {'district': 'old_town', 'style': 'oldtown', 'wall': 'ochre', 'roof': 'slate', 'roof_c': 'slate', 'trim': 'chalk',
         'plinth': 'asphalt', 'door': 'wood', 'accent': 'cobalt'}
OLD_D = {'district': 'old_town', 'style': 'oldtown', 'wall': 'mint', 'roof': 'terracotta', 'roof_c': 'terracotta',
         'trim': 'chalk', 'plinth': 'asphalt', 'door': 'red', 'accent': 'red'}
MID = {'district': 'old_town', 'style': 'commercial (ground floor) + oldtown', 'wall': 'ochre', 'roof': 'grey', 'roof_c': 'grey',
       'deck': 'grey', 'trim': 'chalk', 'plinth': 'asphalt', 'door': 'wood', 'accent': 'red'}
PANEL = {'district': 'residential', 'style': 'panel', 'wall': 'panel', 'roof': 'grey', 'roof_c': 'grey', 'deck': 'grey',
         'trim': 'chalk', 'plinth': 'asphalt', 'door': 'ink', 'accent': 'mustard'}


def old_town_a():
    """2 floors + gable roof 35 deg (terracotta, PT_RoofTile_v2), 4 bays at 2.8 m, panelled red door off-centre in bay
    2 under a canopy, flower boxes on the 2nd-floor windows (the one accent), chimney near the right gable."""
    W, D, floors = 11.6, 8.4, 2
    h = hk.House(W, D, 0.5 + floors * 3.2 + 0.25, OLD_A)
    bays = [-4.2, -1.4, 1.4, 4.2]
    front = {}
    for f in range(floors):
        for i, c in enumerate(bays):
            if f == 0 and i == 1:
                continue
            glass = 'glass.light' if (f, i) in ((1, 2), (0, 3)) else 'glass'
            front[(f, i)] = h.window(0, c, f, glass=glass)
            h.window(2, c, f, glass='glass.light' if (f, i) == (0, 1) else 'glass')
        for c in (-1.6, 1.6):
            h.window(1, c, f, glass='glass.light' if (f, c) == (1, 1.6) else 'glass')
            h.window(3, c, f)
    h.door(0, -1.4, canopy=(1.6, 0.8), steps=3)
    for (f, i), (u0, u1, z) in front.items():
        if f == 1:
            h.later.append(lambda u0=u0, u1=u1, z=z: h.flower_box(0, u0, u1, z, 'cobalt', 'red'))
    h.plinth_box()
    h.pilasters(h.z1)
    h.band(h.floor_z(1) - 0.05)
    zE, ztop = h.gable_roof(35)
    h.chimney(3.9, 1.6, ztop + 0.7, h.z1)
    return h.finish()


def old_town_b():
    """3 floors + hipped roof 30 deg (slate), 3 bays, central arched panelled door, a closed pediment dormer over the
    middle bay, lintels over the 2nd-floor windows, cobalt shutters on the two lower floors, chimney at the left end."""
    W, D, floors = 8.8, 8.4, 3
    h = hk.House(W, D, 0.5 + floors * 3.2 + 0.25, OLD_B)
    bays = [-2.8, 0.0, 2.8]
    front = {}
    for f in range(floors):
        for i, c in enumerate(bays):
            if f == 0 and i == 1:
                continue
            lin = f == 1
            front[(f, i)] = h.window(0, c, f, lintel=lin, glass='glass.light' if (f, i) in ((2, 0), (1, 2)) else 'glass')
            h.window(2, c, f, lintel=lin, glass='glass.light' if (f, i) == (1, 1) else 'glass')
        h.window(1, 0.0, f, lintel=f == 1, glass='glass.light' if f == 2 else 'glass')
        h.window(3, 0.0, f, lintel=f == 1)
    h.door(0, 0.0, w=1.3, h=2.5, transom=2.05, arch=True, steps=3)
    for (f, i), (u0, u1, z) in front.items():
        if f <= 1:
            h.later.append(lambda u0=u0, u1=u1, z=z: h.shutters(0, u0, u1, z, 1.8, 'cobalt'))
    h.plinth_box()
    h.pilasters(h.z1)
    h.band(h.floor_z(1) - 0.05)
    h.band(h.floor_z(2) - 0.05)
    zf, ztop = h.hip_roof(30)
    h.cross_gable(0, 0.0, 3.0, 38, 3.2, main_pitch=30)
    h.oculus(0, h.body.u_of(0, 0.0), h.z1 + 0.86, r=0.34)
    h.chimney(-2.6, 1.2, ztop + 0.5, h.z1)
    return h.finish()


def old_town_c():
    """4 floors, gable to the street (ridge front-to-back, 7.4 m frontage x 12 m), ochre + slate, panelled wood door
    under a canopy, cobalt shutters, lintels on the 2nd floor, oculus in the front gable."""
    return hk.masonry({'id': 'HS_OldTown_C', 'W': 7.4, 'D': 12.0, 'floors': 4, 'roof': 'gable', 'axis': 'y', 'rc': OLD_C,
                       'accent_kind': 'shutters', 'pitch': 38})


def old_town_d():
    """2 floors, hipped terracotta roof (PT_RoofTile_v2), mint walls, 5 bays with a central door under civic-free
    canopy, flower boxes (red) - the warm counterpart of B."""
    return hk.masonry({'id': 'HS_OldTown_D', 'W': 14.0, 'D': 9.0, 'floors': 2, 'roof': 'hip', 'rc': OLD_D,
                       'accent_kind': 'flower', 'central_door': True, 'pitch': 30})


def midrise():
    """5 floors: a tall shop ground floor (3.8 m) with three display windows and red/white awnings, a panelled wood
    door; four old-town floors above; floor bands, corner pilasters, a deep chalk cornice RING (v02: no slab through
    the deck), parapet with a 0.40 m chalk cap, a machine room and two vents on the grey roof."""
    W, D = 17.0, 12.0
    gf, fl = 3.8, 3.2
    z_top = 0.5 + gf + 4 * fl
    h = hk.House(W, D, z_top, MID, plinth=0.5, floor=fl, ground_floor=gf)
    bays = [-7.0, -4.2, -1.4, 1.4, 4.2, 7.0]
    for f in range(1, 5):
        for i, c in enumerate(bays):
            h.window(0, c, f, glass='glass.light' if (f + i) % 5 == 0 else 'glass', lintel=(f == 1))
            h.window(2, c, f, glass='glass.light' if (f + 2 * i) % 5 == 0 else 'glass')
        h.window(1, 0.0, f, glass='glass.light' if f == 3 else 'glass')
        h.window(3, 0.0, f, glass='glass.light' if f == 2 else 'glass')
    z0 = 0.5
    for c in (-5.6, -2.0, 5.6):
        h.shopfront(0, c, 2.6, h=3.0, sill=0.55)
    h.door(0, 2.4, w=1.4, h=2.8, transom=2.2, steps=3)
    for side in (1, 3, 2):
        for c in ([-2.8, 2.8] if side != 2 else [-5.6, 0.0, 5.6]):
            h.window(side, c, 0, w=1.4, h=1.6, sill_h=1.2, cross=False)
    h.plinth_box()
    h.pilasters(z_top)
    for f in range(1, 5):
        h.band(h.floor_z(f) - 0.12)
    m = h.finish()
    for c in (-5.6, -2.0, 5.6):
        hk.awning(m, h.body, 0, c, 3.0, z0 + 3.45, 1.1, 0.55, 7, ['red', 'chalk'])
    h.cornice(z_top, h=0.35, out=0.25)
    h.parapet(z_top, ph=0.8)
    m.box(3.6, 2.6, 2.2, MID['wall'], base=True, at=(3.0, 1.5, z_top), kind='hard', member=2.2)
    m.box(3.8, 2.8, 0.15, 'chalk', base=True, at=(3.0, 1.5, z_top + 2.2), kind='hard', member=0.15)
    for x, y in ((-4.5, -2.0), (-6.2, 2.4)):
        m.box(0.7, 0.7, 0.9, 'grey', base=True, at=(x, y, z_top), kind='hard', member=0.7)
        m.box(0.86, 0.86, 0.1, 'grey.dark', base=True, at=(x, y, z_top + 0.9), kind='hard', member=0.1)
    return m


def panel_section():
    """One entrance section of a 5-storey panel block (18 x 12 m, five 3.6 m bays): see sk2_house.slab."""
    return hk.slab({'id': 'HS_PanelSection', 'W': 18.0, 'D': 12.0, 'floors': 5, 'rc': PANEL})


# ---------------------------------------------------------------- assets + recipe checks (R1-R3, pairs)
def recipe_checks(rc, flat):
    c = {'trim_lighter_than_wall_ge_6_L': lstar(rc['trim']) - lstar(rc['wall']) >= 6 - 1e-6,
         'plinth_wall_dL_ge_12': abs(lstar(rc['plinth']) - lstar(rc['wall'])) >= 12 - 1e-6}
    if not flat:
        c['roof_wall_dL_ge_15'] = abs(lstar(rc['roof']) - lstar(rc['wall'])) >= 15 - 1e-6
        c['roof_allowed_for_wall_2_6'] = rc['roof'] in PAIRS.get(rc['wall'], [])
    return c


BUILDINGS = [
    ('HS_OldTown_A', old_town_a, OLD_A, False, (1, 4500), '2 floors, gable roof, flower boxes'),
    ('HS_OldTown_B', old_town_b, OLD_B, False, (1, 4500), '3 floors, hipped roof with a closed pediment dormer, shutters'),
    ('HS_OldTown_C', old_town_c, OLD_C, False, (1, 5500), '4 floors, gable to the street, shutters'),
    ('HS_OldTown_D', old_town_d, OLD_D, False, (1, 5500), '2 floors, hipped terracotta roof, flower boxes'),
    ('HS_MidRise', midrise, MID, True, (1, 8000), '5 floors, shops on the ground floor, flat roof'),
    ('HS_PanelSection', panel_section, dict(PANEL, plinth='asphalt.dark'), True, (1, 14000), '5-storey panel block, one entrance section'),
]
for i, (name, fn, rc, flat, budget, what) in enumerate(BUILDINGS):
    fam.add_asset(name, fn, budget=budget, row=0 if i < 4 else 1, recipe=rc, form=what,
                  wall_L=round(lstar(rc['wall']), 1), extra_checks=recipe_checks(rc, flat))

_orig = fam._validate_asset


def _validate(a):
    r = _orig(a)
    r['checks'].update(a['meta'].get('extra_checks', {}))
    r['all_checks_passed'] = all(r['checks'].values())
    return r


fam._validate_asset = _validate
report = fam.finish(lineup_gap=6.0, row_gap=8.0, extra_notes=[
    'Reference buildings for the facade grammar of bible 7.1-7.3 and for the trial frame; ProceduralBuilding keeps '
    'generating the map houses and is measured against these. The geometry kit is _lib/sk2_house.py (v02).',
    'Windows are recessed cells of one closed body (reveal 0.15 m); trims are overlapping closed shells.',
    'Old-town floor 3.2 m, panel floor 2.8 m, door 2.1-2.6 m, sill 0.9 m (bible 4.6).',
    'v02: panelled doors, one accent per house, closed dormers, cornice ring, panel block without the cobalt glazing, '
    'PT_RoofTile_v2 / PT_PanelSeams_v2 / PT_Brick_v2 pattern maps (second material per pattern, mip-mapped in Unity).'])


# ---------------------------------------------------------------- previews
def ground_patch(w, d, col, at=(0, 0)):
    m = sk.Mesh()
    m.box(w, d, 0.02, col, base=True, at=(at[0], at[1], -0.015))
    return m


if not fam.args.no_render:
    for name, *_ in BUILDINGS:
        objs = fam.place(name, 0.0, 0.0)
        r = report['assets'][name]
        pave = fam.proxy('Proxy_Paving', ground_patch(r['size_m'][0] + 10, r['size_m'][1] + 10, 'paving'))
        fam.showcase(True)
        fam.shot(f'01_{name}_front.png', objs, az=28, el=12, res=(1600, 1200), lens=40, ground='meadow',
                 person=(r['bounds_min'][0] - 1.5, r['bounds_min'][1] - 1.5))
        fam.shot(f'02_{name}_back.png', objs, az=208, el=20, res=(1600, 1200), lens=40, ground='meadow')
        fam.clear_showcase()
    # eye level, 15 m in front of house A: the facade grammar check of the trial frame (bible 12, camera 3)
    objs = fam.place('HS_OldTown_A', 0.0, 0.0)
    pave = fam.proxy('Proxy_Paving', ground_patch(30, 30, 'paving'))
    fam.showcase(True)
    fam.shot('03_HS_OldTown_A_eye_level_15m.png', objs, az=8, el=0, res=(1600, 1200), lens=35, ground='meadow',
             eye=1.6, target=(0.0, 0.0, 4.2), dist=15.0 + 4.2, person=(2.4, -6.0))
    fam.clear_showcase()
    # a street front: four different houses on one eave line rule (bible 10.8) - the "copy-paste pair" check
    objs = []
    x = 0.0
    for n in ('HS_OldTown_B', 'HS_OldTown_A', 'HS_OldTown_C', 'HS_OldTown_D'):
        r = report['assets'][n]
        x += -r['bounds_min'][0]
        objs += fam.place(n, x, 0.0)
        x += r['bounds_max'][0] + 0.6
    pave = fam.proxy('Proxy_Paving', ground_patch(x + 6, 14, 'paving', at=(x / 2, -2)))
    fam.showcase(True)
    fam.shot('04_street_front_ABCD.png', objs, az=22, el=10, res=(2200, 1100), lens=40, ground='meadow', person=(4.0, -7.0))
    fam.shot('05_street_back_ABCD.png', objs, az=200, el=26, res=(2200, 1100), lens=40, ground='meadow')
    fam.clear_showcase()
    fam.showcase(False)
print('done')
