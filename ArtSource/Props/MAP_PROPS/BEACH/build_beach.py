"""MAP-BEACH-001 - beach props (bpy 5.0.1 / Blender 5.x, background).

  * BC_SunLounger        - wooden slat lounger on a metal frame, backrest raised (the backrest is a child: pivot on its hinge)
  * BC_Umbrella_Red      - beach umbrella, red/white canopy on a concrete foot
  * BC_Umbrella_Teal     - the same in teal/white
  * BC_LifeguardTower    - wooden lifeguard tower: splayed legs, deck with a red/white booth, ladder, flag, life ring
Run:  python3 build_beach.py -- [--revision N] [--no-render] [--force] [--samples N]
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp
from mapprops import T, R

fam = mp.Family('MAP-BEACH-001', __file__, prefix='BC_', tri_budget_default=1200,
                description='Beach props: sun lounger, umbrellas, lifeguard tower.')


def torus(m, R0, r, segs, sides, mfn, M):
    v, f, mats = [], [], []
    for i in range(segs):
        a = math.tau * i / segs
        for j in range(sides):
            b = math.tau * j / sides
            rr = R0 + r * math.cos(b)
            v.append((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))
    for i in range(segs):
        for j in range(sides):
            i1, j1 = (i + 1) % segs, (j + 1) % sides
            f.append((i * sides + j, i1 * sides + j, i1 * sides + j1, i * sides + j1))
            mats.append(mfn(i))
    m._shell(v, f, mats, M)


# =============================================================== sun lounger
LL, LWID, SEAT_Z = 1.95, 0.66, 0.36
BACK_L, BACK_DEG = 0.70, 42
m = mp.Mesh()
for sx in (-1, 1):
    m.box(0.04, LL, 0.05, 'MP_Metal_Grey', at=(sx * (LWID / 2 - 0.02), 0, SEAT_Z - 0.05), base=True)        # side rails
    for y in (-LL / 2 + 0.12, LL / 2 - 0.12):
        m.box(0.04, 0.04, SEAT_Z - 0.05, 'MP_Metal_Grey', at=(sx * (LWID / 2 - 0.02), y, 0), base=True)      # legs
m.box(LWID, 0.04, 0.04, 'MP_Metal_Grey', at=(0, LL / 2 - 0.12, 0.10), base=True)                               # foot bar
seat_y0, seat_y1 = -LL / 2 + BACK_L + 0.02, LL / 2
n = 10
for i in range(n):
    y = seat_y0 + (seat_y1 - seat_y0) * (i + 0.5) / n
    m.box(LWID - 0.02, (seat_y1 - seat_y0) / n - 0.025, 0.025, 'MP_Wood', at=(0, y, SEAT_Z), base=True)
# backrest prop strut
m.cyl_between((-(LWID / 2 - 0.08), -LL / 2 + 0.55, SEAT_Z), (-(LWID / 2 - 0.08), -LL / 2 + 0.38, SEAT_Z + 0.32), 0.015, 4, 'MP_Metal_Grey')
m.cyl_between(((LWID / 2 - 0.08), -LL / 2 + 0.55, SEAT_Z), ((LWID / 2 - 0.08), -LL / 2 + 0.38, SEAT_Z + 0.32), 0.015, 4, 'MP_Metal_Grey')
bm_ = mp.Mesh()
hinge_y = -LL / 2 + BACK_L
for sx in (-1, 1):
    bm_.box(0.04, BACK_L, 0.04, 'MP_Metal_Grey', at=(sx * (LWID / 2 - 0.06), hinge_y - BACK_L / 2, SEAT_Z + 0.01), base=True)
for i in range(6):
    y = hinge_y - BACK_L * (i + 0.5) / 6
    bm_.box(LWID - 0.06, BACK_L / 6 - 0.025, 0.025, 'MP_Wood', at=(0, y, SEAT_Z + 0.04), base=True)
# raise: rotate the backrest about the hinge line (X axis at hinge_y, SEAT_Z)
rot = T(0, hinge_y, SEAT_Z) @ R(-BACK_DEG, 'X') @ T(0, -hinge_y, -SEAT_Z)
bm_.verts = [tuple(rot @ mp.Vector(p)) for p in bm_.verts]
root = fam.make_object('BC_SunLounger', m)
back = fam.make_object('BC_SunLounger_Back', bm_, parent=root, pivot=(0, hinge_y, SEAT_Z))
fam.add_asset('BC_SunLounger', [root, back], budget=600, row=0, size_note='1.95 x 0.66 m',
              notes=f'Backrest raised {BACK_DEG} deg; its pivot is on the hinge (rotate about local X to fold flat).')


# =============================================================== umbrellas
def umbrella(name, col_a, col_b):
    m = mp.Mesh()
    m.lathe([(0.30, 0.0), (0.30, 0.10), (0.20, 0.16), (0.0, 0.17)], 8, 'MP_Concrete', offset=math.pi / 8)       # foot
    m.cyl(0.025, 2.35, 6, 'MP_White', at=(0, 0, 0.12))
    m.cyl(0.035, 0.10, 6, 'MP_Metal_Grey', at=(0, 0, 1.15))                                                   # tilt joint
    top, rim, RAD = 2.42, 2.02, 1.15
    seg = 8
    m.lathe([(0.0, top + 0.06), (0.06, top + 0.05), (RAD, rim), (RAD * 0.97, rim - 0.04), (0.0, top - 0.04)], seg, col_a,
            offset=0.0, mfn=lambda b, k: col_a if k % 2 == 0 else col_b)
    # scalloped valance: short flaps under the rim edges
    for k in range(seg):
        a0, a1 = math.tau * k / seg, math.tau * (k + 1) / seg
        am = (a0 + a1) / 2
        rr = RAD * math.cos(math.pi / seg) - 0.01
        w = 2 * RAD * math.sin(math.pi / seg) * 0.94
        m.box(w, 0.012, 0.12, col_b if k % 2 == 0 else col_a, M=T(rr * math.cos(am), rr * math.sin(am), rim - 0.07) @ R(math.degrees(am) + 90, 'Z'))
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.0, 0.08)], 6, col_b, M=T(0, 0, top + 0.06))                           # finial
    root = fam.make_object(name, m)
    fam.add_asset(name, [root], budget=500, row=0, notes='Canopy diameter 2.3 m, height 2.5 m.')


umbrella('BC_Umbrella_Red', 'MP_Red', 'MP_Fabric_Stripe')
umbrella('BC_Umbrella_Teal', 'MP_Teal', 'MP_Fabric_Stripe')

# =============================================================== lifeguard tower
m = mp.Mesh()
DECK_Z = 2.2
DW, DD = 2.2, 2.2
leg_top = 0.85
for sx in (-1, 1):
    for sy in (-1, 1):
        m.lathe([(0.24, 0.0), (0.2, 0.16), (0.0, 0.18)], 6, 'MP_Concrete', M=T(sx * 1.25, sy * 1.25, 0))     # footings
        m.cyl_between((sx * 1.25, sy * 1.25, 0.10), (sx * leg_top, sy * leg_top, DECK_Z), 0.07, 6, 'MP_White')
# cross braces (two levels) on each side
for z0, z1, t0, t1 in ((0.3, 1.25, 1.21, 1.04),):
    for sx, sy, ex, ey in ((-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)):
        m.cyl_between((sx * t0, sy * t0, z0), (ex * t1, ey * t1, z1), 0.035, 4, 'MP_Wood')
        m.cyl_between((ex * t0, ey * t0, z0), (sx * t1, sy * t1, z1), 0.035, 4, 'MP_Wood')
# deck
m.box(DW, DD, 0.10, 'MP_Wood', at=(0, 0, DECK_Z), base=True)
m.box(DW + 0.06, DD + 0.06, 0.06, 'MP_Wood_Dark', at=(0, 0, DECK_Z - 0.06), base=True)
# booth: four corner posts, red/white half walls on three sides (back +Y and both sides), open front (-Y) with a rail
BZ = DECK_Z + 0.10
for sx in (-1, 1):
    for sy in (-1, 1):
        m.box(0.09, 0.09, 1.9, 'MP_White', at=(sx * (DW / 2 - 0.05), sy * (DD / 2 - 0.05), BZ), base=True)
for i in range(4):
    colour = 'MP_Red' if i % 2 == 0 else 'MP_White'
    z = BZ + 0.05 + i * 0.22
    m.box(DW - 0.1, 0.04, 0.2, colour, at=(0, DD / 2 - 0.05, z), base=True)                              # back
    for sx in (-1, 1):
        m.box(0.04, DD - 0.1, 0.2, colour, at=(sx * (DW / 2 - 0.05), 0, z), base=True)                  # sides
m.box(DW - 0.1, 0.06, 0.06, 'MP_White', at=(0, -DD / 2 + 0.05, BZ + 0.95), base=True)                   # front rail
m.box(0.06, 0.06, 0.95, 'MP_White', at=(0.45, -DD / 2 + 0.05, BZ), base=True)
# roof: low pyramid in red with white rim
RZ = BZ + 1.9
m.box(DW + 0.3, DD + 0.3, 0.08, 'MP_White', at=(0, 0, RZ), base=True)
m.lathe([(0.0, 0.0), ((DW + 0.3) / 2 * math.sqrt(2) - 0.02, 0.0), (0.0, 0.7)], 4, 'MP_Red', M=T(0, 0, RZ + 0.08), offset=math.pi / 4)
# flag pole + flag on the roof apex
m.cyl(0.025, 1.4, 5, 'MP_White', at=(0, 0, RZ + 0.6))
m.box(0.6, 0.02, 0.38, 'MP_White', at=(0.32, 0, RZ + 1.75))                                            # white flag, red cross
m.box(0.30, 0.026, 0.08, 'MP_Red', at=(0.32, 0, RZ + 1.75))
m.box(0.08, 0.032, 0.28, 'MP_Red', at=(0.32, 0, RZ + 1.75))
# ladder at the front-left going down to the sand
lx0, lx1 = -0.75, -0.25
ly_top, ly_bot = -DD / 2 - 0.02, -DD / 2 - 1.15
for x in (lx0, lx1):
    m.cyl_between((x, ly_bot, 0.03), (x, ly_top, DECK_Z + 0.08), 0.04, 4, 'MP_Wood_Dark')
for i in range(7):
    t = (i + 0.7) / 7.8
    y = ly_bot + (ly_top - ly_bot) * t
    z = (DECK_Z + 0.08) * t
    m.box(lx1 - lx0, 0.10, 0.04, 'MP_Wood', at=((lx0 + lx1) / 2, y, z))
# life ring hanging on the front-right post
torus(m, 0.30, 0.075, 12, 6, lambda i: 'MP_Red' if (i // 3) % 2 == 0 else 'MP_White',
      T(DW / 2 - 0.05, -DD / 2 - 0.12, BZ + 0.75) @ R(90, 'X'))
root = fam.make_object('BC_LifeguardTower', m)
fam.add_asset('BC_LifeguardTower', [root], budget=1500, row=1, deck_height_m=DECK_Z + 0.1,
              notes='Faces -Y (the sea). Ladder at the front-left, booth open to the front.')

fam.finish(lineup_gap=1.2, row_gap=1.5, render=False)
if not fam.args.no_render:
    fam.render_previews(camera=[('01_front.png', 270, 8, (1600, 1000), 50),
                                ('02_three_quarter.png', 235, 22, (1600, 1100), 50)], person_at=(-1.4, -0.4, 0))
