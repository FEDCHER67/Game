"""Бесшовная карта нормалей мелкой ряби для моря «как Sea of Thieves» (TASK-000813): сумма синусов с целыми частотами
(тайл без шва), острые вытянутые гребешки (1 - |sin|)^2, нормаль из градиента с переносом через край. 512 px, PIL без numpy."""
import math
import os
import random
from PIL import Image

N = 512
r = random.Random(13)
WAVES = []
for k in range(22):
    f = r.choice((3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14))
    ang = r.uniform(-0.9, 0.9) + (math.pi if r.random() < 0.15 else 0)     # в основном вдоль ветра, немного вбок
    kx, ky = round(f * math.cos(ang)), round(f * math.sin(ang))
    if kx == 0 and ky == 0:
        continue
    WAVES.append((kx, ky, 1.0 / math.hypot(kx, ky) ** 0.9, r.uniform(0, 2 * math.pi)))
h = [0.0] * (N * N)
for y in range(N):
    v = y / N
    row = y * N
    for x in range(N):
        u = x / N
        s = 0.0
        for kx, ky, a, ph in WAVES:
            t = 1 - abs(math.sin(math.pi * (kx * u + ky * v) + ph))           # острый гребешок, период вдвое меньше
            s += a * t * t
        h[row + x] = s
mx, mn = max(h), min(h)
h = [(q - mn) / (mx - mn) for q in h]
S = 6.0
out = Image.new('RGB', (N, N))
px = out.load()
for y in range(N):
    for x in range(N):
        dx = h[y * N + (x + 1) % N] - h[y * N + (x - 1) % N]
        dy = h[((y + 1) % N) * N + x] - h[((y - 1) % N) * N + x]
        nx, ny, nz = -dx * S, -dy * S, 1.0
        L = math.sqrt(nx * nx + ny * ny + nz * nz)
        px[x, y] = (int(round((nx / L * 0.5 + 0.5) * 255)), int(round((ny / L * 0.5 + 0.5) * 255)), int(round((nz / L * 0.5 + 0.5) * 255)))
path = os.path.join(r'C:' + os.sep, 'Users', 'chern_0eqkb03', 'Desktop', 'GAME', 'Assets', 'OnlyVolunteers', 'Art', 'StyleKit_v3', 'WaterTests', 'WaterTest_v02_001', 'Water_ripples_normal_v01.png')
out.save(path)
print(path, len(WAVES))
