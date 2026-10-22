"""Construction site + its fuel station static props (M2). Blender frame = W85 box frame (X = size[0], Y = size[1], Z up).
Palette leans on C2 (warm concrete, red / white accents)."""
import math
from m2reg import prop
import parts


@prop('AirWaterPost', ['air_water_post'], data_size=[0.5, 0.5, 1.4], front='display and hoses at Unity +Z (Blender -Y)',
      collider_note='Box 0.38 x 0.3 x 1.35.', notes='Fuel-station air / water post: cabinet, blank display, coiled air and water hoses. No text.')
def air_water(A, v):
    A.box((.46, .4, .08), (0, 0, .04), 'concrete', bevel=.015)
    A.box((.36, .28, 1.1), (0, 0, .08 + .55), 'red', bevel=.03)
    A.box((.4, .32, .1), (0, 0, 1.23), 'white_paint', bevel=.025)
    A.box((.22, .02, .14), (0, -.145, 1.0), 'display_green', bevel=0)
    A.box((.26, .025, .2), (0, -.142, 1.0), 'charcoal', bevel=0)
    A.box((.3, .02, .06), (0, -.145, 1.16), 'white_paint', bevel=0, detail=True)
    for x, c in ((-.21, 'rubber'), (.21, 'plastic_green')):
        A.box((.04, .06, .06), (x * .85, -.06, .8), 'steel_dark', bevel=0)
        A.torus(.13, .016, (x, -.06, .66), c, n=12, m=4, rot=(0, 90, 0))
        A.sweep([(x, -.06, .53), (x * 1.05, -.12, .45), (x * .9, -.16, .5)], .016, c, n=4, detail=True)
    A.col_box((.38, .3, 1.35), (0, 0, .67))


@prop('PricePylonBlank', ['price_pylon_blank'], data_size=[1.2, 0.4, 4.0], collider_note='Two leg boxes + cabinet box.',
      notes='Fuel price pylon without text (v02 par. 11): double-sided cabinet with a red header, a round colour mark and '
            'blank dark price plates with colour tabs.')
def price_pylon(A, v):
    for x in (-.38, .38):
        A.box((.16, .26, 2.45), (x, 0, 1.225), 'dark_grey', bevel=.02)
        A.box((.3, .38, .1), (x, 0, .05), 'concrete', bevel=.015)
        A.col_box((.16, .26, 2.45), (x, 0, 1.225))
    A.box((1.2, .32, 1.6), (0, 0, 2.4 + .8), 'white_paint', bevel=.03)
    A.box((1.22, .34, .3), (0, 0, 3.85), 'red', bevel=.03)
    for sy in (-1, 1):
        A.cyl(.16, .02, (0, sy * .165, 3.5), 'red', n=14, rot=(90 * sy, 0, 0), bevel=0)
        A.cyl(.08, .02, (0, sy * .175, 3.5), 'white_paint', n=10, rot=(90 * sy, 0, 0), bevel=0, detail=True)
        for k, tab in enumerate(('yellow', 'green', 'blue')):
            z = 3.08 - k * .32
            A.box((.62, .02, .24), (.15, sy * .165, z), 'charcoal', bevel=0)
            A.box((.22, .02, .24), (-.33, sy * .165, z), tab, bevel=0)
    A.col_box((1.2, .32, 1.6), (0, 0, 3.2))


@prop('BioToilet', ['bio_toilet', 'portable_toilet'], variants=['A', 'B', 'C'], data_size=[1.2, 1.2, 2.3],
      variant_rule='construction: A blue x2, C orange x1, B green x1; port portable_toilet: A', front='door at Unity +Z (Blender -Y)',
      collider_note='Box 1.12 x 1.12 x 2.3.', notes='Portable plastic toilet: ribbed shell, translucent white roof, door with vents and latch, vent pipe. A blue, B green, C orange.')
def bio_toilet(A, v):
    c = {'A': 'plastic_blue', 'B': 'plastic_green', 'C': 'plastic_orange'}[v]
    A.box((1.16, 1.16, .1), (0, 0, .05), 'plastic_grey', bevel=.02)
    A.box((1.08, 1.08, 2.0), (0, 0, .1 + 1.0), c, bevel=.06)
    for s in (-1, 1):
        for k in (-.3, 0, .3):
            A.box((.04, .1, 1.7), (s * .55, k, 1.05), c, bevel=.012, detail=True)
            A.box((.1, .04, 1.7), (k, .55, 1.05), c, bevel=.012, detail=True) if s > 0 else None
    A.box((1.16, 1.16, .1), (0, 0, 2.15), 'plastic_white', bevel=.03)
    A.box((1.1, 1.1, .14), (0, 0, 2.2 + .07), 'plastic_white', taper=(.75, .75), bevel=.02)
    A.box((.8, .05, 1.85), (0, -.555, .2 + .925), c, bevel=.02)
    for k in range(3):
        A.box((.5, .02, .03), (0, -.585, 1.85 + k * .07), 'charcoal', bevel=0)
    A.box((.08, .03, .05), (.28, -.59, 1.25), 'green' if v != 'B' else 'red', bevel=0, detail=True)
    A.box((.03, .05, .2), (.3, -.6, 1.05), 'plastic_grey', bevel=0)
    A.cyl(.04, .4, (.38, .38, 2.1), 'plastic_grey', n=8)
    A.col_box((1.12, 1.12, 2.3), (0, 0, 1.15))


@prop('SiteBin', ['bin'], data_size=[0.6, 0.6, 1.0], collider_note='Box 0.5 x 0.5 x 1.0.',
      notes='Fuel-station litter bin: galvanised square body, green flap lid, short legs.')
def site_bin(A, v):
    for x in (-.2, .2):
        for y in (-.2, .2):
            A.box((.05, .05, .1), (x, y, .05), 'steel_dark', bevel=0)
    A.box((.48, .48, .78), (0, 0, .1 + .39), 'steel_galv', taper=(1.04, 1.04), bevel=.02)
    A.box((.54, .54, .1), (0, 0, .93), 'green_dark', bevel=.02)
    A.box((.3, .04, .12), (0, -.27, .86), 'charcoal', bevel=0)
    A.col_box((.5, .5, 1.0), (0, 0, .5))


@prop('ClothesLine', ['clothes_line'], data_size=[12.0, 0.1, 1.8], collider_note='None (thin posts and lines).',
      notes='Workers\' clothes line at the site huts: three T-posts, two sagging lines, overalls, shirts, towels.')
def clothes_line(A, v):
    for x in (-5.9, 0, 5.9):
        A.cyl(.03, 1.85, (x, 0, 0), 'steel_dark', n=6)
        A.box((.05, .5, .05), (x, 0, 1.8), 'steel_dark', bevel=0)
    for y in (-.2, .2):
        for x0, x1 in ((-5.9, 0), (0, 5.9)):
            pts = [(x0 + (x1 - x0) * k / 6, y, 1.78 - .12 * math.sin(math.pi * k / 6)) for k in range(7)]
            A.sweep(pts, .008, 'rope', n=3)
    items = [(-4.9, -.2, 'overall_orange', (.5, .9)), (-3.9, -.2, 'shirt_white', (.55, .6)), (-2.6, .2, 'denim', (.45, .85)),
             (-1.4, -.2, 'towel_blue', (.5, .7)), (1.2, .2, 'overall_orange', (.5, .9)), (2.3, -.2, 'shirt_green', (.55, .6)),
             (3.5, .2, 'shirt_white', (.5, .45)), (4.6, -.2, 'red', (.45, .55))]
    for x, y, c, (w, h) in items:
        t = ((x + 5.9) / 5.9) if x < 0 else (x / 5.9)
        z = 1.78 - .12 * math.sin(math.pi * t)
        A.box((w, .025, h), (x, y, z - h / 2), c, bevel=0, rot=(0, 0, A.rng.uniform(-4, 4)))
        if c == 'overall_orange':
            A.box((.04, .026, .25), (x - .12, y, z - h - .1), c, bevel=0, detail=True)
            A.box((.18, .026, .25), (x + .12, y, z - h - .1), c, bevel=0, detail=True)


@prop('FireBarrel', ['fire_barrel'], data_size=[1.0, 1.0, 1.0], collider_note='Box 0.62 x 0.62 x 0.95.',
      notes='Rusty steel drum used as a fire barrel on two bricks: glowing vent holes, charred wood sticking out, embers on top (emissive).')
def fire_barrel(A, v):
    for x in (-.14, .14):
        A.box((.24, .12, .07), (x, 0, .035), 'brick', bevel=.01)
    A.lathe([(0, .07), (.28, .07), (.29, .09), (.29, .33), (.3, .35), (.29, .37), (.29, .63), (.3, .65), (.29, .67),
             (.29, .93), (.3, .95)], (0, 0, 0), 'rust', n=14, cap_top=False)
    A.tube(.3, .275, .02, (0, 0, .93), 'rust_dark', n=14)
    A.cyl(.27, .02, (0, 0, .8), 'ember', n=12, bevel=0)
    for k in range(6):
        a = k * math.tau / 6 + .3
        A.box((.09, .02, .06), (.292 * math.cos(a), .292 * math.sin(a), .2), 'ember', rot=(0, 0, math.degrees(a) + 90), bevel=0)
    for k, (a, tilt) in enumerate(((0, 25), (2.1, 35), (4.2, 20))):
        A.beam((.1 * math.cos(a), .1 * math.sin(a), .75), (.24 * math.cos(a), .24 * math.sin(a), 1.12 + .03 * k), .045, 'charred', n=6)
    A.col_box((.62, .62, .95), (0, 0, .47))


@prop('FormworkPanels', ['formwork_panels'], data_size=[4.8, 2.0, 1.2], collider_note='Two boxes (one per stack).',
      notes='Two stacks of framed formwork panels (red steel frames, yellow plywood faces) on timber bearers.')
def formwork_panels(A, v):
    for x, n in ((-1.2, 8), (1.2, 6)):
        A.rng.seed(int(x * 10) + 7)
        sub = _formwork_stack_at(A, x, 2.3, 1.9, n)
        A.col_box((2.35, 1.95, sub), (x, 0, sub / 2))


def _formwork_stack_at(A, x0, L, W, n):
    for x in (-L / 2 + .3, L / 2 - .3):
        A.box((.14, W + .1, .12), (x0 + x, 0, .06), 'wood_weathered', bevel=.015)
    z = .12
    for i in range(n):
        j = (A.rng.uniform(-.03, .03), A.rng.uniform(-.03, .03))
        A.box((L, W, .1), (x0 + j[0], j[1], z + .05), 'formwork_red', bevel=.012)
        A.box((L - .07, W - .07, .02), (x0 + j[0], j[1], z + .1), 'formwork_yellow', bevel=0)
        z += .12
    return z


@prop('FormworkShields', ['formwork_shields'], data_size=[6.8, 1.4, 1.2], collider_note='Three boxes (one per stack).',
      notes='Three stacks of timber board shields (planks nailed on battens) on bearers.')
def formwork_shields(A, v):
    for k, x in enumerate((-2.25, 0, 2.25)):
        for bx in (-.8, .8):
            A.box((.12, 1.4, .1), (x + bx, 0, .05), 'wood_weathered', bevel=.015)
        z = .1
        for i in range((6, 5, 7)[k]):
            j = A.rng.uniform(-.04, .04)
            for b in range(3):
                A.box((.08, 1.3, .04), (x + j - .7 + b * .7, 0, z + .02), 'wood_dark', bevel=0, detail=True)
            A.box((2.1, 1.3, .03), (x + j, 0, z + .055), 'plywood' if i % 2 else 'wood_fresh', bevel=0)
            z += .075 if A.lod else .085
        A.col_box((2.15, 1.35, z), (x, 0, z / 2))


@prop('FormworkStack', ['formwork_stack'], data_size=[12.4, 1.6, 1.0], collider_note='One box 12.4 x 1.5 x 1.0.',
      notes='Stack of yellow timber formwork beams (H20-type) with red ends on three bearers.')
def formwork_stack(A, v):
    for x in (-5, 0, 5):
        A.box((.15, 1.6, .12), (x, 0, .06), 'wood_weathered', bevel=.015)
    rows, cols = 5, 7
    for r in range(rows):
        for c in range(cols):
            if r == rows - 1 and c in (0, 6):
                continue
            y = -.66 + c * .22
            z = .12 + r * .2 + .1
            dx = A.rng.uniform(-.08, .08)
            A.box((12.0, .08, .2), (dx, y, z), 'formwork_yellow', bevel=0)
            for s in (-1, 1):
                A.box((.12, .085, .205), (dx + s * 6.0, y, z), 'formwork_red', bevel=0, detail=(r < rows - 1 and c not in (0, 6)))
    A.col_box((12.4, 1.5, 1.0), (0, 0, .5))


@prop('GravelPile', ['gravel_pile'], data_size=[5.2, 4.4, 1.5], collider_note='Convex hull of the heap (walkable).',
      notes='Heap of crushed stone with a few larger stones at the foot.')
def gravel_pile(A, v):
    hull = A.mound(2.6, 2.2, 1.5, (0, 0, 0), 'gravel', rings=5, segs=18, noise=.07, power=.75)
    for k in range(9):
        a = k * math.tau / 9 + .2
        A.ico(.12 + .05 * (k % 3), (2.4 * math.cos(a), 2.0 * math.sin(a), .05), 'gravel_dark' if k % 2 else 'rock_light', subdiv=1, detail=True)
    A.col_hull(hull)


@prop('SandPile', ['sand_pile'], data_size=[7.2, 6.0, 1.8], collider_note='Convex hull of the heap (walkable).',
      notes='Heap of building sand with a shovel stuck in it.')
def sand_pile(A, v):
    hull = A.mound(3.6, 3.0, 1.8, (0, 0, 0), 'sand', rings=5, segs=20, noise=.05, power=.6, facet=False)
    A.mound(1.4, 1.1, .45, (2.6, -1.6, 0), 'sand_dark', rings=3, segs=10, noise=.08, power=.7, facet=False)
    A.beam((.9, -.6, 1.25), (1.5, -1.0, 2.3), .022, 'wood_fresh', n=6)
    A.box((.24, .03, .3), (.86, -.57, 1.18), 'steel_dark', rot=(0, -25, 30), bevel=0)
    A.col_hull(hull)


@prop('IceChest', ['ice_chest'], data_size=[1.6, 0.8, 1.0], front='Unity +Z (Blender -Y)', collider_note='Box 1.52 x 0.76 x 0.98.',
      notes='Fuel-station ice chest / freezer: white body with a blue band, blue lid with handle, dark base. No text.')
def ice_chest(A, v):
    A.box((1.5, .74, .08), (0, 0, .04), 'charcoal', bevel=.015)
    A.box((1.5, .74, .78), (0, 0, .08 + .39), 'plastic_white', bevel=.04)
    A.box((1.52, .76, .16), (0, 0, .55), 'blue_soft', bevel=.02)
    A.box((1.54, .78, .1), (0, 0, .91), 'blue', bevel=.03)
    A.box((.5, .05, .04), (0, -.41, .9), 'steel_galv', bevel=0)
    A.box((.12, .04, .06), (.6, -.39, .8), 'charcoal', bevel=0, detail=True)
    A.col_box((1.52, .76, .98), (0, 0, .49))


def _brick_cube(A, loc, blocks=False):
    x, y, z = loc
    rows = 6
    h = .82 / rows
    for r in range(rows):
        inset = .01 if r % 2 else 0
        zc = z + h * (r + .5)
        if blocks:
            for k, yy in enumerate((-.3, .3)):
                A.box((1.0 - inset, .58, h - .014), (x, y + yy, zc), 'concrete' if (r + k) % 2 else 'concrete_dark', bevel=0)
        else:
            A.box((1.0 - inset, 1.18 - inset, h - .01), (x, y, zc), 'brick' if r % 2 else 'brick_dark', bevel=0)
    for yy in (-.35, .35):
        A.box((1.03, .04, .01), (x, y + yy, z + .825), 'charcoal', bevel=0, detail=True)
        for sx in (-1, 1):
            A.box((.01, .04, .82), (x + sx * .51, y + yy, z + .41), 'charcoal', bevel=0, detail=True)


def _pallet_cubes(A, v, blocks):
    spots = [(-.78, -.78), (.78, -.78), (-.78, .78), (.78, .78)]
    for k, (x, y) in enumerate(spots):
        top = parts.pallet(A, (x, y, 0), 90 + A.rng.uniform(-3, 3), top=False, dx=1.2, dy=1.0)
        if v == 'B' and k == 3:
            for j in range(4):
                A.box((.39 if blocks else .23, .19 if blocks else .11, .19 if blocks else .07),
                      (x + A.rng.uniform(-.3, .3), y + A.rng.uniform(-.3, .3), top + .05), 'concrete' if blocks else 'brick',
                      rot=(0, 0, A.rng.uniform(0, 90)), bevel=0)
            A.col_box((1.0, 1.2, .2), (x, y, .1))
            continue
        _brick_cube(A, (x, y, top), blocks)
        A.col_box((1.0, 1.2, top + .83), (x, y, (top + .83) / 2))


@prop('PalletBricks', ['pallet_bricks'], variants=['A', 'B'], data_size=[3.2, 3.2, 1.2], variant_rule='stable hash of id % 2',
      collider_note='One box per loaded pallet.', notes='Four pallets of strapped red bricks; B has one pallet half emptied.')
def pallet_bricks(A, v):
    _pallet_cubes(A, v, False)


@prop('PalletBlocks', ['pallet_blocks'], variants=['A', 'B'], data_size=[3.2, 3.2, 1.2], variant_rule='stable hash of id % 2',
      collider_note='One box per loaded pallet.', notes='Four pallets of strapped grey concrete blocks; B has one pallet emptied.')
def pallet_blocks(A, v):
    _pallet_cubes(A, v, True)


def _pipe_pyramid(A, L, r, counts, col_fn, chock_x):
    for x in chock_x:
        A.box((.15, (counts[0]) * 2 * r + .3, .1), (x, 0, .05), 'wood_weathered', bevel=.015)
    z = .1 + r
    k = 0
    for row, n in enumerate(counts):
        for i in range(n):
            y = (i - (n - 1) / 2) * 2 * r * 1.01
            dx = A.rng.uniform(-.1, .1)
            A.tube(r, r * .8, L, (dx - L / 2, y, z), col_fn(k), n=10, rot=(0, 90, 0))
            k += 1
        z += r * 2 * .87
    return z - r * .87 + r


@prop('PipeStackSite', ['pipe_stack (construction, 12.4 x 0.8 x 0.8)'], variants=['A', 'B'], data_size=[12.4, 0.8, 0.8],
      variant_rule='A steel, B orange PVC sewer pipes (mix on site)', collider_note='One box 12.4 x 0.8 x 0.8.',
      notes='Pyramid of six pipes (3-2-1) on timber chocks; A dark steel, B orange PVC.')
def pipe_stack_site(A, v):
    col = 'steel_dark' if v == 'A' else 'plastic_orange'
    _pipe_pyramid(A, 12.0, .13, (3, 2, 1), lambda k: col, (-5, 0, 5))
    A.col_box((12.4, .8, .75), (0, 0, .375))


@prop('RebarBundles', ['rebar_bundles'], data_size=[13.0, 3.0, 0.5], collider_note='One low box 12.4 x 2.8 x 0.45.',
      notes='Five tied bundles of rebar on three bearers, bar ends sticking out, a few loose bars on top.')
def rebar(A, v):
    for x in (-5, 0, 5):
        A.box((.16, 3.0, .12), (x, 0, .06), 'wood_weathered', bevel=.015)
    for i, y in enumerate((-1.1, -.55, 0, .55, 1.1)):
        L = 12.0 - .3 * (i % 2)
        A.cyl(.1, L, (-L / 2, y, .22), 'rust', n=8, rot=(0, 90, 0), bevel=0)
        for x in (-4, 0, 4):
            A.cyl(.106, .04, (x, y, .22), 'charcoal', n=8, rot=(0, 90, 0), bevel=0, detail=True)
        for s in (-1, 1):
            for k in range(5):
                a = k * math.tau / 5 + i
                p = (s * L / 2, y + .055 * math.cos(a), .22 + .055 * math.sin(a))
                A.beam(p, (p[0] + s * A.rng.uniform(.1, .45), p[1], p[2]), .012, 'rust_dark', n=4, detail=True)
    for k in range(3):
        A.beam((-4 + 3 * k, -1.2 + k * .5, .34), (2 + 2.5 * k, -.4 + k * .6, .34), .013, 'rust_dark', n=4)
    A.col_box((12.4, 2.8, .45), (0, 0, .225))


@prop('ScrapMetalPile', ['scrap_metal_pile'], data_size=[4.8, 3.2, 1.4], collider_note='Convex hull of the base heap.',
      notes='Heap of scrap: rusty base, bent sheets, pipes, an I-beam, a wheel with tyre, a painted panel.')
def scrap_pile(A, v):
    hull = A.mound(2.3, 1.5, .75, (0, 0, 0), 'rust_dark', rings=3, segs=12, noise=.15)
    pieces = [((1.6, .9, .03), (-.6, .2, .7), (20, 15, 30), 'rust'), ((1.2, .7, .03), (.7, -.3, .55), (-25, 10, -20), 'steel_galv'),
              ((1.0, .6, .03), (.2, .6, .8), (35, -20, 60), 'blue'), ((.9, .9, .03), (-1.3, -.5, .35), (10, 40, 0), 'rust_light'),
              ((.7, .5, .03), (1.5, .4, .3), (-15, -35, 10), 'red_dark')]
    for size, loc, rot, c in pieces:
        A.box(size, loc, c, rot=rot, bevel=0)
    A.beam((-1.8, .6, .3), (.6, 1.0, 1.15), .07, 'rust', n=8)
    A.beam((-.4, -1.1, .2), (1.9, -.2, .5), .05, 'steel_dark', n=6)
    for dz, w, h in ((0, .1, .26),):
        A.box((2.2, .1, .02), (.1, .1, 1.0), 'rust_dark', rot=(0, -12, 18), bevel=0)
        A.box((2.2, .02, .24), (.1, .1, 1.0), 'rust_dark', rot=(0, -12, 18), bevel=0)
    A.torus(.33, .1, (1.2, .9, .55), 'tyre', n=12, m=5, rot=(70, 0, 20))
    A.cyl(.22, .18, (1.2, .9, .55), 'steel_dark', n=10, rot=(70, 0, 20))
    A.col_hull(hull)


@prop('SmokingShelter', ['smoking_shelter'], data_size=[4.4, 3.2, 2.4], front='open side at Unity +Z (Blender -Y)',
      collider_note='4 post boxes, back-wall box, roof box.',
      notes='Workers\' smoking shelter (kurilka): steel posts, red profiled mono-pitch roof, galvanised half-walls, bench, red ash bucket with sand.')
def smoking_shelter(A, v):
    X, Y = 2.0, 1.4
    for x in (-X, X):
        for y in (-Y, Y):
            h = 2.25 if y < 0 else 2.05
            A.box((.08, .08, h), (x, y, h / 2), 'steel_dark', bevel=0)
            A.col_box((.08, .08, h), (x, y, h / 2))
    ang = math.degrees(math.atan2(.2, 2 * Y))
    A.box((4.4, 3.2, .04), (0, 0, 2.17), 'red', rot=(-ang, 0, 0), bevel=0)
    for k in range(12):
        x = -2.1 + k * .38
        A.box((.05, 3.2, .04), (x, 0, 2.2), 'red_dark', rot=(-ang, 0, 0), bevel=0, detail=True)
    A.box((4.0, .04, 1.1), (0, Y, .3 + .55), 'steel_galv', bevel=0)
    for x in (-X, X):
        A.box((.04, 2.8, 1.1), (x, 0, .3 + .55), 'steel_galv', bevel=0)
    for k in range(10):
        A.box((.04, .05, 1.1), (-1.8 + k * .4, Y - .03, .85), 'steel_dark', bevel=0, detail=True)
    A.box((3.6, .38, .05), (0, Y - .3, .45), 'wood_fresh', bevel=.01)
    for x in (-1.6, 0, 1.6):
        A.box((.06, .3, .43), (x, Y - .3, .215), 'steel_dark', bevel=0)
    A.cyl(.17, .35, (-1.5, -Y + .35, 0), 'red', n=10, r2=.2)
    A.cyl(.18, .03, (-1.5, -Y + .35, .31), 'sand', n=10, bevel=0)
    A.col_box((4.0, .1, 1.4), (0, Y, .7)); A.col_box((4.4, 3.2, .2), (0, 0, 2.2))


@prop('TyreStack', ['tyre_stack'], variants=['A', 'B'], data_size=[1.0, 1.0, 1.2], variant_rule='stable hash of id % 2',
      collider_note='Box 0.95 x 0.95 x 1.2 (A) / 0.95 x 0.95 x 0.75 (B).', notes='A: five stacked truck tyres. B: three stacked plus one leaning.')
def tyre_stack(A, v):
    n = 5 if v == 'A' else 3
    for i in range(n):
        A.torus(.33, .13, (A.rng.uniform(-.03, .03), A.rng.uniform(-.03, .03), .12 + i * .235), 'tyre', n=14, m=6, scale=(1, 1, .9))
    if v == 'B':
        A.torus(.33, .13, (.15, -.62, .45), 'tyre', n=14, m=6, rot=(75, 0, 10))
        A.col_box((.95, .95, .75), (0, 0, .375))
    else:
        A.col_box((.95, .95, 1.2), (0, 0, .6))


@prop('WaterTank', ['water_tank'], variants=['A', 'B'], data_size=[3.6, 3.6, 2.4], scale_rule='uniform = data size[0] / 3.6 (3.2 m tank -> 0.889)',
      variant_rule='A blue (3.6 m), B white (3.2 m)', collider_note='Hull of the tank (16-gon prism).',
      notes='Vertical plastic water tank with ribs, top hatch, outlet valve, on a concrete pad.')
def water_tank(A, v):
    c = 'plastic_blue' if v == 'A' else 'plastic_white'
    A.box((3.6, 3.6, .1), (0, 0, .05), 'concrete', bevel=.03)
    A.lathe([(1.55, .1), (1.62, .16), (1.64, .3), (1.64, 2.0), (1.6, 2.1), (1.3, 2.25), (.4, 2.32), (0, 2.33)], (0, 0, 0), c, n=24)
    for z in (.7, 1.3, 1.85):
        A.cyl(1.665, .07, (0, 0, z), c, n=24, bevel=0)
    A.cyl(.3, .1, (0, 0, 2.28), 'plastic_blue' if v == 'B' else 'plastic_white', n=12)
    A.beam((0, -1.6, .35), (0, -1.9, .35), .05, 'plastic_grey', n=8)
    A.cyl(.08, .12, (0, -1.85, .35), 'steel_dark', n=8, detail=True)
    A.torus(.08, .015, (0, -1.85, .5), 'red', n=8, m=4, rot=(0, 0, 0), detail=True)
    A.col_hull([(1.64 * math.cos(k * math.tau / 16), 1.64 * math.sin(k * math.tau / 16), z) for k in range(16) for z in (0, 2.1)] + [(0, 0, 2.33)])


@prop('WheelWash', ['wheel_wash'], data_size=[7.6, 5.2, 0.4], collider_note='Two ramp hulls + a grate box at 0.3 m (van drives over).',
      notes='Drive-over wheel-wash grate with ramps at both ends (drive along X), yellow frame, spray pipes, low blue pump box on the side.')
def wheel_wash(A, v):
    Lg, Wg, h = 4.4, 3.6, .3
    A.box((Lg, Wg, .06), (0, 0, .03), 'charcoal', bevel=0)
    for s in (-1, 1):
        A.box((Lg, .14, h), (0, s * (Wg / 2 - .07), h / 2), 'yellow', bevel=.02)
        A.prism([(0, 0), (1.6, 0), (0, h)], Wg, (s * Lg / 2, Wg / 2 if s > 0 else -Wg / 2, 0), 'steel_dark',
                rot=(90, 0, 0) if s > 0 else (90, 0, 180))
        A.col_hull([(s * Lg / 2, -Wg / 2, 0), (s * Lg / 2, Wg / 2, 0), (s * (Lg / 2 + 1.6), -Wg / 2, 0), (s * (Lg / 2 + 1.6), Wg / 2, 0),
                    (s * Lg / 2, -Wg / 2, h), (s * Lg / 2, Wg / 2, h)])
    for k in range(16):
        x = -Lg / 2 + .2 + k * (Lg - .4) / 15
        A.box((.08, Wg - .28, .1), (x, 0, h - .05), 'steel_galv', bevel=0)
    for s in (-1, 1):
        A.beam((-Lg / 2 + .3, s * (Wg / 2 - .25), h + .08), (Lg / 2 - .3, s * (Wg / 2 - .25), h + .08), .04, 'steel_dark', n=6)
    A.box((1.2, .8, .6), (-1.2, Wg / 2 + .5, .3), 'blue', bevel=.03)
    A.box((1.25, .85, .06), (-1.2, Wg / 2 + .5, .63), 'white_paint', bevel=.01)
    A.sweep([(-.6, Wg / 2 + .5, .35), (0, Wg / 2 + .3, .1), (.6, Wg / 2 - .25, .38)], .04, 'rubber', n=5, detail=True)
    A.col_box((Lg, Wg, h), (0, 0, h / 2))
