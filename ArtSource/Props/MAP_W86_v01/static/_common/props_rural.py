"""Forest + Hamlet static props (M2). Blender frame = W85 box frame: X = data size[0], Y = data size[1], Z up."""
import math, random
from m2reg import prop


# ------------------------------------------------------------------ FOREST
@prop('CampfireCold', ['campfire_cold'], data_size=[6.8, 6.8, 0.4], front=None,
      collider_note='Two stump seats only; stones / ash are walk-over (no collider).',
      notes='Cold campfire in the wagon clearing: ring of 9 stones, ash, charred logs, two stump seats, kindling pile, two empty bottles (no labels).')
def campfire(A, v):
    A.cyl(.66, .04, (0, 0, 0), 'ash', n=16, bevel=0)
    A.cyl(.42, .06, (0, 0, 0), 'charred', n=12, bevel=0)
    stones = ['rock', 'rock_dark', 'rock_light']
    for i in range(9):
        a = i * math.tau / 9 + A.rng.uniform(-.08, .08)
        r = .2 + A.rng.uniform(-.03, .04)
        A.ico(r, (.82 * math.cos(a), .82 * math.sin(a), .0), stones[i % 3], subdiv=2,
              scale=(1.25, 1.0, .72), rot=(0, 0, math.degrees(a)), noise=.12, flat_bottom=-.02)
    for i, a in enumerate((20, 115, 205, 290)):
        ar = math.radians(a)
        p = (.62 * math.cos(ar), .62 * math.sin(ar), .07)
        q = (-.12 * math.cos(ar + .5), -.12 * math.sin(ar + .5), .16 + .04 * (i % 2))
        A.beam(p, q, .065, 'charred', n=7)
        A.beam((1.15 * math.cos(ar), 1.15 * math.sin(ar), .05), p, .06, 'bark', n=7, detail=True) if i % 2 else None
    for a in (200, 330):
        ar = math.radians(a)
        x, y = 2.35 * math.cos(ar), 2.35 * math.sin(ar)
        A.cyl(.25, .40, (x, y, 0), 'bark', n=10)
        A.cyl(.22, .025, (x, y, .40), 'log_end', n=10, bevel=0)
        A.col_box((.48, .48, .42), (x, y, .21))
    # kindling pile next to the first stump
    for k, (dx, dz, ang) in enumerate(((0, .06, 0), (.13, .06, 8), (.26, .06, -6), (.07, .17, 3), (.2, .17, -4))):
        A.beam((-2.6 + dx, -1.25, dz), (-2.6 + dx + .08, -.7, dz), .055, 'bark', n=6, detail=True)
    # two empty bottles, lying (no labels)
    A.cyl(.035, .2, (.95, 1.35, .035), 'green_dark', n=8, rot=(0, 90, 20), detail=True)
    A.cyl(.014, .07, (1.14, 1.42, .035), 'green_dark', n=6, rot=(0, 90, 20), detail=True)
    A.cyl(.035, .2, (-1.3, .9, .035), 'brown', n=8, rot=(90, 0, 60), detail=True)


@prop('LogBench', ['log_bench'], data_size=[5.8, 1.4, 0.5],
      collider_note='One box along the seat (5.2 x 0.5 x 0.48).',
      notes='Fallen-log bench by the campfire: sawn flat seat, root plate at one end, branch stubs.')
def log_bench(A, v):
    pts = [(-2.45 + i * .98, 0, .25 - .015 * i) for i in range(6)]
    A.sweep(pts, .25, 'bark', n=10, radii=[.27, .26, .25, .24, .23, .21])
    A.box((4.2, .27, .04), (.15, 0, .47), 'log_end', bevel=.01)
    A.cyl(.2, .03, (2.47, 0, .18), 'log_end', n=10, rot=(0, 90, 0), bevel=0)
    # root plate
    A.cyl(.46, .22, (-2.62, 0, .26), 'bark', n=10, rot=(0, -90, 0))
    A.cyl(.30, .02, (-2.84, 0, .26), 'earth', n=8, rot=(0, -90, 0), bevel=0)
    for k in range(7):
        a = k * math.tau / 7 + .3
        p = (-2.7, .38 * math.cos(a), .26 + .38 * math.sin(a))
        q = (-2.95 + A.rng.uniform(-.1, .1), .66 * math.cos(a), max(.02, .26 + .62 * math.sin(a)))
        A.beam(p, q, .06, 'bark', n=5, r2=.02, detail=True)
    for x, a in ((-1.2, 35), (.6, -40), (1.7, 25)):
        ar = math.radians(a)
        A.beam((x, .2 * math.sin(ar), .3), (x + .1, .45 * math.sin(ar) + .05, .45), .05, 'bark', n=5, r2=.03)
    A.col_box((5.2, .5, .48), (-.05, 0, .24))


@prop('BlockedTunnelMouth', ['blocked_tunnel_mouth'], data_size=[6.0, 3.0, 5.0], front='Unity +X (Blender -X): the cliff is on the -X side',
      collider_note='Portal wall box + rock-fill box + spill hull: no way through.',
      view=(-1.3, -.9, .55), notes='Old single-track rail tunnel portal (stone voussoir arch, concrete face, wing walls) completely filled with rocks; '
            'rails come out from under the rocks. Terrain check (heightmap v02): ground rises steeply toward local -X, so the face looks to local +X.')
def tunnel(A, v):
    # everything built facing -X (Blender); face plane at x = -0.6
    R90 = (90, 0, 90)       # local X->Y, Y->Z, Z->X : prism(poly in (y,z)) extruded along +X
    fx, depth = -.6, 1.2
    A.box((depth, 1.1, 3.0), (0, -2.75, 1.5), 'concrete')
    A.box((depth, 1.1, 3.0), (0, 2.75, 1.5), 'concrete')
    # spandrel wall above the arch (U-shape cut by arch extrados r=2.75)
    arc = [(2.75 * math.cos(math.radians(a)), 3.0 + 2.75 * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    poly = [(-3.3, 3.0), (-3.3, 6.2), (3.3, 6.2), (3.3, 3.0)] + arc     # arc runs 0 deg (y=+2.75) -> 180 deg (y=-2.75)
    A.prism(list(reversed(poly)), depth, (fx, 0, 0), 'concrete', rot=R90)
    # voussoirs
    n = 11
    for i in range(n):
        a = math.radians((i + .5) * 180 / n)
        r = 2.48
        A.box((depth + .1, .62, .5), (fx + depth / 2 - .05, r * math.cos(a), 3.0 + r * math.sin(a)), 'stone_warm',
              rot=(math.degrees(a) - 90, 0, 0), bevel=.025, segs=1)
    A.box((depth + .2, 7.0, .35), (0, 0, 6.35), 'concrete_dark')          # cornice
    A.box((depth + .1, 7.0, .3), (0, 0, .15), 'concrete_dark')            # plinth course
    # wing walls (sloping tops), going forward (-X) and outward
    for s in (-1, 1):
        prof = [(0, 0), (2.6, 0), (2.6, 1.6), (0, 5.4)]
        A.prism(prof, .55, (fx, s * 3.3 + (0 if s > 0 else -.55), 0), 'concrete', rot=(90, 0, 180 + (0 if s > 0 else 0)))
    # rock fill in the arch + spill in front
    cols = ['rock', 'rock_dark', 'rock_light']
    k = 0
    for y in (-1.7, -.6, .55, 1.65):
        for z in (.7, 1.9, 3.1):
            if abs(y) > 1.6 and z > 2.5:
                continue
            A.ico(.75 + A.rng.uniform(-.1, .15), (fx + .35, y + A.rng.uniform(-.15, .15), z), cols[k % 3], subdiv=1,
                  scale=(.8, 1.0, .85), rot=(A.rng.uniform(0, 90), A.rng.uniform(0, 90), 0), noise=.15)
            k += 1
    for y, z, r in ((-.9, 4.15, .6), (.7, 4.3, .55), (-.1, 4.85, .45)):
        A.ico(r, (fx + .3, y, z), cols[k % 3], subdiv=1, noise=.15); k += 1
    spill = [(-1.3, -1.2, .45, .7), (-1.5, .4, .4, .65), (-1.2, 1.6, .35, .55), (-2.1, -.4, .3, .5), (-2.4, 1.0, .2, .4),
             (-2.6, -1.6, .15, .35), (-1.9, -2.3, .2, .45)]
    for x, y, z, r in spill:
        A.ico(r, (x, y, z), cols[k % 3], subdiv=1, scale=(1.1, 1.0, .8), noise=.15, rot=(0, 0, A.rng.uniform(0, 90))); k += 1
    A.mound(1.9, 2.4, .55, (-1.6, 0, 0), 'gravel_dark', rings=3, segs=10, noise=.12)
    # rails emerging from the rocks + sleepers
    for y in (-.72, .72):
        A.box((2.0, .07, .14), (-2.6, y, .07), 'rust_dark', bevel=0)
    for x in (-3.3, -2.6, -1.9):
        A.box((.26, 2.2, .12), (x, 0, .03), 'wood_dark', bevel=.02)
    A.col_box((depth, 6.6, 6.5), (0, 0, 3.25))
    A.col_hull([(-.6, -2.4, 0), (-.6, 2.4, 0), (-3.2, -2.0, 0), (-3.2, 1.8, 0), (-.6, -2.0, 1.6), (-.6, 2.0, 1.6), (-1.6, 0, 1.1)])


# ------------------------------------------------------------------ HAMLET
@prop('Grave', ['grave'], variants=['A', 'B', 'C'], data_size=[1.0, 1.9, 0], variant_rule='stable hash of id % 3',
      front='head end (cross / stone) at Blender +Y = Unity -Z',
      collider_note='Low box over the mound/fence (1.0 x 1.9 x 0.5) + post box for the cross.',
      notes='A: wooden Orthodox cross with a little roof, grass mound, wreath. B: dark granite headstone with stone kerb and flowers. '
            'C: blue-painted iron fence (ogradka) with a metal cross, small bench and table.')
def grave(A, v):
    head = .72
    if v in ('A', 'C'):
        A.ico(.5, (0, -.05, 0), 'leaf' if v == 'A' else 'earth', subdiv=2, scale=(.82, 1.55, .32), noise=.04, flat_bottom=0, facet=False)
    if v == 'A':
        wd = 'wood_weathered'
        A.box((.09, .09, 1.55), (0, head, .775), wd, bevel=.015)
        A.box((.72, .07, .08), (0, head, 1.15), wd, bevel=.012)
        A.box((.36, .07, .07), (0, head, 1.38), wd, bevel=.012)
        A.box((.42, .07, .07), (0, head, .58), wd, rot=(0, -22, 0), bevel=.012)
        for s in (-1, 1):
            A.box((.18, .3, .025), (s * .07, head, 1.6), 'wood_dark', rot=(0, s * 38, 0), bevel=0)
        A.torus(.13, .03, (.05, -.2, .16), 'leaf', n=12, m=5, rot=(8, 0, 0), detail=True)
        for k in range(5):
            a = k * math.tau / 5
            A.sphere(.035, (.05 + .13 * math.cos(a), -.2 + .13 * math.sin(a), .19), 'flower_red' if k % 2 else 'flower_white', seg=6, rings=4, detail=True)
        A.col_box((.12, .12, 1.5), (0, head, .75))
    elif v == 'B':
        A.box((.95, 1.75, .12), (0, -.05, .06), 'granite', bevel=.02)
        A.box((.75, 1.45, .14), (0, -.05, .1), 'soil', bevel=.02)
        A.box((.8, .3, .14), (0, head, .07), 'granite_dark', bevel=.02)
        A.box((.6, .11, .72), (0, head, .5), 'granite_dark', bevel=.02)
        A.cyl(.3, .11, (0, head + .055, .86), 'granite_dark', n=16, rot=(90, 0, 0), bevel=.015)
        A.box((.34, .015, .22), (0, head - .062, .6), 'granite', bevel=0, detail=True)  # blank plaque, no text
        cols = ['flower_red', 'flower_yellow', 'flower_white', 'leaf']
        for k, (x, y) in enumerate(((-.2, .2), (.15, -.05), (-.1, -.4), (.2, -.55), (0, .45))):
            A.ico(.12, (x, y, .17), cols[k % 4], subdiv=2, scale=(1, 1, .6), noise=.1, detail=k > 2, facet=False)
        A.col_box((.95, 1.75, .25), (0, -.05, .12))
    else:
        c = 'blue_soft'
        hx, hy, h = .5, .95, .62
        for x in (-hx, hx):
            for y in (-hy, hy):
                A.box((.045, .045, h + .05), (x, y, (h + .05) / 2), c, bevel=0)
                A.cyl(.025, .06, (x, y, h + .05), c, n=6, r2=.002, bevel=0)
        for z in (.1, h - .04):
            A.box((2 * hx, .03, .03), (0, -hy, z), c, bevel=0); A.box((2 * hx, .03, .03), (0, hy, z), c, bevel=0)
            A.box((.03, 2 * hy, .03), (-hx, 0, z), c, bevel=0); A.box((.03, 2 * hy, .03), (hx, 0, z), c, bevel=0)
        step = .14
        for side, (L, fixed, axis) in enumerate(((2 * hx, hy, 'x'), (2 * hx, -hy, 'x'), (2 * hy, hx, 'y'), (2 * hy, -hx, 'y'))):
            n = int(L / step)
            for i in range(1, n):
                t = -L / 2 + i * L / n
                p = (t, fixed, 0) if axis == 'x' else (fixed, t, 0)
                if axis == 'y' and fixed < 0 and abs(t + .2) < .25:
                    continue                     # gate opening on one long side
                A.box((.018, .018, h - .1), (p[0], p[1], .1 + (h - .1) / 2), c, bevel=0)
                A.cyl(.02, .07, (p[0], p[1], h - .04), c, n=4, r2=.002, bevel=0, detail=True)
        A.box((.016, .5, .45), (-hx - .01, -.2, .35), c, rot=(0, 0, 35), bevel=0)    # gate leaf ajar
        mc = 'steel_galv'
        A.cyl(.03, 1.25, (0, head - .05, 0), mc, n=8)
        A.cyl(.025, .6, (-.3, head - .05, 1.0), mc, n=8, rot=(0, 90, 0))
        A.cyl(.022, .3, (-.15, head - .05, 1.15), mc, n=8, rot=(0, 90, 0))
        A.cyl(.022, .36, (-.18, head - .05, .55), mc, n=8, rot=(0, 70, 0))
        A.box((.36, .16, .035), (.28, -.62, .4), 'wood_bench', bevel=.01)      # bench
        for x in (.16, .4):
            A.box((.04, .04, .39), (x, -.62, .195), 'blue_soft', bevel=0)
        A.box((.26, .26, .03), (-.28, -.62, .55), 'wood_bench', bevel=.01, detail=True)    # table
        A.box((.04, .04, .54), (-.28, -.62, .27), 'blue_soft', bevel=0, detail=True)
        A.col_box((1.04, 1.94, .66), (0, 0, .33))


@prop('Standpipe', ['standpipe'], variants=['A', 'B'], data_size=[0.4, 0.4, 0], variant_rule='A green, B blue (stable hash of id % 2)',
      front='spout to Blender -Y (Unity +Z)', collider_note='Thin box 0.2 x 0.2 x 1.1.',
      notes='Soviet street water column (vodorazbornaya kolonka): cast-iron column, lever handle, spout with bucket hook, concrete pad.')
def standpipe(A, v):
    c = 'green_dark' if v == 'A' else 'blue'
    A.box((.4, .4, .08), (0, 0, .04), 'concrete', bevel=.015)
    A.lathe([(.11, .08), (.11, .14), (.085, .2), (.075, .55), (.07, .9), (.08, .95), (.095, 1.0), (.095, 1.06), (.06, 1.11), (0, 1.13)],
            (0, 0, 0), c, n=12)
    A.torus(.078, .012, (0, 0, .62), 'black_iron', n=12, m=4, detail=True)
    A.beam((0, -.06, .78), (0, -.21, .76), .028, c, n=8)
    A.beam((0, -.21, .77), (0, -.23, .68), .026, c, n=8)
    A.bar((0, -.2, .58), (0, -.24, .58), .015, .012, 'black_iron', detail=True)
    A.bar((0, -.24, .58), (0, -.24, .64), .015, .012, 'black_iron', detail=True)
    A.box((.05, .06, .06), (0, .02, 1.12), 'black_iron', bevel=0)
    A.bar((0, .02, 1.14), (0, .5, 1.24), .03, .035, 'black_iron')
    A.sphere(.03, (0, .52, 1.245), 'black_iron', seg=6, rings=4, detail=True)
    A.col_box((.22, .22, 1.12), (0, 0, .56))


@prop('FishingNets', ['fishing_nets'], data_size=[2.2, 0.3, 0], collider_note='None (line visuals have no blocking collider per data).',
      notes='Net hung between two leaning stakes on the river bank, cork floats on the head rope, lead line at the bottom, two torn holes.')
def fishing_nets(A, v):
    for x, lean in ((-1.08, -4), (1.08, 5)):
        A.cyl(.04, 1.95, (x, 0, 0), 'wood_weathered', n=7, rot=(0, lean, 0))
        A.cyl(.03, .05, (x + math.sin(math.radians(lean)) * 1.95, 0, 1.95 * math.cos(math.radians(lean))), 'wood_dark', n=6, bevel=0, detail=True)
    top = [(-1.0 + i * .25, 0, 1.78 - .14 * math.sin(math.pi * i / 8)) for i in range(9)]
    A.sweep(top, .012, 'rope', n=4)
    bot = [(-0.95 + i * .2375, .06, .32 - .05 * math.sin(math.pi * i / 8)) for i in range(9)]
    A.sweep(bot, .016, 'dark_grey', n=4)
    def at(u, w):
        x = -1.0 + 2.0 * u
        zt = 1.78 - .14 * math.sin(math.pi * u); zb = .32 - .05 * math.sin(math.pi * u)
        y = .06 * w + .08 * math.sin(math.pi * u) * math.sin(math.pi * w)
        return (x, y, zt + (zb - zt) * w)
    A.grid_strips(None, 8, 6, .012, 'net_green', holes={(2, 2), (2, 3), (3, 3), (6, 4)}, at=at)
    for i in range(1, 8):
        p = top[i]
        A.cyl(.03, .07, (p[0] - .035, 0, p[2] + .005), 'cork', n=6, rot=(0, 90, 0), bevel=0)


@prop('NetDryingRack', ['net_drying_rack'], data_size=[2.5, 0.3, 0], collider_note='Two thin boxes on the trestles; net has none.',
      notes='Two X-trestles with a pole, net drying over it on both sides, cork floats, one float line hanging.')
def net_rack(A, v):
    for x in (-1.12, 1.12):
        for s in (-1, 1):
            A.beam((x, s * .42, 0), (x, -s * .12, 1.75), .035, 'wood_weathered', n=6)
        A.col_box((.1, .7, 1.6), (x, 0, .8))
    A.beam((-1.3, .07, 1.52), (1.3, .07, 1.52), .04, 'wood_fresh', n=7)
    for s in (-1, 1):
        def at(u, w, s=s):
            x = -1.0 + 2.0 * u
            return (x, .07 + s * (.05 + .3 * w), 1.5 - 1.0 * w + .06 * math.sin(math.pi * u) * w)
        A.grid_strips(None, 8, 4, .012, 'net_brown', holes={(5, 3)} if s > 0 else {(1, 2), (2, 2)}, at=at)
        for i in range(1, 8):
            x = -1.0 + i * .25
            A.cyl(.028, .06, (x - .03, .07 + s * .37, .52), 'cork', n=6, rot=(0, 90, 0), bevel=0, detail=True)


@prop('ReedClump', ['reed_clump'], variants=['A', 'B'], data_size=[1.5, 1.0, 0], variant_rule='stable hash of id % 2',
      collider_note='None (decorative, walk-through).', notes='Pond-margin reeds with cattails; A green, B taller and drier.')
def reeds(A, v):
    n = 34 if v == 'A' else 40
    if A.lod:
        n //= 2
    cols = ['reed', 'leaf_light', 'reed', 'reed_dry'] if v == 'A' else ['reed_dry', 'reed', 'reed_dry', 'ochre']
    hmax = 1.55 if v == 'A' else 1.9
    for i in range(n):
        a = A.rng.uniform(0, math.tau); r = math.sqrt(A.rng.random())
        x, y = .68 * r * math.cos(a), .45 * r * math.sin(a)
        h = hmax * A.rng.uniform(.55, 1.0) * (1 - .3 * r)
        dx, dy = A.rng.uniform(-.25, .25) + x * .3, A.rng.uniform(-.2, .2) + y * .3
        pts = [(x, y, 0), (x + dx * .3, y + dy * .3, h * .55), (x + dx, y + dy, h)]
        A.sweep(pts, .02, cols[i % 4], n=3, radii=[.022, .015, .002])
    for i in range(5 if v == 'A' else 7):
        a = A.rng.uniform(0, math.tau); r = .5 * math.sqrt(A.rng.random())
        x, y = .6 * r * math.cos(a), .4 * r * math.sin(a)
        h = hmax * A.rng.uniform(.85, 1.05)
        A.beam((x, y, 0), (x + .05, y, h), .008, 'reed', n=4)
        A.cyl(.03, .18, (x + .05, y, h - .3), 'cattail', n=6, bevel=0)
