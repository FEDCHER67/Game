"""Step 8: headless verification renders (bpy, Cycles CPU) of the generated v76 data — no Unity needed.

Scene = terrain (2 m mesh from the 1 m heightmap, coloured by the splat layers), roads, water, district buildings
(extruded footprints, flat / gable / hip roofs), trees, border fence + checkpoint, tunnel axis.
Renders: full map top view + for each district a top view and 6 oblique views (N, NE, SE, S, SW, NW at 35°),
each top view side by side with the same crop of the 2D map v76 -> Tools/MapV76/out/renders/.
Run: python3 s08_render_bpy.py [district ...]   (pip install bpy)
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from common import MAP_PREVIEW, OUT, WORK, W, H, load_json  # noqa: E402

RDIR = os.path.join(WORK, 'renders')
LAYER_RGB = [(0.43, 0.50, 0.30), (0.62, 0.58, 0.40), (0.55, 0.45, 0.33), (0.33, 0.38, 0.24), (0.97, 0.95, 0.88), (0.80, 0.76, 0.66),
             (0.60, 0.59, 0.56), (0.48, 0.49, 0.46), (0.36, 0.52, 0.27), (0.45, 0.33, 0.22), (0.72, 0.64, 0.42)]
SURF_RGB = {'asphalt_A5d12': (0.33, 0.35, 0.37), 'asphalt_old_SK2a': (0.45, 0.46, 0.45), 'cobble_SK2c': (0.55, 0.50, 0.42)}
WALL_RGB = {'KH1b': (0.62, 0.62, 0.60), 'facade_downtown_stucco': (0.78, 0.72, 0.62), 'facade_downtown_brick': (0.55, 0.31, 0.26),
            'tower_glass': (0.20, 0.30, 0.42), 'facade_hamlet': (0.52, 0.40, 0.31), 'logs_SK5b': (0.50, 0.37, 0.26), 'boards_SK5a': (0.52, 0.40, 0.31),
            'facade_elite_villa': (0.93, 0.92, 0.89), 'concrete_panel_SK3c': (0.66, 0.65, 0.61), 'facade_warehouse': (0.62, 0.62, 0.58),
            'metal_painted_SK6a': (0.35, 0.45, 0.55), 'brick_SK3a': (0.55, 0.31, 0.26), 'stucco_SK3b': (0.80, 0.76, 0.68)}
ROOF_RGB = {'roof_tile_SK4a': (0.64, 0.39, 0.29), 'roof_slate_SK4b': (0.35, 0.37, 0.39), 'roof_wavy_slate': (0.55, 0.56, 0.54),
            'roof_flat_SK4d': (0.38, 0.38, 0.37), 'roof_profsheet_SK4c': (0.45, 0.48, 0.50), 'metal_rusty': (0.50, 0.33, 0.22)}
DISTRICTS = {   # name: (cx, cy, half-size of the view in m)
    'forest': (300, 200, 140), 'hamlet': (320, 490, 140), 'construction': (610, 420, 100), 'rough': (830, 785, 170),
    'downtown': (1030, 345, 160), 'port': (1265, 640, 110), 'elite': (1420, 320, 120), 'quiet_valley': (590, 195, 120),
    'beach': (1080, 195, 210), 'tramduro': (1555, 765, 130), 'hill_B_tunnel': (950, 590, 170), 'border_checkpoint': (860, 905, 110)}


def mat(name, rgb, rough=0.8, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    return m


def mesh_obj(name, verts, faces, material, colors=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if colors is not None:
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        loop_cols = np.repeat(np.asarray(colors, np.float32)[np.array([v for p in me.polygons for v in p.vertices])][:, None, :], 1, 1).reshape(-1, 4)
        ca.data.foreach_set('color', loop_cols.ravel())
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def terrain():
    h = np.load(os.path.join(WORK, 'height_1m.npy'))
    s = 2
    hs = h[::s, ::s]
    ny, nx = hs.shape
    xs, ys = np.meshgrid(np.arange(nx) * s + .5, np.arange(ny) * s + .5)
    verts = np.stack([xs, ys, hs], -1).reshape(-1, 3)
    idx = np.arange(nx * ny).reshape(ny, nx)
    faces = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    t = load_json('terrain_v76.json')
    acc = np.zeros((H, W, 3), np.float32)
    for k, f in enumerate(t['splat']['files']):
        im = np.asarray(Image.open(os.path.join(OUT, f)), np.float32)[::-1] / 255
        for c in range(4):
            li = 4 * k + c
            if li < len(LAYER_RGB):
                acc += im[..., c:c + 1] * np.array(LAYER_RGB[li], np.float32)
    acc = acc[::s, ::s].reshape(-1, 3)
    shade = 1.0
    cols = np.concatenate([acc * shade, np.ones((len(acc), 1), np.float32)], 1)
    m = mat('terrain', (1, 1, 1))
    nt = m.node_tree
    attr = nt.nodes.new('ShaderNodeVertexColor')
    attr.layer_name = 'Col'
    nt.links.new(attr.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    me = bpy.data.meshes.new('terrain')
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(len(faces) * 4)
    me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', (np.arange(len(faces)) * 4).astype(np.int32))
    me.update()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', cols.astype(np.float32).ravel())
    ob = bpy.data.objects.new('terrain', me)
    ob.data.materials.append(m)
    bpy.context.scene.collection.objects.link(ob)
    return h


def ribbon(pts, width, z_of, lift=0.15):
    verts, faces = [], []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx_, ny_ = -dy / L * width / 2, dx / L * width / 2
        z = z_of(p) + lift
        verts += [(p[0] + nx_, p[1] + ny_, z), (p[0] - nx_, p[1] - ny_, z)]
        if i:
            k = 2 * i
            faces.append((k - 2, k - 1, k + 1, k))
    return verts, faces


def sample(h, p):
    x, y = int(min(W - 1, max(0, p[0]))), int(min(H - 1, max(0, p[1])))
    return float(h[y, x])


def roads(h):
    rj = load_json('roads_v76.json')
    groups = {}
    for r in rj['roads']:
        if r['kind'] in ('tunnel',):
            continue
        pts = [tuple(p) for p in r['points']]
        surf = 'sand' if r['kind'] == 'sand_track' else 'dirt' if r['kind'] == 'dirt_from_map' else r.get('surface', 'asphalt_A5d12')
        v, f = ribbon(pts, r['width_m'], lambda p: sample(h, p), 0.12)
        g = groups.setdefault(surf, ([], []))
        off = len(g[0])
        g[0].extend(v)
        g[1].extend([tuple(i + off for i in fc) for fc in f])
    rgb = dict(SURF_RGB, sand=(0.86, 0.80, 0.62), dirt=(0.62, 0.50, 0.36))
    for surf, (v, f) in groups.items():
        mesh_obj('road_' + surf, v, f, mat('road_' + surf, rgb.get(surf, (0.33, 0.35, 0.37))))
    t = load_json('terrain_v76.json')['tunnel']
    v, f = ribbon([tuple(p) for p in t['axis']], 9.0, lambda p: 0, 0)
    za, zb = t['portal_heights_m']
    n = len(v) // 2
    v = [(x, y, za + (zb - za) * (i // 2) / max(1, n - 1) + 6.0) for i, (x, y, _) in enumerate(v)]
    ob = mesh_obj('tunnel_axis', v, f, mat('tunnel', (0.95, 0.35, 0.10)))
    ob.display_type = 'WIRE'


def poly_fill(outline, z):
    n = len(outline)
    verts = [(p[0], p[1], z) for p in outline]
    return verts, [tuple(range(n))]


def water(h):
    wj = load_json('water_v76.json')
    t = load_json('terrain_v76.json')
    lv = {l['id']: l['surface_m'] for l in t['lakes']}
    sea_v = [(-300, -300, 0), (W + 300, -300, 0), (W + 300, H + 300, 0), (-300, H + 300, 0)]
    mesh_obj('sea', sea_v, [(0, 1, 2, 3)], mat('water', (0.25, 0.62, 0.78), 0.05))
    for b in wj['bodies']:
        if 'outline' not in b:
            continue
        if b['kind'] == 'river':
            yy = np.mean([p[1] for p in b['outline']])
            z = 1.5 + 2.5 * sm((yy - 96) / 200) + 11 * sm((yy - 560) / 180) + 1.2
        else:
            z = lv.get(b['id'], sample(h, b['centre']) + .2)
        v, f = poly_fill(b['outline'], z)
        mesh_obj('water_' + b['id'], v, f, mat('water_swamp' if b['kind'] == 'swamp' else 'water', (0.16, 0.22, 0.15) if b['kind'] == 'swamp' else (0.25, 0.62, 0.78), 0.05))


def sm(t):
    t = min(1, max(0, t))
    return t * t * (3 - 2 * t)


def buildings(h):
    import glob
    d = os.path.join(OUT, 'districts')
    total = 0
    groups = {}
    for f in sorted(glob.glob(os.path.join(d, '*_v76.json'))):
        dj = json.load(open(f, encoding='utf-8'))
        for b in dj.get('buildings', []):
            fp = [tuple(p) for p in b.get('footprint', [])]
            if len(fp) < 3:
                continue
            hgt = b.get('height_m') or max(2.5, (b.get('floors') or 1) * (b.get('floor_h_m') or 3.0))
            base = min(sample(h, p) for p in fp) - .25
            top = base + hgt
            wall = b.get('walls') or ('KH1b' if 'rough' in f else 'stucco_SK3b')
            g = groups.setdefault(('w', wall, b.get('tint')), ([], []))
            n = len(fp)
            o = len(g[0])
            g[0].extend([(x, y, base) for x, y in fp] + [(x, y, top) for x, y in fp])
            for i in range(n):
                j = (i + 1) % n
                g[1].append((o + i, o + j, o + n + j, o + n + i))
            roof = b.get('roof') or {}
            rt = roof.get('type', 'flat')
            rm = roof.get('material') or ('roof_flat_SK4d' if rt == 'flat' else 'roof_tile_SK4a')
            gr = groups.setdefault(('r', rm, None), ([], []))
            o = len(gr[0])
            if rt in ('flat', 'none') or len(fp) != 4:
                gr[0].extend([(x, y, top + .02) for x, y in fp])
                gr[1].append(tuple(range(o, o + n)))
            else:
                e = [np.array(fp[(i + 1) % 4]) - np.array(fp[i]) for i in range(4)]
                k = 0 if np.linalg.norm(e[0]) >= np.linalg.norm(e[1]) else 1
                p0, p1, p2, p3 = [np.array(fp[(k + i) % 4]) for i in range(4)]
                rh = roof.get('ridge_h_m') or max(1.5, 0.35 * np.linalg.norm(p2 - p1))
                m01, m23 = (p0 + p3) / 2, (p1 + p2) / 2
                if rt == 'hip':
                    ax = (p1 - p0) / (np.linalg.norm(p1 - p0) or 1)
                    inset = min(np.linalg.norm(p2 - p1) / 2, np.linalg.norm(p1 - p0) / 2 - .1)
                    m01, m23 = m01 + ax * inset, m23 - ax * inset
                gr[0].extend([(*p0, top), (*p1, top), (*p2, top), (*p3, top), (*m01, top + rh), (*m23, top + rh)])
                gr[1].extend([(o, o + 1, o + 5, o + 4), (o + 2, o + 3, o + 4, o + 5), (o + 3, o, o + 4), (o + 1, o + 2, o + 5)])
            total += 1
    for (kind, key, tint), (v, f) in groups.items():
        rgb = WALL_RGB.get(key, (0.75, 0.72, 0.66)) if kind == 'w' else ROOF_RGB.get(key, (0.40, 0.40, 0.40))
        if tint:
            try:
                rgb = tuple(int(tint.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
            except ValueError:
                pass
        mesh_obj('%s_%s_%s' % (kind, key, tint), v, f, mat('%s_%s_%s' % (kind, key, tint), rgb))
    return total


def trees(h):
    vj = load_json('vegetation_v76.json')
    pts = [(t[0], t[1], t[2], t[3]) for t in vj['trees']]
    import glob
    for f in glob.glob(os.path.join(OUT, 'districts', '*_v76.json')):
        for p in json.load(open(f, encoding='utf-8')).get('props', []):
            k = str(p.get('kind', '')).lower()
            if any(s in k for s in ('tree', 'palm', 'bush', 'oak', 'apple', 'pine', 'birch')):
                pts.append((p['pos'][0], p['pos'][1], 'palm' if 'palm' in k else 'bare' if 'rough' in f else 'leafy', 1.0))
    groups = {}
    for x, y, kind, s in pts:
        z = sample(h, (x, y))
        conifer = kind in ('pine', 'spruce')
        r, ht = (2.2 if conifer else 3.0) * s, (14 if kind == 'pine' else 11 if conifer else 8) * s
        if kind == 'palm':
            r, ht = 2.4, 9
        g = groups.setdefault('conifer' if conifer else kind if kind in ('palm', 'bare') else 'leafy', ([], []))
        o = len(g[0])
        seg = 6
        g[0].extend([(x + r * math.cos(2 * math.pi * i / seg), y + r * math.sin(2 * math.pi * i / seg), z + ht * (0.25 if conifer else 0.4)) for i in range(seg)] + [(x, y, z + ht)])
        g[1].extend([(o + i, o + (i + 1) % seg, o + seg) for i in range(seg)] + [tuple(range(o + seg - 1, o - 1, -1))])
    rgb = {'conifer': (0.18, 0.30, 0.18), 'leafy': (0.30, 0.45, 0.22), 'palm': (0.35, 0.55, 0.25), 'bare': (0.40, 0.35, 0.30)}
    for k, (v, f) in groups.items():
        mesh_obj('trees_' + k, v, f, mat('tree_' + k, rgb[k]))
    return len(pts)


def border(h):
    bj = load_json('border_v76.json')
    pts = [tuple(p) for p in bj['fence']['points']]
    v, f = [], []
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        za, zb = sample(h, a), sample(h, b)
        o = len(v)
        v += [(a[0], a[1], za), (b[0], b[1], zb), (b[0], b[1], zb + 2.5), (a[0], a[1], za + 2.5)]
        f.append((o, o + 1, o + 2, o + 3))
    mesh_obj('fence', v, f, mat('fence', (0.55, 0.57, 0.58)))
    cp = bj['checkpoint']
    cx, cy = cp['building_centre']
    sx, sy, sz = cp['building_size_m']
    z = sample(h, (cx, cy))
    v = [(cx - sx / 2, cy - sy / 2, z), (cx + sx / 2, cy - sy / 2, z), (cx + sx / 2, cy + sy / 2, z), (cx - sx / 2, cy + sy / 2, z)]
    v += [(x, y, z + sz) for x, y, _ in v]
    mesh_obj('checkpoint', v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], mat('cp', (0.70, 0.70, 0.66)))
    g0, g1 = cp['gate']['from'], cp['gate']['to']
    z = sample(h, g0)
    mesh_obj('gate', [(g0[0], g0[1], z), (g1[0], g1[1], z), (g1[0], g1[1], z + 3.2), (g0[0], g0[1], z + 3.2)], [(0, 1, 2, 3)], mat('gate', (0.75, 0.15, 0.12)))


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 12
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.render.resolution_x, sc.render.resolution_y = 960, 960
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.72, 0.80, 0.88, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    sc.world = world
    sun = bpy.data.lights.new('sun', 'SUN')
    sun.energy = 3.5
    so = bpy.data.objects.new('sun', sun)
    so.rotation_euler = (math.radians(53), 0, math.radians(-35))
    sc.collection.objects.link(so)
    cam = bpy.data.cameras.new('cam')
    co = bpy.data.objects.new('cam', cam)
    sc.collection.objects.link(co)
    sc.camera = co
    cam.clip_end = 6000
    return co


def look_at(ob, eye, target):
    from mathutils import Vector
    ob.location = eye
    d = Vector(target) - Vector(eye)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render(co, path, eye, target, ortho=None, res=(960, 960)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    co.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        co.data.ortho_scale = ortho
    else:
        co.data.lens = 28
    look_at(co, eye, target)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def side_by_side(render_png, cx, cy, half, out_png):
    m = Image.open(MAP_PREVIEW).convert('RGB')
    box = (int(cx - half), int(H - (cy + half)), int(cx + half), int(H - (cy - half)))
    crop = m.crop(box).resize((960, 960))
    r = Image.open(render_png).convert('RGB').resize((960, 960))
    out = Image.new('RGB', (1920, 960), (255, 255, 255))
    out.paste(crop, (0, 0))
    out.paste(r, (960, 0))
    out.save(out_png)


def main():
    only = sys.argv[1:]
    os.makedirs(RDIR, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    h = terrain()
    roads(h)
    water(h)
    nb = buildings(h)
    nt = trees(h)
    border(h)
    co = setup_render()
    report = {'buildings': nb, 'trees': nt, 'renders': []}
    if not only or 'map' in only:
        p = os.path.join(RDIR, 'map_top_v76.png')
        render(co, p, (W / 2, H / 2, 900), (W / 2, H / 2, 0), ortho=W, res=(1744, 950))
        m = Image.open(MAP_PREVIEW).convert('RGB')
        r = Image.open(p).convert('RGB')
        both = Image.new('RGB', (1744, 1900))
        both.paste(m, (0, 0))
        both.paste(r, (0, 950))
        both.resize((872, 950)).save(os.path.join(RDIR, 'map_top_vs_2d_v76.png'))
        report['renders'].append(p)
    for name, (cx, cy, half) in DISTRICTS.items():
        if only and name not in only:
            continue
        zc = sample(h, (cx, cy))
        top = os.path.join(RDIR, '%s_top.png' % name)
        render(co, top, (cx, cy, zc + 600), (cx, cy, zc), ortho=2 * half)
        side_by_side(top, cx, cy, half, os.path.join(RDIR, '%s_top_vs_2d.png' % name))
        for k, az in enumerate((90, 45, 315, 270, 225, 135)):                       # N, NE, SE, S, SW, NW (camera position)
            a = math.radians(az)
            dist = half * 1.5
            eye = (cx + dist * math.cos(a), cy + dist * math.sin(a), zc + dist * math.tan(math.radians(35)))
            p = os.path.join(RDIR, '%s_oblique_%d_%s.png' % (name, k + 1, ['N', 'NE', 'SE', 'S', 'SW', 'NW'][k]))
            render(co, p, eye, (cx, cy, zc + 4), res=(960, 600))
            report['renders'].append(p)
        report['renders'].append(top)
    json.dump(report, open(os.path.join(RDIR, 'render_report.json'), 'w'), indent=1)
    print(report['buildings'], 'buildings', report['trees'], 'trees', len(report['renders']), 'renders')


if __name__ == '__main__':
    main()
