"""Stylised tileable ground / nature textures for VOLUNTEERS ONLY map props.

Usage (from the repo root):
    python3 ArtSource/Props/MAP_PROPS/TEXTURES/gen_textures.py [--size 1024] [--seed 1] [--only Sand,Grass]
                                                               [--out DIR] [--revision 1] [--force]

Writes TEXTURES/Out/vNN/TX_<Name>_Albedo_vNN.png, TX_<Name>_Normal_vNN.png, Previews/<Name>_preview.png,
Previews/contact_sheet.png and textures_vNN.json. Same seed -> identical bytes.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texlib as tl  # noqa: E402

HERE = Path(__file__).resolve().parent

# Prop palette (RGB) the textures must sit next to.
P = {
    'concrete': (162, 158, 148), 'wood': (150, 108, 68), 'leaf': (92, 150, 64), 'leaf_dark': (58, 110, 56),
    'pine': (44, 96, 66), 'bark': (104, 80, 60), 'birch': (228, 224, 214), 'sand': (222, 200, 150),
}


# ======================================================================== generators
# Each returns (albedo float HxWx3 in 0..1, height float HxW, normal strength).

def gen_sea(u, v, rng):
    uw, vw = tl.warp(u, v, 3, rng, 0.06)
    depth = tl.fbm(uw, vw, 2, rng, 4)
    base = tl.ramp(tl.soft_posterize(depth, 4, 0.3), [
        (0.0, (30, 92, 120)), (0.45, (40, 118, 140)), (0.75, (54, 140, 152)), (1.0, (66, 156, 160))])
    # caustic-like soft web of lighter cell edges (two layers, warped)
    u2, v2 = tl.warp(u, v, 4, rng, 0.06)
    c1 = tl.voronoi(u2, v2, 7, rng)
    web1 = 1.0 - tl.smoothstep(0.0, 0.16, c1['f2'] - c1['f1'])
    c2 = tl.voronoi(u2 + 0.37, v2 + 0.11, 11, rng)
    web2 = 1.0 - tl.smoothstep(0.0, 0.12, c2['f2'] - c2['f1'])
    mask = tl.smoothstep(0.35, 0.65, tl.fbm(u, v, 3, rng, 3))
    caustic = np.clip(web1 * 0.8 + web2 * 0.45 * mask, 0, 1)
    img = tl.mix(base, tl.rgb((112, 190, 188)), caustic * 0.45)
    # foam streaks: elongated horizontally (low x freq, high y freq), sparse
    su, sv = tl.warp(u, v, 3, rng, 0.04)
    streak = tl.fbm(su, sv, (3, 14), rng, 3)
    foam = tl.smoothstep(0.6, 0.74, streak) * tl.smoothstep(0.45, 0.7, tl.fbm(u, v, 2, rng, 2))
    img = tl.mix(img, tl.rgb((206, 232, 226)), foam * 0.7)
    height = depth * 0.6 + caustic * 0.3 + foam * 0.2
    return img, height, 10.0


def gen_sand(u, v, rng):
    uw, vw = tl.warp(u, v, 3, rng, 0.08)
    ripple_phase = tl.fbm(u, v, 2, rng, 3) * 1.6
    ripples = 0.5 + 0.5 * np.sin(2 * np.pi * (9 * vw + 2 * uw + ripple_phase))
    ripples = ripples ** 1.6                               # sharper crests, wide troughs (wind ripples)
    rip_amt = tl.smoothstep(0.3, 0.7, tl.fbm(u, v, 2, rng, 3))
    patches = tl.fbm(u, v, 3, rng, 4)
    t = tl.soft_posterize(patches, 3, 0.35)
    img = tl.ramp(t, [(0.0, (204, 180, 132)), (0.5, (220, 198, 148)), (1.0, (232, 214, 168))])
    img = tl.shade(img, 1.0 + (ripples - 0.5) * 0.09 * (0.4 + rip_amt))
    # speckles: small grains, a few dark and a few light
    g = tl.value_noise(u, v, 340, rng)
    g2 = tl.value_noise(u, v, 260, rng)
    img = tl.mix(img, tl.rgb((150, 124, 92)), tl.smoothstep(0.86, 0.93, g) * 0.55)
    img = tl.mix(img, tl.rgb((246, 236, 210)), tl.smoothstep(0.88, 0.95, g2) * 0.6)
    height = ripples * (0.4 + rip_amt) * 0.8 + patches * 0.4
    return img, height, 10.0


def _pebbles(u, v, rng, cells, radius, coverage):
    """Periodic pebble field from Voronoi: returns (mask 0..1, dome height, per-pebble tone)."""
    c = tl.voronoi(u, v, cells, rng, 0.8)
    present, rad, tone = tl.cell_random(c['id'], c['n'], rng, 3)
    r = radius * (0.55 + 0.6 * rad)
    # slightly squashed pebbles
    d = np.sqrt((c['dx'] * 1.15) ** 2 + (c['dy'] * 0.9) ** 2)
    m = (1.0 - tl.smoothstep(r * 0.82, r, d)) * (present < coverage)
    dome = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1)) * m
    return m, dome, tone


def gen_ground(u, v, rng):
    uw, vw = tl.warp(u, v, 3, rng, 0.07)
    big = tl.fbm(uw, vw, 3, rng, 5)
    t = tl.soft_posterize(big, 4, 0.3)
    img = tl.ramp(t, [(0.0, (112, 86, 62)), (0.4, (130, 102, 74)), (0.75, (146, 118, 86)), (1.0, (156, 132, 98))])
    fine = tl.fbm(u, v, 24, rng, 3)
    img = tl.shade(img, 0.94 + fine * 0.12)
    # dry lighter crusts
    crust = tl.smoothstep(0.62, 0.7, tl.fbm(u, v, 5, rng, 4))
    img = tl.mix(img, tl.rgb((168, 146, 112)), crust * 0.5)
    m, dome, tone = _pebbles(u, v, rng, 14, 0.3, 0.55)
    cluster = tl.smoothstep(0.4, 0.62, tl.fbm(u, v, 3, rng, 3))   # pebbles gather in patches
    m, dome = m * cluster, dome * cluster
    pcol = tl.ramp(tone, [(0.0, (120, 106, 90)), (0.5, (152, 138, 118)), (1.0, (176, 162, 138))])
    pcol = tl.shade(pcol, 0.82 + 0.25 * dome)
    img = tl.mix(img, pcol, m)
    # contact shadow ring around pebbles
    ring = tl.blur_wrap(m, 2, 1) - m
    img = tl.shade(img, 1.0 - np.clip(ring, 0, 1) * 0.35)
    m2, dome2, tone2 = _pebbles(u, v, rng, 36, 0.24, 0.45)
    m2, dome2 = m2 * cluster, dome2 * cluster
    img = tl.mix(img, tl.shade(tl.ramp(tone2, [(0, (104, 92, 80)), (1, (164, 150, 128))]), 0.85 + 0.2 * dome2), m2 * 0.9)
    height = big * 0.5 + fine * 0.15 + dome * 1.2 + dome2 * 0.6 + crust * 0.1
    return img, height, 16.0


def gen_dirt(u, v, rng):
    uw, vw = tl.warp(u, v, 3, rng, 0.08)
    big = tl.fbm(uw, vw, 2, rng, 5)
    t = tl.soft_posterize(big, 4, 0.3)
    img = tl.ramp(t, [(0.0, (70, 54, 40)), (0.5, (88, 68, 50)), (1.0, (106, 84, 62))])
    fine = tl.fbm(u, v, 20, rng, 3)
    img = tl.shade(img, 0.93 + fine * 0.14)
    # two worn wheel tracks running along v (tileable: function of u only, wobbling with v)
    wob = (tl.fbm(u, v, (1, 3), rng, 2) - 0.5) * 0.06
    track = np.zeros_like(u)
    for c in (0.27, 0.73):
        d = np.abs(tl.wrap_dist(u + wob, c))
        track = np.maximum(track, 1.0 - tl.smoothstep(0.06, 0.11, d))
    tread = 0.5 + 0.5 * np.sin(2 * np.pi * 96 * (v + wob * 0.3))
    img = tl.shade(img, 1.0 - track * 0.12)
    img = tl.shade(img, 1.0 - track * (tread > 0.75) * 0.06 * tl.smoothstep(0.4, 0.7, tl.fbm(u, v, 4, rng, 2)))
    # puddle-ish dark wet patches, smoother inside, biased into the tracks
    wet_f = tl.fbm(uw, vw, 5, rng, 4) + track * 0.12
    wet = tl.smoothstep(0.63, 0.71, wet_f)
    wet_rim = tl.smoothstep(0.59, 0.64, wet_f) - wet
    img = tl.mix(img, tl.rgb((54, 44, 36)), wet * 0.65)
    img = tl.mix(img, tl.rgb((60, 48, 38)), np.clip(wet_rim, 0, 1) * 0.4)
    # sheen on wet areas (lighter sky reflection hints)
    sheen = wet * tl.smoothstep(0.62, 0.8, tl.fbm(u, v, 6, rng, 2))
    img = tl.mix(img, tl.rgb((92, 90, 86)), sheen * 0.35)
    m, dome, tone = _pebbles(u, v, rng, 40, 0.22, 0.3)
    img = tl.mix(img, tl.shade(tl.ramp(tone, [(0, (90, 80, 68)), (1, (128, 116, 98))]), 0.85 + 0.2 * dome), m * (1 - wet))
    height = big * 0.5 + fine * 0.2 - track * 0.35 - wet * 0.25 + dome * 0.6 * (1 - wet)
    height = np.where(wet > 0.5, tl.blur_wrap(height, 3, 1), height)
    return img, height, 20.0


def _blade(base, length, width, ang, h0):
    """Tapered grass-blade stroke; colour darkens towards the root."""
    ca, sa = np.cos(ang), np.sin(ang)

    def fn(X, Y):
        a = -(X * sa + Y * ca)                       # along the blade, pointing up the image
        b = X * ca - Y * sa
        s = a / length
        m = (s > 0) & (s < 1) & (np.abs(b) < width * (1 - s) + 0.35)
        col = base[None, None, :] * (0.82 + 0.3 * np.clip(s, 0, 1))[..., None]
        return m, col, h0 + 0.5 * np.clip(s, 0, 1)
    return fn


def gen_grass(u, v, rng, size):
    big = tl.fbm(*tl.warp(u, v, 3, rng, 0.06), 2, rng, 4)
    t = tl.soft_posterize(big, 4, 0.3)
    img = tl.ramp(t, [(0.0, (58, 108, 52)), (0.35, (72, 126, 56)), (0.7, (88, 144, 62)), (1.0, (104, 154, 66))])
    # soft clumps: warped blobs, top-lit (light from the top of the image) by a vertical difference
    cu, cv = tl.warp(u, v, 6, rng, 0.03)
    clump = tl.fbm(cu, cv, 7, rng, 3)
    blob = tl.smoothstep(0.47, 0.6, clump)
    lit = blob - np.roll(blob, 7, axis=0)           # >0 on the upper rim of a clump, <0 under it
    img = tl.shade(img, 0.9 + 0.12 * blob + 0.16 * lit)
    # dry yellowish and cool bluish clumps for colour variation
    hue = tl.fbm(u, v, 5, rng, 3)
    img = tl.mix(img, tl.rgb((122, 150, 66)), tl.smoothstep(0.62, 0.72, hue) * 0.35)
    img = tl.mix(img, tl.rgb((54, 104, 64)), tl.smoothstep(0.38, 0.28, hue) * 0.3)
    fine = tl.fbm(u, v, 40, rng, 2)
    img = tl.shade(img, 0.97 + fine * 0.06)
    height = blob * 0.5 + clump * 0.3 + fine * 0.1
    # blade suggestions: sparse tapered strokes, lighter on clump tops, a few dark ones
    n = int(1500 * (size / 1024) ** 2)
    for _ in range(n):
        cx, cy = rng.random(2) * size
        iy, ix = int(cy) % size, int(cx) % size
        base = img[iy, ix].copy()
        r = rng.random()
        on_top = blob[iy, ix]
        if r < 0.75 * on_top:
            col = np.clip(base * 1.2 + np.array([0.04, 0.05, 0.0]), 0, 1)
        elif r > 0.9 and on_top < 0.3:
            col = base * 0.86
        else:
            continue
        L = size * (0.014 + 0.014 * rng.random())
        W = size * 0.0022 * (0.8 + 0.5 * rng.random())
        ang = (rng.random() - 0.5) * 0.7
        tl.stamp(img, height, cx, cy, L, _blade(col, L, W, ang, height[iy, ix]))
    return img, height, 18.0


def gen_asphalt(u, v, rng):
    big = tl.fbm(u, v, 3, rng, 5)
    t = tl.soft_posterize(big, 3, 0.35)
    img = tl.ramp(t, [(0.0, (78, 79, 82)), (0.5, (92, 93, 95)), (1.0, (108, 108, 108))])
    # worn lighter areas (faded binder)
    worn = tl.smoothstep(0.55, 0.7, tl.fbm(u, v, 4, rng, 4))
    img = tl.mix(img, tl.rgb((124, 122, 118)), worn * 0.45)
    # aggregate speckles
    a1 = tl.value_noise(u, v, 300, rng)
    a2 = tl.value_noise(u, v, 220, rng)
    img = tl.mix(img, tl.rgb((150, 148, 142)), tl.smoothstep(0.82, 0.9, a1) * 0.6)
    img = tl.mix(img, tl.rgb((50, 50, 52)), tl.smoothstep(0.84, 0.92, a2) * 0.5)
    # repair patches: a few wrap-aware rectangles of darker, smoother asphalt
    patch = np.zeros_like(u)
    for _ in range(2):
        cx, cy = rng.random(2)
        hw, hh = 0.05 + 0.08 * rng.random(), 0.04 + 0.06 * rng.random()
        jag = (tl.fbm(u, v, 24, rng, 2) - 0.5) * 0.012
        dx = np.abs(tl.wrap_dist(u, cx)) + jag
        dy = np.abs(tl.wrap_dist(v, cy)) + jag
        m = (1 - tl.smoothstep(hw - 0.002, hw + 0.002, dx)) * (1 - tl.smoothstep(hh - 0.002, hh + 0.002, dy))
        patch = np.maximum(patch, m)
    img = tl.mix(img, tl.rgb((72, 73, 76)), patch * 0.5)
    seam = np.clip(tl.blur_wrap(patch, 2, 1) - patch, 0, 1) + np.clip(patch - tl.blur_wrap(patch, 2, 1), 0, 1)
    img = tl.mix(img, tl.rgb((50, 50, 52)), np.clip(seam * 3, 0, 1) * 0.45)
    # cracks: warped cell edges, only where a low-frequency mask allows
    cu, cv = tl.warp(u, v, 6, rng, 0.03)
    c = tl.voronoi(cu, cv, 5, rng)
    crack_line = 1.0 - tl.smoothstep(0.0, 0.035, c['f2'] - c['f1'])
    cmask = tl.smoothstep(0.5, 0.6, tl.fbm(u, v, 3, rng, 3)) * (1 - patch)
    crack = crack_line * cmask
    img = tl.mix(img, tl.rgb((34, 34, 36)), crack * 0.85)
    halo = np.clip(tl.blur_wrap(crack, 3, 1) - crack, 0, 1)
    img = tl.shade(img, 1.0 - halo * 0.25)
    height = big * 0.3 + tl.smoothstep(0.82, 0.9, a1) * 0.3 - tl.smoothstep(0.84, 0.92, a2) * 0.2 - crack * 0.8 \
        + patch * 0.15 - worn * 0.05
    return img, height, 16.0


def gen_concrete(u, v, rng):
    big = tl.fbm(u, v, 2, rng, 5)
    t = tl.soft_posterize(big, 3, 0.35)
    img = tl.ramp(t, [(0.0, (146, 142, 132)), (0.5, (160, 156, 146)), (1.0, (172, 168, 158))])
    mott = tl.fbm(u, v, 12, rng, 3)
    img = tl.shade(img, 0.95 + mott * 0.1)
    # formwork: faint horizontal board lines every 1/6 tile, per-board tone
    nb = 6
    wob = (tl.fbm(u, v, (4, 1), rng, 2) - 0.5) * 0.01
    s = (v + wob) * nb + 0.5                       # board joints sit between, not on, the tile seam
    board = np.floor(s).astype(np.int64) % nb
    btone = rng.random(nb)[board]
    img = tl.shade(img, 0.975 + btone * 0.05)
    fr = s - np.floor(s)
    line = 1.0 - tl.smoothstep(0.0, 0.012, np.minimum(fr, 1 - fr))
    img = tl.shade(img, 1.0 - line * 0.1)
    # vertical rain stains: streaks (high x freq, low y freq) gated by a mask, plus darker blotches
    streak = tl.fbm(u, v, (22, 2), rng, 3)
    smask = tl.smoothstep(0.45, 0.7, tl.fbm(u, v, (3, 2), rng, 3))
    stain = tl.smoothstep(0.55, 0.75, streak) * smask
    img = tl.mix(img, tl.rgb((128, 122, 108)), stain * 0.45)
    blot = tl.smoothstep(0.62, 0.72, tl.fbm(*tl.warp(u, v, 3, rng, 0.05), 4, rng, 4))
    img = tl.mix(img, tl.rgb((136, 132, 120)), blot * 0.4)
    # pores / air bubbles
    c = tl.voronoi(u, v, 64, rng, 0.9)
    present, rad = tl.cell_random(c['id'], c['n'], rng, 2)
    pore = (1 - tl.smoothstep(0.08 + 0.1 * rad, 0.14 + 0.12 * rad, c['f1'])) * (present < 0.35)
    img = tl.mix(img, tl.rgb((98, 96, 90)), pore * 0.7)
    height = big * 0.3 + mott * 0.15 - line * 0.25 - pore * 0.6 + btone * 0.05
    return img, height, 8.0


def gen_bark(u, v, rng):
    uw, vw = tl.warp(u, v, (4, 2), rng, 0.03)
    c = tl.voronoi(uw, vw, (9, 3), rng, 0.85)            # cells 9 across, 3 tall -> plates stretched vertically
    gap = c['f2'] - c['f1']
    fissure = 1.0 - tl.smoothstep(0.0, 0.16, gap)
    plate = tl.smoothstep(0.05, 0.45, gap)
    tone = tl.cell_random(c['id'], c['n'], rng)
    stri = tl.fbm(uw, vw, (48, 4), rng, 3)                  # fine vertical striations
    t = np.clip(0.35 + 0.3 * tone + 0.35 * (stri - 0.5) * 2 * 0.5, 0, 1)
    img = tl.ramp(t, [(0.0, (88, 66, 48)), (0.5, (106, 82, 62)), (1.0, (124, 100, 78))])
    img = tl.shade(img, 0.85 + 0.2 * plate)
    img = tl.mix(img, tl.rgb((50, 38, 30)), fissure * 0.85)
    # greyish weathering on plate tops
    weather = tl.smoothstep(0.55, 0.7, tl.fbm(u, v, (6, 3), rng, 3)) * plate
    img = tl.mix(img, tl.rgb((130, 120, 106)), weather * 0.3)
    height = plate * 1.0 - fissure * 0.6 + (stri - 0.5) * 0.35 + tone * 0.15
    return img, height, 22.0


def gen_birch(u, v, rng):
    big = tl.fbm(u, v, (2, 4), rng, 4)
    img = tl.ramp(tl.soft_posterize(big, 3, 0.35), [
        (0.0, (210, 204, 190)), (0.5, (226, 222, 212)), (1.0, (236, 233, 224))])
    # faint horizontal paper bands
    band = tl.fbm(u, v, (2, 40), rng, 2)
    img = tl.shade(img, 0.97 + band * 0.05)
    # lenticels: thin horizontal dashes in a stretched cell grid (6 wide, 26 tall)
    lu, lv = tl.warp(u, v, (3, 6), rng, 0.01)
    c = tl.voronoi(lu, lv, (6, 26), rng, 0.8)
    present, w, h = tl.cell_random(c['id'], c['n'], rng, 3)
    hw = 0.18 + 0.32 * w
    hh = 0.08 + 0.08 * h
    dash = (1 - tl.smoothstep(hw * 0.85, hw, np.abs(c['dx']))) * (1 - tl.smoothstep(hh * 0.7, hh, np.abs(c['dy'])))
    dash *= (present < 0.6)
    img = tl.mix(img, tl.rgb((52, 48, 46)), dash * 0.85)
    # larger black marks: horizontal blotches (low x freq, higher y freq), warped
    mu, mv = tl.warp(u, v, 3, rng, 0.04)
    marks_f = tl.fbm(mu, mv, (3, 8), rng, 4)
    marks = tl.smoothstep(0.7, 0.74, marks_f)
    img = tl.mix(img, tl.rgb((44, 42, 40)), marks * 0.92)
    rim = np.clip(tl.smoothstep(0.64, 0.7, marks_f) - marks, 0, 1)
    img = tl.mix(img, tl.rgb((150, 142, 130)), rim * 0.35)
    # small grey-warm smudges
    smudge = tl.smoothstep(0.6, 0.72, tl.fbm(u, v, 6, rng, 3))
    img = tl.mix(img, tl.rgb((196, 186, 168)), smudge * 0.35)
    height = big * 0.2 + band * 0.1 - dash * 0.4 - marks * 0.5 - rim * 0.1
    return img, height, 12.0


def gen_leaves(u, v, rng, size):
    """Overlapping stylised leaves stamped with wrap-around (painter's order)."""
    img = tl.ramp(tl.fbm(u, v, 3, rng, 3), [(0.0, (30, 66, 40)), (1.0, (44, 88, 50))])
    height = np.zeros((size, size))
    cols = [P['leaf'], P['leaf_dark'], (74, 130, 60), (104, 160, 70), (66, 120, 58), (84, 140, 62)]
    n = 900
    L = size * 0.055
    for i in range(n):
        layer = i / n
        cx, cy = rng.random(2) * size
        ang = rng.random() * 2 * np.pi
        ln = L * (0.75 + 0.5 * rng.random())
        wd = ln * (0.36 + 0.12 * rng.random())
        base = np.array(cols[rng.integers(len(cols))], dtype=np.float64) / 255.0
        base = base * (0.8 + 0.3 * layer + 0.08 * (rng.random() - 0.5))   # later (upper) leaves are lighter
        r = int(np.ceil(ln)) + 2
        ys = np.arange(int(cy) - r, int(cy) + r + 1)
        xs = np.arange(int(cx) - r, int(cx) + r + 1)
        X, Y = np.meshgrid(xs + 0.5 - cx, ys + 0.5 - cy)
        ca, sa = np.cos(ang), np.sin(ang)
        a = X * ca + Y * sa                         # along the leaf, 0 = stem end
        b = -X * sa + Y * ca
        s = a / ln                                  # 0..1 along leaf (stem at 0, tip at 1)
        prof = np.sin(np.clip(s, 0, 1) * np.pi) ** 0.8 * wd   # almond outline
        inside = (s > 0) & (s < 1) & (np.abs(b) < prof)
        if not inside.any():
            continue
        rows, cols_ = ys % size, xs % size
        ix = np.ix_(rows, cols_)
        sub = img[ix]
        hsub = height[ix]
        bn = np.abs(b) / np.maximum(prof, 1e-6)
        side = np.where(b > 0, 1.04, 0.92)          # one half lit, one half in shade
        rib = 1.0 + 0.12 * (1 - tl.smoothstep(0.0, 0.12, bn)) * (s < 0.9)
        edge = 1.0 - 0.18 * tl.smoothstep(0.7, 1.0, bn)
        tipfade = 0.9 + 0.1 * s
        colr = base[None, None, :] * (side * rib * edge * tipfade)[..., None]
        sub[inside] = colr[inside]
        dome = np.sqrt(np.clip(1 - bn ** 2, 0, 1)) * 0.6 + layer * 0.8
        hsub[inside] = dome[inside]
        img[ix] = sub
        height[ix] = hsub
    return img, height, 24.0


TEXTURES = {
    # name: (generator, metres_per_tile)
    'SeaWater': (gen_sea, 8.0),
    'Sand': (gen_sand, 4.0),
    'Ground': (gen_ground, 3.0),
    'Dirt': (gen_dirt, 4.0),
    'Grass': (gen_grass, 3.0),
    'Asphalt': (gen_asphalt, 4.0),
    'Concrete': (gen_concrete, 3.0),
    'Bark': (gen_bark, 1.0),
    'BirchBark': (gen_birch, 1.0),
    'Leaves': (gen_leaves, 1.5),
}


# ======================================================================== outputs
def tiled_preview(albedo_u8, px=512):
    half = Image.fromarray(albedo_u8).resize((px // 2, px // 2), Image.LANCZOS)
    out = Image.new('RGB', (px, px))
    for oy in (0, px // 2):
        for ox in (0, px // 2):
            out.paste(half, (ox, oy))
    return out


def contact_sheet(entries, path, cell=256):
    cols = 5
    rows = (len(entries) + cols - 1) // cols
    label_h = 18
    sheet = Image.new('RGB', (cols * cell, rows * (2 * cell + label_h)), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    for i, (name, alb, nrm) in enumerate(entries):
        x = (i % cols) * cell
        y = (i // cols) * (2 * cell + label_h)
        sheet.paste(tiled_preview(alb, cell), (x, y + label_h))
        sheet.paste(tiled_preview(tl.lit_preview(alb, nrm), cell), (x, y + label_h + cell))
        draw.text((x + 4, y + 3), f'{name}  (top: albedo 2x2, bottom: lit by normal)', fill=(230, 230, 230))
    sheet.save(path, format='PNG')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--only', default='', help='comma separated texture names')
    ap.add_argument('--out', default=str(HERE / 'Out'), help='parent output dir (revision folder is created inside)')
    ap.add_argument('--revision', type=int, default=1)
    ap.add_argument('--force', action='store_true', help='overwrite an existing revision folder')
    args = ap.parse_args()

    names = list(TEXTURES)
    if args.only:
        want = [n.strip() for n in args.only.split(',') if n.strip()]
        bad = [n for n in want if n not in TEXTURES]
        if bad:
            ap.error(f'unknown texture(s): {bad}; known: {names}')
        names = want

    rev = f'v{args.revision:02d}'
    out = Path(args.out) / rev
    if out.exists():
        if not args.force:
            sys.exit(f'{out} already exists; pass --force to overwrite or use another --revision')
        shutil.rmtree(out)
    (out / 'Previews').mkdir(parents=True)

    size = args.size
    u, v = tl.uv_grid(size)
    meta = {'revision': rev, 'size': size, 'seed': args.seed, 'generator': 'gen_textures.py',
            'normal_convention': 'OpenGL (+Y up, Unity)', 'textures': []}
    sheet = []
    t_all = time.time()
    for name in names:
        t0 = time.time()
        fn, mpt = TEXTURES[name]
        rng = tl.rng_for(args.seed, name)
        if name in ('Leaves', 'Grass'):
            alb, h, strength = fn(u, v, rng, size)
        else:
            alb, h, strength = fn(u, v, rng)
        alb8 = tl.to_u8(alb)
        nrm8 = tl.normal_from_height(tl.normalize(h), strength)
        fa = f'TX_{name}_Albedo_{rev}.png'
        fnrm = f'TX_{name}_Normal_{rev}.png'
        tl.save_png(alb8, out / fa)
        tl.save_png(nrm8, out / fnrm)
        tiled_preview(alb8).save(out / 'Previews' / f'{name}_preview.png', format='PNG')
        seam_a = tl.seam_check(alb8)
        seam_n = tl.seam_check(nrm8)
        meta['textures'].append({
            'name': name,
            'files': {'albedo': fa, 'normal': fnrm, 'preview': f'Previews/{name}_preview.png'},
            'size': [size, size],
            'seed': args.seed,
            'metres_per_tile': mpt,
            'mean_rgb': [round(float(x), 1) for x in alb8.reshape(-1, 3).mean(axis=0)],
            'seam_check': {'albedo': seam_a, 'normal': seam_n},
            'tileable_ok': bool(seam_a['tileable_ok'] and seam_n['tileable_ok']),
        })
        sheet.append((name, alb8, nrm8))
        print(f'{name:10s} {time.time() - t0:5.1f}s  tileable_ok={meta["textures"][-1]["tileable_ok"]}  '
              f'mean={meta["textures"][-1]["mean_rgb"]}')
    contact_sheet(sheet, out / 'Previews' / 'contact_sheet.png')
    with open(out / f'textures_{rev}.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f'done in {time.time() - t_all:.1f}s -> {out}')


if __name__ == '__main__':
    main()
