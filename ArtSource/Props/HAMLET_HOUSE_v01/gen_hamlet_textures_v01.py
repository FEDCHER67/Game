"""Own painted textures for HAMLET_HOUSE_v01 (One-Armed Robber style: clean colour, soft volume, no photo grime).
python gen_hamlet_textures_v01.py  ->  Assets/OnlyVolunteers/Art/TextureTest_v01/Source_v02/
  TT_logs_v02_albedo.png            1024 px = 2.4 x 2.4 m, 10 log courses of 0.24 m (matches the 3D corner joints), natural wood
  TT_boards_vertical_v02_albedo.png 1024 px = 2.4 x 2.4 m, 16 vertical boards of 0.15 m, near-white base (paint colour = material)
Seamless in X and Y. Original work (no third-party source).
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parents[3] / 'Assets/OnlyVolunteers/Art/TextureTest_v01/Source_v02'
OUT.mkdir(parents=True, exist_ok=True)
N = 1024


def smooth_noise(seed, cells):
    """Tileable value noise, cells x cells grid, bicubic-upscaled."""
    r = random.Random(seed)
    small = Image.new('L', (cells, cells))
    small.putdata([int(r.random() * 255) for _ in range(cells * cells)])
    big = Image.new('L', (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(small, (i * cells, j * cells))
    big = big.resize((N * 3, N * 3), Image.BICUBIC)
    return big.crop((N, N, 2 * N, 2 * N))


def logs():
    r = random.Random(7)
    courses = 10
    h = N / courses
    grain = smooth_noise(11, 32).filter(ImageFilter.GaussianBlur(4))
    gx = grain.resize((N, N // 8)).resize((N, N))            # streaky along X
    tones = [(r.uniform(-.06, .06)) for _ in range(courses)]
    px = []
    g = gx.load()
    for y in range(N):
        k = int(y // h); t = (y - k * h) / h                      # 0 top .. 1 bottom of a log
        prof = math.sin(math.pi * t)                              # round log: light middle, dark seams
        shade = .62 + .38 * prof ** .6
        seam = 1.0
        if t < .06 or t > .94:
            seam = .7                                             # caulk line
        for x in range(N):
            gr = (g[x, y] / 255 - .5) * .07
            v = shade * seam * (1 + tones[k] + gr)
            base = (150, 112, 78)                                 # warm natural wood, palette v07 (#856450 family, a touch lighter)
            px.append(tuple(max(0, min(255, int(c * v))) for c in base))
    im = Image.new('RGB', (N, N)); im.putdata(px)
    im.save(OUT / 'TT_logs_v02_albedo.png')


def boards():
    r = random.Random(3)
    nb = 16
    w = N / nb
    grain = smooth_noise(5, 48)
    gy = grain.resize((N // 10, N)).resize((N, N))           # streaky along Y (vertical boards)
    tones = [r.uniform(-.04, .04) for _ in range(nb)]
    g = gy.load()
    px = []
    for y in range(N):
        for x in range(N):
            k = int(x // w); t = (x - k * w) / w
            v = .9 + tones[k] + (g[x, y] / 255 - .5) * .06
            if t < .05 or t > .95:
                v *= .62                                          # gap between boards
            elif t < .12:
                v *= .93                                          # soft shadow next to the gap
            elif t > .88:
                v *= 1.03
            c = int(max(0, min(1, v)) * 255)
            px.append((c, c, c))
    im = Image.new('RGB', (N, N)); im.putdata(px)
    im.save(OUT / 'TT_boards_vertical_v02_albedo.png')


logs()
boards()
print('ok', OUT)
