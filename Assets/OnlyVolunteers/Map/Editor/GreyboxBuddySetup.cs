using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using OnlyVolunteers.Characters.Npc;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map
{
    // Turns the Sausage Buddy FBX exports (copied from ArtSource/Characters/SAUSAGE_BUDDY_01) into grey-box prefabs:
    // named looping clips, one Animator Controller (Idle / Walk / Run / TurnFlee) and a prefab per variant.
    // Stage 9 step 3: InstallClips (menu Tools/Only Volunteers/Characters/Install Buddy Clips; EnsurePrefabs runs it too)
    // installs the clip sets listed in Animations/clips.json (design §5.3): copies each source FBX in once (never over an
    // existing file), imports it like Walk_v02 (Generic, Copy From Other Avatar = Buddy A v04, Preserve Hierarchy, no
    // compression) with its one clip named after its Animator state, adds those states and the manifest's exit-time links
    // to SausageBuddy_Greybox.controller (the same asset, existing states kept), and writes the numbers the runtime needs
    // into the Buddy ragdoll profile (Characters/Npc/NpcGetUp reads them): states, lengths, the first-frame Hips, the
    // Stable share, events, and the seated visual layout measured on Buddy A (the sit idle's figure centred on the seated
    // capsule). Re-runnable: unchanged importers are not re-imported; the links of the states it names are rebuilt.
    // Stage 9 step 5: the controller is generated (Characters/Npc/Editor/NpcAnimatorBuilder: the contract's parameters, the
    // modes, the one-shots, the upper-body and struggle layers) from the Buddy FBX's built-in clips plus clips.json, whose
    // entries now say each clip's role (NpcAnimContract: Idle, Walk, Run, RunCop, RunCopFat, the cargo and get-up clips,
    // Scramble, JumpOut, the hit reacts, Punch, ShakeFist, Trip, Struggle, AimRaise, Aim, "<CrowdActivity>/Enter|Loop|Exit"),
    // the ground speed a locomotion clip was authored for ("speed", m/s), whether it is an additive clip ("additive": its
    // first frame is the reference pose) and, for the record, the file it replaced ("was": rollback = put that file back
    // in "file"/"take"/"source" and run the menu again; nothing is ever deleted). "states" entries may carry a role too (a
    // second activity reusing a clip). The profile gets every entry by role (Roles) besides the named clips it had.
    public static class GreyboxBuddySetup
    {
        private const string Dir = "Assets/OnlyVolunteers/Characters/SausageBuddy";
        private const string ControllerPath = Dir + "/SausageBuddy_Greybox.controller";
        private const string WalkPath = Dir + "/Animations/Walk_v02.fbx";
        private const string ManifestPath = Dir + "/Animations/clips.json";
        private static readonly string[] Variants = { "A", "B" };

        public static GameObject[] EnsurePrefabs()
        {
            foreach (string v in Variants)
                ConfigureImporter(FbxPath(v));
            ConfigureWalkImporter();
            AnimatorController controller = BuildController(FbxPath("A"));
            var prefabs = new List<GameObject>();
            foreach (string v in Variants)
            {
                var root = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath(v)));
                PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
                root.name = $"SausageBuddy_{v}";
                if (!root.TryGetComponent(out Animator animator))
                    animator = root.AddComponent<Animator>();
                animator.runtimeAnimatorController = controller;
                animator.applyRootMotion = false;
                // The FBX rest pose sits ~11 m below the root, so culled Animators never move the bones into view.
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                // Stage 9: which ragdoll profile fits this rig (Characters/Npc/NpcRig; a warning until the profile exists).
                OnlyVolunteers.Characters.Npc.NpcRagdollBuilder.EnsureRig(root);
                prefabs.Add(PrefabUtility.SaveAsPrefabAsset(root, $"{Dir}/SausageBuddy_{v}.prefab"));
                Object.DestroyImmediate(root);
            }
            if (File.Exists(ManifestPath)) Debug.Log(InstallClips());
            return prefabs.ToArray();
        }

        private static string FbxPath(string variant) => $"{Dir}/SAUSAGE_BUDDY_{variant}_v04.fbx";

        [MenuItem("Tools/Only Volunteers/Characters/Install Buddy Walk")]
        public static void InstallWalk()
        {
            ConfigureWalkImporter();
            BuildController(FbxPath("A"));
            if (File.Exists(ManifestPath)) Debug.Log(InstallClips());
        }

        private static void ConfigureWalkImporter()
        {
            var importer = AssetImporter.GetAtPath(WalkPath) as ModelImporter;
            if (importer == null)
                throw new System.InvalidOperationException("Missing Buddy walk animation: " + WalkPath);
            Avatar avatar = null;
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(FbxPath("A")))
                if (asset is Avatar found) { avatar = found; break; }
            if (avatar == null)
                throw new System.InvalidOperationException("Buddy A needs its existing Generic Avatar before importing Walk.");

            importer.importAnimation = true;
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
            importer.sourceAvatar = avatar;
            // Animation-only FBX otherwise collapses the armature object and loses the prefab's binding prefix.
            importer.preserveHierarchy = true;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            var clips = new List<ModelImporterClipAnimation>();
            foreach (ModelImporterClipAnimation clip in importer.defaultClipAnimations)
            {
                if (!clip.takeName.EndsWith("|Walk") && clip.takeName != "Walk") continue;
                clip.name = "Walk";
                clip.loopTime = true;
                // The authored endpoint is identical; blending a second correction into it causes foot drift.
                clip.loopPose = false;
                clips.Add(clip);
            }
            if (clips.Count != 1)
                throw new System.InvalidOperationException("Expected exactly one authored Walk take, got " + clips.Count);
            importer.clipAnimations = clips.ToArray();
            importer.SaveAndReimport();
        }

        private static void ConfigureImporter(string path)
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            // Without a generic Avatar the Animator cannot bind the clips and the skin collapses at the rest pose.
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            var clips = new List<ModelImporterClipAnimation>();
            foreach (ModelImporterClipAnimation clip in importer.defaultClipAnimations)
            {
                // The Mixamo source take keeps the original rig far from the origin; the Buddy's own clips do not.
                if (clip.takeName.Contains("mixamo.com")) continue;
                clip.name = clip.takeName.Substring(clip.takeName.LastIndexOf('|') + 1);
                clip.loopTime = clip.name == "Idle" || clip.name == "Panic_Run_Loop";
                clips.Add(clip);
            }
            importer.clipAnimations = clips.ToArray();
            importer.SaveAndReimport();
        }

        // The controller asset (reused: deleting and recreating it in the same pass left prefabs pointing at a dead
        // controller). With clips.json, InstallClips generates it (EnsurePrefabs and InstallWalk run that next); without,
        // the built-in clips alone.
        private static AnimatorController BuildController(string fbx)
        {
            AnimatorController controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath)
                ?? AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            if (!File.Exists(ManifestPath))
            {
                Debug.Log(Generate(controller, null, null));
                AssetDatabase.SaveAssets();
            }
            return controller;
        }

        // Step 5: the controller from the Buddy FBX's built-in clips (Idle, Panic_Run_Loop, Panic_TurnFlee), Walk_v02 and
        // the manifest's clips by role (NpcAnimatorBuilder).
        private static string Generate(AnimatorController controller, Manifest manifest, Dictionary<string, AnimationClip> clips)
        {
            var builtIn = new Dictionary<string, AnimationClip>();
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(FbxPath("A")))
                if (asset is AnimationClip clip && !clip.name.StartsWith("__preview"))
                    builtIn[clip.name] = clip;
            var spec = new NpcAnimatorBuilder.Spec
            {
                Idle = builtIn["Idle"],
                Run = builtIn["Panic_Run_Loop"],
                TurnFlee = builtIn.TryGetValue("Panic_TurnFlee", out AnimationClip turn) ? turn : null,
                MaskPrefab = $"{Dir}/SausageBuddy_A.prefab",
            };
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(WalkPath))
                if (asset is AnimationClip walk && walk.name == "Walk")
                    spec.Walk = walk;
            if (manifest == null) return NpcAnimatorBuilder.Build(controller, spec);
            foreach (ClipEntry entry in manifest.clips)
            {
                spec.States[entry.state] = clips[entry.state];
                if (!string.IsNullOrEmpty(entry.role)) spec.Roles[entry.role] = entry.state;
            }
            foreach (StateEntry entry in manifest.states)
            {
                Motion motion = spec.States.TryGetValue(entry.motion, out Motion m) ? m
                    : entry.motion == NpcAnimContract.IdleState ? spec.Idle
                    : entry.motion == NpcAnimContract.WalkState ? spec.Walk
                    : entry.motion == NpcAnimContract.RunState ? spec.Run : null;
                if (motion == null) throw new InvalidOperationException($"clips.json: state {entry.state}: no state '{entry.motion}' to take the motion from");
                spec.States[entry.state] = motion;
                if (!string.IsNullOrEmpty(entry.role)) spec.Roles[entry.role] = entry.state;
            }
            foreach (LinkEntry link in manifest.links) spec.Links.Add((link.from, link.to, link.exitTime, link.blend));
            return NpcAnimatorBuilder.Build(controller, spec);
        }

        // Locomotion clips play in the contract's states (the player's Buddy and the preview ask for them by name).
        private static void Validate(Manifest manifest)
        {
            var states = new HashSet<string>();
            foreach (ClipEntry entry in manifest.clips)
            {
                if (!states.Add(entry.state)) throw new InvalidOperationException("clips.json: two clips named " + entry.state);
                string want = entry.role == NpcAnimContract.RoleIdle ? NpcAnimContract.IdleState
                    : entry.role == NpcAnimContract.RoleWalk ? NpcAnimContract.WalkState
                    : entry.role == NpcAnimContract.RoleRun ? NpcAnimContract.RunState : null;
                if (want != null && entry.state != want)
                    throw new InvalidOperationException($"clips.json: the {entry.role} clip must be in state '{want}', not '{entry.state}'");
            }
            foreach (StateEntry entry in manifest.states)
                if (!states.Add(entry.state)) throw new InvalidOperationException("clips.json: two states named " + entry.state);
        }

        // ---------- Stage 9 step 3: the clip manifest (Animations/clips.json) ----------

        // JsonUtility shapes of clips.json (field names as in the file).
        [Serializable]
        private sealed class Manifest
        {
            public ClipEntry[] clips = Array.Empty<ClipEntry>();
            public StateEntry[] states = Array.Empty<StateEntry>();
            public LinkEntry[] links = Array.Empty<LinkEntry>();
            public SeatEntry seat = new();
            public PlacementEntry[] placement = Array.Empty<PlacementEntry>();
            public PropEntry[] props = Array.Empty<PropEntry>();
        }

        // Step 5 hook: a hand prop shown during a crowd activity (NpcRagdollProfile.ActivityProp). prefab: an asset path, or
        // empty for a plain cylinder of size (m).
        [Serializable]
        private sealed class PropEntry
        {
            public string activity = "", bone = "", prefab = "";
            public float[] position = Array.Empty<float>(), rotation = Array.Empty<float>(), size = Array.Empty<float>();
            public bool upright;
        }

        // Step 5: a crowd activity's prop behind the NPC (NpcRagdollProfile.ActivityPlacement).
        [Serializable]
        private sealed class PlacementEntry
        {
            public string activity = "", prop = "";
            public float height, gap, reach;
        }

        [Serializable]
        private sealed class ClipEntry
        {
            public string role = "", state = "", source = "", file = "", take = "", was = "";
            public bool loop, additive;
            public float seconds, stable, speed;
            public float[] hipsStart = Array.Empty<float>();
            public float[] events = Array.Empty<float>();
        }

        [Serializable]
        private sealed class StateEntry
        {
            public string state = "", motion = "", role = "";
        }

        [Serializable]
        private sealed class LinkEntry
        {
            public string from = "", to = "";
            public float exitTime = 1f, blend = 0.15f;
        }

        [Serializable]
        private sealed class SeatEntry
        {
            public float yaw;
            public string clip = "";
        }

        [MenuItem("Tools/Only Volunteers/Characters/Install Buddy Clips (clips.json)")]
        public static void InstallClipsMenu() => Debug.Log(InstallClips());

        /// <summary>Installs every clip of Animations/clips.json (see the header); returns the report.</summary>
        public static string InstallClips()
        {
            var log = new StringBuilder("[GreyboxBuddySetup] clips.json:\n");
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            Validate(manifest);
            Avatar avatar = BuddyAvatar();

            // Files and importers.
            var clips = new Dictionary<string, AnimationClip>();
            foreach (ClipEntry entry in manifest.clips)
            {
                string path = $"{Dir}/Animations/{entry.file}";
                if (!File.Exists(path))
                {
                    if (!File.Exists(entry.source)) throw new InvalidOperationException($"clips.json: {entry.state}: neither {path} nor {entry.source}");
                    File.Copy(entry.source, path, false);
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    log.AppendLine($"  copied {entry.source} -> {path}");
                }
                bool changed = ConfigureClipImporter(path, entry.take, entry.state, entry.loop, entry.additive, avatar);
                AnimationClip clip = null;
                foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
                    if (asset is AnimationClip c && c.name == entry.state) clip = c;
                if (clip == null) throw new InvalidOperationException($"clips.json: no clip '{entry.state}' in {path}");
                clips[entry.state] = clip;
                log.AppendLine(Inv($"  {entry.state,-16} {entry.role,-14} {entry.file} {clip.length:0.00} s (manifest {entry.seconds:0.00}) loop={(entry.loop ? 1 : 0)}") +
                               $"{(entry.additive ? " additive" : "")}{(changed ? " (re-imported)" : "")}");
            }

            // The controller (the same asset), generated (step 5: NpcAnimatorBuilder).
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (controller == null) throw new InvalidOperationException("Missing " + ControllerPath + " (run the Buddy setup first)");
            log.Append(Generate(controller, manifest, clips));

            // The numbers, into the ragdoll profile (Characters/Npc/NpcGetUp), checked against Buddy A.
            var profile = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>(NpcRagdollBuilder.ProfilePath);
            if (profile == null) throw new InvalidOperationException("Missing " + NpcRagdollBuilder.ProfilePath);
            var roles = new List<NpcRagdollProfile.ClipInfo>();
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                GameObject buddy = NpcRagdollBuilder.InstantiateSampled(NpcRagdollBuilder.BuddyPrefabs[0], scene);
                Transform hips = Bone(buddy.transform, "mixamorig:Hips");
                foreach (ClipEntry entry in manifest.clips)
                {
                    bool hasHips = entry.hipsStart != null && entry.hipsStart.Length == 3;
                    var byRole = new NpcRagdollProfile.ClipInfo();
                    Fill(byRole, entry, clips[entry.state]);
                    roles.Add(byRole);
                    NpcRagdollProfile.ClipInfo info = entry.role switch
                    {
                        NpcAnimContract.RoleGetUpBack => profile.GetUpBack,
                        NpcAnimContract.RoleGetUpBelly => profile.GetUpBelly,
                        NpcAnimContract.RoleSitUp => profile.SitUp,
                        NpcAnimContract.RoleSitIdle => profile.SitIdle,
                        NpcAnimContract.RoleKnock => profile.Knock,
                        NpcAnimContract.RoleScramble => profile.Scramble,
                        NpcAnimContract.RoleJumpOut => profile.JumpOut, // its Land event too (step 5)
                        _ => null,
                    };
                    if (info == null) continue;
                    Fill(info, entry, clips[entry.state]);
                    if (!hasHips) continue;
                    clips[entry.state].SampleAnimation(buddy, 0f);
                    Vector3 measured = buddy.transform.InverseTransformPoint(hips.position);
                    float miss = Vector3.Distance(measured, info.HipsStart);
                    log.AppendLine(Inv($"  {entry.role,-10} first-frame Hips ({measured.x:0.000}, {measured.y:0.000}, {measured.z:0.000}) vs manifest ") +
                                   Inv($"({info.HipsStart.x:0.000}, {info.HipsStart.y:0.000}, {info.HipsStart.z:0.000}){(miss > 0.01f ? "  WARN off by " + miss.ToString("0.000", CultureInfo.InvariantCulture) + " m" : "")}"));
                }
                MeasureSeat(profile, manifest.seat, clips, buddy, log);
                MeasureSeatReach(profile, clips, scene, log);
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
            // "states" entries with a role (a second activity reusing a clip): listed under their own state name.
            foreach (StateEntry entry in manifest.states)
            {
                if (string.IsNullOrEmpty(entry.role)) continue;
                AnimationClip motion = clips.TryGetValue(entry.motion, out AnimationClip c) ? c : null;
                roles.Add(new NpcRagdollProfile.ClipInfo
                {
                    Role = entry.role,
                    State = entry.state,
                    Seconds = motion != null ? motion.length : 0f,
                    Loop = motion != null && motion.isLooping,
                });
            }
            profile.Roles = roles.ToArray();
            var placements = new List<NpcRagdollProfile.ActivityPlacement>();
            foreach (PlacementEntry entry in manifest.placement ?? Array.Empty<PlacementEntry>())
            {
                placements.Add(new NpcRagdollProfile.ActivityPlacement
                {
                    Activity = entry.activity,
                    Prop = entry.prop ?? "",
                    Height = entry.height,
                    Gap = entry.gap,
                    Reach = entry.reach,
                });
                log.AppendLine(Inv($"  placement {entry.activity}: {(string.IsNullOrEmpty(entry.prop) ? "a wall" : entry.prop)} behind, {entry.gap:0.00} m gap, at {entry.height:0.00} m, within {entry.reach:0.0} m"));
            }
            profile.Placements = placements.ToArray();
            var props = new List<NpcRagdollProfile.ActivityProp>();
            foreach (PropEntry entry in manifest.props ?? Array.Empty<PropEntry>())
            {
                var prop = new NpcRagdollProfile.ActivityProp
                {
                    Activity = entry.activity,
                    Bone = entry.bone,
                    Position = V3(entry.position, Vector3.zero),
                    Rotation = V3(entry.rotation, Vector3.zero),
                    Size = V3(entry.size, new Vector3(0.008f, 0.07f, 0.008f)),
                    Prefab = string.IsNullOrEmpty(entry.prefab) ? null : AssetDatabase.LoadAssetAtPath<GameObject>(entry.prefab),
                    Upright = entry.upright,
                };
                if (!string.IsNullOrEmpty(entry.prefab) && prop.Prefab == null) throw new InvalidOperationException("clips.json: no prop prefab " + entry.prefab);
                props.Add(prop);
                log.AppendLine($"  prop {entry.activity}: {(prop.Prefab != null ? prop.Prefab.name : "a cylinder")} on {entry.bone}");
            }
            profile.Props = props.ToArray();
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            return log.ToString();
        }

        // A clip's numbers from its clips.json entry (lengths default to the clip's own).
        private static void Fill(NpcRagdollProfile.ClipInfo info, ClipEntry entry, AnimationClip clip)
        {
            bool hasHips = entry.hipsStart != null && entry.hipsStart.Length == 3;
            info.Role = entry.role ?? "";
            info.State = entry.state;
            info.Seconds = entry.seconds > 0f ? entry.seconds : clip.length;
            info.HipsStart = hasHips ? new Vector3(entry.hipsStart[0], entry.hipsStart[1], entry.hipsStart[2]) : Vector3.zero;
            info.Stable = entry.stable;
            info.Events = entry.events ?? Array.Empty<float>();
            info.Speed = entry.speed;
            info.Loop = entry.loop;
        }

        // The seated visual layout: the visual turned seat.yaw (the sit clips face their -X), and moved so the seat clip's
        // figure (its skinned vertices at frame 0, 0.5-99.5th percentile on the floor plane) is centred over the root; the
        // footprint around the root that the sit-up keeps inside the cargo bay.
        private static void MeasureSeat(NpcRagdollProfile profile, SeatEntry seat, Dictionary<string, AnimationClip> clips, GameObject buddy,
            StringBuilder log)
        {
            if (seat == null || string.IsNullOrEmpty(seat.clip) || !clips.TryGetValue(seat.clip, out AnimationClip clip))
            {
                log.AppendLine("  seat: no seat clip in the manifest");
                return;
            }
            clip.SampleAnimation(buddy, 0f);
            var xs = new List<float>();
            var zs = new List<float>();
            float top = float.MinValue;
            foreach (SkinnedMeshRenderer smr in buddy.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null) continue;
                var baked = new Mesh();
                smr.BakeMesh(baked, true);
                Matrix4x4 toRoot = buddy.transform.worldToLocalMatrix * smr.transform.localToWorldMatrix;
                foreach (Vector3 v in baked.vertices)
                {
                    Vector3 p = toRoot.MultiplyPoint3x4(v);
                    xs.Add(p.x);
                    zs.Add(p.z);
                    top = Mathf.Max(top, p.y);
                }
                Object.DestroyImmediate(baked);
            }
            if (xs.Count == 0)
            {
                log.AppendLine("  seat: no skinned vertices on Buddy A");
                return;
            }
            xs.Sort();
            zs.Sort();
            float minX = Pick(xs, 0.005f), maxX = Pick(xs, 0.995f), minZ = Pick(zs, 0.005f), maxZ = Pick(zs, 0.995f);
            Quaternion turn = Quaternion.Euler(0f, seat.yaw, 0f);
            Vector3 centre = turn * new Vector3((minX + maxX) * 0.5f, 0f, (minZ + maxZ) * 0.5f);
            profile.SeatYaw = seat.yaw;
            profile.SeatOffset = -centre;
            var min = new Vector2(float.MaxValue, float.MaxValue);
            var max = new Vector2(float.MinValue, float.MinValue);
            for (int corner = 0; corner < 4; corner++)
            {
                Vector3 c = turn * new Vector3((corner & 1) == 0 ? minX : maxX, 0f, (corner & 2) == 0 ? minZ : maxZ) - centre;
                min = Vector2.Min(min, new Vector2(c.x, c.z));
                max = Vector2.Max(max, new Vector2(c.x, c.z));
            }
            profile.SeatMin = min;
            profile.SeatMax = max;
            log.AppendLine(Inv($"  seat ({seat.clip} frame 0): clip x {minX:0.00}..{maxX:0.00} z {minZ:0.00}..{maxZ:0.00}, top {top:0.00} m; ") +
                           Inv($"visual yaw {seat.yaw:0}, offset ({profile.SeatOffset.x:0.00}, {profile.SeatOffset.z:0.00}), footprint x {min.x:0.00}..{max.x:0.00} z {min.y:0.00}..{max.y:0.00}"));
        }

        // How far each skinned mesh of the Buddy prefabs reaches toward the wall behind the seated figure (the sit clips'
        // +X, turned and moved by the seat layout above), every 1/30 s over the sit idle, the knock and the sit-up from
        // 0.8 s before its Seated event (earlier it lies where the ragdoll lay: GreyboxNpc holds it there); LowBack: the part
        // under SeatLowHeight. NpcGetUp.SitUp puts the deepest of an NPC's meshes just off the van wall.
        private static void MeasureSeatReach(NpcRagdollProfile profile, Dictionary<string, AnimationClip> clips, Scene scene, StringBuilder log)
        {
            var reaches = new List<NpcRagdollProfile.SeatReach>();
            if (!clips.TryGetValue(profile.SitIdle.State ?? "", out AnimationClip idle) ||
                !clips.TryGetValue(profile.SitUp.State ?? "", out AnimationClip sitUp))
            {
                profile.SeatReaches = reaches.ToArray();
                log.AppendLine("  seat reach: no sit clips");
                return;
            }
            clips.TryGetValue(profile.Knock.State ?? "", out AnimationClip knock);
            float sitFrom = Mathf.Max(0f, (profile.SitUp.Events != null && profile.SitUp.Events.Length >= 2 ? profile.SitUp.Events[1] : sitUp.length) - 0.8f);
            Quaternion turn = Quaternion.Euler(0f, profile.SeatYaw, 0f);
            Vector3 back = turn * Vector3.right;
            foreach (string path in NpcRagdollBuilder.BuddyPrefabs)
            {
                GameObject buddy = NpcRagdollBuilder.InstantiateSampled(path, scene);
                var skins = buddy.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                var baked = new Mesh();
                var deep = new float[skins.Length];
                var low = new float[skins.Length];
                for (int i = 0; i < skins.Length; i++) deep[i] = low[i] = float.MinValue;
                foreach ((AnimationClip clip, float from) in new[] { (idle, 0f), (knock, 0f), (sitUp, sitFrom) })
                {
                    if (clip == null) continue;
                    for (float t = from; t <= clip.length + 1e-4f; t += 1f / 30f)
                    {
                        clip.SampleAnimation(buddy, Mathf.Min(t, clip.length));
                        for (int i = 0; i < skins.Length; i++)
                        {
                            if (skins[i].sharedMesh == null) continue;
                            skins[i].BakeMesh(baked, true);
                            Matrix4x4 toRoot = buddy.transform.worldToLocalMatrix * skins[i].transform.localToWorldMatrix;
                            foreach (Vector3 v in baked.vertices)
                            {
                                Vector3 q = profile.SeatOffset + turn * toRoot.MultiplyPoint3x4(v);
                                float d = Vector3.Dot(q, back);
                                deep[i] = Mathf.Max(deep[i], d);
                                if (q.y < NpcRagdollProfile.SeatLowHeight) low[i] = Mathf.Max(low[i], d);
                            }
                        }
                    }
                }
                Object.DestroyImmediate(baked);
                for (int i = 0; i < skins.Length; i++)
                {
                    Mesh mesh = skins[i].sharedMesh;
                    if (mesh == null || deep[i] == float.MinValue) continue;
                    float lowBack = low[i] == float.MinValue ? 0f : low[i];
                    NpcRagdollProfile.SeatReach known = reaches.Find(r => r.Mesh == mesh);
                    if (known != null) continue; // shared by both prefabs: the same rig, the same numbers
                    reaches.Add(new NpcRagdollProfile.SeatReach { Mesh = mesh, Back = deep[i], LowBack = lowBack });
                    log.AppendLine(Inv($"  seat reach {Path.GetFileNameWithoutExtension(path)}/{skins[i].name} ({mesh.name}): back {deep[i]:0.000} m, under {NpcRagdollProfile.SeatLowHeight:0.00} m {lowBack:0.000} m"));
                }
                Object.DestroyImmediate(buddy);
            }
            profile.SeatReaches = reaches.ToArray();
        }

        private static float Pick(List<float> sorted, float q) => sorted[Mathf.Clamp(Mathf.RoundToInt(q * (sorted.Count - 1)), 0, sorted.Count - 1)];

        private static Vector3 V3(float[] v, Vector3 fallback) => v != null && v.Length == 3 ? new Vector3(v[0], v[1], v[2]) : fallback;

        // Like ConfigureWalkImporter, for one take of a manifest clip (additive: its first frame is the additive reference
        // pose, step 5). True when it had to re-import.
        private static bool ConfigureClipImporter(string path, string take, string clipName, bool loop, bool additive, Avatar avatar)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("Not a model: " + path);
            ModelImporterClipAnimation[] current = importer.clipAnimations;
            bool same = importer.importAnimation && importer.animationType == ModelImporterAnimationType.Generic &&
                        importer.avatarSetup == ModelImporterAvatarSetup.CopyFromOther && importer.sourceAvatar == avatar &&
                        importer.preserveHierarchy && importer.animationCompression == ModelImporterAnimationCompression.Off &&
                        importer.materialImportMode == ModelImporterMaterialImportMode.None &&
                        current.Length == 1 && current[0].name == clipName && current[0].loopTime == loop && !current[0].loopPose &&
                        current[0].hasAdditiveReferencePose == additive &&
                        (!additive || Mathf.Approximately(current[0].additiveReferencePoseFrame, current[0].firstFrame)) &&
                        (current[0].takeName == take || current[0].takeName.EndsWith("|" + take));
            if (same) return false;
            importer.importAnimation = true;
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
            importer.sourceAvatar = avatar;
            // Animation-only FBX otherwise collapses the armature object and loses the prefab's binding prefix.
            importer.preserveHierarchy = true;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.materialImportMode = ModelImporterMaterialImportMode.None; // armature only: nothing to extract
            var clips = new List<ModelImporterClipAnimation>();
            foreach (ModelImporterClipAnimation clip in importer.defaultClipAnimations)
            {
                if (clip.takeName != take && !clip.takeName.EndsWith("|" + take)) continue;
                clip.name = clipName;
                clip.loopTime = loop;
                // The authored seams are exact; a second correction blended into them causes drift.
                clip.loopPose = false;
                clip.hasAdditiveReferencePose = additive;
                if (additive) clip.additiveReferencePoseFrame = clip.firstFrame;
                clips.Add(clip);
            }
            if (clips.Count != 1) throw new InvalidOperationException($"{path}: expected one take '{take}', got {clips.Count}");
            importer.clipAnimations = clips.ToArray();
            importer.SaveAndReimport();
            return true;
        }

        private static Avatar BuddyAvatar()
        {
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(FbxPath("A")))
                if (asset is Avatar avatar) return avatar;
            throw new InvalidOperationException("Buddy A needs its Generic Avatar before importing clips.");
        }

        private static Transform Bone(Transform root, string name)
        {
            foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == name) return t;
            throw new InvalidOperationException("No bone " + name);
        }

        private static string Inv(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);
    }
}
