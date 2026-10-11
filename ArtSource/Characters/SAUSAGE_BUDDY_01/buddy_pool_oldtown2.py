"""Old town NPC pool, part 2 (TASK-000270): fitness coach, courier, selfie tourist on the base Sausage Buddy.
Same format as buddy_types.TYPES / BUILDERS; every garment and prop has its own material slot <TYPE>_<Slot>.
Carried props are rigid on the right hand and exported as the separate 'Props' mesh."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T          # noqa: F401  (registry; helpers are used at build time only)

P = 'mixamorig:'
GROUP = 'Старый город'
WHITE = (248, 248, 244)

TYPES = {
    'OLD_FITNESS': dict(
        label='Фитнес-коуч', group=GROUP, body=dict(muscle=1.0), face=dict(Happy=0.6),
        look=dict(skin=(214, 136, 86), nose=(202, 116, 72), brow=(58, 40, 30), rim=(150, 84, 58)),
        slots={'Top': ((228, 46, 58), 0.75), 'Top_Trim': (WHITE, 0.75), 'Shorts': ((30, 32, 40), 0.8),
               'Shorts_Stripe': ((228, 46, 58), 0.8), 'Socks': (WHITE, 0.9), 'Shoe_Upper': ((196, 238, 44), 0.55),
               'Shoe_Sole': (WHITE, 0.6), 'Shoe_Lace': ((30, 32, 40), 0.7), 'Headband': ((228, 46, 58), 0.9),
               'Bands': ((228, 46, 58), 0.9), 'Hair': ((52, 38, 30), 0.6), 'Cord': ((30, 32, 40), 0.7),
               'Whistle': ((206, 208, 214), 0.22, 'metal'), 'Shaker': ((226, 234, 240), 0.25), 'Shake': ((128, 84, 56), 0.4),
               'Shaker_Lid': ((196, 238, 44), 0.45)},
        colourways=[{'Top': (36, 116, 220), 'Shorts_Stripe': (36, 116, 220), 'Headband': (36, 116, 220), 'Bands': (36, 116, 220),
                     'Shorts': (236, 236, 232), 'Shoe_Upper': (250, 110, 40), 'Shaker_Lid': (250, 110, 40), 'Shake': (232, 150, 170)},
                    {'Top': (30, 30, 34), 'Top_Trim': (250, 206, 40), 'Shorts': (88, 94, 108), 'Shorts_Stripe': (250, 206, 40),
                     'Headband': (250, 206, 40), 'Bands': (250, 206, 40), 'Shoe_Upper': (246, 246, 242), 'Shoe_Lace': (250, 206, 40),
                     'Shaker_Lid': (250, 206, 40)}]),
    'OLD_COURIER': dict(
        label='Курьер', group=GROUP, face=dict(Worried=0.3, Surprised=0.1),
        slots={'Jacket': ((40, 44, 56), 0.7), 'Jacket_Panel': ((250, 196, 30), 0.7), 'Jacket_Rib': ((26, 28, 34), 0.85),
               'Pants': ((44, 48, 56), 0.9), 'Pants_Rib': ((30, 32, 38), 0.9), 'Pocket': ((56, 60, 70), 0.9),
               'Socks': ((40, 40, 44), 0.9), 'Shoe_Upper': ((240, 240, 236), 0.7), 'Shoe_Sole': ((58, 58, 62), 0.6),
               'Shoe_Lace': ((240, 240, 236), 0.7), 'Cap': ((250, 196, 30), 0.85), 'Cap_Peak': ((40, 44, 56), 0.8),
               'Hair': ((62, 46, 36), 0.85), 'Box': ((250, 196, 30), 0.6), 'Box_Trim': ((40, 44, 56), 0.6),
               'Reflect': ((206, 210, 216), 0.25), 'Straps': ((30, 32, 38), 0.8), 'Sweat': ((150, 210, 250), 0.08),
               'Phone': ((24, 24, 28), 0.35), 'Screen': ((86, 196, 150), 0.15)},
        colourways=[{'Jacket_Panel': (60, 186, 90), 'Box': (60, 186, 90), 'Cap': (60, 186, 90), 'Pants': (60, 64, 58)},
                    {'Jacket': (232, 232, 228), 'Jacket_Panel': (230, 58, 50), 'Box': (230, 58, 50), 'Cap': (230, 58, 50),
                     'Cap_Peak': (232, 232, 228), 'Box_Trim': (232, 232, 228), 'Pants': (30, 30, 34), 'Shoe_Upper': (30, 30, 34)}]),
    'OLD_TOURIST': dict(
        label='Турист', group=GROUP, body=dict(belly=0.5), arm_down=71.0, face=dict(Happy=0.5),
        look=dict(skin=(240, 138, 110), nose=(230, 92, 82), brow=(150, 108, 72)),
        slots={'Shirt': ((36, 168, 186), 0.85), 'Flower': ((240, 78, 98), 0.85), 'Flower_2': ((250, 246, 236), 0.85),
               'Flower_Centre': ((250, 208, 60), 0.85), 'Leaf': ((28, 112, 78), 0.85), 'Buttons': (WHITE, 0.5),
               'Shorts': ((196, 178, 136), 0.9), 'Shorts_Pocket': ((172, 154, 114), 0.9), 'Socks': (WHITE, 0.9),
               'Sandal': ((112, 70, 40), 0.6), 'Sandal_Sole': ((70, 50, 36), 0.7), 'Hat': ((232, 222, 196), 0.95),
               'Hat_Band': ((60, 90, 130), 0.9), 'Hair': ((156, 124, 92), 0.85), 'Sunscreen': ((252, 252, 250), 0.6),
               'Camera': ((30, 30, 34), 0.45), 'Camera_Top': ((200, 202, 208), 0.25, 'metal'), 'Lens_Glass': ((70, 100, 150), 0.05),
               'Camera_Strap': ((40, 40, 46), 0.8), 'Pack': ((122, 60, 164), 0.6), 'Pack_Strap': ((30, 30, 34), 0.8),
               'Zip': ((220, 220, 224), 0.4), 'Stick': ((30, 30, 34), 0.3), 'Stick_Grip': ((52, 52, 58), 0.9),
               'Phone': (WHITE, 0.4), 'Screen': ((38, 56, 88), 0.1)},
        colourways=[{'Shirt': (236, 86, 86), 'Flower': (250, 246, 236), 'Flower_2': (250, 208, 60), 'Flower_Centre': (236, 86, 86),
                     'Shorts': (128, 128, 118), 'Shorts_Pocket': (110, 110, 102), 'Hat': (250, 250, 246), 'Pack': (36, 160, 160)},
                    {'Shirt': (250, 212, 66), 'Flower': (54, 116, 200), 'Flower_2': (236, 86, 86), 'Leaf': (60, 140, 60),
                     'Shorts': (92, 110, 80), 'Shorts_Pocket': (78, 94, 68), 'Hat': (112, 140, 92), 'Hat_Band': (60, 40, 30),
                     'Pack': (232, 60, 120)}]),
}

# ------------------------------------------------------------------ small helpers
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _decal_t(pieces, garment, filt=None):
    src = C.weight_source([garment])
    return [C.transfer(o, src, filt) for o in pieces]


def _rbox(name, center, half, material, bevel=0.010, segs=2, rot=None):
    """Bevelled box (flat shaded): half extents along the columns of rot."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.scale(bm, vec=Vector(half), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=bevel, segments=segs, profile=0.5, affect='EDGES')
    m = Matrix.Translation(Vector(center)) @ (rot if rot is not None else Matrix.Identity(3)).to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return G.from_bm(name, bm, material, smooth=False)


def _frame(u, v, w):
    """3x3 matrix with columns u, v, w."""
    return Matrix((tuple(u), tuple(v), tuple(w))).transposed()


def _cyl(name, p0, p1, r, material, seg=12, mats=None):
    """Capped cylinder; r may be a list of (t, radius) rows along p0 -> p1 (mats: per band material index)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    u = d.orthogonal().normalized()
    v = d.cross(u).normalized()
    rows = r if isinstance(r, (list, tuple)) else [(0.0, r), (1.0, r)]
    secs = [(p0.lerp(p1, t), u, v, rr, rr) for t, rr in rows]
    extra = mats[1] if mats else ()
    return G.loft(name, secs, material, seg=seg, mat_rows=mats[0] if mats else None, extra=extra)


def _on_surface(bvh, p, off, up=0.3):
    loc, nrm, _, _ = bvh.find_nearest(p)
    if loc is None:
        return Vector(p)
    nrm = nrm if nrm.dot(Vector((p.x, p.y, up))) >= 0 else -nrm
    return loc + nrm * off


def _idle_hand(side, arm_down):
    """Rotation of the hand bone in the idle pose (idle_joints at t = 0) and the wrist in rest / idle space."""
    s = 1 if side == 'Left' else -1
    R = lambda ax, d: Quaternion(Vector(ax), math.radians(d))
    qa = R((1, 0, 0), -4) @ R((0, 1, 0), s * arm_down)
    qf = R((1, 0, 0), -14)
    qh = R((0, 1, 0), s * 6)
    S = W.bone_rest(side + 'Arm').translation
    F = W.bone_rest(side + 'ForeArm').translation
    Wt = W.bone_rest(side + 'Hand').translation
    Fi = S + qa @ (F - S)
    Wi = Fi + (qf @ qa) @ (Wt - F)
    return qh @ qf @ qa, Vector(Wt), Wi


def _idle_to_rest(objs, side, arm_down):
    """Meshes modelled in the idle pose (world space) -> the hand's rest (T-pose) placement."""
    q, Wt, Wi = _idle_hand(side, arm_down)
    m = Matrix.Translation(Wt) @ q.inverted().to_matrix().to_4x4() @ Matrix.Translation(-Wi)
    for o in objs:
        o.data.transform(m)
        o.data.update()
    return objs


def _hand_axes(side='Right'):
    """Rest-pose hand frame: wrist, a (wrist -> fingertips), n (palm normal), f (thumb side / front)."""
    rm = W.bone_rest(side + 'Hand')
    a = Vector(rm.col[1][:3]).normalized()
    n = Vector((0, 0, -1))
    n = (n - a * n.dot(a)).normalized()
    f = Vector((0, -1, 0))
    f = (f - a * f.dot(a) - n * f.dot(n)).normalized()
    return rm.translation.copy(), a, n, f


def _head_band_hair(name, material, upper, arc=(50, 310), off=0.0018, thick=0.004):
    ob, _ = W.shell(name, material, W.HAIRLINE, upper, off=off, thick=thick, seg=24, rows=3,
                    arc=(math.radians(arc[0]), math.radians(arc[1])))
    return C.rigid(ob, 'Head')


def _neck_cord(bvh, s, z_end, x_end, y_off, off=0.007, n=9):
    """Cord / strap path for one side: from the back of the neck round the side and down the chest to (x_end, z_end)."""
    pts = []
    for k in range(n):
        a = math.radians(180 - 125 * k / (n - 1))           # 180 = back, 55 = front side
        p = Vector((s * 0.172 * math.sin(a), -0.160 * math.cos(a), 1.258 - 0.010 * (1 - math.cos(a)) / 2))
        pts.append(_on_surface(bvh, p, off, up=1.0))
    start = pts[-1]
    tgt = Vector((s * x_end, y_off, z_end))
    for k in range(1, 6):
        t = k / 5
        p = start.lerp(tgt, t)
        pts.append(_on_surface(bvh, p, off, up=0.2))
    return pts

# ------------------------------------------------------------------ OLD_FITNESS
def _shaker(prefix, M):
    """Shaker bottle in the right palm (rest pose); upright in the idle pose: lid toward the wrist."""
    wr, a, n, f = _hand_axes('Right')
    c = wr + a * 0.080 + n * 0.052 + f * 0.006
    r = 0.042
    lid0, top = c - a * 0.088, c + a * 0.112           # body from the lid seam to the bottom
    body = _cyl(prefix + '_Shaker', lid0, top, [(0.0, r), (0.45, r), (0.47, r + 0.0015), (0.96, r + 0.0015), (1.0, r - 0.004)],
                M['Shaker'], seg=16, mats=([0, 1, 1, 1], [M['Shake']]))
    lid = _cyl(prefix + '_Lid', lid0 + a * 0.004, lid0 - a * 0.034, [(0.0, r + 0.004), (0.7, r + 0.004), (1.0, r - 0.006)],
               M['Shaker_Lid'], seg=16)
    spout = _cyl(prefix + '_Spout', lid0 - a * 0.030, lid0 - a * 0.052 + f * 0.0, 0.012, M['Shaker_Lid'], seg=10)
    loop = G.tube(prefix + '_Loop', [lid0 - a * 0.020 + n * 0.030 + f * 0.020, lid0 - a * 0.052 + n * 0.040 + f * 0.010,
                                     lid0 - a * 0.058 + n * 0.040 - f * 0.012, lid0 - a * 0.020 + n * 0.030 - f * 0.024],
                  0.005, M['Shaker_Lid'], seg=6)
    return [W.prop(o, 'RightHand') for o in (body, lid, spout, loop)]


def _whistle(prefix, M, src_obj):
    bvh = G.bvh_of([src_obj])
    out = []
    z_end, x_end = 1.085, 0.020
    for s in (1, -1):
        pts = _neck_cord(bvh, s, z_end, x_end, -0.16, off=0.006)
        out.append(_t(G.tube(f'{prefix}_Cord_{s}', pts, 0.0042, M['Cord'], seg=6), C.weight_source([src_obj]), C.no_head))
    tip = _on_surface(bvh, Vector((0, -0.16, z_end - 0.012)), 0.020, up=0.0)
    barrel = G.ellipsoid(prefix + '_Whistle', tip + Vector((0.0, -0.002, -0.012)), (0.020, 0.016, 0.018), M['Whistle'], seg=14, rings=8)
    mouth = _rbox(prefix + '_Mouthpiece', tip + Vector((0.026, -0.001, -0.004)), (0.018, 0.009, 0.008), M['Whistle'], bevel=0.003, segs=1)
    ring = G.tube(prefix + '_Ring', [tip + Vector((-0.012, 0, 0.004)), tip + Vector((-0.010, 0, 0.016)), tip + Vector((0.0, 0, 0.020)),
                                     tip + Vector((0.010, 0, 0.016)), tip + Vector((0.012, 0, 0.004))], 0.0028, M['Whistle'], seg=6)
    out += [C.rigid(o, 'Spine2') for o in (barrel, mouth, ring)]
    return out


def old_fitness(body, face, M, skin):
    src = C.weight_source([body])
    rows = W.TEE
    nb = len(rows) - 1
    top = W.top('FIT_Top', rows, 6, None, (.806, .184, .124, -.004), [M['Top'], M['Top_Trim']],
                row_mat=[1] + [0] * (nb - 3) + [1, 1], hem_mat=1)
    _t(top, src, C.no_head)
    chev = W.front_decal('FIT_Chevron', [(-0.130, 1.168), (-0.098, 1.168), (0.0, 1.118), (0.098, 1.168), (0.130, 1.168), (0.0, 1.090)],
                         top, M['Top_Trim'], 0.003, step=0.012)
    out = [top] + _decal_t([chev], top)
    out += _whistle('FIT', M, top)
    shorts = W.bottoms('FIT_Shorts', [(.70, .090), (.676, .092), (.668, .086)], [M['Shorts']])
    _t(shorts, src)
    out += [shorts] + _decal_t(W.leg_stripes('FIT_Stripe', shorts, M['Shorts_Stripe'], offsets=(0.0,), width=0.024, z0=0.675, z1=0.86),
                               shorts)
    out.append(_t(W.plain_socks('FIT_Socks', M['Socks'], top=0.165), src))
    out += W.shoes('FIT', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    out += W.wristbands('FIT_Band', M['Bands'])                            # TASK-000281: bald, no headband
    out += _shaker('FIT', M)
    return out

# ------------------------------------------------------------------ OLD_COURIER
def baseball_cap(prefix, cap_m, peak_m):
    base = W.zprofile([(0, 1.662), (90, 1.646), (180, 1.626)])
    up = lambda dz: (lambda phi: base(phi) + dz)
    rows = [('fit', base, 0.006), ('fit', up(0.030), 0.012), ('fit', lambda phi: 1.748, 0.015), ('fit', lambda phi: 1.786, 0.016),
            ('fit', lambda phi: 1.814, 0.016)]
    crown = W.ring_loft(prefix + '_Crown', rows, [cap_m], seg=32)
    pk = W.peak(prefix + '_Peak', peak_m, base, length=0.082, droop=0.016, curve=0.014, span=62, off=0.008, thick=0.008)
    btn = G.ellipsoid(prefix + '_Button', (0, 0, B.HEAD_TOP + 0.020), (0.012, 0.012, 0.006), cap_m, seg=10, rings=6)
    return [C.rigid(o, 'Head') for o in (crown, pk, btn)], base


def _stand_collar(name, material, open_deg=14.0, seg=24):
    vs, fs, cols = [], [], []
    a0, a1 = math.radians(open_deg), math.radians(360 - open_deg)
    rows = ((1.250, 0.162, 0.158), (1.296, 0.158, 0.154), (1.304, 0.154, 0.150))
    for j in range(seg + 1):
        phi = a0 + (a1 - a0) * j / seg
        col = []
        for z, rx, ry in rows:
            col.append(len(vs)); vs.append(Vector((rx * math.sin(phi), -ry * math.cos(phi), z)))
        cols.append(col)
    for j in range(seg):
        a, b = cols[j], cols[j + 1]
        for i in range(len(rows) - 1):
            fs.append((a[i], b[i], b[i + 1], a[i + 1]))
    ob = G.from_data(name, vs, fs, material, True, fix_normals=False)
    G.solidify(ob, 0.006, offset=0.0)
    return ob


def _phone_in_hand(prefix, M):
    """Phone along the fingers, screen to the front, thumb on the screen (rest pose, right hand)."""
    wr, a, n, f = _hand_axes('Right')
    c = wr + a * 0.088 + f * 0.064 + n * 0.006
    rot = _frame(a, f, a.cross(f).normalized())
    body = _rbox(prefix + '_Phone', c, (0.086, 0.007, 0.043), M['Phone'], bevel=0.006, segs=2, rot=rot)
    screen = _rbox(prefix + '_Screen', c + f * 0.0075, (0.076, 0.0012, 0.036), M['Screen'], bevel=0.0, rot=rot)
    return [W.prop(o, 'RightHand') for o in (body, screen)]


def _cube_bag(prefix, M, jacket):
    bvh = G.bvh_of([jacket])
    hit = bvh.ray_cast(Vector((0, 0.9, 1.06)), Vector((0, -1, 0)), 1.8)
    back = hit[0].y if hit[0] is not None else 0.16
    hx, hy, hz = 0.235, 0.195, 0.245
    c = Vector((0.0, back + 0.012 + hy, 1.065))
    out = [_rbox(prefix + '_Box', c, (hx, hy, hz), M['Box'], bevel=0.030, segs=3)]
    out.append(_rbox(prefix + '_Lid', c + Vector((0, 0, hz - 0.052)), (hx + 0.005, hy + 0.005, 0.012), M['Box_Trim'], bevel=0.012, segs=2))
    for k, dz in enumerate((-0.110, -0.150)):
        out.append(_rbox(f'{prefix}_Reflect_{k}', c + Vector((0, 0, dz)), (hx + 0.004, hy + 0.004, 0.010), M['Reflect'], bevel=0.010, segs=2))
    out.append(_rbox(prefix + '_Handle', c + Vector((0, 0.0, hz + 0.010)), (0.070, 0.016, 0.010), M['Box_Trim'], bevel=0.006, segs=1))
    out = [C.rigid(o, 'Spine2') for o in out]
    # shoulder straps from the top of the box over the shoulders, down the chest; a sternum strap between them
    jsrc = C.weight_source([jacket])
    ends = {}
    for s in (1, -1):
        raw = [Vector((s * 0.090, back + 0.010, 1.215)), Vector((s * 0.140, 0.110, 1.240)), Vector((s * 0.162, 0.020, 1.262)),
               Vector((s * 0.156, -0.090, 1.238)), Vector((s * 0.130, -0.150, 1.150)), Vector((s * 0.134, -0.152, 1.040)),
               Vector((s * 0.168, -0.124, 0.960)), Vector((s * 0.200, -0.050, 0.920)), Vector((s * 0.210, 0.060, 0.915))]
        pts = [_on_surface(bvh, p, 0.007) for p in raw]
        pts[0] = Vector((s * 0.090, back + 0.016, 1.205))
        pts[-1] = Vector((s * 0.205, back + 0.020, 0.900))
        st = C.strap(f'{prefix}_Strap_{s}', pts, M['Straps'], width=0.040, thick=0.007,
                     normal_fn=lambda q: (lambda r: r[1] if r[1].dot(Vector((q.x, q.y, 0.3))) >= 0 else -r[1])(bvh.find_nearest(q)))
        out.append(_t(st, jsrc, C.no_head))
        ends[s] = pts[4]
    chest = [_on_surface(bvh, Vector((x, -0.17, 1.120)), 0.013, up=0.0) for x in (-0.13, -0.07, 0.0, 0.07, 0.13)]
    out.append(_t(C.strap(prefix + '_ChestStrap', chest, M['Straps'], width=0.022, thick=0.005,
                          normal_fn=lambda q: Vector((0, -1, 0))), jsrc, C.no_head))
    bk = _rbox(prefix + '_ChestBuckle', chest[2] + Vector((0, -0.006, 0)), (0.018, 0.005, 0.014), M['Box_Trim'], bevel=0.003, segs=1)
    out.append(_t(bk, jsrc, C.no_head))
    return out


def _sweat_drop(prefix, material):
    p, nrm = W.head_at(math.radians(-62), W.h_of(1.640), 0.010)
    path = [p + Vector((0, 0, 0.020)), p + Vector((0, 0, 0.008)), p + Vector((0, 0, -0.004)), p + Vector((0, 0, -0.014))]
    drop = G.tube(prefix + '_Sweat', path, lambda i, k: (0.0015, 0.007, 0.0095, 0.006)[i], material, seg=10)
    return [C.rigid(drop, 'Head')]


def old_courier(body, face, M, skin):
    src = C.weight_source([body])
    rows = W.HOODIE
    jacket = W.top('COURIER_Jacket', rows, 7, W.HOODIE_SLEEVE, (.750, .174, .118, -.010),
                   [M['Jacket'], M['Jacket_Panel'], M['Jacket_Rib']],
                   row_mat=[2] + [0] * 5 + [1] * 6 + [2, 2], sleeve_mat=[1] * 4 + [0] * 5 + [2] * 5, hem_mat=2)
    _t(jacket, src, C.no_head)
    jsrc = C.weight_source([jacket])
    zip_ = W.front_decal('COURIER_Zip', [(-0.006, 0.745), (0.006, 0.745), (0.006, 1.262), (-0.006, 1.262)], jacket, M['Jacket_Rib'], 0.003,
                         step=0.012)
    collar = _stand_collar('COURIER_Collar', M['Jacket_Rib'])
    out = [jacket, _t(collar, jsrc, C.no_head)] + _decal_t([zip_], jacket)
    out += _cube_bag('COURIER_Bag', M, jacket)
    pants = W.bottoms('COURIER_Pants', W.LEGS_SWEAT, [M['Pants'], M['Pants_Rib']], cuff=W.SWEAT_CUFF)
    _t(pants, src)
    pockets = []
    for s in (1, -1):
        pockets.append(G.decal(f'COURIER_CargoPocket_{s}', [(-0.046, 0.470), (0.046, 0.470), (0.046, 0.585), (-0.046, 0.585)], G.SIDE(s),
                               [pants], 0.003, M['Pocket'], step=0.016, thickness=0.004))
        pockets.append(G.decal(f'COURIER_CargoFlap_{s}', [(-0.050, 0.568), (0.050, 0.568), (0.050, 0.598), (-0.050, 0.598)], G.SIDE(s),
                               [pants], 0.0075, M['Pants_Rib'], step=0.016, thickness=0.003))
    out += [pants] + _decal_t(pockets, pants)
    out.append(_t(W.plain_socks('COURIER_Socks', M['Socks'], top=0.21), src))
    out += W.shoes('COURIER', M['Shoe_Upper'], M['Shoe_Sole'], M['Shoe_Lace'])
    cap, base = baseball_cap('COURIER_Cap', M['Cap'], M['Cap_Peak'])
    out += cap
    out.append(_head_band_hair('COURIER_Hair', M['Hair'], lambda phi: base(phi) + 0.012, arc=(48, 312)))
    out += _sweat_drop('COURIER', M['Sweat'])
    out += _phone_in_hand('COURIER', M)
    return out

# ------------------------------------------------------------------ OLD_TOURIST
def _flower_outline(cx, cz, r, rot=0.0, n=30, petals=5):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (0.42 + 0.58 * abs(math.cos(petals / 2 * (a - rot))) ** 0.6)
        pts.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
    return pts


def _leaf_outline(cx, cz, length, width, ang, n=12):
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = length / 2 * math.cos(t), width / 2 * math.sin(t) * abs(math.cos(t / 2)) ** 0.3
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cz + x * math.sin(ang) + y * math.cos(ang)))
    return pts


def _hawaii(prefix, shirt, M):
    """Hibiscus flowers with a leaf each: front, back and on top of the short sleeves."""
    out = []
    spots = [('F', -0.140, 0.975, 0.044, 0.3), ('F', 0.150, 1.010, 0.040, 1.1), ('F', -0.112, 1.168, 0.036, 0.7),
             ('F', 0.128, 1.172, 0.034, 0.2), ('F', 0.175, 0.870, 0.034, 0.9), ('F', -0.180, 0.860, 0.036, 0.5),
             ('B', -0.090, 0.880, 0.046, 0.4), ('B', 0.110, 0.990, 0.044, 1.0), ('B', -0.110, 1.110, 0.042, 0.1),
             ('B', 0.070, 1.190, 0.036, 0.8), ('B', 0.000, 1.010, 0.030, 0.5), ('B', 0.160, 0.850, 0.034, 0.6),
             ('T', 0.275, 0.000, 0.032, 0.3), ('T', -0.275, 0.010, 0.032, 0.9)]
    for k, (side, cx, cz, r, rot) in enumerate(spots):
        axes = {'F': G.FRONT(), 'B': G.BACK(), 'T': W.TOP(1.6)}[side]
        fm = M['Flower'] if k % 3 != 1 else M['Flower_2']
        ang = rot * 2.0 + 2.3
        lx, lz = cx + math.cos(ang) * r * 0.95, cz + math.sin(ang) * r * 0.95
        leaf = G.decal(f'{prefix}_Leaf_{k}', _leaf_outline(lx, lz, r * 1.5, r * 0.75, ang), axes, [shirt], 0.0022, M['Leaf'], step=0.020)
        fl = G.decal(f'{prefix}_Flower_{k}', _flower_outline(cx, cz, r, rot), axes, [shirt], 0.0034, fm, step=0.016)
        ce = G.decal(f'{prefix}_FlowerC_{k}', C.ellipse(cx, cz, r * 0.22, r * 0.22, 8), axes, [shirt], 0.0046, M['Flower_Centre'], step=0.05)
        out += [leaf, fl, ce]
    return out


def bucket_hat_band(prefix, hat_m, band_m):
    """W.bucket_hat with a band round the crown base."""
    base = W.zprofile([(0, 1.676), (90, 1.660), (180, 1.646)])
    rows = [('fit', base, 0.006), (1.700, 0.147, 0.143, 0.0, 0.010), (1.712, 0.151, 0.147, 0.0, 0.010), (1.746, 0.135, 0.131, 0.0, 0.006),
            (1.768, 0.090, 0.088, 0.0, 0.003), (1.776, 0.030, 0.030, 0.0, 0.0)]
    crown = W.ring_loft(prefix + '_Crown', rows, [hat_m, band_m], row_mat=[1, 1, 0, 0, 0, 0], seg=32)
    droop = W.profile([(0, 0.012), (90, 0.024), (180, 0.028)])
    vs, fs, seg = [], [], 32
    rings = [[], [], []]
    for j in range(seg):
        phi = 2 * math.pi * j / seg - math.pi
        p0, _ = W.head_at(phi, base(phi), 0.006)
        o = Vector((math.sin(phi), -math.cos(phi), 0))
        for k, (w, d) in enumerate(((0.0, 0.0), (0.036, 0.45), (0.072, 1.0))):
            rings[k].append(len(vs)); vs.append(p0 + o * w + Vector((0, 0, -droop(phi) * d)))
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            fs.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    brim = G.from_data(prefix + '_Brim', vs, fs, hat_m, True, fix_normals=False)
    G.solidify(brim, 0.006, offset=0.0)
    return [C.rigid(o, 'Head') for o in (crown, brim)], base


def _sandals(prefix, sock_m, strap_m, sole_m):
    """Socks in sandals: the sock-coloured foot on a chunky sole, toe and instep straps, a heel strap."""
    out = []
    for s in (1, -1):
        up, so, top_h, yaw = C.sneaker(f'{prefix}_Foot_{s}', s, sock_m, sole_m)
        cx = s * B.LEG_X
        toe = W.wrap_band(f'{prefix}_ToeStrap_{s}', up, cx - s * 0.010, [-0.132, -0.150, -0.168], strap_m, zc=0.045)
        mid = W.wrap_band(f'{prefix}_Instep_{s}', up, cx - s * 0.004, [-0.030, -0.050, -0.070], strap_m, zc=0.047)
        bvh = G.bvh_of([up])
        ring = []
        for k in range(13):
            a = math.radians(-100 + 200 * k / 12)          # 0 = straight back (+y)
            d = Vector((math.sin(a), math.cos(a), 0.0))
            o = Vector((cx, 0.020, 0.070)) + d * 0.3
            hit = bvh.ray_cast(o, -d, 0.6)
            ring.append(hit[0] + hit[1] * 0.006 if hit[0] is not None else Vector((cx, 0.02, 0.07)) + d * 0.06)
        heel = G.tube(f'{prefix}_Heel_{s}', ring, 0.0085, strap_m, seg=6)
        wf = C.shoe_weights(s)
        for o in (up, so, toe, mid, heel):
            C.set_weights(o, [wf(o.matrix_world @ v.co) for v in o.data.vertices])
        out += [up, so, toe, mid, heel]
    return out


def _camera(prefix, M, shirt, collar):
    bvh = G.bvh_of([shirt, collar])
    ssrc = C.weight_source([shirt])
    hit = bvh.ray_cast(Vector((0, -0.9, 1.035)), Vector((0, 1, 0)), 1.8)
    fy = hit[0].y if hit[0] is not None else -0.14
    c = Vector((0.0, fy - 0.034, 1.035))
    parts = [_rbox(prefix + '_Body', c, (0.064, 0.030, 0.040), M['Camera'], bevel=0.008, segs=2),
             _rbox(prefix + '_Top', c + Vector((0.0, 0.0, 0.044)), (0.062, 0.026, 0.006), M['Camera_Top'], bevel=0.004, segs=1),
             _rbox(prefix + '_Prism', c + Vector((0.0, -0.002, 0.056)), (0.020, 0.018, 0.012), M['Camera'], bevel=0.005, segs=1),
             _cyl(prefix + '_Button', c + Vector((0.040, 0.0, 0.048)), c + Vector((0.040, 0.0, 0.058)), 0.007, M['Camera_Top'], seg=8),
             _cyl(prefix + '_Lens', c + Vector((0.0, -0.026, -0.002)), c + Vector((0.0, -0.068, -0.002)),
                  [(0.0, 0.028), (0.75, 0.026), (0.8, 0.030), (1.0, 0.030)], M['Camera'], seg=16),
             G.ellipsoid(prefix + '_Glass', c + Vector((0.0, -0.068, -0.002)), (0.023, 0.006, 0.023), M['Lens_Glass'], seg=14, rings=6)]
    out = [C.rigid(o, 'Spine1') for o in parts]
    for s in (1, -1):
        pts = _neck_cord(bvh, s, c.z + 0.026, 0.066, c.y + 0.010, off=0.006)
        pts[-1] = c + Vector((s * 0.068, 0.006, 0.024))
        out.append(_t(G.tube(f'{prefix}_Strap_{s}', pts, 0.0055, M['Camera_Strap'], seg=6), ssrc, C.no_head))
    return out


def _fanny_pack(prefix, M, shirt):
    bvh = G.bvh_of([shirt])
    ssrc = C.weight_source([shirt])
    z = 0.842
    pts = []
    for k in range(33):
        a = 2 * math.pi * k / 32
        p = Vector((0.24 * math.sin(a), -0.012 - 0.17 * math.cos(a), z))
        pts.append(_on_surface(bvh, p, 0.004, up=0.0))
    belt = C.strap(prefix + '_Belt', pts, M['Pack_Strap'], width=0.028, thick=0.005,
                   normal_fn=lambda q: (lambda r: r[1] if r[1].dot(Vector((q.x, q.y, 0))) >= 0 else -r[1])(bvh.find_nearest(q)))
    hit = bvh.ray_cast(Vector((0, -0.9, z)), Vector((0, 1, 0)), 1.8)
    fy = hit[0].y if hit[0] is not None else -0.15
    c = Vector((0.0, fy - 0.034, z - 0.006))
    pouch = G.ellipsoid(prefix + '_Pouch', c, (0.118, 0.040, 0.058), M['Pack'], seg=20, rings=10)
    for v in pouch.data.vertices:             # flatten the back against the belly, square up the shape
        if v.co.y > c.y + 0.006:
            v.co.y = c.y + 0.006 + (v.co.y - c.y - 0.006) * 0.35
    zp = G.tube(prefix + '_Zip', [c + Vector((0.090 * math.cos(a), -0.039 * math.sin(a) ** 0.5 - 0.004, 0.030 * math.sin(a) + 0.010))
                                  for a in [math.radians(15 + 150 * k / 10) for k in range(11)]], 0.0035, M['Zip'], seg=6)
    pull = _rbox(prefix + '_Pull', c + Vector((0.060, -0.046, 0.016)), (0.006, 0.003, 0.012), M['Zip'], bevel=0.002, segs=1)
    out = [_t(belt, ssrc)]
    out += [_t(o, ssrc, lambda p, w: {P + 'Hips': 0.5, P + 'Spine': 0.5}) for o in (pouch, zp, pull)]
    return out


def _sunscreen(prefix, material):
    tmp = G.ellipsoid(prefix + '_tmp', B.NOSE_C, B.NOSE_R, material, seg=20, rings=12)
    try:
        pts = [(x * 1.0, z) for x, z in C.ellipse(0.0, B.NOSE_C[2] + 0.012, 0.030, 0.026, 16)]
        smear = G.decal(prefix + '_Nose', pts, G.FRONT(), [tmp], 0.0016, material, step=0.010)
    finally:
        me = tmp.data
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(me)
    return [C.rigid(smear, 'Head')]


def _selfie_stick(prefix, M, arm_down):
    """Long selfie stick held up and out to the right with the phone turned to the face; modelled in the idle pose."""
    q, Wt, Wi = _idle_hand('Right', arm_down)
    wr, a, n, f = _hand_axes('Right')
    grip = Wi + q @ (a * 0.070 + n * 0.024)
    d = Vector((-0.40, -0.34, 0.85)).normalized()
    L = 1.08
    parts = [_cyl(prefix + '_Grip', grip - d * 0.085, grip + d * 0.075, [(0.0, 0.016), (0.08, 0.018), (1.0, 0.016)], M['Stick_Grip'], seg=10),
             _cyl(prefix + '_Stick', grip + d * 0.07, grip + d * L, [(0.0, 0.0105), (0.45, 0.0105), (0.46, 0.0085), (1.0, 0.0085)],
                  M['Stick'], seg=8)]
    end = grip + d * L
    head = Vector((0.0, -0.05, 1.55))
    nrm = (head - end).normalized()
    upv = (Vector((0, 0, 1)) - nrm * nrm.z).normalized()
    side = upv.cross(nrm).normalized()
    pc = end + upv * 0.020 + nrm * 0.010
    rot = _frame(side, upv, nrm)
    parts.append(_rbox(prefix + '_Clamp', end + nrm * 0.000, (0.050, 0.012, 0.010), M['Stick'], bevel=0.004, segs=1, rot=rot))
    parts.append(_rbox(prefix + '_Phone', pc + nrm * 0.010, (0.044, 0.086, 0.006), M['Phone'], bevel=0.006, segs=2, rot=rot))
    parts.append(_rbox(prefix + '_Screen', pc + nrm * 0.0165, (0.038, 0.076, 0.0012), M['Screen'], bevel=0.0, rot=rot))
    _idle_to_rest(parts, 'Right', arm_down)
    return [W.prop(o, 'RightHand') for o in parts]


def old_tourist(body, face, M, skin):
    src = C.weight_source([body])
    shirt = _t(W.top('TOUR_Shirt', W.TEE, 6, W.SLEEVE_SHORT, (.806, .184, .124, -.004), [M['Shirt']]), src, C.no_head)
    ssrc = C.weight_source([shirt])
    collar = _t(W.collar('TOUR_Collar', M['Shirt'], open_deg=36, tip=0.030), ssrc, C.no_head)
    deco = [W.front_decal('TOUR_OpenNeck', [(-0.070, 1.262), (0.070, 1.262), (0.0, 1.150)], shirt, skin, 0.0022, step=0.010)]
    deco += W.buttons('TOUR_Btn', shirt, M['Buttons'], [(0.0, z) for z in (1.120, 1.030, 0.940, 0.850)], r=0.0085)
    out = [shirt, collar] + _decal_t(deco + _hawaii('TOUR', shirt, M), shirt)
    out += _camera('TOUR_Camera', M, shirt, collar)
    out += _fanny_pack('TOUR_Pack', M, shirt)
    shorts = W.bottoms('TOUR_Shorts', [(.70, .090), (.60, .094), (.52, .096), (.462, .097), (.452, .097), (.458, .090)], [M['Shorts']])
    _t(shorts, src)
    pockets = []
    for s in (1, -1):
        pockets.append(G.decal(f'TOUR_CargoPocket_{s}', [(-0.050, 0.500), (0.050, 0.500), (0.050, 0.610), (-0.050, 0.610)], G.SIDE(s),
                               [shorts], 0.003, M['Shorts_Pocket'], step=0.016, thickness=0.004))
        pockets.append(G.decal(f'TOUR_CargoFlap_{s}', [(-0.054, 0.592), (0.054, 0.592), (0.054, 0.622), (-0.054, 0.622)], G.SIDE(s),
                               [shorts], 0.0075, M['Shorts_Pocket'], step=0.016, thickness=0.003))
    out += [shorts] + _decal_t(pockets, shorts)
    out.append(_t(W.plain_socks('TOUR_Socks', M['Socks'], top=0.385), src))
    out += _sandals('TOUR_Sandal', M['Socks'], M['Sandal'], M['Sandal_Sole'])
    hat, base = bucket_hat_band('TOUR_Hat', M['Hat'], M['Hat_Band'])
    out += hat
    out.append(_head_band_hair('TOUR_Hair', M['Hair'], lambda phi: base(phi) + 0.010, arc=(52, 308)))
    out += _sunscreen('TOUR_Sunscreen', M['Sunscreen'])
    out += _selfie_stick('TOUR_Selfie', M, TYPES['OLD_TOURIST'].get('arm_down', 74.0))
    return out



def _drop_slots(type_id, *slots):
    """TASK-000281: slots of garments a type no longer wears (bald: no hat, no hair)."""
    spec = TYPES[type_id]
    for k in slots:
        spec['slots'].pop(k, None)
        for cw in spec['colourways']:
            cw.pop(k, None)

_drop_slots('OLD_FITNESS', 'Headband', 'Hair')

BUILDERS = {'OLD_FITNESS': old_fitness, 'OLD_COURIER': old_courier, 'OLD_TOURIST': old_tourist}
