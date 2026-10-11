"""Garment and accessory library for the NPC types (TASK-000246), built on Fedya's Sausage Buddy helpers
(buddy_geo / buddy_body / buddy_clothes). Z up, -Y forward, left = +X, metres. Every piece takes its materials from
the caller, so each type can recolour every garment."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
from buddy_geo import smoothstep, mix, FRONT, BACK, SIDE

P = 'mixamorig:'
HR, HRY, CYL = B.HEAD_R, B.HEAD_RY, B.HEAD_CYL_TOP
H_POLE = CYL + HR * math.pi / 2          # meridian coordinate of the top of the head
SPINE = {P + n for n in ('Hips', 'Spine', 'Spine1', 'Spine2')}


def TOP(z=2.3):
    """Decal axes looking down: outline (x, forward), forward = -y."""
    return ((0, 0, z), (1, 0, 0), (0, -1, 0), (0, 0, -1))

# ------------------------------------------------------------------ materials
def make_mats(prefix, slots):
    """slots: {slot: (rgb, roughness[, 'metal'])} -> {slot: material named PREFIX_Slot}."""
    out = {}
    for slot, spec in slots.items():
        m = G.mat(f'{prefix}_{slot}', spec[0], spec[1])
        if len(spec) > 2 and spec[2] == 'metal':
            b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            b.inputs['Metallic'].default_value = 1.0
        out[slot] = m
    return out


def set_color(material, rgb):
    b = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = G.srgb(rgb)
    material.diffuse_color = G.srgb(rgb)

# ------------------------------------------------------------------ head surface
_NECK = ((1.08, 0.62), (1.13, 0.74), (1.175, 0.90), (1.205, 0.99), (1.25, 1.0))


def neck_k(z):
    if z >= 1.25:
        return 1.0
    if z <= 1.08:
        return 0.62
    for (z0, k0), (z1, k1) in zip(_NECK, _NECK[1:]):
        if z <= z1:
            return k0 + (k1 - k0) * (z - z0) / (z1 - z0)
    return 1.0


def h_of(z):
    """Meridian coordinate of height z: z itself on the cylinder, arc length over the dome."""
    return z if z <= CYL else CYL + HR * math.asin(min(1.0, (z - CYL) / HR))


def head_at(phi, h, off=0.0):
    """Point on the head capsule at azimuth phi (0 = front, +90 deg = left/+X) and meridian coordinate h, pushed
    `off` along the surface normal. Returns (point, normal)."""
    s, c = math.sin(phi), math.cos(phi)
    if h <= CYL:
        k = neck_k(h)
        p = Vector((HR * k * s, -HRY * k * c, h))
        n = Vector((s / HR, -c / HRY, 0.0)).normalized()
    else:
        th = min((h - CYL) / HR, math.pi / 2)
        ct, st = math.cos(th), math.sin(th)
        p = Vector((HR * ct * s, -HRY * ct * c, CYL + HR * st))
        n = Vector((ct * s / HR, -ct * c / HRY, st / HR)).normalized()
    return p + n * off, n


def profile(table):
    """[(azimuth deg 0..180, value)] -> f(phi), cosine-eased, mirrored left/right."""
    t = sorted(table)

    def f(phi):
        a = abs(math.degrees(math.atan2(math.sin(phi), math.cos(phi))))
        if a <= t[0][0]:
            return t[0][1]
        for (a0, v0), (a1, v1) in zip(t, t[1:]):
            if a <= a1:
                u = (1 - math.cos(math.pi * (a - a0) / (a1 - a0))) / 2
                return v0 + (v1 - v0) * u
        return t[-1][1]
    return f


def zprofile(table):
    """Same as profile() but the table holds heights z; returns meridian coordinates."""
    return profile([(a, h_of(z)) for a, z in table])


def shell(name, material, lower, upper=None, off=0.004, thick=0.006, seg=32, rows=8, arc=None):
    """Cloth / hair shell over the head from lower(phi) up to upper(phi) or the pole (meridian coordinates).
    off: float or f(phi, u), u = 0 at the lower edge and 1 at the top. arc=(phi0, phi1) makes an open band.
    Thickness grows outward. Returns (object, lower-edge points)."""
    closed = arc is None
    a0, a1 = (-math.pi, math.pi) if closed else arc
    cols = seg if closed else seg + 1
    pole = upper is None
    nrow = rows - 1 if pole else rows
    vs, fs, grid, edge = [], [], [], []
    for j in range(cols):
        phi = a0 + (a1 - a0) * j / seg
        lo, hi = lower(phi), (H_POLE if pole else upper(phi))
        col = []
        for i in range(nrow + 1):
            u = i / rows
            o = off(phi, u) if callable(off) else off
            p, _ = head_at(phi, lo + (hi - lo) * u, o)
            col.append(len(vs)); vs.append(p)
        grid.append(col); edge.append(vs[col[0]].copy())
    span = cols if closed else cols - 1
    for j in range(span):
        a, b = grid[j], grid[(j + 1) % cols]
        for i in range(nrow):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    if pole:
        o = off(0.0, 1.0) if callable(off) else off
        top = len(vs); vs.append(Vector((0, 0, B.HEAD_TOP + o)))
        for j in range(span):
            fs.append((grid[j][-1], grid[(j + 1) % cols][-1], top))
    ob = G.from_data(name, vs, fs, material, True, fix_normals=False)
    if thick:
        G.solidify(ob, thick, offset=1.0)
    return ob, edge


def ring_loft(name, rows, mats, row_mat=None, seg=32, cap_top=True):
    """Hat-like loft. rows: (z, rx, ry, cy, tilt) rings (z + tilt * cos(phi): tilt > 0 lifts the front) or
    ('fit', lower(phi), off) rings that follow the head surface. A centre vertex closes the top."""
    vs, fs, idx, rings = [], [], [], []
    for r in rows:
        ring = []
        for j in range(seg):
            phi = 2 * math.pi * j / seg - math.pi
            if r[0] == 'fit':
                p, _ = head_at(phi, r[1](phi), r[2](phi) if callable(r[2]) else r[2])
            else:
                z, rx, ry, cy, tilt = r
                p = Vector((rx * math.sin(phi), cy - ry * math.cos(phi), z + tilt * math.cos(phi)))
            ring.append(len(vs)); vs.append(p)
        rings.append(ring)
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
            idx.append(row_mat[k] if row_mat else 0)
    if cap_top:
        c = sum((vs[i] for i in rings[-1]), Vector()) / seg
        top = len(vs); vs.append(c + Vector((0, 0, 0.003)))
        for j in range(seg):
            fs.append((rings[-1][j], rings[-1][(j + 1) % seg], top))
            idx.append(row_mat[-1] if row_mat else 0)
    return G.from_data(name, vs, fs, mats[0], True, idx, list(mats[1:]), fix_normals=False)


def peak(name, material, base, length=0.055, droop=0.016, curve=0.020, span=62.0, off=0.006, thick=0.008, u=10, v=4):
    """Cap peak growing forward from the cap base line base(phi) over +-span degrees."""
    vs, fs = [], []
    for i in range(u + 1):
        t = i / u * 2 - 1
        phi = math.radians(span) * t
        rim, _ = head_at(phi, base(phi), off)
        out = Vector((math.sin(phi), -math.cos(phi), 0))
        L = length * math.sqrt(max(0.0, 1 - t * t)) + 0.010
        for j in range(v + 1):
            w = j / v
            vs.append(rim + out * (L * w) + Vector((0, 0, -droop * w - curve * t * t * w)))
    for i in range(u):
        for j in range(v):
            a = i * (v + 1) + j
            fs.append((a, a + v + 1, a + v + 2, a + 1))
    ob = G.from_data(name, vs, fs, material, True)
    G.solidify(ob, thick, offset=0.0)
    return ob


def box(name, center, half, material, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    m = Matrix.Translation(center) @ (rot or Matrix.Identity(3)).to_4x4() @ Matrix.Diagonal((*half, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return G.from_bm(name, bm, material, smooth=False)


def blob(cx, cz, r, n=12, seed=0, rough=0.35, rot=0.0, sx=1.0):
    """Irregular closed outline (stains, holes)."""
    rnd = random.Random(seed)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 - rough / 2 + rough * rnd.random())
        x, z = rr * math.cos(a) * sx, rr * math.sin(a)
        pts.append((cx + x * math.cos(rot) - z * math.sin(rot), cz + x * math.sin(rot) + z * math.cos(rot)))
    return pts

# ------------------------------------------------------------------ body edits
def remove_ears(body):
    """Hoods and headscarves cover the ears: delete the two ear islands (the head capsule under them is closed)."""
    bm = bmesh.new(); bm.from_mesh(body.data)
    seen, kill = set(), []
    for v in bm.verts:
        if v.index in seen or abs(v.co.x) < 0.15 or abs(v.co.z - B.EAR_C[2]) > 0.07:
            continue
        island, stack = [], [v]
        seen.add(v.index)
        while stack and len(island) < 3000:
            a = stack.pop(); island.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); stack.append(b)
        if len(island) < 3000 and all(abs(q.co.z - B.EAR_C[2]) < 0.08 and abs(q.co.x) > 0.09 for q in island):
            kill += island
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(body.data); bm.free()
    return len(kill)


def reshape(objs, belly=0.0, thin=0.0, muscle=0.0):
    """Fat belly / thin waist as one smooth displacement applied to the body and every garment alike (so layers keep
    their gaps). Only spine/hips-weighted vertices move; arms, legs and the head stay as built.
    muscle (TASK-000270, bodybuilder / fitness coach): broader chest and lats, a slight waist taper, and bulging
    shoulders, upper arms, forearms and thighs (those move radially round their T-pose bone axis)."""
    if not belly and not thin and not muscle:
        return
    for ob in objs:
        names = {g.index: g.name for g in ob.vertex_groups}
        for v in ob.data.vertices:
            if muscle:
                _muscle_limbs(v, names, muscle)
            ws = sum(g.weight for g in v.groups if names.get(g.group) in SPINE)
            if ws < 1e-3:
                continue
            x, y, z = v.co
            yy = y + 0.01
            r = math.hypot(x, yy)
            if r < 1e-4:
                continue
            c = -yy / r                          # 1 at the front, -1 at the back
            d = Vector((x / r, yy / r, 0.0))
            amt, sag = 0.0, 0.0
            if belly:
                bz = math.exp(-((z - 0.935) / (0.105 if z < 0.935 else 0.125)) ** 2)
                front = max(0.0, c) ** 1.2
                amt += belly * bz * (0.030 + 0.100 * front - 0.012 * max(0.0, -c))
                sag = belly * bz * front * 0.018
            if thin:
                tz = smoothstep(0.74, 0.86, z) * (1 - smoothstep(1.10, 1.20, z))
                amt -= thin * tz * (0.022 + 0.008 * max(0.0, c))
            if muscle:
                side = abs(x) / r
                chest = math.exp(-((z - 1.100) / 0.070) ** 2)
                lats = math.exp(-((z - 1.010) / 0.060) ** 2)
                amt += muscle * (chest * (0.034 * max(0.0, c) ** 1.5 + 0.030 * side ** 2) + lats * 0.018 * side ** 2)
                amt -= muscle * 0.010 * math.exp(-((z - 0.900) / 0.050) ** 2)
            v.co += (d * amt + Vector((0, 0, -sag))) * ws



ARM_MUSCLE = {P + s + n for s in ('Left', 'Right') for n in ('Shoulder', 'Arm', 'ForeArm')}
THIGH_MUSCLE = {P + s + 'UpLeg' for s in ('Left', 'Right')}


def _bump(x, c, w):
    return math.exp(-((x - c) / w) ** 2)


def _muscle_limbs(v, names, muscle):
    """Radial bulge of the T-pose arms (axis y = 0, z ~ 1.165, along x) and thighs (axis x = +-LEG_X, y = 0, along z)."""
    wa = sum(g.weight for g in v.groups if names.get(g.group) in ARM_MUSCLE)
    wl = sum(g.weight for g in v.groups if names.get(g.group) in THIGH_MUSCLE)
    x, y, z = v.co
    if wa > 1e-3:
        ax = abs(x)
        prof = 0.020 * _bump(ax, 0.225, 0.060) + 0.028 * _bump(ax, 0.320, 0.075) + 0.016 * _bump(ax, 0.500, 0.070)
        prof *= 1.0 - smoothstep(0.58, 0.63, ax)                 # nothing at the wrist: hands and hand props stay put
        zc = 1.165 - (ax - 0.20) * 0.016
        rad = Vector((0.0, y, z - zc))
        if rad.length > 1e-4:
            v.co += rad.normalized() * (muscle * prof * wa)
    if wl > 1e-3:
        cx = B.LEG_X if x >= 0 else -B.LEG_X
        rad = Vector((x - cx, y, 0.0))
        if rad.length > 1e-4:
            v.co += rad.normalized() * (muscle * 0.014 * _bump(z, 0.62, 0.11) * wl)


# ------------------------------------------------------------------ hand / head props (TASK-000270)
REST = None      # set by build_buddy.py before dressing: bone name -> rest matrix (armature space, rig at the origin)


def bone_rest(bone):
    """Rest (T-pose) matrix of a Mixamo bone, e.g. bone_rest('RightHand'); its Y axis runs head -> tail."""
    return REST[P + bone]


def to_bone(ob, bone, local=None):
    """Bake a mesh modelled in a bone's local frame (Y along the bone) into armature space at the T-pose."""
    m = bone_rest(bone) @ (local if local is not None else Matrix())
    ob.data.transform(m)
    ob.data.update()
    return ob


def prop(ob, bone='RightHand'):
    """A carried prop (bucket, bottle, stick, phone, straw...): rigid on one bone and exported as the separate
    'Props' mesh, so the game can hide or drop it; it is not reshaped and does not count for floor contact."""
    C.rigid(ob, bone)
    ob['ov_prop'] = True
    ob['ov_prop_bone'] = bone
    return ob


def prop_group(bone):
    """Export mesh of a carried prop: one per hand (forearm pieces such as a wrist loop go with their hand), else per bone."""
    for side in ('Left', 'Right'):
        if bone in (side + 'Hand', side + 'ForeArm'):
            return 'Props_' + side + 'Hand'
    return 'Props_' + bone

def head_target(skin):
    """Temporary bare head capsule (no nose / ears) for projecting face decals; delete it afterwards."""
    return B.head_capsule(skin)

# ------------------------------------------------------------------ tops
def top(name, rows, arm_row, sleeve, hem_inner, mats, row_mat=None, sleeve_mat=None, hem_mat=0, cut=None, armhole=True):
    """Fedya's torso_garment with per-row / per-sleeve-row materials and an optional cut(face centre) predicate."""
    r = G.res('top', n=24, subdiv=1)
    n, subdiv = r['n'], r['subdiv']
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
            if armhole and k in (arm_row, arm_row + 1) and j in side:
                continue
            q = (rings[k][j], rings[k][(j + 1) % n], rings[k + 1][(j + 1) % n], rings[k + 1][j])
            if cut is not None and cut(sum((Vector(vs[i]) for i in q), Vector()) / 4):
                continue
            fs.append(q)
            idx.append(row_mat[k] if row_mat else 0)
    if sleeve:
        h = n // 8
        for sign, c in ((1, 0), (-1, n // 2)):
            js = [(c + j) % n for j in range(-h, h + 1)]
            boundary = ([rings[arm_row][j] for j in js] + [rings[arm_row + 1][js[-1]], rings[arm_row + 2][js[-1]]]
                        + [rings[arm_row + 2][j] for j in reversed(js[:-1])] + [rings[arm_row + 1][js[0]]])
            start = -3 * math.pi / 4 if sign == 1 else -math.pi / 4
            angles = [start + sign * j * 2 * math.pi / len(boundary) for j in range(len(boundary))]
            last = boundary
            for k, (x, rr) in enumerate(sleeve):
                new = []
                for a in angles:
                    new.append(len(vs)); vs.append((sign * x, rr * math.cos(a), B.arm_z(x) + rr * 1.02 * math.sin(a)))
                for j in range(len(new)):
                    fs.append((last[j], last[(j + 1) % len(new)], new[(j + 1) % len(new)], new[j]))
                    idx.append(sleeve_mat[k] if sleeve_mat else 0)
                last = new
    if hem_inner is not None:
        z, rx, ry, dy = hem_inner
        inner = []
        for j in range(n):
            a = j * 2 * math.pi / n
            inner.append(len(vs)); vs.append((rx * math.cos(a), dy + ry * math.sin(a), z))
        for j in range(n):
            fs.append((inner[j], inner[(j + 1) % n], rings[0][(j + 1) % n], rings[0][j]))
            idx.append(hem_mat)
    return G.from_data(name, vs, fs, mats[0], True, idx, list(mats[1:]), subdiv=subdiv)


def lerp_row(rows, z):
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0] and b[0] > a[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return (z,) + tuple(a[i] + (b[i] - a[i]) * t for i in range(1, len(a)))
    raise ValueError(z)


def quilt(rows, arm_z, step=0.056, puff=0.006, half=0.0035):
    """Quilted padding (telogreika) below the armhole row: puffy panels between thin dented stitch bands.
    Returns rows, per-band materials (1 = stitch band) and the new armhole row index."""
    rest = [r for r in rows if r[0] >= arm_z - 1e-6 or r[0] > 1.2]
    out, bands = [rows[0]], []

    def add(z, extra, m):
        r = lerp_row(rows, z)
        out.append((z, r[1] + extra, r[2] + extra, r[3])); bands.append(m)
    prev = rows[0][0]
    z = prev + step * 0.75
    while z < arm_z - step * 0.45:
        add((prev + z - half) / 2, puff, 0)
        add(z - half, 0.0, 0)
        add(z + half, 0.0, 1)
        prev = z + half
        z += step
    add((prev + arm_z) / 2, puff * 0.6, 0)
    arm = len(out)
    for r in rest:
        out.append(r); bands.append(0)
    return out, bands, arm


def quilt_sleeve(sleeve, x_end, step=0.055, puff=0.005, half=0.003):
    """Quilted sleeve rows up to x_end; returns rows and per-row materials (1 = stitch band)."""
    def r_at(x):
        for (xa, ra), (xb, rb) in zip(sleeve, sleeve[1:]):
            if xa <= x <= xb and xb > xa:
                return ra + (rb - ra) * (x - xa) / (xb - xa)
        return sleeve[-1][1]
    out, mats = [sleeve[0]], [0]
    prev = sleeve[0][0]
    x = prev + step * 0.7
    while x < x_end - step * 0.4:
        out += [((prev + x - half) / 2, r_at((prev + x - half) / 2) + puff), (x - half, r_at(x - half)), (x + half, r_at(x + half))]
        mats += [0, 0, 1]
        prev = x + half
        x += step
    out.append(((prev + x_end) / 2, r_at((prev + x_end) / 2) + puff * 0.6)); mats.append(0)
    for xs, rs in sleeve:
        if xs >= x_end:
            out.append((xs, rs)); mats.append(0)
    return out, mats


def collar(name, material, z0=1.250, r0=(0.152, 0.146), z1=1.278, r1=(0.157, 0.151), z2=1.236, r2=(0.176, 0.170),
           open_deg=24.0, tip=0.034, seg=24, thick=0.004):
    """Fold-down collar: stand from the neckline up to the fold, then the leaf down over the shoulders; open at the
    front, where the two points droop."""
    vs, fs, cols = [], [], []
    a0, a1 = math.radians(open_deg), math.radians(360 - open_deg)
    for j in range(seg + 1):
        phi = a0 + (a1 - a0) * j / seg
        k = max(0.0, math.cos(phi)) ** 6          # 1 near the collar points
        sd = math.sin(phi) ** 2                   # 1 over the shoulders
        rows = ((z0, r0[0], r0[1]), (z1, r1[0], r1[1]),
                (z2 + 0.012 * sd - tip * k, r2[0] + 0.010 * k, r2[1] + 0.004 * k))
        col = []
        for z, rx, ry in rows:
            col.append(len(vs)); vs.append(Vector((rx * math.sin(phi), -ry * math.cos(phi), z)))
        cols.append(col)
    for j in range(seg):
        a, b = cols[j], cols[j + 1]
        for i in range(2):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    ob = G.from_data(name, vs, fs, material, True, fix_normals=False)
    G.solidify(ob, thick, offset=0.0)
    return ob

# shared torso profiles (z, rx, ry, dy)
TEE = C.BASE_TEE_ROWS                 # arm row 6
SLEEVE_SHORT = C.TEE_SLEEVE
SLEEVE_LONG = [(.212, .072), (.25, .067), (.30, .062), (.36, .058), (.43, .055), (.50, .052), (.56, .049), (.590, .047),
               (.600, .045), (.597, .040)]
# shirt tucked into trousers: the lower rows step inside the waistband, a little blousing above it
TUCKED = [(.842, .172, .116, -.006), (.862, .175, .118, -.008), (.900, .190, .126, -.010), (.94, .194, .130, -.012)] + \
         [r for r in TEE if r[0] >= 1.0]                                     # arm row 6
JACKET = [(.700, .208, .143, -.012), (.716, .210, .144, -.012), (.78, .209, .143, -.013), (.86, .208, .142, -.013),
          (.94, .208, .142, -.012), (1.02, .209, .143, -.008), (1.08, .213, .149, -.002), (1.10, .215, .153, 0.0),
          (1.17, .213, .159, .002), (1.235, .201, .163, .002), (1.250, .177, .168, .002), (1.262, .167, .165, .002),
          (1.266, .161, .159, 0.0), (1.258, .157, .153, 0.0)]        # arm row 7
JACKET_SLEEVE = [(.222, .080), (.26, .074), (.31, .069), (.37, .065), (.43, .062), (.50, .059), (.555, .056), (.580, .055),
                 (.588, .051), (.585, .047)]
HOODIE = [(.735, .184, .126, -.012), (.750, .192, .132, -.012), (.770, .204, .140, -.014), (.82, .210, .146, -.016),
          (.90, .212, .148, -.016), (.98, .212, .149, -.012), (1.05, .214, .150, -.006), (1.10, .218, .152, 0.0),
          (1.17, .218, .156, .002), (1.235, .206, .158, .002), (1.250, .180, .164, .002), (1.262, .168, .166, .002),
          (1.266, .162, .160, .002), (1.258, .157, .154, .002), (1.246, .157, .152, .002)]     # Fedya's A hoodie, arm row 7
HOODIE_SLEEVE = [(.22, .080), (.25, .078), (.29, .076), (.34, .074), (.39, .072), (.44, .070), (.49, .068), (.54, .066),
                 (.575, .064), (.586, .056), (.600, .055), (.622, .054), (.630, .050), (.622, .046)]


def tank_top(name, material, body, z_top=1.118):
    """Vest top ('mayka'): body up to the chest with deep armholes, two straps over the shoulders."""
    rows = [r for r in TEE if r[0] <= 1.10] + [lerp_row(TEE, z_top)]

    def cut(p):
        a = math.degrees(math.atan2(abs(p.y + 0.004), abs(p.x) * 1.45))     # 0 at the side, 90 front / back
        return p.z > 1.03 and a < 56
    ob = top(name, rows, 0, None, (.806, .184, .124, -.004), [material], cut=cut, armhole=False)
    out = [ob]
    bvh = G.bvh_of([body])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    for s in (1, -1):
        raw = [(0.098, -0.150, 1.104), (0.128, -0.112, 1.160), (0.152, -0.050, 1.198), (0.160, 0.008, 1.208),
               (0.152, 0.062, 1.196), (0.130, 0.106, 1.156), (0.102, 0.140, 1.104)]
        pts = [on(Vector((s * x, y, z)), 0.004)[0] for x, y, z in raw]
        out.append(C.strap(f'{name}_Strap_{s}', pts, material, width=0.032, thick=0.005, normal_fn=lambda q: on(q, 0.0)[1]))
    return out


# ------------------------------------------------------------------ bottoms
WAIST = C.WAIST
LEGS_LONG = [(.70, .084), (.60, .082), (.50, .078), (.43, .075), (.34, .073), (.26, .072), (.19, .073), (.135, .075), (.125, .070)]
LEGS_TUCKED = [(.70, .084), (.60, .082), (.50, .078), (.43, .074), (.36, .070), (.33, .066), (.325, .060)]
LEGS_SWEAT = [(.70, .094), (.60, .092), (.50, .088), (.43, .085), (.34, .080), (.26, .074), (.20, .066)]
SWEAT_CUFF = [(.186, .054), (.162, .050), (.160, .046)]
LEGS_ANKLE = [(.70, .084), (.60, .082), (.50, .078), (.43, .075), (.34, .072), (.26, .070), (.215, .069)]
ANKLE_CUFF = [(.204, .078), (.262, .078), (.266, .072)]
LEGS_RUN = [(.70, .090), (.676, .092), (.668, .086)]
LEGS_TIGHTS = [(.70, .062), (.60, .0565), (.50, .053), (.43, .050), (.34, .048), (.22, .0455), (.12, .0435), (.095, .0435)]


def bottoms(name, legs, mats, cuff=None, waist=WAIST):
    return C.legwear(name, waist, .742, legs, mats, cuff=cuff, **G.res('bottoms', n=16, subdiv=1))


def leg_stripes(prefix, target, material, offsets=(-0.011, 0.011), width=0.007, z0=0.14, z1=0.86):
    """Stripes down the outer side of both legs (track pants, police piping)."""
    out = []
    for s in (1, -1):
        for k, c in enumerate(offsets):
            pts = [(c - width / 2, z0), (c + width / 2, z0), (c + width / 2, z1), (c - width / 2, z1)]
            out.append(G.decal(f'{prefix}_{s}_{k}', pts, SIDE(s), [target], 0.0025, material, step=0.012))
    return out


def skirt(name, material, rows=None, seg=32):
    rows = rows or [(0.892, 0.186, 0.127, -0.004), (0.86, 0.193, 0.132, -0.006), (0.80, 0.207, 0.143, -0.008),
                    (0.70, 0.224, 0.158, -0.010), (0.60, 0.240, 0.172, -0.010), (0.50, 0.253, 0.184, -0.010),
                    (0.40, 0.265, 0.195, -0.010), (0.355, 0.268, 0.198, -0.010), (0.362, 0.260, 0.190, -0.010)]
    secs = [((0, dy, z), (1, 0, 0), (0, 1, 0), rx, ry) for z, rx, ry, dy in rows]
    ob = G.loft(name, secs, material, seg=seg, cap_start=False, cap_end=False)
    for p in ob.data.polygons:
        p.use_smooth = True

    def w(p):
        t = 0.62 * smoothstep(0.84, 0.40, p.z)
        k = smoothstep(-0.07, 0.07, p.x)
        return {P + 'Hips': 1 - t, P + 'LeftUpLeg': t * k, P + 'RightUpLeg': t * (1 - k)}
    C.set_weights(ob, [w(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return ob

# ------------------------------------------------------------------ footwear
def shoes(prefix, upper_m, sole_m, lace_m=None, high=False):
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Shoe_{s}', s, upper_m, sole_m, high)
        parts = [up, so]
        if lace_m is not None:
            parts += C.laces(f'{prefix}_Lace_{s}', s, top_h, yaw, lace_m)
        wf = C.shoe_weights(s)
        for o in parts:
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += parts
    return out


def boot_shafts(prefix, material, top=0.40, seg=16):
    """Rubber-boot shafts up to just under the knee, over the shoe-shaped foot."""
    out = []
    for s in (1, -1):
        side = 'Left' if s > 0 else 'Right'
        cx = s * B.LEG_X
        rows = [(0.095, 0.060), (0.16, 0.067), (0.24, 0.072), (0.32, 0.078), (top - 0.008, 0.083), (top, 0.084),
                (top + 0.003, 0.079), (top - 0.006, 0.073)]
        secs = [((cx, 0.006, z), (1, 0, 0), (0, 1, 0), r, r * 0.96) for z, r in rows]
        ob = G.loft(f'{prefix}_Shaft_{s}', secs, material, seg=seg, cap_start=False, cap_end=False)
        wf = C.shoe_weights(s)
        C.set_weights(ob, [mix(wf(p), {P + side + 'Leg': 1.0}, smoothstep(0.15, 0.26, p.z))
                           for p in (ob.matrix_world @ v.co for v in ob.data.vertices)])
        out.append(ob)
    return out


def wrap_band(name, target, cx, ys, material, zc=0.034, off=0.004, n=13, thick=0.006):
    """Band hugging the top half of a foot-like mesh: for each y a ring of rays shot inward from the sides and the
    top toward the axis (cx, y, zc)."""
    bvh = G.bvh_of([target])
    vs, fs, rows = [], [], []
    for y in ys:
        row = []
        for k in range(n):
            a = math.pi * k / (n - 1)
            d = Vector((math.cos(a), 0.0, math.sin(a)))
            o = Vector((cx, y, zc)) + d * 0.3
            hit = bvh.ray_cast(o, -d, 0.6)
            p = hit[0] + hit[1] * off if hit[0] is not None else Vector((cx, y, zc)) + d * 0.08
            row.append(len(vs)); vs.append(p)
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for k in range(n - 1):
            fs.append((a[k], a[k + 1], b[k + 1], b[k]))
    ob = G.from_data(name, vs, fs, material, True)
    G.solidify(ob, thick, offset=0.0)
    return ob


def slides(prefix, sock_m, slide_m):
    """Socks in slides: the shoe-shaped foot in the sock colour on a chunky slide sole (as thick as the sneaker sole,
    so the shared clips keep the feet on the floor), a wide strap over the instep."""
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Foot_{s}', s, sock_m, slide_m)
        cx = s * B.LEG_X
        strap = wrap_band(f'{prefix}_Strap_{s}', up, cx - s * 0.006, [-0.022, -0.050, -0.078, -0.104], slide_m, zc=0.047)
        wf = C.shoe_weights(s)
        for o in (up, so, strap):
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += [up, so, strap]
    return out


def plain_socks(name, material, top=0.280):
    sk = C.socks(name, material, material, [], top=top, **G.res('socks', seg=14))
    sk.data.materials.pop()
    return sk

# ------------------------------------------------------------------ headwear
HAIRLINE = zprofile([(0, 1.692), (30, 1.684), (55, 1.646), (80, 1.586), (100, 1.556), (130, 1.505), (180, 1.470)])


def hair(name, material, kind='slick', upper=None):
    """'slick' combed helmet, 'buzz' very short. upper(phi) limits it to a band under a hat."""
    if kind == 'buzz':
        ob, _ = shell(name, material, HAIRLINE, upper, off=0.0015, thick=0.0035, seg=32, rows=8)
    else:
        ob, _ = shell(name, material, HAIRLINE, upper,
                      off=lambda phi, u: 0.003 + 0.007 * smoothstep(0.0, 0.45, u) * (0.6 + 0.4 * max(0.0, math.cos(phi))),
                      thick=0.008, seg=32, rows=8)
    return C.rigid(ob, 'Head')


def hair_part(name, material, target, x=0.050):
    pts = [(x - 0.004, 0.092), (x + 0.004, 0.092), (x - 0.008, -0.060), (x - 0.014, -0.060)]
    return C.rigid(G.decal(name, pts, TOP(), [target], 0.0015, material, step=0.010), 'Head')


def hair_ring(name, material):
    """Bald on top, a fluffy horseshoe of hair round the back of the head with a ragged lower edge."""
    base = zprofile([(70, 1.540), (110, 1.512), (180, 1.492)])
    lo = lambda phi: base(phi) + 0.007 * abs(2 * ((math.degrees(phi) / 9.0) % 1.0) - 1)
    hi = zprofile([(70, 1.546), (86, 1.582), (130, 1.586), (180, 1.574)])
    ob, _ = shell(name, material, lo, hi, off=lambda phi, u: 0.004 + 0.007 * math.sin(math.pi * u), thick=0.008, seg=36, rows=3,
                  arc=(math.radians(70), math.radians(290)))
    return C.rigid(ob, 'Head')


def ponytail(prefix, hair_m, tie_m):
    out = [hair(prefix + '_Hair', hair_m, 'slick')]
    path = [(0, 0.128, 1.655), (0, 0.168, 1.620), (0, 0.205, 1.560), (0, 0.222, 1.490), (0, 0.214, 1.420), (0, 0.196, 1.360)]
    prof = [0.026, 0.030, 0.034, 0.030, 0.022, 0.010]
    out.append(G.tube(prefix + '_Tail', path, lambda i, n: prof[i], hair_m, seg=12))
    out.append(G.tube(prefix + '_Tie', [(0, 0.150, 1.648), (0, 0.172, 1.628)], 0.030, tie_m, seg=12))
    return [C.rigid(o, 'Head') for o in out]


def fringe(prefix, material, ragged=((1.664, 1.682), 11.0)):
    """Greasy messy fringe sticking out from under a hood: a hair band over the forehead with a ragged lower edge."""
    (lo_a, lo_b), period = ragged

    def lower(phi):
        d = math.degrees(phi)
        t = (d / period) % 1.0
        z = lo_a + (lo_b - lo_a) * abs(2 * t - 1)               # zigzag strands
        return h_of(z)
    upper = lambda phi: h_of(1.716)
    ob, _ = shell(prefix, material, lower, upper, off=0.006, thick=0.007, seg=28, rows=3,
                  arc=(math.radians(-48), math.radians(48)))
    return [C.rigid(ob, 'Head')]


def flat_cap(prefix, material):
    base = zprofile([(0, 1.668), (90, 1.650), (180, 1.632)])
    rows = [('fit', base, 0.005), (1.690, 0.162, 0.163, -0.010, 0.012), (1.724, 0.170, 0.178, -0.020, -0.002),
            (1.750, 0.152, 0.164, -0.024, -0.010), (1.766, 0.100, 0.112, -0.018, -0.010), (1.773, 0.034, 0.038, -0.012, -0.006)]
    crown = ring_loft(prefix + '_Crown', rows, [material], seg=32)
    pk = peak(prefix + '_Peak', material, base, length=0.050, droop=0.014, curve=0.018, span=58, off=0.008, thick=0.008)
    btn = G.ellipsoid(prefix + '_Button', (0, -0.012, 1.778), (0.012, 0.012, 0.005), material, seg=10, rings=6)
    return [C.rigid(o, 'Head') for o in (crown, pk, btn)]


def police_cap(prefix, cap_m, band_m, visor_m, gold_m):
    base = zprofile([(0, 1.667), (90, 1.656), (180, 1.642)])
    rows = [('fit', base, 0.004), (1.703, 0.150, 0.146, 0.0, 0.012), (1.709, 0.166, 0.163, -0.003, 0.014),
            (1.730, 0.214, 0.220, -0.010, 0.022), (1.739, 0.218, 0.224, -0.011, 0.025), (1.748, 0.219, 0.225, -0.012, 0.028),
            (1.760, 0.202, 0.208, -0.012, 0.031), (1.767, 0.130, 0.134, -0.010, 0.030), (1.769, 0.040, 0.042, -0.008, 0.029)]
    crown = ring_loft(prefix + '_Crown', rows, [cap_m, band_m], row_mat=[1, 0, 0, 0, 1, 0, 0, 0], seg=32)
    visor = peak(prefix + '_Visor', visor_m, base, length=0.062, droop=0.024, curve=0.016, span=64, off=0.006, thick=0.007)
    p, _ = head_at(0.0, h_of(1.692), 0.012)
    cockade = G.ellipsoid(prefix + '_Cockade', p, (0.012, 0.005, 0.014), gold_m, seg=12, rings=8)
    cord = G.tube(prefix + '_Cord', [head_at(math.radians(a), h_of(1.674), 0.0075)[0] for a in range(-56, 57, 8)], 0.0028, gold_m, seg=6)
    return [C.rigid(o, 'Head') for o in (crown, visor, cockade, cord)]


def bucket_hat(prefix, material):
    base = zprofile([(0, 1.676), (90, 1.660), (180, 1.646)])
    rows = [('fit', base, 0.006), (1.712, 0.151, 0.147, 0.0, 0.010), (1.746, 0.135, 0.131, 0.0, 0.006),
            (1.768, 0.090, 0.088, 0.0, 0.003), (1.776, 0.030, 0.030, 0.0, 0.0)]
    crown = ring_loft(prefix + '_Crown', rows, [material], seg=32)
    droop = profile([(0, 0.010), (90, 0.022), (180, 0.026)])
    vs, fs, seg = [], [], 32
    rings = [[], [], []]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        p0, _ = head_at(phi, base(phi), 0.006)
        out = Vector((math.sin(phi), -math.cos(phi), 0))
        for k, (w, d) in enumerate(((0.0, 0.0), (0.034, 0.45), (0.066, 1.0))):
            rings[k].append(len(vs)); vs.append(p0 + out * w + Vector((0, 0, -droop(phi) * d)))
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    brim = G.from_data(prefix + '_Brim', vs, fs, material, True, fix_normals=False)
    G.solidify(brim, 0.006, offset=0.0)
    return [C.rigid(o, 'Head') for o in (crown, brim)]


def beanie(prefix, material):
    base = zprofile([(0, 1.668), (90, 1.640), (180, 1.616)])
    back = lambda phi: (1 - math.cos(phi)) / 2
    up = lambda dz: (lambda phi: base(phi) + dz)
    rows = [('fit', base, 0.006), ('fit', up(0.003), 0.017), ('fit', up(0.046), 0.018), ('fit', up(0.050), 0.011),
            ('fit', lambda phi: h_of(1.700) + 0.6 * (base(phi) - h_of(1.668)), lambda phi: 0.012 + 0.010 * back(phi)),
            ('fit', lambda phi: 1.752, lambda phi: 0.013 + 0.018 * back(phi)),
            ('fit', lambda phi: 1.790, lambda phi: 0.014 + 0.024 * back(phi)),
            ('fit', lambda phi: 1.818, lambda phi: 0.015 + 0.020 * back(phi))]
    ob = ring_loft(prefix, rows, [material], seg=32)
    return [C.rigid(ob, 'Head')]


def headband(prefix, material, height=0.032):
    lo = zprofile([(0, 1.670), (90, 1.640), (180, 1.606)])
    vs, fs, seg = [], [], 32
    rings = [[], [], [], []]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        h0 = lo(phi)
        for k, (dh, off) in enumerate(((0, 0.015), (0, 0.024), (height, 0.024), (height, 0.015))):
            p, _ = head_at(phi, h0 + dh, off)
            rings[k].append(len(vs)); vs.append(p)
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    return [C.rigid(G.from_data(prefix, vs, fs, material, True), 'Head')]


def headscarf(prefix, scarf_m, dot_m):
    """Babushka headscarf: frames the face, covers the ears, tied under the chin; white polka dots."""
    lower = zprofile([(0, 1.684), (32, 1.678), (50, 1.570), (62, 1.430), (76, 1.335), (180, 1.300)])
    back = lambda phi: (1 - math.cos(phi)) / 2
    sc, _ = shell(prefix + '_Scarf', scarf_m, lower, off=lambda phi, u: 0.012 + 0.014 * back(phi) * u, thick=0.007, seg=36, rows=9)
    out = [sc]
    path = [head_at(math.radians(a), 1.330, 0.016)[0] for a in range(-74, 75, 6)]
    out.append(C.strap(prefix + '_ChinBand', path, scarf_m, width=0.036, thick=0.006,
                       normal_fn=lambda p: Vector((p.x / HR, p.y / HRY, 0)).normalized()))
    kp, _ = head_at(0.0, 1.326, 0.034)
    out.append(G.ellipsoid(prefix + '_Knot', kp, (0.028, 0.017, 0.021), scarf_m, seg=14, rings=8))
    for s in (1, -1):
        out.append(G.ellipsoid(f'{prefix}_KnotTail_{s}', kp + Vector((s * 0.018, -0.004, -0.032)), (0.013, 0.007, 0.030), scarf_m,
                               rot=Matrix.Rotation(math.radians(s * 24), 3, 'Y'), seg=10, rings=6))
    dots = []
    for s in (1, -1):
        for u, v in ((-0.060, 1.380), (0.010, 1.400), (-0.100, 1.470), (-0.030, 1.480), (0.030, 1.560), (-0.075, 1.560),
                     (-0.010, 1.640), (-0.090, 1.650)):
            dots.append(G.decal(f'{prefix}_DotS_{s}_{len(dots)}', C.ellipse(u * s, v, 0.011, 0.011, 10), SIDE(s), [sc], 0.002, dot_m))
    for u, v in ((-0.090, 1.360), (0.0, 1.380), (0.090, 1.360), (-0.050, 1.460), (0.050, 1.460), (-0.095, 1.540), (0.0, 1.550),
                 (0.095, 1.540), (-0.050, 1.630), (0.050, 1.630), (0.0, 1.700)):
        dots.append(G.decal(f'{prefix}_DotB_{len(dots)}', C.ellipse(u, v, 0.011, 0.011, 10), BACK(), [sc], 0.002, dot_m))
    for u, v in ((-0.040, 0.050), (0.040, 0.050), (0.0, -0.010), (-0.060, -0.050), (0.060, -0.050)):
        dots.append(G.decal(f'{prefix}_DotT_{len(dots)}', C.ellipse(u, v, 0.011, 0.011, 10), TOP(), [sc], 0.002, dot_m))
    return [C.rigid(o, 'Head') for o in out + dots]


def hood_up(prefix, material, rim_m=None):
    """Hood pulled up: a baggy shell round the head, open for the face, with a soft rim; it meets the hoodie at the
    neck, so the lower part follows the chest."""
    lower = zprofile([(0, 1.712), (38, 1.700), (52, 1.585), (64, 1.405), (80, 1.300), (180, 1.262)])
    back = lambda phi: (1 - math.cos(phi)) / 2
    sh, edge = shell(prefix + '_Hood', material, lower, off=lambda phi, u: 0.020 + 0.024 * back(phi) * (u ** 0.7), thick=0.010,
                     seg=36, rows=10)
    rim_pts = [head_at(math.radians(a), lower(math.radians(a)), 0.026)[0] for a in range(-100, 101, 5)]
    rim = G.tube(prefix + '_HoodRim', rim_pts, 0.012, rim_m or material, seg=8)
    out = []
    for o in (sh, rim):
        C.set_weights(o, [{P + 'Head': smoothstep(1.27, 1.40, p.z), P + 'Spine2': 1 - smoothstep(1.27, 1.40, p.z)}
                          for p in (o.matrix_world @ v.co for v in o.data.vertices)])
        out.append(o)
    return out

# ------------------------------------------------------------------ face extras
def mustache(prefix, material, droop=0.0, size=1.0):
    out = []
    for s in (1, -1):
        base = [(0.004, 1.447), (0.022, 1.447), (0.042, 1.441), (0.060, 1.431), (0.072, 1.419 - droop * 0.5), (0.079, 1.405 - droop)]
        n = len(base)
        rad = [(0.006 + 0.008 * math.sin(math.pi * (i + 0.6) / (n + 0.2))) * size for i in range(n)]
        pts = [Vector((s * x, B.head_surface_y(s * x, z, 0.004 + rad[i]), z)) for i, (x, z) in enumerate(base)]
        out.append(C.rigid(G.tube(f'{prefix}_{s}', pts, lambda i, k: rad[i], material, seg=10), 'Head'))
    return out


def eye_bags(prefix, material, head):
    out = []
    for s in (1, -1):
        cx, cz = s * B.EYE_C[0], B.EYE_C[2]
        outer = [(cx + 0.054 * math.cos(a), cz - 0.006 + 0.064 * math.sin(a)) for a in [math.radians(198 + 144 * k / 10) for k in range(11)]]
        inner = [(cx + 0.044 * math.cos(a), cz + 0.001 + 0.052 * math.sin(a)) for a in [math.radians(342 - 144 * k / 10) for k in range(11)]]
        out.append(C.rigid(G.decal(f'{prefix}_{s}', outer + inner, FRONT(), [head], 0.0016, material, step=0.006), 'Head'))
    return out


STUBBLE_OUTLINE = [(-0.104, 1.452), (-0.064, 1.437), (-0.030, 1.430), (0.0, 1.428), (0.030, 1.430), (0.064, 1.437), (0.104, 1.452),
                   (0.112, 1.400), (0.100, 1.352), (0.060, 1.318), (0.0, 1.306), (-0.060, 1.318), (-0.100, 1.352), (-0.112, 1.400)]


def stubble(prefix, dot_m, head, dots=120, seed=7):
    """Unshaven jaw: dark stipple dots over the lower face."""
    out = []
    rnd = random.Random(seed)
    poly = [Vector(p) for p in STUBBLE_OUTLINE]
    placed = []
    tries = 0
    while len(placed) < dots and tries < dots * 40:
        tries += 1
        q = Vector((rnd.uniform(-0.108, 0.108), rnd.uniform(1.31, 1.448)))
        if not G.inside(q, poly) or any((q - o).length < 0.0075 for o in placed):
            continue
        if abs(q.x) < 0.040 and abs(q.y - 1.404) < 0.010:       # keep the mouth line clear
            continue
        placed.append(q)
    pts = [C.ellipse(q.x, q.y, 0.0018, 0.0018, 5) for q in placed]
    parts = [G.decal(f'{prefix}_Dot_{k}', o, FRONT(), [head], 0.0016, dot_m, step=0.01) for k, o in enumerate(pts)]
    dot = parts[0]
    G.join(dot, parts[1:])
    out.append(C.rigid(dot, 'Head'))
    return out


def blush(prefix, material, head):
    return [C.rigid(G.decal(f'{prefix}_{s}', C.ellipse(s * 0.098, 1.446, 0.021, 0.013, 14), FRONT(), [head], 0.0014, material), 'Head')
            for s in (1, -1)]


def _glasses_parts(prefix, frame_m, lens_m, rx=0.050, rz=0.062, round_k=1.0):
    out = []
    for s in (1, -1):
        c = Vector((s * (B.EYE_C[0] + 0.006), -0.162, B.EYE_C[2]))
        ring = []
        for k in range(24):
            a = 2 * math.pi * k / 24
            ca, sa = math.cos(a), math.sin(a)
            ex = math.copysign(abs(ca) ** round_k, ca)        # round_k < 1: rounded rectangle
            ez = math.copysign(abs(sa) ** round_k, sa)
            wrap = 0.010 * max(0.0, ex * s) ** 2              # the outer side bends back round the head
            ring.append(c + Vector((rx * ex, wrap, rz * ez)))
        ring += ring[:2]
        out.append(G.tube(f'{prefix}_Rim_{s}', ring, 0.0042, frame_m, seg=6))
        if lens_m is not None:
            out.append(G.ellipsoid(f'{prefix}_Lens_{s}', c + Vector((0, -0.001, 0)), (rx * 0.97, 0.004, rz * 0.97), lens_m, seg=20, rings=8))
        hinge = c + Vector((s * rx, 0.010, 0.006))
        temple = [hinge, hinge + Vector((s * 0.024, 0.040, -0.002)), Vector((s * 0.150, -0.030, 1.552)), Vector((s * 0.153, 0.010, 1.532))]
        out.append(G.tube(f'{prefix}_Temple_{s}', temple, 0.0035, frame_m, seg=6))
    gap = B.EYE_C[0] + 0.006 - rx
    out.append(G.tube(prefix + '_Bridge', [Vector((gap, -0.163, 1.574)), Vector((0, -0.167, 1.580)), Vector((-gap, -0.163, 1.574))],
                      0.0038, frame_m, seg=6))
    return out


def glasses(prefix, frame_m, lens_m=None, rx=0.056, rz=0.062, round_k=1.0):
    return [C.rigid(o, 'Head') for o in _glasses_parts(prefix, frame_m, lens_m, rx, rz, round_k)]


def slide_up(ob, dh, squeeze=1.0, floor=0.008):
    """Slide a mesh along the head surface by dh (meridian coordinate); heights over the surface above `floor` are
    scaled by `squeeze` so the piece lies on the head: sunglasses pushed up onto the head."""
    for v in ob.data.vertices:
        p = v.co
        phi = math.atan2(p.x, -p.y)
        h = h_of(p.z)
        s0, n0 = head_at(phi, h)
        off = (p - s0).dot(n0)
        off = floor + (off - floor) * squeeze if off > floor else off
        q, _ = head_at(phi, min(h + dh, H_POLE - 0.01), off)
        v.co = q


def sunglasses_on_head(prefix, frame_m, lens_m, dh=0.150):
    parts = _glasses_parts(prefix, frame_m, lens_m, rx=0.052, rz=0.044, round_k=0.7)
    for o in parts:
        slide_up(o, dh, squeeze=0.35)
    return [C.rigid(o, 'Head') for o in parts]


def earpiece(prefix, material):
    """Bodyguard earpiece in the right ear with the coiled wire down into the collar at the back."""
    ear = Vector((-B.EAR_C[0] - B.EAR_R[0] + 0.004, B.EAR_C[1] - 0.004, B.EAR_C[2] - 0.004))
    bud = G.ellipsoid(prefix + '_Bud', ear, (0.012, 0.011, 0.013), material, seg=12, rings=8)
    spine = [ear + Vector((0.002, 0.004, -0.014)), Vector((-0.166, 0.030, 1.400)), Vector((-0.152, 0.060, 1.335)),
             Vector((-0.125, 0.098, 1.280)), Vector((-0.100, 0.122, 1.240))]
    cum = [0.0]
    for a, b in zip(spine, spine[1:]):
        cum.append(cum[-1] + (b - a).length)
    turns_per_m, per_turn = 90.0, 7
    n = int(cum[-1] * turns_per_m * per_turn)

    def at(d):
        for k in range(len(spine) - 1):
            if d <= cum[k + 1] or k == len(spine) - 2:
                t = (d - cum[k]) / max(1e-9, cum[k + 1] - cum[k])
                return spine[k].lerp(spine[k + 1], min(1.0, max(0.0, t))), (spine[k + 1] - spine[k]).normalized()
    coil = []
    for i in range(n + 1):
        d = cum[-1] * i / n
        p, t = at(d)
        a = (Vector((0, 0, 1)).cross(t)).normalized() if abs(t.z) < 0.99 else t.orthogonal().normalized()
        b = t.cross(a).normalized()
        ang = 2 * math.pi * turns_per_m * d
        coil.append(p + (a * math.cos(ang) + b * math.sin(ang)) * 0.0055)
    wire = G.tube(prefix + '_Coil', coil, 0.0017, material, seg=4, caps=False)
    out = [C.rigid(bud, 'Head')]
    C.set_weights(wire, [{P + 'Head': smoothstep(1.26, 1.40, p.z), P + 'Spine2': 1 - smoothstep(1.26, 1.40, p.z)}
                         for p in (wire.matrix_world @ v.co for v in wire.data.vertices)])
    out.append(wire)
    return out

# ------------------------------------------------------------------ accessories
def belt(prefix, strap_m, buckle_m, z=0.872, rx=0.190, ry=0.130, dy=-0.002, width=0.030, seg=32):
    pts = [Vector((rx * math.sin(a), dy - ry * math.cos(a), z)) for a in [2 * math.pi * k / seg for k in range(seg + 1)]]
    st = C.strap(prefix + '_Belt', pts, strap_m, width=width, thick=0.006,
                 normal_fn=lambda p: Vector((p.x / rx, (p.y - dy) / ry, 0)).normalized())
    bk = box(prefix + '_Buckle', Vector((0, dy - ry - 0.009, z)), (0.024, 0.004, 0.018), buckle_m)
    return [st, bk]


def holster_baton(prefix, holster_m, baton_m):
    h = box(prefix + '_Holster', Vector((-0.222, 0.035, 0.805)), (0.022, 0.044, 0.068), holster_m)
    flap = box(prefix + '_HolsterFlap', Vector((-0.226, 0.035, 0.868)), (0.024, 0.046, 0.012), holster_m)
    bat = G.tube(prefix + '_Baton', [(0.214, 0.050, 0.872), (0.222, 0.064, 0.600)], 0.0145, baton_m, seg=10)
    grip = G.tube(prefix + '_BatonGrip', [(0.214, 0.050, 0.880), (0.211, 0.046, 0.920)], 0.016, baton_m, seg=10)
    return [C.rigid(o, 'Hips') for o in (h, flap, bat, grip)]


def watch(prefix, band_m, face_m, x=0.608, side=1):
    s = side
    r = 0.040
    band = G.loft(prefix + '_Band', [((s * (x - 0.009), 0, B.arm_z(x)), (0, 1, 0), (0, 0, 1), r, r),
                                     ((s * (x + 0.009), 0, B.arm_z(x)), (0, 1, 0), (0, 0, 1), r, r)], band_m, seg=14)
    dial = G.ellipsoid(prefix + '_Case', (s * x, 0, B.arm_z(x) + r + 0.002), (0.016, 0.016, 0.006), band_m, seg=14, rings=6)
    glass = G.ellipsoid(prefix + '_Dial', (s * x, 0, B.arm_z(x) + r + 0.006), (0.012, 0.012, 0.003), face_m, seg=14, rings=6)
    return [C.rigid(o, ('Left' if s > 0 else 'Right') + 'ForeArm') for o in (band, dial, glass)]


def wristbands(prefix, material):
    out = []
    for s in (1, -1):
        b = G.loft(f'{prefix}_{s}', [((s * 0.585, 0, B.arm_z(0.585)), (0, 1, 0), (0, 0, 1), 0.043, 0.044),
                                      ((s * 0.618, 0, B.arm_z(0.618)), (0, 1, 0), (0, 0, 1), 0.042, 0.043)], material, seg=14)
        out.append(C.rigid(b, ('Left' if s > 0 else 'Right') + 'ForeArm'))
    return out


def gold_chain(prefix, material, targets, seg=64):
    bvh = G.bvh_of(targets)
    pts = []
    for k in range(seg + 1):
        a = 2 * math.pi * k / seg
        f = ((1 + math.cos(a)) / 2) ** 3
        p = Vector((0.160 * math.sin(a), -0.162 * math.cos(a), 1.262 - 0.160 * f))
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None:
            nrm = nrm if nrm.dot(Vector((p.x, p.y, 0))) >= 0 else -nrm
            p = loc + nrm * 0.011
        pts.append(p)
    return [G.tube(prefix, pts, lambda i, n: 0.0068 + 0.0030 * (i % 2), material, seg=8)]


def backpack(prefix, bag_m, strap_m, target):
    bvh = G.bvh_of([target])

    def back_y(z, x=0.0):
        hit = bvh.ray_cast(Vector((x, 0.8, z)), Vector((0, -1, 0)), 1.6)
        return hit[0].y if hit[0] is not None else 0.16
    secs = []
    for z, rx, ry in ((0.905, 0.095, 0.036), (0.930, 0.128, 0.056), (1.050, 0.136, 0.064), (1.150, 0.126, 0.058), (1.190, 0.090, 0.040)):
        secs.append(((0, back_y(z) + ry * 0.85, z), (1, 0, 0), (0, 1, 0), rx, ry))
    bag = G.loft(prefix + '_Bag', secs, bag_m, seg=16)
    pocket = G.loft(prefix + '_Pocket', [((0, back_y(0.96) + 0.100, z), (1, 0, 0), (0, 1, 0), rx, ry)
                                         for z, rx, ry in ((0.935, 0.070, 0.016), (0.955, 0.092, 0.024), (1.010, 0.094, 0.025), (1.030, 0.074, 0.016))],
                    strap_m, seg=14)
    out = [bag, pocket]
    for s in (1, -1):
        raw = [Vector((s * 0.085, 0.16, 1.175)), Vector((s * 0.150, 0.105, 1.236)), Vector((s * 0.168, 0.0, 1.258)),
               Vector((s * 0.158, -0.100, 1.236)), Vector((s * 0.132, -0.150, 1.150)), Vector((s * 0.138, -0.148, 1.040)),
               Vector((s * 0.170, -0.120, 0.975))]
        pts, nrms = [], []
        for p in raw:
            loc, nrm, _, _ = bvh.find_nearest(p)
            nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.3))) >= 0 else -nrm
            pts.append(loc + nrm * 0.006); nrms.append(nrm)
        st = C.strap(f'{prefix}_Strap_{s}', pts, strap_m, width=0.034, thick=0.006,
                     normal_fn=lambda q: (lambda r: r[1] if r[1].dot(Vector((q.x, q.y, 0.3))) >= 0 else -r[1])(bvh.find_nearest(q)))
        out.append(st)
    return out


def sweater_on_shoulders(prefix, material, target):
    bvh = G.bvh_of([target])
    drape = G.decal(prefix + '_Drape', [(-0.160, 1.060), (0.160, 1.060), (0.172, 1.150), (0.160, 1.212), (0.0, 1.236), (-0.160, 1.212),
                                        (-0.172, 1.150)], BACK(), [target], 0.010, material, step=0.016, thickness=0.010)
    out = [drape]

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.4))) >= 0 else -nrm
        return loc + nrm * off
    knot_c = on(Vector((0.0, -0.17, 1.150)), 0.030)
    for s in (1, -1):
        path = [on(Vector((s * 0.160, 0.110, 1.245)), 0.020), on(Vector((s * 0.175, 0.020, 1.262)), 0.020),
                on(Vector((s * 0.160, -0.090, 1.236)), 0.022), on(Vector((s * 0.090, -0.150, 1.190)), 0.024), knot_c + Vector((s * 0.018, 0, 0.004))]
        out.append(G.tube(f'{prefix}_Sleeve_{s}', path, 0.022, material, seg=10))
        out.append(G.tube(f'{prefix}_End_{s}', [knot_c + Vector((s * 0.012, -0.004, -0.010)), knot_c + Vector((s * 0.030, -0.006, -0.090)),
                                                knot_c + Vector((s * 0.036, -0.004, -0.120))], lambda i, n: (0.021, 0.022, 0.016)[i], material, seg=10))
    out.append(G.ellipsoid(prefix + '_Knot', knot_c, (0.034, 0.022, 0.026), material, seg=12, rings=8))
    return out

# ------------------------------------------------------------------ front details (decals)
def front_decal(name, pts, target, material, offset=0.003, thickness=0.0, step=0.010):
    return G.decal(name, pts, FRONT(), [target], offset, material, step=step, thickness=thickness)


def buttons(prefix, target, material, xz, r=0.0095, offset=0.004):
    return [front_decal(f'{prefix}_{k}', C.ellipse(x, z, r, r, 10), target, material, offset) for k, (x, z) in enumerate(xz)]


def tie(prefix, target, material, z_tip=0.985, offset=0.0045):
    knot = [(-0.016, 1.262), (0.016, 1.262), (0.011, 1.236), (-0.011, 1.236)]
    blade = [(-0.010, 1.240), (0.010, 1.240), (0.025, z_tip + 0.030), (0.0, z_tip), (-0.025, z_tip + 0.030)]
    return [front_decal(prefix + '_Knot', knot, target, material, offset + 0.0015, thickness=0.004, step=0.006),
            front_decal(prefix + '_Blade', blade, target, material, offset, thickness=0.003, step=0.010)]


def suit_front(prefix, jacket, M, tie_slot='Tie', v_tip=1.030, button_slot='Button', square_slot=None):
    """Closed cartoon suit jacket: shirt V with the tie, lapels, buttons, pocket flaps (decals on the jacket)."""
    out = [front_decal(prefix + '_ShirtV', [(-0.066, 1.258), (0.066, 1.258), (0.0, v_tip)], jacket, M['Shirt'], 0.0025, step=0.008)]
    if tie_slot:
        knot = [(-0.015, 1.256), (0.015, 1.256), (0.010, 1.232), (-0.010, 1.232)]
        blade = [(-0.009, 1.236), (0.009, 1.236), (0.019, v_tip + 0.060), (0.0, v_tip + 0.030), (-0.019, v_tip + 0.060)]
        out += [front_decal(prefix + '_TieKnot', knot, jacket, M[tie_slot], 0.0055, step=0.006),
                front_decal(prefix + '_TieBlade', blade, jacket, M[tie_slot], 0.0045, step=0.008)]
    for s in (1, -1):
        lap = [(s * 0.064, 1.258), (s * 0.104, 1.244), (s * 0.090, 1.200), (s * 0.112, 1.185), (s * 0.004, v_tip - 0.004), (s * 0.002, v_tip + 0.010)]
        if s < 0:
            lap = lap[::-1]
        out.append(front_decal(f'{prefix}_Lapel_{s}', lap, jacket, M['Lapel'], 0.0035, step=0.008))
        out.append(front_decal(f'{prefix}_Flap_{s}', [(s * 0.075, 0.822), (s * 0.165, 0.822), (s * 0.165, 0.846), (s * 0.075, 0.846)][::s],
                               jacket, M['Lapel'], 0.0035, thickness=0.003))
    out += buttons(prefix + '_Btn', jacket, M[button_slot], [(0.0, v_tip - 0.050), (0.0, v_tip - 0.120)], r=0.010)
    if square_slot:
        out.append(front_decal(prefix + '_Square', [(0.074, 1.120), (0.128, 1.120), (0.118, 1.146), (0.100, 1.132), (0.084, 1.148)],
                               jacket, M[square_slot], 0.0035, step=0.006))
    return out


def shoulder_boards(prefix, jacket, material, star_m=None):
    out = []
    for s in (1, -1):
        pts = [(s * 0.152, 0.028), (s * 0.206, 0.030), (s * 0.206, -0.030), (s * 0.152, -0.028)]
        if s < 0:
            pts = pts[::-1]
        out.append(G.decal(f'{prefix}_{s}', pts, TOP(1.6), [jacket], 0.004, material, step=0.010, thickness=0.004))
        if star_m is not None:
            for k, x in enumerate((0.168, 0.192)):
                out.append(G.decal(f'{prefix}_Star_{s}_{k}', C.ellipse(s * x, 0.0, 0.007, 0.007, 8), TOP(1.6), [jacket], 0.0065, star_m))
    return out
