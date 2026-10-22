"""MAP_W86_v01 static props (agent M2) - shared Blender library.

Original procedural low-poly models (no third-party geometry). Blender 5.2, run headless.
Conventions
  * 1 unit = 1 m, Blender Z up. Every asset is modelled in the frame of the W85 placeholder box it replaces:
    Blender X = data size[0], Blender Y = data size[1], Z = height. Pivot = centre of the base on the ground.
  * FBX: axis_forward=-Z, axis_up=Y, apply_unit_scale, FBX_SCALE_UNITS, bake_space_transform (as GRANDPA_YARD_v01 /
    FACADE_KIT_v01, both imported in Unity). Blender -Y -> Unity +Z, Blender +X -> Unity -X, Blender +Z -> Unity +Y.
  * One shared material MW86_StaticPalette_v01 for every asset: flat colour swatches in a 256 px atlas
    (albedo + metallic/smoothness + emission maps), UVs collapsed to swatch centres.
  * Soft volume: per-part chamfers (2 segments) + face-area weighted normals; sharp edges only above 50 degrees.
"""
import math, json, random
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix, Euler

ATLAS_PX, CELL_PX = 256, 16
PER_ROW = ATLAS_PX // CELL_PX
MAT_NAME = 'MW86_StaticPalette_v01'

# name: (sRGB 0-255, metallic, smoothness, emission 0..1)
PALETTE = {
    # neutrals / metals
    'white_paint': ((236, 232, 222), 0, .25, 0), 'offwhite': ((214, 208, 194), 0, .2, 0),
    'light_grey': ((184, 182, 176), 0, .2, 0), 'concrete': ((166, 162, 153), 0, .1, 0),
    'concrete_dark': ((128, 125, 118), 0, .1, 0), 'mid_grey': ((110, 112, 116), 0, .25, 0),
    'dark_grey': ((72, 75, 80), 0, .25, 0), 'charcoal': ((46, 48, 52), 0, .25, 0),
    'black_iron': ((36, 37, 40), .3, .35, 0), 'rubber': ((40, 40, 42), 0, .2, 0),
    'steel_galv': ((160, 168, 172), .6, .45, 0), 'steel_dark': ((92, 98, 106), .5, .4, 0),
    'chrome': ((200, 204, 208), .9, .7, 0), 'tyre': ((44, 45, 48), 0, .15, 0),
    # woods
    'wood_fresh': ((196, 152, 100), 0, .1, 0), 'wood_pallet': ((205, 172, 120), 0, .1, 0),
    'wood_weathered': ((142, 124, 100), 0, .1, 0), 'wood_dark': ((96, 72, 54), 0, .1, 0),
    'wood_bench': ((170, 110, 66), 0, .2, 0), 'bark': ((104, 84, 66), 0, .05, 0),
    'log_end': ((206, 170, 122), 0, .05, 0), 'charred': ((40, 34, 31), 0, .05, 0),
    'plywood': ((214, 178, 118), 0, .1, 0), 'formwork_yellow': ((222, 176, 60), 0, .2, 0),
    'formwork_red': ((176, 58, 44), 0, .2, 0),
    # stone / earth
    'granite': ((122, 118, 116), 0, .35, 0), 'granite_dark': ((70, 68, 72), 0, .45, 0),
    'granite_red': ((130, 86, 74), 0, .35, 0), 'stone_warm': ((184, 172, 152), 0, .15, 0),
    'stone_cool': ((150, 152, 154), 0, .15, 0), 'travertine': ((206, 192, 166), 0, .2, 0),
    'earth': ((110, 86, 64), 0, .05, 0), 'earth_dark': ((80, 64, 50), 0, .05, 0),
    'sand': ((214, 188, 136), 0, .05, 0), 'sand_dark': ((184, 158, 108), 0, .05, 0),
    'gravel': ((150, 146, 138), 0, .05, 0), 'gravel_dark': ((112, 108, 102), 0, .05, 0),
    'ash': ((92, 88, 84), 0, .05, 0), 'ash_light': ((140, 136, 130), 0, .05, 0),
    'rock': ((128, 120, 108), 0, .1, 0), 'rock_dark': ((92, 86, 78), 0, .1, 0),
    'rock_light': ((160, 152, 138), 0, .1, 0), 'brick': ((146, 78, 62), 0, .1, 0),
    'brick_dark': ((118, 62, 50), 0, .1, 0), 'mortar': ((190, 182, 168), 0, .1, 0),
    # paints
    'red': ((184, 58, 50), 0, .35, 0), 'red_dark': ((138, 44, 40), 0, .3, 0),
    'orange': ((222, 120, 46), 0, .35, 0), 'yellow': ((230, 184, 54), 0, .35, 0),
    'yellow_soft': ((228, 200, 110), 0, .3, 0), 'ochre': ((200, 154, 70), 0, .25, 0),
    'cream': ((232, 214, 170), 0, .25, 0), 'navy': ((40, 62, 96), 0, .35, 0),
    'blue': ((58, 104, 160), 0, .35, 0), 'blue_soft': ((98, 140, 186), 0, .3, 0),
    'sky': ((136, 180, 214), 0, .3, 0), 'teal': ((52, 132, 130), 0, .3, 0),
    'green_dark': ((54, 84, 58), 0, .3, 0), 'green': ((82, 132, 72), 0, .3, 0),
    'green_soft': ((126, 164, 100), 0, .3, 0), 'olive': ((108, 112, 70), 0, .25, 0),
    'sage': ((140, 160, 130), 0, .25, 0), 'mil_green': ((88, 96, 64), 0, .2, 0),
    'mil_khaki': ((150, 140, 100), 0, .2, 0), 'mil_dark': ((62, 68, 50), 0, .2, 0),
    'purple': ((130, 88, 150), 0, .3, 0), 'brown': ((120, 86, 60), 0, .2, 0),
    'rust': ((150, 82, 48), .1, .15, 0), 'rust_dark': ((110, 62, 40), .1, .15, 0),
    'rust_light': ((178, 112, 66), .1, .15, 0), 'gold': ((226, 176, 72), 1, .62, 0),
    'gold_dark': ((172, 124, 46), 1, .5, 0), 'bronze': ((150, 110, 66), .8, .45, 0),
    # plastics
    'plastic_blue': ((44, 108, 180), 0, .45, 0), 'plastic_green': ((58, 150, 90), 0, .45, 0),
    'plastic_orange': ((226, 118, 40), 0, .45, 0), 'plastic_white': ((232, 232, 226), 0, .45, 0),
    'plastic_grey': ((150, 154, 158), 0, .4, 0), 'plastic_red': ((196, 50, 44), 0, .45, 0),
    'plastic_yellow': ((236, 196, 48), 0, .45, 0), 'plastic_black': ((50, 52, 56), 0, .4, 0),
    # fabric / rope
    'red_cloth': ((160, 40, 44), 0, .15, 0), 'red_cloth_dark': ((118, 30, 36), 0, .15, 0),
    'canvas': ((204, 194, 166), 0, .1, 0), 'bigbag': ((226, 222, 210), 0, .1, 0),
    'denim': ((66, 92, 130), 0, .1, 0), 'overall_orange': ((222, 112, 40), 0, .1, 0),
    'shirt_white': ((228, 226, 218), 0, .1, 0), 'towel_blue': ((98, 150, 196), 0, .1, 0),
    'shirt_green': ((110, 140, 90), 0, .1, 0), 'rope': ((188, 160, 112), 0, .1, 0),
    'net_green': ((96, 116, 104), 0, .1, 0), 'net_brown': ((118, 100, 80), 0, .1, 0),
    'cork': ((200, 140, 70), 0, .1, 0), 'float_red': ((196, 64, 50), 0, .3, 0),
    # plants
    'leaf_dark': ((52, 90, 48), 0, .15, 0), 'leaf': ((74, 118, 58), 0, .15, 0),
    'leaf_light': ((110, 150, 74), 0, .15, 0), 'hedge': ((66, 106, 54), 0, .15, 0),
    'hedge_dark': ((50, 84, 44), 0, .15, 0), 'reed': ((130, 148, 82), 0, .15, 0),
    'reed_dry': ((186, 170, 104), 0, .1, 0), 'cattail': ((112, 74, 46), 0, .1, 0),
    'flower_red': ((204, 64, 60), 0, .2, 0), 'flower_yellow': ((232, 196, 64), 0, .2, 0),
    'flower_purple': ((140, 90, 170), 0, .2, 0), 'flower_white': ((236, 232, 224), 0, .2, 0),
    'flower_pink': ((226, 120, 160), 0, .2, 0), 'soil': ((88, 66, 50), 0, .05, 0),
    'turf': ((96, 150, 70), 0, .15, 0), 'turf_light': ((126, 174, 88), 0, .15, 0),
    # glass / screens
    'glass_dark': ((52, 66, 78), 0, .85, 0), 'glass': ((96, 124, 140), 0, .85, 0),
    'glass_light': ((150, 180, 196), 0, .85, 0), 'screen_frame': ((36, 38, 42), 0, .4, 0),
    # emissive
    'neon_pink': ((255, 84, 164), 0, .5, 1.0), 'lantern': ((255, 214, 150), 0, .5, 1.0),
    'ember': ((255, 110, 40), 0, .3, 1.0), 'beacon_blue': ((70, 140, 255), 0, .6, .7),
    'beacon_red': ((255, 60, 50), 0, .6, .7), 'screen_blue': ((40, 110, 200), 0, .7, .6),
    'screen_sky': ((110, 180, 236), 0, .7, .6), 'screen_yellow': ((244, 196, 70), 0, .7, .6),
    'screen_navy': ((30, 60, 120), 0, .7, .6), 'screen_white': ((226, 234, 240), 0, .7, .55),
    'display_green': ((80, 200, 140), 0, .7, .5), 'atm_screen': ((90, 170, 210), 0, .7, .5),
    'button_red': ((220, 40, 36), 0, .6, .3), 'neon_pink_tube': ((255, 150, 200), 0, .6, 1.0),
}
ORDER = list(PALETTE)
assert len(ORDER) <= PER_ROW * PER_ROW


def uv_of(col):
    i = ORDER.index(col)
    c, r = i % PER_ROW, i // PER_ROW
    return ((c + .5) / PER_ROW, 1 - (r + .5) / PER_ROW)


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def write_atlases(folder, stem='MW86_StaticPalette_v01'):
    """Albedo (sRGB), MetallicSmoothness (R metal, A smoothness; URP Lit 'Metallic Alpha'), Emission (sRGB)."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    W = ATLAS_PX
    alb = [0.5] * (W * W * 4); ms = [0.0] * (W * W * 4); em = [0.0] * (W * W * 4)
    for i, name in enumerate(ORDER):
        rgb, metal, smooth, emit = PALETTE[name]
        c, r = i % PER_ROW, i // PER_ROW
        for py in range(CELL_PX):
            y = W - 1 - (r * CELL_PX + py)          # bpy pixels: row 0 = bottom
            for px in range(CELL_PX):
                x = c * CELL_PX + px
                k = (y * W + x) * 4
                alb[k:k + 4] = [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1]
                ms[k:k + 4] = [metal, metal, metal, smooth]
                e = [v / 255 * emit for v in rgb] if emit else [0, 0, 0]
                em[k:k + 4] = [e[0], e[1], e[2], 1]
    # fill unused cells with a neutral grey (already .5), alpha 1
    for i in range(len(ORDER), PER_ROW * PER_ROW):
        c, r = i % PER_ROW, i // PER_ROW
        for py in range(CELL_PX):
            y = W - 1 - (r * CELL_PX + py)
            for px in range(CELL_PX):
                k = (y * W + c * CELL_PX + px) * 4
                alb[k + 3] = 1; ms[k + 3] = .2; em[k + 3] = 1
    out = {}
    for suffix, px, cs in (('Albedo', alb, 'sRGB'), ('MetallicSmoothness', ms, 'Non-Color'), ('Emission', em, 'sRGB')):
        img = bpy.data.images.new(f'{stem}_{suffix}', W, W, alpha=True)
        img.colorspace_settings.name = cs
        img.pixels = px
        p = folder / f'{stem}_{suffix}.png'
        img.filepath_raw = str(p); img.file_format = 'PNG'; img.save()
        out[suffix] = p
        bpy.data.images.remove(img)
    return out


def palette_json():
    return {n: {'srgb': list(PALETTE[n][0]), 'metallic': PALETTE[n][1], 'smoothness': PALETTE[n][2],
                'emission': PALETTE[n][3], 'uv': [round(v, 5) for v in uv_of(n)]} for n in ORDER}


def make_material(atlas_paths, pack=True):
    m = bpy.data.materials.get(MAT_NAME)
    if m:
        return m
    m = bpy.data.materials.new(MAT_NAME)
    nt = m.node_tree; nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    def tex(key, cs):
        img = bpy.data.images.load(str(atlas_paths[key]), check_existing=True)
        img.colorspace_settings.name = cs
        if pack:
            img.pack()
        t = nodes.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Closest'
        return t
    ta = tex('Albedo', 'sRGB'); tm = tex('MetallicSmoothness', 'Non-Color'); te = tex('Emission', 'sRGB')
    links.new(ta.outputs['Color'], bsdf.inputs['Base Color'])
    sep = nodes.new('ShaderNodeSeparateColor'); links.new(tm.outputs['Color'], sep.inputs[0])
    links.new(sep.outputs[0], bsdf.inputs['Metallic'])
    inv = nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    links.new(tm.outputs['Alpha'], inv.inputs[1]); links.new(inv.outputs[0], bsdf.inputs['Roughness'])
    links.new(te.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 1.5
    return m


# ------------------------------------------------------------------ geometry
def _mat(loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    M = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4()
    if scale is not None:
        M = M @ Matrix.Diagonal(Vector(tuple(scale) + (1,)))
    return M


class Asset:
    """One mesh being built. lod=0 full detail, lod=1 reduced (no bevel, fewer segments, detail parts skipped)."""

    def __init__(self, name, lod=0, seed=1):
        self.name, self.lod = name, lod
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.facet = self.bm.faces.layers.int.new('facet')
        self.ucx = []          # (size, loc, rot) boxes or ('hull', points)
        self.rng = random.Random(seed)
        self.notes = []

    # ---- core: take a temp bmesh, bevel it, colour it, transform, merge
    def _add(self, pb, col, M, bevel=0.0, bevel_edges=None, segs=1, facet=False):
        if col not in PALETTE:
            raise KeyError(col)
        if bevel and self.lod == 0:
            edges = bevel_edges if bevel_edges is not None else list(pb.edges)
            if edges:
                bmesh.ops.bevel(pb, geom=edges, offset=bevel, offset_type='OFFSET', segments=segs, profile=.5,
                                affect='EDGES', clamp_overlap=True)
        elif bevel and self.lod == 1 and bevel > .03:
            edges = bevel_edges if bevel_edges is not None else list(pb.edges)
            if edges:
                bmesh.ops.bevel(pb, geom=edges, offset=bevel * .7, offset_type='OFFSET', segments=1, profile=.5,
                                affect='EDGES', clamp_overlap=True)
        bmesh.ops.transform(pb, matrix=M, verts=pb.verts)
        if M.determinant() < 0:
            bmesh.ops.reverse_faces(pb, faces=pb.faces)
        u = uv_of(col)
        vmap = {v: self.bm.verts.new(v.co) for v in pb.verts}
        for f in pb.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.smooth = True
            nf[self.facet] = 1 if facet else 0
            for l in nf.loops:
                l[self.uv].uv = u
        pb.free()

    def seg(self, n):
        return max(4, int(round(n * (.5 if self.lod else 1))))

    # ---- primitives (all sizes in metres; loc = centre unless noted)
    def box(self, size, loc, col, rot=(0, 0, 0), bevel=None, detail=False, taper=None, facet=False, segs=1):
        """Box centred at loc. taper=(sx,sy) scales the top face (pyramids/frustums)."""
        if detail and self.lod:
            return
        pb = bmesh.new()
        bmesh.ops.create_cube(pb, size=1.0)
        for v in pb.verts:
            v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
            if taper and v.co.z > 0:
                v.co.x *= taper[0]; v.co.y *= taper[1]
        if bevel is None:
            bevel = min(.05, .12 * min(size)) if min(size) >= .06 else 0
        self._add(pb, col, _mat(loc, rot), bevel, facet=facet, segs=segs)

    def cyl(self, r, h, loc, col, n=12, r2=None, rot=(0, 0, 0), bevel=None, detail=False, caps=True, facet=False):
        """Cylinder / cone, base centre at loc, along local +Z, then rotated."""
        if detail and self.lod:
            return
        n = self.seg(n)
        pb = bmesh.new()
        bmesh.ops.create_cone(pb, cap_ends=caps, cap_tris=False, segments=n, radius1=r,
                              radius2=r if r2 is None else r2, depth=h)
        for v in pb.verts:
            v.co.z += h / 2
        if bevel is None:
            bevel = min(.04, .15 * min(r, h)) if min(r, h) >= .05 else 0
        rims = [e for e in pb.edges if all(abs(v.co.z) < 1e-6 or abs(v.co.z - h) < 1e-6 for v in e.verts)
                and len(e.link_faces) == 2 and abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6] if caps else []
        self._add(pb, col, _mat(loc, rot), bevel if caps else 0, bevel_edges=rims, facet=facet)

    def tube(self, r_out, r_in, h, loc, col, n=12, rot=(0, 0, 0), detail=False):
        """Open pipe / ring with wall thickness, base at loc along +Z."""
        if detail and self.lod:
            return
        n = self.seg(n)
        pb = bmesh.new()
        rings = []
        for rr, z in ((r_out, 0), (r_out, h), (r_in, h), (r_in, 0)):
            rings.append([pb.verts.new((rr * math.cos(i * math.tau / n), rr * math.sin(i * math.tau / n), z)) for i in range(n)])
        for a in range(4):
            A, B = rings[a], rings[(a + 1) % 4]
            for i in range(n):
                j = (i + 1) % n
                pb.faces.new((A[i], A[j], B[j], B[i]))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, _mat(loc, rot))

    def sphere(self, r, loc, col, seg=10, rings=6, scale=(1, 1, 1), rot=(0, 0, 0), detail=False, facet=False):
        if detail and self.lod:
            return
        pb = bmesh.new()
        bmesh.ops.create_uvsphere(pb, u_segments=self.seg(seg), v_segments=max(3, self.seg(rings)), radius=r)
        self._add(pb, col, _mat(loc, rot, scale), facet=facet)

    def ico(self, r, loc, col, subdiv=1, scale=(1, 1, 1), rot=(0, 0, 0), noise=0.0, flat_bottom=None, detail=False, facet=True):
        """Faceted rock / lump. flat_bottom: clamp z (local, before scale) to >= this value."""
        if detail and self.lod:
            return
        pb = bmesh.new()
        bmesh.ops.create_icosphere(pb, subdivisions=subdiv if not self.lod else max(1, subdiv - 1), radius=r)
        for v in pb.verts:
            if noise:
                v.co *= 1 + self.rng.uniform(-noise, noise)
            if flat_bottom is not None and v.co.z < flat_bottom:
                v.co.z = flat_bottom
        self._add(pb, col, _mat(loc, rot, scale), facet=facet)

    def beam(self, p, q, r, col, n=6, detail=False, r2=None, caps=True):
        """Round bar from p to q."""
        if detail and self.lod:
            return
        p, q = Vector(p), Vector(q)
        d = q - p
        L = d.length
        if L < 1e-5:
            return
        rotq = Vector((0, 0, 1)).rotation_difference(d.normalized())
        n = max(3, self.seg(n)) if n > 3 else n
        pb = bmesh.new()
        bmesh.ops.create_cone(pb, cap_ends=caps, cap_tris=False, segments=n, radius1=r, radius2=r if r2 is None else r2, depth=L)
        for v in pb.verts:
            v.co.z += L / 2
        M = Matrix.Translation(p) @ rotq.to_matrix().to_4x4()
        self._add(pb, col, M)

    def bar(self, p, q, w, h, col, up=(0, 0, 1), detail=False, bevel=None):
        """Rectangular bar from p to q (w across, h along 'up')."""
        if detail and self.lod:
            return
        p, q = Vector(p), Vector(q)
        d = q - p; L = d.length
        if L < 1e-5:
            return
        x = d.normalized(); z = Vector(up)
        y = z.cross(x)
        if y.length < 1e-4:
            y = Vector((0, 1, 0)).cross(x)
        y.normalize(); z = x.cross(y).normalized()
        R = Matrix((x, y, z)).transposed().to_4x4()
        pb = bmesh.new()
        bmesh.ops.create_cube(pb, size=1.0)
        for v in pb.verts:
            v.co.x *= L; v.co.y *= w; v.co.z *= h
        if bevel is None:
            bevel = min(.03, .12 * min(w, h)) if min(w, h) >= .06 else 0
        self._add(pb, col, Matrix.Translation((p + q) / 2) @ R, bevel)

    def sweep(self, pts, r, col, n=6, closed=False, detail=False, radii=None):
        """Tube swept along a polyline (ropes, hoses, neon)."""
        if detail and self.lod:
            return
        pts = [Vector(p) for p in pts]
        ded = [pts[0]]
        for p in pts[1:]:
            if (p - ded[-1]).length > 1e-4:
                ded.append(p)
        if closed and len(ded) > 2 and (ded[0] - ded[-1]).length < 1e-4:
            ded.pop()
        pts = ded
        if self.lod and len(pts) > 6 and not closed:
            pts = pts[::2] + ([pts[-1]] if (len(pts) - 1) % 2 else [])
        n = max(3, self.seg(n)) if n > 3 else n
        pb = bmesh.new(); rings = []
        N = len(pts)
        u_prev = None
        for i, p in enumerate(pts):
            if closed:
                t = (pts[(i + 1) % N] - pts[i - 1])
            else:
                t = (pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)])
            t.normalize()
            if u_prev is None:          # first frame, then parallel transport (no twisting)
                a = Vector((0, 0, 1)) if abs(t.z) < .9 else Vector((1, 0, 0))
                u = t.cross(a).normalized()
            else:
                u = u_prev - t * u_prev.dot(t)
                u = u.normalized() if u.length > 1e-6 else t.cross(Vector((0, 0, 1))).normalized()
            u_prev = u
            w = t.cross(u).normalized()
            rr = radii[i] if radii else r
            rings.append([pb.verts.new(p + (u * math.cos(k * math.tau / n) + w * math.sin(k * math.tau / n)) * rr) for k in range(n)])
        segs = N if closed else N - 1
        for i in range(segs):
            A, B = rings[i], rings[(i + 1) % N]
            for k in range(n):
                j = (k + 1) % n
                pb.faces.new((A[k], A[j], B[j], B[k]))
        if not closed:
            pb.faces.new(list(reversed(rings[0]))); pb.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, Matrix())

    def lathe(self, prof, loc, col, n=16, rot=(0, 0, 0), detail=False, cap_top=True, cap_bottom=True, facet=False):
        """Surface of revolution around local Z; prof = [(r, z), ...] bottom to top."""
        if detail and self.lod:
            return
        n = self.seg(n)
        pb = bmesh.new(); rings = []
        for r, z in prof:
            if r < 1e-6:
                rings.append([pb.verts.new((0, 0, z))])
            else:
                rings.append([pb.verts.new((r * math.cos(i * math.tau / n), r * math.sin(i * math.tau / n), z)) for i in range(n)])
        for a in range(len(rings) - 1):
            A, B = rings[a], rings[a + 1]
            for i in range(n):
                j = (i + 1) % n
                if len(A) == 1:
                    pb.faces.new((A[0], B[i], B[j]))
                elif len(B) == 1:
                    pb.faces.new((A[i], A[j], B[0]))
                else:
                    pb.faces.new((A[i], A[j], B[j], B[i]))
        if cap_bottom and len(rings[0]) > 1:
            pb.faces.new(list(reversed(rings[0])))
        if cap_top and len(rings[-1]) > 1:
            pb.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, _mat(loc, rot), facet=facet)

    def prism(self, poly, h, loc, col, rot=(0, 0, 0), bevel=0.0, detail=False):
        """Extrude a 2D polygon (local XY, CCW) by h along +Z, base at loc."""
        if detail and self.lod:
            return
        pb = bmesh.new()
        bot = [pb.verts.new((x, y, 0)) for x, y in poly]
        top = [pb.verts.new((x, y, h)) for x, y in poly]
        pb.faces.new(list(reversed(bot))); pb.faces.new(top)
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            pb.faces.new((bot[i], bot[j], top[j], top[i]))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, _mat(loc, rot), bevel)

    def torus(self, R, r, loc, col, n=16, m=6, rot=(0, 0, 0), detail=False, scale=(1, 1, 1)):
        if detail and self.lod:
            return
        n = self.seg(n); m = max(4, self.seg(m))
        pb = bmesh.new(); rings = []
        for i in range(n):
            a = i * math.tau / n
            c = Vector((R * math.cos(a), R * math.sin(a), 0))
            out = Vector((math.cos(a), math.sin(a), 0))
            rings.append([pb.verts.new(c + out * r * math.cos(k * math.tau / m) + Vector((0, 0, r * math.sin(k * math.tau / m)))) for k in range(m)])
        for i in range(n):
            A, B = rings[i], rings[(i + 1) % n]
            for k in range(m):
                j = (k + 1) % m
                pb.faces.new((A[k], B[k], B[j], A[j]))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, _mat(loc, rot, scale))

    def strip(self, p, q, w, col):
        """Thin 3-sided prism without caps (net cords, wires): 6 tris."""
        p, q = Vector(p), Vector(q)
        d = q - p
        if d.length < 1e-5:
            return
        t = d.normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < .9 else Vector((1, 0, 0))
        u = t.cross(a).normalized(); v = t.cross(u).normalized()
        offs = [(u * math.cos(k * math.tau / 3) + v * math.sin(k * math.tau / 3)) * w * .58 for k in range(3)]
        pb = bmesh.new()
        A = [pb.verts.new(p + o) for o in offs]; B = [pb.verts.new(q + o) for o in offs]
        for k in range(3):
            j = (k + 1) % 3
            pb.faces.new((A[k], A[j], B[j], B[k]))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, Matrix())

    def grid_strips(self, corners, nu, nv, w, col, holes=None, sag=0.0, detail=False, at=None):
        """Net: cords along a bilinear patch. corners = (p00, p10, p11, p01) (u along p00->p10, v along p00->p01);
        holes = set of (i, j) cells torn out; a cord is skipped when every cell next to it is a hole."""
        if detail and self.lod:
            return
        if self.lod:
            nu, nv = max(2, (nu + 1) // 2), max(2, (nv + 1) // 2)
            holes = {(i // 2, j // 2) for i, j in (holes or ())}
        P = [Vector(c) for c in corners] if corners else None
        def at_(u, v):
            p = P[0] * (1 - u) * (1 - v) + P[1] * u * (1 - v) + P[2] * u * v + P[3] * (1 - u) * v
            if sag:
                p += Vector(sag) * (4 * u * (1 - u)) * (4 * v * (1 - v))
            return p
        f = (lambda u, v: Vector(at(u, v))) if at else at_
        holes = holes or set()
        def skip(cells):
            cells = [c for c in cells if 0 <= c[0] < nu and 0 <= c[1] < nv]
            return bool(cells) and all(c in holes for c in cells)
        for j in range(nv + 1):
            for i in range(nu):
                if not skip([(i, j - 1), (i, j)]):
                    self.strip(f(i / nu, j / nv), f((i + 1) / nu, j / nv), w, col)
        for i in range(nu + 1):
            for j in range(nv):
                if not skip([(i - 1, j), (i, j)]):
                    self.strip(f(i / nu, j / nv), f(i / nu, (j + 1) / nv), w, col)

    # ---- colliders (UCX_ convex boxes; Blender coords)
    def col_box(self, size, loc, rot=(0, 0, 0)):
        if self.lod == 0:
            self.ucx.append(('box', tuple(size), tuple(loc), tuple(rot)))

    def col_hull(self, points):
        if self.lod == 0:
            self.ucx.append(('hull', [tuple(p) for p in points]))

    # ---- extra shapes
    def add_mesh(self, me, col, M=None, facet=False):
        """Append existing mesh data (e.g. an evaluated skin-modifier figure)."""
        pb = bmesh.new(); pb.from_mesh(me)
        self._add(pb, col, M or Matrix(), facet=facet)

    def mound(self, rx, ry, h, loc, col, rings=5, segs=16, noise=.08, power=.8, rot=(0, 0, 0), detail=False, facet=True, seed=None):
        """Heap / pile: radial grid, height h*(1-r^2)^power with noise; flat base at loc."""
        if detail and self.lod:
            return
        rng = random.Random(seed) if seed is not None else self.rng
        segs = self.seg(segs); rings = max(2, self.seg(rings))
        pb = bmesh.new(); grid = []
        for i in range(rings + 1):
            t = i / rings                     # 0 = rim, 1 = top
            rr = 1 - t
            row = []
            for k in range(segs):
                a = k * math.tau / segs
                if i == rings:
                    break
                n = 1 + (rng.uniform(-noise, noise) if 0 < i else rng.uniform(-noise, noise) * .6)
                x = math.cos(a) * rr * rx * n; y = math.sin(a) * rr * ry * n
                z = h * (1 - rr * rr) ** power * (1 + (rng.uniform(-noise, noise) if i > 0 else 0)) if i > 0 else 0.0
                row.append(pb.verts.new((x, y, z)))
            grid.append(row)
        top = pb.verts.new((0, 0, h))
        for i in range(rings - 1):
            A, B = grid[i], grid[i + 1]
            for k in range(segs):
                j = (k + 1) % segs
                pb.faces.new((A[k], A[j], B[j], B[k]))
        last = grid[rings - 1]
        for k in range(segs):
            pb.faces.new((last[k], last[(k + 1) % segs], top))
        pb.faces.new(list(reversed(grid[0])))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        self._add(pb, col, _mat(loc, rot), facet=facet)
        return [tuple(v) for v in [(loc[0] + rx * math.cos(a), loc[1] + ry * math.sin(a), loc[2]) for a in
                                   [k * math.tau / 8 for k in range(8)]] + [(loc[0], loc[1], loc[2] + h)]]

    def pillow(self, size, loc, col, bulge=.08, cuts=2, rot=(0, 0, 0), detail=False):
        """Soft bag / cushion: subdivided box pushed outward in the middle of each face."""
        if detail and self.lod:
            return
        pb = bmesh.new(); bmesh.ops.create_cube(pb, size=1.0)
        bmesh.ops.subdivide_edges(pb, edges=pb.edges[:], cuts=cuts if not self.lod else 1, use_grid_fill=True)
        for v in pb.verts:
            x, y, z = v.co.x * 2, v.co.y * 2, v.co.z * 2      # -1..1
            v.co.x *= size[0] * (1 + bulge * (1 - y * y) * (1 - z * z * .6))
            v.co.y *= size[1] * (1 + bulge * (1 - x * x) * (1 - z * z * .6))
            v.co.z *= size[2] * (1 + bulge * .5 * (1 - x * x) * (1 - y * y))
        self._add(pb, col, _mat(loc, rot))

    # ---- finish
    def to_object(self, name, collection, sharp_deg=50.0):
        bm = self.bm
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        ng = [f for f in bm.faces if len(f.verts) > 4]
        if ng:
            bmesh.ops.triangulate(bm, faces=ng, quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.normal_update()
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) != 2:
                e.smooth = False
                continue
            ang = lf[0].normal.angle(lf[1].normal, 0)
            facet = lf[0][self.facet] or lf[1][self.facet]
            e.smooth = ang < math.radians(22 if facet else sharp_deg)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(bpy.data.materials[MAT_NAME])
        if 'facet' in me.attributes:
            me.attributes.remove(me.attributes['facet'])
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        mod = ob.modifiers.new('WN', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True; mod.mode = 'FACE_AREA'; mod.weight = 50
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me2 = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear()
        old = ob.data; ob.data = me2; bpy.data.meshes.remove(old); me2.name = name
        return ob

    def ucx_objects(self, root_name, collection):
        out = []
        for i, u in enumerate(self.ucx, 1):
            pb = bmesh.new()
            if u[0] == 'box':
                _, size, loc, rot = u
                bmesh.ops.create_cube(pb, size=1.0)
                bmesh.ops.transform(pb, matrix=_mat(loc, rot, size), verts=pb.verts)
            else:
                vs = [pb.verts.new(p) for p in u[1]]
                res = bmesh.ops.convex_hull(pb, input=vs)
                bmesh.ops.delete(pb, geom=[g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert)], context='VERTS')
                bmesh.ops.triangulate(pb, faces=pb.faces[:])
            me = bpy.data.meshes.new(f'UCX_{root_name}_{i:02d}')
            pb.to_mesh(me); pb.free()
            ob = bpy.data.objects.new(me.name, me)
            collection.objects.link(ob)
            ob.display_type = 'WIRE'; ob.hide_render = True
            out.append(ob)
        return out


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bounds(objs):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    return mn, mx


def export_fbx(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=True,
                             object_types={'EMPTY', 'MESH'}, mesh_smooth_type='OFF', use_mesh_modifiers=False,
                             add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_custom_props=False)
