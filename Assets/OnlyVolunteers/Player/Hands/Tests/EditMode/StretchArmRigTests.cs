using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands.Tests
{
    /// <summary>The stretch rig on a synthetic Mixamo-named skeleton built like the sausage's (rig root scaled 100 and
    /// turned -90° about X, bones along local +Y in centimetre-scale units).</summary>
    public sealed class StretchArmRigTests
    {
        private readonly List<Object> made = new List<Object>();
        private GameObject root;
        private SkinnedMeshRenderer skin;

        [SetUp]
        public void Build()
        {
            root = new GameObject("TestSausage");
            made.Add(root);
            var rig = Child(root.transform, "Buddy_Rig_Mixamo65", Vector3.zero);
            rig.localScale = Vector3.one * 100f;
            rig.localRotation = Quaternion.Euler(270f, 0f, 0f);
            var hips = Child(rig, "mixamorig:Hips", new Vector3(0f, 0f, 0.0082f));
            hips.rotation = Quaternion.identity;
            var spine = Child(hips, "mixamorig:Spine2", new Vector3(0f, 0.0026f, 0f));
            var bones = new List<Transform> { hips, spine };
            foreach (var side in new[] { "Right", "Left" })
            {
                float x = side == "Right" ? 1f : -1f;
                var shoulder = Child(spine, "mixamorig:" + side + "Shoulder", new Vector3(0.0006f * x, 0.0008f, 0f));
                var arm = Child(shoulder, "mixamorig:" + side + "Arm", Vector3.zero);
                arm.position = new Vector3(0.2f * x, 1.166f, 0f);
                arm.rotation = Quaternion.LookRotation(Vector3.forward, Vector3.down); // hanging down: +Y points down
                var fore = Child(arm, "mixamorig:" + side + "ForeArm", new Vector3(0f, 0.0023f, 0f));
                var hand = Child(fore, "mixamorig:" + side + "Hand", new Vector3(0f, 0.0021f, 0f));
                var middle = Child(hand, "mixamorig:" + side + "HandMiddle1", new Vector3(0f, 0.001f, 0f));
                var middle2 = Child(middle, "mixamorig:" + side + "HandMiddle2", new Vector3(0f, 0.0002f, 0f));
                Child(middle2, "mixamorig:" + side + "HandMiddle4", new Vector3(0f, 0.0002f, 0f));
                bones.AddRange(new[] { shoulder, arm, fore, hand, middle, middle2 });
            }
            var skinGo = new GameObject("Top_01_LOD0");
            made.Add(skinGo);
            skinGo.transform.SetParent(root.transform, false);
            skin = skinGo.AddComponent<SkinnedMeshRenderer>();
            skin.bones = bones.ToArray();
            skin.rootBone = hips;
        }

        [TearDown]
        public void Clean()
        {
            foreach (var o in made) if (o != null) Object.DestroyImmediate(o);
            made.Clear();
        }

        private static Transform Child(Transform parent, string name, Vector3 local)
        {
            var t = new GameObject(name).transform;
            t.SetParent(parent, false);
            t.localPosition = local;
            return t;
        }

        [Test]
        public void Bind_FindsArms_MakesHelpers_RepointsTheSkin()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            Assert.IsNotNull(rig);
            Assert.AreEqual(1, rig.PatchedRenderers);
            var right = rig[StretchArmRigV01.Side.Right];
            var bones = skin.bones;
            CollectionAssert.DoesNotContain(bones, right.Upper);
            CollectionAssert.DoesNotContain(bones, right.Lower);
            CollectionAssert.Contains(bones, right.UpperHelper);
            CollectionAssert.Contains(bones, right.LowerHelper);
            CollectionAssert.Contains(bones, right.Hand, "the hand stays the real bone (keeps its size)");
            Assert.AreEqual(0.44f, rig.RestReach(StretchArmRigV01.Side.Right), 1e-3f);
            Assert.Greater(right.Fingers.Length, 0, "fingers found");
            Assert.Less(Vector3.Distance(right.UpperHelper.position, right.Upper.position), 1e-5f);
            Assert.Less(Vector3.Distance(right.UpperHelper.lossyScale, right.Upper.lossyScale), 1e-3f, "at rest the helper equals the bone");
        }

        [Test]
        public void Solve_Reachable_PutsTheWristOnTarget_WithoutStretch()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var side = StretchArmRigV01.Side.Right;
            Vector3 shoulder = rig.ShoulderPosition(side);
            Vector3 target = shoulder + new Vector3(0.05f, 0.05f, 0.35f);
            float shortBy = rig.Solve(side, target, Quaternion.identity, shoulder + new Vector3(0.5f, -1f, 0f), 1f, 1f);
            Assert.Less(shortBy, 1e-3f);
            Assert.Less(Vector3.Distance(rig[side].Hand.position, target), 1e-3f);
            Assert.AreEqual(0.44f, rig.RestReach(side), 1e-3f, "bone lengths unchanged");
            Assert.AreEqual(rig[side].LowerRestLocal, rig[side].Lower.localPosition);
        }

        [Test]
        public void Solve_FarTarget_StretchesTheChain_AndTheHelpersScaleAlongTheBone()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var side = StretchArmRigV01.Side.Right;
            Vector3 shoulder = rig.ShoulderPosition(side);
            Vector3 target = shoulder + new Vector3(0f, 0f, 1.2f);
            float stretch = ArmStretchMath.NeededStretch(1.2f, rig.RestReach(side), 0f, 0f);
            rig.Solve(side, target, Quaternion.identity, shoulder + Vector3.down, stretch, 1f);
            float thickness = ArmStretchMath.Thickness(stretch);
            rig.SyncHelpers(stretch, thickness, 1f, 1f);
            var arm = rig[side];
            Assert.Less(Vector3.Distance(arm.Hand.position, target), 2e-3f, "the stretched arm reaches 1.2 m");
            Assert.AreEqual(stretch, arm.Lower.localPosition.magnitude / arm.LowerRestLocal.magnitude, 1e-3f);
            Assert.Less(Vector3.Distance(Vector3.one * 100f, arm.Hand.lossyScale), 1e-2f, "the original bones are never scaled");
            Vector3 helper = arm.UpperHelper.lossyScale;
            Assert.AreEqual(100f * stretch, helper.y, 0.05f, "long along the bone");
            Assert.AreEqual(100f * thickness, helper.x, 0.05f, "thin across it");
            Assert.Less(Vector3.Distance(arm.LowerHelper.position, arm.Lower.position), 1e-5f);
            Assert.Less(Quaternion.Angle(arm.LowerHelper.rotation, arm.Lower.rotation), 0.01f);
        }

        [Test]
        public void Solve_WeightZero_LeavesTheAnimatedPose()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var side = StretchArmRigV01.Side.Left;
            var arm = rig[side];
            Quaternion before = arm.Upper.rotation;
            Vector3 hand = arm.Hand.position;
            rig.Solve(side, hand + Vector3.forward, Quaternion.identity, Vector3.zero, 3f, 0f);
            Assert.Less(Quaternion.Angle(before, arm.Upper.rotation), 1e-3f);
            Assert.Less(Vector3.Distance(hand, arm.Hand.position), 1e-5f);
        }

        [Test]
        public void ResetToRest_UndoesASolve()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var side = StretchArmRigV01.Side.Right;
            var arm = rig[side];
            Vector3 hand = arm.Hand.position;
            rig.Solve(side, rig.ShoulderPosition(side) + Vector3.forward * 2f, Quaternion.identity, Vector3.zero, 4f, 1f);
            rig.Curl(side, 1f, 1f);
            rig.ResetToRest();
            Assert.Less(Vector3.Distance(hand, arm.Hand.position), 1e-4f);
            for (int i = 0; i < arm.Fingers.Length; i++) Assert.Less(Quaternion.Angle(arm.FingerRest[i], arm.Fingers[i].localRotation), 1e-3f);
        }

        [Test]
        public void Cuffs_RideTheForearm_NotTheBendingHand()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var arm = rig[StretchArmRigV01.Side.Right];
            Assert.AreEqual(2, rig.BindCuffs(skin), "both hands of the sleeve renderer re-pointed to their cuff helpers");
            CollectionAssert.Contains(skin.bones, arm.CuffHelper);
            CollectionAssert.DoesNotContain(skin.bones, arm.Hand);
            rig.SyncHelpers();
            Assert.Less(Vector3.Distance(arm.CuffHelper.position, arm.Hand.position), 1e-5f);
            Assert.Less(Quaternion.Angle(arm.CuffHelper.rotation, arm.Hand.rotation), 0.01f, "at the rest bend: identical skinning");
            Assert.Less(Vector3.Distance(arm.CuffHelper.lossyScale, arm.Hand.lossyScale), 1e-2f);
            // bend the wrist hard: the cuff keeps the forearm's frame, it stays on the wrist joint
            arm.Hand.localRotation = arm.HandRestRotation * Quaternion.Euler(70f, 0f, 25f);
            Vector3 shoulder = rig.ShoulderPosition(StretchArmRigV01.Side.Right);
            rig.Solve(StretchArmRigV01.Side.Right, shoulder + new Vector3(0f, 0f, 0.6f), arm.Hand.rotation, shoulder + Vector3.down, 1.6f, 1f);
            rig.SyncHelpers(1.6f, ArmStretchMath.Thickness(1.6f), 1f, 1f);
            Assert.Less(Vector3.Distance(arm.CuffHelper.position, arm.Hand.position), 1e-4f, "on the (stretched) wrist");
            Assert.Less(Quaternion.Angle(arm.CuffHelper.rotation, arm.Lower.rotation * arm.HandRestRotation), 0.01f, "with the forearm");
            Assert.Greater(Quaternion.Angle(arm.CuffHelper.rotation, arm.Hand.rotation), 20f, "not with the bent hand");
        }

        [Test]
        public void Curl_BendsTheFingersTowardThePalm()
        {
            var rig = StretchArmRigV01.Bind(root.transform);
            var arm = rig[StretchArmRigV01.Side.Right];
            Assert.Greater(arm.Fingers.Length, 0);
            Transform tip = arm.Fingers[arm.Fingers.Length - 1];
            Vector3 palm = arm.Hand.forward; // +Z out of the palm
            float before = Vector3.Dot(tip.position - arm.Hand.position, palm);
            rig.Curl(StretchArmRigV01.Side.Right, 1f, 1f);
            float after = Vector3.Dot(tip.position - arm.Hand.position, palm);
            Assert.Greater(after, before + 0.005f);
        }
    }
}
