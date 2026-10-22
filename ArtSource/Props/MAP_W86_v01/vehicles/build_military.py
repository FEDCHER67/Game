"""MAP_W86_v01 vehicles - MILITARY family (Tramduro): tank, air defence, missile silo, jeep, cargo truck, helicopter,
patrol boat. Original procedural models (no third-party assets). Atlas MW86_Military_<A|B|C>.png ('@camo' = camo region).

blender -b --factory-startup -P build_military.py -- --out-root <ArtSource/Props/MAP_W86_v01/vehicles> --fbx-dir <Unity Vehicles dir>
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / '_lib'))
import mw86lib as L  # noqa: E402
from mw86lib import Mesh, T, R, octa  # noqa: E402

CAMO = '@camo'


# ---------------------------------------------------------------------------------------------- shared parts
def track_unit(m, x0, x1, y0, y1, h, wheel_n, wheel_r, col_track='ink', col_wheel='mil_dark', skirt=None):
    """Track block (side silhouette extruded x0..x1) with road-wheel discs on the outer face; optional skirt plate."""
    s = 1 if x1 > 0 else -1
    L_ = y1 - y0
    poly = [(y0 + 0.5, 0.0), (y1 - 0.5, 0.0), (y1 - 0.12, h * 0.36), (y1, h * 0.72), (y1 - 0.16, h), (y0 + 0.16, h),
            (y0, h * 0.74), (y0 + 0.14, h * 0.34)]
    m.side(poly, x0, x1, col_track, bev=0.04)
    xo = max(abs(x0), abs(x1)) * s
    for i in range(wheel_n):
        y = y0 + 0.62 + (L_ - 1.24) * i / max(1, wheel_n - 1)
        m.cyl_x(wheel_r, 0.08, m.seg(10, 6), col_wheel, at=(xo + s * 0.03, y, wheel_r + 0.05))
        if m.lod == 0:
            m.cyl_x(wheel_r * 0.38, 0.05, 6, 'ink', at=(xo + s * 0.08, y, wheel_r + 0.05))
    # drive sprocket / idler bulges
    m.cyl_x(h * 0.3, 0.1, m.seg(8, 6), col_wheel, at=(xo + s * 0.03, y1 - 0.22, h * 0.68))
    m.cyl_x(h * 0.28, 0.1, m.seg(8, 6), col_wheel, at=(xo + s * 0.03, y0 + 0.22, h * 0.68))
    if skirt:
        z0, z1, colr = skirt
        m.bb(0.06, L_ - 0.1, z1 - z0, 0.02, colr, at=(xo + s * 0.1, (y0 + y1) / 2, z0), base=True)


def glass_x(m, s, x, y0, y1, z0, z1, col='glass_dark', slope=0.0):
    """Side window plate on x = s*x (slope shifts the top edge in y)."""
    m.xplate(s, x, [(y0, z0), (y1, z0), (y1 + slope, z1), (y0 + slope, z1)], col, t=0.012)


def plain_wheel(m, x, y, r, w, rim='mil_dark', seg=12):
    return m.wheel(x, y, r, w, 'tyre', rim, seg=seg)


# ---------------------------------------------------------------------------------------------- TANK
def tank(lod):
    m = Mesh(lod)
    # lower hull between the tracks
    hull = [(-2.9, 0.35), (2.95, 0.35), (3.3, 0.72), (3.3, 1.38), (-1.55, 1.44), (-3.4, 1.06), (-3.36, 0.72)]
    m.side(hull, -1.12, 1.12, CAMO, bev=0.05)
    for s in (1, -1):
        track_unit(m, s * 1.08, s * 1.62, -3.3, 3.3, 0.98, 6, 0.33, skirt=(0.62, 1.0, CAMO))
    # fender deck over the tracks
    m.side([(-3.25, 0.98), (3.3, 0.98), (3.3, 1.08), (-3.3, 1.06)], -1.7, 1.7, CAMO, bev=0.02)
    # rear: exhaust grille + tail lights
    m.zplate(1.39, [(-0.9, 2.2), (0.9, 2.2), (0.9, 3.05), (-0.9, 3.05)], 'ink', t=0.02)
    if lod == 0:
        for x in (-0.8, -0.5, -0.2, 0.1, 0.4, 0.7):
            m.box(0.06, 0.8, 0.03, 'ink_dark', at=(x + 0.05, 2.62, 1.41))
        for s in (1, -1):
            m.bb(0.24, 0.16, 0.14, 0.02, 'ink', at=(s * 1.25, -3.18, 1.1))       # headlight boxes
            m.cyl_y(0.06, 0.04, 8, 'lamp_glow', at=(s * 1.25, -3.27, 1.17))
    # turret
    tb = [(-0.85, -1.55), (0.85, -1.55), (1.42, -0.55), (1.42, 1.15), (1.05, 1.75), (-1.05, 1.75), (-1.42, 1.15), (-1.42, -0.55)]
    tt = [(-0.62, -1.18), (0.62, -1.18), (1.12, -0.42), (1.12, 1.0), (0.85, 1.48), (-0.85, 1.48), (-1.12, 1.0), (-1.12, -0.42)]
    yo = 0.25
    m.frustum([(x, y + yo) for x, y in tb], 1.42, [(x, y + yo) for x, y in tt], 2.06, CAMO, bev=0.04)
    # mantlet + gun
    m.bb(0.86, 0.5, 0.5, 0.05, 'mil_dark', at=(0, -1.38 + yo, 1.5), base=True)
    m.cyl_y(0.11, 3.0, m.seg(10, 6), 'mil_dark', at=(0, -3.1, 1.75))
    m.cyl_y(0.165, 0.55, m.seg(10, 6), 'mil_dark', at=(0, -3.35, 1.75))
    m.cyl_y(0.135, 0.22, m.seg(10, 6), 'ink', at=(0, -4.49, 1.75))
    # commander cupola + hatch + MG, loader hatch
    m.cyl(0.38, 0.22, m.seg(10, 6), CAMO, at=(0.55, 0.65 + yo, 2.05))
    m.cyl(0.33, 0.06, m.seg(10, 6), 'mil_dark', at=(0.55, 0.65 + yo, 2.27))
    m.cyl(0.3, 0.05, m.seg(8, 6), 'mil_dark', at=(-0.55, 0.85 + yo, 2.05))
    if lod == 0:
        m.bb(0.16, 0.5, 0.16, 0.02, 'ink', at=(0.55, 0.15 + yo, 2.38), base=True)
        m.bar((0.55, -0.1 + yo, 2.46), (0.55, -0.85 + yo, 2.46), 0.035, 'ink', seg=6)
        for s in (1, -1):                                   # smoke launchers
            for k in range(3):
                m.cyl_y(0.06, 0.32, 6, 'mil_dark', at=(s * (0.95 + 0.13 * k), -1.0 + yo, 1.86 + 0.02 * k))
    # stowage basket at the turret rear
    m.bb(2.1, 0.55, 0.42, 0.04, 'mil_canvas', at=(0, 1.95 + yo, 1.5), base=True)
    if lod == 0:
        m.bb(0.9, 0.5, 0.3, 0.06, 'mil_dark', at=(-0.5, 1.95 + yo, 1.92), base=True)   # rolled tarp
    return m


# ---------------------------------------------------------------------------------------------- AIR DEFENCE
def air_defence(lod):
    m = Mesh(lod)
    hull = [(-2.55, 0.32), (2.6, 0.32), (2.9, 0.62), (2.9, 1.42), (-1.6, 1.46), (-2.95, 1.0), (-2.9, 0.66)]
    m.side(hull, -1.0, 1.0, CAMO, bev=0.05)
    for s in (1, -1):
        track_unit(m, s * 0.98, s * 1.5, -2.9, 2.9, 0.9, 5, 0.31, skirt=(0.6, 0.94, CAMO))
    m.side([(-2.85, 0.9), (2.9, 0.9), (2.9, 0.99), (-2.9, 0.98)], -1.56, 1.56, CAMO, bev=0.02)
    # driver cab at the front left
    m.bb(1.25, 1.15, 0.6, 0.06, CAMO, at=(0.52, -1.75, 1.42), base=True)
    m.yplate(-1, -2.33, [(0.05, 1.6), (1.0, 1.6), (1.0, 1.85), (0.05, 1.85)], 'glass_dark', t=0.02)
    # turntable + launcher frame
    yt = 0.55
    m.cyl(1.05, 0.28, m.seg(14, 8), 'mil_dark', at=(0, yt, 1.44))
    m.bb(1.7, 1.5, 0.35, 0.05, CAMO, at=(0, yt + 0.2, 1.72), base=True)
    for s in (1, -1):                                       # launcher arms
        m.side([(yt - 0.5, 1.98), (yt + 0.9, 1.98), (yt + 0.75, 2.3), (yt - 0.3, 2.28)], s * 0.6, s * 0.76, 'mil_dark', bev=0.02)
    # 2 x 2 canisters, elevated 18 deg, pointing forward (-Y)
    Lc = 3.1
    M = T(0, yt + 0.75, 1.92) @ R(-18, 'X')
    for ix in (-0.29, 0.29):
        for iz in (0.28, 0.82):
            m.bb(0.52, Lc, 0.52, 0.04, CAMO, M=M, at=(ix, -Lc / 2 + 0.25, iz))
            if lod == 0:
                m.box(0.38, 0.04, 0.38, 'mil_light', M=M, at=(ix, -Lc + 0.23, iz))       # canister caps
    m.box(1.2, 0.3, 1.1, 'mil_dark', M=M, at=(0, 0.25, 0.55))
    # radar: mast + tilted flat panel at the rear
    m.cyl(0.12, 0.85, m.seg(8, 6), 'mil_dark', at=(0, 2.3, 1.46))
    Mr = T(0, 2.3, 2.62) @ R(18, 'X')
    m.bb(1.7, 0.14, 1.0, 0.04, 'mil_light', M=Mr)
    if lod == 0:
        m.box(1.5, 0.03, 0.82, 'mil_dark', M=Mr, at=(0, -0.08, 0))
        m.bar((-0.7, 2.75, 1.46), (-0.7, 2.75, 2.4), 0.03, 'ink')                    # whip antenna stub
    return m


# ---------------------------------------------------------------------------------------------- MISSILE SILO
def missile_silo(lod):
    m = Mesh(lod)
    sg = m.seg(16, 10)
    # concrete collar with hazard top ring, dark shaft opening
    m.ring(1.55, 3.35, 0.0, 0.45, sg, 'silo_concrete', topfn=lambda k: 'mustard' if k % 2 == 0 else 'ink')
    m.cyl(1.56, 0.04, sg, 'ink_dark', at=(0, 0, 0.0))
    # opened hatch leaves standing up on both sides (half discs, hinged at the collar edge)
    for s in (1, -1):
        half = [(1.7 * math.cos(math.radians(a)), 1.7 * math.sin(math.radians(a))) for a in range(0, 181, 30 if lod == 0 else 45)]
        poly = [(y, z) for y, z in half]
        m.side([(y, z + 0.45) for y, z in poly], s * 2.55, s * 2.8, 'grey_dark', bev=0.03)
        if lod == 0:
            m.side([(y * 0.7, z * 0.7 + 0.45) for y, z in poly], s * 2.5, s * 2.85, 'mil_dark', bev=0.0)
        m.bb(0.35, 3.6, 0.3, 0.03, 'grey_dark', at=(s * 2.7, 0, 0.3), base=True)     # hinge beam
    # missile (body sticks out of the shaft)
    sm = m.seg(16, 10)
    prof = [(1.02, 0.02), (1.02, 1.2), (1.02, 1.6), (1.02, 7.0), (1.02, 7.4), (1.02, 8.3), (0.97, 8.85), (0.82, 9.5),
            (0.58, 10.15), (0.3, 10.65), (0.0, 11.0)]
    cols = ['missile_white', 'ink', 'missile_white', 'ink', 'missile_white', 'missile_red', 'missile_red', 'missile_red',
            'missile_red', 'missile_red']
    m.lathe(prof, sm, 'missile_white', cols=cols)
    if lod == 0:                                            # four small guide rails / fins near the shaft lip
        for a in (45, 135, 225, 315):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            p0 = (ca * 1.0, sa * 1.0, 0.5)
            m.beam(p0, (ca * 1.45, sa * 1.45, 0.5), 0.12, 0.7, 'grey_dark')
    return m


# ---------------------------------------------------------------------------------------------- JEEP
def jeep(lod):
    m = Mesh(lod)
    r, wy = 0.46, (-1.62, 1.62)
    # chassis tub (narrow, between the wheels)
    m.side([(-2.3, 0.42), (2.3, 0.42), (2.38, 0.98), (-2.38, 0.98)], -0.8, 0.8, CAMO, bev=0.03)
    # hood + fenders (full width, over the wheels)
    m.side([(-2.42, 0.92), (-0.82, 0.92), (-0.82, 1.3), (-2.38, 1.24)], -1.1, 1.1, CAMO, bev=0.05)
    # cabin with slanted windscreen and short slanted tail
    cab = [(-0.84, 0.92), (2.42, 0.92), (2.42, 1.36), (1.62, 1.44), (1.48, 1.86), (-0.42, 1.86), (-0.78, 1.3)]
    m.side(cab, -1.08, 1.08, CAMO, bev=0.05)
    # glass: windscreen (2 panes), side windows, rear
    for x0, x1 in ((-0.98, -0.06), (0.06, 0.98)):
        m.plate([(x0, -0.79, 1.36), (x1, -0.79, 1.36), (x1, -0.44, 1.8), (x0, -0.44, 1.8)], (0, -1, 0.6), 0.012, 'glass_dark')
    for s in (1, -1):
        glass_x(m, s, 1.08, -0.3, 0.55, 1.4, 1.78)
        glass_x(m, s, 1.08, 0.7, 1.4, 1.4, 1.78)
        if lod == 0:
            m.xplate(s, 1.08, [(0.6, 0.98), (0.64, 0.98), (0.64, 1.8), (0.6, 1.8)], 'mil_dark', t=0.012)   # door seam
    m.yplate(1, 2.42, [(-0.7, 1.1), (0.7, 1.1), (0.7, 1.32), (-0.7, 1.32)], 'glass_dark', t=0.012)
    # front: grille, bumper, lights; rear bumper
    m.yplate(-1, -2.42, [(-0.75, 0.98), (0.75, 0.98), (0.75, 1.2), (-0.75, 1.2)], 'ink', t=0.02)
    m.bb(2.05, 0.22, 0.22, 0.04, 'mil_dark', at=(0, -2.45, 0.6), base=True)
    m.bb(1.9, 0.18, 0.2, 0.04, 'mil_dark', at=(0, 2.42, 0.58), base=True)
    for s in (1, -1):
        m.cyl_y(0.08, 0.04, m.seg(8, 6), 'lamp_glow', at=(s * 0.88, -2.44, 1.1))
    # roof ring + gun shield + MG
    m.cyl(0.46, 0.12, m.seg(12, 8), 'mil_dark', at=(0, 0.45, 1.86))
    m.bb(0.9, 0.08, 0.42, 0.02, CAMO, at=(0, 0.02, 1.98), base=True)
    if lod == 0:
        m.bar((0, 0.15, 2.2), (0, -0.75, 2.22), 0.04, 'ink')
        m.bb(0.16, 0.42, 0.16, 0.02, 'ink', at=(0, 0.3, 2.12), base=True)
        for s in (1, -1):
            m.bb(0.06, 0.12, 0.16, 0.02, 'ink', at=(s * 1.17, -0.65, 1.42), base=True)   # mirrors
        m.bb(0.5, 0.35, 0.45, 0.04, 'mil_canvas', at=(-0.7, 2.25, 1.38), base=True)       # jerrycan rack
    # wheels (under the fenders)
    for x in (-0.86, 0.86):
        for y in wy:
            plain_wheel(m, x, y, r, 0.4)
    return m


# ---------------------------------------------------------------------------------------------- CARGO TRUCK
def cargo_truck(lod):
    m = Mesh(lod)
    r = 0.55
    # frame rails
    for s in (1, -1):
        m.box(0.14, 6.6, 0.26, 'ink', at=(s * 0.45, 0.05, 0.62), base=True)
    # bonnet, front fenders
    m.side([(-3.45, 1.0), (-2.05, 1.0), (-2.05, 1.66), (-3.3, 1.62), (-3.45, 1.45)], -0.66, 0.66, CAMO, bev=0.05)
    for s in (1, -1):
        m.side([(-3.38, 1.02), (-2.05, 1.02), (-2.05, 1.18), (-2.4, 1.36), (-3.22, 1.36)], s * 0.62, s * 1.2, CAMO, bev=0.04)
    m.yplate(-1, -3.45, [(-0.55, 1.05), (0.55, 1.05), (0.55, 1.42), (-0.55, 1.42)], 'ink', t=0.02)   # grille
    m.bb(2.3, 0.2, 0.22, 0.04, 'mil_dark', at=(0, -3.5, 0.78), base=True)
    for s in (1, -1):
        m.cyl_y(0.11, 0.06, m.seg(8, 6), 'lamp_glow', at=(s * 0.9, -3.27, 1.42))
    # cab
    cab = [(-2.08, 1.0), (-0.62, 1.0), (-0.62, 2.55), (-1.75, 2.55), (-2.08, 1.85)]
    m.side(cab, -1.18, 1.18, CAMO, bev=0.06)
    for x0, x1 in ((-1.05, -0.06), (0.06, 1.05)):
        m.plate([(x0, -2.06, 1.9), (x1, -2.06, 1.9), (x1, -1.77, 2.47), (x0, -1.77, 2.47)], (0, -1, 0.5), 0.012, 'glass_dark')
    for s in (1, -1):
        glass_x(m, s, 1.18, -1.65, -0.95, 1.85, 2.42)
        if lod == 0:
            m.bb(0.06, 0.14, 0.24, 0.02, 'ink', at=(s * 1.3, -1.95, 1.95), base=True)     # mirrors
            m.beam((s * 1.18, -1.95, 2.05), (s * 1.28, -1.95, 2.05), 0.04, 0.04, 'ink')
    # spare wheel behind the cab, fuel tank
    m.cyl_x(0.5, 0.3, m.seg(10, 6), 'tyre', at=(0, -0.42, 1.65))
    for s in (1, -1):
        m.cyl_y(0.24, 0.9, m.seg(8, 6), 'mil_dark', at=(s * 0.82, -0.05, 0.62))
    # cargo bed with drop sides + canvas canopy
    m.bb(2.5, 3.95, 0.14, 0.03, 'mil_dark', at=(0, 1.52, 1.18), base=True)
    for s in (1, -1):
        m.bb(0.08, 3.95, 0.5, 0.02, CAMO, at=(s * 1.21, 1.52, 1.32), base=True)
    m.bb(2.5, 0.08, 0.5, 0.02, CAMO, at=(0, 3.46, 1.32), base=True)
    can = [(-1.24, 1.8), (1.24, 1.8), (1.24, 2.62), (0.95, 2.86), (0.4, 2.96), (-0.4, 2.96), (-0.95, 2.86), (-1.24, 2.62)]
    m.end(can, -0.36, 3.44, 'mil_canvas', bev=0.04)
    if lod == 0:
        for y in (0.4, 1.4, 2.4):                               # canopy hoops showing as ribs
            m.end([(x * 1.01, z + (0.012 if z > 1.9 else 0)) for x, z in can], y - 0.04, y + 0.04, 'mil_dark')
    # mudguards over the rear axles
    for s in (1, -1):
        m.bb(0.5, 2.5, 0.06, 0.02, 'mil_dark', at=(s * 1.0, 2.1, 1.16), base=True)
    # wheels: front axle + rear tandem
    for x in (-0.98, 0.98):
        for y in (-2.75, 1.55, 2.75):
            plain_wheel(m, x, y, r, 0.42)
    return m


# ---------------------------------------------------------------------------------------------- HELICOPTER
def rring(a, z0, z1, c, y, n=2):
    """Rounded-rectangle section at y: half-width a, z0..z1, corner radius c with n segments per corner (CCW from -Y)."""
    pts = []
    for cx, cz, a0 in ((a - c, z0 + c, -90), (a - c, z1 - c, 0), (-a + c, z1 - c, 90), (-a + c, z0 + c, 180)):
        for k in range(n + 1):
            t = math.radians(a0 + 90 * k / n)
            pts.append((cx + c * math.cos(t), y, cz + c * math.sin(t)))
    return pts


def helicopter(lod):
    m = Mesh(lod)
    n = 2 if lod == 0 else 1
    st = [(-5.25, 0.22, 0.98, 1.3, 0.1), (-5.0, 0.55, 0.78, 1.72, 0.24), (-4.45, 0.86, 0.62, 2.12, 0.34),
          (-3.6, 1.04, 0.56, 2.38, 0.38), (-2.4, 1.1, 0.55, 2.55, 0.4), (0.8, 1.1, 0.55, 2.55, 0.4),
          (1.7, 0.98, 0.66, 2.52, 0.36), (2.5, 0.62, 1.4, 2.46, 0.24), (3.4, 0.36, 1.9, 2.42, 0.14), (5.3, 0.2, 2.04, 2.36, 0.08)]
    if lod:
        st = [st[0], st[2], st[3], st[5], st[7], st[9]]
    rings = [rring(a, z0, z1, min(c, a * 0.9, (z1 - z0) * 0.45), y, n) for y, a, z0, z1, c in st]
    cnt = len(rings[0])                                     # 4 * (n + 1)
    glass_segs = 3 if lod == 0 else 2

    def colfn(i, k):
        # k indexes the ring edges; upper half = edges whose both ends have z above the ring middle
        if i >= glass_segs:
            return None
        r = rings[i]
        za, zb = r[k][2], r[(k + 1) % cnt][2]
        zm = (r[0][2] + max(p[2] for p in r)) / 2
        if za > zm - 0.15 and zb > zm - 0.15:
            top = max(p[2] for p in r)
            if i == glass_segs - 1 and za > top - 0.02 and zb > top - 0.02:
                return None                                 # roof over the cockpit stays painted
            return 'glass_dark'
        return None
    m.loft(rings, CAMO, colfn=colfn, cap_cols=('glass_dark', CAMO))
    # cabin door openings (dark), door windows, cockpit door frames
    for s in (1, -1):
        m.xplate(s, 1.1, [(-2.3, 0.78), (-0.4, 0.78), (-0.4, 2.15), (-2.3, 2.15)], 'ink_dark', t=0.015)
        glass_x(m, s, 1.1, 0.05, 0.65, 1.55, 2.12)
        if lod == 0:
            m.xplate(s, 1.1, [(-2.45, 2.2), (0.75, 2.2), (0.75, 2.28), (-2.45, 2.28)], 'ink', t=0.03)   # door rail
            m.bb(0.3, 1.2, 0.06, 0.02, 'ink', at=(s * 1.05, -1.4, 0.5), base=True)                        # step
            m.xplate(s, 1.05, [(-3.4, 1.62), (-3.3, 1.62), (-3.3, 2.32), (-3.4, 2.32)], 'mil_dark', t=0.03)  # cockpit pillar
    # engine deck with intakes, exhausts, mast, hub, blades
    m.bb(1.3, 3.4, 0.62, 0.08, CAMO, at=(0, 0.2, 2.5), base=True)
    m.bb(1.0, 1.0, 0.28, 0.05, CAMO, at=(0, -1.2, 2.5), base=True)
    if lod == 0:
        for s in (1, -1):
            m.yplate(-1, -1.5, [(s * 0.15, 2.62), (s * 0.55, 2.62), (s * 0.55, 2.98), (s * 0.15, 2.98)], 'ink', t=0.02)
            m.cyl_y(0.17, 0.55, 8, 'ink', at=(s * 0.45, 2.1, 2.88), r2=0.2)
        m.bar((0, 1.0, 2.55), (0.0, 1.35, 3.05), 0.03, 'ink')            # antenna
        m.bar((0, -3.0, 0.55), (0, -3.3, 0.25), 0.03, 'ink')             # belly antenna
        m.cyl(0.15, 0.14, 8, 'lamp_glow', at=(0, -4.3, 0.5))            # landing light
        m.bar((0.25, -5.1, 1.5), (0.25, -5.7, 1.5), 0.025, 'ink')        # pitot
    m.cyl(0.17, 0.62, m.seg(8, 6), 'mil_dark', at=(0, -0.35, 3.1))
    m.cyl(0.36, 0.2, m.seg(10, 6), 'ink', at=(0, -0.35, 3.62))
    for a in (20, 110, 200, 290):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p0 = (ca * 0.3, -0.35 + sa * 0.3, 3.72)
        p1 = (ca * 5.35, -0.35 + sa * 5.35, 3.5)
        m.beam(p0, p1, 0.48, 0.07, 'mil_dark')
        if lod == 0:
            m.beam((ca * 4.9, -0.35 + sa * 4.9, 3.53), (ca * 5.36, -0.35 + sa * 5.36, 3.51), 0.5, 0.08, 'mustard')  # tip
    # tail: fin, stabiliser, tail rotor
    m.side([(4.7, 2.15), (5.55, 2.15), (5.75, 3.35), (5.35, 3.4)], -0.07, 0.07, CAMO, bev=0.02)
    m.bb(2.0, 0.42, 0.07, 0.02, CAMO, at=(0, 4.55, 2.12), base=True)
    if lod == 0:
        for s in (1, -1):
            m.bb(0.06, 0.4, 0.3, 0.01, CAMO, at=(s * 1.0, 4.58, 2.0), base=True)     # stabiliser end plates
    m.cyl_x(0.12, 0.2, 6, 'ink', at=(0.16, 5.45, 2.85))
    for a in (30, 120):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        m.beam((0.24, 5.45 - ca * 0.85, 2.85 - sa * 0.85), (0.24, 5.45 + ca * 0.85, 2.85 + sa * 0.85), 0.2, 0.05, 'mil_dark', up=(1, 0, 0))
    # skids + cross tubes
    sk = m.seg(8, 4)
    for s in (1, -1):
        m.tube_path([(s * 1.28, -3.15, 0.34), (s * 1.28, -2.9, 0.14), (s * 1.28, -2.6, 0.08), (s * 1.28, 2.1, 0.08)], 0.07, sk, 'ink')
        for y in (-1.8, 1.0):
            m.tube_path([(s * 1.28, y, 0.1), (s * 1.2, y, 0.42), (s * 0.7, y, 0.62)], 0.06, sk, 'ink')
    return m


# ---------------------------------------------------------------------------------------------- PATROL BOAT
def patrol_boat(lod):
    m = Mesh(lod)
    Lb, B = 8.4, 2.7
    rings = L.hull(m, Lb, B, 1.05, 0.55, 'navy_grey', 'navy_grey', 'navy_grey_dark', 'navy_grey_dark', bow_rise=0.35,
                   transom=0.88, deadrise=0.25, ts=None if lod == 0 else [0.0, 0.1, 0.3, 0.6, 1.0])
    # rubber fender collar along the sheer (both sides)
    for s in (1, -1):
        pts = [(x * 1.02, y, z - 0.05) for x, y, z in L.sheer_line(rings, s)[1:]]
        m.tube_path(pts, 0.12, m.seg(6, 4), 'ink')
    # wheelhouse with window band, roof, mast
    m.bb(2.0, 2.4, 1.25, 0.06, 'navy_grey', at=(0, 0.4, 1.1), base=True)
    m.bb(2.2, 2.7, 0.12, 0.04, 'navy_grey_dark', at=(0, 0.35, 2.35), base=True)
    m.plate([(-0.9, -0.81, 1.78), (0.9, -0.81, 1.78), (0.9, -0.81, 2.22), (-0.9, -0.81, 2.22)], (0, -1, 0), 0.012, 'glass_dark')
    for s in (1, -1):
        glass_x(m, s, 1.0, -0.6, 1.3, 1.8, 2.22)
    # radar arch (two legs) + dome + light
    for s in (1, -1):
        m.beam((s * 0.7, 1.35, 2.47), (s * 0.45, 1.15, 3.05), 0.12, 0.12, 'navy_grey_dark', up=(0, 1, 0))
    m.bb(1.1, 0.3, 0.12, 0.03, 'navy_grey_dark', at=(0, 1.15, 3.02), base=True)
    m.cyl(0.32, 0.22, m.seg(10, 6), 'chalk', at=(0, 1.15, 3.14), r_top=0.28)
    if lod == 0:
        m.cyl(0.06, 0.16, 6, 'lamp_glow', at=(0.42, 1.15, 3.14))
        m.bb(0.5, 0.2, 0.18, 0.03, 'chalk', at=(0, 0.6, 2.47), base=True)                # searchlight
    # bow gun: pedestal, shield, barrel
    m.cyl(0.18, 0.6, m.seg(8, 6), 'navy_grey_dark', at=(0, -2.6, 1.05))
    m.bb(0.75, 0.08, 0.42, 0.02, 'navy_grey', at=(0, -2.78, 1.55), base=True)
    m.bb(0.2, 0.55, 0.2, 0.02, 'ink', at=(0, -2.6, 1.68), base=True)
    m.bar((0, -2.85, 1.78), (0, -3.6, 1.78), 0.04, 'ink')
    # twin outboard engines on the transom
    for s in (1, -1):
        m.bb(0.42, 0.5, 0.75, 0.06, 'ink_light', at=(s * 0.55, 4.43, 0.55), base=True)
        m.box(0.14, 0.2, 0.7, 'ink', at=(s * 0.55, 4.48, 0.0))
    return m


SPECS = [
    dict(name='MW86_Tank', family='Military', kind='ground', budget=6000, folder='tank', target=(3.4, 8.0, 2.8),
         notes='Tramduro parade tank (kind tank, data box 3.4 x 8 x 2.8, long axis on data Y).'),
    dict(name='MW86_AirDefence', family='Military', kind='ground', budget=6000, folder='air_defence', target=(4.0, 6.0, 3.5),
         notes='Tracked SAM launcher, 2x2 canisters at 24 deg + radar panel (kind stylized_air_defence, data 6 x 4 x 3.5, long axis on data X).'),
    dict(name='MW86_MissileSilo', family='Military', kind='ground', budget=6000, folder='missile_silo', target=(7.0, 7.0, 11.0),
         notes='Cartoon missile sticking out of an open shaft (kind fictional_nuclear_missile, 7 x 7 x 11). No symbols, no text.'),
    dict(name='MW86_MilJeep', family='Military', kind='ground', budget=3000, folder='mil_jeep', target=(3.0, 7.0, 2.8),
         notes='Military utility vehicle (kind military_utility_vehicle; real 4.9 x 2.2 m inside the 3 x 7 data box).'),
    dict(name='MW86_MilTruck', family='Military', kind='ground', budget=6000, folder='mil_truck', target=(3.0, 7.0, 2.8),
         notes='6x6 cargo truck with canvas canopy (kind military_cargo_truck, 3 x 7 data box).'),
    dict(name='MW86_Helicopter', family='Military', kind='ground', budget=8000, folder='helicopter', target=(11.0, 12.0, 4.0),
         notes='Utility helicopter on skids, rotor parked (kind helicopter, data 12 x 11 x 4, long axis on data X).'),
    dict(name='MW86_PatrolBoat', family='Military', kind='water', budget=6000, folder='patrol_boat', target=(3.0, 9.0, 4.0),
         notes='Patrol boat, navy grey, bow MG, twin outboards (kind patrol_boat, 9 x 3, moves on a route). Pivot = waterline.'),
]
BUILDERS = {'MW86_Tank': tank, 'MW86_AirDefence': air_defence, 'MW86_MissileSilo': missile_silo, 'MW86_MilJeep': jeep,
            'MW86_MilTruck': cargo_truck, 'MW86_Helicopter': helicopter, 'MW86_PatrolBoat': patrol_boat}

if __name__ == '__main__':
    L.run_family(SPECS, BUILDERS)
