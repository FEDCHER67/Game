using System;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using JointKind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.JointKind;
using Part = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Part;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Characters.Npc.Tests
{
    // T0 of the stage-9 design (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §6): the Buddy ragdoll profile is sane and
    // the runtime builds it right. EditMode, a few seconds: the profile's shape, both Buddy prefabs, the colliders in
    // the Idle pose, and a short physics probe in a preview scene that every hinge bends the anatomical way (PhysX
    // measures joint angles against Unity's sense of rotation, so a sign slip would bend knees forward). Step 3: the clip
    // manifest is installed (ClipManifestInstalled).
    public sealed class NpcRagdollProfileTests
    {
        private static NpcRagdollProfile Profile()
        {
            var profile = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>(NpcRagdollBuilder.ProfilePath);
            Assert.IsNotNull(profile, NpcRagdollBuilder.ProfilePath + " is missing (OnlyVolunteers/Characters/Npc/Build Buddy Ragdoll Profile)");
            return profile;
        }

        [Test]
        public void ElevenPartsParentsFirst()
        {
            Part[] parts = Profile().Parts;
            Assert.AreEqual(11, parts.Length, "part count");
            int roots = 0;
            var count = new Dictionary<(Kind, NpcSide), int>();
            for (int i = 0; i < parts.Length; i++)
            {
                Assert.Less(parts[i].Parent, i, $"{parts[i].Name}: parent after it");
                if (parts[i].Parent < 0) roots++;
                Assert.AreEqual(parts[i].Parent < 0, parts[i].Joint == JointKind.None, parts[i].Name + ": a joint exactly when it has a parent");
                var key = (parts[i].Kind, parts[i].Kind >= Kind.UpperArm ? parts[i].Side : NpcSide.Left);
                count[key] = count.TryGetValue(key, out int c) ? c + 1 : 1;
            }
            Assert.AreEqual(1, roots, "exactly one root (the pelvis)");
            Assert.AreEqual(Kind.Pelvis, parts[0].Kind);
            foreach (KeyValuePair<(Kind, NpcSide), int> kv in count) Assert.AreEqual(1, kv.Value, kv.Key.ToString());
            Assert.AreEqual(11, count.Count, "pelvis, chest, head and both arms and legs");
        }

        [Test]
        public void BonesFoundOnBuddyAAndB()
        {
            NpcRagdollProfile profile = Profile();
            foreach (string path in NpcRagdollBuilder.BuddyPrefabs)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Assert.IsNotNull(prefab, path);
                Assert.IsTrue(prefab.TryGetComponent(out NpcRig rig), path + ": no NpcRig");
                Assert.AreSame(profile, rig.Ragdoll, path + ": NpcRig points elsewhere");
                Assert.AreSame(prefab.GetComponent<Animator>(), rig.Animator, path + ": NpcRig's Animator");
                var names = new HashSet<string>();
                foreach (Transform t in prefab.GetComponentsInChildren<Transform>(true)) names.Add(t.name);
                int feet = 0;
                foreach (Part part in profile.Parts)
                {
                    Assert.IsTrue(names.Contains(part.Bone), $"{path}: {part.Bone}");
                    if (string.IsNullOrEmpty(part.BoxBone)) continue;
                    Assert.IsTrue(names.Contains(part.BoxBone), $"{path}: {part.BoxBone}");
                    feet++;
                }
                Assert.AreEqual(2, feet, "both feet have a box");
            }
        }

        [Test]
        public void MassIs28Kg() => Assert.AreEqual(28f, Profile().TotalMass, 0.05f);

        [Test]
        public void AdjacentMassRatioAtMost5()
        {
            Part[] parts = Profile().Parts;
            foreach (Part part in parts)
            {
                if (part.Parent < 0) continue;
                float a = part.Mass, b = parts[part.Parent].Mass;
                Assert.Greater(a, 0f, part.Name);
                Assert.LessOrEqual(Mathf.Max(a, b) / Mathf.Min(a, b), 5f, $"{part.Name} : {parts[part.Parent].Name}");
            }
        }

        [Test]
        public void ShapesArePositive()
        {
            foreach (Part part in Profile().Parts)
            {
                Assert.Greater(part.Radius, 0.02f, part.Name + " radius");
                Assert.GreaterOrEqual(part.Height, part.Radius * 2f, part.Name + " height");
                Assert.IsTrue(part.Direction >= 0 && part.Direction <= 2, part.Name + " direction");
                Assert.AreEqual(1f, part.Up.magnitude, 0.01f, part.Name + " up");
                if (part.Kind == Kind.Calf)
                    Assert.IsTrue(part.BoxSize.x > 0.02f && part.BoxSize.y > 0.02f && part.BoxSize.z > 0.05f, part.Name + " foot box");
            }
        }

        [Test]
        public void LimitsAreOrdered()
        {
            foreach (Part part in Profile().Parts)
            {
                if (part.Joint == JointKind.None) continue;
                Assert.LessOrEqual(part.LowX, 0f, part.Name + ": the reference pose must be inside the limits");
                Assert.GreaterOrEqual(part.HighX, 0f, part.Name);
                Assert.Less(part.LowX, part.HighX, part.Name);
                Assert.IsTrue(part.LowX >= -177f && part.HighX <= 177f, part.Name + " X within +-177");
                Assert.IsTrue(part.LimitY > 0f && part.LimitY <= 177f && part.LimitZ > 0f && part.LimitZ <= 177f, part.Name + " Y/Z");
                Assert.AreEqual(1f, part.Axis.magnitude, 0.01f, part.Name + " axis");
                Assert.AreEqual(1f, part.Secondary.magnitude, 0.01f, part.Name + " secondary");
                Assert.Less(Mathf.Abs(Vector3.Dot(part.Axis, part.Secondary)), 0.05f, part.Name + ": axes not perpendicular");
            }
        }

        [Test]
        public void NoNonAdjacentOverlapInIdle()
        {
            NpcRagdollProfile profile = Profile();
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                foreach (string path in NpcRagdollBuilder.BuddyPrefabs)
                {
                    NpcRagdoll ragdoll = Build(path, scene);
                    var owner = new Dictionary<Collider, int>();
                    for (int i = 0; i < ragdoll.PartCount; i++)
                        foreach (Collider c in ragdoll.BodyOf(i).GetComponentsInChildren<Collider>())
                            if (c.attachedRigidbody == ragdoll.BodyOf(i)) owner[c] = i;
                    Assert.AreEqual(13, owner.Count, path + ": 11 capsules and 2 foot boxes");
                    var colliders = new List<Collider>(owner.Keys);
                    for (int a = 0; a < colliders.Count; a++)
                        for (int b = a + 1; b < colliders.Count; b++)
                        {
                            int pa = owner[colliders[a]], pb = owner[colliders[b]];
                            if (pa == pb || profile.Parts[pa].Parent == pb || profile.Parts[pb].Parent == pa) continue;
                            Collider ca = colliders[a], cb = colliders[b];
                            if (!Physics.ComputePenetration(ca, ca.transform.position, ca.transform.rotation,
                                    cb, cb.transform.position, cb.transform.rotation, out _, out float depth)) continue;
                            Assert.LessOrEqual(depth, 0.03f, $"{path}: {profile.Parts[pa].Name} ({ca.GetType().Name}) overlaps {profile.Parts[pb].Name} ({cb.GetType().Name}) by {depth:0.000} m");
                        }
                    ragdoll.Deactivate();
                    Assert.AreEqual(0, ragdoll.GetComponentsInChildren<Rigidbody>().Length, path + ": bodies left after Deactivate");
                    Assert.AreEqual(0, ragdoll.GetComponentsInChildren<Joint>().Length, path + ": joints left after Deactivate");
                    Assert.AreEqual(0, ragdoll.GetComponentsInChildren<Collider>().Length, path + ": colliders left after Deactivate");
                    Object.DestroyImmediate(ragdoll.gameObject);
                }
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // Each hinge driven hard both ways for a second (everything else held still, no gravity): it must bend the
        // anatomical way up to about its flexion limit, and stop near its extension limit.
        [Test]
        public void HingesBendTheAnatomicalWay()
        {
            NpcRagdollProfile profile = Profile();
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                NpcRagdoll ragdoll = Build(NpcRagdollBuilder.BuddyPrefabs[0], scene);
                PhysicsScene physics = scene.GetPhysicsScene();
                Transform root = ragdoll.transform;
                Transform Bone(string name)
                {
                    foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                        if (t.name == "mixamorig:" + name) return t;
                    throw new InvalidOperationException(name);
                }
                Transform hips = Bone("Hips"), spine = Bone("Spine"), spine1 = Bone("Spine1"), neck = Bone("Neck");
                // (part, parent segment, this segment); anatomical angle = signed, about the part's flexion axis.
                var checks = new (Kind kind, Func<Vector3> parentDir, Func<Vector3> childDir)[]
                {
                    (Kind.Calf, () => Bone("LeftLeg").position - Bone("LeftUpLeg").position, () => Bone("LeftFoot").position - Bone("LeftLeg").position),
                    (Kind.ForeArm, () => Bone("LeftForeArm").position - Bone("LeftArm").position, () => Bone("LeftHand").position - Bone("LeftForeArm").position),
                    (Kind.Thigh, () => hips.position - spine.position, () => Bone("LeftLeg").position - Bone("LeftUpLeg").position),
                    (Kind.Chest, () => spine.position - hips.position, () => neck.position - spine1.position),
                };
                // Anatomical limits from the design table (§2.2): flexion max, extension min.
                var design = new Dictionary<Kind, (float low, float high)>
                {
                    [Kind.Calf] = (0f, 135f), [Kind.ForeArm] = (0f, 140f), [Kind.Thigh] = (-20f, 110f), [Kind.Chest] = (-25f, 55f),
                };
                foreach ((Kind kind, Func<Vector3> parentDir, Func<Vector3> childDir) in checks)
                {
                    int part = profile.IndexOf(kind, NpcSide.Left);
                    Rigidbody body = ragdoll.BodyOf(part);
                    Vector3 Flex() => body.rotation * profile.Parts[part].Axis;
                    float Angle()
                    {
                        Vector3 f = Flex();
                        return Vector3.SignedAngle(Vector3.ProjectOnPlane(parentDir(), f), Vector3.ProjectOnPlane(childDir(), f), f);
                    }
                    for (int i = 0; i < ragdoll.PartCount; i++)
                    {
                        Rigidbody rb = ragdoll.BodyOf(i);
                        rb.useGravity = false;
                        rb.isKinematic = i != part && !IsBelow(profile, i, part);
                        if (!rb.isKinematic) rb.linearVelocity = rb.angularVelocity = Vector3.zero;
                    }
                    float start = Angle();
                    float flexed = Drive(physics, body, Flex, 3f, Angle);
                    float extended = Drive(physics, body, Flex, -3f, Angle);
                    (float low, float high) = design[kind];
                    string what = $"{profile.Parts[part].Name}: Idle {start:0} deg, driven to {flexed:0} / {extended:0} (design {low:0}..{high:0})";
                    Debug.Log("[NpcRagdollProfileTests] " + what);
                    Assert.GreaterOrEqual(flexed, high - 20f, what + ": does not flex the anatomical way");
                    Assert.LessOrEqual(flexed, high + 10f, what + ": flexes past its limit");
                    Assert.GreaterOrEqual(extended, low - 10f, what + ": extends past its limit");
                    Assert.LessOrEqual(extended, low + 12f, what + ": does not extend");
                }
                ragdoll.Deactivate();
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // Stage 9 step 2, assist A4: the carry tone of a split pair (SetTone(2)) drives the hips toward CarryHipFlexion
        // degrees of flexion and the waist toward the Idle line. A sign slip in the drive's joint-space target would extend
        // the hips instead. The left leg alone is free (no gravity), the rest held still; the waist is checked the same way
        // from a bend.
        [Test]
        public void CarryToneFlexesTheHipsAndStraightensTheWaist()
        {
            NpcRagdollProfile profile = Profile();
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                NpcRagdoll ragdoll = Build(NpcRagdollBuilder.BuddyPrefabs[0], scene);
                PhysicsScene physics = scene.GetPhysicsScene();
                Transform root = ragdoll.transform;
                Transform Bone(string name)
                {
                    foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                        if (t.name == "mixamorig:" + name) return t;
                    throw new InvalidOperationException(name);
                }
                Transform hips = Bone("Hips"), spine = Bone("Spine"), spine1 = Bone("Spine1"), neck = Bone("Neck");
                int thigh = profile.IndexOf(Kind.Thigh, NpcSide.Left), chest = profile.IndexOf(Kind.Chest);
                float Angle(int part, Vector3 parentDir, Vector3 childDir)
                {
                    Vector3 f = ragdoll.BodyOf(part).rotation * profile.Parts[part].Axis;
                    return Vector3.SignedAngle(Vector3.ProjectOnPlane(parentDir, f), Vector3.ProjectOnPlane(childDir, f), f);
                }
                float Hip() => Angle(thigh, hips.position - spine.position, Bone("LeftLeg").position - Bone("LeftUpLeg").position);
                float Waist() => Angle(chest, spine.position - hips.position, neck.position - spine1.position);

                // The hip: only the left leg free.
                for (int i = 0; i < ragdoll.PartCount; i++)
                {
                    Rigidbody rb = ragdoll.BodyOf(i);
                    rb.useGravity = false;
                    rb.isKinematic = i != thigh && !IsBelow(profile, i, thigh);
                    if (!rb.isKinematic) rb.linearVelocity = rb.angularVelocity = Vector3.zero;
                }
                float hip0 = Hip();
                ragdoll.SetTone(2);
                for (int step = 0; step < 90; step++) physics.Simulate(1f / 60f);
                float hip1 = Hip();
                string hipWhat = $"hip: Idle {hip0:0.0} deg, carried {hip1:0.0} deg (target +{profile.CarryHipFlexion:0} flexion)";
                Debug.Log("[NpcRagdollProfileTests] " + hipWhat);
                Assert.AreEqual(profile.CarryHipFlexion, hip1 - hip0, 4f, hipWhat);

                // The waist: the chest free (the head and arms with it), bent forward 30 degrees, then the carry tone.
                ragdoll.SetTone(0);
                for (int i = 0; i < ragdoll.PartCount; i++)
                {
                    Rigidbody rb = ragdoll.BodyOf(i);
                    rb.isKinematic = i != chest && !IsBelow(profile, i, chest);
                    if (!rb.isKinematic) rb.linearVelocity = rb.angularVelocity = Vector3.zero;
                }
                float waist0 = Waist();
                Rigidbody chestBody = ragdoll.BodyOf(chest);
                Vector3 flex = chestBody.rotation * profile.Parts[chest].Axis;
                for (int step = 0; step < 30; step++)
                {
                    chestBody.angularVelocity = flex * 1f; // ~30 degrees of flexion in half a second
                    physics.Simulate(1f / 60f);
                }
                chestBody.angularVelocity = Vector3.zero;
                physics.Simulate(1f / 60f);
                float bent = Waist();
                ragdoll.SetTone(2);
                for (int step = 0; step < 90; step++) physics.Simulate(1f / 60f);
                float waist1 = Waist();
                string waistWhat = $"waist: Idle {waist0:0.0} deg, bent {bent:0.0}, carried {waist1:0.0}";
                Debug.Log("[NpcRagdollProfileTests] " + waistWhat);
                Assert.Greater(bent - waist0, 15f, waistWhat + ": the bend did not happen");
                Assert.Less(Mathf.Abs(waist1 - waist0), 5f, waistWhat + ": the carry tone does not straighten the waist");
                ragdoll.Deactivate();
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // Stage 9 step 4 (NpcStruggle): the shoulder targets point the arm where the struggle asks. The left arm alone is
        // free (no gravity), the rest held still; driven hard toward three directions of the chest's frame (over the head:
        // the crawl's reach; out in front: the held flail; down by the hip: the crawl's pull) it must end within 15 degrees
        // of each. A slip in the joint-space formula (target = W^-1 · rel^-1 · reference · W) would swing it elsewhere.
        [Test]
        public void StruggleShoulderTargetsPointTheArm()
        {
            NpcRagdollProfile profile = Profile();
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                NpcRagdoll ragdoll = Build(NpcRagdollBuilder.BuddyPrefabs[0], scene);
                PhysicsScene physics = scene.GetPhysicsScene();
                int upper = profile.IndexOf(Kind.UpperArm, NpcSide.Left), chest = profile.IndexOf(Kind.Chest);
                Part arm = profile.Parts[upper];
                for (int i = 0; i < ragdoll.PartCount; i++)
                {
                    Rigidbody rb = ragdoll.BodyOf(i);
                    rb.useGravity = false;
                    rb.isKinematic = i != upper && !IsBelow(profile, i, upper);
                    if (!rb.isKinematic) rb.linearVelocity = rb.angularVelocity = Vector3.zero;
                }
                ConfigurableJoint joint = ragdoll.JointOf(upper);
                Quaternion frame = NpcStruggle.JointFrame(joint.axis, joint.secondaryAxis);
                Rigidbody chestBody = ragdoll.BodyOf(chest), armBody = ragdoll.BodyOf(upper);
                ragdoll.DrivesTaken = true;
                foreach (Vector3 dir in new[] { new Vector3(-0.35f, 1f, 0f), new Vector3(-0.3f, 0.1f, 1f), new Vector3(-0.55f, -0.85f, 0f) })
                {
                    Vector3 want = (Quaternion.Inverse(profile.Parts[chest].PoseRotation) * dir).normalized;
                    ragdoll.Drive(upper, NpcStruggle.ShoulderTarget(arm, frame, want), 400f, 40f, 1000f);
                    for (int step = 0; step < 90; step++) physics.Simulate(1f / 60f);
                    Vector3 got = Quaternion.Inverse(chestBody.rotation) * (armBody.rotation * arm.Axis.normalized);
                    float miss = Vector3.Angle(got, want);
                    string what = $"left arm driven toward {dir} (chest frame): ended {miss:0.0} deg off";
                    Debug.Log("[NpcRagdollProfileTests] " + what);
                    Assert.Less(miss, 15f, what);
                }
                ragdoll.DrivesTaken = false;
                ragdoll.Deactivate();
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // ---------- Step 3: the clip manifest (T0 of §6) ----------

        private const string ManifestPath = "Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/clips.json";

        [Serializable]
        private sealed class ManifestShape
        {
            public ClipShape[] clips = Array.Empty<ClipShape>();
            public LinkShape[] links = Array.Empty<LinkShape>();
            public SeatShape seat = new();
        }

        [Serializable]
        private sealed class ClipShape
        {
            public string role = "", state = "", file = "";
            public bool loop;
            public float seconds, stable;
            public float[] hipsStart = Array.Empty<float>();
        }

        [Serializable]
        private sealed class LinkShape
        {
            public string from = "", to = "";
        }

        [Serializable]
        private sealed class SeatShape
        {
            public float yaw;
        }

        // Every clip of clips.json is installed (GreyboxBuddySetup.InstallClips): the Buddy controller plays that clip (step
        // 5: the generated controller, in any layer or blend tree), every curve of it binds on Buddy A and B (0 missing
        // paths), looping clips close exactly (frame 0 = the last frame within 0.5 degrees on every bone), the links exist,
        // and the profile carries the manifest's numbers (every clip by its role) and a seat layout.
        [Test]
        public void ClipManifestInstalled()
        {
            Assert.IsTrue(System.IO.File.Exists(ManifestPath), ManifestPath);
            ManifestShape manifest = JsonUtility.FromJson<ManifestShape>(System.IO.File.ReadAllText(ManifestPath));
            Assert.Greater(manifest.clips.Length, 0, "clips.json lists no clips");
            NpcRagdollProfile profile = Profile();
            var prefabA = AssetDatabase.LoadAssetAtPath<GameObject>(NpcRagdollBuilder.BuddyPrefabs[0]);
            var controller = prefabA.GetComponent<Animator>().runtimeAnimatorController as UnityEditor.Animations.AnimatorController;
            Assert.IsNotNull(controller, "Buddy A has no AnimatorController");
            var states = new Dictionary<string, UnityEditor.Animations.AnimatorState>();
            foreach (UnityEditor.Animations.ChildAnimatorState child in controller.layers[0].stateMachine.states)
                states[child.state.name] = child.state;
            var played = new Dictionary<string, AnimationClip>();
            foreach (UnityEditor.Animations.AnimatorControllerLayer layer in controller.layers)
                foreach (UnityEditor.Animations.ChildAnimatorState child in layer.stateMachine.states)
                    Collect(child.state.motion, played);
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                GameObject buddy = NpcRagdollBuilder.InstantiateSampled(NpcRagdollBuilder.BuddyPrefabs[0], scene);
                foreach (ClipShape entry in manifest.clips)
                {
                    Assert.IsTrue(played.TryGetValue(entry.state, out AnimationClip clip), $"the controller does not play {entry.state}");
                    if (!string.IsNullOrEmpty(entry.role))
                        Assert.IsNotNull(profile.Role(entry.role), $"the profile has no clip for the role {entry.role}");
                    StringAssert.EndsWith(entry.file, AssetDatabase.GetAssetPath(clip), $"{entry.state}: from the wrong file");
                    Assert.AreEqual(entry.loop, clip.isLooping, $"{entry.state}: loop");
                    if (entry.seconds > 0f) Assert.AreEqual(entry.seconds, clip.length, 0.05f, $"{entry.state}: length");
                    foreach (string path in NpcRagdollBuilder.BuddyPrefabs)
                    {
                        Transform root = AssetDatabase.LoadAssetAtPath<GameObject>(path).transform;
                        int missing = 0;
                        string first = null;
                        foreach (EditorCurveBinding binding in AnimationUtility.GetCurveBindings(clip))
                        {
                            if (root.Find(binding.path) != null || binding.path.Length == 0) continue;
                            missing++;
                            first ??= binding.path;
                        }
                        Assert.AreEqual(0, missing, $"{entry.state} on {path}: {missing} curves bind to nothing (first: {first})");
                    }
                    if (!entry.loop) continue;
                    var start = new Dictionary<Transform, Quaternion>();
                    clip.SampleAnimation(buddy, 0f);
                    foreach (Transform t in buddy.GetComponentsInChildren<Transform>(true)) start[t] = t.localRotation;
                    clip.SampleAnimation(buddy, clip.length);
                    float worst = 0f;
                    foreach (KeyValuePair<Transform, Quaternion> kv in start) worst = Mathf.Max(worst, Quaternion.Angle(kv.Value, kv.Key.localRotation));
                    Assert.LessOrEqual(worst, 0.5f, $"{entry.state}: loop seam {worst:0.00} degrees");
                }
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
            foreach (LinkShape link in manifest.links)
            {
                Assert.IsTrue(states.TryGetValue(link.from, out UnityEditor.Animations.AnimatorState from), $"link from {link.from}: no state");
                bool found = false;
                foreach (UnityEditor.Animations.AnimatorStateTransition t in from.transitions) found |= t.destinationState != null && t.destinationState.name == link.to;
                Assert.IsTrue(found, $"no link {link.from} -> {link.to}");
            }
            foreach (ClipShape entry in manifest.clips)
            {
                NpcRagdollProfile.ClipInfo info = entry.role switch
                {
                    "GetUpBack" => profile.GetUpBack,
                    "GetUpBelly" => profile.GetUpBelly,
                    "SitUp" => profile.SitUp,
                    "SitIdle" => profile.SitIdle,
                    "Knock" => profile.Knock,
                    "Scramble" => profile.Scramble,
                    "JumpOut" => profile.JumpOut,
                    _ => null,
                };
                if (info == null) continue;
                Assert.AreEqual(entry.state, info.State, entry.role + " state");
                Assert.AreEqual(entry.stable, info.Stable, 1e-4f, entry.role + " stable");
                if (entry.hipsStart.Length == 3) Assert.AreEqual(entry.hipsStart[1], info.HipsStart.y, 1e-3f, entry.role + " hipsStart");
            }
            Assert.IsTrue(profile.HasGetUps && profile.HasSeat, "the profile lacks the get-up or seat clips");
            Assert.AreEqual(manifest.seat.yaw, profile.SeatYaw, 1e-3f, "seat yaw");
            Assert.Less(profile.SeatMin.x, profile.SeatMax.x, "seat footprint x");
            Assert.Less(profile.SeatMin.y, profile.SeatMax.y, "seat footprint z");
        }

        // Every clip a state plays, through blend trees.
        private static void Collect(Motion motion, Dictionary<string, AnimationClip> clips)
        {
            if (motion is AnimationClip clip) clips[clip.name] = clip;
            else if (motion is UnityEditor.Animations.BlendTree tree)
                foreach (UnityEditor.Animations.ChildMotion child in tree.children) Collect(child.motion, clips);
        }

        // Spins the body about its flexion axis for a second (the joint limit stops it); the angle at the end.
        private static float Drive(PhysicsScene physics, Rigidbody body, Func<Vector3> flex, float speed, Func<float> angle)
        {
            for (int step = 0; step < 60; step++)
            {
                body.angularVelocity = flex() * speed;
                physics.Simulate(1f / 60f);
            }
            body.angularVelocity = Vector3.zero;
            physics.Simulate(1f / 60f);
            return angle();
        }

        private static bool IsBelow(NpcRagdollProfile profile, int part, int ancestor)
        {
            for (int p = profile.Parts[part].Parent; p >= 0; p = profile.Parts[p].Parent)
                if (p == ancestor) return true;
            return false;
        }

        // A Buddy in its sampled Idle pose in 'scene' with the ragdoll built the runtime's way.
        private static NpcRagdoll Build(string prefabPath, Scene scene)
        {
            GameObject buddy = NpcRagdollBuilder.InstantiateSampled(prefabPath, scene);
            NpcRagdoll ragdoll = buddy.AddComponent<NpcRagdoll>();
            Assert.IsTrue(ragdoll.Ready, prefabPath + ": " + ragdoll.Problem);
            ragdoll.Activate(Vector3.zero, Vector3.zero);
            Assert.IsTrue(ragdoll.Active, prefabPath + ": not built");
            Assert.AreEqual(11, buddy.GetComponentsInChildren<Rigidbody>().Length, prefabPath + ": bodies");
            Assert.AreEqual(10, buddy.GetComponentsInChildren<ConfigurableJoint>().Length, prefabPath + ": joints");
            Assert.AreEqual(28f, SumMass(buddy), 0.05f, prefabPath + ": mass");
            return ragdoll;
        }

        private static float SumMass(GameObject go)
        {
            float m = 0f;
            foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>()) m += rb.mass;
            return m;
        }
    }
}
