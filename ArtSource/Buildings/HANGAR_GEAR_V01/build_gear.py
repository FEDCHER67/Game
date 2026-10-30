"""HANGAR_GEAR_V01 builder: the GEAR room (armoury / outfitter) of the base hangar (Blender 5.2, background).

Run:  blender -b --factory-startup --python build_gear.py -- --revision N [--no-render] [--samples S] [--res W] [--out DIR]
Every revision writes new numbered files (HANGAR_GEAR_vNN.blend / .fbx / _report.json / _materials.json, Previews/vNN);
existing files are never overwritten. The two derived textures in Textures/ are made once and then reused.

Axes: Blender Z up, metres, origin = the room's floor centre. The hall (front) side is Blender -Y; the FBX export
(axis_forward -Z, axis_up Y) makes that Unity +Z: Unity (x, y, z) = (-bx, bz, -by). The door is at Blender -X (Unity +X),
on the left of a player in the hall looking at the room, like the hangar's GEAR room (VadimHangarLab: door x 6.6-7.8).
Room: 11 x 6 m on the wall centre lines, walls 0.2 m, clear height 4.2 m, roof slab 0.2 m; door opening 1.2 x 2.3 m;
a 3 m window counter centred under the hangar's GEAR sign (sign centre Blender x +0.5 = Unity x -0.5, z 3.6).

Style: docs/specs/HANGAR_ROOMS_STYLE_2026-10-30.md and docs/ArtDirection.md section 2: chunky parts (>= 0.06 m, long
parts >= 0.10 m), three detail levels, one-segment bevels on secondary parts, two segments on the masses a player stands
next to, weighted normals, flat hard faces. Boards, frames, lips, latches, handles, vents and slats are geometry; the
textures (set 45, tileable copies in Assets/VadimLocal/Hangar/Textures) only add colour and wear; UVs are in metres and
the plank seams of the light wood (texture 12: 0.15 m rows) sit on the modelled grooves. Walls are painted steel:
trapezoid-ribbed olive-drab sheets outside (container style: graphite corner posts, castings, top and bottom rails),
tan plate panels with battens and a mid rail inside.

Objects: GEAR_<group>_<zone>; zone Hall / Room / Both = the hangar's rendering layers (lit by the hall lamps, the room
lamps, or both). COL_* boxes are collider volumes: the Unity prefab script turns them into BoxColliders.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] if (HERE.parents[2] / 'Assets').is_dir() else Path(r'C:/Users/chern_0eqkb03/Desktop/GAME')
ART = GAME / 'ArtSource' / 'Buildings' / 'HANGAR_GEAR_V01'
NAME = 'HANGAR_GEAR'
SHARED_TEX = GAME / 'Assets' / 'VadimLocal' / 'Hangar' / 'Textures'
UNITY_SHARED_TEX = 'Assets/VadimLocal/Hangar/Textures'
UNITY_GEAR_TEX = 'Assets/VadimLocal/Hangar/Rooms/Gear/Textures'
TEXOUT = ART / 'Textures'

ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--no-render', action='store_true')
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--res', type=int, default=1280)
ap.add_argument('--out', default='', help='output folder for test runs (default: the ArtSource folder)')
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = f'v{args.revision:02d}'
OUT = Path(args.out) if args.out else ART
OUT.mkdir(parents=True, exist_ok=True)
blend_path = OUT / f'{NAME}_{REV}.blend'
fbx_path = OUT / f'{NAME}_{REV}.fbx'
report_path = OUT / f'{NAME}_{REV}_report.json'
mats_path = OUT / f'{NAME}_{REV}_materials.json'
preview_dir = OUT / 'Previews' / REV
for p in (blend_path, fbx_path, report_path, mats_path):
    if p.exists():
        sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
random.seed(30)

# ------------------------------------------------------------------ room dimensions (Blender coordinates)
XI, XO = 5.4, 5.6           # inner / outer half width (walls centred on x = +-5.5)
YI, YO = 2.9, 3.1           # inner / outer half depth (front wall y -3.1..-2.9, back wall 2.9..3.1)
H = 4.2                     # clear height = underside of the roof slab
ROOF_T = 0.2
DOOR = (-4.95, -3.65, 0.0, 2.35)        # rough opening x0, x1, z0, z1 (clear 1.2 x 2.3 inside the casings)
WIN = (-1.05, 2.05, 1.0, 2.2)           # rough opening (clear x -1.0..2.0, z 1.05 counter top .. 2.15)
RIB = (0.30, 0.10, 0.05, 0.035)         # outer steel sheet: pitch, flat crest, slope, depth (trapezoid ribs)
PANEL = 1.2                             # inner steel plate panels: batten spacing
PLANK = 0.15                            # light wood plank (texture 12: 7 planks per 1.05 m tile)
GROOVE_HALF, GROOVE_DEPTH = 0.014, 0.012


# ------------------------------------------------------------------ colour helpers
def s2l(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def l2s(v):
    return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


# ------------------------------------------------------------------ textures
TEXOUT.mkdir(parents=True, exist_ok=True)


def shared_img(n):
    return bpy.data.images.load(str(SHARED_TEX / f'Hangar_Tex_{n}_v01.png'), check_existing=True)


def neutral_tex(src, out, contrast, mean=0.80):
    """A grey copy of a set-45 texture (luminance, variation scaled by `contrast`, mean 0.80) so an accent tint keeps
    the texture's wear without its colour."""
    p = TEXOUT / f'Gear_Tex_{out}_v01.png'
    if not p.exists():
        s = shared_img(src)
        w, h = s.size
        a = np.empty(w * h * 4, np.float32)
        s.pixels.foreach_get(a)
        a = a.reshape(h, w, 4)
        lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
        m0 = lum.mean()
        lum = np.clip((m0 + (lum - m0) * contrast) * (mean / m0), 0.0, 1.0)
        im = bpy.data.images.new(f'Gear_Tex_{out}_new', w, h, alpha=False)
        im.pixels.foreach_set(np.dstack([lum, lum, lum, np.ones_like(lum)]).astype(np.float32).ravel())
        im.filepath_raw = str(p)
        im.file_format = 'PNG'
        im.save()
    im = bpy.data.images.load(str(p), check_existing=True)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    g = a.reshape(-1, 4)[:, 0]
    lin = np.where(g <= 0.04045, g / 12.92, ((g + 0.055) / 1.055) ** 2.4)
    return im, float(lin.mean()), f'{UNITY_GEAR_TEX}/{p.name}'


def hazard_tex(yellow='#E4DC3E', black='#1E1D1B'):
    """Texture 06's diagonal stripes redrawn crisp in two flat colours (a lemon yellow that stays yellow, not orange,
    under the warm 3000 K lamps), 2 px anti-aliased edges."""
    p = TEXOUT / 'Gear_Tex_06Y_HazardCrisp_v01.png'
    if not p.exists():
        s_ = shared_img('06_Hazard')
        w, h = s_.size
        a = np.empty(w * h * 4, np.float32)
        s_.pixels.foreach_get(a)
        a = a.reshape(h, w, 4)
        lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
        t = np.clip((lum - 0.30) / 0.10, 0.0, 1.0)[..., None]
        y = np.array(hexrgb(yellow), np.float32)
        k = np.array(hexrgb(black), np.float32)
        rgb = k * (1 - t) + y * t
        im = bpy.data.images.new('Gear_Tex_06Y_new', w, h, alpha=False)
        im.pixels.foreach_set(np.dstack([rgb, np.ones((h, w, 1), np.float32)]).astype(np.float32).ravel())
        im.filepath_raw = str(p)
        im.file_format = 'PNG'
        im.save()
    return bpy.data.images.load(str(p), check_existing=True), f'{UNITY_GEAR_TEX}/{p.name}'


# ------------------------------------------------------------------ materials (Blender preview == Unity URP Lit table)
MATS, MATINFO = {}, []


def make_mat(name, tint_srgb, img=None, unity_tex='', tile=(1.0, 1.0), smooth=0.15, metal=0.0, emit=None):
    """tint_srgb multiplies the texture (Unity _BaseColor); emit = (sRGB colour, intensity) for _EmissionColor."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tint_lin = [s2l(c) for c in tint_srgb]
    if img is not None:
        uv = nt.nodes.new('ShaderNodeUVMap')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1.0 / tile[0], 1.0 / tile[1], 1.0)
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = img
        ti.interpolation = 'Linear'
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        ca, cb = [i for i in mix.inputs if i.type == 'RGBA'][:2]
        cb.default_value = (*tint_lin, 1.0)
        nt.links.new(uv.outputs[0], mp.inputs['Vector'])
        nt.links.new(mp.outputs[0], ti.inputs['Vector'])
        nt.links.new(ti.outputs['Color'], ca)
        nt.links.new(next(o for o in mix.outputs if o.type == 'RGBA'), b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*tint_lin, 1.0)
    b.inputs['Roughness'].default_value = 1.0 - smooth
    b.inputs['Metallic'].default_value = metal
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.3
    if emit:
        b.inputs['Emission Color'].default_value = (*[s2l(c) for c in emit[0]], 1.0)
        b.inputs['Emission Strength'].default_value = emit[1]
    m.diffuse_color = (*tint_lin, 1.0)
    MATS[name] = m
    MATINFO.append({'name': name, 'texture': unity_tex, 'tileW': tile[0], 'tileH': tile[1],
                    'color': [round(c, 4) for c in tint_srgb], 'smoothness': smooth, 'metallic': metal,
                    'emission': [round(c, 4) for c in emit[0]] if emit else [], 'emissionIntensity': emit[1] if emit else 0.0})


def grey(t):
    return (t, t, t)


def ntint(hexc, mean):
    """sRGB tint that turns a neutral texture (linear mean `mean`) into the target average colour hexc."""
    return tuple(l2s(min(1.0, s2l(c) / mean)) for c in hexrgb(hexc))


# Vadim 30.10: each room its own style outside and inside, no wood cladding; every wall surface one even colour with soft
# shading only from the real ribs / battens; the armoury reads military at a glance: olive-drab ribbed steel outside,
# tan steel plate panels inside, khaki / dark tan accents, olive metal, camo; hazard stripes crisp, yellow under 3000 K.
metal_n, metal_mean, metal_n_unity = neutral_tex('09_OliveMetal', '09N_MetalNeutral', 0.5)
lwood_n, lwood_mean, lwood_n_unity = neutral_tex('12_LightWood', '12N_LightWoodNeutral', 0.25)
haz_img, haz_unity = hazard_tex()
ST = lambda n: f'{UNITY_SHARED_TEX}/Hangar_Tex_{n}_v01.png'  # noqa: E731
make_mat('GEAR_Floor_Concrete', grey(.75), shared_img('01_Concrete'), ST('01_Concrete'), (6.0, 6.0), .15)
make_mat('GEAR_Wall_Outside', ntint('#5C6040', metal_mean), metal_n, metal_n_unity, (1.5, 1.5), .2, .15)
make_mat('GEAR_Wall_Inside', ntint('#9C8F72', metal_mean), metal_n, metal_n_unity, (1.5, 1.5), .15, .1)
make_mat('GEAR_Graphite', grey(.71), shared_img('04_Graphite'), ST('04_Graphite'), (2.0, 2.0), .25, .3)
make_mat('GEAR_OliveMetal', grey(.87), shared_img('09_OliveMetal'), ST('09_OliveMetal'), (1.5, 1.5), .25, .2)
make_mat('GEAR_Crate', ntint('#4E5233', metal_mean), metal_n, metal_n_unity, (1.0, 1.0), .2, .1)
make_mat('GEAR_Khaki', ntint('#7A7A4E', metal_mean), metal_n, metal_n_unity, (1.5, 1.5), .2, .1)
make_mat('GEAR_DarkTan', ntint('#8C7A55', metal_mean), metal_n, metal_n_unity, (1.5, 1.5), .1)
make_mat('GEAR_Camo', grey(.94), shared_img('10_Camo'), ST('10_Camo'), (1.0, 1.0), .05)
make_mat('GEAR_LightWood', ntint('#A08A68', lwood_mean), lwood_n, lwood_n_unity, (1.305, 1.05), .1)
make_mat('GEAR_Hazard', grey(1.0), haz_img, haz_unity, (1.0, 1.0), .25)
make_mat('GEAR_ToyOrange', hexrgb('#C8642A'), smooth=.3)
make_mat('GEAR_OffWhite', hexrgb('#D9CDB4'), smooth=.2)
make_mat('GEAR_LampWarm', (1.0, .85, .6), smooth=.3, emit=((1.0, .706, .42), 2.2))

# ------------------------------------------------------------------ accumulators: one mesh per (group, zone)
col = bpy.data.collections.new(NAME)
scene.collection.children.link(col)
col_cols = bpy.data.collections.new('Colliders')
scene.collection.children.link(col_cols)


class Acc:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.mats = []

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)


ACC = {}
ITEMS = []          # floating / sinking check: (item, support z, lowest z)
_item = None
COLLIDERS = []
TRIS = {}           # triangles per prop category (report)
CAT = ['shell']


def cat(name):
    CAT[0] = name


def acc(group, zone):
    k = f'GEAR_{group}_{zone}'
    if k not in ACC:
        ACC[k] = Acc(k)
    return ACC[k]


def new_part():
    bm = bmesh.new()
    bm.loops.layers.uv.new('UVMap')
    return bm


def box_part(x0, x1, y0, y1, z0, z1, faces=None, bm=None):
    """Box from corner ranges; faces = subset of '+x -x +y -y +z -z' (None = all)."""
    bm = bm or new_part()
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return hexa_part(c, faces, bm)


def hexa_part(c, faces=None, bm=None):
    """Hexahedron from 8 corners (bottom 0-3 counter-clockwise from (-x,-y), then top 4-7)."""
    bm = bm or new_part()
    v = [bm.verts.new(p) for p in c]
    spec = {'-z': (0, 3, 2, 1), '+z': (4, 5, 6, 7), '-y': (0, 1, 5, 4), '+x': (1, 2, 6, 5), '+y': (2, 3, 7, 6), '-x': (3, 0, 4, 7)}
    for k, idx in spec.items():
        if faces is None or k in faces:
            bm.faces.new([v[i] for i in idx])
    if faces is not None:
        for vv in [x for x in v if not x.link_faces]:
            bm.verts.remove(vv)
    return bm


def cyl_part(r, z0, z1, seg=12, caps=True, rot=0.0, bm=None):
    """Prism along z around the origin; rot in radians (octagon with flats on the axes: seg 8, rot pi/8)."""
    bm = bm or new_part()
    bot, top = [], []
    for i in range(seg):
        a = rot + 2 * math.pi * i / seg
        bot.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z0)))
        top.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z1)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    if caps:
        bm.faces.new(list(reversed(bot)))
        bm.faces.new(top)
    return bm


def bar_part(p0, p1, apothem, seg=8, caps=True):
    """Octagonal (or seg-sided) bar between two points, flats on the axes; caps=False when both ends are buried."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    r = apothem / math.cos(math.pi / seg)
    bm = cyl_part(r, 0.0, d.length, seg, caps, math.pi / seg)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    M = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def groove_part(axis, c, s, a_axis, a0, a1, b0, b1, step, depth=GROOVE_DEPTH, half=GROOVE_HALF, margin=0.03, phase=0.0):
    """A flat face (normal s along `axis`, plane coordinate c) with V grooves across a_axis every `step` (seams at
    phase + k * step), running along the third axis from b0 to b1. Grooves stop `margin` short of a0 / a1."""
    bm = new_part()
    b_axis = 3 - axis - a_axis
    pts = [(a0, 0.0)]
    k = math.ceil((a0 + margin - phase) / step)
    while phase + k * step < a1 - margin:
        sm = phase + k * step
        pts += [(sm - half, 0.0), (sm, depth), (sm + half, 0.0)]
        k += 1
    pts.append((a1, 0.0))
    rows = []
    for a, d in pts:
        row = []
        for b in (b0, b1):
            co = [0.0, 0.0, 0.0]
            co[axis] = c - s * d
            co[a_axis] = a
            co[b_axis] = b
            row.append(bm.verts.new(co))
        rows.append(row)
    want = Vector([0, 0, 0])
    want[axis] = s
    for i in range(len(rows) - 1):
        f = bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
        f.normal_update()
        if f.normal.dot(want) < 0:
            f.normal_flip()
    return bm


def rib_part(axis, c, s, a_axis, a0, a1, b0, b1, rib=RIB):
    """Trapezoid-ribbed sheet (normal s along `axis`, crest plane c): crests flat, valleys `depth` deep, ribs across
    a_axis at multiples of the pitch, running along the third axis from b0 to b1."""
    pitch, crest, slope, depth = rib

    def dep(u):
        t = u % pitch
        if t <= crest:
            return 0.0
        if t <= crest + slope:
            return (t - crest) / slope * depth
        if t <= pitch - slope:
            return depth
        return (pitch - t) / slope * depth
    us = {a0, a1}
    for k in range(math.floor(a0 / pitch) - 1, math.ceil(a1 / pitch) + 1):
        for o in (0.0, crest, crest + slope, pitch - slope):
            u = k * pitch + o
            if a0 + 1e-4 < u < a1 - 1e-4:
                us.add(u)
    bm = new_part()
    b_axis = 3 - axis - a_axis
    rows = []
    for u in sorted(us):
        row = []
        for b in (b0, b1):
            co = [0.0, 0.0, 0.0]
            co[axis] = c - s * dep(u)
            co[a_axis] = u
            co[b_axis] = b
            row.append(bm.verts.new(co))
        rows.append(row)
    want = Vector([0, 0, 0])
    want[axis] = s
    for i in range(len(rows) - 1):
        f = bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
        f.normal_update()
        if f.normal.dot(want) < 0:
            f.normal_flip()
    return bm


def panel_face(group, axis, c, s, a_axis, a0, a1, z0, z1, mat='GEAR_Wall_Inside'):
    """Inner steel plate wall: one flat face + dark-tan battens every PANEL m (2 cm proud) + a graphite mid rail
    at 1.15-1.25 m (2.5 cm proud) where the face spans that height."""
    bm = new_part()
    v = []
    for a, z in ((a0, z0), (a1, z0), (a1, z1), (a0, z1)):
        co = [0.0, 0.0, 0.0]
        co[axis] = c
        co[a_axis] = a
        co[2] = z
        v.append(bm.verts.new(co))
    f = bm.faces.new(v)
    f.normal_update()
    want = Vector([0, 0, 0])
    want[axis] = s
    if f.normal.dot(want) < 0:
        f.normal_flip()
    emit(bm, group, 'Room', mat, uv_axis=axis)

    def strip(a_lo, a_hi, za, zb, proud, m, bev_w=None):
        lo = [0.0, 0.0, 0.0]
        hi = [0.0, 0.0, 0.0]
        lo[axis], hi[axis] = sorted((c - s * 0.01, c + s * proud))
        lo[a_axis], hi[a_axis] = a_lo, a_hi
        lo[2], hi[2] = za, zb
        box(group, 'Room', m, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], bev=(bev_w, 1) if bev_w else None)
    k = math.ceil((a0 + 0.12) / PANEL)
    while k * PANEL < a1 - 0.12:
        u = k * PANEL
        strip(u - 0.045, u + 0.045, z0, z1, 0.02, 'GEAR_DarkTan')
        k += 1
    if z0 <= 1.15 and z1 >= 1.25:
        strip(a0, a1, 1.15, 1.25, 0.025, 'GEAR_Graphite')


def bevel(bm, width, segs=1, min_angle=60.0):
    bm.normal_update()
    edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) >= math.radians(min_angle)]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type='OFFSET', segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    return bm


def uv_box(bm, axis=None, off=(0.0, 0.0)):
    uvl = bm.loops.layers.uv['UVMap']
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        a = axis if axis is not None else max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            co = lp.vert.co
            u, v = (co.y, co.z) if a == 0 else (co.x, co.z) if a == 1 else (co.x, co.y)
            lp[uvl].uv = (u + off[0], v + off[1])


def emit(part, group, zone, mat, M=None, bev=None, uv_axis=None, uv_off=(0.0, 0.0)):
    """Bevel (width, segments), metre UVs in the part's own space, transform, merge into GEAR_<group>_<zone>."""
    if bev:
        bevel(part, bev[0], bev[1])
    uv_box(part, uv_axis, uv_off)
    if M is not None:
        bmesh.ops.transform(part, matrix=M, verts=part.verts)
    a = acc(group, zone)
    mi = a.slot(mat)
    TRIS[CAT[0]] = TRIS.get(CAT[0], 0) + sum(len(f.verts) - 2 for f in part.faces)
    src_uv = part.loops.layers.uv['UVMap']
    vmap = {v: a.bm.verts.new(v.co) for v in part.verts}
    for f in part.faces:
        nf = a.bm.faces.new([vmap[v] for v in f.verts])
        nf.material_index = mi
        nf.smooth = True
        for ls, ld in zip(f.loops, nf.loops):
            ld[a.uv].uv = ls[src_uv].uv
    if _item is not None and part.verts:
        _item[2] = min(_item[2], min(v.co.z for v in part.verts))
    part.free()


def item(name, support):
    """Start a prop whose lowest point must rest on z = support (checked in the report)."""
    global _item
    end_item()
    _item = [name, support, 1e9]


def end_item():
    global _item
    if _item is not None:
        ITEMS.append(tuple(_item))
    _item = None


def collider(name, x0, x1, y0, y1, z0, z1):
    COLLIDERS.append((name, (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1))))


def T(x=0.0, y=0.0, z=0.0, rz=0.0, rx=0.0, ry=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X')


def box(group, zone, mat, x0, x1, y0, y1, z0, z1, bev=None, faces=None, M=None, uv_axis=None, uv_off=(0.0, 0.0)):
    emit(box_part(x0, x1, y0, y1, z0, z1, faces), group, zone, mat, M, bev, uv_axis, uv_off)


# ------------------------------------------------------------------ shell: walls with real boards
def solid_rects(cols, holes, z_top):
    out = []
    for a, b in zip(cols, cols[1:]):
        cuts = sorted([h for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6], key=lambda h: h[2])
        z = 0.0
        for h in cuts:
            if h[2] > z:
                out.append((a, b, z, h[2]))
            z = max(z, h[3])
        if z < z_top:
            out.append((a, b, z, z_top))
    return out


def walls():
    # front wall: ribbed olive-drab steel outside, tan plate panels inside; reveals are covered by the casings
    front_cols = [-XI, DOOR[0], DOOR[1], WIN[0], WIN[1], XI]
    for i, (a, b, z0, z1) in enumerate(solid_rects(front_cols, [DOOR, WIN], H)):
        emit(rib_part(1, -YO, -1, 0, a, b, z0, z1), 'Shell', 'Hall', 'GEAR_Wall_Outside', uv_axis=1)
        panel_face('Shell', 1, -YI, 1, 0, a, b, z0, z1)
        collider(f'COL_wall_front_{i}', a, b, -YO, -YI, z0, z1)
    # side walls run the full depth; front ends hidden by the corner posts, back ends by the hangar wall
    for s in (-1, 1):
        emit(rib_part(0, s * XO, s, 1, -YO, YO, 0.0, H), 'Shell', 'Hall', 'GEAR_Wall_Outside', uv_axis=0)
        panel_face('Shell', 0, s * XI, -s, 1, -YI, YI, 0.0, H)
        collider(f'COL_wall_side_{"L" if s < 0 else "R"}', s * XI, s * XO, -YO, YO, 0, H)
    # back wall: a separate object (it stands against the hangar's own back wall; the outer face is plain graphite)
    panel_face('BackWall', 1, YI, -1, 0, -XI, XI, 0.0, H)
    box('BackWall', 'Room', 'GEAR_Graphite', -XI, XI, YI, YO, 0, H, faces={'+y'})
    collider('COL_wall_back', -XI, XI, YI, YO, 0, H)

    # container frame: graphite corner posts, corner castings top and bottom, top rails, bottom (kick) rails
    for s in (-1, 1):
        xa, xb = sorted((s * 5.36, s * 5.68))
        box('Shell', 'Both', 'GEAR_Graphite', xa, xb, -3.18, -2.84, 0, H, bev=(0.03, 1))
        box('Shell', 'Both', 'GEAR_Graphite', xa, xb, 2.84, 3.08, 0, H, bev=(0.03, 1))
        ca, cb = sorted((s * 5.34, s * 5.70))
        for za, zb in ((0.0, 0.22), (H - 0.22, H)):
            box('Shell', 'Hall', 'GEAR_Graphite', ca, cb, -3.21, -2.96, za, zb, bev=(0.02, 1))
        ra, rb = sorted((s * 5.57, s * 5.68))
        box('Shell', 'Hall', 'GEAR_Graphite', ra, rb, -2.96, 3.08, H - 0.20, H, bev=(0.015, 1))
        box('Shell', 'Hall', 'GEAR_Graphite', ra, rb, -2.96, 3.08, 0, 0.15, bev=(0.015, 1))
    box('Shell', 'Hall', 'GEAR_Graphite', -5.34, 5.34, -3.17, -3.06, H - 0.20, H, bev=(0.015, 1))

    # door casing: jambs and head through the wall, 0.10 m bands on both faces, 3-4 cm proud
    dx0, dx1 = DOOR[0], DOOR[1]
    for x0, x1 in ((dx0 - 0.10, dx0 + 0.05), (dx1 - 0.05, dx1 + 0.10)):
        box('Shell', 'Both', 'GEAR_Graphite', x0, x1, -3.14, -2.87, 0.0, 2.45, bev=(0.02, 1))
    box('Shell', 'Both', 'GEAR_Graphite', dx0 - 0.10, dx1 + 0.10, -3.14, -2.87, 2.30, 2.45, bev=(0.02, 1))
    # window casing (the counter top is the sill)
    wx0, wx1 = WIN[0], WIN[1]
    for x0, x1 in ((wx0 - 0.10, wx0 + 0.05), (wx1 - 0.05, wx1 + 0.10)):
        box('Shell', 'Both', 'GEAR_Graphite', x0, x1, -3.14, -2.87, 0.95, 2.30, bev=(0.02, 1))
    box('Shell', 'Both', 'GEAR_Graphite', wx0 - 0.10, wx1 + 0.10, -3.14, -2.87, 2.15, 2.30, bev=(0.02, 1))
    # roller-shutter box over the window (khaki), end plates, guide rails down the casing, the shutter's bottom bar
    box('Shell', 'Hall', 'GEAR_Khaki', wx0 - 0.15, wx1 + 0.15, -3.40, -3.08, 2.32, 2.60, bev=(0.04, 2))
    for xa, xb in ((wx0 - 0.20, wx0 - 0.15), (wx1 + 0.15, wx1 + 0.20)):
        box('Shell', 'Hall', 'GEAR_Graphite', xa, xb, -3.43, -3.07, 2.30, 2.62, bev=(0.01, 1))
    for xa, xb in ((wx0 - 0.17, wx0 - 0.09), (wx1 + 0.09, wx1 + 0.17)):
        box('Shell', 'Hall', 'GEAR_Graphite', xa, xb, -3.23, -3.135, 1.06, 2.32, bev=(0.012, 1))
    box('Shell', 'Hall', 'GEAR_Graphite', wx0 - 0.07, wx1 + 0.07, -3.30, -3.20, 2.26, 2.325, bev=(0.012, 1))

    # graphite bottom rail outside (front) and skirting inside (covers the panel feet)
    for x0, x1 in ((-5.34, dx0 - 0.10), (dx1 + 0.10, -1.26), (2.26, 5.34)):
        box('Shell', 'Hall', 'GEAR_Graphite', x0, x1, -3.17, -3.06, 0, 0.15, bev=(0.015, 1))
    for x0, x1 in ((-5.36, dx0 - 0.10), (dx1 + 0.10, -1.24), (2.24, 5.36)):
        box('Shell', 'Room', 'GEAR_Graphite', x0, x1, -2.93, -2.86, 0, 0.10, bev=(0.015, 1))
    for s in (-1, 1):
        box('Shell', 'Room', 'GEAR_Graphite', *sorted((s * 5.43, s * 5.36)), -2.84, 2.84, 0, 0.10, bev=(0.015, 1))
    box('BackWall', 'Room', 'GEAR_Graphite', -5.36, 5.36, 2.86, 2.93, 0, 0.10, bev=(0.015, 1))

    # outside wall lamp over the door (emissive only)
    cx = (dx0 + dx1) / 2
    box('Shell', 'Hall', 'GEAR_Graphite', cx - 0.25, cx + 0.25, -3.26, -3.06, 2.60, 2.78, bev=(0.025, 1))
    box('Shell', 'Hall', 'GEAR_LampWarm', cx - 0.20, cx + 0.20, -3.23, -3.11, 2.575, 2.605)
    # hazard guards on the hall side of the door
    for x0, x1 in ((dx0 - 0.16, dx0 + 0.03), (dx1 - 0.03, dx1 + 0.16)):
        item('door hazard guard', 0.0)
        box('Shell', 'Hall', 'GEAR_Hazard', x0, x1, -3.29, -3.10, 0.0, 1.0, bev=(0.02, 1))
        collider('COL_door_guard', x0, x1, -3.29, -3.10, 0, 1.0)
    end_item()


def ceiling():
    # roof slab: underside (one face over the whole footprint, closes the board grooves), top + edges for the hall
    box('Ceiling', 'Room', 'GEAR_Graphite', -5.75, 5.75, -3.25, 3.10, H, H + ROOF_T, faces={'-z'})
    box('Ceiling', 'Hall', 'GEAR_Graphite', -5.75, 5.75, -3.25, 3.10, H, H + ROOF_T, faces={'+z'})
    collider('COL_roof', -5.75, 5.75, -3.25, 3.10, H, H + ROOF_T)
    box('Ceiling', 'Hall', 'GEAR_Graphite', -5.81, 5.81, -3.31, -3.21, H - 0.06, H + ROOF_T + 0.06, bev=(0.02, 1))
    for s in (-1, 1):
        box('Ceiling', 'Hall', 'GEAR_Graphite', *sorted((s * 5.71, s * 5.81)), -3.21, 3.08, H - 0.06, H + ROOF_T + 0.06, bev=(0.02, 1))
    # joists and two warm strip lamps hanging under them
    for x in (-2.75, 2.75):
        box('Ceiling', 'Room', 'GEAR_Graphite', x - 0.07, x + 0.07, -2.95, 2.95, H - 0.18, H + 0.01, bev=(0.02, 1))
        for y in (-0.55, 0.55):
            box('Ceiling', 'Room', 'GEAR_Graphite', x - 0.03, x + 0.03, y - 0.03, y + 0.03, 3.73, H - 0.17)
        box('Ceiling', 'Room', 'GEAR_Graphite', x - 0.12, x + 0.12, -0.75, 0.75, 3.62, 3.74, bev=(0.02, 1))
        box('Ceiling', 'Room', 'GEAR_LampWarm', x - 0.09, x + 0.09, -0.70, 0.70, 3.60, 3.625)


# ------------------------------------------------------------------ props
def crate(name, cx, cy, z0, w, d, h, rz=0.0, zone='Room', group='Props', corners=True, handles=True):
    """Olive crate: skid band, body, overhanging lid (real seam), corner guards, two latches (local -y), side bar handles."""
    M = T(cx, cy, z0, rz)
    item(name, z0)
    hw, hd = w / 2, d / 2
    seam = h - 0.10
    box(group, zone, 'GEAR_Crate', -hw - 0.012, hw + 0.012, -hd - 0.012, hd + 0.012, 0.0, 0.06, bev=(0.01, 1), M=M)
    box(group, zone, 'GEAR_Crate', -hw, hw, -hd, hd, 0.005, seam, bev=(0.025, 1), M=M)
    box(group, zone, 'GEAR_Crate', -hw - 0.015, hw + 0.015, -hd - 0.015, hd + 0.015, seam + 0.008, h, bev=(0.02, 1), M=M)
    if corners:
        for sx in (-1, 1):
            for sy in (-1, 1):
                xa, xb = sorted((sx * (hw - 0.05), sx * (hw + 0.012)))
                ya, yb = sorted((sy * (hd - 0.05), sy * (hd + 0.012)))
                box(group, zone, 'GEAR_Crate', xa, xb, ya, yb, 0.06, seam - 0.004, M=M)
    for sx in (-1, 1):
        lx = sx * hw * 0.55
        box(group, zone, 'GEAR_Graphite', lx - 0.05, lx + 0.05, -hd - 0.02, -hd + 0.005, seam - 0.13, seam - 0.03, M=M)
        box(group, zone, 'GEAR_Graphite', lx - 0.035, lx + 0.035, -hd - 0.048, -hd - 0.016, seam - 0.11, seam + 0.06, M=M)
    hz = min(h * 0.55, seam - 0.08)
    for sx in ((-1, 1) if handles else ()):
        xa, xb = sorted((sx * (hw - 0.005), sx * (hw + 0.045)))
        for sy in (-1, 1):
            box(group, zone, 'GEAR_Graphite', xa, xb, sy * 0.10 - 0.02, sy * 0.10 + 0.02, hz - 0.02, hz + 0.02, M=M)
        ga, gb = sorted((sx * (hw + 0.035), sx * (hw + 0.075)))
        box(group, zone, 'GEAR_Graphite', ga, gb, -0.12, 0.12, hz - 0.022, hz + 0.022, M=M)
    end_item()


def ammo_can(cx, cy, z0, zone='Room'):
    item('ammo can', z0)
    M = T(cx, cy, z0, random.uniform(-0.08, 0.08))
    box('Props', zone, 'GEAR_OliveMetal', -0.12, 0.12, -0.07, 0.07, 0.0, 0.13, bev=(0.015, 1), M=M)
    box('Props', zone, 'GEAR_OliveMetal', -0.125, 0.125, -0.075, 0.075, 0.135, 0.17, M=M)
    for x in (-0.05, 0.05):
        box('Props', zone, 'GEAR_Graphite', x - 0.012, x + 0.012, -0.015, 0.015, 0.165, 0.21, M=M)
    box('Props', zone, 'GEAR_Graphite', -0.07, 0.07, -0.02, 0.02, 0.205, 0.235, M=M)
    end_item()


def helmet(cx, cy, z0, rz=0.0, zone='Room', group='Props'):
    """Olive helmet: dome + flared rim lip, smooth normals (organic lobe)."""
    item('helmet', z0)
    bm = new_part()
    seg, rings = 10, 3
    rx, ry, rz_ = 0.135, 0.155, 0.15
    base = 0.045
    rows = []
    for j in range(rings):
        t = j / rings * (math.pi / 2)
        rows.append([bm.verts.new((rx * math.cos(t) * math.cos(2 * math.pi * i / seg), ry * math.cos(t) * math.sin(2 * math.pi * i / seg),
                                   base + rz_ * math.sin(t))) for i in range(seg)])
    top = bm.verts.new((0, 0, base + rz_))
    for j in range(rings - 1):
        for i in range(seg):
            k = (i + 1) % seg
            bm.faces.new((rows[j][i], rows[j][k], rows[j + 1][k], rows[j + 1][i]))
    for i in range(seg):
        bm.faces.new((rows[-1][i], rows[-1][(i + 1) % seg], top))
    # rim: out and down to a lip, then back in underneath
    lip = [bm.verts.new((1.22 * rx * math.cos(2 * math.pi * i / seg), 1.20 * ry * math.sin(2 * math.pi * i / seg), 0.02)) for i in range(seg)]
    under = [bm.verts.new((1.14 * rx * math.cos(2 * math.pi * i / seg), 1.12 * ry * math.sin(2 * math.pi * i / seg), 0.0)) for i in range(seg)]
    for i in range(seg):
        k = (i + 1) % seg
        bm.faces.new((lip[i], lip[k], rows[0][k], rows[0][i]))
        bm.faces.new((under[i], under[k], lip[k], lip[i]))
    bm.faces.new(list(reversed(under)))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    emit(bm, group, zone, 'GEAR_OliveMetal', T(cx, cy, z0, rz))
    end_item()


def folded(cx, cy, z0, n=3, zone='Room', group='Props'):
    item('folded uniforms', z0)
    z = z0
    for i in range(n):
        dz = 0.075
        box(group, zone, 'GEAR_Camo', -0.18, 0.18, -0.14, 0.14, 0.0, dz, bev=(0.025, 1),
            M=T(cx + random.uniform(-0.012, 0.012), cy + random.uniform(-0.01, 0.01), z, random.uniform(-0.06, 0.06)),
            uv_off=(random.random(), random.random()))
        z += dz
    end_item()


def vest(cx, cy, z0, rz=0.0):
    """Body armour vest standing on a shelf, front local -y: plump plate, shoulder straps, pouch row."""
    item('vest', z0)
    M = T(cx, cy, z0, rz)
    emit(box_part(-0.19, 0.19, -0.06, 0.06, 0.0, 0.40), 'Props', 'Room', 'GEAR_Khaki', M, bev=(0.04, 2))
    for s in (-1, 1):
        xa, xb = sorted((s * 0.07, s * 0.165))
        box('Props', 'Room', 'GEAR_Khaki', xa, xb, -0.052, 0.052, 0.36, 0.48, bev=(0.02, 1), M=M)
    box('Props', 'Room', 'GEAR_DarkTan', -0.16, 0.16, -0.095, -0.04, 0.05, 0.18, bev=(0.02, 1), M=M)
    end_item()


def jacket(rail_x, y, z_top, yaw, uv_seed):
    """Camo jacket on a hanger, front = local -y: plump torso, sloped shoulder yoke, two sleeves from the shoulder
    points, stand-up collar, placket, two chest pockets. The graphite hook rises beside the rail (axis rail_x, z 1.80)
    and caps over it."""
    M = T(rail_x, y, z_top, yaw)
    off = (uv_seed * 0.37 % 1.0, uv_seed * 0.61 % 1.0)
    d = 0.07
    torso = [(-0.19, -d, -0.66), (0.19, -d, -0.66), (0.19, d, -0.66), (-0.19, d, -0.66),
             (-0.21, -d, -0.13), (0.21, -d, -0.13), (0.21, d, -0.13), (-0.21, d, -0.13)]
    emit(hexa_part(torso), 'Props', 'Room', 'GEAR_Camo', M, bev=(0.04, 2), uv_off=off)
    yoke = [(-0.235, -d + 0.005, -0.15), (0.235, -d + 0.005, -0.15), (0.235, d - 0.005, -0.15), (-0.235, d - 0.005, -0.15),
            (-0.10, -d + 0.01, -0.02), (0.10, -d + 0.01, -0.02), (0.10, d - 0.01, -0.02), (-0.10, d - 0.01, -0.02)]
    emit(hexa_part(yoke), 'Props', 'Room', 'GEAR_Camo', M, bev=(0.03, 1), uv_off=off)
    for s in (-1, 1):
        sl = box_part(-0.06, 0.06, -0.06, 0.06, -0.50, 0.0)
        emit(sl, 'Props', 'Room', 'GEAR_Camo', M @ T(s * 0.235, 0.0, -0.12, ry=s * math.radians(7)), bev=(0.025, 1), uv_off=off)
    box('Props', 'Room', 'GEAR_Camo', -0.10, 0.10, -0.075, 0.08, -0.04, 0.04, M=M, uv_off=off)
    box('Props', 'Room', 'GEAR_Camo', -0.025, 0.025, -0.088, -0.06, -0.64, -0.10, M=M, uv_off=off)
    for s in (-1, 1):
        xa, xb = sorted((s * 0.05, s * 0.16))
        box('Props', 'Room', 'GEAR_Camo', xa, xb, -0.094, -0.062, -0.30, -0.20, M=M, uv_off=off)
    # hanger hook (world, rail frame): vertical stem beside the rail + cap over the rail top (z 1.85)
    box('Props', 'Room', 'GEAR_Graphite', rail_x + 0.052, rail_x + 0.092, y - 0.02, y + 0.02, z_top - 0.03, 1.89)
    box('Props', 'Room', 'GEAR_Graphite', rail_x - 0.06, rail_x + 0.092, y - 0.02, y + 0.02, 1.85, 1.89)


def clothes_rail(name, x, y0, y1, jackets, yaw):
    """Free-standing rail along y: two T feet, two uprights, a round top bar (axis z 1.80), jackets fanned at `yaw`."""
    item(name, 0.0)
    for y in (y0, y1):
        box('Props', 'Room', 'GEAR_Graphite', x - 0.30, x + 0.30, y - 0.045, y + 0.045, 0.0, 0.07, bev=(0.02, 1))
        box('Props', 'Room', 'GEAR_Graphite', x - 0.05, x + 0.05, y - 0.05, y + 0.05, 0.07, 1.86, bev=(0.02, 1))
    emit(bar_part((x, y0 - 0.07, 1.80), (x, y1 + 0.07, 1.80), 0.05), 'Props', 'Room', 'GEAR_Graphite')
    end_item()
    n = len(jackets)
    for i, yy in enumerate(jackets):
        jacket(x, yy, 1.62, yaw, i * 1.7 + n)
    collider(f'COL_{name}', x - 0.33, x + 0.33, y0 - 0.08, y1 + 0.08, 0, 1.9)


def shelf(name, x0, x1, levels, y0=2.385):
    """Graphite shelf against the back wall: 0.10 m posts, boards with a 0.12 m front lip."""
    item(name, 0.0)
    for xa in (x0, x1 - 0.10):
        for ya in (y0 + 0.015, 2.82):
            box('Props', 'Room', 'GEAR_Graphite', xa, xa + 0.10, ya, ya + 0.10, 0.0, levels[-1] + 0.04, bev=(0.02, 1))
    for L in levels:
        box('Props', 'Room', 'GEAR_Graphite', x0 + 0.03, x1 - 0.03, 2.43, 2.88, L - 0.06, L)
        box('Props', 'Room', 'GEAR_Graphite', x0 + 0.03, x1 - 0.03, y0, 2.45, L - 0.10, L + 0.02, bev=(0.015, 1))
    end_item()
    collider(f'COL_{name}', x0, x1, y0, 2.92, 0, levels[-1] + 0.04)


def rifle(cx, cy, cz, kind, zone='Room'):
    """Toy-like long gun along +x (muzzle), thickness on y; generic shapes, no real model."""
    M = T(cx, cy, cz)
    g, t, o = 'GEAR_Graphite', 'GEAR_DarkTan', 'GEAR_ToyOrange'
    stock = [(-0.43, -0.032, -0.095), (-0.20, -0.032, -0.035), (-0.20, 0.032, -0.035), (-0.43, 0.032, -0.095),
             (-0.43, -0.032, 0.045), (-0.20, -0.032, 0.045), (-0.20, 0.032, 0.045), (-0.43, 0.032, 0.045)]
    emit(hexa_part(stock), 'Props', zone, t, M, bev=(0.012, 1))
    grip = [(-0.19, -0.03, -0.15), (-0.13, -0.03, -0.15), (-0.13, 0.03, -0.15), (-0.19, 0.03, -0.15),
            (-0.16, -0.03, -0.03), (-0.10, -0.03, -0.03), (-0.10, 0.03, -0.03), (-0.16, 0.03, -0.03)]
    emit(hexa_part(grip), 'Props', zone, t, M)
    if kind == 'rifle':
        box('Props', zone, g, -0.21, 0.10, -0.035, 0.035, -0.035, 0.055, bev=(0.012, 1), M=M)
        box('Props', zone, g, -0.15, 0.04, -0.026, 0.026, 0.05, 0.095, M=M)
        mag = [(0.0, -0.028, -0.20), (0.07, -0.028, -0.20), (0.07, 0.028, -0.20), (0.0, 0.028, -0.20),
               (-0.02, -0.028, -0.03), (0.05, -0.028, -0.03), (0.05, 0.028, -0.03), (-0.02, 0.028, -0.03)]
        emit(hexa_part(mag), 'Props', zone, g, M)
        box('Props', zone, t, 0.10, 0.30, -0.035, 0.035, -0.03, 0.045, bev=(0.012, 1), M=M)
        emit(bar_part((0.29, 0, 0.01), (0.40, 0, 0.01), 0.03, caps=False), 'Props', zone, g, M)
        box('Props', zone, o, 0.40, 0.43, -0.035, 0.035, -0.025, 0.045, M=M)
    else:  # pump shotgun: longer barrel, pump grip, no magazine
        box('Props', zone, g, -0.21, 0.03, -0.035, 0.035, -0.035, 0.05, bev=(0.012, 1), M=M)
        emit(bar_part((0.02, 0, 0.015), (0.42, 0, 0.015), 0.03, caps=False), 'Props', zone, g, M)
        emit(bar_part((0.08, 0, -0.035), (0.36, 0, -0.035), 0.022), 'Props', zone, g, M)
        box('Props', zone, t, 0.09, 0.27, -0.04, 0.04, -0.07, 0.0, bev=(0.012, 1), M=M)
        box('Props', zone, o, 0.42, 0.45, -0.035, 0.035, -0.02, 0.05, M=M)


def pistol(cx, cy, cz, zone='Room'):
    """Toy pistol along +x; origin = slide bottom at the peg."""
    M = T(cx, cy, cz)
    box('Props', zone, 'GEAR_Graphite', -0.12, 0.10, -0.03, 0.03, 0.0, 0.065, bev=(0.01, 1), M=M)
    grip = [(-0.155, -0.028, -0.13), (-0.085, -0.028, -0.13), (-0.085, 0.028, -0.13), (-0.155, 0.028, -0.13),
            (-0.12, -0.028, 0.0), (-0.05, -0.028, 0.0), (-0.05, 0.028, 0.0), (-0.12, 0.028, 0.0)]
    emit(hexa_part(grip), 'Props', zone, 'GEAR_DarkTan', M)
    box('Props', zone, 'GEAR_ToyOrange', 0.10, 0.125, -0.032, 0.032, 0.0, 0.065, M=M)


def peg(x, z_top, hook=True):
    """Graphite peg out of the gun board (board face y 2.80), top at z_top, upturned tip."""
    box('Props', 'Room', 'GEAR_Graphite', x - 0.03, x + 0.03, 2.58, 2.82, z_top - 0.05, z_top)
    if hook:
        box('Props', 'Room', 'GEAR_Graphite', x - 0.03, x + 0.03, 2.58, 2.635, z_top, z_top + 0.07)


def cage_leaf(hinge_x, hinge_y, direction, open_angle):
    """Gun-cage leaf 1.5 x 1.8 m: 0.10 m frame, mid rail, 0.06 m octagonal bars; hinge stile at local x 0, leaf along
    local +x (direction +1) or -x (-1); open_angle rotates about the hinge (radians, + = counter-clockwise from above)."""
    W, z0, z1, zm = 1.5, 0.74, 2.54, 1.42
    M = T(hinge_x, hinge_y, 0.0, open_angle)
    xs = lambda a, b: sorted((direction * a, direction * b))  # noqa: E731
    g = 'GEAR_Graphite'
    box('Props', 'Room', g, *xs(0.0, 0.10), -0.03, 0.03, z0, z1, bev=(0.015, 1), M=M)
    box('Props', 'Room', g, *xs(W - 0.10, W), -0.03, 0.03, z0, z1, bev=(0.015, 1), M=M)
    for za, zb in ((z0, z0 + 0.10), (zm, zm + 0.10), (z1 - 0.10, z1)):
        box('Props', 'Room', g, *xs(0.08, W - 0.08), -0.03, 0.03, za, zb, bev=(0.015, 1), M=M)
    n = 5
    for i in range(1, n + 1):
        x = direction * (0.10 + (W - 0.20) * i / (n + 1))
        emit(bar_part((x, 0, z0 + 0.09), (x, 0, zm + 0.01), 0.03, caps=False), 'Props', 'Room', g, M)
        emit(bar_part((x, 0, zm + 0.09), (x, 0, z1 - 0.09), 0.03, caps=False), 'Props', 'Room', g, M)
    for z in (z0 + 0.25, z1 - 0.35):
        emit(cyl_part(0.035, z, z + 0.16, 8), 'Props', 'Room', g, M @ T(direction * -0.035, 0.035, 0.0))


def gun_wall():
    """Hero object on the back wall, facing the window: base cabinet with drawers, light-wood board with rifles,
    shotguns and pistols on pegs, ledge with ammo cans, header with a warm strip, two caged leaves (right one open)."""
    item('gun wall', 0.0)
    g = 'GEAR_Graphite'
    box('Props', 'Room', g, -0.98, 1.98, 2.42, 2.93, 0.0, 0.10)
    box('Props', 'Room', g, -1.01, 2.01, 2.36, 2.93, 0.10, 0.70, bev=(0.03, 2))
    for i in range(3):
        xa = -0.95 + i * 0.99
        box('Props', 'Room', 'GEAR_Khaki', xa, xa + 0.92, 2.325, 2.37, 0.17, 0.63, bev=(0.015, 1))
        hx = xa + 0.46
        for x in (hx - 0.10, hx + 0.10):
            box('Props', 'Room', g, x - 0.02, x + 0.02, 2.29, 2.33, 0.50, 0.54)
        box('Props', 'Room', g, hx - 0.13, hx + 0.13, 2.265, 2.30, 0.495, 0.545, bev=(0.01, 1))
    for xa, xb in ((-1.12, -1.0), (2.0, 2.12)):
        box('Props', 'Room', g, xa, xb, 2.30, 2.93, 0.0, 2.72, bev=(0.025, 1))
    box('Props', 'Room', g, -1.14, 2.14, 2.22, 2.93, 2.58, 2.76, bev=(0.03, 2))
    box('Props', 'Room', 'GEAR_LampWarm', -0.80, 1.80, 2.36, 2.48, 2.545, 2.585)
    # board: horizontal light-wood planks (grooves on the 0.15 m texture rows)
    emit(groove_part(1, 2.80, -1, 2, 0.70, 2.585, -1.0, 2.0, PLANK), 'Props', 'Room', 'GEAR_LightWood', uv_axis=1)
    # ledge + ammo cans
    box('Props', 'Room', g, -0.97, 1.97, 2.60, 2.82, 0.84, 0.92, bev=(0.015, 1))
    box('Props', 'Room', g, -0.97, 1.97, 2.585, 2.625, 0.80, 0.95, bev=(0.012, 1))
    end_item()
    for x in (-0.62, -0.05, 0.95, 1.60):
        ammo_can(x, 2.71, 0.92)
    # long guns: row A (shotguns, z 2.18) and row B (rifles, z 1.70); pegs under handguard and stock
    for row_z, kind in ((2.18, 'shotgun'), (1.70, 'rifle')):
        for cx in (-0.47, 0.50, 1.47):
            rifle(cx, 2.70, row_z, kind)
            peg(cx + 0.20, row_z - (0.07 if kind == 'shotgun' else 0.03))
            peg(cx - 0.32, row_z - 0.066)
    for cx in (-0.72, -0.24, 0.24, 0.76, 1.24, 1.72):
        pistol(cx, 2.70, 1.22)
        peg(cx + 0.03, 1.22, hook=False)
    # cage: left leaf closed (hinge x -1.0), right leaf open 90 degrees into the room (hinge x 2.0)
    cage_leaf(-1.0, 2.23, +1, 0.0)
    cage_leaf(2.0, 2.23, -1, math.radians(90))
    # padlock hanging open on the closed leaf's free stile
    box('Props', 'Room', g, 0.38, 0.52, 2.17, 2.20, 1.40, 1.56, bev=(0.01, 1))
    box('Props', 'Room', 'GEAR_OliveMetal', 0.385, 0.515, 2.095, 2.17, 1.27, 1.40, bev=(0.015, 1))
    for x in (0.40, 0.465):
        box('Props', 'Room', g, x, x + 0.035, 2.115, 2.15, 1.40, 1.50)
    box('Props', 'Room', g, 0.40, 0.50, 2.115, 2.15, 1.50, 1.535)
    collider('COL_gun_wall', -1.14, 2.14, 2.20, 2.93, 0, 2.76)
    collider('COL_gun_cage_open_leaf', 1.93, 2.07, 0.70, 2.25, 0, 2.56)


def lockers():
    """Bank of 5 olive lockers on the back wall right: carcass, crown, plinth, 6 cm doors with louvres and bar handles."""
    item('lockers', 0.0)
    x0, x1 = 2.55, 5.30
    box('Props', 'Room', 'GEAR_Graphite', x0 + 0.04, x1 - 0.04, 2.44, 2.93, 0.0, 0.10)
    box('Props', 'Room', 'GEAR_OliveMetal', x0, x1, 2.38, 2.93, 0.10, 1.98, bev=(0.03, 2))
    box('Props', 'Room', 'GEAR_Graphite', x0 - 0.03, x1 + 0.03, 2.35, 2.93, 1.98, 2.06, bev=(0.02, 1))
    dw = (x1 - x0 - 6 * 0.05) / 5
    for i in range(5):
        a = x0 + 0.05 + i * (dw + 0.05)
        b = a + dw
        box('Props', 'Room', 'GEAR_OliveMetal', a, b, 2.32, 2.385, 0.16, 1.92, bev=(0.02, 1))
        cx = (a + b) / 2
        for z in (1.64, 1.72, 1.80, 0.30, 0.38):
            box('Props', 'Room', 'GEAR_OliveMetal', cx - 0.15, cx + 0.15, 2.295, 2.325, z - 0.025, z + 0.025, faces={'-y', '+z', '-z', '+x', '-x'})
        hx = b - 0.08
        for z in (0.98, 1.20):
            box('Props', 'Room', 'GEAR_Graphite', hx - 0.02, hx + 0.02, 2.285, 2.325, z - 0.02, z + 0.02)
        box('Props', 'Room', 'GEAR_Graphite', hx - 0.022, hx + 0.022, 2.245, 2.29, 0.95, 1.23)
    end_item()
    collider('COL_lockers', x0 - 0.03, x1 + 0.03, 2.24, 2.93, 0, 2.06)


def counter():
    """Window counter: plank top through the window, khaki-panelled bodies outside (hall) and inside (clerk side),
    graphite bar grille with a pass slot, NO REFUNDS plate, hazard guards on the outer corners."""
    x0, x1 = -1.25, 2.25
    item('counter top', 0.0)
    # top: 9 light-wood planks along x, 0.15 m wide on the texture rows (y = k * 0.15), 0.10 m thick
    ys = [-3.60 + i * PLANK for i in range(10)]
    for ya, yb in zip(ys, ys[1:]):
        zone = 'Hall' if yb <= -3.1 + 1e-6 else ('Room' if ya >= -2.9 - 1e-6 else 'Both')
        box('Props', zone, 'GEAR_LightWood', x0, x1, ya, yb, 0.95, 1.05, bev=(0.012, 1))
    # outside body (hall): plinth, graphite body, three khaki panels, hazard corner guards
    box('Props', 'Hall', 'GEAR_Graphite', -1.15, 2.15, -3.45, -3.06, 0.0, 0.10)
    box('Props', 'Hall', 'GEAR_Graphite', -1.20, 2.20, -3.50, -3.06, 0.10, 0.95, bev=(0.03, 2))
    pw = (3.24 - 2 * 0.06) / 3
    for i in range(3):
        a = -1.12 + i * (pw + 0.06)
        box('Props', 'Hall', 'GEAR_DarkTan', a, a + pw, -3.535, -3.49, 0.20, 0.86, bev=(0.015, 1))
    for xa, xb in ((-1.27, -1.13), (2.13, 2.27)):
        box('Props', 'Hall', 'GEAR_Hazard', xa, xb, -3.57, -3.43, 0.0, 0.94, bev=(0.02, 1))
    # inside cabinet (clerk side faces +y): plinth, body, three khaki doors with bar handles
    box('Props', 'Room', 'GEAR_Graphite', -1.15, 2.15, -2.93, -2.36, 0.0, 0.10)
    box('Props', 'Room', 'GEAR_Graphite', -1.20, 2.20, -2.93, -2.30, 0.10, 0.95, bev=(0.03, 2))
    for i in range(3):
        a = -1.12 + i * (pw + 0.06)
        box('Props', 'Room', 'GEAR_Khaki', a, a + pw, -2.31, -2.265, 0.20, 0.86, bev=(0.015, 1))
        hx = a + pw / 2
        for x in (hx - 0.10, hx + 0.10):
            box('Props', 'Room', 'GEAR_Graphite', x - 0.02, x + 0.02, -2.275, -2.235, 0.74, 0.78)
        box('Props', 'Room', 'GEAR_Graphite', hx - 0.13, hx + 0.13, -2.24, -2.205, 0.735, 0.785, bev=(0.01, 1))
    end_item()
    # grille in the window: bottom rail (pass slot 1.05..1.27 under it), 11 bars up into the head casing
    box('Shell', 'Both', 'GEAR_Graphite', WIN[0] + 0.02, WIN[1] - 0.02, -3.03, -2.97, 1.27, 1.37, bev=(0.015, 1))
    for i in range(11):
        x = -0.75 + i * 0.25
        emit(bar_part((x, -3.0, 1.36), (x, -3.0, 2.16), 0.03, caps=False), 'Shell', 'Both', 'GEAR_Graphite')
    collider('COL_window_grille', WIN[0], WIN[1], -3.05, -2.95, 1.05, 2.2)
    # NO REFUNDS plate wired on the bars (hall side)
    box('Shell', 'Both', 'GEAR_Graphite', 0.02, 0.98, -3.08, -3.03, 1.86, 2.10, bev=(0.012, 1))
    txt = bpy.data.curves.new('NoRefunds', 'FONT')
    txt.body = 'NO REFUNDS'
    txt.size = 0.15
    txt.extrude = 0.008
    txt.resolution_u = 2
    txt.align_x = 'CENTER'
    txt.align_y = 'CENTER'
    to = bpy.data.objects.new('NoRefunds', txt)
    scene.collection.objects.link(to)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(to.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = new_part()
    bm.from_mesh(me)
    bpy.data.objects.remove(to)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.9], context='FACES')
    emit(bm, 'Shell', 'Both', 'GEAR_OffWhite', T(0.50, -3.088, 1.98, rx=math.radians(90)), uv_axis=1)
    # on the counter: a cash box inside, a helmet outside for trying on, folded uniforms inside
    item('cash box', 1.05)
    box('Props', 'Room', 'GEAR_Graphite', 1.40, 1.76, -2.72, -2.46, 1.05, 1.19, bev=(0.02, 1))
    box('Props', 'Room', 'GEAR_Khaki', 1.44, 1.72, -2.70, -2.48, 1.185, 1.215, bev=(0.008, 1))
    end_item()
    helmet(-0.55, -3.36, 1.05, 0.4, zone='Hall')
    folded(0.30, -2.58, 1.05, 2)
    collider('COL_counter_out', -1.27, 2.27, -3.60, -3.08, 0, 1.05)
    collider('COL_counter_in', -1.25, 2.25, -2.93, -2.20, 0, 1.05)


def stool(cx, cy):
    item('stool', 0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = [(sx * 0.17 - 0.03, sy * 0.17 - 0.03, 0.0), (sx * 0.17 + 0.03, sy * 0.17 - 0.03, 0.0),
                 (sx * 0.17 + 0.03, sy * 0.17 + 0.03, 0.0), (sx * 0.17 - 0.03, sy * 0.17 + 0.03, 0.0),
                 (sx * 0.12 - 0.03, sy * 0.12 - 0.03, 0.60), (sx * 0.12 + 0.03, sy * 0.12 - 0.03, 0.60),
                 (sx * 0.12 + 0.03, sy * 0.12 + 0.03, 0.60), (sx * 0.12 - 0.03, sy * 0.12 + 0.03, 0.60)]
            emit(hexa_part(c), 'Props', 'Room', 'GEAR_Graphite', T(cx, cy, 0))
    for s in (-1, 1):
        box('Props', 'Room', 'GEAR_Graphite', -0.16, 0.16, s * 0.155 - 0.022, s * 0.155 + 0.022, 0.22, 0.26, M=T(cx, cy, 0))
        box('Props', 'Room', 'GEAR_Graphite', s * 0.155 - 0.022, s * 0.155 + 0.022, -0.16, 0.16, 0.20, 0.24, M=T(cx, cy, 0))
    emit(cyl_part(0.17, 0.58, 0.62, 12), 'Props', 'Room', 'GEAR_Graphite', T(cx, cy, 0))
    emit(cyl_part(0.21, 0.62, 0.70, 12), 'Props', 'Room', 'GEAR_DarkTan', T(cx, cy, 0), bev=(0.02, 1))
    end_item()
    collider('COL_stool', cx - 0.22, cx + 0.22, cy - 0.22, cy + 0.22, 0, 0.70)


def sandbag(cx, cy, z0, rz=0.0, ry=0.0, L=0.56, W=0.30, Hh=0.16, zone='Room'):
    """Pillow-shaped bag (superellipsoid of a subdivided box, flattened underside), smooth normals; lowest point at z0."""
    bm = new_part()
    nx, ny, nz = 4, 2, 2
    grid = {}

    def vert(i, j, k):
        key = (i, j, k)
        if key not in grid:
            p = Vector((-1 + 2 * i / nx, -1 + 2 * j / ny, -1 + 2 * k / nz))
            n4 = (p.x ** 4 + p.y ** 4 + p.z ** 4) ** 0.25
            q = p / n4
            grid[key] = bm.verts.new((q.x * L / 2, q.y * W / 2, max(q.z, -0.75) * Hh / 2))
        return grid[key]

    for i in range(nx):
        for j in range(ny):
            bm.faces.new([vert(i, j, 0), vert(i, j + 1, 0), vert(i + 1, j + 1, 0), vert(i + 1, j, 0)])
            bm.faces.new([vert(i, j, nz), vert(i + 1, j, nz), vert(i + 1, j + 1, nz), vert(i, j + 1, nz)])
    for i in range(nx):
        for k in range(nz):
            bm.faces.new([vert(i, 0, k), vert(i + 1, 0, k), vert(i + 1, 0, k + 1), vert(i, 0, k + 1)])
            bm.faces.new([vert(i, ny, k), vert(i, ny, k + 1), vert(i + 1, ny, k + 1), vert(i + 1, ny, k)])
    for j in range(ny):
        for k in range(nz):
            bm.faces.new([vert(0, j, k), vert(0, j, k + 1), vert(0, j + 1, k + 1), vert(0, j + 1, k)])
            bm.faces.new([vert(nx, j, k), vert(nx, j + 1, k), vert(nx, j + 1, k + 1), vert(nx, j, k + 1)])
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if ry:
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(ry, 4, 'Y'), verts=bm.verts)
    zmin = min(v.co.z for v in bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, -zmin), verts=bm.verts)
    emit(bm, 'Props', zone, 'GEAR_DarkTan', T(cx, cy, z0, rz), uv_off=(random.random(), random.random()))


def sandbags():
    item('sandbags', 0.0)
    sandbag(-3.17, -2.70, 0.0, 0.03)
    sandbag(-2.60, -2.71, 0.0, -0.04)
    end_item()
    # the top bag lies across the two lower ones; it rests on their crowns (checked in the renders)
    sandbag(-2.88, -2.69, 0.125, 0.06)
    item('sandbag leaning', 0.0)
    sandbag(-2.85, -2.27, 0.0, 1.45, L=0.52)
    end_item()
    collider('COL_sandbags', -3.47, -2.30, -2.88, -1.98, 0, 0.30)
    # outside: a low barricade against the facade right of the counter (2 rows)
    item('sandbag barricade', 0.0)
    for i, x in enumerate((2.97, 3.55, 4.13)):
        sandbag(x, -3.36, 0.0, (-0.03, 0.04, -0.02)[i], zone='Hall')
    end_item()
    for i, x in enumerate((3.26, 3.84)):
        sandbag(x, -3.35, 0.125, (0.05, -0.04)[i], zone='Hall')
    collider('COL_sandbag_barricade', 2.66, 4.44, -3.54, -3.10, 0, 0.30)


def door_leaf():
    """Khaki door leaf standing open 90 degrees into the room beside the hinge jamb: plump slab, kick plates, levers."""
    hx, hy = DOOR[0] + 0.05 + 0.035, -2.85
    M = T(hx, hy, 0.0, math.radians(90))
    item('door leaf', 0.01)
    box('Props', 'Room', 'GEAR_Khaki', 0.0, 1.18, -0.03, 0.03, 0.01, 2.28, bev=(0.025, 2), M=M)
    for s in (-1, 1):
        ya, yb = sorted((s * 0.026, s * 0.042))
        box('Props', 'Room', 'GEAR_Graphite', 0.06, 1.12, ya, yb, 0.06, 0.30, bev=(0.006, 1), M=M)
        ya, yb = sorted((s * 0.028, s * 0.065))
        box('Props', 'Room', 'GEAR_Graphite', 1.02, 1.10, ya, yb, 0.98, 1.10, bev=(0.01, 1), M=M)
        ya, yb = sorted((s * 0.065, s * 0.10))
        box('Props', 'Room', 'GEAR_Graphite', 0.86, 1.10, ya, yb, 1.02, 1.06, bev=(0.008, 1), M=M)
    for z in (0.35, 1.95):
        emit(cyl_part(0.03, z, z + 0.16, 8), 'Props', 'Room', 'GEAR_Graphite', M @ T(-0.03, 0.0, 0.0))
    end_item()
    collider('COL_door_leaf', hx - 0.11, hx + 0.11, hy, hy + 1.20, 0, 2.30)


def pallet(x0, y0):
    """Light-wood pallet 1.2 x 1.05: 4 top planks on the texture rows, 3 stringers, 3 bottom boards (local origin = corner)."""
    item('pallet', 0.0)
    M = T(x0, y0, 0.0)
    for k in (0, 2, 4, 6):
        box('Props', 'Room', 'GEAR_LightWood', 0.0, 1.2, k * PLANK + 0.005, k * PLANK + 0.145, 0.105, 0.145, bev=(0.01, 1), M=M)
    for x in (0.0, 0.55, 1.10):
        box('Props', 'Room', 'GEAR_LightWood', x + 0.005, x + 0.095, 0.005, 1.045, 0.025, 0.105, M=M)
    for k in (0, 3, 6):
        box('Props', 'Room', 'GEAR_LightWood', 0.0, 1.2, k * PLANK + 0.005, k * PLANK + 0.145, 0.0, 0.025, M=M)
    end_item()


def floor():
    box('Floor', 'Room', 'GEAR_Floor_Concrete', -XO, XO, -YO, YO, -0.05, 0.0, faces={'+z'})


# ------------------------------------------------------------------ build the room
cat('walls + facade')
walls()
cat('ceiling + lamps')
ceiling()
cat('counter + grille + sign')
counter()
cat('gun wall + guns + cage')
gun_wall()
cat('lockers')
lockers()
cat('shelves + helmets + vests + folded + shelf crates')
shelf('shelf_helmets', -5.25, -3.45, [0.12, 0.62, 1.12, 1.62, 2.06])
shelf('shelf_vests', -3.25, -1.45, [0.12, 0.66, 1.30, 2.04])
for L in (1.12, 1.62):
    for x in (-4.92, -4.35, -3.78):
        helmet(x, 2.64, L, random.uniform(-0.35, 0.35))
for x in (-4.85, -4.35, -3.85):
    folded(x, 2.65, 0.62)
for x in (-4.75, -3.95):
    folded(x, 2.65, 2.06, 2)
crate('crate_shelfA_1', -4.78, 2.66, 0.12, 0.62, 0.38, 0.28, corners=False, handles=False)
crate('crate_shelfA_2', -3.93, 2.66, 0.12, 0.62, 0.38, 0.28, rz=math.radians(4), corners=False, handles=False)
for L in (0.66, 1.30):
    for x in (-2.80, -1.92):
        vest(x, 2.66, L, random.uniform(-0.12, 0.12))
for x in (-2.75, -1.95):
    helmet(x, 2.64, 2.04, random.uniform(-0.4, 0.4))
crate('crate_shelfB', -2.35, 2.66, 0.12, 0.84, 0.42, 0.34, handles=False)
cat('clothes rails + jackets')
clothes_rail('rail_wall', -4.95, -1.25, 1.65, [-0.85 + i * 0.42 for i in range(6)], math.radians(55))
clothes_rail('rail_free', -3.15, -0.90, 1.50, [-0.45 + i * 0.42 for i in range(4)], math.radians(-55))
cat('pallet + crates')
pallet(4.05, -2.85)
crate('crate_pallet_big', 4.65, -2.30, 0.145, 0.95, 0.50, 0.45, rz=math.pi)
crate('crate_pallet_top', 4.62, -2.30, 0.145 + 0.45, 0.78, 0.44, 0.38, rz=math.pi + math.radians(5))
crate('crate_floor', 3.50, -2.55, 0.0, 0.62, 0.40, 0.30, rz=math.pi + math.radians(-6))
collider('COL_pallet_stack', 4.0, 5.3, -2.90, -1.75, 0, 0.99)
collider('COL_crate_floor', 3.15, 3.85, -2.80, -2.30, 0, 0.30)
cat('stool')
stool(0.95, -1.80)
cat('sandbags')
sandbags()
cat('door leaf')
door_leaf()
cat('floor (standalone)')
floor()

# ------------------------------------------------------------------ objects, normals, colliders
objs = []
for k, a in ACC.items():
    me = bpy.data.meshes.new(k)
    a.bm.normal_update()
    for e in a.bm.edges:
        if e.is_manifold and e.calc_face_angle(0.0) > math.radians(75):
            e.smooth = False
    a.bm.to_mesh(me)
    a.bm.free()
    for m in a.mats:
        me.materials.append(MATS[m])
    ob = bpy.data.objects.new(k, me)
    col.objects.link(ob)
    wn = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    wn.mode = 'FACE_AREA'
    wn.weight = 50
    wn.keep_sharp = True
    objs.append(ob)

col_objs = []
for name, (x0, x1, y0, y1, z0, z1) in COLLIDERS:
    bm = box_part(x0, x1, y0, y1, z0, z1)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col_cols.objects.link(ob)
    ob.hide_render = True
    ob.display_type = 'WIRE'
    col_objs.append(ob)

# ------------------------------------------------------------------ report
dg = bpy.context.evaluated_depsgraph_get()
report = {'name': f'{NAME}_{REV}', 'axes': 'Blender Z up, hall side -Y; Unity (x,y,z) = (-bx, bz, -by)',
          'objects': {}, 'colliders': [n for n, _ in COLLIDERS]}
total = 0
for ob in objs:
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    report['objects'][ob.name] = {'triangles': tris, 'materials': [m.name for m in ob.data.materials],
                                  'bounds_min': [round(min(v[i] for v in bb), 3) for i in range(3)],
                                  'bounds_max': [round(max(v[i] for v in bb), 3) for i in range(3)]}
    ev.to_mesh_clear()
    total += tris
report['total_triangles'] = total
report['triangles_by_category_before_export'] = TRIS
report['total_triangles_without_standalone_floor'] = total - report['objects'].get('GEAR_Floor_Room', {}).get('triangles', 0)
bad = [{'item': n, 'support': s, 'lowest': round(z, 4)} for n, s, z in ITEMS if s is not None and abs(z - s) > 0.002]
report['resting_check'] = {'items': len(ITEMS), 'off_support': bad}
allbb = [ob.matrix_world @ Vector(c) for ob in objs for c in ob.bound_box]
report['overall_size_m'] = [round(max(v[i] for v in allbb) - min(v[i] for v in allbb), 3) for i in range(3)]
report['unity_lights'] = [{'name': f'Lamp {n}', 'unity_pos': [-x, 3.50, 0.0], 'color_srgb': [1.0, 0.706, 0.42]}
                          for n, x in (('L', -2.75), ('R', 2.75))]

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.object.select_all(action='DESELECT')
for o in objs + col_objs:
    o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'MESH'},
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=True,
                         mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, use_tspace=False)
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
mats_path.write_text(json.dumps({'materials': MATINFO}, indent=2), encoding='utf-8')
print('[GEAR] triangles', total, 'size', report['overall_size_m'])
for k, v in report['objects'].items():
    print('[GEAR]', k, v['triangles'])
print('[GEAR] by category', json.dumps(TRIS))
print('[GEAR] resting check', json.dumps(report['resting_check']))

if args.no_render:
    sys.exit(0)

# ------------------------------------------------------------------ review renders (warm 3000 K light, not exported)
preview_dir.mkdir(parents=True, exist_ok=True)
studio = bpy.data.collections.new('Studio_NotExported')
scene.collection.children.link(studio)
world = bpy.data.worlds.new('HangarDark')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (s2l(0.30), s2l(0.28), s2l(0.25), 1.0)
bg.inputs[1].default_value = 0.12
WARM = (1.0, s2l(0.706), s2l(0.42))
HALL = (1.0, s2l(0.78), s2l(0.52))


def light(name, kind, loc, power, size=0.2, size_y=None, target=None, color=WARM):
    d = bpy.data.lights.new(name, kind)
    d.energy = power
    d.color = color
    if kind == 'AREA':
        d.shape = 'RECTANGLE'
        d.size = size
        d.size_y = size_y or size
    else:
        d.shadow_soft_size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    if target is not None:
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    studio.objects.link(o)
    return o


# the two room lamps (Unity: point lights at the same places) + the gun wall strip + dim warm hall lamps
for x in (-2.75, 2.75):
    light(f'Room {x}', 'AREA', (x, 0.0, 3.59), 150, 0.18, 1.4, target=(x, 0.0, 0.0))
    light(f'RoomFill {x}', 'POINT', (x, 0.0, 3.3), 45, 0.3)
light('GunStrip', 'AREA', (0.5, 2.42, 2.54), 45, 2.6, 0.12, target=(0.5, 2.42, 0.0))
light('HallPendantA', 'AREA', (-3.0, -8.0, 7.0), 450, 1.0, target=(-3.0, -8.0, 0.0), color=HALL)
light('HallPendantB', 'AREA', (4.0, -8.0, 7.0), 450, 1.0, target=(4.0, -8.0, 0.0), color=HALL)
light('HallBounce', 'AREA', (0.5, -9.0, 3.0), 160, 8.0, 3.0, target=(0.5, 0.0, 1.5), color=HALL)

hf_bm = new_part()
box_part(-30, 30, -30, 30, -0.05, -0.003, faces={'+z'}, bm=hf_bm)
uv_box(hf_bm)
hall_me = bpy.data.meshes.new('REVIEW_HallFloor')
hf_bm.to_mesh(hall_me)
hf_bm.free()
hall_me.materials.append(MATS['GEAR_Floor_Concrete'])
studio.objects.link(bpy.data.objects.new('REVIEW_HallFloor', hall_me))

# 1.80 m scale figure in the hall (renders only)
mat_fig = bpy.data.materials.new('REVIEW_Figure')
try:
    mat_fig.use_nodes = True
    next(n for n in mat_fig.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (s2l(.84), s2l(.47), s2l(.24), 1)
except Exception:
    pass
fig_bm = cyl_part(0.17, 0.0, 1.56, 12)
fig_me = bpy.data.meshes.new('REVIEW_Figure')
fig_bm.to_mesh(fig_me)
fig_bm.free()
fig_me.materials.append(mat_fig)
figure = bpy.data.objects.new('REVIEW_Figure_1m80', fig_me)
figure.location = (1.3, -4.25, 0.0)
studio.objects.link(figure)
hd_bm = bmesh.new()
bmesh.ops.create_uvsphere(hd_bm, u_segments=16, v_segments=8, radius=0.12)
hd_me = bpy.data.meshes.new('REVIEW_Head')
hd_bm.to_mesh(hd_me)
hd_bm.free()
hd_me.materials.append(mat_fig)
head = bpy.data.objects.new('REVIEW_Head', hd_me)
head.location = (1.3, -4.25, 1.68)
studio.objects.link(head)

scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
try:
    scene.cycles.use_denoising = True
except Exception:
    pass
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            prefs.compute_device_type = dev
            prefs.get_devices()
            if any(d.type == dev for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = 'GPU'
                print('[GEAR] render device', dev)
                break
        except Exception:
            continue
except Exception:
    pass
scene.render.resolution_x = args.res
scene.render.resolution_y = int(args.res * 0.75)
for vt in ('AgX', 'Khronos PBR Neutral', 'Standard'):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue
scene.view_settings.exposure = 0.0
cd = bpy.data.cameras.new('Cam')
cam = bpy.data.objects.new('Cam', cd)
studio.objects.link(cam)
scene.camera = cam
ceiling_objs = [o for o in objs if o.name.startswith('GEAR_Ceiling')]


def render(fname, loc, target, lens=24, ortho=None, no_ceiling=False, figure_on=False):
    for o in ceiling_objs:
        o.hide_render = no_ceiling
    figure.hide_render = head.hide_render = not figure_on
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    else:
        cd.type = 'PERSP'
        cd.lens = lens
    cd.clip_start = 0.05
    scene.render.filepath = str(preview_dir / fname)
    bpy.ops.render.render(write_still=True)
    print('[GEAR] rendered', fname)


render('01_door_view_1m7.png', (-4.30, -2.75, 1.70), (0.6, 1.4, 1.0), lens=17)
render('02_hall_view_1m7.png', (-0.6, -10.5, 1.70), (-0.6, 0.0, 1.75), lens=20, figure_on=True)
render('03_overview34_no_ceiling.png', (-6.8, -8.2, 10.5), (0.0, 0.6, 0.3), lens=22, no_ceiling=True, figure_on=True)
render('04_top_no_ceiling.png', (0.0, -0.2, 25.0), (0.0, -0.2, 0.0), ortho=12.6, no_ceiling=True)
render('05_gun_wall.png', (0.5, -0.45, 1.65), (0.5, 2.9, 1.55), lens=22)
render('06_locker.png', (3.15, 0.95, 1.50), (4.05, 2.55, 1.05), lens=26)
render('07_crate.png', (2.70, -0.55, 1.45), (4.45, -2.25, 0.45), lens=28)
render('08_uniforms.png', (-3.55, -1.55, 1.65), (-4.85, 0.35, 1.20), lens=22)
render('09_clerk_view.png', (0.55, -1.10, 1.55), (0.35, -3.6, 1.15), lens=20)
render('10_facade_close.png', (3.9, -6.2, 1.55), (1.7, -3.2, 1.15), lens=26)
render('11_sandbags_door.png', (-2.0, -0.7, 1.45), (-3.7, -2.6, 0.35), lens=24)
print('[GEAR] previews in', preview_dir)
