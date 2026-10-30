using System;
using OnlyVolunteers.Characters.Npc;
using UnityEngine;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture (docs/specs/V2_CAPTURE_SLAP_DRAG_THROW_2026-10-31.md §3): the one point a player holds.</summary>
    public enum GrabPointV2 : byte { None, Head, Collar, ArmLeft, ArmRight, LegLeft, LegRight, Torso }

    /// <summary>The throw per grab (§5): head / collar / torso over the head like a sack, a leg half a hammer-thrower
    /// spin, an arm a full spin and fling.</summary>
    public enum ThrowStyleV2 : byte { OverHead, Hammer, Spin }

    /// <summary>Every tunable number of V2 capture phase 1 (+ the cling of phase 2), on CaptureV2Rig.Tuning.</summary>
    [Serializable]
    public sealed class CaptureV2Tuning
    {
        [Header("Slap (LMB: hold to charge, release to slap; Vadim 31.10: short, snappy, never tiring)")]
        public float ChargeMax = 1f;          // s of holding LMB for the full charge
        public float ClickSeconds = 0.12f;    // held up to this long: a plain click (no charge)
        public float MinWindup = 0.12f;       // a quick click still cocks the arm this long before the swipe (CaptureV2Palm.Entry)
        public float ChargeAutoRelease = 3f;  // held this long: it fires by itself (he is not frozen forever)
        public float ChargeHitStopGain = 0.8f; // full charge: hit-stop x(1 + gain): 0.05 -> 0.09 s
        public float ChargeShakeGain = 1f;    // full charge: shake x(1 + gain)
        public float ChargeSpinExtra = 180f;  // full charge: he spins this much further (a whole turn)
        public float ChargeFlySpeed = 4.5f;   // full charge: m/s along the smack as he drops (flies a little)
        public float ChargeFlyUp = 2.2f;      // full charge: m/s up
        public float ChargeKnockOutGain = 0.4f; // full charge: out cold x(1 + gain): 5 -> 7 s
        public float SlapCooldown = 0.2f;     // after the smack
        public float SlapReach = 2.3f;        // the target must be this close when LMB is pressed
        public float SlapLungeReach = 3.2f;   // and still this close at the smack (he freezes in shock meanwhile)
        public float SlapHitStop = 0.05f;     // the contact frame held (real seconds)
        public float SlapShake = 0.25f;       // degrees, pitch/yaw only (no roll), ~0.07 s
        public float SlapKickYaw = 0.9f;      // degrees: the view snaps this way along the swipe (x(1 + charge))
        public float SlapPushIn = 3.5f;       // degrees of field of view the charge narrows (toward his face)
        public float HeadSnapDegrees = 50f;   // the head whips this far along the swipe first (+25 % charged), then the body follows
        public float HeadSnapSeconds = 0.045f;
        public float SpinDelay = 0.06f;       // the body starts turning this long after the head
        public float SpinSeconds = 0.28f;     // the half turn before he drops
        public float SpinDegrees = 180f;
        public float SackImpulse = 18f;       // N·s at the smack (the stock fist pushes 60: he flies, here he drops)

        [Header("Knock-out (Vadim 31.10: time to grab him and throw him in)")]
        public float[] KnockOutLadder = { 5f, 3f, 2f, 1f }; // 1st, 2nd, 3rd, 4th and later slap of one catch
        public float HuhBefore = 0.5f;        // the "huh?" face this long before waking
        public float LadderReset = 12f;       // s free and unslapped: the ladder starts over

        [Header("Carry: player speed x walk speed")]
        public float SpeedHead = 0.85f, SpeedCollar = 0.85f, SpeedArm = 0.75f, SpeedLeg = 0.65f, SpeedTorso = 0.6f;

        [Header("Escape meter (0..1, fills only while he is awake in the hands)")]
        public float MeterBase = 0.12f;          // per s
        public float MeterPerSecondHeld = 0.04f; // per s, for every s held since the grab
        public float MeterPerMetre = 0.02f;      // per s, for every m dragged since the grab
        public float MeterArmScale = 1.2f, MeterLegScale = 0.9f;

        [Header("Throw into the van (E at an open door)")]
        public float SwingSeconds = 0.55f;
        public float FlightSeconds = 0.32f;
        public float ThrowHitStop = 0.1f;
        public float ThrowKick = 3.5f;          // degrees of camera kick on release
        public float VanDip = 1100f;            // N·s down on the van where he lands
        public float VanRock = 350f;            // N·s sideways at the roof
        public float BeltDelay = 0.45f;         // s after landing: the belt goes "clack"

        [Header("Cling and yank (§4)")]
        public bool AutoCling = true;
        public float ClingCheckEvery = 0.5f, ClingChance = 0.35f, ClingReach = 0.45f, ClingCooldown = 3f;
        public float ClingHeavyMouse = 0.3f;    // share of the mouse turn the camera still gets
        public float ClingMaxView = 25f;      // degrees: the view cannot be flicked further than this off him
        public float ClingPullDegPerSec = 28f;  // the counter-force: the view dragged toward what he holds
        public float FlickThreshold = 300f;     // deg/s along the arrow before a flick counts
        public float FlickGain = 1.6f;          // bar per s for every 1000 deg/s above the threshold
        public float BarDrain = 0.35f;          // per s
        public float PopPlayerKnock = 3f, PopNpcSpeed = 4f;
    }

    /// <summary>Pure rules of V2 capture (no scene state): grab classification, speeds, the knock-out ladder, the escape
    /// meter and the yank bar.</summary>
    public static class CaptureV2Rules
    {
        /// <summary>The slap's charge 0..1 after holding LMB 'held' s: 0 up to ClickSeconds, 1 at ChargeMax.</summary>
        public static float Charge(CaptureV2Tuning t, float held) =>
            Mathf.Clamp01((held - t.ClickSeconds) / Mathf.Max(0.05f, t.ChargeMax - t.ClickSeconds));

        public static GrabPointV2 Classify(Kind kind, NpcSide side, bool badHandle)
        {
            switch (kind)
            {
                case Kind.Head: return GrabPointV2.Head;
                case Kind.Chest: return badHandle ? GrabPointV2.Torso : GrabPointV2.Collar;
                case Kind.UpperArm:
                case Kind.ForeArm: return side == NpcSide.Left ? GrabPointV2.ArmLeft : GrabPointV2.ArmRight;
                case Kind.Thigh:
                case Kind.Calf: return side == NpcSide.Left ? GrabPointV2.LegLeft : GrabPointV2.LegRight;
                default: return GrabPointV2.Torso;
            }
        }

        public static bool IsArm(GrabPointV2 g) => g == GrabPointV2.ArmLeft || g == GrabPointV2.ArmRight;
        public static bool IsLeg(GrabPointV2 g) => g == GrabPointV2.LegLeft || g == GrabPointV2.LegRight;
        public static bool IsLeft(GrabPointV2 g) => g == GrabPointV2.ArmLeft || g == GrabPointV2.LegLeft;

        public static float SpeedScale(CaptureV2Tuning t, GrabPointV2 g) => g switch
        {
            GrabPointV2.Head => t.SpeedHead,
            GrabPointV2.Collar => t.SpeedCollar,
            GrabPointV2.ArmLeft or GrabPointV2.ArmRight => t.SpeedArm,
            GrabPointV2.LegLeft or GrabPointV2.LegRight => t.SpeedLeg,
            GrabPointV2.Torso => t.SpeedTorso,
            _ => 1f,
        };

        public static ThrowStyleV2 Style(GrabPointV2 g) =>
            IsLeg(g) ? ThrowStyleV2.Hammer : IsArm(g) ? ThrowStyleV2.Spin : ThrowStyleV2.OverHead;

        /// <summary>Seconds out cold for the slap with this index in one catch (0 = first): 5 / 3 / 2 / 1 / 1 ...</summary>
        public static float KnockOut(CaptureV2Tuning t, int slapIndex)
        {
            float[] l = t.KnockOutLadder;
            if (l == null || l.Length == 0) return 5f;
            return l[Mathf.Clamp(slapIndex, 0, l.Length - 1)];
        }

        /// <summary>Escape meter per second: faster the longer and the further he has been dragged since the grab.</summary>
        public static float MeterRate(CaptureV2Tuning t, GrabPointV2 g, float heldSeconds, float draggedMetres)
        {
            float scale = IsArm(g) ? t.MeterArmScale : IsLeg(g) ? t.MeterLegScale : 1f;
            return scale * (t.MeterBase + t.MeterPerSecondHeld * Mathf.Max(0f, heldSeconds) + t.MeterPerMetre * Mathf.Max(0f, draggedMetres));
        }

        /// <summary>The yank bar this frame: flicks faster than the threshold along the arrow fill it, anything else drains it.</summary>
        public static float YankBar(CaptureV2Tuning t, float bar, float alongDegPerSecond, float dt)
        {
            float over = alongDegPerSecond - t.FlickThreshold;
            bar = over > 0f ? bar + over / 1000f * t.FlickGain * dt : bar - t.BarDrain * dt;
            return Mathf.Clamp01(bar);
        }

        /// <summary>HUD name of the hold (accusative: "держишь за ...").</summary>
        public static string Name(GrabPointV2 g) => g switch
        {
            GrabPointV2.Head => "голову",
            GrabPointV2.Collar => "шкирку",
            GrabPointV2.ArmLeft => "левую руку",
            GrabPointV2.ArmRight => "правую руку",
            GrabPointV2.LegLeft => "левую ногу",
            GrabPointV2.LegRight => "правую ногу",
            GrabPointV2.Torso => "пояс",
            _ => "?",
        };
    }
}
