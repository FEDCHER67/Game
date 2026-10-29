"""Workshop_W86 v01 - mechanic's workshop (palette A), game-ready low-poly build.

Run headless:
  blender -b --factory-startup -noaudio --python build_workshop_w86_v01.py -- [--force] [--no-render]
Outputs (ArtSource/Buildings/Workshop_W86/):
  Workshop_W86_building_v01.fbx  shell + fixed interior, LOD0/LOD1, UCX_ colliders, ANCHOR_ empties
  Workshop_W86_westdoor_curtain_v01.fbx  optional closing curtain for the west bay (pivot = top of opening)
  Workshop_W86_props_v01.fbx     every prop a separate object (LOD0/LOD1 when > 500 tris, UCX_ for large ones)
  Workshop_W86_apron_v01.fbx     concrete apron + UCX
  Workshop_W86_anchors_v01.json, Workshop_W86_materials_v01.json, Workshop_W86_report_v01.json
  Workshop_W86_v01.blend
Blender: Z up, front = -Y, pivot = floor level at the footprint centre.  Unity: (x, y, z) = (-bx, bz, -by).
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws_lib_v01 as L  # noqa: E402
from ws_lib_v01 import MB, Wall, pieces, corrugate, brick_face, brick_bump, whexa, hexa_xy, T, RZ, RX, RY  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FORCE = '--force' in ARGS
REV = 'v01'
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ART = 'C:/Dev/Game/Assets/OnlyVolunteers/Art/'

# ============================================================================ dimensions
HX, HY, WT = 12.0, 6.0, 0.25
IX, IY = HX - WT, HY - WT


def zr(y):
    """Underside of the mono-pitch roof deck (falls to the back)."""
    return 5.0 - 0.05 * y


DOOR_H = 3.6
DOORS = [('East', -8.175, 3.4, 'closed'), ('Middle', 0.0, 3.8, 'open'), ('West', 8.175, 4.0, 'open_openable')]


def door_x(name):
    for n, c, w, _ in DOORS:
        if n == name:
            return c - w / 2, c + w / 2
    raise KeyError(name)


PARTS = [-4.5, 4.5]
PD_Y, PD_H = (0.45, 1.55), 2.2
WIN_Z = (2.5, 3.5)
WIN_BACK = [(-8.175, 1.6), (-3.2, 1.4), (3.2, 1.4), (7.0, 1.4)]
WIN_SIDE = {'West': (-1.5, 1.6), 'East': (1.5, 1.6)}
PIT = (-0.45, 0.45, -3.4, 1.6)
PIT_D = 1.5
STEP_RUN, STEP_RISE, NSTEP = 0.26, 0.25, 5
STAIR_Y0 = PIT[3] - STEP_RUN * NSTEP  # 0.30
COLS = [(-11.625, 0.25), (-10.03, 0.25), (-6.32, 0.25), (-4.5, 0.30), (-2.055, 0.25), (2.055, 0.25),
        (4.5, 0.30), (6.02, 0.25), (10.33, 0.25), (11.625, 0.25)]
LAMPS = [(-2.055, -2.5), (2.055, -2.5), (-2.055, 2.5), (2.055, 2.5),
         (6.02, -3.0), (10.33, -3.0), (6.02, 1.5), (10.33, 1.5), (-10.03, 0.5), (-6.32, 0.5)]
LAMP_Z = 3.9
VAN = dict(length=5.2, width=2.0, height=2.4, centre=(0.0, -2.4))

W_OUT = {'Front': Wall((0, -HY, 0), (1, 0, 0), (0, -1, 0)), 'Back': Wall((0, HY, 0), (-1, 0, 0), (0, 1, 0)),
         'West': Wall((HX, 0, 0), (0, 1, 0), (1, 0, 0)), 'East': Wall((-HX, 0, 0), (0, -1, 0), (-1, 0, 0))}
W_IN = {'Front': Wall((0, -IY, 0), (-1, 0, 0), (0, 1, 0)), 'Back': Wall((0, IY, 0), (1, 0, 0), (0, -1, 0)),
        'West': Wall((IX, 0, 0), (0, -1, 0), (-1, 0, 0)), 'East': Wall((-IX, 0, 0), (0, 1, 0), (1, 0, 0))}
OUT_EXT = {'Front': (-HX, HX), 'Back': (-HX, HX), 'West': (-HY, HY), 'East': (-HY, HY)}
IN_EXT = {'Front': (-IX, IX), 'Back': (-IX, IX), 'West': (-IY, IY), 'East': (-IY, IY)}

# world openings: (wall, kind, pa, pb, z0, z1)
OPENINGS = []
for n, c, w, st in DOORS:
    OPENINGS.append(('Front', 'door_' + n, (c - w / 2, -HY), (c + w / 2, -HY), 0.0, DOOR_H))
for i, (c, w) in enumerate(WIN_BACK):
    OPENINGS.append(('Back', 'win_back%d' % i, (c - w / 2, HY), (c + w / 2, HY), WIN_Z[0], WIN_Z[1]))
for side, (c, w) in WIN_SIDE.items():
    x = HX if side == 'West' else -HX
    OPENINGS.append((side, 'win_' + side, (x, c - w / 2), (x, c + w / 2), WIN_Z[0], WIN_Z[1]))


def ops_for(wall, W):
    out = []
    for wn, kind, pa, pb, z0, z1 in OPENINGS:
        if wn != wall:
            continue
        ua, ub = W.u_of((pa[0], pa[1], 0)), W.u_of((pb[0], pb[1], 0))
        out.append((min(ua, ub), max(ua, ub), z0, z1, kind))
    return out


def topfn(W, dz=0.0):
    return lambda u: zr((W.O + W.T * u).y) + dz


# ============================================================================ materials
MATS = {
    'MAT_WS_corrugated_grey': dict(tex='TextureTest_v01/Source_v07/T7_metal_trapez_albedo.png',
                                   nrm='TextureTest_v01/Source_v07/T7_metal_trapez_normal.png', tile=1.5,
                                   tint='#A3A8AB', smooth=0.35, metal=0.3, sheet='1 / option 1',
                                   note='Wall cladding, interior liner, roof deck. Geometry carries 0.1875 m trapezoid ribs; texture adds fine rib shading.'),
    'MAT_WS_red_steel': dict(tex='MapTextures_W86/T1/Textures/T1_painted_metal_albedo.png', nrm=None, tile=2.0,
                             tint='#B23A2C', smooth=0.35, metal=0.1, sheet='4 + 10 / option 1',
                             note='Columns, rafters, braces, shelving, tool chests, drawer fronts, heater cabinet.'),
    'MAT_WS_brick': dict(tex='StyleKit_v3/Textures/3a_brick/3a_brick_v07_albedo.png',
                         nrm='StyleKit_v3/Textures/3a_brick/3a_brick_v07_normal.png', tile=2.0, tint='#FFFFFF',
                         smooth=0.08, metal=0.0, sheet='2 / option 1 (tile 2 m instead of 3 m)',
                         note='Geometric courses every 0.125 m from z=0.05 and protruding bricks are aligned to this texture at tile 2.0 m, offset 0. Do not change the tile.'),
    'MAT_WS_concrete': dict(tex='MapTextures_W86/T1/Textures/T1_concrete_light_albedo.png',
                            nrm='MapTextures_W86/T1/Textures/T1_concrete_light_normal.png', tile=3.0, tint='#C9C5BD',
                            smooth=0.22, metal=0.0, sheet='5 / option 1', note='Bay floors, foundation band, thresholds.'),
    'MAT_WS_concrete_pit': dict(tex='MapTextures_W86/T1/Textures/T1_concrete_bridge_albedo.png',
                                nrm='MapTextures_W86/T1/Textures/T1_concrete_bridge_normal.png', tile=4.0,
                                tint='#B9B6B0', smooth=0.18, metal=0.0, sheet='7 / option 1', note='Inspection pit walls, steps, pit floor.'),
    'MAT_WS_apron': dict(tex='MapTextures_W86/T1/Textures/T1_concrete_slabs_old_albedo.png',
                         nrm='MapTextures_W86/T1/Textures/T1_concrete_slabs_old_normal.png', tile=6.0, tint='#CFCCC6',
                         smooth=0.12, metal=0.0, sheet='6 / note (old slabs over the dirt yard)',
                         note='Apron slab only; the yard around stays terrain layer 1b_dirt_road (sheet 6 option 1).'),
    'MAT_WS_yellow_rail': dict(tex='MapTextures_W86/T1/Textures/T1_painted_metal_albedo.png', nrm=None, tile=1.0,
                               tint='#E0B13A', smooth=0.45, metal=0.1, sheet='8 / option 1',
                               note='Pit rails, hoop guard, bollards, step nosings, hand-in zone floor outline, hose.'),
    'MAT_WS_rubber': dict(tex=None, nrm=None, tile=1.0, tint='#2B2B2E', smooth=0.18, metal=0.0, sheet='-',
                          note='Tyres, castors, seals, phone, plastic chair. Plain colour.'),
    'MAT_WS_metal_worn': dict(tex='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_albedo.png',
                              nrm='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_normal.png',
                              tile=2.0, tint='#9AA0A6', smooth=0.42, metal=0.55, sheet='9 / option 1',
                              note='Galvanised / bare steel: workbench frames, pipes, pit edge angle, handles, desk.'),
    'MAT_WS_metal_dark': dict(tex='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_albedo.png',
                              nrm='StyleKit_v3/Textures/6b_lightly_weathered_metal/6b_lightly_weathered_metal_v07_normal.png',
                              tile=2.0, tint='#45494E', smooth=0.35, metal=0.35, sheet='9 / option 1 (dark tint)',
                              note='Trims, fascia, door hoods/guides/coil boxes, window frames, conduits, cabinets.'),
    'MAT_WS_glass': dict(tex=None, nrm=None, tile=1.0, tint='#6F8A96', smooth=0.92, metal=0.0, alpha=0.35, sheet='-',
                         note='Window panes (two-sided quads). URP Lit Transparent, alpha ~0.35; opaque is acceptable.'),
    'MAT_WS_wood': dict(tex='StyleKit_v3/Textures/5a_wood_planks_fences/5a_wood_planks_fences_v07_albedo.png',
                        nrm='StyleKit_v3/Textures/5a_wood_planks_fences/5a_wood_planks_fences_v07_normal.png', tile=2.0,
                        tint='#FFFFFF', smooth=0.15, metal=0.0, sheet='- (StyleKit 5a)', note='Bench tops, crates, pegboards, tool handles.'),
    'MAT_WS_rollerdoor_red': dict(tex='NEW:Workshop_rollerdoor_v01.png', nrm=None, tile=0.64, tint='#B23A2C',
                                  smooth=0.38, metal=0.15, sheet='3 / new texture',
                                  note='Outer face of roller-door curtains. Geometric lamellae every 0.08 m are aligned to the texture (UV v = z - 0.10).'),
    'MAT_WS_rollerdoor_grey': dict(tex='NEW:Workshop_rollerdoor_v01.png', nrm=None, tile=0.64, tint='#5A6067',
                                   smooth=0.35, metal=0.2, sheet='3 / new texture (dark grey, as in reference 04)',
                                   note='Inner face of the curtains.'),
    'MAT_WS_paint_white': dict(tex=None, nrm=None, tile=1.0, tint='#E4DDC8', smooth=0.3, metal=0.0, sheet='-',
                               note='Floor markings (flush, cut into the floor), sign board, calendar, lamp housings.'),
    'MAT_WS_emissive': dict(tex=None, nrm=None, tile=1.0, tint='#FFF3DA', smooth=0.5, metal=0.0, emission='#FFF3DA',
                            sheet='-', note='Lamp diffusers. Emission ~2-4 (HDR), pair with real lights at the anchors.'),
    'MAT_WS_fabric': dict(tex=None, nrm=None, tile=1.0, tint='#6A2C26', smooth=0.05, metal=0.0, sheet='-',
                          note='Sofa, office chair upholstery, rag (reference A: dark red).'),
    'MAT_WS_oil': dict(tex=None, nrm=None, tile=1.0, tint='#24211E', smooth=0.7, metal=0.0, sheet='-',
                       note='Oil stains on the floor (4 mm above it).'),
    'MAT_WS_cardboard': dict(tex=None, nrm=None, tile=1.0, tint='#B48F63', smooth=0.1, metal=0.0, sheet='-',
                             note='Cardboard boxes on shelves.'),
}


def hex2lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def make_materials():
    lib = {}
    for name, m in MATS.items():
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        col = hex2lin(m['tint'])
        bsdf.inputs['Base Color'].default_value = (*col, 1.0)
        bsdf.inputs['Roughness'].default_value = 1.0 - m['smooth']
        bsdf.inputs['Metallic'].default_value = m['metal']
        mat.diffuse_color = (*col, 1.0)
        if m.get('emission'):
            bsdf.inputs['Emission Color'].default_value = (*hex2lin(m['emission']), 1.0)
            bsdf.inputs['Emission Strength'].default_value = 3.0
        lib[name] = mat
    return lib


def texture_materials(lib):
    """Preview-only: project textures x tint (UVs are metres, mapping scale = 1/tile)."""
    for name, m in MATS.items():
        if not m['tex']:
            if m.get('alpha'):
                mat = lib[name]
                bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                bsdf.inputs['Alpha'].default_value = m['alpha']
                try:
                    mat.surface_render_method = 'BLENDED'
                except Exception:
                    pass
            continue
        path = os.path.join(OUT, m['tex'][4:]) if m['tex'].startswith('NEW:') else ART + m['tex']
        mat = lib[name]
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        s = 1.0 / m['tile']
        mp.inputs['Scale'].default_value = (s, s, 1.0)
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(path, check_existing=True)
        mul = nt.nodes.new('ShaderNodeVectorMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = hex2lin(m['tint'])
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


M_CORR, M_RED, M_BRICK, M_CONC, M_PIT = 'MAT_WS_corrugated_grey', 'MAT_WS_red_steel', 'MAT_WS_brick', 'MAT_WS_concrete', 'MAT_WS_concrete_pit'
M_YEL, M_RUB, M_WORN, M_DARK, M_GLASS = 'MAT_WS_yellow_rail', 'MAT_WS_rubber', 'MAT_WS_metal_worn', 'MAT_WS_metal_dark', 'MAT_WS_glass'
M_WOOD, M_DRED, M_DGREY, M_WHITE, M_EMIT = 'MAT_WS_wood', 'MAT_WS_rollerdoor_red', 'MAT_WS_rollerdoor_grey', 'MAT_WS_paint_white', 'MAT_WS_emissive'
M_FAB, M_OIL, M_CARD, M_APRON = 'MAT_WS_fabric', 'MAT_WS_oil', 'MAT_WS_cardboard', 'MAT_WS_apron'

# ============================================================================ shell
CORR_P = 0.1875
UCX = []          # (name_suffix, points)
ANCHORS = {}      # name -> dict


def ucx_box(mn, mx):
    UCX.append([Vector((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])])


def ucx_pts(pts):
    UCX.append([Vector(p) for p in pts])


def build_shell(lod):
    mb = MB('WS_Building_Shell_LOD%d' % lod)
    flat = lod > 0
    rnd = random.Random(86)
    for wn, W in W_OUT.items():
        u0, u1 = OUT_EXT[wn]
        ops = ops_for(wn, W)
        op4 = [o[:4] for o in ops]
        # --- brick base course and cladding
        for a, b, za, zb in pieces(u0, u1, 0.05, 1.30, op4):
            brick_face(mb, W, a, b, za, zb, M_BRICK, flat=flat)
            if not flat:  # selected protruding bricks, kept away from edges
                for k in range(int(round((zb - za) / L.BRICK_COURSE))):
                    kk = int(round((za - L.BRICK_Z0) / L.BRICK_COURSE)) + k
                    off = L.brick_joint_us(kk)
                    j0 = math.ceil((a + 0.3 - off) / L.BRICK_LEN)
                    j1 = math.floor((b - 0.3 - off) / L.BRICK_LEN) - 1
                    for j in range(j0, j1 + 1):
                        if rnd.random() < 0.06:
                            ua = off + j * L.BRICK_LEN + 0.016
                            brick_bump(mb, W, ua, ua + L.BRICK_LEN - 0.032, kk, M_BRICK)
        for a, b, za, zb in pieces(u0, u1, 1.30, topfn(W), op4):
            corrugate(mb, W, a, b, za, zb, M_CORR, CORR_P, -0.045, -0.015, flat=flat)
        # --- foundation band (concrete, can be sunk 0.3-0.6 m: finished face down to -0.8)
        e = 0.02
        lo, hi = u0 - e, u1 + e
        doors = sorted((o[0], o[1]) for o in ops if o[4].startswith('door'))
        br = sorted(set([lo, hi] + [x for d in doors for x in d]))
        for a, b in zip(br, br[1:]):
            m = 0.5 * (a + b)
            is_door = any(d[0] <= m <= d[1] for d in doors)
            ztop = 0.0 if is_door else 0.05
            mb.face([W.P(a, -0.8, e), W.P(b, -0.8, e), W.P(b, ztop, e), W.P(a, ztop, e)], M_CONC, want=W.N, uvax=W.uax())
            if is_door:
                mb.face([W.P(a, 0.0, -WT), W.P(b, 0.0, -WT), W.P(b, 0.0, e), W.P(a, 0.0, e)], M_CONC, want=(0, 0, 1))
            else:
                la, lb = a, b
                if wn in ('West', 'East'):
                    la, lb = max(a, u0 + 0.012), min(b, u1 - 0.012)
                if lb > la:
                    mb.face([W.P(la, 0.05, -0.012), W.P(lb, 0.05, -0.012), W.P(lb, 0.05, e), W.P(la, 0.05, e)], M_CONC, want=(0, 0, 1))
        # --- cap flashing on top of the brick (with end caps at openings)
        trims = sorted((o[0] - 0.10, o[1] + 0.10) for o in ops if o[4].startswith('door'))
        f_lo, f_hi = u0 - 0.05, u1 + 0.05
        br = [f_lo] + [x for t in trims for x in t] + [f_hi]
        zb_f = 1.265 if wn in ('Front', 'Back') else 1.271
        poly = [(0.0, zb_f), (0.045, zb_f), (0.045, 1.30), (-0.05, 1.36), (-0.05, 1.29)]
        for a, b in zip(br[0::2], br[1::2]):
            if b - a > 0.01:
                mb.prism(poly, a, b, M_DARK, lambda s, t, w, W=W: W.P(w, t, s), skip_sides=(3, 4))
        # --- openings: reveals, trims, sills, frames, glass
        for ou0, ou1, oz0, oz1, kind in ops:
            is_door = kind.startswith('door')
            d_in, d_out = -WT, 0.025
            mb.face([W.P(ou0, oz0, d_in), W.P(ou0, oz0, d_out), W.P(ou0, oz1, d_out), W.P(ou0, oz1, d_in)], M_DARK, want=W.T)
            mb.face([W.P(ou1, oz0, d_in), W.P(ou1, oz0, d_out), W.P(ou1, oz1, d_out), W.P(ou1, oz1, d_in)], M_DARK, want=-W.T)
            mb.face([W.P(ou0, oz1, d_in), W.P(ou1, oz1, d_in), W.P(ou1, oz1, d_out), W.P(ou0, oz1, d_out)], M_DARK, want=(0, 0, -1))
            if is_door:
                whexa(mb, W, ou0 - 0.10, ou0, -0.045, 0.025, 0.05, oz1, M_DARK, skip=('x+', 'z-', 'y-'))
                whexa(mb, W, ou1, ou1 + 0.10, -0.045, 0.025, 0.05, oz1, M_DARK, skip=('x-', 'z-', 'y-'))
                hood = [(0.025, 3.6), (0.20, 3.6), (0.20, 4.02), (0.025, 4.16)]
                mb.prism(hood, ou0 - 0.12, ou1 + 0.12, M_DARK, lambda s, t, w, W=W: W.P(w, t, s), skip_sides=(3,))
                build_door(mb, W, kind[5:], ou0, ou1, lod)
            else:
                mb.face([W.P(ou0, oz0, d_in), W.P(ou1, oz0, d_in), W.P(ou1, oz0, -0.045), W.P(ou0, oz0, -0.045)], M_DARK, want=(0, 0, 1))
                sill = [(-0.045, oz0), (-0.045, oz0 - 0.05), (0.07, oz0 - 0.05), (0.07, oz0 - 0.03)]
                mb.prism(sill, ou0 - 0.12, ou1 + 0.12, M_DARK, lambda s, t, w, W=W: W.P(w, t, s), skip_sides=(0,))
                if not flat:
                    whexa(mb, W, ou0 - 0.08, ou0, -0.045, 0.02, oz0, oz1, M_DARK, skip=('x+', 'z-', 'z+', 'y-'))
                    whexa(mb, W, ou1, ou1 + 0.08, -0.045, 0.02, oz0, oz1, M_DARK, skip=('x-', 'z-', 'z+', 'y-'))
                    whexa(mb, W, ou0 - 0.08, ou1 + 0.08, -0.045, 0.02, oz1, oz1 + 0.08, M_DARK, skip=('z-', 'y-'))
                # frame + glass
                fd0, fd1 = -0.13, -0.07
                fw = 0.05
                whexa(mb, W, ou0, ou0 + fw, fd0, fd1, oz0, oz1, M_DARK, skip=('x-', 'z-', 'z+'))
                whexa(mb, W, ou1 - fw, ou1, fd0, fd1, oz0, oz1, M_DARK, skip=('x+', 'z-', 'z+'))
                whexa(mb, W, ou0 + fw, ou1 - fw, fd0, fd1, oz1 - fw, oz1, M_DARK, skip=('x-', 'x+', 'z+'))
                whexa(mb, W, ou0 + fw, ou1 - fw, fd0, fd1, oz0, oz0 + fw, M_DARK, skip=('x-', 'x+', 'z-'))
                um = 0.5 * (ou0 + ou1)
                whexa(mb, W, um - 0.02, um + 0.02, fd0, fd1, oz0 + fw, oz1 - fw, M_DARK, skip=('z-', 'z+'))
                for ga, gb in ((ou0 + fw, um - 0.02), (um + 0.02, ou1 - fw)):
                    za, zb = oz0 + fw, oz1 - fw
                    mb.face([W.P(ga, za, -0.095), W.P(gb, za, -0.095), W.P(gb, zb, -0.095), W.P(ga, zb, -0.095)], M_GLASS, want=W.N)
                    mb.face([W.P(ga, za, -0.105), W.P(gb, za, -0.105), W.P(gb, zb, -0.105), W.P(ga, zb, -0.105)], M_GLASS, want=-W.N)
    # --- corners: quoins (brick zone) and L trims (cladding zone)
    for sx in (-1, 1):
        for sy in (-1, 1):
            if not flat:
                for k in range(10):
                    z0 = L.BRICK_Z0 + k * L.BRICK_COURSE + 0.008
                    z1 = L.BRICK_Z0 + (k + 1) * L.BRICK_COURSE - 0.008
                    lx, ly = (0.25, 0.12) if k % 2 == 0 else (0.12, 0.25)
                    xs = sorted((sx * (HX - lx), sx * (HX + 0.02)))
                    ys = sorted((sy * (HY - ly), sy * (HY + 0.02)))
                    mb.box((xs[0], ys[0], z0), (xs[1], ys[1], z1), M_BRICK)
            tpl = [(11.88, 6.005), (12.005, 6.005), (12.005, 5.88), (11.955, 5.88), (11.955, 5.955), (11.88, 5.955)]
            poly = [(sx * x, sy * y) for x, y in tpl]
            ztop = zr(sy * HY)
            mb.prism(poly, 1.30, ztop, M_DARK, lambda s, t, w: Vector((s, t, w)))
    build_roof(mb, lod)
    return mb


def build_door(mb, W, name, ou0, ou1, lod):
    """Roller door in the opening of the front wall frame W (outer). Guides, curtain or raised bottom bar."""
    for u, sgn in ((ou0, 1), (ou1, -1)):
        a, b = sorted((u, u + sgn * 0.06))
        sk = ('x-',) if sgn > 0 else ('x+',)
        whexa(mb, W, a, b, -0.18, -0.135, 0.0, DOOR_H, M_DARK, skip=sk + ('z-', 'z+'))
        whexa(mb, W, a, b, -0.105, -0.06, 0.0, DOOR_H, M_DARK, skip=sk + ('z-', 'z+'))
    st = dict(DOORS_STATE)[name]
    if st == 'closed':
        curtain(mb, W, ou0, ou1, 0.0, lod)
    else:
        # raised: bottom bar visible just under the lintel, rubber seal below it (clear height 3.48 m)
        whexa(mb, W, ou0 + 0.03, ou1 - 0.03, -0.14, -0.10, 3.50, DOOR_H, M_DARK, skip=('x-', 'x+', 'z+'))
        whexa(mb, W, ou0 + 0.03, ou1 - 0.03, -0.13, -0.11, 3.48, 3.50, M_RUB, skip=('x-', 'x+', 'z+'))


DOORS_STATE = [(n, s) for n, c, w, s in DOORS]


def curtain(mb, W, ou0, ou1, z_base, lod, top=DOOR_H):
    """Closed curtain: rubber seal, bottom bar, lamellae every 0.08 m (front red, back grey)."""
    a, b = ou0 + 0.03, ou1 - 0.03
    whexa(mb, W, a, b, -0.13, -0.11, z_base, z_base + 0.02, M_RUB, skip=('x-', 'x+'))
    whexa(mb, W, a, b, -0.145, -0.095, z_base + 0.02, z_base + 0.10, M_DARK, skip=('x-', 'x+'))
    z0 = z_base + 0.10
    df, g = -0.105, 0.012
    if lod > 0:
        mb.face([W.P(a, z0, df), W.P(b, z0, df), W.P(b, top, df), W.P(a, top, df)], M_DRED, want=W.N, uvax=W.uax(), voff=-z0)
    else:
        prof = []
        n = int(math.floor((top - z0) / 0.08 + 1e-6))
        for j in range(n):
            zj = z0 + 0.08 * j
            prof += [(zj, df - g), (zj + 0.012, df), (zj + 0.068, df)]
        prof.append((z0 + 0.08 * n, df - g))
        if top > z0 + 0.08 * n + 1e-4:
            prof.append((top, df - g))
        for (za, da), (zb, db) in zip(prof, prof[1:]):
            want = W.N * (zb - za) - Vector((0, 0, 1)) * (db - da)
            mb.face([W.P(a, za, da), W.P(b, za, da), W.P(b, zb, db), W.P(a, zb, db)], M_DRED, want=want, uvax=W.uax(), voff=-z0)
    mb.face([W.P(a, z0, -0.135), W.P(b, z0, -0.135), W.P(b, top, -0.135), W.P(a, top, -0.135)], M_DGREY, want=-W.N, uvax=W.uax(), voff=-z0)


def build_roof(mb, lod):
    x0, x1, y0, y1 = -12.2, 12.2, -6.15, 6.45
    th = 0.12
    # underside (ceiling + soffits)
    mb.face([(x0, y0, zr(y0)), (x0, y1, zr(y1)), (x1, y1, zr(y1)), (x1, y0, zr(y0))], M_CORR, want=(0, 0, -1))
    # top: ribs along the slope
    if lod == 0:
        prof = L.periodic_profile(x0, x1, 0.375, L.corr_bps(0.375, 0.0, 0.035))
    else:
        prof = [(x0, 0.0), (x1, 0.0)]
    for (xa, da), (xb, db) in zip(prof, prof[1:]):
        pts = [(xa, y0, zr(y0) + th + da), (xb, y0, zr(y0) + th + db), (xb, y1, zr(y1) + th + db), (xa, y1, zr(y1) + th + da)]
        mb.face(pts, M_CORR, want=(-(db - da), 0, xb - xa), uvax='z')
    # front fascia
    mb.box((-12.25, -6.20, 5.15), (12.25, -6.15, 5.57), M_DARK)
    # side barge trims
    for sx in (-1, 1):
        xa, xb = sorted((sx * 12.2, sx * 12.25))
        hexa_xy(mb, xa, xb, -6.15, 6.50, lambda x, y: zr(y) - 0.12, lambda x, y: zr(y) + th + 0.10, M_DARK, skip=('y-',))
    # back: drip trim + gutter + downpipes
    zg = zr(6.45)
    mb.box((-12.2, 6.45, zg - 0.05), (12.2, 6.49, zg + th + 0.045), M_DARK, skip=('x-', 'x+', 'y-'))
    gpoly = [(6.48, zg + 0.06), (6.48, zg - 0.12), (6.66, zg - 0.12), (6.66, zg + 0.06), (6.64, zg + 0.06),
             (6.64, zg - 0.10), (6.50, zg - 0.10), (6.50, zg + 0.06)]
    mb.prism(gpoly, -12.2, 12.2, M_DARK, lambda s, t, w: Vector((w, s, t)))
    for sx in (-1, 1):
        x = sx * 11.70
        n = 8 if lod == 0 else 5
        pts = [(x, 6.57, zg - 0.12), (x, 6.57, zg - 0.30), (x, 6.10, zg - 0.62), (x, 6.10, 0.30), (x, 6.30, 0.10)]
        mb.tube(pts, 0.05, M_DARK, n=n)
        if lod == 0:
            for z in (0.9, 2.3, 3.6):
                mb.box((x - 0.06, 6.0, z), (x + 0.06, 6.06, z + 0.05), M_DARK, skip=('y-',))
                mb.box((x - 0.065, 6.04, z + 0.006), (x + 0.065, 6.16, z + 0.044), M_DARK)


# ============================================================================ interior
def build_interior(lod):
    mb = MB('WS_Building_Interior_LOD%d' % lod)
    flat = lod > 0
    rnd = random.Random(860)
    # --- inner faces of the outer walls
    for wn, W in W_IN.items():
        u0, u1 = IN_EXT[wn]
        ops = [o[:4] for o in ops_for(wn, W)]
        for a, b, za, zb in pieces(u0, u1, 0.0, 1.80, ops):
            brick_face(mb, W, a, b, za, zb, M_BRICK, flat=flat)
            if not flat:
                for k in range(1, 14):
                    off = L.brick_joint_us(k)
                    j0 = math.ceil((a + 0.4 - off) / L.BRICK_LEN)
                    j1 = math.floor((b - 0.4 - off) / L.BRICK_LEN) - 1
                    for j in range(j0, j1 + 1):
                        if rnd.random() < 0.025:
                            ua = off + j * L.BRICK_LEN + 0.016
                            brick_bump(mb, W, ua, ua + L.BRICK_LEN - 0.032, k, M_BRICK, proud=0.012)
        for a, b, za, zb in pieces(u0, u1, 1.80, topfn(W), ops):
            corrugate(mb, W, a, b, za, zb, M_CORR, CORR_P, -0.03, 0.0, flat=flat)
        cap = [(0.0, 1.78), (0.03, 1.78), (0.03, 1.80), (-0.035, 1.84), (-0.035, 1.79)]
        br = sorted(set([u0, u1] + [x for o in ops if o[2] < 1.8 for x in o[:2]]))
        for a, b in zip(br, br[1:]):
            m = 0.5 * (a + b)
            if any(o[0] <= m <= o[1] and o[2] < 1.8 for o in ops):
                continue
            a2 = a + (0.24 if abs(a - u0) < 1e-6 else 0.005)
            b2 = b - (0.24 if abs(b - u1) < 1e-6 else 0.005)
            mb.prism(cap, a2, b2, M_DARK, lambda s, t, w, W=W: W.P(w, t, s), skip_sides=(3, 4))
    # --- partitions
    for xp in PARTS:
        for sgn in (1, -1):
            W = Wall((xp + sgn * 0.1, 0, 0), (0, sgn, 0), (sgn, 0, 0))
            ua, ub = sorted((W.u_of((0, PD_Y[0], 0)), W.u_of((0, PD_Y[1], 0))))
            ops = [(ua, ub, 0.0, PD_H)]
            top = lambda u, W=W: zr((W.O + W.T * u).y) - 0.3
            for a, b, za, zb in pieces(-IY, IY, 0.0, 1.80, ops):
                brick_face(mb, W, a, b, za, zb, M_BRICK, flat=flat)
            for a, b, za, zb in pieces(-IY, IY, 1.80, top, ops):
                corrugate(mb, W, a, b, za, zb, M_CORR, CORR_P, -0.03, 0.0, flat=flat)
            cap = [(0.0, 1.78), (0.03, 1.78), (0.03, 1.80), (-0.035, 1.84), (-0.035, 1.79)]
            for a, b in ((-IY + 0.24, ua - 0.06), (ub + 0.06, IY - 0.24)):
                mb.prism(cap, a, b, M_DARK, lambda s, t, w, W=W: W.P(w, t, s), skip_sides=(3, 4))
            # architrave around the doorway (steel frame)
            whexa(mb, W, ua - 0.06, ua, -0.012, 0.022, 0.0, PD_H, M_DARK, skip=('x+', 'z-', 'z+', 'y-'))
            whexa(mb, W, ub, ub + 0.06, -0.012, 0.022, 0.0, PD_H, M_DARK, skip=('x-', 'z-', 'z+', 'y-'))
            whexa(mb, W, ua - 0.06, ub + 0.06, -0.03, 0.022, PD_H, PD_H + 0.06, M_DARK, skip=('z-', 'y-'))
            if sgn == 1:  # doorway reveals across the full partition (once)
                d_in, d_out = -0.2 - 0.022, 0.022
                mb.face([W.P(ua, 0, d_in), W.P(ua, 0, d_out), W.P(ua, PD_H, d_out), W.P(ua, PD_H, d_in)], M_DARK, want=W.T)
                mb.face([W.P(ub, 0, d_in), W.P(ub, 0, d_out), W.P(ub, PD_H, d_out), W.P(ub, PD_H, d_in)], M_DARK, want=-W.T)
                mb.face([W.P(ua, PD_H, d_in), W.P(ub, PD_H, d_in), W.P(ub, PD_H, d_out), W.P(ua, PD_H, d_out)], M_DARK, want=(0, 0, -1))
    # --- floor (markings cut in flush: no coplanar overlays)
    pit_hole = (PIT[0], PIT[1], PIT[2], PIT[3])
    paints = [
        ((-0.62, 0.62, PIT[2] - 0.17, PIT[3] + 0.17), M_WHITE),
        ((-0.50, 0.50, PIT[2] - 0.05, PIT[3] + 0.05), M_WORN),
        ((-1.65, -1.55, -5.6, 0.6), M_WHITE), ((1.55, 1.65, -5.6, 0.6), M_WHITE),
        ((-1.65, -1.05, -5.6, -5.5), M_WHITE), ((1.05, 1.65, -5.6, -5.5), M_WHITE),
        ((-1.35, -0.75, 0.55, 0.85), M_DARK),
    ]
    hz = (6.4, 9.95, -5.3, -0.3)   # west-bay hand-in zone outline
    for r in ((hz[0], hz[1], hz[2], hz[2] + 0.08), (hz[0], hz[1], hz[3] - 0.08, hz[3]),
              (hz[0], hz[0] + 0.08, hz[2], hz[3]), (hz[1] - 0.08, hz[1], hz[2], hz[3])):
        paints.append((r, M_YEL))
    floor_grid(mb, -IX, IX, -IY, IY, 0.0, [pit_hole], paints, M_CONC)
    if not flat:  # drain grate bars
        for i in range(6):
            x = -1.32 + i * 0.105
            mb.box((x, 0.58, 0.0), (x + 0.03, 0.82, 0.012), M_DARK, skip=('z-',))
    # oil stains (4 mm above the floor)
    if not flat:
        for cx, cy, r in ((1.0, -1.7, 0.33), (-0.95, -3.9, 0.25), (-3.3, -0.6, 0.28), (-2.7, 4.75, 0.3), (8.6, 1.4, 0.22)):
            pts = []
            n = 9
            for i in range(n):
                a = 2 * math.pi * i / n
                rr = r * (0.7 + 0.3 * rnd.random())
                pts.append((cx + rr * math.cos(a), cy + rr * 0.8 * math.sin(a), 0.004))
            mb.face(pts, M_OIL, want=(0, 0, 1))
    build_pit(mb, lod)
    # --- steel frame: columns, base plates, rafters, braces, purlins
    for xc, w in COLS:
        xa, xb = xc - w / 2, xc + w / 2
        for wy, s in ((-IY, 1), (IY, -1)):
            ya, yb = sorted((wy, wy + s * 0.25))
            sk = ['z-', 'z+', 'y-' if s == 1 else 'y+']
            if xa <= -IX + 1e-6:
                sk.append('x-')
            if xb >= IX - 1e-6:
                sk.append('x+')
            hexa_xy(mb, xa, xb, ya, yb, 0.0, lambda x, y: zr(y) - 0.3, M_RED, skip=tuple(sk))
            if not flat:
                pa, pb = sorted((wy, wy + s * 0.29))
                mb.box((max(xa - 0.025, -IX + 0.003), pa, 0.0), (min(xb + 0.025, IX - 0.003), pb, 0.02), M_DARK, skip=('z-', 'y-' if s == 1 else 'y+'))
                # haunch brace
                yb0 = wy + s * 0.25
                yb1 = wy + s * 0.85
                tri = [(yb0, zr(yb0) - 0.3 - 0.6), (yb0, zr(yb0) - 0.3), (yb1, zr(yb1) - 0.3)]
                mb.prism(tri, xc - 0.025, xc + 0.025, M_RED, lambda s_, t, w: Vector((w, s_, t)))
        sk = ['z+', 'y-', 'y+']
        if xa <= -IX + 1e-6:
            sk.append('x-')
        if xb >= IX - 1e-6:
            sk.append('x+')
        hexa_xy(mb, xa, xb, -IY, IY, lambda x, y: zr(y) - 0.3, lambda x, y: zr(y), M_RED, skip=tuple(sk))
    for sx in (-1, 1):  # side wind posts
        xa, xb = sorted((sx * IX, sx * (IX - 0.25)))
        hexa_xy(mb, xa, xb, -0.125, 0.125, 0.0, lambda x, y: zr(y) - 0.3, M_RED, skip=('z-', 'z+', 'x+' if sx > 0 else 'x-'))
    for xp in PARTS:  # mid columns in the partitions
        hexa_xy(mb, xp - 0.15, xp + 0.15, -2.125, -1.875, 0.0, lambda x, y: zr(y) - 0.3, M_RED, skip=('z-', 'z+'))
    if not flat:
        for yc in (-3.0, 0.0, 3.0):
            hexa_xy(mb, -IX, IX, yc - 0.06, yc + 0.06, lambda x, y: zr(y) - 0.15, lambda x, y: zr(y), M_RED, skip=('z+', 'x-', 'x+'))
    # --- door headers and coil boxes (inside)
    Wf = W_OUT['Front']
    for n, c, w, st in DOORS:
        x0, x1 = c - w / 2, c + w / 2
        cl = max(xc + ww / 2 for xc, ww in COLS if xc + ww / 2 <= x0 + 1e-6)
        cr = min(xc - ww / 2 for xc, ww in COLS if xc - ww / 2 >= x1 - 1e-6)
        mb.box((cl, -IY, 3.6), (cr, -IY + 0.22, 3.85), M_RED, skip=('y-', 'x-', 'x+'))
        coil = [(-0.25, 3.86), (-0.58, 3.86), (-0.68, 3.96), (-0.68, 4.42), (-0.25, 4.42)]
        mb.prism(coil, x0, x1, M_DARK, lambda s, t, w_, W=Wf: W.P(w_, t, s), skip_sides=(4,))
    if not flat:
        build_services(mb)
    else:
        for x, y in LAMPS:
            mb.box((x - 0.08, y - 0.62, LAMP_Z - 0.07), (x + 0.08, y + 0.62, LAMP_Z), M_WHITE, mats={'z-': M_EMIT})
    return mb


def floor_grid(mb, x0, x1, y0, y1, z, holes, paints, base_mat):
    xs, ys = {x0, x1}, {y0, y1}
    for r in holes + [p[0] for p in paints]:
        for x in r[:2]:
            if x0 < x < x1:
                xs.add(round(x, 5))
        for y in r[2:]:
            if y0 < y < y1:
                ys.add(round(y, 5))
    xs, ys = sorted(xs), sorted(ys)

    def cls(cx, cy):
        for h in holes:
            if h[0] < cx < h[1] and h[2] < cy < h[3]:
                return None
        m = base_mat
        for r, mat in paints:
            if r[0] < cx < r[1] and r[2] < cy < r[3]:
                m = mat
        return m

    def emit(xa, xb, ya, yb, m):
        mb.face([(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], m, want=(0, 0, 1))

    for ya, yb in zip(ys, ys[1:]):
        cy = 0.5 * (ya + yb)
        run = None
        for xa, xb in zip(xs, xs[1:]):
            m = cls(0.5 * (xa + xb), cy)
            if run is not None and run[2] == m:
                run[1] = xb
            else:
                if run is not None and run[2]:
                    emit(run[0], run[1], ya, yb, run[2])
                run = [xa, xb, m]
        if run is not None and run[2]:
            emit(run[0], run[1], ya, yb, run[2])


def build_pit(mb, lod):
    x0, x1, y0, y1 = PIT
    zb = -PIT_D
    frames = [Wall((x0, 0, 0), (0, 1, 0), (1, 0, 0)), Wall((x1, 0, 0), (0, -1, 0), (-1, 0, 0)), Wall((0, y0, 0), (-1, 0, 0), (0, 1, 0))]
    for i, W in enumerate(frames):
        if i < 2:
            ua, ub = sorted((W.u_of((0, y0, 0)), W.u_of((0, y1, 0))))
        else:
            ua, ub = sorted((W.u_of((x0, 0, 0)), W.u_of((x1, 0, 0))))
        # edge angle (steel) on the top 6 cm
        mb.face([W.P(ua, -0.06, 0), W.P(ub, -0.06, 0), W.P(ub, 0, 0), W.P(ua, 0, 0)], M_WORN, want=W.N)
        niches = []
        if i < 2 and lod == 0:
            for yc in (-2.3, -0.6):
                u = W.u_of((0, yc, 0))
                niches.append((u - 0.15, u + 0.15, -0.95, -0.65))
        for a, b, za, zb2 in pieces(ua, ub, zb, -0.06, niches):
            mb.face([W.P(a, za, 0), W.P(b, za, 0), W.P(b, zb2, 0), W.P(a, zb2, 0)], M_PIT, want=W.N)
        for a, b, za, zb2 in niches:
            dd = -0.12
            mb.face([W.P(a, za, dd), W.P(a, za, 0), W.P(a, zb2, 0), W.P(a, zb2, dd)], M_PIT, want=W.T)
            mb.face([W.P(b, za, dd), W.P(b, za, 0), W.P(b, zb2, 0), W.P(b, zb2, dd)], M_PIT, want=-W.T)
            mb.face([W.P(a, za, dd), W.P(b, za, dd), W.P(b, za, 0), W.P(a, za, 0)], M_PIT, want=(0, 0, 1))
            mb.face([W.P(a, zb2, dd), W.P(b, zb2, dd), W.P(b, zb2, 0), W.P(a, zb2, 0)], M_PIT, want=(0, 0, -1))
            mb.face([W.P(a, za, dd), W.P(b, za, dd), W.P(b, zb2, dd), W.P(a, zb2, dd)], M_EMIT, want=W.N)
    # stair end: edge angle + risers + treads with yellow nosings
    mb.face([(x0, y1, -0.06), (x1, y1, -0.06), (x1, y1, 0), (x0, y1, 0)], M_WORN, want=(0, -1, 0))
    for k in range(1, NSTEP + 2):
        yr = y1 - STEP_RUN * (k - 1)
        ztop = -0.06 if k == 1 else -STEP_RISE * (k - 1)
        zbot = -STEP_RISE * k if k <= NSTEP else zb
        mb.face([(x0, yr, zbot), (x1, yr, zbot), (x1, yr, ztop), (x0, yr, ztop)], M_PIT, want=(0, -1, 0))
        if k <= NSTEP:
            zt = -STEP_RISE * k
            ya = yr - STEP_RUN
            mb.face([(x0, ya, zt), (x1, ya, zt), (x1, ya + 0.05, zt), (x0, ya + 0.05, zt)], M_YEL, want=(0, 0, 1))
            mb.face([(x0, ya + 0.05, zt), (x1, ya + 0.05, zt), (x1, yr, zt), (x0, yr, zt)], M_PIT, want=(0, 0, 1))
    mb.face([(x0, y0, zb), (x1, y0, zb), (x1, STAIR_Y0, zb), (x0, STAIR_Y0, zb)], M_PIT, want=(0, 0, 1))
    # rails beside the stairs and the hoop guard by the drain
    n = 8 if lod == 0 else 4
    for sx in (-1, 1):
        x = sx * 0.68
        ya, yb = STAIR_Y0 + 0.15, y1 - 0.05
        for y in (ya, yb):
            mb.cyl((x, y, 0.0), (x, y, 1.0), 0.03, M_YEL, n=n, caps=(False, True))
            if lod == 0:
                mb.box((x - 0.06, y - 0.06, 0.0), (x + 0.06, y + 0.06, 0.012), M_DARK, skip=('z-',))
        for z in (0.55, 1.0):
            mb.cyl((x, ya - 0.03, z), (x, yb + 0.03, z), 0.025, M_YEL, n=n)
        ucx_box((x - 0.04, ya - 0.04, 0.0), (x + 0.04, yb + 0.04, 1.05))
    hx = -1.6
    pts = [(hx, 0.5, 0.0), (hx, 0.5, 0.75), (hx, 0.62, 0.9), (hx, 0.98, 0.9), (hx, 1.1, 0.75), (hx, 1.1, 0.0)]
    mb.tube(pts, 0.035, M_YEL, n=n, caps=(False, False))
    ucx_box((hx - 0.05, 0.45, 0.0), (hx + 0.05, 1.15, 0.92))


def build_services(mb):
    """LOD0-only fixed services: lamps on rods, air line, conduits, electrical box, heater, bulkhead, hook."""
    for x, y in LAMPS:
        mb.box((x - 0.08, y - 0.62, LAMP_Z - 0.07), (x + 0.08, y + 0.62, LAMP_Z), M_WHITE, mats={'z-': M_DARK})
        mb.box((x - 0.06, y - 0.58, LAMP_Z - 0.075), (x + 0.06, y + 0.58, LAMP_Z - 0.07), M_EMIT, skip=('z+',))
        for dy in (-0.45, 0.45):
            yy = y + dy
            mb.cyl((x, yy, LAMP_Z), (x, yy, zr(yy) - 0.3), 0.008, M_DARK, n=4, caps=(False, False))
            mb.box((x - 0.05, yy - 0.03, zr(yy) - 0.32), (x + 0.05, yy + 0.03, zr(yy) - 0.3), M_DARK, skip=('z+',))
    # compressed-air line on the east partition (middle-bay face) and the back wall
    ax = -4.28
    az = 2.3
    path = [(ax, -5.45, az), (ax, 5.62, az), (-2.6, 5.62, az), (-2.6, 5.62, 1.15)]
    mb.tube(path, 0.025, M_WORN, n=8)
    mb.tube([(ax, -0.4, az), (ax, -0.4, 1.3)], 0.025, M_WORN, n=8, caps=(False, True))
    mb.box((ax - 0.05, -0.45, 1.36), (ax + 0.05, -0.35, 1.46), M_RED)                     # valve body
    mb.box((ax + 0.05, -0.41, 1.40), (ax + 0.16, -0.39, 1.42), M_RED)                     # valve lever
    mb.cyl((ax, -0.4, 1.3), (ax, -0.4, 1.22), 0.03, M_WORN, n=8)                           # coupling
    for y in (-4.5, -3.0, -1.2, 0.9, 2.4, 3.9, 5.2):
        mb.box((-4.4, y - 0.02, az - 0.04), (ax + 0.03, y + 0.02, az + 0.04), M_DARK, skip=('x-',))
    for x in (-3.6,):
        mb.box((x - 0.02, 5.6, az - 0.04), (x + 0.02, IY, az + 0.04), M_DARK, skip=('y+',))
    mb.box((-2.64, 5.6, 1.6), (-2.56, IY, 1.65), M_DARK, skip=('y+',))
    # electrical box + conduits (middle bay, back wall)
    mb.box((-0.75, 5.55, 1.35), (-0.15, IY, 2.15), M_WORN, skip=('y+',))
    mb.box((-0.72, 5.54, 1.38), (-0.18, 5.55, 2.12), M_WORN, skip=('y+',))
    mb.box((-0.24, 5.52, 1.70), (-0.21, 5.54, 1.80), M_DARK, skip=('y+',))
    for x in (-0.6, -0.45, -0.3):
        mb.cyl((x, 5.68, 2.15), (x, 5.68, 4.3), 0.016, M_DARK, n=6, caps=(False, False))
    mb.tube([(-1.85, 5.68, 4.3), (1.85, 5.68, 4.3)], 0.018, M_DARK, n=6)
    for x in (-1.85, 1.85):
        mb.cyl((x, 5.68, 4.3), (x, 5.68, zr(5.68)), 0.018, M_DARK, n=6, caps=(False, False))
    for x in (-1.2, 0.6, 1.4):
        mb.box((x - 0.02, 5.66, 4.27), (x + 0.02, IY, 4.33), M_DARK, skip=('y+',))
    # light switch by the middle/west doorway + conduit
    mb.box((4.36, 0.2, 1.2), (4.40, 0.3, 1.32), M_DARK, skip=('x+',))
    mb.cyl((4.385, 0.25, 1.32), (4.385, 0.25, zr(0.25) - 0.3), 0.012, M_DARK, n=6, caps=(False, False))
    # west bay: heater cabinet with pipe and flanges (reference 04)
    for fx in (5.03, 5.62):
        for fy in (5.29, 5.66):
            mb.box((fx, fy, 0.0), (fx + 0.05, fy + 0.05, 0.08), M_DARK, skip=('z-',))
    mb.box((5.0, 5.27, 0.08), (5.7, 5.72, 1.05), M_RED, skip=('y+',))
    mb.box((5.06, 5.255, 0.16), (5.64, 5.27, 0.96), M_RED, skip=('y+',))
    mb.box((5.55, 5.24, 0.5), (5.58, 5.255, 0.62), M_WORN, skip=('y+',))
    mb.box((5.1, 5.3, 1.05), (5.6, 5.6, 1.08), M_DARK, skip=('z-',))
    hp = [(5.35, 5.42, 1.08), (5.35, 5.42, 1.6), (7.8, 5.42, 1.6), (7.8, IY, 1.6)]
    mb.tube(hp, 0.04, M_WORN, n=8, caps=(False, False))
    mb.cyl((5.35, 5.42, 1.08), (5.35, 5.42, 1.16), 0.075, M_RED, n=8)
    mb.cyl((7.8, IY - 0.04, 1.6), (7.8, IY, 1.6), 0.085, M_RED, n=8, caps=(True, False))
    for x in (6.6, 7.3):
        mb.box((x - 0.02, 5.46, 1.56), (x + 0.02, IY, 1.64), M_DARK, skip=('y+',))
    # bulkhead lamp with conduit (west bay back wall)
    bx, bz = 9.4, 2.6
    mb.cyl((bx, IY, bz), (bx, IY - 0.10, bz), 0.09, M_DARK, n=10, caps=(False, True))
    mb.cyl((bx, IY - 0.10, bz), (bx, IY - 0.16, bz), 0.07, M_EMIT, n=10, caps=(False, True))
    mb.box((bx - 0.075, IY - 0.175, bz - 0.008), (bx + 0.075, IY - 0.165, bz + 0.008), M_DARK)
    mb.box((bx - 0.008, IY - 0.175, bz - 0.075), (bx + 0.008, IY - 0.165, bz + 0.075), M_DARK)
    mb.cyl((bx, IY - 0.04, bz + 0.09), (bx, IY - 0.04, zr(IY - 0.04)), 0.014, M_DARK, n=6, caps=(False, False))
    # coat hook with rag (west bay)
    mb.box((6.86, IY - 0.02, 1.76), (6.94, IY, 1.84), M_DARK, skip=('y+',))
    mb.box((6.89, IY - 0.08, 1.78), (6.91, IY - 0.02, 1.80), M_DARK)
    rag = MB('rag')
    rag.box((-0.1, -0.02, -0.46), (0.1, 0.02, 0.0), M_FAB)
    mb.merge(rag, T(6.9, IY - 0.07, 1.79) @ RY(4))


# ============================================================================ colliders + anchors
def building_colliders():
    pit = PIT
    ucx_box((-IX, -HY - 0.02, -0.3), (pit[0], IY, 0.0))
    ucx_box((pit[1], -HY - 0.02, -0.3), (IX, IY, 0.0))
    ucx_box((pit[0], -HY - 0.02, -0.3), (pit[1], pit[2], 0.0))
    ucx_box((pit[0], pit[3], -0.3), (pit[1], IY, 0.0))
    ucx_box((pit[0] - 0.2, pit[2] - 0.2, -PIT_D - 0.2), (pit[0], pit[3], 0.0))
    ucx_box((pit[1], pit[2] - 0.2, -PIT_D - 0.2), (pit[1] + 0.2, pit[3], 0.0))
    ucx_box((pit[0], pit[2] - 0.2, -PIT_D - 0.2), (pit[1], pit[2], 0.0))
    ucx_box((pit[0], pit[2], -PIT_D - 0.2), (pit[1], pit[3], -PIT_D))
    ucx_pts([(x, y, z) for x in pit[:2] for (y, z) in ((pit[3], 0.0), (pit[3], -PIT_D), (STAIR_Y0 - 0.02, -PIT_D))])
    # front wall piers + lintels (+ closed east door)
    xs = [(-HX - 0.02, door_x('East')[0]), (door_x('East')[1], door_x('Middle')[0]),
          (door_x('Middle')[1], door_x('West')[0]), (door_x('West')[1], HX + 0.02)]
    for a, b in xs:
        ucx_box((a, -HY - 0.02, -0.8), (b, -IY, zr(-HY)))
    for n, c, w, st in DOORS:
        a, b = c - w / 2, c + w / 2
        ucx_box((a, -HY - 0.02, DOOR_H), (b, -IY, zr(-HY)))
        if st == 'closed':
            ucx_box((a, -HY + 0.05, 0.0), (b, -HY + 0.17, DOOR_H))
    ucx_box((-HX - 0.02, IY, -0.8), (HX + 0.02, HY + 0.02, zr(HY)))
    for sx in (-1, 1):
        xa, xb = sorted((sx * IX, sx * (HX + 0.02)))
        ucx_pts([(x, y, z) for x in (xa, xb) for y in (-HY, HY) for z in (-0.8, zr(y))])
    for xp in PARTS:
        for ya, yb, za in ((-IY, PD_Y[0], 0.0), (PD_Y[1], IY, 0.0), (PD_Y[0], PD_Y[1], PD_H)):
            ucx_pts([(x, y, z) for x in (xp - 0.15, xp + 0.15) for y in (ya, yb) for z in (za, zr(y))])
    ucx_pts([(x, y, z) for x in (-12.25, 12.25) for y in (-6.2, 6.5) for z in (zr(y), zr(y) + 0.17)])
    for xc, w in COLS:
        if abs(abs(xc) - 4.5) < 1e-6:
            continue
        for wy, s in ((-IY, 1), (IY, -1)):
            ya, yb = sorted((wy, wy + s * 0.25))
            ucx_box((xc - w / 2, ya, 0.0), (xc + w / 2, yb, zr(ya) - 0.3))
    for sx in (-1, 1):
        xa, xb = sorted((sx * IX, sx * (IX - 0.25)))
        ucx_box((xa, -0.125, 0.0), (xb, 0.125, 4.6))
    for xp in PARTS:
        ucx_box((xp - 0.15, -2.125, 0.0), (xp + 0.15, -1.875, 4.8))


def U(p):
    """Blender building space -> Unity local (x, y, z)."""
    return [round(-p[0], 4), round(p[2], 4), round(-p[1], 4)]


def Usize(sx, sy, sz):
    """Blender (x, y, z) extents -> Unity (x, y, z) extents."""
    return [round(sx, 4), round(sz, 4), round(sy, 4)]


def uyaw(bdeg):
    """Blender yaw (front = -Y) -> Unity yaw (forward = +Z)."""
    y = -bdeg % 360.0
    return round(y if y <= 180 else y - 360, 2)


def collect_anchors(props):
    A = {}
    vc = VAN['centre']
    A['middle_bay_repair_zone'] = dict(position=U((0.0, -2.55, 0.0)), size=Usize(3.2, 6.4, 3.0), yaw=0.0,
                                       note='Box (bottom-centre position). Covers the van parked over the pit, door line to the pit stairs.')
    A['van_park_point'] = dict(position=U((vc[0], vc[1], 0.0)), yaw=180.0,
                               note='Van centre on the floor, nose toward the back wall (Unity -Z); front bumper at the pit stairs, wheels straddle the pit.')
    A['pit'] = dict(position=U((0.0, 0.5 * (PIT[2] + PIT[3]), 0.0)), size=Usize(PIT[1] - PIT[0], PIT[3] - PIT[2], PIT_D), depth=PIT_D,
                    floor_y=-PIT_D, stairs_top_edge=U((0.0, PIT[3], 0.0)), stairs_bottom=U((0.0, STAIR_Y0, -PIT_D)),
                    note='Opening at floor level; stairs (5 steps, 0.25 rise) at the back end, descending toward the door. '
                         'The pit shell reaches y=-1.7 (colliders): terrain under it must be cut (terrain hole) or lowered below -1.7, '
                         'otherwise terrain shows inside the pit.')
    A['mechanic_standing_point'] = dict(position=U((2.85, 2.2, 0.0)), yaw=0.0,
                                        note='Beside the desk/pit stairs, facing the door (Unity +Z).')
    A['mechanic_desk_seat'] = dict(position=U((3.35, 3.35, 0.0)), yaw=uyaw(90),
                                   note='Office chair in front of the desk; seated mechanic faces the desk/partition.')
    A['west_bay_handin_zone'] = dict(position=U((0.5 * (6.4 + 9.95), -2.8, 0.0)), size=Usize(3.55, 5.0, 2.8), yaw=0.0,
                                     note='Clear floor 3.55 x 5.0 m, outlined in yellow; reached through the open west door.')
    A['doors'] = {}
    for n, c, w, st in DOORS:
        A['doors'][n] = dict(position=U((c, -HY, 0.0)), width=w, height=DOOR_H,
                             clear_height=(DOOR_H if st == 'closed' else 3.48), state=st)
    A['doors']['West']['note'] = 'Open in the building FBX. Optional closing curtain: Workshop_W86_westdoor_curtain_v01.fbx (pivot top of opening).'
    A['partition_doorways'] = {
        'Middle_to_West': dict(position=U((4.5, 0.5 * sum(PD_Y), 0.0)), width=PD_Y[1] - PD_Y[0], height=PD_H),
        'Middle_to_East': dict(position=U((-4.5, 0.5 * sum(PD_Y), 0.0)), width=PD_Y[1] - PD_Y[0], height=PD_H)}
    A['lights'] = []
    for i, (x, y) in enumerate(LAMPS):
        A['lights'].append(dict(name='Light_Strip_%02d' % (i + 1), position=U((x, y, LAMP_Z - 0.08)), type='area/point down',
                                colour='#FFF3DA', suggested=dict(point_range_m=7, intensity_lm=1800)))
    A['lights'].append(dict(name='Light_Bulkhead_West', position=U((9.4, IY - 0.2, 2.6)), type='point', colour='#FFE2B0',
                            suggested=dict(point_range_m=5, intensity_lm=500)))
    for pid, pdef in props.items():
        if pdef['builder'] == 'wall_light':
            A['lights'].append(dict(name='Light_' + pid, position=U(pdef['light_point']), type='spot down', colour='#FFE2B0',
                                    suggested=dict(spot_range_m=9, spot_angle_deg=100, intensity_lm=900)))
    A['phone'] = dict(position=U(props['WS_P_Phone']['loc']), yaw=uyaw(props['WS_P_Phone']['rot']))
    return A


# ============================================================================ props
def P_bollard(lod):
    mb = MB('bollard')
    n = 10 if lod == 0 else 6
    mb.box((-0.13, -0.13, 0.0), (0.13, 0.13, 0.02), M_DARK, skip=('z-',))
    mb.cyl((0, 0, 0.02), (0, 0, 0.74), 0.1, M_YEL, n=n, caps=(False, False))
    mb.cyl((0, 0, 0.74), (0, 0, 0.82), 0.1, M_DARK, n=n, caps=(False, False))
    mb.cyl((0, 0, 0.82), (0, 0, 1.0), 0.1, M_YEL, n=n, caps=(False, False))
    mb.cyl((0, 0, 1.0), (0, 0, 1.05), 0.1, M_YEL, n=n, r1=0.07, caps=(False, True))
    return mb, [((-0.1, -0.1, 0), (0.1, 0.1, 1.05))]


def tyre(mb, M, lod, mat=M_RUB):
    prof = [(0.20, -0.08), (0.30, -0.105), (0.32, -0.06), (0.32, 0.06), (0.30, 0.105), (0.20, 0.08), (0.20, -0.08)]
    mb.lathe(prof, 10 if lod == 0 else 6, mat, M=M)


def P_tyre_stack(lod, n=4, seed=1):
    mb = MB('tyres')
    r = random.Random(seed)
    for i in range(n):
        M = T(r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), 0.105 + 0.21 * i) @ RZ(r.uniform(0, 36))
        tyre(mb, M, lod)
    return mb, [((-0.32, -0.32, 0), (0.32, 0.32, 0.21 * n))]


def P_tyre_rack(lod):
    mb = MB('tyre_rack')
    Lx, D, H = 2.0, 0.5, 1.58
    for x in (-Lx / 2, Lx / 2 - 0.05):
        for y in (-D / 2, D / 2 - 0.05):
            mb.box((x, y, 0), (x + 0.05, y + 0.05, H), M_RED, skip=('z-',))
    for z in (0.12, 0.85):
        for y in (-0.16, 0.11):
            mb.box((-Lx / 2 + 0.05, y, z), (Lx / 2 - 0.05, y + 0.05, z + 0.04), M_RED, skip=('x-', 'x+'))
        for x in (-Lx / 2 + 0.05, Lx / 2 - 0.1):
            mb.box((x, -D / 2 + 0.05, z + 0.006), (x + 0.05, D / 2 - 0.05, z + 0.034), M_RED, skip=('y-', 'y+'))
    mb.box((-Lx / 2 + 0.05, -0.02, H - 0.05), (Lx / 2 - 0.05, 0.02, H - 0.01), M_RED, skip=('x-', 'x+'))
    for z in (0.12, 0.85):
        for i in range(4):
            x = -0.69 + i * 0.46
            tyre(mb, T(x, 0.0, z + 0.04 + 0.29) @ RY(90) @ RZ(i * 13), lod)
    return mb, [((-Lx / 2, -D / 2, 0), (Lx / 2, D / 2, H))]


def P_drum(lod, mat=M_RED):
    mb = MB('drum')
    prof = [(0, 0), (0.285, 0), (0.285, 0.28), (0.298, 0.29), (0.298, 0.31), (0.285, 0.32), (0.285, 0.56),
            (0.298, 0.57), (0.298, 0.59), (0.285, 0.60), (0.285, 0.88), (0.25, 0.88), (0.25, 0.87), (0, 0.87)]
    if lod:
        prof = [(0, 0), (0.29, 0), (0.29, 0.88), (0, 0.88)]
    mb.lathe(prof, 10 if lod == 0 else 6, mat)
    if lod == 0:
        mb.cyl((0.14, 0.05, 0.87), (0.14, 0.05, 0.895), 0.03, M_DARK, n=6, caps=(False, True))
    return mb, [((-0.29, -0.29, 0), (0.29, 0.29, 0.9))]


def P_crate_wood(lod, w=0.8, d=0.6, h=0.5):
    mb = MB('crate')
    mb.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), M_WOOD, skip=('z-',))
    if lod == 0:
        for z in (0.08, h - 0.14):
            for s in (-1, 1):
                y0, y1 = sorted((s * d / 2, s * (d / 2 + 0.012)))
                mb.box((-w / 2 + 0.06, y0, z), (w / 2 - 0.06, y1, z + 0.08), M_WOOD, skip=('y+' if s < 0 else 'y-',))
        for sx in (-1, 1):
            for sy in (-1, 1):
                xa, xb = sorted((sx * w / 2, sx * (w / 2 - 0.06)))
                ya, yb = sorted((sy * d / 2, sy * (d / 2 + 0.018)))
                mb.box((xa, ya, 0.0), (xb, yb, h), M_WOOD, skip=('z-', 'y+' if sy < 0 else 'y-'))
    return mb, [((-w / 2, -d / 2, 0), (w / 2, d / 2, h))]


def P_crates_yard(lod):
    mb = MB('crates_yard')
    c, _ = P_crate_wood(lod)
    mb.merge(c, RZ(0))
    mb.merge(c, T(0.05, -0.02, 0.5) @ RZ(6))
    c2, _ = P_crate_wood(lod, 0.6, 0.5, 0.45)
    mb.merge(c2, T(0.85, 0.15, 0) @ RZ(-12))
    return mb, [((-0.42, -0.32, 0), (0.42, 0.32, 1.0)), ((0.5, -0.2, 0), (1.2, 0.5, 0.45))]


def P_crate_military(lod):
    mb = MB('crate_mil')
    mb.box((-0.4, -0.25, 0), (0.4, 0.25, 0.36), M_DARK, skip=('z-',))
    mb.box((-0.41, -0.26, 0.36), (0.41, 0.26, 0.42), M_DARK)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.4, sx * 0.43))
        mb.box((x0, -0.08, 0.22), (x1, 0.08, 0.25), M_WORN)
    for x in (-0.25, 0.25):
        mb.box((x - 0.03, -0.27, 0.3), (x + 0.03, -0.25, 0.38), M_WORN, skip=('y+',))
    return mb, [((-0.41, -0.26, 0), (0.41, 0.26, 0.42))]


def P_jerry(mb, M):
    j = MB('j')
    j.box((-0.17, -0.08, 0), (0.17, 0.08, 0.42), M_RED, skip=('z-',))
    for x in (-0.12, -0.04, 0.04):
        j.box((x, -0.015, 0.42), (x + 0.025, 0.015, 0.47), M_RED, skip=('z-',))
    j.box((-0.12, -0.015, 0.47), (0.065, 0.015, 0.49), M_RED)
    j.cyl((0.11, 0, 0.42), (0.13, 0, 0.48), 0.022, M_DARK, n=6)
    mb.merge(j, M)


def P_can(mb, M, mat=M_RED):
    c = MB('c')
    c.cyl((0, 0, 0), (0, 0, 0.27), 0.075, mat, n=8, caps=(False, True))
    c.cyl((0.03, 0, 0.27), (0.05, 0, 0.32), 0.012, M_DARK, n=4)
    mb.merge(c, M)


def P_oil_group(lod):
    mb = MB('oil')
    P_can(mb, T(-0.15, 0.0, 0))
    P_can(mb, T(0.02, 0.06, 0), M_WORN)
    P_can(mb, T(0.0, -0.12, 0) @ RZ(40), M_YEL)
    P_jerry(mb, T(0.3, 0.02, 0) @ RZ(90))
    return mb, []


def P_canisters_yard(lod):
    mb = MB('canisters')
    P_jerry(mb, T(0, 0, 0))
    P_jerry(mb, T(0.02, 0.2, 0) @ RZ(8))
    P_can(mb, T(0.35, 0.05, 0), M_WORN)
    return mb, [((-0.2, -0.12, 0), (0.45, 0.3, 0.5))]


def drawer_fronts(mb, x0, x1, z0, z1, n, y_face, mat=M_RED, handle=M_WORN, sign=-1):
    """Drawer fronts proud of a face at y=y_face (pointing -Y when sign=-1)."""
    h = (z1 - z0) / n
    for i in range(n):
        za, zb = z0 + i * h + 0.006, z0 + (i + 1) * h - 0.006
        ya, yb = sorted((y_face, y_face + sign * 0.012))
        mb.box((x0 + 0.01, ya, za), (x1 - 0.01, yb, zb), mat, skip=('y+' if sign < 0 else 'y-',))
        hy0, hy1 = sorted((y_face + sign * 0.012, y_face + sign * 0.035))
        zc = zb - 0.035 if h > 0.12 else 0.5 * (za + zb)
        mb.box((x0 + 0.25 * (x1 - x0), hy0, zc - 0.008), (x1 - 0.25 * (x1 - x0), hy1, zc + 0.008), handle)


def P_workbench(lod):
    mb = MB('workbench')
    Lx, D, H = 2.0, 0.75, 0.92
    for x in (-Lx / 2 + 0.03, Lx / 2 - 0.08):
        for y in (-D / 2 + 0.03, D / 2 - 0.08):
            mb.box((x, y, 0), (x + 0.05, y + 0.05, H - 0.05), M_WORN, skip=('z-', 'z+'))
    mb.box((-Lx / 2, -D / 2, H - 0.05), (Lx / 2, D / 2, H), M_WOOD)
    mb.box((-Lx / 2 + 0.08, -D / 2 + 0.03, 0.15), (Lx / 2 - 0.08, D / 2 - 0.03, 0.17), M_WORN)
    mb.box((-Lx / 2 + 0.08, -D / 2 + 0.03, H - 0.13), (Lx / 2 - 0.08, -D / 2 + 0.06, H - 0.05), M_WORN, skip=('z+',))
    # drawer unit
    dx0, dx1 = Lx / 2 - 0.62, Lx / 2 - 0.08
    mb.box((dx0, -D / 2 + 0.06, 0.17), (dx1, D / 2 - 0.05, H - 0.13), M_RED, skip=('z-', 'z+'))
    if lod == 0:
        drawer_fronts(mb, dx0, dx1, 0.19, H - 0.15, 4, -D / 2 + 0.06)
        # vice on the left end
        vx = -Lx / 2 + 0.25
        mb.box((vx - 0.08, -D / 2 + 0.02, H), (vx + 0.08, -D / 2 + 0.2, H + 0.05), M_DARK)
        mb.box((vx - 0.09, -D / 2 - 0.02, H + 0.05), (vx + 0.09, -D / 2 + 0.03, H + 0.16), M_DARK)
        mb.box((vx - 0.09, -D / 2 + 0.08, H + 0.05), (vx + 0.09, -D / 2 + 0.14, H + 0.16), M_DARK)
        mb.cyl((vx, -D / 2 - 0.02, H + 0.1), (vx, -D / 2 - 0.12, H + 0.1), 0.015, M_WORN, n=6)
        mb.cyl((vx - 0.12, -D / 2 - 0.12, H + 0.1), (vx + 0.12, -D / 2 - 0.12, H + 0.1), 0.008, M_WORN, n=4)
        # small red toolbox and a part on top
        mb.box((0.0, -0.05, H), (0.42, 0.17, H + 0.18), M_RED)
        mb.box((0.15, 0.02, H + 0.18), (0.27, 0.10, H + 0.2), M_DARK)
        mb.cyl((-0.25, 0.05, H), (-0.25, 0.05, H + 0.04), 0.12, M_WORN, n=10)
    return mb, [((-Lx / 2, -D / 2, 0), (Lx / 2, D / 2, H))]


def P_toolboard(lod):
    mb = MB('toolboard')
    W_, H_ = 1.4, 0.9
    for x in (-0.6, 0.6):
        mb.box((x - 0.03, -0.04, 0.05), (x + 0.03, 0.0, H_ - 0.05), M_DARK, skip=('y+',))
    mb.box((-W_ / 2, -0.062, 0.0), (W_ / 2, -0.04, H_), M_WOOD)
    if lod == 0:
        fr = lambda s, t, w: Vector((s, w, t))
        for i, (x, z, ln) in enumerate(((-0.5, 0.45, 0.32), (-0.38, 0.45, 0.27), (-0.27, 0.45, 0.22))):
            poly = [(px * ln, pz * ln) for px, pz in L.wrench_poly()]
            poly = [(x + pz, z + px) for px, pz in poly]  # vertical wrench
            mb.prism(poly, -0.062, -0.074, M_WORN, fr, caps=(False, True))
        # hammer
        mb.box((0.02, -0.08, 0.2), (0.05, -0.062, 0.605), M_WOOD, skip=('y+',))
        mb.box((-0.04, -0.09, 0.6), (0.11, -0.062, 0.66), M_DARK, skip=('y+',))
        # screwdrivers
        for i, x in enumerate((0.22, 0.30, 0.38)):
            mb.cyl((x, -0.075, 0.68), (x, -0.075, 0.55), 0.016, M_RED if i != 1 else M_YEL, n=6)
            mb.cyl((x, -0.075, 0.55), (x, -0.075, 0.38 - i * 0.03), 0.004, M_WORN, n=4)
        # pliers
        for a, yo in ((-12, -0.071), (12, -0.077)):
            mb.merge(_bar(0.012, 0.24, M_RED), T(0.55, yo, 0.45) @ RY(a))
        mb.box((0.45, -0.08, 0.14), (0.65, -0.062, 0.2), M_DARK, skip=('y+',))
    return mb, []


def _bar(w, h, mat):
    b = MB('bar')
    b.box((-w, -0.006, -h / 2), (w, 0.006, h / 2), mat)
    return b


def P_toolchest(lod):
    mb = MB('toolchest')
    W_, D, H = 0.7, 0.46, 1.0
    for x in (-W_ / 2 + 0.06, W_ / 2 - 0.06):
        for y in (-D / 2 + 0.06, D / 2 - 0.06):
            mb.cyl((x, y - 0.02, 0.045), (x, y + 0.02, 0.045), 0.045, M_RUB, n=8)
            mb.box((x - 0.03, y - 0.03, 0.09), (x + 0.03, y + 0.03, 0.1), M_DARK, skip=('z-',))
    mb.box((-W_ / 2, -D / 2, 0.1), (W_ / 2, D / 2, H - 0.04), M_RED)
    mb.box((-W_ / 2 - 0.01, -D / 2 - 0.01, H - 0.04), (W_ / 2 + 0.01, D / 2 + 0.01, H), M_DARK)
    if lod == 0:
        drawer_fronts(mb, -W_ / 2, W_ / 2, 0.14, H - 0.08, 6, -D / 2)
        mb.tube([(W_ / 2, -0.15, 0.85), (W_ / 2 + 0.06, -0.15, 0.85), (W_ / 2 + 0.06, 0.15, 0.85), (W_ / 2, 0.15, 0.85)], 0.012, M_WORN, n=6)
    return mb, [((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H))]


def P_cabinet_dark(lod):
    mb = MB('cabinet')
    W_, D, H = 0.9, 0.5, 1.85
    mb.box((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H), M_DARK, skip=('z-',))
    for s in (-1, 1):
        xa, xb = sorted((s * 0.005, s * (W_ / 2 - 0.01)))
        mb.box((xa, -D / 2 - 0.012, 0.06), (xb, -D / 2, H - 0.05), M_DARK, skip=('y+',))
        hx = s * 0.05
        mb.box((hx - 0.01, -D / 2 - 0.035, 0.9), (hx + 0.01, -D / 2 - 0.012, 1.1), M_WORN)
    if lod == 0:
        for z in (1.55, 1.6, 1.65):
            for s in (-1, 1):
                xa, xb = sorted((s * 0.1, s * 0.35))
                mb.box((xa, -D / 2 - 0.02, z), (xb, -D / 2 - 0.012, z + 0.015), M_DARK)
    return mb, [((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H))]


def shelf_items(mb, kind, Lx, D, levels, lod, seed):
    r = random.Random(seed)
    for li, z in enumerate(levels):
        if kind == 'parts' and li == 1:
            # engine block
            e = MB('engine')
            e.box((-0.22, -0.17, 0), (0.22, 0.17, 0.26), M_DARK)
            e.box((-0.2, -0.12, 0.26), (0.2, 0.12, 0.33), M_WORN)
            if lod == 0:
                for i in range(4):
                    e.cyl((-0.15 + i * 0.1, 0.0, 0.33), (-0.15 + i * 0.1, 0.0, 0.37), 0.02, M_WORN, n=6)
                e.cyl((-0.22, 0.0, 0.1), (-0.27, 0.0, 0.1), 0.09, M_DARK, n=8)
            mb.merge(e, T(-0.45, 0.0, z) @ RZ(r.uniform(-8, 8)))
            for i in range(2):
                mb.cyl((0.25 + i * 0.33, 0.0, z), (0.25 + i * 0.33, 0.0, z + 0.03), 0.14, M_WORN, n=10)
                mb.cyl((0.25 + i * 0.33, 0.0, z + 0.03), (0.25 + i * 0.33, 0.0, z + 0.07), 0.07, M_WORN, n=8)
        elif kind == 'parts' and li == 2:
            for i in range(3):
                tyre(mb, T(-0.6 + i * 0.6, 0.0, z + 0.105), lod)
        else:
            x = -Lx / 2 + 0.08
            while x < Lx / 2 - 0.3:
                w = r.uniform(0.28, 0.5)
                h = r.uniform(0.18, 0.36)
                d = r.uniform(0.3, D - 0.12)
                if r.random() < 0.8:
                    mb.box((x, -d / 2, z), (x + w, d / 2, z + h), M_CARD)
                else:
                    for k in range(3):
                        P_can(mb, T(x + 0.09 + k * 0.16, -0.05, z))
                x += w + r.uniform(0.04, 0.12)


def P_shelving(lod, kind='boxes', seed=3):
    mb = MB('shelving')
    Lx, D, H = 2.0, 0.6, 2.0
    for x in (-Lx / 2, Lx / 2 - 0.045):
        for y in (-D / 2, D / 2 - 0.045):
            mb.box((x, y, 0), (x + 0.045, y + 0.045, H), M_RED, skip=('z-',))
    levels = [0.12, 0.7, 1.28, 1.86]
    for z in levels:
        mb.box((-Lx / 2 + 0.045, -D / 2 + 0.01, z - 0.025), (Lx / 2 - 0.045, D / 2 - 0.01, z), M_RED)
        mb.box((-Lx / 2 + 0.045, -D / 2, z - 0.09), (Lx / 2 - 0.045, -D / 2 + 0.01, z), M_RED)
    if lod == 0:
        for x in (-Lx / 2 + 0.02, Lx / 2 - 0.025):
            for (za, zb) in ((0.15, 0.68), (0.73, 1.26)):
                p0 = Vector((x, -D / 2 + 0.05, za))
                p1 = Vector((x, D / 2 - 0.05, zb))
                mb.cyl(p0, p1, 0.01, M_RED, n=4)
    shelf_items(mb, kind, Lx, D, levels[:3] if kind == 'parts' else levels, lod, seed)
    return mb, [((-Lx / 2, -D / 2, 0), (Lx / 2, D / 2, H))]


def P_desk(lod):
    mb = MB('desk')
    W_, D, H = 1.6, 0.7, 0.75
    mb.box((-W_ / 2, -D / 2, H - 0.035), (W_ / 2, D / 2, H), M_WORN)
    mb.box((-W_ / 2 + 0.02, -D / 2 + 0.05, 0), (-W_ / 2 + 0.05, D / 2 - 0.03, H - 0.035), M_WORN, skip=('z-', 'z+'))
    mb.box((-W_ / 2 + 0.05, D / 2 - 0.05, 0.3), (W_ / 2 - 0.45, D / 2 - 0.03, H - 0.035), M_WORN, skip=('z+',))
    px0 = W_ / 2 - 0.45
    mb.box((px0, -D / 2 + 0.04, 0.0), (W_ / 2 - 0.02, D / 2 - 0.03, H - 0.035), M_WORN, skip=('z-', 'z+'))
    drawer_fronts(mb, px0, W_ / 2 - 0.02, 0.04, H - 0.06, 3, -D / 2 + 0.04)
    return mb, [((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H))]


def P_office_chair(lod):
    mb = MB('chair')
    for i in range(5):
        a = 2 * math.pi * i / 5
        c, s = math.cos(a), math.sin(a)
        mb.merge(_spoke(), RZ(math.degrees(a)))
        mb.box((0.29 * c - 0.025, 0.29 * s - 0.025, 0.0), (0.29 * c + 0.025, 0.29 * s + 0.025, 0.06), M_RUB, skip=('z-',))
    mb.cyl((0, 0, 0.055), (0, 0, 0.11), 0.065, M_DARK, n=10)
    mb.cyl((0, 0, 0.11), (0, 0, 0.42), 0.025, M_DARK, n=6, caps=(False, True))
    mb.box((-0.24, -0.23, 0.42), (0.24, 0.23, 0.5), M_FAB)
    mb.box((-0.03, 0.2, 0.45), (0.03, 0.26, 0.62), M_DARK)
    mb.box((-0.22, 0.22, 0.6), (0.22, 0.29, 1.05), M_FAB)
    if lod == 0:
        for s in (-1, 1):
            mb.box((s * 0.25 - 0.015, -0.05, 0.5), (s * 0.25 + 0.015, 0.0, 0.66), M_DARK)
            mb.box((s * 0.25 - 0.03, -0.15, 0.66), (s * 0.25 + 0.03, 0.08, 0.69), M_RUB)
    return mb, [((-0.3, -0.3, 0), (0.3, 0.3, 1.05))]


def _spoke():
    b = MB('spoke')
    b.box((0.045, -0.022, 0.06), (0.29, 0.022, 0.1), M_DARK)
    return b


def P_phone(lod):
    mb = MB('phone')
    base = [(-0.1, 0.0), (0.1, 0.0), (0.1, 0.05), (-0.1, 0.075)]
    mb.prism([(y, z) for y, z in base], -0.09, 0.09, M_RUB, lambda s, t, w: Vector((w, -s, t)))
    mb.box((-0.1, -0.035, 0.07), (0.1, 0.035, 0.1), M_RUB)
    mb.box((-0.11, -0.04, 0.09), (-0.07, 0.04, 0.115), M_RUB)
    mb.box((0.07, -0.04, 0.09), (0.11, 0.04, 0.115), M_RUB)
    mb.box((-0.045, -0.09, 0.03), (0.045, -0.02, 0.058), M_DARK, skip=('z-',))
    return mb, []


def P_desk_lamp(lod):
    mb = MB('desklamp')
    mb.cyl((0, 0, 0), (0, 0, 0.025), 0.07, M_DARK, n=8, caps=(False, True))
    mb.cyl((0, 0, 0.025), (0.0, 0.08, 0.3), 0.01, M_DARK, n=4)
    mb.cyl((0.0, 0.08, 0.3), (0.0, -0.12, 0.42), 0.01, M_DARK, n=4)
    shade = MB('shade')
    shade.lathe([(0.0, -0.1), (0.075, -0.1), (0.03, 0.0), (0.0, 0.0)], 8, M_DARK, mats={0: M_EMIT})
    mb.merge(shade, T(0.0, -0.12, 0.42) @ RX(-25))
    return mb, []


def P_mugs(lod):
    mb = MB('mugs')
    for x, y in ((0.0, 0.0), (0.1, 0.22)):
        mb.lathe([(0, 0), (0.04, 0), (0.04, 0.09), (0.034, 0.09), (0.034, 0.01), (0, 0.01)], 8, M_WHITE, M=T(x, y, 0))
        mb.box((x + 0.04, y - 0.006, 0.025), (x + 0.065, y + 0.006, 0.07), M_WHITE)
    mb.box((-0.25, 0.25, 0.0), (0.05, 0.47, 0.004), M_WHITE)  # paper sheet on the desk
    return mb, []


def P_calendar(lod):
    mb = MB('calendar')
    mb.box((-0.21, -0.004, 0.0), (0.21, 0.0, 0.6), M_WHITE, skip=('y+',))
    mb.box((-0.18, -0.008, 0.33), (0.18, -0.004, 0.57), M_DARK, skip=('y+',))
    tri = [(-0.16, 0.35), (-0.05, 0.47), (0.02, 0.4), (0.09, 0.5), (0.16, 0.35)]
    mb.prism(tri, -0.008, -0.013, M_WORN, lambda s, t, w: Vector((s, w, t)), caps=(False, True))
    mb.box((-0.18, -0.008, 0.27), (0.18, -0.005, 0.30), M_RED, skip=('y+',))
    for r_ in range(4):
        for c_ in range(7):
            x = -0.17 + c_ * 0.05
            z = 0.04 + r_ * 0.055
            mb.box((x, -0.006, z), (x + 0.035, -0.004, z + 0.035), M_DARK, skip=('y+',)) if lod == 0 and (r_ * 7 + c_) % 3 == 0 else None
    return mb, []


def P_filing(lod):
    mb = MB('filing')
    W_, D, H = 0.47, 0.6, 1.0
    mb.box((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H), M_DARK, skip=('z-',))
    drawer_fronts(mb, -W_ / 2, W_ / 2, 0.03, H - 0.03, 3, -D / 2, mat=M_DARK)
    mb.box((-0.2, -0.18, H), (0.2, 0.18, H + 0.22), M_CARD)
    return mb, [((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, H))]


def P_waste_bin(lod):
    mb = MB('bin')
    mb.lathe([(0, 0), (0.14, 0), (0.165, 0.34), (0.17, 0.35), (0.16, 0.35), (0.135, 0.02), (0, 0.02)], 10, M_RUB)
    return mb, []


def P_sofa(lod):
    mb = MB('sofa')
    W_, D = 1.9, 0.85
    for x in (-W_ / 2 + 0.08, W_ / 2 - 0.13):
        for y in (-D / 2 + 0.08, D / 2 - 0.13):
            mb.box((x, y, 0), (x + 0.05, y + 0.05, 0.1), M_DARK, skip=('z-', 'z+'))
    mb.box((-W_ / 2, -D / 2, 0.1), (W_ / 2, D / 2, 0.3), M_FAB)
    mb.box((-W_ / 2, D / 2 - 0.2, 0.3), (W_ / 2, D / 2, 0.82), M_FAB)
    for s in (-1, 1):
        xa, xb = sorted((s * W_ / 2, s * (W_ / 2 - 0.16)))
        mb.box((xa, -D / 2, 0.3), (xb, D / 2 - 0.2, 0.62), M_FAB)
    for x0 in (-W_ / 2 + 0.17, 0.005):
        mb.box((x0, -D / 2 + 0.02, 0.3), (x0 + 0.775, D / 2 - 0.22, 0.45), M_FAB)
        if lod == 0:
            mb.box((x0 + 0.02, D / 2 - 0.36, 0.45), (x0 + 0.755, D / 2 - 0.2, 0.78), M_FAB)
    return mb, [((-W_ / 2, -D / 2, 0), (W_ / 2, D / 2, 0.82))]


def P_jack(lod):
    mb = MB('jack')
    for s in (-1, 1):
        xa, xb = sorted((s * 0.11, s * 0.14))
        mb.box((xa, -0.35, 0.05), (xb, 0.35, 0.17), M_RED)
        mb.cyl((s * 0.16, -0.28, 0.05), (s * 0.20, -0.28, 0.05), 0.05, M_DARK, n=8)
    mb.box((-0.11, 0.2, 0.06), (0.11, 0.35, 0.16), M_RED)
    for s in (-1, 1):
        mb.cyl((s * 0.08 - 0.015, 0.3, 0.03), (s * 0.08 + 0.015, 0.3, 0.03), 0.03, M_RUB, n=6)
    arm = MB('arm')
    arm.box((-0.07, -0.02, -0.02), (0.07, 0.45, 0.04), M_RED)
    mb.merge(arm, T(0, -0.36, 0.13) @ RX(-14))
    mb.cyl((0, -0.38, 0.17), (0, -0.38, 0.21), 0.06, M_DARK, n=8)
    mb.cyl((0, 0.2, 0.12), (0, 0.05, 0.28), 0.035, M_DARK, n=8)
    mb.cyl((0, 0.33, 0.12), (0, 0.85, 0.85), 0.016, M_RED, n=6)
    mb.cyl((0, 0.85, 0.85), (0, 0.93, 0.96), 0.02, M_RUB, n=6)
    return mb, [((-0.2, -0.45, 0), (0.2, 0.4, 0.3))]


def P_compressor(lod):
    mb = MB('compressor')
    n = 12 if lod == 0 else 7
    prof = [(0, -0.45), (0.12, -0.44), (0.18, -0.41), (0.2, -0.36), (0.2, 0.36), (0.18, 0.41), (0.12, 0.44), (0, 0.45)]
    mb.lathe(prof, n, M_RED, M=T(0, 0, 0.32) @ RY(90))
    for s in (-1, 1):
        mb.cyl((0.3, s * 0.2, 0.12), (0.3, s * 0.25, 0.12), 0.12, M_RUB, n=n)
    mb.box((-0.38, -0.05, 0.0), (-0.3, 0.05, 0.16), M_DARK, skip=('z-',))
    mb.box((-0.3, -0.12, 0.5), (0.05, 0.12, 0.7), M_DARK)
    mb.cyl((0.05, 0, 0.6), (0.25, 0, 0.6), 0.09, M_DARK, n=n)
    if lod == 0:
        for i in range(4):
            z = 0.72 + i * 0.03
            mb.box((-0.25, -0.1, z), (-0.05, 0.1, z + 0.015), M_WORN)
        mb.cyl((0.28, -0.12, 0.62), (0.28, -0.14, 0.62), 0.05, M_WHITE, n=10)
        mb.tube([(0.4, -0.16, 0.3), (0.4, -0.16, 0.85), (0.45, -0.16, 0.9), (0.45, 0.16, 0.9), (0.4, 0.16, 0.85), (0.4, 0.16, 0.3)], 0.014, M_WORN, n=6, caps=(True, True))
        circ = [(0.17 + 0.015 * math.cos(2 * math.pi * k / 6), 0.015 * math.sin(2 * math.pi * k / 6)) for k in range(7)]
        mb.lathe(circ, 12, M_YEL, M=T(0.47, 0.0, 0.62) @ RY(90))
    return mb, [((-0.45, -0.25, 0), (0.5, 0.25, 0.95))]


def P_waste_container(lod):
    mb = MB('container')
    c = [None] * 8
    for xi, sx in enumerate((-1, 1)):
        for yi, sy in enumerate((-1, 1)):
            c[xi | (yi << 1)] = Vector((sx * 0.55, sy * 0.45, 0.12))
            c[xi | (yi << 1) | 4] = Vector((sx * 0.62, sy * 0.5, 1.1))
    mb.hexa(c, M_WORN)
    mb.box((-0.65, -0.53, 1.1), (0.65, 0.53, 1.14), M_WORN)
    for s in (-1, 1):
        xa, xb = sorted((s * 0.005, s * 0.64))
        lid = [Vector(p) for p in ((xa, -0.54, 1.14), (xb, -0.54, 1.14), (xa, 0.54, 1.2), (xb, 0.54, 1.2))]
        mb.hexa([lid[0], lid[1], lid[2], lid[3], lid[0] + Vector((0, 0, 0.03)), lid[1] + Vector((0, 0, 0.03)),
                 lid[2] + Vector((0, 0, 0.03)), lid[3] + Vector((0, 0, 0.03))], M_DARK)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cyl((sx * 0.45 - 0.03, sy * 0.36, 0.08), (sx * 0.45 + 0.03, sy * 0.36, 0.08), 0.08, M_RUB, n=8)
    mb.tube([(-0.5, -0.5, 0.95), (-0.5, -0.6, 0.95), (0.5, -0.6, 0.95), (0.5, -0.5, 0.95)], 0.016, M_WORN, n=6)
    return mb, [((-0.62, -0.5, 0), (0.62, 0.5, 1.2))]


def P_outdoor_bench(lod):
    mb = MB('outbench')
    Lx, D, H = 1.8, 0.7, 0.9
    for x in (-Lx / 2 + 0.05, Lx / 2 - 0.1):
        for y in (-D / 2 + 0.05, D / 2 - 0.1):
            mb.box((x, y, 0), (x + 0.05, y + 0.05, H - 0.06), M_RED, skip=('z-', 'z+'))
    mb.box((-Lx / 2, -D / 2, H - 0.06), (Lx / 2, D / 2, H), M_WOOD)
    mb.box((-Lx / 2 + 0.1, -D / 2 + 0.05, 0.2), (Lx / 2 - 0.1, D / 2 - 0.05, 0.23), M_WOOD)
    if lod == 0:
        vx = Lx / 2 - 0.2
        mb.box((vx - 0.08, -D / 2 + 0.02, H), (vx + 0.08, -D / 2 + 0.2, H + 0.05), M_DARK)
        mb.box((vx - 0.09, -D / 2 - 0.02, H + 0.05), (vx + 0.09, -D / 2 + 0.03, H + 0.16), M_DARK)
        mb.box((vx - 0.09, -D / 2 + 0.08, H + 0.05), (vx + 0.09, -D / 2 + 0.14, H + 0.16), M_DARK)
        mb.lathe([(0, 0), (0.13, 0), (0.15, 0.28), (0.14, 0.28), (0.12, 0.02), (0, 0.02)], 10, M_WORN, M=T(-0.4, 0.0, 0.23))
        mb.box((0.1, -0.1, 0.23), (0.55, 0.12, 0.43), M_RED)
        mb.box((-0.5, -0.15, H), (-0.1, 0.1, H + 0.12), M_CARD)
    return mb, [((-Lx / 2, -D / 2, 0), (Lx / 2, D / 2, H))]


def P_sign(lod):
    mb = MB('sign')
    W_, H_ = 3.0, 0.8
    for x in (-1.2, 1.2):
        for z in (0.15, 0.65):
            mb.cyl((x, 0.0, z), (x, -0.06, z), 0.025, M_DARK, n=6, caps=(False, False))
    mb.box((-W_ / 2, -0.10, 0.0), (W_ / 2, -0.06, H_), M_WHITE, mats={'x-': M_DARK, 'x+': M_DARK, 'z-': M_DARK, 'z+': M_DARK})
    fr = lambda s, t, w: Vector((s, w, t))
    for x0, x1, z0, z1 in ((-W_ / 2, W_ / 2, 0.0, 0.05), (-W_ / 2, W_ / 2, H_ - 0.05, H_), (-W_ / 2, -W_ / 2 + 0.05, 0.05, H_ - 0.05), (W_ / 2 - 0.05, W_ / 2, 0.05, H_ - 0.05)):
        mb.box((x0, -0.12, z0), (x1, -0.10, z1), M_DARK, skip=('y+',))
    poly = [(px * 1.7, 0.4 + pz * 1.7) for px, pz in L.wrench_poly()]
    poly = [(x * math.cos(math.radians(-12)) - (z - 0.4) * math.sin(math.radians(-12)), 0.4 + x * math.sin(math.radians(-12)) + (z - 0.4) * math.cos(math.radians(-12))) for x, z in poly]
    mb.prism(poly, -0.10, -0.125, M_DARK, fr, caps=(False, True))
    for xc in (-1.15, 1.15):
        hexp = [(xc + 0.13 * math.cos(math.pi / 6 + k * math.pi / 3), 0.4 + 0.13 * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
        mb.prism(hexp, -0.10, -0.12, M_RED, fr, caps=(False, True))
        mb.cyl((xc, -0.12, 0.4), (xc, -0.128, 0.4), 0.055, M_WHITE, n=8, caps=(False, True))
    return mb, []


def P_wall_light(lod):
    mb = MB('walllight')
    mb.box((-0.06, -0.03, -0.09), (0.06, 0.0, 0.09), M_DARK, skip=('y+',))
    pts = [(0, -0.03, 0.0), (0, -0.2, 0.05), (0, -0.36, 0.0), (0, -0.4, -0.08)]
    mb.tube(pts, 0.014, M_DARK, n=6, caps=(False, False))
    shade = MB('shade')
    shade.lathe([(0.0, -0.1), (0.14, -0.1), (0.03, 0.0), (0.0, 0.0)], 10, M_DARK, mats={0: M_EMIT})
    mb.merge(shade, T(0, -0.4, -0.08))
    return mb, []


def P_chair_plain(lod):
    mb = MB('chair_plain')
    for x in (-0.2, 0.17):
        for y in (-0.2, 0.17):
            mb.box((x, y, 0), (x + 0.03, y + 0.03, 0.45), M_DARK, skip=('z-',))
    mb.box((-0.23, -0.23, 0.45), (0.23, 0.23, 0.49), M_RUB)
    for x in (-0.2, 0.17):
        mb.box((x, 0.17, 0.49), (x + 0.03, 0.2, 0.86), M_DARK)
    mb.box((-0.23, 0.165, 0.62), (0.23, 0.225, 0.88), M_RUB)
    return mb, [((-0.23, -0.23, 0), (0.23, 0.23, 0.88))]


PROP_BUILDERS = {
    'bollard': P_bollard, 'tyre_stack4': lambda l: P_tyre_stack(l, 4, 1), 'tyre_stack3': lambda l: P_tyre_stack(l, 3, 7),
    'tyre_rack': P_tyre_rack, 'drum_red': lambda l: P_drum(l, M_RED), 'drum_grey': lambda l: P_drum(l, M_WORN),
    'crates_yard': P_crates_yard, 'crate_military': P_crate_military, 'canisters': P_canisters_yard, 'oil_group': P_oil_group,
    'workbench': P_workbench, 'toolboard': P_toolboard, 'toolchest': P_toolchest, 'cabinet_dark': P_cabinet_dark,
    'shelving_parts': lambda l: P_shelving(l, 'parts', 3), 'shelving_boxes': lambda l: P_shelving(l, 'boxes', 5),
    'shelving_boxes_b': lambda l: P_shelving(l, 'boxes', 11),
    'desk': P_desk, 'office_chair': P_office_chair, 'phone': P_phone, 'desk_lamp': P_desk_lamp, 'mugs': P_mugs,
    'calendar': P_calendar, 'filing': P_filing, 'waste_bin': P_waste_bin, 'sofa': P_sofa, 'jack': P_jack,
    'compressor': P_compressor, 'waste_container': P_waste_container, 'outdoor_bench': P_outdoor_bench, 'sign': P_sign,
    'wall_light': P_wall_light, 'chair_plain': P_chair_plain,
}

# id: (builder, location (Blender building space), rotZ deg, area, collider)
PROP_LAYOUT = [
    # middle bay - east partition side
    ('WS_P_Shelving_Parts', 'shelving_parts', (-4.07, -4.3, 0.0), 90, 'middle_bay', True),
    ('WS_P_ToolChest_A', 'toolchest', (-4.1, -2.6, 0.0), 90, 'middle_bay', True),
    ('WS_P_Workbench_A', 'workbench', (-4.0, -0.8, 0.0), 90, 'middle_bay', True),
    ('WS_P_ToolBoard_A', 'toolboard', (-4.40, -0.8, 1.25), 90, 'middle_bay', False),
    ('WS_P_Shelving_Boxes_A', 'shelving_boxes', (-4.07, 2.9, 0.0), 90, 'middle_bay', True),
    ('WS_P_TyreStack_Corner', 'tyre_stack4', (-3.95, 5.3, 0.0), 0, 'middle_bay', True),
    ('WS_P_Compressor', 'compressor', (-2.75, 5.42, 0.0), 0, 'middle_bay', True),
    ('WS_P_Cabinet_Dark', 'cabinet_dark', (-1.4, 5.47, 0.0), 0, 'middle_bay', True),
    ('WS_P_ToolChest_B', 'toolchest', (0.55, 5.49, 0.0), 0, 'middle_bay', True),
    ('WS_P_Jerry_Back', 'oil_group', (1.25, 5.45, 0.0), 0, 'middle_bay', False),
    ('WS_P_Sofa', 'sofa', (3.2, 5.3, 0.0), 0, 'middle_bay', True),
    ('WS_P_Filing', 'filing', (4.05, 4.55, 0.0), -90, 'middle_bay', True),
    ('WS_P_Desk', 'desk', (4.03, 3.35, 0.0), -90, 'middle_bay', True),
    ('WS_P_OfficeChair', 'office_chair', (3.35, 3.35, 0.0), 90, 'middle_bay', False),
    ('WS_P_Phone', 'phone', (4.12, 3.85, 0.75), -90, 'middle_bay', False),
    ('WS_P_DeskLamp', 'desk_lamp', (4.2, 2.8, 0.75), -90, 'middle_bay', False),
    ('WS_P_Mugs', 'mugs', (3.9, 3.05, 0.75), -90, 'middle_bay', False),
    ('WS_P_ToolBoard_B', 'toolboard', (4.40, 3.0, 1.12), -90, 'middle_bay', False),
    ('WS_P_Calendar', 'calendar', (4.40, 4.1, 1.95), -90, 'middle_bay', False),
    ('WS_P_WasteBin', 'waste_bin', (4.05, 2.3, 0.0), 0, 'middle_bay', False),
    ('WS_P_TyreStack_Front', 'tyre_stack4', (3.9, -4.9, 0.0), 20, 'middle_bay', True),
    ('WS_P_OilCans', 'oil_group', (3.95, -3.95, 0.0), -90, 'middle_bay', False),
    ('WS_P_TrolleyJack', 'jack', (-2.9, -4.6, 0.0), 35, 'middle_bay', False),
    # east bay (storage, closed door)
    ('WS_P_TyreRack_Indoor', 'tyre_rack', (-8.85, 5.45, 0.0), 0, 'east_bay', True),
    ('WS_P_Shelving_Boxes_B', 'shelving_boxes_b', (-11.42, 1.35, 0.0), 90, 'east_bay', True),
    ('WS_P_Drum_East_1', 'drum_grey', (-11.15, 4.95, 0.0), 0, 'east_bay', True),
    ('WS_P_Drum_East_2', 'drum_red', (-10.5, 5.1, 0.0), 40, 'east_bay', True),
    ('WS_P_Workbench_B', 'workbench', (-5.0, 3.6, 0.0), -90, 'east_bay', True),
    ('WS_P_Crates_East', 'crates_yard', (-11.05, -4.9, 0.0), 90, 'east_bay', True),
    # west bay (hand-in; front 6 m kept clear)
    ('WS_P_Chair_West', 'chair_plain', (8.6, 5.33, 0.0), 0, 'west_bay', False),
    ('WS_P_Crate_Military', 'crate_military', (11.2, 5.2, 0.0), 8, 'west_bay', True),
    ('WS_P_Shelving_West', 'shelving_boxes', (11.42, 2.25, 0.0), -90, 'west_bay', True),
    ('WS_P_TyreStack_West', 'tyre_stack3', (11.15, -4.95, 0.0), 0, 'west_bay', True),
    # yard - east flank
    ('WS_P_TyreRack_Yard', 'tyre_rack', (-14.0, -8.2, 0.0), 90, 'yard', True),
    ('WS_P_TyreStack_Yard_A', 'tyre_stack4', (-12.95, -6.75, 0.0), 10, 'yard', True),
    ('WS_P_TyreStack_Yard_B', 'tyre_stack3', (-13.0, -10.1, 0.0), 0, 'yard', True),
    ('WS_P_Crates_Yard', 'crates_yard', (-14.55, -11.1, 0.0), 15, 'yard', True),
    # yard - west flank
    ('WS_P_Drum_Yard_Red', 'drum_red', (12.85, -6.62, 0.0), 0, 'yard', True),
    ('WS_P_Drum_Yard_Grey_1', 'drum_grey', (13.5, -6.65, 0.0), 30, 'yard', True),
    ('WS_P_Drum_Yard_Grey_2', 'drum_grey', (13.15, -7.25, 0.0), 75, 'yard', True),
    ('WS_P_Canisters_Yard', 'canisters', (12.65, -7.85, 0.0), 90, 'yard', False),
    ('WS_P_OutdoorBench', 'outdoor_bench', (14.85, -8.0, 0.0), -90, 'yard', True),
    ('WS_P_WasteContainer', 'waste_container', (14.6, -10.6, 0.0), -90, 'yard', True),
    # facade
    ('WS_P_Sign', 'sign', (0.0, -HY + 0.015, 4.28), 0, 'facade', False),
    ('WS_P_WallLight_East', 'wall_light', (-8.175, -HY + 0.015, 4.55), 0, 'facade', False),
    ('WS_P_WallLight_West', 'wall_light', (8.175, -HY + 0.015, 4.55), 0, 'facade', False),
    ('WS_P_WallLight_SideW', 'wall_light', (HX - 0.015, -4.5, 3.3), 90, 'facade', False),
    ('WS_P_WallLight_SideE', 'wall_light', (-HX + 0.015, -4.5, 3.3), -90, 'facade', False),
]
for i, x in enumerate((-10.4, -5.95, -2.45, 2.45, 5.65, 10.7)):
    PROP_LAYOUT.append(('WS_P_Bollard_%02d' % (i + 1), 'bollard', (x, -6.55, 0.0), 0, 'facade', True))


def build_apron():
    mb = MB('Workshop_W86_apron')
    x0, x1, y0, y1 = -16.0, 16.0, -15.0, -HY - 0.02
    b = 0.4
    top = [(x0 + b, y0 + b, 0.0), (x1 - b, y0 + b, 0.0), (x1 - b, y1, 0.0), (x0 + b, y1, 0.0)]
    mb.face(top, M_APRON, want=(0, 0, 1))
    e = -0.05
    mb.face([(x0, y0, e), (x1, y0, e), (x1 - b, y0 + b, 0.0), (x0 + b, y0 + b, 0.0)], M_APRON, want=(0, -0.1, 1))
    mb.face([(x1, y0, e), (x1, y1, e), (x1 - b, y1, 0.0), (x1 - b, y0 + b, 0.0)], M_APRON, want=(0.1, 0, 1))
    mb.face([(x0, y1, e), (x0, y0, e), (x0 + b, y0 + b, 0.0), (x0 + b, y1, 0.0)], M_APRON, want=(-0.1, 0, 1))
    z = -0.6
    mb.face([(x0, y0, z), (x1, y0, z), (x1, y0, e), (x0, y0, e)], M_APRON, want=(0, -1, 0))
    mb.face([(x1, y0, z), (x1, y1, z), (x1, y1, e), (x1, y0, e)], M_APRON, want=(1, 0, 0))
    mb.face([(x0, y1, z), (x0, y0, z), (x0, y0, e), (x0, y1, e)], M_APRON, want=(-1, 0, 0))
    hull = [(x, y, zz) for x in (x0, x1) for y in (y0, y1) for zz in (z, e)] + [(x, y, 0.0) for x in (x0 + b, x1 - b) for y in (y0 + b, y1)]
    return mb, hull, dict(x=(x0, x1), y=(y0, y1))


# ============================================================================ Blender objects + export
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
    return ob


def export_fbx(path, roots):
    bpy.ops.object.select_all(action='DESELECT')
    objs = []
    for r in roots:
        objs.append(r)
        objs.extend(r.children_recursive)
    for o in objs:
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
    if os.path.exists(path) and not FORCE:
        raise SystemExit('refusing to overwrite existing revision: ' + path)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    outs = {k: os.path.join(OUT, 'Workshop_W86_%s_%s.%s' % (k, REV, ext)) for k, ext in
            (('building', 'fbx'), ('props', 'fbx'), ('apron', 'fbx'), ('westdoor_curtain', 'fbx'), ('anchors', 'json'),
             ('materials', 'json'), ('report', 'json'))}
    outs['blend'] = os.path.join(OUT, 'Workshop_W86_%s.blend' % REV)
    for p in outs.values():
        guard(p)
    lib = make_materials()
    cb = bpy.data.collections.new('WS_Building')
    cp = bpy.data.collections.new('WS_Props')
    ca = bpy.data.collections.new('WS_Apron')
    cd = bpy.data.collections.new('WS_WestDoorCurtain')
    for c in (cb, cp, ca, cd):
        sc.collection.children.link(c)
    report = {'revision': REV}

    # ---------------- building
    root = link_new(cb, 'Workshop_W86_building')
    tris = {}
    for lod in (0, 1):
        for fn in (build_shell, build_interior):
            if lod == 1:
                UCX_BACKUP = list(UCX)
            mb = fn(lod)
            if lod == 1:
                UCX[:] = UCX_BACKUP
            ob = mb.build(lib, cb)
            ob.parent = root
            tris[ob.name] = tri_count(ob)
    building_colliders()
    for i, pts in enumerate(UCX):
        hull_object('UCX_WS_Building_%02d' % (i + 1), pts, cb, root)
    report['building_tris'] = tris
    report['building_lod0_tris'] = tris['WS_Building_Shell_LOD0'] + tris['WS_Building_Interior_LOD0']
    report['building_lod1_tris'] = tris['WS_Building_Shell_LOD1'] + tris['WS_Building_Interior_LOD1']
    report['building_ucx_count'] = len(UCX)

    # ---------------- props
    prop_holders = []
    cache = {}
    props = {}
    ptris = {}
    total = 0
    for pid, key, loc, rot, area, coll_on in PROP_LAYOUT:
        if key not in cache:
            mb0, ucx = PROP_BUILDERS[key](0)
            t0 = mb0.tris()
            mb1 = PROP_BUILDERS[key](1)[0] if t0 > 500 else None
            me0 = mb0.build(lib, cp, name='WS_PM_%s_LOD0' % key).data
            me1 = mb1.build(lib, cp, name='WS_PM_%s_LOD1' % key).data if mb1 else None
            for nm in ('WS_PM_%s_LOD0' % key, 'WS_PM_%s_LOD1' % key):
                if nm in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects[nm])
            cache[key] = (me0, me1, ucx, t0, mb1.tris() if mb1 else None)
        me0, me1, ucx, t0, t1 = cache[key][:5]
        if len(cache[key]) > 5:
            me0 = me0.copy()
            me1 = me1.copy() if me1 else None
        cache[key] = (cache[key][0], cache[key][1], ucx, t0, t1, True)
        me0.name = 'WS_PM_' + pid[5:] + ('_LOD0' if me1 else '')
        if me1:
            me1.name = 'WS_PM_' + pid[5:] + '_LOD1'
        # facade-kit structure: top-level empty <pid> at the prop's base point + yaw, identity children
        # <pid>_Mesh or <pid>_LOD0/_LOD1 and UCX_<pid>_NN. No common props root: with bake_space_transform
        # (project convention) the FBX exporter writes wrong local transforms for nodes two levels below a
        # top-level node (verified on the raw FBX and with a minimal test), so the hierarchy is kept 2 deep.
        holder = link_new(cp, pid)
        holder.location = loc
        holder.rotation_euler = (0, 0, math.radians(rot))
        holder.empty_display_size = 0.3
        prop_holders.append(holder)
        parts = [('%s_Mesh' % pid, me0)] if me1 is None else [('%s_LOD0' % pid, me0), ('%s_LOD1' % pid, me1)]
        for nm, me in parts:
            o = link_new(cp, nm, me)
            o.parent = holder
        if coll_on:
            for j, (mn, mx) in enumerate(ucx):
                pts = [(x, y, z) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
                u = hull_object('UCX_%s_%02d' % (pid, j + 1), pts, cp, holder)
        ptris[pid] = dict(builder=key, lod0=t0, lod1=t1, area=area, collider=bool(coll_on and ucx))
        total += t0
        props[pid] = dict(builder=key, loc=loc, rot=rot, area=area)
        if key == 'wall_light':
            lp = Matrix.Translation(loc) @ RZ(rot) @ Vector((0, -0.4, -0.18))
            props[pid]['light_point'] = tuple(lp)
    report['props_tris'] = ptris
    report['props_total_lod0_tris'] = total

    # ---------------- apron
    amb, hull, aext = build_apron()
    aroot = link_new(ca, 'Workshop_W86_apron')
    aob = amb.build(lib, ca, name='WS_Apron')
    aob.parent = aroot
    hull_object('UCX_WS_Apron_01', hull, ca, aroot)
    report['apron_tris'] = tri_count(aob)

    # ---------------- west door curtain (separate, pivot = top centre of the opening, at the curtain plane)
    x0, x1 = door_x('West')
    W = W_OUT['Front']
    cmb = MB('WS_DoorWest_Curtain')
    curtain(cmb, W, x0, x1, 0.0, 0)
    pivot = Vector((0.5 * (x0 + x1), -HY + 0.12, DOOR_H))
    for i in range(len(cmb.P)):
        cmb.P[i] = cmb.P[i] - pivot
    droot = link_new(cd, 'Workshop_W86_westdoor_curtain')
    dob = cmb.build(lib, cd)
    dob.parent = droot
    dob.location = pivot
    ucd = hull_object('UCX_WS_DoorWest_Curtain_01', [(x - pivot.x, y - pivot.y, z - pivot.z) for x in (x0 + 0.03, x1 - 0.03)
                                                   for y in (-HY + 0.09, -HY + 0.16) for z in (0.0, DOOR_H)], cd, droot)
    ucd.location = pivot
    report['westdoor_curtain_tris'] = tri_count(dob)

    # ---------------- anchors (JSON + empties in the building FBX)
    A = collect_anchors(props)
    def emp(name, p, yaw_b=0.0):
        e = link_new(cb, name)
        e.parent = root
        e.location = p
        e.rotation_euler = (0, 0, math.radians(yaw_b))
        e.empty_display_size = 0.4
    emp('ANCHOR_RepairZone', (0.0, -2.55, 0.0))
    emp('ANCHOR_VanPark', (VAN['centre'][0], VAN['centre'][1], 0.0), 180)
    emp('ANCHOR_Pit', (0.0, 0.5 * (PIT[2] + PIT[3]), 0.0))
    emp('ANCHOR_MechanicStand', (2.85, 2.2, 0.0), 0)
    emp('ANCHOR_HandInZone', (0.5 * (6.4 + 9.95), -2.8, 0.0))
    emp('ANCHOR_Phone', props['WS_P_Phone']['loc'], props['WS_P_Phone']['rot'])
    for n, c, w, st in DOORS:
        emp('ANCHOR_Door_' + n, (c, -HY, 0.0))
    for i, (x, y) in enumerate(LAMPS):
        emp('ANCHOR_Light_%02d' % (i + 1), (x, y, LAMP_Z - 0.08))
    anchors = dict(
        revision=REV, units='metres',
        coordinate_system='Unity local space of the building root: +Y up, +Z = front (door side), pivot = floor level at the footprint centre. '
                          'Converted from Blender (x, y, z) as (-x, z, -y). The same points exist as ANCHOR_* empties in Workshop_W86_building_v01.fbx; '
                          'if the importer axes differ, trust the empties.',
        yaw='degrees about Unity +Y, 0 = facing +Z (out of the doors)',
        footprint=dict(size=Usize(24.0, 12.0, 5.3), floor_y=0.0, foundation_bottom_y=-0.8,
                       note='Foundation band is finished concrete down to -0.8 m: the floor may sit 0.3-0.6 m above lower terrain on a slope. Terrain must be below y=0 inside the footprint.'),
        bays=dict(East=dict(x_range_unity=sorted([-(-IX), -(-4.6)]), state='closed, storage'),
                  Middle=dict(x_range_unity=[-4.4, 4.4], state='open, repair bay with pit'),
                  West=dict(x_range_unity=sorted([-IX, -4.6]), state='open (curtain optional), M06 hand-in')),
        van=dict(length=VAN['length'], width=VAN['width'], height=VAN['height'],
                 middle_door_clear=dict(width=3.8, height=3.48), bollard_gap_middle=4.7),
        apron=dict(file='Workshop_W86_apron_v01.fbx', position=[0, 0, 0],
                   extent_unity=dict(x=sorted([-aext['x'][0], -aext['x'][1]]), z=sorted([-aext['y'][0], -aext['y'][1]])),
                   top_y=0.0, edge_bevel=0.4, skirt_bottom_y=-0.6,
                   note='Same root transform as the building. Top flush with the floor; 0.4 m bevel to -0.05 then a skirt to -0.6 for sinking into terrain.'),
        props=dict(file='Workshop_W86_props_v01.fbx',
                   note='Place the imported props model at the building root transform. Each prop is a top-level node WS_P_* at its base point and yaw '
                        '(pivot = base centre on the floor/apron, or the wall plane for wall-mounted items) with children *_Mesh or *_LOD0/*_LOD1 and UCX_* (large props only).',
                   items={pid: dict(position=U(p['loc']), yaw=uyaw(p['rot']), builder=p['builder'], area=p['area']) for pid, p in props.items()}),
        **A)
    with open(outs['anchors'], 'w', encoding='utf-8') as f:
        json.dump(anchors, f, indent=1)
    mats = {}
    for name, m in MATS.items():
        tex = m['tex']
        if tex and tex.startswith('NEW:'):
            tex_path = 'ArtSource/Buildings/Workshop_W86/' + tex[4:]
            tex_rel = None
        else:
            tex_path = ('Assets/OnlyVolunteers/Art/' + tex) if tex else None
            tex_rel = tex
        mats[name] = dict(albedo=tex_path, albedo_from_art_root=tex_rel,
                          normal=('Assets/OnlyVolunteers/Art/' + m['nrm']) if m.get('nrm') else None,
                          tile_m=m['tile'], unity_tiling=round(1.0 / m['tile'], 5), unity_offset=[0, 0], tint=m['tint'],
                          smoothness=m['smooth'], metallic=m['metal'], emission=m.get('emission'), alpha=m.get('alpha'),
                          texture_sheet_row=m['sheet'], note=m['note'])
    with open(outs['materials'], 'w', encoding='utf-8') as f:
        json.dump(dict(revision=REV, shader='URP/Lit', uv='UV0 in metres (1 UV = 1 m); set material tiling = 1 / tile_m',
                       sheet='Working/Reviews/Workshop_2026-10-28/TEXTURE_SHEET_A_v01.md', materials=mats), f, indent=1)

    # ---------------- export
    export_fbx(outs['building'], [root])
    export_fbx(outs['props'], prop_holders)
    export_fbx(outs['apron'], [aroot])
    export_fbx(outs['westdoor_curtain'], [droot])
    with open(outs['report'], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    print('REPORT', json.dumps({k: v for k, v in report.items() if k != 'props_tris'}))
    bpy.ops.wm.save_as_mainfile(filepath=outs['blend'])
    return outs


if __name__ == '__main__':
    main()
