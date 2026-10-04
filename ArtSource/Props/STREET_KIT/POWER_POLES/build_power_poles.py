"""STREET_KIT / POWER_POLES - 10 kV concrete pole (straight and with a strut) and a 0.4 kV wooden pole on a concrete stub.

Each pole has SOCKET_Wire_* empties at the insulator heads: wires attach there. The line runs along the Y axis,
crossarms run along X. Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/POWER_POLES/build_power_poles.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/POWER_POLES/build_power_poles.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-POWER_POLES', __file__)


def pin_insulator(m, x, y, z, glass=True):
    """Steel pin + bell insulator standing at (x, y, z); returns the wire socket point (groove at the head)."""
    m.bar((x, y, z), (x, y, z + 0.14), 0.02, 'metal_dark', seg=6)
    # slightly oversized (cartoon) so the insulators read from the street
    m.lathe([(0.0, z + 0.09), (0.11, z + 0.12), (0.085, z + 0.20), (0.06, z + 0.25), (0.07, z + 0.29), (0.0, z + 0.32)], 8,
            'glass' if glass else 'white')
    return (x, y, z + 0.27)


def concrete_pole(m, H=9.4):
    """SV-type vibrated concrete pole: tapered rectangle with a darker ground stain."""
    m.prism_xy([(-0.14, -0.10), (0.14, -0.10), (0.14, 0.10), (-0.14, 0.10)], 0.0, 0.6, 'concrete_dark')
    # taper by building the shaft as a frustum loft (lathe with 4 sides, non-uniform scale)
    m.lathe([(0.17, 0.6), (0.11, H), (0.0, H + 0.02)], 4, 'concrete', M=sk.S(1.0, 0.7, 1.0), offset=math.pi / 4)
    m.box(0.16, 0.02, 0.22, 'yellow', at=(0, -0.085, 2.6))           # pole number plate
    m.box(0.10, 0.02, 0.05, 'black', at=(0, -0.096, 2.62))
    m.prism([(-0.10, 3.2), (0.10, 3.2), (0.0, 3.37)], 0.02, 'yellow', M=T(0, -0.085, 0))    # danger triangle
    m.beam((-0.015, -0.097, 3.22), (0.015, -0.097, 3.33), 0.02, 0.022, 'black', up=(0, 1, 0))      # lightning stroke
    return H


def pole_10kv(strut):
    m = Mesh()
    H = concrete_pole(m)
    za = H - 0.55
    m.beam((-0.95, -0.12, za), (0.95, -0.12, za), 0.07, 0.07, 'metal_dark', up=(0, 0, 1))           # crossarm (angle iron)
    m.beam((-0.70, -0.12, za), (-0.06, -0.12, za - 0.55), 0.04, 0.04, 'metal_dark', up=(0, 1, 0))   # braces
    m.beam((0.70, -0.12, za), (0.06, -0.12, za - 0.55), 0.04, 0.04, 'metal_dark', up=(0, 1, 0))
    m.box(0.36, 0.05, 0.16, 'metal_dark', at=(0, -0.105, za))                                          # clamp plate
    sockets = [('SOCKET_Wire_A', pin_insulator(m, -0.85, -0.12, za + 0.035)),
               ('SOCKET_Wire_B', pin_insulator(m, 0.85, -0.12, za + 0.035))]
    m.box(0.06, 0.06, 0.30, 'metal_dark', at=(0, 0, H + 0.12))                                         # top pin bracket
    sockets.append(('SOCKET_Wire_C', pin_insulator(m, 0, 0, H + 0.26)))
    if strut:
        # angle pole: a second concrete pole leans against it as a strut (подкос), along +Y
        top = (0, 0.10, 6.4)
        foot = (0, 2.25, 0.10)
        m.beam(foot, top, 0.20, 0.16, 'concrete', up=(0, 0, 1))
        m.box(0.30, 0.10, 0.30, 'metal_dark', at=(0, 0.14, 6.35))
        m.bevel_box(0.5, 0.5, 0.06, 0.02, 'concrete_dark', at=(0, 2.2, 0), base=True)
    return m, sockets


def pole_04kv():
    m = Mesh()
    # concrete stub (пасынок) with the wooden pole banded to its side
    m.prism_xy([(-0.12, 0.10), (0.12, 0.10), (0.10, 0.32), (-0.10, 0.32)], 0.0, 2.2, 'concrete')
    m.lathe([(0.13, 0.0), (0.12, 1.2), (0.10, 8.6), (0.0, 8.72)], 8, 'wood_dark')
    m.lathe([(0.13, 0.0), (0.135, 0.5), (0.0, 0.5)], 8, 'black')                     # tarred butt
    for z in (0.8, 1.9):
        m.box(0.30, 0.46, 0.05, 'metal_dark', at=(0, 0.10, z))                         # steel bands
    # four hook insulators, two each side, stacked (0.4 kV street line)
    sockets = []
    for k, (s, z) in enumerate(((-1, 8.25), (1, 8.25), (-1, 7.75), (1, 7.75))):
        x = s * 0.10
        m.bar((x, 0, z), (s * 0.30, 0, z), 0.012, 'metal_dark', seg=6)                    # hook going out
        m.bar((s * 0.30, 0, z), (s * 0.30, 0, z + 0.06), 0.012, 'metal_dark', seg=6)
        sockets.append((f'SOCKET_Wire_{k + 1}', pin_insulator(m, s * 0.30, 0, z + 0.02, glass=False)))
    # house service drop bracket and a rusty junction box
    m.bar((0, 0, 7.3), (0, -0.40, 7.3), 0.015, 'metal_dark', seg=6)
    sockets.append(('SOCKET_Wire_Drop', pin_insulator(m, 0, -0.40, 7.3, glass=False)))
    m.bevel_box(0.22, 0.12, 0.30, 0.02, 'rust', at=(0, -0.18, 2.9))
    return m, sockets


for name, fn, notes in (
        ('SK_PowerPole_Concrete_10kV', lambda: pole_10kv(False), '10 kV line pole ~9.6 m: tapered concrete shaft, crossarm with braces, 3 pin insulators. Wires: SOCKET_Wire_A/B/C, line along Y.'),
        ('SK_PowerPole_Concrete_10kV_Strut', lambda: pole_10kv(True), 'Same pole with a concrete strut leaning from +Y (corner / end pole).'),
        ('SK_PowerPole_Wood_04kV', pole_04kv, '0.4 kV street pole ~8.7 m: wooden pole banded to a concrete stub, 4 hook insulators + service drop. Wires: SOCKET_Wire_1..4, SOCKET_Wire_Drop.')):
    if fam.wants(name):
        m, socks = fn()
        fam.asset(name, [(name + '_Mesh', m, None, None)], sockets=socks, notes=notes)

fam.finish()
