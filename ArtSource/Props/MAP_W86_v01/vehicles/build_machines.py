"""MAP_W86_v01 vehicles - MACHINES family: concrete mixer, dump truck, wheel loader, van on jacks (Construction), reach stacker,
forklift, semi truck with a 40 ft container (Port), food truck (Downtown square), base-1 railway wagon (Forest).
Original procedural models (no third-party assets). Atlas MW86_Machines_<A|B|C>.png ('#hazard', '#wagon_boards').

blender -b --factory-startup -P build_machines.py -- --out-root <ArtSource/Props/MAP_W86_v01/vehicles> --fbx-dir <Unity Vehicles dir>
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / '_lib'))
import mw86lib as L  # noqa: E402
from mw86lib import Mesh, T, R  # noqa: E402

HAZ = '#hazard'
BOARDS = '#wagon_boards'


def rect(a0, a1, b0, b1):
    return [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]


def cab_over(m, y0, y1, w, z0, z1, col, bev=0.08, grille='ink', mirrors=True, visor=True):
    """European cab-over cab: front face at y0 (nose -Y), windscreen, side windows, grille, lights, bumper, mirrors."""
    h = z1 - z0
    m.bb(w, y1 - y0, h, bev, col, at=(0, (y0 + y1) / 2, z0), base=True)
    m.yplate(-1, y0, rect(-w / 2 + 0.12, w / 2 - 0.12, z0 + h * 0.52, z1 - 0.16), 'glass_dark', t=0.015)
    m.yplate(-1, y0, rect(-w / 2 + 0.32, w / 2 - 0.32, z0 + h * 0.12, z0 + h * 0.36), grille, t=0.02)
    for s in (1, -1):
        m.xplate(s, w / 2, rect(y0 + 0.14, y0 + min(1.05, (y1 - y0) * 0.55), z0 + h * 0.52, z1 - 0.18), 'glass_dark', t=0.015)
        m.yplate(-1, y0, rect(s * (w / 2 - 0.1), s * (w / 2 - 0.38), z0 + h * 0.14, z0 + h * 0.26), 'lamp_glow', t=0.025)
        if m.lod == 0:
            yd = y0 + min(1.15, (y1 - y0) * 0.6)
            m.xplate(s, w / 2, rect(yd, yd + 0.04, z0 + 0.1, z1 - 0.12), 'ink_light', t=0.012)          # door seam
            m.bb(0.3, 0.32, 0.06, 0.01, 'ink', at=(s * (w / 2 - 0.2), y0 + 0.5, z0 - 0.42), base=True)  # step
            if mirrors:
                m.beam((s * (w / 2 - 0.02), y0 + 0.12, z1 - 0.35), (s * (w / 2 + 0.12), y0 - 0.02, z1 - 0.3), 0.05, 0.05, 'ink')
                m.bb(0.1, 0.12, 0.5, 0.02, 'ink', at=(s * (w / 2 + 0.16), y0 - 0.04, z1 - 0.75), base=True)
    m.bb(w + 0.04, 0.26, 0.34, 0.04, 'ink_light', at=(0, y0 - 0.06, z0 - 0.3), base=True)
    if visor and m.lod == 0:
        m.bb(w - 0.1, 0.32, 0.06, 0.02, col, at=(0, y0 - 0.1, z1 - 0.12), base=True)


def wheels(m, xs, ys, r, w, rim='grey', seg=12):
    for x in xs:
        for y in ys:
            m.wheel(x, y, r, w, 'tyre', rim, seg=seg)


def well(m, s, x, y, hz, r, col='ink_dark'):
    """Dark half-disc wheel well on a body side (x = s*x)."""
    pts = [(y + r * math.cos(math.radians(a)), hz + r * math.sin(math.radians(a))) for a in range(0, 181, 30 if m.lod == 0 else 45)]
    m.xplate(s, x, pts, col, t=0.012)


# ---------------------------------------------------------------------------------------------- CONCRETE MIXER
def mixer(lod):
    m = Mesh(lod)
    r = 0.52
    for s in (1, -1):
        m.box(0.16, 8.6, 0.28, 'ink', at=(s * 0.48, -0.05, 0.72), base=True)
    cab_over(m, -4.45, -2.3, 2.45, 1.05, 3.15, 'mixer_cab')
    wheels(m, (-1.0, 1.0), (-3.2,), r, 0.38)
    wheels(m, (-0.92, 0.92), (1.7, 3.05), r, 0.58)
    for s in (1, -1):
        m.bb(0.62, 2.5, 0.06, 0.02, 'ink_light', at=(s * 0.92, 2.38, 1.12), base=True)        # rear mudguards
        m.cyl_y(0.26, 1.0, m.seg(8, 6), 'chrome', at=(s * 0.9, -1.0, 0.72))                    # fuel / air tanks
    # water tank behind the cab, drum pedestal and rear roller frame
    m.cyl_x(0.36, 1.1, m.seg(10, 6), 'mixer_cab', at=(0, -1.95, 1.62))
    m.bb(1.4, 0.4, 1.0, 0.04, 'ink_light', at=(0, -1.55, 1.0), base=True)
    for s in (1, -1):
        m.beam((s * 0.55, 3.25, 1.0), (s * 0.75, 3.25, 2.55), 0.18, 0.18, 'ink_light', up=(0, 1, 0))
    # drum: pear-shaped lathe on a tilted axis with paint bands
    p0 = (0.0, -1.75, 2.18)
    p1 = (0.0, 3.55, 2.95)
    dy, dz = p1[1] - p0[1], p1[2] - p0[2]
    Ld = math.hypot(dy, dz)
    ang = math.degrees(math.atan2(dz, dy))
    M = T(*p0) @ R(-(90 - ang), 'X')
    prof = [(0.35, 0.0), (0.95, 0.45), (1.12, 1.25), (1.12, 2.0), (1.08, 2.7), (0.95, 3.5), (0.72, 4.35), (0.5, 4.95), (0.4, Ld)]
    cols = ['mixer_drum', 'mixer_drum', 'mixer_band', 'mixer_drum', 'mixer_band', 'mixer_drum', 'mixer_band', 'mixer_drum']
    m.lathe(prof, m.seg(16, 10), 'mixer_drum', M=M, cols=cols)
    m.cyl(0.3, 0.12, m.seg(10, 6), 'ink', M=M @ T(0, 0, Ld))                               # drum mouth
    # hopper + chute + ladder at the rear
    m.frustum([(-0.25, 3.85), (0.25, 3.85), (0.25, 4.25), (-0.25, 4.25)], 2.75,
              [(-0.5, 3.7), (0.5, 3.7), (0.5, 4.45), (-0.5, 4.45)], 3.35, 'ink_light', bev=0.02)
    m.beam((0, 4.15, 2.55), (0, 4.75, 1.85), 0.42, 0.1, 'ink_light', up=(0, 0.7, 0.7))
    if lod == 0:
        for s in (1, -1):
            m.bar((s * 0.32, 4.45, 1.0), (s * 0.32, 4.3, 3.1), 0.035, 'ink', seg=6)
        for z in (1.4, 1.8, 2.2, 2.6):
            m.bar((-0.32, 4.4 - (z - 1.0) * 0.07, z), (0.32, 4.4 - (z - 1.0) * 0.07, z), 0.025, 'ink', seg=4)
        for s in (1, -1):
            m.yplate(1, 4.4, rect(s * 0.85, s * 1.15, 1.05, 1.2), 'lamp_red', t=0.03)
    return m


# ---------------------------------------------------------------------------------------------- DUMP TRUCK
def dump_truck(lod):
    m = Mesh(lod)
    r = 0.53
    for s in (1, -1):
        m.box(0.16, 7.7, 0.28, 'ink', at=(s * 0.48, -0.05, 0.72), base=True)
    cab_over(m, -4.1, -2.0, 2.5, 1.05, 3.1, 'dump_cab')
    wheels(m, (-1.02, 1.02), (-2.95,), r, 0.4)
    wheels(m, (-0.94, 0.94), (1.45, 2.85), r, 0.6)
    for s in (1, -1):
        m.cyl_y(0.25, 0.9, m.seg(8, 6), 'chrome', at=(s * 0.9, -0.9, 0.72))
        m.bb(0.66, 2.4, 0.06, 0.02, 'ink_light', at=(s * 0.94, 2.15, 1.12), base=True)
    # tub: floor, flared sides, front wall with cab visor, tailgate (real hollow), ribs
    y0, y1, zf = -1.75, 3.95, 1.22
    m.bb(2.45, y1 - y0, 0.16, 0.03, 'dump_tub', at=(0, (y0 + y1) / 2, zf), base=True)
    for s in (1, -1):
        m.hexa([(s * 1.18, y0, zf + 0.1), (s * 1.3, y0, zf + 0.1), (s * 1.3, y1, zf + 0.1), (s * 1.18, y1, zf + 0.1)][::s],
               [(s * 1.24, y0, zf + 1.3), (s * 1.36, y0, zf + 1.3), (s * 1.36, y1, zf + 1.3), (s * 1.24, y1, zf + 1.3)][::s],
               'dump_tub', bev=0.02)
        if lod == 0:
            for y in (-0.6, 0.9, 2.4):
                m.beam((s * 1.33, y, zf + 0.12), (s * 1.39, y, zf + 1.26), 0.12, 0.1, 'dump_tub', up=(s, 0, 0))
    m.bb(2.7, 0.14, 1.7, 0.03, 'dump_tub', at=(0, y0 + 0.07, zf + 0.1), base=True)
    m.bb(2.6, 0.75, 0.08, 0.02, 'dump_tub', at=(0, y0 - 0.35, zf + 1.72), base=True)       # visor over the cab
    m.bb(2.62, 0.14, 1.25, 0.03, 'dump_tub', at=(0, y1 - 0.07, zf + 0.1), base=True)
    # load of sand heaped in the tub
    m.frustum([(-1.12, y0 + 0.2), (1.12, y0 + 0.2), (1.12, y1 - 0.25), (-1.12, y1 - 0.25)], zf + 0.16,
              [(-0.45, y0 + 1.6), (0.45, y0 + 1.6), (0.35, y1 - 1.5), (-0.35, y1 - 1.5)], zf + 1.58, 'sand', bev=0.0)
    if lod == 0:
        m.bar((0, -1.6, 1.0), (0, -1.75, 1.55), 0.12, 'chrome', seg=8)                     # tipping ram
        for s in (1, -1):
            m.yplate(1, y1, rect(s * 0.85, s * 1.15, 1.0, 1.15), 'lamp_red', t=0.03)
    return m


# ---------------------------------------------------------------------------------------------- WHEEL LOADER
def wheel_loader(lod):
    m = Mesh(lod)
    r = 0.6
    # rear frame / engine hood and counterweight
    m.side([(0.15, 0.65), (2.15, 0.65), (2.15, 1.75), (1.95, 1.9), (0.15, 1.9)], -0.82, 0.82, 'loader_paint', bev=0.06)
    m.bb(1.85, 0.32, 1.0, 0.06, 'loader_paint', at=(0, 2.05, 0.55), base=True)
    m.yplate(1, 2.21, rect(-0.75, 0.75, 0.62, 1.45), HAZ, t=0.015)
    if lod == 0:
        for z in (1.25, 1.4, 1.55, 1.7):
            m.xplate(1, 0.82, rect(0.9, 1.8, z, z + 0.06), 'ink', t=0.012)
            m.xplate(-1, 0.82, rect(0.9, 1.8, z, z + 0.06), 'ink', t=0.012)
        m.bar((0.55, 1.4, 1.9), (0.55, 1.4, 2.45), 0.06, 'ink', seg=6)                      # exhaust
        for s in (1, -1):
            m.yplate(1, 2.21, rect(s * 0.78, s * 0.9, 1.5, 1.65), 'lamp_red', t=0.03)
    # cab with glass on all sides, ROPS roof
    m.bb(1.3, 1.2, 0.35, 0.04, 'loader_paint', at=(0, 0.35, 1.45), base=True)
    m.bb(1.3, 1.2, 1.25, 0.05, 'ink_light', at=(0, 0.35, 1.8), base=True)
    for s in (1, -1):
        m.xplate(s, 0.65, rect(-0.15, 0.85, 1.9, 2.95), 'glass_dark', t=0.012)
    m.yplate(-1, -0.25, rect(-0.55, 0.55, 1.85, 2.95), 'glass_dark', t=0.012)
    m.yplate(1, 0.95, rect(-0.55, 0.55, 2.0, 2.95), 'glass_dark', t=0.012)
    m.bb(1.42, 1.34, 0.12, 0.04, 'loader_paint', at=(0, 0.35, 3.05), base=True)
    # front frame, lift arms, bucket on the ground
    m.bb(0.85, 1.1, 0.6, 0.04, 'loader_paint', at=(0, -0.65, 0.6), base=True)
    for s in (1, -1):
        m.beam((s * 0.5, -0.15, 1.6), (s * 0.55, -1.62, 0.58), 0.16, 0.28, 'loader_paint', up=(0, -0.6, 0.8))
    m.beam((0, -0.3, 1.4), (0, -1.55, 0.95), 0.18, 0.18, 'loader_paint', up=(0, -0.3, 1))    # tilt link
    bucket = [(-2.2, 0.0), (-1.55, 0.0), (-1.42, 0.12), (-1.42, 0.9), (-1.62, 0.98), (-1.68, 0.9), (-1.56, 0.84),
              (-1.56, 0.16), (-2.12, 0.1)]
    m.side(bucket, -1.12, 1.12, 'ink_light')
    for s in (1, -1):
        m.side([(-2.2, 0.0), (-1.42, 0.0), (-1.42, 0.98), (-1.6, 0.98)], s * 1.08, s * 1.14, 'ink_light')
    if lod == 0:
        for k in range(5):
            x = -0.88 + 0.44 * k
            m.bb(0.12, 0.22, 0.06, 0.01, 'grey', at=(x, -2.25, 0.0), base=True)
    wheels(m, (-0.88, 0.88), (-1.0, 1.3), r, 0.46, rim='loader_paint')
    if lod == 0:
        for s in (1, -1):
            m.bb(0.06, 0.14, 0.2, 0.02, 'ink', at=(s * 0.72, -0.2, 2.75), base=True)          # mirrors
            m.bb(0.5, 0.25, 0.05, 0.01, 'ink', at=(s * 0.5, 0.1, 0.62), base=True)            # step
    return m


# ---------------------------------------------------------------------------------------------- VAN ON JACKS
def van_on_jacks(lod):
    m = Mesh(lod)
    w = 2.0
    # high-roof panel van body (wheels removed), hood propped open
    body = [(-2.0, 0.55), (2.95, 0.55), (2.95, 2.5), (2.85, 2.6), (-1.25, 2.6), (-2.0, 1.48)]
    m.side(body, -w / 2, w / 2, 'van_paint', bev=0.08)
    m.side([(-2.95, 0.55), (-2.0, 0.55), (-2.0, 1.2), (-2.9, 1.12)], -w / 2 + 0.04, w / 2 - 0.04, 'van_paint', bev=0.05)
    m.bb(1.7, 0.85, 0.04, 0.0, 'ink_dark', at=(0, -2.45, 1.16), base=True)                    # engine bay (dark)
    hood = m.lod == 0
    Mh = T(0, -2.0, 1.48) @ R(-52, 'X')
    m.bb(1.86, 0.98, 0.05, 0.02, 'van_paint', M=Mh, at=(0, -0.49, 0.0))                       # open hood
    if hood:
        m.bar((0.7, -2.6, 1.18), (0.7, -2.5, 2.05), 0.015, 'ink', seg=4)                       # hood stay
        m.bb(0.9, 0.5, 0.25, 0.03, 'ink_light', at=(0, -2.5, 1.2), base=True)                  # engine block top
    # glass
    m.plate([(-0.88, -1.97, 1.52), (0.88, -1.97, 1.52), (0.85, -1.3, 2.5), (-0.85, -1.3, 2.5)], (0, -1, 0.7), 0.015, 'glass_dark')
    for s in (1, -1):
        m.xplate(s, w / 2, [(-1.85, 1.55), (-0.95, 1.55), (-0.95, 2.3), (-1.3, 2.3)], 'glass_dark', t=0.015)
    m.yplate(1, 2.95, rect(-0.85, -0.05, 1.7, 2.35), 'glass_dark', t=0.015)
    m.yplate(1, 2.95, rect(0.05, 0.85, 1.7, 2.35), 'glass_dark', t=0.015)
    m.yplate(-1, -2.95, rect(-0.7, 0.7, 0.75, 1.02), 'ink', t=0.015)                           # grille
    for s in (1, -1):
        m.yplate(-1, -2.95, rect(s * 0.72, s * 0.92, 0.82, 1.02), 'lamp_glow', t=0.02)
        m.yplate(1, 2.95, rect(s * 0.86, s * 0.97, 1.0, 1.5), 'lamp_red', t=0.02)
    m.bb(2.0, 0.22, 0.25, 0.03, 'ink_light', at=(0, -3.0, 0.5), base=True)
    m.bb(2.0, 0.2, 0.22, 0.03, 'ink_light', at=(0, 3.0, 0.5), base=True)
    # sliding door seam (kerb side, -X), rear door split
    if lod == 0:
        m.xplate(-1, w / 2, rect(-0.85, -0.81, 0.62, 2.45), 'ink_light', t=0.012)
        m.xplate(-1, w / 2, rect(0.75, 0.79, 0.62, 2.45), 'ink_light', t=0.012)
        m.xplate(-1, w / 2, rect(-0.1, 0.75, 2.38, 2.42), 'ink_light', t=0.02)                 # door rail
        m.yplate(1, 2.95, rect(-0.02, 0.02, 0.6, 2.5), 'ink_light', t=0.012)
    # empty wheel wells + hubs, four jack stands
    for s in (1, -1):
        for y in (-1.7, 1.9):
            well(m, s, w / 2, y, 0.55, 0.42)
            m.cyl_x(0.16, 0.1, m.seg(8, 6), 'ink_light', at=(s * 0.82, y, 0.42))
            m.frustum([(s * 0.55 - 0.18, y - 0.18), (s * 0.55 + 0.18, y - 0.18), (s * 0.55 + 0.18, y + 0.18), (s * 0.55 - 0.18, y + 0.18)], 0.0,
                      [(s * 0.55 - 0.06, y - 0.06), (s * 0.55 + 0.06, y - 0.06), (s * 0.55 + 0.06, y + 0.06), (s * 0.55 - 0.06, y + 0.06)], 0.56,
                      'red', bev=0.0)
    # removed wheels stacked behind the van
    if lod == 0:
        for k in range(2):
            m.cyl(0.34, 0.22, 12, 'tyre', at=(0.45, 3.32, 0.22 * k))
            m.cyl(0.18, 0.225, 6, 'grey', at=(0.45, 3.32, 0.22 * k))
    return m


# ---------------------------------------------------------------------------------------------- REACH STACKER
def reach_stacker(lod):
    m = Mesh(lod)
    # chassis + engine hood + rounded counterweight with hazard plate
    m.side([(-2.6, 0.55), (2.7, 0.55), (2.7, 1.55), (-2.4, 1.55), (-2.6, 1.2)], -0.72, 0.72, 'stacker_paint', bev=0.08)
    m.box(3.3, 0.5, 0.42, 'ink_light', at=(0, -1.75, 0.6), base=True)                         # front axle housing
    m.bb(2.7, 1.2, 0.08, 0.02, 'stacker_paint', at=(0, -1.75, 1.66), base=True)               # front fender deck
    m.bb(1.9, 2.1, 0.75, 0.08, 'stacker_paint', at=(0, 1.6, 1.5), base=True)
    m.side([(2.65, 0.5), (3.55, 0.5), (3.75, 0.9), (3.75, 2.15), (3.5, 2.45), (2.65, 2.45)], -1.35, 1.35, 'stacker_paint', bev=0.08)
    m.yplate(1, 3.75, rect(-1.1, 1.1, 0.95, 1.7), HAZ, t=0.015)
    for s in (1, -1):
        m.yplate(1, 3.75, rect(s * 0.9, s * 1.2, 1.9, 2.1), 'lamp_red', t=0.03)
    # wheels: dual fronts under the boom, singles at the rear
    wheels(m, (-1.0, 1.0), (-1.75,), 0.82, 0.5, rim='stacker_paint', seg=14)
    wheels(m, (-1.56, 1.56), (-1.75,), 0.82, 0.5, rim='stacker_paint', seg=14)
    wheels(m, (-1.12, 1.12), (1.9,), 0.72, 0.5, rim='stacker_paint', seg=12)
    # cab (offset to the left / +X), glass all round
    cx, cy = 0.78, -0.25
    m.bb(1.3, 1.4, 0.22, 0.04, 'stacker_paint', at=(cx, cy, 1.62), base=True)
    m.bb(1.3, 1.4, 1.5, 0.05, 'ink_light', at=(cx, cy, 1.84), base=True)
    m.xplate(1, cx + 0.65, rect(cy - 0.6, cy + 0.6, 2.0, 3.25), 'glass_dark', t=0.012)
    m.xplate(-1, -(cx - 0.65), rect(cy - 0.6, cy + 0.6, 2.0, 3.25), 'glass_dark', t=0.012)
    m.yplate(-1, cy - 0.7, rect(cx - 0.55, cx + 0.55, 1.95, 3.28), 'glass_dark', t=0.012)
    m.bb(1.5, 1.65, 0.1, 0.03, 'stacker_paint', at=(cx, cy - 0.05, 3.34), base=True)
    # telescopic boom: rear pivot (top of the counterweight frame) -> over the cab -> tip in front of the wheels
    bx = -0.42
    p0, p1 = (bx, 2.45, 2.35), (bx, -2.85, 4.25)

    def at(t):
        return (bx, p0[1] + (p1[1] - p0[1]) * t, p0[2] + (p1[2] - p0[2]) * t)
    m.beam(at(-0.04), at(0.64), 0.62, 0.72, 'stacker_paint')
    m.beam(at(0.58), at(1.0), 0.5, 0.56, 'stacker_paint')
    for sx in (1, -1):
        m.bb(0.16, 0.8, 1.1, 0.03, 'ink_light', at=(bx + sx * 0.4, 2.45, 1.45), base=True)    # pivot cheeks
    m.bar((bx, -1.0, 1.55), at(0.42), 0.15, 'chrome', seg=m.seg(8, 6))                      # lift cylinder rod
    m.bar((bx, -1.05, 1.45), (bx, -0.7, 2.35), 0.21, 'ink_light', seg=m.seg(8, 6))           # cylinder barrel
    # rotator + spreader (crane yellow) hanging from the tip
    tip = at(1.0)
    m.cyl(0.26, 0.35, m.seg(10, 6), 'ink_light', at=(bx, tip[1], tip[2] - 0.62))
    m.bb(0.55, 0.55, 0.22, 0.03, 'mustard', at=(bx, tip[1], tip[2] - 0.8), base=True)
    m.bb(4.2, 0.46, 0.4, 0.05, 'mustard', at=(0, tip[1], tip[2] - 1.2), base=True)
    for sx in (1, -1):
        m.bb(0.32, 0.62, 0.5, 0.04, 'mustard', at=(sx * 1.94, tip[1], tip[2] - 1.62), base=True)
        if lod == 0:
            m.bb(0.16, 0.16, 0.1, 0.01, 'ink', at=(sx * 1.94, tip[1], tip[2] - 1.72), base=True)  # twistlocks
    if lod == 0:
        m.cyl(0.09, 0.14, 8, 'orange', at=(cx + 0.45, cy + 0.6, 3.44))                          # beacon
        m.bar((-0.95, 1.2, 2.25), (-0.95, 1.2, 2.9), 0.06, 'ink', seg=6)                          # exhaust
    return m


# ---------------------------------------------------------------------------------------------- FORKLIFT
def forklift(lod):
    m = Mesh(lod)
    # body + rounded counterweight
    m.side([(-0.62, 0.22), (0.85, 0.22), (0.85, 1.1), (-0.25, 1.1), (-0.62, 0.8)], -0.56, 0.56, 'forklift_paint', bev=0.05)
    m.side([(0.8, 0.2), (1.1, 0.2), (1.18, 0.4), (1.18, 1.05), (1.05, 1.22), (0.8, 1.22)], -0.58, 0.58, 'forklift_paint', bev=0.05)
    m.yplate(1, 1.18, rect(-0.45, 0.45, 0.45, 0.95), HAZ, t=0.012)
    # wheels
    wheels(m, (-0.47, 0.47), (-0.42,), 0.32, 0.24, rim='grey', seg=12)
    wheels(m, (-0.46, 0.46), (0.92,), 0.26, 0.2, rim='grey', seg=10)
    # seat, steering column + wheel
    m.bb(0.48, 0.42, 0.12, 0.03, 'ink', at=(0, 0.42, 1.1), base=True)
    m.bb(0.46, 0.1, 0.45, 0.03, 'ink', at=(0, 0.62, 1.18), base=True)
    m.bar((0, -0.35, 1.05), (0, -0.2, 1.45), 0.04, 'ink', seg=6)
    m.cyl(0.17, 0.04, m.seg(10, 6), 'ink', M=T(0, -0.18, 1.45) @ R(-30, 'X'))
    # overhead guard: 4 posts + roof slats
    for s in (1, -1):
        m.beam((s * 0.5, -0.45, 1.05), (s * 0.5, -0.32, 2.12), 0.08, 0.08, 'ink', up=(0, 1, 0))
        m.beam((s * 0.5, 0.95, 1.18), (s * 0.5, 0.95, 2.12), 0.08, 0.08, 'ink', up=(0, 1, 0))
    if lod:
        m.box(1.08, 1.4, 0.07, 'ink', at=(0, 0.31, 2.1), base=True)
    else:
        for s in (1, -1):
            m.box(0.08, 1.4, 0.07, 'ink', at=(s * 0.5, 0.31, 2.1), base=True)
        for k in range(5):
            m.box(0.92, 0.07, 0.05, 'ink', at=(0, -0.3 + 0.3 * k, 2.11), base=True)
    # mast, carriage, forks (lowered)
    for s in (1, -1):
        m.box(0.1, 0.14, 2.12, 'ink_light', at=(s * 0.36, -0.72, 0.08), base=True)
    m.box(0.82, 0.12, 0.1, 'ink_light', at=(0, -0.72, 2.05), base=True)
    m.box(0.82, 0.12, 0.1, 'ink_light', at=(0, -0.72, 1.0), base=True)
    m.box(0.95, 0.08, 0.5, 'ink', at=(0, -0.84, 0.12), base=True)
    for x in (-0.28, 0.28):
        m.box(0.12, 0.05, 0.6, 'ink', at=(x, -0.9, 0.04), base=True)
        m.box(0.12, 1.0, 0.045, 'ink', at=(x, -1.4, 0.0), base=True)
    if lod == 0:
        m.cyl(0.07, 0.1, 8, 'orange', at=(0.42, 0.9, 2.17))                                    # beacon
        for s in (1, -1):
            m.yplate(-1, -0.62, rect(s * 0.32, s * 0.48, 0.85, 0.97), 'lamp_glow', t=0.02)
    return m


# ---------------------------------------------------------------------------------------------- SEMI TRUCK + 40 FT CONTAINER
def corrugated_wall(m, s, x_in, x_out, y0, y1, z0, z1, pitch, col):
    """Container side wall: trapezoid corrugation (top view zigzag) extruded z0..z1 on side s."""
    n = max(2, int(round((y1 - y0) / pitch)))
    p = (y1 - y0) / n
    d = x_out - x_in
    pts = [(x_in, y0)]
    for k in range(n):
        ya = y0 + k * p
        pts += [(x_in + d * 0.55, ya + p * 0.08), (x_in + d * 0.55, ya + p * 0.42), (x_out, ya + p * 0.58), (x_out, ya + p * 0.92)]
    pts += [(x_in + d * 0.55, y1), (x_in - 0.04, y1), (x_in - 0.04, y0)]
    pts = [(s * x, y) for x, y in pts]
    m.prism_xy(pts, z0, z1, col)


def truck_container(lod):
    m = Mesh(lod)
    r = 0.5
    # tractor
    for s in (1, -1):
        m.box(0.16, 6.0, 0.28, 'ink', at=(s * 0.45, -5.6, 0.72), base=True)
    cab_over(m, -8.45, -6.25, 2.45, 1.08, 3.75, 'truck_cab')
    m.frustum([(-1.15, -7.0), (1.15, -7.0), (1.15, -6.3), (-1.15, -6.3)], 3.75,
              [(-1.0, -6.75), (1.0, -6.75), (1.0, -6.3), (-1.0, -6.3)], 4.0, 'truck_cab', bev=0.03)   # roof deflector
    wheels(m, (-1.02, 1.02), (-7.45,), r, 0.38)
    wheels(m, (-0.92, 0.92), (-4.6, -3.35), r, 0.58)
    for s in (1, -1):
        m.cyl_y(0.3, 1.1, m.seg(10, 6), 'chrome', at=(s * 0.95, -5.6, 0.75))                    # fuel tanks
        m.bb(0.62, 2.4, 0.06, 0.02, 'ink_light', at=(s * 0.92, -3.98, 1.1), base=True)
    m.bb(1.6, 1.0, 0.18, 0.02, 'ink_light', at=(0, -4.0, 1.0), base=True)                       # fifth wheel
    if lod == 0:
        m.bar((1.0, -6.05, 1.2), (1.0, -6.05, 3.9), 0.08, 'chrome', seg=8)                      # exhaust stack
    # skeletal container chassis
    for s in (1, -1):
        m.box(0.18, 12.2, 0.3, 'ink', at=(s * 0.5, 1.5, 1.08), base=True)
    for y in (-4.4, 7.45):
        m.box(2.44, 0.2, 0.25, 'ink', at=(0, y, 1.13), base=True)
    for s in (1, -1):
        m.box(0.12, 0.12, 0.95, 'ink_light', at=(s * 0.8, -2.4, 0.1), base=True)                # landing legs
        m.box(0.3, 0.3, 0.06, 'ink', at=(s * 0.8, -2.4, 0.0), base=True)
    wheels(m, (-0.92, 0.92), (4.3, 5.55, 6.8), r, 0.58)
    for s in (1, -1):
        m.bb(0.6, 3.5, 0.06, 0.02, 'ink_light', at=(s * 0.92, 5.55, 1.08), base=True)
        m.yplate(1, 7.6, rect(s * 0.85, s * 1.15, 0.95, 1.12), 'lamp_red', t=0.03)
    m.bb(2.4, 0.12, 0.18, 0.02, 'ink_light', at=(0, 7.55, 0.82), base=True)                     # under-run bar
    # 40 ft container 12.19 x 2.44 x 2.59 on z 1.38
    y0, y1, z0, z1 = -4.6, 7.59, 1.38, 3.97
    m.box(2.44, y1 - y0, 0.12, 'container_dark', at=(0, (y0 + y1) / 2, z0), base=True)
    m.box(2.36, y1 - y0 - 0.2, 0.08, 'container_dark', at=(0, (y0 + y1) / 2, z1 - 0.1), base=True)
    if lod == 0:
        for s in (1, -1):
            corrugated_wall(m, s, 1.15, 1.2, y0 + 0.12, y1 - 0.12, z0 + 0.1, z1 - 0.1, 0.28, 'container')
    else:
        for s in (1, -1):
            m.box(0.06, y1 - y0 - 0.24, z1 - z0 - 0.2, 'container', at=(s * 1.17, (y0 + y1) / 2, z0 + 0.1), base=True)
    for s in (1, -1):
        for y in (y0 + 0.08, y1 - 0.08):
            m.box(0.16, 0.16, z1 - z0, 'container_dark', at=(s * 1.14, y, z0), base=True)      # corner posts
        m.box(0.1, y1 - y0, 0.14, 'container_dark', at=(s * 1.17, (y0 + y1) / 2, z1 - 0.14), base=True)
        m.box(0.1, y1 - y0, 0.14, 'container_dark', at=(s * 1.17, (y0 + y1) / 2, z0), base=True)
    m.box(2.3, 0.08, z1 - z0 - 0.2, 'container', at=(0, y0 + 0.08, z0 + 0.1), base=True)        # front wall
    # rear doors with locking bars
    for s in (1, -1):
        m.box(1.08, 0.08, z1 - z0 - 0.26, 'container', at=(s * 0.56, y1 - 0.06, z0 + 0.13), base=True)
    m.box(0.04, 0.1, z1 - z0 - 0.26, 'container_dark', at=(0, y1 - 0.05, z0 + 0.13), base=True)
    if lod == 0:
        for x in (-0.8, -0.3, 0.3, 0.8):
            m.cyl(0.03, z1 - z0 - 0.3, 6, 'grey', at=(x, y1 + 0.02, z0 + 0.15))
            m.box(0.1, 0.05, 0.08, 'grey', at=(x + 0.08, y1 + 0.03, z0 + 1.1))
        for z in (z0 + 0.35, z1 - 0.45):
            for s in (1, -1):
                m.box(0.18, 0.05, 0.1, 'grey', at=(s * 1.06, y1 + 0.01, z))                     # hinges
    return m


# ---------------------------------------------------------------------------------------------- FOOD TRUCK
def food_truck(lod):
    m = Mesh(lod)
    w = 2.3
    # body: lower paint, upper body colour, accent stripe; cab nose with near-vertical windscreen
    m.side([(-2.2, 0.55), (3.05, 0.55), (3.05, 1.3), (-2.2, 1.3)], -w / 2, w / 2, 'food_paint', bev=0.06)
    m.side([(-2.2, 1.28), (3.05, 1.28), (3.05, 2.9), (2.95, 3.0), (-2.1, 3.0), (-2.2, 2.9)], -w / 2, w / 2, 'food_body', bev=0.1)
    m.side([(-3.12, 0.55), (-2.15, 0.55), (-2.15, 2.92), (-2.75, 2.86), (-2.95, 1.75), (-3.18, 1.25)], -w / 2 + 0.05, w / 2 - 0.05,
           'food_paint', bev=0.08)
    for s in (1, -1):
        m.xplate(s, w / 2, rect(-2.15, 3.0, 2.52, 2.64), 'food_paint', t=0.012)
    # glass: windscreen, cab side windows
    m.plate([(-1.0, -2.94, 1.85), (1.0, -2.94, 1.85), (1.0, -2.76, 2.78), (-1.0, -2.76, 2.78)], (0, -1, 0.2), 0.015, 'glass_dark')
    for s in (1, -1):
        m.xplate(s, w / 2 - 0.05, [(-2.85, 1.75), (-2.3, 1.75), (-2.3, 2.7), (-2.72, 2.7)], 'glass_dark', t=0.015)
    # front: grille, lights, bumper; rear: lights, step bumper, door split
    m.yplate(-1, -3.15, rect(-0.6, 0.6, 0.8, 1.15), 'ink', t=0.015)
    for s in (1, -1):
        m.yplate(-1, -3.15, rect(s * 0.7, s * 0.95, 0.9, 1.12), 'lamp_glow', t=0.02)
        m.yplate(1, 3.05, rect(s * 0.85, s * 1.05, 1.0, 1.4), 'lamp_red', t=0.02)
    m.bb(2.3, 0.22, 0.25, 0.03, 'chrome', at=(0, -3.2, 0.5), base=True)
    m.bb(2.2, 0.3, 0.12, 0.02, 'ink_light', at=(0, 3.15, 0.55), base=True)
    m.yplate(1, 3.05, rect(-0.02, 0.02, 0.62, 2.85), 'ink_light', t=0.012)
    # serving window on the kerb side (-X): dark opening, counter, propped awning flap, blank menu board
    s = -1
    m.xplate(s, w / 2, rect(-1.1, 1.75, 1.42, 2.32), 'ink_dark', t=0.015)
    m.bb(0.34, 2.95, 0.06, 0.02, 'chrome', at=(s * (w / 2 + 0.14), 0.32, 1.36), base=True)
    Mf = T(s * (w / 2 + 0.03), 0.32, 2.42) @ R(80 * s, 'Y')
    m.bb(0.06, 3.0, 0.85, 0.02, 'food_paint', M=Mf, at=(0, 0, 0.425))
    if lod == 0:
        for y in (-1.0, 1.65):
            m.bar((s * (w / 2), y, 1.75), (s * 1.95, y, 2.52), 0.025, 'ink', seg=4)                  # struts
        m.xplate(s, w / 2, rect(2.05, 2.85, 1.45, 2.3), 'ink', t=0.02)
        m.xplate(s, w / 2 + 0.02, rect(2.1, 2.8, 1.5, 2.25), 'chalk', t=0.012)                      # blank menu board
    # roof: vent hood, AC box; side gas bottles at the rear
    m.bb(1.0, 0.8, 0.35, 0.04, 'chrome', at=(0, 0.6, 3.0), base=True)
    m.bb(0.8, 0.9, 0.28, 0.04, 'chalk', at=(0, 2.1, 3.0), base=True)
    if lod == 0:
        for x in (0.55, 0.85):
            m.cyl(0.14, 0.6, 8, 'chalk', at=(x, 3.38, 0.6))
            m.cyl(0.05, 0.1, 6, 'ink', at=(x, 3.38, 1.2))
    # wheels with dark wells
    hz = 0.42 * math.cos(math.pi / 12)
    for sx in (1, -1):
        for y in (-2.45, 1.95):
            well(m, sx, w / 2, y, 0.55, 0.5)
    wheels(m, (-0.88, 0.88), (-2.45,), 0.42, 0.3)
    wheels(m, (-0.86, 0.86), (1.95,), 0.42, 0.42)
    return m


# ---------------------------------------------------------------------------------------------- RAIL WAGON (BASE 1)
def rail_wagon(lod):
    m = Mesh(lod)
    Lb, hw = 23.0, 1.6                      # body length, half width (outer)
    y0, y1 = -Lb / 2, Lb / 2
    zf, zw = 1.3, 3.45                      # floor top, wall top (eaves)
    th = 0.1
    # underframe: sills, floor slab (wood floor inside), buffer beams + buffers + couplers
    m.box(2 * hw - 0.1, Lb, 0.2, 'ink_light', at=(0, 0, zf - 0.2), base=True, cols=[None, 'wood', None, None, None, None])
    for s in (1, -1):
        m.box(0.24, Lb + 0.1, 0.3, 'ink', at=(s * (hw - 0.12), 0, zf - 0.42), base=True)
    for e in (1, -1):
        m.box(2.9, 0.22, 0.42, 'ink', at=(0, e * (Lb / 2 + 0.06), zf - 0.5), base=True)
        for s in (1, -1):
            if lod == 0:
                m.cyl_y(0.09, 0.42, 8, 'ink_light', at=(s * 0.88, e * (Lb / 2 + 0.38), zf - 0.3))
            m.cyl_y(0.22, 0.06 if lod == 0 else 0.48, m.seg(10, 6), 'ink', at=(s * 0.88, e * (Lb / 2 + (0.6 if lod == 0 else 0.39)), zf - 0.3))
        m.box(0.3, 0.45, 0.22, 'ink', at=(0, e * (Lb / 2 + 0.33), zf - 0.4), base=True)
    # bogies with two axles each (1520 mm gauge, wheel r 0.475)
    for yb in (-8.3, 8.3):
        m.box(2.1, 0.5, 0.3, 'ink', at=(0, yb, 0.62), base=True)
        for s in (1, -1):
            m.bb(0.16, 2.9, 0.42, 0.03, 'ink_light', at=(s * 0.98, yb, 0.3), base=True)
            if lod == 0:
                for dy in (-0.45, 0.45):
                    m.cyl(0.09, 0.3, 8, 'ink', at=(s * 0.98, yb + dy, 0.72))                   # springs
        for dy in (-0.925, 0.925):
            if lod == 0:
                m.cyl_x(0.07, 1.7, 6, 'ink', at=(0, yb + dy, 0.47))
            for s in (1, -1):
                m.wheel(s * 0.76, yb + dy, 0.475, 0.14, 'ink_light', 'ink' if lod == 0 else None, seg=14, rim_r=0.3)
    # walls: board panels between steel posts (door opening on the -X side, centre)
    n = 12
    pw = Lb / n
    door = (-0.95, 0.95)
    zdoor = 3.25
    for s in (1, -1):
        for k in range(n):
            a, b = y0 + k * pw, y0 + (k + 1) * pw
            segs = [(a, b)]
            if s < 0 and a < door[1] and b > door[0]:
                segs = []
                if a < door[0]:
                    segs.append((a, door[0]))
                if b > door[1]:
                    segs.append((door[1], b))
                m.box(th, min(b, door[1]) - max(a, door[0]), zw - zdoor, BOARDS,
                      at=(s * (hw - th / 2), (min(b, door[1]) + max(a, door[0])) / 2, zdoor), base=True)
            for c, d in segs:
                m.box(th, d - c, zw - zf, BOARDS, at=(s * (hw - th / 2), (c + d) / 2, zf), base=True)
            if lod == 0 and not (s < 0 and a < door[1] and b > door[0]):                       # diagonal brace
                up = (k % 2 == 0)
                m.beam((s * (hw + 0.02), a + 0.1, zf + 0.1 if up else zw - 0.12), (s * (hw + 0.02), b - 0.1, zw - 0.12 if up else zf + 0.1),
                       0.04, 0.1, 'wagon_roof', up=(s, 0, 0))
        for k in range(n + 1):                                                                    # posts
            y = y0 + k * pw
            if (s < 0 and door[0] < y < door[1]) or (lod and k % 2 and 0 < k < n):
                continue
            m.box(0.08, 0.14, zw - zf + 0.25, 'wagon_roof', at=(s * (hw + 0.04), min(max(y, y0 + 0.07), y1 - 0.07), zf - 0.2), base=True)
        if lod == 0:
            m.box(0.06, Lb, 0.1, 'wagon_roof', at=(s * (hw + 0.03), 0, 2.35), base=True)          # belt rail
    for e in (1, -1):                                                                             # end walls
        m.box(2 * hw - 2 * th, th, zw - zf, BOARDS, at=(0, e * (Lb / 2 - th / 2), zf), base=True)
        if lod == 0:
            for x in (-0.8, 0.8):
                m.box(0.12, 0.08, zw - zf, 'wagon_roof', at=(x, e * (Lb / 2 + 0.04), zf), base=True)
    # door frame posts, sliding door shifted open along its rail, steps under the doorway
    for y in door:
        m.box(0.12, 0.14, zw - zf + 0.2, 'wagon_roof', at=(-(hw + 0.05), y, zf - 0.15), base=True)
    m.box(0.08, 4.4, 0.1, 'ink', at=(-(hw + 0.12), 1.0, zdoor + 0.08), base=True)               # door rail
    m.box(0.07, 2.0, zdoor - zf + 0.04, BOARDS, at=(-(hw + 0.17), 1.95, zf - 0.02), base=True)  # door leaf (open)
    if lod == 0:
        for z in (zf + 0.05, zdoor - 0.1):
            m.box(0.04, 2.0, 0.09, 'wagon_roof', at=(-(hw + 0.22), 1.95, z), base=True)
        m.beam((-(hw + 0.22), 1.0, zf + 0.1), (-(hw + 0.22), 2.9, zdoor - 0.12), 0.03, 0.09, 'wagon_roof', up=(-1, 0, 0))
    for s in (1, -1):                                                                             # step hangers
        m.box(0.06, 0.06, 0.95, 'ink', at=(-(hw + 0.1), s * 0.55, zf - 1.15), base=True)
    for z in (0.4, 0.82):
        m.box(0.3, 1.2, 0.05, 'ink_light', at=(-(hw + 0.12), 0, z), base=True)
    # small barred windows high on the walls
    for s, ys in ((1, (-7.8, -2.0, 4.0, 8.8)), (-1, (-7.8, 6.2))):
        for y in ys:
            m.xplate(s, hw, rect(y - 0.35, y + 0.35, 2.55, 3.05), 'glass_dark', t=0.02)
            if lod == 0:
                for dy in (-0.18, 0.0, 0.18):
                    m.box(0.04, 0.04, 0.5, 'ink', at=(s * (hw + 0.035), y + dy, 2.55), base=True)
    # barrel roof (thick arc) with stove pipe
    seg = m.seg(10, 6)
    arc = []
    for k in range(seg + 1):
        t = -1 + 2 * k / seg
        x = (hw + 0.08) * t
        arc.append((x, zw + 0.42 * (1 - t * t)))
    inner = [(x * 0.97, z - 0.08) for x, z in reversed(arc)]
    m.end(arc + inner, -(Lb / 2 + 0.12), Lb / 2 + 0.12, 'wagon_roof')
    m.cyl(0.11, 0.75, m.seg(8, 6), 'ink', at=(0.65, 7.6, zw + 0.25))
    m.cyl(0.18, 0.06, m.seg(8, 6), 'ink', at=(0.65, 7.6, zw + 1.0))
    return m


# ---------------------------------------------------------------------------------------------- BLACK SUV (Elite / FBI)
def suv(lod):
    m = Mesh(lod)
    hw = 0.98
    m.side([(-2.5, 0.42), (2.46, 0.42), (2.5, 0.75), (2.46, 1.1), (-2.38, 1.06), (-2.52, 0.8)], -hw, hw, 'suv_paint', bev=0.06)
    m.side([(-1.05, 1.04), (2.36, 1.04), (2.3, 1.82), (-0.32, 1.84)], -hw + 0.08, hw - 0.08, 'suv_paint', bev=0.06)
    # glass: windscreen, rear, three side windows per side
    m.plate([(-0.84, -1.0, 1.12), (0.84, -1.0, 1.12), (0.8, -0.38, 1.76), (-0.8, -0.38, 1.76)], (0, -1, 0.9), 0.015, 'glass_v')
    m.plate([(-0.8, 2.35, 1.2), (0.8, 2.35, 1.2), (0.78, 2.3, 1.72), (-0.78, 2.3, 1.72)], (0, 1, 0.1), 0.015, 'glass_v')
    for sx in (1, -1):
        for y0, y1 in ((-0.62, 0.55), (0.65, 1.62), (1.72, 2.2)):
            m.xplate(sx, hw - 0.08, [(max(y0, -0.6), 1.16), (y1, 1.16), (y1, 1.72), (max(y0, -0.3), 1.72)], 'glass_v', t=0.015)
        if lod == 0:
            m.xplate(sx, hw, rect(0.6, 0.63, 0.5, 1.04), 'ink', t=0.01)                             # door seams
            m.xplate(sx, hw, rect(1.67, 1.7, 0.5, 1.04), 'ink', t=0.01)
            m.box(0.05, 1.9, 0.05, 'chrome', at=(sx * 0.7, 1.0, 1.84), base=True)                     # roof rails
            m.bb(0.08, 0.2, 0.14, 0.02, 'suv_paint', at=(sx * (hw + 0.06), -0.85, 1.12), base=True)  # mirrors
    # front: chrome grille, lights; bumpers
    m.yplate(-1, -2.52, rect(-0.55, 0.55, 0.62, 0.98), 'chrome', t=0.02)
    if lod == 0:
        for z in (0.7, 0.8, 0.9):
            m.yplate(-1, -2.54, rect(-0.5, 0.5, z, z + 0.04), 'ink', t=0.01)
    for sx in (1, -1):
        m.yplate(-1, -2.5, rect(sx * 0.62, sx * 0.9, 0.82, 0.97), 'lamp_glow', t=0.02)
        m.yplate(1, 2.46, rect(sx * 0.62, sx * 0.9, 0.86, 1.04), 'lamp_red', t=0.02)
    m.bb(2.0, 0.2, 0.22, 0.03, 'ink', at=(0, -2.5, 0.38), base=True)
    m.bb(2.0, 0.2, 0.22, 0.03, 'ink', at=(0, 2.48, 0.38), base=True)
    for sx in (1, -1):
        for y in (-1.5, 1.5):
            well(m, sx, hw, y, 0.4, 0.46)
    wheels(m, (-0.84, 0.84), (-1.5, 1.5), 0.4, 0.28, rim='chrome', seg=12)
    m.verts = [(x * 0.94, y * 0.94, z * 0.94) for x, y, z in m.verts]            # 4.87 m: fits the 4.8 m guard box too
    return m


SPECS = [
    dict(name='MW86_MixerTruck', family='Machines', kind='ground', budget=6000, folder='mixer_truck', target=(4.0, 9.6, 3.4),
         notes='Concrete mixer truck, cab-over, banded drum (kind concrete_mixer_truck, data 9.6 x 4.0 x 3.4, long axis on data X).'),
    dict(name='MW86_DumpTruck', family='Machines', kind='ground', budget=6000, folder='dump_truck', target=(3.6, 8.8, 3.2),
         notes='3-axle tipper with a sand load (kind dump_truck, data 8.8 x 3.6 x 3.2, long axis on data X).'),
    dict(name='MW86_WheelLoader', family='Machines', kind='ground', budget=6000, folder='wheel_loader', target=(2.8, 4.4, 3.0),
         notes='Compact wheel loader, bucket on the ground (kind wheel_loader, data 4.4 x 2.8 x 3.0, long axis on data X).'),
    dict(name='MW86_VanOnJacks', family='Machines', kind='ground', budget=3000, folder='van_on_jacks', target=(3.2, 7.2, 2.4),
         notes='High-roof panel van on jack stands, wheels off, hood open (kind van_on_jacks, workshop 03-01).'),
    dict(name='MW86_ReachStacker', family='Machines', kind='ground', budget=6000, folder='reach_stacker', target=(4.2, 7.5, 5.0),
         notes='Reach stacker, P3 blue (variant A), crane-yellow spreader (kind reach_stacker, data 4.2 x 7.5 x 5.0, long axis on data Y).'),
    dict(name='MW86_Forklift', family='Machines', kind='ground', budget=3000, folder='forklift', target=(1.2, 3.2, 2.2),
         notes='Counterbalance forklift, forks lowered (kind forklift, data 3.2 x 1.2 x 2.2, long axis on data X).'),
    dict(name='MW86_TruckContainer', family='Machines', kind='ground', budget=6000, folder='truck_container', target=(2.5, 17.0, 4.0),
         tol_m=0.3, notes='Cab-over tractor + skeletal chassis + 40 ft corrugated container (kind truck_with_container, 17 x 2.5 x 4.0, cab_end east). Mirrors stick out 0.25 m past the 2.5 m data box.'),
    dict(name='MW86_FoodTruck', family='Machines', kind='ground', budget=3000, folder='food_truck', target=(3.1, 6.5, 3.0),
         notes='Step-van food truck, serving window + propped awning on the kerb side (Blender -X = Unity +X), blank menu board, no text.'),
    dict(name='MW86_RailWagon_Base1', family='Machines', kind='ground', budget=8000, folder='rail_wagon_base1', target=(3.2, 24.0, 4.0),
         tol_m=0.25, notes='Base 1: old 24 m boxcar on two bogies, enterable (hollow, floor 1.3 m over the rail), sliding door shifted open on Blender -X (Unity +X), steps, barred windows, barrel roof, stove pipe.'),
    dict(name='MW86_SUV_Black', family='Machines', kind='ground', budget=3000, folder='suv_black', target=(2.2, 4.8, 1.9),
         notes='Black SUV for kind black_suv (Elite 07-05 / FBI guard; currently mapped to the blue Soviet sedan prefab). Optional replacement, not a box.'),
]
BUILDERS = {'MW86_SUV_Black': suv, 'MW86_MixerTruck': mixer, 'MW86_DumpTruck': dump_truck, 'MW86_WheelLoader': wheel_loader, 'MW86_VanOnJacks': van_on_jacks,
            'MW86_ReachStacker': reach_stacker, 'MW86_Forklift': forklift, 'MW86_TruckContainer': truck_container,
            'MW86_FoodTruck': food_truck, 'MW86_RailWagon_Base1': rail_wagon}

if __name__ == '__main__':
    L.run_family(SPECS, BUILDERS)
