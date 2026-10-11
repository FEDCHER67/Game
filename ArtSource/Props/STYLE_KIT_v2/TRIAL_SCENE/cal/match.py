import numpy as np, sys, json
from PIL import Image
from scipy import ndimage
ref = np.asarray(Image.open(sys.argv[1]).convert('L'), float)
ren = np.asarray(Image.open(sys.argv[2]).convert('L'), float)
out = sys.argv[3]
R, S = 15, int(sys.argv[4]) if len(sys.argv) > 4 else 50
gx, gy = ndimage.sobel(ren, 1), ndimage.sobel(ren, 0)
g = ndimage.gaussian_filter(np.hypot(gx, gy), 3)
H, W = ren.shape
cand = []
gg = g.copy()
gg[:R+S] = 0; gg[-R-S:] = 0; gg[:, :R+S] = 0; gg[:, -R-S:] = 0
for _ in range(400):
    y, x = np.unravel_index(np.argmax(gg), gg.shape)
    if gg[y, x] <= 0: break
    cand.append((x, y)); gg[max(0, y-30):y+30, max(0, x-30):x+30] = 0
res = []
for x, y in cand:
    p = ren[y-R:y+R+1, x-R:x+R+1]; p = (p - p.mean()) / (p.std() + 1e-6)
    if np.std(ren[y-R:y+R+1, x-R:x+R+1]) < 8: continue
    best = (-2, 0, 0)
    for dy in range(-S, S+1, 1):
        for dx in range(-S, S+1, 1):
            q = ref[y+dy-R:y+dy+R+1, x+dx-R:x+dx+R+1]
            if q.shape != p.shape: continue
            qs = q.std()
            if qs < 1e-3: continue
            c = ((q - q.mean()) / qs * p).mean()
            if c > best[0]: best = (c, dx, dy)
    if best[0] > 0.85: res.append([int(x), int(y), int(x+best[1]), int(y+best[2]), round(float(best[0]), 3)])
json.dump(res, open(out, 'w'))
print(len(cand), len(res))
