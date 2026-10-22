"""Step 4 / coast districts: City Beach (09, plan v06), Industrial Port (06, plan v03), Tramduro island (10, plan 06 FINAL)
-> world v85 district data (lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §0-§1, §5, §6, §7.6, §7.9, §7.10; v02 §5, §8.6, §8.9, §8.10; BEACH_SPEC v01 §2a):
 Beach    placement = the v85 world drawing (build_world_v85.py R45_miami_beach constants in pre-shift metres -> common.post,
          v83 pier from the waterline, v84 palm rows 11 m, v85 two lifeguard towers, v84 van rut TRACK to the Elite beach);
          content inventory = D09 layout/plan v06 + BEACH_SPEC §2a (68 umbrella sets scattered, 2 volleyball, 2 bars, rental,
          swim zone, oil splashes in the west). No drawn trees / towels / dots are copied.
 Port     plan v03 metres (layout v03 + WORLD_MAP_v11 district 06) -> the world picture P_port_v03_world.png is the plan stretched
          1.25 x 0.8 (PORT_SCALE of build_world_v85): T(x, y) = (1197.2 + 1.25 (x - 960), 670.4 + 0.8 (y - 634)) world m (post-shift
          = 0 there). Object CENTRES follow T (the drawn layout), SIZES stay real (plan metres) - no squashed containers / elliptic
          tanks; groups (container stacks, drums) keep their internal spacing; overlaps / road conflicts after that are resolved by
          the smallest nudge and logged. Port road = R84_port_road, cornice = R27_cornice_in_port, bridge = L05b_bridges (master SVG).
 Tramduro TRAMDURO_LAYOUT_v06.json (v11 metres) + translation measured on the v85 render (palace + hangar + gate posts).
          Bridge = real bridge on piers (v10 §5): axis of the drawn bridge, cut to the shorelines measured on the render.
Outputs: Data/<REV>/districts/{beach,port,tramduro}_v85.json (DISTRICT_SCHEMA.md), out_<REV>/check_{beach,port,tramduro}.png
(preview v85 crop x3). Run: python s04_coast.py (deterministic, ~20 s).

REV != v01 (Map W86, agent A3, 2026-10-22, Downtown plan v37, Vadim: "beach one-to-one from v85, only 54 m lower - the city grew up and
down, beach the same size"): every beach object keeps its v85 layout and is moved by beach_dy(x): -54 m for world x 790-1280 (the city
beach), smooth taper to 0 at x 700 (sand arc at the Quiet Valley rocks) and x 1400 (the Elite beach stays where it is; the van rut track
runs diagonally between them, as drawn on v37). bpost = common.post + beach_dy. beach_outline / new_coast feed downtown_v37_land.json.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from common import (MAP_FULL, MAP_PREVIEW, REF, REV, ROOT, WORK, area, ccw, chaikin, contour, h01, nearest_on, plen, points_of,
                    post, resample, rnd2, rrect, save_json, svg_tags, svg_text, u2w, attr)

Image.MAX_IMAGE_PIXELS = None
D11 = os.path.join(REF, 'World_v11', 'Districts')
BEACH_JSON = os.path.join(D11, 'D09_City_Beach_layout_v06.json')
BEACH_PNG = os.path.join(D11, 'D09_City_Beach_plan_v06.png')
PORT_JSON = os.path.join(D11, 'D06_Industrial_Port_layout_v03.json')
PORT_PNG = os.path.join(D11, 'D06_Industrial_Port_plan_v03.png')
WORLD11 = os.path.join(REF, 'World_v11', 'WORLD_MAP_v11.json')
BUILD = os.path.join(REF, 'World_v85', 'build_world_v85.py')
PORT_IMG = os.path.join(REF, 'World_v85', 'v85_assets', 'P_port_v03_world.png')
TRAM_DIR = os.path.join(ROOT, 'Working', 'Reviews', 'Tramduro_2026-10-14')
TRAM_JSON = os.path.join(TRAM_DIR, 'TRAMDURO_LAYOUT_v06.json')
TRAM_PNG = os.path.join(TRAM_DIR, 'TRAMDURO_PLAN_06_FINAL.png')
TRAM_DEC = os.path.join(TRAM_DIR, 'TRAMDURO_OWNER_DECISIONS_v08.txt')
ROAD_W = 6.4                                   # v10 §6 rural asphalt / v02 §5 bridge carriageway
BRIDGE_W = 8.8                                 # v02 §5 bridge deck
PIER_STEP = 20.0                               # bridge pier spacing (brief)
_IMG = {}


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, '/')


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def R(poly):
    return [rnd2(p) for p in poly]


def Rccw(poly):
    return [rnd2(p) for p in ccw(poly)]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def ellipse(c, rx, ry, n=20):
    return [(c[0] + rx * math.cos(2 * math.pi * i / n), c[1] + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def full():
    if 'f' not in _IMG:
        _IMG['f'] = np.asarray(Image.open(MAP_FULL).convert('RGB')).astype(np.int16)
    return _IMG['f']


def px(x, y):
    a = full()
    return a[int((950 - y) * 5), int(x * 5)]


def is_water(c):
    return int(c[2]) - int(c[0]) > 18                                    # sea / foam: blue clearly above red; sand, rock, lawn: not


def buffer_line(pl, hw):
    """Polygon of a polyline buffered by hw (mitred joins, flat caps)."""
    L, Rr = [], []
    n = len(pl)
    for i in range(n):
        a = pl[max(0, i - 1)]
        b = pl[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        L.append((pl[i][0] + nx * hw, pl[i][1] + ny * hw))
        Rr.append((pl[i][0] - nx * hw, pl[i][1] - ny * hw))
    return L + Rr[::-1]


def sat_overlap(a, b, gap=0.0):
    """Convex polygons a, b overlap (or are closer than gap along every separating axis test)."""
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            ax, ay = -(q[1] - p[1]), q[0] - p[0]
            L = math.hypot(ax, ay) or 1.0
            ax, ay = ax / L, ay / L
            pa = [v[0] * ax + v[1] * ay for v in a]
            pb = [v[0] * ax + v[1] * ay for v in b]
            if max(pa) + gap <= min(pb) or max(pb) + gap <= min(pa):
                return False
    return True


def poly_inside(poly, ring, margin=0.0):
    """All vertices of poly inside ring and >= margin from its edges."""
    from common import inside, seg_dist
    for v in poly:
        if not inside(v, ring):
            return False
        if margin > 0 and min(seg_dist(v, ring[i - 1], ring[i])[0] for i in range(len(ring))) < margin:
            return False
    return True


def line_poly_clear(poly, pl, dist):
    """True if every vertex and edge midpoint of poly is >= dist from polyline pl."""
    pts = list(poly) + [((poly[i][0] + poly[i - 1][0]) / 2, (poly[i][1] + poly[i - 1][1]) / 2) for i in range(len(poly))]
    pts.append((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
    return all(nearest_on(pl, p)[0] >= dist for p in pts)


def measure_profile(ref, rgb, tol, pad=6.0, frac=0.4):
    """Bbox (world m) of the drawn object of colour rgb near the expected bbox ref on the FINAL render: columns / rows whose share of
    matching pixels (inside the expected extent of the other axis) exceeds frac. Robust to labels, ribs and outlines."""
    a = full()
    x0, y0, x1, y1 = ref[0] - pad, ref[1] - pad, ref[2] + pad, ref[3] + pad
    sub = a[int((950 - y1) * 5):int((950 - y0) * 5), int(x0 * 5):int(x1 * 5)]
    m = np.abs(sub - np.array(rgb)).max(axis=2) <= tol
    r0, r1 = int((y1 - ref[3]) * 5), int((y1 - ref[1]) * 5)
    c0, c1 = int((ref[0] - x0) * 5), int((ref[2] - x0) * 5)
    cols = np.nonzero(m[r0:r1, :].mean(axis=0) > frac)[0]
    rows = np.nonzero(m[:, c0:c1].mean(axis=1) > frac)[0]
    if len(cols) == 0 or len(rows) == 0:
        return None
    return (x0 + cols.min() / 5.0, y1 - (rows.max() + 1) / 5.0, x0 + (cols.max() + 1) / 5.0, y1 - rows.min() / 5.0)


def mprof(poly, seed, tol, frac=0.4, pad=6.0):
    return measure_profile(bbox(poly), tuple(int(v) for v in px(*seed)), tol, pad, frac)


def centre_of(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def bbox(poly):
    return (min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly))


def resid(meas, ref):
    """max |edge difference| (m) between two bboxes and centre shift."""
    if meas is None:
        return None
    e = max(abs(meas[i] - ref[i]) for i in range(4))
    c = ((meas[0] + meas[2] - ref[0] - ref[2]) / 2, (meas[1] + meas[3] - ref[1] - ref[3]) / 2)
    return round(e, 2), (round(c[0], 2), round(c[1], 2))


class Log:
    def __init__(self, tag):
        self.tag, self.fixes, self.qs = tag, [], []

    def fix(self, where, ru, why):
        self.fixes.append({'id': '%s-%02d' % (self.tag, len(self.fixes) + 1), 'where': rnd2(where), 'ru': ru, 'why_ru': why})

    def q(self, ru, options, default, applied):
        self.qs.append({'id': '%s-q%d' % (self.tag, len(self.qs) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


def bld(bid, kind, slot, poly, h, roof, walls, notes, floors=1, fh=None, ents=(), tint=None, sockets=None, **kw):
    b = {'id': bid, 'kind': kind, 'material_slot': slot, 'footprint': Rccw(poly), 'floors': floors, 'floor_h_m': round(fh or h / floors, 2),
         'height_m': h, 'roof': roof, 'walls': walls, 'tint': tint, 'entrances': list(ents), 'facade_kit': 'none',
         'sockets': sockets or {'windows': True}, 'collider': 'full_roof', 'disabled': False, 'notes': notes}
    b.update(kw)
    return b


def prop(pid, kind, pos, rot=0.0, size=None, grip=False, **kw):
    p = {'id': pid, 'kind': kind, 'pos': rnd2(pos), 'rot_deg': round(rot, 1), 'size': size, 'grip_anchor': grip}
    p.update(kw)
    return p


# ============================================================================================ 09 City Beach
# build_world_v85.py constants (pre-shift metres; world = common.post = +(20, -28) over the whole beach x > 770, y < 470)
PARK_TOP, PARK_BOT, DUNE_BOT = 246.3, 229.0, 221.0
LOTS = [(902.0, 936.0), (1149.0, 1183.0)]
X0B, X1B = 786.0, 1240.0
STREETS = (895.0, 1012.0, 1142.0)
VAN_IN = (895.0, 1142.0)
PIER_X = 1012.0
TOWERS = [(905.0, 191.0), (1150.0, 196.0)]                               # v85: one at each van entry onto the sand
BARS = (955.0, 1068.0)
VOLLEY = (1100.0, 1124.0)
COAST_B = [(642, 62), (650, 76), (654, 90), (664, 116), (684, 146), (712, 168), (750, 182), (800, 186), (860, 178), (900, 170), (960, 163),
           (1020, 157), (1060, 161), (1100, 169), (1140, 178), (1190, 186), (1225, 191), (1255, 186), (1290, 188), (1330, 197), (1370, 207),
           (1410, 215), (1450, 224), (1482, 236), (1502, 250), (1512, 266)]
SAND_TOP = [(X0B - 12, PARK_TOP + 2), (1262, PARK_TOP + 2), (1282, 252), (1300, 259), (1322, 264), (1350, 268), (1400, 272), (1440, 276),
            (1468, 270), (1494, 264), (1506, 262)]
TRACK_DRAWN = [(1142, 214), (1190, 216), (1240, 226), (1290, 238), (1340, 248), (1390, 254), (1430, 257), (1452, 255)]   # build_world_v85 TRACK (v84)
TRACK_PTS = [(1142, 214), (1190, 215), (1225, 216.5), (1248, 221.5), (1270, 230), (1290, 238), (1340, 248), (1390, 254), (1430, 257), (1452, 255)]   # below the dune end
FOOT_B = [(1236, 238), (1262, 244), (1282, 248), (1300, 254), (1322, 259), (1350, 263), (1400, 267), (1440, 270), (1466, 265)]
CABANA = (1406.0, 242.0, 1418.0, 250.0)
BACK_Y = 207.0                                                           # rear van strip along the dunes (centre), 6 m wide
VAN_STRIP_W = 6.0
ENTRY_W = 9.2                                                            # drawn van entry (46 SVG units)
UMB_KINDS = [('umbrella_towel', 12), ('lounger_1', 12), ('umbrella_2_loungers', 20), ('loungers_2', 20), ('umbrella_1_lounger', 2),
             ('umbrella_3_loungers', 2)]                                 # layout v06 umbrella_sets kinds u0/l1/u2/l2/u1/u3 = 68


BEACH_DY = 0.0 if REV == 'v01' else -54.0       # Downtown plan v37: the city beach 54 m further south (same layout)
SHIFT_X = (700.0, 790.0, 1280.0, 1400.0)          # world x: taper in, full shift, taper out (Elite beach unchanged)


def beach_dy(x):
    """World dy of the v37 beach move at world x (0 for REV v01)."""
    if not BEACH_DY:
        return 0.0
    a, b, c, d = SHIFT_X
    if x <= a or x >= d:
        return 0.0
    if x < b:
        t = (x - a) / (b - a)
        return BEACH_DY * t * t * (3 - 2 * t)
    if x <= c:
        return BEACH_DY
    t = (x - c) / (d - c)
    return BEACH_DY * (1 - t * t * (3 - 2 * t))


def bpost(p):
    q = post(p)
    return (q[0], q[1] + beach_dy(q[0]))


post0 = post                                      # v85 position (render residuals are measured where the beach is DRAWN)


def P(p):
    return bpost(p)


def PL(pts):
    return [rnd2(bpost(p)) for p in pts]


def new_coast(step=4.0, x0=690.0, x1=1520.0):
    """Sea edge of the beach after the move (world polyline, west -> east)."""
    cb = chaikin(COAST_B, 3)
    out = []
    for q in cb:
        w = bpost(q)
        if x0 <= w[0] <= x1 and (not out or w[0] - out[-1][0] >= step):
            out.append((round(w[0], 2), round(w[1], 2)))
    return out


def beach_outline():
    """District 09 after the move: palm park + dunes + sand down to the waterline (world polygon, ccw)."""
    cb = chaikin(COAST_B, 3)
    top = [(X0B - 12, PARK_TOP)] + [(x, PARK_TOP) for x in np.arange(X0B, 1262.0, 8.0)] + SAND_TOP[1:]
    dense = []
    for a, b in zip(top[:-1], top[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 6.0))
        dense += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    dense.append(top[-1])
    def coast_at(x):
        for (ax, ay), (bx, by) in zip(cb[:-1], cb[1:]):
            if ax <= x <= bx:
                return ay + (by - ay) * (x - ax) / max(1e-6, bx - ax)
        return cb[-1][1]
    bottom = [(x, coast_at(x)) for x in np.arange(SAND_TOP[-1][0], X0B - 12.0, -6.0)] + [(X0B - 12, coast_at(X0B - 12))]
    return Rccw([bpost(p) for p in dense + bottom])


def beach():
    post = bpost                                                         # v37: whole beach moved (beach_dy); v01: identity
    lg = Log('beach')
    src = load(BEACH_JSON)
    cb = chaikin(COAST_B, 3)

    def coast_at(x):
        for (ax, ay), (bx, by) in zip(cb[:-1], cb[1:]):
            if ax <= x <= bx:
                return ay + (by - ay) * (x - ax) / max(1e-6, bx - ax)
        return cb[-1][1]

    blds, props, zones = [], [], []
    # ---------------------------------------------------------------- surfaces
    sand = SAND_TOP + [(1506, coast_at(1506))] + [p for p in cb[::-1] if X0B - 12 < p[0] < 1506] + [(X0B - 12, coast_at(X0B - 12))]
    zones.append({'id': '09-sand', 'kind': 'sand', 'poly': Rccw([post(p) for p in sand]), 'surface': 'sand_white', 'color': '#F7F2E0', 'layer': 0,
                  'notes': 'white Miami sand (v10 §7.9, BEACH_SPEC §2a); slightly uneven; wet sand 1.5 m at the waterline, foam; '
                           'extends east along the Elite hill foot to the Elite beach (v74). West edge x %.0f = transition to the sand arc / Quiet valley rocks.' % post((X0B - 12, 0))[0]})
    zones.append({'id': '09-waterline', 'kind': 'shoreline', 'line': PL([p for p in cb if X0B - 20 < p[0] < 1512]), 'wet_sand_m': 1.5,
                  'notes': 'sea polygon edge of the v85 drawing (coast_b, chaikin x3)'})
    zones.append({'id': '09-park', 'kind': 'palm_park', 'poly': Rccw(PL(rect(X0B, PARK_BOT, X1B, PARK_TOP))), 'surface': 'lawn', 'layer': 2,
                  'notes': 'palm park ~17 m between the embankment street and the dunes; hides the sea from the city; trees = the 2 designed palm rows only (props)'})
    path = chaikin([(X0B + 4, 240)] + [(x, 240 + 6 * math.sin((x - X0B) / 31.0)) for x in range(int(X0B) + 20, int(X1B) - 10, 20)] + [(X1B - 4, 240)], 2)
    zones.append({'id': '09-park-path', 'kind': 'path', 'line': PL(path), 'width_m': 3.6, 'surface': 'sidewalk_S1', 'notes': 'winding promenade path through the palm park'})
    dune_poly = [(X0B, PARK_BOT), (X1B, PARK_BOT)] + [(x, DUNE_BOT + 1.5 * math.sin(x / 9.0)) for x in range(int(X1B), int(X0B) - 1, -6)]
    zones.append({'id': '09-dunes', 'kind': 'dunes', 'poly': Rccw(PL(dune_poly)), 'surface': 'sand_white', 'layer': 1, 'shrubs': True,
                  'notes': 'low dunes with beach grass and bushes; crossed only by the boardwalks, the pier square boardwalk and the 2 van entries'})
    zones.append({'id': '09-veg-dunes', 'kind': 'veg_zone', 'poly': Rccw(PL(dune_poly)), 'density': 'sparse', 'species': 'bush',
                  'notes': 'bushes / beach grass + a few palm groups of 1-3 (BEACH_SPEC §2a); keep the boardwalks and van entries clear'})
    for k, (l0, l1) in enumerate(LOTS):
        zones.append({'id': '09-parking-%d' % k, 'kind': 'parking', 'poly': Rccw(PL(rect(l0, 231.0, l1, 247.5))), 'surface': 'asphalt_A5d12', 'layer': 3,
                      'stall_w_m': 3.0, 'stall_rows_y': [round(post((l0, y))[1], 2) for y in (243.5, 235.0)], 'stalls': 2 * int((l1 - l0) / 3.0),
                      'notes': 'beach parking as drawn (next to the van entry %s), stalls N-S, white lines; access from the embankment street' % ('W' if k == 0 else 'E')})
    zones.append({'id': '09-pier-square', 'kind': 'plaza', 'poly': Rccw(PL(rect(PIER_X - 14, PARK_BOT, PIER_X + 14, PARK_TOP))), 'surface': 'plaza_M3', 'layer': 3,
                  'notes': 'square at the central street (x %.0f) with the boardwalk to the beach; no palms on it' % post((PIER_X, 0))[0]})
    zones.append({'id': '09-boardwalk-main', 'kind': 'boardwalk', 'line': PL([(PIER_X, PARK_BOT), (PIER_X, DUNE_BOT - 4)]), 'width_m': 6.0, 'surface': 'boards_pier_SK5a_v02'})
    for x in range(int(X0B) + 30, int(X1B) - 20, 55):
        if any(abs(x - sx) < 20 for sx in STREETS):
            continue
        zones.append({'id': '09-dune-walk-%d' % x, 'kind': 'boardwalk', 'line': PL([(x, PARK_BOT + 1), (x, DUNE_BOT - 3)]), 'width_m': 2.4,
                      'surface': 'boards_pier_SK5a_v02', 'anchors': ['shower', 'bin'], 'notes': 'wooden walk over the dunes; shower + bin at the sand end'})
    # ---------------------------------------------------------------- van: entries, free strips (BEACH_SPEC §2a), rut track to the Elite beach (v10 §7.7)
    for sx in VAN_IN:                                                    # street asphalt ends at pre y 249.5: entry starts 0.5 m on it
        zones.append({'id': '09-van-entry-%d' % int(post((sx, 0))[0]), 'kind': 'van_entry_sand', 'line': PL([(sx, 250.0), (sx, DUNE_BOT - 6)]),
                      'width_m': ENTRY_W, 'surface': 'sand_ruts', 'van_drive': True, 'world_road': False,
                      'notes': 'van entry from the end of the city street onto the sand (drawn 9.2 m); kerb lowered at the street; nothing stands on it'})
    for sx in VAN_IN:
        zones.append({'id': '09-van-corridor-%d' % int(post((sx, 0))[0]), 'kind': 'van_route', 'line': PL([(sx, DUNE_BOT - 6), (sx, coast_at(sx) + 3.0)]),
                      'width_m': 8.0, 'surface': 'sand_white', 'keep_clear': True, 'notes': 'corridor from the entry to the water (BEACH_SPEC §2a)'})
    wl = [(x, coast_at(x) + 6.0) for x in range(800, 1236, 8)]
    zones.append({'id': '09-van-strip-water', 'kind': 'van_route', 'line': PL(wl), 'width_m': VAN_STRIP_W, 'surface': 'sand_white', 'keep_clear': True,
                  'notes': 'strip along the waterline (coast + 3..9 m), passes landward of the pier root'})
    zones.append({'id': '09-van-strip-back', 'kind': 'van_route', 'line': PL([(815, BACK_Y), (1218, BACK_Y)]), 'width_m': VAN_STRIP_W, 'surface': 'sand_white',
                  'keep_clear': True, 'notes': 'rear strip along the dunes, south of the two bars; links both entries'})
    track = chaikin(TRACK_PTS, 3)
    zones.append({'id': '09-van-track-elite', 'kind': 'track', 'line': PL(track), 'width_m': 5.0, 'surface': 'sand_ruts', 'world_road': True, 'van_drive': True,
                  'notes': 'two van ruts in the sand from the east van entry along the foot of the Elite hill to the Elite beach (v10 §7.7); never climbs the hill'})
    dmax = max(nearest_on(chaikin(TRACK_DRAWN, 3), q)[0] for q in track)
    lg.fix(post((1230, 218)), 'Колея бусика к пляжу Элиты обходит восточный край дюн по песку (x %.0f…%.0f, отход от рисунка до %.1f м), дальше — как нарисовано (v84)'
           % (post((1200, 0))[0], post((1270, 0))[0], dmax), 'на картинке колея срезает угол дюн и газона парка (x 1218…1240 до сдвига) — проезд бусика по кустам дюн')
    # ---------------------------------------------------------------- pier from the waterline (v83 / v10 §7.9)
    c_p = coast_at(PIER_X)
    pier = rect(PIER_X - 5, 112.0, PIER_X + 5, c_p)
    if abs(c_p - 161.0) > 0.5:
        lg.fix(post((PIER_X, c_p)), 'Начало пирса поставлено точно на кромку воды (y %.1f), на карте v85 — y %.1f' % (post((PIER_X, c_p))[1], post((PIER_X, 161))[1]),
               'v10 §7.9: пирс начинается от кромки воды; разница — рисованная (прямоугольник поверх мокрого песка)')
    zones.append({'id': '09-pier', 'kind': 'pier', 'poly': Rccw(PL(pier)), 'surface': 'boards_pier_SK5a_v02', 'deck_h_m': 1.2, 'pile_step_m': 4.0, 'railing': True,
                  'fishermen': src['pier'].get('fishermen', 15), 'length_m': round(c_p - 112.0, 1),
                  'notes': 'wooden pier 10 m wide (as drawn), starts AT the waterline (abutment on the wet sand), ~%.0f m into the sea + head platform; fishermen with rods' % (c_p - 112.0)})
    zones.append({'id': '09-pier-head', 'kind': 'pier', 'poly': Rccw(PL(rect(PIER_X - 15, 100.0, PIER_X + 15, 112.0))), 'surface': 'boards_pier_SK5a_v02',
                  'deck_h_m': 1.2, 'pile_step_m': 4.0, 'railing': True, 'notes': 'head platform 30 x 12 m'})
    zones.append({'id': '09-swim-zone', 'kind': 'swim_zone', 'line': PL([(PIER_X - 70, coast_at(PIER_X - 70) - 1), (PIER_X - 70, 135), (PIER_X + 70, 135),
                                                                           (PIER_X + 70, coast_at(PIER_X + 70) - 1)]),
                  'notes': 'buoy line (layout v06 swim_zone, 150 m wide around the pier); jet skis outside'})
    # ---------------------------------------------------------------- oil splashes in the west (BEACH_SPEC §2a)
    oil_x = (790.0, 852.0)
    oil = [(x, coast_at(x)) for x in np.linspace(oil_x[1], oil_x[0], 7)] + [(oil_x[0], coast_at(oil_x[0]) + 22), (821, coast_at(821) + 17), (oil_x[1], coast_at(oil_x[1]) + 9)]
    zones.append({'id': '09-oil-spill', 'kind': 'oil_spill', 'poly': Rccw(PL(oil)), 'surface': 'sand_white', 'decal': 'OilTar',
                  'notes': 'splashes "from a brush": drops with fans of small spray, dense at the water, sparse inland; NOT one blot; no sunbathers here '
                           '(layout v06 oil_spill: %d main drops, west end near the Quiet valley)' % len(src['oil_spill']['drops_main'])})
    film = [(x, coast_at(x) - 1) for x in np.linspace(780, 862, 6)] + [(862, coast_at(862) - 13), (780, coast_at(780) - 15)]
    zones.append({'id': '09-oil-film', 'kind': 'oil_film_water', 'poly': Rccw(PL(film)), 'notes': 'light oily film on the water in front of the splashes'})
    # ---------------------------------------------------------------- buildings: 2 bars on the sand at the dunes, rental hut, Elite cabana
    bar_rects = []
    for i, bx in enumerate(BARS):
        r_ = rect(bx - 8, DUNE_BOT - 9, bx + 8, DUNE_BOT - 1)
        bar_rects.append(r_)
        blds.append(bld('09-bar-%s' % 'WE'[i], 'beach_bar', 'beach_bar', [post(p) for p in r_], 3.4,
                        {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3, 'striped_awning': True}, 'stucco_SK3b',
                        'pastel art-deco cocktail bar on the sand at the dune foot (BEACH_SPEC §2a "13"): striped roof / awning, counter facing the sea, '
                        'high stools, 2 tables with umbrellas on the sea side; %s' % ('west bar' if i == 0 else 'east bar, next to the volleyball courts'),
                        ents=[{'pos': rnd2(post((bx, DUNE_BOT - 9))), 'facing_deg': 270, 'kind': 'counter', 'w_m': 10.0}],
                        tint=('#F6C9C4', '#BFE7E4')[i], sockets={'awning': True, 'windows': False, 'storefront': True}))
    hut_c = (1190.0, coast_at(1190.0) + 13.0)
    hut = rrect(hut_c, 5.0, 4.0, 0)
    blds.append(bld('09-rental', 'rental_hut', 'beach_bar', [post(p) for p in hut], 2.8, {'type': 'flat', 'material': 'boards_SK5a'}, 'boards_SK5a',
                    'jet-ski / SUP rental hut by the water (layout v06 rental: 3 jet skis, 6 SUPs); east of the swim zone',
                    ents=[{'pos': rnd2(post((hut_c[0], hut_c[1] - 2))), 'facing_deg': 270, 'kind': 'door', 'w_m': 1.2}], tint='#F4EFE4'))
    blds.append(bld('09e-cabana', 'beach_bar', 'beach_bar', [post(p) for p in rect(*CABANA)], 3.0, {'type': 'flat', 'material': 'boards_SK5a', 'parapet_h_m': 0.0},
                    'boards_SK5a', 'Elite beach cabana bar (open canopy) under the hill; reached only by the sand track', tint='#F4EFE4', sub_area='elite_beach',
                    sockets={'awning': True, 'windows': False}))
    for k in range(src['rental']['jetskis']):
        props.append(prop('09-jetski%d' % k, 'jet_ski', post((1183.0 + 6 * k, coast_at(1183.0 + 6 * k) - 3)), 270, [3.2, 1.2, 1.1]))
    for k in range(src['rental']['sups']):
        props.append(prop('09-sup%d' % k, 'sup_board', post((hut_c[0] + 4.5 + 1.0 * k, hut_c[1])), 90, [0.8, 3.2, 0.2]))
    # ---------------------------------------------------------------- volleyball, lifeguard towers
    for i, cx in enumerate(VOLLEY):
        zones.append({'id': '09-volley-%d' % i, 'kind': 'volleyball', 'poly': Rccw(PL(rect(cx - 8, 186, cx + 8, 194))), 'surface': 'sand_white',
                      'net': PL([(cx, 185), (cx, 195)]), 'notes': '16 x 8 m court, posts + net + rope lines, side by side along the shore'})
    lg.q('Волейбольные площадки: на карте v85 стоят на востоке от пирса (рядом с восточным баром); в BEACH_SPEC §2а — «у западного кафе».',
         ['1 — оставить как на карте v85 (восток от пирса, у восточного бара)', '2 — перенести к западному бару (x ~%.0f), лежаки — на восток' % post((955, 0))[0]],
         1, 'данные: вариант 1 (как нарисовано на v85)')
    for k, (x, y) in enumerate(TOWERS):
        props.append(prop('09-lifeguard%d' % k, 'lifeguard_tower', post((x, y)), 270, [3.0, 3.0, 4.5], True,
                          material='boards_SK5a', tint=('#F4D35E', '#9BD08A')[k], solid=True,
                          notes='lifeguard tower facing the sea, at the %s van entry (v85: exactly 2)' % ('west' if k == 0 else 'east')))
    # ---------------------------------------------------------------- palms: 2 park rows 11 m (v84), bar palms, Elite foot row 11 m
    sq = (PIER_X - 14, PIER_X + 14)
    nfix_sq = 0
    for row, y in enumerate((244.0, 232.5)):
        for x in range(int(X0B) + 6 + (row % 2) * 5, int(X1B) - 4, 11):
            if any(abs(x - sx) < 10 for sx in STREETS) or abs(y - 240 - 6 * math.sin((x - X0B) / 31.0)) < 5.0 or any(l0 - 4 < x < l1 + 4 for l0, l1 in LOTS):
                continue
            if sq[0] - 2 <= x <= sq[1] + 2:                               # drawn rule (|x - street| < 10) leaves palms on the pier square
                nfix_sq += 1
                continue
            props.append(prop('09-palm-park-%d-%d' % (row, x), 'palm', post((x, y)), 0, [4.0, 4.0, 9.0], row='park_%s' % ('north' if row == 0 else 'south')))
    if nfix_sq:
        lg.fix(post((PIER_X, 238)), 'Убрано пальм ряда парка на площади у пирса: %d (площадь x %.0f…%.0f)' % (nfix_sq, post((sq[0], 0))[0], post((sq[1], 0))[0]),
               'правило картинки отступает от улицы только на 10 м, а площадь шире (28 м) — дерево на мощёной площади')
    bar_palms = [((947, 214), (941, 214)), ((963, 214), (969, 214)), ((1060, 214), (1054, 214)), ((1076, 214), (1082, 214)), ((800, 205), (800, 205)), ((1235, 204), (1235, 204))]
    for (o, n) in bar_palms:
        props.append(prop('09-palm-bar-%d' % n[0], 'palm', post(n), 0, [4.5, 4.5, 10.0], row='single'))
    lg.fix(post((1012, 214)), 'Пальмы у баров вынесены за стены баров: x %s -> %s (y %.0f)' % ('/'.join('%.0f' % post(o)[0] for o, n in bar_palms[:4]),
           '/'.join('%.0f' % post(n)[0] for o, n in bar_palms[:4]), post((950, 214))[1]),
           'на картинке ствол пальмы стоит на углу бара (внутри контура 16 x 8 м)')
    acc, k = 0.0, 0
    for (ax, ay), (bx, by) in zip(FOOT_B[:-1], FOOT_B[1:]):
        L = math.hypot(bx - ax, by - ay)
        while acc < L:
            u = acc / L
            props.append(prop('09e-palm-foot-%02d' % k, 'palm', post((ax + (bx - ax) * u, ay + (by - ay) * u)), 0, [4.0, 4.0, 9.0], row='elite_foot', sub_area='elite_beach'))
            acc += 11.0
            k += 1
        acc -= L
    for o, n in (((1404, 252), (1400, 246)), ((1421, 252), (1422, 248.5)), ((1490, 262), (1490, 262))):
        props.append(prop('09e-palm-cabana-%d' % n[0], 'palm', post(n), 0, [4.5, 4.5, 10.0], row='single', sub_area='elite_beach'))
    lg.fix(post((1410, 252)), 'Две пальмы у кабаны Элиты сдвинуты с колеи бусика: %s' % ', '.join('(%.0f, %.0f) -> (%.0f, %.1f)' % (post(o) + post(n)) for o, n in
                                                                         (((1404, 252), (1400, 246)), ((1421, 252), (1422, 248.5)))),
           'на картинке пальма в 0,5 м от края колеи 5 м — дерево на проезде; v10 §1.2: от края дороги не ближе ~2 м')
    # ---------------------------------------------------------------- 68 umbrella sets scattered (BEACH_SPEC §2a, layout v06 kinds)
    blocked = [rect(x - 8 - 3, 186 - 3, x + 8 + 3, 194 + 3) for x in VOLLEY] + [rect(x - 5.5, y - 5.5, x + 5.5, y + 5.5) for x, y in TOWERS]
    blocked += [rect(r_[0][0] - 3, r_[0][1] - 3, r_[2][0] + 3, r_[2][1] + 3) for r_ in bar_rects] + [rect(hut_c[0] - 6, hut_c[1] - 5, hut_c[0] + 13, hut_c[1] + 5), rect(1219, 198, 1243, 212)]
    cands = []
    for row, d in enumerate((12.0, 17.5, 23.0, 28.5, 34.0, 39.5)):
        for x0 in np.arange(812.0 + (row % 2) * 3.5, 1228.0, 7.0):
            cid = 'r%d_%d' % (row, int(x0 * 10))
            x = x0 + (h01(cid + 'x') - 0.5) * 3.0
            y = coast_at(x) + d + (h01(cid + 'y') - 0.5) * 2.4
            if y > BACK_Y - VAN_STRIP_W / 2 - 2.5 or x < oil_x[1] + 8:
                continue
            if any(abs(x - sx) < 4 + 3.5 for sx in VAN_IN) or abs(x - PIER_X) < 6:
                continue
            if any(r_[0][0] <= x <= r_[2][0] and r_[0][1] <= y <= r_[2][1] for r_ in blocked):
                continue
            w = 0.35 + 0.65 * math.exp(-((x - PIER_X) / 140.0) ** 2)
            cands.append((h01(cid + 's') / w, cid, x, y))
    cands.sort()
    chosen = []
    for s_, cid, x, y in cands:
        if all(math.hypot(x - c[1], y - c[2]) >= 4.8 for c in chosen):
            chosen.append((cid, x, y))
        if len(chosen) == sum(n for _, n in UMB_KINDS):
            break
    kinds = [k_ for k_, n in UMB_KINDS for _ in range(n)]
    order = sorted(range(len(chosen)), key=lambda i: h01(chosen[i][0] + 'k'))
    for j, i in enumerate(order):
        cid, x, y = chosen[i]
        props.append(prop('09-umb-%02d' % j, kinds[j], post((x, y)), 270 + (h01(cid + 'r') - 0.5) * 40, None,
                          umbrella=kinds[j].startswith('umbrella'), umbrella_color=('#4F8FD8', '#F2C14E', '#E86F5C', '#FFFFFF', '#6CC3A0')[int(h01(cid + 'c') * 5) % 5]))
    lg.fix(post((1012, 205)), 'Лежаки: вместо 4 ровных блоков у дюн (54 шт. на картинке) — %d наборов вразброс, гуще к центру, ряды угадываются, '
           'наборы по плану v06 (зонт+полотенце 12, 1 лежак 12, зонт+2 лежака 20, 2 лежака 20, зонт+1 2, зонт+3 2)' % len(chosen),
           'BEACH_SPEC §2а и v02 §8.9 («не ровные ряды», ~70 наборов, зонт у половины); блоки картинки стояли на задней полосе бусика вдоль дюн')
    lg.fix(post((1012, 180)), 'Проезды бусика по песку заданы явно (2 коридора к воде, полоса у воды, задняя полоса у дюн, колея к Элите) — на них ничего не стоит',
           'BEACH_SPEC §2а; полотенца/зонтики-точки картинки (60 + 18 шт.) не переносятся — мелочи ставит s06 вне проездов')
    for k_, x in enumerate(range(1424, 1484, 8)):                             # Elite beach: two rows at the water, as drawn
        for j, off in enumerate((9.0, 17.0)):
            props.append(prop('09e-lounger-%02d-%d' % (k_, j), 'lounger_umbrella_elite', post((x + 4 * j, coast_at(x + 4 * j) + off)), 270, None,
                              umbrella=True, umbrella_color=('#1F3B57', '#FFFFFF', '#C9A86A')[(k_ + j) % 3], sub_area='elite_beach'))
    if BEACH_DY:                                                         # Fedya 22.10 (W86 item 14): Elite beach - catching allowed, guard patrol
        cab = rect(*CABANA)
        lng = [pp['pos'] for pp in props if pp['kind'] == 'lounger_umbrella_elite']
        sea_ = [(x, coast_at(x) + 5.0) for x in (1392.0, 1416.0, 1440.0, 1464.0, 1488.0)]
        land_ = [(1488.0, min(coast_at(1488.0) + 22.0, 262.0))] + [(x, CABANA[3] + 4.0 + (2.0 if x > 1450 else 0.0)) for x in (1460.0, 1430.0, 1400.0)]
        # landward leg behind the lounger rows and 4 m behind (north of) the cabana, along the van ruts
        loop = [post(q) for q in sea_ + land_]
        clr_cab = min(math.hypot(px_ - min(max(px_, post(cab[0])[0]), post(cab[2])[0]), py_ - min(max(py_, post(cab[0])[1]), post(cab[2])[1]))
                      for px_, py_ in (q for a, b in zip(loop, loop[1:] + loop[:1]) for q in resample([a, b], 1.0)))
        clr_lng = min(math.hypot(q[0] - l[0], q[1] - l[1]) for a, b in zip(loop, loop[1:] + loop[:1]) for q in resample([a, b], 1.0) for l in lng)
        L = sum(math.dist(a, b) for a, b in zip(loop, loop[1:] + loop[:1]))
        zones.append({'id': '09e-guard-patrol', 'kind': 'patrol_route', 'sub_area': 'elite_beach', 'loop': [rnd2(q) for q in loop], 'closed': True,
                      'length_m': round(L, 1), 'guards': 2, 'guard_kind': 'elite_guard', 'phases': [0.0, 0.5], 'speed_mps': 1.3,
                      'waits': [{'waypoint': 0, 's': 6}, {'waypoint': 4, 's': 6}, {'waypoint': 7, 's': 4}],
                      'catching_allowed': True, 'clear_m': {'cabana': round(clr_cab, 1), 'loungers': round(clr_lng, 1)},
                      'notes': 'Elite beach under the hill, outside the village fence (Fedya 22.10): NPC may be caught here, but 2 guards walk this loop '
                               '(opposite phase, ~%.0f s per lap): seaward leg 5 m above the waterline, landward leg behind the lounger rows and behind '
                               'the cabana (along the van ruts). Patrol behaviour (vision, alarm to the Elite gate guards) = gameplay code; this is the map data.' % (L / 1.3)})
        for k_, q in enumerate((loop[0], loop[len(sea_)])):
            props.append(prop('09e-guard-spawn%d' % (k_ + 1), 'npc_spot', q, 270, [0.6, 0.6, 1.8], role='elite_guard', patrol='09e-guard-patrol',
                              sub_area='elite_beach', notes='patrol start (phase %.1f)' % (0.5 * k_)))
        lg.fix(loop[0], 'Решение Феди 22.10 (W86 п. 14): на пляже Элиты ловить можно, но там ходит патруль охраны — маршрут 09e-guard-patrol '
                        '(%d точек, %.0f м, 2 охранника в противофазе).' % (len(loop), L), 'Элита остаётся опасной: риск и награда.')
    # ---------------------------------------------------------------- vegetation rules
    zones.append({'id': '09-no-tree-sand', 'kind': 'no_tree', 'poly': Rccw(PL([(806, DUNE_BOT - 1)] + [(x, coast_at(x)) for x in range(806, 1229, 8)] + [(1228, DUNE_BOT - 1)])),
                  'why': 'sand: van drives, loungers, courts'})
    zones.append({'id': '09-no-tree-park', 'kind': 'no_tree', 'poly': Rccw(PL(rect(X0B, PARK_BOT, X1B, PARK_TOP))), 'why': 'palm park: only the 2 designed palm rows (props)'})
    zones.append({'id': '09-grove-W', 'kind': 'veg_zone', 'poly': Rccw(PL(rect(786, 197, 806, 220))), 'density': 'grove', 'species': 'palm',
                  'notes': 'small palm grove at the west edge of the sand (BEACH_SPEC §2a); keep the water strip free'})
    zones.append({'id': '09-grove-E', 'kind': 'veg_zone', 'poly': Rccw(PL(rect(1222, 200, 1240, 209))), 'density': 'grove', 'species': 'palm',
                  'notes': 'small palm grove at the east edge of the sand (BEACH_SPEC §2a), between the van strips and the track (>= 4 m from both)'})
    # ---------------------------------------------------------------- checks + residuals on the v85 render
    pp = [p for p in props if p['kind'] == 'palm']
    min_palm = min(math.hypot(a['pos'][0] - b['pos'][0], a['pos'][1] - b['pos'][1]) for i, a in enumerate(pp) for b in pp[i + 1:])
    trk = [rnd2(post(p)) for p in track]
    palm_track = min(nearest_on(trk, p['pos'])[0] for p in pp) - 2.5
    umb = [p for p in props if p['id'].startswith('09-umb')]
    strips = [z for z in zones if z['kind'] in ('van_route', 'van_entry_sand')]
    umb_strip = min(nearest_on(z['line'], p['pos'])[0] - z['width_m'] / 2 for z in strips for p in umb)
    pier_w = [post(p) for p in pier]
    post = post0                                                         # residuals: where the beach is drawn on the v85 render
    meas = {
        'pier+head (drawn from y 161 pre)': resid(mprof([post(p) for p in rect(PIER_X - 15, 100, PIER_X + 15, 161)], post((PIER_X, 140)), 14, 0.15), bbox([post(p) for p in rect(PIER_X - 15, 100, PIER_X + 15, 161)])),
        'tower_W': resid(mprof([post(p) for p in rrect(TOWERS[0], 6, 6, 0)], post(TOWERS[0]), 20), bbox([post(p) for p in rrect(TOWERS[0], 6, 6, 0)])),
        'tower_E': resid(mprof([post(p) for p in rrect(TOWERS[1], 6, 6, 0)], post(TOWERS[1]), 20), bbox([post(p) for p in rrect(TOWERS[1], 6, 6, 0)])),
        'bar_W': resid(mprof([post(p) for p in bar_rects[0]], post((951, 217)), 8), bbox([post(p) for p in bar_rects[0]])),
        'bar_E': resid(mprof([post(p) for p in bar_rects[1]], post((1064, 217)), 8), bbox([post(p) for p in bar_rects[1]])),
        'lot_W': resid(mprof([post(p) for p in rect(902, 231, 936, 247.5)], post((919, 239.3)), 6), bbox([post(p) for p in rect(902, 231, 936, 247.5)])),
        'lot_E': resid(mprof([post(p) for p in rect(1149, 231, 1183, 247.5)], post((1166, 239.3)), 6), bbox([post(p) for p in rect(1149, 231, 1183, 247.5)])),
    }
    wl_meas = []
    for x in (850, 950, 1012, 1080, 1180):
        wx, wy = post((x, coast_at(x)))
        ys = [wy + d / 5.0 for d in range(-40, 41)]
        flips = [y for y in ys if is_water(px(wx, y)) and not is_water(px(wx, y + 0.2))]
        wl_meas.append(round(min((y - wy for y in flips), key=abs), 2) if flips else None)
    post = bpost
    fit = {'transform': 'world = common.post(pre-shift metres of build_world_v85.py) = pre + (20, -28) on the whole beach (x > 770, y < 470)'
                        + ('' if not BEACH_DY else '; then plan v37 move: y += beach_dy(x) = %.0f m for x %.0f-%.0f, smooth taper to 0 at x %.0f / %.0f '
                           '(residuals below are measured at the v85 drawn position, before the move)' % (BEACH_DY, SHIFT_X[1], SHIFT_X[2], SHIFT_X[0], SHIFT_X[3])),
           'residuals_m (max bbox edge diff, centre shift)': meas, 'waterline_drawn_minus_coast_b_m': wl_meas}
    if BEACH_DY:
        lg.fix(post((PIER_X, 200)), 'План Даунтауна v37 (Вадим 22.10): пляж один в один с карты v85, сдвинут на %.0f м к югу (город вырос вверх и вниз). '
               'Сдвиг целиком для x %.0f-%.0f, плавный переход к 0 у скал Тихой долины (x %.0f) и у пляжа Элиты (x %.0f): колея бусика к Элите идёт '
               'по песку наискосок, как на картинке v37.' % (-BEACH_DY, SHIFT_X[1], SHIFT_X[2], SHIFT_X[0], SHIFT_X[3]),
               'Набережная SP Даунтауна v37 на 54 м южнее старой S1; суша на месте бывшего моря — land_override в out_v02/downtown_v37_land.json.')
    counts = {'buildings': len(blds), 'palms_park': sum(1 for p in pp if p.get('row', '').startswith('park')), 'palms_single': sum(1 for p in pp if p.get('row') == 'single'),
              'palms_elite_foot': sum(1 for p in pp if p.get('row') == 'elite_foot'), 'umbrella_sets': len(umb),
              'umbrella_sets_with_umbrella': sum(1 for p in umb if p['umbrella']), 'elite_loungers': sum(1 for p in props if p['kind'] == 'lounger_umbrella_elite'),
              'lifeguard_towers': sum(1 for p in props if p['kind'] == 'lifeguard_tower'), 'volleyball': 2, 'parking_lots': 2,
              'parking_stalls': sum(z['stalls'] for z in zones if z['kind'] == 'parking'), 'zones': len(zones), 'props': len(props)}
    checks = {'min_palm_spacing_m': round(min_palm, 2), 'min_palm_to_track_edge_m': round(palm_track, 2), 'min_umbrella_set_to_van_strip_edge_m': round(umb_strip, 2),
              'pier_start_y': round(pier_w[3][1], 2), 'pier_start_on_coast': True}
    return {'district': 'beach', 'version': 'v85 (placement: world v85 drawing; content: plan v06 + BEACH_SPEC)' + (' + Downtown v37 move %.0f m' % BEACH_DY if BEACH_DY else ''),
            'shift_v37': {'dy_m': BEACH_DY, 'x_taper_full_full_taper': list(SHIFT_X), 'rule': 'world y += beach_dy(x), smoothstep tapers'} if BEACH_DY else None,
            'sources': [rel(BUILD) + ' (R45_miami_beach, R38_ocean_drive, R74_elite_ring TRACK)', rel(BEACH_JSON), rel(BEACH_PNG), 'docs/specs/BEACH_SPEC_2026-10-15_v01.md',
                        'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §7.7 §7.9', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.9'],
            'transform': fit['transform'], 'fit': fit, 'pad_height_m': None, 'pad_note': 'sand slopes gently from the dunes (~+2.5 m) to the waterline (0 m)',
            'abs_heights': False, 'lighting': 'sunny_bright_miami', 'buildings': blds, 'props': props, 'zones': zones,
            'fixed_by_logic': lg.fixes, 'questions_for_vadim': lg.qs, 'counts': counts, 'checks': checks,
            'notes': 'ids 09e-* = the Elite beach under the hill (cabana, loungers, foot palm row) reached by the van track; drop them if the Elite file also carries them. '
                     'Small details for s06: showers + bins at the dune boardwalks, scooters (2 at the west bar, 2 at the embankment, 1 at the east bar), towels at the water.'}


# ============================================================================================ 06 Industrial Port
PORT_SHAPE = [(1178, 672), (1176, 611), (1191, 599), (1320, 598), (1341, 609), (1352, 637), (1344, 664), (1325, 677), (1191, 679)]
PIER_PORT = [(1274, 677), (1298, 677), (1300, 714), (1290, 721), (1278, 716)]
PT0, PW0, PSC = (960.0, 634.0), (1197.2, 670.4), (1.25, 0.8)            # warehouse NW corner (v11) -> world; PORT_SCALE


def T(p):
    return (PW0[0] + PSC[0] * (p[0] - PT0[0]), PW0[1] + PSC[1] * (p[1] - PT0[1]))


def svg_lines(svg, gid, stroke):
    out = []
    for nm, at, M, gids, s, e in svg_tags(svg):
        if gids and gids[-1] == gid and nm == 'polyline' and attr(at, 'stroke') == stroke:
            out.append([u2w(*q) for q in points_of(at, M)])
    return out


def bridge_axis(svg):
    for pl in svg_lines(svg, 'L05b_bridges', '#5F666C'):
        if pl[0][0] > 1300:
            return pl
    raise RuntimeError('Tramduro bridge not found in L05b_bridges')


def shore_cut(axis):
    """Cut the drawn bridge axis to the water: start = first axis point with water on both sides (+-7 m), end = island shore."""
    rs = resample(axis, 0.5)
    wet = []
    for i in range(len(rs) - 1):
        a, b = rs[i], rs[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        wet.append(is_water(px(a[0] + nx * 7, a[1] + ny * 7)) and is_water(px(a[0] - nx * 7, a[1] - ny * 7)))
    i0 = wet.index(True)
    s0 = rs[i0]
    l0 = plen(rs[:i0 + 1])
    e = axis[-1]                                                        # extend along the last direction to the island land
    d = (axis[-1][0] - axis[-2][0], axis[-1][1] - axis[-2][1])
    L = math.hypot(*d)
    d = (d[0] / L, d[1] / L)
    k = 0
    while is_water(px(e[0] + d[0] * 0.2 * k, e[1] + d[1] * 0.2 * k)) and k < 100:
        k += 1
    e = (e[0] + d[0] * 0.2 * k, e[1] + d[1] * 0.2 * k)
    seg = [s0] + [p for k_, p in enumerate(axis) if plen(axis[:k_ + 1]) > l0 + 0.05]
    if math.hypot(e[0] - seg[-1][0], e[1] - seg[-1][1]) > 0.05:
        seg.append(e)
    return seg, s0, e, i0


def nudge(poly, obstacles, ring, road_lines, clear, step=0.25, maxd=6.0):
    """Smallest axis-aligned shift that clears obstacles (gap 0.8 m), the road corridors and keeps the item in the yard."""
    def ok(pl):
        if ring is not None and not poly_inside(pl, ring, 0.8):
            return False
        if any(sat_overlap(pl, o, 0.8) for o in obstacles):
            return False
        return all(line_poly_clear(pl, ln, ROAD_W / 2 + clear) for ln in road_lines)
    if ok(poly):
        return poly, (0.0, 0.0)
    k = 1
    while k * step <= maxd:
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            d = (dx * k * step, dy * k * step)
            pl = [(p[0] + d[0], p[1] + d[1]) for p in poly]
            if ok(pl):
                return pl, d
        k += 1
    return poly, None


def port(svg):
    lg = Log('port')
    lay = load(PORT_JSON)
    w11 = {b['id']: b for b in load(WORLD11)['buildings'] if str(b['district']) == '06'}
    st11 = {s['id']: s for s in load(WORLD11)['structures'] if str(s.get('district')) == '06'}
    road_pl = svg_lines(svg, 'R84_port_road', '#5F666C')[0]
    corn = svg_lines(svg, 'R27_cornice_in_port', '#5F666C')[0]
    axis = bridge_axis(svg)
    bseg, s0, e_isl, _ = shore_cut(axis)
    # port road: R84 (smooth from the approach, through the yard) + the straight on to the shoreline where the bridge begins
    road = [p for p in road_pl] + [s0]
    # cornice VIEW C: last 15 m straight along x = 1263 (perpendicular), axis ends on the port road axis -> T
    xT = 1263.0 if abs(corn[-1][0] - 1263.0) < 1.0 else corn[-1][0]
    yT = road_pl[-1][1]
    cor = [p for p in corn if p[1] < yT - 15.0] + [(xT, yT - 15.0), (xT, yT)]
    dev = max(abs(p[0] - xT) for p in corn if p[1] >= yT - 15.0)
    blds, props, zones = [], [], []
    ring = [tuple(p) for p in PORT_SHAPE]
    roads = [road, cor]
    placed = []

    def place(poly, clear, name, where_ru, inside=True, group=None):
        new, d = nudge(poly, placed, ring if inside else None, roads, clear)
        if d is None:
            lg.fix(centre(poly), 'НЕ удалось развести «%s» без пересечения — оставлен как на плане' % where_ru, 'проверить вручную')
            new = poly
        elif d != (0.0, 0.0) and math.hypot(*d) > 0.3:
            nudges.append((name, where_ru, d, centre(poly)))
        placed.append(new)
        return new, (d or (0.0, 0.0))
    nudges = []

    def centre(pl):
        return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))
    # ---------------------------------------------------------------- buildings (plan sizes at T centres)
    wh = w11['06_02_warehouse']['footprint_m']
    whb = bbox(wh)
    wc = T(((whb[0] + whb[2]) / 2, (whb[1] + whb[3]) / 2))
    wpoly, d = place(rrect(wc, whb[2] - whb[0], whb[3] - whb[1], 0), 3.0, 'warehouse', 'склад 02')
    wb = bbox(wpoly)
    ents = [{'pos': rnd2((wc[0] + d[0] + dx, wb[1])), 'facing_deg': 270, 'kind': 'rollshutter', 'w_m': 5.0} for dx in (-15.0, 0.0, 15.0)]
    blds.append(bld('06-02-warehouse', 'warehouse', 'port_warehouse', wpoly, 9.6, {'type': 'flat', 'material': 'roof_profsheet_SK4c', 'parapet_h_m': 0.3},
                    'facade_warehouse', 'warehouse 02, corrugated metal, 50 x 24 m (plan v03 / WORLD_MAP_v11), 3 roll-shutters onto the loading apron; '
                    'no interior required', floors=1, fh=9.6, ents=ents, sockets={'windows': True, 'ribbed_walls': True}))
    lyb = bbox(st11['06_loading_yard']['polygon_m'])
    apron = rect(wb[0] + (whb[2] - whb[0] - (lyb[2] - lyb[0])) / 2, wb[1] - (lyb[3] - lyb[1]), wb[0] + (whb[2] - whb[0] + (lyb[2] - lyb[0])) / 2, wb[1])
    zones.append({'id': '06-09-loading-apron', 'kind': 'loading_pad', 'poly': Rccw(apron), 'surface': 'concrete_SK3c',
                  'notes': 'light concrete loading apron in front of the warehouse (plan v03 34 x 8 m); pallets / forklifts; no trees, no details on it'})
    placed.append(apron)
    for tid in ('06_05_tank_1', '06_05_tank_2'):
        fb = bbox(w11[tid]['footprint_m'])
        c = T(((fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2))
        r_ = (fb[2] - fb[0]) / 2
        tp, d = place(ellipse(c, r_, r_, 24), 3.0, tid, 'бак 05')
        c = centre(tp)
        blds.append(bld('06-05-tank%s' % tid[-1], 'storage_tank', 'port_tank', tp, 10.0, {'type': 'dome_low', 'material': 'metal_painted_SK6a'},
                        'metal_painted_SK6a', 'round fuel-oil tank 05, d %.1f m (plan size; the world picture draws it as an ellipse), ladder, bund' % (2 * r_),
                        sockets={'windows': False, 'ladder': True}, centre=rnd2(c), radius_m=round(r_, 2)))
    kb = bbox(w11['06_01_gate']['footprint_m'])
    kc = T(((kb[0] + kb[2]) / 2, (kb[1] + kb[3]) / 2))
    kpoly, d = place(rrect(kc, kb[2] - kb[0], kb[3] - kb[1], 0), 0.6, 'kpp', 'КПП 01')
    blds.append(bld('06-01-kpp', 'checkpoint_booth', 'port_booth', kpoly, 3.2, {'type': 'flat', 'material': 'roof_flat_SK4d'}, 'concrete_panel_SK3c',
                    'KPP 01 at the west entry, booth only - NO barrier (v02 §8.6); window to the road', ents=[{'pos': rnd2((centre(kpoly)[0], bbox(kpoly)[1])),
                                                                                                           'facing_deg': 270, 'kind': 'door', 'w_m': 0.9}]))
    sp = rect(946.0, 578.2, 949.7, 581.7)                                # plan v03 png: red square "08" (px 203..225 x 612..633, 6 px/m)
    spc = T(centre(sp))
    spoly, d = place(rrect(spc, 3.7, 3.5, 0), 1.0, 'service_post', 'сервисный пост 08')
    blds.append(bld('06-08-service-post', 'service_post', 'port_booth', spoly, 2.8, {'type': 'flat', 'material': 'roof_flat_SK4d'}, 'metal_painted_SK6a',
                    'service post 08 (red booth), next to the site cabin and the blue toilet', tint='#C9473F'))
    cab = lay['small']['site_cabin']
    cpoly, d = place(rrect(T(((cab[0] + cab[2]) / 2, (cab[1] + cab[3]) / 2)), cab[2] - cab[0], cab[3] - cab[1], 0), 1.0, 'site_cabin', 'бытовка 13')
    blds.append(bld('06-13-site-cabin', 'site_cabin', 'generic_container_cabin', cpoly, 2.6, {'type': 'flat', 'material': 'metal_painted_SK6a'}, 'metal_painted_SK6a',
                    'site cabin 13 (container hut)', tint='#E8E6DF'))
    ph = lay['pump_house']
    pc = T(((ph[0] + ph[2]) / 2, (ph[1] + ph[3]) / 2))
    ppoly, d = place(rrect(pc, ph[2] - ph[0], ph[3] - ph[1], 0), 3.0, 'pump_house', 'насосная')
    blds.append(bld('06-06-pump-house', 'pump_house', 'port_pump_house', ppoly, 3.4, {'type': 'gable', 'material': 'roof_tile_SK4a', 'ridge_axis_deg': 0, 'ridge_h_m': 1.6,
                                                                                      'overhang_m': 0.3}, 'brick_SK3a',
                    'brick pump house next to the water tower (plan v03 "06"); roof type not given on the plan -> gable (assumption)', sockets={'windows': True, 'ridge_cap': 'tile'}))
    wt = lay['water_tower']
    wtc = T(wt['center'])
    wtp, d = place(ellipse(wtc, wt['tank_r'], wt['tank_r'], 16), 3.0, 'water_tower', 'водонапорная башня')
    props.append(prop('06-06-water-tower', 'water_tower', centre(wtp), 0, [2 * wt['tank_r'], 2 * wt['tank_r'], 18.0], False, material_slot='port_water_tower',
                      collider='full', solid=True, notes='old water tower on legs, tank r %.1f m (plan v03), shadow side to the NE' % wt['tank_r']))
    # ---------------------------------------------------------------- containers (layout v03): stacks keep spacing, real size 6.1 / 12.2 x 2.44
    C = lay['containers']
    groups = [('stackA', [0, 1, 2, 3, 4, 5], 'стопка контейнеров A (40 футов)'), ('stackB', [6, 7, 8, 9, 10, 11], 'стопка контейнеров B (20 футов)')]
    for gname, idx, ru in groups:
        cs = [C[i] for i in idx]
        gc = (sum(c['c'][0] for c in cs) / len(cs), sum(c['c'][1] for c in cs) / len(cs))
        wc_ = T(gc)
        polys = [rrect((wc_[0] + c['c'][0] - gc[0], wc_[1] + c['c'][1] - gc[1]), c['len'], 2.44, math.degrees(c['angle'])) for c in cs]
        hull = rect(min(p[0] for pl in polys for p in pl), min(p[1] for pl in polys for p in pl), max(p[0] for pl in polys for p in pl), max(p[1] for pl in polys for p in pl))
        hp, d = place(hull, 3.0, gname, ru)
        for i, c, pl in zip(idx, cs, polys):
            pl = [(p[0] + d[0], p[1] + d[1]) for p in pl]
            props.append(prop('06-04-cont%02d' % i, 'shipping_container_%dft' % (40 if c['len'] > 7 else 20), centre(pl), math.degrees(c['angle']),
                              [c['len'], 2.44, round(2.59 * c['tiers'], 2)], False, tiers=c['tiers'], footprint=R(pl), group=gname,
                              material='metal_painted_SK6a', solid=True))
    m = lay['machines']
    # reach stacker (plan-drawn 4.2 x 7.5 m, N-S) with container 14 on the spreader (offset kept)
    rs_c = T(m['reach_stacker'])
    c14 = C[14]
    off = (c14['c'][0] - m['reach_stacker'][0], c14['c'][1] - m['reach_stacker'][1])
    body = rrect(rs_c, 4.2, 7.5, 0)
    cpl = rrect((rs_c[0] + off[0], rs_c[1] + off[1]), c14['len'], 2.44, 0)
    hull = rect(min(p[0] for p in body + cpl), min(p[1] for p in body + cpl), max(p[0] for p in body + cpl), max(p[1] for p in body + cpl))
    hp, d = place(hull, 3.0, 'reach_stacker', 'ричстакер с контейнером')
    props.append(prop('06-03-reach-stacker', 'reach_stacker', (rs_c[0] + d[0], rs_c[1] + d[1]), 90, [4.2, 7.5, 5.0], False, solid=True, tint='#E2B13B'))
    props.append(prop('06-04-cont14', 'shipping_container_20ft', (rs_c[0] + off[0] + d[0], rs_c[1] + off[1] + d[1]), 0, [6.1, 2.44, 2.59], False, tiers=1,
                      footprint=R([(p[0] + d[0], p[1] + d[1]) for p in cpl]), group='on_reach_stacker', lifted_m=2.0, solid=True))
    # truck with the 40 ft container 15 (E-W)
    tc = T(m['truck_with_40ft'])
    tpoly, d = place(rrect(tc, 17.0, 2.5, 0), 3.0, 'truck', 'фура с контейнером 07')
    tcen = centre(tpoly)
    props.append(prop('06-07-truck', 'truck_with_container', tcen, 0, [17.0, 2.5, 4.0], False, solid=True, cab_end='east'))
    props.append(prop('06-04-cont15', 'shipping_container_40ft', (tcen[0] - 0.5, tcen[1]), 0, [12.2, 2.44, 2.59], False, tiers=1, group='on_truck', on_truck=True, solid=True))
    for i, note in ((12, 'open container with boxes, at an angle'), (13, 'rusty single container')):
        c = C[i]
        cp, d = place(rrect(T(c['c']), c['len'], 2.44, math.degrees(c['angle'])), 3.0, 'cont%d' % i, 'контейнер %d' % i)
        props.append(prop('06-04-cont%02d' % i, 'shipping_container_20ft', centre(cp), math.degrees(c['angle']), [c['len'], 2.44, 2.59], False, tiers=1,
                          footprint=R(cp), solid=True, notes=note, open_doors=(i == 12), rusty=(i == 13)))
    for i, f in enumerate(m['forklifts']):
        fp, d = place(rrect(T(f), 1.2, 3.2, 0 if i else 90), 2.0, 'forklift%d' % i, 'погрузчик')
        props.append(prop('06-09-forklift%d' % i, 'forklift', centre(fp), 90 if i == 0 else 0, [3.2, 1.2, 2.2], False, solid=True))
    sm = lay['small']
    ps = sm['pipe_stack']
    pp_, d = place(rrect(T(((ps[0] + ps[2]) / 2, (ps[1] + ps[3]) / 2)), ps[2] - ps[0], ps[3] - ps[1], 0), 2.0, 'pipes', 'трубы')
    props.append(prop('06-10-pipe-stack', 'pipe_stack', centre(pp_), 0, [ps[2] - ps[0], ps[3] - ps[1], 1.2], False, footprint=R(pp_), solid=True))
    reels = [(1022.2, 550.8), (1024.8, 548.2), (1022.0, 548.2)]          # plan v03 png "10" (layout gives the count only)
    rc = (sum(r[0] for r in reels) / 3, sum(r[1] for r in reels) / 3)
    rw = T(rc)
    hull = rect(rw[0] - 2.6, rw[1] - 2.6, rw[0] + 2.6, rw[1] + 2.6)
    hp, d = place(hull, 2.0, 'reels', 'катушки кабеля')
    for i, r in enumerate(reels):
        props.append(prop('06-10-cable-reel%d' % i, 'cable_reel', (rw[0] + r[0] - rc[0] + d[0], rw[1] + r[1] - rc[1] + d[1]), 0, [1.6, 1.0, 1.6], False, solid=True))
    dr_ = sm['drums']
    dc = (sum(q[0] for q in dr_) / len(dr_), sum(q[1] for q in dr_) / len(dr_))
    dw = T(dc)
    hull = rect(dw[0] - 2.2, dw[1] - 1.5, dw[0] + 2.2, dw[1] + 1.5)
    hp, d = place(hull, 2.0, 'drums', 'бочки с мазутом')
    for i, q in enumerate(dr_):
        props.append(prop('06-11-drum%02d' % i, 'oil_drum', (dw[0] + q[0] - dc[0] + d[0], dw[1] + q[1] - dc[1] + d[1]), 0, [0.6, 0.6, 0.9], False, solid=True))
    for nm_, c_, sz, ru in (('pallets', (1006.2, 605.1), (3.6, 2.4), 'паллеты'), ('big_bags', (1017.9, 598.7), (3.6, 1.2), 'биг-бэги')):
        bp, d = place(rrect(T(c_), sz[0], sz[1], 0), 2.0, nm_, ru)
        props.append(prop('06-09-%s' % nm_, nm_, centre(bp), 0, [sz[0], sz[1], 1.2], False, footprint=R(bp), solid=True, source='plan v03 png (not in layout json)'))
    tl = sm['toilet']
    tlp, d = place(rrect(T(tl), 1.2, 1.2, 0), 1.0, 'toilet', 'туалет')
    props.append(prop('06-13-toilet', 'portable_toilet', centre(tlp), 270, [1.2, 1.2, 2.3], False, solid=True, tint='#2F6DB5'))
    bt = sm['boat_on_blocks']
    btp, d = place(rrect(T(bt), 10.0, 3.0, 0), 2.0, 'boat', 'лодка на кильблоках')
    props.append(prop('06-14-boat-on-blocks', 'boat_on_keel_blocks', centre(btp), 0, [10.0, 3.0, 2.6], False, solid=True))
    mf = [T(p) for p in ((1032.2, 615.0), (1032.2, 608.8), (1049.8, 608.8), (1049.8, 615.0))]
    props.append(prop('06-05-manifold', 'pipe_manifold', centre(mf), 0, None, False, line=R(mf), notes='low pipe run from the two tanks (plan v03 "05" frame)'))
    for i, q in enumerate(sm['light_masts']):
        c = T(q)
        mp, d = place(rrect(c, 1.2, 1.2, 0), 1.5, 'mast%d' % i, 'мачта освещения %d' % (i + 1))
        props.append(prop('06-12-light-mast%d' % i, 'light_mast', centre(mp), 0, [1.2, 1.2, 20.0], True, solid=True))
    # ---------------------------------------------------------------- pier (quay) with bollards / fenders; fence with openings
    zones.append({'id': '06-pier', 'kind': 'pier', 'poly': Rccw(PIER_PORT), 'surface': 'concrete_SK3c', 'deck_h_m': 1.5,
                  'notes': 'concrete pier into the bay (as drawn on v85): quay edges with bollards and rubber fenders, ladder; boats may moor'})
    edges = [(PIER_PORT[0], PIER_PORT[4]), (PIER_PORT[4], PIER_PORT[3]), (PIER_PORT[3], PIER_PORT[2]), (PIER_PORT[2], PIER_PORT[1])]
    nb = nf = 0
    for a, b in edges:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L // 8))
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        pc_ = centre_of(PIER_PORT)
        mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = uy, -ux
        if (mx_ - pc_[0]) * nx + (my_ - pc_[1]) * ny < 0:                # outward = away from the pier centre
            nx, ny = -nx, -ny
        for k in range(n):
            t = (k + 0.5) / n
            q = (a[0] + (b[0] - a[0]) * t - nx * 0.6, a[1] + (b[1] - a[1]) * t - ny * 0.6)   # on the deck, 0.6 m in
            if q[1] < 680:
                continue                                                 # not at the root (rocks / yard)
            props.append(prop('06-quay-bollard%02d' % nb, 'bollard', q, 0, [0.5, 0.5, 0.7], True, solid=True))
            nb += 1
            qf = (a[0] + (b[0] - a[0]) * t + nx * 0.25, a[1] + (b[1] - a[1]) * t + ny * 0.25)
            props.append(prop('06-quay-fender%02d' % nf, 'rubber_fender', qf, math.degrees(math.atan2(uy, ux)), [1.2, 0.4, 1.0], False))
            nf += 1
    lg.fix((1217, 707), 'Кнехты (3 точки x %.0f, y 697…717) перенесены с открытой воды на кромки пирса порта: %d кнехтов + %d кранцев' % (1217, nb, nf),
           'на карте v85 три кнехта нарисованы в море левее пирса (x 1274…1300) — рисованный артефакт; v02 §8.6: набережная с кнехтами и кранцами')
    # fence ring (PORT_SHAPE, world) with openings at the road (W), road / bridge (E), cornice (S), pier root (N)
    ring_c = ring + [ring[0]]
    rr = resample(ring_c, 0.5)
    openings = []
    for nm_, pl, hw in (('west road', road, 6.0), ('east road / bridge', road, 6.0), ('cornice VIEW C', cor, 6.0)):
        best = None
        for p in rr:
            dd = nearest_on(pl, p)[0]
            if (nm_ == 'west road' and p[0] > 1200) or (nm_ == 'east road / bridge' and p[0] < 1300) or (nm_ == 'cornice VIEW C' and p[1] > 610):
                continue
            if best is None or dd < best[0]:
                best = (dd, p)
        openings.append((nm_, best[1], hw))
    openings.append(('pier root', ((PIER_PORT[0][0] + PIER_PORT[1][0]) / 2, 677.6), (PIER_PORT[1][0] - PIER_PORT[0][0]) / 2))
    keep = [not any(math.hypot(p[0] - o[1][0], p[1] - o[1][1]) < o[2] for o in openings) for p in rr]
    runs, cur = [], []
    for p, k_ in zip(rr, keep):
        if k_:
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        if runs and keep[0]:
            runs[0] = cur + runs[0]
        else:
            runs.append(cur)
    for i, rn in enumerate(runs):
        zones.append({'id': '06-fence-%d' % i, 'kind': 'fence', 'line': R(rn[::4] + [rn[-1]]), 'height_m': 2.2, 'material': 'fence_net',
                      'notes': 'port yard fence (chain-link on concrete posts) along PORT_SHAPE'})
    zones.append({'id': '06-gates', 'kind': 'gates', 'items': [{'name': o[0], 'centre': rnd2(o[1]), 'w_m': round(2 * o[2], 1), 'barrier': False} for o in openings],
                  'notes': 'open gaps in the fence, posts at both sides, NO barriers (v02 §8.6 KPP without barrier)'})
    zones.append({'id': '06-yard', 'kind': 'yard', 'poly': Rccw(ring), 'surface': 'concrete_SK3c', 'layer': 0,
                  'notes': 'concrete port yard (PORT_SHAPE of build_world_v85, world m); oil stains, cracks; the road crosses it on asphalt without a step'})
    zones.append({'id': '06-no-tree', 'kind': 'no_tree', 'poly': Rccw(ring), 'why': 'port yard / loading pads'})
    zones.append({'id': '06-port-road', 'kind': 'road', 'line': R(road), 'width_m': ROAD_W, 'surface': 'asphalt_A5d12', 'world_road': True, 'shoulders': 'concrete inside the yard, gravel outside',
                  'notes': 'map road Rough -> port -> bridge to Tramduro (R84_port_road, v84: smooth from the approach, no step at the entry); '
                           'continues as the bridge 10-bridge from the shoreline (%.1f, %.1f)' % s0})
    zones.append({'id': '06-cornice-T', 'kind': 'road', 'line': R(cor), 'width_m': ROAD_W, 'surface': 'asphalt_A5d12', 'world_road': True,
                  'join': {'onto': '06-port-road', 'at': rnd2((xT, yT)), 'type': 'T', 'straight_m': 15.0},
                  'notes': 'cornice VIEW C inside the port (R27_cornice_in_port): last 15 m straight and perpendicular, axis ends on the port-road axis (T); '
                           'fillet radius ~6 m at both corners'})
    if dev > 0.05:
        lg.fix((xT, yT - 8), 'Карниз VIEW C: последние 15 м выпрямлены по x = %.1f (отклонение рисунка до %.2f м), ось доходит до оси дороги порта — стык буквой Т' % (xT, dev),
               'v10 §6/§7.6: примыкание под прямым углом с прямым подходом 10–20 м')
    rl = road_pl[-1]
    lg.fix(s0, 'Дорога порта продолжена от конца R84 (x %.0f) до кромки воды x %.1f; мост начинается там, где кончается берег (на карте полотно моста идёт от x %.0f через площадку и песок)'
           % (rl[0], s0[0], axis[0][0]), 'v10 §6: начало моста — там, где кончается берег; на суше — обычная дорога без ступеньки')
    lg.fix(T((985, 590)), 'Порт: картинка порта растянута 1.25 x 0.8 под контур карты; центры объектов взяты с картинки, размеры — реальные по плану v03 '
           '(склад 50 x 24, баки d 15.2 круглые, контейнеры 6.1/12.2 x 2.44), стопки сохраняют свои зазоры',
           'иначе баки стали бы эллипсами, контейнеры 15 x 1.95 м, а ряды контейнеров налезли бы друг на друга')
    for name, ru, d, c in nudges:
        lg.fix(c, '«%s» сдвинут на (%.2f, %.2f) м' % (ru, d[0], d[1]),
               'после перевода в реальный размер пересекался с соседним объектом / дорогой (карниз VIEW C новый, на плане v03 его нет) или вылезал за скошенный угол площадки')
    lg.fix(T((1063, 566)), 'Козловой / портальный кран не ставится (в WORLD_MAP_v11 он есть — 06_crane)', 'план v03 «без крана», v02 §8.6 «Не: козловой кран»; работает ричстакер')
    # ---------------------------------------------------------------- residuals: T on the render (stretched drawn footprints)
    tc1 = T((1032.0, 624.0))
    xs_ = [tc1[0] + k_ / 5.0 for k_ in range(-55, 56) if int(np.abs(np.array(px(tc1[0] + k_ / 5.0, tc1[1])) - (215, 220, 223)).max()) <= 6]
    tank_res = round((min(xs_) + max(xs_)) / 2 - tc1[0], 2) if xs_ else None
    meas = {
        'warehouse (drawn, stretched)': resid(mprof([T(p) for p in wh], T((965, 626)), 6), bbox([T(p) for p in wh])),
        'tank_1 centre (row scan of the drawn ellipse)': tank_res,
    }
    road_res = max(nearest_on(road_pl, p)[0] for p in resample(road[:-1], 2.0))
    fit = {'transform': 'plan v03 / WORLD_MAP_v11 metres -> world: T(x, y) = (1197.2 + 1.25 (x - 960), 670.4 + 0.8 (y - 634)) (image P_port_v03_world.png at '
                        'SVG (5336.2, -52) 1250 x 624 = plan stretched by PORT_SCALE; post-shift 0 here); sizes real',
           'residuals_m (max bbox edge diff, centre shift)': meas, 'road_vs_R84_m': round(road_res, 3), 'bridge_start_shore': rnd2(s0)}
    counts = {'buildings': len(blds), 'containers': sum(1 for p in props if p['kind'].startswith('shipping_container')), 'light_masts': len(sm['light_masts']),
              'bollards': nb, 'fenders': nf, 'drums': len(dr_), 'props': len(props), 'zones': len(zones), 'nudged': len(nudges)}
    return {'district': 'port', 'version': 'v85 from plan v03',
            'sources': [rel(PORT_JSON), rel(PORT_PNG), rel(WORLD11) + ' (district 06 buildings / structures)', rel(PORT_IMG), rel(BUILD) + ' (PORT_SHAPE, PIER, _PR)',
                        'VOLUNTEERS_MAP_MASTER_v85.svg (R84_port_road, R27_cornice_in_port, L05b_bridges)', 'handoff v10 §6 §7.6, v02 §8.6'],
            'transform': fit['transform'], 'fit': fit, 'pad_height_m': 2.5, 'pad_note': 'flat concrete pad ~2.5 m above the sea; the road enters level (no step)',
            'abs_heights': False, 'lighting': 'sea_fog_cold', 'buildings': blds, 'props': props, 'zones': zones,
            'fixed_by_logic': lg.fixes, 'questions_for_vadim': lg.qs, 'counts': counts,
            'notes': 'Bridge to Tramduro, its piers and the missile trigger are in tramduro_v85.json (10-bridge). NPC "industrial zone" few; police = city.'}, \
        {'bridge': bseg, 's0': s0, 'e': e_isl, 'axis': axis}


# ============================================================================================ 10 Tramduro
TRAM_FIT0 = (244.2, 194.5)                                               # v76 fit; re-measured below on v85


def tramduro(br):
    lg = Log('tramduro')
    d = load(TRAM_JSON)
    objs = {o['id']: o for o in d['objects']}
    # ---------------------------------------------------------------- re-measure the translation on the v85 render
    pal, hng = objs['residence'], objs['garage']

    def drawn(o, seed_off, tol):
        rb = rrect((o['centre_m'][0] + TRAM_FIT0[0], o['centre_m'][1] + TRAM_FIT0[1]), *o['size_m'], 0)
        c = centre_of(rb)
        return mprof(rb, (c[0] + seed_off[0], c[1] + seed_off[1]), tol)
    mp = drawn(pal, (-12, 0), 10)
    mh = drawn(hng, (-14, -10), 6)
    ests = []
    for o, mb in ((pal, mp), (hng, mh)):
        if mb:
            ests.append(((mb[0] + mb[2]) / 2 - o['centre_m'][0], (mb[1] + mb[3]) / 2 - o['centre_m'][1]))
    fx = sum(e_[0] for e_ in ests) / len(ests) if ests else TRAM_FIT0[0]
    fy = sum(e_[1] for e_ in ests) / len(ests) if ests else TRAM_FIT0[1]
    if math.hypot(fx - TRAM_FIT0[0], fy - TRAM_FIT0[1]) < 1.0:
        fx, fy = TRAM_FIT0                                               # keep the v76 fit when v85 confirms it (< 1 m)
    FIT = (fx, fy)

    def tw(p):
        return (p[0] + FIT[0], p[1] + FIT[1])
    blds, props, zones = [], [], []
    # ---------------------------------------------------------------- buildings
    o = pal
    c = tw(o['centre_m'])
    blds.append(bld('10-01-palace', 'palace_facade_only', 'tramduro_palace', rrect(c, *o['size_m'], 0), o['height_m'],
                    {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.8, 'balustrade': True}, 'stucco_SK3b',
                    'white palace 48 x 22 m on the +2 m presidential hill, White-House-like, detailed facade (porticoes, columns, stairs); NO interior anywhere',
                    floors=3, fh=3.2, tint='#F4F1EA', ents=[{'pos': rnd2(tw(objs['portico']['centre_m'])), 'facing_deg': 270, 'kind': 'door', 'w_m': 3.0, 'closed': True}],
                    sockets={'windows': True, 'columns': True, 'portico': True, 'interior': False}))
    o = hng
    c = tw(o['centre_m'])
    posts = [rnd2(tw(objs['canopy_post%d' % i]['centre_m'])) for i in range(1, 7)]
    blds.append(bld('10-05-hangar', 'arched_hangar_open', 'tramduro_hangar', rrect(c, *o['size_m'], 0), o['height_m'],
                    {'type': 'barrel', 'material': 'roof_profsheet_SK4c'}, 'concrete_panel_SK3c',
                    'open arched hangar 44 x 30 x 8 m with 3 tanks; broad open front to the north apron, open sides on posts (van fits physically)',
                    ents=[{'pos': rnd2((c[0], c[1] + o['size_m'][1] / 2)), 'facing_deg': 90, 'kind': 'open_front', 'w_m': 40.0}],
                    sockets={'windows': False, 'open_front': True, 'open_sides': True}, canopy_posts=posts))
    o = objs['checkpoint']
    c = tw(o['centre_m'])
    blds.append(bld('10-07-kpp', 'guard_booth', 'tramduro_booth', rrect(c, *o['size_m'], 0), o['height_m'], {'type': 'flat', 'material': 'roof_flat_SK4d'},
                    'concrete_panel_SK3c', 'bridge KPP booth at the island end of the bridge; guards attack immediately at the closed entry',
                    ents=[{'pos': rnd2((c[0], c[1] - o['size_m'][1] / 2)), 'facing_deg': 270, 'kind': 'door', 'w_m': 0.9}]))
    # ---------------------------------------------------------------- props from the layout (key objects only)
    PROPS = ['portico', 'statue', 'statue_pedestal', 'tank1', 'tank2', 'tank3', 'helicopter', 'barrier', 'aa1', 'aa2', 'aa3', 'aa4', 'missile1', 'missile2', 'missile3',
             'speech_platform', 'speech_lectern', 'speech_steps', 'military_jeep', 'military_truck', 'boat1', 'boat2', 'green1', 'green2', 'green3']
    for pid in PROPS:
        o = objs[pid]
        sz = list(o['size_m']) + [o.get('height_m') or 0]
        p = prop('10-' + pid, o['kind'], tw(o['centre_m']), o.get('rotation_deg', 0), sz, pid in ('barrier', 'speech_lectern'), solid=o.get('solid'))
        if o.get('elevation_m'):
            p['elevation_m'] = o['elevation_m']
        if pid == 'barrier':
            p['notes'] = 'boom barrier of the island KPP across the road (closed)'
        if pid.startswith('missile'):
            p['notes'] = 'cartoon missile protruding from an open shaft (decorative; replaces the waterfall)'
        if pid.startswith('boat'):
            p['route_id'] = '10-' + o['route_id']
        props.append(p)
    # ---------------------------------------------------------------- zones
    for zid, kind, surf in (('concrete_yard', 'yard', 'concrete_SK3c'), ('palace_lawn', 'lawn', 'lawn'), ('golf', 'golf', 'lawn'), ('missile_cluster', 'missile_shafts', 'concrete_SK3c')):
        o = objs[zid]
        zones.append({'id': '10-' + zid, 'kind': kind, 'poly': Rccw([tw(p) for p in o['polygon_m']]), 'surface': surf, 'notes': o.get('notes', '')})
    for zid, kind, surf in (('concrete_entry', 'apron', 'concrete_SK3c'), ('garage_apron', 'apron', 'concrete_SK3c'), ('statue_plaza', 'plaza', 'plaza_M3'),
                            ('helipad', 'helipad', 'concrete_SK3c')):
        o = objs[zid]
        z = {'id': '10-' + zid, 'kind': kind, 'poly': Rccw(rrect(tw(o['centre_m']), *o['size_m'], o.get('rotation_deg', 0))), 'surface': surf, 'notes': o.get('notes', '')}
        if o.get('elevation_m'):
            z['elevation_m'] = o['elevation_m']
        zones.append(z)
    for t in d['terrain']:
        if t.get('polygon_m'):
            poly = [tw(p) for p in t['polygon_m']]
        elif t.get('centre_m'):
            poly = rrect(tw(t['centre_m']), *t['size_m'], t.get('rotation_deg', 0))
        else:
            continue                                                     # cliffs: along the island outline (10-island-outline)
        zones.append({'id': '10-' + t['id'], 'kind': 'terrain_' + t['kind'], 'poly': Rccw(poly), 'height_delta_m': t.get('height_delta_m'),
                      'notes': t.get('notes', '')})
    for i in range(1, 5):
        o = objs['aa_plinth%d' % i]
        zones.append({'id': '10-aa_plinth%d' % i, 'kind': 'plinth', 'poly': Rccw(rrect(tw(o['centre_m']), *o['size_m'], 0)), 'surface': 'concrete_SK3c'})
    per = objs['perimeter']
    zones.append({'id': '10-perimeter', 'kind': 'fence', 'line': R([tw(p) for p in per['polyline_m']]), 'height_m': per.get('height_m', 4), 'material': 'metal_painted_SK6a',
                  'barbed_wire': True, 'gate': {'between': R([tw(per['polyline_m'][-1]), tw(per['polyline_m'][0])]), 'w_m': round(per['polyline_m'][-1][1] - per['polyline_m'][0][1], 1),
                                                'note': 'the only gate, on the bridge road'},
                  'notes': 'one common steel fence 4 m with barbed wire, one gate (open ring: the gap between the last and the first point)'})
    for pid in ('guard_bridge', 'guard_luxury', 'guard_service', 'boat_route1', 'boat_route2'):
        o = objs[pid]
        zones.append({'id': '10-' + pid, 'kind': 'patrol_route' if pid.startswith('guard') else 'patrol_boat_route', 'line': R([tw(p) for p in o['polyline_m']]),
                      'width_m': o.get('width_m'), 'notes': o.get('notes', '')})
    zones.append({'id': '10-no-tree-base', 'kind': 'no_tree', 'poly': Rccw([tw(p) for p in objs['concrete_yard']['polygon_m']]), 'why': 'military concrete base (functional yard)'})
    for zid in ('golf', 'missile_cluster'):
        zones.append({'id': '10-no-tree-' + zid, 'kind': 'no_tree', 'poly': Rccw([tw(p) for p in objs[zid]['polygon_m']]), 'why': zid})
    pc = tw(pal['centre_m'])
    zones.append({'id': '10-no-tree-palace', 'kind': 'no_tree', 'poly': Rccw(rrect((pc[0], pc[1] - 7), 64, 48, 0)), 'why': 'palace, portico, forecourt, stage and monument'})
    zones.append({'id': '10-veg-lawn', 'kind': 'veg_zone', 'poly': Rccw([tw(p) for p in objs['palace_lawn']['polygon_m']]), 'density': 'sparse', 'species': 'leafy',
                  'notes': 'tidy single trees and clipped shrubs, formal flower beds (OWNER_DECISIONS 29); not on paths, golf, plinths'})
    zones.append({'id': '10-veg-palms-E', 'kind': 'veg_zone', 'poly': Rccw([tw(p) for p in rect(1395, 610, 1401, 642)]), 'density': 'row', 'species': 'palm',
                  'notes': 'a few palms on the east shore strip outside the fence by the missile shafts (plan 06 FINAL draws them there); >= 3 m from the fence, not on the rocks'})
    # ---------------------------------------------------------------- island outline (render) and the bridge on piers
    a = np.asarray(Image.open(MAP_PREVIEW).convert('RGB')).astype(np.int16)
    xs0, ys0, xs1, ys1 = 1425, 640, 1690, 940
    sub = a[950 - ys1:950 - ys0, xs0:xs1]
    land = ~((sub[:, :, 2] - sub[:, :, 0]) > 18)
    land = ndimage.binary_opening(land, iterations=1)
    lab, n = ndimage.label(land)
    k = lab[950 - int(pc[1]) - (950 - ys1), int(pc[0]) - xs0]
    isl = ndimage.binary_fill_holes(lab == k)
    cont = contour(isl[::-1], step=4)                                    # rows -> y north
    outline = [(xs0 + p[0], ys0 + p[1]) for p in cont]
    zones.append({'id': '10-island-outline', 'kind': 'island_outline', 'poly': Rccw(outline), 'surface': None, 'area_m2': int(isl.sum()),
                  'notes': 'land outline measured on the v85 preview (1 px/m); sharp rocks 5-10 m along all shores except the bridge landing; no beach, no pier'})
    seg, s0, e = br['bridge'], br['s0'], br['e']
    ap = next(z for z in zones if z['id'] == '10-concrete_entry')
    ab = bbox(ap['poly'])
    if ab[0] - e[0] > 0.2:                                               # island apron starts exactly where the bridge ends (no gap / step)
        ap['poly'] = Rccw(rect(e[0], ab[1], ab[2], ab[3]))
        lg.fix((e[0], ab[1]), 'Площадка въезда на острове продлена на запад на %.1f м до конца моста (берег x %.1f)' % (ab[0] - e[0], e[0]),
               'по раскладке v06 между концом моста и площадкой оставалась щель — без щели и ступеньки на стыке (v10 §14)')
    L = plen(seg)
    n = max(1, round(L / PIER_STEP))
    step = L / n
    piers = []
    acc = 0.0
    for (p0, p1) in zip(seg[:-1], seg[1:]):
        l_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        while len(piers) < n - 1 and (len(piers) + 1) * step <= acc + l_:
            t = ((len(piers) + 1) * step - acc) / l_
            ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
            piers.append({'pos': rnd2((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)), 'axis_deg': round(ang, 1), 'kind': 'twin_column_pier', 'w_m': BRIDGE_W})
        acc += l_
    zones.append({'id': '10-bridge', 'kind': 'bridge', 'line': R(seg), 'deck_w_m': BRIDGE_W, 'carriageway_w_m': ROAD_W, 'width_m': BRIDGE_W, 'surface': 'asphalt_A5d12',
                  'world_road': True, 'start': rnd2(s0), 'end': rnd2(e), 'length_m': round(L, 1), 'pier_step_m': round(step, 2), 'piers': piers,
                  'abutments': [rnd2(s0), rnd2(e)], 'railing': 'concrete parapet + steel rail, 1.1 m', 'kerbs_m': round((BRIDGE_W - ROAD_W) / 2, 2),
                  'deck_profile': 'level with the port road at the start and the island apron at the end, no step; gentle crest mid-span; '
                                  'clear height above the sea >= 4 m mid-span',
                  'notes': 'REAL bridge on piers over the water (v10 §5, v02 §5: 8.8 m deck, 6.4 m carriageway), NOT an embankment; axis = drawn L05b bridge, '
                           'cut to the shores measured on the v85 render; joins 06-port-road at the start and 10-concrete_entry at the end'})
    zones.append({'id': '10-missile-strike-trigger', 'kind': 'trigger', 'event': 'missile_strike_on_van', 'poly': Rccw(buffer_line(seg, BRIDGE_W / 2)),
                  'notes': 'MARKER ONLY (v02 §8.10, 18.10): the van is shelled with missiles already on the bridge; then the military meet it; mechanic separate'})
    props.append(prop('10-missile-strike-marker', 'trigger_marker', seg[0], 0, None, False, event='missile_strike_on_van', zone='10-missile-strike-trigger'))
    lg.fix(s0, 'Мост на Трамдуро: зона моста (на опорах, шаг %.1f м, %d опор) начинается на кромке воды у порта x %.1f, а не у x %.0f внутри площадки порта; конец — на берегу острова (%.1f, %.1f)'
           % (step, len(piers), s0[0], br['axis'][0][0], e[0], e[1]), 'v10 §5/§6: настоящий мост на опорах, начало — где кончается берег; на суше — дорога/площадка без ступеньки')
    # ---------------------------------------------------------------- residuals
    rp = resid(mp, bbox(rrect(tw(pal['centre_m']), *pal['size_m'], 0)))
    rh = resid(mh, bbox(rrect(tw(hng['centre_m']), *hng['size_m'], 0)))
    gate = tw(per['polyline_m'][0])
    gpx = [x / 5.0 for x in range(int((gate[0] - 3) * 5), int((gate[0] + 3) * 5)) if px(x / 5.0, gate[1] - 1.5)[0] < 100]
    gres = round((sum(gpx) / len(gpx)) - gate[0], 2) if gpx else None
    fit = {'transform': 'TRAMDURO_LAYOUT_v06 metres (= WORLD_MAP_v11 frame) + (%.1f, %.1f); v76 fit (244.2, 194.5) re-measured on the v85 render (tramduro_06_world.png '
                        'at SVG (6895.3, -1163.3), unchanged since v22) -> estimates %s' % (FIT[0], FIT[1], [tuple(round(float(v), 2) for v in e_) for e_ in ests]),
           'residuals_m (max bbox edge diff, centre shift)': {'palace': rp, 'hangar': rh}, 'gate_post_x_m': gres,
           'bridge_end_vs_island_shore_m': round(math.hypot(e[0] - br['axis'][-1][0], e[1] - br['axis'][-1][1]), 2)}
    counts = {'buildings': len(blds), 'props': len(props), 'zones': len(zones), 'bridge_length_m': round(L, 1), 'bridge_piers': len(piers),
              'tanks': 3, 'aa': 4, 'missiles': 3, 'soldiers_target': d['security']['military_outside']}
    return {'district': 'tramduro', 'version': 'v85 from plan 06 FINAL / layout v06 / owner decisions v08',
            'sources': [rel(TRAM_JSON), rel(TRAM_PNG), rel(TRAM_DEC), 'VOLUNTEERS_MAP_MASTER_v85.svg (D10 image, L05b_bridges)', 'handoff v10 §5 §6 §7.10, v02 §5 §8.10'],
            'transform': fit['transform'], 'fit': fit, 'pad_height_m': None, 'pad_note': 'base floor level; palace terrace +2 m; helipad mound +3 m; rocky shore 5-10 m',
            'abs_heights': False, 'lighting': 'light_sea_haze', 'buildings': blds, 'props': props, 'zones': zones,
            'fixed_by_logic': lg.fixes, 'questions_for_vadim': lg.qs, 'counts': counts,
            'notes': 'entry only via the bridge from the port, KPP with barrier at the island end; south = military concrete base, north = presidential lawn with the palace; '
                     '20-25 soldiers (3 patrol routes), 1-2 patrol boats; Tramduro himself only in the finale; no streets / barracks / HQ / radar / navy / beach.'}


# ============================================================================================ overlays
def overlay(dist, name, box, extra=None):
    x0, y0, x1, y1 = box
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    tp = lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for z in dist['zones']:
        if 'line' in z and z['kind'] in ('road', 'track', 'bridge', 'van_route', 'van_entry_sand'):
            col = {'road': (255, 225, 0, 90), 'track': (0, 210, 0, 90), 'bridge': (255, 120, 0, 90)}.get(z['kind'], (0, 200, 255, 60))
            dl.polygon([tp(q) for q in buffer_line(z['line'], z['width_m'] / 2.0)], fill=col)
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    dr = ImageDraw.Draw(im)
    for z in dist['zones']:
        if z['kind'] in ('no_tree', 'sand', 'island_outline', 'trigger'):
            if z['kind'] == 'island_outline':
                dr.polygon([tp(q) for q in z['poly']], outline=(120, 120, 255))
            continue
        if 'poly' in z:
            col = (20, 140, 40) if z['kind'] == 'veg_zone' else (0, 160, 255)
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            col = {'fence': (150, 0, 200), 'road': (200, 160, 0), 'bridge': (230, 90, 0)}.get(z['kind'], (0, 150, 0))
            dr.line([tp(q) for q in z['line']], fill=col, width=2 if z['kind'] == 'fence' else 1)
        if z['kind'] == 'bridge':
            for pr in z['piers']:
                x, y = tp(pr['pos'])
                dr.rectangle([x - 3, y - 3, x + 3, y + 3], outline=(230, 90, 0), width=2)
    for b in dist['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2)
        for e in b.get('entrances', []):
            x, y = tp(e['pos'])
            dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(0, 0, 255))
    for p in dist['props']:
        if p.get('footprint'):
            dr.polygon([tp(q) for q in p['footprint']], outline=(255, 0, 255))
        x, y = tp(p['pos'])
        r_ = 3 if p['kind'] == 'palm' else 2
        col = (0, 120, 0) if p['kind'] == 'palm' else (255, 0, 255)
        dr.ellipse([x - r_, y - r_, x + r_, y + r_], fill=col)
    im.save(os.path.join(WORK, 'check_%s.png' % name))


def main():
    os.makedirs(WORK, exist_ok=True)
    svg = svg_text()
    b = beach()
    p, br = port(svg)
    t = tramduro(br)
    for name, dist, box in (('beach', b, (775, 60, 1500, 255) if not BEACH_DY else (690, 2, 1500, 250)), ('port', p, (1110, 585, 1400, 730)),
                            ('tramduro', t, (1330, 625, 1675, 940))):
        save_json('districts/%s_v85.json' % name, dist)
        overlay(dist, name, box)
        print('%s_v85:' % name, json.dumps(dist['counts'], ensure_ascii=False))
        print('  fit:', json.dumps({k: v for k, v in dist['fit'].items() if k != 'transform'}, ensure_ascii=False))
        print('  fixes:', len(dist['fixed_by_logic']), 'questions:', len(dist['questions_for_vadim']))
    print('beach checks:', b['checks'])


if __name__ == '__main__':
    main()
