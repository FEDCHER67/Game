"""Port static props (M2). Blender frame = W85 box frame (X = size[0], Y = size[1], Z up). P1/P3: cast-iron bollards,
rubber fenders, yellow edge accents, colourful industrial."""
import math
from m2reg import prop
import parts


@prop('BigBags', ['big_bags'], data_size=[3.6, 1.2, 1.2], collider_note='One box 3.5 x 1.15 x 1.15.',
      notes='Three white woven bulk bags (FIBC) with corner lift loops and tied spouts, one with a blue band.')
def big_bags(A, v):
    for k, x in enumerate((-1.2, 0, 1.2)):
        h = 1.08 - .06 * (k == 1)
        A.pillow((1.08, 1.08, h), (x, 0, h / 2), 'bigbag', bulge=.07, cuts=2)
        if k == 2:
            A.box((1.12, 1.12, .08), (x, 0, h * .7), 'blue_soft', bevel=0)
        for sx in (-1, 1):
            for sy in (-1, 1):
                A.torus(.07, .018, (x + sx * .42, sy * .42, h + .03), 'canvas', n=6, m=3, rot=(90, 0, 45 * sx * sy), detail=True)
        A.cyl(.12, .12, (x, 0, h - .02), 'canvas', n=8, r2=.05, detail=True)
    A.col_box((3.5, 1.15, 1.15), (0, 0, .575))


@prop('MooringBollard', ['bollard'], data_size=[0.5, 0.5, 0.7], collider_note='Box 0.36 x 0.36 x 0.7 (keeps W76GripAnchor).',
      notes='Cast-iron mooring bollard on a bolted base plate, black with a yellow painted head rim.')
def mooring_bollard(A, v):
    A.box((.5, .5, .06), (0, 0, .03), 'black_iron', bevel=.015)
    A.lathe([(.17, .06), (.15, .18), (.13, .36), (.135, .46), (.16, .5)], (0, 0, 0), 'black_iron', n=14, cap_bottom=False, cap_top=False)
    A.lathe([(.16, .5), (.22, .54), (.225, .62), (.2, .66), (.0, .68)], (0, 0, 0), 'yellow', n=14, cap_bottom=False)
    for x in (-.19, .19):
        for y in (-.19, .19):
            A.cyl(.025, .03, (x, y, .06), 'steel_dark', n=6, bevel=0, detail=True)
    A.col_box((.36, .36, .7), (0, 0, .35))


@prop('RubberFender', ['rubber_fender'], data_size=[1.2, 0.4, 1.0], y_offset=-1.0,
      front='rubber face to Unity +Z (Blender -Y) = the water side (verified on all 10 data fenders: box convention local +Z points to the sea)',
      collider_note='Box 1.2 x 0.4 x 1.0.',
      notes='D-section rubber quay fender on steel back plates with a yellow-painted top angle. Intended to hang on the quay face: '
            'lower by ~1.0 m (top flush with the deck) and push ~0.2 m outward if it floats in front of the edge.')
def fender(A, v):
    prof = [(.18, 0), (.18, 1.0)] + [(.18 - .34 * math.sin(math.pi * k / 8), 1.0 - k / 8) for k in range(1, 8)]
    A.prism([(y, z) for y, z in prof], 1.0, (-.5, 0, 0), 'rubber', rot=(90, 0, 90))
    for x in (-.45, .45):
        A.box((.12, .05, 1.0), (x, .18, .5), 'steel_dark', bevel=0)
        for z in (.15, .85):
            A.cyl(.03, .04, (x, .13, z), 'steel_dark', n=6, rot=(90, 0, 0), bevel=0, detail=True)
    A.box((1.2, .06, .14), (0, .2, .97), 'yellow', bevel=.01)
    A.box((1.2, .2, .03), (0, .12, 1.0), 'yellow', bevel=0)
    A.col_box((1.2, .4, 1.0), (0, 0, .5))


@prop('CableReel', ['cable_reel'], variants=['A', 'B'], data_size=[1.6, 1.0, 1.6], variant_rule='stable hash of id % 2',
      collider_note='Box 1.6 x 1.0 x 1.6 (or a 16-gon hull).', notes='Wooden cable drum on its edge; A black cable, B orange cable with a loose end.')
def cable_reel(A, v):
    R = .8
    for y in (-.47, .47):
        A.cyl(R, .06, (0, y - .03, R), 'wood_pallet', n=18, rot=(-90, 0, 0), bevel=.012)
        for z in (-.25, .25):
            A.box((1.3, .02, .1), (0, y + (.04 if y > 0 else -.04), R + z), 'wood_dark', bevel=0, detail=True)
        A.cyl(.1, .02, (0, y + (.04 if y > 0 else -.06), R), 'charcoal', n=8, rot=(-90, 0, 0), bevel=0)
    A.cyl(.62, .88, (0, -.44, R), 'rubber' if v == 'A' else 'orange', n=18, rot=(-90, 0, 0), bevel=0)
    if v == 'B':
        A.sweep([(.3, -.2, R + .55), (.7, -.15, R), (.9, -.1, .2), (1.3, .1, .05), (1.6, .3, .05)], .025, 'orange', n=5)
    A.col_hull([(R * math.cos(k * math.tau / 16), y, R + R * math.sin(k * math.tau / 16)) for k in range(16) for y in (-.5, .5)])


@prop('OilDrum', ['oil_drum'], variants=['A', 'B', 'C'], data_size=[0.6, 0.6, 0.9], variant_rule='stable hash of id % 3',
      collider_note='Box 0.58 x 0.58 x 0.9.', notes='200 L steel drum with rolling hoops and bung caps. A blue, B red, C yellow.')
def oil_drum(A, v):
    c = {'A': 'blue', 'B': 'red', 'C': 'yellow'}[v]
    A.lathe([(0, 0), (.27, 0), (.29, .02), (.29, .27), (.3, .29), (.29, .31), (.29, .57), (.3, .59), (.29, .61), (.29, .86),
             (.285, .88), (.265, .88), (.265, .87), (0, .87)], (0, 0, 0), c, n=16)
    A.cyl(.03, .02, (.15, .05, .87), 'steel_dark', n=6, bevel=0)
    A.cyl(.02, .02, (-.15, -.08, .87), 'steel_dark', n=6, bevel=0, detail=True)
    A.col_box((.58, .58, .9), (0, 0, .45))


@prop('Pallets', ['pallets'], data_size=[3.6, 2.4, 1.2], collider_note='One box per stack.',
      notes='Six stacks of empty pallets of different heights.')
def pallets(A, v):
    heights = [6, 2, 5, 2, 5, 3]
    k = 0
    for i, x in enumerate((-1.2, 0, 1.2)):
        for j, y in enumerate((-.62, .62)):
            n = heights[k]; k += 1
            z = parts.pallet_stack(A, (x, y, 0), n, rot_z=90 + A.rng.uniform(-4, 4), dx=1.2, dy=1.0)
            A.col_box((1.0, 1.2, z), (x, y, z / 2))


@prop('PipeStackPort', ['pipe_stack (port, 9 x 2.7 x 1.2)'], data_size=[9.0, 2.7, 1.2], budget=1800,
      collider_note='Hull of the pyramid.', notes='Pyramid of 15 large steel pipes (6-5-4) on timber chocks, some rusty, some galvanised.')
def pipe_stack_port(A, v):
    cols = ['steel_galv', 'rust_light', 'steel_galv', 'steel_dark', 'rust']
    from props_site import _pipe_pyramid
    _pipe_pyramid(A, 8.8, .215, (6, 5, 4), lambda k: cols[(k * 7) % 5], (-3.6, 0, 3.6))
    A.col_hull([(sx * 4.5, sy * 1.35, 0) for sx in (-1, 1) for sy in (-1, 1)] + [(sx * 4.5, sy * .9, 1.2) for sx in (-1, 1) for sy in (-1, 1)])


@prop('WaterTowerPort', ['water_tower'], data_size=[9.2, 9.2, 18.0], budget=2500,
      collider_note='4 leg boxes, riser box, tank hull (full, solid per data).',
      notes='Old steel water tower on four braced legs: pale sage tank r 4.6 m with a catwalk and railing, conical roof, '
            'central riser pipe, ladder. Not the Hamlet Rozhnovsky tower (that is WATER-TOWER-ASTRA-001).')
def water_tower(A, v):
    leg = 'steel_dark'
    B, T, Zt = 3.6, 3.0, 12.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            A.beam((sx * B, sy * B, 0), (sx * T, sy * T, Zt), .18, leg, n=6)
            A.box((.9, .9, .4), (sx * B, sy * B, .2), 'concrete', bevel=.04)
            A.col_box((.5, .5, Zt), (sx * (B + T) / 2, sy * (B + T) / 2, Zt / 2))
    def lp(z, sx, sy):
        f = z / Zt
        return (sx * (B + (T - B) * f), sy * (B + (T - B) * f), z)
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for z0, z1 in ((.6, 4.4), (4.4, 8.4), (8.4, 12.2)):
        for i in range(4):
            (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
            A.beam(lp(z0, ax, ay), lp(z1, bx, by), .05, leg, n=4)
            A.beam(lp(z0, bx, by), lp(z1, ax, ay), .05, leg, n=4)
            A.beam(lp(z1, ax, ay), lp(z1, bx, by), .07, leg, n=6)
    A.cyl(.32, Zt, (0, 0, 0), 'steel_dark', n=10)
    A.col_box((.64, .64, Zt), (0, 0, Zt / 2))
    # tank
    A.lathe([(.4, Zt - .3), (2.8, Zt), (4.6, Zt + .5), (4.6, Zt + 4.6), (4.68, Zt + 4.7)], (0, 0, 0), 'sage', n=20, cap_bottom=True, cap_top=False)
    A.lathe([(4.68, Zt + 4.7), (4.7, Zt + 4.85), (.35, Zt + 5.6), (0, Zt + 5.65)], (0, 0, 0), 'dark_grey', n=20)
    for z in (Zt + 1.9, Zt + 3.3):
        A.cyl(4.63, .08, (0, 0, z), 'sage', n=20, bevel=0, detail=True)
    A.cyl(.12, .5, (0, 0, Zt + 5.6), 'steel_dark', n=6)
    # catwalk + railing at the tank foot
    A.tube(5.3, 4.5, .08, (0, 0, Zt + .45), 'steel_dark', n=20)
    for k in range(12):
        a = k * math.tau / 12
        A.bar((5.25 * math.cos(a), 5.25 * math.sin(a), Zt + .53), (5.25 * math.cos(a), 5.25 * math.sin(a), Zt + 1.55), .04, .04, leg, bevel=0, detail=True)
    ring = [(5.25 * math.cos(k * math.tau / 24), 5.25 * math.sin(k * math.tau / 24), Zt + 1.55) for k in range(24)]
    A.sweep(ring, .03, leg, n=4, closed=True)
    ring2 = [(p[0], p[1], Zt + 1.05) for p in ring]
    A.sweep(ring2, .02, leg, n=4, closed=True, detail=True)
    # ladder up the front-left leg to the catwalk
    for x in (-.25, .25):
        A.beam((x, -B - .5, 0), (x, -5.25, Zt + .5), .03, 'steel_galv', n=4)
    for k in range(1, 20):
        z = k * (Zt + .5) / 20
        y = -B - .5 + (-5.25 + B + .5) * k / 20
        A.bar((-.25, y, z), (.25, y, z), .035, .035, 'steel_galv', bevel=0, detail=(k % 2 == 1))
    A.col_hull([(4.7 * math.cos(k * math.tau / 16), 4.7 * math.sin(k * math.tau / 16), z) for k in range(16)
                for z in (Zt + .4, Zt + 4.8)] + [(0, 0, Zt + 5.65), (0, 0, Zt - .3)])


@prop('PipeManifold', ['pipe_manifold'], data_size=None,
      front='built to the data polyline (U-run): legs at local x = +-11 m reaching 2.48 m toward the tanks (data +y = north), run along y = -2.48',
      collider_note='None needed (low pipe, 0.65 m) or one box per straight run.',
      notes='Low yellow product pipe on H-supports from the two tanks: polyline [[1287.45,655.2],[1287.45,650.24],[1309.45,650.24],[1309.45,655.2]] '
            'around pos (1298.45, 652.72); flanges, two gate valves with red handwheels near the tanks. Data has size null -> builder made a 1 m cube.')
def pipe_manifold(A, v):
    zc = .55
    yr, yt = 2.48, -2.48          # Blender y: data y -> -Blender y
    pts = [(-11, yt, zc), (-11, yr - .4, zc), (-10.6, yr, zc), (10.6, yr, zc), (11, yr - .4, zc), (11, yt, zc)]
    A.sweep(pts, .15, 'yellow', n=10)
    def support(p, along_x):
        x, y = p
        d = (0, .3) if along_x else (.3, 0)
        for s in (-1, 1):
            A.box((.08, .08, zc), (x + s * d[0], y + s * d[1], zc / 2), 'steel_dark', bevel=0)
        A.box((.7 if not along_x else .1, .1 if not along_x else .7, .06), (x, y, zc - .18), 'steel_dark', bevel=0)
        A.box((.5, .5, .1), (x, y, .05), 'concrete', bevel=.015)
    for x in (-8, -5, -2, 1, 4, 7):
        support((x + .5, yr), True)
    for s in (-1, 1):
        support((s * 11, 0), False)
        for y in (yt + .3, 0.9):
            A.cyl(.22, .06, (s * 11, y - .03, zc), 'steel_dark', n=12, rot=(-90, 0, 0), bevel=0)
        A.box((.36, .4, .36), (s * 11, yt + 1.0, zc), 'steel_dark', bevel=.02)
        A.cyl(.04, .35, (s * 11, yt + 1.0, zc + .15), 'steel_dark', n=6)
        A.torus(.18, .025, (s * 11, yt + 1.0, zc + .52), 'red', n=12, m=4)
    for x in (-6.5, 0, 6.5):
        A.cyl(.21, .06, (x - .03, yr, zc), 'steel_dark', n=12, rot=(0, 90, 0), bevel=0, detail=True)
