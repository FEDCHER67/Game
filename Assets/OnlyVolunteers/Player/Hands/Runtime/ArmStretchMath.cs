using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// PLAYER HANDS v01 (Fedya 30.10: "the arms reach to it and STRETCH comically, the farther/heavier, the longer"): the
    /// pure maths of the stretchy sausage arms. No scene, no clock: every function is covered by EditMode tests
    /// (Player/Hands/Tests/EditMode). Lengths are world metres, "stretch" is the factor on the rest length of the
    /// upper arm and the forearm (1 = the model's own arm, 2 = twice as long).
    /// </summary>
    public static class ArmStretchMath
    {
        private const float Epsilon = 1e-5f;

        /// <summary>The arm keeps this share of its length as a bend before it starts to stretch (never a locked elbow).</summary>
        public const float DefaultComfort = 0.92f;

        /// <summary>Stretch the chain needs so the wrist lies <paramref name="distance"/> from the shoulder.
        /// 1 while the target is within easy reach (<paramref name="restReach"/> x <paramref name="comfort"/>); beyond it the
        /// arm grows so it keeps the same slight bend. Once stretched, heft (0..1) adds <paramref name="sagPerHeft"/> of
        /// extra length so a heavy load makes the long arm droop at the elbow (faded in over the first half reach of
        /// stretch, so a near hold never sags). Never below 1 (the springs alone may squash the arm a little).</summary>
        public static float NeededStretch(float distance, float restReach, float heft, float sagPerHeft,
            float comfort = DefaultComfort)
        {
            if (restReach <= Epsilon || float.IsNaN(distance)) return 1f;
            comfort = Mathf.Clamp(comfort, 0.5f, 1f);
            float easy = restReach * comfort;
            if (distance <= easy) return 1f;
            float fade = SmoothStep(Mathf.InverseLerp(easy, restReach * 1.5f, distance));
            float sag = 1f + Mathf.Max(0f, sagPerHeft) * Mathf.Clamp01(heft) * fade;
            return Mathf.Max(1f, distance * sag / easy);
        }

        /// <summary>Share of the stretch range (1..max) that passes unchanged before the soft clamp bends in.</summary>
        public const float SoftKnee = 0.7f;

        /// <summary>Soft upper clamp: identity up to the knee (1 + <see cref="SoftKnee"/> of the range), then approaches
        /// <paramref name="max"/> smoothly (tanh, same slope at the knee) and never passes it; monotonic, so a farther target
        /// always means a longer arm until the limit. (v01 bent in from 1 already, so mid holds fell short of the grip.)</summary>
        public static float SoftClamp(float stretch, float max)
        {
            if (float.IsNaN(stretch)) return 1f;
            if (stretch <= 1f || max <= 1f + Epsilon) return Mathf.Min(stretch, Mathf.Max(1f, max));
            float knee = 1f + (max - 1f) * SoftKnee;
            if (stretch <= knee) return stretch;
            float k = max - knee;
            return knee + k * Tanh((stretch - knee) / k);
        }

        /// <summary>How fast a stretched arm thins: thickness = stretch^-ThinExponent (0.5 would keep the volume; less
        /// keeps a long arm readable as a sausage, not a cable).</summary>
        public const float ThinExponent = 0.3f;

        /// <summary>Cross-section factor of a stretched (thinner, a rubber hose) or squashed (fatter) arm:
        /// stretch^-<see cref="ThinExponent"/> when stretched, 1/sqrt(stretch) when squashed, kept within
        /// [minThickness, maxSquash].</summary>
        public static float Thickness(float stretch, float minThickness = 0.6f, float maxSquash = 1.3f)
        {
            if (stretch <= Epsilon || float.IsNaN(stretch)) return 1f;
            if (stretch >= 1f) return Mathf.Clamp(Mathf.Pow(stretch, -ThinExponent), Mathf.Clamp(minThickness, 0.05f, 1f), 1f);
            return Mathf.Clamp(1f / Mathf.Sqrt(stretch), 1f, Mathf.Max(1f, maxSquash));
        }

        /// <summary>Damped spring step (any damping: below 1 it overshoots and wobbles, the comic snap-back). Semi-implicit
        /// Euler in sub-steps of at most 1/120 s, so a hitch frame stays stable.</summary>
        public static float Spring(float value, ref float velocity, float target, float frequencyHz, float damping, float dt)
        {
            if (dt <= 0f || float.IsNaN(dt)) return value;
            if (frequencyHz <= Epsilon) { velocity = 0f; return target; }
            float w = 2f * Mathf.PI * frequencyHz;
            int steps = Mathf.Clamp(Mathf.CeilToInt(dt * 120f), 1, 16);
            float h = Mathf.Min(dt, 0.25f) / steps;
            for (int i = 0; i < steps; i++)
            {
                float a = -w * w * (value - target) - 2f * damping * w * velocity;
                velocity += a * h;
                value += velocity * h;
            }
            return value;
        }

        public static Vector3 Spring(Vector3 value, ref Vector3 velocity, Vector3 target, float frequencyHz, float damping, float dt)
        {
            float vx = velocity.x, vy = velocity.y, vz = velocity.z;
            var r = new Vector3(Spring(value.x, ref vx, target.x, frequencyHz, damping, dt),
                Spring(value.y, ref vy, target.y, frequencyHz, damping, dt),
                Spring(value.z, ref vz, target.z, frequencyHz, damping, dt));
            velocity = new Vector3(vx, vy, vz);
            return r;
        }

        /// <summary>Two-bone IK (law of cosines) in world space: shoulder <paramref name="root"/>, bone lengths
        /// <paramref name="upper"/> and <paramref name="lower"/> (already stretched), elbow bent toward
        /// <paramref name="pole"/>. An unreachable target is clamped onto the reach sphere (arm straight toward it, the
        /// hand falls short); a too-near one onto the inner sphere. Returns true when the target was reached.</summary>
        public static bool SolveTwoBone(Vector3 root, float upper, float lower, Vector3 target, Vector3 pole,
            out Vector3 elbow, out Vector3 end)
        {
            upper = Mathf.Max(upper, Epsilon * 10f);
            lower = Mathf.Max(lower, Epsilon * 10f);
            Vector3 toTarget = target - root;
            float distance = toTarget.magnitude;
            Vector3 dir = distance > Epsilon ? toTarget / distance : Vector3.forward;
            float maxReach = (upper + lower) * 0.9999f;
            float minReach = Mathf.Abs(upper - lower) + Epsilon;
            bool reached = distance <= maxReach + 1e-4f && distance >= minReach - 1e-4f;
            float d = Mathf.Clamp(distance, minReach, Mathf.Max(minReach, maxReach));

            Vector3 bend = Vector3.ProjectOnPlane(pole - root, dir);
            if (bend.sqrMagnitude < Epsilon * Epsilon)
            {
                bend = Vector3.ProjectOnPlane(Vector3.down, dir);
                if (bend.sqrMagnitude < Epsilon * Epsilon) bend = Vector3.ProjectOnPlane(Vector3.forward, dir);
            }
            bend.Normalize();
            float cosA = Mathf.Clamp((upper * upper + d * d - lower * lower) / (2f * upper * d), -1f, 1f);
            float sinA = Mathf.Sqrt(Mathf.Max(0f, 1f - cosA * cosA));
            elbow = root + dir * (upper * cosA) + bend * (upper * sinA);
            end = root + dir * d;
            return reached;
        }

        /// <summary>Hand frame: local +Y along the fingers, local +Z out of the palm (the Mixamo hand bones of the sausage
        /// rig). The palm hint is made orthogonal to the finger direction; degenerate hints fall back to a stable axis.</summary>
        public static Quaternion HandRotation(Vector3 fingerDirection, Vector3 palmHint)
        {
            if (fingerDirection.sqrMagnitude < Epsilon) fingerDirection = Vector3.forward;
            fingerDirection.Normalize();
            Vector3 palm = Vector3.ProjectOnPlane(palmHint, fingerDirection);
            if (palm.sqrMagnitude < 1e-6f)
            {
                palm = Vector3.ProjectOnPlane(Vector3.up, fingerDirection);
                if (palm.sqrMagnitude < 1e-6f) palm = Vector3.ProjectOnPlane(Vector3.forward, fingerDirection);
            }
            return Quaternion.LookRotation(palm.normalized, fingerDirection);
        }

        /// <summary>Weapon-style sway: the arms lag the look. (yaw, pitch) degrees per second in; (pitch, yaw, roll) offset
        /// degrees out, each clamped to <paramref name="maxDegrees"/>.</summary>
        public static Vector3 SwayAngles(Vector2 lookVelocity, float gain, float maxDegrees, float rollGain)
        {
            float yaw = Mathf.Clamp(-lookVelocity.x * gain, -maxDegrees, maxDegrees);
            float pitch = Mathf.Clamp(lookVelocity.y * gain, -maxDegrees, maxDegrees);
            float roll = Mathf.Clamp(-lookVelocity.x * rollGain, -maxDegrees, maxDegrees);
            return new Vector3(pitch, yaw, roll);
        }

        /// <summary>Advances the walk-bob phase (radians, wrapped) by the distance walked.</summary>
        public static float AdvanceBobPhase(float phase, float planarSpeed, float cyclesPerMeter, float dt)
        {
            phase += Mathf.Max(0f, planarSpeed) * cyclesPerMeter * Mathf.Max(0f, dt) * 2f * Mathf.PI;
            return Mathf.Repeat(phase, 2f * Mathf.PI);
        }

        /// <summary>Figure-eight walk bob: sideways once per cycle, a dip at each footstep; weight 0..1.</summary>
        public static Vector3 BobOffset(float phase, float weight, Vector2 amplitude)
        {
            weight = Mathf.Clamp01(weight);
            return new Vector3(Mathf.Sin(phase) * amplitude.x, -Mathf.Abs(Mathf.Sin(phase)) * amplitude.y, 0f) * weight;
        }

        /// <summary>How far to pull the camera-held hands back (0 none .. 1 all the way) when a wall is
        /// <paramref name="hitDistance"/> ahead and the hands sit <paramref name="reach"/> in front.</summary>
        public static float WallRetract(float hitDistance, float reach)
        {
            if (reach <= Epsilon || hitDistance >= reach) return 0f;
            return Mathf.Clamp01(1f - Mathf.Max(0f, hitDistance) / reach);
        }

        public static float SmoothStep(float t)
        {
            t = Mathf.Clamp01(t);
            return t * t * (3f - 2f * t);
        }

        private static float Tanh(float x)
        {
            if (x > 9f) return 1f;
            if (x < -9f) return -1f;
            float e = Mathf.Exp(2f * x);
            return (e - 1f) / (e + 1f);
        }
    }
}
