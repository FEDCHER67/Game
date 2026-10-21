"""Weathered corrugated roof sheets for the Hamlet houses (round 4), One-Armed Robber painted style (original work).
python gen_hamlet_textures_v02.py -> Assets/OnlyVolunteers/Art/TextureTest_v01/Source_v04/TT_roof_corrugated_weathered_v01_albedo.png
1024 px = 2.4 x 2.4 m. Corrugation waves of 0.15 m run along V (image rows), so on the house roof (UV u = down-slope) the ridges
run down the slope. Sheets 1.2 x 1.2 m with overlap seams, per-sheet tone, soft lichen / damp patches and rain streaks along the
slope. Neutral grey (mean ~0.7): the roof colour is the material tint (dark grey, dark rust, dark green-grey per house).
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parents[3] / 'Assets/OnlyVolunteers/Art/TextureTest_v01/Source_v04'
OUT.mkdir(parents=True, exist_ok=True)
N, PPM = 1024, 1024 / 2.4
WAVE = .15 * PPM            # px per corrugation wave
SHEET = int(1.2 * PPM)      # 512 px


def tile_noise(seed, cells, blur):
    r = random.Random(seed)
    small = Image.new('L', (cells, cells)); small.putdata([int(r.random() * 255) for _ in range(cells * cells)])
    big = Image.new('L', (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(small, (i * cells, j * cells))
    big = big.resize((N * 3, N * 3), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    return big.crop((N, N, 2 * N, 2 * N)).load()


def main():
    r = random.Random(11)
    patches = tile_noise(21, 6, 18)          # big soft lichen / damp patches
    streak = tile_noise(33, 48, 2)
    tones = {(i, j): r.uniform(-.07, .07) for i in range(2) for j in range(2)}
    px = []
    for y in range(N):
        wave = math.sin(2 * math.pi * y / WAVE)
        shade = .80 + .16 * wave + .06 * (wave * wave)        # lit crest, darker trough
        sj = y // SHEET
        for x in range(N):
            si = ((x + (sj * SHEET // 3)) % N) // SHEET           # staggered sheet ends
            v = shade * (1 + tones[(si % 2, sj % 2)])
            v *= 1 - .12 * (patches[x, y] / 255 - .45)           # weathering patches (keep the variation)
            v *= 1 - .05 * (streak[x // 1, y] / 255 - .5)        # streaks along the slope (x = u = down-slope)
            ex = (x + (sj * SHEET // 3)) % SHEET
            if ex < 6:
                v *= .72                                         # sheet end overlap shadow
            if (y % SHEET) < 4:
                v *= .8                                          # side lap
            c = max(0, min(255, int(v * .74 * 255)))
            px.append((c, c, c))
    im = Image.new('RGB', (N, N)); im.putdata(px)
    im.save(OUT / 'TT_roof_corrugated_weathered_v01_albedo.png')
    print('ok', OUT)


main()
