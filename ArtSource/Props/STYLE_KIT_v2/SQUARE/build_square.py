"""STYLE_KIT_v2 / SQUARE - the old-town square set: fountain with a monument, bench, lamp post, planter
(style bible v2, sections 3.5, 4 and 8).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/SQUARE/build_square.py -- --revision 1

Props the player stands next to get the "Tripo plumpness" of bible 3.5: two-segment bevels (2-4 cm) with weighted
normals, so big faces stay flat and every edge catches a soft highlight. Members are stout (bible 4.2: lamp post
0.18 m, bench frames 0.08 m), colours are <= 3 swatches per prop, and nothing is textured.
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
import sk2_house as hk                                   # noqa: E402
from mathutils import Vector                             # noqa: E402

fam = sk.Family('SK2-SQUARE-001', __file__, 'SQ_', budget=(1, 1500),
                description='Square set v2: SQ_Fountain (+ monument), SQ_Bench, SQ_LampPost, SQ_Planter, SQ_ClockShaft '
                            '(bible 2.7, 8, 12)')


def bbox(m, sx, sy, sz, col, at, bev=0.03, seg=2, M=None, **kw):
    """Bevelled box centred at `at` (the prop workhorse)."""
    Mx = (M or sk.Matrix.Identity(4)) @ sk.T(*at)
    return m.bevel_box(sx, sy, sz, bev, col, M=Mx, segments=seg, normals='weighted', **kw)


def rounded_profile(pts, r, steps=2):
    """Rounds the corners of an (r, z) profile polyline (not the poles): each inner corner becomes `steps` + 1 points
    on a quarter-ish arc of radius r. Gives lathed props their soft, cast look."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        d0, d1 = (p0 - p1), (p2 - p1)
        l0, l1 = d0.length, d1.length
        rr = min(r, l0 * 0.45, l1 * 0.45)
        a, b = p1 + d0.normalized() * rr, p1 + d1.normalized() * rr
        for k in range(steps + 1):
            t = k / steps
            q = (1 - t) ** 2 * a + 2 * (1 - t) * t * p1 + t ** 2 * b        # quadratic Bezier through the corner
            out.append((q.x, q.y))
    out.append(pts[-1])
    return out


# ---------------------------------------------------------------- fountain with a monument
STATUE = 'slate.dark'


def statue(m, z0):
    """A generic standing figure in a long coat, right arm raised forward (pointing ahead), left arm down -
    cast in one dark bronze-like swatch. Built from a few smooth lathed and tubed masses, no detail below 6 cm."""
    m.lathe(rounded_profile([(0.0, z0), (0.42, z0), (0.42, z0 + 0.14), (0.0, z0 + 0.14)], 0.03), 12, STATUE,
            normals='soft_weighted', kind='hard', member=0.14, name='statue')                   # base plate
    coat = [(0.0, z0 + 0.14), (0.35, z0 + 0.14), (0.3, z0 + 0.7), (0.26, z0 + 1.25), (0.31, z0 + 1.6), (0.37, z0 + 1.92),
            (0.34, z0 + 2.02), (0.14, z0 + 2.1), (0.0, z0 + 2.12)]
    m.lathe(coat, 10, STATUE, M=sk.S(1.0, 0.72, 1.0), normals='smooth', kind='hard', member=0.24, name='statue')
    m.lathe([(0.0, z0 + 2.08), (0.08, z0 + 2.1), (0.085, z0 + 2.22), (0.0, z0 + 2.24)], 8, STATUE, normals='smooth',
            kind='hard', member=0.16, name='statue')                                             # neck
    m.lobe(0.17, STATUE, at=(0.0, -0.02, z0 + 2.38), squash=(0.92, 1.0, 1.1), kind='hard', grad=None, name='statue')   # head
    m.tube([(0.3, -0.02, z0 + 1.9), (0.56, -0.26, z0 + 2.14), (0.8, -0.5, z0 + 2.4)], [0.1, 0.085, 0.075], 8, STATUE,
           normals='smooth', kind='hard', member=0.15, name='statue')                           # right arm raised ahead
    m.lobe(0.09, STATUE, at=(0.83, -0.53, z0 + 2.43), subdiv=1, kind='hard', grad=None, name='statue')                 # hand
    m.tube([(-0.3, 0.0, z0 + 1.95), (-0.36, 0.02, z0 + 1.6), (-0.34, 0.05, z0 + 1.22)], [0.1, 0.09, 0.08], 8, STATUE,
           normals='smooth', kind='hard', member=0.16, name='statue')                           # left arm down


def fountain():
    m = sk.Mesh()
    seg = 32
    # step ring and basin wall (stone), rounded rim cap (chalk)
    m.lathe_loop([(3.15, 0.0), (3.65, 0.0), (3.65, 0.11), (3.61, 0.15), (3.15, 0.15)], seg, 'paving',
                 normals='soft_weighted', kind='hard', member=0.15, name='step')
    m.lathe_loop([(2.85, 0.0), (3.2, 0.0), (3.2, 0.46), (2.85, 0.46)], seg, 'paving', normals='soft_weighted', kind='hard',
                 member=0.35, name='basin')
    rim = [(2.78, 0.44), (3.32, 0.44), (3.32, 0.52), (3.26, 0.58), (2.84, 0.58), (2.78, 0.52)]
    m.lathe_loop(rim, seg, 'chalk', normals='soft_weighted', kind='hard', member=0.14, name='rim')
    # pedestal: plinth, shaft, cornice, top plate (stone with chalk mouldings), standing in the water
    bbox(m, 1.7, 1.7, 0.55, 'paving', (0, 0, 0.275), bev=0.04)
    bbox(m, 1.9, 1.9, 0.14, 'chalk', (0, 0, 0.6), bev=0.03)
    bbox(m, 1.15, 1.15, 1.75, 'paving', (0, 0, 1.53), bev=0.04)
    bbox(m, 1.42, 1.42, 0.18, 'chalk', (0, 0, 2.48), bev=0.04)
    bbox(m, 1.25, 1.25, 0.12, 'paving', (0, 0, 2.63), bev=0.03)
    statue(m, 2.69)
    return m


def fountain_water():
    """Opaque water (bible 3.4) as a child: a disc filling the basin + four arcing jets from the pedestal."""
    m = sk.Mesh()
    m.lathe([(0.0, 0.0), (2.9, 0.0), (2.9, 0.38), (0.0, 0.38)], 32, 'water', normals='soft', kind='hard', member=0.38,
            name='water')
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0.0))

        def P(r, z):
            return tuple(d * r + Vector((0, 0, z)))
        m.tube([P(0.5, 1.12), P(0.9, 1.42), P(1.35, 1.44), P(1.72, 1.08), P(1.92, 0.62), P(1.98, 0.34)],
               [0.1, 0.095, 0.085, 0.08, 0.08, 0.09], 6, 'water.light', normals='smooth', kind='hard', member=0.16, name='jet')
    return m


# ---------------------------------------------------------------- bench
def bench():
    """Old-town park bench, 1.8 m: three seat slats and two back slats (wood) on two cast frames (ink)."""
    m = sk.Mesh()
    L = 1.8
    for y in (-0.165, -0.01, 0.145):                                       # seat slats, top at 0.45
        bbox(m, L, 0.14, 0.07, 'wood', (0, y, 0.415), bev=0.02)
    tilt = sk.R(-12, 'X')
    for z in (0.64, 0.82):                                                 # back slats, leaning 12 deg
        yb = 0.255 + (z - 0.45) * math.tan(math.radians(12))
        bbox(m, L, 0.15, 0.07, 'wood', (0, 0, 0), bev=0.02, M=sk.T(0, yb, z) @ tilt)
    for x in (-0.68, 0.68):                                                # cast frames
        bbox(m, 0.08, 0.08, 0.38, 'ink', (x, -0.18, 0.19), bev=0.015, seg=1)              # front leg
        bbox(m, 0.08, 0.08, 0.38, 'ink', (x, 0.215, 0.19), bev=0.015, seg=1)              # back leg
        bbox(m, 0.08, 0.08, 0.62, 'ink', (0, 0, 0), bev=0.015, seg=1,                      # back support, leaning
             M=sk.T(x, 0.215 + 0.31 * math.sin(math.radians(12)), 0.35 + 0.31 * math.cos(math.radians(12))) @ tilt)
        bbox(m, 0.08, 0.5, 0.07, 'ink', (x, 0.03, 0.345), bev=0.015, seg=1)               # seat rail
        bbox(m, 0.09, 0.46, 0.06, 'ink', (x, 0.02, 0.66), bev=0.015, seg=1)               # armrest
        bbox(m, 0.07, 0.07, 0.27, 'ink', (x, -0.18, 0.51), bev=0.015, seg=1)              # armrest post
    return m


# ---------------------------------------------------------------- lamp post
def lamp_post():
    """Old-town lamp, 4.85 m: bell base, 0.18 m post with collars, a four-paned lantern under a pyramid cap.
    The glass panes are the emissive child (lamp_glow)."""
    m = sk.Mesh()
    prof = [(0.0, 0.0), (0.27, 0.0), (0.27, 0.12), (0.2, 0.2), (0.16, 0.55), (0.2, 0.6), (0.2, 0.68), (0.09, 0.78),
            (0.09, 3.7), (0.13, 3.75), (0.13, 3.85), (0.09, 3.9), (0.09, 4.02), (0.0, 4.02)]
    m.lathe(rounded_profile(prof, 0.03, 1), 10, 'ink', normals='soft_weighted', kind='hard', member=0.18, name='post')
    bbox(m, 0.46, 0.46, 0.07, 'ink', (0, 0, 4.04), bev=0.02)                  # lantern floor
    for sx in (-1, 1):
        for sy in (-1, 1):
            bbox(m, 0.06, 0.06, 0.44, 'ink', (sx * 0.17, sy * 0.17, 4.29), bev=0.012)    # corner posts
    bbox(m, 0.48, 0.48, 0.06, 'ink', (0, 0, 4.53), bev=0.02)                  # lantern roof plate
    m.lathe([(0.0, 4.56), (0.34, 4.56), (0.0, 4.82)], 4, 'ink', offset=math.pi / 4, normals='flat', kind='hard',
            member=0.26, name='cap')                                           # pyramid cap
    m.lobe(0.055, 'ink', at=(0, 0, 4.86), subdiv=1, kind='hard', grad=None, name='finial')
    return m


def lamp_glass():
    m = sk.Mesh()
    m.box(0.3, 0.3, 0.42, 'lamp_glow', base=True, at=(0, 0, 4.075), kind='hard', member=0.3)
    return m


# ---------------------------------------------------------------- planter
def planter():
    """Soviet-square vase: a white-painted concrete cup (chalk) holding a low mound of leaves with red flowers."""
    m = sk.Mesh()
    prof = [(0.0, 0.0), (0.38, 0.0), (0.38, 0.1), (0.26, 0.2), (0.24, 0.3), (0.44, 0.42), (0.62, 0.62), (0.68, 0.7),
            (0.68, 0.78), (0.6, 0.8), (0.58, 0.72), (0.0, 0.72)]
    m.lathe(rounded_profile(prof, 0.04, 1), 16, 'chalk', normals='soft_weighted', kind='hard', member=0.24, name='vase')
    m.lobe(0.6, 'grad.bush', at=(0, 0, 0.74), squash=(1, 1, 0.52), flat_bottom=-0.3, grad=(0.6, 1.05), name='mound')
    for k, (az, el) in enumerate([(10, 55), (85, 40), (150, 62), (205, 35), (265, 50), (320, 30), (40, 80)]):
        a, e = math.radians(az), math.radians(el)
        p = Vector((0.6 * math.cos(e) * math.cos(a), 0.6 * math.cos(e) * math.sin(a), 0.74 + 0.6 * 0.52 * math.sin(e)))
        m.lobe(0.095, 'red', at=tuple(p * 1.0), subdiv=1, squash=(1, 1, 0.8), grad=None, member=0.15, name='bloom')
    return m


# ---------------------------------------------------------------- clock tower shaft (v02)
CLOCK = {'wall': 'brick', 'roof': 'grey', 'roof_c': 'grey', 'deck': 'grey', 'trim': 'chalk', 'plinth': 'grey', 'door': 'wood',
         'accent': 'red'}


def clock_shaft():
    """The shaft under the LANDMARKS clock top (plan: free-standing tower, shaft 3.2 x 3.2 x 9 m, bible 2.7 brick):
    PT_Brick_v2 walls on a grey plinth, chalk corner pilasters and two bands, a panelled wood door under a fanlight,
    narrow windows on every side, a chalk cornice ring at 9 m where the clock top sits."""
    h = hk.House(3.2, 3.2, 9.0, CLOCK, plinth=0.6, floor=2.8)
    h.door(0, 0.0, w=1.1, h=2.3, transom=1.9, arch=True, steps=1)
    for side in range(4):
        for z in (3.9, 6.3):
            h.body.opening(side, 0.0, 0.6, z, z + 1.3, 'glass', depth=0.15)
    h.plinth_box()
    h.pilasters(9.0, w=0.32)
    for z in (3.35, 5.85):
        h.band(z, h=0.22, proud=0.06)
    m = h.finish()
    h.cornice(9.0, h=0.4, out=0.22)
    return m


fam.add_asset('SQ_Fountain', fountain, budget=(1, 4000), max_swatches=4, row=0,
              children=[('Water', fountain_water, False)], kind='landmark',
              notes='The water and the four jets are the child SQ_Fountain_Water (swap in an animated water material if wanted).')
fam.add_asset('SQ_Bench', bench, budget=(1, 1500), max_swatches=2, row=1, seat_height_m=0.45, kind='prop near the player')
fam.add_asset('SQ_LampPost', lamp_post, budget=(1, 1500), max_swatches=2, row=1, children=[('Emissive', lamp_glass, True)],
              kind='prop near the player', notes='Lantern glass is the child SQ_LampPost_Emissive (lamp_glow, emission x1.5 day / x3 night).')
fam.add_asset('SQ_Planter', planter, budget=(1, 1500), max_swatches=3, row=1, kind='prop near the player')
fam.add_asset('SQ_ClockShaft', clock_shaft, budget=(1, 2500), row=0, kind='landmark',
              notes='Shaft of the free-standing clock tower; the LANDMARKS clock_tower_top sits on it at z = 9 m.')

report = fam.finish(lineup_gap=1.5, extra_notes=[
    'Fountain: stone (paving) basin and pedestal, chalk rim and mouldings, a slate.dark monument, opaque water child.',
    'Bevels: 2 segments, weighted normals (bible 3.5) on every prop the player can stand next to.',
    'v02: SQ_ClockShaft (brick, PT_Brick_v2) for the plan clock tower; the lantern glass stays the emissive child, the '
    'daytime emission is switched off in the Unity material (critique 13c).'])


# ---------------------------------------------------------------- previews
def slab(w, d, col, at=(0, 0)):
    m = sk.Mesh()
    m.box(w, d, 0.02, col, base=True, at=(at[0], at[1], -0.015))
    return m


if not fam.args.no_render:
    for name, az, el, lens in (('SQ_Fountain', 30, 18, 45), ('SQ_Bench', 32, 16, 55), ('SQ_LampPost', 28, 10, 50),
                               ('SQ_Planter', 30, 16, 55), ('SQ_ClockShaft', 30, 12, 45)):
        objs = fam.place(name, 0.0, 0.0)
        pave = fam.proxy('Proxy_Paving', slab(14, 14, 'paving'))
        fam.showcase(True)
        r = report['assets'][name]
        person = (r['bounds_min'][0] - 0.8, r['bounds_min'][1] - 0.4) if name != 'SQ_Fountain' else (-4.2, -3.0)
        fam.shot(f'01_{name}.png', objs, az=az, el=el, res=(1400, 1100), lens=lens, ground='lawn', person=person)
        fam.clear_showcase()
    # the set on the square: benches in pairs facing the fountain, lamps on one line, planters at the corners
    objs = fam.place('SQ_Fountain', 0.0, 0.0)
    for k in range(4):
        a = math.radians(90 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-d.y, d.x, 0))
        for s in (-1, 1):
            p = d * 6.2 + t * s * 1.3
            objs += fam.place('SQ_Bench', p.x, p.y, rot=math.degrees(a) + 270)          # facing the fountain
        lp = d * 6.4 + t * 3.6
        objs += fam.place('SQ_LampPost', lp.x, lp.y)
        pc = d * 6.2 + t * -3.6
        objs += fam.place('SQ_Planter', pc.x, pc.y)
    pave = fam.proxy('Proxy_Square', slab(24, 24, 'paving'))
    objs.append(pave)
    fam.showcase(True)
    fam.shot('02_set_on_the_square.png', objs, az=25, el=32, res=(1800, 1200), lens=40, ground='lawn', person=(4.5, -7.5))
    fam.shot('03_set_eye_level.png', objs, az=15, el=0, res=(1800, 1000), lens=32, ground='lawn', eye=1.6,
             target=(0.0, 0.0, 2.2), dist=15.0, person=(2.0, -9.0))
    fam.clear_showcase()
    fam.showcase(False)
print('done')
