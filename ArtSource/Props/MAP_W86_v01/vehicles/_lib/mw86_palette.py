"""MAP_W86_v01 vehicles - family palette atlases (pure Python; imported by Blender builders and by make_atlases.py).

Atlas per family and colour variant: 512 x 512 px, sRGB.
  * top half  (v 0.5 .. 1.0): flat colour cells, 32 px, 16 columns x 8 rows. A flat face gets ONE UV point in the centre
    of its cell (constant UV per face -> no mip bleeding), exactly like SK_Palette / Look_Palette_v2.
  * bottom half (v 0 .. 0.5): pattern regions (camo, teak deck, hazard stripes, wagon boards), mapped by projection.
Variants A/B/C share the layout; only the paint cells and pattern colours differ, so a colour variant is just another
material with the same shader and a different texture (MW86_<Family>_<V>.png).
Colours: Style Bible v2 core swatches (hex = on-screen colour in sun) + a few family paints (navy, olive, ...).
"""
from collections import OrderedDict

ATLAS_PX = 512
CELL_PX = 32
COLS = ATLAS_PX // CELL_PX          # 16
ROWS = 8                            # top half only
VARIANTS = ('A', 'B', 'C')

# ---------------------------------------------------------------- shared core cells (same index in every family atlas)
CORE = OrderedDict([
    ('chalk', '#F4EFE6'), ('chalk_dark', '#DAD4CD'), ('cream', '#EEDCB8'), ('panel', '#C9CDCA'),
    ('grey_light', '#B5B9BE'), ('grey', '#A3A6AB'), ('grey_dark', '#8C8D92'), ('asphalt', '#7E838A'),
    ('ink_light', '#4A5058'), ('ink', '#3B4048'), ('ink_dark', '#282B32'), ('tyre', '#2F3237'),
    ('glass_v', '#4D6A86'), ('glass_light', '#7EAFD5'), ('glass_dark', '#3A4E62'), ('chrome', '#DDE0DD'),
    ('wood_light', '#AB825B'), ('wood', '#9C6E4A'), ('wood_dark', '#815740'), ('rust', '#8D423F'),
    ('red', '#D9473A'), ('mustard', '#E0A830'), ('teal', '#3F9196'), ('cobalt', '#3E6FB8'),
    ('terracotta', '#D27A55'), ('sand', '#F1DEAC'), ('sand_dark', '#D9C29B'), ('orange', '#E8892E'),
    ('lamp_glow', '#FFE2A8'), ('lamp_red', '#C8352E'), ('leaf', '#4F8F4E'), ('ochre', '#EAC27C'),
])

# ---------------------------------------------------------------- family paints: name -> (A, B, C)
FAMILY_PAINTS = {
    'Water': OrderedDict([
        ('yacht_hull', ('#F4EFE6', '#2C4466', '#F4EFE6')),
        ('yacht_stripe', ('#2C4466', '#F4EFE6', '#3F9196')),
        ('yacht_boot', ('#2C4466', '#282B32', '#2F7378')),
        ('yacht_super', ('#F4EFE6', '#F4EFE6', '#EEDCB8')),
        ('cushion', ('#EEDCB8', '#F4EFE6', '#C9CDCA')),
        ('canopy', ('#2C4466', '#C9CDCA', '#3F9196')),
        ('boat_hull', ('#3E6FB8', '#4F8F4E', '#D9473A')),
        ('boat_bottom', ('#B5483C', '#B5483C', '#3B4048')),
        ('boat_house', ('#F4EFE6', '#EEDCB8', '#F4EFE6')),
        ('row_paint', ('#5E9C98', '#7AA06A', '#6F8FB0')),
        ('row_bottom', ('#8D423F', '#4A5058', '#8D423F')),
        ('jetski_paint', ('#E0A830', '#D9473A', '#3E6FB8')),
        ('sup_paint', ('#3F9196', '#E5A486', '#E0A830')),
        ('teak', ('#C9A27A', '#C9A27A', '#C9A27A')),
        ('teak_dark', ('#9C764F', '#9C764F', '#9C764F')),
    ]),
    'Military': OrderedDict([
        ('mil_base', ('#6E7350', '#C2A878', '#7D8670')),
        ('mil_dark', ('#4E533A', '#8E7650', '#5F6758')),
        ('mil_light', ('#8D9068', '#D8C49A', '#98A08A')),
        ('mil_canvas', ('#8F8A62', '#C9B68A', '#8A8F7C')),
        ('navy_grey', ('#8A96A2', '#8A96A2', '#8A96A2')),
        ('navy_grey_dark', ('#6C7782', '#6C7782', '#6C7782')),
        ('missile_white', ('#F4EFE6', '#F4EFE6', '#F4EFE6')),
        ('missile_red', ('#D9473A', '#D9473A', '#D9473A')),
        ('silo_concrete', ('#B9B5AE', '#B9B5AE', '#B9B5AE')),
        ('heli_paint', ('#6E7350', '#C2A878', '#5F6758')),
    ]),
    'Machines': OrderedDict([
        ('loader_paint', ('#E0A830', '#E07B39', '#D9473A')),
        ('dump_cab', ('#E07B39', '#3E6FB8', '#E0A830')),
        ('dump_tub', ('#C8662F', '#A3A6AB', '#C79226')),
        ('mixer_cab', ('#F4EFE6', '#E0A830', '#D9473A')),
        ('mixer_drum', ('#E07B39', '#F4EFE6', '#E0A830')),
        ('mixer_band', ('#F4EFE6', '#D9473A', '#F4EFE6')),
        ('stacker_paint', ('#3E6FB8', '#E0A830', '#D9473A')),
        ('forklift_paint', ('#3E6FB8', '#E0A830', '#E07B39')),
        ('truck_cab', ('#F4EFE6', '#3E6FB8', '#D9473A')),
        ('container', ('#C4513F', '#3E6E9E', '#4F8F4E')),
        ('container_dark', ('#A6443A', '#345C84', '#437A43')),
        ('food_paint', ('#3F9196', '#D9473A', '#E0A830')),
        ('food_body', ('#EEDCB8', '#F4EFE6', '#F4EFE6')),
        ('van_paint', ('#ECE8DE', '#9FB4C4', '#EAC27C')),
        ('wagon_wall', ('#8C4A36', '#4E6B4A', '#6E4A36')),
        ('wagon_roof', ('#6B6E73', '#6B6E73', '#6B6E73')),
        ('suv_paint', ('#2A2D33', '#2A2D33', '#3B4048')),
    ]),
}

# ---------------------------------------------------------------- pattern regions (UV rects u0, v0, u1, v1 inside the bottom half)
REGIONS = {
    'full': (0.0, 0.0, 1.0, 0.5),
    'left': (0.0, 0.0, 0.5, 0.5),
    'right': (0.5, 0.0, 1.0, 0.5),
}
# family -> {pattern name: (region, kind, {variant: colours}, params)}
FAMILY_PATTERNS = {
    'Water': {
        'teak_deck': ('left', 'planks', {'A': ('#C9A27A', '#9C764F'), 'B': ('#C9A27A', '#9C764F'), 'C': ('#C9A27A', '#9C764F')},
                      {'count': 22, 'seam_px': 2, 'axis': 'u'}),
        'hull_planks': ('right', 'planks', {'A': ('#5E9C98', '#4E8582'), 'B': ('#7AA06A', '#658957'), 'C': ('#6F8FB0', '#5D7A98')},
                        {'count': 7, 'seam_px': 3, 'axis': 'v'}),
    },
    'Military': {
        'camo': ('full', 'camo', {'A': ('#6E7350', '#4B5A3A', '#7A6448', '#3B4048'),
                                  'B': ('#C2A878', '#A88B5E', '#DCC9A0', '#8E7650'),
                                  'C': ('#7D8670', '#717A64', '#7D8670', '#717A64')},
                 {'seed': 11, 'blur': 18}),
    },
    'Machines': {
        'hazard': ('left', 'hazard', {'A': ('#E0A830', '#3B4048'), 'B': ('#E0A830', '#3B4048'), 'C': ('#E0A830', '#3B4048')},
                   {'stripe_px': 26}),
        'wagon_boards': ('right', 'planks', {'A': ('#8C4A36', '#743C2D'), 'B': ('#4E6B4A', '#405A3D'), 'C': ('#6E4A36', '#5B3D2C')},
                         {'count': 12, 'seam_px': 3, 'axis': 'u'}),
    },
}


def cells(family):
    """Ordered list of cell names for a family atlas (core first)."""
    names = list(CORE.keys()) + list(FAMILY_PAINTS[family].keys())
    assert len(names) <= COLS * ROWS, (family, len(names))
    return names


def cell_index(family, name):
    return cells(family).index(name)


def cell_uv(family, name):
    i = cell_index(family, name)
    c, r = i % COLS, i // COLS
    return ((c + 0.5) / COLS, 1.0 - (r + 0.5) * CELL_PX / ATLAS_PX)


def cell_hex(family, name, variant='A'):
    if name in CORE:
        return CORE[name]
    return FAMILY_PAINTS[family][name][VARIANTS.index(variant)]


def region_uv(family, pattern):
    reg = FAMILY_PATTERNS[family][pattern][0]
    u0, v0, u1, v1 = REGIONS[reg]
    pad = 3 / ATLAS_PX
    return (u0 + pad, v0 + pad, u1 - pad, v1 - pad)


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
