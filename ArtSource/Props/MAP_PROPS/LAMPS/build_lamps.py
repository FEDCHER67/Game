"""MAP-LAMPS-001 - street lamps (bpy 5.0.1 / Blender 5.x, background).

  * LP_SovietConcrete        - tapered vibro-concrete pole (~9 m) with a bent steel arm and a "cobra" head
  * LP_SovietConcrete_Broken - same pole, slightly leaning, dark smashed head (sleeping district: part of the lamps is broken)
  * LP_OldTown_Single        - old-town cast-iron style lamp (~4.3 m), fluted shaft, four-sided lantern
  * LP_OldTown_Double        - the same post with a scrolled crossbar and two lanterns (squares, embankment)

Each lamp has empty children LP_*_Light (one per light) at the bulb: put the Unity Light there.
Glow faces use MP_Lamp_Glow (emissive in Blender; in Unity give it an emission colour, switch off for daytime/broken).
Run:  python3 build_lamps.py -- [--revision N] [--no-render] [--force] [--samples N]
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp
from mapprops import T, R

fam = mp.Family('MAP-LAMPS-001', __file__, prefix='LP_', tri_budget_default=900,
                description='Street lamps: Soviet concrete pole with cobra head (working and broken), old-town lantern (single and double).')

# =============================================================== Soviet concrete pole
POLE_H = 9.0


def soviet_lamp(broken=False):
    m = mp.Mesh()
    # tapered octagonal-ish pole: a lathe with 8 sides, wider at the bottom, darker concrete near the ground
    prof = [(0.17, 0.0), (0.165, 0.6), (0.15, 2.5), (0.12, 6.0), (0.095, POLE_H)]
    m.lathe(prof, 8, 'MP_Concrete', offset=math.pi / 8,
            mfn=lambda b, k: 'MP_Concrete_Stain' if b == 0 else 'MP_Concrete')
    m.lathe([(0.0, POLE_H), (0.10, POLE_H), (0.08, POLE_H + 0.06), (0.0, POLE_H + 0.08)], 8, 'MP_Concrete_Dark', offset=math.pi / 8)
    # access hatch near the base (dark metal plate), facing -Y
    m.box(0.16, 0.04, 0.32, 'MP_Metal_Dark', at=(0, -0.155, 0.75), base=True)
    # clamp + arm: steel pipe going up the pole then bending out towards -Y
    for z in (POLE_H - 1.3, POLE_H - 0.5):
        m.cyl(0.125, 0.10, 8, 'MP_Metal_Dark', at=(0, 0, z), M=None)
    arm = [(0, -0.13, POLE_H - 1.35), (0, -0.14, POLE_H - 0.4), (0, -0.25, POLE_H + 0.15), (0, -0.6, POLE_H + 0.45),
           (0, -1.2, POLE_H + 0.6), (0, -1.75, POLE_H + 0.62)]
    m.tube_path(arm, [0.045] * len(arm), 6, 'MP_Metal_Grey')
    # cobra head: tapered elongated body tilted slightly up, glow lens underneath
    head = mp.Mesh()
    L = 0.75
    sec = [(-0.0, 0.10, 0.07), (0.25, 0.17, 0.11), (0.55, 0.16, 0.10), (L, 0.09, 0.06)]   # (y, half width, half height)
    rings = []
    v, f = [], []
    for y, hw, hh in sec:
        idx = len(v)
        v += [(-hw, -y, -hh * 0.6), (hw, -y, -hh * 0.6), (hw * 0.8, -y, hh), (-hw * 0.8, -y, hh)]
        rings.append(idx)
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            k1 = (k + 1) % 4
            f.append((a + k, b + k, b + k1, a + k1))
    f.append(tuple(rings[0] + k for k in range(4)))
    f.append(tuple(rings[-1] + k for k in (3, 2, 1, 0)))
    head._shell(v, f, 'MP_Metal_Grey')
    glow = 'MP_Glass' if broken else 'MP_Lamp_Glow'
    lens_v = [(-0.13, -0.12, -0.075), (0.13, -0.12, -0.075), (0.12, -0.62, -0.06), (-0.12, -0.62, -0.06)]
    lv = lens_v + [(x * 0.85, y, z - 0.05) for x, y, z in lens_v]
    head._shell(lv, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], glow)
    if broken:
        head.box(0.10, 0.18, 0.02, 'MP_Metal_Dark', at=(0.03, -0.35, -0.13))                      # hole / missing lens
    tilt = R(-8, 'X')
    m.merge(head, T(0, -1.70, POLE_H + 0.60) @ tilt)
    light = (0, -2.05, POLE_H + 0.50)
    if broken:
        m.box(0.30, 0.02, 0.6, 'MP_Paint_Rust', at=(0, -0.13, 1.6), base=True)                     # rust streak / old notice
    return m, light


for broken in (False, True):
    name = 'LP_SovietConcrete' + ('_Broken' if broken else '')
    m, light = soviet_lamp(broken)
    lean = R(2.5, 'X') if broken else None
    if lean is not None:
        m.verts = [tuple(lean @ mp.Vector(p)) for p in m.verts]
        m.verts = [(x, y, max(z, 0.0)) for x, y, z in m.verts]          # base ring cut flat at the ground
        light = tuple(lean @ mp.Vector(light))
    root = fam.make_object(name, m)
    objs = [root]
    if not broken:
        objs.append(fam.add_socket(name + '_Light', root, light))
    fam.add_asset(name, objs, budget=600, row=0, height_m=POLE_H,
                  notes='Arm and head point to -Y (the road side). ' + ('Leans 2.5 deg, smashed dark head, no light socket.' if broken else ''))

# =============================================================== old-town lamp
OT_H = 3.2            # top of the shaft capital


def oldtown_post(m):
    prof = [(0.26, 0.0), (0.26, 0.12), (0.20, 0.14), (0.20, 0.30), (0.15, 0.36), (0.13, 0.62), (0.085, 0.70),
            (0.085, 0.80), (0.065, 0.86), (0.055, OT_H - 0.30), (0.075, OT_H - 0.26), (0.075, OT_H - 0.20),
            (0.06, OT_H - 0.16), (0.10, OT_H - 0.04), (0.10, OT_H), (0.0, OT_H + 0.02)]
    gold_bands = {9, 10}
    m.lathe(prof, 8, 'MP_Metal_Black', offset=math.pi / 8,
            mfn=lambda b, k: 'MP_Gold' if b in gold_bands else 'MP_Metal_Black')


def lantern(m, x, y, z, s=1.0):
    """Four-sided lantern standing at (x, y, z): base cup, tapered glow box, frame posts, pyramid roof with finial."""
    m.lathe([(0.0, 0.0), (0.05 * s, 0.0), (0.12 * s, 0.10 * s), (0.12 * s, 0.13 * s), (0.0, 0.13 * s)], 4, 'MP_Metal_Black',
            M=T(x, y, z), offset=math.pi / 4)
    z0, z1 = z + 0.13 * s, z + 0.58 * s
    m.lathe([(0.12 * s, z0 - z), (0.17 * s, z1 - z), (0.0, z1 - z)], 4, 'MP_Lamp_Glow', M=T(x, y, z), offset=math.pi / 4)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p0 = (x + 0.125 * s * math.cos(a), y + 0.125 * s * math.sin(a), z0)
        p1 = (x + 0.175 * s * math.cos(a), y + 0.175 * s * math.sin(a), z1)
        m.cyl_between(p0, p1, 0.018 * s, 4, 'MP_Metal_Black')
    m.lathe([(0.0, 0.0), (0.24 * s, 0.0), (0.24 * s, 0.03 * s), (0.10 * s, 0.17 * s), (0.04 * s, 0.20 * s), (0.04 * s, 0.25 * s),
             (0.0, 0.31 * s)], 4, 'MP_Metal_Black', M=T(x, y, z1), offset=math.pi / 4,
            mfn=lambda b, k: 'MP_Gold' if b >= 4 else 'MP_Metal_Black')
    return (x, y, (z0 + z1) / 2)


m = mp.Mesh()
oldtown_post(m)
light = lantern(m, 0, 0, OT_H)
root = fam.make_object('LP_OldTown_Single', m)
fam.add_asset('LP_OldTown_Single', [root, fam.add_socket('LP_OldTown_Single_Light', root, light)], budget=900, row=1,
              height_m=OT_H + 0.89, notes='Lantern glow panels are MP_Lamp_Glow.')

m = mp.Mesh()
oldtown_post(m)
lights = []
for s in (-1, 1):
    arm = [(0, 0, OT_H - 0.28)] + [(s * 0.62 * t, 0, OT_H - 0.28 + 0.18 * math.sin(t * math.pi) + 0.22 * t) for t in (0.25, 0.5, 0.75, 1.0)]
    m.tube_path(arm, [0.035, 0.032, 0.03, 0.028, 0.028], 5, 'MP_Metal_Black')
    scroll = [(s * (0.12 + 0.30 * t), 0, OT_H - 0.30 - 0.28 * math.sin(t * math.pi) * (1 - 0.4 * t)) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    m.tube_path(scroll, [0.02] * 5, 4, 'MP_Metal_Black')
    m.blob(0.045, 'MP_Gold', M=T(s * 0.42, 0, OT_H - 0.42), subdiv=1, jitter=0.0)
    lights.append(lantern(m, s * 0.62, 0, OT_H - 0.06 + 0.22, s=0.9))
m.lathe([(0.0, 0.0), (0.05, 0.0), (0.04, 0.25), (0.0, 0.35)], 6, 'MP_Gold', M=T(0, 0, OT_H))                    # centre finial
root = fam.make_object('LP_OldTown_Double', m)
objs = [root] + [fam.add_socket(f'LP_OldTown_Double_Light{i + 1}', root, p) for i, p in enumerate(lights)]
fam.add_asset('LP_OldTown_Double', objs, budget=1300, row=1, height_m=OT_H + 0.7, notes='Crossbar along X, lanterns at x = +-0.62 m.')

fam.finish(lineup_gap=2.0, row_gap=3.0, camera=[('01_front.png', 270, 6, (1400, 1100), 50),
                                                ('02_three_quarter.png', 235, 16, (1400, 1100), 50)])
