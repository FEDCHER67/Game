"""Tileable procedural texture helpers (numpy + Pillow only).

Coordinates: every sampler takes arrays u, v in *tile units* (0..1 covers the texture once). All noise lattices are
periodic with an integer number of cells per tile, so sampling at u and u+1 gives exactly the same value: textures
wrap without seams. Anything built only from these samplers (plus np.roll-based filters) stays tileable.

Image convention: arrays are indexed [row, col] = [y, x]; row 0 is the top of the PNG. v grows downwards.
"""
import zlib
from pathlib import Path

import numpy as np
from PIL import Image


# ---------------------------------------------------------------- seeding / grids
def rng_for(seed, *names):
    """Stable per-texture RNG (crc32, not Python's randomised hash)."""
    key = '/'.join(str(n) for n in names).encode()
    return np.random.default_rng([int(seed) & 0xFFFFFFFF, zlib.crc32(key)])


def uv_grid(size):
    """Pixel-centre coordinates in tile units, shape (size, size)."""
    t = (np.arange(size, dtype=np.float64) + 0.5) / size
    u, v = np.meshgrid(t, t)          # u varies along columns (x), v along rows (y)
    return u, v


def _periods(period):
    return (int(period), int(period)) if np.isscalar(period) else (int(period[0]), int(period[1]))


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


# ---------------------------------------------------------------- periodic value / gradient noise
def value_noise(u, v, period, rng):
    """Periodic value noise in [0,1]. period = int or (px, py) lattice cells per tile."""
    px, py = _periods(period)
    lat = rng.random((py, px))
    x = u * px
    y = v * py
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = _fade(x - x0)
    fy = _fade(y - y0)
    xi = x0.astype(np.int64) % px
    yi = y0.astype(np.int64) % py
    xj = (xi + 1) % px
    yj = (yi + 1) % py
    a = lat[yi, xi] + (lat[yi, xj] - lat[yi, xi]) * fx
    b = lat[yj, xi] + (lat[yj, xj] - lat[yj, xi]) * fx
    return a + (b - a) * fy


def gradient_noise(u, v, period, rng):
    """Periodic Perlin-style gradient noise, roughly in [0,1] (0.5 mean)."""
    px, py = _periods(period)
    ang = rng.random((py, px)) * 2 * np.pi
    gx, gy = np.cos(ang), np.sin(ang)
    x = u * px
    y = v * py
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = x - x0
    fy = y - y0
    xi = x0.astype(np.int64) % px
    yi = y0.astype(np.int64) % py
    xj = (xi + 1) % px
    yj = (yi + 1) % py

    def dot(iy, ix, dx, dy):
        return gx[iy, ix] * dx + gy[iy, ix] * dy

    n00 = dot(yi, xi, fx, fy)
    n10 = dot(yi, xj, fx - 1, fy)
    n01 = dot(yj, xi, fx, fy - 1)
    n11 = dot(yj, xj, fx - 1, fy - 1)
    sx, sy = _fade(fx), _fade(fy)
    a = n00 + (n10 - n00) * sx
    b = n01 + (n11 - n01) * sx
    return np.clip((a + (b - a) * sy) * 0.75 + 0.5, 0.0, 1.0)


def fbm(u, v, period, rng, octaves=5, gain=0.5, lacunarity=2, kind='gradient'):
    """Fractal sum of periodic noise, normalised to [0,1]. lacunarity must be an integer to keep tiling."""
    px, py = _periods(period)
    fn = gradient_noise if kind == 'gradient' else value_noise
    total = np.zeros_like(u)
    amp, norm = 1.0, 0.0
    for _ in range(octaves):
        total += amp * fn(u, v, (px, py), rng)
        norm += amp
        amp *= gain
        px *= int(lacunarity)
        py *= int(lacunarity)
    return total / norm


def warp(u, v, period, rng, amount, octaves=3):
    """Domain warp: returns (u', v') displaced by a periodic fBm field (amount in tile units)."""
    du = fbm(u, v, period, rng, octaves) - 0.5
    dv = fbm(u, v, period, rng, octaves) - 0.5
    return u + du * 2 * amount, v + dv * 2 * amount


# ---------------------------------------------------------------- periodic Voronoi / cellular
def voronoi(u, v, cells, rng, jitter=1.0):
    """Periodic Worley noise with one feature point per cell.

    cells = int or (nx, ny). Distances are measured in cell units of the x axis scale per axis (i.e. in cell space),
    so with nx != ny cells are stretched. Returns dict: f1, f2 (distances), id (int cell id), cx, cy (feature point
    position in tile units, unwrapped near the pixel), dx, dy (pixel minus nearest feature, in cell units).
    """
    nx, ny = _periods(cells)
    pts = 0.5 + (rng.random((ny, nx, 2)) - 0.5) * jitter
    x = u * nx
    y = v * ny
    xc = np.floor(x).astype(np.int64)
    yc = np.floor(y).astype(np.int64)
    f1 = np.full(u.shape, np.inf)
    f2 = np.full(u.shape, np.inf)
    cid = np.zeros(u.shape, np.int64)
    bdx = np.zeros(u.shape)
    bdy = np.zeros(u.shape)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx = xc + ox
            cy = yc + oy
            wx = cx % nx
            wy = cy % ny
            p = pts[wy, wx]
            dx = x - (cx + p[..., 0])
            dy = y - (cy + p[..., 1])
            d = np.sqrt(dx * dx + dy * dy)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            f1 = np.where(closer, d, f1)
            cid = np.where(closer, wy * nx + wx, cid)
            bdx = np.where(closer, dx, bdx)
            bdy = np.where(closer, dy, bdy)
    return {'f1': f1, 'f2': f2, 'id': cid, 'dx': bdx, 'dy': bdy, 'n': nx * ny}


def cell_random(cid, n, rng, count=1):
    """Per-cell random values in [0,1) looked up by cell id; returns array (or tuple when count > 1)."""
    table = rng.random((count, n))
    out = tuple(table[i][cid] for i in range(count))
    return out[0] if count == 1 else out


# ---------------------------------------------------------------- shaping
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def soft_posterize(t, levels, softness=0.35):
    """Pull a 0..1 field towards `levels` flat bands with soft edges (painterly banding)."""
    s = t * levels
    base = np.floor(s)
    frac = s - base
    stepped = base + smoothstep(0.5 - softness, 0.5 + softness, frac)
    return np.clip(stepped / levels, 0.0, 1.0)


def normalize(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo + 1e-12)


def wrap_dist(a, c):
    """Signed shortest distance on a unit circle (tile units)."""
    return (a - c + 0.5) % 1.0 - 0.5


def blur_wrap(a, radius=1, passes=1):
    """Cheap wrap-around box blur (keeps tiling)."""
    out = a
    for _ in range(passes):
        acc = np.zeros_like(out)
        for s in range(-radius, radius + 1):
            acc += np.roll(out, s, axis=1)
        out = acc / (2 * radius + 1)
        acc = np.zeros_like(out)
        for s in range(-radius, radius + 1):
            acc += np.roll(out, s, axis=0)
        out = acc / (2 * radius + 1)
    return out


def stamp(img, height, cx, cy, radius, shape_fn):
    """Paint one shape centred at pixel (cx, cy) with wrap-around (painter's order).

    shape_fn(X, Y) gets pixel offsets from the centre (arrays) and returns (mask bool, rgb (h,w,3), height (h,w)).
    """
    size = img.shape[0]
    r = int(np.ceil(radius)) + 2
    ys = np.arange(int(cy) - r, int(cy) + r + 1)
    xs = np.arange(int(cx) - r, int(cx) + r + 1)
    X, Y = np.meshgrid(xs + 0.5 - cx, ys + 0.5 - cy)
    mask, col, h = shape_fn(X, Y)
    if not mask.any():
        return
    ix = np.ix_(ys % size, xs % size)
    sub = img[ix]
    hsub = height[ix]
    sub[mask] = col[mask]
    hsub[mask] = h[mask]
    img[ix] = sub
    height[ix] = hsub


# ---------------------------------------------------------------- colour
def rgb(c):
    return np.asarray(c, dtype=np.float64) / 255.0


def ramp(t, stops):
    """Map scalar field t (0..1) to RGB via [(pos, (r,g,b) 0-255), ...]. Returns (H, W, 3) float 0..1."""
    pos = np.array([s[0] for s in stops], dtype=np.float64)
    cols = np.array([s[1] for s in stops], dtype=np.float64) / 255.0
    t = np.clip(t, 0.0, 1.0)
    return np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], axis=-1)


def mix(a, b, t):
    """Lerp colours/images; t may be a scalar field (broadcast over RGB)."""
    t = np.asarray(t, dtype=np.float64)
    if t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


def shade(img, f):
    """Multiply brightness by scalar field f (around 1.0)."""
    return img * np.asarray(f)[..., None]


# ---------------------------------------------------------------- normals
def normal_from_height(h, strength=2.0):
    """OpenGL / Unity normal map (+Y up = green up) from a height field (any range, wrap-aware gradients).

    h should be normalised to 0..1. strength = slope multiplier: a full 0..1 height change spread over `strength`
    pixels (at 1024 px; scaled with size so the look is resolution independent) gives a 45 degree slope.
    Returns uint8 (H, W, 3).
    """
    size = h.shape[0]
    k = strength * size / 1024.0
    dhdx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * k
    dhdrow = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * k
    # image rows grow downwards; tangent-space +Y is up, so dh/dy = -dh/drow
    nx = -dhdx
    ny = dhdrow
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx * inv, ny * inv, nz * inv], axis=-1)
    return to_u8(n * 0.5 + 0.5)


def lit_preview(albedo_u8, normal_u8, light=(-0.45, 0.55, 0.7)):
    """Albedo lit by the normal map with a light from the upper left (tangent space, +Y up) - to judge normals."""
    n = normal_u8.astype(np.float64) / 255.0 * 2 - 1
    l = np.asarray(light, dtype=np.float64)
    l = l / np.linalg.norm(l)
    ndl = np.clip((n * l).sum(-1), 0, 1)
    f = 0.35 + 0.65 * ndl / l[2]                      # flat surface stays ~ albedo brightness
    return to_u8(albedo_u8.astype(np.float64) / 255.0 * f[..., None])


# ---------------------------------------------------------------- io / checks
def to_u8(img):
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def save_png(arr_u8, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr_u8, 'RGB').save(path, format='PNG', optimize=False, compress_level=6)


def seam_check(img_u8):
    """Compare the wrap seam with ordinary neighbouring-pixel differences, horizontally and vertically."""
    a = img_u8.astype(np.int32)
    res = {}
    for axis, label in ((1, 'columns'), (0, 'rows')):
        d = np.abs(np.diff(a, axis=axis)).max(axis=-1)                  # interior neighbour diffs (per pixel, max over RGB)
        first = np.take(a, 0, axis=axis)
        last = np.take(a, -1, axis=axis)
        s = np.abs(first - last).max(axis=-1)                            # across the wrap seam
        line_means = d.mean(axis=1 - axis)                               # mean diff of each interior column/row pair
        res[label] = {
            'seam_mean': round(float(s.mean()), 3),
            'seam_max': int(s.max()),
            'interior_mean': round(float(d.mean()), 3),
            'interior_line_mean_max': round(float(line_means.max()), 3),
            'interior_p99': float(np.percentile(d, 99)),
            'interior_max': int(d.max()),
        }
        r = res[label]
        # The seam line must look like any other neighbouring line: its mean difference within the range of the
        # interior line means (a busy row of an anisotropic texture can legitimately sit on the seam) and its
        # worst pixel no worse than the worst interior pixel.
        r['ok'] = bool(r['seam_mean'] <= max(1.5 * r['interior_mean'] + 1.0, r['interior_line_mean_max'])
                       and r['seam_max'] <= r['interior_max'])
    res['tileable_ok'] = bool(res['columns']['ok'] and res['rows']['ok'])
    return res
