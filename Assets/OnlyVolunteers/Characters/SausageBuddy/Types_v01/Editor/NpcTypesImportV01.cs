using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Player.Physics;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Characters.Types
{
    // G44 phase 1 ("integrate only"): Vadim's finished NPC types into Unity, nothing in them changed.
    // Import: copies each pool type's FBX (current revision, README "Пул NPC по районам") from
    // ArtSource/Characters/SAUSAGE_BUDDY_01/Types into Types_v01/Models (never over an existing file) and imports it like
    // Buddy A v04 (Generic; Copy From Other Avatar = Buddy A's, so every existing clip binds; materials embedded from the
    // FBX as for A/B; the type's own Idle take is not imported: the controller plays the shared clips); a visual prefab
    // per type built as GreyboxBuddySetup.EnsurePrefabs builds SausageBuddy_A (Animator with SausageBuddy_Greybox and A's
    // avatar, no root motion, always animate, NpcRig; NpcHeldProps when it has Props_*Hand meshes; npc_type.game_scale as
    // scale); a preset per type (NpcTypePreset) and the district spawn tables (NpcSpawnTables_v01.asset). The log lists
    // per type the bones matched against Buddy A, their largest deviation from A under A's Idle, triangles, height and the feet under Buddy A's
    // Idle (sinking or floating).
    // AddTypeTemplates (phase 2 / smoke test): one inactive crowd template per type next to a CrowdDirector's own.
    public static class NpcTypesImportV01
    {
        public const string Root = "Assets/OnlyVolunteers/Characters/SausageBuddy/Types_v01";
        public const string ModelsDir = Root + "/Models";
        public const string PrefabsDir = Root + "/Prefabs";
        public const string PresetsDir = Root + "/Data/Presets";
        public const string TablesPath = Root + "/Data/NpcSpawnTables_v01.asset";
        private const string SourceDir = "ArtSource/Characters/SAUSAGE_BUDDY_01/Types";
        private const string BuddyDir = "Assets/OnlyVolunteers/Characters/SausageBuddy";
        private const string BuddyAFbx = BuddyDir + "/SAUSAGE_BUDDY_A_v04.fbx";
        private const string ControllerPath = BuddyDir + "/SausageBuddy_Greybox.controller";
        private const string GrabProfilePath = "Assets/OnlyVolunteers/Map/Data/NpcGrabProfile.asset";
        private const string MoundFbx = "BEACH_BURIED_SandMound_v01.fbx";
        private const float HeavyTriangles = 20000f; // the crowd budget is 12-15k (handoff v02 §11)
        // Lighter LOD0 derivatives of the heavy types (ArtSource/.../Types_opt_v01/build_types_opt_v01.py): same rig, object
        // names and materials, hidden faces removed and the outfit decimated within 1.5 mm. A type with an opt FBX there is
        // imported from it; the source revision stays in ArtSource (and its old copy in Models).
        // TASK-000900: Types_opt_v02 (build_types_opt_v02.py, its README): opt_v01 minus the hidden face interior as LOD0,
        // plus crowd levels LOD1 (~50 %) / LOD2 (~27 %), Unity's LOD names <name>_LOD0/1/2 in one FBX per type (see LODs below).
        private const string OptDir = "ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v02";
        private const string OptTag = "opt_v02";
        // LOD switch distances: the opt_v02 error limits hold at 15 m (LOD1) and 40 m (LOD2); LOD2 is culled at ~150 m
        // (README: ~1 % of the screen height). Screen heights for a 1.8 m figure seen by the play camera (FOV 75 at runtime in
        // Map_W85_Play_v02) at the quality level's LOD bias (2 on PC), as V3Props17 / W86Decals do.
        private const float GameFov = 75f, LodFigureM = 1.8f;
        private static readonly float[] LodDistancesM = { 15f, 40f, 150f };

        // Vadim's approved pool with current revisions (README of SAUSAGE_BUDDY_01, TASK-000506..000545).
        // W86 (Vadim 976100c7, TASK-000859..000897): CONSTR_INDIAN v08 / MEXICAN v05 / UZBEK v05 replace v07 / v04 / v04;
        // new HAMLET_MUZHIK and OLD_POPKING walk (Hamlet / Downtown tables); the rest of that push is ImportOnly below.
        public static readonly (string id, int rev)[] Pool =
        {
            ("FOREST_OD_JUNKIE", 1), ("FOREST_STASHER", 3),
            ("HAMLET_GRANNY", 7), ("HAMLET_SHEPHERD", 6), ("HAMLET_BODYBUILDER", 4), ("HAMLET_BOXERS_GRANDPA", 5),
            ("CONSTR_INDIAN", 8), ("CONSTR_UZBEK", 5), ("CONSTR_MEXICAN", 5), ("CONSTR_AFROAMERICAN", 5), ("CONSTR_ARAB", 5),
            ("BAD_GOPNIK", 5), ("BAD_RAPPER", 10), ("BAD_HUSTLER", 4), ("BAD_DRUNK", 4), ("BAD_GIRL", 7), ("BAD_BOMZH", 1),
            ("BAD_BOMZHIHA", 2), ("BAD_VAPER", 2), ("BAD_ALTGIRL", 14),
            ("OLD_RAPPER", 1), ("OLD_STREAMER", 9), ("OLD_STUDENT", 8), ("OLD_OFFICE", 4), ("OLD_FITNESS", 5), ("OLD_COURIER", 5),
            ("OLD_BUSINESSMAN", 3), ("OLD_KAREN", 6),
            ("PROM_FOREMAN", 4), ("PROM_SAILOR", 3),
            ("BEACH_CORN", 3), ("BEACH_CASTLE", 1), ("BEACH_SUNBURN", 2), ("BEACH_LIFEGUARD", 3), ("BEACH_DETECTOR", 3),
            ("BEACH_NUDIST", 1), ("BEACH_BURIED", 1),
            ("HAMLET_MUZHIK", 1), ("OLD_POPKING", 1),
            ("HAMLET_HUNTER_GRANDPA", 1), ("POLICE_THIN", 2), ("POLICE_FAT", 2), ("FBI_AGENT", 1), ("ARMY_SOLDIER", 1),
            ("TRAMDURO", 1), ("VIP_BEASTMAN", 1), ("VIP_SPEEDSTER", 1), ("VIP_BLINDFOLD", 1),
        };

        /// <summary>Types with a prefab and a preset but no spawn-table row (W86): their systems do not exist yet (hunter
        /// responder, police crews, Elite gate trap / FBI, island garrison, Tramduro finale, VIP special orders). BAD_ALTGIRL
        /// left the Rough table (Vadim TASK-000883: VIP only); her prefab and preset stay.</summary>
        public static readonly string[] ImportOnly =
        {
            "HAMLET_HUNTER_GRANDPA", "POLICE_THIN", "POLICE_FAT", "FBI_AGENT", "ARMY_SOLDIER", "TRAMDURO",
            "VIP_BEASTMAN", "VIP_SPEEDSTER", "VIP_BLINDFOLD", "BAD_ALTGIRL",
        };

        /// <summary>The 14 models of Vadim's commit 976100c7, imported by ImportW86 from their opt_v01 derivatives.</summary>
        public static readonly string[] W86Types =
        {
            "CONSTR_INDIAN", "CONSTR_MEXICAN", "CONSTR_UZBEK", "HAMLET_MUZHIK", "OLD_POPKING", "HAMLET_HUNTER_GRANDPA",
            "POLICE_THIN", "POLICE_FAT", "FBI_AGENT", "ARMY_SOLDIER", "TRAMDURO", "VIP_BEASTMAN", "VIP_SPEEDSTER", "VIP_BLINDFOLD",
        };

        [MenuItem("Tools/Only Volunteers/Characters/NPC Types v01: Import, Presets, Spawn Tables")]
        public static void ImportMenu() => Debug.Log(Import());

        public static string Import()
        {
            var log = new StringBuilder("[NpcTypesV01] import\n");
            string project = Path.GetDirectoryName(Application.dataPath);
            foreach (string dir in new[] { ModelsDir, PrefabsDir, PresetsDir }) EnsureFolder(dir);

            // 1. Files (copied once).
            var copied = new List<string>();
            foreach ((string id, int rev) in Pool) Copy(project, SourceFbx(project, id, rev), $"{ModelsDir}/{ModelName(project, id, rev)}", copied);
            Copy(project, $"{SourceDir}/BEACH_BURIED/{MoundFbx}", $"{ModelsDir}/{MoundFbx}", copied);
            foreach (string path in copied) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            log.AppendLine($"  copied {copied.Count} FBX into {ModelsDir}");

            // 2. Importers.
            Avatar avatar = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is Avatar a) avatar = a;
            if (avatar == null) throw new InvalidOperationException("Buddy A v04 has no avatar: " + BuddyAFbx);
            int reimported = 0;
            foreach ((string id, int rev) in Pool) if (ConfigureType($"{ModelsDir}/{ModelName(project, id, rev)}", avatar)) reimported++;
            if (ConfigureStatic($"{ModelsDir}/{MoundFbx}")) reimported++;
            log.AppendLine($"  importers set: {reimported} re-imported");

            // 3. Prefabs, presets, checks.
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            GameObject buddyA = AssetDatabase.LoadAssetAtPath<GameObject>(BuddyAFbx);
            AnimationClip idle = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is AnimationClip c && c.name == "Idle") idle = c;
            Scene scene = EditorSceneManager.NewPreviewScene();
            var presets = new Dictionary<string, NpcTypePreset>();
            try
            {
                var refInstance = (GameObject)PrefabUtility.InstantiatePrefab(buddyA, scene);
                if (idle != null) idle.SampleAnimation(refInstance, 0f);
                Dictionary<string, Transform> refBones = Bones(refInstance);
                float refFeet = FeetUnderIdle((GameObject)PrefabUtility.InstantiatePrefab(buddyA, scene), idle);
                log.AppendLine(Inv($"  Buddy A v04 under its Idle: lowest vertex {refFeet:0.000} m"));
                log.AppendLine("  type                    rev bones  dPos(m) dRot(deg) tris    height  feet(Idle) scale lift props");
                foreach ((string id, int rev) in Pool)
                {
                    NpcTypePreset preset = ImportOne(project, id, rev, scene, refBones, refFeet, idle, controller, avatar, false, log);
                    if (preset != null) presets[id] = preset;
                }
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }

            // 4. Spawn tables.
            WriteTables(presets, AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelsDir}/{MoundFbx}"));
            AssetDatabase.SaveAssets();
            log.AppendLine($"  {presets.Count} presets in {PresetsDir}, spawn tables {TablesPath}");
            return log.ToString();
        }

        // One type: checks against Buddy A, prefab, preset; one log row. keepPrefab: an existing prefab is not rebuilt but
        // pointed at the new model (UpdatePrefab: the prefab's objects and file IDs stay, so scene instances keep their
        // overrides); only when the model's renderers cannot be matched is it rebuilt.
        private static NpcTypePreset ImportOne(string project, string id, int rev, Scene scene, Dictionary<string, Transform> refBones, float refFeet,
            AnimationClip idle, AnimatorController controller, Avatar avatar, bool keepPrefab, StringBuilder log)
        {
            string fbx = $"{ModelsDir}/{ModelName(project, id, rev)}";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
            if (model == null) { log.AppendLine($"  {id}: MISSING model {fbx}"); return null; }
            Validation v = ReadValidation(project, id, rev);
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
            if (idle != null) idle.SampleAnimation(instance, 0f);
            Compare(refBones, Bones(instance), out int matched, out float dPos, out float dRot);
            int tris = 0;
            var bounds = new Bounds();
            bool any = false, props = false;
            foreach (SkinnedMeshRenderer smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (LodOf(smr.name, out string part) > 0) continue; // LOD0 only
                if (smr.sharedMesh != null) tris += smr.sharedMesh.triangles.Length / 3;
                if (any) bounds.Encapsulate(smr.bounds); else { bounds = smr.bounds; any = true; }
                if (part.StartsWith("Props_") && part.EndsWith("Hand")) props = true;
            }
            float feet = FeetUnderIdle((GameObject)PrefabUtility.InstantiatePrefab(model, scene), idle);
            float scale = v.npc_type != null && v.npc_type.game_scale > 0f ? v.npc_type.game_scale : 1f;
            float lift = v.grounding_offset_m != null && v.grounding_offset_m.Idle > 0.02f ? v.grounding_offset_m.Idle : 0f;
            string prefabPath = $"{PrefabsDir}/SausageBuddy_{id}.prefab";
            string how = "built";
            GameObject prefab = null;
            if (keepPrefab && AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) != null)
            {
                string error = UpdatePrefab(prefabPath, model, props, scale, out string changes);
                if (error == null) { prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath); how = "updated in place" + changes; }
                else how = "REBUILT (" + error + ")";
            }
            if (prefab == null) prefab = BuildPrefab(model, scene, id, controller, avatar, props, scale);
            NpcTypePreset preset = WritePreset(id, rev, v, prefab, SourceFbx(project, id, rev), tris, props, scale, lift);
            log.AppendLine(Inv($"  {id,-23} v{rev:00} {matched,2}/{refBones.Count} {dPos,7:0.0000} {dRot,7:0.00}  {tris,6} {bounds.size.y,6:0.000} {feet - refFeet,8:+0.000;-0.000} {scale,5:0.00} {lift,4:0.00} {(props ? "hand" : "-")}") +
                           (tris > HeavyTriangles ? "  HEAVY" : "") + (matched < refBones.Count || dPos > 0.01f || dRot > 1f ? "  RIG DIFFERS" : "") +
                           (keepPrefab ? "  prefab " + how : ""));
            return preset;
        }

        [MenuItem("Tools/Only Volunteers/Characters/NPC Types v01: Import W86 additions (Vadim 976100c7)")]
        public static void ImportW86Menu() => Debug.Log(ImportW86());

        /// <summary>W86: only the 14 models of Vadim's commit 976100c7 (W86Types), from their opt_v01 derivatives: copied into
        /// Models under their new names (the older revisions' files stay), importers set like the pool's, the CONSTR updates'
        /// prefabs re-pointed in place, new prefabs and presets for the rest, then the spawn tables rewritten (WriteTables:
        /// MUZHIK in the Hamlet, POPKING in Downtown, BAD_ALTGIRL out of Rough; ImportOnly types get no rows). The other 35
        /// types' prefabs and presets are not touched.</summary>
        public static string ImportW86()
        {
            var log = new StringBuilder("[NpcTypesV01] W86 additions (Vadim 976100c7)\n");
            string project = Path.GetDirectoryName(Application.dataPath);
            foreach (string dir in new[] { ModelsDir, PrefabsDir, PresetsDir }) EnsureFolder(dir);
            var revs = new Dictionary<string, int>();
            foreach ((string id, int rev) in Pool) revs[id] = rev;
            var copied = new List<string>();
            foreach (string id in W86Types)
            {
                if (!HasOpt(project, id, revs[id])) log.AppendLine($"  {id}: WARNING no opt_v01 FBX, the source revision is used");
                Copy(project, SourceFbx(project, id, revs[id]), $"{ModelsDir}/{ModelName(project, id, revs[id])}", copied);
            }
            foreach (string path in copied) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            log.AppendLine($"  copied {copied.Count} FBX into {ModelsDir}");
            Avatar avatar = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is Avatar a) avatar = a;
            if (avatar == null) throw new InvalidOperationException("Buddy A v04 has no avatar: " + BuddyAFbx);
            int reimported = 0;
            foreach (string id in W86Types) if (ConfigureType($"{ModelsDir}/{ModelName(project, id, revs[id])}", avatar)) reimported++;
            log.AppendLine($"  importers set: {reimported} re-imported");

            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            GameObject buddyA = AssetDatabase.LoadAssetAtPath<GameObject>(BuddyAFbx);
            AnimationClip idle = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is AnimationClip c && c.name == "Idle") idle = c;
            var presets = new Dictionary<string, NpcTypePreset>();
            foreach ((string id, int _) in Pool)
            {
                var existing = AssetDatabase.LoadAssetAtPath<NpcTypePreset>($"{PresetsDir}/{id}.asset");
                if (existing != null) presets[id] = existing;
            }
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                var refInstance = (GameObject)PrefabUtility.InstantiatePrefab(buddyA, scene);
                if (idle != null) idle.SampleAnimation(refInstance, 0f);
                Dictionary<string, Transform> refBones = Bones(refInstance);
                float refFeet = FeetUnderIdle((GameObject)PrefabUtility.InstantiatePrefab(buddyA, scene), idle);
                log.AppendLine(Inv($"  Buddy A v04 under its Idle: lowest vertex {refFeet:0.000} m"));
                log.AppendLine("  type                    rev bones  dPos(m) dRot(deg) tris    height  feet(Idle) scale lift props");
                foreach (string id in W86Types)
                {
                    NpcTypePreset preset = ImportOne(project, id, revs[id], scene, refBones, refFeet, idle, controller, avatar, true, log);
                    if (preset != null) presets[id] = preset;
                }
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
            WriteTables(presets, AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelsDir}/{MoundFbx}"));
            AssetDatabase.SaveAssets();
            var tables = AssetDatabase.LoadAssetAtPath<NpcSpawnTables>(TablesPath);
            foreach (NpcSpawnTables.District d in tables.Districts)
            {
                var names = new List<string>();
                foreach (NpcSpawnTables.Entry e in d.Entries) names.Add(e.Type != null ? e.Type.TypeId : "null");
                log.AppendLine($"  table {d.Id}: {(names.Count > 0 ? string.Join(", ", names) : "-")}");
            }
            log.AppendLine($"  import only (no rows): {string.Join(", ", ImportOnly)}");
            return log.ToString();
        }

        // Re-points an existing type prefab at a new revision's model without rebuilding it (as ApplyOptimized does):
        // same-named skinned renderers get the new mesh, materials, bones (by name) and bounds; a Props_* renderer the new
        // model no longer has is removed; NpcHeldProps follows the props; the root scale follows game_scale. Null = saved;
        // otherwise the reason it could not (a renderer only the new model has, a bone missing) and nothing is saved.
        private static string UpdatePrefab(string prefabPath, GameObject model, bool props, float scale, out string changes)
        {
            changes = "";
            GameObject root = PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                if ((root.transform.localScale - Vector3.one * scale).sqrMagnitude > 1e-8f) { root.transform.localScale = Vector3.one * scale; changes += Inv($", scale {scale:0.00}"); }
                string error = Repoint(root, model, ref changes, out _, out _);
                if (error != null) return error;
                bool hasHeld = root.TryGetComponent(out NpcHeldProps held);
                if (props && !hasHeld) { root.AddComponent<NpcHeldProps>(); changes += ", + NpcHeldProps"; }
                else if (!props && hasHeld) { Object.DestroyImmediate(held); changes += ", - NpcHeldProps"; }
                PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
                return null;
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(root);
            }
        }

        // ---------- LODs (Types_opt_v02) ----------

        /// <summary>Unity's LOD naming: 0 for "Body" or "Body_LOD0", n for "Body_LODn"; part = "Body".</summary>
        public static int LodOf(string name, out string part)
        {
            int i = name.LastIndexOf("_LOD", StringComparison.Ordinal);
            if (i > 0 && i + 4 < name.Length && int.TryParse(name.Substring(i + 4), NumberStyles.None, CultureInfo.InvariantCulture, out int lod))
            {
                part = name.Substring(0, i);
                return lod;
            }
            part = name;
            return 0;
        }

        // Points an opened prefab (root) at a model's meshes without rebuilding it. The prefab keeps LOD0 under the plain
        // names (Body, Face, Outfit, Props_*: KeepAppearance, CaptureUndress, OperationPatientRig and the type checks look
        // them up by name): its renderer X takes the model's X / X_LOD0 mesh, materials, bones (by name), root bone and
        // bounds. The model's X_LOD1 / X_LOD2 go onto sibling renderers X_LOD1 / X_LOD2 (made next to X when missing, with
        // X's layer and render settings); levels the model no longer has are removed, and so is a Props_* renderer the new
        // model lacks (with its levels). Then the LODGroup (SetupLods). tris[level] = the model's triangles per level.
        // Null = done; otherwise the reasons (a part only one side has, a bone missing) and nothing is changed.
        private static string Repoint(GameObject root, GameObject model, ref string changes, out int before, out int[] tris)
        {
            before = 0;
            tris = Array.Empty<int>();
            var source = new Dictionary<(string part, int lod), SkinnedMeshRenderer>();
            int maxLod = 0;
            foreach (SkinnedMeshRenderer smr in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = LodOf(smr.name, out string part);
                source[(part, lod)] = smr;
                maxLod = Math.Max(maxLod, lod);
            }
            var byName = new Dictionary<string, Transform>();
            foreach (Transform t in root.GetComponentsInChildren<Transform>(true)) if (!byName.ContainsKey(t.name)) byName.Add(t.name, t);
            var lod0 = new List<SkinnedMeshRenderer>();
            var levels = new Dictionary<(string part, int lod), SkinnedMeshRenderer>();
            foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = LodOf(smr.name, out string part);
                if (lod == 0) lod0.Add(smr); else levels[(part, lod)] = smr;
            }
            var errors = new List<string>();
            var drop = new List<SkinnedMeshRenderer>();
            var have = new HashSet<string>();
            foreach (SkinnedMeshRenderer smr in lod0)
            {
                LodOf(smr.name, out string part);
                have.Add(part);
                if (source.ContainsKey((part, 0))) continue;
                if (part.StartsWith("Props_")) drop.Add(smr); else errors.Add($"no {part} in the new model");
            }
            foreach ((string part, int lod) in source.Keys)
            {
                if (lod == 0 && !have.Contains(part)) errors.Add($"{part} only in the new model");
                if (lod > 0 && !source.ContainsKey((part, 0))) errors.Add($"{part}_LOD{lod} without its LOD0");
            }
            var bones = new Dictionary<SkinnedMeshRenderer, Transform[]>();
            foreach (SkinnedMeshRenderer src in source.Values)
            {
                var mapped = new Transform[src.bones.Length];
                for (int i = 0; i < mapped.Length; i++)
                    if (src.bones[i] == null || !byName.TryGetValue(src.bones[i].name, out mapped[i])) errors.Add($"{src.name}: bone {src.bones[i]?.name} missing");
                if (src.rootBone != null && !byName.ContainsKey(src.rootBone.name)) errors.Add($"{src.name}: root bone {src.rootBone.name} missing");
                bones[src] = mapped;
            }
            if (errors.Count > 0) return string.Join("; ", errors);

            tris = new int[maxLod + 1];
            foreach (SkinnedMeshRenderer smr in drop)
            {
                LodOf(smr.name, out string part);
                foreach (var key in new List<(string part, int lod)>(levels.Keys))
                    if (key.part == part) { Object.DestroyImmediate(levels[key].gameObject); levels.Remove(key); }
                changes += $", removed {smr.name}";
                Object.DestroyImmediate(smr.gameObject);
            }
            var kept = new HashSet<string>();
            foreach (SkinnedMeshRenderer smr in lod0)
            {
                if (smr == null) continue; // dropped above
                LodOf(smr.name, out string part);
                kept.Add(part);
                before += Tris(smr.sharedMesh);
                SkinnedMeshRenderer src = source[(part, 0)];
                Assign(smr, src, bones[src], byName);
                tris[0] += Tris(src.sharedMesh);
                for (int lod = 1; lod <= maxLod; lod++)
                {
                    levels.TryGetValue((part, lod), out SkinnedMeshRenderer level);
                    if (!source.TryGetValue((part, lod), out SkinnedMeshRenderer srcLevel))
                    {
                        if (level != null) { Object.DestroyImmediate(level.gameObject); levels.Remove((part, lod)); }
                        continue;
                    }
                    if (level == null) levels[(part, lod)] = level = MakeLevel(smr, $"{part}_LOD{lod}");
                    Assign(level, srcLevel, bones[srcLevel], byName);
                    tris[lod] += Tris(srcLevel.sharedMesh);
                }
            }
            // Levels left without their LOD0 part or above the model's coarsest level.
            foreach (var kv in new List<KeyValuePair<(string part, int lod), SkinnedMeshRenderer>>(levels))
                if (kv.Value != null && (!kept.Contains(kv.Key.part) || kv.Key.lod > maxLod)) { Object.DestroyImmediate(kv.Value.gameObject); levels.Remove(kv.Key); }
            SetupLods(root);
            return null;
        }

        private static int Tris(Mesh mesh) => mesh != null ? mesh.triangles.Length / 3 : 0;

        private static void Assign(SkinnedMeshRenderer smr, SkinnedMeshRenderer src, Transform[] bones, Dictionary<string, Transform> byName)
        {
            smr.sharedMesh = src.sharedMesh;
            smr.sharedMaterials = src.sharedMaterials;
            smr.bones = bones;
            smr.rootBone = src.rootBone != null ? byName[src.rootBone.name] : null;
            smr.localBounds = src.localBounds;
        }

        // A coarser level of part X: a sibling of X with X's pose, layer and render settings.
        private static SkinnedMeshRenderer MakeLevel(SkinnedMeshRenderer lod0, string name)
        {
            var go = new GameObject(name) { layer = lod0.gameObject.layer };
            go.transform.SetParent(lod0.transform.parent, false);
            go.transform.SetLocalPositionAndRotation(lod0.transform.localPosition, lod0.transform.localRotation);
            go.transform.localScale = lod0.transform.localScale;
            var r = go.AddComponent<SkinnedMeshRenderer>();
            r.shadowCastingMode = lod0.shadowCastingMode;
            r.receiveShadows = lod0.receiveShadows;
            r.updateWhenOffscreen = lod0.updateWhenOffscreen;
            r.quality = lod0.quality;
            r.skinnedMotionVectors = lod0.skinnedMotionVectors;
            r.motionVectorGenerationMode = lod0.motionVectorGenerationMode;
            r.lightProbeUsage = lod0.lightProbeUsage;
            r.reflectionProbeUsage = lod0.reflectionProbeUsage;
            r.probeAnchor = lod0.probeAnchor;
            r.renderingLayerMask = lod0.renderingLayerMask;
            r.allowOcclusionWhenDynamic = lod0.allowOcclusionWhenDynamic;
            r.enabled = lod0.enabled;
            return r;
        }

        // The LODGroup on the prefab root: level 0 = every part's LOD0, level n = X_LODn where the part has it, else its
        // next finer level (every part stays drawn down to the cull). Switches at LodDistancesM for a LodFigureM figure
        // (size and reference point set, not from the bind-pose bounds); no LOD renderers = no LODGroup.
        private static void SetupLods(GameObject root)
        {
            var parts = new Dictionary<string, SortedDictionary<int, Renderer>>();
            int maxLod = 0;
            foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = LodOf(smr.name, out string part);
                if (!parts.TryGetValue(part, out var p)) parts[part] = p = new SortedDictionary<int, Renderer>();
                p[lod] = smr;
                maxLod = Math.Max(maxLod, lod);
            }
            foreach (LODGroup old in root.GetComponentsInChildren<LODGroup>(true)) if (old.gameObject != root) Object.DestroyImmediate(old);
            root.TryGetComponent(out LODGroup group);
            if (maxLod == 0)
            {
                if (group != null) Object.DestroyImmediate(group);
                return;
            }
            var levels = new List<Renderer>[maxLod + 1];
            for (int l = 0; l <= maxLod; l++) levels[l] = new List<Renderer>();
            foreach (SortedDictionary<int, Renderer> p in parts.Values)
            {
                if (!p.ContainsKey(0)) continue;
                Renderer last = null;
                for (int l = 0; l <= maxLod; l++)
                {
                    if (p.TryGetValue(l, out Renderer r)) last = r;
                    levels[l].Add(last);
                }
            }
            if (group == null) group = root.AddComponent<LODGroup>();
            float k = Mathf.Max(0.1f, QualitySettings.lodBias) * LodFigureM / (2f * Mathf.Tan(GameFov * 0.5f * Mathf.Deg2Rad));
            var lods = new LOD[maxLod + 1];
            float previous = 1f;
            for (int l = 0; l <= maxLod; l++)
            {
                // the last level ends at the cull distance, the others at 15 m / 40 m
                float d = l == maxLod ? LodDistancesM[LodDistancesM.Length - 1] : LodDistancesM[Math.Min(l, LodDistancesM.Length - 2)];
                previous = Mathf.Min(previous * 0.999f, Mathf.Clamp(k / d, 0.001f, 0.99f));
                lods[l] = new LOD(previous, levels[l].ToArray());
            }
            group.fadeMode = LODFadeMode.None;
            group.animateCrossFading = false;
            group.SetLODs(lods);
            Vector3 s = root.transform.lossyScale;
            float scale = Mathf.Max(1e-3f, Mathf.Max(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z)));
            group.localReferencePoint = new Vector3(0f, LodFigureM * 0.5f / scale, 0f);
            group.size = LodFigureM / scale;
        }

        private static string FbxName(string id, int rev) => $"SAUSAGE_BUDDY_{id}_v{rev:00}.fbx";
        private static string OptName(string id, int rev) => $"SAUSAGE_BUDDY_{id}_v{rev:00}_{OptTag}.fbx";
        private static bool HasOpt(string project, string id, int rev) => File.Exists(Path.Combine(project, OptDir, OptName(id, rev)));
        private static string ModelName(string project, string id, int rev) => HasOpt(project, id, rev) ? OptName(id, rev) : FbxName(id, rev);
        private static string SourceFbx(string project, string id, int rev) =>
            HasOpt(project, id, rev) ? $"{OptDir}/{OptName(id, rev)}" : $"{SourceDir}/{id}/{FbxName(id, rev)}";

        [MenuItem("Tools/Only Volunteers/Characters/NPC Types v01: Use Optimized Meshes + crowd LODs (opt_v02)")]
        public static void ApplyOptimizedMenu() => Debug.Log(ApplyOptimized());

        /// <summary>Points the existing type prefabs at the opt meshes (OptDir, now opt_v02 with LODs) without rebuilding
        /// them: copies and imports each opt FBX like the source FBX, then Repoint: every LOD0 SkinnedMeshRenderer keeps its
        /// name and gets the new mesh, materials, bones (by name) and bounds, the LOD1 / LOD2 renderers are added next to it
        /// and a LODGroup on the root; the prefab's other objects, components, colliders and file IDs (the scene instances'
        /// overrides) stay as they are; the preset gets the new source and LOD0 triangle count. Spawn tables and placements
        /// are not touched. Types without an opt FBX are skipped.</summary>
        public static string ApplyOptimized()
        {
            var log = new StringBuilder($"[NpcTypesV01] {OptTag} meshes\n");
            string project = Path.GetDirectoryName(Application.dataPath);
            Avatar avatar = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is Avatar a) avatar = a;
            if (avatar == null) throw new InvalidOperationException("Buddy A v04 has no avatar: " + BuddyAFbx);
            int done = 0, failed = 0;
            foreach ((string id, int rev) in Pool)
            {
                if (!HasOpt(project, id, rev)) continue;
                string target = $"{ModelsDir}/{OptName(id, rev)}";
                var copied = new List<string>();
                Copy(project, $"{OptDir}/{OptName(id, rev)}", target, copied);
                foreach (string path in copied) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                ConfigureType(target, avatar);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(target);
                string prefabPath = $"{PrefabsDir}/SausageBuddy_{id}.prefab";
                if (model == null || AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) == null)
                {
                    log.AppendLine($"  {id}: MISSING {(model == null ? target : prefabPath)}");
                    failed++;
                    continue;
                }
                GameObject root = PrefabUtility.LoadPrefabContents(prefabPath);
                int before;
                int[] tris;
                string error, changes = "";
                try
                {
                    error = Repoint(root, model, ref changes, out before, out tris);
                    if (error == null) PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
                if (error != null)
                {
                    log.AppendLine($"  {id}: NOT CHANGED: {error}");
                    failed++;
                    continue;
                }
                int after = tris.Length > 0 ? tris[0] : 0;
                var preset = AssetDatabase.LoadAssetAtPath<NpcTypePreset>($"{PresetsDir}/{id}.asset");
                if (preset != null)
                {
                    preset.SourceFbx = SourceFbx(project, id, rev);
                    preset.Triangles = after;
                    EditorUtility.SetDirty(preset);
                }
                var lodGroup = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath).GetComponent<LODGroup>();
                log.AppendLine(Inv($"  {id,-23} v{rev:00} {before,6} -> {after,6} tris, LODs {string.Join(" / ", tris)}, LODGroup {(lodGroup != null ? lodGroup.lodCount : 0)}  {OptName(id, rev)}{changes}"));
                done++;
            }
            AssetDatabase.SaveAssets();
            log.AppendLine($"  {done} prefabs on opt meshes, {failed} failed");
            return log.ToString();
        }

        private static void Copy(string project, string source, string target, List<string> copied)
        {
            string from = Path.Combine(project, source), to = Path.Combine(project, target);
            if (File.Exists(to)) return;
            if (!File.Exists(from)) throw new FileNotFoundException("NPC type source missing", from);
            File.Copy(from, to, false);
            copied.Add(target);
        }

        private static bool ConfigureType(string path, Avatar avatar)
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            if (importer.animationType == ModelImporterAnimationType.Generic && importer.avatarSetup == ModelImporterAvatarSetup.CopyFromOther &&
                importer.sourceAvatar == avatar && !importer.importAnimation) return false;
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
            importer.sourceAvatar = avatar;
            importer.importAnimation = false;
            importer.importBlendShapes = true;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
            importer.SaveAndReimport();
            return true;
        }

        private static bool ConfigureStatic(string path)
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            if (importer.animationType == ModelImporterAnimationType.None && !importer.importAnimation) return false;
            importer.animationType = ModelImporterAnimationType.None;
            importer.importAnimation = false;
            importer.SaveAndReimport();
            return true;
        }

        // The visual prefab, as GreyboxBuddySetup.EnsurePrefabs makes SausageBuddy_A.
        private static GameObject BuildPrefab(GameObject model, Scene scene, string id, AnimatorController controller, Avatar avatar, bool handProps, float scale)
        {
            var root = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
            PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
            root.name = "SausageBuddy_" + id;
            // opt_v02 models: LOD0 under the plain part names (as Repoint keeps them), our LODGroup instead of the importer's.
            foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.name.EndsWith("_LOD0", StringComparison.Ordinal) && LodOf(smr.name, out string part) == 0) smr.gameObject.name = part;
            if (!root.TryGetComponent(out Animator animator)) animator = root.AddComponent<Animator>();
            animator.runtimeAnimatorController = controller;
            animator.avatar = avatar;
            animator.applyRootMotion = false;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            NpcRagdollBuilder.EnsureRig(root);
            if (handProps && !root.TryGetComponent(out NpcHeldProps _)) root.AddComponent<NpcHeldProps>();
            root.transform.localScale = Vector3.one * scale;
            SetupLods(root);
            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(root, $"{PrefabsDir}/SausageBuddy_{id}.prefab");
            Object.DestroyImmediate(root);
            return prefab;
        }

        private static NpcTypePreset WritePreset(string id, int rev, Validation v, GameObject prefab, string fbx, int tris, bool props, float scale, float lift)
        {
            string path = $"{PresetsDir}/{id}.asset";
            var preset = AssetDatabase.LoadAssetAtPath<NpcTypePreset>(path);
            if (preset == null)
            {
                preset = ScriptableObject.CreateInstance<NpcTypePreset>();
                AssetDatabase.CreateAsset(preset, path);
            }
            preset.TypeId = id;
            preset.Revision = rev;
            preset.DisplayName = v.npc_type != null && !string.IsNullOrEmpty(v.npc_type.label) ? v.npc_type.label : id;
            preset.Group = v.npc_type != null ? v.npc_type.group ?? "" : "";
            preset.Visual = prefab;
            preset.GameScale = scale;
            preset.GroundLift = lift;
            preset.HandProps = props;
            preset.Triangles = tris;
            preset.HeightM = v.height_m;
            preset.SourceFbx = fbx;
            EditorUtility.SetDirty(preset);
            return preset;
        }

        // Weights: no numbers in Vadim's specs; 1 each, Rough gopniks and drunks 1.5 (ROUGH_SPEC: drunks at the shop and
        // the den, gopniks at the entrances and the football box). The special-prop beach types and the bodybuilder's
        // pull-up bar are placements (data for the scene builder).
        private static void WriteTables(Dictionary<string, NpcTypePreset> p, GameObject mound)
        {
            var tables = AssetDatabase.LoadAssetAtPath<NpcSpawnTables>(TablesPath);
            if (tables == null)
            {
                tables = ScriptableObject.CreateInstance<NpcSpawnTables>();
                AssetDatabase.CreateAsset(tables, TablesPath);
            }
            NpcSpawnTables.District D(string id, string[] aliases, params (string type, float weight, bool unique)[] entries)
            {
                var d = new NpcSpawnTables.District { Id = id, Aliases = aliases };
                foreach (var e in entries)
                    if (p.TryGetValue(e.type, out NpcTypePreset preset)) d.Entries.Add(new NpcSpawnTables.Entry { Type = preset, Weight = e.weight, Unique = e.unique });
                return d;
            }
            string[] none = Array.Empty<string>();
            tables.Districts = new List<NpcSpawnTables.District>
            {
                D("forest", none, ("FOREST_OD_JUNKIE", 1f, false), ("FOREST_STASHER", 1f, false)),
                // W86: + HAMLET_MUZHIK (README Hamlet row), + OLD_POPKING (Downtown street NPC, "not VIP", spec 5б),
                // BAD_ALTGIRL out of Rough (Vadim TASK-000883: VIP only). ImportOnly types have no rows.
                D("hamlet", new[] { "village" }, ("HAMLET_GRANNY", 1f, false), ("HAMLET_SHEPHERD", 1f, false), ("HAMLET_BOXERS_GRANDPA", 1f, false),
                    ("HAMLET_BODYBUILDER", 1f, true), ("HAMLET_MUZHIK", 1f, false)),
                D("construction", new[] { "transition" }, ("CONSTR_INDIAN", 1f, false), ("CONSTR_UZBEK", 1f, false), ("CONSTR_MEXICAN", 1f, false),
                    ("CONSTR_AFROAMERICAN", 1f, false), ("CONSTR_ARAB", 1f, false)),
                D("rough", new[] { "residential" }, ("BAD_GOPNIK", 1.5f, false), ("BAD_DRUNK", 1.5f, false), ("BAD_RAPPER", 1f, false), ("BAD_HUSTLER", 1f, false),
                    ("BAD_GIRL", 1f, false), ("BAD_BOMZH", 1f, false), ("BAD_BOMZHIHA", 1f, false), ("BAD_VAPER", 1f, false)),
                D("downtown", new[] { "old_town" }, ("OLD_RAPPER", 1f, false), ("OLD_STREAMER", 1f, false), ("OLD_STUDENT", 1f, false), ("OLD_OFFICE", 1f, false),
                    ("OLD_FITNESS", 1f, false), ("OLD_COURIER", 1f, false), ("OLD_BUSINESSMAN", 1f, false), ("OLD_KAREN", 1f, false), ("OLD_POPKING", 1f, false)),
                D("port", new[] { "industrial" }, ("PROM_FOREMAN", 1f, false), ("PROM_SAILOR", 1f, false)),
                D("beach", none, ("BEACH_CORN", 1f, false), ("BEACH_SUNBURN", 1f, false), ("BEACH_LIFEGUARD", 1f, false), ("BEACH_NUDIST", 1f, false)),
                D("elite", none),
                D("quiet_valley", none),
                D("tramduro", none),
            };
            NpcSpawnTables.Placement P(string type, string district, string activity, GameObject prop, Vector2 hours, string note) =>
                new() { Type = p.TryGetValue(type, out NpcTypePreset t) ? t : null, District = district, Activity = activity, Prop = prop, Hours = hours, Note = note };
            var allDay = new Vector2(0f, 24f);
            tables.Placements = new List<NpcSpawnTables.Placement>
            {
                P("BEACH_BURIED", "beach", "Idle", mound, allDay, "Buried to the neck: stands in Idle at the centre of BEACH_BURIED_SandMound_v01 (the mound hides the body). No walking."),
                P("BEACH_CASTLE", "beach", "Idle", null, allDay, "Builds sand pies by the water: bucket and spade are hand props (dropped on danger)."),
                P("BEACH_DETECTOR", "beach", "Idle", null, allDay, "Treasure hunter: the metal detector is a hand prop (dropped on danger)."),
                P("BEACH_SUNBURN", "beach", "BeachLie", null, allDay, "Lies on a lounger (BEACH_SPEC: part of the beach NPCs lie on loungers); also walks (beach table)."),
                P("HAMLET_BODYBUILDER", "hamlet", "Idle", null, new Vector2(6f, 10f),
                  "Unique (buyers' special order). At the pull-up bar on the Hamlet square 06:00-10:00 (SALES spec); walks the Hamlet otherwise. Twin-brother respawn = sales logic, not here."),
            };
            EditorUtility.SetDirty(tables);
        }

        // ---------- phase 2 / smoke test ----------

        /// <summary>One inactive crowd template per type of the tables (MapGreyboxBuilder.SpawnCrowdNpc, as MapCrowdPlacer
        /// makes the A/B templates) under the director's "Templates" object, appended to director.Templates (the visual
        /// lifted by the preset's GroundLift); director.TypeTable = tables. Returns how many were added.</summary>
        public static int AddTypeTemplates(CrowdDirector director, NpcSpawnTables tables, bool sea)
        {
            var grab = AssetDatabase.LoadAssetAtPath<GrabPhysicsProfile>(GrabProfilePath);
            Transform parent = director.transform.Find("Templates");
            if (parent == null)
            {
                parent = new GameObject("Templates").transform;
                parent.SetParent(director.transform, false);
            }
            var list = new List<GameObject>(director.Templates ?? Array.Empty<GameObject>());
            var have = new HashSet<string>();
            foreach (GameObject t in list) if (t != null) have.Add(NpcSpawnTables.VisualOf(t));
            var types = new List<NpcTypePreset>();
            foreach (NpcSpawnTables.District d in tables.Districts) foreach (NpcSpawnTables.Entry e in d.Entries) if (e.Type != null && !types.Contains(e.Type)) types.Add(e.Type);
            foreach (NpcSpawnTables.Placement pl in tables.Placements) if (pl.Type != null && !types.Contains(pl.Type)) types.Add(pl.Type);
            int added = 0;
            foreach (NpcTypePreset type in types)
            {
                if (type.Visual == null || have.Contains(type.VisualName)) continue;
                GameObject npc = MapGreyboxBuilder.SpawnCrowdNpc(type.Visual, "CrowdTemplate_" + type.TypeId, Vector3.zero, 0f, grab, sea);
                npc.transform.SetParent(parent, false);
                if (type.GroundLift > 0f) npc.GetComponentInChildren<Animator>(true).transform.localPosition = Vector3.up * type.GroundLift;
                npc.SetActive(false);
                list.Add(npc);
                added++;
            }
            director.Templates = list.ToArray();
            director.TypeTable = tables;
            EditorUtility.SetDirty(director);
            return added;
        }

        // ---------- checks ----------

        private static Dictionary<string, Transform> Bones(GameObject instance)
        {
            var bones = new Dictionary<string, Transform>();
            foreach (Transform t in instance.GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("mixamorig:") && !bones.ContainsKey(t.name)) bones.Add(t.name, t);
            return bones;
        }

        private static void Compare(Dictionary<string, Transform> reference, Dictionary<string, Transform> bones, out int matched, out float dPos, out float dRot)
        {
            matched = 0;
            dPos = dRot = 0f;
            foreach (var kv in reference)
            {
                if (!bones.TryGetValue(kv.Key, out Transform t)) continue;
                matched++;
                // Both posed by Buddy A's Idle frame 0 at the origin: what the game shows (the FBX rest rotations differ:
                // A v04 was exported posed, the types in their rest pose; every clip keys the bones).
                dPos = Mathf.Max(dPos, Vector3.Distance(kv.Value.position, t.position));
                dRot = Mathf.Max(dRot, Quaternion.Angle(kv.Value.rotation, t.rotation));
            }
        }

        // Lowest vertex (m above the root) of the model posed by Buddy A's Idle frame 0 (the game plays A's clips on it).
        private static float FeetUnderIdle(GameObject instance, AnimationClip idle)
        {
            if (idle != null) idle.SampleAnimation(instance, 0f);
            float min = float.MaxValue;
            var baked = new Mesh();
            foreach (SkinnedMeshRenderer smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null || smr.name.StartsWith("Props_") || LodOf(smr.name, out _) > 0) continue;
                smr.BakeMesh(baked, true);
                foreach (Vector3 v in baked.vertices) min = Mathf.Min(min, smr.transform.TransformPoint(v).y);
            }
            Object.DestroyImmediate(baked);
            Object.DestroyImmediate(instance);
            return min;
        }

        [Serializable] private sealed class Validation { public float height_m; public NpcTypeJson npc_type; public Grounding grounding_offset_m; }
        [Serializable] private sealed class NpcTypeJson { public string label, group; public float game_scale = 1f; public bool hand_props; }
        [Serializable] private sealed class Grounding { public float Idle; }

        private static Validation ReadValidation(string project, string id, int rev)
        {
            string path = Path.Combine(project, SourceDir, id, $"validation_{id}_v{rev:00}.json");
            return File.Exists(path) ? JsonUtility.FromJson<Validation>(File.ReadAllText(path)) ?? new Validation() : new Validation();
        }

        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        private static string Inv(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);
    }
}
