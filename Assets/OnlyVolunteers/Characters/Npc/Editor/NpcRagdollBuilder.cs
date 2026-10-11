using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;
using JointKind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.JointKind;
using Handle = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Handle;
using Part = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Part;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Characters.Npc
{
    // OnlyVolunteers/Characters/Npc/Build Buddy Ragdoll Profile (re-runnable): measures the 11 ragdoll parts on
    // SausageBuddy_A and writes Data/Buddy_RagdollProfile.asset (only Parts; the tuned settings stay), then puts NpcRig on
    // both Buddy prefabs. Design: docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §2.1-§2.2, §2.6.
    // - The prefab is instantiated in a preview scene and its Idle clip sampled at frame 0 FIRST: the v04 FBX stores a
    //   pose with the Hips ~11.5 m below the root, so nothing reads the prefab's own pose (§1.5).
    // - Bone axes come from child bone positions; capsule radii from the skinned vertices each part owns (dominant bone
    //   weight, walked up to the part's bone): the 70th percentile of their distance to the part's axis segment, so
    //   clothing flaps do not inflate them (the pelvis and chest: to their left-right line). Limb capsules reach 0.4 r
    //   past each joint; the forearm reaches the fingertips, the head runs from the neck base to the top; the pelvis and
    //   chest lie left-right across the 5th-95th percentile width. Foot boxes: twice the 70th percentile offset per axis, lying flat in the character frame. Measured values
    //   are clamped to 0.6-1.6x the design's starting values (the log prints both).
    // - Masses, joint limits, handles and hints are the design's (§2.1, §2.2). Hinge limits are stored relative to the
    //   Idle pose (its own bend subtracted: the Buddy's Idle elbows are bent ~14 degrees); the shoulders' cone is centred
    //   on the arms held out sideways (T-pose), so a body dragged by a wrist can have its arm overhead.
    public static class NpcRagdollBuilder
    {
        public const string ProfilePath = "Assets/OnlyVolunteers/Characters/Npc/Data/Buddy_RagdollProfile.asset";
        public static readonly string[] BuddyPrefabs =
        {
            "Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_A.prefab",
            "Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_B.prefab",
        };
        private const string Prefix = "mixamorig:";
        private const float LimbCapReach = 0.4f; // of the radius, past each joint
        private const float ClampLow = 0.6f, ClampHigh = 1.6f;

        // The design table: kind, side, bone, parent, mass (kg), handle, hint, joint, low/high (flexion, degrees from
        // anatomical zero), Y/Z (hinge: twist/side; ball: cone), flexion sign (+1: about the character's right), the
        // child bone that gives the axis, starting radius and length (m).
        private sealed class Spec
        {
            public Kind Kind;
            public NpcSide Side;
            public string Bone, Child;
            public int Parent;
            public float Mass;
            public Handle Handle;
            public string Hint;
            public JointKind Joint;
            public float Low, High, LimitY, LimitZ, Flex;
            public float Radius, Length;
        }

        private static Spec S(Kind kind, NpcSide side, string bone, string child, int parent, float mass, Handle handle, string hint,
            JointKind joint, float low, float high, float y, float z, float flex, float radius, float length) =>
            new()
            {
                Kind = kind, Side = side, Bone = Prefix + bone, Child = Prefix + child, Parent = parent, Mass = mass,
                Handle = handle, Hint = hint, Joint = joint, Low = low, High = high, LimitY = y, LimitZ = z, Flex = flex,
                Radius = radius, Length = length,
            };

        private static readonly Spec[] Specs =
        {
            S(Kind.Pelvis, NpcSide.Left, "Hips", "Spine", -1, 5.0f, Handle.Bad, "таз", JointKind.None, 0, 0, 0, 0, 0, 0.13f, 0.34f),
            S(Kind.Chest, NpcSide.Left, "Spine1", "Neck", 0, 5.6f, Handle.Good, "грудь", JointKind.Hinge, -25, 55, 20, 25, 1, 0.14f, 0.42f),
            S(Kind.Head, NpcSide.Left, "Head", "HeadTop_End", 1, 2.4f, Handle.Good, "голову", JointKind.Hinge, -40, 50, 40, 30, 1, 0.12f, 0.62f),
            S(Kind.UpperArm, NpcSide.Left, "LeftArm", "LeftForeArm", 1, 1.3f, Handle.Good, "плечо", JointKind.Ball, -50, 50, 85, 85, 0, 0.065f, 0.28f),
            S(Kind.ForeArm, NpcSide.Left, "LeftForeArm", "LeftHand", 3, 1.0f, Handle.Good, "руку", JointKind.Hinge, 0, 140, 30, 10, -1, 0.06f, 0.44f),
            S(Kind.UpperArm, NpcSide.Right, "RightArm", "RightForeArm", 1, 1.3f, Handle.Good, "плечо", JointKind.Ball, -50, 50, 85, 85, 0, 0.065f, 0.28f),
            S(Kind.ForeArm, NpcSide.Right, "RightForeArm", "RightHand", 5, 1.0f, Handle.Good, "руку", JointKind.Hinge, 0, 140, 30, 10, -1, 0.06f, 0.44f),
            S(Kind.Thigh, NpcSide.Left, "LeftUpLeg", "LeftLeg", 0, 3.0f, Handle.Medium, "бедро", JointKind.Hinge, -20, 110, 25, 35, -1, 0.09f, 0.44f),
            S(Kind.Calf, NpcSide.Left, "LeftLeg", "LeftFoot", 7, 2.2f, Handle.Good, "ногу", JointKind.Hinge, 0, 135, 5, 5, 1, 0.07f, 0.36f),
            S(Kind.Thigh, NpcSide.Right, "RightUpLeg", "RightLeg", 0, 3.0f, Handle.Medium, "бедро", JointKind.Hinge, -20, 110, 25, 35, -1, 0.09f, 0.44f),
            S(Kind.Calf, NpcSide.Right, "RightLeg", "RightFoot", 9, 2.2f, Handle.Good, "ногу", JointKind.Hinge, 0, 135, 5, 5, 1, 0.07f, 0.36f),
        };

        // ---------- Menu ----------

        [MenuItem("OnlyVolunteers/Characters/Npc/Build Buddy Ragdoll Profile")]
        public static void BuildMenu()
        {
            NpcRagdollProfile profile = Build(out string report);
            Debug.Log(report);
            if (profile != null) EnsureRigOnPrefabs();
        }

        /// <summary>Measures SausageBuddy_A in its sampled Idle pose and writes the profile's Parts (asset created if
        /// missing). Null (and the reason in the report) if the rig lacks a bone.</summary>
        public static NpcRagdollProfile Build(out string report)
        {
            var log = new StringBuilder("[NpcRagdollBuilder] Buddy ragdoll profile (Idle frame 0 of SausageBuddy_A):\n");
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                GameObject buddy = InstantiateSampled(BuddyPrefabs[0], scene);
                Part[] parts = Measure(buddy, log);
                if (parts == null)
                {
                    report = log.ToString();
                    return null;
                }
                NpcRagdollProfile profile = LoadOrCreateProfile();
                profile.Parts = parts;
                EditorUtility.SetDirty(profile);
                AssetDatabase.SaveAssets();
                log.Append(Inv($"total mass {profile.TotalMass:0.00} kg -> {ProfilePath}"));
                report = log.ToString();
                return profile;
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        /// <summary>A plain copy of a character prefab in 'scene' at the origin, with its Idle clip sampled at frame 0
        /// (the only trustworthy pose of the Buddy v04 FBX).</summary>
        public static GameObject InstantiateSampled(string prefabPath, Scene scene)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null) throw new InvalidOperationException("Missing prefab " + prefabPath);
            var go = (GameObject)Object.Instantiate(prefab);
            SceneManager.MoveGameObjectToScene(go, scene);
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            AnimationClip idle = null;
            if (go.TryGetComponent(out Animator animator) && animator.runtimeAnimatorController != null)
                foreach (AnimationClip clip in animator.runtimeAnimatorController.animationClips)
                    if (clip != null && clip.name == "Idle") idle = clip;
            if (idle == null) throw new InvalidOperationException(prefabPath + " has no Idle clip in its Animator controller");
            idle.SampleAnimation(go, 0f);
            return go;
        }

        // ---------- Measuring ----------

        /// <summary>The 11 parts measured on an instance in its Idle pose at the origin (character frame = world).</summary>
        public static Part[] Measure(GameObject instance, StringBuilder log)
        {
            var byName = new Dictionary<string, Transform>();
            foreach (Transform t in instance.GetComponentsInChildren<Transform>(true))
                if (!byName.ContainsKey(t.name)) byName.Add(t.name, t);
            string[] extra = { "Spine", "Neck", "LeftHand", "RightHand", "LeftFoot", "RightFoot" };
            int n = Specs.Length;
            var bones = new Transform[n];
            var children = new Transform[n];
            for (int i = 0; i < n; i++)
            {
                if (!byName.TryGetValue(Specs[i].Bone, out bones[i]) || !byName.TryGetValue(Specs[i].Child, out children[i]))
                {
                    log.AppendLine($"FAIL: {Specs[i].Bone} or {Specs[i].Child} missing");
                    return null;
                }
            }
            foreach (string e in extra)
                if (!byName.ContainsKey(Prefix + e))
                {
                    log.AppendLine($"FAIL: {Prefix}{e} missing");
                    return null;
                }
            Transform neck = byName[Prefix + "Neck"], spine = byName[Prefix + "Spine"];
            Transform leftFoot = byName[Prefix + "LeftFoot"], rightFoot = byName[Prefix + "RightFoot"];
            int head = Index(Kind.Head, NpcSide.Left), pelvisIndex = Index(Kind.Pelvis, NpcSide.Left), chestIndex = Index(Kind.Chest, NpcSide.Left);

            // Skinned vertices (world = character frame) by owning part; feet separately.
            var verts = new List<Vector3>[n];
            var feet = new List<Vector3>[n];
            for (int i = 0; i < n; i++)
            {
                verts[i] = new List<Vector3>();
                feet[i] = new List<Vector3>();
            }
            foreach (SkinnedMeshRenderer smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null) continue;
                var baked = new Mesh();
                smr.BakeMesh(baked, true);
                Vector3[] v = baked.vertices;
                BoneWeight[] weights = smr.sharedMesh.boneWeights;
                Transform[] smrBones = smr.bones;
                Matrix4x4 toWorld = smr.transform.localToWorldMatrix;
                for (int k = 0; k < v.Length && k < weights.Length; k++)
                {
                    int bi = weights[k].boneIndex0;
                    Transform b = bi >= 0 && bi < smrBones.Length ? smrBones[bi] : null;
                    if (b == null) continue;
                    int owner = Owner(b, bones, neck, head, leftFoot, rightFoot, out bool foot);
                    if (owner < 0) continue;
                    (foot ? feet : verts)[owner].Add(toWorld.MultiplyPoint3x4(v[k]));
                }
                Object.DestroyImmediate(baked);
            }

            Vector3 right = Vector3.right, up = Vector3.up, forward = Vector3.forward; // the character frame (root at identity)
            Vector3 pelvisUp = (spine.position - bones[pelvisIndex].position).normalized;
            Vector3 chestUp = (neck.position - bones[chestIndex].position).normalized;
            var parts = new Part[n];
            log.AppendLine("part        mass  r (design)     height (design)  centre (bone frame)");
            for (int i = 0; i < n; i++)
            {
                Spec spec = Specs[i];
                Transform bone = bones[i];
                Quaternion toBone = Quaternion.Inverse(bone.rotation);
                var part = new Part
                {
                    Name = spec.Kind + (spec.Kind >= Kind.UpperArm ? (spec.Side == NpcSide.Left ? "_L" : "_R") : ""),
                    Kind = spec.Kind,
                    Side = spec.Side,
                    Bone = spec.Bone,
                    Parent = spec.Parent,
                    Mass = spec.Mass,
                    Handle = spec.Handle,
                    Hint = spec.Hint,
                    Joint = spec.Joint,
                    PosePosition = bone.position,
                    PoseRotation = bone.rotation,
                };
                List<Vector3> own = verts[i];
                float radius, height;
                Vector3 centre, along;
                if (spec.Kind == Kind.Pelvis || spec.Kind == Kind.Chest)
                {
                    // Left-right across the body (a lying body rests on two bars), as wide as the part's vertices.
                    // The radius from the distance to the left-right line (not to the capsule's inner segment, which
                    // shrinks as the radius grows and turns a wide part into a ball).
                    along = right;
                    centre = new Vector3(MidRange(own, right), MidRange(own, up), MidRange(own, forward));
                    height = Range(own, right);
                    radius = Percentile(LineDistances(own, centre, along), 0.7f);
                    part.Up = toBone * (spec.Kind == Kind.Pelvis ? pelvisUp : chestUp);
                }
                else
                {
                    Vector3 near = spec.Kind == Kind.Head ? neck.position : bone.position;
                    along = (children[i].position - bone.position).normalized;
                    Vector3 far = children[i].position;
                    if (spec.Kind == Kind.ForeArm || spec.Kind == Kind.Head)
                        far = near + along * Percentile(Projections(own, near, along), 0.99f); // fingertips, head top
                    // The head's mesh sits a little forward of its bone: centre the axis on its vertices.
                    Vector3 offset = Vector3.zero;
                    if (spec.Kind == Kind.Head)
                    {
                        Vector3 side = Vector3.Cross(along, forward).normalized, front = Vector3.Cross(side, along).normalized;
                        offset = side * (MidRange(own, side) - Vector3.Dot(near, side)) + front * (MidRange(own, front) - Vector3.Dot(near, front));
                    }
                    radius = Percentile(Distances(own, near + offset, far + offset), 0.7f);
                    radius = Clamp(radius, spec.Radius);
                    float reach = spec.Kind == Kind.Head ? 0f : radius * LimbCapReach;
                    float farReach = spec.Kind == Kind.Head || spec.Kind == Kind.ForeArm ? 0f : radius * LimbCapReach;
                    Vector3 tipA = near - along * reach + offset, tipB = far + along * farReach + offset;
                    height = Vector3.Distance(tipA, tipB);
                    centre = (tipA + tipB) * 0.5f;
                    part.Up = toBone * along;
                }
                radius = Clamp(radius, spec.Radius);
                height = Mathf.Max(Clamp(height, spec.Length), radius * 2f + 0.01f);
                part.Radius = radius;
                part.Height = height;
                part.Center = toBone * (centre - bone.position);
                part.Direction = NearestAxis(toBone * along, out float alignment);
                if (alignment < 0.95f)
                    log.AppendLine(Inv($"  WARN {part.Name}: its capsule axis is {Mathf.Acos(alignment) * Mathf.Rad2Deg:0} degrees off the bone's nearest axis"));

                if (spec.Kind == Kind.Calf)
                    MeasureFoot(part, feet[i], spec.Side == NpcSide.Left ? leftFoot : rightFoot);

                SetJoint(part, spec, i, bones, children, pelvisUp, chestUp, neck);
                parts[i] = part;
                char axisName = "XYZ"[part.Direction];
                log.AppendLine(Inv($"{part.Name,-11} {part.Mass,4:0.0}  {radius:0.000} ({spec.Radius:0.000})  {height:0.000} ({spec.Length:0.00})") +
                               Inv($"    ({part.Center.x:0.000}, {part.Center.y:0.000}, {part.Center.z:0.000}) dir {axisName}") +
                               (part.BoxSize != Vector3.zero ? Inv($"  foot box {part.BoxSize.x:0.00} x {part.BoxSize.y:0.00} x {part.BoxSize.z:0.00}") : "") +
                               (part.Joint != JointKind.None ? Inv($"  joint {part.Joint} X {part.LowX:0}..{part.HighX:0} Y {part.LimitY:0} Z {part.LimitZ:0}") : ""));
            }
            return parts;
        }

        // Which part a skinned vertex belongs to: the nearest part bone up the hierarchy from its dominant bone; the neck goes
        // with the head (the head capsule starts at the neck base); everything from a foot down is that leg's foot box.
        private static int Owner(Transform bone, Transform[] parts, Transform neck, int head, Transform leftFoot, Transform rightFoot, out bool foot)
        {
            foot = false;
            if (bone == neck) return head;
            for (Transform t = bone; t != null; t = t.parent)
            {
                if (t == leftFoot || t == rightFoot) foot = true;
                int i = Array.IndexOf(parts, t);
                if (i >= 0) return i;
            }
            return -1;
        }

        // The shoe as a box lying flat along the character frame, on a child of the foot bone.
        private static void MeasureFoot(Part part, List<Vector3> points, Transform foot)
        {
            if (points.Count == 0) return;
            Vector3 centre = new(MidRange(points, Vector3.right), MidRange(points, Vector3.up), MidRange(points, Vector3.forward));
            var size = new Vector3(2f * Percentile(Offsets(points, centre, Vector3.right), 0.7f),
                2f * Percentile(Offsets(points, centre, Vector3.up), 0.7f),
                2f * Percentile(Offsets(points, centre, Vector3.forward), 0.7f));
            part.BoxBone = foot.name;
            part.BoxSize = Vector3.Max(size, Vector3.one * 0.03f);
            part.BoxPoseCenter = centre;
            part.BoxCenter = Quaternion.Inverse(foot.rotation) * (centre - foot.position);
            part.BoxRotation = Quaternion.Inverse(foot.rotation); // the character frame (world at the origin) in the foot's frame
        }

        // Joint frames in the bone's own frame. Hinge: X = flexion about the character's lateral axis (sign per the design),
        // Y = along the bone; limits from anatomical zero, minus the Idle pose's own bend. Ball (shoulder): X = along the
        // bone, the swing cone around the arm held out sideways.
        private static void SetJoint(Part part, Spec spec, int i, Transform[] bones, Transform[] children, Vector3 pelvisUp, Vector3 chestUp, Transform neck)
        {
            if (spec.Joint == JointKind.None) return;
            Transform bone = bones[i], parent = bones[spec.Parent];
            Quaternion toBone = Quaternion.Inverse(bone.rotation);
            Vector3 along = (children[i].position - bone.position).normalized;
            if (spec.Kind == Kind.Chest) along = chestUp;
            part.Reference = Quaternion.Inverse(parent.rotation) * bone.rotation;
            if (spec.Joint == JointKind.Ball)
            {
                Vector3 front = Vector3.ProjectOnPlane(Vector3.forward, along).normalized;
                part.Axis = toBone * along;
                part.Secondary = toBone * front;
                part.LowX = spec.Low;
                part.HighX = spec.High;
                part.LimitY = spec.LimitY;
                part.LimitZ = spec.LimitZ;
                Vector3 outward = spec.Side == NpcSide.Left ? -Vector3.right : Vector3.right;
                Quaternion held = Quaternion.FromToRotation(along, outward) * bone.rotation;
                part.Reference = Quaternion.Inverse(parent.rotation) * held;
                return;
            }
            Vector3 flex = Vector3.ProjectOnPlane(Vector3.right * spec.Flex, along).normalized;
            part.Axis = toBone * flex;
            part.Secondary = toBone * along;
            // The Idle pose's own flexion (signed, about 'flex'), from the parent segment's direction to this one's.
            Vector3 parentDir = spec.Kind switch
            {
                Kind.Chest => pelvisUp,
                Kind.Head => chestUp,
                Kind.Thigh => -pelvisUp,
                _ => (bone.position - parent.position).normalized, // elbow: upper arm; knee: thigh
            };
            float idle = Vector3.SignedAngle(Vector3.ProjectOnPlane(parentDir, flex), Vector3.ProjectOnPlane(along, flex), flex);
            part.LowX = Mathf.Min(spec.Low - idle, 0f);
            part.HighX = Mathf.Max(spec.High - idle, 0f);
            part.LimitY = spec.LimitY;
            part.LimitZ = spec.LimitZ;
        }

        // ---------- NpcRig on the prefabs ----------

        /// <summary>Puts NpcRig (the Buddy ragdoll profile and the root's Animator) on a character prefab root. True if it
        /// changed anything. GreyboxBuddySetup.EnsurePrefabs calls it when it regenerates the Buddy prefabs.</summary>
        public static bool EnsureRig(GameObject root)
        {
            var profile = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>(ProfilePath);
            if (profile == null)
            {
                Debug.LogWarning($"[NpcRagdollBuilder] {ProfilePath} is missing: run OnlyVolunteers/Characters/Npc/Build Buddy Ragdoll Profile. " +
                                 "Until then NPCs always go down as the capsule.");
                return false;
            }
            root.TryGetComponent(out Animator animator);
            if (!root.TryGetComponent(out NpcRig rig)) rig = root.AddComponent<NpcRig>();
            else if (rig.Ragdoll == profile && rig.Animator == animator) return false;
            rig.Ragdoll = profile;
            rig.Animator = animator;
            return true;
        }

        public static void EnsureRigOnPrefabs()
        {
            foreach (string path in BuddyPrefabs)
            {
                GameObject root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    if (EnsureRig(root))
                    {
                        PrefabUtility.SaveAsPrefabAsset(root, path);
                        Debug.Log($"[NpcRagdollBuilder] NpcRig set on {path}");
                    }
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
            }
        }

        private static NpcRagdollProfile LoadOrCreateProfile()
        {
            var profile = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>(ProfilePath);
            if (profile != null) return profile;
            string folder = System.IO.Path.GetDirectoryName(ProfilePath).Replace('\\', '/');
            if (!AssetDatabase.IsValidFolder(folder))
                AssetDatabase.CreateFolder(System.IO.Path.GetDirectoryName(folder).Replace('\\', '/'), System.IO.Path.GetFileName(folder));
            profile = ScriptableObject.CreateInstance<NpcRagdollProfile>();
            AssetDatabase.CreateAsset(profile, ProfilePath);
            return profile;
        }

        // ---------- Maths ----------

        private static int Index(Kind kind, NpcSide side)
        {
            for (int i = 0; i < Specs.Length; i++)
                if (Specs[i].Kind == kind && (kind < Kind.UpperArm || Specs[i].Side == side)) return i;
            return -1;
        }

        private static float Clamp(float measured, float design) =>
            float.IsNaN(measured) || measured <= 0f ? design : Mathf.Clamp(measured, design * ClampLow, design * ClampHigh);

        private static int NearestAxis(Vector3 local, out float alignment)
        {
            Vector3 a = new(Mathf.Abs(local.x), Mathf.Abs(local.y), Mathf.Abs(local.z));
            float length = Mathf.Max(1e-6f, local.magnitude);
            int axis = a.x >= a.y && a.x >= a.z ? 0 : a.y >= a.z ? 1 : 2;
            alignment = a[axis] / length;
            return axis;
        }

        private static List<float> Distances(List<Vector3> points, Vector3 a, Vector3 b)
        {
            var d = new List<float>(points.Count);
            Vector3 ab = b - a;
            float len = Mathf.Max(1e-10f, ab.sqrMagnitude);
            foreach (Vector3 p in points)
                d.Add((p - (a + ab * Mathf.Clamp01(Vector3.Dot(p - a, ab) / len))).magnitude);
            return d;
        }

        private static List<float> LineDistances(List<Vector3> points, Vector3 origin, Vector3 axis)
        {
            var d = new List<float>(points.Count);
            foreach (Vector3 p in points) d.Add(Vector3.ProjectOnPlane(p - origin, axis).magnitude);
            return d;
        }

        private static List<float> Projections(List<Vector3> points, Vector3 origin, Vector3 axis)
        {
            var d = new List<float>(points.Count);
            foreach (Vector3 p in points) d.Add(Vector3.Dot(p - origin, axis));
            return d;
        }

        private static List<float> Offsets(List<Vector3> points, Vector3 centre, Vector3 axis)
        {
            var d = new List<float>(points.Count);
            foreach (Vector3 p in points) d.Add(Mathf.Abs(Vector3.Dot(p - centre, axis)));
            return d;
        }

        private static float MidRange(List<Vector3> points, Vector3 axis)
        {
            List<float> d = Projections(points, Vector3.zero, axis);
            return (Percentile(d, 0.05f) + Percentile(d, 0.95f)) * 0.5f;
        }

        private static float Range(List<Vector3> points, Vector3 axis)
        {
            List<float> d = Projections(points, Vector3.zero, axis);
            return Percentile(d, 0.95f) - Percentile(d, 0.05f);
        }

        private static float Percentile(List<float> values, float q)
        {
            if (values.Count == 0) return float.NaN;
            values.Sort();
            return values[Mathf.Clamp(Mathf.RoundToInt(q * (values.Count - 1)), 0, values.Count - 1)];
        }

        private static string Inv(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);
    }
}
