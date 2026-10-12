"""G12-US: deterministic American Downtown facade/street kit. Blender 5.2, Z up, metres, front -Y.

Companion of ../BUILDING_DETAILS (G12, post-Soviet Rough District). Reuses its Mesh helpers and
STYLE_KIT_v2 geometry/palette READ ONLY; slot colours come from StyleKit_v3 candidate_v07/grade_v07.json.
Run blender -b --factory-startup --python-exit-code 1 --python <this> -- --revision 1
(or `python -I <this> -- --revision 1` with the PyPI bpy 5.2 module).
Existing deliverables are never replaced. --check-only writes nothing.
--preview-existing adds only missing renders; --audit-existing adds a numbered audit.
"""
import argparse
import colorsys
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
G12_DIR = HERE.parent / 'BUILDING_DETAILS'
LIB = HERE.parents[1] / 'STYLE_KIT_v2' / '_lib'
GRADE = HERE.parents[2] / 'Textures' / 'StyleKit_v3' / 'candidate_v07' / 'grade_v07.json'
sys.path.insert(0, str(G12_DIR))
import build_building_details as g12          # read-only reuse of G12 Mesh/profile helpers
sk = g12.sk
import bpy
from mathutils import Vector

FAMILY = 'SK3-BLDDETAILS-US-001'
# First eight slots are exactly G12's ordered roles, so the Rough District remap stays valid.
# Three US slots are appended: canvas (awning cloth), accent (per-instance paint), emissive (neon/lamps).
ROLES = g12.ROLES + ('canvas', 'accent', 'emissive')
# Role -> StyleKit_v3 texture category (Assets/OnlyVolunteers/Art/StyleKit_v3, materials_v3_v07.json).
CATEGORY = {
    'plaster': '3b_plaster_stucco',
    'brick': '3a_brick',
    'concrete': '3c_concrete_panels',
    'metal_painted': '6a_painted_metal_panels',
    'metal_dark': '6b_lightly_weathered_metal',
    'wood': '5a_wood_planks_fences',
    'glass': None,
    'roof': '4d_flat_bitumen_roof',
    'canvas': None,
    'accent': '6a_painted_metal_panels',
    'emissive': None,
}
# Roles without their own v07 mean use a Look_Palette_v2 swatch muted by the v07 initial grade
# (S x 0.75, V x 0.85, grade_v07.json recipe notes). metal_dark is the 6b mean at value 0.32 (cast iron).
FALLBACK = {'glass': 'glass.dark', 'canvas': 'red.dark', 'accent': 'cobalt.dark', 'emissive': 'lamp_glow'}
DARK_IRON_VALUE = 0.32
WALL_PIVOT = g12.WALL_PIVOT
GROUND_PIVOT = 'Ground plane Z=0, footprint centre X=Y=0; front -Y'
FENCE_PIVOT = 'Ground plane Z=0, fence line Y=0, panel centre X=0'
ROOF_PIVOT = 'Roof plane Z=0, footprint centre X=Y=0; door faces -Y'
SPECS = {}


def register(name, budget, snap, pivot=WALL_PIVOT, width=None, tint=None):
    """width: exact X extent checked in validation. tint: per-instance preview swatch for accent/canvas/emissive."""
    def deco(fn):
        SPECS[name] = dict(build=fn, budget=budget, snap=snap, pivot=pivot, width=width, tint=tint or {})
        return fn
    return deco


class Mesh(g12.Mesh):
    def wire(self, a, b, t, col='grey.light', role='metal_painted', name='mesh_wire'):
        """Triangular-section rod a->b in the XZ plane (fence mesh). 8 triangles."""
        a, b = Vector(a), Vector(b)
        d = (b-a).normalized(); u = Vector((0, 1, 0)); w = d.cross(u)
        ring = [t*(math.cos(k*math.tau/3+math.pi/2)*u+math.sin(k*math.tau/3+math.pi/2)*w) for k in range(3)]
        v = [tuple(a+r) for r in ring]+[tuple(b+r) for r in ring]
        f = [(2, 1, 0), (3, 4, 5)]+[(i, (i+1) % 3, 3+(i+1) % 3, 3+i) for i in range(3)]
        return self.shell(v, f, col, role=role, normals='flat', member=t, name=name)

    def rod(self, pts, r, col='ink.light', role='metal_dark', seg=6, name='rod'):
        return self.tube(pts, [r]*len(pts), seg, col, role=role, normals='soft', name=name)


# ------------------------------------------------------------------ storefronts
def storefront(W):
    m = Mesh(); H = 3.2; inner = W/2-.30
    # Cast-iron end columns: base, fluted-looking shaft (chamfered prism), capital.
    for s in (-1, 1):
        xc = s*(W/2-.15)
        m.b(.30, .46, .30, x=xc, col='ink.light', role='metal_dark', name='column_base')
        m.prism_xy([(-.11, -.02), (-.11, -.34), (-.08, -.38), (.08, -.38), (.11, -.34), (.11, -.02)], .30, 2.65,
                   'ink.light', M=sk.T(xc, 0, 0), role='metal_dark', normals='weighted', member=.22, name='column_shaft')
        m.b(.30, .48, .18, x=xc, z=2.65, col='ink.light', role='metal_dark', name='column_capital')
    # Sign fascia with a cornice lip over the whole front.
    m.profile_x(W, [(0, 2.83), (-.46, 2.83), (-.46, 3.04), (-.52, 3.08), (-.52, 3.17), (-.49, 3.2), (0, 3.2)],
                col='grey', role='metal_painted', name='sign_fascia')
    # Recessed entrance: door 1.0 m wide set 0.36 m behind the glass line.
    dw = 1.0; dx = dw/2+.05
    bays = [(-inner, -dx-.05), (dx+.05, inner)]
    for x0, x1 in bays:
        bw = x1-x0; cx = (x0+x1)/2
        m.b(bw, .16, .45, x=cx, y=-.36, col='ink.light', role='metal_dark', name='kick_plate')
        m.b(bw-.20, .04, .25, x=cx, y=-.46, z=.10, col='grey', role='metal_painted', name='kick_panel')
        m.b(bw, .22, .06, x=cx, y=-.35, z=.45, col='ink.light', role='metal_dark', name='display_sill')
        m.b(bw, .012, 1.84, x=cx, y=-.36, z=.51, col='glass', role='glass', name='display_glass')
        if bw > 1.2:
            m.b(.08, .10, 1.84, x=cx, y=-.39, z=.51, col='ink.light', role='metal_dark', name='display_mullion')
            m.b(.08, .10, .38, x=cx, y=-.39, z=2.45, col='ink.light', role='metal_dark', name='transom_mullion')
    for s in (-1, 1):
        m.b(.10, .10, 2.35, x=s*dx, y=-.39, col='ink.light', role='metal_dark', name='recess_corner_post')
        m.b(.10, .34, .45, x=s*dx, y=-.21, col='ink.light', role='metal_dark', name='recess_side_kick')
        m.b(.012, .30, 1.84, x=s*dx, y=-.21, z=.51, col='glass', role='glass', name='recess_side_glass')
        m.b(.08, .10, .38, x=s*dx, y=-.39, z=2.45, col='ink.light', role='metal_dark', name='transom_mullion')
    m.b(2*inner, .14, .10, y=-.37, z=2.35, col='ink.light', role='metal_dark', name='transom_bar')
    m.b(2*inner, .012, .38, y=-.36, z=2.45, col='glass', role='glass', name='transom_glass')
    m.b(dw+.10, .40, .04, y=-.22, col='paving', role='concrete', name='mosaic_threshold')
    m.b(dw+.10, .36, .06, y=-.22, z=2.29, col='ink.light', role='metal_dark', name='recess_ceiling')
    m.b(dw, .06, 2.25, y=-.04, z=.04, col='wood', role='wood', name='door_leaf')
    m.b(dw-.32, .012, 1.30, y=-.074, z=.85, col='glass', role='glass', name='door_glass')
    m.b(dw-.12, .03, .30, y=-.085, z=.12, col='grey', role='metal_painted', name='door_kick_plate')
    m.b(.10, .10, .40, x=dw/2-.18, y=-.12, z=1.0, col='ink.light', role='metal_dark', name='door_pull')
    return m


register('US_STOREFRONT_CASTIRON_3M', 420, '3.0 m wide x 3.2 m high ground floor; threshold at origin. Fascia top Z=3.2; '
         'awning mounts with valance at Z=2.1.', width=3.0)(lambda: storefront(3.0))
register('US_STOREFRONT_CASTIRON_4_5M', 460, '4.5 m wide x 3.2 m high ground floor; threshold at origin. Same section as 3M; '
         'adjacent storefronts abut column to column.', width=4.5)(lambda: storefront(4.5))


def awning(W):
    m = Mesh()
    # Shed awning, 1.2 m projection: sloping cloth, flat valance and closed fabric cheeks.
    m.profile_x(W, [(0, 1.00), (-1.20, .30), (-1.20, 0), (-1.16, 0), (-1.16, .27), (0, .95)],
                col='red.dark', role='canvas', name='canvas_slope_valance')
    for s in (-1, 1):
        m.profile_x(.04, [(0, .97), (-1.17, .29), (0, .29)], col='red.dark', role='canvas',
                    x=s*(W/2-.02), name='canvas_cheek')
    m.b(W, .10, .10, y=-.05, z=.90, col='ink.light', role='metal_dark', name='wall_rail')
    for x in (-W/2+.25, W/2-.25):
        m.beam((x, -.04, .32), (x, -1.10, .30), .10, 'ink.light', 'metal_dark')
    return m


register('US_AWNING_CANVAS_3M', 150, '3 m width; wall origin at lowest valance level, wall rail +.95 m. Over '
         'US_STOREFRONT_CASTIRON_3M at Z=2.10. Cloth colour = canvas slot.', width=3.0, tint={'canvas': 'red.dark'})(lambda: awning(3.0))
register('US_AWNING_CANVAS_4_5M', 150, '4.5 m width; wall origin at lowest valance level, wall rail +.95 m. Over '
         'US_STOREFRONT_CASTIRON_4_5M at Z=2.10. Cloth colour = canvas slot.', width=4.5, tint={'canvas': 'conifer.dark'})(lambda: awning(4.5))


# ------------------------------------------------------------------ signs
@register('US_BLADE_SIGN', 120, 'Projecting sign; wall plane origin at bottom of board. Mount at Z>=3.0 between '
          'storefront fascia and first-floor windows. Faces = accent slot.', tint={'accent': 'teal.dark'})
def blade_sign():
    m = Mesh()
    m.b(.30, .06, 1.90, y=-.03, z=-.10, col='ink.light', role='metal_dark', name='wall_plate')
    m.b(.12, .70, 1.50, y=-.65, col='ink.light', role='metal_dark', name='board_frame')
    for s in (-1, 1):
        m.b(.02, .58, 1.36, x=s*.065, y=-.65, z=.07, col='teal.dark', role='accent', name='sign_face')
    m.b(.10, 1.00, .10, y=-.50, z=1.70, col='ink.light', role='metal_dark', name='top_arm')
    m.beam((0, -.06, 1.25), (0, -.70, 1.70), .10, 'ink.light', 'metal_dark')
    m.prism([(-.10, 0), (.10, 0), (0, .16)], .70, 'ink.light', M=sk.T(0, -.65, 1.50), role='metal_dark', name='crest')
    return m


@register('US_NEON_SIGN_BOARD', 200, '2.4 m wide wall board, wall plane bottom-centre origin. Tubes on 0.06 m '
          'stand-offs; emissive slot. Mount above the storefront fascia.', width=2.4, tint={'emissive': 'neon_pink'})
def neon_board():
    m = Mesh()
    m.prism([(-1.17, 0), (1.17, 0), (1.2, .03), (1.2, .87), (1.17, .90), (-1.17, .90), (-1.2, .87), (-1.2, .03)],
            .10, 'ink', M=sk.T(0, -.05, 0), role='metal_dark', normals='weighted', name='dark_board')
    t = .06; y = -.15; e = 'neon_pink'
    def tube(x, z, w, h):
        m.b(w, t, h, x=x, y=y, z=z, col=e, role='emissive', name='neon_tube')
    # Border loop.
    tube(0, .08, 2.20, t); tube(0, .76, 2.20, t); tube(-1.07, .14, t, .62); tube(1.07, .14, t, .62)
    # Generic blocky "EAT" lettering, 0.44 m tall.
    tube(-.62, .24, t, .44)
    for z in (.24, .43, .62):
        tube(-.50, z, .24 if z != .43 else .18, t)
    m.beam((-.20, y, .24), (0, y, .68), t, e, 'emissive')
    m.beam((.20, y, .24), (0, y, .68), t, e, 'emissive')
    tube(0, .40, .20, t)
    tube(.55, .62, .34, t); tube(.55, .24, t, .40)
    return m


@register('US_WALL_AD_PANEL', 140, '4.0 x 3.0 m painted ad on a blank brick wall; wall plane bottom-centre origin. '
          'Field = accent slot, lettering/border = plaster. Raised 1-3 cm, never coplanar with the wall.',
          width=4.0, tint={'accent': 'mustard.dark'})
def wall_ad():
    m = Mesh()
    m.b(4.0, .02, 3.0, y=-.01, col='mustard.dark', role='accent', name='paint_field')
    for z, h in ((0, .14), (2.86, .14)):
        m.b(4.0, .03, h, y=-.015, z=z, col='cream', role='plaster', name='border')
    for x in (-1.93, 1.93):
        m.b(.14, .03, 2.72, x=x, y=-.015, z=.14, col='cream', role='plaster', name='border')
    for x, w, z, h in ((-.55, 2.40, 2.15, .42), (-.85, 1.80, 1.45, .36), (.30, 2.60, .50, .30)):
        m.b(w, .03, h, x=x, y=-.015, z=z, col='cream', role='plaster', name='block_lettering')
    m.cyl(.48, .03, 8, 'cream', M=sk.T(1.25, -.03, 1.55)@sk.R(90, 'X'), role='plaster', normals='flat', name='logo_disc')
    return m


# ------------------------------------------------------------------ brick window heads
def voussoir_ring(m, pts_in, pts_out, gap, col, role, name):
    """Splayed brick pieces between matching inner/outer polylines; a gap reveals the wall as mortar."""
    for i in range(len(pts_in)-1):
        a, b, c, d = Vector(pts_in[i]), Vector(pts_in[i+1]), Vector(pts_out[i+1]), Vector(pts_out[i])
        ab = (b-a).normalized()*gap/2; dc = (c-d).normalized()*gap/2
        poly = [tuple(a+ab), tuple(b-ab), tuple(c-dc), tuple(d+dc)]
        m.prism(poly, .06, col, M=sk.T(0, -.03, 0), role=role, normals='flat', name=name)


@register('US_LINTEL_BRICK_JACK', 120, 'Flat splayed jack arch for WIN_FRAME_M (1.2 m). Z=0 = window top (sill +1.5 m); '
          'width 1.50 m, 6 cm relief, protruding keystone.', width=1.5)
def jack_lintel():
    m = Mesh(); h = .30; splay = 1.27            # joints radiate from a point 1.1 m below the window head
    for s in (-1, 1):
        x0 = (.75+.008)/splay                     # outer joint lands exactly on X=+/-.75 after the mortar gap
        xb = [s*(x0-(x0-.12)*k/3) for k in range(4)]
        voussoir_ring(m, [(x, 0) for x in xb], [(x*splay, h) for x in xb], .016, 'brick', 'brick', 'jack_brick')
    m.prism([(-.12, -.04), (.12, -.04), (.17, .34), (-.17, .34)], .10, 'chalk.dark',
            M=sk.T(0, -.05, 0), role='concrete', name='keystone')
    return m


@register('US_ARCH_BRICK_SEGMENTAL', 140, 'Segmental brick arch for WIN_FRAME_M (1.2 m). Spring line Z=0 = window top; '
          '9 voussoirs, rise .22 m, ring ~.23 m.', width=1.5)
def segmental_arch():
    m = Mesh(); span = 1.20; rise = .22
    r = (span*span/4+rise*rise)/(2*rise); cz = rise-r
    half = math.asin(span/2/r); n = 9
    ring = .75/math.sin(half)-r                   # ~.23 m ring; outer springing lands exactly on X=+/-.75
    ang = [-half+2*half*i/n for i in range(n+1)]
    inner = [(r*math.sin(a), cz+r*math.cos(a)) for a in ang]
    outer = [((r+ring)*math.sin(a), cz+(r+ring)*math.cos(a)) for a in ang]
    # Spring blocks square off both ends onto Z=0 so the arch sits on the window head.
    for s in (-1, 1):
        x0 = s*span/2; xo = s*(r+ring)*math.sin(half)
        o = outer[0 if s < 0 else n]
        m.prism([(x0, 0), (xo, 0), o], .06, 'brick.dark',
                M=sk.T(0, -.03, 0), role='brick', name='skewback')
    voussoir_ring(m, inner, outer, .014, 'brick', 'brick', 'voussoir')
    # Keystone: middle voussoir is stone and stands proud.
    k = n//2; a0, a1 = ang[k]-.02, ang[k+1]+.02
    m.prism([(r*math.sin(a0), cz+r*math.cos(a0)-.03), (r*math.sin(a1), cz+r*math.cos(a1)-.03),
             ((r+ring+.05)*math.sin(a1), cz+(r+ring+.05)*math.cos(a1)), ((r+ring+.05)*math.sin(a0), cz+(r+ring+.05)*math.cos(a0))],
            .10, 'chalk.dark', M=sk.T(0, -.05, 0), role='concrete', name='keystone')
    return m


# ------------------------------------------------------------------ stoop
@register('US_STOOP_BROWNSTONE', 300, 'Wall plane bottom-centre origin on ground. 7 x .18 m rises to a 1.0 m landing at '
          'Z=1.26 (parlour door threshold); six .30 m treads; 2.3 m wide incl. cheeks. Brownstone = brick slot.', width=2.30)
def stoop():
    m = Mesh(); n = 7; rise = .18; tread = .30; land = 1.0; top = n*rise; run = land+(n-1)*tread
    p = [(0, 0), (-run, 0)]
    for i in range(n):
        y = -run+i*tread
        p.append((y, (i+1)*rise))
        if i < n-1: p.append((y+tread, (i+1)*rise))  # the seventh rise lands on the landing itself
    p.append((0, top))
    m.profile_x(1.80, p, col='terracotta.dark', role='brick', name='stone_flight')
    for s in (-1, 1):
        x = s*1.025
        m.profile_x(.25, [(0, 0), (-run-.10, 0), (-run-.10, .62), (-run+.25, .62), (-land, top+.30), (0, top+.30)],
                    col='terracotta.dark', role='brick', x=x, name='cheek_wall')
        m.b(.25, .35, .14, x=x, y=-run+.075, z=.62, col='chalk.dark', role='concrete', name='newel_cap')
        # Iron railing: newel post, rake rail, landing rail, two balusters.
        m.b(.10, .10, .95, x=x, y=-run+.10, z=.76, col='ink.light', role='metal_dark', name='rail_newel')
        m.beam((x, -run+.10, 1.66), (x, -land, top+1.20), .10, 'ink.light', 'metal_dark')
        m.b(.10, land+.05, .10, x=x, y=-(land+.05)/2, z=top+1.15, col='ink.light', role='metal_dark', name='landing_rail')
        for k in (1, 2):
            yy = -run+.10+(run-land-.10)*k/3; zz = .62+(top+.30-.62)*k/3
            m.b(.10, .10, .90, x=x, y=yy, z=zz-.02, col='ink.light', role='metal_dark', name='baluster')
        m.b(.10, .10, .90, x=x, y=-land, z=top+.30, col='ink.light', role='metal_dark', name='landing_post')
    return m


# ------------------------------------------------------------------ cornices
@register('US_CORNICE_PRESSED_METAL_1M', 160, 'Tile along X at exactly 1 m pitch; flat end caps. Two console brackets per '
          'metre at X=+/-.25 keep the rhythm continuous. Top Z=.84; sits on the parapet/top-floor line.', width=1.0)
def pressed_cornice():
    m = Mesh()
    m.profile_x(1, [(0, 0), (-.08, 0), (-.08, .30), (-.14, .34), (-.14, .42), (-.30, .50), (-.62, .56), (-.66, .60),
                    (-.66, .78), (-.62, .84), (0, .84)], col='grey', role='metal_painted', name='pressed_profile')
    for x in (-.25, .25):
        m.profile_x(.12, [(-.06, .06), (-.20, .08), (-.24, .22), (-.56, .50), (-.56, .56), (-.06, .56)],
                    col='grey.dark', role='metal_painted', x=x, name='console_bracket')
    m.b(.30, .03, .16, y=-.095, z=.08, col='grey.dark', role='metal_painted', name='frieze_panel')
    return m


@register('US_CORNICE_DENTIL_1M', 120, 'Tile along X at exactly 1 m pitch; five .10 m dentils at .20 m pitch '
          '(X=-.4..+.4) so joints repeat seamlessly. Top Z=.40.', width=1.0)
def dentil_cornice():
    m = Mesh()
    m.profile_x(1, [(0, 0), (-.10, 0), (-.10, .08), (-.08, .10), (-.08, .26), (-.30, .26), (-.30, .36), (-.27, .40),
                    (0, .40)], col='chalk.dark', role='concrete', name='stone_profile')
    for x in (-.4, -.2, 0, .2, .4):
        m.b(.10, .12, .14, x=x, y=-.13, z=.11, col='chalk.dark', role='concrete', name='dentil')
    return m


# ------------------------------------------------------------------ roof / service
@register('US_ROOF_STAIR_BULKHEAD', 220, 'Roof-plane origin at footprint centre; 2.2 x 3.0 m brick box, 2.5 m walls; '
          'steel door on -Y. Keep 1.8 m clear in front of the door.', pivot=ROOF_PIVOT)
def bulkhead():
    m = Mesh()
    m.b(2.2, 3.0, 2.5, y=0, col='brick', role='brick', name='brick_box')
    m.prism_xy([(-1.22, -1.62), (1.22, -1.62), (1.25, -1.59), (1.25, 1.59), (1.22, 1.62), (-1.22, 1.62), (-1.25, 1.59),
                (-1.25, -1.59)], 2.5, 2.66, 'ink.light', role='roof', normals='weighted', name='roof_slab')
    m.b(1.10, .10, 2.25, y=-1.55, col='ink.light', role='metal_dark', name='door_frame')
    m.b(.90, .06, 2.05, y=-1.60, z=.05, col='grey', role='metal_painted', name='steel_door')
    m.b(.10, .10, .25, x=.32, y=-1.67, z=1.0, col='ink.light', role='metal_dark', name='door_lever')
    m.b(1.30, .45, .15, y=-1.72, col='paving', role='concrete', name='landing_slab')
    m.b(.18, .16, .22, x=.75, y=-1.58, z=2.10, col='lamp_glow', role='emissive', name='bulkhead_lamp')
    m.cyl(.15, .45, 8, 'grey', at=(-.55, .80, 2.66), role='metal_painted', normals='soft', name='roof_vent')
    return m


@register('US_LOADING_DOCK_DOOR', 220, 'Wall plane origin on street ground. 1.2 m dock, 3.0 x 3.0 m sectional door '
          '(sill Z=1.2), header to 4.5 m. Truck backs on -Y; keep 4 m clear.', width=3.4)
def loading_dock():
    m = Mesh()
    m.profile_x(3.4, [(0, 0), (-.98, 0), (-.98, 1.12), (-1.0, 1.14), (-1.0, 1.20), (0, 1.20)],
                col='grey', role='concrete', name='dock_platform')
    m.b(3.4, .10, .08, y=-.95, z=1.12, col='ink.light', role='metal_dark', name='edge_angle')
    for x in (-1.1, 1.1):
        m.b(.30, .14, .45, x=x, y=-1.05, z=.55, col='ink', role='metal_dark', name='rubber_bumper')
    m.b(2.0, .50, .04, y=-.40, z=1.20, col='grey.dark', role='metal_dark', name='leveller_plate')
    # Sectional door: six broad panels with V grooves in one closed profile.
    p = [(-.04, 1.2)]
    for i in range(6):
        z = 1.2+i*.5
        p += [(-.10, z+.04), (-.10, z+.46), (-.06, z+.5)]
    p += [(-.04, 4.2)]
    m.profile_x(3.0, p, col='grey.light', role='metal_painted', name='sectional_door')
    for x in (-1.6, 1.6):
        m.b(.20, .18, 3.05, x=x, y=-.09, z=1.2, col='mustard.dark', role='metal_painted', name='jamb_guard')
    m.b(3.4, .30, .30, y=-.15, z=4.2, col='ink.light', role='metal_dark', name='header_box')
    return m


# ------------------------------------------------------------------ chain-link fence
FENCE_H = 1.80


def chain_mesh(m, x0, x1, z0, z1, pitch, t=.035):
    """Diamond lattice of +/-45 degree wires clipped to the rectangle; chunky 0.30 m diamonds."""
    for sgn in (1, -1):
        cmin = (z0-x1) if sgn > 0 else (z0+x0)
        cmax = (z1-x0) if sgn > 0 else (z1+x1)
        k0 = math.ceil((cmin-1e-6)/pitch); k1 = math.floor((cmax+1e-6)/pitch)
        for k in range(k0, k1+1):
            c = k*pitch
            pts = []
            for x in (x0, x1):                       # z = sgn*x + c
                z = sgn*x+c
                if z0-1e-9 <= z <= z1+1e-9: pts.append((x, z))
            for z in (z0, z1):
                x = (z-c)*sgn
                if x0-1e-9 <= x <= x1+1e-9: pts.append((x, z))
            pts = sorted(set((round(x, 6), round(z, 6)) for x, z in pts))
            if len(pts) < 2: continue
            (ax, az), (bx, bz) = pts[0], pts[-1]
            if math.hypot(bx-ax, bz-az) < .08: continue
            m.wire((ax, 0, az), (bx, 0, bz), t)


@register('US_CHAINLINK_PANEL_3M', 240, 'Fence line Y=0; tile along X at exactly 3 m pitch with US_CHAINLINK_POST at '
          'every joint (X=+/-1.5). Top rail Z=1.75. Mesh wires .035 m: deliberate thin exception.',
          pivot=FENCE_PIVOT, width=3.0)
def chain_panel():
    m = Mesh()
    m.rod([(-1.5, 0, 1.75), (1.5, 0, 1.75)], .05, 'grey', 'metal_painted', name='top_rail')
    m.rod([(-1.5, 0, .10), (1.5, 0, .10)], .03, 'grey', 'metal_painted', name='bottom_tension_wire')
    chain_mesh(m, -1.45, 1.45, .10, 1.75, 3/7)
    return m


@register('US_CHAINLINK_POST', 80, 'Fence line Y=0, post centre X=0. Place at every 3 m panel joint and both gate '
          'sides. 2.0 m tall incl. dome cap.', pivot='Ground plane Z=0, post centre X=Y=0')
def chain_post():
    m = Mesh()
    m.cyl(.16, .08, 6, 'grey', role='concrete', normals='soft', name='footing')
    m.cyl(.06, 1.90, 6, 'grey', role='metal_painted', normals='soft', name='post_pipe')
    m.lathe([(.08, 1.90), (.08, 1.95), (0, 2.0)], 6, 'grey', role='metal_painted', normals='soft', name='dome_cap')
    m.b(.18, .14, .10, z=1.70, y=0, col='grey.dark', role='metal_dark', name='rail_clamp')
    return m


@register('US_CHAINLINK_GATE_1_2M', 240, 'Fence line Y=0; gate opening centre X=0 between posts at X=+/-0.60. '
          'Hinges on -X; swing about (-.60,0). Frame 1.10 x 1.75 m.', pivot=FENCE_PIVOT, width=1.20)
def chain_gate():
    m = Mesh(); x0, x1, z0, z1 = -.55, .55, .05, 1.80
    m.rod([(x0, 0, z0), (x1, 0, z0)], .05, 'grey', 'metal_painted', name='gate_frame')
    m.rod([(x0, 0, z1), (x1, 0, z1)], .05, 'grey', 'metal_painted', name='gate_frame')
    m.rod([(x0, 0, z0-.05), (x0, 0, z1+.05)], .05, 'grey', 'metal_painted', name='gate_frame')
    m.rod([(x1, 0, z0-.05), (x1, 0, z1+.05)], .05, 'grey', 'metal_painted', name='gate_frame')
    m.rod([(x0, 0, z0), (x1, 0, z1)], .04, 'grey', 'metal_painted', name='brace')
    chain_mesh(m, x0+.05, x1-.05, z0+.05, z1-.05, 3/7)
    for z in (.30, 1.50):
        m.b(.10, .14, .10, x=x0, y=0, z=z, col='ink.light', role='metal_dark', name='hinge')
    m.b(.10, .16, .20, x=x1, y=0, z=1.0, col='ink.light', role='metal_dark', name='fork_latch')
    return m


# ------------------------------------------------------------------ street furniture
@register('US_STREETLIGHT_COBRA', 320, 'Ground origin at pole base; arm reaches 2.25 m towards -Y (the carriageway). '
          'Kerb-side, 23 m spacing (map plan v17). Lens = emissive.', pivot='Ground plane Z=0, pole base centre X=Y=0; arm -Y')
def cobra():
    m = Mesh()
    m.cyl(.30, .10, 8, 'grey', role='concrete', normals='soft', name='footing')
    m.lathe([(.22, .10), (.22, .45), (.15, .58), (.11, .58)], 8, 'ink.light', role='metal_dark', normals='soft', name='base_cover')
    m.cyl(.12, 7.0, 8, 'grey', r_top=.07, at=(0, 0, .10), role='metal_painted', normals='soft', name='tapered_pole')
    m.lathe([(.07, 7.10), (.05, 7.18), (0, 7.20)], 8, 'grey', role='metal_painted', normals='soft', name='pole_cap')
    pts = [(0, 0, 6.70), (0, -.25, 7.15), (0, -.70, 7.42), (0, -1.30, 7.55), (0, -1.75, 7.58)]
    m.tube(pts, [.07, .065, .06, .055, .055], 6, 'grey', role='metal_painted', normals='soft', name='mast_arm')
    # Cobra head: rounded top-view teardrop shell + flat lens underneath.
    outline = [(0, -1.62), (.17, -1.72), (.22, -1.95), (.19, -2.25), (.08, -2.40), (-.08, -2.40), (-.19, -2.25),
               (-.22, -1.95), (-.17, -1.72)]
    m.prism_xy(outline, 7.46, 7.62, 'grey.light', role='metal_painted', normals='weighted', member=.16, name='cobra_head_body')
    top = [(x*.80, -2.0+(y+2.0)*.85) for x, y in outline]
    m.prism_xy(top, 7.62, 7.68, 'grey.light', role='metal_painted', normals='weighted', member=.06, name='cobra_head_top')
    lens = [(x*.80, -2.02+(y+2.0)*.80) for x, y in outline[1:]]
    m.prism_xy(lens, 7.40, 7.46, 'lamp_glow', role='emissive', normals='flat', member=.06, name='lens')
    return m


@register('US_PARKING_METER', 120, 'Ground origin; kerb edge .45 m from the kerb line, head faces the sidewalk (-Y). '
          'One per kerb parking bay.', pivot=GROUND_PIVOT)
def parking_meter():
    m = Mesh()
    m.cyl(.11, .04, 6, 'grey', role='metal_dark', normals='soft', name='flange')
    m.cyl(.05, 1.06, 6, 'ink.light', at=(0, 0, .04), role='metal_dark', normals='soft', name='pipe')
    m.prism([(-.13, 0), (.13, 0), (.13, .26), (-.13, .26)], .18, 'grey', M=sk.T(0, 0, 1.10), role='metal_painted', name='housing')
    m.lathe([(.13, 0), (.13, .06), (.09, .14), (0, .16)], 6, 'grey', M=sk.T(0, 0, 1.36)@sk.R(90, 'X')@sk.S(1, 1, .7)@sk.T(0, 0, -.08),
            role='metal_painted', normals='soft', name='dome_head')
    m.b(.18, .012, .10, y=-.10, z=1.38, col='glass', role='glass', name='display_window')
    m.b(.08, .04, .06, y=-.11, z=1.18, col='ink', role='metal_dark', name='coin_slot')
    return m


@register('US_NEWSPAPER_BOX', 120, 'Ground origin; set against a building or lamp, door faces -Y. Body colour = accent.',
          pivot=GROUND_PIVOT, tint={'accent': 'cobalt.dark'})
def news_box():
    m = Mesh()
    for x in (-.20, .20):
        m.b(.06, .38, .32, x=x, y=0, col='ink.light', role='metal_dark', name='pedestal_leg')
    m.b(.50, .44, .62, y=0, z=.32, col='cobalt.dark', role='accent', name='body')
    m.profile_x(.54, [(.24, .94), (-.26, .94), (-.26, .98), (-.20, 1.02), (.24, 1.02)], col='cobalt.dark', role='accent', name='lid')
    m.b(.38, .012, .30, y=-.226, z=.56, col='glass', role='glass', name='window')
    m.b(.40, .05, .10, y=-.245, z=.48, col='ink.light', role='metal_dark', name='pull_handle')
    m.b(.14, .10, .14, x=.12, y=-.10, z=1.02, col='grey', role='metal_painted', name='coin_mech')
    return m


@register('US_MAILBOX', 150, 'Ground origin; USPS-style collection box, chute faces -Y (sidewalk). Body = accent.',
          pivot=GROUND_PIVOT, tint={'accent': 'cobalt.dark'})
def mailbox():
    m = Mesh()
    for x in (-.20, .20):
        for y in (-.22, .22):
            m.b(.10, .10, .22, x=x, y=y, col='ink.light', role='metal_dark', name='leg')
    arc = [(.26*math.cos(a), 1.04+.18*math.sin(a)) for a in [math.pi*k/6 for k in range(7)]]
    m.prism([(-.26, .20), (.26, .20)]+arc, .56, 'cobalt.dark', role='accent', normals='weighted', name='body_round_top')
    m.prism([(-.18, .80), (.18, .80), (.18, .98), (-.18, .98)], .06, 'ink.light', M=sk.T(0, -.30, 0), role='metal_dark', name='chute_plate')
    m.b(.22, .06, .06, y=-.35, z=.98, col='grey', role='metal_painted', name='chute_handle')
    m.b(.30, .02, .16, y=-.285, z=.45, col='chalk', role='plaster', name='label_plate')
    return m


@register('US_FIRE_HYDRANT', 280, 'Ground origin at barrel centre; pumper nozzle faces the street (-Y). Kerb-side, '
          '.6 m from kerb. Body = accent.', pivot=GROUND_PIVOT, tint={'accent': 'red.dark'})
def hydrant():
    m = Mesh()
    m.lathe([(.18, 0), (.18, .06), (.12, .08), (.12, .52), (.15, .56), (.15, .61), (.11, .70), (.05, .80), (0, .80)], 8, 'red.dark', role='accent', normals='soft', name='barrel_bonnet')
    m.cyl(.04, .07, 6, 'grey', at=(0, 0, .78), role='metal_painted', normals='flat', name='operating_nut')
    for s in (-1, 1):
        m.cyl(.055, .12, 6, 'red.dark', M=sk.T(s*.10, 0, .44)@sk.R(s*90, 'Y'), role='accent', normals='soft', name='hose_nozzle')
        m.cyl(.065, .05, 6, 'grey', M=sk.T(s*.22, 0, .44)@sk.R(s*90, 'Y'), role='metal_painted', normals='flat', name='nozzle_cap')
    m.cyl(.08, .12, 6, 'red.dark', M=sk.T(0, -.10, .40)@sk.R(90, 'X'), role='accent', normals='soft', name='pumper_nozzle')
    m.cyl(.095, .06, 6, 'grey', M=sk.T(0, -.22, .40)@sk.R(90, 'X'), role='metal_painted', normals='flat', name='pumper_cap')
    return m


@register('US_DUMPSTER', 220, 'Ground origin at footprint centre; lids slope up to the back (+Y); fork pockets on X sides. '
          'Alley/courtyard placement. Body = accent.', pivot=GROUND_PIVOT, width=2.24, tint={'accent': 'conifer.dark'})
def dumpster():
    m = Mesh()
    m.profile_x(2.0, [(-.45, .15), (.60, .15), (.65, .20), (.65, 1.25), (-.62, 1.05), (-.62, .25)],
                col='conifer.dark', role='accent', name='steel_bin')
    m.profile_x(2.04, [(-.66, 1.03), (.69, 1.26), (.69, 1.31), (-.66, 1.09)], col='conifer.dark', role='accent', name='top_rim')
    for x in (-.50, .50):
        m.profile_x(.96, [(-.64, 1.09), (.62, 1.31), (.62, 1.36), (-.64, 1.15)], col='ink', role='metal_dark', x=x, name='plastic_lid')
    for s in (-1, 1):
        m.b(.12, .90, .18, x=s*1.06, y=.05, z=.72, col='conifer.dark', role='accent', name='fork_pocket')
    for x in (-.80, .80):
        for y in (-.30, .45):
            m.b(.12, .12, .15, x=x, y=y, col='ink', role='metal_dark', name='caster')
    return m


# ------------------------------- validation / export (same contracts as G12, extended slot list)
ensure_new = g12.ensure_new


def write_json(path, data):
    ensure_new(path)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def _hex(rgb): return '#%02X%02X%02X' % tuple(int(round(c*255)) for c in rgb)
def _unhex(h): return tuple(int(h[i:i+2], 16)/255 for i in (1, 3, 5))


def muted(swatch):
    r, g, b = (c/255 for c in sk.SWATCH[swatch])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return _hex(colorsys.hsv_to_rgb(h, s*.75, v*.85))


def slot_colours():
    grade = json.loads(GRADE.read_text(encoding='utf-8'))['categories']
    out = {}
    for role in ROLES:
        cat = CATEGORY[role]
        if role == 'metal_dark':
            h, s, v = colorsys.rgb_to_hsv(*_unhex(grade[cat]['after']['mean_hex']))
            out[role] = dict(category=cat, source='v07 mean at value %.2f (dark cast iron)' % DARK_IRON_VALUE,
                             hex=_hex(colorsys.hsv_to_rgb(h, s, DARK_IRON_VALUE)))
        elif role == 'emissive':
            out[role] = dict(category=None, source='Look_Palette_v2 lamp_glow, unmuted (light source)',
                             hex=sk._hexstr(sk.SWATCH['lamp_glow']).upper())
        elif role in FALLBACK:
            out[role] = dict(category=cat, source='Look_Palette_v2 %s, v07 initial grade S*0.75 V*0.85' % FALLBACK[role],
                             hex=muted(FALLBACK[role]))
        else:
            out[role] = dict(category=cat, source='grade_v07.json after.mean_hex', hex=grade[cat]['after']['mean_hex'])
    return out


def tint_hex(role, swatch):
    return sk._hexstr(sk.SWATCH[swatch]).upper() if role == 'emissive' else muted(swatch)


def flat_material(name, hexcol, role):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    lin = (*sk.srgb_to_linear(tuple(int(round(c*255)) for c in _unhex(hexcol))), 1.0)
    b.inputs['Base Color'].default_value = lin
    b.inputs['Roughness'].default_value = .65 if role == 'glass' else .95
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = .35
    if role == 'emissive':
        b.inputs['Emission Color'].default_value = lin; b.inputs['Emission Strength'].default_value = 1.5
    mat.diffuse_color = lin
    mat['surface_role'] = role; mat['stylekit_v3_category'] = CATEGORY[role] or ''; mat['v07_hex'] = hexcol
    return mat


def shared_materials(colours):
    if not (LIB/'Look_Palette_v2.png').is_file():
        raise RuntimeError('Existing STYLE_KIT_v2 palette required; shared assets are read only.')
    return {role: flat_material(role, colours[role]['hex'], role) for role in ROLES}


def object_from(name, m, coll, mats):
    sk.split_ngons(m)
    me = bpy.data.meshes.new(name+'_Mesh')
    me.from_pydata(m.verts, [], m.faces)
    if me.validate(): raise RuntimeError('Invalid mesh '+name)
    # All eleven ordered slots exist on every module, including unused ones (stable remapping).
    for role in ROLES: me.materials.append(mats[role])
    uv = me.uv_layers.new(name='UVMap'); values = []
    for i, f in enumerate(m.faces):
        values += list(sk.swatch_uv(m.fcol[i]))*len(f)
        me.polygons[i].material_index = ROLES.index(m.shells[m.fshell[i]]['role'])
    uv.data.foreach_set('uv', values)
    me.polygons.foreach_set('use_smooth', [True]*len(me.polygons))
    me.normals_split_custom_set(sk.loop_normals(m)); me.update()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob['module_id'] = name.removeprefix('SM_')
    return ob


def check_asset(name, m, ob, colours):
    spec = SPECS[name]; mn, mx = m.bounds()
    dup, opened = sk.Family._topology(m)
    vols = sk.Family._shell_volumes(m)
    ob.data.calc_loop_triangles()
    degenerate = 0
    for tri in ob.data.loop_triangles:
        p = [ob.data.vertices[k].co for k in tri.vertices]
        degenerate += (p[1]-p[0]).cross(p[2]-p[0]).length < 1e-10
    again = spec['build'](); sk.split_ngons(again)
    slots = [x.name for x in ob.data.materials]
    checks = dict(
        triangle_budget=len(ob.data.loop_triangles) <= spec['budget'],
        closed_shells=opened == 0 and dup == 0,
        all_shells_outward=all(v > 1e-9 for v in vols.values()),
        no_degenerate_triangles=degenerate == 0,
        palette_uv_cells=sk.Family._uv_check(ob, m) == 0,
        g12_eight_roles_first_then_us_slots=slots == list(ROLES) and tuple(slots[:8]) == g12.ROLES,
        slot_colours_from_v07=all(mat.get('v07_hex') == colours[mat.name]['hex'] for mat in ob.data.materials),
        applied_transforms=list(ob.scale) == [1, 1, 1] and all(abs(a) < 1e-7 for a in ob.rotation_euler) and ob.location.length < 1e-7,
        deterministic_rebuild=m.digest() == again.digest(),
        no_rig_animation=ob.animation_data is None and len(bpy.data.actions) == 0,
        no_jitter=True,
        nothing_behind_wall_or_below_ground=mx[1] <= 1e-6 if spec['pivot'] == WALL_PIVOT else mn[2] >= -1e-6,
    )
    if spec['width']:
        checks['exact_nominal_width'] = abs(mx[0]-mn[0]-spec['width']) < 1e-6
    used = sorted({ROLES[p.material_index] for p in ob.data.polygons})
    return dict(triangles=len(ob.data.loop_triangles), budget=spec['budget'],
                size_m=[round(mx[i]-mn[i], 6) for i in range(3)], bounds_min=mn, bounds_max=mx,
                pivot_local_m=[0, 0, 0], pivot=spec['pivot'], snapping=spec['snap'],
                swatches=sorted(set(m.fcol)), slots=slots, used_slots=used,
                preview_tints={r: dict(swatch=s, hex=tint_hex(r, s)) for r, s in spec['tint'].items()},
                shell_count=len(m.shells), closed_boundary_edges=opened, duplicate_directed_edges=dup,
                geometry_sha1=m.digest(), checks=checks, all_checks_passed=all(checks.values()))


def build_all():
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    for ob in list(scene.objects): bpy.data.objects.remove(ob, do_unlink=True)
    coll = bpy.data.collections.new('COL_G12US_Modules_Export'); scene.collection.children.link(coll)
    colours = slot_colours(); mats = shared_materials(colours); objects = {}; results = {}
    for name, spec in SPECS.items():
        mesh = spec['build']()
        ob = object_from('SM_'+name, mesh, coll, mats)
        ob['pivot_contract'] = spec['pivot']; ob['snapping'] = spec['snap']
        objects[name] = ob; results[name] = check_asset(name, mesh, ob, colours)
        bad = [k for k, v in results[name]['checks'].items() if not v]
        print('MODULE_CHECK', name, results[name]['triangles'], results[name]['size_m'], bad, flush=True)
    report = dict(task='G12-US', family=FAMILY, blender=bpy.app.version_string,
                  units='metres', source_axes='X right, Z up, facade outward -Y',
                  fbx_axes='axis_forward=-Z, axis_up=Y, apply_unit_scale=True, scale 1',
                  palette_source='../../STYLE_KIT_v2/_lib/Look_Palette_v2.png (UV0 cell selector, fallback only)',
                  palette_sha256=hashlib.sha256((LIB/'Look_Palette_v2.png').read_bytes()).hexdigest(),
                  colour_source='../../../Textures/StyleKit_v3/candidate_v07/grade_v07.json',
                  colour_source_sha256=hashlib.sha256(GRADE.read_bytes()).hexdigest(),
                  material_roles=list(ROLES), slot_categories=colours,
                  assets=results, total_assets=len(results),
                  total_triangles=sum(r['triangles'] for r in results.values()),
                  all_checks_passed=all(r['all_checks_passed'] for r in results.values()))
    return objects, mats, report


def export_all(objects, report, rev):
    blend = HERE/f'{FAMILY}_{rev}.blend'
    paths = [blend, HERE/f'validation_{rev}.json']+[HERE/f'{n}_{rev}.fbx' for n in objects]
    for p in paths: ensure_new(p)
    for name, ob in objects.items():
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = HERE/f'{name}_{rev}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                                 axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                                 use_mesh_modifiers=False, mesh_smooth_type='FACE', add_leaf_bones=False,
                                 bake_anim=False, path_mode='STRIP', use_custom_props=False)
        report['assets'][name]['fbx'] = path.name
    for i, ob in enumerate(objects.values()): ob.location = (i % 6*6, i//6*6, 0)
    report['master_layout'] = '6-column review grid; translate to origin before exporting. Local pivot stays (0,0,0).'
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report['files'] = {'blend': blend.name, 'validation': f'validation_{rev}.json'}
    write_json(HERE/f'validation_{rev}.json', report)
    return blend


def audit_existing(rev):
    report = json.loads((HERE/f'validation_{rev}.json').read_text(encoding='utf-8'))
    audit = dict(revision=rev, family=FAMILY, assets={})
    for name, expected in report['assets'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(HERE/f'{name}_{rev}.fbx'), use_anim=False)
        objects = list(bpy.context.scene.objects); meshes = [o for o in objects if o.type == 'MESH']
        bpy.context.view_layer.update()
        points = [o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        mn = [min(p[i] for p in points) for i in range(3)]; mx = [max(p[i] for p in points) for i in range(3)]
        tris = 0; bad_uv = 0; bad_tri = 0
        for o in meshes:
            o.data.calc_loop_triangles(); tris += len(o.data.loop_triangles)
            uv = o.data.uv_layers.active
            if uv is None: bad_uv += 1
            else:
                cells = [sk.swatch_uv(s) for s in expected['swatches']]
                bad_uv += sum(not any(abs(item.uv.x-u) < 1e-5 and abs(item.uv.y-v) < 1e-5 for u, v in cells) for item in uv.data)
            for t in o.data.loop_triangles:
                p = [o.matrix_world@o.data.vertices[k].co for k in t.vertices]
                bad_tri += (p[1]-p[0]).cross(p[2]-p[0]).length < 1e-10
        checks = dict(one_root_mesh=len(meshes) == 1 and meshes[0].parent is None,
                      triangles_match=tris == expected['triangles'],
                      bounds_match_1mm=all(abs(mn[i]-expected['bounds_min'][i]) <= .001 and abs(mx[i]-expected['bounds_max'][i]) <= .001 for i in range(3)),
                      pivot_origin=all(o.matrix_world.translation.length < 1e-5 for o in meshes),
                      ordered_slots=all([m.name for m in o.data.materials] == list(ROLES) for o in meshes),
                      palette_uv_preserved=bad_uv == 0, custom_normals=all(o.data.has_custom_normals for o in meshes),
                      no_degenerate_triangles=bad_tri == 0,
                      no_rigs_or_actions=all(o.type != 'ARMATURE' and o.animation_data is None for o in objects))
        audit['assets'][name] = dict(triangles=tris, size_m=[mx[i]-mn[i] for i in range(3)], checks=checks,
                                     all_checks_passed=all(checks.values()))
        print('FBX_AUDIT', name, [k for k, v in checks.items() if not v], flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(HERE/f'{FAMILY}_{rev}.blend'))
    mesh_names = sorted(o.name for o in bpy.context.scene.objects if o.type == 'MESH')
    audit['master_checks'] = dict(exact_module_meshes=mesh_names == sorted('SM_'+n for n in SPECS),
                                  metres=bpy.context.scene.unit_settings.scale_length == 1 and bpy.context.scene.unit_settings.system == 'METRIC',
                                  no_actions=len(bpy.data.actions) == 0)
    audit['all_checks_passed'] = all(r['all_checks_passed'] for r in audit['assets'].values()) and all(audit['master_checks'].values())
    number = 1
    while (HERE/f'export_audit_{rev}_{number:02d}.json').exists(): number += 1
    write_json(HERE/f'export_audit_{rev}_{number:02d}.json', audit)
    if not audit['all_checks_passed']: raise RuntimeError('Export audit failed')
    print('EXPORT_AUDIT_PASS', flush=True)


# ------------------------------- non-exported previews
def tinted_instance(src, coll, name, x=0, y=0, z=0, angle=0, tint=None):
    """Instance; preview tints override the accent/canvas/emissive slot per object (master data untouched)."""
    ob = g12.instance(src, coll, name, x, y, z, angle)
    for role, swatch in (tint or SPECS[src['module_id']]['tint']).items():
        idx = ROLES.index(role)
        key = f'Tint_{role}_{swatch}'
        mat = bpy.data.materials.get(key) or flat_material(key, tint_hex(role, swatch), role)
        ob.material_slots[idx].link = 'OBJECT'; ob.material_slots[idx].material = mat
    return ob


def lineup(objects, mats, rev, args):
    scene, coll, studio = g12.make_scene('G12US_All_Module_Lineup', args.samples, args.cpu)
    view = []
    for i, (name, src) in enumerate(objects.items()):
        col = i % 6; row = i//6
        x = (col-2.5)*5.6; z = (4-row)*9.0+.45
        # Ground/roof pieces stand in front of their panel; wall pieces sit on it.
        y = 0 if SPECS[name]['pivot'] == WALL_PIVOT else -1.4
        if name == 'US_STREETLIGHT_COBRA': y = -2.6
        inst = tinted_instance(src, coll, 'Lineup_'+name, x, y, z+(.45 if name.startswith(('US_LINTEL', 'US_ARCH')) else 0))
        view.append(inst)
        m = Mesh(); m.b(5.35, .08, 8.40, y=.06, col='panel' if row % 2 else 'cream', role='plaster')
        panel = object_from('Preview_Wall_'+name, m, coll, mats); panel.location = (x, .12, z-.40); view.append(panel)
        g12.label(coll, name.removeprefix('US_'), x, -.08, z+7.70, .24)
        g12.label(coll, str(len(src.data.loop_triangles))+' / '+str(SPECS[name]['budget'])+' TRIS', x, -.08, z+7.35, .20)
    m = Mesh(); m.b(.50, .32, 1.75, y=0, col='ochre', role='plaster')
    # Empty sixth cell of the last row holds the 1.75 m scale box.
    scale = object_from('HumanSize_Box_1_75m', m, coll, mats); scale.location = (2.5*5.6, -1.4, 9.45); view.append(scale)
    g12.label(coll, '1.75 m SCALE BOX', 2.5*5.6, -.08, 9.45+2.0, .24)
    fname = '01_all_modules_lineup.png'
    g12.render(studio, coll, HERE/'Previews'/rev/fname, view, az=10, el=6, res=(3600, 3600), ortho=True, pad=1.03)
    return dict(module_count=len(objects), scale_box_m=[.50, .32, 1.75], preview=fname)


def street_scene(objects, mats, rev, args):
    """Three-storey brick corner of American Downtown on a plain box, with a sidewalk and kerb furniture."""
    scene, coll, studio = g12.make_scene('G12US_Downtown_Street', args.samples, args.cpu)
    part = []; base = []; serial = 0
    def add(name, x=0, y=0, z=0, angle=0, tint=None):
        nonlocal serial; serial += 1
        ob = tinted_instance(objects[name], coll, f'street_{serial:03d}_{name}', x, y, z, angle, tint)
        part.append(ob); return ob
    def box(name, w, d, h, x=0, y=0, z=0, col='cream', role='plaster'):
        m = Mesh(); m.b(w, d, h, y=0, col=col, role=role)
        ob = object_from(name, m, coll, mats); ob.location = (x, y, z); base.append(ob); return ob
    W, D, H = 15, 9, 9.6
    box('Plain_Box_Brick', W, D, H, y=D/2, col='brick', role='brick')
    box('Plain_Roof', W, D, .18, y=D/2, z=H, col='ink.light', role='roof')
    # Studio ground is the paving sidewalk; the carriageway starts at the kerb line Y=-4.
    box('Street', W+4, 6.0, .01, y=-7.0, col='asphalt.dark', role='roof')
    box('HumanSize_Box_1_75m', .50, .32, 1.75, x=-2.6, y=-1.6, col='ochre')
    # Ground floor: two storefronts, a brownstone-style stoop entrance, loading dock on the side.
    add('US_STOREFRONT_CASTIRON_4_5M', x=-5.0); add('US_AWNING_CANVAS_4_5M', x=-5.0, z=2.10)
    add('US_STOREFRONT_CASTIRON_3M', x=4.2); add('US_AWNING_CANVAS_3M', x=4.2, z=2.10)
    add('US_STOOP_BROWNSTONE', x=-.4); add('DOOR_FRAME_ENTRANCE', x=-.4, z=1.26)
    add('US_NEON_SIGN_BOARD', x=4.2, z=4.45); add('US_BLADE_SIGN', x=-7.0, z=3.75)
    add('US_LOADING_DOCK_DOOR', x=7.5, y=5.5, angle=90)
    for f, head in ((1, 'US_LINTEL_BRICK_JACK'), (2, 'US_ARCH_BRICK_SEGMENTAL')):
        for x in (-5.8, -3.0, 1.6, 6.2) if f == 1 else (-5.8, -3.0, 1.6, 4.2, 6.2):
            add('WIN_FRAME_M', x=x, z=f*3.2+.9); add(head, x=x, z=f*3.2+2.4)
    add('WIN_FRAME_M', x=-.4, z=3.2+.9); add('US_ARCH_BRICK_SEGMENTAL', x=-.4, z=3.2+2.4)
    add('WIN_FRAME_M', x=-.4, z=6.4+.9); add('US_LINTEL_BRICK_JACK', x=-.4, z=6.4+2.4)
    add('US_WALL_AD_PANEL', x=7.5, y=4.5, z=5.4, angle=90)
    for x in range(-7, 8): add('US_CORNICE_PRESSED_METAL_1M', x=x, z=H-.84)
    for x in range(-7, 8): add('US_CORNICE_DENTIL_1M', x=x, z=3.20)
    add('US_ROOF_STAIR_BULKHEAD', x=-4.0, y=5.5, z=H+.18)
    # Kerb line at Y=-4.0.
    add('US_STREETLIGHT_COBRA', x=-6.5, y=-3.55); add('US_FIRE_HYDRANT', x=1.6, y=-3.4)
    for x in (-3.5, 2.5, 6.0): add('US_PARKING_METER', x=x, y=-3.55)
    add('US_NEWSPAPER_BOX', x=-7.4, y=-.6, tint={'accent': 'red.dark'}); add('US_NEWSPAPER_BOX', x=-8.0, y=-.6)
    add('US_MAILBOX', x=-1.6, y=-3.2, angle=180)
    add('US_DUMPSTER', x=9.6, y=1.4, angle=90)
    for x in (9.0, 12.0): add('US_CHAINLINK_PANEL_3M', x=x, y=8.5)
    for x in (7.5, 10.5, 13.5): add('US_CHAINLINK_POST', x=x, y=8.5)
    bpy.context.view_layer.update()
    root = HERE/'Previews'/rev
    records = {}
    for fname, az, el, eye, target in (('02_downtown_street_eye_3q.png', 28, 10, 1.75, (0, 1.5, 4.2)),
                                       ('03_downtown_street_high_3q.png', 35, 28, None, None),
                                       ('04_ground_floor_closeup.png', 20, 6, 1.75, (0, -.5, 1.9))):
        view = [o for o in base+part if not fname.startswith('04') or (o.location.z < 3 and abs(o.location.x) < 7.5)]
        g12.render(studio, coll, root/fname, view, az=az, el=el, res=(2000, 1500), eye=eye, target=target,
                   pad=1.05 if not fname.startswith('04') else .62)
        records[fname] = dict(eye_z_m=eye, camera=list(studio.cam.location))
    for o in part: o.hide_render = True
    path = root/'02_downtown_street_plain_box_same_camera.png'
    if not path.exists():
        g12.render(studio, coll, path, base+part, az=28, el=10, res=(2000, 1500), eye=1.75, target=(0, 1.5, 4.2), pad=1.05)
    for o in part: o.hide_render = False
    return dict(previews=records, plain_box_dimensions=[W, D, H], module_instances=len(part))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', type=int, default=1)
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--cpu', action='store_true')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--preview-existing', action='store_true')
    parser.add_argument('--audit-existing', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.revision < 1: raise RuntimeError('Positive revision required')
    rev = f'v{args.revision:02d}'
    if args.audit_existing: audit_existing(rev); return
    if not args.check_only and not args.preview_existing:
        for p in [HERE/f'{FAMILY}_{rev}.blend', HERE/f'validation_{rev}.json']+[HERE/f'{n}_{rev}.fbx' for n in SPECS]: ensure_new(p)
    objects, mats, report = build_all()
    if not report['all_checks_passed']: raise RuntimeError('Geometry gate failed; no deliverables exported.')
    print(f'ALL_{len(SPECS)}_GEOMETRY_PASS', report['total_triangles'], flush=True)
    if args.check_only: return
    if args.preview_existing:
        saved = json.loads((HERE/f'validation_{rev}.json').read_text(encoding='utf-8'))
        if any(saved['assets'][n]['geometry_sha1'] != r['geometry_sha1'] for n, r in report['assets'].items()):
            raise RuntimeError('Existing revision geometry differs; new revision required.')
    else: export_all(objects, report, rev)
    if not args.no_render:
        # G12 window frames are placed in the street preview only; they are not part of this export.
        g12_objs = {}
        coll = bpy.data.collections.new('COL_G12_Borrowed_NotExported')
        for n in ('WIN_FRAME_M', 'DOOR_FRAME_ENTRANCE'):
            mesh = g12.SPECS[n]['build'](); g12_objs[n] = object_from('G12_'+n, mesh, coll, mats)
            g12_objs[n]['module_id'] = n
            SPECS.setdefault(n, dict(tint={}))
        line = lineup(objects, mats, rev, args)
        street = street_scene({**objects, **g12_objs}, mats, rev, args)
        path = HERE/f'preview_manifest_{rev}.json'
        if not path.exists(): write_json(path, dict(lineup=line, street=street))
        preview_blend = HERE/f'{FAMILY}_Demos_{rev}.blend'
        if not preview_blend.exists():
            ensure_new(preview_blend); bpy.ops.wm.save_as_mainfile(filepath=str(preview_blend))


if __name__ == '__main__': main()
