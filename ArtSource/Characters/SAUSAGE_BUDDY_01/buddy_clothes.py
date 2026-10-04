"""Variant outfits A/B/C for the Sausage Buddy, following the owner's reference image."""
import math
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc
import buddy_geo as G
from buddy_geo import mat, smoothstep, chain, mix, FRONT, SIDE, BACK
import buddy_body as B

P = 'mixamorig:'

# ------------------------------------------------------------------ weights
def weight_source(objs):
    verts, tris, vw = [], [], []
    for o in objs:
        names = [g.name for g in o.vertex_groups]
        base = len(verts); mw = o.matrix_world
        for v in o.data.vertices:
            verts.append(mw @ v.co)
            vw.append({names[g.group]: g.weight for g in v.groups if g.weight > 1e-4})
        o.data.calc_loop_triangles()
        tris += [tuple(base + i for i in lt.vertices) for lt in o.data.loop_triangles]
    return verts, tris, vw, BVHTree.FromPolygons(verts, tris)


def set_weights(ob, per_vertex):
    for vi, w in enumerate(per_vertex):
        items = sorted(((k, x) for k, x in w.items() if x > 1e-4), key=lambda kv: -kv[1])[:4]
        tot = sum(x for _, x in items) or 1.0
        for k, x in items:
            g = ob.vertex_groups.get(k) or ob.vertex_groups.new(name=k)
            g.add([vi], x / tot, 'REPLACE')


def transfer(ob, src, filt=None):
    verts, tris, vw, bvh = src
    out = []
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        loc, _, idx, _ = bvh.find_nearest(p)
        tri = tris[idx]
        bw = poly_3d_calc([verts[i] for i in tri], loc)
        acc = {}
        for i, f in zip(tri, bw):
            for g, x in vw[i].items():
                acc[g] = acc.get(g, 0.0) + x * f
        out.append(filt(p, acc) if filt else acc)
    set_weights(ob, out)
    return ob


def rigid(ob, bone='Head'):
    set_weights(ob, [{P + bone: 1.0} for _ in ob.data.vertices])
    return ob

# ------------------------------------------------------------------ garment builders
def torso_garment(name, rows, arm_row, sleeve, hem_inner, mats, rib_rows=(), cuff_from=None, n=24, subdiv=1):
    """Rings around the torso, armholes cut from the side panels, sleeves grown along the arms."""
    vs, fs, idx, rings = [], [], [], []
    for z, rx, ry, dy in rows:
        ring = []
        for j in range(n):
            a = j * 2 * math.pi / n
            ring.append(len(vs)); vs.append((rx * math.cos(a), dy + ry * math.sin(a), z))
        rings.append(ring)
    side = {(c + j) % n for c in (0, n // 2) for j in range(-n // 8, n // 8)}
    for k in range(len(rings) - 1):
        for j in range(n):
            if k in (arm_row, arm_row + 1) and j in side:
                continue
            fs.append((rings[k][j], rings[k][(j + 1) % n], rings[k + 1][(j + 1) % n], rings[k + 1][j]))
            idx.append(1 if k in rib_rows else 0)
    h = n // 8
    for sign, c in ((1, 0), (-1, n // 2)):
        js = [(c + j) % n for j in range(-h, h + 1)]
        boundary = ([rings[arm_row][j] for j in js] + [rings[arm_row + 1][js[-1]], rings[arm_row + 2][js[-1]]]
                    + [rings[arm_row + 2][j] for j in reversed(js[:-1])] + [rings[arm_row + 1][js[0]]])
        start = -3 * math.pi / 4 if sign == 1 else -math.pi / 4
        angles = [start + sign * j * 2 * math.pi / len(boundary) for j in range(len(boundary))]
        last = boundary
        for k, (x, r) in enumerate(sleeve):
            new = []
            for a in angles:
                new.append(len(vs)); vs.append((sign * x, r * math.cos(a), B.arm_z(x) + r * 1.02 * math.sin(a)))
            for j in range(len(new)):
                fs.append((last[j], last[(j + 1) % len(new)], new[(j + 1) % len(new)], new[j]))
                idx.append(1 if (cuff_from is not None and k >= cuff_from) else 0)
            last = new
    z, rx, ry, dy = hem_inner
    inner = []
    for j in range(n):
        a = j * 2 * math.pi / n
        inner.append(len(vs)); vs.append((rx * math.cos(a), dy + ry * math.sin(a), z))
    for j in range(n):
        fs.append((inner[j], inner[(j + 1) % n], rings[0][(j + 1) % n], rings[0][j]))
        idx.append(1 if 0 in rib_rows else 0)
    return G.from_data(name, vs, fs, mats[0], True, idx, mats[1:], subdiv=subdiv)


def legwear(name, waist, crotch_z, legs, mats, cuff=None, leg_x=B.LEG_X, n=16, subdiv=1, crotch=1.0):
    vs, fs, idx, rings = [], [], [], []
    for z, rx, ry in waist:
        ring = []
        for j in range(n):
            a = j * 2 * math.pi / n
            ring.append(len(vs)); vs.append((rx * math.cos(a), ry * math.sin(a), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        G.bridge(fs, a, b); idx += [0] * n
    rxb, ryb = waist[-1][1] * crotch, (waist[-1][2] - 0.006) * crotch     # crotch < 1: the pull-in subdivision used to give
    bottom = []
    for j in range(n):
        a = j * 2 * math.pi / n
        bottom.append(len(vs)); vs.append((rxb * math.cos(a), ryb * math.sin(a), crotch_z + 0.022 * abs(math.sin(a))))
    G.bridge(fs, rings[-1], bottom); idx += [0] * n
    q = n // 4
    seam = [bottom[q]]
    for y in (ryb * 0.45, 0.0, -ryb * 0.45):
        seam.append(len(vs)); vs.append((0, y, crotch_z + 0.008))
    seam.append(bottom[3 * q])
    for sign, outer in ((1, [(3 * q + j) % n for j in range(n // 2 + 1)]), (-1, list(range(q, 3 * q + 1)))):
        boundary = [bottom[j] for j in outer] + (seam[1:-1] if sign == 1 else list(reversed(seam[1:-1])))
        angles = [math.atan2(vs[i][1] / ryb, (vs[i][0] - sign * leg_x) / (rxb - leg_x + 0.001)) for i in boundary]
        last = boundary
        rows = list(legs) + (list(cuff) if cuff else [])
        for k, (z, r) in enumerate(rows):
            new = []
            for a in angles:
                new.append(len(vs)); vs.append((sign * leg_x + r * math.cos(a), r * math.sin(a), z))
            for j in range(len(new)):
                fs.append((last[j], last[(j + 1) % len(new)], new[(j + 1) % len(new)], new[j]))
                idx.append(1 if (cuff and k >= len(legs)) else 0)
            last = new
    z0, rx0, ry0 = waist[0]
    inner = []
    for j in range(n):
        a = j * 2 * math.pi / n
        inner.append(len(vs)); vs.append(((rx0 - 0.008) * math.cos(a), (ry0 - 0.005) * math.sin(a), z0 - 0.004))
    G.bridge(fs, inner, rings[0]); idx += [0] * n
    return G.from_data(name, vs, fs, mats[0], True, idx, mats[1:], subdiv=subdiv)


def socks(name, base, stripe, stripes, top=0.300, seg=14, rows=(0.090, 0.120, 0.170, 0.220), lip=True):
    vs, fs, idx = [], [], []
    zs = sorted(set(rows) | ({top - 0.004} if lip else set()) | {top} | {z for s in stripes for z in s})
    for sign in (1, -1):
        rings = []
        for z in zs:
            r = 0.0455 if z < 0.13 else 0.0440
            ring = []
            for j in range(seg):
                a = 2 * math.pi * j / seg
                ring.append(len(vs)); vs.append((sign * B.LEG_X + r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)
        inner = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            inner.append(len(vs)); vs.append((sign * B.LEG_X + 0.0400 * math.cos(a), 0.0400 * math.sin(a), top - 0.007))
        for k in range(len(rings) - 1):
            mid = (zs[k] + zs[k + 1]) / 2
            G.bridge(fs, rings[k], rings[k + 1]); idx += [1 if any(a <= mid <= b for a, b in stripes) else 0] * seg
        G.bridge(fs, rings[-1], inner); idx += [0] * seg
    return G.from_data(name, vs, fs, base, True, idx, [stripe], subdiv=0)


def round_ends(ys, heel, toe):
    """Unsubdivided stand-in for the rounding Catmull-Clark gave the shoe ends: one shrunken section just beyond
    the heel (+y) and the toe (-y). Returns [(y, shrink)]."""
    return [(ys[0] + heel, 0.62)] + [(y, 1.0) for y in ys] + [(ys[-1] - toe, 0.62)]


def sneaker(name, sign, upper, sole, high=False, seg=14):
    """Chunky cartoon sneaker around the foot: thick sole slab + rounded upper; toes turned out 6 deg."""
    yaw = Matrix.Rotation(math.radians(-6 * sign), 3, 'Z')
    cx = sign * B.LEG_X
    rsh = G.res('shoe', ys=(0.096, 0.086, 0.060, 0.022, -0.020, -0.064, -0.108, -0.150, -0.184, -0.208, -0.224, -0.231), bottom=4)
    ys = list(rsh['ys'])
    def half_w(y):
        t = (0.096 - y) / 0.327
        return 0.055 + 0.026 * math.sin(math.pi * min(1.0, t * 1.12)) - (0.030 * smoothstep(0.82, 1.0, t))
    def top_h(y):
        if high:
            base = 0.215 if y > -0.025 else 0.132 - 0.24 * (-0.025 - y) * 0.55
        else:
            base = 0.140 if y > 0.000 else 0.134 - 0.30 * (0.000 - y) * 0.55
        return max(base, 0.076 + 0.03 * smoothstep(-0.231, -0.185, y))
    lift = lambda y: 0.011 * smoothstep(-0.16, -0.231, y)
    # sole
    rs = G.res('sole', seg=12, subdiv=1, round_ends=False)
    s_rows = round_ends(ys, 0.010, 0.008) if rs['round_ends'] else [(y, 1.0) for y in ys]
    s_secs = []
    for y, k in s_rows:
        yc = max(min(y, ys[0]), ys[-1])
        w = (half_w(yc) + 0.004) * k
        s_secs.append(((cx, y, 0.021 + lift(yc) + 0.004 * (1 - k)), (1, 0, 0), (0, 0, 1), w, 0.022 * (0.5 + 0.5 * k)))
    sole_ob = G.loft(name + '_Sole', s_secs, sole, seg=rs['seg'], subdiv=rs['subdiv'])
    # upper: half-ellipse arch over the sole
    ru = G.res('upper', seg=seg, subdiv=1, round_ends=False)
    u_rows = round_ends(ys, 0.008, 0.006) if ru['round_ends'] else [(y, 1.0) for y in ys]
    vs, fs, rings = [], [], []
    for y, k in u_rows:
        yc = max(min(y, ys[0]), ys[-1])
        w, h, z0 = half_w(yc) * k, top_h(yc), 0.036 + lift(yc)
        h = z0 + (h - z0) * (0.55 + 0.45 * k)
        ring = []
        for j in range(ru['seg']):
            a = math.pi * j / (ru['seg'] - 1)
            ring.append(len(vs)); vs.append((cx + w * math.cos(a), y, z0 + (h - z0) * (max(0.0, math.sin(a)) ** 0.85)))
        ring_b = []
        nb = rsh['bottom']
        for j in range(nb):
            x = cx + w * (-1 + 2 * (j + 1) / (nb + 1))
            ring_b.append(len(vs)); vs.append((x, y, z0))
        rings.append(ring + ring_b)
    for a, b in zip(rings, rings[1:]):
        G.bridge(fs, a, b)
    fs.append(tuple(reversed(rings[0]))); fs.append(tuple(rings[-1]))
    up = G.from_data(name + '_Upper', vs, fs, upper, True, subdiv=ru['subdiv'])
    for o in (sole_ob, up):
        me = o.data
        piv = Vector((cx, 0, 0))
        for v in me.vertices:
            v.co = piv + yaw @ (v.co - piv)
    return up, sole_ob, top_h, yaw


def shoe_weights(sign):
    side = 'Left' if sign > 0 else 'Right'
    def w(p):
        base = chain(-p.y, [(0.04, side + 'Foot'), (0.11, side + 'ToeBase')])
        return {P + k: v for k, v in mix(base, {side + 'Leg': 1.0}, smoothstep(0.125, 0.19, p.z) * 0.85).items()}
    return w


def laces(name, sign, top_h, yaw, material):
    cx = sign * B.LEG_X
    out = []
    r = G.res('lace', seg=6, pts=4, caps=True)
    for k, y in enumerate((-0.005, -0.035, -0.065, -0.095)):
        z = top_h(y) + 0.002
        if r['pts'] == 3:   # one arched span; the ends sink into the upper, so no caps are needed
            pts = [Vector((cx - 0.030, y, z - 0.010)), Vector((cx, y - 0.003, z + 0.004)), Vector((cx + 0.030, y, z - 0.010))]
        else:
            pts = [Vector((cx - 0.030, y, z - 0.010)), Vector((cx - 0.012, y - 0.003, z + 0.003)), Vector((cx + 0.012, y - 0.003, z + 0.003)), Vector((cx + 0.030, y, z - 0.010))]
        piv = Vector((cx, 0, 0))
        pts = [piv + yaw @ (p - piv) for p in pts]
        out.append(G.tube(f'{name}_{k}', pts, 0.0042, material, seg=r['seg'], caps=r['caps']))
    return out


def dome(name, center, rx, ry, rz, z_cut, material, seg=32, ribs=0.0, cuff=None, front=None, bands=10):
    vs, fs, idx, rings = [], [], [], []
    cx, cy, cz = center
    t_cut = math.acos(max(-1, min(1, (z_cut - cz) / rz)))
    rows = []
    if cuff:
        z0, z1, rc = cuff
        rows += [(z0, rc * rx / max(rx, ry), rc * ry / max(rx, ry)), ((z0 + z1) / 2, (rc + 0.003) * rx / max(rx, ry), (rc + 0.003) * ry / max(rx, ry)),
                 (z1, rc * rx / max(rx, ry), rc * ry / max(rx, ry))]
    for k in range(bands):
        t = t_cut * (1 - k / bands)
        rows.append((cz + rz * math.cos(t), rx * math.sin(t), ry * math.sin(t)))
    for z, ax, ay in rows:
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            bump = ribs if (ribs and j % 2 == 0) else 0.0
            ring.append(len(vs)); vs.append((cx + (ax + bump) * math.cos(a), cy + (ay + bump) * math.sin(a), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
            m = (Vector(vs[a[j]]) + Vector(vs[b[(j + 1) % seg]])) / 2
            idx.append(1 if (front and abs(math.degrees(math.atan2(m.x, -(m.y - cy)))) < 46.0) else 0)
    top = len(vs); vs.append((cx, cy, cz + rz))
    for j in range(seg):
        fs.append((rings[-1][j], rings[-1][(j + 1) % seg], top)); idx.append(0)
    return G.from_data(name, vs, fs, material, True, idx, [front] if front else [])


def strap(name, path, material, width=0.024, thick=0.004, normal_fn=None):
    vs, fs = [], []
    Pp = [Vector(p) for p in path]
    for i, p in enumerate(Pp):
        t = (Pp[min(i + 1, len(Pp) - 1)] - Pp[max(i - 1, 0)]).normalized()
        out = normal_fn(p) if normal_fn else Vector((p.x, p.y, 0)).normalized()
        side = t.cross(out).normalized()
        for a, b in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            vs.append(p + side * (a * width / 2) + out * (b * thick))
    for i in range(len(Pp) - 1):
        a, b = i * 4, (i + 1) * 4
        for j in range(4):
            fs.append((a + j, a + (j + 1) % 4, b + (j + 1) % 4, b + j))
    fs.append((3, 2, 1, 0)); n = (len(Pp) - 1) * 4; fs.append((n, n + 1, n + 2, n + 3))
    return G.from_data(name, vs, fs, material, False)


def projected_path(targets, pts2d, axes, offset):
    origin, u, v, ray = (Vector(a) for a in axes)
    bvh = G.bvh_of(targets)
    out = []
    for a, b in pts2d:
        p0 = origin + u * a + v * b
        hit = bvh.ray_cast(p0 - ray * 0.7, ray, 1.6)
        if hit[0] is None:
            out.append(p0); continue
        n = hit[1] if hit[1].dot(ray) < 0 else -hit[1]
        out.append(hit[0] + n * offset)
    return out


def ellipse(cx, cz, rx, rz, n=20, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(a) * c - rz * math.sin(a) * s, cz + rx * math.cos(a) * s + rz * math.sin(a) * c)
            for a in [2 * math.pi * k / n for k in range(n)]]


def hotdog(prefix, cx, cz, length, height, rot, targets, offset, mats, outline=None):
    """Flat sausage print/patch: optional white outline, sausage body, three dark grill marks, light shine."""
    body_m, grill_m, shine_m = mats
    r = G.res('print', n=24, grill=10, shine=12, step=0.010)
    parts = []
    if outline:
        parts.append(G.decal(prefix + '_Outline', ellipse(cx, cz, length / 2 + 0.008, height / 2 + 0.008, r['n'], rot), FRONT(), targets, offset, outline, step=r['step']))
        offset += 0.0015
    parts.append(G.decal(prefix + '_Body', ellipse(cx, cz, length / 2, height / 2, r['n'], rot), FRONT(), targets, offset, body_m, step=r['step']))
    c, s = math.cos(rot), math.sin(rot)
    for k in (-1, 0, 1):
        gx, gz = cx + k * length * 0.22 * c, cz + k * length * 0.22 * s
        parts.append(G.decal(f'{prefix}_Grill_{k}', ellipse(gx, gz, height * 0.10, height * 0.34, r['grill'], rot + 0.5), FRONT(), targets, offset + 0.0015, grill_m))
    parts.append(G.decal(prefix + '_Shine', ellipse(cx - length * 0.05 * c, cz + height * 0.22, length * 0.30, height * 0.08, r['shine'], rot), FRONT(), targets,
                         offset + 0.0015, shine_m))
    return parts


def text_arc(name, text, cz, radius, a0, a1, up, ink, target, size=0.034):
    out = []
    bvh = G.bvh_of([target])
    for i, ch in enumerate(text):
        ang = math.radians(a0 + (a1 - a0) * (i + 0.5) / len(text))
        ang = math.pi - ang if up else ang
        cu = bpy.data.curves.new(f'{name}_{i}', 'FONT')
        cu.body = ch; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = G.res('text', resolution=3)['resolution']
        try:
            cu.offset = 0.0012
        except Exception:
            pass
        tmp = bpy.data.objects.new(f'{name}_{i}_tmp', cu); G.COLLECTION.objects.link(tmp)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg)
        bpy.data.objects.remove(tmp)
        cx, cz2 = radius * math.cos(ang), cz + radius * math.sin(ang)
        rot = (ang - math.pi / 2) if up else (ang + math.pi / 2)
        ca, sa = math.cos(rot), math.sin(rot)
        vs = []
        for v in me.vertices:
            x = cx + v.co.x * ca - v.co.y * sa
            z = cz2 + v.co.x * sa + v.co.y * ca
            hit = bvh.ray_cast(Vector((x, -0.7, z)), Vector((0, 1, 0)), 1.6)
            vs.append(hit[0] + hit[1] * 0.004 if hit[0] is not None else Vector((x, -0.14, z)))
        fs = [tuple(p.vertices) for p in me.polygons]
        bpy.data.meshes.remove(me)
        o = G.from_data(f'{name}_{i}', vs, fs, ink, False, fix_normals=False)
        if o.data.polygons and o.data.polygons[0].normal.y > 0:
            o.data.flip_normals()
        out.append(o)
    return out

# ------------------------------------------------------------------ shared pieces
TEE_ROWS = [(.795, .188, .126, -.010), (.806, .192, .128, -.010), (.86, .194, .130, -.012), (.94, .194, .130, -.012),
            (1.02, .194, .130, -.008), (1.08, .198, .136, -.002), (1.10, .200, .140, 0.0), (1.17, .198, .146, .002),
            (1.235, .186, .150, .002), (1.248, .162, .156, .002), (1.257, .155, .152, 0), (1.259, .151, .146, 0), (1.250, .149, .142, 0)]
TEE_SLEEVE = [(.212, .074), (.24, .070), (.28, .067), (.32, .065), (.338, .063), (.334, .058)]


def tee(name, color):
    m = mat(name + '_Fabric', color, 0.85)
    r = G.res('tee', rows=TEE_ROWS, arm_row=6, sleeve=TEE_SLEEVE)
    return torso_garment(name, r['rows'], r['arm_row'], r['sleeve'], (.806, .180, .120, -.010), [m], **G.res('top', n=24, subdiv=1))


WAIST = [(.880, .182, .124), (.868, .184, .125), (.822, .186, .124), (.784, .188, .123)]


def shoes_pair(prefix, upper_rgb, sole_rgb, high=False, lace_rgb=(240, 238, 232)):
    upper = mat(prefix + '_Shoe_Upper', upper_rgb, 0.7)
    sole = mat(prefix + '_Shoe_Sole', sole_rgb, 0.6)
    lace = mat(prefix + '_Shoe_Lace', lace_rgb, 0.7)
    objs = []
    for s in (1, -1):
        up, so, top_h, yaw = sneaker(f'{prefix}_Shoe_{s}', s, upper, sole, high)
        ls = laces(f'{prefix}_Lace_{s}', s, top_h, yaw, lace)
        wf = shoe_weights(s)
        for o in [up, so] + ls:
            set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
            objs.append(o)
        objs_side = (up, so, top_h, yaw)
        yield s, objs_side, [up, so] + ls


# ------------------------------------------------------------------ variants
def variant_a(body):
    src = weight_source([body])
    red = mat('A_Hoodie_Red', (182, 62, 54), 0.9)
    rib = mat('A_Hoodie_Rib', (160, 52, 46), 0.9)
    dark = mat('A_Hoodie_Shadow', (120, 38, 34), 0.9)
    cord = mat('A_Drawstring', (240, 236, 228), 0.7)
    rows = [(.735, .184, .126, -.012), (.750, .192, .132, -.012), (.770, .204, .140, -.014), (.82, .210, .146, -.016),
            (.90, .212, .148, -.016), (.98, .212, .149, -.012), (1.05, .214, .150, -.006), (1.10, .218, .152, 0.0),
            (1.17, .218, .156, .002), (1.235, .206, .158, .002), (1.250, .180, .164, .002), (1.262, .168, .166, .002),
            (1.266, .162, .160, .002), (1.258, .157, .154, .002), (1.246, .157, .152, .002)]
    sleeve = [(.22, .080), (.25, .078), (.29, .076), (.34, .074), (.39, .072), (.44, .070), (.49, .068), (.54, .066), (.575, .064),
              (.586, .056), (.600, .055), (.622, .054), (.630, .050), (.622, .046)]
    rh = G.res('hoodie', rows=rows, arm_row=7, sleeve=sleeve, cuff_from=9)
    hoodie = torso_garment('A_Hoodie', rh['rows'], rh['arm_row'], rh['sleeve'], (.750, .174, .118, -.010), [red, rib], rib_rows=(0,),
                           cuff_from=rh['cuff_from'], **G.res('top', n=24, subdiv=1))
    transfer(hoodie, src)
    out = [hoodie]
    # Hood: soft roll around the back of the neck, open at the front where the drawstrings come out.
    rh = G.res('hood', seg=14, subdiv=1, rings=27)
    vs, fs, rings = [], [], []
    for k in range(rh['rings']):
        phi = math.radians(-152 + 304 * k / (rh['rings'] - 1))
        t = math.cos(phi / 2) ** 2
        R = 0.176 + 0.050 * t
        c = Vector((R * math.sin(phi), 0.004 + R * math.cos(phi) * 1.02, 1.268 - 0.068 * t))
        radial = Vector((math.sin(phi), math.cos(phi), 0))
        a, b = 0.026 + 0.046 * t, 0.034 + 0.066 * t
        ring = []
        for j in range(rh['seg']):
            ang = 2 * math.pi * j / rh['seg']
            ring.append(len(vs)); vs.append(c + radial * (a * math.cos(ang)) + Vector((0, 0, b * math.sin(ang))))
        rings.append(ring)
    for a_, b_ in zip(rings, rings[1:]):
        G.bridge(fs, a_, b_)
    fs.append(tuple(reversed(rings[0]))); fs.append(tuple(rings[-1]))
    hood = G.from_data('A_Hood', vs, fs, red, True, subdiv=rh['subdiv'])
    pouch = G.ellipsoid('A_HoodPouch', (0, 0.170, 1.165), (0.125, 0.032, 0.100), red, **G.res('hood_pouch', seg=20, rings=12))
    G.join(hood, [pouch])
    rigid(hood, 'Spine2'); out.append(hood)
    for s in (1, -1):
        path = [(s * 0.040, -0.168, 1.236), (s * 0.044, -0.192, 1.17), (s * 0.046, -0.198, 1.10), (s * 0.045, -0.199, 1.045)]
        c1 = G.tube(f'A_Drawstring_{s}', path, 0.0062, cord, **G.res('cord', seg=8))
        c2 = G.tube(f'A_Aglet_{s}', [(s * 0.045, -0.199, 1.048), (s * 0.045, -0.199, 1.022)], 0.0082, cord, **G.res('cord', seg=8))
        for o in (c1, c2):
            transfer(o, src, lambda p, w: {P + 'Spine2': 1.0} if p.z > 1.16 else w); out.append(o)
    rp = G.res('pocket', **G.res('big_decal', step=0.010))
    pocket = G.decal('A_Pocket', [(-0.135, 0.795), (0.135, 0.795), (0.108, 0.975), (-0.108, 0.975)], FRONT(), [hoodie], 0.004, red, thickness=0.010, **rp)
    out.append(transfer(pocket, weight_source([hoodie])))
    for s in (1, -1):
        slot = G.decal(f'A_PocketSlot_{s}', [(s * 0.126, 0.822), (s * 0.136, 0.822), (s * 0.111, 0.970), (s * 0.101, 0.970)], FRONT(), [pocket, hoodie], 0.0025, dark)
        out.append(transfer(slot, weight_source([hoodie])))
    denim = mat('A_Shorts_Denim', (84, 112, 152), 0.9)
    shorts = legwear('A_Shorts', WAIST, .742, G.res('shorts_a', legs=[(.70, .084), (.65, .082), (.61, .080), (.600, .076), (.606, .071)])['legs'], [denim],
                     **G.res('bottoms', n=16, subdiv=1))
    out.append(transfer(shorts, src))
    rs = G.res('socks', seg=14, base=(0.090, 0.120, 0.170, 0.220), lip=True)
    sk = socks('A_Socks', mat('A_Socks_White', (242, 240, 234), 0.85), mat('A_Socks_Red', (196, 54, 50), 0.85), [(0.250, 0.263), (0.274, 0.287)],
               seg=rs['seg'], rows=rs['base'], lip=rs['lip'])
    out.append(transfer(sk, src))
    stripe = mat('A_Shoe_Stripe', (196, 62, 54), 0.7)
    for s, (up, so, top_h, yaw), objs in shoes_pair('A', (238, 228, 210), (246, 242, 232)):
        out += objs
        for side_sign in (1, -1):        # outer and inner face of each shoe: two diagonal stripes
            for k, off in enumerate((-0.012, 0.012)):
                pts = [(-0.050 + off, 0.040), (-0.034 + off, 0.040), (0.010 + off, 0.108), (-0.006 + off, 0.108)]
                axes = ((side_sign * 0.7 + s * B.LEG_X, 0, 0), (0, -side_sign, 0), (0, 0, 1), (-side_sign, 0, 0))
                d = G.decal(f'A_ShoeStripe_{s}_{side_sign}_{k}', pts, axes, [up], 0.0018, stripe, **G.res('shoe_stripe'))
                set_weights(d, [shoe_weights(s)(d.matrix_world @ v.co) for v in d.data.vertices]); out.append(d)
    return out


def variant_b(body, face):
    src = weight_source([body])
    out = []
    blue = mat('B_Cap_Blue', (52, 92, 152), 0.8)
    cream = mat('B_Cap_Cream', (240, 234, 218), 0.8)
    saus = mat('B_Sausage', (196, 88, 66), 0.6)
    grill = mat('B_Sausage_Grill', (128, 50, 38), 0.7)
    shine = mat('B_Sausage_Shine', (226, 142, 112), 0.6)
    rc = G.res('cap_crown', seg=32, rows=10)
    crown = dome('B_Cap_Crown', (0, 0.006, 1.672), 0.141, 0.135, 0.136, 1.664, blue, seg=rc['seg'], front=cream, bands=rc['rows'])
    G.solidify(crown, 0.007, offset=1.0)
    vs, fs = [], []
    rp = G.res('cap_peak', u=12, v=6)
    U, V = rp['u'], rp['v']
    for i in range(U + 1):
        th = math.radians(-62 + 124 * i / U)
        u = (i / U) * 2 - 1
        rim = Vector((0.141 * math.sin(th), 0.006 - 0.135 * math.cos(th), 1.668))
        outv = Vector((math.sin(th), -math.cos(th), 0))
        L = 0.122 * math.sqrt(max(0.0, 1 - u * u)) + 0.012
        for j in range(V + 1):
            v = j / V
            vs.append(rim + outv * (L * v) + Vector((0, 0, -0.014 * v - 0.024 * u * u * v)))
    for i in range(U):
        for j in range(V):
            a = i * (V + 1) + j
            fs.append((a, a + V + 1, a + V + 2, a + 1))
    peak = G.from_data('B_Cap_Peak', vs, fs, blue, True)
    G.solidify(peak, 0.009, offset=0.0)
    button = G.ellipsoid('B_Cap_Button', (0, 0.006, 1.672 + 0.136 + 0.003), (0.013, 0.013, 0.006), blue, **G.res('cap_button', seg=16, rings=10))
    logo = hotdog('B_Cap_Logo', 0.0, 1.728, 0.090, 0.033, math.radians(6), [crown], 0.0025, (saus, grill, shine))
    tongue = G.ellipsoid('B_Tongue', (-0.031, B.head_surface_y(-0.031, 1.388, 0.014), 1.382), (0.0175, 0.0075, 0.025), mat('B_Tongue', (226, 112, 120), 0.4),
                         rot=Matrix.Rotation(math.radians(-58), 3, 'X') @ Matrix.Rotation(math.radians(16), 3, 'Y'), **G.res('tongue', seg=16, rings=10))
    tongue_line = G.tube('B_Tongue_Groove', [(-0.031, B.head_surface_y(-0.031, 1.383, 0.024), 1.383), (-0.032, B.head_surface_y(-0.032, 1.370, 0.026), 1.369)],
                         0.0016, mat('B_Tongue_Groove', (176, 74, 84), 0.5), seg=6)
    for o in [crown, peak, button, tongue, tongue_line] + logo:
        rigid(o, 'Head'); out.append(o)
    shirt = tee('B_Tee', (240, 238, 232))
    transfer(shirt, src); out.append(shirt)
    ink = mat('B_Print_Ink', (70, 60, 56), 0.8)
    prints = hotdog('B_Print', 0.0, 1.030, 0.120, 0.046, math.radians(-8), [shirt], 0.0035, (saus, grill, shine))
    for k, (x0, z0, x1, z1) in enumerate([(-0.112, 1.062, -0.090, 1.054), (-0.112, 1.000, -0.090, 1.008), (0.090, 1.054, 0.112, 1.062), (0.090, 1.008, 0.112, 1.000)]):
        d = Vector((x1 - x0, z1 - z0)).normalized(); nrm = Vector((-d.y, d.x)) * 0.0032
        prints.append(G.decal(f'B_Print_Dash_{k}', [(x0 + nrm.x, z0 + nrm.y), (x1 + nrm.x, z1 + nrm.y), (x1 - nrm.x, z1 - nrm.y), (x0 - nrm.x, z0 - nrm.y)],
                              FRONT(), [shirt], 0.0035, ink))
    prints += text_arc('B_Print_GOOD', 'GOOD', 1.030, 0.098, 70, 150, True, ink, shirt)
    prints += text_arc('B_Print_TIMES', 'TIMES', 1.030, 0.098, 210, 330, False, ink, shirt)
    ssrc = weight_source([shirt])
    for o in prints:
        transfer(o, ssrc); out.append(o)
    olive = mat('B_Cargo_Olive', (96, 106, 62), 0.9)
    olive_d = mat('B_Cargo_Pocket', (80, 90, 50), 0.9)
    cargo = legwear('B_CargoShorts', WAIST, .742, G.res('cargo_b', legs=[(.70, .094), (.62, .092), (.55, .090), (.505, .088), (.492, .084), (.499, .079)])['legs'],
                    [olive], **G.res('bottoms', n=16, subdiv=1))
    transfer(cargo, src); out.append(cargo)
    csrc = weight_source([cargo])
    for s in (1, -1):
        axes = ((s * 0.7 + s * B.LEG_X, 0, 0), (0, -s, 0), (0, 0, 1), (-s, 0, 0))
        pk = G.decal(f'B_CargoPocket_{s}', [(-0.052, 0.545), (0.052, 0.545), (0.052, 0.655), (-0.052, 0.655)], axes, [cargo], 0.004, olive_d, thickness=0.009,
                     **G.res('cargo_pocket'))
        fl = G.decal(f'B_CargoFlap_{s}', [(-0.056, 0.640), (0.056, 0.640), (0.056, 0.672), (-0.056, 0.672)], axes, [cargo], 0.014, olive, thickness=0.006,
                     **G.res('cargo_flap'))
        out += [transfer(pk, csrc), transfer(fl, csrc)]
    rs = G.res('socks', seg=14, base=(0.090, 0.120, 0.170, 0.220), lip=True)
    sk = socks('B_Socks', mat('B_Socks_White', (242, 240, 234), 0.85), mat('B_Socks_Blue', (52, 86, 156), 0.85), [(0.240, 0.252), (0.262, 0.274)], top=0.285,
               seg=rs['seg'], rows=rs['base'], lip=rs['lip'])
    out.append(transfer(sk, src))
    white = mat('B_Toe_White', (244, 240, 230), 0.6)
    for s, (up, so, top_h, yaw), objs in shoes_pair('B', (44, 64, 118), (244, 240, 230), high=True):
        out += objs
        cx = s * B.LEG_X
        rt = G.res('toe_cap', n=13, step=0.010)
        cap = G.decal(f'B_ToeCap_{s}', [(cx + 0.060 * math.cos(a), 0.034 + 0.040 * math.sin(a)) for a in [math.pi * k / (rt['n'] - 1) for k in range(rt['n'])]],
                      FRONT(), [up], 0.0022, white, step=rt['step'])
        set_weights(cap, [shoe_weights(s)(cap.matrix_world @ v.co) for v in cap.data.vertices]); out.append(cap)
    return out


def variant_c(body):
    src = weight_source([body])
    out = []
    knit = mat('C_Beanie_Charcoal', (54, 56, 60), 0.95)
    beanie = dome('C_Beanie', (0, 0.006, 1.680), 0.142, 0.136, 0.128, 1.668, knit, seg=36, ribs=0.0026, cuff=(1.668, 1.728, 0.146))
    G.solidify(beanie, 0.007, offset=1.0)
    out.append(rigid(beanie, 'Head'))
    shirt = tee('C_Tee', (60, 60, 64))
    transfer(shirt, src); out.append(shirt)
    brown = mat('C_Trousers_Brown', (100, 74, 56), 0.9)
    cuffm = mat('C_Trousers_Cuff', (112, 84, 64), 0.9)
    trousers = legwear('C_Trousers', WAIST, .742,
                       [(.70, .084), (.60, .082), (.50, .078), (.43, .075), (.34, .072), (.26, .070), (.215, .069)], [brown, cuffm],
                       cuff=[(.204, .078), (.262, .078), (.266, .072)])
    transfer(trousers, src); out.append(trousers)
    canvas = mat('C_Apron_Canvas', (200, 178, 146), 0.95)
    seam = mat('C_Apron_Seam', (170, 148, 116), 0.95)
    bvh = G.bvh_of([shirt, trousers])
    def front_y(x, z):
        hit = bvh.ray_cast(Vector((x, -0.7, z)), Vector((0, 1, 0)), 1.6)
        return hit[0].y if hit[0] is not None else -0.13
    rows = [1.150, 1.120, 1.080, 1.040, 1.000, 0.960, 0.920, 0.890, 0.860, 0.810, 0.750, 0.690, 0.630, 0.570, 0.520]
    cols = 15
    vs, fs, grid, hang = [], [], [], {}
    for r, z in enumerate(rows):
        if z > 1.07:
            half = 0.105
        elif z > 0.89:
            half = 0.105 + 0.075 * smoothstep(1.07, 0.89, z)
        else:
            half = 0.180 + 0.022 * smoothstep(0.89, 0.70, z)
        row = []
        for c in range(cols):
            x = -half + 2 * half * c / (cols - 1)
            y = front_y(x, z) - 0.010
            if z < 0.89:
                y = min(hang.get(c, y), y, front_y(x, min(0.89, z + 0.12)) - 0.010)
            hang[c] = y
            wrap = max(0.0, abs(x) - 0.150) * 1.1 if z < 0.90 else 0.0
            row.append(len(vs)); vs.append((x, y + wrap, z))
        grid.append(row)
    for r in range(len(rows) - 1):
        for c in range(cols - 1):
            fs.append((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    apron = G.from_data('C_Apron', vs, fs, canvas, True)
    G.solidify(apron, 0.006, offset=1.0)
    def skirt(p, w):
        if p.z >= 0.88:
            return w
        t = 0.55 * smoothstep(0.86, 0.52, p.z)
        hips = {P + 'Hips': 1.0 - t, P + 'LeftUpLeg': t / 2, P + 'RightUpLeg': t / 2}
        k = smoothstep(0.90, 0.82, p.z)
        return mix(w, hips, k)
    transfer(apron, weight_source([body, shirt, trousers]), skirt); out.append(apron)
    asrc = weight_source([apron])
    pk = G.decal('C_Apron_Pocket', [(-0.130, 0.580), (0.130, 0.580), (0.130, 0.745), (-0.130, 0.745)], FRONT(), [apron], 0.004, canvas, thickness=0.007)
    hem = G.decal('C_Apron_PocketHem', [(-0.130, 0.731), (0.130, 0.731), (0.130, 0.745), (-0.130, 0.745)], FRONT(), [pk], 0.002, seam)
    out += [transfer(pk, asrc), transfer(hem, asrc)]
    patch = hotdog('C_Apron_Logo', 0.010, 1.000, 0.100, 0.036, math.radians(-12), [apron], 0.003,
                   (mat('C_Logo_Sausage', (196, 92, 70), 0.6), mat('C_Logo_Grill', (128, 54, 40), 0.7), mat('C_Logo_Shine', (226, 146, 116), 0.6)),
                   outline=mat('C_Logo_Outline', (246, 242, 234), 0.7))
    for o in patch:
        out.append(transfer(o, asrc))
    pad = G.decal('C_Notepad', [(0.020, 0.715), (0.072, 0.715), (0.072, 0.790), (0.020, 0.790)], FRONT(), [apron], 0.012, mat('C_Notepad', (242, 240, 232), 0.7), thickness=0.010)
    pen_y = front_y(0.090, 0.76) - 0.030
    pen = G.tube('C_Pen', [(0.090, pen_y, 0.700), (0.092, pen_y - 0.002, 0.800)], 0.0062, mat('C_Pen', (28, 28, 32), 0.3), seg=8)
    out += [transfer(pad, asrc), transfer(pen, asrc)]
    # straps over the shoulders with buttons on the bib, crossed on the back down to the waist tie
    bsrc = weight_source([body, shirt])
    top = projected_path([shirt], [(s * 0.090, 1.140) for s in (1, -1)], FRONT(), 0.012)
    for i, s in enumerate((1, -1)):
        front_pts = projected_path([shirt], [(s * 0.090, 1.14), (s * 0.098, 1.19), (s * 0.104, 1.225)], FRONT(), 0.010)
        over = [Vector((s * 0.108, -0.06, 1.252)), Vector((s * 0.110, 0.00, 1.262)), Vector((s * 0.108, 0.06, 1.252))]
        back_pts = projected_path([shirt, trousers], [(-s * (0.100 - 0.230 * t), 1.220 - 0.340 * t) for t in [k / 6 for k in range(7)]], BACK(), 0.010)
        st = strap(f'C_Strap_{s}', front_pts + over + back_pts, canvas, width=0.026)
        out.append(transfer(st, bsrc))
        btn = G.ellipsoid(f'C_Button_{s}', top[i] + Vector((0, -0.006, 0)), (0.011, 0.005, 0.011), mat('C_Button', (96, 66, 46), 0.4))
        out.append(transfer(btn, asrc))
    waist = [Vector((0.190 * math.sin(a), 0.130 * math.cos(a), 0.880)) for a in [math.radians(-62 + 304 * k / 18) for k in range(19)]]
    wt = strap('C_Strap_Waist', waist, canvas, width=0.024, normal_fn=lambda p: Vector((p.x, p.y, 0)).normalized())
    out.append(transfer(wt, bsrc))
    knot = G.ellipsoid('C_Strap_Knot', (0, 0.140, 0.880), (0.024, 0.012, 0.016), canvas)
    tails = [G.tube(f'C_Strap_Tail_{s}', [(s * 0.012, 0.142, 0.874), (s * 0.034, 0.148, 0.800), (s * 0.038, 0.146, 0.760)], 0.0085, canvas, seg=6) for s in (1, -1)]
    for o in [knot] + tails:
        out.append(transfer(o, bsrc))
    for s, objs_side, objs in shoes_pair('C', (40, 40, 44), (242, 238, 228)):
        out += objs
    return out
