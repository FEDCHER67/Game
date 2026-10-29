"""Workshop_rollerdoor_v01.png - tileable greyscale roller-door slats for tinting (red #B23A2C / grey).

512 x 512 px = 0.64 x 0.64 m tile (Unity tiling 1.5625 with UVs in metres), 8 horizontal slats of 8 cm (64 px).
The groove sits on the slat boundary (image rows 0, 64, 128, ...), matching the geometric lamellae of the
Workshop_W86 curtains (UV v = z - 0.10 m, grooves every 0.08 m). Run: python make_rollerdoor_tex_v01.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / 'Workshop_rollerdoor_v01.png'
if OUT.exists() and '--force' not in sys.argv:
    sys.exit(f'{OUT} exists; numbered revisions are never overwritten')

N = 512
SLAT = 64
rng = np.random.default_rng(86)
y = np.arange(N)[:, None].astype(float)
x = np.arange(N)[None, :].astype(float)
t = (y % SLAT) / SLAT  # 0 at the top edge of a slat (groove), 1 at its bottom

# slat profile: groove (dark) - highlight ridge - face with soft vertical gradient - shadow lip
prof = np.where(t < 0.05, 92.0,
       np.where(t < 0.11, 226.0,
       np.where(t < 0.92, 212.0 - 36.0 * (t - 0.11) / 0.81,
                160.0 - 40.0 * (t - 0.92) / 0.08)))
img = np.broadcast_to(prof, (N, N)).copy()

# tileable low-frequency streaks (integer periods across the tile)
for k, amp in ((1, 3.0), (2, 2.5), (3, 2.0), (5, 1.5), (9, 1.0)):
    ph = rng.uniform(0, 2 * math.pi)
    img += amp * np.sin(2 * math.pi * k * x / N + ph)
# faint vertical wear (rain/dirt streaks), tileable
for k, amp in ((7, 2.0), (13, 1.5), (23, 1.0)):
    ph = rng.uniform(0, 2 * math.pi)
    img += amp * np.sin(2 * math.pi * k * x / N + ph) * (0.6 + 0.4 * np.sin(2 * math.pi * y / N + ph))
# per-slat brightness jitter (8 slats -> tile-safe)
jit = rng.uniform(-5, 5, size=N // SLAT)
img += jit[(np.arange(N) // SLAT)][:, None]
# fine grain
img += rng.normal(0, 2.2, size=(N, N))

img = np.clip(img, 0, 255).astype(np.uint8)
Image.fromarray(img, mode='L').save(OUT)
print('saved', OUT, img.shape, int(img.min()), int(img.max()), round(float(img.mean()), 1))
