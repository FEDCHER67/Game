using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Economy.EditorTools
{
    /// <summary>
    /// MECHANIC_W86 into the game (29.10; v02 model + v03 clips since the rifle-sized wrench): copies the game model
    /// (ArtSource/Characters/MECHANIC_W86/MECHANIC_W86_v02_opt_v02.fbx: LOD0/1/2, the 65-bone crowd rig, the 0.85 m wrench
    /// v02) and the clips of the newest manifest (Animations_v03/clips_mechanic_v03.json: each clip from its "source"
    /// path, his own carry copies of Idle / Walk ("carry_clips"), the Grip_R v02 finger pose) into <see cref="Root"/>, sets
    /// the importers like the crowd types (Generic, avatar copied from Sausage Buddy A v04, no root motion; clip names =
    /// Animator states, loop flags and the manifest's events as OnMechanicCue), builds the finger-only AvatarMask, the
    /// Animator controller (base layer: Idle / Walk = the carry clips (the shared Idle_Stand_v04 / Walk_v04 only as a
    /// fallback) + the mechanic's work, gag, attention and upgrade states; last layer HandGrip_R: Override, weight 1, the
    /// mask, Grip_R) and the prefab (LODGroup, a standing capsule, MechanicW86PresenterV01 with the face cues). The wrench
    /// mesh is Wrench_RightHand (rigid on mixamorig:RightHand): it is NOT a Props_*Hand mesh and the prefab gets no
    /// NpcHeldProps, so he never drops it. Idempotent: copies once, re-sets importers only when they differ, rebuilds the
    /// controller in place (same asset) and re-saves the prefab at the same path (same GUID). The v01 prefab / controller /
    /// mask / model / clips stay in the folder untouched (the W85 integrator and the scene use <see cref="PrefabPath"/>).
    /// </summary>
    public static class MechanicW86ImportV01
    {
        public const string Root = "Assets/OnlyVolunteers/Characters/Mechanic_W86";
        public const string ModelPath = Root + "/Models/MECHANIC_W86_v02_opt_v02.fbx";
        public const string AnimDir = Root + "/Animations";
        public const string CuesPath = AnimDir + "/clips_mechanic_v03.json";
        public const string MaskPath = Root + "/Mechanic_HandR_Grip_v02.mask";
        public const string ControllerPath = Root + "/Mechanic_W86_v02.controller";
        public const string PrefabPath = Root + "/Mechanic_W86_v02.prefab";
        public const string PuffMaterialPath = Root + "/Fx/MechanicPuff_v01.mat";
        private const string Source = "ArtSource/Characters/MECHANIC_W86";
        /// <summary>The newest clip manifest (every clip entry carries its own "source" path).</summary>
        private const string ManifestSource = Source + "/Animations_v03/clips_mechanic_v03.json";
        private const string ModelSource = Source + "/MECHANIC_W86_v02_opt_v02.fbx";
        private const string BuddyAFbx = "Assets/OnlyVolunteers/Characters/SausageBuddy/SAUSAGE_BUDDY_A_v04.fbx";
        private const string SharedIdle = "Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Idle_Stand_v04.fbx";
        private const string SharedWalk = "Assets/OnlyVolunteers/Characters/SausageBuddy/Animations/Walk_v04.fbx";
        private const string GripStem = "MECHANIC_W86_Grip_R_v02";
        private const string CueFunction = "OnMechanicCue";
        /// <summary>LOD screen heights (MECHANIC_W86_v01_notes.json: LOD0 0.1, LOD1 0.037, cull 0.01).</summary>
        private static readonly float[] LodHeights = { 0.1f, 0.037f, 0.01f };

        private static readonly string[] GripBones =
        {
            "mixamorig:RightHandThumb1", "mixamorig:RightHandThumb2", "mixamorig:RightHandThumb3", "mixamorig:RightHandThumb4",
            "mixamorig:RightHandIndex1", "mixamorig:RightHandIndex2", "mixamorig:RightHandIndex3", "mixamorig:RightHandIndex4",
            "mixamorig:RightHandMiddle1", "mixamorig:RightHandMiddle2", "mixamorig:RightHandMiddle3", "mixamorig:RightHandMiddle4",
            "mixamorig:RightHandRing1", "mixamorig:RightHandRing2", "mixamorig:RightHandRing3", "mixamorig:RightHandRing4",
            "mixamorig:RightHandPinky1", "mixamorig:RightHandPinky2", "mixamorig:RightHandPinky3", "mixamorig:RightHandPinky4",
        };

        [Serializable] private sealed class Manifest { public ManifestClip[] clips; public ManifestClip[] carry_clips; public ManifestGrip grip_clip; }
        [Serializable] private sealed class ManifestClip { public string state; public string file; public string source; public bool loop; public float seconds; }
        [Serializable] private sealed class ManifestGrip { public string file; public string source; }

        [MenuItem("OnlyVolunteers/Characters/Mechanic W86 - import and build prefab (v02 model, v03 clips)")]
        public static void Menu() => Debug.Log(Build());

        public static string Build()
        {
            if (EditorApplication.isPlaying) return "[MECHANIC_W86] leave Play mode first";
            var log = new StringBuilder("[MECHANIC_W86] import v02 model + v03 clips\n");
            string project = Path.GetDirectoryName(Application.dataPath);
            foreach (string d in new[] { Root, Root + "/Models", AnimDir, Root + "/Fx" }) Folder(d);

            // 1. files (copied once; never overwritten)
            var copied = new List<string>();
            Copy(project, ModelSource, ModelPath, copied);
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(project, ManifestSource)));
            ManifestClip[] carry = manifest.carry_clips ?? new ManifestClip[0];
            foreach (ManifestClip c in manifest.clips.Concat(carry)) Copy(project, SourceOf(c), AnimDir + "/" + c.file, copied);
            Copy(project, manifest.grip_clip != null && !string.IsNullOrEmpty(manifest.grip_clip.source) ? manifest.grip_clip.source : Source + "/Animations_v03/" + GripStem + ".fbx",
                 AnimDir + "/" + GripStem + ".fbx", copied);
            Copy(project, ManifestSource, CuesPath, copied);
            foreach (string p in copied) AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceSynchronousImport);
            log.AppendLine($"  copied {copied.Count} files into {Root}");

            // 2. importers (crowd-type conventions)
            Avatar buddy = AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx).OfType<Avatar>().FirstOrDefault();
            if (buddy == null) return log.Append("  FAILED: no avatar in " + BuddyAFbx).ToString();
            int changed = ConfigureModel(ModelPath, buddy) ? 1 : 0;
            Dictionary<string, ManifestEvents> events = ReadEvents(Path.Combine(project, ManifestSource));
            foreach (ManifestClip c in manifest.clips)
                if (ConfigureClip(AnimDir + "/" + c.file, buddy, c.state, c.loop, events.TryGetValue(c.state, out ManifestEvents ev) ? ev : null, log)) changed++;
            foreach (ManifestClip c in carry)
                if (ConfigureClip(AnimDir + "/" + c.file, buddy, c.state, c.loop, null, log)) changed++;
            if (ConfigureClip(AnimDir + "/" + GripStem + ".fbx", buddy, "Grip_R", true, null, log)) changed++;
            log.AppendLine($"  importers: {changed} (re)configured");

            // 3. mask, controller, puff material, prefab
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (model == null) return log.Append("  FAILED: model missing " + ModelPath).ToString();
            AvatarMask mask = BuildMask(model, log);
            AnimatorController controller = BuildController(manifest, mask, log);
            Material puff = BuildPuffMaterial(log);
            BuildPrefab(model, controller, buddy, log);
            AssetDatabase.SaveAssets();
            log.AppendLine($"  done: prefab {PrefabPath}, controller {ControllerPath}, mask {MaskPath}, puff {PuffMaterialPath} ({(puff != null ? "ok" : "MISSING")})");
            return log.ToString();
        }

        // ------------------------------------------------------------------ files and importers

        /// <summary>A manifest clip's ArtSource file: its "source" path, else the v01 folder (the v01 manifest format).</summary>
        private static string SourceOf(ManifestClip c) => !string.IsNullOrEmpty(c.source) ? c.source : Source + "/Animations_v01/" + c.file;

        private static void Folder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            Folder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        private static void Copy(string project, string source, string target, List<string> copied)
        {
            string from = Path.Combine(project, source), to = Path.Combine(project, target);
            if (File.Exists(to)) return;
            if (!File.Exists(from)) throw new FileNotFoundException("MECHANIC_W86 source missing", from);
            File.Copy(from, to, false);
            copied.Add(target);
        }

        private static bool ConfigureModel(string path, Avatar avatar)
        {
            var mi = (ModelImporter)AssetImporter.GetAtPath(path);
            if (mi.animationType == ModelImporterAnimationType.Generic && mi.avatarSetup == ModelImporterAvatarSetup.CopyFromOther &&
                mi.sourceAvatar == avatar && !mi.importAnimation && mi.importBlendShapes &&
                mi.materialLocation == ModelImporterMaterialLocation.InPrefab) return false;
            mi.animationType = ModelImporterAnimationType.Generic;
            mi.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
            mi.sourceAvatar = avatar;
            mi.importAnimation = false;
            mi.importBlendShapes = true;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            mi.SaveAndReimport();
            return true;
        }

        private sealed class ManifestEvents { public readonly List<(string name, float fraction)> List = new List<(string, float)>(); }

        /// <summary>The manifest's events per state ("events": {"Poof": {"fraction": 0.3723, ...}}): JsonUtility cannot read a
        /// dictionary, so a tiny scan of the text.</summary>
        private static Dictionary<string, ManifestEvents> ReadEvents(string file)
        {
            var result = new Dictionary<string, ManifestEvents>();
            var root = MiniJsonLite.Parse(File.ReadAllText(file)) as Dictionary<string, object>;
            if (root == null || !(root.TryGetValue("clips", out object clips) && clips is List<object> list)) return result;
            foreach (object o in list)
            {
                if (!(o is Dictionary<string, object> c) || !(c.TryGetValue("state", out object st) && st is string state)) continue;
                var e = new ManifestEvents();
                if (c.TryGetValue("events", out object evs) && evs is Dictionary<string, object> map)
                    foreach (KeyValuePair<string, object> kv in map)
                        if (kv.Value is Dictionary<string, object> ev && ev.TryGetValue("fraction", out object f))
                            e.List.Add((kv.Key, Convert.ToSingle(f, CultureInfo.InvariantCulture)));
                e.List.Sort((a, b) => a.fraction.CompareTo(b.fraction));
                result[state] = e;
            }
            return result;
        }

        private static bool ConfigureClip(string path, Avatar avatar, string state, bool loop, ManifestEvents events, StringBuilder log)
        {
            var mi = (ModelImporter)AssetImporter.GetAtPath(path);
            if (mi == null) { log.AppendLine("  MISSING clip " + path); return false; }
            // preserveHierarchy: these FBX hold only the armature, which would otherwise become the asset root and drop the
            // "Buddy_Rig_Mixamo65/" prefix of every curve path (the model and the shared clips have it)
            bool baseOk = mi.animationType == ModelImporterAnimationType.Generic && mi.avatarSetup == ModelImporterAvatarSetup.CopyFromOther &&
                          mi.sourceAvatar == avatar && mi.importAnimation && mi.preserveHierarchy;
            ModelImporterClipAnimation[] current = mi.clipAnimations;
            int want = events?.List.Count ?? 0;
            if (baseOk && current.Length == 1 && current[0].name == state && current[0].loopTime == loop && (current[0].events?.Length ?? 0) == want) return false;
            if (!baseOk)
            {
                mi.animationType = ModelImporterAnimationType.Generic;
                mi.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
                mi.sourceAvatar = avatar;
                mi.importAnimation = true;
                mi.preserveHierarchy = true;
                mi.materialImportMode = ModelImporterMaterialImportMode.None;
                mi.SaveAndReimport();
            }
            ModelImporterClipAnimation[] takes = mi.defaultClipAnimations;
            if (takes.Length == 0) { log.AppendLine("  NO TAKE in " + path); return true; }
            ModelImporterClipAnimation clip = takes.FirstOrDefault(t => t.takeName.IndexOf(Path.GetFileNameWithoutExtension(path), StringComparison.OrdinalIgnoreCase) >= 0 ||
                                                                      t.takeName.EndsWith(state, StringComparison.OrdinalIgnoreCase)) ?? takes[0];
            clip.name = state;
            clip.loopTime = loop;
            clip.loop = false;
            clip.keepOriginalPositionY = true;
            clip.keepOriginalPositionXZ = false;
            clip.events = events != null
                ? events.List.Select(e => new AnimationEvent { time = Mathf.Clamp01(e.fraction), functionName = CueFunction, stringParameter = e.name }).ToArray()
                : new AnimationEvent[0];
            mi.clipAnimations = new[] { clip };
            mi.SaveAndReimport();
            log.AppendLine($"  clip {state,-24} take '{clip.takeName}' frames {clip.firstFrame:0}-{clip.lastFrame:0} loop {loop} events {want}");
            return true;
        }

        private static AnimationClip ClipIn(string fbx, string name = null)
        {
            AnimationClip[] clips = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__", StringComparison.Ordinal)).ToArray();
            return name != null ? clips.FirstOrDefault(c => c.name == name) ?? clips.FirstOrDefault() : clips.FirstOrDefault();
        }

        // ------------------------------------------------------------------ mask, controller, material

        private static AvatarMask BuildMask(GameObject model, StringBuilder log)
        {
            AvatarMask mask = AssetDatabase.LoadAssetAtPath<AvatarMask>(MaskPath);
            bool fresh = mask == null;
            if (fresh) mask = new AvatarMask();
            mask.transformCount = 0;
            mask.AddTransformPath(model.transform, true);
            int on = 0;
            for (int i = 0; i < mask.transformCount; i++)
            {
                string path = mask.GetTransformPath(i);
                string leaf = path.Substring(path.LastIndexOf('/') + 1);
                bool active = Array.IndexOf(GripBones, leaf) >= 0;
                mask.SetTransformActive(i, active);
                if (active) on++;
            }
            for (int p = 0; p < (int)AvatarMaskBodyPart.LastBodyPart; p++) mask.SetHumanoidBodyPartActive((AvatarMaskBodyPart)p, false);
            if (fresh) AssetDatabase.CreateAsset(mask, MaskPath); else EditorUtility.SetDirty(mask);
            log.AppendLine($"  mask {MaskPath}: {on}/{GripBones.Length} finger transforms of {mask.transformCount} active");
            return mask;
        }

        private static AnimatorController BuildController(Manifest manifest, AvatarMask mask, StringBuilder log)
        {
            AnimatorController c = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (c == null) c = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            while (c.layers.Length > 0) c.RemoveLayer(0);
            foreach (AnimatorControllerParameter p in c.parameters.ToArray()) c.RemoveParameter(p);
            c.AddParameter(new AnimatorControllerParameter { name = MechanicClips.WalkRateParam, type = AnimatorControllerParameterType.Float, defaultFloat = 1f });

            c.AddLayer("Base Layer");
            AnimatorStateMachine sm = c.layers[0].stateMachine;
            // Idle / Walk: his carry copies of the shared clips (the big wrench clear of the leg and floor), else the shared ones
            ManifestClip carryIdle = manifest.carry_clips?.FirstOrDefault(m => m.state == MechanicClips.Idle);
            ManifestClip carryWalk = manifest.carry_clips?.FirstOrDefault(m => m.state == MechanicClips.Walk);
            AnimationClip idle = (carryIdle != null ? ClipIn(AnimDir + "/" + carryIdle.file, MechanicClips.Idle) : null) ?? ClipIn(SharedIdle, "Idle");
            AnimationClip walk = (carryWalk != null ? ClipIn(AnimDir + "/" + carryWalk.file, MechanicClips.Walk) : null) ?? ClipIn(SharedWalk, "Walk");
            AnimatorState sIdle = sm.AddState(MechanicClips.Idle, new Vector3(300f, 0f, 0f));
            sIdle.motion = idle;
            AnimatorState sWalk = sm.AddState(MechanicClips.Walk, new Vector3(300f, 80f, 0f));
            sWalk.motion = walk;
            sWalk.speedParameterActive = true;
            sWalk.speedParameter = MechanicClips.WalkRateParam;
            sm.defaultState = sIdle;
            var states = new Dictionary<string, AnimatorState>();
            int row = 0;
            foreach (ManifestClip m in manifest.clips)
            {
                AnimatorState s = sm.AddState(m.state, new Vector3(600f, row++ * 60f, 0f));
                s.motion = ClipIn(AnimDir + "/" + m.file, m.state);
                states[m.state] = s;
            }
            // the attention enter flows into its loop on its own (the presenter also switches it by time)
            if (states.TryGetValue(MechanicClips.AttendEnter, out AnimatorState enter) && states.TryGetValue(MechanicClips.AttendLoop, out AnimatorState loopState))
            {
                AnimatorStateTransition t = enter.AddTransition(loopState);
                t.hasExitTime = true;
                t.exitTime = 1f;
                t.hasFixedDuration = true;
                t.duration = 0.1f;
            }

            c.AddLayer("HandGrip_R");
            AnimatorControllerLayer[] layers = c.layers;
            layers[1].defaultWeight = 1f;
            layers[1].blendingMode = AnimatorLayerBlendingMode.Override;
            layers[1].avatarMask = mask;
            AnimatorState grip = layers[1].stateMachine.AddState("Grip_R", new Vector3(300f, 0f, 0f));
            grip.motion = ClipIn(AnimDir + "/" + GripStem + ".fbx", "Grip_R");
            layers[1].stateMachine.defaultState = grip;
            c.layers = layers;
            EditorUtility.SetDirty(c);
            int missing = states.Values.Count(s => s.motion == null) + (idle == null ? 1 : 0) + (walk == null ? 1 : 0) + (grip.motion == null ? 1 : 0);
            log.AppendLine($"  controller {ControllerPath}: base {states.Count + 2} states (Idle '{(idle != null ? AssetDatabase.GetAssetPath(idle) : "NONE")}', Walk '{(walk != null ? AssetDatabase.GetAssetPath(walk) : "NONE")}' x WalkRate), " +
                           $"HandGrip_R override weight 1 mask {(mask != null ? mask.name : "NONE")} clip '{grip.motion?.name}'; {(missing == 0 ? "every state has its clip" : "MISSING clips: " + missing)}");
            return c;
        }

        private static Material BuildPuffMaterial(StringBuilder log)
        {
            Material m = AssetDatabase.LoadAssetAtPath<Material>(PuffMaterialPath);
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            if (lit == null) { log.AppendLine("  puff: URP Lit shader not found"); return m; }
            bool fresh = m == null;
            if (fresh) m = new Material(lit) { name = "MechanicPuff_v01" };
            m.shader = lit;
            var cream = new Color(0.97f, 0.94f, 0.86f);
            m.SetColor("_BaseColor", cream);
            m.SetFloat("_Smoothness", 0.12f);
            m.SetFloat("_Metallic", 0f);
            m.EnableKeyword("_EMISSION");
            m.SetColor("_EmissionColor", new Color(0.32f, 0.3f, 0.27f)); // reads against the garage's dim corners
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            if (fresh) AssetDatabase.CreateAsset(m, PuffMaterialPath); else EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------ prefab

        private static void BuildPrefab(GameObject model, AnimatorController controller, Avatar avatar, StringBuilder log)
        {
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                var root = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
                PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
                root.name = "Mechanic_W86_v02";
                root.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                // LOD0 under the plain part names (Face / Body / Outfit / Wrench_RightHand, as the crowd types keep them)
                foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (smr.name.EndsWith("_LOD0", StringComparison.Ordinal)) smr.gameObject.name = smr.name.Substring(0, smr.name.Length - 5);
                if (!root.TryGetComponent(out Animator animator)) animator = root.AddComponent<Animator>();
                animator.runtimeAnimatorController = controller;
                animator.avatar = avatar;
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                Lods(root, log);
                if (!root.TryGetComponent(out CapsuleCollider capsule)) capsule = root.AddComponent<CapsuleCollider>();
                capsule.radius = 0.32f;
                capsule.height = 1.75f;
                capsule.center = new Vector3(0f, 0.875f, 0f);
                capsule.direction = 1;
                if (!root.TryGetComponent(out MechanicW86PresenterV01 presenter)) presenter = root.AddComponent<MechanicW86PresenterV01>();
                presenter.FaceCues = AssetDatabase.LoadAssetAtPath<TextAsset>(CuesPath);
                foreach (var held in root.GetComponentsInChildren<OnlyVolunteers.Characters.NpcHeldProps>(true)) Object.DestroyImmediate(held);
                var parts = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Select(r => r.name).OrderBy(n => n).ToArray();
                var tris = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).GroupBy(r => r.name.Contains("_LOD") ? r.name.Substring(r.name.IndexOf("_LOD", StringComparison.Ordinal) + 1) : "LOD0")
                    .OrderBy(g => g.Key).Select(g => g.Key + " " + g.Sum(r => r.sharedMesh != null ? r.sharedMesh.triangles.Length / 3 : 0)).ToArray();
                SkinnedMeshRenderer wrench = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault(r => r.name == "Wrench_RightHand");
                string wrenchBones = wrench != null ? string.Join(",", WeightedBones(wrench)) : "NO WRENCH";
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath, out bool ok);
                log.AppendLine($"  prefab {(ok ? "saved" : "FAILED")}: {PrefabPath}; renderers {string.Join(", ", parts)}; tris {string.Join(" / ", tris)}; wrench weighted to [{wrenchBones}]; no NpcHeldProps");
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        private static IEnumerable<string> WeightedBones(SkinnedMeshRenderer r)
        {
            Mesh m = r.sharedMesh;
            if (m == null) return new string[0];
            var used = new HashSet<int>();
            foreach (BoneWeight w in m.boneWeights)
            {
                if (w.weight0 > 0f) used.Add(w.boneIndex0);
                if (w.weight1 > 0f) used.Add(w.boneIndex1);
                if (w.weight2 > 0f) used.Add(w.boneIndex2);
                if (w.weight3 > 0f) used.Add(w.boneIndex3);
            }
            return used.Where(i => i >= 0 && i < r.bones.Length && r.bones[i] != null).Select(i => r.bones[i].name);
        }

        /// <summary>One LODGroup on the root: level n = every part's _LODn (LOD0 = the renamed plain parts).</summary>
        private static void Lods(GameObject root, StringBuilder log)
        {
            var levels = new List<Renderer>[3];
            for (int l = 0; l < 3; l++) levels[l] = new List<Renderer>();
            foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = 0;
                int at = smr.name.LastIndexOf("_LOD", StringComparison.Ordinal);
                if (at >= 0 && int.TryParse(smr.name.Substring(at + 4), out int n)) lod = n;
                if (lod >= 0 && lod < 3) levels[lod].Add(smr);
            }
            foreach (LODGroup old in root.GetComponentsInChildren<LODGroup>(true)) if (old.gameObject != root) Object.DestroyImmediate(old);
            if (!root.TryGetComponent(out LODGroup group)) group = root.AddComponent<LODGroup>();
            int count = levels[2].Count > 0 ? 3 : levels[1].Count > 0 ? 2 : 1;
            var lods = new LOD[count];
            for (int l = 0; l < count; l++) lods[l] = new LOD(LodHeights[Math.Min(l, LodHeights.Length - 1)], levels[l].ToArray());
            group.fadeMode = LODFadeMode.None;
            group.SetLODs(lods);
            group.RecalculateBounds();
            log.AppendLine($"  LODGroup: {string.Join(" / ", levels.Take(count).Select((v, i) => $"LOD{i} {v.Count} renderers @{LodHeights[i]:0.###}"))}");
        }

        // ------------------------------------------------------------------ a tiny JSON reader (dictionaries + lists)

        private static class MiniJsonLite
        {
            public static object Parse(string s) { int i = 0; return Value(s, ref i); }

            private static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

            private static object Value(string s, ref int i)
            {
                Ws(s, ref i);
                char c = s[i];
                if (c == '{')
                {
                    var d = new Dictionary<string, object>();
                    i++;
                    Ws(s, ref i);
                    if (s[i] == '}') { i++; return d; }
                    while (true)
                    {
                        Ws(s, ref i);
                        string k = Str(s, ref i);
                        Ws(s, ref i);
                        i++; // ':'
                        d[k] = Value(s, ref i);
                        Ws(s, ref i);
                        if (s[i++] == '}') return d;
                    }
                }
                if (c == '[')
                {
                    var l = new List<object>();
                    i++;
                    Ws(s, ref i);
                    if (s[i] == ']') { i++; return l; }
                    while (true)
                    {
                        l.Add(Value(s, ref i));
                        Ws(s, ref i);
                        if (s[i++] == ']') return l;
                    }
                }
                if (c == '"') return Str(s, ref i);
                int start = i;
                while (i < s.Length && ",}] \r\n\t".IndexOf(s[i]) < 0) i++;
                string tok = s.Substring(start, i - start);
                if (tok == "true") return true;
                if (tok == "false") return false;
                if (tok == "null") return null;
                return double.Parse(tok, CultureInfo.InvariantCulture);
            }

            private static string Str(string s, ref int i)
            {
                var sb = new StringBuilder();
                i++; // opening quote
                while (s[i] != '"')
                {
                    if (s[i] == '\\')
                    {
                        i++;
                        char e = s[i];
                        if (e == 'u') { sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; }
                        else sb.Append(e == 'n' ? '\n' : e == 't' ? '\t' : e == 'r' ? '\r' : e);
                    }
                    else sb.Append(s[i]);
                    i++;
                }
                i++;
                return sb.ToString();
            }
        }
    }
}
