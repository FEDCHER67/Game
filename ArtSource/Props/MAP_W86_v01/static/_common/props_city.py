"""Downtown + Rough static props (M2). Blender frame = W85 box frame: X = data size[0], Y = data size[1], Z up.
Blender -Y = Unity +Z."""
import math
from m2reg import prop
import parts


# ------------------------------------------------------------------ DOWNTOWN plaza
@prop('ATM', ['atm'], data_size=[1.0, 1.0, 2.0], front='Unity +Z (Blender -Y); data gives no facing - check on the plaza',
      collider_note='One box 0.8 x 0.62 x 1.95.', notes='Free-standing ATM pillar, blank top lightbox, no brand or text.')
def atm(A, v):
    A.box((.92, .74, .1), (0, 0, .05), 'concrete_dark', bevel=.02)
    A.box((.8, .6, 1.75), (0, 0, .1 + .875), 'navy', bevel=.04)
    A.box((.7, .05, .9), (0, -.31, 1.15), 'light_grey', bevel=.015)
    A.box((.48, .03, .34), (0, -.33, 1.33), 'atm_screen', rot=(-12, 0, 0), bevel=0)
    A.box((.78, .26, .05), (0, -.38, 1.58), 'light_grey', rot=(18, 0, 0), bevel=.012)          # hood over the screen
    A.box((.5, .2, .045), (0, -.4, 1.0), 'steel_dark', rot=(15, 0, 0), bevel=.01)               # keypad shelf
    for i in range(3):
        for j in range(3):
            A.box((.045, .04, .015), (-.06 + j * .06, -.43 + i * .05, 1.035 + i * .013), 'charcoal', rot=(15, 0, 0), bevel=0, detail=True)
    A.box((.12, .03, .02), (.17, -.34, 1.12), 'charcoal', bevel=0, detail=True)               # card slot
    A.box((.3, .03, .05), (0, -.34, .85), 'charcoal', bevel=0)                                 # cash slot
    A.box((.82, .62, .26), (0, 0, 1.98), 'blue_soft', bevel=.03)                               # blank lightbox
    A.box((.7, .01, .14), (0, -.315, 1.98), 'screen_white', bevel=0)
    A.col_box((.8, .62, 1.95), (0, 0, .97))


@prop('BigScreen', ['big_screen'], data_size=[26.9, 0.6, 8.0], placement='facing', rotation_offset_y=90,
      front='Unity +Z (Blender -Y) must face the data rot direction (270 = south onto the plaza)',
      collider_note='One box 26.9 x 0.6 x 8.4.',
      notes='LED screen on the podium edge between the towers, abstract blue / yellow geometric picture as in the approved plaza '
            'reference (no text, no logo). The screen colours are emissive swatches. DATA NOTE: with the box convention the '
            'placeholder ran N-S across the stair; place with Euler(0, 90 - rot_deg, 0) so it runs E-W and faces south.')
def big_screen(A, v):
    W, H, z0 = 26.9, 8.0, .45
    A.box((W, .6, z0), (0, 0, z0 / 2), 'concrete_dark', bevel=.04)
    A.box((W, .6, .38), (0, 0, z0 + H - .38 - .02 + .19), 'charcoal', bevel=.04)
    A.box((W, .6, .38), (0, 0, z0 + .19), 'charcoal', bevel=.04)
    for x in (-W / 2 + .19, W / 2 - .19):
        A.box((.38, .6, H - .4), (x, 0, z0 + H / 2 - .2), 'charcoal', bevel=.04)
    A.box((W - .6, .3, H - .7), (0, .12, z0 + H / 2 - .2), 'dark_grey', bevel=0)
    # picture: slanted bands (bottom x, top x), thin prisms in the XZ plane just in front of the back panel
    w2, zb, zt = (W - .76) / 2, z0 + .38, z0 + H - .42 - .02
    bx = [-w2, -9.0, -3.5, -.8, 4.2, 7.5, w2]
    tx = [-w2, -11.5, -6.0, 1.5, 3.0, 10.5, w2]
    cols = ['screen_navy', 'screen_blue', 'screen_sky', 'screen_white', 'screen_yellow', 'screen_blue']
    for i in range(len(cols)):
        poly = [(bx[i], zb), (bx[i + 1], zb), (tx[i + 1], zt), (tx[i], zt)]
        A.prism(poly, .04, (0, -.03, 0), cols[i], rot=(90, 0, 0))
    # two overlay triangles for the "geometric" read
    A.prism([(-w2 + .05, zb + 2.6), (-6.5, zt - .05), (-w2 + .05, zt - .05)], .04, (0, -.07, 0), 'screen_sky', rot=(90, 0, 0))
    A.prism([(5.0, zb + .05), (w2 - .05, zb + .05), (w2 - .05, zb + 3.4)], .04, (0, -.07, 0), 'screen_yellow', rot=(90, 0, 0))
    # rear service frame
    for x in (-9, -3, 3, 9):
        A.box((.2, .12, H - .8), (x, .27, z0 + H / 2), 'steel_dark', bevel=0, detail=True)
    A.col_box((W, .6, H + z0), (0, 0, (H + z0) / 2))


@prop('BollardYellow', ['bollard_yellow'], data_size=[0.3, 0.3, 1.0], collider_note='Box 0.22 x 0.22 x 1.0 (blocks the van).',
      notes='Steel plaza bollard, yellow, two white reflective bands, dome top, base flange.')
def bollard_yellow(A, v):
    A.cyl(.14, .03, (0, 0, 0), 'steel_dark', n=12, bevel=.008)
    A.lathe([(.1, 0), (.1, .9), (.085, .95), (.05, .985), (0, 1.0)], (0, 0, .02), 'yellow', n=12, cap_top=False)
    for z in (.7, .8):
        A.cyl(.103, .045, (0, 0, z), 'white_paint', n=12, bevel=0)
    A.col_box((.22, .22, 1.0), (0, 0, .5))


@prop('CourtyardGate', ['courtyard_gate'], data_size=[5.8, 0.25, 2.4], collider_note='One box 5.8 x 0.12 x 2.3 (closed gate).',
      notes='Closed double gate of black wrought iron with an arched top, spear finials, scroll rings; no text. Sits between the two GatePier models.')
def courtyard_gate(A, v):
    c = 'black_iron'
    Wl, gap = 2.85, .05
    def top(x):     # arch: 2.05 at the outer edges, 2.4 at the centre
        return 2.05 + .35 * math.cos(math.pi * x / 5.8)
    for s in (-1, 1):
        x0, x1 = s * gap, s * (gap + Wl)
        xs = sorted((x0, x1))
        mid = (xs[0] + xs[1]) / 2
        for z in (.1, .55, 1.75):
            A.box((Wl, .05, .05), (mid, 0, z), c, bevel=0)
        for x in xs:
            A.box((.07, .07, top(x) + .05), (x, 0, (top(x) + .05) / 2), c, bevel=0)
        pts = [(xs[0] + (xs[1] - xs[0]) * k / 8, 0, top(xs[0] + (xs[1] - xs[0]) * k / 8)) for k in range(9)]
        A.sweep(pts, .03, c, n=4)
        n = 15
        for k in range(1, n):
            x = xs[0] + (xs[1] - xs[0]) * k / n
            h = top(x) + .1
            A.box((.022, .022, h - .1), (x, 0, .1 + (h - .1) / 2), c, bevel=0)
            A.cyl(.03, .1, (x, 0, h), c, n=4, r2=.002, bevel=0, detail=True)
        for k in range(3):
            A.torus(.11, .014, (mid - .7 + k * .7, 0, .325), c, n=8, m=3, rot=(90, 0, 0), detail=True)
    A.box((.16, .06, .25), (.13, -.04, 1.05), c, bevel=0, detail=True)        # lock box
    A.col_box((5.8, .12, 2.3), (0, 0, 1.15))


@prop('GatePier', ['gate_pier'], data_size=[0.6, 0.6, 2.8], collider_note='Box 0.62 x 0.62 x 2.45.',
      notes='Brick gate pier with corner pilasters, stone plinth and cap, iron lantern (emissive warm glass) on top.')
def gate_pier(A, v):
    A.box((.64, .64, .3), (0, 0, .15), 'stone_warm', bevel=.02)
    A.box((.52, .52, 1.95), (0, 0, .3 + .975), 'brick_dark', bevel=.01)
    for x in (-.24, .24):
        for y in (-.24, .24):
            A.box((.1, .1, 1.95), (x, y, .3 + .975), 'brick', bevel=.008)
    A.box((.62, .62, .08), (0, 0, 2.29), 'stone_warm', bevel=.015)
    A.box((.7, .7, .1), (0, 0, 2.38), 'stone_warm', bevel=.02)
    A.box((.62, .62, .1), (0, 0, 2.48), 'stone_warm', taper=(.6, .6), bevel=.01)
    A.cyl(.06, .08, (0, 0, 2.53), 'black_iron', n=8)
    A.box((.18, .18, .24), (0, 0, 2.73), 'lantern', bevel=0)
    for x in (-.095, .095):
        for y in (-.095, .095):
            A.box((.022, .022, .26), (x, y, 2.73), 'black_iron', bevel=0)
    A.box((.26, .26, .08), (0, 0, 2.89), 'black_iron', taper=(.3, .3), bevel=0)
    A.sphere(.025, (0, 0, 2.95), 'black_iron', seg=6, rings=4, detail=True)
    A.col_box((.64, .64, 2.45), (0, 0, 1.22))


@prop('HedgeTrimmed_2p8', ['hedge_trimmed (size 2.8 x 0.8 x 1.1)'], data_size=[2.8, 0.8, 1.1],
      collider_note='Box 2.8 x 0.8 x 1.1.', notes='Boxwood, flat top, near-sharp corners, low stone planter kerb.')
def hedge_short(A, v):
    parts.hedge(A, 2.8, .8, 1.1)
    A.col_box((2.8, .8, 1.1), (0, 0, .55))


@prop('HedgeTrimmed_29p4', ['hedge_trimmed (size 29.4 x 0.9 x 1.2)'], data_size=[29.4, 0.9, 1.2], budget=2500,
      collider_note='Box 29.4 x 0.9 x 1.2.', notes='Same hedge as HedgeTrimmed_2p8, built at the full 29.4 m length (no stretching).')
def hedge_long(A, v):
    parts.hedge(A, 29.4, .9, 1.2, step=.6)
    A.col_box((29.4, .9, 1.2), (0, 0, .6))


@prop('MonumentTramduro', ['monument_tramduro'], data_size=[4.8, 4.8, 12.0], placement='facing', budget=6000,
      front='figure faces Unity +Z (Blender -Y) = data rot direction (270 = the boulevard, south)',
      collider_note='Round podium as 3 stacked boxes (walkable steps) + drum box + figure box.',
      notes='Golden cartoon leader (round glasses, hair tuft, suit, right arm raised in a wave) on a low dark granite drum and a round '
            'podium of 3 steps, D 8.8 m as in the data notes and the approved plaza picture (wider than the 4.8 m placeholder box). '
            'Parody without likeness to real people. ~11.8 m total.')
def monument(A, v):
    for i, (r, z) in enumerate(((4.4, 0), (3.95, .3), (3.5, .6))):
        A.cyl(r, .3, (0, 0, z), 'granite_dark' if i % 2 == 0 else 'granite', n=32, bevel=.03)
    A.cyl(2.7, 1.1, (0, 0, .9), 'granite_dark', n=32, bevel=.05)
    A.cyl(2.85, .2, (0, 0, 1.9), 'granite', n=32, bevel=.04)
    A.cyl(2.75, .12, (0, 0, .9), 'granite', n=32, bevel=.02)
    A.box((1.2, .04, .45), (0, -2.71, 1.45), 'gold_dark', bevel=0, detail=True)        # blank plaque (no text)
    parts.figure(A, 10.0, (0, 0, 2.1))
    for k, (r, z, h) in enumerate(((4.4, 0, .3), (3.95, .3, .3), (3.5, .6, .3))):
        A.col_box((r * 1.6, r * 1.6, z + h), (0, 0, (z + h) / 2))
    A.col_box((4.4, 4.4, 2.1), (0, 0, 1.05))
    A.col_box((4.0, 2.6, 7.6), (0, 0, 2.1 + 3.8))


@prop('PoliceBooth', ['police_booth'], data_size=[3.2, 3.2, 3.0], front='door at Unity +Z (Blender -Y); data gives no facing',
      collider_note='One box 2.6 x 2.6 x 2.75.', notes='Small glazed police booth: navy lower panels, white fascia with a blue band, blue roof beacon; no text.')
def police_booth(A, v):
    A.box((2.7, 2.7, .15), (0, 0, .075), 'concrete_dark', bevel=.03)
    A.box((2.4, 2.4, .85), (0, 0, .15 + .425), 'navy', bevel=.03)
    A.box((2.3, 2.3, 1.4), (0, 0, 1.0 + .7), 'glass', bevel=0)
    for x in (-1.17, 1.17):
        for y in (-1.17, 1.17):
            A.box((.12, .12, 2.3), (x, y, .15 + 1.15), 'navy', bevel=.015)
    for s in (-1, 1):
        A.box((.06, 2.3, .06), (s * 1.16, 0, 1.73), 'navy', bevel=0)
        A.box((2.3, .06, .06), (0, s * 1.16, 1.73), 'navy', bevel=0)
    A.box((2.5, 2.5, .32), (0, 0, 2.4 + .16), 'white_paint', bevel=.03)
    A.box((2.52, 2.52, .09), (0, 0, 2.56), 'blue', bevel=0)
    A.box((2.85, 2.85, .12), (0, 0, 2.78), 'dark_grey', bevel=.03)
    A.cyl(.2, .06, (0, 0, 2.84), 'charcoal', n=10)
    A.cyl(.12, .16, (0, 0, 2.9), 'beacon_blue', n=10, bevel=.02)
    # door on the front
    A.box((.92, .06, 2.15), (.5, -1.2, .15 + 1.075), 'navy', bevel=.015)
    A.box((.7, .03, 1.2), (.5, -1.235, 1.55), 'glass_dark', bevel=0)
    A.box((.04, .05, .18), (.15, -1.25, 1.2), 'steel_galv', bevel=0, detail=True)
    A.box((.6, .4, .4), (0, 1.38, 1.9), 'light_grey', bevel=.02, detail=True)          # AC unit on the back
    A.col_box((2.6, 2.6, 2.75), (0, 0, 1.38))


@prop('RoundBenchFlowerbed', ['round_bench_flowerbed'], variants=['A', 'B'], data_size=[5.2, 5.2, 0.5],
      variant_rule='alternate A/B along the plaza rows', collider_note='Box 3.6 x 3.6 x 0.48 for the bed + 8 low boxes for the seat ring.',
      notes='Round wooden bench ring around a raised flowerbed (no tree), as in the approved plaza reference. A red / yellow, B purple / white / pink.')
def round_bench(A, v):
    A.tube(1.78, 1.6, .45, (0, 0, 0), 'stone_warm', n=28)
    A.cyl(1.6, .38, (0, 0, 0), 'soil', n=24, bevel=0)
    cols = ['flower_red', 'flower_yellow', 'flower_white'] if v == 'A' else ['flower_purple', 'flower_white', 'flower_pink']
    parts.flower_mound(A, 1.5, .38, cols, n=12 if not A.lod else 7)
    n = 20
    for ring, r in enumerate((2.05, 2.35)):
        for k in range(n):
            a = (k + .5 * ring) * math.tau / n
            A.box((2 * r * math.sin(math.pi / n) * .97, .25, .05), (r * math.cos(a), r * math.sin(a), .455),
                  'wood_bench', rot=(0, 0, math.degrees(a) + 90), bevel=0)
    for k in range(8):
        a = k * math.tau / 8
        A.box((.5, .07, .43), (2.2 * math.cos(a), 2.2 * math.sin(a), .215), 'charcoal', rot=(0, 0, math.degrees(a)), bevel=0)
        A.col_box((.7, .7, .48), (2.2 * math.cos(a), 2.2 * math.sin(a), .24), rot=(0, 0, math.degrees(a)))
    A.col_box((3.56, 3.56, .48), (0, 0, .24))


@prop('PalletStack', ['pallet_stack'], data_size=[2.2, 2.4, 1.2], collider_note='Two boxes, one per stack.',
      notes='Two stacks of empty wooden pallets (8 and 6 high), slightly uneven.')
def pallet_stack(A, v):
    parts.pallet_stack(A, (-.55, 0, 0), 8, rot_z=90, dx=1.2, dy=1.0)
    parts.pallet_stack(A, (.58, .05, 0), 6, rot_z=92, dx=1.2, dy=1.0)
    A.col_box((1.0, 1.2, 1.15), (-.55, 0, .575)); A.col_box((1.0, 1.2, .87), (.58, .05, .43))


def _dispenser(A, loc, rot_z, col):
    x, y, z = loc
    c, s = math.cos(math.radians(rot_z)), math.sin(math.radians(rot_z))
    def L(px, py, pz):
        return (x + px * c - py * s, y + px * s + py * c, z + pz)
    R = (0, 0, rot_z)
    A.box((.62, 1.0, .12), L(0, 0, .06), 'charcoal', rot=R, bevel=.02)
    A.box((.52, .9, 1.3), L(0, 0, .12 + .65), 'white_paint', rot=R, bevel=.04)
    A.box((.58, .96, .36), L(0, 0, 1.42 + .18), col, rot=R, bevel=.04)
    A.box((.6, .98, .06), L(0, 0, 1.81), 'white_paint', rot=R, bevel=.02)
    for sx in (-1, 1):
        A.box((.02, .42, .26), L(sx * .265, -.12, 1.18), 'display_green', rot=R, bevel=0)
        A.box((.03, .5, .34), L(sx * .262, -.12, 1.18), 'charcoal', rot=R, bevel=0)
        for k, py in enumerate((.12, .32)):
            A.box((.1, .1, .16), L(sx * .3, py, .95), 'charcoal', rot=R, bevel=0)
            A.box((.06, .05, .2), L(sx * .34, py, .98), 'black_iron' if k else col, rot=R, bevel=0, detail=True)
            A.sweep([L(sx * .3, py, 1.42), L(sx * .45, py + .02, 1.0), L(sx * .42, py + .03, .55), L(sx * .34, py, .9)],
                    .016, 'rubber', n=4, detail=True)


@prop('FuelPumpSingle', ['fuel_pump_island (size 1.2 x 2.4 x 1.9)'], variants=['A', 'B', 'C'], data_size=[1.2, 2.4, 1.9],
      variant_rule='one variant per station (all 3 Downtown pumps the same, e.g. B); A red, B blue, C green - no brand',
      collider_note='Island box 1.2 x 2.4 x 0.15 + dispenser box 0.55 x 0.95 x 1.85 + 2 bollard boxes.',
      notes='Fuel island (rounded kerb, yellow end bollards) with one double-sided dispenser: displays, nozzles, hoses. No text.')
def fuel_single(A, v):
    col = {'A': 'red', 'B': 'blue', 'C': 'green'}[v]
    A.box((1.2, 1.2, .15), (0, 0, .075), 'concrete', bevel=.03)
    for s in (-1, 1):
        A.cyl(.6, .15, (0, s * .6, 0), 'concrete', n=16, bevel=.03)
        A.cyl(.075, .9, (0, s * 1.02, .15), 'yellow', n=10)
        A.cyl(.077, .1, (0, s * 1.02, .75), 'charcoal', n=10, bevel=0)
        A.col_box((.16, .16, 1.05), (0, s * 1.02, .52))
    _dispenser(A, (0, 0, .15), 0, col)
    A.col_box((1.2, 2.4, .15), (0, 0, .075)); A.col_box((.55, .95, 1.85), (0, 0, 1.07))


@prop('FuelPumpDouble', ['fuel_pump_island (size 5.6 x 1.2 x 1.8)'], variants=['A', 'B', 'C'], data_size=[5.6, 1.2, 1.8],
      variant_rule='Construction station: A (red) to match C2; B / C spare', collider_note='Island box + 2 dispenser boxes + 2 bollard boxes.',
      notes='One long island, 2 dispensers serving both sides (cars N and S), kerb 0.15 m, bollards at the ends (data note). No text.')
def fuel_double(A, v):
    col = {'A': 'red', 'B': 'blue', 'C': 'green'}[v]
    A.box((4.4, 1.2, .15), (0, 0, .075), 'concrete', bevel=.03)
    for s in (-1, 1):
        A.cyl(.6, .15, (s * 2.2, 0, 0), 'concrete', n=16, bevel=.03)
        A.cyl(.075, .9, (s * 2.55, 0, .15), 'yellow', n=10)
        A.cyl(.077, .1, (s * 2.55, 0, .75), 'charcoal', n=10, bevel=0)
        _dispenser(A, (s * 1.2, 0, .15), 90, col)
        A.col_box((.16, .16, 1.05), (s * 2.55, 0, .52)); A.col_box((.95, .55, 1.85), (s * 1.2, 0, 1.07))
    A.col_box((5.6, 1.2, .15), (0, 0, .075))


# ------------------------------------------------------------------ ROUGH
@prop('FootballGoalTornNet', ['football_goal_torn_net'], data_size=[5.0, 1.2, 2.0],
      front='goal mouth opens to Blender +Y = Unity -Z (toward the pitch for both data goals, rot 90 / 270, box convention)',
      collider_note='Boxes for the two posts and the crossbar only (net does not block).',
      notes='Pipe goal, off-white paint with rusty feet, back stanchions, torn and sagging net with holes and a hanging flap.')
def goal(A, v):
    c = 'offwhite'
    X, yf, yb, H = 2.45, .55, -.6, 2.0
    for s in (-1, 1):
        A.cyl(.055, H, (s * X, yf, 0), c, n=8)
        A.cyl(.065, .18, (s * X, yf, 0), 'rust', n=8, bevel=0, detail=True)
        A.beam((s * X, yf, H - .05), (s * X, yb, .05), .035, c, n=6)
        A.beam((s * X, yf, .03), (s * X, yb, .03), .03, c, n=6)
        A.col_box((.12, .12, H), (s * X, yf, H / 2))
    A.cyl(.055, 2 * X + .1, (-X - .05, yf, H), c, n=8, rot=(0, 90, 0))
    A.beam((-X, yb, .03), (X, yb, .03), .03, c, n=6)
    A.col_box((2 * X + .2, .12, .12), (0, yf, H))
    holes = {(2, 1), (3, 1), (3, 2), (2, 2), (7, 3), (8, 3), (8, 2), (6, 0)}
    A.grid_strips(((-X, yf - .02, H - .04), (X, yf - .02, H - .04), (X, yb, .04), (-X, yb, .04)), 10, 5, .014, 'shirt_white',
                  holes=holes, sag=(0, -.12, -.08))
    for s in (-1, 1):
        def at(u, w, s=s):
            # u along the ground (front -> back), w up: triangle (post foot, back foot, post top)
            y = yf + (yb - yf) * u * (1 - w)
            return (s * (X - .01), y, H * w * (1 - .02))
        A.grid_strips(None, 3, 5, .014, 'shirt_white', holes={(1, 2), (2, 1)} if s > 0 else set(), at=at)
    for k, x in enumerate((-.4, -.15, .1, 1.25, 1.5)):                  # hanging torn cords
        A.strip((x, -.1 - .05 * k, .95 - .03 * k), (x + .05, -.05, .45 - .05 * k), .014, 'shirt_white')


@prop('WatchTower', ['watch_tower'], data_size=[5.0, 5.0, 9.0], budget=1800,
      front='ladder and door on Unity +Z (Blender -Y); data gives no facing',
      collider_note='4 leg boxes, platform box (walkable) and cabin box.',
      notes='Border watch tower at the Rough KPP: steel legs with X-bracing, timber cabin with a window band, pyramid roof, '
            'searchlight, ladder. Military green / dark grey, no insignia.')
def watch_tower(A, v):
    leg = 'steel_dark'
    B, T, Zp = 2.25, 1.55, 6.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            A.bar((sx * B, sy * B, 0), (sx * T, sy * T, Zp), .16, .16, leg, up=(0, 0, 1) if False else (sx, -sy, 0))
            A.box((.5, .5, .3), (sx * B, sy * B, .15), 'concrete', bevel=.03)
            A.col_box((.4, .4, Zp), (sx * (B + T) / 2, sy * (B + T) / 2, Zp / 2))
    def lp(z, sx, sy):
        f = z / Zp
        return (sx * (B + (T - B) * f), sy * (B + (T - B) * f), z)
    for z0, z1 in ((.4, 3.1), (3.1, 5.8)):
        for side in range(4):
            sx0, sy0, sx1, sy1 = [(-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)][side]
            A.beam(lp(z0, sx0, sy0), lp(z1, sx1, sy1), .035, leg, n=4)
            A.beam(lp(z0, sx1, sy1), lp(z1, sx0, sy0), .035, leg, n=4)
            A.beam(lp(z1, sx0, sy0), lp(z1, sx1, sy1), .045, leg, n=4)
    A.box((3.6, 3.6, .18), (0, 0, Zp + .09), 'mil_dark', bevel=.03)
    zc = Zp + .18
    A.box((3.0, 3.0, 1.0), (0, 0, zc + .5), 'mil_green', bevel=.03)
    A.box((2.9, 2.9, .85), (0, 0, zc + 1.0 + .425), 'glass_dark', bevel=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            A.box((.12, .12, 1.0), (sx * 1.44, sy * 1.44, zc + 1.42), 'mil_green', bevel=0)
    for s in (-1, 1):
        A.box((.08, 2.9, .08), (s * 1.46, 0, zc + 1.42), 'mil_green', bevel=0, detail=True)
        A.box((2.9, .08, .08), (0, s * 1.46, zc + 1.42), 'mil_green', bevel=0, detail=True)
    A.box((3.1, 3.1, .25), (0, 0, zc + 1.97), 'mil_green', bevel=.03)
    A.box((3.8, 3.8, 1.0), (0, 0, zc + 2.1 + .5), 'dark_grey', taper=(.08, .08), bevel=.03)
    A.cyl(.04, .5, (0, 0, zc + 3.05), 'steel_dark', n=6)
    # searchlight on the front edge of the roof
    A.cyl(.08, .25, (1.2, -1.65, zc + 1.97), 'steel_dark', n=8, detail=True)
    A.cyl(.22, .32, (1.2, -1.55, zc + 2.38), 'mil_dark', n=12, rot=(90, 0, 0))
    A.cyl(.18, .02, (1.2, -1.88, zc + 2.38), 'glass_light', n=12, rot=(90, 0, 0), bevel=0)
    # ladder on the front face up to a hatch
    for x in (-.28, .28):
        A.beam((x, -B - .45, 0), (x, -T - .25, Zp), .03, 'steel_galv', n=4)
    for k in range(1, 20):
        z = k * Zp / 20
        f = z / Zp
        y = (-B - .45) + ((-T - .25) - (-B - .45)) * f
        A.beam((-.28, y, z), (.28, y, z), .016, 'steel_galv', n=4)
    A.box((.8, .06, 1.8), (-.6, -1.53, zc + .9), 'mil_dark', bevel=.01)      # door
    A.col_box((3.6, 3.6, .18), (0, 0, Zp + .09)); A.col_box((3.0, 3.0, 2.0), (0, 0, zc + 1.0))


@prop('LeaveCountryButton', ['leave_country_button'], data_size=[0.4, 0.3, 1.3],
      front='button face looks along local +X (Unity +X, Blender -X) = data rot direction (270 = south, toward the arriving van)',
      collider_note='Box 0.3 x 0.3 x 1.3. Keeps W76LeaveCountryButton on the root.',
      notes='Hazard-striped steel post with a slanted control box and a big red mushroom button (slight glow). No text on the model.')
def leave_button(A, v):
    A.box((.4, .32, .04), (0, 0, .02), 'steel_dark', bevel=.01)
    A.box((.22, .22, 1.0), (0, 0, .04 + .5), 'yellow', bevel=.02)
    for k in range(4):
        A.box((.235, .235, .07), (0, 0, .2 + k * .22), 'charcoal', bevel=0)
    A.box((.34, .3, .2), (0, 0, 1.12), 'dark_grey', rot=(0, 28, 0), bevel=.025)
    A.cyl(.075, .035, (-.08, 0, 1.2), 'steel_galv', n=12, rot=(0, -62, 0), bevel=.008)
    A.lathe([(.07, 0), (.072, .03), (.06, .055), (.03, .068), (0, .072)], (-.11, 0, 1.215), 'button_red', n=12, rot=(0, -62, 0))
    A.cyl(.02, .02, (-.05, .1, 1.17), 'display_green', n=6, rot=(0, -62, 0), bevel=0, detail=True)
    A.col_box((.3, .3, 1.3), (0, 0, .65))


@prop('NeonHeartSign', ['neon_heart_sign'], data_size=[1.0, 0.1, 1.0], y_offset=2.3,
      collider_note='None (wall decoration).',
      notes='Pink neon heart tube (emissive) with wall stand-offs and a small transformer box; plane = X/Z, wall side Blender +Y. '
            'Data box stands on the ground: lift it ~2.3 m onto the club wall.')
def neon_heart(A, v):
    pts = []
    for i in range(44):
        t = i * math.tau / 44
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 17 * .46, -.01, .44 + (z + 2) / 17 * .46))
    A.sweep(pts, .02, 'neon_pink', n=6, closed=True)
    inner = [(p[0] * .78, p[1], .44 + (p[2] - .44) * .78 + .02) for p in pts[::2]]
    A.sweep(inner, .012, 'neon_pink_tube', n=5, closed=True, detail=True)
    for i in (0, 11, 22, 33):
        p = pts[i]
        A.beam((p[0], 0, p[2]), (p[0], .05, p[2]), .008, 'steel_dark', n=4)
    A.box((.16, .04, .1), (0, .03, .1), 'charcoal', bevel=0)


@prop('SlidingGateSteel', ['sliding_gate_steel'], data_size=[8.4, 0.4, 3.2], collider_note='Box 8.4 x 0.2 x 3.2 (closed, blocks the road).',
      notes='One heavy steel sliding gate: tube frame, vertical ribs proud on both faces, red / white striped infill, bottom rollers. '
            'Pairs with GateGuideRail to the east.')
def sliding_gate(A, v):
    L, H, zb = 8.4, 3.2, .14
    A.box((L, .14, .14), (0, 0, zb + .07), 'steel_dark', bevel=.02)
    A.box((L, .14, .14), (0, 0, H - .07), 'steel_dark', bevel=.02)
    for x in (-L / 2 + .07, L / 2 - .07):
        A.box((.14, .14, H - zb), (x, 0, zb + (H - zb) / 2), 'steel_dark', bevel=.02)
    n = 14
    w = (L - .28) / n
    for i in range(n):
        x = -L / 2 + .14 + w * (i + .5)
        A.box((w, .04, H - zb - .28), (x, 0, zb + .14 + (H - zb - .28) / 2), 'red' if i % 2 == 0 else 'white_paint', bevel=0)
        if i:
            A.box((.06, .16, H - zb - .28), (x - w / 2, 0, zb + .14 + (H - zb - .28) / 2), 'steel_dark', bevel=0)
    A.box((L - .28, .12, .08), (0, 0, H / 2 + .1), 'steel_dark', bevel=0)
    for x in (-3.4, 0, 3.4):
        A.cyl(.11, .1, (x - .05, 0, .02), 'black_iron', n=10, rot=(0, 90, 0))
    A.col_box((L, .2, H), (0, 0, H / 2))


@prop('GateGuideRail', ['gate_guide_rail'], data_size=[6.9, 0.3, 0.6], collider_note='Low box 6.9 x 0.3 x 0.2 (+ post box at the far end).',
      notes='Ground guide rail for the sliding gate: concrete strip, steel rail with support rollers, end stop and a roller guide post.')
def guide_rail(A, v):
    A.box((6.9, .34, .1), (0, 0, .05), 'concrete', bevel=.02)
    A.box((6.9, .05, .07), (0, 0, .135), 'steel_dark', bevel=0)
    for x in (-2.8, -1.4, 0, 1.4, 2.8):
        A.box((.2, .26, .08), (x, 0, .14), 'steel_dark', bevel=.01, detail=True)
    A.box((.2, .3, .25), (3.35, 0, .225), 'red', bevel=.02)
    for y in (-.13, .13):
        A.box((.1, .08, .6), (-3.25, y, .3), 'steel_dark', bevel=.01)
    A.cyl(.06, .14, (-3.25, -.07, .5), 'rubber', n=8, rot=(-90, 0, 0), detail=True)
    A.col_box((6.9, .3, .2), (0, 0, .1)); A.col_box((.12, .3, .6), (-3.25, 0, .3))
