"""Sausage Buddy Walk v04 - motion design (maths only; no file I/O, no keying).

Frame: the character faces -Y, left = +X, Z up, metres. The cycle is in place: the ground
moves toward +Y at SPEED. Cycle phase t in [0, 1): t = 0 is the LEFT heel strike and
t = 0.5 the RIGHT heel strike. Frame f (1-based, 30 fps) has phase (f - 1) / N.

How it is built (animation craft, not plain sines):
- Every body channel is a periodic key curve (cubic Hermite, flat tangents on extremes, like
  auto-clamped keys in a graph editor), keyed on the classic contact / down / passing / up poses.
- Feet: heel strike with the toe up -> quick forefoot slap -> flat -> heel peel with the shoe
  bending at the ball (ToeBase stays planted) -> roll over the toe tip -> lift-off. Each contact
  phase is a pure rotation about a ground point that travels with the ground. Pivots are the
  convex hull of the real shoe-sole vertices, so the planted sole neither slides nor sinks.
- Swing: cubic Hermite from the lift-off state to the strike state with matching velocities
  (C1 at both ends), plus a knee-lift bump and a toe-down dangle early in the swing.
- Legs: analytic two-bone IK; thigh and shin share one hinge axis, so the knee never twists.
- Overlap: chest lags the pelvis, the head lags the chest (nod and bobble); upper arm,
  forearm and hand each lag the previous segment (loose, relaxed wrists).
"""
import math
from mathutils import Vector, Matrix, Quaternion

P = 'mixamorig:'

# ----------------------------------------------------------------------------- timing
FPS = 30
N = 20                          # frames per cycle; key frame N + 1 repeats frame 1
SPEED = 1.5                     # nominal ground speed, m/s (Unity plays at speed / 1.5)
CYCLE_S = N / FPS               # 0.6667 s
TRAVEL = SPEED * CYCLE_S        # ground travel per cycle = stride, m (two 0.5 m steps)


def frames(n):
    """Convert a delay in frames to cycle phase."""
    return n / N


# ----------------------------------------------------------------------------- feet
STRIKE_TOE_UP = 24.0            # deg, toe up at heel strike
STRIKE_RATE = 0.35              # 0 = foot stops turning at contact, 1 = constant rate into the slap
T_FLAT = 0.07                   # phase: forefoot slap ends the heel roll (1.4 frames)
T_HEEL_OFF = 0.27               # heel starts to peel
T_TIP = 0.49                    # toe starts to roll over its tip
T_OFF = 0.585                   # toe leaves the ground (double support 0.085 = 1.7 frames)
BALL_END = 42.0                 # shoe bend at the ball at lift-off, deg
BALL_POWER = 1.7                # heel peel accelerates
TIP_END = 13.0                  # roll over the toe tip before lift-off, deg
TRACK = 0.092                   # ankle |x| on the ground
TOE_OUT = 7.0                   # deg, feet point slightly outward
KNEE_OUT = 4.0                  # deg, extra knee splay beyond the toe-out
Y0 = None                       # flat-foot ankle offset at strike; None = balance leg reach
SWING_LIFT = 0.020              # m, ankle lift bump in swing (on top of the Hermite path)
SWING_LIFT_AB = (2.4, 2.0)      # bump exponents: peak at a / (a + b) of the swing
SWING_TOE = 4.0                 # deg, extra toe-down dangle early in the swing
SWING_TOE_AB = (2.0, 4.0)
TOE_SPRING = 1.0                # fraction of the toe-bend rate carried into the swing (1 = C1 lift-off)
SWING_INWARD = 0.012            # m, swing foot passes slightly toward the midline
SWING_CARRY_Z = 0.4             # v04: fraction of the toe-roll's upward ankle speed carried into the swing
SWING_CARRY_PITCH = 0.4         # v04: fraction of the toe-roll's foot pitch rate carried into the swing
                                # (1.0 = v03: foot whipped on to 77 deg and the ankle rose 14 cm -> marching)
LIFT_VZ = 0.30                  # m/s, toe pops off the floor at lift-off (v04: removes the 1.3 mm toe skim)
LAND_VZ = -0.30                 # m/s, heel plants with a small downward accent at the strike

# ----------------------------------------------------------------------------- pelvis
# Hips height per step (u = 0 contact, ~0.17 down, ~0.5 passing, ~0.75 up), normalised -1..1.
BOB_KEYS = [(0.00, 0.35), (0.20, -1.00), (0.46, -0.05), (0.78, 1.00)]
BOB_CENTER = -0.042             # m, offset of the Hips from rest (legs stay bent)
BOB_HALF = 0.033                # m, half of the peak-to-peak bounce
SWAY = 0.022                    # m, hips over the support foot
SWAY_KEYS = [(0.03, 0.0), (0.28, 1.0)]          # odd: second half mirrored
PELVIS_YAW = 6.0                # deg, swing-side hip travels forward with the leg
YAW_KEYS = [(0.00, -1.0), (0.25, 0.0)]
PELVIS_ROLL = 4.5               # deg, swing-side hip drops in early single support
ROLL_KEYS = [(0.04, 0.0), (0.19, -1.0)]
PELVIS_TILT = 2.0               # deg, forward tilt of the pelvis
PELVIS_TILT_BOB = 1.5           # deg, extra forward tilt on the down

# ----------------------------------------------------------------------------- torso and head
CHEST_LEAN = 1.0                # deg, chest world pitch (+ forward)
CHEST_SQUASH = 2.6              # deg, sausage body folds forward after the down
CHEST_LAG = frames(1.2)
CHEST_YAW = 5.5                 # deg, shoulders counter-rotate against the pelvis
CHEST_YAW_LAG = frames(0.6)
CHEST_ROLL = 3.2                # deg, shoulders tilt against the hips
CHEST_ROLL_LAG = frames(1.2)
HEAD_PITCH = -4.0               # deg, head world pitch (- = chin up, happy-go-lucky)
HEAD_NOD = 4.0                  # deg, nod after the down
HEAD_NOD_LAG = frames(2.6)
HEAD_ROLL = 0.45                # fraction of the chest tilt the head keeps, lagged
HEAD_ROLL_LAG = frames(2.0)
HEAD_YAW = 0.25                 # fraction of the chest yaw the head keeps (eyes look ahead)

# ----------------------------------------------------------------------------- arms
ARM_DOWN = 75.0                 # deg from the T-pose
ARM_SWING = 25.0                # deg, half range of the upper-arm swing
ARM_BIAS = -3.0                 # deg (- = forward)
ARM_KEYS = [(0.05, 1.0), (0.30, 0.0)]           # odd: left arm back after the left strike
ARM_CROSS = 10.0                # deg, swing plane turned so forward swing goes a bit inward
ARM_OUT_FWD = 4.0               # deg, extra abduction when forward (clears the belly)
ELBOW = 18.0                    # deg, base elbow bend
ELBOW_FWD = 14.0                # deg, extra bend on the forward swing
FOREARM_LAG = frames(1.6)
HAND_LAG = frames(1.6)
WRIST_FLEX = 12.0               # deg, relaxed wrist bends toward the body
FINGER_CURL = (14.0, 20.0, 16.0)
THUMB_CURL = 8.0
SHRUG = 3.0                     # deg, shoulders lag the bounce
SHRUG_LAG = frames(1.5)
PROTRACT = 3.0                  # deg, shoulder rolls forward with the arm


# ============================================================================= curve tools
class Loop:
    """Periodic cubic Hermite key curve. keys: (fraction of the period, value[, slope per period]).
    Extremes get flat tangents (auto-clamped); other keys use Catmull-Rom slopes.
    odd=True: keys cover the first half period, the second half repeats them negated
    (left/right alternating channels)."""

    def __init__(self, keys, period=1.0, odd=False):
        ks = [(k[0], k[1], k[2] if len(k) > 2 else None) for k in keys]
        if odd:
            ks += [(k[0] + 0.5, -k[1], None if k[2] is None else -k[2]) for k in ks]
        ks = sorted(((k[0] % 1.0) * period, k[1], None if k[2] is None else k[2] / period) for k in ks)
        self.period = period
        self.t = [k[0] for k in ks]
        self.v = [k[1] for k in ks]
        n = len(ks)
        self.m = []
        for i in range(n):
            if ks[i][2] is not None:
                self.m.append(ks[i][2])
                continue
            tp = self.t[i - 1] - (period if i == 0 else 0.0)
            tn = self.t[(i + 1) % n] + (period if i == n - 1 else 0.0)
            vp, v, vn = self.v[i - 1], self.v[i], self.v[(i + 1) % n]
            self.m.append(0.0 if (v - vp) * (vn - v) <= 0.0 else (vn - vp) / (tn - tp))

    def __call__(self, t):
        p, n = self.period, len(self.t)
        t %= p
        if t < self.t[0]:
            i, t0, t1 = n - 1, self.t[-1] - p, self.t[0]
        else:
            i = max(j for j in range(n) if self.t[j] <= t)
            t0, t1 = self.t[i], self.t[(i + 1) % n] + (p if i == n - 1 else 0.0)
        h = t1 - t0
        s = (t - t0) / h
        return hermite(self.v[i], self.m[i] * h, self.v[(i + 1) % n], self.m[(i + 1) % n] * h, s)


def hermite(p0, m0, p1, m1, s):
    s2, s3 = s * s, s * s * s
    return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1


def bump(w, a, b):
    """Smooth 0..1..0 bump on [0, 1] with zero value and slope at both ends; peak at a / (a + b)."""
    if w <= 0.0 or w >= 1.0:
        return 0.0
    c = a / (a + b)
    return (w ** a * (1 - w) ** b) / (c ** a * (1 - c) ** b)


def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def eul(pitch=0.0, roll=0.0, yaw=0.0):
    """World orientation from degrees: pitch about X (+ forward), roll about Y, yaw about Z."""
    return R((0, 0, 1), yaw) @ R((0, 1, 0), roll) @ R((1, 0, 0), pitch)


BOB = Loop(BOB_KEYS, period=0.5)
SWAYC = Loop(SWAY_KEYS, odd=True)
YAWC = Loop(YAW_KEYS, odd=True)
ROLLC = Loop(ROLL_KEYS, odd=True)
ARMC = Loop(ARM_KEYS, odd=True)


# ============================================================================= feet
def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def lower_hull(points):
    """Lower convex hull of (y, z) points, sorted by y."""
    hull = []
    for p in sorted(set(points)):
        while len(hull) >= 2 and _cross(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    return hull


def roll_matrix(chain, angle, toe_up):
    """Rigid roll over a convex sole profile. chain: [(y, z)] pivots in rest space, the first one
    on the ground for the flat foot. The body turns about each pivot in turn until the next hull
    edge lies flat, so every pivot is a fixed ground point while it carries the weight."""
    M = Matrix.Identity(4)
    done = 0.0
    sign = -1.0 if toe_up else 1.0          # rotation about +X: negative lifts the toe
    for i, (y, z) in enumerate(chain):
        if i + 1 < len(chain):
            y2, z2 = chain[i + 1]
            limit = math.degrees(math.atan2(z2 - z, abs(y2 - y)))
        else:
            limit = 180.0
        target = min(angle, limit)
        if target > done:
            p = M @ Vector((0.0, y, z))
            M = Matrix.Translation(p) @ Matrix.Rotation(math.radians(sign * (target - done)), 4, 'X') @ Matrix.Translation(-p) @ M
            done = target
        if done >= angle - 1e-12:
            break
    return M


class Foot:
    """Foot rolls and the swing for one side. Matrices returned are armature-space rigid
    transforms applied to rest matrices (desired = M @ rest)."""

    def __init__(self, side, rest, heel_points, toe_points):
        self.side = side
        self.sgn = 1.0 if side == 'Left' else -1.0
        self.ankle = rest[P + side + 'Foot'].translation.copy()
        self.ball = rest[P + side + 'ToeBase'].translation.copy()
        self.sole = min(p[2] for p in heel_points + toe_points)       # rest sole height (~ -1 mm)
        flat = self.sole + 2e-4
        heel = lower_hull([(p[1], p[2]) for p in heel_points])
        rear = max(p[0] for p in heel if p[1] <= flat)
        self.heel_chain = [p for p in heel if p[0] >= rear]                       # backward and up
        toe = lower_hull([(p[1], p[2]) for p in toe_points])
        front = min(p[0] for p in toe if p[1] <= flat)
        self.toe_chain = sorted((p for p in toe if p[0] <= front), key=lambda p: -p[0])  # forward and up
        self.yaw = Matrix.Rotation(math.radians(self.sgn * TOE_OUT), 4, 'Z')
        self.yaw_inv = Matrix.Rotation(math.radians(-self.sgn * TOE_OUT), 3, 'Z')
        self.y0 = 0.0

    # --- stance pieces
    def anchor(self, yg):
        """Flat foot on the ground: toed out about the ankle axis, on the track, sole exactly at
        z = 0, ankle shifted by yg along +Y (the ground direction)."""
        a = self.ankle
        turn = Matrix.Translation(a) @ self.yaw @ Matrix.Translation(-a)
        return Matrix.Translation(Vector((self.sgn * TRACK - a.x, yg, -self.sole))) @ turn

    def bend(self, deg):
        """Rotation about the ball joint; + lifts the heel (toe down)."""
        b = self.ball
        return Matrix.Translation(b) @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-b)

    @staticmethod
    def heel_angle(s):
        u = s / T_FLAT
        return STRIKE_TOE_UP * (1 - u) * (1 + STRIKE_RATE * u)

    @staticmethod
    def ball_angle(s):
        if s <= T_HEEL_OFF:
            return 0.0
        return BALL_END * ((s - T_HEEL_OFF) / (T_OFF - T_HEEL_OFF)) ** BALL_POWER

    @staticmethod
    def tip_angle(s):
        if s <= T_TIP:
            return 0.0
        return TIP_END * ((s - T_TIP) / (T_OFF - T_TIP)) ** 2

    def stance(self, s):
        """s: phase since this foot's heel strike, 0..T_OFF. Returns (M_foot, M_toe, phase name)."""
        anchor = self.anchor(self.y0 + TRAVEL * s)
        if s < T_FLAT:
            M = anchor @ roll_matrix(self.heel_chain, self.heel_angle(s), True)
            return M, M, 'heel'
        if s <= T_HEEL_OFF:
            return anchor, anchor, 'flat'
        toe = anchor @ roll_matrix(self.toe_chain, self.tip_angle(s), False)
        return toe @ self.bend(self.ball_angle(s)), toe, ('ball' if s <= T_TIP else 'tip')

    # --- swing
    def state(self, Mf, Mt):
        """Ankle position, foot pitch (+ toe down) and toe bend relative to the foot."""
        rf = self.yaw_inv @ Mf.to_3x3()
        rt = self.yaw_inv @ Mt.to_3x3()
        pf = math.degrees(math.atan2(rf[2][1], rf[1][1]))
        pt = math.degrees(math.atan2(rt[2][1], rt[1][1]))
        return Mf @ self.ankle, pf, pt - pf

    def compose(self, ankle, pitch, toe):
        Mf = Matrix.Translation(ankle) @ self.yaw @ Matrix.Rotation(math.radians(pitch), 4, 'X') @ Matrix.Translation(-self.ankle)
        return Mf, Mf @ self.bend(toe)

    def prepare_swing(self, h=1e-5):
        """Boundary states and phase-derivatives of the swing (C1 with both stance ends)."""
        def st(s):
            Mf, Mt, _ = self.stance(s)
            return self.state(Mf, Mt)
        def diff(a, b, dt):
            return ((b[0] - a[0]) / dt, (b[1] - a[1]) / dt, (b[2] - a[2]) / dt)
        self.lift0 = st(T_OFF)
        self.dlift0 = diff(st(T_OFF - h), self.lift0, h)
        self.land1 = st(0.0)
        self.dland1 = diff(self.land1, st(h), h)

    def swing(self, w):
        D = 1.0 - T_OFF
        (p0, a0, k0), (dp0, da0, dk0) = self.lift0, self.dlift0
        (p1, a1, k1), (dp1, da1, dk1) = self.land1, self.dland1
        # Vertical accents (m/s -> per unit phase): the swing leaves and meets the floor with a
        # little vertical speed instead of grazing it tangentially.
        dp0, dp1 = dp0.copy(), dp1.copy()
        dp0.z = SWING_CARRY_Z * dp0.z + LIFT_VZ * CYCLE_S
        da0 = SWING_CARRY_PITCH * da0
        dp1.z += LAND_VZ * CYCLE_S
        # the landing state belongs to the next stance, which starts one cycle later
        p1 = p1.copy()
        ankle = hermite(p0, dp0 * D, p1, dp1 * D, w)
        ankle = Vector(ankle)
        ankle.z += SWING_LIFT * bump(w, *SWING_LIFT_AB)
        ankle.x -= self.sgn * SWING_INWARD * bump(w, 2.0, 2.0)
        pitch = hermite(a0, da0 * D, a1, da1 * D, w) + SWING_TOE * bump(w, *SWING_TOE_AB)
        # The unloaded shoe springs straight: no bend velocity carried over from the stance.
        toe = hermite(k0, TOE_SPRING * dk0 * D, k1, dk1 * D, w)
        return self.compose(ankle, pitch, toe)

    def at(self, s):
        """s: phase since this foot's heel strike, 0..1."""
        s %= 1.0
        if s <= T_OFF:
            Mf, Mt, name = self.stance(s)
            return Mf, Mt, name
        Mf, Mt = self.swing((s - T_OFF) / (1.0 - T_OFF))
        return Mf, Mt, 'swing'


# ============================================================================= whole body
class Walk:
    def __init__(self, rig, rest, shoe, ordered, pose_from_joints, rotate_subtree):
        """shoe: {side: (heel_points, toe_points)} rigid shoe vertices in rest space.
        ordered / pose_from_joints / rotate_subtree: helpers from the character's buddy modules."""
        self.rig, self.rest = rig, rest
        self.pose_from_joints = pose_from_joints
        self.feet = {side: Foot(side, rest, *shoe[side]) for side in ('Left', 'Right')}
        self.l1 = (rest[P + 'LeftLeg'].translation - rest[P + 'LeftUpLeg'].translation).length
        self.l2 = (rest[P + 'LeftFoot'].translation - rest[P + 'LeftLeg'].translation).length
        self.diag = []
        y0 = Y0 if Y0 is not None else self.balance_y0()
        for f in self.feet.values():
            f.y0 = y0
            f.prepare_swing()
        self.y0 = y0

    def balance_y0(self):
        """Centre the stance between the strike ankle and the lift-off ankle around the hips."""
        f = self.feet['Left']
        f.y0 = 0.0
        strike = f.stance(0.0)[0] @ f.ankle
        lift = f.stance(T_OFF)[0] @ f.ankle
        return -(strike.y + lift.y) / 2.0

    # --- pelvis and spine as world orientations
    def pelvis(self, t):
        bob = BOB(t)
        root = Vector((SWAY * SWAYC(t), 0.0, BOB_CENTER + BOB_HALF * bob))
        q = eul(pitch=PELVIS_TILT + PELVIS_TILT_BOB * max(0.0, -BOB(t - frames(0.5))),
                roll=PELVIS_ROLL * ROLLC(t), yaw=PELVIS_YAW * YAWC(t))
        return root, q

    def chest(self, t):
        return eul(pitch=CHEST_LEAN + CHEST_SQUASH * -BOB(t - CHEST_LAG),
                   roll=-CHEST_ROLL * ROLLC(t - CHEST_ROLL_LAG),
                   yaw=-CHEST_YAW * YAWC(t - CHEST_YAW_LAG))

    def head(self, t):
        chest_roll = -CHEST_ROLL * ROLLC(t - HEAD_ROLL_LAG)
        chest_yaw = -CHEST_YAW * YAWC(t - CHEST_YAW_LAG)
        return eul(pitch=HEAD_PITCH + HEAD_NOD * -BOB(t - HEAD_NOD_LAG),
                   roll=HEAD_ROLL * chest_roll, yaw=HEAD_YAW * chest_yaw)

    # --- arms as world orientations of each segment (T-pose based)
    def arm_world(self, side, t):
        sgn = 1.0 if side == 'Left' else -1.0

        def swing(tt):
            return sgn * ARM_SWING * ARMC(tt) + ARM_BIAS        # + back, - forward

        def forward(tt):                                         # 0..1, how far forward the arm is
            return max(0.0, -(swing(tt) - ARM_BIAS) / ARM_SWING)

        def elbow(tt):
            return ELBOW + ELBOW_FWD * (0.5 - 0.5 * sgn * ARMC(tt))

        cross = R((0, 0, 1), -sgn * ARM_CROSS)
        cross_inv = cross.inverted()

        def seg(sw, fl, out, extra=Quaternion()):
            down = R((0, 1, 0), sgn * (ARM_DOWN - out))
            return cross @ R((1, 0, 0), sw) @ cross_inv @ down @ R((0, 0, 1), -sgn * fl) @ extra

        out_a = ARM_OUT_FWD * forward(t)
        upper = seg(swing(t), 0.0, out_a)
        tf = t - FOREARM_LAG
        fore = seg(swing(tf), elbow(t), ARM_OUT_FWD * forward(tf))
        th = tf - HAND_LAG
        hand = seg(swing(th), elbow(t - HAND_LAG), ARM_OUT_FWD * forward(th), R((0, 1, 0), sgn * WRIST_FLEX))
        return upper, fore, hand

    def body_joints(self, t):
        root, qp = self.pelvis(t)
        qc = self.chest(t)
        qh = self.head(t)
        world = {
            'Hips': qp,
            'Spine': qp.slerp(qc, 1 / 3),
            'Spine1': qp.slerp(qc, 2 / 3),
            'Spine2': qc,
            'Neck': qc.slerp(qh, 0.45),
            'Head': qh,
        }
        for side in ('Left', 'Right'):
            sgn = 1.0 if side == 'Left' else -1.0
            sw = sgn * ARMC(t)
            shrug = SHRUG * (BOB(t - SHRUG_LAG) - BOB(t)) * 0.5
            protract = PROTRACT * max(0.0, -sw)
            clav = R((0, 0, 1), -sgn * protract) @ R((0, 1, 0), -sgn * shrug)
            world[side + 'Shoulder'] = clav @ qc
            upper, fore, hand = self.arm_world(side, t)
            world[side + 'Arm'] = upper
            world[side + 'ForeArm'] = fore
            world[side + 'Hand'] = hand
            for finger in ('Index', 'Middle', 'Ring', 'Pinky'):
                q = hand
                for k, c in enumerate(FINGER_CURL, start=1):
                    q = q @ R((0, 1, 0), sgn * c)          # T-pose: +Y curls the left fingers to the palm
                    world[side + 'Hand' + finger + str(k)] = q
            q = hand
            for k in (1, 2, 3):
                q = q @ R((0, 0, 1), sgn * THUMB_CURL) @ R((0, 1, 0), sgn * 0.5 * THUMB_CURL)
                world[side + 'HandThumb' + str(k)] = q
        # world orientation -> joint rotations relative to the parent (telescoping product)
        J = {}
        for name in world:
            bone = self.rig.data.bones[P + name]
            parent = bone.parent
            while parent is not None and parent.name[len(P):] not in world:
                parent = parent.parent
            qparent = world[parent.name[len(P):]] if parent is not None else Quaternion()
            J[name] = world[name] @ qparent.inverted()
        return J, root

    # --- legs
    def solve_leg(self, desired, side, Mf, Mt):
        rest = self.rest
        up, lo, ft, tb, te = (P + side + n for n in ('UpLeg', 'Leg', 'Foot', 'ToeBase', 'Toe_End'))
        hip = desired[up].translation.copy()
        ankle = Mf @ rest[ft].translation
        l1, l2 = self.l1, self.l2
        d_vec = ankle - hip
        d = d_vec.length
        assert d < l1 + l2 - 1e-6, (side, d, l1 + l2)
        dirv = d_vec / d
        sgn = self.feet[side].sgn
        a = math.radians(TOE_OUT + KNEE_OUT)
        pole = Vector((sgn * math.sin(a), -math.cos(a), 0.0))
        pole_perp = (pole - dirv * pole.dot(dirv)).normalized()
        along = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        bend = math.sqrt(max(0.0, l1 * l1 - along * along))
        knee = hip + dirv * along + pole_perp * bend
        lateral = pole_perp.cross(dirv).normalized()

        def frame(direction, lat):
            direction = direction.normalized()
            lat = (lat - direction * lat.dot(direction)).normalized()
            m = Matrix((lat, direction, lat.cross(direction))).transposed()
            return m
        rest_frame = frame(Vector((0, 0, -1)), Vector((1, 0, 0)))
        r_thigh = frame(knee - hip, lateral) @ rest_frame.transposed()
        r_shin = frame(ankle - knee, lateral) @ rest_frame.transposed()
        m = (r_thigh @ rest[up].to_3x3()).to_4x4(); m.translation = hip; desired[up] = m
        m = (r_shin @ rest[lo].to_3x3()).to_4x4(); m.translation = knee; desired[lo] = m
        desired[ft] = Mf @ rest[ft]
        desired[tb] = Mt @ rest[tb]
        desired[te] = Mt @ rest[te]
        knee_angle = math.degrees((knee - hip).angle(ankle - knee))
        return d / (l1 + l2), knee_angle

    def pose(self, t):
        """Armature-space matrices of all bones at cycle phase t, plus diagnostics."""
        J, root = self.body_joints(t)
        desired = self.pose_from_joints(self.rig, self.rest, J, root_offset=root)
        info = {'t': t, 'root': tuple(root)}
        for side, offset in (('Left', 0.0), ('Right', 0.5)):
            Mf, Mt, phase = self.feet[side].at(t - offset)
            reach, knee = self.solve_leg(desired, side, Mf, Mt)
            info[side] = {'phase': phase, 'reach': reach, 'knee': knee}
        return desired, info
