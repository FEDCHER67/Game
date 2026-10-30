"""Procedural VAN-TIER0-ASTRA-001 builder (Blender 5.2, background).

Blender Z up, -Y forward, metres. Vehicle left = +X (driver side), right = -X (sliding door side).
Proportions measured from Source/TripoViews/Rev01 (owner-approved REV07 views).
Run:  blender -b --factory-startup --python build_van.py -- --revision N [--no-render]
Every revision writes new numbered .blend/.fbx/validation/previews; existing files are never overwritten.
v01 was built by the previous version of this script (closed cab, three opening doors).
--revision 2 builds the v02 layout (Fedya-approved, 4.78 x 1.88 x 2.08 m).
--revision 3 builds the v03 layout (Vadim 30.10, V2): the same van, bigger (5.6 x 2.05 x 2.6 m, high roof),
so a 1.8 m player stands upright in the cargo bay and walks in through the sliding and rear doors; a full-height
see-through bar grille (dark metal) between the cab and the bay; the two front seats joined into one bench.
--revision 4 and later build the v04 layout (Vadim 30.10): v02's exact design stretched to 5.6 x 2.16 x 2.6 m (no roof
step), a bulkhead with a mesh window, a detailed bench and dashboard, interior-only materials (see V04 below).
--revision 5 and later build the v05 layout (Vadim 30.10, after driving v04): v04 with the cargo section 0.55 m longer
(6.15 m over the bumpers, v02's elongated look back), two identical front seats instead of the bench, the bumper top 6 mm
under the rear sill (no coplanar faces, no z-fight flicker).
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
NAME = 'VAN-TIER0-ASTRA-001'
ap = argparse.ArgumentParser()
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--no-render', action='store_true')
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = f'v{args.revision:02d}'
blend_path = HERE / f'{NAME}_{REV}.blend'
fbx_path = HERE / f'{NAME}_{REV}.fbx'
json_path = HERE / f'validation_{REV}.json'
preview_dir = HERE / 'Previews' / REV
for p in (blend_path, fbx_path, json_path):
    if p.exists():
        sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ---------------------------------------------------------------- dimensions per layout
# Boxes are (x0, x1, y0, y1, z0, z1); x values given for the left (+X) side are mirrored where the code says so.
V02 = dict(
    HALF_W=0.94,            # body half width below the belt
    BELT_Z=1.30,            # sides lean inward above this height
    ROOF_Z=2.08,
    ROOF_HALF_W=0.80,       # half width at roof height (tumblehome)
    BODY_BOTTOM=0.35,
    FRONT_Y=-2.29, REAR_Y=2.19,
    WHEEL_R=0.37, WHEEL_W=0.24, WHEEL_X=0.80, HUB_R=0.215, CAP_R=0.08,
    AXLES=(-1.60, 1.56),    # front, rear (y)
    WALL=0.05,
    FLOOR_Z=0.55,
    GAP=0.006,              # visible door gap
    SIDE_PROFILE=[(2.19, 0.35), (2.19, 2.08), (-0.99, 2.08), (-1.69, 1.38), (-2.22, 1.08), (-2.29, 0.98), (-2.29, 0.35)],
    # hollow cab + cargo: rear wall, roof, windshield inner face, footwell front
    CAVITY_PROFILE=[(2.13, 0.55), (2.13, 1.98), (-1.019, 1.98), (-1.699, 1.30), (-1.70, 0.55)],
    FRONT_DOOR_POLY=[(-1.48, 0.40), (-0.44, 0.40), (-0.44, 1.97), (-1.04, 1.97), (-1.65, 1.36)],
    CAB_WINDOW=[(-1.61, 1.36), (-0.55, 1.36), (-0.55, 1.92), (-1.05, 1.92)],
    SLIDE_RECT=(-0.42, 0.90, 0.40, 1.93),   # y0, y1, z0, z1
    SLIDE_TRAVEL=1.02,
    REAR_DOOR_Z=(0.62, 1.94), REAR_DOOR_W=0.80,
    DRIVER_EYE=(0.48, -0.78, 1.60),
    BEVEL=0.045,
    ARCH=(0.44, 0.75, 0.925), HOUSING=(0.48, 0.80, 0.92),          # radius, depth, x
    CREASE=(0.93, 1.2, -2.25, 2.25, 1.0),                           # x0, x1, y0, y1, z
    WS_TOP=(-0.99, 2.08), WS_Z=(2.00, 1.44),                        # windshield line top point; opening z range
    HOLE_OUT=1.3,
    MIRROR_ARM_HW_Z=1.40, MIRROR_ARM=(1.01, -1.33, -1.29, 1.36, 1.41),  # x1, y0, y1, z0, z1 (x0 = hw - 0.02)
    MIRROR=(1.00, 1.07, -1.37, -1.25, 1.30, 1.57),
    HANDLE_FRONT=(0.935, 0.958, -0.70, -0.58, 1.19, 1.24),
    HANDLE_SLIDE=(-0.958, -0.935, -0.37, -0.32, 1.10, 1.27),
    REAR_WIN=(0.07, 0.70, 1.36, 1.86), REAR_GLASS=(0.05, 0.72, 1.34, 1.88),   # x0, x1, z0, z1
    HANDLE_REAR=(-0.10, -0.06, 1.08, 1.22),
    FASCIA=(0.80, 0.70, 1.02), GRILLE=(0.40, 0.735, 0.985),       # half width, z0, z1
    SLATS=(0.38, (0.79, 0.86, 0.93), 0.016),                        # half width, z centres, half height
    HEADLIGHT=(0.105, 0.61, 0.86), INDICATOR=(0.52, 0.72, 0.635, 0.685),
    TAILS=(0.81, 0.915, [(0.84, 0.98, 'VAN_Tail_Red'), (0.98, 1.10, 'VAN_Indicator_Orange'), (1.10, 1.24, 'VAN_Tail_Red')]),
    BUMPER=(0.97, -2.42, 2.36, 0.28, 0.62),                         # half width, front y0, rear y1, z0, z1
    RAIL=(-0.962, -0.935, 0.95, 1.98, 1.15, 1.21),
    SEATS=[('Seat_Driver', 0.26, 0.72), ('Seat_Bench', -0.82, -0.10)],
    SEAT_Y=(-1.06, -0.62, -0.50), SEAT_Z=(0.98, 1.66),             # base front, back front, back rear; base top, back top
    DASH=(-1.70, -1.40, 0.95, 1.30, 1.25),                          # y0, y1, z0, z1, z for its width
    COLUMN=(0.455, 0.505, -1.44, -1.32, 1.04, 1.14),
    SW=((0.48, -1.30, 1.17), 0.165, 0.022, 0.05, 0.155),            # centre, rim radius, tube, hub, spoke half
    FRONT_PIVOT_Y=-1.55,
    PARTITION=None,
    RENDER=dict(scale=1.0, target_z=1.05, ortho_front=3.3, ortho_side=5.6),
)

V03 = dict(V02)
V03.update(
    HALF_W=1.025, BELT_Z=1.44, ROOF_Z=2.60, ROOF_HALF_W=0.93, BODY_BOTTOM=0.36,
    FRONT_Y=-2.68, REAR_Y=2.60,
    WHEEL_R=0.40, WHEEL_W=0.26, WHEEL_X=0.875, HUB_R=0.232, CAP_R=0.086,
    AXLES=(-1.88, 1.80),
    # high roof: the 45 degree windshield as on v02, then a 26.6 degree roof cap up to the raised roof over cab and bay
    SIDE_PROFILE=[(2.60, 0.36), (2.60, 2.60), (-0.62, 2.60), (-1.30, 2.26), (-2.06, 1.50), (-2.60, 1.18), (-2.68, 1.07),
                  (-2.68, 0.36)],
    # 6 cm roof and rear wall, the cap and windshield faces 6 / 5 cm inside the shell; inner height 2.54 - 0.55 = 1.99 m
    CAVITY_PROFILE=[(2.54, 0.55), (2.54, 2.54), (-0.6058, 2.54), (-1.2927, 2.1965), (-2.0693, 1.42), (-2.07, 0.55)],
    FRONT_DOOR_POLY=[(-1.74, 0.40), (-0.62, 0.40), (-0.62, 2.18), (-1.32, 2.18), (-2.00, 1.50)],
    CAB_WINDOW=[(-1.955, 1.50), (-0.73, 1.50), (-0.73, 2.12), (-1.335, 2.12)],
    SLIDE_RECT=(-0.50, 0.98, 0.40, 2.46),
    SLIDE_TRAVEL=1.26,
    REAR_DOOR_Z=(0.62, 2.50), REAR_DOOR_W=0.86,
    DRIVER_EYE=(0.53, -0.90, 1.72),
    BEVEL=0.05,
    ARCH=(0.47, 0.80, 1.01), HOUSING=(0.51, 0.84, 1.00),
    CREASE=(1.015, 1.3, -2.64, 2.66, 1.10),
    WS_TOP=(-1.30, 2.26), WS_Z=(2.18, 1.56),
    HOLE_OUT=1.4,
    MIRROR_ARM_HW_Z=1.52, MIRROR_ARM=(1.095, -1.67, -1.63, 1.50, 1.55),
    MIRROR=(1.085, 1.16, -1.71, -1.59, 1.43, 1.73),
    HANDLE_FRONT=(1.02, 1.043, -0.88, -0.76, 1.31, 1.36),
    HANDLE_SLIDE=(-1.043, -1.02, -0.45, -0.40, 1.22, 1.42),
    REAR_WIN=(0.07, 0.76, 1.50, 2.40), REAR_GLASS=(0.05, 0.78, 1.48, 2.42),
    HANDLE_REAR=(-0.10, -0.06, 1.22, 1.38),
    FASCIA=(0.872, 0.754, 1.115), GRILLE=(0.436, 0.794, 1.076),
    SLATS=(0.414, (0.856, 0.935, 1.014), 0.018),
    HEADLIGHT=(0.115, 0.665, 0.935), INDICATOR=(0.567, 0.785, 0.681, 0.737),
    TAILS=(0.875, 1.0, [(0.90, 1.06, 'VAN_Tail_Red'), (1.06, 1.19, 'VAN_Indicator_Orange'), (1.19, 1.35, 'VAN_Tail_Red')]),
    BUMPER=(1.055, -2.83, 2.77, 0.28, 0.62),
    RAIL=(-1.047, -1.02, 1.03, 2.40, 1.28, 1.34),
    # one bench across the cab: driver seat and passenger bench joined, no passage between them
    SEATS=[('Seat_Bench', -0.93, 0.93)],
    SEAT_Y=(-1.20, -0.74, -0.62), SEAT_Z=(1.02, 1.64),
    DASH=(-2.06, -1.70, 1.05, 1.42, 1.35),
    COLUMN=(0.505, 0.555, -1.72, -1.52, 1.16, 1.26),
    SW=((0.53, -1.50, 1.30), 0.18, 0.024, 0.055, 0.17),
    FRONT_PIVOT_Y=-1.84,
    # cab / bay grille: a frame on the inner walls, floor and roof, vertical bars every 12 cm (10 cm clear), cross bars
    PARTITION=dict(y0=-0.585, y1=-0.535, frame=0.05, bar=0.02, bar_step=0.12, bar_x=0.78, cross_z=(0.90, 1.25, 1.60, 1.95, 2.30)),
    RENDER=dict(scale=1.17, target_z=1.30, ortho_front=3.9, ortho_side=6.6),
)

V02['WS_BOTTOM'] = (-1.69, 1.38)
V03['WS_BOTTOM'] = (-2.06, 1.50)

# v04 (Vadim 30.10, after the v03 renders): v02's exact shape and lines, only bigger. Every v02 number goes through one
# affine stretch (x * 1.15, y * 1.1715, z * 1.3356 - 0.178: roof 2.08 -> 2.60, bumper top 0.62 -> 0.65, floor 0.55 ->
# 0.556), so the roof, the windshield sloping straight into it, the glass, doors and nose stay v02's. Round parts (wheels,
# arches, headlights, steering wheel) keep round. Changed on purpose: the inner roof 6 cm under the roof (inner height
# 1.98 m), the sliding and rear door tops raised (2.46 / 2.50: a 1.8 m player walks in upright), the B-pillar 2 cm wider
# for the bulkhead. Inside: a bulkhead behind the front bench (solid panel up to the seat backs, a mesh window above), the
# bench as three joined seats with cushions, backrests and headrests, a dashboard with an instrument hood, gauges, vents
# and a glovebox. Interior surfaces use their own materials (VAN_Interior, VAN_Dash, VAN_Seat, VAN_Seat_Fabric,
# VAN_Interior_Black) so the game can switch shadow receiving off for them (no shadow shimmer inside the van).
SX4, SY4, AZ4, BZ4 = 1.15, 1.1715, 1.3356, -0.178
X4 = lambda x: round(SX4 * x, 4)
Y4 = lambda y: round(SY4 * y, 4)
Z4 = lambda z: round(AZ4 * z + BZ4, 4)
P4 = lambda pts: [(Y4(y), Z4(z)) for y, z in pts]
V04 = dict(V02)
_floor4 = Z4(0.55)
_roof_in4 = 2.54
# the inner windshield face of v02 (through (-1.019, 1.98) and (-1.699, 1.30)), stretched, met by the 6 cm inner roof
_wa, _wb = (Y4(-1.019), Z4(1.98)), (Y4(-1.699), Z4(1.30))
_wy = _wa[0] + (_roof_in4 - _wa[1]) * (_wa[0] - _wb[0]) / (_wa[1] - _wb[1])
V04.update(
    HALF_W=X4(0.94), BELT_Z=Z4(1.30), ROOF_Z=Z4(2.08), ROOF_HALF_W=X4(0.80), BODY_BOTTOM=Z4(0.35),
    FRONT_Y=Y4(-2.29), REAR_Y=Y4(2.19),
    WHEEL_R=0.44, WHEEL_W=0.27, WHEEL_X=X4(0.80), HUB_R=0.255, CAP_R=0.095,
    AXLES=(Y4(-1.60), Y4(1.56)),
    FLOOR_Z=_floor4,
    SIDE_PROFILE=P4(V02['SIDE_PROFILE']),
    CAVITY_PROFILE=[(Y4(2.13), _floor4), (Y4(2.13), _roof_in4), (round(_wy, 4), _roof_in4), _wb, (Y4(-1.70), _floor4)],
    FRONT_DOOR_POLY=[(Y4(-1.48), Z4(0.40)), (-0.535, Z4(0.40)), (-0.535, Z4(1.97)), (Y4(-1.04), Z4(1.97)), (Y4(-1.65), Z4(1.36))],
    CAB_WINDOW=[(Y4(-1.61), Z4(1.36)), (-0.664, Z4(1.36)), (-0.664, Z4(1.92)), (Y4(-1.05), Z4(1.92))],
    SLIDE_RECT=(Y4(-0.42), Y4(0.90), Z4(0.40), 2.46),
    SLIDE_TRAVEL=round(1.02 * SY4, 3),
    REAR_DOOR_Z=(Z4(0.62), 2.50), REAR_DOOR_W=X4(0.80),
    DRIVER_EYE=(X4(0.48), Y4(-0.78), Z4(1.60)),
    BEVEL=0.05,
    ARCH=(0.51, X4(0.75), X4(0.925)), HOUSING=(0.55, X4(0.80), X4(0.92)),
    CREASE=(X4(0.93), X4(1.2), Y4(-2.25), Y4(2.25), Z4(1.0)),
    WS_TOP=(Y4(-0.99), Z4(2.08)), WS_BOTTOM=(Y4(-1.69), Z4(1.38)), WS_Z=(Z4(2.00), Z4(1.44)),
    WS_INSET=0.092, HOLE_OUT=1.45,
    MIRROR_ARM_HW_Z=Z4(1.40), MIRROR_ARM=(X4(1.01), Y4(-1.33), Y4(-1.29), Z4(1.36), Z4(1.41)),
    MIRROR=(X4(1.00), X4(1.07), Y4(-1.37), Y4(-1.25), Z4(1.30), Z4(1.57)),
    HANDLE_FRONT=(X4(0.935), X4(0.958), Y4(-0.70), Y4(-0.58), Z4(1.19), Z4(1.24)),
    HANDLE_SLIDE=(X4(-0.958), X4(-0.935), Y4(-0.37), Y4(-0.32), Z4(1.10), Z4(1.27)),
    REAR_WIN=(X4(0.07), X4(0.70), Z4(1.36), 2.393), REAR_GLASS=(X4(0.05), X4(0.72), Z4(1.34), 2.42),
    HANDLE_REAR=(X4(-0.10), X4(-0.06), Z4(1.08), Z4(1.22)),
    FASCIA=(X4(0.80), Z4(0.70), Z4(1.02)), GRILLE=(X4(0.40), Z4(0.735), Z4(0.985)),
    SLATS=(X4(0.38), (Z4(0.79), Z4(0.86), Z4(0.93)), 0.021),
    HEADLIGHT=(0.125, X4(0.61), Z4(0.86)), INDICATOR=(X4(0.52), X4(0.72), Z4(0.635), Z4(0.685)),
    TAILS=(X4(0.81), X4(0.915), [(Z4(0.84), Z4(0.98), 'VAN_Tail_Red'), (Z4(0.98), Z4(1.10), 'VAN_Indicator_Orange'),
                                 (Z4(1.10), Z4(1.24), 'VAN_Tail_Red')]),
    BUMPER=(X4(0.97), Y4(-2.42), Y4(2.36), Z4(0.28), Z4(0.62)),
    RAIL=(X4(-0.962), X4(-0.935), Y4(0.95), Y4(1.98), Z4(1.15), Z4(1.21)),
    SEATS=[],
    SEAT_Y=(Y4(-1.06), Y4(-0.62), Y4(-0.50)), SEAT_Z=(Z4(0.98), 1.80),
    DASH=(Y4(-1.70), Y4(-1.40), Z4(0.95), Z4(1.30), Z4(1.25)),
    COLUMN=(X4(0.455), X4(0.505), Y4(-1.44), Y4(-1.32), Z4(1.04), Z4(1.14)),
    SW=((X4(0.48), Y4(-1.30), Z4(1.17)), 0.185, 0.025, 0.055, 0.175),
    FRONT_PIVOT_Y=Y4(-1.55),
    PARTITION=None,
    # bench: three joined seats (driver, two passengers), x ranges; bulkhead between the two door edges
    BENCH=[(0.13, 0.99), (-0.43, 0.13), (-0.99, -0.43)],
    BULKHEAD=dict(y0=-0.534, y1=-0.494, panel_top=1.82, frame=0.05, wire=0.016, step=0.09),
    INTERIOR_MATS=True,
    RENDER=dict(scale=1.17, target_z=1.30, ortho_front=3.9, ortho_side=6.6),
)

# v05 (Vadim 30.10, after driving v04): v04 got bigger but lost v02's elongated look (L/H 2.30 -> 2.15). The cargo
# section is 0.55 m longer: everything behind y 1.15 (behind the sliding door, in front of the rear arch) moves back
# 0.55 m, so the cab, the nose and the sliding door stay v04's, the side panel, roof, floor, rail and wheelbase grow
# (5.60 -> 6.15 m over the bumpers, L/H 2.37). Two identical seats (driver left, passenger right, mirrored, a narrow gap)
# instead of the bench. The bumper top 6 mm under the rear door sill: the bumper runs 6 cm into the body, and a top
# coplanar with the sill z-fights (flickers) at the rear threshold (found by a coplanar-face check).
SPLIT5, STRETCH5 = 1.15, 0.55
S5 = lambda y: round(y + STRETCH5, 4) if y > SPLIT5 else y
V05 = dict(V04)
_c, _b, _r = V04['CREASE'], V04['BUMPER'], V04['RAIL']
V05.update(
    REAR_Y=S5(V04['REAR_Y']),
    AXLES=(V04['AXLES'][0], S5(V04['AXLES'][1])),
    SIDE_PROFILE=[(S5(y), z) for y, z in V04['SIDE_PROFILE']],
    CAVITY_PROFILE=[(S5(y), z) for y, z in V04['CAVITY_PROFILE']],
    CREASE=(_c[0], _c[1], _c[2], S5(_c[3]), _c[4]),
    BUMPER=(_b[0], _b[1], S5(_b[2]), _b[3], _b[4] - 0.006),
    RAIL=(_r[0], _r[1], _r[2], S5(_r[3]), _r[4], _r[5]),
    # two identical seats, mirrored: centres +-0.50 (the steering wheel at 0.55), 0.80 wide, 0.20 apart
    BENCH=[(0.10, 0.90), (-0.90, -0.10)], SEPARATE_SEATS=True,
    RENDER=dict(V04['RENDER'], ortho_side=7.2),
)

G = V02 if args.revision <= 2 else (V03 if args.revision == 3 else (V04 if args.revision == 4 else V05))
IM = G.get('INTERIOR_MATS', False)
M_DASH = 'VAN_Dash' if IM else 'VAN_Trim_Dark'          # dashboard, steering column and wheel, bulkhead frame
M_IBLACK = 'VAN_Interior_Black' if IM else 'VAN_Grille_Black'
HALF_W, BELT_Z, ROOF_Z, ROOF_HALF_W = G['HALF_W'], G['BELT_Z'], G['ROOF_Z'], G['ROOF_HALF_W']
BODY_BOTTOM, FRONT_Y, REAR_Y = G['BODY_BOTTOM'], G['FRONT_Y'], G['REAR_Y']
WHEEL_R, WHEEL_W, WHEEL_X = G['WHEEL_R'], G['WHEEL_W'], G['WHEEL_X']
AXLES, WALL, FLOOR_Z, GAP = G['AXLES'], G['WALL'], G['FLOOR_Z'], G['GAP']
SIDE_PROFILE, CAVITY_PROFILE = G['SIDE_PROFILE'], G['CAVITY_PROFILE']
FRONT_DOOR_POLY, CAB_WINDOW, SLIDE_RECT = G['FRONT_DOOR_POLY'], G['CAB_WINDOW'], G['SLIDE_RECT']
REAR_DOOR_Z, REAR_DOOR_W, DRIVER_EYE = G['REAR_DOOR_Z'], G['REAR_DOOR_W'], G['DRIVER_EYE']


def hw(z):
    """Outer half width of the body at height z."""
    if z <= BELT_Z:
        return HALF_W
    t = min(1.0, (z - BELT_Z) / (ROOF_Z - BELT_Z))
    return HALF_W + (ROOF_HALF_W - HALF_W) * t


def srgb(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


MATS = {}


def mat(name, rgb, rough=0.85, alpha=1.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = srgb(rgb)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.25
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    m.diffuse_color = srgb(rgb)[:3] + (alpha,)
    MATS[name] = m
    return m


mat('VAN_Body_Cream', (233, 222, 203))
mat('VAN_Body_Crease', (196, 184, 163))
mat('VAN_Interior', (150, 144, 134))
mat('VAN_Trim_Dark', (62, 63, 66))
mat('VAN_Grille_Black', (34, 35, 37))
mat('VAN_Glass', (58, 66, 80), rough=0.15, alpha=0.45)
mat('VAN_Light_White', (236, 236, 232), rough=0.4)
mat('VAN_Indicator_Orange', (226, 128, 28), rough=0.5)
mat('VAN_Tail_Red', (204, 38, 38), rough=0.5)
mat('VAN_Hub_Cream', (214, 205, 186))
mat('VAN_Tire', (44, 44, 46), rough=0.95)
mat('VAN_Seat', (70, 72, 78), rough=0.95)
# v04 interior-only materials (same tones as their outside twins; the seat fabric a lighter grey-blue)
mat('VAN_Dash', (62, 63, 66))
mat('VAN_Interior_Black', (34, 35, 37))
mat('VAN_Seat_Fabric', (112, 117, 128), rough=0.95)

col = bpy.data.collections.new(NAME)
scene.collection.children.link(col)
cutters = bpy.data.collections.new('Cutters_NotExported')
scene.collection.children.link(cutters)


def obj_from_bm(name, bm, material, collection=col):
    # mirrored construction can leave closed meshes inside-out; booleans then imprint without removing
    if bm.faces and all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MATS[material])
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, material, collection=col):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return obj_from_bm(name, bm, material, collection)


def beam(name, p0, p1, w, y0, y1, material, collection=col):
    """Box from (x, z) point p0 to p1, w wide across in the XZ plane, from y0 to y1 deep."""
    a, b = Vector((p0[0], 0.0, p0[1])), Vector((p1[0], 0.0, p1[1]))
    u = (b - a).normalized()
    n = Vector((-u.z, 0.0, u.x))
    length = (b - a).length
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        c = v.co.copy()
        p = a + u * ((c.x + 0.5) * length) + n * (c.z * w)
        v.co = Vector((p.x, (y0 + y1) / 2 + c.y * (y1 - y0), p.z))
    return obj_from_bm(name, bm, material, collection)


def cyl(name, r, depth, center, axis, material, segments=16, collection=col):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r, radius2=r, depth=depth)
    rot = {'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X'), 'Z': Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ rot, verts=bm.verts)
    return obj_from_bm(name, bm, material, collection)


def side_prism(name, poly, inner_offset, outer, side, material, collection=cutters):
    """(y,z) polygon extruded across X; inner face follows the leaning body side.
    side=+1/-1: x from side*(hw(z)-inner_offset) to side*outer. side=0: symmetric slab between both inner walls."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((0.0, y, z)) for y, z in poly])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(1.0, 0, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    zs = [z for _, z in poly]
    if min(zs) < BELT_Z < max(zs):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                               plane_co=(0, 0, BELT_Z), plane_no=(0, 0, 1))
    for v in bm.verts:
        inner = hw(v.co.z) - inner_offset
        if side == 0:
            v.co.x = -inner if v.co.x < 0.5 else inner
        else:
            v.co.x = side * (inner if v.co.x < 0.5 else outer)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)


def rect(y0, y1, z0, z1):
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def inset_convex(poly, d):
    """Shrink a convex counter-clockwise (y,z) polygon by distance d."""
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))            # inward for CCW
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        p1, t1 = lines[i - 1]
        p2, t2 = lines[i]
        den = t1.x * t2.y - t1.y * t2.x
        s = ((p2 - p1).x * t2.y - (p2 - p1).y * t2.x) / den
        q = p1 + t1 * s
        out.append((q.x, q.y))
    return out


def through_prism(name, pts, direction, depth, material, collection=cutters):
    """Planar polygon pts (3D) extruded +-depth along direction (window openings)."""
    d = Vector(direction).normalized() * depth
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new(Vector(p) - d) for p in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=d * 2, verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)


def pane(name, pts, normal, material='VAN_Glass'):
    """Double-sided glass: outward quad plus an inward-facing copy 3 mm inside."""
    n = Vector(normal).normalized()
    bm = bmesh.new()
    outer = bm.faces.new([bm.verts.new(Vector(p)) for p in pts])
    inner = bm.faces.new([bm.verts.new(Vector(p) - n * 0.003) for p in reversed(pts)])
    bm.normal_update()
    if outer.normal.dot(n) < 0:
        bmesh.ops.reverse_faces(bm, faces=[outer, inner])
    return obj_from_bm(name, bm, material)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)


def boolean(target, cutter, op='DIFFERENCE'):
    m = target.modifiers.new(f'{op}_{cutter.name}', 'BOOLEAN')
    m.operation = op
    m.solver = 'EXACT'
    m.object = cutter
    m.material_mode = 'TRANSFER'
    apply_mods(target)


def join(target, parts):
    for p in parts:
        mw = target.matrix_world.inverted() @ p.matrix_world
        bm = bmesh.new()
        bm.from_mesh(p.data)
        bmesh.ops.transform(bm, matrix=mw, verts=bm.verts)
        for m in p.data.materials:
            if m.name not in [t.name for t in target.data.materials]:
                target.data.materials.append(m)
        remap = [[t.name for t in target.data.materials].index(m.name) for m in p.data.materials]
        for f in bm.faces:
            f.material_index = remap[f.material_index]
        tmp = bpy.data.meshes.new('tmp')
        bm.to_mesh(tmp)
        bm.free()
        tb = bmesh.new()
        tb.from_mesh(target.data)
        tb.from_mesh(tmp)
        tb.to_mesh(target.data)
        tb.free()
        bpy.data.meshes.remove(tmp)
        bpy.data.objects.remove(p)


def set_origin(ob, point):
    point = Vector(point)
    ob.data.transform(Matrix.Translation(-point))
    ob.location = point


def profile_solid(name, profile, inset, material, collection):
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((-1.0, y, z)) for y, z in profile])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(2.0, 0, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6, plane_co=(0, 0, BELT_Z), plane_no=(0, 0, 1))
    for v in bm.verts:
        v.co.x = math.copysign(hw(v.co.z) - inset, v.co.x)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, material, collection)

# ---------------------------------------------------------------- outer shell
body = profile_solid('VAN_Body', SIDE_PROFILE, 0.0, 'VAN_Body_Cream', col)
bev = body.modifiers.new('Chamfer', 'BEVEL')
bev.width = G['BEVEL']
bev.segments = 1
bev.limit_method = 'ANGLE'
bev.angle_limit = math.radians(30)
bev.use_clamp_overlap = True
apply_mods(body)

ARCH_R, ARCH_D, ARCH_X = G['ARCH']
for i, y in enumerate(AXLES):                      # wheel arches, per side so the cab is not tunnelled
    for s in (1, -1):
        boolean(body, cyl(f'Cut_Arch_{i}_{s}', ARCH_R, ARCH_D, Vector((s * ARCH_X, y, WHEEL_R)), 'X', 'VAN_Trim_Dark', 16, cutters))
CX0, CX1, CY0, CY1, CZ = G['CREASE']
for s in (1, -1):                                   # side crease line
    boolean(body, box(f'Cut_Crease_{s}', s * CX0, s * CX1, CY0, CY1, CZ - 0.006, CZ + 0.006, 'VAN_Body_Crease', cutters))

# one hollow space for cab and cargo, with wheel housings
cavity = profile_solid('Cut_Cavity', CAVITY_PROFILE, WALL, 'VAN_Interior', cutters)
HOUSE_R, HOUSE_D, HOUSE_X = G['HOUSING']
for i, y in enumerate(AXLES):
    for s in (1, -1):
        boolean(cavity, cyl(f'Cut_Housing_{i}_{s}', HOUSE_R, HOUSE_D, Vector((s * HOUSE_X, y, WHEEL_R)), 'X', 'VAN_Interior', 16, cutters))
boolean(body, cavity)

# windshield opening (on the windshield line; 45 degrees on v02 / v03, a little steeper on the stretched v04)
WS_Y, WS_ZTOP = G['WS_TOP']
WS_YB, WS_ZB = G['WS_BOTTOM']
n_ws = Vector((0, -(WS_ZTOP - WS_ZB), WS_Y - WS_YB)).normalized()
ws_k = (WS_Y - WS_YB) / (WS_ZTOP - WS_ZB)
ws_pts = []
for z, sgn in ((G['WS_Z'][0], 1), (G['WS_Z'][0], -1), (G['WS_Z'][1], -1), (G['WS_Z'][1], 1)):
    y = WS_Y - (WS_ZTOP - z) * ws_k
    ws_pts.append(Vector((sgn * (hw(z) - G.get('WS_INSET', 0.08)), y, z)))
boolean(body, through_prism('Cut_Windshield', ws_pts, n_ws, 0.2, 'VAN_Trim_Dark'))

# ---------------------------------------------------------------- doors cut from the shell
doors = {}
specs = [
    ('VAN_Door_Front_Left', FRONT_DOOR_POLY, 1),
    ('VAN_Door_Front_Right', FRONT_DOOR_POLY, -1),
    ('VAN_Door_Slide', rect(*SLIDE_RECT), -1),
]
for name, poly, s in specs:
    hole = side_prism('Cut_Hole_' + name, poly, WALL + 0.006, G['HOLE_OUT'], s, 'VAN_Interior')
    keep = side_prism('Keep_' + name, inset_convex(poly, GAP), WALL + 0.006, G['HOLE_OUT'], s, 'VAN_Interior')
    door = body.copy(); door.data = body.data.copy(); door.name = name; col.objects.link(door)
    boolean(door, keep, 'INTERSECT')
    doors[name] = (door, hole)
for name, x0, x1 in (('VAN_Door_Rear_Left', 0.0, REAR_DOOR_W), ('VAN_Door_Rear_Right', -REAR_DOOR_W, 0.0)):
    z0, z1 = REAR_DOOR_Z
    hole = box('Cut_Hole_' + name, x0, x1, REAR_Y - 0.09, REAR_Y + 0.3, z0, z1, 'VAN_Interior', cutters)
    sx0 = x0 + (GAP if x0 != 0 else GAP / 2)
    sx1 = x1 - (GAP if x1 != 0 else GAP / 2)
    keep = box('Keep_' + name, sx0, sx1, REAR_Y - 0.09, REAR_Y + 0.3, z0 + GAP, z1 - GAP, 'VAN_Interior', cutters)
    door = body.copy(); door.data = body.data.copy(); door.name = name; col.objects.link(door)
    boolean(door, keep, 'INTERSECT')
    doors[name] = (door, hole)
for name, (door, hole) in doors.items():
    boolean(body, hole)
fl, fr = doors['VAN_Door_Front_Left'][0], doors['VAN_Door_Front_Right'][0]
slide = doors['VAN_Door_Slide'][0]
rl, rr = doors['VAN_Door_Rear_Left'][0], doors['VAN_Door_Rear_Right'][0]

# cab door windows: opening + glass, mirror and handle travel with the door
AX1, AY0, AY1, AZ0, AZ1 = G['MIRROR_ARM']
MX0, MX1, MY0, MY1, MZ0, MZ1 = G['MIRROR']
HX0, HX1, HY0, HY1, HZ0, HZ1 = G['HANDLE_FRONT']
for door, s in ((fl, 1), (fr, -1)):
    win = [Vector((s * hw(z), y, z)) for y, z in inset_convex(CAB_WINDOW, 0.0)]
    boolean(door, through_prism(f'Cut_CabWin_{s}', win, (s, 0, 0), 0.25, 'VAN_Trim_Dark'))
    glass = pane(f'Glass_Cab_{s}', [Vector((s * (hw(z) + 0.004), y, z)) for y, z in inset_convex(CAB_WINDOW, -0.02)], (s, 0, 0))
    join(door, [glass,
                box(f'MirrorArm_{s}', s * (hw(G['MIRROR_ARM_HW_Z']) - 0.02), s * AX1, AY0, AY1, AZ0, AZ1, 'VAN_Trim_Dark'),
                box(f'Mirror_{s}', s * MX0, s * MX1, MY0, MY1, MZ0, MZ1, 'VAN_Trim_Dark'),
                box(f'Handle_Front_{s}', s * HX0, s * HX1, HY0, HY1, HZ0, HZ1, 'VAN_Trim_Dark')])

join(slide, [box('Handle_Slide', *G['HANDLE_SLIDE'], 'VAN_Trim_Dark')])
RWX0, RWX1, RWZ0, RWZ1 = G['REAR_WIN']
RGX0, RGX1, RGZ0, RGZ1 = G['REAR_GLASS']
for door, s in ((rl, 1), (rr, -1)):
    pts = [(s * RWX0, RWZ0), (s * RWX1, RWZ0), (s * RWX1, RWZ1), (s * RWX0, RWZ1)]
    boolean(door, through_prism(f'Cut_RearWin_{s}', [Vector((x, REAR_Y, z)) for x, z in pts], (0, 1, 0), 0.2, 'VAN_Trim_Dark'))
    big = [(s * RGX0, RGZ0), (s * RGX1, RGZ0), (s * RGX1, RGZ1), (s * RGX0, RGZ1)]
    join(door, [pane(f'Glass_Rear_{s}', [Vector((x, REAR_Y + 0.004, z)) for x, z in big], (0, 1, 0))])
HRX0, HRX1, HRZ0, HRZ1 = G['HANDLE_REAR']
join(rr, [box('Handle_Rear', HRX0, HRX1, REAR_Y, REAR_Y + 0.025, HRZ0, HRZ1, 'VAN_Trim_Dark')])

# ---------------------------------------------------------------- body details
details = [pane('Glass_Windshield', [p + n_ws * 0.006 + (Vector((math.copysign(0.02, p.x), 0, 0))) for p in ws_pts], n_ws)]
FW, FZ0, FZ1 = G['FASCIA']
details.append(box('Fascia', -FW, FW, FRONT_Y - 0.02, FRONT_Y + 0.02, FZ0, FZ1, 'VAN_Trim_Dark'))
GW, GZ0, GZ1 = G['GRILLE']
details.append(box('Grille', -GW, GW, FRONT_Y - 0.028, FRONT_Y, GZ0, GZ1, 'VAN_Grille_Black'))
SW_HALF, SLAT_ZS, SLAT_H = G['SLATS']
for z in SLAT_ZS:
    details.append(box(f'Slat_{z}', -SW_HALF, SW_HALF, FRONT_Y - 0.036, FRONT_Y - 0.02, z - SLAT_H, z + SLAT_H, 'VAN_Trim_Dark'))
HL_R, HL_X, HL_Z = G['HEADLIGHT']
IX0, IX1, IZ0, IZ1 = G['INDICATOR']
TX0, TX1, TAIL_BANDS = G['TAILS']
for s in (1, -1):
    details.append(cyl(f'Headlight_{s}', HL_R, 0.03, Vector((s * HL_X, FRONT_Y - 0.03, HL_Z)), 'Y', 'VAN_Light_White', 16))
    details.append(box(f'Indicator_{s}', s * IX0, s * IX1, FRONT_Y - 0.012, FRONT_Y + 0.01, IZ0, IZ1, 'VAN_Indicator_Orange'))
    for z0, z1, m in TAIL_BANDS:
        details.append(box(f'Tail_{s}_{z0}', s * TX0, s * TX1, REAR_Y - 0.01, REAR_Y + 0.02, z0, z1, m))
BW, BFY0, BRY1, BZ0, BZ1 = G['BUMPER']
for nm, y0, y1 in (('Bumper_Front', BFY0, FRONT_Y + 0.06), ('Bumper_Rear', REAR_Y - 0.06, BRY1)):
    b = box(nm, -BW, BW, y0, y1, BZ0, BZ1, 'VAN_Trim_Dark')
    m = b.modifiers.new('Chamfer', 'BEVEL'); m.width = 0.03; m.segments = 1
    apply_mods(b)
    details.append(b)
details.append(box('Rail_Slide', *G['RAIL'], 'VAN_Trim_Dark'))
# cab interior: seats (v02: driver seat left + two-seat bench right; v03: one joined bench), dashboard, steering column
SEAT_Y0, SEAT_Y1, SEAT_Y2 = G['SEAT_Y']
SEAT_TOP, BACK_TOP = G['SEAT_Z']
for nm, x0, x1 in G['SEATS']:
    details.append(box(nm + '_Base', x0, x1, SEAT_Y0, SEAT_Y1, FLOOR_Z, SEAT_TOP, 'VAN_Seat'))
    details.append(box(nm + '_Back', x0, x1, SEAT_Y1, SEAT_Y2, SEAT_TOP, BACK_TOP, 'VAN_Seat'))
DY0, DY1, DZ0, DZ1, DZW = G['DASH']
dash_w = hw(DZW) - WALL - 0.01
details.append(box('Dashboard', -dash_w, dash_w, DY0, DY1, DZ0, DZ1, M_DASH))
details.append(box('SteeringColumn', *G['COLUMN'], M_DASH))


def soft_box(name, x0, x1, y0, y1, z0, z1, material, width=0.035, segments=2):
    """Box with rounded (bevelled) edges: seat cushions, backrests, headrests, the instrument hood."""
    b = box(name, x0, x1, y0, y1, z0, z1, material)
    m = b.modifiers.new('Round', 'BEVEL'); m.width = width; m.segments = segments; m.use_clamp_overlap = True
    apply_mods(b)
    return b


if G.get('BENCH'):
    # v04 bench: three seats joined into one bench (no passage), each a cushion, a backrest and a headrest on two posts,
    # on one dark pedestal across the cab. v05: two identical separate seats, each on its own pedestal.
    in_w = HALF_W - WALL
    separate = G.get('SEPARATE_SEATS', False)
    if not separate:
        details.append(box('Bench_Pedestal', -in_w + 0.04, in_w - 0.04, SEAT_Y0 + 0.06, SEAT_Y1 - 0.02, FLOOR_Z, SEAT_TOP - 0.10, 'VAN_Seat'))
    for i, (x0, x1) in enumerate(G['BENCH']):
        cx = (x0 + x1) / 2
        if separate:
            details.append(box(f'Seat_Pedestal_{i}', x0 + 0.07, x1 - 0.07, SEAT_Y0 + 0.06, SEAT_Y1 - 0.02, FLOOR_Z, SEAT_TOP - 0.10, 'VAN_Seat'))
        details.append(soft_box(f'Bench_Cushion_{i}', x0, x1, SEAT_Y0, SEAT_Y1 + 0.03, SEAT_TOP - 0.13, SEAT_TOP, 'VAN_Seat_Fabric', 0.045))
        details.append(soft_box(f'Bench_Back_{i}', x0, x1, SEAT_Y1, SEAT_Y2, SEAT_TOP - 0.04, BACK_TOP, 'VAN_Seat_Fabric', 0.045))
        hw_head = 0.14 if (i == 0 or separate) else 0.12
        details.append(soft_box(f'Bench_Headrest_{i}', cx - hw_head, cx + hw_head, SEAT_Y1 + 0.015, SEAT_Y2 - 0.015,
                                BACK_TOP + 0.07, BACK_TOP + 0.25, 'VAN_Seat_Fabric', 0.035))
        for px in (-0.075, 0.075):
            details.append(box(f'Bench_HeadPost_{i}_{px}', cx + px - 0.009, cx + px + 0.009, SEAT_Y1 + 0.06, SEAT_Y1 + 0.078,
                               BACK_TOP - 0.03, BACK_TOP + 0.09, 'VAN_Interior_Black'))
    # dashboard: instrument hood over the gauges in front of the driver, two vents in the middle, a glovebox lid
    ex = DRIVER_EYE[0]
    details.append(soft_box('Dash_InstrumentHood', ex - 0.25, ex + 0.25, DY1 - 0.18, DY1 + 0.05, DZ1 - 0.03, DZ1 + 0.09, M_DASH, 0.03))
    details.append(box('Dash_Gauges', ex - 0.20, ex + 0.20, DY1 - 0.002, DY1 + 0.010, DZ1 - 0.14, DZ1 - 0.02, M_IBLACK))
    for vx in (-0.17, 0.03):
        details.append(box(f'Dash_Vent_{vx}', vx, vx + 0.14, DY1 - 0.002, DY1 + 0.012, DZ1 - 0.13, DZ1 - 0.05, M_IBLACK))
    details.append(box('Dash_Glovebox', -dash_w + 0.12, -0.30, DY1 - 0.002, DY1 + 0.010, DZ0 + 0.13, DZ1 - 0.15, 'VAN_Seat'))

# cab / cargo partition (v03): full height, see-through bar grille in dark metal; no gap a person could pass
PART = G['PARTITION']
partition_info = None
if PART:
    py0, py1, F, bar = PART['y0'], PART['y1'], PART['frame'], PART['bar']
    roof_in = CAVITY_PROFILE[1][1]
    xi = lambda z: hw(z) - WALL                      # inner wall face at height z
    pm = (py0 + py1) / 2
    details.append(box('Partition_Bottom', -xi(FLOOR_Z), xi(FLOOR_Z), py0, py1, FLOOR_Z, FLOOR_Z + F, 'VAN_Trim_Dark'))
    details.append(box('Partition_Top', -xi(roof_in), xi(roof_in), py0, py1, roof_in - F, roof_in, 'VAN_Trim_Dark'))
    for s in (1, -1):
        details.append(beam(f'Partition_Post_Low_{s}', (s * (xi(FLOOR_Z) - F / 2), FLOOR_Z), (s * (xi(BELT_Z) - F / 2), BELT_Z + F / 2),
                            F, py0, py1, 'VAN_Trim_Dark'))
        details.append(beam(f'Partition_Post_High_{s}', (s * (xi(BELT_Z) - F / 2), BELT_Z - F / 2), (s * (xi(roof_in) - F / 2), roof_in),
                            F, py0, py1, 'VAN_Trim_Dark'))
    bars_x = []
    x = -PART['bar_x']
    while x <= PART['bar_x'] + 1e-6:
        bars_x.append(round(x, 4))
        details.append(box(f'Partition_Bar_{len(bars_x)}', x - bar / 2, x + bar / 2, pm - bar / 2, pm + bar / 2,
                           FLOOR_Z + F, roof_in - F, 'VAN_Grille_Black'))
        x += PART['bar_step']
    for z in PART['cross_z']:
        details.append(box(f'Partition_Cross_{z}', -(xi(z) - F), xi(z) - F, pm - bar / 2, pm + bar / 2, z - bar / 2, z + bar / 2,
                           'VAN_Grille_Black'))
    side_gap_low = (xi(FLOOR_Z) - F) - (PART['bar_x'] + bar / 2)
    side_gap_top = (xi(roof_in) - F) - (PART['bar_x'] + bar / 2)
    partition_info = {'y': [py0, py1], 'bars': len(bars_x), 'bar_clear_gap_m': round(PART['bar_step'] - bar, 3),
                      'side_gap_m_floor_roof': [round(side_gap_low, 3), round(side_gap_top, 3)],
                      'cross_bars_z': list(PART['cross_z']), 'height_m': round(roof_in - FLOOR_Z, 3)}
# bulkhead (v04): right behind the bench, between the front door and the sliding door edges; a solid panel up to the seat
# backs, a dark frame and a see-through wire mesh above it up to the roof (you see into the bay, nobody gets through)
BH = G.get('BULKHEAD')
if BH:
    by0, by1, F, wire, step = BH['y0'], BH['y1'], BH['frame'], BH['wire'], BH['step']
    roof_in = CAVITY_PROFILE[1][1]
    pt = BH['panel_top']
    xi = lambda z: hw(z) - WALL
    pm = (by0 + by1) / 2
    poly = [(-xi(FLOOR_Z), FLOOR_Z), (xi(FLOOR_Z), FLOOR_Z), (xi(BELT_Z), BELT_Z), (xi(pt), pt), (-xi(pt), pt), (-xi(BELT_Z), BELT_Z)]
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, pm - 0.012, z)) for x, z in poly])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0.024, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    details.append(obj_from_bm('Bulkhead_Panel', bm, 'VAN_Interior'))
    details.append(box('Bulkhead_Rail_Low', -xi(pt), xi(pt), by0, by1, pt - 0.01, pt + F, M_DASH))
    details.append(box('Bulkhead_Rail_Top', -xi(roof_in), xi(roof_in), by0, by1, roof_in - F, roof_in, M_DASH))
    for s in (1, -1):
        details.append(beam(f'Bulkhead_Post_{s}', (s * (xi(pt) - F / 2), pt), (s * (xi(roof_in) - F / 2), roof_in), F, by0, by1, M_DASH))
    win_x = xi(roof_in) - F
    n_v = int((2 * win_x - 0.04) // step)
    x_first = -n_v * step / 2
    for k in range(n_v + 1):
        x = x_first + k * step
        details.append(box(f'Bulkhead_Wire_V_{k}', x - wire / 2, x + wire / 2, pm - wire / 2, pm + wire / 2, pt + F - 0.005,
                           roof_in - F + 0.005, M_IBLACK))
    z = pt + F + step
    k = 0
    while z < roof_in - F - 0.03:
        details.append(box(f'Bulkhead_Wire_H_{k}', -(xi(z) - F / 2), xi(z) - F / 2, pm - wire * 0.4, pm + wire * 0.4,
                           z - wire / 2, z + wire / 2, M_IBLACK))
        z += step
        k += 1
    partition_info = {'kind': 'bulkhead', 'y': [by0, by1], 'solid_panel_top_z': pt, 'mesh_window_z': [pt + F, roof_in - F],
                      'mesh_clear_gap_m': round(step - wire, 3), 'vertical_wires': n_v + 1, 'horizontal_wires': k}
join(body, details)

# steering wheel as its own object so the game can turn it
SW_CENTER, SW_MAJOR, SW_MINOR, SW_HUB, SW_SPOKE = G['SW']
bpy.ops.mesh.primitive_torus_add(major_radius=SW_MAJOR, minor_radius=SW_MINOR, major_segments=14, minor_segments=6)
sw = bpy.context.active_object
sw.name = 'VAN_SteeringWheel'
for c in sw.users_collection:
    c.objects.unlink(sw)
col.objects.link(sw)
sw.data.materials.append(MATS[M_DASH])
hub = cyl('SW_Hub', SW_HUB, 0.03, Vector((0, 0, 0)), 'Z', M_DASH, 8)
spoke = box('SW_Spoke', -SW_SPOKE, SW_SPOKE, -0.015, 0.015, -0.01, 0.01, M_DASH)
join(sw, [hub, spoke])
SW_CENTER = Vector(SW_CENTER)
sw.data.transform(Matrix.Rotation(math.radians(-62), 4, 'X'))   # tilt the rim towards the driver
sw.location = SW_CENTER

# ---------------------------------------------------------------- pivots
set_origin(fl, (hw(0.9), G['FRONT_PIVOT_Y'], 0.40))
set_origin(fr, (-hw(0.9), G['FRONT_PIVOT_Y'], 0.40))
set_origin(slide, (-HALF_W, SLIDE_RECT[0], SLIDE_RECT[2]))
set_origin(rl, (REAR_DOOR_W, REAR_Y, REAR_DOOR_Z[0]))
set_origin(rr, (-REAR_DOOR_W, REAR_Y, REAR_DOOR_Z[0]))

# ---------------------------------------------------------------- wheels
wheels = []
for i, y in enumerate(AXLES):
    for s in (1, -1):
        nm = f"VAN_Wheel_{'Front' if i == 0 else 'Rear'}_{'Left' if s > 0 else 'Right'}"
        tire = cyl(nm, WHEEL_R, WHEEL_W, Vector((s * WHEEL_X, y, WHEEL_R)), 'X', 'VAN_Tire', 16)
        hubc = cyl(nm + '_Hub', G['HUB_R'], 0.02, Vector((s * (WHEEL_X + WHEEL_W / 2 + 0.008), y, WHEEL_R)), 'X', 'VAN_Hub_Cream', 16)
        cap = cyl(nm + '_Cap', G['CAP_R'], 0.02, Vector((s * (WHEEL_X + WHEEL_W / 2 + 0.022), y, WHEEL_R)), 'X', 'VAN_Grille_Black', 12)
        join(tire, [hubc, cap])
        set_origin(tire, (s * WHEEL_X, y, WHEEL_R))
        wheels.append(tire)

# ---------------------------------------------------------------- finish
root = bpy.data.objects.new(NAME, None)
root.empty_display_type = 'PLAIN_AXES'
col.objects.link(root)
eye = bpy.data.objects.new('SOCKET_DriverEye', None)
eye.empty_display_type = 'SPHERE'; eye.empty_display_size = 0.08
eye.location = DRIVER_EYE
col.objects.link(eye)
door_objs = [fl, fr, slide, rl, rr]
parts = [body, *door_objs, sw, *wheels]
for p in parts + [eye]:
    p.parent = root          # root sits at the world origin, so local == world placement
for p in parts:
    for poly in p.data.polygons:
        poly.use_smooth = False
    bm = bmesh.new(); bm.from_mesh(p.data)
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(p.data); bm.free()
for c in list(cutters.objects):
    bpy.data.objects.remove(c)
bpy.data.collections.remove(cutters)
for m in bpy.data.meshes:
    if m.users == 0:
        bpy.data.meshes.remove(m)

# ---------------------------------------------------------------- review animation (kept in .blend, not exported)
OPEN = {  # name: (kind, value) -- hinge angle in degrees about world Z, or slide path
    'VAN_Door_Front_Left': ('hinge', -70), 'VAN_Door_Front_Right': ('hinge', 70),
    'VAN_Door_Rear_Left': ('hinge', -100), 'VAN_Door_Rear_Right': ('hinge', 100),
    'VAN_Door_Slide': ('slide', (Vector((-0.07, 0.0, 0)), Vector((-0.07, G['SLIDE_TRAVEL'], 0)))),
}
scene.frame_start, scene.frame_end = 1, 110
for d in door_objs:
    kind, val = OPEN[d.name]
    base_loc, base_rot = d.location.copy(), d.rotation_euler.copy()
    if kind == 'hinge':
        for f, a in ((1, 0), (35, val), (70, val), (105, 0)):
            d.rotation_euler.z = math.radians(a); d.keyframe_insert('rotation_euler', index=2, frame=f)
        d.rotation_euler = base_rot
    else:
        pop, slid = val
        for f, off in ((1, Vector()), (10, pop), (35, slid), (70, slid), (95, pop), (105, Vector())):
            d.location = base_loc + off; d.keyframe_insert('location', frame=f)
        d.location = base_loc
scene.frame_set(1)

# ---------------------------------------------------------------- validation
bpy.context.view_layer.update()
report = {'asset': NAME, 'revision': REV, 'axes': 'Blender Z up, -Y forward, metres; vehicle left=+X (driver)', 'objects': {}}
total = 0
for p in parts:
    bm = bmesh.new(); bm.from_mesh(p.data)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    bb = [p.matrix_world @ Vector(c) for c in p.bound_box]
    report['objects'][p.name] = {
        'triangles': tris, 'vertices': len(p.data.vertices), 'open_edges': nonman,
        'materials': [m.name for m in p.data.materials], 'origin': [round(v, 4) for v in p.location],
        'bounds_min': [round(min(v[i] for v in bb), 4) for i in range(3)],
        'bounds_max': [round(max(v[i] for v in bb), 4) for i in range(3)]}
    total += tris
report['total_triangles'] = total
allbb = [p.matrix_world @ Vector(c) for p in parts for c in p.bound_box]
report['overall_size_m'] = [round(max(v[i] for v in allbb) - min(v[i] for v in allbb), 3) for i in range(3)]
report['sockets'] = {'SOCKET_DriverEye': list(DRIVER_EYE)}
report['door_motion_blender'] = {k: (v[0], v[1] if v[0] == 'hinge' else [list(v[1][0]), list(v[1][1])]) for k, v in OPEN.items()}
if args.revision >= 3:
    roof_in = CAVITY_PROFILE[1][1]
    housing_in = HOUSE_X - HOUSE_D / 2
    report['body_size_m'] = {'length_body': round(REAR_Y - FRONT_Y, 3), 'length_with_bumpers': round(G['BUMPER'][2] - G['BUMPER'][1], 3),
                             'width_body': round(2 * HALF_W, 3), 'width_roof': round(2 * ROOF_HALF_W, 3), 'height': ROOF_Z,
                             'wheelbase': round(AXLES[1] - AXLES[0], 3), 'wheel_radius': WHEEL_R}
    report['interior_m'] = {
        'front_seats': 'two separate, identical (mirrored)' if G.get('SEPARATE_SEATS') else ('bench' if G.get('BENCH') else 'seats'),
        'floor_z': FLOOR_Z, 'roof_inner_z': roof_in, 'height_floor_to_roof': round(roof_in - FLOOR_Z, 3),
        'width_at_floor': round(2 * (hw(FLOOR_Z) - WALL), 3), 'width_at_belt': round(2 * (hw(BELT_Z) - WALL), 3),
        'width_at_roof': round(2 * (hw(roof_in) - WALL), 3),
        'width_between_rear_housings': round(2 * housing_in, 3), 'housing_top_z': round(WHEEL_R + HOUSE_R, 3),
        'bay_length_partition_to_rear_wall': round(CAVITY_PROFILE[0][0] - partition_info['y'][1], 3),
        'slide_opening_y_z': [SLIDE_RECT[0], SLIDE_RECT[1], SLIDE_RECT[2], SLIDE_RECT[3]],
        'slide_clear_opening_when_open_m': round(G['SLIDE_TRAVEL'], 3),
        'slide_clear_height_from_floor': round(SLIDE_RECT[3] - FLOOR_Z, 3),
        'rear_opening_width': round(2 * REAR_DOOR_W, 3), 'rear_opening_z': list(REAR_DOOR_Z),
        'rear_clear_height_from_bumper_top': round(REAR_DOOR_Z[1] - REAR_DOOR_Z[0], 3),
        'cab_door_top_z': FRONT_DOOR_POLY[2][1], 'partition': partition_info,
        'front_bench': {'x': ([G['SEATS'][0][1], G['SEATS'][0][2]] if G['SEATS'] else [G['BENCH'][-1][0], G['BENCH'][0][1]]),
                        'seat_top_z': SEAT_TOP, 'back_top_z': BACK_TOP}}
report['note'] = 'Glass panes are intentionally open double-sided quads (open_edges). Door motions are review keyframes only; the FBX is exported closed and without animation.'

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
bpy.ops.object.select_all(action='DESELECT')
for o in [root, eye, *parts]:
    o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'EMPTY', 'MESH'},
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                         mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('[VAN] triangles', total, 'size', report['overall_size_m'])
for k, v in report['objects'].items():
    print('[VAN]', k, v['triangles'], 'open_edges', v['open_edges'])
if 'interior_m' in report:
    print('[VAN] interior', json.dumps(report['interior_m']))

if args.no_render:
    sys.exit(0)

# ---------------------------------------------------------------- review renders (not part of the FBX)
preview_dir.mkdir(parents=True, exist_ok=True)
studio = bpy.data.collections.new('Studio_NotExported'); scene.collection.children.link(studio)
world = bpy.data.worlds.new('Studio'); scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = srgb((70, 76, 84)); bg.inputs[1].default_value = 0.9


def light(name, loc, power, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size
    o = bpy.data.objects.new(name, d); o.location = loc
    o.rotation_euler = (Vector((0, 0, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    studio.objects.link(o)


light('Key', (-6, -7, 8), 2600, 6)
light('Fill', (7, 5, 5), 1100, 6)
light('Rim', (0, 9, 6), 700, 5)
fm = bpy.data.materials.new('Floor')
try:
    fm.use_nodes = True
except Exception:
    pass
fb = next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
fb.inputs['Base Color'].default_value = srgb((70, 76, 84)); fb.inputs['Roughness'].default_value = 1
bpy.ops.mesh.primitive_plane_add(size=60)
floor = bpy.context.active_object; floor.data.materials.append(fm)
for c in floor.users_collection:
    c.objects.unlink(floor)
studio.objects.link(floor)

# v03 scale reference (renders only): a plain 1.80 m figure standing on the cargo floor behind the partition
figure = None
if args.revision >= 3:
    mat('REVIEW_Figure', (214, 120, 60))
    fx, fy = -0.35, 0.30
    figure = cyl('REVIEW_Figure_1m80', 0.17, 1.56, Vector((fx, fy, FLOOR_Z + 0.78)), 'Z', 'REVIEW_Figure', 16, studio)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(fx, fy, FLOOR_Z + 1.68), segments=16, ring_count=8)
    head = bpy.context.active_object
    head.data.materials.append(MATS['REVIEW_Figure'])
    for c in head.users_collection:
        c.objects.unlink(head)
    studio.objects.link(head)
    join(figure, [head])

scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dev
            prefs.get_devices()
            if any(d.type == dev for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = 'GPU'
                break
        except Exception:
            continue
except Exception:
    pass
scene.render.resolution_x, scene.render.resolution_y = 1448, 1086
scene.view_settings.view_transform = 'Standard'
cd = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cd); studio.objects.link(cam); scene.camera = cam
R = G['RENDER']
K, TZ = R['scale'], R['target_z']


def render(fname, loc, target=(0, 0, 1.05), ortho=None, lens=50, frame=1, show_figure=False):
    scene.frame_set(frame)
    if figure is not None:
        figure.hide_render = not show_figure
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.type = 'PERSP'; cd.lens = lens
    cd.clip_start = 0.05
    scene.render.filepath = str(preview_dir / fname)
    bpy.ops.render.render(write_still=True)


if args.revision >= 4:
    # quick check set (Vadim wants v04 fast): 3/4 front-right, v02 next to it at the same scale, the driver looking back
    render('05_three_quarter_right.png', (-6.8 * K, -7.8 * K, 3.2 * K), target=(0, 0, 0.95 * K), lens=45)
    v02_blend = HERE / f'{NAME}_v02.blend'
    if v02_blend.exists():
        with bpy.data.libraries.load(str(v02_blend)) as (src, dst):
            dst.objects = [n for n in src.objects]
        cmp = bpy.data.collections.new('Compare_v02_NotExported'); scene.collection.children.link(cmp)
        cam_dir = Vector((6.8, 7.8, 0)).normalized()
        right = Vector((cam_dir.y, -cam_dir.x, 0))
        offset = right * (5.4 if args.revision == 4 else 6.0)
        for o in dst.objects:
            if o is None:
                continue
            cmp.objects.link(o)
            o.animation_data_clear()
            if o.parent is None:
                o.location = offset
        mid = offset / 2 + Vector((0, 0, 1.0))
        render(f'14_compare_v02_right_{REV}_left.png', tuple(mid + Vector((-11.0, -12.6, 5.2))), target=tuple(mid), lens=45)
        if args.revision >= 5:
            # side by side from the right, orthographic, same scale: v02 in front, this revision behind it
            v02_y = G['BUMPER'][1] - 0.8 - V02['BUMPER'][2]
            for o in dst.objects:
                if o is not None and o.parent is None:
                    o.location = (0, v02_y, 0)
            cy = (v02_y + V02['BUMPER'][1] + G['BUMPER'][2]) / 2
            render(f'15_side_compare_v02_front_{REV}_back.png', (-20, cy, 1.3), target=(0, cy, 1.3), ortho=13.2)
        for o in list(cmp.objects):
            o.hide_render = True
    if args.revision >= 5:
        render('03_right.png', (-14 * K, 0, TZ), target=(0, 0, TZ), ortho=R['ortho_side'])
    render('12_driver_look_back.png', (DRIVER_EYE[0] - 0.13, DRIVER_EYE[1] - 0.22, DRIVER_EYE[2] + 0.08),
           target=(-0.25, 2.4, 1.45), lens=18, frame=50, show_figure=True)
    render('11_interior_from_rear.png', (0, REAR_Y + 1.0, 1.85), target=(0, -1.2, 1.55), lens=18, frame=50, show_figure=True)
else:
    render('01_front.png', (0, -14 * K, TZ), target=(0, 0, TZ), ortho=R['ortho_front'])
    render('02_left.png', (14 * K, 0, TZ), target=(0, 0, TZ), ortho=R['ortho_side'])
    render('03_right.png', (-14 * K, 0, TZ), target=(0, 0, TZ), ortho=R['ortho_side'])
    render('04_back.png', (0, 14 * K, TZ), target=(0, 0, TZ), ortho=R['ortho_front'])
    render('05_three_quarter_right.png', (-6.8 * K, -7.8 * K, 3.2 * K), target=(0, 0, 0.95 * K), lens=45)
    render('06_three_quarter_left.png', (6.8 * K, -7.8 * K, 3.2 * K), target=(0, 0, 0.95 * K), lens=45)
    render('07_open_rear.png', (-5.5 * K, 9.0 * K, 3.4 * K), target=(0, 0.8 * K, 0.95 * K), lens=40, frame=50, show_figure=True)
    render('08_open_right.png', (-8.5 * K, -3.0 * K, 2.8 * K), target=(0, -0.2 * K, 0.95 * K), lens=40, frame=50, show_figure=True)
    render('09_open_left.png', (8.0 * K, -5.0 * K, 2.8 * K), target=(0, -0.6 * K, 0.95 * K), lens=40, frame=50, show_figure=True)
    render('10_driver_view.png', (DRIVER_EYE[0], DRIVER_EYE[1], DRIVER_EYE[2]), target=(DRIVER_EYE[0], -6, DRIVER_EYE[2] - 0.35), lens=20)
    if args.revision >= 3:
        # interior: from the open rear doors forward to the grille; the driver looking back through it; a standing player's eye
        render('11_interior_from_rear.png', (0, REAR_Y + 1.0, 1.75), target=(0, -1.2, 1.45), lens=18, frame=50, show_figure=True)
        render('12_driver_look_back.png', (DRIVER_EYE[0] - 0.13, DRIVER_EYE[1] - 0.22, DRIVER_EYE[2] + 0.08),
               target=(-0.15, 2.4, 1.30), lens=18, frame=50, show_figure=True)
        render('13_bay_standing_eye.png', (0.25, 1.9, FLOOR_Z + 1.65), target=(0.0, -1.6, 1.55), lens=18, frame=50, show_figure=True)
print('[VAN] previews in', preview_dir)
