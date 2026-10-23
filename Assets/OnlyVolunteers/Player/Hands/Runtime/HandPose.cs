using System;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>One hand of a <see cref="HandPose"/>: where the hand's grip point sits in view space (metres and
    /// degrees, relative to the camera; +z forward) and how curled the fingers are.</summary>
    [Serializable]
    public struct HandTarget
    {
        public Vector3 gripPosition;
        public Vector3 gripEuler;
        [Tooltip("Finger curl 0 (flat) .. 1 (fist): x thumb, y index, z middle, w ring+pinky.")]
        public Vector4 curl;
        [Range(-1f, 1f)] public float spread;

        public Pose GripPose => new Pose(gripPosition, Quaternion.Euler(gripEuler));

        public HandTarget(Vector3 position, Vector3 euler, Vector4 curl, float spread = 0f)
        {
            gripPosition = position; gripEuler = euler; this.curl = curl; this.spread = spread;
        }
    }

    /// <summary>A static first-person hand pose (spec §3). Authored once per <see cref="HandPoseId"/> in a
    /// <see cref="HandPoseLibrary"/>; items only pick an id and add a small offset (<see cref="ItemGrip"/>).</summary>
    [CreateAssetMenu(menuName = "OnlyVolunteers/Hands/Hand Pose", fileName = "HandPose_")]
    public sealed class HandPose : ScriptableObject
    {
        public HandPoseId id;
        public HandTarget right;
        public HandTarget left;
        [Tooltip("The off hand IKs to the held item's Grip_Off socket (two-handed carry, phone) instead of its own target.")]
        public bool offHandUsesSocket;
        [Min(0f)] public float blendTime = 0.15f;
        [Tooltip("Multiplies sway/bob: heavy two-handed loads swing more, the phone less.")]
        [Min(0f)] public float motionScale = 1f;
        [Header("Use (one-shot)")]
        [Tooltip("Primary hand offset at the peak of a Use, in view space.")]
        public Vector3 useOffset = new Vector3(0f, 0f, 0.06f);
        public Vector3 useEuler;
        [Min(0.01f)] public float useDuration = 0.25f;

        /// <summary>Greybox values for every pose, used when a library has no asset for an id, so the hands work
        /// before any art or authoring. View space: x right, y up, z forward; rotations use the grip axes of ItemGrip.</summary>
        public static void Defaults(HandPoseId id, out HandTarget r, out HandTarget l, out bool offHandSocket)
        {
            var relaxed = new Vector4(0.3f, 0.35f, 0.4f, 0.45f);
            var fist = new Vector4(0.7f, 0.85f, 0.9f, 0.95f);
            var lowLeft = new HandTarget(new Vector3(-0.3f, -0.42f, 0.22f), new Vector3(10f, 0f, 20f), relaxed);
            offHandSocket = false;
            switch (id)
            {
                case HandPoseId.GripCylinder:
                    r = new HandTarget(new Vector3(0.17f, -0.2f, 0.38f), new Vector3(-10f, -8f, 0f), fist); l = lowLeft; break;
                case HandPoseId.Pinch:
                    r = new HandTarget(new Vector3(0.15f, -0.17f, 0.36f), new Vector3(-20f, -10f, 0f),
                        new Vector4(0.55f, 0.6f, 0.3f, 0.5f)); l = lowLeft; break;
                case HandPoseId.PalmUpCarry:
                    r = new HandTarget(new Vector3(0.13f, -0.22f, 0.4f), new Vector3(0f, -10f, -90f),
                        new Vector4(0.15f, 0.25f, 0.25f, 0.3f), 0.3f); l = lowLeft; break;
                case HandPoseId.TwoHandCarry:
                    r = new HandTarget(new Vector3(0.2f, -0.3f, 0.42f), new Vector3(0f, -15f, 0f), fist);
                    l = new HandTarget(new Vector3(-0.2f, -0.3f, 0.42f), new Vector3(0f, 15f, 0f), fist); offHandSocket = true; break;
                case HandPoseId.PhoneHold:
                    r = new HandTarget(new Vector3(0.12f, -0.2f, 0.34f), new Vector3(-30f, -20f, 0f),
                        new Vector4(0.2f, 0.5f, 0.8f, 0.9f));
                    l = new HandTarget(new Vector3(-0.05f, -0.16f, 0.36f), new Vector3(-30f, 15f, 70f),
                        new Vector4(0.4f, 0.6f, 0.6f, 0.65f)); offHandSocket = true; break;
                case HandPoseId.PushPull:
                    r = new HandTarget(new Vector3(0.2f, -0.25f, 0.5f), new Vector3(0f, 0f, 80f), fist);
                    l = new HandTarget(new Vector3(-0.2f, -0.25f, 0.5f), new Vector3(0f, 0f, -80f), fist); break;
                case HandPoseId.ThrowWindup:
                    r = new HandTarget(new Vector3(0.28f, -0.05f, 0.08f), new Vector3(-40f, -30f, 0f), fist);
                    l = new HandTarget(new Vector3(-0.15f, -0.2f, 0.4f), new Vector3(0f, 10f, 30f), relaxed, 0.6f); break;
                default: // Empty
                    r = new HandTarget(new Vector3(0.3f, -0.42f, 0.22f), new Vector3(10f, 0f, -20f), relaxed); l = lowLeft; break;
            }
        }

        public void ResetToDefaults()
        {
            Defaults(id, out right, out left, out offHandUsesSocket);
        }

        private void Reset() => ResetToDefaults();
    }
}
