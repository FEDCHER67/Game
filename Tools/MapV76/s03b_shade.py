"""Hillshade preview of the 1 m heightmap (sea blue), for a quick visual check next to the 2D map."""
import os
import numpy as np
from PIL import Image
from common import WORK, MAP_PREVIEW

h = np.load(os.path.join(WORK, 'height_1m.npy'))
gy, gx = np.gradient(h)
n = np.dstack([-gx, -gy, np.ones_like(h)])
n /= np.linalg.norm(n, axis=2, keepdims=True)
l = np.array([-0.5, 0.5, 0.7]); l /= np.linalg.norm(l)
sh = np.clip(n @ l, 0, 1)
base = np.dstack([0.55 + 0.004 * h, 0.62 + 0.002 * h, 0.45 + 0.004 * h])
img = base * (0.35 + 0.75 * sh[..., None])
img[h < 0] = np.array([0.45, 0.7, 0.85]) * (1 + h[h < 0, None] / 30)
img = (np.clip(img, 0, 1)[::-1] * 255).astype(np.uint8)
Image.fromarray(img).save(os.path.join(WORK, 'relief_shaded_v76.png'))
m = Image.open(MAP_PREVIEW).convert('RGB')
both = Image.new('RGB', (1744, 1900)); both.paste(m, (0, 0)); both.paste(Image.fromarray(img), (0, 950))
both.resize((872, 950)).save(os.path.join(WORK, 'relief_vs_map_v76.png'))
