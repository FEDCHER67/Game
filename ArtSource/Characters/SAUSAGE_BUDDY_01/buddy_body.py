"""Sausage Buddy body, face and Mixamo-compatible skeleton layout (Blender Z up, -Y forward, left = +X).
Proportions measured from the owner's reference (1.75 m tall, wide capsule head, chunky mitten hands)."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
from buddy_geo import smoothstep, chain, mix

P = 'mixamorig:'
HEAD_R, HEAD_RY = 0.142, 0.134          # capsule half width / half depth
HEAD_TOP = 1.75
HEAD_CYL_TOP = HEAD_TOP - HEAD_R
EYE_C = (0.051, -0.116, 1.556)
EYE_R = (0.046, 0.032, 0.054)
NOSE_C, NOSE_R = (0.0, -0.160, 1.482), (0.045, 0.040, 0.050)
LEG_X = 0.100

# Joint layout for the Mixamo skeleton (head, tail) -- the builder uses these to fit the source rig.
def joints():
    J = {}
    def b(n, h, t):
        J[P + n] = (Vector(h), Vector(t))
    b('Hips', (0, 0, .82), (0, 0, .90)); b('Spine', (0, 0, .90), (0, 0, .99)); b('Spine1', (0, 0, .99), (0, 0, 1.08))
    b('Spine2', (0, 0, 1.08), (0, 0, 1.18)); b('Neck', (0, 0, 1.18), (0, 0, 1.25)); b('Head', (0, 0, 1.25), (0, 0, 1.75))
    b('HeadTop_End', (0, 0, 1.75), (0, 0, 1.79))
    for side, s in (('Left', 1), ('Right', -1)):
        def m(n, h, t):
            b(side + n, (s * h[0], h[1], h[2]), (s * t[0], t[1], t[2]))
        m('Shoulder', (.06, 0, 1.162), (.20, 0, 1.165)); m('Arm', (.20, 0, 1.165), (.43, 0, 1.162))
        m('ForeArm', (.43, 0, 1.162), (.64, 0, 1.158)); m('Hand', (.64, 0, 1.158), (.735, 0, 1.156))
        th = [(.676, -.034, 1.152), (.696, -.060, 1.150), (.712, -.080, 1.149), (.726, -.097, 1.148), (.734, -.106, 1.148)]
        for i in range(4):
            m('HandThumb' + str(i + 1), th[i], th[i + 1])
        for digit, y, xs in (('Index', -.035, [.735, .752, .770, .788, .798]), ('Middle', 0, [.735, .754, .774, .794, .805]),
                             ('Ring', .035, [.735, .751, .768, .785, .795]), ('Pinky', .035, [.735, .751, .768, .785, .795])):
            for i in range(4):
                m('Hand' + digit + str(i + 1), (xs[i], y, 1.156), (xs[i + 1], y, 1.156))
        m('UpLeg', (LEG_X, 0, .80), (LEG_X, 0, .43)); m('Leg', (LEG_X, 0, .43), (LEG_X, 0, .115))
        m('Foot', (LEG_X, 0, .115), (LEG_X, -.10, .040)); m('ToeBase', (LEG_X, -.10, .040), (LEG_X, -.16, .030))
        m('Toe_End', (LEG_X, -.16, .030), (LEG_X, -.18, .030))
    return J


def weigh(ob, fn):
    for v in ob.data.vertices:
        w = fn(ob.matrix_world @ v.co)
        items = sorted(((k, x) for k, x in w.items() if x > 1e-4), key=lambda kv: -kv[1])[:4]
        tot = sum(x for _, x in items) or 1
        for k, x in items:
            g = ob.vertex_groups.get(P + k) or ob.vertex_groups.new(name=P + k)
            g.add([v.index], x / tot, 'REPLACE')
    return ob


def side_of(p):
    return 'Left' if p.x >= 0 else 'Right'

# ------------------------------------------------------------------ skin parts
def head_capsule(skin):
    secs = []
    # below the collar the capsule narrows so it never shows through tight shirts
    for z, k in ((1.08, 0.62), (1.13, 0.74), (1.175, 0.90), (1.205, 0.99), (1.25, 1.0), (1.32, 1.0), (1.40, 1.0), (1.48, 1.0), (1.55, 1.0), (HEAD_CYL_TOP, 1.0)):
        secs.append(((0, 0, z), (1, 0, 0), (0, 1, 0), HEAD_R * k, HEAD_RY * k))
    for k in range(1, 7):
        th = math.radians(15 * k)
        secs.append(((0, 0, HEAD_CYL_TOP + HEAD_R * math.sin(th)), (1, 0, 0), (0, 1, 0), HEAD_R * math.cos(th), HEAD_RY * math.cos(th)))
    ob = G.loft('Skin_Head', secs, skin, seg=24, cap_start=True, cap_end=True, subdiv=1)
    return weigh(ob, lambda p: chain(p.z, [(1.12, 'Spine2'), (1.20, 'Neck'), (1.26, 'Head')]))


def head_features(skin, nose_mat, inner_mat):
    parts = [G.ellipsoid('Skin_Nose', NOSE_C, NOSE_R, nose_mat, seg=20, rings=12)]
    for s in (1, -1):
        parts.append(G.ellipsoid(f'Skin_Ear_{s}', (s * 0.138, 0.006, 1.468), (0.027, 0.038, 0.051), skin, seg=16, rings=10))
        parts.append(G.ellipsoid(f'Skin_EarInner_{s}', (s * 0.158, 0.004, 1.466), (0.008, 0.023, 0.033), inner_mat, seg=12, rings=8))
    for o in parts:
        weigh(o, lambda p: {'Head': 1.0})
    return parts


def torso(skin):
    rows = [(.76, .128, .086, 0.0), (.80, .152, .097, -0.004), (.86, .164, .105, -0.010), (.94, .170, .109, -0.012),
            (1.02, .172, .109, -0.008), (1.08, .176, .107, -0.002), (1.13, .180, .105, 0.004), (1.17, .172, .101, 0.006),
            (1.205, .142, .093, 0.006), (1.235, .112, .087, 0.004)]
    secs = [((0, dy, z), (1, 0, 0), (0, 1, 0), rx, ry) for z, rx, ry, dy in rows]
    ob = G.loft('Skin_Torso', secs, skin, seg=24, subdiv=1)

    def w(p):
        t = chain(p.z, [(.84, 'Hips'), (.93, 'Spine'), (1.02, 'Spine1'), (1.11, 'Spine2')])
        k = smoothstep(.11, .16, abs(p.x)) * smoothstep(1.08, 1.16, p.z)
        return mix(t, {side_of(p) + 'Shoulder': 1.0}, k * 0.6)
    return weigh(ob, w)


def arm_z(x):
    return 1.165 - 0.007 * smoothstep(0.20, 0.64, x)


def arms(skin):
    out = []
    for s in (1, -1):
        side = 'Left' if s > 0 else 'Right'
        rows = [(.10, .046), (.16, .047), (.21, .046), (.28, .045), (.36, .043), (.43, .041), (.50, .039), (.57, .036), (.62, .033), (.645, .031)]
        secs = [((s * x, 0, arm_z(x)), (0, 1, 0), (0, 0, 1), r, r * 1.02) for x, r in rows]
        a = G.loft(f'Skin_Arm_{side}', secs, skin, seg=16, subdiv=1)
        weigh(a, lambda p, side=side: chain(abs(p.x), [(.12, 'Spine2'), (.17, side + 'Shoulder'), (.23, side + 'Arm'), (.40, side + 'Arm'),
                                                         (.47, side + 'ForeArm'), (.60, side + 'ForeArm'), (.655, side + 'Hand')]))
        out.append(a)
        out += hand(s, side, skin)
    return out


def capsule_along(name, start, direction, length, radius, material, seg=12, tip_taper=0.92):
    d = Vector(direction).normalized()
    u = d.orthogonal().normalized(); v = d.cross(u).normalized()
    secs = []
    for k in range(5):
        t = length * (k / 4) * 0.82
        secs.append((Vector(start) + d * t, u, v, radius * (1 - (1 - tip_taper) * k / 4), radius * (1 - (1 - tip_taper) * k / 4) * 0.92))
    base = Vector(start) + d * length * 0.82
    rt = radius * tip_taper
    for k in range(1, 5):
        th = math.radians(22.5 * k)
        secs.append((base + d * (rt * math.sin(th)), u, v, rt * math.cos(th), rt * math.cos(th) * 0.92))
    return G.loft(name, secs, material, seg=seg, cap_start=True, cap_end=True, subdiv=1)


def hand(s, side, skin):
    rows = [(.625, .032, .029), (.645, .045, .030), (.668, .054, .030), (.695, .058, .029), (.722, .057, .027), (.744, .052, .024), (.754, .044, .021)]
    secs = [((s * x, 0, 1.157), (0, 1, 0), (0, 0, 1), ry, rz) for x, ry, rz in rows]
    palm = G.loft(f'Skin_Palm_{side}', secs, skin, seg=16, subdiv=1)
    weigh(palm, lambda p: chain(abs(p.x), [(.632, side + 'ForeArm'), (.662, side + 'Hand')]))
    parts = [palm]
    for digit, y, length in (('Index', -.035, .072), ('Middle', 0.0, .078), ('Ring', .035, .068)):
        f = capsule_along(f'Skin_{digit}_{side}', (s * .728, y, 1.155), (s, 0, -0.04), length, .0195, skin)
        weigh(f, lambda p, digit=digit: chain(abs(p.x), [(.736, side + 'Hand'), (.750, side + 'Hand' + digit + '1'), (.762, side + 'Hand' + digit + '1'),
                                                           (.776, side + 'Hand' + digit + '2'), (.790, side + 'Hand' + digit + '3')]))
        parts.append(f)
    th0 = Vector((s * .672, -.030, 1.150)); thd = Vector((s * .55, -.82, -0.10)).normalized()
    t = capsule_along(f'Skin_Thumb_{side}', th0, thd, .074, .0215, skin)
    weigh(t, lambda p: chain((p - th0).dot(thd), [(.004, side + 'Hand'), (.016, side + 'HandThumb1'), (.034, side + 'HandThumb2'), (.052, side + 'HandThumb3')]))
    parts.append(t)
    return parts


def legs(skin):
    out = []
    for s in (1, -1):
        side = 'Left' if s > 0 else 'Right'
        rows = [(.82, .058), (.76, .056), (.66, .053), (.54, .049), (.44, .046), (.34, .044), (.22, .041), (.12, .039), (.085, .039)]
        secs = [((s * LEG_X, 0, z), (1, 0, 0), (0, 1, 0), r, r) for z, r in rows]
        l = G.loft(f'Skin_Leg_{side}', secs, skin, seg=14, subdiv=1)
        weigh(l, lambda p, side=side: mix(chain(p.z, [(.38, side + 'Leg'), (.48, side + 'UpLeg')]), {'Hips': 1.0}, smoothstep(.74, .86, p.z)))
        out.append(l)
    return out


def build_body(skin, nose_mat, inner_mat):
    parts = [torso(skin), head_capsule(skin)] + head_features(skin, nose_mat, inner_mat) + arms(skin) + legs(skin)
    body = parts[0]
    G.join(body, parts[1:])
    body.name = 'Body'
    body.data.name = 'Body'
    for p in body.data.polygons:
        p.use_smooth = True
    return body

# ------------------------------------------------------------------ face (separate object with expression shape keys)
EXPRESSIONS = ('Basis', 'Blink', 'Surprised', 'Worried', 'Happy')


def head_surface_y(x, z, extra=0.0):
    """Front surface y of the head capsule at (x, z) plus `extra` toward the viewer."""
    if z > HEAD_CYL_TOP:
        dz = z - HEAD_CYL_TOP
        k = max(0.0, 1 - (dz / HEAD_R) ** 2) ** 0.5
        rx, ry = HEAD_R * k, HEAD_RY * k
    else:
        rx, ry = HEAD_R, HEAD_RY
    q = max(0.0, 1 - (x / max(rx, 1e-6)) ** 2)
    return -ry * math.sqrt(q) - extra


def face_parts(expr, mats):
    """Same topology for every expression; only positions change."""
    white, rim, pupil, shine, brow_m, mouth_m = mats
    eye_scale = {'Surprised': 1.12, 'Happy': 1.0}.get(expr, 1.0)
    squash = {'Blink': 0.10, 'Happy': 0.72}.get(expr, 1.0)
    pupil_scale = {'Surprised': 0.72, 'Worried': 0.88}.get(expr, 1.0)
    pupil_dz = {'Worried': 0.006, 'Surprised': 0.0}.get(expr, -0.002)
    parts = []
    for s in (1, -1):
        cx, cy, cz = EYE_C
        rx, ry, rz = (r * eye_scale for r in EYE_R)
        rz_eff = rz * squash
        cz_eff = cz - (rz - rz_eff) * (0.55 if expr == 'Happy' else 0.0)
        yaw = Matrix.Rotation(math.radians(-14 * s), 3, 'Z')
        center = Vector((s * cx, cy, cz_eff))
        parts.append(G.ellipsoid(f'Eye_{s}', center, (rx, ry, rz_eff), white, rot=yaw, seg=20, rings=12))
        parts.append(G.ellipsoid(f'EyeRim_{s}', center + Vector((0, 0.0065, 0)), (rx * 1.035, ry * 0.92, rz_eff * 1.03 + 0.0012), rim, rot=yaw, seg=20, rings=12))
        fwd = yaw @ Vector((0, -1, 0))
        pc = center + fwd * (ry - 0.0045) + Vector((-s * 0.011, 0, pupil_dz * squash))
        pr = 0.0245 * pupil_scale
        parts.append(G.ellipsoid(f'Pupil_{s}', pc, (pr, 0.0075, pr * 1.12 * max(squash, 0.12)), pupil, rot=yaw, seg=16, rings=10))
        sc = pc + fwd * 0.0055 + Vector((s * 0.006 * pupil_scale, 0, 0.008 * pupil_scale * squash))
        parts.append(G.ellipsoid(f'Shine_{s}', sc, (0.0058 * pupil_scale, 0.0025, 0.0058 * pupil_scale * max(squash, 0.12)), shine, rot=yaw, seg=10, rings=6))
        # Brow: thick soft arc above the eye.
        lift = {'Surprised': 0.020, 'Happy': 0.006, 'Worried': 0.010}.get(expr, 0.0)
        tilt = {'Worried': 0.014, 'Surprised': 0.0}.get(expr, 0.0)
        pts = []
        for k in range(7):
            t = k / 6
            x = s * (0.020 + 0.072 * t)
            arch = 0.010 * math.sin(math.pi * t) * (1.4 if expr == 'Surprised' else 1.0)
            z = 1.636 + arch + lift + tilt * (1 - t) - 0.004 * t
            pts.append(Vector((x, head_surface_y(x, z, 0.005), z)))
        parts.append(G.tube(f'Brow_{s}', pts, lambda i, n: 0.0074 + 0.0050 * math.sin(math.pi * i / (n - 1)), brow_m, seg=8, frame_up=(0, -1, 0)))
    # Mouth: smile line, an "O" when surprised, a wobbly frown when worried.
    pts = []
    for k in range(13):
        t = k / 12
        if expr == 'Surprised':
            a = 2 * math.pi * t + math.pi / 2
            x, z = 0.016 * math.cos(a), 1.405 + 0.019 * math.sin(a)
        elif expr == 'Worried':
            x = -0.030 + 0.060 * t
            z = 1.408 - 0.008 * math.cos(2 * math.pi * t) * 0.6 - 0.006 * (1 - abs(2 * t - 1))
        elif expr == 'Happy':
            x = -0.045 + 0.090 * t
            z = 1.402 + 0.030 * (2 * t - 1) ** 2
        else:
            x = -0.036 + 0.070 * t
            z = 1.404 + 0.010 * (2 * t - 1) ** 2 + (0.004 * (t - 0.85) / 0.15 if t > 0.85 else 0.0)
        pts.append(Vector((x, head_surface_y(x, z, 0.0025), z)))
    parts.append(G.tube('Mouth', pts, 0.0032, mouth_m, seg=8, frame_up=(0, -1, 0)))
    return parts


def build_face(mats):
    shapes = {}
    for expr in EXPRESSIONS:
        parts = face_parts(expr, mats)
        f = parts[0]; G.join(f, parts[1:])
        shapes[expr] = f
    face = shapes['Basis']; face.name = 'Face'; face.data.name = 'Face'
    face.shape_key_add(name='Basis')
    for expr in EXPRESSIONS[1:]:
        src = shapes[expr]
        key = face.shape_key_add(name=expr, from_mix=False)
        key.value = 0.0      # Blender 5.2 creates new keys at 1.0
        assert len(src.data.vertices) == len(face.data.vertices)
        for i, v in enumerate(src.data.vertices):
            key.data[i].co = v.co
        bpy.data.objects.remove(src)
    for p in face.data.polygons:
        p.use_smooth = True
    weigh(face, lambda p: {'Head': 1.0})
    return face
