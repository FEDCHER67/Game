"""District pool 'Старый город' (TASK-000270) on the base Sausage Buddy: the streamer, the student, the office worker;
TASK-000272: the vaper moved here from 'Переход' with his first design kept (OLD_VAPER builds
from buddy_pool_transit2's TRANSIT_VAPER builder and slots).
Same format as buddy_types.TYPES / BUILDERS; every garment and prop has its own material slot <TYPE>_<Slot>.
Carried props are modelled in the idle pose (world space, arms hanging) and baked back to the hand's T-pose frame,
so they sit in the hand exactly where the idle renders show them."""
import math
import bpy
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_anim as A
import buddy_types as T

P = 'mixamorig:'
GROUP = 'Старый город'
METAL = 'metal'

TYPES = {
    'OLD_STREAMER': dict(
        label='Стример (редко)', group=GROUP, no_ears=True, hand_props=True,
        look=dict(skin=(242, 212, 192), nose=(236, 178, 160), rim=(196, 132, 136), brow=(70, 54, 46)),
        face=dict(Surprised=0.4, Happy=0.25),
        slots={'Hoodie': ((40, 42, 52), 0.9), 'Hoodie_Rib': ((30, 32, 40), 0.9), 'Print': ((250, 66, 150), 0.7),
               'Pants': ((126, 130, 140), 0.95), 'Pants_Rib': ((104, 108, 118), 0.95), 'Socks': ((244, 242, 236), 0.9),
               'Slides': ((34, 36, 42), 0.55), 'Hair': ((66, 50, 42), 0.8), 'EyeBags': ((168, 126, 156), 0.8),
               'Headset': ((28, 28, 32), 0.45), 'Headset_Pad': ((52, 52, 58), 0.9), 'Headset_Glow': ((70, 240, 130), 0.3),
               'Mic': ((22, 22, 24), 0.6), 'Stick': ((30, 30, 34), 0.4), 'RingLight': ((252, 250, 240), 0.3),
               'Phone': ((22, 22, 26), 0.25), 'Screen': ((120, 200, 255), 0.15)},
        colourways=[{'Hoodie': (232, 232, 228), 'Hoodie_Rib': (210, 210, 206), 'Print': (40, 170, 240), 'Pants': (40, 42, 50),
                     'Pants_Rib': (30, 32, 40), 'Headset': (238, 238, 236), 'Headset_Glow': (40, 170, 240), 'Slides': (232, 64, 60)},
                    {'Hoodie': (96, 62, 176), 'Hoodie_Rib': (80, 50, 150), 'Print': (250, 222, 60), 'Pants': (54, 58, 66),
                     'Pants_Rib': (42, 46, 54), 'Headset_Glow': (250, 70, 160), 'Socks': (250, 222, 60), 'Hair': (232, 92, 140)}]),
    'OLD_STUDENT': dict(
        label='Студент', group=GROUP, face=dict(Surprised=0.3),
        slots=dict(T.TYPES['CITY_STUDENT']['slots'],
                   **{'Phones': ((236, 66, 58), 0.4), 'Phones_Pad': ((40, 40, 44), 0.9), 'Phones_Plate': ((240, 238, 232), 0.35),
                      'Can': ((132, 222, 52), 0.3), 'Can_Band': ((26, 26, 30), 0.35), 'Can_Metal': ((206, 208, 214), 0.25, METAL)}),
        colourways=[dict(T.TYPES['CITY_STUDENT']['colourways'][0], Phones=(240, 240, 236), Phones_Plate=(40, 40, 44),
                         Can=(60, 140, 240)),
                    dict(T.TYPES['CITY_STUDENT']['colourways'][1], Phones=(40, 40, 44), Phones_Plate=(236, 66, 58),
                         Can=(250, 120, 30), Can_Band=(250, 246, 236))]),
    'OLD_OFFICE': dict(
        label='Работник офиса', group=GROUP, face=dict(Worried=0.35, Blink=0.3),
        slots=dict(T.TYPES['CITY_CLERK']['slots'],
                   **{'Lanyard': ((40, 92, 186), 0.7), 'Clip': ((196, 198, 204), 0.3, METAL), 'Badge': ((248, 248, 244), 0.4),
                      'Badge_Stripe': ((40, 92, 186), 0.5), 'Badge_Photo': ((236, 170, 128), 0.6), 'Badge_Line': ((60, 62, 70), 0.6),
                      'EyeBags': ((168, 130, 146), 0.8), 'Cup': ((246, 244, 238), 0.6), 'Cup_Sleeve': ((150, 104, 64), 0.85),
                      'Cup_Lid': ((40, 36, 34), 0.45)}),
        colourways=[dict(T.TYPES['CITY_CLERK']['colourways'][0], Lanyard=(196, 40, 48), Badge_Stripe=(196, 40, 48),
                         Cup_Lid=(246, 244, 238), Cup_Sleeve=(60, 120, 80)),
                    dict(T.TYPES['CITY_CLERK']['colourways'][1], Lanyard=(42, 140, 96), Badge_Stripe=(42, 140, 96),
                         Cup=(232, 206, 160), Cup_Sleeve=(232, 206, 160), Cup_Lid=(246, 244, 238))]),
}

# ------------------------------------------------------------------ prop helpers (idle pose <-> T-pose)
def _idle(bone):
    """Armature-space matrix of a bone in the idle pose (frame 1 of 'Idle')."""
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    return A.pose_from_joints(rig, W.REST, A.idle_joints())[P + bone]


def _hand_frame(side):
    """Idle-pose palm centre and axes of a hand: finger direction (down), palm normal, thumb direction (forward)."""
    bone = side + 'Hand'
    K = _idle(bone) @ W.bone_rest(bone).inverted()          # T-pose -> idle
    s = 1 if side == 'Left' else -1
    R3 = K.to_3x3()
    return (K @ Vector((s * 0.690, 0.0, 1.157)), (R3 @ Vector((s, 0, 0))).normalized(),
            (R3 @ Vector((0, 0, -1))).normalized(), (R3 @ Vector((0, -1, 0))).normalized())


def _held(objs, side):
    """Meshes modelled in the idle pose -> baked to the T-pose, rigid on the hand bone, flagged as carried props."""
    bone = side + 'Hand'
    K = W.bone_rest(bone) @ _idle(bone).inverted()
    for ob in objs:
        ob.data.transform(K)
        ob.data.update()
        W.prop(ob, bone)
    return objs


def _frame(axis, ref=Vector((0, 0, 1))):
    """3x3 matrix whose Z column is `axis`."""
    z = Vector(axis).normalized()
    x = ref.cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def _lathe(name, base, axis, rows, mats, seg=16, cap_start=True, cap_end=True):
    """Body of revolution: rows (h, r, mat index of the band from this row to the next) along `axis` from `base`."""
    F = _frame(axis)
    u, v, a = F.col[0], F.col[1], F.col[2]
    secs = [(Vector(base) + a * h, u, v, r, r) for h, r, _ in rows]
    return G.loft(name, secs, mats[0], seg=seg, cap_start=cap_start, cap_end=cap_end, mat_rows=[m for _, _, m in rows[:-1]],
                  extra=list(mats[1:]))


def _torus(name, center, normal, R, r, material, seg=28, tseg=8):
    F = _frame(normal)
    u, v, n = F.col[0], F.col[1], F.col[2]
    vs, fs = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        d = u * math.cos(a) + v * math.sin(a)
        for j in range(tseg):
            b = 2 * math.pi * j / tseg
            vs.append(Vector(center) + d * (R + r * math.cos(b)) + n * (r * math.sin(b)))
    for i in range(seg):
        for j in range(tseg):
            a0, a1 = i * tseg, ((i + 1) % seg) * tseg
            fs.append((a0 + j, a1 + j, a1 + (j + 1) % tseg, a0 + (j + 1) % tseg))
    return G.from_data(name, vs, fs, material, True)


def _rename(objs, old, new):
    for o in objs:
        if o.name.startswith(old):
            o.name = new + o.name[len(old):]
        elif not o.name.startswith(new):
            o.name = new + '_' + o.name
    return objs


def _ear_cup(prefix, center, axis, M, shell, pad, plate, r=0.050, depth=0.040):
    """Headphone cup: soft pad on the inner side (toward -axis), hard shell, a coloured plate on the outer face."""
    rows = [(0.0, r * 0.70, 1), (0.004, r * 0.92, 1), (0.012, r * 0.98, 1), (0.014, r * 0.96, 0), (0.018, r * 1.0, 0),
            (depth - 0.006, r * 0.98, 0), (depth, r * 0.82, 0)]
    cup = _lathe(prefix + '_Cup', Vector(center) - Vector(axis).normalized() * (depth / 2), axis, rows, [M[shell], M[pad]], seg=18)
    a = Vector(axis).normalized()
    pl = G.ellipsoid(prefix + '_Plate', Vector(center) + a * (depth / 2 + 0.001), (r * 0.62, r * 0.62, 0.005), M[plate],
                     rot=_frame(a), seg=16, rings=6)
    return [cup, pl]

# ------------------------------------------------------------------ OLD_STREAMER
# 8-bit heart as one stepped outline in grid units (x right, y down), 7 x 6 cells
PIXEL_HEART = [(1, 0), (3, 0), (3, 1), (4, 1), (4, 0), (6, 0), (6, 1), (7, 1), (7, 3), (6, 3), (6, 4), (5, 4), (5, 5), (4, 5), (4, 6),
               (3, 6), (3, 5), (2, 5), (2, 4), (1, 4), (1, 3), (0, 3), (0, 1), (1, 1)]


def _pixel_heart(prefix, target, material, cz=1.108, px=0.018):
    pts = [(px * (x - 3.5), cz + px * (3 - y)) for x, y in PIXEL_HEART]
    return [W.front_decal(prefix, pts[::-1], target, material, 0.0028, step=0.006)]


def _headset(prefix, M):
    """Gaming headset: padded band over the head, big cups over the ears with glowing plates, boom mic to the mouth."""
    out = []
    ez = B.EAR_C[2] + 0.004
    for s in (1, -1):
        out += _ear_cup(f'{prefix}_Cup_{s}', (s * (B.HEAD_R + 0.020), 0.006, ez), (s, 0, 0), M, 'Headset', 'Headset_Pad', 'Headset_Glow',
                        r=0.054, depth=0.044)
    # band: from one cup up over the head and down to the other, a flat strap riding on the hair
    h0 = W.h_of(ez + 0.045)
    hs = [h0 + (W.H_POLE - 0.004 - h0) * k / 12 for k in range(13)]
    pts = [W.head_at(math.radians(90), h, 0.030)[0] for h in hs] + [W.head_at(math.radians(-90), h, 0.030)[0] for h in reversed(hs)]
    band = C.strap(prefix + '_Band', pts, M['Headset'], width=0.034, thick=0.012,
                   normal_fn=lambda p: Vector((p.x, 0.0, max(0.0, p.z - B.HEAD_CYL_TOP))).normalized())
    out.append(band)
    # boom mic from the left cup round the cheek to the mouth corner
    path = [Vector((0.176, -0.020, ez - 0.012)), Vector((0.172, -0.070, 1.440)), Vector((0.140, -0.128, 1.414)),
            Vector((0.092, -0.165, 1.404)), Vector((0.060, -0.178, 1.402))]
    out.append(G.tube(prefix + '_Boom', path, 0.0052, M['Mic'], seg=8))
    out.append(G.ellipsoid(prefix + '_MicTip', path[-1] + Vector((-0.006, -0.002, 0)), (0.016, 0.013, 0.013), M['Mic'], seg=12, rings=8))
    return [C.rigid(o, 'Head') for o in out]


def _ring_light_rig(prefix, M):
    """Phone in a mini ring light on a selfie/gimbal stick, held in the right hand in front of his face."""
    c, down, palm, fwd = _hand_frame('Right')
    ring_c = Vector((-0.125, -0.470, 1.290))
    face_pt = Vector((0.0, -0.140, 1.500))
    n = (face_pt - ring_c).normalized()                   # the light and the phone screen look at his face
    grip = c + palm * 0.012
    d = (ring_c - grip).normalized()
    out = [G.tube(prefix + '_Handle', [grip - d * 0.060, grip + d * 0.070], 0.0175, M['Stick'], seg=12)]
    R_ring = 0.115
    up = (Vector((0, 0, 1)) - n * n.z).normalized()
    bottom = ring_c - up * R_ring
    out.append(G.tube(prefix + '_Rod', [grip + d * 0.070, bottom - up * 0.030], 0.0085, M['Stick'], seg=8))
    out.append(G.ellipsoid(prefix + '_Gimbal', bottom - up * 0.030, (0.020, 0.020, 0.020), M['Stick'], seg=12, rings=8))
    out.append(_torus(prefix + '_Ring', ring_c, n, R_ring, 0.016, M['RingLight'], seg=28, tseg=8))
    out.append(G.tube(prefix + '_Arm', [bottom - up * 0.030, ring_c - up * 0.060], 0.0060, M['Stick'], seg=8))
    # phone flat in the ring plane: half extents (across, along `up`, thickness along n)
    F = Matrix((up.cross(n).normalized(), up, n)).transposed()
    out.append(W.box(prefix + '_Phone', ring_c, (0.040, 0.080, 0.0045), M['Phone'], rot=F))
    out.append(W.box(prefix + '_Screen', ring_c + n * 0.0040, (0.036, 0.074, 0.0012), M['Screen'], rot=F))
    return _held(out, 'Right')


def old_streamer(body, face, M, skin):
    src = C.weight_source([body])
    hoodie, pocket, out = T._hoodie('OLD_STREAMER', M, src)
    out.append(T._hood_down('OLD_STREAMER', M['Hoodie']))
    out += T._decal_t(_pixel_heart('OLD_STREAMER_Heart', hoodie, M['Print']), hoodie)
    out.append(T._trousers('OLD_STREAMER', M, 'Pants', src, legs=W.LEGS_SWEAT, cuff=W.SWEAT_CUFF, cuff_slot='Pants_Rib'))
    out.append(T._t(W.plain_socks('OLD_STREAMER_Socks', M['Socks'], top=0.24), src))
    out += W.slides('OLD_STREAMER', M['Socks'], M['Slides'])
    out.append(W.hair('OLD_STREAMER_Hair', M['Hair'], 'slick'))
    out += _headset('OLD_STREAMER_Headset', M)
    out += T._face(skin, lambda head: W.eye_bags('OLD_STREAMER_EyeBag', M['EyeBags'], head))
    out += _ring_light_rig('OLD_STREAMER_Prop', M)
    return out

# ------------------------------------------------------------------ OLD_VAPER (TASK-000272)
def _vaper_spec():
    """The vaper moved from 'Переход' to the old town: Vadim kept his first design, so the same slots and colourways."""
    import buddy_pool_transit2 as V2
    spec = dict(V2.TYPES['TRANSIT_VAPER'])
    spec['group'] = GROUP
    spec['hand_props'] = True
    return spec


def old_vaper(body, face, M, skin):
    import buddy_pool_transit2 as V2
    return V2.transit_vaper(body, face, M, skin)


TYPES['OLD_VAPER'] = _vaper_spec()

# ------------------------------------------------------------------ OLD_STUDENT
def _neck_headphones(prefix, M, targets):
    """Big headphones resting round the neck: band over the hood roll at the back, cups on the collarbones."""
    bvh = G.bvh_of(targets)

    def over(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.5))) >= 0 else -nrm
        return loc + nrm * off
    out = []
    for s in (1, -1):
        cc = Vector((s * 0.118, -0.182, 1.262))
        axis = Vector((s * 0.42, -0.62, 0.66)).normalized()
        out += _ear_cup(f'{prefix}_Cup_{s}', cc, axis, M, 'Phones', 'Phones_Pad', 'Phones_Plate', r=0.058, depth=0.044)
    pts = []
    for k in range(25):                                   # azimuth from the back (+y): the band runs round behind the neck
        a = math.radians(-138 + 276 * k / 24)
        pts.append(over(Vector((0.215 * math.sin(a), 0.020 + 0.205 * math.cos(a), 1.316)), 0.014))
    path = ([Vector((math.copysign(0.140, pts[0].x), -0.172, 1.296))] + pts
            + [Vector((math.copysign(0.140, pts[-1].x), -0.172, 1.296))])
    out.append(G.tube(prefix + '_Band', path, 0.013, M['Phones'], seg=10))
    return [C.rigid(o, 'Spine2') for o in out]


def _energy_can(prefix, M):
    c, down, palm, fwd = _hand_frame('Right')
    base = c + palm * 0.048 + fwd * 0.016 + Vector((0, 0, -0.095))
    H, r = 0.185, 0.038
    rows = [(0.0, r * 0.80, 2), (0.004, r * 0.96, 2), (0.012, r, 0), (0.070, r, 1), (0.112, r, 0), (H - 0.016, r, 2), (H - 0.006, r * 0.86, 2),
            (H, r * 0.84, 2)]
    can = _lathe(prefix + '_Can', base, (0, 0, 1), rows, [M['Can'], M['Can_Band'], M['Can_Metal']], seg=16)
    tab = G.ellipsoid(prefix + '_Tab', base + Vector((0, -0.010, H + 0.001)), (0.008, 0.012, 0.0018), M['Can_Metal'], seg=10, rings=4)
    return _held([can, tab], 'Right')


def old_student(body, face, M, skin):
    M = dict(M, Beanie=M['Hoodie'])        # city_student still makes the beanie; it is removed right below
    out = _rename(T.city_student(body, face, M, skin), 'STUDENT', 'OLD_STUDENT')
    for o in [o for o in out if o.name.startswith('OLD_STUDENT_Beanie')]:      # TASK-000281: bald, no beanie
        out.remove(o)
        me = o.data
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    hood = [o for o in out if o.name.startswith('OLD_STUDENT_Hood') and 'Pouch' not in o.name]
    hoodie = [o for o in out if o.name == 'OLD_STUDENT_Hoodie']
    out += _neck_headphones('OLD_STUDENT_Phones', M, hood + hoodie)
    out += _energy_can('OLD_STUDENT_Prop', M)
    return out

# ------------------------------------------------------------------ OLD_OFFICE
def _lanyard_badge(prefix, M, shirt, collar):
    bvh = G.bvh_of([shirt, collar])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    out = []
    for s in (1, -1):
        raw = [(0.168 * math.sin(math.radians(a)), 0.164 * math.cos(math.radians(a)), 1.276 - 0.012 * a / 90) for a in range(0, 91, 10)]
        raw += [(0.150, -0.060, 1.246), (0.116, -0.132, 1.198), (0.064, -0.162, 1.128), (0.016, -0.172, 1.074)]
        pts = [on(Vector((s * x, y, z)), 0.005)[0] for x, y, z in raw]
        out.append(C.strap(f'{prefix}_Lanyard_{s}', pts, M['Lanyard'], width=0.018, thick=0.003, normal_fn=lambda q: on(q, 0.0)[1]))
    cp, cn = on(Vector((0.0, -0.17, 1.062)), 0.011)
    out.append(W.box(prefix + '_Clip', cp, (0.010, 0.004, 0.012), M['Clip']))
    card = W.front_decal(prefix + '_Badge', [(-0.044, 0.928), (0.044, 0.928), (0.044, 1.054), (-0.044, 1.054)], shirt, M['Badge'], 0.011,
                         thickness=0.003, step=0.008)
    out.append(card)
    for name, rect, m in (('Stripe', (-0.044, 1.030, 0.044, 1.054), 'Badge_Stripe'), ('Photo', (-0.033, 0.968, -0.004, 1.018), 'Badge_Photo'),
                          ('Line_0', (0.006, 1.004, 0.034, 1.012), 'Badge_Line'), ('Line_1', (0.006, 0.986, 0.026, 0.994), 'Badge_Line'),
                          ('Line_2', (-0.033, 0.944, 0.033, 0.952), 'Badge_Line')):
        x0, z0, x1, z1 = rect
        out.append(G.decal(f'{prefix}_Badge{name}', [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], W.FRONT(), [card], 0.0012, M[m], step=0.008))
    return out


def _coffee(prefix, M):
    c, down, palm, fwd = _hand_frame('Left')
    base = c + palm * 0.050 + fwd * 0.016 + Vector((0, 0, -0.090))
    k = 1.25                                               # a big 'grande' cup: he needs it
    rows = [(0.0, 0.029, 0), (0.030, 0.0322, 0), (0.030, 0.0342, 1), (0.078, 0.0378, 1), (0.078, 0.0362, 0), (0.112, 0.0392, 0),
            (0.112, 0.0418, 2), (0.122, 0.0418, 2), (0.126, 0.0380, 2), (0.136, 0.0330, 2), (0.138, 0.012, 2)]
    rows = [(h * k, r * k, m) for h, r, m in rows]
    cup = _lathe(prefix + '_Cup', base, (0, 0, 1), rows, [M['Cup'], M['Cup_Sleeve'], M['Cup_Lid']], seg=18)
    sip = G.ellipsoid(prefix + '_Sip', base + Vector((0, -0.030, 0.137 * k)), (0.009, 0.006, 0.004), M['Cup_Lid'], seg=8, rings=4)
    return _held([cup, sip], 'Left')


def old_office(body, face, M, skin):
    out = _rename(T.city_clerk(body, face, M, skin), 'CLERK', 'OLD_OFFICE')
    shirt = next(o for o in out if o.name == 'OLD_OFFICE_Shirt')
    collar = next(o for o in out if o.name == 'OLD_OFFICE_Collar')
    ssrc = C.weight_source([shirt])
    out += [T._t(o, ssrc, C.no_head) for o in _lanyard_badge('OLD_OFFICE', M, shirt, collar)]
    out += T._face(skin, lambda head: W.eye_bags('OLD_OFFICE_EyeBag', M['EyeBags'], head))
    out += _coffee('OLD_OFFICE_Prop', M)
    return out



def _drop_slots(type_id, *slots):
    """TASK-000281: slots of garments a type no longer wears (bald: no hat, no hair)."""
    spec = TYPES[type_id]
    for k in slots:
        spec['slots'].pop(k, None)
        for cw in spec['colourways']:
            cw.pop(k, None)

_drop_slots('OLD_STUDENT', 'Beanie')

BUILDERS = {'OLD_STREAMER': old_streamer, 'OLD_STUDENT': old_student, 'OLD_OFFICE': old_office, 'OLD_VAPER': old_vaper}
