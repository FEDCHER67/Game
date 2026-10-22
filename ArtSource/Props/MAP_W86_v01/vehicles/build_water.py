"""MAP_W86_v01 vehicles - WATER family: motor yacht 22 m, sport cruiser 10 m, fishing boat on keel blocks (port),
upturned rowing boat (Hamlet bank), jet ski and SUP board (beach). Original procedural models (no third-party assets).
Atlas MW86_Water_<A|B|C>.png ('@teak_deck' teak region, '@hull_planks' painted clinker planks).

blender -b --factory-startup -P build_water.py -- --out-root <ArtSource/Props/MAP_W86_v01/vehicles> --fbx-dir <Unity Vehicles dir>
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / '_lib'))
import mw86lib as L  # noqa: E402
from mw86lib import Mesh, T, R  # noqa: E402

TEAK = '@teak_deck'


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def rails(m, rings, y_end, h, side_set=(1, -1), stanchions=5, start=1):
    """Stainless bow rails along the sheer from the bow to y_end, h above the deck, with stanchions."""
    for s in side_set:
        pts = [(x * 0.94, y, z + h) for x, y, z in L.sheer_line(rings, s)[start:] if y <= y_end]
        if len(pts) < 2:
            continue
        m.tube_path(pts, 0.03, 6, 'chrome')
        n = len(pts)
        for k in range(stanchions):
            p = pts[min(n - 1, int(round(k * (n - 1) / max(1, stanchions - 1))))]
            m.bar((p[0], p[1], p[2] - h), p, 0.025, 'chrome', seg=6)


def motor_yacht(lod):
    m = Mesh(lod)
    Lh, B = 21.0, 5.8
    ts = None if lod == 0 else [0.0, 0.1, 0.3, 0.6, 1.0]
    rings = L.hull(m, Lh, B, 1.7, 1.0, 'yacht_hull', 'yacht_stripe', 'yacht_boot', TEAK, transom_col='yacht_hull',
                   bow_rise=0.6, transom=0.88, deadrise=0.2, ts=ts)
    # hull side windows (dark slits) + sheer accent line
    for s in (1, -1):
        for y0, y1 in ((-4.2, -1.4), (-0.8, 2.6), (3.2, 5.6)):
            L.hull_plate(m, rings, s, y0, y1, 0.85, 1.18, 'glass_dark')
        if lod == 0:
            L.hull_plate(m, rings, s, -7.5, 9.8, 1.48, 1.58, 'yacht_stripe')
    # main superstructure: sloped windscreen, slight tumblehome
    zb, zt = 1.62, 3.75
    bot = [(-1.55, -4.7), (1.55, -4.7), (2.22, -2.7), (2.22, 7.3), (-2.22, 7.3), (-2.22, -2.7)]
    top = [(-1.38, -3.25), (1.38, -3.25), (2.06, -1.65), (2.06, 7.1), (-2.06, 7.1), (-2.06, -1.65)]
    m.frustum(bot, zb, top, zt, 'yacht_super', bev=0.06)
    # windscreen glass on the three front faces
    for i0, i1 in ((5, 0), (0, 1), (1, 2)):
        b0, b1 = (*bot[i0], zb), (*bot[i1], zb)
        t0, t1 = (*top[i0], zt), (*top[i1], zt)
        q = [lerp(b0, t0, 0.38), lerp(b1, t1, 0.38), lerp(b1, t1, 0.9), lerp(b0, t0, 0.9)]
        q = [lerp(q[0], q[1], 0.04), lerp(q[1], q[0], 0.04), lerp(q[2], q[3], 0.04), lerp(q[3], q[2], 0.04)]
        cx = sum(p[0] for p in q) / 4
        cy = sum(p[1] for p in q) / 4
        m.plate(q, (cx, cy + 0.5, 0.6), 0.014, 'glass_dark')
    # side window band (follows the tumblehome)
    for s in (1, -1):
        def sx(z):
            return s * (2.22 + (2.06 - 2.22) * (z - zb) / (zt - zb))
        za, zc = 2.45, 3.45
        m.plate([(sx(za), -1.9, za), (sx(za), 6.4, za), (sx(zc), 6.4, zc), (sx(zc), -1.9, zc)], (s, 0, 0.1), 0.014, 'glass_dark')
    # aft saloon doors (glass) on the rear face
    m.yplate(1, 7.3, [(-1.4, 1.75), (1.4, 1.75), (1.4, 3.4), (-1.4, 3.4)], 'glass_dark', t=0.014)
    # flybridge deck, console, seats, hardtop on posts, radar
    fb_bot = [(-1.2, -2.7), (1.2, -2.7), (1.95, -1.2), (1.95, 5.6), (-1.95, 5.6), (-1.95, -1.2)]
    m.prism_xy(fb_bot, zt, zt + 0.2, 'yacht_super', bev=0.04)
    m.frustum([(x * 0.98, y) for x, y in fb_bot[:3]] + [(1.9, -0.6), (-1.9, -0.6), (-1.91, -1.2)], zt + 0.2,
              [(-0.9, -2.2), (0.9, -2.2), (1.6, -1.05), (1.6, -0.55), (-1.6, -0.55), (-1.6, -1.05)], zt + 0.75,
              'yacht_super', bev=0.03)                                      # flybridge front coaming
    m.bb(1.4, 0.6, 0.9, 0.05, 'yacht_super', at=(0.6, -0.1, zt + 0.2), base=True)       # helm console
    m.bb(2.6, 0.7, 0.45, 0.06, 'cushion', at=(0, 1.2, zt + 0.2), base=True)              # helm seat bench
    m.bb(3.4, 0.6, 0.4, 0.06, 'cushion', at=(0, 4.9, zt + 0.2), base=True)               # aft sofa
    ht = zt + 2.0
    m.bb(3.6, 4.6, 0.14, 0.05, 'yacht_super', at=(0, 1.9, ht), base=True)                # hardtop
    for x in (-1.6, 1.6):
        for y in (0.0, 3.9):
            m.bar((x, y, zt + 0.2), (x * 0.95, y, ht), 0.06, 'chrome', seg=m.seg(6, 4))
    m.cyl(0.3, 0.26, m.seg(10, 6), 'chalk', at=(0, 1.2, ht + 0.14), r_top=0.26)          # radar dome
    if lod == 0:
        m.bar((0.9, 2.9, ht + 0.14), (0.9, 2.9, ht + 0.75), 0.03, 'chrome')              # antenna
        m.bar((-0.9, 2.9, ht + 0.14), (-0.9, 2.9, ht + 0.6), 0.03, 'chrome')
        m.cyl(0.18, 0.06, 8, 'ink', at=(0.6, -0.25, zt + 1.12))                           # wheel
    # aft cockpit: stern bench + table, swim platform with steps
    m.bb(4.0, 0.7, 0.5, 0.06, 'cushion', at=(0, 9.7, 1.6), base=True)
    m.bb(1.2, 0.8, 0.08, 0.02, 'teak_dark', at=(0, 8.6, 2.25), base=True)
    m.cyl(0.08, 0.6, 6, 'chrome', at=(0, 8.6, 1.65))
    m.bb(5.0, 1.15, 0.18, 0.04, TEAK, at=(0, 11.05, 0.22), base=True)
    if lod == 0:
        rails(m, rings, -4.6, 0.8, stanchions=5)
        for s in (1, -1):                                   # stern rails
            m.tube_path([(s * 2.3, 7.4, 2.55), (s * 2.42, 10.4, 2.55)], 0.03, 6, 'chrome')
        m.bb(0.5, 0.6, 0.25, 0.04, 'ink_light', at=(0, -9.9, 2.15), base=True)           # anchor winch
    return m


def cruiser(lod):
    m = Mesh(lod)
    Lh, B = 9.6, 3.5
    ts = None if lod == 0 else [0.0, 0.1, 0.3, 0.6, 1.0]
    rings = L.hull(m, Lh, B, 1.1, 0.6, 'yacht_hull', 'yacht_stripe', 'yacht_boot', TEAK, transom_col='yacht_hull',
                   bow_rise=0.38, transom=0.9, deadrise=0.22, ts=ts)
    for s in (1, -1):
        L.hull_plate(m, rings, s, -2.6, -0.6, 0.62, 0.8, 'glass_dark')
        L.hull_plate(m, rings, s, -1.4, 4.4, 1.0, 1.08, 'yacht_stripe')
    # low coachroof over the cabin with window slits
    zb = 1.12
    bot = [(-0.75, -3.6), (0.75, -3.6), (1.45, -2.2), (1.5, 0.6), (-1.5, 0.6), (-1.45, -2.2)]
    top = [(-0.55, -2.9), (0.55, -2.9), (1.22, -1.9), (1.28, 0.45), (-1.28, 0.45), (-1.22, -1.9)]
    m.frustum(bot, zb, top, zb + 0.55, 'yacht_super', bev=0.05)
    for s in (1, -1):
        m.plate([(s * 1.47, -2.0, 1.3), (s * 1.49, 0.3, 1.3), (s * 1.33, 0.3, 1.55), (s * 1.31, -2.0, 1.55)], (s, 0, 0.3), 0.012, 'glass_dark')
    # windscreen (sloped) at the front of the cockpit
    m.plate([(-1.5, 0.55, 1.62), (1.5, 0.55, 1.62), (1.38, 0.95, 2.1), (-1.38, 0.95, 2.1)], (0, -1, 0.8), 0.03, 'glass_dark')
    # hardtop on two raked posts per side
    m.bb(2.9, 2.5, 0.12, 0.05, 'yacht_super', at=(0, 2.05, 2.62), base=True)
    for s in (1, -1):
        m.beam((s * 1.4, 1.0, 1.15), (s * 1.3, 1.25, 2.64), 0.12, 0.08, 'yacht_super', up=(0, 1, 0))
        m.beam((s * 1.4, 3.1, 1.15), (s * 1.3, 3.05, 2.64), 0.12, 0.08, 'yacht_super', up=(0, 1, 0))
    # cockpit: helm, seats, U-sofa, swim platform
    m.bb(0.9, 0.5, 0.75, 0.04, 'yacht_super', at=(0.6, 1.25, 1.1), base=True)
    m.bb(1.0, 0.55, 0.45, 0.05, 'cushion', at=(0.6, 2.0, 1.1), base=True)
    m.bb(2.7, 0.55, 0.42, 0.05, 'cushion', at=(0, 4.0, 1.0), base=True)
    m.bb(0.55, 1.4, 0.42, 0.05, 'cushion', at=(-1.15, 3.2, 1.0), base=True)
    m.bb(3.1, 0.9, 0.14, 0.03, TEAK, at=(0, 5.2, 0.2), base=True)
    if lod == 0:
        rails(m, rings, -2.4, 0.55, stanchions=4)
        m.cyl(0.15, 0.05, 8, 'ink', M=T(0.6, 1.08, 1.75) @ R(-60, 'X'))                     # wheel
        m.bb(0.3, 0.35, 0.18, 0.03, 'ink_light', at=(0, -4.25, 1.38), base=True)           # anchor
        m.cyl(0.18, 0.18, 8, 'chalk', at=(0, 2.4, 2.74))                                   # radar
    return m


def keel_block_boat(lod):
    m = Mesh(lod)
    Lh, B = 9.4, 2.7
    ts = None if lod == 0 else [0.0, 0.12, 0.35, 0.65, 1.0]
    zl = 1.05                                               # waterline height above the yard (keel on 0.45 m blocks)
    rings = L.hull_rings(Lh, B, 1.0, 0.6, ts=ts, bow_rise=0.45, transom=0.8, deadrise=0.42, chine=0.7)
    rings = [[(x, y, z + zl) for x, y, z in r] for r in rings]
    m.loft(rings, 'boat_hull', cols=['boat_hull', 'chalk', 'boat_bottom', 'boat_bottom', 'boat_bottom', 'boat_bottom', 'chalk',
                                     'boat_hull', 'wood'], cap_cols=('boat_hull', 'boat_hull'))
    for s in (1, -1):                                       # rubbing strake
        pts = [(x * 1.015, y, z - 0.08) for x, y, z in L.sheer_line(rings, s)[1:]]
        m.tube_path(pts, 0.06, m.seg(6, 4), 'wood_dark')
    # wheelhouse
    zd = L.deck_z(rings, 0.6)
    m.bb(1.8, 1.8, 1.4, 0.05, 'boat_house', at=(0, 0.6, zd - 0.05), base=True)
    m.bb(2.0, 2.1, 0.1, 0.03, 'boat_hull', at=(0, 0.6, zd + 1.35), base=True)
    m.yplate(-1, -0.3, [(-0.75, zd + 0.75), (0.75, zd + 0.75), (0.75, zd + 1.15), (-0.75, zd + 1.15)], 'glass_dark', t=0.012)
    for s in (1, -1):
        m.xplate(s, 0.9, [(-0.1, zd + 0.75), (0.9, zd + 0.75), (0.9, zd + 1.15), (-0.1, zd + 1.15)], 'glass_dark', t=0.012)
    m.cyl(0.06, 0.8, m.seg(6, 4), 'grey', at=(0.55, 1.3, zd + 1.45))                    # light mast
    if lod == 0:
        m.cyl(0.08, 0.14, 6, 'lamp_glow', at=(0.55, 1.3, zd + 2.25))
        m.cyl(0.22, 0.12, 8, 'chalk', at=(-0.4, 0.9, zd + 1.45))                          # radar dome
        m.bb(1.6, 1.4, 0.5, 0.06, 'canopy', at=(0, 3.1, L.deck_z(rings, 3.1) - 0.05), base=True)   # tarp-covered hatch
    # keel blocks (two crossed timber layers) and four jack stands
    kz = L.hull_rings(Lh, B, 1.0, 0.6, ts=[0.5], bow_rise=0.45, transom=0.8, deadrise=0.42, chine=0.7)[0][4][2] + zl
    for y in (-2.4, 0.2, 2.8):
        m.bb(0.9, 0.35, 0.22, 0.02, 'wood', at=(0, y, 0.0), base=True)
        m.bb(0.35, 0.8, kz - 0.22 + 0.02, 0.02, 'wood_dark', at=(0, y, 0.22), base=True)
    for s in (1, -1):
        for y in (-1.6, 2.0):
            x_top = L.hull_x(rings, y, 0.95, s)
            m.bb(0.4, 0.4, 0.05, 0.01, 'ink_light', at=(s * (abs(x_top) + 0.3), y, 0.0), base=True)
            m.bar((s * (abs(x_top) + 0.3), y, 0.05), (x_top + s * 0.06, y, 0.95), 0.05, 'red', seg=m.seg(6, 4))
            if lod == 0:
                m.bb(0.06, 0.3, 0.3, 0.01, 'ink', at=(x_top + s * 0.06, y, 0.95))
    return m


def upturned_rowboat(lod):
    m = Mesh(lod)
    Lh, B = 3.7, 1.4
    ts = [0.0, 0.08, 0.22, 0.42, 0.62, 0.82, 1.0] if lod == 0 else [0.0, 0.2, 0.55, 1.0]
    rings = L.hull_rings(Lh, B, 0.42, 0.12, ts=ts, bow_rise=0.12, transom=0.62, deadrise=0.3, chine=0.72, bow_w=0.02)
    ztop = max(p[2] for r in rings for p in r)
    flip = [[(x, y, ztop - z + 0.16) for x, y, z in reversed(r)] for r in rings]
    m.loft(flip, '@hull_planks', cols=['@hull_planks', '@hull_planks', 'row_bottom', 'row_bottom', 'row_bottom',
                                       'row_bottom', '@hull_planks', '@hull_planks', 'wood_dark'],
           cap_cols=('@hull_planks', '@hull_planks'))
    # keel strip on top, stem
    keel = [r[4] for r in flip]
    m.tube_path([(x, y, z + 0.02) for x, y, z in keel[1:]], 0.04, 4, 'wood_dark')
    # two log supports underneath
    for y in (-0.85, 0.95):
        m.cyl_x(0.09, 1.3, m.seg(8, 6), 'wood_dark', at=(0, y, 0.09))
    if lod == 0:                                            # a pair of oars lying across the upturned bottom
        top = max(p[2] for p in keel)
        for k, dx in enumerate((-0.12, 0.12)):
            p0, p1 = (dx - 0.35, -1.25, top - 0.06 + 0.07 * k), (dx + 0.35, 1.0, top - 0.02 + 0.07 * k)
            m.beam(p0, p1, 0.05, 0.05, 'wood')
            m.beam(p1, (p1[0] + 0.12, p1[1] + 0.42, p1[2] - 0.06), 0.14, 0.03, 'wood')
    return m


def jet_ski(lod):
    m = Mesh(lod)
    Lh, B = 3.05, 1.12
    ts = [0.0, 0.08, 0.22, 0.45, 0.7, 1.0] if lod == 0 else [0.0, 0.25, 0.6, 1.0]
    rings = L.hull_rings(Lh, B, 0.42, 0.28, ts=ts, bow_rise=0.16, transom=0.86, deadrise=0.4, chine=0.8, keel_bow=0.25)
    rings = [[(x, y, z + 0.28) for x, y, z in r] for r in rings]
    m.loft(rings, 'chalk', cols=['chalk', 'jetski_paint', 'ink_light', 'ink_light', 'ink_light', 'ink_light', 'jetski_paint',
                                 'chalk', 'jetski_paint'], cap_cols=('chalk', 'chalk'))
    zd = 0.72
    # front hood (bulging cowl) and steering pod
    hb = [(-0.2, -1.42), (0.2, -1.42), (0.48, -0.9), (0.5, -0.3), (-0.5, -0.3), (-0.48, -0.9)]
    ht = [(-0.1, -1.2), (0.1, -1.2), (0.36, -0.85), (0.38, -0.4), (-0.38, -0.4), (-0.36, -0.85)]
    m.frustum(hb, zd - 0.05, ht, zd + 0.3, 'jetski_paint', bev=0.04)
    m.frustum([(-0.22, -0.45), (0.22, -0.45), (0.22, -0.2), (-0.22, -0.2)], zd + 0.25,
              [(-0.16, -0.38), (0.16, -0.38), (0.16, -0.24), (-0.16, -0.24)], zd + 0.42, 'ink', bev=0.02)
    m.bar((-0.42, -0.3, zd + 0.42), (0.42, -0.3, zd + 0.42), 0.035, 'ink', seg=6)
    if lod == 0:
        for s in (1, -1):
            m.cyl_x(0.045, 0.14, 6, 'ink_light', at=(s * 0.38, -0.3, zd + 0.42))
        m.plate([(-0.18, -0.95, zd + 0.27), (0.18, -0.95, zd + 0.27), (0.12, -0.72, zd + 0.33), (-0.12, -0.72, zd + 0.33)],
                (0, -0.3, 1), 0.01, 'glass_dark')                    # small screen
    # seat on a pedestal, rear grab handle, footwells implied by the hull deck
    m.bb(0.42, 1.25, 0.12, 0.04, 'jetski_paint', at=(0, 0.35, zd - 0.02), base=True)
    m.bb(0.4, 1.2, 0.17, 0.06, 'ink', at=(0, 0.35, zd + 0.1), base=True)
    m.tube_path([(-0.18, 1.0, zd + 0.1), (-0.18, 1.12, zd + 0.24), (0.18, 1.12, zd + 0.24), (0.18, 1.0, zd + 0.1)], 0.025, 4, 'ink')
    return m


def sup_board(lod):
    m = Mesh(lod)
    n = 7 if lod == 0 else 4
    half = []
    for k in range(n + 1):                                  # nose half-ellipse
        a = math.pi * k / n
        half.append((0.38 * math.cos(a), -1.0 - 0.6 * math.sin(a)))
    tail = [(-0.33, 1.42), (-0.2, 1.6), (0.2, 1.6), (0.33, 1.42)]
    poly = half + [(-0.38, 0.8)] + tail + [(0.38, 0.8)]
    m.prism_xy(poly, 0.0, 0.12, 'chalk', bev=0.03 if lod == 0 else 0.0)
    inset = [(x * 0.92, y * 0.97) for x, y in poly]
    m.zplate(0.12, inset, 'sup_paint', t=0.008)
    m.zplate(0.128, [(-0.28, -0.3), (0.28, -0.3), (0.28, 0.9), (-0.28, 0.9)], 'ink_light', t=0.01)   # deck pad
    if lod == 0:
        m.zplate(0.128, [(-0.04, -1.5), (0.04, -1.5), (0.04, -0.45), (-0.04, -0.45)], 'chalk', t=0.006)
    return m


SPECS = [
    dict(name='MW86_Yacht_Motor22', family='Water', kind='water', budget=8000, folder='yacht_motor22', target=(6.0, 22.0, 4.0),
         notes='Motor yacht with flybridge, 22 m (kind yacht 22 x 6; scale 0.68 for the 15 x 5 one). White / teak / navy stripe. Pivot = waterline.'),
    dict(name='MW86_Yacht_Cruiser10', family='Water', kind='water', budget=8000, folder='yacht_cruiser10', target=(3.6, 10.0, 3.0),
         notes='Sport cruiser with hardtop, 10 m (kind yacht 12 / 10 / 8 m -> scale 1.2 / 1.0 / 0.8). Pivot = waterline.'),
    dict(name='MW86_Boat_KeelBlocks', family='Water', kind='ground', budget=6000, folder='boat_keel_blocks', target=(3.0, 10.0, 2.6),
         notes='Fishing boat laid up on keel blocks with jack stands (kind boat_on_keel_blocks, port yard).'),
    dict(name='MW86_Rowboat_Upturned', family='Water', kind='ground', budget=3000, folder='rowboat_upturned', target=(1.5, 3.8, 1.0),
         notes='Wooden rowing boat upside down on two logs + oars (kind upturned_boat, Hamlet river bank). Fishing nets = M2.'),
    dict(name='MW86_JetSki', family='Water', kind='ground', budget=3000, folder='jet_ski', target=(1.2, 3.2, 1.1),
         notes='Jet ski parked on the sand (kind jet_ski, data 3.2 x 1.2 x 1.1, long axis on data X).'),
    dict(name='MW86_SUP', family='Water', kind='ground', budget=1000, folder='sup_board', target=(0.8, 3.2, 0.2),
         notes='Stand-up paddle board lying flat (kind sup_board, 0.8 x 3.2, long axis on data Y).'),
]
BUILDERS = {'MW86_Yacht_Motor22': motor_yacht, 'MW86_Yacht_Cruiser10': cruiser, 'MW86_Boat_KeelBlocks': keel_block_boat,
            'MW86_Rowboat_Upturned': upturned_rowboat, 'MW86_JetSki': jet_ski, 'MW86_SUP': sup_board}

if __name__ == '__main__':
    L.run_family(SPECS, BUILDERS)
