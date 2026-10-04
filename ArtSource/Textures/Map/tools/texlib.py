"""Shared helpers for the VOLUNTEERS ONLY map texture generators.

numpy + Pillow only. Every array is float32 in 0..1, shape (H, W) or (H, W, C).
All filters wrap around the borders (FFT / np.roll), so anything built from these
helpers tiles seamlessly as long as periodic structures divide the tile size.
"""
import os
import zlib
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- randomness

def rng_for(name, salt=0):
    """Deterministic generator per texture name (independent of run order)."""
    return np.random.default_rng(zlib.crc32(f"{name}:{salt}".encode("utf-8")))


# ---------------------------------------------------------------- colour

def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def lerp(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2 and np.ndim(a) in (1, 3) or (t.ndim == 2 and np.ndim(b) in (1, 3)):
        t = t[..., None]
    return a + (b - a) * t


def fill(shape, color):
    return np.broadcast_to(np.asarray(color, np.float32), (*shape, 3)).copy()


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- noise

def value_noise(shape, freq, rng):
    """Periodic smooth value noise. freq = lattice cells across the width (int)."""
    h, w = shape
    fx = max(1, int(round(freq[0] if isinstance(freq, tuple) else freq)))
    fy = max(1, int(round(freq[1] if isinstance(freq, tuple) else freq * h / w)))
    grid = rng.random((fy, fx)).astype(np.float32)
    y = np.arange(h, dtype=np.float32) * fy / h
    x = np.arange(w, dtype=np.float32) * fx / w
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    ty = y - y0
    tx = x - x0
    ty = ty * ty * ty * (ty * (ty * 6 - 15) + 10)
    tx = tx * tx * tx * (tx * (tx * 6 - 15) + 10)
    y1 = (y0 + 1) % fy
    x1 = (x0 + 1) % fx
    y0 %= fy
    x0 %= fx
    a = grid[np.ix_(y0, x0)]
    b = grid[np.ix_(y0, x1)]
    c = grid[np.ix_(y1, x0)]
    d = grid[np.ix_(y1, x1)]
    tx = tx[None, :]
    ty = ty[:, None]
    return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty


def fbm(shape, freq, rng, octaves=4, gain=0.5, lacunarity=2):
    """Fractal sum of periodic value noise, normalised to 0..1.
    freq may be an int or an (fx, fy) tuple for stretched noise."""
    total = np.zeros(shape, np.float32)
    amp, norm = 1.0, 0.0
    fx, fy = freq if isinstance(freq, tuple) else (freq, max(1, round(freq * shape[0] / shape[1])))
    for _ in range(octaves):
        total += amp * value_noise(shape, (fx, fy), rng)
        norm += amp
        amp *= gain
        fx *= lacunarity
        fy *= lacunarity
    total /= norm
    lo, hi = np.percentile(total, 0.5), np.percentile(total, 99.5)
    return np.clip((total - lo) / (hi - lo + 1e-9), 0, 1).astype(np.float32)


def blur(a, sigma):
    """Periodic gaussian blur (FFT). Works on (H, W) and (H, W, C)."""
    if sigma <= 0:
        return a
    h, w = a.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (kx ** 2 + ky ** 2)).astype(np.float32)
    if a.ndim == 3:
        g = g[..., None]
    out = np.fft.irfft2(np.fft.rfft2(a, axes=(0, 1)) * g, s=(h, w), axes=(0, 1))
    return out.astype(np.float32)


def warp(a, dx, dy):
    """Periodic domain warp by pixel offsets dx, dy (nearest sample)."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    sy = (yy + np.round(dy).astype(int)) % h
    sx = (xx + np.round(dx).astype(int)) % w
    return a[sy, sx]


def voronoi(shape, cells, rng, jitter=0.9):
    """Periodic Worley noise on a cells x cells' jittered grid.
    Returns (f1, f2, cell_id) with distances in pixels."""
    h, w = shape
    cx = cells
    cy = max(1, round(cells * h / w))
    sx, sy = w / cx, h / cy
    pts = (rng.random((cy, cx, 2)) - 0.5) * jitter + 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gx = np.floor(xx / sx).astype(int)
    gy = np.floor(yy / sy).astype(int)
    f1 = np.full(shape, 1e9, np.float32)
    f2 = np.full(shape, 1e9, np.float32)
    cid = np.zeros(shape, np.int32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            nx, ny = gx + ox, gy + oy
            p = pts[ny % cy, nx % cx]
            px = (nx + p[..., 0]) * sx
            py = (ny + p[..., 1]) * sy
            d = np.hypot(xx - px, yy - py)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, (ny % cy) * cx + (nx % cx), cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


def cell_table(rng, shape):
    return rng.random(shape).astype(np.float32)


# ---------------------------------------------------------------- shapes

def box(x, x0, x1, soft=1.0):
    """Soft 1-D box mask, x0 <= x < x1."""
    return np.clip((x - x0) / soft + 0.5, 0, 1) * np.clip((x1 - x) / soft + 0.5, 0, 1)


def rect(xx, yy, x0, y0, x1, y1, soft=1.0):
    return box(xx, x0, x1, soft) * box(yy, y0, y1, soft)


def grid_coords(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


# ---------------------------------------------------------------- surface

class Surface:
    """Layered PBR canvas: albedo, height, roughness, metallic, emission, alpha."""

    def __init__(self, shape, color=(0.5, 0.5, 0.5), rough=0.8, height=0.5):
        self.shape = shape
        self.albedo = fill(shape, color)
        self.height = np.full(shape, height, np.float32)
        self.rough = np.full(shape, rough, np.float32)
        self.metal = np.zeros(shape, np.float32)
        self.emission = None
        self.alpha = None

    def lay(self, mask, color=None, rough=None, height=None, metal=None, add_height=None,
            emission=None):
        m = np.clip(mask, 0, 1).astype(np.float32)
        if color is not None:
            self.albedo = lerp(self.albedo, np.asarray(color, np.float32), m)
        if rough is not None:
            self.rough = lerp(self.rough, np.asarray(rough, np.float32), m)
        if height is not None:
            self.height = lerp(self.height, np.asarray(height, np.float32), m)
        if add_height is not None:
            self.height = self.height + m * np.asarray(add_height, np.float32)
        if metal is not None:
            self.metal = lerp(self.metal, np.asarray(metal, np.float32), m)
        if emission is not None:
            if self.emission is None:
                self.emission = np.zeros((*self.shape, 3), np.float32)
            self.emission = lerp(self.emission, np.asarray(emission, np.float32), m)

    def tint(self, factor):
        """Multiply albedo by a (H, W) or scalar factor."""
        f = np.asarray(factor, np.float32)
        self.albedo = self.albedo * (f[..., None] if f.ndim == 2 else f)


def normal_from_height(height, strength):
    """OpenGL-style (+Y up, Unity convention) tangent-space normal map."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, dy, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def cavity_ao(height, radius, amount):
    """Cheap painted ambient occlusion from height: dark where below local mean."""
    diff = blur(height, radius) - height
    return np.clip(1.0 - np.maximum(diff, 0) * amount, 0.0, 1.0)


# ---------------------------------------------------------------- IO

def to8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def save(path, arr):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = to8(arr)
    mode = {2: "L"}.get(a.ndim, None) or {3: "RGB", 4: "RGBA"}[a.shape[2]]
    Image.fromarray(a, mode).save(path, compress_level=6)


def write_surface(out_dir, name, s, normal_strength, ao_radius=6.0, ao_amount=4.0):
    """Write albedo, normal, roughness, URP mask (+emission) and return the file map."""
    files = {}
    ao = cavity_ao(s.height, ao_radius, ao_amount)
    alb = s.albedo * (0.55 + 0.45 * ao)[..., None]
    if s.alpha is not None:
        alb = np.concatenate([alb, s.alpha[..., None]], -1)
    files["albedo"] = f"{name}_albedo.png"
    save(os.path.join(out_dir, files["albedo"]), alb)
    files["normal"] = f"{name}_normal.png"
    save(os.path.join(out_dir, files["normal"]), normal_from_height(s.height, normal_strength))
    files["roughness"] = f"{name}_roughness.png"
    save(os.path.join(out_dir, files["roughness"]), s.rough)
    # URP Lit "Metallic Map": R = metallic, G = occlusion (HDRP-style, harmless), A = smoothness.
    mask = np.stack([s.metal, ao, np.zeros_like(ao), 1.0 - s.rough], -1)
    files["mask_urp"] = f"{name}_mask.png"
    save(os.path.join(out_dir, files["mask_urp"]), mask)
    if s.emission is not None:
        files["emission"] = f"{name}_emission.png"
        save(os.path.join(out_dir, files["emission"]), s.emission)
    return files


# ---------------------------------------------------------------- fonts

FONT_CSS = ("https://fonts.googleapis.com/css2?family=Rubik:wght@500;800"
            "&family=PT+Sans+Narrow:wght@700&subset=cyrillic")
FALLBACK = {
    "display": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "narrow": ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "label": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def ensure_fonts(cache_dir, offline=False):
    """Download OFL fonts (Rubik, PT Sans Narrow) once; fall back to DejaVu.
    Returns {"display": path, "narrow": path, "label": path, "source": str}."""
    want = {"display": "Rubik-ExtraBold.ttf", "narrow": "PTSansNarrow-Bold.ttf",
            "label": "Rubik-Medium.ttf"}
    os.makedirs(cache_dir, exist_ok=True)
    have = {k: os.path.join(cache_dir, v) for k, v in want.items()}
    if not offline and not all(os.path.exists(p) for p in have.values()):
        try:
            req = urllib.request.Request(FONT_CSS, headers={"User-Agent": "Mozilla/4.0"})
            css = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
            urls = {}
            for block in css.split("@font-face")[1:]:
                fam = block.split("font-family: '")[1].split("'")[0]
                wght = block.split("font-weight: ")[1].split(";")[0].strip()
                url = block.split("url(")[1].split(")")[0]
                urls[(fam, wght)] = url
            mapping = {"display": ("Rubik", "800"), "label": ("Rubik", "500"),
                       "narrow": ("PT Sans Narrow", "700")}
            for k, key in mapping.items():
                if not os.path.exists(have[k]) and key in urls:
                    with urllib.request.urlopen(urls[key], timeout=30) as r, open(have[k], "wb") as f:
                        f.write(r.read())
        except Exception as e:  # network blocked: use DejaVu
            print(f"[fonts] download failed ({e.__class__.__name__}); using DejaVu fallback")
    out, source = {}, []
    for k in want:
        if os.path.exists(have[k]):
            out[k] = have[k]
            source.append(os.path.basename(have[k]))
        else:
            out[k] = next((p for p in FALLBACK[k] if os.path.exists(p)), None)
            source.append(os.path.basename(out[k]) if out[k] else "PIL default")
    out["source"] = ", ".join(source)
    return out


def load_font(path, size):
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_mask(shape, text, font_path, box_xywh, max_size, align="center"):
    """Render text fitted into a box; returns float mask (H, W)."""
    h, w = shape
    bx, by, bw, bh = box_xywh
    size = max_size
    while size > 8:
        font = load_font(font_path, size)
        l, t, r, b = font.getbbox(text)
        if r - l <= bw and b - t <= bh:
            break
        size -= 2
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    l, t, r, b = font.getbbox(text)
    x = bx + (bw - (r - l)) / 2 - l if align == "center" else bx - l
    y = by + (bh - (b - t)) / 2 - t
    d.text((x, y), text, fill=255, font=font)
    return np.asarray(img, np.float32) / 255.0
