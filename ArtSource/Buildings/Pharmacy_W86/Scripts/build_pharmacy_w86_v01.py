"""Pharmacy_W86 v01 - city pharmacy ground-floor unit insert (exterior C, sales floor B, stockroom A), game-ready low poly.

Run headless (after make_labels_v01.py):
  blender -b --factory-startup -noaudio --python build_pharmacy_w86_v01.py -- [--width 11.5 --depth 12.7 --height 3.4
          --rear-door-x 0.7] [--rev v01] [--force]
Outputs (ArtSource/Buildings/Pharmacy_W86/):
  Pharmacy_W86_unit_<rev>.fbx    shell insert + ceiling + fixed interior (LOD0/LOD1), UCX_ colliders (door openings open),
                                 Door_Staff / Door_Street / Door_Rear (pivot = hinge, closed, own UCX), ANCHOR_ empties
  Pharmacy_W86_props_<rev>.fbx   every prop a separate object (LOD0/LOD1 when > 500 tris, UCX_ for large ones)
  Pharmacy_W86_anchors_<rev>.json, Pharmacy_W86_materials_<rev>.json, Pharmacy_W86_report_<rev>.json, Pharmacy_W86_<rev>.blend
Blender: Z up, street = -Y, pivot = floor level at the street-front centre.  Unity local: (x, y, z) = (-bx, bz, -by).
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ph_lib_v01 as LIB  # noqa: E402
from ph_lib_v01 import MB, Wall, pieces, whexa, T, RZ, RX, RY  # noqa: E402
import ph_layout_v01 as P  # noqa: E402

ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.abspath(P.OUTDIR) if P.OUTDIR else ASSET_DIR
ART = 'C:/Dev/Game/Assets/OnlyVolunteers/Art/'
ECON = 'C:/Dev/Game/Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json'
REV = P.REV
EPS = 1e-6
with open(os.path.join(ASSET_DIR, 'Pharmacy_labels_v01_regions.json'), encoding='utf-8') as _f:
    ATLAS = json.load(_f)
RG = ATLAS['regions']

# ============================================================================ materials
MATS = {
    'MAT_PH_tile_floor': dict(tex='MapTextures_W86/T1/Textures/T1_tile_facade_albedo.png', nrm='MapTextures_W86/T1/Textures/T1_tile_facade_normal.png',
                              tile=6.0, tint='#E8DAC0', smooth=0.25, metal=0.0,
                              note='Sales floor + stockroom floor. 10x10 tiles per texture -> 0.6 m tiles at tile 6 m. UVs are offset so grout lines start at the inner wall faces.'),
    'MAT_PH_wall_turquoise': dict(tex='TextureTest_v01/Source_v03/TT_acg_Plaster001_neutral_albedo.png', nrm='TextureTest_v01/Source_v03/TT_acg_Plaster001_normal.png',
                                  tile=2.0, tint='#66A9AA', smooth=0.22, metal=0.0,
                                  note='Reference B faded turquoise: sales-floor dado, skirting, dado rail, cornice band, shelving frames, counter bases, cash desk, staff door (sales face).'),
    'MAT_PH_wall_cream': dict(tex='TextureTest_v01/Source_v03/TT_acg_Plaster001_neutral_albedo.png', nrm='TextureTest_v01/Source_v03/TT_acg_Plaster001_normal.png',
                              tile=2.0, tint='#FFF6CC', smooth=0.12, metal=0.0, note='Reference B warm cream: sales-floor upper walls.'),
    'MAT_PH_facade_greyblue': dict(tex='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_albedo.png',
                                   nrm='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_normal.png', tile=2.0, tint='#A5BBD3',
                                   smooth=0.38, metal=0.2,
                                   note='Reference C muted grey-blue: storefront frames, risers with inset panels, fascia, pier, plinths, rear plinth.'),
    'MAT_PH_offwhite': dict(tex='MapTextures_W86/T1/Textures/T1_plaster_whitewash_albedo.png', nrm='MapTextures_W86/T1/Textures/T1_plaster_whitewash_normal.png',
                            tile=3.0, tint='#E8E8E4', smooth=0.12, metal=0.0,
                            note='Reference C/A dirty off-white: pilasters, cornice, sills, reveals, ceilings, stockroom upper walls, shelf boards, counter tops, rear facade.'),
    'MAT_PH_green': dict(tex='MapTextures_W86/T1/Textures/T1_painted_metal_albedo.png', nrm=None, tile=1.0, tint='#5FA076', smooth=0.35, metal=0.1,
                         note='Reference A muted green: stockroom dado + skirting, steel shelving, rear door + frame, staff door (stock face), chair seat, cross-sign body.'),
    'MAT_PH_glass': dict(tex=None, nrm=None, tile=1.0, tint='#A9C6CA', smooth=0.9, metal=0.0, alpha=0.28,
                         note='Shop windows, door glazing, counter vitrine, fridge door. Panes are two single-sided quads 4 mm apart. URP Lit Transparent alpha ~0.28 (opaque acceptable).'),
    'MAT_PH_metal': dict(tex='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_albedo.png',
                         nrm='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_normal.png', tile=2.0, tint='#FFFFFF', smooth=0.45, metal=0.6,
                         note='Brushed / galvanised steel: handles, thresholds, posts, brackets, pipes, tap, lamp end caps, canopy, ceiling T-bars, bars.'),
    'MAT_PH_wood': dict(tex='StyleKit_v3/Textures/5a_wood_planks_fences/5a_wood_planks_fences_v07_albedo.png',
                        nrm='StyleKit_v3/Textures/5a_wood_planks_fences/5a_wood_planks_fences_v07_normal.png', tile=2.0, tint='#FFFFFF', smooth=0.15, metal=0.0,
                        note='Mop / broom handles, pallet slats.'),
    'MAT_PH_cardboard': dict(tex='TextureTest_v01/Source_v03/TT_acg_Plaster001_neutral_albedo.png', nrm=None, tile=1.0, tint='#CDA06B', smooth=0.08, metal=0.0,
                             note='Plain carton faces (printed side and taped top use MAT_PH_labels).'),
    'MAT_PH_labels': dict(tex='NEW:Pharmacy_labels_v01.png', nrm=None, tile=1.0, tint='#FFFFFF', smooth=0.2, metal=0.0, atlas=True,
                          note='Atlas material (UV0 is atlas space, tiling 1, offset 0): price cards, STAFF ONLY signs, package faces, labels, posters, solid swatches.'),
    'MAT_PH_turquoise_paint': dict(tex='TextureTest_v01/Source_v03/TT_acg_Plaster001_neutral_albedo.png', nrm=None, tile=1.0, tint='#69A9AA', smooth=0.40, metal=0.0,
                                   note='Reference B painted furniture: shelving uprights, counter base + frame, cash desk, gate, fridge body, staff door (sales face) + frame.'),
    'MAT_PH_wall_green': dict(tex='TextureTest_v01/Source_v03/TT_acg_Plaster001_neutral_albedo.png', nrm='TextureTest_v01/Source_v03/TT_acg_Plaster001_normal.png',
                              tile=2.0, tint='#5E9A70', smooth=0.18, metal=0.0, note='Reference A green wall paint: stockroom dado and skirting.'),
    'MAT_PH_laminate': dict(tex=None, nrm=None, tile=1.0, tint='#F2EFE6', smooth=0.45, metal=0.0,
                            note='White laminate / enamel: shelf boards + lips, counter tops, worktop, display platform, cabinet carcasses, lamp housings, switch boxes, conduit.'),
    'MAT_PH_rubber': dict(tex=None, nrm=None, tile=1.0, tint='#232426', smooth=0.08, metal=0.0, note='Rubber: toe kicks, chair feet, entrance mat, bucket base, door seals.'),
    'MAT_PH_concrete': dict(tex='MapTextures_W86/T1/Textures/T1_concrete_light_albedo.png', nrm='MapTextures_W86/T1/Textures/T1_concrete_light_normal.png',
                            tile=3.0, tint='#FFFFFF', smooth=0.18, metal=0.0, note='Street-door step, rear landing ramp.'),
    'MAT_PH_ceramic': dict(tex=None, nrm=None, tile=1.0, tint='#EEEDE7', smooth=0.75, metal=0.0, note='Stockroom sink.'),
    'MAT_PH_dark': dict(tex=None, nrm=None, tile=1.0, tint='#2C2E31', smooth=0.3, metal=0.0,
                        note='Black plastic / rubber: register, chair legs, bins, door seals, hinges, body and trash bags.'),
    'MAT_PH_emissive': dict(tex=None, nrm=None, tile=1.0, tint='#FFF1D8', smooth=0.5, metal=0.0, emission='#FFF1D8',
                            note='Lamp diffusers, fridge light strip. Emission 2-4 (HDR); pair with real lights at the light anchors.'),
    'MAT_PH_cross_glow': dict(tex=None, nrm=None, tile=1.0, tint='#45C46C', smooth=0.5, metal=0.0, emission='#45C46C',
                              note='Faces of the projecting green cross sign (wordless storefront). Emission ~3.'),
}
M_FLOOR, M_TURQ, M_CREAM, M_GB, M_OFF = 'MAT_PH_tile_floor', 'MAT_PH_wall_turquoise', 'MAT_PH_wall_cream', 'MAT_PH_facade_greyblue', 'MAT_PH_offwhite'
M_GREEN, M_GLASS, M_METAL, M_WOOD, M_CARD = 'MAT_PH_green', 'MAT_PH_glass', 'MAT_PH_metal', 'MAT_PH_wood', 'MAT_PH_cardboard'
M_LAB, M_CONC, M_CER, M_DARK, M_EMIT, M_CROSS = 'MAT_PH_labels', 'MAT_PH_concrete', 'MAT_PH_ceramic', 'MAT_PH_dark', 'MAT_PH_emissive', 'MAT_PH_cross_glow'
M_TQP, M_GWALL, M_LAM, M_RUB = 'MAT_PH_turquoise_paint', 'MAT_PH_wall_green', 'MAT_PH_laminate', 'MAT_PH_rubber'


def hex2lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def make_materials():
    lib = {}
    for name, m in MATS.items():
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        col = hex2lin(m['tint'])
        bsdf.inputs['Base Color'].default_value = (*col, 1.0)
        bsdf.inputs['Roughness'].default_value = 1.0 - m['smooth']
        bsdf.inputs['Metallic'].default_value = m['metal']
        mat.diffuse_color = (*col, 1.0)
        if m.get('emission'):
            bsdf.inputs['Emission Color'].default_value = (*hex2lin(m['emission']), 1.0)
            bsdf.inputs['Emission Strength'].default_value = 3.0
        if m.get('alpha'):
            bsdf.inputs['Alpha'].default_value = m['alpha']
            try:
                mat.surface_render_method = 'BLENDED'
            except Exception:
                pass
            mat.use_backface_culling = False
        if m['tex']:
            path = os.path.join(ASSET_DIR, m['tex'][4:]) if m['tex'].startswith('NEW:') else ART + m['tex']
            tc = nt.nodes.new('ShaderNodeTexCoord')
            mp = nt.nodes.new('ShaderNodeMapping')
            s = 1.0 / m['tile']
            mp.inputs['Scale'].default_value = (s, s, 1.0)
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(path, check_existing=True)
            if m.get('atlas'):
                img.interpolation = 'Linear'
            mul = nt.nodes.new('ShaderNodeVectorMath')
            mul.operation = 'MULTIPLY'
            mul.inputs[1].default_value = col
            nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
            nt.links.new(mp.outputs['Vector'], img.inputs['Vector'])
            nt.links.new(img.outputs['Color'], mul.inputs[0])
            nt.links.new(mul.outputs['Vector'], bsdf.inputs['Base Color'])
            if m.get('nrm'):
                nimg = nt.nodes.new('ShaderNodeTexImage')
                nimg.image = bpy.data.images.load(ART + m['nrm'], check_existing=True)
                nimg.image.colorspace_settings.name = 'Non-Color'
                nm = nt.nodes.new('ShaderNodeNormalMap')
                nm.inputs['Strength'].default_value = 0.6
                nt.links.new(mp.outputs['Vector'], nimg.inputs['Vector'])
                nt.links.new(nimg.outputs['Color'], nm.inputs['Color'])
                nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        lib[name] = mat
    return lib


# ============================================================================ helpers
ZV = Vector((0, 0, 1))
UCX = []        # unit colliders: list of point lists (convex hulls)
SUPPORTS = []   # (name, bottom-centre point) of fixed furniture / prop items, checked for floating


def ucx_box(mn, mx):
    UCX.append([Vector((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])])


def bx(mb, x0, x1, y0, y1, z0, z1, mat, skip=(), mats=None, rects=None, M=None, zoff=(0.0, 0.0)):
    mb.box((min(x0, x1), min(y0, y1), min(z0, z1)), (max(x0, x1), max(y0, y1), max(z0, z1)), mat, M=M, skip=skip, mats=mats,
           rects=rects, zoff=zoff)


def cbar(mb, axis, a0, a1, s0, s1, t0, t1, c, mat, chamf=(1, 1, 1, 1), caps=(True, True)):
    """Bar extruded along axis ('x' or 'y') whose cross-section [s0,s1]x[t0,t1] (s = other horizontal axis, t = z) has
    chamfered corners: chamf flags for corners (s0,t0), (s1,t0), (s1,t1), (s0,t1)."""
    cs = [c if f else 0.0 for f in chamf]
    raw = [(s0 + cs[0], t0), (s1 - cs[1], t0), (s1, t0 + cs[1]), (s1, t1 - cs[2]), (s1 - cs[2], t1), (s0 + cs[3], t1),
           (s0, t1 - cs[3]), (s0, t0 + cs[0])]
    poly = []
    for q in raw:
        if not poly or (abs(q[0] - poly[-1][0]) > 1e-7 or abs(q[1] - poly[-1][1]) > 1e-7):
            poly.append(q)
    if abs(poly[0][0] - poly[-1][0]) < 1e-7 and abs(poly[0][1] - poly[-1][1]) < 1e-7:
        poly.pop()
    if axis == 'x':
        frame = lambda u, v, w: Vector((w, u, v))
    else:
        frame = lambda u, v, w: Vector((u, w, v))
    mb.prism(poly, a0, a1, mat, frame, caps=caps)


def WF(axis, c, sign):
    """Wall frame for a face on plane axis=c whose normal is sign*axis.  u runs along the wall (right when facing it)."""
    if axis == 'y':
        return Wall((0, c, 0), (-sign, 0, 0), (0, sign, 0))
    return Wall((c, 0, 0), (0, sign, 0), (sign, 0, 0))


def a2u(axis, sign, a):
    return (-sign * a) if axis == 'y' else (sign * a)


def _uops(axis, sign, ops):
    out = []
    for o in ops:
        u0, u1 = sorted((a2u(axis, sign, o[0]), a2u(axis, sign, o[1])))
        out.append((u0, u1, o[2], o[3]))
    return out


def paint(mb, axis, c, sign, a0, a1, z0, z1, ops, bands):
    """Flat wall face minus openings; bands = [(z_from, mat), ...] ascending."""
    Wf = WF(axis, c, sign)
    ua, ub = sorted((a2u(axis, sign, a0), a2u(axis, sign, a1)))
    iv = [(b[0], bands[i + 1][0] if i + 1 < len(bands) else 1e9, b[1]) for i, b in enumerate(bands)]
    for pa, pb, za, zb in pieces(ua, ub, z0, z1, _uops(axis, sign, ops)):
        for b0, b1, mat in iv:
            lo, hi = max(za, b0), min(zb, b1)
            if hi - lo > EPS:
                mb.face([Wf.P(pa, lo), Wf.P(pb, lo), Wf.P(pb, hi), Wf.P(pa, hi)], mat, want=Wf.N)


def trim(mb, axis, c, sign, a0, a1, z0, z1, proud, mat, ops, skip_top=False, skip_bottom=False):
    """Protruding strip along a wall face, interrupted by openings that overlap its height."""
    Wf = WF(axis, c, sign)
    ua, ub = sorted((a2u(axis, sign, a0), a2u(axis, sign, a1)))
    cuts = sorted((u0, u1) for u0, u1, oz0, oz1 in _uops(axis, sign, ops) if oz0 < z1 - EPS and oz1 > z0 + EPS)
    segs, cur = [], ua
    for u0, u1 in cuts:
        if u1 <= cur or u0 >= ub:
            continue
        if u0 > cur + EPS:
            segs.append((cur, u0))
        cur = max(cur, u1)
    if cur < ub - EPS:
        segs.append((cur, ub))
    sk = ('y-',) + (('z+',) if skip_top else ()) + (('z-',) if skip_bottom else ())
    for s0, s1 in segs:
        whexa(mb, Wf, s0, s1, 0.0, proud, z0, z1, mat, skip=sk)


def reveal(mb, axis, c0, c1, a0, a1, oz0, oz1, bands, sill=True, head=True, jambs=True):
    """Opening lining through a wall of thickness [c0, c1] (along axis).  bands = [(c_from, c_to, mat), ...]."""
    for (b0, b1, mat) in bands:
        def p(a, cc, z):
            return Vector((a, cc, z)) if axis == 'y' else Vector((cc, a, z))
        nx = (lambda s: Vector((s, 0, 0))) if axis == 'y' else (lambda s: Vector((0, s, 0)))
        if jambs:
            mb.face([p(a0, b0, oz0), p(a0, b1, oz0), p(a0, b1, oz1), p(a0, b0, oz1)], mat, want=nx(1))
            mb.face([p(a1, b0, oz0), p(a1, b1, oz0), p(a1, b1, oz1), p(a1, b0, oz1)], mat, want=nx(-1))
        if head:
            mb.face([p(a0, b0, oz1), p(a1, b0, oz1), p(a1, b1, oz1), p(a0, b1, oz1)], mat, want=(0, 0, -1))
        if sill:
            mb.face([p(a0, b0, oz0), p(a1, b0, oz0), p(a1, b1, oz0), p(a0, b1, oz0)], mat, want=(0, 0, 1))


def inset_panel(mb, Wf, u0, u1, z0, z1, d, border, depth, mat, mat_in=None):
    """Framed panel on a wall frame at distance d: ring at d, panel recessed by depth (raised if depth < 0)."""
    a0, a1, b0, b1 = u0 + border, u1 - border, z0 + border, z1 - border
    P_ = Wf.P
    for q in ((u0, u1, z0, b0), (u0, u1, b1, z1), (u0, a0, b0, b1), (a1, u1, b0, b1)):
        mb.face([P_(q[0], q[2], d), P_(q[1], q[2], d), P_(q[1], q[3], d), P_(q[0], q[3], d)], mat, want=Wf.N)
    di = d - depth
    mb.face([P_(a0, b0, di), P_(a1, b0, di), P_(a1, b1, di), P_(a0, b1, di)], mat_in or mat, want=Wf.N)
    s = 1 if depth > 0 else -1
    mb.face([P_(a0, b0, d), P_(a1, b0, d), P_(a1, b0, di), P_(a0, b0, di)], mat, want=ZV * s)
    mb.face([P_(a0, b1, d), P_(a1, b1, d), P_(a1, b1, di), P_(a0, b1, di)], mat, want=-ZV * s)
    mb.face([P_(a0, b0, d), P_(a0, b1, d), P_(a0, b1, di), P_(a0, b0, di)], mat, want=Wf.T * s)
    mb.face([P_(a1, b0, d), P_(a1, b1, d), P_(a1, b1, di), P_(a1, b0, di)], mat, want=-Wf.T * s)


def glass(mb, pts_cw, n):
    """Two single-sided panes 4 mm apart (front along n, back along -n)."""
    n = Vector(n).normalized()
    a = [Vector(p) + n * 0.002 for p in pts_cw]
    b = [Vector(p) - n * 0.002 for p in pts_cw]
    mb.face(a, M_GLASS, want=n)
    mb.face(b, M_GLASS, want=-n)


def rect_uv(r):
    return [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]


def label_quad(mb, Wf, u0, u1, z0, z1, d, region):
    """Upright label on a wall frame at distance d, readable from the room side."""
    r = RG[region]
    mb.face([Wf.P(u0, z0, d), Wf.P(u1, z0, d), Wf.P(u1, z1, d), Wf.P(u0, z1, d)], M_LAB, want=Wf.N, uvs=rect_uv(r))


def frame_M(Wf):
    """Shelf-local frame: x = along the wall (Wf.T), y = into the wall (-Wf.N), z up; origin on the wall plane."""
    Tt, N, O = Wf.T, Wf.N, Wf.O
    return Matrix(((Tt.x, -N.x, 0, O.x), (Tt.y, -N.y, 0, O.y), (Tt.z, -N.z, 1, O.z), (0, 0, 0, 1)))


def sw(name):
    return RG['sw_' + name]


def all_rects(front, side='white', top=None):
    s = sw(side) if isinstance(side, str) else side
    return {'y-': RG[front] if isinstance(front, str) else front, 'y+': s, 'x-': s, 'x+': s,
            'z+': (sw(top) if isinstance(top, str) else top) if top else s, 'z-': s}


# ============================================================================ shell (walls, floor, storefront, rear facade)
SALES_B = [(0.0, M_TURQ), (1.05, M_CREAM)]
STOCK_B = [(0.0, M_GWALL), (1.25, M_OFF)]


def build_shell(lod):
    mb = MB('PH_Unit_Shell_LOD%d' % lod)
    flat = lod > 0
    HW, H, D = P.HW, P.H, P.D
    X0, X1, Y0, Y3, PY0, PY1 = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1
    top = H + P.SLAB
    # ---------------- floors (grout aligned to the inner wall faces)
    zo = ((-X0) % 0.6, (-Y0) % 0.6)
    mb.face([(X0, Y0, 0), (X1, Y0, 0), (X1, PY0, 0), (X0, PY0, 0)], M_FLOOR, want=(0, 0, 1), zoff=zo)
    mb.face([(X0, PY1, 0), (X1, PY1, 0), (X1, Y3, 0), (X0, Y3, 0)], M_FLOOR, want=(0, 0, 1), zoff=zo)
    mb.face([(P.SD0, PY0, 0), (P.SD1, PY0, 0), (P.SD1, PY1, 0), (P.SD0, PY1, 0)], M_FLOOR, want=(0, 0, 1), zoff=zo)
    mb.face([(P.RD0, Y3, 0), (P.RD1, Y3, 0), (P.RD1, D, 0), (P.RD0, D, 0)], M_METAL, want=(0, 0, 1))
    if not flat:
        cbar(mb, 'x', P.RD0 + 0.06, P.RD1 - 0.06, D - 0.20, D - 0.08, 0.0, 0.008, 0.006, M_METAL, chamf=(0, 0, 1, 1))
        cbar(mb, 'x', P.SD0, P.SD1, P.PY0 + 0.01, P.PY1 - 0.01, 0.0, 0.006, 0.005, M_METAL, chamf=(0, 0, 1, 1))
    mb.face([(-HW, 0, -0.2), (-HW, D, -0.2), (HW, D, -0.2), (HW, 0, -0.2)], M_CONC, want=(0, 0, -1))
    # ---------------- interior wall faces + trims
    win_op = (P.XW0, P.XW1, P.SILL, P.OH)
    bay_op = (P.BAY0, P.BAY1, 0.0, P.OH)
    sd_op = (P.SD0, P.SD1, 0.0, P.SDH)
    rd_op = (P.RD0, P.RD1, 0.0, P.RDH)
    rw_op = (P.RW0, P.RW1, P.RWZ[0], P.RWZ[1])
    sd_arch = (P.SD0 - 0.08, P.SD1 + 0.08, 0.0, P.SDH + 0.08)
    rd_arch = (P.RD0 - 0.07, P.RD1 + 0.07, 0.0, P.RDH + 0.07)
    walls_sales = [('y', Y0, 1, X0, X1, [win_op, bay_op], [(P.XW0, P.XW1, 0.0, P.SILL)]),
                   ('x', X0, 1, Y0, PY0, [], []), ('x', X1, -1, Y0, PY0, [], []),
                   ('y', PY0, -1, X0, X1, [sd_op], [sd_arch])]
    walls_stock = [('y', PY1, 1, X0, X1, [sd_op], [sd_arch]), ('x', X0, 1, PY1, Y3, [], []), ('x', X1, -1, PY1, Y3, [], []),
                   ('y', Y3, -1, X0, X1, [rd_op, rw_op], [rd_arch])]

    def tr(axis, a0, a1, proud):
        return (a0 + proud, a1 - proud) if axis == 'x' else (a0, a1)
    for axis, c, sg, a0, a1, ops, xops in walls_sales:
        paint(mb, axis, c, sg, a0, a1, 0.0, H, ops, SALES_B)
        if not flat:
            trim(mb, axis, c, sg, *tr(axis, a0, a1, 0.015), 0.0, 0.09, 0.015, M_TURQ, ops + xops, skip_bottom=True)
            trim(mb, axis, c, sg, *tr(axis, a0, a1, 0.022), 1.03, 1.08, 0.022, M_TURQ, ops + xops)
        trim(mb, axis, c, sg, *tr(axis, a0, a1, 0.035), H - 0.12, H, 0.035, M_TURQ, [], skip_top=True)
    for axis, c, sg, a0, a1, ops, xops in walls_stock:
        paint(mb, axis, c, sg, a0, a1, 0.0, H, ops, STOCK_B)
        if not flat:
            trim(mb, axis, c, sg, *tr(axis, a0, a1, 0.012), 0.0, 0.08, 0.012, M_GWALL, ops + xops, skip_bottom=True)
    # ---------------- side walls, rear wall, partition bodies (outer faces, tops, reveals)
    for sx in (-1, 1):
        xo = sx * HW
        mb.face([(xo, Y0, -0.2), (xo, D, -0.2), (xo, D, top), (xo, Y0, top)], M_OFF, want=(sx, 0, 0))
        xi = X0 if sx < 0 else X1
        xa, xb = sorted((xi, xo))
        mb.face([(xa, Y0, top), (xb, Y0, top), (xb, Y3, top), (xa, Y3, top)], M_OFF, want=(0, 0, 1))
    # rear wall outer face, plinth band, reveals
    paint(mb, 'y', D, 1, -HW, HW, P.FOUND, top, [(P.RD0, P.RD1, P.FOUND, P.RDH), rw_op], [(P.FOUND, M_OFF)])
    mb.face([(-HW, Y3, top), (HW, Y3, top), (HW, D, top), (-HW, D, top)], M_OFF, want=(0, 0, 1))
    trim(mb, 'y', D, 1, -HW, HW, P.FOUND, 0.45, 0.03, M_GB, [(P.RD0, P.RD1, P.FOUND, P.RDH)])
    reveal(mb, 'y', Y3, D, P.RD0, P.RD1, 0.0, P.RDH, [(Y3, D - 0.14, M_OFF), (D - 0.02, D, M_OFF)], sill=False)
    reveal(mb, 'y', Y3, D, P.RW0, P.RW1, P.RWZ[0], P.RWZ[1], [(Y3, D, M_OFF)], sill=False)
    # rear door steel frame (green), inner architrave
    fy0, fy1 = D - 0.14, D - 0.02
    bx(mb, P.RD0, P.RD0 + 0.06, fy0, fy1, 0.0, P.RDH - 0.06, M_GREEN, skip=('z-', 'x-'))
    bx(mb, P.RD1 - 0.06, P.RD1, fy0, fy1, 0.0, P.RDH - 0.06, M_GREEN, skip=('z-', 'x+'))
    bx(mb, P.RD0, P.RD1, fy0, fy1, P.RDH - 0.06, P.RDH, M_GREEN, skip=('z+',))
    Wr = WF('y', Y3, -1)
    for (u0, u1, z0, z1) in ((P.RD0 - 0.07, P.RD0, 0.0, P.RDH + 0.07), (P.RD1, P.RD1 + 0.07, 0.0, P.RDH + 0.07),
                             (P.RD0, P.RD1, P.RDH, P.RDH + 0.07)):
        uu = sorted((a2u('y', -1, u0), a2u('y', -1, u1)))
        whexa(mb, Wr, uu[0], uu[1], 0.0, 0.02, z0, z1, M_GREEN, skip=('y-', 'z-') if z0 == 0.0 else ('y-',))
    # rear window: frame, glass, sill, bars
    wz0, wz1 = P.RWZ
    bx(mb, P.RW0, P.RW1, Y3 - 0.05, Y3, wz0 - 0.03, wz0, M_LAM, skip=('y+', 'z-'))
    fy = D - 0.12
    for (a0, a1, z0, z1) in ((P.RW0, P.RW0 + 0.05, wz0, wz1), (P.RW1 - 0.05, P.RW1, wz0, wz1),
                             (P.RW0 + 0.05, P.RW1 - 0.05, wz0, wz0 + 0.05), (P.RW0 + 0.05, P.RW1 - 0.05, wz1 - 0.05, wz1)):
        bx(mb, a0, a1, fy - 0.03, fy + 0.03, z0, z1, M_GREEN)
    glass(mb, [(P.RW0 + 0.05, fy, wz0 + 0.05), (P.RW1 - 0.05, fy, wz0 + 0.05), (P.RW1 - 0.05, fy, wz1 - 0.05), (P.RW0 + 0.05, fy, wz1 - 0.05)], (0, -1, 0))
    if not flat:
        for k in range(1, 6):
            x = P.RW0 + (P.RW1 - P.RW0) * k / 6
            mb.cyl((x, D - 0.035, wz0), (x, D - 0.035, wz1), 0.009, M_METAL, n=6, caps=(False, False))
    mb.face([(P.RW0, Y3, wz0), (P.RW1, Y3, wz0), (P.RW1, fy - 0.03, wz0), (P.RW0, fy - 0.03, wz0)], M_OFF, want=(0, 0, 1))
    bx(mb, P.RW0 - 0.04, P.RW1 + 0.04, D, D + 0.06, wz0 - 0.05, wz0, M_METAL, skip=('y-',))
    mb.face([(P.RW0, fy + 0.03, wz0), (P.RW1, fy + 0.03, wz0), (P.RW1, D, wz0), (P.RW0, D, wz0)], M_OFF, want=(0, 0, 1))
    # partition reveal (staff door): turquoise lining, architraves both faces
    reveal(mb, 'y', PY0, PY1, P.SD0, P.SD1, 0.0, P.SDH, [(PY0, PY1, M_TQP)], sill=False)
    for c, sg, mat in ((PY0, -1, M_TQP), (PY1, 1, M_GREEN)):
        Wf = WF('y', c, sg)
        for (a0, a1, z0, z1) in ((P.SD0 - 0.08, P.SD0, 0.0, P.SDH + 0.08), (P.SD1, P.SD1 + 0.08, 0.0, P.SDH + 0.08),
                                 (P.SD0, P.SD1, P.SDH, P.SDH + 0.08)):
            uu = sorted((a2u('y', sg, a0), a2u('y', sg, a1)))
            whexa(mb, Wf, uu[0], uu[1], 0.0, 0.025, z0, z1, mat, skip=('y-', 'z-') if z0 == 0.0 else ('y-',))
    # ---------------- storefront (reference C, wordless)
    build_storefront(mb, lod)
    # ---------------- rear exterior: landing ramp, canopy, lamp
    lx0, lx1, ly1 = P.RD0 - 0.45, P.RD1 + 0.45, D + 1.40
    zr = lambda y: -0.12 * (y - D) / (ly1 - D)
    mb.face([(lx0, D, 0.0), (lx1, D, 0.0), (lx1, ly1, zr(ly1)), (lx0, ly1, zr(ly1))], M_CONC, want=(0, 0, 1))
    for xs, w in ((lx0, -1), (lx1, 1)):
        mb.face([(xs, D, -0.45), (xs, ly1, -0.45), (xs, ly1, zr(ly1)), (xs, D, 0.0)], M_CONC, want=(w, 0, 0))
    mb.face([(lx0, ly1, -0.45), (lx1, ly1, -0.45), (lx1, ly1, zr(ly1)), (lx0, ly1, zr(ly1))], M_CONC, want=(0, 1, 0))
    cz = P.RDH + 0.32
    bx(mb, P.RD0 - 0.30, P.RD1 + 0.30, D, D + 0.95, cz, cz + 0.05, M_METAL, skip=('y-',))
    if not flat:
        bx(mb, P.RD0 - 0.30, P.RD1 + 0.30, D + 0.92, D + 0.95, cz - 0.06, cz, M_METAL, skip=('z+',))
        for x in (P.RD0 - 0.22, P.RD1 + 0.22):
            mb.cyl((x, D + 0.01, cz + 0.65), (x, D + 0.90, cz + 0.05), 0.012, M_METAL, n=6)
            bx(mb, x - 0.04, x + 0.04, D, D + 0.02, cz + 0.58, cz + 0.72, M_METAL, skip=('y-',))
    lxp = P.RD1 + 0.45
    bx(mb, lxp - 0.11, lxp + 0.11, D, D + 0.10, 2.15, 2.31, M_DARK, skip=('y-',))
    if not flat:
        mb.face([(lxp - 0.08, D + 0.102, 2.17), (lxp + 0.08, D + 0.102, 2.17), (lxp + 0.08, D + 0.102, 2.29), (lxp - 0.08, D + 0.102, 2.29)], M_EMIT, want=(0, 1, 0))
    # ---------------- staff/sales light switches + stockroom conduit (fixtures)
    if not flat:
        for (xs, c, sg) in ((P.SD0 - 0.30, PY0, -1), (P.RD0 - 0.35, Y3, -1)):
            Wf = WF('y', c, sg)
            u = a2u('y', sg, xs)
            whexa(mb, Wf, u - 0.045, u + 0.045, 0.0, 0.035, 1.20, 1.32, M_LAM, skip=('y-',))
            whexa(mb, Wf, u - 0.012, u + 0.012, 0.035, 0.045, 1.245, 1.275, M_DARK, skip=('y-',))
            if c == Y3:
                p0 = Wf.P(u, 1.32, 0.02)
                mb.cyl(p0, Vector((p0.x, p0.y, H)), 0.011, M_LAM, n=6, caps=(False, False))
                for zc in (1.8, 2.5, 3.1):
                    if zc < H - 0.1:
                        whexa(mb, Wf, u - 0.018, u + 0.018, 0.0, 0.034, zc - 0.012, zc + 0.012, M_LAM, skip=('y-',))
    return mb


def build_storefront(mb, lod):
    flat = lod > 0
    HW, FH, OH, Y0 = P.HW, P.FH, P.OH, P.Y0
    f0, f1 = P.FR
    found = P.FOUND
    Wst = WF('y', 0.0, -1)  # facing the street, u = x
    # pilasters (two boxes each so the reveal stops at the fascia), plinths
    for side in (-1, 1):
        xa, xb = (-HW, P.XW0) if side < 0 else (P.BAY1, HW)
        rev = 'x+' if side < 0 else 'x-'
        outer = 'x-' if side < 0 else 'x+'
        bx(mb, xa, xb, -0.05, Y0, found, OH, M_OFF, skip=('y+', 'z-', 'z+'))
        bx(mb, xa, xb, -0.05, Y0, OH, FH - 0.12, M_OFF, skip=('y+', 'z-', 'z+', rev))
        bx(mb, xa - (0.0 if side > 0 else 0.0), xb, -0.085, -0.05, found, 0.38, M_GB, skip=('y+', 'z-'))
        if not flat:
            # recessed vertical groove pair on the pilaster face
            for k in (0.33, 0.67):
                x = xa + (xb - xa) * k
                bx(mb, x - 0.012, x + 0.012, -0.065, -0.05, 0.40, OH - 0.05, M_OFF, skip=('y+',))
    # window block riser with inset panels, sill, window board
    xw0, xw1 = P.XW0, P.XW1
    if flat:
        bx(mb, xw0, xw1, 0.0, Y0, found, P.RZ, M_GB, skip=('y+', 'z-', 'z+', 'x-', 'x+'))
    else:
        bx(mb, xw0, xw1, 0.0, Y0, found, P.RZ, M_GB, skip=('y+', 'z-', 'z+', 'x-', 'x+', 'y-'))
        mb.face([(xw0, 0.0, found), (xw1, 0.0, found), (xw1, 0.0, 0.0), (xw0, 0.0, 0.0)], M_GB, want=(0, -1, 0))
        pw = (xw1 - xw0) / P.NPANES
        for i in range(P.NPANES):
            inset_panel(mb, Wst, xw0 + i * pw, xw0 + (i + 1) * pw, 0.0, P.RZ, 0.0, 0.09, 0.018, M_GB)
    cbar(mb, 'x', xw0, xw1, -0.07, f0, P.RZ, P.RZ + 0.06, 0.015, M_OFF, chamf=(1, 0, 0, 1), caps=(False, False))
    if not flat:  # drip groove under the sill nose
        bx(mb, xw0, xw1, -0.05, -0.04, P.RZ - 0.006, P.RZ, M_OFF, skip=('z+',))
    bx(mb, xw0, xw1, f0, Y0, P.RZ, P.SILL, M_OFF, skip=('y-', 'y+', 'z-', 'x-', 'x+'))
    # window frames
    fx = [xw0 + (xw1 - xw0) * i / P.NPANES for i in range(P.NPANES + 1)]
    tz0, tz1 = 2.42, 2.50
    bx(mb, xw0, xw1, f0, f1, P.SILL, P.SILL + 0.08, M_GB, skip=('z-',))
    bx(mb, xw0, xw1, f0, f1, OH - 0.08, OH, M_GB, skip=('z+',))
    for i, x in enumerate(fx):
        w = 0.07 if i in (0, P.NPANES) else 0.05
        a, b = (x, x + w) if i == 0 else ((x - w, x) if i == P.NPANES else (x - w, x + w))
        for z0, z1 in ((P.SILL + 0.08, tz0), (tz1, OH - 0.08)):
            bx(mb, a, b, f0, f1, z0, z1, M_GB, skip=('z-', 'z+'))
    for i in range(P.NPANES):
        a = fx[i] + (0.07 if i == 0 else 0.05)
        b = fx[i + 1] - (0.07 if i + 1 == P.NPANES else 0.05)
        bx(mb, a, b, f0, f1, tz0, tz1, M_GB, skip=('x-', 'x+'))
        for z0, z1 in ((P.SILL + 0.08, tz0), (tz1, OH - 0.08)):
            glass(mb, [(a, P.GY, z0), (b, P.GY, z0), (b, P.GY, z1), (a, P.GY, z1)], (0, -1, 0))
        if not flat:  # glazing beads (thin raised strip on the street side, all four sides of the lower pane)
            for z in (P.SILL + 0.08, tz0 - 0.015):
                bx(mb, a, b, f0 - 0.012, f0, z, z + 0.015, M_GB, skip=('y+',))
            for xa in (a, b - 0.015):
                bx(mb, xa, xa + 0.015, f0 - 0.012, f0, P.SILL + 0.095, tz0 - 0.015, M_GB, skip=('y+', 'z-', 'z+'))
    # pier between the window block and the door bay
    bx(mb, xw1, P.BAY0, 0.0, Y0, found, OH, M_GB, skip=('y+', 'z-', 'z+'))
    # door bay: base, kick panels, sidelights, jambs, transom
    b0, b1, d0, d1 = P.BAY0, P.BAY1, P.DO0, P.DO1
    mb.face([(b0, 0.0, 0.0), (b1, 0.0, 0.0), (b1, Y0, 0.0), (b0, Y0, 0.0)], M_METAL, want=(0, 0, 1))
    mb.face([(b0, 0.0, found), (b1, 0.0, found), (b1, 0.0, 0.0), (b0, 0.0, 0.0)], M_GB, want=(0, -1, 0))
    st = 0.07
    for (a, b) in ((b0, b0 + st), (d0 - st, d0), (d1, d1 + st), (b1 - st, b1)):
        bx(mb, a, b, f0, f1, 0.0, OH - 0.08, M_GB, skip=('z-', 'z+'))
    for (a, b) in ((b0 + st, d0 - st), (d1 + st, b1 - st)):
        if b - a < 0.02:
            continue
        bx(mb, a, b, f0, f1, 0.0, P.SILL, M_GB, skip=('z-', 'x-', 'x+'))
        glass(mb, [(a, P.GY, P.SILL), (b, P.GY, P.SILL), (b, P.GY, P.DH), (a, P.GY, P.DH)], (0, -1, 0))
        bx(mb, a, b, f0, f1, P.DH, P.DH + 0.08, M_GB, skip=('x-', 'x+'))
    bx(mb, d0, d1, f0, f1, P.DH, P.DH + 0.08, M_GB, skip=('x-', 'x+'))
    bx(mb, b0, b1, f0, f1, OH - 0.08, OH, M_GB, skip=('z+',))
    for (a, b) in ((b0 + st, d0 - st), (d0, d1), (d1 + st, b1 - st)):
        if b - a > 0.02:
            glass(mb, [(a, P.GY, P.DH + 0.08), (b, P.GY, P.DH + 0.08), (b, P.GY, OH - 0.08), (a, P.GY, OH - 0.08)], (0, -1, 0))
    # fascia (wordless), drip trim, inner head, cornice
    bx(mb, xw0, b1, -0.14, f0, OH, FH - 0.12, M_GB, skip=('y+', 'z+'))
    if not flat:
        bx(mb, xw0, b1, -0.17, -0.14, OH, OH + 0.05, M_OFF, skip=('y+',))
        bx(mb, xw0, b1, -0.165, -0.14, FH - 0.20, FH - 0.17, M_OFF, skip=('y+',))
        for xj in fx[1:-1] + [P.BAY0 - 0.11]:
            bx(mb, xj - 0.012, xj + 0.012, -0.150, -0.14, OH + 0.05, FH - 0.20, M_GB, skip=('y+', 'z-', 'z+'))
    bx(mb, xw0, b1, f0, Y0, OH, FH - 0.12, M_OFF, skip=('y-', 'y+', 'z+', 'x-', 'x+'))
    cbar(mb, 'x', -HW, HW, -0.20, Y0, FH - 0.12, FH, 0.04, M_OFF, chamf=(1, 0, 0, 0))
    if not flat:
        cbar(mb, 'x', -HW, HW, -0.25, -0.20, FH - 0.06, FH, 0.015, M_OFF, chamf=(1, 0, 0, 1))
    # single low step at the street door (top flush with the floor; sinks into a higher pavement)
    bx(mb, d0 - 0.30, d1 + 0.30, -0.42, 0.0, found, 0.0, M_CONC, skip=('y+', 'z-'))
    if not flat:
        bx(mb, d0 - 0.30, d1 + 0.30, -0.44, -0.42, -0.02, 0.0, M_METAL, skip=('y+', 'z-'))
    # projecting green cross sign on the right pilaster
    build_cross_sign(mb, lod)


def plus_poly(s, a):
    """Plus outline (CCW), half size s, half arm width a."""
    return [(a, -s), (a, -a), (s, -a), (s, a), (a, a), (a, s), (-a, s), (-a, a), (-s, a), (-s, -a), (-a, -a), (-a, -s)]


def build_cross_sign(mb, lod):
    cx = P.HW - P.PIL / 2
    cy, cz = -0.66, P.OH + 0.30
    s, a, t = 0.36, 0.125, 0.07
    frame = lambda u, v, w: Vector((cx + w, cy + u, cz + v))
    outer = plus_poly(s, a)
    mb.prism(outer, -t, t, M_GREEN, frame, caps=(False, False))
    inner = plus_poly(s - 0.03, a - 0.03)
    for sgn in (-1, 1):
        ring_out = [frame(u, v, sgn * t) for u, v in outer]
        ring_in = [frame(u, v, sgn * t) for u, v in inner]
        n = len(outer)
        for i in range(n):
            j = (i + 1) % n
            mb.face([ring_out[i], ring_out[j], ring_in[j], ring_in[i]], M_GREEN, want=(sgn, 0, 0))
        tin = sgn * (t - (0.012 if lod == 0 else 0.0))
        if lod == 0:
            for i in range(n):
                j = (i + 1) % n
                pa, pb = Vector(inner[i]), Vector(inner[j])
                e = pb - pa
                nrm = Vector((e.y, -e.x)).normalized()  # inward-facing walls of the recess point to the centre
                mb.face([frame(pa.x, pa.y, sgn * t), frame(pb.x, pb.y, sgn * t), frame(pb.x, pb.y, tin), frame(pa.x, pa.y, tin)],
                        M_GREEN, want=Vector((0, -nrm.x, -nrm.y)))
        mb.face([frame(u, v, tin) for u, v in inner], M_CROSS, want=(sgn, 0, 0))
    # bracket: wall plate + two arms
    bx(mb, cx - 0.10, cx + 0.10, -0.08, -0.05, cz - 0.30, cz + 0.30, M_METAL, skip=('y+',))
    for dz in (-0.22, 0.22):
        bx(mb, cx - 0.02, cx + 0.02, cy + s - 0.02, -0.08, cz + dz - 0.02, cz + dz + 0.02, M_METAL)


# ============================================================================ ceiling (separate object, hidden in the cutaway)
LAMPS_SALES, LAMPS_STOCK = [], []


def build_ceiling(lod):
    mb = MB('PH_Unit_Ceiling_LOD%d' % lod)
    flat = lod > 0
    X0, X1, Y0, Y3, PY0, PY1, H = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1, P.H
    mb.face([(X0, Y0, H), (X1, Y0, H), (X1, PY0, H), (X0, PY0, H)], M_OFF, want=(0, 0, -1))
    mb.face([(X0, PY1, H), (X1, PY1, H), (X1, Y3, H), (X0, Y3, H)], M_OFF, want=(0, 0, -1))
    mb.face([(X0, Y0, H + P.SLAB), (X1, Y0, H + P.SLAB), (X1, Y3, H + P.SLAB), (X0, Y3, H + P.SLAB)], M_OFF, want=(0, 0, 1))
    LAMPS_SALES.clear()
    LAMPS_STOCK.clear()
    nx = max(2, round(P.W / 3.8))
    xs = [X0 + (X1 - X0) * (i + 0.5) / nx for i in range(nx)]
    rows = [Y0 + 0.28 * (P.CY0 - Y0), Y0 + 0.75 * (P.CY0 - Y0), 0.5 * (P.CY1 + PY0)]
    if not flat:  # suspended-ceiling T-bars (sales floor)
        y = Y0 + 0.6
        while y < PY0 - 0.1:
            bx(mb, X0 + 0.035, X1 - 0.035, y - 0.012, y + 0.012, H - 0.012, H, M_METAL, skip=('z+', 'x-', 'x+'))
            y += 0.6
        x = 0.0 - 1.2 * math.floor((0.0 - X0) / 1.2)
        while x < X1 - 0.1:
            if x > X0 + 0.1:
                yy = [Y0 + 0.6 * k for k in range(int((PY0 - Y0) / 0.6) + 2)]
                yy = [Y0 + 0.035] + [v for v in yy if Y0 + 0.1 < v < PY0 - 0.1] + [PY0 - 0.035]
                for ya, yb in zip(yy, yy[1:]):
                    a, b = ya + (0.012 if ya > Y0 + 0.05 else 0.0), yb - (0.012 if yb < PY0 - 0.05 else 0.0)
                    if b - a > 0.02:
                        bx(mb, x - 0.012, x + 0.012, a, b, H - 0.012, H, M_METAL, skip=('z+', 'y-', 'y+'))
            x += 1.2
    if not flat:
        yv = Y0 + 0.6 * round((0.5 * (rows[0] + rows[1]) - Y0 - 0.3) / 0.6) + 0.3
        for xv in (-1.8, 1.8):
            for k, hs in enumerate((0.28, 0.21, 0.14)):
                bx(mb, xv - hs, xv + hs, yv - hs, yv + hs, H - 0.015 * (k + 1), H - 0.015 * k, M_LAM if k != 1 else M_METAL, skip=('z+',))
    for y in rows:
        for x in xs:
            lamp_troffer(mb, x, y, H, flat)
            LAMPS_SALES.append((x, y, H - 0.075))
    for x in (0.5 * (X0 + P.RACK_B[1]) + 0.3, 0.5 * (P.RD1 + X1)):
        y = 0.5 * (PY1 + Y3)
        lamp_batten(mb, x, y, H, flat)
        LAMPS_STOCK.append((x, y, H - 0.10))
    return mb


def lamp_troffer(mb, x, y, H, flat):
    L, Wd, d = 1.25, 0.30, 0.07
    x0, x1, y0, y1 = x - L / 2, x + L / 2, y - Wd / 2, y + Wd / 2
    bx(mb, x0, x1, y0, y1, H - d, H, M_LAM, skip=('z+', 'z-'))
    zb = H - d
    if flat:
        mb.face([(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb)], M_EMIT, want=(0, 0, -1))
        return
    bd = 0.035
    ring = [((x0, y0), (x1, y0 + bd)), ((x0, y1 - bd), (x1, y1)), ((x0, y0 + bd), (x0 + bd, y1 - bd)), ((x1 - bd, y0 + bd), (x1, y1 - bd))]
    for (a, b) in ring:
        mb.face([(a[0], a[1], zb), (b[0], a[1], zb), (b[0], b[1], zb), (a[0], b[1], zb)], M_LAM, want=(0, 0, -1))
    zi = zb + 0.012
    ix0, ix1, iy0, iy1 = x0 + bd, x1 - bd, y0 + bd, y1 - bd
    mb.face([(ix0, iy0, zi), (ix1, iy0, zi), (ix1, iy1, zi), (ix0, iy1, zi)], M_EMIT, want=(0, 0, -1))
    for (a, b), w in ((((ix0, iy0), (ix1, iy0)), (0, 1, 0)), (((ix1, iy1), (ix0, iy1)), (0, -1, 0)), (((ix0, iy1), (ix0, iy0)), (1, 0, 0)),
                      (((ix1, iy0), (ix1, iy1)), (-1, 0, 0))):
        mb.face([(a[0], a[1], zb), (b[0], b[1], zb), (b[0], b[1], zi), (a[0], a[1], zi)], M_LAM, want=w)
    # louvre bars across the diffuser + metal end caps fixed to the ceiling
    for k in (1, 2, 3):
        xl = ix0 + (ix1 - ix0) * k / 4
        bx(mb, xl - 0.006, xl + 0.006, iy0, iy1, zb - 0.004, zi, M_METAL, skip=('z+', 'y-', 'y+'))
    for xe in (x0 - 0.02, x1):
        bx(mb, xe, xe + 0.02, y0 - 0.01, y1 + 0.01, H - d - 0.008, H, M_METAL, skip=('z+',))


def lamp_batten(mb, x, y, H, flat):
    L = 1.30
    y0, y1 = y - L / 2, y + L / 2
    bx(mb, x - 0.08, x + 0.08, y0, y1, H - 0.06, H, M_LAM, skip=('z+',))
    cbar(mb, 'y', y0 + 0.04, y1 - 0.04, x - 0.06, x + 0.06, H - 0.10, H - 0.06, 0.02, M_EMIT, chamf=(1, 1, 0, 0))
    if not flat:
        for ye in (y0 - 0.015, y1):
            bx(mb, x - 0.085, x + 0.085, ye, ye + 0.015, H - 0.07, H, M_METAL, skip=('z+',))


# ============================================================================ fixed interior
SHELF_SLOTS = []   # (name, M(shelf-local), u0, u1, z, depth, hmax, style)


def add_slot(name, M, u0, u1, z, depth, hmax, style):
    SHELF_SLOTS.append(dict(name=name, M=M, u0=u0, u1=u1, z=z, depth=depth, hmax=hmax, style=style))


def wall_shelving(mb, name, Wf, u0, u1, lod, levels=(0.10, 0.52, 0.92, 1.32, 1.72), height=P.SHELF_H, depth=P.SHELF_D,
                  frame_mat=M_TQP, board_mat=M_LAM, gap=0.025, style='pharmacy', header=True):
    """Reference-B wall shelving on wall frame Wf (u along the wall, d into the room)."""
    M = frame_M(Wf)
    n = max(1, round((u1 - u0) / 1.0))
    bw = (u1 - u0) / n
    pw = 0.025
    d0, d1 = gap, gap + depth
    for i in range(n + 1):
        u = u0 + i * bw
        a, b = (u, u + 2 * pw) if i == 0 else ((u - 2 * pw, u) if i == n else (u - pw, u + pw))
        whexa(mb, Wf, a, b, d0, d1, 0.0, height, frame_mat, skip=('z-',))
    if lod == 0:
        whexa(mb, Wf, u0 + 2 * pw, u1 - 2 * pw, d0, d1 - 0.035, 0.0, levels[0], frame_mat, skip=('z-', 'y-'))
    for i in range(n):
        a = u0 + i * bw + (2 * pw if i == 0 else pw)
        b = u0 + (i + 1) * bw - (2 * pw if i == n - 1 else pw)
        for k, z in enumerate(levels):
            whexa(mb, Wf, a, b, d0 + (0.012 if lod == 0 else 0.0), d1 - 0.005, z, z + 0.025, board_mat, skip=('y-',) if lod else ())
            if lod == 0:
                whexa(mb, Wf, a, b, d1 - 0.005, d1 + 0.004, z - 0.012, z + 0.035, frame_mat, skip=('y-',))
                if k:
                    for ub_ in (a + 0.002, b - 0.014):
                        whexa(mb, Wf, ub_, ub_ + 0.012, d0 + 0.01, d1 - 0.06, z - 0.045, z, M_METAL, skip=('z+',))
            hmax = (levels[k + 1] if k + 1 < len(levels) else height) - z - 0.06
            add_slot('%s_b%d_l%d' % (name, i, k), M, a + 0.02, b - 0.02, z + 0.025, (d0 + 0.02, d1 - 0.03), hmax, style)
        if lod == 0:  # back panel
            whexa(mb, Wf, a, b, d0, d0 + 0.012, levels[0] + 0.025, height, board_mat, skip=('y-',))
    if header:
        whexa(mb, Wf, u0, u1, d0, d1 + 0.02, height, height + 0.10, frame_mat)
    SUPPORTS.append((name, Wf.P(0.5 * (u0 + u1), 0.0, 0.5 * (d0 + d1))))
    return (d0, d1)


def steel_rack(mb, name, x0, x1, y0, y1, lod, levels=(0.12, 0.55, 0.98, 1.41, 1.84), height=2.0, sides=('x-', 'x+'), along='y'):
    """Reference-A green steel shelving (freestanding or against a wall); fill slots on the given open sides."""
    pw = 0.04
    long_ = (y1 - y0) if along == 'y' else (x1 - x0)
    nb = max(1, round(long_ / 1.3))
    ps = [i / nb for i in range(nb + 1)]
    for t in ps:
        if along == 'y':
            yc = y0 + (y1 - y0) * t
            ya, yb = (yc, yc + pw) if t == 0 else ((yc - pw, yc) if t == 1 else (yc - pw / 2, yc + pw / 2))
            for xa, xb in ((x0, x0 + pw), (x1 - pw, x1)):
                bx(mb, xa, xb, ya, yb, 0.0, height, M_GREEN, skip=('z-',))
        else:
            xc = x0 + (x1 - x0) * t
            xa, xb = (xc, xc + pw) if t == 0 else ((xc - pw, xc) if t == 1 else (xc - pw / 2, xc + pw / 2))
            for ya, yb in ((y0, y0 + pw), (y1 - pw, y1)):
                bx(mb, xa, xb, ya, yb, 0.0, height, M_GREEN, skip=('z-',))
    for k, z in enumerate(levels):
        bx(mb, x0 + 0.005, x1 - 0.005, y0 + 0.005, y1 - 0.005, z, z + 0.025, M_GREEN)
        if lod == 0:
            for sd in sides:
                if sd == 'x-':
                    bx(mb, x0 + 0.002, x0 + 0.012, y0 + pw, y1 - pw, z - 0.035, z, M_GREEN, skip=('z+',))
                elif sd == 'x+':
                    bx(mb, x1 - 0.012, x1 - 0.002, y0 + pw, y1 - pw, z - 0.035, z, M_GREEN, skip=('z+',))
                elif sd == 'y-':
                    bx(mb, x0 + pw, x1 - pw, y0 + 0.002, y0 + 0.012, z - 0.035, z, M_GREEN, skip=('z+',))
                elif sd == 'y+':
                    bx(mb, x0 + pw, x1 - pw, y1 - 0.012, y1 - 0.002, z - 0.035, z, M_GREEN, skip=('z+',))
        hmax = (levels[k + 1] if k + 1 < len(levels) else height + 0.25) - z - 0.07
        for sd in sides:
            if sd in ('x-', 'x+'):
                Wf = WF('x', x0 if sd == 'x-' else x1, -1 if sd == 'x-' else 1)
                half = (x1 - x0) / 2 if len(sides) == 2 else (x1 - x0)
                lo = sorted((a2u('x', Wf.N.x, y0), a2u('x', Wf.N.x, y1)))
                Ml = frame_M(Wf)
                # Wf plane is the rack's outer face; depth goes into the rack (negative d)
                add_slot('%s_%s_l%d' % (name, sd, k), Ml, lo[0] + pw + 0.02, lo[1] - pw - 0.02, z + 0.025, (-half + 0.02, -0.02), hmax, 'stock')
            else:
                Wf = WF('y', y0 if sd == 'y-' else y1, -1 if sd == 'y-' else 1)
                half = (y1 - y0) / 2 if len(sides) == 2 else (y1 - y0)
                lo = sorted((a2u('y', Wf.N.y, x0), a2u('y', Wf.N.y, x1)))
                add_slot('%s_%s_l%d' % (name, sd, k), frame_M(Wf), lo[0] + pw + 0.02, lo[1] - pw - 0.02, z + 0.025, (-half + 0.02, -0.02), hmax, 'stock')
    SUPPORTS.append((name, Vector((0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.0))))


def build_interior(lod):
    mb = MB('PH_Unit_Interior_LOD%d' % lod)
    SHELF_SLOTS.clear()
    flat = lod > 0
    X0, X1, Y0, Y3, PY0, PY1, H = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1, P.H
    CY0, CY1 = P.CY0, P.CY1
    # ---------------- sales: wall shelving (B)
    wall_shelving(mb, 'ShelfL', WF('x', X0, 1), a2u('x', 1, P.LSH[0]), a2u('x', 1, P.LSH[1]), lod)
    ur = sorted((a2u('x', -1, P.RSH[0]), a2u('x', -1, P.RSH[1])))
    wall_shelving(mb, 'ShelfR', WF('x', X1, -1), ur[0], ur[1], lod)
    # back cabinets behind the counter (lower doors + open shelves)
    Wb = WF('y', PY0, -1)
    ub = sorted((a2u('y', -1, P.BC0), a2u('y', -1, P.BC1)))
    n = max(1, round((ub[1] - ub[0]) / 1.55))
    bw = (ub[1] - ub[0]) / n
    whexa(mb, Wb, ub[0], ub[1], 0.025, 0.47, 0.0, 0.08, M_TQP, skip=('z-', 'y-'))
    whexa(mb, Wb, ub[0], ub[1], 0.025, 0.50, 0.08, 0.84, M_TQP, skip=('y-', 'z+') if not flat else ('y-', 'z+'))
    cbar(mb, 'x', P.BC0 - 0.02, P.BC1 + 0.02, PY0 - 0.53, PY0 - 0.025, 0.84, 0.88, 0.01, M_LAM, chamf=(1, 0, 0, 1))
    for i in range(n):
        for j in range(2):
            u0 = ub[0] + i * bw + j * bw / 2 + 0.006
            u1 = u0 + bw / 2 - 0.012
            if flat:
                continue
            inset_panel(mb, Wb, u0, u1, 0.10, 0.82, 0.512, 0.05, 0.010, M_TQP)
            # door thickness edges
            for (a, b) in ((u0, u0), (u1, u1)):
                pass
            hu = u1 - 0.06 if j == 0 else u0 + 0.06
            whexa(mb, Wb, hu - 0.008, hu + 0.008, 0.512, 0.535, 0.62, 0.76, M_METAL)
        if not flat:  # door front plane at 0.50..0.512: fill the reveal between doors
            pass
    # door leaves sit 12 mm proud of the carcass front
    if not flat:
        for i in range(n):
            for j in range(2):
                u0 = ub[0] + i * bw + j * bw / 2 + 0.006
                u1 = u0 + bw / 2 - 0.012
                whexa(mb, Wb, u0, u1, 0.50, 0.512, 0.10, 0.82, M_TQP, skip=('y-', 'y+'))
    up_levels = (0.88, 1.28, 1.66, 2.04)
    wall_shelving_upper(mb, Wb, ub[0], ub[1], n, up_levels, lod)
    # tall locked cabinet in the staff zone (left)
    tx0, tx1 = X0 + 0.03, X0 + 1.0
    bx(mb, tx0, tx1, PY0 - 0.50, PY0 - 0.025, 0.0, 2.0, M_LAM, skip=('z-', 'y+'))
    if not flat:
        Wt = WF('y', PY0 - 0.50, -1)
        for j in range(2):
            u0 = tx0 + 0.02 + j * (tx1 - tx0 - 0.04) / 2 + 0.004
            u1 = u0 + (tx1 - tx0 - 0.04) / 2 - 0.008
            whexa(mb, Wt, u0, u1, 0.0, 0.014, 0.06, 1.94, M_LAM, skip=('y-', 'y+'))
            inset_panel(mb, Wt, u0, u1, 0.06, 1.94, 0.014, 0.05, 0.01, M_LAM)
            hu = u1 - 0.05 if j == 0 else u0 + 0.05
            whexa(mb, Wt, hu - 0.008, hu + 0.008, 0.014, 0.04, 0.95, 1.15, M_METAL, skip=('y-',))
    SUPPORTS.append(('TallCabinet', Vector((0.5 * (tx0 + tx1), PY0 - 0.26, 0.0))))
    # ---------------- counter line: fridge, glass counter, cash desk, staff gate, end cabinet
    build_fridge(mb, lod)
    build_glass_counter(mb, lod)
    build_cash_desk(mb, lod)
    build_gate(mb, lod)
    # ---------------- window display (behind the windows)
    wy0, wy1 = Y0 + 0.02, Y0 + 0.40
    bx(mb, P.XW0, P.XW1, wy0, wy1, 0.0, P.SILL - 0.03, M_TQP, skip=('z-', 'y-', 'z+') + (('y+',) if not flat else ()))
    cbar(mb, 'x', P.XW0, P.XW1, wy0, wy1 + 0.015, P.SILL - 0.03, P.SILL, 0.008, M_LAM, chamf=(0, 1, 1, 0))
    if not flat:
        Ww = WF('y', wy1, 1)
        npn = P.NPANES
        pw = (P.XW1 - P.XW0) / npn
        for i in range(npn):
            uu = sorted((a2u('y', 1, P.XW0 + i * pw), a2u('y', 1, P.XW0 + (i + 1) * pw)))
            inset_panel(mb, Ww, uu[0], uu[1], 0.0, P.SILL - 0.03, 0.0, 0.06, 0.012, M_TQP)
    Mw = frame_M(WF('y', wy0, 1))
    nup = max(2, round((P.XW1 - P.XW0) / 1.4) + 1)
    ups = [P.XW0 + 0.05 + (P.XW1 - P.XW0 - 0.10) * i / (nup - 1) for i in range(nup)]
    for x in ups:
        bx(mb, x - 0.0125, x + 0.0125, wy1 - 0.06, wy1 - 0.035, P.SILL, 1.95, M_METAL, skip=('z-',))
    for z in (1.15, 1.60):
        bx(mb, P.XW0 + 0.03, P.XW1 - 0.03, wy0 + 0.02, wy1 - 0.065, z, z + 0.02, M_LAM)
    for k, z in enumerate((P.SILL, 1.17)):
        for i in range(len(ups) - 1):
            a = ups[i] + 0.03
            b = ups[i + 1] - 0.03
            ua = sorted((a2u('y', 1, a), a2u('y', 1, b)))
            add_slot('Window_%d_%d' % (i, k), Mw, ua[0], ua[1], z, (0.04, 0.27), 0.40, 'window')
    SUPPORTS.append(('WindowDisplay', Vector((0.5 * (P.XW0 + P.XW1), 0.5 * (wy0 + wy1), 0.0))))
    # ---------------- stockroom (A)
    sx = P.STOCK_LW
    ul = sorted((a2u('x', 1, sx[0]), a2u('x', 1, sx[1])))
    steel_rack(mb, 'StockL', X0 + 0.03, X0 + 0.53, sx[0], sx[1], lod, sides=('x+',))
    steel_rack(mb, 'StockR', X1 - 0.53, X1 - 0.03, P.STOCK_RW[0], P.STOCK_RW[1], lod, sides=('x-',))
    steel_rack(mb, 'StockRear', P.STOCK_REAR[0], P.STOCK_REAR[1], Y3 - 0.50, Y3 - 0.03, lod, sides=('y-',), along='x')
    steel_rack(mb, 'RackA', P.RACK_A[0], P.RACK_A[1], P.RACK_Y[0], P.RACK_Y[1], lod)
    steel_rack(mb, 'RackB', P.RACK_B[0], P.RACK_B[1], P.RACK_Y[0], P.RACK_Y[1], lod)
    build_sink(mb, lod)
    # electrical distribution board + conduit (stockroom side of the partition)
    We = WF('y', PY1, 1)
    ue = a2u('y', 1, P.SD0 - 0.80)
    whexa(mb, We, ue - 0.20, ue + 0.20, 0.0, 0.11, 1.35, 1.90, M_METAL, skip=('y-',) if flat else ('y-', 'y+'))
    if not flat:
        inset_panel(mb, We, ue - 0.20, ue + 0.20, 1.35, 1.90, 0.11, 0.035, 0.006, M_METAL)
        whexa(mb, We, ue + 0.12, ue + 0.15, 0.11, 0.125, 1.58, 1.68, M_DARK, skip=('y-',))
        for du in (-0.08, 0.08):
            p0 = We.P(ue + du, 1.90, 0.035)
            mb.cyl(p0, Vector((p0.x, p0.y, H)), 0.014, M_LAM, n=6, caps=(False, False))
            for zc in (2.4, 3.0):
                if zc < H - 0.1:
                    whexa(mb, We, ue + du - 0.02, ue + du + 0.02, 0.0, 0.052, zc - 0.012, zc + 0.012, M_LAM, skip=('y-',))
    SUPPORTS.append(('ElectricBoard', We.P(ue, 1.62, 0.0)))
    return mb


def wall_shelving_upper(mb, Wf, u0, u1, n, levels, lod):
    M = frame_M(Wf)
    bw = (u1 - u0) / n
    d0, d1 = 0.025, 0.36
    top = levels[-1] + 0.30
    for i in range(n + 1):
        u = u0 + i * bw
        a, b = (u, u + 0.05) if i == 0 else ((u - 0.05, u) if i == n else (u - 0.025, u + 0.025))
        whexa(mb, Wf, a, b, d0, d1, 0.88, top, M_TQP, skip=('z-',))
    for i in range(n):
        a = u0 + i * bw + (0.05 if i == 0 else 0.025)
        b = u0 + (i + 1) * bw - (0.05 if i == n - 1 else 0.025)
        for k, z in enumerate(levels[1:]):
            whexa(mb, Wf, a, b, d0 + (0.012 if lod == 0 else 0.0), d1 - 0.005, z, z + 0.025, M_LAM)
        for k, z in enumerate(levels):
            hmax = (levels[k + 1] if k + 1 < len(levels) else top) - z - 0.07
            zz = z + (0.0 if k == 0 else 0.025)
            if k == 0 and i == 0:
                continue  # bay 0 worktop: gloves box + staff items (props)
            add_slot('Back_b%d_l%d' % (i, k), M, a + 0.02, b - 0.02, zz, (d0 + 0.02, d1 - 0.03), hmax, 'pharmacy' if k else 'worktop')
        if lod == 0:
            whexa(mb, Wf, a, b, d0, d0 + 0.012, 0.88, top, M_CREAM, skip=('y-',))
    whexa(mb, Wf, u0 - 0.02, u1 + 0.02, d0, d1 + 0.03, top, top + 0.10, M_TQP)


def build_fridge(mb, lod):
    x0, x1, y0, y1 = P.FX0, P.FX1, P.FY0, P.FY1
    t = 0.05
    bx(mb, x0, x0 + t, y0 + 0.05, y1, 0.0, 1.85, M_TQP, skip=('z-',), mats={'x+': M_LAM})
    bx(mb, x1 - t, x1, y0 + 0.05, y1, 0.0, 1.85, M_TQP, skip=('z-',), mats={'x-': M_LAM})
    bx(mb, x0 + t, x1 - t, y1 - t, y1, 0.12, 1.85, M_TQP, skip=('x-', 'x+'), mats={'y-': M_LAM})
    bx(mb, x0, x1, y0, y1, 1.85, 2.02, M_TQP)
    bx(mb, x0 + t, x1 - t, y0 + 0.05, y1 - t, 0.0, 0.12, M_TQP, skip=('z-', 'x-', 'x+', 'y+'), mats={'z+': M_LAM})
    bx(mb, x0 + 0.004, x1 - 0.004, y0 + 0.055, y0 + 0.09, 0.0, 0.10, M_DARK, skip=('z-',))
    # door frame + glass
    fy0, fy1 = y0, y0 + 0.05
    for (a, b, z0, z1) in ((x0, x0 + 0.06, 0.12, 1.85), (x1 - 0.06, x1, 0.12, 1.85), (x0 + 0.06, x1 - 0.06, 0.12, 0.18),
                           (x0 + 0.06, x1 - 0.06, 1.79, 1.85)):
        bx(mb, a, b, fy0, fy1, z0, z1, M_METAL)
    glass(mb, [(x0 + 0.06, fy0 + 0.025, 0.18), (x1 - 0.06, fy0 + 0.025, 0.18), (x1 - 0.06, fy0 + 0.025, 1.79),
               (x0 + 0.06, fy0 + 0.025, 1.79)], (0, -1, 0))
    mb.face([(x0 + 0.04, y0 - 0.002, 1.88), (x1 - 0.04, y0 - 0.002, 1.88), (x1 - 0.04, y0 - 0.002, 1.98), (x0 + 0.04, y0 - 0.002, 1.98)],
            M_EMIT, want=(0, -1, 0))
    if lod == 0:
        bx(mb, x1 - 0.10, x1 - 0.08, y0 - 0.05, y0 - 0.03, 0.75, 1.35, M_METAL)
        for z in (0.95, 1.15):
            bx(mb, x1 - 0.10, x1 - 0.08, y0 - 0.03, y0, z - 0.01, z + 0.01, M_METAL, skip=('y+',))
    M = frame_M(WF('y', y0 + 0.05, -1))
    for k, z in enumerate((0.12, 0.52, 0.90, 1.28)):
        if k:
            bx(mb, x0 + t, x1 - t, y0 + 0.06, y1 - t - 0.005, z - 0.012, z, M_METAL, skip=('x-', 'x+'))
        ua = sorted((a2u('y', -1, x0 + t + 0.02), a2u('y', -1, x1 - t - 0.02)))
        add_slot('Fridge_l%d' % k, M, ua[0], ua[1], z, (-0.55, -0.08), 0.32, 'fridge')
    # internal light strip under the top
    mb.face([(x0 + t, y0 + 0.08, 1.849), (x1 - t, y0 + 0.08, 1.849), (x1 - t, y0 + 0.14, 1.849), (x0 + t, y0 + 0.14, 1.849)],
            M_EMIT, want=(0, 0, -1))
    SUPPORTS.append(('Fridge', Vector((0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.0))))


def build_glass_counter(mb, lod):
    x0, x1, y0, y1 = P.GC0, P.GC1, P.CY0, P.CY1
    flat = lod > 0
    bx(mb, x0 + 0.04, x1, y0 + 0.07, y1 - 0.03, 0.0, 0.10, M_RUB, skip=('z-', 'x+', 'z+'))
    nsec = max(1, round((x1 - x0) / 2.2))
    sw_ = (x1 - x0) / nsec
    Wf = WF('y', y0, -1)
    if flat:
        bx(mb, x0, x1, y0, y1, 0.10, 0.42, M_TQP, skip=('z+', 'x+'))
    else:
        bx(mb, x0, x1, y0, y1, 0.10, 0.42, M_TQP, skip=('z+', 'x+', 'y-'))
        for i in range(nsec):
            inset_panel(mb, Wf, x0 + i * sw_, x0 + (i + 1) * sw_, 0.10, 0.42, 0.0, 0.05, 0.012, M_TQP)
    bx(mb, x0, x1, y0, y1, 0.42, 0.45, M_LAM, skip=('z-', 'x+'))
    posts = [x0 + i * sw_ for i in range(nsec + 1)]
    for i, x in enumerate(posts):
        a, b = (x, x + 0.04) if i == 0 else ((x - 0.04, x) if i == nsec else (x - 0.02, x + 0.02))
        bx(mb, a, b, y0, y1, 0.45, 0.95, M_METAL, skip=('z-', 'z+'))
    for i in range(nsec):
        a = posts[i] + (0.04 if i == 0 else 0.02)
        b = posts[i + 1] - (0.04 if i == nsec - 1 else 0.02)
        glass(mb, [(a, y0 + 0.012, 0.465), (b, y0 + 0.012, 0.465), (b, y0 + 0.012, 0.935), (a, y0 + 0.012, 0.935)], (0, -1, 0))
        glass(mb, [(a, y1 - 0.012, 0.465), (b, y1 - 0.012, 0.465), (b, y1 - 0.012, 0.935), (a, y1 - 0.012, 0.935)], (0, 1, 0))
        if not flat:  # aluminium channels holding the glass (top + bottom, both faces)
            for yy0, yy1 in ((y0 - 0.002, y0 + 0.026), (y1 - 0.026, y1 + 0.002)):
                bx(mb, a, b, yy0, yy1, 0.45, 0.465, M_METAL, skip=('z-', 'x-', 'x+'))
                bx(mb, a, b, yy0, yy1, 0.935, 0.95, M_METAL, skip=('z+', 'x-', 'x+'))
            # sliding-door pulls on the staff side
            for xm in (a + 0.25, b - 0.25):
                bx(mb, xm - 0.04, xm + 0.04, y1 + 0.002, y1 + 0.012, 0.66, 0.72, M_METAL, skip=('y-',))
        bx(mb, a, b, y0 + 0.05, y1 - 0.05, 0.68, 0.70, M_LAM)
        M = frame_M(WF('y', y0, -1))
        ua = sorted((a2u('y', -1, a + 0.03), a2u('y', -1, b - 0.03)))
        add_slot('Vitrine_%d_lo' % i, M, ua[0], ua[1], 0.45, (-0.50, -0.10), 0.18, 'vitrine')
        add_slot('Vitrine_%d_hi' % i, M, ua[0], ua[1], 0.70, (-0.50, -0.10), 0.20, 'vitrine')
    cbar(mb, 'x', x0 - 0.02, x1, y0 - 0.03, y1, 0.95, P.CTOP, 0.012, M_LAM, chamf=(1, 0, 0, 1), caps=(True, False))
    SUPPORTS.append(('GlassCounter', Vector((0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.0))))


def offset_poly(poly, d):
    """Offset a convex CCW polygon outward by d (miter)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((e0.y, -e0.x))
        n1 = Vector((e1.y, -e1.x))
        m = (n0 + n1).normalized()
        s = d / max(0.2, m.dot(n0))
        q = p1 + m * s
        out.append((q.x, q.y))
    return out


def build_cash_desk(mb, lod):
    x0, x1, y0, y1 = P.CD0, P.GT0, P.CY0, P.CY1
    ch = 0.35
    poly = [(x0, y0), (x1 - ch, y0), (x1, y0 + ch), (x1, y1), (x0, y1)]
    fr = lambda s, t, w: Vector((s, t, w))
    mb.prism(offset_poly(poly, -0.05), 0.0, 0.08, M_RUB, fr, caps=(False, False), skip_sides=(4,))
    mb.prism(poly, 0.08, P.DTOP, M_TQP, fr, caps=(True, False), skip_sides=(4, 3))
    mb.prism(offset_poly(poly, 0.03), P.DTOP, P.DTOP + 0.05, M_LAM, fr, caps=(True, True), skip_sides=(4,))
    if lod == 0:
        mb.prism(offset_poly(poly, 0.015), 0.86, 0.90, M_LAM, fr, caps=(True, True), skip_sides=(4,))
        mb.prism(offset_poly(poly, 0.012), 0.22, 0.25, M_LAM, fr, caps=(True, True), skip_sides=(4,))
    # staff-side under-counter shelf (open niche look): a shelf board on the back face
    Wd = WF('y', y1, 1)
    ua = sorted((a2u('y', 1, x0 + 0.04), a2u('y', 1, x1 - 0.04)))
    nd = 3
    dw = (ua[1] - ua[0]) / nd
    for i in range(nd):
        for j, (z0, z1) in enumerate(((0.12, 0.46), (0.48, 0.66), (0.68, 0.84))):
            u0, u1 = ua[0] + i * dw + 0.004, ua[0] + (i + 1) * dw - 0.004
            whexa(mb, Wd, u0, u1, 0.0, 0.018, z0, z1, M_TQP, skip=('y-',))
            if lod == 0:
                um = 0.5 * (u0 + u1)
                whexa(mb, Wd, um - 0.07, um + 0.07, 0.018, 0.034, z1 - 0.05, z1 - 0.03, M_METAL, skip=('y-',))
    SUPPORTS.append(('CashDesk', Vector((0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.0))))


def build_gate(mb, lod):
    g0, g1, y0, y1 = P.GT0, P.GT1, P.CY0, P.CY1
    gy = 0.5 * (y0 + y1)
    # hinge post (at the end cabinet) and latch post (at the cash desk)
    bx(mb, g1 - 0.05, g1, gy - 0.04, gy + 0.04, 0.0, 1.02, M_METAL, skip=('z-', 'x+'))
    bx(mb, g0, g0 + 0.04, gy - 0.04, gy + 0.04, 0.08, 0.95, M_METAL, skip=('x-',))
    # gate leaf: framed panel
    a, b = g0 + 0.05, g1 - 0.06
    Wg = WF('y', gy - 0.02, -1)
    bx(mb, a, b, gy - 0.02, gy + 0.02, 0.10, 1.00, M_TQP, skip=('y-',) if lod == 0 else ())
    if lod == 0:
        inset_panel(mb, Wg, a, b, 0.10, 1.00, 0.0, 0.06, 0.012, M_TQP)
    cbar(mb, 'x', a - 0.005, b + 0.005, gy - 0.03, gy + 0.03, 1.00, 1.04, 0.01, M_LAM)
    label_quad(mb, Wg, a + 0.5 * (b - a) - 0.16, a + 0.5 * (b - a) + 0.16, 0.62, 0.78, 0.003, 'staff_only')
    # end cabinet to the right wall
    bx(mb, g1, P.X1 - 0.02, y0, y1, 0.08, 1.0, M_TQP, skip=('z-', 'x-'))
    bx(mb, g1, P.X1 - 0.02, y0 + 0.06, y1 - 0.03, 0.0, 0.08, M_RUB, skip=('z-', 'x-', 'z+'))
    cbar(mb, 'x', g1, P.X1 - 0.02, y0 - 0.03, y1, 1.0, 1.04, 0.012, M_LAM, chamf=(1, 0, 0, 1), caps=(False, True))
    SUPPORTS.append(('EndCabinet', Vector((0.5 * (g1 + P.X1), 0.5 * (y0 + y1), 0.0))))


def build_sink(mb, lod):
    flat = lod > 0
    Y3 = P.Y3
    cx = P.SKX
    x0, x1 = cx - 0.28, cx + 0.28
    yb, yf = Y3, Y3 - 0.46
    z0, z1, zb = 0.66, 0.86, 0.73
    # basin: outer shell, rim, bowl
    bx(mb, x0, x1, yf, yb - 0.003, z0, z1, M_CER, skip=('z+', 'y+'))
    if flat:
        mb.face([(x0, yf, z1), (x1, yf, z1), (x1, yb - 0.003, z1), (x0, yb - 0.003, z1)], M_CER, want=(0, 0, 1))
    else:
        r = 0.045
        ix0, ix1, iyf, iyb = x0 + r, x1 - r, yf + r, yb - 0.003 - 0.10
        ring = [((x0, yf), (x1, iyf)), ((x0, iyb), (x1, yb - 0.003)), ((x0, iyf), (ix0, iyb)), ((ix1, iyf), (x1, iyb))]
        for (a, b) in ring:
            mb.face([(a[0], a[1], z1), (b[0], a[1], z1), (b[0], b[1], z1), (a[0], b[1], z1)], M_CER, want=(0, 0, 1))
        mb.face([(ix0, iyf, zb), (ix1, iyf, zb), (ix1, iyb, zb), (ix0, iyb, zb)], M_CER, want=(0, 0, 1))
        mb.face([(ix0, iyf, zb), (ix1, iyf, zb), (ix1, iyf, z1), (ix0, iyf, z1)], M_CER, want=(0, 1, 0))
        mb.face([(ix0, iyb, zb), (ix1, iyb, zb), (ix1, iyb, z1), (ix0, iyb, z1)], M_CER, want=(0, -1, 0))
        mb.face([(ix0, iyf, zb), (ix0, iyb, zb), (ix0, iyb, z1), (ix0, iyf, z1)], M_CER, want=(1, 0, 0))
        mb.face([(ix1, iyf, zb), (ix1, iyb, zb), (ix1, iyb, z1), (ix1, iyf, z1)], M_CER, want=(-1, 0, 0))
        mb.cyl((cx, 0.5 * (iyf + iyb), zb - 0.004), (cx, 0.5 * (iyf + iyb), zb + 0.003), 0.03, M_METAL, n=8, caps=(False, True))
    # brackets (triangular steel)
    for xb in (x0 + 0.08, x1 - 0.08):
        tri = [(0.0, 0.0), (0.0, 0.24), (0.36, 0.24)]
        frame = lambda s, t, w, xb=xb: Vector((xb + w, Y3 - s, z0 - 0.24 + t))
        mb.prism([(0.0, 0.0), (0.36, 0.24), (0.0, 0.24)], -0.012, 0.012, M_METAL, frame)
    # tap + supply pipes
    ty = Y3 - 0.03
    bx(mb, cx - 0.06, cx + 0.06, Y3 - 0.06, Y3, 0.95, 1.01, M_METAL, skip=('y+',))
    mb.tube([(cx, Y3 - 0.05, 0.98), (cx, Y3 - 0.20, 0.98), (cx, Y3 - 0.20, 0.93)], 0.011, M_METAL, n=6)
    if not flat:
        bx(mb, cx - 0.01, cx + 0.01, Y3 - 0.05, Y3 - 0.03, 1.01, 1.04, M_METAL)
        bx(mb, cx - 0.01, cx + 0.07, Y3 - 0.05, Y3 - 0.03, 1.04, 1.055, M_METAL)
        for px in (cx + 0.10, cx + 0.15):
            mb.tube([(cx + 0.04, ty, 0.98 if px < cx + 0.12 else 0.965), (px, ty, 0.98 if px < cx + 0.12 else 0.965), (px, ty, P.H)], 0.011, M_METAL, n=6, caps=(False, False))
            for z in (1.6, 2.3, 3.0):
                if z < P.H - 0.1:
                    bx(mb, px - 0.02, px + 0.02, Y3 - 0.012, Y3, z - 0.015, z + 0.015, M_METAL, skip=('y+',))
        # P-trap into the wall
        dy = Y3 - 0.20
        mb.tube([(cx, dy, z0 + 0.002), (cx, dy, 0.48), (cx, dy + 0.07, 0.43), (cx, dy + 0.12, 0.48), (cx, dy + 0.12, 0.52), (cx, Y3, 0.52)], 0.022, M_METAL, n=8,
                caps=(False, False))
        bx(mb, cx - 0.05, cx + 0.05, Y3 - 0.012, Y3, 0.47, 0.57, M_METAL, skip=('y+',))
        # towel hook
        hx = x0 - 0.18
        bx(mb, hx - 0.02, hx + 0.02, Y3 - 0.012, Y3, 1.50, 1.58, M_METAL, skip=('y+',))
        mb.tube([(hx, Y3 - 0.012, 1.54), (hx, Y3 - 0.06, 1.54), (hx, Y3 - 0.07, 1.58)], 0.007, M_METAL, n=6)
    SUPPORTS.append(('Sink', Vector((cx, Y3 - 0.2, 0.0))))


# ============================================================================ doors (separate objects, pivot = hinge, closed)
def door_leaf(mb, w, h, t, front_mat, back_mat, edge_mat, lod, kick=True, handle_side=-1):
    """Leaf from the hinge at x=0 extending to x=-w; front faces -y."""
    bx(mb, -w, 0.0, -t / 2, t / 2, 0.0, h, edge_mat, mats={'y-': front_mat, 'y+': back_mat})
    if lod == 0 and kick:
        for sg in (-1, 1):
            y = sg * (t / 2)
            bx(mb, -w + 0.04, -0.04, y if sg > 0 else y - 0.003, y + 0.003 if sg > 0 else y, 0.03, 0.25, M_METAL,
               skip=('y+',) if sg < 0 else ('y-',))
    # lever handles both sides + rose
    hx = -w + 0.08
    for sg in (-1, 1):
        y = sg * (t / 2)
        d = sg
        bx(mb, hx - 0.035, hx + 0.035, y if d > 0 else y - 0.012, y + 0.012 if d > 0 else y, 0.92, 1.10, M_METAL,
           skip=('y+',) if d < 0 else ('y-',))
        mb.cyl((hx, y + d * 0.012, 1.04), (hx, y + d * 0.06, 1.04), 0.011, M_METAL, n=6, caps=(False, False))
        mb.cyl((hx, y + d * 0.06, 1.04), (hx + 0.13, y + d * 0.06, 1.04), 0.0085, M_METAL, n=6)
    for z in (0.2, h - 0.25):
        mb.cyl((0.008, 0.0, z), (0.008, 0.0, z + 0.12), 0.012, M_DARK, n=6)


def build_door_staff(lod=0):
    mb = MB('Door_Staff')
    w, h, t = P.SDW - 0.01, P.SDH - 0.015, 0.045
    door_leaf(mb, w, h, t, M_TQP, M_GREEN, M_OFF, lod)
    Wf = Wall((0, -t / 2, 0), (1, 0, 0), (0, -1, 0))
    label_quad(mb, Wf, -w / 2 - 0.20, -w / 2 + 0.20, 1.42, 1.62, 0.004, 'staff_only')
    bx(mb, -w / 2 - 0.21, -w / 2 + 0.21, -t / 2 - 0.004, -t / 2, 1.41, 1.63, M_OFF, skip=('y+', 'y-'))
    bx(mb, -0.30, -0.05, t / 2, t / 2 + 0.05, h - 0.10, h - 0.04, M_METAL, skip=('y-',))  # closer on the stock side
    return mb


def build_door_rear(lod=0):
    mb = MB('Door_Rear')
    w, h, t = P.RDW - 0.12 - 0.01, P.RDH - 0.06 - 0.01, 0.05
    door_leaf(mb, w, h, t, M_GREEN, M_GREEN, M_GREEN, lod)
    if lod == 0:  # pressed panels on the courtyard face
        Wf = Wall((0, t / 2, 0), (-1, 0, 0), (0, 1, 0))
        for (z0, z1) in ((0.35, 1.0), (1.20, h - 0.15)):
            whexa(mb, Wf, 0.10, w - 0.10, 0.0, 0.007, z0, z1, M_GREEN, skip=('y-',))
            whexa(mb, Wf, 0.16, w - 0.16, 0.007, 0.011, z0 + 0.06, z1 - 0.06, M_GREEN, skip=('y-',))
        bx(mb, -0.35, -0.05, -t / 2 - 0.05, -t / 2, h - 0.10, h - 0.04, M_METAL, skip=('y+',))
    return mb


def build_door_street(lod=0):
    mb = MB('Door_Street')
    w, h, t = P.DOOR_W - 0.02, P.DH - 0.01, 0.05
    st, tr, br = 0.09, 0.09, 0.24
    for (a, b, z0, z1) in ((-w, -w + st, 0.0, h), (-st, 0.0, 0.0, h), (-w + st, -st, 0.0, br), (-w + st, -st, h - tr, h)):
        bx(mb, a, b, -t / 2, t / 2, z0, z1, M_GB)
    glass(mb, [(-w + st, 0.0, br), (-st, 0.0, br), (-st, 0.0, h - tr), (-w + st, 0.0, h - tr)], (0, -1, 0))
    # push bars both sides
    for sg in (-1, 1):
        y = sg * (t / 2 + 0.05)
        mb.cyl((-w + 0.12, y, 1.02), (-0.12, y, 1.02), 0.016, M_METAL, n=8)
        for x in (-w + 0.15, -0.15):
            mb.cyl((x, sg * t / 2, 1.02), (x, y, 1.02), 0.012, M_METAL, n=6, caps=(False, False))
    for z in (0.25, h - 0.3):
        mb.cyl((0.008, 0.0, z), (0.008, 0.0, z + 0.12), 0.012, M_DARK, n=6)
    return mb


DOORS = {
    'Door_Staff': dict(builder=build_door_staff, hinge=(P.SD1 - 0.005, 0.5 * (P.PY0 + P.PY1), 0.005), open_yaw_blender=-90.0,
                       opens_into='stockroom (+Y Blender / -Z Unity)', state='closed, locked for the player; staff NPCs may open it',
                       clear_w=P.SDW, clear_h=P.SDH),
    'Door_Street': dict(builder=build_door_street, hinge=(P.DO1 - 0.005, P.GY, 0.005), open_yaw_blender=-90.0,
                        opens_into='sales floor (inward)', state='closed in the FBX; player-openable / auto-open shop door',
                        clear_w=P.DOOR_W, clear_h=P.DH),
    'Door_Rear': dict(builder=build_door_rear, hinge=(P.RD1 - 0.065, P.D - 0.08, 0.005), open_yaw_blender=-95.0,
                      opens_into='courtyard (outward)', state='closed in the FBX; openable from the courtyard and from inside',
                      clear_w=P.RDW - 0.12, clear_h=P.RDH - 0.06),
}


def door_ucx(name):
    if name == 'Door_Staff':
        w, h, t = P.SDW - 0.01, P.SDH - 0.015, 0.06
    elif name == 'Door_Rear':
        w, h, t = P.RDW - 0.13, P.RDH - 0.07, 0.07
    else:
        w, h, t = P.DOOR_W - 0.02, P.DH - 0.01, 0.07
    return [Vector((x, y, z)) for x in (-w, 0.0) for y in (-t / 2, t / 2) for z in (0.0, h)]


# ============================================================================ unit colliders
def unit_colliders():
    HW, D, H = P.HW, P.D, P.H
    X0, X1, Y0, Y3, PY0, PY1 = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1
    top = H + P.SLAB
    ucx_box((-HW, 0.0, -0.30), (HW, D, 0.0))                                   # floor slab
    ucx_box((-HW, -0.05, H), (HW, D, top))                                     # ceiling slab
    ucx_box((P.DO0 - 0.30, -0.42, -0.35), (P.DO1 + 0.30, 0.0, 0.0))            # street step
    # storefront: everything except the door opening (glass blocks)
    ucx_box((-HW, -0.05, 0.0), (P.DO0, Y0, P.FH))
    ucx_box((P.DO1, -0.05, 0.0), (HW, Y0, P.FH))
    ucx_box((P.DO0, -0.05, P.DH), (P.DO1, Y0, P.FH))
    ucx_box((-HW, -0.20, P.OH), (HW, Y0, P.FH))
    # side walls, rear wall (door open), partition (staff door open: Door_Staff has its own collider)
    ucx_box((-HW, Y0, 0.0), (X0, Y3, top))
    ucx_box((X1, Y0, 0.0), (HW, Y3, top))
    ucx_box((-HW, Y3, 0.0), (P.RD0 + 0.06, D, top))
    ucx_box((P.RD1 - 0.06, Y3, 0.0), (HW, D, top))
    ucx_box((P.RD0, Y3, P.RDH - 0.06), (P.RD1, D, top))
    ucx_box((X0, PY0, 0.0), (P.SD0, PY1, H))
    ucx_box((P.SD1, PY0, 0.0), (X1, PY1, H))
    ucx_box((P.SD0, PY0, P.SDH), (P.SD1, PY1, H))
    # rear landing ramp
    lx0, lx1, ly1 = P.RD0 - 0.45, P.RD1 + 0.45, D + 1.40
    UCX.append([Vector(p) for p in ((lx0, D, 0.0), (lx1, D, 0.0), (lx0, ly1, -0.12), (lx1, ly1, -0.12),
                                    (lx0, D, -0.45), (lx1, D, -0.45), (lx0, ly1, -0.45), (lx1, ly1, -0.45))])
    # counter line: fridge, glass counter, cash desk (convex prism), gate, end cabinet
    ucx_box((P.FX0, P.FY0 - 0.05, 0.0), (P.FX1, P.FY1, 2.02))
    ucx_box((P.GC0 - 0.02, P.CY0 - 0.03, 0.0), (P.GC1, P.CY1, P.CTOP))
    ch = 0.35
    poly = offset_poly([(P.CD0, P.CY0), (P.GT0 - ch, P.CY0), (P.GT0, P.CY0 + ch), (P.GT0, P.CY1), (P.CD0, P.CY1)], 0.03)
    UCX.append([Vector((x, y, z)) for x, y in poly for z in (0.0, P.DTOP + 0.05)])
    ucx_box((P.GT0, P.CY0 + 0.27, 0.0), (P.GT1, P.CY1 - 0.27, 1.04))
    ucx_box((P.GT1, P.CY0 - 0.03, 0.0), (X1, P.CY1, 1.04))
    # wall shelving, cabinets, window display
    ucx_box((X0, P.LSH[0], 0.0), (X0 + 0.025 + P.SHELF_D, P.LSH[1], P.SHELF_H + 0.10))
    ucx_box((X1 - 0.025 - P.SHELF_D, P.RSH[0], 0.0), (X1, P.RSH[1], P.SHELF_H + 0.10))
    ucx_box((P.BC0 - 0.02, PY0 - 0.53, 0.0), (P.BC1 + 0.02, PY0, 0.88))
    ucx_box((P.BC0 - 0.02, PY0 - 0.39, 0.88), (P.BC1 + 0.02, PY0, 2.44))
    ucx_box((X0, PY0 - 0.50, 0.0), (X0 + 1.0, PY0, 2.0))
    ucx_box((P.XW0, Y0, 0.0), (P.XW1, Y0 + 0.415, 1.97))
    # stockroom
    ucx_box((X0, P.STOCK_LW[0], 0.0), (X0 + 0.53, P.STOCK_LW[1], 2.0))
    ucx_box((X1 - 0.53, P.STOCK_RW[0], 0.0), (X1, P.STOCK_RW[1], 2.0))
    ucx_box((P.STOCK_REAR[0], Y3 - 0.50, 0.0), (P.STOCK_REAR[1], Y3, 2.0))
    ucx_box((P.RACK_A[0], P.RACK_Y[0], 0.0), (P.RACK_A[1], P.RACK_Y[1], 2.0))
    ucx_box((P.RACK_B[0], P.RACK_Y[0], 0.0), (P.RACK_B[1], P.RACK_Y[1], 2.0))
    ucx_box((P.SKX - 0.30, Y3 - 0.47, 0.40), (P.SKX + 0.30, Y3, 1.06))


# ============================================================================ props
PROPS = []   # dict(name, mb0, mb1, loc, rot, ucx(local boxes), items(local support points), area, meta)


def add_prop(name, builder, loc, rot=0.0, area='sales', collide=False, meta=None, **kw):
    mb0, ucx, items = builder(0, **kw)
    mb1 = None
    if mb0.tris() > 500:
        mb1 = builder(1, **kw)[0]
    PROPS.append(dict(name=name, mb0=mb0, mb1=mb1, loc=Vector(loc), rot=rot, ucx=ucx if collide else [], items=items, area=area,
                      meta=meta or {}))


def cyl_uv(mb, p0, p1, r, mat, n, rect, caps=(False, True), cap_rect=None, M=None):
    """Upright/any-axis cylinder whose side wraps an atlas rect (u around, v along)."""
    M = M or Matrix.Identity(4)
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((0, -1, 0))
    u = ax.cross(ref).normalized()
    v = ax.cross(u).normalized()
    R = M.to_3x3()
    ring0, ring1, nrm = [], [], []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        d = u * math.cos(a) + v * math.sin(a)
        ring0.append(M @ (p0 + d * r))
        ring1.append(M @ (p1 + d * r))
        nrm.append((R @ d).normalized())
    for i in range(n):
        uv0 = rect[0] + (rect[2] - rect[0]) * i / n
        uv1 = rect[0] + (rect[2] - rect[0]) * (i + 1) / n
        mb.face([ring0[i], ring0[i + 1], ring1[i + 1], ring1[i]], mat, want=(nrm[i] + nrm[i + 1]),
                normals=[nrm[i], nrm[i + 1], nrm[i + 1], nrm[i]], uvs=[(uv0, rect[1]), (uv1, rect[1]), (uv1, rect[3]), (uv0, rect[3])])
    cr = cap_rect or rect
    cu = [(0.5 * (cr[0] + cr[2]) + 0.3 * (cr[2] - cr[0]) * math.cos(2 * math.pi * i / n),
           0.5 * (cr[1] + cr[3]) + 0.3 * (cr[3] - cr[1]) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    if caps[0]:
        mb.face(ring0[:n], mat, want=R @ -ax, uvs=cu)
    if caps[1]:
        mb.face(ring1[:n], mat, want=R @ ax, uvs=cu)


PKG = ['pkg_%d' % i for i in range(8)]
PKG_SIDE = {0: 'teal', 1: 'orange', 2: 'blue', 3: 'green', 4: 'teal_dark', 5: 'orange', 6: 'blue', 7: 'green'}
BOTTLES = ['bottle_%d' % i for i in range(4)]


def fill_slot(mb, rnd, slot, lod, items):
    """Products on one shelf slot (shelf-local frame: x along, y into the wall = -d, z up)."""
    M = slot['M']
    u0, u1, z = slot['u0'], slot['u1'], slot['z']
    dn, dfar = slot['depth']        # d range measured from the wall plane into the room (d_near_wall, d_front)
    hmax = slot['hmax']
    style = slot['style']
    u = u0 + rnd.uniform(0.0, 0.05)
    while u < u1 - 0.06:
        kind = rnd.random()
        if style == 'stock':
            w = rnd.uniform(0.30, 0.45)
            if u + w > u1:
                break
            dep = min(dfar - dn, rnd.uniform(0.30, 0.42))
            h = min(hmax, rnd.uniform(0.22, 0.32))
            front = dfar if dfar > dn else dn
            if rnd.random() < 0.72:
                rects = {'y-': RG['carton_side'], 'z+': RG['carton_top']}
                mb.box((u, -front, z), (u + w, -front + dep, z + h), M_CARD, M=M, skip=('z-',),
                       mats={'y-': M_LAB, 'z+': M_LAB}, rects=rects)
            else:
                k = rnd.randrange(8)
                hw = min(h, 0.18)
                mb.box((u, -front, z), (u + w * 0.6, -front + dep * 0.7, z + hw), M_LAB, M=M, skip=('z-',),
                       rects=all_rects(PKG[k], PKG_SIDE[k], 'white'))
                w = w * 0.6
            items.append(M @ Vector((u + w / 2, -front + dep / 2, z)))
            u += w + rnd.uniform(0.02, 0.07)
            continue
        if style == 'fridge':
            r = rnd.uniform(0.036, 0.046)
            h = min(hmax, rnd.uniform(0.20, 0.27))
            c = Vector((u + r, -(dfar + 0.0) * 0.5 - 0.5 * dn, z)) if False else Vector((u + r, -(0.5 * (dn + dfar)), z))
            cyl_uv(mb, c, c + Vector((0, 0, h * 0.78)), r, M_LAB, 6, RG['bottle_%d' % rnd.randrange(4)], M=M,
                   caps=(False, False))
            cyl_uv(mb, c + Vector((0, 0, h * 0.78)), c + Vector((0, 0, h)), r * 0.45, M_LAB, 4, sw('clear'), M=M, caps=(False, True))
            mb.face([M @ (c + Vector((r * math.cos(2 * math.pi * i / 6), r * math.sin(2 * math.pi * i / 6), h * 0.78))) for i in range(6)],
                    M_LAB, want=M.to_3x3() @ ZV, uvs=[(sw('clear')[0], sw('clear')[1])] * 6)
            items.append(M @ c)
            u += 2 * r + rnd.uniform(0.01, 0.03)
            continue
        if kind < (0.28 if style != 'vitrine' else 0.0) and hmax > 0.14:
            r = rnd.uniform(0.028, 0.042)
            h = min(hmax - 0.02, rnd.uniform(0.10, 0.17))
            dc = dfar - r - 0.01
            c = Vector((u + r, -dc, z))
            amber = rnd.random() < 0.35
            cyl_uv(mb, c, c + Vector((0, 0, h * 0.8)), r, M_LAB, 6 if lod else 8,
                   sw('amber') if amber else RG[BOTTLES[rnd.randrange(4)]], M=M, caps=(False, False))
            capc = rnd.choice(['white', 'dark', 'teal', 'orange'])
            cyl_uv(mb, c + Vector((0, 0, h * 0.8)), c + Vector((0, 0, h)), r * 0.7, M_LAB, 6, sw(capc), M=M, caps=(False, True))
            mb.face([M @ (c + Vector((r * math.cos(2 * math.pi * i / 6), r * math.sin(2 * math.pi * i / 6), h * 0.8))) for i in range(6)],
                    M_LAB, want=M.to_3x3() @ ZV, uvs=[(sw('white')[0], sw('white')[1])] * 6)
            items.append(M @ c)
            u += 2 * r + rnd.uniform(0.012, 0.03)
        else:
            w = rnd.uniform(0.09, 0.19)
            if u + w > u1:
                break
            h = min(hmax, rnd.uniform(0.07, 0.20 if style != 'vitrine' else 0.12))
            dep = min(dfar - dn - 0.01, rnd.uniform(0.07, 0.16))
            k = rnd.randrange(8)
            stack = 2 if (style in ('pharmacy', 'window') and h < 0.11 and hmax > 2.3 * h and rnd.random() < 0.5) else 1
            for s_ in range(stack):
                zz = z + s_ * h
                mb.box((u, -dfar, zz), (u + w, -dfar + dep, zz + h), M_LAB, M=M, skip=('z-', 'y+'),
                       rects=all_rects(PKG[k], PKG_SIDE[k], 'white'))
                items.append(M @ Vector((u + w / 2, -dfar + dep / 2, zz)))
            u += w + (rnd.uniform(0.06, 0.20) if style == 'window' else rnd.uniform(0.008, 0.03))


def P_fill(lod, slots=None, seed=1):
    mb = MB('fill')
    items = []
    rnd = random.Random(seed)
    for s in slots:
        fill_slot(mb, rnd, s, lod, items)
    return mb, [], items


def tray(mb, x0, x1, y0, y1, z, h, mat=M_OFF, t=0.008):
    bx(mb, x0, x1, y0, y1, z, z + 0.006, mat)
    bx(mb, x0, x1, y0, y0 + t, z + 0.006, z + h, mat, skip=('z-',))
    bx(mb, x0, x1, y1 - t, y1, z + 0.006, z + h, mat, skip=('z-',))
    bx(mb, x0, x0 + t, y0 + t, y1 - t, z + 0.006, z + h, mat, skip=('z-', 'y-', 'y+'))
    bx(mb, x1 - t, x1, y0 + t, y1 - t, z + 0.006, z + h, mat, skip=('z-', 'y-', 'y+'))


def P_syringes(lod, kind='blood'):
    mb = MB('syr')
    tray(mb, -0.17, 0.17, -0.12, 0.12, 0.0, 0.035)
    lab = RG['lbl_syringe_' + ('blood' if kind == 'blood' else 'anaesthesia')]
    tip = 'plunger_red' if kind == 'blood' else 'plunger_blue'
    for i in range(3):
        for j in range(2):
            x = -0.11 + i * 0.11
            y = -0.055 + j * 0.11
            z0 = 0.006 + j * 0.0
            bx(mb, x - 0.045, x + 0.045, y - 0.05, y + 0.05, z0, z0 + 0.010, M_LAB, rects=all_rects(lab, 'paper', lab))
            if lod == 0:
                cyl_uv(mb, (x - 0.035, y, z0 + 0.019), (x + 0.025, y, z0 + 0.019), 0.008, M_LAB, 6, sw('clear'), caps=(True, True))
                cyl_uv(mb, (x + 0.025, y, z0 + 0.019), (x + 0.045, y, z0 + 0.019), 0.004, M_LAB, 4, sw(tip), caps=(False, True))
                cyl_uv(mb, (x - 0.045, y, z0 + 0.019), (x - 0.035, y, z0 + 0.019), 0.010, M_LAB, 6, sw(tip), caps=(True, False))
    return mb, [], [Vector((0, 0, 0))]


def P_vials(lod):
    mb = MB('vials')
    tray(mb, -0.14, 0.14, -0.10, 0.10, 0.0, 0.025, mat=M_METAL)
    for i in range(4):
        for j in range(3):
            c = Vector((-0.09 + i * 0.06, -0.055 + j * 0.055, 0.006))
            n = 6
            cyl_uv(mb, c, c + Vector((0, 0, 0.042)), 0.015, M_LAB, n, RG['lbl_vial'], caps=(False, False))
            cyl_uv(mb, c + Vector((0, 0, 0.042)), c + Vector((0, 0, 0.050)), 0.008, M_LAB, 4, sw('clear'), caps=(False, False))
            cyl_uv(mb, c + Vector((0, 0, 0.050)), c + Vector((0, 0, 0.060)), 0.011, M_LAB, 6, sw('green'), caps=(False, True))
            mb.face([c + Vector((0.015 * math.cos(2 * math.pi * k / n), 0.015 * math.sin(2 * math.pi * k / n), 0.042)) for k in range(n)],
                    M_LAB, want=(0, 0, 1), uvs=[(sw('clear')[0], sw('clear')[1])] * n)
    return mb, [], [Vector((0, 0, 0))]


def P_cable_ties_loose(lod):
    mb = MB('ties')
    tray(mb, -0.13, 0.13, -0.09, 0.09, 0.0, 0.03, mat=M_DARK)
    rnd = random.Random(5)
    for k in range(10):
        a = rnd.uniform(-12, 12)
        Mx = T(rnd.uniform(-0.02, 0.02), -0.06 + k * 0.013, 0.006 + 0.0023 * k) @ RZ(a)
        bx(mb, -0.10, 0.10, -0.0025, 0.0025, 0.0, 0.003, M_DARK, M=Mx, skip=('z-',))
        bx(mb, 0.10, 0.11, -0.004, 0.004, 0.0, 0.006, M_DARK, M=Mx, skip=('z-',))
    return mb, [], [Vector((0, 0, 0))]


def P_cable_tie_packs(lod):
    mb = MB('tiepacks')
    for k in range(3):
        Mx = T(-0.12 + k * 0.12, 0.0 + 0.01 * k, 0.0 + 0.0) @ RZ(-4 + 4 * k)
        bx(mb, -0.05, 0.05, -0.13, 0.11, 0.0, 0.018, M_LAB, M=Mx, rects=all_rects(sw('clear'), 'clear', sw('clear')), skip=('z-',))
        bx(mb, -0.052, 0.052, -0.17, -0.13, 0.0, 0.004, M_LAB, M=Mx, rects=all_rects(RG['lbl_cable_ties'], 'white', RG['lbl_cable_ties']), skip=('z-',))
        for j in range(4):
            x = -0.03 + j * 0.02
            bx(mb, x - 0.003, x + 0.003, -0.12, 0.10, 0.018, 0.0195, M_DARK, M=Mx, skip=('z-',))
    return mb, [], [Vector((0, 0, 0))]


def P_iv_stand(lod):
    mb = MB('ivstand')
    bx(mb, -0.10, 0.10, -0.08, 0.08, 0.0, 0.012, M_METAL)
    mb.cyl((0, 0, 0.012), (0, 0, 0.62), 0.008, M_METAL, n=6)
    mb.cyl((-0.16, 0, 0.60), (0.16, 0, 0.60), 0.007, M_METAL, n=6)
    for x in (-0.11, 0.11):
        mb.cyl((x, 0, 0.60), (x, 0, 0.56), 0.004, M_METAL, n=4)
        # bag: pillow box with label, tube
        z1, z0 = 0.555, 0.33
        bx(mb, x - 0.065, x + 0.065, -0.014, 0.014, z0, z1 - 0.02, M_LAB, rects=all_rects(sw('clear'), 'clear', 'clear'))
        bx(mb, x - 0.045, x + 0.045, -0.0155, -0.014, z0 + 0.07, z0 + 0.16, M_LAB, rects=all_rects(RG['lbl_blood_bag'], 'white', 'white'), skip=('y+',))
        bx(mb, x - 0.05, x + 0.05, -0.0150, -0.014, z0 + 0.012, z0 + 0.03, M_LAB, rects=all_rects(sw('red'), 'red', 'red'), skip=('y+',))
        bx(mb, x - 0.015, x + 0.015, -0.006, 0.006, z1 - 0.02, z1, M_LAB, rects=all_rects(sw('clear'), 'clear', 'clear'))
        cyl_uv(mb, (x, 0, z0), (x, 0, z0 - 0.10), 0.004, M_LAB, 4, sw('clear'), caps=(False, True))
    return mb, [], [Vector((0, 0, 0))]


def P_organ_bags(lod):
    mb = MB('organbags')
    rnd = random.Random(7)
    for k in range(4):
        Mx = T(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), k * 0.016) @ RZ(rnd.uniform(-5, 5))
        top = RG['lbl_organ_bag'] if k == 3 else sw('bag_white')
        bx(mb, -0.14, 0.14, -0.10, 0.10, 0.0, 0.016, M_LAB, M=Mx, rects=all_rects(sw('bag_white'), 'bag_white', top), skip=('z-',))
        bx(mb, -0.14, 0.14, 0.075, 0.085, 0.016, 0.019, M_LAB, M=Mx, rects=all_rects(sw('zip_blue'), 'zip_blue', 'zip_blue'), skip=('z-',))
    return mb, [], [Vector((0, 0, 0))]


def P_body_bags(lod):
    mb = MB('bodybags')
    rnd = random.Random(9)
    for k in range(3):
        Mx = T(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), k * 0.05) @ RZ(rnd.uniform(-4, 4))
        bx(mb, -0.21, 0.21, -0.15, 0.15, 0.0, 0.05, M_DARK, M=Mx, skip=('z-',))
        if lod == 0:
            bx(mb, -0.205, 0.205, -0.004, 0.004, 0.05, 0.054, M_METAL, M=Mx, skip=('z-',))
    Mx = T(0.08, 0.06, 0.15)
    bx(mb, -0.06, 0.06, -0.035, 0.035, 0.0, 0.002, M_LAB, M=Mx, rects=all_rects(RG['lbl_body_bag'], 'dark', RG['lbl_body_bag']), skip=('z-',))
    return mb, [], [Vector((0, 0, 0))]


def P_trash_bags(lod):
    mb = MB('trashbags')
    n = 6 if lod else 10
    for (x, y, z) in ((-0.0, -0.06, 0.05), (0.0, 0.06, 0.05), (0.0, 0.0, 0.135)):
        cyl_uv(mb, (x - 0.13, y, z), (x + 0.13, y, z), 0.05, M_LAB, n, sw('black_bag'), caps=(True, True), cap_rect=sw('dark'))
        cyl_uv(mb, (x - 0.04, y, z), (x + 0.04, y, z), 0.053, M_LAB, n, RG['lbl_trash_bag'], caps=(False, False))
        for xe in (x - 0.04, x + 0.04):
            mb.face([Vector((xe, y + 0.053 * math.cos(2 * math.pi * i / n), z + 0.053 * math.sin(2 * math.pi * i / n))) for i in range(n)],
                    M_LAB, want=(1 if xe > x else -1, 0, 0), uvs=[(sw('black_bag')[0], sw('black_bag')[1])] * n)
    return mb, [], [Vector((0, 0.06, 0.0)), Vector((0, -0.06, 0.0))]


def P_price_card(lod, key='syringe_blood'):
    mb = MB('card')
    w, h, tilt = 0.20, 0.10, math.radians(16)
    zt = h * math.cos(tilt)
    dy = h * math.sin(tilt)
    r = RG['card_' + key]
    mb.face([(-w / 2, -dy, 0.0), (w / 2, -dy, 0.0), (w / 2, 0.0, zt), (-w / 2, 0.0, zt)], M_LAB, want=(0, -1, 0.3), uvs=rect_uv(r))
    s = sw('paper')
    mb.face([(-w / 2, dy, 0.0), (w / 2, dy, 0.0), (w / 2, 0.0, zt), (-w / 2, 0.0, zt)], M_LAB, want=(0, 1, 0.3), uvs=rect_uv(s))
    return mb, [], [Vector((0, 0, 0))]


def P_register(lod):
    mb = MB('register')
    bx(mb, -0.20, 0.20, -0.17, 0.17, 0.0, 0.10, M_DARK, skip=('z-',))
    if lod == 0:
        bx(mb, -0.17, 0.17, -0.174, -0.17, 0.02, 0.08, M_DARK, skip=('y+',))
    # keyboard slab, monitor on a pole facing the cashier (+y)
    bx(mb, -0.16, 0.16, 0.0, 0.14, 0.10, 0.125, M_LAB, rects=all_rects(sw('grey'), 'dark', sw('grey')))
    mb.cyl((0, -0.08, 0.10), (0, -0.08, 0.30), 0.018, M_DARK, n=6)
    Mx = T(0, -0.08, 0.40) @ RX(-12)
    bx(mb, -0.17, 0.17, -0.025, 0.0, -0.11, 0.11, M_DARK, M=Mx)
    bx(mb, -0.155, 0.155, 0.0, 0.003, -0.095, 0.095, M_LAB, M=Mx, rects={'y+': RG['register_screen'], 'x-': sw('dark'), 'x+': sw('dark'),
                                                                        'z+': sw('dark'), 'z-': sw('dark'), 'y-': sw('dark')})
    # card terminal facing the customer
    Mt = T(0.30, -0.12, 0.0) @ RX(15)
    bx(mb, -0.04, 0.04, -0.06, 0.06, 0.0, 0.035, M_DARK, M=Mt, skip=('z-',))
    return mb, [(Vector((-0.2, -0.17, 0)), Vector((0.2, 0.17, 0.5)))], [Vector((0, 0, 0)), Vector((0.30, -0.12, 0))]


def P_mini_cross(lod):
    mb = MB('minicross')
    Mx = RX(-12)
    bx(mb, -0.09, 0.09, -0.006, 0.006, 0.0, 0.18, M_GREEN, M=Mx, skip=('z-',), mats={'y-': M_LAB},
       rects={'y-': RG['poster_cross']})
    bx(mb, -0.06, 0.06, 0.0, 0.06, 0.0, 0.006, M_GREEN)
    return mb, [], [Vector((0, 0.03, 0))]


def P_gloves(lod):
    mb = MB('gloves')
    bx(mb, -0.12, 0.12, -0.065, 0.065, 0.0, 0.09, M_LAB, skip=('z-',), rects=all_rects(RG['lbl_gloves'], 'blue', 'white'))
    return mb, [], [Vector((0, 0, 0))]


def P_chair(lod):
    mb = MB('chair')
    n = 6
    for x in (-0.19, 0.19):
        for y in (-0.19, 0.19):
            mb.cyl((x, y, 0.02), (x, y, 0.45), 0.012, M_DARK, n=n, caps=(False, False))
            mb.cyl((x, y, 0.0), (x, y, 0.02), 0.015, M_RUB, n=n, caps=(False, True))
    for x in (-0.19, 0.19):
        mb.cyl((x, 0.19, 0.45), (x, 0.21, 0.88), 0.012, M_DARK, n=n)
        mb.cyl((x, -0.19, 0.06), (x, 0.19, 0.06), 0.009, M_DARK, n=n)
    bx(mb, -0.22, 0.22, -0.22, 0.21, 0.45, 0.49, M_GREEN)
    Mx = T(0, 0.205, 0.0) @ RX(-6)
    bx(mb, -0.22, 0.22, -0.015, 0.015, 0.62, 0.86, M_GREEN, M=Mx)
    return mb, [(Vector((-0.23, -0.23, 0)), Vector((0.23, 0.23, 0.9)))], [Vector((0, 0, 0))]


def P_bucket(lod):
    mb = MB('bucket')
    n = 8 if lod == 0 else 6
    mb.lathe([(0.0, 0.004), (0.15, 0.004), (0.17, 0.28), (0.155, 0.28), (0.135, 0.02), (0.0, 0.02)], n, M_TQP, smooth=True)
    mb.lathe([(0.0, 0.0), (0.15, 0.0), (0.15, 0.004), (0.0, 0.004)], n, M_RUB)
    mb.cyl((0.0, 0.0, 0.05), (0.0, 0.32, 1.32), 0.013, M_WOOD, n=6)
    bx(mb, -0.10, 0.10, -0.06, 0.06, 0.03, 0.10, M_OFF)
    return mb, [(Vector((-0.17, -0.17, 0)), Vector((0.17, 0.17, 0.3)))], [Vector((0, 0, 0))]


def P_bin(lod, r=0.15, h=0.32):
    mb = MB('bin')
    n = 10 if lod == 0 else 6
    mb.lathe([(0.0, 0.0), (r * 0.9, 0.0), (r, h), (r - 0.01, h), (r * 0.9 - 0.01, 0.015), (0.0, 0.015)], n, M_DARK, smooth=True)
    return mb, [(Vector((-r, -r, 0)), Vector((r, r, h)))], [Vector((0, 0, 0))]


def P_street_bin(lod):
    mb = MB('streetbin')
    bx(mb, -0.22, 0.22, -0.22, 0.22, 0.04, 0.80, M_DARK, skip=('z+', 'z-'))
    bx(mb, -0.20, 0.20, -0.20, 0.20, 0.04, 0.78, M_DARK, skip=('z-', 'z+'))
    for (a, b, c, d_) in ((-0.22, 0.22, -0.22, -0.20), (-0.22, 0.22, 0.20, 0.22), (-0.22, -0.20, -0.20, 0.20), (0.20, 0.22, -0.20, 0.20)):
        mb.face([(a, c, 0.80), (b, c, 0.80), (b, d_, 0.80), (a, d_, 0.80)], M_DARK, want=(0, 0, 1))
    mb.face([(-0.20, -0.20, 0.10), (0.20, -0.20, 0.10), (0.20, 0.20, 0.10), (-0.20, 0.20, 0.10)], M_DARK, want=(0, 0, 1))
    for x in (-0.18, 0.18):
        for y in (-0.18, 0.18):
            bx(mb, x - 0.03, x + 0.03, y - 0.03, y + 0.03, 0.0, 0.04, M_METAL, skip=('z-',))
    bx(mb, -0.23, 0.23, -0.23, 0.23, 0.80, 0.83, M_DARK, skip=())
    return mb, [(Vector((-0.23, -0.23, 0)), Vector((0.23, 0.23, 0.83)))], [Vector((0, 0, 0))]


def P_poster(lod, region='poster_cross', w=0.60, h=0.60, frame=0.03, depth=0.025, frame_mat=M_TQP):
    mb = MB('poster')
    bx(mb, -w / 2, w / 2, -depth, 0.0, 0.0, h, frame_mat, skip=('y+', 'y-'))
    Wf = Wall((0, -depth, 0), (1, 0, 0), (0, -1, 0))
    if lod == 0 and frame > 0:
        inset_panel(mb, Wf, -w / 2, w / 2, 0.0, h, 0.0, frame, 0.008, frame_mat, mat_in=M_LAB)
        # put the art on the recessed panel: replace the last-but-4 face UVs
        mb_face_uv(mb, region, -w / 2 + frame, w / 2 - frame, frame, h - frame, Wf, -depth + 0.008)
    else:
        label_quad(mb, Wf, -w / 2, w / 2, 0.0, h, 0.0, region)
    return mb, [], [Vector((0, 0.0, h / 2))]


def mb_face_uv(mb, region, u0, u1, z0, z1, Wf, d):
    """Re-map UVs of the face whose centre matches the given rectangle (used for the recessed poster art)."""
    c = Wf.P(0.5 * (u0 + u1), 0.5 * (z0 + z1), Wf.N.dot(Vector((0, 0, 0))) + 0.0)
    r = RG[region]
    for fi in range(len(mb.F) - 1, -1, -1):
        f = mb.F[fi]
        if mb.M[fi] != M_LAB or len(f) != 4:
            continue
        pts = [mb.P[i] for i in f]
        uvs = []
        for p in pts:
            a = (p - Wf.O).dot(Wf.T)
            b = p.z
            uvs.append((r[0] + (r[2] - r[0]) * (a - u0) / (u1 - u0), r[1] + (r[3] - r[1]) * (b - z0) / (z1 - z0)))
        for i, uv in zip(f, uvs):
            mb.UV[i] = uv
        return


def P_window_poster(lod, z0=1.92):
    mb = MB('winposter')
    w, h = 0.50, 0.50
    bx(mb, -w / 2, w / 2, -0.004, 0.004, 0.0, h, M_LAM, mats={'y-': M_LAB}, rects={'y-': RG['poster_cross']})
    for x in (-0.18, 0.18):
        mb.cyl((x, 0.0, h), (x, 0.0, P.OH - z0), 0.0015, M_DARK, n=3, caps=(False, False))
    return mb, [], [Vector((-0.18, 0.0, P.OH - z0)), Vector((0.18, 0.0, P.OH - z0))]


def P_towel(lod):
    mb = MB('towel')
    Mx = RX(4)
    bx(mb, -0.14, 0.14, -0.012, 0.012, -0.55, 0.0, M_TQP, M=Mx, skip=())
    bx(mb, -0.142, 0.142, -0.014, 0.014, -0.50, -0.47, M_OFF, M=Mx)
    return mb, [], [Vector((0, 0, 0))]


def P_soap(lod):
    mb = MB('soap')
    cyl_uv(mb, (0, 0, 0), (0, 0, 0.13), 0.032, M_LAB, 8 if lod == 0 else 6, RG['bottle_2'], caps=(False, True))
    cyl_uv(mb, (0, 0, 0.13), (0, 0, 0.16), 0.01, M_LAB, 6, sw('white'), caps=(False, True))
    bx(mb, -0.006, 0.006, -0.05, -0.004, 0.145, 0.155, M_LAB, rects=all_rects(sw('white'), 'white', 'white'))
    return mb, [], [Vector((0, 0, 0))]


def P_clock(lod):
    mb = MB('clock')
    n = 16 if lod == 0 else 10
    mb.cyl((0, 0.0, 0), (0, -0.045, 0), 0.17, M_DARK, n=n, caps=(False, True))
    mb.disc((0, -0.035, 0), 0.15, n, M_LAM, normal=(0, -1, 0))
    for i in range(12):
        a = 2 * math.pi * i / 12
        Mx = T(0.125 * math.sin(a), -0.036, 0.125 * math.cos(a)) @ RY(-math.degrees(a))
        bx(mb, -0.004, 0.004, -0.001, 0.0, -0.012, 0.012, M_DARK, M=Mx, skip=('y+',))
    bx(mb, -0.004, 0.004, -0.040, -0.037, -0.005, 0.09, M_DARK, skip=('y+',))
    Mh = T(0, -0.041, 0) @ RY(-120)
    bx(mb, -0.005, 0.005, -0.003, 0.0, -0.005, 0.065, M_DARK, M=Mh, skip=('y+',))
    return mb, [], [Vector((0, 0, 0))]


def P_cartons(lod, n=3, seed=3):
    mb = MB('cartons')
    rnd = random.Random(seed)
    z = 0.0
    items = []
    for k in range(n):
        w, d, h = rnd.uniform(0.45, 0.6), rnd.uniform(0.35, 0.45), rnd.uniform(0.28, 0.38)
        Mx = T(rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), z) @ RZ(rnd.uniform(-6, 6))
        bx(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, M_CARD, M=Mx, skip=('z-',) if k else ('z-',), mats={'y-': M_LAB, 'z+': M_LAB},
           rects={'y-': RG['carton_side'], 'z+': RG['carton_top']})
        items.append(Vector((Mx.translation.x, Mx.translation.y, z)))
        z += h
    return mb, [(Vector((-0.33, -0.25, 0)), Vector((0.33, 0.25, z)))], items[:1]


def P_extinguisher(lod):
    mb = MB('extinguisher')
    n = 8 if lod == 0 else 6
    # wall bracket (back plate on the wall plane y = 0, the body hangs in front of it)
    bx(mb, -0.05, 0.05, -0.012, 0.0, 0.25, 0.55, M_METAL, skip=('y+',))
    bx(mb, -0.08, 0.08, -0.17, -0.012, 0.36, 0.38, M_METAL)
    c = Vector((0.0, -0.09, 0.0))
    cyl_uv(mb, c + Vector((0, 0, 0.02)), c + Vector((0, 0, 0.44)), 0.075, M_LAB, n, sw('red'), caps=(True, True))
    cyl_uv(mb, c + Vector((0, 0, 0.44)), c + Vector((0, 0, 0.50)), 0.022, M_LAB, 6, sw('steel'), caps=(False, True))
    bx(mb, -0.012, 0.012, -0.16, -0.02, 0.50, 0.52, M_DARK)
    mb.tube([(0.03, -0.09, 0.47), (0.08, -0.12, 0.40), (0.085, -0.13, 0.15)], 0.008, M_DARK, n=4)
    bx(mb, -0.055, 0.055, -0.168, -0.163, 0.20, 0.30, M_LAB, rects=all_rects(sw('white'), 'white', 'white'), skip=())
    return mb, [], [Vector((0.0, 0.0, 0.40))]


def P_mat(lod):
    mb = MB('mat')
    cbar(mb, 'x', -0.60, 0.60, -0.40, 0.40, 0.0, 0.012, 0.008, M_RUB, chamf=(0, 0, 1, 1))
    if lod == 0:
        for k in range(1, 8):
            y = -0.40 + 0.8 * k / 8
            bx(mb, -0.54, 0.54, y - 0.012, y + 0.012, 0.012, 0.016, M_RUB, skip=('z-',))
    return mb, [], [Vector((0, 0, 0))]


def P_info(lod):
    mb = MB('info')
    bx(mb, -0.17, 0.17, -0.006, 0.0, 0.0, 0.34, M_LAM, skip=('y+',), mats={'y-': M_LAB}, rects={'y-': RG['info_sheet']})
    return mb, [], [Vector((0, 0.0, 0.17))]


def prop_layout():
    PROPS.clear()
    X0, X1, Y0, Y3, PY0, PY1, H = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1, P.H
    CY0, CY1, ct, dt = P.CY0, P.CY1, P.CTOP, P.DTOP
    groups = {}
    for s in SHELF_SLOTS:
        g = s['name'].split('_')[0]
        if g in ('ShelfL', 'ShelfR'):
            g = g + '_' + s['name'].split('_')[1]
        if g.startswith('Back'):
            g = 'Back_' + s['name'].split('_')[1]
        groups.setdefault(g, []).append(s)
    for i, (g, slots) in enumerate(sorted(groups.items())):
        area = 'stock' if g.startswith(('Stock', 'Rack')) else 'sales'
        add_prop('PH_P_Fill_%s' % g, P_fill, (0, 0, 0), area=area, slots=slots, seed=11 + i)
    # counter display (customer side) + price cards (catalog keys, G48 prices)
    yc = CY0 + 0.26
    gx = [P.GC0 + (P.GC1 - P.GC0) * (k + 0.5) / 7 for k in range(7)]
    dx = [P.CD0 + 0.32, P.GT0 - 0.62]
    display = [('body_bag', P_body_bags, gx[0], ct, {}), ('trash_bag', P_trash_bags, gx[1], ct, {}),
               ('organ_bag', P_organ_bags, gx[2], ct, {}), ('blood_bag_empty', P_iv_stand, gx[3], ct, {}),
               ('syringe_blood', P_syringes, gx[4], ct, dict(kind='blood')),
               ('syringe_anaesthesia', P_syringes, gx[5], ct, dict(kind='anaesthesia')),
               ('zip_tie', P_cable_ties_loose, gx[6], ct, {}), ('zip_tie_pack_4', P_cable_tie_packs, dx[0], dt + 0.05, {}),
               ('anaesthesia_basic', P_vials, dx[1], dt + 0.05, {})]
    cards = {c['catalog_key']: c for c in ATLAS['price_cards']}
    for key, fn, x, z, kw in display:
        add_prop('PH_P_Item_%s' % key, fn, (x, yc + (0.04 if key == 'blood_bag_empty' else 0.0), z), area='counter', meta=dict(catalog_key=key), **kw)
        add_prop('PH_P_PriceCard_%s' % key, P_price_card, (x, CY0 + 0.075 - (0.03 if z > 1.02 else 0.0), z), area='counter',
                 meta=dict(catalog_key=key, label=cards[key]['label'], price=cards[key]['price'], unit=cards[key]['unit']), key=key)
    add_prop('PH_P_CashRegister', P_register, (P.REG_X, CY1 - 0.24, dt + 0.05), rot=0.0, area='counter', collide=True)
    add_prop('PH_P_MiniCross', P_mini_cross, (dx[1] + 0.02, CY1 - 0.13, dt + 0.05), area='counter')
    add_prop('PH_P_Gloves', P_gloves, (P.BC0 + 0.6, PY0 - 0.30, 0.88), area='staff')
    # walls: poster + information sheet (left wall after the shelving), clock above the back cabinets
    wy = 0.5 * (P.LSH[1] + P.FY0)
    add_prop('PH_P_PosterCross', P_poster, (X0, wy - 0.25, 1.30), rot=90.0, area='sales')
    add_prop('PH_P_InfoSheet', P_info, (X0, wy + 0.32, 1.38), rot=90.0, area='sales')
    add_prop('PH_P_Clock', P_clock, (0.5 * (P.BC0 + P.BC1), PY0, 2.80), area='staff')
    xr = P.XW0 + (P.XW1 - P.XW0) * (P.NPANES - 0.5) / P.NPANES
    add_prop('PH_P_WindowPoster', P_window_poster, (xr, 0.20, 1.92), area='window', z0=1.92)
    add_prop('PH_P_DoorMat', P_mat, (P.DCX, Y0 + 0.55, 0.0), area='sales')
    add_prop('PH_P_Extinguisher_Sales', P_extinguisher, (X1, 0.5 * (CY1 + PY0) + 0.4, 0.55), rot=-90.0, area='staff')
    add_prop('PH_P_Extinguisher_Stock', P_extinguisher, (P.RD1 + 0.35, Y3, 0.30), rot=0.0, area='stock')
    add_prop('PH_P_BinSales', P_bin, (P.XW1 + 0.11 - 0.0, Y0 + 0.62, 0.0), area='sales', collide=True)
    add_prop('PH_P_StreetBin', P_street_bin, (P.BAY1 + 0.0 - 0.0 + 0.18, -0.55, 0.0), area='street', collide=True,
             meta=dict(note='Exterior, beside the door. Snap to the pavement height in Unity.'))
    # stockroom clutter (reference A)
    add_prop('PH_P_Chair', P_chair, (P.SKX + 0.85, Y3 - 0.55, 0.0), rot=200.0, area='stock', collide=True)
    add_prop('PH_P_MopBucket', P_bucket, (P.SKX - 0.50, Y3 - 0.30, 0.0), rot=180.0, area='stock', collide=True)
    add_prop('PH_P_Towel', P_towel, (P.SKX - 0.28 - 0.18, Y3 - 0.075, 1.575), area='stock')
    add_prop('PH_P_Soap', P_soap, (P.SKX + 0.19, Y3 - 0.06, 0.86), area='stock')
    add_prop('PH_P_Cartons_A', P_cartons, (P.RACK_A[0] - 0.235, 0.5 * (P.RACK_Y[0] + P.RACK_Y[1]) - 0.2, 0.0), rot=90.0, area='stock', collide=True,
             n=3, seed=4)
    add_prop('PH_P_Cartons_B', P_cartons, (X1 - 0.95, Y3 - 0.45, 0.0), rot=-5.0, area='stock', collide=True, n=2, seed=8)


# ============================================================================ Blender objects, export
def link_new(coll, name, data=None):
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    return ob


def hull_object(name, pts, coll, parent):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link_new(coll, name, me)
    ob.parent = parent
    ob.display_type = 'WIRE'
    ob.hide_render = True
    return ob


def export_fbx(path, roots):
    bpy.ops.object.select_all(action='DESELECT')
    objs = []
    for r in roots:
        objs.append(r)
        objs.extend(r.children_recursive)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=True,
                             object_types={'EMPTY', 'MESH'}, mesh_smooth_type='OFF', use_mesh_modifiers=True,
                             add_leaf_bones=False, path_mode='STRIP', embed_textures=False, use_tspace=False,
                             colors_type='NONE', use_custom_props=False)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def guard(path):
    if os.path.exists(path) and not P.FORCE:
        raise SystemExit('refusing to overwrite existing revision: ' + path)


def U(p):
    return [round(-p[0], 4), round(p[2], 4), round(-p[1], 4)]


def uyaw(bdeg):
    y = -bdeg % 360.0
    return round(y if y <= 180 else y - 360, 2)


# ============================================================================ checks
def world_tris(objs):
    verts, tris = [], []
    for ob in objs:
        me = ob.data
        mw = ob.matrix_world
        base = len(verts)
        verts.extend([mw @ v.co for v in me.vertices])
        me.calc_loop_triangles()
        tris.extend([tuple(base + i for i in lt.vertices) for lt in me.loop_triangles])
    return verts, tris


def check_zfight(objs):
    """Coplanar overlapping faces with the same facing (true z-fighting) across all LOD0 render meshes."""
    from collections import defaultdict
    faces = []
    for ob in objs:
        mw = ob.matrix_world
        R = mw.to_3x3()
        for p in ob.data.polygons:
            pts = [mw @ ob.data.vertices[i].co for i in p.vertices]
            n = (R @ p.normal).normalized()
            if n.length < 0.5:
                continue
            faces.append((ob.name, pts, n, n.dot(pts[0])))
    buckets = defaultdict(list)
    for i, (nm, pts, n, d) in enumerate(faces):
        key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d / 0.002))
        buckets[key].append(i)
    hits = []

    def proj(pts, n):
        a = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
        u = n.cross(a).normalized()
        v = n.cross(u)
        return [(p.dot(u), p.dot(v)) for p in pts]

    def clip(subj, clipper):
        def inside(p, a, b):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

        def inter(p, q, a, b):
            x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
            x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-12:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        out = subj
        for i in range(len(clipper)):
            a, b = clipper[i - 1], clipper[i]
            inp, out = out, []
            if not inp:
                break
            s = inp[-1]
            for e in inp:
                if inside(e, a, b):
                    if not inside(s, a, b):
                        out.append(inter(s, e, a, b))
                    out.append(e)
                elif inside(s, a, b):
                    out.append(inter(s, e, a, b))
                s = e
        return out

    def area(poly):
        return 0.5 * sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))

    seen = set()
    for key, idx in buckets.items():
        cand = list(idx)
        k2 = (key[0], key[1], key[2], key[3] + 1)
        cand2 = buckets.get(k2, [])
        allc = cand + cand2
        if len(allc) < 2:
            continue
        for ii in range(len(cand)):
            i = cand[ii]
            for j in allc:
                if j <= i or (i, j) in seen:
                    continue
                seen.add((i, j))
                ni, pi, n, di = faces[i][0], faces[i][1], faces[i][2], faces[i][3]
                nj, pj, n2, dj = faces[j][0], faces[j][1], faces[j][2], faces[j][3]
                if abs(di - dj) > 0.0008 or n.dot(n2) < 0.999:
                    continue
                a = proj(pi, n)
                b = proj(pj, n)
                if area(a) < 0:
                    a = a[::-1]
                if area(b) < 0:
                    b = b[::-1]
                c = clip(a, b)
                if len(c) >= 3 and abs(area(c)) > 2e-5:
                    hits.append((ni, nj, [round(v, 3) for v in sum(pi, Vector()) / len(pi)], round(abs(area(c)), 5)))
    return hits


def check_floating(unit_objs, prop_objs):
    verts, tris = world_tris(unit_objs + prop_objs)
    bvh = BVHTree.FromPolygons(verts, tris)
    bad = []
    pts = list(SUPPORTS)
    for pr in PROPS:
        Mw = Matrix.Translation(pr['loc']) @ RZ(pr['rot'])
        if pr['area'] == 'street':
            continue
        for k, it in enumerate(pr['items']):
            pts.append(('%s#%d' % (pr['name'], k), Mw @ it))
    for name, p in pts:
        near = bvh.find_nearest(p, 0.05)
        if near[0] is None or near[3] > 0.012:
            bad.append((name, [round(v, 3) for v in p], None if near[0] is None else round(near[3], 4)))
    return bad, len(pts)


def check_paths(routes, extra_boxes):
    """Every route sample keeps >= 0.5 m (1.0 m path) from every collider footprint overlapping 0.1..1.8 m height."""
    boxes = []
    for pts in UCX:
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        zs = [p.z for p in pts]
        if max(zs) < 0.10 or min(zs) > 1.8:
            continue
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    boxes += extra_boxes
    res = {}
    for name, (poly, rad) in routes.items():
        worst = 99.0
        where = None
        for a, b in zip(poly, poly[1:]):
            a, b = Vector(a), Vector(b)
            L = (b - a).length
            n = max(1, int(L / 0.05))
            for i in range(n + 1):
                p = a + (b - a) * (i / n)
                for (x0, x1, y0, y1) in boxes:
                    dx = max(x0 - p.x, 0.0, p.x - x1)
                    dy = max(y0 - p.y, 0.0, p.y - y1)
                    dd = math.hypot(dx, dy)
                    if dd < worst:
                        worst, where = dd, (round(p.x, 2), round(p.y, 2))
        res[name] = dict(min_clearance_m=round(worst, 3), clear_width_m=round(2 * worst, 3), at=where, required_half_width=rad,
                         ok=worst >= rad - 1e-3)
    return res


def check_prices():
    with open(ECON, encoding='utf-8') as f:
        econ = {e['id']: e for e in json.load(f)['entries']}
    out = []
    for c in ATLAS['price_cards']:
        e = econ.get(c['catalog_key'])
        want = '$%d' % e['price'] if e else None
        out.append(dict(key=c['catalog_key'], label=c['label'], card_price=c['price'], unit=c['unit'], catalog_price=e['price'] if e else None,
                        catalog_unit=e['unit'] if e else None, ok=(want == c['price'])))
    return out


# ============================================================================ main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    stem = 'Pharmacy_W86_%s_' + REV
    outs = {k: os.path.join(OUT, (stem % k) + '.' + ext) for k, ext in
            (('unit', 'fbx'), ('props', 'fbx'), ('anchors', 'json'), ('materials', 'json'), ('report', 'json'))}
    outs['blend'] = os.path.join(OUT, 'Pharmacy_W86_%s.blend' % REV)
    for p in outs.values():
        guard(p)
    lib = make_materials()
    cu = bpy.data.collections.new('PH_Unit')
    cp = bpy.data.collections.new('PH_Props')
    for c in (cu, cp):
        sc.collection.children.link(c)
    report = dict(revision=REV, footprint=dict(width=P.W, depth=P.D, ceiling=P.H, rear_door_x_blender=P.RDX))

    # ---------------- unit
    root = link_new(cu, 'Pharmacy_W86_unit')
    tris = {}
    unit_lod0 = []
    for lod in (0, 1):
        for fn in (build_shell, build_ceiling, build_interior):
            mb = fn(lod)
            ob = mb.build(lib, cu)
            ob.parent = root
            tris[ob.name] = tri_count(ob)
            if lod == 0:
                unit_lod0.append(ob)
            else:
                ob.hide_render = True
                ob.hide_set(True)
            if fn is build_interior and lod == 0:
                slots0 = list(SHELF_SLOTS)
                sup0 = list(SUPPORTS)
    SHELF_SLOTS[:] = slots0
    SUPPORTS[:] = sup0
    unit_colliders()
    for i, pts in enumerate(UCX):
        hull_object('UCX_PH_Unit_%02d' % (i + 1), pts, cu, root)
    # doors: top-level empty at the hinge (closed), identity children <name>_Mesh + UCX_<name>_01 (2-level FBX rule)
    door_objs = {}
    door_roots = []
    for name, dd in DOORS.items():
        holder = link_new(cu, name)
        holder.location = dd['hinge']
        holder.empty_display_size = 0.25
        mb = dd['builder'](0)
        ob = mb.build(lib, cu, name=name + '_Mesh')
        ob.parent = holder
        hull_object('UCX_%s_01' % name, door_ucx(name), cu, holder)
        tris[name] = tri_count(ob)
        unit_lod0.append(ob)
        door_objs[name] = holder
        door_roots.append(holder)
    report['unit_tris'] = tris
    report['unit_lod0_tris'] = sum(v for k, v in tris.items() if 'LOD1' not in k)
    report['unit_lod1_tris'] = sum(v for k, v in tris.items() if 'LOD0' not in k)
    report['unit_ucx_count'] = len(UCX)

    # ---------------- props
    prop_layout()
    # props: no common root; each prop is a top-level empty at its base point + yaw with identity children
    # <pid>_Mesh or <pid>_LOD0/_LOD1 and UCX_<pid>_NN (2-level FBX rule from Workshop_W86).
    prop_roots = []
    ptris, total0, total1 = {}, 0, 0
    prop_lod0 = []
    for pr in PROPS:
        holder = link_new(cp, pr['name'])
        holder.location = pr['loc']
        holder.rotation_euler = (0, 0, math.radians(pr['rot']))
        holder.empty_display_size = 0.15
        prop_roots.append(holder)
        if pr['mb1'] is None:
            ob = pr['mb0'].build(lib, cp, name=pr['name'] + '_Mesh')
            ob.parent = holder
            prop_lod0.append(ob)
        else:
            o0 = pr['mb0'].build(lib, cp, name=pr['name'] + '_LOD0')
            o1 = pr['mb1'].build(lib, cp, name=pr['name'] + '_LOD1')
            for o in (o0, o1):
                o.parent = holder
            o1.hide_render = True
            o1.hide_set(True)
            prop_lod0.append(o0)
        for j, (mn, mx) in enumerate(pr['ucx']):
            hull_object('UCX_%s_%02d' % (pr['name'], j + 1), [(x, y, z) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)], cp, holder)
        t0 = pr['mb0'].tris()
        t1 = pr['mb1'].tris() if pr['mb1'] else None
        ptris[pr['name']] = dict(lod0=t0, lod1=t1, area=pr['area'], collider=bool(pr['ucx']))
        total0 += t0
        total1 += t1 if t1 is not None else t0
    report['props_tris'] = ptris
    report['props_total_lod0_tris'] = total0
    report['props_total_lod1_tris'] = total1
    report['budget'] = dict(unit_lod0_max=20000, props_max=15000, unit_ok=report['unit_lod0_tris'] <= 20000, props_ok=total0 <= 15000)
    bpy.context.view_layer.update()

    # ---------------- anchors
    A = collect_anchors(door_objs)
    for nm, pos, yaw in A.pop('_empties'):
        e = link_new(cu, nm)
        e.parent = root
        e.location = pos
        e.rotation_euler = (0, 0, math.radians(yaw))
        e.empty_display_size = 0.3
    with open(outs['anchors'], 'w', encoding='utf-8') as f:
        json.dump(A, f, indent=1, ensure_ascii=False)

    # ---------------- checks
    zf = check_zfight([o for o in unit_lod0 + prop_lod0])
    report['zfight_same_facing_overlaps'] = len(zf)
    report['zfight_examples'] = zf[:60]
    fl, nsup = check_floating(unit_lod0, prop_lod0)
    report['floating_checked_points'] = nsup
    report['floating'] = fl
    routes = A['_routes_blender']
    prop_boxes = []
    for pr in PROPS:
        Mw = Matrix.Translation(pr['loc']) @ RZ(pr['rot'])
        for mn, mx in pr['ucx']:
            cs = [Mw @ Vector((x, y, 0)) for x in (mn.x, mx.x) for y in (mn.y, mx.y)]
            if pr['area'] != 'street':
                prop_boxes.append((min(c.x for c in cs), max(c.x for c in cs), min(c.y for c in cs), max(c.y for c in cs)))
    report['paths'] = check_paths(routes, prop_boxes)
    report['prices'] = check_prices()
    del A['_routes_blender']
    with open(outs['anchors'], 'w', encoding='utf-8') as f:
        json.dump(A, f, indent=1, ensure_ascii=False)

    # ---------------- materials JSON
    mats = {}
    for name, m in MATS.items():
        tex = m['tex']
        if tex and tex.startswith('NEW:'):
            tex_path, tex_rel = 'ArtSource/Buildings/Pharmacy_W86/' + tex[4:], None
        else:
            tex_path = ('Assets/OnlyVolunteers/Art/' + tex) if tex else None
            tex_rel = tex
        mats[name] = dict(albedo=tex_path, albedo_from_art_root=tex_rel,
                          normal=('Assets/OnlyVolunteers/Art/' + m['nrm']) if m.get('nrm') else None,
                          tile_m=m['tile'], unity_tiling=1.0 if m.get('atlas') else round(1.0 / m['tile'], 5), unity_offset=[0, 0],
                          tint=m['tint'], smoothness=m['smooth'], metallic=m['metal'], emission=m.get('emission'), alpha=m.get('alpha'),
                          uv='atlas' if m.get('atlas') else 'metres', note=m['note'])
    with open(outs['materials'], 'w', encoding='utf-8') as f:
        json.dump(dict(revision=REV, shader='URP/Lit',
                       uv='UV0 in metres (1 UV = 1 m) except MAT_PH_labels (atlas). Unity tiling = 1 / tile_m. Tints were chosen as target colour / texture mean so the '
                          'average surface colour matches the concept swatches.',
                       textures_new=['ArtSource/Buildings/Pharmacy_W86/Pharmacy_labels_v01.png (2048 sRGB, mip-mapped, Clamp)'],
                       atlas_regions='ArtSource/Buildings/Pharmacy_W86/Pharmacy_labels_v01_regions.json', materials=mats), f, indent=1)

    # ---------------- export
    export_fbx(outs['unit'], [root] + door_roots)
    export_fbx(outs['props'], prop_roots)
    with open(outs['report'], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    print('REPORT', json.dumps({k: v for k, v in report.items() if k not in ('props_tris', 'zfight_examples', 'unit_tris')}))
    bpy.ops.wm.save_as_mainfile(filepath=outs['blend'])
    return outs


def collect_anchors(door_objs):
    X0, X1, Y0, Y3, PY0, PY1, D = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1, P.D
    CY0, CY1 = P.CY0, P.CY1
    E = []

    def pt(name, p, yaw_b=0.0, **kw):
        E.append(('ANCHOR_' + name, Vector(p), yaw_b))
        return dict(position=U(p), yaw=uyaw(yaw_b), **kw)

    # Blender yaw convention for "facing": 0 = facing -Y (street), 180 = facing +Y (courtyard)
    A = dict(revision=REV, units='metres',
             coordinate_system='Unity local space of the unit root: +Y up, +Z = street side, pivot = floor level at the centre of the street front '
                               '(outer face of the storefront wall). Converted from Blender (x, y, z) as (-x, z, -y). The same points exist as ANCHOR_* '
                               'empties in Pharmacy_W86_unit_%s.fbx; if importer axes differ, trust the empties.' % REV,
             yaw='degrees about Unity +Y; 0 = facing +Z (toward the street), 180 = facing -Z (toward the courtyard)',
             footprint=dict(size_xyz=[P.W, round(P.H + P.SLAB, 3), P.D], floor_y=0.0, ceiling_y=P.H, storefront_top_y=P.FH,
                            interior_x=[round(-X1, 3), round(-X0, 3)], interior_z=[round(-Y3, 3), round(-Y0, 3)],
                            foundation_bottom_y=P.FOUND,
                            note='Self-contained ground-floor insert: storefront piece (street, +Z), side wall linings 0.2 m, rear wall 0.3 m with door, '
                                 'ceiling slab to y=%.2f. The existing building above/around stays. Street step top flush with the floor; '
                                 'its front face reaches y=-0.35 for a pavement up to 0.35 m lower.' % (P.H + P.SLAB)),
             site=dict(building='Rough 04-H3 (5-storey khrushchevka), ground-floor west unit', street='south (unit +Z)',
                       rear_door_offset_note='Rear door centre at Unity local x=%.2f (Blender x=%+.2f). With the unit yawed so +Z faces south, '
                                             'local -X points east.' % (-P.RDX, P.RDX)))
    A['street_door'] = dict(outside=pt('StreetDoor_Out', (P.DCX, -0.9, 0.0), 180), inside=pt('StreetDoor_In', (P.DCX, Y0 + 0.9, 0.0), 180),
                            centre=U((P.DCX, P.GY, 0.0)), clear_width=P.DOOR_W, clear_height=P.DH, step_height_max=0.15,
                            leaf='Door_Street')
    A['counter_purchase_point'] = pt('PurchasePoint', (P.REG_X, CY0 - 0.56, 0.0), 180,
                                     note='Player stands here facing the cash desk (Unity -Z); register and card terminal on the desk.')
    A['cashier_point'] = pt('Cashier', (P.REG_X, CY1 + 0.58, 0.0), 0, note='Staff NPC behind the cash desk, facing the customer.')
    A['staff_door'] = dict(sales_side=pt('StaffDoor_Sales', (P.SDX, PY0 - 0.60, 0.0), 180), stock_side=pt('StaffDoor_Stock', (P.SDX, PY1 + 0.60, 0.0), 180),
                           centre=U((P.SDX, 0.5 * (PY0 + PY1), 0.0)), clear_width=P.SDW, clear_height=P.SDH, leaf='Door_Staff',
                           player_access='none: behind the counter line (glass counter, cash desk, staff gate with STAFF ONLY plate, end cabinet) '
                                         'and the closed Door_Staff (STAFF ONLY sign on the sales face)')
    A['staff_gate'] = dict(centre=U((0.5 * (P.GT0 + P.GT1), 0.5 * (CY0 + CY1), 0.0)), width=round(P.GT1 - P.GT0, 3), height=1.04,
                           note='Fixed closed counter gate (part of the unit mesh + collider). Staff do not need it: their route is staff door -> behind counter.')
    A['stockroom'] = dict(centre=pt('Stockroom', (0.5 * (P.RD0 + X1) - 0.3, 0.5 * (PY1 + Y3) + 0.2, 0.0), 0),
                          bounds_min=U((X1, Y3, 0.0)), bounds_max=U((X0, PY1, P.H)),
                          capture_space=dict(centre=U((0.5 * (P.RD0 + X1) - 0.3, 0.5 * (PY1 + Y3), 0.0)),
                                             size_x_z=[round(X1 - P.RD0 - 0.6, 2), round(Y3 - PY1 - 0.8, 2)],
                                             note='Open floor between rack B / rear door and the right wall shelving; usable from the courtyard door.'))
    A['rear_door'] = dict(inside=pt('RearDoor_In', (P.RDX, Y3 - 0.80, 0.0), 180), outside=pt('RearDoor_Out', (P.RDX, D + 0.80, 0.0), 180),
                          centre=U((P.RDX, 0.5 * (Y3 + D), 0.0)), clear_width=round(P.RDW - 0.12, 3), clear_height=round(P.RDH - 0.06, 3),
                          threshold='flush (floor level), landing ramp 1.4 m falls 0.12 m to the yard', leaf='Door_Rear')
    route = [(P.REG_X, CY1 + 0.58), (P.SDX, CY1 + 0.75), (P.SDX, PY0 - 0.60), (P.SDX, PY1 + 0.60), (0.5 * (P.RDX + P.SDX), 0.5 * (PY1 + Y3) + 0.3),
             (P.RDX, Y3 - 0.80), (P.RDX, D + 0.80), (P.RDX, D + 2.60)]
    A['staff_npc_route'] = [pt('StaffRoute_%02d' % (i + 1), (x, y, 0.0), 180) for i, (x, y) in enumerate(route)]
    A['staff_npc_route_note'] = 'Cashier -> behind the counter -> staff door (opens into the stockroom) -> across the stockroom -> rear door -> yard.'
    van_c = (P.RDX, D + 1.40 + 1.0 + 2.6)
    A['rear_van_loading'] = dict(
        loading_point=pt('VanLoad', (P.RDX, D + 1.90, 0.0), 180),
        van_stop=pt('VanStop', (van_c[0], van_c[1], 0.0), 180, note='Van centre; nose toward the yard (Unity -Z), rear doors facing the pharmacy door.'),
        van_rear_bumper=U((P.RDX, D + 2.40, 0.0)),
        carry_path=[U((P.RDX, Y3 - 0.8, 0)), U((P.RDX, D + 0.8, 0)), U((P.RDX, D + 1.9, 0))],
        clear_zone=dict(centre=U((P.RDX, D + 6.0, 0)), size_x_z=[8.0, 10.0],
                        note='Keep this yard area flat and free for stopping / a three-point turn (van 5.2 x 2.0 m). Not part of the insert.'),
        side_option=dict(van_stop=U((P.RDX + 3.2, D + 3.0, 0.0)), yaw=uyaw(90),
                         note='Alternative: van parked parallel to the wall, side door at the loading point.'))
    A['zones'] = dict(customer=dict(min=U((X1, CY0, 0)), max=U((X0, Y0, 0)), note='Public sales floor.'),
                      staff=dict(min=U((X1, PY0, 0)), max=U((X0, CY1, 0)), note='Behind the counter: no player access from the sales floor.'))
    A['lights'] = []
    for i, (x, y, z) in enumerate(LAMPS_SALES):
        A['lights'].append(dict(name='Light_Sales_%02d' % (i + 1), position=U((x, y, z)), type='area or point down', colour='#FFE3BC',
                                suggested=dict(point_range_m=6.5, intensity_lm=1600)))
        E.append(('ANCHOR_Light_Sales_%02d' % (i + 1), Vector((x, y, z)), 0.0))
    for i, (x, y, z) in enumerate(LAMPS_STOCK):
        A['lights'].append(dict(name='Light_Stock_%02d' % (i + 1), position=U((x, y, z)), type='point down', colour='#F3F0E6',
                                suggested=dict(point_range_m=6, intensity_lm=1400)))
        E.append(('ANCHOR_Light_Stock_%02d' % (i + 1), Vector((x, y, z)), 0.0))
    A['lights'].append(dict(name='Light_Rear_Bulkhead', position=U((P.RD1 + 0.45, D + 0.15, 2.23)), type='point', colour='#FFE2B0',
                            suggested=dict(point_range_m=6, intensity_lm=500)))
    A['lights'].append(dict(name='Light_CrossSign', position=U((P.HW - P.PIL / 2, -0.66, P.OH + 0.30)), type='point (green, small)', colour='#45C46C',
                            suggested=dict(point_range_m=3, intensity_lm=150)))
    A['doors'] = {}
    for name, dd in DOORS.items():
        A['doors'][name] = dict(hinge_position=U(dd['hinge']), pivot='hinge, floor', closed_local_yaw=0.0, open_local_yaw=uyaw(dd['open_yaw_blender']),
                                opens_into=dd['opens_into'], state=dd['state'], clear_width=round(dd['clear_w'], 3), clear_height=round(dd['clear_h'], 3),
                                collider='UCX_%s_01 (child)' % name)
    cards = {}
    for pr in PROPS:
        if pr['name'].startswith('PH_P_PriceCard_'):
            m = pr['meta']
            cards[m['catalog_key']] = dict(object=pr['name'], item_object='PH_P_Item_' + m['catalog_key'], position=U(pr['loc']), yaw=0.0,
                                           label=m['label'], price=m['price'], unit=m['unit'])
    A['price_cards'] = dict(source='Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json (G48 catalog, read-only)', cards=cards,
                            note='Customer-facing tent cards on the counter. Labels are baked into Pharmacy_labels_v01.png; the runtime shop must charge the '
                                 'same catalog entry (keys above). Improved/late anaesthetic are not displayed (unlock-gated).')
    A['props'] = dict(file='Pharmacy_W86_props_%s.fbx' % REV, note='Place the props root at the unit root transform; every child is already in position.',
                      items={pr['name']: dict(position=U(pr['loc']), yaw=uyaw(pr['rot']), area=pr['area'], **({k: v for k, v in pr['meta'].items()}))
                             for pr in PROPS if not pr['name'].startswith('PH_P_Fill_')},
                      shelf_fills=[pr['name'] for pr in PROPS if pr['name'].startswith('PH_P_Fill_')])
    A['_empties'] = E
    A['_routes_blender'] = {
        'customer_street_to_purchase': ([(P.DCX, -0.9), (P.DCX, Y0 + 0.9), (P.REG_X + 0.4, CY0 - 0.9), (P.REG_X, CY0 - 0.56)], 0.5),
        'staff_cashier_to_yard': ([tuple(p) for p in route], 0.5),
        'courtyard_to_stockroom_carry': ([(P.RDX, D + 1.90), (P.RDX, D + 0.8), (P.RDX, Y3 - 0.8), (0.5 * (P.RD0 + X1) - 0.3, 0.5 * (PY1 + Y3) + 0.2)], 0.5),
        'customer_aisle_left': ([(X0 + 0.025 + P.SHELF_D + 0.55, Y0 + 1.0), (X0 + 0.025 + P.SHELF_D + 0.55, P.FY0 - 0.55)], 0.5),
        'stock_aisle_left': ([(0.5 * (X0 + 0.53 + P.RACK_A[0] - 0.50), PY1 + 0.5), (0.5 * (X0 + 0.53 + P.RACK_A[0] - 0.50), Y3 - 0.50 - 0.55)], 0.5),
        'stock_aisle_racks': ([(0.5 * (P.RACK_A[1] + P.RACK_B[0]), PY1 + 0.5), (0.5 * (P.RACK_A[1] + P.RACK_B[0]), Y3 - 0.5)], 0.5),
        'stock_front_cross_aisle': ([(X0 + 0.53 + 0.5, PY1 + 0.5), (P.SD0, PY1 + 0.5)], 0.5),
        'stock_rear_cross_aisle': ([(P.STOCK_REAR[1] + 0.55, 0.5 * (P.RACK_Y[1] + Y3)), (P.RD0, 0.5 * (P.RACK_Y[1] + Y3))], 0.5),
    }
    return A


if __name__ == '__main__':
    main()
