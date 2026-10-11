"""Fast motion-review rasteriser for GPU-less sessions (review only, never a deliverable).

Flat-shaded skinned A v04 mesh, orthographic cameras, painter's algorithm in numpy + Pillow:
about 0.1 s per frame instead of ~6 s for software EEVEE, so every frame of a clip can be looked at.
  python quicklook.py -- --clip Cargo_Knock --out DIR [--times a,b,c | --every 1]
         [--views side,three_quarter,front,knock34,wallcam,top] [--res 300]
         [--saved <stem>.blend]  (read the saved deliverable instead of re-authoring)
         [--grid sheet.png --cols 8] [--mp4 clip.mp4 --loops 3]
'wallcam' looks through the cargo wall (debug only); 'top' is a plan view. Prints the min/max mesh z
and min x of all sampled frames (floor, 1.2 m limit, wall plane).
"""
import sys, os, math, argparse, json
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import bpy
from mathutils import Vector
import acting_core as C
import clips_standing as CS
try:
    import clips_cargo as CC
except ImportError as e:
    print('no cargo', e); CC = None

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument('--clip', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--times', default='')
ap.add_argument('--every', type=float, default=1)
ap.add_argument('--views', default='side,three_quarter,front')
ap.add_argument('--res', type=int, default=360)
ap.add_argument('--mp4', default='')
ap.add_argument('--grid', default='')
ap.add_argument('--cols', type=int, default=8)
ap.add_argument('--loops', type=int, default=1)
ap.add_argument('--saved', default='')
a = ap.parse_args(argv)
REG = dict(CS.CLIPS)
if CC: REG.update(CC.CLIPS)
spec = REG[a.clip]
cargo = spec.get('stage') == 'cargo'
VIEWS = {
    'side': ((0.0, -5.0, 0.80), (-0.20, 0.0, 0.52), 1.85),
    'three_quarter': ((3.3, -3.6, 1.75), (-0.22, 0.0, 0.48), 1.85),
    'front': ((4.6, 0.0, 0.85), (-0.25, 0.0, 0.50), 1.85),
    'knock34': ((2.0, -4.0, 1.6), (-0.30, -0.1, 0.50), 1.85),
    'wallcam': ((-4.0, -0.6, 1.2), (-0.30, 0.0, 0.50), 1.85),
    'top': ((-0.3, -0.01, 5.0), (-0.3, 0.0, 0.0), 2.0),
} if cargo else {
    'side': ((5.0, 0.0, 1.05), (0.0, 0.0, 0.92), 2.15),
    'three_quarter': ((3.4, -4.4, 1.85), (0.0, 0.0, 0.90), 2.15),
    'front': ((0.0, -5.0, 1.05), (0.0, 0.0, 0.92), 2.15),
}
if a.saved:
    class _B: pass
    bpy.ops.wm.open_mainfile(filepath=a.saved)
    B = _B(); B.meshes = [bpy.data.objects[n] for n in C.MESH_NAMES]
    rig = bpy.data.objects[C.RIG_NAME]
    def _mp():
        dg = bpy.context.evaluated_depsgraph_get(); pts = []
        for o in B.meshes:
            ev = o.evaluated_get(dg); me = ev.to_mesh(); arr = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', arr)
            M = np.array(o.matrix_world); pts.append(arr.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]); ev.to_mesh_clear()
        return np.concatenate(pts)
    ctx = None
else:
    B = C.Buddy()
    ctx = spec['setup'](B)
T = spec['T']
N = int(round(T * C.FPS))
if a.times:
    times = [float(x) for x in a.times.split(',')]
else:
    times = [i / C.FPS for i in np.arange(0, N + 1e-9, a.every)]

tris, cols = [], []
for o in B.meshes:
    me = o.data
    mc = [np.array(m.diffuse_color[:3]) for m in me.materials]
    T_ = []
    for p in me.polygons:
        vs = list(p.vertices)
        for k in range(1, len(vs) - 1):
            T_.append((vs[0], vs[k], vs[k + 1]))
            cols.append(mc[p.material_index] if mc else np.array([.7, .7, .7]))
    tris.append(np.array(T_))
cols = np.array(cols)
offs = np.cumsum([0] + [len(o.data.vertices) for o in B.meshes])
TRI = np.concatenate([t + offs[i] for i, t in enumerate(tris)])


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def basis(loc, tgt):
    f = (np.array(tgt) - np.array(loc)); f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


LIGHT = np.array([-0.45, -0.6, 0.65]); LIGHT /= np.linalg.norm(LIGHT)


def render(pts, view, res, label):
    loc, tgt, ortho = VIEWS[view]
    f, r, u = basis(loc, tgt)
    s = res / ortho
    def proj(P):
        P = np.atleast_2d(P) - np.array(tgt)
        return np.stack([res / 2 + P @ r * s, res / 2 - P @ u * s], -1), P @ f
    img = Image.new('RGB', (res, res), (200, 202, 208))
    d = ImageDraw.Draw(img)
    # floor
    fl = np.array([[-3, -3, 0], [3, -3, 0], [3, 3, 0], [-3, 3, 0]])
    xy, _ = proj(fl); d.polygon([tuple(p) for p in xy], fill=(172, 174, 180))
    if cargo:
        w = C.WALL_X
        wl = np.array([[w, -1.6, 0], [w, 1.6, 0], [w, 1.6, 1.3], [w, -1.6, 1.3]])
        xy, dep = proj(wl)
        if view not in ('top', 'wallcam'):
            d.polygon([tuple(p) for p in xy], fill=(52, 66, 78))
        ln = np.array([[w + .002, -1.6, 1.2], [w + .002, 1.6, 1.2]])
        xy, _ = proj(ln); d.line([tuple(p) for p in xy], fill=(230, 90, 20), width=2)
    V = pts[TRI]
    n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    facing = (n @ f) < 0
    lam = np.abs(n @ LIGHT) * 0.6 + 0.4 * (0.5 + 0.5 * n[:, 2])
    c = to_srgb(cols * (0.25 + 0.95 * lam[:, None])) * 255
    xy, dep = proj(V.reshape(-1, 3))
    xy = xy.reshape(-1, 3, 2); dep = dep.reshape(-1, 3).mean(1)
    order = np.argsort(-dep)
    for i in order:
        if not facing[i]:
            continue
        d.polygon([tuple(p) for p in xy[i]], fill=tuple(int(x) for x in c[i]))
    d.text((4, 4), label, fill=(0, 0, 0))
    return img


os.makedirs(a.out, exist_ok=True)
views = a.views.split(',')
frames = []
stats = []
for k, t in enumerate(times):
    if a.saved:
        f = 1 + t * 30
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        pts = _mp()
    else:
        pose, extra = spec['pose'](ctx, t)
        pts = B.mesh_points(pose)
    stats.append((t, float(pts[:, 2].min()), float(pts[:, 2].max()), float(pts[:, 0].min())))
    ims = [render(pts, v, a.res, f'{a.clip} t={t:.3f}s f={1 + t * 30:.1f} {v}') for v in views]
    im = Image.new('RGB', (a.res * len(ims), a.res))
    for j, x in enumerate(ims):
        im.paste(x, (j * a.res, 0))
    p = os.path.join(a.out, f's{k:04d}.png')
    im.save(p)
    frames.append(p)
st = np.array(stats)
print('MINZ %.4f MAXZ %.4f MINX %.4f (wall %.3f)' % (st[:, 1].min(), st[:, 2].max(), st[:, 3].min(), C.WALL_X))
json.dump(stats, open(os.path.join(a.out, 'stats.json'), 'w'))
if a.grid:
    ims = [Image.open(p) for p in frames]
    w, h = ims[0].size
    cols_ = a.cols
    rows = (len(ims) + cols_ - 1) // cols_
    g = Image.new('RGB', (w * cols_, h * rows), (255, 255, 255))
    for i, x in enumerate(ims):
        g.paste(x, ((i % cols_) * w, (i // cols_) * h))
    g.save(a.grid)
if a.mp4:
    os.system(f'ffmpeg -n -loglevel error -stream_loop {a.loops - 1} -framerate 30 -i {a.out}/s%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20 {a.mp4}')
print('DONE', len(frames))
