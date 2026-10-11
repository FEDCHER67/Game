"""v02 revisions of four escape-set clips (fixes round 2026-10-11): Escape_Scramble_Start, JumpOut,
Hit_React_Front, Stagger. Registry keys keep the v01 names; build_ep_v02.py writes <Clip>_v02.* files.

Reuses ep_core / clips_escape / clips_police (imported, never edited). See ep_core.py for the conventions.
"""
import math, os, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
import ep_core as E
import clips_escape as CE
import clips_police as CPOL
from ep_core import (R, QI, Curve, P, X, Y, Z, SIDES, SGN, smooth, smoother, clamp, lerp, win, bump, K, Chan, stand,
                     arm, spine, head, idle_canonical, step_arc)

CLIPS = {}
HERE = Path(__file__).resolve().parent


# ============================================================================= shared checks
def shoulder_gimbal(ctx, frames, info=None):
    """FBX reimport guard. The exporter writes each bone's parent-relative rotation (rest included) as
    XYZ Euler, computed in float32. For the shoulders that local rotation sits at Euler Y = +-90 deg exactly
    at rest (well conditioned: the gimbal branch). Close to, but not at, +-90 deg (|cos Y| between ~1e-6 and
    ~1e-3) the float32 conversion splits X/Z badly and the reimport is off by up to 0.3 mm (the v01 JumpOut
    failure: Y = 90.0034 deg at frame 12.5). Reports the samples in that band."""
    B = ctx.B
    band = []
    for f in sorted(frames):
        Pf = frames[f]
        for s in SIDES:
            n = P + s + 'Shoulder'
            L = Pf[B.parent[n]].inverted() @ Pf[n]
            c = abs(math.cos(L.to_quaternion().to_euler('XYZ')[1]))
            if 1.9e-6 < c < 1.5e-3:          # 16 * FLT_EPSILON: below it Blender takes the gimbal branch
                band.append((round(c, 7), f, s))
    band.sort()
    return {'shoulder_gimbal_band_samples': len(band), 'shoulder_gimbal_worst': band[:4]}


def big_steps(ctx, frames, info=None, lim=20.0):
    """Every key-to-key local rotation above `lim` degrees (bone, frame): the validator's limit is 25."""
    B = ctx.B
    ks = sorted(frames)
    vals = [B.values_from_pose(frames[f]) for f in ks]
    out = []
    for i in range(len(ks) - 1):
        for n in B.order:
            a_, b_ = vals[i][n]['q'], vals[i + 1][n]['q']
            d = abs(sum(x * y for x, y in zip(a_, b_)))
            ang = math.degrees(2 * math.acos(min(1.0, d)))
            if ang > lim:
                out.append((round(ang, 1), ks[i + 1], n[len(P):]))
    return {'per_big_steps': sorted(out, reverse=True)[:12]}


def with_checks(extra=None):
    def f(ctx, frames, info):
        d = shoulder_gimbal(ctx, frames, info)
        d.update(big_steps(ctx, frames, info))
        if extra:
            d.update(extra(ctx, frames, info))
        return d
    return f


# ============================================================================= JumpOut v02
# v01 problems: (1) a pop at 0.30-0.33 s: hips, spine and head unfolded ~80 deg in 0.04 s right after the
# peek (head 1746 m/s^2); (2) the FBX check: the run blend started at 0.38 s with an ease-in, so the first
# sample (frame 12.5) nudged the shoulders' exporter Euler Y to 90.0034 deg (see shoulder_gimbal).
# v02: the peek / gulp reads first (head dips, shoulders jolt up with a sharp onset, arms swing back), then
# the unfold is spread over 0.30-0.45 s with the head leading and the hips following (overlap); the toe push
# starts earlier; the shoulder shrug carries the shoulders decisively off the gimbal band and fades into the
# Flee_Run shoulders through the landing blend. Frog hop, flight, Land event (0.567 s), stumble and run are v01.
JO_T, JO_CROUCH, JO_TAKEOFF, JO_LAND = CE.JO_T, CE.JO_CROUCH, CE.JO_TAKEOFF, CE.JO_LAND
VF = E.VAN_FLOOR
SH_ON = 17 / 60          # shrug onset exactly on a sample (value 0 there, ~9 deg one sample later)


class JumpCtx2(CE.JumpCtx):
    def __init__(self, B, cache):
        CE.JumpCtx.__init__(self, B, cache)
        self.ch = Chan(
            hy=K((JO_CROUCH, 0.03), (JO_TAKEOFF, -0.06), (0.42, -0.02), (JO_LAND, 0.0)),
            # the unfold is one long ease per channel (no intermediate keys: a key between the extremes gives the
            # Hermite a near-constant-speed middle with abrupt starts): head first (0.30), spine (0.31), hips (0.32)
            pitch=K((JO_CROUCH, 40), (0.32, 43), (0.49, 11), (JO_LAND, 10)),
            spine_p=K((JO_CROUCH, 16), (0.31, 19), (0.48, -7), (JO_LAND, -4)),
            look=K((JO_CROUCH, 24), (0.30, 29), (0.47, -18), (JO_LAND, -15)),
            # arms: swing back for the anticipation (gulp), then up and flailing
            arms_f=K((JO_CROUCH, -40), (0.305, -50), (0.35, -24), (0.47, 85), (0.51, 95), (0.545, 75), (JO_LAND, 50)),
            arms_o=K((JO_CROUCH, 20), (JO_TAKEOFF, 30), (0.40, 55), (JO_LAND, 40)),
            elb=K((JO_CROUCH, 30), (JO_TAKEOFF, 10), (0.40, 30), (JO_LAND, 35)),
            # gulp shrug: sharp onset on a sample, jolts up, stays shrugged through the fall
            sh=K((JO_CROUCH, 0), (SH_ON, 0, (0.0, 300.0)), (0.31, 13), (0.37, 9), (0.47, 8), (JO_LAND, 7)),
            # ...and hunch forward (protraction). This is the component that moves the shoulders' exporter Euler Y
            # off 90 deg (a pure shrug keeps it there), so its onset is sharp too
            shf=K((JO_CROUCH, 0), (SH_ON, 0, (0.0, 260.0)), (0.31, 11), (0.37, 9), (0.47, 7), (JO_LAND, 6)),
            blend=K((0.38, 0), (JO_LAND, 1)),
        )


def jo2_air_pose(ctx, t):
    """Crouch on the sill (planted feet), gulp, take-off, flight; blends into the Flee_Run parts by the landing."""
    b = ctx.body
    c = ctx.ch(t)
    if t <= JO_TAKEOFF:
        hz = VF + 0.40 + 0.10 * smooth((t - JO_CROUCH) / (JO_TAKEOFF - JO_CROUCH)) ** 2 - 0.04 * bump(t, JO_CROUCH, 0.30, JO_TAKEOFF)
    else:
        tau = t - JO_TAKEOFF
        hz = VF + 0.50 + CE.JO_VZ * tau - 0.5 * 9.81 * tau * tau
    hips = Vector((0.0, c.hy, hz))
    hrot = R(X, c.pitch)
    J = {}
    spine(J, pitch=c.spine_p)
    head(J, pitch=c.look - c.pitch * 0.6, yaw=8 * math.sin(2 * math.pi * 6 * t), neck=0.5)
    for s in SIDES:
        flail = 16 * math.sin(2 * math.pi * 4.5 * t + (0 if s == 'Left' else 2.2)) * smooth((t - JO_TAKEOFF) / 0.12)
        arm(J, s, fwd=c.arms_f + flail, out=c.arms_o, elbow=c.elb, wrist=-15, sh_up=c.sh, sh_fwd=c.shf)
    legs, toes = {}, {}
    run_legs = ctx.run.legs
    for s in SIDES:
        if t <= JO_TAKEOFF:
            M = ctx._crouch_foot(s, t)
            peel = 50 * smooth((t - 0.285) / (JO_TAKEOFF - 0.285))     # push off through the toes (v01: from 0.30)
            if peel > 0:
                lat = R(Z, SGN[s] * 8) @ Vector(X)
                mtp = M @ (b.F0[s].inverted() @ b.pivot0[s]['mtp'])
                M = E.rot_about(mtp, R(lat, peel)) @ M
            legs[s], toes[s] = M, peel
        else:
            # flight (v01): from the take-off foot to the Flee_Run foot at landing time, with a comic air-run tuck
            M0 = ctx._crouch_foot(s, JO_TAKEOFF)
            mtp = M0 @ (b.F0[s].inverted() @ b.pivot0[s]['mtp'])
            M0 = E.rot_about(mtp, R(R(Z, SGN[s] * 8) @ Vector(X), 50)) @ M0
            u_land = 0.0 if s == 'Left' else 0.5
            M1, toe1 = run_legs[s](u_land)
            k = (t - JO_TAKEOFF) / (JO_LAND - JO_TAKEOFF)
            Ts = JO_LAND - JO_TAKEOFF
            p0, p1 = M0.translation, M1.translation
            v0 = Vector((0, CE.jo_speed(JO_TAKEOFF), 1.0))
            v1 = Vector((0, 0.95 * CPOL.FLEE.v, -1.2)) if s == 'Left' else Vector((0, -2.0, 0.0))
            pos = Vector([E.hermite(p0[i], v0[i], p1[i], v1[i], Ts, k) for i in range(3)])
            if s == 'Right':
                ky = k ** 3
                pos.y = E.hermite(p0.y, 0.0, p1.y, -1.0, Ts, ky) - 0.05 * math.sin(math.pi * ky)
            pos.z += 0.34 * bump(k, 0.0, 0.40, 0.92) * (1.0 if s == 'Left' else 0.4)
            pos.y += (-0.12 if s == 'Left' else 0.10) * math.sin(math.pi * k)
            q0, q1 = M0.to_quaternion(), M1.to_quaternion()
            if q0.dot(q1) < 0:
                q1.negate()
            q = q0.slerp(q1, smooth(k))
            M = q.to_matrix().to_4x4()
            M.translation = pos
            legs[s], toes[s] = M, 50 * (1 - smooth(k / 0.4)) + toe1 * smooth(k)
    w = c.blend
    if w > 0:
        r = ctx.run0
        hips = hips.lerp(r['hips'], w)
        hrot = hrot.slerp(r['hrot'], w)
        for n in set(J) | set(r['J']):
            a = J.get(n, QI())
            bq = r['J'].get(n, QI())
            if a.dot(bq) < 0:
                bq = -bq
            J[n] = a.slerp(bq, w)
    curl = {s: (0.1 * (1 - w) + w * CPOL.FLEE.fist, 0.8 * w) for s in SIDES}
    return b.pose(hips, hrot, J, legs=legs, toes=toes, curl=curl)


def jo2_pose(ctx, t):
    b = ctx.body
    if t >= JO_LAND:
        return CE.jo_pose(ctx, t)          # landing squash, stumble and run: unchanged from v01
    if t >= JO_CROUCH:
        return jo2_air_pose(ctx, t)
    # frog hop (v01): whole-skeleton blend from the crawl frame 1 (on the van floor) to the crouch
    P1, _ = jo2_air_pose(ctx, JO_CROUCH)
    shift = CE.JO_GROUND(t) - CE.JO_GROUND(JO_CROUCH)
    P1 = {n: Matrix.Translation((0, shift, 0)) @ m for n, m in P1.items()}
    k = smoother(t / JO_CROUCH)
    kr = smooth(t / JO_CROUCH)
    P0 = {n: Matrix.Translation((0, CE.JO_GROUND(t), 0)) @ m for n, m in ctx.P0.items()}
    u = t / JO_CROUCH
    out = E.rigid_blend(b, P0, P1, k, kr, lift=0.13 * math.sin(math.pi * k) ** 0.7, kr_feet=smooth(u / 0.9),
                        feet_local=True, floor_guard=VF + 0.010)
    return out, {'leg_over': 0.0, 'arm_over': 0.0, 'hips': tuple(out[P + 'Hips'].translation)}


CLIPS['JumpOut'] = dict(CE.CLIPS['JumpOut'])
CLIPS['JumpOut'].update({
    'setup': JumpCtx2, 'pose': jo2_pose, 'extra_metrics': with_checks(),
    'beats': ['0.00-0.27 frog hop (v01): from the crawl, hands shove off and both feet snap under him onto the sill',
              '0.27-0.31 crouched on the edge peeking down: GULP (head dips at 0.295 s, shoulders jolt up at 0.283 s), arms swing back',
              '0.29-0.45 unfold, spread out: the head comes up first, the spine and hips follow; toes push off from 0.285 s, feet leave at 0.35 s',
              '0.35-0.567 falls: arms fly up and flail, cannonball tuck until the van is behind him, drop of 0.55 m (v01)',
              '0.567 LAND on the left foot (= a Flee_Run touchdown): squash 9 cm, chest and head fold, arms splay (v01)',
              '0.567-1.02 stumbling forward lean while the legs already run (v01)', '1.133 = Flee_Run frame 1'],
})


# ============================================================================= Escape_Scramble_Start v02
# Frame 1 = the frozen cargo sit contract (Cargo_Sit_Idle_v04 frame 1, raw values from
# Idle_Knock_v03/Cargo_Sit_Contract_v04.json; hips (-0.357, 0, 0.114)); last frame = Escape_Scramble_v01 frame 1.
# Every sample keeps something on the van floor: butt + feet, then the right palm (the pivot of the turn), the
# left palm, the left knee, and the left palm again on the last frame.
# The contract pose is rebuilt exactly by Body.pose (torso FK deltas, IK arms, fingers) except the legs: the
# cargo package's IK takes the knee roll from an unsplayed reference, so its thighs and shins are rolled 6.85 deg
# about their own axes relative to ep_core's hinge IK. That constant twist is applied on top of the leg IK and
# faded out while the legs swing (it never moves a joint).
SIT_JSON = 'Cargo_Sit_Contract_v04.json'
TORSO = ('Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftShoulder', 'RightShoulder')
SS2_T = 1.0
PALM = CE.CrawlP.palm_h          # wrist height of a flat palm (crawl measurement)
KNEE_R = CE.CrawlP.knee_r        # knee joint height of a knee resting on the floor
RH_PLANT = Vector((-0.19, -0.208, PALM))     # right palm = where the crawl tail's right palm is planted (lifts at 0.98 s)
RH_PLANT1 = Vector((-0.27, -0.20, PALM))     # right palm, first slap (nearer the body; re-planted on RH_PLANT at 0.72 s)
LH_PLANT = Vector((0.11, -0.26, PALM))       # left palm, first plant (across the body, under the left shoulder)
LK_PLANT = Vector((0.13, 0.276, KNEE_R))     # left knee = where the crawl tail's left knee is planted (lifts at 1.0 s)
TAIL = 0.10                                  # the last 0.10 s are the crawl itself (see tail_pose)
TAIL_IN = 0.74                               # the turn blends into the tail from here
CRAWL_YAW = -4.0                             # crawl pelvis yaw around the tail start
BUTT = Vector((-0.37, 0.0, 0.0))             # rocking pivot: the sit bones, under the hip joints


def sit_contract_file():
    """PKG/../Idle_Knock_v03/Cargo_Sit_Contract_v04.json (after the packages are merged), else $CARGO_SIT_CONTRACT."""
    cands = [HERE.parent / 'Idle_Knock_v03' / SIT_JSON]
    env = os.environ.get('CARGO_SIT_CONTRACT')
    if env:
        cands.append(Path(env))
    for p in cands:
        if p.is_file():
            return p
    raise FileNotFoundError('%s not found: expected %s or $CARGO_SIT_CONTRACT' % (SIT_JSON, cands[0]))


def load_sit_contract():
    p = sit_contract_file()
    raw = p.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    vals = {n: {'q': tuple(v['q']), 'loc': tuple(v['loc']) if v['loc'] else None} for n, v in d['values'].items()}
    return vals, hashlib.sha256(raw).hexdigest(), p


def pose_params(B, body, pose):
    """Body.pose parameters that rebuild `pose`: hips, hips rotation, torso FK deltas, and per limb the end-bone
    matrix, the wrist/ankle, the elbow/knee and the bend direction (joint offset from the limb line)."""
    base = B.idle
    D = {n: pose[n] @ base[n].inverted() for n in B.order}
    J = {n: (D[B.parent[P + n]].inverted() @ D[P + n]).to_quaternion() for n in TORSO}
    limbs = {}
    for s in SIDES:
        for kind, names in (('leg', ('UpLeg', 'Leg', 'Foot')), ('arm', ('Arm', 'ForeArm', 'Hand'))):
            H, Km, Ee = (pose[P + s + x].translation.copy() for x in names)
            line = (Ee - H).normalized()
            perp = (Km - H) - line * (Km - H).dot(line)
            limbs[(kind, s)] = {'end': pose[P + s + names[2]].copy(), 'pos': Ee, 'joint': Km, 'bend': perp.normalized(),
                                'hq': (pose[P + s + 'Hand'].to_3x3() @ body.H0[s].inverted()).to_quaternion() if kind == 'arm' else None}
    return pose[P + 'Hips'].translation.copy(), D[P + 'Hips'].to_quaternion(), J, limbs


def hinge_of(H, A, bend):
    line = (Vector(A) - Vector(H)).normalized()
    p = Vector(bend) - line * Vector(bend).dot(line)
    return line.cross(p.normalized())


class VPath:
    """Keyed points: keys (t, xyz) -> monotone Hermite per component, flat at the ends (stops on the end keys)."""

    def __init__(self, keys):
        self.c = [Curve([(k[0], k[1][i]) for k in keys]) for i in range(3)]

    def __call__(self, t):
        return Vector([c(t) for c in self.c])


class QPath:
    """Keyed rotations: slerp between neighbouring keys with smoothstep timing (eases into each key)."""

    def __init__(self, keys):
        self.ts = [k[0] for k in keys]
        qs = []
        for k in keys:
            q = k[1].copy()
            if qs and q.dot(qs[-1]) < 0:
                q.negate()
            qs.append(q)
        self.qs = qs

    def __call__(self, t):
        ts, qs = self.ts, self.qs
        if t <= ts[0]:
            return qs[0].copy()
        if t >= ts[-1]:
            return qs[-1].copy()
        i = max(j for j in range(len(ts)) if ts[j] <= t)
        return qs[i].slerp(qs[i + 1], smooth((t - ts[i]) / (ts[i + 1] - ts[i])))


def plant_q(s):
    """Flat palm, fingers toward the doors (-Y), turned 12 deg out: the crawl's stance hand."""
    sg = SGN[s]
    return R(Z, -sg * 12) @ R(Y, -sg * 90) @ R(X, -90)


class SS2Ctx:
    def __init__(self, B, cache):
        self.B = B
        self.body = b = E.Body(B)
        self.crawl = CE.CrawlCtx(B, cache)
        vals, self.sit_sha, self.sit_path = load_sit_contract()
        self.sit_values = vals
        CLIPS['Escape_Scramble_Start']['start'] = (
            'Cargo sit contract = Cargo_Sit_Idle_v04 frame 1, exact raw values of %s (sha256 %s); hips (-0.357, 0, 0.114), '
            'facing +X, back to the wall x = -0.65' % (SIT_JSON, self.sit_sha))
        self.S0 = B.pose_from_values(vals)
        self.C1 = tail_pose(self, SS2_T)
        self.pS = pose_params(B, b, self.S0)
        hipsS, hrotS, JS, LS = self.pS
        # cargo leg roll: rebuild the contract legs with ep_core's IK and measure the constant twist
        legs = {s: (LS[('leg', s)]['end'], hinge_of(self.S0[P + s + 'UpLeg'].translation, LS[('leg', s)]['pos'],
                                                     LS[('leg', s)]['bend'])) for s in SIDES}
        out, _ = b.pose(hipsS, hrotS, JS, legs=legs)
        self.twist = {s: {n: (out[P + s + n].to_3x3().inverted() @ self.S0[P + s + n].to_3x3()).to_quaternion()
                          for n in ('UpLeg', 'Leg')} for s in SIDES}
        # foot relative to the shin while kneeling (the crawl's planted left knee at 0.40 s)
        o, _ = CE.crawl_pose(self.crawl, 0.40)
        self.Lk = (o[P + 'Left' + 'Leg'].to_3x3().inverted() @ o[P + 'Left' + 'Foot'].to_3x3()).to_quaternion()
        self.l1 = b.leg['Left']['l1']
        self.l2 = b.leg['Left']['l2']
        self.Larm = b.Larm
        self.pC1 = pose_params(B, b, self.C1)
        self.ch = ss2_chan(self)
        self.paths = ss2_paths(self)
        self._cache = {}
        ss2_body(self, 0.0)
        self.sh0 = dict(self._sh)
        self.vsets = leg_vertex_sets(B)
        # hand relative to the forearm in the shin grip (the relaxed wrist of the reaches)
        self.grip_rel = {s: (self.S0[P + s + 'ForeArm'].to_3x3().inverted() @ self.S0[P + s + 'Hand'].to_3x3()).to_quaternion()
                         for s in SIDES}
        self._cache = {}
        self._final = None

    def tail(self, t):
        key = ('tail', round(t, 6))
        if key not in self._cache:
            self._cache[key] = pose_params(self.B, self.body, tail_pose(self, t))
        return self._cache[key]


def tail_pose(ctx, t):
    """The crawl itself (Escape_Scramble_v01 at tau = t - T), carried so the van floor stands still: planted palms
    and knees stay put while the body moves toward the doors at the crawl speed. tau = 0 is exactly frame 1."""
    tau = t - SS2_T
    out, _ = CE.crawl_pose(ctx.crawl, tau)
    if abs(tau) < 1e-12:
        return out
    M = Matrix.Translation((0.0, -CE.CrawlP.v * tau, 0.0))
    return {n: M @ m for n, m in out.items()}


def leg_vertex_sets(B):
    """Mesh vertex indices (concatenated Body, Face, Outfit) by dominant bone: thigh+shin, foot+toes and hand+fingers
    per side, and the seat (pelvis and spine)."""
    import numpy as np
    sets = {k: [] for k in ('leg_Left', 'leg_Right', 'foot_Left', 'foot_Right', 'hand_Left', 'hand_Right', 'fore_Left',
                            'fore_Right', 'seat')}
    off = 0
    for o in B.meshes:
        vg = [g.name for g in o.vertex_groups]
        for vx in o.data.vertices:
            g = max(vx.groups, key=lambda g: g.weight, default=None)
            n = vg[g.group][len(P):] if g else ''
            for s in SIDES:
                if n in (s + 'UpLeg', s + 'Leg'):
                    sets['leg_' + s].append(off + vx.index)
                elif n.startswith(s + 'Foot') or n.startswith(s + 'Toe'):
                    sets['foot_' + s].append(off + vx.index)
                elif n.startswith(s + 'Hand'):
                    sets['hand_' + s].append(off + vx.index)
                if n == s + 'ForeArm':
                    sets['fore_' + s].append(off + vx.index)
            if n in ('Hips', 'Spine', 'Spine1', 'Spine2'):
                sets['seat'].append(off + vx.index)
        off += len(o.data.vertices)
    return {k: np.array(v) for k, v in sets.items()}


def qslerp(a, b, w):
    b = b.copy()
    if a.dot(b) < 0:
        b.negate()
    return a.slerp(b, w)


def ss2_chan(ctx):
    hipsS, hrotS, JS, LS = ctx.pS
    T = SS2_T
    TT = T - TAIL
    return Chan(
        # pelvis: rocks forward over the butt as he bows (0.36-0.48), lifts and swings round the right palm (+X +Y),
        # comes over the knees; from TAIL_IN it blends into the crawl tail (which carries it on toward the doors)
        hx=K((0, hipsS.x), (0.48, hipsS.x), (0.55, -0.31), (0.63, -0.19), (0.73, -0.07), (TT, -0.01)),
        hy=K((0, hipsS.y), (0.48, hipsS.y), (0.55, -0.02), (0.63, 0.03), (0.74, 0.09), (TT, 0.12)),
        hz=K((0, hipsS.z), (0.42, hipsS.z), (0.49, hipsS.z + 0.045), (0.56, 0.23), (0.63, 0.29), (0.72, 0.32), (TT, 0.32)),
        yaw=K((0, 90), (0.40, 90), (0.50, 72), (0.60, 36), (0.70, 8), (TT, CRAWL_YAW)),
        pitch=K((0, -16), (0.36, -16), (0.48, 10), (0.56, 42), (0.64, 58), (0.72, 66), (TT, 72)),
        roll=K((0, 0), (0.40, 0), (0.50, -6), (0.62, -6), (0.74, -2), (TT, 0)),
        seat=K((0, 1), (0.46, 1), (0.53, 0), (T, 0)),
        wT=K((0, 0), (TAIL_IN, 0), (TT, 1), (T, 1)),
        # torso: contract deltas -> the tail's deltas, plus acting on top
        wt=K((0, 0), (0.46, 0), (TT, 1), (T, 1)),
        sp=K((0, 0), (0.34, 0), (0.46, 18), (0.56, 18), (0.66, 10), (0.78, 2), (TT, 0)),
        sr=K((0, 0), (0.36, 0), (0.48, -16), (0.60, -10), (0.78, 0), (TT, 0)),
        sy=K((0, 0), (0.10, 0), (0.17, -9), (0.30, -10), (0.40, -24), (0.48, -40), (0.56, -30), (0.66, -12), (0.80, 0), (TT, 0)),
        # head: SNAP glance at the doors (lin tangent = whip), held stare, keeps facing the doors while the body turns
        ny=K((0, 0), (0.09, 0), (0.15, -54, ('lin', 'auto')), (0.19, -48), (0.30, -50), (0.40, -40), (0.48, -26),
             (0.62, -16), (0.75, -6), (TT, 0)),
        np=K((0, 0), (0.09, 0), (0.15, -14), (0.30, -16), (0.46, -34), (0.56, -52), (0.66, -40), (0.80, -12), (TT, 0)),
        nr=K((0, 0), (0.09, 0), (0.16, 6), (0.30, 4), (0.50, 0), (TT, 0)),
        shr=K((0, 0), (0.09, 0), (0.13, 10), (0.20, 7), (0.30, 9), (0.42, 3), (0.56, 0), (TT, 0)),
        trem=K((0, 0), (0.15, 0), (0.19, 1), (0.32, 1), (0.38, 0), (T, 0)),
        # left knee planted from its landing (pelvis height solved from it)
        kpl=K((0, 0), (0.75, 0), (0.82, 1), (0.967, 1), (T, 0)),
        # the left knee hands over to the crawl's (it lifts on frame 1)
        wKe=K((0, 0), (0.967, 0), (T, 1)),
        # leg roll: cargo convention -> ep_core convention while the legs swing
        tw=K((0, 1), (0.50, 1), (0.66, 0), (T, 0)),
        # contact solves (palm / knee pressed onto the floor on the skinned mesh) while planted; they fade where the
        # crawl lifts them (the crawl's own contacts hover about 1 cm)
        kcR=K((0, 0), (0.48, 0), (0.505, 1), (0.625, 1), (0.65, 0), (0.705, 0), (0.73, 1), (0.955, 1), (0.985, 0), (T, 0)),
        kcL=K((0, 0), (0.585, 0), (0.61, 1), (0.72, 1), (0.75, 0), (T, 0)),
        kcK=K((0, 0), (0.82, 0), (0.84, 1), (0.96, 1), (T, 0)),
        # the left palm lands early on its crawl frame-1 spot (0.967 s) and stays
        lhl=K((0, 0), (0.80, 0), (0.967, 1), (T, 1)),
    )


def ss2_paths(ctx):
    hipsS, hrotS, JS, LS = ctx.pS
    T = SS2_T
    p = {}
    aR, aL = LS[('arm', 'Right')], LS[('arm', 'Left')]
    to_body = R(Z, -(90.0 - CRAWL_YAW))          # contract (yaw 90) -> pelvis-yaw frame of the crawl
    # right palm: lets go of the shin, flies out to the doors side and slaps down as he bows; pivot of the turn,
    # planted on the crawl tail's own right-palm spot (it lifts there at 0.98 s inside the tail)
    p['wR'] = VPath([(0, aR['pos']), (0.27, aR['pos']), (0.37, aR['pos'] + Vector((-0.10, -0.14, 0.0))),
                     (0.45, RH_PLANT1 + Vector((0.0, 0.0, 0.06))), (0.50, RH_PLANT1), (0.645, RH_PLANT1), (0.68, (RH_PLANT1 + RH_PLANT) * 0.5 + Vector((0, 0, 0.06))),
                     (0.72, RH_PLANT), (T, RH_PLANT)])
    # first slap: the palm-down orientation (fingers turned about the vertical) nearest to the shin grip, so the
    # wrist turns as little as possible on the way down
    q1 = min((R(Z, float(psi)) @ plant_q('Right') for psi in range(-180, 180, 5)),
             key=lambda q: max(aR['hq'].rotation_difference(q).angle / 0.19,
                               q.rotation_difference(plant_q('Right')).angle / 0.085))
    p['qR'] = QPath([(0, aR['hq']), (0.27, aR['hq']), (0.50, q1), (0.64, q1), (0.725, plant_q('Right')), (T, plant_q('Right'))])
    # elbow directions in the pelvis-yaw frame (they turn with him): contract -> back and out like the crawl's
    p['pR'] = VPath([(0, to_body @ aR['bend']), (0.27, to_body @ aR['bend']), (0.39, (to_body @ aR['bend']).lerp(Vector((-0.8, 0.8, 0.3)).normalized(), 0.5)),
                     (0.50, Vector((-0.8, 0.8, 0.3))),
                     (T, Vector((-0.6, 1.0, 0.3)))])
    # left palm: lets go later, reaches across the body, plants, lifts and joins the tail's crawl step
    p['wL'] = VPath([(0, aL['pos']), (0.42, aL['pos']), (0.51, Vector((0.10, -0.22, 0.20))),
                     (0.60, LH_PLANT), (0.735, LH_PLANT), (0.80, LH_PLANT + Vector((0.04, -0.04, 0.09))), (T, LH_PLANT + Vector((0.12, -0.13, 0.04)))])
    p['qL'] = QPath([(0, aL['hq']), (0.42, aL['hq']), (0.59, plant_q('Left')), (T, plant_q('Left'))])
    p['pL'] = VPath([(0, to_body @ aL['bend']), (0.42, to_body @ aL['bend']), (0.51, Vector((0.8, 0.1, 0.6))), (0.60, Vector((0.8, 0.7, 0.4))),
                     (T, Vector((0.6, 1.0, 0.3)))])
    # the hands on the shins follow the shoulders while gripping (shrug, glance)
    p['gripR'] = K((0, 0), (0.10, 0), (0.15, 0.8), (0.24, 0.8), (0.29, 0), (T, 0))
    p['gripL'] = K((0, 0), (0.10, 0), (0.15, 0.8), (0.30, 0.8), (0.38, 0), (T, 0))
    # finger curl (grip 0.5 / thumb 0.4 -> spread for the slap -> open palms of the crawl)
    p['curl'] = {'Right': (K((0, 0.5), (0.27, 0.5), (0.42, -0.15), (0.50, 0.1), (T, 0.1)), K((0, 0.4), (0.27, 0.4), (0.44, 0.0), (T, 0.0))),
                 'Left': (K((0, 0.5), (0.42, 0.5), (0.52, -0.15), (0.60, 0.1), (T, 0.1)), K((0, 0.4), (0.42, 0.4), (0.54, 0.0), (T, 0.0)))}
    # legs: planted feet (IK) until 'lift', then a keyframed FK swing (leg_keys) to 'land': the left knee lands on
    # the tail's left-knee spot, the right leg ends on the tail's right leg (it is mid-swing there)
    p['leg'] = {'Left': {'lift': 0.49, 'land': 0.82}, 'Right': {'lift': 0.52, 'land': T - TAIL}}
    return p


def ss2_body(ctx, t, kz=0.0):
    """Pelvis and torso at time t: (hips, hrot, J, hip-joint offsets, channels). kz lowers the planted knee spot."""
    b, B = ctx.body, ctx.B
    c = ctx.ch(t)
    hipsS, hrotS, JS, LS = ctx.pS
    hipsT, hrotT, JT, LT = ctx.tail(max(t, SS2_T - TAIL - 0.2))      # tail parameters (blended in late)
    hrot = R(Z, c.yaw) @ R(X, c.pitch) @ R(Y, c.roll)
    hips = Vector((c.hx, c.hy, c.hz))
    if c.seat > 0:
        # still sitting: the pelvis turns about the butt contact on the floor (rocks / swivels on it, no skid)
        Rd = (hrot @ hrotS.inverted()).to_matrix()
        hips = hips + ((BUTT + Rd @ (hipsS - BUTT)) - hipsS) * c.seat
    if c.wT > 0:
        hips = hips.lerp(hipsT, c.wT)
        hrot = qslerp(hrot, hrotT, c.wT)
    tr = c.trem
    A = {}
    spine(A, pitch=c.sp + 1.2 * tr * math.sin(2 * math.pi * 9 * t), roll=c.sr, yaw=c.sy)
    head(A, pitch=c.np + 1.5 * tr * math.sin(2 * math.pi * 11 * t + 1.0), roll=c.nr + 1.5 * tr * math.sin(2 * math.pi * 9 * t + 2.0),
         yaw=c.ny + 2.0 * tr * math.sin(2 * math.pi * 10 * t), neck=0.45)
    J = {}
    for n in TORSO:
        J[n] = A.get(n, QI()) @ qslerp(JS[n], JT[n], c.wt)
    for s in SIDES:
        J[s + 'Shoulder'] = R(Y, -SGN[s] * c.shr) @ J[s + 'Shoulder']
    o1, _ = B.fk(b.base, dict(J, Hips=hrot), Matrix.Translation(hips - b.hips0))
    v = {s: o1[P + s + 'UpLeg'].translation - hips for s in SIDES}
    ctx._sh = {s: o1[P + s + 'Arm'].translation.copy() for s in SIDES}
    if c.kpl > 0:
        K_ = LK_PLANT - Vector((0, 0, kz))
        H = hips + v['Left']
        d2 = (H.x - K_.x) ** 2 + (H.y - K_.y) ** 2
        zreq = K_.z + math.sqrt(max(ctx.l1 ** 2 - d2, 0.0)) - v['Left'].z
        hips.z = lerp(hips.z, zreq, c.kpl)
    return hips, hrot, J, v, c


def leg_dirs(out, s):
    H, Km, A = (out[P + s + x].translation for x in ('UpLeg', 'Leg', 'Foot'))
    return (Km - H).normalized(), (A - Km).normalized()


def lift_state(ctx, s):
    """Leg at its lift-off (planted-foot IK then): thigh and shin unit vectors in the pelvis-yaw frame, foot rel. shin."""
    key = ('lift', s)
    if key not in ctx._cache:
        tl = ctx.paths['leg'][s]['lift']
        out, _ = ss2_pose_raw(ctx, tl, legs_only=True)
        Rb = R(Z, ctx.ch(tl).yaw).inverted()
        d, sh = leg_dirs(out, s)
        rel = (out[P + s + 'Leg'].to_3x3().inverted() @ out[P + s + 'Foot'].to_3x3()).to_quaternion()
        ctx._cache[key] = (Rb @ d, Rb @ sh, rel)
    return ctx._cache[key]


def land_state(ctx, s):
    """Leg at its landing: the left knee on its spot (knee mode), the right leg = the tail's right leg."""
    key = ('land', s)
    if key not in ctx._cache:
        tl = ctx.paths['leg'][s]['land']
        hips, hrot, J, v, c = ss2_body(ctx, tl)
        Rb = R(Z, c.yaw).inverted()
        if s == 'Left':
            H = hips + v[s]
            Kp, shin = knee_mode(ctx, H, c, 0.0)
            d, sh, rel = (Kp - H).normalized(), shin, ctx.Lk
        else:
            o = tail_pose(ctx, tl)
            d, sh = leg_dirs(o, s)
            rel = (o[P + s + 'Leg'].to_3x3().inverted() @ o[P + s + 'Foot'].to_3x3()).to_quaternion()
        ctx._cache[key] = (Rb @ d, Rb @ sh, rel)
    return ctx._cache[key]


def vslerp(a, b, w):
    """Slerp of unit vectors (falls back to a normalised lerp when they are nearly opposite)."""
    if w <= 0:
        return Vector(a)
    if w >= 1:
        return Vector(b)
    if Vector(a).dot(Vector(b)) < -0.999:
        return Vector(a).lerp(Vector(b), w).normalized()
    return Vector(a).slerp(Vector(b), w)


def dorsi_rel(ctx, s, deg=38.0):
    """Foot relative to the shin at the lift-off, flexed toes-up by `deg` about the ankle hinge (cached)."""
    key = ('dorsi', s)
    if key not in ctx._cache:
        tl = ctx.paths['leg'][s]['lift']
        out, _ = ss2_pose_raw(ctx, tl, legs_only=True)
        Hh, Kk, Aa = (out[P + s + x].translation for x in ('UpLeg', 'Leg', 'Foot'))
        shin = out[P + s + 'Leg'].to_3x3()
        foot = out[P + s + 'Foot'].to_3x3()
        rel0 = (shin.inverted() @ foot).to_quaternion()
        axl = (shin.inverted() @ (Kk - Hh).cross(Aa - Kk)).normalized()
        toe_l = foot.inverted() @ (out[P + s + 'ToeBase'].translation - Aa)
        best = None
        for sg in (1.0, -1.0):
            q = Quaternion(axl, math.radians(sg * deg)) @ rel0
            z = (shin @ q.to_matrix() @ toe_l).z
            if best is None or z > best[0]:
                best = (z, q)
        ctx._cache[key] = best[1]
    return ctx._cache[key]


def _pitch(v):
    return math.degrees(math.atan2(v.z, -v.y))


def leg_keys(ctx, s):
    """Swing keys per leg (cached): thigh pitch, knee flexion, splay, foot pointing; the ends come from the
    lift-off and landing states."""
    key = ('keys', s)
    if key not in ctx._cache:
        L = ctx.paths['leg'][s]
        A0, K0 = lift_pts(ctx, s)
        A1, K1 = land_pts(ctx, s)
        th0, th1 = _pitch(K0), _pitch(K1)
        sh0, sh1 = _pitch(A0 - K0), _pitch(A1 - K1)
        fl0 = (th0 - sh0) % 360.0
        fl1 = (th1 - sh1) % 360.0
        if th1 > th0:
            th1 -= 360.0
        t0, t1 = L['lift'], L['land']
        tk = [t0 + (t1 - t0) * f for f in (0.0, 0.22, 0.42, 0.63, 0.82, 1.0)]
        ctx._cache[key] = {
            # knees up / heels kick up behind (knee still high) / the folded leg drops / opens into the kneel
            'th': K((tk[0], th0), (tk[1], th0 + 8.0), (tk[2], 30.0), (tk[3], -45.0), (tk[4], -80.0), (tk[5], th1)),
            'fl': K((tk[0], fl0), (tk[1], 140.0), (tk[2], 162.0), (tk[3], 160.0), (tk[4], 132.0), (tk[5], fl1)),
            'sp': K((tk[0], 0.0), (tk[1], 8.0), (tk[4], 8.0), (tk[5], 0.0)),
            'ab': K((tk[0], 0.0), (tk[2], 18.0), (tk[3], 48.0), (tk[4], 42.0), (tk[5], 0.0)),
            # the foot flexes (toes up) while the shin hangs down, and points only as the shin swings through back
            'df': K((tk[0], 0.0), (tk[1], 1.0), (tk[5], 1.0)),
            'pt': K((tk[0], 0.0), (tk[2], 0.0), (tk[4], 1.0), (tk[5], 1.0)),
        }
    return ctx._cache[key]


def lift_pts(ctx, s):
    key = ('liftp', s)
    if key not in ctx._cache:
        tl = ctx.paths['leg'][s]['lift']
        out, _ = ss2_pose_raw(ctx, tl, legs_only=True)
        Rb = R(Z, ctx.ch(tl).yaw).inverted()
        H, Km, A = (out[P + s + x].translation for x in ('UpLeg', 'Leg', 'Foot'))
        ctx._cache[key] = (Rb @ (A - H), Rb @ (Km - H))
    return ctx._cache[key]


def land_pts(ctx, s):
    key = ('landp', s)
    if key not in ctx._cache:
        tl = ctx.paths['leg'][s]['land']
        hips, hrot, J, v, c = ss2_body(ctx, tl)
        Rb = R(Z, c.yaw).inverted()
        H = hips + v[s]
        if s == 'Left':
            Kp, shin = knee_mode(ctx, H, c, 0.0)
            A = Kp + shin * ctx.l2
        else:
            o = tail_pose(ctx, tl)
            Kp, A = o[P + s + 'Leg'].translation, o[P + s + 'Foot'].translation
            H = o[P + s + 'UpLeg'].translation
        ctx._cache[key] = (Rb @ (A - H), Rb @ (Kp - H))
    return ctx._cache[key]


def knee_mode(ctx, H, c, kz):
    """Left knee on its spot (the pelvis height is solved for it), shin back and up 22 deg like the crawl's."""
    Kp = H + ((LK_PLANT - Vector((0, 0, kz))) - H).normalized() * ctx.l1
    phi = math.radians(22.0)
    yaw_rel = (c.yaw - CRAWL_YAW) * (1 - c.wT)
    shin = R(Z, yaw_rel) @ Vector((0.0, math.cos(phi), math.sin(phi)))
    return Kp, shin


def ss2_pose_raw(ctx, t, legs_only=False):
    b, B = ctx.body, ctx.B
    pa = ctx.paths
    hipsS, hrotS, JS, LS = ctx.pS
    hipsT, hrotT, JT, LT = ctx.tail(max(t, SS2_T - TAIL - 0.2))
    l1, l2 = ctx.l1, ctx.l2
    cz = {'R': 0.0, 'L': 0.0, 'K': 0.0}                 # contact solves: palm / knee pressed down by these
    raise_k = {'Left': 0.0, 'Right': 0.0}
    raise_a = {'Left': 0.0, 'Right': 0.0}
    raise_w = {'Left': 0.0, 'Right': 0.0}
    seat_dz = 0.0
    c = ctx.ch(t)
    for it in range(24):
        hips, hrot, J, v, c = ss2_body(ctx, t, cz['K'] * c.kcK)
        sh = getattr(ctx, '_sh', {})
        Rb = R(Z, c.yaw)
        wT = c.wT
        hp = hips + Vector((0, 0, seat_dz))
        legs, foot_q, footw = {}, {}, {}
        swing_legs = {}
        for s in SIDES:
            L = pa['leg'][s]
            H = hp + v[s]
            sitL = LS[('leg', s)]
            u = (t - L['lift']) / (L['land'] - L['lift'])
            fq, rel, Km, hs = None, None, None, None
            if u <= 0 or legs_only:
                A_, bend = sitL['pos'], sitL['bend']
                fq = sitL['end'].to_quaternion()
            elif u >= 1 and s == 'Left':
                Km, shin = knee_mode(ctx, H, c, cz['K'] * c.kcK)
                A_ = Km + shin * l2
                rel = ctx.Lk
                hs = None
            else:
                uu = min(u, 1.0)
                w = smooth(uu)
                d0, s0, rel0 = lift_state(ctx, s)
                d1, s1, rel1 = land_state(ctx, s)
                # keyframed swing in the pelvis-yaw frame (sagittal plane plus a little splay): thigh pitch th (deg,
                # 0 = forward, +90 = up) and knee flexion fl (shin pitch = th - fl). The keys keep the ankle well off
                # the floor: the knees jerk up while the heels tuck, the folded leg drops, then opens into the kneel.
                # The exact lift-off / landing directions are blended in over the first / last 0.06 s.
                A0, K0 = lift_pts(ctx, s)
                A1, K1 = land_pts(ctx, s)
                d0, d1 = K0.normalized(), K1.normalized()
                s0, s1 = (A0 - K0).normalized(), (A1 - K1).normalized()
                kk = leg_keys(ctx, s)
                th, fl, sp, ab = kk['th'](t), kk['fl'](t), kk['sp'](t), kk['ab'](t)
                # splay (about the vertical) and abduction (about the forward axis): the knee passes under the hip
                # round the outside, high enough to clear the floor
                Rs = R(Y, -SGN[s] * ab) @ R(Z, SGN[s] * sp)
                dk = Rs @ Vector((0.0, -math.cos(math.radians(th)), math.sin(math.radians(th))))
                sk = Rs @ Vector((0.0, -math.cos(math.radians(th - fl)), math.sin(math.radians(th - fl))))
                e0 = 1 - smooth((t - L['lift']) / 0.06)
                e1 = smooth((t - (L['land'] - 0.10)) / 0.10)
                dthb = vslerp(vslerp(dk, d0, e0), d1, e1)
                dshb = vslerp(vslerp(sk, s0, e0), s1, e1)
                up = Vector((0, 0, 0.08 * bump(uu, 0.0, 0.16, 0.48)))           # lift-off: the leg rises first
                Km = H + (Rb @ dthb * l1 + up + Vector((0, 0, raise_k[s]))).normalized() * l1
                zc = KNEE_R + 0.012
                if Km.z < zc and H.z - zc < l1:
                    r = math.sqrt(max(l1 * l1 - (H.z - zc) ** 2, 0.0))
                    dxy = Vector((Km.x - H.x, Km.y - H.y, 0.0))
                    if dxy.length > 1e-6:
                        Km = Vector((H.x, H.y, zc)) + dxy.normalized() * r
                dth = (Km - H).normalized()
                dsh = (Rb @ dshb + Vector((0, 0, raise_a[s]))).normalized()
                A_ = Km + dsh * l2
                hs = dsh.cross(dth)
                hs = hs.normalized() if hs.length > 1e-6 else None
                footw[s] = smooth(uu / 0.20)              # the foot leaves level, then turns with the shin
                if u < 1:
                    swing_legs[s] = u
                # ankle: neutral -> flexed (toes up) while the shin hangs down -> pointed once it has turned back
                relD = dorsi_rel(ctx, s)
                rel = qslerp(qslerp(rel0, relD, kk['df'](t)), rel1, kk['pt'](t))
            if Km is not None:
                ln = (A_ - H).normalized()
                bend = (Km - H) - ln * (Km - H).dot(ln)
            wl = wT if not (s == 'Left' and u >= 1) else c.wKe
            if wl > 0:
                lt = LT[('leg', s)]
                A_ = A_.lerp(lt['pos'], wl)
                bend = Vector(bend).normalized() * (1 - wl) + lt['bend'] * wl
                hs = None
            Fm = (fq if fq is not None else sitL['end'].to_quaternion()).to_matrix().to_4x4()
            Fm.translation = A_
            if hs is not None:
                ln = (A_ - H).normalized()
                hs = hs - ln * hs.dot(ln)
                hinge = hs.normalized() if hs.length > 1e-6 else hinge_of(H, A_, bend)
            else:
                hinge = hinge_of(H, A_, bend)
            legs[s] = (Fm, hinge)
            foot_q[s] = rel
        arms = {}
        if not legs_only:
            Rp = R(Z, c.yaw - CRAWL_YAW)
            for s, key in (('Right', 'R'), ('Left', 'L')):
                W, q, pole = pa['w' + key](t), pa['q' + key](t), Rp @ pa['p' + key](t).normalized()
                gw = pa['grip' + key](t)
                if gw > 0:
                    W = W + (sh[s] - ctx.sh0[s]) * gw
                wa = wT if s == 'Right' else 0.0      # the left hand steps onto its own frame-1 spot (lhl)
                if wa > 0:
                    at = LT[('arm', s)]
                    W = W.lerp(at['pos'], wa)
                    q = qslerp(q, at['hq'], wa)
                    pole = pole * (1 - wa) + at['bend'] * wa
                if s == 'Left' and c.lhl > 0:
                    ac = ctx.pC1[3][('arm', 'Left')]
                    W = W.lerp(ac['pos'], c.lhl)
                    q = qslerp(q, ac['hq'], c.lhl)
                    pole = pole * (1 - c.lhl) + ac['bend'] * c.lhl
                W = W - Vector((0, 0, cz[key] * getattr(c, 'kc' + key))) + Vector((0, 0, raise_w[s]))
                arms[s] = (W, q, pole)
        curl = {s: (pa['curl'][s][0](t), pa['curl'][s][1](t)) for s in SIDES}
        tw = c.tw

        def post(out):
            for s, (t0r, t1r) in (('Right', (0.27, 0.475)), ('Left', (0.42, 0.585))):
                # the wrist turns evenly over the whole reach (the grip -> palm-down turn is ~160 deg)
                kr = 1.0 - clamp((t - t0r) / (t1r - t0r)) if t0r <= t <= t1r else 0.0
                if kr > 0 and not legs_only:
                    fa = out[P + s + 'ForeArm'].to_3x3()
                    relax = (fa @ ctx.grip_rel[s].to_matrix()).to_quaternion()
                    q = qslerp(out[P + s + 'Hand'].to_quaternion(), relax, kr)
                    m = q.to_matrix().to_4x4()
                    m.translation = out[P + s + 'Hand'].translation
                    delta = m @ out[P + s + 'Hand'].inverted()
                    for nn in B.subtree(s + 'Hand'):
                        out[nn] = delta @ out[nn]
            for s in SIDES:
                if tw > 1e-9:
                    for n in ('UpLeg', 'Leg'):
                        m = out[P + s + n]
                        r = (m.to_3x3() @ QI().slerp(ctx.twist[s][n], tw).to_matrix()).to_4x4()
                        r.translation = m.translation
                        out[P + s + n] = r
                rel = foot_q[s]
                if rel is None and wT <= 0:
                    continue
                if rel is not None:
                    q = (out[P + s + 'Leg'].to_3x3() @ rel.to_matrix()).to_quaternion()
                    if s in footw:
                        q = qslerp(LS[('leg', s)]['end'].to_quaternion(), q, footw[s])
                else:
                    q = out[P + s + 'Foot'].to_quaternion()
                if wT > 0:
                    q = qslerp(q, LT[('leg', s)]['end'].to_quaternion(), wT)
                m = q.to_matrix().to_4x4()
                m.translation = out[P + s + 'Foot'].translation
                delta = m @ out[P + s + 'Foot'].inverted()
                for nn in B.subtree(s + 'Foot'):
                    out[nn] = delta @ out[nn]
        out, info = b.pose(hp, hrot, J, legs=legs, arms=arms, curl=curl, post=post)
        if legs_only:
            return out, info
        # skinned-mesh solves: planted palms / knee pressed onto the floor; swinging legs and the seat kept above it
        pts = B.mesh_points(out)
        moved = False
        for key, side, k in (('R', 'Right', c.kcR), ('L', 'Left', c.kcL)):
            if k < 1 and not (side == 'Left' and c.lhl > 0):
                # a moving hand / forearm never brushes the floor (it would skid): lift the wrist target
                lowa = min(float(pts[ctx.vsets['hand_' + side], 2].min()), float(pts[ctx.vsets['fore_' + side], 2].min()))
                if lowa < 0.0025 and (k <= 0 or lowa < -0.0003):
                    raise_w[side] += (0.0030 - lowa) * (1 - k)
                    moved = True
            if k > 0:
                low = float(pts[ctx.vsets['hand_' + side], 2].min())
                lowf = float(pts[ctx.vsets['fore_' + side], 2].min())
                d = min(low - 0.0004, lowf - 0.0012)      # palm down; the sleeve cuff may graze but not dig
                if abs(d) > 0.0002:
                    cz[key] += d / max(k, 0.5)
                    moved = True
        if c.kcK > 0 and t >= pa['leg']['Left']['land']:
            low = float(pts[ctx.vsets['leg_Left'], 2].min())
            if abs(low - 0.0004) > 0.0002:
                cz['K'] += (low - 0.0004) / max(c.kcK, 0.5)
                moved = True
        for s in SIDES:
            L = pa['leg'][s]
            u = (t - L['lift']) / (L['land'] - L['lift'])
            if 0 < u < 1:
                lowf = float(pts[ctx.vsets['foot_' + s], 2].min())
                lowk = float(pts[ctx.vsets['leg_' + s], 2].min())
                low = min(lowf, lowk)
                if low < 0.0120:               # a swinging leg never touches (no drag / slide), with margin for
                    if lowk < 0.0120:          # the in-between samples of the linear keys
                        raise_k[s] += 1.5 * (0.0125 - lowk)
                    if lowf < 0.0120:
                        raise_a[s] += 3.0 * (0.0125 - lowf)
                    moved = True
        low = float(pts[ctx.vsets['seat'], 2].min()) if t < 0.56 else 1.0
        if low < -0.0003:
            seat_dz += -low + 0.0003
            moved = True
        if not moved:
            break
    info['hips'] = tuple(out[P + 'Hips'].translation)
    info['over'] = {s: max(0.0, (out[P + s + 'Arm'].translation - arms[s][0]).length - ctx.Larm) for s in SIDES}
    info['cz'] = dict(cz)
    info['iters'] = it
    info['raise'] = {k: round(v, 4) for k, v in list(raise_k.items()) + [('w' + k, v) for k, v in raise_w.items()] if v > 0.004}
    return out, info


def limit_rotation_steps(B, frames, max_deg=21.0, pad=3, iters=400, keep=(), frozen=None):
    """Copied from the Idle_Knock_v03 cargo package's acting_core (its newer version; not in this worktree's
    acting_core). Safety net: where a bone's parent-relative rotation changes by more than max_deg between
    neighbouring samples, smooth that bone's local rotation sequence inside a window (+-pad samples) with an
    iterative 3-tap quaternion filter until every step is under the limit. Frames listed in `keep` are never
    changed, nor the samples in frozen[bone] (here: limbs planted on the floor). Positions are recomposed by FK from the unchanged local offsets. Returns {bone: samples changed}."""
    keys = sorted(frames)
    n = len(keys)
    keep = set(keep)
    loc = {b: [] for b in B.order}
    for f in keys:
        pose = frames[f]
        for b in B.order:
            p = B.parent[b]
            loc[b].append(pose[b].copy() if p is None else pose[p].inverted() @ pose[b])
    changed = {}
    lim = math.radians(max_deg)
    for b in B.order:
        q = [m.to_quaternion() for m in loc[b]]
        for i in range(1, n):
            if q[i - 1].dot(q[i]) < 0:
                q[i].negate()

        def ang(i):
            return 2 * math.acos(min(1.0, abs(q[i - 1].dot(q[i]))))
        bad = [i for i in range(1, n) if ang(i) > lim]
        if not bad:
            continue
        mask = [False] * n
        fz = (frozen or {}).get(b, ())
        for i in bad:
            for j in range(max(1, i - pad - 1), min(n - 1, i + pad + 1)):
                if keys[j] not in keep and keys[j] not in fz:
                    mask[j] = True
        idx = [j for j in range(n) if mask[j]]
        for _ in range(iters):
            new = list(q)
            for j in idx:
                mid = q[j - 1].slerp(q[j + 1], 0.5)
                new[j] = q[j].slerp(mid, 0.6)
            q = new
            if max(ang(i) for i in range(1, n)) <= lim:
                break
        for j in idx:
            m = q[j].to_matrix().to_4x4()
            m.translation = loc[b][j].translation
            loc[b][j] = m
        changed[b] = len(idx)
    if changed:
        for k, f in enumerate(keys):
            out = {}
            for b in B.order:
                p = B.parent[b]
                out[b] = loc[b][k].copy() if p is None else out[p] @ loc[b][k]
            frames[f] = out
    return changed


def ss2_pose(ctx, t):
    """The registered pose: every sample is authored once (ss2_pose_raw), then the few in-air limb samples that
    turn faster than 22 deg per half frame (the slap's wrist, the re-plant) are smoothed locally; the exact
    contract ends are kept."""
    if ctx._final is None:
        n2 = int(round(SS2_T * 2 * E.FPS))
        frames, infos = {}, {}
        for i in range(n2 + 1):
            frames[i], infos[i] = ss2_pose_raw(ctx, i / (2 * E.FPS))
        # limbs touching the floor are never smoothed (their contact must not move)
        frozen = {}
        for i in range(n2 + 1):
            ti = i / (2 * E.FPS)
            c = ctx.ch(ti)
            planted = []
            if c.kcR > 0.0:
                planted.append('RightArm')
            if c.kcL > 0.0 or c.lhl > 0.0:
                planted.append('LeftArm')
            for side in SIDES:
                L = ctx.paths['leg'][side]
                if ti <= L['lift'] or (side == 'Left' and ti >= L['land']):
                    planted.append(side + 'UpLeg')
            for root in planted:
                for bn in ctx.B.subtree(root):
                    frozen.setdefault(bn, set()).add(i)
        changed = limit_rotation_steps(ctx.B, frames, max_deg=22.0, pad=2, keep=(0, n2), frozen=frozen)
        ctx._final = (frames, infos, changed)
    frames, infos, changed = ctx._final
    i = int(round(t * 2 * E.FPS))
    info = dict(infos[i])
    info['t'] = t
    info['smoothed'] = {k[len(P):]: v for k, v in changed.items()} if i == 0 else None
    return frames[i], info


def ss2_canonical(ctx, frames, N):
    return {1.0: ctx.sit_values, float(N + 1): ctx.B.values_from_pose(ctx.C1)}


def ss2_contact(ctx, frames, info):
    """Floor contact at every sample (the mesh's lowest point and its body part) for the review."""
    import numpy as np
    B = ctx.B
    names = getattr(ctx, '_vnames', None)
    if names is None:
        nm = []
        for o in B.meshes:
            vg = [g.name for g in o.vertex_groups]
            for vx in o.data.vertices:
                g = max(vx.groups, key=lambda g: g.weight, default=None)
                nm.append(vg[g.group][len(P):] if g else '-')
        ctx._vnames = names = np.array(nm)
    worst_gap, at, who = -1.0, None, None
    parts = []
    for f in sorted(frames):
        pts = B.mesh_points(frames[f])
        i = int(pts[:, 2].argmin())
        z = float(pts[i, 2])
        parts.append((f, str(names[i]), round(z * 1000, 2)))
        if z > worst_gap:
            worst_gap, at, who = z, f, str(names[i])
    over = [(i['t'], {s: round(v * 1000, 1) for s, v in i['over'].items() if v > 0.0005}) for i in info if i.get('over')]
    lows = [(round(f, 1), str(names[int(B.mesh_points(frames[f])[:, 2].argmin())]), round(float(B.mesh_points(frames[f])[:, 2].min()) * 1000, 2))
            for f in sorted(frames)]
    pen = [x for x in lows if x[2] < -0.5]
    its = [(round(i['t'], 3), i['iters']) for i in info if i.get('iters', 0) >= 10]
    its += [('raise', round(i['t'], 3), i['raise']) for i in info if i.get('raise')]
    sm = next((i.get('smoothed') for i in info if i.get('smoothed')), {})
    its.append(('smoothed', sm))
    return {'max_lowest_point_mm': worst_gap * 1000, 'max_lowest_at': [at, who], 'lowest_part_every_2nd_sample': parts[::2],
            'per_arm_overreach_mm': [o for o in over if o[1]], 'per_penetration_mm': pen, 'per_solver_iters': its}


def review_box(col, name, lo, hi, rgb):
    """E.box with a node colour as well (EEVEE ignores the viewport colour)."""
    o = E.box(col, name, lo, hi, rgb)
    m = o.data.materials[0]
    try:
        m.use_nodes = True
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = E.C.srgb(rgb)
        bsdf.inputs['Roughness'].default_value = 0.8
    except Exception:
        pass
    return o


def ss2_stage(col):
    """Review stage only (not exported): the cargo side wall x = -0.65 and a 1.2 m roof line behind him."""
    review_box(col, 'Cargo_Wall_Review', (-0.72, -1.6, 0.0), (-0.65, 1.6, 1.25), (78, 92, 106))
    review_box(col, 'Roof_1p2_Review', (-0.65, 0.95, 1.192), (0.75, 0.97, 1.208), (215, 80, 25))
    return []


CLIPS['Escape_Scramble_Start'] = {
    'T': SS2_T, 'loop': False, 'stage': 'cargo', 'setup': SS2Ctx, 'pose': ss2_pose, 'canonical': ss2_canonical,
    'views': CE.CARGO_VIEWS, 'height_ref': lambda t: 0.0, 'stage_objects': ss2_stage,
    'extra_metrics': with_checks(ss2_contact),
    'start': 'Cargo sit contract = Cargo_Sit_Idle_v04 frame 1, exact raw values of Cargo_Sit_Contract_v04.json',
    'end': 'Escape_Scramble frame 1 (exact)',
    'events': {},
    'beats': ['0.00 = the cargo sit contract (knee hug, hood on the wall x = -0.65)',
              '0.09-0.15 SNAP: the head whips ~55 deg to his right at the open doors (-Y), shoulders jolt up',
              '0.15-0.32 frozen stare with a tremble, hands still on the shins (they slide up a little with the shrug)',
              '0.27-0.50 the right hand lets go, swings out and slaps the floor on the doors side (palm planted 0.50-0.64); '
              'the trunk bows forward over it, the butt rocks forward on the sit bones and lifts (0.42-0.53)',
              '0.42-0.61 the left hand lets go, reaches across and plants under the left shoulder (0.61-0.73)',
              '0.49-0.82 the legs: knees jerk up, heels kick up behind, the folded legs drop and swing round the outside; '
              'the left knee lands on its crawl spot at 0.82 s, the right leg swings into the right-leg step of the crawl',
              '0.47-0.85 the pelvis lifts and swivels ~94 deg to his right round the right palm; the head stays on the doors',
              '0.65-0.73 the right palm hops onto its crawl spot; 0.74-0.97 the left hand steps forward and lands on its '
              'crawl frame-1 spot (0.967 s)',
              '0.90-1.00 the last 0.1 s is Escape_Scramble itself (-0.1..0 s) with the van floor held still: the body already '
              'moves toward the doors at 1.2 m/s, so the hand-off to the crawl (and the moving capsule) is seamless',
              'something is on the floor at every 120 Hz sample: butt + feet, right palm, left palm, left knee, left palm',
              '1.00 = Escape_Scramble frame 1 (exact)'],
}


# ============================================================================= Hit_React_Front v02 (belly punch: "OOF")
# v01: the fold and the belly hug were small and the recovery fast. v02: a hard fold (pelvis bows and the butt
# shoots back, knees buckle, the chest goes well past 45 deg, the big head whips back then down after the chest),
# the arms fly out then clutch the belly, a held fold with three wheezes, then a slow groggy recovery.
HF2_T = 1.1


def hf2_chan():
    T = HF2_T
    return Chan(
        # butt back (+Y), knee bend (drop), pelvis bow (+ forward), spine fold (+ forward)
        hy=K((0, 0), (0.05, 0.075, ('lin', 'auto')), (0.12, 0.105), (0.50, 0.095), (0.95, 0.025), (1.04, -0.004), (T, 0)),
        drop=K((0, 0), (0.06, 0.055), (0.14, 0.115), (0.30, 0.10), (0.50, 0.105), (0.95, 0.03), (1.04, 0.004), (T, 0)),
        hp=K((0, 0), (0.06, 12), (0.14, 24), (0.50, 22), (0.95, 5), (1.04, -1.0), (T, 0)),
        sp=K((0, 0), (0.045, 22, ('lin', 'auto')), (0.12, 46), (0.20, 41), (0.50, 40), (0.95, 6), (1.03, -2), (T, 0)),
        # the head lags: tips back on the impact, then whips down past the chest and bobs; hangs, comes up last
        hd=K((0, 0), (0.05, -14), (0.15, 54), (0.24, 38), (0.50, 44), (0.80, 24), (1.00, -4), (T, 0)),
        # arms: fly forward/out on the impact, then clutch the belly, let go slowly
        fwd=K((0, 0), (0.06, 44), (0.14, 22), (0.55, 20), (0.95, 3), (T, 0)),
        out=K((0, 0), (0.06, 16), (0.14, -4), (0.55, -4), (0.95, 0), (T, 0)),
        elb=K((0, 0), (0.06, 25), (0.15, 112), (0.55, 108), (0.98, 10), (T, 0)),
        sw=K((0, 0), (0.05, 0), (0.15, 42), (0.55, 40), (0.98, 4), (T, 0)),
        curl=K((0, 0), (0.05, -0.25), (0.15, 0.65), (0.55, 0.6), (0.98, 0.05), (T, 0)),
        sh=K((0, 0), (0.04, 14), (0.16, 10), (0.55, 9), (0.95, -3), (T, 0)),
        wh=K((0, 0), (0.18, 0), (0.24, 1), (0.48, 1), (0.56, 0), (T, 0)),     # wheeze heaves
        sway=K((0, 0), (0.50, 0), (0.62, 1), (0.92, 0.7), (1.04, 0), (T, 0)),  # groggy sway in the recovery
    )


def hf2_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    # three wheezes: quick chest heaves with a shoulder hitch (and the head bobbing after them)
    whz = c.wh * max(0.0, math.sin(2 * math.pi * 4.5 * (t - 0.24))) ** 2
    wob = CE.wob(t, 0.10, 3.2, 4.0, 3.0) * (1 - win(t, 0.55, 0.75))
    gr = c.sway * math.sin(2 * math.pi * 1.6 * (t - 0.55))
    spine(J, pitch=c.sp - 10 * whz, roll=wob + 4.5 * gr, yaw=-3 * gr, w=(0.22, 0.38, 0.40))
    head(J, pitch=c.hd - 0.25 * c.sp + 12 * whz, roll=-1.6 * wob - 7 * gr, yaw=5 * gr, neck=0.55)
    for s in SIDES:
        arm(J, s, fwd=c.fwd, out=c.out, swing=c.sw, elbow=c.elb, sh_up=c.sh + 9 * whz,
            twist=-22 * c.elb / 110, wrist=12 * max(c.curl, 0.0))
    hrot = R(X, c.hp) @ R(Y, 0.5 * wob + 2 * gr)
    cur = (c.curl, 0.5 * abs(c.curl))
    return stand(ctx.body, 0.0, c.hy, hrot, J, drop=c.drop, curl={'Left': cur, 'Right': cur})


CLIPS['Hit_React_Front'] = CE._spec(HF2_T, hf2_chan, hf2_pose, [
    '0.00-0.05 belly punch: the pelvis bows and the butt shoots back 10 cm, knees buckle 11 cm, the chest snaps forward ("OOF"); arms fly out',
    '0.05-0.15 the big head tips back on the impact, then whips down past the chest (lag + overshoot); hands clutch the belly',
    '0.15-0.50 held fold, chest ~70 deg down: two wheezes (0.29, 0.40 s: chest heaves, shoulders hitch, head bobs)',
    '0.50-0.98 slow groggy recovery: straightens with a woozy sway, the head hangs and comes up last, hands let go',
    '0.98-1.10 settles into Idle frame 1'],
    extra_metrics=with_checks())


# ============================================================================= Stagger v02 (dazed, wobblier)
# v01: reads, but steps and sway were tame. v02: bigger drunken lurches where the upper body leads and the feet
# catch up, knees buckling, a dizzy head circle, arms flailing for balance, a near-fall backward that a late step
# saves (windmill), then shuffling back onto the exact Idle foot spots.
ST2_T = 1.6


def st2_chan():
    T = ST2_T
    return Chan(
        # pelvis wanders ahead of the feet (it leads; the steps catch it) and comes home
        hx=K((0, 0), (0.14, -0.06), (0.34, -0.12), (0.52, 0.02), (0.70, 0.07), (0.86, 0.05), (1.04, 0.08), (1.22, 0.02), (1.42, 0.004), (T, 0)),
        hy=K((0, 0), (0.16, 0.0), (0.36, -0.06), (0.56, -0.15), (0.72, -0.20), (0.88, -0.07), (1.02, 0.02), (1.22, 0.01), (1.42, 0.0), (T, 0)),
        drop=K((0, 0), (0.12, 0.04), (0.30, 0.09), (0.44, 0.05), (0.62, 0.11), (0.78, 0.06), (0.94, 0.12), (1.08, 0.07), (1.30, 0.03), (1.48, 0.004), (T, 0)),
        # upper-body lean (deg): + roll tips to his left, + pitch forward
        lean_r=K((0, 0), (0.10, -6), (0.28, -17), (0.44, -8), (0.60, 13), (0.76, 9), (0.92, 15), (1.06, 4), (1.24, -3), (1.44, 0.5), (T, 0)),
        lean_f=K((0, 0), (0.14, 5), (0.34, 2), (0.56, 20), (0.70, 14), (0.86, -14), (0.98, -9), (1.14, 4), (1.34, -1), (T, 0)),
        dizzy=K((0, 0), (0.08, 1), (1.30, 1), (1.52, 0), (T, 0)),
        arms=K((0, 0), (0.18, 0.5), (0.50, 1), (1.12, 1), (1.40, 0.15), (T, 0)),
        mill=K((0, 0), (0.78, 0), (0.86, 1), (1.04, 1), (1.14, 0), (T, 0)),
        soft=K((0, 0), (0.10, 1), (1.42, 1), (T, 0)),
    )


def st2_feet(body, t):
    """Steps (the feet catch the pelvis): right out to his right, left crosses over in front, right lurches
    forward, left saves the backward near-fall out to his left, then both shuffle home onto the Idle spots."""
    F0 = body.F0

    def at(s, dx, dy, yaw=0.0):
        return Matrix.Translation((dx, dy, 0.0)) @ E.rot_about(body.pivot0[s]['ankle'], R(Z, yaw)) @ F0[s]
    R1 = at('Right', -0.17, -0.02, -16)
    L1 = at('Left', -0.06, -0.16, 12)
    R2 = at('Right', 0.00, -0.32, -6)
    L2 = at('Left', 0.10, -0.06, 14)
    R3 = at('Right', -0.02, -0.08, -4)
    steps = {'Right': [(0.16, 0.34, F0['Right'], R1, 0.09), (0.56, 0.72, R1, R2, 0.10), (1.06, 1.22, R2, R3, 0.06),
                       (1.30, 1.44, R3, F0['Right'], 0.05)],
             'Left': [(0.36, 0.54, F0['Left'], L1, 0.09), (0.82, 0.98, L1, L2, 0.08), (1.20, 1.38, L2, F0['Left'], 0.06)]}
    feet = {}
    for s in SIDES:
        M = F0[s]
        for t0, t1, a, b, lift in steps[s]:
            if t >= t0:
                M, moving = step_arc(a, b, t, t0, t1, lift=lift, pitch=0)
        feet[s] = M
    return feet


def st2_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    dz = c.dizzy
    ph = 2 * math.pi * 1.5 * t                     # dizzy circle (1.5 Hz)
    spine(J, pitch=c.lean_f + 4 * dz * math.sin(ph), roll=c.lean_r + 6 * dz * math.cos(ph), yaw=5 * dz * math.sin(ph + 0.6))
    # the head circles (lagging the body), big and loose
    head(J, pitch=14 * dz * math.sin(ph + 1.0) - 0.35 * c.lean_f, roll=-0.6 * c.lean_r + 20 * dz * math.cos(ph + 1.0),
         yaw=12 * dz * math.sin(2 * ph + 0.3), neck=0.5)
    m = c.mill
    for s in SIDES:
        sg = SGN[s]
        # arms out for balance, flapping against the lean; a windmill on the backward near-fall
        out = c.arms * (30 + 14 * sg * math.sin(math.radians(c.lean_r) * 5)) + 10 * dz * math.sin(ph * 1.3 + sg)
        fwd = 22 * c.arms * math.sin(ph * 0.8 + sg) + m * 70 * math.sin(2 * math.pi * 2.6 * (t - 0.80) + (0 if s == 'Left' else math.pi))
        arm(J, s, fwd=fwd, out=out, elbow=22 * c.arms + 28 * m, wrist=12 * dz * math.sin(ph * 1.7 + sg), sh_up=6 * m)
    feet = st2_feet(ctx.body, t)
    hrot = R(Y, -0.45 * c.lean_r) @ R(X, 0.3 * c.lean_f) @ R(Z, 7 * dz * math.sin(ph * 0.7))
    return stand(ctx.body, c.hx, c.hy, hrot, J, drop=c.drop, feet=feet, free=(), support=1 - 0.02 * c.soft ** 2,
                 curl={'Left': (0.12 * c.arms - 0.2 * m, 0.1 * c.arms), 'Right': (0.12 * c.arms - 0.2 * m, 0.1 * c.arms)})


CLIPS['Stagger'] = CE._spec(ST2_T, st2_chan, st2_pose, [
    '0.00-0.16 dizzy sway starts: the upper body tips to his right ahead of the feet, arms drift out, head starts circling',
    '0.16-0.34 the right foot stumbles out to catch it (knees buckle 9 cm)',
    '0.36-0.54 lurch back to his left: the left foot crosses over in front',
    '0.50-0.72 drunken forward lurch, chest 20 deg down; the right foot catches it 32 cm ahead',
    '0.80-1.06 near-fall backward: arms windmill, knees buckle 12 cm, the left foot saves it out to his left',
    '1.06-1.44 shuffles back: right, left, right onto their exact Idle spots; the dizzy head circle fades',
    '1.44-1.60 settles into Idle frame 1'],
    extra_metrics=with_checks())
