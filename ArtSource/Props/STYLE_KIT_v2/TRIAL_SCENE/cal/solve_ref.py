import json, sys, numpy as np
from pnp import project
from scipy.optimize import least_squares
hits = {}
for line in open(sys.argv[1]).read().strip().split('\n'):
    p = line.split(' ')
    hits[(int(p[0]), int(p[1]))] = (float(p[2].replace(',', '.')), float(p[3].replace(',', '.')), float(p[4].replace(',', '.')), p[5])
m = json.load(open(sys.argv[2]))
x0 = json.loads(sys.argv[3]); fov_fixed = float(sys.argv[4]) if len(sys.argv) > 4 else None
P, UV = [], []
for rx, ry, fx, fy, c in m:
    if (rx, ry) in hits:
        P.append(hits[(rx, ry)][:3]); UV.append((fx + 0.5, fy + 0.5))
P, UV = np.array(P), np.array(UV)
def res(q):
    fov = fov_fixed if fov_fixed else q[5]
    uv, _ = project([q[0], q[1], q[2], q[3], q[4], 0], P, 1280, 720, fov)
    return (uv - UV).ravel()
q0 = x0 + ([] if fov_fixed else [60.0])
r = least_squares(res, q0, loss='soft_l1', f_scale=2.0)
e = np.hypot(*res(r.x).reshape(-1, 2).T)
inl = e < 4
r2 = least_squares(lambda q: res(q).reshape(-1, 2)[inl].ravel(), r.x)
e2 = np.hypot(*res(r2.x).reshape(-1, 2).T)
print('n', len(P), 'inliers', inl.sum(), 'median err', round(float(np.median(e2)), 2), 'inlier mean', round(float(e2[inl].mean()), 2))
print('pose', [round(float(v), 3) for v in r2.x])
