"""District pool 'Городской пляж' (City Beach, TASK-000540/541/542/544/545, Vadim). Plain figurines in the vibe of the
approved pool, undressed for the beach (TASK-000542: no giant gimmicks, no lettering, little detail):
  BEACH_CORN         the pushy corn seller in flip-flops with a silver thermal bag of hot corn (v03)
  BEACH_CASTLE       the dumb grown-up who builds sand pies: a kid's bucket of sand and a spade (v01)
  BEACH_SUNBURN      the dumb sunburnt tourist: lobster red, bald, trunks; also lies on a lounger (v02)
  BEACH_LIFEGUARD    the bald action-film jock lifeguard: muscles, red shorts, a whistle, a lifebuoy (v03)
  BEACH_DETECTOR     the dumb treasure hunter with headphones and a metal detector, shirtless (v03)
  BEACH_NUDIST       the old nudist under the Sims-style pixel censor (v01)
  BEACH_BURIED       the guy his friends buried in the sand up to the neck: a knotted handkerchief on the head (v01); the
                     sand mound and the buried preview come from beach_buried_scene.py
  BEACH_HOLIDAYMAKER the ordinary dumb holidaymaker (v02) - out of the pool since TASK-000545; kept in the code like
                     OLD_TOURIST
Same format as buddy_types.TYPES / BUILDERS; registered from buddy_types.POOLS. No bpy calls at import time."""
import math
from mathutils import Vector, Matrix
import buddy_geo as G
import buddy_body as B
import buddy_clothes as C
import buddy_wear as W
import buddy_types as T

GROUP = 'Городской пляж'
METAL = 'metal'

TYPES = {
    'BEACH_DETECTOR': dict(
        label='Кладоискатель с металлоискателем', group=GROUP, hand_props=True, no_ears=True, body=dict(thin=0.3, belly=0.8),
        arm_down=68.0, face=dict(Surprised=0.55, Happy=0.45),
        look=dict(skin=(236, 178, 140), nose=(232, 140, 112), brow=(170, 160, 150)),
        slots={'Shorts': ((150, 140, 96), 0.9), 'Pocket': ((132, 122, 82), 0.9), 'Socks': ((246, 246, 242), 0.9),
               'Sandal': ((96, 66, 42), 0.6), 'Pack': ((40, 120, 170), 0.6), 'Pack_Strap': ((30, 30, 34), 0.6),
               'Buckle': ((206, 208, 212), 0.3, METAL), 'Hair': ((206, 200, 190), 0.95), 'Phones': ((250, 196, 40), 0.4),
               'Phones_Pad': ((30, 30, 32), 0.9), 'Phones_Plate': ((220, 40, 40), 0.4), 'Frame': ((30, 28, 28), 0.3),
               'Det_Shaft': ((176, 180, 186), 0.3, METAL), 'Det_Box': ((40, 44, 50), 0.5), 'Det_Screen': ((120, 230, 110), 0.2),
               'Det_Grip': ((24, 24, 26), 0.8), 'Det_Coil': ((250, 200, 40), 0.4), 'Det_Coil_Rim': ((30, 30, 32), 0.5), 'Tooth': ((250, 248, 236), 0.3)},
        colourways=[{'Shorts': (90, 110, 140), 'Pocket': (76, 94, 122), 'Phones': (60, 160, 220)},
                    {'Shorts': (120, 90, 70), 'Pocket': (104, 76, 58), 'Pack': (230, 90, 40)}]),
    'BEACH_SUNBURN': dict(
        label='Обгоревший турист', group=GROUP, hand_props=False, body=dict(belly=1.1), arm_down=66.0,
        face=dict(Surprised=0.5, Worried=0.3, Blink=0.3), own_eyes=True,
        look=dict(skin=(228, 92, 68), nose=(204, 56, 50), brow=(200, 150, 90), mouth=(140, 44, 44)),
        slots={'Trunks': ((40, 70, 170), 0.6), 'Trunks_Band': ((246, 246, 242), 0.7), 'Pale': ((246, 186, 160), 0.9),
               'Foot': ((228, 92, 68), 0.9), 'Slide': ((40, 40, 44), 0.5)},
        colourways=[{'Trunks': (200, 40, 50)}, {'Trunks': (240, 140, 40)}]),
    'BEACH_NUDIST': dict(
        label='Дед-нудист', group=GROUP, hand_props=False, body=dict(belly=0.9, thin=0.2), arm_down=66.0,
        face=dict(Happy=0.8, Blink=0.25),
        look=dict(skin=(170, 104, 70), nose=(160, 88, 62), brow=(232, 228, 220), mouth=(120, 60, 50)),
        slots={'Hat': ((246, 244, 236), 0.95), 'Frame': ((20, 20, 22), 0.3), 'Lens': ((24, 26, 30), 0.08),
               'Socks': ((246, 246, 242), 0.9), 'Sandal': ((110, 74, 46), 0.6),
               'Mustache': ((236, 232, 224), 0.95), 'Censor': ((196, 122, 86), 1.0), 'Watch': ((214, 174, 76), 0.28, METAL),
               'Watch_Face': ((246, 246, 240), 0.2)},
        colourways=[{'Hat': (230, 220, 160), 'Socks': (60, 60, 66), 'Sandal': (40, 40, 44)},
                    {'Hat': (180, 220, 240), 'Lens': (40, 120, 60)}]),
    'BEACH_HOLIDAYMAKER': dict(
        label='Отдыхающий', group=GROUP, hand_props=False, body=dict(belly=0.7), arm_down=68.0,
        face=dict(Happy=0.5, Surprised=0.45, Blink_R=0.5), own_eyes=True,
        look=dict(skin=(240, 170, 130), nose=(232, 140, 110)),
        slots={'Shorts': ((40, 150, 190), 0.9), 'Shorts_Print': ((250, 240, 120), 0.8),
               'Foot': ((240, 170, 130), 0.9), 'Slide': ((30, 120, 200), 0.5), 'Cap': ((246, 246, 242), 0.85),
               'Visor': ((246, 246, 242), 0.85), 'Frame': ((30, 30, 34), 0.3), 'Lens': ((30, 60, 90), 0.08),
               'Towel': ((240, 60, 70), 0.95), 'Towel_Stripe': ((250, 250, 246), 0.95)},
        colourways=[{'Shorts': (230, 90, 60), 'Towel': (60, 120, 220)},
                    {'Shorts': (40, 60, 120), 'Shorts_Print': (240, 120, 160), 'Towel': (250, 200, 40)}]),
    'BEACH_CORN': dict(
        label='Продавец кукурузы', group=GROUP, hand_props=True, body=dict(thin=0.5, belly=0.7), arm_down=68.0,
        face=dict(Happy=0.95, Surprised=0.35),
        look=dict(skin=(178, 108, 70), nose=(170, 92, 64), brow=(44, 34, 28), mouth=(110, 48, 40)),
        slots={'Track': ((40, 44, 58), 0.8), 'Track_Roll': ((34, 38, 50), 0.8), 'Stripes': ((240, 240, 236), 0.8),
               'Foot': ((178, 108, 70), 0.9), 'Sole': ((40, 120, 210), 0.5), 'Thong': ((246, 246, 242), 0.5),
               'Cap': ((206, 44, 44), 0.85), 'Visor': ((206, 44, 44), 0.85), 'Gold': ((214, 174, 76), 0.28, METAL),
               'Pack': ((26, 26, 28), 0.5), 'Pack_Strap': ((26, 26, 28), 0.6), 'Buckle': ((206, 208, 212), 0.3, METAL),
               'Stubble': ((44, 34, 28), 0.95), 'Mustache': ((44, 34, 28), 0.9),
               'Bag': ((178, 184, 194), 0.34, METAL), 'Bag_Handle': ((40, 90, 190), 0.6), 'Zip': ((50, 50, 56), 0.6),
               'Corn': ((250, 204, 64), 0.55), 'Husk': ((200, 208, 124), 0.8)},
        colourways=[{'Track': (30, 30, 34), 'Track_Roll': (24, 24, 28), 'Cap': (246, 246, 242), 'Visor': (246, 246, 242),
                     'Bag_Handle': (200, 44, 44)},
                    {'Track': (40, 80, 52), 'Track_Roll': (32, 66, 42), 'Cap': (40, 60, 120), 'Visor': (40, 60, 120),
                     'Bag': (60, 110, 200), 'Bag_Handle': (246, 246, 242)}]),
    'BEACH_CASTLE': dict(
        label='Строитель куличиков', group=GROUP, hand_props=True, body=dict(belly=0.8), arm_down=66.0,
        face=dict(Happy=0.55, Surprised=0.4), eyes=dict(pupil_in=0.021),
        look=dict(skin=(242, 180, 140), nose=(234, 148, 118), brow=(150, 110, 70)),
        slots={'Trunks': ((70, 170, 60), 0.6), 'Foot': ((242, 180, 140), 0.9), 'Sole': ((246, 120, 28), 0.5),
               'Thong': ((246, 120, 28), 0.5), 'Sand': ((206, 172, 112), 0.95), 'Tooth': ((250, 248, 236), 0.3),
               'Hair': ((150, 112, 66), 0.9), 'Bucket': ((40, 120, 220), 0.35), 'Bucket_Rim': ((250, 200, 40), 0.35),
               'Bucket_Handle': ((250, 200, 40), 0.4), 'Spade': ((230, 50, 40), 0.4)},
        colourways=[{'Trunks': (200, 40, 50), 'Bucket': (250, 120, 160)},
                    {'Trunks': (40, 60, 140), 'Bucket': (250, 200, 40), 'Bucket_Rim': (40, 120, 220), 'Bucket_Handle': (40, 120, 220)}]),
    'BEACH_BURIED': dict(
        label='Закопанный в песок', group=GROUP, hand_props=False, body=dict(belly=0.8), arm_down=66.0,
        face=dict(Happy=0.85, Surprised=0.15),
        look=dict(skin=(236, 160, 116), nose=(228, 136, 100), brow=(90, 64, 44), mouth=(120, 50, 40)),
        slots={'Trunks': ((236, 120, 40), 0.6), 'Kerchief': ((246, 246, 240), 0.9), 'Mustache': ((90, 64, 44), 0.9),
               'Foot': ((236, 160, 116), 0.9), 'Sole': ((214, 146, 104), 0.9)},
        colourways=[{'Trunks': (40, 90, 180), 'Kerchief': (250, 250, 250)}, {'Trunks': (40, 140, 70), 'Kerchief': (236, 230, 210)}]),
    'BEACH_LIFEGUARD': dict(
        label='Спасатель-качок', group=GROUP, hand_props=True, body=dict(muscle=1.8), arm_down=62.0,
        face=dict(Happy=0.2),
        look=dict(skin=(236, 170, 128), nose=(228, 146, 112), brow=(40, 30, 26), mouth=(110, 46, 40)),
        slots={'Shorts': ((214, 36, 40), 0.7), 'Foot': ((236, 170, 128), 0.9), 'Sole': ((30, 30, 34), 0.6),
               'Stubble': ((70, 52, 44), 0.95), 'Cord': ((246, 246, 242), 0.7),
               'Whistle': ((250, 120, 20), 0.35), 'Buoy': ((226, 40, 36), 0.5), 'Buoy_Stripe': ((250, 250, 246), 0.5)},
        colourways=[{'Shorts': (250, 200, 30)}, {'Shorts': (40, 80, 200)}]),
}


# ------------------------------------------------------------------ shared pieces
def _t(ob, src, filt=None):
    return C.transfer(ob, src, filt)


def _on_body(body):
    """Nearest-point projection onto the body: returns on(p, off) -> (point lifted by off along the outward normal, normal)."""
    bvh = G.bvh_of([body])

    def on(p, off):
        loc, nrm, _, _ = bvh.find_nearest(p)
        nrm = nrm if nrm.dot(Vector((p.x, p.y, 0.6))) >= 0 else -nrm
        return loc + nrm * off, nrm
    return on


SHOULDER_PATH = [(0.098, -0.150, 1.104), (0.128, -0.112, 1.160), (0.152, -0.050, 1.198), (0.160, 0.008, 1.208),
                 (0.152, 0.062, 1.196), (0.130, 0.106, 1.156), (0.102, 0.140, 1.104)]     # tank-top strap line


def shoulder_strap(name, body, material, s, width, off, thick, front=(), back=()):
    """A strap over one shoulder along the vest-top strap line, optionally continued down the chest/back."""
    on = _on_body(body)
    raw = [Vector(p) for p in front] + [Vector(p) for p in SHOULDER_PATH] + [Vector(p) for p in back]
    pts = [on(Vector((s * p.x, p.y, p.z)), off)[0] for p in raw]
    return C.strap(name, pts, material, width=width, thick=thick, normal_fn=lambda q: on(q, 0.0)[1])


def over_ear_headphones(prefix, M):
    """Big over-ear headphones on the bald head: cups over the (removed) ears, a thick band over the crown."""
    import buddy_pool_oldtown as O
    out = []
    for s in (1, -1):
        out += O._ear_cup(f'{prefix}_Cup_{s}', Vector((s * 0.166, 0.006, 1.468)), Vector((s, 0.0, 0.0)), M, 'Phones', 'Phones_Pad',
                          'Phones_Plate', r=0.060, depth=0.046)
    pts = []
    for k in range(19):
        a = math.radians(180 * k / 18)
        pts.append(Vector((0.176 * math.cos(a), 0.006, 1.520 + (B.HEAD_TOP + 0.022 - 1.520) * math.sin(a) ** 0.85)))
    out.append(G.tube(prefix + '_Band', pts, 0.012, M['Phones'], seg=10))
    return [C.rigid(o, 'Head') for o in out]


def fanny_pack(prefix, M, body, z=0.840):
    """Bum bag worn in front on a thin belt: a rounded pouch with a zip line."""
    on = _on_body(body)
    front, _ = on(Vector((0.0, -0.2, z)), 0.0)
    out = W.belt(prefix, M['Pack_Strap'], M['Buckle'], z=z, rx=0.205, ry=0.150, dy=-0.004, width=0.020)
    c = front + Vector((0.0, -0.040, -0.004))
    out.append(G.ellipsoid(prefix + '_Pouch', c, (0.110, 0.042, 0.060), M['Pack'], seg=16, rings=10))
    out.append(G.tube(prefix + '_Zip', [c + Vector((-0.090, -0.034, 0.022)), c + Vector((0.0, -0.041, 0.030)), c + Vector((0.090, -0.034, 0.022))],
                      0.0030, M['Pack_Strap'], seg=5))
    return [C.rigid(o, 'Hips') for o in out]


def metal_detector(prefix, M, arm_down):
    """Metal detector swept low in front: grip in the right fist, a control box with a green screen just below it, a
    telescopic shaft down to a yellow search coil hovering over the sand ahead. Dropped at the slightest danger."""
    import buddy_pool_hamlet as HM
    fist, _, thumb = HM.grip('Right', arm_down)
    fwd = Vector((thumb.x, thumb.y, 0.0)).normalized()
    coil_c = Vector((fist.x - 0.040, 0.0, 0.060)) + fwd * 0.560
    coil_c.y = fist.y + fwd.y * 0.560
    d = (coil_c - fist).normalized()
    at = lambda s: fist + d * s
    L = (coil_c - fist).length
    out = [G.tube(prefix + '_Grip', [at(-0.060), at(0.050)], 0.0170, M['Det_Grip'], seg=10),
           G.tube(prefix + '_Shaft', [at(0.050), at(0.45 * L)], 0.0110, M['Det_Shaft'], seg=8),
           G.tube(prefix + '_ShaftLow', [at(0.45 * L), at(L - 0.050)], 0.0085, M['Det_Shaft'], seg=8),
           G.tube(prefix + '_Lock', [at(0.45 * L - 0.012), at(0.45 * L + 0.012)], 0.0150, M['Det_Grip'], seg=8)]
    up = Vector((0.0, 0.0, 1.0))
    side = d.cross(up).normalized()
    top = side.cross(d).normalized()
    box_c = at(0.120) + top * 0.035
    rot = Matrix((side, d, top)).transposed()
    out.append(W.box(prefix + '_Box', box_c, (0.032, 0.055, 0.022), M['Det_Box'], rot=rot))
    out.append(W.box(prefix + '_Screen', box_c + top * 0.023, (0.022, 0.032, 0.002), M['Det_Screen'], rot=rot))
    # the search coil: a flat yellow disc with a dark rim, joined to the shaft by a little yoke
    out.append(G.ellipsoid(prefix + '_Coil', coil_c, (0.110, 0.130, 0.014), M['Det_Coil'], seg=24, rings=6))
    out.append(G.tube(prefix + '_CoilRim', [coil_c + Vector((0.112 * math.cos(a), 0.132 * math.sin(a), 0.0))
                                            for a in [2 * math.pi * k / 32 for k in range(33)]], 0.0080, M['Det_Coil_Rim'], seg=6, caps=False))
    out.append(G.tube(prefix + '_Yoke', [at(L - 0.050), coil_c + Vector((0.0, 0.0, 0.016))], 0.0100, M['Det_Grip'], seg=8))
    return HM.hold(out, 'Right', arm_down)


def _math(N, L, op, a, b=None, clamp=False):
    n = N.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = float(x)
        else:
            L.new(x, n.inputs[i])
    return n.outputs[0]


def mosaic_material(mat, tones, block=0.034):
    """The Sims / Saints Row censor: flat square blocks aligned to the SCREEN, one world size (block, metres) at the
    character's distance, coloured from the skin tones by a soft low-frequency noise plus a little per-block jitter, so
    it reads as 'the body, pixelated'. Unlit (emission) so the blocks stay flat. The Principled base colour keeps the
    skin tone (slot colour) for the FBX: in Unity the slot falls back to an opaque skin blob until the screen-space
    mosaic shader is assigned (see README)."""
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    cam = N.new('ShaderNodeCameraData')
    sv = N.new('ShaderNodeSeparateXYZ')
    L.new(cam.outputs['View Vector'], sv.inputs[0])
    az = _math(N, L, 'ABSOLUTE', sv.outputs['Z'])
    u, v = _math(N, L, 'DIVIDE', sv.outputs['X'], az), _math(N, L, 'DIVIDE', sv.outputs['Y'], az)
    oi = N.new('ShaderNodeObjectInfo')
    vt = N.new('ShaderNodeVectorTransform')
    vt.vector_type, vt.convert_from, vt.convert_to = 'POINT', 'WORLD', 'CAMERA'
    L.new(oi.outputs['Location'], vt.inputs[0])
    so = N.new('ShaderNodeSeparateXYZ')
    L.new(vt.outputs[0], so.inputs[0])
    zo = _math(N, L, 'ABSOLUTE', so.outputs['Z'])
    bx = _math(N, L, 'FLOOR', _math(N, L, 'DIVIDE', _math(N, L, 'MULTIPLY', u, zo), block))
    by = _math(N, L, 'FLOOR', _math(N, L, 'DIVIDE', _math(N, L, 'MULTIPLY', v, zo), block))
    cb = N.new('ShaderNodeCombineXYZ')
    L.new(bx, cb.inputs[0])
    L.new(by, cb.inputs[1])
    wn = N.new('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    L.new(cb.outputs[0], wn.inputs['Vector'])
    sn = N.new('ShaderNodeTexNoise')
    sn.inputs['Scale'].default_value = 0.55
    sn.inputs['Detail'].default_value = 0.0
    L.new(cb.outputs[0], sn.inputs['Vector'])
    t = _math(N, L, 'ADD', _math(N, L, 'MULTIPLY', _math(N, L, 'SUBTRACT', sn.outputs['Fac'], 0.5), 2.2),
              _math(N, L, 'MULTIPLY', wn.outputs['Value'], 0.30))
    t = _math(N, L, 'ADD', t, 0.35, clamp=True)
    ramp = N.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, G.srgb(tones[0])
    els[1].position, els[1].color = 1.0, G.srgb(tones[2])
    mid = els.new(0.5)
    mid.color = G.srgb(tones[1])
    L.new(t, ramp.inputs['Fac'])
    black = N.new('ShaderNodeRGB')
    black.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    L.new(black.outputs[0], bsdf.inputs['Base Color'])            # no lit diffuse: the blocks stay flat
    L.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 1.0
    for key in ('Specular IOR Level', 'Specular'):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.0
    return mat


def censor(prefix, M, body, z_c=0.740, rz=0.112, margin=0.042, tones=((172, 100, 68), (204, 126, 88), (230, 156, 116))):
    """One rounded censor volume round the pelvis (groin, between the legs and the seat), horizontally round so its
    outline hardly changes with the view; rigid on the hips, so it stays put when he runs, lies down or is dragged as a
    ragdoll. Its material is the screen-space pixel mosaic."""
    bvh = G.bvh_of([body])
    hf = bvh.ray_cast(Vector((0.0, -0.6, 0.780)), Vector((0.0, 1.0, 0.0)))
    hb = bvh.ray_cast(Vector((0.0, 0.6, 0.760)), Vector((0.0, -1.0, 0.0)))
    yf = hf[0].y if hf[0] is not None else -0.125
    yb = hb[0].y if hb[0] is not None else 0.135
    r = 0.5 * (yb - yf) + margin
    blob = G.ellipsoid(prefix + '_Blob', Vector((0.0, 0.5 * (yf + yb), z_c)), (r, r, rz), M['Censor'], seg=28, rings=14)
    mosaic_material(M['Censor'], tones)
    return [C.rigid(blob, 'Hips')]


def baseball_cap(prefix, cap_m, visor_m, yaw_deg=0.0):
    """Baseball cap: a rounded crown and a long visor; yaw_deg turns the whole cap on the head (askew)."""
    base = W.zprofile([(0, 1.676), (90, 1.664), (180, 1.652)])
    cap = W.ring_loft(prefix, [('fit', base, 0.008), (1.720, 0.150, 0.146, -0.004, 0.0), (1.770, 0.132, 0.128, -0.004, 0.0),
                               (1.800, 0.080, 0.078, -0.004, 0.0), (1.808, 0.020, 0.020, -0.004, 0.0)], [cap_m], seg=32)
    visor = W.peak(prefix + '_Visor', visor_m, base, length=0.075, droop=0.012, curve=0.016, span=70, off=0.010, thick=0.008)
    out = [cap, visor]
    if yaw_deg:
        m = Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')
        for o in out:
            o.data.transform(m)
            o.data.update()
    return [C.rigid(o, 'Head') for o in out]


def corn_cob(prefix, M, base, axis, length=0.160, r=0.026, husk=True):
    """Boiled corn on the cob: a lathe with staggered kernel bumps, closed at both ends; husk leaves peeled back over
    the base (the 'handle')."""
    a = axis.normalized()
    u = a.orthogonal().normalized()
    w = a.cross(u)
    seg, rows = 18, 12
    vs, fs = [], []
    for j in range(rows + 1):
        t = 0.04 + 0.92 * j / rows
        prof = (1.0 - 0.30 * t) * max(0.20, (1.0 - (2.0 * t - 1.0) ** 6)) ** 0.5
        for i in range(seg):
            ang = 2.0 * math.pi * i / seg
            bump = 1.0 + 0.07 * math.cos(9.0 * ang + (j % 2) * math.pi)
            rr = r * prof * bump
            vs.append(base + a * (length * t) + (u * math.cos(ang) + w * math.sin(ang)) * rr)
    for j in range(rows):
        for i in range(seg):
            fs.append((j * seg + i, j * seg + (i + 1) % seg, (j + 1) * seg + (i + 1) % seg, (j + 1) * seg + i))
    c0 = len(vs)
    vs.append(base + a * (length * 0.0))
    c1 = len(vs)
    vs.append(base + a * length)
    for i in range(seg):
        fs.append(((i + 1) % seg, i, c0))
        fs.append((rows * seg + i, rows * seg + (i + 1) % seg, c1))
    out = [G.from_data(prefix + '_Cob', vs, fs, M['Corn'], True)]
    if husk:
        for k in range(3):
            ang = 2.0 * math.pi * k / 3 + 0.4
            radial = u * math.cos(ang) + w * math.sin(ang)
            tang = a.cross(radial)
            d = (-a * 0.92 + radial * 0.40).normalized()            # peeled back and out
            c = base + radial * (r * 0.70) + d * 0.050
            rot = Matrix((tang, radial, d)).transposed()
            out.append(G.ellipsoid(f'{prefix}_Husk_{k}', c, (0.020, 0.005, 0.060), M['Husk'], rot=rot, seg=10, rings=6))
    return out


def _rounded_box(name, c, ax, ay, z0, z1, material, bulge=0.010, seg=32):
    """A soft rounded box (a squircle in plan, slightly bulging sides), closed top and bottom."""
    def ring(z, a, b):
        out = []
        for k in range(seg):
            t = 2 * math.pi * k / seg
            co, si = math.cos(t), math.sin(t)
            out.append(Vector((c.x + a * math.copysign(abs(co) ** 0.5, co), c.y + b * math.copysign(abs(si) ** 0.5, si), z)))
        return out
    h = z1 - z0
    rows = [(z0, ax - 0.012, ay - 0.012), (z0 + 0.010, ax, ay), (z0 + 0.5 * h, ax + bulge, ay + bulge), (z1 - 0.010, ax, ay),
            (z1, ax - 0.014, ay - 0.014)]
    rings = [ring(z, a, b) for z, a, b in rows]
    vs = [p for r in rings for p in r]
    fs = []
    for k in range(len(rings) - 1):
        G.bridge(fs, list(range(k * seg, (k + 1) * seg)), list(range((k + 1) * seg, (k + 2) * seg)))
    for k0, top in ((0, False), ((len(rings) - 1) * seg, True)):
        cidx = len(vs)
        vs.append(sum(vs[k0:k0 + seg], Vector()) / seg)
        for j in range(seg):
            a, b = k0 + j, k0 + (j + 1) % seg
            fs.append((a, b, cidx) if top else (b, a, cidx))
    return G.from_data(name, vs, fs, material, True)


def thermal_bag(prefix, M, fist):
    """The corn seller's medium silver thermal bag ('термосумка') hanging from the left fist by two blue handles: a soft
    rounded box with a zip along the top and one hot cob poking out of the open end of the zip."""
    ax, ay, h = 0.088, 0.150, 0.250
    top = fist.z - 0.085
    c = Vector((fist.x - 0.012, fist.y, 0.0))
    out = [_rounded_box(prefix + '_Bag', c, ax, ay, top - h, top, M['Bag'])]
    out.append(G.tube(prefix + '_Zip', [Vector((c.x, c.y - ay + 0.030, top + 0.002)), Vector((c.x, c.y + ay - 0.030, top + 0.002))],
                      0.0045, M['Zip'], seg=6))
    for s in (1, -1):                    # handles from the long top edges up to the fist
        pts = [Vector((c.x + s * (ax - 0.010), c.y + dy, top - 0.004)) for dy in (-0.070,)]
        pts += [Vector((c.x + s * 0.020, c.y - 0.030, fist.z - 0.012)), Vector((c.x + s * 0.004, c.y, fist.z + 0.004)),
                Vector((c.x + s * 0.020, c.y + 0.030, fist.z - 0.012)), Vector((c.x + s * (ax - 0.010), c.y + 0.070, top - 0.004))]
        out.append(G.tube(f'{prefix}_Handle_{s}', pts, 0.0080, M['Bag_Handle'], seg=6))
    out += corn_cob(prefix + '_Peek', M, Vector((c.x, c.y + ay - 0.050, top - 0.070)), Vector((0.10, 0.45, 1.0)), length=0.170,
                    r=0.025, husk=True)
    return out


def _bucktooth(name, material, x, z=1.384, half=(0.0090, 0.0055, 0.0150)):
    tooth = G.ellipsoid(name, Vector((x, B.head_surface_y(x, z, 0.002), z)), half, material, seg=10, rings=6)
    return C.rigid(tooth, 'Head')


def sand_bucket(prefix, M, arm_down):
    """A kid's plastic beach bucket of wet sand in the left fist (for the sand pies), a red spade in the right."""
    import buddy_pool_hamlet as HM
    fist, _, _ = HM.grip('Left', arm_down)
    out = HM.bucket(prefix, M, fist, r_top=0.088, r_bot=0.066, h=0.140, fill=False)
    z_rim = fist.z - 0.135
    out.append(G.ellipsoid(prefix + '_Sand', Vector((fist.x, fist.y, z_rim - 0.004)), (0.084, 0.084, 0.022), M['Sand'], seg=16, rings=8))
    res = HM.hold(out, 'Left', arm_down)
    fist, _, thumb = HM.grip('Right', arm_down)
    fwd = Vector((thumb.x, thumb.y, 0.0)).normalized()
    d = (fwd * math.cos(math.radians(35)) - Vector((0.0, 0.0, math.sin(math.radians(35))))).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    nrm = side.cross(d).normalized()
    spade = [G.tube(prefix + '_SpadeHandle', [fist - d * 0.040, fist + d * 0.190], 0.0110, M['Spade'], seg=8),
             G.ellipsoid(prefix + '_SpadeGrip', fist - d * 0.046, (0.020, 0.020, 0.020), M['Spade'], seg=10, rings=6),
             G.ellipsoid(prefix + '_SpadeBlade', fist + d * 0.250, (0.052, 0.070, 0.008), M['Spade'], rot=Matrix((side, d, nrm)).transposed(),
                         seg=16, rings=8)]
    return res + HM.hold(spade, 'Right', arm_down)


def lifebuoy(prefix, M, arm_down, R=0.190, r=0.050):
    """A red lifebuoy with four white bands, held by its top in the right fist and hanging beside the leg."""
    import buddy_pool_hamlet as HM
    fist, _, thumb = HM.grip('Right', arm_down)
    fwd = Vector((thumb.x, thumb.y, 0.0)).normalized()
    up = Vector((0.0, 0.0, 1.0))
    side = fwd.cross(up).normalized()
    c = fist - up * R
    seg, ring = 32, 10
    vs, fs, idx = [], [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        d = fwd * math.cos(a) + up * math.sin(a)
        for j in range(ring):
            b = 2 * math.pi * j / ring
            vs.append(c + d * (R + r * math.cos(b)) + side * (r * math.sin(b)))
    for i in range(seg):
        for j in range(ring):
            a0, a1 = i * ring + j, ((i + 1) % seg) * ring + j
            fs.append((a0, a1, ((i + 1) % seg) * ring + (j + 1) % ring, i * ring + (j + 1) % ring))
            idx.append(1 if (i + 2) // 4 % 2 else 0)
    ob = G.from_data(prefix + '_Buoy', vs, fs, M['Buoy'], True, idx, [M['Buoy_Stripe']])
    return HM.hold([ob], 'Right', arm_down)


def whistle_cord(prefix, M, body):
    """A white cord round the neck with an orange whistle on the chest."""
    bvh = G.bvh_of([body])
    pts = []
    for k in range(49):
        a = 2 * math.pi * k / 48
        f = ((1 + math.cos(a)) / 2) ** 3
        p = Vector((0.150 * math.sin(a), -0.156 * math.cos(a), 1.262 - 0.190 * f))
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None:
            nrm = nrm if nrm.dot(Vector((p.x, p.y, 0))) >= 0 else -nrm
            p = loc + nrm * 0.008
        pts.append(p)
    low = min(pts, key=lambda q: q.z)
    return [G.tube(prefix + '_Cord', pts, 0.0040, M['Cord'], seg=6, caps=False),
            G.ellipsoid(prefix + '_Whistle', low + Vector((0.0, -0.016, -0.018)), (0.020, 0.016, 0.016), M['Whistle'], seg=12, rings=8),
            W.box(prefix + '_Mouth', low + Vector((0.020, -0.016, -0.010)), (0.014, 0.008, 0.006), M['Whistle'])]


def knotted_kerchief(prefix, material):
    """The CIS beach classic: a white handkerchief over the head with a knot at each corner."""
    lower = W.zprofile([(0, 1.650), (90, 1.632), (180, 1.622)])
    cap, _ = W.shell(prefix, material, lower, None, off=0.004, thick=0.004, seg=32, rows=6)
    out = [cap]
    for k, deg in enumerate((45.0, -45.0, 135.0, -135.0)):
        phi = math.radians(deg)
        p, n = W.head_at(phi, lower(phi), 0.010)
        out.append(G.ellipsoid(f'{prefix}_Knot_{k}', p + n * 0.006, (0.015, 0.015, 0.013), material, seg=10, rings=6))
        tip = (n + Vector((0.0, 0.0, -0.9))).normalized()
        out.append(G.ellipsoid(f'{prefix}_Tip_{k}', p + n * 0.010 + tip * 0.020, (0.010, 0.010, 0.016), material,
                               rot=Matrix((tip.orthogonal().normalized(), tip.cross(tip.orthogonal()).normalized(), tip)).transposed(),
                               seg=8, rings=5))
    return [C.rigid(o, 'Head') for o in out]


# ------------------------------------------------------------------ builders
LEGS_CARGO = [(.70, .104), (.62, .110), (.54, .112), (.48, .110), (.455, .104)]          # baggy shorts to the knee
LEGS_TRUNKS = [(.70, .094), (.680, .096), (.668, .090)]                                 # short swim trunks
LEGS_SWIM = [(.70, .100), (.64, .106), (.58, .108), (.555, .102)]                       # board shorts to mid-thigh
LEGS_ROLLED = [(.70, .094), (.60, .092), (.52, .089), (.466, .087), (.460, .097), (.432, .098), (.426, .090)]   # rolled to the knee


def beach_detector(body, face, M, skin):
    """BEACH_DETECTOR v02 (TASK-000542; v01 TASK-000540, Vadim: 'definitely a dumb one'; v02: as before, but undressed
    for the beach): the dumb treasure hunter - huge yellow over-ear headphones on a bald head with a grey ring of hair
    (he hears nothing, an easy catch), thick round glasses without lenses, a gaping grin with two buck teeth; shirtless
    with a belly, baggy khaki shorts to the knee (v03: no bum bag, no pockets), white socks in sandals; the metal detector swept
    low in the right hand."""
    pre = 'BEACH_DETECTOR'
    src = C.weight_source([body])
    out = [_t(W.bottoms(pre + '_Shorts', LEGS_CARGO, [M['Shorts']]), src)]
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.slides(pre + '_Sandal', M['Socks'], M['Sandal'])
    out.append(W.hair_ring(pre + '_Hair', M['Hair']))
    out += over_ear_headphones(pre + '_Phones', M)
    out += W.glasses(pre + '_Glasses', M['Frame'], None, rx=0.060, rz=0.060, round_k=1.0)     # frames only: the eyes show
    out += [_bucktooth(f'{pre}_Tooth_{s}', M['Tooth'], s * 0.0090) for s in (1, -1)]
    out += metal_detector(pre + '_Detector', M, TYPES['BEACH_DETECTOR']['arm_down'])
    return out


def beach_sunburn(body, face, M, skin):
    """BEACH_SUNBURN v02 (TASK-000542, Vadim: 'just sunburnt, and dumb'; v01 TASK-000540): the tourist burnt like a
    boiled crayfish - lobster-red skin with pale stripes where yesterday's vest straps were, a bald burnt head with
    nothing on it, a dazed open-mouthed stare, tight blue swim trunks under a big belly, black slides on bare feet.
    Walks about the beach and lies on his back on a lounger (the BeachLie clips)."""
    pre = 'BEACH_SUNBURN'
    src = C.weight_source([body])
    out = []
    for s in (1, -1):                                             # pale tan lines of a vest top, chest and back
        out.append(_t(shoulder_strap(f'{pre}_TanLine_{s}', body, M['Pale'], s, 0.030, 0.0015, 0.0012,
                                     front=[(0.092, -0.170, 0.990), (0.096, -0.164, 1.050)],
                                     back=[(0.098, 0.150, 1.050), (0.094, 0.152, 0.990)]), src, C.no_head))
    trunks = _t(W.bottoms(pre + '_Trunks', LEGS_TRUNKS, [M['Trunks']]), src)
    band = [W.front_decal(pre + '_Band', [(-0.150, 0.858), (0.150, 0.858), (0.150, 0.872), (-0.150, 0.872)], trunks, M['Trunks_Band'], 0.003)]
    out += [trunks] + T._decal_t(band, trunks)
    out += W.slides(pre + '_Slide', M['Foot'], M['Slide'])
    return out


def beach_nudist(body, face, M, skin):
    """BEACH_NUDIST (TASK-000540, Vadim: 'so Steam does not ban us'): the old nudist, tanned to the colour of a
    walnut and proud of it - a white panama, black sunglasses, a white walrus moustache, a gold
    watch, white socks in brown sandals and nothing else. The body is the plain doll body (no anatomy); the pixel
    censor round the pelvis (as in The Sims / Saints Row) hides the groin and the seat from every side."""
    pre = 'BEACH_NUDIST'
    src = C.weight_source([body])
    out = W.bucket_hat(pre + '_Hat', M['Hat'])
    out += W.glasses(pre + '_Shades', M['Frame'], M['Lens'], rx=0.058, rz=0.046, round_k=0.6)
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.020, size=1.7)
    out += W.watch(pre + '_Watch', M['Watch'], M['Watch_Face'], side=1)
    out.append(_t(W.plain_socks(pre + '_Socks', M['Socks']), src))
    out += W.slides(pre + '_Sandal', M['Socks'], M['Sandal'])
    out += censor(pre + '_Censor', M, body)
    return out


def beach_holidaymaker(body, face, M, skin):
    """BEACH_HOLIDAYMAKER v02 (TASK-000542; v01 TASK-000540, Vadim: 'an ordinary holidaymaker, take the NPC BASE and
    work from it', 'but dumb'; v02: as before, undressed for the beach): the BASE NPC on the beach without his tee - the
    BASE shorts cut as patterned board shorts, a belly, bare feet in slides, a white cap, sunglasses up on the cap, a
    striped towel over the bare left shoulder; a dumb open grin with one droopy eyelid."""
    pre = 'BEACH_HOLIDAYMAKER'
    src = C.weight_source([body])
    shorts = _t(W.bottoms(pre + '_Shorts', LEGS_SWIM, [M['Shorts']]), src)
    spots = [(0.080, 0.640, 0.024), (0.140, 0.590, 0.020), (0.050, 0.590, 0.018), (-0.090, 0.640, 0.024), (-0.140, 0.600, 0.020),
             (-0.040, 0.600, 0.018), (0.120, 0.700, 0.018), (-0.120, 0.710, 0.018)]
    prints = [W.front_decal(f'{pre}_PrintF_{k}', W.blob(x, z, r, seed=320 + k, rough=0.4), shorts, M['Shorts_Print'], 0.003, step=0.008)
              for k, (x, z, r) in enumerate(spots)]
    prints += [G.decal(f'{pre}_PrintB_{k}', W.blob(-x, z + 0.010, r, seed=340 + k, rough=0.4), G.BACK(), [shorts], 0.003, M['Shorts_Print'],
                       step=0.008) for k, (x, z, r) in enumerate(spots)]
    out = [shorts] + T._decal_t(prints, shorts)
    out += W.slides(pre + '_Slide', M['Foot'], M['Slide'])
    out += baseball_cap(pre + '_Cap', M['Cap'], M['Visor'])
    out += W.sunglasses_on_head(pre + '_Shades', M['Frame'], M['Lens'], dh=0.090)
    # the towel over the bare left shoulder: a wide band lying on the skin, down the chest and the back, a white stripe
    for name, mat, w, off in ((pre + '_Towel', M['Towel'], 0.120, 0.006), (pre + '_TowelStripeA', M['Towel_Stripe'], 0.016, 0.0145)):
        t = shoulder_strap(name, body, mat, 1, w, off, 0.008 if mat is M['Towel'] else 0.0015,
                           front=[(0.096, -0.190, 0.860), (0.098, -0.180, 0.960), (0.098, -0.168, 1.050)],
                           back=[(0.104, 0.160, 1.050), (0.104, 0.170, 0.940), (0.102, 0.176, 0.840)])
        out.append(_t(t, src, C.no_head))
    return out


def beach_corn(body, face, M, skin):
    """BEACH_CORN v02 (TASK-000542; v01 TASK-000540, Vadim: 'the beach corn seller, like the ones on CIS beaches - in
    flip-flops, dumb and pushy'; v02: he carries a medium thermal bag on his arm, shouts 'горячая кукуруза', takes a cob
    out of the bag and walks on): a skinny, walnut-tanned guy with a little pot belly, shirtless (v03: no chain, no money bag),
    old track pants rolled up to the knees, blue flip-flops on bare feet, a red cap pushed askew,
    a big gold-tooth grin and stubble; the silver thermal bag of hot corn in the left hand and one cob thrust forward in
    the right. He walks the beach and pesters everyone - an easy, very loud catch."""
    import buddy_pool_construction as CN
    import buddy_pool_hamlet as HM
    pre = 'BEACH_CORN'
    src = C.weight_source([body])
    pants = _t(W.bottoms(pre + '_Track', LEGS_ROLLED, [M['Track']]), src)
    out = [pants] + T._decal_t(W.leg_stripes(pre + '_Lampas', pants, M['Stripes'], z0=0.47, z1=0.86), pants)
    out += CN.bare_feet(pre + '_Feet', M['Foot'], M['Sole'], thong_m=M['Thong'])
    out += baseball_cap(pre + '_Cap', M['Cap'], M['Visor'], yaw_deg=-28.0)
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.010, size=1.2)
    tx = -0.0110                                                  # one gold front tooth in the grin
    tooth = G.ellipsoid(pre + '_GoldTooth', Vector((tx, B.head_surface_y(tx, 1.388, 0.002), 1.388)), (0.0075, 0.0048, 0.0105),
                        M['Gold'], seg=10, rings=6)
    out.append(C.rigid(tooth, 'Head'))
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head))
    ad = TYPES['BEACH_CORN']['arm_down']
    gl, _, _ = HM.grip('Left', ad)
    out += HM.hold(thermal_bag(pre + '_Thermo', M, gl), 'Left', ad)
    gr, _, thumb = HM.grip('Right', ad)
    fwd = Vector((thumb.x, thumb.y, 0.0)).normalized()
    d = (fwd * math.cos(math.radians(25)) + Vector((0.0, 0.0, math.sin(math.radians(25))))).normalized()
    out += HM.hold(corn_cob(pre + '_Offer', M, gr + d * 0.020, d, length=0.205, r=0.032), 'Right', ad)
    return out


def beach_castle(body, face, M, skin):
    """BEACH_CASTLE v01 (TASK-000542, Vadim: 'the one on the beach who builds sand pies'): a grown-up with a belly who
    plays in the sand like a child - green swim trunks, orange flip-flops, wet sand on the knees, a buzz cut, crossed
    eyes and two big front teeth; a kid's blue bucket of wet sand in the left hand and a red spade in the right."""
    import buddy_pool_construction as CN
    pre = 'BEACH_CASTLE'
    src = C.weight_source([body])
    out = [_t(W.bottoms(pre + '_Trunks', LEGS_TRUNKS, [M['Trunks']]), src)]
    out += CN.bare_feet(pre + '_Feet', M['Foot'], M['Sole'], thong_m=M['Thong'])
    out.append(W.hair(pre + '_Hair', M['Hair'], kind='buzz'))
    out += [_bucktooth(f'{pre}_Tooth_{s}', M['Tooth'], s * 0.0100, z=1.392, half=(0.0098, 0.0058, 0.0150)) for s in (1, -1)]
    for k, (x, z, r, seed) in enumerate(((0.105, 0.430, 0.040, 11), (-0.098, 0.445, 0.034, 12))):      # wet sand on the knees
        d = G.decal(f'{pre}_SandKnee_{k}', W.blob(x, z, r, n=10, seed=seed, rough=0.45), G.FRONT(), [body], 0.0018, M['Sand'], step=0.010)
        out.append(_t(d, src, C.no_head))
    out += sand_bucket(pre + '_Bucket', M, TYPES['BEACH_CASTLE']['arm_down'])
    return out


def beach_lifeguard(body, face, M, skin):
    """BEACH_LIFEGUARD v01 (TASK-000542, Vadim: 'a jock lifeguard', nothing fancy, no lettering): a big muscled,
    shirtless lifeguard (v02, Vadim: a bald jock like from the action films, not a migrant) - bald, clean-shaven,
    light skin, dark stubble, a tough straight face, red swim shorts, a white cord with an orange
    whistle, barefoot; a red-and-white lifebuoy in the right hand."""
    import buddy_pool_construction as CN
    pre = 'BEACH_LIFEGUARD'
    src = C.weight_source([body])
    out = [_t(W.bottoms(pre + '_Shorts', LEGS_SWIM, [M['Shorts']]), src)]
    out += CN.bare_feet(pre + '_Feet', M['Foot'], M['Sole'])
    out += T._face(skin, lambda head: W.stubble(pre + '_Stubble', M['Stubble'], head, dots=170, seed=31))
    out += [_t(o, src, C.no_head) for o in whistle_cord(pre + '_Whistle', M, body)]
    out += lifebuoy(pre + '_Buoy', M, TYPES['BEACH_LIFEGUARD']['arm_down'])
    return out


def beach_buried(body, face, M, skin):
    """BEACH_BURIED v01 (TASK-000545, Vadim: the guy buried in the sand, last): the dumb happy dad his friends buried up
    to the neck - a knotted white handkerchief on the head, a moustache, a pot belly, orange swim trunks, barefoot. When buried only his head shows from the sand mound (BEACH_BURIED_SandMound,
    beach_buried_scene.py); the players have to dig him out (a separate mechanic, not built)."""
    import buddy_pool_construction as CN
    pre = 'BEACH_BURIED'
    src = C.weight_source([body])
    out = [_t(W.bottoms(pre + '_Trunks', LEGS_TRUNKS, [M['Trunks']]), src)]
    out += CN.bare_feet(pre + '_Feet', M['Foot'], M['Sole'])
    out += knotted_kerchief(pre + '_Kerchief', M['Kerchief'])
    out += W.mustache(pre + '_Mustache', M['Mustache'], droop=0.012, size=1.25)
    return out


BUILDERS = {'BEACH_DETECTOR': beach_detector, 'BEACH_SUNBURN': beach_sunburn, 'BEACH_NUDIST': beach_nudist,
            'BEACH_HOLIDAYMAKER': beach_holidaymaker, 'BEACH_CORN': beach_corn, 'BEACH_CASTLE': beach_castle,
            'BEACH_LIFEGUARD': beach_lifeguard, 'BEACH_BURIED': beach_buried}
