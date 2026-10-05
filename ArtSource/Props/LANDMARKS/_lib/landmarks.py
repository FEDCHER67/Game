"""Shared helpers for the LANDMARKS family builders (valley and old-town landmark props).

Thin layer over STREET_KIT/_lib/streetkit.py: same axes, pivots, FBX export, validation, previews and the same shared
palette material SK_Palette (one 128 x 64 texture + vertex colours). Additions:
  * Emissive parts (neon tubes, bulb dots, lit clock faces) are separate child meshes named <Asset>_Emissive so Unity can
    give them an emissive variant of the palette material; their faces still use palette cells.
  * Billboard poster faces use the second material LM_Poster with UV 0..1 over the whole poster (one poster texture
    per billboard instance, aspect 2:1), instead of the full STREET_KIT signage atlas.
  * Budget for every landmark: 200-1500 triangles for the whole asset.

Usage inside a family script:
    import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
    import landmarks as lm
    from landmarks import sk, Mesh, T, R
"""
import math, sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB_DIR.parents[1] / 'STREET_KIT' / '_lib'))
import streetkit as sk                                       # noqa: E402  (shared palette, Mesh, Family)
from streetkit import Mesh, T, R, S                          # noqa: E402,F401
import bpy                                                   # noqa: E402

BUDGET = (200, 1500)
TAU = math.tau
_save_palette = sk.save_textures


def _save_palette_if_missing(out_dir):
    """The shared STREET_KIT/_lib/SK_Palette.png is owned by STREET_KIT: write it only when it is not there yet."""
    p = Path(out_dir) / 'SK_Palette.png'
    return p if p.exists() else _save_palette(out_dir)


sk.save_textures = _save_palette_if_missing


class Family(sk.Family):
    def asset(self, name, parts, budget=BUDGET, **kw):
        return super().asset(name, parts, budget=budget, **kw)

    def finish(self, gap=1.0):
        if bpy.data.images.get('LM_Poster_Placeholder'):
            poster_placeholder_image().pack()
        super().finish(gap)

    def render(self):
        """Previews: lift assets that do not stand on the ground (bells) so they hang above the studio floor."""
        for a in self.assets:
            if not a['ground']:
                a['root'].location.z = -self.report[a['name']]['bounds_min'][2] + 0.4
        super().render()


# ---------------------------------------------------------------- primitives
def ball(m, r, col, at=(0, 0, 0), seg=8, rings=4, M=None):
    """Low-poly UV sphere centred on `at` (seg x rings)."""
    prof = [(r * math.sin(math.pi * i / rings), -r * math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    prof[0], prof[-1] = (0.0, -r), (0.0, r)
    return m.lathe(prof, seg, col, (M or T()) @ T(*at))


def bulb(m, r, col, at, axis='Y'):
    """Tiny 6-sided diamond bulb (12 triangles), pointing along -Y (or Z) from its base point `at`."""
    rot = R(90, 'X') if axis == 'Y' else T()
    return m.lathe([(0.0, 0.0), (r, r * 0.9), (0.0, r * 2.0)], 6, col, T(*at) @ rot)


def ring_xz(m, pts, r, col, seg=6, M=None):
    """Closed tube loop through points given as (x, z) in the XZ plane (neon outlines, letter O)."""
    sub = Mesh()
    sub.tube_path([(x, 0.0, z) for x, z in pts], r, seg, col, closed=True)
    m.merge(sub, M)


def path_xz(m, pts, r, col, seg=6, M=None):
    sub = Mesh()
    sub.tube_path([(x, 0.0, z) for x, z in pts], r, seg, col)
    m.merge(sub, M)


def circle_pts(rx, rz, n, cx=0.0, cz=0.0, a0=0.0):
    return [(cx + rx * math.cos(a0 + TAU * i / n), cz + rz * math.sin(a0 + TAU * i / n)) for i in range(n)]


# ---------------------------------------------------------------- Cyrillic block letters (strokes in a 1 x 1 cell)
# Each glyph: list of strokes ((x0, z0), (x1, z1)) in a unit cell, x 0..W, z 0..1; 'O' uses a ring instead.
GLYPHS = {
    'К': (0.80, [((0.06, 0.0), (0.06, 1.0)), ((0.10, 0.50), (0.74, 1.0)), ((0.24, 0.62), (0.74, 0.0))]),
    'А': (0.86, [((0.04, 0.0), (0.43, 1.0)), ((0.43, 1.0), (0.82, 0.0)), ((0.20, 0.36), (0.66, 0.36))]),
    'З': (0.76, [((0.06, 0.94), (0.62, 0.94)), ((0.62, 0.94), (0.70, 0.74)), ((0.70, 0.74), (0.60, 0.52)),
                 ((0.24, 0.50), (0.60, 0.52)), ((0.60, 0.52), (0.72, 0.28)), ((0.72, 0.28), (0.62, 0.06)),
                 ((0.62, 0.06), (0.06, 0.06))]),
    'И': (0.84, [((0.07, 0.0), (0.07, 1.0)), ((0.77, 0.0), (0.77, 1.0)), ((0.07, 0.04), (0.77, 0.96))]),
    'Н': (0.84, [((0.07, 0.0), (0.07, 1.0)), ((0.77, 0.0), (0.77, 1.0)), ((0.07, 0.50), (0.77, 0.50))]),
    'О': (0.84, None),
}


def word(m, text, height, col, y=0.0, z0=0.0, stroke_w=0.14, depth=0.10, gap=0.10, centre=True):
    """Block letters standing in the XZ plane at y, baseline z0; stroke width relative to height."""
    sw = stroke_w * height
    total = sum(GLYPHS[c][0] for c in text) * height + gap * height * (len(text) - 1)
    x = -total / 2 if centre else 0.0
    for c in text:
        w, strokes = GLYPHS[c]
        if strokes is None:
            rx, rz = (w * height - sw) / 2, (height - sw) / 2
            ring_xz(m, circle_pts(rx, rz, 10, x + w * height / 2, z0 + height / 2, math.pi / 10), sw / 2, col, seg=4,
                    M=T(0, y, 0))
        else:
            for j, (a, b) in enumerate(strokes):
                pa = (x + a[0] * height, z0 + min(max(a[1] * height, sw / 2), height - sw / 2))
                pb = (x + b[0] * height, z0 + min(max(b[1] * height, sw / 2), height - sw / 2))
                dx, dz = pb[0] - pa[0], pb[1] - pa[1]
                L = math.hypot(dx, dz)
                ex, ez = dx / L * sw / 2, dz / L * sw / 2          # extend by half a stroke so joints overlap
                yj = y - 0.004 * j                                   # stagger strokes: no coplanar overlapping faces
                m.beam((pa[0] - ex, yj, pa[1] - ez), (pb[0] + ex, yj, pb[1] + ez), sw, depth, col, up=(0, 1, 0))
        x += (w + gap) * height
    return total


# ---------------------------------------------------------------- materials
def poster_placeholder_image():
    img = bpy.data.images.get('LM_Poster_Placeholder')
    if img:
        return img
    W, H = 128, 64
    img = bpy.data.images.new('LM_Poster_Placeholder', W, H, alpha=False)
    px = [0.0] * (W * H * 4)
    for y in range(H):
        for x in range(W):
            edge = x < 3 or x >= W - 3 or y < 3 or y >= H - 3
            band = 22 <= y < 42 and 16 <= x < 112
            c = (0.1, 0.1, 0.12) if edge else ((0.95, 0.85, 0.3) if band else (0.85, 0.35, 0.45))
            o = (y * W + x) * 4
            px[o:o + 4] = [*c, 1.0]
    img.pixels = px
    return img


def poster_material():
    return sk._image_material('LM_Poster', poster_placeholder_image(), 0.7)


def use_poster(ob):
    """Swap the second material slot (SK_Signage set by streetkit for faces with explicit UVs) to LM_Poster."""
    ob.data.materials[1] = poster_material()


def poster_face_box(m, w, h, d, frame_col, M=None):
    """Board w x h (XZ) x d deep, centred; its -Y face carries UV 0..1 for the LM_Poster material."""
    fs = m.box(w, d, h, frame_col, M)
    m.fuv[list(fs)[2]] = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    return fs

