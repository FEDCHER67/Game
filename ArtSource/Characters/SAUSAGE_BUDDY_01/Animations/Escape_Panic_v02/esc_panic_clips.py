"""Escape_Panic_v02 clip definitions: PANIC variants of the Escape_v01 table-escape clips (K10 case).

The patient wakes on the operating table with his belly cut open, one arm strap open, and frees himself in
a dumb, hectic, comic panic: fumbles and misses the buckles, shakes his hand, stares at his open belly in
horror, double-takes, clutches the belly, hops on his butt, slides off clumsily and runs hunched with both
hands on the belly.

Same rig, table, strap/buckle geometry, pose keys and gameplay timing hooks as Escape_v01 (read-only
imports of ../Escape_v01/esc_core.py, esc_clips.py, esc_hop.py). Every buckle contact (Grab / StrapOpen
follow / Release) happens at the v01 time on the v01 target; only the approach and the acting around it
change. Authoring frame = armature space at PatientRest (see esc_core): head +Y, face +Z, his LEFT = +X.

New channels (added to esc_core.CH by install()):
  bw_t      0..1 hand t on the belly (IK target = skin point of the belly + normal * bo_t, palm on the skin)
  bx_t bz_t belly point in the bind frame (x = his left, z = height; bind faces -Y)
  bo_t      palm distance from the skin (m); ba_t finger angle (deg, 0 = fingers toward the midline,
            + = tilted down)
  lbw       look at his own belly (weight; blends with the look_w target)
  hop       sitting hop: extra seat height of the pelvis over the pad (m), the closed leg straps hold
Additive procedural layers (spec['add'], functions of t, zero at both clip ends): hand tremble, head
shakes, panting.
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import esc_core as E
import esc_clips as EC
import esc_hop as EH
import op_clips as OC
from esc_core import ik_keys, look_keys, P, R, X, Y, Z
from esc_clips import other, side_name, follow_keys, strap_curve, reach_body, leg_reach_body, leg_look

FPS = 30


def V(*a):
    return Vector(a)


# ===================================================================================== channels / install
PANIC_CH = []
for _t in ('L', 'R'):
    PANIC_CH += [c + '_' + _t for c in ('bw', 'bx', 'bz', 'bo', 'ba')]
PANIC_CH += ['lbw', 'hop']
DEF = {}
for _t, _sg in (('L', 1), ('R', -1)):
    DEF.update({'bw_' + _t: 0.0, 'bx_' + _t: 0.065 * _sg, 'bz_' + _t: 0.92, 'bo_' + _t: 0.014, 'ba_' + _t: 20.0})
DEF.update(lbw=0.0, hop=0.0)


def install(sess):
    """Extend the esc_core channel set (module globals, read at call time) and the session context."""
    if 'lbw' not in E.CH:
        E.CH = tuple(E.CH) + tuple(PANIC_CH)
    E.MIRROR_NEG |= {'bx_L', 'bx_R'}
    ctx = sess.ctx
    base_ch0 = type(ctx).ch0
    ctx.ch0 = lambda: {**base_ch0(ctx), **DEF}
    sess.belly = Belly(ctx)
    bc_setup(sess)


def rest_full(lib):
    return {**lib.rest(), **DEF}


def sit_full(lib):
    return {**lib.SIT(), **DEF}


def edge_full(lib, side='R'):
    return {**lib.EDGE(side), **DEF}


def belly(t, w=1.0, x=0.05, z=None, off=0.03, ang=25.0):
    """Clutch on the upper belly near the midline (the one spot with no arm-trunk / arm-thigh contact in
    every pose of the set: lying, sitting, leaning 116, knees tucked, on the edge). Left hand a little higher."""
    sg = 1 if t == 'L' else -1
    if z is None:
        z = 1.025 if t == 'L' else 0.985
    return {'bw_' + t: w, 'bx_' + t: sg * x, 'bz_' + t: z, 'bo_' + t: off, 'ba_' + t: ang, 'ik_' + t: 1.0}


def sbelly(t, w=1.0):
    return belly(t, w)


def lbelly(t, w=1.0):
    """Lying: lower on the belly (the lifted head would hit hands on the upper belly)."""
    return belly(t, w, x=0.06, z=0.93 if t == 'L' else 0.90, off=0.025)


def lift_out(t):
    """Sitting: hand up, out and forward of the hip (path to the belly that clears the flank)."""
    sg = 1 if t == 'L' else -1
    return hand_at(t, V(0.27 * sg, -0.10, 0.22))


def hand_at(t, pos, f=None, n=None, pole=None):
    """Free hand IK target with an explicit (or sitting-plant like) orientation."""
    sg = 1 if t == 'L' else -1
    return ik_keys(t, pos=pos, f=f or V(0.35 * sg, -0.9, 0.0), n=n or V(0, 0, -1), pole=pole or V(0.8 * sg, 0.5, 0.0), w=1.0)


# ===================================================================================== belly geometry
class Belly:
    """Front trunk skin of the Body mesh (chest / pelvis regions, front-facing): a smooth surface point
    for a bind-frame (x, z), skinned with the current pose (numpy LBS on the subset)."""

    def __init__(self, ctx, sigma=0.015):
        B = self.B = ctx.B
        body = B.meshes[0]
        nb = len(body.data.vertices)
        vv = B.sk_v[:nb]
        reg = B.region[:nb]
        M = (B.rig.matrix_world.inverted() @ body.matrix_world).to_3x3()
        nrm = np.array([list((M @ v.normal).normalized()) for v in body.data.vertices])
        m = (np.isin(reg, ['chest', 'pelvis']) & (np.abs(vv[:, 0]) < 0.175) & (vv[:, 2] > 0.80) & (vv[:, 2] < 1.10)
             & (vv[:, 1] < 0.0) & (nrm[:, 1] < -0.1))
        self.idx = np.where(m)[0]
        self.v = vv[self.idx]
        self.n = nrm[self.idx]
        self.ski = B.sk_i[self.idx]
        self.skw = B.sk_w[self.idx]
        self.sig = sigma

    def frame(self, out, bx, bz):
        B = self.B
        d = (self.v[:, 0] - bx) ** 2 + (self.v[:, 2] - bz) ** 2
        w = np.exp(-d / (2 * self.sig ** 2))
        k = w > 1e-4 * w.max()
        w = w[k] / w[k].sum()
        S = np.array([np.array(out[n]) for n in B.deform]) @ B.rest_inv
        A = S[self.ski[k]]
        p = np.einsum('vkij,vj->vki', A[:, :, :3, :3], self.v[k]) + A[:, :, :3, 3]
        pd = np.einsum('vk,vki->vi', self.skw[k], p)
        pos = Vector((w[:, None] * pd).sum(0))
        nr = np.einsum('vkij,vj->vki', A[:, :, :3, :3], self.n[k])
        nd = np.einsum('vk,vki->vi', self.skw[k], nr)
        n = Vector((w[:, None] * nd).sum(0)).normalized()
        Rs = out[P + 'Spine'].to_3x3() @ B.rest[P + 'Spine'].to_3x3().inverted()
        return pos, n, Rs


def hand_basis(f, n):
    n = Vector(n).normalized()
    f = Vector(f)
    f = (f - n * f.dot(n)).normalized()
    return Matrix((f, n, f.cross(n))).transposed()


def belly_targets(sess, out, t, bx, bz, off, ang):
    sg = 1 if t == 'L' else -1
    pos, n, Rs = sess.belly.frame(out, bx, bz)
    a = math.radians(ang)
    f = Rs @ Vector((-sg * math.cos(a), 0.0, -math.sin(a)))
    pole = (Rs @ Vector((sg * 1.0, 0.15, -0.30))).normalized()
    return pos + n * off, f, -n, pole


def belly_apply(sess, out, c):
    c2 = dict(c)
    for t in ('L', 'R'):
        w = min(1.0, max(0.0, c['bw_' + t]))
        if w <= 1e-6:
            continue
        tgt, f, palm, pole = belly_targets(sess, out, t, c['bx_' + t], c['bz_' + t], c['bo_' + t], c['ba_' + t])
        t0 = Vector((c['tx_' + t], c['ty_' + t], c['tz_' + t]))
        F0 = hand_basis(Vector((c['fx_' + t], c['fy_' + t], c['fz_' + t])), Vector((c['nx_' + t], c['ny_' + t], c['nz_' + t])))
        F1 = hand_basis(f, palm)
        q0, q1 = F0.to_quaternion(), F1.to_quaternion()
        if q0.dot(q1) < 0:
            q1.negate()
        Fm = q0.slerp(q1, w).to_matrix()
        p0 = Vector((c['qx_' + t], c['qy_' + t], c['qz_' + t])).normalized()
        if p0.dot(pole) > -0.999:
            pp = Quaternion().slerp(p0.rotation_difference(pole), w) @ p0
        else:
            pp = p0.lerp(pole, w)
        tt = t0.lerp(tgt, w)
        for k, v in zip(('tx', 'ty', 'tz', 'fx', 'fy', 'fz', 'nx', 'ny', 'nz', 'qx', 'qy', 'qz'),
                        list(tt) + list(Fm.col[0]) + list(Fm.col[1]) + list(pp)):
            c2[k + '_' + t] = v
        c2['arail_' + t] = c['arail_' + t] * (1.0 - w)
    lb = c['lbw']
    if lb > 1e-6:
        pos, n, _ = sess.belly.frame(out, 0.0, 0.93)
        lt = pos + n * 0.02
        lw = c['look_w']
        k = lb / (lb + lw)
        l0 = Vector((c['lk_x'], c['lk_y'], c['lk_z']))
        c2['lk_x'], c2['lk_y'], c2['lk_z'] = l0.lerp(lt, k)
        c2['look_w'] = max(lb, lw)
    return c2


def solve_hop(ctx, c, closed):
    return ctx.solve(c, closed, seat_target=0.002 + max(0.0, c.get('hop', 0.0)))


def panic_pose(sess, spec, t, c, closed):
    """pose_fn: additive layers, vertical solve, belly hands / belly look on the solved trunk (2-3 passes)."""
    ctx = sess.ctx
    for fn in spec.get('add', ()):
        for k, v in fn(t).items():
            c[k] = c[k] + v
    if not (c['bw_L'] > 1e-6 or c['bw_R'] > 1e-6 or c['lbw'] > 1e-6):
        out, cc, info = solve_hop(ctx, c, closed)
        return out, info
    # first pass only locates the trunk: belly hands on FK (their stale IK targets would stretch the arms)
    c1 = dict(c)
    for t in ('L', 'R'):
        c1['ik_' + t] = 0.0 if c['bw_' + t] > 1e-6 else c['ik_' + t]
    out, cc, info = solve_hop(ctx, c1, closed)
    for _ in range(3):
        c2 = belly_apply(sess, out, c)
        out2, cc2, info2 = solve_hop(ctx, c2, closed)
        d = (out2[P + 'Spine2'].translation - out[P + 'Spine2'].translation).length
        out, info = out2, info2
        if d < 2e-4:
            break
    return out, info


# ===================================================================================== additive layers
def bump(t, t0, t1, ramp=0.06):
    if t <= t0 or t >= t1:
        return 0.0
    a = min(1.0, (t - t0) / ramp, (t1 - t) / ramp)
    return a * a * (3 - 2 * a)


def layer(t0, t1, ramp, **chans):
    """chans: name=(amplitude, hz, phase) -> f(t) = {name: amp sin(2 pi hz t + ph) * envelope}."""
    def fn(t):
        e = bump(t, t0, t1, ramp)
        if e <= 0:
            return {}
        return {k: a * math.sin(2 * math.pi * hz * t + ph) * e for k, (a, hz, ph) in chans.items()}
    return fn


def mirror_layer(fn):
    return lambda t: E.mirror_dict(fn(t))


def pant(t0, t1, amp=1.6, hz=4.2, side=None):
    """Panting: chest / shoulders / neck heave. side: only that shoulder (e.g. the other arm is strapped)."""
    sh = {'sh_' + s: (2.5, hz, 0.4) for s in ('L', 'R') if side in (None, s)}
    return layer(t0, t1, 0.12, crunch=(amp, hz, 0.0), neck=(1.2, hz, 1.1), **sh)


def tremble(t, t0, t1, amp=0.010, hz=7.3):
    return layer(t0, t1, 0.05, **{'tx_' + t: (amp, hz, 0.0), 'ty_' + t: (amp * 0.8, hz * 0.81, 1.3), 'tz_' + t: (amp * 0.8, hz * 1.19, 0.4)})


def contact(t, hand, strap, lift):
    return {'t': round(t, 4), 'hand': hand, 'strap': strap, 'lift': lift}


# ===================================================================================== lying: wrists
T_UA = 3.0


def unbuckle_arm(lib, A):
    """Free hand A opens the other wrist strap in a panic; LIE -> LIE. v01 contacts kept exactly."""
    Pp = other(A)
    a, p = A, Pp
    sg = 1 if A == 'L' else -1
    sA, sP = side_name(A), side_name(Pp)
    strap = 'STRAP_ARM_' + Pp
    f_reach = V(-0.8 * sg, -0.3, -0.5)
    pole = V(0.4 * sg, 0.3, 1.0)
    T = T_UA
    G1, G2, OPEN = EC.ARM_GRAB1, EC.ARM_GRAB2, EC.ARM_OPEN
    sk = [(0.0, 0.0), (OPEN, 0.0), (OPEN + 0.12, 30.0), (OPEN + 0.30, 120.0)]
    sc = strap_curve(sk)

    def ob(lift, off=V(0, 0, 0), **kw):
        return lib.on_buckle(a, strap, lift=lift, off=off, **kw)
    K = [(0.0, rest_full(lib)), (0.0, {'ik_' + a: 1.0, 'ik_' + p: 1.0})]
    # wakes with a jolt, fingers splay, feet twitch
    K.append((0.06, {'neck': 9, 'crunch': 7, 'cu_L': -0.5, 'cu_R': -0.5, 'sh_' + a: 9, 'sh_' + p: 3, 'fo_L': -16, 'fo_R': -10,
                     **lib.look_strap(strap, 0.0)}))
    # lifts his head: sees his open belly (horror), legs kick in their straps
    K.append((0.15, {'neck': 21, 'crunch': 9, 'hnod': 6, 'lbw': 0.85, 'sh_' + a: 13, 'sh_' + p: 4, 'fo_L': -22, 'fo_R': 2,
                     'klift_L': 0.025}))
    K.append((0.25, {'neck': 22, 'crunch': 10, 'lbw': 0.9, 'cu_L': -0.65, 'cu_R': -0.65, 'fo_L': 0, 'fo_R': -24,
                     'klift_L': 0.0, 'klift_R': 0.025}))
    # double-take: head snaps to the strapped wrist
    K.append((0.31, {'lbw': 0.0, 'look_w': 0.95, 'neck': 12, 'crunch': 12, 'hnod': 2, 'sh_L': 3, 'sh_R': 3, 'fo_L': 0, 'fo_R': 0,
                     'klift_R': 0.0, 'arail_' + a: 1.0}))
    # free hand peels off the pad in a hurry and swings across
    K.append((0.36, {**lib.rest_hand(a, V(0.02 * sg, 0.05, 0.14)), 'arail_' + a: 0.0, 'crunch': 14, 'roll': -7 * sg,
                     'cu_' + a: -0.3, 'cu_' + p: 0.6, 'sh_L': 0, 'sh_R': 0}))
    K.append((0.46, {**ik_keys(a, pos=V(0.05 * sg, 0.13, 0.31), f=f_reach, n=V(0, 0, -1), pole=pole), 'crunch': 19,
                     'roll': -12 * sg, 'twist': -12 * sg, 'bend': 5 * sg, 'pr_' + a: 12, 'look_w': 0.85}))
    # miss #1: claws at the air over the band (toward the elbow)
    K.append((0.56, {**ob(0.035, V(0.0, 0.06, 0.0), f=f_reach, pole=pole), **reach_body(a), 'cu_' + a: -0.4}))
    K.append((0.60, {'cu_' + a: 0.75}))
    K.append((0.64, {**ob(0.09, V(0.02 * sg, 0.03, 0.0)), 'cu_' + a: -0.35, 'hyaw': 8 * sg, 'crunch': 21}))
    # miss #2: slaps the back of his own strapped hand
    K.append((0.70, {**ob(0.04, V(0.0, -0.06, 0.0)), 'cu_' + a: -0.15, 'hyaw': -5 * sg, 'crunch': 23}))
    K.append((0.73, {'cu_' + a: 0.6}))
    K.append((0.765, {**ob(0.045, V(0.0, -0.02, 0.0)), 'cu_' + a: -0.25, 'hyaw': 0.0}))
    # grab #1 (v01 contact)
    K.append((G1, {**ob(0.004), 'cu_' + a: 0.0}))
    K.append((0.88, {'cu_' + a: 0.65, 'cu_' + p: 0.5}))
    # two frantic yanks; the buckle holds
    K.append((0.93, {**ob(0.016), 'crunch': 26, 'cu_' + a: 0.75, 'sh_' + a: 8, 'neck': 13, 'ftw_' + p: 5}))
    K.append((0.98, {**ob(0.006), 'crunch': 23, 'sh_' + a: 1, 'ftw_' + p: -4}))
    K.append((1.02, {**ob(0.018), 'crunch': 26, 'sh_' + a: 9, 'neck': 14, 'ftw_' + p: 6}))
    # slip: fingers fly off (outward, toward his feet), he shakes the hand (layer), stares at the belly, double-take
    K.append((1.06, {**ob(0.07, V(-0.03 * sg, -0.08, 0.0)), 'cu_' + a: -0.55, 'crunch': 20, 'sh_' + a: 0, 'hyaw': 10 * sg,
                     'ftw_' + p: 6, 'neck': 10}))
    K.append((1.13, {'lbw': 0.55, 'neck': 15, 'hyaw': 0.0, 'ftw_' + p: -6, 'cu_' + p: 0.9}))
    K.append((1.19, {'lbw': 0.0, 'neck': 7, 'look_w': 0.85}))
    # grab #2 (v01 contact) and pop the buckle open (the hand follows the buckle to 30 deg)
    K.append((G2, {**ob(0.004), 'cu_' + a: 0.0, 'hyaw': 0.0, 'ftw_' + p: 0.0, 'neck': 4, 'crunch': 24}))
    K.append((1.33, {'cu_' + a: 0.7}))
    K += follow_keys(lib, a, strap, sc, OPEN, OPEN + 0.12)
    K.append((OPEN + 0.12, {'cu_' + a: 0.55}))
    p30, n30, _, _ = lib.buckle(strap, 30.0)
    K.append((1.61, {**ik_keys(a, pos=p30 + n30 * 0.10 + V(0.05 * sg, 0.03, 0.06)), 'cu_' + a: -0.4, 'look_w': 0.6}))
    # the freed arm rips out of the open strap, both arms flail up
    yank_pole = V(-0.8 * sg, 0.3, 0.6)
    K.append((1.61, {'arail_' + p: 1.0, 'cu_' + p: 0.9, **ik_keys(p, pole=yank_pole)}))
    K.append((1.69, {'arail_' + p: 0.0, **lib.rest_hand(p, V(0.0, 0.01, 0.05)), **ik_keys(p, pole=yank_pole)}))
    K.append((1.82, {**lib.rest_hand(p, V(-0.02 * sg, 0.10, 0.30)), **ik_keys(p, pole=yank_pole), 'cu_' + p: -0.5,
                     **ik_keys(a, pos=V(0.24 * sg, 0.08, 0.34)), 'cu_' + a: -0.5,
                     'roll': -4 * sg, 'crunch': 17, 'twist': -4 * sg, 'bend': 2 * sg, 'pr_' + a: 6, 'look_w': 0.0, 'lbw': 0.5, 'neck': 12}))
    # both hands slap onto the open belly: holds his guts in, horrified, legs kicking
    K.append((1.96, {**lbelly('L'), **lbelly('R'), 'cu_L': 0.05, 'cu_R': 0.05, 'lbw': 0.85, 'neck': 16, 'crunch': 15,
                     'roll': 0.0, 'twist': 0.0, 'bend': 0.0, 'pr_' + a: 0.0, 'klift_L': 0.025, 'fo_L': -20}))
    K.append((2.10, {'klift_L': 0.0, 'klift_R': 0.025, 'fo_L': 2, 'fo_R': -22}))
    K.append((2.24, {'klift_R': 0.0, 'klift_L': 0.02, 'fo_R': 2, 'fo_L': -16, 'neck': 15}))
    K.append((2.38, {'klift_L': 0.0, 'fo_L': 0, 'fo_R': 0, 'neck': 13, 'crunch': 12, 'lbw': 0.8}))
    # lets go and flops back to LIE
    K.append((2.50, {'bw_L': 0.0, 'bw_R': 0.0, **lib.rest_hand('L', V(0.04, 0.10, 0.17)), **lib.rest_hand('R', V(-0.04, 0.10, 0.17)),
                     'lbw': 0.0, 'neck': 6, 'crunch': 6, 'cu_L': 0.0, 'cu_R': 0.0}))
    K.append((2.66, {**lib.rest_hand('L', V(0, 0, 0.04)), **lib.rest_hand('R', V(0, 0, 0.04)), 'crunch': 2, 'neck': 2}))
    K.append((2.80, {**lib.rest_hand('L'), **lib.rest_hand('R'), 'crunch': 0.5, 'neck': 0.5, 'arail_L': 0.0, 'arail_R': 0.0}))
    K.append((2.88, {'arail_L': 1.0, 'arail_R': 1.0}))
    K.append((T, rest_full(lib)))
    K.append((T, {'ik_' + a: 1.0, 'ik_' + p: 1.0}))
    add = [tremble(a, 0.38, 0.77, 0.012),
           layer(1.06, 1.23, 0.03, **{'tx_' + a: (0.03, 9.0, 0.0), 'tz_' + a: (0.02, 9.0, 1.6), 'cu_' + a: (0.25, 9.0, 0.7)}),
           layer(1.98, 2.44, 0.06, hyaw=(16.0, 4.2, 0.0)),
           pant(0.08, 0.32, side=a), pant(1.92, 2.52, 2.0)]
    events = [
        {'name': 'LookBelly', 't': 0.15}, {'name': 'Miss', 'strap': strap, 'hand': sA, 't': 0.60},
        {'name': 'Miss', 'strap': strap, 'hand': sA, 't': 0.73},
        {'name': 'Grab', 'strap': strap, 'hand': sA, 't': G1},
        {'name': 'Slip', 'strap': strap, 'hand': sA, 't': 1.06},
        {'name': 'Grab', 'strap': strap, 'hand': sA, 't': G2},
        {'name': 'StrapOpen', 'strap': strap, 't': OPEN},
        {'name': 'Release', 'strap': strap, 'hand': sA, 't': OPEN + 0.12},
        {'name': 'BellyGrab', 't': 1.96},
    ]
    cts = [contact(G1, a, strap, 0.004), contact(G2, a, strap, 0.004)] + \
        [contact(OPEN + 0.02 * i, a, strap, 0.004) for i in range(7)]
    return dict(stem='Esc_Lie_UnbuckleArm%s_By%s_Panic_v02' % (Pp, A), v01='Esc_Lie_UnbuckleArm%s_By%s_v01' % (Pp, A),
                T=T, loop=False, start='LIE', end='LIE',
                pre={'closed': [strap], 'open': ['STRAP_ARM_' + A], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=[strap, 'STRAP_LEG_L', 'STRAP_LEG_R'], straps={strap: sk}, keys=K, add=add, events=events, contacts=cts,
                after={strap: 'open'}, pose_fn=panic_pose,
                next=['Esc_SitUp_Panic_v02 / Esc_SitUp_v01 (both arms now free)'],
                views=('wrist_' + Pp, 'side'), shots=(0.0, 0.25, 0.60, 0.80, 1.13, 1.40, 1.82, 2.20),
                beats=['0.00 LIE', '0.06 wakes with a jolt', '0.15-0.25 lifts his head: sees his open belly (horror, legs kick)',
                       '0.31 double-take to the strapped %s wrist' % sP.lower(),
                       '0.36-0.46 %s hand peels off and swings across, trembling' % sA.lower(),
                       '0.60 miss #1 (claws at the air over the band), 0.73 miss #2 (slaps his own strapped hand)',
                       '0.80 grab #1 (v01 contact), 0.93/1.02 frantic yanks, 1.06 fingers slip off',
                       '1.06-1.20 shakes the hand, stares at the belly again, double-take',
                       '1.25 grab #2, 1.40 STRAP OPEN (hand follows the buckle to 30 deg), 1.52 lets go',
                       '1.61-1.82 freed %s arm rips out of the strap, both arms flail up' % sP.lower(),
                       '1.96-2.40 both hands slap onto the open belly, head shakes no-no, legs kick, panting',
                       '2.50-3.00 lets go, flops back to LIE'])


# ===================================================================================== lying: tug loop
T_TUG = 2.0


def tug_arm(lib, Pp):
    """Strapped arm Pp yanks wildly against its strap, body jerks, legs kick; LIE loop."""
    A = other(Pp)
    a, p = A, Pp
    sg = 1 if A == 'L' else -1
    sP = side_name(Pp)
    strap = 'STRAP_ARM_' + Pp
    p0, n0, u0, w0 = lib.buckle(strap)
    band = u0 * 0.03
    f_reach = V(-0.8 * sg, -0.3, -0.5)
    pole = V(0.4 * sg, 0.3, 1.0)
    T = T_TUG

    def ob(lift, off=V(0, 0, 0), **kw):
        return lib.on_buckle(a, strap, lift=lift, off=band + off, **kw)
    K = [(0.0, rest_full(lib)), (0.0, {'ik_' + a: 1.0})]
    K.append((0.06, {'crunch': 8, 'neck': 8, 'sh_' + a: 8, 'cu_' + p: 0.9, 'cu_' + a: -0.4, 'fo_L': -16, 'fo_R': -8,
                     **lib.look_strap(strap, 0.0)}))
    K.append((0.12, {'arail_' + a: 1.0, 'look_w': 0.85, 'neck': 10, 'fo_L': 6, 'fo_R': -18}))
    K.append((0.18, {'arail_' + a: 0.0, **lib.rest_hand(a, V(0.02 * sg, 0.05, 0.13)), 'crunch': 13, 'roll': -8 * sg,
                     'fo_L': 0, 'fo_R': 0}))
    K.append((0.29, {**ob(0.06, f=f_reach, pole=pole), **reach_body(a), 'cu_' + a: -0.3}))
    K.append((0.36, {**ob(0.006), 'cu_' + a: 0.0}))
    # four wild yanks: the body jerks off the pad, strapped shoulder heaves, legs kick alternately
    for i, t0 in enumerate((0.42, 0.62, 0.82, 1.02)):
        s1, s2 = ('L', 'R') if i % 2 == 0 else ('R', 'L')
        sgn = 1 if i % 2 == 0 else -1
        K.append((t0, {'cu_' + a: 0.8, 'cu_' + p: 1.0, 'crunch': 24, **ob(0.006), 'pz': 0.0}))
        K.append((t0 + 0.08, {'sh_' + p: 9, 'sh_' + a: 10, 'crunch': 28, 'neck': 14, 'roll': -14 * sg, 'ftw_' + p: 9 * sgn,
                              'hnod': -8, 'klift_' + s1: 0.032, 'fo_' + s1: -30, 'fo_' + s2: -4, 'pz': 0.012,
                              'hyaw': 6 * sg * sgn, **ob(0.022)}))
        K.append((t0 + 0.17, {'sh_' + p: 2, 'sh_' + a: 1, 'crunch': 23, 'neck': 6, 'roll': -11 * sg, 'ftw_' + p: 0.0, 'hnod': 3,
                              'klift_' + s1: 0.0, 'fo_' + s1: 2, 'fo_' + s2: 0, 'pz': 0.0, 'hyaw': 0.0, **ob(0.006)}))
    # gives up in a rage: hand flies off, glance at the belly (horror), both legs kick
    K.append((1.24, {**lib.rest_hand(a, V(0.06 * sg, 0.02, 0.16)), 'cu_' + a: -0.5, 'hyaw': 12 * sg, 'neck': 9, 'crunch': 15,
                     'roll': -4 * sg, 'twist': -3 * sg, 'pr_' + a: 4}))
    K.append((1.34, {'lbw': 0.85, 'hyaw': 0.0, 'neck': 16, 'crunch': 14, 'klift_L': 0.022, 'klift_R': 0.022, 'fo_L': -20,
                     'fo_R': -20, 'sh_L': 10, 'sh_R': 10}))
    K.append((1.46, {'lbw': 0.85, 'klift_L': 0.0, 'klift_R': 0.0, 'fo_L': 2, 'fo_R': 2}))
    K.append((1.56, {**lib.rest_hand(a, V(0.0, 0.0, 0.06)), 'lbw': 0.0, 'look_w': 0.0, 'neck': 4, 'crunch': 4, 'roll': -2 * sg,
                     'twist': -2 * sg, 'bend': 1 * sg, 'pr_' + a: 2, 'sh_L': 0, 'sh_R': 0, 'fo_L': 0, 'fo_R': 0,
                     'cu_' + a: 0.1, 'cu_' + p: 0.2}))
    K.append((1.76, {**lib.rest_hand(a), 'arail_' + a: 0.0, 'roll': 0.0, 'crunch': 1.0, 'neck': 1.0, 'twist': 0.0, 'bend': 0.0,
                     'pr_' + a: 0.0, 'cu_' + a: 0.0, 'cu_' + p: 0.0}))
    K.append((1.86, {'arail_' + a: 1.0}))
    K.append((T, rest_full(lib)))
    K.append((T, {'ik_' + a: 1.0}))
    add = [pant(0.05, 1.95, 1.4, 4.6), layer(0.40, 1.22, 0.06, htilt=(7.0, 5.5, 0.0))]
    return dict(stem='Esc_Lie_TugArm%s_Loop_Panic_v02' % Pp, v01='Esc_Lie_TugArm%s_Loop_v01' % Pp, T=T, loop=True,
                start='LIE', end='LIE',
                pre={'closed': [strap], 'open': ['STRAP_ARM_' + A], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=[strap, 'STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, add=add, events=[], contacts=[],
                after={}, pose_fn=panic_pose,
                next=['loop', 'Esc_Lie_UnbuckleArm%s_By%s_Panic_v02' % (Pp, A)],
                views=('wrist_' + Pp, 'side'), shots=(0.0, 0.12, 0.36, 0.50, 0.70, 0.90, 1.34, 1.70),
                beats=['0.06 jolt, 0.12 glares at the strapped %s wrist' % sP.lower(), '0.18-0.36 free hand grabs the strap band',
                       '0.42 / 0.62 / 0.82 / 1.02 four wild yanks: body jerks off the pad, shoulder heaves, legs kick, head thrashes',
                       '1.24 lets go in a rage, 1.34-1.46 stares at his belly, both legs kick', '1.56-2.00 back to LIE (loop seam)'])


# ===================================================================================== sit up
T_SITUP = 1.2


def sit_up(lib):
    K = [(0.0, rest_full(lib)), (0.0, {'ik_L': 1.0, 'ik_R': 1.0})]
    K.append((0.05, {'neck': 10, 'hnod': 4, 'crunch': 6, 'cu_L': -0.45, 'cu_R': -0.45, 'sh_L': 10, 'sh_R': 10,
                     'arail_L': 1.0, 'arail_R': 1.0}))
    K.append((0.10, {'lbw': 0.8, 'neck': 14, 'crunch': 10}))
    K.append((0.13, {'arail_L': 0.0, 'arail_R': 0.0, **lib.rest_hand('L', V(0.0, 0.02, 0.07)), **lib.rest_hand('R', V(0.0, 0.02, 0.07))}))
    # sits up WAY too fast, arms swing forward
    K.append((0.22, {'pitch': 40, 'crunch': 27, 'neck': 14, 'hnod': 6, 'seat': 0.5, 'sh_L': 4, 'sh_R': 4, 'lbw': 0.3,
                     **ik_keys('L', pos=V(0.20, -0.20, 0.38), f=V(0.0, -1, 0.1), n=V(-0.3, 0, -1), pole=V(1, 0.3, -0.4)),
                     **ik_keys('R', pos=V(-0.20, -0.20, 0.38), f=V(0.0, -1, 0.1), n=V(0.3, 0, -1), pole=V(-1, 0.3, -0.4)),
                     'cu_L': 0.1, 'cu_R': 0.1}))
    K.append((0.32, {'pitch': 108, 'crunch': 20, 'neck': -4, 'hnod': -4, 'seat': 1.0, 'lbw': 0.0, 'sh_L': 0, 'sh_R': 0,
                     **ik_keys('L', pos=V(0.24, -0.30, 0.16), f=V(0.2, -1, -0.3), n=V(0, 0, -1), pole=V(1, 0.5, 0)),
                     **ik_keys('R', pos=V(-0.24, -0.30, 0.16), f=V(-0.2, -1, -0.3), n=V(0, 0, -1), pole=V(-1, 0.5, 0)),
                     'cu_L': -0.3, 'cu_R': -0.3}))
    # ...ouch: both hands slap onto the open belly
    K.append((0.42, {**sbelly('L'), **sbelly('R'), 'pitch': 97, 'crunch': 20, 'lbw': 0.9,
                     'neck': -8, 'hnod': -6, 'cu_L': 0.05, 'cu_R': 0.05}))
    # wobbles like a weeble
    K.append((0.53, {'bend': 9, 'twist': 5, 'pitch': 88, 'htilt': -9, 'crunch': 20}))
    K.append((0.65, {'bend': -10, 'twist': -6, 'pitch': 92, 'htilt': 9}))
    K.append((0.76, {'bend': 7, 'twist': 3, 'pitch': 85, 'htilt': -5}))
    K.append((0.86, {'bend': -3, 'twist': -1, 'pitch': 84, 'htilt': 2, 'lbw': 0.6}))
    # catches himself: palms slap down on the pad, quick look around (where's the door?)
    K.append((0.95, {'bw_L': 0.0, 'bw_R': 0.0, **hand_at('L', V(0.27, -0.14, 0.20)), **hand_at('R', V(-0.27, -0.14, 0.20)),
                     'lbw': 0.0, 'hyaw': 14, 'bend': 0, 'twist': 0, 'htilt': 0, 'pitch': 80, 'crunch': 12, 'cu_L': -0.3, 'cu_R': -0.3,
                     'neck': -4, 'hnod': 0}))
    K.append((1.04, {**lib.sit_plant('L', lift=0.03), **lib.sit_plant('R', lift=0.03), 'pitch': 76, 'hyaw': -12, 'cu_L': 0, 'cu_R': 0}))
    K.append((1.12, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'pitch': 79, 'hyaw': -4}))
    K.append((T_SITUP, sit_full(lib)))
    add = [pant(0.40, 1.12, 2.0, 4.0)]
    return dict(stem='Esc_SitUp_Panic_v02', v01='Esc_SitUp_v01', T=T_SITUP, loop=False, start='LIE', end='SIT',
                pre={'closed': [], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, add=add, events=[{'name': 'BellyGrab', 't': 0.42}],
                contacts=[], after={}, pose_fn=panic_pose,
                next=['Esc_Sit_UnbuckleLegsBoth_Panic_v02 / _LegL_ / _LegR_ (a leg strap closed)', 'Esc_SwingOff_R/L_Panic_v02 (all open)'],
                views=('side', 'feet'), shots=(0.0, 0.10, 0.22, 0.32, 0.42, 0.53, 0.65, 0.95),
                beats=['0.05 jolt, 0.10 glimpses his belly', '0.13-0.32 jackknifes up WAY too fast, overshoots face to the knees',
                       '0.42 both hands slap onto the open belly, hunched, panting', '0.53-0.86 wobbles side to side like a weeble',
                       '0.95-1.12 catches himself: palms slap down on the pad, quick look around', '1.20 SIT'])


# ===================================================================================== sitting: legs
T_LEG_ONE = 2.4
T_LEGS_BOTH = 2.8


def panic_leg_body():
    """v01 leg_reach_body with less spine fold (crunch 24 -> 18) and more shoulder reach (pr 14 -> 24): the buckle
    hand still reaches the v01 targets exactly and the belly hand is not crushed between chest and thighs."""
    return dict(leg_reach_body(), pitch=116, crunch=18, pr_L=24, pr_R=24)


def _leg_plan(a):
    sg = 1 if a == 'L' else -1
    return 'STRAP_LEG_' + a, V(0.15 * sg, -1, -0.05), V(0.7 * sg, 0.2, 0.6)


def _hops(K, ts, h=0.035, dur=0.07, pitch=None):
    for t0 in ts:
        K.append((t0, {'hop': 0.0}))
        d = {'hop': h}
        if pitch is not None:
            d['pitch'] = pitch[0]
        K.append((t0 + dur * 0.5, d))
        d = {'hop': 0.0}
        if pitch is not None:
            d['pitch'] = pitch[1]
        K.append((t0 + dur, d))


def unbuckle_leg(lib, a):
    """Seated: hand a fumbles the shin strap on its side open while the other hand clutches the belly;
    hops on his butt, panting; SIT -> SIT. v01 contacts kept exactly."""
    o = other(a)
    sg = 1 if a == 'L' else -1
    strap, f, pole = _leg_plan(a)
    T = T_LEG_ONE
    to = 1.35
    body = dict(panic_leg_body(), bend=-5 * sg)
    body['pr_' + o] = 4

    def ob(lift, off=V(0, 0, 0), **kw):
        return lib.on_buckle(a, strap, lift=lift, off=off, **kw)
    K = [(0.0, sit_full(lib))]
    # jolt: sees the belly, the other hand flies to it
    K.append((0.06, {'lbw': 0.75, 'crunch': 8, 'neck': -10, 'cu_L': -0.1, 'cu_R': -0.1}))
    K.append((0.12, {**lift_out(o), 'cu_' + o: -0.4}))
    K.append((0.20, {**sbelly(o), 'cu_' + o: 0.05, 'lbw': 0.85}))
    # double-take to the strapped shin, hops on his butt in panic
    K.append((0.25, {**leg_look(), 'lbw': 0.0, 'pitch': 88, 'neck': -12, 'sh_L': 0, 'sh_R': 0}))
    _hops(K, (0.27,), 0.035, 0.10, pitch=(84, 89))
    K.append((0.37, {**lib.sit_plant(a, lift=0.05)}))
    K.append((0.52, {**ik_keys(a, pos=V(0.20 * sg, -0.40, 0.20), f=f, n=V(0, 0, -1), pole=pole), 'cu_' + a: -0.2}))
    # miss: grabs his own shin above the strap
    K.append((0.60, {**ob(0.025, V(0.0, 0.07, 0.0), f=f, pole=pole), **body, **sbelly(o), 'cu_' + a: -0.3}))
    K.append((0.63, {'cu_' + a: 0.7}))
    K.append((0.68, {**ob(0.06), 'cu_' + a: -0.3}))
    # grab (v01 contact)
    K.append((EC.LEGS_GRAB, {**ob(0.012), 'cu_' + a: -0.3}))
    K.append((EC.LEGS_GRAB + 0.08, {'cu_' + a: 0.2}))
    K.append((0.94, {**ob(0.02), 'cu_' + a: 0.25, 'crunch': body['crunch'] + 3}))
    # slip, shakes the hand, glance at the belly, double-take
    K.append((1.00, {**ob(0.07, V(0.0, -0.03, 0.0)), 'cu_' + a: -0.45, 'hyaw': 8}))
    K.append((1.07, {'lbw': 0.8, 'hyaw': -6}))
    K.append((1.14, {'lbw': 0.0, 'hyaw': 0}))
    K.append((1.20, {**ob(0.012), 'cu_' + a: -0.3, 'hyaw': 0, 'crunch': body['crunch']}))
    K.append((1.28, {'cu_' + a: 0.2}))
    sk = [(0.0, 0.0), (to, 0.0), (to + 0.12, 40.0), (to + 0.30, 120.0)]
    sc = strap_curve(sk)
    K += follow_keys(lib, a, strap, sc, to, to + 0.12, lift=0.012)
    K.append((to + 0.12, {'cu_' + a: 0.3}))
    p40, n40, _, _ = lib.buckle(strap, 40.0)
    K.append((to + 0.24, {**ik_keys(a, pos=p40 + n40 * 0.08 + V(0.02 * sg, 0.04, 0.08)), 'cu_' + a: -0.3}))
    K.append((to + 0.30, {'fo_' + a: -24}))
    # sits back, the freed hand joins the belly, two panicky hops
    K.append((1.68, {'pitch': 90, 'crunch': 14, 'neck': -6, 'hnod': 0, 'twist': 0, 'bend': 0, 'pr_L': 0, 'pr_R': 0, 'fo_' + a: 6,
                     'lbw': 0.5, 'look_w': 0.0, **sbelly(o), **hand_at(o, V(-0.27 * sg, -0.12, 0.20)),
                     **ik_keys(a, pos=V(0.17 * sg, -0.30, 0.27))}))
    K.append((1.76, {**sbelly(a), **hand_at(a, V(0.27 * sg, -0.12, 0.20)), 'cu_' + a: 0.05, 'fo_' + a: 0}))
    _hops(K, (1.78, 1.92), 0.04, 0.08, pitch=(86, 90))
    # catches himself: palms back on the pad
    K.append((2.06, {'bw_L': 0.0, 'bw_R': 0.0, **hand_at('L', V(0.27, -0.12, 0.20)), **hand_at('R', V(-0.27, -0.12, 0.20)),
                     'lbw': 0.0, 'pitch': 84, 'crunch': 10, 'cu_L': -0.2, 'cu_R': -0.2}))
    K.append((2.20, {**lib.sit_plant('L', lift=0.04), **lib.sit_plant('R', lift=0.04), 'pitch': 80, 'crunch': 9, 'neck': -5,
                     'cu_L': 0.0, 'cu_R': 0.0}))
    K.append((2.32, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'pitch': 77}))
    K.append((T, sit_full(lib)))
    add = [pant(0.14, 2.30, 1.8, 4.3), tremble(a, 0.30, 0.76, 0.010),
           layer(1.00, 1.16, 0.03, **{'tx_' + a: (0.025, 9.0, 0.0), 'tz_' + a: (0.018, 9.0, 1.6), 'cu_' + a: (0.25, 9.0, 0.7)})]
    events = [{'name': 'BellyGrab', 'hand': side_name(o), 't': 0.20}, {'name': 'Hop', 't': 0.32},
              {'name': 'Miss', 'strap': strap, 'hand': side_name(a), 't': 0.63},
              {'name': 'Grab', 'strap': strap, 'hand': side_name(a), 't': EC.LEGS_GRAB},
              {'name': 'Slip', 'strap': strap, 'hand': side_name(a), 't': 1.00},
              {'name': 'Grab', 'strap': strap, 'hand': side_name(a), 't': 1.20},
              {'name': 'StrapOpen', 'strap': strap, 't': to}, {'name': 'Release', 'strap': strap, 'hand': side_name(a), 't': to + 0.12},
              {'name': 'Hop', 't': 1.82}, {'name': 'Hop', 't': 1.96}]
    cts = [contact(EC.LEGS_GRAB, a, strap, 0.012), contact(1.20, a, strap, 0.012)] + \
        [contact(to + 0.02 * i, a, strap, 0.012) for i in range(7)]
    return dict(stem='Esc_Sit_UnbuckleLeg%s_Panic_v02' % a, v01='Esc_Sit_UnbuckleLeg%s_v01' % a, T=T, loop=False,
                start='SIT', end='SIT',
                pre={'closed': ['STRAP_LEG_' + a], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_' + o]},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={strap: sk}, keys=K, add=add, events=events, contacts=cts,
                after={strap: 'open'}, pose_fn=panic_pose, root_smooth=False,
                next=['Esc_Sit_UnbuckleLeg%s_Panic_v02 if the other leg is still strapped' % o, 'Esc_SwingOff_R/L_Panic_v02'],
                views=('feet', 'side'), shots=(0.0, 0.20, 0.34, 0.63, 0.80, 1.07, 1.40, 1.82),
                beats=['0.06 jolt, sees the belly; 0.20 %s hand clutches the belly (holds it to the end)' % side_name(o).lower(),
                       '0.25 double-take to the strapped shin; 0.32 panicky butt hop, panting',
                       '0.52-0.68 %s hand dives at the shin, 0.63 misses (grabs his own shin)' % side_name(a).lower(),
                       '0.80 grab (v01 contact), 1.00 slip, shakes the hand, glance at the belly, double-take',
                       '1.20 grab #2, %.2f STRAP OPEN %s, %.2f lets go, foot wiggles' % (to, strap, to + 0.12),
                       '1.68-2.00 sits back, both hands on the belly, two hops', '2.06-2.40 palms back on the pad = SIT'])


def unbuckle_legs_both(lib):
    """Seated, both shin straps: the hands take turns between the shin buckles and the belly; SIT -> SIT.
    v01 contacts kept exactly (both grab 0.80, L slips 1.00, R opens 1.08, L grabs 1.28, L opens 1.42)."""
    T = T_LEGS_BOTH
    body = panic_leg_body()
    sL, fL, poleL = _leg_plan('L')
    sR, fR, poleR = _leg_plan('R')

    def oL(lift, off=V(0, 0, 0), **kw):
        return lib.on_buckle('L', sL, lift=lift, off=off, **kw)

    def oR(lift, off=V(0, 0, 0), **kw):
        return lib.on_buckle('R', sR, lift=lift, off=off, **kw)
    K = [(0.0, sit_full(lib))]
    K.append((0.06, {'lbw': 0.75, 'crunch': 8, 'neck': -10, 'cu_L': -0.1, 'cu_R': -0.1}))
    K.append((0.10, {**lib.sit_plant('L', lift=0.06), **lib.sit_plant('R', lift=0.06)}))
    K.append((0.16, {**lift_out('L'), **lift_out('R'), 'cu_L': -0.4, 'cu_R': -0.4}))
    K.append((0.24, {**sbelly('L'), **sbelly('R'), 'cu_L': 0.05, 'cu_R': 0.05, 'lbw': 0.9}))
    K.append((0.29, {**leg_look(), 'lbw': 0.0, 'pitch': 88, 'neck': -12, 'sh_L': 0, 'sh_R': 0}))
    _hops(K, (0.31,), 0.035, 0.08, pitch=(85, 89))
    # both hands leave the belly in a frantic dive at the shins
    K.append((0.42, {'bw_L': 1.0, 'bw_R': 1.0, **ik_keys('L', pos=V(0.20, -0.30, 0.26)), **ik_keys('R', pos=V(-0.20, -0.30, 0.26))}))
    K.append((0.52, {'bw_L': 0.0, 'bw_R': 0.0, **ik_keys('L', pos=V(0.20, -0.40, 0.20), f=fL, n=V(0, 0, -1), pole=poleL),
                     **ik_keys('R', pos=V(-0.20, -0.40, 0.20), f=fR, n=V(0, 0, -1), pole=poleR), 'cu_L': -0.3, 'cu_R': -0.3}))
    # miss (right): grabs his own shin above the strap
    K.append((0.60, {**oR(0.025, V(0, 0.07, 0), f=fR, pole=poleR), **oL(0.08, f=fL, pole=poleL), **body, 'cu_R': -0.3}))
    K.append((0.63, {'cu_R': 0.7}))
    K.append((0.67, {**oL(0.06), **oR(0.06), 'cu_R': -0.3, 'cu_L': -0.2}))
    # grabs (v01 contacts)
    K.append((EC.LEGS_GRAB, {**oL(0.012), **oR(0.012), 'cu_L': -0.3, 'cu_R': -0.3}))
    K.append((EC.LEGS_GRAB + 0.08, {'cu_L': 0.05, 'cu_R': 0.05}))
    K.append((0.94, {**oL(0.02), 'cu_L': 0.25, 'crunch': body['crunch'] + 3}))
    # left slips (shakes the hand, glance at the belly) while the right one opens
    K.append((1.00, {**oL(0.06, V(0, -0.03, 0)), 'cu_L': -0.4, 'hyaw': 8}))
    K.append((1.12, {'hyaw': -4, 'lbw': 0.55}))
    t_oR, t_oL = 1.08, 1.42
    skR = [(0.0, 0.0), (t_oR, 0.0), (t_oR + 0.12, 40.0), (t_oR + 0.30, 120.0)]
    skL = [(0.0, 0.0), (t_oL, 0.0), (t_oL + 0.12, 40.0), (t_oL + 0.30, 120.0)]
    K += follow_keys(lib, 'R', sR, strap_curve(skR), t_oR, t_oR + 0.12, lift=0.012)
    K.append((t_oR + 0.12, {'cu_R': 0.3, 'hyaw': 0, 'crunch': body['crunch'], 'lbw': 0.0}))
    p40, n40, _, _ = lib.buckle(sR, 40.0)
    K.append((t_oR + 0.24, {**ik_keys('R', pos=p40 + n40 * 0.08 + V(-0.02, 0.04, 0.08)), 'cu_R': -0.3, 'cu_L': 0.2}))
    K.append((t_oR + 0.30, {'fo_R': -22}))
    # left grabs again (v01 contact), the right one clutches the belly
    K.append((1.28, {**oL(0.012), 'cu_L': -0.3}))
    K.append((1.37, {**ik_keys('R', pos=V(-0.20, -0.30, 0.30))}))
    K.append((1.415, {**sbelly('R'), **ik_keys('R', pos=V(-0.17, -0.30, 0.27)), 'cu_R': 0.05}))
    K.append((t_oR + 0.46, {'fo_R': 6}))
    K += follow_keys(lib, 'L', sL, strap_curve(skL), t_oL, t_oL + 0.12, lift=0.012)
    K.append((t_oL + 0.12, {'cu_L': 0.3}))
    p40, n40, _, _ = lib.buckle(sL, 40.0)
    K.append((t_oL + 0.24, {**ik_keys('L', pos=p40 + n40 * 0.08 + V(0.02, 0.04, 0.08)), 'cu_L': -0.3}))
    K.append((t_oL + 0.30, {'fo_L': -22, 'fo_R': 0}))
    K.append((t_oL + 0.46, {'fo_L': 6}))
    # sits back (freed left hand comes up over the knee), both hands on the belly, three panicky hops
    K.append((1.72, {'pitch': 100, 'crunch': 14, **ik_keys('L', pos=V(0.17, -0.30, 0.27))}))
    K.append((1.80, {**hand_at('L', V(0.27, -0.12, 0.20)), **hand_at('R', V(-0.27, -0.12, 0.20)), 'pitch': 90, 'crunch': 14, 'neck': -6, 'hnod': 0, 'twist': 0, 'bend': 0, 'pr_L': 0, 'pr_R': 0, 'look_w': 0.0,
                     'lbw': 0.6, 'fo_L': 0, **sbelly('L'), **sbelly('R'), 'cu_L': 0.05, 'cu_R': 0.05}))
    _hops(K, (1.86, 2.00, 2.14), 0.04, 0.08, pitch=(86, 90))
    K.append((2.30, {'bw_L': 0.0, 'bw_R': 0.0, **hand_at('L', V(0.27, -0.12, 0.20)), **hand_at('R', V(-0.27, -0.12, 0.20)),
                     'lbw': 0.0, 'pitch': 84, 'crunch': 10, 'cu_L': -0.2, 'cu_R': -0.2}))
    K.append((2.46, {**lib.sit_plant('L', lift=0.04), **lib.sit_plant('R', lift=0.04), 'pitch': 80, 'crunch': 9, 'neck': -5,
                     'cu_L': 0.0, 'cu_R': 0.0}))
    K.append((2.62, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'pitch': 77}))
    K.append((T, sit_full(lib)))
    add = [pant(0.14, 2.70, 1.8, 4.3), tremble('R', 0.40, 0.76, 0.010), tremble('L', 0.40, 0.76, 0.008, 6.1),
           layer(1.00, 1.18, 0.03, tx_L=(0.025, 9.0, 0.0), tz_L=(0.018, 9.0, 1.6), cu_L=(0.25, 9.0, 0.7))]
    events = [{'name': 'BellyGrab', 't': 0.24}, {'name': 'Hop', 't': 0.35},
              {'name': 'Miss', 'strap': sR, 'hand': 'Right', 't': 0.63},
              {'name': 'Grab', 'strap': sL, 'hand': 'Left', 't': EC.LEGS_GRAB}, {'name': 'Grab', 'strap': sR, 'hand': 'Right', 't': EC.LEGS_GRAB},
              {'name': 'Slip', 'strap': sL, 'hand': 'Left', 't': 1.00},
              {'name': 'StrapOpen', 'strap': sR, 't': t_oR}, {'name': 'Release', 'strap': sR, 'hand': 'Right', 't': t_oR + 0.12},
              {'name': 'Grab', 'strap': sL, 'hand': 'Left', 't': 1.28},
              {'name': 'StrapOpen', 'strap': sL, 't': t_oL}, {'name': 'Release', 'strap': sL, 'hand': 'Left', 't': t_oL + 0.12},
              {'name': 'Hop', 't': 1.90}, {'name': 'Hop', 't': 2.04}, {'name': 'Hop', 't': 2.18}]
    cts = [contact(EC.LEGS_GRAB, 'L', sL, 0.012), contact(EC.LEGS_GRAB, 'R', sR, 0.012), contact(1.28, 'L', sL, 0.012)] + \
        [contact(t_oR + 0.02 * i, 'R', sR, 0.012) for i in range(7)] + [contact(t_oL + 0.02 * i, 'L', sL, 0.012) for i in range(7)]
    return dict(stem='Esc_Sit_UnbuckleLegsBoth_Panic_v02', v01='Esc_Sit_UnbuckleLegsBoth_v01', T=T, loop=False, start='SIT', end='SIT',
                pre={'closed': ['STRAP_LEG_L', 'STRAP_LEG_R'], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': []},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={sL: skL, sR: skR}, keys=K, add=add, events=sorted(events, key=lambda e: e['t']),
                contacts=cts, after={sL: 'open', sR: 'open'}, pose_fn=panic_pose, root_smooth=False,
                next=['Esc_SwingOff_R/L_Panic_v02'], views=('feet', 'side'),
                shots=(0.0, 0.24, 0.35, 0.63, 0.80, 1.12, 1.42, 1.90),
                beats=['0.06 jolt, 0.24 both hands clutch the belly', '0.29 double-take to the feet, 0.35 butt hop',
                       '0.42-0.67 frantic dive at both shins, 0.63 right hand misses (grabs his shin)',
                       '0.80 both grab (v01 contacts), 1.00 left slips: shakes the hand, glance at the belly',
                       '1.08 STRAP OPEN LEG_R, 1.20 lets go, 1.41 right hand clutches the belly', '1.28 left grabs again, 1.42 STRAP OPEN LEG_L, 1.54 lets go',
                       '1.80-2.22 sits back, both hands on the belly, three panicky hops', '2.30-2.80 palms back on the pad = SIT'])


# ===================================================================================== swing off
T_SWING = 1.4


def swing_off(lib, side='R'):
    if side == 'L':
        sp = swing_off(lib, 'R')
        sp.update(stem='Esc_SwingOff_L_Panic_v02', v01='Esc_SwingOff_L_v01', end='EDGE_L', leg_clear=0.010,
                  keys=EC.mirror_keys(sp['keys'], sit_full(lib)), add=[mirror_layer(f) for f in sp['add']],
                  next=['Esc_HopRun_L_BellyClutch_v02 / Esc_HopRun_L_v01'],
                  beats=[b.replace('right', 'left').replace('EDGE_R', 'EDGE_L') for b in sp['beats']])
        return sp

    def pl(px, py, yaw, **kw):
        return {**lib.plant('L', px, py, yaw, **kw), **lib.plant('R', px, py, yaw, **kw)}
    K = [(0.0, sit_full(lib)), (0.0, {'fl_L': 78, 'fl_R': 78})]
    K.append((0.06, {'lbw': 0.8, 'crunch': 8, 'neck': -6, 'cu_L': -0.1, 'cu_R': -0.1}))
    K.append((0.11, {**lift_out('L'), **lift_out('R'), 'cu_L': -0.4, 'cu_R': -0.4}))
    K.append((0.19, {**sbelly('L'), **sbelly('R'), 'cu_L': 0.05, 'cu_R': 0.05, 'lbw': 0.9,
                     'crunch': 17, 'hnod': -6, **pl(-0.21, -0.30, -98, lift=0.12), 'lrail_L': 1.0, 'lrail_R': 1.0}))
    # double-take at his right edge; knees tuck (no hands to push with: rocks back)
    K.append((0.42, {'lrail_L': 0.0, 'lrail_R': 0.0, 'fl_L': 126, 'fl_R': 126, 'kn_L': 128, 'kn_R': 128, 'fo_L': -10, 'fo_R': -10,
                     'pitch': 72, 'crunch': 16, 'px': -0.02, 'lbw': 0.0, 'hyaw': -30, 'neck': -4, 'hnod': 0, 'sh_L': 0, 'sh_R': 0}))
    # wriggles round on his butt, legs pedalling
    K.append((0.51, {'yaw': -28, 'px': -0.05, 'py': -0.09, 'fl_L': 132, 'fl_R': 127, 'kn_L': 134, 'kn_R': 129, 'pitch': 73,
                     'hyaw': -20, 'bend': 4}))
    K.append((0.60, {'yaw': -50, 'px': -0.08, 'py': -0.14, 'fl_L': 128, 'fl_R': 132, 'kn_L': 130, 'kn_R': 135, 'pitch': 76,
                     'hyaw': -14, 'bend': -4}))
    K.append((0.69, {'yaw': -76, 'px': -0.13, 'py': -0.24, 'fl_L': 116, 'fl_R': 113, 'kn_L': 122, 'kn_R': 119, 'pitch': 80,
                     'hyaw': -6, 'bend': 3}))
    # overshoots and slides off the edge: nearly falls, arms fly off the belly
    K.append((0.77, {'yaw': -98, 'px': -0.21, 'py': -0.30, 'fl_L': 84, 'fl_R': 80, 'kn_L': 84, 'kn_R': 80, 'pitch': 88, 'hyaw': 0,
                     'bend': 0, 'crunch': 12, **pl(-0.21, -0.30, -98, out=0.16, back=-0.24, lift=0.32)}))
    K.append((0.86, {'bw_L': 0.0, 'bw_R': 0.0, 'px': -0.27, 'pz': -0.035, 'seat': 0.4, 'pitch': 98, 'crunch': 4, 'neck': 16,
                     'hnod': 12, 'fl_L': 62, 'fl_R': 58, 'kn_L': 46, 'kn_R': 52, 'fo_L': 20, 'fo_R': 16,
                     **pl(-0.27, -0.30, -98, lift=0.25, out=0.34), 'cu_L': -0.6, 'cu_R': -0.6}))
    # catches himself: palms slap onto the pad, hauls back onto the edge
    K.append((0.95, {**pl(-0.17, -0.30, -90), 'px': -0.25, 'pz': -0.02, 'seat': 0.6, 'pitch': 94, 'neck': 10, 'hnod': 6,
                     'fl_L': 76, 'fl_R': 74, 'kn_L': 80, 'kn_R': 84, 'cu_L': 0.0, 'cu_R': 0.0, 'yaw': -94}))
    K.append((1.07, {'px': -0.18, 'pz': 0.0, 'seat': 1.0, 'pitch': 86, 'yaw': -91, 'neck': 6, 'hnod': 10, 'kn_L': 92, 'kn_R': 90,
                     'fl_L': 84, 'fl_R': 83, 'fo_L': 6, 'fo_R': 4}))
    # glance down at the belly, panting
    K.append((1.16, {'lbw': 0.75, 'neck': 8, 'hnod': 8, 'px': -0.17}))
    K.append((1.28, {'lbw': 0.0, 'neck': 2, 'hnod': 2, 'yaw': -90, 'kn_L': 89, 'kn_R': 87}))
    K.append((T_SWING, edge_full(lib)))
    add = [pant(0.14, 1.36, 1.6, 4.0)]
    return dict(stem='Esc_SwingOff_R_Panic_v02', v01='Esc_SwingOff_R_v01', T=T_SWING, loop=False, start='SIT', end='EDGE_R',
                pre={'closed': [], 'open': list(E.LIMB_STRAPS), 'any': []},
                closed0=[], straps={}, keys=K, add=add,
                events=[{'name': 'BellyGrab', 't': 0.19}, {'name': 'SlipOffEdge', 't': 0.86}, {'name': 'CatchPalms', 't': 0.95}],
                contacts=[], after={}, pose_fn=panic_pose,
                next=['Esc_HopRun_R_BellyClutch_v02 / Esc_HopRun_R_v01'], views=('three_quarter', 'side'),
                shots=(0.0, 0.19, 0.42, 0.60, 0.77, 0.86, 0.95, 1.16),
                beats=['0.06 sees the belly, 0.19 both hands clutch it', '0.27 double-take at his right edge',
                       '0.19-0.42 knees tuck, no hands: rocks back', '0.51-0.69 wriggles round on his butt, legs pedalling',
                       '0.77-0.86 overshoots and slides over the edge: nearly falls, arms fly up',
                       '0.95 catches himself: palms slap onto the pad', '1.07 hauls back onto the edge, 1.16 glance at the belly',
                       '1.40 EDGE_R (interrupt rule unchanged: before 0.76 SlumpSit, after 0.76 SlumpEdge)'])


# ===================================================================================== stumble off (interrupt)
T_STUMBLE = 1.8
# v01 key time -> v02 time for the shared tail (knees buckle .. DOWN)
ST_MAP = [(0.30, 0.70), (0.52, 0.88), (0.62, 0.96), (0.84, 1.12), (1.00, 1.28), (1.12, 1.40), (1.28, 1.56), (1.60, 1.80)]


def stumble_off(lib, land_c, side='R'):
    """Interrupt right after the hop-off (crossfade from HopRun / HopRun_BellyClutch 0.47-0.98): jolt, both hands
    to the belly, nearly falls forward, catches himself, wobbles, knees give, drops to the knees and topples face
    down = DOWN_x (ragdoll start). The tail is the v01 Stumble_Off channel state (exact end pose)."""
    if side == 'L':
        sp = stumble_off(lib, E.mirror_dict(land_c), 'R')
        sp.update(stem='Esc_Stumble_Off_L_Panic_v02', v01='Esc_Stumble_Off_L_v01', side='L', start='LAND_L', end='DOWN_L', views=('exit_L',),
                  keys=[(0.0, {**land_c, **DEF})] + [(t, E.mirror_dict(d)) for t, d in sp['keys'][1:]],
                  add=[mirror_layer(f) for f in sp['add']],
                  beats=[b.replace('_R', '_L') for b in sp['beats']])
        return sp
    v1 = EH.stumble_off(lib, land_c, 'R')
    cv, _ = E.build_curves(v1['keys'], lib.ctx)

    def v01_at(tv):
        return {k: f(tv) for k, f in cv.items()}
    LX, LY = land_c['px'], land_c['py']
    K = [(0.0, {**land_c, **DEF}), (0.0, {'floor': 1.0})]
    K.append((0.08, {**{k: v for k, v in v01_at(0.08).items() if k in ('pitch', 'crunch', 'neck', 'hnod', 'cu_L', 'cu_R', 'afl_L', 'afl_R',
                                                                       'aab_L', 'aab_R', 'el_L', 'el_R')},
                     **belly('L'), **belly('R'), 'ik_L': 0.0, 'ik_R': 0.0}))
    # both hands slap onto the belly, hunched, staring at it
    K.append((0.18, {'ik_L': 1.0, 'ik_R': 1.0, **belly('L'), **belly('R'), 'pitch': 112,
                     'crunch': 22, 'lbw': 0.8, 'neck': 0, 'hnod': -4, 'cu_L': 0.05, 'cu_R': 0.05, 'fik_L': 1.0, 'fik_R': 1.0}))
    # nearly falls forward, catches himself, wobbles
    K.append((0.32, {'pitch': 126, 'pz': -0.16, 'crunch': 18, 'neck': 16, 'hnod': -10, 'lbw': 0.0}))
    K.append((0.46, {'pitch': 100, 'pz': -0.08, 'roll': 6, 'hyaw': 10, 'crunch': 20, 'neck': 2, 'hnod': 0, 'lbw': 0.5}))
    K.append((0.58, {'pitch': 104, 'pz': -0.10, 'roll': -6, 'hyaw': -8, 'htilt': 8}))
    # knees give (v01 tail from here, the hands stay on the belly until he topples)
    for tv, t2 in ST_MAP:
        d = v01_at(tv)
        if t2 < 1.20:                 # keep the belly hands (IK + belly channels stay as keyed below)
            for k in ['ik_L', 'ik_R'] + PANIC_CH:
                d.pop(k, None)
            d['lbw'] = 0.4 if t2 < 1.0 else 0.0
        K.append((t2, d))
    K.append((1.04, {'bw_L': 1.0, 'bw_R': 1.0, 'ik_L': 1.0, 'ik_R': 1.0}))
    K.append((1.20, {'ik_L': 0.0, 'ik_R': 0.0}))
    add = [pant(0.18, 0.66, 2.0, 4.5), layer(0.18, 0.66, 0.05, kn_L=(4.0, 7.0, 0.0), kn_R=(4.0, 7.0, 2.0))]
    return dict(stem='Esc_Stumble_Off_R_Panic_v02', v01='Esc_Stumble_Off_R_v01', side='R', T=T_STUMBLE, loop=False,
                start='LAND_R', end='DOWN_R',
                pre={'closed': [], 'open': list(E.LIMB_STRAPS), 'any': []},
                closed0=[], straps={}, keys=K, add=add, contacts=[], pose_fn=panic_pose,
                events=[{'name': 'Limp', 't': 0.08}, {'name': 'BellyGrab', 't': 0.18}, {'name': 'NearlyFalls', 't': 0.32},
                        {'name': 'KneesHit', 't': 0.88}, {'name': 'BodyHitsFloor', 't': 1.28},
                        {'name': 'RagdollReady', 't': T_STUMBLE, 'note': 'end pose DOWN_x (= v01): face down on the floor, relaxed; start the knocked-down ragdoll from this pose (or hold it)'}],
                after={}, next=['knocked-down ragdoll (start from the last frame), then the capture flow'],
                views=('exit',), shots=(0.0, 0.08, 0.18, 0.32, 0.46, 0.70, 0.96, 1.20),
                root='none: rig object at PatientRest, the Hips curves place the body on the floor beside the table (Apply Root Motion off)',
                beats=['0.00 = LAND_R (HopRun_R at %.2f; crossfade in from HopRun_R / HopRun_R_BellyClutch 0.47-0.98)' % EH.STUMBLE_FROM,
                       '0.08 jolt, arms fly up', '0.18 both hands slap onto the belly, hunched', '0.32 nearly falls forward',
                       '0.46-0.58 catches himself, wobbles', '0.70 knees give, 0.88 knees hit the floor (hands still on the belly)',
                       '0.96-1.28 topples face down, arms flop out at the last moment', '1.28 body hits the floor, 1.40-1.80 bounce, settles = DOWN_R'])


# ===================================================================================== belly-clutch run (cycle space)
BC = dict(hunch=36.0, neck_back=-24.0, bob=5.0, hip=36.0, knee=26.0, h0=0.035, h1=0.09,
          bx=0.05, bz_L=1.04, bz_R=1.005, off=0.05, pole_y=0.0, pole_z=-0.40)


def _smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def bc_setup(sess):
    """Swing-phase weights of each foot (from the plain Flee_Run ankle height) and the rotation signs."""
    B, flee = sess.B, sess.flee
    S = flee['samples']
    n = len(S) - 1
    poses = [OC.pose_from_vals(B, S[i]) for i in range(n)]
    sess.bc_sw = {}
    for s in ('Left', 'Right'):
        h = np.array([p[P + s + 'Foot'].translation.z for p in poses])
        lo = float(h.min())
        sess.bc_sw[s] = np.array([_smooth01((x - lo - BC['h0']) / (BC['h1'] - BC['h0'])) for x in h])
    p0 = poses[0]
    lat = _lat(B, p0)
    # hunch sign: the head goes forward (-Y, the cycle faces -Y)
    o = {k: v.copy() for k, v in p0.items()}
    B.rotate_subtree(o, 'Spine', R(lat, 10))
    sess.bc_sg_hunch = 1.0 if o[P + 'Head'].translation.y < p0[P + 'Head'].translation.y else -1.0
    o = {k: v.copy() for k, v in p0.items()}
    B.rotate_subtree(o, 'LeftUpLeg', R(lat, 10))
    sess.bc_sg_hip = 1.0 if o[P + 'LeftLeg'].translation.y < p0[P + 'LeftLeg'].translation.y else -1.0
    sess.bc_sg_knee = -sess.bc_sg_hip      # knee flexion folds the shin back (opposite sense to hip flexion)
    sess.bc_cache = {}


def _lat(B, out):
    Rh = out[P + 'Hips'].to_3x3() @ B.rest[P + 'Hips'].to_3x3().inverted()
    return (Rh @ X).normalized()


def _sw(sess, s, u):
    w = sess.bc_sw[s]
    n = len(w)
    x = (u % 1.0) * n
    i = int(math.floor(x)) % n
    f = x - math.floor(x)
    return w[i] * (1 - f) + w[(i + 1) % n] * f


def bc_cycle_pose(sess, phase):
    """Flee_Run_v01 at cycle time `phase`, cartoon-hunched, knees high, both hands clutching the belly
    (cycle space: in place, faces -Y, floor z = 0). Periodic in phase."""
    Tc = sess.flee['Tc']
    u = (phase % Tc) / Tc
    key = round(u, 6) % 1.0
    if key in sess.bc_cache:
        return {k: v.copy() for k, v in sess.bc_cache[key].items()}
    B, ctx = sess.B, sess.ctx
    out = EH.flee_pose(B, sess.flee, u * Tc)
    lat = _lat(B, out)
    for s in ('Left', 'Right'):
        sw = _sw(sess, s, u)
        if sw > 1e-5:
            B.rotate_subtree(out, s + 'UpLeg', R(lat, sess.bc_sg_hip * BC['hip'] * sw))
            B.rotate_subtree(out, s + 'Leg', R(lat, sess.bc_sg_knee * BC['knee'] * sw))
    hb = BC['hunch'] + BC['bob'] * math.sin(4 * math.pi * u)
    B.rotate_subtree(out, 'Spine', R(lat, sess.bc_sg_hunch * hb))
    B.rotate_subtree(out, 'Neck', R(lat, sess.bc_sg_hunch * BC['neck_back']))
    # arms: shoulders back to the bind relation, then both hands on the belly (elbows out, chicken wings)
    sp2 = P + 'Spine2'
    for s, sg in E.SIDES:
        for nme in B.subtree(s + 'Shoulder'):
            out[nme] = out[sp2] @ (B.rest[sp2].inverted() @ B.rest[nme])
    for s, sg in E.SIDES:
        t = s[0]
        bx, bz = BC['bx'] * sg, BC['bz_' + t]
        tgt, f, palm, pole = belly_targets(sess, out, t, bx, bz, BC['off'], 25.0)
        _, _, Rs = sess.belly.frame(out, bx, bz)
        bounce = 0.006 * math.sin(4 * math.pi * u + (0.0 if t == 'L' else math.pi))
        tgt = tgt + (Rs @ Z) * bounce
        pole = (Rs @ Vector((sg * 1.0, BC['pole_y'], BC['pole_z']))).normalized()
        ctx.hand_ik(out, s, tgt, f, palm, pole, tag='hand_' + t)
        B.curl(out, s, 0.25, thumb=0.15)
    sess.bc_cache[key] = {k: v.copy() for k, v in out.items()}
    return out


def run_loop(lib, sess):
    Tc = sess.flee['Tc']
    return dict(stem='Esc_Run_BellyClutch_Loop_Panic_v02', v01='Flee_Run_v01 (Escape_Police_v01, same legs/footfalls/speed)',
                T=Tc, loop=True, start='BCRUN', end='BCRUN', cycle=True, pre={'closed': [], 'open': [], 'any': []},
                closed0=[], straps={}, keys=[], events=[{'name': 'FootL', 't': 0.0}, {'name': 'FootR', 't': round(Tc / 2, 4)}],
                contacts=[], after={}, next=['loop'], views=('run',), shots=tuple(round(Tc * i / 8, 4) for i in range(8)),
                root='in place (like Flee_Run_v01): ground +Y at 3.20 m/s, play at speed / 3.20; drive the free NPC root (Apply Root Motion off)',
                beats=['Flee_Run_v01 legs (left heel touchdown at frame 1, right at 0.283 s), knees driven higher in the swing',
                       'cartoon hunch (spine %.0f deg forward, bobbing twice per cycle), head pushed forward like a chicken' % BC['hunch'],
                       'both hands clutch the open belly, elbows out (chicken wings), hands bounce with the steps',
                       'seam = frame 1 (exact)'])


# ===================================================================================== hop run, belly clutch
def hop_keys_bc(lib, side='R'):
    K = list(EH.hop_keys(lib, 'R'))
    K = [(0.0, {**K[0][1], **DEF})] + K[1:]
    K += [(0.10, {'lbw': 0.8}), (0.20, {'lbw': 0.8}), (0.30, {'lbw': 0.0}),
          (0.34, {'bw_L': 0.0, 'bw_R': 0.0}),
          (0.39, {'ik_L': 1.0, 'ik_R': 1.0}),
          (0.41, {**belly('L'), **belly('R'), 'cu_L': 0.05, 'cu_R': 0.05}),
          (0.52, {'crunch': 22, 'lbw': 0.0}), (0.60, {'crunch': 26, 'lbw': 0.5}), (0.70, {'crunch': 18, 'lbw': 0.6}),
          (0.80, {'crunch': 18, 'lbw': 0.5}), (0.86, {'crunch': 20, 'lbw': 0.0})]
    if side == 'L':
        K = [(0.0, {**lib.EDGE('L'), **DEF})] + [(t, E.mirror_dict(d)) for t, d in K[1:]]
    return K


def hop_pose_bc(sess, spec, t, c, closed):
    side = spec.get('side', 'R')
    EH.setup_run(sess, side)
    ctx = sess.ctx
    out, info = None, {}
    if t < EH.RUN_T0 + EH.RUN_BLEND:
        out, info = panic_pose(sess, spec, t, c, closed)
    if t >= EH.RUN_T0:
        Rr = EH.run_root(sess, t, side)
        fp = bc_cycle_pose(sess, EH.run_phase(t))
        cyc = {k: Rr @ v for k, v in fp.items()}
        uu = min(1.0, (t - EH.RUN_T0) / EH.RUN_BLEND)
        w = uu * uu * (3 - 2 * uu)
        if w >= 1.0:
            return cyc, {'run_w': 1.0, 'dist': EH.dist(t)}
        out = EH.blend_full(sess.B, out, cyc, w)
        zmin = float(ctx.world_pts(out)[:, 2].min())
        if zmin < 0.001:
            M = Matrix.Translation((0, 0, 0.001 - zmin))
            out = {k: M @ v for k, v in out.items()}
        return out, {'run_w': w, 'dist': EH.dist(t)}
    return out, info


def hop_run_bc(lib, side='R'):
    sp = EH.hop_run(lib, side)
    end = 'RUN0_BC' + ('_L' if side == 'L' else '')
    sp.update(stem='Esc_HopRun_%s_BellyClutch_v02' % side, v01='Esc_HopRun_%s_v01' % side, end=end, keys=hop_keys_bc(lib, side),
              views=('exit_L',) if side == 'L' else ('exit',),
              pose_fn=hop_pose_bc, contacts=[], add=[],
              shots=(0.0, 0.12, 0.30, 0.43, 0.52, 0.70, 0.93, 1.24),
              next=['Esc_Run_BellyClutch_Loop_Panic_v02 (loop) on the free NPC root placed at %s (= RUN0%s of v01), moving 3.2 m/s along its facing'
                    % ('RUN0_L' if side == 'L' else 'RUN0', '_L' if side == 'L' else '')])
    sp['events'] = [{'name': 'LookBelly', 't': 0.12}, {'name': 'BellyGrab', 't': 0.41}, {'name': 'Land', 't': EH.LAND_T},
                    {'name': 'RunStart', 't': EH.RUN_T0},
                    {'name': 'HandOffToRun', 't': EH.T_HOP, 'note': 'end pose = Esc_Run_BellyClutch_Loop_Panic_v02 frame 1 at %s'
                     % ('RUN0_L' if side == 'L' else 'RUN0')}]
    sp['beats'] = ['0.00 EDGE_%s' % side, '0.12-0.24 stares at his belly (gulp)', '0.30-0.39 leans, palms push, slides off the edge',
                   '0.41 both hands slap onto the belly (from here to the end)', '0.52 LAND, squash, hunched',
                   '0.60-0.80 dizzy wobble, hands on the belly, glances at it', '0.86-0.98 hop-turn 40 deg toward the foot end',
                   '0.98-1.50 accelerates 0.8 -> 3.2 m/s into the belly-clutch run', '1.50 = Esc_Run_BellyClutch_Loop_Panic_v02 frame 1 at RUN0%s'
                   % ('_L' if side == 'L' else '')]
    return sp


# ===================================================================================== registry
def make_specs(sess):
    lib = sess.lib
    sp = {}
    sp['UnbuckleArmR_ByL'] = unbuckle_arm(lib, 'L')
    sp['UnbuckleArmL_ByR'] = unbuckle_arm(lib, 'R')
    sp['TugArmR'] = tug_arm(lib, 'R')
    sp['TugArmL'] = tug_arm(lib, 'L')
    sp['SitUp'] = sit_up(lib)
    sp['UnbuckleLegL'] = unbuckle_leg(lib, 'L')
    sp['UnbuckleLegR'] = unbuckle_leg(lib, 'R')
    sp['UnbuckleLegsBoth'] = unbuckle_legs_both(lib)
    sp['SwingOffR'] = swing_off(lib, 'R')
    sp['SwingOffL'] = swing_off(lib, 'L')
    for nm, src, a in (('StumbleOffR', 'HopRun', 'R'), ('StumbleOffL', 'HopRun_L', 'L')):
        curves, _ = E.build_curves(sess.specs[src]['keys'], lib.ctx)
        sp[nm] = stumble_off(lib, {k: cv(EH.STUMBLE_FROM) for k, cv in curves.items()}, a)
    sp['HopRunR_BC'] = hop_run_bc(lib, 'R')
    sp['HopRunL_BC'] = hop_run_bc(lib, 'L')
    sp['RunBellyLoop'] = run_loop(lib, sess)
    return {'P2_' + k: v for k, v in sp.items()}


def add_keys(sess):
    """New pose keys: BCRUN (belly-clutch run frame 1, cycle space) and RUN0_BC / RUN0_BC_L (the same at the
    v01 RUN0 / RUN0_L hand-off roots, PatientRest armature space)."""
    B = sess.B
    fp = bc_cycle_pose(sess, 0.0)
    sess.keys['BCRUN'] = B.values_from_pose(fp)
    for side, k in (('R', 'RUN0_BC'), ('L', 'RUN0_BC_L')):
        EH.setup_run(sess, side)
        Rr = EH.run_root(sess, EH.T_HOP, side)
        sess.keys[k] = B.values_from_pose({n: Rr @ v for n, v in fp.items()})
