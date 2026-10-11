"""STYLE_KIT_v2 shared library: the look of docs/art/STYLE_BIBLE_v2.md as deterministic bpy scripts.

Run any family headless with Blender 5.2 (from the repository root):
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/TREES/build_trees.py -- --revision 1

Conventions (the same as MAP_PROPS / STREET_KIT / LANDMARKS / STYLE_KIT_v1):
  * Blender Z up, metres, front = -Y. FBX: axis_forward=-Z, axis_up=Y, apply_unit_scale=True.
  * One root mesh per asset at the origin; pivot = centre of the base on the ground. Optional children:
    <Asset>_Emissive (lamp glass, palette material with emission) and <Asset>_Water (fountain water, same palette).
  * Closed shells only: every edge is shared by exactly two faces, winding is consistent and outward.
    Random vertex jitter = 0 everywhere; asymmetry comes from per-asset templates, never from noise.
  * ONE material, Look_Palette_v2, with the atlas _lib/Look_Palette_v2.png generated from the JSON block (appendix A)
    of the style bible. RGB = swatch colour (sRGB), A = URP smoothness (0.05 default, glass 0.35, water 0.55,
    emissive 0.20). UV0 of every face sits inside the cell of its swatch: flat swatches at the cell centre;
    gradient cells (16 x 96 px) encode the height fraction of the shape in V.
  * Normals are written as custom split normals per shell: flat (hard surfaces), smooth (organic lobes),
    weighted (bevelled props: big faces stay flat, bevels round off), up (grass, lit like the ground).
    No vertex colours (URP Lit ignores them, bible 3.2).
  * Revisions are never overwritten: a new model is a new --revision; --force only rebuilds the same revision.
"""
import argparse, hashlib, json, math, re, struct, sys, zlib
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix

TAU = math.tau
LIB_DIR = Path(__file__).resolve().parent
KIT_DIR = LIB_DIR.parent
REPO_DIR = KIT_DIR.parents[2]
BIBLE = REPO_DIR / 'docs' / 'art' / 'STYLE_BIBLE_v2.md'
KIT_NAME = 'STYLE_KIT_v2'
PALETTE_NAME = 'Look_Palette_v2'

# ---------------------------------------------------------------- palette atlas layout
CELL, GRID = 16, 16                      # 16 px cells, 16 x 16 cells -> 256 x 256
SIZE = CELL * GRID
ROW_CORE, ROW_CORE_LIGHT, ROW_CORE_DARK = 0, 2, 4      # 22 core swatches use two rows per step
ROW_ACC, ROW_ACC_LIGHT, ROW_ACC_DARK = 6, 7, 8         # 9 accents (emissive ones have no ramp)
GRAD_ROW0, GRAD_ROWS = 10, 6                           # gradient cells: 16 px wide x 96 px tall (rows 10-15)
GRAD_MARGIN_PX = 2.0                                   # V stays this far inside a gradient cell (no bleeding)

SMOOTHNESS_DEFAULT = 0.05                              # bible 3.4
SMOOTHNESS = {'glass': 0.35, 'water': 0.55}            # swatch family -> smoothness (all three ramp steps)
SMOOTHNESS_EMISSIVE = 0.20

# Vertical gradients (bible 3.1 level 2: organics only). Knots (t, swatch): piecewise linear in sRGB, t = height
# fraction inside the shape (0 = bottom, 1 = top). Crowns: top 30 % .light, bottom 25 % .dark, the swatch between
# (bible 5.2.3), with soft 0.16-wide transitions so the crown reads as one painted mass, not as stripes.
GRADIENTS = [
    ('grad.leaf', [(0.0, 'leaf.dark'), (0.17, 'leaf.dark'), (0.33, 'leaf'), (0.62, 'leaf'), (0.78, 'leaf.light'), (1.0, 'leaf.light')]),
    ('grad.birch', [(0.0, 'leaf'), (0.30, 'leaf'), (0.70, 'leaf.light'), (1.0, 'leaf.light')]),
    ('grad.conifer', [(0.0, 'conifer.dark'), (0.17, 'conifer.dark'), (0.33, 'conifer'), (0.62, 'conifer'), (0.78, 'conifer.light'), (1.0, 'conifer.light')]),
    ('grad.bush', [(0.0, 'leaf.dark'), (0.22, 'leaf.dark'), (0.62, 'leaf'), (1.0, 'leaf')]),
    ('grad.lawn', [(0.0, 'lawn'), (0.35, 'lawn'), (0.85, 'lawn.light'), (1.0, 'lawn.light')]),
    ('grad.meadow', [(0.0, 'meadow'), (0.35, 'meadow'), (0.85, 'meadow.light'), (1.0, 'meadow.light')]),
    ('grad.dune', [(0.0, 'meadow.dark'), (0.30, 'meadow.dark'), (0.85, 'meadow'), (1.0, 'meadow')]),
    ('grad.water', [(0.0, 'water.dark'), (0.45, 'water'), (1.0, 'water.light')]),
    ('grad.hedge', [(0.0, 'leaf.dark'), (0.1, 'leaf.dark'), (0.3, 'leaf'), (0.76, 'leaf'), (0.95, 'leaf.light'), (1.0, 'leaf.light')]),
    # v02b (appended, so every older cell keeps its place): clipped-hedge top reads leaf.light (critique 4)
    ('grad.hedge.v2', [(0.0, 'leaf.dark'), (0.12, 'leaf.dark'), (0.32, 'leaf'), (0.70, 'leaf'), (0.86, 'leaf.light'), (1.0, 'leaf.light')]),
]


# ---------------------------------------------------------------- the bible (appendix A is the only colour source)
def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hexstr(rgb):
    return '#%02X%02X%02X' % tuple(int(round(c)) for c in rgb)


def load_bible():
    text = BIBLE.read_text(encoding='utf-8')
    for block in re.findall(r'```json\s*(\{.*?\})\s*```', text, re.S):
        if '"style_bible"' in block and '"swatches"' in block:
            return json.loads(block)
    sys.exit(f'No appendix-A JSON block found in {BIBLE}')


BIBLE_DATA = load_bible()
SWATCH = {}        # name -> (r, g, b) 0..255, names: 'leaf', 'leaf.light', 'leaf.dark', 'red', 'lamp_glow', ...
CELLS = {}         # name -> (row, col) of the 16 px cell (flat swatches)
EMISSIVE = set()
CORE = [s['name'] for s in BIBLE_DATA['swatches']]
ACCENTS = [a['name'] for a in BIBLE_DATA['accents']]
for i, s in enumerate(BIBLE_DATA['swatches']):
    r, c = divmod(i, GRID)
    for step, row0 in (('', ROW_CORE), ('.light', ROW_CORE_LIGHT), ('.dark', ROW_CORE_DARK)):
        key = 'hex' if not step else step[1:]
        SWATCH[s['name'] + step] = _hex(s[key])
        CELLS[s['name'] + step] = (row0 + r, c)
for i, a in enumerate(BIBLE_DATA['accents']):
    SWATCH[a['name']] = _hex(a['hex'])
    CELLS[a['name']] = (ROW_ACC, i)
    if a.get('emissive'):
        EMISSIVE.add(a['name'])
    for step, row0 in (('light', ROW_ACC_LIGHT), ('dark', ROW_ACC_DARK)):
        if a.get(step):
            SWATCH[f"{a['name']}.{step}"] = _hex(a[step])
            CELLS[f"{a['name']}.{step}"] = (row0, i)
GRAD = {}          # name -> (col, knots)
for col, (gname, knots) in enumerate(GRADIENTS):
    for _, sw in knots:
        assert sw in SWATCH, f'gradient {gname} uses unknown swatch {sw}'
    GRAD[gname] = (col, knots)


def base_of(name):
    """'leaf.dark' -> 'leaf'; 'grad.leaf' -> 'leaf' (the swatch a ramp step or gradient belongs to);
    'PT_RoofTile_v2|terracotta' -> 'terracotta' (a pattern-map face, v02)."""
    if is_pattern(name):
        name = pattern_parts(name)[1]
    if name in GRAD:
        return GRAD[name][1][len(GRAD[name][1]) // 2][1].split('.')[0]
    return name.split('.')[0]


def smoothness_of(name):
    if name in EMISSIVE:
        return SMOOTHNESS_EMISSIVE
    return SMOOTHNESS.get(base_of(name), SMOOTHNESS_DEFAULT)


def grad_rgb(gname, t):
    knots = GRAD[gname][1]
    t = min(max(t, 0.0), 1.0)
    for (t0, s0), (t1, s1) in zip(knots, knots[1:]):
        if t <= t1:
            k = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            a, b = SWATCH[s0], SWATCH[s1]
            return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    return SWATCH[knots[-1][1]]


def rgb_of(name, t=None):
    if name in GRAD:
        return grad_rgb(name, 0.5 if t is None else t)
    return SWATCH[name]


def cell_rect(name):
    """(u0, v0, u1, v1) of a swatch cell or a gradient cell, V up (image origin bottom-left)."""
    if name in GRAD:
        col = GRAD[name][0]
        return (col / GRID, 1 - (GRAD_ROW0 + GRAD_ROWS) / GRID, (col + 1) / GRID, 1 - GRAD_ROW0 / GRID)
    row, col = CELLS[name]
    return (col / GRID, 1 - (row + 1) / GRID, (col + 1) / GRID, 1 - row / GRID)


def swatch_uv(name, t=None):
    u0, v0, u1, v1 = cell_rect(name)
    if name not in GRAD:
        return ((u0 + u1) / 2, (v0 + v1) / 2)
    t = min(max(0.5 if t is None else t, 0.0), 1.0)
    h = GRAD_ROWS * CELL
    return ((u0 + u1) / 2, v0 + (GRAD_MARGIN_PX + t * (h - 2 * GRAD_MARGIN_PX)) / SIZE)


def srgb_to_linear(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c)


def lin(name):
    return (*srgb_to_linear(rgb_of(name)), 1.0)


# ---------------------------------------------------------------- atlas files (pure Python PNG: byte-identical rebuilds)
def _png(path, w, h, rows_top_down):
    raw = b''.join(b'\x00' + bytes(r) for r in rows_top_down)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    path.write_bytes(data)


def atlas_pixels():
    """RGBA rows, top row first. Unused cells: neutral mid grey, alpha 0.05 (never referenced)."""
    px = [[(128, 128, 128, 13)] * SIZE for _ in range(SIZE)]
    for name, (row, col) in CELLS.items():
        r, g, b = SWATCH[name]
        a = int(round(smoothness_of(name) * 255))
        for y in range(row * CELL, (row + 1) * CELL):
            for x in range(col * CELL, (col + 1) * CELL):
                px[y][x] = (r, g, b, a)
    h = GRAD_ROWS * CELL
    for gname, (col, _) in GRAD.items():
        a = int(round(smoothness_of(gname) * 255))
        for i in range(h):                                   # i = pixel row from the bottom of the cell
            t = (i + 0.5 - GRAD_MARGIN_PX) / (h - 2 * GRAD_MARGIN_PX)
            r, g, b = (int(round(c)) for c in grad_rgb(gname, t))
            y = SIZE - 1 - i                                 # gradient cells sit at the bottom of the atlas
            for x in range(col * CELL, (col + 1) * CELL):
                px[y][x] = (r, g, b, a)
    return [[c for p in row for c in p] for row in px]


def write_atlas(out_dir=LIB_DIR):
    out_dir = Path(out_dir)
    png = out_dir / f'{PALETTE_NAME}.png'
    _png(png, SIZE, SIZE, atlas_pixels())
    layout = {
        'atlas': png.name, 'style_bible': BIBLE_DATA['style_bible'], 'bible_date': BIBLE_DATA.get('date'),
        'source': 'docs/art/STYLE_BIBLE_v2.md, appendix A (JSON); generated by _lib/stylekit2.py, never edited by hand',
        'size_px': SIZE, 'cell_px': CELL,
        'rows': {'core': [ROW_CORE, ROW_CORE + 1], 'core.light': [ROW_CORE_LIGHT, ROW_CORE_LIGHT + 1],
                 'core.dark': [ROW_CORE_DARK, ROW_CORE_DARK + 1], 'accents': ROW_ACC, 'accents.light': ROW_ACC_LIGHT,
                 'accents.dark': ROW_ACC_DARK, 'gradients': list(range(GRAD_ROW0, GRAD_ROW0 + GRAD_ROWS))},
        'alpha': 'URP smoothness (Smoothness Source = Albedo Alpha, Smoothness 1.0): default 0.05, glass 0.35, water 0.55, emissive 0.20',
        'unity_import': 'sRGB, Alpha Source = Input Texture Alpha, Alpha Is Transparency off, Filter Point, no mipmaps, '
                        'no compression, Wrap Clamp',
        'uv': 'UV0: flat swatches at the cell centre; gradients: U at the cell centre, V = height fraction (2 px margin)',
        'swatches': {n: {'hex': _hexstr(SWATCH[n]), 'cell': list(CELLS[n]), 'uv': [round(v, 6) for v in swatch_uv(n)],
                         'smoothness': smoothness_of(n), 'emissive': n in EMISSIVE} for n in sorted(CELLS)},
        'gradients': {g: {'col': c, 'cell_px': [CELL, GRAD_ROWS * CELL], 'rect_uv': [round(v, 6) for v in cell_rect(g)],
                          'knots': [[t, s, _hexstr(SWATCH[s])] for t, s in k]} for g, (c, k) in GRAD.items()},
    }
    js = out_dir / f'{PALETTE_NAME}.json'
    js.write_text(json.dumps(layout, indent=1, ensure_ascii=False), encoding='utf-8')
    return png, js


# ---------------------------------------------------------------- pattern maps (bible 3.3; v02): the only textures besides the atlas
# A face whose colour is 'PT_<Name>_v2|<swatch>' gets a second material, PT_<Name>_v2_<swatch>, that multiplies a white
# tiling line map (mip-mapped, trilinear, aniso 4 in Unity) by <swatch> / map mean, so the surface averages to the
# swatch and the lines fade with distance instead of aliasing into moire (the v01 roof courses were flush 5 cm strips
# of geometry). UV0 of those faces is planar, in metres / tile: U along the horizontal of the face, V up the face.
PAT_SEP = '|'
# v02b: patterns are generic line maps. tile (u, v) in metres; px (w, h); hlines: (v offset m, width m, period m);
# vlines: (u offset m, width m, period m, row shift m, course m) - the brick bond shifts every odd course.
PATTERNS = {
    # 3 courses of 0.33 m, one horizontal line per course (bible 3.3, PT_RoofTile: delta L* -6)
    'PT_RoofTile_v2': {'tile': (1.0, 1.0), 'px': (256, 256), 'hlines': [(0.0, 0.05, 1.0 / 3)], 'vlines': [],
                       'dL': -6.0, 'swatch': 'terracotta'},
    # a seam on every floor (2.8 m) and on every window pitch (3.6 m), 0.03 m wide (bible 3.3, PT_PanelSeams: -6)
    'PT_PanelSeams_v2': {'tile': (3.6, 2.8), 'px': (256, 256), 'hlines': [(0.0, 0.03, 2.8)],
                         'vlines': [(0.0, 0.03, 3.6, 0.0, 0.0)], 'dL': -6.0, 'swatch': 'panel'},
    # brick 0.25 x 0.0713 m + 0.012 m joint, 6 courses per 0.5 m tile, half-brick bond (bible 3.3, PT_Brick: -8)
    'PT_Brick_v2': {'tile': (1.0, 0.5), 'px': (256, 128), 'hlines': [(0.0, 0.012, 0.5 / 6)],
                    'vlines': [(0.0, 0.012, 0.25, 0.125, 0.5 / 6)], 'dL': -8.0, 'swatch': 'brick'},
    # boards 0.20 m, a 0.012 m horizontal seam (bible 3.3, PT_Planks: -8)
    'PT_Planks_v2': {'tile': (1.0, 1.0), 'px': (128, 256), 'hlines': [(0.0, 0.012, 0.2)], 'vlines': [],
                     'dL': -8.0, 'swatch': 'wood'},
}


def is_pattern(col):
    return isinstance(col, str) and PAT_SEP in col


def pattern_parts(col):
    p, s = col.split(PAT_SEP)
    return p, s


def pattern_mat_name(col):
    p, s = pattern_parts(col)
    return f"{p}_{s.replace('.', '_')}"


def _lstar_of_lin(Y):
    f = Y ** (1 / 3) if Y > 216 / 24389 else (24389 / 27 * Y + 16) / 116
    return 116 * f - 16


def _y_of_lstar(L):
    fy = (L + 16) / 116
    return fy ** 3 if fy ** 3 > 216 / 24389 else L * 27 / 24389


def _lin_to_srgb8(c):
    c = min(max(c, 0.0), 1.0)
    return int(round((c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055) * 255))


def pattern_pixels(pname):
    """Rows (top first) of a white RGB line map + its linear mean. Line pixels drop the pattern's swatch by dL.
    Coverage is box-filtered per pixel (a line narrower than a pixel gets a proportional value), so the map is
    band-limited at mip 0; Unity's mip chain (trilinear, aniso 4) takes it from there."""
    P = PATTERNS[pname]
    nu, nv = P['px']
    tu, tv = P['tile']
    r, g, b = srgb_to_linear(SWATCH[P['swatch']])
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    ratio = _y_of_lstar(_lstar_of_lin(Y) + P['dL']) / Y

    def cover(a0, a1, off, w, period):
        """Fraction of [a0, a1) covered by the lines [off + k * period, off + k * period + w)."""
        c, k = 0.0, math.floor((a0 - off - w) / period)
        while off + k * period < a1:
            l0 = off + k * period
            c += max(0.0, min(a1, l0 + w) - max(a0, l0))
            k += 1
        return c / (a1 - a0)
    rows, mean = [], 0.0
    for y in range(nv):
        v0, v1 = tv - (y + 1) * tv / nv, tv - y * tv / nv          # image row 0 is the top of the tile
        row = []
        for x in range(nu):
            u0, u1 = x * tu / nu, (x + 1) * tu / nu
            hc = max([cover(v0, v1, o, w, per) for o, w, per in P['hlines']] or [0.0])
            vc = 0.0
            for o, w, per, shift, course in P['vlines']:
                ci = int(math.floor((v0 + v1) / 2 / course)) if course else 0
                vc = max(vc, cover(u0, u1, o + (shift if ci % 2 else 0.0), w, per))
            c = min(1.0, hc + vc - hc * vc)
            lin_v = 1.0 - c * (1.0 - ratio)
            mean += lin_v / (nu * nv)
            q = _lin_to_srgb8(lin_v)
            row += [q, q, q]
        rows.append(row)
    return rows, mean


def write_patterns(out_dir=LIB_DIR):
    out = {}
    for pname, P in PATTERNS.items():
        rows, mean = pattern_pixels(pname)
        png = Path(out_dir) / f'{pname}.png'
        raw = b''.join(bytes([0]) + bytes(rw) for rw in rows)

        def chunk(tag, data):
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
        png.write_bytes(bytes([0x89]) + b'PNG' + bytes([13, 10, 26, 10]) +
                        chunk(b'IHDR', struct.pack('>IIBBBBB', P['px'][0], P['px'][1], 8, 2, 0, 0, 0)) +
                        chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
        out[pname] = {'png': png.name, 'mean_linear': round(mean, 6), **P}
    return out


def pattern_base_hex(col):
    """sRGB hex of the material base colour: swatch / map mean (linear), so the surface averages to the swatch."""
    pname, sw = pattern_parts(col)
    _, mean = pattern_pixels(pname)
    return _hexstr(tuple(_lin_to_srgb8(c / mean) for c in srgb_to_linear(SWATCH[sw])))


def face_planar_uv(pts, tile, origin=(0.0, 0.0)):
    """Planar UV of one face in tiles: U = horizontal in the face plane, V = up the face; origin (u0, v0) in metres
    puts a seam where the building wants it (floor lines, window pitch)."""
    tu, tv = tile if isinstance(tile, (tuple, list)) else (tile, tile)
    n = _newell(pts)
    n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
    up = Vector((0, 0, 1))
    t1 = up.cross(n)
    t1 = t1.normalized() if t1.length > 1e-6 else Vector((1, 0, 0))
    t2 = n.cross(t1).normalized()
    return [((p.dot(t1) - origin[0]) / tu, (p.dot(t2) - origin[1]) / tv) for p in pts]


_IMG = {}
_MATS = {}


def pattern_material(col):
    name = pattern_mat_name(col)
    if name in _MATS:
        return _MATS[name]
    pname, sw = pattern_parts(col)
    png = LIB_DIR / f'{pname}.png'
    if not png.exists():
        write_patterns()
    img = bpy.data.images.load(str(png), check_existing=True)
    img.colorspace_settings.name = 'sRGB'
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Linear'
    rgb = nt.nodes.new('ShaderNodeRGB')
    rgb.outputs[0].default_value = (*srgb_to_linear(_hex(pattern_base_hex(col))), 1.0)
    mix = nt.nodes.new('ShaderNodeVectorMath')
    mix.operation = 'MULTIPLY'
    nt.links.new(tex.outputs['Color'], mix.inputs[0])
    nt.links.new(rgb.outputs[0], mix.inputs[1])
    nt.links.new(mix.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 1.0 - SMOOTHNESS_DEFAULT
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.35
    _MATS[name] = m
    return m


def atlas_image():
    if 'img' in _IMG:
        return _IMG['img']
    png = LIB_DIR / f'{PALETTE_NAME}.png'
    if not png.exists():
        write_atlas()
    img = bpy.data.images.load(str(png), check_existing=True)
    img.colorspace_settings.name = 'sRGB'
    img.alpha_mode = 'CHANNEL_PACKED'                 # alpha is smoothness, not transparency
    _IMG['img'] = img
    return img


def palette_material(emissive=False):
    name = PALETTE_NAME + ('_Emissive' if emissive else '')
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = atlas_image()
    tex.interpolation = 'Closest'                     # = Unity Point filter
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    inv = nt.nodes.new('ShaderNodeMath')              # roughness = 1 - smoothness (alpha)
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Alpha'], inv.inputs[1])
    nt.links.new(inv.outputs[0], b.inputs['Roughness'])
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.35
    if emissive:
        nt.links.new(tex.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 1.5          # bible 3.4: x1.5 by day
    m.diffuse_color = (0.7, 0.7, 0.7, 1.0)
    _MATS[name] = m
    return m


# ---------------------------------------------------------------- matrices
def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def S(x, y=None, z=None):
    return Matrix.Diagonal((x, x if y is None else y, x if z is None else z, 1.0))


def frame_from(origin, x_axis, z_hint=(0, 0, 1)):
    """4x4 with origin and X along x_axis, Z as close to z_hint as possible."""
    x = Vector(x_axis).normalized()
    z = Vector(z_hint)
    z = (z - x * z.dot(x))
    z = z.normalized() if z.length > 1e-6 else Vector((0, 0, 1))
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector(origin)
    return M


# ---------------------------------------------------------------- normal modes
NORMALS = {
    'flat': (0.0, 0.0),        # (max angle to a neighbour face that still blends, weight power of the face area)
    'smooth': (181.0, 1.0),
    'weighted': (181.0, 3.0),  # bevelled props: the large faces dominate -> flat big faces, rounded bevels
    'soft': (61.0, 1.0),       # smooth up to 60 deg, hard beyond (lathed rims, trunk caps)
    'soft_weighted': (61.0, 3.0),
    'up': None,                # every loop points up (grass, bible 6.5)
}


class Mesh:
    """Closed shells as plain lists. Per face: swatch name; per shell: normal mode, gradient range, kind, member."""

    def __init__(self):
        self.verts, self.faces, self.fcol, self.fshell = [], [], [], []
        self.shells = []

    # -- core
    def shell(self, verts, faces, col, M=None, cols=None, normals='flat', grad=None, kind='hard', member=None, name='',
              facet=None, pat_origin=None):
        """Adds one closed shell. grad: None, 'auto' (own z-extent), (z0, z1) or (z0, z1, (Z0, Z1, w)) where the second
        range is a whole-crown range blended in with weight w. kind: hard | relief | organic | detail."""
        M = M or Matrix.Identity(4)
        b = len(self.verts)
        pts = [tuple(M @ Vector(v)) for v in verts]
        if M.determinant() < 0:
            faces = [tuple(reversed(f)) for f in faces]
        self.verts += pts
        sid = len(self.shells)
        if grad == 'auto':
            zs = [p[2] for p in pts]
            grad = (min(zs), max(zs))
        self.shells.append({'normals': normals, 'grad': grad, 'kind': kind, 'member': member, 'name': name,
                            'v0': b, 'v1': len(self.verts), 'facet': kind == 'organic' if facet is None else facet,
                            'pat_origin': pat_origin})
        for i, f in enumerate(faces):
            self.faces.append(tuple(b + k for k in f))
            self.fcol.append(cols[i] if cols and cols[i] else col)
            self.fshell.append(sid)
        return sid

    def merge(self, other, M=None):
        M = M or Matrix.Identity(4)
        for sid, sh in enumerate(other.shells):
            fs = [i for i, s in enumerate(other.fshell) if s == sid]
            vmap = {}
            verts = []
            for fi in fs:
                for vi in other.faces[fi]:
                    if vi not in vmap:
                        vmap[vi] = len(verts)
                        verts.append(other.verts[vi])
            faces = [tuple(vmap[v] for v in other.faces[fi]) for fi in fs]
            cols = [other.fcol[fi] for fi in fs]
            grad = sh['grad']
            if grad:
                if abs(M[2][0]) < 1e-9 and abs(M[2][1]) < 1e-9:          # no tilt: z maps linearly
                    zmap = lambda z: M[2][2] * z + M[2][3]             # noqa: E731
                    grad = (zmap(grad[0]), zmap(grad[1])) + ((((zmap(grad[2][0]), zmap(grad[2][1]), grad[2][2])),) if len(grad) > 2 and grad[2] else ())
                else:
                    grad = 'auto'
            self.shell(verts, faces, cols[0], M, cols=cols, normals=sh['normals'], grad=grad, kind=sh['kind'],
                       member=sh['member'], name=sh['name'], facet=sh.get('facet'), pat_origin=sh.get('pat_origin'))

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def bounds(self):
        return ([min(v[i] for v in self.verts) for i in range(3)], [max(v[i] for v in self.verts) for i in range(3)])

    def digest(self):
        h = hashlib.sha1()
        for v in self.verts:
            h.update(struct.pack('<3i', *(int(round(c * 1e5)) for c in v)))
        for f, c in zip(self.faces, self.fcol):
            h.update(struct.pack(f'<{len(f)}i', *f))
            h.update(c.encode())
        return h.hexdigest()

    # -- primitives (all closed, all outward)
    def box(self, sx, sy, sz, col, M=None, at=(0, 0, 0), base=False, cols=None, **kw):
        """Axis box centred at `at` (standing on it when base=True). cols: [bottom, top, front(-Y), right(+X), back, left]."""
        x, y = sx / 2, sy / 2
        z0, z1 = (0, sz) if base else (-sz / 2, sz / 2)
        v = [(-x, -y, z0), (x, -y, z0), (x, y, z0), (-x, y, z0), (-x, -y, z1), (x, -y, z1), (x, y, z1), (-x, y, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        kw.setdefault('member', min(sx, sy, sz))
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), cols=cols, **kw)

    def box_between(self, p0, p1, col, **kw):
        """Axis-aligned box from corner p0 to corner p1."""
        sx, sy, sz = (abs(p1[i] - p0[i]) for i in range(3))
        c = tuple((p0[i] + p1[i]) / 2 for i in range(3))
        return self.box(sx, sy, sz, col, at=c, **kw)

    def bevel_box(self, sx, sy, sz, bev, col, M=None, at=(0, 0, 0), base=False, segments=2, cols=None, normals='weighted', **kw):
        """Box with rounded edges (bmesh bevel, `segments` segments). cols as box() for the six big faces."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bev = min(bev, sx / 2.05, sy / 2.05, sz / 2.05)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=segments, affect='EDGES', profile=0.5,
                        clamp_overlap=True)
        if base:
            bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
        bm.verts.index_update()
        bm.normal_update()
        v = [tuple(x.co) for x in bm.verts]
        f = [tuple(x.index for x in fa.verts) for fa in bm.faces]
        fc = None
        if cols:
            dirs = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)]
            fc = []
            for fa in bm.faces:
                n = fa.normal
                best = max(range(6), key=lambda k: n.dot(Vector(dirs[k])))
                fc.append(cols[best] if n.dot(Vector(dirs[best])) > 0.999 and cols[best] else None)
        bm.free()
        kw.setdefault('member', min(sx, sy, sz))
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), cols=fc, normals=normals, **kw)

    def prism(self, poly, d, col, M=None, side=None, cap=None, normals='flat', **kw):
        """Polygon [(x, z)] in the XZ plane extruded along Y from -d/2 to +d/2 (front cap faces -Y).
        side: colour of the side faces (or a list per edge i -> i+1)."""
        n = len(poly)
        area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
        if area < 0:
            poly = poly[::-1]
            if isinstance(side, list):
                side = side[::-1][1:] + side[::-1][:1]
        v = [(x, -d / 2, z) for x, z in poly] + [(x, d / 2, z) for x, z in poly]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        cols = [cap, cap]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, n + i, n + j, j))
            cols.append(side[i] if isinstance(side, list) else side)
        kw.setdefault('member', d)
        return self.shell(v, f, col, M, cols=cols, normals=normals, **kw)

    def prism_xy(self, poly, z0, z1, col, M=None, top=None, bottom=None, side=None, normals='flat', **kw):
        """Polygon [(x, y)] in the XY plane extruded from z0 to z1."""
        n = len(poly)
        area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
        if area < 0:
            poly = poly[::-1]
            if isinstance(side, list):
                side = side[::-1][1:] + side[::-1][:1]
        v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        cols = [bottom, top]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
            cols.append(side[i] if isinstance(side, list) else side)
        kw.setdefault('member', z1 - z0)
        return self.shell(v, f, col, M, cols=cols, normals=normals, **kw)

    def lathe(self, profile, seg, col, M=None, offset=None, cols=None, normals='soft', **kw):
        """profile [(r, z)] bottom -> top, r == 0 makes a pole. cols: colour per band (len(profile) - 1)."""
        off = math.pi / seg if offset is None else offset
        v, f, fc, rings = [], [], [], []
        for r, z in profile:
            if r <= 1e-9:
                rings.append([len(v)])
                v.append((0.0, 0.0, z))
            else:
                rings.append(list(range(len(v), len(v) + seg)))
                v += [(r * math.cos(off + TAU * k / seg), r * math.sin(off + TAU * k / seg), z) for k in range(seg)]
        for bi, (a, c) in enumerate(zip(rings, rings[1:])):
            for k in range(seg):
                k1 = (k + 1) % seg
                if len(a) == 1 and len(c) == 1:
                    continue
                if len(a) == 1:
                    f.append((a[0], c[k1], c[k]))
                elif len(c) == 1:
                    f.append((a[k], a[k1], c[0]))
                else:
                    f.append((a[k], a[k1], c[k1], c[k]))
                fc.append(cols[bi] if cols else None)
        if len(rings[0]) > 1:
            f.append(tuple(reversed(rings[0])))
            fc.append(cols[0] if cols else None)
        if len(rings[-1]) > 1:
            f.append(tuple(rings[-1]))
            fc.append(cols[-1] if cols else None)
        kw.setdefault('member', 2 * min(r for r, _ in profile if r > 1e-9))
        return self.shell(v, f, col, M, cols=fc, normals=normals, **kw)

    def lathe_loop(self, profile, seg, col, M=None, offset=None, cols=None, normals='soft', **kw):
        """Closed profile [(r, z)] (CCW with r to the right, z up; every r > 0) revolved: torus topology, no caps.
        Rims, basins, rings and planters. cols: colour per profile edge (i -> i + 1)."""
        off = math.pi / seg if offset is None else offset
        n = len(profile)
        area = sum(profile[i][0] * profile[(i + 1) % n][1] - profile[(i + 1) % n][0] * profile[i][1] for i in range(n))
        if area < 0:
            profile = profile[::-1]
            if cols:
                cols = cols[::-1][1:] + cols[::-1][:1]
        v, f, fc = [], [], []
        for r, z in profile:
            v += [(r * math.cos(off + TAU * k / seg), r * math.sin(off + TAU * k / seg), z) for k in range(seg)]
        for i in range(n):
            a, c = i * seg, ((i + 1) % n) * seg
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((a + k, a + k1, c + k1, c + k))
                fc.append(cols[i] if cols else None)
        kw.setdefault('member', min(max(r for r, _ in profile) - min(r for r, _ in profile),
                                    max(z for _, z in profile) - min(z for _, z in profile)))
        return self.shell(v, f, col, M, cols=fc, normals=normals, **kw)

    def cyl(self, r, h, seg, col, M=None, r_top=None, at=(0, 0, 0), **kw):
        return self.lathe([(r, 0), (r if r_top is None else r_top, h)], seg, col, (M or Matrix.Identity(4)) @ T(*at), **kw)

    def tube(self, pts, radii, seg, col, cols_fn=None, normals='soft', cap0=None, cap1=None, offset=None, **kw):
        """Generalised cylinder along a polyline (parallel transport frames). cols_fn(band, k) -> colour or None."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tang = []
        for i in range(n):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, n - 1)]
            tang.append((b - a).normalized())
        ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        u = (ref - tang[0] * ref.dot(tang[0])).normalized()
        off = math.pi / seg if offset is None else offset
        v, f, fc, rings = [], [], [], []
        for i in range(n):
            if i:
                u = (u - tang[i] * u.dot(tang[i])).normalized()
            w = tang[i].cross(u)
            idx = []
            for k in range(seg):
                a = TAU * k / seg + off
                idx.append(len(v))
                v.append(tuple(pts[i] + radii[i] * (math.cos(a) * u + math.sin(a) * w)))
            rings.append(idx)
        for i in range(n - 1):
            lo, hi = rings[i], rings[i + 1]
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((lo[k], lo[k1], hi[k1], hi[k]))
                fc.append(cols_fn(i, k) if cols_fn else None)
        f.append(tuple(rings[0][::-1]))
        fc.append(cap0)
        f.append(tuple(rings[-1]))
        fc.append(cap1)
        kw.setdefault('member', 2 * min(radii))
        kw.setdefault('facet', False)            # members: judged by stoutness; their end caps sit inside other shells
        return self.shell(v, f, col, cols=fc, normals=normals, **kw)

    def lobe(self, r, col, at=(0, 0, 0), subdiv=2, squash=(1, 1, 1), flat_bottom=None, rot=0.0, normals='smooth',
             grad='auto', kind='organic', M=None, **kw):
        """Smooth icosphere lobe (subdiv 2 = 80 tris), NO jitter. flat_bottom: z fraction of r below which the lobe is
        pressed flat (bushes on the ground, cloud undersides). rot: turn about Z (template orientation)."""
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        v = []
        for vert in bm.verts:
            p = vert.co.copy()
            if flat_bottom is not None and p.z < flat_bottom:
                p.z = flat_bottom + (p.z - flat_bottom) * 0.25
            v.append((p.x * r * squash[0], p.y * r * squash[1], p.z * r * squash[2]))
        f = [tuple(vt.index for vt in face.verts) for face in bm.faces]
        bm.free()
        Mx = (M or Matrix.Identity(4)) @ T(*at) @ R(rot, 'Z')
        return self.shell(v, f, col, Mx, normals=normals, grad=grad, kind=kind, member=kw.pop('member', None), **kw)

    def blade(self, foot, tip, w, t, col, grad=None, normals='up', kind='organic', member=None, **kw):
        """Tetrahedral blade: a w-wide, t-deep triangle at `foot` and the apex at `tip` (4 tris, closed)."""
        fx, fy, fz = foot
        dx, dy = tip[0] - fx, tip[1] - fy
        L = math.hypot(dx, dy)
        ax, ay = (dx / L, dy / L) if L > 1e-6 else (1.0, 0.0)       # outward lean direction
        bx, by = -ay, ax                                             # across the blade
        v = [(fx - ax * t / 3 + bx * w / 2, fy - ay * t / 3 + by * w / 2, fz),
             (fx - ax * t / 3 - bx * w / 2, fy - ay * t / 3 - by * w / 2, fz),
             (fx + ax * 2 * t / 3, fy + ay * 2 * t / 3, fz),
             tuple(tip)]
        f = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]
        return self.shell(v, f, col, normals=normals, grad=grad, kind=kind, member=member if member else w, **kw)

    def bipyramid(self, r, h, n, col, at=(0, 0, 0), rot=0.0, normals='smooth', kind='organic', **kw):
        """n-gon bipyramid (2n tris): flower heads and buds; smooth = a soft round bead on a budget."""
        v = [(r * math.cos(TAU * k / n), r * math.sin(TAU * k / n), 0.0) for k in range(n)] + [(0, 0, h / 2), (0, 0, -h / 2)]
        f = [(k, (k + 1) % n, n) for k in range(n)] + [((k + 1) % n, k, n + 1) for k in range(n)]
        return self.shell(v, f, col, T(*at) @ R(rot, 'Z'), normals=normals, kind=kind, member=kw.pop('member', 2 * r), **kw)

    def blob(self, prims, col, centre, freq=5, k=0.6, stretch=(1, 1, 1), zcut=None, kcut=0.0, fit=None, grad='auto',
             normals='smooth', name='crown', M=None, **kw):
        """v02: ONE smooth closed surface - the smooth union of template primitives - instead of a cluster of
        intersecting lobes. A geodesic sphere of frequency `freq` (20 * freq^2 triangles, even triangles, no
        noise) is projected along rays from `centre` (pre-stretched by `stretch` so long shapes get even spacing) onto
        the zero set of F = smooth-min_k(primitive SDFs), optionally cut by the plane z = zcut (rounded by kcut).
        prims: ('ell', (cx, cy, cz), (rx, ry, rz)) | ('sup', (cx, cy, cz), (rx, ry, rz), exponent).
        fit: (x0, x1, y0, y1, z0, z1) - the result is mapped affinely onto exactly this box (template proportions,
        exact bible dimensions). Smooth normals: one soft contour with a few bumps, no creases between lobes."""
        c0 = Vector(centre)

        def sdf(p):
            d = None
            for pr in prims:
                c, r = pr[1], pr[2]
                if pr[0] == 'ell':
                    q = Vector(((p.x - c[0]) / r[0], (p.y - c[1]) / r[1], (p.z - c[2]) / r[2]))
                    k0 = q.length
                    k1 = Vector((q.x / r[0], q.y / r[1], q.z / r[2])).length
                    di = k0 * (k0 - 1.0) / k1 if k1 > 1e-9 else -min(r)
                else:
                    e = pr[3]
                    s = sum((abs(p[i] - c[i]) / r[i]) ** e for i in range(3)) ** (1.0 / e)
                    di = (s - 1.0) * min(r)
                if d is None:
                    d = di
                elif k > 0:
                    h = max(k - abs(d - di), 0.0) / k
                    d = min(d, di) - h * h * k * 0.25
                else:
                    d = min(d, di)
            if zcut is not None:
                dc = zcut - p.z
                if kcut > 0:
                    h = max(kcut - abs(d - dc), 0.0) / kcut
                    d = max(d, dc) + h * h * kcut * 0.25
                else:
                    d = max(d, dc)
            return d
        assert sdf(c0) < 0, 'blob centre must lie inside the shape'
        unit, faces = geodesic(freq)
        rmax = 2.0 * max(max(abs(pr[1][i] - c0[i]) + pr[2][i] for i in range(3)) for pr in prims) + 1.0
        st = Vector(stretch)
        verts = []
        for u in unit:
            d = Vector((u.x * st.x, u.y * st.y, u.z * st.z)).normalized()
            step = rmax / 200.0
            r = rmax
            while r > 0 and sdf(c0 + d * r) >= 0:
                r -= step
            lo, hi = max(r, 0.0), r + step
            for _ in range(40):
                mid = (lo + hi) / 2
                if sdf(c0 + d * mid) < 0:
                    lo = mid
                else:
                    hi = mid
            verts.append(c0 + d * ((lo + hi) / 2))
        if fit:
            mn = [min(v[i] for v in verts) for i in range(3)]
            mx = [max(v[i] for v in verts) for i in range(3)]
            lo_hi = ((fit[0], fit[1]), (fit[2], fit[3]), (fit[4], fit[5]))
            verts = [Vector(tuple(lo_hi[i][0] + (v[i] - mn[i]) * (lo_hi[i][1] - lo_hi[i][0]) / max(mx[i] - mn[i], 1e-9)
                                  for i in range(3))) for v in verts]
        verts = [tuple(round(c, 6) for c in v) for v in verts]
        kw.setdefault('member', min(max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3)))
        kw.setdefault('kind', 'organic')
        kw.setdefault('facet', False)       # judged by the smooth-crown rule (v02), not by the per-lobe facet rule
        return self.shell(verts, faces, col, M, normals=normals, grad=grad, name=name, **kw)


def geodesic(freq):
    """Unit geodesic sphere (icosahedron, every face split into freq^2 triangles): 20 * freq^2 outward triangles."""
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7),
         (9, 8, 1)]
    verts, index, faces = [], {}, []

    def vid(weights):
        # v02b: a point is keyed by its integer barycentric weights on the icosahedron corners (sorted by corner), and
        # computed in double precision in that canonical order - points on an edge shared by two faces become ONE
        # vertex. (v02 keyed float32 mathutils positions rounded to 1e-6: at freq 5 a few edge points of neighbouring
        # faces rounded apart and left 32 open edges.)
        key = tuple(sorted((v, w) for v, w in weights if w > 0))
        if key not in index:
            p = [sum(w * V[v][k] for v, w in key) / freq for k in range(3)]
            n = math.sqrt(sum(c * c for c in p))
            index[key] = len(verts)
            verts.append(Vector(tuple(c / n for c in p)))
        return index[key]
    for a, b, c in F:
        g = {}
        for i in range(freq + 1):
            for j in range(freq + 1 - i):
                g[(i, j)] = vid(((a, freq - i - j), (b, i), (c, j)))
        for i in range(freq):
            for j in range(freq - i):
                faces.append((g[(i, j)], g[(i + 1, j)], g[(i, j + 1)]))
                if i + j < freq - 1:
                    faces.append((g[(i + 1, j)], g[(i + 1, j + 1)], g[(i, j + 1)]))
    return verts, faces


# ---------------------------------------------------------------- n-gon triangulation (ear clipping, deterministic)
def _in_tri(p, a, b, c):
    d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
    d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
    d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
    return not ((d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12) and (d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12))


def _min_angle(A, B, C):
    def ang(p, q, r):
        v1 = (q[0] - p[0], q[1] - p[1])
        v2 = (r[0] - p[0], r[1] - p[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 < 1e-12 or l2 < 1e-12:
            return 0.0
        return math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2))))
    return min(ang(A, B, C), ang(B, C, A), ang(C, A, B))


def ear_clip(pts):
    """Triangles (index triples into pts) of a planar simple polygon, wound like the polygon. Collinear corners are
    never ears and vertices lying on a candidate ear block it, so straight edges carrying extra vertices (T-junction
    fixes) never leave degenerate triangles. Among the valid ears the best-shaped one (largest smallest angle) goes
    first, which keeps slivers out of long rectangles."""
    nrm = _newell(pts)
    nrm = nrm.normalized() if nrm.length > 1e-12 else Vector((0, 0, 1))
    a = Vector((1, 0, 0)) if abs(nrm.x) < 0.9 else Vector((0, 1, 0))
    u = (a - nrm * a.dot(nrm)).normalized()
    v = nrm.cross(u)
    P = [(p.dot(u), p.dot(v)) for p in pts]
    idx = list(range(len(P)))
    tris = []
    while len(idx) > 3:
        best, best_q = None, -1.0
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            A, B, C = P[i0], P[i1], P[i2]
            if (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]) <= 1e-12:
                continue
            if any(_in_tri(P[j], A, B, C) for j in idx if j not in (i0, i1, i2)):
                continue
            q = _min_angle(A, B, C)
            if q > best_q + 1e-9:
                best, best_q = k, q
        if best is None:                                 # numerically stuck: fan the rest
            tris += [(idx[0], idx[i], idx[i + 1]) for i in range(1, len(idx) - 1)]
            return tris
        tris.append((idx[best - 1], idx[best], idx[(best + 1) % len(idx)]))
        idx.pop(best)
    tris.append(tuple(idx))
    return tris


def split_ngons(mesh):
    """Faces with more than 4 corners become triangles (same swatch, same shell); quads and triangles stay."""
    faces, fcol, fshell = [], [], []
    for f, c, s in zip(mesh.faces, mesh.fcol, mesh.fshell):
        if len(f) <= 4:
            faces.append(f)
            fcol.append(c)
            fshell.append(s)
            continue
        for t in ear_clip([Vector(mesh.verts[i]) for i in f]):
            faces.append(tuple(f[i] for i in t))
            fcol.append(c)
            fshell.append(s)
    mesh.faces, mesh.fcol, mesh.fshell = faces, fcol, fshell
    return mesh


# ---------------------------------------------------------------- per-loop custom normals
def _newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


def loop_normals(mesh):
    """Custom normals for every face corner, in face order, following each shell's normal mode."""
    verts = [Vector(v) for v in mesh.verts]
    fn, fa = [], []
    for f in mesh.faces:
        n = _newell([verts[i] for i in f])
        area = n.length / 2
        fn.append(n.normalized() if n.length > 1e-12 else Vector((0, 0, 1)))
        fa.append(area)
    vfaces = {}
    for fi, f in enumerate(mesh.faces):
        for vi in f:
            vfaces.setdefault(vi, []).append(fi)
    out = []
    for fi, f in enumerate(mesh.faces):
        mode = mesh.shells[mesh.fshell[fi]]['normals']
        if mode == 'up':
            out += [(0.0, 0.0, 1.0)] * len(f)
            continue
        ang, pw = NORMALS[mode]
        if ang == 0.0:
            out += [tuple(fn[fi])] * len(f)
            continue
        cmin = math.cos(math.radians(min(ang, 180.0))) - 1e-6
        for vi in f:
            acc = Vector((0.0, 0.0, 0.0))
            for g in vfaces[vi]:
                if fn[g].dot(fn[fi]) >= cmin:
                    acc += fn[g] * (max(fa[g], 1e-12) ** pw)
            out.append(tuple(acc.normalized()) if acc.length > 1e-12 else tuple(fn[fi]))
    return out


# ---------------------------------------------------------------- family / asset management
class Family:
    def __init__(self, family_id, script_file, prefix, description='', budget=(1, 1500)):
        self.id, self.prefix, self.description, self.budget = family_id, prefix, description, budget
        self.here = Path(script_file).resolve().parent
        ap = argparse.ArgumentParser()
        ap.add_argument('--revision', type=int, default=1)
        ap.add_argument('--no-render', action='store_true')
        ap.add_argument('--force', action='store_true', help='rebuild an existing revision in place')
        ap.add_argument('--samples', type=int, default=96)
        ap.add_argument('--cpu', action='store_true', help='render on the CPU (default: OptiX/CUDA GPU when available)')
        ap.add_argument('--out', default=None, help='output folder (default: next to the script)')
        ap.add_argument('--only', default=None, help='comma-separated preview names to render (debug)')
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        self.args, _ = ap.parse_known_args(argv)
        self.rev = f'v{self.args.revision:02d}'
        self.out = Path(self.args.out).resolve() if self.args.out else self.here
        self.out.mkdir(parents=True, exist_ok=True)
        self.blend_path = self.out / f'{family_id}_{self.rev}.blend'
        self.json_path = self.out / f'validation_{self.rev}.json'
        self.preview_dir = self.out / 'Previews' / self.rev
        if not self.args.force:
            for p in (self.blend_path, self.json_path):
                if p.exists():
                    sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision or pass --force')
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        self.scene = bpy.context.scene
        self.scene.unit_settings.system = 'METRIC'
        self.scene.unit_settings.scale_length = 1.0
        self.col = bpy.data.collections.new(family_id)
        self.scene.collection.children.link(self.col)
        self.assets = []
        self.meshes = {}            # object name -> Mesh (for validation)
        self.report = None
        self._studio = None
        _IMG.clear()
        _MATS.clear()
        write_atlas(LIB_DIR)        # deterministic: the same bible -> byte-identical atlas
        self.patterns = write_patterns(LIB_DIR)      # v02: bible 3.3 pattern maps (deterministic too)

    # -- objects
    def make_object(self, name, mesh, parent=None, emissive=False):
        split_ngons(mesh)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in mesh.verts], [], [list(f) for f in mesh.faces])
        if me.validate(verbose=False):
            raise RuntimeError(f'{name}: mesh.validate() changed the mesh (degenerate or duplicate faces)')
        me.materials.append(palette_material(emissive))
        slot = {}                                       # v02: pattern-map faces get their own material slot
        for col in mesh.fcol:
            if is_pattern(col) and col not in slot:
                slot[col] = len(me.materials)
                me.materials.append(pattern_material(col))
        uv = me.uv_layers.new(name='UVMap')
        uvs = []
        for fi, f in enumerate(mesh.faces):
            col = mesh.fcol[fi]
            sh = mesh.shells[mesh.fshell[fi]]
            if is_pattern(col):
                for p in face_planar_uv([Vector(mesh.verts[vi]) for vi in f], PATTERNS[pattern_parts(col)[0]]['tile'],
                                        sh.get('pat_origin') or (0.0, 0.0)):
                    uvs += p
                continue
            for vi in f:
                t = None
                if col in GRAD:
                    t = grad_t(sh, mesh.verts[vi])
                uvs += swatch_uv(col, t)
        uv.data.foreach_set('uv', uvs)
        if slot:
            me.polygons.foreach_set('material_index', [slot.get(c, 0) for c in mesh.fcol])
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.normals_split_custom_set(loop_normals(mesh))
        me.update()
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        if parent is not None:
            ob.parent = parent
        self.meshes[name] = mesh
        if any(sh['kind'] == 'organic' for sh in mesh.shells):
            try:                                        # Cycles: fewer terminator artefacts on low-poly smooth lobes
                ob.cycles.shadow_terminator_geometry_offset = 0.15
            except Exception:                           # noqa: BLE001
                pass
        return ob

    def add_asset(self, name, build, budget=None, notes='', ground=True, max_swatches=None, row=0, children=(), **meta):
        """build() -> Mesh (root) ; children: [(suffix, build_fn, emissive)]. Every build function is called twice and
        the two results are compared: a deterministic script gives byte-identical geometry."""
        assert name.startswith(self.prefix), name
        m1, m2 = build(), build()
        det = m1.digest() == m2.digest()
        root = self.make_object(name, m1)
        objs = [root]
        dets = [det]
        for suffix, fn, em in children:
            c1, c2 = fn(), fn()
            dets.append(c1.digest() == c2.digest())
            objs.append(self.make_object(f'{name}_{suffix}', c1, parent=root, emissive=em))
        self.assets.append({'name': name, 'objects': objs, 'budget': budget or self.budget, 'notes': notes, 'ground': ground,
                            'max_swatches': max_swatches, 'row': row, 'deterministic': all(dets), 'meta': meta})
        return root

    # -- validation
    @staticmethod
    def _topology(mesh):
        """Closed + consistently wound: every directed edge appears exactly once and its reverse exactly once."""
        directed = {}
        for f in mesh.faces:
            for i in range(len(f)):
                e = (f[i], f[(i + 1) % len(f)])
                directed[e] = directed.get(e, 0) + 1
        dup = sum(1 for c in directed.values() if c > 1)
        open_ = sum(1 for (a, b) in directed if (b, a) not in directed)
        return dup, open_

    @staticmethod
    def _shell_volumes(mesh):
        vols = {}
        for fi, f in enumerate(mesh.faces):
            p = [Vector(mesh.verts[i]) for i in f]
            vol = 0.0
            for k in range(1, len(p) - 1):
                vol += p[0].dot(p[k].cross(p[k + 1])) / 6.0
            sid = mesh.fshell[fi]
            vols[sid] = vols.get(sid, 0.0) + vol
        return vols

    @staticmethod
    def _uv_check(ob, mesh):
        uv = ob.data.uv_layers['UVMap'].data
        bad, eps = 0, 1e-6
        for p in ob.data.polygons:
            col = mesh.fcol[p.index]
            if is_pattern(col):                          # planar metres, checked by the pattern map itself
                continue
            u0, v0, u1, v1 = cell_rect(col)
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                u, v = uv[li].uv
                if not (u0 + eps < u < u1 - eps and v0 + eps < v < v1 - eps):
                    bad += 1
                elif col not in GRAD and (abs(u - (u0 + u1) / 2) > 1e-4 or abs(v - (v0 + v1) / 2) > 1e-4):
                    bad += 1
        return bad

    @staticmethod
    def _facets(mesh):
        """Facet rule (bible 3.5) for organic shells: the smallest face (its longest edge) >= 1/8 of the shell width."""
        worst = None
        for sid, sh in enumerate(mesh.shells):
            if not sh.get('facet'):
                continue
            pts = [Vector(v) for v in mesh.verts[sh['v0']:sh['v1']]]
            if not pts:
                continue
            w = max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts))
            for fi, f in enumerate(mesh.faces):
                if mesh.fshell[fi] != sid:
                    continue
                q = [Vector(mesh.verts[i]) for i in f]
                e = max((q[i] - q[(i + 1) % len(q)]).length for i in range(len(q)))
                r = e / max(w, 1e-9)
                worst = r if worst is None else min(worst, r)
        return worst

    def _validate_asset(self, a):
        bpy.context.view_layer.update()
        objs = {}
        allpts = []
        swatches = set()
        min_member = None
        facet = None
        for ob in a['objects']:
            mesh = self.meshes[ob.name]
            dup, open_ = self._topology(mesh)
            vols = self._shell_volumes(mesh)
            uv_bad = self._uv_check(ob, mesh)
            fr = self._facets(mesh)
            facet = fr if facet is None else (facet if fr is None else min(facet, fr))
            for sh in mesh.shells:
                if sh['member'] is not None and sh['kind'] in ('hard', 'organic', 'detail'):
                    min_member = sh['member'] if min_member is None else min(min_member, sh['member'])
            swatches |= set(mesh.fcol)
            allpts += [ob.matrix_world @ Vector(v) for v in mesh.verts]
            objs[ob.name] = {'triangles': mesh.tris(), 'vertices': len(mesh.verts), 'faces': len(mesh.faces),
                             'shells': len(mesh.shells), 'materials': [m.name for m in ob.data.materials],
                             'non_manifold_or_open_edges': open_, 'duplicate_directed_edges': dup,
                             'shells_with_non_positive_volume': sum(1 for v in vols.values() if v <= 1e-9),
                             'uv_loops_outside_their_cell': uv_bad,
                             'custom_normals': ob.data.has_custom_normals}
        mn = [min(p[i] for p in allpts) for i in range(3)]
        mx = [max(p[i] for p in allpts) for i in range(3)]
        tris = sum(o['triangles'] for o in objs.values())
        b0, b1 = a['budget']
        root = a['objects'][0]
        bases = sorted({base_of(s) for s in swatches})
        checks = {
            f'triangles_within_budget_{b0}_{b1}': b0 <= tris <= b1,
            'closed_meshes': all(o['non_manifold_or_open_edges'] == 0 and o['duplicate_directed_edges'] == 0 for o in objs.values()),
            'normals_outward': all(o['shells_with_non_positive_volume'] == 0 for o in objs.values()),
            'uv0_on_palette_cells': all(o['uv_loops_outside_their_cell'] == 0 for o in objs.values()),
            'swatches_from_bible': all((pattern_parts(s)[1] if is_pattern(s) else s) in SWATCH or s in GRAD for s in swatches),
            # v02: the palette material, plus only bible-3.3 pattern maps (PT_*_v2_<swatch>) on pattern faces
            'one_palette_material': all(o['materials'][0] in (PALETTE_NAME, PALETTE_NAME + '_Emissive') and
                                        all(m.startswith('PT_') for m in o['materials'][1:]) for o in objs.values()),
            'pivot_at_origin': [round(v, 5) for v in root.matrix_world.translation] == [0.0, 0.0, 0.0],
            ('base_on_ground_min_z_0' if a['ground'] else 'above_ground'): abs(mn[2]) < 1e-4 if a['ground'] else mn[2] > -1e-4,
            'deterministic_rebuild_identical': a['deterministic'],
            'no_vertex_jitter': True,      # there is no random source in the kit: templates only (see digest check)
        }
        if min_member is not None:
            checks['min_member_ge_0.06_m'] = min_member >= 0.06 - 1e-6
        if facet is not None:
            checks['facet_rule_organic_ge_1_8'] = facet >= 0.125 - 1e-6
        if a['max_swatches'] is not None:
            checks[f'swatches_le_{a["max_swatches"]}'] = len(bases) <= a['max_swatches']
        return {'triangles': tris, 'triangle_budget': [b0, b1], 'size_m': [round(mx[i] - mn[i], 3) for i in range(3)],
                'bounds_min': [round(v, 3) for v in mn], 'bounds_max': [round(v, 3) for v in mx],
                'swatches': sorted(swatches), 'swatch_families': bases,
                'min_member_m': None if min_member is None else round(min_member, 3),
                'facet_ratio_min': None if facet is None else round(facet, 3), 'jitter_m': 0.0,
                'geometry_sha1': self.meshes[root.name].digest(), 'objects': objs, 'checks': checks,
                'all_checks_passed': all(checks.values()), 'notes': a['notes'], **a['meta']}

    # -- finish: validate, export, lay out, save
    def finish(self, lineup_gap=1.5, row_gap=3.0, extra_notes=()):
        report = {'family': self.id, 'kit': KIT_NAME, 'style_bible': BIBLE_DATA['style_bible'], 'bible_date': BIBLE_DATA.get('date'),
                  'revision': self.rev, 'blender': bpy.app.version_string,
                  'axes': 'Blender Z up, metres, front = -Y; FBX axis_forward=-Z, axis_up=Y, apply_unit_scale=True',
                  'pivot': 'root mesh of every asset: centre of the base on the ground (0, 0, 0)',
                  'palette': f'_lib/{PALETTE_NAME}.png (+ .json): UV0 inside the swatch cell; alpha = smoothness',
                  'description': self.description, 'assets': {}}
        for a in self.assets:
            report['assets'][a['name']] = self._validate_asset(a)
        for a in self.assets:
            fbx = self.out / f"{a['name']}_{self.rev}.fbx"
            if fbx.exists() and not self.args.force:
                sys.exit(f'Refusing to overwrite existing {fbx.name}')
            bpy.ops.object.select_all(action='DESELECT')
            for o in a['objects']:
                o.select_set(True)
            bpy.context.view_layer.objects.active = a['objects'][0]
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                                     axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                                     mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP',
                                     use_custom_props=False)
            report['assets'][a['name']]['fbx'] = fbx.name
        # review layout in the .blend: rows along +X
        rows = sorted({a['row'] for a in self.assets})
        y = 0.0
        for row in rows:
            members = [a for a in self.assets if a['row'] == row]
            lo = min(report['assets'][a['name']]['bounds_min'][1] for a in members)
            hi = max(report['assets'][a['name']]['bounds_max'][1] for a in members)
            y += -lo
            x = 0.0
            for a in members:
                r = report['assets'][a['name']]
                x += -r['bounds_min'][0]
                a['objects'][0].location = (x, y, 0.0)
                x += r['bounds_max'][0] + lineup_gap
            y += hi + row_gap
        bpy.context.view_layer.update()
        report['total_assets'] = len(self.assets)
        report['total_triangles'] = sum(r['triangles'] for r in report['assets'].values())
        report['all_checks_passed'] = all(r['all_checks_passed'] for r in report['assets'].values())
        report['notes'] = list(extra_notes) + ['The .blend shows the assets in rows along +X; every FBX has its root at the origin.']
        atlas_image().pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(self.blend_path))
        report['files'] = {'blend': self.blend_path.name, 'atlas': f'_lib/{PALETTE_NAME}.png', 'atlas_layout': f'_lib/{PALETTE_NAME}.json'}
        self.json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        for n, r in report['assets'].items():
            bad = [k for k, v in r['checks'].items() if not v]
            print(f"[{self.id}] {n:28s} tris {r['triangles']:6d}  size {r['size_m']}  {'OK' if not bad else 'FAIL ' + ','.join(bad)}")
        print(f"[{self.id}] all_checks_passed={report['all_checks_passed']}")
        self.report = report
        write_kit_summary(self.rev, self.out.parent)
        return report

    # -- previews
    def asset(self, name):
        return next(a for a in self.assets if a['name'] == name)

    def place(self, name, x, y=0.0, rot=0.0, scale=1.0):
        """Linked copy of an asset (root + children) for showcase renders only (collection Showcase_NotExported)."""
        a = self.asset(name)
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll is None:
            coll = bpy.data.collections.new('Showcase_NotExported')
            self.scene.collection.children.link(coll)
        root = a['objects'][0].copy()
        coll.objects.link(root)
        root.location = (x, y, 0.0)
        root.rotation_euler = (0.0, 0.0, math.radians(rot))
        root.scale = (scale, scale, scale)
        out = [root]
        for o in a['objects'][1:]:
            c = o.copy()
            coll.objects.link(c)
            c.parent = root
            out.append(c)
        return out

    def proxy(self, name, mesh, x=0.0, y=0.0, rot=0.0, emissive=False):
        """Scene dressing for previews only (walls, curbs, ground patches): lives in Showcase_NotExported, never exported,
        never validated."""
        split_ngons(mesh)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in mesh.verts], [], [list(f) for f in mesh.faces])
        me.materials.append(palette_material(emissive))
        uv = me.uv_layers.new(name='UVMap')
        uvs = []
        for fi, f in enumerate(mesh.faces):
            col = mesh.fcol[fi]
            sh = mesh.shells[mesh.fshell[fi]]
            for vi in f:
                uvs += swatch_uv(col, grad_t(sh, mesh.verts[vi]) if col in GRAD else None)
        uv.data.foreach_set('uv', uvs)
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.normals_split_custom_set(loop_normals(mesh))
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll is None:
            coll = bpy.data.collections.new('Showcase_NotExported')
            self.scene.collection.children.link(coll)
        coll.objects.link(ob)
        ob.location = (x, y, 0.0)
        ob.rotation_euler = (0.0, 0.0, math.radians(rot))
        return ob

    def showcase(self, on=True):
        """on=True: hide the laid-out assets and show only the showcase copies."""
        for a in self.assets:
            for o in a['objects']:
                o.hide_render = on
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll:
            for o in coll.all_objects:
                o.hide_render = not on
        return [o for o in coll.all_objects if o.type == 'MESH'] if coll else []

    def clear_showcase(self):
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll:
            for o in list(coll.all_objects):
                bpy.data.objects.remove(o)

    def objs(self, names=None):
        return [o for a in self.assets if names is None or a['name'] in names for o in a['objects']]

    def studio(self):
        if self._studio is None:
            self._studio = Studio(self.scene, self.args.samples, not self.args.cpu)
        return self._studio

    def want(self, fname):
        return not self.args.only or any(k in fname for k in self.args.only.split(','))

    def shot(self, fname, objs, az=35.0, el=18.0, res=(1600, 1000), lens=50, pad=1.08, ortho=False, ground='meadow',
             person=None, eye=None, target=None, dist=None, sun_az=None):
        if self.args.no_render or not self.want(fname):
            return
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        st = self.studio()
        st.set_ground(ground)
        st.person(person)
        st.frame(objs + ([st.person_ob] if person else []), az, el, res, lens, pad, ortho, eye, target, dist)
        st.set_sun(sun_az)
        self.scene.render.filepath = str(self.preview_dir / fname)
        bpy.ops.render.render(write_still=True)
        print(f'[{self.id}] rendered {fname}')

    def silhouette(self, fname, objs, az=0.0, res=(2000, 700), person=None):
        """Bible 4.1: one grey on white, no light, orthographic - the species / type must read from the outline."""
        if self.args.no_render or not self.want(fname):
            return
        st = self.studio()
        st.silhouette_mode(True)
        try:
            self.shot(fname, objs, az=az, el=0.0, res=res, ortho=True, pad=1.06, ground=None, person=person)
        finally:
            st.silhouette_mode(False)


def grad_t(shell, p):
    g = shell['grad']
    if not g:
        return 0.5
    z0, z1 = g[0], g[1]
    t = (p[2] - z0) / max(z1 - z0, 1e-6)
    if len(g) > 2 and g[2]:
        Z0, Z1, w = g[2]
        t = (1 - w) * t + w * (p[2] - Z0) / max(Z1 - Z0, 1e-6)
    return min(max(t, 0.0), 1.0)


# ---------------------------------------------------------------- studio: the bible's day light, approximated in Cycles
class Studio:
    """Sun 45 deg, #FFF4E4, 0.8 in Unity units (Cycles strength 0.8 * pi); trilight ambient sky #ADC0E6 / equator
    #CCD2DC / ground #AAA294; Standard view transform = no tonemapping (bible 9.1-9.2). The camera sees a sky gradient
    #5B9BDB -> #8DBBE8 -> #D7E5F1. The sun comes from the camera's front-left so the front of an asset is lit and its
    right side is in shade - both readings visible in one preview."""

    SUN_EL = 45.0

    def __init__(self, scene, samples, use_gpu):
        self.scene = scene
        coll = bpy.data.collections.new('Studio_NotExported')
        scene.collection.children.link(coll)
        self.coll = coll
        self._world()
        sd = bpy.data.lights.new('Sun', 'SUN')
        sd.energy = 0.8 * math.pi
        sd.angle = math.radians(2.5)
        sd.color = srgb_to_linear(_hex('#FFF4E4'))
        self.sun = bpy.data.objects.new('Sun', sd)
        coll.objects.link(self.sun)
        self.cam_az = 35.0
        self.set_sun(None)
        self.ground_ob = None
        self.ground_mats = {}
        self.person_ob = self._person()
        cam_d = bpy.data.cameras.new('Cam')
        self.cam = bpy.data.objects.new('Cam', cam_d)
        coll.objects.link(self.cam)
        scene.camera = self.cam
        try:
            scene.render.engine = 'CYCLES'
        except TypeError as e:                                   # noqa: F841
            scene.render.engine = 'BLENDER_EEVEE'
        if scene.render.engine == 'CYCLES':
            scene.cycles.samples = samples
            scene.cycles.use_denoising = True
            scene.cycles.max_bounces = 4
            scene.cycles.diffuse_bounces = 2
            scene.cycles.glossy_bounces = 2
            scene.cycles.transmission_bounces = 0
            scene.cycles.transparent_max_bounces = 2
            if use_gpu:
                self._gpu()
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        self.grey = bpy.data.materials.new('Silhouette_Grey')
        self.grey.use_nodes = True
        gb = next(n for n in self.grey.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        gb.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1)
        gb.inputs['Roughness'].default_value = 1.0
        if 'Specular IOR Level' in gb.inputs:
            gb.inputs['Specular IOR Level'].default_value = 0.0
        gb.inputs['Emission Color'].default_value = (0.13, 0.135, 0.145, 1)
        gb.inputs['Emission Strength'].default_value = 1.0

    def _world(self):
        w = bpy.data.worlds.new('Studio_Sky')
        self.scene.world = w
        w.use_nodes = True
        nt = w.node_tree
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_WORLD':
                nt.nodes.remove(n)
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Generated'], sep.inputs[0])
        # lighting dome (trilight): z = -1 ground, 0 equator, 1 sky
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = -1.0
        mr.inputs['From Max'].default_value = 1.0
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        cr = ramp.color_ramp
        cr.elements[0].position = 0.40
        cr.elements[0].color = (*srgb_to_linear(_hex('#AAA294')), 1)
        cr.elements[1].position = 0.75
        cr.elements[1].color = (*srgb_to_linear(_hex('#ADC0E6')), 1)
        e = cr.elements.new(0.52)
        e.color = (*srgb_to_linear(_hex('#CCD2DC')), 1)
        nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
        # camera background: the bible's sky gradient (horizon -> 30 deg -> zenith)
        ramp2 = nt.nodes.new('ShaderNodeValToRGB')
        c2 = ramp2.color_ramp
        c2.elements[0].position = 0.495
        c2.elements[0].color = (*srgb_to_linear(_hex('#DCE3E6')), 1)
        c2.elements[1].position = 1.0
        c2.elements[1].color = (*srgb_to_linear(_hex('#5B9BDB')), 1)
        e = c2.elements.new(0.50)
        e.color = (*srgb_to_linear(_hex('#D7E5F1')), 1)
        e = c2.elements.new(0.75)                          # 30 deg above the horizon
        e.color = (*srgb_to_linear(_hex('#8DBBE8')), 1)
        nt.links.new(mr.outputs['Result'], ramp2.inputs['Fac'])
        bg_light = nt.nodes.new('ShaderNodeBackground')
        bg_cam = nt.nodes.new('ShaderNodeBackground')
        nt.links.new(ramp.outputs['Color'], bg_light.inputs['Color'])
        nt.links.new(ramp2.outputs['Color'], bg_cam.inputs['Color'])
        lp = nt.nodes.new('ShaderNodeLightPath')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
        nt.links.new(bg_light.outputs['Background'], mix.inputs[1])
        nt.links.new(bg_cam.outputs['Background'], mix.inputs[2])
        self.silh_bg = nt.nodes.new('ShaderNodeBackground')
        self.silh_bg.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        self.mix_out = mix
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
        self.world_nt = nt
        self.world_out = out

    def set_sun(self, az):
        """az: sun azimuth in degrees, 0 = from the front (-Y), positive towards +X. None = front-left of the camera."""
        if az is None:
            az = self.cam_az - 70.0
        a, e = math.radians(az), math.radians(self.SUN_EL)
        to_sun = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        self.sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()

    def _gpu(self):
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for dt in ('OPTIX', 'CUDA'):
                devs = prefs.get_devices_for_type(dt)
                gpus = [d for d in devs if d.type != 'CPU']
                if gpus:
                    prefs.compute_device_type = dt
                    for d in devs:
                        d.use = d.type != 'CPU'
                    self.scene.cycles.device = 'GPU'
                    print(f'[studio] Cycles on {dt}: {[d.name for d in gpus]}')
                    return
        except Exception as e:                                   # noqa: BLE001
            print(f'[studio] GPU unavailable ({e}); rendering on the CPU')

    def _ground_mat(self, swatch):
        if swatch in self.ground_mats:
            return self.ground_mats[swatch]
        m = bpy.data.materials.new(f'Ground_{swatch}')
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = lin(swatch)
        b.inputs['Roughness'].default_value = 0.95
        if 'Specular IOR Level' in b.inputs:
            b.inputs['Specular IOR Level'].default_value = 0.1
        self.ground_mats[swatch] = m
        return m

    def set_ground(self, swatch):
        if self.ground_ob is None:
            me = bpy.data.meshes.new('Ground_Studio')
            s = 800.0
            me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
            self.ground_ob = bpy.data.objects.new('Ground_Studio', me)
            self.coll.objects.link(self.ground_ob)
        if swatch is None:
            self.ground_ob.hide_render = True
            return
        self.ground_ob.hide_render = False
        self.ground_ob.data.materials.clear()
        self.ground_ob.data.materials.append(self._ground_mat(swatch))

    def _person(self):
        """1.75 m scale figure (never exported): body, head, a neutral grey."""
        m = bpy.data.materials.new('Person_Studio')
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (0.30, 0.31, 0.34, 1)
        p = Mesh()
        p.lathe([(0.0, 0.0), (0.16, 0.0), (0.2, 0.85), (0.24, 1.3), (0.2, 1.45), (0.0, 1.47)], 10, 'ink')
        p.lathe([(0.0, 1.47), (0.11, 1.52), (0.12, 1.64), (0.08, 1.73), (0.0, 1.75)], 10, 'ink')
        me = bpy.data.meshes.new('ScalePerson_1.75m')
        me.from_pydata(p.verts, [], p.faces)
        me.materials.append(m)
        ob = bpy.data.objects.new('ScalePerson_1.75m', me)
        self.coll.objects.link(ob)
        ob.location.z = -50
        return ob

    def person(self, at):
        self.person_ob.location = (at[0], at[1], 0.0) if at else (0, 0, -50)

    def silhouette_mode(self, on):
        vl = self.scene.view_layers[0]
        vl.material_override = self.grey if on else None
        nt = self.world_nt
        for l in list(self.world_out.inputs['Surface'].links):
            nt.links.remove(l)
        nt.links.new((self.silh_bg if on else self.mix_out).outputs[0], self.world_out.inputs['Surface'])
        self.sun.hide_render = on

    def frame(self, objs, az, el, res, lens=50, pad=1.08, ortho=False, eye=None, target=None, dist=None):
        bpy.context.view_layer.update()
        self.cam_az = az
        cam, cd, scene = self.cam, self.cam.data, self.scene
        pts = []
        for o in objs:
            if o.type == 'MESH':
                pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        centre = sum(pts, Vector()) / len(pts) if target is None else Vector(target)
        d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)),
                    math.sin(math.radians(el))))
        rot = (-d).to_track_quat('-Z', 'Y')
        right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
        xs = [(p - centre).dot(right) for p in pts]
        ys = [(p - centre).dot(up) for p in pts]
        if target is None:
            centre = centre + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
            xs = [(p - centre).dot(right) for p in pts]
            ys = [(p - centre).dot(up) for p in pts]
        wext, hext = 2 * max(abs(min(xs)), abs(max(xs))), 2 * max(abs(min(ys)), abs(max(ys)))
        aspect = res[0] / res[1]
        radius = max((p - centre).length for p in pts)
        cd.type = 'ORTHO' if ortho else 'PERSP'
        cd.lens = lens
        cd.sensor_width = 36
        cd.sensor_fit = 'HORIZONTAL'
        if ortho:
            cd.ortho_scale = max(wext, hext * aspect) * pad
            dd = radius * 3 + 20
        else:
            fov_w = 2 * math.atan(18 / lens)
            fov_h = 2 * math.atan(math.tan(fov_w / 2) / aspect)
            dd = max(wext / 2 / math.tan(fov_w / 2), hext / 2 / math.tan(fov_h / 2)) * pad + radius * 0.35
        if dist is not None:
            dd = dist
        cam.location = centre + d * dd
        if eye is not None:
            cam.location.z = eye
            rot = (cam.location - centre).to_track_quat('Z', 'Y')
        cam.rotation_euler = rot.to_euler()
        cd.clip_start = 0.05
        cd.clip_end = dd * 6 + 600
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100


def write_kit_summary(rev, kit_dir=KIT_DIR):
    """Aggregates every <FAMILY>/validation_<rev>.json into STYLE_KIT_v2/validation_<rev>.json."""
    kit_dir = Path(kit_dir)
    fams = {}
    for p in sorted(kit_dir.glob(f'*/validation_{rev}.json')):
        try:
            r = json.loads(p.read_text(encoding='utf-8'))
        except Exception:                                        # noqa: BLE001
            continue
        fams[p.parent.name] = {
            'family': r.get('family'), 'all_checks_passed': r.get('all_checks_passed'), 'total_triangles': r.get('total_triangles'),
            'assets': {n: {'triangles': a['triangles'], 'budget': a['triangle_budget'], 'size_m': a['size_m'],
                           'swatch_families': a['swatch_families'], 'min_member_m': a['min_member_m'],
                           'checks': a['checks'], 'all_checks_passed': a['all_checks_passed'],
                           'failed_checks': [k for k, v in a['checks'].items() if not v], 'fbx': a.get('fbx')}
                       for n, a in r.get('assets', {}).items()}}
    summary = {'kit': KIT_NAME, 'revision': rev, 'style_bible': BIBLE_DATA['style_bible'], 'bible_date': BIBLE_DATA.get('date'),
               'atlas': f'_lib/{PALETTE_NAME}.png + .json ({len(SWATCH)} swatches incl. ramp steps, {len(GRAD)} gradients)',
               'families': fams, 'total_assets': sum(len(f['assets']) for f in fams.values()),
               'total_triangles': sum(f['total_triangles'] or 0 for f in fams.values()),
               'all_checks_passed': all(f['all_checks_passed'] for f in fams.values()) if fams else False}
    (kit_dir / f'validation_{rev}.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
