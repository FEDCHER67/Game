"""Tramduro (presidential island) static props (M2). Blender frame = W85 box frame (X = size[0], Y = size[1], Z up).
Palace white / travertine, red cloth, gold accents; military dark green; no emblems, no text."""
import math
from m2reg import prop
import parts


@prop('BridgeBarrier', ['bridge_barrier'], data_size=[0.25, 6.4, 0],
      front='boom along Blender Y (= data size[1] 6.4 m across the road); post at the Blender +Y end (Unity -Z)',
      collider_note='None (data solid = false); add a trigger if the KPP logic needs one.',
      notes='Closed red / white striped boom barrier of the island KPP: post with motor box and counterweight, boom rest fork at the far end.')
def bridge_barrier(A, v):
    yp = 3.0
    A.box((.4, .4, .06), (0, yp, .03), 'concrete', bevel=.01)
    A.box((.26, .3, 1.0), (0, yp, .06 + .5), 'white_paint', bevel=.025)
    A.box((.27, .31, .14), (0, yp, .7), 'red', bevel=.01)
    A.box((.3, .36, .2), (0, yp, 1.1), 'dark_grey', bevel=.02)
    A.box((.22, .3, .22), (0, yp + .45, .98), 'charcoal', bevel=.02)
    n = 12
    L = 6.3
    for k in range(n):
        y0 = yp - .1 - k * L / n
        A.cyl(.055, L / n, (0, y0, .98), 'red' if k % 2 == 0 else 'white_paint', n=8, rot=(90, 0, 0), bevel=0)
    A.box((.06, .06, .82), (0, -3.05, .41), 'white_paint', bevel=0)
    for s in (-1, 1):
        A.box((.04, .04, .14), (s * .07, -3.05, .88), 'white_paint', bevel=0)
    A.cyl(.05, .04, (0, -3.15, .98), 'beacon_red', n=6, rot=(90, 0, 0), bevel=0, detail=True)


@prop('FictionalNuclearMissile', ['fictional_nuclear_missile'], data_size=[7.0, 7.0, 11.0], budget=1800,
      collider_note='Missile body box + collar ring as 4 boxes.',
      notes='Cartoon missile rising from an open silo: concrete collar with yellow / black hazard ring, two blast doors folded open, '
            'white body with red nose and fins, dark bands. No symbols or text.')
def missile(A, v):
    A.tube(3.4, 2.35, .8, (0, 0, 0), 'concrete', n=24)
    A.tube(2.9, 2.6, .05, (0, 0, .8), 'yellow', n=24)
    for k in range(12):
        a = (k + .5) * math.tau / 12
        A.box((.32, .3, .06), (2.75 * math.cos(a), 2.75 * math.sin(a), .82), 'charcoal', rot=(0, 0, math.degrees(a)), bevel=0, detail=True)
    A.cyl(2.36, .05, (0, 0, .1), 'charcoal', n=20, bevel=0)
    for s in (-1, 1):
        A.box((2.3, 4.6, .3), (s * 3.55, 0, .95 + .3), 'mil_green', rot=(0, s * 78, 0), bevel=.04)
        A.box((.4, 4.0, .1), (s * 3.5, 0, 1.3), 'mil_dark', rot=(0, s * 78, 0), bevel=0, detail=True)
    A.cyl(1.0, 7.4, (0, 0, .1), 'white_paint', n=20)
    A.lathe([(1.0, 7.5), (.96, 8.3), (.82, 9.1), (.55, 9.9), (.22, 10.5), (0, 10.75)], (0, 0, 0), 'red', n=20)
    for z, c in ((1.6, 'charcoal'), (4.4, 'charcoal'), (7.2, 'yellow')):
        A.cyl(1.02, .3, (0, 0, z), c, n=20, bevel=0)
    for k in range(4):
        a = k * 90 + 45
        A.prism([(.9, 0), (2.05, 0), (2.05, .7), (.9, 2.7)], .14, (0, 0, .9), 'red', rot=(90, 0, a))
    A.col_box((2.0, 2.0, 10.7), (0, 0, 5.35))
    for k in range(4):
        a = k * math.pi / 2
        A.col_box((1.1, 6.8, .85), (2.9 * math.cos(a), 2.9 * math.sin(a), .425), rot=(0, 0, math.degrees(a)))


@prop('GoldStatue', ['gold_statue'], data_size=[2.8, 2.8, 3.7], placement='facing', y_offset=1.3,
      front='figure faces Unity +Z (Blender -Y); facing convention gives east for rot 0 - suggest yaw 180 (Unity) so it faces the lawn / south',
      collider_note='Plinth box + figure box.', budget=6000,
      notes='Same golden cartoon leader as the Downtown monument, 3.3 m on a 0.4 m dark plinth. Stands ON StepPedestal (same pos): lift by 1.3 m.')
def gold_statue(A, v):
    A.box((1.7, 1.7, .4), (0, 0, .2), 'granite_dark', bevel=.04)
    parts.figure(A, 3.4, (0, 0, .4))
    A.col_box((1.7, 1.7, .4), (0, 0, .2)); A.col_box((1.3, .9, 3.3), (0, 0, .4 + 1.65))


@prop('StepPedestal', ['stepped_monument_pedestal'], data_size=[4.8, 4.8, 1.3], collider_note='Three stacked boxes (walkable steps).',
      notes='Three square travertine steps with dark granite edge bands; carries GoldStatue.')
def step_pedestal(A, v):
    for k, (w, z, h) in enumerate(((4.8, 0, .4), (4.0, .4, .4), (3.2, .8, .5))):
        A.box((w, w, h), (0, 0, z + h / 2), 'travertine', bevel=.03)
        A.box((w + .02, w + .02, .06), (0, 0, z + h - .03), 'granite_dark', bevel=0)
        A.col_box((w, w, z + h), (0, 0, (z + h) / 2))


@prop('GolfGreen', ['golf_green'], variants=['A', 'B', 'C'], data_size=[8.0, 7.0, 0], variant_rule='one per data green (green1 A, green2 B, green3 C)',
      collider_note='None (raised 8 cm; walkable). Flag pin optional thin box.', notes='Joke mini-golf putting green: oval green on a fringe, cup, flag pin, '
      'balls; B with a small sand bunker, C with a little bridge-less water edge stone ring. Red flags, no numbers.')
def golf_green(A, v):
    A.mound(4.0, 3.5, .06, (0, 0, 0), 'turf', rings=2, segs=20, noise=.04, power=.3, facet=False)
    A.mound(3.4, 2.9, .09, (0, 0, 0), 'turf_light', rings=3, segs=20, noise=.04, power=.25, facet=False)
    hx, hy = (.9, -.6) if v == 'A' else (-1.2, .5) if v == 'B' else (.4, .9)
    A.cyl(.08, .095, (hx, hy, 0), 'charcoal', n=10, bevel=0)
    A.cyl(.012, 2.1, (hx, hy, 0), 'white_paint', n=6)
    A.prism([(0, 0), (.5, -.12), (0, -.32)], .01, (hx, hy, 2.08), 'red', rot=(90, 0, 0))
    for k in range(2):
        A.sphere(.025, (hx - .6 - k * .9, hy + .4 + k * .5, .1), 'white_paint', seg=6, rings=4, detail=True)
    if v == 'B':
        A.mound(1.1, .7, .03, (2.6, -2.2, 0), 'sand', rings=2, segs=12, noise=.05, facet=False)
    if v == 'C':
        for k in range(10):
            a = k * math.tau / 10
            A.ico(.12, (-2.2 + .7 * math.cos(a), -1.6 + .5 * math.sin(a), .03), 'stone_warm', subdiv=1, detail=True)


@prop('PorticoSteps', ['portico_steps'], data_size=[10.0, 4.0, 0], front='climbs toward Blender -Y = Unity +Z (north, to the palace door at y 812.5)',
      collider_note='One box per step (walkable).', notes='White travertine stair of the palace portico: 5 steps (0.18 m) and a landing, cheek blocks with urns.')
def portico_steps(A, v):
    W = 8.6
    for k in range(5):
        y0 = 2.0 - k * .6
        A.box((W, 4.0 - k * .6 - (4.0 - 3.0) * 0, .18), (0, (y0 + (-2.0)) / 2, .09 + k * .18), 'travertine', bevel=.015)
        A.col_box((W, y0 + 2.0, .18 * (k + 1)), (0, (y0 - 2.0) / 2, .09 * (k + 1)))
    for s in (-1, 1):
        A.box((.7, 4.0, 1.1), (s * (W / 2 + .35), 0, .55), 'offwhite', bevel=.03)
        A.box((.8, 4.1, .1), (s * (W / 2 + .35), 0, 1.15), 'travertine', bevel=.02)
        A.lathe([(.18, 0), (.12, .08), (.25, .3), (.28, .45), (.2, .6), (.0, .62)], (s * (W / 2 + .35), 1.6, 1.2), 'offwhite', n=10)
        A.col_box((.7, 4.0, 1.2), (s * (W / 2 + .35), 0, .6))


@prop('PresidentialSpeechStage', ['presidential_speech_stage'], data_size=[16.0, 9.0, 0.8], budget=1800,
      front='audience / steps side = Blender +Y = Unity -Z (south)', collider_note='One box 16 x 9 x 0.8 (walkable top).',
      notes='Stage platform: pleated red skirt with gold trim, light deck, red carpet runner from the steps to the lectern, '
            'two flag stands with plain red / gold flags at the back.')
def stage(A, v):
    L, W, H = 16.0, 9.0, .8
    A.box((L - .1, W - .1, H - .06), (0, 0, (H - .06) / 2), 'red_cloth_dark', bevel=0)
    A.box((L, W, .08), (0, 0, H - .04), 'offwhite', bevel=.02)
    A.box((L + .02, W + .02, .06), (0, 0, H - .1), 'gold', bevel=0)
    step = .8
    for side in range(4):
        length = L if side < 2 else W
        n = int(length / step)
        for k in range(n):
            t = -length / 2 + (k + .5) * length / n
            if side == 0:
                p = (t, W / 2, 0)
            elif side == 1:
                p = (t, -W / 2, 0)
            elif side == 2:
                p = (L / 2, t, 0)
            else:
                p = (-L / 2, t, 0)
            sz = (length / n * .5, .06, H - .12) if side < 2 else (.06, length / n * .5, H - .12)
            A.box(sz, (p[0], p[1], (H - .12) / 2), 'red_cloth', bevel=0, detail=True)
    A.box((1.8, 6.6, .02), (0, 1.15, H + .01), 'red_cloth', bevel=0)
    for s in (-1, 1):
        x, y = s * 6.8, -3.6
        A.cyl(.25, .1, (x, y, H), 'gold_dark', n=10)
        A.cyl(.03, 3.4, (x, y, H), 'gold', n=6)
        A.box((1.3, .02, .8), (x + s * .67, y, H + 2.9), 'red_cloth', bevel=0)
        A.box((1.3, .025, .14), (x + s * .67, y, H + 2.75), 'yellow', bevel=0)
        A.sphere(.06, (x, y, H + 3.45), 'gold', seg=6, rings=4, detail=True)
    A.col_box((L, W, H), (0, 0, H / 2))


@prop('PresidentialLectern', ['presidential_lectern'], data_size=[1.4, 0.8, 1.2], y_offset=0.8,
      front='front panel to Blender +Y = Unity -Z (south, the audience); speaker stands on the Blender -Y side',
      collider_note='Box 1.1 x 0.7 x 1.2.', notes='Dark wood lectern with a red front panel and gold trim, slanted reading desk, two microphones. '
      'No emblem. Stands ON the stage (same area): lift by 0.8 m.')
def lectern(A, v):
    A.box((1.4, .8, .08), (0, 0, .04), 'granite_dark', bevel=.02)
    A.box((1.0, .6, 1.0), (0, 0, .08 + .5), 'wood_dark', taper=(1.1, 1.05), bevel=.03)
    A.box((.7, .03, .6), (0, .32, .62), 'red_cloth', bevel=0)
    for z in (.3, .95):
        A.box((1.08, .64, .04), (0, 0, z), 'gold', bevel=0)
    A.box((1.2, .55, .06), (0, -.05, 1.12), 'wood_dark', rot=(-14, 0, 0), bevel=.02)
    for s in (-1, 1):
        A.sweep([(s * .25, .12, 1.15), (s * .24, .05, 1.35), (s * .2, -.08, 1.42)], .008, 'charcoal', n=4)
        A.sphere(.025, (s * .2, -.1, 1.42), 'charcoal', seg=6, rings=4)
    A.col_box((1.1, .7, 1.2), (0, 0, .6))


@prop('SpeechPlatformSteps', ['speech_platform_steps'], data_size=[8.0, 2.0, 0],
      front='climbs toward Blender -Y = Unity +Z (north, up onto the stage); top = 0.8 m',
      collider_note='One box per step (walkable).', notes='Four steps up to the stage with the red carpet runner and brass rope posts.')
def stage_steps(A, v):
    n, rise, tread = 4, .2, .5
    for k in range(n):
        y0 = 1.0 - k * tread
        A.box((8.0, y0 + 1.0, rise), (0, (y0 - 1.0) / 2, rise / 2 + k * rise), 'offwhite', bevel=.012)
        A.box((1.8, tread, .015), (0, y0 - tread / 2, rise * (k + 1) + .007), 'red_cloth', bevel=0)
        A.col_box((8.0, y0 + 1.0, rise * (k + 1)), (0, (y0 - 1.0) / 2, rise * (k + 1) / 2))
    for s in (-1, 1):
        pts = []
        for k in range(4):
            y = .85 - k * .55
            z = rise * min(n, k + 1)
            A.cyl(.03, .9, (s * 1.3, y, z), 'gold', n=6)
            A.sphere(.045, (s * 1.3, y, z + .92), 'gold', seg=6, rings=4, detail=True)
            pts.append((s * 1.3, y, z + .85))
        A.sweep(pts, .02, 'red_cloth', n=4)
