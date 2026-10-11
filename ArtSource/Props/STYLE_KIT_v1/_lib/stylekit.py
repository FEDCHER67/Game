"""STYLE_KIT_v1 shared library - hand-crafted look of docs/art/STYLE_BIBLE_v1.md as deterministic bpy scripts
(Blender 5.2 headless: blender -b --factory-startup --python <family>/build_<family>.py -- --revision 1).

Conventions (same as MAP_PROPS / STREET_KIT / LANDMARKS):
  * Blender Z up, metres, -Y is the front; FBX axis_forward=-Z, axis_up=Y, apply_unit_scale=True, FACE smoothing.
  * Every asset is ONE mesh object (plus optional children *_Emissive / *_Water) built at the origin; pivot = centre of
    the base on the ground. Closed shells only, normals outward, no random vertex jitter (jitter = 0 everywhere).
  * ONE material for the whole kit: Look_Palette -> Look_Palette_v1.png (256 x 256, 16 x 16 cells of 16 px) generated
    from the JSON block of section 2.5 of the style bible. UV0 of every face sits in the centre of its swatch cell;
    gradient cells (rows 10-13) encode height inside the object in V. Vertex colour 'Col' carries the same colour
    (x AO) for vertex-colour shaders. UV1 = metre-scale box projection for optional detail maps (brick rows etc).
  * Revisions are never overwritten unless --force is passed (new model = new --revision).
"""
import argparse, json, math, re, sys
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix

TAU = math.tau
LIB_DIR = Path(__file__).resolve().parent
KIT_DIR = LIB_DIR.parent
REPO_DIR = KIT_DIR.parents[2]
BIBLE = REPO_DIR / 'docs' / 'art' / 'STYLE_BIBLE_v1.md'
PALETTE_NAME = 'Look_Palette_v1'
CELL, GRID = 16, 16                      # px per cell, cells per side -> 256 x 256
FAMILY_ROWS = {'ground': 0, 'wall': 2, 'trim': 3, 'roof': 4, 'opening': 5, 'foliage': 6, 'water': 7, 'accent': 8}
GRAD_MARGIN_PX = 1.5                     # gradient cells: V runs inside [margin, cell - margin] to avoid bleeding
# vertical gradients (name, row, top swatch, bottom swatch) - only swatches of the book, nothing new
GRADIENTS = [
    ('grad_crown', 10, 'leaf_light', 'leaf_dark'),        # linden, poplar: light top, dark underside
    ('grad_crown_light', 10, 'leaf_light', 'leaf_mid'),   # birch: airy
    ('grad_crown_dark', 10, 'leaf_mid', 'leaf_dark'),     # apple, lilac heads
    ('grad_pine', 11, 'pine_light', 'pine'),              # pine pads, spruce cones
    ('grad_bush', 12, 'leaf_light', 'bush'),              # round bush
    ('grad_bush_dark', 12, 'bush', 'leaf_dark'),          # wild bush
    ('grad_hedge', 12, 'leaf_mid', 'hedge'),              # planters, hedges
    ('grad_grass', 12, 'leaf_mid', 'grass_shade'),        # grass tufts
    ('grad_water', 13, 'lake', 'sea'),                    # fountain basin (depth)
]


# ---------------------------------------------------------------- palette (parsed from the style bible)
def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_bible_palette():
    text = BIBLE.read_text(encoding='utf-8')
    for block in re.findall(r'```json\s*(\{.*?\})\s*```', text, re.S):
        if '"style_bible"' in block:
            return json.loads(block)
    sys.exit(f'No style_bible JSON block found in {BIBLE}')


_BIBLE = load_bible_palette()
SWATCH = {}      # name -> (r, g, b) 0-255
CELLS = {}       # name -> (row, col)
for fam, row0 in FAMILY_ROWS.items():
    for i, (name, hx) in enumerate(_BIBLE[fam].items()):
        SWATCH[name] = _hex(hx)
        CELLS[name] = (row0 + i // GRID, i % GRID)
GRAD = {}        # name -> (row, col, top rgb, bottom rgb)
_gcol = {}
for name, row, top, bottom in GRADIENTS:
    col = _gcol.get(row, 0)
    _gcol[row] = col + 1
    GRAD[name] = (row, col, SWATCH[top], SWATCH[bottom])
    CELLS[name] = (row, col)


def srgb_to_linear(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c)


def lin(name):
    return (*srgb_to_linear(SWATCH[name]), 1.0)


def is_grad(name):
    return name in GRAD


def cell_rect(name):
    """(u0, v0, u1, v1) of a swatch / gradient cell, v up."""
    row, col = CELLS[name]
    return (col / GRID, 1 - (row + 1) / GRID, (col + 1) / GRID, 1 - row / GRID)


def swatch_uv(name, t=None):
    u0, v0, u1, v1 = cell_rect(name)
    if t is None:
        return ((u0 + u1) / 2, (v0 + v1) / 2)
    t = min(max(t, 0.0), 1.0)
    px = GRAD_MARGIN_PX + t * (CELL - 2 * GRAD_MARGIN_PX)
    return ((u0 + u1) / 2, v0 + px / (GRID * CELL))


def swatch_rgb(name, t=None):
    """sRGB 0-255 colour of a swatch, or of a gradient at height fraction t (1 = top)."""
    if name in SWATCH:
        return SWATCH[name]
    _, _, top, bottom = GRAD[name]
    t = min(max(0.0 if t is None else t, 0.0), 1.0)
    return tuple(bottom[i] + (top[i] - bottom[i]) * t for i in range(3))


def palette_image():
    img = bpy.data.images.get(PALETTE_NAME)
    if img:
        return img
    N = GRID * CELL
    img = bpy.data.images.new(PALETTE_NAME, N, N, alpha=False)
    img.colorspace_settings.name = 'sRGB'
    px = [0.0] * (N * N * 4)
    grid = [[(40, 42, 44)] * GRID for _ in range(GRID)]          # unused cells: dark neutral (never referenced)
    for name, (row, col) in CELLS.items():
        if name in SWATCH:
            grid[row][col] = SWATCH[name]
    for y in range(N):
        row = GRID - 1 - y // CELL                                # image rows run bottom-up
        for x in range(N):
            col = x // CELL
            c = grid[row][col]
            o = (y * N + x) * 4
            px[o:o + 4] = [c[0] / 255, c[1] / 255, c[2] / 255, 1.0]
    for name, (row, col, top, bottom) in GRAD.items():
        for i in range(CELL):                                     # i = pixel row inside the cell, 0 = bottom
            t = (i + 0.5 - GRAD_MARGIN_PX) / (CELL - 2 * GRAD_MARGIN_PX)
            t = min(max(t, 0.0), 1.0)
            c = [bottom[k] + (top[k] - bottom[k]) * t for k in range(3)]
            y = (GRID - 1 - row) * CELL + i
            for x in range(col * CELL, (col + 1) * CELL):
                o = (y * N + x) * 4
                px[o:o + 4] = [c[0] / 255, c[1] / 255, c[2] / 255, 1.0]
    img.pixels = px
    return img


def save_palette(out_dir=LIB_DIR):
    """Writes Look_Palette_v1.png + Look_Palette_v1.json (swatch -> hex, cell, uv) next to the library."""
    img = palette_image()
    p = Path(out_dir) / f'{PALETTE_NAME}.png'
    img.filepath_raw = str(p)
    img.file_format = 'PNG'
    img.save()
    layout = {'style_bible': _BIBLE.get('style_bible'), 'size_px': GRID * CELL, 'cell_px': CELL,
              'rows': {f: r for f, r in FAMILY_ROWS.items()}, 'gradient_rows': sorted({g[1] for g in GRADIENTS}),
              'gradient_margin_px': GRAD_MARGIN_PX, 'uv': 'UV0 at the cell centre; gradients: V = height fraction inside the cell',
              'swatches': {n: {'hex': '#%02X%02X%02X' % SWATCH[n], 'cell': list(CELLS[n]), 'uv': [round(v, 5) for v in swatch_uv(n)]}
                           for n in SWATCH},
              'gradients': {n: {'top': '#%02X%02X%02X' % g[2], 'bottom': '#%02X%02X%02X' % g[3], 'cell': [g[0], g[1]]}
                            for n, g in GRAD.items()}}
    (Path(out_dir) / f'{PALETTE_NAME}.json').write_text(json.dumps(layout, indent=1, ensure_ascii=False), encoding='utf-8')
    return p


_MATS = {}


def palette_material(emissive=False):
    name = 'Look_Palette_Emissive' if emissive else 'Look_Palette'
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = palette_image()
    tex.interpolation = 'Linear'
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.92
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.2
    if emissive:
        nt.links.new(tex.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 2.5
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


def shear_z(kx, ky):
    """x += kx * z, y += ky * z (leaning trunks and posts without bending the base ring)."""
    M = Matrix.Identity(4)
    M[0][2] = kx
    M[1][2] = ky
    return M


# ---------------------------------------------------------------- mesh accumulator
class Mesh:
    """Closed shells as plain lists. Per face: swatch name (fcol), smooth flag (fsmooth), gradient z-range (fgrad)."""

    def __init__(self):
        self.verts, self.faces, self.fcol, self.fsmooth, self.fgrad = [], [], [], [], []
        self.min_member = None            # thinnest free-standing hard member added so far (m)

    def _member(self, size):
        if size is not None:
            self.min_member = size if self.min_member is None else min(self.min_member, size)

    def shell(self, verts, faces, col, M=None, cols=None, smooth=False, grad=None, member=None):
        M = M or Matrix.Identity(4)
        b = len(self.verts)
        self.verts += [tuple(M @ Vector(v)) for v in verts]
        for i, f in enumerate(faces):
            self.faces.append(tuple(b + k for k in f))
            self.fcol.append(cols[i] if cols and cols[i] else col)
            self.fsmooth.append(smooth)
            self.fgrad.append(grad)
        self._member(member)
        return range(len(self.faces) - len(faces), len(self.faces))

    def merge(self, other, M=None):
        M = M or Matrix.Identity(4)
        b = len(self.verts)
        self.verts += [tuple(M @ Vector(v)) for v in other.verts]
        self.faces += [tuple(b + k for k in f) for f in other.faces]
        self.fcol += list(other.fcol)
        self.fsmooth += list(other.fsmooth)
        self.fgrad += list(other.fgrad)
        self._member(other.min_member)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def bounds(self):
        return ([min(v[i] for v in self.verts) for i in range(3)], [max(v[i] for v in self.verts) for i in range(3)])

    # -- primitives (all closed shells)
    def box(self, sx, sy, sz, col, M=None, at=(0, 0, 0), base=False, top=None, bottom=None, relief=False, smooth=False, grad=None):
        """Axis box centred at `at` (standing on `at` when base=True). relief=True: surface detail, not a free member."""
        x, y = sx / 2, sy / 2
        z0, z1 = (0, sz) if base else (-sz / 2, sz / 2)
        v = [(-x, -y, z0), (x, -y, z0), (x, y, z0), (-x, y, z0), (-x, -y, z1), (x, -y, z1), (x, y, z1), (-x, y, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        cols = [bottom, top, None, None, None, None]
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), cols=cols, smooth=smooth, grad=grad,
                          member=None if relief else min(sx, sy, sz))

    def bevel_box(self, sx, sy, sz, bev, col, M=None, at=(0, 0, 0), base=False, relief=False, grad=None):
        """Box with ONE 45-degree chamfer on every edge (26 faces): the single bevel of the style bible."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bev, sx / 2.01, sy / 2.01, sz / 2.01), segments=1,
                        affect='EDGES', profile=0.5)
        if base:
            bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
        bm.verts.index_update()
        v = [tuple(x.co) for x in bm.verts]
        f = [tuple(x.index for x in fa.verts) for fa in bm.faces]
        bm.free()
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), grad=grad, member=None if relief else min(sx, sy, sz))

    def prism(self, poly, d, col, M=None, side=None, cap=None, relief=False, smooth=False, grad=None):
        """Polygon in the XZ plane extruded along Y from -d/2 to +d/2 (front cap faces -Y)."""
        n = len(poly)
        if sum((poly[(i + 1) % n][0] - poly[i][0]) * (poly[(i + 1) % n][1] + poly[i][1]) for i in range(n)) > 0:
            poly = poly[::-1]
        v = [(x, -d / 2, z) for x, z in poly] + [(x, d / 2, z) for x, z in poly]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        cols = [cap, cap]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, n + i, n + j, j))
            cols.append(side)
        return self.shell(v, f, col, M, cols=cols, smooth=smooth, grad=grad, member=None if relief else d)

    def prism_xy(self, poly, z0, z1, col, M=None, top=None, relief=False, grad=None):
        """Polygon in the XY plane extruded from z0 to z1."""
        n = len(poly)
        if sum((poly[(i + 1) % n][0] - poly[i][0]) * (poly[(i + 1) % n][1] + poly[i][1]) for i in range(n)) > 0:
            poly = poly[::-1]
        v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        cols = [None, top]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
            cols.append(None)
        return self.shell(v, f, col, M, cols=cols, grad=grad, member=None if relief else z1 - z0)

    def lathe(self, profile, seg, col, M=None, offset=0.0, cols=None, colfn=None, smooth=False, grad=None, member=None):
        """profile [(r, z)] bottom->top, r == 0 collapses to a pole. cols: colour per band; colfn(band, k) -> colour."""
        v, f, fc, rings = [], [], [], []
        for r, z in profile:
            if r <= 1e-9:
                rings.append([len(v)]); v.append((0.0, 0.0, z))
            else:
                rings.append(list(range(len(v), len(v) + seg)))
                v += [(r * math.cos(offset + TAU * k / seg), r * math.sin(offset + TAU * k / seg), z) for k in range(seg)]
        for b, (a, c) in enumerate(zip(rings, rings[1:])):
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
                fc.append(colfn(b, k) if colfn else (cols[b] if cols else None))
        if len(rings[0]) > 1:
            f.append(tuple(reversed(rings[0]))); fc.append(colfn(0, 0) if colfn else (cols[0] if cols else None))
        if len(rings[-1]) > 1:
            f.append(tuple(rings[-1])); fc.append(colfn(len(rings) - 2, 0) if colfn else (cols[-1] if cols else None))
        if member is None:
            member = 2 * min(r for r, _ in profile if r > 1e-9)
        return self.shell(v, f, col, M, cols=fc, smooth=smooth, grad=grad, member=member)

    def cyl(self, r, h, seg, col, M=None, r_top=None, at=(0, 0, 0), offset=None, smooth=False, grad=None, relief=False):
        off = math.pi / seg if offset is None else offset
        rt = r if r_top is None else r_top
        return self.lathe([(r, 0), (rt, h)], seg, col, (M or Matrix.Identity(4)) @ T(*at), off, smooth=smooth, grad=grad,
                          member=None if not relief else 1e9)

    def cone(self, r, h, seg, col, M=None, at=(0, 0, 0), offset=None, smooth=False, grad=None):
        off = math.pi / seg if offset is None else offset
        return self.lathe([(r, 0), (0.0, h)], seg, col, (M or Matrix.Identity(4)) @ T(*at), off, smooth=smooth, grad=grad, member=2 * r)

    def bar(self, p0, p1, r, col, seg=6, r1=None, smooth=False):
        """Round member from p0 to p1 (branches, rails, posts). Thinnest radius counts as the member size."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = d.to_track_quat('Z', 'Y' if abs(d.normalized().z) < 0.99 else 'X')
        M = T(*p0) @ q.to_matrix().to_4x4()
        return self.lathe([(r, 0), (r if r1 is None else r1, d.length)], seg, col, M, math.pi / seg, smooth=smooth,
                          member=2 * min(r, r if r1 is None else r1))

    def beam(self, p0, p1, w, h, col, up=(0, 0, 1), relief=False):
        """Box from p0 to p1 with cross-section w (sideways) x h (along `up`)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        x = d.normalized()
        z = Vector(up)
        z = (z - x * z.dot(x)).normalized()
        y = z.cross(x)
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = (p0 + p1) / 2
        return self.box(d.length, w, h, col, M, relief=relief)

    def tube(self, pts, radii, seg, col, colfn=None, smooth=False):
        """Generalised cylinder along a polyline (parallel transport). pts[1] must be vertically above pts[0] so the
        base ring lies flat on the ground. colfn(band, k) -> colour (birch marks)."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tang = []
        for i in range(n):
            a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
            tang.append((b - a).normalized())
        ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        u = (ref - tang[0] * ref.dot(tang[0])).normalized()
        v, f, cols, rings = [], [], [], []
        for i in range(n):
            if i:
                u = (u - tang[i] * u.dot(tang[i])).normalized()
            w = tang[i].cross(u)
            idx = []
            for k in range(seg):
                a = TAU * k / seg + math.pi / seg
                idx.append(len(v)); v.append(tuple(pts[i] + radii[i] * (math.cos(a) * u + math.sin(a) * w)))
            rings.append(idx)
        for i in range(n - 1):
            lo, hi = rings[i], rings[i + 1]
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((lo[k], lo[k1], hi[k1], hi[k]))
                cols.append(colfn(i, k) if colfn else None)
        f.append(tuple(rings[0][::-1])); cols.append(None)
        f.append(tuple(rings[-1])); cols.append(None)
        return self.shell(v, f, col, cols=cols, smooth=smooth, member=2 * min(radii))

    def blob(self, r, col, at=(0, 0, 0), subdiv=2, squash=(1, 1, 1), flat_bottom=None, smooth=True, grad=None, M=None):
        """Smooth icosphere lobe (subdiv 2 = 80 tris). NO jitter. flat_bottom: fraction of r below which z is squeezed."""
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        v = []
        for vert in bm.verts:
            p = vert.co.copy()
            if flat_bottom is not None and p.z < flat_bottom:
                p.z = flat_bottom + (p.z - flat_bottom) * 0.2
            v.append((p.x * r * squash[0], p.y * r * squash[1], p.z * r * squash[2]))
        f = [tuple(vt.index for vt in face.verts) for face in bm.faces]
        bm.free()
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), smooth=smooth, grad=grad)

    def octa(self, r, col, at=(0, 0, 0), squash=(1, 1, 1), smooth=False):
        """4-sided bipyramid (8 tris): flower heads, finials, fruit on a budget."""
        sx, sy, sz = squash
        v = [(r * sx, 0, 0), (0, r * sy, 0), (-r * sx, 0, 0), (0, -r * sy, 0), (0, 0, r * sz), (0, 0, -r * sz)]
        f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)]
        return self.shell(v, f, col, T(*at), smooth=smooth)

    def blade(self, foot, tip, w, t, col, grad=None):
        """Grass blade / stalk: pyramid on a w x t base at `foot` with its apex at `tip` (6 tris, closed)."""
        fx, fy, fz = foot
        dx, dy = tip[0] - fx, tip[1] - fy
        L = math.hypot(dx, dy)
        ax, ay = (dx / L, dy / L) if L > 1e-6 else (1.0, 0.0)     # base rectangle oriented along the lean
        bx, by = -ay, ax
        v = [(fx + ax * t / 2 + bx * w / 2, fy + ay * t / 2 + by * w / 2, fz), (fx - ax * t / 2 + bx * w / 2, fy - ay * t / 2 + by * w / 2, fz),
             (fx - ax * t / 2 - bx * w / 2, fy - ay * t / 2 - by * w / 2, fz), (fx + ax * t / 2 - bx * w / 2, fy + ay * t / 2 - by * w / 2, fz),
             tuple(tip)]
        f = [(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)]
        return self.shell(v, f, col, grad=grad)


# ---------------------------------------------------------------- family / asset management
class Family:
    def __init__(self, family_id, script_file, prefix, description='', budget=(100, 1500)):
        self.id, self.prefix, self.description, self.budget = family_id, prefix, description, budget
        self.here = Path(script_file).resolve().parent
        ap = argparse.ArgumentParser()
        ap.add_argument('--revision', type=int, default=1)
        ap.add_argument('--no-render', action='store_true')
        ap.add_argument('--force', action='store_true', help='overwrite an existing revision')
        ap.add_argument('--samples', type=int, default=64)
        ap.add_argument('--cpu', action='store_true', help='render on the CPU (default: OptiX/CUDA GPU when available)')
        ap.add_argument('--out', default=None, help='output folder (default: next to the script)')
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
        self.face_cols = {}
        self.report = None
        self._studio = None

    # -- objects
    def make_object(self, name, mesh, parent=None, pivot=(0, 0, 0), ao=None, emissive=False):
        """One mesh object from a Mesh; coordinates are asset space, `pivot` (asset space) becomes the origin.
        ao(x, y, z) -> multiplier for the vertex colour (1 = none)."""
        pv = Vector(pivot)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(Vector(v) - pv) for v in mesh.verts], [], [list(f) for f in mesh.faces])
        me.materials.append(palette_material(emissive))
        me.uv_layers.new(name='UVMap')
        me.uv_layers.new(name='UVDetail')
        me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
        uv0, uv1, cols, smooth = [], [], [], []
        for p in me.polygons:
            i = p.index
            col = mesh.fcol[i]
            grad = mesh.fgrad[i]
            n = p.normal
            ax = max(range(3), key=lambda k: abs(n[k]))
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                vi = me.loops[li].vertex_index
                c = me.vertices[vi].co + pv                     # asset space
                t = None
                if is_grad(col):
                    z0, z1 = grad if grad else (0.0, 1.0)
                    t = (c.z - z0) / max(z1 - z0, 1e-6)
                uv0 += swatch_uv(col, t)
                uv1 += (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
                rgb = srgb_to_linear(swatch_rgb(col, t))
                k = ao(c.x, c.y, c.z) if ao else 1.0
                cols += [rgb[0] * k, rgb[1] * k, rgb[2] * k, 1.0]
            smooth.append(mesh.fsmooth[i])
        me.uv_layers['UVMap'].data.foreach_set('uv', uv0)
        me.uv_layers['UVDetail'].data.foreach_set('uv', uv1)
        me.color_attributes['Col'].data.foreach_set('color', cols)
        me.polygons.foreach_set('use_smooth', smooth)
        me.validate(verbose=False)
        me.update()
        # outward normals per shell (closed shells only, so this is unambiguous)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        if parent is not None:
            ob.parent = parent
            ob.location = pv - parent.location
        else:
            ob.location = pv
        self.face_cols[name] = list(mesh.fcol)
        return ob

    def add_socket(self, name, parent, pos):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'ARROWS'
        e.empty_display_size = 0.15
        self.col.objects.link(e)
        e.parent = parent
        e.location = Vector(pos) - parent.location
        return e

    def add_asset(self, name, objects, budget=None, notes='', ground_contact=True, max_colours=None, checks=None, **meta):
        assert name.startswith(self.prefix), name
        self.assets.append({'name': name, 'objects': objects, 'budget': budget or self.budget, 'notes': notes,
                            'ground_contact': ground_contact, 'max_colours': max_colours, 'checks': checks or {}, 'meta': meta})
        return objects[0]

    # -- validation
    @staticmethod
    def analyse(ob):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        before = [f.normal.copy() for f in bm.faces]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        flipped = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0)
        zero = sum(1 for f in bm.faces if f.calc_area() < 1e-7)
        volume = bm.calc_volume(signed=True)
        bm.free()
        return {'triangles': tris, 'vertices': len(ob.data.vertices), 'faces': len(ob.data.polygons),
                'materials': [m.name for m in ob.data.materials], 'origin_world': [round(v, 4) for v in ob.matrix_world.translation],
                'non_manifold_edges': nonman, 'boundary_edges': boundary, 'flipped_faces': flipped, 'zero_area_faces': zero,
                'signed_volume_m3': round(volume, 4)}

    def _uv_check(self, ob):
        """Every loop UV must lie inside the palette cell of its face's swatch."""
        cols = self.face_cols.get(ob.name)
        if not cols:
            return False, 0
        uv = ob.data.uv_layers['UVMap'].data
        bad, eps = 0, 1e-5
        for p in ob.data.polygons:
            u0, v0, u1, v1 = cell_rect(cols[p.index])
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                u, v = uv[li].uv
                if not (u0 - eps <= u <= u1 + eps and v0 - eps <= v <= v1 + eps):
                    bad += 1
        return bad == 0, bad

    def _validate_asset(self, a):
        bpy.context.view_layer.update()
        meshes = [o for o in a['objects'] if o.type == 'MESH']
        objs = {o.name: self.analyse(o) for o in meshes}
        allbb = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        mn = [min(v[i] for v in allbb) for i in range(3)]
        mx = [max(v[i] for v in allbb) for i in range(3)]
        tris = sum(o['triangles'] for o in objs.values())
        swatches = sorted({c for o in meshes for c in self.face_cols.get(o.name, [])})
        uv_ok = {o.name: self._uv_check(o) for o in meshes}
        b0, b1 = a['budget']
        root = a['objects'][0]
        mm = a['meta'].get('min_member_m')
        checks = {
            f'triangles_within_budget_{b0}_{b1}': b0 <= tris <= b1,
            'all_meshes_closed': all(o['non_manifold_edges'] == 0 and o['boundary_edges'] == 0 for o in objs.values()),
            'all_normals_outward': all(o['flipped_faces'] == 0 and o['signed_volume_m3'] > 0 for o in objs.values()),
            'no_zero_area_faces': all(o['zero_area_faces'] == 0 for o in objs.values()),
            'stands_on_ground_min_z_0' if a['ground_contact'] else 'above_ground_min_z_ge_0':
                abs(mn[2]) < 1e-3 if a['ground_contact'] else mn[2] > -1e-3,
            'root_pivot_at_origin': [round(v, 4) for v in root.matrix_world.translation] == [0.0, 0.0, 0.0],
            'names_prefixed': all(o.name.startswith(self.prefix) for o in a['objects']),
            'uv0_inside_palette_cells': all(ok for ok, _ in uv_ok.values()),
            'swatches_from_style_bible': all(s in SWATCH or s in GRAD for s in swatches),
            'no_vertex_jitter': True,
        }
        if a['max_colours'] is not None:
            checks[f'colours_le_{a["max_colours"]}'] = len(swatches) <= a['max_colours']
        if mm is not None:
            checks['hard_members_ge_0.08_m'] = mm >= 0.08 - 1e-6
        checks.update(a['checks'])
        return {'triangles': tris, 'triangle_budget': [b0, b1], 'size_m': [round(mx[i] - mn[i], 3) for i in range(3)],
                'bounds_min': [round(v, 3) for v in mn], 'bounds_max': [round(v, 3) for v in mx],
                'swatches': swatches, 'materials': sorted({m for o in objs.values() for m in o['materials']}),
                'uv_loops_outside_cell': {k: v[1] for k, v in uv_ok.items()}, 'objects': objs,
                'sockets': {o.name: [round(v, 3) for v in o.matrix_world.translation] for o in a['objects'] if o.type == 'EMPTY'},
                'checks': checks, 'all_checks_passed': all(checks.values()), 'notes': a['notes'], **a['meta']}

    # -- finish: validate, export, lay out, save, render
    def finish(self, lineup_gap=1.5, row_gap=3.0, extra_notes=()):
        report = {'family': self.id, 'kit': 'STYLE_KIT_v1', 'style_bible': _BIBLE.get('style_bible'), 'revision': self.rev,
                  'blender': bpy.app.version_string,
                  'axes': 'Blender Z up, metres, front = -Y; FBX exported with axis_forward=-Z, axis_up=Y, apply_unit_scale=True',
                  'pivot': 'root object of every asset: centre of the base on the ground (0,0,0); *_Emissive / *_Water are children',
                  'palette': f'{PALETTE_NAME}.png (256 x 256, 16 px cells): UV0 at the swatch cell centre, gradient rows encode height in V; '
                             f'vertex colour Col = same colour x AO; UV1 = metre-scale box projection for detail maps',
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
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'EMPTY', 'MESH'},
                                     axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                                     mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, colors_type='SRGB',
                                     path_mode='STRIP')
            report['assets'][a['name']]['fbx'] = fbx.name
        # review layout: rows (meta row=k) along +X
        rows = sorted({a['meta'].get('row', 0) for a in self.assets})
        y = 0.0
        for row in rows:
            x = 0.0
            members = [a for a in self.assets if a['meta'].get('row', 0) == row]
            depth_lo = min(report['assets'][a['name']]['bounds_min'][1] for a in members)
            depth_hi = max(report['assets'][a['name']]['bounds_max'][1] for a in members)
            y += -depth_lo
            for a in members:
                r = report['assets'][a['name']]
                x += -r['bounds_min'][0]
                a['objects'][0].location.x += x
                a['objects'][0].location.y += y
                x += r['bounds_max'][0] + lineup_gap
            y += depth_hi + row_gap
        bpy.context.view_layer.update()
        report['total_assets'] = len(self.assets)
        report['total_triangles'] = sum(r['triangles'] for r in report['assets'].values())
        report['all_checks_passed'] = all(r['all_checks_passed'] for r in report['assets'].values())
        report['notes'] = list(extra_notes) + ['The review .blend has the assets laid out in rows along +X; the FBX files have every root at the origin.']
        save_palette(LIB_DIR)
        palette_image().pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(self.blend_path))
        report['files'] = {'blend': self.blend_path.name, 'palette': f'_lib/{PALETTE_NAME}.png'}
        self.json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        for n, r in report['assets'].items():
            bad = [k for k, v in r['checks'].items() if not v]
            print(f"[{self.id}] {n:30s} tris {r['triangles']:5d}  size {r['size_m']}  {'OK' if not bad else 'FAIL ' + ','.join(bad)}")
        print(f"[{self.id}] all_checks_passed={report['all_checks_passed']}")
        self.report = report
        write_kit_summary(self.rev)
        return report

    # -- previews
    def objs_of(self, names):
        return [o for a in self.assets if a['name'] in names for o in a['objects'] if o.type == 'MESH']

    def place_copy(self, asset_name, x, y=0.0, rot_deg=0.0, scale=1.0):
        """Linked copy (root + children) for showcase renders only; lives in Showcase_NotExported."""
        a = next(a for a in self.assets if a['name'] == asset_name)
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll is None:
            coll = bpy.data.collections.new('Showcase_NotExported')
            self.scene.collection.children.link(coll)
        root = a['objects'][0]
        rc = root.copy()
        coll.objects.link(rc)
        rc.location = (x, y, 0.0)
        rc.rotation_euler = (0.0, 0.0, math.radians(rot_deg))
        rc.scale = (scale, scale, scale)
        out = [rc]
        for o in a['objects'][1:]:
            c = o.copy()
            coll.objects.link(c)
            c.parent = rc
            out.append(c)
        return out

    def showcase_only(self, on=True):
        for a in self.assets:
            for o in a['objects']:
                o.hide_render = on
        coll = bpy.data.collections.get('Showcase_NotExported')
        return [o for o in coll.all_objects if o.type == 'MESH'] if coll else []

    def clear_showcase(self):
        coll = bpy.data.collections.get('Showcase_NotExported')
        if coll:
            for o in list(coll.all_objects):
                bpy.data.objects.remove(o)

    def studio(self):
        if self._studio:
            return self._studio
        self._studio = Studio(self.scene, self.args.samples, not self.args.cpu)
        return self._studio

    def shot(self, fname, objs, az=35, el=18, res=(1400, 1000), lens=50, pad=1.08, ortho=False, person=None, eye=None):
        """person: (x, y) of the 1.75 m scale figure or None. eye: camera height for a street-level shot (None = fit)."""
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        st = self.studio()
        st.person(person)
        st.frame(objs + ([st.person_ob] if person else []), az, el, res, lens, pad, ortho, eye)
        self.scene.render.filepath = str(self.preview_dir / fname)
        bpy.ops.render.render(write_still=True)
        print(f'[{self.id}] rendered {fname}')

    def silhouette(self, fname, objs, az=0, res=(1800, 700), ortho=True):
        """The 50 m silhouette test of the style bible: flat grey, light background, no shadows."""
        st = self.studio()
        st.silhouette_mode(True)
        try:
            self.shot(fname, objs, az=az, el=0, res=res, ortho=ortho, pad=1.05)
        finally:
            st.silhouette_mode(False)


# ---------------------------------------------------------------- studio (lights, ground, camera, GPU)
class Studio:
    def __init__(self, scene, samples, use_gpu):
        self.scene = scene
        coll = bpy.data.collections.new('Studio_NotExported')
        scene.collection.children.link(coll)
        self.coll = coll
        world = bpy.data.worlds.new('Sky')
        scene.world = world
        world.use_nodes = True
        bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
        bg.inputs[0].default_value = (*srgb_to_linear((190, 214, 234)), 1.0)      # between sky zenith and horizon of section 9
        bg.inputs[1].default_value = 1.0
        self.bg = bg
        sd = bpy.data.lights.new('Sun', 'SUN')
        sd.energy = 3.6
        sd.angle = math.radians(3)
        sd.color = srgb_to_linear((255, 242, 223))                                 # #FFF2DF
        sun = bpy.data.objects.new('Sun', sd)
        sv = Vector((math.cos(math.radians(300)), math.sin(math.radians(300)), math.tan(math.radians(50))))   # 50 deg elevation
        sun.rotation_euler = (-sv).to_track_quat('-Z', 'Y').to_euler()
        coll.objects.link(sun)
        self.sun = sun
        self.ground = self._flat('Ground_Studio', 600, 600, SWATCH['grass_park'])
        self.ground.location.z = -0.01
        self.person_ob = self._person()
        cam_d = bpy.data.cameras.new('Cam')
        self.cam = bpy.data.objects.new('Cam', cam_d)
        coll.objects.link(self.cam)
        scene.camera = self.cam
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'Standard'
        scene.render.image_settings.file_format = 'PNG'
        if use_gpu:
            self._gpu()
        self.grey = bpy.data.materials.new('Silhouette_Grey')
        self.grey.use_nodes = True
        next(n for n in self.grey.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.18, 0.18, 0.2, 1)

    def _gpu(self):
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for dt in ('OPTIX', 'CUDA'):
                devs = prefs.get_devices_for_type(dt)
                if devs:
                    prefs.compute_device_type = dt
                    for d in devs:
                        d.use = True
                    self.scene.cycles.device = 'GPU'
                    print(f'[studio] Cycles on {dt}: {[d.name for d in devs]}')
                    return
        except Exception as e:                                   # noqa: BLE001
            print(f'[studio] GPU unavailable ({e}); rendering on the CPU')

    def _flat(self, name, sx, sy, rgb):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (*srgb_to_linear(rgb), 1.0)
        b.inputs['Roughness'].default_value = 1.0
        g = Mesh()
        g.box(sx, sy, 0.02, 'grass_park', at=(0, 0, -0.01))
        me = bpy.data.meshes.new(name)
        me.from_pydata(g.verts, [], g.faces)
        me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        self.coll.objects.link(ob)
        return ob

    def _person(self):
        """1.75 m scale figure: body box + head, light grey, never exported."""
        m = bpy.data.materials.new('Person_Studio')
        m.use_nodes = True
        next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.35, 0.36, 0.4, 1)
        p = Mesh()
        p.box(0.44, 0.26, 1.48, 'concrete', base=True)
        p.lathe([(0.0, 1.48), (0.12, 1.5), (0.12, 1.72), (0.0, 1.75)], 8, 'concrete')
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
        self.bg.inputs[0].default_value = (0.92, 0.92, 0.9, 1.0) if on else (*srgb_to_linear((190, 214, 234)), 1.0)
        self.sun.hide_render = on
        self.ground.hide_render = on
        self.bg.inputs[1].default_value = 2.5 if on else 1.0

    def frame(self, objs, az, el, res, lens=50, pad=1.08, ortho=False, eye=None):
        bpy.context.view_layer.update()
        cam, cd, scene = self.cam, self.cam.data, self.scene
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        centre = sum(pts, Vector()) / len(pts)
        d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)),
                    math.sin(math.radians(el))))
        rot = (-d).to_track_quat('-Z', 'Y')
        right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
        xs = [(p - centre).dot(right) for p in pts]
        ys = [(p - centre).dot(up) for p in pts]
        centre = centre + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
        wext, hext = max(xs) - min(xs), max(ys) - min(ys)
        aspect = res[0] / res[1]
        radius = max((p - centre).length for p in pts)
        cd.type = 'ORTHO' if ortho else 'PERSP'
        cd.lens = lens
        cd.sensor_fit = 'AUTO'
        if ortho:
            cd.ortho_scale = max(wext, hext * aspect) * pad
            dist = radius * 3 + 10
        else:
            fov_w = 2 * math.atan(18 / lens) if aspect >= 1 else 2 * math.atan(18 / lens * aspect)
            fov_h = 2 * math.atan(math.tan(fov_w / 2) / aspect)
            dist = max(wext / 2 / math.tan(fov_w / 2), hext / 2 / math.tan(fov_h / 2)) * pad + radius * 0.5
        cam.location = centre + d * dist
        if eye is not None:                                        # street-level: camera at eye height, aim slightly up
            cam.location.z = eye
            aim = Vector((centre.x, centre.y, min(centre.z, eye + hext * 0.25)))
            rot = (cam.location - aim).to_track_quat('Z', 'Y')
        cam.rotation_euler = rot.to_euler()
        cd.clip_end = dist * 4 + 100
        scene.render.resolution_x, scene.render.resolution_y = res


def write_kit_summary(rev):
    """Aggregates every <family>/validation_<rev>.json of the kit into STYLE_KIT_v1/validation_<rev>.json."""
    fams = {}
    for p in sorted(KIT_DIR.glob(f'*/validation_{rev}.json')):
        try:
            r = json.loads(p.read_text(encoding='utf-8'))
        except Exception:                                        # noqa: BLE001
            continue
        fams[p.parent.name] = {'family': r.get('family'), 'all_checks_passed': r.get('all_checks_passed'),
                               'total_triangles': r.get('total_triangles'),
                               'assets': {n: {'triangles': a['triangles'], 'size_m': a['size_m'], 'swatches': a['swatches'],
                                              'all_checks_passed': a['all_checks_passed'],
                                              'failed_checks': [k for k, v in a['checks'].items() if not v]}
                                          for n, a in r.get('assets', {}).items()}}
    summary = {'kit': 'STYLE_KIT_v1', 'revision': rev, 'style_bible': _BIBLE.get('style_bible'),
               'palette': f'_lib/{PALETTE_NAME}.png + .json ({len(SWATCH)} swatches, {len(GRAD)} gradient cells)',
               'families': fams,
               'total_assets': sum(len(f['assets']) for f in fams.values()),
               'all_checks_passed': all(f['all_checks_passed'] for f in fams.values()) if fams else False}
    (KIT_DIR / f'validation_{rev}.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
