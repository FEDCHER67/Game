using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// The two arms of one Mixamo-named body (the player sausage PLAYER_SAUSAGE_W86, Buddy_Rig_Mixamo65; any rig with
    /// mixamorig:*Arm / *ForeArm / *Hand) made stretchy and solvable.
    ///
    /// How the stretch is drawn without shearing: a non-uniform scale on a parent bone would skew every rotated child, so
    /// the original bones are never scaled. Instead the elbow and the wrist move out along the bone (ForeArm/Hand
    /// localPosition x stretch) and two helper transforms per arm (siblings under the rig root, never animated) copy the
    /// upper arm's and the forearm's pose with a scale along the bone axis (local +Y) and a thinner cross-section. Every
    /// SkinnedMeshRenderer of the body is re-pointed from those two bones to the helpers, so the sleeve and the arm skin
    /// stretch like a rubber hose while the hand (still the real bone) keeps its size. At stretch 1 the helpers equal the
    /// bones exactly, so the body clip looks as before.
    /// </summary>
    public sealed class StretchArmRigV01
    {
        public enum Side { Right = 0, Left = 1 }

        /// <summary>How far the grip point sits out of the palm, as a share of the wrist-to-knuckles length.</summary>
        public const float PalmDepth = 0.28f;

        public sealed class Arm
        {
            public Side Side;
            public Transform Shoulder, Upper, Lower, Hand;
            public Transform UpperHelper, LowerHelper;
            /// <summary>v02 cuffs: the hand as it would sit on the forearm without its own bend (the wrist joint, the
            /// forearm's rotation x the hand's rest rotation). Sleeve vertices skinned to the hand use it, so a cuff stays
            /// a clean ring on the forearm while the real hand bends inside it.</summary>
            public Transform CuffHelper;
            public Vector3 LowerRestLocal, HandRestLocal;
            public Quaternion UpperRestRotation, LowerRestRotation, HandRestRotation, ShoulderRestRotation;
            /// <summary>The grip (palm centre) in the hand bone's local space.</summary>
            public Vector3 GripLocal;
            public Transform[] Fingers;
            public Quaternion[] FingerRest;
            public bool[] Thumb;
            public int[] Segment;
            /// <summary>Helper scale per unit (bone lossy / helper parent lossy at bind time).</summary>
            public float HelperUnit = 1f;
        }

        public readonly Arm[] Arms = new Arm[2];
        public Transform Root { get; private set; }
        public Transform RigRoot { get; private set; }
        public Transform Head { get; private set; }
        public Transform Neck { get; private set; }
        public Quaternion HeadRest { get; private set; }
        public Quaternion NeckRest { get; private set; }
        public bool Valid => Arms[0] != null && Arms[1] != null;
        public int PatchedRenderers { get; private set; }

        public Arm this[Side side] => Arms[(int)side];

        /// <summary>Finds the arm bones under <paramref name="root"/> (names ending in RightArm, RightForeArm, ...), creates
        /// the helpers and re-points every SkinnedMeshRenderer below root. Returns null when the rig has no such arms.</summary>
        public static StretchArmRigV01 Bind(Transform root)
        {
            if (root == null) return null;
            var all = root.GetComponentsInChildren<Transform>(true);
            var rig = new StretchArmRigV01 { Root = root };
            rig.Arms[0] = BindArm(all, Side.Right, "Right");
            rig.Arms[1] = BindArm(all, Side.Left, "Left");
            if (!rig.Valid) return null;
            rig.Head = Find(all, "Head");
            rig.Neck = Find(all, "Neck");
            if (rig.Head != null) rig.HeadRest = rig.Head.localRotation;
            if (rig.Neck != null) rig.NeckRest = rig.Neck.localRotation;
            // The helpers' parent: the topmost ancestor of the arms below root (Buddy_Rig_Mixamo65), uniformly scaled.
            Transform rigRoot = rig.Arms[0].Upper;
            while (rigRoot.parent != null && rigRoot.parent != root) rigRoot = rigRoot.parent;
            rig.RigRoot = rigRoot;
            var map = new Dictionary<Transform, Transform>();
            foreach (var arm in rig.Arms)
            {
                arm.UpperHelper = MakeHelper(rigRoot, arm.Upper, "ArmStretch_" + arm.Side + "_Upper");
                arm.LowerHelper = MakeHelper(rigRoot, arm.Lower, "ArmStretch_" + arm.Side + "_Lower");
                arm.CuffHelper = MakeHelper(rigRoot, arm.Hand, "ArmStretch_" + arm.Side + "_Cuff");
                float parentUnit = Mathf.Max(1e-6f, Mathf.Abs(rigRoot.lossyScale.x));
                arm.HelperUnit = Mathf.Abs(arm.Upper.lossyScale.x) / parentUnit;
                map[arm.Upper] = arm.UpperHelper;
                map[arm.Lower] = arm.LowerHelper;
            }
            foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var bones = smr.bones;
                bool changed = false;
                for (int i = 0; i < bones.Length; i++)
                    if (bones[i] != null && map.TryGetValue(bones[i], out var helper)) { bones[i] = helper; changed = true; }
                if (!changed) continue;
                smr.bones = bones;
                rig.PatchedRenderers++;
            }
            rig.SyncHelpers();
            return rig;
        }

        private static Transform Find(Transform[] all, string suffix)
        {
            foreach (var t in all)
                if (t.name == suffix || t.name.EndsWith(":" + suffix)) return t;
            return null;
        }

        private static Arm BindArm(Transform[] all, Side side, string s)
        {
            var arm = new Arm
            {
                Side = side,
                Shoulder = Find(all, s + "Shoulder"),
                Upper = Find(all, s + "Arm"),
                Lower = Find(all, s + "ForeArm"),
                Hand = Find(all, s + "Hand"),
            };
            if (arm.Upper == null || arm.Lower == null || arm.Hand == null) return null;
            arm.LowerRestLocal = arm.Lower.localPosition;
            arm.HandRestLocal = arm.Hand.localPosition;
            arm.UpperRestRotation = arm.Upper.localRotation;
            arm.LowerRestRotation = arm.Lower.localRotation;
            arm.HandRestRotation = arm.Hand.localRotation;
            arm.ShoulderRestRotation = arm.Shoulder != null ? arm.Shoulder.localRotation : Quaternion.identity;
            var fingers = new List<Transform>();
            var thumb = new List<bool>();
            var segment = new List<int>();
            Transform middle1 = null;
            foreach (var t in arm.Hand.GetComponentsInChildren<Transform>(true))
            {
                if (t == arm.Hand) continue;
                string n = t.name;
                int k = n.Length > 0 ? n[n.Length - 1] - '0' : -1;
                if (k < 1 || k > 3) continue; // ...1..3 are joints, ...4 the tip ends
                bool isThumb = n.Contains("Thumb");
                if (!isThumb && !n.Contains("Index") && !n.Contains("Middle") && !n.Contains("Ring") && !n.Contains("Pinky")) continue;
                fingers.Add(t); thumb.Add(isThumb); segment.Add(k);
                if (k == 1 && n.Contains("Middle")) middle1 = t;
            }
            arm.Fingers = fingers.ToArray();
            arm.Thumb = thumb.ToArray();
            arm.Segment = segment.ToArray();
            arm.FingerRest = new Quaternion[arm.Fingers.Length];
            for (int i = 0; i < arm.Fingers.Length; i++) arm.FingerRest[i] = arm.Fingers[i].localRotation;
            // Palm centre: most of the way from the wrist to the middle finger's root, a little out of the palm (+Z).
            Vector3 knuckles = middle1 != null ? middle1.localPosition : arm.HandRestLocal * 0.45f;
            arm.GripLocal = knuckles * 0.8f + Vector3.forward * (knuckles.magnitude * PalmDepth);
            return arm;
        }

        private static Transform MakeHelper(Transform parent, Transform bone, string name)
        {
            var existing = parent.Find(name);
            Transform t = existing != null ? existing : new GameObject(name).transform;
            t.SetParent(parent, false);
            t.SetPositionAndRotation(bone.position, bone.rotation);
            t.localScale = Vector3.one;
            return t;
        }

        /// <summary>v02 cuffs: re-points this renderer's hand bones to the cuff helpers (call for clothing only, never for
        /// the hands themselves). At the hand's rest bend the helper equals the hand bone, so nothing moves until the wrist
        /// bends; then the sleeve's hand-weighted rim follows the forearm instead of twisting with the hand. Returns the
        /// number of bone slots re-pointed.</summary>
        public int BindCuffs(SkinnedMeshRenderer smr)
        {
            if (smr == null) return 0;
            var bones = smr.bones;
            int n = 0;
            for (int i = 0; i < bones.Length; i++)
                foreach (var a in Arms)
                    if (a != null && a.CuffHelper != null && bones[i] == a.Hand) { bones[i] = a.CuffHelper; n++; }
            if (n > 0) smr.bones = bones;
            return n;
        }

        /// <summary>World length of the unstretched upper arm + forearm (shoulder to wrist).</summary>
        public float RestReach(Side side)
        {
            var a = Arms[(int)side];
            return a.LowerRestLocal.magnitude * Mathf.Abs(a.Upper.lossyScale.x) +
                   a.HandRestLocal.magnitude * Mathf.Abs(a.Lower.lossyScale.x);
        }

        public Vector3 ShoulderPosition(Side side) => Arms[(int)side].Upper.position;

        /// <summary>Wrist position that puts the palm centre on <paramref name="grip"/> with the hand turned to
        /// <paramref name="handRotation"/>.</summary>
        public Vector3 WristForGrip(Side side, Vector3 grip, Quaternion handRotation)
        {
            var a = Arms[(int)side];
            return grip - handRotation * Vector3.Scale(a.GripLocal, a.Hand.lossyScale);
        }

        /// <summary>First-person arms (no Animator): back to the bind pose before solving.</summary>
        public void ResetToRest()
        {
            foreach (var a in Arms)
            {
                if (a.Shoulder != null) a.Shoulder.localRotation = a.ShoulderRestRotation;
                a.Upper.localRotation = a.UpperRestRotation;
                a.Lower.localRotation = a.LowerRestRotation;
                a.Hand.localRotation = a.HandRestRotation;
                a.Lower.localPosition = a.LowerRestLocal;
                a.Hand.localPosition = a.HandRestLocal;
                for (int i = 0; i < a.Fingers.Length; i++) a.Fingers[i].localRotation = a.FingerRest[i];
            }
        }

        /// <summary>Puts the arm's bone lengths back to rest (third person: the clip may not write positions).</summary>
        public void RestoreLengths(Side side)
        {
            var a = Arms[(int)side];
            a.Lower.localPosition = a.LowerRestLocal;
            a.Hand.localPosition = a.HandRestLocal;
        }

        /// <summary>Solves one arm: stretches it by <paramref name="stretch"/>, bends the elbow toward
        /// <paramref name="pole"/> so the wrist lands on <paramref name="wrist"/> (as far as the stretched arm reaches) and
        /// turns the hand to <paramref name="handRotation"/>. <paramref name="weight"/> blends the target and the hand turn
        /// from the current (animated) pose: 0 leaves it untouched. The caller blends the stretch itself (pass the same
        /// value to <see cref="SyncHelpers"/>). Returns how far the wrist fell short (0 = reached).</summary>
        public float Solve(Side side, Vector3 wrist, Quaternion handRotation, Vector3 pole, float stretch, float weight)
        {
            var a = Arms[(int)side];
            weight = Mathf.Clamp01(weight);
            if (weight <= 0f) { RestoreLengths(side); return 0f; }
            float s = Mathf.Max(0.3f, stretch);
            Vector3 animatedWrist = a.Hand.position;
            a.Lower.localPosition = a.LowerRestLocal * s;
            a.Hand.localPosition = a.HandRestLocal * s;
            Vector3 shoulder = a.Upper.position;
            Vector3 elbowNow = a.Lower.position;
            Vector3 wristNow = a.Hand.position;
            float l1 = (elbowNow - shoulder).magnitude, l2 = (wristNow - elbowNow).magnitude;
            Vector3 target = weight < 1f ? Vector3.Lerp(animatedWrist, wrist, weight) : wrist;
            ArmStretchMath.SolveTwoBone(shoulder, l1, l2, target, pole, out Vector3 elbow, out Vector3 end);
            a.Upper.rotation = Quaternion.FromToRotation(elbowNow - shoulder, elbow - shoulder) * a.Upper.rotation;
            Vector3 elbowAfter = a.Lower.position, wristAfter = a.Hand.position;
            a.Lower.rotation = Quaternion.FromToRotation(wristAfter - elbowAfter, end - elbowAfter) * a.Lower.rotation;
            a.Hand.rotation = weight < 1f ? Quaternion.Slerp(a.Hand.rotation, handRotation, weight) : handRotation;
            return Vector3.Distance(a.Hand.position, target);
        }

        /// <summary>Curls the fingers (0 flat .. 1 fist) over their rest pose, blended over the current pose by weight.
        /// The sausage rig curls toward the palm around each joint's local +X; the thumb folds less.</summary>
        public void Curl(Side side, float curl, float weight, float maxDegrees = 80f)
        {
            var a = Arms[(int)side];
            weight = Mathf.Clamp01(weight);
            if (weight <= 0f) return;
            curl = Mathf.Clamp01(curl);
            for (int i = 0; i < a.Fingers.Length; i++)
            {
                float deg = a.Thumb[i] ? maxDegrees * 0.45f * (a.Segment[i] == 1 ? 0.5f : 1f)
                                       : maxDegrees * (a.Segment[i] == 1 ? 0.85f : a.Segment[i] == 2 ? 1.05f : 0.8f);
                Quaternion goal = a.FingerRest[i] * Quaternion.AngleAxis(curl * deg, Vector3.right);
                a.Fingers[i].localRotation = weight < 1f ? Quaternion.Slerp(a.Fingers[i].localRotation, goal, weight) : goal;
            }
        }

        /// <summary>Copies the upper arm and forearm poses to their helpers with the stretch along the bone and the
        /// thinner (or, squashed, fatter) cross-section. Call every frame after the bones are final.</summary>
        public void SyncHelpers(float rightStretch = 1f, float rightThickness = 1f, float leftStretch = 1f, float leftThickness = 1f)
        {
            Sync(Arms[0], rightStretch, rightThickness);
            Sync(Arms[1], leftStretch, leftThickness);
        }

        private static void Sync(Arm a, float stretch, float thickness)
        {
            if (a == null || a.UpperHelper == null || a.LowerHelper == null) return;
            var scale = new Vector3(thickness, stretch, thickness) * a.HelperUnit;
            a.UpperHelper.SetPositionAndRotation(a.Upper.position, a.Upper.rotation);
            a.UpperHelper.localScale = scale;
            a.LowerHelper.SetPositionAndRotation(a.Lower.position, a.Lower.rotation);
            a.LowerHelper.localScale = scale;
            if (a.CuffHelper != null)
            {
                a.CuffHelper.SetPositionAndRotation(a.Hand.position, a.Lower.rotation * a.HandRestRotation);
                a.CuffHelper.localScale = Vector3.one * a.HelperUnit;
            }
        }
    }
}
