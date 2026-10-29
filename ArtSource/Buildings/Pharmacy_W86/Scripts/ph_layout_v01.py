"""Pharmacy_W86 v01 - parametric layout (all numbers in metres, Blender space).

Blender: Z up, street = -Y, the outer face of the storefront wall is the plane y = 0, pivot (0, 0, 0) = floor level at the
centre of the street front.  The unit runs from y = 0 (street) to y = DEPTH (courtyard).  +X is to the right when seen from
the street.  Unity local = (-x, z, -y): street side = +Z.

Command-line overrides (after `--`):  --width 11.5 --depth 12.7 --height 3.4 --rear-door-x 0.7 --rev v01 [--out DIR] --force
Valid range for the automatic layout: width 8..16 m, depth 10..16 m, height 3.0..4.2 m.
"""
import sys

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def _arg(name, default, cast=float):
    if name in ARGS:
        return cast(ARGS[ARGS.index(name) + 1])
    return default


FORCE = '--force' in ARGS
NO_RENDER = '--no-render' in ARGS
REV = _arg('--rev', 'v01', str)
OUTDIR = _arg('--out', None, str)          # optional output folder (default: ArtSource/Buildings/Pharmacy_W86)

# ---------------------------------------------------------------- footprint (site: Rough 04-H3 ground-floor west unit)
W = _arg('--width', 11.5)          # street frontage (x)
D = _arg('--depth', 12.7)          # depth street -> courtyard (y)
H = _arg('--height', 3.4)          # clear ceiling height
RDX = _arg('--rear-door-x', 0.7)   # rear door centre x (Blender +x = Unity -x; east when the unit's +Z faces south)
assert 8.0 <= W <= 16.0 and 10.0 <= D <= 16.0 and 3.0 <= H <= 4.2, 'footprint outside the supported range'

HW = W / 2.0
FT, RT, ST, PT = 0.30, 0.30, 0.20, 0.15   # front, rear, side wall, partition thickness
SLAB = 0.25                               # ceiling slab above H
FH = H + 0.40                             # top of the storefront piece (cornice top)
FOUND = -0.35                             # facade / rear wall bodies go down to this level
X0, X1 = -HW + ST, HW - ST                # interior x range
Y0, Y3 = FT, D - RT                       # interior y range
SD = round(min(5.0, max(3.6, D / 3.0)), 2)  # stockroom depth
PY1 = Y3 - SD                             # stockroom side of the partition
PY0 = PY1 - PT                            # sales side of the partition

# ---------------------------------------------------------------- storefront (reference C)
PIL = 0.45                                # end pilasters
OH = 3.05 if H >= 3.3 else H - 0.30       # storefront opening head
RZ = 0.55                                 # riser (stall board) top
SILL = 0.60                               # window board / frame bottom
FR = (0.06, 0.16)                         # storefront frame depth (y)
GY = 0.11                                 # glass plane
XW0 = -HW + PIL                           # window block left
BAY1 = HW - PIL                           # door bay right
BAY0 = BAY1 - 1.95                        # door bay left
XW1 = BAY0 - 0.22                         # window block right (pier XW1..BAY0)
NPANES = max(1, round((XW1 - XW0) / 3.0))
DOOR_W = 1.20                             # street door clear opening
DCX = 0.5 * (BAY0 + BAY1)
DO0, DO1 = DCX - DOOR_W / 2, DCX + DOOR_W / 2
DH = 2.35                                 # street door head (transom bottom)

# ---------------------------------------------------------------- sales floor (reference B)
STAFF_ZONE = 2.38                         # depth behind the counter (counter back -> partition)
CY1 = PY0 - STAFF_ZONE                    # counter back
CY0 = CY1 - 0.62                          # counter front (customer side)
FX0, FX1 = X0 + 0.03, X0 + 0.80           # display fridge (left end of the counter line)
FY0, FY1 = CY1 - 0.72, CY1
GC0 = X0 + 0.85                           # glass display counter
GT1 = X1 - 0.55                           # staff gate right edge / end cabinet left
GT0 = X1 - 1.50                           # staff gate left edge = cash desk right
CD0 = GT0 - 2.20                          # cash desk left = glass counter right
GC1 = CD0
CTOP = 1.00                               # glass counter top
DTOP = 1.05                               # cash desk top
SDW, SDH = 1.05, 2.10                     # staff door opening
SDX = X1 - 1.05
SD0, SD1 = SDX - SDW / 2, SDX + SDW / 2
REG_X = CD0 + 0.95                        # cash register / purchase point x
SHELF_D = 0.42                            # wall shelving depth
SHELF_H = 2.15
LSH = (Y0 + 0.45, CY0 - 1.30)             # left wall shelving (y range); poster + info sheet on the wall after it
RSH = (Y0 + 1.25, CY0 - 0.20)             # right wall shelving (clear of the street door swing)
BC0, BC1 = X0 + 1.15, SD0 - 0.50          # back cabinets behind the counter (x range)

# ---------------------------------------------------------------- stockroom (reference A) + rear door
RDW, RDH = 1.42, 2.25                     # rear door opening (clear 1.30 x 2.19 inside the steel frame)
RD0, RD1 = RDX - RDW / 2, RDX + RDW / 2
RW0, RW1 = X0 + 1.25, X0 + 2.25           # small barred window in the rear wall, above the shelving
RWZ = (2.20, 2.80) if H >= 3.2 else (H - 1.0, H - 0.4)
SKX = RD1 + 1.15                          # sink centre x (rear wall, right of the door)
RACK_B = (min(RD0 - 1.15, X0 + 4.4), min(RD0 - 0.60, X0 + 4.95))   # freestanding racks (run along y)
_RA1 = min(X0 + 2.80, RACK_B[0] - 1.05)   # keep >= 1.05 m between the racks
RACK_A = (_RA1 - 0.55, _RA1)
RACK_Y = (PY1 + 1.05, Y3 - 1.05)
STOCK_LW = (PY1 + 0.20, Y3 - 0.05)        # left wall shelving
STOCK_RW = (PY1 + 1.25, Y3 - 0.05)        # right wall shelving (clear of the staff door swing)
STOCK_REAR = (X0 + 0.58, X0 + 2.15)       # rear wall shelving under the window

assert CY0 - Y0 > 3.2, 'sales floor too shallow for the counter layout'
assert RD0 > RACK_B[1] + 0.5 and RD1 < X1 - 1.0, 'rear door collides with the stockroom layout'
assert CD0 - GC0 > 2.0
assert RACK_A[0] - 0.50 - (X0 + 0.53) >= 1.0 - 1e-6, 'stockroom too narrow for two racks + 1 m aisles'
