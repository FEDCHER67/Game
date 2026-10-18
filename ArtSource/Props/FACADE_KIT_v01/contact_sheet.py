"""Headless contact sheet for FACADE_KIT_v01 (matplotlib, no GL needed): every piece on a 1 m grid
plus two assemblies built only from kit pieces + plain wall boxes (khrushchevka bay, Downtown alley corner)."""
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
import numpy as np

LIGHT = np.array([-.4, -.7, .6]) / np.linalg.norm([-.4, -.7, .6])


def xf(tris, dx=0, dy=0, dz=0, rot=0):
    c, s = math.cos(rot), math.sin(rot)
    return [[[(x * c - y * s + dx, x * s + y * c + dy, z + dz) for x, y, z in t], col] for t, col in tris]


def box(x0, x1, y0, y1, z0, z1, col):
    v = lambda x, y, z: (x, y, z)
    q = [[v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1)], [v(x1, y0, z0), v(x1, y1, z0), v(x1, y1, z1), v(x1, y0, z1)],
         [v(x0, y1, z0), v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1)], [v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1)],
         [v(x1, y1, z0), v(x0, y1, z0), v(x0, y1, z1), v(x1, y1, z1)]]
    out = []
    for a in q:  # split into ~1 m cells so painter's sort works against attached pieces
        a = np.array(a, float)
        nu = max(1, int(np.linalg.norm(a[1] - a[0]) / 1.0)); nv = max(1, int(np.linalg.norm(a[3] - a[0]) / 1.0))
        for i in range(nu):
            for j in range(nv):
                P = lambda u, v: tuple(a[0] + (a[1] - a[0]) * u / nu + (a[3] - a[0]) * v / nv)
                out.append([[P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)], col])
    return out


def draw(ax, tris, grid, elev=18, azim=-62):
    polys, fc = [], []
    for t, col in tris:
        p = np.array(t)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        cam = np.array([math.cos(math.radians(azim)), math.sin(math.radians(azim)), .3])
        if len(t) == 4 and np.dot(n, cam) < 0:
            continue  # backface cull wall cells
        ln = np.linalg.norm(n)
        sh = .45 + .55 * max(0, float(np.dot(n / ln, LIGHT))) if ln > 1e-12 else .6
        polys.append(p)
        c = np.array(col[:3]) ** (1 / 2.2)
        fc.append(tuple(np.clip(c * sh, 0, 1)))
    (x0, x1), (y0, y1) = grid
    lines = [[(x, y0, 0), (x, y1, 0)] for x in range(x0, x1 + 1)] + [[(x0, y, 0), (x1, y, 0)] for y in range(y0, y1 + 1)]
    ax.add_collection3d(Line3DCollection(lines, colors=(.75, .75, .75), linewidths=.3))
    ax.add_collection3d(Poly3DCollection(polys, facecolors=fc, edgecolors=(0, 0, 0, .15), linewidths=.15))
    pts = np.concatenate(polys)
    mn, mx = pts.min(0), pts.max(0)
    mn = np.minimum(mn, [x0, y0, 0]); mx = np.maximum(mx, [x1, y1, 0])
    c, r = (mn + mx) / 2, (mx - mn).max() / 2 * .9
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev, azim); ax.set_axis_off()


def khrushchevka(d):
    W, H, FH, PIT = 12.8, 11.2, 2.8, 3.2
    grey, dark = (.40, .39, .36), (.25, .24, .22)
    t = box(-W / 2, W / 2, 0, 6, 0, H, grey) + box(-W / 2 - .1, W / 2 + .1, -.02, 6.1, H, H + .05, dark)
    t += xf(d['FK_R_Parapet_3m2'], 0, 0, H)
    for b in range(4):
        t += xf(d['FK_R_Parapet_3m2'], -W / 2 + PIT * (b + .5), 0, H) if b != 1 else []
    for f in range(4):
        for b in range(4):
            x = -W / 2 + PIT * (b + .5)
            if f == 0 and b == 1:
                continue
            if f > 0 and b == 2:
                t += xf(d['FK_R_Balcony_Glazed' if f % 2 else 'FK_R_Balcony_Open'], x, 0, f * FH)
                continue
            t += xf(d['FK_R_Window_Frame'], x, 0, f * FH + .85 + (.45 if f == 0 else 0))
    xe = -W / 2 + PIT * 1.5
    t += xf(d['FK_R_IronDoor'], xe, 0, .48) + xf(d['FK_R_Entrance_Steps3'], xe, 0, 0) + xf(d['FK_R_Entrance_Canopy'], xe, 0, 2.95)
    for f in range(4):
        t += xf(d['FK_R_Drainpipe_2m8'], W / 2 - .3, 0, f * FH)
    t += xf(d['FK_R_Roof_Vent'], -3, 3, H) + xf(d['FK_R_Roof_Vent'], 3.5, 3, H)
    return t


def alley(d):
    FH, brick, stone = 3.5, (.36, .17, .12), (.55, .5, .42)
    L, H = 9.0, FH * 3
    t = box(-L, 0, 0, 7, 0, H, brick)                                   # building A: alley face y=0, x in [-L,0]
    t += box(1.0, 7, -L, 0, 0, H - 3.5, (.45, .40, .33))                # building B (street side), lower
    t += xf(d['FK_D_Parapet_2m'], -1, 0, H, 0) + xf(d['FK_D_Parapet_2m'], -3, 0, H) + xf(d['FK_D_Parapet_2m'], -7, 0, H)
    for x in (-1, -3, -5, -7):
        t += xf(d['FK_D_Cornice_2m'], x, 0, H - .55)
    for f in range(3):
        for x in (-1.3, -7.6):
            t += xf(d['FK_D_Window_Frame'], x, 0, f * FH + .9)
        if f > 0:
            t += xf(d['FK_D_FireEscape_Landing'], -4.4, 0, f * FH)
            t += xf(d['FK_D_Window_Frame'], -4.4, 0, f * FH + .9) if f else []
        if f > 0 and f < 3:
            t += xf(d['FK_D_FireEscape_Stair'], -4.4, 0, f * FH) if f < 2 else []
    t += xf(d['FK_D_FireEscape_Ladder'], -3.6, 0, FH)
    t += xf(d['FK_D_AC_Unit'], -1.3, 0, FH + .1) + xf(d['FK_D_AC_Unit'], -7.6, 0, 2 * FH + .1)
    t += xf(d['FK_D_RoofWaterTank'], -5, 3.5, H)
    t += xf(d['FK_D_Dumpster'], -6.5, -1.0, 0, 0)
    # building B faces the alley (wall plane x=1, outward -X): rotate -90
    for f in range(2):
        t += xf(d['FK_D_Window_Frame'], 1.0, -6, f * FH + .9, -math.pi / 2)
    t += xf(d['FK_D_AC_Unit'], 1.0, -3, FH + .2, -math.pi / 2)
    t += xf(d['FK_D_Storefront_Awning'], 4, -L, 3.1, 0)
    return t


def render(d, manifest, path):
    names = [m['name'] for m in manifest]
    n = len(names)
    cols = 8
    rows = math.ceil(n / cols)
    fig = plt.figure(figsize=(cols * 3, rows * 3.1 + 7.5), dpi=110)
    gs = fig.add_gridspec(rows + 2, cols, height_ratios=[1] * rows + [2.6, .01])
    for i, nm in enumerate(names):
        ax = fig.add_subplot(gs[i // cols, i % cols], projection='3d')
        pts = np.concatenate([np.array(t) for t, _ in d[nm]])
        g = ((int(math.floor(pts[:, 0].min())), int(math.ceil(pts[:, 0].max()))),
             (int(math.floor(pts[:, 1].min())), int(math.ceil(pts[:, 1].max()))))
        draw(ax, d[nm], g)
        m = manifest[i]
        ax.set_title(f"{nm[3:]}\n{m['tris_lod0']} tris · {m['colliders']} UCX" + (f" · LOD1 {m['tris_lod1']}" if m['tris_lod1'] else ''),
                     fontsize=7)
    ax = fig.add_subplot(gs[rows, :cols // 2], projection='3d')
    draw(ax, khrushchevka(d), ((-8, 8), (-4, 6)), elev=12, azim=-70)
    ax.set_title('Sample: khrushchevka KH1b tile 12.8 x 11.2 m (4 bays x 3.2 m, 4 floors x 2.8 m)', fontsize=9)
    ax = fig.add_subplot(gs[rows, cols // 2:], projection='3d')
    draw(ax, alley(d), ((-10, 7), (-10, 7)), elev=18, azim=-128)
    ax.set_title('Sample: Downtown alley corner (3 floors x 3.5 m)', fontsize=9)
    fig.suptitle('FACADE_KIT_v01 — 1 m grid, placeholder materials', fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
